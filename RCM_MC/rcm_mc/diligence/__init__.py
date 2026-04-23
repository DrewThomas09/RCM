"""RCM Diligence — the analyst's primary workspace.

Organised around the four-phase RCM Diligence Playbook:

    Phase 1 — Ingestion & Normalization  → rcm_mc/diligence/ingest/
    Phase 2 — KPI Benchmarking           → rcm_mc/diligence/benchmarks/
    Phase 3 — Root Cause Analysis        → rcm_mc/diligence/root_cause/
    Phase 4 — Value Creation Model       → rcm_mc/diligence/value/

Phase 1 is load-bearing: every number every downstream phase produces
has to trace back to a row in the CCD (Canonical Claims Dataset)
emitted by the ingester. Phase 1 alone ships in this session; Phases
2–4 are empty scaffolds for follow-up work.

The diligence workspace doesn't replace the packet spine — it *feeds*
it. When a deal has a CCD attached, ``DealAnalysisPacket.observed_metrics``
carries CCD-derived KPIs (higher confidence weighting than partner-
supplied YAML).
"""
from __future__ import annotations

from .benchmarks import (
    CohortLiquidationReport,
    KPIBundle,
    KPIResult,
    compute_cohort_liquidation,
    compute_kpis,
)
from .ccd_bridge import (
    CCDBridgeOutput,
    kpis_to_observed,
    merge_observed_sources,
)
from .ingest import (
    CanonicalClaim,
    CanonicalClaimsDataset,
    Transformation,
    TransformationLog,
    ingest_dataset,
)
from .integrity import (
    DistributionScore,
    LeakageError,
    ProviderSplit,
    TemporalValidity,
    audit_features,
    check_regulatory_overlap,
    make_three_way_split,
    score_distribution,
)

__all__ = [
    "CCDBridgeOutput",
    "CanonicalClaim",
    "CanonicalClaimsDataset",
    "CohortLiquidationReport",
    "DistributionScore",
    "KPIBundle",
    "KPIResult",
    "LeakageError",
    "ProviderSplit",
    "TemporalValidity",
    "Transformation",
    "TransformationLog",
    "audit_features",
    "check_regulatory_overlap",
    "compute_cohort_liquidation",
    "compute_kpis",
    "ingest_dataset",
    "kpis_to_observed",
    "make_three_way_split",
    "merge_observed_sources",
    "score_distribution",
]
