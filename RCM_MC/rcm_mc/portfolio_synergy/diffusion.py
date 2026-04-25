"""Best-practice diffusion modeling.

When a sponsor implements a best practice at one portfolio
company (e.g., AI-enabled denial-management workflow), it
diffuses to the other portfolio companies over time. The
adoption curve is empirically logistic:

    f(t) = L / (1 + exp(-k(t − t0)))

where L is the asymptotic adoption fraction (rarely 100%; more
like 75-85% in healthcare PE due to platform heterogeneity), k
is the diffusion speed (peer-to-peer coaching, formal program
office, etc.), and t0 is the inflection point.

This module fits the curve to historical adoption data + uses
the fitted parameters to forecast adoption + EBITDA-lift timing
for a new add-on entering the portfolio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

import numpy as np


@dataclass
class DiffusionCurve:
    """Logistic-fit parameters."""
    L: float          # asymptote (max adoption fraction)
    k: float          # diffusion speed
    t0: float         # inflection point (months)
    rmse: float       # fit quality
    n_observations: int = 0


@dataclass
class SynergyTiming:
    """Predicted timing for a new add-on."""
    months_to_50pct_adoption: float
    months_to_80pct_adoption: float
    expected_ebitda_lift_at_18mo: float    # as % of platform EBITDA
    expected_ebitda_lift_at_36mo: float


def _logistic(t: np.ndarray, L: float, k: float,
              t0: float) -> np.ndarray:
    return L / (1.0 + np.exp(-k * (t - t0)))


def fit_diffusion_curve(
    months: Iterable[float],
    adoption_fractions: Iterable[float],
    *,
    n_iterations: int = 200,
    learning_rate: float = 0.05,
) -> DiffusionCurve:
    """Fit the logistic curve via gradient descent.

    Inputs are matched arrays: months[i] = t, adoption[i] = f(t).
    """
    t = np.asarray(list(months), dtype=float)
    y = np.asarray(list(adoption_fractions), dtype=float)
    n = len(t)
    if n < 4:
        # Too few points for a stable fit
        L = float(max(y)) if n else 0.0
        return DiffusionCurve(
            L=L, k=0.10,
            t0=float(t.mean()) if n else 0.0,
            rmse=0.0, n_observations=n)

    # Initial guesses
    L = max(0.5, float(y.max()) + 0.05)
    k = 0.20
    t0 = float(t.mean())

    for _ in range(n_iterations):
        pred = _logistic(t, L, k, t0)
        err = pred - y
        # Numerical gradients (analytic gradients are clean but
        # the diligence-grade tolerance here is loose; finite
        # differences keep the implementation small + auditable)
        eps = 1e-4
        grad_L = float(np.mean(
            err * (_logistic(t, L + eps, k, t0) - pred) / eps))
        grad_k = float(np.mean(
            err * (_logistic(t, L, k + eps, t0) - pred) / eps))
        grad_t0 = float(np.mean(
            err * (_logistic(t, L, k, t0 + eps) - pred) / eps))
        L -= learning_rate * grad_L
        k -= learning_rate * grad_k
        t0 -= learning_rate * grad_t0
        # Constrain L into [0, 1]
        L = max(0.05, min(1.0, L))
        # k > 0 keeps the curve monotone-increasing
        k = max(0.01, k)

    pred = _logistic(t, L, k, t0)
    rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
    return DiffusionCurve(
        L=round(L, 4), k=round(k, 4), t0=round(t0, 2),
        rmse=round(rmse, 4), n_observations=n,
    )


def predict_synergy_timing(
    curve: DiffusionCurve,
    *,
    target_ebitda_lift_pct: float = 0.10,
) -> SynergyTiming:
    """Forecast adoption + EBITDA-lift timing for a new add-on.

    target_ebitda_lift_pct is the assumed EBITDA-lift impact
    when the practice fully takes hold at the add-on (default
    10% of the add-on's EBITDA).
    """
    L = curve.L
    k = curve.k
    t0 = curve.t0

    # Solve t for f(t) = 0.5 × L → 0.5 × L = L / (1 + e^(-k(t-t0)))
    # → 1 + e^(-k(t-t0)) = 2 → t = t0
    t_50 = t0

    # Solve t for f(t) = 0.8 × L
    # 0.8 = 1 / (1 + e^(-k(t-t0)))
    # → e^(-k(t-t0)) = 0.25
    # → t = t0 + ln(4)/k
    t_80 = t0 + (np.log(4.0) / k)

    # EBITDA lift at month X = adoption(X) × target_ebitda_lift_pct
    lift_18 = float(_logistic(np.array([18.0]), L, k, t0)[0]
                    * target_ebitda_lift_pct)
    lift_36 = float(_logistic(np.array([36.0]), L, k, t0)[0]
                    * target_ebitda_lift_pct)

    return SynergyTiming(
        months_to_50pct_adoption=round(t_50, 2),
        months_to_80pct_adoption=round(t_80, 2),
        expected_ebitda_lift_at_18mo=round(lift_18, 4),
        expected_ebitda_lift_at_36mo=round(lift_36, 4),
    )
