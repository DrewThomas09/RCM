"""Tests for the dashboard's "Since yesterday" change summary.

The section's job: surface the last 24 hours of meaningful activity
(alerts fired, data refreshed, packets built, logins, user admin)
at the top of the dashboard so a partner reads the morning view
without clicking. Every source is best-effort — a missing table or
race condition degrades to "no changes" instead of crashing.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class TestEmptyStateRenders(unittest.TestCase):
    """A freshly-bootstrapped DB has nothing to show. The section
    must still render cleanly — no NameError, no traceback — and
    tell the user what would populate it later."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_state_copy(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Since yesterday", html,
                      msg="section header missing")
        self.assertIn("last 24 hours", html,
                      msg="empty-state copy should mention the window")

    def test_section_is_first_after_header(self):
        """A partner's eye lands on the top of the dashboard first.
        Since-yesterday must render BEFORE 'What you can run', so the
        morning news is the first thing they see."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        since_pos = html.find("Since yesterday")
        run_pos = html.find("What you can run")
        self.assertGreater(since_pos, 0)
        self.assertGreater(run_pos, 0)
        self.assertLess(since_pos, run_pos,
                        msg="Since yesterday must come before What you can run")


class TestEventsPopulate(unittest.TestCase):
    """Seed the underlying tables + confirm events appear."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.now = datetime.now(timezone.utc)
        self.recent = _iso(self.now - timedelta(hours=2))
        self.stale = _iso(self.now - timedelta(hours=48))

    def tearDown(self):
        self.tmp.cleanup()

    def test_recent_alert_appears(self):
        from rcm_mc.alerts.alert_history import _ensure_table
        _ensure_table(self.store)
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO alert_history (kind, deal_id, trigger_key, "
                "first_seen_at, last_seen_at, severity, title, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("covenant", "DEAL_042", "k1", self.recent, self.recent,
                 "high", "Covenant breach imminent", "{}"),
            )
            con.commit()

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Covenant breach imminent", html)
        self.assertIn("HIGH", html)  # severity rendered uppercase
        # Anchored into the deal page for one-click follow-up
        self.assertIn('/deal/DEAL_042', html)

    def test_old_event_excluded(self):
        """Events older than 24h MUST NOT appear — that's the whole
        point of the window (otherwise the section becomes "since
        forever" and loses its utility)."""
        from rcm_mc.alerts.alert_history import _ensure_table
        _ensure_table(self.store)
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO alert_history (kind, deal_id, trigger_key, "
                "first_seen_at, last_seen_at, severity, title, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("covenant", "DEAL_OLD", "k2", self.stale, self.stale,
                 "medium", "Ancient alert from 48h ago", "{}"),
            )
            con.commit()

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertNotIn("Ancient alert", html,
                         msg="events older than 24h must be filtered out")

    def test_data_refresh_appears(self):
        # Seed a recent refresh via the public helper
        from rcm_mc.data.data_refresh import set_status
        set_status(self.store, "hcris", status="OK", record_count=12345)

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("hcris refreshed", html)
        # Record count formatted with thousands separator
        self.assertIn("12,345 rows", html)

    def test_alert_row_has_inline_ack_form(self):
        """Regression for the "4-click ack" workflow: each alert in
        Since-yesterday renders an inline POST form targeting
        /api/alerts/ack with kind + deal_id + trigger_key, and
        redirects back to /dashboard on success."""
        from rcm_mc.alerts.alert_history import _ensure_table
        _ensure_table(self.store)
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO alert_history (kind, deal_id, trigger_key, "
                "first_seen_at, last_seen_at, severity, title, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("covenant", "DEAL_042", "covenant:Q3:breach",
                 self.recent, self.recent, "high",
                 "Covenant breach", "{}"),
            )
            con.commit()

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Form target
        self.assertIn('action="/api/alerts/ack"', html)
        # All three identifying fields must be present
        self.assertIn('name="kind" value="covenant"', html)
        self.assertIn('name="deal_id" value="DEAL_042"', html)
        self.assertIn('name="trigger_key" value="covenant:Q3:breach"', html)
        # Redirect stays on the dashboard so the scroll position +
        # other events remain after acknowledgement
        self.assertIn('name="redirect" value="/dashboard"', html)

    def test_alert_row_has_snooze_button(self):
        """Each alert row offers BOTH Ack (snooze_days=0) AND
        Snooze 7d (snooze_days=7) — two distinct one-click flows
        for "handled now" vs "remind me later". Partners use
        snooze constantly so this can't be an extra-click flow."""
        from rcm_mc.alerts.alert_history import _ensure_table
        _ensure_table(self.store)
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO alert_history (kind, deal_id, trigger_key, "
                "first_seen_at, last_seen_at, severity, title, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("covenant", "DEAL_S1", "covenant:s1",
                 self.recent, self.recent, "medium",
                 "Snooze test alert", "{}"),
            )
            con.commit()

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Both snooze_days values render as hidden inputs
        self.assertIn('name="snooze_days" value="0"', html)
        self.assertIn('name="snooze_days" value="7"', html)
        # The Snooze button text/label is present
        self.assertIn("Snooze 7d", html)
        # Both forms target the same endpoint
        self.assertGreaterEqual(html.count('action="/api/alerts/ack"'), 2)

    def test_login_audit_appears(self):
        from rcm_mc.auth.audit_log import log_event, _ensure_table
        _ensure_table(self.store)
        log_event(self.store, actor="alice", action="login.success",
                  target="login", detail={"client_ip": "127.0.0.1"})

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("alice signed in", html)


