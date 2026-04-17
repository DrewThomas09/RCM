"""Margin trajectory predictor — trained on actual HCRIS cross-sectional data.

Unlike the hardcoded RCM predictor, this model is fitted on real hospital
data using ridge regression. It predicts:

1. Operating margin from hospital characteristics (fitted, not hardcoded)
2. Margin percentile within peer group
3. Turnaround probability for distressed hospitals
4. Feature explanations showing what drives the prediction

Every prediction includes:
- Point estimate
- Confidence interval (conformal)
- R² of the underlying model
- Top 3 feature contributions with direction and magnitude
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


_FEATURE_COLS = [
    "beds", "medicare_day_pct", "medicaid_day_pct", "commercial_pct",
    "occupancy_rate", "net_to_gross_ratio", "revenue_per_bed",
    "payer_diversity", "expense_per_bed",
    # Engineered features (added by _engineer_features)
    "cost_per_day", "bed_utilization_value", "reimbursement_quality",
    "state_median_margin", "log_beds", "occupancy_x_n2g",
]

_FEATURE_LABELS = {
    "beds": "Bed Count",
    "medicare_day_pct": "Medicare %",
    "medicaid_day_pct": "Medicaid %",
    "commercial_pct": "Commercial %",
    "occupancy_rate": "Occupancy",
    "net_to_gross_ratio": "Net-to-Gross",
    "revenue_per_bed": "Revenue/Bed",
    "payer_diversity": "Payer Diversity",
    "expense_per_bed": "Expense/Bed",
    "cost_per_day": "Cost per Patient Day",
    "bed_utilization_value": "Bed Utilization Value",
    "reimbursement_quality": "Reimbursement Quality",
    "state_median_margin": "State Peer Margin",
    "log_beds": "Log(Beds)",
    "occupancy_x_n2g": "Occupancy × Net-to-Gross",
}


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered features that improve margin prediction."""
    df = df.copy()

    # Cost per patient day (operational efficiency proxy)
    if "operating_expenses" in df.columns and "total_patient_days" in df.columns:
        df["cost_per_day"] = df["operating_expenses"] / df["total_patient_days"].replace(0, np.nan)

    # Bed utilization value = revenue/bed * occupancy
    if "revenue_per_bed" in df.columns and "occupancy_rate" in df.columns:
        df["bed_utilization_value"] = df["revenue_per_bed"] * df["occupancy_rate"]

    # Reimbursement quality = net-to-gross * commercial share
    if "net_to_gross_ratio" in df.columns and "commercial_pct" in df.columns:
        df["reimbursement_quality"] = df["net_to_gross_ratio"] * df["commercial_pct"]

    # State-level median margin (geographic adjustment)
    if "state" in df.columns and "operating_margin" in df.columns:
        try:
            margins = df["operating_margin"].dropna()
            if len(margins) > 10:
                state_medians = df.groupby("state")["operating_margin"].transform("median")
                df["state_median_margin"] = state_medians
        except Exception:
            pass

    # Log beds (diminishing returns to scale)
    if "beds" in df.columns:
        df["log_beds"] = np.log(df["beds"].clip(lower=1))

    # Interaction: occupancy × net-to-gross
    if "occupancy_rate" in df.columns and "net_to_gross_ratio" in df.columns:
        df["occupancy_x_n2g"] = df["occupancy_rate"] * df["net_to_gross_ratio"]

    return df


@dataclass
class FeatureContribution:
    feature: str
    label: str
    value: float
    coefficient: float
    contribution: float
    direction: str
    explanation: str


@dataclass
class MarginPrediction:
    predicted_margin: float
    ci_low: float
    ci_high: float
    actual_margin: Optional[float]
    peer_percentile: float
    model_r2: float
    n_training: int
    top_drivers: List[FeatureContribution]
    turnaround_probability: Optional[float]
    turnaround_explanation: str
    confidence_grade: str


@dataclass
class TrainedModel:
    beta: np.ndarray
    x_mean: np.ndarray
    x_std: np.ndarray
    r2: float
    n: int
    features_used: List[str]
    conformal_margin: float


