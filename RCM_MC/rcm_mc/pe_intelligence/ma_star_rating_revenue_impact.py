"""MA Star Rating → QBP bonus → revenue impact.

Partner statement: "A 4-star MA plan gets 5% QBP
bonus plus rebates. Drop to 3.5 stars and you lose
most of it. For MA-heavy deals the rating trajectory
is the entire thesis. If HEDIS/CAHPS scores trended
down in the prior year, we're underwriting a rating
cliff, not growth."

Distinct from:
- `medicare_advantage_bridge_trap` — "MA will make
  it up" narrative.
- `vbc_risk_share_underwriter` — single contract
  economics.

This module maps observed star rating to QBP bonus
+ rebate capture, computes at-risk EBITDA if the
rating drops a half-star or full star.

### QBP / rebate structure

- 5 stars: 5% bonus + 70% rebate
- 4.5 stars: 5% bonus + 70% rebate
- 4 stars: 5% bonus + 65% rebate
- 3.5 stars: 0% bonus + 65% rebate
- 3 stars: 0% bonus + 50% rebate
- < 3 stars: 0% bonus + 50% rebate + restricted enrollment

### Output

- current bonus rate + rebate rate
- bonus / rebate $ on current plan revenue
- bear (half-star drop) EBITDA impact
- bull (half-star lift) EBITDA impact
- partner verdict on rating-cliff risk
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# (bonus_pct, rebate_capture_pct, note)
STAR_RATING_ECONOMICS: Dict[float, Dict[str, Any]] = {
    5.0: {"bonus": 0.05, "rebate": 0.70,
          "note": "Top tier; full bonus + rebate."},
    4.5: {"bonus": 0.05, "rebate": 0.70,
          "note": "Top tier; full bonus."},
    4.0: {"bonus": 0.05, "rebate": 0.65,
          "note": "Bonus eligible; strong position."},
    3.5: {"bonus": 0.00, "rebate": 0.65,
          "note": "Bonus lost; rebate held."},
    3.0: {"bonus": 0.00, "rebate": 0.50,
          "note": "No bonus; reduced rebate."},
    2.5: {"bonus": 0.00, "rebate": 0.50,
          "note": "Enrollment restricted zone."},
    2.0: {"bonus": 0.00, "rebate": 0.50,
          "note": "Enrollment restricted."},
}


@dataclass
class MAStarInputs:
    current_star_rating: float = 4.0
    ma_plan_revenue_m: float = 100.0
    ma_plan_ebitda_margin_pct: float = 0.10
    hedis_trend: str = "flat"
    """improving / flat / declining"""
    cahps_trend: str = "flat"


@dataclass
class MAStarReport:
    current_star_rating: float = 0.0
    current_bonus_pct: float = 0.0
    current_rebate_pct: float = 0.0
    bonus_dollars_m: float = 0.0
    rebate_dollars_m: float = 0.0
    bear_half_star_drop_ebitda_m: float = 0.0
    bull_half_star_lift_ebitda_m: float = 0.0
    rating_cliff_risk: str = "low"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_star_rating":
                self.current_star_rating,
            "current_bonus_pct":
                self.current_bonus_pct,
            "current_rebate_pct":
                self.current_rebate_pct,
            "bonus_dollars_m": self.bonus_dollars_m,
            "rebate_dollars_m": self.rebate_dollars_m,
            "bear_half_star_drop_ebitda_m":
                self.bear_half_star_drop_ebitda_m,
            "bull_half_star_lift_ebitda_m":
                self.bull_half_star_lift_ebitda_m,
            "rating_cliff_risk":
                self.rating_cliff_risk,
            "partner_note": self.partner_note,
        }


def _lookup_econ(rating: float) -> Dict[str, Any]:
    # Round to nearest half-star in catalog
    rounded = max(2.0, min(5.0, round(rating * 2) / 2))
    return STAR_RATING_ECONOMICS.get(
        rounded,
        {"bonus": 0.00, "rebate": 0.50, "note": "n/a"},
    )


def impact_ma_star_rating(
    inputs: MAStarInputs,
) -> MAStarReport:
    current = _lookup_econ(inputs.current_star_rating)
    bear_rating = max(2.0, inputs.current_star_rating - 0.5)
    bull_rating = min(5.0, inputs.current_star_rating + 0.5)
    bear = _lookup_econ(bear_rating)
    bull = _lookup_econ(bull_rating)

    bonus_dollars = (
        inputs.ma_plan_revenue_m * current["bonus"]
    )
    # Assume rebate = 15% of revenue × rebate-capture rate
    rebate_pool = inputs.ma_plan_revenue_m * 0.15
    rebate_dollars = rebate_pool * current["rebate"]

    def ebitda_from(bonus_pct: float, rebate_pct: float) -> float:
        return (
            inputs.ma_plan_revenue_m * bonus_pct +
            rebate_pool * rebate_pct
        )

    current_ebitda_contrib = ebitda_from(
        current["bonus"], current["rebate"])
    bear_ebitda_contrib = ebitda_from(
        bear["bonus"], bear["rebate"])
    bull_ebitda_contrib = ebitda_from(
        bull["bonus"], bull["rebate"])

    bear_delta = (
        bear_ebitda_contrib - current_ebitda_contrib
    )
    bull_delta = (
        bull_ebitda_contrib - current_ebitda_contrib
    )

    # Cliff risk
    declining_trends = (
        (inputs.hedis_trend == "declining") +
        (inputs.cahps_trend == "declining")
    )
    at_4_boundary = (
        3.75 <= inputs.current_star_rating <= 4.25
    )
    if at_4_boundary and declining_trends >= 1:
        risk = "high"
        note = (
            f"Plan at {inputs.current_star_rating} "
            "stars with declining HEDIS/CAHPS — "
            f"half-star drop wipes out "
            f"${abs(bear_delta):.1f}M EBITDA "
            "(bonus lost). Star rating is the thesis; "
            "verify quality-improvement program."
        )
    elif at_4_boundary:
        risk = "medium"
        note = (
            f"{inputs.current_star_rating} stars — at "
            "the 4-star boundary. Quality investments "
            "needed to hold the bonus."
        )
    elif inputs.current_star_rating >= 4.5:
        risk = "low"
        note = (
            f"{inputs.current_star_rating} stars — "
            "solid bonus + rebate position; "
            "half-star drop manageable."
        )
    elif inputs.current_star_rating <= 3.0:
        risk = "high"
        note = (
            f"{inputs.current_star_rating} stars — no "
            "bonus; restricted enrollment zone below "
            "3.0. Rating improvement is capital-"
            "intensive and multi-year."
        )
    else:
        risk = "medium"
        note = (
            f"{inputs.current_star_rating} stars — no "
            "bonus, standard rebate. Half-star lift to "
            "4 stars unlocks "
            f"${bull_delta:.1f}M EBITDA upside."
        )

    return MAStarReport(
        current_star_rating=round(
            inputs.current_star_rating, 2),
        current_bonus_pct=round(current["bonus"], 4),
        current_rebate_pct=round(current["rebate"], 4),
        bonus_dollars_m=round(bonus_dollars, 2),
        rebate_dollars_m=round(rebate_dollars, 2),
        bear_half_star_drop_ebitda_m=round(
            bear_delta, 2),
        bull_half_star_lift_ebitda_m=round(
            bull_delta, 2),
        rating_cliff_risk=risk,
        partner_note=note,
    )


def render_ma_star_markdown(
    r: MAStarReport,
) -> str:
    lines = [
        "# MA Star Rating impact",
        "",
        f"_Cliff risk: **{r.rating_cliff_risk}**_ — "
        f"{r.partner_note}",
        "",
        f"- Current rating: {r.current_star_rating:.1f}",
        f"- Bonus rate: {r.current_bonus_pct:.1%}",
        f"- Rebate capture: {r.current_rebate_pct:.1%}",
        f"- Bonus $: ${r.bonus_dollars_m:.2f}M",
        f"- Rebate $: ${r.rebate_dollars_m:.2f}M",
        f"- Bear (half-star drop): "
        f"${r.bear_half_star_drop_ebitda_m:+.2f}M",
        f"- Bull (half-star lift): "
        f"${r.bull_half_star_lift_ebitda_m:+.2f}M",
    ]
    return "\n".join(lines)
