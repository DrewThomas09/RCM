"""k-fold cross-validation for the regression rebuild — Phase 4A.

Phase 1–3 made the regression diagnostic: it surfaces in-sample R²,
collinearity, segment-specific fits, and leakage flags. Phase 4
finally lets the page answer the question the diagnostic banner
explicitly punts on:

  Does this model generalize to hospitals it hasn't seen?

This module runs deterministic k-fold cross-validation on the same
OLS engine used in :mod:`rcm_mc.finance.regression`. For each
fold the test set is held out, the model is fit on the remaining
rows, and out-of-sample R² / RMSE / MAE are computed on the held-
out fold. Per-fold metrics + aggregate mean ± std are returned so
the UI can show partner-facing OOS numbers next to the in-sample
ones — a much smaller R² out-of-sample than in-sample is the
canonical overfit signature.

Uses numpy only (no sklearn) to keep the zero-runtime-deps rule
from CLAUDE.md.

DIAGNOSTIC SCOPE NOTE: CV makes the OOS claim that in-sample fits
cannot. A partner reading "Test R² = 0.42, Train R² = 0.61" gets
the truthful generalization picture. CV does NOT fix leakage —
if leaky features are still in the spec, CV will report inflated
OOS numbers too. Run with ``drop_leakage=True`` upstream for the
honest forecasting picture.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CVFoldResult:
    """Metrics for one fold of k-fold CV.

    All metrics computed on the held-out test set (out-of-sample).
    ``train_r_squared`` is the in-sample R² on the rest — included
    so the partner can read train-vs-test gap fold by fold.
    """
    fold: int
    n_train: int
    n_test: int
    train_r_squared: float
    test_r_squared: float
    test_rmse: float
    test_mae: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "fold": self.fold,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "train_r_squared": round(self.train_r_squared, 4),
            "test_r_squared": round(self.test_r_squared, 4),
            "test_rmse": round(self.test_rmse, 4),
            "test_mae": round(self.test_mae, 4),
        }


@dataclass
class CVResult:
    """k-fold cross-validation summary.

    ``mean_test_r2`` / ``std_test_r2`` are the partner-facing
    headline numbers. A big gap between ``baseline_in_sample_r2``
    (model fit on every row, scored on every row) and
    ``mean_test_r2`` is the overfit signal — the larger the gap,
    the more the in-sample R² was reading off noise / leakage /
    high-influence rows.

    ``requested_k`` and ``k`` will differ only when the caller passed
    ``auto_reduce_k=True`` and the requested k was too aggressive for
    the universe size — k was knocked down to the largest viable
    value. The UI surfaces this so the partner knows their "5-fold"
    request actually became 3-fold on a thin CAH universe.
    """
    target: str
    features: List[str]
    k: int
    target_was_log_transformed: bool
    baseline_in_sample_r2: float
    mean_train_r2: float
    mean_test_r2: float
    std_test_r2: float
    mean_test_rmse: float
    mean_test_mae: float
    folds: List[CVFoldResult] = field(default_factory=list)
    requested_k: Optional[int] = None  # only set when auto-reduced
    # Empirical prediction-interval coverage (Phase 5 — editorial
    # redesign spec §8). Each entry quotes the fraction of held-out
    # test rows whose absolute residual fell inside a PI whose half-
    # width was set from the TRAINING fold's |resid| quantile at the
    # nominal level. Honest: this is a leave-one-fold-out conformal
    # estimate, not a parametric Gaussian PI. Empty list when CV was
    # skipped or coverage couldn't be computed.
    pi_coverage: List[Dict[str, float]] = field(default_factory=list)

    @property
    def overfit_gap(self) -> float:
        """In-sample R² minus mean OOS R². Larger = more overfit."""
        return self.baseline_in_sample_r2 - self.mean_test_r2

    def to_dict(self) -> Dict[str, object]:
        return {
            "target": self.target,
            "features": self.features,
            "k": self.k,
            "requested_k": self.requested_k,
            "target_was_log_transformed":
                self.target_was_log_transformed,
            "baseline_in_sample_r2": round(self.baseline_in_sample_r2, 4),
            "mean_train_r2": round(self.mean_train_r2, 4),
            "mean_test_r2": round(self.mean_test_r2, 4),
            "std_test_r2": round(self.std_test_r2, 4),
            "mean_test_rmse": round(self.mean_test_rmse, 4),
            "mean_test_mae": round(self.mean_test_mae, 4),
            "overfit_gap": round(self.overfit_gap, 4),
            "folds": [f.to_dict() for f in self.folds],
            "pi_coverage": [dict(p) for p in self.pi_coverage],
        }


def _ols_fit(X: np.ndarray, y: np.ndarray):
    """Fit OLS with intercept; return beta. Falls back to lstsq on
    singular matrices."""
    X_aug = np.column_stack([np.ones(len(X)), X])
    return np.linalg.lstsq(X_aug, y, rcond=None)[0]


def _predict(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(X)), X]) @ beta


def _r2(y, y_hat) -> float:
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 0:
        return 0.0
    ss_res = float(np.sum((y - y_hat) ** 2))
    return 1.0 - ss_res / ss_tot


def _min_rows_for_k(p: int, k: int) -> int:
    """Conservative row floor: each training set ≥ 2 * (p + 2) rows,
    AND each fold has ≥ 5 test rows."""
    return max(2 * (p + 2) * k, k * 5)


def run_cv_regression(
    df: pd.DataFrame,
    target: str,
    features: Optional[List[str]] = None,
    *,
    k: int = 5,
    log_transform_target: bool = False,
    random_state: int = 42,
    auto_reduce_k: bool = False,
) -> CVResult:
    """Run k-fold cross-validation on an OLS spec.

    The fold-assignment is deterministic (seeded), so the same df +
    spec always returns the same folds. This matters for partner
    trust — re-running the page on the same data shouldn't shuffle
    the OOS numbers around.

    Behavior mirrors :func:`rcm_mc.finance.regression.run_regression`
    where it overlaps:
      - same dropna semantics for target + features
      - log_transform_target drops rows where target ≤ 0
      - rejects calls with too few rows for a stable fold split
        (each fold's training set must clear ``n_features + 2``).

    ``auto_reduce_k=True``: when the requested ``k`` is too aggressive
    for the universe size, knock k down to the largest viable value
    (≥ 2). Lets thin universes (CAH, Small Community segments) still
    get OOS numbers instead of an error. ``CVResult.requested_k``
    records what the caller asked for so the UI can surface the
    reduction.

    Raises ``ValueError`` for unrecoverable inputs (missing target,
    no usable features, k < 2, too few rows even for k=2).
    """
    if k < 2:
        raise ValueError(f"k must be at least 2, got {k}")

    numeric_df = df.select_dtypes(include=[np.number]).dropna()
    if target not in numeric_df.columns:
        raise ValueError(f"target {target!r} not in numeric columns")

    if features is None:
        features = [c for c in numeric_df.columns if c != target]
    features = [
        f for f in features
        if f in numeric_df.columns and f != target
    ]
    if not features:
        raise ValueError("no valid feature columns")

    clean = numeric_df[[target] + features].dropna()
    if log_transform_target:
        clean = clean[clean[target] > 0]
    n = len(clean)
    p = len(features)
    # Each fold's training set must have enough rows for a stable
    # fit — n*(k-1)/k > p + 1. Conservative threshold: n > 2 * p * k.
    requested_k: Optional[int] = None
    if n < _min_rows_for_k(p, k):
        if auto_reduce_k:
            # Walk k down to the largest viable value ≥ 2. CAH and
            # Small Community universes often hit this — without
            # auto-reduce the partner just sees a "need 70 rows"
            # error and no OOS numbers at all.
            original_k = k
            new_k = None
            for trial_k in range(k - 1, 1, -1):
                if n >= _min_rows_for_k(p, trial_k):
                    new_k = trial_k
                    break
            if new_k is None:
                raise ValueError(
                    f"need at least {_min_rows_for_k(p, 2)} rows for "
                    f"even 2-fold CV with {p} features, got {n}"
                )
            requested_k = original_k
            k = new_k
        else:
            raise ValueError(
                f"need at least {_min_rows_for_k(p, k)} rows for "
                f"{k}-fold CV with {p} features, got {n}"
            )

    y_raw = clean[target].values.astype(float)
    y = np.log(y_raw) if log_transform_target else y_raw
    X = clean[features].values.astype(float)

    # Deterministic fold assignment via seeded permutation
    rng = np.random.default_rng(random_state)
    perm = rng.permutation(n)
    fold_sizes = np.array([n // k] * k)
    fold_sizes[: n % k] += 1
    fold_starts = np.cumsum(np.concatenate([[0], fold_sizes[:-1]]))

    folds: List[CVFoldResult] = []
    train_r2s = []
    test_r2s = []
    test_rmses = []
    test_maes = []
    # Empirical PI coverage (spec §8) — accumulated across folds.
    # For each nominal level we record per-fold (within_count, total)
    # then aggregate at the end. Width half-widths come from the
    # TRAINING fold's |resid| at the matching quantile — this is the
    # split-conformal construction, which is finite-sample valid
    # under row-exchangeability without distributional assumptions
    # on residuals.
    pi_levels = (0.5, 0.8, 0.95)
    pi_hits = {lvl: 0 for lvl in pi_levels}
    pi_widths_abs: Dict[float, List[float]] = {lvl: [] for lvl in pi_levels}
    pi_total = 0

    for i in range(k):
        test_idx = perm[fold_starts[i]: fold_starts[i] + fold_sizes[i]]
        train_idx = np.setdiff1d(perm, test_idx, assume_unique=True)
        try:
            beta = _ols_fit(X[train_idx], y[train_idx])
        except np.linalg.LinAlgError:
            # Singular fit on this split — skip but record so the
            # caller can see something went wrong on aggregate
            continue
        y_hat_train = _predict(beta, X[train_idx])
        y_hat_test = _predict(beta, X[test_idx])
        # Train + test R² in FIT space (log if log_transform_target)
        train_r2 = _r2(y[train_idx], y_hat_train)
        test_r2 = _r2(y[test_idx], y_hat_test)
        err = y[test_idx] - y_hat_test
        test_rmse = float(np.sqrt(np.mean(err ** 2)))
        test_mae = float(np.mean(np.abs(err)))
        folds.append(CVFoldResult(
            fold=i,
            n_train=int(len(train_idx)),
            n_test=int(len(test_idx)),
            train_r_squared=train_r2,
            test_r_squared=test_r2,
            test_rmse=test_rmse,
            test_mae=test_mae,
        ))
        train_r2s.append(train_r2)
        test_r2s.append(test_r2)
        test_rmses.append(test_rmse)
        test_maes.append(test_mae)

        # Conformal PI coverage: half-widths are the training-fold
        # |resid| quantile at the nominal level; test-set rows count
        # as "covered" when their |resid| is within that half-width.
        try:
            train_abs = np.abs(y[train_idx] - y_hat_train)
            test_abs = np.abs(err)
            pi_total += int(len(test_abs))
            for lvl in pi_levels:
                half_w = float(np.quantile(train_abs, lvl))
                pi_widths_abs[lvl].append(half_w)
                pi_hits[lvl] += int(np.sum(test_abs <= half_w))
        except Exception:
            # Defensive: if quantile computation fails on a thin
            # fold, skip coverage for that fold rather than blow up.
            pass

    # Baseline in-sample R² for the overfit-gap comparison
    beta_all = _ols_fit(X, y)
    baseline_r2 = _r2(y, _predict(beta_all, X))

    if not folds:
        raise ValueError(
            "every fold failed to fit — features may be perfectly "
            "collinear on every split"
        )

    # Aggregate the conformal PI coverage across folds. Empirical
    # coverage = sum(test rows inside the per-fold PI) / total test
    # rows. Median half-width is the per-fold half-width's median —
    # avoids letting one thin fold dominate.
    pi_coverage: List[Dict[str, float]] = []
    if pi_total > 0:
        for lvl in pi_levels:
            emp = pi_hits[lvl] / pi_total if pi_total else 0.0
            widths = pi_widths_abs[lvl]
            median_w = float(np.median(widths)) if widths else 0.0
            pi_coverage.append({
                "nominal": float(lvl),
                "empirical": float(emp),
                "median_half_width": float(median_w),
            })

    return CVResult(
        target=target,
        features=features,
        k=k,
        target_was_log_transformed=log_transform_target,
        baseline_in_sample_r2=baseline_r2,
        mean_train_r2=float(np.mean(train_r2s)),
        mean_test_r2=float(np.mean(test_r2s)),
        std_test_r2=float(np.std(test_r2s)),
        mean_test_rmse=float(np.mean(test_rmses)),
        mean_test_mae=float(np.mean(test_maes)),
        folds=folds,
        requested_k=requested_k,
        pi_coverage=pi_coverage,
    )
