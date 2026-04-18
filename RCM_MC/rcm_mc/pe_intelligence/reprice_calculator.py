"""Reprice calculator — by how much do we reprice given diligence findings.

Partner statement: "Diligence surfaces a $5M EBITDA
haircut from QofE, a $2M lease concession that
wasn't in the model, and a $3M one-time item sitting
in the stated EBITDA. How do we reprice the bid?
The answer is math, not negotiation. If the multiple
is 11x and run-rate drops $10M, that's $110M off
the bid, possibly with a margin-of-safety haircut."

Distinct from:
- `pricing_concession_ladder` — concession moves.
- `thesis_break_price_calculator` — walk-away price.
- `banker_partner_pricing_tension` — gap to banker
  pitch.

This module is the **post-diligence reprice math**:
given explicit findings, compute the new bid and the
seller-conversation framing.

### Input shape

- Original bid (EV)
- Original multiple
- Finding list: each with category (ebitda_hit /
  working_capital_hit / one_time_addback_removal /
  capex_reserve) and $ amount

### Output

- new bid (EV)
- bid delta ($ and %)
- multiple preserved
- seller-conversation talking points
- verdict: small_reprice / meaningful_reprice /
  material_reprice / kill
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


FINDING_CATEGORIES = {
    "ebitda_hit",
    "working_capital_hit",
    "one_time_addback_removal",
    "capex_reserve",
    "legal_indemnity",
    "regulatory_reserve",
}


@dataclass
class DiligenceFinding:
    category: str
    name: str
    dollar_impact_m: float
    hit_ebitda: bool = False
    """If True, impact is on recurring EBITDA (and
    gets multiplied at exit). If False, it's a
    dollar-for-dollar adjustment (WC, indemnity,
    capex)."""


@dataclass
class RepriceInputs:
    original_bid_ev_m: float = 500.0
    original_multiple: float = 11.0
    findings: List[DiligenceFinding] = field(
        default_factory=list)
    safety_haircut_pct: float = 0.00
    """Additional margin-of-safety haircut on top of
    raw math."""


@dataclass
class RepriceReport:
    original_bid_ev_m: float = 0.0
    ebitda_hit_m: float = 0.0
    dollar_hit_m: float = 0.0
    raw_reprice_m: float = 0.0
    safety_haircut_m: float = 0.0
    new_bid_ev_m: float = 0.0
    bid_delta_m: float = 0.0
    bid_delta_pct: float = 0.0
    finding_summaries: List[Dict[str, Any]] = field(
        default_factory=list)
    seller_talking_points: List[str] = field(
        default_factory=list)
    verdict: str = "small_reprice"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_bid_ev_m": self.original_bid_ev_m,
            "ebitda_hit_m": self.ebitda_hit_m,
            "dollar_hit_m": self.dollar_hit_m,
            "raw_reprice_m": self.raw_reprice_m,
            "safety_haircut_m": self.safety_haircut_m,
            "new_bid_ev_m": self.new_bid_ev_m,
            "bid_delta_m": self.bid_delta_m,
            "bid_delta_pct": self.bid_delta_pct,
            "finding_summaries":
                self.finding_summaries,
            "seller_talking_points":
                self.seller_talking_points,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def compute_reprice(
    inputs: RepriceInputs,
) -> RepriceReport:
    ebitda_hit = sum(
        f.dollar_impact_m for f in inputs.findings
        if f.hit_ebitda
    )
    dollar_hit = sum(
        f.dollar_impact_m for f in inputs.findings
        if not f.hit_ebitda
    )
    raw_reprice = (
        ebitda_hit * inputs.original_multiple +
        dollar_hit
    )
    safety_haircut = (
        inputs.original_bid_ev_m *
        inputs.safety_haircut_pct
    )
    new_bid = max(
        0.0,
        inputs.original_bid_ev_m - raw_reprice -
        safety_haircut,
    )
    bid_delta = inputs.original_bid_ev_m - new_bid
    bid_delta_pct = (
        bid_delta / max(0.01, inputs.original_bid_ev_m)
    )

    finding_summaries = [
        {"category": f.category,
         "name": f.name,
         "dollar_impact_m": round(f.dollar_impact_m, 2),
         "hit_ebitda": f.hit_ebitda,
         "ev_impact_m": round(
             f.dollar_impact_m *
             (inputs.original_multiple if f.hit_ebitda else 1.0),
             2,
         )}
        for f in inputs.findings
    ]

    talking_points: List[str] = []
    if ebitda_hit > 0:
        talking_points.append(
            f"Run-rate EBITDA revised down "
            f"${ebitda_hit:.1f}M based on QofE / "
            "diligence findings — multiple stays; EV "
            f"adjusts by "
            f"${ebitda_hit * inputs.original_multiple:.1f}M."
        )
    if dollar_hit > 0:
        talking_points.append(
            f"${dollar_hit:.1f}M of identified "
            "dollar items (WC peg, capex reserve, "
            "indemnity) — dollar-for-dollar off EV."
        )
    if safety_haircut > 0:
        talking_points.append(
            f"${safety_haircut:.1f}M additional "
            "margin-of-safety given identified "
            "execution risk."
        )
    if talking_points:
        talking_points.append(
            f"Revised bid: ${new_bid:.0f}M "
            f"(down ${bid_delta:.0f}M / "
            f"{bid_delta_pct:.0%} from original)."
        )

    if bid_delta_pct == 0:
        verdict = "small_reprice"
        note = "No reprice — original bid holds."
    elif bid_delta_pct < 0.03:
        verdict = "small_reprice"
        note = (
            f"Small reprice "
            f"({bid_delta_pct:.1%} of original). "
            "Standard diligence adjustment; seller "
            "should accept."
        )
    elif bid_delta_pct < 0.08:
        verdict = "meaningful_reprice"
        note = (
            f"Meaningful reprice "
            f"({bid_delta_pct:.1%} of original). "
            "Seller will push back; lead with the "
            "biggest finding + QofE evidence; reference "
            "closing-timeline pressure."
        )
    elif bid_delta_pct < 0.15:
        verdict = "material_reprice"
        note = (
            f"Material reprice "
            f"({bid_delta_pct:.1%} of original). "
            "Process may break; seller will test other "
            "bidders first. Prepare for walk scenario."
        )
    else:
        verdict = "kill"
        note = (
            f"Reprice {bid_delta_pct:.0%} of original — "
            "seller won't take it; deal is effectively "
            "dead at this level. Walk or restructure "
            "the ask."
        )

    return RepriceReport(
        original_bid_ev_m=round(
            inputs.original_bid_ev_m, 2),
        ebitda_hit_m=round(ebitda_hit, 2),
        dollar_hit_m=round(dollar_hit, 2),
        raw_reprice_m=round(raw_reprice, 2),
        safety_haircut_m=round(safety_haircut, 2),
        new_bid_ev_m=round(new_bid, 2),
        bid_delta_m=round(bid_delta, 2),
        bid_delta_pct=round(bid_delta_pct, 4),
        finding_summaries=finding_summaries,
        seller_talking_points=talking_points,
        verdict=verdict,
        partner_note=note,
    )


def render_reprice_markdown(
    r: RepriceReport,
) -> str:
    lines = [
        "# Reprice calculation",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Original bid: ${r.original_bid_ev_m:.0f}M",
        f"- EBITDA hit: ${r.ebitda_hit_m:.1f}M",
        f"- Dollar hit: ${r.dollar_hit_m:.1f}M",
        f"- Raw reprice: ${r.raw_reprice_m:.1f}M",
        f"- Safety haircut: ${r.safety_haircut_m:.1f}M",
        f"- New bid: ${r.new_bid_ev_m:.0f}M "
        f"({r.bid_delta_pct:.0%} ↓)",
        "",
        "## Findings",
        "",
        "| Name | Category | $ Impact | Hits EBITDA | EV impact |",
        "|---|---|---|---|---|",
    ]
    for f in r.finding_summaries:
        lines.append(
            f"| {f['name']} | {f['category']} | "
            f"${f['dollar_impact_m']:.1f} | "
            f"{'yes' if f['hit_ebitda'] else 'no'} | "
            f"${f['ev_impact_m']:.1f} |"
        )
    if r.seller_talking_points:
        lines.append("")
        lines.append("## Seller talking points")
        for t in r.seller_talking_points:
            lines.append(f"- {t}")
    return "\n".join(lines)
