"""Hospital revenue-at-risk under CY2026 site-neutral.

Inputs:
  • Total OPPS revenue from off-campus PBDs (the only setting
    affected — main-hospital outpatient and inpatient are NOT
    affected).
  • Per-category revenue mix (drug admin / imaging / E&M /
    dialysis).
  • Medicare share (only Medicare beneficiaries are affected;
    commercial / Medicaid pay separate negotiated rates).

Output: per-category $-EBITDA at risk + total at-risk EBITDA
+ implied revenue haircut percentage on the affected line.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .codes import SITE_NEUTRAL_CODES_2026, SiteNeutralCategory


@dataclass
class CategoryExposure:
    category: SiteNeutralCategory
    label: str
    affected_revenue_mm: float
    payment_reduction_pct: float
    revenue_at_risk_mm: float
    ebitda_at_risk_mm: float        # revenue × ebitda margin


@dataclass
class HospitalRevenueAtRisk:
    company_name: str
    total_offcampus_pbd_revenue_mm: float
    medicare_share: float
    ebitda_margin: float
    per_category: List[CategoryExposure] = field(
        default_factory=list)
    total_revenue_at_risk_mm: float = 0.0
    total_ebitda_at_risk_mm: float = 0.0
    implied_haircut_pct: float = 0.0    # weighted average


def compute_hospital_revenue_at_risk(
    company_name: str,
    *,
    offcampus_pbd_revenue_mm: float,
    category_revenue_share: Dict[SiteNeutralCategory, float],
    medicare_share: float = 0.45,
    ebitda_margin: float = 0.18,
) -> HospitalRevenueAtRisk:
    """Compute the hospital's site-neutral revenue-at-risk.

    Args:
      offcampus_pbd_revenue_mm: total revenue from off-campus
        provider-based departments (the only setting CY2026
        site-neutral touches).
      category_revenue_share: how that revenue is distributed
        across the four affected categories. Shares need not
        sum to 1 — any unspecified residual is assumed
        unaffected.
      medicare_share: Medicare beneficiary share in the affected
        line. Only Medicare bills get the site-neutral haircut.
      ebitda_margin: EBITDA / revenue ratio in the affected
        line. Used to convert revenue at risk → EBITDA at risk.

    Returns HospitalRevenueAtRisk with per-category breakdown.
    """
    per_cat: List[CategoryExposure] = []
    total_rar = 0.0
    total_eb_at_risk = 0.0
    affected_total_rev = 0.0

    for cat, rule in SITE_NEUTRAL_CODES_2026.items():
        share = category_revenue_share.get(cat, 0.0)
        if share <= 0:
            continue
        affected_rev = (
            offcampus_pbd_revenue_mm * share * medicare_share)
        affected_total_rev += affected_rev
        rar = affected_rev * rule.payment_reduction_pct
        eb_at_risk = rar * ebitda_margin
        per_cat.append(CategoryExposure(
            category=cat,
            label=rule.label,
            affected_revenue_mm=round(affected_rev, 2),
            payment_reduction_pct=rule.payment_reduction_pct,
            revenue_at_risk_mm=round(rar, 2),
            ebitda_at_risk_mm=round(eb_at_risk, 2),
        ))
        total_rar += rar
        total_eb_at_risk += eb_at_risk

    implied_haircut = (
        total_rar / affected_total_rev
        if affected_total_rev > 0 else 0.0)

    return HospitalRevenueAtRisk(
        company_name=company_name,
        total_offcampus_pbd_revenue_mm=offcampus_pbd_revenue_mm,
        medicare_share=medicare_share,
        ebitda_margin=ebitda_margin,
        per_category=per_cat,
        total_revenue_at_risk_mm=round(total_rar, 2),
        total_ebitda_at_risk_mm=round(total_eb_at_risk, 2),
        implied_haircut_pct=round(implied_haircut, 4),
    )
