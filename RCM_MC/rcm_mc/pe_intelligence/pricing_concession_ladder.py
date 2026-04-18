"""Pricing concession ladder — the sequence before walking.

Partner statement: "I never give price first. I give
structure, reps, indemnity, then earn-out, then peg —
and price last. Every concession costs something
different, and the cheapest ones move first."

`negotiation_position.py` gives a read on our position.
This module produces the **actual sequence** of concessions
a partner should make across rounds, tuned to:

- **Seller motivation** — from `seller_motivation_decoder`.
- **Pattern matches** — from `cross_pattern_digest`.
- **Seller's current demands** — what they've asked for
  that we haven't conceded yet.
- **Buyer walk-away line** — the price below which we've
  priced out of thesis.

### Concession cost hierarchy (partner rule of thumb)

In healthcare-services PE, concessions are valued
roughly in this order (cheapest for buyer first):

1. **Earn-out structure** — defers price to performance.
   Cheap if we're confident in execution; expensive if
   we think seller will game EBITDA.
2. **Working-capital peg** — 2-3% peg buffer costs little
   vs. principal.
3. **Interim covenants tightness** — free to us pre-close.
4. **R&W insurance mechanics** — carriers price this;
   modest cost.
5. **Reps & warranties scope** — material scope costs
   nothing if asset is clean.
6. **Indemnity cap / basket** — costs buyer basis points
   in premium + escrow.
7. **Rollover equity** — gives seller upside; cheap if we
   believe the deal, expensive if we don't.
8. **Structure (installment / contingent)** — buyer tax +
   capital efficiency cost.
9. **Price** — the nuclear concession. Give last.

### Walk-away line

Concession sequence terminates at the **buyer walk-away
price**. If seller ask > walk-away after all concessions
exhausted, partner walks.

### Output

`ConcessionLadder` with ordered list of moves, each
tagged with:
- **cost_to_buyer** — "low" / "medium" / "high"
- **seller_pain** — "low" / "medium" / "high"
- **recommended_round** — 1 (opening) / 2 / 3 / final
- **partner_rationale** — why this move, why this round
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Concession library keyed by move name. Each entry captures
# partner-standard cost + seller-pain rating.
CONCESSION_CATALOG: Dict[str, Dict[str, Any]] = {
    "earnout_structure": {
        "description": (
            "Move portion of price to performance-based "
            "earn-out."
        ),
        "cost_to_buyer": "low",
        "seller_pain": "medium",
        "default_round": 1,
        "partner_rationale": (
            "Earn-out converts price-argument into "
            "execution-argument. Cheap to offer if we "
            "trust execution."
        ),
    },
    "working_capital_peg": {
        "description": (
            "Adjust WC peg by ±2-3% in seller's favor."
        ),
        "cost_to_buyer": "low",
        "seller_pain": "low",
        "default_round": 1,
        "partner_rationale": (
            "Trivial dollar cost; signals cooperation."
        ),
    },
    "interim_covenants": {
        "description": (
            "Loosen interim operating covenants."
        ),
        "cost_to_buyer": "low",
        "seller_pain": "low",
        "default_round": 2,
        "partner_rationale": (
            "Costs us nothing pre-close unless seller "
            "materially changes the asset."
        ),
    },
    "rw_insurance_mechanics": {
        "description": (
            "Adjust R&W cap, deductible, or exclusion "
            "list in seller's favor."
        ),
        "cost_to_buyer": "medium",
        "seller_pain": "low",
        "default_round": 2,
        "partner_rationale": (
            "Carriers price mechanics adjustments; buyer "
            "absorbs premium delta."
        ),
    },
    "reps_and_warranties_scope": {
        "description": (
            "Narrow scope of specific reps (environmental, "
            "IT, employment)."
        ),
        "cost_to_buyer": "medium",
        "seller_pain": "medium",
        "default_round": 3,
        "partner_rationale": (
            "Free if asset is clean; risk-transfer if not."
        ),
    },
    "indemnity_cap_basket": {
        "description": (
            "Lower indemnity cap or raise basket threshold."
        ),
        "cost_to_buyer": "medium",
        "seller_pain": "medium",
        "default_round": 3,
        "partner_rationale": (
            "Mostly R&W-insured above basket; partner "
            "eats tail risk for price stability."
        ),
    },
    "rollover_equity_increase": {
        "description": (
            "Accept larger seller rollover at close."
        ),
        "cost_to_buyer": "medium",
        "seller_pain": "low",
        "default_round": 3,
        "partner_rationale": (
            "Aligns incentives; cheap if we believe in "
            "the asset. Expensive if rollover dilutes "
            "our stake."
        ),
    },
    "installment_structure": {
        "description": (
            "Move portion of price to deferred payment / "
            "seller note."
        ),
        "cost_to_buyer": "high",
        "seller_pain": "medium",
        "default_round": 4,
        "partner_rationale": (
            "Capital-efficient but creates future claim "
            "and financing complications."
        ),
    },
    "price_bump": {
        "description": (
            "Raise headline enterprise value."
        ),
        "cost_to_buyer": "high",
        "seller_pain": "low",
        "default_round": 4,
        "partner_rationale": (
            "Nuclear concession — give last, give small, "
            "and only against reciprocal seller concession."
        ),
    },
}


@dataclass
class ConcessionInputs:
    buyer_walk_away_price_m: float
    current_seller_ask_m: float
    buyer_base_offer_m: float
    open_seller_demands: List[str] = field(default_factory=list)
    seller_motivation: str = ""                # from decoder
    seller_urgency: str = "medium"             # low/medium/high
    pattern_matches: List[str] = field(default_factory=list)
    # Optional: explicit moves the partner has already made
    # (exclude from ladder).
    already_conceded: List[str] = field(default_factory=list)


@dataclass
class ConcessionMove:
    name: str
    description: str
    cost_to_buyer: str
    seller_pain: str
    recommended_round: int
    partner_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "cost_to_buyer": self.cost_to_buyer,
            "seller_pain": self.seller_pain,
            "recommended_round": self.recommended_round,
            "partner_rationale": self.partner_rationale,
        }


@dataclass
class ConcessionLadder:
    moves: List[ConcessionMove] = field(default_factory=list)
    walk_away_price_m: float = 0.0
    gap_vs_seller_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "moves": [m.to_dict() for m in self.moves],
            "walk_away_price_m": self.walk_away_price_m,
            "gap_vs_seller_m": self.gap_vs_seller_m,
            "partner_note": self.partner_note,
        }


def _adjust_rounds_by_motivation(
    motivation: str,
    urgency: str,
    moves: List[ConcessionMove],
) -> List[ConcessionMove]:
    """High-urgency sellers compress the ladder.
    Price-sensitive sellers accept structure moves over
    headline price.
    """
    if urgency == "high":
        # Compress ladder: everything shifts up one round.
        for m in moves:
            m.recommended_round = max(1, m.recommended_round - 1)
    if motivation == "family_liquidity":
        # Family-liquidity prefers cash — price bump may be
        # unavoidable earlier.
        for m in moves:
            if m.name == "price_bump":
                m.recommended_round = 3
            if m.name == "earnout_structure":
                m.recommended_round = 4  # family resists
    elif motivation == "sponsor_vintage_end":
        # LP-scorecard — hold price hard, accept R&W
        # aggressively.
        for m in moves:
            if m.name == "rw_insurance_mechanics":
                m.recommended_round = 1
            if m.name == "price_bump":
                m.recommended_round = 4
    elif motivation == "covenant_trip_imminent":
        # Distressed — ladder collapses; price move fast.
        for m in moves:
            if m.name == "price_bump":
                m.recommended_round = max(2, m.recommended_round - 1)
    return moves


def build_concession_ladder(
    inputs: ConcessionInputs,
) -> ConcessionLadder:
    gap = inputs.current_seller_ask_m - inputs.buyer_base_offer_m
    walk_buffer = inputs.buyer_walk_away_price_m \
        - inputs.buyer_base_offer_m
    moves: List[ConcessionMove] = []

    # Build full catalog, skip already-conceded.
    for name, cfg in CONCESSION_CATALOG.items():
        if name in inputs.already_conceded:
            continue
        moves.append(ConcessionMove(
            name=name,
            description=cfg["description"],
            cost_to_buyer=cfg["cost_to_buyer"],
            seller_pain=cfg["seller_pain"],
            recommended_round=cfg["default_round"],
            partner_rationale=cfg["partner_rationale"],
        ))

    moves = _adjust_rounds_by_motivation(
        inputs.seller_motivation,
        inputs.seller_urgency,
        moves,
    )

    # Sort by recommended round then cost-to-buyer.
    cost_rank = {"low": 0, "medium": 1, "high": 2}
    moves.sort(
        key=lambda m: (
            m.recommended_round,
            cost_rank.get(m.cost_to_buyer, 1),
        )
    )

    # Partner note.
    if inputs.current_seller_ask_m > inputs.buyer_walk_away_price_m:
        over_walk = inputs.current_seller_ask_m \
            - inputs.buyer_walk_away_price_m
        note = (
            f"Seller ask ${inputs.current_seller_ask_m:,.0f}M is "
            f"${over_walk:,.0f}M above walk-away "
            f"${inputs.buyer_walk_away_price_m:,.0f}M. Ladder "
            "delays walk; every concession must close that gap "
            "or save equivalent structure."
        )
    elif gap / max(0.01, inputs.buyer_base_offer_m) > 0.10:
        note = (
            f"Ask ${gap:,.0f}M above base offer ({gap/inputs.buyer_base_offer_m*100:.0f}%). "
            "Standard ladder; use structure moves before price."
        )
    elif gap > 0:
        note = (
            f"Small gap ${gap:,.0f}M. One or two concessions "
            "should close. Lead with low-cost structure moves."
        )
    else:
        note = (
            "Seller at or below our base offer. No concessions "
            "required on price; tighten structure to our benefit."
        )

    return ConcessionLadder(
        moves=moves,
        walk_away_price_m=inputs.buyer_walk_away_price_m,
        gap_vs_seller_m=round(gap, 2),
        partner_note=note,
    )


def render_concession_ladder_markdown(
    l: ConcessionLadder,
) -> str:
    lines = [
        "# Pricing concession ladder",
        "",
        f"_{l.partner_note}_",
        "",
        f"- Walk-away price: ${l.walk_away_price_m:,.0f}M",
        f"- Gap vs seller: ${l.gap_vs_seller_m:,.0f}M",
        "",
        "| Round | Move | Cost to buyer | Seller pain | "
        "Rationale |",
        "|---|---|---|---|---|",
    ]
    for m in l.moves:
        lines.append(
            f"| R{m.recommended_round} | {m.name} | "
            f"{m.cost_to_buyer} | {m.seller_pain} | "
            f"{m.partner_rationale} |"
        )
    return "\n".join(lines)


def list_concession_catalog() -> List[str]:
    return list(CONCESSION_CATALOG.keys())
