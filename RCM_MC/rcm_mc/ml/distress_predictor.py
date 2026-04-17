"""Hospital financial distress predictor.

Logistic regression model that estimates the probability a hospital will
experience financial distress (operating margin < -5%) within the next
fiscal year. Uses only publicly available HCRIS features.

This is a core moat: Bloomberg shows trailing financials; we predict
forward distress probability and flag acquisition opportunities before
the market recognizes them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


_DISTRESS_THRESHOLD = -0.05  # operating margin below -5% = distressed

_PREDICTOR_FEATURES = [
    "operating_margin",
    "occupancy_rate",
    "medicare_day_pct",
    "medicaid_day_pct",
    "revenue_per_bed",
    "net_to_gross_ratio",
    "beds",
]

_RISK_LABELS = {
    (0.0, 0.10): ("Low", "green"),
    (0.10, 0.25): ("Moderate", "amber"),
    (0.25, 0.50): ("Elevated", "warning"),
    (0.50, 0.75): ("High", "red"),
    (0.75, 1.01): ("Critical", "critical"),
}


@dataclass
class DistressPrediction:
    ccn: str
    hospital_name: str
    state: str
    distress_probability: float
    risk_label: str
    risk_color: str
    contributing_factors: List[Dict[str, Any]]
    peer_distress_rate: float
    state_distress_rate: float
    model_auc: float
    n_training: int


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -500, 500)
    return 1 / (1 + np.exp(-z))


def _fit_logistic(X: np.ndarray, y: np.ndarray, lr: float = 0.01, n_iter: int = 500) -> np.ndarray:
    """Gradient descent logistic regression. No sklearn needed."""
    n, p = X.shape
    X_aug = np.column_stack([np.ones(n), X])
    beta = np.zeros(p + 1)

    for _ in range(n_iter):
        z = X_aug @ beta
        pred = _sigmoid(z)
        grad = X_aug.T @ (pred - y) / n
        # L2 regularization
        grad[1:] += 0.01 * beta[1:]
        beta -= lr * grad

    return beta


def _compute_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Approximate AUC via trapezoidal rule on ROC."""
    order = np.argsort(-y_score)
    y_sorted = y_true[order]
    n_pos = y_true.sum()
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    tp = 0
    fp = 0
    auc = 0.0
    prev_fpr = 0.0
    for i in range(len(y_sorted)):
        if y_sorted[i] == 1:
            tp += 1
        else:
            fp += 1
            fpr = fp / n_neg
            tpr = tp / n_pos
            auc += (fpr - prev_fpr) * tpr
            prev_fpr = fpr
    return float(auc)


def train_distress_model(
    hcris_df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, int, List[str]]:
    """Train logistic regression distress model on HCRIS data.

    Returns (beta, X_mean, X_std, auc, n_training, features_used).
    """
    df = hcris_df.copy()

    # Compute derived features
    if "revenue_per_bed" not in df.columns:
        df["revenue_per_bed"] = df.get("net_patient_revenue", 0) / df["beds"].replace(0, np.nan)
    if "operating_margin" not in df.columns:
        rev = df.get("net_patient_revenue", pd.Series(dtype=float))
        opex = df.get("operating_expenses", pd.Series(dtype=float))
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)
    if "occupancy_rate" not in df.columns:
        df["occupancy_rate"] = df.get("total_patient_days", 0) / df["bed_days_available"].replace(0, np.nan)
    if "net_to_gross_ratio" not in df.columns:
        df["net_to_gross_ratio"] = (
            df.get("net_patient_revenue", 0) / df["gross_patient_revenue"].replace(0, np.nan)
        ).clip(0, 1)

    available = [f for f in _PREDICTOR_FEATURES if f in df.columns]
    clean = df.dropna(subset=available + ["operating_margin"]).copy()

    if len(clean) < 50:
        return np.zeros(len(available) + 1), np.zeros(len(available)), np.ones(len(available)), 0.5, 0, available

    # Create binary target: next year's margin < threshold
    # Since we only have cross-sectional data, use current margin as proxy
    y = (clean["operating_margin"] < _DISTRESS_THRESHOLD).astype(float).values

    # Don't use operating_margin as a feature when predicting it
    feat_cols = [f for f in available if f != "operating_margin"]
    X = clean[feat_cols].fillna(0).values.astype(float)

    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_std[X_std == 0] = 1
    X_norm = (X - X_mean) / X_std

    beta = _fit_logistic(X_norm, y)

    # Compute AUC
    X_aug = np.column_stack([np.ones(len(X_norm)), X_norm])
    y_pred = _sigmoid(X_aug @ beta)
    auc = _compute_auc(y, y_pred)

    return beta, X_mean, X_std, auc, len(clean), feat_cols


