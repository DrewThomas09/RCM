"""Tests for the dashboard's "Quiet too long" card.

Surfaces watchlisted deals not opened in 14+ days. The complement
to "Needs attention": the deal nobody is yelling at might be the
one that needs fresh eyes more than the one pinging daily.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


def _seed_deal(store, deal_id: str, name: str = "Test") -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name, datetime.now(timezone.utc).isoformat(),
             json.dumps({"sector": "hospital"})),
        )
        con.commit()


def _seed_audit_event(store, target: str, days_ago: int) -> None:
    """Plant an audit_events row with a backdated `at` timestamp."""
    from rcm_mc.auth.audit_log import _ensure_table, log_event
    _ensure_table(store)
    log_event(store, actor="alice", action="view.deal",
              target=target)
    # Backdate the row we just inserted
    when = (datetime.now(timezone.utc)
            - timedelta(days=days_ago)).isoformat()
    with store.connect() as con:
        con.execute(
            "UPDATE audit_events SET at = ? WHERE target = ? "
            "AND id = (SELECT MAX(id) FROM audit_events WHERE target = ?)",
            (when, target, target),
        )
        con.commit()


class TestQuietTooLong(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_watchlist_no_section(self):
        """Empty watchlist → no card."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertNotIn("Quiet too long", html)

    def test_no_audit_table_no_section(self):
        """Watchlist exists but audit_events table doesn't (fresh
        DB) → section silently omitted."""
        _seed_deal(self.store, "DEAL_A", "Hospital A")
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "DEAL_A")

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # No table, no card
        self.assertNotIn("Quiet too long", html)

    def test_recently_viewed_deals_filtered_out(self):
        """A deal viewed 5d ago isn't quiet — section either omits
        it or omits the whole section if it's the only deal."""
        _seed_deal(self.store, "RECENT", "Recent View")
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "RECENT")
        _seed_audit_event(self.store, "RECENT", days_ago=5)

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Only one starred deal and it's not quiet → no section
        self.assertNotIn("Quiet too long", html)

    def test_deal_unviewed_for_60_days_surfaces(self):
        """Stale watchlist entry → appears in the card."""
        _seed_deal(self.store, "STALE", "Forgotten Deal")
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "STALE")
        _seed_audit_event(self.store, "STALE", days_ago=60)

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Quiet too long", html)
        self.assertIn("STALE", html)
        # 60d quiet → red palette
        self.assertIn("60d quiet", html)
        self.assertIn("#fee2e2", html)

    def test_never_viewed_deal_surfaces_with_red_chip(self):
        """A starred deal with NO audit_events at all → 'never
        viewed' label, red palette (treated as worst)."""
        _seed_deal(self.store, "NEVER", "Never Viewed")
        # Seed audit table by writing a UNRELATED event so the
        # table exists but our deal has no rows
        from rcm_mc.auth.audit_log import _ensure_table, log_event
        _ensure_table(self.store)
        log_event(self.store, actor="x", action="login.success",
                  target="login")
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "NEVER")

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Quiet too long", html)
        self.assertIn("NEVER", html)
        self.assertIn("never viewed", html)


if __name__ == "__main__":
    unittest.main()
