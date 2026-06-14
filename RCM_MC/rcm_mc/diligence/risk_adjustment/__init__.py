"""CMS-HCC risk adjustment + risk-adjusted peer benchmarking.

The native, zero-dependency reimplementation of the slice of the Tuva
``cms_hcc`` mart diligence needs: score a panel's case-mix burden
(RAF) and put peer cost/outcome comparisons on a case-mix-normalized
footing so a sicker panel isn't mistaken for an inefficient operator.

See ``README.md`` and ``docs/TUVA_MYELIN_INTEGRATION.md``.
"""
from __future__ import annotations

from .hcc_library import (
    DISEASE_INTERACTIONS,
    HCC_FACTORS,
    SEGMENT,
    HCCFactor,
    apply_hierarchies,
    demographic_factor,
    get_hcc,
    map_condition_to_hcc,
)
from .risk_scorer import (
    Demographics,
    PanelRiskScore,
    RiskAdjustedBenchmark,
    RiskScore,
    RiskVerdict,
    compute_raf,
    risk_adjust_metric,
    score_panel,
)

__all__ = [
    "DISEASE_INTERACTIONS",
    "HCC_FACTORS",
    "SEGMENT",
    "Demographics",
    "HCCFactor",
    "PanelRiskScore",
    "RiskAdjustedBenchmark",
    "RiskScore",
    "RiskVerdict",
    "apply_hierarchies",
    "compute_raf",
    "demographic_factor",
    "get_hcc",
    "map_condition_to_hcc",
    "risk_adjust_metric",
    "score_panel",
]
