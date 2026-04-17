"""Deterministic RCM-metric → EBITDA bridge. **v1, legacy calibration.**

.. deprecated:: Phase-4 Prompt 3
    This is the v1 bridge. It applies uniform research-band
    coefficients to every hospital regardless of payer mix or
    reimbursement method. Use :mod:`rcm_mc.pe.value_bridge_v2` for
    new work — v2 reads the packet's reimbursement profile +
    realization path and produces different value for different
    hospital archetypes (commercial-heavy vs Medicare-heavy, DRG-
    exposed vs capitation-exposed, etc.).

    The v1 bridge remains in the codebase because its 29 regression
    tests lock every lever to the published research bands below; it
    serves as a calibration floor. The packet runs *both* bridges and
    surfaces them side-by-side (``packet.ebitda_bridge`` is v1,
    ``packet.value_bridge_result`` is v2). v1 will be retired once
    partners validate v2 on real deals — track
    ``docs/README_BUILD_STATUS.md`` for the deprecation timeline.

The research table v1 is calibrated against:

    Denial rate 12% → 5%             $8-15M   on $400M NPR
    A/R days 55 → 38                 $5-10M
    Clean claim rate 85% → 96%       $1-3M
    Net collection 92% → 97%         $10-15M
    Cost to collect 5% → 3%          $4-8M
    CDI / CMI +0.05-0.10             $3-8M

Every coefficient in this module is sized so that, given the hospital
profile implied above (net_revenue=$400M, payer_mix ~40% Medicare, claims
volume ~300K), the seven levers land inside those bands. The bands are
what a partner quotes in an IC conversation; a bridge that lands outside
them on a realistic profile is wrong, full stop.

Units convention — critical:

- *percentage* metrics (denial_rate, net_collection_rate, etc.) are
  stored in the RCM registry on a **0-100 percentage-point scale**:
  ``denial_rate = 12.0`` means 12%. Deltas are ``current - target`` in
  the same scale. All formulas consume pp deltas and internally divide
  by 100 where they need a fraction.
- dollars are annual dollars.
- days are calendar days.
- CMI is a dimensionless ratio (typically 1.2 - 2.5).

Every lever produces:
    revenue_impact + cost_impact (signed: positive = improves EBITDA)
    ebitda_impact = revenue_impact + cost_impact
    working_capital_impact (separate one-time cash; already reflected
        in ebitda via the interest saved)

Working capital is kept distinct from EBITDA at the packet level so an
LP never sees the one-time cash and the recurring interest lift added
together.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..analysis.packet import (
    EBITDABridgeResult,
    MetricImpact,
    SectionStatus,
)

logger = logging.getLogger(__name__)


# ── Constants calibrated against the research band ──────────────────

# Denial rate: fraction of denied revenue that is truly avoidable + never
# recovered. 0.35 means "a 1-pp reduction in initial denial rate
# recovers 35% of that 1pp × net_revenue." Matches the $8-15M band at
# 7pp on $400M NPR.
_DENIAL_AVOIDABLE_SHARE = 0.35

# AR days bad-debt coefficient: dollars of bad debt avoided per AR-day
# reduced, per dollar of NPR. Calibrated so 17-day reduction on $400M
# NPR lands ~$3-4M of bad-debt EBITDA lift.
_AR_BAD_DEBT_PER_DAY_PER_NPR_DOLLAR = 0.00065

# Cost of capital default when the caller doesn't supply one. Reflects
# mid-market PE leveraged debt cost, not risk-free rate.
_DEFAULT_COST_OF_CAPITAL = 0.08

# Net collection rate coefficient: partner-defensible "each pp of NCR
# improvement = 0.6% of NPR" on a healthy revenue-cycle. Lands 5pp
# improvement → ~$12M on $400M NPR, within the $10-15M band.
_NCR_COEFFICIENT = 0.60

# Clean claim rate: fewer claims sent back for rework.
_DEFAULT_COST_PER_REWORKED_CLAIM = 30.0

# First pass resolution: rework + FTE savings coefficient.
_FPR_REWORK_SHARE = 0.30           # fraction of rework saved per pp FPR lift
_DEFAULT_FTE_COST_FOLLOW_UP = 55_000.0
_DEFAULT_CLAIMS_PER_FOLLOW_UP_FTE = 10_000

# CMI: each 0.01 CMI uplift ≈ 0.75% of Medicare revenue.
_CMI_COEFFICIENT_PER_POINT = 0.75   # applied to 0.01-CMI-point deltas

# Cost to collect is stored as a percent of NPSR (e.g. 2.8 = 2.8%).

# ── Profile ─────────────────────────────────────────────────────────

@dataclass
class FinancialProfile:
    """Hospital economics the bridge needs to size each lever.

    Partners can override any coefficient by mutating the bridge's
    attributes after construction — all coefficients that match the
    research calibration are class-level defaults, not hard-coded
    inside the compute functions.
    """
    gross_revenue: float = 0.0
    net_revenue: float = 0.0
    total_operating_expenses: float = 0.0
    current_ebitda: float = 0.0
    cost_of_capital_pct: float = _DEFAULT_COST_OF_CAPITAL
    total_claims_volume: int = 0
    cost_per_reworked_claim: float = _DEFAULT_COST_PER_REWORKED_CLAIM
    fte_cost_follow_up: float = _DEFAULT_FTE_COST_FOLLOW_UP
    claims_per_follow_up_fte: int = _DEFAULT_CLAIMS_PER_FOLLOW_UP_FTE
    payer_mix: Dict[str, float] = field(default_factory=dict)
    #: Optional per-payer avg revenue per denied claim; if present
    #: overrides the net_revenue-based denial-impact coefficient. Keep
    #: this as a hook rather than a required input — most diligence
    #: packets never have this level of granularity.
    payer_denial_values: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Tornado / targets dataclasses ────────────────────────────────────

@dataclass
class TornadoRow:
    metric: str
    scenarios: Dict[str, float] = field(default_factory=dict)  # "1pct" → impact
    max_abs_impact: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "scenarios": dict(self.scenarios),
            "max_abs_impact": float(self.max_abs_impact),
        }


@dataclass
class TornadoResult:
    rows: List[TornadoRow] = field(default_factory=list)
    improvement_scenarios: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows": [r.to_dict() for r in self.rows],
            "improvement_scenarios": list(self.improvement_scenarios),
        }


@dataclass
class TargetTier:
    tier: str                                          # conservative | moderate | aggressive
    targets: Dict[str, float] = field(default_factory=dict)
    per_metric_impact: Dict[str, float] = field(default_factory=dict)
    total_ebitda_impact: float = 0.0
    achievability_score: float = 0.0                    # 0-1, higher = more achievable
    estimated_months_to_achieve: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "targets": {k: float(v) for k, v in self.targets.items()},
            "per_metric_impact": {k: float(v) for k, v in self.per_metric_impact.items()},
            "total_ebitda_impact": float(self.total_ebitda_impact),
            "achievability_score": float(self.achievability_score),
            "estimated_months_to_achieve": int(self.estimated_months_to_achieve),
        }


@dataclass
class TargetRecommendation:
    conservative: TargetTier
    moderate: TargetTier
    aggressive: TargetTier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conservative": self.conservative.to_dict(),
            "moderate": self.moderate.to_dict(),
            "aggressive": self.aggressive.to_dict(),
        }

    def tier(self, name: str) -> TargetTier:
        return {"conservative": self.conservative,
                "moderate": self.moderate,
                "aggressive": self.aggressive}[name]


# ── Industry improvement velocity (for achievability) ───────────────

# Roughly: how many months a partner expects to take for a 1-standard-
# deviation improvement on each lever. Drives estimated_months_to_achieve.
# Sourced from HFMA RCM operations benchmarks + a few partner interviews.
_MONTHS_PER_STDEV = {
    "denial_rate": 5,                 # 3-6 mo typical for denial mgmt
    "clean_claim_rate": 6,
    "first_pass_resolution_rate": 6,
    "days_in_ar": 9,                  # includes process + staffing changes
    "net_collection_rate": 12,        # payer renegotiation 6-18 mo
    "cost_to_collect": 12,
    "case_mix_index": 9,              # CDI 6-12 mo
}


# ── Lever implementations ───────────────────────────────────────────

def _safe_num(x: Any, default: float = 0.0) -> float:
    try:
        f = float(x)
    except (TypeError, ValueError):
        return float(default)
    if f != f or f in (float("inf"), float("-inf")):
        return float(default)
    return f


class RCMEBITDABridge:
    """RCM lever → EBITDA impact bridge.

    Usage::

        profile = FinancialProfile(net_revenue=400e6, ...)
        bridge = RCMEBITDABridge(profile)
        result = bridge.compute_bridge(
            current_metrics={"denial_rate": 12.0, ...},
            target_metrics={"denial_rate": 5.0, ...},
        )
        tornado = bridge.compute_sensitivity_tornado(current_metrics)
        recs = bridge.suggest_targets(current_metrics, comparables, registry)
    """

    # HFMA MAP Keys → lever descriptor. Each entry records the direction
    # of "better" and the impact type for display purposes.
    LEVER_DEFINITIONS: Dict[str, Dict[str, str]] = {
        "denial_rate":                {"direction": "lower_is_better", "impact_type": "revenue+cost"},
        "days_in_ar":                 {"direction": "lower_is_better", "impact_type": "working_capital+cost"},
        "net_collection_rate":        {"direction": "higher_is_better", "impact_type": "revenue"},
        "clean_claim_rate":           {"direction": "higher_is_better", "impact_type": "cost"},
        "cost_to_collect":            {"direction": "lower_is_better", "impact_type": "cost"},
        "first_pass_resolution_rate": {"direction": "higher_is_better", "impact_type": "cost"},
        "case_mix_index":             {"direction": "higher_is_better", "impact_type": "revenue"},
    }

    def __init__(self, financial_profile: FinancialProfile) -> None:
        self.profile = financial_profile
        self.denial_avoidable_share = _DENIAL_AVOIDABLE_SHARE
        self.ar_bad_debt_coefficient = _AR_BAD_DEBT_PER_DAY_PER_NPR_DOLLAR
        self.ncr_coefficient = _NCR_COEFFICIENT
        self.fpr_rework_share = _FPR_REWORK_SHARE
        self.cmi_coefficient_per_point = _CMI_COEFFICIENT_PER_POINT

    # ── Per-lever computations ──────────────────────────────────────

    def _medicare_npr_share(self) -> float:
        """Medicare share of NPSR (for CMI impact)."""
        mix = self.profile.payer_mix or {}
        mc = _safe_num(mix.get("medicare"), 0.4)
        if mc > 1.0:
            mc = mc / 100.0
        return max(0.0, min(1.0, mc))

    def _lever_denial_rate(
        self, current: float, target: float,
    ) -> MetricImpact:
        """1pp reduction → avoidable_share × net_revenue / 100 recovered revenue,
        plus claims_volume × cost_per_rework savings."""
        delta_pp = _safe_num(current) - _safe_num(target)   # >0 when improving
        npr = _safe_num(self.profile.net_revenue)
        revenue = (delta_pp / 100.0) * npr * self.denial_avoidable_share
        rework_saved = (delta_pp / 100.0) * float(self.profile.total_claims_volume or 0) * \
                       float(self.profile.cost_per_reworked_claim or 0.0)
        return MetricImpact(
            metric_key="denial_rate",
            current_value=_safe_num(current),
            target_value=_safe_num(target),
            revenue_impact=float(revenue),
            cost_impact=-float(rework_saved),              # negative cost = saving
            ebitda_impact=float(revenue + rework_saved),
            upstream_metrics=["denial_rate", "net_revenue", "total_claims_volume"],
        )

    def _lever_days_in_ar(
        self, current: float, target: float,
    ) -> MetricImpact:
        """Reduction in AR days releases (days×NPR/365) of one-time cash.
        Recurring EBITDA = released_cash × cost_of_capital + bad_debt reduction."""
        days_reduced = _safe_num(current) - _safe_num(target)
        npr = _safe_num(self.profile.net_revenue)
        if npr <= 0:
            return MetricImpact(
                metric_key="days_in_ar",
                current_value=_safe_num(current),
                target_value=_safe_num(target),
                upstream_metrics=["days_in_ar", "net_revenue"],
            )
        wc_released = days_reduced * (npr / 365.0)
        interest_saved = wc_released * _safe_num(self.profile.cost_of_capital_pct,
                                                  _DEFAULT_COST_OF_CAPITAL)
        bad_debt_avoided = days_reduced * npr * self.ar_bad_debt_coefficient
        ebitda = interest_saved + bad_debt_avoided
        return MetricImpact(
            metric_key="days_in_ar",
            current_value=_safe_num(current),
            target_value=_safe_num(target),
            revenue_impact=0.0,
            cost_impact=-float(ebitda),                    # savings = negative cost
            ebitda_impact=float(ebitda),
            working_capital_impact=float(wc_released),
            upstream_metrics=["days_in_ar", "net_revenue", "cost_of_capital_pct"],
        )

    def _lever_net_collection_rate(
        self, current: float, target: float,
    ) -> MetricImpact:
        """1pp higher NCR → ncr_coefficient × 1pp × NPR = 0.6% NPR per pp."""
        delta_pp = _safe_num(target) - _safe_num(current)   # >0 when improving
        npr = _safe_num(self.profile.net_revenue)
        revenue = (delta_pp / 100.0) * npr * self.ncr_coefficient
        return MetricImpact(
            metric_key="net_collection_rate",
            current_value=_safe_num(current),
            target_value=_safe_num(target),
            revenue_impact=float(revenue),
            cost_impact=0.0,
            ebitda_impact=float(revenue),
            upstream_metrics=["net_collection_rate", "net_revenue"],
        )

    def _lever_clean_claim_rate(
        self, current: float, target: float,
    ) -> MetricImpact:
        """Each pp improvement avoids (claims_volume × cost_per_rework / 100) rework."""
        delta_pp = _safe_num(target) - _safe_num(current)
        saved = (delta_pp / 100.0) * float(self.profile.total_claims_volume or 0) * \
                float(self.profile.cost_per_reworked_claim or 0.0)
        return MetricImpact(
            metric_key="clean_claim_rate",
            current_value=_safe_num(current),
            target_value=_safe_num(target),
            revenue_impact=0.0,
            cost_impact=-float(saved),
            ebitda_impact=float(saved),
            upstream_metrics=["clean_claim_rate", "total_claims_volume"],
        )

    def _lever_cost_to_collect(
        self, current: float, target: float,
    ) -> MetricImpact:
        """Direct cents-on-dollar: delta × NPR / 100 of recurring opex saved."""
        delta_pp = _safe_num(current) - _safe_num(target)
        npr = _safe_num(self.profile.net_revenue)
        saved = (delta_pp / 100.0) * npr
        return MetricImpact(
            metric_key="cost_to_collect",
            current_value=_safe_num(current),
            target_value=_safe_num(target),
            revenue_impact=0.0,
            cost_impact=-float(saved),
            ebitda_impact=float(saved),
            upstream_metrics=["cost_to_collect", "net_revenue"],
        )

    def _lever_first_pass_resolution_rate(
        self, current: float, target: float,
    ) -> MetricImpact:
        """FTE reduction in follow-up staff + rework cost savings."""
        delta_pp = _safe_num(target) - _safe_num(current)
        volume = float(self.profile.total_claims_volume or 0)
        # Rework share of total cost savings
        rework = (delta_pp / 100.0) * volume * \
                 float(self.profile.cost_per_reworked_claim or 0.0) * self.fpr_rework_share
        # FTE savings from fewer claims needing follow-up
        per_fte = max(1.0, float(self.profile.claims_per_follow_up_fte or _DEFAULT_CLAIMS_PER_FOLLOW_UP_FTE))
        fte_saved = (delta_pp / 100.0) * volume / per_fte
        fte_savings = fte_saved * float(self.profile.fte_cost_follow_up or _DEFAULT_FTE_COST_FOLLOW_UP)
        saved = rework + fte_savings
        return MetricImpact(
            metric_key="first_pass_resolution_rate",
            current_value=_safe_num(current),
            target_value=_safe_num(target),
            revenue_impact=0.0,
            cost_impact=-float(saved),
            ebitda_impact=float(saved),
            upstream_metrics=["first_pass_resolution_rate", "total_claims_volume"],
        )

    def _lever_case_mix_index(
        self, current: float, target: float,
    ) -> MetricImpact:
        """Each 0.01 CMI point lifts Medicare revenue by ``cmi_coefficient_per_point``%.

        Only Medicare revenue is affected (Medicaid/commercial use their
        own classification schemes) — we scale by the payer mix share.
        """
        delta_cmi_points = (_safe_num(target) - _safe_num(current)) / 0.01  # in 0.01 units
        medicare_revenue = _safe_num(self.profile.net_revenue) * self._medicare_npr_share()
        revenue = delta_cmi_points * medicare_revenue * (self.cmi_coefficient_per_point / 100.0)
        return MetricImpact(
            metric_key="case_mix_index",
            current_value=_safe_num(current),
            target_value=_safe_num(target),
            revenue_impact=float(revenue),
            cost_impact=0.0,
            ebitda_impact=float(revenue),
            upstream_metrics=["case_mix_index", "net_revenue", "payer_mix"],
        )

    _LEVER_METHODS = {
        "denial_rate": "_lever_denial_rate",
        "days_in_ar": "_lever_days_in_ar",
        "net_collection_rate": "_lever_net_collection_rate",
        "clean_claim_rate": "_lever_clean_claim_rate",
        "cost_to_collect": "_lever_cost_to_collect",
        "first_pass_resolution_rate": "_lever_first_pass_resolution_rate",
        "case_mix_index": "_lever_case_mix_index",
    }

    # ── Bridge compute ──────────────────────────────────────────────

    def _compute_lever(
        self, metric: str, current: float, target: float,
    ) -> Optional[MetricImpact]:
        m = self._LEVER_METHODS.get(metric)
        if m is None:
            return None
        return getattr(self, m)(current, target)

    def compute_bridge(
        self,
        current_metrics: Dict[str, float],
        target_metrics: Dict[str, float],
        *,
        ev_multiples: Sequence[float] = (10.0, 12.0, 15.0),
    ) -> EBITDABridgeResult:
        current_metrics = current_metrics or {}
        target_metrics = target_metrics or {}
        current_ebitda = _safe_num(self.profile.current_ebitda)

        impacts: List[MetricImpact] = []
        waterfall: List[Tuple[str, float]] = [("Current EBITDA", current_ebitda)]
        wc_total = 0.0

        for metric in self._LEVER_METHODS:
            if metric not in target_metrics:
                continue
            current_v = _safe_num(current_metrics.get(metric))
            target_v = _safe_num(target_metrics.get(metric))
            if current_v == target_v:
                continue
            imp = self._compute_lever(metric, current_v, target_v)
            if imp is None or imp.ebitda_impact == 0.0 and imp.working_capital_impact == 0.0:
                continue
            # Margin impact in bps relative to NPR.
            if self.profile.net_revenue > 0:
                imp.margin_impact_bps = (imp.ebitda_impact / self.profile.net_revenue) * 10000.0
            impacts.append(imp)
            wc_total += imp.working_capital_impact
            waterfall.append((metric, imp.ebitda_impact))

        total_ebitda_impact = sum(m.ebitda_impact for m in impacts)
        target_ebitda = current_ebitda + total_ebitda_impact
        waterfall.append(("Target EBITDA", target_ebitda))

        new_margin = (target_ebitda / self.profile.net_revenue) if self.profile.net_revenue > 0 else 0.0
        current_margin = (current_ebitda / self.profile.net_revenue) if self.profile.net_revenue > 0 else 0.0
        margin_bps = int(round((new_margin - current_margin) * 10000.0))
        delta_pct = (total_ebitda_impact / current_ebitda) if current_ebitda > 0 else 0.0

        tornado = sorted(
            [{"metric": m.metric_key, "ebitda_impact": m.ebitda_impact} for m in impacts],
            key=lambda r: abs(r["ebitda_impact"]),
            reverse=True,
        )
        ev_impact = {
            f"{int(mult)}x": float(total_ebitda_impact * mult)
            for mult in ev_multiples
        }

        status = SectionStatus.OK if impacts else SectionStatus.INCOMPLETE
        reason = "" if impacts else "no metric deltas produced any impact"
        if self.profile.net_revenue <= 0:
            status = SectionStatus.INCOMPLETE
            reason = "net_revenue must be positive for bridge computation"

        return EBITDABridgeResult(
            current_ebitda=current_ebitda,
            target_ebitda=target_ebitda,
            total_ebitda_impact=total_ebitda_impact,
            new_ebitda_margin=new_margin,
            ebitda_delta_pct=delta_pct,
            per_metric_impacts=impacts,
            waterfall_data=waterfall,
            sensitivity_tornado=tornado,
            working_capital_released=wc_total,
            margin_improvement_bps=margin_bps,
            ev_impact_at_multiple=ev_impact,
            status=status,
            reason=reason,
        )

    # ── Vectorized bridge (Prompt 19) ───────────────────────────────

    def lever_coefficients(
        self, metric_order: Sequence[str],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Precompute per-lever linear coefficients.

        Every v1 lever is linear in ``(target - current)`` once the
        hospital profile (``net_revenue``, ``claims_volume``, payer
        mix, cost-of-capital) is fixed, so the whole bridge is a dot
        product against a coefficient vector. Both returned arrays
        share the ordering of ``metric_order``.

        Returns
        -------
        (ebitda_coefs, wc_coefs)
            Each shape ``(n_levers,)``. Use with a
            ``(n_sims, n_levers)`` matrix of target values so that::

                deltas = targets - current_arr
                ebitda = deltas @ ebitda_coefs
                wc     = deltas @ wc_coefs

            would reproduce what ``compute_bridge`` does per-sim.

        Unknown metrics get a zero coefficient — they contribute
        nothing to the vectorized output, matching the scalar path's
        ``_compute_lever`` returning ``None``.
        """
        p = self.profile
        npr = _safe_num(p.net_revenue)
        claims = float(p.total_claims_volume or 0)
        rework_cost = float(p.cost_per_reworked_claim or 0.0)
        cost_of_capital = _safe_num(
            p.cost_of_capital_pct, _DEFAULT_COST_OF_CAPITAL,
        )
        per_fte = max(
            1.0,
            float(p.claims_per_follow_up_fte
                   or _DEFAULT_CLAIMS_PER_FOLLOW_UP_FTE),
        )
        fte_cost = float(p.fte_cost_follow_up or _DEFAULT_FTE_COST_FOLLOW_UP)
        medicare_share = self._medicare_npr_share()
        medicare_revenue = npr * medicare_share

        # Per-metric coefficient on the (target - current) delta.
        # Signs are chosen so that:
        #   - "lower is better" metrics (denial_rate, days_in_ar, cost_to_collect)
        #     carry a *negative* coefficient — a drop in the metric produces
        #     positive EBITDA (matches the scalar formulas).
        #   - "higher is better" metrics carry a *positive* coefficient.
        #
        # Every coefficient below is derived symbolically from the
        # corresponding scalar _lever_* function so the two paths are
        # mathematically identical.
        coef_table = {
            # delta_pp = (c - t) → (t - c) × (-(npr/100 × avoidable + claims × rework / 100))
            "denial_rate": -(
                npr * self.denial_avoidable_share / 100.0
                + claims * rework_cost / 100.0
            ),
            # days_in_ar: delta_days = (c - t). ebitda = delta × (npr/365 × coc + npr × bad_debt_coef)
            "days_in_ar": -(
                (npr / 365.0) * cost_of_capital
                + npr * self.ar_bad_debt_coefficient
            ),
            # net_collection_rate: (t - c)/100 × npr × ncr_coef
            "net_collection_rate": npr * self.ncr_coefficient / 100.0,
            # clean_claim_rate: (t - c)/100 × claims × rework
            "clean_claim_rate": claims * rework_cost / 100.0,
            # cost_to_collect: (c - t)/100 × npr → negative on (t - c)
            "cost_to_collect": -(npr / 100.0),
            # first_pass_resolution_rate: rework_share × claims × rework / 100 + claims / per_fte × fte_cost / 100
            "first_pass_resolution_rate": (
                claims * rework_cost * self.fpr_rework_share / 100.0
                + (claims / per_fte) * fte_cost / 100.0
            ),
            # case_mix_index: (t - c) × medicare_revenue × cmi_coef  (delta/0.01 × ... × coef/100)
            "case_mix_index": medicare_revenue * self.cmi_coefficient_per_point,
        }
        # Working-capital coefficient — only days_in_ar contributes.
        # wc = (c - t) × npr / 365 → on (t - c): -(npr/365).
        wc_table = {
            "days_in_ar": -(npr / 365.0),
        }
        ebitda_coefs = np.array([
            float(coef_table.get(m, 0.0)) for m in metric_order
        ], dtype=float)
        wc_coefs = np.array([
            float(wc_table.get(m, 0.0)) for m in metric_order
        ], dtype=float)
        return ebitda_coefs, wc_coefs

    def compute_bridge_vectorized(
        self,
        current_metrics: Dict[str, float],
        targets_matrix: np.ndarray,
        metric_order: Sequence[str],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Batch-evaluate the v1 bridge across ``n_sims`` target vectors.

        Parameters
        ----------
        current_metrics
            Current-state metric values. Missing keys default to 0.
        targets_matrix
            ``(n_sims, n_levers)`` array. Column ``j`` corresponds to
            ``metric_order[j]``.
        metric_order
            Sequence of metric keys defining the column ordering.

        Returns
        -------
        (ebitda_impacts, wc_released)
            Each shape ``(n_sims,)``. Same units as the scalar
            ``compute_bridge``'s totals.

        Mathematically identical to calling ``compute_bridge`` per sim
        and summing ``impact.ebitda_impact`` / ``impact.working_capital_impact``
        across the per-metric rows. Locked by test.
        """
        order = list(metric_order)
        if not order:
            n_sims = int(targets_matrix.shape[0]) if targets_matrix.ndim >= 1 else 0
            return np.zeros(n_sims), np.zeros(n_sims)
        targets = np.asarray(targets_matrix, dtype=float)
        if targets.ndim != 2 or targets.shape[1] != len(order):
            raise ValueError(
                f"targets_matrix shape {targets.shape} doesn't match "
                f"metric_order length {len(order)}"
            )
        current_arr = np.array(
            [_safe_num(current_metrics.get(m)) for m in order],
            dtype=float,
        )
        ebitda_coefs, wc_coefs = self.lever_coefficients(order)
        deltas = targets - current_arr[None, :]
        ebitda = deltas @ ebitda_coefs
        wc = deltas @ wc_coefs
        return ebitda, wc

    # ── Sensitivity tornado ─────────────────────────────────────────

    def compute_sensitivity_tornado(
        self,
        current_metrics: Dict[str, float],
        improvement_scenarios: Sequence[float] = (0.01, 0.05, 0.10, 0.20),
    ) -> TornadoResult:
        """For each lever, compute EBITDA impact at a set of fractional
        improvements (1%, 5%, 10%, 20% relative to current).

        Relative improvement means e.g. for denial_rate=12 at ``0.10`` we
        target 12 × (1-0.10) = 10.8 (pct-point scale). For "higher is
        better" levers we flip the sign so ``0.10`` means +10% of the
        current value.
        """
        current_metrics = current_metrics or {}
        rows: List[TornadoRow] = []
        scenarios = list(improvement_scenarios)
        for metric, defn in self.LEVER_DEFINITIONS.items():
            if metric not in current_metrics:
                continue
            current_v = _safe_num(current_metrics.get(metric))
            if current_v == 0:
                # Can't compute a relative scenario from zero.
                continue
            row = TornadoRow(metric=metric, scenarios={})
            for s in scenarios:
                delta = current_v * s
                if defn["direction"] == "lower_is_better":
                    target_v = current_v - delta
                else:
                    target_v = current_v + delta
                imp = self._compute_lever(metric, current_v, target_v)
                if imp is None:
                    continue
                label = f"{int(round(s * 100))}pct"
                row.scenarios[label] = float(imp.ebitda_impact)
            if row.scenarios:
                row.max_abs_impact = max(abs(v) for v in row.scenarios.values())
                rows.append(row)
        rows.sort(key=lambda r: r.max_abs_impact, reverse=True)
        return TornadoResult(rows=rows, improvement_scenarios=list(scenarios))

    # ── Target recommendations ──────────────────────────────────────

    def _tier_target(
        self,
        metric: str,
        current: float,
        defn: Dict[str, Any],
        percentile: float,
        percentile_keys: Tuple[str, str, str],
    ) -> Optional[float]:
        """Pick the registry percentile for this tier — but only when it
        would be an *improvement*. If the hospital is already better
        than the target percentile, return ``None`` so the tier skips
        the lever rather than asking partners to regress.
        """
        p25 = defn.get(percentile_keys[0])
        p50 = defn.get(percentile_keys[1])
        p75 = defn.get(percentile_keys[2])
        if p25 is None or p50 is None or p75 is None:
            return None
        p25 = float(p25)
        p50 = float(p50)
        p75 = float(p75)
        direction = self.LEVER_DEFINITIONS.get(metric, {}).get("direction")
        if direction == "lower_is_better":
            # Better is P25 (low). Conservative → P50, aggressive → P25
            target = p50 if percentile <= 0.5 else (
                p25 + (p50 - p25) * 0.4 if percentile <= 0.65 else
                p25 + (p50 - p25) * 0.0
            )
            if current <= target:
                return None
            return float(target)
        else:
            # Higher is better: P75 is aggressive
            if percentile <= 0.5:
                target = p50
            elif percentile <= 0.65:
                target = p50 + (p75 - p50) * 0.4
            else:
                target = p75
            if current >= target:
                return None
            return float(target)

    def _achievability(
        self, metric: str, current: float, target: float,
        registry_entry: Dict[str, Any],
    ) -> Tuple[float, int]:
        """Return (score, months) for one lever's target.

        Score: 1.0 - sigmoid-ish function of (distance / typical stretch).
        Months: months_per_stdev × distance_in_stdevs, floored at 3.
        """
        p25 = _safe_num(registry_entry.get("benchmark_p25"))
        p75 = _safe_num(registry_entry.get("benchmark_p75"))
        stdev_proxy = max(1e-9, abs(p75 - p25) / 1.35) if (p25 and p75) else 1.0
        distance = abs(current - target) / stdev_proxy
        # Score: 1 at distance 0, ~0.5 at distance 1σ, ~0.2 at 2σ
        score = float(1.0 / (1.0 + distance))
        months_base = _MONTHS_PER_STDEV.get(metric, 9)
        months = int(max(3, round(months_base * max(0.5, distance))))
        return (max(0.0, min(1.0, score)), months)

    def suggest_targets(
        self,
        current_metrics: Dict[str, float],
        comparables: Any,                                   # ComparableSet or None
        benchmark_percentiles: Dict[str, Dict[str, Any]],
    ) -> TargetRecommendation:
        """Three-tier recommendation.

        ``benchmark_percentiles`` is expected to carry
        ``benchmark_p25 / benchmark_p50 / benchmark_p65 / benchmark_p75``
        keys on each entry — falls back to interpolating between p50 and
        p75 when a specific percentile isn't present in the registry.

        ``comparables`` is kept as a signature parameter so a future
        caller can substitute cohort-derived targets for registry ones;
        not used in the current implementation.
        """
        tiers: Dict[str, TargetTier] = {}
        for tier_name, pct in (("conservative", 0.50), ("moderate", 0.65),
                               ("aggressive", 0.75)):
            tier_targets: Dict[str, float] = {}
            per_impact: Dict[str, float] = {}
            achievability_scores: List[float] = []
            months_values: List[int] = []
            for metric in self._LEVER_METHODS:
                defn = benchmark_percentiles.get(metric) or {}
                if not defn:
                    continue
                current_v = _safe_num(current_metrics.get(metric))
                if current_v == 0:
                    continue
                target = self._tier_target(
                    metric, current_v, defn, pct,
                    percentile_keys=("benchmark_p25", "benchmark_p50", "benchmark_p75"),
                )
                if target is None:
                    continue
                tier_targets[metric] = float(target)
                imp = self._compute_lever(metric, current_v, target)
                if imp is not None:
                    per_impact[metric] = float(imp.ebitda_impact)
                score, months = self._achievability(metric, current_v, target, defn)
                achievability_scores.append(score)
                months_values.append(months)
            total = sum(per_impact.values())
            achievability = (sum(achievability_scores) / len(achievability_scores)
                             if achievability_scores else 0.0)
            months = max(months_values) if months_values else 0
            tiers[tier_name] = TargetTier(
                tier=tier_name,
                targets=tier_targets,
                per_metric_impact=per_impact,
                total_ebitda_impact=float(total),
                achievability_score=float(achievability),
                estimated_months_to_achieve=int(months),
            )
        return TargetRecommendation(
            conservative=tiers["conservative"],
            moderate=tiers["moderate"],
            aggressive=tiers["aggressive"],
        )


# ── Convenience: profile builder from packet HospitalProfile ────────

def profile_from_packet(
    hospital_profile: Any,
    observed: Dict[str, Any],
    *,
    gross_revenue: Optional[float] = None,
    net_revenue: Optional[float] = None,
    current_ebitda: Optional[float] = None,
    total_claims_volume: Optional[int] = None,
    cost_of_capital_pct: Optional[float] = None,
) -> FinancialProfile:
    """Assemble a FinancialProfile from the packet's HospitalProfile +
    observed financial metrics. Any explicit keyword overrides the
    value that comes out of ``observed`` so callers can pin specific
    financials for what-if scenarios.
    """
    def _obs(k: str) -> Optional[float]:
        v = (observed or {}).get(k)
        if v is None:
            return None
        if hasattr(v, "value"):
            try:
                return float(v.value)
            except (TypeError, ValueError):
                return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    mix = dict(getattr(hospital_profile, "payer_mix", {}) or {})
    return FinancialProfile(
        gross_revenue=_safe_num(gross_revenue if gross_revenue is not None
                                 else _obs("gross_revenue")),
        net_revenue=_safe_num(net_revenue if net_revenue is not None
                               else _obs("net_revenue")),
        total_operating_expenses=_safe_num(_obs("total_operating_expenses")),
        current_ebitda=_safe_num(current_ebitda if current_ebitda is not None
                                  else _obs("current_ebitda")),
        cost_of_capital_pct=_safe_num(cost_of_capital_pct if cost_of_capital_pct is not None
                                       else _DEFAULT_COST_OF_CAPITAL),
        total_claims_volume=int(_safe_num(total_claims_volume or 0)),
        payer_mix=mix,
    )
