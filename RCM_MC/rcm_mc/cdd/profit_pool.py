"""NEW-18 Profit-pool stacked-column exhibit.

McKinsey's franchise healthcare exhibit: industry economic health measured in
EBITDA ("profit pools") by major segment over time, with explicit forward
CAGRs. Years sit on the x axis (a historical anchor, a current year, a
projected year); EBITDA in dollars stacks into payers, providers, health
services and technology (HST), and pharmacy; the total is labeled atop each
column; CAGR brackets connect the columns; projected columns are ghosted.

A framing-metric variant expresses industry EBITDA as a percentage of national
health expenditure (NHE) when an NHE series is supplied.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div

from .registry import CddFeature, register

FEATURE_ID = "NEW-18"


def _cagr(start: float, end: float, years: float) -> Optional[float]:
    """Compound annual growth rate, or None when it is undefined.

    Undefined when the span is zero, the base is non-positive, or the endpoint
    is non-positive. Returning None keeps a meaningless ratio out of a bracket
    rather than emitting a misleading number.
    """
    if years <= 0 or start <= 0 or end <= 0:
        return None
    return (end / start) ** (1.0 / years) - 1.0


def profit_pool(
    columns: Sequence[Mapping[str, Any]],
    *,
    nhe_by_year: Optional[Mapping[int, float]] = None,
    projected_from_year: Optional[int] = None,
    source: str = "McKinsey-style profit-pool model (HCRIS, NHE, NAIC proxy)",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Stacked EBITDA by segment over years with CAGR brackets.

    ``columns``: ordered records of {year, segments: {name: ebitda}}. Segment
    order follows first appearance so the stack is stable across years.
    ``projected_from_year``: the first year that is a forecast; that year and
    every later year render ghosted.
    """
    if len(columns) < 2:
        raise ValueError("profit_pool requires at least two year columns")

    years: List[int] = []
    seg_order: List[str] = []
    by_year: Dict[int, Dict[str, float]] = {}
    for col in columns:
        year = int(col["year"])
        segs = {str(k): float(v) for k, v in dict(col["segments"]).items()}
        if year in by_year:
            raise ValueError(f"duplicate year column: {year}")
        years.append(year)
        by_year[year] = segs
        for name in segs:
            if name not in seg_order:
                seg_order.append(name)

    years.sort()
    totals = {y: sum(by_year[y].get(s, 0.0) for s in seg_order) for y in years}

    def _is_projected(year: int) -> bool:
        return projected_from_year is not None and year >= projected_from_year

    # Stacked long-format points: one per (year, segment).
    stacked: List[Dict[str, Any]] = []
    for y in years:
        for s in seg_order:
            stacked.append({
                "label": str(y),
                "year": y,
                "segment": s,
                "value": by_year[y].get(s, 0.0),
                "projected": _is_projected(y),
            })

    total_points = [
        {"label": str(y), "year": y, "value": totals[y], "projected": _is_projected(y)}
        for y in years
    ]

    # CAGR brackets: consecutive pairs, plus the full span when there are more
    # than two columns. Each bracket carries the total CAGR and a per-segment map.
    brackets: List[Dict[str, Any]] = []

    def _bracket(y0: int, y1: int) -> Dict[str, Any]:
        span = y1 - y0
        seg_cagrs = {
            s: _cagr(by_year[y0].get(s, 0.0), by_year[y1].get(s, 0.0), span)
            for s in seg_order
        }
        return {
            "from_year": y0,
            "to_year": y1,
            "years": span,
            "total_cagr": _cagr(totals[y0], totals[y1], span),
            "segment_cagrs": seg_cagrs,
        }

    for a, b in zip(years, years[1:]):
        brackets.append(_bracket(a, b))
    if len(years) > 2:
        brackets.append(_bracket(years[0], years[-1]))

    # Framing-metric variant: industry EBITDA as a percentage of NHE.
    nhe_points: List[Dict[str, Any]] = []
    if nhe_by_year:
        for y in years:
            nhe = float(nhe_by_year.get(y, 0.0))
            nhe_points.append({
                "label": str(y),
                "year": y,
                "value": safe_div(totals[y], nhe) * 100.0,
                "nhe": nhe,
                "projected": _is_projected(y),
            })

    flags: List[Flag] = []
    full = brackets[-1]
    for s, c in full["segment_cagrs"].items():
        if c is not None and c < 0:
            flags.append(Flag(
                code="declining_pool",
                severity="warn",
                message=(
                    f"The {s} pool shrinks over the full span at "
                    f"{c*100:.1f} percent per year."
                ),
                source=source,
            ))
    if projected_from_year is not None:
        flags.append(Flag(
            code="contains_projection",
            severity="info",
            message=(
                f"Columns from {projected_from_year} onward are projections, "
                "not actuals, and are shown ghosted."
            ),
            source=source,
        ))

    # Reconciliations: column totals tie to the segment sum, and the full-span
    # CAGR rebuilds the endpoint from the base.
    reconciliations = [
        Reconciliation(
            identity="column totals equal the sum of their segments",
            lhs=sum(totals.values()),
            rhs=sum(by_year[y].get(s, 0.0) for y in years for s in seg_order),
            tolerance=1e-9,
        )
    ]
    if full["total_cagr"] is not None:
        rebuilt = totals[years[0]] * (1.0 + full["total_cagr"]) ** full["years"]
        reconciliations.append(Reconciliation(
            identity="full-span CAGR rebuilds the final total from the first",
            lhs=rebuilt,
            rhs=totals[years[-1]],
            tolerance=1e-6,
        ))

    series = [
        Series(name="EBITDA by segment", kind="bar", points=stacked),
        Series(name="Total EBITDA", kind="line", points=total_points),
    ]
    if nhe_points:
        series.append(Series(name="EBITDA as percent of NHE", kind="line",
                             points=nhe_points))

    fn_assumptions = [
        "EBITDA is stacked by segment; the total is the column height.",
        "CAGR is compounded between the bracket endpoints.",
        "Projected columns are estimates, not actuals, and render ghosted.",
    ]
    if nhe_by_year:
        fn_assumptions.append(
            "Percent of NHE is total industry EBITDA divided by national health "
            "expenditure for the year."
        )
    footnote = Footnote(source=source, vintage=vintage or "not stated",
                        assumptions=fn_assumptions)

    tc = full["total_cagr"]
    cagr_txt = f"{tc*100:.1f} percent" if tc is not None else "not defined"
    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Healthcare profit pools by segment",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Total EBITDA {totals[years[0]]:,.0f} in {years[0]} to "
            f"{totals[years[-1]]:,.0f} in {years[-1]}, a {cagr_txt} CAGR."
        ),
        meta={
            "years": years,
            "segments": seg_order,
            "totals": totals,
            "by_year": by_year,
            "brackets": brackets,
            "projected_from_year": projected_from_year,
            "nhe_points": nhe_points,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # Shaped to the published 2024 report: total grows from 583 (2022) to 819
    # (2027) at roughly a 7 percent CAGR; HST grows fastest at roughly 12 percent.
    columns = [
        {"year": 2022, "segments": {"Payers": 60, "Providers": 254, "HST": 49, "Pharmacy": 220}},
        {"year": 2027, "segments": {"Payers": 78, "Providers": 366, "HST": 86, "Pharmacy": 289}},
    ]
    return profit_pool(
        columns,
        nhe_by_year={2022: 4464, 2027: 6215},
        projected_from_year=2027,
        source="Demo profit-pool table shaped to the 2024 What to expect report",
        vintage="2024",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Profit-pool stacked column with CAGR brackets",
        audience="both",
        demo=_demo,
    )
)
