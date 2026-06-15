"""NEW-21 Contested market-size triangulation.

Several of the supply-side markets in the healthcare reference report carry
market-size estimates that diverge wildly by source and definition: global
medtech is quoted anywhere from 586 to 695 billion dollars, IVD from 82 to 101,
and revenue-cycle management from 57 to 172, where the spread is driven almost
entirely by whether the figure is software-only or services-inclusive.

The report's Stage 2 recommendation is explicit: do not let a single vendor
market-research point estimate masquerade as fact. Present a range with named
sources, standardize on one documented house estimate per vintage, and when two
reputable sources diverge by more than 25 percent, show the range in the chart
rather than a single bar.

This exhibit operationalizes that rule. It takes named source estimates for one
market, computes the low, median, high, and spread, picks (or accepts) a house
estimate, and raises a divergence flag when the spread crosses the threshold and
a basis-mismatch flag when the sources do not share a scope definition. The
house estimate is reconciled to lie inside the source range.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-21"

# The report's Stage 2 threshold: above this spread, show the range, not a bar.
DEFAULT_DIVERGENCE_THRESHOLD = 0.25


def _median(values: Sequence[float]) -> float:
    """Median of a non-empty sequence; the mean of the two central values when
    the count is even, so an even set does not silently pick a side."""
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def market_size_estimates(
    market: str,
    estimates: Sequence[Mapping[str, Any]],
    *,
    house: Optional[float] = None,
    house_source: str = "",
    divergence_threshold: float = DEFAULT_DIVERGENCE_THRESHOLD,
    unit: str = "USD billions",
    source: str = "Multiple market-research sources",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Triangulate a contested market size across named source estimates.

    ``estimates``: records of {source, value, vintage?, basis?, note?}. ``value``
    is the size in ``unit``. ``basis`` is the scope definition (for example
    "software-led scope" versus "services-inclusive scope"); when sources carry
    different non-empty bases the exhibit flags the mismatch so the reader does
    not compare incompatible scopes.

    ``house``: the single point estimate the analysis standardizes on. When
    omitted it defaults to the median of the sources and the footnote records
    that basis. An explicit house outside the source range is a hard flag and
    fails the in-range reconciliation.
    """
    if not estimates:
        raise ValueError("market_size_estimates requires at least one source estimate")

    rows: List[Dict[str, Any]] = []
    for e in estimates:
        value = float(e["value"])
        if value <= 0:
            raise ValueError(f"estimate value must be positive: {e}")
        rows.append({
            "source": str(e["source"]),
            "value": value,
            "vintage": str(e.get("vintage", "") or ""),
            "basis": str(e.get("basis", "") or ""),
            "note": str(e.get("note", "") or ""),
        })

    rows.sort(key=lambda r: r["value"])
    values = [r["value"] for r in rows]
    low = min(values)
    high = max(values)
    median = _median(values)
    mean = sum(values) / len(values)
    # Spread is defined off the low estimate so it reads as "the high is X percent
    # above the low", the comparison the report's 25 percent rule is stated on.
    spread = safe_div(high - low, low)

    house_is_default = house is None
    house_value = float(median if house is None else house)
    house_basis = (
        "median of source estimates" if house_is_default
        else (house_source or "analyst-selected house estimate")
    )

    # Deviation of each source from the house, so a chart can show how far each
    # vendor sits from the standardized number.
    for r in rows:
        r["deviation_from_house"] = safe_div(r["value"] - house_value, house_value)

    flags: List[Flag] = []
    if len(rows) == 1:
        flags.append(Flag(
            code="single_source",
            severity="info",
            message=(
                f"Only one source estimates {market}, so the figure cannot be "
                "triangulated. Treat it as a single point, not a consensus."
            ),
            source=source,
        ))
    if spread > divergence_threshold:
        flags.append(Flag(
            code="wide_estimate_divergence",
            severity="warn",
            message=(
                f"{market} estimates span {low:,.1f} to {high:,.1f}, a "
                f"{spread*100:.0f} percent spread above the "
                f"{divergence_threshold*100:.0f} percent line. Show the range, "
                "not a single bar."
            ),
            source=source,
        ))

    distinct_bases = sorted({r["basis"] for r in rows if r["basis"]})
    if len(distinct_bases) > 1:
        flags.append(Flag(
            code="basis_mismatch",
            severity="warn",
            message=(
                f"{market} sources use different scope definitions "
                f"({', '.join(distinct_bases)}). Do not compare them as like for "
                "like."
            ),
            source=source,
        ))

    house_in_range = low <= house_value <= high
    if not house_in_range:
        flags.append(Flag(
            code="house_outside_range",
            severity="risk",
            message=(
                f"The house estimate {house_value:,.1f} falls outside the source "
                f"range {low:,.1f} to {high:,.1f}."
            ),
            source=source,
        ))

    # Reconciliations. The load-bearing one is that the house estimate lies
    # within the source range: the clamped house equals the house exactly when it
    # is in range, and diverges (failing the tie-out) when it is not.
    reconciliations = [
        Reconciliation(
            identity="house estimate lies within the source range",
            lhs=_clamp(house_value, low, high),
            rhs=house_value,
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="spread equals high minus low over low",
            lhs=spread,
            rhs=safe_div(high - low, low),
            tolerance=1e-12,
        ),
    ]

    source_points = [
        {
            "label": r["source"],
            "value": r["value"],
            "vintage": r["vintage"],
            "basis": r["basis"],
            "deviation_from_house": r["deviation_from_house"],
        }
        for r in rows
    ]
    # Range band: low, house, high, the three marks a range chart draws.
    band_points = [
        {"label": "low", "value": low, "source": rows[0]["source"]},
        {"label": "house", "value": house_value, "basis": house_basis},
        {"label": "high", "value": high, "source": rows[-1]["source"]},
    ]

    series = [
        Series(name="Source estimates", kind="bar", points=source_points),
        Series(name="Estimate range band", kind="line", points=band_points),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        basis=house_basis,
        assumptions=[
            f"Values are in {unit}.",
            "The range spans the lowest and highest named source estimate.",
            f"The house estimate is the {house_basis}.",
            f"Divergence flag fires above a {divergence_threshold*100:.0f} percent "
            "spread of high over low.",
            "Sources with different scope definitions are not compared as like for like.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title=f"{market} market size, source triangulation",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(rows)} sources put {market} at {low:,.1f} to {high:,.1f} "
            f"{unit}, a {spread*100:.0f} percent spread. House estimate "
            f"{house_value:,.1f}."
        ),
        meta={
            "market": market,
            "unit": unit,
            "low": low,
            "high": high,
            "median": median,
            "mean": mean,
            "spread": spread,
            "house": house_value,
            "house_is_default": house_is_default,
            "house_basis": house_basis,
            "house_in_range": house_in_range,
            "distinct_bases": distinct_bases,
            "sources": rows,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # Revenue-cycle management, the report's most contested supply-side market:
    # 57 to 172 billion, where the spread is software-only versus
    # services-inclusive scope (report section 18). House defaults to the median.
    estimates = [
        {"source": "Market Data Forecast", "value": 56.8, "vintage": "2024",
         "basis": "software-led scope"},
        {"source": "Precedence", "value": 58.5, "vintage": "2024",
         "basis": "software-led scope"},
        {"source": "Arizton", "value": 141.6, "vintage": "2024",
         "basis": "services-inclusive scope"},
        {"source": "Grand View", "value": 172.2, "vintage": "2024",
         "basis": "services-inclusive scope"},
    ]
    return market_size_estimates(
        "US revenue-cycle management",
        estimates,
        source="Healthcare supply-side reference report, section 18",
        vintage="2024",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Contested market-size triangulation",
        audience="both",
        demo=_demo,
    )
)
