"""
Machine-readable run provenance: manifest + per-metric lineage for summary.csv rows.
Written to provenance.json each CLI run (see cli.py).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd


# Static registry: formula_id -> human formula + code + config levers
METRIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ebitda_drag": {
        "formula": "Per iteration: drag_rcm_ebitda_impact = actual_rcm_ebitda_impact − bench_rcm_ebitda_impact. Summary: mean/p10/p90 over scrubbed simulations.csv column ebitda_drag.",
        "formula_id": "drag_rcm_minus_agg",
        "source_columns": ["ebitda_drag", "actual_rcm_ebitda_impact", "bench_rcm_ebitda_impact"],
        "code": {"module": "rcm_mc.breakdowns", "function": "simulate_compare_with_breakdowns"},
        "config_keys": [
            "payers.*.denials",
            "payers.*.underpayments",
            "payers.*.dar_clean_days",
            "appeals.stages",
            "operations.denial_capacity",
            "economics.wacc_annual",
        ],
        "caveats": [
            "data_scrub.scrub_simulation_data may winsorize ebitda_drag and cap drivers.",
            "Profile alignment copies Actual revenue/mix to Benchmark when enabled.",
        ],
    },
    "economic_drag": {
        "formula": "Per iteration: drag_economic_cost = actual_economic_cost − bench_economic_cost. Summary stats on economic_drag.",
        "formula_id": "drag_economic_agg",
        "source_columns": ["economic_drag", "actual_economic_cost", "bench_economic_cost"],
        "code": {"module": "rcm_mc.simulator", "function": "simulate_one → economic_cost per payer"},
        "config_keys": ["economics.wacc_annual", "payers.*.dar_clean_days", "payers.*.denials", "payers.*.underpayments"],
        "caveats": ["economic_cost ties to simulated A/R dollars × WACC."],
    },
    "drag_denial_writeoff": {
        "formula": "drag_denial_writeoff = actual_denial_writeoff − bench_denial_writeoff per iteration; aggregate.",
        "formula_id": "drag_component_agg",
        "source_columns": ["drag_denial_writeoff"],
        "code": {"module": "rcm_mc.simulator", "function": "_simulate_payer_pass2 denial_writeoff"},
        "config_keys": ["payers.*.denials.idr", "payers.*.denials.fwr", "payers.*.denials.stage_mix", "operations.denial_capacity.backlog"],
        "caveats": [],
    },
    "drag_underpay_leakage": {
        "formula": "drag_underpay_leakage = actual_underpay_leakage − bench_underpay_leakage per iteration; aggregate.",
        "formula_id": "drag_component_agg",
        "source_columns": ["drag_underpay_leakage"],
        "code": {"module": "rcm_mc.simulator", "function": "_simulate_payer_pass2 underpay_leakage"},
        "config_keys": ["payers.*.underpayments.upr", "payers.*.underpayments.severity", "payers.*.underpayments.recovery"],
        "caveats": [],
    },
    "drag_denial_rework_cost": {
        "formula": "drag_denial_rework_cost = actual_denial_rework_cost − bench_denial_rework_cost per iteration; aggregate.",
        "formula_id": "drag_component_agg",
        "source_columns": ["drag_denial_rework_cost"],
        "code": {"module": "rcm_mc.simulator", "function": "_simulate_payer_pass2 appeal costs"},
        "config_keys": ["appeals.stages.L1", "appeals.stages.L2", "appeals.stages.L3", "payers.*.denials"],
        "caveats": [],
    },
    "drag_underpay_cost": {
        "formula": "drag_underpay_cost = actual_underpay_cost − bench_underpay_cost per iteration; aggregate.",
        "formula_id": "drag_component_agg",
        "source_columns": ["drag_underpay_cost"],
        "code": {"module": "rcm_mc.simulator", "function": "_simulate_payer_pass2 underpay_cost"},
        "config_keys": ["payers.*.underpayments"],
        "caveats": [],
    },
    "drag_dar_total": {
        "formula": "drag_dar_total = actual_dar_total − bench_dar_total per iteration; aggregate.",
        "formula_id": "drag_component_agg",
        "source_columns": ["drag_dar_total"],
        "code": {"module": "rcm_mc.simulator", "function": "simulate_one dar_total"},
        "config_keys": ["payers.*.dar_clean_days", "payers.*.denials", "payers.*.underpayments"],
        "caveats": ["DAR is model proxy from simulated A/R and collectible velocity."],
    },
    "actual_rcm_ebitda_impact": {
        "formula": "Per iteration Actual world: rcm_ebitda_impact = denial_writeoff + underpay_leakage + denial_rework_cost + underpay_cost (totals in simulate_one).",
        "formula_id": "actual_rcm_total_agg",
        "source_columns": ["actual_rcm_ebitda_impact"],
        "code": {"module": "rcm_mc.simulator", "function": "simulate_one"},
        "config_keys": ["payers.*", "appeals.stages", "operations.denial_capacity"],
        "caveats": ["Uses Actual config only; Benchmark row is separate column."],
    },
    "bench_rcm_ebitda_impact": {
        "formula": "Same as actual_rcm_ebitda_impact but for Benchmark scenario draw (paired iteration index, seed+1).",
        "formula_id": "bench_rcm_total_agg",
        "source_columns": ["bench_rcm_ebitda_impact"],
        "code": {"module": "rcm_mc.simulator", "function": "simulate_one"},
        "config_keys": ["payers.*", "appeals.stages", "operations.denial_capacity"],
        "caveats": ["After profile alignment, volume/mix may match Actual."],
    },
}


def _file_sha256(path: str) -> Optional[str]:
    if not path or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha_short() -> Optional[str]:
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if root.returncode != 0:
            return None
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=root.stdout.strip(),
            timeout=5,
        )
        if rev.returncode != 0:
            return None
        return rev.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def build_run_manifest(
    *,
    outdir: str,
    n_sims: int,
    seed: int,
    align_profile: bool,
    actual_config_path: Optional[str],
    benchmark_config_path: Optional[str],
    scrub_applied: bool = True,
) -> Dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "outdir": os.path.abspath(outdir),
        "n_sims": int(n_sims),
        "seed": int(seed),
        "align_profile": bool(align_profile),
        "scrub_applied": bool(scrub_applied),
        "git_revision": _git_sha_short(),
        "inputs": {
            "actual_config_path": actual_config_path,
            "benchmark_config_path": benchmark_config_path,
            "actual_config_sha256": _file_sha256(actual_config_path) if actual_config_path else None,
            "benchmark_config_sha256": _file_sha256(benchmark_config_path) if benchmark_config_path else None,
        },
        "documentation": {
            "metric_dictionary": "docs/METRIC_PROVENANCE.md",
            "improvement_guide": "docs/MODEL_IMPROVEMENT.md",
        },
    }


def build_metrics_provenance(summary_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Attach registry entries to each row in summary (index = metric name)."""
    rows: List[Dict[str, Any]] = []
    for metric in summary_df.index:
        m = str(metric)
        reg = METRIC_REGISTRY.get(m, {})
        row = summary_df.loc[m]
        agg = {
            "mean": float(row["mean"]) if pd.notna(row.get("mean")) else None,
            "median": float(row["median"]) if pd.notna(row.get("median")) else None,
            "p10": float(row["p10"]) if pd.notna(row.get("p10")) else None,
            "p90": float(row["p90"]) if pd.notna(row.get("p90")) else None,
            "p95": float(row["p95"]) if pd.notna(row.get("p95")) else None,
        }
        rows.append({
            "metric": m,
            "aggregations": agg,
            "formula_id": reg.get("formula_id", "custom_or_unknown"),
            "formula": reg.get("formula", "See rcm_mc reporting and simulator source."),
            "source_columns": reg.get("source_columns", [m]),
            "code": reg.get("code", {}),
            "config_keys": reg.get("config_keys", []),
            "caveats": reg.get("caveats", []),
        })
    return rows


