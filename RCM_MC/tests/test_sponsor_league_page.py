"""Tests for rcm_mc/ui/data_public/sponsor_league_page.py."""
from __future__ import annotations

import unittest


class TestRenderSponsorLeague(unittest.TestCase):
    def test_renders_html(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        self.assertIn("<!doctype html>", html)
        self.assertGreater(len(html), 50_000)

    def test_contains_league_table(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        self.assertIn("Sponsor League Table", html)

    def test_contains_consistency_score(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        self.assertIn("Consistency", html)

    def test_contains_known_sponsors(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        # At least one major sponsor should appear
        has_sponsor = any(s in html for s in ["KKR", "Blackstone", "Carlyle", "Warburg", "Bain"])
        self.assertTrue(has_sponsor)

    def test_sort_by_deal_count(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league(sort_by="deal_count")
        self.assertIn("<!doctype html>", html)

    def test_sort_by_consistency(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league(sort_by="consistency")
        self.assertIn("<!doctype html>", html)

    def test_min_deals_5(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league(min_deals=5)
        self.assertIn("<!doctype html>", html)

    def test_nav_link_present(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        self.assertIn("/sponsor-league", html)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        self.assertIn("Sponsors Ranked", html)

    def test_methodology_panel(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        self.assertIn("Methodology", html)
        self.assertIn("Consistency Score", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        self.assertNotIn("background:#ffffff", html.lower())

    def test_moic_formatted_with_x(self):
        from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league
        html = render_sponsor_league()
        self.assertIn("×", html)

    def test_consistency_bar_svg(self):
        from rcm_mc.ui.data_public.sponsor_league_page import _consistency_bar
        bar = _consistency_bar(75.0)
        self.assertIn("<svg", bar)
        self.assertIn("75", bar)

    def test_sparkline_svg(self):
        from rcm_mc.ui.data_public.sponsor_league_page import _sparkline_moics
        spark = _sparkline_moics([1.2, 2.5, 3.1, 1.8])
        self.assertIn("<svg", spark)

    def test_sparkline_empty(self):
        from rcm_mc.ui.data_public.sponsor_league_page import _sparkline_moics
        self.assertEqual(_sparkline_moics([]), "")


class TestHelpers(unittest.TestCase):
    def test_moic_color_critical(self):
        from rcm_mc.ui.data_public.sponsor_league_page import _moic_color
        self.assertIn("b5321e", _moic_color(0.8))

    def test_moic_color_green(self):
        from rcm_mc.ui.data_public.sponsor_league_page import _moic_color
        self.assertIn("22c55e", _moic_color(3.0))

    def test_loss_color_red(self):
        from rcm_mc.ui.data_public.sponsor_league_page import _loss_color
        self.assertIn("b5321e", _loss_color(0.35))

    def test_loss_color_green(self):
        from rcm_mc.ui.data_public.sponsor_league_page import _loss_color
        self.assertIn("22c55e", _loss_color(0.05))


if __name__ == "__main__":
    unittest.main()
