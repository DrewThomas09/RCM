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

    def feature_importance(
        self,
    ) -> List[Tuple[str, float, float]]:
        """Global feature importance for the whole training set.

        Returns: list of (feature_name, std_coefficient,
        relative_importance) tuples sorted by |std_coefficient|
        descending. relative_importance is the share of total
        |coefficient| budget — sums to 1.0 across features.

        Because features are standardized at fit time, |β| has a
        clean interpretation: 'a 1-σ change in this feature
        moves the prediction by β units, holding others fixed.'
        Sign tells you direction; magnitude tells you importance.
        """
        abs_coefs = np.abs(self.coefficients)
        total = float(abs_coefs.sum())
        if total <= 0:
            return [(n, 0.0, 0.0)
                    for n in self.feature_names]
        out = []
        for i, n in enumerate(self.feature_names):
            beta = float(self.coefficients[i])
            rel = float(abs_coefs[i] / total)
            out.append((n, beta, rel))
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


def permutation_importance(
    predictor: TrainedRCMPredictor,
    X: Any,
    y: Any,
    *,
    n_repeats: int = 5,
    seed: int = 42,
) -> List[Tuple[str, float, float]]:
    """Permutation importance: for each feature, shuffle that
    column and measure how much R² drops. The drop is the
    feature's importance.

    More honest than |coefficient| because it accounts for
    feature correlations — a feature with a big coefficient
    that's redundant with another feature won't show much
    permutation importance.

    Returns: (name, importance_drop, std_drop) tuples sorted
    by importance_drop descending.
    """
    rng = np.random.default_rng(seed)
    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    base_pred = predictor.predict(X_arr)
    base_r2 = _r2_score(y_arr, base_pred)

    out = []
    for i, name in enumerate(predictor.feature_names):
        drops = []
        for _ in range(n_repeats):
            X_perm = X_arr.copy()
            rng.shuffle(X_perm[:, i])
            perm_pred = predictor.predict(X_perm)
            perm_r2 = _r2_score(y_arr, perm_pred)
            drops.append(base_r2 - perm_r2)
        out.append((
            name, float(np.mean(drops)),
            float(np.std(drops))))
    out.sort(key=lambda t: -t[1])
    return out


@dataclass
class CohortCVResult:
    """Per-cohort transfer skill: train on N-1 cohorts, evaluate
    on the left-out one. Catches the failure mode where a model
    trained on big urban hospitals doesn't transfer to rural
    critical-access — the standard k-fold score wouldn't notice
    because the held-out fold is iid with the training data."""
    cohort_labels: List[str]
    per_cohort_r2: Dict[str, float]
    per_cohort_mae: Dict[str, float]
    per_cohort_n: Dict[str, int]
    overall_transfer_r2: float
    worst_cohort: str
    worst_r2: float


def cross_validate_across_cohorts(
    X: Any,
    y: Any,
    cohort: List[Any],
    *,
    feature_names: List[str],
    alpha: float = 1.0,
    sanity_range: Tuple[float, float] = (-1e9, 1e9),
) -> CohortCVResult:
    """Leave-one-cohort-out CV. For each unique cohort label,
    train on all other cohorts, evaluate on this one.

    Args:
      X: (n, p) feature matrix.
      y: (n,) target vector.
      cohort: list of length n with cohort labels (e.g. bed-size
        bucket, region, urban/rural).
      feature_names: column labels for X.
      alpha: Ridge penalty.
      sanity_range: clip applied to predictions before evaluation.

    Returns: CohortCVResult — per-cohort R²+MAE+n, overall
    transfer R², worst-cohort label.
    """
    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    cohort_arr = np.array(cohort)
    if not (X_arr.shape[0] == y_arr.shape[0]
            == cohort_arr.shape[0]):
        raise ValueError(
            "X, y, cohort row counts must match")

    mask = (~np.isnan(X_arr).any(axis=1)
            & ~np.isnan(y_arr))
    X_arr = X_arr[mask]
    y_arr = y_arr[mask]
    cohort_arr = cohort_arr[mask]

    unique = sorted(set(cohort_arr.tolist()),
                    key=lambda x: str(x))
    if len(unique) < 2:
        raise ValueError(
            "Need ≥2 cohorts for "
            "leave-one-cohort-out CV")

    per_r2: Dict[str, float] = {}
    per_mae: Dict[str, float] = {}
    per_n: Dict[str, int] = {}
    all_y: List[float] = []
    all_yhat: List[float] = []
    for label in unique:
        train_mask = cohort_arr != label
        val_mask = cohort_arr == label
        if (int(train_mask.sum()) < 5
                or int(val_mask.sum()) < 1):
            per_r2[str(label)] = float("nan")
            per_mae[str(label)] = float("nan")
            per_n[str(label)] = int(val_mask.sum())
            continue
        Xtr = X_arr[train_mask]
        ytr = y_arr[train_mask]
        m = Xtr.mean(axis=0)
        s = Xtr.std(axis=0)
        s[s < 1e-9] = 1.0
        Xtr_s = (Xtr - m) / s
        b, _ = _ridge_fit(Xtr_s, ytr - ytr.mean(), alpha)
        Xv_s = (X_arr[val_mask] - m) / s
        yv_hat = Xv_s @ b + ytr.mean()
        lo, hi = sanity_range
        yv_hat = np.clip(yv_hat, lo, hi)
        yv_true = y_arr[val_mask]
        per_r2[str(label)] = _r2_score(yv_true, yv_hat)
        per_mae[str(label)] = float(
            np.mean(np.abs(yv_true - yv_hat)))
        per_n[str(label)] = int(val_mask.sum())
        all_y.extend(yv_true.tolist())
        all_yhat.extend(yv_hat.tolist())

    overall = _r2_score(
        np.array(all_y), np.array(all_yhat))
    valid = {k: v for k, v in per_r2.items()
             if not np.isnan(v)}
    if valid:
        worst = min(valid, key=valid.get)
        worst_r2 = valid[worst]
    else:
        worst = ""
        worst_r2 = float("nan")
    return CohortCVResult(
        cohort_labels=[str(u) for u in unique],
        per_cohort_r2=per_r2,
        per_cohort_mae=per_mae,
        per_cohort_n=per_n,
        overall_transfer_r2=overall,
        worst_cohort=worst,
        worst_r2=worst_r2,
    )
