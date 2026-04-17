"""Tests for /variance portfolio drill-down (Brick 108)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.pe.hold_tracking import portfolio_variance_matrix, record_quarterly_actuals
from tests.test_alerts import _seed_with_pe_math


class TestVarianceMatrix(unittest.TestCase):
    def test_empty_store_returns_empty_df(self):
        with tempfile.TemporaryDirectory() as tmp:
            from rcm_mc.portfolio.store import PortfolioStore
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            df = portfolio_variance_matrix(store)
            self.assertTrue(df.empty)
            self.assertIn("deal_id", df.columns)

    def test_latest_per_deal_when_quarter_unspecified(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_quarterly_actuals(store, "ccf", "2025Q4",
                                     actuals={"ebitda": 10e6},
                                     plan={"ebitda": 12e6})
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 11.5e6},
                                     plan={"ebitda": 12e6})
            df = portfolio_variance_matrix(store)
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["quarter"], "2026Q1")

    def test_worst_variance_sorted_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "big_miss")
            _seed_with_pe_math(tmp, "on_plan")
            record_quarterly_actuals(store, "big_miss", "2026Q1",
                                     actuals={"ebitda": 6e6},   # -50%
                                     plan={"ebitda": 12e6})
            record_quarterly_actuals(store, "on_plan", "2026Q1",
                                     actuals={"ebitda": 12e6},  # 0%
                                     plan={"ebitda": 12e6})
            df = portfolio_variance_matrix(store)
            self.assertEqual(df.iloc[0]["deal_id"], "big_miss")

    def test_quarter_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_quarterly_actuals(store, "ccf", "2025Q4",
                                     actuals={"ebitda": 10e6},
                                     plan={"ebitda": 12e6})
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 11.5e6},
                                     plan={"ebitda": 12e6})
            df = portfolio_variance_matrix(store, quarter="2025Q4")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["quarter"], "2025Q4")


class TestVarianceHttp(unittest.TestCase):
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

    def test_variance_page_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/variance") as r:
                    body = r.read().decode()
                    self.assertIn("No variance rows", body)
            finally:
                server.shutdown(); server.server_close()

    def test_variance_page_lists_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 8e6},
                                     plan={"ebitda": 12e6})
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/variance") as r:
                    body = r.read().decode()
                    self.assertIn("ccf", body)
                    self.assertIn("OFF TRACK", body)
                    self.assertIn("2026Q1", body)
            finally:
                server.shutdown(); server.server_close()

    def test_variance_severity_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "miss")
            _seed_with_pe_math(tmp, "good")
            record_quarterly_actuals(store, "miss", "2026Q1",
                                     actuals={"ebitda": 8e6},
                                     plan={"ebitda": 12e6})
            record_quarterly_actuals(store, "good", "2026Q1",
                                     actuals={"ebitda": 12e6},
                                     plan={"ebitda": 12e6})
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/variance?severity=off_track"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("miss", body)
                    # "good" deal must not appear (it's on_track)
                    self.assertNotIn("<td><a href='/deal/good'", body)
            finally:
                server.shutdown(); server.server_close()

    def test_api_portfolio_variance_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 8e6},
                                     plan={"ebitda": 12e6})
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/variance"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data), 1)
                    self.assertEqual(data[0]["deal_id"], "ccf")
                    self.assertEqual(data[0]["severity"], "off_track")
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_variance_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('href="/variance"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
