"""Fund-level learning engine — cross-deal accuracy and systematic bias.

Aggregates value creation actual-vs-plan across all closed deals to:
1. Compute fund-level bridge realization rate
2. Detect systematic bias by lever ("we overestimate denial improvement by 18%")
3. Adjust future predictions based on fund history
4. Generate an accuracy narrative for LP reporting

This is the compounding moat: every closed deal improves the next underwrite.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class LeverBias:
    lever: str
    planned_total: float
    actual_total: float
    realization_pct: float
    bias_direction: str
    n_deals: int
    adjustment_factor: float


@dataclass
class FundAccuracy:
    n_closed_deals: int
    total_planned: float
    total_realized: float
    fund_realization_pct: float
    lever_biases: List[LeverBias]
    accuracy_trend: List[Dict[str, Any]]
    narrative: str
    adjustment_factors: Dict[str, float]


def compute_fund_accuracy(db_path: str) -> Optional[FundAccuracy]:
    """Aggregate value creation accuracy across all deals with plans + actuals."""
    try:
        con = sqlite3.connect(db_path)
    except Exception:
        return None

    # Get all plans
    try:
        plans = con.execute(
            "SELECT deal_id, hospital_name, plan_json, total_planned_uplift "
            "FROM value_creation_plans"
        ).fetchall()
    except Exception:
        con.close()
        return None

    if not plans:
        con.close()
        return None

    # Get all actuals
    try:
        actuals = con.execute(
            "SELECT deal_id, lever, SUM(actual_impact) as total_actual, "
            "SUM(planned_impact) as total_planned, COUNT(*) as n_quarters "
            "FROM value_creation_actuals "
            "GROUP BY deal_id, lever"
        ).fetchall()
    except Exception:
        actuals = []
        pass

    con.close()

    if not actuals:
        # Plans exist but no actuals yet — return stub
        total_planned = sum(p[3] for p in plans)
        return FundAccuracy(
            n_closed_deals=len(plans),
            total_planned=total_planned,
            total_realized=0,
            fund_realization_pct=0,
            lever_biases=[],
            accuracy_trend=[],
            narrative=f"{len(plans)} deals with value creation plans. No quarterly actuals recorded yet.",
            adjustment_factors={},
        )

    # Aggregate by lever
    lever_data: Dict[str, Dict[str, float]] = {}
    deal_ids_with_actuals = set()
    for deal_id, lever, total_actual, total_planned, n_q in actuals:
        deal_ids_with_actuals.add(deal_id)
        if lever not in lever_data:
            lever_data[lever] = {"planned": 0, "actual": 0, "n_deals": 0}
        lever_data[lever]["planned"] += total_planned or 0
        lever_data[lever]["actual"] += total_actual or 0
        lever_data[lever]["n_deals"] += 1

    total_planned = sum(v["planned"] for v in lever_data.values())
    total_realized = sum(v["actual"] for v in lever_data.values())
    fund_pct = total_realized / total_planned if total_planned != 0 else 0

    biases = []
    adjustment_factors = {}
    for lever, data in sorted(lever_data.items(), key=lambda x: -abs(x[1]["planned"])):
        r_pct = data["actual"] / data["planned"] if data["planned"] != 0 else 0
        if r_pct > 1.0:
            direction = "underestimates"
        elif r_pct < 0.8:
            direction = "overestimates"
        else:
            direction = "accurate"

        adj = min(1.5, max(0.3, r_pct)) if data["planned"] != 0 else 1.0
        adjustment_factors[lever] = round(adj, 3)

        biases.append(LeverBias(
            lever=lever,
            planned_total=round(data["planned"], 0),
            actual_total=round(data["actual"], 0),
            realization_pct=round(r_pct, 3),
            bias_direction=direction,
            n_deals=data["n_deals"],
            adjustment_factor=round(adj, 3),
        ))

    biases.sort(key=lambda b: abs(1 - b.realization_pct), reverse=True)

    # Build narrative
    n_deals = len(deal_ids_with_actuals)
    parts = [f"Across {n_deals} deal(s) with actuals, fund-level bridge realization is {fund_pct:.0%}."]

    overest = [b for b in biases if b.bias_direction == "overestimates"]
    underest = [b for b in biases if b.bias_direction == "underestimates"]
    if overest:
        parts.append(
            f"Model systematically overestimates: {', '.join(b.lever for b in overest[:2])} "
            f"({overest[0].realization_pct:.0%} realized)."
        )
    if underest:
        parts.append(
            f"Model underestimates: {', '.join(b.lever for b in underest[:2])} "
            f"({underest[0].realization_pct:.0%} realized)."
        )
    parts.append("Adjustment factors applied to future predictions automatically.")

    return FundAccuracy(
        n_closed_deals=n_deals,
        total_planned=round(total_planned, 0),
        total_realized=round(total_realized, 0),
        fund_realization_pct=round(fund_pct, 3),
        lever_biases=biases,
        accuracy_trend=[],
        narrative=" ".join(parts),
        adjustment_factors=adjustment_factors,
    )


def get_adjusted_bridge(
    db_path: str,
    bridge: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply fund-level bias corrections to a new bridge.

    If the fund has historical data showing we overestimate denial
    improvement by 18%, discount the denial lever by 18% for new deals.
    """
    accuracy = compute_fund_accuracy(db_path)
    if not accuracy or not accuracy.adjustment_factors:
        return bridge

    adjusted = dict(bridge)
    adjusted_levers = []
    total_adj_impact = 0

    for lev in bridge.get("levers", []):
        adj_lev = dict(lev)
        lever_name = lev.get("name", "")
        factor = accuracy.adjustment_factors.get(lever_name, 1.0)

        if factor != 1.0:
            adj_lev["ebitda_impact"] = round(lev["ebitda_impact"] * factor, 0)
            adj_lev["revenue_impact"] = round(lev["revenue_impact"] * factor, 0)
            adj_lev["cost_impact"] = round(lev["cost_impact"] * factor, 0)
            adj_lev["_adjustment_factor"] = factor
            adj_lev["_original_impact"] = lev["ebitda_impact"]

        total_adj_impact += adj_lev["ebitda_impact"]
        adjusted_levers.append(adj_lev)

    adjusted["levers"] = adjusted_levers
    adjusted["total_ebitda_impact"] = total_adj_impact
    adjusted["_fund_adjusted"] = True
    adjusted["_fund_realization"] = accuracy.fund_realization_pct

    return adjusted
