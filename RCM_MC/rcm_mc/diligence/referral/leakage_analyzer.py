"""Referral-leakage analyzer.

Given a referral graph (referring-provider → destination), compute
the share of outbound referrals that land within the target's own
network vs. leaked to competitors.

A pragmatic model using CMS Medicare referring-physician data.
When Trella Health / CareJourney feeds are live, the graph
inputs get all-payer coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class LeakageResult:
    total_outbound_referrals: int
    retained_referrals: int
    leaked_referrals: int
    retention_rate: float
    leakage_rate: float
    leaked_dollars_estimate_usd: float
    severity: str                       # LOW | MEDIUM | HIGH

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def analyze_referral_leakage(
    referrals: Iterable[Dict[str, Any]],
    *,
    network_ids: Iterable[str],
    avg_downstream_revenue_per_referral_usd: float = 2500.0,
) -> LeakageResult:
    """Each referral dict: {referring_npi, destination_npi,
    count, avg_downstream_revenue_usd (optional override)}.

    Retention rate = retained / total. Leaked dollars estimate
    multiplies leaked_count × average downstream revenue.
    """
    network = {str(x) for x in network_ids}
    total = 0
    retained = 0
    leaked_dollars = 0.0
    for r in referrals:
        cnt = int(r.get("count", 1) or 1)
        total += cnt
        if str(r.get("destination_npi")) in network:
            retained += cnt
        else:
            leaked_dollars += cnt * float(
                r.get("avg_downstream_revenue_usd")
                or avg_downstream_revenue_per_referral_usd
            )
    leaked = total - retained
    retention = retained / total if total > 0 else 0.0
    leakage = leaked / total if total > 0 else 0.0
    if leakage >= 0.40:
        sev = "HIGH"
    elif leakage >= 0.20:
        sev = "MEDIUM"
    else:
        sev = "LOW"
    return LeakageResult(
        total_outbound_referrals=total,
        retained_referrals=retained,
        leaked_referrals=leaked,
        retention_rate=retention,
        leakage_rate=leakage,
        leaked_dollars_estimate_usd=leaked_dollars,
        severity=sev,
    )
