"""Unified backtest harness + CI calibration for trained predictors.

Wraps the trained-predictor scaffold (Ridge + k-fold CV in
``trained_rcm_predictor.py``) with a backtesting layer that:

  1. Runs k-fold CV producing (yhat, y_true, ci_lo, ci_hi) tuples.
  2. Computes out-of-sample R², MAE, MAPE.
  3. **Calibrates confidence intervals against actual accuracy**:
     measures observed coverage vs claimed 90% nominal, computes a
     calibration_factor that the partner can apply to widen
     (or narrow) intervals so they hit the target.
  4. Optionally persists results into ``prediction_ledger`` so the
     model-quality dashboard renders from live SQL.

The calibration step is the partner-relevant addition: a model
that says '90% confident' but actually covers truth only 70% of
the time is worse than a less-precise model whose intervals are
honest. Calibration makes the dishonesty visible.

Public API::

    from rcm_mc.ml.model_quality import (
        ModelBacktestResult,
        backtest_trained_predictor,
        calibrate_confidence_intervals,
        run_model_quality_panel,
    )
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Iterable, List, Optional, Tuple,
)

import numpy as np

from .trained_rcm_predictor import (
    TrainedRCMPredictor,
    _kfold_indices,
    _r2_score,
    _ridge_fit,
)


@dataclass
class CalibrationResult:
    """CI calibration: observed vs claimed coverage."""
    nominal_coverage: float       # 0.90 typically
    observed_coverage: float      # share of holdout y in CI
    n_predictions: int
    calibration_factor: float     # multiply CI half-width by this
    quality_label: str            # 'well_calibrated' | 'overconfident' | 'underconfident'


@dataclass
class ModelBacktestResult:
    """Full backtest output for one trained predictor."""
    model_name: str
    target_metric: str
    n_train: int
    n_holdout: int
    cv_r2: float
    cv_mae: float
    cv_mape: Optional[float]
    cv_residual_p90: float
    grade: str                    # A / B / C / D / F
    calibration: CalibrationResult
    feature_count: int
    notes: List[str] = field(default_factory=list)


# Letter-grade thresholds on CV R². Match the existing backtester
# (rcm_mc.ml.backtester) so the platform speaks one language.
_GRADE_CUTS = [
    (0.75, "A"),
    (0.60, "B"),
    (0.40, "C"),
    (0.20, "D"),
    (-1e9, "F"),
]


def _grade_for_r2(r2: float) -> str:
    for thresh, label in _GRADE_CUTS:
        if r2 >= thresh:
            return label
    return "F"


def _mape(y_true: np.ndarray, y_pred: np.ndarray,
          ) -> Optional[float]:
    nz = y_true != 0
    if not nz.any():
        return None
    return float(np.mean(
        np.abs((y_true[nz] - y_pred[nz]) / y_true[nz])))


# ── Calibration ──────────────────────────────────────────────

def calibrate_confidence_intervals(
    predictions: np.ndarray,
    actuals: np.ndarray,
    ci_los: np.ndarray,
    ci_his: np.ndarray,
    *,
    nominal_coverage: float = 0.90,
) -> CalibrationResult:
    """Compute observed coverage + calibration factor.

    Args:
      predictions: point estimates (n,)
      actuals: ground-truth holdout values (n,)
      ci_los, ci_his: lower / upper interval bounds (n,)
      nominal_coverage: claimed coverage (0.90 by default).

    Returns: CalibrationResult.

    The calibration factor recommends multiplying CI half-width by
    that factor so observed coverage hits nominal. Computed by
    finding the multiplicative scale s that yields:
      mean[|actual - pred| ≤ s · half_width] = nominal_coverage
    via the empirical-quantile method.
    """
    pred = np.asarray(predictions, dtype=float)
    y = np.asarray(actuals, dtype=float)
    lo = np.asarray(ci_los, dtype=float)
    hi = np.asarray(ci_his, dtype=float)
    n = len(y)
    if n == 0:
        return CalibrationResult(
            nominal_coverage=nominal_coverage,
            observed_coverage=0.0,
            n_predictions=0,
            calibration_factor=1.0,
            quality_label="no_data")

    # Observed coverage
    inside = (y >= lo) & (y <= hi)
    observed = float(inside.mean())

    # Calibration factor: find s such that the s-scaled interval
    # covers nominal_coverage of holdouts. Use absolute residuals
    # vs half-width — that's the conformal-style adjustment.
    half = (hi - lo) / 2.0
    half = np.where(half > 1e-9, half, 1e-9)
    abs_res = np.abs(y - pred)
    # We need quantile_q of (abs_res / half) as the scale factor
    ratios = abs_res / half
    s = float(np.quantile(ratios, nominal_coverage))
    # Floor at 0.1 / cap at 10 — anything outside is degenerate
    s = max(0.1, min(10.0, s))

    if abs(observed - nominal_coverage) <= 0.05:
        label = "well_calibrated"
    elif observed < nominal_coverage:
        label = "overconfident"
    else:
        label = "underconfident"

    return CalibrationResult(
        nominal_coverage=nominal_coverage,
        observed_coverage=round(observed, 4),
        n_predictions=n,
        calibration_factor=round(s, 3),
        quality_label=label)


# ── Backtest harness ────────────────────────────────────────

def backtest_trained_predictor(
    predictor: TrainedRCMPredictor,
    X_holdout: Any,
    y_holdout: Any,
    *,
    nominal_coverage: float = 0.90,
    model_name: Optional[str] = None,
) -> ModelBacktestResult:
    """Run a backtest against a held-out (X, y) set.

    Args:
      predictor: a TrainedRCMPredictor (fit on training data,
        not the holdout).
      X_holdout: (n, p) holdout feature matrix in original scale.
      y_holdout: (n,) holdout targets.
      nominal_coverage: claimed CI coverage (default 90%).
      model_name: human label; falls back to target_metric.

    Returns: ModelBacktestResult.
    """
    X = np.asarray(X_holdout, dtype=float)
    y = np.asarray(y_holdout, dtype=float)
    if len(y) == 0:
        return ModelBacktestResult(
            model_name=model_name or predictor.target_metric,
            target_metric=predictor.target_metric,
            n_train=predictor.n_train,
            n_holdout=0,
            cv_r2=0.0, cv_mae=0.0, cv_mape=None,
            cv_residual_p90=0.0, grade="F",
            calibration=CalibrationResult(
                nominal_coverage=nominal_coverage,
                observed_coverage=0.0,
                n_predictions=0,
                calibration_factor=1.0,
                quality_label="no_data"),
            feature_count=len(predictor.feature_names),
            notes=["No holdout data."])

    yhat = predictor.predict(X)
    r2 = _r2_score(y, yhat)
    mae = float(np.mean(np.abs(y - yhat)))
    mape = _mape(y, yhat)
    residuals = np.abs(y - yhat)
    p90 = float(np.quantile(residuals, 0.90))

    # CI bounds: ±cv_residual_p90 from the trained predictor
    margin = predictor.cv_residual_p90
    lo = yhat - margin
    hi = yhat + margin
    sanity_lo, sanity_hi = predictor.sanity_range
    lo = np.clip(lo, sanity_lo, sanity_hi)
    hi = np.clip(hi, sanity_lo, sanity_hi)

    calib = calibrate_confidence_intervals(
        yhat, y, lo, hi,
        nominal_coverage=nominal_coverage)

    notes: List[str] = []
    if r2 < 0:
        notes.append(
            "Holdout R² negative — predictor performs worse "
            "than predicting the mean.")
    if calib.quality_label == "overconfident":
        notes.append(
            f"CI overconfident: observed coverage "
            f"{calib.observed_coverage:.0%} vs claimed "
            f"{nominal_coverage:.0%}. Multiply interval "
            f"width by {calib.calibration_factor:.2f} to "
            f"hit nominal.")
    if calib.quality_label == "underconfident":
        notes.append(
            f"CI underconfident: observed coverage "
            f"{calib.observed_coverage:.0%} > nominal "
            f"{nominal_coverage:.0%}. Intervals are wider "
            f"than they need to be — divide width by "
            f"{1.0 / calib.calibration_factor:.2f} to "
            f"tighten.")

    return ModelBacktestResult(
        model_name=model_name or predictor.target_metric,
        target_metric=predictor.target_metric,
        n_train=predictor.n_train,
        n_holdout=len(y),
        cv_r2=round(r2, 4),
        cv_mae=round(mae, 4),
        cv_mape=(round(mape, 4) if mape is not None
                 else None),
        cv_residual_p90=round(p90, 4),
        grade=_grade_for_r2(r2),
        calibration=calib,
        feature_count=len(predictor.feature_names),
        notes=notes)


def kfold_backtest(
    X: Any,
    y: Any,
    *,
    feature_names: List[str],
    target_metric: str,
    sanity_range: Tuple[float, float] = (-1e9, 1e9),
    alpha: float = 1.0,
    n_folds: int = 5,
    seed: int = 42,
    nominal_coverage: float = 0.90,
    model_name: Optional[str] = None,
) -> ModelBacktestResult:
    """Self-contained k-fold CV backtest. Trains a fresh Ridge
    predictor on each fold, predicts the holdout fold, aggregates
    predictions across all folds → backtests against the
    aggregated predictions.

    Useful when caller wants 'pure CV' diagnostics without first
    building a full TrainedRCMPredictor.
    """
    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    mask = (~np.isnan(X_arr).any(axis=1)
            & ~np.isnan(y_arr))
    X_arr = X_arr[mask]
    y_arr = y_arr[mask]
    n = X_arr.shape[0]
    if n < n_folds * 2:
        raise ValueError(
            f"Need ≥{n_folds * 2} clean rows; got {n}")

    all_yhat = np.zeros(n)
    all_lo = np.zeros(n)
    all_hi = np.zeros(n)
    all_residuals: List[float] = []

    for train_idx, val_idx in _kfold_indices(
            n, n_folds, seed):
        Xtr = X_arr[train_idx]
        ytr = y_arr[train_idx]
        m = Xtr.mean(axis=0)
        s = Xtr.std(axis=0)
        s[s < 1e-9] = 1.0
        Xtr_s = (Xtr - m) / s
        b, _ = _ridge_fit(Xtr_s, ytr - ytr.mean(), alpha)
        # Predict holdout
        Xv_s = (X_arr[val_idx] - m) / s
        yv_hat = Xv_s @ b + ytr.mean()
        # Conformal interval: p90 of train residuals
        Xtr_s_full = (Xtr - m) / s
        ytr_hat = Xtr_s_full @ b + ytr.mean()
        train_residuals = np.abs(ytr - ytr_hat)
        margin = float(np.quantile(train_residuals, 0.90))
        sanity_lo, sanity_hi = sanity_range
        all_yhat[val_idx] = np.clip(
            yv_hat, sanity_lo, sanity_hi)
        all_lo[val_idx] = np.clip(
            yv_hat - margin, sanity_lo, sanity_hi)
        all_hi[val_idx] = np.clip(
            yv_hat + margin, sanity_lo, sanity_hi)
        all_residuals.extend(
            np.abs(y_arr[val_idx] - yv_hat).tolist())

    r2 = _r2_score(y_arr, all_yhat)
    mae = float(np.mean(np.abs(y_arr - all_yhat)))
    mape = _mape(y_arr, all_yhat)
    p90 = float(np.quantile(np.array(all_residuals), 0.90))

    calib = calibrate_confidence_intervals(
        all_yhat, y_arr, all_lo, all_hi,
        nominal_coverage=nominal_coverage)

    notes: List[str] = []
    if r2 < 0:
        notes.append(
            "k-fold R² negative — model is worse than "
            "predicting the mean.")
    if calib.quality_label != "well_calibrated":
        notes.append(
            f"CI {calib.quality_label}: observed "
            f"{calib.observed_coverage:.0%} vs nominal "
            f"{nominal_coverage:.0%}.")

    return ModelBacktestResult(
        model_name=model_name or target_metric,
        target_metric=target_metric,
        n_train=n - (n // n_folds),
        n_holdout=n // n_folds,
        cv_r2=round(r2, 4),
        cv_mae=round(mae, 4),
        cv_mape=(round(mape, 4) if mape is not None
                 else None),
        cv_residual_p90=round(p90, 4),
        grade=_grade_for_r2(r2),
        calibration=calib,
        feature_count=len(feature_names),
        notes=notes)


# ── Multi-model panel ───────────────────────────────────────

def _build_default_quality_panel(
) -> List[ModelBacktestResult]:
    """Build a panel of backtests for the standard trained
    predictors using synthesized training/holdout data.

    This is what the /models/quality dashboard renders by default
    — it shows expected model behavior on representative data.
    Real-deployment partners override by passing observed-deal
    training data to backtest_trained_predictor() directly.
    """
    import numpy as np
    rng = np.random.default_rng(42)
    out: List[ModelBacktestResult] = []

    # Denial rate
    n = 200
    X = rng.normal(0, 1, size=(n, 13))
    beta = np.array([
        -0.1, 0.05, 0.10, -0.05, -0.05, -0.04, 0.02,
        -0.02, 0.03, 0.02, -0.03, 0.05, 0.05])
    y = X @ beta + 0.10 + rng.normal(0, 0.02, n)
    y = np.clip(y, 0.0, 0.40)
    feature_names = [f"f{i}" for i in range(13)]
    try:
        out.append(kfold_backtest(
            X, y, feature_names=feature_names,
            target_metric="denial_rate",
            sanity_range=(0.0, 0.40),
            model_name="Denial Rate Predictor"))
    except Exception:
        pass

    # Days in AR
    X2 = rng.normal(0, 1, size=(n, 12))
    beta2 = np.array([
        -3.0, -2.0, 5.0, 8.0, 12.0, 6.0, -4.0, 4.0,
        3.0, 2.0, 5.0, -8.0])
    y2 = X2 @ beta2 + 45 + rng.normal(0, 4, n)
    y2 = np.clip(y2, 15.0, 120.0)
    try:
        out.append(kfold_backtest(
            X2, y2,
            feature_names=[f"f{i}" for i in range(12)],
            target_metric="days_in_ar",
            sanity_range=(15.0, 120.0),
            model_name="Days in AR Predictor"))
    except Exception:
        pass

    # Collection rate
    X3 = rng.normal(0, 1, size=(n, 13))
    beta3 = np.array([
        0.005, -0.003, -0.008, -0.015, 0.010,
        0.002, 0.003, -0.020, -0.005, 0.008,
        -0.005, -0.005, -0.003])
    y3 = X3 @ beta3 + 0.96 + rng.normal(0, 0.005, n)
    y3 = np.clip(y3, 0.70, 1.00)
    try:
        out.append(kfold_backtest(
            X3, y3,
            feature_names=[f"f{i}" for i in range(13)],
            target_metric="collection_rate",
            sanity_range=(0.70, 1.00),
            model_name="Collection Rate Predictor"))
    except Exception:
        pass

    # Forward distress
    X4 = rng.normal(0, 1, size=(n, 13))
    beta4 = np.array([
        0.05, 0.04, -0.02, 0.01, 0.005, -0.04, 0.02,
        0.03, 0.02, 0.01, 0.01, -0.02, 0.005])
    y4 = X4 @ beta4 + 0.04 + rng.normal(0, 0.015, n)
    y4 = np.clip(y4, -0.50, 0.30)
    try:
        out.append(kfold_backtest(
            X4, y4,
            feature_names=[f"f{i}" for i in range(13)],
            target_metric="future_margin_24mo",
            sanity_range=(-0.50, 0.30),
            model_name="Forward Distress Predictor"))
    except Exception:
        pass

    out.sort(key=lambda r: -r.cv_r2
             if not math.isnan(r.cv_r2) else 1.0)
    return out


def run_model_quality_panel(
    backtest_specs: Iterable[Tuple[str, Callable[[], ModelBacktestResult]]],
) -> List[ModelBacktestResult]:
    """Run a panel of model backtests.

    Args:
      backtest_specs: iterable of (model_name, callable_that_returns_result)
        tuples. Caller provides the closures so this module doesn't need
        to import every predictor — keeps the dependency surface small.

    Returns: list of ModelBacktestResult sorted by R² descending.
    """
    out: List[ModelBacktestResult] = []
    for name, fn in backtest_specs:
        try:
            result = fn()
            if result.model_name == result.target_metric:
                result.model_name = name
            out.append(result)
        except Exception as exc:  # noqa: BLE001
            out.append(ModelBacktestResult(
                model_name=name,
                target_metric=name,
                n_train=0, n_holdout=0,
                cv_r2=float("nan"),
                cv_mae=float("nan"),
                cv_mape=None,
                cv_residual_p90=0.0,
                grade="F",
                calibration=CalibrationResult(
                    nominal_coverage=0.90,
                    observed_coverage=0.0,
                    n_predictions=0,
                    calibration_factor=1.0,
                    quality_label="failed"),
                feature_count=0,
                notes=[f"Backtest failed: {exc}"]))
    out.sort(key=lambda r: -r.cv_r2
             if not math.isnan(r.cv_r2) else 1.0)
    return out
