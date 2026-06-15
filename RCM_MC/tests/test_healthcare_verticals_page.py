"""Healthcare Verticals 2025-2026 — loader, renderer, and route.

Guards the public-source-synthesis reference bundle and its UI surface:
  1. The loader reads all 17 verticals with provenance, and the cross-file
     ``vertical_id`` join key is intact (no dataset references an unknown id).
  2. This bundle is kept OUT of the licensed-IBISWorld industry_intel loader —
     the two provenance classes must not bleed together.
  3. The index + detail pages render real, attributed content with the
     Public-source-synthesis chip (NOT the "Licensed report derived" chip).
  4. The /healthcare-verticals routes open (200) on a real server.
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

from rcm_mc.data import healthcare_verticals as hv


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LoaderTests(unittest.TestCase):
    def test_seventeen_verticals_with_provenance(self):
        vs = hv.load_verticals()
        self.assertEqual(len(vs), 17)
        for v in vs:
            for field in ("vertical_id", "group", "vertical_name",
                          "payment_system", "source", "confidence"):
                self.assertTrue(v.get(field), f"{v.get('vertical_id')} missing {field}")
            self.assertIn(v["group"], hv.GROUPS)

    def test_join_key_integrity(self):
        ids = {v["vertical_id"] for v in hv.load_verticals()}
        for loader in (hv.load_payment_updates, hv.load_payment_buildup,
                       hv.load_unit_economics, hv.load_market_structure,
                       hv.load_workforce, hv.load_sources):
            bad = {r["vertical_id"] for r in loader()} - ids
            self.assertEqual(bad, set(), f"{loader.__name__}: unknown vertical_id {bad}")

    def test_anchor_facts_present(self):
        self.assertIsNotNone(hv.vertical_by_id("dialysis_esrd"))
        self.assertEqual(len(hv.load_gene_therapy_prices()), 16)
        # ESRD CY2026 base rate is the load-bearing per-treatment anchor.
        ue = hv.load_unit_economics("dialysis_esrd")
        self.assertTrue(any(r.get("value_low") == "281.71" for r in ue))

    def test_source_kind_is_synthesis_not_licensed(self):
        self.assertEqual(hv.SOURCE_KIND, "PUBLIC_SOURCE_SYNTHESIS")

    def test_not_mixed_into_industry_intel(self):
        # The licensed-IBISWorld loader must still see exactly its 5 reports;
        # this bundle lives in a subdirectory it never reads.
        from rcm_mc.data import industry_intel as ii
        self.assertEqual(len(ii.load_industry_reports()), 5)


class RenderTests(unittest.TestCase):
    def test_index_renders_attributed(self):
        from rcm_mc.ui.data_public.healthcare_verticals_page import (
            render_verticals_intel_index)
        html = render_verticals_intel_index()
        self.assertIn("Healthcare Verticals", html)
        self.assertIn("Public-source synthesis", html)
        # Group section labels + a deep link to a detail page.
        self.assertIn("Long-Term Care", html)
        self.assertIn("/healthcare-verticals/dialysis_esrd", html)
        # Must NOT borrow the licensed-report provenance label.
        self.assertNotIn("Licensed report derived", html)

    def test_detail_renders_real_numbers(self):
        from rcm_mc.ui.data_public.healthcare_verticals_page import (
            render_vertical_intel)
        esrd = render_vertical_intel("dialysis_esrd")
        self.assertIn("281.71", esrd)
        self.assertIn("DaVita", esrd)
        gene = render_vertical_intel("cell_gene_therapy")
        self.assertIn("Lenmeldy", gene)

    def test_unknown_vertical_is_graceful(self):
        from rcm_mc.ui.data_public.healthcare_verticals_page import (
            render_vertical_intel)
        self.assertIn("not found", render_vertical_intel("nope").lower())


class RouteTests(unittest.TestCase):
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
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _get(self, path):
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{self.port}{path}", timeout=15) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""

    def test_index_and_detail_routes(self):
        s, b = self._get("/healthcare-verticals")
        self.assertEqual(s, 200)
        self.assertIn("Healthcare Verticals", b)
        s, b = self._get("/healthcare-verticals/dialysis_esrd")
        self.assertEqual(s, 200)
        self.assertIn("281.71", b)


if __name__ == "__main__":
    unittest.main()
