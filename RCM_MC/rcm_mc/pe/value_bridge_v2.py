"""RCM unit-economics EBITDA value bridge (v2).

Replaces the top-down coefficient bridge in ``rcm_ebitda_bridge.py``
with a transparent unit-economics model that:

- Starts from the *collectible* net revenue (Prompt 2's realization
  path) — not raw NPSR — so leakage already modeled doesn't double-count.
- Weights every lever by the hospital's payer mix AND reimbursement
  method mix, using the :data:`METHOD_SENSITIVITY_TABLE` from
  :mod:`rcm_mc.finance.reimbursement_engine`.
- Separates four distinct economic flavors per lever:
  recurring revenue uplift, recurring cost savings, one-time working
  capital release, and ongoing financing benefit (WC × cost-of-capital).
- Applies the exit multiple **only to recurring EBITDA**. One-time
  cash release is reported separately and never inflates enterprise
  value.

Why the v1 bridge stays in place: ``rcm_ebitda_bridge.py`` is
research-band-calibrated against the $400M NPR reference hospital and
30 regression tests lock it to those numbers. v2 is additive — run
both, compare, deprecate v1 when partners agree the v2 mechanics hold
up on real deals.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from ..finance.reimbursement_engine import (
    METHOD_SENSITIVITY_TABLE,
    PayerClass,
    ProvenanceTag,
    ReimbursementMethod,
    ReimbursementProfile,
)

logger = logging.getLogger(__name__)


# ── Tunable economic constants ──────────────────────────────────────

# Per-payer-class "revenue leverage" — how much a recovered denied
# claim is worth relative to a pure commercial contract. Commercial is
# the baseline 1.0; Medicare FFS pays less per unit so recovering a
# Medicare denial is worth less per-claim. This is what makes the same
# denial-rate improvement produce *different* dollar value under
# different payer mixes.
_PAYER_REVENUE_LEVERAGE: Dict[PayerClass, float] = {
    PayerClass.COMMERCIAL:          1.00,
    PayerClass.MEDICARE_FFS:        0.75,
    PayerClass.MEDICARE_ADVANTAGE:  0.80,
    PayerClass.MEDICAID:            0.50,
    PayerClass.SELF_PAY:            0.40,
    PayerClass.MANAGED_GOVERNMENT:  0.55,
}

# How much of a reduced denial rate actually flows into recovered
# revenue (vs. already-captured by appeals). 1 - (appeal_rate ×
# appeal_success_rate). Default 0.6 appeal × 0.65 success → 0.61
# recovery → 0.39 avoidable-share.
_DEFAULT_AVOIDABLE_SHARE = 0.39

# Baseline days in AR for computing the timing-drag delta. AR below
# this gets no additional financing benefit.
_BASELINE_AR_DAYS = 30.0

# Metrics considered "lower is better" for sign determination. Kept
# explicit rather than routed through the ontology so this module is
# self-contained and easy to audit.
_LOWER_IS_BETTER = frozenset({
    "denial_rate", "initial_denial_rate", "final_denial_rate",
    "days_in_ar", "ar_over_90_pct", "cost_to_collect",
    "discharged_not_final_billed_days", "coding_denial_rate",
    "auth_denial_rate", "eligibility_denial_rate",
    "timely_filing_denial_rate", "medical_necessity_denial_rate",
    "bad_debt",
})


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class BridgeAssumptions:
    """Explicit knobs the partner controls. No hidden constants."""
    exit_multiple: float = 10.0
    cost_of_capital: float = 0.08
    #: Share of collectible-net that realistically converts to cash once
    #: denials/appeals/write-offs are modeled. Tightens with better RCM
    #: ops; 0.65 is a conservative default.
    collection_realization: float = 0.65
    #: Probability that an appealed denial ultimately pays. Partners
    #: adjust based on known appeal success by payer.
    denial_overturn_rate: float = 0.55
    rework_cost_per_claim: float = 30.0
    cost_per_follow_up_fte: float = 55_000.0
    claims_per_follow_up_fte: int = 10_000
    #: Implementation ramp — 1.0 = fully ramped in year 1; 0.5 = half
    #: effect in year 1. Scales all recurring outputs proportionally.
    implementation_ramp: float = 1.0
    #: Confidence penalty per inferred assumption. Applied to the
    #: per-lever ``confidence`` score.
    confidence_inference_penalty: float = 0.15
    #: When the caller explicitly supplies a ``claims_volume`` and
    #: ``net_revenue`` it's observed; otherwise the bridge backs into
    #: these from the realization path and tags them inferred.
    claims_volume: int = 0
    net_revenue: float = 0.0
    #: Optional per-payer override of the module-level
    #: ``_PAYER_REVENUE_LEVERAGE`` table. Keyed either by
    #: :class:`PayerClass` enum or its ``.value`` string. Used by the
    #: v2 Monte Carlo (Prompt 16) to sample leverage uncertainty
    #: per-simulation without patching module-level state. ``None`` →
    #: use the module default.
    payer_revenue_leverage: Optional[Dict[Any, float]] = None
    #: Per-lever-family implementation ramp curves (Prompt 17). ``None``
    #: → use :data:`rcm_mc.pe.ramp_curves.DEFAULT_RAMP_CURVES`. Accepts
    #: either :class:`~rcm_mc.pe.ramp_curves.RampCurve` instances or
    #: their ``.to_dict()`` form so deserialized assumptions still
    #: round-trip.
    ramp_curves: Optional[Dict[str, Any]] = None
    #: Month at which the bridge is evaluated. Month 36 is the "full
    #: run-rate" steady state — the old default behavior. Drop to 12
    #: for a Year-1 bridge, 24 for a Year-2 bridge. The v2 Monte Carlo
    #: passes a sampled hold_months in per-sim.
    evaluation_month: int = 36

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        # payer_revenue_leverage may be keyed by PayerClass enum — JSON
        # only accepts string keys. Normalize to the enum's ``.value``.
        prl = self.payer_revenue_leverage
        if prl:
            out["payer_revenue_leverage"] = {
                (k.value if hasattr(k, "value") else str(k)): float(v)
                for k, v in prl.items()
            }
        # ramp_curves may hold RampCurve instances; serialize via
        # their to_dict so asdict's recursive walk doesn't hit the
        # frozen dataclass at the wrong time.
        rc = self.ramp_curves
        if rc:
            out["ramp_curves"] = {
                k: (v.to_dict() if hasattr(v, "to_dict") else dict(v))
                for k, v in rc.items()
            }
        return out


@dataclass
class WorkingCapitalEffect:
    """Cash released (or tied up) by a timing-oriented lever."""
    days_change: float = 0.0
    cash_release_one_time: float = 0.0
    financing_benefit_annual: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RevenueLeakageBreakdown:
    """Per-lever view of how much revenue leakage the change closes."""
    stage: str
    baseline_leakage: float = 0.0
    target_leakage: float = 0.0
    recovered: float = 0.0
    recovery_confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeverImpact:
    """Four-flavor economic decomposition for one RCM metric lever.

    ``recurring_ebitda_delta`` = ``recurring_revenue_uplift`` +
    ``recurring_cost_savings`` + ``ongoing_financing_benefit``. The
    one-time WC release is intentionally excluded from
    ``recurring_ebitda_delta`` and from EV translation.
    """
    metric_key: str
    current_value: float
    target_value: float
    recurring_revenue_uplift: float = 0.0
    recurring_cost_savings: float = 0.0
    one_time_working_capital_release: float = 0.0
    ongoing_financing_benefit: float = 0.0
    recurring_ebitda_delta: float = 0.0
    revenue_leakage: Optional[RevenueLeakageBreakdown] = None
    working_capital: Optional[WorkingCapitalEffect] = None
    explanation: str = ""
    confidence: float = 0.5
    pathway_tags: List[str] = field(default_factory=list)
    provenance: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "current_value": float(self.current_value),
            "target_value": float(self.target_value),
            "recurring_revenue_uplift": float(self.recurring_revenue_uplift),
            "recurring_cost_savings": float(self.recurring_cost_savings),
            "one_time_working_capital_release": float(self.one_time_working_capital_release),
            "ongoing_financing_benefit": float(self.ongoing_financing_benefit),
            "recurring_ebitda_delta": float(self.recurring_ebitda_delta),
            "revenue_leakage": (self.revenue_leakage.to_dict()
                                 if self.revenue_leakage else None),
            "working_capital": (self.working_capital.to_dict()
                                 if self.working_capital else None),
            "explanation": self.explanation,
            "confidence": float(self.confidence),
            "pathway_tags": list(self.pathway_tags),
            "provenance": dict(self.provenance),
        }


@dataclass
class EbitdaBridgeComponent:
    """One row in the final waterfall."""
    label: str
    value: float
    kind: str                      # revenue | cost | working_capital | financing | anchor
    source_metric: Optional[str] = None
    provenance: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValueBridgeResult:
    assumptions: BridgeAssumptions = field(default_factory=BridgeAssumptions)
    lever_impacts: List[LeverImpact] = field(default_factory=list)
    current_ebitda: float = 0.0
    target_recurring_ebitda: float = 0.0
    total_recurring_revenue_uplift: float = 0.0
    total_recurring_cost_savings: float = 0.0
    total_one_time_wc_release: float = 0.0
    total_financing_benefit: float = 0.0
    total_recurring_ebitda_delta: float = 0.0
    enterprise_value_delta: float = 0.0
    enterprise_value_from_recurring: float = 0.0
    cash_release_excluded_from_ev: float = 0.0
    bridge_components: List[EbitdaBridgeComponent] = field(default_factory=list)
    #: Per-lever adjustments applied by the cross-lever dependency
    #: walker (Prompt 15). Each row records which upstream levers
    #: caused the adjustment and by how much. Empty list means every
    #: lever was independent of the others.
    dependency_audit: List[Any] = field(default_factory=list)
    #: Raw totals *before* dependency adjustment. Kept so renderers
    #: can show "naive vs adjusted" side by side without recomputing.
    raw_total_recurring_ebitda_delta: float = 0.0
    raw_total_recurring_revenue_uplift: float = 0.0
    #: ``True`` when per-lever ramp curves actually scaled anything
    #: (i.e., evaluation_month < max months_to_full across fired
    #: levers). Stays ``False`` at the default full-run-rate month 36.
    ramp_applied: bool = False
    #: Per-lever ramp multiplier actually applied during this bridge
    #: call, keyed by metric_key. Always populated — at full run-rate
    #: every value is 1.0.
    per_lever_ramp_factors: Dict[str, float] = field(default_factory=dict)
    rationale: str = ""
    status: str = "OK"
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assumptions": self.assumptions.to_dict(),
            "lever_impacts": [li.to_dict() for li in self.lever_impacts],
            "current_ebitda": float(self.current_ebitda),
            "target_recurring_ebitda": float(self.target_recurring_ebitda),
            "total_recurring_revenue_uplift": float(self.total_recurring_revenue_uplift),
            "total_recurring_cost_savings": float(self.total_recurring_cost_savings),
            "total_one_time_wc_release": float(self.total_one_time_wc_release),
            "total_financing_benefit": float(self.total_financing_benefit),
            "total_recurring_ebitda_delta": float(self.total_recurring_ebitda_delta),
            "enterprise_value_delta": float(self.enterprise_value_delta),
            "enterprise_value_from_recurring": float(self.enterprise_value_from_recurring),
            "cash_release_excluded_from_ev": float(self.cash_release_excluded_from_ev),
            "bridge_components": [c.to_dict() for c in self.bridge_components],
            "dependency_audit": [
                (row.to_dict() if hasattr(row, "to_dict") else dict(row))
                for row in self.dependency_audit
            ],
            "raw_total_recurring_ebitda_delta": float(self.raw_total_recurring_ebitda_delta),
            "raw_total_recurring_revenue_uplift": float(self.raw_total_recurring_revenue_uplift),
            "ramp_applied": bool(self.ramp_applied),
            "per_lever_ramp_factors": {
                k: float(v) for k, v in self.per_lever_ramp_factors.items()
            },
            "rationale": self.rationale,
            "status": self.status,
            "reason": self.reason,
        }


# ── Helpers: reimbursement-weighted sensitivities ──────────────────

def _payer_method_sensitivity(
    pcp_method_distribution: Dict[ReimbursementMethod, float],
    fields: List[str],
) -> float:
    """Weighted avg of the named sensitivity fields across a payer
    class's method distribution."""
    acc = 0.0
    total = 0.0
    for method, share in pcp_method_distribution.items():
        entry = METHOD_SENSITIVITY_TABLE.get(method)
        if entry is None or share <= 0:
            continue
        vals = [float(getattr(entry, f, 0.0)) for f in fields]
        if not vals:
            continue
        acc += share * (sum(vals) / len(vals))
        total += share
    return acc / total if total > 0 else 0.0


