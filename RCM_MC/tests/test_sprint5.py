"""Tests for Sprint 5: Timeline (34), Diligence Package (35), Portfolio MC (37).

TIMELINE:
 1. collect_timeline returns analysis events from analysis_runs.
 2. collect_timeline returns override events from deal_overrides.
 3. Empty deal → empty event list.
 4. Events sorted newest-first.
 5. render_timeline produces HTML with event cards.
 6. GET /deal/<id>/timeline route renders.
 7. GET /api/deals/<id>/timeline returns JSON events.

DILIGENCE PACKAGE:
 8. generate_package produces a valid zip.
 9. Zip contains manifest.json.
10. Zip contains 01_Executive_Summary.html.
11. Zip contains 05_Data_Request_List.md.
12. Zip contains 06_Risk_Register.csv.
13. Manifest has deal_id + generated_at.
14. GET /api/analysis/<id>/export?format=package returns zip bytes.

PORTFOLIO MC:
15. Empty deal list → empty result.
16. Single deal → fund EBITDA = deal EBITDA.
17. Two uncorrelated deals → diversification benefit > 0.
18. Per-deal contribution sums to 1.0.
19. Tail risk P5 < P50.
20. to_dict round-trips.
21. GET /portfolio/monte-carlo returns JSON.
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
import zipfile
from pathlib import Path

from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    DiligenceQuestion,
    DiligencePriority,
    EBITDABridgeResult,
    MetricImpact,
    RiskFlag,
    RiskSeverity,
)
from rcm_mc.exports.diligence_package import generate_package
from rcm_mc.mc.portfolio_monte_carlo import PortfolioMCResult, run_portfolio_mc
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.deal_timeline import collect_timeline, render_timeline


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


def _sample_packet():
    return DealAnalysisPacket(
        deal_id="demo", deal_name="Demo Regional", run_id="R-test",
        ebitda_bridge=EBITDABridgeResult(
            current_ebitda=60e6, target_ebitda=68e6,
            total_ebitda_impact=8e6,
            per_metric_impacts=[
                MetricImpact(metric_key="denial_rate",
                             current_value=12.0, target_value=7.0,
                             ebitda_impact=5e6),
            ],
        ),
        risk_flags=[
            RiskFlag(category="OPERATIONAL", severity=RiskSeverity.HIGH,
                     title="High denial", detail="12.5% exceeds P75"),
        ],
        diligence_questions=[
            DiligenceQuestion(
                question="Please provide denial CARC breakdown.",
                priority=DiligencePriority.P0,
                context="Top bridge lever is denial rate.",
            ),
        ],
    )


# ── Timeline ──────────────────────────────────────────────────────

class TestTimeline(unittest.TestCase):

    def test_empty_deal(self):
        store, path = _tmp_store()
        try:
            events = collect_timeline(store, "ghost", days=90)
            self.assertEqual(events, [])
        finally:
            os.unlink(path)

    def test_analysis_events_collected(self):
        from rcm_mc.analysis.analysis_store import save_packet
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            p = DealAnalysisPacket(deal_id="d1", run_id="R1")
            save_packet(store, p, inputs_hash="h1")
            events = collect_timeline(store, "d1", days=90)
            types = {e["event_type"] for e in events}
            self.assertIn("analysis", types)
        finally:
            os.unlink(path)

    def test_override_events_collected(self):
        from rcm_mc.analysis.deal_overrides import set_override
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            set_override(store, "d1", "bridge.exit_multiple", 11.0,
                         set_by="u")
            events = collect_timeline(store, "d1", days=90)
            types = {e["event_type"] for e in events}
            self.assertIn("override", types)
        finally:
            os.unlink(path)

    def test_events_sorted_newest_first(self):
        from rcm_mc.analysis.analysis_store import save_packet
        from rcm_mc.analysis.deal_overrides import set_override
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            save_packet(store, DealAnalysisPacket(deal_id="d1"),
                        inputs_hash="h1")
            set_override(store, "d1", "bridge.exit_multiple", 10.0,
                         set_by="u")
            events = collect_timeline(store, "d1", days=90)
            timestamps = [e["timestamp"] for e in events]
            self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        finally:
            os.unlink(path)

    def test_render_timeline_html(self):
        events = [
            {"event_type": "analysis", "timestamp": "2026-01-01T00:00:00",
             "title": "Packet built", "detail": "", "deal_id": "d1",
             "author": ""},
        ]
        html = render_timeline("d1", "Test Deal", events)
        self.assertIn("Packet built", html)
        self.assertIn("tl-card", html)

    def test_render_timeline_empty(self):
        html = render_timeline("d1", "Test Deal", [])
        self.assertIn("No activity", html)


# ── Diligence Package ─────────────────────────────────────────────

class TestDiligencePackage(unittest.TestCase):

    def test_generates_valid_zip(self):
        out = Path(tempfile.mkdtemp())
        path = generate_package(_sample_packet(), out)
        self.assertTrue(zipfile.is_zipfile(path))

    def test_zip_contains_manifest(self):
        out = Path(tempfile.mkdtemp())
        path = generate_package(_sample_packet(), out)
        with zipfile.ZipFile(path) as z:
            self.assertIn("manifest.json", z.namelist())

    def test_zip_contains_exec_summary(self):
        out = Path(tempfile.mkdtemp())
        path = generate_package(_sample_packet(), out)
        with zipfile.ZipFile(path) as z:
            self.assertIn("01_Executive_Summary.html", z.namelist())

    def test_zip_contains_data_request(self):
        out = Path(tempfile.mkdtemp())
        path = generate_package(_sample_packet(), out)
        with zipfile.ZipFile(path) as z:
            self.assertIn("05_Data_Request_List.md", z.namelist())
            md = z.read("05_Data_Request_List.md").decode()
            self.assertIn("denial CARC", md)

    def test_zip_contains_risk_register(self):
        out = Path(tempfile.mkdtemp())
        path = generate_package(_sample_packet(), out)
        with zipfile.ZipFile(path) as z:
            self.assertIn("06_Risk_Register.csv", z.namelist())

    def test_manifest_has_deal_id(self):
        out = Path(tempfile.mkdtemp())
        path = generate_package(_sample_packet(), out, inputs_hash="HH")
        with zipfile.ZipFile(path) as z:
            m = json.loads(z.read("manifest.json"))
        self.assertEqual(m["deal_id"], "demo")
        self.assertEqual(m["packet_hash"], "HH")
        self.assertIn("generated_at", m)

    def test_zip_has_at_least_9_files(self):
        out = Path(tempfile.mkdtemp())
        path = generate_package(_sample_packet(), out)
        with zipfile.ZipFile(path) as z:
            # 9 documents + manifest.json = 10
            self.assertGreaterEqual(len(z.namelist()), 10)


# ── Portfolio Monte Carlo ─────────────────────────────────────────

class TestPortfolioMC(unittest.TestCase):

    def test_empty_deals(self):
        r = run_portfolio_mc([])
        self.assertEqual(r.n_deals, 0)

    def test_single_deal(self):
        r = run_portfolio_mc([
            {"deal_id": "d1", "ebitda_p50": 5e6, "ebitda_std": 1e6},
        ], n_simulations=1000, seed=1)
        self.assertEqual(r.n_deals, 1)
        self.assertAlmostEqual(
            r.fund_ebitda_impact.p50, 5e6, delta=5e5,
        )

    def test_diversification_benefit_positive(self):
        r = run_portfolio_mc([
            {"deal_id": "d1", "ebitda_p50": 5e6, "ebitda_std": 2e6},
            {"deal_id": "d2", "ebitda_p50": 3e6, "ebitda_std": 1.5e6},
        ], n_simulations=5000, seed=2, within_family_rho=0.1)
        self.assertGreater(r.diversification_benefit_pct, 0.0)

    def test_contribution_sums_to_one(self):
        r = run_portfolio_mc([
            {"deal_id": "d1", "ebitda_p50": 5e6, "ebitda_std": 2e6},
            {"deal_id": "d2", "ebitda_p50": 3e6, "ebitda_std": 1.5e6},
        ], n_simulations=3000, seed=3)
        total = sum(r.per_deal_contribution.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_tail_risk_below_median(self):
        r = run_portfolio_mc([
            {"deal_id": "d1", "ebitda_p50": 5e6, "ebitda_std": 2e6},
        ], n_simulations=2000, seed=4)
        self.assertLess(r.tail_risk_p5, r.fund_ebitda_impact.p50)

    def test_to_dict_roundtrip(self):
        r = run_portfolio_mc([
            {"deal_id": "d1", "ebitda_p50": 5e6, "ebitda_std": 1e6},
        ], n_simulations=500, seed=5)
        d = r.to_dict()
        self.assertEqual(d["n_deals"], 1)
        json.dumps(d)  # must not raise


# ── Routes ────────────────────────────────────────────────────────

class TestRoutes(unittest.TestCase):

    def _start(self, db_path):
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); time.sleep(0.05)
        return server, port

    def test_timeline_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/deal/d1/timeline",
                ) as r:
                    self.assertIn("Timeline", r.read().decode())
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_timeline_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/timeline",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertIn("events", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_portfolio_mc_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/portfolio/monte-carlo",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("n_deals", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_package_export_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal(
                "d1", name="D1",
                profile={"bed_count": 200, "payer_mix": {"commercial": 1.0}},
            )
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/analysis/d1/export?format=package",
                ) as r:
                    body = r.read()
                    ctype = r.headers.get("Content-Type", "")
                self.assertIn("zip", ctype)
                self.assertTrue(body.startswith(b"PK"))
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
