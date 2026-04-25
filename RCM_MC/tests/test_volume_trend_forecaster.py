"""Tests for service-line volume forecaster + trajectory classifier."""
from __future__ import annotations

import unittest


def _quarterly_series(start_value, growth_rate_quarter,
                      n_periods, noise=0.0, seed=42):
    """Synthesize a quarterly time series."""
    import random
    rng = random.Random(seed)
    out = []
    val = start_value
    for q in range(n_periods):
        year = 2020 + q // 4
        quarter = q % 4 + 1
        label = f"{year}Q{quarter}"
        v = val * (1 + rng.uniform(-noise, noise))
        out.append((label, max(0, v)))
        val *= (1 + growth_rate_quarter)
    return out


class TestTrajectoryClassification(unittest.TestCase):
    def test_band_thresholds(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            _classify_trajectory,
        )
        self.assertEqual(
            _classify_trajectory(-0.10), "rapid_decline")
        self.assertEqual(
            _classify_trajectory(-0.03), "decline")
        self.assertEqual(
            _classify_trajectory(0.00), "stable")
        self.assertEqual(
            _classify_trajectory(0.03), "growth")
        self.assertEqual(
            _classify_trajectory(0.10), "rapid_growth")

    def test_none_or_nan_is_stable(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            _classify_trajectory,
        )
        self.assertEqual(
            _classify_trajectory(None), "stable")
        self.assertEqual(
            _classify_trajectory(float("nan")), "stable")


class TestVolumeForecasting(unittest.TestCase):
    def test_growing_service_line(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
        )
        # 3% per quarter ≈ 12.55% annualized → 'rapid_growth'
        history = _quarterly_series(
            1000, 0.03, n_periods=12)
        forecasts = forecast_service_line_volumes(
            {"Surgery": history})
        self.assertEqual(len(forecasts), 1)
        f = forecasts[0]
        self.assertEqual(f.service_line, "Surgery")
        self.assertGreater(f.projected_cagr, 0.05)
        self.assertEqual(f.trajectory, "rapid_growth")

    def test_declining_service_line(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
        )
        history = _quarterly_series(
            1000, -0.02, n_periods=12)
        forecasts = forecast_service_line_volumes(
            {"ED Admit": history})
        f = forecasts[0]
        self.assertLess(f.projected_cagr, -0.04)
        self.assertIn(f.trajectory,
                      ["decline", "rapid_decline"])

    def test_stable_service_line(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
        )
        history = _quarterly_series(
            1000, 0.001, n_periods=12, noise=0.005)
        forecasts = forecast_service_line_volumes(
            {"Imaging": history})
        f = forecasts[0]
        self.assertEqual(f.trajectory, "stable")

    def test_results_sorted_by_cagr_desc(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
        )
        forecasts = forecast_service_line_volumes({
            "Declining": _quarterly_series(
                1000, -0.02, 12),
            "Growing": _quarterly_series(
                1000, 0.03, 12),
            "Stable": _quarterly_series(
                1000, 0.001, 12, noise=0.005),
        })
        # Sorted by CAGR descending
        self.assertEqual(
            forecasts[0].service_line, "Growing")
        self.assertEqual(
            forecasts[-1].service_line, "Declining")

    def test_thin_history_uses_weighted_recent(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
        )
        history = _quarterly_series(
            1000, 0.03, n_periods=4)
        forecasts = forecast_service_line_volumes(
            {"X": history})
        self.assertEqual(
            forecasts[0].method, "weighted_recent")


class TestClassification(unittest.TestCase):
    def test_split_into_three_groups(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
            classify_trajectories,
        )
        forecasts = forecast_service_line_volumes({
            "Surgery": _quarterly_series(1000, 0.025, 12),
            "ED": _quarterly_series(1000, 0.001, 12,
                                    noise=0.005),
            "OB": _quarterly_series(1000, -0.02, 12),
        })
        growing, stable, declining = (
            classify_trajectories(forecasts))
        self.assertIn("Surgery", growing)
        self.assertIn("ED", stable)
        self.assertIn("OB", declining)