def _coding_sensitivity(
    pcp_method_distribution: Dict[ReimbursementMethod, float],
) -> float:
    return _payer_method_sensitivity(
        pcp_method_distribution, ["coding_cdi_acuity"],
    )


def _front_end_sensitivity(
    pcp_method_distribution: Dict[ReimbursementMethod, float],
) -> float:
    return _payer_method_sensitivity(
        pcp_method_distribution,
        ["auth_denials", "eligibility_denials"],
    )


def _medical_necessity_sensitivity(
    pcp_method_distribution: Dict[ReimbursementMethod, float],
) -> float:
    return _payer_method_sensitivity(
        pcp_method_distribution, ["medical_necessity"],
    )


def _timely_sensitivity(
    pcp_method_distribution: Dict[ReimbursementMethod, float],
) -> float:
    return _payer_method_sensitivity(
        pcp_method_distribution, ["timely_filing"],
    )


# ── Revenue-recovery backbone ──────────────────────────────────────

def _get_payer_leverage(
    pc: PayerClass,
    override: Optional[Dict[Any, float]],
) -> float:
    """Return the dollar-per-recovered-claim leverage for payer ``pc``.

    If ``override`` is provided (from ``BridgeAssumptions.payer_revenue_leverage``),
    its value wins over the module-level ``_PAYER_REVENUE_LEVERAGE``
    table. The override may be keyed either by the enum itself or by
    ``pc.value`` so the v2 Monte Carlo can drop in a sampled dict
    without worrying about key shape.
    """
    if override:
        if pc in override:
            return float(override[pc])
        key = getattr(pc, "value", None)
        if key is not None and key in override:
            return float(override[key])
    return _PAYER_REVENUE_LEVERAGE.get(pc, 0.7)


