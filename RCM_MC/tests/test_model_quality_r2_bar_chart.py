"""Pin for the CV R² horizontal-bar chart on /models/quality."""
from __future__ import annotations

import unittest
from types import SimpleNamespace


def _calib(label="well_calibrated", coverage=0.91, factor=1.0):
    return SimpleNamespace(
        quality_label=label,
        observed_coverage=coverage,
        nominal_coverage=0.9,
        calibration_factor=factor,
    )


def _result(name, cv_r2, grade, calib_label="well_calibrated"):
    return SimpleNamespace(
        model_name=name,
        target_metric="x",
        feature_count=10,
        cv_r2=cv_r2,
        cv_mae=1.0,
        cv_mape=0.1,
        grade=grade,
        calibration=_calib(label=calib_label),
        n_train=400,
        n_holdout=120,
        notes=[],
    )


class R2BarChartTests(unittest.TestCase):
    def test_renders_bar_per_model_sorted_high_to_low(self):
        from rcm_mc.ui.model_quality_dashboard import _r2_bar_chart
        svg = _r2_bar_chart([
            _result("low", 0.4, "C"),
            _result("high", 0.85, "A"),
            _result("mid", 0.65, "B"),
        ])
        self.assertEqual(svg.count("<rect"), 3)
        # Sorted high-on-top: "high" model name appears earlier in
        # the SVG than "low"
        self.assertLess(svg.index(">high"), svg.index(">low"))

    def test_overconfident_renders_red_tick(self):
        # Overconfident gets a thick red tick mark on the left edge
        # of the bar
        from rcm_mc.ui.model_quality_dashboard import _r2_bar_chart
        svg = _r2_bar_chart([
            _result("overc", 0.6, "B", calib_label="overconfident"),
        ])
        self.assertIn("#b5321e", svg)
        self.assertIn('stroke-width="3"', svg)

    def test_well_calibrated_renders_no_red_tick(self):
        from rcm_mc.ui.model_quality_dashboard import _r2_bar_chart
        svg = _r2_bar_chart([
            _result("good", 0.7, "B"),
        ])
        # No red stroke-width=3 marker
        self.assertNotIn('stroke-width="3"', svg)

    def test_returns_empty_for_no_results(self):
        from rcm_mc.ui.model_quality_dashboard import _r2_bar_chart
        self.assertEqual(_r2_bar_chart([]), "")

    def test_grade_colors_applied(self):
        from rcm_mc.ui.model_quality_dashboard import _r2_bar_chart
        svg = _r2_bar_chart([
            _result("a_model", 0.92, "A"),
            _result("c_model", 0.55, "C"),
            _result("d_model", 0.30, "D"),
        ])
        # A=green, C=amber, D=red — each color present
        self.assertIn("#0a8a5f", svg)
        self.assertIn("#b8732a", svg)
        self.assertIn("#b5321e", svg)


if __name__ == "__main__":
    unittest.main()
