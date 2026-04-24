"""Cybersecurity posture + business-interruption risk (Prompt K).

Anchored to the Change Healthcare 2024 ransomware attack as the
causal story. Every PE sponsor now treats cyber as a board-level
screening issue; this module integrates cyber posture into the
DealAnalysisPacket alongside EBITDA and EV.

Modules:

    bi_loss_model.py               — Monte Carlo BI loss model
    ehr_vendor_risk.py             — Epic/Cerner/Athena/etc. matrix
    business_associate_map.py      — BA cascade risk (Change Healthcare)
    cyber_score.py                 — composite 0-100 + band + bridge lever
    deferred_it_capex_detector.py  — IT capex overdue signal
"""
from __future__ import annotations

from .bi_loss_model import BILossResult, simulate_bi_loss
from .business_associate_map import (
    BACascadeFinding, assess_business_associates,
)
from .cyber_score import (
    CyberScore, compose_cyber_score, cyber_bridge_reserve_pct,
)
from .deferred_it_capex_detector import (
    ITCapexFinding, detect_deferred_it_capex,
)
from .ehr_vendor_risk import ehr_vendor_risk_score, list_ehr_vendors

__all__ = [
    "BACascadeFinding",
    "BILossResult",
    "CyberScore",
    "ITCapexFinding",
    "assess_business_associates",
    "compose_cyber_score",
    "cyber_bridge_reserve_pct",
    "detect_deferred_it_capex",
    "ehr_vendor_risk_score",
    "list_ehr_vendors",
    "simulate_bi_loss",
]