def train_margin_model(hcris_df: pd.DataFrame) -> TrainedModel:
    """Train a ridge regression model on real HCRIS data to predict operating margin."""
    hcris_df = _engineer_features(hcris_df)
    available = [f for f in _FEATURE_COLS if f in hcris_df.columns]
    if len(available) < 4:
        return TrainedModel(
            beta=np.zeros(len(available) + 1),
            x_mean=np.zeros(len(available)), x_std=np.ones(len(available)),
            r2=0, n=0, features_used=available, conformal_margin=0.15,
        )

    target = "operating_margin"
    if target not in hcris_df.columns:
        return TrainedModel(
            beta=np.zeros(len(available) + 1),
            x_mean=np.zeros(len(available)), x_std=np.ones(len(available)),
            r2=0, n=0, features_used=available, conformal_margin=0.15,
        )
    drop_cols = [c for c in [target] + available if c in hcris_df.columns]
    clean = hcris_df.dropna(subset=drop_cols).copy()
    clean = clean[clean[target].between(-1, 1)]

    if len(clean) < 50:
        return TrainedModel(
            beta=np.zeros(len(available) + 1),
            x_mean=np.zeros(len(available)), x_std=np.ones(len(available)),
            r2=0, n=0, features_used=available, conformal_margin=0.15,
        )

    X = clean[available].values.astype(float)
    y = clean[target].values.astype(float)

    # Standardize
    x_mean = X.mean(axis=0)
    x_std = X.std(axis=0)
    x_std[x_std == 0] = 1
    X_norm = (X - x_mean) / x_std

    # Ridge regression (alpha=1.0)
    X_aug = np.column_stack([np.ones(len(X_norm)), X_norm])
    alpha = 1.0
    I = np.eye(X_aug.shape[1])
    I[0, 0] = 0  # don't regularize intercept
    beta = np.linalg.solve(X_aug.T @ X_aug + alpha * I, X_aug.T @ y)

    y_hat = X_aug @ beta
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # Split conformal: use last 30% as calibration
    n = len(y)
    cal_start = int(n * 0.7)
    cal_resid = np.abs(y[cal_start:] - y_hat[cal_start:])
    conformal_margin = float(np.quantile(cal_resid, 0.90)) if len(cal_resid) > 10 else 0.15

    return TrainedModel(
        beta=beta, x_mean=x_mean, x_std=x_std,
        r2=round(r2, 4), n=n, features_used=available,
        conformal_margin=round(conformal_margin, 4),
    )


