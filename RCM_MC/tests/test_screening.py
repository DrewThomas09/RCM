"""Tests for the Deal Screening Engine + dashboard route."""
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


# ── Predict ─────────────────────────────────────────────────────

class TestPredict(unittest.TestCase):
    def test_uplift_proportional_to_ebitda(self):
        from rcm_mc.screening import (
            DealCandidate, predict_deal_metrics,
        )
        small = DealCandidate(
            deal_id="A", name="Small", sector="physician_group",
            ebitda_mm=5.0, ebitda_margin=0.15)
        big = DealCandidate(
            deal_id="B", name="Big", sector="physician_group",
            ebitda_mm=50.0, ebitda_margin=0.15)
        small_r = predict_deal_metrics(small)
        big_r = predict_deal_metrics(big)
        # Bigger EBITDA → bigger uplift
        self.assertGreater(
            big_r.predicted_ebitda_uplift_mm,
            small_r.predicted_ebitda_uplift_mm)

    def test_high_concentration_lowers_confidence(self):
        from rcm_mc.screening import (
            DealCandidate, predict_deal_metrics,
        )
        clean = DealCandidate(
            deal_id="C", name="Clean", sector="hospital",
            ebitda_mm=20.0, ebitda_margin=0.18,
            payer_concentration=0.40,
            physician_concentration=0.30,
            cash_pay_share=0.05,
            out_of_network_share=0.04)
        risky = DealCandidate(
            deal_id="R", name="Risky", sector="hospital",
            ebitda_mm=20.0, ebitda_margin=0.05,
            payer_concentration=0.65,
            physician_concentration=0.50,
            cash_pay_share=0.30,
            out_of_network_share=0.18)
        clean_r = predict_deal_metrics(clean)
        risky_r = predict_deal_metrics(risky)
        self.assertLess(
            risky_r.confidence, clean_r.confidence)
        # Risky deal flagged with multiple risks
        self.assertGreater(len(risky_r.risk_factors), 1)

    def test_score_universe_sorted_by_uplift(self):
        from rcm_mc.screening import (
            DealCandidate, score_universe,
        )
        cands = [
            DealCandidate(
                deal_id=f"D{i}", name=f"Deal {i}",
                sector="physician_group",
                ebitda_mm=5.0 + i * 3, ebitda_margin=0.18)
            for i in range(5)
        ]
        results = score_universe(cands)
        uplifts = [r.predicted_ebitda_uplift_mm for r in results]
        self.assertEqual(uplifts, sorted(uplifts, reverse=True))


# ── Filter ─────────────────────────────────────────────────────

class TestFilter(unittest.TestCase):
    def test_size_range_filter(self):
        from rcm_mc.screening import (
            DealCandidate, DealFilter, apply_filter,
            score_universe,
        )
        cands = [
            DealCandidate(
                deal_id=f"D{i}", name=f"D{i}",
                sector="hospital",
                ebitda_mm=float(i * 5), ebitda_margin=0.15)
            for i in range(1, 6)    # 5, 10, 15, 20, 25
        ]
        results = score_universe(cands)
        flt = DealFilter(size_min_mm=10, size_max_mm=20)
        out = apply_filter(results, flt)
        self.assertEqual(len(out), 3)   # 10, 15, 20
        for r in out:
            self.assertGreaterEqual(r.ebitda_mm, 10)
            self.assertLessEqual(r.ebitda_mm, 20)

    def test_exclude_topic_filter(self):
        from rcm_mc.screening import (
            DealCandidate, DealFilter, apply_filter,
            score_universe,
        )
        cands = [
            # PE-history deal — picked-over flag
            DealCandidate(
                deal_id="A", name="A", sector="hospital",
                ebitda_mm=20.0, ebitda_margin=0.18,
                has_pe_history=True),
            # Clean deal
            DealCandidate(
                deal_id="B", name="B", sector="hospital",
                ebitda_mm=20.0, ebitda_margin=0.18),
        ]
        results = score_universe(cands)
        flt = DealFilter(exclude_topics=["picked-over"])
        out = apply_filter(results, flt)
        ids = {r.deal_id for r in out}
        self.assertNotIn("A", ids)
        self.assertIn("B", ids)


# ── Dashboard renderer ─────────────────────────────────────────

class TestDashboardRender(unittest.TestCase):
    def test_renders_kpis_and_table(self):
        from rcm_mc.screening import (
            DealCandidate, render_screening_dashboard,
            score_universe,
        )
        cands = [
            DealCandidate(
                deal_id="D1", name="Test Hospital",
                sector="hospital", revenue_mm=200, ebitda_mm=30,
                ebitda_margin=0.15),
        ]
        html = render_screening_dashboard(score_universe(cands))
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("Test Hospital", html)
        self.assertIn("Universe size", html)
        self.assertIn("Median uplift", html)
        # Click-through link to synthesis
        self.assertIn("/diligence/synthesis/D1", html)

    def test_empty_universe_message(self):
        from rcm_mc.screening import render_screening_dashboard
        html = render_screening_dashboard([])
        self.assertIn("No deals match", html)


# ── HTTP route ────────────────────────────────────────────────

class TestRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import RCMHandler, ServerConfig
        cls._tmp = tempfile.TemporaryDirectory()
        cls._db = os.path.join(cls._tmp.name, "p.db")
        # Seed two deals
        from rcm_mc.portfolio.store import PortfolioStore
        store = PortfolioStore(cls._db)
        store.init_db()
        with store.connect() as con:
            for did, name, sector, ebitda in (
                ("D1", "Big Hospital", "hospital", 50.0),
                ("D2", "Small PG", "physician_group", 8.0),
            ):
                con.execute(
                    "INSERT INTO deals (deal_id, name, "
                    "created_at, profile_json) "
                    "VALUES (?, ?, ?, ?)",
                    (did, name,
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps({
                         "sector": sector,
                         "ebitda_mm": ebitda,
                         "revenue_mm": ebitda * 6,
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

    def test_dashboard_renders_seeded_deals(self):
        url = (f"http://127.0.0.1:{self.port}"
               f"/screening/dashboard")
        body = urlopen(url, timeout=15).read().decode("utf-8")
        self.assertIn("Big Hospital", body)
        self.assertIn("Small PG", body)
        self.assertIn("Universe size", body)

    def test_dashboard_filter_size_min(self):
        # size_min = 20 → drops Small PG (EBITDA $8M)
        url = (f"http://127.0.0.1:{self.port}"
               f"/screening/dashboard?size_min=20")
        body = urlopen(url, timeout=15).read().decode("utf-8")
        self.assertIn("Big Hospital", body)
        self.assertNotIn("Small PG", body)


if __name__ == "__main__":
    unittest.main()
