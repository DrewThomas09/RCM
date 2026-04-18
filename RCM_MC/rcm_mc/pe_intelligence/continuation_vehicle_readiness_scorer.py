"""Continuation vehicle readiness — CV exit fit scoring.

Partner statement: "Not every asset is a continuation
candidate. CV investors want a known asset with a
clear remaining value-creation runway, management
that wants to stay and re-up, and a GP that can
actually commit additional capital. The worst CVs
are the ones where the GP just couldn't find a
buyer — LP advisory committees now see those a mile
away. Before I pitch a CV, I need an honest read on
the asset's CV fit."

Distinct from:
- `exit_alternative_comparator` — compares 5 exit
  paths.
- `exit_buyer_view_mirror` — buyer IC memo.
- `exit_planning` — readiness checklist.
- `buyer_type_fit_analyzer` — buyer profiles.

This module is **CV-specific**: scores the asset on
the 6 criteria LP-side secondary investors actually
probe.

### 6 CV fit dimensions

1. **remaining_runway_years** — VCP still to execute;
   CV investors want 3-5 years of visible upside.
2. **management_rollover_intent** — mgmt wants to stay
   with CV structure and re-up meaningful equity.
3. **gp_reinvest_commitment_m** — GP cross-fund
   commitment size (LP-signal for skin-in-the-game).
4. **strip_sale_possible** — asset is salable at
   market-tested price if CV fails (escape hatch).
5. **lp_advisory_committee_conflict_risk** — LP AC
   has approved similar CVs recently (or not).
6. **third_party_lead_identified** — named lead
   secondary investor (Goldman / Lexington / Ardian
   / HarbourVest / AlpInvest) with LOI-level
   interest.

### Output

Per-dimension score + composite CV fit + partner
verdict: pursue_cv / conditional / pursue_sale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CVReadinessInputs:
    remaining_runway_years: float = 3.0
    management_rollover_intent_pct: float = 0.50
    """% of mgmt equity rolling into CV (0-1); 50% is
    strong, <25% is concerning."""
    gp_reinvest_commitment_m: float = 10.0
    """GP cross-fund commitment."""
    strip_sale_price_validated: bool = False
    lp_ac_recent_similar_cv_approved: bool = False
    third_party_lead_identified: bool = False
    existing_moic: float = 2.0
    existing_irr: float = 0.18


@dataclass
class CVDimensionScore:
    dimension: str
    score_0_4: int
    note: str


@dataclass
class CVReadinessReport:
    dimensions: List[CVDimensionScore] = field(
        default_factory=list)
    composite_score_0_24: int = 0
    verdict: str = "conditional"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": [
                {"dimension": d.dimension,
                 "score_0_4": d.score_0_4,
                 "note": d.note}
                for d in self.dimensions
            ],
            "composite_score_0_24":
                self.composite_score_0_24,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def score_cv_readiness(
    inputs: CVReadinessInputs,
) -> CVReadinessReport:
    dims: List[CVDimensionScore] = []

    # 1. remaining runway
    runway = inputs.remaining_runway_years
    if runway >= 4.0:
        s, note = 4, (
            f"{runway:.1f}-yr runway — LP secondary "
            "investors want to see 3-5 years of "
            "visible upside; this is the sweet spot."
        )
    elif runway >= 3.0:
        s, note = 3, (
            f"{runway:.1f}-yr runway — acceptable CV "
            "window."
        )
    elif runway >= 2.0:
        s, note = 2, (
            f"{runway:.1f}-yr runway is short for a "
            "CV; investors will question the story."
        )
    else:
        s, note = 0, (
            f"{runway:.1f}-yr runway is too short for "
            "a CV; LP reads as 'couldn't find a buyer.'"
        )
    dims.append(CVDimensionScore(
        "remaining_runway_years", s, note))

    # 2. mgmt rollover
    mrol = inputs.management_rollover_intent_pct
    if mrol >= 0.50:
        s, note = 4, (
            f"{mrol:.0%} rollover — strong alignment "
            "signal; mgmt wants to stay."
        )
    elif mrol >= 0.30:
        s, note = 3, (
            f"{mrol:.0%} rollover — adequate; probe "
            "whether mgmt sees upside or is cashing "
            "out."
        )
    elif mrol >= 0.15:
        s, note = 2, (
            f"{mrol:.0%} — thin rollover; CV investors "
            "will push for higher."
        )
    else:
        s, note = 0, (
            f"{mrol:.0%} — inadequate; mgmt signals "
            "exit, not re-up."
        )
    dims.append(CVDimensionScore(
        "management_rollover_intent", s, note))

    # 3. GP reinvest
    gp = inputs.gp_reinvest_commitment_m
    if gp >= 25.0:
        s, note = 4, (
            f"${gp:.0f}M GP commitment — strong LP "
            "skin-in-the-game signal."
        )
    elif gp >= 10.0:
        s, note = 3, (
            f"${gp:.0f}M GP commitment — adequate."
        )
    elif gp >= 5.0:
        s, note = 2, (
            f"${gp:.0f}M — light but acceptable."
        )
    else:
        s, note = 0, (
            f"${gp:.0f}M GP commitment — LP advisory "
            "committee will flag this as low skin."
        )
    dims.append(CVDimensionScore(
        "gp_reinvest_commitment_m", s, note))

    # 4. strip sale
    if inputs.strip_sale_price_validated:
        s, note = 4, (
            "Strip sale validated at market price — "
            "fallback credibility and price-discovery "
            "benchmark."
        )
    else:
        s, note = 1, (
            "No validated strip sale — LP will ask "
            "'how do we know this price?'; run a "
            "sub-process for market testing."
        )
    dims.append(CVDimensionScore(
        "strip_sale_possible", s, note))

    # 5. LP AC recent approvals
    if inputs.lp_ac_recent_similar_cv_approved:
        s, note = 3, (
            "LP advisory committee has approved "
            "similar CVs recently — the playbook "
            "precedent is established."
        )
    else:
        s, note = 1, (
            "No recent similar CV approval from LP AC "
            "— expect extended negotiation and "
            "conditioning."
        )
    dims.append(CVDimensionScore(
        "lp_advisory_committee_conflict_risk", s, note))

    # 6. third-party lead
    if inputs.third_party_lead_identified:
        s, note = 4, (
            "Named lead secondary investor identified "
            "— LOI-level interest validates CV "
            "pricing mechanism."
        )
    else:
        s, note = 0, (
            "No named lead — without a lead investor "
            "the CV is a pitch, not a process."
        )
    dims.append(CVDimensionScore(
        "third_party_lead_identified", s, note))

    composite = sum(d.score_0_4 for d in dims)

    if composite >= 18 and inputs.existing_moic >= 2.0:
        verdict = "pursue_cv"
        note = (
            f"Composite {composite}/24; existing MOIC "
            f"{inputs.existing_moic:.1f}x. CV fit is "
            "strong — pursue with named lead and LP AC "
            "pre-alignment."
        )
    elif composite >= 12:
        verdict = "conditional"
        note = (
            f"Composite {composite}/24 — CV viable "
            "with specific gaps closed. Prioritize "
            "strip-sale validation and management "
            "rollover conversion."
        )
    else:
        verdict = "pursue_sale"
        note = (
            f"Composite {composite}/24 is below CV "
            "threshold. The pattern LP secondaries "
            "now screen for is 'GP couldn't find a "
            "buyer' — run a real sale process and "
            "don't pitch a CV until the fit is there."
        )

    return CVReadinessReport(
        dimensions=dims,
        composite_score_0_24=composite,
        verdict=verdict,
        partner_note=note,
    )


def render_cv_readiness_markdown(
    r: CVReadinessReport,
) -> str:
    lines = [
        "# Continuation vehicle readiness",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Composite: {r.composite_score_0_24}/24",
        "",
        "| Dimension | Score | Note |",
        "|---|---|---|",
    ]
    for d in r.dimensions:
        lines.append(
            f"| {d.dimension} | {d.score_0_4}/4 | "
            f"{d.note} |"
        )
    return "\n".join(lines)
