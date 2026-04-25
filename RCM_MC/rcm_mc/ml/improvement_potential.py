"""Improvement potential estimator — current metrics + peer benchmarks
→ realistic EBITDA uplift in dollars.

Wraps the existing :class:`rcm_mc.pe.rcm_ebitda_bridge.RCMEBITDABridge`
with a layer that:

  1. Computes the gap between current and a peer-benchmark target
     (default p75) for each of the 7 RCM levers.
  2. Applies a literature-based **realism factor** per lever — not
     every gap can be closed. Denial-rate gaps close at ~60%, DSO
     gaps at ~50% (capped by payer terms), CMI gaps at ~30%
     (clinical documentation has hard limits).
  3. Calls the bridge to convert gap-closure into EBITDA dollars.
  4. Surfaces three scenarios — conservative / realistic /
     optimistic — using configurable realism multipliers.

This is the answer to *'how much EBITDA uplift is achievable?'* —
the lever-by-lever decomposition the partner uses to size the
value-creation plan in an IC memo.

Public API::

    from rcm_mc.ml.improvement_potential import (
        PeerBenchmarks,
        LeverImprovement,
        ImprovementPotentialEstimate,
        estimate_improvement_potential,
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..pe.rcm_ebitda_bridge import (
    FinancialProfile,
    RCMEBITDABridge,
)


# Per-lever realism factors — share of the identified gap that is
# realistically closeable in 18-24 months. Sourced from HFMA case
# studies and partner experience; override via constructor arg if
# the deal has stronger / weaker change capacity.
DEFAULT_REALISM: Dict[str, float] = {
    "denial_rate": 0.60,
    "days_in_ar": 0.50,
    "net_collection_rate": 0.50,
    "clean_claim_rate": 0.70,
    "cost_to_collect": 0.60,
    "first_pass_resolution_rate": 0.65,
    "case_mix_index": 0.30,
}

# Direction map — which side of the gap is "improvement"
LEVER_DIRECTION: Dict[str, str] = {
    "denial_rate": "lower_is_better",
    "days_in_ar": "lower_is_better",
    "net_collection_rate": "higher_is_better",
    "clean_claim_rate": "higher_is_better",
    "cost_to_collect": "lower_is_better",
    "first_pass_resolution_rate": "higher_is_better",
    "case_mix_index": "higher_is_better",
}

# Conservative / Realistic / Optimistic scenario multipliers
# applied to the realism factor. e.g. realistic 0.6 → conservative
# 0.6 * 0.70 = 0.42, optimistic 0.6 * 1.30 = 0.78.
_SCENARIO_MULTIPLIERS = {
    "conservative": 0.70,
    "realistic": 1.00,
    "optimistic": 1.30,
}


@dataclass
class PeerBenchmarks:
    """Peer-percentile target for each RCM lever.

    Default target percentile is 75 — top quartile. For a value-
    creation plan the partner can argue for, p75 is the realistic
    aspiration; p90 belongs in the bull case.

    Each value is in the same units the bridge consumes:
      - rates as percentage points (e.g. denial_rate 7.5 = 7.5%)
      - days_in_ar in days
      - case_mix_index dimensionless
      - cost_to_collect as percentage of NPSR
    """
    denial_rate: Optional[float] = None
    days_in_ar: Optional[float] = None
    net_collection_rate: Optional[float] = None
    clean_claim_rate: Optional[float] = None
    cost_to_collect: Optional[float] = None
    first_pass_resolution_rate: Optional[float] = None
    case_mix_index: Optional[float] = None
    target_percentile: int = 75

    def get(self, metric: str) -> Optional[float]:
        return getattr(self, metric, None)


@dataclass
class LeverImprovement:
    """Per-lever improvement decomposition."""
    lever: str
    current_value: float
    peer_target_value: float
    raw_gap: float                  # current - target, signed by direction
    realism_factor: float
    realistic_target_value: float   # what we model as actually hitting
    revenue_impact: float           # $/yr recurring
    cost_impact: float
    ebitda_impact: float
    working_capital_impact: float   # one-time cash; not in EBITDA


@dataclass
class ImprovementPotentialEstimate:
    """Full estimator output."""
    levers: List[LeverImprovement] = field(default_factory=list)
    realistic_total_ebitda: float = 0.0
    conservative_total_ebitda: float = 0.0
    optimistic_total_ebitda: float = 0.0
    total_working_capital: float = 0.0
    realistic_uplift_pct_of_npr: Optional[float] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "levers": [
                {
                    "lever": lv.lever,
                    "current_value": lv.current_value,
                    "peer_target_value": lv.peer_target_value,
                    "raw_gap": lv.raw_gap,
                    "realism_factor": lv.realism_factor,
                    "realistic_target_value":
                        lv.realistic_target_value,
                    "revenue_impact": lv.revenue_impact,
                    "cost_impact": lv.cost_impact,
                    "ebitda_impact": lv.ebitda_impact,
                    "working_capital_impact":
                        lv.working_capital_impact,
                }
                for lv in self.levers
            ],
            "realistic_total_ebitda":
                self.realistic_total_ebitda,
            "conservative_total_ebitda":
                self.conservative_total_ebitda,
            "optimistic_total_ebitda":
                self.optimistic_total_ebitda,
            "total_working_capital":
                self.total_working_capital,
            "realistic_uplift_pct_of_npr":
                self.realistic_uplift_pct_of_npr,
            "notes": list(self.notes),
        }


def _signed_gap(
    current: float, target: float, direction: str,
) -> float:
    """Signed gap > 0 means there's improvement room."""
    if direction == "lower_is_better":
        return current - target
    return target - current