def _per_payer_revenue_recovery(
    profile: ReimbursementProfile,
    net_revenue: float,
    delta_fraction: float,
    *,
    sensitivity_fields: List[str],
    avoidable_share: float,
    assumptions: Optional[BridgeAssumptions] = None,
) -> float:
    """Core revenue-recovery formula used by all denial-style levers.

    For each payer class:
        payer_nr      = net_revenue × payer.revenue_share
        sensitivity   = weighted sensitivity of that payer's methods
        leverage      = per-payer $-per-recovered-claim leverage
        recovered_rev = payer_nr × delta × sensitivity × leverage × avoidable_share

    Commercial mixes produce more revenue per point of denial reduction
    than Medicare FFS or Medicaid, by design.

    ``assumptions`` is optional so direct callers from tests still work;
    when present, ``assumptions.payer_revenue_leverage`` overrides the
    module default per-payer. The v2 Monte Carlo uses this to sample
    leverage uncertainty.
    """
    if net_revenue <= 0 or delta_fraction == 0 or not profile.payer_classes:
        return 0.0
    override = assumptions.payer_revenue_leverage if assumptions else None
    acc = 0.0
    for pc, pcp in profile.payer_classes.items():
        payer_nr = net_revenue * pcp.revenue_share
        sensitivity = _payer_method_sensitivity(
            pcp.method_distribution, sensitivity_fields,
        )
        leverage = _get_payer_leverage(pc, override)
        acc += payer_nr * delta_fraction * sensitivity * leverage * avoidable_share
    return acc


