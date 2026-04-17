"""Backtest the predictor against held-out hospital data.

Two entry points:

- :func:`backtest` — per-hospital: hold the last ``holdout_months`` of
  data for each target metric, predict from the rest + comparables,
  and score.
- :func:`run_cohort_backtest` — walks every hospital, treats each as
  the target, predicts against the remaining cohort, and aggregates.

The partner-facing output is a letter grade (A/B/C/D/F) per metric so
it fits on a one-row summary card.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from .comparable_finder import find_comparables
from .rcm_predictor import RCM_METRICS, predict_missing

# R² → letter grade. Thresholds match what partners tolerate on a
# model card: A ≥ .75 is "cite it"; below .50 is "directionally useful
# only"; < .20 is don't ship.
_GRADE_CUTS = [
    (0.75, "A"),
    (0.60, "B"),
    (0.45, "C"),
    (0.25, "D"),
]


def _grade(r_squared: float) -> str:
    for cut, letter in _GRADE_CUTS:
        if r_squared >= cut:
            return letter
    return "F"


@dataclass
class BacktestResult:
    """Per-metric accuracy breakdown plus aggregate reliability grade.

    ``per_metric`` maps metric_name → dict with keys: ``mae``, ``r2``,
    ``mape``, ``n``, ``grade``. Metrics with no test samples are
    omitted.
    """

    per_metric: Dict[str, Dict[str, float]] = field(default_factory=dict)
    overall_grade: str = "F"
    n_hospitals: int = 0
    n_predictions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_metric": self.per_metric,
            "overall_grade": self.overall_grade,
            "n_hospitals": self.n_hospitals,
            "n_predictions": self.n_predictions,
        }


def _mae(y_true: List[float], y_pred: List[float]) -> float:
    if not y_true:
        return float("nan")
    return float(np.mean([abs(a - b) for a, b in zip(y_true, y_pred)]))


def _mape(y_true: List[float], y_pred: List[float]) -> float:
    if not y_true:
        return float("nan")
    errs: List[float] = []
    for a, b in zip(y_true, y_pred):
        if abs(a) < 1e-9:
            continue
        errs.append(abs((a - b) / a))
    return float(np.mean(errs)) if errs else float("nan")


def _r2(y_true: List[float], y_pred: List[float]) -> float:
    if len(y_true) < 2:
        return 0.0
    y = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    ss_res = float(np.sum((y - yp) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 1e-12:
        return 0.0
    return max(-1.0, 1.0 - ss_res / ss_tot)


def backtest(
    hospital_data: List[Dict[str, Any]],
    *,
    holdout_months: int = 6,  # noqa: ARG001 — reserved for monthly streams
    max_comparables: int = 50,
) -> BacktestResult:
    """Leave-one-out backtest across ``hospital_data``.

    Each hospital in turn is treated as the target; the rest is the
    candidate pool for comparables. All RCM_METRICS the target carries
    are predicted — the predicted vs. observed pairs build up the
    per-metric accuracy stats.

    ``holdout_months`` is reserved for when we start ingesting monthly
    RCM streams per hospital (not the current cross-sectional snapshot
    model). The parameter is accepted now so the API shape is stable.
    """
    hospital_data = list(hospital_data or [])
    n = len(hospital_data)
    if n < 2:
        return BacktestResult(overall_grade="F", n_hospitals=n)

    pairs: Dict[str, List[List[float]]] = {}  # metric → [[true], [pred]]
    n_preds = 0
    for i, target in enumerate(hospital_data):
        pool = [h for j, h in enumerate(hospital_data) if j != i]
        comps = find_comparables(target, pool, max_results=max_comparables)
        # Mask every known RCM metric and predict it.
        known = {k: v for k, v in target.items()
                 if k not in set(RCM_METRICS)
                 or k == "payer_mix"}
        # Keep non-RCM context (bed_count, region, payer_mix) as features.
        preds = predict_missing(known, comps)
        for metric, pm in preds.items():
            actual = target.get(metric)
            if actual is None:
                continue
            try:
                a = float(actual)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(a):
                continue
            pairs.setdefault(metric, [[], []])
            pairs[metric][0].append(a)
            pairs[metric][1].append(float(pm.value))
            n_preds += 1

    per_metric: Dict[str, Dict[str, float]] = {}
    for metric, (y_true, y_pred) in pairs.items():
        r2 = _r2(y_true, y_pred)
        per_metric[metric] = {
            "mae": _mae(y_true, y_pred),
            "r2": r2,
            "mape": _mape(y_true, y_pred),
            "n": len(y_true),
            "grade": _grade(r2),
        }

    overall_r2 = (
        float(np.mean([m["r2"] for m in per_metric.values()]))
        if per_metric else 0.0
    )
    return BacktestResult(
        per_metric=per_metric,
        overall_grade=_grade(overall_r2),
        n_hospitals=n,
        n_predictions=n_preds,
    )


def run_cohort_backtest(
    all_hospitals: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """System-wide backtest — aggregate accuracy across the entire
    cohort so a partner can see "our denial_rate predictions grade B
    on 243 hospitals" at a glance.

    Returns a JSON-safe dict with overall grade, per-metric table, and
    cohort size.
    """
    result = backtest(list(all_hospitals))
    return result.to_dict()


# ── Conformal-backed backtest with coverage accounting ──────────────

@dataclass
class PredictionBacktestResult:
    """Per-metric MAE / R² / conformal coverage across randomized trials.

    ``coverage_rate`` is the critical signal — if the ridge predictor's
    90% intervals cover the truth <85% of the time on historical data,
    the conformal calibration is broken and we should NOT ship the
    predictor until we understand why.
    """
    per_metric_mae: Dict[str, float] = field(default_factory=dict)
    per_metric_r_squared: Dict[str, float] = field(default_factory=dict)
    coverage_rate: Dict[str, float] = field(default_factory=dict)
    n_predictions: Dict[str, int] = field(default_factory=dict)
    overall_reliability: str = "F"
    n_trials: int = 0
    holdout_fraction: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_metric_mae": self.per_metric_mae,
            "per_metric_r_squared": self.per_metric_r_squared,
            "coverage_rate": self.coverage_rate,
            "n_predictions": self.n_predictions,
            "overall_reliability": self.overall_reliability,
            "n_trials": self.n_trials,
            "holdout_fraction": self.holdout_fraction,
        }


def _pick_metrics_to_hide(
    hospital: Dict[str, Any],
    registry_keys: List[str],
    fraction: float,
    rng: "np.random.Generator",
) -> List[str]:
    """Uniformly sample `fraction` of the hospital's observed registry
    metrics to hide for this trial. At least 1, at most all-but-1.
    """
    present = [k for k in registry_keys
               if k in hospital and _finite(hospital[k])]
    if len(present) < 2:
        return []
    n_hide = max(1, min(len(present) - 1,
                        int(round(len(present) * float(fraction)))))
    idx = rng.choice(len(present), size=n_hide, replace=False)
    return [present[int(i)] for i in idx]


def _finite(x: Any) -> bool:
    try:
        f = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


def backtest_predictions(
    hospital_pool: Iterable[Dict[str, Any]],
    *,
    holdout_fraction: float = 0.3,
    n_trials: int = 50,
    coverage: float = 0.90,
    seed: int = 1337,
) -> PredictionBacktestResult:
    """Randomized hide-and-predict backtest for the ridge predictor.

    For each trial we pick a random hospital, hide a random slice of
    its metrics (``holdout_fraction``), and call
    :func:`rcm_mc.ml.ridge_predictor.predict_missing_metrics` against
    the rest of the pool. The hidden actuals become the ground truth
    against which we score MAE / R² / empirical coverage.

    An ``overall_reliability`` grade combines mean R² and coverage
    health — coverage within ±5pp of the target lifts the grade; a
    big coverage miss caps it at "C" regardless of R².
    """
    from ..analysis.completeness import RCM_METRIC_REGISTRY
    from .ridge_predictor import predict_missing_metrics

    pool = [h for h in (hospital_pool or []) if isinstance(h, dict)]
    n = len(pool)
    if n < 3:
        return PredictionBacktestResult(
            n_trials=0, holdout_fraction=holdout_fraction, overall_reliability="F",
        )
    registry_keys = list(RCM_METRIC_REGISTRY.keys())
    rng = np.random.default_rng(int(seed))

    pairs: Dict[str, List[List[float]]] = {}   # metric → [[y_true], [y_pred]]
    covered: Dict[str, List[int]] = {}         # metric → [0/1 per prediction]

    for _ in range(int(n_trials)):
        # Pick a random target hospital
        tgt_idx = int(rng.integers(0, n))
        target = pool[tgt_idx]
        rest = [h for i, h in enumerate(pool) if i != tgt_idx]
        hide = _pick_metrics_to_hide(target, registry_keys,
                                     holdout_fraction, rng)
        if not hide:
            continue
        # Build "known" set = everything except the hidden metrics.
        known: Dict[str, Any] = {
            k: v for k, v in target.items()
            if (k not in hide) and (_finite(v) or isinstance(v, dict))
        }
        # Synthetic ComparableSet-like list of peer dicts.
        peers = []
        for h in rest:
            d = dict(h)
            d.setdefault("similarity_score", 1.0)
            peers.append(d)
        try:
            preds = predict_missing_metrics(
                known, peers, RCM_METRIC_REGISTRY,
                coverage=coverage, seed=int(rng.integers(0, 1_000_000)),
            )
        except Exception:  # noqa: BLE001
            continue
        for metric in hide:
            actual = target.get(metric)
            if not _finite(actual):
                continue
            pm = preds.get(metric)
            if pm is None:
                continue
            pairs.setdefault(metric, [[], []])
            pairs[metric][0].append(float(actual))
            pairs[metric][1].append(float(pm.value))
            in_band = 1 if (pm.ci_low <= float(actual) <= pm.ci_high) else 0
            covered.setdefault(metric, []).append(in_band)

    per_mae: Dict[str, float] = {}
    per_r2: Dict[str, float] = {}
    per_cov: Dict[str, float] = {}
    per_n: Dict[str, int] = {}
    for metric, (y_true, y_pred) in pairs.items():
        per_mae[metric] = _mae(y_true, y_pred)
        per_r2[metric] = _r2(y_true, y_pred)
        per_n[metric] = len(y_true)
        c = covered.get(metric) or []
        per_cov[metric] = (sum(c) / len(c)) if c else 0.0

    mean_r2 = float(np.mean(list(per_r2.values()))) if per_r2 else 0.0
    # Coverage health: mean |observed - target| over metrics with >=5 preds.
    cov_errors = [abs(per_cov[m] - coverage)
                  for m in per_cov if per_n.get(m, 0) >= 5]
    mean_cov_err = float(np.mean(cov_errors)) if cov_errors else 0.0

    base = _grade(mean_r2)
    if mean_cov_err > 0.15:
        # Coverage is way off — cap grade at C regardless of R².
        base = min(base, "C", key=lambda g: "ABCDF".index(g))
    return PredictionBacktestResult(
        per_metric_mae=per_mae,
        per_metric_r_squared=per_r2,
        coverage_rate=per_cov,
        n_predictions=per_n,
        overall_reliability=base,
        n_trials=int(n_trials),
        holdout_fraction=float(holdout_fraction),
    )
