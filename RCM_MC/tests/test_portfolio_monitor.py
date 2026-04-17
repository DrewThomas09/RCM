"""Tests for the portfolio monitoring dashboard."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore


class TestPortfolioMonitor(unittest.TestCase):

    def setUp(self):
        self.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tf.close()
        self.store = PortfolioStore(self.tf.name)

    def tearDown(self):
        os.unlink(self.tf.name)

    def test_renders_empty_portfolio(self):
        from rcm_mc.ui.portfolio_monitor_page import render_portfolio_monitor
        html = render_portfolio_monitor(self.store)
        self.assertIn("SeekingChartis", html)
        self.assertIn("No active deals", html)

    def test_renders_with_deals(self):
        from rcm_mc.ui.portfolio_monitor_page import render_portfolio_monitor
        self.store.upsert_deal("d1", name="Alpha Hospital",
                               profile={"bed_count": 200})
        self.store.upsert_deal("d2", name="Beta Medical",
                               profile={"bed_count": 150})
        html = render_portfolio_monitor(self.store)
        self.assertIn("Alpha", html)
        self.assertIn("Beta", html)
        self.assertIn("Deal Status", html)
        self.assertIn("Health Distribution", html)

    def test_renders_with_actuals(self):
        from rcm_mc.ui.portfolio_monitor_page import render_portfolio_monitor
        from rcm_mc.pe.hold_tracking import record_quarterly_actuals
        self.store.upsert_deal("d1", name="Alpha")
        record_quarterly_actuals(
            self.store, "d1", "2026Q1",
            actuals={"ebitda": 12e6, "net_patient_revenue": 100e6},
            plan={"ebitda": 15e6, "net_patient_revenue": 110e6},
        )
        html = render_portfolio_monitor(self.store)
        self.assertIn("Alpha", html)

    def test_shows_alert_count(self):
        from rcm_mc.ui.portfolio_monitor_page import render_portfolio_monitor
        self.store.upsert_deal("d1", name="Alpha")
        html = render_portfolio_monitor(self.store)
        self.assertIn("Active Deals", html)

    def test_health_distribution(self):
        from rcm_mc.ui.portfolio_monitor_page import render_portfolio_monitor
        self.store.upsert_deal("d1", name="Alpha")
        self.store.upsert_deal("d2", name="Beta")
        html = render_portfolio_monitor(self.store)
        self.assertIn("Health Distribution", html)
        self.assertIn("Green", html)


if __name__ == "__main__":
    unittest.main()
