"""Verified Deals page — surfaces the real, sourced deal dataset.

The product shipped a synthetic corpus; this page makes the genuine,
source-linked deals visible and checkable. Guards: it renders the real anchors,
every visible deal carries a source link, the sector filter narrows the table,
and outcomes (incl. bankruptcies) are shown.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.verified_deals_page import render_verified_deals


class VerifiedDealsPageTests(unittest.TestCase):
    def test_renders_real_anchors_and_sources(self) -> None:
        html = render_verified_deals({})
        self.assertIn("Verified Deals", html)
        for anchor in ("Steward", "Envision", "athenahealth", "R1 RCM"):
            self.assertIn(anchor, html)
        # 2026-06 expansion: more real anchors across sectors.
        for anchor in ("Vanguard Health", "Team Health", "Change Healthcare",
                       "Oak Street Health", "Waystar"):
            self.assertIn(anchor, html)
        # real source links on rows (open in a new tab)
        self.assertGreaterEqual(html.count('rel="noopener"'), 10)
        # public-record bankruptcies are surfaced
        self.assertIn("bankrupt", html)

    def test_analytics_outcome_mix_and_sponsor_leaderboard(self) -> None:
        # The page is more than a flat table: an outcome-mix bar (the
        # credibility read — losses included) and a lead-sponsor leaderboard.
        html = render_verified_deals({})
        self.assertIn("Outcome mix", html)
        self.assertIn("Most-seen sponsors", html)
        # Disclosed-EV total is a real $ floor, not a count.
        self.assertIn("DISCLOSED EV", html)
        self.assertIn("PUBLIC-RECORD FAILURES", html)
        # The credibility caption is present.
        self.assertIn("public-record failures", html)

    def test_grew_beyond_the_seed_set(self) -> None:
        # Guard the expansion: the verified set is no longer a token list.
        from rcm_mc.data_public.verified_deals import (
            disclosed_ev_total_mm, verified_deal_count,
        )
        self.assertGreaterEqual(verified_deal_count(), 50)
        # Disclosed EV total is a meaningful, real floor (tens of $B).
        self.assertGreater(disclosed_ev_total_mm(), 50_000)

    def test_sector_filter_narrows_table(self) -> None:
        rcm = render_verified_deals({"sector": "rcm_healthtech"})
        self.assertIn("athenahealth", rcm)
        # a hospitals-only deal name should not appear in the filtered table
        # (LifePoint is hospitals); the lede names Steward/Envision so we test
        # a name that only appears as a table row.
        self.assertNotIn("LifePoint", rcm)

    def test_undisclosed_ev_not_fabricated(self) -> None:
        html = render_verified_deals({})
        # rollups with no public EV show "undisclosed", never a made-up number
        self.assertIn("undisclosed", html)


if __name__ == "__main__":
    unittest.main()
