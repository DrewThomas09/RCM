"""Conformal-calibrated Ridge predictor with a size-gated fallback ladder.

Three branches, picked by how many comparable hospitals carry the target
metric:

- ``>= _MIN_FOR_RIDGE`` (15)  — Ridge + split conformal. Best accuracy,
  honest 90% intervals.
- ``>= _MIN_FOR_MEDIAN`` (5)  — similarity-weighted median + bootstrap
  CI. No feature leverage, but still beats a benchmark fallback when
  there's any signal.
- ``< 5``                      — benchmark P25 / P50 / P75 fallback. No
  hospital-specific information; we flag it ``LOW_CONFIDENCE``.

Why two Ridge modules (this one + :mod:`rcm_mc.ml.rcm_predictor`):
- ``rcm_predictor.py`` is the original Phase-1 predictor and stays the
  default inside :mod:`~rcm_mc.ml` for legacy callers (``backtester``
  and the CLI still import from it).
- This module is the conformal-prediction layer the Deal Analysis Packet
  uses going forward. It returns richer ``PredictedMetric`` rows
  (coverage target, reliability grade, conformal interval) than the
  original.

Both use the same closed-form numpy Ridge — no sklearn. The project's
dependency stance is "numpy + pandas + matplotlib, nothing else."
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .conformal import (
    ConformalPredictor,
    bootstrap_interval,
    percentile_interval,
    split_train_calibration,
)
from .feature_engineering import (
    _safe_float,
    derive_interaction_features,
)

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────

_MIN_FOR_RIDGE = 15
_MIN_FOR_MEDIAN = 5
_RIDGE_ALPHA = 1.0
_DEFAULT_COVERAGE = 0.90


# ── PredictedMetric (ridge-flavor) ───────────────────────────────────

@dataclass
class PredictedMetric:
    """One metric prediction with enough audit detail for IC review.

    Differs from :class:`rcm_mc.ml.rcm_predictor.PredictedMetric` by
    carrying a conformal coverage target + a letter reliability grade.
    """
    value: float
    method: str = "ridge_regression"   # ridge_regression | weighted_median | benchmark_fallback
    ci_low: float = 0.0
    ci_high: float = 0.0
    coverage_target: float = _DEFAULT_COVERAGE
    n_comparables_used: int = 0
    r_squared: float = 0.0
    feature_importances: Dict[str, float] = field(default_factory=dict)
    reliability_grade: str = "D"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Ridge core (closed-form, numpy) ──────────────────────────────────

class _RidgeModel:
    """Minimal Ridge estimator with a sklearn-ish fit/predict surface.

    z-scores features internally so importances are comparable across
    columns. Not threadsafe — callers own their own instance.
    """

    def __init__(self, alpha: float = _RIDGE_ALPHA) -> None:
        self.alpha = float(alpha)
        self.coef_: np.ndarray = np.asarray([])
        self.intercept_: float = 0.0
        self.feature_mu_: np.ndarray = np.asarray([])
        self.feature_sd_: np.ndarray = np.asarray([])

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_RidgeModel":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.shape[0] == 0 or X.shape[1] == 0:
            # No data — degenerate to a constant.
            self.coef_ = np.zeros(X.shape[1] if X.ndim == 2 else 0)
            self.intercept_ = float(y.mean()) if len(y) else 0.0
            self.feature_mu_ = np.zeros(self.coef_.shape[0])
            self.feature_sd_ = np.ones(self.coef_.shape[0])
            return self
        mu = X.mean(axis=0)
        sd = X.std(axis=0)
        sd_safe = np.where(sd > 1e-12, sd, 1.0)
        Xz = (X - mu) / sd_safe
        y_mean = float(y.mean())
        yc = y - y_mean
        A = Xz.T @ Xz + self.alpha * np.eye(Xz.shape[1])
        try:
            w = np.linalg.solve(A, Xz.T @ yc)
        except np.linalg.LinAlgError:
            w = np.linalg.pinv(A) @ (Xz.T @ yc)
        self.coef_ = w
        self.intercept_ = y_mean
        self.feature_mu_ = mu
        self.feature_sd_ = sd_safe
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        Xz = (X - self.feature_mu_) / self.feature_sd_
        return Xz @ self.coef_ + self.intercept_


def _loo_r_squared(X: np.ndarray, y: np.ndarray, alpha: float) -> float:
    """Leave-one-out R² — honest out-of-sample score. Returns 0 on <3."""
    n = X.shape[0]
    if n < 3:
        return 0.0
    preds = np.zeros(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        try:
            m = _RidgeModel(alpha=alpha).fit(X[mask], y[mask])
            preds[i] = m.predict(X[i])[0]
        except Exception:  # noqa: BLE001
            preds[i] = float(y.mean())
    ss_res = float(np.sum((y - preds) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 1e-12:
        return 0.0
    return max(0.0, 1.0 - ss_res / ss_tot)


# ── Helpers ──────────────────────────────────────────────────────────

def _is_finite_number(v: Any) -> bool:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


def _iter_peers(comparables: Any) -> List[Dict[str, Any]]:
    """Accept a ``ComparableSet`` (packet dataclass) OR an iterable of
    peer dicts. Returns a list of peer dicts with metric fields
    flattened for downstream use.
    """
    # Duck-type: packet's ComparableSet has .peers of ComparableHospital
    peers_attr = getattr(comparables, "peers", None)
    if peers_attr is not None:
        out: List[Dict[str, Any]] = []
        for p in peers_attr:
            d = dict(getattr(p, "fields", {}) or {})
            d["similarity_score"] = float(getattr(p, "similarity_score", 1.0))
            out.append(d)
        return out
    return list(comparables or [])


def _feature_keys(known: Dict[str, Any], comparables: List[Dict[str, Any]],
                  exclude: str) -> List[str]:
    """Which known metrics are usable as features to predict ``exclude``?

    A feature is usable when the target has it AND at least half the
    comparables have it (Ridge has no native NaN handling; row-drop
    would decimate the training set otherwise).
    """
    if not comparables:
        return []
    candidate = [k for k, v in known.items()
                 if k != exclude and _is_finite_number(v)]
    out: List[str] = []
    n = len(comparables)
    for k in candidate:
        present = sum(1 for p in comparables if _is_finite_number(p.get(k)))
        if present >= max(1, n // 2):
            out.append(k)
    return out


def _assemble_xy(
    comparables: List[Dict[str, Any]],
    features: List[str],
    target: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build (X, y, weights) from peer records. Drops rows missing any
    feature or the target so Ridge sees a clean dense matrix.
    """
    X_rows: List[List[float]] = []
    y_vals: List[float] = []
    w_vals: List[float] = []
    for peer in comparables:
        y_raw = peer.get(target)
        if not _is_finite_number(y_raw):
            continue
        row: List[float] = []
        ok = True
        for f in features:
            fv = peer.get(f)
            if not _is_finite_number(fv):
                ok = False
                break
            row.append(float(fv))
        if not ok:
            continue
        X_rows.append(row)
        y_vals.append(float(y_raw))
        w_vals.append(float(peer.get("similarity_score") or 1.0))
    return (np.asarray(X_rows, dtype=float),
            np.asarray(y_vals, dtype=float),
            np.asarray(w_vals, dtype=float))


