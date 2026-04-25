"""Tests for the comparable-outcomes time-saver exports.

Two endpoints are exercised end-to-end against a real
ThreadingHTTPServer:

  GET /api/diligence/comparable-outcomes.csv  → 16-col CSV
  GET /api/diligence/comparable-outcomes.memo → markdown bullets

And one HTML-render check that the export bar surfaces the
download links on the comparable outcomes page.
"""
from __future__ import annotations

import csv
import http.server
import io
import os
import socket
import tempfile
import threading
import unittest
from urllib.parse import urlencode
from urllib.request import urlopen


class _ServerCase(unittest.TestCase):
    """Spin a ThreadingHTTPServer pointed at a temp DB."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import RCMHandler, ServerConfig
        cls._tmp = tempfile.TemporaryDirectory()
        cls._db = os.path.join(cls._tmp.name, "comp.db")
        # Seed the corpus once so endpoints have data to return.
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        DealsCorpus(cls._db).seed(skip_if_populated=True)
        # Point the handler at our scratch DB. ServerConfig stores
        # values as class attributes — instantiate then mutate.
        cls._prev_config = RCMHandler.config
        cfg = ServerConfig()
        cfg.db_path = cls._db
        RCMHandler.config = cfg
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", cls.port), RCMHandler,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True,
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        from rcm_mc.server import RCMHandler
        cls.server.shutdown()
        cls.server.server_close()
        RCMHandler.config = cls._prev_config
        cls._tmp.cleanup()


class TestComparableCsvExport(_ServerCase):
    def test_csv_endpoint_returns_csv(self):
        qs = urlencode({"sector": "hospital", "ev_mm": "200",
                        "year": "2020", "top_n": "5"})
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/api/diligence/comparable-outcomes.csv?{qs}"
        )
        resp = urlopen(url, timeout=15)
        self.assertEqual(resp.status, 200)
        ct = resp.headers.get("Content-Type", "")
        self.assertIn("text/csv", ct)
        cd = resp.headers.get("Content-Disposition", "")
        self.assertIn("attachment", cd)
        self.assertIn("comparables-hospital-", cd)
        body = resp.read().decode("utf-8")

        reader = csv.reader(io.StringIO(body))
        rows = list(reader)
        # Header + at least one data row
        self.assertGreaterEqual(len(rows), 2)
        header = rows[0]
        # Schema sanity — the breakdown columns are the whole point of
        # the time-saver: partner can sort by score_sector etc. in
        # Excel without re-deriving the math.
        for col in (
            "rank", "deal_id", "deal_name", "match_score",
            "score_sector", "score_size", "score_year",
            "score_payer_mix", "score_buyer_type",
            "match_reasons",
        ):
            self.assertIn(col, header)

    def test_csv_filename_uses_today(self):
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/api/diligence/comparable-outcomes.csv?sector=hospital"
        )
        resp = urlopen(url, timeout=15)
        cd = resp.headers.get("Content-Disposition", "")
        self.assertIn(today, cd)


class TestComparableMemoExport(_ServerCase):
    def test_memo_endpoint_returns_text(self):
        qs = urlencode({"sector": "hospital", "ev_mm": "200",
                        "year": "2020"})
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/api/diligence/comparable-outcomes.memo?{qs}"
        )
        resp = urlopen(url, timeout=15)
        self.assertEqual(resp.status, 200)
        ct = resp.headers.get("Content-Type", "")
        self.assertIn("text/plain", ct)
        body = resp.read().decode("utf-8")

        # Markdown structure — paste-ready.
        self.assertIn("## Comparable benchmark", body)
        self.assertIn("hospital", body)
        self.assertIn("**Outcome distribution**", body)
        self.assertIn("**Top comparables**", body)
        # Bullets present
        self.assertIn("- ", body)

    def test_memo_renders_target_size(self):
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/api/diligence/comparable-outcomes.memo"
            f"?sector=hospital&ev_mm=350"
        )
        body = urlopen(url, timeout=15).read().decode("utf-8")
        # $350M should be rendered in the headline.
        self.assertIn("$350M", body)


class TestExportBarOnPage(unittest.TestCase):
    def test_page_surfaces_download_buttons(self):
        from rcm_mc.ui.comparable_outcomes_page import (
            render_comparable_outcomes_page,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            from rcm_mc.data_public.deals_corpus import DealsCorpus
            DealsCorpus(db).seed(skip_if_populated=True)
            html = render_comparable_outcomes_page(
                {"sector": "hospital", "ev_mm": "200", "year": "2020"},
                db_path=db,
            )
            self.assertIn(
                "/api/diligence/comparable-outcomes.csv", html)
            self.assertIn(
                "/api/diligence/comparable-outcomes.memo", html)
            self.assertIn("One-click export", html)
        finally:
            tmp.cleanup()

    def test_export_bar_absent_before_inputs(self):
        """First-load (no inputs) — the export bar should not show
        because there's nothing to export yet."""
        from rcm_mc.ui.comparable_outcomes_page import (
            render_comparable_outcomes_page,
        )
        html = render_comparable_outcomes_page({})
        self.assertNotIn(
            "/api/diligence/comparable-outcomes.csv", html)


if __name__ == "__main__":
    unittest.main()
