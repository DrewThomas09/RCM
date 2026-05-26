"""Conformal-calibrated Ridge predictor with a size-gated fallback ladder.

Three branches, picked by how many comparable hospitals carry the target
metric:

- ``>= _MIN_FOR_RIDGE`` (15)  — Ridge + split conformal. Best accuracy,
  honest 90% intervals.
- ``>= _MIN_FOR_MEDIAN`` (5)  — similarity-weighted median + bootstrap
  CI. No feature leverage, but still beats a benchmark fallback when
  there's any signal.
- ``< 5``                      — benchmark P25 / P50 / P75 fallback. No
  hospital-specific information; we flag it ``LOW_CONFIDENCE``.

Why two Ridge modules (this one + :mod:`rcm_mc.ml.rcm_predictor`):
- ``rcm_predictor.py`` is the original Phase-1 predictor and stays the
  default inside :mod:`~rcm_mc.ml` for legacy callers (``backtester``
  and the CLI still import from it).
- This module is the conformal-prediction layer the Deal Analysis Packet
  uses going forward. It returns richer ``PredictedMetric`` rows
  (coverage target, reliability grade, conformal interval) than the
  original.

Both use the same closed-form numpy Ridge — no sklearn. The project's
dependency stance is "numpy + pandas + matplotlib, nothing else."
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .conformal import (
    ConformalPredictor,
    bootstrap_interval,
    percentile_interval,
    split_train_calibration,
)
from .feature_engineering import (
    _safe_float,
    derive_interaction_features,
)

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────

_MIN_FOR_RIDGE = 15
_MIN_FOR_MEDIAN = 5
#: Default α retained for back-compat callers (EnsemblePredictor default
#: argument, legacy code paths). B.1 deprecates *using* this constant
#: as the live ridge penalty — production paths now tune α per-cohort
#: via :func:`_loo_select_alpha`. Kept as a numeric default so existing
#: import sites don't break; new code should NEVER pass this to a live
#: fit. The methodology-version channel preserves which paths still
#: rely on it (see :mod:`rcm_mc.analysis.thresholds`).
_RIDGE_ALPHA = 1.0
_DEFAULT_COVERAGE = 0.90

# Relative-CI-width threshold for the CI_UNSTABLE chip. A fit lands here
# when (ci_high - ci_low) > _CI_UNSTABLE_REL_WIDTH × |point|. The 2.0
# value is a 200%-relative-width rule of thumb calibrated for unitless
# rate metrics (denial_rate, ncr, etc.). It over-fires when |point| is
# near zero — the abs(value) > 1e-9 guard in the caller avoids the
# worst pathology, but partner should treat near-zero predictions with
# extra care anyway. Tier B will replace this with a principled
# normalized stability metric (CV against per-metric baseline, or CI
# half-width / pooled residual SE). Logged in TODO_TIER_B.md.
_CI_UNSTABLE_REL_WIDTH = 2.0

# ── B.1 RidgeCV + diagnostics constants ──────────────────────────────

#: Alpha-search grid for RidgeCV LOO. logspace(-3, 3, 25) ⇒ 25 candidate
#: α values spanning 5 orders of magnitude (0.001 → 1000). Grid chosen
#: per D1 — wide enough to reach genuinely degenerate problems on both
#: ends (over-regularized → mean predictor at α=1000; under-regularized
#: → high-variance fit at α=0.001), dense enough that the LOO MSE
#: surface is sampled finely. The grid endpoints both produce
#: ALPHA_AT_BOUNDARY when selected — see _loo_select_alpha guardrail.
import numpy as _np_for_grid  # local alias to avoid module re-import cost
_ALPHA_SEARCH_GRID: "_np_for_grid.ndarray" = _np_for_grid.logspace(-3, 3, 25)
del _np_for_grid

#: Diagnostic thresholds. Each carries a literature anchor per D2:
#:   - VIF > 10:        Kutner et al. (2005), Hair et al. (2010)
#:   - Cook's D > 4/N:  Bollen & Jackman (1985)
#:   - BP p < 0.05:     Breusch & Pagan (1979); standard alpha
#:   - Leverage > 2p/N: Belsley, Kuh & Welsch (1980)
#:   - |t_slope| > 2:   ~95th percentile of Student's t for N>15
_DIAG_VIF_MAX = 10.0
_DIAG_BP_PVALUE_MAX = 0.05
_DIAG_T_SLOPE_MAX = 2.0
#: Advisory skewness threshold for the log-transform hint. |g1| > 1 is the
#: conventional "highly skewed" cutoff; we only suggest a log transform for
#: strictly-positive right-skewed targets (log is undefined for <= 0).
_SKEW_LOG_THRESH = 1.0


def _sample_skewness(y: "np.ndarray") -> float:
    """Sample skewness g1 = m3 / m2**1.5. Returns 0.0 for n<3 or zero variance
    (a symmetric/degenerate target), so it never raises on edge inputs."""
    n = y.shape[0]
    if n < 3:
        return 0.0
    yc = y - y.mean()
    m2 = float((yc ** 2).mean())
    if m2 <= 1e-18:
        return 0.0
    m3 = float((yc ** 3).mean())
    return m3 / (m2 ** 1.5)
# Cook's D and leverage thresholds depend on N and p — computed per fit.


# ── Wilson-Hilferty chi-squared survival function ────────────────────

def _wilson_hilferty_chi2_sf(x: float, df: int) -> float:
    """Approximate P(X > x) where X ~ χ²(df), without scipy.

    Uses the Wilson-Hilferty cube-root transformation
    (Johnson, Kotz & Balakrishnan 1994, *Continuous Univariate
    Distributions* vol 1 §17.6): if X ~ χ²(k), then
    ((X/k)^(1/3) - (1 - 2/(9k))) / sqrt(2/(9k)) ≈ N(0, 1).
    Precision ±0.005 in p-value for k ≥ 3 (assuming exact Φ). Our Φ is
    itself an erf approximation (Abramowitz & Stegun 7.1.26 via numpy);
    composed error has been measured against scipy.stats.chi2.sf in
    tests/test_b1_bp_precision.py — passes the ±0.01 gate at df ∈ {3, 5, 10}.

    Returns 1.0 for x ≤ 0 (entire distribution above), and falls back
    to a conservative 1e-12 for very large x (numerical underflow guard).
    """
    if x <= 0:
        return 1.0
    if df < 1:
        return 1.0  # degenerate; no diagnostic signal
    k = float(df)
    cube_root = (x / k) ** (1.0 / 3.0)
    mean = 1.0 - 2.0 / (9.0 * k)
    sd = (2.0 / (9.0 * k)) ** 0.5
    if sd <= 0:
        return 1.0
    z = (cube_root - mean) / sd
    # Φ(z) via erf; survival = 1 - Φ(z) = 0.5 * erfc(z/√2)
    from math import erfc, sqrt
    p = 0.5 * erfc(z / sqrt(2.0))
    # Floor to avoid 0.0 from numerical underflow at very large x — the
    # BP test caller will compare against α=0.05, so any value below
    # ~1e-12 is "definitely heteroscedastic" and the exact value doesn't
    # matter beyond that.
    return max(p, 1e-12)


# ── FailureReason — diagnostic channel for PredictedMetric ───────────


class FailureReason(Enum):
    """Why a PredictedMetric is diagnostically suspect.

    Set on ``PredictedMetric.failure_reason`` when the predictor's
    internal fit hit a recoverable issue or a hard data-shape failure.
    The UI chip helper (``ck_prediction_chip`` in
    :mod:`rcm_mc.ui._chartis_kit`) renders one of three visual variants
    keyed off this enum.

    A.1 scope (the seven original reasons): orchestrator and recoverable
    fit channels. B.1 adds six diagnostic variants (MULTICOLLINEAR
    through DIAGNOSTIC_SUSPECT) that fire from the new
    :meth:`_RidgeModel.diagnostics` method when the post-fit checks
    detect a partner-relevant fit pathology. All B.1 additions are
    Tier 2 (UNSTABLE_FIT, amber) — the fit ran and produced a number,
    but the diagnostics flag a reason for partner skepticism.
    """
    INSUFFICIENT_COMPARABLES = "insufficient_comparables"  # n too small for chosen method
    TARGET_FEATURES_MISSING  = "target_features_missing"   # can't build x_target vector
    NO_BENCHMARK             = "no_benchmark"               # registry has no P50 fallback
    PINV_FALLBACK            = "pinv_fallback"              # singular matrix → pinv recovery
    CI_UNSTABLE              = "ci_unstable"                # 200%+ relative CI width
    R2_NEGATIVE              = "r2_negative"                # LOO R² < 0 (worse than mean)
    FIT_EXCEPTION            = "fit_exception"              # non-recoverable solver raise
    # ── B.1 diagnostic variants ──
    MULTICOLLINEAR        = "multicollinear"        # max VIF > 10 (Kutner 2005)
    INFLUENTIAL_OUTLIER   = "influential_outlier"   # max Cook's D > 4/N (Bollen & Jackman 1985)
    HETEROSCEDASTIC       = "heteroscedastic"       # BP p < 0.05 (Breusch & Pagan 1979)
    HIGH_LEVERAGE         = "high_leverage"         # max h_ii > 2p/N (Belsley-Kuh-Welsch 1980)
    NONLINEAR_PATTERN     = "nonlinear_pattern"     # |t_slope(resid~fitted)| > 2
    DIAGNOSTIC_SUSPECT    = "diagnostic_suspect"    # ≥2 of the above fired (multi-flag composition)
    # ── B.1 alpha-search boundary guardrail ──
    ALPHA_AT_BOUNDARY     = "alpha_at_boundary"     # RidgeCV picked grid endpoint (search range too narrow or y near-constant)


# ── PredictedMetric (ridge-flavor) ───────────────────────────────────

@dataclass
class PredictedMetric:
    """One metric prediction with enough audit detail for IC review.

    Differs from :class:`rcm_mc.ml.rcm_predictor.PredictedMetric` by
    carrying a conformal coverage target + a letter reliability grade.
    """
    value: float
    method: str = "ridge_regression"   # ridge_regression | weighted_median | benchmark_fallback
    ci_low: float = 0.0
    ci_high: float = 0.0
    coverage_target: float = _DEFAULT_COVERAGE
    n_comparables_used: int = 0
    r_squared: float = 0.0
    feature_importances: Dict[str, float] = field(default_factory=dict)
    reliability_grade: str = "D"
    #: Diagnostic channel — set when the fit had a recoverable issue
    #: (e.g. pinv fallback) or unstable diagnostics (wide CI, negative
    #: LOO R²). Renders as a chip via ``ck_prediction_chip``. ``None``
    #: on a clean fit. See :class:`FailureReason`. Audit-corrected
    #: framing: the original "silent zero-fill on r_squared" framing
    #: was incomplete — the actual bug is that ``0.0`` is used as a
    #: "method N/A" sentinel by weighted_median + benchmark_fallback
    #: and is indistinguishable from a genuine zero. ``failure_reason``
    #: is the authoritative diagnostic channel; the numeric-default
    #: refactor is deferred to Tier B as a separate logical change.
    failure_reason: Optional[FailureReason] = None
    #: B.1 — cohort-tuned ridge penalty. The α value RidgeCV LOO
    #: selected from :data:`_ALPHA_SEARCH_GRID` for this specific
    #: fit. ``None`` for non-ridge methods (weighted_median,
    #: benchmark_fallback) and for legacy code paths that haven't
    #: been wired through RidgeCV yet. Partner-visible via the
    #: α-disclosure on the analysis workbench (see ProfileMetric).
    cohort_alpha: Optional[float] = None
    #: B.1 — list of contributing failure reasons when
    #: ``failure_reason == DIAGNOSTIC_SUSPECT``. Empty for
    #: single-reason fits. Renders into the chip tooltip via the
    #: AggregatedFailure pattern from A.10. Ordered tier-severity
    #: first, then signal strength within tier.
    contributing_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # asdict() preserves the Enum object — coerce to its string
        # value so JSON round-trip stays clean.
        if self.failure_reason is not None:
            d["failure_reason"] = self.failure_reason.value
        return d


# ── B.1 DiagnosticReport — output of _RidgeModel.diagnostics() ───────

@dataclass(frozen=True)
class DiagnosticReport:
    """Post-fit diagnostics on a ridge fit's cohort.

    Per D2: five orthogonal diagnostics each catch a partner-relevant
    failure mode the others miss. ``failure_reasons_fired`` is the
    derived set of FailureReason variants this report would trigger
    under the locked thresholds — ordered tier-severity first, then
    signal strength within tier (matches D2 tooltip-ordering rule).

    Fields default to safe "not fired" values so a degenerate fit
    (e.g. n < 3) returns a clean report rather than raising.
    """
    max_vif: float = 0.0
    max_cooks_d: float = 0.0
    bp_pvalue: float = 1.0
    max_leverage: float = 0.0
    resid_fit_t_slope: float = 0.0
    cooks_d_argmax: int = -1   # row index of max Cook's D, for R2_NEGATIVE-Cook's-D verify
    #: Sample skewness (g1) of the target y. 0.0 on degenerate inputs.
    target_skewness: float = 0.0
    #: Advisory only (not a FailureReason): True when the target is strictly
    #: positive and at least moderately right-skewed (g1 > _SKEW_LOG_THRESH),
    #: i.e. a log/Box-Cox transform would likely stabilize variance and improve
    #: fit. Surfaced as guidance; does NOT alter the fit or the locked Tier-2
    #: failure-reason logic.
    log_transform_suggested: bool = False

    @property
    def failure_reasons_fired(self) -> List["FailureReason"]:
        """List of B.1 FailureReason variants this report would trigger.

        Computed against the locked thresholds (D2). Order is
        tier-severity then within-tier signal strength. All five B.1
        diagnostic variants are Tier 2, so the within-tier sort
        breaks ties by "how badly does this fire" (e.g. VIF=50 ranks
        before VIF=11).
        """
        # Caller resolves N + p; we report raw stats here. The threshold
        # comparisons that depend on (N, p) get applied in _predict_ridge
        # via :meth:`failure_reasons_at`.
        raise NotImplementedError("use failure_reasons_at(n, p) — DiagnosticReport doesn't know N/p")

    def failure_reasons_at(self, n: int, p: int) -> List["FailureReason"]:
        """Apply locked thresholds at (N, p) to derive which reasons fired.

        Returns list in tier-severity → within-tier-strength order so
        the caller can drop into multi-flag composition cleanly. All
        Tier 2; severity ranking within tier uses normalized signal
        strength (vif/threshold, cooks_d/threshold, etc.) so the
        chip tooltip names the strongest signal first.
        """
        cooks_thresh = 4.0 / max(n, 1)
        leverage_thresh = 2.0 * p / max(n, 1)
        candidates: List[Tuple[float, "FailureReason"]] = []
        if self.max_vif > _DIAG_VIF_MAX:
            candidates.append((self.max_vif / _DIAG_VIF_MAX, FailureReason.MULTICOLLINEAR))
        if self.max_cooks_d > cooks_thresh:
            candidates.append((self.max_cooks_d / cooks_thresh, FailureReason.INFLUENTIAL_OUTLIER))
        if self.bp_pvalue < _DIAG_BP_PVALUE_MAX:
            # Inverted: low p = strong signal. Normalize as threshold/p.
            candidates.append((_DIAG_BP_PVALUE_MAX / max(self.bp_pvalue, 1e-12), FailureReason.HETEROSCEDASTIC))
        if self.max_leverage > leverage_thresh:
            candidates.append((self.max_leverage / leverage_thresh, FailureReason.HIGH_LEVERAGE))
        if abs(self.resid_fit_t_slope) > _DIAG_T_SLOPE_MAX:
            candidates.append((abs(self.resid_fit_t_slope) / _DIAG_T_SLOPE_MAX, FailureReason.NONLINEAR_PATTERN))
        # Sort by signal strength descending — strongest first
        candidates.sort(key=lambda t: -t[0])
        return [fr for _, fr in candidates]


# ── Ridge core (closed-form, numpy) ──────────────────────────────────

class _RidgeModel:
    """Minimal Ridge estimator with a sklearn-ish fit/predict surface.

    z-scores features internally so importances are comparable across
    columns. Not threadsafe — callers own their own instance.
    """

    def __init__(self, alpha: float = _RIDGE_ALPHA) -> None:
        self.alpha = float(alpha)
        self.coef_: np.ndarray = np.asarray([])
        self.intercept_: float = 0.0
        self.feature_mu_: np.ndarray = np.asarray([])
        self.feature_sd_: np.ndarray = np.asarray([])
        # Set to True in ``fit`` if the normal-equation solve raised
        # ``np.linalg.LinAlgError`` and we recovered via ``pinv``.
        # Read by ``_predict_ridge`` to flag PINV_FALLBACK on the
        # outgoing PredictedMetric. Reset per ``fit`` call below.
        self.used_pinv: bool = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_RidgeModel":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.shape[0] == 0 or X.shape[1] == 0:
            # No data — degenerate to a constant.
            self.coef_ = np.zeros(X.shape[1] if X.ndim == 2 else 0)
            self.intercept_ = float(y.mean()) if len(y) else 0.0
            self.feature_mu_ = np.zeros(self.coef_.shape[0])
            self.feature_sd_ = np.ones(self.coef_.shape[0])
            return self
        mu = X.mean(axis=0)
        sd = X.std(axis=0)
        sd_safe = np.where(sd > 1e-12, sd, 1.0)
        Xz = (X - mu) / sd_safe
        y_mean = float(y.mean())
        yc = y - y_mean
        A = Xz.T @ Xz + self.alpha * np.eye(Xz.shape[1])
        self.used_pinv = False
        try:
            w = np.linalg.solve(A, Xz.T @ yc)
        except np.linalg.LinAlgError:
            # Singular / near-singular design matrix. Pinv recovers
            # numerically but the resulting coefficients are unstable;
            # callers should surface this as a diagnostic chip (the
            # PINV_FALLBACK FailureReason) rather than silently use
            # the recovered fit.
            w = np.linalg.pinv(A) @ (Xz.T @ yc)
            self.used_pinv = True
        self.coef_ = w
        self.intercept_ = y_mean
        self.feature_mu_ = mu
        self.feature_sd_ = sd_safe
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        Xz = (X - self.feature_mu_) / self.feature_sd_
        return Xz @ self.coef_ + self.intercept_


def _loo_r_squared(X: np.ndarray, y: np.ndarray, alpha: float) -> float:
    """Leave-one-out R² — honest out-of-sample score. Returns 0 on <3.

    Uses the naive refit-N-times implementation. For B.1's RidgeCV
    alpha search, see :func:`_loo_r_squared_shortcut` (O(N·p²)
    hat-matrix shortcut, 30x faster at K=25 alphas).

    A.10 follow-up amendment: returns ``max(-1.0, ...)`` so negative
    R² propagates honestly. Callers that want the "clamped to 0"
    behavior (e.g. _grade) clamp downstream. The diagnostic chain
    needs to see the genuine negative value to fire R2_NEGATIVE.
    """
    n = X.shape[0]
    if n < 3:
        return 0.0
    preds = np.zeros(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        try:
            m = _RidgeModel(alpha=alpha).fit(X[mask], y[mask])
            preds[i] = m.predict(X[i])[0]
        except Exception:  # noqa: BLE001
            preds[i] = float(y.mean())
    ss_res = float(np.sum((y - preds) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 1e-12:
        return 0.0
    # B.1: return raw 1 - SS_res/SS_tot (can be negative) so R2_NEGATIVE
    # diagnostic fires honestly. Clamping to 0 was the A.1-era behavior
    # that hid the diagnostic signal. Floor at -1 to prevent
    # implausible extreme negatives from a degenerate fit dominating.
    return max(-1.0, 1.0 - ss_res / ss_tot)


def _loo_r_squared_shortcut(
    X: np.ndarray, y: np.ndarray, alpha: float,
) -> float:
    """LOO R² via the hat-matrix shortcut.

    For ridge fits, the LOO residual at row i has closed form:
        ê^{LOO}_i = ê_i / (1 - h_ii)
    where ê_i is the in-sample residual and h_ii is the i-th diagonal
    of the hat matrix H = Xz (Xzᵀ Xz + α I)⁻¹ Xzᵀ. This is
    Allen (1974) / Hastie-Tibshirani-Friedman ESL §7.10 eq 7.65.

    Cost: O(N·p²) — one fit + N divisions. Naive LOO is O(N²·p²).
    At K=25 alphas in RidgeCV, that's 30x speedup at N=30/p=10.

    Returns same scale as :func:`_loo_r_squared` (raw 1 - SS/SS_tot,
    can be negative, floored at -1). Returns 0 when n < 3 OR when the
    hat-matrix solve fails — caller should fall back to naive LOO.
    """
    n = X.shape[0]
    if n < 3 or X.shape[1] == 0:
        return 0.0
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd_safe = np.where(sd > 1e-12, sd, 1.0)
    Xz = (X - mu) / sd_safe
    y_mean = float(y.mean())
    yc = y - y_mean
    A = Xz.T @ Xz + alpha * np.eye(Xz.shape[1])
    try:
        A_inv = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        return 0.0
    # Coefficients + in-sample fit
    w = A_inv @ (Xz.T @ yc)
    y_hat_centered = Xz @ w
    resid = yc - y_hat_centered
    # Hat-matrix diagonal: h_ii = Xz[i] @ A_inv @ Xz[i].T
    # Vectorize: h = sum((Xz @ A_inv) * Xz, axis=1)
    h_diag = np.sum((Xz @ A_inv) * Xz, axis=1)
    # Guard 1 - h_ii against numerical underflow at high-leverage rows
    denom = np.clip(1.0 - h_diag, 1e-9, None)
    loo_resid = resid / denom
    ss_res = float(np.sum(loo_resid ** 2))
    ss_tot = float(np.sum(yc ** 2))
    if ss_tot <= 1e-12:
        return 0.0
    return max(-1.0, 1.0 - ss_res / ss_tot)


def _loo_select_alpha(
    X: np.ndarray, y: np.ndarray,
    grid: Optional[np.ndarray] = None,
) -> Tuple[float, bool]:
    """Select α via LOO MSE minimization across the search grid.

    Returns ``(alpha_selected, at_boundary)``. ``at_boundary`` is True
    when the selected α is the first or last grid value AND y has
    non-trivial variance (i.e. the boundary selection isn't an
    artifact of near-constant y, which would correctly drive α to
    the upper bound).

    The "y has non-trivial variance" guard implements the D2 Edge
    Case 4 ↔ Edge Case 3 distinction: near-constant y legitimately
    picks max-α (over-regularize to the mean) and shouldn't fire
    ALPHA_AT_BOUNDARY — that's correct behavior, not a search-range
    failure. Genuinely high-variance problems picking max-α DO fire
    the chip because the search grid was too narrow for the cohort.

    Cost: O(K·N·p²) for K=25 alphas via the hat-matrix shortcut.
    """
    if grid is None:
        grid = _ALPHA_SEARCH_GRID
    n = X.shape[0]
    if n < 3 or X.shape[1] == 0:
        return _RIDGE_ALPHA, False
    # Compute LOO MSE per α. Use SS_res rather than R² to avoid
    # numerical artifacts from clamping; argmin equals argmax(R²).
    best_alpha = float(grid[0])
    best_ss = float("inf")
    best_idx = 0
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd_safe = np.where(sd > 1e-12, sd, 1.0)
    Xz = (X - mu) / sd_safe
    y_mean = float(y.mean())
    yc = y - y_mean
    XtX = Xz.T @ Xz
    Xtyc = Xz.T @ yc
    eye = np.eye(Xz.shape[1])
    for i, alpha in enumerate(grid):
        A = XtX + float(alpha) * eye
        try:
            A_inv = np.linalg.inv(A)
        except np.linalg.LinAlgError:
            continue
        w = A_inv @ Xtyc
        y_hat_centered = Xz @ w
        resid = yc - y_hat_centered
        h_diag = np.sum((Xz @ A_inv) * Xz, axis=1)
        denom = np.clip(1.0 - h_diag, 1e-9, None)
        loo_resid = resid / denom
        ss = float(np.sum(loo_resid ** 2))
        if ss < best_ss:
            best_ss = ss
            best_alpha = float(alpha)
            best_idx = i
    # Boundary guard — only flag if y has non-trivial variance
    y_var = float(np.var(y))
    y_scale = float(np.mean(np.abs(y))) + 1e-9
    # "Near-constant" = relative variance < 0.01 (CV < 10%)
    is_y_near_constant = (y_var ** 0.5 / y_scale) < 0.01
    at_boundary = (best_idx == 0 or best_idx == len(grid) - 1) and not is_y_near_constant
    return best_alpha, at_boundary


def _compute_diagnostics(
    X: np.ndarray, y: np.ndarray, alpha: float,
) -> DiagnosticReport:
    """Compute the five B.1 diagnostics + return DiagnosticReport.

    Single one-time fit on (X, y). Cost: O(N·p³) dominated by VIF
    (p separate ridge fits, each O(N·p²)). At N=50/p=10, < 1ms.

    Returns a DiagnosticReport with safe defaults on degenerate inputs
    (n < 4 or empty X) — callers can call .failure_reasons_at(n, p)
    to derive which Tier 2 chips would fire under the locked thresholds.
    """
    n, p = X.shape
    if n < 4 or p == 0:
        return DiagnosticReport()
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd_safe = np.where(sd > 1e-12, sd, 1.0)
    Xz = (X - mu) / sd_safe
    y_mean = float(y.mean())
    yc = y - y_mean
    A = Xz.T @ Xz + alpha * np.eye(p)
    try:
        A_inv = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        return DiagnosticReport()
    w = A_inv @ (Xz.T @ yc)
    fitted = Xz @ w
    resid = yc - fitted
    # ── Hat-matrix diagonal (for Cook's D + leverage) ──
    h_diag = np.sum((Xz @ A_inv) * Xz, axis=1)
    max_leverage = float(np.max(h_diag))
    # σ̂² for Cook's D denominator
    sigma2 = float(np.sum(resid ** 2)) / max(n - p, 1)
    sigma2 = max(sigma2, 1e-12)
    # Cook's D per row: (resid_i² / (p · σ̂²)) × (h_ii / (1-h_ii)²)
    denom_h = np.clip((1.0 - h_diag) ** 2, 1e-12, None)
    cooks_d = (resid ** 2 / (p * sigma2)) * (h_diag / denom_h)
    cooks_d_argmax = int(np.argmax(cooks_d))
    max_cooks_d = float(cooks_d[cooks_d_argmax])
    # ── VIF per column: ridge fit of Xz[:,j] ~ Xz[:,~j] ──
    max_vif = 0.0
    if p > 1:
        for j in range(p):
            mask = np.ones(p, dtype=bool)
            mask[j] = False
            X_others = Xz[:, mask]
            y_j = Xz[:, j]
            # Ridge fit (same α — ridge VIF is correctly regularized)
            A_j = X_others.T @ X_others + alpha * np.eye(p - 1)
            try:
                A_j_inv = np.linalg.inv(A_j)
            except np.linalg.LinAlgError:
                continue
            w_j = A_j_inv @ (X_others.T @ y_j)
            yhat_j = X_others @ w_j
            ss_res_j = float(np.sum((y_j - yhat_j) ** 2))
            ss_tot_j = float(np.sum(y_j ** 2))  # y_j is already z-scored, mean ≈ 0
            if ss_tot_j > 1e-12:
                r2_j = 1.0 - ss_res_j / ss_tot_j
                if r2_j < 0.999:
                    vif_j = 1.0 / max(1.0 - r2_j, 1e-9)
                    if vif_j > max_vif:
                        max_vif = vif_j
    # ── Breusch-Pagan: regress resid² on Xz, take n*R² ~ χ²(p) ──
    bp_pvalue = 1.0
    if n > p + 2:
        u = resid ** 2
        u_mean = float(u.mean())
        u_c = u - u_mean
        # OLS regression u_c ~ Xz (no ridge here — BP is an OLS test)
        try:
            beta_bp, *_ = np.linalg.lstsq(Xz, u_c, rcond=None)
            u_hat = Xz @ beta_bp
            ss_res_bp = float(np.sum((u_c - u_hat) ** 2))
            ss_tot_bp = float(np.sum(u_c ** 2))
            if ss_tot_bp > 1e-12:
                r2_bp = 1.0 - ss_res_bp / ss_tot_bp
                lm_stat = n * max(r2_bp, 0.0)
                bp_pvalue = _wilson_hilferty_chi2_sf(lm_stat, p)
        except (np.linalg.LinAlgError, ValueError):
            pass
    # ── Residual-vs-fitted nonlinearity (RESET-style) ──
    # Regress residuals on fitted² to detect missing curvature. For
    # ridge fits, residuals are nearly orthogonal to FITTED (by
    # construction the linear component is fit), so a slope test on
    # fitted alone has very low power. Slope on fitted² catches the
    # quadratic-component-of-residual pattern that signals the linear
    # model is missing curvature (Ramsey RESET, simplified to one
    # added power).
    resid_fit_t_slope = 0.0
    if n >= 5:
        fit_squared = fitted ** 2
        fs_centered = fit_squared - float(fit_squared.mean())
        ss_x = float(np.sum(fs_centered ** 2))
        if ss_x > 1e-12:
            slope = float(np.sum(fs_centered * resid) / ss_x)
            # SE from the auxiliary regression's own residuals, not
            # the original fit's σ̂ (which understates the SE when
            # residuals are highly variable around their relationship
            # with fitted²).
            aux_resid = resid - slope * fs_centered
            aux_sigma2 = float(np.sum(aux_resid ** 2)) / max(n - 2, 1)
            slope_se = (aux_sigma2 / ss_x) ** 0.5
            if slope_se > 1e-12:
                resid_fit_t_slope = slope / slope_se
    # ── Target distribution: skewness + advisory log-transform hint ──
    skew = _sample_skewness(y)
    log_hint = bool(skew > _SKEW_LOG_THRESH and float(np.min(y)) > 0.0)
    return DiagnosticReport(
        max_vif=float(max_vif),
        max_cooks_d=max_cooks_d,
        bp_pvalue=float(bp_pvalue),
        max_leverage=max_leverage,
        resid_fit_t_slope=float(resid_fit_t_slope),
        cooks_d_argmax=cooks_d_argmax,
        target_skewness=float(skew),
        log_transform_suggested=log_hint,
    )


# ── Helpers ──────────────────────────────────────────────────────────

def _is_finite_number(v: Any) -> bool:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


def _iter_peers(comparables: Any) -> List[Dict[str, Any]]:
    """Accept a ``ComparableSet`` (packet dataclass) OR an iterable of
    peer dicts. Returns a list of peer dicts with metric fields
    flattened for downstream use.
    """
    # Duck-type: packet's ComparableSet has .peers of ComparableHospital
    peers_attr = getattr(comparables, "peers", None)
    if peers_attr is not None:
        out: List[Dict[str, Any]] = []
        for p in peers_attr:
            d = dict(getattr(p, "fields", {}) or {})
            d["similarity_score"] = float(getattr(p, "similarity_score", 1.0))
            out.append(d)
        return out
    return list(comparables or [])


def _feature_keys(known: Dict[str, Any], comparables: List[Dict[str, Any]],
                  exclude: str) -> List[str]:
    """Which known metrics are usable as features to predict ``exclude``?

    A feature is usable when the target has it AND at least half the
    comparables have it (Ridge has no native NaN handling; row-drop
    would decimate the training set otherwise).
    """
    if not comparables:
        return []
    candidate = [k for k, v in known.items()
                 if k != exclude and _is_finite_number(v)]
    out: List[str] = []
    n = len(comparables)
    for k in candidate:
        present = sum(1 for p in comparables if _is_finite_number(p.get(k)))
        if present >= max(1, n // 2):
            out.append(k)
    return out


def _assemble_xy(
    comparables: List[Dict[str, Any]],
    features: List[str],
    target: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build (X, y, weights) from peer records. Drops rows missing any
    feature or the target so Ridge sees a clean dense matrix.
    """
    X_rows: List[List[float]] = []
    y_vals: List[float] = []
    w_vals: List[float] = []
    for peer in comparables:
        y_raw = peer.get(target)
        if not _is_finite_number(y_raw):
            continue
        row: List[float] = []
        ok = True
        for f in features:
            fv = peer.get(f)
            if not _is_finite_number(fv):
                ok = False
                break
            row.append(float(fv))
        if not ok:
            continue
        X_rows.append(row)
        y_vals.append(float(y_raw))
        w_vals.append(float(peer.get("similarity_score") or 1.0))
    return (np.asarray(X_rows, dtype=float),
            np.asarray(y_vals, dtype=float),
            np.asarray(w_vals, dtype=float))


