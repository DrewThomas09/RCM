"""Monte Carlo over the v2 value bridge.

The v1 simulator (:mod:`rcm_mc.mc.ebitda_mc`) samples two noise
sources — prediction uncertainty and execution uncertainty — and runs
each draw through :class:`~rcm_mc.pe.rcm_ebitda_bridge.RCMEBITDABridge`.
That was the right surface for the research-band-calibrated v1
bridge. The v2 bridge (:mod:`rcm_mc.pe.value_bridge_v2`) exposes
*more* honest knobs: collection realization, denial overturn rate,
per-payer revenue leverage, and an exit multiple that partners want
to sample over rather than fix. This simulator runs Monte Carlo over
those additional dimensions *on top* of prediction+execution noise.

Why a separate simulator rather than extending v1? Three reasons:

1. The v2 bridge's per-sim assumption-construction surface is
   non-trivial (sampled ``BridgeAssumptions`` object with a sampled
   per-payer leverage dict). Sitting that inside v1's loop would
   branch the v1 code and make the research-band-calibration tests
   harder to reason about.
2. The v2 bridge already runs the cross-lever dependency walker on
   every call (Prompt 15); v1 doesn't. Running both off the same
   simulator loop would have to fork anyway.
3. The v2 output shape is richer — one-time cash and EV from recurring
   are first-class separate distributions, not folded into a single
   "ebitda_impact" series. Partners want to see both.

Shared primitives — ``DistributionSummary``, ``TornadoBar``,
``HistogramBin``, ``check_convergence`` — are imported from
:mod:`rcm_mc.mc.ebitda_mc` and :mod:`rcm_mc.mc.convergence`. The v1
simulator is untouched; both coexist.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..finance.reimbursement_engine import PayerClass, ReimbursementProfile
from ..pe.value_bridge_v2 import (
    BridgeAssumptions,
    ValueBridgeResult,
    _PAYER_REVENUE_LEVERAGE,
    compute_value_bridge,
)
from .convergence import ConvergenceReport, check_convergence
from .ebitda_mc import (
    DistributionSummary,
    HistogramBin,
    MetricAssumption,
    RCMMonteCarloSimulator,
    TornadoBar,
    _histogram,
)

logger = logging.getLogger(__name__)


# ── Default sampling parameters ────────────────────────────────────

# Collection realization: beta(6.5, 3.5) → mean 0.65, concentration 10.
# Matches the ``BridgeAssumptions`` default so the center of the
# distribution reproduces the deterministic bridge when variance is
# collapsed.
_DEFAULT_COLLECTION_ALPHA = 6.5
_DEFAULT_COLLECTION_BETA = 3.5

# Denial overturn: beta(5.5, 4.5) → mean 0.55. Slightly wider because
# overturn success is notoriously counterparty-dependent and partner
# priors are less tight than on collection realization.
_DEFAULT_OVERTURN_ALPHA = 5.5
_DEFAULT_OVERTURN_BETA = 4.5

# Per-payer revenue leverage: normal(μ, σ=0.05) clipped to [0.2, 1.2].
# σ=0.05 gives ±10pts at 2σ which feels right for payer-mix driven
# revenue-per-recovered-claim leverage uncertainty.
_DEFAULT_LEVERAGE_SIGMA = 0.05
_LEVERAGE_CLIP_LOW = 0.2
_LEVERAGE_CLIP_HIGH = 1.2

# Exit multiple triangular: low=0.85×mode, high=1.25×mode by default.
# Skewed right because partners worry more about multiple compression
# than about multiple expansion — the loss tail is the binding one.
_EXIT_MULT_LOW_FRACTION = 0.85
_EXIT_MULT_HIGH_FRACTION = 1.25


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class V2MonteCarloResult:
    """Output of a v2 Monte Carlo run.

    Unlike the v1 ``MonteCarloResult``, the v2 result carries *four*
    separate distributions — recurring EBITDA, one-time cash, EV from
    recurring, and total cash — because the v2 bridge is explicit that
    capitalizing one-time cash release would overstate enterprise
    value. Partners read these side-by-side.
    """
    n_simulations: int = 0
    recurring_ebitda_distribution: DistributionSummary = field(
        default_factory=DistributionSummary,
    )
    one_time_cash_distribution: DistributionSummary = field(
        default_factory=DistributionSummary,
    )
    ev_from_recurring_distribution: DistributionSummary = field(
        default_factory=DistributionSummary,
    )
    total_cash_distribution: DistributionSummary = field(
        default_factory=DistributionSummary,
    )
    moic_distribution: DistributionSummary = field(
        default_factory=DistributionSummary,
    )
    irr_distribution: DistributionSummary = field(
        default_factory=DistributionSummary,
    )
    probability_of_negative_impact: float = 0.0
    probability_of_target_moic: Dict[str, float] = field(default_factory=dict)
    #: Share-of-variance in recurring EBITDA attributable to each
    #: sampled dimension. Keys are metric_keys plus the bridge-level
    #: dimensions ``collection_realization``, ``denial_overturn_rate``,
    #: ``exit_multiple``, and ``leverage:<payer>`` per sampled payer.
    variance_contribution: Dict[str, float] = field(default_factory=dict)
    tornado_data: List[TornadoBar] = field(default_factory=list)
    histogram_data: List[HistogramBin] = field(default_factory=list)
    convergence_check: ConvergenceReport = field(default_factory=ConvergenceReport)
    #: Always ``True`` — the v2 bridge always runs the dependency
    #: walker. Exposed as a flag so renderers can label results
    #: unambiguously when sitting next to a v1 output.
    dependency_adjusted: bool = True
    scenario_label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_simulations": int(self.n_simulations),
            "recurring_ebitda_distribution": self.recurring_ebitda_distribution.to_dict(),
            "one_time_cash_distribution": self.one_time_cash_distribution.to_dict(),
            "ev_from_recurring_distribution": self.ev_from_recurring_distribution.to_dict(),
            "total_cash_distribution": self.total_cash_distribution.to_dict(),
            "moic_distribution": self.moic_distribution.to_dict(),
            "irr_distribution": self.irr_distribution.to_dict(),
            "probability_of_negative_impact": float(
                self.probability_of_negative_impact
            ),
            "probability_of_target_moic": {
                k: float(v) for k, v in self.probability_of_target_moic.items()
            },
            "variance_contribution": {
                k: float(v) for k, v in self.variance_contribution.items()
            },
            "tornado_data": [t.to_dict() for t in self.tornado_data],
            "histogram_data": [h.to_dict() for h in self.histogram_data],
            "convergence_check": self.convergence_check.to_dict(),
            "dependency_adjusted": bool(self.dependency_adjusted),
            "scenario_label": self.scenario_label,
        }


# ── Simulator ──────────────────────────────────────────────────────

class V2MonteCarloSimulator:
    """Monte Carlo wrapper around :func:`compute_value_bridge`.

    Usage::

        sim = V2MonteCarloSimulator(n_simulations=5000, seed=42)
        sim.configure(
            current_metrics=current,
            metric_assumptions=assumptions,
            reimbursement_profile=profile,
            base_assumptions=BridgeAssumptions(...),
            current_ebitda=80_000_000,
        )
        result = sim.run(scenario_label="base")

    Every ``metric_assumptions`` entry is a :class:`MetricAssumption`
    (shared with v1). The simulator reuses v1's prediction+execution
    sampling primitives and then layers in the v2-specific
    collection/overturn/leverage/exit-multiple sampling.
    """

    def __init__(
        self,
        *,
        n_simulations: int = 5_000,
        seed: int = 42,
    ) -> None:
        if n_simulations < 1:
            raise ValueError(
                f"n_simulations must be >= 1, got {n_simulations}"
            )
        self.n_simulations = int(n_simulations)
        self.seed = int(seed)
        # Populated by configure().
        self._current_metrics: Dict[str, float] = {}
        self._assumptions: Dict[str, MetricAssumption] = {}
        self._metric_order: List[str] = []
        self._reimbursement_profile: Optional[ReimbursementProfile] = None
        self._realization: Optional[Dict[str, Any]] = None
        self._base_assumptions: BridgeAssumptions = BridgeAssumptions()
        self.current_ebitda: float = 0.0
        self.entry_multiple: float = 10.0
        self.hold_years: float = 5.0
        # Prompt 17: month at which each sim's bridge is evaluated.
        # ``None`` → use ``base_assumptions.evaluation_month`` (36 =
        # full run-rate). Drop to 12 to model Year-1 partial credit.
        self.hold_months: Optional[int] = None
        self.organic_growth_pct: float = 0.0
        self.moic_targets: Sequence[float] = (1.5, 2.0, 2.5, 3.0)
        # v2-specific sampling controls. ``None`` means "use defaults".
        self._collection_alpha_beta: Tuple[float, float] = (
            _DEFAULT_COLLECTION_ALPHA, _DEFAULT_COLLECTION_BETA,
        )
        self._overturn_alpha_beta: Tuple[float, float] = (
            _DEFAULT_OVERTURN_ALPHA, _DEFAULT_OVERTURN_BETA,
        )
        self._leverage_sigma: float = _DEFAULT_LEVERAGE_SIGMA
        self._exit_multiple_low: Optional[float] = None
        self._exit_multiple_high: Optional[float] = None
        # Zero-variance mode: when True, every sampled dimension
        # collapses to its mean. The v2 bridge then reproduces its
        # deterministic output — useful for equivalence tests.
        self._zero_variance: bool = False

    # ── Configuration ─────────────────────────────────────────────

    def configure(
        self,
        *,
        current_metrics: Dict[str, float],
        metric_assumptions: Dict[str, MetricAssumption],
        reimbursement_profile: Optional[ReimbursementProfile],
        base_assumptions: Optional[BridgeAssumptions] = None,
        realization: Optional[Dict[str, Any]] = None,
        current_ebitda: float = 0.0,
        entry_multiple: float = 10.0,
        hold_years: float = 5.0,
        organic_growth_pct: float = 0.0,
        moic_targets: Sequence[float] = (1.5, 2.0, 2.5, 3.0),
        metric_order: Optional[List[str]] = None,
        collection_alpha_beta: Optional[Tuple[float, float]] = None,
        overturn_alpha_beta: Optional[Tuple[float, float]] = None,
        leverage_sigma: Optional[float] = None,
        exit_multiple_range: Optional[Tuple[float, float]] = None,
        zero_variance: bool = False,
        hold_months: Optional[int] = None,
    ) -> "V2MonteCarloSimulator":
        """Wire the simulator with deal-specific inputs.

        ``base_assumptions.exit_multiple`` is the *mode* of the
        triangular exit-multiple distribution. ``exit_multiple_range``
        overrides the default [0.85×mode, 1.25×mode] band.

        Setting ``zero_variance=True`` collapses every sampled dimension
        to its mean, which makes the simulator's output deterministic
        and identical to a single :func:`compute_value_bridge` call.
        Used by the identity-equivalence test.
        """
        self._current_metrics = dict(current_metrics or {})
        self._assumptions = {
            str(k): v for k, v in (metric_assumptions or {}).items()
        }
        order = (
            list(metric_order) if metric_order is not None
            else list(self._assumptions.keys())
        )
        for k in order:
            if k not in self._assumptions:
                raise ValueError(
                    f"metric_order references unknown metric {k!r}"
                )
        self._metric_order = order
        self._reimbursement_profile = reimbursement_profile
        self._realization = (
            dict(realization) if realization is not None else None
        )
        self._base_assumptions = base_assumptions or BridgeAssumptions()
        self.current_ebitda = float(current_ebitda)
        self.entry_multiple = float(entry_multiple)
        self.hold_years = float(hold_years)
        self.organic_growth_pct = float(organic_growth_pct)
        self.moic_targets = tuple(float(t) for t in moic_targets)
        if collection_alpha_beta is not None:
            self._collection_alpha_beta = (
                float(collection_alpha_beta[0]),
                float(collection_alpha_beta[1]),
            )
        if overturn_alpha_beta is not None:
            self._overturn_alpha_beta = (
                float(overturn_alpha_beta[0]),
                float(overturn_alpha_beta[1]),
            )
        if leverage_sigma is not None:
            self._leverage_sigma = float(leverage_sigma)
        if exit_multiple_range is not None:
            lo, hi = exit_multiple_range
            self._exit_multiple_low = float(lo)
            self._exit_multiple_high = float(hi)
        self._zero_variance = bool(zero_variance)
        self.hold_months = int(hold_months) if hold_months is not None else None
        return self

    # ── Sampling primitives ───────────────────────────────────────

    def _sample_collection_realization(
        self, rng: np.random.Generator,
    ) -> float:
        if self._zero_variance:
            return float(self._base_assumptions.collection_realization)
        a, b = self._collection_alpha_beta
        # Retarget so the beta's mean matches the configured
        # collection_realization. We do this by keeping the sum a+b
        # (the concentration) and rebalancing.
        total = a + b
        target_mean = max(
            0.001,
            min(0.999, float(self._base_assumptions.collection_realization)),
        )
        a_eff = target_mean * total
        b_eff = (1.0 - target_mean) * total
        return float(np.clip(rng.beta(a_eff, b_eff), 0.0, 1.0))

    def _sample_denial_overturn_rate(
        self, rng: np.random.Generator,
    ) -> float:
        if self._zero_variance:
            return float(self._base_assumptions.denial_overturn_rate)
        a, b = self._overturn_alpha_beta
        total = a + b
        target_mean = max(
            0.001,
            min(0.999, float(self._base_assumptions.denial_overturn_rate)),
        )
        a_eff = target_mean * total
        b_eff = (1.0 - target_mean) * total
        return float(np.clip(rng.beta(a_eff, b_eff), 0.0, 1.0))

    def _sample_exit_multiple(self, rng: np.random.Generator) -> float:
        mode = float(self._base_assumptions.exit_multiple)
        if self._zero_variance:
            return mode
        lo = (
            self._exit_multiple_low
            if self._exit_multiple_low is not None
            else _EXIT_MULT_LOW_FRACTION * mode
        )
        hi = (
            self._exit_multiple_high
            if self._exit_multiple_high is not None
            else _EXIT_MULT_HIGH_FRACTION * mode
        )
        # Guard against degenerate configurations.
        if not (lo <= mode <= hi):
            lo, mode, hi = min(lo, mode, hi), mode, max(lo, mode, hi)
        if lo == hi:
            return lo
        return float(rng.triangular(lo, mode, hi))

    # ── Vectorized dimension samplers (Prompt 19) ────────────────

    def _sample_collection_vectorized(
        self, rng: np.random.Generator, n: int,
    ) -> np.ndarray:
        """Draw ``n`` collection-realization samples in one batch.

        Matches :meth:`_sample_collection_realization` distributionally
        — the beta is rebalanced to the configured mean and scaled by
        the configured concentration.
        """
        if self._zero_variance:
            return np.full(n, self._base_assumptions.collection_realization)
        a, b = self._collection_alpha_beta
        total = a + b
        target_mean = max(
            0.001,
            min(0.999, float(self._base_assumptions.collection_realization)),
        )
        a_eff = target_mean * total
        b_eff = (1.0 - target_mean) * total
        return np.clip(rng.beta(a_eff, b_eff, size=n), 0.0, 1.0)

    def _sample_overturn_vectorized(
        self, rng: np.random.Generator, n: int,
    ) -> np.ndarray:
        if self._zero_variance:
            return np.full(n, self._base_assumptions.denial_overturn_rate)
        a, b = self._overturn_alpha_beta
        total = a + b
        target_mean = max(
            0.001,
            min(0.999, float(self._base_assumptions.denial_overturn_rate)),
        )
        a_eff = target_mean * total
        b_eff = (1.0 - target_mean) * total
        return np.clip(rng.beta(a_eff, b_eff, size=n), 0.0, 1.0)

    def _sample_exit_multiple_vectorized(
        self, rng: np.random.Generator, n: int,
    ) -> np.ndarray:
        mode = float(self._base_assumptions.exit_multiple)
        if self._zero_variance:
            return np.full(n, mode)
        lo = (
            self._exit_multiple_low
            if self._exit_multiple_low is not None
            else _EXIT_MULT_LOW_FRACTION * mode
        )
        hi = (
            self._exit_multiple_high
            if self._exit_multiple_high is not None
            else _EXIT_MULT_HIGH_FRACTION * mode
        )
        if not (lo <= mode <= hi):
            lo, hi = min(lo, mode, hi), max(lo, mode, hi)
        if lo == hi:
            return np.full(n, lo)
        return rng.triangular(lo, mode, hi, size=n)

    def _sample_payer_leverage_vectorized(
        self, rng: np.random.Generator, n: int,
        payer_keys: List[PayerClass],
    ) -> np.ndarray:
        """Return a ``(n_payers, n)`` array of per-payer leverage draws.

        Rows follow the order of ``payer_keys`` — keeps the variance-
        decomposition rekey stable across a single run.
        """
        override = self._base_assumptions.payer_revenue_leverage or {}
        out = np.zeros((len(payer_keys), n), dtype=float)
        for k, pc in enumerate(payer_keys):
            mu = _resolve_leverage_mean(pc, override)
            if self._zero_variance:
                out[k, :] = mu
                continue
            draws = rng.normal(mu, self._leverage_sigma, size=n)
            out[k, :] = np.clip(
                draws, _LEVERAGE_CLIP_LOW, _LEVERAGE_CLIP_HIGH,
            )
        return out

    def _sample_payer_leverage(
        self, rng: np.random.Generator,
    ) -> Dict[PayerClass, float]:
        """Draw per-payer leverage, clipped to ``[0.2, 1.2]``."""
        payers: List[PayerClass]
        if (
            self._reimbursement_profile
            and self._reimbursement_profile.payer_classes
        ):
            payers = list(self._reimbursement_profile.payer_classes.keys())
        else:
            payers = list(_PAYER_REVENUE_LEVERAGE.keys())
        override = self._base_assumptions.payer_revenue_leverage or {}
        out: Dict[PayerClass, float] = {}
        for pc in payers:
            mu = _resolve_leverage_mean(pc, override)
            if self._zero_variance:
                out[pc] = mu
                continue
            draw = rng.normal(mu, self._leverage_sigma)
            out[pc] = float(
                np.clip(draw, _LEVERAGE_CLIP_LOW, _LEVERAGE_CLIP_HIGH)
            )
        return out

    # ── Run ───────────────────────────────────────────────────────

    def run(self, *, scenario_label: str = "") -> V2MonteCarloResult:
        if not self._assumptions:
            raise RuntimeError(
                "configure() must be called with at least one metric assumption"
            )
        rng = np.random.default_rng(self.seed)
        n = self.n_simulations
        order = list(self._metric_order)

        # Pre-resolve the payer order so leverage_samples keys are
        # stable across the run.
        if (
            self._reimbursement_profile
            and self._reimbursement_profile.payer_classes
        ):
            payer_order_keys: List[PayerClass] = list(
                self._reimbursement_profile.payer_classes.keys(),
            )
        else:
            payer_order_keys = list(_PAYER_REVENUE_LEVERAGE.keys())
        payer_order = [pc.value for pc in payer_order_keys]

        # ── 1. Vectorized sampling (Prompt 19) ──────────────────
        # Per-metric target + execution via the v1 simulator's
        # vectorized helpers. We re-use them rather than duplicating
        # the sampling code here.
        self_v1_view = RCMMonteCarloSimulator.__new__(RCMMonteCarloSimulator)
        self_v1_view._assumptions = self._assumptions
        self_v1_view._metric_order = order
        self_v1_view._corr_matrix = None
        sampled_targets = self_v1_view._sample_predictions_vectorized(
            rng, n, order,
        )
        exec_fractions = self_v1_view._sample_executions_vectorized(
            rng, n, order,
        )
        current_row = np.array(
            [self._assumptions[m].current_value for m in order],
            dtype=float,
        )
        final_values = current_row[None, :] + (
            sampled_targets - current_row[None, :]
        ) * exec_fractions

        # v2-specific sampled dimensions — all at once.
        collection_samples = self._sample_collection_vectorized(rng, n)
        overturn_samples = self._sample_overturn_vectorized(rng, n)
        exit_mult_samples = self._sample_exit_multiple_vectorized(rng, n)
        leverage_by_payer = self._sample_payer_leverage_vectorized(
            rng, n, payer_order_keys,
        )   # (n_payers, n)

        # Build per-sim BridgeAssumptions lazily; compute_value_bridge
        # is called once per sim via the vectorized adapter.
        eval_month = (
            self.hold_months
            if self.hold_months is not None
            else int(self._base_assumptions.evaluation_month)
        )
        assumptions_per_sim: List[BridgeAssumptions] = []
        for i in range(n):
            leverage_dict = {
                pc: float(leverage_by_payer[k, i])
                for k, pc in enumerate(payer_order_keys)
            }
            assumptions_per_sim.append(BridgeAssumptions(
                exit_multiple=float(exit_mult_samples[i]),
                cost_of_capital=self._base_assumptions.cost_of_capital,
                collection_realization=float(collection_samples[i]),
                denial_overturn_rate=float(overturn_samples[i]),
                rework_cost_per_claim=self._base_assumptions.rework_cost_per_claim,
                cost_per_follow_up_fte=self._base_assumptions.cost_per_follow_up_fte,
                claims_per_follow_up_fte=self._base_assumptions.claims_per_follow_up_fte,
                implementation_ramp=self._base_assumptions.implementation_ramp,
                confidence_inference_penalty=self._base_assumptions.confidence_inference_penalty,
                claims_volume=self._base_assumptions.claims_volume,
                net_revenue=self._base_assumptions.net_revenue,
                payer_revenue_leverage=leverage_dict,
                ramp_curves=self._base_assumptions.ramp_curves,
                evaluation_month=eval_month,
            ))

        # Baseline current metrics — shared across sims.
        current_metrics_for_sim = dict(self._current_metrics)
        for k in order:
            current_metrics_for_sim.setdefault(
                k, self._assumptions[k].current_value,
            )

        # ── 2. Vectorized bridge adapter ──────────────────────
        from ..pe.value_bridge_v2 import compute_value_bridge_vectorized
        recurring_ebitda, one_time_cash = compute_value_bridge_vectorized(
            current_metrics_for_sim,
            final_values,
            order,
            self._reimbursement_profile,
            assumptions_per_sim=assumptions_per_sim,
            base_assumptions=self._base_assumptions,
            realization=self._realization,
            current_ebitda=self.current_ebitda,
        )

        # EV from recurring: bridge's ``enterprise_value_from_recurring``
        # equals ``total_recurring_ebitda_delta × exit_multiple``. We
        # reproduce that here vectorially (rather than asking the
        # adapter to hand back a third array).
        ev_from_recurring = recurring_ebitda * exit_mult_samples

        # ── 3. Returns (vectorized) ──────────────────────────
        growth_factor = (1.0 + self.organic_growth_pct) ** self.hold_years
        exit_ebitda = self.current_ebitda * growth_factor + recurring_ebitda
        exit_ev = exit_ebitda * exit_mult_samples
        # Total cash to equity = exit EV + one-time WC release.
        # WC is *not* capitalized; it passes through as cash.
        total_cash = exit_ev + one_time_cash
        entry_ev = self.current_ebitda * self.entry_multiple
        if entry_ev > 0 and self.hold_years > 0:
            moic_values = total_cash / entry_ev
            with np.errstate(invalid="ignore"):
                irr_values = np.where(
                    moic_values > 0,
                    np.power(np.maximum(moic_values, 1e-18),
                              1.0 / self.hold_years) - 1.0,
                    -1.0,
                )
        else:
            moic_values = np.ones(n)
            irr_values = np.zeros(n)

        # Metric sample matrix for variance / tornado downstream.
        metric_samples: Dict[str, np.ndarray] = {
            m: final_values[:, col] for col, m in enumerate(order)
        }
        leverage_samples: Dict[str, np.ndarray] = {
            f"leverage:{pc.value}": leverage_by_payer[k]
            for k, pc in enumerate(payer_order_keys)
        }

        # ── Aggregate ────────────────────────────────────────────
        recurring_summary = DistributionSummary.from_array(recurring_ebitda)
        one_time_summary = DistributionSummary.from_array(one_time_cash)
        ev_summary = DistributionSummary.from_array(ev_from_recurring)
        total_cash_summary = DistributionSummary.from_array(total_cash)
        moic_summary = DistributionSummary.from_array(moic_values)
        irr_summary = DistributionSummary.from_array(irr_values)

        p_neg = float(np.mean(recurring_ebitda < 0))
        p_target_moic = {
            f"{t:g}x": float(np.mean(moic_values >= t))
            for t in self.moic_targets
        }

        # Variance contribution: correlation² against recurring EBITDA
        # across every sampled dimension. Normalized so contributions
        # sum to 1.0 (unless all samples are constant, then zeros).
        dimension_series: Dict[str, np.ndarray] = {}
        for k, arr in metric_samples.items():
            dimension_series[k] = arr
        dimension_series["collection_realization"] = collection_samples
        dimension_series["denial_overturn_rate"] = overturn_samples
        dimension_series["exit_multiple"] = exit_mult_samples
        for k, arr in leverage_samples.items():
            dimension_series[k] = arr

        variance_contribution = _variance_decomposition(
            dimension_series, recurring_ebitda,
        )

        tornado = _build_tornado(dimension_series, recurring_ebitda)
        histogram = _histogram(recurring_ebitda, n_bins=30)
        convergence = check_convergence(
            recurring_ebitda,
            window=max(100, int(n / 10)),
            tolerance=0.02,
        )

        return V2MonteCarloResult(
            n_simulations=int(n),
            recurring_ebitda_distribution=recurring_summary,
            one_time_cash_distribution=one_time_summary,
            ev_from_recurring_distribution=ev_summary,
            total_cash_distribution=total_cash_summary,
            moic_distribution=moic_summary,
            irr_distribution=irr_summary,
            probability_of_negative_impact=p_neg,
            probability_of_target_moic=p_target_moic,
            variance_contribution=variance_contribution,
            tornado_data=tornado,
            histogram_data=histogram,
            convergence_check=convergence,
            dependency_adjusted=True,
            scenario_label=str(scenario_label),
        )


# ── Helpers ────────────────────────────────────────────────────────

def _resolve_leverage_mean(
    pc: PayerClass, override: Dict[Any, float],
) -> float:
    """Resolve μ for a payer's leverage: override → module default → 0.7."""
    if pc in override:
        return float(override[pc])
    key = getattr(pc, "value", None)
    if key is not None and key in override:
        return float(override[key])
    return float(_PAYER_REVENUE_LEVERAGE.get(pc, 0.7))


