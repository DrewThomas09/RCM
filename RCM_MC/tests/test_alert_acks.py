"""Tests for alert acknowledgement + snooze (Brick 102)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from rcm_mc.alerts.alert_acks import (
    ack_alert, is_acked, list_acks, trigger_key_for,
)
from rcm_mc.alerts.alerts import Alert, evaluate_active, evaluate_all, active_count
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math  # reuse helper


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestAckCore(unittest.TestCase):
    def test_trigger_key_stable(self):
        a = Alert(kind="covenant_tripped", severity="red", deal_id="ccf",
                  title="t", detail="d", triggered_at="2026-04-14T10:00:00")
        self.assertEqual(
            trigger_key_for(a),
            "covenant_tripped|ccf|2026-04-14T10:00:00",
        )

    def test_is_acked_false_when_no_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertFalse(is_acked(
                store, kind="covenant_tripped", deal_id="x",
                trigger_key="k",
            ))

    def test_permanent_ack_hides_until_key_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            ack_alert(store, kind="covenant_tripped", deal_id="ccf",
                      trigger_key="k1", snooze_days=0)
            self.assertTrue(is_acked(
                store, kind="covenant_tripped", deal_id="ccf",
                trigger_key="k1",
            ))
            # Different trigger_key → not acked (new instance)
            self.assertFalse(is_acked(
                store, kind="covenant_tripped", deal_id="ccf",
                trigger_key="k2",
            ))

    def test_snooze_expires(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            ack_alert(store, kind="variance_miss_red", deal_id="ccf",
                      trigger_key="2026Q1", snooze_days=7)
            # Now → acked
            now = datetime.now(timezone.utc)
            self.assertTrue(is_acked(
                store, kind="variance_miss_red", deal_id="ccf",
                trigger_key="2026Q1", now=now,
            ))
            # 8 days later → expired
            self.assertFalse(is_acked(
                store, kind="variance_miss_red", deal_id="ccf",
                trigger_key="2026Q1", now=now + timedelta(days=8),
            ))

    def test_list_acks_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            ack_alert(store, kind="k", deal_id="a", trigger_key="t1")
            ack_alert(store, kind="k", deal_id="b", trigger_key="t2")
            df = list_acks(store)
            self.assertEqual(len(df), 2)
            self.assertEqual(df.iloc[0]["deal_id"], "b")


class TestEvaluateActive(unittest.TestCase):
    def test_active_hides_acked_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            alerts = evaluate_all(store)
            self.assertTrue(any(a.kind == "covenant_tripped" for a in alerts))
            # Ack the covenant alert
            alert = next(a for a in alerts if a.kind == "covenant_tripped")
            ack_alert(
                store, kind=alert.kind, deal_id=alert.deal_id,
                trigger_key=trigger_key_for(alert), snooze_days=0,
            )
            active = evaluate_active(store)
            self.assertFalse(any(a.kind == "covenant_tripped" for a in active))

    def test_active_count_excludes_acked(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            self.assertEqual(active_count(store), 1)
            alert = next(
                a for a in evaluate_all(store) if a.kind == "covenant_tripped"
            )
            ack_alert(store, kind=alert.kind, deal_id=alert.deal_id,
                      trigger_key=trigger_key_for(alert))
            self.assertEqual(active_count(store), 0)


class TestAckHttp(unittest.TestCase):
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

    def test_post_ack_silences_on_subsequent_views(self):
        import urllib.parse as _p
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                # Grab the alert to get its trigger_key
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/active"
                ) as r:
                    data = json.loads(r.read().decode())
                self.assertEqual(len(data), 1)
                a = data[0]
                tk = f"{a['kind']}|{a['deal_id']}|{a['triggered_at']}"

                body = _p.urlencode({
                    "kind": a["kind"], "deal_id": a["deal_id"],
                    "trigger_key": tk, "snooze_days": "0",
                    "note": "acknowledged by partner",
                }).encode()
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
                    ack = json.loads(r.read().decode())
                    self.assertIn("ack_id", ack)

                # Next call returns empty
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/active"
                ) as r:
                    data2 = json.loads(r.read().decode())
                self.assertEqual(data2, [])
            finally:
                server.shutdown(); server.server_close()

    def test_post_ack_missing_params_returns_400(self):
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/alerts/ack",
                    data=b"", method="POST",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()

    def test_alerts_page_has_ack_form(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertIn('action="/api/alerts/ack"', body)
                    self.assertIn('name="trigger_key"', body)
                    self.assertIn('name="snooze_days"', body)
            finally:
                server.shutdown(); server.server_close()

    def test_alerts_page_show_all_includes_acked(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            alerts = evaluate_all(store)
            a = alerts[0]
            ack_alert(store, kind=a.kind, deal_id=a.deal_id,
                      trigger_key=trigger_key_for(a))
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertIn("No active alerts", body)
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/alerts?show=all"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("Covenant TRIPPED", body)
            finally:
                server.shutdown(); server.server_close()

    def test_api_alerts_acks_audit(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            a = evaluate_all(store)[0]
            ack_alert(store, kind=a.kind, deal_id=a.deal_id,
                      trigger_key=trigger_key_for(a),
                      note="on it", acked_by="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/acks"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data), 1)
                    self.assertEqual(data[0]["note"], "on it")
                    self.assertEqual(data[0]["acked_by"], "AT")
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
