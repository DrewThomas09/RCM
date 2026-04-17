"""Tests for /audit admin dashboard (Brick 127)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u
from urllib.error import HTTPError

from rcm_mc.alerts.alert_acks import ack_alert, trigger_key_for
from rcm_mc.alerts.alerts import evaluate_all
from rcm_mc.auth.auth import create_session, create_user
from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


class TestAuditPage(unittest.TestCase):
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

    def test_audit_open_in_single_user_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No users → single-user mode → audit is accessible
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/audit") as r:
                    body = r.read().decode()
                    self.assertIn("Users", body)
                    self.assertIn("No users created yet", body)
            finally:
                server.shutdown(); server.server_close()

    def test_audit_denies_non_admin(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            create_user(store, "at", "supersecret1", role="analyst")
            token = create_session(store, "at")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/audit",
                    headers={"Cookie": f"rcm_session={token}"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 403)
            finally:
                server.shutdown(); server.server_close()

    def test_audit_allows_admin(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            create_user(store, "admin", "supersecret1", role="admin")
            token = create_session(store, "admin")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/audit",
                    headers={"Cookie": f"rcm_session={token}"},
                )
                with _u.urlopen(req) as r:
                    body = r.read().decode()
                    self.assertIn("Users (1)", body)
                    self.assertIn("admin", body)
            finally:
                server.shutdown(); server.server_close()

    def test_audit_shows_recent_acks(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            create_user(store, "admin", "supersecret1", role="admin")
            token = create_session(store, "admin")
            a = next(x for x in evaluate_all(store)
                     if x.kind == "covenant_tripped")
            ack_alert(store, kind=a.kind, deal_id=a.deal_id,
                      trigger_key=trigger_key_for(a),
                      acked_by="admin", note="ack test")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/audit",
                    headers={"Cookie": f"rcm_session={token}"},
                )
                with _u.urlopen(req) as r:
                    body = r.read().decode()
                    self.assertIn("Recent acks (1)", body)
                    self.assertIn("ack test", body)
                    self.assertIn("covenant_tripped", body)
            finally:
                server.shutdown(); server.server_close()

    def test_audit_shows_owner_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            create_user(store, "admin", "supersecret1", role="admin")
            token = create_session(store, "admin")
            assign_owner(store, deal_id="ccf", owner="AT", note="lead")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/audit",
                    headers={"Cookie": f"rcm_session={token}"},
                )
                with _u.urlopen(req) as r:
                    body = r.read().decode()
                    self.assertIn("Owner assignments (1)", body)
                    self.assertIn("AT", body)
                    self.assertIn("lead", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
