"""Causal inference for initiative impact (Prompt 81).

Three methods — all numpy-only:
1. Interrupted Time Series (ITS): segmented regression.
2. Difference-in-Differences (DiD): treatment vs control.
3. Simple pre-post comparison with confidence interval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


@dataclass
class CausalEstimate:
    method: str
    estimated_effect: float
    ci_low: float = 0.0
    ci_high: float = 0.0
    p_value: float = 1.0
    confidence: str = "low"    # low | medium | high
    n_pre: int = 0
    n_post: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "estimated_effect": float(self.estimated_effect),
            "ci_low": float(self.ci_low),
            "ci_high": float(self.ci_high),
            "p_value": float(self.p_value),
            "confidence": self.confidence,
            "n_pre": self.n_pre, "n_post": self.n_post,
        }


def interrupted_time_series(
    values: Sequence[float], intervention_index: int,
) -> CausalEstimate:
    """Segmented regression with level break at ``intervention_index``.

    Pre-period: values[:intervention_index].
    Post-period: values[intervention_index:].
    Effect = mean(post) - predicted(post from pre-trend).
    """
    xs = np.asarray(values, dtype=float)
    n = len(xs)
    if intervention_index < 2 or intervention_index >= n - 1:
        return CausalEstimate(method="its", estimated_effect=0.0)
    pre = xs[:intervention_index]
    post = xs[intervention_index:]
    # OLS on pre-period.
    t_pre = np.arange(len(pre), dtype=float)
    slope = float(np.polyfit(t_pre, pre, 1)[0]) if len(pre) >= 2 else 0.0
    intercept = float(pre.mean() - slope * t_pre.mean())
    # Predicted post = extrapolate pre-trend.
    t_post = np.arange(intervention_index, n, dtype=float)
    predicted_post = intercept + slope * t_post
    actual_post = post
    effect = float(actual_post.mean() - predicted_post.mean())
    # Rough CI from residual std.
    residuals = pre - (intercept + slope * t_pre)
    sigma = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
    ci_width = 1.96 * sigma / max(1, np.sqrt(len(post)))
    conf = "medium" if len(pre) >= 4 and len(post) >= 2 else "low"
    return CausalEstimate(
        method="its", estimated_effect=effect,
        ci_low=effect - ci_width, ci_high=effect + ci_width,
        confidence=conf, n_pre=len(pre), n_post=len(post),
    )


def difference_in_differences(
    treated_pre: Sequence[float], treated_post: Sequence[float],
    control_pre: Sequence[float], control_post: Sequence[float],
) -> CausalEstimate:
    """Classic DiD: (treated_post - treated_pre) - (control_post - control_pre)."""
    tp = np.asarray(treated_pre, dtype=float)
    tq = np.asarray(treated_post, dtype=float)
    cp = np.asarray(control_pre, dtype=float)
    cq = np.asarray(control_post, dtype=float)
    if len(tp) < 1 or len(tq) < 1 or len(cp) < 1 or len(cq) < 1:
        return CausalEstimate(method="did", estimated_effect=0.0)
    effect = (tq.mean() - tp.mean()) - (cq.mean() - cp.mean())
    # Pooled std for CI.
    all_vals = np.concatenate([tp, tq, cp, cq])
    sigma = float(np.std(all_vals, ddof=1))
    n = len(tp) + len(tq)
    ci_width = 1.96 * sigma / max(1, np.sqrt(n))
    conf = "high" if min(len(tp), len(tq), len(cp), len(cq)) >= 4 else "medium"
    return CausalEstimate(
        method="did", estimated_effect=float(effect),
        ci_low=float(effect - ci_width), ci_high=float(effect + ci_width),
        confidence=conf, n_pre=len(tp), n_post=len(tq),
    )
