"""Bear Case Auto-Generator.

Pulls evidence from Regulatory Calendar × Covenant Stress ×
Bridge Audit × Deal MC × Deal Autopsy × Exit Timing and composes
a ranked, cited, partner-facing bear case — the counter-narrative
every IC memo needs, auto-generated in 2 seconds.

Public API::

    from rcm_mc.diligence.bear_case import (
        BearCaseReport, Evidence, EvidenceSeverity,
        EvidenceSource, EvidenceTheme,
        generate_bear_case, generate_bear_case_from_pipeline,
    )
"""
from __future__ import annotations

from .evidence import (
    Evidence, EvidenceSeverity, EvidenceSource, EvidenceTheme,
    extract_autopsy_evidence, extract_bridge_audit_evidence,
    extract_covenant_evidence, extract_deal_mc_evidence,
    extract_exit_timing_evidence, extract_hcris_xray_evidence,
    extract_payer_stress_evidence, extract_regulatory_evidence,
)
from .generator import (
    BearCaseReport, generate_bear_case,
    generate_bear_case_from_pipeline,
)

__all__ = [
    "BearCaseReport",
    "Evidence",
    "EvidenceSeverity",
    "EvidenceSource",
    "EvidenceTheme",
    "extract_autopsy_evidence",
    "extract_bridge_audit_evidence",
    "extract_covenant_evidence",
    "extract_deal_mc_evidence",
    "extract_exit_timing_evidence",
    "extract_hcris_xray_evidence",
    "extract_payer_stress_evidence",
    "extract_regulatory_evidence",
    "generate_bear_case",
    "generate_bear_case_from_pipeline",
]
