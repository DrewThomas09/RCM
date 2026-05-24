"""PR F — Pipeline = real deals only.

Pipeline holds the user's actual opportunities (USER DEAL data), with explicit
lifecycle entry actions and an honest empty state. Market-discovery screeners
live in Source; PE Intelligence (reference) moved to Research. Routes are
unchanged (nav placement only).
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing

from rcm_mc.ui._chartis_kit import _SUB_NAV, _resolve_sub_section


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PipelineNavTests(unittest.TestCase):
    def test_pipeline_holds_only_deal_workflow_surfaces(self):
        hrefs = [i["href"] for i in _SUB_NAV["pipeline"]]
        for real in ("/pipeline", "/new-deal", "/deal-quality",
                     "/deal-risk-scores", "/deal-flow-heatmap", "/pipeline/bridge"):
            self.assertIn(real, hrefs)
        # market-discovery / reference surfaces are NOT in Pipeline
        for gone in ("/screen", "/predictive-screener", "/pe-intelligence",
                     "/find-comps", "/conferences", "/source"):
            self.assertNotIn(gone, hrefs)

    def test_discovery_moved_to_source(self):
        src = [i["href"] for i in _SUB_NAV["source"]]
        self.assertIn("/deal-screening", src)            # thesis screening
        self.assertEqual(_resolve_sub_section("/screen"), "source")
        self.assertEqual(_resolve_sub_section("/predictive-screener"), "source")

    def test_pe_intelligence_moved_to_research(self):
        self.assertIn("/pe-intelligence",
                      [i["href"] for i in _SUB_NAV["research"]])
        self.assertEqual(_resolve_sub_section("/pe-intelligence"), "research")

    def test_new_deal_routes_resolve_to_pipeline(self):
        for r in ("/deal-quality", "/deal-risk-scores", "/deal-flow-heatmap",
                  "/pipeline/bridge", "/new-deal"):
            self.assertEqual(_resolve_sub_section(r), "pipeline")


class PipelinePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.thread.join(timeout=5); cls.tmp.cleanup()

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def test_pipeline_labeled_user_deals(self):
        status, html = self._get("/pipeline")
        self.assertEqual(status, 200)
        self.assertIn("USER DEALS", html)               # data-universe chip

    def test_explicit_lifecycle_actions(self):
        _, html = self._get("/pipeline")
        self.assertIn("Create opportunity", html)
        self.assertIn("Import deal", html)
        self.assertIn("Promote from Source", html)

    def test_honest_empty_state_on_fresh_db(self):
        # No deals seeded → honest empty state, never fabricated rows.
        _, html = self._get("/pipeline")
        self.assertIn("pipeline yet", html.lower())

    def test_no_second_rail(self):
        _, html = self._get("/pipeline")
        self.assertNotIn('<nav class="ck-subnav"', html)


if __name__ == "__main__":
    unittest.main()
