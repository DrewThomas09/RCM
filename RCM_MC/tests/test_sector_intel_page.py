"""Tests for sector intelligence analytics and /sector-intel page."""
from __future__ import annotations

import unittest


class TestSectorIntelligence(unittest.TestCase):
    def _mini_corpus(self):
        return [
            {"source_id": f"t{i:02}", "deal_name": f"Deal {i}", "buyer": "B", "seller": "S",
             "ev_mm": 100.0 + i * 10, "hold_years": 4.0, "realized_moic": 2.0 + i * 0.1,
             "realized_irr": 0.18, "payer_mix": {}, "sector": "physician_group",
             "year": 2018 + (i % 5)}
            for i in range(8)
        ] + [
            {"source_id": f"h{i:02}", "deal_name": f"Hospital {i}", "buyer": "B", "seller": "S",
             "ev_mm": 500.0, "hold_years": 6.0, "realized_moic": 1.5 + i * 0.2,
             "realized_irr": 0.12, "payer_mix": {}, "sector": "hospital",
             "year": 2015 + i}
            for i in range(5)
        ]

    def test_compute_stats(self):
        from rcm_mc.data_public.sector_intelligence import compute_sector_stats
        corpus = self._mini_corpus()
        stats = compute_sector_stats(corpus)
        self.assertGreater(len(stats), 0)
        sectors = [s.sector for s in stats]
        self.assertIn("physician_group", sectors)
        self.assertIn("hospital", sectors)

    def test_percentiles_ordered(self):
        from rcm_mc.data_public.sector_intelligence import compute_sector_stats
        stats = compute_sector_stats(self._mini_corpus())
        for s in stats:
            self.assertLessEqual(s.moic_p25, s.moic_p50)
            self.assertLessEqual(s.moic_p50, s.moic_p75)

    def test_loss_rate_range(self):
        from rcm_mc.data_public.sector_intelligence import compute_sector_stats
        stats = compute_sector_stats(self._mini_corpus())
        for s in stats:
            self.assertGreaterEqual(s.loss_rate, 0.0)
            self.assertLessEqual(s.loss_rate, 1.0)

    def test_sharpe_proxy(self):
        from rcm_mc.data_public.sector_intelligence import compute_sector_stats
        stats = compute_sector_stats(self._mini_corpus())
        # All moic > 1, so sharpe should be positive
        for s in stats:
            if s.moic_p50 > 1.0:
                self.assertGreater(s.sharpe_proxy, 0)

    def test_sorted_by_moic(self):
        from rcm_mc.data_public.sector_intelligence import compute_sector_stats
        stats = compute_sector_stats(self._mini_corpus())
        moics = [s.moic_p50 for s in stats]
        self.assertEqual(moics, sorted(moics, reverse=True))

    def test_vintage_moic_populated(self):
        from rcm_mc.data_public.sector_intelligence import compute_sector_stats
        stats = compute_sector_stats(self._mini_corpus())
        pg = next(s for s in stats if s.sector == "physician_group")
        self.assertGreater(len(pg.vintage_moic), 0)

    def test_full_corpus(self):
        from rcm_mc.data_public.sector_intelligence import compute_sector_stats
        import importlib
        from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
        corpus = []
        for i in range(15, 20):
            try:
                mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
                corpus += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
            except (ImportError, AttributeError):
                pass
        stats = compute_sector_stats(corpus)
        self.assertGreater(len(stats), 0)


class TestRenderSectorIntel(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertGreater(len(html), 30_000)

    def test_scatter_svg_present(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel()
        self.assertIn("<svg", html)
        self.assertIn("P50 MOIC vs Loss Rate", html)

    def test_table_present(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel()
        self.assertIn("Sector Performance", html)
        self.assertIn("Loss %", html)
        self.assertIn("Avg Hold", html)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel()
        self.assertIn("Sectors Analyzed", html)
        self.assertIn("Top Sector", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel()
        self.assertIn("/sector-intel", html)

    def test_sort_by_loss_rate(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel(sort_by="loss_rate")
        self.assertIn("<!DOCTYPE html>", html)

    def test_min_deals_filter(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel(min_deals=10)
        self.assertIn("<!DOCTYPE html>", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel()
        self.assertNotIn("background:#ffffff", html.lower())

    def test_sparklines_present(self):
        from rcm_mc.ui.data_public.sector_intel_page import render_sector_intel
        html = render_sector_intel()
        self.assertIn("polyline", html)

    def test_moic_spread_bar_helper(self):
        from rcm_mc.ui.data_public.sector_intel_page import _moic_spread_bar
        bar = _moic_spread_bar(1.5, 2.5, 3.5)
        self.assertIn("<svg", bar)

    def test_sparkline_helper(self):
        from rcm_mc.ui.data_public.sector_intel_page import _sparkline
        svg = _sparkline({2018: [2.0, 2.5], 2019: [3.0], 2020: [2.2]})
        self.assertIn("<svg", svg)


if __name__ == "__main__":
    unittest.main()
