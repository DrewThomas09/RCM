"""Regression tests for B152 bugs (seventh audit pass)."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest
import urllib.request as _u
from urllib.error import HTTPError

from rcm_mc.auth.auth import create_session, create_user
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.deals.watchlist import is_starred, star_deal
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestAuthPathBypass(unittest.TestCase):
    """B152 #1: path.startswith('/api/login') allowed auth bypass via
    crafted paths like /api/login-foo. Must require exact match."""

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

    def test_crafted_login_path_does_not_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Creating a user switches server into multi-user mode
            create_user(_store(tmp), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                # /api/login-foo must NOT match the login exemption
                # and should require auth (redirect/401).
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/login-foo",
                    headers={"Accept": "application/json"},
                )
                try:
                    with _u.urlopen(req) as r:
                        # Either 401 or 404, but NEVER 200 without auth
                        self.assertNotEqual(r.status, 200)
                except HTTPError as exc:
                    self.assertIn(exc.code, (401, 404))
            finally:
                server.shutdown(); server.server_close()

    def test_legitimate_login_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(_store(tmp), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                # Normal /login still reachable without auth
                with _u.urlopen(f"http://127.0.0.1:{port}/login") as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown(); server.server_close()


class TestDealRefUpsertedOnStar(unittest.TestCase):
    """B152 #2: star_deal on an unknown deal_id must create the deal row
    so downstream queries (dashboards, compute_health) find it."""

    def test_star_deal_creates_deal_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertTrue(star_deal(store, "brand_new"))
            # Deal row should now exist
            with store.connect() as con:
                row = con.execute(
                    "SELECT deal_id FROM deals WHERE deal_id = ?",
                    ("brand_new",),
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertTrue(is_starred(store, "brand_new"))

    def test_alert_history_upserts_deal(self):
        """record_sightings should upsert the deal so history rows
        don't dangle."""
        from rcm_mc.alerts.alerts import Alert
        from rcm_mc.alerts.alert_history import record_sightings
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a = Alert(
                kind="k", severity="red", deal_id="orphan",
                title="t", detail="d", triggered_at="x",
            )
            record_sightings(store, [a])
            with store.connect() as con:
                row = con.execute(
                    "SELECT deal_id FROM deals WHERE deal_id = ?",
                    ("orphan",),
                ).fetchone()
            self.assertIsNotNone(row)


class TestHealthPerfCache(unittest.TestCase):
    """B152 #3: /cohorts should call compute_health once per deal,
    not once per (cohort, deal) pair."""

    def test_cohorts_page_does_not_explode_with_many_cohorts(self):
        """Sanity check: the page renders quickly with 5 cohorts × 5
        deals. Pre-fix this was 25 compute_health calls; post-fix is 5."""
        import time
        from rcm_mc.deals.deal_tags import add_tag
        with tempfile.TemporaryDirectory() as tmp:
            store = None
            for i in range(5):
                store = _seed_with_pe_math(tmp, f"d{i}", headroom=2.0)
                # Each deal in 5 cohorts
                for j in range(5):
                    add_tag(store, deal_id=f"d{i}", tag=f"cohort{j}")
            import socket as _socket, time as _time
            from rcm_mc.server import build_server
            s = _socket.socket(); s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]; s.close()
            server, _ = build_server(port=port,
                                     db_path=os.path.join(tmp, "p.db"))
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start(); _time.sleep(0.05)
            try:
                t0 = time.monotonic()
                with _u.urlopen(f"http://127.0.0.1:{port}/cohorts") as r:
                    self.assertEqual(r.status, 200)
                elapsed = time.monotonic() - t0
                # Rough sanity: with 5 deals × 5 cohorts = 25 pairs,
                # the cache keeps it under a couple of seconds even
                # on a slow laptop.
                self.assertLess(elapsed, 5.0)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
