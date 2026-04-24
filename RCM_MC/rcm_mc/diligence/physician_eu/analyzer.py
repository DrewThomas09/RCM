"""Roster-level analyzer — rank by contribution, find loss-makers,
quantify the drop-them-at-close bridge lever.

Outputs the partner-facing "Roster Optimization" section:

    - per-provider contribution envelope (revenue / comp / overhead
      / contribution / margin pct)
    - contribution rank within roster
    - loss-makers at current comp vs loss-makers even at FMV
    - total EBITDA uplift from removing the loss-maker tail via
      retention structure or earnout (with FMV and revenue-margin
      assumptions surfaced)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..physician_comp.comp_ingester import Provider
from .features import (
    DEFAULT_OVERHEAD_PCT_OF_REVENUE, ProviderEconomicUnit,
    allocated_overhead_per_provider, compute_economic_unit,
)


@dataclass
class RosterOptimization:
    """The bridge-lever output — the 'drop these named providers'
    recommendation partners can act on at close."""
    candidates: List[ProviderEconomicUnit] = field(default_factory=list)
    total_comp_removed_usd: float = 0.0
    total_revenue_forgone_usd: float = 0.0
    # Annual EBITDA uplift: the providers' current comp minus
    # their contribution (which may be negative).  Dropping a
    # loss-maker converts a negative contribution into a positive
    # EBITDA lift — their comp is no longer spent AND their
    # (negative) contribution is no longer a drag.
    ebitda_uplift_usd: float = 0.0
    ebitda_uplift_pct_of_roster: float = 0.0
    # Confidence on realization — captures whether partners can
    # plausibly effect the drop via retention-structure negotiation.
    confidence: str = "MEDIUM"              # LOW / MEDIUM / HIGH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidates": [c.to_dict() for c in self.candidates],
            "total_comp_removed_usd": self.total_comp_removed_usd,
            "total_revenue_forgone_usd": self.total_revenue_forgone_usd,
            "ebitda_uplift_usd": self.ebitda_uplift_usd,
            "ebitda_uplift_pct_of_roster": self.ebitda_uplift_pct_of_roster,
            "confidence": self.confidence,
        }


@dataclass
class EconomicUnitReport:
    """Roster-level output surface."""
    units: List[ProviderEconomicUnit] = field(default_factory=list)
    roster_size: int = 0

    # Aggregates
    total_collections_usd: float = 0.0
    total_comp_usd: float = 0.0
    total_overhead_usd: float = 0.0
    total_contribution_usd: float = 0.0
    aggregate_contribution_margin_pct: float = 0.0

    # Counts
    loss_makers_at_current_comp: int = 0
    loss_makers_at_fmv_comp: int = 0

    # Top concentration — how much of the positive contribution
    # comes from the top-10% of providers?
    top_decile_contribution_share: float = 0.0

    # Partner-facing: drop-the-loss-maker-tail recommendation
    optimization: Optional[RosterOptimization] = None

    # Inputs used for transparency
    overhead_pct: float = DEFAULT_OVERHEAD_PCT_OF_REVENUE
    overhead_method: str = "revenue_weighted"
    ownership_type: str = "independent"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roster_size": self.roster_size,
            "total_collections_usd": self.total_collections_usd,
            "total_comp_usd": self.total_comp_usd,
            "total_overhead_usd": self.total_overhead_usd,
            "total_contribution_usd": self.total_contribution_usd,
            "aggregate_contribution_margin_pct":
                self.aggregate_contribution_margin_pct,
            "loss_makers_at_current_comp":
                self.loss_makers_at_current_comp,
            "loss_makers_at_fmv_comp":
                self.loss_makers_at_fmv_comp,
            "top_decile_contribution_share":
                self.top_decile_contribution_share,
            "units": [u.to_dict() for u in self.units],
            "optimization": (
                self.optimization.to_dict() if self.optimization else None
            ),
            "overhead_pct": self.overhead_pct,
            "overhead_method": self.overhead_method,
            "ownership_type": self.ownership_type,
        }


# ────────────────────────────────────────────────────────────────────
# Confidence band
# ────────────────────────────────────────────────────────────────────

def _confidence_for_optimization(
    n_candidates: int, n_roster: int, has_fmv_data: bool,
) -> str:
    """Confidence on the partner's ability to execute the drop.

    HIGH   — ≤3 candidates, fewer than 20% of the roster, and the
             loss-makers are still loss-makers at FMV (so the drop
             is structurally justified — not a comp negotiation).
    MEDIUM — small share of roster; drop is plausible via retention
             structure.
    LOW    — many candidates OR no FMV benchmarks to justify the
             drop with.
    """
    if not has_fmv_data:
        return "LOW"
    if n_roster == 0:
        return "LOW"
    share = n_candidates / n_roster
    if n_candidates <= 3 and share <= 0.20:
        return "HIGH"
    if share <= 0.30:
        return "MEDIUM"
    return "LOW"


def _build_optimization(
    units: List[ProviderEconomicUnit],
    total_collections: float,
    total_comp: float,
) -> RosterOptimization:
    """Flag the providers who are loss-makers even at FMV comp —
    those are the structurally-negative ones a partner drops at
    close via retention negotiation."""
    candidates = [u for u in units if u.is_loss_maker_at_fmv]
    if not candidates:
        return RosterOptimization(
            confidence=_confidence_for_optimization(
                0, len(units),
                has_fmv_data=any(
                    u.fmv_p50_comp_usd is not None for u in units
                ),
            ),
        )

    total_comp_removed = sum(u.total_comp_usd for u in candidates)
    total_revenue_forgone = sum(u.collections_annual_usd for u in candidates)
    # EBITDA uplift = revenue forgone - comp removed - overhead freed.
    # If contribution is negative, removing the provider lifts EBITDA
    # by |contribution|. Sum of negative contributions = uplift.
    ebitda_uplift = sum(
        -u.contribution_usd for u in candidates
        if u.contribution_usd < 0
    )
    baseline_ebitda = total_collections - total_comp
    uplift_pct = (
        ebitda_uplift / baseline_ebitda
        if baseline_ebitda > 0 else 0.0
    )
    has_fmv_data = any(u.fmv_p50_comp_usd is not None for u in units)
    conf = _confidence_for_optimization(
        len(candidates), len(units), has_fmv_data,
    )
    return RosterOptimization(
        candidates=candidates,
        total_comp_removed_usd=total_comp_removed,
        total_revenue_forgone_usd=total_revenue_forgone,
        ebitda_uplift_usd=ebitda_uplift,
        ebitda_uplift_pct_of_roster=uplift_pct,
        confidence=conf,
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def analyze_roster_eu(
    providers: Sequence[Provider],
    *,
    total_overhead_usd: Optional[float] = None,
    overhead_pct: float = DEFAULT_OVERHEAD_PCT_OF_REVENUE,
    overhead_method: str = "revenue_weighted",
    ownership_type: str = "independent",
) -> EconomicUnitReport:
    """Run the full economic-unit analysis against a roster."""
    providers = list(providers)
    n = len(providers)
    if n == 0:
        return EconomicUnitReport(
            overhead_pct=overhead_pct,
            overhead_method=overhead_method,
            ownership_type=ownership_type,
        )

    overhead_allocation = allocated_overhead_per_provider(
        providers,
        total_overhead_usd=total_overhead_usd,
        overhead_pct=overhead_pct,
        method=overhead_method,
    )

    # Compute unranked units first, then assign ranks.
    units_unranked: List[ProviderEconomicUnit] = [
        compute_economic_unit(
            p,
            overhead_allocation.get(p.provider_id, 0.0),
            ownership_type=ownership_type,
        )
        for p in providers
    ]
    # Sort by contribution descending, assign rank
    units_unranked.sort(
        key=lambda u: u.contribution_usd, reverse=True,
    )
    units: List[ProviderEconomicUnit] = []
    for idx, u in enumerate(units_unranked, start=1):
        units.append(ProviderEconomicUnit(
            provider_id=u.provider_id, npi=u.npi,
            specialty=u.specialty,
            employment_status=u.employment_status,
            collections_annual_usd=u.collections_annual_usd,
            total_comp_usd=u.total_comp_usd,
            allocated_overhead_usd=u.allocated_overhead_usd,
            contribution_usd=u.contribution_usd,
            contribution_margin_pct=u.contribution_margin_pct,
            fmv_p50_comp_usd=u.fmv_p50_comp_usd,
            fmv_neutral_contribution_usd=u.fmv_neutral_contribution_usd,
            fmv_neutral_contribution_margin_pct=u.fmv_neutral_contribution_margin_pct,
            is_loss_maker_observed=u.is_loss_maker_observed,
            is_loss_maker_at_fmv=u.is_loss_maker_at_fmv,
            contribution_rank=idx,
        ))

    # Aggregates
    total_collections = sum(u.collections_annual_usd for u in units)
    total_comp = sum(u.total_comp_usd for u in units)
    total_overhead = sum(u.allocated_overhead_usd for u in units)
    total_contribution = sum(u.contribution_usd for u in units)
    agg_margin = (
        total_contribution / total_collections
        if total_collections > 0 else 0.0
    )
    n_loss_observed = sum(1 for u in units if u.is_loss_maker_observed)
    n_loss_fmv = sum(1 for u in units if u.is_loss_maker_at_fmv)

    # Top-decile concentration: share of positive contribution from
    # the top 10% of providers (at least one).
    positive_units = [u for u in units if u.contribution_usd > 0]
    total_positive = sum(u.contribution_usd for u in positive_units)
    top_decile_count = max(1, int(len(units) * 0.10))
    top_decile_sum = sum(
        u.contribution_usd for u in units[:top_decile_count]
        if u.contribution_usd > 0
    )
    top_decile_share = (
        top_decile_sum / total_positive
        if total_positive > 0 else 0.0
    )

    optimization = _build_optimization(
        units, total_collections, total_comp,
    )

    return EconomicUnitReport(
        units=units,
        roster_size=n,
        total_collections_usd=total_collections,
        total_comp_usd=total_comp,
        total_overhead_usd=total_overhead,
        total_contribution_usd=total_contribution,
        aggregate_contribution_margin_pct=agg_margin,
        loss_makers_at_current_comp=n_loss_observed,
        loss_makers_at_fmv_comp=n_loss_fmv,
        top_decile_contribution_share=top_decile_share,
        optimization=optimization,
        overhead_pct=overhead_pct,
        overhead_method=overhead_method,
        ownership_type=ownership_type,
    )
