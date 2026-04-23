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
from .contract_repricer import (
    CCD_TO_BRIDGE_PAYER_CLASS,
    REASON_CARVE_OUT,
    REASON_MATCHED,
    REASON_MISSING_DATA,
    REASON_NO_CONTRACT,
    REASON_STOP_LOSS_APPLIED,
    REASON_WITHHOLD_APPLIED,
    ContractRate,
    ContractSchedule,
    PayerRollUp,
    RepricingReport,
    RepricingResult,
    payer_leverage_for_bridge,
    reprice_claim,
    reprice_claims,
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
    "CCD_TO_BRIDGE_PAYER_CLASS",
    "CashWaterfallReport",
    "CohortCell",
    "CohortLiquidationReport",
    "CohortStatus",
    "ContractRate",
    "ContractSchedule",
    "DEFAULT_BAD_DEBT_AGE_DAYS",
    "DEFAULT_QOR_DIVERGENCE_THRESHOLD",
    "DEFAULT_REALIZATION_WINDOW_DAYS",
    "DEFAULT_WINDOWS",
    "DenialCategory",
    "DenialStratRow",
    "KPIBundle",
    "KPIResult",
    "PayerRollUp",
    "REASON_CARVE_OUT",
    "REASON_MATCHED",
    "REASON_MISSING_DATA",
    "REASON_NO_CONTRACT",
    "REASON_STOP_LOSS_APPLIED",
    "REASON_WITHHOLD_APPLIED",
    "RepricingReport",
    "RepricingResult",
    "WATERFALL_STEPS",
    "WaterfallCohort",
    "WaterfallStep",
    "classify_carc",
    "classify_carc_set",
    "compute_cash_waterfall",
    "compute_cohort_liquidation",
    "compute_kpis",
    "payer_leverage_for_bridge",
    "reprice_claim",
    "reprice_claims",
]
