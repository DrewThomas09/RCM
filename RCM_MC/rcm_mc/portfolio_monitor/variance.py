"""Variance + early-warning classification.

Per-asset:
  ebitda_variance_pct = (actual - plan) / plan
  revenue_variance_pct = (actual - plan) / plan
  comp_relative = (current_moic / comp_moic_p50) − 1
                  (positive = outperforming peers)

Status bands:
  early_warning   ebitda_variance_pct < -0.10 (10%+ below plan)
  watch           -0.10 ≤ variance < -0.05
  on_track        −0.05 ≤ variance ≤ +0.05
  outperforming   variance > +0.05

Portfolio-wide:
  total_plan_ebitda + total_actual_ebitda
  per-status counts
  projected-vs-actual EBITDA bridge: aggregate plan → aggregate
  actual decomposed into on-track + outperformers + early-
  warnings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from .snapshot import PortfolioAsset, PortfolioSnapshot


@dataclass
class AssetVariance:
    deal_id: str
    name: str
    sector: str
    plan_ebitda_mm: float
    actual_ebitda_mm: float
    ebitda_variance_pct: float
    ebitda_variance_mm: float
    revenue_variance_pct: float
    comp_relative: float       # (current_moic / p50) - 1
    status: str                # early_warning / watch /
                               # on_track / outperforming
    notes: str = ""


@dataclass
class PortfolioVariance:
    fund_name: str
    n_assets: int
    total_plan_ebitda_mm: float
    total_actual_ebitda_mm: float
    total_variance_mm: float
    total_variance_pct: float
    by_status: dict = field(default_factory=dict)   # status → count
    bridge_breakdown: dict = field(default_factory=dict)
    asset_variances: List[AssetVariance] = field(
        default_factory=list)


def _band(variance_pct: float) -> str:
    if variance_pct < -0.10:
        return "early_warning"
    if variance_pct < -0.05:
        return "watch"
    if variance_pct <= 0.05:
        return "on_track"
    return "outperforming"


def _safe_pct(actual: float, plan: float) -> float:
    if plan <= 0:
        return 0.0
    return (actual - plan) / plan


def compute_variance(
    snapshot: PortfolioSnapshot,
) -> PortfolioVariance:
    """Compute variance + status per asset, plus the portfolio-
    wide projected-vs-actual bridge."""
    total_plan = 0.0
    total_actual = 0.0
    by_status: dict = {
        "early_warning": 0, "watch": 0,
        "on_track": 0, "outperforming": 0,
    }
    bridge: dict = {
        "outperforming_contribution_mm": 0.0,
        "on_track_contribution_mm": 0.0,
        "watch_contribution_mm": 0.0,
        "early_warning_contribution_mm": 0.0,
    }
    asset_variances: List[AssetVariance] = []

    for a in snapshot.assets:
        ebitda_pct = _safe_pct(
            a.actual_ebitda_mm, a.plan_ebitda_mm)
        ebitda_mm = a.actual_ebitda_mm - a.plan_ebitda_mm
        revenue_pct = _safe_pct(
            a.actual_revenue_mm, a.plan_revenue_mm)
        if (a.current_moic is not None
                and a.comparable_moic_p50
                and a.comparable_moic_p50 > 0):
            comp_rel = (a.current_moic / a.comparable_moic_p50
                        - 1.0)
        else:
            comp_rel = 0.0
        status = _band(ebitda_pct)
        total_plan += a.plan_ebitda_mm
        total_actual += a.actual_ebitda_mm
        by_status[status] += 1
        bridge[f"{status}_contribution_mm"] += ebitda_mm

        notes = ""
        if status == "early_warning":
            if ebitda_pct < -0.20:
                notes = (
                    "Severe miss — recommend operating-partner "
                    "intervention this quarter.")
            else:
                notes = (
                    "Material miss — schedule plan-revision "
                    "review with management.")
        elif status == "outperforming" and comp_rel > 0.20:
            notes = (
                "Outperforming both plan AND peer group — strong "
                "candidate for IC discussion of accelerated "
                "exit.")

        asset_variances.append(AssetVariance(
            deal_id=a.deal_id,
            name=a.name,
            sector=a.sector,
            plan_ebitda_mm=round(a.plan_ebitda_mm, 2),
            actual_ebitda_mm=round(a.actual_ebitda_mm, 2),
            ebitda_variance_pct=round(ebitda_pct, 4),
            ebitda_variance_mm=round(ebitda_mm, 2),
            revenue_variance_pct=round(revenue_pct, 4),
            comp_relative=round(comp_rel, 4),
            status=status,
            notes=notes,
        ))

    asset_variances.sort(
        key=lambda av: av.ebitda_variance_pct)

    total_variance_mm = total_actual - total_plan
    total_variance_pct = (
        total_variance_mm / total_plan if total_plan > 0 else 0.0)

    # Round bridge entries for readability
    bridge = {
        k: round(v, 2) for k, v in bridge.items()
    }

    return PortfolioVariance(
        fund_name=snapshot.fund_name,
        n_assets=len(snapshot.assets),
        total_plan_ebitda_mm=round(total_plan, 2),
        total_actual_ebitda_mm=round(total_actual, 2),
        total_variance_mm=round(total_variance_mm, 2),
        total_variance_pct=round(total_variance_pct, 4),
        by_status=by_status,
        bridge_breakdown=bridge,
        asset_variances=asset_variances,
    )
