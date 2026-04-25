"""Tests for the dashboard's "Needs attention today" auto-triage card.

Complement to "Pinned deals" — Pinned shows deals the partner
explicitly starred; this section shows deals the TOOL auto-flagged
via the risk-scan priority ranker. A covenant-tripped deal the
partner hasn't starred still surfaces here.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone


def _seed_deal(store, deal_id: str, name: str,
               covenant_status: str = "SAFE") -> None:
    """Raw-SQL seed to avoid depending on higher-level deal APIs."""
    now = datetime.now(timezone.utc).isoformat()
    store.init_db()
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name, now, json.dumps({"sector": "hospital"})),
        )
        con.commit()


class TestNoDealsHidesCard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_deals_no_card(self):
        """An empty portfolio shouldn't show the 'Needs attention'
        section at all — the rest of the dashboard already has an
        empty-state message."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertNotIn("Needs attention today", html)


class TestHealthyPortfolioShowsReassurance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        _seed_deal(self.store, "DEAL_HEALTHY", "Healthy Hospital",
                   covenant_status="SAFE")

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_flags_shows_green_reassurance(self):
        """When every deal has priority=0, show a reassurance
        message rather than a blank card or an empty list."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Needs attention today", html)
        self.assertIn("Everything looks healthy", html)


class TestFlaggedDealsSurface(unittest.TestCase):
    """When we seed a concerning_signals snapshot or similar that
    trips the priority ranker, the deal appears in the card."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        _seed_deal(self.store, "DEAL_BAD", "Problem Hospital")

    def tearDown(self):
        self.tmp.cleanup()

    def test_overdue_deadline_surfaces_deal(self):
        """Overdue deadlines flip priority_rank > 0, so the deal
        appears in the Needs-attention card."""
        from rcm_mc.deals.deal_deadlines import add_deadline
        # Seed a past-due deadline
        add_deadline(
            self.store, deal_id="DEAL_BAD",
            label="IOI response",
            due_date="2020-01-01",  # long overdue
            owner="partner",
        )

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Needs attention today", html)
        self.assertIn("DEAL_BAD", html)
        self.assertIn("overdue deadline", html)


class TestCapAtThree(unittest.TestCase):
    """Card shows top 3 + a "see all N" link pointing at
    /portfolio/risk-scan. Regression guard against the card
    ballooning to show every flagged deal."""

    def test_more_than_three_shows_link(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            store = PortfolioStore(db)
            from rcm_mc.deals.deal_deadlines import add_deadline
            for i in range(5):
                _seed_deal(store, f"DEAL_{i}", f"Hospital {i}")
                add_deadline(store, deal_id=f"DEAL_{i}",
                             label="overdue thing",
                             due_date="2020-01-01", owner="partner")

            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(db)

            # Card title has the full count
            self.assertIn("Needs attention today (5)", html)
            # Link to the full scanner present
            self.assertIn("/portfolio/risk-scan", html)
            # Only 3 deal_id labels in the section — we render the
            # card body then look at the deal-id spans
            import re
            section_start = html.find("Needs attention today")
            # Close the section_card wrapper — look for the next </section>
            section_end = html.find("</section>", section_start)
            section = html[section_start:section_end]
            # Each deal renders a monospace deal_id badge
            deal_links = re.findall(r'/deal/DEAL_\d+', section)
            # Three unique deal links
            self.assertLessEqual(len(set(deal_links)), 3,
                                 msg=f"expected ≤3 deal cards, got {len(set(deal_links))}")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
