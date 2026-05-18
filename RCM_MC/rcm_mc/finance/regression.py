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
    # Phase 1: error magnitudes are partner-facing (the original
    # regression page surfaces RMSE next to the target mean so the
    # reader can tell whether the error is "small fraction of mean"
    # or "as big as mean"). Adding MAE so the log-transformed fits
    # have a comparable scale-free number.
    rmse: float = 0.0
    mae: float = 0.0
    # Phase 1: target_mean is needed to interpret RMSE — partner
    # reading "$218.8M RMSE" only knows it's a disaster if they
    # also see "$254.8M target mean". Bundling it on the result
    # so callers don't have to compute it twice.
    target_mean: float = 0.0
    target_was_log_transformed: bool = False
    # Phase 1: VIF for each feature (variance inflation factor).
    # VIF > 10 is the classic threshold for "drop this feature, it's
    # collinear with the others". Empty dict means VIF wasn't
    # computed (e.g. matrix was singular).
    vifs: Dict[str, float] = field(default_factory=dict)

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
            "rmse": round(self.rmse, 4),
            "mae": round(self.mae, 4),
            "target_mean": round(self.target_mean, 4),
            "target_was_log_transformed": self.target_was_log_transformed,
            "vifs": {k: round(v, 3) for k, v in self.vifs.items()},
        }


@dataclass
class SegmentedRegressionResult:
    """Per-segment regression fits side-by-side with the all-segments
    baseline. Built by ``run_segmented_regression``.

    Lets the regression page answer the question the user's plan
    raises: do flagship academic hospitals, rural CAHs, and community
    hospitals follow the same revenue equation, or do their slopes
    differ enough that one blind regression hides the structure?

    A segment whose fit is dramatically better than the all-segments
    baseline confirms the "different economic regime" hypothesis;
    a segment whose fit barely moves means the global slopes were
    fine for it already.
    """
    target: str
    features: List[str]
    segment_column: str
    target_was_log_transformed: bool
    # The "Model 1" all-segments baseline — same data, no segmentation.
    baseline: "RegressionResult"
    # The "Model 3" per-segment fits, keyed by segment label.
    by_segment: Dict[str, "RegressionResult"]
    # Per-segment row counts (segments with too few rows to fit are
    # dropped from ``by_segment`` but still recorded here so the UI
    # can show "segment X: 4 rows, fit skipped").
    segment_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "features": self.features,
            "segment_column": self.segment_column,
            "target_was_log_transformed": self.target_was_log_transformed,
            "baseline": self.baseline.to_dict(),
            "by_segment": {
                seg: res.to_dict() for seg, res in self.by_segment.items()
            },
            "segment_counts": self.segment_counts,
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