def _variance_decomposition(
    dimension_series: Dict[str, np.ndarray],
    output: np.ndarray,
) -> Dict[str, float]:
    """First-order variance decomposition via ``corr²``.

    For each input dimension, compute squared Pearson correlation
    against the output. Normalize so contributions sum to 1.0 when
    any variance is present. Constant dimensions return 0.
    """
    var_y = float(np.var(output))
    raw: Dict[str, float] = {}
    for key, col in dimension_series.items():
        var_x = float(np.var(col))
        if var_x <= 1e-18 or var_y <= 1e-18:
            raw[key] = 0.0
            continue
        cov = float(
            np.mean((col - col.mean()) * (output - output.mean()))
        )
        r = cov / math.sqrt(var_x * var_y)
        raw[key] = r * r
    total = sum(raw.values())
    if total <= 0:
        return {k: 0.0 for k in raw}
    return {k: v / total for k, v in raw.items()}


def _build_tornado(
    dimension_series: Dict[str, np.ndarray],
    output: np.ndarray,
) -> List[TornadoBar]:
    """Tornado bars: mean output when the dimension is in its P10
    tail vs. its P90 tail. Sorted by absolute range descending.
    """
    bars: List[TornadoBar] = []
    for key, col in dimension_series.items():
        if len(col) == 0 or np.std(col) <= 0:
            continue
        lo_mask = col <= np.quantile(col, 0.10)
        hi_mask = col >= np.quantile(col, 0.90)
        if lo_mask.sum() == 0 or hi_mask.sum() == 0:
            continue
        p10 = float(np.mean(output[lo_mask]))
        p90 = float(np.mean(output[hi_mask]))
        bars.append(TornadoBar(
            metric=key,
            p10_impact=p10,
            p90_impact=p90,
            range=abs(p90 - p10),
        ))
    bars.sort(key=lambda t: t.range, reverse=True)
    return bars
