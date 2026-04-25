"""DiligenceDossier — input shape for the synthesis runner."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional  # noqa: F401


@dataclass
class DiligenceDossier:
    """Everything a partner could plausibly know about a target,
    bundled into one input. Most fields are optional — the
    synthesis runner fails open per-packet."""
    deal_name: str
    sector: str
    states: List[str] = field(default_factory=list)
    ebitda_mm: float = 0.0
    revenue_mm: float = 0.0

    # Optional inputs unlocking specific packets
    pricing_store: Any = None             # for PayerNegotiationSimulator
    target_npis: List[str] = field(default_factory=list)
    target_codes: List[str] = field(default_factory=list)

    cohort: Any = None                    # rcm_mc.vbc.Cohort
    contract: Any = None                  # rcm_mc.vbc.ContractTerms

    referral_graph: Any = None            # rcm_mc.referral.ReferralGraph
    platform_orgs: List[str] = field(default_factory=list)

    regulatory_corpus: Any = None         # rcm_mc.regulatory.RegulatoryCorpus

    financial_panel: Optional[Dict[str, Any]] = None  # QoE input

    # BuyAndBuildOptimizer inputs
    platform: Any = None                  # rcm_mc.buyandbuild.Platform
    add_on_candidates: List[Any] = field(default_factory=list)

    # ExitReadinessPacket inputs
    exit_target: Any = None               # rcm_mc.exit_readiness.ExitTarget

    # VBC-ContractValuator inputs (besides cohort)
    program_ids: List[str] = field(default_factory=list)

    # ESG-HealthcarePacket inputs
    facilities: List[Any] = field(default_factory=list)         # esg.Facility
    workforce: Any = None                                       # esg.WorkforceProfile
    governance_profile: Any = None                              # esg.GovernanceProfile
    issb_attested: bool = False
    cybersecurity_attested: bool = False

    # DealComparablesEngine inputs
    deal_corpus: List[Dict[str, Any]] = field(default_factory=list)
    target_deal_profile: Optional[Dict[str, Any]] = None
    comparables_method: str = "psm"
    comparables_k: int = 15


@dataclass
class SynthesisResult:
    """Compiled output across every packet that ran."""
    deal_name: str
    sections_run: List[str] = field(default_factory=list)
    missing_inputs: List[str] = field(default_factory=list)
    payer_negotiation: Any = None
    cohort_ltv: Any = None
    referral_leakage: Any = None
    regulatory_exposure: Any = None
    qoe_result: Any = None
    buyandbuild_optimal: Any = None
    exit_readiness: Any = None
    vbc_track_choice: Any = None
    esg_scorecard: Any = None
    esg_disclosure_md: str = ""
    comparables: Any = None
