"""Ranked "best of <section>" index pages — the nav "show more" target.

Pins that the ranked manifest is present + sane, the section-best page renders
the ranked surfaces with evidence (tier + score), and /best/<section> serves
200 end-to-end.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing


class ManifestTests(unittest.TestCase):
    def test_manifest_imports_and_has_sections(self):
        from rcm_mc.ui._surface_rankings import RANKINGS
        self.assertIn("source", RANKINGS)
        self.assertIn("diligence", RANKINGS)
        # every entry carries the fields the page renders
        for sec, rows in RANKINGS.items():
            for r in rows:
                self.assertIn("route", r)
                self.assertIn("label", r)
                self.assertIn("total", r)
                self.assertIn("tier", r)

    def test_source_leads_with_target_screener(self):
        from rcm_mc.ui._surface_rankings import RANKINGS
        self.assertEqual(RANKINGS["source"][0]["route"], "/target-screener")

    def test_each_section_sorted_descending(self):
        from rcm_mc.ui._surface_rankings import RANKINGS
        for sec, rows in RANKINGS.items():
            totals = [r["total"] for r in rows]
            self.assertEqual(totals, sorted(totals, reverse=True), sec)


class SectionBestPageTests(unittest.TestCase):
    def _r(self, section):
        from rcm_mc.ui.section_best_page import render_section_best
        return render_section_best(section)

    def test_renders_all_sections(self):
        for s in ("source", "diligence", "portfolio", "research", "library", "pipeline"):
            h = self._r(s)
            self.assertIn("<!doctype html>", h.lower(), s)
            self.assertIn("tools", h.lower(), s)

    def test_shows_tools_in_order_without_score(self):
        # Ranked order is used, but the numeric score is never surfaced.
        h = self._r("source")
        self.assertIn("Target Screener", h)
        self.assertIn("LIVE — real data", h)   # honesty tier kept
        self.assertNotRegex(h, r"\d\.\d/10")    # score hidden

    def test_no_ranking_methodology(self):
        # "Don't explain the ranking" — no score formula / source attribution.
        h = self._r("diligence")
        self.assertNotIn("Ranking from", h)
        self.assertNotIn("usefulness×1.5", h)
        self.assertNotIn("How this is ranked", h)

    def test_unknown_section_safe(self):
        h = self._r("nope")
        self.assertIn("<!doctype html>", h.lower())


class SectionBestRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as s:
            s.bind(("127.0.0.1", 0)); cls.port = s.getsockname()[1]
        from rcm_mc.server import build_server
        cls.server, _ = build_server(port=cls.port, host="127.0.0.1",
                                     db_path=os.path.join(cls.tmp.name, "t.db"), auth=None)
        cls.t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.t.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.t.join(timeout=5); cls.tmp.cleanup()

    def test_best_routes_200(self):
        for sec in ("source", "diligence", "portfolio"):
            url = f"http://127.0.0.1:{self.port}/best/{sec}"
            with urllib.request.urlopen(url, timeout=30) as r:
                self.assertEqual(r.status, 200, sec)


if __name__ == "__main__":
    unittest.main()
