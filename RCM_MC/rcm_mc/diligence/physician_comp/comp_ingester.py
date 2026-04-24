"""Provider roster ingester.

Accepts payroll + W-2 + 1099 + scheduling inputs as a list of
``Provider`` dataclasses. Computes per-provider comp-per-wRVU,
comp-as-%-of-collections, and comp-per-hour-worked.

This module does NOT parse payroll CSV directly — callers bring
structured data. The typical pipeline is:
    payroll → CSV parser (call-site specific) → Provider list →
    ingest_providers(...) → per-provider metrics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Provider:
    """One provider's comp + productivity record."""
    provider_id: str
    npi: Optional[str] = None
    specialty: str = ""
    employment_status: str = "W2"      # W2 | 1099 | PARTNER | LOCUM
    base_salary_usd: float = 0.0
    productivity_bonus_usd: float = 0.0
    stipend_usd: float = 0.0
    call_coverage_usd: float = 0.0
    admin_usd: float = 0.0
    wrvus_annual: float = 0.0
    collections_annual_usd: float = 0.0
    hours_worked_annual: Optional[float] = None

    @property
    def total_comp_usd(self) -> float:
        return float(
            self.base_salary_usd + self.productivity_bonus_usd
            + self.stipend_usd + self.call_coverage_usd + self.admin_usd
        )

    @property
    def total_directed_comp_usd(self) -> float:
        """Comp components that flow from specific arrangements
        (stipend + call + admin + productivity). Used by the Stark
        red-line check."""
        return float(
            self.productivity_bonus_usd + self.stipend_usd
            + self.call_coverage_usd + self.admin_usd
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id, "npi": self.npi,
            "specialty": self.specialty,
            "employment_status": self.employment_status,
            "base_salary_usd": self.base_salary_usd,
            "productivity_bonus_usd": self.productivity_bonus_usd,
            "stipend_usd": self.stipend_usd,
            "call_coverage_usd": self.call_coverage_usd,
            "admin_usd": self.admin_usd,
            "wrvus_annual": self.wrvus_annual,
            "collections_annual_usd": self.collections_annual_usd,
            "hours_worked_annual": self.hours_worked_annual,
            "total_comp_usd": self.total_comp_usd,
        }


def comp_per_wrvu(p: Provider) -> Optional[float]:
    if p.wrvus_annual <= 0:
        return None
    return p.total_comp_usd / p.wrvus_annual


def comp_pct_collections(p: Provider) -> Optional[float]:
    if p.collections_annual_usd <= 0:
        return None
    return p.total_comp_usd / p.collections_annual_usd


def comp_per_hour(p: Provider) -> Optional[float]:
    if not p.hours_worked_annual or p.hours_worked_annual <= 0:
        return None
    return p.total_comp_usd / float(p.hours_worked_annual)


@dataclass
class RosterMetrics:
    per_provider: List[Dict[str, Any]] = field(default_factory=list)
    total_comp_usd: float = 0.0
    total_wrvus: float = 0.0
    total_collections_usd: float = 0.0
    aggregate_comp_per_wrvu: Optional[float] = None
    aggregate_comp_pct_collections: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def ingest_providers(providers: Iterable[Provider]) -> RosterMetrics:
    """Aggregate per-provider + portfolio-level metrics."""
    rows: List[Dict[str, Any]] = []
    total_comp = 0.0
    total_wrvus = 0.0
    total_coll = 0.0
    for p in providers:
        total_comp += p.total_comp_usd
        total_wrvus += float(p.wrvus_annual or 0.0)
        total_coll += float(p.collections_annual_usd or 0.0)
        rows.append({
            "provider_id": p.provider_id,
            "npi": p.npi,
            "specialty": p.specialty,
            "employment_status": p.employment_status,
            "total_comp_usd": p.total_comp_usd,
            "comp_per_wrvu": comp_per_wrvu(p),
            "comp_pct_collections": comp_pct_collections(p),
            "comp_per_hour": comp_per_hour(p),
            "wrvus_annual": p.wrvus_annual,
        })
    agg_cpr = (total_comp / total_wrvus) if total_wrvus > 0 else None
    agg_pct = (total_comp / total_coll) if total_coll > 0 else None
    return RosterMetrics(
        per_provider=rows,
        total_comp_usd=total_comp,
        total_wrvus=total_wrvus,
        total_collections_usd=total_coll,
        aggregate_comp_per_wrvu=agg_cpr,
        aggregate_comp_pct_collections=agg_pct,
    )