def _realization_base(
    reimbursement_profile: ReimbursementProfile,
    realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> Tuple[float, float, int, str]:
    """Return (net_revenue, collectible_revenue, claims_volume,
    provenance_tag).

    Preference order for net_revenue:
    1. ``assumptions.net_revenue`` (observed)
    2. ``realization.gross_charges - contractual_adjustments``
    3. 0.0 (caller gets a status=INCOMPLETE result)

    For claims_volume, we use assumptions.claims_volume when >0;
    otherwise try to infer from collectible_revenue / avg-claim-dollars
    using a $1,500 default claim size (tagged inferred).
    """
    if realization is None:
        realization = {}
    gross = float(realization.get("gross_charges") or 0.0)
    contractual = float(realization.get("contractual_adjustments") or 0.0)
    collectible = float(realization.get("collectible_net_revenue") or 0.0)

    if assumptions.net_revenue > 0:
        net_rev = assumptions.net_revenue
        tag = ProvenanceTag.OBSERVED.value
    elif gross > 0 and contractual >= 0:
        net_rev = max(0.0, gross - contractual)
        tag = ProvenanceTag.CALCULATED.value
    elif collectible > 0:
        net_rev = collectible
        tag = ProvenanceTag.CALCULATED.value
    else:
        return (0.0, 0.0, 0, ProvenanceTag.BENCHMARK_DEFAULT.value)

    collectible = collectible if collectible > 0 else net_rev * 0.95

    claims = assumptions.claims_volume if assumptions.claims_volume > 0 else 0
    if claims <= 0:
        # Assume $1,500 average collectible per claim as a partner-
        # defensible inference. Real deals should override.
        claims = int(collectible / 1500.0) if collectible > 0 else 0

    return (net_rev, collectible, claims, tag)


# ── Per-lever formulas ──────────────────────────────────────────────

def _delta(metric_key: str, current: float, target: float) -> float:
    """Positive delta = improvement, regardless of direction."""
    if metric_key in _LOWER_IS_BETTER:
        return current - target
    return target - current


def _lever_denial_rate(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """Generic denial-rate lever. Operates on initial_denial_rate,
    denial_rate, or any of the categorical denial_rate_* siblings.

    Route economic impact:
    - Preventable front-end denials → revenue recovery (method × payer)
    - Fewer reworks → cost savings (claims_volume × delta)
    - Slightly less AR timing tail → tiny WC benefit (not material
      enough to model explicitly at this level)
    """
    delta_pp = _delta(metric_key, current, target)
    net_rev, collectible, claims, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or delta_pp == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")

    delta_frac = delta_pp / 100.0

    # Determine sensitivity fields based on metric specificity.
    if metric_key == "coding_denial_rate":
        fields = ["coding_cdi_acuity"]
    elif metric_key == "auth_denial_rate":
        fields = ["auth_denials"]
    elif metric_key == "eligibility_denial_rate":
        fields = ["eligibility_denials"]
    elif metric_key == "medical_necessity_denial_rate":
        fields = ["medical_necessity"]
    elif metric_key == "timely_filing_denial_rate":
        fields = ["timely_filing"]
    elif metric_key == "final_denial_rate":
        # Final denials are permanent write-offs; 100% recovery is
        # revenue-only and avoidable-share is effectively 1.0.
        fields = ["auth_denials", "medical_necessity"]
    else:   # denial_rate / initial_denial_rate
        fields = ["auth_denials", "eligibility_denials", "coding_cdi_acuity"]

    avoidable = 1.0 if metric_key == "final_denial_rate" else _DEFAULT_AVOIDABLE_SHARE

    revenue_uplift = _per_payer_revenue_recovery(
        profile, net_rev, delta_frac,
        sensitivity_fields=fields, avoidable_share=avoidable,
        assumptions=assumptions,
    )

    # Rework cost savings — only for first-pass / initial denials,
    # not for final (by the time we hit final the rework is sunk).
    cost_saving = 0.0
    if metric_key in ("denial_rate", "initial_denial_rate",
                       "coding_denial_rate", "auth_denial_rate",
                       "eligibility_denial_rate",
                       "medical_necessity_denial_rate"):
        cost_saving = (
            delta_frac * float(claims) * assumptions.rework_cost_per_claim
        )

    # Apply implementation ramp to both recurring flows.
    revenue_uplift *= assumptions.implementation_ramp
    cost_saving *= assumptions.implementation_ramp

    leakage = RevenueLeakageBreakdown(
        stage=("final_denial" if metric_key == "final_denial_rate"
               else "initial_denial"),
        baseline_leakage=float(net_rev * (current / 100.0) * avoidable),
        target_leakage=float(net_rev * (target / 100.0) * avoidable),
        recovered=float(revenue_uplift),
        recovery_confidence=_overall_confidence(profile, assumptions),
    )

    impact = LeverImpact(
        metric_key=metric_key,
        current_value=current, target_value=target,
        recurring_revenue_uplift=revenue_uplift,
        recurring_cost_savings=cost_saving,
        one_time_working_capital_release=0.0,
        ongoing_financing_benefit=0.0,
        recurring_ebitda_delta=revenue_uplift + cost_saving,
        revenue_leakage=leakage,
        pathway_tags=["revenue", "cost"] if cost_saving else ["revenue"],
        confidence=_overall_confidence(profile, assumptions),
        provenance={
            "revenue_base": base_tag,
            "claims_volume": (ProvenanceTag.OBSERVED.value
                              if assumptions.claims_volume > 0
                              else ProvenanceTag.INFERRED_FROM_PROFILE.value),
            "method_sensitivity": ProvenanceTag.CALCULATED.value,
            "payer_revenue_leverage": ProvenanceTag.BENCHMARK_DEFAULT.value,
        },
    )
    impact.explanation = _lever_narrative(impact, profile)
    return impact


def _lever_clean_claim_rate(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """Clean claim rate: primary pathway is rework cost savings, with
    a small revenue recovery tail."""
    delta_pp = _delta(metric_key, current, target)
    net_rev, collectible, claims, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or delta_pp == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")
    delta_frac = delta_pp / 100.0
    # Each pp of clean claim improvement saves approximately that pct
    # of claims × rework cost.
    cost_saving = delta_frac * float(claims) * assumptions.rework_cost_per_claim
    # A small share converts to recovered revenue via fewer downstream
    # denials. ~15% of the lever lands here.
    rev = 0.15 * _per_payer_revenue_recovery(
        profile, net_rev, delta_frac,
        sensitivity_fields=["eligibility_denials", "coding_cdi_acuity"],
        avoidable_share=_DEFAULT_AVOIDABLE_SHARE,
        assumptions=assumptions,
    )
    cost_saving *= assumptions.implementation_ramp
    rev *= assumptions.implementation_ramp

    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_revenue_uplift=rev,
        recurring_cost_savings=cost_saving,
        recurring_ebitda_delta=rev + cost_saving,
        pathway_tags=["cost", "revenue"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"Clean claim rate {current}→{target}%: "
            f"primarily rework-cost savings "
            f"({cost_saving:,.0f}) with smaller revenue-recovery tail "
            f"({rev:,.0f})."
        ),
        provenance={"revenue_base": base_tag,
                     "claims_volume": (ProvenanceTag.OBSERVED.value
                                        if assumptions.claims_volume > 0
                                        else ProvenanceTag.INFERRED_FROM_PROFILE.value),
                     "method_sensitivity": ProvenanceTag.CALCULATED.value},
    )


def _lever_first_pass_resolution_rate(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """First-pass resolution: reduces follow-up FTE need + rework."""
    delta_pp = _delta(metric_key, current, target)
    net_rev, collectible, claims, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or delta_pp == 0 or claims <= 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline or zero claims"
                              if net_rev <= 0 else "no delta")
    delta_frac = delta_pp / 100.0
    # FTE reduction — claims no longer needing follow-up.
    freed_claims = delta_frac * float(claims)
    ftes_freed = freed_claims / max(1, assumptions.claims_per_follow_up_fte)
    cost_saving = ftes_freed * assumptions.cost_per_follow_up_fte
    # Plus rework avoidance
    rework_saving = (
        0.30 * delta_frac * float(claims) * assumptions.rework_cost_per_claim
    )
    total_cost = (cost_saving + rework_saving) * assumptions.implementation_ramp
    # Light revenue tail via fewer denials crystallizing
    rev = 0.10 * _per_payer_revenue_recovery(
        profile, net_rev, delta_frac,
        sensitivity_fields=["auth_denials", "eligibility_denials"],
        avoidable_share=_DEFAULT_AVOIDABLE_SHARE,
        assumptions=assumptions,
    ) * assumptions.implementation_ramp
    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_cost_savings=total_cost,
        recurring_revenue_uplift=rev,
        recurring_ebitda_delta=total_cost + rev,
        pathway_tags=["cost", "revenue"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"First-pass resolution {current}→{target}%: "
            f"frees ~{ftes_freed:.1f} follow-up FTE plus rework savings."
        ),
        provenance={"revenue_base": base_tag,
                     "claims_volume": (ProvenanceTag.OBSERVED.value
                                        if assumptions.claims_volume > 0
                                        else ProvenanceTag.INFERRED_FROM_PROFILE.value),
                     "fte_assumption": ProvenanceTag.BENCHMARK_DEFAULT.value},
    )


def _lever_days_in_ar(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """AR-days reduction: one-time WC release + recurring financing
    benefit. *Not* a recurring revenue lift — the money was always
    going to land, it just lands sooner now.

    Capitated exposure should lower the working-capital benefit (the
    money is prepaid). We weight the release by the share of method
    mix with ``gain_pathway == working_capital``-sensitive timing —
    FFS/DRG/APC/per_diem/bundled/value_based. Capitation and cost-based
    receive partial weight.
    """
    days_delta = _delta(metric_key, current, target)   # positive = improvement
    net_rev, collectible, claims, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or days_delta == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")

    # Weight by method sensitivity to timely filing / cash timing.
    # Capitation has ~20-day DSO and very low sensitivity — a day of
    # AR improvement there is worth much less.
    timing_weight = _timing_weight(profile)
    per_day_cash = (net_rev / 365.0) * timing_weight
    wc_release = days_delta * per_day_cash
    financing = wc_release * assumptions.cost_of_capital * assumptions.implementation_ramp

    # Small recurring revenue effect from bad-debt avoidance on
    # receivables that would otherwise age past collection windows.
    rev = (
        days_delta * (net_rev / 365.0) * 0.002   # ~0.2% of daily NPR per day
        * assumptions.implementation_ramp
    )

    wc_effect = WorkingCapitalEffect(
        days_change=days_delta,
        cash_release_one_time=wc_release,
        financing_benefit_annual=financing,
    )

    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_revenue_uplift=rev,
        recurring_cost_savings=0.0,
        one_time_working_capital_release=wc_release,
        ongoing_financing_benefit=financing,
        recurring_ebitda_delta=rev + financing,
        working_capital=wc_effect,
        pathway_tags=["working_capital", "financing"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"Days in AR {current}→{target}: ~{days_delta:.0f} days faster "
            f"cash cycle releases {wc_release:,.0f} one-time and "
            f"{financing:,.0f}/yr financing benefit. Recurring EBITDA "
            f"effect is small; the headline is cash timing, not margin."
        ),
        provenance={"revenue_base": base_tag,
                     "timing_weight": ProvenanceTag.CALCULATED.value,
                     "cost_of_capital": ProvenanceTag.BENCHMARK_DEFAULT.value},
    )


def _timing_weight(profile: ReimbursementProfile) -> float:
    """How much a hospital's method mix exposes it to AR timing.

    Capitation and cost-based reimbursement are weakly timing-sensitive.
    FFS / DRG / APC / per-diem / bundled / VBP are strongly timing-
    sensitive. Returns a weight in [0, 1].
    """
    low_sensitivity = {ReimbursementMethod.CAPITATION: 0.2,
                        ReimbursementMethod.COST_BASED: 0.6}
    weight = 0.0
    total = 0.0
    for method, share in profile.method_weights.items():
        total += share
        w = low_sensitivity.get(method, 1.0)
        weight += share * w
    return weight / total if total > 0 else 1.0


def _lever_ar_over_90_pct(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """Aged A/R concentration — mostly a write-off leading indicator,
    so the lever is partly revenue recovery (prevented write-offs) and
    partly working capital timing."""
    delta_pp = _delta(metric_key, current, target)
    net_rev, collectible, _, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or delta_pp == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")
    delta_frac = delta_pp / 100.0
    # Revenue recovery: 50% of the prevented aging converts to
    # collected revenue (the rest was going to collect anyway).
    rev = net_rev * delta_frac * 0.15 * assumptions.implementation_ramp
    # Plus a modest WC release — aged AR tied up cash.
    wc_release = net_rev * delta_frac * 0.08
    financing = wc_release * assumptions.cost_of_capital * assumptions.implementation_ramp
    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_revenue_uplift=rev,
        one_time_working_capital_release=wc_release,
        ongoing_financing_benefit=financing,
        recurring_ebitda_delta=rev + financing,
        working_capital=WorkingCapitalEffect(
            days_change=0.0, cash_release_one_time=wc_release,
            financing_benefit_annual=financing,
        ),
        pathway_tags=["revenue", "working_capital"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"Aged A/R > 90d {current}→{target}%: prevents write-offs "
            f"(≈{rev:,.0f} revenue recovery) and releases "
            f"{wc_release:,.0f} of working capital."
        ),
        provenance={"revenue_base": base_tag,
                     "aging_conversion": ProvenanceTag.BENCHMARK_DEFAULT.value},
    )


def _lever_net_collection_rate(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """Pure revenue realization — every percentage point on NCR is
    nearly pure EBITDA."""
    delta_pp = _delta(metric_key, current, target)
    net_rev, collectible, _, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or delta_pp == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")
    delta_frac = delta_pp / 100.0
    # Revenue recovery is method-weighted: FFS/DRG book the gain; a
    # purely capitated hospital sees very little NCR lift because the
    # revenue is capped by PMPM.
    ncr_sensitivity = _payer_method_sensitivity(
        profile.method_weights if isinstance(profile.method_weights, dict) else {},
        ["timely_filing", "auth_denials"],
    )
    # Fall back to a partner-defensible baseline if method_weights
    # is empty or the sensitivity collapses.
    if ncr_sensitivity <= 0:
        ncr_sensitivity = 0.6
    rev = net_rev * delta_frac * ncr_sensitivity * assumptions.implementation_ramp
    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_revenue_uplift=rev,
        recurring_ebitda_delta=rev,
        pathway_tags=["revenue"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"Net collection rate {current}→{target}%: direct revenue "
            f"realization of {rev:,.0f}/yr. Method sensitivity: "
            f"{ncr_sensitivity:.2f}."
        ),
        provenance={"revenue_base": base_tag,
                     "method_sensitivity": ProvenanceTag.CALCULATED.value},
    )


def _lever_cost_to_collect(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    delta_pp = _delta(metric_key, current, target)
    net_rev, _, _, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or delta_pp == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")
    delta_frac = delta_pp / 100.0
    # Direct opex reduction.
    cost_save = net_rev * delta_frac * assumptions.implementation_ramp
    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_cost_savings=cost_save,
        recurring_ebitda_delta=cost_save,
        pathway_tags=["cost"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"Cost to collect {current}→{target}%: direct RCM opex "
            f"savings of {cost_save:,.0f}/yr."
        ),
        provenance={"revenue_base": base_tag},
    )


def _lever_dnfb(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """Pure timing lever: DNFB days feed AR days. Working-capital only."""
    days_delta = _delta(metric_key, current, target)
    net_rev, _, _, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or days_delta == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")
    timing_weight = _timing_weight(profile)
    wc_release = days_delta * (net_rev / 365.0) * timing_weight
    financing = wc_release * assumptions.cost_of_capital * assumptions.implementation_ramp
    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        one_time_working_capital_release=wc_release,
        ongoing_financing_benefit=financing,
        recurring_ebitda_delta=financing,
        working_capital=WorkingCapitalEffect(
            days_change=days_delta, cash_release_one_time=wc_release,
            financing_benefit_annual=financing,
        ),
        pathway_tags=["working_capital"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"DNFB {current}→{target}d: accelerates cash cycle — "
            f"{wc_release:,.0f} one-time release, {financing:,.0f}/yr."
        ),
        provenance={"revenue_base": base_tag,
                     "timing_weight": ProvenanceTag.CALCULATED.value},
    )


def _lever_cmi(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """Case Mix Index — revenue uplift concentrated on the DRG-exposed
    payer mix share. Capitation contributes minimally (HCC coding
    matters but we don't model it here)."""
    delta_points = _delta(metric_key, current, target)  # in raw CMI units
    net_rev, _, _, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or delta_points == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")
    # DRG-exposed share = share of method mix that's DRG-prospective.
    drg_share = float(profile.method_weights.get(
        ReimbursementMethod.DRG_PROSPECTIVE, 0.0,
    ))
    # Plus a small contribution from APC (OPPS uses APCs, which have
    # their own acuity / packaging sensitivity).
    apc_share = float(profile.method_weights.get(
        ReimbursementMethod.OUTPATIENT_APC, 0.0,
    ))
    effective_share = drg_share + 0.3 * apc_share
    # Each 0.01 CMI point ≈ 0.75% of the DRG-exposed revenue.
    delta_x100 = delta_points / 0.01
    rev = (net_rev * effective_share
           * delta_x100 * (0.0075)
           * assumptions.implementation_ramp)
    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_revenue_uplift=rev,
        recurring_ebitda_delta=rev,
        pathway_tags=["revenue"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"CMI {current:.2f}→{target:.2f}: uplift on DRG-exposed "
            f"share ({effective_share*100:.0f}% of mix). Revenue "
            f"recovery {rev:,.0f}/yr."
        ),
        provenance={"revenue_base": base_tag,
                     "drg_share": ProvenanceTag.CALCULATED.value,
                     "cmi_coefficient": ProvenanceTag.BENCHMARK_DEFAULT.value},
    )


def _lever_bad_debt(
    metric_key: str, current: float, target: float,
    profile: ReimbursementProfile, realization: Optional[Dict[str, Any]],
    assumptions: BridgeAssumptions,
) -> LeverImpact:
    """Bad debt — cost save amplified by self-pay exposure."""
    delta_pp = _delta(metric_key, current, target)
    net_rev, _, _, base_tag = _realization_base(
        profile, realization, assumptions,
    )
    if net_rev <= 0 or delta_pp == 0:
        return _empty_impact(metric_key, current, target,
                              "no revenue baseline" if net_rev <= 0 else "no delta")
    delta_frac = delta_pp / 100.0
    # Amplifier by self-pay share — self-pay-heavy hospitals get more
    # out of each pp of bad-debt reduction.
    self_pay_share = 0.0
    if PayerClass.SELF_PAY in profile.payer_classes:
        self_pay_share = profile.payer_classes[PayerClass.SELF_PAY].revenue_share
    medicaid_share = 0.0
    if PayerClass.MEDICAID in profile.payer_classes:
        medicaid_share = profile.payer_classes[PayerClass.MEDICAID].revenue_share
    amplifier = 1.0 + 1.5 * self_pay_share + 0.8 * medicaid_share
    cost_save = net_rev * delta_frac * amplifier * assumptions.implementation_ramp
    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_cost_savings=cost_save,
        recurring_ebitda_delta=cost_save,
        pathway_tags=["cost"],
        confidence=_overall_confidence(profile, assumptions),
        explanation=(
            f"Bad debt {current}→{target}%: "
            f"amplifier {amplifier:.2f}× from self-pay "
            f"({self_pay_share*100:.0f}%) and Medicaid "
            f"({medicaid_share*100:.0f}%) exposure. "
            f"Recurring cost savings {cost_save:,.0f}/yr."
        ),
        provenance={"revenue_base": base_tag,
                     "self_pay_amplifier": ProvenanceTag.CALCULATED.value},
    )


