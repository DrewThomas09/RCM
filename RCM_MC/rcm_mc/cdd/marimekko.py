"""NEW-19 Marimekko profit-pool map.

McKinsey's most distinctive healthcare exhibit: the whole industry on one
two-dimensional map. Variable-width stacked columns with no gap, where the
width of each column is a sector's share of total industry EBITDA and the
height of each rectangle within a column is a sub-segment's share of that
sector's EBITDA. A rectangle's area is therefore the sub-segment's share of
total industry EBITDA.

This is the EBITDA-share by EBITDA-share variant McKinsey uses for healthcare,
not the textbook revenue-width by margin-height market map. The classic variant
is offered as an alternate encoding when revenue and margin are supplied, for
margin-pressure diligence.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-19"

# Above this column count the area-comparison reading degrades (a documented
# marimekko limitation), so the exhibit raises a clutter flag.
CLUTTER_COLUMNS = 7


def marimekko_profit_pool(
    sectors: Sequence[Mapping[str, Any]],
    *,
    source: str = "McKinsey-style profit-pools model (101 sub-segments)",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Build the EBITDA-share by EBITDA-share marimekko.

    ``sectors``: ordered records of {sector, subsegments: {name: ebitda}}.
    A sector's EBITDA is the sum of its sub-segments. Optional ``revenue`` and
    ``margin`` per sector produce the classic revenue-width by margin-height
    alternate.
    """
    if not sectors:
        raise ValueError("marimekko_profit_pool requires at least one sector")

    rows: List[Dict[str, Any]] = []
    for sec in sectors:
        subs = {str(k): float(v) for k, v in dict(sec["subsegments"]).items()}
        ebitda = sum(subs.values())
        if ebitda <= 0:
            raise ValueError(f"sector {sec.get('sector')!r} must have positive EBITDA")
        rows.append({
            "sector": str(sec["sector"]),
            "subsegments": subs,
            "ebitda": ebitda,
            "revenue": float(sec["revenue"]) if "revenue" in sec else None,
            "margin": float(sec["margin"]) if "margin" in sec else None,
        })

    total = sum(r["ebitda"] for r in rows)

    # EBITDA-share by EBITDA-share rectangles. Width is sector share of total;
    # height within a column is sub-segment share of the sector; area is the
    # sub-segment share of total.
    rects: List[Dict[str, Any]] = []
    x0 = 0.0
    for r in rows:
        width = safe_div(r["ebitda"], total)
        x1 = x0 + width
        y0 = 0.0
        for name, sub_ebitda in r["subsegments"].items():
            height = safe_div(sub_ebitda, r["ebitda"])
            y1 = y0 + height
            rects.append({
                "sector": r["sector"],
                "subsegment": name,
                "label": f"{r['sector']}: {name}",
                "x0": x0, "x1": x1,
                "y0": y0, "y1": y1,
                "width": width,
                "height": height,
                "area": width * height,
                "ebitda": sub_ebitda,
            })
            y0 = y1
        x0 = x1

    # Classic revenue-width by margin-height alternate, one rectangle per
    # sector, when revenue and margin are present for every sector.
    alt_rects: List[Dict[str, Any]] = []
    have_classic = all(r["revenue"] is not None and r["margin"] is not None for r in rows)
    if have_classic:
        rev_total = sum(r["revenue"] for r in rows)
        ax0 = 0.0
        for r in rows:
            w = safe_div(r["revenue"], rev_total)
            ax1 = ax0 + w
            alt_rects.append({
                "sector": r["sector"],
                "label": r["sector"],
                "x0": ax0, "x1": ax1,
                "y0": 0.0, "y1": r["margin"],
                "width": w,
                "height": r["margin"],
                "revenue": r["revenue"],
                "margin": r["margin"],
            })
            ax0 = ax1

    flags: List[Flag] = []
    if len(rows) > CLUTTER_COLUMNS:
        flags.append(Flag(
            code="too_many_columns",
            severity="warn",
            message=(
                f"{len(rows)} sectors exceed the {CLUTTER_COLUMNS}-column "
                "readability limit for a marimekko. Area comparisons get hard "
                "to read; consider grouping smaller sectors."
            ),
            source=source,
        ))

    reconciliations = [
        Reconciliation(
            identity="sector widths sum to 1.0",
            lhs=sum(safe_div(r["ebitda"], total) for r in rows),
            rhs=1.0,
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="rectangle areas sum to 1.0",
            lhs=sum(rc["area"] for rc in rects),
            rhs=1.0,
            tolerance=1e-9,
        ),
    ]

    series = [Series(name="Profit-pool map", kind="bar", points=rects)]
    if alt_rects:
        series.append(Series(name="Revenue width by margin height", kind="bar",
                             points=alt_rects))

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Column width is a sector's share of total industry EBITDA.",
            "Rectangle height is a sub-segment's share of its sector's EBITDA.",
            "Rectangle area is the sub-segment's share of total industry EBITDA.",
            "Area comparisons are imprecise; labels carry the exact values.",
        ],
    )

    widest = max(rows, key=lambda r: r["ebitda"])
    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Profit-pool map",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(rows)} sectors, {len(rects)} sub-segments. Widest sector "
            f"{widest['sector']} at {safe_div(widest['ebitda'], total)*100:.1f} "
            "percent of industry EBITDA."
        ),
        meta={
            "total_ebitda": total,
            "rects": rects,
            "alt_rects": alt_rects,
            "sector_widths": {r["sector"]: safe_div(r["ebitda"], total) for r in rows},
            "n_sectors": len(rows),
            "n_subsegments": len(rects),
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # Widths match the published 2017/18 map: payers 10 percent, delivery 50,
    # service vendors 5, manufacturers and distributors 35 percent of EBITDA.
    sectors = [
        {"sector": "Payers", "subsegments": {"Medicare Advantage": 6, "Individual": 4}},
        {"sector": "Delivery systems", "subsegments": {"Acute care": 30, "ASCs": 20}},
        {"sector": "Service vendors", "subsegments": {"Software and platforms": 3, "Data and analytics": 2}},
        {"sector": "Manufacturers and distributors", "subsegments": {"Pharma": 25, "Distribution": 10}},
    ]
    return marimekko_profit_pool(
        sectors,
        source="Demo profit-pool map shaped to the 2017/18 report widths",
        vintage="2018",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Marimekko profit-pool map",
        audience="both",
        demo=_demo,
    )
)
