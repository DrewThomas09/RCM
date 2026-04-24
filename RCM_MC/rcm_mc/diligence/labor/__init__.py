"""Labor economics diligence module (Prompt M, Gap 2).

Scope-reduced from the original spec: three pragmatic submodules
covering the highest-value analytics.

    wage_forecaster.py          — regional wage inflation projection
    staffing_ratio_benchmark.py — nurse/coder/biller FTE ratios
    synthetic_fte_detector.py   — billing NPIs vs scheduling FTE

Union / NLRB exposure is handled in the reputational module
(Gap 12) where it overlaps naturally; we don't duplicate that
surface here.
"""
from __future__ import annotations

from .staffing_ratio_benchmark import (
    StaffingRatioResult, benchmark_staffing_ratio,
)
from .synthetic_fte_detector import (
    SyntheticFTEFinding, detect_synthetic_fte,
)
from .wage_forecaster import (
    WageForecast, forecast_wage_inflation,
)

__all__ = [
    "StaffingRatioResult",
    "SyntheticFTEFinding",
    "WageForecast",
    "benchmark_staffing_ratio",
    "detect_synthetic_fte",
    "forecast_wage_inflation",
]
