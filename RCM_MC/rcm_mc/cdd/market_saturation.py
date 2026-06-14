"""NEW-08 Market saturation / white-space mapping.

Computes a saturation ratio (providers per N beneficiaries) by service area and
ranks areas to surface under-served white space for roll-up screening. Lowest
saturation ranks first as the most open white space. Encodes the CMS rule that a
provider serves an area only if more than 10 located beneficiaries had paid
claims. The Market Saturation source is fee-for-service only, noted in metadata.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-08"
SERVE_THRESHOLD = 10  # located beneficiaries with paid claims, strictly greater


def _serving_count(area: Mapping[str, Any], serve_threshold: int) -> int:
    """Apply the >10 located-beneficiary rule when per-provider data is present."""
    recs = area.get("provider_claims")
    if recs is None:
        return int(area["providers"])
    return sum(1 for c in recs if float(c) > serve_threshold)


def market_saturation(
    areas: Sequence[Mapping[str, Any]],
    *,
    per_n: int = 1000,
    serve_threshold: int = SERVE_THRESHOLD,
    source: str = "CMS Market Saturation and Utilization",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Saturation ratio and white-space ranking by service area.

    ``areas``: records of {area, providers, beneficiaries} and optionally
    {provider_claims: [located beneficiaries with claims per provider]} to apply
    the serve rule.
    """
    if not areas:
        raise ValueError("market_saturation requires at least one area")

    rows: List[Dict[str, Any]] = []
    for a in areas:
        name = str(a["area"])
        benes = float(a["beneficiaries"])
        serving = _serving_count(a, serve_threshold)
        saturation = safe_div(serving, benes) * per_n
        rows.append({
            "area": name,
            "serving_providers": serving,
            "beneficiaries": benes,
            "saturation_per_n": saturation,
        })

    # White-space ranking: lowest saturation ranks first (most open).
    ordered = sorted(rows, key=lambda r: (r["saturation_per_n"], r["area"]))
    for i, r in enumerate(ordered, start=1):
        r["white_space_rank"] = i

    n = len(ordered)
    rank_sum = sum(r["white_space_rank"] for r in ordered)
    reconciliations = [
        Reconciliation(
            identity="white-space ranks are a permutation of 1..n",
            lhs=rank_sum,
            rhs=n * (n + 1) / 2,
            tolerance=1e-9,
        )
    ]

    flags = [Flag(
        code="ffs_only",
        severity="info",
        message="Market Saturation counts fee-for-service beneficiaries only. Managed care is excluded.",
        source=source,
    )]

    series = [
        Series(name=f"Saturation per {per_n} beneficiaries", kind="bar",
               points=[{"label": r["area"], "value": r["saturation_per_n"]} for r in ordered]),
        Series(name="White-space ranking", kind="bar",
               points=[{"label": r["area"], "value": r["white_space_rank"]} for r in ordered]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            f"Saturation is serving providers per {per_n} beneficiaries.",
            f"A provider serves an area only if more than {serve_threshold} located beneficiaries had paid claims.",
            "Fee-for-service only. Medicare Advantage beneficiaries are not counted.",
        ],
    )

    top = ordered[0]["area"] if ordered else ""
    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Market saturation and white space",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=f"{n} service area(s). Most open white space: {top}.",
        meta={
            "rows": ordered,
            "ranking": [r["area"] for r in ordered],
            "ffs_only": True,
            "serve_threshold": serve_threshold,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    areas = [
        {"area": "CBSA-A", "providers": 50, "beneficiaries": 100000},
        {"area": "CBSA-B", "providers": 10, "beneficiaries": 100000},
        {"area": "CBSA-C", "providers": 200, "beneficiaries": 100000},
    ]
    return market_saturation(areas, source="Demo Market Saturation", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Market saturation / white-space mapping",
        audience="both",
        demo=_demo,
    )
)
