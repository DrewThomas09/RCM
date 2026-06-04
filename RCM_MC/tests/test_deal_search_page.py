"""Tests for the deal search page."""
from __future__ import annotations

import unittest


class TestRenderDealSearch(unittest.TestCase):
    def test_renders_default(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search()
        self.assertIn("<!doctype html>", html.lower())
        self.assertGreater(len(html), 30_000)

    def test_query_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(query="KKR")
        self.assertIn("KKR", html)
        self.assertIn("Results", html)

    def test_query_is_token_prefix_not_substring(self):
        """Regression: raw-substring search matched 'hca' inside 'healthcare',
        so searching the company 'HCA' returned scores of unrelated healthcare
        deals. Query must match on token prefixes — 'hca' must NOT match a deal
        whose only hit is the word 'healthcare'."""
        from rcm_mc.ui.data_public.deal_search_page import _match_deal
        healthcare_only = {"deal_name": "Acme Healthcare Partners", "buyer": "X"}
        real_hca = {"deal_name": "HCA Healthcare", "buyer": "KKR"}
        # 'hca' is a substring of 'healthcare' but not a token prefix of it.
        self.assertFalse(_match_deal(healthcare_only, "HCA", "", None, None,
                                     None, None, None, None, ""))
        self.assertTrue(_match_deal(real_hca, "HCA", "", None, None,
                                    None, None, None, None, ""))

    def test_query_prefix_and_multiword(self):
        """Prefix search is preserved ('ortho' -> orthopedics) and multi-word
        queries are order-independent (each token must prefix some token)."""
        from rcm_mc.ui.data_public.deal_search_page import _match_deal
        d = {"deal_name": "Orthopedic Surgery Partners", "sector": "asc"}
        self.assertTrue(_match_deal(d, "ortho", "", None, None, None, None, None, None, ""))
        self.assertTrue(_match_deal(d, "surgery partners", "", None, None, None, None, None, None, ""))
        self.assertTrue(_match_deal(d, "partners surgery", "", None, None, None, None, None, None, ""))
        # A token with no prefix hit fails the AND.
        self.assertFalse(_match_deal(d, "surgery cardiology", "", None, None, None, None, None, None, ""))

    def test_deal_type_canonicalization(self):
        """deal_type is uncontrolled free text ('lbo', 'LBO', 'Platform LBO').
        The canonical bucketing must collapse casing/phrasing variants so the
        dropdown isn't fragmented and selecting a type captures them all."""
        from rcm_mc.ui.data_public.deal_search_page import _canon_deal_type
        self.assertEqual(_canon_deal_type("lbo"), "lbo")
        self.assertEqual(_canon_deal_type("LBO"), "lbo")
        self.assertEqual(_canon_deal_type("Platform LBO"), "lbo")
        self.assertEqual(_canon_deal_type("Take-private"), "take_private")
        self.assertEqual(_canon_deal_type("Public-to-Private"), "take_private")
        self.assertEqual(_canon_deal_type("Corporate Carve-Out LBO"), "carve_out")
        self.assertEqual(_canon_deal_type("Growth Equity"), "growth_equity")
        # Missing type returns "" so the "All Types" default skips the filter.
        self.assertEqual(_canon_deal_type(None), "")
        self.assertEqual(_canon_deal_type(""), "")

    def test_deal_type_filter_captures_variants(self):
        """Selecting the canonical 'lbo' must return at least as many deals as
        the old exact-string match did — the previously-stranded casing/phrasing
        variants are now reachable, and the dropdown has no case-duplicates."""
        from rcm_mc.ui.data_public.deal_search_page import (
            render_deal_search, _load_corpus, _canon_deal_type,
        )
        corpus = _load_corpus()
        exact = sum(1 for d in corpus if d.get("deal_type") == "lbo")
        canon = sum(1 for d in corpus if _canon_deal_type(d.get("deal_type")) == "lbo")
        self.assertGreaterEqual(canon, exact)
        self.assertGreater(canon, 0)
        # The dropdown options must be canonical (lower_snake, no spaces/caps).
        opts = sorted({_canon_deal_type(d.get("deal_type"))
                       for d in corpus if d.get("deal_type")})
        for o in opts:
            self.assertEqual(o, o.lower())
            self.assertNotIn(" ", o)
        html = render_deal_search(deal_type="lbo")
        self.assertIn("Results", html)

    def test_sector_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(sector="Dental")
        self.assertIn("<!doctype html>", html.lower())

    def test_moic_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(moic_lo=3.0)
        self.assertIn("<!doctype html>", html.lower())

    def test_year_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(yr_lo=2018, yr_hi=2022)
        self.assertIn("<!doctype html>", html.lower())

    def test_ev_filter(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(ev_lo=100.0, ev_hi=500.0)
        self.assertIn("<!doctype html>", html.lower())

    def test_no_results(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(query="ZZZNOMATCHXXX")
        self.assertIn("0", html)
        self.assertIn("Results", html)

    def test_sort_by_year(self):
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        html = render_deal_search(sort_by="year")
        self.assertIn("<!doctype html>", html.lower())

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
        self.assertIn("<!doctype html>", html.lower())

    def test_payer_mini_svg(self):
        from rcm_mc.ui.data_public.deal_search_page import _payer_mini
        svg = _payer_mini({"commercial": 0.6, "medicare": 0.3, "medicaid": 0.1})
        self.assertIn("<svg", svg)


if __name__ == "__main__":
    unittest.main()
