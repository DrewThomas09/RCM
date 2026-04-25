"""Tests for the /diligence/synthesis HTTP routes.

The IC binder + synthesis runner already work standalone; these
tests verify that the partner can hit them from a browser /
external pipeline via two routes:

  GET /diligence/synthesis/<deal_id>      → IC binder HTML
  GET /api/diligence/synthesis/<deal_id>  → JSON summary

Both routes build a DiligenceDossier from the portfolio store
and run_full_diligence; they fail open per-packet so a deal with
no QoE / no cohort / etc. still renders an IC binder with the
data-gaps appendix.
"""
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
from urllib.error import HTTPError
from urllib.request import urlopen


def _seed_deal(db_path: str, deal_id: str = "DEAL_TEST",
               name: str = "Test Hospital Co") -> None:
    from rcm_mc.portfolio.store import PortfolioStore
    store = PortfolioStore(db_path)
    store.init_db()
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, "
            "profile_json) VALUES (?, ?, ?, ?)",
            (deal_id, name,
             datetime.now(timezone.utc).isoformat(),
             json.dumps({
                 "sector": "hospital",
                 "states": ["TX"],
                 "ebitda_mm": 50.0,
                 "revenue_mm": 280.0,
             })),
        )
        con.commit()


class _ServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import RCMHandler, ServerConfig
        cls._tmp = tempfile.TemporaryDirectory()
        cls._db = os.path.join(cls._tmp.name, "p.db")
        _seed_deal(cls._db)

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
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        from rcm_mc.server import RCMHandler
        cls.server.shutdown()
        cls.server.server_close()
        RCMHandler.config = cls._prev_config
        cls._tmp.cleanup()


class TestHTMLRoute(_ServerCase):
    def test_renders_ic_binder_html(self):
        url = (f"http://127.0.0.1:{self.port}"
               f"/diligence/synthesis/DEAL_TEST")
        body = urlopen(url, timeout=15).read().decode("utf-8")
        self.assertIn("<!DOCTYPE html>", body)
        self.assertIn("IC Binder", body)
        self.assertIn("Test Hospital Co", body)

    def test_unknown_deal_returns_404(self):
        url = (f"http://127.0.0.1:{self.port}"
               f"/diligence/synthesis/UNKNOWN")
        try:
            urlopen(url, timeout=15)
            self.fail("Expected HTTPError")
        except HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_empty_deal_id_returns_404(self):
        url = (f"http://127.0.0.1:{self.port}"
               f"/diligence/synthesis/")
        try:
            urlopen(url, timeout=15)
            self.fail("Expected HTTPError")
        except HTTPError as e:
            self.assertEqual(e.code, 404)


class TestJSONRoute(_ServerCase):
    def test_returns_json_summary(self):
        url = (f"http://127.0.0.1:{self.port}"
               f"/api/diligence/synthesis/DEAL_TEST")
        resp = urlopen(url, timeout=15)
        body = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(body["deal_name"], "Test Hospital Co")
        self.assertIn("sections_run", body)
        self.assertIn("missing_inputs", body)
        self.assertEqual(body["sections_total"], 13)
        # With only the deal record (no cohort, no graph, no
        # corpus, etc.), most sections should be marked missing.
        self.assertGreater(len(body["missing_inputs"]), 0)

    def test_unknown_deal_json_404(self):
        url = (f"http://127.0.0.1:{self.port}"
               f"/api/diligence/synthesis/UNKNOWN")
        try:
            urlopen(url, timeout=15)
            self.fail("Expected HTTPError")
        except HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()
