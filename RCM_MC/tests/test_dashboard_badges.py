"""Tests for live badge counts on the dashboard's Daily workflow section.

The badges show a partner what's actually waiting for them when they
land on /dashboard:
  - watchlist size
  - active alerts
  - overdue deadlines
  - saved searches

Each badge is best-effort — missing tables on a fresh DB must NOT
break the render, and zero-count surfaces must not show a chip at
all (avoids visual noise on a clean inbox).
"""
from __future__ import annotations

import os
import re
import sqlite3
import tempfile
import unittest


class TestEmptyDbNoBadges(unittest.TestCase):
    """A freshly-bootstrapped DB has 0 alerts, 0 watchlist entries, etc.
    None of those should render a badge — the row should look the same
    as before badges shipped."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_zero_state_omits_chips(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Nothing in the database means no chip should appear anywhere
        # in the rendered Daily workflow section. We slice the section
        # to avoid false positives from elsewhere on the page.
        m = re.search(
            r"Daily workflow.*?</section>", html, flags=re.S,
        )
        self.assertIsNotNone(m, msg="Daily workflow section not found")
        section = m.group(0)
        # Badge wrapper shape — `border-radius:9999px;` on a small chip.
        # If counts are all 0/None, no chips should be in the section.
        self.assertNotIn("border-radius:9999px", section)


class TestBadgesPopulate(unittest.TestCase):
    """Seed the underlying tables and confirm the badges show up."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_watchlist_count_appears_when_starred(self):
        from rcm_mc.deals.watchlist import star_deal
        # Pin two hospitals
        star_deal(self.store, "010001")
        star_deal(self.store, "010002")

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Find the Watchlist row and confirm a chip with "2" rendered
        # next to the link.
        m = re.search(
            r'Watchlist</a><span[^>]*border-radius:9999px[^>]*>(\d+)</span>',
            html,
        )
        self.assertIsNotNone(
            m, msg="watchlist=2 should produce a count chip after the link",
        )
        self.assertEqual(m.group(1), "2",
                         msg=f"chip count was {m.group(1)!r}, expected '2'")


class TestBadgeHelpers(unittest.TestCase):
    def test_badge_helper_omits_zero(self):
        from rcm_mc.ui.dashboard_page import _badge
        self.assertEqual(_badge(0), "")
        self.assertEqual(_badge(None), "")

    def test_badge_helper_renders_positive(self):
        from rcm_mc.ui.dashboard_page import _badge
        out = _badge(7)
        self.assertIn(">7<", out)
        self.assertIn("border-radius:9999px", out)

    def test_alert_level_palette(self):
        from rcm_mc.ui.dashboard_page import _badge
        # Each level produces a distinct background color — cheap proxy
        # for "the palette dispatch wired correctly".
        out_alert = _badge(1, level="alert")
        out_warn = _badge(1, level="warn")
        out_ok = _badge(1, level="ok")
        out_neutral = _badge(1, level="neutral")
        self.assertNotEqual(out_alert, out_warn)
        self.assertNotEqual(out_alert, out_ok)
        self.assertNotEqual(out_warn, out_neutral)


class TestBadgeFailureGraceful(unittest.TestCase):
    """If any underlying helper raises, the dashboard still renders —
    the badge value just becomes None and nothing visual appears."""

    def test_render_survives_alerts_failure(self):
        from unittest.mock import patch
        tmp = tempfile.TemporaryDirectory()
        db = os.path.join(tmp.name, "t.db")
        try:
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db)
            with patch("rcm_mc.alerts.alerts.active_count",
                       side_effect=RuntimeError("simulated failure")):
                from rcm_mc.ui.dashboard_page import render_dashboard
                html = render_dashboard(db)
            self.assertIn("Daily workflow", html,
                          msg="dashboard must render even when a count source dies")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
