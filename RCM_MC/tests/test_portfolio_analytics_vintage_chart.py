"""Pin for the SVG vintage-MOIC chart on /portfolio-analytics.

Replaces the previously bland vintage-cohort table with a visual:
median MOIC by year as colored SVG bars (green ≥2.5x, amber 1.5–
2.5x, red <1.5x). Partners read portfolio shape at a glance
instead of scanning a 7-column table.
"""
from __future__ import annotations

import unittest


class VintageChartTests(unittest.TestCase):
    def test_chart_renders_bars_per_cohort(self):
        from rcm_mc.ui.chartis.portfolio_analytics_page import (
            _vintage_chart,
        )
        cohorts = [
            {"year": 2020, "count": 5, "realized_count": 2,
             "median_moic": 2.7, "total_ev_mm": 480,
             "loss_rate": 0.2, "home_run_rate": 0.4},
            {"year": 2021, "count": 4, "realized_count": 3,
             "median_moic": 1.8, "total_ev_mm": 320,
             "loss_rate": 0.25, "home_run_rate": 0.25},
            {"year": 2022, "count": 6, "realized_count": 1,
             "median_moic": 1.2, "total_ev_mm": 540,
             "loss_rate": 0.5, "home_run_rate": 0.0},
        ]
        svg = _vintage_chart(cohorts)
        self.assertTrue(svg.startswith("<svg"))
        # One bar per cohort
        self.assertEqual(svg.count("<rect"), 3)
        # Value labels rendered (e.g. "2.7x")
        self.assertIn("2.7x", svg)
        self.assertIn("1.8x", svg)
        self.assertIn("1.2x", svg)
        # Axis label "Median MOIC"
        self.assertIn("Median MOIC", svg)

    def test_chart_colors_bars_by_performance_band(self):
        from rcm_mc.ui.chartis.portfolio_analytics_page import (
            _vintage_chart,
        )
        # One in each band
        svg = _vintage_chart([
            {"year": 2018, "count": 3, "realized_count": 3,
             "median_moic": 3.2, "total_ev_mm": 240,
             "loss_rate": 0.0, "home_run_rate": 0.6},
            {"year": 2019, "count": 3, "realized_count": 3,
             "median_moic": 2.0, "total_ev_mm": 220,
             "loss_rate": 0.1, "home_run_rate": 0.2},
            {"year": 2020, "count": 3, "realized_count": 2,
             "median_moic": 1.0, "total_ev_mm": 200,
             "loss_rate": 0.4, "home_run_rate": 0.0},
        ])
        # Each band's canonical color
        self.assertIn("#0a8a5f", svg)  # green band (≥2.5x)
        self.assertIn("#b8732a", svg)  # amber band (1.5–2.5x)
        self.assertIn("#b5321e", svg)  # red band (<1.5x)

    def test_chart_returns_empty_for_no_data(self):
        from rcm_mc.ui.chartis.portfolio_analytics_page import (
            _vintage_chart,
        )
        self.assertEqual(_vintage_chart([]), "")

    def test_chart_skips_cohorts_with_no_median_moic(self):
        # Cohorts that have no realized deals get median_moic=None;
        # skip rather than draw a zero-height bar that looks like
        # "performed badly".
        from rcm_mc.ui.chartis.portfolio_analytics_page import (
            _vintage_chart,
        )
        svg = _vintage_chart([
            {"year": 2024, "count": 5, "realized_count": 0,
             "median_moic": None, "total_ev_mm": 400,
             "loss_rate": None, "home_run_rate": None},
            {"year": 2025, "count": 5, "realized_count": 0,
             "median_moic": None, "total_ev_mm": 400,
             "loss_rate": None, "home_run_rate": None},
        ])
        # No realized cohorts → no chart
        self.assertEqual(svg, "")

    def test_chart_appears_in_full_page(self):
        from rcm_mc.ui.chartis.portfolio_analytics_page import (
            render_portfolio_analytics,
        )
        out = render_portfolio_analytics()
        # The chart's axis label is unique enough to identify
        self.assertIn("Median MOIC</text>", out)


if __name__ == "__main__":
    unittest.main()
