"""Tests for finance models: DCF, LBO, regression, market analysis.

DCF:
 1. build_dcf produces valid projections.
 2. Sensitivity matrix has multiple WACC/growth combos.
 3. API endpoint returns DCF for a deal.

LBO:
 4. build_lbo produces sources & uses + returns.
 5. MOIC > 1 for reasonable assumptions.
 6. API endpoint returns LBO for a deal.

REGRESSION:
 7. run_regression returns coefficients and R-squared.
 8. Portfolio regression endpoint works.

MARKET:
 9. analyze_market returns competitors and moat.
10. API endpoint returns market analysis.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

import pandas as pd

from rcm_mc.finance.dcf_model import build_dcf, build_dcf_from_deal
from rcm_mc.finance.lbo_model import build_lbo, build_lbo_from_deal
from rcm_mc.finance.regression import run_regression
from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestDCF(unittest.TestCase):

    def test_dcf_produces_projections(self):
        result = build_dcf(revenue_base=400e6, ebitda_margin_base=0.12)
        self.assertEqual(len(result.projections), 5)
        self.assertGreater(result.enterprise_value, 0)
        self.assertGreater(result.terminal_value, 0)

    def test_dcf_sensitivity(self):
        result = build_dcf(revenue_base=400e6)
        sens = result.sensitivity["wacc_vs_terminal_growth"]
        self.assertGreater(len(sens), 10)
        self.assertIn("enterprise_value", sens[0])

    def test_dcf_from_deal(self):
        result = build_dcf_from_deal({"net_revenue": 400e6, "current_ebitda": 50e6})
        self.assertGreater(result.enterprise_value, 0)

    def test_dcf_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"net_revenue": 400e6, "current_ebitda": 50e6})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/dcf",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("projections", body)
                self.assertIn("enterprise_value", body)
                self.assertIn("sensitivity", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestLBO(unittest.TestCase):

    def test_lbo_produces_returns(self):
        result = build_lbo(entry_ebitda=50e6, revenue_base=400e6)
        self.assertEqual(len(result.projections), 5)
        self.assertGreater(result.returns.moic, 0)
        self.assertGreater(result.returns.equity_invested, 0)

    def test_lbo_moic_reasonable(self):
        result = build_lbo(entry_ebitda=50e6, revenue_base=400e6)
        self.assertGreater(result.returns.moic, 1.0)
        self.assertLess(result.returns.moic, 10.0)

    def test_lbo_sources_uses_balance(self):
        result = build_lbo(entry_ebitda=50e6)
        su = result.sources_and_uses
        self.assertAlmostEqual(su.total_sources, su.total_uses, places=0)

    def test_lbo_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"net_revenue": 400e6, "current_ebitda": 50e6})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/lbo",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("sources_and_uses", body)
                self.assertIn("returns", body)
                self.assertIn("moic", body["returns"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestRegression(unittest.TestCase):

    def test_regression_runs(self):
        df = pd.DataFrame({
            "denial_rate": [10, 12, 15, 18, 20, 14, 16],
            "bed_count": [200, 150, 300, 250, 180, 220, 280],
            "days_in_ar": [45, 50, 55, 60, 48, 52, 58],
        })
        result = run_regression(df, "denial_rate", ["bed_count", "days_in_ar"])
        self.assertEqual(result.target, "denial_rate")
        self.assertEqual(result.n_observations, 7)
        self.assertGreaterEqual(result.r_squared, 0)
        self.assertLessEqual(result.r_squared, 1)
        self.assertEqual(len(result.coefficients), 2)

    def test_correlation_matrix(self):
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5],
            "b": [2, 4, 6, 8, 10],
            "c": [5, 3, 1, 2, 4],
        })
        result = run_regression(df, "a", ["b", "c"])
        self.assertIn("a", result.correlation_matrix)
        self.assertGreater(len(result.top_correlations), 0)


class TestMarketAnalysis(unittest.TestCase):

    def test_market_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Southeast Health",
                              profile={"bed_count": 332, "net_revenue": 386e6,
                                       "state": "AL", "county": "HOUSTON"})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/market",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("market_size", body)
                self.assertIn("competitors", body)
                self.assertIn("moat", body)
                self.assertIn("moat_rating", body["moat"])
                self.assertIn("hhi_index", body["moat"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
