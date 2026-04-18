"""Service line growth × margin quadrant — star / cash cow / question / dog.

Partner statement: "For a multi-service-line deal,
put each line on the growth × margin 2x2. Stars are
high-growth high-margin (invest). Cash cows are
low-growth high-margin (harvest for capital).
Question marks are high-growth low-margin (invest
with caution). Dogs are low-growth low-margin
(divest or starve). The portfolio conversation is
which to feed and which to starve."

Distinct from:
- `service_line_analysis` — concentration + HHI.
- `subsector_ebitda_margin_benchmark` — single-
  subsector margin band.

This module **classifies each line** across two
thresholds and outputs a partner verdict for each.

### Thresholds

- growth: >= 7% = high growth
- margin: >= 20% = high margin

### Quadrants

- star → invest
- cash_cow → harvest
- question_mark → invest_with_caution
- dog → divest_or_starve
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


GROWTH_THRESHOLD = 0.07
MARGIN_THRESHOLD = 0.20


@dataclass
class ServiceLine:
    name: str
    revenue_m: float
    growth_rate_pct: float
    ebitda_margin_pct: float


@dataclass
class QuadrantInputs:
    service_lines: List[ServiceLine] = field(
        default_factory=list)


@dataclass
class LineClassification:
    name: str
    revenue_m: float
    growth_rate_pct: float
    ebitda_margin_pct: float
    quadrant: str
    recommendation: str


@dataclass
class QuadrantReport:
    classifications: List[LineClassification] = field(
        default_factory=list)
    stars_revenue_m: float = 0.0
    cash_cows_revenue_m: float = 0.0
    question_marks_revenue_m: float = 0.0
    dogs_revenue_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classifications": [
                {"name": c.name,
                 "revenue_m": c.revenue_m,
                 "growth_rate_pct": c.growth_rate_pct,
                 "ebitda_margin_pct":
                     c.ebitda_margin_pct,
                 "quadrant": c.quadrant,
                 "recommendation": c.recommendation}
                for c in self.classifications
            ],
            "stars_revenue_m": self.stars_revenue_m,
            "cash_cows_revenue_m":
                self.cash_cows_revenue_m,
            "question_marks_revenue_m":
                self.question_marks_revenue_m,
            "dogs_revenue_m": self.dogs_revenue_m,
            "partner_note": self.partner_note,
        }


def _classify(
    growth: float, margin: float,
) -> tuple:
    high_g = growth >= GROWTH_THRESHOLD
    high_m = margin >= MARGIN_THRESHOLD
    if high_g and high_m:
        return (
            "star",
            "invest — fund growth; this line drives "
            "multiple at exit",
        )
    if not high_g and high_m:
        return (
            "cash_cow",
            "harvest — fund other investments; don't "
            "starve if share is dominant",
        )
    if high_g and not high_m:
        return (
            "question_mark",
            "invest with caution — if margin improves "
            "it becomes a star; if not, it becomes a "
            "dog",
        )
    return (
        "dog",
        "divest or starve — free up management capacity",
    )


def classify_service_line_portfolio(
    inputs: QuadrantInputs,
) -> QuadrantReport:
    if not inputs.service_lines:
        return QuadrantReport(
            partner_note=(
                "No service lines provided — "
                "classification requires per-line "
                "revenue, growth, margin."),
        )

    classifications: List[LineClassification] = []
    buckets = {
        "star": 0.0,
        "cash_cow": 0.0,
        "question_mark": 0.0,
        "dog": 0.0,
    }
    for sl in inputs.service_lines:
        q, rec = _classify(
            sl.growth_rate_pct, sl.ebitda_margin_pct)
        classifications.append(LineClassification(
            name=sl.name,
            revenue_m=round(sl.revenue_m, 2),
            growth_rate_pct=round(sl.growth_rate_pct, 4),
            ebitda_margin_pct=round(
                sl.ebitda_margin_pct, 4),
            quadrant=q,
            recommendation=rec,
        ))
        buckets[q] += sl.revenue_m

    classifications.sort(
        key=lambda c: c.revenue_m, reverse=True)

    total = sum(buckets.values())
    if total == 0:
        star_pct = cow_pct = q_pct = dog_pct = 0.0
    else:
        star_pct = buckets["star"] / total
        cow_pct = buckets["cash_cow"] / total
        q_pct = buckets["question_mark"] / total
        dog_pct = buckets["dog"] / total

    if star_pct + cow_pct >= 0.60:
        note = (
            f"Portfolio dominated by stars "
            f"({star_pct:.0%}) + cash cows "
            f"({cow_pct:.0%}). Healthy mix — fund the "
            "stars, harvest the cows."
        )
    elif q_pct >= 0.30:
        note = (
            f"Question marks = {q_pct:.0%} of revenue. "
            "Execution-dependent mix — the question is "
            "which convert to stars; operating-partner "
            "cadence matters."
        )
    elif dog_pct >= 0.30:
        note = (
            f"Dogs = {dog_pct:.0%} of revenue. "
            "Portfolio drag; operating plan must "
            "either fix margin / growth or divest."
        )
    else:
        note = (
            f"Balanced mix — stars {star_pct:.0%}, "
            f"cash cows {cow_pct:.0%}, questions "
            f"{q_pct:.0%}, dogs {dog_pct:.0%}. "
            "Standard management attention."
        )

    return QuadrantReport(
        classifications=classifications,
        stars_revenue_m=round(buckets["star"], 2),
        cash_cows_revenue_m=round(
            buckets["cash_cow"], 2),
        question_marks_revenue_m=round(
            buckets["question_mark"], 2),
        dogs_revenue_m=round(buckets["dog"], 2),
        partner_note=note,
    )


def render_service_line_quadrant_markdown(
    r: QuadrantReport,
) -> str:
    lines = [
        "# Service line growth × margin quadrant",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Stars: ${r.stars_revenue_m:.1f}M",
        f"- Cash cows: ${r.cash_cows_revenue_m:.1f}M",
        f"- Question marks: "
        f"${r.question_marks_revenue_m:.1f}M",
        f"- Dogs: ${r.dogs_revenue_m:.1f}M",
        "",
        "| Line | Revenue | Growth | Margin | Quadrant | Action |",
        "|---|---|---|---|---|---|",
    ]
    for c in r.classifications:
        lines.append(
            f"| {c.name} | ${c.revenue_m:.1f}M | "
            f"{c.growth_rate_pct:+.1%} | "
            f"{c.ebitda_margin_pct:.0%} | "
            f"{c.quadrant} | {c.recommendation} |"
        )
    return "\n".join(lines)
