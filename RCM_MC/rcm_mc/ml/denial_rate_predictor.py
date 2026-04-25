"""Trained denial-rate predictor — public-data → likely denial rate.

Predicts a hospital's expected denial rate from features available
*before* requesting internal data:

  • HCRIS: bed count, payer-mix (Medicare/Medicaid/commercial day
    pct), occupancy, gross-to-net ratio, operating margin
  • Hospital Compare: Star Rating, readmission rate, mortality
    rate, HCAHPS satisfaction
  • Geography: state-level RCM-environment factor, MA penetration
  • Case mix: case-mix index proxy (gross charges / discharges)

Uses the shared Ridge + 5-fold CV scaffold in
``trained_rcm_predictor.py``. The trained predictor reports
out-of-sample R², MAE, MAPE — not training fit — so partner sees
genuine generalization skill.

Public API::

    predictor = train_denial_rate_predictor(training_df)
    yhat, (lo, hi) = predictor.predict_with_interval(features)
    contributions = predictor.explain(features)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .trained_rcm_predictor import (
    TrainedRCMPredictor,
    train_ridge_with_cv,
)


# Canonical feature set for the denial-rate predictor. Order is
# fixed so model files, JSON exports, and feature attributions
# stay stable across training runs.
DENIAL_RATE_FEATURES: List[str] = [
    "beds_log",
    "medicare_day_pct",
    "medicaid_day_pct",
    "occupancy_rate",
    "net_to_gross_ratio",
    "operating_margin",
    "case_mix_proxy",      # gross charges / discharges
    "star_rating",
    "readmission_rate",
    "mortality_rate",
    "hcahps_score",
    "ma_penetration",
    "state_rcm_factor",
]

# Sanity range for denial rate. National averages run 5-15%;
# the worst tail rarely exceeds 30%. Negative is impossible.
DENIAL_RATE_RANGE: Tuple[float, float] = (0.0, 0.40)


def build_denial_features(
    hospital: Dict[str, Any],
    *,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Build the canonical feature dict from a HCRIS+quality row.

    Missing fields fall back to national-average defaults so a
    sparse row doesn't refuse to predict — partner sees the
    explain() output and can judge how much the missing fields
    matter.
    """
    state_factors = state_rcm_factors or {}
    beds = float(hospital.get("beds") or 100)
    discharges = float(hospital.get("discharges") or beds * 4)
    gross = float(hospital.get("gross_patient_revenue")
                  or hospital.get("gross_charges")
                  or beds * 4 * 50_000)
    rev = float(hospital.get("net_patient_revenue") or gross * 0.3)
    opex = float(hospital.get("operating_expenses") or rev)
    days = float(hospital.get("total_patient_days")
                 or beds * 200)
    bda = float(hospital.get("bed_days_available")
                or beds * 365)

    occupancy = days / bda if bda > 0 else 0.5
    n2g = rev / gross if gross > 0 else 0.30
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
        "occupancy_rate": occupancy,
        "net_to_gross_ratio": n2g,
        "operating_margin": margin,
        "case_mix_proxy": case_mix / 100_000,  # scale ~1
        "star_rating": float(
            hospital.get("star_rating") or 3.0),
        "readmission_rate": float(
            hospital.get("readmission_rate") or 0.15),
        "mortality_rate": float(
            hospital.get("mortality_rate") or 0.10),
        "hcahps_score": float(
            hospital.get("hcahps_score") or 0.72),
        "ma_penetration": float(
            hospital.get("ma_penetration") or 0.40),
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
        f = build_denial_features(
            r, state_rcm_factors=state_rcm_factors)
        out.append([f[n] for n in DENIAL_RATE_FEATURES])
    return np.array(out, dtype=float)


def train_denial_rate_predictor(
    training_data: Iterable[Dict[str, Any]],
    *,
    target_field: str = "denial_rate",
    alpha: float = 1.0,
    n_folds: int = 5,
    seed: int = 42,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> TrainedRCMPredictor:
    """Fit the denial-rate predictor with k-fold CV.

    Args:
      training_data: iterable of dicts. Each dict must contain
        the target field (default ``denial_rate``) plus any
        public-data feature fields (HCRIS / Hospital Compare /
        geography). Missing features fall back to national
        averages — see ``build_denial_features``.
      target_field: the ground-truth column name in training_data.
      alpha: Ridge penalty (1.0 default for standardized features).
      n_folds: 5-fold CV by default.
      seed: deterministic.
      state_rcm_factors: optional dict mapping state → numeric
        RCM-environment adjustment.

    Returns: TrainedRCMPredictor with sanity_range clamped to
    (0.0, 0.40) — denial rates can't go negative and rarely
    exceed 30%.
    """
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
        feature_names=DENIAL_RATE_FEATURES,
        target_metric="denial_rate",
        alpha=alpha,
        n_folds=n_folds,
        seed=seed,
        sanity_range=DENIAL_RATE_RANGE,
    )


def predict_denial_rate(
    predictor: TrainedRCMPredictor,
    hospital: Dict[str, Any],
    *,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> Tuple[float, Tuple[float, float],
           List[Tuple[str, float]]]:
    """Convenience wrapper: features + interval + contributions.

    Returns: (point_estimate, (ci_lo, ci_hi), explanation)
    """
    features = build_denial_features(
        hospital, state_rcm_factors=state_rcm_factors)
    yhat, ci = predictor.predict_with_interval(features)
    explanation = predictor.explain(features)
    return yhat, ci, explanation
