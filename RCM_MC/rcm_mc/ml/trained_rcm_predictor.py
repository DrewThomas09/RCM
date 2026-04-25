"""Trained RCM-KPI predictor scaffold (Ridge + k-fold CV, pure numpy).

The existing ``rcm_performance_predictor.py`` applies a hand-coded
weight vector — useful for a heuristic, but it isn't *trained*.
This module ships the actual trained-from-data predictor:

  • Closed-form Ridge regression on standardized features
    (β̂ = (X̃ᵀX̃ + αI)⁻¹X̃ᵀỹ)
  • K-fold cross-validation across hospital cohorts (default
    5-fold, deterministic seed) — reports CV R², CV MAE,
    CV MAPE so the partner sees genuine out-of-sample skill,
    not training fit
  • Conformal-style 90% interval from CV residuals
  • Feature-contribution decomposition for every prediction

Usage::

    predictor = train_ridge_with_cv(
        X, y, feature_names=["beds", "medicare_pct", ...],
        target_metric="denial_rate")
    print(predictor.cv_r2_mean, predictor.cv_mae)
    yhat = predictor.predict_one({"beds": 200, ...})
    contributions = predictor.explain({"beds": 200, ...})

The two RCM-specific wrappers (denial_rate + days_in_ar) live in
sibling modules so each can carry its own feature set + sanity
range. This module is the *scaffold*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np


@dataclass
class TrainedRCMPredictor:
    """Result of fitting Ridge with CV. Self-contained — picklable
    via the dataclass-asdict path; no external state."""
    target_metric: str
    feature_names: List[str]
    feature_means: np.ndarray
    feature_stds: np.ndarray
    coefficients: np.ndarray  # in standardized space
    intercept: float          # in original (un-standardized) y scale
    target_mean: float
    alpha: float
    n_train: int
    train_r2: float
    cv_r2_mean: float
    cv_r2_std: float
    cv_mae: float
    cv_mape: Optional[float]
    cv_residual_p90: float       # 90th percentile of |residual|
    sanity_range: Tuple[float, float] = (-1e9, 1e9)

    def _standardize(self, X: np.ndarray) -> np.ndarray:
        return (X - self.feature_means) / self.feature_stds

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict for a (n_samples, n_features) matrix."""
        Xs = self._standardize(np.asarray(X, dtype=float))
        yhat = Xs @ self.coefficients + self.intercept
        lo, hi = self.sanity_range
        return np.clip(yhat, lo, hi)

    def predict_one(self, features: Dict[str, float]) -> float:
        """Predict for a single hospital. Missing features fall
        back to feature_means (the no-information default)."""
        x = np.array([
            features.get(n, self.feature_means[i])
            for i, n in enumerate(self.feature_names)
        ], dtype=float)
        return float(self.predict(x.reshape(1, -1))[0])

    def predict_with_interval(
        self, features: Dict[str, float],
    ) -> Tuple[float, Tuple[float, float]]:
        """Point + 90% conformal interval (residual-based)."""
        yhat = self.predict_one(features)
        margin = self.cv_residual_p90
        lo, hi = self.sanity_range
        return (yhat,
                (max(lo, yhat - margin),
                 min(hi, yhat + margin)))

    def explain(
        self, features: Dict[str, float],
    ) -> List[Tuple[str, float]]:
        """Per-feature signed contribution to the prediction.

        Sorted by |contribution| descending so the partner sees
        the biggest drivers first. Contributions sum to
        (yhat - target_mean) in expectation."""
        out: List[Tuple[str, float]] = []
        for i, n in enumerate(self.feature_names):
            v = features.get(n, self.feature_means[i])
            std_v = (v - self.feature_means[i]) / self.feature_stds[i]
            contrib = std_v * self.coefficients[i]
            out.append((n, float(contrib)))
        out.sort(key=lambda t: -abs(t[1]))
        return out


# ── Core fitting ──────────────────────────────────────────────

def _ridge_fit(
    X: np.ndarray,
    y: np.ndarray,
    alpha: float,
) -> Tuple[np.ndarray, float]:
    """Closed-form Ridge on standardized X.

    Returns (coefficients, intercept). The intercept is
    y_mean (since X is centered)."""
    n, p = X.shape
    XtX = X.T @ X
    A = XtX + alpha * np.eye(p)
    XtY = X.T @ y
    beta = np.linalg.solve(A, XtY)
    intercept = float(np.mean(y))
    return beta, intercept


