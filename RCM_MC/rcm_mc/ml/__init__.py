"""Phase-1 regression prediction engine — fills missing RCM metrics from
partial data by finding comparable hospitals and fitting Ridge models
against the comparable cohort.

Public surface::

    from rcm_mc.ml import (
        find_comparables,
        RCM_METRICS, predict_missing, PredictedMetric,
        backtest, run_cohort_backtest, BacktestResult,
        derive_features, normalize_metrics, detect_outliers,
    )
"""
from .comparable_finder import find_comparables, similarity_score
from .feature_engineering import (
    derive_features, normalize_metrics, detect_outliers,
)
from .rcm_predictor import (
    RCM_METRICS, PredictedMetric, predict_missing,
)
from .backtester import (
    BacktestResult, backtest, run_cohort_backtest,
)

__all__ = [
    "find_comparables", "similarity_score",
    "RCM_METRICS", "PredictedMetric", "predict_missing",
    "BacktestResult", "backtest", "run_cohort_backtest",
    "derive_features", "normalize_metrics", "detect_outliers",
]