def _grade(
    method: str, n: int, r_squared: float,
    methodology_version: str = "b1-tuned-alpha",
) -> str:
    """Reliability grade combining method, cohort size, and fit quality.

    Delegates threshold-table lookup to
    :func:`rcm_mc.analysis.thresholds.reliability_grade_for` so the
    cutpoints are versioned alongside methodology changes. Default
    ``methodology_version='b1-tuned-alpha'`` matches the new live
    methodology; legacy callers (rcm_predictor backtest path) pass
    ``'pre-b1'`` to retain their original thresholds.

    Method-specific baselines (preserved):
      - benchmark_fallback → D (no hospital-specific lift)
      - weighted_median → B (n≥10) | C (else) (no feature leverage)
      - ridge_regression → compound n×r² ladder via thresholds module
    """
    from ..analysis.thresholds import reliability_grade_for
    return reliability_grade_for(method, n, r_squared, methodology_version)


# ── Per-metric prediction branches ───────────────────────────────────

def _compose_failure_reason(
    X: np.ndarray, y: np.ndarray, alpha: float,
    *,
    diag: DiagnosticReport,
    used_pinv: bool,
    alpha_at_boundary: bool,
    r2: float,
    value: float,
    ci_low: float,
    ci_high: float,
) -> Tuple[Optional[FailureReason], List[str]]:
    """Apply the D2 priority chain to derive (failure_reason, contributing_sources).

    Extracted from ``_predict_ridge`` so the EnsemblePredictor path
    can call the same composition logic when its chosen base model is
    ridge — without this extraction the same metric would get
    diagnostic chips through ``_predict_ridge`` but no chips through
    ``predict_metric_ensemble``, even though both ran the same ridge
    fit at the same α. Symmetric chip behavior across both predictor
    paths is a partner-defensibility requirement (you can be a
    thick-cohort deal one day, a thin-cohort deal the next — same
    methodology rigor either way).

    Priority chain (D2 lock):
      1. PINV_FALLBACK         (numerical instability — root cause)
      2. R2_NEGATIVE + Cook's D verify-not-assume guardrail:
         - if R²<0 AND Cook's D fires: recompute LOO R² without
           the high-Cook's-D row.
           - if R² recovers ≥0 → INFLUENTIAL_OUTLIER (single)
           - else → DIAGNOSTIC_SUSPECT(R2_NEGATIVE,
             INFLUENTIAL_OUTLIER)
         - if R²<0 alone → R2_NEGATIVE
      3. ALPHA_AT_BOUNDARY     (search grid too narrow)
      4. Multi-flag composition from diagnostics:
         - 0 fired → continue
         - 1 fired → that specific reason
         - ≥2 fired → DIAGNOSTIC_SUSPECT + contributing_sources
      5. CI_UNSTABLE           (sanity floor)

    The R2_NEGATIVE-and-Cook's-D verification (step 2) implements
    the D2 refinement: don't ASSUME the outlier caused the negative
    R²; ACTUALLY recompute without it and verify. One extra LOO fit
    in the rare double-fire case, partner-defensibility improves
    materially. See test_b1_ridge_predictor.py fixtures 4A/4B.
    """
    failure_reason: Optional[FailureReason] = None
    contributing_sources: List[str] = []
    n, p = X.shape
    diag_fired = diag.failure_reasons_at(n, p)

    if used_pinv:
        failure_reason = FailureReason.PINV_FALLBACK
    elif r2 < 0:
        cooks_thresh = 4.0 / max(n, 1)
        if diag.max_cooks_d > cooks_thresh and diag.cooks_d_argmax >= 0:
            # Verify: recompute LOO R² without the high-Cook's-D row
            mask = np.ones(n, dtype=bool)
            mask[diag.cooks_d_argmax] = False
            r2_no_outlier = _loo_r_squared_shortcut(X[mask], y[mask], alpha)
            if r2_no_outlier >= 0:
                # Hypothesis held — outlier caused negative R²
                failure_reason = FailureReason.INFLUENTIAL_OUTLIER
            else:
                # Scenario B: both true. Multi-flag composition.
                failure_reason = FailureReason.DIAGNOSTIC_SUSPECT
                contributing_sources = [
                    FailureReason.R2_NEGATIVE.value,
                    FailureReason.INFLUENTIAL_OUTLIER.value,
                ]
        else:
            failure_reason = FailureReason.R2_NEGATIVE
    elif alpha_at_boundary:
        failure_reason = FailureReason.ALPHA_AT_BOUNDARY
    elif len(diag_fired) >= 2:
        failure_reason = FailureReason.DIAGNOSTIC_SUSPECT
        contributing_sources = [fr.value for fr in diag_fired]
    elif len(diag_fired) == 1:
        failure_reason = diag_fired[0]
    elif abs(value) > 1e-9 and (ci_high - ci_low) > _CI_UNSTABLE_REL_WIDTH * abs(value):
        # CI_UNSTABLE as sanity floor — see _CI_UNSTABLE_REL_WIDTH docs
        failure_reason = FailureReason.CI_UNSTABLE

    return failure_reason, contributing_sources


