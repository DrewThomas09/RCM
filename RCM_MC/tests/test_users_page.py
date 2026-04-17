"""Tests for /users admin management page (Brick 134)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u
from urllib.error import HTTPError

from rcm_mc.auth.auth import create_session, create_user
from rcm_mc.portfolio.store import PortfolioStore


class TestUsersPage(unittest.TestCase):
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

    def test_open_in_single_user_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/users") as r:
                    body = r.read().decode()
                    self.assertIn("Add user", body)
                    self.assertIn("single-user mode", body)
            finally:
                server.shutdown(); server.server_close()

    def test_denies_non_admin(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            create_user(store, "at", "supersecret1", role="analyst")
            token = create_session(store, "at")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/users",
                    headers={"Cookie": f"rcm_session={token}"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 403)
            finally:
                server.shutdown(); server.server_close()

    def test_allows_admin_and_lists_users(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            create_user(store, "boss", "supersecret1", role="admin",
                        display_name="Partner")
            create_user(store, "at", "supersecret1", role="analyst")
            token = create_session(store, "boss")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/users",
                    headers={"Cookie": f"rcm_session={token}"},
                )
                with _u.urlopen(req) as r:
                    body = r.read().decode()
                    self.assertIn("Users (2)", body)
                    self.assertIn("boss", body)
                    self.assertIn("at", body)
                    self.assertIn("Partner", body)
                    # Rotate + Delete forms per row
                    self.assertIn("/api/users/password", body)
                    self.assertIn("/api/users/delete", body)
                    # Add form
                    self.assertIn("/api/users/create", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
