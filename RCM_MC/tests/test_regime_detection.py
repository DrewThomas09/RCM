"""Tests for PELT changepoint detection + regime classification."""
from __future__ import annotations

import unittest

import numpy as np


class TestPELT(unittest.TestCase):
    def test_no_changepoints_on_constant_series(self):
        from rcm_mc.ml.regime_detection import (
            detect_changepoints,
        )
        cps = detect_changepoints([5.0] * 10)
        self.assertEqual(cps, [])

    def test_single_step_change(self):
        from rcm_mc.ml.regime_detection import (
            detect_changepoints,
        )
        # 5 periods at 1.0, 5 periods at 5.0 — clear break at 5
        series = [1.0] * 5 + [5.0] * 5
        cps = detect_changepoints(series)
        self.assertEqual(len(cps), 1)
        self.assertEqual(cps[0], 5)

    def test_two_changepoints(self):
        from rcm_mc.ml.regime_detection import (
            detect_changepoints,
        )
        rng = np.random.default_rng(7)
        # Three regimes
        seg1 = rng.normal(1.0, 0.05, 6)
        seg2 = rng.normal(3.0, 0.05, 6)
        seg3 = rng.normal(0.5, 0.05, 6)
        series = np.concatenate([seg1, seg2, seg3])
        cps = detect_changepoints(series)
        # Should detect 2 breaks at indices 6 and 12
        self.assertEqual(len(cps), 2)
        self.assertIn(6, cps)
        self.assertIn(12, cps)

    def test_short_series_no_breaks(self):
        from rcm_mc.ml.regime_detection import (
            detect_changepoints,
        )
        # Below 2*min_segment_length → no breaks
        cps = detect_changepoints([1.0, 2.0, 3.0])
        self.assertEqual(cps, [])

    def test_min_segment_length_respected(self):
        from rcm_mc.ml.regime_detection import (
            detect_changepoints,
        )
        # Short bursts shouldn't be detected as separate regimes
        # when min_segment_length is large
        series = [1.0, 1.0, 5.0, 1.0, 1.0, 5.0, 5.0, 5.0,
                  5.0, 5.0]
        cps = detect_changepoints(
            series, min_segment_length=4)
        # Only the structural break at index 5 should remain
        # (the brief 5.0 at index 2 is too short)
        for cp in cps:
            self.assertGreaterEqual(cp, 4)

    def test_nan_rejected(self):
        from rcm_mc.ml.regime_detection import (
            detect_changepoints,
        )
        with self.assertRaises(ValueError):
            detect_changepoints([1.0, float("nan"), 2.0])


class TestRegimeClassification(unittest.TestCase):
    def test_growth_regime(self):
        from rcm_mc.ml.regime_detection import (
            classify_regime,
        )
        # Steeply rising series
        values = [100, 110, 120, 130, 140]
        # Series std ≈ 14.1, slope = 10/period → 0.71 std/period
        regime = classify_regime(values, series_std=14.1)
        self.assertEqual(regime, "rapid_growth")

    def test_distress_regime(self):
        from rcm_mc.ml.regime_detection import (
            classify_regime,
        )
        values = [100, 90, 80, 70, 60]
        regime = classify_regime(values, series_std=14.1)
        self.assertEqual(regime, "distress")

    def test_stable_regime(self):
        from rcm_mc.ml.regime_detection import (
            classify_regime,
        )
        values = [100, 102, 99, 101, 100]
        regime = classify_regime(values, series_std=10)
        self.assertEqual(regime, "stable")

    def test_zero_std_returns_stable(self):
        from rcm_mc.ml.regime_detection import (
            classify_regime,
        )
        regime = classify_regime([5, 5, 5, 5], series_std=0)
        self.assertEqual(regime, "stable")