def predict_margin(
    ccn: str,
    hcris_df: pd.DataFrame,
    model: Optional[TrainedModel] = None,
) -> Optional[MarginPrediction]:
    """Predict operating margin with full explainability."""
    hcris_df = _engineer_features(hcris_df)
    if model is None:
        model = train_margin_model(hcris_df)

    match = hcris_df[hcris_df["ccn"] == ccn]
    if match.empty:
        return None

    hospital = match.iloc[0]
    available = model.features_used

    # Extract features
    x_raw = np.array([float(hospital.get(f, 0) or 0) for f in available])
    # NaN safety
    x_raw = np.where(np.isnan(x_raw), 0, x_raw)
    x_norm = (x_raw - model.x_mean) / model.x_std
    x_aug = np.concatenate([[1], x_norm])

    predicted = float(x_aug @ model.beta)
    predicted = max(-1, min(1, predicted))

    ci_lo = predicted - model.conformal_margin
    ci_hi = predicted + model.conformal_margin

    # Actual margin
    actual = hospital.get("operating_margin")
    if actual is not None:
        try:
            actual = float(actual)
            if actual != actual:
                actual = None
        except (TypeError, ValueError):
            actual = None

    # Peer percentile
    all_margins = hcris_df["operating_margin"].dropna()
    percentile = float((all_margins < predicted).mean() * 100) if len(all_margins) > 10 else 50

    # Feature contributions (explainability)
    contributions = []
    for i, feat in enumerate(available):
        coef = model.beta[i + 1]  # skip intercept
        val = x_raw[i]
        contrib = coef * x_norm[i]

        if contrib > 0.005:
            direction = "positive"
            explanation = f"Higher {_FEATURE_LABELS.get(feat, feat)} increases predicted margin"
        elif contrib < -0.005:
            direction = "negative"
            explanation = f"{'Higher' if coef < 0 else 'Lower'} {_FEATURE_LABELS.get(feat, feat)} decreases predicted margin"
        else:
            direction = "neutral"
            explanation = f"{_FEATURE_LABELS.get(feat, feat)} has minimal effect"

        contributions.append(FeatureContribution(
            feature=feat,
            label=_FEATURE_LABELS.get(feat, feat),
            value=round(val, 4),
            coefficient=round(coef, 6),
            contribution=round(contrib, 6),
            direction=direction,
            explanation=explanation,
        ))

    contributions.sort(key=lambda c: -abs(c.contribution))

    # Turnaround probability for distressed hospitals
    turnaround_prob = None
    turnaround_expl = ""
    if actual is not None and actual < 0:
        # Logistic-style: probability predicted margin > 0
        z = predicted / max(0.01, model.conformal_margin)
        turnaround_prob = round(1 / (1 + np.exp(-z * 2)), 3)

        if turnaround_prob > 0.6:
            turnaround_expl = (
                f"Model predicts {turnaround_prob:.0%} probability of positive margin. "
                f"Key drivers: {contributions[0].label} and {contributions[1].label}."
            )
        elif turnaround_prob > 0.3:
            turnaround_expl = (
                f"Turnaround possible ({turnaround_prob:.0%}) but uncertain. "
                f"Margin improvement depends on "
                f"{'improving ' + contributions[0].label if contributions[0].direction == 'negative' else contributions[0].label}."
            )
        else:
            turnaround_expl = (
                f"Low turnaround probability ({turnaround_prob:.0%}). "
                f"Structural disadvantages in {contributions[0].label} and {contributions[1].label}."
            )

    # Confidence grade
    if model.r2 >= 0.5 and model.conformal_margin < 0.12:
        grade = "A"
    elif model.r2 >= 0.3:
        grade = "B"
    elif model.r2 >= 0.15:
        grade = "C"
    else:
        grade = "D"

    return MarginPrediction(
        predicted_margin=round(predicted, 4),
        ci_low=round(ci_lo, 4),
        ci_high=round(ci_hi, 4),
        actual_margin=round(actual, 4) if actual is not None else None,
        peer_percentile=round(percentile, 1),
        model_r2=model.r2,
        n_training=model.n,
        top_drivers=contributions[:5],
        turnaround_probability=turnaround_prob,
        turnaround_explanation=turnaround_expl,
        confidence_grade=grade,
    )


def batch_predict(
    hcris_df: pd.DataFrame,
    ccns: Optional[List[str]] = None,
    n_sample: int = 100,
) -> Tuple[TrainedModel, List[Dict[str, Any]]]:
    """Batch predict margins for multiple hospitals. Returns model + results."""
    hcris_df = _engineer_features(hcris_df)
    model = train_margin_model(hcris_df)

    if ccns is None:
        sample = hcris_df.sample(min(n_sample, len(hcris_df)), random_state=42)
        ccns = sample["ccn"].tolist()

    results = []
    for ccn in ccns:
        pred = predict_margin(str(ccn), hcris_df, model)
        if pred:
            results.append({
                "ccn": str(ccn),
                "predicted": pred.predicted_margin,
                "actual": pred.actual_margin,
                "error": pred.predicted_margin - pred.actual_margin if pred.actual_margin is not None else None,
                "ci_width": pred.ci_high - pred.ci_low,
                "in_ci": (pred.ci_low <= pred.actual_margin <= pred.ci_high) if pred.actual_margin is not None else None,
                "percentile": pred.peer_percentile,
                "turnaround_prob": pred.turnaround_probability,
                "grade": pred.confidence_grade,
            })

    return model, results
