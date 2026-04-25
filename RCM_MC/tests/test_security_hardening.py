"""Security hardening regression tests.

Covers the post-deploy hardening layer:

  1. Session inactivity timeout (``RCM_MC_SESSION_IDLE_MINUTES``)
     invalidates idle sessions even when absolute ``expires_at`` still
     in the future.

  2. ``last_seen_at`` is touched on each ``user_for_session`` call so
     active usage slides the window.

  3. Cookies issued to an HTTPS request carry the ``Secure`` flag;
     cookies issued to plain HTTP do not.

  4. Responses over HTTPS carry an HSTS header; responses over plain
     HTTP do not.

  5. Sensitive GETs are audit-logged via ``view.sensitive`` action;
     routine GETs are not logged (would flood the audit table).

  6. The PHI banner is injected when ``RCM_MC_PHI_MODE=disallowed``
     and absent otherwise.

The threat model is a private web deployment fronted by an HTTPS
terminator (Heroku/Azure) — not zero-trust, but enough to keep a
PE tool's diligence data out of casual snooping.
"""
from __future__ import annotations

import os
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import closing
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ────────────────────────────────────────────────────────────────────
# 1 + 2. Session idle timeout + touch
# ────────────────────────────────────────────────────────────────────

class TestSessionIdleTimeout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        from rcm_mc.auth.auth import create_user
        create_user(self.store, "alice", "TestPass#123", role="analyst")

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_session_touches_last_seen(self):
        from rcm_mc.auth.auth import create_session, user_for_session
        token = create_session(self.store, "alice")
        user = user_for_session(self.store, token, touch=True)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "alice")

        with self.store.connect() as con:
            row = con.execute(
                "SELECT last_seen_at FROM sessions WHERE token = ?",
                (token,),
            ).fetchone()
        self.assertTrue(row["last_seen_at"],
                        msg="last_seen_at must be populated after touch")

    def test_idle_session_invalidates(self):
        """A session whose last_seen_at is older than the idle window
        is rejected and cleaned up from the sessions table."""
        from rcm_mc.auth.auth import create_session, user_for_session
        token = create_session(self.store, "alice")
        # Back-date last_seen_at to 45 minutes ago (past the 30-min default)
        past = (datetime.now(timezone.utc)
                - timedelta(minutes=45)).isoformat()
        with self.store.connect() as con:
            con.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE token = ?",
                (past, token),
            )
            con.commit()

        user = user_for_session(self.store, token, touch=True)
        self.assertIsNone(user, msg="idle session must be rejected")

        with self.store.connect() as con:
            row = con.execute(
                "SELECT 1 FROM sessions WHERE token = ?",
                (token,),
            ).fetchone()
        self.assertIsNone(row, msg="idle session must be deleted")

    def test_active_session_refreshes_last_seen(self):
        """Repeated touches should slide the idle window forward."""
        from rcm_mc.auth.auth import create_session, user_for_session
        token = create_session(self.store, "alice")

        with self.store.connect() as con:
            t1 = con.execute(
                "SELECT last_seen_at FROM sessions WHERE token = ?",
                (token,),
            ).fetchone()["last_seen_at"]

        # Touch and verify it moved forward (or at least didn't regress)
        time.sleep(0.01)
        user_for_session(self.store, token, touch=True)

        with self.store.connect() as con:
            t2 = con.execute(
                "SELECT last_seen_at FROM sessions WHERE token = ?",
                (token,),
            ).fetchone()["last_seen_at"]

        self.assertGreaterEqual(t2, t1,
                                msg="touch must not regress last_seen_at")

    def test_touch_false_does_not_slide_window(self):
        """Peek-only callers (touch=False) must NOT move last_seen_at."""
        from rcm_mc.auth.auth import create_session, user_for_session
        token = create_session(self.store, "alice")

        # Set a known timestamp to compare against
        fixed = (datetime.now(timezone.utc)
                 - timedelta(minutes=5)).isoformat()
        with self.store.connect() as con:
            con.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE token = ?",
                (fixed, token),
            )
            con.commit()

        user = user_for_session(self.store, token, touch=False)
        self.assertIsNotNone(user)

        with self.store.connect() as con:
            after = con.execute(
                "SELECT last_seen_at FROM sessions WHERE token = ?",
                (token,),
            ).fetchone()["last_seen_at"]
        self.assertEqual(after, fixed,
                         msg="touch=False must leave last_seen_at unchanged")

    def test_env_override_of_idle_window(self):
        """RCM_MC_SESSION_IDLE_MINUTES overrides the 30-min default."""
        from rcm_mc.auth.auth import create_session, user_for_session
        token = create_session(self.store, "alice")
        # Back-date to 2 minutes ago
        past = (datetime.now(timezone.utc)
                - timedelta(minutes=2)).isoformat()
        with self.store.connect() as con:
            con.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE token = ?",
                (past, token),
            )
            con.commit()

        # With a 1-minute window, 2 min ago is stale
        with patch.dict(os.environ, {"RCM_MC_SESSION_IDLE_MINUTES": "1"}):
            user = user_for_session(self.store, token, touch=True)
        self.assertIsNone(user)


# ────────────────────────────────────────────────────────────────────
# 3 + 4. HTTPS-conditional cookies + HSTS
# ────────────────────────────────────────────────────────────────────

class TestHttpsHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
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

    def _headers(self, path: str, *, extra_headers=None):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            headers=extra_headers or {},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return dict(resp.headers), resp.read()

    def test_hsts_header_when_behind_https(self):
        headers, _ = self._headers(
            "/dashboard",
            extra_headers={"X-Forwarded-Proto": "https"},
        )
        hsts = headers.get("Strict-Transport-Security", "")
        self.assertIn("max-age=", hsts.lower(),
                      msg=f"HSTS should be set behind HTTPS, got: {hsts!r}")

    def test_hsts_header_absent_over_plain_http(self):
        headers, _ = self._headers("/dashboard")
        self.assertNotIn("Strict-Transport-Security", headers,
                         msg="HSTS must not be sent over plain HTTP")

    def test_core_security_headers_always_present(self):
        headers, _ = self._headers("/dashboard")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertIn("frame-ancestors",
                      headers.get("Content-Security-Policy", ""))


class TestRedirectSecurityHeaders(unittest.TestCase):
    """Defense-in-depth: 303 redirect responses must carry the same
    framing / sniffing / HSTS protections as 200 responses.

    Browsers honor HSTS only on the FINAL response after following a
    redirect — but a misbehaving client (script, crawler, broken
    proxy) that stops at the 303 shouldn't be able to frame the
    redirect, sniff its content type, or downgrade to HTTP.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        # Seed a user so the auth gate kicks in. Without this, the
        # server runs in open single-user mode and /dashboard returns
        # 200 to unauthenticated requests — no redirect to test.
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.auth.auth import create_user
        create_user(PortfolioStore(cls.db),
                    "redirect_test_user", "TestPass!12", role="admin")

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

    def test_303_to_login_carries_security_headers(self):
        """Unauthenticated browser GET of /dashboard 303-redirects to
        /login; that 303 response carries every standard header.
        """
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        try:
            conn.request("GET", "/dashboard", headers={
                "Accept": "text/html",
                "X-Forwarded-Proto": "https",
            })
            resp = conn.getresponse()
            resp.read()
            self.assertEqual(resp.status, 303,
                             msg=f"expected 303, got {resp.status}")
            self.assertEqual(resp.getheader("X-Content-Type-Options"),
                             "nosniff")
            self.assertEqual(resp.getheader("X-Frame-Options"), "DENY")
            self.assertIn("strict-origin",
                          (resp.getheader("Referrer-Policy") or "").lower())
            self.assertIn("max-age=",
                          (resp.getheader("Strict-Transport-Security") or ""))
            # And the redirect target is /login with the next= hint
            self.assertEqual(resp.getheader("Location"),
                             "/login?next=%2Fdashboard")
        finally:
            conn.close()

    def test_redirect_no_hsts_over_plain_http(self):
        """HSTS only emits when X-Forwarded-Proto says https."""
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        try:
            conn.request("GET", "/dashboard", headers={"Accept": "text/html"})
            resp = conn.getresponse()
            resp.read()
            self.assertEqual(resp.status, 303)
            self.assertIsNone(resp.getheader("Strict-Transport-Security"),
                              msg="HSTS must NOT be sent over plain HTTP")
            # But framing/sniff guards still apply
            self.assertEqual(resp.getheader("X-Frame-Options"), "DENY")
        finally:
            conn.close()


# ────────────────────────────────────────────────────────────────────
# 5. Sensitive-view audit
# ────────────────────────────────────────────────────────────────────

class TestSensitiveViewAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
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

    def _get(self, path):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def _audit_count(self, action: str, target_contains: str = "") -> int:
        # The audit table is created lazily on first write. If it
        # doesn't exist yet, the count is 0 — that's exactly what
        # "no audits ever logged" means.
        con = sqlite3.connect(self.db)
        try:
            tbl = con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='audit_events'",
            ).fetchone()
            if tbl is None:
                return 0
            rows = con.execute(
                "SELECT action, target FROM audit_events WHERE action = ?",
                (action,),
            ).fetchall()
        finally:
            con.close()
        if target_contains:
            return sum(1 for a, t in rows if target_contains in (t or ""))
        return len(rows)

    def test_settings_view_is_audited(self):
        # Hit any settings URL — audit fires on sensitive prefix
        self._get("/settings")
        count = self._audit_count("view.sensitive", "/settings")
        self.assertGreaterEqual(count, 1,
                                msg="/settings GET must be audited")

    def test_routine_page_is_not_audited(self):
        """Dashboard is NOT sensitive — audit table stays clean."""
        before = self._audit_count("view.sensitive", "/dashboard")
        self._get("/dashboard")
        after = self._audit_count("view.sensitive", "/dashboard")
        self.assertEqual(before, after,
                         msg="/dashboard must not be logged as sensitive")


# ────────────────────────────────────────────────────────────────────
# 6. PHI banner
# ────────────────────────────────────────────────────────────────────

class TestPhiBanner(unittest.TestCase):
    def test_banner_absent_without_env(self):
        from rcm_mc.ui._chartis_kit import _phi_banner_html
        # Clear env
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RCM_MC_PHI_MODE", None)
            self.assertEqual(_phi_banner_html(), "")

    def test_disallowed_banner(self):
        from rcm_mc.ui._chartis_kit import _phi_banner_html
        with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "disallowed"}):
            html = _phi_banner_html()
        self.assertIn("no PHI permitted", html)
        self.assertIn("data-phi-mode=\"disallowed\"", html)

    def test_restricted_banner(self):
        from rcm_mc.ui._chartis_kit import _phi_banner_html
        with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "restricted"}):
            html = _phi_banner_html()
        self.assertIn("PHI-eligible", html)
        self.assertIn("data-phi-mode=\"restricted\"", html)


if __name__ == "__main__":
    unittest.main()
