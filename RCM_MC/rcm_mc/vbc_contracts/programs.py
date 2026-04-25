"""VBC program templates — one record per Track / contract design.

The active 2026-program landscape:

  • MSSP Basic A/B   — upside-only (no downside risk). Typically
                       30-40% sharing, 2% MSR. The on-ramp.
  • MSSP Basic C/D   — two-sided (5% MLR, ~30% downside share)
  • MSSP Enhanced E  — full risk (75% upside, 75% downside)
  • ACO REACH Global — 100% upside, 100% downside, no MSR/MLR
                       (standard Direct Contracting successor).
                       Quality withhold 2%. Most aggressive.
  • ACO REACH Pro    — 50% upside / 50% downside. Easier on-ramp.
  • MA delegated     — global cap with 90/10 risk split, withhold
                       varies. Used by full-risk MA primary care.
  • Commercial DCE   — total-care cap with employer plan. Margin
                       structure varies; defaults match ACO Pro.
  • Medicaid MCO     — state-specific; we model as 80% MLR floor
                       (state recoups above-floor) and a fixed
                       PMPM at the state's regional rate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..vbc.contracts import ContractTerms


@dataclass
class VBCProgram:
    """A single Track / contract template."""
    program_id: str
    label: str
    contract_template: ContractTerms
    on_ramp_difficulty: float = 0.5    # 0-1, easier=lower; partners
                                       # use this to weight against
                                       # NPV when choosing a Track
    typical_year: int = 2026


# ── Program registry ───────────────────────────────────────────

PROGRAMS: Dict[str, VBCProgram] = {
    "mssp_basic_a": VBCProgram(
        program_id="mssp_basic_a",
        label="MSSP Basic Track A (upside only)",
        contract_template=ContractTerms(
            contract_type="SS", benchmark_pmpm=1100.0,
            quality_withhold_pct=0.02,
            msr_pct=0.02, mlr_pct=1.00,    # mlr=100% effectively no downside
            upside_share=0.40, downside_share=0.0,
            upside_cap_pct=0.10, downside_cap_pct=0.0,
        ),
        on_ramp_difficulty=0.2,
    ),
    "mssp_basic_d": VBCProgram(
        program_id="mssp_basic_d",
        label="MSSP Basic Track D (two-sided)",
        contract_template=ContractTerms(
            contract_type="SS", benchmark_pmpm=1100.0,
            quality_withhold_pct=0.02,
            msr_pct=0.02, mlr_pct=0.02,
            upside_share=0.50, downside_share=0.30,
            upside_cap_pct=0.10, downside_cap_pct=0.05,
        ),
        on_ramp_difficulty=0.5,
    ),
    "mssp_enhanced_e": VBCProgram(
        program_id="mssp_enhanced_e",
        label="MSSP Enhanced Track E (full risk)",
        contract_template=ContractTerms(
            contract_type="SS", benchmark_pmpm=1100.0,
            quality_withhold_pct=0.02,
            msr_pct=0.02, mlr_pct=0.02,
            upside_share=0.75, downside_share=0.75,
            upside_cap_pct=0.20, downside_cap_pct=0.15,
        ),
        on_ramp_difficulty=0.75,
    ),
    "aco_reach_global": VBCProgram(
        program_id="aco_reach_global",
        label="ACO REACH Global Risk",
        contract_template=ContractTerms(
            contract_type="TCC", benchmark_pmpm=1180.0,
            quality_withhold_pct=0.02,
            msr_pct=0.0, mlr_pct=0.0,    # symmetrically full risk
            upside_share=1.00, downside_share=1.00,
            upside_cap_pct=0.10, downside_cap_pct=0.05,
        ),
        on_ramp_difficulty=0.85,
    ),
    "aco_reach_professional": VBCProgram(
        program_id="aco_reach_professional",
        label="ACO REACH Professional",
        contract_template=ContractTerms(
            contract_type="TCC", benchmark_pmpm=1180.0,
            quality_withhold_pct=0.02,
            msr_pct=0.02, mlr_pct=0.02,
            upside_share=0.50, downside_share=0.50,
            upside_cap_pct=0.10, downside_cap_pct=0.05,
        ),
        on_ramp_difficulty=0.55,
    ),
    "ma_delegated_global": VBCProgram(
        program_id="ma_delegated_global",
        label="MA delegated-risk Global",
        contract_template=ContractTerms(
            contract_type="TCC", benchmark_pmpm=1240.0,
            quality_withhold_pct=0.03,
            msr_pct=0.0, mlr_pct=0.0,
            upside_share=0.90, downside_share=0.90,
            upside_cap_pct=0.12, downside_cap_pct=0.10,
        ),
        on_ramp_difficulty=0.80,
    ),
    "commercial_dce": VBCProgram(
        program_id="commercial_dce",
        label="Commercial DCE (employer plan)",
        contract_template=ContractTerms(
            contract_type="TCC", benchmark_pmpm=950.0,
            quality_withhold_pct=0.02,
            msr_pct=0.02, mlr_pct=0.02,
            upside_share=0.50, downside_share=0.50,
            upside_cap_pct=0.10, downside_cap_pct=0.05,
        ),
        on_ramp_difficulty=0.55,
    ),
    "medicaid_mco_partial": VBCProgram(
        program_id="medicaid_mco_partial",
        label="Medicaid MCO (partial risk)",
        contract_template=ContractTerms(
            contract_type="PCC", benchmark_pmpm=520.0,
            quality_withhold_pct=0.02,
            msr_pct=0.05, mlr_pct=0.05,
            upside_share=0.40, downside_share=0.40,
            upside_cap_pct=0.08, downside_cap_pct=0.05,
        ),
        on_ramp_difficulty=0.40,
    ),
}


def list_programs() -> List[VBCProgram]:
    """All registered programs."""
    return list(PROGRAMS.values())
