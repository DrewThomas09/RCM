"""Negotiation position — derive offer strategy from the review.

Given a PartnerReview, this module generates a partner-voice
negotiation posture:

- **Anchor price** — where to open.
- **Walkaway** — where to pull the offer.
- **Leverage points** — findings from the review that support a
  lower offer.
- **Concessions** — what we can give back to unstick talks.
- **Cadence** — aggressive vs disciplined vs collaborative.

This is not a full deal-sim — it's a structured partner cheatsheet
for the pricing discussion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .heuristics import SEV_CRITICAL, SEV_HIGH
from .partner_review import PartnerReview


@dataclass
class NegotiationPosition:
    anchor_multiple: Optional[float] = None
    anchor_price_m: Optional[float] = None
    walkaway_multiple: Optional[float] = None
    walkaway_price_m: Optional[float] = None
    leverage_points: List[str] = field(default_factory=list)
    concessions_available: List[str] = field(default_factory=list)
    cadence: str = "disciplined"           # "aggressive" | "disciplined" | "collaborative"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_multiple": self.anchor_multiple,
            "anchor_price_m": self.anchor_price_m,
            "walkaway_multiple": self.walkaway_multiple,
            "walkaway_price_m": self.walkaway_price_m,
            "leverage_points": list(self.leverage_points),
            "concessions_available": list(self.concessions_available),
            "cadence": self.cadence,
            "partner_note": self.partner_note,
        }


def _leverage_points(review: PartnerReview) -> List[str]:
    out: List[str] = []
    for h in review.heuristic_hits:
        if h.severity in (SEV_CRITICAL, SEV_HIGH) and h.partner_voice:
            out.append(f"{h.title}: {h.partner_voice}")
    for b in review.reasonableness_checks:
        if b.verdict in ("OUT_OF_BAND", "IMPLAUSIBLE") and b.partner_note:
            out.append(f"{b.metric} off-band: {b.partner_note}")
    return out[:5]


def _concessions() -> List[str]:
    # Common concessions a sponsor can offer without moving price.
    return [
        "Higher equity rollover pool for management.",
        "Longer reps-and-warranties tail with R&W insurance.",
        "Earnout on retained contingencies.",
        "Staged payments tied to regulatory outcomes.",
        "Fast closing timeline (30-day outside date).",
    ]


def _cadence(review: PartnerReview) -> str:
    rec = review.narrative.recommendation
    if rec == "STRONG_PROCEED":
        return "aggressive"
    if rec == "PASS":
        return "walk"
    if any(h.severity == SEV_CRITICAL for h in review.heuristic_hits):
        return "disciplined"
    return "disciplined"


def derive_negotiation_position(
    review: PartnerReview,
    *,
    seller_ask_multiple: Optional[float] = None,
) -> NegotiationPosition:
    ctx = review.context_summary or {}
    modeled_exit = ctx.get("exit_multiple")
    modeled_entry = ctx.get("entry_multiple")
    ebitda = ctx.get("ebitda_m")

    # Anchor: 1.0 turn below seller ask or 0.5 turn below modeled entry.
    anchor = None
    if seller_ask_multiple is not None:
        anchor = max(4.5, seller_ask_multiple - 1.0)
    elif modeled_entry is not None:
        anchor = max(4.5, modeled_entry - 0.5)
    # Walkaway: 0.75 turn below anchor.
    walkaway = (anchor - 0.75) if anchor is not None else None

    anchor_price = None
    walkaway_price = None
    if ebitda and anchor is not None:
        anchor_price = ebitda * anchor
    if ebitda and walkaway is not None:
        walkaway_price = ebitda * walkaway

    leverage = _leverage_points(review)
    concessions = _concessions()
    cadence = _cadence(review)

    if cadence == "walk":
        note = ("Do not engage at seller's ask. If price moves materially, "
                "revisit; otherwise walk.")
    elif cadence == "aggressive":
        note = ("Strong deal — can price in tight but preserve optionality "
                "on covenant structure.")
    else:
        note = ("Disciplined stance — anchor below seller ask, use "
                "findings as leverage, concessions to close the gap.")

    return NegotiationPosition(
        anchor_multiple=anchor,
        anchor_price_m=anchor_price,
        walkaway_multiple=walkaway,
        walkaway_price_m=walkaway_price,
        leverage_points=leverage,
        concessions_available=concessions,
        cadence=cadence,
        partner_note=note,
    )


def render_negotiation_markdown(position: NegotiationPosition) -> str:
    lines = [
        "# Negotiation position",
        "",
        f"**Cadence:** {position.cadence}",
        "",
        f"_{position.partner_note}_",
        "",
        "## Anchor / walkaway",
        "",
        f"- Anchor multiple: {position.anchor_multiple or 'n/a'}  ",
        f"- Anchor price: ${position.anchor_price_m:,.1f}M" if position.anchor_price_m else "- Anchor price: n/a",
        f"- Walkaway multiple: {position.walkaway_multiple or 'n/a'}  ",
        f"- Walkaway price: ${position.walkaway_price_m:,.1f}M" if position.walkaway_price_m else "- Walkaway price: n/a",
    ]
    if position.leverage_points:
        lines.extend(["", "## Leverage points", ""])
        for p in position.leverage_points:
            lines.append(f"- {p}")
    lines.extend(["", "## Concessions available", ""])
    for c in position.concessions_available:
        lines.append(f"- {c}")
    return "\n".join(lines)
