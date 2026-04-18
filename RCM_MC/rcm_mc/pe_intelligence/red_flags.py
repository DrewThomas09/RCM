"""Red-flag detectors — targeted deal-killer patterns.

Red flags are the subset of heuristics a partner treats as categorical,
not probabilistic. "Payer concentration over 50% with a single
commercial insurer" is not a matter of judgment — it is a specific
structural risk that changes the underwriting approach or kills the
deal outright.

This module adds detectors that extend the base :mod:`heuristics`
registry. They share the :class:`HeuristicContext` and return
:class:`HeuristicHit` objects so downstream renderers treat them
uniformly.

Red flags run on top of heuristics — the :func:`run_all_rules` helper
runs both and merges results, dedup'd by id.
"""
from __future__ import annotations

from typing import List, Optional

from .heuristics import (
    HeuristicContext,
    HeuristicHit,
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_LOW,
    SEV_MEDIUM,
    run_heuristics,
)


# ── Detectors ────────────────────────────────────────────────────────

def _red_payer_concentration(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """A single payer > 40% of mix is a contract-negotiation risk.

    Not about Medicare share (that's the other rule) — this is about
    commercial-payer concentration. A hospital where a single Blue plan
    is 45% of revenue has a named, single-point negotiation risk.
    """
    mix = ctx.payer_mix or {}
    if not mix:
        return None
    norm = {str(k).lower(): float(v) for k, v in mix.items() if v is not None}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    # Exclude structurally-dominant aggregates.
    exclude = {"medicare", "medicaid", "other", "self_pay", "self-pay",
               "commercial", "managed_care"}
    single_payers = {k: v for k, v in norm.items() if k not in exclude}
    if not single_payers:
        return None
    top_name, top_share = max(single_payers.items(), key=lambda kv: kv[1])
    if top_share < 0.40:
        return None
    severity = SEV_HIGH if top_share >= 0.50 else SEV_MEDIUM
    return HeuristicHit(
        id="payer_concentration_risk",
        title="Single-payer concentration — contract negotiation risk",
        severity=severity,
        category="PAYER",
        finding=(
            f"{top_name.title()} accounts for {top_share*100:.0f}% of payer "
            "mix. A single-payer negotiation loss would materially "
            "re-rate the deal."
        ),
        partner_voice=(
            "What's the current contract expiry, and have we modeled a "
            "down-rate renewal? If the answer is 'no change', we're not "
            "actually diligencing."
        ),
        trigger_metrics=["payer_mix"],
        trigger_values={f"share_{top_name}": top_share},
        remediation=(
            "Obtain contract renewal timelines; model a 3-5% down-rate at "
            "renewal and test the covenant."
        ),
        references=["PE_HEURISTICS#payer-concentration"],
    )


def _red_contract_labor_dependency(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Premium / agency labor > 15% of total labor spend = margin cliff
    risk. Only evaluated if the caller populated the field."""
    value = getattr(ctx, "contract_labor_share", None)
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v > 1.5:
        v = v / 100.0
    if v < 0.15:
        return None
    severity = SEV_HIGH if v >= 0.25 else SEV_MEDIUM
    return HeuristicHit(
        id="contract_labor_dependency",
        title="Premium / agency labor share is elevated",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"{v*100:.0f}% of labor spend is contract/agency. Rates are "
            "volatile — a 10% agency-rate reset at $500M of labor is $50M "
            "of EBITDA exposure."
        ),
        partner_voice=(
            "Contract labor is the first thing I stress when margin looks "
            "clean — because when rates spiked in 2022, every single one "
            "of our portfolio hospitals got hit."
        ),
        trigger_metrics=["contract_labor_share"],
        trigger_values={"contract_labor_share": v},
        remediation="Stress agency rates +20%; if margin breaks covenant, re-price the deal.",
        references=["PE_HEURISTICS#contract-labor"],
    )


def _red_single_service_line_concentration(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """A single service line / DRG > 30% of revenue is a
    reimbursement-cliff risk — one CMS update wipes out margin."""
    value = getattr(ctx, "top_service_line_share", None)
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v > 1.5:
        v = v / 100.0
    if v < 0.30:
        return None
    severity = SEV_HIGH if v >= 0.40 else SEV_MEDIUM
    return HeuristicHit(
        id="service_line_concentration",
        title="Single service line concentrated — reimbursement-cliff risk",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"Top service line is {v*100:.0f}% of revenue. A CMS DRG update "
            "or payer policy change affecting this line moves the whole deal."
        ),
        partner_voice=(
            "Name the DRG and the pending CMS proposal. If you can't, we "
            "have a single-point-of-failure thesis we haven't diligenced."
        ),
        trigger_metrics=["top_service_line_share"],
        trigger_values={"top_service_line_share": v},
        remediation=(
            "Map the top DRG to the current CMS rule-making cycle; stress "
            "a 5% rate change."
        ),
        references=["PE_HEURISTICS#service-line-concentration"],
    )


def _red_340b_dependency(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """340B drug-discount revenue is politically contested and has
    been reduced twice by CMS in the last five years. High dependency =
    structural risk."""
    value = getattr(ctx, "share_340b_of_margin", None)
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v > 1.5:
        v = v / 100.0
    if v < 0.15:
        return None
    severity = SEV_HIGH if v >= 0.25 else SEV_MEDIUM
    return HeuristicHit(
        id="340b_margin_dependency",
        title="340B share of EBITDA is material — program risk",
        severity=severity,
        category="REGULATORY",
        finding=(
            f"340B contributes ~{v*100:.0f}% of EBITDA. The program has "
            "been cut twice by CMS since 2018 and the 2024 AHA ruling "
            "left the payback schedule unresolved."
        ),
        partner_voice=(
            "If 340B goes away in year three, what does the bridge look "
            "like? If the answer is 'broken', we need a different thesis."
        ),
        trigger_metrics=["share_340b_of_margin"],
        trigger_values={"share_340b_of_margin": v},
        remediation="Build an ex-340B sensitivity; hold the bid to clearing at half the current 340B benefit.",
        references=["PE_HEURISTICS#340b-risk"],
    )


def _red_covid_unwind_risk(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Some 2021-2023 baseline EBITDA numbers are inflated by
    one-time COVID relief (PRF, ERC, temporary-rate add-ons). If the
    baseline period includes these and they haven't been normalized,
    flag."""
    value = getattr(ctx, "covid_relief_share_of_ebitda", None)
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v > 1.5:
        v = v / 100.0
    if v < 0.05:
        return None
    severity = SEV_HIGH if v >= 0.12 else SEV_MEDIUM
    return HeuristicHit(
        id="covid_relief_unwind",
        title="Baseline EBITDA still contains COVID relief",
        severity=severity,
        category="FINANCIAL",
        finding=(
            f"Approximately {v*100:.0f}% of baseline EBITDA is COVID-relief "
            "funds (PRF, ERC, rate add-ons). These do not recur — the "
            "entry multiple should be calculated on normalized EBITDA."
        ),
        partner_voice=(
            "You don't pay 10x on PRF money. Strip it out of the baseline "
            "and re-compute the entry multiple before we talk price."
        ),
        trigger_metrics=["covid_relief_share_of_ebitda"],
        trigger_values={"covid_relief_share_of_ebitda": v},
        remediation="Normalize EBITDA to remove one-time relief; recompute multiples.",
        references=["PE_HEURISTICS#covid-normalization"],
    )


def _red_rate_cliff_ahead(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Known CMS / state rate cliff in the hold window — e.g.,
    behavioral-health IMD waiver expiry, sequestration reset, 340B
    rebate rule."""
    value = getattr(ctx, "known_rate_cliff_in_hold", None)
    if not value:
        return None
    return HeuristicHit(
        id="known_rate_cliff_in_hold",
        title="Known reimbursement cliff falls inside the hold window",
        severity=SEV_HIGH,
        category="REGULATORY",
        finding=(
            f"Identified rate-cliff event inside hold: {value}. The "
            "exit-year EBITDA must be modeled post-cliff, not pre-cliff."
        ),
        partner_voice=(
            "Don't exit into the cliff. Either shorten the hold, "
            "accelerate the lever program, or discount the exit case."
        ),
        trigger_metrics=["known_rate_cliff_in_hold"],
        remediation="Model exit-year EBITDA under post-cliff rate schedule.",
        references=["PE_HEURISTICS#rate-cliffs"],
    )


def _red_ehr_migration_planned(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """An EHR migration during the hold is a 12-24 month revenue-
    disruption risk — claims drop, DNFB spikes, DSO extends."""
    value = getattr(ctx, "ehr_migration_planned", None)
    if not value:
        return None
    return HeuristicHit(
        id="ehr_migration_planned",
        title="EHR migration planned during hold — revenue-disruption risk",
        severity=SEV_HIGH,
        category="OPERATIONS",
        finding=(
            "An EHR swap is planned during the hold period. Every EHR "
            "conversion we've seen produces 6-12 months of claims-lag, "
            "DNFB growth, and a measurable DSO extension."
        ),
        partner_voice=(
            "I've watched three EHR conversions and all three produced "
            "at least one covenant waiver quarter. Do not model "
            "this period at trend."
        ),
        trigger_metrics=["ehr_migration_planned"],
        remediation="Model a 9-12 month revenue-drag period around the cutover; pre-negotiate covenant relief.",
        references=["PE_HEURISTICS#ehr-conversion-drag"],
    )


def _red_prior_regulatory_action(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Past CMS penalties, CIA, or OIG investigations — these stay on
    the record and shape future diligence posture."""
    value = getattr(ctx, "prior_regulatory_action", None)
    if not value:
        return None
    return HeuristicHit(
        id="prior_regulatory_action",
        title="Prior CMS / OIG regulatory action on record",
        severity=SEV_MEDIUM,
        category="REGULATORY",
        finding=(
            f"Target has a prior regulatory action: {value}. This shapes "
            "the posture of any future audit or payer-dispute proceeding."
        ),
        partner_voice=(
            "We don't walk away over old penalties, but we do want the "
            "current compliance program documented before we sign."
        ),
        trigger_metrics=["prior_regulatory_action"],
        remediation="Document current compliance program + corrective-action outcomes before LOI.",
        references=["PE_HEURISTICS#prior-regulatory"],
    )


def _red_quality_score_below_peer(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """CMS star rating below 3 or HCAHPS percentile below 25 —
    reimbursement (VBP) headwind plus reputational drag."""
    stars = getattr(ctx, "cms_star_rating", None)
    if stars is None:
        return None
    try:
        s = float(stars)
    except (TypeError, ValueError):
        return None
    if s >= 3.0:
        return None
    severity = SEV_MEDIUM if s >= 2.0 else SEV_HIGH
    return HeuristicHit(
        id="quality_score_below_peer",
        title="CMS quality rating below peer floor",
        severity=severity,
        category="REGULATORY",
        finding=(
            f"CMS Star Rating is {s:.1f}. Below 3.0 triggers VBP penalty "
            "schedules on roughly 2% of Medicare revenue and correlates "
            "with above-peer readmissions cost."
        ),
        partner_voice=(
            "Low stars are fixable but they are a tell on operating "
            "maturity. Assume the RCM lever is harder to execute here."
        ),
        trigger_metrics=["cms_star_rating"],
        trigger_values={"cms_star_rating": s},
        remediation="Discount RCM lever realization 15-25% to reflect execution-quality signal.",
        references=["PE_HEURISTICS#quality-gate"],
    )


def _red_debt_maturity_in_hold(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Existing target debt that matures inside the hold requires
    refinance — and refinance rates at exit can break the exit thesis."""
    value = getattr(ctx, "debt_maturity_years", None)
    hold = ctx.hold_years
    if value is None or hold is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v > hold + 0.5:
        return None
    return HeuristicHit(
        id="debt_maturity_in_hold",
        title="Existing debt matures inside the hold — refinance risk",
        severity=SEV_MEDIUM,
        category="STRUCTURE",
        finding=(
            f"Target debt matures in ~{v:.1f} years against a {hold:.1f}-year "
            "hold. Refinance rates inside the hold window directly shape "
            "the exit-year cash coverage."
        ),
        partner_voice=(
            "Don't close a deal where refinance risk sits on your watch. "
            "Either term-out the debt at close or discount the exit for "
            "the rate environment."
        ),
        trigger_metrics=["debt_maturity_years", "hold_years"],
        trigger_values={"debt_maturity_years": v, "hold_years": hold},
        remediation="Term-out existing debt at close or build a rate-shock sensitivity.",
        references=["PE_HEURISTICS#debt-maturity"],
    )


# ── Additional context fields (duck-typed) ───────────────────────────
# These fields are consumed by the red-flag detectors above but do NOT
# exist on the base HeuristicContext dataclass. Callers add them via
# ``setattr`` on a context instance, or via a dict-shaped packet. This
# keeps the base HeuristicContext dataclass lean — you only pay the
# complexity if you use the feature.

RED_FLAG_FIELDS = (
    "contract_labor_share",
    "top_service_line_share",
    "share_340b_of_margin",
    "covid_relief_share_of_ebitda",
    "known_rate_cliff_in_hold",
    "ehr_migration_planned",
    "prior_regulatory_action",
    "cms_star_rating",
    "debt_maturity_years",
)


# ── Orchestrator ─────────────────────────────────────────────────────

RED_FLAG_DETECTORS = [
    _red_payer_concentration,
    _red_contract_labor_dependency,
    _red_single_service_line_concentration,
    _red_340b_dependency,
    _red_covid_unwind_risk,
    _red_rate_cliff_ahead,
    _red_ehr_migration_planned,
    _red_prior_regulatory_action,
    _red_quality_score_below_peer,
    _red_debt_maturity_in_hold,
]


def run_red_flags(ctx: HeuristicContext) -> List[HeuristicHit]:
    """Run every red-flag detector; return hits in severity order."""
    hits: List[HeuristicHit] = []
    for fn in RED_FLAG_DETECTORS:
        try:
            result = fn(ctx)
        except Exception as exc:
            result = HeuristicHit(
                id=getattr(fn, "__name__", "red_flag_unknown").lstrip("_"),
                title="Red-flag detector errored",
                severity=SEV_LOW,
                category="DATA",
                finding=f"Detector raised: {exc}",
                partner_voice="",
                remediation="Review detector inputs.",
            )
        if result is not None:
            hits.append(result)
    hits.sort(key=lambda h: (-h.severity_rank(), h.id))
    return hits


def run_all_rules(ctx: HeuristicContext) -> List[HeuristicHit]:
    """Union of base heuristics + red-flag detectors, dedup'd by id.

    If a red-flag detector and a base heuristic share an id, the
    base heuristic wins (never observed in practice, but documented).
    """
    base = run_heuristics(ctx)
    reds = run_red_flags(ctx)
    seen = {h.id for h in base}
    merged = list(base)
    for r in reds:
        if r.id not in seen:
            merged.append(r)
            seen.add(r.id)
    merged.sort(key=lambda h: (-h.severity_rank(), h.id))
    return merged
