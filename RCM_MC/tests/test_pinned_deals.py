"""Tests for the dashboard's "Pinned deals" mini-card.

The card shows watchlist-starred deals with their current health
score + the top-impact component. Goal: partner sees "which of my
important deals changed" without clicking anywhere.

Contract:
  - No watchlist → no section at all (saves vertical space for
    partners who haven't starred anything yet).
  - Watchlist with N deals (N ≤ 12) → N cards.
  - Watchlist with N > 12 deals → cap at 12 cards (full list still
    in /watchlist).
  - Compute failures on individual deals → skipped, not fatal.
  - Each card links to /deal/<id>.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch


class TestPinnedDealsEmpty(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_watchlist_no_section(self):
        """A partner who hasn't starred anything sees no section —
        not an empty card, not a "star a deal to pin it" nag. The
        whole section is omitted."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertNotIn("Pinned deals", html)


class TestPinnedDealsPopulates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "DEAL_042")
        star_deal(self.store, "DEAL_017")

    def tearDown(self):
        self.tmp.cleanup()

    def test_section_rendered_with_counter(self):
        """Card title includes the count so a partner knows there
        are 2 pinned deals without counting the chips."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Pinned deals (2)", html)

    def test_each_pin_links_to_deal_page(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn('href="/deal/DEAL_042"', html)
        self.assertIn('href="/deal/DEAL_017"', html)

    def test_health_compute_failure_skips_deal(self):
        """If compute_health() raises on one deal, the other deals
        still render — the section is convenience, not critical."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        original_compute_health = None

        def _flaky(store, deal_id):
            if deal_id == "DEAL_017":
                raise RuntimeError("simulated compute failure")
            return {"deal_id": deal_id, "score": 72, "band": "good",
                    "components": [{"label": "OK", "impact": 0,
                                    "detail": ""}]}

        with patch("rcm_mc.deals.health_score.compute_health",
                   side_effect=_flaky):
            html = render_dashboard(self.db)

        # Good deal still appears
        self.assertIn("DEAL_042", html)
        # Flaky deal dropped from the Pinned-deals card. Other
        # sections (e.g. Predicted exit outcomes) iterate the
        # watchlist independent of compute_health and may still
        # reference the deal — that's fine; this test asserts
        # only that the Pinned-deals card itself drops the broken
        # row. Bound the slice to the next </section> so we don't
        # bleed into adjacent cards.
        section_start = html.find("Pinned deals")
        section_end = html.find("</section>", section_start)
        section = (html[section_start:section_end]
                   if section_start >= 0 and section_end > 0 else "")
        self.assertNotIn('href="/deal/DEAL_017"', section,
                         msg="Pinned deals card should NOT link to "
                             "DEAL_017 when its health compute failed")

    def test_cap_at_12_pins(self):
        """Watchlist of 20 deals → 12 cards on dashboard (cap).
        Full list still available at /watchlist."""
        from rcm_mc.deals.watchlist import star_deal
        for i in range(20):
            star_deal(self.store, f"DEAL_{i:03d}")

        # Mock compute_health to return consistent data for all
        with patch("rcm_mc.deals.health_score.compute_health",
                   return_value={"score": 75, "band": "good",
                                 "components": []}):
            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(self.db)

        # Count /deal/ links in the Pinned deals section
        import re
        section_start = html.find("Pinned deals")
        section_end = html.find("section", section_start + 100)
        section = html[section_start:section_end + 20] if section_start >= 0 else ""
        deal_links = re.findall(r'href="/deal/DEAL_\d+"', section)
        self.assertEqual(len(deal_links), 12,
                         msg=f"cap should render 12 cards, got {len(deal_links)}")


class TestPinnedDealsSafety(unittest.TestCase):
    def test_malicious_deal_id_is_escaped(self):
        """Deal IDs come from user input (watchlist star_deal).
        Any ID that somehow contains HTML metacharacters must be
        escaped before injection into the card."""
        tmp = tempfile.TemporaryDirectory()
        db = os.path.join(tmp.name, "t.db")
        try:
            from rcm_mc.portfolio.store import PortfolioStore
            store = PortfolioStore(db)
            from rcm_mc.deals.watchlist import star_deal
            star_deal(store, '<script>alert(1)</script>')

            with patch("rcm_mc.deals.health_score.compute_health",
                       return_value={"score": 50, "band": "fair",
                                     "components": []}):
                from rcm_mc.ui.dashboard_page import render_dashboard
                html = render_dashboard(db)
            # Raw script tag must NOT appear
            self.assertNotIn("<script>alert(1)</script>", html)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
