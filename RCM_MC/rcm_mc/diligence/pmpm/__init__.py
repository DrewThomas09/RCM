"""Risk-adjusted PMPM (per-member-per-month) financial-trend mart.

Separates real cost inflation from case-mix drift by trending PMPM/RAF
alongside raw PMPM, benchmarks the risk-adjusted level against peers
(reusing diligence.risk_adjustment), and projects a continuing trend
into an EBITDA-at-risk overlay.

See ``README.md`` and ``docs/TUVA_MYELIN_INTEGRATION.md``.
"""
from __future__ import annotations

from .pmpm_trend import (
    PMPMPeriod,
    PMPMTrendResult,
    PMPMVerdict,
    analyze_pmpm,
)

__all__ = [
    "PMPMPeriod",
    "PMPMTrendResult",
    "PMPMVerdict",
    "analyze_pmpm",
]