# ── Shared utilities ────────────────────────────────────────────────

def _empty_impact(
    metric_key: str, current: float, target: float, reason: str,
) -> LeverImpact:
    return LeverImpact(
        metric_key=metric_key, current_value=current, target_value=target,
        recurring_revenue_uplift=0.0, recurring_cost_savings=0.0,
        one_time_working_capital_release=0.0, ongoing_financing_benefit=0.0,
        recurring_ebitda_delta=0.0,
        explanation=f"no impact modeled: {reason}",
        confidence=0.0,
        provenance={"status": ProvenanceTag.CALCULATED.value},
    )


def _overall_confidence(
    profile: ReimbursementProfile, assumptions: BridgeAssumptions,
) -> float:
    """Baseline ~0.80, minus a penalty for every inferred method
    distribution, clamped to [0, 1]."""
    if not profile.payer_classes:
        return 0.3
    n_inferred = sum(
        1 for pcp in profile.payer_classes.values()
        if pcp.provenance.get("method_distribution") in (
            ProvenanceTag.BENCHMARK_DEFAULT.value,
            ProvenanceTag.INFERRED_FROM_PROFILE.value,
        )
    )
    n_total = max(1, len(profile.payer_classes))
    penalty = (n_inferred / n_total) * assumptions.confidence_inference_penalty * 3
    return max(0.0, min(1.0, 0.85 - penalty))


