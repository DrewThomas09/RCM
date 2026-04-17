"""Data Envelopment Analysis (DEA) for hospital operational efficiency.

Computes the efficient frontier across hospitals using multiple inputs
(staff, costs, beds) and outputs (revenue, patient days, quality).
Identifies which hospitals are operationally efficient and which have
the most room for improvement.

References: Cooper, Seiford, Zhu — Data Envelopment Analysis
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class EfficiencyScore:
    ccn: str
    hospital_name: str
    state: str
    efficiency_score: float  # 0-1, 1=frontier
    efficiency_rank: int
    efficiency_percentile: float
    is_frontier: bool
    input_levels: Dict[str, float]
    output_levels: Dict[str, float]
    slack_inputs: Dict[str, float]
    improvement_potential: Dict[str, float]
    reference_set: List[str]  # CCNs of efficient peers


def _simple_dea_output_oriented(
    inputs: np.ndarray,
    outputs: np.ndarray,
) -> np.ndarray:
    """Simplified output-oriented DEA using ratio analysis.

    For each hospital, compute the maximum output achievable given its
    inputs, relative to the best-practice frontier. Returns efficiency
    scores in [0, 1] where 1 = on the frontier.

    This is a simplified version that doesn't require linear programming —
    uses output-to-input ratios and frontier envelope estimation.
    """
    n = len(inputs)
    if n == 0:
        return np.array([])

    # Normalize inputs and outputs
    inp_min = inputs.min(axis=0)
    inp_range = inputs.max(axis=0) - inp_min
    inp_range[inp_range == 0] = 1
    inp_norm = (inputs - inp_min) / inp_range

    out_min = outputs.min(axis=0)
    out_range = outputs.max(axis=0) - out_min
    out_range[out_range == 0] = 1
    out_norm = (outputs - out_min) / out_range

    # Composite efficiency: weighted output / weighted input
    # Use equal weights for simplicity
    n_inp = inputs.shape[1]
    n_out = outputs.shape[1]

    composite_input = inp_norm.mean(axis=1)
    composite_output = out_norm.mean(axis=1)

    # Efficiency ratio
    efficiency = np.zeros(n)
    for i in range(n):
        if composite_input[i] <= 0:
            efficiency[i] = 0
            continue

        # Find the best output among hospitals with similar or fewer inputs
        similar = composite_input <= composite_input[i] * 1.1
        if similar.sum() == 0:
            efficiency[i] = 1
            continue

        best_output = composite_output[similar].max()
        if best_output <= 0:
            efficiency[i] = 1
        else:
            efficiency[i] = min(1, composite_output[i] / best_output)

    return efficiency


def compute_efficiency_frontier(
    hcris_df: pd.DataFrame,
    input_cols: Optional[List[str]] = None,
    output_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, List[EfficiencyScore]]:
    """Compute DEA efficiency scores for all hospitals."""
    df = hcris_df.copy()

    if input_cols is None:
        input_cols = ["beds", "operating_expenses"]
    if output_cols is None:
        output_cols = ["net_patient_revenue", "total_patient_days"]

    available_in = [c for c in input_cols if c in df.columns]
    available_out = [c for c in output_cols if c in df.columns]

    if not available_in or not available_out:
        return df, []

    clean = df.dropna(subset=available_in + available_out).copy()
    clean = clean[(clean[available_in] > 0).all(axis=1) & (clean[available_out] > 0).all(axis=1)]

    if len(clean) < 10:
        return df, []

    inputs = clean[available_in].values.astype(float)
    outputs = clean[available_out].values.astype(float)

    scores = _simple_dea_output_oriented(inputs, outputs)

    clean["efficiency_score"] = scores
    clean["efficiency_rank"] = clean["efficiency_score"].rank(ascending=False, method="min").astype(int)

    # Build EfficiencyScore objects for top and bottom
    results = []
    sorted_df = clean.sort_values("efficiency_score", ascending=False)

    frontier_ccns = list(sorted_df[sorted_df["efficiency_score"] >= 0.95]["ccn"].values[:10])

    for _, row in sorted_df.head(100).iterrows():
        score = float(row["efficiency_score"])
        rank = int(row["efficiency_rank"])
        pctile = float((clean["efficiency_score"] < score).mean() * 100)

        inp_levels = {c: float(row[c]) for c in available_in}
        out_levels = {c: float(row[c]) for c in available_out}

        # Improvement potential: how much more output at same input
        improvement = {}
        for c in available_out:
            frontier_val = clean.loc[clean["efficiency_score"] >= 0.95, c].median()
            current = float(row[c])
            if current > 0 and frontier_val > current:
                improvement[c] = round((frontier_val - current) / current, 3)

        # Input slack: how much less input at same output
        slack = {}
        for c in available_in:
            frontier_input = clean.loc[clean["efficiency_score"] >= 0.95, c].median()
            current = float(row[c])
            if current > frontier_input and current > 0:
                slack[c] = round((current - frontier_input) / current, 3)

        results.append(EfficiencyScore(
            ccn=str(row.get("ccn", "")),
            hospital_name=str(row.get("name", ""))[:40],
            state=str(row.get("state", "")),
            efficiency_score=round(score, 4),
            efficiency_rank=rank,
            efficiency_percentile=round(pctile, 1),
            is_frontier=score >= 0.95,
            input_levels=inp_levels,
            output_levels=out_levels,
            slack_inputs=slack,
            improvement_potential=improvement,
            reference_set=frontier_ccns[:5] if score < 0.95 else [],
        ))

    df["efficiency_score"] = np.nan
    df.loc[clean.index, "efficiency_score"] = clean["efficiency_score"]
    df.loc[clean.index, "efficiency_rank"] = clean["efficiency_rank"]

    return df, results
