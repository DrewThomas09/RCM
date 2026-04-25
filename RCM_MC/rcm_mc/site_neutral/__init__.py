"""Site-Neutral Module — CY2026 OPPS impact modeling.

CMS' Outpatient Prospective Payment System (OPPS) historically
paid hospital outpatient departments materially more than ASCs
or physician offices for the same procedure. Site-neutral
payment rules cap the OPPS payment at the lower-site rate for
specified services. The CY2026 OPPS final rule expands the
site-neutral list to include:

  • Drug administration in off-campus provider-based departments
  • Several diagnostic-imaging codes
  • Additional E&M codes already paid at the site-neutral rate
    in 2025 but with extended scope

For a hospital target, this is revenue-at-risk: the affected
revenue lines lose ~30-50% of their reimbursement. For an ASC
target, it's an opportunity: hospitals lose volume → some flows
to nearby ASCs that don't trigger the site-neutral haircut.

Three modules:

  • codes        — CY2026 affected CPT/HCPCS code list
                   organized by category, with the site-neutral
                   payment-reduction percentage CMS specified
                   for each.
  • revenue_at_risk — hospital exposure calculator: given the
                   hospital's affected-line revenue mix +
                   payer-mix (Medicare share is the binding
                   factor), compute $-EBITDA at risk.
  • asc_opportunity — ASC capture model: given the ASC's
                   geographic catchment + service-line
                   capability, estimate the volume + margin
                   pickup from neighboring hospitals losing
                   site-neutral revenue.

Public API::

    from rcm_mc.site_neutral import (
        SITE_NEUTRAL_CODES_2026,
        is_site_neutral_code,
        compute_hospital_revenue_at_risk,
        HospitalRevenueAtRisk,
        compute_asc_opportunity,
        ASCOpportunity,
        compute_site_neutral_impact,
        SiteNeutralImpact,
    )
"""
from .codes import (
    SITE_NEUTRAL_CODES_2026,
    is_site_neutral_code,
    SiteNeutralCategory,
)
from .revenue_at_risk import (
    compute_hospital_revenue_at_risk,
    HospitalRevenueAtRisk,
)
from .asc_opportunity import (
    compute_asc_opportunity,
    ASCOpportunity,
)
from .impact import (
    compute_site_neutral_impact,
    SiteNeutralImpact,
)

__all__ = [
    "SITE_NEUTRAL_CODES_2026",
    "is_site_neutral_code",
    "SiteNeutralCategory",
    "compute_hospital_revenue_at_risk",
    "HospitalRevenueAtRisk",
    "compute_asc_opportunity",
    "ASCOpportunity",
    "compute_site_neutral_impact",
    "SiteNeutralImpact",
]
