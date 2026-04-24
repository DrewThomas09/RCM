"""Synthetic-FTE detector.

Reconciles scheduling FTEs vs. billing NPIs vs. 941 payroll
headcount. Flags when billing NPIs exceed scheduled FTEs by
>25% — a historical signature of locum inflation or ghost-
biller configurations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class SyntheticFTEFinding:
    scheduled_fte: float
    billing_npi_count: int
    fte_941_headcount: float
    npi_vs_scheduled_gap_pct: float
    severity: str               # LOW | MEDIUM | HIGH | CRITICAL
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def detect_synthetic_fte(
    *,
    scheduled_fte: float,
    billing_npi_count: int,
    fte_941_headcount: float,
) -> SyntheticFTEFinding:
    """Flag when billing NPIs materially exceed scheduled FTEs."""
    if scheduled_fte <= 0:
        gap_pct = 0.0
    else:
        gap_pct = (billing_npi_count - scheduled_fte) / scheduled_fte
    if gap_pct >= 0.50:
        sev = "CRITICAL"
        narrative = (
            f"Billing NPIs ({billing_npi_count}) exceed scheduled "
            f"FTE ({scheduled_fte:.0f}) by {gap_pct*100:.0f}%. "
            f"Substantial ghost-biller / locum-inflation risk."
        )
    elif gap_pct >= 0.25:
        sev = "HIGH"
        narrative = (
            f"Billing NPIs outnumber scheduled FTE by "
            f"{gap_pct*100:.0f}%. Investigate locum composition + "
            f"billing-privilege authorisations."
        )
    elif gap_pct >= 0.10:
        sev = "MEDIUM"
        narrative = f"Modest NPI/FTE gap {gap_pct*100:.0f}%."
    else:
        sev = "LOW"
        narrative = "NPI and scheduled FTE aligned."
    return SyntheticFTEFinding(
        scheduled_fte=scheduled_fte,
        billing_npi_count=billing_npi_count,
        fte_941_headcount=fte_941_headcount,
        npi_vs_scheduled_gap_pct=gap_pct,
        severity=sev,
        narrative=narrative,
    )
