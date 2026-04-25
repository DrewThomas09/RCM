"""Tests for /insights — the full ranked list of cross-portfolio signals.

The dashboard headline card surfaces only the top-1 insight. The
/insights page renders all of them, ranked, with a tone summary
strip at the top. Reuses the same `_all_insights` generator that
the headline card uses, so the two views can't diverge.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing
from datetime import datetime, timezone


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _seed_deal(store, deal_id: str, name: str,
               sector: str = "hospital",
               sponsor: str = "") -> None:
    profile: dict = {"sector": sector}
    if sponsor:
        profile["sponsor"] = sponsor
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name,
             datetime.now(timezone.utc).isoformat(),
             json.dumps(profile)),
        )
        con.commit()


class TestAllInsightsGenerator(unittest.TestCase):
    """The new dispatcher — `_all_insights` — must compose every
    detector and return a sorted list."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_empty_list_on_empty_db(self):
        from rcm_mc.ui.dashboard_page import _all_insights
        self.assertEqual(_all_insights(self.db), [])

    def test_results_are_sorted_by_score(self):
        from rcm_mc.data.cms_pos import refresh_pos_source
        refresh_pos_source(self.store)
        # Seed enough to fire chain_concentration + all_green
        # collisions — the higher-score chain insight wins.
        _seed_deal(self.store, "100007", "LifePoint A")
        _seed_deal(self.store, "450022", "LifePoint B")
        _seed_deal(self.store, "INDEPENDENT", "Solo Hospital")

        from rcm_mc.ui.dashboard_page import _all_insights
        out = _all_insights(self.db)
        scores = [i.get("score", 0) for i in out]
        self.assertEqual(scores, sorted(scores, reverse=True),
                         msg="insights must be sorted highest-score first")

    def test_sponsor_concentration_detector(self):
        """Same sponsor on 3+ deals → fires the new
        sponsor_concentration insight."""
        for i in range(3):
            _seed_deal(self.store, f"NMC_{i}", f"NMC Deal {i}",
                       sponsor="New Mountain")

        from rcm_mc.ui.dashboard_page import _all_insights
        out = _all_insights(self.db)
        kinds = {i["kind"] for i in out}
        self.assertIn("sponsor_concentration", kinds)

    def test_sponsor_below_threshold_does_not_fire(self):
        """2 deals from same sponsor → not a flagged concentration."""
        for i in range(2):
            _seed_deal(self.store, f"NMC_{i}", f"NMC Deal {i}",
                       sponsor="New Mountain")

        from rcm_mc.ui.dashboard_page import _all_insights
        out = _all_insights(self.db)
        kinds = {i["kind"] for i in out}
        self.assertNotIn("sponsor_concentration", kinds)


class TestSingleWorstDealDetector(unittest.TestCase):
    """Mock-driven test for the new single-worst-deal insight."""

    def test_low_health_deal_surfaces(self):
        from unittest.mock import patch
        fake_deals = [
            {"deal_id": "BAD", "name": "Bad Hospital",
             "sector": "hospital", "stage": "hold",
             "score": 28, "band": "poor",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "chain": "", "chain_size": 0},
            {"deal_id": "OK_1", "name": "OK Hospital",
             "sector": "hospital", "stage": "hold",
             "score": 80, "band": "good",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "chain": "", "chain_size": 0},
        ]
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db).init_db()
            with patch(
                "rcm_mc.ui.portfolio_risk_scan_page._gather_per_deal",
                return_value=fake_deals,
            ):
                from rcm_mc.ui.dashboard_page import _all_insights
                out = _all_insights(db)
            kinds = {i["kind"] for i in out}
            self.assertIn("single_worst_deal", kinds)
            worst = next(i for i in out if i["kind"] == "single_worst_deal")
            self.assertIn("Bad Hospital", worst["headline"])
            self.assertEqual(worst["href"], "/deal/BAD")
        finally:
            tmp.cleanup()

    def test_covenant_tight_pileup_detector(self):
        """3+ TIGHT covenant deals → fires the new pileup insight."""
        from unittest.mock import patch
        fake_deals = []
        for i in range(4):
            fake_deals.append({
                "deal_id": f"TIGHT_{i}", "name": f"Tight {i}",
                "sector": "hospital", "stage": "hold",
                "score": 65, "band": "fair",
                "covenant_status": "TIGHT",
                "alerts": 0, "snap_age_days": 5,
                "open_deadlines": 0, "overdue_deadlines": 0,
                "chain": "", "chain_size": 0,
            })
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db).init_db()
            with patch(
                "rcm_mc.ui.portfolio_risk_scan_page._gather_per_deal",
                return_value=fake_deals,
            ):
                from rcm_mc.ui.dashboard_page import _all_insights
                out = _all_insights(db)
            kinds = {i["kind"] for i in out}
            self.assertIn("covenant_tight_pileup", kinds)
        finally:
            tmp.cleanup()


class TestInsightsHttpRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def test_route_returns_200(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/insights", timeout=10,
        ) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode()
        self.assertIn("All insights", html)

    def test_full_list_api(self):
        """GET /api/insights returns the full ranked list."""
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/insights", timeout=10,
        ) as resp:
            body = json.loads(resp.read())
        self.assertIn("insights", body)
        self.assertIsInstance(body["insights"], list)
        self.assertIn("count", body)


class TestSeeAllLinkOnHeadline(unittest.TestCase):
    """When >1 insight fires, the dashboard headline card links to
    /insights for the full list."""

    def test_see_all_link_appears(self):
        """Mock _gather_per_deal to deliver enough signal for
        2+ insights so the see-all hint surfaces."""
        from unittest.mock import patch
        fake_deals = []
        # Three healthy hospitals — fires all_green
        for i in range(3):
            fake_deals.append({
                "deal_id": f"H_{i}", "name": f"H{i}",
                "sector": "hospital", "stage": "hold",
                "score": 85, "band": "good",
                "covenant_status": "SAFE",
                "alerts": 0, "snap_age_days": 5,
                "open_deadlines": 0, "overdue_deadlines": 0,
                "chain": "LP_TEST", "chain_size": 3,
            })
        # Third deal in same chain → fires chain_concentration too
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db).init_db()
            with patch(
                "rcm_mc.ui.portfolio_risk_scan_page._gather_per_deal",
                return_value=fake_deals,
            ):
                from rcm_mc.ui.dashboard_page import render_dashboard
                html = render_dashboard(db)
            self.assertIn("see all", html.lower())
            self.assertIn('href="/insights"', html)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
