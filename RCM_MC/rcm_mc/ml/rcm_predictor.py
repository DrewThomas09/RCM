"""Ridge-regression engine that fills in missing RCM metrics.

Given a target hospital with a partial set of metrics plus a list of
comparable hospitals with fuller data, fit a per-metric Ridge model
using the target's known metrics as features and predict every missing
metric.

**Ridge, not sklearn.** The closed-form Ridge solution is one line of
numpy — we avoid a 100MB+ sklearn/scipy dep and keep the stdlib+numpy
invariant intact.

Fallback ladder:

1. ≥10 comparables have the target metric → Ridge fit.
2. 1-9 comparables have it → weighted median (weights from
   ``similarity_score`` on each comparable).
3. Zero comparables have it → None (graceful miss; caller filters).

Every prediction is wrapped in a :class:`DataPoint` so the partner can
trace the number through the provenance UI.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from ..provenance.tracker import DataPoint, Source
from .feature_engineering import derive_features

logger = logging.getLogger(__name__)


# The metric set the predictor knows how to infer. Ordering is stable
# so downstream consumers (UI, API) can iterate deterministically.
RCM_METRICS: List[str] = [
    "denial_rate",
    "clean_claim_rate",
    "days_in_ar",
    "cost_to_collect",
    "net_collection_rate",
    "first_pass_resolution_rate",
    "appeals_overturn_rate",
    "discharged_not_final_billed_days",
    # "denial_rate_by_payer" is a dict, handled separately.
    "denial_rate_by_payer",
    "initial_denial_rate",
    "final_denial_rate",
    "avoidable_denial_pct",
    "coding_denial_rate",
    "auth_denial_rate",
    "eligibility_denial_rate",
    "timely_filing_denial_rate",
    "medical_necessity_denial_rate",
]

# Minimum comparables with the target metric to attempt a Ridge fit;
# below this, fall back to weighted median.
_MIN_FOR_RIDGE = 10

# Ridge regularization strength. 1.0 is the standard numerical-analysis
# default (MacKay 1992) and behaves well when features are z-scored.
_RIDGE_ALPHA = 1.0


@dataclass
class PredictedMetric:
    """Single predicted metric with enough detail for a partner audit.

    Attributes
    ----------
    value
        Point prediction.
    confidence_interval_low / confidence_interval_high
        Approximate 80% CI from residual stddev on the comparable cohort.
        Simple bootstrap-free formula: ``value ± 1.28 · residual_sd``.
    r_squared
        Out-of-sample R² on the Ridge leave-one-out residuals. For
        weighted-median fallbacks this is computed against the comparable
        values (lower by design — a median is conservative).
    n_comparables_used
        How many comparables had this metric non-null.
    feature_importances
        Absolute coefficient magnitudes (on standardized features) for
        the Ridge model. Empty dict for weighted-median fallbacks.
    method
        ``"ridge"`` | ``"weighted_median"`` | ``"peer_mean"`` — so the
        UI can label the number with its provenance method.
    """

    value: float
    confidence_interval_low: float
    confidence_interval_high: float
    r_squared: float
    n_comparables_used: int
    feature_importances: Dict[str, float] = field(default_factory=dict)
    method: str = "ridge"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence_interval_low": self.confidence_interval_low,
            "confidence_interval_high": self.confidence_interval_high,
            "r_squared": self.r_squared,
            "n_comparables_used": self.n_comparables_used,
            "feature_importances": self.feature_importances,
            "method": self.method,
        }


# ────────────────────────────────────────────────────────────────────
# Core helpers
# ────────────────────────────────────────────────────────────────────

def _is_finite_number(v: Any) -> bool:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


def _feature_matrix(
    comparables: List[Dict[str, Any]],
    feature_names: List[str],
    target_metric: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assemble (X, y, weights) for Ridge training.

    Only keeps comparables that have both the target metric AND every
    feature. Rows with missing features are dropped (Ridge has no native
    NaN handling; imputation would introduce a second source of error).
    """
    X_rows: List[List[float]] = []
    y_vals: List[float] = []
    w: List[float] = []
    for peer in comparables:
        y_raw = peer.get(target_metric)
        if not _is_finite_number(y_raw):
            continue
        row: List[float] = []
        ok = True
        for fname in feature_names:
            fv = peer.get(fname)
            if not _is_finite_number(fv):
                ok = False
                break
            row.append(float(fv))
        if not ok:
            continue
        X_rows.append(row)
        y_vals.append(float(y_raw))
        w.append(float(peer.get("similarity_score") or 1.0))
    return (np.asarray(X_rows, dtype=float),
            np.asarray(y_vals, dtype=float),
            np.asarray(w, dtype=float))


