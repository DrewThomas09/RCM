"""Tests for CSRF protection on session-auth POSTs (Brick 128)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u
from urllib.error import HTTPError

from rcm_mc.alerts.alert_acks import trigger_key_for
from rcm_mc.alerts.alerts import evaluate_all
from rcm_mc.auth.auth import create_user
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _login_and_get_tokens(port, username, password):
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
        data = json.loads(r.read().decode())
    return data["token"], data["csrf_token"]


class TestCsrf(unittest.TestCase):
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

    def test_session_post_without_csrf_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                token, _ = _login_and_get_tokens(port, "at", "supersecret1")
                alert = next(a for a in evaluate_all(store)
                             if a.kind == "covenant_tripped")
                body = _p.urlencode({
                    "kind": alert.kind,
                    "deal_id": alert.deal_id,
                    "trigger_key": trigger_key_for(alert),
                }).encode()  # no csrf_token
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/alerts/ack",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Cookie": f"rcm_session={token}",
                        "Accept": "application/json",
                    },
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 403)
                err = json.loads(ctx.exception.read().decode())
                self.assertIn("CSRF", err["error"])
            finally:
                server.shutdown(); server.server_close()

    def test_session_post_with_form_csrf_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                token, csrf = _login_and_get_tokens(port, "at", "supersecret1")
                alert = next(a for a in evaluate_all(store)
                             if a.kind == "covenant_tripped")
                body = _p.urlencode({
                    "kind": alert.kind,
                    "deal_id": alert.deal_id,
                    "trigger_key": trigger_key_for(alert),
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
                with _u.urlopen(req) as r:
                    self.assertEqual(r.status, 201)
            finally:
                server.shutdown(); server.server_close()

    def test_session_post_with_header_csrf_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                token, csrf = _login_and_get_tokens(port, "at", "supersecret1")
                alert = next(a for a in evaluate_all(store)
                             if a.kind == "covenant_tripped")
                body = _p.urlencode({
                    "kind": alert.kind,
                    "deal_id": alert.deal_id,
                    "trigger_key": trigger_key_for(alert),
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/alerts/ack",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Cookie": f"rcm_session={token}",
                        "X-CSRF-Token": csrf,
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    self.assertEqual(r.status, 201)
            finally:
                server.shutdown(); server.server_close()

    def test_session_post_with_wrong_csrf_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                token, _ = _login_and_get_tokens(port, "at", "supersecret1")
                alert = next(a for a in evaluate_all(store)
                             if a.kind == "covenant_tripped")
                body = _p.urlencode({
                    "kind": alert.kind,
                    "deal_id": alert.deal_id,
                    "trigger_key": trigger_key_for(alert),
                    "csrf_token": "nope",
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
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 403)
            finally:
                server.shutdown(); server.server_close()

    def test_open_mode_no_csrf_required(self):
        """Without a session cookie, CSRF gate skips (scripts, open mode)."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            # No users created → open mode
            server, port = self._start(tmp)
            try:
                alert = next(a for a in evaluate_all(PortfolioStore(
                    os.path.join(tmp, "p.db"))) if a.kind == "covenant_tripped")
                body = _p.urlencode({
                    "kind": alert.kind,
                    "deal_id": alert.deal_id,
                    "trigger_key": trigger_key_for(alert),
                }).encode()  # no csrf, no session
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/alerts/ack",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    self.assertEqual(r.status, 201)
            finally:
                server.shutdown(); server.server_close()

    def test_login_itself_is_csrf_exempt(self):
        """Login cannot require CSRF — the client has no token yet."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                token, _ = _login_and_get_tokens(port, "at", "supersecret1")
                self.assertTrue(token)  # login succeeded despite no CSRF
            finally:
                server.shutdown(); server.server_close()

    def test_form_pages_include_csrf_patch_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/login") as r:
                    body = r.read().decode()
                    self.assertIn("rcm_csrf", body)
                    self.assertIn("csrf_token", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
