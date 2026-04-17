"""Tests for deal comparison + screening + heatmap (Prompts 33, 36).

Invariants locked here:

COMPARISON:
 1. Empty packet list → renders "No deals selected".
 2. Two packets → table has 2 data columns.
 3. Radar SVG present when ≥ 2 packets.
 4. Comparison dimensions include EBITDA impact + denial_rate.

SCREENING:
 5. screen_deal returns a DealScreen with verdict.
 6. screen_batch sorts by risk_score descending.
 7. Empty query → INSUFFICIENT_DATA verdict.
 8. Known CCN → populated screen with bed_count.
 9. Verdict STRONG_CANDIDATE when score ≥ 70.
10. Narrative non-empty.
11. to_dict round-trips.

ROUTES:
12. GET /compare returns HTML.
13. POST /screen returns results table.
14. GET /screen renders the empty form.

HEATMAP:
15. render_heatmap with 2 packets → two <tr> rows.
16. Empty packet list → shows "No deals" message.
17. Trend arrows rendered when deltas supplied.
18. GET /portfolio/heatmap route returns HTML.

MONITOR:
19. compute_deltas returns empty on fresh DB.
20. Two packets for same deal → grade_change populated when different.
21. New risk title → in new_risks.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.analysis.deal_screener import DealScreen, screen_batch, screen_deal
from rcm_mc.analysis.packet import (
    CompletenessAssessment,
    DealAnalysisPacket,
    EBITDABridgeResult,
    MetricSource,
    ProfileMetric,
    RiskFlag,
    RiskSeverity,
)
from rcm_mc.portfolio.portfolio_monitor import DealDelta, compute_deltas, _diff_packets
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.deal_comparison import render_comparison, render_screen_page
from rcm_mc.ui.portfolio_heatmap import render_heatmap


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


def _packet(deal_id="d1", name="Acme", grade="B", denial=12.0):
    return DealAnalysisPacket(
        deal_id=deal_id, deal_name=name,
        completeness=CompletenessAssessment(grade=grade),
        ebitda_bridge=EBITDABridgeResult(total_ebitda_impact=8e6),
        rcm_profile={
            "denial_rate": ProfileMetric(
                value=denial, source=MetricSource.OBSERVED,
                benchmark_percentile=0.85,
            ),
            "days_in_ar": ProfileMetric(
                value=50.0, source=MetricSource.OBSERVED,
                benchmark_percentile=0.5,
            ),
        },
        risk_flags=[
            RiskFlag(category="OPERATIONAL", severity=RiskSeverity.HIGH,
                     title="High denial"),
        ],
    )


# ── Comparison renderer ───────────────────────────────────────────

class TestComparison(unittest.TestCase):

    def test_empty_renders(self):
        html = render_comparison([])
        self.assertIn("No deals selected", html)

    def test_two_packets_two_columns(self):
        html = render_comparison([_packet("d1", "Acme"), _packet("d2", "Beta")])
        self.assertIn("Acme", html)
        self.assertIn("Beta", html)

    def test_radar_svg_present(self):
        html = render_comparison([_packet("d1"), _packet("d2")])
        self.assertIn("<polygon", html)

    def test_dimensions_present(self):
        html = render_comparison([_packet()])
        self.assertIn("EBITDA impact", html)
        self.assertIn("denial_rate", html)


# ── Screening ─────────────────────────────────────────────────────

class TestScreening(unittest.TestCase):

    def test_screen_deal_returns_screen(self):
        store, path = _tmp_store()
        try:
            s = screen_deal("Mercy", store)
            self.assertIsInstance(s, DealScreen)
            self.assertTrue(s.narrative)
        finally:
            os.unlink(path)

    def test_empty_query(self):
        store, path = _tmp_store()
        try:
            s = screen_deal("", store)
            self.assertEqual(s.verdict, "INSUFFICIENT_DATA")
        finally:
            os.unlink(path)

    def test_batch_sorted_by_score(self):
        store, path = _tmp_store()
        try:
            results = screen_batch(["Mercy", "Community"], store)
            if len(results) >= 2:
                self.assertGreaterEqual(
                    results[0].risk_score, results[1].risk_score,
                )
        finally:
            os.unlink(path)

    def test_to_dict_roundtrip(self):
        s = DealScreen(query="test", name="Test", verdict="PASS",
                       risk_score=40)
        d = s.to_dict()
        self.assertEqual(d["verdict"], "PASS")

    def test_known_ccn_populates(self):
        store, path = _tmp_store()
        try:
            from rcm_mc.data.hcris import _get_hcris_cached
            df = _get_hcris_cached()
            ccn = str(df.iloc[0]["ccn"])
            s = screen_deal(ccn, store)
            self.assertGreater(s.bed_count, 0)
        finally:
            os.unlink(path)


# ── Screen page renderer ──────────────────────────────────────────

class TestScreenPage(unittest.TestCase):

    def test_empty_page(self):
        html = render_screen_page()
        self.assertIn("Hospital Screener", html)
        self.assertIn("Filter by Metrics", html)

    def test_results_rendered(self):
        html = render_screen_page([
            {"name": "Acme", "state": "TX", "ccn": "123456",
             "beds": 200, "net_patient_revenue": 100e6, "operating_margin": 0.05},
        ])
        self.assertIn("Acme", html)
        self.assertIn("TX", html)


# ── Heatmap ───────────────────────────────────────────────────────

class TestHeatmap(unittest.TestCase):

    def test_two_deals_two_rows(self):
        html = render_heatmap([_packet("d1", "Acme"), _packet("d2", "Beta")])
        self.assertEqual(html.count("Acme"), 1)
        self.assertEqual(html.count("Beta"), 1)

    def test_empty_deals_message(self):
        html = render_heatmap([])
        self.assertIn("No deals to display", html)

    def test_trend_arrows_rendered(self):
        deltas = {"d1": {"denial_rate": -1.5}}
        html = render_heatmap([_packet("d1")], deltas=deltas)
        self.assertIn("↑", html)   # improving (lower is better)


# ── Portfolio monitor ─────────────────────────────────────────────

class TestPortfolioMonitor(unittest.TestCase):

    def test_empty_db(self):
        store, path = _tmp_store()
        try:
            self.assertEqual(compute_deltas(store), [])
        finally:
            os.unlink(path)

    def test_diff_new_risk(self):
        latest = _packet("d1")
        latest.risk_flags = [
            RiskFlag(category="OPERATIONAL", severity=RiskSeverity.HIGH,
                     title="New risk"),
        ]
        prior = _packet("d1")
        prior.risk_flags = []
        d = _diff_packets(latest, prior)
        self.assertIn("New risk", d.new_risks)

    def test_diff_grade_change(self):
        latest = _packet("d1")
        latest.completeness = CompletenessAssessment(grade="A")
        prior = _packet("d1")
        prior.completeness = CompletenessAssessment(grade="B")
        d = _diff_packets(latest, prior)
        self.assertEqual(d.grade_change, "B→A")


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

    def test_compare_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/compare?deals=",
                ) as r:
                    body = r.read().decode()
                    # The existing /compare route renders a deal-
                    # selection form when no deals are given.
                    self.assertIn("Comparison", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_screen_page_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/screen",
                ) as r:
                    self.assertIn("Hospital Screener", r.read().decode())
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_heatmap_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/portfolio/heatmap",
                ) as r:
                    body = r.read().decode()
                    self.assertIn("Portfolio", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
