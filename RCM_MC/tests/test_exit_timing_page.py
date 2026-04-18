"""Tests for rcm_mc/ui/data_public/exit_timing_page.py."""
from __future__ import annotations

import unittest


class TestRenderExitTiming(unittest.TestCase):
    def test_renders_html(self):
        from rcm_mc.ui.data_public.exit_timing_page import render_exit_timing
        html = render_exit_timing()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertGreater(len(html), 30_000)

    def test_contains_svgs(self):
        import re
        from rcm_mc.ui.data_public.exit_timing_page import render_exit_timing
        html = render_exit_timing()
        self.assertGreaterEqual(len(re.findall(r"<svg", html)), 3)

    def test_contains_kpis(self):
        from rcm_mc.ui.data_public.exit_timing_page import render_exit_timing
        html = render_exit_timing()
        self.assertIn("P50 Hold Period", html)
        self.assertIn("Short Hold", html)
        self.assertIn("Mid Hold", html)

    def test_contains_sector_table(self):
        from rcm_mc.ui.data_public.exit_timing_page import render_exit_timing
        html = render_exit_timing()
        self.assertIn("Hold Period by Sector", html)

    def test_contains_vintage_panel(self):
        from rcm_mc.ui.data_public.exit_timing_page import render_exit_timing
        html = render_exit_timing()
        self.assertIn("Vintage", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.exit_timing_page import render_exit_timing
        html = render_exit_timing()
        self.assertIn("/exit-timing", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.exit_timing_page import render_exit_timing
        html = render_exit_timing()
        self.assertNotIn("background:#ffffff", html.lower())


class TestHelpers(unittest.TestCase):
    def test_percentile_basic(self):
        from rcm_mc.ui.data_public.exit_timing_page import _percentile
        self.assertAlmostEqual(_percentile([1, 2, 3, 4, 5], 50), 3.0, delta=0.5)

    def test_overall_stats(self):
        from rcm_mc.ui.data_public.exit_timing_page import _overall_stats, _load_corpus
        stats = _overall_stats(_load_corpus())
        self.assertGreater(stats["realized_with_hold"], 100)
        self.assertGreater(stats["hold_p50"], 1.0)
        self.assertLess(stats["hold_p50"], 10.0)

    def test_sector_hold_stats(self):
        from rcm_mc.ui.data_public.exit_timing_page import _sector_hold_stats, _load_corpus
        rows = _sector_hold_stats(_load_corpus())
        self.assertGreater(len(rows), 3)
        p50s = [r["hold_p50"] for r in rows]
        self.assertEqual(p50s, sorted(p50s))  # sorted by P50

    def test_vintage_unrealized(self):
        from rcm_mc.ui.data_public.exit_timing_page import _vintage_unrealized, _load_corpus
        vd = _vintage_unrealized(_load_corpus())
        self.assertGreater(len(vd), 5)
        for yr, data in vd.items():
            self.assertIn("pct_realized", data)
            self.assertGreaterEqual(data["pct_realized"], 0.0)
            self.assertLessEqual(data["pct_realized"], 1.0)

    def test_hold_histogram_svg(self):
        from rcm_mc.ui.data_public.exit_timing_page import _hold_histogram
        svg = _hold_histogram([3.5, 4.2, 5.0, 2.1, 7.3])
        self.assertIn("<svg", svg)
        self.assertIn("<rect", svg)

    def test_hold_moic_scatter_svg(self):
        from rcm_mc.ui.data_public.exit_timing_page import _hold_moic_scatter
        pts = [(3.5, 2.5), (5.0, 3.1), (4.2, 1.8)]
        svg = _hold_moic_scatter(pts)
        self.assertIn("<svg", svg)
        self.assertIn("<circle", svg)

    def test_hold_moic_scatter_empty(self):
        from rcm_mc.ui.data_public.exit_timing_page import _hold_moic_scatter
        self.assertEqual(_hold_moic_scatter([]), "")


if __name__ == "__main__":
    unittest.main()
