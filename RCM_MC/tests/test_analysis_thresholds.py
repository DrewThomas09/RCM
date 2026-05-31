"""Tests for the methodology-versioned threshold tables.

`rcm_mc/analysis/thresholds.py` ships 5 pure categorical-grade
functions that turn R² (and sometimes coverage) into the letter
grades and color bins shown to partners across the workbench,
validation page, and backtester. The functions are versioned (the
'pre-b1' methodology used different cutpoints from the current
'b1-tuned-alpha') and have an explicit "unknown-version → fallback
to most-recent" path with a log warning.

Pure-logic with multiple downstream renderers + silent-shift risk if
a threshold moves → exactly the kind of function that needs unit
coverage. No direct test references existed before this file.
"""
from __future__ import annotations

import logging
import unittest

from rcm_mc.analysis.thresholds import (
    backtest_grade_for,
    quality_label_for,
    reliability_grade_for,
    validation_color_class_for,
    validation_grade_for,
)


class QualityLabelForTests(unittest.TestCase):
    """``quality_label_for`` maps R² to {high, medium, low} per version."""

    def test_pre_b1_thresholds(self):
        # pre-b1: high≥0.5, medium≥0.2, else low
        self.assertEqual(quality_label_for(0.80, "pre-b1"), "high")
        self.assertEqual(quality_label_for(0.50, "pre-b1"), "high")
        self.assertEqual(quality_label_for(0.49, "pre-b1"), "medium")
        self.assertEqual(quality_label_for(0.20, "pre-b1"), "medium")
        self.assertEqual(quality_label_for(0.19, "pre-b1"), "low")
        self.assertEqual(quality_label_for(0.0, "pre-b1"), "low")
        self.assertEqual(quality_label_for(-0.5, "pre-b1"), "low")

    def test_b1_tuned_alpha_thresholds(self):
        # b1-tuned-alpha: high≥0.6, medium≥0.3 (placeholder +0.10 shift)
        self.assertEqual(
            quality_label_for(0.80, "b1-tuned-alpha"), "high")
        self.assertEqual(
            quality_label_for(0.60, "b1-tuned-alpha"), "high")
        self.assertEqual(
            quality_label_for(0.59, "b1-tuned-alpha"), "medium")
        self.assertEqual(
            quality_label_for(0.30, "b1-tuned-alpha"), "medium")
        self.assertEqual(
            quality_label_for(0.29, "b1-tuned-alpha"), "low")

    def test_unknown_version_falls_back_to_most_recent(self):
        # Unknown → most-recent (b1-tuned-alpha)
        with self.assertLogs("rcm_mc.analysis.thresholds",
                              level="WARNING"):
            self.assertEqual(
                quality_label_for(0.60, "future-b2"), "high")

    def test_same_r2_can_grade_differently_across_versions(self):
        # 0.55 is 'high' in pre-b1 but 'medium' in b1-tuned-alpha
        # — the entire point of versioning the threshold table.
        self.assertEqual(quality_label_for(0.55, "pre-b1"), "high")
        self.assertEqual(
            quality_label_for(0.55, "b1-tuned-alpha"), "medium")


class ReliabilityGradeForTests(unittest.TestCase):
    """``reliability_grade_for`` is the compound n × r² ladder for
    the workbench reliability column."""

    def test_benchmark_fallback_always_D(self):
        # Regardless of n / r², benchmark_fallback grades D.
        for r in (-1, 0, 0.5, 0.99):
            for n in (0, 10, 1000):
                self.assertEqual(
                    reliability_grade_for("benchmark_fallback", n, r,
                                           "pre-b1"),
                    "D",
                )

    def test_weighted_median_uses_n_threshold_at_10(self):
        # weighted_median caps at B (n≥10) or C (else); r² ignored.
        self.assertEqual(
            reliability_grade_for("weighted_median", 10, 0.99,
                                   "pre-b1"), "B")
        self.assertEqual(
            reliability_grade_for("weighted_median", 9, 0.99,
                                   "pre-b1"), "C")
        self.assertEqual(
            reliability_grade_for("weighted_median", 50, -0.5,
                                   "pre-b1"), "B")

    def test_ridge_regression_compound_ladder_pre_b1(self):
        # pre-b1: A=(30, 0.60), B=(20, 0.45), C=(15, 0.25)
        m = "ridge_regression"
        self.assertEqual(
            reliability_grade_for(m, 50, 0.80, "pre-b1"), "A")
        self.assertEqual(
            reliability_grade_for(m, 30, 0.60, "pre-b1"), "A")
        # Just below the A r² floor → drops to B
        self.assertEqual(
            reliability_grade_for(m, 30, 0.59, "pre-b1"), "B")
        # Just below the A n floor → drops to B
        self.assertEqual(
            reliability_grade_for(m, 29, 0.65, "pre-b1"), "B")
        self.assertEqual(
            reliability_grade_for(m, 20, 0.45, "pre-b1"), "B")
        self.assertEqual(
            reliability_grade_for(m, 15, 0.25, "pre-b1"), "C")
        self.assertEqual(
            reliability_grade_for(m, 14, 0.99, "pre-b1"), "D")
        self.assertEqual(
            reliability_grade_for(m, 100, 0.10, "pre-b1"), "D")

    def test_ridge_regression_b1_thresholds_are_stricter(self):
        # b1-tuned-alpha is +0.05 on every r² floor vs pre-b1
        m = "ridge_regression"
        # 0.60 r² + n=30 → A in pre-b1 but B in b1 (0.60 < 0.65)
        self.assertEqual(
            reliability_grade_for(m, 30, 0.60, "pre-b1"), "A")
        self.assertEqual(
            reliability_grade_for(m, 30, 0.60, "b1-tuned-alpha"), "B")
        self.assertEqual(
            reliability_grade_for(m, 30, 0.65, "b1-tuned-alpha"), "A")

    def test_unknown_version_falls_back_with_warning(self):
        with self.assertLogs("rcm_mc.analysis.thresholds",
                              level="WARNING"):
            # Same input as the b1-tuned-alpha A floor
            self.assertEqual(
                reliability_grade_for("ridge_regression",
                                       30, 0.65, "future-b2"),
                "A",
            )


