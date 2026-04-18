"""Priority scoring — which deal deserves partner attention next.

Partners juggle 10-30 deals at once. This module takes a list of
PartnerReviews and ranks them so the partner's next hour goes to the
highest-value item.

Scoring factors (default weights):

- **Urgency** (30%) — deals close to a gate (bid deadline, close,
  covenant test). Pulled from an explicit `urgency_days` metadata
  field.
- **Leverage of attention** (40%) — how much the partner's input
  moves the recommendation. Measured by the number of open
  STRETCH/OUT_OF_BAND bands + CRITICAL/HIGH hits.
- **Investability** (20%) — composite 0..100 from
  `investability_scorer`. Partners prefer spending time on deals
  that might actually clear.
- **Strategic signal** (10%) — explicit `is_flagship` / `is_strategic`
  flags the deal team sets.

Returns a ranked list + per-deal commentary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .partner_review import PartnerReview


@dataclass
class PriorityInputs:
    """Extra metadata beyond the review — set by the deal team."""
    urgency_days: Optional[int] = None        # days to the next gate
    is_flagship: bool = False
    is_strategic: bool = False
    is_blocked: bool = False                  # no partner action will help
    partner_owner: Optional[str] = None       # display only


@dataclass
class PriorityScore:
    deal_id: str
    deal_name: str
    composite: float                          # 0..100
    urgency_score: float                      # 0..1
    leverage_score: float                     # 0..1
    investability_score: float                # 0..1
    strategic_score: float                    # 0..1
    partner_note: str = ""
    rank: Optional[int] = None                # populated by ranker

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "composite": self.composite,
            "urgency_score": self.urgency_score,
            "leverage_score": self.leverage_score,
            "investability_score": self.investability_score,
            "strategic_score": self.strategic_score,
            "partner_note": self.partner_note,
            "rank": self.rank,
        }


# ── Sub-scorers ────────────────────────────────────────────────────

def _urgency(inputs: Optional[PriorityInputs]) -> float:
    """Convert urgency_days into 0..1 (closer = higher)."""
    if inputs is None or inputs.urgency_days is None:
        return 0.30  # neutral-low default
    days = max(0, int(inputs.urgency_days))
    if days <= 3:
        return 1.0
    if days <= 10:
        return 0.85
    if days <= 30:
        return 0.60
    if days <= 60:
        return 0.40
    if days <= 120:
        return 0.20
    return 0.10


def _leverage_of_attention(review: PartnerReview) -> float:
    """How much partner judgment can still move the call."""
    # If the review is already clean or already doomed, low leverage.
    rec = review.narrative.recommendation
    if rec == "STRONG_PROCEED":
        return 0.20  # rubber stamp
    if rec == "PASS":
        return 0.10  # the answer's clear
    # Count open stretch/out-of-band bands + high/critical heuristics.
    stretches = sum(
        1 for b in review.reasonableness_checks
        if b.verdict in ("STRETCH", "OUT_OF_BAND")
    )
    high_plus = sum(
        1 for h in review.heuristic_hits
        if h.severity in ("HIGH", "CRITICAL")
    )
    # Scale: 1-2 items = 0.5; 3-5 = 0.75; 6+ = 1.0.
    total = stretches + high_plus
    if total >= 6:
        return 1.0
    if total >= 3:
        return 0.75
    if total >= 1:
        return 0.50
    return 0.30  # proceed-with-caveats / proceed but nothing specific


def _investability(review: PartnerReview) -> float:
    """Score 0..1 from the review's composite."""
    inv = review.investability or {}
    score = inv.get("score")
    if score is None:
        return 0.50
    try:
        return max(0.0, min(1.0, float(score) / 100.0))
    except (TypeError, ValueError):
        return 0.50


def _strategic(inputs: Optional[PriorityInputs]) -> float:
    if inputs is None:
        return 0.0
    score = 0.0
    if inputs.is_flagship:
        score += 0.6
    if inputs.is_strategic:
        score += 0.4
    return min(score, 1.0)


def _partner_note(score: PriorityScore, inputs: Optional[PriorityInputs]) -> str:
    bits: List[str] = []
    if inputs and inputs.urgency_days is not None:
        bits.append(f"{inputs.urgency_days}d to gate")
    if inputs and inputs.is_flagship:
        bits.append("flagship")
    if inputs and inputs.is_blocked:
        bits.append("blocked — no partner action helps")
    bits.append(f"composite {score.composite:.0f}")
    return "; ".join(bits)


# ── Scorer ──────────────────────────────────────────────────────────

def score_deal_priority(
    review: PartnerReview,
    inputs: Optional[PriorityInputs] = None,
    *,
    weights: Optional[Dict[str, float]] = None,
) -> PriorityScore:
    """Compute the composite priority for one deal."""
    w = {"urgency": 0.30, "leverage": 0.40,
         "investability": 0.20, "strategic": 0.10}
    if weights:
        w.update(weights)
    urgency = _urgency(inputs)
    leverage = _leverage_of_attention(review)
    if inputs is not None and inputs.is_blocked:
        leverage = 0.0
    invest = _investability(review)
    strategic = _strategic(inputs)
    composite = (w["urgency"] * urgency
                 + w["leverage"] * leverage
                 + w["investability"] * invest
                 + w["strategic"] * strategic) * 100.0
    result = PriorityScore(
        deal_id=review.deal_id,
        deal_name=review.deal_name,
        composite=round(composite, 2),
        urgency_score=round(urgency, 4),
        leverage_score=round(leverage, 4),
        investability_score=round(invest, 4),
        strategic_score=round(strategic, 4),
    )
    result.partner_note = _partner_note(result, inputs)
    return result


def rank_deal_portfolio(
    reviews_and_inputs: List[Any],
    *,
    weights: Optional[Dict[str, float]] = None,
) -> List[PriorityScore]:
    """Rank a list of (review, inputs) pairs or bare reviews.

    Accepts either ``(review, PriorityInputs)`` tuples or bare
    ``PartnerReview`` objects. Returns PriorityScore list sorted by
    composite desc, with ``.rank`` populated.
    """
    scored: List[PriorityScore] = []
    for entry in reviews_and_inputs:
        if isinstance(entry, tuple):
            review, inputs = entry
        else:
            review, inputs = entry, None
        scored.append(score_deal_priority(review, inputs, weights=weights))
    scored.sort(key=lambda s: -s.composite)
    for i, s in enumerate(scored, start=1):
        s.rank = i
    return scored


def render_priority_list_markdown(scores: List[PriorityScore]) -> str:
    lines = ["# Deal priority queue", "",
             "| Rank | Deal | Composite | Urgency | Leverage | Invest | Strategic | Note |",
             "|---:|---|---:|---:|---:|---:|---:|---|"]
    for s in scores:
        name = s.deal_name or s.deal_id or "(unnamed)"
        lines.append(
            f"| {s.rank} | {name} | {s.composite:.0f} | "
            f"{s.urgency_score:.2f} | {s.leverage_score:.2f} | "
            f"{s.investability_score:.2f} | {s.strategic_score:.2f} | "
            f"{s.partner_note} |"
        )
    return "\n".join(lines)
