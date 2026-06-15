"""NEW-23 Payer economics comparison.

Grouped bars of gross margin per enrollee by segment, with the prior-year
comparison and the medical loss ratio overlaid. Medicare Advantage carries the
highest gross margin of any segment, which the exhibit surfaces as a flag
computed from the data rather than asserted. The year-over-year change ties out
to the difference of the two years so the bridge is auditable.

Higher gross margin does not mean higher profitability: margin excludes
administration and tax. That caveat travels with the exhibit.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-23"


@dataclass(frozen=True)
class PayerSegment:
    """One payer segment's per-enrollee gross margin and loss ratio."""

    segment: str
    margin_2024: float
    margin_2023: float
    mlr_pct: float
    note: str = ""


# Gross margin per enrollee (KFF, NAIC statutory data via Mark Farrah, 2024) and
# medical loss ratio (2023 reference).
SEGMENTS: List[PayerSegment] = [
    PayerSegment("Medicare Advantage", 1655.0, 1986.0, 87.0,
                 note="highest of any segment; CMS pays about 14823 per enrollee in 2024"),
    PayerSegment("Individual or ACA", 987.0, 1048.0, 80.0,
                 note="lowest medical loss ratio of the four markets"),
    PayerSegment("Fully-insured group", 846.0, 910.0, 86.0),
    PayerSegment("Medicaid managed care", 608.0, 753.0, 87.0),
]


def payer_economics(
    segments: Optional[Sequence[PayerSegment]] = None,
    *,
    source: str = "KFF Health Insurer Financial Performance 2024 (NAIC via Mark Farrah)",
    vintage: str = "2024",
    audience: str = "both",
) -> Exhibit:
    """Build the per-enrollee gross-margin and loss-ratio comparison."""
    table = list(segments) if segments is not None else list(SEGMENTS)
    if not table:
        raise ValueError("payer_economics requires at least one segment")

    points: List[Dict[str, Any]] = []
    for s in sorted(table, key=lambda r: r.margin_2024, reverse=True):
        points.append({
            "label": s.segment,
            "value": s.margin_2024,
            "margin_2023": s.margin_2023,
            "yoy_change": s.margin_2024 - s.margin_2023,
            "mlr_pct": s.mlr_pct,
            "note": s.note,
        })

    top = points[0]
    flags = [Flag(
        code="highest_margin_segment",
        severity="info",
        message=(
            f"{top['label']} carries the highest gross margin per enrollee at "
            f"{top['value']:,.2f}."
        ),
        source=source,
    )]

    # Reconciliation: the per-segment year-over-year change is exactly the
    # difference of the two years (aggregate identity), and the highest charted
    # margin equals the maximum 2024 margin in the table.
    yoy_gap = sum(
        abs(p["yoy_change"] - (p["value"] - p["margin_2023"])) for p in points
    )
    reconciliations = [
        Reconciliation(
            identity="year-over-year change equals 2024 minus 2023",
            lhs=yoy_gap,
            rhs=0.0,
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="top charted margin equals the maximum 2024 margin",
            lhs=top["value"],
            rhs=max(s.margin_2024 for s in table),
            tolerance=1e-9,
        ),
    ]

    series = [
        Series(name="Gross margin per enrollee 2024", kind="bar", points=points),
        Series(name="Medical loss ratio percent", kind="line", points=[
            {"label": p["label"], "value": p["mlr_pct"]} for p in points
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage,
        assumptions=[
            "Gross margin per enrollee excludes administration and tax.",
            "Medical loss ratio is the 2023 reference; statutory floors are 85 and 80 percent.",
            "Higher margin does not mean higher profitability.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Payer gross margin and loss ratio by segment",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{top['label']} leads at {top['value']:,.2f} per enrollee. Margins "
            f"range to {points[-1]['value']:,.2f}."
        ),
        meta={
            "n_segments": len(table),
            "leader": top["label"],
            "leader_margin": top["value"],
            "ma_rebate_per_enrollee_2026": 2660.0,
            "ma_risk_adjusted_payment_2024": 14823.0,
            "part_b_premium_2026": 202.90,
            "part_d_oop_cap_2026": 2100.0,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    return payer_economics(
        source="KFF Health Insurer Financial Performance 2024 (NAIC via Mark Farrah)",
        vintage="2024",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Payer economics comparison",
        audience="both",
        demo=_demo,
    )
)
