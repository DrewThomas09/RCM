from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Tuple, List

import numpy as np
import pandas as pd

from ..core.simulator import simulate_one
from ..infra.taxonomy import infer_root_cause


def _dict_to_df_mean(acc: Dict[Tuple[str, str], float], n: int, value_col: str) -> pd.DataFrame:
    rows = []
    for (payer, key), v in acc.items():
        rows.append({"payer": payer, "key": key, value_col: float(v) / float(n)})
    return pd.DataFrame(rows)


def simulate_with_mean_breakdowns(cfg: Dict[str, Any], n_sims: int, seed: int) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Run simulation and also return mean breakdown tables for denial drivers."""
    rng = np.random.default_rng(int(seed))

    rows: List[Dict[str, Any]] = []

    # accumulators for means (sum over sims)
    wo_by_payer_type = defaultdict(float)
    cost_by_payer_type = defaultdict(float)
    cases_by_payer_type = defaultdict(float)

    cost_by_payer_stage = defaultdict(float)
    cases_by_payer_stage = defaultdict(float)

    under_leak_by_payer = defaultdict(float)
    under_cost_by_payer = defaultdict(float)

    for i in range(int(n_sims)):
        out = simulate_one(cfg, rng)
        t = out["totals"]
        row = {"sim": i, **t}
        for pr in out["payers"]:
            p = pr["payer"]
            row[f"idr_{p}"] = pr.get("idr", 0.0)
            row[f"fwr_{p}"] = pr.get("fwr_base", 0.0)
            row[f"dar_clean_{p}"] = pr.get("dar_clean", 0.0)
            row[f"upr_{p}"] = pr.get("upr", 0.0)
        rows.append(row)

        for pr in out["payers"]:
            payer = pr["payer"]

            # Denial write-offs by type
            for dt, v in (pr.get("denial_writeoff_by_type", {}) or {}).items():
                wo_by_payer_type[(payer, dt)] += float(v)

            # Denial rework cost by type (Leap 6)
            for dt, v in (pr.get("denial_rework_cost_by_type", {}) or {}).items():
                cost_by_payer_type[(payer, dt)] += float(v)

            # Denial cases by type (Leap 6)
            for dt, c in (pr.get("denial_cases_by_type", {}) or {}).items():
                cases_by_payer_type[(payer, dt)] += float(c)

            # Denial rework cost by stage (Leap 6)
            for st, v in (pr.get("denial_rework_cost_by_stage", {}) or {}).items():
                cost_by_payer_stage[(payer, st)] += float(v)

            # Denial cases by stage (existing)
            for st in ("L1", "L2", "L3"):
                cases_by_payer_stage[(payer, st)] += float(pr.get(f"denial_cases_{st}", 0.0))

            # Underpayments (payer level)
            under_leak_by_payer[(payer, "underpay_leakage")] += float(pr.get("underpay_leakage", 0.0))
            under_cost_by_payer[(payer, "underpay_cost")] += float(pr.get("underpay_cost", 0.0))

    df = pd.DataFrame(rows)

    # Build breakdown tables (means)
    df_wo = _dict_to_df_mean(wo_by_payer_type, int(n_sims), "mean_denial_writeoff")
    df_cost = _dict_to_df_mean(cost_by_payer_type, int(n_sims), "mean_denial_rework_cost")
    df_cases = _dict_to_df_mean(cases_by_payer_type, int(n_sims), "mean_denial_cases")

    df_pt = df_wo.merge(df_cost, on=["payer", "key"], how="outer").merge(df_cases, on=["payer", "key"], how="outer")
    df_pt = df_pt.fillna(0.0)
    df_pt = df_pt.rename(columns={"key": "denial_type"})
    df_pt["root_cause"] = df_pt["denial_type"].apply(infer_root_cause)

    df_stage_cost = _dict_to_df_mean(cost_by_payer_stage, int(n_sims), "mean_denial_rework_cost")
    df_stage_cases = _dict_to_df_mean(cases_by_payer_stage, int(n_sims), "mean_denial_cases")
    df_ps = df_stage_cost.merge(df_stage_cases, on=["payer", "key"], how="outer").fillna(0.0).rename(columns={"key": "stage"})

    df_u_leak = _dict_to_df_mean(under_leak_by_payer, int(n_sims), "mean_value").rename(columns={"key": "metric"})
    df_u_cost = _dict_to_df_mean(under_cost_by_payer, int(n_sims), "mean_value").rename(columns={"key": "metric"})
    df_u = pd.concat([df_u_leak, df_u_cost], axis=0, ignore_index=True)

    breakdowns = {
        "payer_denial_type": df_pt.sort_values(["payer", "mean_denial_writeoff"], ascending=[True, False]).reset_index(drop=True),
        "payer_stage": df_ps.sort_values(["payer", "stage"]).reset_index(drop=True),
        "payer_underpayments": df_u.sort_values(["payer", "metric"]).reset_index(drop=True),
    }
    return df, breakdowns


def compare_mean_breakdowns(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    n_sims: int,
    seed: int,
) -> Dict[str, pd.DataFrame]:
    """Return mean breakdowns for actual/benchmark and their difference (drag)."""
    df_a, bd_a = simulate_with_mean_breakdowns(actual_cfg, n_sims=n_sims, seed=seed)
    df_b, bd_b = simulate_with_mean_breakdowns(benchmark_cfg, n_sims=n_sims, seed=seed + 1)

    out: Dict[str, pd.DataFrame] = {}
    for k in bd_a.keys():
        a = bd_a[k].copy()
        b = bd_b[k].copy()

        # Merge on the relevant keys
        if k == "payer_denial_type":
            keys = ["payer", "denial_type", "root_cause"]
            merged = a.merge(b, on=keys, how="outer", suffixes=("_actual", "_bench")).fillna(0.0)
            for col in ("mean_denial_writeoff", "mean_denial_rework_cost", "mean_denial_cases"):
                merged[f"drag_{col}"] = merged[f"{col}_actual"] - merged[f"{col}_bench"]
            out[k] = merged.sort_values(["payer", "drag_mean_denial_writeoff"], ascending=[True, False]).reset_index(drop=True)

        elif k == "payer_stage":
            keys = ["payer", "stage"]
            merged = a.merge(b, on=keys, how="outer", suffixes=("_actual", "_bench")).fillna(0.0)
            for col in ("mean_denial_rework_cost", "mean_denial_cases"):
                merged[f"drag_{col}"] = merged[f"{col}_actual"] - merged[f"{col}_bench"]
            out[k] = merged.sort_values(["payer", "stage"]).reset_index(drop=True)

        elif k == "payer_underpayments":
            keys = ["payer", "metric"]
            merged = a.merge(b, on=keys, how="outer", suffixes=("_actual", "_bench")).fillna(0.0)
            merged["drag_mean_value"] = merged["mean_value_actual"] - merged["mean_value_bench"]
            out[k] = merged.sort_values(["payer", "metric"]).reset_index(drop=True)

    return out


from ..infra.profile import align_benchmark_to_actual


def _merge_breakdowns_mean(actual: pd.DataFrame, bench: pd.DataFrame, keys: List[str], value_cols: List[str]) -> pd.DataFrame:
    a = actual.copy()
    b = bench.copy()
    merged = a.merge(b, on=keys, how="outer", suffixes=("_actual", "_bench")).fillna(0.0)
    for col in value_cols:
        merged[f"drag_{col}"] = merged[f"{col}_actual"] - merged[f"{col}_bench"]
    return merged


def simulate_compare_with_breakdowns(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    n_sims: int,
    seed: int,
    align_profile: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, pd.DataFrame]]]:
    """Simulate Actual vs Benchmark (distribution) and also provide mean driver breakdowns (no extra sim passes)."""
    if align_profile:
        actual_cfg, benchmark_cfg = align_benchmark_to_actual(actual_cfg, benchmark_cfg, deepcopy_inputs=True)

    df_a, bd_a = simulate_with_mean_breakdowns(actual_cfg, n_sims=n_sims, seed=seed)
    df_b, bd_b = simulate_with_mean_breakdowns(benchmark_cfg, n_sims=n_sims, seed=seed + 1)

    df = pd.DataFrame({"sim": df_a["sim"]})

    out_cols = [
        "denial_writeoff",
        "underpay_leakage",
        "denial_rework_cost",
        "underpay_cost",
        "economic_cost",
        "dar_total",
        "rcm_ebitda_impact",
        "queue_wait_days",
        "queue_wait_days_dollar_weighted",
        "backlog_x",
    ]
    for col in out_cols:
        if col not in df_a.columns or col not in df_b.columns:
            continue
        df[f"actual_{col}"] = df_a[col].values
        df[f"bench_{col}"] = df_b[col].values
        df[f"drag_{col}"] = df[f"actual_{col}"] - df[f"bench_{col}"]

    df["ebitda_drag"] = df["drag_rcm_ebitda_impact"]
    df["economic_drag"] = df["drag_economic_cost"]

    # Add driver columns for sensitivity analysis (Actual only)
    driver_cols = [c for c in df_a.columns if c.startswith(("idr_", "fwr_", "dar_clean_", "upr_"))]
    for c in driver_cols:
        df[f"actual_{c}"] = df_a[c].values
        df[f"bench_{c}"] = df_b[c].values

    # Mean breakdown drag (merge actual/bench mean tables)
    drag_tables: Dict[str, pd.DataFrame] = {}

    # payer_denial_type
    a = bd_a["payer_denial_type"]
    b = bd_b["payer_denial_type"]
    drag_tables["payer_denial_type"] = _merge_breakdowns_mean(
        a, b,
        keys=["payer", "denial_type", "root_cause"],
        value_cols=["mean_denial_writeoff", "mean_denial_rework_cost", "mean_denial_cases"],
    ).sort_values(["payer", "drag_mean_denial_writeoff"], ascending=[True, False]).reset_index(drop=True)

    # payer_stage
    a = bd_a["payer_stage"]
    b = bd_b["payer_stage"]
    drag_tables["payer_stage"] = _merge_breakdowns_mean(
        a, b,
        keys=["payer", "stage"],
        value_cols=["mean_denial_rework_cost", "mean_denial_cases"],
    ).sort_values(["payer", "stage"]).reset_index(drop=True)

    # payer_underpayments
    a = bd_a["payer_underpayments"]
    b = bd_b["payer_underpayments"]
    drag_tables["payer_underpayments"] = _merge_breakdowns_mean(
        a, b,
        keys=["payer", "metric"],
        value_cols=["mean_value"],
    ).sort_values(["payer", "metric"]).reset_index(drop=True)

    return df, {
        "actual": bd_a,
        "benchmark": bd_b,
        "drag": drag_tables,
    }
