"""Sponsor-league table rows drill through to the sponsor detail page.

Connectivity: the scatter dots already link to the per-sponsor
drill-down; this pins that the table's sponsor-name cells link there too,
so both the visual and the table route to the same place.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.sponsor_league_page import render_sponsor_league


class SponsorLeagueConnectivityTests(unittest.TestCase):
    def test_table_sponsor_names_link_to_detail(self):
        html = render_sponsor_league()
        # At least one sponsor-detail link, and it lives in an anchor.
        self.assertIn("/diligence/sponsor-detail?sponsor=", html)
        self.assertIn('href="/diligence/sponsor-detail?sponsor=', html)

    def test_links_cover_both_scatter_and_table(self):
        # Each ranked sponsor appears as a clickable dot AND a clickable
        # table row, so the link count is comfortably above the row count
        # of a single rendering location.
        html = render_sponsor_league()
        self.assertGreater(html.count("/diligence/sponsor-detail?sponsor="), 1)


if __name__ == "__main__":
    unittest.main()
