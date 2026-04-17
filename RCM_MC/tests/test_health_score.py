"""Tests for composite deal health score (Brick 135)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.deal_deadlines import add_deadline
from rcm_mc.deals.health_score import compute_health
from rcm_mc.pe.hold_tracking import record_quarterly_actuals
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


class TestHealthScoreCore(unittest.TestCase):
    def test_unknown_deal_score_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            h = compute_health(store, "ghost")
            self.assertIsNone(h["score"])
            self.assertEqual(h["band"], "unknown")

    def test_clean_deal_scores_100(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            h = compute_health(store, "ccf")
            self.assertEqual(h["score"], 100)
            self.assertEqual(h["band"], "green")
            self.assertEqual(h["components"], [])

    def test_tripped_covenant_deducts_40(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            h = compute_health(store, "ccf")
            self.assertEqual(h["score"], 60)
            self.assertEqual(h["band"], "amber")
            labels = [c["label"] for c in h["components"]]
            self.assertIn("Covenant TRIPPED", labels)

    def test_tight_covenant_deducts_15(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=0.3)
            h = compute_health(store, "ccf")
            self.assertEqual(h["score"], 85)
            self.assertEqual(h["band"], "green")

    def test_ebitda_miss_red_stacks_with_covenant(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)  # -40
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 8e6},  # -33% miss → -25
                plan={"ebitda": 12e6},
            )
            h = compute_health(store, "ccf")
            self.assertEqual(h["score"], 35)
            self.assertEqual(h["band"], "red")

    def test_concerning_signals_deduction(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", concerning=4)
            h = compute_health(store, "ccf")
            # 4 concerning signals = amber cluster alert (-8) via threshold
            # but also concerning_signals column → -8 (≥3) via direct deduction
            # + residual concerning_cluster amber alert = -5
            # Expect 100 - 8 - 5 = 87
            self.assertEqual(h["score"], 87)

    def test_score_clamped_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5,
                                       concerning=6)
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 1e6},
                plan={"ebitda": 12e6},
            )
            # add stacking overdue deadlines
            past = (date.today() - timedelta(days=5)).isoformat()
            for i in range(6):
                add_deadline(store, deal_id="ccf",
                             label=f"t{i}", due_date=past)
            h = compute_health(store, "ccf")
            self.assertGreaterEqual(h["score"], 0)
            self.assertEqual(h["band"], "red")

    def test_components_are_transparent(self):
        """Every deduction must be named so partners can audit the score."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            h = compute_health(store, "ccf")
            total_impact = sum(c["impact"] for c in h["components"])
            self.assertEqual(h["score"], 100 + total_impact)


class TestHealthHttp(unittest.TestCase):
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

    def test_api_health_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/ccf/health"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["deal_id"], "ccf")
                    self.assertEqual(data["score"], 60)
                    self.assertEqual(data["band"], "amber")
                    self.assertTrue(len(data["components"]) >= 1)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_shows_health_kpi_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("Health (green)", body)
                    self.assertIn(">\n          100\n", body)
            finally:
                server.shutdown(); server.server_close()

    def test_deal_page_health_red_for_broken_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 5e6},
                plan={"ebitda": 12e6},
            )
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("Health (red)", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