class TestIPOPMigration(unittest.TestCase):
    def test_classic_ip_to_op_migration(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
            detect_ip_op_migration,
        )
        forecasts = forecast_service_line_volumes({
            "ED Admit": _quarterly_series(
                1000, -0.025, 12),  # declining IP
            "Observation": _quarterly_series(
                500, 0.04, 12),     # growing OP
        })
        flags = detect_ip_op_migration(forecasts)
        self.assertEqual(len(flags), 1)
        self.assertEqual(
            flags[0].inpatient_line, "ED Admit")
        self.assertEqual(
            flags[0].outpatient_line, "Observation")
        self.assertGreater(
            flags[0].migration_strength, 0.06)

    def test_no_migration_when_both_decline(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
            detect_ip_op_migration,
        )
        forecasts = forecast_service_line_volumes({
            "ED Admit": _quarterly_series(
                1000, -0.025, 12),
            "Observation": _quarterly_series(
                500, -0.01, 12),
        })
        flags = detect_ip_op_migration(forecasts)
        self.assertEqual(len(flags), 0)

    def test_custom_pairs(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            forecast_service_line_volumes,
            detect_ip_op_migration,
        )
        forecasts = forecast_service_line_volumes({
            "InpatientCardio": _quarterly_series(
                1000, -0.02, 12),
            "OutpatientCardio": _quarterly_series(
                500, 0.05, 12),
        })
        flags = detect_ip_op_migration(
            forecasts,
            pairs=[("InpatientCardio",
                    "OutpatientCardio")])
        self.assertEqual(len(flags), 1)


class TestHospitalTrajectoryReport(unittest.TestCase):
    def test_growing_hospital(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            build_hospital_trajectory_report,
        )
        report = build_hospital_trajectory_report({
            "Surgery": _quarterly_series(2000, 0.025, 12),
            "Imaging": _quarterly_series(1500, 0.02, 12),
            "ED": _quarterly_series(1000, 0.001, 12,
                                    noise=0.005),
        }, ccn="450001")
        self.assertEqual(report.ccn, "450001")
        self.assertGreater(report.overall_cagr, 0.04)
        self.assertIn(
            report.overall_trajectory,
            ["growth", "rapid_growth"])
        self.assertIn("Surgery", report.growing_lines)
        self.assertIn("Imaging", report.growing_lines)
        # Growth note fires
        self.assertTrue(any(
            "growing" in n
            for n in report.notes))

    def test_declining_hospital_no_migration_note(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            build_hospital_trajectory_report,
        )
        report = build_hospital_trajectory_report({
            "Surgery": _quarterly_series(2000, -0.02, 12),
            "Imaging": _quarterly_series(1500, -0.02, 12),
        })
        self.assertIn(report.overall_trajectory,
                      ["decline", "rapid_decline"])
        # No migration to explain it → catchment note fires
        # (only fires on rapid_decline)
        if report.overall_trajectory == "rapid_decline":
            self.assertTrue(any(
                "catchment-area" in n
                for n in report.notes))

    def test_volume_weighted_overall_cagr(self):
        """Overall CAGR weighted by last-period volume — small
        line shouldn't dominate big line."""
        from rcm_mc.ml.volume_trend_forecaster import (
            build_hospital_trajectory_report,
        )
        report = build_hospital_trajectory_report({
            # Big line growing slowly
            "Surgery": _quarterly_series(10_000, 0.005, 12),
            # Small line growing fast
            "BoutiqueClinic": _quarterly_series(
                100, 0.05, 12),
        })
        # Overall should be closer to Surgery's 2%/yr
        # than to BoutiqueClinic's 21%/yr
        self.assertLess(report.overall_cagr, 0.05)
        self.assertGreater(report.overall_cagr, 0.005)

    def test_thin_history_warning(self):
        from rcm_mc.ml.volume_trend_forecaster import (
            build_hospital_trajectory_report,
        )
        report = build_hospital_trajectory_report({
            "Surgery": _quarterly_series(1000, 0.02, 4),
        })
        self.assertTrue(any(
            "weighted-recent" in n or "<6 periods" in n
            for n in report.notes))


if __name__ == "__main__":
    unittest.main()
