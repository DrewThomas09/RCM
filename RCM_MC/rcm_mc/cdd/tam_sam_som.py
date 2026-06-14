"""NEW-01 Bottom-up TAM/SAM/SOM engine.

SOM is built from sales capacity times a realistic win rate, never a flat
percentage of TAM. Every assumption (win rate, sales capacity, per-segment
penetration and price) is an explicit, named, editable, sourced node. The
engine reconciles the bottom-up total against an optional top-down market
figure and flags divergence above a stated tolerance (default 20%).

Definitions:
- TAM: every addressable unit at its price, across all segments.
- SAM: the reachable segments only (serviceable addressable market).
- Demand ceiling: reachable units times their realistic penetration rate.
- SOM: capacity-constrained capture, min(sales_capacity * win_rate priced at
  the blended reachable price, demand ceiling). Capacity, not a flat TAM cut.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .exhibit import (
    AssumptionNode,
    Exhibit,
    Flag,
    Footnote,
    Reconciliation,
    Series,
    safe_div,
)
from .registry import CddFeature, register

FEATURE_ID = "NEW-01"
DEFAULT_DIVERGENCE_TOLERANCE = 0.20


def tam_sam_som(
    segments: Sequence[Dict[str, Any]],
    *,
    sales_capacity_units: float,
    win_rate: float,
    top_down: Optional[float] = None,
    source: str = "Target data room",
    vintage: str = "",
    capacity_source: str = "Sales plan, reps x quota",
    win_rate_source: str = "Historical close rate",
    divergence_tolerance: float = DEFAULT_DIVERGENCE_TOLERANCE,
    audience: str = "both",
) -> Exhibit:
    """Compute TAM, SAM, SOM bottom-up and reconcile to a top-down figure.

    ``segments``: rows of {segment, unit_count, price, penetration_rate,
    reachable(optional bool, default True)}.
    """
    if not segments:
        raise ValueError("tam_sam_som requires at least one segment")
    if not (0.0 <= win_rate <= 1.0):
        raise ValueError(f"win_rate must be in [0, 1], got {win_rate}")
    if sales_capacity_units < 0:
        raise ValueError("sales_capacity_units must be non-negative")

    flags: List[Flag] = []
    assumptions: List[AssumptionNode] = [
        AssumptionNode(
            key="win_rate",
            label="Realistic sales win rate",
            value=float(win_rate),
            source=win_rate_source,
            unit="share",
        ),
        AssumptionNode(
            key="sales_capacity_units",
            label="Annual sales capacity in units",
            value=float(sales_capacity_units),
            source=capacity_source,
            unit="units",
        ),
    ]

    tam = 0.0
    sam_rev = 0.0
    sam_units = 0.0
    demand_ceiling = 0.0
    seg_points: List[Dict[str, Any]] = []
    for i, seg in enumerate(segments):
        name = str(seg["segment"])
        units = float(seg["unit_count"])
        price = float(seg["price"])
        pen = float(seg.get("penetration_rate", 1.0))
        reachable = bool(seg.get("reachable", True))
        if units < 0 or price < 0:
            raise ValueError(f"segment {name}: unit_count and price must be non-negative")
        if not (0.0 <= pen <= 1.0):
            raise ValueError(f"segment {name}: penetration_rate must be in [0, 1]")

        seg_tam = units * price
        tam += seg_tam
        if reachable:
            sam_rev += seg_tam
            sam_units += units
            demand_ceiling += units * pen * price

        assumptions.append(
            AssumptionNode(
                key=f"penetration_{i}",
                label=f"Penetration ceiling, {name}",
                value=pen,
                source=source,
                unit="share",
            )
        )
        assumptions.append(
            AssumptionNode(
                key=f"price_{i}",
                label=f"Unit price, {name}",
                value=price,
                source=source,
                unit="currency",
            )
        )
        seg_points.append(
            {
                "segment": name,
                "unit_count": units,
                "price": price,
                "penetration_rate": pen,
                "reachable": reachable,
                "segment_tam": seg_tam,
            }
        )

    blended_reachable_price = safe_div(sam_rev, sam_units, default=0.0)
    winnable_units = sales_capacity_units * win_rate
    som_capacity = winnable_units * blended_reachable_price
    som = min(som_capacity, demand_ceiling)

    # Ordering sanity. SOM <= SAM <= TAM must hold by construction.
    if not (som <= sam_rev + 1e-9 <= tam + 1e-9):
        flags.append(
            Flag(
                code="ordering_violation",
                severity="warn",
                message="SOM, SAM, TAM ordering did not hold. Check inputs.",
            )
        )
    if som_capacity > demand_ceiling + 1e-9:
        flags.append(
            Flag(
                code="capacity_exceeds_demand",
                severity="info",
                message=(
                    "Sales capacity exceeds the demand ceiling, so SOM is "
                    "demand-constrained rather than capacity-constrained."
                ),
            )
        )

    reconciliations: List[Reconciliation] = []
    if top_down is not None and top_down > 0:
        divergence = safe_div(abs(tam - top_down), max(tam, top_down), default=0.0)
        reconciliations.append(
            Reconciliation(
                identity="abs(bottom_up_TAM - top_down)/max(.) <= tolerance",
                lhs=divergence,
                rhs=0.0,
                tolerance=divergence_tolerance,
            )
        )
        if divergence > divergence_tolerance:
            flags.append(
                Flag(
                    code="tam_divergence",
                    severity="risk",
                    message=(
                        f"Bottom-up TAM and top-down market figure diverge by "
                        f"{divergence * 100:.1f} percent, above the "
                        f"{divergence_tolerance * 100:.0f} percent tolerance."
                    ),
                    source=source,
                )
            )

    series = [
        Series(
            name="TAM / SAM / SOM",
            kind="bar",
            points=[
                {"label": "TAM", "value": tam},
                {"label": "SAM", "value": sam_rev},
                {"label": "SOM", "value": som},
            ],
        ),
        Series(name="Segments", kind="bar", points=seg_points, internal_only=True),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "SOM is capacity-constrained, sales capacity times win rate, not a flat TAM cut.",
            "SAM counts reachable segments only.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Market sizing: TAM, SAM, SOM",
        audience=audience,
        series=series,
        footnote=footnote,
        assumptions=assumptions,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"TAM {tam:,.0f}, SAM {sam_rev:,.0f}, SOM {som:,.0f}. "
            f"SOM from {winnable_units:,.0f} winnable units at a blended "
            f"reachable price of {blended_reachable_price:,.2f}."
        ),
        meta={
            "tam": tam,
            "sam": sam_rev,
            "som": som,
            "som_capacity": som_capacity,
            "demand_ceiling": demand_ceiling,
            "blended_reachable_price": blended_reachable_price,
            "winnable_units": winnable_units,
            "top_down": top_down,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    segments = [
        {"segment": "Hospital outpatient", "unit_count": 1000, "price": 10.0, "penetration_rate": 0.5},
        {"segment": "ASC", "unit_count": 500, "price": 20.0, "penetration_rate": 0.4},
        {"segment": "Office, non-reachable", "unit_count": 2000, "price": 5.0, "penetration_rate": 0.3, "reachable": False},
    ]
    return tam_sam_som(
        segments,
        sales_capacity_units=600,
        win_rate=0.5,
        top_down=33000.0,
        source="Demo data room",
        vintage="2026",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Bottom-up TAM/SAM/SOM engine",
        audience="both",
        demo=_demo,
    )
)
