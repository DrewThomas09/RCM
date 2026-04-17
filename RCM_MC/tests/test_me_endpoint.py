"""Tests for /api/me + nav sign-in indicator (Brick 126)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.auth.auth import create_session, create_user
from rcm_mc.portfolio.store import PortfolioStore


class TestMeEndpoint(unittest.TestCase):
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

    def test_me_empty_when_not_signed_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/api/me") as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data, {})
            finally:
                server.shutdown(); server.server_close()

    def test_me_returns_user_with_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            create_user(store, "at", "supersecret1", role="admin")
            token = create_session(store, "at")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/me",
                    headers={"Cookie": f"rcm_session={token}"},
                )
                with _u.urlopen(req) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["username"], "at")
                    self.assertEqual(data["role"], "admin")
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_whoami_element(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('id="rcm-whoami"', body)
                    self.assertIn("/api/me", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