class TestMetricRegimeAnalysis(unittest.TestCase):
    def test_growing_hospital_revenue(self):
        from rcm_mc.ml.regime_detection import (
            analyze_metric_regime,
        )
        rng = np.random.default_rng(13)
        # 8 periods of steady growth
        revenue = [
            100_000_000 * (1.05 ** i)
            * (1 + rng.normal(0, 0.01))
            for i in range(8)
        ]
        result = analyze_metric_regime("revenue", revenue)
        self.assertEqual(result.metric, "revenue")
        self.assertEqual(result.n_periods, 8)
        self.assertIn(
            result.current_regime,
            ["growth", "rapid_growth"])

    def test_distressed_hospital_margin(self):
        from rcm_mc.ml.regime_detection import (
            analyze_metric_regime,
        )
        margin = [0.06, 0.05, 0.03, 0.01,
                  -0.01, -0.03, -0.05, -0.07]
        result = analyze_metric_regime(
            "ebitda_margin", margin)
        self.assertIn(
            result.current_regime,
            ["distress", "decline"])

    def test_changepoint_with_regime_shift(self):
        """3 years stable, then 4 years declining — one
        changepoint, current regime is decline."""
        from rcm_mc.ml.regime_detection import (
            analyze_metric_regime,
        )
        rng = np.random.default_rng(7)
        stable = [100 + rng.normal(0, 1) for _ in range(6)]
        decline = [
            100 - 5 * (i + 1) + rng.normal(0, 1)
            for i in range(6)
        ]
        result = analyze_metric_regime(
            "revenue", stable + decline)
        self.assertGreaterEqual(len(result.changepoints), 1)
        # Last segment should be in distress
        last = result.segments[-1]
        self.assertIn(last.regime,
                      ["distress", "decline"])

    def test_short_history_single_segment(self):
        from rcm_mc.ml.regime_detection import (
            analyze_metric_regime,
        )
        result = analyze_metric_regime(
            "revenue", [100, 110, 120])
        # Below 2 × min_segment_length → single segment
        self.assertEqual(len(result.changepoints), 0)
        self.assertEqual(len(result.segments), 1)
        self.assertTrue(any(
            "best-current-estimate" in n
            for n in result.notes))

    def test_empty_series_handled(self):
        from rcm_mc.ml.regime_detection import (
            analyze_metric_regime,
        )
        result = analyze_metric_regime("revenue", [])
        self.assertEqual(result.n_periods, 0)
        self.assertEqual(result.current_regime, "stable")

    def test_timestamps_attached(self):
        from rcm_mc.ml.regime_detection import (
            analyze_metric_regime,
        )
        rng = np.random.default_rng(7)
        values = [
            100 + i * 5 + rng.normal(0, 0.5)
            for i in range(8)
        ]
        ts = [f"FY{2018 + i}" for i in range(8)]
        result = analyze_metric_regime(
            "revenue", values, timestamps=ts)
        self.assertEqual(
            result.segments[0].start_timestamp, "FY2018")
        self.assertEqual(
            result.segments[-1].end_timestamp, "FY2025")


class TestHospitalRegimeReport(unittest.TestCase):
    def test_aligned_growth_high_confidence(self):
        from rcm_mc.ml.regime_detection import (
            analyze_hospital_regime,
        )
        rng = np.random.default_rng(7)
        report = analyze_hospital_regime({
            "revenue": [
                100 * (1.04 ** i)
                * (1 + rng.normal(0, 0.005))
                for i in range(8)],
            "ebitda_margin": [
                0.04 + 0.005 * i
                + rng.normal(0, 0.001)
                for i in range(8)],
            "volume": [
                10000 * (1.03 ** i)
                * (1 + rng.normal(0, 0.005))
                for i in range(8)],
        }, ccn="450001")
        self.assertEqual(report.overall_regime, "growth")
        self.assertEqual(report.confidence, "high")
        self.assertEqual(report.ccn, "450001")
        self.assertEqual(report.conflict_flags, [])

    def test_revenue_growing_margin_distressed(self):
        """Classic 'unit economics deteriorating' flag —
        revenue growing while margin in distress."""
        from rcm_mc.ml.regime_detection import (
            analyze_hospital_regime,
        )
        rng = np.random.default_rng(11)
        report = analyze_hospital_regime({
            "revenue": [
                100 * (1.05 ** i)
                * (1 + rng.normal(0, 0.005))
                for i in range(8)],
            "ebitda_margin": [
                0.06 - 0.012 * i
                + rng.normal(0, 0.001)
                for i in range(8)],
        })
        self.assertGreater(
            len(report.conflict_flags), 0)
        self.assertTrue(any(
            "unit-economics" in f
            for f in report.conflict_flags))

    def test_volume_declining_revenue_growing(self):
        """Rate-driven growth flag — volume falling,
        revenue still rising."""
        from rcm_mc.ml.regime_detection import (
            analyze_hospital_regime,
        )
        rng = np.random.default_rng(13)
        report = analyze_hospital_regime({
            "revenue": [
                100 * (1.04 ** i)
                * (1 + rng.normal(0, 0.005))
                for i in range(8)],
            "volume": [
                10000 * (0.95 ** i)
                * (1 + rng.normal(0, 0.005))
                for i in range(8)],
        })
        self.assertTrue(any(
            "rate-driven" in f
            for f in report.conflict_flags))

    def test_distress_overall_regime(self):
        from rcm_mc.ml.regime_detection import (
            analyze_hospital_regime,
        )
        rng = np.random.default_rng(17)
        report = analyze_hospital_regime({
            "revenue": [
                100 * (0.93 ** i)
                * (1 + rng.normal(0, 0.005))
                for i in range(8)],
            "ebitda_margin": [
                0.04 - 0.015 * i
                + rng.normal(0, 0.001)
                for i in range(8)],
        })
        self.assertEqual(report.overall_regime, "distress")
        self.assertTrue(any(
            "restructuring" in n or "turnaround" in n
            for n in report.notes))

    def test_empty_metric_series(self):
        from rcm_mc.ml.regime_detection import (
            analyze_hospital_regime,
        )
        report = analyze_hospital_regime({})
        self.assertEqual(report.overall_regime, "stable")


if __name__ == "__main__":
    unittest.main()