_RidgeModel = Tuple[np.ndarray, float, np.ndarray, np.ndarray]


def _ridge_fit_closed_form(
    X: np.ndarray, y: np.ndarray, alpha: float,
) -> _RidgeModel:
    """Ridge closed form on z-scored features with intercept.

    Returns (coefficients, intercept). Features are standardized
    internally; coefficients are returned in the standardized space so
    their magnitudes are directly comparable for feature importance.
    Callers that want to apply to a *raw* feature vector must z-score
    it the same way — use :func:`_ridge_predict` which does that.
    """
    n, p = X.shape
    # Center the target so intercept handling is trivial.
    y_mean = float(y.mean())
    yc = y - y_mean

    # Standardize features (per-column). Guard against zero-variance
    # columns — they'd divide by zero; replace sd with 1.0 so the
    # column contributes 0 via centering (X-mean = 0 for constant cols).
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd_safe = np.where(sd > 1e-12, sd, 1.0)
    Xz = (X - mu) / sd_safe

    # Closed-form Ridge: (X'X + αI)⁻¹ X'y
    A = Xz.T @ Xz + alpha * np.eye(p)
    try:
        W = np.linalg.solve(A, Xz.T @ yc)
    except np.linalg.LinAlgError:
        W = np.linalg.pinv(A) @ (Xz.T @ yc)
    # (coefficients_in_standardized_space, y_mean, feature_mu, feature_sd)
    return W, y_mean, mu, sd_safe


def _ridge_predict(model: _RidgeModel, x_raw: np.ndarray) -> float:
    """Apply a model trained by :func:`_ridge_fit_closed_form`."""
    W, y_mean, mu, sd = model
    xz = (x_raw - mu) / sd
    return float(xz @ W + y_mean)


