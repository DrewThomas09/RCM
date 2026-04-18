"""Cohort benchmarking — compare deals within a vintage cohort.

Partners compare deals to peers in the same vintage (e.g., 2023
healthcare-PE deals). A deal that looks great on its own numbers
may still underperform its cohort — or vice versa.

This module:

- Groups a list of deals into vintage cohorts.
- Ranks each deal within its cohort on a blended IRR/MOIC/margin
  score.
- Flags outliers (top-decile or bottom-decile).
- Compares a candidate deal's metrics to cohort p25/p50/p75.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CohortDeal:
    deal_id: str
    vintage_year: int
    name: str = ""
    projected_irr: Optional[float] = None
    projected_moic: Optional[float] = None
    ebitda_margin: Optional[float] = None
    exited: bool = False


@dataclass
class CohortStats:
    vintage_year: int
    n_deals: int
    irr_p25: Optional[float] = None
    irr_p50: Optional[float] = None
    irr_p75: Optional[float] = None
    moic_p25: Optional[float] = None
    moic_p50: Optional[float] = None
    moic_p75: Optional[float] = None
    margin_p25: Optional[float] = None
    margin_p50: Optional[float] = None
    margin_p75: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vintage_year": self.vintage_year,
            "n_deals": self.n_deals,
            "irr_p25": self.irr_p25, "irr_p50": self.irr_p50, "irr_p75": self.irr_p75,
            "moic_p25": self.moic_p25, "moic_p50": self.moic_p50, "moic_p75": self.moic_p75,
            "margin_p25": self.margin_p25, "margin_p50": self.margin_p50, "margin_p75": self.margin_p75,
        }


def _percentiles(values: List[float]) -> Optional[Dict[str, float]]:
    clean = sorted(v for v in values if v is not None)
    n = len(clean)
    if n == 0:
        return None

    def _pick(p: float) -> float:
        idx = int(round((n - 1) * p))
        idx = max(0, min(idx, n - 1))
        return clean[idx]

    return {"p25": _pick(0.25), "p50": _pick(0.50), "p75": _pick(0.75)}


def group_by_vintage(deals: List[CohortDeal]) -> Dict[int, List[CohortDeal]]:
    out: Dict[int, List[CohortDeal]] = {}
    for d in deals:
        out.setdefault(d.vintage_year, []).append(d)
    return out


def cohort_stats(deals: List[CohortDeal], vintage: int) -> CohortStats:
    """Compute p25/p50/p75 for IRR, MOIC, margin within a vintage."""
    subset = [d for d in deals if d.vintage_year == vintage]
    irr_p = _percentiles([d.projected_irr for d in subset])
    moic_p = _percentiles([d.projected_moic for d in subset])
    margin_p = _percentiles([d.ebitda_margin for d in subset])
    return CohortStats(
        vintage_year=vintage,
        n_deals=len(subset),
        irr_p25=irr_p["p25"] if irr_p else None,
        irr_p50=irr_p["p50"] if irr_p else None,
        irr_p75=irr_p["p75"] if irr_p else None,
        moic_p25=moic_p["p25"] if moic_p else None,
        moic_p50=moic_p["p50"] if moic_p else None,
        moic_p75=moic_p["p75"] if moic_p else None,
        margin_p25=margin_p["p25"] if margin_p else None,
        margin_p50=margin_p["p50"] if margin_p else None,
        margin_p75=margin_p["p75"] if margin_p else None,
    )


@dataclass
class CohortRanking:
    deal_id: str
    rank: int                        # 1-indexed
    percentile: int                  # rough percentile
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "rank": self.rank,
            "percentile": self.percentile,
            "score": self.score,
        }


def rank_within_cohort(
    deals: List[CohortDeal],
    vintage: int,
) -> List[CohortRanking]:
    """Rank deals within a vintage by blended score (IRR × 0.5 + MOIC * 0.05 + margin × 0.5)."""
    subset = [d for d in deals if d.vintage_year == vintage]

    def _score(d: CohortDeal) -> float:
        irr = d.projected_irr or 0.0
        moic = d.projected_moic or 0.0
        margin = d.ebitda_margin or 0.0
        return 0.50 * irr + 0.05 * moic + 0.45 * margin

    scored = [(d.deal_id, _score(d)) for d in subset]
    scored.sort(key=lambda kv: -kv[1])
    n = max(len(scored), 1)
    out: List[CohortRanking] = []
    for rank, (sid, score) in enumerate(scored, start=1):
        pct = 100 - int(round(100 * (rank - 1) / n))
        out.append(CohortRanking(
            deal_id=sid, rank=rank, percentile=pct, score=score,
        ))
    return out


def top_decile(deals: List[CohortDeal], vintage: int) -> List[str]:
    rankings = rank_within_cohort(deals, vintage)
    if not rankings:
        return []
    cutoff = max(1, int(round(len(rankings) * 0.10)))
    return [r.deal_id for r in rankings[:cutoff]]


def bottom_decile(deals: List[CohortDeal], vintage: int) -> List[str]:
    rankings = rank_within_cohort(deals, vintage)
    if not rankings:
        return []
    cutoff = max(1, int(round(len(rankings) * 0.10)))
    return [r.deal_id for r in rankings[-cutoff:]]


def compare_to_cohort(
    deal: CohortDeal,
    cohort: List[CohortDeal],
) -> Dict[str, Any]:
    """Return the candidate's position vs. cohort medians on each metric."""
    stats = cohort_stats(cohort, deal.vintage_year)
    out: Dict[str, Any] = {"vintage": deal.vintage_year, "cohort_n": stats.n_deals}
    if deal.projected_irr is not None and stats.irr_p50 is not None:
        out["irr_delta_vs_median"] = deal.projected_irr - stats.irr_p50
    if deal.projected_moic is not None and stats.moic_p50 is not None:
        out["moic_delta_vs_median"] = deal.projected_moic - stats.moic_p50
    if deal.ebitda_margin is not None and stats.margin_p50 is not None:
        out["margin_delta_vs_median"] = deal.ebitda_margin - stats.margin_p50
    return out