def compute_vif(features_df: pd.DataFrame) -> Dict[str, float]:
    """Variance Inflation Factor per feature column.

    VIF(j) = 1 / (1 - R²_j) where R²_j is the R² from regressing
    feature j on every other feature. Rule of thumb: VIF > 10 means
    feature j is mostly explainable by the others and should be
    dropped or merged. The current /portfolio/regression model is
    showing VIFs of 999 (medicare/medicaid/commercial day-percent
    sum to 100, so the third is determined by the other two) and
    143 (beds vs bed_days_available, which are mechanically related
    via fiscal-year length); both are textbook collinearity that
    bloats coefficient standard errors and makes individual
    coefficients meaningless.

    Returns ``{feature: VIF}`` with VIF = ``float('inf')`` for any
    feature whose helper-regression is singular. Empty dict if the
    input has fewer than 2 features (VIF needs another feature on
    the RHS).
    """
    clean = features_df.select_dtypes(include=[np.number]).dropna()
    cols = list(clean.columns)
    if len(cols) < 2:
        return {}
    n = len(clean)
    vifs: Dict[str, float] = {}
    for j, feat in enumerate(cols):
        y = clean[feat].values.astype(float)
        others = [c for c in cols if c != feat]
        X = clean[others].values.astype(float)
        X_intercept = np.column_stack([np.ones(n), X])
        try:
            beta = np.linalg.lstsq(X_intercept, y, rcond=None)[0]
            y_hat = X_intercept @ beta
            ss_res = float(np.sum((y - y_hat) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            if r2 >= 0.99999:
                vifs[feat] = float("inf")
            else:
                vifs[feat] = 1.0 / max(1.0 - r2, 1e-9)
        except np.linalg.LinAlgError:
            vifs[feat] = float("inf")
    return vifs


def run_regression(
    df: pd.DataFrame,
    target: str,
    features: Optional[List[str]] = None,
    significance_level: float = 0.05,
    *,
    log_transform_target: bool = False,
    compute_vifs: bool = True,
) -> RegressionResult:
    """Run OLS multi-linear regression.

    If features is None, uses all numeric columns except target.

    ``log_transform_target`` fits the model on ``ln(target)`` instead
    of raw values. The current /portfolio/regression page predicts
    Net Patient Revenue in raw dollars, where the target spans
    several hundred thousand to ~$9B — OLS in that space gives the
    largest hospitals overwhelming weight on the loss and the model
    ends up explaining "which hospital is biggest" rather than
    "what predicts revenue intensity". Log-transforming switches
    the question to percentage differences, which makes the rural-
    vs-academic comparison meaningful. Coefficients on a
    log-transformed target are interpreted as semi-elasticities
    (a one-unit change in feature → β fractional change in target).

    ``compute_vifs`` adds variance-inflation factors for every
    feature so the partner sees which slopes are unreliable due to
    collinearity. On by default; turn off for hot-path callers.
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
    # Log transform requires strictly positive target — drop rows
    # whose target is <= 0 so np.log doesn't return -inf / NaN.
    if log_transform_target:
        clean = clean[clean[target] > 0]
    n = len(clean)
    k = len(features)

    if n < k + 2:
        raise ValueError(f"need at least {k+2} observations, got {n}")

    y_raw = clean[target].values.astype(float)
    y = np.log(y_raw) if log_transform_target else y_raw
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

    # Error metrics — reported in the FIT space (raw $ for an
    # untransformed fit, log units for a log fit). A naive
    # exp(y_hat) back-transform amplifies error asymmetrically
    # (Jensen's inequality: exp(0.6) - 1 = 82%, not a 0.6 dollar
    # difference) so we'd be quoting numbers that look catastrophic
    # but don't reflect prediction quality. Log-space RMSE is
    # already an interpretable number: RMSE_log = 0.3 ↔ typical
    # prediction error is a factor of exp(0.3) ≈ 1.35x (i.e. ~35%).
    #
    # ``target_mean`` is reported on the FIT space too (mean of
    # ln(y) for a log fit) so RMSE / target_mean is a like-for-like
    # comparison. UI code that needs the raw-dollar mean can read
    # it off the underlying frame.
    if log_transform_target:
        err = y - y_hat  # both in log space
        target_mean = float(np.mean(y))
    else:
        err = y - y_hat
        target_mean = float(np.mean(y_raw))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))

    vifs = compute_vif(clean[features]) if compute_vifs else {}

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
        rmse=rmse,
        mae=mae,
        target_mean=target_mean,
        target_was_log_transformed=log_transform_target,
        vifs=vifs,
    )


def run_segmented_regression(
    df: pd.DataFrame,
    target: str,
    features: Optional[List[str]] = None,
    *,
    segment_column: str = "segment_label",
    log_transform_target: bool = False,
    significance_level: float = 0.05,
    min_segment_rows: int = 30,
) -> SegmentedRegressionResult:
    """Fit one OLS per segment plus a single all-segments baseline.

    This is the operational answer to "academic hospitals follow a
    different revenue equation than community hospitals." For each
    distinct value of ``segment_column``, refit the same model and
    report R² / RMSE / coefficients side-by-side. Segments below
    ``min_segment_rows`` are skipped (not enough data for a stable
    fit) but their row count is still surfaced so the UI can show
    why a particular segment is missing.

    Returns a ``SegmentedRegressionResult`` with both the baseline
    (all rows, no segmentation) and the per-segment fits. Use the
    delta between baseline R² and segment R² to assess whether the
    segmentation actually buys you explanatory power.
    """
    if segment_column not in df.columns:
        raise ValueError(
            f"segment_column {segment_column!r} not in DataFrame; "
            "did you forget to call hospital_taxonomy.derive_taxonomy?"
        )

    baseline = run_regression(
        df, target, features,
        significance_level=significance_level,
        log_transform_target=log_transform_target,
    )

    # Use the features the baseline actually fit (in case features=None)
    fit_features = baseline.features

    by_segment: Dict[str, RegressionResult] = {}
    segment_counts: Dict[str, int] = {}
    for seg, sdf in df.groupby(segment_column, dropna=True):
        seg_name = str(seg)
        # Count rows that would survive the same dropna+target>0
        # filter the baseline applied — that's the row budget the
        # per-segment fit has to work with.
        sclean = sdf[[c for c in [target] + fit_features
                      if c in sdf.columns]].apply(
            pd.to_numeric, errors="coerce"
        ).dropna()
        if log_transform_target:
            sclean = sclean[sclean[target] > 0]
        segment_counts[seg_name] = int(len(sclean))
        if len(sclean) < max(min_segment_rows, len(fit_features) + 2):
            continue
        try:
            by_segment[seg_name] = run_regression(
                sdf, target, fit_features,
                significance_level=significance_level,
                log_transform_target=log_transform_target,
            )
        except ValueError:
            # Singular matrix in this segment — skip rather than
            # poison the whole result. UI surfaces "fit_skipped".
            continue

    return SegmentedRegressionResult(
        target=target,
        features=fit_features,
        segment_column=segment_column,
        target_was_log_transformed=log_transform_target,
        baseline=baseline,
        by_segment=by_segment,
        segment_counts=segment_counts,
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