def _lever_narrative(
    impact: LeverImpact, profile: ReimbursementProfile,
) -> str:
    top_methods = sorted(
        profile.method_weights.items(), key=lambda t: t[1], reverse=True,
    )[:2]
    methods = ", ".join(
        f"{m.value.replace('_', ' ')} ({w*100:.0f}%)"
        for m, w in top_methods
    ) or "no reimbursement profile"
    return (
        f"{impact.metric_key} {impact.current_value}→{impact.target_value}: "
        f"revenue {impact.recurring_revenue_uplift:,.0f}/yr, "
        f"cost savings {impact.recurring_cost_savings:,.0f}/yr. "
        f"Reimbursement mix: {methods}. "
        f"Confidence: {impact.confidence:.2f}."
    )


# ── Lever dispatcher ────────────────────────────────────────────────

_LEVER_DISPATCH = {
    "denial_rate": _lever_denial_rate,
    "initial_denial_rate": _lever_denial_rate,
    "final_denial_rate": _lever_denial_rate,
    "coding_denial_rate": _lever_denial_rate,
    "auth_denial_rate": _lever_denial_rate,
    "eligibility_denial_rate": _lever_denial_rate,
    "medical_necessity_denial_rate": _lever_denial_rate,
    "timely_filing_denial_rate": _lever_denial_rate,
    "clean_claim_rate": _lever_clean_claim_rate,
    "first_pass_resolution_rate": _lever_first_pass_resolution_rate,
    "days_in_ar": _lever_days_in_ar,
    "ar_over_90_pct": _lever_ar_over_90_pct,
    "net_collection_rate": _lever_net_collection_rate,
    "cost_to_collect": _lever_cost_to_collect,
    "discharged_not_final_billed_days": _lever_dnfb,
    "case_mix_index": _lever_cmi,
    "cmi": _lever_cmi,
    "bad_debt": _lever_bad_debt,
}


# ── Public entry points ────────────────────────────────────────────

