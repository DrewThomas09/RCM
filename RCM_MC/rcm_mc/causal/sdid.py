"""Synthetic Difference-in-Differences (SDID).

Implements the closed-form treatment-effect estimator from
Arkhangelsky, Athey, Hirshberg, Imbens, Wager (2021).

Inputs:
  Y: (N units) × (T periods) outcome panel.
  treated_unit: row index of the treated unit (e.g., the
    portfolio company that adopted the best practice).
  treated_period: column index where treatment starts. All
    periods < treated_period are pre-treatment.

Outputs:
  unit_weights ω* fitted on pre-treatment data so that the
    weighted control units' outcomes match the treated unit's.
  time_weights λ* fitted on control-unit data so that the
    weighted pre-treatment periods match the post-treatment
    periods.
  effect = (Ŷ_post_treated − Ŷ_post_control_weighted)
         − (Ŷ_pre_treated  − Ŷ_pre_control_weighted)

Closed-form via L2-regularized regression (no iterative solver
needed for diligence-grade panels with N ≤ 50 units, T ≤ 24
periods).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class SDIDResult:
    treatment_effect: float
    unit_weights: np.ndarray = field(
        default_factory=lambda: np.zeros(0))
    time_weights: np.ndarray = field(
        default_factory=lambda: np.zeros(0))
    n_units: int = 0
    n_periods: int = 0
    pre_treatment_match_quality: float = 0.0   # R² on pre period
    notes: str = ""


def _ridge_weights(
    X: np.ndarray,
    y: np.ndarray,
    *,
    ridge: float = 0.10,
) -> np.ndarray:
    """Solve the convex problem
        min ||X w − y||² + ridge ||w||²
    by closed form. Returns unconstrained weights; callers can
    normalize or clip as needed for the SDID convention.
    """
    XtX = X.T @ X + ridge * np.eye(X.shape[1])
    return np.linalg.solve(XtX, X.T @ y)


def _normalized_weights(w: np.ndarray) -> np.ndarray:
    """Normalize to sum to 1 (the SDID convention for the unit
    + time weight vectors)."""
    s = float(w.sum())
    if s <= 0:
        # All zero or negative — use uniform weights as fallback
        return np.ones(len(w)) / len(w)
    return w / s


def sdid_estimate(
    Y: np.ndarray,
    *,
    treated_unit: int,
    treated_period: int,
    ridge: float = 0.10,
) -> SDIDResult:
    """Estimate the treatment effect via synthetic DiD.

    Y: (N, T) panel. treated_unit is the row index whose
    treatment effect we're estimating; treated_period is the
    column index where treatment begins.
    """
    Y = np.asarray(Y, dtype=float)
    if Y.ndim != 2:
        raise ValueError("Y must be 2-D (n_units × n_periods)")
    n_units, n_periods = Y.shape
    if not (0 <= treated_unit < n_units):
        raise ValueError("treated_unit out of range")
    if not (0 < treated_period < n_periods):
        raise ValueError("treated_period out of range "
                         "(must be > 0 and < n_periods)")

    # Pre / post split
    pre_periods = list(range(treated_period))
    post_periods = list(range(treated_period, n_periods))

    # Control units = all units except treated
    control_idx = [i for i in range(n_units) if i != treated_unit]
    Y_pre_ctl = Y[control_idx][:, pre_periods]    # (N-1, T_pre)
    Y_pre_treated = Y[treated_unit, pre_periods]  # (T_pre,)

    # ── Unit weights ω* ─────────────────────────────────────
    # Solve: min || Y_pre_ctl.T @ ω − Y_pre_treated ||²
    # Y_pre_ctl.T is (T_pre, N-1); ω is (N-1,)
    omega_raw = _ridge_weights(
        Y_pre_ctl.T, Y_pre_treated, ridge=ridge)
    omega = _normalized_weights(omega_raw)

    # Embed the (N-1) control weights back into a full N-vector
    # with 0 at the treated row position.
    full_omega = np.zeros(n_units)
    for k, idx in enumerate(control_idx):
        full_omega[idx] = omega[k]

    # ── Time weights λ* ─────────────────────────────────────
    # Solve: min || Y_ctl_pre @ λ − Y_ctl_post_mean ||²
    Y_ctl_pre = Y[control_idx][:, pre_periods]     # (N-1, T_pre)
    Y_ctl_post = Y[control_idx][:, post_periods]   # (N-1, T_post)
    Y_ctl_post_mean = Y_ctl_post.mean(axis=1)      # (N-1,)
    if len(pre_periods) >= 1:
        lam_raw = _ridge_weights(
            Y_ctl_pre, Y_ctl_post_mean, ridge=ridge)
        lam = _normalized_weights(lam_raw)
    else:
        lam = np.array([])

    full_lambda = np.zeros(n_periods)
    for k, idx in enumerate(pre_periods):
        full_lambda[idx] = lam[k] if k < len(lam) else 0.0

    # ── Treatment effect ────────────────────────────────────
    # Treated post mean (uniform over post-periods)
    treated_post = Y[treated_unit, post_periods].mean()
    # Control post — weighted by ω across units
    control_post = sum(
        full_omega[i] * Y[i, post_periods].mean()
        for i in range(n_units))
    # Treated pre — weighted by λ across pre-periods
    if len(pre_periods) > 0 and len(lam) > 0:
        treated_pre = sum(
            lam[k] * Y[treated_unit, pre_periods[k]]
            for k in range(len(pre_periods)))
        # Control pre — double-weighted by ω × λ
        control_pre = sum(
            full_omega[i] * sum(
                lam[k] * Y[i, pre_periods[k]]
                for k in range(len(pre_periods)))
            for i in range(n_units))
    else:
        treated_pre = float(Y[treated_unit, :treated_period].mean())
        control_pre = sum(
            full_omega[i] * Y[i, :treated_period].mean()
            for i in range(n_units))

    effect = (treated_post - control_post) - (
        treated_pre - control_pre)

    # Pre-treatment match R²: how well the weighted control
    # tracked the treated unit pre-treatment.
    if len(pre_periods) > 0:
        synthetic_pre = (
            np.array(control_idx_to_full_omega := [
                Y[i, pre_periods] for i in control_idx])
            .T @ omega
        )
        ss_res = float(np.sum(
            (Y_pre_treated - synthetic_pre) ** 2))
        ss_tot = float(np.sum(
            (Y_pre_treated - Y_pre_treated.mean()) ** 2)) or 1e-9
        r2 = 1.0 - ss_res / ss_tot
    else:
        r2 = 0.0

    return SDIDResult(
        treatment_effect=float(effect),
        unit_weights=full_omega,
        time_weights=full_lambda,
        n_units=n_units,
        n_periods=n_periods,
        pre_treatment_match_quality=float(round(r2, 4)),
    )
