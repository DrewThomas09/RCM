"""
Step 79: Run comparison tool.
Step 80: Trend analysis (year-over-year).

Compare two output directories or summary CSVs.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..infra.logger import logger


def compare_summaries(
    summary_a: pd.DataFrame,
    summary_b: pd.DataFrame,
    label_a: str = "Prior",
    label_b: str = "Current",
) -> pd.DataFrame:
    """Compare two summary DataFrames and compute deltas."""
    common_metrics = sorted(set(summary_a.index) & set(summary_b.index))
    rows = []
    for metric in common_metrics:
        row: Dict[str, Any] = {"metric": metric}
        for stat in ("mean", "p10", "p90"):
            if stat in summary_a.columns and stat in summary_b.columns:
                va = float(summary_a.loc[metric, stat])
                vb = float(summary_b.loc[metric, stat])
                row[f"{label_a}_{stat}"] = va
                row[f"{label_b}_{stat}"] = vb
                row[f"delta_{stat}"] = vb - va
                if va != 0:
                    row[f"pct_change_{stat}"] = (vb - va) / abs(va) * 100
                else:
                    row[f"pct_change_{stat}"] = 0.0
        rows.append(row)

    return pd.DataFrame(rows)


def compare_run_dirs(
    dir_a: str,
    dir_b: str,
    label_a: str = "Prior",
    label_b: str = "Current",
) -> pd.DataFrame:
    """Compare two output directories."""
    path_a = os.path.join(dir_a, "summary.csv")
    path_b = os.path.join(dir_b, "summary.csv")

    if not os.path.exists(path_a):
        raise FileNotFoundError(f"summary.csv not found in {dir_a}")
    if not os.path.exists(path_b):
        raise FileNotFoundError(f"summary.csv not found in {dir_b}")

    sa = pd.read_csv(path_a, index_col=0)
    sb = pd.read_csv(path_b, index_col=0)

    return compare_summaries(sa, sb, label_a=label_a, label_b=label_b)


def narrative_comparison(comparison_df: pd.DataFrame) -> str:
    """Generate a plain-English narrative of the comparison."""
    lines = []
    for _, row in comparison_df.iterrows():
        metric = row["metric"]
        if "pct_change_mean" in row:
            pct = row["pct_change_mean"]
            direction = "increased" if pct > 0 else "decreased"
            if abs(pct) > 5:
                lines.append(f"- {metric}: {direction} by {abs(pct):.1f}%")
    if not lines:
        return "No significant changes detected between the two runs."
    return "Key changes:\n" + "\n".join(lines)
