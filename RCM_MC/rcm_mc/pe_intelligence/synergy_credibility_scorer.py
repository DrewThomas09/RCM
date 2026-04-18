"""Synergy credibility scorer — are the claimed synergies real?

Partners see synergy slides on every deal. The question is always
the same: is this real or aspirational? A partner's mental check:

1. **Category type** — procurement synergies are more reliable
   than revenue synergies. GPO rebates > contract renegotiations
   > cross-sell > 'network effects.'
2. **Timing** — year-1 cost takeouts with signed severance are
   believable. Year-3 revenue synergies are not.
3. **Evidence** — signed contracts, benchmark references,
   executed actions raise credibility. 'Management estimate'
   lowers it.
4. **Magnitude vs EBITDA** — synergies > 20% of entry EBITDA
   are rarely all real.
5. **Ownership** — named owner with monthly scorecard raises
   credibility. No owner = wishful.

This module takes a list of claimed synergies and returns a
per-synergy credibility score + partner-prudent realization %.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Base realization % by synergy category (partner-approximated).
CATEGORY_BASE_REALIZATION = {
    "procurement_gpo": 0.85,
    "shared_services": 0.70,
    "back_office_consolidation": 0.60,
    "contract_renegotiation": 0.55,
    "rcm_denial_reduction": 0.50,
    "labor_productivity": 0.45,
    "cross_sell_revenue": 0.30,
    "revenue_mix_shift": 0.25,
    "network_effects": 0.15,
    "cultural_alignment": 0.10,
}


@dataclass
class SynergyClaim:
    name: str
    category: str                           # key from CATEGORY_BASE_REALIZATION
    amount_m: float
    year_realized: int                      # 1-5
    has_signed_contract: bool = False
    has_benchmark_reference: bool = False
    has_action_already_executed: bool = False
    has_named_owner: bool = False
    source: str = "management_estimate"     # "management_estimate" /
                                            # "third_party" / "signed"


@dataclass
class SynergyAssessment:
    name: str
    category: str
    claimed_m: float
    credibility_0_100: int
    realization_pct: float
    partner_credit_m: float
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "claimed_m": self.claimed_m,
            "credibility_0_100": self.credibility_0_100,
            "realization_pct": self.realization_pct,
            "partner_credit_m": self.partner_credit_m,
            "rationale": self.rationale,
        }


@dataclass
class SynergyReport:
    assessments: List[SynergyAssessment] = field(default_factory=list)
    total_claimed_m: float = 0.0
    total_partner_credit_m: float = 0.0
    overall_realization_pct: float = 0.0
    vs_entry_ebitda_pct: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessments": [a.to_dict() for a in self.assessments],
            "total_claimed_m": self.total_claimed_m,
            "total_partner_credit_m": self.total_partner_credit_m,
            "overall_realization_pct": self.overall_realization_pct,
            "vs_entry_ebitda_pct": self.vs_entry_ebitda_pct,
            "partner_note": self.partner_note,
        }


def _score_synergy(c: SynergyClaim) -> SynergyAssessment:
    base = CATEGORY_BASE_REALIZATION.get(c.category, 0.30)
    cred = 50
    # Evidence modifiers:
    if c.has_signed_contract:
        cred += 20
    if c.has_benchmark_reference:
        cred += 10
    if c.has_action_already_executed:
        cred += 15
    if c.has_named_owner:
        cred += 5
    # Source modifier.
    if c.source == "signed":
        cred += 10
    elif c.source == "third_party":
        cred += 5
    elif c.source == "management_estimate":
        cred -= 5
    # Timing decay: year 3+ synergies take a haircut.
    if c.year_realized >= 3:
        cred -= 10
    if c.year_realized >= 4:
        cred -= 10
    cred = max(0, min(100, cred))

    # Realization = base × (credibility / 75 — anchor at 75 = full base).
    anchor = 75.0
    modifier = min(1.25, max(0.40, cred / anchor))
    realization = max(0.0, min(0.95, base * modifier))
    partner_credit = c.amount_m * realization

    # Rationale.
    bits = [f"Category '{c.category}' base realization "
            f"{base*100:.0f}%"]
    if c.has_signed_contract:
        bits.append("signed contract boosts credibility")
    if c.has_action_already_executed:
        bits.append("action already executed")
    if c.year_realized >= 3:
        bits.append(f"year-{c.year_realized} timing takes a haircut")
    if not c.has_named_owner:
        bits.append("no named owner — track that")
    rationale = "; ".join(bits) + "."

    return SynergyAssessment(
        name=c.name, category=c.category,
        claimed_m=round(c.amount_m, 2),
        credibility_0_100=int(cred),
        realization_pct=round(realization, 4),
        partner_credit_m=round(partner_credit, 2),
        rationale=rationale,
    )


def score_synergies(
    claims: List[SynergyClaim], entry_ebitda_m: float = 0.0,
) -> SynergyReport:
    assessments = [_score_synergy(c) for c in claims]
    total_claimed = sum(a.claimed_m for a in assessments)
    total_credit = sum(a.partner_credit_m for a in assessments)
    overall_real = (total_credit / total_claimed
                     if total_claimed > 0 else 0.0)
    vs_ebitda = (total_claimed / entry_ebitda_m
                  if entry_ebitda_m > 0 else 0.0)

    if not claims:
        note = "No synergies claimed."
    elif vs_ebitda >= 0.30:
        note = (f"Claimed synergies {vs_ebitda*100:.0f}% of entry "
                "EBITDA. Partner-prudent realization "
                f"${total_credit:,.1f}M "
                f"({overall_real*100:.0f}% of claimed). "
                "When synergies are a huge share of the thesis, "
                "diligence the TOP 3 by owner, not the list.")
    elif overall_real < 0.40:
        note = (f"Overall realization {overall_real*100:.0f}% — "
                "thin. The synergy slide is aspirational, not "
                "operational. Underwrite heavily haircut.")
    elif overall_real >= 0.70:
        note = (f"Synergy credibility strong "
                f"({overall_real*100:.0f}% realized). Signed / "
                "executed actions backing the claims.")
    else:
        note = (f"Standard synergy profile. ${total_credit:,.1f}M "
                f"partner-prudent credit vs ${total_claimed:,.1f}M "
                "claimed.")

    return SynergyReport(
        assessments=assessments,
        total_claimed_m=round(total_claimed, 2),
        total_partner_credit_m=round(total_credit, 2),
        overall_realization_pct=round(overall_real, 4),
        vs_entry_ebitda_pct=round(vs_ebitda, 4),
        partner_note=note,
    )


def render_synergy_report_markdown(r: SynergyReport) -> str:
    lines = [
        "# Synergy credibility scorecard",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total claimed: ${r.total_claimed_m:,.1f}M",
        f"- Partner-prudent credit: ${r.total_partner_credit_m:,.1f}M",
        f"- Overall realization: {r.overall_realization_pct*100:.0f}%",
        f"- Synergies vs entry EBITDA: "
        f"{r.vs_entry_ebitda_pct*100:.1f}%",
        "",
        "| Synergy | Category | Claimed | Cred | Real % | Credit |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for a in r.assessments:
        lines.append(
            f"| {a.name} | {a.category} | ${a.claimed_m:,.1f}M | "
            f"{a.credibility_0_100}/100 | "
            f"{a.realization_pct*100:.0f}% | "
            f"${a.partner_credit_m:,.2f}M |"
        )
    return "\n".join(lines)
