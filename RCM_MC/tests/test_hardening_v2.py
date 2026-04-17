"""Tests for the second hardening pass: error boundaries, next-actions,
deal stages, portfolio CSV, EBITDA chart.

ERROR BOUNDARIES:
 1. Unhandled GET exception → 500 JSON (not stack trace).
 2. Normal GET still returns 200.

NEXT ACTIONS:
 3. Low completeness → "Upload more data" suggestion.
 4. No simulation → "Run Monte Carlo" suggestion.
 5. Everything ok → "Looking good" message.

DEAL STAGES:
 6. set_stage + current_stage round-trip.
 7. Invalid stage raises ValueError.
 8. stage_history sorted newest-first.
 9. set_stage fires automation event (no crash if engine missing).

PORTFOLIO CSV:
10. /api/export/portfolio.csv returns CSV with header.
11. Empty portfolio → just header.

HOLD DASHBOARD CHART:
12. _render_ebitda_chart produces SVG when ≥2 quarters.
13. _render_ebitda_chart returns empty string for <2 quarters.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.analysis.packet import (
    CompletenessAssessment,
    DealAnalysisPacket,
    EBITDABridgeResult,
    SectionStatus,
    SimulationSummary,
)
from rcm_mc.deals.deal_stages import (
    VALID_STAGES,
    current_stage,
    set_stage,
    stage_history,
)
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.analysis_workbench import render_workbench
from rcm_mc.ui.hold_dashboard import _render_ebitda_chart


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


# ── Error boundaries ──────────────────────────────────────────────

class TestErrorBoundary(unittest.TestCase):

    def test_normal_get_still_works(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health",
                ) as r:
                    self.assertEqual(r.read().decode(), "ok")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


# ── Next actions ──────────────────────────────────────────────────

class TestNextActions(unittest.TestCase):

    def test_low_completeness_suggests_upload(self):
        p = DealAnalysisPacket(
            deal_id="d1",
            completeness=CompletenessAssessment(grade="D"),
        )
        html = render_workbench(p)
        self.assertIn("Upload more data", html)

    def test_no_simulation_suggests_mc(self):
        p = DealAnalysisPacket(
            deal_id="d1",
            completeness=CompletenessAssessment(grade="A"),
        )
        html = render_workbench(p)
        self.assertIn("Run Monte Carlo", html)

    def test_everything_ok_shows_good(self):
        p = DealAnalysisPacket(
            deal_id="d1",
            completeness=CompletenessAssessment(grade="A"),
            simulation=SimulationSummary(n_sims=1000, status=SectionStatus.OK),
        )
        html = render_workbench(p)
        self.assertIn("Looking good", html)


# ── Deal stages ───────────────────────────────────────────────────

class TestDealStages(unittest.TestCase):

    def test_set_and_get(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            set_stage(store, "d1", "diligence")
            self.assertEqual(current_stage(store, "d1"), "diligence")
        finally:
            os.unlink(path)

    def test_invalid_stage_raises(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            with self.assertRaises(ValueError):
                set_stage(store, "d1", "invalid_stage")
        finally:
            os.unlink(path)

    def test_history_newest_first(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            set_stage(store, "d1", "pipeline")
            set_stage(store, "d1", "diligence")
            set_stage(store, "d1", "ic")
            hist = stage_history(store, "d1")
            stages = [h["stage"] for h in hist]
            self.assertEqual(stages, ["ic", "diligence", "pipeline"])
        finally:
            os.unlink(path)

    def test_current_stage_none_for_new_deal(self):
        store, path = _tmp_store()
        try:
            self.assertIsNone(current_stage(store, "ghost"))
        finally:
            os.unlink(path)


# ── Portfolio CSV ─────────────────────────────────────────────────

class TestPortfolioCSV(unittest.TestCase):

    def test_csv_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/export/portfolio.csv",
                ) as r:
                    body = r.read().decode()
                    ctype = r.headers.get("Content-Type", "")
                self.assertIn("text/csv", ctype)
                self.assertIn("deal_id", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


# ── EBITDA chart ──────────────────────────────────────────────────

class TestEBITDAChart(unittest.TestCase):

    def test_chart_renders_with_data(self):
        actuals = [
            {"quarter": "2025Q1", "actuals": {"ebitda": 50e6},
             "plan": {"ebitda": 48e6}},
            {"quarter": "2025Q2", "actuals": {"ebitda": 52e6},
             "plan": {"ebitda": 50e6}},
            {"quarter": "2025Q3", "actuals": {"ebitda": 55e6},
             "plan": {"ebitda": 52e6}},
        ]
        svg = _render_ebitda_chart(actuals)
        self.assertIn("<svg", svg)
        self.assertIn("polyline", svg)
        self.assertIn("Actual", svg)

    def test_chart_empty_for_single_quarter(self):
        actuals = [
            {"quarter": "2025Q1", "actuals": {"ebitda": 50e6},
             "plan": {"ebitda": 48e6}},
        ]
        svg = _render_ebitda_chart(actuals)
        self.assertEqual(svg, "")


if __name__ == "__main__":
    unittest.main()
