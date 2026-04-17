"""Regression tests for B148 bugs (third audit pass).

Covers:
- Unvalidated int query parameters are clamped
- deal_deadlines uses UTC today (not naive local)
"""
from __future__ import annotations

import os
import tempfile
import threading
import unittest
import urllib.request as _u
from datetime import date, datetime, timedelta, timezone

from rcm_mc.deals.deal_deadlines import add_deadline, overdue, upcoming
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestClampInt(unittest.TestCase):
    def test_clamp_int_helper(self):
        from rcm_mc.server import RCMHandler
        # Can't instantiate RCMHandler directly (needs socket);
        # call the method as an unbound method with a mock self.
        class _M:
            _clamp_int = RCMHandler._clamp_int
        m = _M()
        self.assertEqual(
            m._clamp_int("500", default=100, min_v=1, max_v=1000), 500,
        )
        self.assertEqual(
            m._clamp_int("99999", default=100, min_v=1, max_v=1000), 1000,
        )
        self.assertEqual(
            m._clamp_int("-5", default=100, min_v=1, max_v=1000), 1
        )
        self.assertEqual(
            m._clamp_int("abc", default=100, min_v=1, max_v=1000), 100,
        )
        self.assertEqual(
            m._clamp_int("", default=100, min_v=1, max_v=1000), 100,
        )


class TestClampedEndpoints(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_activity_huge_limit_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/activity?limit=99999999999"
                ) as r:
                    self.assertEqual(r.status, 200)
                # And negative limit is clamped too
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/activity?limit=-5"
                ) as r:
                    self.assertEqual(r.status, 200)
                # Garbage is treated as default
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/activity?limit=not-an-int"
                ) as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown(); server.server_close()

    def test_lp_update_huge_days_clamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/lp-update?days=99999"
                ) as r:
                    body = r.read().decode()
                    # clamped to max 365
                    self.assertIn("window 365 days", body)
            finally:
                server.shutdown(); server.server_close()

    def test_escalations_garbage_min_days_uses_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/escalations?min_days=xyz"
                ) as r:
                    body = r.read().decode()
                    self.assertEqual(r.status, 200)
                    self.assertIn("30 days", body)
            finally:
                server.shutdown(); server.server_close()


class TestDeadlinesUTC(unittest.TestCase):
    def test_upcoming_uses_utc_today_by_default(self):
        """Implicit today defaults to UTC so non-UTC server timezones
        don't shift the window by a day."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            utc_today = datetime.now(timezone.utc).date()
            # Deadline one day out from UTC-today
            due = (utc_today + timedelta(days=1)).isoformat()
            add_deadline(store, deal_id="ccf", label="soon", due_date=due)
            # With default today (UTC), this should be in the 14-day window
            df = upcoming(store, days_ahead=14)
            self.assertEqual(len(df), 1)

    def test_overdue_uses_utc_today_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            utc_today = datetime.now(timezone.utc).date()
            past = (utc_today - timedelta(days=3)).isoformat()
            add_deadline(store, deal_id="ccf", label="missed", due_date=past)
            df = overdue(store)
            self.assertEqual(len(df), 1)
            # days_overdue is computed against UTC today
            self.assertEqual(int(df.iloc[0]["days_overdue"]), 3)

    def test_explicit_today_still_honored(self):
        """Passing today= explicitly still overrides the UTC default."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_deadline(store, deal_id="ccf", label="x",
                         due_date="2026-06-15")
            df = upcoming(
                store, days_ahead=14, today=date(2026, 6, 10),
            )
            self.assertEqual(len(df), 1)
            df = upcoming(
                store, days_ahead=14, today=date(2020, 1, 1),
            )
            self.assertEqual(len(df), 0)


if __name__ == "__main__":
    unittest.main()
