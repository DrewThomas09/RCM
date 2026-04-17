"""Multi-linear regression analysis for deal diligence.

Associates want to see which variables correlate with financial
outcomes (EBITDA margin, denial rate, collection rate). This module
runs OLS regression across the portfolio to surface relationships.

Uses numpy only — no sklearn dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class RegressionCoefficient:
    variable: str
    coefficient: float
    std_error: float
    t_statistic: float
    p_value: float
    significant: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.variable,
            "coefficient": round(self.coefficient, 6),
            "std_error": round(self.std_error, 6),
            "t_statistic": round(self.t_statistic, 3),
            "p_value": round(self.p_value, 4),
            "significant": self.significant,
        }


@dataclass
class RegressionResult:
    target: str
    features: List[str]
    n_observations: int
    r_squared: float
    adjusted_r_squared: float
    coefficients: List[RegressionCoefficient]
    intercept: float
    correlation_matrix: Dict[str, Dict[str, float]]
    top_correlations: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "features": self.features,
            "n_observations": self.n_observations,
            "r_squared": round(self.r_squared, 4),
            "adjusted_r_squared": round(self.adjusted_r_squared, 4),
            "coefficients": [c.to_dict() for c in self.coefficients],
            "intercept": round(self.intercept, 6),
            "correlation_matrix": self.correlation_matrix,
            "top_correlations": self.top_correlations,
        }


def _t_dist_cdf_approx(t: float, df: int) -> float:
    """Approximate two-tailed p-value for t-distribution."""
    x = abs(t)
    if df <= 0:
        return 1.0
    a = 1.0 / (1.0 + 0.2316419 * x)
    poly = a * (0.319381530 + a * (-0.356563782 + a * (
        1.781477937 + a * (-1.821255978 + 1.330274429 * a))))
    pdf = np.exp(-0.5 * x * x) / np.sqrt(2 * np.pi)
    one_tail = pdf * poly
    return min(2 * one_tail, 1.0)


def run_regression(
    df: pd.DataFrame,
    target: str,
    features: Optional[List[str]] = None,
    significance_level: float = 0.05,
) -> RegressionResult:
    """Run OLS multi-linear regression.

    If features is None, uses all numeric columns except target.
    """
    numeric_df = df.select_dtypes(include=[np.number]).dropna()

    if target not in numeric_df.columns:
        raise ValueError(f"target {target!r} not in numeric columns")

    if features is None:
        features = [c for c in numeric_df.columns if c != target]
    features = [f for f in features if f in numeric_df.columns and f != target]

    if not features:
        raise ValueError("no valid feature columns")

    clean = numeric_df[[target] + features].dropna()
    n = len(clean)
    k = len(features)

    if n < k + 2:
        raise ValueError(f"need at least {k+2} observations, got {n}")

    y = clean[target].values.astype(float)
    X = clean[features].values.astype(float)
    X_with_intercept = np.column_stack([np.ones(n), X])

    try:
        beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        raise ValueError("singular matrix — features may be collinear")

    y_hat = X_with_intercept @ beta
    residuals = y - y_hat
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 else r2

    mse = ss_res / (n - k - 1) if n > k + 1 else 0
    try:
        var_beta = mse * np.linalg.inv(X_with_intercept.T @ X_with_intercept)
        se = np.sqrt(np.diag(var_beta))
    except np.linalg.LinAlgError:
        se = np.zeros(k + 1)

    coefficients = []
    for i, feat in enumerate(features):
        b = float(beta[i + 1])
        s = float(se[i + 1]) if i + 1 < len(se) else 0
        t_stat = b / s if s > 0 else 0
        p_val = _t_dist_cdf_approx(t_stat, n - k - 1)
        coefficients.append(RegressionCoefficient(
            variable=feat, coefficient=b, std_error=s,
            t_statistic=t_stat, p_value=p_val,
            significant=p_val < significance_level,
        ))

    corr_df = clean.corr()
    corr_matrix = {
        c: {r: round(float(corr_df.loc[c, r]), 4) for r in corr_df.columns}
        for c in corr_df.columns
    }

    all_pairs = []
    cols = list(corr_df.columns)
    for i, c1 in enumerate(cols):
        for c2 in cols[i+1:]:
            val = float(corr_df.loc[c1, c2])
            all_pairs.append({
                "var1": c1, "var2": c2,
                "correlation": round(val, 4),
                "abs_correlation": round(abs(val), 4),
            })
    all_pairs.sort(key=lambda x: -x["abs_correlation"])

    return RegressionResult(
        target=target,
        features=features,
        n_observations=n,
        r_squared=r2,
        adjusted_r_squared=adj_r2,
        coefficients=coefficients,
        intercept=float(beta[0]),
        correlation_matrix=corr_matrix,
        top_correlations=all_pairs[:15],
    )


def run_portfolio_regression(
    store: Any,
    target: str = "denial_rate",
    features: Optional[List[str]] = None,
) -> RegressionResult:
    """Run regression across the entire portfolio's deal profiles."""
    deals = store.list_deals(include_archived=True)
    if deals.empty:
        raise ValueError("no deals in portfolio")
    return run_regression(deals, target, features)
