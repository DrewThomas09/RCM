"""Tests for overdue-deadline → alert integration (Brick 115)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.alerts.alerts import evaluate_active, evaluate_all
from rcm_mc.deals.deal_deadlines import add_deadline, complete_deadline
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestOverdueAlerts(unittest.TestCase):
    def test_overdue_deadline_produces_amber_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            past = (date.today() - timedelta(days=7)).isoformat()
            add_deadline(store, deal_id="ccf", label="covenant test",
                         due_date=past)
            alerts = evaluate_all(store)
            deadline_alerts = [a for a in alerts
                               if a.kind == "deadline_overdue"]
            self.assertEqual(len(deadline_alerts), 1)
            self.assertEqual(deadline_alerts[0].severity, "amber")
            self.assertEqual(deadline_alerts[0].deal_id, "ccf")
            self.assertIn("covenant test", deadline_alerts[0].title)

    def test_future_deadline_does_not_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            future = (date.today() + timedelta(days=30)).isoformat()
            add_deadline(store, deal_id="ccf", label="board review",
                         due_date=future)
            self.assertFalse(any(a.kind == "deadline_overdue"
                                 for a in evaluate_all(store)))

    def test_completing_deadline_clears_its_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            past = (date.today() - timedelta(days=3)).isoformat()
            did = add_deadline(store, deal_id="ccf", label="audit",
                               due_date=past)
            self.assertEqual(
                len([a for a in evaluate_all(store)
                     if a.kind == "deadline_overdue"]),
                1,
            )
            complete_deadline(store, did)
            self.assertEqual(
                len([a for a in evaluate_all(store)
                     if a.kind == "deadline_overdue"]),
                0,
            )

    def test_multiple_overdue_deadlines_produce_separate_alerts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            past = (date.today() - timedelta(days=2)).isoformat()
            add_deadline(store, deal_id="ccf", label="a", due_date=past)
            add_deadline(store, deal_id="ccf", label="b", due_date=past)
            alerts = [a for a in evaluate_all(store)
                      if a.kind == "deadline_overdue"]
            self.assertEqual(len(alerts), 2)
            # Each alert has a unique trigger_key
            tks = {a.triggered_at for a in alerts}
            self.assertEqual(len(tks), 2)


class TestDeadlineAlertHttp(unittest.TestCase):
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

    def test_overdue_deadline_appears_on_alerts_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            past = (date.today() - timedelta(days=5)).isoformat()
            add_deadline(store, deal_id="ccf", label="lender call",
                         due_date=past)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertIn("Overdue: lender call", body)
                    self.assertIn("AMBER", body)
            finally:
                server.shutdown(); server.server_close()

    def test_overdue_deadline_appears_on_deal_page_alert_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            past = (date.today() - timedelta(days=1)).isoformat()
            add_deadline(store, deal_id="ccf", label="refi window",
                         due_date=past)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("Active alerts", body)
                    self.assertIn("refi window", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
