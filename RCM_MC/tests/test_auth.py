"""Tests for multi-user auth (Brick 125)."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u
from contextlib import redirect_stderr, redirect_stdout
from urllib.error import HTTPError

from rcm_mc import portfolio_cmd
from rcm_mc.auth.auth import (
    create_session, create_user, delete_user, list_users,
    revoke_session, user_for_session, verify_password,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestAuthCore(unittest.TestCase):
    def test_create_and_verify_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1", display_name="Andrew")
            self.assertTrue(verify_password(store, "at", "supersecret1"))
            self.assertFalse(verify_password(store, "at", "wrong"))
            self.assertFalse(verify_password(store, "nobody", "x"))

    def test_short_password_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                create_user(store, "at", "short")

    def test_duplicate_username_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            with self.assertRaises(ValueError):
                create_user(store, "at", "anotherpw123")

    def test_invalid_username_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for bad in ("", "has space", "a" * 100, None):
                with self.assertRaises(ValueError):
                    create_user(store, bad, "supersecret1")

    def test_invalid_role_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                create_user(store, "at", "supersecret1", role="superuser")

    def test_session_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1",
                        display_name="AT", role="admin")
            token = create_session(store, "at")
            user = user_for_session(store, token)
            self.assertIsNotNone(user)
            self.assertEqual(user["username"], "at")
            self.assertEqual(user["role"], "admin")

    def test_revoke_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            token = create_session(store, "at")
            self.assertTrue(revoke_session(store, token))
            self.assertIsNone(user_for_session(store, token))

    def test_expired_session_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            token = create_session(store, "at", ttl_hours=1)
            # Backdate expiry into the past
            with store.connect() as con:
                from datetime import datetime as _dt, timedelta as _td, timezone as _tz
                past = (_dt.now(_tz.utc) - _td(hours=1)).isoformat()
                con.execute(
                    "UPDATE sessions SET expires_at = ? WHERE token = ?",
                    (past, token),
                )
                con.commit()
            self.assertIsNone(user_for_session(store, token))

    def test_non_positive_ttl_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            with self.assertRaises(ValueError):
                create_session(store, "at", ttl_hours=0)
            with self.assertRaises(ValueError):
                create_session(store, "at", ttl_hours=-1)

    def test_delete_user_removes_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            token = create_session(store, "at")
            self.assertTrue(delete_user(store, "at"))
            self.assertIsNone(user_for_session(store, token))


class TestAuthCli(unittest.TestCase):
    def _run(self, *argv, db_path):
        buf = io.StringIO(); err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = portfolio_cmd.main(["--db", db_path, *argv])
        return rc, buf.getvalue(), err.getvalue()

    def test_create_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, _, _ = self._run(
                "users", "create",
                "--username", "at", "--password", "supersecret1",
                "--role", "admin",
                db_path=db,
            )
            self.assertEqual(rc, 0)
            rc, out, _ = self._run("users", "list", db_path=db)
            self.assertEqual(rc, 0)
            self.assertIn("at", out)

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            self._run("users", "create",
                      "--username", "at", "--password", "supersecret1",
                      db_path=db)
            rc, _, _ = self._run("users", "delete", "--username", "at",
                                 db_path=db)
            self.assertEqual(rc, 0)
            self.assertEqual(len(list_users(PortfolioStore(db))), 0)


class TestAuthHttp(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, threading, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_open_mode_when_no_users(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown(); server.server_close()

    def test_protected_once_a_user_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                # Browser-style GET (Accept: text/html) → 303 to /login
                req = _u.Request(
                    f"http://127.0.0.1:{port}/",
                    headers={"Accept": "text/html"},
                )
                # urllib follows redirects by default; disable redirect
                opener = _u.build_opener(_NoRedirect())
                resp = opener.open(req)
                self.assertEqual(resp.status, 303)
                self.assertIn("/login", resp.headers.get("Location", ""))
            finally:
                server.shutdown(); server.server_close()

    def test_login_post_sets_cookie_and_grants_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({
                    "username": "at", "password": "supersecret1",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/login",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    self.assertEqual(r.status, 200)
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["username"], "at")
                    cookie_header = r.headers.get("Set-Cookie", "")
                    self.assertIn("rcm_session=", cookie_header)
                    token = None
                    for part in cookie_header.split(";"):
                        k, _, v = part.strip().partition("=")
                        if k == "rcm_session":
                            token = v
                            break
                    self.assertIsNotNone(token)
                # Now access with the cookie
                req2 = _u.Request(
                    f"http://127.0.0.1:{port}/",
                    headers={
                        "Cookie": f"rcm_session={token}",
                        "Accept": "text/html",
                    },
                )
                with _u.urlopen(req2) as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown(); server.server_close()

    def test_login_post_invalid_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({
                    "username": "at", "password": "wrong",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/login",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 401)
            finally:
                server.shutdown(); server.server_close()

    def test_logout_clears_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            token = create_session(store, "at")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/logout",
                    data=b"", method="POST",
                    headers={
                        "Cookie": f"rcm_session={token}",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    cookie = r.headers.get("Set-Cookie", "")
                    self.assertIn("Max-Age=0", cookie)
                # Token should no longer validate
                self.assertIsNone(user_for_session(store, token))
            finally:
                server.shutdown(); server.server_close()

    def test_ack_uses_current_user_over_form_field(self):
        """B125: acked_by is the logged-in user, not the self-reported field."""
        from rcm_mc.alerts.alert_acks import list_acks
        from tests.test_alerts import _seed_with_pe_math
        from rcm_mc.alerts.alerts import evaluate_all
        from rcm_mc.alerts.alert_acks import trigger_key_for
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            # Use the login endpoint so we also get a matching csrf token
            login_body = _p.urlencode({
                "username": "at", "password": "supersecret1",
            }).encode()
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/login",
                    data=login_body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    data = json.loads(r.read().decode())
                    token = data["token"]
                    csrf = data["csrf_token"]
                alert = next(a for a in evaluate_all(store)
                             if a.kind == "covenant_tripped")
                tk = trigger_key_for(alert)
                body = _p.urlencode({
                    "kind": alert.kind, "deal_id": alert.deal_id,
                    "trigger_key": tk,
                    "acked_by": "SPOOFED",  # should be overridden
                    "csrf_token": csrf,
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/alerts/ack",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Cookie": f"rcm_session={token}",
                        "Accept": "application/json",
                    },
                )
                _u.urlopen(req)
                df = list_acks(store)
                self.assertEqual(df.iloc[0]["acked_by"], "at")
            finally:
                server.shutdown(); server.server_close()


class _NoRedirect(_u.HTTPRedirectHandler):
    def http_error_303(self, req, fp, code, msg, headers):
        return fp
    http_error_301 = http_error_303
    http_error_302 = http_error_303
    http_error_307 = http_error_303


if __name__ == "__main__":
    unittest.main()
