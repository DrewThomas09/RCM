"""Tests for inline alert card on the deal detail page (Brick 103)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.alerts.alert_acks import ack_alert, trigger_key_for
from rcm_mc.alerts.alerts import evaluate_all
from tests.test_alerts import _seed_with_pe_math


class TestDealAlertCard(unittest.TestCase):
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

    def test_deal_page_shows_alert_card_when_tripped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("Active alerts", body)
                    self.assertIn("Covenant TRIPPED", body)
                    # Ack form is inline on the deal page
                    self.assertIn('action="/api/alerts/ack"', body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_hides_alert_card_when_no_alerts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertNotIn("Active alerts", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_hides_alert_card_after_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            a = next(x for x in evaluate_all(store)
                     if x.kind == "covenant_tripped")
            ack_alert(store, kind=a.kind, deal_id=a.deal_id,
                      trigger_key=trigger_key_for(a))
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertNotIn("Active alerts", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_scopes_alerts_to_this_deal(self):
        """Alerts for other deals must not show on this deal's page."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            _seed_with_pe_math(tmp, "aaa", headroom=2.0)  # safe, no alert
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/aaa") as r:
                    body = r.read().decode()
                    # aaa is safe; should have no alert card
                    self.assertNotIn("Active alerts", body)
                    # And definitely no reference to ccf's alert
                    self.assertNotIn("Covenant TRIPPED", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
