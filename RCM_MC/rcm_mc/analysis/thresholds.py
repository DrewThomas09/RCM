"""Methodology-versioned threshold tables for B.1.

B.1 introduces per-cohort RidgeCV α tuning, which shifts the
distribution of LOO R² upward (less overfit penalty under tuned
regularization). Existing R² thresholds for quality / reliability /
backtest-grade / validation-grade were calibrated against the
α=1.0 distribution. Recalibrating them to preserve the categorical
distribution under tuned-α is D6.

This module centralizes the threshold tables keyed on
``methodology_version`` so every renderer that derives a categorical
signal from R² (quality bar, reliability grade, validation letter
grade, backtest passing-fits cutoff) looks them up here. A future
B.1+1 PR that adjusts thresholds touches one file.

**Initial threshold values are simulation-informed guesses pending
the corpus recalibration run.** Per D6 deploy plan, the methodology
doc lands first with placeholder values; the actual
distribution-preserving recalibration runs after one week of
production observation; updated thresholds replace these in a
follow-up PR. The placeholders are conservative shifts of +0.05 to
+0.10 above the pre-B.1 thresholds — picked to track the typical
LOO R² shift reported for RidgeCV LOO vs fixed-α on small-N
regression problems (Hastie/Tibshirani 2008 simulation).
"""
from __future__ import annotations

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


#: Methodology versions in chronological order. The "most recent
#: known" is used as the fallback when a renderer sees an unknown
#: version (forward-compat with future B.X PRs that introduce new
#: tags before this dict gets updated).
_METHODOLOGY_VERSIONS_ORDERED: Tuple[str, ...] = (
    "pre-b1",
    "b1-tuned-alpha",
)

_MOST_RECENT_VERSION = _METHODOLOGY_VERSIONS_ORDERED[-1]


# ── Quality label thresholds (high / medium / low) ────────────────
#
# Used by :func:`rcm_mc.analysis.packet_builder._merge_rcm_profile`
# to derive ProfileMetric.quality from r_squared. Drives the
# quality bar visual on the analysis workbench.

_QUALITY_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    # (high_min, medium_min) — r² ≥ high_min → "high"; ≥ medium_min → "medium"
    "pre-b1":         (0.5, 0.2),   # original A.1-era thresholds
    "b1-tuned-alpha": (0.6, 0.3),   # +0.10 / +0.10 placeholder
}


def quality_label_for(r_squared: float, methodology_version: str) -> str:
    """Map r_squared → 'high' | 'medium' | 'low' using version-specific thresholds.

    Unknown version falls back to most-recent-known with a logged
    warning (don't crash, don't silently regress to pre-b1).
    """
    thresholds = _QUALITY_THRESHOLDS.get(methodology_version)
    if thresholds is None:
        logger.warning(
            "unknown methodology_version=%r in quality_label_for; "
            "falling back to %r thresholds",
            methodology_version, _MOST_RECENT_VERSION,
        )
        thresholds = _QUALITY_THRESHOLDS[_MOST_RECENT_VERSION]
    high_min, medium_min = thresholds
    if r_squared >= high_min:
        return "high"
    if r_squared >= medium_min:
        return "medium"
    return "low"


# ── Reliability grade thresholds (A / B / C / D) for ridge_predictor._grade ──
#
# Used by :func:`rcm_mc.ml.ridge_predictor._grade` for the workbench
# reliability_grade column. Compound thresholds: each tier requires
# both minimum n AND minimum r². Below the C threshold → D.

_RELIABILITY_GRADE_THRESHOLDS: Dict[str, Tuple[Tuple[int, float], ...]] = {
    # ((n_A, r2_A), (n_B, r2_B), (n_C, r2_C))
    "pre-b1": (
        (30, 0.60),
        (20, 0.45),
        (15, 0.25),
    ),
    "b1-tuned-alpha": (
        (30, 0.65),   # +0.05 placeholder
        (20, 0.50),   # +0.05 placeholder
        (15, 0.30),   # +0.05 placeholder
    ),
}


def reliability_grade_for(
    method: str, n: int, r_squared: float,
    methodology_version: str,
) -> str:
    """Map (method, n, r²) → A/B/C/D using version-specific thresholds.

    Method-specific baseline (preserved from A.1 _grade logic):
      - benchmark_fallback always D
      - weighted_median capped at B (n≥10) or C (else)
      - ridge_regression uses the compound n×r² ladder
    """
    if method == "benchmark_fallback":
        return "D"
    if method == "weighted_median":
        return "B" if n >= 10 else "C"
    # ridge_regression
    tiers = _RELIABILITY_GRADE_THRESHOLDS.get(methodology_version)
    if tiers is None:
        logger.warning(
            "unknown methodology_version=%r in reliability_grade_for; "
            "falling back to %r",
            methodology_version, _MOST_RECENT_VERSION,
        )
        tiers = _RELIABILITY_GRADE_THRESHOLDS[_MOST_RECENT_VERSION]
    (n_a, r2_a), (n_b, r2_b), (n_c, r2_c) = tiers
    if n >= n_a and r_squared >= r2_a:
        return "A"
    if n >= n_b and r_squared >= r2_b:
        return "B"
    if n >= n_c and r_squared >= r2_c:
        return "C"
    return "D"


