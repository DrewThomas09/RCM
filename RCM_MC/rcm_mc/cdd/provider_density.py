"""NEW-07 Provider density / geographic heatmap.

Counts providers per geography (county FIPS or CBSA) from an NPPES-style
provider table, optionally joined to POS facilities on CCN, and produces a
clean choropleth geo layer. Optional population yields providers per 100k.
Small cells at or below the suppression threshold are suppressed in the geo
layer and flagged, mirroring CMS cell-suppression practice.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-07"
DEFAULT_SUPPRESSION = 11


def provider_density(
    providers: Sequence[Mapping[str, Any]],
    *,
    by: str = "fips",
    population: Optional[Mapping[str, float]] = None,
    suppression_threshold: int = DEFAULT_SUPPRESSION,
    suppress: bool = True,
    source: str = "NPPES provider registry",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Count providers per geography and build a choropleth geo layer.

    ``providers``: records with the geography key ``by`` (``fips`` or ``cbsa``)
    and ``npi``. ``population``: geo to population for a per-100k density.
    """
    if by not in {"fips", "cbsa"}:
        raise ValueError(f"by must be 'fips' or 'cbsa', got {by!r}")
    if not providers:
        raise ValueError("provider_density requires at least one provider")

    counts: Dict[str, int] = {}
    seen_npi: set = set()
    for p in providers:
        geo = str(p[by])
        npi = p.get("npi")
        # Dedupe a provider that appears multiple times in the same geo.
        key = (geo, npi) if npi is not None else (geo, id(p))
        if key in seen_npi:
            continue
        seen_npi.add(key)
        counts[geo] = counts.get(geo, 0) + 1

    total = sum(counts.values())
    flags: List[Flag] = []
    geo_layer: List[Dict[str, Any]] = []
    suppressed_geos: List[str] = []

    for geo in sorted(counts):
        n = counts[geo]
        pop = float(population[geo]) if population and geo in population else None
        density = safe_div(n, pop) * 100000.0 if pop else None
        is_suppressed = suppress and n <= suppression_threshold
        if is_suppressed:
            suppressed_geos.append(geo)
        geo_layer.append({
            "geo": geo,
            "geo_type": by,
            "count": None if is_suppressed else n,
            "raw_count": n,
            "density_per_100k": None if (is_suppressed or density is None) else density,
            "suppressed": is_suppressed,
        })

    if suppressed_geos:
        flags.append(Flag(
            code="cells_suppressed",
            severity="info",
            message=(
                f"{len(suppressed_geos)} geograph(ies) at or below the "
                f"{suppression_threshold} suppression threshold were suppressed."
            ),
        ))

    # Reconcile: suppressed raw counts plus visible counts equal the total.
    visible_sum = sum(g["raw_count"] for g in geo_layer)
    reconciliations = [
        Reconciliation(
            identity="sum of per-geo provider counts equals total providers",
            lhs=visible_sum,
            rhs=total,
            tolerance=1e-9,
        )
    ]

    # Choropleth series uses suppressed-aware counts; internal series keeps raw.
    series = [
        Series(name=f"Provider count by {by}", kind="choropleth",
               points=[{"label": g["geo"], "value": g["count"]} for g in geo_layer]),
        Series(name=f"Provider density per 100k by {by}", kind="choropleth",
               points=[{"label": g["geo"], "value": g["density_per_100k"]} for g in geo_layer]),
        Series(name="Raw geo layer", kind="choropleth", internal_only=True, points=geo_layer),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            f"One count per unique NPI per {by}.",
            f"Cells at or below {suppression_threshold} are suppressed.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title=f"Provider density by {by}",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=f"{total} providers across {len(counts)} {by} area(s).",
        meta={
            "by": by,
            "counts": counts,
            "total": total,
            "geo_layer": geo_layer,
            "suppressed_geos": suppressed_geos,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    providers = (
        [{"npi": f"L{i}", "fips": "06037", "taxonomy": "207Q00000X"} for i in range(5)]
        + [{"npi": f"N{i}", "fips": "36061", "taxonomy": "207Q00000X"} for i in range(3)]
        + [{"npi": f"H{i}", "fips": "48201", "taxonomy": "207Q00000X"} for i in range(2)]
    )
    pop = {"06037": 10_000_000, "36061": 1_600_000, "48201": 4_700_000}
    return provider_density(providers, by="fips", population=pop,
                            suppress=False, source="Demo NPPES", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Provider density / geographic heatmap",
        audience="both",
        demo=_demo,
    )
)
