"""Synthetic Controls (Abadie-Gardeazabal 2003).

Solves for non-negative simplex weights ω (Σω = 1, ω ≥ 0) that
make the weighted control units' pre-treatment outcomes match
the treated unit's. The treatment effect is the post-treatment
gap between the treated unit and the synthetic control.

Optimization: projected gradient descent on the simplex. The
projection step (Wang & Carreira-Perpiñán 2013) keeps ω in
the simplex efficiently in O(N log N) per iteration.

Pure numpy. No scipy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class SyntheticControlResult:
    treatment_effect: float
    unit_weights: np.ndarray = field(
        default_factory=lambda: np.zeros(0))
    treated_unit: int = 0
    n_units: int = 0
    n_periods: int = 0
    pre_match_rmse: float = 0.0
    placebo_rmsi_ratio: float = 0.0   # post / pre RMSPE ratio
                                      # (>2 = significant per
                                      # Abadie literature)
    notes: str = ""


def _project_to_simplex(v: np.ndarray) -> np.ndarray:
    """Project a vector onto the (probability) simplex
    {ω : ω ≥ 0, Σω = 1}. Wang & Carreira-Perpiñán O(N log N)
    closed-form algorithm.
    """
    n = len(v)
    u = np.sort(v)[::-1]
    cssv = np.cumsum(u) - 1.0
    rho = np.where(u - cssv / (np.arange(n) + 1.0) > 0)[0]
    if len(rho) == 0:
        return np.full(n, 1.0 / n)
    rho = rho[-1]
    theta = cssv[rho] / (rho + 1.0)
    return np.maximum(v - theta, 0.0)


def synthetic_control_estimate(
    Y: np.ndarray,
    *,
    treated_unit: int,
    treated_period: int,
    n_iterations: int = 500,
    learning_rate: float = 0.10,
) -> SyntheticControlResult:
    """Estimate the treatment effect via Synthetic Controls.

    Returns a SyntheticControlResult with simplex unit weights
    (sum-to-1, non-negative) and the ratio of post-treatment to
    pre-treatment RMSPE — Abadie literature's standard
    "placebo significance" check.
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
    n_ctl = len(control_idx)
    if n_ctl == 0:
        raise ValueError("Need at least one control unit")

    Y_ctl_pre = Y[control_idx][:, pre]            # (n_ctl, T_pre)
    Y_treated_pre = Y[treated_unit, pre]          # (T_pre,)

    # Initial: uniform simplex
    omega = np.full(n_ctl, 1.0 / n_ctl)
    for _ in range(n_iterations):
        # Synthetic pre = ω.T @ Y_ctl_pre  (since ω is (n_ctl,)
        # and Y_ctl_pre is (n_ctl, T_pre))
        synth_pre = omega @ Y_ctl_pre
        residual = synth_pre - Y_treated_pre
        # Gradient of 0.5 ||synth - Y_treated||² w.r.t. ω:
        # Y_ctl_pre @ residual
        grad = Y_ctl_pre @ residual
        omega = omega - learning_rate * grad
        omega = _project_to_simplex(omega)

    # Embed control weights back into a full N-vector
    full_omega = np.zeros(n_units)
    for k, idx in enumerate(control_idx):
        full_omega[idx] = omega[k]

    # Pre-period match RMSE
    synth_pre = omega @ Y_ctl_pre
    pre_rmse = float(np.sqrt(
        np.mean((synth_pre - Y_treated_pre) ** 2)))

    # Treatment effect = average post-treatment gap
    Y_ctl_post = Y[control_idx][:, post]         # (n_ctl, T_post)
    synth_post = omega @ Y_ctl_post
    treated_post = Y[treated_unit, post]
    effect = float(np.mean(treated_post - synth_post))

    # Placebo ratio: post-RMSPE / pre-RMSPE
    post_rmse = float(np.sqrt(
        np.mean((treated_post - synth_post) ** 2)))
    if pre_rmse > 1e-9:
        ratio = post_rmse / pre_rmse
    else:
        ratio = 0.0

    notes = ""
    if ratio < 2.0 and abs(effect) > 0:
        notes = ("Placebo ratio < 2 — effect is within the noise "
                 "band of the pre-treatment match. Treat as "
                 "suggestive, not significant.")

    return SyntheticControlResult(
        treatment_effect=effect,
        unit_weights=full_omega,
        treated_unit=treated_unit,
        n_units=n_units, n_periods=n_periods,
        pre_match_rmse=round(pre_rmse, 4),
        placebo_rmsi_ratio=round(ratio, 4),
        notes=notes,
    )
