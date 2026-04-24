"""Per-provider economic unit math.

Contribution margin for provider p:
    contribution_margin(p) = collections(p) - direct_cost(p) - allocated_overhead(p)

Where:
    collections(p)   = p.collections_annual_usd (from CCD or reported)
    direct_cost(p)   = p.total_comp_usd
    allocated_overhead = roster_overhead × (p.collections / roster_collections)

Overhead allocation is revenue-weighted because that matches how
PE firms attribute shared back-office cost in physician-group
diligence. Alternative allocations (per-wRVU, per-FTE, equal-
share) are supported via the ``method`` parameter but revenue is
the partner default.

FMV-neutral overlay:
    For the "what's the savings if we hold comp at FMV?" scenario
    we compute a second contribution using FMV-anchored comp.
    This is the lever a partner would pull at close via the
    retention structure: rewrite the comp to the p50 FMV anchor,
    drop the loss-makers that are still net-negative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..physician_comp.comp_ingester import Provider
from ..physician_comp.fmv_benchmarks import get_benchmark


# Default overhead as a percentage of total roster collections.
# Benchmark: physician groups typically run 18-28% overhead
# (rent, IT, billing, admin). Use 23% midpoint when not supplied.
DEFAULT_OVERHEAD_PCT_OF_REVENUE: float = 0.23


@dataclass
class ProviderEconomicUnit:
    """Per-provider P&L + FMV-neutral projection."""
    provider_id: str
    npi: Optional[str]
    specialty: str
    employment_status: str

    # Observed P&L
    collections_annual_usd: float
    total_comp_usd: float
    allocated_overhead_usd: float
    contribution_usd: float              # collections - comp - overhead
    contribution_margin_pct: float       # contribution / collections

    # FMV-neutral projection: hold comp at p50 FMV
    fmv_p50_comp_usd: Optional[float]
    fmv_neutral_contribution_usd: Optional[float]
    fmv_neutral_contribution_margin_pct: Optional[float]

    # Classification
    is_loss_maker_observed: bool         # contribution < 0 at current comp
    is_loss_maker_at_fmv: bool           # still negative even at FMV comp
    contribution_rank: int               # 1 = highest contributor

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _collections(p: Provider) -> float:
    return float(max(0.0, p.collections_annual_usd or 0.0))


def direct_cost(p: Provider) -> float:
    """Total comp (base + productivity + stipend + call + admin)."""
    return float(max(0.0, p.total_comp_usd or 0.0))


def allocated_overhead_per_provider(
    providers: Sequence[Provider],
    *,
    total_overhead_usd: Optional[float] = None,
    overhead_pct: float = DEFAULT_OVERHEAD_PCT_OF_REVENUE,
    method: str = "revenue_weighted",
) -> Dict[str, float]:
    """Allocate roster overhead across providers.

    ``total_overhead_usd``: explicit roster overhead dollars; when
    ``None`` we assume ``overhead_pct × total collections``.

    ``method``:
        "revenue_weighted" (default) — allocation proportional to collections
        "equal_share"                — flat per-provider split
        "wrvu_weighted"              — allocation proportional to wRVUs
    """
    total_collections = sum(_collections(p) for p in providers)
    total_wrvus = sum(float(p.wrvus_annual or 0.0) for p in providers)
    n = max(1, len(providers))
    if total_overhead_usd is None:
        total_overhead_usd = overhead_pct * total_collections

    out: Dict[str, float] = {}
    for p in providers:
        if method == "equal_share" or total_collections <= 0:
            out[p.provider_id] = total_overhead_usd / n
        elif method == "wrvu_weighted" and total_wrvus > 0:
            share = float(p.wrvus_annual or 0.0) / total_wrvus
            out[p.provider_id] = total_overhead_usd * share
        else:
            share = _collections(p) / total_collections if total_collections > 0 else 0.0
            out[p.provider_id] = total_overhead_usd * share
    return out


def contribution_margin(
    p: Provider, overhead_usd: float,
) -> float:
    """Per-provider contribution margin in absolute dollars."""
    return _collections(p) - direct_cost(p) - overhead_usd


def _fmv_p50_for(
    p: Provider, ownership_type: str = "independent",
) -> Optional[float]:
    """Look up the specialty p50 FMV anchor for this provider.
    Returns None when no FMV benchmark is available."""
    if not p.specialty:
        return None
    bench = get_benchmark(p.specialty, ownership_type)
    if not bench or bench.get("p50", 0) <= 0:
        return None
    return float(bench["p50"])


def compute_economic_unit(
    p: Provider,
    overhead_usd: float,
    *,
    ownership_type: str = "independent",
    rank: int = 0,
) -> ProviderEconomicUnit:
    """Compute one provider's economic-unit envelope."""
    collections = _collections(p)
    comp = direct_cost(p)
    contribution = collections - comp - overhead_usd
    margin_pct = contribution / collections if collections > 0 else 0.0

    fmv_p50 = _fmv_p50_for(p, ownership_type=ownership_type)
    fmv_contribution: Optional[float] = None
    fmv_margin_pct: Optional[float] = None
    loss_maker_at_fmv: bool = False
    if fmv_p50 is not None:
        fmv_contribution = collections - fmv_p50 - overhead_usd
        fmv_margin_pct = (
            fmv_contribution / collections if collections > 0 else 0.0
        )
        loss_maker_at_fmv = fmv_contribution < 0

    return ProviderEconomicUnit(
        provider_id=p.provider_id,
        npi=p.npi,
        specialty=p.specialty,
        employment_status=p.employment_status,
        collections_annual_usd=collections,
        total_comp_usd=comp,
        allocated_overhead_usd=overhead_usd,
        contribution_usd=contribution,
        contribution_margin_pct=margin_pct,
        fmv_p50_comp_usd=fmv_p50,
        fmv_neutral_contribution_usd=fmv_contribution,
        fmv_neutral_contribution_margin_pct=fmv_margin_pct,
        is_loss_maker_observed=contribution < 0,
        is_loss_maker_at_fmv=loss_maker_at_fmv,
        contribution_rank=rank,
    )
