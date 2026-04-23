"""Phase 2 — KPI Benchmarking & Stress Testing.

Reads the CCD from Phase 1. Computes HFMA-vocabulary KPIs with cited
formulas, cohort liquidation curves with as_of censoring, and denial
stratification by ANSI CARC category.

Public surface:

    from rcm_mc.diligence.benchmarks import (
        compute_kpis, KPIBundle, KPIResult,
        compute_cohort_liquidation, CohortLiquidationReport,
    )
"""
from __future__ import annotations

from ._ansi_codes import DenialCategory, classify_carc, classify_carc_set
from .cash_waterfall import (
    DEFAULT_BAD_DEBT_AGE_DAYS,
    DEFAULT_QOR_DIVERGENCE_THRESHOLD,
    DEFAULT_REALIZATION_WINDOW_DAYS,
    WATERFALL_STEPS,
    CashWaterfallReport,
    WaterfallCohort,
    WaterfallStep,
    compute_cash_waterfall,
)
from .cohort_liquidation import (
    CohortCell,
    CohortLiquidationReport,
    CohortStatus,
    DEFAULT_WINDOWS,
    compute_cohort_liquidation,
)
from .kpi_engine import (
    DenialStratRow,
    KPIBundle,
    KPIResult,
    compute_kpis,
)

__all__ = [
    "CashWaterfallReport",
    "CohortCell",
    "CohortLiquidationReport",
    "CohortStatus",
    "DEFAULT_BAD_DEBT_AGE_DAYS",
    "DEFAULT_QOR_DIVERGENCE_THRESHOLD",
    "DEFAULT_REALIZATION_WINDOW_DAYS",
    "DEFAULT_WINDOWS",
    "DenialCategory",
    "DenialStratRow",
    "KPIBundle",
    "KPIResult",
    "WATERFALL_STEPS",
    "WaterfallCohort",
    "WaterfallStep",
    "classify_carc",
    "classify_carc_set",
    "compute_cash_waterfall",
    "compute_cohort_liquidation",
    "compute_kpis",
]
