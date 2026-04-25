"""EDCI (ESG Data Convergence Initiative) PE-specific scorecard.

EDCI is the standardized ESG reporting framework adopted by the
major LPs (CalPERS, CPP, GIC). Six headline metrics + a maturity
band. We compute the band from the underlying carbon, DEI, and
governance inputs already produced in this package.

Maturity bands:
  Beginner    — fewer than 3 metrics reported
  Reporting   — 3-5 metrics reported
  Comprehensive — 6+ metrics + scope 3 disclosed
  Aligned     — Comprehensive + ISSB IFRS S1/S2 attestation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .carbon import aggregate_portfolio_footprint, Facility
from .dei import DEIMetrics
from .governance import GovernanceScore


@dataclass
class EDCIScorecard:
    company: str
    metric_count: int
    maturity_band: str
    metrics: Dict[str, Any] = field(default_factory=dict)


def compute_edci_scorecard(
    company_name: str,
    *,
    facilities: Optional[List[Facility]] = None,
    dei: Optional[DEIMetrics] = None,
    governance: Optional[GovernanceScore] = None,
    issb_attested: bool = False,
    cybersecurity_attested: bool = False,
    work_related_injuries: Optional[int] = None,
    net_new_hires: Optional[int] = None,
) -> EDCIScorecard:
    """Build the EDCI scorecard. Each input can be omitted if the
    diligence team hasn't pulled it yet — the scorecard documents
    what's missing in the maturity band."""
    metrics: Dict[str, Any] = {}
    metric_count = 0

    if facilities:
        carbon = aggregate_portfolio_footprint(facilities)
        metrics["scope_1_2_kgco2e"] = (
            carbon["scope_1_kgco2e"] + carbon["scope_2_kgco2e"])
        metrics["scope_3_kgco2e"] = carbon["scope_3_kgco2e"]
        metric_count += 2

    if dei:
        metrics["pct_female_workforce"] = dei.pct_female
        metrics["pct_female_management"] = dei.pct_female_in_management
        metrics["pay_equity_ratio"] = dei.pay_equity_ratio
        metrics["voluntary_turnover_rate"] = dei.annual_turnover_rate
        metric_count += 4

    if governance:
        metrics["governance_composite"] = governance.composite
        metrics["board_independence"] = governance.board_independence
        metric_count += 2

    if work_related_injuries is not None:
        metrics["work_related_injuries"] = work_related_injuries
        metric_count += 1

    if net_new_hires is not None:
        metrics["net_new_hires"] = net_new_hires
        metric_count += 1

    if cybersecurity_attested:
        metrics["cybersecurity_attestation"] = True
        metric_count += 1

    # Maturity banding
    has_scope_3 = "scope_3_kgco2e" in metrics
    if metric_count < 3:
        band = "Beginner"
    elif metric_count <= 5:
        band = "Reporting"
    elif has_scope_3 and metric_count >= 6:
        if issb_attested:
            band = "Aligned"
        else:
            band = "Comprehensive"
    else:
        band = "Reporting"

    return EDCIScorecard(
        company=company_name,
        metric_count=metric_count,
        maturity_band=band,
        metrics=metrics,
    )
