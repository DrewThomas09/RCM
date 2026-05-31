"""Tests for the run-comparison helpers.

`rcm_mc/analysis/compare_runs.py` ships 3 helpers used to diff a
'Prior' simulation run against a 'Current' run (and render a
plain-English narrative for the LP-letter):

  - compare_summaries(summary_a, summary_b, ...) — DataFrame diff
  - compare_run_dirs(dir_a, dir_b, ...) — load both summary.csv +
    compare
  - narrative_comparison(comparison_df) — partner-readable text

Three functions, zero test references before this file. Pure
data-manipulation; testing locks the schema (column names) +
edge cases (zero divisor, missing metrics, missing files).
"""
from __future__ import annotations

import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.analysis.compare_runs import (
    compare_run_dirs,
    compare_summaries,
    narrative_comparison,
)


def _summary(data):
    """Helper: build the per-metric summary DataFrame the
    simulator writes out."""
    return pd.DataFrame(data).T  # metric × stat


class CompareSummariesTests(unittest.TestCase):
    """Contract for ``compare_summaries``."""

    def test_basic_delta_and_pct_change(self):
        a = _summary({
            "denial_rate": {"mean": 0.10, "p10": 0.08, "p90": 0.12},
            "days_in_ar": {"mean": 50.0, "p10": 40.0, "p90": 60.0},
        })
        b = _summary({
            "denial_rate": {"mean": 0.08, "p10": 0.06, "p90": 0.10},
            "days_in_ar": {"mean": 45.0, "p10": 38.0, "p90": 52.0},
        })
        out = compare_summaries(a, b)
        # Columns include prior/current/delta/pct_change for each stat
        row = out[out["metric"] == "denial_rate"].iloc[0]
        self.assertAlmostEqual(row["Prior_mean"], 0.10)
        self.assertAlmostEqual(row["Current_mean"], 0.08)
        self.assertAlmostEqual(row["delta_mean"], -0.02, places=4)
        # pct_change = (0.08 - 0.10) / 0.10 × 100 = -20%
        self.assertAlmostEqual(row["pct_change_mean"], -20.0,
                                places=2)

    def test_only_common_metrics_compared(self):
        # Metric in A only / metric in B only → excluded from output.
        a = _summary({
            "shared": {"mean": 5.0, "p10": 3.0, "p90": 7.0},
            "only_a": {"mean": 1.0, "p10": 0.0, "p90": 2.0},
        })
        b = _summary({
            "shared": {"mean": 6.0, "p10": 4.0, "p90": 8.0},
            "only_b": {"mean": 99.0, "p10": 0.0, "p90": 100.0},
        })
        out = compare_summaries(a, b)
        metrics = set(out["metric"])
        self.assertEqual(metrics, {"shared"})

    def test_custom_labels_appear_in_columns(self):
        a = _summary({"x": {"mean": 1.0, "p10": 0.5, "p90": 1.5}})
        b = _summary({"x": {"mean": 2.0, "p10": 1.5, "p90": 2.5}})
        out = compare_summaries(a, b, label_a="Q1", label_b="Q2")
        cols = set(out.columns)
        self.assertIn("Q1_mean", cols)
        self.assertIn("Q2_mean", cols)
        self.assertNotIn("Prior_mean", cols)

    def test_zero_divisor_uses_zero_pct_change(self):
        # If Prior value is 0, pct_change defaults to 0 (avoid
        # ZeroDivisionError; documents the explicit fallback).
        a = _summary({"x": {"mean": 0.0, "p10": 0.0, "p90": 0.0}})
        b = _summary({"x": {"mean": 5.0, "p10": 0.0, "p90": 10.0}})
        out = compare_summaries(a, b)
        row = out.iloc[0]
        self.assertEqual(row["pct_change_mean"], 0.0)
        # delta still computed
        self.assertEqual(row["delta_mean"], 5.0)

    def test_missing_stat_column_skipped(self):
        # If a stat (e.g. p10) is missing in either input, that
        # stat's columns are omitted; other stats still computed.
        a = pd.DataFrame({"mean": [0.10]}, index=["x"])
        b = pd.DataFrame({"mean": [0.08]}, index=["x"])
        out = compare_summaries(a, b)
        row = out.iloc[0]
        # mean stats present
        self.assertIn("Prior_mean", row.index)
        self.assertIn("delta_mean", row.index)
        # p10 / p90 stats absent (not in either input)
        self.assertNotIn("Prior_p10", row.index)
        self.assertNotIn("Current_p90", row.index)

    def test_returns_dataframe_with_metric_column(self):
        a = _summary({"x": {"mean": 1.0, "p10": 0.5, "p90": 1.5}})
        b = _summary({"x": {"mean": 2.0, "p10": 1.5, "p90": 2.5}})
        out = compare_summaries(a, b)
        self.assertIsInstance(out, pd.DataFrame)
        self.assertIn("metric", out.columns)

    def test_empty_intersection_returns_empty_df(self):
        a = _summary({"only_a": {"mean": 1.0, "p10": 0, "p90": 2}})
        b = _summary({"only_b": {"mean": 5.0, "p10": 0, "p90": 10}})
        out = compare_summaries(a, b)
        self.assertEqual(len(out), 0)

    def test_metrics_sorted(self):
        # Output metrics are sorted (deterministic ordering).
        a = _summary({
            "z": {"mean": 1, "p10": 0, "p90": 2},
            "a": {"mean": 1, "p10": 0, "p90": 2},
            "m": {"mean": 1, "p10": 0, "p90": 2},
        })
        b = _summary({
            "z": {"mean": 2, "p10": 0, "p90": 2},
            "a": {"mean": 2, "p10": 0, "p90": 2},
            "m": {"mean": 2, "p10": 0, "p90": 2},
        })
        out = compare_summaries(a, b)
        self.assertEqual(list(out["metric"]), ["a", "m", "z"])


