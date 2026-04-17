"""
Single-iteration audit trace: expand simulate_one Actual vs Benchmark for one Monte Carlo draw.
Pre-scrub (raw engine). Pair with provenance.json and scrubbed simulations.csv for full picture.
"""
from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional

import numpy as np

from .profile import align_benchmark_to_actual
from ..core.simulator import simulate_one


def _json_safe(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _json_safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json_safe(v) for v in x]
    if isinstance(x, (np.floating, float)):
        if not np.isfinite(x):
            return None
        return float(x)
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, bool):
        return x
    if x is None:
        return None
    try:
        if hasattr(x, "item"):
            return _json_safe(x.item())
    except Exception:
        pass
    return str(x)


def export_iteration_trace(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    *,
    iteration: int,
    seed: int,
    align_profile: bool = True,
) -> Dict[str, Any]:
    """
    Reproduce draw `iteration` the same way as the main compare loop:
    Actual uses RNG(seed), Benchmark uses RNG(seed+1). For iteration > 0, burn in by
    calling simulate_one that many times on each side first.
    """
    if iteration < 0:
        raise ValueError("iteration must be >= 0")

    a = copy.deepcopy(actual_cfg)
    b = copy.deepcopy(benchmark_cfg)
    if align_profile:
        a, b = align_benchmark_to_actual(a, b, deepcopy_inputs=True)

    rng_a = np.random.default_rng(int(seed))
    rng_b = np.random.default_rng(int(seed) + 1)

    for _ in range(iteration):
        simulate_one(a, rng_a)
        simulate_one(b, rng_b)

    out_a = simulate_one(a, rng_a)
    out_b = simulate_one(b, rng_b)

    def pack(side: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        totals = raw.get("totals") or {}
        payers: List[Dict[str, Any]] = []
        for pr in raw.get("payers") or []:
            payers.append(
                {
                    "payer": pr.get("payer"),
                    "revenue": pr.get("revenue"),
                    "net_collectible": pr.get("net_collectible"),
                    "idr": pr.get("idr"),
                    "fwr_base": pr.get("fwr_base"),
                    "dar_clean": pr.get("dar_clean"),
                    "upr": pr.get("upr"),
                    "denial_writeoff": pr.get("denial_writeoff"),
                    "denial_rework_cost": pr.get("denial_rework_cost"),
                    "underpay_leakage": pr.get("underpay_leakage"),
                    "underpay_cost": pr.get("underpay_cost"),
                    "economic_cost": pr.get("economic_cost"),
                    "dar_total": pr.get("dar_total"),
                    "denial_cases": pr.get("denial_cases"),
                    "underpay_cases": pr.get("underpay_cases"),
                    "backlog_x": pr.get("backlog_x"),
                    "queue_wait_days": pr.get("queue_wait_days"),
                }
            )
        return {
            "side": side,
            "totals": {
                "denial_writeoff": totals.get("denial_writeoff"),
                "denial_rework_cost": totals.get("denial_rework_cost"),
                "underpay_leakage": totals.get("underpay_leakage"),
                "underpay_cost": totals.get("underpay_cost"),
                "economic_cost": totals.get("economic_cost"),
                "dar_total": totals.get("dar_total"),
                "rcm_ebitda_impact": totals.get("rcm_ebitda_impact"),
                "backlog_x": totals.get("backlog_x"),
                "queue_wait_days": totals.get("queue_wait_days"),
                "capacity_touches": totals.get("capacity_touches"),
                "total_denial_touches": totals.get("total_denial_touches"),
            },
            "payers": payers,
        }

    pa = pack("actual", out_a)
    pb = pack("benchmark", out_b)

    drag = {}
    for k in (
        "denial_writeoff",
        "denial_rework_cost",
        "underpay_leakage",
        "underpay_cost",
        "economic_cost",
        "dar_total",
        "rcm_ebitda_impact",
    ):
        va = pa["totals"].get(k)
        vb = pb["totals"].get(k)
        if va is not None and vb is not None:
            drag[k] = float(va) - float(vb)

    return {
        "schema": "rcm_mc.trace/v1",
        "iteration": int(iteration),
        "seed_actual": int(seed),
        "seed_benchmark": int(seed) + 1,
        "align_profile": bool(align_profile),
        "note": "Pre-scrub engine draw. simulations.csv rows may differ after data_scrub.scrub_simulation_data.",
        "actual": pa,
        "benchmark": pb,
        "drag_totals": drag,
        "ebitda_drag": drag.get("rcm_ebitda_impact"),
        "economic_drag": drag.get("economic_cost"),
    }


def write_trace_json(
    path: str,
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    *,
    iteration: int,
    seed: int,
    align_profile: bool = True,
) -> str:
    doc = export_iteration_trace(
        actual_cfg,
        benchmark_cfg,
        iteration=iteration,
        seed=seed,
        align_profile=align_profile,
    )
    safe = _json_safe(doc)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(safe, f, indent=2, allow_nan=False)
    return path
