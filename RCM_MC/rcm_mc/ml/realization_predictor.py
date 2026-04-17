"""Bridge Realization Predictor — risk-adjusts the EBITDA bridge.

Predicts what fraction of the modeled EBITDA bridge a hospital can
actually achieve, based on observable characteristics that correlate
with RCM improvement success.

This directly changes the investment decision: a $25M bridge with
85% realization is worth more than a $30M bridge with 50% realization.

Model: Logistic regression trained on HCRIS data, using margin
outperformance vs state peers as the proxy for "can execute."
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


_FEATURES = [
    "occupancy_rate", "revenue_per_bed", "beds", "commercial_pct",
    "net_to_gross_ratio", "payer_diversity", "log_beds",
]

_FEATURE_LABELS = {
    "occupancy_rate": "Occupancy Rate",
    "revenue_per_bed": "Revenue per Bed",
    "beds": "Bed Count",
    "commercial_pct": "Commercial Payer %",
    "net_to_gross_ratio": "Net-to-Gross Ratio",
    "payer_diversity": "Payer Diversity",
    "log_beds": "Scale (Log Beds)",
}


@dataclass
class RealizationFactor:
    feature: str
    label: str
    value: float
    effect: float
    direction: str
    explanation: str


@dataclass
class RealizationPrediction:
    expected_realization: float
    confidence_interval: Tuple[float, float]
    risk_adjusted_uplift: float
    raw_uplift: float
    discount: float
    model_accuracy: float
    n_training: int
    factors: List[RealizationFactor]
    grade: str
    narrative: str


def _sigmoid(z):
    z = np.clip(z, -500, 500)
    return 1 / (1 + np.exp(-z))


def train_realization_model(
    hcris_df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, int, List[str]]:
    """Train logistic model: P(outperforms state peers on margin).

    Returns (beta, x_mean, x_std, accuracy, n, features_used).
    """
    df = hcris_df.copy()

    # Engineer features if missing
    if "log_beds" not in df.columns and "beds" in df.columns:
        df["log_beds"] = np.log(df["beds"].clip(lower=1))

    available = [f for f in _FEATURES if f in df.columns]
    if "operating_margin" not in df.columns or len(available) < 3:
        return np.zeros(len(available) + 1), np.zeros(len(available)), np.ones(len(available)), 0.5, 0, available

    clean = df.dropna(subset=["operating_margin", "state"] + available).copy()
    clean = clean[clean["operating_margin"].between(-1, 1)]
    if len(clean) < 100:
        return np.zeros(len(available) + 1), np.zeros(len(available)), np.ones(len(available)), 0.5, 0, available

    # Target: outperforms state peer median
    state_medians = clean.groupby("state")["operating_margin"].transform("median")
    y = (clean["operating_margin"] > state_medians).astype(float).values

    X = clean[available].values.astype(float)
    X = np.where(np.isnan(X), 0, X)
    x_mean = X.mean(axis=0)
    x_std = X.std(axis=0)
    x_std[x_std == 0] = 1
    X_norm = (X - x_mean) / x_std
    X_aug = np.column_stack([np.ones(len(X_norm)), X_norm])

    # Logistic regression via gradient descent
    beta = np.zeros(X_aug.shape[1])
    lr = 0.05
    for _ in range(300):
        pred = _sigmoid(X_aug @ beta)
        grad = X_aug.T @ (pred - y) / len(y)
        grad[1:] += 0.01 * beta[1:]
        beta -= lr * grad

    # Accuracy
    preds = (_sigmoid(X_aug @ beta) > 0.5).astype(float)
    accuracy = float((preds == y).mean())

    return beta, x_mean, x_std, accuracy, len(clean), available


def predict_realization(
    ccn: str,
    hcris_df: pd.DataFrame,
    bridge_uplift: float = 0,
) -> Optional[RealizationPrediction]:
    """Predict what fraction of the EBITDA bridge is achievable."""
    df = hcris_df.copy()
    if "log_beds" not in df.columns and "beds" in df.columns:
        df["log_beds"] = np.log(df["beds"].clip(lower=1))

    beta, x_mean, x_std, accuracy, n_train, feats = train_realization_model(df)

    match = df[df["ccn"] == ccn]
    if match.empty or n_train == 0:
        return None

    hospital = match.iloc[0]

    x_raw = np.array([float(hospital.get(f, 0) or 0) for f in feats])
    x_raw = np.where(np.isnan(x_raw), 0, x_raw)
    x_norm = (x_raw - x_mean) / x_std
    x_aug = np.concatenate([[1], x_norm])

    # P(outperformance) → realization fraction
    p_outperform = float(_sigmoid(x_aug @ beta))

    # Map P(outperform) to realization: 0.5 → 70%, 0.8 → 90%, 0.2 → 50%
    realization = 0.40 + p_outperform * 0.55
    realization = max(0.30, min(0.98, realization))

    # Confidence interval
    margin = 0.12
    ci_lo = max(0.20, realization - margin)
    ci_hi = min(1.0, realization + margin)

    # Risk-adjusted uplift
    risk_adj = bridge_uplift * realization
    discount = bridge_uplift - risk_adj

    # Feature factors
    factors = []
    for i, feat in enumerate(feats):
        coef = beta[i + 1]
        val = x_raw[i]
        contrib = coef * x_norm[i]

        if contrib > 0.05:
            direction = "supports"
            expl = f"Higher {_FEATURE_LABELS.get(feat, feat)} increases execution likelihood"
        elif contrib < -0.05:
            direction = "hinders"
            expl = f"{'Lower' if coef > 0 else 'Higher'} {_FEATURE_LABELS.get(feat, feat)} reduces execution likelihood"
        else:
            direction = "neutral"
            expl = f"{_FEATURE_LABELS.get(feat, feat)} has minimal effect on execution"

        factors.append(RealizationFactor(
            feature=feat,
            label=_FEATURE_LABELS.get(feat, feat),
            value=round(val, 4),
            effect=round(contrib, 4),
            direction=direction,
            explanation=expl,
        ))

    factors.sort(key=lambda f: -abs(f.effect))

    # Grade
    if realization >= 0.85:
        grade = "A"
    elif realization >= 0.70:
        grade = "B"
    elif realization >= 0.55:
        grade = "C"
    else:
        grade = "D"

    # Narrative
    top_positive = [f for f in factors if f.direction == "supports"][:2]
    top_negative = [f for f in factors if f.direction == "hinders"][:2]

    parts = [f"Expected realization: {realization:.0%} of modeled bridge."]
    if top_positive:
        parts.append(f"Strengths: {', '.join(f.label for f in top_positive)}.")
    if top_negative:
        parts.append(f"Risks: {', '.join(f.label for f in top_negative)}.")
    if bridge_uplift > 0:
        parts.append(f"Risk-adjusted uplift: ${risk_adj/1e6:.1f}M (vs ${bridge_uplift/1e6:.1f}M modeled).")

    return RealizationPrediction(
        expected_realization=round(realization, 3),
        confidence_interval=(round(ci_lo, 3), round(ci_hi, 3)),
        risk_adjusted_uplift=round(risk_adj, 0),
        raw_uplift=round(bridge_uplift, 0),
        discount=round(discount, 0),
        model_accuracy=round(accuracy, 3),
        n_training=n_train,
        factors=factors[:6],
        grade=grade,
        narrative=" ".join(parts),
    )