def _grade(method: str, n: int, r_squared: float) -> str:
    """Reliability grade combining method, cohort size, and fit quality.

    Thresholds: anchored to what a partner will defend in IC. A Ridge
    fit on 30+ peers with R²>.6 is an "A" signal; a benchmark fallback
    is always a "D" regardless of cohort (by definition no
    hospital-specific lift).
    """
    if method == "benchmark_fallback":
        return "D"
    if method == "weighted_median":
        if n >= 10:
            return "B"
        return "C"
    # ridge_regression
    if n >= 30 and r_squared >= 0.60:
        return "A"
    if n >= 20 and r_squared >= 0.45:
        return "B"
    if n >= 15 and r_squared >= 0.25:
        return "C"
    return "D"


# ── Per-metric prediction branches ───────────────────────────────────

def _predict_ridge(
    target: str,
    known: Dict[str, Any],
    comparables: List[Dict[str, Any]],
    coverage: float,
    seed: int,
) -> Optional[PredictedMetric]:
    features = _feature_keys(known, comparables, exclude=target)
    if not features:
        return None
    X, y, _ = _assemble_xy(
        [p for p in comparables if _is_finite_number(p.get(target))],
        features, target,
    )
    if X.shape[0] < _MIN_FOR_RIDGE or X.shape[1] == 0:
        return None

    # Split 70/30 train/calibration; conformal margin from the cal split.
    X_tr, y_tr, X_cal, y_cal = split_train_calibration(
        X, y, cal_fraction=0.30, random_state=seed,
    )
    if len(X_tr) < 3:
        return None
    cp = ConformalPredictor(_RidgeModel(alpha=_RIDGE_ALPHA), coverage=coverage)
    try:
        cp.fit(X_tr, y_tr, X_cal, y_cal)
    except Exception:  # noqa: BLE001
        return None

    # Feature vector for the target hospital.
    try:
        x_target = np.asarray(
            [float(known[f]) for f in features], dtype=float,
        )
    except (KeyError, TypeError, ValueError):
        return None
    point, low, high = cp.predict_interval(x_target.reshape(1, -1))
    value = float(point[0])
    ci_low = float(low[0])
    ci_high = float(high[0])

    # LOO R² on the full X/y so the partner-facing score reflects the
    # whole cohort, not just the train split.
    r2 = _loo_r_squared(X, y, _RIDGE_ALPHA)

    # Feature importances = |standardized coefficient|, normalized to
    # sum to 1 so the UI can label the top driver cleanly.
    coefs = getattr(cp.base_model, "coef_", np.zeros(len(features)))
    abs_c = np.abs(np.asarray(coefs, dtype=float))
    total = float(abs_c.sum()) or 1.0
    importances = {f: float(abs_c[i] / total) for i, f in enumerate(features)}

    return PredictedMetric(
        value=value,
        method="ridge_regression",
        ci_low=ci_low,
        ci_high=ci_high,
        coverage_target=coverage,
        n_comparables_used=int(X.shape[0]),
        r_squared=float(r2),
        feature_importances=importances,
        reliability_grade=_grade("ridge_regression", int(X.shape[0]), r2),
    )