class BacktestGradeForTests(unittest.TestCase):
    """``backtest_grade_for`` is the simple R² → letter ladder used
    by the cohort-backtest card."""

    def test_pre_b1_cuts(self):
        # pre-b1: A≥0.75, B≥0.60, C≥0.45, D≥0.25, else F
        self.assertEqual(backtest_grade_for(0.90, "pre-b1"), "A")
        self.assertEqual(backtest_grade_for(0.75, "pre-b1"), "A")
        self.assertEqual(backtest_grade_for(0.74, "pre-b1"), "B")
        self.assertEqual(backtest_grade_for(0.60, "pre-b1"), "B")
        self.assertEqual(backtest_grade_for(0.59, "pre-b1"), "C")
        self.assertEqual(backtest_grade_for(0.45, "pre-b1"), "C")
        self.assertEqual(backtest_grade_for(0.44, "pre-b1"), "D")
        self.assertEqual(backtest_grade_for(0.25, "pre-b1"), "D")
        self.assertEqual(backtest_grade_for(0.24, "pre-b1"), "F")
        self.assertEqual(backtest_grade_for(0.0, "pre-b1"), "F")
        self.assertEqual(backtest_grade_for(-1.0, "pre-b1"), "F")

    def test_b1_tuned_alpha_cuts_are_stricter(self):
        # b1: A≥0.80, B≥0.65, C≥0.50, D≥0.30, else F
        self.assertEqual(
            backtest_grade_for(0.80, "b1-tuned-alpha"), "A")
        self.assertEqual(
            backtest_grade_for(0.79, "b1-tuned-alpha"), "B")
        self.assertEqual(
            backtest_grade_for(0.65, "b1-tuned-alpha"), "B")
        self.assertEqual(
            backtest_grade_for(0.50, "b1-tuned-alpha"), "C")
        self.assertEqual(
            backtest_grade_for(0.30, "b1-tuned-alpha"), "D")
        self.assertEqual(
            backtest_grade_for(0.29, "b1-tuned-alpha"), "F")

    def test_unknown_version_falls_back(self):
        # 0.80 in b1-tuned-alpha = A; unknown should map to most-recent
        with self.assertLogs("rcm_mc.analysis.thresholds",
                              level="WARNING"):
            self.assertEqual(
                backtest_grade_for(0.80, "future-b2"), "A")