def _predict_ridge(
    target: str,
    known: Dict[str, Any],
    comparables: List[Dict[str, Any]],
    coverage: float,
    seed: int,
) -> Optional[PredictedMetric]:
    """B.1: RidgeCV LOO α + 5 diagnostics + verified composition.

    Flow (replaces the A.1-era hardcoded-α path):
        1. Assemble X/y from peers
        2. _loo_select_alpha: RidgeCV LOO MSE across _ALPHA_SEARCH_GRID
           (D1). Returns (alpha, at_boundary).
        3. Fit ConformalPredictor on train/cal split with chosen alpha
        4. Predict x_target → value, ci_low, ci_high
        5. LOO R² on full X/y at chosen alpha (shortcut O(N·p²))
        6. _compute_diagnostics on full X/y → DiagnosticReport (D2)
        7. Compose failure_reason via priority chain with R2_NEGATIVE-
           and-Cook's-D verify-not-assume guardrail (D2 refinement)
        8. Return PredictedMetric with cohort_alpha + contributing_sources
    """
    features = _feature_keys(known, comparables, exclude=target)
    if not features:
        return None
    X, y, _ = _assemble_xy(
        [p for p in comparables if _is_finite_number(p.get(target))],
        features, target,
    )
    if X.shape[0] < _MIN_FOR_RIDGE or X.shape[1] == 0:
        return None

    # ── Step 2: RidgeCV α-search (D1) ──
    alpha_selected, alpha_at_boundary = _loo_select_alpha(X, y)

    # ── Step 3: ConformalPredictor at chosen α ──
    X_tr, y_tr, X_cal, y_cal = split_train_calibration(
        X, y, cal_fraction=0.30, random_state=seed,
    )
    if len(X_tr) < 3:
        return None
    cp = ConformalPredictor(
        _RidgeModel(alpha=alpha_selected), coverage=coverage,
    )
    try:
        cp.fit(X_tr, y_tr, X_cal, y_cal)
    except Exception:  # noqa: BLE001
        return None

    # ── Step 4: predict x_target ──
    try:
        x_target = np.asarray(
            [float(known[f]) for f in features], dtype=float,
        )
    except (KeyError, TypeError, ValueError):
        return None
    point, low, high = cp.predict_interval(x_target.reshape(1, -1))
    value = float(point[0])
    ci_low = float(low[0])
    ci_high = float(high[0])

    # ── Step 5: LOO R² on full X/y at chosen α (via shortcut) ──
    r2 = _loo_r_squared_shortcut(X, y, alpha_selected)
    if r2 == 0.0 and X.shape[0] >= 3:
        # Shortcut returned the "solve failed" sentinel — fall back
        # to naive LOO for an honest score.
        r2 = _loo_r_squared(X, y, alpha_selected)

    # Feature importances = |standardized coefficient|, normalized
    coefs = getattr(cp.base_model, "coef_", np.zeros(len(features)))
    abs_c = np.abs(np.asarray(coefs, dtype=float))
    total = float(abs_c.sum()) or 1.0
    importances = {f: float(abs_c[i] / total) for i, f in enumerate(features)}

    # ── Step 6: B.1 diagnostics on full X/y ──
    diag = _compute_diagnostics(X, y, alpha_selected)

    # ── Step 7: failure_reason composition via shared helper ──
    # Same _compose_failure_reason() runs from EnsemblePredictor when
    # its chosen base model is ridge — symmetric chip behavior across
    # both predictor paths per D4 partner-defensibility lock.
    failure_reason, contributing_sources = _compose_failure_reason(
        X, y, alpha_selected,
        diag=diag,
        used_pinv=bool(getattr(cp.base_model, "used_pinv", False)),
        alpha_at_boundary=alpha_at_boundary,
        r2=r2,
        value=value,
        ci_low=ci_low,
        ci_high=ci_high,
    )

    return PredictedMetric(
        value=value,
        method="ridge_regression",
        ci_low=ci_low,
        ci_high=ci_high,
        coverage_target=coverage,
        n_comparables_used=int(X.shape[0]),
        r_squared=float(r2),
        feature_importances=importances,
        reliability_grade=_grade("ridge_regression", int(X.shape[0]), r2),
        failure_reason=failure_reason,
        cohort_alpha=float(alpha_selected),
        contributing_sources=contributing_sources,
    )


