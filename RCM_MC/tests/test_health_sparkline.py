"""Tests for B143 health-over-time sparkline on /deal/<id>."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.health_score import history_series
from tests.test_alerts import _seed_with_pe_math


def _backdate_history(store, deal_id, score, days_ago):
    from rcm_mc.deals.health_score import _ensure_history_table
    _ensure_history_table(store)
    d = (date.today() - timedelta(days=days_ago)).isoformat()
    band = "green" if score >= 80 else "amber" if score >= 50 else "red"
    with store.connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO deal_health_history "
            "(deal_id, at_date, score, band) VALUES (?, ?, ?, ?)",
            (deal_id, d, int(score), band),
        )
        con.commit()


class TestHistorySeries(unittest.TestCase):
    def test_empty_when_no_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            self.assertEqual(history_series(store, "ccf"), [])

    def test_returns_oldest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            for d, s in [(5, 90), (2, 70), (1, 60)]:
                _backdate_history(store, "ccf", s, days_ago=d)
            series = history_series(store, "ccf")
            dates = [d for d, _ in series]
            self.assertEqual(dates, sorted(dates))

    def test_days_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            for d in range(20):
                _backdate_history(store, "ccf", 80, days_ago=d + 1)
            self.assertEqual(len(history_series(store, "ccf", days=5)), 5)


class TestSparklineHttp(unittest.TestCase):
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

    def test_deal_page_hides_spark_with_less_than_2_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertNotIn("<polyline", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_renders_spark_with_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            for d, s in [(5, 100), (3, 80), (1, 60)]:
                _backdate_history(store, "ccf", s, days_ago=d)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("<polyline", body)
                    self.assertIn("Health history", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
