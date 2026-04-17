"""Split conformal prediction — distribution-free uncertainty intervals.

Why conformal over bootstrap / parametric CIs:
- Gives *finite-sample coverage guarantees*: if the predictor is
  exchangeable on the calibration set and new point, the 90% interval
  really contains the truth 90% of the time. No normality assumption.
- One page of numpy — no sklearn. Matches the project's
  stdlib-and-numpy dependency stance.
- Calibrates per-metric: a poorly-fit Ridge gets a wide margin; a
  well-fit one gets a tight one. The partner sees the model's honest
  uncertainty, not a fake-confident ±2σ.

This module is the base predictor-agnostic primitive. The caller
(``ridge_predictor``) passes any object with ``.fit(X, y)`` and
``.predict(X)`` methods. For the weighted-median and benchmark-fallback
branches we have :func:`bootstrap_interval` and :func:`percentile_interval`
helpers in the same module so every branch produces the same
``(point, low, high)`` tuple shape.

References:
- Vovk, Gammerman & Shafer (2005) — "Algorithmic Learning in a Random World"
- Angelopoulos & Bates (2021) — "A Gentle Introduction to Conformal
  Prediction"
"""
from __future__ import annotations

import math
from typing import Any, Protocol, Tuple

import numpy as np


class _BaseModel(Protocol):
    def fit(self, X: np.ndarray, y: np.ndarray) -> "_BaseModel": ...
    def predict(self, X: np.ndarray) -> np.ndarray: ...


class ConformalPredictor:
    """Split conformal regression wrapper.

    Usage::

        cp = ConformalPredictor(base_model=RidgeModel(), coverage=0.90)
        cp.fit(X_train, y_train, X_cal, y_cal)
        point, low, high = cp.predict_interval(X_new)

    The margin is the ``ceil((1-α)(n+1)) / n``-quantile of the absolute
    residuals on the calibration set — the standard split-conformal
    formula. On small calibration sets we clamp the quantile to 1.0
    (widest observed residual), which is the right thing to do —
    under-covering a 90% interval is worse than over-covering it.
    """

    def __init__(self, base_model: _BaseModel, coverage: float = 0.90) -> None:
        if not (0.0 < coverage < 1.0):
            raise ValueError(f"coverage must be in (0, 1), got {coverage}")
        self.base_model = base_model
        self.coverage = float(coverage)
        self.margin = 0.0
        self.residuals: np.ndarray = np.asarray([], dtype=float)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_cal: np.ndarray,
        y_cal: np.ndarray,
    ) -> "ConformalPredictor":
        """Fit base model on train split; compute margin from cal residuals."""
        X_train = np.asarray(X_train, dtype=float)
        y_train = np.asarray(y_train, dtype=float)
        X_cal = np.asarray(X_cal, dtype=float)
        y_cal = np.asarray(y_cal, dtype=float)

        self.base_model.fit(X_train, y_train)
        if len(X_cal) == 0:
            # Nothing to calibrate on — return a zero-width interval and
            # mark empty residuals. Caller should notice.
            self.margin = 0.0
            self.residuals = np.asarray([], dtype=float)
            return self
        y_pred_cal = np.asarray(self.base_model.predict(X_cal), dtype=float)
        self.residuals = np.abs(y_cal - y_pred_cal)

        n = len(self.residuals)
        alpha = 1.0 - self.coverage
        # ceil((1-α)(n+1)) / n — the correct split-conformal quantile
        # level. Clamp to 1.0 on small n (degenerate to max residual).
        q_level = math.ceil((1.0 - alpha) * (n + 1)) / n
        q_level = min(q_level, 1.0)
        self.margin = float(np.quantile(self.residuals, q_level))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self.base_model.predict(X), dtype=float)

    def predict_interval(
        self, X_new: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return ``(point, low, high)`` arrays for ``X_new``."""
        y_pred = self.predict(X_new)
        return y_pred, y_pred - self.margin, y_pred + self.margin


# ── Non-ridge interval helpers ───────────────────────────────────────

def bootstrap_interval(
    values: np.ndarray,
    weights: np.ndarray | None = None,
    *,
    coverage: float = 0.90,
    n_bootstrap: int = 1000,
    statistic: str = "weighted_median",
    random_state: int = 0,
) -> Tuple[float, float, float]:
    """Bootstrap ``(point, low, high)`` for the weighted-median fallback.

    Resamples ``values`` with replacement ``n_bootstrap`` times and
    computes the chosen statistic on each draw. The returned low/high
    are the symmetric percentile bounds of the bootstrap distribution.

    ``statistic`` = ``"weighted_median"`` | ``"median"`` | ``"mean"``.
    """
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return (0.0, 0.0, 0.0)
    if weights is None or len(weights) != len(values):
        weights = np.ones_like(values)
    else:
        weights = np.asarray(weights, dtype=float)
    if not np.any(weights > 0):
        weights = np.ones_like(values)

    rng = np.random.default_rng(int(random_state))
    n = len(values)
    draws = rng.integers(0, n, size=(int(n_bootstrap), n))

    def _stat(sample_vals: np.ndarray, sample_w: np.ndarray) -> float:
        if statistic == "mean":
            s = float(sample_w.sum())
            return float((sample_vals * sample_w).sum() / s) if s > 0 else float(sample_vals.mean())
        if statistic == "median":
            return float(np.median(sample_vals))
        # Weighted median (default).
        order = np.argsort(sample_vals)
        v_sorted = sample_vals[order]
        w_sorted = sample_w[order]
        cum = np.cumsum(w_sorted)
        total = cum[-1]
        if total <= 0:
            return float(np.median(sample_vals))
        cutoff = total / 2.0
        idx = int(np.searchsorted(cum, cutoff))
        idx = min(idx, len(v_sorted) - 1)
        return float(v_sorted[idx])

    stats = np.empty(int(n_bootstrap), dtype=float)
    for i in range(int(n_bootstrap)):
        idx = draws[i]
        stats[i] = _stat(values[idx], weights[idx])
    alpha = 1.0 - coverage
    low = float(np.quantile(stats, alpha / 2.0))
    high = float(np.quantile(stats, 1.0 - alpha / 2.0))
    point = _stat(values, weights)
    return (point, low, high)


def percentile_interval(
    p25: float, p50: float, p75: float,
) -> Tuple[float, float, float]:
    """Benchmark-fallback interval: P50 with [P25, P75] as the band.

    We deliberately do NOT stretch this to match ``coverage`` because:
    with no hospital-specific data we can't claim 90% coverage. The
    IQR is a partner-defensible "typical range" that honestly widens
    the uncertainty compared to the ridge branch.
    """
    return (float(p50), float(p25), float(p75))


def split_train_calibration(
    X: np.ndarray,
    y: np.ndarray,
    *,
    cal_fraction: float = 0.30,
    random_state: int = 0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic train/cal split. ``cal_fraction`` rounded so the
    calibration set has at least 2 points whenever ``len(X) >= 4``.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(X)
    if n == 0:
        return X, y, X, y
    rng = np.random.default_rng(int(random_state))
    idx = rng.permutation(n)
    n_cal = max(1, int(round(n * float(cal_fraction))))
    # Keep training set non-empty.
    n_cal = min(n_cal, n - 1) if n > 1 else 0
    cal_idx = idx[:n_cal]
    train_idx = idx[n_cal:]
    return X[train_idx], y[train_idx], X[cal_idx], y[cal_idx]