def _predict_weighted_median(
    target: str,
    comparables: List[Dict[str, Any]],
    coverage: float,
    seed: int,
) -> Optional[PredictedMetric]:
    pool = [p for p in comparables if _is_finite_number(p.get(target))]
    n = len(pool)
    if n < _MIN_FOR_MEDIAN:
        return None
    values = np.asarray([float(p[target]) for p in pool], dtype=float)
    weights = np.asarray([float(p.get("similarity_score") or 1.0) for p in pool],
                         dtype=float)
    point, low, high = bootstrap_interval(
        values, weights,
        coverage=coverage,
        statistic="weighted_median",
        random_state=seed,
    )
    return PredictedMetric(
        value=float(point),
        method="weighted_median",
        ci_low=float(low),
        ci_high=float(high),
        coverage_target=coverage,
        n_comparables_used=n,
        r_squared=0.0,
        feature_importances={},
        reliability_grade=_grade("weighted_median", n, 0.0),
    )


def _predict_benchmark_fallback(
    target: str,
    metric_registry: Dict[str, Dict[str, Any]],
) -> Optional[PredictedMetric]:
    meta = (metric_registry or {}).get(target) or {}
    p25 = _safe_float(meta.get("benchmark_p25"))
    p50 = _safe_float(meta.get("benchmark_p50"))
    p75 = _safe_float(meta.get("benchmark_p75"))
    if p50 is None:
        return None
    point, low, high = percentile_interval(
        p25 if p25 is not None else p50,
        p50,
        p75 if p75 is not None else p50,
    )
    return PredictedMetric(
        value=float(point),
        method="benchmark_fallback",
        ci_low=float(low),
        ci_high=float(high),
        coverage_target=_DEFAULT_COVERAGE,
        n_comparables_used=0,
        r_squared=0.0,
        feature_importances={},
        reliability_grade="D",
    )


