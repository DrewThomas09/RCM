"""Tests for the rcm_mc.portfolio_monitor package — distinct
from the earlier test_portfolio_monitor.py which covers a
separate prior monitoring module."""
from __future__ import annotations

import http.server
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from urllib.request import urlopen


def _baseline_snapshot():
    from rcm_mc.portfolio_monitor import (
        PortfolioAsset, PortfolioSnapshot,
    )
    return PortfolioSnapshot(
        fund_name="TestFund I",
        snapshot_date="2026-04-25",
        assets=[
            PortfolioAsset(
                deal_id="A1", name="OnTrack Co",
                sector="hospital",
                plan_ebitda_mm=20.0, actual_ebitda_mm=20.5,
                plan_revenue_mm=110.0, actual_revenue_mm=112.0,
                comparable_moic_p50=2.4, current_moic=2.4),
            PortfolioAsset(
                deal_id="A2", name="Watch Co",
                sector="physician_group",
                plan_ebitda_mm=10.0, actual_ebitda_mm=9.3,
                plan_revenue_mm=55.0, actual_revenue_mm=52.0,
                comparable_moic_p50=2.6, current_moic=2.4),
            PortfolioAsset(
                deal_id="A3", name="Warning Co",
                sector="hospital",
                plan_ebitda_mm=15.0, actual_ebitda_mm=12.7,
                plan_revenue_mm=80.0, actual_revenue_mm=70.0,
                comparable_moic_p50=2.5, current_moic=1.9),
            PortfolioAsset(
                deal_id="A4", name="Star Co",
                sector="asc",
                plan_ebitda_mm=8.0, actual_ebitda_mm=9.0,
                plan_revenue_mm=42.0, actual_revenue_mm=46.0,
                comparable_moic_p50=2.3, current_moic=3.0),
        ],
    )


class TestVariance(unittest.TestCase):
    def test_per_status_classification(self):
        from rcm_mc.portfolio_monitor import compute_variance
        pv = compute_variance(_baseline_snapshot())
        self.assertEqual(pv.by_status["on_track"], 1)
        self.assertEqual(pv.by_status["watch"], 1)
        self.assertEqual(pv.by_status["early_warning"], 1)
        self.assertEqual(pv.by_status["outperforming"], 1)

    def test_assets_sorted_by_variance_ascending(self):
        from rcm_mc.portfolio_monitor import compute_variance
        pv = compute_variance(_baseline_snapshot())
        variances = [av.ebitda_variance_pct
                     for av in pv.asset_variances]
        self.assertEqual(variances, sorted(variances))
        self.assertEqual(
            pv.asset_variances[0].status, "early_warning")

    def test_total_bridge_decomposes(self):
        from rcm_mc.portfolio_monitor import compute_variance
        pv = compute_variance(_baseline_snapshot())
        bridge_sum = sum(pv.bridge_breakdown.values())
        self.assertAlmostEqual(
            bridge_sum, pv.total_variance_mm, places=1)

    def test_severe_miss_fires_intervention_note(self):
        from rcm_mc.portfolio_monitor import (
            compute_variance, PortfolioAsset, PortfolioSnapshot,
        )
        snap = PortfolioSnapshot(
            fund_name="Test",
            assets=[
                PortfolioAsset(
                    deal_id="A", name="Severe",
                    sector="hospital",
                    plan_ebitda_mm=10.0,
                    actual_ebitda_mm=7.0)])
        pv = compute_variance(snap)
        av = pv.asset_variances[0]
        self.assertEqual(av.status, "early_warning")
        self.assertIn("intervention", av.notes.lower())

    def test_outperforming_above_peers_fires_exit_note(self):
        from rcm_mc.portfolio_monitor import (
            compute_variance, PortfolioAsset, PortfolioSnapshot,
        )
        snap = PortfolioSnapshot(
            fund_name="Test",
            assets=[
                PortfolioAsset(
                    deal_id="S", name="Star",
                    sector="asc",
                    plan_ebitda_mm=10.0,
                    actual_ebitda_mm=12.0,
                    comparable_moic_p50=2.0,
                    current_moic=2.6)])
        pv = compute_variance(snap)
        av = pv.asset_variances[0]
        self.assertEqual(av.status, "outperforming")
        self.assertIn("exit", av.notes.lower())


class TestDashboardRender(unittest.TestCase):
    def test_renders_kpi_table_bridge(self):
        from rcm_mc.portfolio_monitor import (
            compute_variance, render_monitor_dashboard,
        )
        pv = compute_variance(_baseline_snapshot())
        html = render_monitor_dashboard(pv)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        for name in ("OnTrack Co", "Watch Co",
                     "Warning Co", "Star Co"):
            self.assertIn(name, html)
        self.assertIn("Plan EBITDA", html)
        self.assertIn("Early-warning count", html)
        self.assertIn(
            "Projected-vs-Actual EBITDA Bridge", html)
        self.assertIn("early_warning", html)
        self.assertIn("outperforming", html)


class TestMonitorRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import RCMHandler, ServerConfig
        cls._tmp = tempfile.TemporaryDirectory()
        cls._db = os.path.join(cls._tmp.name, "p.db")
        from rcm_mc.portfolio.store import PortfolioStore
        store = PortfolioStore(cls._db)
        store.init_db()
        with store.connect() as con:
            for did, name, plan, actual in (
                ("M1", "Monitor One", 20.0, 22.0),
                ("M2", "Monitor Two", 15.0, 12.5),
            ):
                con.execute(
                    "INSERT INTO deals (deal_id, name, "
                    "created_at, profile_json) "
                    "VALUES (?, ?, ?, ?)",
                    (did, name,
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps({
                         "sector": "hospital",
                         "plan_ebitda_mm": plan,
                         "actual_ebitda_mm": actual,
                         "plan_revenue_mm": plan * 6,
                         "actual_revenue_mm": actual * 6,
                     })))
            con.commit()
        cls._prev = RCMHandler.config
        cfg = ServerConfig()
        cfg.db_path = cls._db
        RCMHandler.config = cfg
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", cls.port), RCMHandler)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        from rcm_mc.server import RCMHandler
        cls.server.shutdown()
        cls.server.server_close()
        RCMHandler.config = cls._prev
        cls._tmp.cleanup()

    def test_renders_monitor_dashboard(self):
        url = (f"http://127.0.0.1:{self.port}"
               f"/portfolio/monitor")
        body = urlopen(url, timeout=15).read().decode("utf-8")
        self.assertIn("Monitor One", body)
        self.assertIn("Monitor Two", body)
        self.assertIn("outperforming", body)
        self.assertIn("early_warning", body)


if __name__ == "__main__":
    unittest.main()