def compute_value_bridge(
    current_metrics: Dict[str, Any],
    target_metrics: Dict[str, Any],
    reimbursement_profile: Optional[ReimbursementProfile],
    assumptions: Optional[BridgeAssumptions] = None,
    *,
    realization: Optional[Dict[str, Any]] = None,
    current_ebitda: float = 0.0,
) -> ValueBridgeResult:
    """Run every configured lever and assemble a :class:`ValueBridgeResult`.

    ``current_metrics`` / ``target_metrics`` maps are ``{metric_key:
    float}`` (or packet-shaped objects with a ``.value`` attribute).

    ``reimbursement_profile`` is expected from Prompt 2. When ``None``
    the bridge falls back to a 100% FFS commercial profile with a
    degraded confidence — useful for test fixtures and for deals where
    payer mix hasn't been entered yet.
    """
    assumptions = assumptions or BridgeAssumptions()
    if reimbursement_profile is None or not reimbursement_profile.method_weights:
        reimbursement_profile = _fallback_ffs_profile()

    def _value_of(d: Dict[str, Any], key: str) -> Optional[float]:
        v = d.get(key)
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

    lever_impacts: List[LeverImpact] = []
    common_keys = set(current_metrics.keys()) & set(target_metrics.keys())
    for metric in sorted(common_keys):
        fn = _LEVER_DISPATCH.get(metric)
        if fn is None:
            continue
        cur = _value_of(current_metrics, metric)
        tgt = _value_of(target_metrics, metric)
        if cur is None or tgt is None:
            continue
        if cur == tgt:
            continue
        try:
            impact = fn(metric, cur, tgt,
                         reimbursement_profile, realization, assumptions)
        except Exception as exc:  # noqa: BLE001 — one lever shouldn't kill the bridge
            logger.debug("lever %s failed: %s", metric, exc)
            continue
        lever_impacts.append(impact)

    # Raw (pre-dependency-adjustment) totals — kept for renderers that
    # want to show "naive vs adjusted" side by side.
    raw_total_rev = sum(li.recurring_revenue_uplift for li in lever_impacts)
    raw_total_recurring = sum(li.recurring_ebitda_delta for li in lever_impacts)

    # Cross-lever dependency adjustment (Prompt 15). Walks the levers
    # in causal-topological order and reduces each lever's
    # revenue-recovery component by the fraction already captured by
    # its parent levers. Idempotent when levers are independent.
    from .lever_dependency import walk_dependency
    adjusted_impacts, dependency_audit = walk_dependency(lever_impacts)
    lever_impacts = adjusted_impacts

    # Per-lever implementation ramp (Prompt 17). Evaluate each lever's
    # ramp factor at ``assumptions.evaluation_month`` using its
    # family's S-curve; scale the recurring flows. WC release is left
    # untouched — it happens at implementation, not at steady state.
    # At month 36 (the default) every default curve returns 1.0, so
    # this step is a no-op for existing callers.
    from .ramp_curves import (
        apply_ramp_to_lever,
        curve_for_metric,
        ramp_factor,
        resolve_ramp_curves,
    )
    ramp_registry = resolve_ramp_curves(assumptions.ramp_curves)
    eval_month = int(assumptions.evaluation_month)
    ramped_impacts: List[LeverImpact] = []
    per_lever_ramp_factors: Dict[str, float] = {}
    ramp_applied_any = False
    for li in lever_impacts:
        curve = curve_for_metric(li.metric_key, ramp_registry)
        factor = ramp_factor(curve, eval_month)
        per_lever_ramp_factors[li.metric_key] = factor
        if factor >= 1.0:
            ramped_impacts.append(li)
            continue
        ramp_applied_any = True
        ramped_impacts.append(apply_ramp_to_lever(li, factor))
    lever_impacts = ramped_impacts

    total_rev = sum(li.recurring_revenue_uplift for li in lever_impacts)
    total_cost = sum(li.recurring_cost_savings for li in lever_impacts)
    total_wc = sum(li.one_time_working_capital_release for li in lever_impacts)
    total_financing = sum(li.ongoing_financing_benefit for li in lever_impacts)
    total_recurring = total_rev + total_cost + total_financing
    target_ebitda = current_ebitda + total_recurring

    # Enterprise value only from recurring — one-time cash is
    # explicitly carried as a separate line (spec §9).
    ev_from_recurring = total_recurring * assumptions.exit_multiple
    ev_delta = ev_from_recurring   # cash release excluded from EV

    # Waterfall components.
    components: List[EbitdaBridgeComponent] = [
        EbitdaBridgeComponent("Current EBITDA", current_ebitda, "anchor"),
    ]
    for li in lever_impacts:
        if li.recurring_ebitda_delta != 0:
            components.append(EbitdaBridgeComponent(
                f"{li.metric_key} (recurring)",
                li.recurring_ebitda_delta,
                "revenue" if li.recurring_revenue_uplift >= li.recurring_cost_savings else "cost",
                source_metric=li.metric_key,
                provenance=dict(li.provenance),
            ))
    components.append(EbitdaBridgeComponent(
        "Target Recurring EBITDA", target_ebitda, "anchor",
    ))

    rationale = (
        f"Recurring EBITDA lift {total_recurring:,.0f} "
        f"(revenue {total_rev:,.0f} + cost {total_cost:,.0f} + "
        f"financing {total_financing:,.0f}). "
        f"One-time WC release {total_wc:,.0f} — excluded from EV. "
        f"EV delta @ {assumptions.exit_multiple:.1f}x: {ev_delta:,.0f}."
    )
    if ramp_applied_any:
        rationale += (
            f" Evaluated at month {eval_month} — recurring flows "
            f"scaled by per-lever ramp curves."
        )

    return ValueBridgeResult(
        assumptions=assumptions,
        lever_impacts=lever_impacts,
        current_ebitda=current_ebitda,
        target_recurring_ebitda=target_ebitda,
        total_recurring_revenue_uplift=total_rev,
        total_recurring_cost_savings=total_cost,
        total_one_time_wc_release=total_wc,
        total_financing_benefit=total_financing,
        total_recurring_ebitda_delta=total_recurring,
        enterprise_value_delta=ev_delta,
        enterprise_value_from_recurring=ev_from_recurring,
        cash_release_excluded_from_ev=total_wc,
        bridge_components=components,
        dependency_audit=list(dependency_audit),
        raw_total_recurring_ebitda_delta=raw_total_recurring,
        raw_total_recurring_revenue_uplift=raw_total_rev,
        ramp_applied=ramp_applied_any,
        per_lever_ramp_factors=per_lever_ramp_factors,
        rationale=rationale,
        status="OK" if lever_impacts else "INCOMPLETE",
        reason=("no target metrics differ from current"
                if not lever_impacts else ""),
    )


