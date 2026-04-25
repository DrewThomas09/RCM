"""Forward financial distress predictor (12-24 month horizon).

The existing ``distress_predictor.py`` is a 1-year logistic
regression on point-in-time HCRIS features. The directive asked
for *forward* distress at 12-24 months with **trends**,
**liquidity**, **debt**, and **volumes** — none of which the
existing model uses. This module fills the gap.

Approach:
  • Train Ridge regression to predict operating margin at horizon
    (12 or 24 months out) from time-series features at year t.
  • Map predicted margin to distress probability using the CV
    residual standard deviation and a margin threshold (default
    -5%, the canonical distressed-hospital line in HCRIS).
  • Continuous probability + categorical risk band (low / moderate
    / elevated / high / critical) so the partner can rank the
    universe.

Features the directive specifically calls out:
  • **Margin trends**: 3-year linear slope of operating margin
    (β from regressing margin against year). A negative slope is
    a stronger signal than negative level alone.
  • **Liquidity**: days cash on hand = cash / (annual op expenses
    / 365). Below 30 days = warning; below 15 = critical.
  • **Debt**: long-term debt / net patient revenue + interest
    coverage (EBIT / interest expense).
  • **Volumes**: discharge CAGR over the trailing 3 years.

Plus point-in-time features that complement the trends:
operating margin level, occupancy, payer mix, beds, n2g ratio.

Public API::

    predictor = train_forward_distress_predictor(
        panel_rows, horizon_months=24)
    prob, label, color, expl = predict_distress(
        predictor, hospital_panel)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .trained_rcm_predictor import (
    TrainedRCMPredictor,
    train_ridge_with_cv,
)


# Canonical feature set. Order is fixed so model files stay stable.
FORWARD_DISTRESS_FEATURES: List[str] = [
    # Margin trend signals
    "operating_margin_t",      # current margin level
    "margin_3yr_slope",        # 3yr linear slope
    "margin_3yr_volatility",   # std of trailing 3 years
    # Liquidity
    "days_cash_on_hand",
    "current_ratio",
    # Debt
    "debt_to_revenue",
    "interest_coverage",
    # Volumes
    "discharges_3yr_cagr",
    "occupancy_rate",
    # Static structural
    "beds_log",
    "medicare_day_pct",
    "medicaid_day_pct",
    "net_to_gross_ratio",
]

# Operating margin range — clamp to sane economic bounds
DISTRESS_RANGE: Tuple[float, float] = (-0.50, 0.30)

# Default distress threshold. -5% margin is the canonical line in
# HCRIS-based PE diligence; <-5% sustained is acquisition territory
# (or restructuring territory if much worse). Override per-deal.
DEFAULT_DISTRESS_THRESHOLD = -0.05

# Risk band thresholds for the partner-facing label
_RISK_BANDS: List[Tuple[float, str, str]] = [
    (0.10, "Low", "green"),
    (0.25, "Moderate", "amber"),
    (0.50, "Elevated", "orange"),
    (0.75, "High", "red"),
    (1.01, "Critical", "critical"),
]


def _safe_div(num: float, den: float, default: float = 0.0,
              ) -> float:
    if den is None or den == 0:
        return default
    return num / den


def _linear_slope(values: List[float]) -> float:
    """OLS slope of values against time index. Returns 0 for
    insufficient data — caller treats slope=0 as 'no trend'."""
    clean = [v for v in values if v is not None
             and not math.isnan(v)]
    if len(clean) < 2:
        return 0.0
    n = len(clean)
    x = np.arange(n, dtype=float)
    y = np.array(clean, dtype=float)
    x_mean = x.mean()
    y_mean = y.mean()
    num = float(np.sum((x - x_mean) * (y - y_mean)))
    den = float(np.sum((x - x_mean) ** 2))
    return num / den if den > 0 else 0.0


def _cagr(start: float, end: float, years: int) -> float:
    if start is None or end is None or start <= 0 or years <= 0:
        return 0.0
    return (end / start) ** (1.0 / years) - 1.0


def build_forward_distress_features(
    panel: Dict[str, Any],
) -> Dict[str, float]:
    """Build the canonical feature dict from a hospital panel.

    Expected ``panel`` keys (all optional with sensible defaults):
      - operating_margin_t (float, current year margin)
      - margin_history (list of 3-5 trailing-year margins)
      - cash_on_hand, annual_operating_expenses
      - current_assets, current_liabilities
      - long_term_debt, net_patient_revenue, interest_expense, ebit
      - discharges_history (list of trailing-year discharges)
      - beds, occupancy_rate, medicare_day_pct, medicaid_day_pct,
        gross_patient_revenue (for n2g)
    """
    margin_t = float(
        panel.get("operating_margin_t")
        or panel.get("operating_margin") or 0.0)
    margin_history = list(
        panel.get("margin_history") or [])
    if margin_history:
        margin_slope = _linear_slope(margin_history)
        margin_vol = (float(np.std(margin_history))
                      if len(margin_history) >= 2 else 0.0)
    else:
        margin_slope = 0.0
        margin_vol = 0.0

    cash = float(panel.get("cash_on_hand") or 0.0)
    annual_opex = float(
        panel.get("annual_operating_expenses")
        or panel.get("operating_expenses")
        or 1.0)
    daily_opex = annual_opex / 365.0
    days_cash = (cash / daily_opex
                 if daily_opex > 0 else 30.0)

    cur_assets = float(panel.get("current_assets") or 0.0)
    cur_liab = float(panel.get("current_liabilities") or 1.0)
    current_ratio = _safe_div(cur_assets, cur_liab, 1.0)

    debt = float(panel.get("long_term_debt") or 0.0)
    rev = float(panel.get("net_patient_revenue") or 1.0)
    debt_to_rev = _safe_div(debt, rev, 0.0)

    interest = float(panel.get("interest_expense") or 0.0)
    ebit = float(panel.get("ebit") or
                 (rev * margin_t))  # proxy from margin
    if interest > 0:
        interest_cov = ebit / interest
    else:
        interest_cov = 10.0  # no interest expense → safe

    disch_history = list(
        panel.get("discharges_history") or [])
    if len(disch_history) >= 2:
        years = len(disch_history) - 1
        cagr = _cagr(disch_history[0],
                     disch_history[-1], years)
    else:
        cagr = 0.0

    beds = float(panel.get("beds") or 100)
    gross = float(panel.get("gross_patient_revenue")
                  or rev * 3)
    n2g = _safe_div(rev, gross, 0.30)

    return {
        "operating_margin_t": margin_t,
        "margin_3yr_slope": margin_slope,
        "margin_3yr_volatility": margin_vol,
        "days_cash_on_hand": min(365.0, days_cash),
        "current_ratio": min(10.0, current_ratio),
        "debt_to_revenue": min(5.0, debt_to_rev),
        "interest_coverage": min(20.0, interest_cov),
        "discharges_3yr_cagr": cagr,
        "occupancy_rate": float(
            panel.get("occupancy_rate") or 0.6),
        "beds_log": float(np.log(max(1.0, beds))),
        "medicare_day_pct": float(
            panel.get("medicare_day_pct") or 0.40),
        "medicaid_day_pct": float(
            panel.get("medicaid_day_pct") or 0.15),
        "net_to_gross_ratio": n2g,
    }


def _features_to_matrix(
    rows: Iterable[Dict[str, Any]],
) -> np.ndarray:
    out = []
    for r in rows:
        f = build_forward_distress_features(r)
        out.append(
            [f[n] for n in FORWARD_DISTRESS_FEATURES])
    return np.array(out, dtype=float)


def train_forward_distress_predictor(
    panel_data: Iterable[Dict[str, Any]],
    *,
    target_field: str = "future_margin",
    horizon_months: int = 24,
    alpha: float = 1.0,
    n_folds: int = 5,
    seed: int = 42,
) -> TrainedRCMPredictor:
    """Fit forward distress predictor.

    Args:
      panel_data: rows of features at t plus target margin at
        t+horizon_months. The target field defaults to
        ``future_margin`` — caller is responsible for joining the
        future row before passing in.
      horizon_months: 12 or 24. Threaded into target_metric label.
      alpha / n_folds / seed: standard knobs.
    """
    rows = list(panel_data)
    if not rows:
        raise ValueError(
            "Cannot train on empty panel_data")
    if horizon_months not in (12, 24):
        raise ValueError(
            f"horizon_months must be 12 or 24; "
            f"got {horizon_months}")
    y = np.array([float(r[target_field]) for r in rows],
                 dtype=float)
    X = _features_to_matrix(rows)
    return train_ridge_with_cv(
        X, y,
        feature_names=FORWARD_DISTRESS_FEATURES,
        target_metric=f"future_margin_{horizon_months}mo",
        alpha=alpha,
        n_folds=n_folds,
        seed=seed,
        sanity_range=DISTRESS_RANGE,
    )


def _normal_cdf(z: float) -> float:
    """Standard-normal CDF via erf — pure stdlib."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _label_for_probability(p: float) -> Tuple[str, str]:
    for thresh, label, color in _RISK_BANDS:
        if p < thresh:
            return label, color
    return _RISK_BANDS[-1][1], _RISK_BANDS[-1][2]


