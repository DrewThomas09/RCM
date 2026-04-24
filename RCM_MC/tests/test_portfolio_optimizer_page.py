"""Tests for rcm_mc/ui/data_public/portfolio_optimizer_page.py."""
from __future__ import annotations

import unittest


class TestRenderPortfolioOptimizer(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 20_000)

    def test_renders_with_sectors(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer(sectors=["Physician Practice", "Dental"])
        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("Physician Practice", html)

    def test_hhi_panel_present(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("Concentration Risk", html)
        self.assertIn("Sector HHI", html)

    def test_sector_weights_panel_present(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("Sector Weights", html)

    def test_optimal_weights_panel_present(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("Corpus-Optimal", html)
        self.assertIn("Target Weight", html)

    def test_form_present(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("portfolio-optimizer", html)
        self.assertIn("Analyze Portfolio", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("/portfolio-optimizer", html)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("Portfolio Deals", html)
        self.assertIn("Unique Sectors", html)

    def test_hhi_svg_present(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("<svg", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertNotIn("background:#ffffff", html.lower())

    def test_hhi_bar_helper(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import _hhi_bar
        bar = _hhi_bar(0.10, "Sector HHI")
        self.assertIn("Low", bar)
        self.assertIn("<svg", bar)

    def test_hhi_signal_levels(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import _hhi_signal
        _, lvl_low = _hhi_signal(0.10)
        _, lvl_mod = _hhi_signal(0.20)
        _, lvl_high = _hhi_signal(0.30)
        self.assertEqual(lvl_low, "Low")
        self.assertEqual(lvl_mod, "Moderate")
        self.assertEqual(lvl_high, "High")

    def test_empty_sectors_falls_back_to_default(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer(sectors=[])
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 20_000)

    def test_single_sector(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer(sectors=["Home Health"])
        self.assertIn("<!doctype html>", html.lower())

    def test_subtitle_contains_hhi(self):
        from rcm_mc.ui.data_public.portfolio_optimizer_page import render_portfolio_optimizer
        html = render_portfolio_optimizer()
        self.assertIn("HHI", html)


if __name__ == "__main__":
    unittest.main()
