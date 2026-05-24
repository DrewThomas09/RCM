"""Data-universe label chips (PR B).

Every confusing page must declare which data universe it shows so a partner
never mistakes a benchmark corpus for their own portfolio. Pins the chip
helper and its application to renderable pages.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_data_universe, chartis_shell


class ChipHelperTests(unittest.TestCase):
    def test_all_kinds_render_label_and_class(self):
        cases = {
            "user-deals": ("USER DEALS", "ck-universe-deals"),
            "user-portfolio": ("USER PORTFOLIO", "ck-universe-port"),
            "cms": ("CMS PUBLIC DATA", "ck-universe-cms"),
            "corpus": ("BENCHMARK CORPUS", "ck-universe-corpus"),
            "research": ("RESEARCH REFERENCE", "ck-universe-ref"),
            "mixed": ("MIXED DATA", "ck-universe-mixed"),
        }
        for kind, (label, cls) in cases.items():
            chip = ck_data_universe(kind)
            with self.subTest(kind=kind):
                self.assertIn(label, chip)
                self.assertIn(cls, chip)
                self.assertIn("title=", chip)        # self-describing tooltip

    def test_unknown_kind_is_safe_empty(self):
        self.assertEqual(ck_data_universe("nope"), "")

    def test_corpus_tooltip_is_explicit_not_portfolio(self):
        self.assertIn("NOT your portfolio", ck_data_universe("corpus"))

    def test_chip_css_present_in_shell(self):
        css = chartis_shell(body="<main/>", title="x")
        self.assertIn(".ck-universe-corpus", css)
        self.assertIn(".ck-universe-deals", css)


class AppliedPageTests(unittest.TestCase):
    def test_portfolio_map_labeled_user_deals(self):
        from rcm_mc.ui.portfolio_map import render_portfolio_map
        h = render_portfolio_map([{"name": "x", "state": "TX"}], con_states={})
        self.assertIn("ck-universe-deals", h)
        self.assertIn("USER DEALS", h)

    def test_find_comps_labeled_benchmark_corpus(self):
        from rcm_mc.ui.data_public.find_comps_page import render_find_comps
        h = render_find_comps({})
        self.assertIn("ck-universe-corpus", h)
        self.assertIn("BENCHMARK CORPUS", h)


if __name__ == "__main__":
    unittest.main()
