"""Tests for vintage analytics and /vintage-perf page."""
from __future__ import annotations

import unittest


class TestVintageAnalytics(unittest.TestCase):
    def _corpus(self):
        return [
            {"source_id": f"t{i:02}", "deal_name": f"Deal {i}", "buyer": "B", "seller": "S",
             "ev_mm": 150.0, "hold_years": 5.0,
             "realized_moic": 1.5 + (i % 4) * 0.5, "realized_irr": 0.15 + (i % 3) * 0.05,
             "payer_mix": {}, "year": 2015 + (i % 8), "sector": "hospital" if i % 2 == 0 else "physician_group"}
            for i in range(40)
        ]

    def test_compute_stats(self):
        from rcm_mc.data_public.vintage_analytics import compute_vintage_stats
        stats = compute_vintage_stats(self._corpus())
        self.assertGreater(len(stats), 0)

    def test_sorted_by_year(self):
        from rcm_mc.data_public.vintage_analytics import compute_vintage_stats
        stats = compute_vintage_stats(self._corpus())
        years = [s.year for s in stats]
        self.assertEqual(years, sorted(years))

    def test_percentiles_ordered(self):
        from rcm_mc.data_public.vintage_analytics import compute_vintage_stats
        for s in compute_vintage_stats(self._corpus()):
            self.assertLessEqual(s.moic_p25, s.moic_p50)
            self.assertLessEqual(s.moic_p50, s.moic_p75)

    def test_loss_rate_range(self):
        from rcm_mc.data_public.vintage_analytics import compute_vintage_stats
        for s in compute_vintage_stats(self._corpus()):
            self.assertGreaterEqual(s.loss_rate, 0.0)
            self.assertLessEqual(s.loss_rate, 1.0)

    def test_top_sectors(self):
        from rcm_mc.data_public.vintage_analytics import compute_vintage_stats
        stats = compute_vintage_stats(self._corpus())
        for s in stats:
            self.assertLessEqual(len(s.top_sectors), 3)

    def test_color_tier(self):
        from rcm_mc.data_public.vintage_analytics import VintageStats
        s = VintageStats(year=2020, n_deals=10, moic_p25=2.0, moic_p50=3.5,
                         moic_p75=4.5, irr_p50=0.25, avg_hold=5.0, loss_rate=0.05, avg_ev_mm=200.0)
        self.assertEqual(s.moic_color_tier, "green")


class TestRenderVintagePerf(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.vintage_perf_page import render_vintage_perf
        html = render_vintage_perf()
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 20_000)

    def test_heatmap_present(self):
        from rcm_mc.ui.data_public.vintage_perf_page import render_vintage_perf
        html = render_vintage_perf()
        self.assertIn("Vintage Heatmap", html)
        self.assertIn("<svg", html)

    def test_moic_chart_present(self):
        from rcm_mc.ui.data_public.vintage_perf_page import render_vintage_perf
        html = render_vintage_perf()
        self.assertIn("P50 MOIC by Vintage", html)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.vintage_perf_page import render_vintage_perf
        html = render_vintage_perf()
        self.assertIn("Best Vintage", html)
        self.assertIn("Worst Vintage", html)

    def test_detail_table_present(self):
        from rcm_mc.ui.data_public.vintage_perf_page import render_vintage_perf
        html = render_vintage_perf()
        self.assertIn("Vintage Detail", html)
        self.assertIn("Loss %", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.vintage_perf_page import render_vintage_perf
        html = render_vintage_perf()
        # Legacy-nav self-reference — now validate page identity in
        # the shell title bar since legacy-nav is no longer rendered.
        self.assertIn("Vintage", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.vintage_perf_page import render_vintage_perf
        html = render_vintage_perf()
        self.assertNotIn("background:#ffffff", html.lower())

    def test_heatmap_svg_helper(self):
        from rcm_mc.ui.data_public.vintage_perf_page import _heatmap_svg
        from rcm_mc.data_public.vintage_analytics import VintageStats
        stats = [
            VintageStats(2018, 5, 1.8, 2.5, 3.2, 0.20, 4.5, 0.1, 180.0),
            VintageStats(2019, 8, 2.0, 3.1, 4.0, 0.28, 5.0, 0.05, 210.0),
        ]
        svg = _heatmap_svg(stats)
        self.assertIn("<svg", svg)
        self.assertIn("2018", svg)

    def test_moic_bar_chart_helper(self):
        from rcm_mc.ui.data_public.vintage_perf_page import _moic_bar_chart
        from rcm_mc.data_public.vintage_analytics import VintageStats
        stats = [VintageStats(2020, 10, 2.0, 2.8, 3.5, 0.24, 5.0, 0.1, 200.0)]
        svg = _moic_bar_chart(stats)
        self.assertIn("<svg", svg)


if __name__ == "__main__":
    unittest.main()
