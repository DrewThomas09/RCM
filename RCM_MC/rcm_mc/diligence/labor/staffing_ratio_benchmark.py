"""Staffing-ratio benchmarks.

HCRIS-derived anchors for nurse-per-occupied-bed, coder-per-10K-
claims, etc. Public aggregates — refresh quarterly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


_BENCHMARKS = {
    "NURSE_PER_OCCUPIED_BED": {"p25": 0.9, "p50": 1.1, "p75": 1.4},
    "FTE_PER_ADJUSTED_DISCHARGE": {"p25": 3.2, "p50": 4.1, "p75": 5.0},
    "CODER_PER_10K_CLAIMS": {"p25": 1.5, "p50": 2.1, "p75": 2.8},
    "BILLER_PER_10K_CLAIMS": {"p25": 3.0, "p50": 4.2, "p75": 5.5},
}


@dataclass
class StaffingRatioResult:
    metric: str
    target_value: float
    p25: float
    p50: float
    p75: float
    placement: str          # below_p25 | p25_to_p50 | p50_to_p75 | above_p75
    gap_to_p50_pct: float
    severity: str           # LOW | MEDIUM | HIGH

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def benchmark_staffing_ratio(
    *,
    metric: str,
    target_value: float,
) -> Optional[StaffingRatioResult]:
    bench = _BENCHMARKS.get(metric.upper())
    if not bench:
        return None
    p25, p50, p75 = bench["p25"], bench["p50"], bench["p75"]
    if target_value < p25:
        placement = "below_p25"
    elif target_value < p50:
        placement = "p25_to_p50"
    elif target_value < p75:
        placement = "p50_to_p75"
    else:
        placement = "above_p75"
    gap = (target_value - p50) / p50 if p50 > 0 else 0.0

    # For ratios where "lower is leaner" (all four seeded here),
    # below-p25 is understaffed → HIGH severity (patient-safety /
    # revenue-cycle risk). Above p75 is overstaffed → MEDIUM.
    if placement == "below_p25":
        severity = "HIGH"
    elif placement == "above_p75":
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return StaffingRatioResult(
        metric=metric.upper(),
        target_value=target_value,
        p25=p25, p50=p50, p75=p75,
        placement=placement,
        gap_to_p50_pct=gap,
        severity=severity,
    )
