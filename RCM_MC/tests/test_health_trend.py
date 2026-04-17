"""Tests for health trend snapshots + arrows (Brick 138)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.health_score import compute_health
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _backdate_history(store, deal_id, score, days_ago=1):
    """Shove a prior-day score into history to simulate passage of time."""
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


class TestHealthTrend(unittest.TestCase):
    def test_first_call_has_flat_trend(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            h = compute_health(store, "ccf")
            self.assertEqual(h["trend"], "flat")
            self.assertEqual(h["delta"], 0)

    def test_improvement_shows_up_arrow(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)  # score=100
            _backdate_history(store, "ccf", 60, days_ago=1)
            h = compute_health(store, "ccf")
            self.assertEqual(h["trend"], "up")
            self.assertEqual(h["delta"], 40)

    def test_deterioration_shows_down_arrow(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)  # score=60
            _backdate_history(store, "ccf", 100, days_ago=2)
            h = compute_health(store, "ccf")
            self.assertEqual(h["trend"], "down")
            self.assertEqual(h["delta"], -40)

    def test_same_day_calls_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            compute_health(store, "ccf")
            compute_health(store, "ccf")
            # Today's row is one deal-date row only
            with store.connect() as con:
                rows = con.execute(
                    "SELECT COUNT(*) AS n FROM deal_health_history "
                    "WHERE deal_id='ccf'"
                ).fetchone()
            self.assertEqual(rows["n"], 1)


class TestHealthTrendHttp(unittest.TestCase):
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

    def test_api_health_includes_trend(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            _backdate_history(store, "ccf", 100, days_ago=1)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/ccf/health"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["trend"], "down")
                    self.assertLess(data["delta"], 0)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_shows_arrow_on_deterioration(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            _backdate_history(store, "ccf", 100, days_ago=1)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    # Trend arrow span with delta tooltip (distinguishes
                    # from the unrelated "↓ Download deal page" link)
                    self.assertIn('title="Δ -40', body)
                    self.assertIn("↓", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_hides_arrow_when_first_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    # No trend arrow span on flat (first-day) trends
                    # (The "↓ Download" link is a different glyph context.)
                    self.assertNotIn('title="Δ ', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
