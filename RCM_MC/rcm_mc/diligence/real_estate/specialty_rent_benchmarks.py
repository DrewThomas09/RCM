"""Specialty rent-benchmark lookups.

Thin read over ``content/specialty_rent_benchmarks.yaml``. Callers
use :func:`get_rent_benchmark` with a specialty code and receive a
p25/p50/p75 band. :func:`classify_rent_share` maps a rent-to-
revenue share to a band label.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .types import load_content


VALID_SPECIALTIES = (
    "HOSPITAL", "SNF", "MOB", "ASC", "SENIOR_LIVING", "BEHAVIORAL",
)


def get_rent_benchmark(specialty: str) -> Optional[Dict[str, Any]]:
    """Return the benchmark band dict for a specialty, or None when
    the specialty isn't in the library."""
    try:
        content = load_content("specialty_rent_benchmarks")
    except FileNotFoundError:
        return None
    specs = content.get("specialties") or {}
    return specs.get(specialty.upper())


def classify_rent_share(
    specialty: str, rent_pct_revenue: float,
) -> str:
    """Classify a rent-to-revenue share as

        'below_p25' | 'p25_to_p50' | 'p50_to_p75' | 'above_p75'
                    | 'unknown' (if specialty has no band).

    Senior-living uses ``rent_plus_debt_pct_revenue`` in the YAML;
    callers that want the senior-living comparison should pass the
    combined rent+debt figure in as ``rent_pct_revenue``.
    """
    entry = get_rent_benchmark(specialty)
    if not entry:
        return "unknown"
    bands = (
        entry.get("rent_pct_revenue")
        or entry.get("rent_plus_debt_pct_revenue")
        or {}
    )
    p25 = bands.get("p25")
    p50 = bands.get("p50")
    p75 = bands.get("p75")
    if None in (p25, p50, p75):
        return "unknown"
    if rent_pct_revenue < p25:
        return "below_p25"
    if rent_pct_revenue < p50:
        return "p25_to_p50"
    if rent_pct_revenue < p75:
        return "p50_to_p75"
    return "above_p75"


def rent_is_suicidal(
    specialty: str, rent_pct_revenue: float,
) -> bool:
    """Convenience: True when a hospital's rent ratio is above 3x
    the hospital p75 benchmark — Steward's pattern at bankruptcy.
    For other specialties, uses 2x p75 as the "extreme" threshold."""
    entry = get_rent_benchmark(specialty)
    if not entry:
        return False
    bands = (
        entry.get("rent_pct_revenue")
        or entry.get("rent_plus_debt_pct_revenue")
        or {}
    )
    p75 = bands.get("p75")
    if p75 is None:
        return False
    multiplier = 3.0 if specialty.upper() == "HOSPITAL" else 2.0
    # Small tolerance — float-multiplier comparisons (0.05 * 3) can
    # produce 0.15000000000000002, failing a naive >= against 0.15.
    return rent_pct_revenue >= (p75 * multiplier) - 1e-9