# ── Backtest passing-fits cutoff (A/B/C/D/F) for backtester._grade ──
#
# Used by :func:`rcm_mc.ml.backtester._grade` for the cohort-backtest
# letter grade. backtest_predictions() routes through ridge_predictor
# (B.1-affected); the legacy backtest() routes through rcm_predictor
# (Phase-1 unaffected). Both pass the appropriate methodology_version
# so each gets the correctly-calibrated grade.

_BACKTEST_GRADE_CUTS: Dict[str, Tuple[Tuple[float, str], ...]] = {
    "pre-b1": (
        (0.75, "A"),
        (0.60, "B"),
        (0.45, "C"),
        (0.25, "D"),
    ),
    "b1-tuned-alpha": (
        (0.80, "A"),    # +0.05 placeholder
        (0.65, "B"),    # +0.05 placeholder
        (0.50, "C"),    # +0.05 placeholder
        (0.30, "D"),    # +0.05 placeholder
    ),
}


def backtest_grade_for(r_squared: float, methodology_version: str) -> str:
    cuts = _BACKTEST_GRADE_CUTS.get(methodology_version)
    if cuts is None:
        logger.warning(
            "unknown methodology_version=%r in backtest_grade_for; "
            "falling back to %r",
            methodology_version, _MOST_RECENT_VERSION,
        )
        cuts = _BACKTEST_GRADE_CUTS[_MOST_RECENT_VERSION]
    for cut, letter in cuts:
        if r_squared >= cut:
            return letter
    return "F"


# ── Validation page letter grade (A/B/C/D) for compute_metric_performance ──
#
# Used by :func:`rcm_mc.ml.prediction_ledger.compute_metric_performance`
# for the /models/validation per-metric letter grade. Compound:
# A requires both R² and coverage minimums; B same; C r² only;
# else D.

_VALIDATION_GRADE_THRESHOLDS: Dict[str, Tuple[Tuple[float, float], Tuple[float, float], float]] = {
    # ((r2_A, cov_A), (r2_B, cov_B), r2_C)
    "pre-b1": (
        (0.70, 0.85),
        (0.50, 0.75),
        0.30,
    ),
    "b1-tuned-alpha": (
        (0.75, 0.85),    # +0.05 r² placeholder; coverage threshold unchanged (conformal still claims 0.90)
        (0.55, 0.75),    # +0.05 r² placeholder
        0.35,             # +0.05 r² placeholder
    ),
}


def validation_grade_for(
    r_squared: float, coverage_rate: float, methodology_version: str,
) -> str:
    thresholds = _VALIDATION_GRADE_THRESHOLDS.get(methodology_version)
    if thresholds is None:
        logger.warning(
            "unknown methodology_version=%r in validation_grade_for; "
            "falling back to %r",
            methodology_version, _MOST_RECENT_VERSION,
        )
        thresholds = _VALIDATION_GRADE_THRESHOLDS[_MOST_RECENT_VERSION]
    (r2_a, cov_a), (r2_b, cov_b), r2_c = thresholds
    if r_squared >= r2_a and coverage_rate >= cov_a:
        return "A"
    if r_squared >= r2_b and coverage_rate >= cov_b:
        return "B"
    if r_squared >= r2_c:
        return "C"
    return "D"


# ── Validation page color bins (color cells on /models/validation) ──
#
# Used by :func:`rcm_mc.ui.model_validation_page` to color the per-metric
# R² cell. cad-pos / cad-warn / cad-neg based on r² band.

_VALIDATION_COLOR_BINS: Dict[str, Tuple[float, float]] = {
    # (pos_min, warn_min) — r² ≥ pos_min → green; ≥ warn_min → amber; else red
    "pre-b1":         (0.5, 0.3),
    "b1-tuned-alpha": (0.55, 0.35),   # +0.05 placeholder
}


def validation_color_class_for(r_squared: float, methodology_version: str) -> str:
    bins = _VALIDATION_COLOR_BINS.get(methodology_version)
    if bins is None:
        logger.warning(
            "unknown methodology_version=%r in validation_color_class_for; "
            "falling back to %r",
            methodology_version, _MOST_RECENT_VERSION,
        )
        bins = _VALIDATION_COLOR_BINS[_MOST_RECENT_VERSION]
    pos_min, warn_min = bins
    if r_squared > pos_min:
        return "cad-pos"
    if r_squared > warn_min:
        return "cad-warn"
    return "cad-neg"