def _apply_realism(
    current: float,
    target: float,
    realism: float,
    direction: str,
) -> float:
    """Move from current toward target by ``realism`` × the gap."""
    gap = _signed_gap(current, target, direction)
    if gap <= 0:
        # Already at or beyond target — no room
        return current
    closure = realism * gap
    if direction == "lower_is_better":
        return current - closure
    return current + closure


def estimate_improvement_potential(
    profile: FinancialProfile,
    current_metrics: Dict[str, float],
    benchmarks: PeerBenchmarks,
    *,
    realism_factors: Optional[Dict[str, float]] = None,
) -> ImprovementPotentialEstimate:
    """Run the lever-by-lever uplift estimator.

    Args:
      profile: hospital financials (NPR, claims volume, payer mix
        — what the bridge needs to size each lever).
      current_metrics: dict of metric → current value. Same units
        the bridge expects (rates as 0-100 pp).
      benchmarks: peer-percentile targets per metric. Levers with
        no benchmark are skipped (we don't make up a target).
      realism_factors: per-lever override of DEFAULT_REALISM. The
        scaffold's defaults match HFMA / partner-experience bands.

    Returns: ImprovementPotentialEstimate with per-lever breakdown
    and three scenario totals (conservative / realistic /
    optimistic).
    """
    realism = {**DEFAULT_REALISM, **(realism_factors or {})}
    bridge = RCMEBITDABridge(profile)

    levers: List[LeverImprovement] = []
    notes: List[str] = []
    realistic_total = 0.0
    wc_total = 0.0

    for metric, direction in LEVER_DIRECTION.items():
        current = current_metrics.get(metric)
        target = benchmarks.get(metric)
        if current is None or target is None:
            continue
        r = realism.get(metric, 0.5)
        gap = _signed_gap(
            float(current), float(target), direction)
        if gap <= 0:
            notes.append(
                f"{metric}: already at or beyond peer "
                f"p{benchmarks.target_percentile} — no "
                f"improvement modeled.")
            continue

        realistic_target = _apply_realism(
            float(current), float(target), r, direction)

        # Reuse the bridge's per-lever math
        impact = bridge.compute_bridge(
            current_metrics={metric: float(current)},
            target_metrics={metric: realistic_target},
        )
        # per_metric_impacts is a list — find the one for this metric
        per = next(
            (m for m in impact.per_metric_impacts
             if m.metric_key == metric), None)
        if per is None:
            continue

        levers.append(LeverImprovement(
            lever=metric,
            current_value=float(current),
            peer_target_value=float(target),
            raw_gap=gap,
            realism_factor=r,
            realistic_target_value=realistic_target,
            revenue_impact=per.revenue_impact,
            cost_impact=per.cost_impact,
            ebitda_impact=per.ebitda_impact,
            working_capital_impact=getattr(
                per, "working_capital_impact", 0.0) or 0.0,
        ))
        realistic_total += per.ebitda_impact
        wc_total += getattr(
            per, "working_capital_impact", 0.0) or 0.0

    # Conservative / optimistic by scaling the realism factor.
    # Re-run the full estimate at those multipliers.
    conservative_total = 0.0
    optimistic_total = 0.0
    for lv in levers:
        # Per-dollar EBITDA scales linearly in the gap closed,
        # which scales linearly in the realism factor — except
        # for non-linear levers (none in v1 bridge). Linear
        # approximation is fine for headline numbers.
        cons_realism = (lv.realism_factor
                        * _SCENARIO_MULTIPLIERS["conservative"])
        opt_realism = (lv.realism_factor
                       * _SCENARIO_MULTIPLIERS["optimistic"])
        ratio_cons = (cons_realism / lv.realism_factor
                      if lv.realism_factor > 0 else 0)
        ratio_opt = (opt_realism / lv.realism_factor
                     if lv.realism_factor > 0 else 0)
        conservative_total += lv.ebitda_impact * ratio_cons
        optimistic_total += lv.ebitda_impact * ratio_opt

    npr = profile.net_revenue
    pct = (round(realistic_total / npr, 4)
           if npr > 0 else None)

    return ImprovementPotentialEstimate(
        levers=levers,
        realistic_total_ebitda=round(realistic_total, 0),
        conservative_total_ebitda=round(
            conservative_total, 0),
        optimistic_total_ebitda=round(optimistic_total, 0),
        total_working_capital=round(wc_total, 0),
        realistic_uplift_pct_of_npr=pct,
        notes=notes,
    )
