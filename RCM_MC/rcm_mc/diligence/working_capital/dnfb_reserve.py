"""Discharged-Not-Final-Billed (DNFB) reserve estimator.

DNFB dollars = claims discharged but not yet billed by the
close date. A typical acute hospital carries 3-5 days of DNFB;
a healthy RCM carries 2-3. DNFB above 5 days is a liquidity
concern + a revenue-cycle inefficiency signal.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class DNFBResult:
    dnfb_days: float
    dnfb_dollars_usd: float
    benchmark_days: float
    excess_days: float
    severity: str                    # LOW | MEDIUM | HIGH

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def estimate_dnfb(
    *,
    discharged_not_billed_claim_count: int,
    avg_claim_value_usd: float,
    avg_daily_discharges: float,
    benchmark_days: float = 3.0,
) -> DNFBResult:
    """Given discharged-unbilled claim counts + avg value + daily
    discharge rate, estimate DNFB days + dollars + excess vs
    benchmark."""
    days = (
        discharged_not_billed_claim_count / avg_daily_discharges
        if avg_daily_discharges > 0 else 0.0
    )
    dollars = discharged_not_billed_claim_count * avg_claim_value_usd
    excess = max(0.0, days - benchmark_days)
    if excess >= 3:
        sev = "HIGH"
    elif excess >= 1.5:
        sev = "MEDIUM"
    else:
        sev = "LOW"
    return DNFBResult(
        dnfb_days=days,
        dnfb_dollars_usd=dollars,
        benchmark_days=benchmark_days,
        excess_days=excess,
        severity=sev,
    )