def build_provenance_document(
    *,
    summary_df: pd.DataFrame,
    outdir: str,
    n_sims: int,
    seed: int,
    align_profile: bool,
    actual_config_path: Optional[str],
    benchmark_config_path: Optional[str],
    scrub_report: Optional[Dict[str, Any]] = None,
    actual_cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    doc = {
        "schema": "rcm_mc.provenance/v1",
        "run": build_run_manifest(
            outdir=outdir,
            n_sims=n_sims,
            seed=seed,
            align_profile=align_profile,
            actual_config_path=actual_config_path,
            benchmark_config_path=benchmark_config_path,
        ),
        "metrics": build_metrics_provenance(summary_df),
    }
    if scrub_report:
        doc["scrub"] = scrub_report
    if actual_cfg is not None:
        from ..data.sources import classify_sources, confidence_grade, path_notes, summarize
        classification = classify_sources(actual_cfg)
        doc["sources"] = {
            "classification": classification,
            "counts": summarize(classification),
            "grade": confidence_grade(classification),
            "notes": path_notes(actual_cfg),
        }
    return doc


def write_provenance_json(
    outdir: str,
    summary_df: pd.DataFrame,
    *,
    n_sims: int,
    seed: int,
    align_profile: bool,
    actual_config_path: Optional[str],
    benchmark_config_path: Optional[str],
    scrub_report: Optional[Dict[str, Any]] = None,
    actual_cfg: Optional[Dict[str, Any]] = None,
) -> str:
    doc = build_provenance_document(
        summary_df=summary_df,
        outdir=outdir,
        n_sims=n_sims,
        seed=seed,
        align_profile=align_profile,
        actual_config_path=actual_config_path,
        benchmark_config_path=benchmark_config_path,
        scrub_report=scrub_report,
        actual_cfg=actual_cfg,
    )
    path = os.path.join(outdir, "provenance.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, allow_nan=False)
    return path
