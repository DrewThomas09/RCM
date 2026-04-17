"""Tests for unified audit log (Brick 133)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u

from rcm_mc.auth.audit_log import list_events, log_event
from rcm_mc.auth.auth import create_session, create_user
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestAuditLogCore(unittest.TestCase):
    def test_log_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            log_event(store, actor="at", action="alert.ack",
                      target="ccf", detail={"kind": "covenant_tripped"})
            df = list_events(store)
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["actor"], "at")
            self.assertEqual(df.iloc[0]["action"], "alert.ack")
            self.assertEqual(df.iloc[0]["target"], "ccf")
            self.assertEqual(
                df.iloc[0]["detail"]["kind"], "covenant_tripped",
            )

    def test_filter_by_actor_and_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            log_event(store, actor="at", action="owner.assign", target="ccf")
            log_event(store, actor="sb", action="owner.assign", target="aaa")
            log_event(store, actor="at", action="alert.ack", target="ccf")
            self.assertEqual(len(list_events(store, actor="at")), 2)
            self.assertEqual(
                len(list_events(store, action="owner.assign")), 2,
            )
            self.assertEqual(
                len(list_events(store, actor="at", action="alert.ack")), 1,
            )

    def test_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for i in range(10):
                log_event(store, actor="at", action="x", target=str(i))
            self.assertEqual(len(list_events(store, limit=3)), 3)

    def test_newest_first_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            log_event(store, actor="at", action="a", target="1")
            log_event(store, actor="at", action="b", target="2")
            df = list_events(store)
            self.assertEqual(df.iloc[0]["action"], "b")


class TestHandlerEmissions(unittest.TestCase):
    """POST handlers should emit audit events for key actions."""

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

    def _login(self, port, username, password):
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

    def test_ack_emits_alert_ack_event(self):
        from rcm_mc.alerts.alert_acks import trigger_key_for
        from rcm_mc.alerts.alerts import evaluate_all
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            create_user(store, "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                auth = self._login(port, "at", "supersecret1")
                alert = next(a for a in evaluate_all(store)
                             if a.kind == "covenant_tripped")
                body = _p.urlencode({
                    "kind": alert.kind,
                    "deal_id": alert.deal_id,
                    "trigger_key": trigger_key_for(alert),
                    "csrf_token": auth["csrf_token"],
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/alerts/ack",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Cookie": f"rcm_session={auth['token']}",
                        "Accept": "application/json",
                    },
                )
                _u.urlopen(req)
                df = list_events(store, action="alert.ack")
                self.assertEqual(len(df), 1)
                self.assertEqual(df.iloc[0]["actor"], "at")
                self.assertEqual(df.iloc[0]["target"], "ccf")
            finally:
                server.shutdown(); server.server_close()

    def test_user_create_emits_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "admin", "supersecret1", role="admin")
            server, port = self._start(tmp)
            try:
                auth = self._login(port, "admin", "supersecret1")
                body = _p.urlencode({
                    "username": "newguy", "password": "brandnew1",
                    "role": "analyst",
                    "csrf_token": auth["csrf_token"],
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/users/create",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Cookie": f"rcm_session={auth['token']}",
                        "Accept": "application/json",
                    },
                )
                _u.urlopen(req)
                df = list_events(store, action="user.create")
                self.assertEqual(len(df), 1)
                self.assertEqual(df.iloc[0]["actor"], "admin")
                self.assertEqual(df.iloc[0]["target"], "newguy")
                self.assertEqual(df.iloc[0]["detail"]["role"], "analyst")
            finally:
                server.shutdown(); server.server_close()

    def test_api_audit_events_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            log_event(store, actor="at", action="owner.assign", target="ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/audit/events"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data), 1)
                    self.assertEqual(data[0]["actor"], "at")
            finally:
                server.shutdown(); server.server_close()

    def test_audit_page_shows_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            log_event(store, actor="at", action="alert.ack", target="ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/audit") as r:
                    body = r.read().decode()
                    self.assertIn("Audit events", body)
                    self.assertIn("alert.ack", body)
                    self.assertIn("ccf", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
