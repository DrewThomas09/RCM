"""Deal filter — narrow the screening universe.

Filter chips the dashboard exposes:
  • sector — one or more
  • size_min / size_max — EBITDA $M range
  • confidence_floor — drop below this
  • exclude_topics — keyword-substring match against risk_factors
  • min_uplift — drop below this $-uplift floor
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from .predict import ScreeningResult


@dataclass
class DealFilter:
    sectors: List[str] = field(default_factory=list)
    size_min_mm: Optional[float] = None
    size_max_mm: Optional[float] = None
    confidence_floor: float = 0.0
    exclude_topics: List[str] = field(default_factory=list)
    min_uplift_mm: float = 0.0


def apply_filter(
    results: Iterable[ScreeningResult],
    flt: DealFilter,
) -> List[ScreeningResult]:
    """Apply a DealFilter, returning the surviving subset.
    Order preserved (callers control sort)."""
    sectors_l = {s.lower() for s in flt.sectors}
    excl_l = [t.lower() for t in flt.exclude_topics]

    out: List[ScreeningResult] = []
    for r in results:
        if sectors_l and (r.sector.lower() not in sectors_l):
            continue
        if (flt.size_min_mm is not None
                and r.ebitda_mm < flt.size_min_mm):
            continue
        if (flt.size_max_mm is not None
                and r.ebitda_mm > flt.size_max_mm):
            continue
        if r.confidence < flt.confidence_floor:
            continue
        if r.predicted_ebitda_uplift_mm < flt.min_uplift_mm:
            continue
        # Topic exclusion: any risk-factor string contains the
        # exclude term → drop this row
        if excl_l:
            row_lower = " ".join(r.risk_factors).lower()
            if any(t in row_lower for t in excl_l):
                continue
        out.append(r)
    return out
