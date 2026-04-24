"""Medicare Advantage V28 + payer-mix dynamics engine (Prompt L).

Targets Gap 11 — MA covers >55% of Medicare beneficiaries and V28
(fully effective 2026-01-01) projects 3.12% avg risk-score
reduction. Cano Health bankruptcy directly tied to pre-V28
assumptions; Aetna/CVS $117.7M DOJ settlement (March 2026)
anchors coding-intensity risk.

Modules:

    v28_recalibration.py          — member-level V24 vs V28 risk score
                                     delta; revenue impact
    coding_intensity_analyzer.py  — FCA-risk signals (Aetna/CVS pattern)
    medicaid_unwind_tracker.py    — state-level unwind + target exposure
    commercial_concentration.py   — payer HHI + market-power squeeze
    risk_contract_modeler.py      — ACO REACH / MSSP / full-risk MA
    downcoding_prior_auth_red_flag.py — payer-behavior signals
"""
from __future__ import annotations

from .coding_intensity_analyzer import (
    CodingIntensityFinding, analyze_coding_intensity,
)
from .commercial_concentration import (
    CommercialConcentrationResult, compute_commercial_concentration,
)
from .downcoding_prior_auth_red_flag import (
    PayerBehaviorFinding, detect_payer_behavior_signals,
)
from .medicaid_unwind_tracker import (
    MedicaidUnwindImpact, estimate_medicaid_unwind_impact,
)
from .risk_contract_modeler import (
    RiskContractProjection, project_risk_contract,
)
from .v28_recalibration import (
    V28CodeMapping, V28Result, compute_v28_recalibration,
    load_code_map,
)

__all__ = [
    "CodingIntensityFinding",
    "CommercialConcentrationResult",
    "MedicaidUnwindImpact",
    "PayerBehaviorFinding",
    "RiskContractProjection",
    "V28CodeMapping",
    "V28Result",
    "analyze_coding_intensity",
    "compute_commercial_concentration",
    "compute_v28_recalibration",
    "detect_payer_behavior_signals",
    "estimate_medicaid_unwind_impact",
    "load_code_map",
    "project_risk_contract",
]
