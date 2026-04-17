"""
Initiative optimizer: rank initiatives by EBITDA uplift, EV uplift, payback, confidence.
Does not change Monte Carlo math; runs N+1 simulations (baseline + each initiative).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .initiatives import get_all_initiatives, initiative_to_scenario
from ..scenarios.scenario_overlay import apply_scenario
from ..core.kernel import run_simulation


def rank_initiatives(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    initiatives: Optional[List[Dict[str, Any]]] = None,
    n_sims: int = 1000,
    seed: int = 42,
    ev_multiple: float = 8.0,
    align_profile: bool = True,
) -> pd.DataFrame:
    """
    Rank initiatives by expected EBITDA uplift, EV uplift, payback, and confidence.

    Runs baseline (actual vs benchmark) plus one simulation per initiative (initiative config vs benchmark).
    Returns a DataFrame sorted by ev_uplift_mean descending.
    """
    initiatives = initiatives or get_all_initiatives()
    if not initiatives:
        return pd.DataFrame()

    # Baseline
    baseline = run_simulation(
        actual_cfg,
        benchmark_cfg,
        n_sims=n_sims,
        seed=seed,
        align_profile=align_profile,
    )
    base_mean = baseline.ebitda_drag_mean

    rows = []
    for i, inv in enumerate(initiatives):
        scenario = initiative_to_scenario(inv)
        shocked_cfg = apply_scenario(actual_cfg, scenario)
        result = run_simulation(
            shocked_cfg,
            benchmark_cfg,
            n_sims=n_sims,
            seed=seed + 1000 + i,
            align_profile=align_profile,
        )
        inv_mean = result.ebitda_drag_mean

        ebitda_uplift = base_mean - inv_mean
        one_time = float(inv.get("one_time_cost", 0))
        annual_run = float(inv.get("annual_run_rate", 0))
        net_uplift = ebitda_uplift - annual_run
        ev_uplift = net_uplift * ev_multiple

        monthly_net = net_uplift / 12.0 if net_uplift > 0 else 0.0
        payback_months = (one_time / monthly_net) if monthly_net > 0 else np.inf

        rows.append({
            "initiative_id": inv.get("id", ""),
            "name": inv.get("name", ""),
            "owner": inv.get("owner", ""),
            "confidence": inv.get("confidence", "C"),
            "ebitda_uplift_mean": ebitda_uplift,
            "net_ebitda_uplift_mean": net_uplift,
            "ev_uplift_mean": ev_uplift,
            "payback_months": payback_months,
            "one_time_cost": one_time,
            "annual_run_rate": annual_run,
            "ramp_months": float(inv.get("ramp_months", 12)),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("ev_uplift_mean", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df


def _ramp_to_phase(ramp_months: float) -> str:
    """Map ramp_months to 100-day plan phase (30/60/90/180 day buckets)."""
    m = float(ramp_months)
    if m <= 3:
        return "Days 1–30"
    if m <= 6:
        return "Days 31–60"
    if m <= 9:
        return "Days 61–90"
    return "Days 91–180"


def build_100_day_plan(
    rank_df: pd.DataFrame,
    initiatives: Optional[List[Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """
    Build a 100-day plan table from ranked initiatives.
    Adds KPI, phase (30/60/90/180 days), and operating cadence.
    """
    if rank_df.empty:
        return pd.DataFrame()

    initiatives = initiatives or get_all_initiatives()
    id_to_inv = {i.get("id"): i for i in initiatives if i.get("id")}

    plan = rank_df.copy()
    plan["phase"] = plan["ramp_months"].apply(_ramp_to_phase)
    plan["kpi"] = plan["initiative_id"].apply(
        lambda x: id_to_inv.get(x, {}).get("kpi", "")
    )
    plan["cadence"] = "Monthly"  # default operating cadence
    plan["payback_months"] = plan["payback_months"].replace(np.inf, np.nan)

    cols = [
        "rank",
        "name",
        "owner",
        "kpi",
        "phase",
        "ebitda_uplift_mean",
        "ev_uplift_mean",
        "payback_months",
        "confidence",
        "cadence",
    ]
    return plan[[c for c in cols if c in plan.columns]]
