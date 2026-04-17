"""Tests for B129 user management + B130 login rate limit."""
from __future__ import annotations

import io
import json
import os
import tempfile
import time
import unittest
import urllib.parse as _p
import urllib.request as _u
from contextlib import redirect_stdout
from urllib.error import HTTPError

from rcm_mc import portfolio_cmd
from rcm_mc.auth.auth import change_password, create_session, create_user, verify_password
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


def _login(port, username, password):
    body = _p.urlencode({
        "username": username, "password": password,
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
        return json.loads(r.read().decode())


class TestPasswordRotation(unittest.TestCase):
    def test_change_password_verifies_new_fails_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "oldpassword1")
            self.assertTrue(change_password(store, "at", "newpassword1"))
            self.assertTrue(verify_password(store, "at", "newpassword1"))
            self.assertFalse(verify_password(store, "at", "oldpassword1"))

    def test_change_password_revokes_sessions(self):
        from rcm_mc.auth.auth import user_for_session
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "oldpassword1")
            token = create_session(store, "at")
            change_password(store, "at", "newpassword1")
            self.assertIsNone(user_for_session(store, token))

    def test_change_password_short_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "oldpassword1")
            with self.assertRaises(ValueError):
                change_password(store, "at", "short")

    def test_change_password_unknown_user_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertFalse(change_password(store, "nobody", "longenough1"))


class TestUsersCli(unittest.TestCase):
    def test_password_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            create_user(store, "at", "oldpassword1")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = portfolio_cmd.main([
                    "--db", db, "users", "password",
                    "--username", "at", "--new-password", "freshpassword1",
                ])
            self.assertEqual(rc, 0)
            self.assertTrue(verify_password(store, "at", "freshpassword1"))


class TestUsersHttp(unittest.TestCase):
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

    def _post(self, port, path, form, *, cookie=None, csrf=None):
        body = _p.urlencode(form).encode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        if cookie:
            headers["Cookie"] = cookie
        if csrf:
            headers["X-CSRF-Token"] = csrf
        req = _u.Request(
            f"http://127.0.0.1:{port}{path}", data=body, method="POST",
            headers=headers,
        )
        return _u.urlopen(req)

    def test_create_user_requires_admin_in_multi_user_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "admin", "supersecret1", role="admin")
            create_user(store, "lowly", "supersecret1", role="analyst")
            server, port = self._start(tmp)
            try:
                analyst = _login(port, "lowly", "supersecret1")
                with self.assertRaises(HTTPError) as ctx:
                    self._post(
                        port, "/api/users/create",
                        {"username": "new", "password": "longenough1"},
                        cookie=f"rcm_session={analyst['token']}",
                        csrf=analyst["csrf_token"],
                    )
                self.assertEqual(ctx.exception.code, 403)
            finally:
                server.shutdown(); server.server_close()

    def test_admin_can_create_delete_rotate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "admin", "supersecret1", role="admin")
            server, port = self._start(tmp)
            try:
                admin = _login(port, "admin", "supersecret1")
                cookie = f"rcm_session={admin['token']}"
                csrf = admin["csrf_token"]

                with self._post(
                    port, "/api/users/create",
                    {"username": "newguy", "password": "brandnew1",
                     "role": "analyst"},
                    cookie=cookie, csrf=csrf,
                ) as r:
                    self.assertEqual(r.status, 201)
                self.assertTrue(verify_password(store, "newguy", "brandnew1"))

                # Rotate
                with self._post(
                    port, "/api/users/password",
                    {"username": "newguy", "new_password": "rotated1pw"},
                    cookie=cookie, csrf=csrf,
                ) as r:
                    self.assertEqual(r.status, 200)
                self.assertTrue(verify_password(store, "newguy", "rotated1pw"))

                # Delete
                with self._post(
                    port, "/api/users/delete",
                    {"username": "newguy"},
                    cookie=cookie, csrf=csrf,
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertTrue(data["deleted"])
            finally:
                server.shutdown(); server.server_close()

    def test_rotate_password_unknown_user_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "admin", "supersecret1", role="admin")
            server, port = self._start(tmp)
            try:
                admin = _login(port, "admin", "supersecret1")
                with self.assertRaises(HTTPError) as ctx:
                    self._post(
                        port, "/api/users/password",
                        {"username": "ghost", "new_password": "longenough1"},
                        cookie=f"rcm_session={admin['token']}",
                        csrf=admin["csrf_token"],
                    )
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()


class TestLoginRateLimit(unittest.TestCase):
    def _start(self, tmp):
        # Reset the class-level counter so tests don't leak state
        from rcm_mc.server import RCMHandler
        RCMHandler._login_fail_log = {}
        import socket as _socket, threading, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_too_many_failures_triggers_429(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "rightpassword1")
            server, port = self._start(tmp)
            try:
                # 5 bad attempts — each should 401
                for _ in range(5):
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

                # 6th → 429 even with correct password
                body = _p.urlencode({
                    "username": "at", "password": "rightpassword1",
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
                self.assertEqual(ctx.exception.code, 429)
            finally:
                server.shutdown(); server.server_close()

    def test_successful_login_clears_counter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "rightpassword1")
            server, port = self._start(tmp)
            try:
                # 4 bad attempts (below threshold)
                for _ in range(4):
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
                    try:
                        _u.urlopen(req)
                    except HTTPError:
                        pass
                # Successful login clears it
                _login(port, "at", "rightpassword1")
                # Subsequent bad attempts start fresh — 4 more should still work
                for _ in range(4):
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
                    # Should be 401 (bad creds), not 429 (rate limited)
                    self.assertEqual(ctx.exception.code, 401)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
