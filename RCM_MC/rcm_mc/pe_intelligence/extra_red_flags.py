"""Extra red-flag detectors beyond the core set.

`red_flags.py` holds 10 deal-killers. This module adds more:

- `physician_turnover_high` — retention below 85%.
- `clinical_staff_shortage` — unfilled RN positions > 15%.
- `payer_denial_spike` — recent quarter denial ratio > base + 200bps.
- `bad_debt_spike` — bad-debt growth > revenue growth × 2.
- `it_system_eol` — legacy EHR with end-of-life date inside hold.
- `lease_expiration_cluster` — >30% of leased sites expire inside hold.
- `regulatory_inspection_open` — unresolved CMS/state inspection.
- `self_insurance_tail` — retained self-insurance reserves not actuarially funded.
- `capex_deferral_pattern` — historical capex below 60% of D&A.
- `key_payer_churn` — planned departure of a top-3 commercial payer.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .heuristics import HeuristicContext, HeuristicHit, SEV_HIGH, SEV_MEDIUM, SEV_CRITICAL


def _r_physician_turnover(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "physician_retention_pct", None)
    if v is None:
        return None
    try:
        pct = float(v)
    except (TypeError, ValueError):
        return None
    if pct > 1.5:
        pct /= 100.0
    if pct >= 0.85:
        return None
    sev = SEV_HIGH if pct < 0.75 else SEV_MEDIUM
    return HeuristicHit(
        id="physician_turnover_high",
        title="Physician retention below peer floor",
        severity=sev,
        category="OPERATIONS",
        finding=(f"Physician retention at {pct*100:.0f}%. Below 85% signals "
                 "burnout or cultural drift; below 75% is a pipeline crisis."),
        partner_voice=("Physicians run the economics. If retention is "
                       "below 85%, the operating thesis has no chassis."),
        trigger_metrics=["physician_retention_pct"],
        trigger_values={"physician_retention_pct": pct},
        remediation="Conduct retention risk review; identify top 20% contributors by RVU.",
        references=["PE_HEURISTICS#physician-retention"],
    )


def _r_rn_shortage(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "unfilled_rn_positions_pct", None)
    if v is None:
        return None
    try:
        pct = float(v)
    except (TypeError, ValueError):
        return None
    if pct > 1.5:
        pct /= 100.0
    if pct < 0.15:
        return None
    sev = SEV_CRITICAL if pct >= 0.25 else SEV_HIGH
    return HeuristicHit(
        id="clinical_staff_shortage",
        title="RN vacancy rate above peer",
        severity=sev,
        category="OPERATIONS",
        finding=(f"{pct*100:.0f}% of RN positions unfilled. Above 15% "
                 "means contract-labor dependency and volume-capacity risk."),
        partner_voice=("Nursing shortages aren't a hiring problem — they're "
                       "a volume and quality problem. Price the contract-"
                       "labor drag."),
        trigger_metrics=["unfilled_rn_positions_pct"],
        trigger_values={"unfilled_rn_positions_pct": pct},
        remediation="Budget explicit contract-labor spend; accelerate hiring programs.",
    )


def _r_payer_denial_spike(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "denial_rate_qoq_delta_bps", None)
    if v is None:
        return None
    try:
        bps = float(v)
    except (TypeError, ValueError):
        return None
    if bps < 200:
        return None
    sev = SEV_HIGH if bps >= 400 else SEV_MEDIUM
    return HeuristicHit(
        id="payer_denial_spike",
        title="Denial-rate spike in recent quarter",
        severity=sev,
        category="PAYER",
        finding=(f"Denial rate up {bps:.0f} bps QoQ. A sudden spike usually "
                 "reflects payer-policy change or billing-system regression."),
        partner_voice=("Sudden denial spikes signal policy drift. Chase the "
                       "specific payer and reason code before scaling the lever plan."),
        trigger_metrics=["denial_rate_qoq_delta_bps"],
        trigger_values={"denial_rate_qoq_delta_bps": bps},
        remediation="Attribute to specific payers / reason codes in last 60 days.",
    )


def _r_bad_debt_spike(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "bad_debt_growth_yoy_pct", None)
    rg = ctx.revenue_growth_pct_per_yr
    if v is None or rg is None:
        return None
    try:
        bd = float(v)
        rev = float(rg)
    except (TypeError, ValueError):
        return None
    if bd < rev * 2 or bd < 5:
        return None
    return HeuristicHit(
        id="bad_debt_spike",
        title="Bad-debt growth outpacing revenue by 2x+",
        severity=SEV_HIGH,
        category="FINANCIAL",
        finding=(f"Bad debt +{bd:.1f}% vs revenue +{rev:.1f}%. Bad-debt "
                 "compounding faster than revenue is a leading-indicator "
                 "of insurance-mix deterioration."),
        partner_voice=("Bad-debt acceleration almost always precedes payer-"
                       "mix problems by 2-3 quarters. Watch the insurance-"
                       "coverage migration."),
        trigger_metrics=["bad_debt_growth_yoy_pct", "revenue_growth_pct_per_yr"],
        trigger_values={"bad_debt_yoy": bd, "revenue_yoy": rev},
        remediation="Decompose bad-debt by payer class; tighten financial-clearance thresholds.",
    )


def _r_it_system_eol(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "ehr_eol_years", None)
    hold = ctx.hold_years
    if v is None or hold is None:
        return None
    try:
        eol = float(v)
    except (TypeError, ValueError):
        return None
    if eol > hold + 1:
        return None
    return HeuristicHit(
        id="it_system_eol",
        title="EHR end-of-life inside hold window",
        severity=SEV_HIGH,
        category="OPERATIONS",
        finding=(f"Current EHR reaches end-of-life in ~{eol:.1f} years; "
                 f"hold is {hold:.1f}. Migration is a certainty."),
        partner_voice=("Budget for an EHR replacement now. Delaying it "
                       "into year 4 makes it the next owner's problem — "
                       "and buyers will discount for it."),
        trigger_metrics=["ehr_eol_years", "hold_years"],
        remediation="Include EHR migration in the capital plan; stand up cutover governance.",
    )


def _r_lease_cluster(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "leased_site_pct_expiring_in_hold", None)
    if v is None:
        return None
    try:
        pct = float(v)
    except (TypeError, ValueError):
        return None
    if pct > 1.5:
        pct /= 100.0
    if pct < 0.30:
        return None
    sev = SEV_HIGH if pct >= 0.50 else SEV_MEDIUM
    return HeuristicHit(
        id="lease_expiration_cluster",
        title="Lease-expiration cluster inside hold",
        severity=sev,
        category="STRUCTURE",
        finding=(f"{pct*100:.0f}% of leased sites expire during the hold. "
                 "Simultaneous renewals compress negotiation leverage."),
        partner_voice=("Renewing 30% of leases at once lets landlords set "
                       "the price. Stagger renewals or tie down terms now."),
        trigger_metrics=["leased_site_pct_expiring_in_hold"],
        trigger_values={"pct_expiring": pct},
        remediation="Stagger lease renewals or negotiate extensions pre-close.",
    )


def _r_open_inspection(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "open_cms_inspection", None)
    if not v:
        return None
    return HeuristicHit(
        id="regulatory_inspection_open",
        title="Unresolved CMS / state inspection on record",
        severity=SEV_HIGH,
        category="REGULATORY",
        finding=(f"Open regulatory inspection: {v}. Unresolved findings "
                 "gate reimbursement and limit operating flexibility."),
        partner_voice=("An open inspection is a contingent liability. "
                       "Resolve before close or structure the deal to the "
                       "resolution outcome."),
        trigger_metrics=["open_cms_inspection"],
        remediation="Track resolution; price any corrective-action plan into the offer.",
    )


def _r_self_insurance_tail(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "self_insurance_reserve_gap_m", None)
    if v is None:
        return None
    try:
        gap = float(v)
    except (TypeError, ValueError):
        return None
    if gap < 1:
        return None
    sev = SEV_HIGH if gap >= 10 else SEV_MEDIUM
    return HeuristicHit(
        id="self_insurance_tail",
        title="Self-insurance reserves under-funded",
        severity=sev,
        category="FINANCIAL",
        finding=(f"~${gap:.1f}M gap in self-insurance actuarial reserves. "
                 "Retained risk not on the balance sheet at book value."),
        partner_voice=("Self-insurance gaps sit on the deal until somebody "
                       "pays. Demand an actuarial study and fund the gap "
                       "at close."),
        trigger_metrics=["self_insurance_reserve_gap_m"],
        trigger_values={"gap_m": gap},
        remediation="Require pre-close actuarial study; fund the reserve at close.",
    )


def _r_capex_deferral(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "capex_to_da_ratio", None)
    if v is None:
        return None
    try:
        ratio = float(v)
    except (TypeError, ValueError):
        return None
    if ratio >= 0.80:
        return None
    sev = SEV_MEDIUM if ratio >= 0.60 else SEV_HIGH
    return HeuristicHit(
        id="capex_deferral_pattern",
        title="Historical capex below peer-typical D&A replacement",
        severity=sev,
        category="FINANCIAL",
        finding=(f"Capex/D&A ratio is {ratio:.2f}. Chronic deferral means "
                 "future owners inherit an aged asset base."),
        partner_voice=("Understated capex is the oldest trick in the book. "
                       "Adjust EBITDA for replacement capex before you price."),
        trigger_metrics=["capex_to_da_ratio"],
        trigger_values={"capex_to_da_ratio": ratio},
        remediation="Normalize maintenance capex to ≥ D&A when stress-testing EBITDA.",
    )


def _r_key_payer_churn(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    v = getattr(ctx, "top_payer_churn_risk", None)
    if not v:
        return None
    return HeuristicHit(
        id="key_payer_churn",
        title="Top-3 commercial payer departure risk",
        severity=SEV_HIGH,
        category="PAYER",
        finding=(f"Top-3 payer at churn risk: {v}. Loss of a top-3 "
                 "commercial payer usually compresses revenue 5-12%."),
        partner_voice=("If a top-3 payer leaves, you're rebuilding the "
                       "book from scratch. Contract status is the single "
                       "most important diligence item here."),
        trigger_metrics=["top_payer_churn_risk"],
        remediation="Get payer contract expiry dates + renewal status in writing pre-close.",
    )


# ── Registry / orchestrator ────────────────────────────────────────

EXTRA_RED_FLAG_FIELDS = (
    "physician_retention_pct",
    "unfilled_rn_positions_pct",
    "denial_rate_qoq_delta_bps",
    "bad_debt_growth_yoy_pct",
    "ehr_eol_years",
    "leased_site_pct_expiring_in_hold",
    "open_cms_inspection",
    "self_insurance_reserve_gap_m",
    "capex_to_da_ratio",
    "top_payer_churn_risk",
)


_DETECTORS: List[Callable[[HeuristicContext], Optional[HeuristicHit]]] = [
    _r_physician_turnover,
    _r_rn_shortage,
    _r_payer_denial_spike,
    _r_bad_debt_spike,
    _r_it_system_eol,
    _r_lease_cluster,
    _r_open_inspection,
    _r_self_insurance_tail,
    _r_capex_deferral,
    _r_key_payer_churn,
]


def run_extra_red_flags(ctx: HeuristicContext) -> List[HeuristicHit]:
    """Run every extra red-flag detector against ``ctx``."""
    hits: List[HeuristicHit] = []
    for fn in _DETECTORS:
        try:
            h = fn(ctx)
        except Exception:
            h = None
        if h is not None:
            hits.append(h)
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    hits.sort(key=lambda h: order.get(h.severity, 5))
    return hits
