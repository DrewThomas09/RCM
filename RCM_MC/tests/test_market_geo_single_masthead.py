"""Regression: the geographic market-intel page rendered its masthead
twice.

chartis_shell already renders the page masthead from its title +
editorial_intro, but the body *also* opened with a ck_page_title, so
"Market Intelligence · Geographic" appeared as two stacked headers. The
body masthead was removed (the coverage meta is kept as a slim line);
there must be exactly one page-title header.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.market_geo_page import render_market_geo_index


class GeoSingleMastheadTests(unittest.TestCase):
    def test_one_page_title_header(self):
        html = render_market_geo_index({})
        self.assertEqual(html.count('class="ck-page-title"'), 1)

    def test_coverage_meta_preserved(self):
        html = render_market_geo_index({})
        self.assertIn("state values", html)
        self.assertIn("SimplyAnalytics-derived", html)


if __name__ == "__main__":
    unittest.main()