# ── Public API ───────────────────────────────────────────────────────

def predict_missing_metrics(
    known_metrics: Dict[str, Any],
    comparables: Any,
    metric_registry: Dict[str, Dict[str, Any]],
    *,
    coverage: float = _DEFAULT_COVERAGE,
    seed: int = 42,
) -> Dict[str, PredictedMetric]:
    """Predict every metric in ``metric_registry`` the target is missing.

    Parameters
    ----------
    known_metrics
        The target hospital's observed metrics + demographics
        (``bed_count``, ``region``, ``payer_mix``). Non-numeric entries
        are passed through the interaction-feature derivation but don't
        enter the Ridge X matrix directly.
    comparables
        Either a :class:`~rcm_mc.analysis.packet.ComparableSet` or a
        list of peer dicts with a ``similarity_score`` key.
    metric_registry
        :data:`rcm_mc.analysis.completeness.RCM_METRIC_REGISTRY` or a
        compatible dict. Drives which metrics get predicted and
        provides the benchmark percentiles for the fallback branch.
    coverage
        Target coverage for conformal + bootstrap intervals (default 0.90).
    seed
        RNG seed for the train/cal split and bootstrap resampling.
        Deterministic output across runs when the inputs are unchanged.
    """
    peers = _iter_peers(comparables)

    # Fold interaction features into both the target and each peer so
    # Ridge can use ``revenue_per_bed`` et al as first-class features.
    enriched_known = dict(known_metrics or {})
    enriched_known.update(derive_interaction_features(enriched_known))
    enriched_peers: List[Dict[str, Any]] = []
    for p in peers:
        q = dict(p)
        q.update(derive_interaction_features(q))
        enriched_peers.append(q)

    out: Dict[str, PredictedMetric] = {}
    for metric in sorted(metric_registry or {}):
        if metric in known_metrics and _is_finite_number(known_metrics[metric]):
            # Already observed; nothing to predict.
            continue
        # Skip non-numeric registry entries that were added for
        # categorical demographics (state, city) — those aren't in the
        # user-facing completeness registry but guard anyway.
        if metric_registry.get(metric, {}).get("unit") == "dollars":
            # Dollar quantities (net_revenue, gross_revenue, current_ebitda,
            # total_operating_expenses) are financial inputs partners
            # supply — never predict them from comparables.
            continue

        pred: Optional[PredictedMetric] = None
        try:
            # Prompt 29: when the cohort is ≥ 15 we run the ensemble,
            # which picks the lowest-MAE base model per metric.
            # Smaller cohorts still use Ridge (already conservative
            # at low n) so we don't fit k-NN / median on data that
            # can't support them.
            from .ensemble_predictor import predict_metric_ensemble
            try:
                pred = predict_metric_ensemble(
                    metric, enriched_known, enriched_peers,
                    coverage=coverage, seed=seed,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "ensemble failed on %s; falling back to ridge: %s",
                    metric, exc,
                )
                pred = None
            if pred is None:
                pred = _predict_ridge(metric, enriched_known, enriched_peers,
                                      coverage, seed)
            if pred is None:
                pred = _predict_weighted_median(metric, enriched_peers,
                                                coverage, seed)
            if pred is None:
                pred = _predict_benchmark_fallback(metric, metric_registry)
        except Exception as exc:  # noqa: BLE001
            logger.debug("prediction for %s failed: %s", metric, exc)
            continue
        if pred is None:
            continue
        out[metric] = pred
    return out