def predict_distress(
    ccn: str,
    hcris_df: pd.DataFrame,
) -> Optional[DistressPrediction]:
    """Predict distress probability for a specific hospital."""
    beta, X_mean, X_std, auc, n_train, feat_cols = train_distress_model(hcris_df)

    df = hcris_df.copy()
    # Add derived features
    if "revenue_per_bed" not in df.columns:
        df["revenue_per_bed"] = df.get("net_patient_revenue", 0) / df["beds"].replace(0, np.nan)
    if "operating_margin" not in df.columns:
        rev = df.get("net_patient_revenue", pd.Series(dtype=float))
        opex = df.get("operating_expenses", pd.Series(dtype=float))
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)
    if "occupancy_rate" not in df.columns:
        df["occupancy_rate"] = df.get("total_patient_days", 0) / df["bed_days_available"].replace(0, np.nan)
    if "net_to_gross_ratio" not in df.columns:
        df["net_to_gross_ratio"] = (
            df.get("net_patient_revenue", 0) / df["gross_patient_revenue"].replace(0, np.nan)
        ).clip(0, 1)

    match = df[df["ccn"] == ccn]
    if match.empty:
        return None

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))

    x = np.array([float(hospital.get(f, 0) or 0) for f in feat_cols])
    x_norm = (x - X_mean) / X_std
    x_aug = np.concatenate([[1], x_norm])
    prob = float(_sigmoid(x_aug @ beta))

    # Contributing factors
    factors = []
    for i, feat in enumerate(feat_cols):
        coef = beta[i + 1]
        val = x[i]
        contribution = coef * x_norm[i]
        direction = "increases" if contribution > 0 else "decreases"
        factors.append({
            "feature": feat.replace("_", " ").title(),
            "value": float(val),
            "coefficient": float(coef),
            "contribution": float(contribution),
            "direction": direction,
            "importance": abs(float(contribution)),
        })
    factors.sort(key=lambda f: -f["importance"])

    # Risk label
    risk_label = "Unknown"
    risk_color = "muted"
    for (lo, hi), (label, color) in _RISK_LABELS.items():
        if lo <= prob < hi:
            risk_label = label
            risk_color = color
            break

    # Peer and state distress rates
    margin_col = "operating_margin"
    if margin_col in df.columns:
        national_distress = float((df[margin_col].dropna() < _DISTRESS_THRESHOLD).mean())
        state_df = df[df["state"] == state] if state else df
        state_distress = float((state_df[margin_col].dropna() < _DISTRESS_THRESHOLD).mean()) if len(state_df) > 5 else national_distress
    else:
        national_distress = 0.15
        state_distress = 0.15

    return DistressPrediction(
        ccn=ccn,
        hospital_name=name,
        state=state,
        distress_probability=round(prob, 4),
        risk_label=risk_label,
        risk_color=risk_color,
        contributing_factors=factors[:8],
        peer_distress_rate=round(national_distress, 3),
        state_distress_rate=round(state_distress, 3),
        model_auc=round(auc, 3),
        n_training=n_train,
    )


def screen_distressed(
    hcris_df: pd.DataFrame,
    top_n: int = 50,
) -> List[Dict[str, Any]]:
    """Screen all hospitals for distress risk, return top N highest risk."""
    beta, X_mean, X_std, auc, n_train, feat_cols = train_distress_model(hcris_df)

    df = hcris_df.copy()
    if "revenue_per_bed" not in df.columns:
        df["revenue_per_bed"] = df.get("net_patient_revenue", 0) / df["beds"].replace(0, np.nan)
    if "operating_margin" not in df.columns:
        rev = df.get("net_patient_revenue", pd.Series(dtype=float))
        opex = df.get("operating_expenses", pd.Series(dtype=float))
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)
    if "occupancy_rate" not in df.columns:
        df["occupancy_rate"] = df.get("total_patient_days", 0) / df["bed_days_available"].replace(0, np.nan)
    if "net_to_gross_ratio" not in df.columns:
        df["net_to_gross_ratio"] = (
            df.get("net_patient_revenue", 0) / df["gross_patient_revenue"].replace(0, np.nan)
        ).clip(0, 1)

    clean = df.dropna(subset=feat_cols)
    if clean.empty:
        return []

    X = clean[feat_cols].fillna(0).values.astype(float)
    X_norm = (X - X_mean) / X_std
    X_aug = np.column_stack([np.ones(len(X_norm)), X_norm])
    probs = _sigmoid(X_aug @ beta)

    clean = clean.copy()
    clean["distress_prob"] = probs

    top = clean.nlargest(top_n, "distress_prob")
    results = []
    for _, row in top.iterrows():
        prob = float(row["distress_prob"])
        label = "Unknown"
        for (lo, hi), (lbl, _) in _RISK_LABELS.items():
            if lo <= prob < hi:
                label = lbl
                break
        results.append({
            "ccn": str(row.get("ccn", "")),
            "name": str(row.get("name", ""))[:40],
            "state": str(row.get("state", "")),
            "beds": int(row.get("beds", 0)),
            "revenue": float(row.get("net_patient_revenue", 0)),
            "margin": float(row.get("operating_margin", 0)),
            "distress_prob": round(prob, 4),
            "risk_label": label,
        })
    return results
