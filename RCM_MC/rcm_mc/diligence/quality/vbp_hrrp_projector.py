"""VBP / HRRP / HAC three-year forward penalty/bonus projector.

Given a hospital's current Care Compare star rating, HRRP
excess-readmission ratios, and HAC score, project the reimbursement
impact under current CMS formulas over a 3-year forward horizon.

Public CMS parameters:
    VBP:  0.5% max bonus/penalty to base MS-DRG payments, scaled by
          Total Performance Score (TPS)
    HRRP: 0-3% of base MS-DRG payments withheld based on
          excess-readmission ratio (ERR) by condition
    HAC:  1% payment reduction for hospitals in the worst quartile
          of the CMS Hospital-Acquired Conditions Reduction Program
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class QualityPenaltyProjection:
    star_rating: int
    tps_vbp_adjustment_pct: float
    hrrp_penalty_pct: float
    hac_penalty_pct: float
    total_adjustment_pct: float
    year1_dollar_impact_usd: float
    year2_dollar_impact_usd: float
    year3_dollar_impact_usd: float
    severity: str                    # LOW | MEDIUM | HIGH | CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def project_vbp_hrrp(
    *,
    star_rating: int,
    excess_readmission_ratios: Dict[str, float],   # by condition
    hac_worst_quartile: bool,
    base_ms_drg_payments_annual_usd: float,
    improvement_trajectory_pct_per_year: float = 0.0,
) -> QualityPenaltyProjection:
    """Project 3-year penalty/bonus impact.

    ``improvement_trajectory_pct_per_year`` can be positive (quality
    improvement reduces the penalty) or negative (quality decay)."""
    # VBP: map star rating to TPS adjustment.
    # 5★ → +0.5%, 4★ → +0.2%, 3★ → 0%, 2★ → -0.3%, 1★ → -0.5%
    tps_map = {5: 0.005, 4: 0.002, 3: 0.0, 2: -0.003, 1: -0.005}
    vbp = tps_map.get(int(star_rating), 0.0)

    # HRRP: average ERR above 1.0 = excess readmissions;
    # CMS penalty ~0.3% per 0.05 ERR above 1.0, capped at 3%.
    avg_err = (
        sum(excess_readmission_ratios.values())
        / max(len(excess_readmission_ratios), 1)
        if excess_readmission_ratios else 1.0
    )
    if avg_err > 1.0:
        hrrp = -min(0.03, (avg_err - 1.0) / 0.05 * 0.003)
    else:
        hrrp = 0.0

    # HAC: flat 1% penalty for worst quartile.
    hac = -0.01 if hac_worst_quartile else 0.0

    total_y1 = vbp + hrrp + hac
    total_y2 = total_y1 + improvement_trajectory_pct_per_year
    total_y3 = total_y2 + improvement_trajectory_pct_per_year

    dollar_y1 = base_ms_drg_payments_annual_usd * total_y1
    dollar_y2 = base_ms_drg_payments_annual_usd * total_y2
    dollar_y3 = base_ms_drg_payments_annual_usd * total_y3

    annual_impact = min(dollar_y1, dollar_y2, dollar_y3)
    if annual_impact <= -5_000_000:
        sev = "CRITICAL"
    elif annual_impact <= -1_000_000:
        sev = "HIGH"
    elif annual_impact < 0:
        sev = "MEDIUM"
    else:
        sev = "LOW"

    return QualityPenaltyProjection(
        star_rating=int(star_rating),
        tps_vbp_adjustment_pct=vbp,
        hrrp_penalty_pct=hrrp,
        hac_penalty_pct=hac,
        total_adjustment_pct=total_y1,
        year1_dollar_impact_usd=dollar_y1,
        year2_dollar_impact_usd=dollar_y2,
        year3_dollar_impact_usd=dollar_y3,
        severity=sev,
    )