def to_packet_predicted_metric(
    rp: PredictedMetric,
    *,
    upstream: Optional[List[str]] = None,
):
    """Convert this module's :class:`PredictedMetric` to the packet-wire
    :class:`rcm_mc.analysis.packet.PredictedMetric`. Avoids a hard
    import cycle — we delay the import to call time.

    Prompt 29: the ensemble path stashes ``_model_selection`` on the
    local ``PredictedMetric`` as an instance attribute. We thread it
    through to the packet's ``model_selection`` field so the
    workbench can show "Ridge picked" vs "k-NN picked" per metric.
    """
    from ..analysis.packet import PredictedMetric as PacketPM
    model_selection = str(
        getattr(rp, "_model_selection", "") or rp.method or ""
    )
    # Propagate the diagnostic channel — packet stores the enum's
    # string value (not the Enum itself) for clean JSON round-trip.
    # Older packets serialized before A.1 won't have this field;
    # packet PredictedMetric.from_dict defaults it to None.
    failure_reason_str = (
        rp.failure_reason.value if rp.failure_reason is not None else None
    )
    return PacketPM(
        value=float(rp.value),
        ci_low=float(rp.ci_low),
        ci_high=float(rp.ci_high),
        method=str(rp.method),
        r_squared=float(rp.r_squared),
        n_comparables_used=int(rp.n_comparables_used),
        feature_importances=dict(rp.feature_importances or {}),
        provenance_chain=list(upstream or []),
        coverage_target=float(rp.coverage_target),
        reliability_grade=str(rp.reliability_grade),
        model_selection=model_selection,
        failure_reason=failure_reason_str,
        # B.1 — propagate α + contributing_sources for workbench
        # α-disclosure and multi-flag chip tooltip
        cohort_alpha=getattr(rp, "cohort_alpha", None),
        contributing_sources=list(getattr(rp, "contributing_sources", []) or []),
    )
