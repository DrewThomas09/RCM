"""Tests for B153 structured error codes in auth responses."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.parse as _p
import urllib.request as _u
from urllib.error import HTTPError

from rcm_mc.auth.auth import create_session, create_user
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestErrorCodes(unittest.TestCase):
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

    def test_invalid_credentials_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(_store(tmp), "at", "supersecret1")
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
                err = json.loads(ctx.exception.read().decode())
                self.assertEqual(err["code"], "INVALID_CREDENTIALS")
                self.assertIn("error", err)
            finally:
                server.shutdown(); server.server_close()

    def test_rate_limited_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(_store(tmp), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                # Trigger 5 failures to lock the IP
                for _ in range(5):
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
                # 6th attempt → 429 with RATE_LIMITED code
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
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 429)
                err = json.loads(ctx.exception.read().decode())
                self.assertEqual(err["code"], "RATE_LIMITED")
            finally:
                server.shutdown(); server.server_close()

    def test_csrf_failed_code(self):
        """Session-auth POST without CSRF returns code=CSRF_FAILED."""
        from rcm_mc.alerts.alert_acks import trigger_key_for
        from rcm_mc.alerts.alerts import evaluate_all
        from tests.test_alerts import _seed_with_pe_math
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            create_user(store, "at", "supersecret1")
            token = create_session(store, "at")
            alert = next(a for a in evaluate_all(store)
                         if a.kind == "covenant_tripped")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({
                    "kind": alert.kind, "deal_id": alert.deal_id,
                    "trigger_key": trigger_key_for(alert),
                    # NO csrf_token
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
                err = json.loads(ctx.exception.read().decode())
                self.assertEqual(err["code"], "CSRF_FAILED")
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
