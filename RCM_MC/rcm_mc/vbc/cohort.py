"""Cohort-level data structures.

A Cohort is a homogeneous group of attributed lives (e.g. "ACO REACH
2025 — Houston metro — high-acuity duals"). A CohortPanel is the
full attributed population — the union of cohorts that an
operator manages.

Why cohorts (instead of per-member): partner-facing diligence
operates at this granularity. Per-member modeling drowns in
sampling noise for any panel <50K; cohort-level shrinkage
(via the Bayesian helper in ``shrinkage.py``) is what keeps
the LTV math honest at typical PE-target panel sizes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Cohort:
    """A homogeneous attributed-lives bucket."""
    cohort_id: str
    name: str = ""
    size: int = 0
    avg_age: float = 65.0
    pct_female: float = 0.55
    pct_dual_eligible: float = 0.20  # qualifies for both Medicare + Medicaid
    pct_lis: float = 0.18            # Low-Income Subsidy
    pct_originally_disabled: float = 0.08

    # CMS-HCC inputs — count of HCCs and weighted score per beneficiary.
    # ``hcc_distribution`` maps HCC code → fraction of cohort with the
    # condition. Used by ``hcc.compute_hcc_score`` to derive the
    # per-member risk score.
    hcc_distribution: Dict[str, float] = field(default_factory=dict)

    # Observed quality + utilization — the past-year baselines that
    # drive shared-savings projections.
    annual_pmpm_cost: float = 1100.0       # observed total medical PMPM
    quality_score: float = 0.85            # 0-1 composite
    expected_attrition_rate: float = 0.10  # annual % leaving panel

    # Region (CBSA) for benchmark anchoring — an empty value means
    # use the national benchmark.
    cbsa: str = ""

    def annual_cost(self) -> float:
        """Total expected medical spend across the cohort, in $."""
        return float(self.size) * float(self.annual_pmpm_cost) * 12.0


@dataclass
class CohortPanel:
    """Top-level container — a roll-up of multiple cohorts."""
    panel_id: str
    operator_name: str = ""
    cohorts: List[Cohort] = field(default_factory=list)
    benchmark_year: int = 2026

    def total_lives(self) -> int:
        return sum(c.size for c in self.cohorts)

    def cohort(self, cohort_id: str) -> Optional[Cohort]:
        return next((c for c in self.cohorts
                     if c.cohort_id == cohort_id), None)

    def total_annual_cost(self) -> float:
        return sum(c.annual_cost() for c in self.cohorts)
