"""NEW-15 Competitive positioning map.

A 2x2 bubble map of market players: x is market share, y is an attractiveness
score (claims-derived share plus a qualitative or derived score), and the bubble
area scales with revenue. Players are classified into four quadrants relative to
share and attractiveness thresholds (median of each axis by default). Clean,
partner-facing styling.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-15"

QUADRANTS = {
    (True, True): "Leaders",
    (False, True): "Challengers",
    (True, False): "Incumbents",
    (False, False): "Niche",
}


def positioning_map(
    players: Sequence[Mapping[str, Any]],
    *,
    share_threshold: Optional[float] = None,
    attractiveness_threshold: Optional[float] = None,
    source: str = "Claims-derived share and attractiveness score",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Place players on a share vs attractiveness bubble map.

    ``players``: records of {name, share, attractiveness, revenue}.
    """
    if not players:
        raise ValueError("positioning_map requires at least one player")

    shares = [float(p["share"]) for p in players]
    attrs = [float(p["attractiveness"]) for p in players]
    revs = [float(p["revenue"]) for p in players]
    max_rev = max(revs) if revs else 0.0

    s_thr = share_threshold if share_threshold is not None else statistics.median(shares)
    a_thr = attractiveness_threshold if attractiveness_threshold is not None else statistics.median(attrs)

    points: List[Dict[str, Any]] = []
    for p in players:
        share = float(p["share"])
        attr = float(p["attractiveness"])
        rev = float(p["revenue"])
        quadrant = QUADRANTS[(share >= s_thr, attr >= a_thr)]
        points.append({
            "label": str(p["name"]),
            "x": share,
            "y": attr,
            "revenue": rev,
            "bubble_size": safe_div(rev, max_rev),  # normalized to [0,1]
            "quadrant": quadrant,
        })

    bubbles_ok = all(0.0 <= pt["bubble_size"] <= 1.0 for pt in points)
    reconciliations = [
        Reconciliation(identity="normalized bubble sizes in [0, 1]",
                       lhs=1.0 if bubbles_ok else 0.0, rhs=1.0, tolerance=1e-9),
        Reconciliation(identity="largest player bubble equals 1.0",
                       lhs=max((pt["bubble_size"] for pt in points), default=0.0),
                       rhs=1.0, tolerance=1e-9),
    ]

    series = [
        Series(name="Competitive positioning", kind="bubble", points=points),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "X axis is market share, Y axis is attractiveness, bubble area scales with revenue.",
            "Quadrant thresholds default to the median of each axis.",
        ],
    )

    counts: Dict[str, int] = {}
    for pt in points:
        counts[pt["quadrant"]] = counts.get(pt["quadrant"], 0) + 1

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Competitive positioning map",
        audience=audience,
        series=series,
        footnote=footnote,
        reconciliations=reconciliations,
        summary=f"{len(points)} players. Leaders: {counts.get('Leaders', 0)}.",
        meta={
            "points": points,
            "share_threshold": s_thr,
            "attractiveness_threshold": a_thr,
            "quadrant_counts": counts,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    players = [
        {"name": "Alpha", "share": 0.40, "attractiveness": 0.8, "revenue": 100},
        {"name": "Beta", "share": 0.10, "attractiveness": 0.3, "revenue": 30},
        {"name": "Gamma", "share": 0.25, "attractiveness": 0.6, "revenue": 60},
    ]
    return positioning_map(players, share_threshold=0.30, attractiveness_threshold=0.5,
                           source="Demo player table", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Competitive positioning map",
        audience="both",
        demo=_demo,
    )
)
