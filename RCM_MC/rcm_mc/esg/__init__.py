"""ESG-HealthcarePacket — sustainability + governance disclosure
for healthcare PE.

85% of LPs prioritized sustainability in their 2025 surveys; PE
sponsors increasingly need EDCI-aligned reporting + ISSB IFRS
S1/S2 disclosures. This package gives partners the math + the
disclosure templates:

  • Scope 1/2/3 carbon accounting per facility, with healthcare-
    specific emission factors (anesthetic gas, sevoflurane,
    N2O, dialysis water).
  • DEI metrics (workforce composition, leadership diversity,
    pay-equity ratio).
  • Governance — CPOM/MSO transparency scoring (corporate
    practice of medicine compliance, friendly-PC structure
    disclosure).
  • EDCI (ESG Data Convergence Initiative) PE-specific scorecard.
  • ISSB IFRS S1 (general) + S2 (climate) disclosure rendering.

Public API::

    from rcm_mc.esg import (
        Facility, FacilityType,
        compute_scope_1_2_3,
        compute_dei_metrics, DEIMetrics,
        score_governance, GovernanceScore,
        compute_edci_scorecard, EDCIScorecard,
        render_lp_disclosure,
    )
"""
from .carbon import (
    Facility, FacilityType,
    compute_scope_1_2_3, CarbonFootprint,
)
from .dei import compute_dei_metrics, DEIMetrics, WorkforceProfile
from .governance import (
    score_governance, GovernanceScore, GovernanceProfile,
)
from .edci import compute_edci_scorecard, EDCIScorecard
from .disclosure import render_lp_disclosure
from .issb import (
    ISSBPillar,
    ISSBStandardReport,
    LPPackage,
    render_ifrs_s1,
    render_ifrs_s2,
    render_issb_markdown,
    build_lp_package,
    render_lp_package_markdown,
)

__all__ = [
    "Facility", "FacilityType",
    "CarbonFootprint", "compute_scope_1_2_3",
    "WorkforceProfile", "DEIMetrics", "compute_dei_metrics",
    "GovernanceProfile", "GovernanceScore", "score_governance",
    "EDCIScorecard", "compute_edci_scorecard",
    "render_lp_disclosure",
    "ISSBPillar", "ISSBStandardReport", "LPPackage",
    "render_ifrs_s1", "render_ifrs_s2",
    "render_issb_markdown",
    "build_lp_package", "render_lp_package_markdown",
]
