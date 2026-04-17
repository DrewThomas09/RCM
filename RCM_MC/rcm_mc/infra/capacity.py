"""
Step 48: Standalone capacity/backlog modeling module.

Isolates capacity logic from the main simulator, enabling
alternative capacity models (unlimited, outsourced, etc.).
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from .logger import logger


def compute_queue_metrics(
    *,
    demand_touches_annual: float,
    capacity_touches_annual: float,
    months: int = 12,
    days_per_month: float = 30.0,
) -> Dict[str, float]:
    """Simulate monthly queue buildup and return wait time metrics."""
    months = int(max(months, 1))
    days_per_month = float(max(days_per_month, 1.0))

    if capacity_touches_annual <= 0:
        return {"queue_wait_days_avg": 0.0, "backlog_months_avg": 0.0, "backlog_months_max": 0.0}

    cap_m = capacity_touches_annual / months
    arr_m = demand_touches_annual / months

    backlog = 0.0
    backlog_months: List[float] = []
    for _ in range(months):
        backlog += arr_m
        processed = min(cap_m, backlog)
        backlog -= processed
        backlog_months.append(backlog / cap_m if cap_m > 0 else 0.0)

    backlog_months_avg = float(np.mean(backlog_months)) if backlog_months else 0.0
    backlog_months_max = float(np.max(backlog_months)) if backlog_months else 0.0
    queue_wait_days_avg = backlog_months_avg * days_per_month

    return {
        "queue_wait_days_avg": float(queue_wait_days_avg),
        "backlog_months_avg": backlog_months_avg,
        "backlog_months_max": backlog_months_max,
    }


def compute_backlog_x(
    total_denial_touches: float,
    capacity_touches: float,
    max_x: float = 3.0,
) -> float:
    """Compute normalized over-capacity ratio."""
    if capacity_touches <= 0 or not np.isfinite(capacity_touches):
        return 0.0
    ratio = total_denial_touches / capacity_touches
    return float(min(max(0.0, ratio - 1.0), max_x))


def compute_capacity(
    cfg: Dict[str, Any],
    total_denial_touches: float,
    total_denial_cases: int,
) -> Dict[str, Any]:
    """Unified capacity computation supporting all modes (Step 42)."""
    cap = cfg["operations"]["denial_capacity"]
    mode = str(cap.get("mode", "annual_backlog")).strip().lower()
    cap_enabled = bool(cap.get("enabled", True))
    working_days = int(cfg["analysis"].get("working_days", 250))
    fte = float(cap.get("fte", 12))
    per_fte_per_day = float(cap.get("denials_per_fte_per_day", 12))

    result = {
        "mode": mode,
        "capacity_touches": 0.0,
        "backlog_x": 0.0,
        "queue_wait_days": 0.0,
        "backlog_months_avg": 0.0,
        "backlog_months_max": 0.0,
        "outsourced_cost": 0.0,
    }

    if not cap_enabled or mode == "unlimited":
        result["capacity_touches"] = float("inf")
        return result

    if mode == "outsourced":
        cost_per_case = float(cap.get("cost_per_case", 35.0))
        result["outsourced_cost"] = cost_per_case * total_denial_cases
        result["capacity_touches"] = float("inf")
        return result

    capacity_touches = fte * per_fte_per_day * working_days
    result["capacity_touches"] = float(capacity_touches)

    if capacity_touches <= 0:
        return result

    max_x = float(cap.get("backlog", {}).get("max_over_capacity_x", 3.0))
    result["backlog_x"] = compute_backlog_x(total_denial_touches, capacity_touches, max_x)

    if mode == "queue":
        q = cap.get("queue", {}) or {}
        if bool(q.get("enabled", True)):
            months = int(q.get("months", 12))
            dpm = float(q.get("days_per_month", 30.0))
            qm = compute_queue_metrics(
                demand_touches_annual=total_denial_touches,
                capacity_touches_annual=capacity_touches,
                months=months,
                days_per_month=dpm,
            )
            result["queue_wait_days"] = qm["queue_wait_days_avg"]
            result["backlog_months_avg"] = qm["backlog_months_avg"]
            result["backlog_months_max"] = qm["backlog_months_max"]

    return result


def assign_bucket_wait_days(
    buckets: List[Dict[str, Any]],
    *,
    queue_wait_days_base: float,
    priority: str,
    min_factor: float = 0.55,
    max_factor: float = 1.55,
) -> None:
    """Assign bucket-specific wait days based on priority strategy."""
    if not buckets:
        return

    queue_wait_days_base = float(max(queue_wait_days_base, 0.0))
    if queue_wait_days_base <= 0 or priority == "fifo" or len(buckets) == 1:
        for b in buckets:
            b["queue_wait_days"] = queue_wait_days_base
        return

    order = sorted(range(len(buckets)), key=lambda i: float(buckets[i].get("mean_amount", 0.0)), reverse=True)
    n = len(order)
    if n <= 1:
        for b in buckets:
            b["queue_wait_days"] = queue_wait_days_base
        return

    raw_factors = np.zeros(n, dtype=float)
    for rank, idx in enumerate(order):
        raw_factors[rank] = min_factor + (rank / (n - 1)) * (max_factor - min_factor)

    w = np.array(
        [float(buckets[i].get("denial_cases", 0.0)) if float(buckets[i].get("denial_cases", 0.0)) > 0 else float(buckets[i].get("claim_count_est", 0.0)) for i in order],
        dtype=float,
    )
    if w.sum() <= 0:
        w = np.ones(n, dtype=float)

    avg = float(np.sum(w * raw_factors) / np.sum(w))
    scale = 1.0 / avg if avg > 0 else 1.0
    factors = np.clip(raw_factors * scale, 0.25, 2.25)

    for rank, idx in enumerate(order):
        buckets[idx]["queue_wait_days"] = queue_wait_days_base * float(factors[rank])
