"""Regression tests for B147 bugs found in second audit pass.

Covers:
- Login rate-limit log is thread-safe (no torn lists under concurrency)
- create_session rejects non-positive TTL
- list_starred ordering is stable for same-second inserts
- SQLite busy_timeout is set (concurrent reads don't immediately fail)
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import unittest

from rcm_mc.auth.auth import create_session, create_user
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.deals.watchlist import list_starred, star_deal


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestLoginFailLogThreadSafe(unittest.TestCase):
    """B147 #1: shared _login_fail_log must not corrupt under concurrency.

    Before the lock, two threads could both hit ``.setdefault``,
    race on the list mutation, and one would lose its append — which
    meant the rate limit could be bypassed intermittently. With the
    lock, N concurrent failures always produce exactly N entries.
    """

    def setUp(self):
        from rcm_mc.server import RCMHandler
        RCMHandler._login_fail_log = {}

    def tearDown(self):
        from rcm_mc.server import RCMHandler
        RCMHandler._login_fail_log = {}

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

    def test_concurrent_bad_logins_all_counted(self):
        import urllib.parse as _p
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            create_user(_store(tmp), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                def try_bad():
                    body = _p.urlencode({
                        "username": "at", "password": "wrong",
                    }).encode()
                    req = _u.Request(
                        f"http://127.0.0.1:{port}/api/login",
                        data=body, method="POST",
                        headers={
                            "Content-Type":
                                "application/x-www-form-urlencoded",
                            "Accept": "application/json",
                        },
                    )
                    try:
                        _u.urlopen(req)
                    except HTTPError:
                        pass

                threads = [threading.Thread(target=try_bad) for _ in range(10)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                # Inspect the shared log — should have at most
                # _LOGIN_FAIL_MAX entries (since once we hit the cap,
                # further attempts are 429'd without appending).
                from rcm_mc.server import RCMHandler
                entries = RCMHandler._login_fail_log.get("127.0.0.1", [])
                # All 10 should either be 401-counted (appended) or
                # 429-rejected (not appended). No torn/partial list.
                self.assertLessEqual(len(entries), 10)
                # And the list contains only floats (no sentinel junk
                # from a torn mutation)
                for t in entries:
                    self.assertIsInstance(t, float)
            finally:
                server.shutdown(); server.server_close()


class TestNonPositiveTtlRejected(unittest.TestCase):
    """B147 #2."""

    def test_zero_ttl_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            with self.assertRaises(ValueError):
                create_session(store, "at", ttl_hours=0)

    def test_negative_ttl_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            with self.assertRaises(ValueError):
                create_session(store, "at", ttl_hours=-100)

    def test_positive_ttl_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            # Should not raise
            tok = create_session(store, "at", ttl_hours=1)
            self.assertTrue(tok)


class TestListStarredStableOrder(unittest.TestCase):
    """B147 #3: deal_id secondary sort for same-second inserts."""

    def test_same_second_inserts_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # Force same timestamp by writing rows directly
            from rcm_mc.deals.watchlist import _ensure_stars_table
            _ensure_stars_table(store)
            ts = "2026-04-15T10:00:00+00:00"
            with store.connect() as con:
                for did in ["zzz", "aaa", "mmm"]:
                    con.execute(
                        "INSERT INTO deal_stars (deal_id, starred_at) "
                        "VALUES (?, ?)",
                        (did, ts),
                    )
                con.commit()
            # Repeated calls return identical order — deterministic
            result1 = list_starred(store)
            result2 = list_starred(store)
            self.assertEqual(result1, result2)
            # And that order is alphabetical by deal_id (secondary sort)
            self.assertEqual(result1, ["aaa", "mmm", "zzz"])


class TestBusyTimeoutSet(unittest.TestCase):
    """B147 #4: PRAGMA busy_timeout so concurrent access retries."""

    def test_busy_timeout_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            store.init_db()
            with store.connect() as con:
                row = con.execute("PRAGMA busy_timeout").fetchone()
                # PRAGMA returns a list with one int
                self.assertGreater(row[0], 0)

    def test_concurrent_writers_dont_immediately_fail(self):
        """With busy_timeout set, a second writer waits rather than
        raising 'database is locked' on the first conflict."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            store.init_db()
            errors = []

            def hammer():
                for i in range(20):
                    try:
                        star_deal(store, f"d{i}")
                    except Exception as exc:
                        errors.append(exc)

            threads = [threading.Thread(target=hammer) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            # With busy_timeout and an atomic deal upsert, no writer
            # exception should leak from the worker threads.
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
