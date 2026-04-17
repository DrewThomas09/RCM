"""Tests for B109 CSV exports on /variance /escalations /cohorts."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.alerts.alert_acks import trigger_key_for
from rcm_mc.alerts.alerts import evaluate_active
from rcm_mc.deals.deal_tags import add_tag
from rcm_mc.pe.hold_tracking import record_quarterly_actuals
from tests.test_alerts import _seed_with_pe_math


def _backdate(store, *, kind, deal_id, trigger_key, days):
    from datetime import datetime, timedelta, timezone
    ts = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with store.connect() as con:
        con.execute(
            "UPDATE alert_history SET first_seen_at = ? "
            "WHERE kind = ? AND deal_id = ? AND trigger_key = ?",
            (ts, kind, deal_id, trigger_key),
        )
        con.commit()


class TestCsvExports(unittest.TestCase):
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

    def test_variance_csv_has_header_and_attachment(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 8e6},
                                     plan={"ebitda": 12e6})
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/variance?format=csv"
                ) as r:
                    self.assertIn("text/csv",
                                  r.headers.get("Content-Type", ""))
                    self.assertIn("attachment",
                                  r.headers.get("Content-Disposition", ""))
                    body = r.read().decode()
                    lines = body.strip().split("\n")
                    self.assertTrue(lines[0].startswith(
                        "deal_id,quarter,kpi,actual,plan"
                    ))
                    self.assertIn("ccf", body)
            finally:
                server.shutdown(); server.server_close()

    def test_escalations_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            alerts = evaluate_active(store)
            covenant = next(a for a in alerts if a.kind == "covenant_tripped")
            _backdate(store, kind=covenant.kind, deal_id=covenant.deal_id,
                      trigger_key=trigger_key_for(covenant), days=45)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/escalations?min_days=30&format=csv"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("ccf", body)
                    self.assertIn("days_open", body)
            finally:
                server.shutdown(); server.server_close()

    def test_cohorts_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            add_tag(store, deal_id="ccf", tag="growth")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/cohorts?format=csv"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("tag,deal_count", body)
                    self.assertIn("growth", body)
            finally:
                server.shutdown(); server.server_close()

    def test_variance_page_has_csv_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/variance") as r:
                    body = r.read().decode()
                    self.assertIn("Download CSV", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
