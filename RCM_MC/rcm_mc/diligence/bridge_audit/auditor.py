"""Audit engine for banker-provided EBITDA bridges.

Takes a list of bridge levers (name + claimed $) + target profile
and produces a risk-adjusted bridge with per-lever verdicts, a
counter-bid recommendation, and the partner-facing "realistic vs
claimed" gap.

Core algorithm per lever:

    1. Classify via keyword matching → LeverCategory
    2. Pull the category's empirical realization prior
    3. Apply target-profile conditional boosts (denial-rate,
       MA-mix, unionized, regulatory exposure)
    4. Adjusted realization = prior_median + Σ boosts (clipped
       to [0, 1.1]).
    5. Adjusted range = prior_p25 × claimed → prior_p75 × claimed
    6. Verdict:
           OVERSTATED   if claimed > realistic p75
           REALISTIC    if realistic p25 ≤ claimed ≤ realistic p75
           UNDERSTATED  if claimed < realistic p25
           UNSUPPORTED  if failure_rate > 0.40 AND claimed > p50 realized
    7. Gap $ = claimed - realistic_median

Counter-bid math:
    bridge_gap = Σ (claimed - realistic_median)
    At entry_multiple M, counter = asking_price - bridge_gap × M
    Recommendation narrative names the worst lever and the dollar gap.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .lever_library import (
    LEVER_PRIORS, LeverCategory, LeverPrior, classify_lever,
    prior_for,
)


class LeverVerdict(str, Enum):
    REALISTIC = "REALISTIC"
    OVERSTATED = "OVERSTATED"
    UNDERSTATED = "UNDERSTATED"
    UNSUPPORTED = "UNSUPPORTED"


# ────────────────────────────────────────────────────────────────────
# Input / output dataclasses
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BridgeLever:
    """One banker-claimed bridge line."""
    name: str
    claimed_usd: float
    category: Optional[LeverCategory] = None   # override classifier
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "claimed_usd": self.claimed_usd,
            "category": self.category.value if self.category else None,
            "narrative": self.narrative,
        }


@dataclass
class LeverAudit:
    """Per-lever audit result."""
    lever: BridgeLever
    category: LeverCategory
    category_label: str
    claimed_usd: float
    adjusted_realization_median: float
    adjusted_realization_p25: float
    adjusted_realization_p75: float
    realistic_median_usd: float
    realistic_p25_usd: float
    realistic_p75_usd: float
    gap_usd: float                                # claimed - realistic_median
    verdict: LeverVerdict
    failure_rate: float
    duration_months_median: int
    applied_boosts: List[Tuple[str, float]] = field(default_factory=list)
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lever": self.lever.to_dict(),
            "category": self.category.value,
            "category_label": self.category_label,
            "claimed_usd": self.claimed_usd,
            "adjusted_realization_median": self.adjusted_realization_median,
            "adjusted_realization_p25": self.adjusted_realization_p25,
            "adjusted_realization_p75": self.adjusted_realization_p75,
            "realistic_median_usd": self.realistic_median_usd,
            "realistic_p25_usd": self.realistic_p25_usd,
            "realistic_p75_usd": self.realistic_p75_usd,
            "gap_usd": self.gap_usd,
            "verdict": self.verdict.value,
            "failure_rate": self.failure_rate,
            "duration_months_median": self.duration_months_median,
            "applied_boosts": [list(b) for b in self.applied_boosts],
            "narrative": self.narrative,
        }


@dataclass
class BridgeAuditReport:
    """Top-level audit output."""
    target_name: str
    claimed_bridge_usd: float
    realistic_bridge_usd: float
    realistic_bridge_p25_usd: float
    realistic_bridge_p75_usd: float
    gap_usd: float
    gap_pct: float
    per_lever: List[LeverAudit] = field(default_factory=list)
    # Counter-bid math
    entry_multiple: Optional[float] = None
    asking_price_usd: Optional[float] = None
    price_reduction_usd: Optional[float] = None
    counter_offer_usd: Optional[float] = None
    # Earn-out alternative (if buyer prefers not to re-price)
    earn_out_target_usd: Optional[float] = None
    earn_out_trigger_usd: Optional[float] = None
    # Summary
    overstated_count: int = 0
    unsupported_count: int = 0
    realistic_count: int = 0
    understated_count: int = 0
    headline: str = ""
    rationale: str = ""
    partner_recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_name": self.target_name,
            "claimed_bridge_usd": self.claimed_bridge_usd,
            "realistic_bridge_usd": self.realistic_bridge_usd,
            "realistic_bridge_p25_usd": self.realistic_bridge_p25_usd,
            "realistic_bridge_p75_usd": self.realistic_bridge_p75_usd,
            "gap_usd": self.gap_usd,
            "gap_pct": self.gap_pct,
            "per_lever": [p.to_dict() for p in self.per_lever],
            "entry_multiple": self.entry_multiple,
            "asking_price_usd": self.asking_price_usd,
            "price_reduction_usd": self.price_reduction_usd,
            "counter_offer_usd": self.counter_offer_usd,
            "earn_out_target_usd": self.earn_out_target_usd,
            "earn_out_trigger_usd": self.earn_out_trigger_usd,
            "overstated_count": self.overstated_count,
            "unsupported_count": self.unsupported_count,
            "realistic_count": self.realistic_count,
            "understated_count": self.understated_count,
            "headline": self.headline,
            "rationale": self.rationale,
            "partner_recommendation": self.partner_recommendation,
        }


# ────────────────────────────────────────────────────────────────────
# Conditional-boost logic
# ────────────────────────────────────────────────────────────────────

def _evaluate_target_conditions(
    target: Mapping[str, Any],
) -> Dict[str, bool]:
    """Translate a raw target profile into the keyed boolean conditions
    that ``LeverPrior.conditional_boosts`` reference.

    Keys produced match the strings in ``conditional_boosts`` tuples
    in ``lever_library.LEVER_PRIORS``.
    """
    conds: Dict[str, bool] = {}

    # Denial rate bands
    dr = target.get("denial_rate_pct")
    if dr is not None:
        dr = float(dr)
        conds["denial_rate_over_8pct"] = dr > 0.08
        conds["denial_rate_over_12pct"] = dr > 0.12

    # AR days
    ar = target.get("days_in_ar")
    if ar is not None:
        ar = float(ar)
        conds["days_in_ar_over_55"] = ar > 55
        conds["days_in_ar_under_40"] = ar < 40

    # Payer / MA
    ma = target.get("ma_mix_pct")
    if ma is not None:
        conds["has_ma_mix_over_40pct"] = float(ma) > 0.40

    comm = target.get("commercial_payer_share")
    if comm is not None:
        conds["commercial_mix_over_40pct"] = float(comm) > 0.40

    top1 = target.get("top_1_payer_share")
    if top1 is not None:
        conds["top_1_payer_share_over_30pct"] = float(top1) > 0.30

    self_pay = target.get("self_pay_share")
    if self_pay is not None:
        conds["self_pay_share_over_10pct"] = float(self_pay) > 0.10

    # Size / structure
    beds = target.get("beds")
    if beds is not None:
        conds["hospital_over_200_beds"] = int(beds) > 200
    sites = target.get("num_sites")
    if sites is not None:
        conds["multi_site_platform_over_5_locations"] = int(sites) > 5
        conds["multi_hospital_system"] = int(sites) > 1

    # EHR
    ehr = (target.get("ehr_vendor") or "").upper()
    conds["has_epic_or_cerner"] = ehr in ("EPIC", "CERNER")
    conds["recent_ehr_migration"] = bool(
        target.get("recent_ehr_migration"),
    )

    # Workforce
    conds["unionized_workforce"] = bool(
        target.get("unionized_workforce"),
    )
    conds["remote_rcm_staff_already"] = bool(
        target.get("remote_rcm_staff_already"),
    )
    conds["employed_physician_model"] = (
        target.get("physician_model") == "EMPLOYED"
    )
    conds["contracted_physician_model"] = (
        target.get("physician_model") == "CONTRACTED"
    )

    # Regulatory
    conds["site_neutral_rule_active"] = bool(
        target.get("site_neutral_rule_active", True),
    )
    conds["v28_rule_finalized"] = bool(
        target.get("v28_rule_finalized", True),
    )
    conds["doj_fca_investigation_active"] = bool(
        target.get("doj_fca_investigation_active"),
    )
    conds["doj_retrospective_chart_review_investigation"] = bool(
        target.get("doj_retrospective_chart_review_investigation"),
    )
    conds["hsr_expanded_reporting_active"] = bool(
        target.get("hsr_expanded_reporting_active", True),
    )

    # Market / history
    conds["prior_denial_initiative_failed"] = bool(
        target.get("prior_denial_initiative_failed"),
    )
    conds["prior_coding_audit_found_gaps"] = bool(
        target.get("prior_coding_audit_found_gaps"),
    )
    conds["already_top_decile_cmi"] = bool(
        target.get("already_top_decile_cmi"),
    )
    conds["has_in_house_underpayment_team"] = bool(
        target.get("has_in_house_underpayment_team"),
    )
    conds["hospital_in_low_income_msa"] = bool(
        target.get("hospital_in_low_income_msa"),
    )
    conds["state_dominant_payer_market"] = bool(
        target.get("state_dominant_payer_market"),
    )
    conds["platform_over_10_tuck_ins_history"] = bool(
        target.get("platform_over_10_tuck_ins_history"),
    )
    conds["cfo_tenure_under_18_months"] = bool(
        target.get("cfo_tenure_under_18_months"),
    )

    return conds


def _apply_boosts(
    prior: LeverPrior,
    target_conditions: Mapping[str, bool],
) -> Tuple[float, List[Tuple[str, float]]]:
    """Apply the prior's conditional boosts given the target conds.

    Returns (adjusted_median, list_of_applied_boosts).
    """
    median = prior.realization_median
    applied: List[Tuple[str, float]] = []
    for condition, boost in prior.conditional_boosts:
        if target_conditions.get(condition):
            median += boost
            applied.append((condition, boost))
    # Clip to a sensible band.  Realization can mildly exceed 1.0
    # (occasional over-delivery), but cap at 1.10 to prevent runaway.
    median = max(0.0, min(1.10, median))
    return median, applied


# ────────────────────────────────────────────────────────────────────
# Audit single lever
# ────────────────────────────────────────────────────────────────────

def _verdict_for_lever(
    *,
    claimed: float,
    p25_usd: float,
    p75_usd: float,
    failure_rate: float,
    median_realized_usd: float,
) -> LeverVerdict:
    """Five-way verdict.

    UNSUPPORTED when the category's failure rate is >40% AND the
    banker's claim is above the median realized — the two signals
    combined say "most deals miss this and you're still claiming
    above-median."
    """
    if claimed > p75_usd and failure_rate > 0.40:
        return LeverVerdict.UNSUPPORTED
    if claimed > p75_usd:
        return LeverVerdict.OVERSTATED
    if claimed < p25_usd:
        return LeverVerdict.UNDERSTATED
    return LeverVerdict.REALISTIC


def audit_lever(
    lever: BridgeLever,
    target_profile: Optional[Mapping[str, Any]] = None,
) -> LeverAudit:
    """Audit a single bridge lever against the lever library."""
    cat = lever.category or classify_lever(lever.name)
    prior = prior_for(cat)
    conds = _evaluate_target_conditions(target_profile or {})
    adj_median, applied = _apply_boosts(prior, conds)
    # Dispersion scales proportionally with the median shift
    scale = adj_median / max(prior.realization_median, 0.01)
    adj_p25 = max(0.0, prior.realization_p25 * scale)
    adj_p75 = max(0.0, prior.realization_p75 * scale)

    realistic_median = lever.claimed_usd * adj_median
    realistic_p25 = lever.claimed_usd * adj_p25
    realistic_p75 = lever.claimed_usd * adj_p75
    gap = lever.claimed_usd - realistic_median

    verdict = _verdict_for_lever(
        claimed=lever.claimed_usd,
        p25_usd=realistic_p25,
        p75_usd=realistic_p75,
        failure_rate=prior.failure_rate,
        median_realized_usd=realistic_median,
    )

    # Narrative
    pct = int(round(adj_median * 100))
    if verdict == LeverVerdict.UNSUPPORTED:
        narr = (
            f"{prior.label}: banker claims "
            f"${lever.claimed_usd/1e6:.1f}M. Our library of "
            f"{prior.realization_n_samples} deals shows "
            f"{int(prior.failure_rate*100)}% realized <50% of claim on "
            f"this lever; realistic capture on your target is "
            f"${realistic_median/1e6:.1f}M "
            f"({pct}% of claim)."
        )
    elif verdict == LeverVerdict.OVERSTATED:
        narr = (
            f"{prior.label}: banker's "
            f"${lever.claimed_usd/1e6:.1f}M is above the P75 "
            f"of realized outcomes (${realistic_p75/1e6:.1f}M). "
            f"Target adjustments applied "
            f"{'+' if (adj_median - prior.realization_median) >= 0 else ''}"
            f"{(adj_median - prior.realization_median)*100:.0f} pp "
            f"vs base prior."
        )
    elif verdict == LeverVerdict.UNDERSTATED:
        narr = (
            f"{prior.label}: banker's "
            f"${lever.claimed_usd/1e6:.1f}M is below typical "
            f"realization range (P25 "
            f"${realistic_p25/1e6:.1f}M). Conservatively framed "
            f"— likely held back for bid optics."
        )
    else:
        narr = (
            f"{prior.label}: banker's "
            f"${lever.claimed_usd/1e6:.1f}M is inside the "
            f"realistic P25-P75 range "
            f"(${realistic_p25/1e6:.1f}M – "
            f"${realistic_p75/1e6:.1f}M). Credible."
        )
    if applied:
        boost_summary = ", ".join(
            f"{cond} ({sign}{abs(b)*100:.0f} pp)"
            for cond, b in applied[:3]
            for sign in ("+" if b >= 0 else "-",)
        )
        narr += f" Target signals: {boost_summary}."

    return LeverAudit(
        lever=lever,
        category=cat,
        category_label=prior.label,
        claimed_usd=lever.claimed_usd,
        adjusted_realization_median=adj_median,
        adjusted_realization_p25=adj_p25,
        adjusted_realization_p75=adj_p75,
        realistic_median_usd=realistic_median,
        realistic_p25_usd=realistic_p25,
        realistic_p75_usd=realistic_p75,
        gap_usd=gap,
        verdict=verdict,
        failure_rate=prior.failure_rate,
        duration_months_median=prior.duration_months_median,
        applied_boosts=applied,
        narrative=narr,
    )


# ────────────────────────────────────────────────────────────────────
# Audit the full bridge
# ────────────────────────────────────────────────────────────────────

def audit_bridge(
    *,
    levers: Sequence[BridgeLever],
    target_name: str = "Target",
    target_profile: Optional[Mapping[str, Any]] = None,
    entry_multiple: Optional[float] = None,
    asking_price_usd: Optional[float] = None,
) -> BridgeAuditReport:
    """Full bridge audit.

    The lever list is audited independently — we do not cap for
    double-counting between denial + clean-claim, since that's a
    judgement call partners should make after seeing the per-lever
    detail.  We flag the double-count in the partner recommendation.
    """
    per_lever = [
        audit_lever(l, target_profile=target_profile) for l in levers
    ]
    claimed = sum(l.claimed_usd for l in levers)
    realistic_med = sum(a.realistic_median_usd for a in per_lever)
    realistic_p25 = sum(a.realistic_p25_usd for a in per_lever)
    realistic_p75 = sum(a.realistic_p75_usd for a in per_lever)
    gap = claimed - realistic_med
    gap_pct = gap / claimed if claimed > 0 else 0.0

    counts = {v: 0 for v in LeverVerdict}
    for a in per_lever:
        counts[a.verdict] += 1

    # Counter-bid math
    price_reduction_usd: Optional[float] = None
    counter_offer_usd: Optional[float] = None
    if entry_multiple and asking_price_usd and gap > 0:
        price_reduction_usd = gap * entry_multiple
        counter_offer_usd = max(
            0.0, asking_price_usd - price_reduction_usd,
        )

    # Earn-out alternative: structure the overstated gap as an
    # earn-out that only pays if realized EBITDA hits the banker's
    # claimed level.  Target = the overstated amount.
    overstated_gap = sum(
        max(0.0, a.gap_usd) for a in per_lever
        if a.verdict in (LeverVerdict.OVERSTATED, LeverVerdict.UNSUPPORTED)
    )
    earn_out_target_usd = overstated_gap if overstated_gap > 0 else None
    earn_out_trigger_usd = (
        realistic_med + overstated_gap if overstated_gap > 0 else None
    )

    # Headline + rationale
    worst = max(
        per_lever,
        key=lambda a: a.gap_usd if a.verdict != LeverVerdict.UNDERSTATED else 0,
        default=None,
    )
    if gap > 0 and gap_pct > 0.15:
        headline = (
            f"Banker's bridge is ${claimed/1e6:.1f}M; realistic "
            f"capture is ${realistic_med/1e6:.1f}M — "
            f"${gap/1e6:.1f}M gap ({gap_pct*100:.0f}% of claim)."
        )
    elif gap > 0:
        headline = (
            f"Banker's bridge is ${claimed/1e6:.1f}M; realistic "
            f"capture is ${realistic_med/1e6:.1f}M — "
            f"small ${gap/1e6:.1f}M gap ({gap_pct*100:.0f}% of claim) "
            f"inside acceptable tolerance."
        )
    elif gap < 0:
        headline = (
            f"Banker's bridge is ${claimed/1e6:.1f}M; realistic "
            f"capture is ${realistic_med/1e6:.1f}M — "
            f"${abs(gap)/1e6:.1f}M *higher* than claimed. "
            f"Seller may be sandbagging."
        )
    else:
        headline = (
            f"Banker's bridge is ${claimed/1e6:.1f}M; audit "
            f"confirms credibility across every lever."
        )

    rationale_parts: List[str] = []
    if counts[LeverVerdict.UNSUPPORTED]:
        rationale_parts.append(
            f"{counts[LeverVerdict.UNSUPPORTED]} unsupported lever"
            f"{'s' if counts[LeverVerdict.UNSUPPORTED] != 1 else ''} "
            "(high historical failure × above-P75 claim)"
        )
    if counts[LeverVerdict.OVERSTATED]:
        rationale_parts.append(
            f"{counts[LeverVerdict.OVERSTATED]} overstated lever"
            f"{'s' if counts[LeverVerdict.OVERSTATED] != 1 else ''} "
            "above P75 realization"
        )
    if counts[LeverVerdict.REALISTIC]:
        rationale_parts.append(
            f"{counts[LeverVerdict.REALISTIC]} realistic lever"
            f"{'s' if counts[LeverVerdict.REALISTIC] != 1 else ''} "
            "inside P25-P75 band"
        )
    if counts[LeverVerdict.UNDERSTATED]:
        rationale_parts.append(
            f"{counts[LeverVerdict.UNDERSTATED]} likely sandbagged "
            "(below P25)"
        )
    rationale = " · ".join(rationale_parts) if rationale_parts else "No levers audited."

    # Partner recommendation
    rec_parts: List[str] = []
    if price_reduction_usd and price_reduction_usd > 1_000_000:
        rec_parts.append(
            f"Counter at ${counter_offer_usd/1e6:.1f}M "
            f"(down ${price_reduction_usd/1e6:.1f}M at "
            f"{entry_multiple:.1f}× on the gap)."
        )
    if earn_out_target_usd:
        rec_parts.append(
            f"Alternative: structure ${earn_out_target_usd/1e6:.1f}M "
            f"as a 24-month earn-out triggered at "
            f"${earn_out_trigger_usd/1e6:.1f}M LTM EBITDA."
        )
    if worst and worst.verdict in (
        LeverVerdict.UNSUPPORTED, LeverVerdict.OVERSTATED,
    ):
        rec_parts.append(
            f"Press banker on '{worst.lever.name}' — largest single "
            f"gap at ${worst.gap_usd/1e6:.1f}M."
        )
    # Double-count flag
    cats = {a.category for a in per_lever}
    if {LeverCategory.DENIAL_WORKFLOW, LeverCategory.CLEAN_CLAIM_RATE} <= cats:
        rec_parts.append(
            "Denial + clean-claim levers likely double-count — "
            "reconcile to single lever before re-rating."
        )
    partner_rec = " ".join(rec_parts) if rec_parts else (
        "Bridge clears audit; no counter-bid adjustment needed."
    )

    return BridgeAuditReport(
        target_name=target_name,
        claimed_bridge_usd=claimed,
        realistic_bridge_usd=realistic_med,
        realistic_bridge_p25_usd=realistic_p25,
        realistic_bridge_p75_usd=realistic_p75,
        gap_usd=gap,
        gap_pct=gap_pct,
        per_lever=per_lever,
        entry_multiple=entry_multiple,
        asking_price_usd=asking_price_usd,
        price_reduction_usd=price_reduction_usd,
        counter_offer_usd=counter_offer_usd,
        earn_out_target_usd=earn_out_target_usd,
        earn_out_trigger_usd=earn_out_trigger_usd,
        overstated_count=counts[LeverVerdict.OVERSTATED],
        unsupported_count=counts[LeverVerdict.UNSUPPORTED],
        realistic_count=counts[LeverVerdict.REALISTIC],
        understated_count=counts[LeverVerdict.UNDERSTATED],
        headline=headline,
        rationale=rationale,
        partner_recommendation=partner_rec,
    )


def parse_bridge_text(text: str) -> List[BridgeLever]:
    """Parse a free-text bridge input into BridgeLever records.

    Accepted formats (one per line):

        Denial workflow, 4.2M
        Denial workflow: $4.2M
        Denial workflow = 4,200,000
        "Denial workflow" 4.2

    Lines starting with ``#`` are comments.  Dollar values can carry
    ``M`` (millions), ``K`` (thousands), or be raw.
    """
    levers: List[BridgeLever] = []
    if not text:
        return levers
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Prefer `:` / `=` as separators (explicit); fall back to
        # the last comma (for "Name, $4.2M" format).  Commas inside
        # numeric amounts like "$3,100,000" would confuse last-comma
        # parsing, so we route those through the colon/equals path.
        sep_idx = -1
        for sep in (":", "="):
            idx = line.find(sep)
            if idx >= 0:
                sep_idx = idx
                break
        if sep_idx < 0:
            # No colon/equals — find the last comma or space
            # that's followed by a number.
            for i in range(len(line) - 1, -1, -1):
                if line[i] in (",", " "):
                    rest = line[i + 1:].strip()
                    if rest and (
                        rest[0].isdigit() or rest[0] == "$"
                    ):
                        sep_idx = i
                        break
        if sep_idx < 0:
            continue
        name = line[:sep_idx].strip().strip('"').strip("'")
        # Trim trailing separators left behind when we split on a
        # trailing space (e.g. "Denial workflow, 4.2M" splits at the
        # space, leaving "Denial workflow," as the name).
        while name and name[-1] in (",", ":", ";", "="):
            name = name[:-1].rstrip()
        amount_str = line[sep_idx + 1:].strip()
        usd = _parse_usd(amount_str)
        if usd is None or not name:
            continue
        levers.append(BridgeLever(name=name, claimed_usd=usd))
    return levers


def _parse_usd(s: str) -> Optional[float]:
    """Parse a money string to a float.  Accepts $, commas,
    M/K suffixes, plain numbers."""
    s = s.replace("$", "").replace(",", "").strip()
    if not s:
        return None
    mult = 1.0
    if s.lower().endswith("m"):
        mult = 1_000_000.0
        s = s[:-1]
    elif s.lower().endswith("k"):
        mult = 1_000.0
        s = s[:-1]
    elif s.lower().endswith("mm"):
        mult = 1_000_000.0
        s = s[:-2]
    try:
        return float(s) * mult
    except ValueError:
        return None
