"""Control-variate variance reduction.

If we want E[Y] but observe (Y, Z) where E[Z] is known and Z is
correlated with Y, the control-variate estimator

    Y_cv = Y − β (Z − E[Z])

has lower variance than Y alone. Optimal β = Cov(Y, Z) / Var(Z),
estimated from the same sample.

Useful when pricing a complicated payoff Y by piggy-backing on
a simpler proxy Z whose expectation is computable in closed form
(e.g. a Black-Scholes call vs. a path-dependent option).
"""
from __future__ import annotations

from typing import Tuple

import numpy as np


def control_variate_estimate(
    y_samples: np.ndarray,
    z_samples: np.ndarray,
    z_expectation: float,
) -> Tuple[float, float, float]:
    """Compute the control-variate estimator + variance reduction.

    Returns:
      (estimate, std_error, variance_reduction_pct)
    """
    if y_samples.shape != z_samples.shape:
        raise ValueError("y_samples and z_samples must align")
    n = y_samples.size
    if n < 2:
        return float(y_samples.mean() if n else 0.0), 0.0, 0.0

    cov = float(np.cov(y_samples, z_samples, ddof=1)[0, 1])
    var_z = float(np.var(z_samples, ddof=1))
    if var_z <= 0:
        return float(y_samples.mean()), float(
            y_samples.std(ddof=1) / np.sqrt(n)), 0.0
    beta = cov / var_z
    adjusted = y_samples - beta * (z_samples - z_expectation)
    est = float(adjusted.mean())
    se = float(adjusted.std(ddof=1) / np.sqrt(n))

    # Variance reduction vs. plain MC
    plain_var = float(np.var(y_samples, ddof=1))
    cv_var = float(np.var(adjusted, ddof=1))
    reduction = (1.0 - cv_var / max(1e-12, plain_var)) * 100.0
    return est, se, reduction
