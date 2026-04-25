"""Standard 2×2 Difference-in-Differences.

The textbook starting point:

    DiD = (Y_t_post − Y_t_pre) − (Y_c_post − Y_c_pre)

where Y_t and Y_c are means over the treated and control units
respectively. No weighting beyond the unit-level mean — every
control unit counts equally.

Closed-form. Used as a baseline against which the more
sophisticated synthetic-control / SDID estimators are
benchmarked.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class DiDResult:
    treatment_effect: float
    treated_pre_mean: float
    treated_post_mean: float
    control_pre_mean: float
    control_post_mean: float
    n_units: int = 0
    n_periods: int = 0
    pre_periods: int = 0
    post_periods: int = 0
    standard_error: float = 0.0


def did_estimate(
    Y: np.ndarray,
    *,
    treated_unit: int,
    treated_period: int,
) -> DiDResult:
    """Standard 2×2 DiD on a panel.

    Args:
      Y: (N, T) outcome panel.
      treated_unit: row index of the treated unit.
      treated_period: column index where treatment starts.

    Returns DiDResult. Standard error computed via the
    within-unit residual variance using the standard textbook
    pooled-variance formula.
    """
    Y = np.asarray(Y, dtype=float)
    if Y.ndim != 2:
        raise ValueError("Y must be 2-D")
    n_units, n_periods = Y.shape
    if not (0 <= treated_unit < n_units):
        raise ValueError("treated_unit out of range")
    if not (0 < treated_period < n_periods):
        raise ValueError("treated_period out of range")

    pre = list(range(treated_period))
    post = list(range(treated_period, n_periods))
    control_idx = [i for i in range(n_units) if i != treated_unit]

    treated_pre = float(Y[treated_unit, pre].mean())
    treated_post = float(Y[treated_unit, post].mean())
    control_pre = float(Y[control_idx][:, pre].mean())
    control_post = float(Y[control_idx][:, post].mean())

    effect = (treated_post - treated_pre) - (
        control_post - control_pre)

    # Standard error: pooled within-unit variance, scaled by
    # 1/n + 1/m factor (textbook DiD inference under
    # homoskedasticity). Conservative under panel auto-
    # correlation but partner-defensible at this granularity.
    treated_resid = (
        Y[treated_unit, post] - treated_post)
    control_resid = (
        Y[control_idx][:, post] - control_post)
    var_t = float(np.var(treated_resid, ddof=1)
                  if len(treated_resid) > 1 else 0.0)
    var_c = float(np.var(control_resid, ddof=1)
                  if control_resid.size > 1 else 0.0)
    n_t_post = len(post)
    n_c_post = len(control_idx) * len(post)
    if n_t_post > 0 and n_c_post > 0:
        se = float(np.sqrt(
            var_t / n_t_post + var_c / n_c_post))
    else:
        se = 0.0

    return DiDResult(
        treatment_effect=float(effect),
        treated_pre_mean=treated_pre,
        treated_post_mean=treated_post,
        control_pre_mean=control_pre,
        control_post_mean=control_post,
        n_units=n_units, n_periods=n_periods,
        pre_periods=len(pre), post_periods=len(post),
        standard_error=round(se, 4),
    )