def compute_value_bridge_vectorized(
    current_metrics: Dict[str, Any],
    targets_matrix: Any,
    metric_order: List[str],
    reimbursement_profile: Optional[ReimbursementProfile],
    assumptions_per_sim: Optional[List[BridgeAssumptions]] = None,
    *,
    base_assumptions: Optional[BridgeAssumptions] = None,
    realization: Optional[Dict[str, Any]] = None,
    current_ebitda: float = 0.0,
) -> Tuple[Any, Any]:
    """Batch-evaluate :func:`compute_value_bridge` across ``n_sims``
    target vectors.

    Parameters
    ----------
    current_metrics
        Baseline metric values. Shared across sims.
    targets_matrix
        ``(n_sims, n_levers)`` numpy array. Column ``j`` is
        ``metric_order[j]``.
    metric_order
        Column-ordering for the matrix.
    reimbursement_profile
        Hospital reimbursement profile. Shared across sims (payer-
        specific leverage sampling lives on ``BridgeAssumptions``).
    assumptions_per_sim
        Optional list of per-sim ``BridgeAssumptions``. When ``None``
        we repeat ``base_assumptions`` (or a default) for every sim —
        useful for the "only targets differ" case.
    base_assumptions
        Fallback assumptions when ``assumptions_per_sim`` is ``None``.

    Returns
    -------
    (recurring_ebitda, one_time_cash)
        Numpy arrays of shape ``(n_sims,)``. Matches
        ``ValueBridgeResult.total_recurring_ebitda_delta`` and
        ``.total_one_time_wc_release`` respectively.

    Implementation note: the v2 bridge's inner math (dependency walk,
    ramp curves, per-payer revenue recovery, per-lever confidence) is
    not trivially vectorizable without re-implementing every lever
    function as a numpy kernel. We loop internally so the adapter is
    correct-by-construction; per-sim target sampling is still done in
    batch by the caller. Locked by the zero-variance and
    point-equivalence tests.
    """
    import numpy as np
    targets = np.asarray(targets_matrix, dtype=float)
    n_sims = int(targets.shape[0]) if targets.ndim >= 1 else 0
    recurring = np.zeros(n_sims)
    one_time = np.zeros(n_sims)
    if n_sims == 0 or not metric_order:
        return recurring, one_time
    order = list(metric_order)
    base_assumptions = base_assumptions or BridgeAssumptions()
    for i in range(n_sims):
        sim_targets = {
            order[j]: float(targets[i, j]) for j in range(len(order))
        }
        assumption = (
            assumptions_per_sim[i]
            if assumptions_per_sim is not None and i < len(assumptions_per_sim)
            else base_assumptions
        )
        try:
            result = compute_value_bridge(
                current_metrics,
                sim_targets,
                reimbursement_profile,
                assumption,
                realization=realization,
                current_ebitda=current_ebitda,
            )
        except Exception as exc:  # noqa: BLE001 — per-sim failures contained
            logger.debug("v2 vectorized draw %d failed: %s", i, exc)
            continue
        recurring[i] = result.total_recurring_ebitda_delta
        one_time[i] = result.total_one_time_wc_release
    return recurring, one_time


def _fallback_ffs_profile() -> ReimbursementProfile:
    """Minimal all-commercial-FFS profile used when no profile exists.
    Confidence penalty is applied by ``_overall_confidence`` via the
    provenance tags below."""
    return ReimbursementProfile(
        payer_classes={
            PayerClass.COMMERCIAL: __import__(
                "rcm_mc.finance.reimbursement_engine",
                fromlist=["PayerClassProfile"],
            ).PayerClassProfile(
                payer_class=PayerClass.COMMERCIAL,
                revenue_share=1.0,
                method_distribution={ReimbursementMethod.FEE_FOR_SERVICE: 1.0},
                collection_difficulty=0.3,
                avg_contractual_discount=0.55,
                provenance={"method_distribution":
                             ProvenanceTag.BENCHMARK_DEFAULT.value,
                             "revenue_share":
                             ProvenanceTag.BENCHMARK_DEFAULT.value},
            ),
        },
        method_weights={ReimbursementMethod.FEE_FOR_SERVICE: 1.0},
        notes=["fallback commercial FFS profile — no payer mix provided"],
        provenance={"payer_mix": ProvenanceTag.BENCHMARK_DEFAULT.value,
                     "method_weights": ProvenanceTag.CALCULATED.value},
    )


def explain_lever_value(
    metric_key: str,
    current_value: float,
    target_value: float,
    reimbursement_profile: Optional[ReimbursementProfile],
    assumptions: Optional[BridgeAssumptions] = None,
    *,
    realization: Optional[Dict[str, Any]] = None,
) -> str:
    """Run one lever and return a paragraph-length explanation."""
    assumptions = assumptions or BridgeAssumptions()
    fn = _LEVER_DISPATCH.get(metric_key)
    if fn is None:
        return (
            f"{metric_key} is not modeled as a value bridge lever. "
            f"Add it to _LEVER_DISPATCH before requesting an explanation."
        )
    profile = reimbursement_profile or _fallback_ffs_profile()
    impact = fn(metric_key, current_value, target_value,
                profile, realization, assumptions)

    # Classification of dominant pathway.
    rev = impact.recurring_revenue_uplift
    cost = impact.recurring_cost_savings
    wc = impact.one_time_working_capital_release
    fin = impact.ongoing_financing_benefit

    if max(wc, fin) > max(rev, cost):
        pathway = "primarily cash timing / working capital"
    elif rev >= cost * 1.2:
        pathway = "primarily revenue"
    elif cost >= rev * 1.2:
        pathway = "primarily cost savings"
    else:
        pathway = "mixed revenue and cost"

    recurring = rev + cost + fin > 0
    timing_note = ""
    if wc > 0 and recurring:
        timing_note = (
            f" One-time cash release {wc:,.0f} is separate from the "
            f"recurring EBITDA effect and should not be capitalized."
        )
    elif wc > 0:
        timing_note = (
            f" This is mostly a one-time cash effect "
            f"({wc:,.0f}) — recurring EBITDA lift is minor."
        )

    # Reimbursement tilt hint.
    tilt = ""
    if profile.payer_classes:
        top_payer = max(profile.payer_classes.items(),
                         key=lambda t: t[1].revenue_share)[0]
        if metric_key in ("denial_rate", "initial_denial_rate",
                           "auth_denial_rate", "eligibility_denial_rate"):
            if top_payer == PayerClass.COMMERCIAL:
                tilt = " Commercial-heavy mix amplifies this lever."
            elif top_payer == PayerClass.MEDICARE_FFS:
                tilt = " Medicare FFS exposure moderates the lever — DRG rates cap per-claim recovery."
        elif metric_key in ("case_mix_index", "cmi", "coding_denial_rate"):
            drg_share = profile.method_weights.get(
                ReimbursementMethod.DRG_PROSPECTIVE, 0.0,
            )
            if drg_share >= 0.4:
                tilt = f" Heavy DRG exposure ({drg_share*100:.0f}%) makes coding / acuity leverage material."
        elif metric_key == "bad_debt":
            sp = 0.0
            if PayerClass.SELF_PAY in profile.payer_classes:
                sp = profile.payer_classes[PayerClass.SELF_PAY].revenue_share
            if sp >= 0.2:
                tilt = f" High self-pay exposure ({sp*100:.0f}%) amplifies bad-debt sensitivity."

    weak = []
    if any(v == ProvenanceTag.INFERRED_FROM_PROFILE.value or
            v == ProvenanceTag.BENCHMARK_DEFAULT.value
            for v in impact.provenance.values()):
        weak.append("some reimbursement method distributions are inferred")
    if assumptions.claims_volume <= 0:
        weak.append("claims volume is inferred from net revenue at $1.5K/claim")
    weakness_note = f" Weak assumptions: {'; '.join(weak)}." if weak else ""

    return (
        f"{metric_key} moving {current_value}→{target_value} under this "
        f"hospital's reimbursement profile: {pathway}. "
        f"{impact.explanation}"
        f"{timing_note}{tilt}{weakness_note}"
    )
