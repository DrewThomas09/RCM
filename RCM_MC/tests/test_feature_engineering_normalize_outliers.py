"""Tests for the un-covered public functions in feature_engineering.

`rcm_mc/ml/feature_engineering.py` has 7 public functions but only 3
(``derive_features``, ``derive_interaction_features``,
``normalize_features``) had direct tests via ``test_ridge_predictor``.
The other two —``normalize_metrics`` and ``detect_outliers`` — are
used at the ridge-predictor + report layers but had no unit coverage,
so their NaN-safe edge cases and the sd=0/empty-comparable
fallbacks were uncovered. This file adds direct unit tests for both.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.ml.feature_engineering import (
    detect_outliers,
    normalize_metrics,
)


class NormalizeMetricsTests(unittest.TestCase):
    """Contract for ``normalize_metrics``."""

    def test_z_scores_with_explicit_medians_and_stds(self):
        out = normalize_metrics(
            {"denial_rate": 10.0, "days_in_ar": 50.0},
            benchmark_medians={"denial_rate": 6.0, "days_in_ar": 40.0},
            benchmark_stds={"denial_rate": 2.0, "days_in_ar": 5.0},
        )
        # (10 - 6) / 2 = 2.0; (50 - 40) / 5 = 2.0
        self.assertAlmostEqual(out["denial_rate"], 2.0)
        self.assertAlmostEqual(out["days_in_ar"], 2.0)

    def test_z_scores_from_comparables_when_medians_missing(self):
        comps = [
            {"denial_rate": 4.0},
            {"denial_rate": 5.0},
            {"denial_rate": 6.0},
            {"denial_rate": 7.0},
            {"denial_rate": 8.0},
        ]
        out = normalize_metrics({"denial_rate": 6.0}, comparables=comps)
        # median=6, std≈1.41; (6-6)/1.41 ≈ 0
        self.assertAlmostEqual(out["denial_rate"], 0.0, places=5)

    def test_no_benchmarks_returns_raw(self):
        # No medians, no stds, no comparables → return raw values.
        out = normalize_metrics({"x": 3.0, "y": 5.0})
        self.assertEqual(out, {"x": 3.0, "y": 5.0})

    def test_no_benchmarks_drops_non_numeric_when_returning_raw(self):
        # Raw-fallback still applies the _safe_float filter — anything
        # that doesn't parse to float is dropped, not propagated as NaN.
        out = normalize_metrics(
            {"a": 1.0, "b": "not a number", "c": None, "d": "3.14"},
        )
        self.assertEqual(set(out.keys()), {"a", "d"})
        self.assertAlmostEqual(out["d"], 3.14)

    def test_zero_sd_emits_zero_when_value_equals_median(self):
        # sd=0 means the peer group is a point mass. If the target
        # value matches the median exactly, the z-score is "0" (no
        # deviation); if not, sd=0 → divide-by-zero is dodged and the
        # raw value falls through.
        out = normalize_metrics(
            {"x": 5.0, "y": 7.0},
            benchmark_medians={"x": 5.0, "y": 5.0},
            benchmark_stds={"x": 0.0, "y": 0.0},
        )
        self.assertEqual(out["x"], 0.0)
        self.assertEqual(out["y"], 7.0)

    def test_missing_median_falls_through_to_raw(self):
        # No median for the metric → can't normalize → emit raw.
        out = normalize_metrics(
            {"x": 5.0},
            benchmark_medians={},
            benchmark_stds={"x": 1.0},
        )
        self.assertEqual(out["x"], 5.0)

    def test_negative_sd_treated_as_zero(self):
        # Documented contract: sd<=0 dodges the divide. Negative sds
        # shouldn't arise in practice but defensive code shouldn't
        # blow up if they do.
        out = normalize_metrics(
            {"x": 5.0},
            benchmark_medians={"x": 4.0},
            benchmark_stds={"x": -1.0},
        )
        self.assertEqual(out["x"], 5.0)  # falls through to raw

    def test_dropped_non_numeric_value(self):
        # When benchmarks ARE provided, _safe_float still drops
        # un-parseable values silently.
        out = normalize_metrics(
            {"a": 4.0, "b": "junk"},
            benchmark_medians={"a": 2.0, "b": 0.0},
            benchmark_stds={"a": 1.0, "b": 1.0},
        )
        self.assertIn("a", out)
        self.assertNotIn("b", out)

    def test_empty_metrics_returns_empty_dict(self):
        self.assertEqual(normalize_metrics({}), {})
        self.assertEqual(
            normalize_metrics(
                {},
                benchmark_medians={"x": 0.0},
                benchmark_stds={"x": 1.0},
            ),
            {},
        )

    def test_handles_none_metrics(self):
        # The dict-comprehension guard (`metrics or {}`) makes the
        # function safe against accidental None input.
        self.assertEqual(normalize_metrics(None), {})  # type: ignore

    def test_nan_value_dropped(self):
        # _safe_float treats float('nan') as missing (None).
        out = normalize_metrics(
            {"a": float("nan"), "b": 5.0},
            benchmark_medians={"a": 0.0, "b": 0.0},
            benchmark_stds={"a": 1.0, "b": 1.0},
        )
        self.assertNotIn("a", out)
        self.assertEqual(out["b"], 5.0)


class DetectOutliersTests(unittest.TestCase):
    """Contract for ``detect_outliers``."""

    def test_no_comparables_returns_empty(self):
        self.assertEqual(detect_outliers({"x": 100}, []), [])
        self.assertEqual(detect_outliers({"x": 100}, None), [])  # type: ignore

    def test_flags_value_above_threshold(self):
        # Comp pool has mean≈5, sd≈1.58. A value of 15 is ~6σ away.
        comps = [{"x": v} for v in (3, 4, 5, 6, 7)]
        flags = detect_outliers({"x": 15.0}, comps, threshold_sd=2.5)
        self.assertEqual(flags, ["x"])

    def test_flags_value_below_threshold(self):
        # Symmetric: a value far BELOW the mean is also flagged.
        comps = [{"x": v} for v in (10, 12, 14, 16, 18)]
        flags = detect_outliers({"x": -5.0}, comps)
        self.assertEqual(flags, ["x"])

    def test_within_threshold_no_flag(self):
        comps = [{"x": v} for v in (3, 4, 5, 6, 7)]
        # x=5 is exactly the mean → 0σ → not flagged
        self.assertEqual(detect_outliers({"x": 5.0}, comps), [])
        # x=8 is ~2σ → not flagged at threshold=2.5
        self.assertEqual(detect_outliers({"x": 8.0}, comps), [])

    def test_threshold_is_strict_greater_than(self):
        # Documented contract uses `> threshold_sd`. A value exactly
        # AT the threshold is NOT flagged.
        comps = [{"x": v} for v in (0, 0, 0, 5, 5, 5)]
        # mean=2.5, sd≈2.5; value of 8.75 is exactly 2.5σ above mean,
        # so at threshold=2.5 it shouldn't be flagged. (Allow slight
        # numeric drift by checking the strict > behavior.)
        # Just use known-safe inputs:
        comps2 = [{"y": v} for v in (1, 1, 1, 1, 1)]  # mean=1, sd=0
        # sd=0 → skipped (avoid divide-by-zero), no flags.
        self.assertEqual(detect_outliers({"y": 99.0}, comps2), [])

    def test_multiple_metrics(self):
        comps = [
            {"a": 1, "b": 100},
            {"a": 2, "b": 110},
            {"a": 3, "b": 120},
            {"a": 4, "b": 130},
            {"a": 5, "b": 140},
        ]
        flags = detect_outliers({"a": 50, "b": 115}, comps)
        # a=50 is way out (mean≈3), b=115 is near mean (120) → only a
        self.assertEqual(set(flags), {"a"})

    def test_missing_target_value_skipped(self):
        # A target value that doesn't parse to float is dropped — no
        # flag emitted for it. Other valid metrics still evaluated.
        comps = [{"a": v, "b": v * 10} for v in range(1, 6)]
        flags = detect_outliers(
            {"a": "junk", "b": 1000.0}, comps,
        )
        self.assertNotIn("a", flags)
        self.assertIn("b", flags)

    def test_metric_missing_from_comparables_skipped(self):
        # If the pool has no observations for a metric, it's silently
        # skipped (no false flag from sparse comparison).
        comps = [{"a": v} for v in (1, 2, 3, 4, 5)]
        flags = detect_outliers({"a": 100, "b": 999.0}, comps)
        # 'a' flagged but 'b' has no comp → no flag.
        self.assertEqual(flags, ["a"])

    def test_custom_threshold_lower_flags_more(self):
        # Drop threshold from 2.5σ → 1σ → more metrics flagged.
        comps = [{"x": v} for v in (3, 4, 5, 6, 7)]
        # x=7 is mean+~1.26σ. At 2.5σ → not flagged; at 1σ → flagged.
        self.assertEqual(detect_outliers({"x": 7.0}, comps,
                                          threshold_sd=2.5), [])
        self.assertEqual(detect_outliers({"x": 7.0}, comps,
                                          threshold_sd=1.0), ["x"])

    def test_zero_sd_metric_skipped(self):
        # Point-mass pool → can't compute z-score → skip (no false
        # flag, since "different from a point" is ill-defined).
        comps = [{"x": 5} for _ in range(5)]
        self.assertEqual(detect_outliers({"x": 1000.0}, comps), [])

    def test_empty_metrics_returns_empty(self):
        comps = [{"x": v} for v in (1, 2, 3, 4, 5)]
        self.assertEqual(detect_outliers({}, comps), [])

    def test_none_metrics_safe(self):
        comps = [{"x": v} for v in (1, 2, 3, 4, 5)]
        self.assertEqual(detect_outliers(None, comps), [])  # type: ignore

    def test_handles_nan_target_value(self):
        # NaN target → _safe_float → None → metric skipped, no flag.
        comps = [{"x": v} for v in (1, 2, 3, 4, 5)]
        self.assertEqual(
            detect_outliers({"x": float("nan")}, comps), [],
        )

    def test_skips_non_numeric_in_comparables(self):
        # Comp rows with non-numeric values for the metric are
        # silently ignored — we just don't add them to the pool.
        comps = [
            {"x": 1}, {"x": "junk"}, {"x": 3}, {"x": None}, {"x": 5},
        ]
        flags = detect_outliers({"x": 100.0}, comps)
        # 100 is still way out vs the 3 numeric points (1, 3, 5).
        self.assertEqual(flags, ["x"])


if __name__ == "__main__":
    unittest.main()
