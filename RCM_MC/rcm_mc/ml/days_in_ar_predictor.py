"""Trained days-in-AR predictor — payer mix + volume + geo + case mix.

Predicts a hospital's expected days in accounts receivable from
public-data features. The directive specifically calls out:

  • **Payer mix** — Medicare/Medicaid pay slower than commercial;
    self-pay is the worst tail. Mix is the dominant driver.
  • **Volume** — log-bed-size + total-discharges. Larger hospitals
    have dedicated AR teams + better front-end registration.
  • **Geography** — state RCM environment + MA penetration
    (high-MA markets carry prior-auth burden = longer AR).
  • **Case mix** — high CMI = more complex claims = longer
    adjudication. Gross charges per discharge is the proxy.

The shared scaffold provides standard 5-fold CV; this module also
exposes a leave-one-cohort-out CV (bed-size buckets) so partner
sees transfer skill — a model trained on big-system hospitals
shouldn't be trusted on rural critical-access hospitals without
seeing that cohort's R² explicitly.

Public API::

    predictor = train_days_in_ar_predictor(training_df)
    cohort_cv = cross_validate_days_in_ar_by_cohort(
        training_df, cohort_field='bed_size_bucket')
    yhat, ci, expl = predict_days_in_ar(predictor, hospital)
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .trained_rcm_predictor import (
    CohortCVResult,
    TrainedRCMPredictor,
    cross_validate_across_cohorts,
    train_ridge_with_cv,
)


# Days-in-AR feature set. Differs from denial_rate in:
#   - explicit volume features (log_discharges + log_beds)
#   - case-mix proxy gets headline weight
#   - payer mix has interaction terms (medicaid × ma_penetration)
DAYS_AR_FEATURES: List[str] = [
    "beds_log",
    "discharges_log",
    "medicare_day_pct",
    "medicaid_day_pct",
    "self_pay_pct",
    "case_mix_proxy",
    "occupancy_rate",
    "ma_penetration",
    "ma_x_medicaid",   # interaction: prior-auth on dual-eligibles
    "state_rcm_factor",
    "rural_flag",
    "operating_margin",
]

# National avg ~45 days, range ~25-90. Clamp to sane bounds.
DAYS_AR_RANGE: Tuple[float, float] = (15.0, 120.0)


def _bed_size_bucket(beds: float) -> str:
    """Canonical bed-size cohort label for transfer-CV."""
    b = float(beds or 0)
    if b < 50:
        return "critical_access"
    if b < 150:
        return "small"
    if b < 400:
        return "mid"
    return "large"


def build_days_ar_features(
    hospital: Dict[str, Any],
    *,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Build the canonical feature dict for days-in-AR."""
    state_factors = state_rcm_factors or {}
    beds = float(hospital.get("beds") or 100)
    discharges = float(
        hospital.get("discharges")
        or hospital.get("total_discharges")
        or beds * 4)
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

    mc = float(hospital.get("medicare_day_pct") or 0.40)
    md = float(hospital.get("medicaid_day_pct") or 0.15)
    sp = float(hospital.get("self_pay_pct") or 0.05)
    ma = float(hospital.get("ma_penetration") or 0.40)

    state = str(hospital.get("state") or "").upper()
    rural = float(hospital.get("rural") or 0.0)

    return {
        "beds_log": float(np.log(max(1.0, beds))),
        "discharges_log": float(
            np.log(max(1.0, discharges))),
        "medicare_day_pct": mc,
        "medicaid_day_pct": md,
        "self_pay_pct": sp,
        "case_mix_proxy": case_mix / 100_000,
        "occupancy_rate": occupancy,
        "ma_penetration": ma,
        "ma_x_medicaid": ma * md,
        "state_rcm_factor": float(
            state_factors.get(state, 0.0)),
        "rural_flag": rural,
        "operating_margin": margin,
    }


def _features_to_matrix(
    rows: Iterable[Dict[str, Any]],
    *,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> np.ndarray:
    out = []
    for r in rows:
        f = build_days_ar_features(
            r, state_rcm_factors=state_rcm_factors)
        out.append([f[n] for n in DAYS_AR_FEATURES])
    return np.array(out, dtype=float)


def train_days_in_ar_predictor(
    training_data: Iterable[Dict[str, Any]],
    *,
    target_field: str = "days_in_ar",
    alpha: float = 1.0,
    n_folds: int = 5,
    seed: int = 42,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> TrainedRCMPredictor:
    """Fit days-in-AR Ridge predictor with 5-fold CV."""
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
        feature_names=DAYS_AR_FEATURES,
        target_metric="days_in_ar",
        alpha=alpha,
        n_folds=n_folds,
        seed=seed,
        sanity_range=DAYS_AR_RANGE,
    )


def cross_validate_days_in_ar_by_cohort(
    training_data: Iterable[Dict[str, Any]],
    *,
    cohort_field: str = "bed_size_bucket",
    target_field: str = "days_in_ar",
    alpha: float = 1.0,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> CohortCVResult:
    """Leave-one-cohort-out CV across hospital cohorts.

    The default cohort is bed-size bucket (critical_access /
    small / mid / large); pass ``cohort_field='region'`` or
    ``cohort_field='urban_rural'`` for those splits if rows have
    them. If the cohort field is missing, falls back to deriving
    the bed-size bucket from beds.
    """
    rows = list(training_data)
    if not rows:
        raise ValueError(
            "Cannot cross-validate on empty data")
    cohorts: List[Any] = []
    for r in rows:
        if cohort_field in r and r[cohort_field]:
            cohorts.append(r[cohort_field])
        else:
            cohorts.append(_bed_size_bucket(
                r.get("beds") or 100))
    y = np.array([float(r[target_field]) for r in rows],
                 dtype=float)
    X = _features_to_matrix(
        rows, state_rcm_factors=state_rcm_factors)
    return cross_validate_across_cohorts(
        X, y, cohorts,
        feature_names=DAYS_AR_FEATURES,
        alpha=alpha,
        sanity_range=DAYS_AR_RANGE,
    )


def predict_days_in_ar(
    predictor: TrainedRCMPredictor,
    hospital: Dict[str, Any],
    *,
    state_rcm_factors: Optional[Dict[str, float]] = None,
) -> Tuple[float, Tuple[float, float],
           List[Tuple[str, float]]]:
    """Returns (point_estimate, ci, contributions)."""
    features = build_days_ar_features(
        hospital, state_rcm_factors=state_rcm_factors)
    yhat, ci = predictor.predict_with_interval(features)
    explanation = predictor.explain(features)
    return yhat, ci, explanation
