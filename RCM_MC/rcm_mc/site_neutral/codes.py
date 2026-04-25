"""CY2026 OPPS site-neutral affected codes.

Categorized by the four major CY2026 site-neutral expansion
buckets, each with the published OPPS-to-PFS payment-reduction
percentage (the percent BELOW the OPPS rate that the lower-site
rate sits at — equivalent to the revenue haircut for hospitals).

These categories aren't an exhaustive code list — they're the
high-revenue category buckets a partner uses to size exposure.
For a precise hospital filing the partner pulls the actual code-
by-code list from the OPPS final rule; this module is for
diligence-grade sizing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class SiteNeutralCategory(str, Enum):
    DRUG_ADMINISTRATION = "drug_administration"
    DIAGNOSTIC_IMAGING = "diagnostic_imaging"
    EM_CODES = "em_codes"
    DIALYSIS_RELATED = "dialysis_related"


@dataclass
class SiteNeutralRule:
    """One category's rule shape."""
    category: SiteNeutralCategory
    label: str
    affected_codes: List[str]    # canonical CPT/HCPCS codes
    payment_reduction_pct: float # 0-1, fraction by which the
                                  # OPPS rate is reduced toward
                                  # the lower-site rate
    effective_year: int = 2026


# Hand-curated CY2026 representative codes per category.
SITE_NEUTRAL_CODES_2026: Dict[SiteNeutralCategory, SiteNeutralRule] = {
    SiteNeutralCategory.DRUG_ADMINISTRATION: SiteNeutralRule(
        category=SiteNeutralCategory.DRUG_ADMINISTRATION,
        label="Drug administration in off-campus PBDs",
        affected_codes=[
            "96365", "96366", "96367", "96368",  # Therapeutic IV
            "96374", "96375", "96376",            # IV push
            "96409", "96411",                     # Chemo IV
            "J0129", "J0178", "J1745", "J3357",   # Specific drugs
        ],
        # CY2026 final rule sets the cap at PFS rate; effective
        # haircut ~40% of the OPPS rate.
        payment_reduction_pct=0.40,
    ),
    SiteNeutralCategory.DIAGNOSTIC_IMAGING: SiteNeutralRule(
        category=SiteNeutralCategory.DIAGNOSTIC_IMAGING,
        label="Diagnostic imaging in off-campus PBDs",
        affected_codes=[
            "70551", "70552", "70553",  # MRI brain
            "71250", "71260", "71270",  # CT chest
            "74176", "74177", "74178",  # CT abdomen
            "76700", "76705",            # Abdominal ultrasound
        ],
        payment_reduction_pct=0.30,
    ),
    SiteNeutralCategory.EM_CODES: SiteNeutralRule(
        category=SiteNeutralCategory.EM_CODES,
        label="E&M visits in off-campus PBDs",
        affected_codes=[
            "99202", "99203", "99204", "99205",  # New patient
            "99212", "99213", "99214", "99215",  # Established
        ],
        payment_reduction_pct=0.40,
    ),
    SiteNeutralCategory.DIALYSIS_RELATED: SiteNeutralRule(
        category=SiteNeutralCategory.DIALYSIS_RELATED,
        label="Dialysis-related ancillary services",
        affected_codes=[
            "90935", "90937",                    # Hemodialysis
            "90945", "90947",                    # Other dialysis
        ],
        # Smaller haircut — narrower set of services already
        # priced near parity.
        payment_reduction_pct=0.15,
    ),
}


def is_site_neutral_code(code: str) -> bool:
    """Quick membership test: is this CPT/HCPCS code on the
    CY2026 site-neutral list?"""
    if not code:
        return False
    code = str(code).strip().upper()
    for rule in SITE_NEUTRAL_CODES_2026.values():
        if code in rule.affected_codes:
            return True
    return False