class CompareRunDirsTests(unittest.TestCase):
    """Contract for ``compare_run_dirs``."""

    def test_reads_summary_csv_and_compares(self):
        with tempfile.TemporaryDirectory() as tmp:
            dir_a = os.path.join(tmp, "a")
            dir_b = os.path.join(tmp, "b")
            os.makedirs(dir_a)
            os.makedirs(dir_b)
            _summary({"x": {"mean": 1.0, "p10": 0.5, "p90": 1.5}}).to_csv(
                os.path.join(dir_a, "summary.csv"))
            _summary({"x": {"mean": 2.0, "p10": 1.5, "p90": 2.5}}).to_csv(
                os.path.join(dir_b, "summary.csv"))
            out = compare_run_dirs(dir_a, dir_b)
            self.assertIn("metric", out.columns)
            row = out.iloc[0]
            self.assertEqual(row["metric"], "x")
            self.assertAlmostEqual(row["delta_mean"], 1.0)

    def test_missing_dir_a_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            dir_b = os.path.join(tmp, "b")
            os.makedirs(dir_b)
            _summary({"x": {"mean": 1.0, "p10": 0.5, "p90": 1.5}}).to_csv(
                os.path.join(dir_b, "summary.csv"))
            with self.assertRaises(FileNotFoundError):
                compare_run_dirs(os.path.join(tmp, "doesnt_exist"),
                                  dir_b)

    def test_missing_dir_b_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            dir_a = os.path.join(tmp, "a")
            os.makedirs(dir_a)
            _summary({"x": {"mean": 1.0, "p10": 0.5, "p90": 1.5}}).to_csv(
                os.path.join(dir_a, "summary.csv"))
            with self.assertRaises(FileNotFoundError):
                compare_run_dirs(dir_a,
                                  os.path.join(tmp, "doesnt_exist"))

    def test_custom_labels_propagate(self):
        with tempfile.TemporaryDirectory() as tmp:
            dir_a = os.path.join(tmp, "a")
            dir_b = os.path.join(tmp, "b")
            os.makedirs(dir_a)
            os.makedirs(dir_b)
            _summary({"x": {"mean": 1.0, "p10": 0.5, "p90": 1.5}}).to_csv(
                os.path.join(dir_a, "summary.csv"))
            _summary({"x": {"mean": 2.0, "p10": 1.5, "p90": 2.5}}).to_csv(
                os.path.join(dir_b, "summary.csv"))
            out = compare_run_dirs(dir_a, dir_b,
                                    label_a="Q3", label_b="Q4")
            self.assertIn("Q3_mean", out.columns)
            self.assertIn("Q4_mean", out.columns)


class NarrativeComparisonTests(unittest.TestCase):
    """Contract for the partner-readable narrative."""

    def test_no_significant_changes_text(self):
        # All deltas <= 5% → 'no significant changes' fallback.
        df = pd.DataFrame([
            {"metric": "x", "pct_change_mean": 2.0},
            {"metric": "y", "pct_change_mean": -3.0},
            {"metric": "z", "pct_change_mean": 5.0},  # boundary
        ])
        out = narrative_comparison(df)
        self.assertEqual(out, "No significant changes detected "
                              "between the two runs.")

    def test_increase_classification(self):
        df = pd.DataFrame([
            {"metric": "denial_rate", "pct_change_mean": 12.0},
        ])
        out = narrative_comparison(df)
        self.assertIn("denial_rate", out)
        self.assertIn("increased", out)
        self.assertIn("12.0%", out)

    def test_decrease_classification(self):
        df = pd.DataFrame([
            {"metric": "days_in_ar", "pct_change_mean": -8.0},
        ])
        out = narrative_comparison(df)
        self.assertIn("days_in_ar", out)
        self.assertIn("decreased", out)
        self.assertIn("8.0%", out)

    def test_threshold_strictly_above_5(self):
        # Boundary: 5% exactly is NOT flagged; 5.01% is.
        df1 = pd.DataFrame([
            {"metric": "x", "pct_change_mean": 5.0},
        ])
        self.assertEqual(narrative_comparison(df1),
                          "No significant changes detected "
                          "between the two runs.")
        df2 = pd.DataFrame([
            {"metric": "x", "pct_change_mean": 5.01},
        ])
        self.assertIn("increased", narrative_comparison(df2))

    def test_handles_missing_pct_change_col(self):
        # Comparison DataFrame missing pct_change_mean column →
        # all rows skipped → 'no significant changes' fallback.
        df = pd.DataFrame([
            {"metric": "x", "delta_mean": 5.0},
        ])
        out = narrative_comparison(df)
        self.assertIn("No significant changes", out)

    def test_multi_metric_listing(self):
        df = pd.DataFrame([
            {"metric": "a", "pct_change_mean": 10.0},
            {"metric": "b", "pct_change_mean": -8.0},
            {"metric": "c", "pct_change_mean": 2.0},  # below threshold
        ])
        out = narrative_comparison(df)
        self.assertIn("a", out)
        self.assertIn("b", out)
        # 'c' shouldn't be mentioned (below 5% threshold)
        # Note: 'c' alone could appear as part of other words —
        # check just that it's not a standalone bullet line.
        self.assertNotIn("- c:", out)


if __name__ == "__main__":
    unittest.main()
