"""Logistic regression in pure numpy.

Standard binary classification fit by gradient descent with L2
regularization. Used by the propensity-score module to estimate
P(treatment | covariates).

We deliberately keep the implementation small and inspectable —
diligence partners are skeptical of "AI black box" claims, and a
50-line logistic regression they can read line-by-line beats a
500-line scikit-learn import for that audience.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np


def _sigmoid(z: np.ndarray) -> np.ndarray:
    # Numerically stable sigmoid
    return np.where(
        z >= 0,
        1.0 / (1.0 + np.exp(-z)),
        np.exp(z) / (1.0 + np.exp(z)),
    )


@dataclass
class LogisticRegression:
    """Trained logistic-regression model — coefficients + intercept."""
    coefficients: np.ndarray = field(
        default_factory=lambda: np.zeros(0))
    intercept: float = 0.0
    converged: bool = False
    iterations: int = 0
    final_loss: float = 0.0

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return P(y=1 | X) for each row of X."""
        if X.size == 0:
            return np.array([])
        z = X @ self.coefficients + self.intercept
        return _sigmoid(z)


def fit_logistic(
    X: np.ndarray,
    y: np.ndarray,
    *,
    learning_rate: float = 0.05,
    l2_penalty: float = 0.01,
    max_iter: int = 500,
    tol: float = 1e-5,
) -> LogisticRegression:
    """Fit a logistic regression by full-batch gradient descent.

    Inputs:
      X — (n_samples, n_features) feature matrix.
      y — (n_samples,) binary labels in {0, 1}.

    Returns a fitted ``LogisticRegression``. The L2 penalty applies
    to coefficients only (intercept is unregularized — standard
    practice).
    """
    if X.size == 0 or y.size == 0:
        return LogisticRegression()
    n, d = X.shape
    coef = np.zeros(d)
    intercept = 0.0

    prev_loss = float("inf")
    for it in range(max_iter):
        z = X @ coef + intercept
        p = _sigmoid(z)
        # Cross-entropy loss with L2
        eps = 1e-12
        loss = -np.mean(
            y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)
        )
        loss += 0.5 * l2_penalty * np.sum(coef * coef)

        # Gradients
        residual = p - y
        grad_coef = (X.T @ residual) / n + l2_penalty * coef
        grad_intercept = float(residual.mean())

        coef -= learning_rate * grad_coef
        intercept -= learning_rate * grad_intercept

        if abs(prev_loss - loss) < tol:
            return LogisticRegression(
                coefficients=coef, intercept=intercept,
                converged=True, iterations=it + 1,
                final_loss=float(loss),
            )
        prev_loss = loss

    return LogisticRegression(
        coefficients=coef, intercept=intercept,
        converged=False, iterations=max_iter,
        final_loss=float(prev_loss),
    )