def _leave_one_out_r2(
    X: np.ndarray, y: np.ndarray, alpha: float,
) -> float:
    """Leave-one-out R² — honest out-of-sample metric.

    Returns 0.0 if cohort is too small (<3) or pathological.
    """
    n = X.shape[0]
    if n < 3:
        return 0.0
    preds = np.zeros(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        try:
            model = _ridge_fit_closed_form(X[mask], y[mask], alpha)
            preds[i] = _ridge_predict(model, X[i])
        except Exception:  # noqa: BLE001
            preds[i] = y.mean()
    ss_res = float(np.sum((y - preds) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 1e-12:
        return 0.0
    return max(0.0, 1.0 - ss_res / ss_tot)


def _weighted_median(
    values: List[float], weights: List[float],
) -> float:
    """Weighted median. Falls back to unweighted when weights sum to 0."""
    pairs = sorted(zip(values, weights), key=lambda p: p[0])
    total = sum(w for _, w in pairs)
    if total <= 0:
        return float(np.median(values))
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= total / 2.0:
            return float(v)
    return float(pairs[-1][0])


# ────────────────────────────────────────────────────────────────────
# Public predictor
# ────────────────────────────────────────────────────────────────────

def _available_features(
    known_metrics: Dict[str, Any],
    comparables: List[Dict[str, Any]],
    exclude: str,
) -> List[str]:
    """Which feature columns are usable for predicting ``exclude``?

    A feature is usable when:
    - the target has it (we need to apply the fitted model)
    - at least half the comparables have it (otherwise the row-drop
      rule destroys the training set)
    """
    if not comparables:
        return []
    n = len(comparables)
    candidate = [
        k for k, v in known_metrics.items()
        if k != exclude and _is_finite_number(v)
    ]
    usable: List[str] = []
    for k in candidate:
        present = sum(1 for p in comparables if _is_finite_number(p.get(k)))
        if present >= max(1, n // 2):
            usable.append(k)
    return usable


def _predict_one(
    target_metric: str,
    known_metrics: Dict[str, Any],
    comparables: List[Dict[str, Any]],
) -> Optional[PredictedMetric]:
    """Predict a single scalar metric. Returns None when no signal."""
    # Pool comparables that have this metric.
    with_metric = [p for p in comparables
                   if _is_finite_number(p.get(target_metric))]
    n_with = len(with_metric)
    if n_with == 0:
        return None

    feature_names = _available_features(
        known_metrics, comparables, exclude=target_metric,
    )

    # Fallback: not enough data to fit Ridge.
    if n_with < _MIN_FOR_RIDGE or not feature_names:
        values = [float(p[target_metric]) for p in with_metric]
        weights = [float(p.get("similarity_score") or 1.0)
                   for p in with_metric]
        val = _weighted_median(values, weights)
        # Rough CI from sample stddev.
        if len(values) >= 2:
            arr = np.asarray(values)
            sd = float(arr.std(ddof=0))
        else:
            sd = 0.0
        # For a median we don't have R² in the normal sense; report
        # (1 - normalized spread) as a proxy so the UI has a number.
        if values and abs(val) > 1e-9:
            r2_proxy = max(0.0, 1.0 - sd / (abs(val) + 1e-9))
        else:
            r2_proxy = 0.0
        return PredictedMetric(
            value=val,
            confidence_interval_low=val - 1.28 * sd,
            confidence_interval_high=val + 1.28 * sd,
            r_squared=r2_proxy,
            n_comparables_used=n_with,
            feature_importances={},
            method=("weighted_median" if n_with > 1 else "peer_mean"),
        )

    # Ridge path.
    X, y, _ = _feature_matrix(with_metric, feature_names, target_metric)
    if X.shape[0] < _MIN_FOR_RIDGE or X.shape[1] == 0:
        # Row-drop dropped us below threshold — retry as weighted median.
        return _predict_one(
            target_metric,
            {k: v for k, v in known_metrics.items() if k in set()},
            comparables,
        )
    model = _ridge_fit_closed_form(X, y, _RIDGE_ALPHA)
    # Target feature vector in the same order as feature_names.
    try:
        x_target = np.asarray(
            [float(known_metrics[f]) for f in feature_names], dtype=float,
        )
    except (KeyError, TypeError, ValueError):
        return None
    pred = _ridge_predict(model, x_target)
    r2 = _leave_one_out_r2(X, y, _RIDGE_ALPHA)

    # Residual-based CI on training fit (not LOO; cheaper and partners
    # read CIs as "how much noise is around this metric in the cohort").
    train_preds = np.array([_ridge_predict(model, row) for row in X])
    residual_sd = float(np.std(y - train_preds, ddof=0))

    W_std, _, _, _ = model
    importances = {
        fname: float(abs(w))
        for fname, w in zip(feature_names, W_std)
    }
    # Normalize so importances sum to 1 (makes the UI a lot cleaner).
    total = sum(importances.values()) or 1.0
    importances = {k: v / total for k, v in importances.items()}

    return PredictedMetric(
        value=float(pred),
        confidence_interval_low=float(pred - 1.28 * residual_sd),
        confidence_interval_high=float(pred + 1.28 * residual_sd),
        r_squared=r2,
        n_comparables_used=int(X.shape[0]),
        feature_importances=importances,
        method="ridge",
    )


def _predict_denial_rate_by_payer(
    known_metrics: Dict[str, Any],
    comparables: List[Dict[str, Any]],
) -> Optional[PredictedMetric]:
    """Dict-valued metric — predict per-payer denial rate.

    Strategy: take the median per-payer denial rate across any
    comparable that has a ``denial_rate_by_payer`` dict. Partners use
    this for payer-mix strategy, so a cohort median beats a fancy
    regression on thin data.
    """
    payer_vals: Dict[str, List[float]] = {}
    count = 0
    for peer in comparables:
        d = peer.get("denial_rate_by_payer")
        if not isinstance(d, dict):
            continue
        count += 1
        for payer, v in d.items():
            if _is_finite_number(v):
                payer_vals.setdefault(str(payer), []).append(float(v))
    if not payer_vals:
        return None
    medians = {p: float(np.median(vs)) for p, vs in payer_vals.items() if vs}
    # Collapse to a single representative number — the weighted overall
    # payer mix of the target, so partners get a usable scalar for the
    # PredictedMetric.value field. Caller can still pull the per-payer
    # dict from feature_importances if they want it.
    payer_mix = known_metrics.get("payer_mix") or {}
    if isinstance(payer_mix, dict) and payer_mix:
        wsum = 0.0
        vsum = 0.0
        for p, frac in payer_mix.items():
            f = float(frac or 0.0)
            if f <= 0 or p not in medians:
                continue
            wsum += f
            vsum += f * medians[p]
        blended = vsum / wsum if wsum > 0 else float(np.mean(list(medians.values())))
    else:
        blended = float(np.mean(list(medians.values())))

    arr = np.concatenate([np.asarray(v) for v in payer_vals.values()])
    sd = float(arr.std(ddof=0)) if arr.size > 1 else 0.0
    return PredictedMetric(
        value=float(blended),
        confidence_interval_low=float(blended - 1.28 * sd),
        confidence_interval_high=float(blended + 1.28 * sd),
        r_squared=0.0,
        n_comparables_used=count,
        feature_importances=medians,
        method="peer_mean",
    )


def predict_missing(
    known_metrics: Dict[str, Any],
    comparables: List[Dict[str, Any]],
    *,
    registry: Any = None,
) -> Dict[str, PredictedMetric]:
    """Predict every metric in :data:`RCM_METRICS` that isn't in
    ``known_metrics``.

    Parameters
    ----------
    known_metrics
        Partial profile. Missing RCM_METRICS entries will be predicted;
        non-RCM keys (like ``bed_count`` or ``payer_mix``) are passed
        through as additional features for the Ridge fit.
    comparables
        List of hospital dicts, typically from :func:`find_comparables`.
        Each should carry ``similarity_score`` and the full metric set.
    registry
        Optional :class:`ProvenanceRegistry` — when passed, every
        prediction is recorded as a ``REGRESSION_PREDICTED`` DataPoint
        with upstream refs to the known metrics that fed the model.

    Returns
    -------
    Dict mapping metric_name → :class:`PredictedMetric`. Metrics with no
    signal (no comparables, all-missing) are omitted from the dict.
    """
    # Fold derived features into known_metrics so Ridge can use them.
    enriched = dict(known_metrics or {})
    enriched.update(derive_features(enriched))
    # Also fold derived features into comparables (once).
    comp_enriched: List[Dict[str, Any]] = []
    for peer in comparables or []:
        p = dict(peer)
        p.update(derive_features(p))
        comp_enriched.append(p)

    # Upstream DataPoints for provenance tagging.
    upstream: List[DataPoint] = []
    if registry is not None:
        for k, v in (known_metrics or {}).items():
            if not _is_finite_number(v):
                continue
            dp = registry.get(k) if k in registry else None
            if dp is None:
                dp = registry.record_user_input(float(v), k)
            upstream.append(dp)

    out: Dict[str, PredictedMetric] = {}
    for metric in RCM_METRICS:
        if metric in known_metrics and _is_finite_number(known_metrics.get(metric)):
            continue
        try:
            if metric == "denial_rate_by_payer":
                pred = _predict_denial_rate_by_payer(enriched, comp_enriched)
            else:
                pred = _predict_one(metric, enriched, comp_enriched)
        except Exception as exc:  # noqa: BLE001
            logger.debug("prediction for %s failed: %s", metric, exc)
            pred = None
        if pred is None:
            continue
        out[metric] = pred

        # Provenance: record as REGRESSION_PREDICTED (or peer_mean for
        # the non-Ridge fallback paths — still provenance-tagged).
        if registry is not None:
            try:
                n = max(1, pred.n_comparables_used)
                registry.record_regression(
                    value=pred.value,
                    metric_name=metric,
                    upstream=upstream,
                    r_squared=pred.r_squared,
                    n_samples=n,
                    predictor_summary=pred.method,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("provenance record_regression failed: %s", exc)

    return out
