"""Trained collection-rate predictor — feature importance focus.

Predicts net collection rate (% of net realizable revenue actually
collected) from public hospital characteristics. National avg
~96-99% for well-run hospitals; <93% is the danger zone. This
module's headline output is **feature importance** — both
per-instance contributions (via the shared scaffold's explain())
and global rankings:

  • Standardized |β| importance: 'a 1-σ change in this feature
    moves prediction by β units, holding others fixed'
  • Permutation importance: shuffle each feature, measure R²
    drop. More honest than |β| under feature correlation.

The two should usually rank features similarly; when they
disagree, permutation importance is closer to ground truth.

Public API::

    predictor = train_collection_rate_predictor(rows)
    importance = predictor.feature_importance()
    perm_imp = collection_rate_permutation_importance(
        predictor, rows)
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .trained_rcm_predictor import (
    TrainedRCMPredictor,
    permutation_importance,
    train_ridge_with_cv,
)


# Collection-rate feature set. Differs from denial / DSO:
#   - Includes denial rate + DSO as upstream RCM signals (when
#     available) — collection rate is downstream of both.
#   - Patient experience proxy (HCAHPS) matters because patient-
#     responsibility collections lean on registration + billing
#     interactions, not just adjudication.
COLLECTION_RATE_FEATURES: List[str] = [
    "beds_log",
    "medicare_day_pct",
    "medicaid_day_pct",
    "self_pay_pct",
    "operating_margin",
    "case_mix_proxy",
    "occupancy_rate",
    "denial_rate_input",       # upstream signal when available
    "days_in_ar_input",        # upstream signal when available
    "hcahps_score",
    "ma_penetration",
    "rural_flag",
    "state_rcm_factor",
]

# Collection rates: ranges 0.85-1.00 in practice. Below 0.85 is a
# distressed asset; above 1.00 is impossible (would be over-
# collection or netting issues).
COLLECTION_RATE_RANGE: Tuple[float, float] = (0.70, 1.00)


def build_collection_features(
    hospital: Dict[str, Any],
    *,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Build the canonical collection-rate feature dict.

    Includes denial_rate_input + days_in_ar_input as upstream
    RCM signals — these are *predictions* in production (from
    the other RCM predictors) but ground-truth in training.
    """
    state_factors = state_rcm_factors or {}
    beds = float(hospital.get("beds") or 100)
    discharges = float(
        hospital.get("discharges") or beds * 4)
    gross = float(hospital.get("gross_patient_revenue")
                  or hospital.get("gross_charges")
                  or beds * 4 * 50_000)
    rev = float(hospital.get("net_patient_revenue")
                or gross * 0.3)
    opex = float(hospital.get("operating_expenses") or rev)
    days = float(hospital.get("total_patient_days")
                 or beds * 200)
    bda = float(hospital.get("bed_days_available")
                or beds * 365)
    occupancy = days / bda if bda > 0 else 0.5
    margin = (rev - opex) / rev if rev > 1e5 else 0.0
    margin = max(-0.5, min(0.5, margin))
    case_mix = gross / discharges if discharges > 0 else 60_000
    state = str(hospital.get("state") or "").upper()

    return {
        "beds_log": float(np.log(max(1.0, beds))),
        "medicare_day_pct": float(
            hospital.get("medicare_day_pct") or 0.40),
        "medicaid_day_pct": float(
            hospital.get("medicaid_day_pct") or 0.15),
        "self_pay_pct": float(
            hospital.get("self_pay_pct") or 0.05),
        "operating_margin": margin,
        "case_mix_proxy": case_mix / 100_000,
        "occupancy_rate": occupancy,
        "denial_rate_input": float(
            hospital.get("denial_rate") or 0.10),
        "days_in_ar_input": float(
            hospital.get("days_in_ar") or 45.0),
        "hcahps_score": float(
            hospital.get("hcahps_score") or 0.72),
        "ma_penetration": float(
            hospital.get("ma_penetration") or 0.40),
        "rural_flag": float(hospital.get("rural") or 0.0),
        "state_rcm_factor": float(
            state_factors.get(state, 0.0)),
    }


def _features_to_matrix(
    rows: Iterable[Dict[str, Any]],
    *,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> np.ndarray:
    out = []
    for r in rows:
        f = build_collection_features(
            r, state_rcm_factors=state_rcm_factors)
        out.append([f[n] for n in COLLECTION_RATE_FEATURES])
    return np.array(out, dtype=float)


def train_collection_rate_predictor(
    training_data: Iterable[Dict[str, Any]],
    *,
    target_field: str = "collection_rate",
    alpha: float = 1.0,
    n_folds: int = 5,
    seed: int = 42,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> TrainedRCMPredictor:
    """Fit collection-rate predictor with 5-fold CV."""
    rows = list(training_data)
    if not rows:
        raise ValueError(
            "Cannot train on empty training_data")
    y = np.array([float(r[target_field]) for r in rows],
                 dtype=float)
    X = _features_to_matrix(
        rows, state_rcm_factors=state_rcm_factors)
    return train_ridge_with_cv(
        X, y,
        feature_names=COLLECTION_RATE_FEATURES,
        target_metric="collection_rate",
        alpha=alpha,
        n_folds=n_folds,
        seed=seed,
        sanity_range=COLLECTION_RATE_RANGE,
    )


def collection_rate_permutation_importance(
    predictor: TrainedRCMPredictor,
    rows: Iterable[Dict[str, Any]],
    *,
    target_field: str = "collection_rate",
    n_repeats: int = 5,
    seed: int = 42,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> List[Tuple[str, float, float]]:
    """Permutation importance for the collection-rate predictor.

    Returns: (feature_name, mean R² drop, std R² drop) tuples
    sorted by mean drop descending — the highest-impact features
    appear first.
    """
    rows_list = list(rows)
    y = np.array(
        [float(r[target_field]) for r in rows_list],
        dtype=float)
    X = _features_to_matrix(
        rows_list, state_rcm_factors=state_rcm_factors)
    return permutation_importance(
        predictor, X, y,
        n_repeats=n_repeats, seed=seed)


def predict_collection_rate(
    predictor: TrainedRCMPredictor,
    hospital: Dict[str, Any],
    *,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> Tuple[float, Tuple[float, float],
           List[Tuple[str, float]]]:
    """Returns (point_estimate, ci, contributions)."""
    features = build_collection_features(
        hospital, state_rcm_factors=state_rcm_factors)
    yhat, ci = predictor.predict_with_interval(features)
    explanation = predictor.explain(features)
    return yhat, ci, explanation
