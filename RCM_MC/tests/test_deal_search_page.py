"""Tests for the deal search page."""
from __future__ import annotations

import unittest


class TestRenderDealSearch(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search()
        self.assertIn("<!doctype html>", html)
        self.assertGreater(len(html), 30_000)

    def test_query_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(query="KKR")
        self.assertIn("KKR", html)
        self.assertIn("Results", html)

    def test_sector_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(sector="Dental")
        self.assertIn("<!doctype html>", html)

    def test_moic_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(moic_lo=3.0)
        self.assertIn("<!doctype html>", html)

    def test_year_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(yr_lo=2018, yr_hi=2022)
        self.assertIn("<!doctype html>", html)

    def test_ev_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(ev_lo=100.0, ev_hi=500.0)
        self.assertIn("<!doctype html>", html)

    def test_no_results(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(query="ZZZNOMATCHXXX")
        self.assertIn("0", html)
        self.assertIn("Results", html)

    def test_sort_by_year(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(sort_by="year")
        self.assertIn("<!doctype html>", html)

    def test_form_present(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search()
        self.assertIn("Search &amp; Filter", html)
        self.assertIn("deal-search", html)

    def test_table_present(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search()
        self.assertIn("EV/EBITDA", html)
        self.assertIn("Payer", html)

    def test_kpi_bar_present(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search()
        self.assertIn("P50 MOIC", html)
        self.assertIn("Avg EV", html)

    def test_nav_link(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search()
        self.assertIn("/deal-search", html)

    def test_no_light_theme(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search()
        self.assertNotIn("background:#ffffff", html.lower())

    def test_page_2(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(page=2)
        self.assertIn("<!doctype html>", html)

    def test_payer_mini_svg(self):
        from rcm_mc.ui.data_public.deal_search_page import _payer_mini
        svg = _payer_mini({"commercial": 0.6, "medicare": 0.3, "medicaid": 0.1})
        self.assertIn("<svg", svg)


if __name__ == "__main__":
    unittest.main()
