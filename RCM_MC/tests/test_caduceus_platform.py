"""Tests for SeekingChartis platform features: hospital profiles, screener, scores.

HOSPITAL PROFILE:
 1. GET /hospital/<ccn> renders profile page.
 2. Unknown CCN shows not found.

SEEKINGCHARTIS SCORE:
 3. Score computed with all components.
 4. Grade assigned correctly.

SCREENER:
 5. POST /api/screener/run returns matches.
 6. GET /api/screener/predefined returns preset screens.

MARKET PULSE API:
 7. GET /api/market-pulse returns indicators.

INSIGHTS API:
 8. GET /api/insights returns insights list.
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

from rcm_mc.intelligence.caduceus_score import compute_caduceus_score
from rcm_mc.intelligence.screener_engine import run_screen, Screen, Filter, PREDEFINED_SCREENS
from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestHospitalProfile(unittest.TestCase):

    def test_profile_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/hospital/010001",
                ) as r:
                    body = r.read().decode()
                self.assertIn("SOUTHEAST HEALTH", body)
                self.assertIn("SeekingChartis Score", body)
                self.assertIn("ck-topbar", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_unknown_ccn(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/hospital/999999",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Not Found", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestSeekingChartisScore(unittest.TestCase):

    def test_score_computed(self):
        score = compute_caduceus_score({
            "ccn": "010001", "name": "Test Hospital",
            "beds": 332, "net_patient_revenue": 386e6,
            "operating_expenses": 393e6, "net_income": -7e6,
        })
        self.assertGreater(score.score, 0)
        self.assertLessEqual(score.score, 100)
        self.assertIn(score.grade[0], "ABCDF")
        self.assertIn("market_position", score.components)
        self.assertIn("financial_health", score.components)

    def test_high_score_for_strong_hospital(self):
        score = compute_caduceus_score({
            "beds": 500, "net_patient_revenue": 800e6,
            "operating_expenses": 700e6, "denial_rate": 6,
            "days_in_ar": 38,
        })
        self.assertGreater(score.score, 60)


class TestScreener(unittest.TestCase):

    def test_predefined_screens_exist(self):
        self.assertGreater(len(PREDEFINED_SCREENS), 0)
        for s in PREDEFINED_SCREENS:
            self.assertTrue(s.is_predefined)

    def test_run_screen_returns_results(self):
        screen = Screen(
            name="Test: Large Hospitals",
            filters=[Filter("beds", ">=", 300)],
        )
        result = run_screen(screen, limit=10)
        self.assertGreater(result.matching_hospitals, 0)
        self.assertGreater(len(result.matches), 0)
        self.assertEqual(result.screen_name, "Test: Large Hospitals")

    def test_screener_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/screener/run",
                    data=json.dumps({
                        "name": "Big Hospitals",
                        "filters": [{"field": "beds", "operator": ">=", "value": 400}],
                        "limit": 5,
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("matches", body)
                self.assertIn("matching_hospitals", body)
                self.assertIn("summary_stats", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_predefined_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/screener/predefined",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("screens", body)
                self.assertGreater(body["count"], 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestMarketPulseAPI(unittest.TestCase):

    def test_market_pulse_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/market-pulse",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("indicators", body)
                self.assertIn("sentiment_label", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestInsightsAPI(unittest.TestCase):

    def test_insights_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="A", profile={"denial_rate": 20})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/insights",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("insights", body)
                self.assertGreater(body["count"], 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
