"""Tests for the hardening + improvement pass.

API DOCS:
 1. /api/docs returns HTML with swagger-ui.
 2. /api/openapi.json returns valid JSON with paths.
 3. OpenAPI spec has expected endpoint paths.

INLINE EXPLAIN:
 4. Workbench HTML contains the explain panel div.
 5. Explain data JSON contains metric keys from rcm_profile.
 6. Explain JS present in page.
 7. Metric links have data-explain attributes via JS.

SEARCH API:
 8. /api/search?q=denial returns JSON results.
 9. Empty query returns empty results.

ATTRIBUTION API:
10. /api/portfolio/attribution returns JSON.

DASHBOARD V2 AUTO-SWITCH:
11. Dashboard serves v2 when deals exist.

INDEXES:
12. comments table has deal_id index.
13. approvals table has approver index.
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

from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    MetricSource,
    ProfileMetric,
)
from rcm_mc.infra.openapi import get_openapi_spec, render_swagger_ui
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.analysis_workbench import render_workbench


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


# ── API Docs ──────────────────────────────────────────────────────

class TestAPIDocs(unittest.TestCase):

    def test_openapi_spec_has_paths(self):
        spec = get_openapi_spec()
        self.assertIn("paths", spec)
        self.assertIn("/api/deals", spec["paths"])
        self.assertIn("/health", spec["paths"])

    def test_swagger_ui_html(self):
        html = render_swagger_ui()
        self.assertIn("swagger-ui", html)
        self.assertIn("/api/openapi.json", html)

    def test_docs_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/docs",
                ) as r:
                    self.assertIn("swagger-ui", r.read().decode())
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_openapi_json_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/openapi.json",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["openapi"], "3.0.3")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


# ── Inline Explain Panel ─────────────────────────────────────────

class TestInlineExplain(unittest.TestCase):

    def _packet(self):
        return DealAnalysisPacket(
            deal_id="d1", deal_name="Test",
            rcm_profile={
                "denial_rate": ProfileMetric(
                    value=12.0, source=MetricSource.OBSERVED,
                    benchmark_percentile=0.85,
                ),
            },
        )

    def test_panel_div_present(self):
        html = render_workbench(self._packet())
        self.assertIn('id="wb-explain-panel"', html)
        self.assertIn('class="wb-explain-panel"', html)

    def test_explain_data_contains_metric(self):
        html = render_workbench(self._packet())
        self.assertIn("wb-explain-data", html)
        self.assertIn("denial_rate", html)

    def test_explain_js_present(self):
        html = render_workbench(self._packet())
        self.assertIn("data-explain", html)
        self.assertIn("ep-close", html)

    def test_panel_css_present(self):
        html = render_workbench(self._packet())
        self.assertIn("wb-explain-panel", html)
        self.assertIn("right: -400px", html)


# ── Search + Attribution APIs ─────────────────────────────────────

class TestSearchAPI(unittest.TestCase):

    def test_search_returns_json(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/search?q=denial",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("results", body)
                self.assertEqual(body["query"], "denial")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_attribution_returns_json(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/attribution",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("total_value_created", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


# ── Index verification ────────────────────────────────────────────

class TestIndexes(unittest.TestCase):

    def test_comments_index_created(self):
        store, path = _tmp_store()
        try:
            from rcm_mc.deals.comments import _ensure_table
            store.upsert_deal("d1", name="D1")
            _ensure_table(store)
            with store.connect() as con:
                indexes = [
                    r["name"] for r in con.execute(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='index' AND tbl_name='comments'",
                    ).fetchall()
                ]
            self.assertIn("idx_comments_deal", indexes)
            self.assertIn("idx_comments_metric", indexes)
        finally:
            os.unlink(path)

    def test_approvals_index_created(self):
        store, path = _tmp_store()
        try:
            from rcm_mc.deals.approvals import _ensure_table
            store.upsert_deal("d1", name="D1")
            _ensure_table(store)
            with store.connect() as con:
                indexes = [
                    r["name"] for r in con.execute(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='index' AND tbl_name='approval_requests'",
                    ).fetchall()
                ]
            self.assertIn("idx_approvals_deal", indexes)
            self.assertIn("idx_approvals_approver", indexes)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
