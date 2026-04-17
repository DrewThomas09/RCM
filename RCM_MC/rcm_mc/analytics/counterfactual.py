"""Counterfactual modeling (Prompt 83).

"What would EBITDA be today if we hadn't done the CDI initiative?"
Uses causal estimates from Prompt 81 + ramp curves from Prompt 17.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


@dataclass
class CounterfactualResult:
    actual_trajectory: List[float] = field(default_factory=list)
    counterfactual_trajectory: List[float] = field(default_factory=list)
    delta_per_period: List[float] = field(default_factory=list)
    cumulative_delta: float = 0.0
    methodology: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actual_trajectory": [float(v) for v in self.actual_trajectory],
            "counterfactual_trajectory": [float(v) for v in self.counterfactual_trajectory],
            "delta_per_period": [float(v) for v in self.delta_per_period],
            "cumulative_delta": float(self.cumulative_delta),
            "methodology": self.methodology,
        }


def counterfactual_without_initiative(
    actual_values: Sequence[float],
    causal_effect: float,
    intervention_index: int,
) -> CounterfactualResult:
    """Remove the initiative's estimated causal impact.

    ``causal_effect`` is the per-period effect estimated by
    :func:`causal_inference.interrupted_time_series`.
    """
    actual = list(float(v) for v in actual_values)
    n = len(actual)
    cf = list(actual)
    for i in range(intervention_index, n):
        cf[i] = actual[i] - causal_effect
    deltas = [actual[i] - cf[i] for i in range(n)]
    return CounterfactualResult(
        actual_trajectory=actual,
        counterfactual_trajectory=cf,
        delta_per_period=deltas,
        cumulative_delta=sum(deltas),
        methodology="causal_subtraction",
    )


def counterfactual_baseline(
    actual_values: Sequence[float],
    industry_drift_per_period: float = 0.0,
) -> CounterfactualResult:
    """What would the metric be with NO initiatives — just organic
    industry drift?"""
    actual = list(float(v) for v in actual_values)
    n = len(actual)
    if not actual:
        return CounterfactualResult()
    baseline = [actual[0] + industry_drift_per_period * i for i in range(n)]
    deltas = [actual[i] - baseline[i] for i in range(n)]
    return CounterfactualResult(
        actual_trajectory=actual,
        counterfactual_trajectory=baseline,
        delta_per_period=deltas,
        cumulative_delta=sum(deltas),
        methodology="baseline_drift",
    )