def predict_distress(
    predictor: TrainedRCMPredictor,
    panel: Dict[str, Any],
    *,
    distress_threshold: float = DEFAULT_DISTRESS_THRESHOLD,
) -> Tuple[float, float, str, str,
           List[Tuple[str, float]]]:
    """Predict future operating margin and distress probability.

    Returns: (predicted_margin, distress_probability,
              risk_label, risk_color, explanation)

    distress_probability uses a normal approximation:
      P(future_margin < threshold) = Φ((threshold - μ) / σ)
    where μ = predicted margin, σ = CV residual SD (estimated from
    cv_residual_p90 / 1.282 since p90 of |residual| under
    half-normal ≈ 1.282 σ).
    """
    features = build_forward_distress_features(panel)
    yhat = predictor.predict_one(features)
    # Recover residual SD from the p90 interval.
    # For half-normal: P(|Z| < c) = 0.9 → c ≈ 1.645
    # For full-normal of residual itself: same factor 1.645.
    sigma = predictor.cv_residual_p90 / 1.645
    if sigma <= 0:
        sigma = 0.05  # defensive floor
    z = (distress_threshold - yhat) / sigma
    prob = _normal_cdf(z)
    label, color = _label_for_probability(prob)
    explanation = predictor.explain(features)
    return yhat, prob, label, color, explanation
