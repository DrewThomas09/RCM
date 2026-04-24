"""Provider revenue concentration + departure stress test.

"Provider X controls $Y of revenue" is the call-out line the
partner-voice memo wants. This module produces both the
concentration stats and a departure-stress projection: what
happens to revenue if the top-N providers leave post-close.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping


@dataclass
class ProviderConcentrationResult:
    total_revenue_usd: float
    provider_count: int
    top1_share: float
    top3_share: float
    top5_share: float
    top10_share: float
    hhi_providers: float
    top_providers: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def compute_provider_concentration(
    revenue_by_provider: Mapping[str, float],
    *,
    top_n: int = 10,
) -> ProviderConcentrationResult:
    """Compute top-N shares + provider HHI."""
    items = sorted(
        revenue_by_provider.items(),
        key=lambda kv: float(kv[1] or 0.0),
        reverse=True,
    )
    total = sum(float(v) for v in revenue_by_provider.values())
    if total <= 0:
        return ProviderConcentrationResult(
            total_revenue_usd=0.0,
            provider_count=len(items),
            top1_share=0.0, top3_share=0.0, top5_share=0.0,
            top10_share=0.0, hhi_providers=0.0,
        )
    shares = [(k, float(v) / total) for k, v in items]
    def prefix(n): return sum(s for _, s in shares[:n])
    hhi = sum((s * 100) ** 2 for _, s in shares)
    return ProviderConcentrationResult(
        total_revenue_usd=total,
        provider_count=len(items),
        top1_share=prefix(1),
        top3_share=prefix(3),
        top5_share=prefix(5),
        top10_share=prefix(10),
        hhi_providers=hhi,
        top_providers=[
            {"provider": k, "revenue_usd": float(v), "share": s}
            for (k, v), (_, s) in zip(items[:top_n], shares[:top_n])
        ],
    )


@dataclass
class DepartureStressResult:
    departed_providers: List[str]
    revenue_lost_usd: float
    revenue_lost_pct: float
    severity: str                       # LOW | MEDIUM | HIGH | CRITICAL


def stress_test_departures(
    revenue_by_provider: Mapping[str, float],
    departing: Iterable[str],
    *,
    follow_on_retention_pct: float = 0.5,
) -> DepartureStressResult:
    """Simulate revenue loss if ``departing`` providers leave
    post-close. ``follow_on_retention_pct`` is the fraction of
    their book that follows a replacement hire vs. departs.

    Revenue lost = sum(departing_revenue × (1 - retention)).
    """
    total = sum(float(v) for v in revenue_by_provider.values()) or 1.0
    lost = 0.0
    dep_list: List[str] = []
    for p in departing:
        v = float(revenue_by_provider.get(p, 0.0) or 0.0)
        lost += v * (1.0 - follow_on_retention_pct)
        dep_list.append(p)
    pct = lost / total
    if pct >= 0.20:
        sev = "CRITICAL"
    elif pct >= 0.10:
        sev = "HIGH"
    elif pct >= 0.05:
        sev = "MEDIUM"
    else:
        sev = "LOW"
    return DepartureStressResult(
        departed_providers=dep_list,
        revenue_lost_usd=lost,
        revenue_lost_pct=pct,
        severity=sev,
    )
