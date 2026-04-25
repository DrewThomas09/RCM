"""ASC opportunity — volume + EBITDA pickup from CY2026
site-neutral.

When OPPS revenue is haircut, hospitals don't necessarily lose
the procedure — they may continue providing it at the lower
rate. But for elective procedures, the volume often shifts to
ASCs in the same catchment that DON'T trigger the haircut.

This module estimates the ASC's pickup:

  1. Identify hospitals in the ASC's catchment (CBSA-level).
  2. Estimate the volume each is losing (their site-neutral
     revenue-at-risk × volume-elasticity).
  3. Apportion that volume across local ASCs by capacity share.
  4. Compute the ASC's EBITDA pickup at its margin profile.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .codes import SITE_NEUTRAL_CODES_2026, SiteNeutralCategory


@dataclass
class HospitalCompetitor:
    """One hospital in the ASC's catchment."""
    company_name: str
    cbsa: str
    affected_revenue_mm: float    # the HOSPITAL's site-neutral
                                  # affected revenue
    asc_relevant_share: float = 0.6  # fraction of volume that
                                      # could plausibly shift to
                                      # an ASC (E&M can't, drug
                                      # admin can't, imaging /
                                      # certain procedures can)


@dataclass
class ASCOpportunity:
    asc_name: str
    cbsa: str
    capacity_share: float    # 0-1, ASC's share of local capacity
    n_competitors: int
    expected_volume_pickup_mm: float
    expected_ebitda_pickup_mm: float
    capture_rate: float      # what fraction of total local
                             # shifting volume the ASC wins


# Volume-elasticity of demand: when the OPPS rate drops, how
# much of the volume shifts to ASCs? Empirical CMMI data:
# elective + low-acuity → high shift; complex → low shift.
_DEFAULT_VOLUME_ELASTICITY = 0.30


def compute_asc_opportunity(
    asc_name: str,
    cbsa: str,
    *,
    capacity_share: float,
    competitors: List[HospitalCompetitor],
    asc_ebitda_margin: float = 0.30,    # ASCs typically run
                                         # higher margins than
                                         # hospitals
    volume_elasticity: float = _DEFAULT_VOLUME_ELASTICITY,
) -> ASCOpportunity:
    """Estimate the ASC's volume + EBITDA pickup.

    The ASC's pickup = capacity_share × elasticity × Σ each
    competitor's affected revenue × asc_relevant_share.
    """
    # Filter to competitors in the same CBSA (the ASC's reachable
    # market).
    local = [c for c in competitors if c.cbsa == cbsa]
    if not local or capacity_share <= 0:
        return ASCOpportunity(
            asc_name=asc_name, cbsa=cbsa,
            capacity_share=round(capacity_share, 4),
            n_competitors=len(local),
            expected_volume_pickup_mm=0.0,
            expected_ebitda_pickup_mm=0.0,
            capture_rate=0.0,
        )
    # Total shiftable volume from each competitor
    total_shiftable = sum(
        c.affected_revenue_mm * c.asc_relevant_share
        * volume_elasticity
        for c in local
    )
    # ASC captures its capacity share of that total
    captured = total_shiftable * capacity_share
    ebitda_pickup = captured * asc_ebitda_margin

    return ASCOpportunity(
        asc_name=asc_name, cbsa=cbsa,
        capacity_share=round(capacity_share, 4),
        n_competitors=len(local),
        expected_volume_pickup_mm=round(captured, 2),
        expected_ebitda_pickup_mm=round(ebitda_pickup, 2),
        capture_rate=round(capacity_share, 4),
    )
