"""Tests for B145 'returning after snooze' alert badge."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u
from datetime import datetime, timedelta, timezone

from rcm_mc.alerts.alert_acks import ack_alert, trigger_key_for, was_snoozed
from rcm_mc.alerts.alerts import evaluate_active, evaluate_all
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _backdate_ack_snooze(store, ack_id, days_in_past):
    """Force the most recent ack's snooze_until into the past."""
    ts = (datetime.now(timezone.utc) - timedelta(days=days_in_past)).isoformat()
    with store.connect() as con:
        con.execute(
            "UPDATE alert_acks SET snooze_until = ? WHERE ack_id = ?",
            (ts, ack_id),
        )
        con.commit()


class TestWasSnoozed(unittest.TestCase):
    def test_no_ack_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            self.assertFalse(was_snoozed(
                store, kind="k", deal_id="d", trigger_key="t",
            ))

    def test_permanent_ack_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            ack_alert(store, kind="k", deal_id="d", trigger_key="t",
                      snooze_days=0)  # permanent
            self.assertFalse(was_snoozed(
                store, kind="k", deal_id="d", trigger_key="t",
            ))

    def test_unexpired_snooze_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            ack_alert(store, kind="k", deal_id="d", trigger_key="t",
                      snooze_days=7)
            self.assertFalse(was_snoozed(
                store, kind="k", deal_id="d", trigger_key="t",
            ))

    def test_expired_snooze_returns_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            aid = ack_alert(store, kind="k", deal_id="d", trigger_key="t",
                            snooze_days=7)
            _backdate_ack_snooze(store, aid, days_in_past=1)
            self.assertTrue(was_snoozed(
                store, kind="k", deal_id="d", trigger_key="t",
            ))


class TestAlertReturningFlag(unittest.TestCase):
    def test_fresh_alert_not_returning(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            for a in evaluate_active(store):
                self.assertFalse(a.returning)

    def test_expired_snooze_marks_returning(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            alert = next(x for x in evaluate_all(store)
                         if x.kind == "covenant_tripped")
            aid = ack_alert(
                store, kind=alert.kind, deal_id=alert.deal_id,
                trigger_key=trigger_key_for(alert), snooze_days=7,
            )
            _backdate_ack_snooze(store, aid, days_in_past=1)
            active = evaluate_active(store)
            cov = next(x for x in active if x.kind == "covenant_tripped")
            self.assertTrue(cov.returning)


class TestReturningBadgeHttp(unittest.TestCase):
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

    def test_alerts_page_shows_returning_badge(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            alert = next(x for x in evaluate_all(store)
                         if x.kind == "covenant_tripped")
            aid = ack_alert(
                store, kind=alert.kind, deal_id=alert.deal_id,
                trigger_key=trigger_key_for(alert), snooze_days=7,
            )
            _backdate_ack_snooze(store, aid, days_in_past=1)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertIn("↩ returning", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_alert_card_shows_returning(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            alert = next(x for x in evaluate_all(store)
                         if x.kind == "covenant_tripped")
            aid = ack_alert(
                store, kind=alert.kind, deal_id=alert.deal_id,
                trigger_key=trigger_key_for(alert), snooze_days=7,
            )
            _backdate_ack_snooze(store, aid, days_in_past=1)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("↩ returning", body)
            finally:
                server.shutdown(); server.server_close()

    def test_no_badge_on_first_alert_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertNotIn("↩ returning", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
