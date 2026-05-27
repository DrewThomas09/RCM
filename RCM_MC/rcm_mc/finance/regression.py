"""Multi-linear regression analysis for deal diligence.

Associates want to see which variables correlate with financial
outcomes (EBITDA margin, denial rate, collection rate). This module
runs OLS regression across the portfolio to surface relationships.

Uses numpy only — no sklearn dependency.

DIAGNOSTIC SCOPE (Phase 1):
  The metrics surfaced here (R², RMSE, MAE, VIFs, segment fits) are
  all IN-SAMPLE explanatory fits — they describe how well the model
  fits the data it was trained on. They do NOT yet make
  out-of-sample prediction claims. Until PR 4 (cross-validation) and
  PR 3 (leakage audit — flagging features that use the target in
  their formula) land, treat these numbers as DIAGNOSTIC ONLY: useful
  for hypothesis generation and feature selection, not for sourcing
  decisions or LP-facing forecasts.
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
    # Belsley condition number of the scaled design matrix — the
    # single-number multicollinearity diagnostic (κ>100 = severe).
    condition_number: float = 0.0

    @property
    def typical_fractional_error(self) -> float:
        """A scale-free "typical multiplicative prediction error" — only
        meaningful for log-transformed fits. Computed as
        ``exp(RMSE_log) - 1``, so a return value of 0.30 means
        "typical prediction is off by ~30% in either direction"
        (e.g. a hospital's $500M NPSR predicted as $650M or $385M).

        Returns 0.0 for raw-target fits (where RMSE is already in
        the target's units and ``rmse / target_mean`` is the
        partner-facing relative error).
        """
        if not self.target_was_log_transformed:
            return 0.0
        import math as _m
        return _m.exp(self.rmse) - 1.0

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
            "condition_number": round(self.condition_number, 1),
            "typical_fractional_error": round(
                self.typical_fractional_error, 4,
            ),
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
    # Per-segment row counts (every segment present in the data,
    # including ones we couldn't fit).
    segment_counts: Dict[str, int]
    # Segments we explicitly chose NOT to fit, with the reason —
    # surfaced as a first-class field instead of just "missing
    # from by_segment" so the UI can render "Flagship Specialty:
    # 9 rows, insufficient sample for stable fit (need at least N)".
    insufficient_n: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # The actual minimum-n threshold the fit used (reflects both
    # the caller's request and the dof safety margin).
    min_n_used: int = 0

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
            "insufficient_n": self.insufficient_n,
            "min_n_used": self.min_n_used,
        }


def _t_dist_cdf_approx(t: float, df: int) -> float:
    """Two-tailed p-value for a t statistic.

    Back-compat shim: the original body was a normal-tail approximation that
    ignored ``df`` (Abramowitz–Stegun 26.2.17) and so overstated significance
    in small samples. It now delegates to the EXACT ``t_two_tailed_pvalue``;
    the name is retained only because existing call sites reference it.
    """
    return t_two_tailed_pvalue(t, df)


def _betacf(a: float, b: float, x: float) -> float:
    """Continued-fraction for the incomplete beta (Numerical Recipes)."""
    import math
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    import math
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def f_pvalue(f_stat: float, df_model: int, df_resid: int) -> float:
    """Upper-tail p-value of an F statistic — P(F > f_stat).

    Exact (to ~1e-10) via the incomplete beta, no scipy. Lets the regression
    page report the F test's verdict, not just the statistic: a tiny p-value
    next to a high F with few significant coefficients is precisely the
    multicollinearity signature — the model is jointly significant while no
    single predictor is."""
    if f_stat <= 0 or df_model < 1 or df_resid < 1:
        return 1.0
    x = df_resid / (df_resid + df_model * float(f_stat))
    return float(_betai(df_resid / 2.0, df_model / 2.0, x))


def t_two_tailed_pvalue(t_stat: float, df: int) -> float:
    """Exact two-tailed p-value of a Student-t statistic — P(|T_df| > |t|).

    Uses the incomplete beta (same machinery as ``f_pvalue``) because
    F(1, df) = t²(df), so P(|T_df| > |t|) = P(F_{1,df} > t²) = I_x(df/2, 1/2)
    with x = df/(df + t²). This is EXACT (to ~1e-10), not the normal-tail
    approximation the legacy ``_t_dist_cdf_approx`` returned — which ignored
    df entirely and so overstated significance for small samples. For a
    universe filter that leaves only n=15 hospitals, df is tiny and the
    normal approximation is materially too optimistic; this is the honest
    p-value at every sample size and converges to the normal as df→∞.
    """
    if df < 1:
        return 1.0
    t = abs(float(t_stat))
    if t == 0.0:
        return 1.0
    x = df / (df + t * t)
    return float(_betai(df / 2.0, 0.5, x))


def t_critical_value(df: int, alpha: float = 0.05) -> float:
    """Two-sided critical t value t_{df, 1-alpha/2} for confidence intervals.

    Inverts ``t_two_tailed_pvalue`` by bisection (monotone in t), so a 95%
    CI uses the correct t multiplier — 2.57 at df=5, 2.23 at df=10 — instead
    of the flat 1.96 normal value, which understates interval width (and thus
    overstates precision) for the small samples a tight universe filter
    produces. Converges to 1.96 as df→∞.
    """
    if df < 1:
        return 1.959963985
    lo, hi = 0.0, 1000.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if t_two_tailed_pvalue(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def hc1_robust_cov(
    x_with_intercept: np.ndarray, residuals: np.ndarray
) -> np.ndarray:
    """Full HC1 (White) heteroskedasticity-consistent covariance matrix.

        V = c · (XᵀX)⁻¹ (Xᵀ diag(eᵢ²) X) (XᵀX)⁻¹,   c = n / (n − p)

    The diagonal gives the robust SEs; the off-diagonals are needed for the
    robust joint Wald/F test of several coefficients at once. pinv keeps it
    stable on collinear designs.
    """
    x = np.asarray(x_with_intercept, dtype=float)
    e = np.asarray(residuals, dtype=float)
    n, kp1 = x.shape
    xtx_inv = np.linalg.pinv(x.T @ x)
    xe = x * e[:, None]            # rows scaled by their residual
    meat = xe.T @ xe              # == Xᵀ diag(e²) X
    cov = xtx_inv @ meat @ xtx_inv
    dof = max(n - kp1, 1)
    return cov * (n / dof)         # HC1 correction


def hc1_robust_se(
    x_with_intercept: np.ndarray, residuals: np.ndarray
) -> np.ndarray:
    """Heteroskedasticity-consistent (HC1) standard errors — the White
    "sandwich" estimator with the n/(n-p) small-sample correction.

    Classical OLS SEs assume the error variance is constant across
    observations. Cross-sectional hospital data almost never satisfies that
    (a $9B academic medical center and a $400K rural CAH do not share an error
    scale), so the classical t-stats/p-values overstate precision. HC1 corrects
    the covariance without assuming a variance form.

    Returns sqrt(diag(V)), clipped at 0 (pinv round-off on collinear designs can
    leave tiny negative diagonals — same guard the classical path uses).
    """
    cov = hc1_robust_cov(x_with_intercept, residuals)
    return np.sqrt(np.clip(np.diag(cov), 0.0, None))


def robust_joint_f_test(
    x_with_intercept: np.ndarray, beta: np.ndarray, residuals: np.ndarray
) -> Dict[str, Any]:
    """Heteroskedasticity-robust Wald test that all slopes are jointly zero.

    The classical overall F assumes homoskedastic errors — but the regression
    page reports robust SEs precisely because Breusch–Pagan usually finds
    heteroskedasticity on HCRIS data, which makes that classical F invalid for
    the headline "is the model jointly significant?" This is the consistent
    version: a Wald statistic on the slope vector using the HC1 covariance,

        W = b'  Σ_bb⁻¹  b   ~  χ²(p)      (b = slopes, Σ_bb = robust cov block)

    reported in F-form W/p ~ F(p, n−p−1) so it reuses the exact ``f_pvalue``
    (no chi-square needed) and is directly comparable to the classical F. The
    intercept is excluded — joint significance is about the slopes. Returns a
    dict; ``significant`` is None when undefined (too few dof / singular block).
    """
    x = np.asarray(x_with_intercept, dtype=float)
    b = np.asarray(beta, dtype=float)
    n, kp1 = x.shape
    p = kp1 - 1
    df_resid = n - kp1
    out: Dict[str, Any] = {"f_stat": 0.0, "p_value": 1.0, "df_model": max(p, 0),
                           "df_resid": max(df_resid, 0), "wald": 0.0,
                           "significant": None}
    if p < 1 or df_resid < 1:
        return out
    cov = hc1_robust_cov(x, residuals)
    cov_bb = cov[1:, 1:]                       # drop intercept row/col
    slopes = b[1:]
    try:
        wald = float(slopes @ np.linalg.pinv(cov_bb) @ slopes)
    except np.linalg.LinAlgError:
        return out
    if not np.isfinite(wald) or wald < 0:
        return out
    f_stat = wald / p
    pv = f_pvalue(f_stat, p, df_resid)
    out.update({"f_stat": float(f_stat), "p_value": float(pv),
                "wald": wald, "significant": bool(pv < 0.05)})
    return out


def breusch_pagan_test(
    x_with_intercept: np.ndarray, residuals: np.ndarray
) -> Dict[str, Any]:
    """Breusch–Pagan / Koenker test for heteroskedasticity (F-form).

    Regresses the squared residuals on the model's regressors; if they explain
    the squared residuals, the error variance depends on the predictors
    (heteroskedasticity). Uses the F-form of the auxiliary regression —
    F = (R²/k) / ((1−R²)/(n−k−1)) ~ F(k, n−k−1) — so it reuses the exact
    ``f_pvalue`` (no chi-square implementation needed) and is robust to
    non-normal errors (Koenker's studentized variant). p < 0.05 ⇒ use robust
    SEs. Returns a dict; ``heteroskedastic`` is None when undefined.
    """
    x = np.asarray(x_with_intercept, dtype=float)
    e2 = np.asarray(residuals, dtype=float) ** 2
    n, kp1 = x.shape
    k = kp1 - 1
    out: Dict[str, Any] = {"f_stat": 0.0, "p_value": 1.0, "df_model": k,
                           "df_resid": max(n - k - 1, 0), "r2_aux": 0.0,
                           "heteroskedastic": None}
    if k < 1 or n - k - 1 < 1:
        return out
    beta_aux = np.linalg.lstsq(x, e2, rcond=None)[0]
    fitted = x @ beta_aux
    ss_res = float(np.sum((e2 - fitted) ** 2))
    ss_tot = float(np.sum((e2 - e2.mean()) ** 2))
    if ss_tot <= 0:
        return out
    r2 = 1.0 - ss_res / ss_tot
    if r2 <= 0.0 or r2 >= 1.0:
        out["r2_aux"] = max(0.0, min(1.0, r2))
        out["heteroskedastic"] = False if r2 <= 0.0 else None
        return out
    f_stat = (r2 / k) / ((1.0 - r2) / (n - k - 1))
    p = f_pvalue(f_stat, k, n - k - 1)
    out.update({"f_stat": float(f_stat), "p_value": float(p), "r2_aux": float(r2),
                "heteroskedastic": bool(p < 0.05)})
    return out


def ramsey_reset_test(
    x_with_intercept: np.ndarray,
    y: np.ndarray,
    fitted: np.ndarray,
    n_powers: int = 2,
) -> Dict[str, Any]:
    """Ramsey RESET test for functional-form misspecification (F-form).

    Heteroskedasticity (Breusch–Pagan) asks whether the *error variance* is
    constant; RESET asks whether the *mean model* is the right SHAPE. It
    refits with powers of the fitted values (ŷ², ŷ³) added as regressors: if
    they jointly add explanatory power, the linear form is missing curvature /
    an interaction and the coefficients are biased. F-test of the added powers
    reuses ``f_pvalue`` (no chi-square). p < 0.05 ⇒ the linear spec is
    misspecified — consider a transform (e.g. log) or a nonlinear term.

    Powers are built from the standardized fitted values for numerical
    stability (ŷ³ on raw dollars overflows); standardizing spans the same
    column space, so the joint F is unchanged.
    """
    x = np.asarray(x_with_intercept, dtype=float)
    y = np.asarray(y, dtype=float)
    yh = np.asarray(fitted, dtype=float)
    n, kp1 = x.shape
    q = max(1, int(n_powers))
    df2 = n - (kp1 + q)
    out: Dict[str, Any] = {"f_stat": 0.0, "p_value": 1.0, "df_model": q,
                           "df_resid": max(df2, 0), "misspecified": None}
    if df2 < 1:
        return out
    sd = float(yh.std()) or 1.0
    yh_s = (yh - yh.mean()) / sd
    powers = [yh_s ** d for d in range(2, 2 + q)]
    z = np.column_stack([x] + powers)
    ss_r = float(np.sum((y - yh) ** 2))                 # restricted (original)
    beta_u = np.linalg.lstsq(z, y, rcond=None)[0]
    ss_u = float(np.sum((y - z @ beta_u) ** 2))         # unrestricted
    if ss_u <= 0 or ss_r <= ss_u:
        out["misspecified"] = False                     # powers add nothing
        return out
    f_stat = ((ss_r - ss_u) / q) / (ss_u / df2)
    p = f_pvalue(f_stat, q, df2)
    out.update({"f_stat": float(f_stat), "p_value": float(p),
                "misspecified": bool(p < 0.05)})
    return out


def jarque_bera_test(residuals: np.ndarray) -> Dict[str, Any]:
    """Jarque–Bera test for non-normality of OLS residuals.

    Completes the residual-diagnostic trio: Breusch–Pagan checks the variance,
    Ramsey RESET checks the mean shape, and JB checks the *distribution*. It
    matters because the exact small-sample t and F p-values this module reports
    are only valid if the errors are (approximately) normal — with a tight
    universe filter there's no large-sample CLT to lean on, so a skewed or
    heavy-tailed residual is the reader's cue to trust the robust SEs and the
    overall direction rather than a borderline p-value.

        JB = n/6 · (S² + (K−3)²/4)     S=skewness, K=kurtosis, JB ~ χ²(2)

    The χ²(2) survival function is exactly ``exp(−JB/2)`` (the df=2 chi-square
    is an exponential), so the p-value is exact with no approximation. Needs
    n ≥ 8 for the moment estimates to mean anything; returns ``normal: None``
    below that or for a degenerate (zero-variance) residual.
    """
    e = np.asarray(residuals, dtype=float)
    n = int(e.size)
    out: Dict[str, Any] = {"jb_stat": 0.0, "p_value": 1.0, "skewness": 0.0,
                           "kurtosis": 3.0, "normal": None}
    if n < 8:
        return out
    e = e - e.mean()
    m2 = float(np.mean(e ** 2))
    if m2 <= 0:
        return out
    skew = float(np.mean(e ** 3) / m2 ** 1.5)
    kurt = float(np.mean(e ** 4) / m2 ** 2)        # raw (normal = 3)
    jb = n / 6.0 * (skew ** 2 + (kurt - 3.0) ** 2 / 4.0)
    p = float(np.exp(-jb / 2.0))                    # exact χ²(2) survival
    out.update({"jb_stat": float(jb), "p_value": p, "skewness": skew,
                "kurtosis": kurt, "normal": bool(p >= 0.05)})
    return out


def information_criteria(
    n: int, ss_res: float, n_features: int
) -> Dict[str, float]:
    """Gaussian-OLS log-likelihood, AIC and BIC for a fitted model.

    Information criteria reward fit and penalize complexity, so they say
    whether dropping a collinear feature actually *improves* the model rather
    than just shrinking it — lower is better, and BIC penalizes extra
    parameters harder than AIC (ln n vs 2 per param), so it's the stricter
    parsimony test. Parameter count = (n_features + intercept) + 1 for the
    estimated error variance, matching the standard OLS convention.

        ln L = -n/2 · (ln 2π + ln(SSR/n) + 1)
        AIC  = 2k − 2 ln L      BIC = (ln n)·k − 2 ln L   (k = params)

    Returns NaN-free zeros for degenerate inputs (n<2 or a perfect fit, where
    ln(0) is undefined).
    """
    import math
    out = {"log_likelihood": 0.0, "aic": 0.0, "bic": 0.0, "n_params": 0}
    k = (int(n_features) + 1) + 1   # coefficients (incl. intercept) + variance
    out["n_params"] = k
    if n < 2 or ss_res <= 0:
        return out
    ll = -0.5 * n * (math.log(2.0 * math.pi) + math.log(ss_res / n) + 1.0)
    out["log_likelihood"] = float(ll)
    out["aic"] = float(2.0 * k - 2.0 * ll)
    out["bic"] = float(math.log(n) * k - 2.0 * ll)
    return out


def _subset_r2(x: np.ndarray, y: np.ndarray) -> float:
    """In-sample R² of OLS(y ~ x + intercept) for a column subset (helper)."""
    if x.shape[1] == 0:
        return 0.0
    xa = np.column_stack([np.ones(len(y)), x])
    beta = np.linalg.lstsq(xa, y, rcond=None)[0]
    resid = y - xa @ beta
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 0:
        return 0.0
    return 1.0 - float(np.sum(resid ** 2)) / ss_tot


def shapley_r2_decomposition(
    x: np.ndarray, y: np.ndarray, feature_names: List[str], max_features: int = 8
) -> Optional[List[Dict[str, Any]]]:
    """Fairly attribute the model's R² to each feature (Shapley / LMG values).

    A standardized coefficient is a *partial* effect (holding the others fixed)
    and a univariate correlation *double-counts* variance shared between
    correlated predictors — neither answers "what share of the explained
    variance does this driver actually own?". The Shapley value averages a
    feature's marginal R² contribution over every order in which features could
    enter the model, which is the unique attribution that is both fair to
    correlated predictors and exactly additive: the shares sum to the full-model
    R². For two collinear drivers with equal effect it splits their shared
    variance 50/50 rather than crediting both fully.

        φ_i = Σ_{S ⊆ N\\{i}}  |S|!(p-|S|-1)!/p! · (R²(S∪{i}) − R²(S))

    Each marginal is ≥ 0 (R² is monotone in OLS), so every share is non-negative.

    Cost is O(2^p) subset fits, so this is capped at ``max_features`` (default 8
    ⇒ 256 fits); above the cap it returns None and the caller shows nothing
    rather than an approximation. Returns a list sorted by descending share,
    each entry carrying the absolute R² share and its percent of total R².
    """
    from itertools import combinations
    from math import factorial

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    p = x.shape[1] if x.ndim == 2 else 0
    if p < 1 or p != len(feature_names) or p > max_features or len(y) <= p + 1:
        return None
    feats = list(range(p))
    # Cache R² for every subset so each is fit exactly once.
    cache: Dict[Tuple[int, ...], float] = {(): 0.0}
    for r in range(1, p + 1):
        for S in combinations(feats, r):
            cache[S] = _subset_r2(x[:, list(S)], y)
    full_r2 = cache[tuple(feats)]
    phi = np.zeros(p)
    for i in feats:
        others = [f for f in feats if f != i]
        for r in range(len(others) + 1):
            w = factorial(r) * factorial(p - r - 1) / factorial(p)
            for S in combinations(others, r):
                with_i = tuple(sorted(S + (i,)))
                phi[i] += w * (cache[with_i] - cache[tuple(sorted(S))])
    out = []
    for i, name in enumerate(feature_names):
        share = float(phi[i])
        out.append({
            "feature": name,
            "r2_share": share,
            "pct_of_r2": (share / full_r2 * 100.0) if full_r2 > 0 else 0.0,
        })
    out.sort(key=lambda d: -d["r2_share"])
    return out


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


def condition_number(features_df: pd.DataFrame) -> float:
    """Belsley condition number of the scaled design matrix.

    The single-number multicollinearity diagnostic that complements VIF:
    VIF flags *which* feature is collinear, the condition number says *how
    bad the design matrix is overall*. Columns are scaled to unit length
    (Belsley/Kuh/Welsch convention) with an intercept column added, then
    κ = σ_max / σ_min of the scaled matrix.

    Rules of thumb: κ < 30 fine · 30–100 moderate collinearity · > 100
    severe (coefficient estimates are numerically unstable and individual
    effects can't be trusted). Returns 1.0 for a degenerate input and
    ``inf`` for an exactly rank-deficient design.
    """
    clean = features_df.select_dtypes(include=[np.number]).dropna()
    if clean.shape[1] < 1 or len(clean) < 2:
        return 1.0
    X = np.column_stack([np.ones(len(clean)), clean.values.astype(float)])
    norms = np.linalg.norm(X, axis=0)
    norms[norms == 0] = 1.0
    Xs = X / norms
    sv = np.linalg.svd(Xs, compute_uv=False)
    smin = float(sv.min())
    if smin <= 1e-12:
        return float("inf")
    return float(sv.max() / smin)


def prune_collinear(
    features_df: pd.DataFrame, max_vif: float = 10.0,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Greedy stepwise VIF reduction → a stable, low-collinearity feature set.

    Iteratively drops the single highest-VIF feature until every remaining
    feature has VIF ≤ ``max_vif`` (the textbook threshold). This is the
    automated alternative to hand-curating which collinear columns to
    exclude — feed it the candidate set and it returns the parsimonious set
    whose coefficients are actually interpretable.

    Returns ``(kept_features, dropped)`` where ``dropped`` is an ordered list
    of ``{"feature", "vif", "explained_by"}`` (highest-VIF first, in drop
    order). ``explained_by`` is the 1–2 still-present features most correlated
    with the dropped one — so the UI can say *"dropped bed_days_available
    (VIF 143): nearly determined by beds, total_patient_days"* instead of an
    unexplained removal.
    """
    clean = features_df.select_dtypes(include=[np.number]).dropna()
    cols = list(clean.columns)
    dropped: List[Dict[str, Any]] = []
    while len(cols) > 1:
        vifs = compute_vif(clean[cols])
        if not vifs:
            break
        worst = max(vifs, key=lambda k: vifs[k])
        worst_vif = vifs[worst]
        if worst_vif <= max_vif:
            break
        # Which surviving features explain this one? Rank the other current
        # columns by |correlation| with the dropped feature.
        others = [c for c in cols if c != worst]
        explained_by: List[Dict[str, Any]] = []
        if others:
            try:
                corrs = clean[others].corrwith(clean[worst]).abs()
                for feat, r in corrs.sort_values(ascending=False).head(2).items():
                    if r >= 0.5:
                        explained_by.append(
                            {"feature": str(feat), "r": round(float(r), 3)})
            except Exception:  # noqa: BLE001
                explained_by = []
        dropped.append({"feature": worst,
                        "vif": (round(worst_vif, 2)
                                if worst_vif != float("inf") else None),
                        "explained_by": explained_by})
        cols.remove(worst)
    return cols, dropped


def multicollinearity_verdict(
    max_vif: float, cond: float,
) -> Dict[str, str]:
    """Plain-English multicollinearity assessment for the partner.

    Synthesizes the worst VIF and the condition number into a single
    severity + message + recommendation, so a reader who isn't a
    statistician immediately knows whether to trust the individual
    coefficients (and the headline R²) or only the joint fit.
    """
    severe = (max_vif >= 30.0) or (cond >= 100.0)
    moderate = (max_vif >= 10.0) or (cond >= 30.0)
    if severe:
        return {
            "severity": "severe",
            "message": (
                "Severe multicollinearity. Predictors are highly "
                "inter-correlated, so individual coefficients (and their "
                "signs) are numerically unstable and the headline R² is "
                "inflated — a high overall F with few individually "
                "significant coefficients is the classic tell."),
            "recommendation": (
                "Do not read individual effects. Use the optimized "
                "(VIF-pruned) feature set below, which keeps the fit "
                "honest with interpretable coefficients."),
        }
    if moderate:
        return {
            "severity": "moderate",
            "message": (
                "Moderate multicollinearity. The joint fit is usable but "
                "some coefficient standard errors are inflated, so treat "
                "individual slopes with caution."),
            "recommendation": (
                "Prefer the optimized feature set, or interpret only the "
                "coefficients whose VIF is below 10."),
        }
    return {
        "severity": "low",
        "message": ("Low multicollinearity. Predictors are sufficiently "
                    "independent that individual coefficients are "
                    "interpretable."),
        "recommendation": "Coefficients can be read directly.",
    }


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

    mse = ss_res / (n - k - 1) if n > k + 1 else 0.0
    # Coefficient standard errors via the (pseudo-)inverse of XᵀX.
    # Plain np.linalg.inv blows up on collinear designs — the HCRIS
    # feature set has VIFs in the hundreds (medicare/medicaid/commercial
    # day-% sum to 100; beds ≈ bed_days_available), so round-off puts
    # tiny NEGATIVE variances on the diagonal and np.sqrt returns NaN.
    # Those NaNs propagated as "nan" std-errors, t=0, and "not
    # significant" for every coefficient — the bug that made the
    # regression page look broken. pinv is stable under rank deficiency
    # (minimum-norm solution), and clipping the diagonal at 0 absorbs
    # the floating-point noise so every SE is a real, non-negative number.
    XtX = X_with_intercept.T @ X_with_intercept
    try:
        XtX_inv = np.linalg.pinv(XtX)
        var_diag = mse * np.clip(np.diag(XtX_inv), 0.0, None)
        se = np.sqrt(var_diag)
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
    cond = condition_number(clean[features]) if compute_vifs else 0.0

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
        condition_number=cond,
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
    dof_safety_margin: int = 10,
) -> SegmentedRegressionResult:
    """Fit one OLS per segment plus a single all-segments baseline.

    Operational answer to "academic hospitals follow a different
    revenue equation than community hospitals." For each distinct
    value of ``segment_column``, refit the same model and report
    R² / RMSE / coefficients side-by-side.

    Each segment must clear ``max(min_segment_rows, n_features +
    dof_safety_margin)`` rows to get its own fit. The
    ``dof_safety_margin`` (default 10) protects against fits with
    barely more rows than parameters — those produce inflated R²
    and unreliable coefficient SEs even when OLS doesn't outright
    fail. Segments that fail the threshold are surfaced in
    ``insufficient_n`` with the reason, not silently dropped.

    Returns a ``SegmentedRegressionResult`` with both the baseline
    (all rows, no segmentation) and the per-segment fits. Use the
    R² delta between baseline and per-segment to assess whether the
    segmentation buys explanatory power — but bear in mind this is
    IN-SAMPLE explanatory fit, not out-of-sample prediction (no
    cross-validation here; that's PR 4 of the rebuild series).
    A worse per-segment fit usually means the segment's variance
    isn't captured by the current feature set, not that the segment
    is inherently unmodellable — sub-segment-appropriate features
    (rurality / occupancy / wage index for CAHs, for example)
    typically lift those R²s.
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
    n_features = len(fit_features)
    min_n = max(min_segment_rows, n_features + dof_safety_margin)

    by_segment: Dict[str, RegressionResult] = {}
    segment_counts: Dict[str, int] = {}
    insufficient_n: Dict[str, Dict[str, Any]] = {}
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
        n_clean = int(len(sclean))
        segment_counts[seg_name] = n_clean
        if n_clean < min_n:
            insufficient_n[seg_name] = {
                "n_clean": n_clean,
                "min_required": min_n,
                "reason": (
                    f"need at least {min_n} rows after dropping NaN "
                    f"({n_features} features + {dof_safety_margin} "
                    f"degrees-of-freedom safety margin); only "
                    f"{n_clean} qualify."
                ),
            }
            continue
        try:
            by_segment[seg_name] = run_regression(
                sdf, target, fit_features,
                significance_level=significance_level,
                log_transform_target=log_transform_target,
            )
        except ValueError as exc:
            insufficient_n[seg_name] = {
                "n_clean": n_clean,
                "min_required": min_n,
                "reason": f"OLS failed: {exc}",
            }
            continue

    return SegmentedRegressionResult(
        target=target,
        features=fit_features,
        segment_column=segment_column,
        target_was_log_transformed=log_transform_target,
        baseline=baseline,
        by_segment=by_segment,
        segment_counts=segment_counts,
        insufficient_n=insufficient_n,
        min_n_used=min_n,
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
