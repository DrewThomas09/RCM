"""Tests for diligence finance: 3-statement model, denial drivers.

THREE-STATEMENT:
 1. Builds IS + BS + CF from deal profile.
 2. Balance sheet balances (A = L + E).
 3. API endpoint returns financial statements.

DENIAL DRIVERS:
 4. Identifies drivers for high denial rate.
 5. Returns expert recommendations.
 6. API endpoint works.
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

from rcm_mc.finance.three_statement import build_three_statement
from rcm_mc.finance.denial_drivers import analyze_denial_drivers
from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestThreeStatement(unittest.TestCase):

    def test_builds_from_profile(self):
        result = build_three_statement({
            "deal_id": "test", "name": "Test Hospital",
            "net_revenue": 400e6, "current_ebitda": 50e6,
        })
        self.assertGreater(
            result.income_statement.net_patient_revenue.value, 0)
        self.assertGreater(
            result.balance_sheet.total_assets.value, 0)
        self.assertNotEqual(
            result.cash_flow.free_cash_flow.value, 0)

    def test_balance_sheet_balances(self):
        result = build_three_statement({
            "deal_id": "test", "name": "Test",
            "net_revenue": 300e6,
        })
        bs = result.balance_sheet
        self.assertAlmostEqual(
            bs.total_assets.value,
            bs.total_liabilities_equity.value,
            places=0,
        )

    def test_every_line_has_source(self):
        result = build_three_statement({"net_revenue": 200e6})
        for item in result.income_statement.to_dict()["line_items"]:
            self.assertIn("source", item)
            self.assertNotEqual(item["source"], "unknown")

    def test_api_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"net_revenue": 386e6, "days_in_ar": 52})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/financials",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("income_statement", body)
                self.assertIn("balance_sheet", body)
                self.assertIn("cash_flow", body)
                self.assertIn("data_quality", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestDenialDrivers(unittest.TestCase):

    def test_identifies_drivers(self):
        result = analyze_denial_drivers({
            "deal_id": "test", "denial_rate": 18.5,
            "days_in_ar": 61, "clean_claim_rate": 82,
            "cost_to_collect": 6.8, "net_collection_rate": 91.2,
            "net_revenue": 195e6, "claims_volume": 110000,
        })
        self.assertGreater(len(result.drivers), 0)
        self.assertGreater(result.excess_denial_rate, 0)
        self.assertGreater(result.estimated_recoverable_revenue, 0)

    def test_returns_experts(self):
        result = analyze_denial_drivers({
            "denial_rate": 18, "days_in_ar": 60,
            "clean_claim_rate": 85, "net_revenue": 200e6,
        })
        self.assertGreater(len(result.expert_recommendations), 0)

    def test_value_creation_thesis(self):
        result = analyze_denial_drivers({
            "denial_rate": 18, "net_revenue": 200e6,
            "claims_volume": 100000,
        })
        self.assertIn("$", result.value_creation_thesis)

    def test_api_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"denial_rate": 18.5, "days_in_ar": 61,
                                       "clean_claim_rate": 82, "cost_to_collect": 6.8,
                                       "net_collection_rate": 91.2,
                                       "net_revenue": 195e6, "claims_volume": 110000})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/denial-drivers",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("drivers", body)
                self.assertIn("value_creation_thesis", body)
                self.assertIn("expert_recommendations", body)
                self.assertGreater(len(body["drivers"]), 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
