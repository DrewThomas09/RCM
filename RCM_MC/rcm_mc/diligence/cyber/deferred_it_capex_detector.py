"""IT capex underinvestment detector.

Flags targets overdue for EHR replacement or running understaffed
IT. EHR replacement cycles: Epic 7-10y, community EHRs 5-7y.
IT FTE staffing ratio: industry benchmark is ~1 IT FTE per $8-10M
revenue for hospitals.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ITCapexFinding:
    severity: str                  # LOW | MEDIUM | HIGH | CRITICAL
    ehr_replacement_overdue_years: float
    it_staffing_ratio_gap_pct: float
    estimated_replacement_cost_usd: float
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


# EHR replacement cost bands (industry aggregates — ~$20M for
# community hospitals, $100M+ for large systems).
def _replacement_cost_band(ehr_vendor: str, revenue_usd: float) -> float:
    v = ehr_vendor.upper() if ehr_vendor else ""
    if "EPIC" in v:
        return max(20_000_000, revenue_usd * 0.10)
    if "CERNER" in v or "ORACLE" in v:
        return max(15_000_000, revenue_usd * 0.09)
    # Community EHRs
    return max(5_000_000, revenue_usd * 0.06)


def detect_deferred_it_capex(
    *,
    ehr_vendor: str,
    years_since_ehr_implementation: float,
    annual_revenue_usd: float,
    it_fte_count: float,
    benchmark_revenue_per_it_fte_usd: float = 9_000_000.0,
) -> ITCapexFinding:
    """Return a finding. The severity rollup considers both EHR age
    and IT staffing ratio."""
    v = (ehr_vendor or "").upper()
    expected_cycle = 9.0 if "EPIC" in v else (
        8.0 if ("CERNER" in v or "ORACLE" in v) else 6.0
    )
    overdue = max(0.0, years_since_ehr_implementation - expected_cycle)

    expected_ftes = (
        annual_revenue_usd / benchmark_revenue_per_it_fte_usd
        if benchmark_revenue_per_it_fte_usd > 0 else 0.0
    )
    if expected_ftes > 0:
        staffing_gap_pct = max(
            0.0, (expected_ftes - it_fte_count) / expected_ftes,
        )
    else:
        staffing_gap_pct = 0.0

    replacement_cost = (
        _replacement_cost_band(ehr_vendor, annual_revenue_usd)
        if overdue > 0 else 0.0
    )

    # Severity rollup.
    if overdue >= 3 and staffing_gap_pct >= 0.30:
        severity = "CRITICAL"
    elif overdue >= 2 or staffing_gap_pct >= 0.30:
        severity = "HIGH"
    elif overdue >= 1 or staffing_gap_pct >= 0.15:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    parts = []
    if overdue > 0:
        parts.append(
            f"EHR {ehr_vendor} is {overdue:.0f}y overdue "
            f"(expected cycle {expected_cycle:.0f}y)"
        )
    if staffing_gap_pct > 0.05:
        parts.append(
            f"IT staffing gap {staffing_gap_pct*100:.0f}% vs benchmark"
        )
    if replacement_cost > 0:
        parts.append(
            f"Estimated replacement cost ${replacement_cost:,.0f}"
        )
    narrative = "; ".join(parts) or "Within benchmark."

    return ITCapexFinding(
        severity=severity,
        ehr_replacement_overdue_years=overdue,
        it_staffing_ratio_gap_pct=staffing_gap_pct,
        estimated_replacement_cost_usd=replacement_cost,
        narrative=narrative,
    )
