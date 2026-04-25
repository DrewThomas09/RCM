"""DEI (Diversity, Equity, Inclusion) metrics.

EDCI mandates four headline numbers:

  1. Workforce diversity — % female / % URM (under-represented
     minority) across the company and by management level.
  2. Leadership diversity — board + C-suite composition.
  3. Pay-equity ratio — median female / median male earnings.
  4. Employee turnover.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkforceProfile:
    """Headcount-level inputs the partner has at diligence."""
    total_headcount: int = 0
    female_count: int = 0
    urm_count: int = 0                # under-represented minorities
    female_in_management_count: int = 0
    management_count: int = 0
    board_members: int = 0
    board_female: int = 0
    board_urm: int = 0
    median_male_earnings: float = 0.0
    median_female_earnings: float = 0.0
    annual_voluntary_turnover_count: int = 0


@dataclass
class DEIMetrics:
    pct_female: float
    pct_urm: float
    pct_female_in_management: float
    pct_board_female: float
    pct_board_urm: float
    pay_equity_ratio: float            # female / male
    annual_turnover_rate: float


def _safe_div(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return num / den


def compute_dei_metrics(profile: WorkforceProfile) -> DEIMetrics:
    """Compute the EDCI-mandated DEI ratios."""
    return DEIMetrics(
        pct_female=round(_safe_div(
            profile.female_count, profile.total_headcount), 4),
        pct_urm=round(_safe_div(
            profile.urm_count, profile.total_headcount), 4),
        pct_female_in_management=round(_safe_div(
            profile.female_in_management_count,
            profile.management_count), 4),
        pct_board_female=round(_safe_div(
            profile.board_female, profile.board_members), 4),
        pct_board_urm=round(_safe_div(
            profile.board_urm, profile.board_members), 4),
        pay_equity_ratio=round(_safe_div(
            profile.median_female_earnings,
            profile.median_male_earnings), 4),
        annual_turnover_rate=round(_safe_div(
            profile.annual_voluntary_turnover_count,
            profile.total_headcount), 4),
    )