class ValidationGradeForTests(unittest.TestCase):
    """``validation_grade_for`` is the compound (r², coverage) ladder
    for the /models/validation per-metric letter grade."""

    def test_pre_b1_a_requires_both_r2_and_coverage(self):
        # A: r²≥0.70 AND coverage≥0.85
        self.assertEqual(
            validation_grade_for(0.80, 0.90, "pre-b1"), "A")
        self.assertEqual(
            validation_grade_for(0.70, 0.85, "pre-b1"), "A")
        # r² hits A floor but coverage drops it to B
        self.assertEqual(
            validation_grade_for(0.70, 0.84, "pre-b1"), "B")
        # Coverage at A but r² drops it to B
        self.assertEqual(
            validation_grade_for(0.69, 0.85, "pre-b1"), "B")

    def test_pre_b1_b_requires_both_r2_and_coverage(self):
        # B: r²≥0.50 AND coverage≥0.75
        self.assertEqual(
            validation_grade_for(0.55, 0.80, "pre-b1"), "B")
        self.assertEqual(
            validation_grade_for(0.50, 0.75, "pre-b1"), "B")
        # Coverage at B floor + r² above C floor → C (compound)
        self.assertEqual(
            validation_grade_for(0.55, 0.74, "pre-b1"), "C")

    def test_pre_b1_c_requires_only_r2(self):
        # C: r²≥0.30 (coverage doesn't matter at this tier)
        self.assertEqual(
            validation_grade_for(0.40, 0.0, "pre-b1"), "C")
        self.assertEqual(
            validation_grade_for(0.30, 0.0, "pre-b1"), "C")
        self.assertEqual(
            validation_grade_for(0.29, 0.99, "pre-b1"), "D")

    def test_d_when_below_every_floor(self):
        self.assertEqual(
            validation_grade_for(0.10, 0.10, "pre-b1"), "D")
        self.assertEqual(
            validation_grade_for(-0.5, 0.0, "pre-b1"), "D")

    def test_b1_tuned_alpha_stricter_r2(self):
        # b1: A r²≥0.75 (coverage 0.85 unchanged); B r²≥0.55;
        # C r²≥0.35
        self.assertEqual(
            validation_grade_for(0.75, 0.85, "b1-tuned-alpha"), "A")
        self.assertEqual(
            validation_grade_for(0.74, 0.85, "b1-tuned-alpha"), "B")
        self.assertEqual(
            validation_grade_for(0.55, 0.75, "b1-tuned-alpha"), "B")
        self.assertEqual(
            validation_grade_for(0.35, 0.0, "b1-tuned-alpha"), "C")
        self.assertEqual(
            validation_grade_for(0.34, 0.99, "b1-tuned-alpha"), "D")

    def test_unknown_version_falls_back(self):
        with self.assertLogs("rcm_mc.analysis.thresholds",
                              level="WARNING"):
            self.assertEqual(
                validation_grade_for(0.75, 0.85, "future-b2"), "A")


class ValidationColorClassForTests(unittest.TestCase):
    """``validation_color_class_for`` is the UI color-bin function
    (cad-pos / cad-warn / cad-neg). Uses strict-greater-than
    (not ≥) on the bin floors."""

    def test_pre_b1_bins(self):
        # pre-b1: pos > 0.5, warn > 0.3, else neg
        self.assertEqual(
            validation_color_class_for(0.80, "pre-b1"), "cad-pos")
        # Strict > so boundary 0.5 is NOT cad-pos
        self.assertEqual(
            validation_color_class_for(0.50, "pre-b1"), "cad-warn")
        self.assertEqual(
            validation_color_class_for(0.31, "pre-b1"), "cad-warn")
        # 0.3 boundary is also strict
        self.assertEqual(
            validation_color_class_for(0.30, "pre-b1"), "cad-neg")
        self.assertEqual(
            validation_color_class_for(0.0, "pre-b1"), "cad-neg")

    def test_b1_tuned_alpha_bins(self):
        # b1: pos > 0.55, warn > 0.35
        self.assertEqual(
            validation_color_class_for(0.60, "b1-tuned-alpha"),
            "cad-pos")
        self.assertEqual(
            validation_color_class_for(0.55, "b1-tuned-alpha"),
            "cad-warn")  # strict-greater, not ≥
        self.assertEqual(
            validation_color_class_for(0.35, "b1-tuned-alpha"),
            "cad-neg")

    def test_unknown_version_falls_back(self):
        with self.assertLogs("rcm_mc.analysis.thresholds",
                              level="WARNING"):
            self.assertEqual(
                validation_color_class_for(0.60, "future-b2"),
                "cad-pos",
            )


class CrossFunctionConsistencyTests(unittest.TestCase):
    """A few cross-function sanity checks: signs / monotonicity
    across functions sharing the same R² input."""

    def test_higher_r2_never_worse_grade(self):
        # Each function should be monotone non-decreasing in R²
        # (better R² never produces a worse grade).
        for v in ("pre-b1", "b1-tuned-alpha"):
            prev = None
            for r in [-0.5, 0.0, 0.10, 0.30, 0.50, 0.65, 0.80, 0.95]:
                g = backtest_grade_for(r, v)
                if prev is not None:
                    # Letter rank: F < D < C < B < A
                    rank = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
                    self.assertGreaterEqual(
                        rank[g], rank[prev],
                        f"backtest_grade_for at version {v!r} "
                        f"not monotone in R²")
                prev = g


if __name__ == "__main__":
    unittest.main()
