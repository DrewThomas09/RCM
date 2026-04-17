"""
Steps 86, 92: Output format utilities.

Step 86: JSON output format
Step 92: CSV column documentation
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from .logger import logger


# ── Step 86: JSON summary output ───────────────────────────────────────────

def write_summary_json(
    summary_df: pd.DataFrame,
    outdir: str,
    *,
    n_sims: int = 0,
    seed: int = 0,
    config_hashes: Optional[Dict[str, str]] = None,
) -> str:
    """Write summary as JSON with metadata."""
    metrics = {}
    for metric in summary_df.index:
        row = summary_df.loc[metric]
        metrics[str(metric)] = {
            stat: float(row[stat]) if pd.notna(row.get(stat)) else None
            for stat in summary_df.columns
        }

    doc = {
        "schema": "rcm_mc.summary/v1",
        "n_sims": n_sims,
        "seed": seed,
        "config_hashes": config_hashes or {},
        "metrics": metrics,
    }

    path = os.path.join(outdir, "summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, allow_nan=False, default=str)
    logger.info("Wrote: %s", path)
    return path


# ── Step 92: CSV column documentation ──────────────────────────────────────

_COLUMN_DOCS: Dict[str, Dict[str, str]] = {
    "sim": {"description": "Iteration index (0-based)", "unit": "integer"},
    "ebitda_drag": {"description": "Actual minus Benchmark total RCM EBITDA impact", "unit": "USD"},
    "economic_drag": {"description": "Working capital cost difference (A/R days x WACC)", "unit": "USD"},
    "drag_denial_writeoff": {"description": "Excess denial write-offs vs benchmark", "unit": "USD"},
    "drag_underpay_leakage": {"description": "Excess underpayment leakage vs benchmark", "unit": "USD"},
    "drag_denial_rework_cost": {"description": "Excess denial rework costs vs benchmark", "unit": "USD"},
    "drag_underpay_cost": {"description": "Excess underpayment follow-up costs vs benchmark", "unit": "USD"},
    "drag_dar_total": {"description": "Excess weighted A/R days vs benchmark", "unit": "days"},
    "actual_rcm_ebitda_impact": {"description": "Total RCM EBITDA impact for Actual scenario", "unit": "USD"},
    "bench_rcm_ebitda_impact": {"description": "Total RCM EBITDA impact for Benchmark scenario", "unit": "USD"},
}


def write_column_docs(outdir: str, csv_name: str = "simulations") -> str:
    """Write column documentation JSON alongside a CSV output."""
    path = os.path.join(outdir, f"{csv_name}_columns.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_COLUMN_DOCS, f, indent=2)
    logger.info("Wrote: %s", path)
    return path
