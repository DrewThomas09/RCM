"""Auto-selecting ensemble predictor for per-metric inference.

Ridge regression is the default for RCM metric prediction, and it's
the right call for the bulk of RCM relationships (denial_rate vs
bed_count vs payer mix — nearly linear once you z-score). But a
handful of metrics — CMI, case-rate-bundled revenue — are nonlinear
enough that Ridge misses systematically. The ensemble adds two
alternative base models:

- **k-NN** with similarity-weighted averaging. K picked by
  leave-one-out cross-validation over ``{3, 5, 10, 15}``.
- **Weighted median** — the Prompt 4 fallback path we already ship.

The :class:`EnsemblePredictor` fits all three on a train split,
scores them on a held-out calibration split using MAE, and picks
the lowest. The chosen model is tagged on the returned
:class:`PredictedMetric` so partners can see *why* one metric came
from Ridge and another from k-NN. Conformal intervals sit on top of
whichever base model won — the ``ConformalPredictor`` wrapper doesn't
care which estimator it's wrapping.

Numpy only; no scikit-learn.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .conformal import ConformalPredictor
from .ridge_predictor import _RidgeModel, _RIDGE_ALPHA
from .ridge_predictor import PredictedMetric as _LocalPredictedMetric

logger = logging.getLogger(__name__)


# ── Base models ────────────────────────────────────────────────────

class _KNNModel:
    """Similarity-weighted k-Nearest-Neighbors regressor.

    At fit time we store the training (X, y) pairs + pick K via LOO
    CV. At predict time we z-score the query against the training
    distribution, compute Euclidean distances to every training row,
    pick the K smallest, and return the weighted mean (weights =
    ``1 / (d + eps)``).

    This is a cheap "smooth memoriser" — good for the non-linear
    tails where Ridge over-regularizes. Not a general KNN library;
    callers shouldn't rely on scikit-learn semantics.
    """

    def __init__(self, k: Optional[int] = None,
                 candidate_ks: Tuple[int, ...] = (3, 5, 10, 15)) -> None:
        self.k = int(k) if k is not None else 0
        self._candidate_ks = tuple(candidate_ks)
        self._X: np.ndarray = np.asarray([])
        self._y: np.ndarray = np.asarray([])
        self._mu: np.ndarray = np.asarray([])
        self._sd: np.ndarray = np.asarray([])

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_KNNModel":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        self._X = X
        self._y = y
        if X.shape[0] == 0:
            self._mu = np.zeros(X.shape[1] if X.ndim == 2 else 0)
            self._sd = np.ones(X.shape[1] if X.ndim == 2 else 0)
            return self
        self._mu = X.mean(axis=0)
        sd = X.std(axis=0)
        self._sd = np.where(sd > 1e-12, sd, 1.0)
        if self.k == 0:
            self.k = self._select_k_via_loo(X, y)
        return self

    def _select_k_via_loo(
        self, X: np.ndarray, y: np.ndarray,
    ) -> int:
        n = X.shape[0]
        if n < 4:
            return 1 if n == 0 else min(n, self._candidate_ks[0])
        # Precompute z-scored X.
        Xz = (X - self._mu) / self._sd
        # All pairwise distances.
        diff = Xz[:, None, :] - Xz[None, :, :]
        d = np.sqrt(np.sum(diff * diff, axis=2))
        # Leave-one-out: mask diagonal with +inf.
        np.fill_diagonal(d, np.inf)
        best_k = self._candidate_ks[0]
        best_mae = float("inf")
        for k in self._candidate_ks:
            k_eff = min(k, n - 1)
            if k_eff < 1:
                continue
            # For each i, pick the k_eff nearest neighbors.
            # Partial sort via argpartition.
            idxs = np.argpartition(d, kth=k_eff - 1, axis=1)[:, :k_eff]
            # Weighted mean of neighbor y values.
            preds = np.zeros(n)
            eps = 1e-9
            for i in range(n):
                nbr = idxs[i]
                dists = d[i, nbr]
                w = 1.0 / (dists + eps)
                preds[i] = float(np.sum(w * y[nbr]) / np.sum(w))
            mae = float(np.mean(np.abs(preds - y)))
            if mae < best_mae:
                best_mae = mae
                best_k = k_eff
        return int(best_k)

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if self._X.shape[0] == 0 or self.k < 1:
            return np.zeros(X.shape[0])
        Xz_train = (self._X - self._mu) / self._sd
        Xz_query = (X - self._mu) / self._sd
        out = np.zeros(X.shape[0])
        eps = 1e-9
        for i, q in enumerate(Xz_query):
            dists = np.sqrt(np.sum((Xz_train - q) ** 2, axis=1))
            k_eff = min(self.k, self._X.shape[0])
            idx = np.argpartition(dists, k_eff - 1)[:k_eff]
            ds = dists[idx]
            w = 1.0 / (ds + eps)
            out[i] = float(np.sum(w * self._y[idx]) / np.sum(w))
        return out


class _WeightedMedianModel:
    """The cohort's similarity-weighted median of the target.

    This is the "when there's no signal, report the middle" fallback
    the original predictor already used. Restated here as a proper
    ``fit/predict`` estimator so the ensemble can score it alongside
    the other two.
    """

    def __init__(self) -> None:
        self._median: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray,
            weights: Optional[np.ndarray] = None) -> "_WeightedMedianModel":
        y = np.asarray(y, dtype=float)
        if len(y) == 0:
            self._median = 0.0
            return self
        if weights is None:
            weights = np.ones_like(y)
        w = np.asarray(weights, dtype=float)
        # Weighted median.
        order = np.argsort(y)
        sorted_y = y[order]
        sorted_w = w[order]
        cum = np.cumsum(sorted_w)
        half = cum[-1] / 2.0
        idx = int(np.searchsorted(cum, half))
        idx = min(idx, len(sorted_y) - 1)
        self._median = float(sorted_y[idx])
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        n = 1 if X.ndim == 1 else X.shape[0]
        return np.full(n, self._median, dtype=float)


# ── Selection metadata ────────────────────────────────────────────

@dataclass
class ModelSelection:
    """Which base model won + the MAE scores that drove the choice."""
    chosen_model: str = "ridge"
    ridge_mae: float = float("inf")
    knn_mae: float = float("inf")
    median_mae: float = float("inf")
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        def _f(v: float) -> Optional[float]:
            return None if (v == float("inf") or math.isnan(v)) else float(v)
        return {
            "chosen_model": self.chosen_model,
            "ridge_mae": _f(self.ridge_mae),
            "knn_mae": _f(self.knn_mae),
            "median_mae": _f(self.median_mae),
            "reason": self.reason,
        }


# ── Ensemble orchestrator ─────────────────────────────────────────

class EnsemblePredictor:
    """Fit + auto-select among Ridge / k-NN / weighted-median.

    Usage::

        ep = EnsemblePredictor(coverage=0.90)
        sel = ep.fit_and_select(X_train, y_train, X_cal, y_cal)
        pred, lo, hi = ep.predict_with_interval(x_new)

    ``fit_and_select`` scores each base model's MAE on the cal split
    and picks the lowest. The conformal wrapper is fitted on top of
    the winning model so intervals reflect the chosen estimator's
    residuals.
    """

    def __init__(self, *, coverage: float = 0.90,
                 alpha: float = _RIDGE_ALPHA) -> None:
        self.coverage = float(coverage)
        self.alpha = float(alpha)
        self._ridge = _RidgeModel(alpha=alpha)
        self._knn = _KNNModel()
        self._median = _WeightedMedianModel()
        self._chosen: Optional[Any] = None
        self._chosen_name: str = "ridge_regression"
        self._conformal: Optional[ConformalPredictor] = None

    def fit_and_select(
        self,
        X_train: np.ndarray, y_train: np.ndarray,
        X_cal: np.ndarray, y_cal: np.ndarray,
    ) -> ModelSelection:
        X_tr = np.asarray(X_train, dtype=float)
        y_tr = np.asarray(y_train, dtype=float)
        X_cal_a = np.asarray(X_cal, dtype=float)
        y_cal_a = np.asarray(y_cal, dtype=float)
        if X_tr.ndim == 1:
            X_tr = X_tr.reshape(-1, 1)
        if X_cal_a.ndim == 1:
            X_cal_a = X_cal_a.reshape(-1, 1)

        # Fit all three on train.
        self._ridge.fit(X_tr, y_tr)
        self._knn.fit(X_tr, y_tr)
        self._median.fit(X_tr, y_tr)

        def _mae(model) -> float:
            try:
                preds = model.predict(X_cal_a)
                if len(preds) == 0:
                    return float("inf")
                return float(np.mean(np.abs(preds - y_cal_a)))
            except Exception as exc:  # noqa: BLE001
                logger.debug("MAE calc failed: %s", exc)
                return float("inf")

        ridge_mae = _mae(self._ridge)
        knn_mae = _mae(self._knn)
        median_mae = _mae(self._median)

        # Prefer Ridge on ties — preserves the prior default behavior
        # when partners have accepted Ridge numbers in earlier IC runs.
        candidates = [
            ("ridge_regression", ridge_mae, self._ridge),
            ("knn", knn_mae, self._knn),
            ("weighted_median", median_mae, self._median),
        ]
        best_name, best_mae, best_model = min(
            candidates, key=lambda t: (t[1], 0 if t[0] == "ridge_regression" else 1),
        )
        self._chosen = best_model
        self._chosen_name = best_name

        # Fit conformal on the chosen model so the CI reflects its
        # residuals. The conformal wrapper refits the base internally,
        # so re-using our already-fit instance is fine.
        try:
            self._conformal = ConformalPredictor(
                self._chosen, coverage=self.coverage,
            )
            self._conformal.fit(X_tr, y_tr, X_cal_a, y_cal_a)
        except Exception as exc:  # noqa: BLE001
            logger.debug("conformal fit failed on %s: %s", best_name, exc)
            self._conformal = None

        lift_pct = 0.0
        baseline = ridge_mae if ridge_mae != float("inf") else 0.0
        if baseline > 0 and best_mae != float("inf"):
            lift_pct = (baseline - best_mae) / baseline * 100.0
        reason = (
            f"chose {best_name} (MAE={best_mae:.4f}) vs ridge={ridge_mae:.4f} "
            f"/ knn={knn_mae:.4f} / median={median_mae:.4f}; "
            f"{lift_pct:+.1f}% vs ridge baseline."
        )
        return ModelSelection(
            chosen_model=best_name,
            ridge_mae=float(ridge_mae),
            knn_mae=float(knn_mae),
            median_mae=float(median_mae),
            reason=reason,
        )

    @property
    def chosen_name(self) -> str:
        return self._chosen_name

    def predict_with_interval(
        self, X: np.ndarray,
    ) -> Tuple[float, float, float]:
        """Point + interval for a single query row. Returns
        ``(value, ci_low, ci_high)``.

        Falls back to a zero-width interval when the conformal fit
        failed during ``fit_and_select`` — callers can still use the
        point prediction but should note the reliability band in
        their downstream logic.
        """
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if self._conformal is not None:
            point, lo, hi = self._conformal.predict_interval(X)
            return float(point[0]), float(lo[0]), float(hi[0])
        if self._chosen is None:
            return 0.0, 0.0, 0.0
        point = float(self._chosen.predict(X)[0])
        return point, point, point


# ── High-level predictor entry ────────────────────────────────────

_MIN_FOR_ENSEMBLE = 15


def predict_metric_ensemble(
    target: str,
    known: Dict[str, Any],
    comparables: List[Dict[str, Any]],
    *,
    coverage: float = 0.90,
    seed: int = 42,
) -> Optional[_LocalPredictedMetric]:
    """Fit an ensemble on the comparable cohort and predict ``target``.

    Mirrors :func:`rcm_mc.ml.ridge_predictor._predict_ridge`'s shape
    so the builder can swap the two at the cohort-size boundary
    without further plumbing. Returns ``None`` when the cohort is
    too thin (< ``_MIN_FOR_ENSEMBLE`` peers) or when the feature
    matrix is degenerate.
    """
    from .ridge_predictor import (
        _assemble_xy, _feature_keys, _grade, _is_finite_number,
        _loo_r_squared, _RIDGE_ALPHA,
    )
    from .conformal import split_train_calibration

    features = _feature_keys(known, comparables, exclude=target)
    if not features:
        return None
    peers = [p for p in comparables if _is_finite_number(p.get(target))]
    X, y, _ = _assemble_xy(peers, features, target)
    if X.shape[0] < _MIN_FOR_ENSEMBLE or X.shape[1] == 0:
        return None
    X_tr, y_tr, X_cal, y_cal = split_train_calibration(
        X, y, cal_fraction=0.30, random_state=seed,
    )
    if len(X_tr) < 3 or len(X_cal) < 1:
        return None

    ep = EnsemblePredictor(coverage=coverage, alpha=_RIDGE_ALPHA)
    try:
        selection = ep.fit_and_select(X_tr, y_tr, X_cal, y_cal)
    except Exception as exc:  # noqa: BLE001
        logger.debug("ensemble fit failed on %s: %s", target, exc)
        return None

    try:
        x_target = np.asarray(
            [float(known[f]) for f in features], dtype=float,
        )
    except (KeyError, TypeError, ValueError):
        return None
    value, lo, hi = ep.predict_with_interval(x_target)

    # LOO R² on the *full* set for the partner-facing "fit quality"
    # number. We still use Ridge's R² here because the metric is
    # model-agnostic (variance explained) — partners read it as a
    # generic fit signal regardless of the chosen estimator.
    r2 = _loo_r_squared(X, y, _RIDGE_ALPHA)

    feature_importances: Dict[str, float] = {}
    if selection.chosen_model == "ridge_regression":
        coefs = np.asarray(getattr(ep._ridge, "coef_", np.zeros(len(features))),
                           dtype=float)
        abs_c = np.abs(coefs)
        total = float(abs_c.sum()) or 1.0
        feature_importances = {
            f: float(abs_c[i] / total) for i, f in enumerate(features)
        }

    pred = _LocalPredictedMetric(
        value=float(value),
        method=selection.chosen_model,
        ci_low=float(lo),
        ci_high=float(hi),
        coverage_target=float(coverage),
        n_comparables_used=int(X.shape[0]),
        r_squared=float(r2),
        feature_importances=feature_importances,
        reliability_grade=_grade(
            # Mapping for the grader: k-NN / weighted-median are both
            # cohort-size-weighted, ridge has a stricter R² band.
            selection.chosen_model if selection.chosen_model == "ridge_regression"
            else "weighted_median",
            int(X.shape[0]), r2,
        ),
    )
    # Stash the ensemble selection name on the returned object via an
    # ad-hoc attribute; the builder picks it up when converting to the
    # packet's ``PredictedMetric``.
    pred.__dict__["_model_selection"] = selection.chosen_model
    return pred