def _r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    if ss_tot <= 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def _kfold_indices(
    n: int, k: int, seed: int,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Deterministic k-fold splits. Returns list of
    (train_idx, val_idx) tuples."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    folds = np.array_split(idx, k)
    out = []
    for i in range(k):
        val = folds[i]
        train = np.concatenate(
            [folds[j] for j in range(k) if j != i])
        out.append((train, val))
    return out


def train_ridge_with_cv(
    X: Any,
    y: Any,
    *,
    feature_names: List[str],
    target_metric: str,
    alpha: float = 1.0,
    n_folds: int = 5,
    seed: int = 42,
    sanity_range: Tuple[float, float] = (-1e9, 1e9),
) -> TrainedRCMPredictor:
    """Fit Ridge with k-fold CV. Pure numpy.

    Args:
      X: (n, p) feature matrix or pandas-like with columns matching
        feature_names. NaN rows are dropped; we don't impute mid-fit
        because RCM data quality is the partner's first signal.
      y: (n,) target vector.
      feature_names: column labels for X.
      target_metric: human label, threaded through to the result.
      alpha: Ridge penalty. 1.0 is a safe default for standardized
        features; tune via outer search if needed.
      n_folds: 5 by default. Smaller for tiny training sets.
      seed: deterministic.
      sanity_range: (lo, hi) clip applied to all predictions.
        e.g. (0.0, 0.5) for denial-rate.

    Returns: TrainedRCMPredictor with fit + CV diagnostics.
    """
    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if X_arr.ndim != 2:
        raise ValueError(
            f"X must be 2-D, got shape {X_arr.shape}")
    if X_arr.shape[0] != y_arr.shape[0]:
        raise ValueError("X and y row counts mismatch")
    if X_arr.shape[1] != len(feature_names):
        raise ValueError(
            "feature_names length must equal X cols")

    # Drop rows with any NaN in features or target
    mask = (~np.isnan(X_arr).any(axis=1)
            & ~np.isnan(y_arr))
    X_arr = X_arr[mask]
    y_arr = y_arr[mask]
    n = X_arr.shape[0]
    if n < n_folds * 2:
        raise ValueError(
            f"Need ≥{n_folds * 2} clean rows for "
            f"{n_folds}-fold CV; got {n}")

    # Standardize features
    means = X_arr.mean(axis=0)
    stds = X_arr.std(axis=0)
    stds[stds < 1e-9] = 1.0  # constant column → no-op scaler
    Xs = (X_arr - means) / stds
    y_centered = y_arr - y_arr.mean()

    # Full-data fit
    beta, _intercept_unused = _ridge_fit(
        Xs, y_centered, alpha)
    intercept = float(y_arr.mean())
    yhat_train = Xs @ beta + intercept
    train_r2 = _r2_score(y_arr, yhat_train)

    # k-fold CV
    cv_r2s: List[float] = []
    cv_residuals: List[np.ndarray] = []
    for train_idx, val_idx in _kfold_indices(
            n, n_folds, seed):
        Xtr = X_arr[train_idx]
        ytr = y_arr[train_idx]
        m = Xtr.mean(axis=0)
        s = Xtr.std(axis=0)
        s[s < 1e-9] = 1.0
        Xtr_s = (Xtr - m) / s
        b, _ = _ridge_fit(Xtr_s, ytr - ytr.mean(), alpha)
        Xv_s = (X_arr[val_idx] - m) / s
        yv_hat = Xv_s @ b + ytr.mean()
        yv_true = y_arr[val_idx]
        cv_r2s.append(_r2_score(yv_true, yv_hat))
        cv_residuals.append(np.abs(yv_true - yv_hat))

    cv_r2 = float(np.mean(cv_r2s))
    cv_r2_std = float(np.std(cv_r2s))
    all_resid = np.concatenate(cv_residuals)
    cv_mae = float(np.mean(all_resid))
    nonzero = y_arr != 0
    if nonzero.any():
        # MAPE on rows where target is non-zero (avoid /0)
        all_y = np.concatenate([
            y_arr[v] for _, v
            in _kfold_indices(n, n_folds, seed)])
        all_yhat = []
        for tr, v in _kfold_indices(n, n_folds, seed):
            Xtr = X_arr[tr]
            ytr = y_arr[tr]
            m = Xtr.mean(axis=0)
            s = Xtr.std(axis=0)
            s[s < 1e-9] = 1.0
            Xtr_s = (Xtr - m) / s
            b, _ = _ridge_fit(
                Xtr_s, ytr - ytr.mean(), alpha)
            Xv_s = (X_arr[v] - m) / s
            all_yhat.append(Xv_s @ b + ytr.mean())
        all_yhat = np.concatenate(all_yhat)
        nz = all_y != 0
        cv_mape = (float(np.mean(
            np.abs((all_y[nz] - all_yhat[nz]) / all_y[nz])))
            if nz.any() else None)
    else:
        cv_mape = None

    cv_resid_p90 = float(np.quantile(all_resid, 0.90))

    return TrainedRCMPredictor(
        target_metric=target_metric,
        feature_names=list(feature_names),
        feature_means=means,
        feature_stds=stds,
        coefficients=beta,
        intercept=intercept,
        target_mean=float(y_arr.mean()),
        alpha=alpha,
        n_train=n,
        train_r2=train_r2,
        cv_r2_mean=cv_r2,
        cv_r2_std=cv_r2_std,
        cv_mae=cv_mae,
        cv_mape=cv_mape,
        cv_residual_p90=cv_resid_p90,
        sanity_range=sanity_range,
    )
