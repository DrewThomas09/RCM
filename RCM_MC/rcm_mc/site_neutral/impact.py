"""Net site-neutral impact wrapper — combines hospital risk +
ASC opportunity into a single partner-facing summary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .asc_opportunity import (
    ASCOpportunity, HospitalCompetitor, compute_asc_opportunity,
)
from .revenue_at_risk import (
    HospitalRevenueAtRisk, compute_hospital_revenue_at_risk,
)
from .codes import SiteNeutralCategory


@dataclass
class SiteNeutralImpact:
    """Combined hospital-side risk + ASC-side opportunity."""
    target_name: str
    target_type: str        # "hospital" | "asc" | "mixed"
    hospital_risk: Optional[HospitalRevenueAtRisk] = None
    asc_opportunity: Optional[ASCOpportunity] = None
    net_ebitda_impact_mm: float = 0.0
    notes: str = ""


def compute_site_neutral_impact(
    target_name: str,
    target_type: str = "hospital",
    *,
    # Hospital inputs (when target_type in ("hospital", "mixed"))
    offcampus_pbd_revenue_mm: float = 0.0,
    category_revenue_share: dict = None,
    medicare_share: float = 0.45,
    hospital_ebitda_margin: float = 0.18,
    # ASC inputs (when target_type in ("asc", "mixed"))
    asc_cbsa: str = "",
    asc_capacity_share: float = 0.0,
    asc_competitors: Optional[List[HospitalCompetitor]] = None,
    asc_ebitda_margin: float = 0.30,
) -> SiteNeutralImpact:
    """Compute the net site-neutral impact.

    For ``target_type='hospital'``: returns the hospital-side
    revenue-at-risk only. Net EBITDA impact = -EBITDA at risk.

    For ``target_type='asc'``: returns the ASC opportunity only.
    Net EBITDA impact = +EBITDA pickup.

    For ``target_type='mixed'`` (a hospital that also operates
    a same-CBSA ASC, the textbook hedge): returns both.
    Net EBITDA impact = pickup − at-risk.
    """
    impact = SiteNeutralImpact(
        target_name=target_name,
        target_type=target_type,
    )

    if target_type in ("hospital", "mixed"):
        hr = compute_hospital_revenue_at_risk(
            target_name,
            offcampus_pbd_revenue_mm=offcampus_pbd_revenue_mm,
            category_revenue_share=category_revenue_share or {},
            medicare_share=medicare_share,
            ebitda_margin=hospital_ebitda_margin,
        )
        impact.hospital_risk = hr
        impact.net_ebitda_impact_mm -= hr.total_ebitda_at_risk_mm

    if target_type in ("asc", "mixed"):
        opp = compute_asc_opportunity(
            target_name, asc_cbsa,
            capacity_share=asc_capacity_share,
            competitors=asc_competitors or [],
            asc_ebitda_margin=asc_ebitda_margin,
        )
        impact.asc_opportunity = opp
        impact.net_ebitda_impact_mm += opp.expected_ebitda_pickup_mm

    impact.net_ebitda_impact_mm = round(
        impact.net_ebitda_impact_mm, 2)

    if target_type == "mixed":
        if impact.net_ebitda_impact_mm > 0:
            impact.notes = (
                "Mixed target: ASC pickup > hospital exposure — "
                "the hedge is working.")
        elif impact.net_ebitda_impact_mm < 0:
            impact.notes = (
                "Mixed target: hospital exposure exceeds ASC "
                "pickup — net negative under CY2026.")
    elif (target_type == "hospital"
          and impact.net_ebitda_impact_mm < -2.0):
        impact.notes = (
            "Material hospital exposure — partner should model "
            "the affected line at a lower run-rate from FY2026.")
    elif (target_type == "asc"
          and impact.net_ebitda_impact_mm > 2.0):
        impact.notes = (
            "Meaningful ASC tailwind — incorporate into the bid "
            "case and the 100-day plan.")

    return impact
