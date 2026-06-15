"""Tests for the /benchmark-reference Healthcare Operational & Benchmarking
Reference page: the compute layer, the render output, and the live route.

The page presents published national reference figures (CMS / MGMA / CDC /
SEER, sourced), so the assertions pin a few load-bearing facts (the $4.9T NHE
total, DRG 871 as the #1 inpatient DRG, CPT 99214 as the top physician code,
Keytruda as the #1 Part B drug) plus the access-tiering of proprietary cells.
Follows the repo convention: the route is exercised against a real HTTP server
on a free port in open (auth=None) mode.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.request

from rcm_mc.data_public.benchmark_reference import compute_benchmark_reference
from rcm_mc.ui.data_public.benchmark_reference_page import render_benchmark_reference


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class ComputeTests(unittest.TestCase):
    def setUp(self):
        self.r = compute_benchmark_reference()

    def test_six_domains_populated(self):
        self.assertEqual(self.r.domain_count, 6)
        for tbl in (self.r.star_weights, self.r.cpt_codes, self.r.drgs,
                    self.r.partb_drugs, self.r.comp_benchmarks, self.r.shortages,
                    self.r.margin_trend, self.r.cost_structure, self.r.prevalence,
                    self.r.causes_of_death, self.r.nhe_categories,
                    self.r.nhe_payers, self.r.sources):
            self.assertTrue(tbl, "every reference table must be non-empty")

    def test_headline_facts(self):
        self.assertEqual(self.r.nhe_total_t, 4.9)
        self.assertEqual(self.r.nhe_gdp_pct, 17.6)
        self.assertIn("871", self.r.top_drg)         # sepsis is the #1 DRG
        self.assertIn("99214", self.r.top_cpt)       # top physician code
        self.assertIn("Keytruda", self.r.top_partb_drug)
        self.assertEqual(self.r.partb_total_b, 46.9)

    def test_star_weight_2026_inflection(self):
        # patient experience / access weight drops 4 -> 2 in 2026
        pe = next(s for s in self.r.star_weights if "experience" in s.category.lower())
        self.assertEqual(pe.weight_2025, 4.0)
        self.assertEqual(pe.weight_2026, 2.0)

    def test_drgs_ranked_and_sum_plausible(self):
        ranks = [d.rank for d in self.r.drgs]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(self.r.drgs[0].drg, "871")
        # top-10 share is roughly a third of inpatient volume
        total = sum(d.pct_of_volume for d in self.r.drgs)
        self.assertTrue(20.0 < total < 35.0, total)

    def test_partb_top10_share(self):
        top10 = sum(d.spend_2022_b for d in self.r.partb_drugs[:10])
        self.assertAlmostEqual(top10, 18.4, delta=0.5)  # ~$18.5B = 39%

    def test_comp_flagged_proprietary(self):
        self.assertTrue(all(c.access == "proprietary" for c in self.r.comp_benchmarks))

    def test_nhe_shares_sum_to_100(self):
        self.assertEqual(sum(c.share_pct for c in self.r.nhe_categories), 100.0)
        self.assertEqual(sum(p.share_pct for p in self.r.nhe_payers), 100.0)

    def test_sources_have_access_tier(self):
        tiers = {s.access for s in self.r.sources}
        self.assertTrue(tiers <= {"free", "proprietary", "estimate"})
        self.assertIn("free", tiers)
        self.assertIn("proprietary", tiers)


class RenderTests(unittest.TestCase):
    def test_render_contains_domains_and_sources(self):
        html = render_benchmark_reference({})
        self.assertIn("<html", html.lower())
        self.assertIn("Benchmarking Reference", html)
        self.assertIn("Domain 1", html)
        self.assertIn("Domain 6", html)
        self.assertIn("DRG 871", html)
        self.assertIn("Keytruda", html)
        # access chips surfaced
        self.assertIn("proprietary", html.lower())
        # caveats panel present
        self.assertIn("Caveats before charting", html)

    def test_render_is_idempotent_and_safe(self):
        # params unused but must not raise; None tolerated
        self.assertIn("<html", render_benchmark_reference(None).lower())


class CatalogTests(unittest.TestCase):
    def test_listed_in_all_tools_module_index(self):
        # The page must surface in the platform's "all tools" directory
        # (/module-index) with a public-data source badge.
        from rcm_mc.data_public.module_index import compute_module_index
        from rcm_mc.ui.data_public.module_index_page import _source_badge
        routes = {m.route for m in compute_module_index().modules}
        self.assertIn("/benchmark-reference", routes)
        self.assertIn("CMS", _source_badge("/benchmark-reference"))


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1", db_path=cls.db, auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _get(self, path: str):
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=10) as resp:
            return resp.status, resp.read().decode()

    def test_page_route_200(self):
        status, body = self._get("/benchmark-reference")
        self.assertEqual(status, 200)
        self.assertIn("Benchmarking Reference", body)
        self.assertIn("National Health Expenditure", body)


if __name__ == "__main__":
    unittest.main()