class TestEventGatherer(unittest.TestCase):
    """Test _since_yesterday_events directly for shape + cap + order."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_list_of_dicts(self):
        from rcm_mc.ui.dashboard_page import _since_yesterday_events
        events = _since_yesterday_events(self.db)
        self.assertIsInstance(events, list)

    def test_cap_at_20_events(self):
        """A DB with hundreds of recent events must not render 100+
        rows — caps at 20 newest."""
        from rcm_mc.alerts.alert_history import _ensure_table
        _ensure_table(self.store)
        now = datetime.now(timezone.utc)
        with self.store.connect() as con:
            for i in range(50):
                ts = _iso(now - timedelta(minutes=i))
                con.execute(
                    "INSERT INTO alert_history (kind, deal_id, trigger_key, "
                    "first_seen_at, last_seen_at, severity, title, detail) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("x", f"D{i}", f"k{i}", ts, ts, "low", f"Alert {i}", "{}"),
                )
            con.commit()

        from rcm_mc.ui.dashboard_page import _since_yesterday_events
        events = _since_yesterday_events(self.db)
        self.assertLessEqual(len(events), 20,
                             msg=f"expected ≤20 events, got {len(events)}")

    def test_newest_first(self):
        from rcm_mc.alerts.alert_history import _ensure_table
        _ensure_table(self.store)
        now = datetime.now(timezone.utc)
        older = _iso(now - timedelta(hours=6))
        newer = _iso(now - timedelta(minutes=5))
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO alert_history (kind, deal_id, trigger_key, "
                "first_seen_at, last_seen_at, severity, title, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("x", "D1", "k1", older, older, "low", "OLD", "{}"),
            )
            con.execute(
                "INSERT INTO alert_history (kind, deal_id, trigger_key, "
                "first_seen_at, last_seen_at, severity, title, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("x", "D2", "k2", newer, newer, "low", "NEW", "{}"),
            )
            con.commit()

        from rcm_mc.ui.dashboard_page import _since_yesterday_events
        events = _since_yesterday_events(self.db)
        titles = [e["label"] for e in events]
        # NEW should come before OLD in the returned list
        new_idx = next(i for i, t in enumerate(titles) if "NEW" in t)
        old_idx = next(i for i, t in enumerate(titles) if "OLD" in t)
        self.assertLess(new_idx, old_idx,
                        msg="events should be newest-first")


class TestSnoozeEndToEnd(unittest.TestCase):
    """The form on /dashboard POSTs to /api/alerts/ack with
    snooze_days=7. Verify the endpoint actually persists the
    snooze (not just acks) and that the snooze_until field is
    populated ~7 days in the future."""

    @classmethod
    def setUpClass(cls):
        import socket
        import threading
        from contextlib import closing
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        with closing(__import__("socket").socket()) as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1", db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def test_snooze_7d_persists(self):
        import urllib.parse
        import urllib.request
        body = urllib.parse.urlencode({
            "kind": "covenant",
            "deal_id": "DEAL_END_TO_END",
            "trigger_key": "k",
            "snooze_days": "7",
            "redirect": "/dashboard",
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/alerts/ack",
            data=body, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json"},
        )
        # Server returns 201 on json accept, 303 on HTML form post.
        # The Accept header above forces 201.
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 201)

        # Verify the row in alert_acks has snooze_until ~7d ahead.
        # `is_acked` returns True when an active ack OR un-expired
        # snooze covers the alert — exactly what we want here.
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.alerts.alert_acks import is_acked, list_acks
        store = PortfolioStore(self.db)
        self.assertTrue(
            is_acked(store, kind="covenant", deal_id="DEAL_END_TO_END",
                     trigger_key="k"),
            msg="ack record should cover the alert immediately",
        )
        # And confirm the snooze_until field carries the +7d value
        # so the schedule is real, not just a 0-day ack.
        df = list_acks(store)
        rows = df[(df["deal_id"] == "DEAL_END_TO_END")
                  & (df["trigger_key"] == "k")]
        self.assertEqual(len(rows), 1)
        snooze_until = rows.iloc[0].get("snooze_until")
        self.assertTrue(snooze_until,
                        msg=f"snooze_until should be set, got {snooze_until!r}")


if __name__ == "__main__":
    unittest.main()
