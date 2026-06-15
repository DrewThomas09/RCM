"""NEW-20 Historic-versus-projected growth archetype map.

McKinsey plots each profit-pool sub-segment by historic growth (x) against
projected growth (y), with bubble size set by pool size. Quadrant lines at a
growth threshold sort sub-segments into sustained growers, accelerators,
decelerators, and laggards. The exhibit also reports the share of EBITDA that
sits in pools projected to grow above the threshold, and notes that historic
and projected growth are only loosely correlated.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-20"
DEFAULT_THRESHOLD = 0.05  # 5 percent growth quadrant line

QUADRANTS = {
    (True, True): "Sustained growth",
    (False, True): "Accelerators",
    (True, False): "Decelerators",
    (False, False): "Laggards",
}


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return None  # zero variance on an axis


def growth_archetype(
    subsegments: Sequence[Mapping[str, Any]],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    source: str = "McKinsey-style profit-pools model (101 sub-segments)",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Sort sub-segments into growth archetypes and size the high-growth share.

    ``subsegments``: records of {name, historic, projected, ebitda, vertical?}.
    ``historic`` and ``projected`` are growth rates as decimals.
    """
    if not subsegments:
        raise ValueError("growth_archetype requires at least one sub-segment")

    rows: List[Dict[str, Any]] = []
    for s in subsegments:
        rows.append({
            "name": str(s["name"]),
            "historic": float(s["historic"]),
            "projected": float(s["projected"]),
            "ebitda": float(s["ebitda"]),
            "vertical": str(s.get("vertical", "")),
        })

    total = sum(r["ebitda"] for r in rows)
    if total <= 0:
        raise ValueError("total EBITDA must be positive")
    max_ebitda = max(r["ebitda"] for r in rows)

    points: List[Dict[str, Any]] = []
    quadrant_ebitda: Dict[str, float] = {q: 0.0 for q in QUADRANTS.values()}
    for r in rows:
        quad = QUADRANTS[(r["historic"] >= threshold, r["projected"] >= threshold)]
        quadrant_ebitda[quad] += r["ebitda"]
        points.append({
            "label": r["name"],
            "x": r["historic"],
            "y": r["projected"],
            "ebitda": r["ebitda"],
            "bubble_size": safe_div(r["ebitda"], max_ebitda),
            "quadrant": quad,
            "vertical": r["vertical"],
        })

    high_growth_ebitda = sum(r["ebitda"] for r in rows if r["projected"] >= threshold)
    high_growth_share = safe_div(high_growth_ebitda, total)

    # The report's observation: high-growth pools tend to be small. Compare the
    # average pool size above the line to the average below it.
    above = [r["ebitda"] for r in rows if r["projected"] >= threshold]
    below = [r["ebitda"] for r in rows if r["projected"] < threshold]
    flags: List[Flag] = []
    if above and below and (sum(above) / len(above)) < (sum(below) / len(below)):
        flags.append(Flag(
            code="high_growth_pools_small",
            severity="info",
            message=(
                "High-growth pools are smaller on average than slow-growth "
                "pools, so the growth is concentrated in small segments."
            ),
            source=source,
        ))

    corr = _pearson([r["historic"] for r in rows], [r["projected"] for r in rows])

    reconciliations = [
        Reconciliation(
            identity="quadrant EBITDA sums to total EBITDA",
            lhs=sum(quadrant_ebitda.values()),
            rhs=total,
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="largest bubble equals 1.0",
            lhs=max(p["bubble_size"] for p in points),
            rhs=1.0,
            tolerance=1e-9,
        ),
    ]

    series = [Series(name="Historic versus projected growth", kind="bubble",
                     points=points)]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "X axis is historic growth, Y axis is projected growth, bubble area scales with EBITDA.",
            f"Quadrant lines sit at {threshold*100:.0f} percent growth on both axes.",
            "Projected growth is an estimate, not an actual.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Historic versus projected growth map",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(rows)} sub-segments. {high_growth_share*100:.1f} percent of "
            f"EBITDA sits in pools projected above {threshold*100:.0f} percent growth."
        ),
        meta={
            "threshold": threshold,
            "points": points,
            "quadrant_ebitda": quadrant_ebitda,
            "quadrant_share": {q: safe_div(v, total) for q, v in quadrant_ebitda.items()},
            "high_growth_share": high_growth_share,
            "correlation": corr,
            "total_ebitda": total,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    subsegments = [
        {"name": "HST data and analytics", "historic": 0.03, "projected": 0.12, "ebitda": 49, "vertical": "HST"},
        {"name": "Health systems", "historic": 0.08, "projected": 0.10, "ebitda": 250, "vertical": "Providers"},
        {"name": "Payer Individual", "historic": 0.06, "projected": 0.02, "ebitda": 60, "vertical": "Payers"},
        {"name": "Legacy pharmacy", "historic": 0.01, "projected": 0.01, "ebitda": 30, "vertical": "Pharmacy"},
    ]
    return growth_archetype(subsegments, source="Demo sub-segment growth table",
                            vintage="2024")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Historic versus projected growth archetype map",
        audience="both",
        demo=_demo,
    )
)
