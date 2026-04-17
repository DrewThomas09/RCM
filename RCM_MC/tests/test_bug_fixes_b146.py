"""Regression tests for B146 bug fixes from the session-wide audit.

Covers:
- toggle_star race condition (atomic CAS)
- login open-redirect via ?next=https://evil
- multipart 10 MB body cap
- health_score NaN handling
- deal_deadlines.upcoming off-by-one
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.parse as _p
import urllib.request as _u
from datetime import date, timedelta
from urllib.error import HTTPError

from rcm_mc.auth.auth import create_user
from rcm_mc.deals.deal_deadlines import add_deadline, upcoming
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.deals.watchlist import is_starred, toggle_star


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestToggleStarRace(unittest.TestCase):
    def test_serial_toggles_alternate(self):
        """Even under serial use, toggle_star is an atomic flip."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertTrue(toggle_star(store, "ccf"))
            self.assertFalse(toggle_star(store, "ccf"))
            self.assertTrue(toggle_star(store, "ccf"))

    def test_concurrent_toggles_end_in_consistent_state(self):
        """10 concurrent toggles on the same deal leave a well-defined state.

        Pre-fix, two concurrent threads could both read "not starred"
        and both insert, or both read "starred" and both delete, corrupting
        the "exactly one row per deal" invariant. After fix, the row count
        for the deal is always 0 or 1 — never 2.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            results = []
            errors = []

            def worker():
                try:
                    results.append(toggle_star(store, "ccf"))
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

            threads = [threading.Thread(target=worker) for _ in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            # Under concurrency SQLite may lock-abort some toggles — that's
            # acceptable. What must NOT happen: a duplicate row in the table.
            with store.connect() as con:
                rows = con.execute(
                    "SELECT COUNT(*) AS n FROM deal_stars WHERE deal_id='ccf'"
                ).fetchone()
            self.assertLessEqual(rows["n"], 1)


class TestLoginOpenRedirect(unittest.TestCase):
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

    def _login_redirect(self, port, nxt):
        body = _p.urlencode({
            "username": "at", "password": "supersecret1",
            "next": nxt,
        }).encode()
        # Don't follow redirects so we can inspect the Location header
        opener = _u.build_opener(_NoRedirect())
        req = _u.Request(
            f"http://127.0.0.1:{port}/api/login",
            data=body, method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        return opener.open(req)

    def test_absolute_url_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(_store(tmp), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                r = self._login_redirect(port, "https://evil.com/takeover")
                self.assertEqual(r.headers.get("Location", ""), "/")
            finally:
                server.shutdown(); server.server_close()

    def test_protocol_relative_url_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(_store(tmp), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                r = self._login_redirect(port, "//evil.com/x")
                self.assertEqual(r.headers.get("Location", ""), "/")
            finally:
                server.shutdown(); server.server_close()

    def test_local_path_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(_store(tmp), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                r = self._login_redirect(port, "/deal/ccf")
                self.assertEqual(r.headers.get("Location", ""), "/deal/ccf")
            finally:
                server.shutdown(); server.server_close()


class TestMultipartSizeCap(unittest.TestCase):
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

    def test_oversize_multipart_rejected(self):
        """Server rejects >10 MB multipart. Either 413 or socket reset
        is acceptable — the key property is that the server doesn't
        OOM and stays responsive for the next request."""
        import socket as _socket
        import urllib.error as _ue
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                boundary = "----Oversize"
                # Just over the 10 MB cap
                filler = b"A" * (11 * 1024 * 1024)
                body = (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="file"; '
                    f'filename="big.csv"\r\n'
                    f"Content-Type: text/csv\r\n\r\n"
                ).encode() + filler + f"\r\n--{boundary}--\r\n".encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/upload-notes",
                    data=body, method="POST",
                    headers={
                        "Content-Type":
                            f"multipart/form-data; boundary={boundary}",
                        "Accept": "application/json",
                    },
                )
                got_413 = False
                got_reset = False
                try:
                    _u.urlopen(req)
                except HTTPError as exc:
                    self.assertEqual(exc.code, 413)
                    got_413 = True
                except (_ue.URLError, ConnectionError, _socket.error):
                    # Broken pipe because server closes after rejecting
                    got_reset = True
                self.assertTrue(got_413 or got_reset)

                # Crucial: server is still up for normal requests
                with _u.urlopen(f"http://127.0.0.1:{port}/health") as r:
                    self.assertEqual(r.read().decode(), "ok")
            finally:
                server.shutdown(); server.server_close()


class TestHealthScoreNaN(unittest.TestCase):
    def test_nan_concerning_signals_treated_as_zero(self):
        import numpy as np
        import pandas as pd
        from rcm_mc.deals.health_score import compute_health
        from tests.test_alerts import _seed_with_pe_math
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            # Directly poke a numpy NaN into the snapshot's
            # concerning_signals column to simulate upstream
            with store.connect() as con:
                con.execute(
                    "UPDATE deal_snapshots SET concerning_signals = NULL "
                    "WHERE deal_id = 'ccf'"
                )
                con.commit()
            # compute_health must not crash on a NULL-backed NaN
            h = compute_health(store, "ccf")
            self.assertIsNotNone(h["score"])


class TestDeadlineUpcomingOffByOne(unittest.TestCase):
    def test_14_days_ahead_includes_exactly_14_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            today = date.today()
            # 14 days of deadlines: today, +1, +2, ..., +13 → all should be in
            # a days_ahead=14 window. +14 should NOT be (first day outside).
            for i in range(16):
                d = (today + timedelta(days=i)).isoformat()
                add_deadline(store, deal_id="ccf", label=f"d{i}",
                             due_date=d)
            df = upcoming(store, days_ahead=14, today=today)
            labels = sorted(df["label"].tolist())
            # Labels d0..d13 should be present; d14, d15 should not
            self.assertEqual(
                labels,
                sorted([f"d{i}" for i in range(14)]),
            )


class _NoRedirect(_u.HTTPRedirectHandler):
    def http_error_303(self, req, fp, code, msg, headers):
        return fp
    http_error_301 = http_error_303
    http_error_302 = http_error_303
    http_error_307 = http_error_303


if __name__ == "__main__":
    unittest.main()