def _predict_weighted_median(
    target: str,
    comparables: List[Dict[str, Any]],
    coverage: float,
    seed: int,
) -> Optional[PredictedMetric]:
    pool = [p for p in comparables if _is_finite_number(p.get(target))]
    n = len(pool)
    if n < _MIN_FOR_MEDIAN:
        return None
    values = np.asarray([float(p[target]) for p in pool], dtype=float)
    weights = np.asarray([float(p.get("similarity_score") or 1.0) for p in pool],
                         dtype=float)
    point, low, high = bootstrap_interval(
        values, weights,
        coverage=coverage,
        statistic="weighted_median",
        random_state=seed,
    )
    return PredictedMetric(
        value=float(point),
        method="weighted_median",
        ci_low=float(low),
        ci_high=float(high),
        coverage_target=coverage,
        n_comparables_used=n,
        r_squared=0.0,
        feature_importances={},
        reliability_grade=_grade("weighted_median", n, 0.0),
    )


def _predict_benchmark_fallback(
    target: str,
    metric_registry: Dict[str, Dict[str, Any]],
) -> Optional[PredictedMetric]:
    meta = (metric_registry or {}).get(target) or {}
    p25 = _safe_float(meta.get("benchmark_p25"))
    p50 = _safe_float(meta.get("benchmark_p50"))
    p75 = _safe_float(meta.get("benchmark_p75"))
    if p50 is None:
        return None
    point, low, high = percentile_interval(
        p25 if p25 is not None else p50,
        p50,
        p75 if p75 is not None else p50,
    )
    return PredictedMetric(
        value=float(point),
        method="benchmark_fallback",
        ci_low=float(low),
        ci_high=float(high),
        coverage_target=_DEFAULT_COVERAGE,
        n_comparables_used=0,
        r_squared=0.0,
        feature_importances={},
        reliability_grade="D",
    )


# ── Public API ───────────────────────────────────────────────────────

