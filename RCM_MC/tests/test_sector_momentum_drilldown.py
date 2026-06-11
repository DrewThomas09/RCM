"""Sector Momentum drill-down — each sector row links into Deal Search.

The momentum tables named 129 taxonomy sectors but linked nowhere: a
partner spotting "dialysis +400%" had to retype the sector into Deal
Search by hand. Each sector cell (accelerating block + decelerating
table) now links to /deal-search?sector=<name> — the same corpus field
Deal Search filters on exactly, so the momentum read is one click from
the underlying deals.
"""
from __future__ import annotations

import re
import unittest
from urllib.parse import unquote


class SectorDrilldownTests(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.data_public.sector_momentum_page import (
            render_sector_momentum,
        )
        self.html = render_sector_momentum(5)

    def test_sector_rows_link_to_deal_search(self):
        links = re.findall(r'href="/deal-search\?sector=([^"]+)"', self.html)
        # Both the accelerating (top 10) and decelerating (top 10) tables
        # carry per-sector drill links.
        self.assertGreaterEqual(len(links), 10)

    def test_drill_link_sectors_resolve_in_deal_search(self):
        # The link target filters on the SAME corpus sector field with an
        # exact match — a drifted taxonomy name would 0-row the search.
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        links = re.findall(r'href="/deal-search\?sector=([^"]+)"', self.html)
        sec = unquote(links[0])
        out = render_deal_search(query="", sector=sec)
        self.assertNotIn("No deals match", out)


class DealSearchEvRollupTests(unittest.TestCase):
    def test_ev_column_rolls_to_billions(self):
        # House style: ev_mm ≥ 1000 (i.e. ≥$1B) reads "$2.00B" not "$2000M".
        from rcm_mc.ui.data_public.deal_search_page import render_deal_search
        h = render_deal_search(query="", sector="dialysis")
        self.assertIn("$2.00B", h)
        self.assertNotIn("$2000M", h)

    def test_find_comps_ev_rolls_to_billions(self):
        # Same invariant on the Find Comps results table ("$2.00B" not
        # "$2,000M").
        import re
        from rcm_mc.ui.data_public.find_comps_page import render_find_comps
        h = render_find_comps(
            {"sector": "hospital", "ev_mm": "500", "max_n": "15"})
        self.assertNotRegex(h, r"\$[0-9]{1,3},[0-9]{3}M\b")
        self.assertRegex(h, r"\$[0-9.]+B\b")


if __name__ == "__main__":
    unittest.main()
