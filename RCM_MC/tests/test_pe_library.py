"""PE Intelligence Library (/diligence/pe-library) + its catalog generator.

Guards the unified catalog that surfaces the long-dark pe_intelligence toolkit:
the manifest must stay populated and accurate, the page must render / search /
filter without fabricating tiers, and the live gems must link out.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

from rcm_mc.pe_intelligence._catalog import CATALOG
from rcm_mc.ui.pe_library_page import render_pe_library_page

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "build_pe_catalog.py"
_SERVER = pathlib.Path(__file__).resolve().parents[1] / "rcm_mc" / "server.py"


class CatalogManifestTests(unittest.TestCase):
    def test_manifest_is_populated(self):
        self.assertGreater(len(CATALOG), 200, "catalog under-cataloged")
        cats = {r["category"] for r in CATALOG}
        self.assertGreaterEqual(len(cats), 8)

    def test_rows_have_required_fields(self):
        for r in CATALOG:
            for k in ("slug", "title", "purpose", "category", "render_fn",
                      "loc", "wired"):
                self.assertIn(k, r)
            self.assertTrue(r["render_fn"].startswith("render_"))
            self.assertGreater(r["loc"], 0)

    def test_purpose_not_truncated_at_word_hyphen(self):
        # Regression: an earlier extractor split on word-internal hyphens
        # ("one-time" → "time …"). Purposes must be whole first lines.
        r = next(x for x in CATALOG
                 if x["slug"] == "reimbursement_cliff_calendar_2026_2029")
        self.assertIn("Reimbursement cliff calendar", r["purpose"])

    def test_generator_reproduces_manifest(self):
        spec = importlib.util.spec_from_file_location("build_pe_catalog", _SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows = mod.build_catalog()
        self.assertEqual(len(rows), len(CATALOG))


class LibraryPageTests(unittest.TestCase):
    def test_renders_and_lists_categories(self):
        h = render_pe_library_page()
        self.assertIn("PE Intelligence Library", h)
        self.assertIn("Process, IC".upper(), h.upper())

    def test_honest_label(self):
        h = render_pe_library_page()
        self.assertIn("Illustrative template", h)
        self.assertIn("not live data", h.lower())

    def test_live_gem_links_out(self):
        # The cliff calendar has a dedicated page — it must link there + be LIVE.
        h = render_pe_library_page()
        self.assertIn("/diligence/cliff-calendar", h)
        self.assertIn("LIVE", h)

    def test_search_filters(self):
        h = render_pe_library_page(q="covenant")
        self.assertIn("PE Intelligence Library", h)
        # A clearly-unrelated term yields the empty state, not a crash.
        empty = render_pe_library_page(q="zzz-no-such-tool")
        self.assertIn("No tool matches", empty)

    def test_category_filter(self):
        h = render_pe_library_page(category="Exit")
        self.assertIn("EXIT", h.upper())

    def test_route_wired(self):
        src = _SERVER.read_text()
        self.assertIn('path == "/diligence/pe-library"', src)
        self.assertIn("render_pe_library_page", src)

    def test_classified_and_navigable(self):
        from rcm_mc.diligence.surface_status import classify_surface
        from rcm_mc.ui._chartis_kit import _SUB_NAV, _DEFAULT_PALETTE_MODULES
        from rcm_mc.ui._surface_rankings import RANKINGS
        self.assertEqual(
            classify_surface("/diligence/pe-library")["tier"], "navy")
        self.assertIn("/diligence/pe-library",
                      {it["href"] for it in _SUB_NAV["diligence"]})
        self.assertIn("/diligence/pe-library",
                      {m["route"] for m in _DEFAULT_PALETTE_MODULES})
        self.assertIn("/diligence/pe-library",
                      {r["route"] for r in RANKINGS.get("diligence", [])})


if __name__ == "__main__":
    unittest.main()