def predict_missing_metrics(
    known_metrics: Dict[str, Any],
    comparables: Any,
    metric_registry: Dict[str, Dict[str, Any]],
    *,
    coverage: float = _DEFAULT_COVERAGE,
    seed: int = 42,
) -> Dict[str, PredictedMetric]:
    """Predict every metric in ``metric_registry`` the target is missing.

    Parameters
    ----------
    known_metrics
        The target hospital's observed metrics + demographics
        (``bed_count``, ``region``, ``payer_mix``). Non-numeric entries
        are passed through the interaction-feature derivation but don't
        enter the Ridge X matrix directly.
    comparables
        Either a :class:`~rcm_mc.analysis.packet.ComparableSet` or a
        list of peer dicts with a ``similarity_score`` key.
    metric_registry
        :data:`rcm_mc.analysis.completeness.RCM_METRIC_REGISTRY` or a
        compatible dict. Drives which metrics get predicted and
        provides the benchmark percentiles for the fallback branch.
    coverage
        Target coverage for conformal + bootstrap intervals (default 0.90).
    seed
        RNG seed for the train/cal split and bootstrap resampling.
        Deterministic output across runs when the inputs are unchanged.
    """
    peers = _iter_peers(comparables)

    # Fold interaction features into both the target and each peer so
    # Ridge can use ``revenue_per_bed`` et al as first-class features.
    enriched_known = dict(known_metrics or {})
    enriched_known.update(derive_interaction_features(enriched_known))
    enriched_peers: List[Dict[str, Any]] = []
    for p in peers:
        q = dict(p)
        q.update(derive_interaction_features(q))
        enriched_peers.append(q)

    out: Dict[str, PredictedMetric] = {}
    for metric in sorted(metric_registry or {}):
        if metric in known_metrics and _is_finite_number(known_metrics[metric]):
            # Already observed; nothing to predict.
            continue
        # Skip non-numeric registry entries that were added for
        # categorical demographics (state, city) — those aren't in the
        # user-facing completeness registry but guard anyway.
        if metric_registry.get(metric, {}).get("unit") == "dollars":
            # Dollar quantities (net_revenue, gross_revenue, current_ebitda,
            # total_operating_expenses) are financial inputs partners
            # supply — never predict them from comparables.
            continue

        pred: Optional[PredictedMetric] = None
        try:
            # Prompt 29: when the cohort is ≥ 15 we run the ensemble,
            # which picks the lowest-MAE base model per metric.
            # Smaller cohorts still use Ridge (already conservative
            # at low n) so we don't fit k-NN / median on data that
            # can't support them.
            from .ensemble_predictor import predict_metric_ensemble
            try:
                pred = predict_metric_ensemble(
                    metric, enriched_known, enriched_peers,
                    coverage=coverage, seed=seed,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "ensemble failed on %s; falling back to ridge: %s",
                    metric, exc,
                )
                pred = None
            if pred is None:
                pred = _predict_ridge(metric, enriched_known, enriched_peers,
                                      coverage, seed)
            if pred is None:
                pred = _predict_weighted_median(metric, enriched_peers,
                                                coverage, seed)
            if pred is None:
                pred = _predict_benchmark_fallback(metric, metric_registry)
        except Exception as exc:  # noqa: BLE001
            logger.debug("prediction for %s failed: %s", metric, exc)
            continue
        if pred is None:
            continue
        out[metric] = pred
    return out


def to_packet_predicted_metric(
    rp: PredictedMetric,
    *,
    upstream: Optional[List[str]] = None,
):
    """Convert this module's :class:`PredictedMetric` to the packet-wire
    :class:`rcm_mc.analysis.packet.PredictedMetric`. Avoids a hard
    import cycle — we delay the import to call time.

    Prompt 29: the ensemble path stashes ``_model_selection`` on the
    local ``PredictedMetric`` as an instance attribute. We thread it
    through to the packet's ``model_selection`` field so the
    workbench can show "Ridge picked" vs "k-NN picked" per metric.
    """
    from ..analysis.packet import PredictedMetric as PacketPM
    model_selection = str(
        getattr(rp, "_model_selection", "") or rp.method or ""
    )
    return PacketPM(
        value=float(rp.value),
        ci_low=float(rp.ci_low),
        ci_high=float(rp.ci_high),
        method=str(rp.method),
        r_squared=float(rp.r_squared),
        n_comparables_used=int(rp.n_comparables_used),
        feature_importances=dict(rp.feature_importances or {}),
        provenance_chain=list(upstream or []),
        coverage_target=float(rp.coverage_target),
        reliability_grade=str(rp.reliability_grade),
        model_selection=model_selection,
    )
