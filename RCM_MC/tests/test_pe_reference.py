"""PE Intelligence reference libraries (/diligence/pe-reference).

Surfaces curated, deal-independent knowledge libraries that were dark. Guards
that the real content renders, the page is honestly labeled as a curated
corpus (not live data), and it's wired into the route/tier/nav system.
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.ui.pe_reference_page import render_pe_reference_page, _LIBRARIES, _load

_SERVER = pathlib.Path(__file__).resolve().parents[1] / "rcm_mc" / "server.py"


class ReferenceLibraryTests(unittest.TestCase):
    def test_libraries_load_real_content(self):
        for key in _LIBRARIES:
            items = _load(key)
            self.assertGreaterEqual(len(items), 5, key)

    def test_failures_render_named_events(self):
        h = render_pe_reference_page("failures")
        # A real, dated, public failure must show — not a placeholder.
        self.assertIn("Envision", h)
        self.assertIn("Partner lesson", h)

    def test_traps_render_pitch_and_rebuttal(self):
        h = render_pe_reference_page("traps")
        self.assertIn("Seller pitch", h)
        self.assertIn("Partner rebuttal", h)

    def test_all_six_libraries_present_and_render(self):
        # The reference page covers six curated libraries, each from a real
        # dataclass constant — not just the original two.
        self.assertEqual(set(_LIBRARIES),
                         {"failures", "traps", "motivations", "archetypes",
                          "bidders", "narratives"})
        for key in _LIBRARIES:
            h = render_pe_reference_page(key)
            self.assertIn("DILIGENCE", h.upper())
            self.assertGreaterEqual(len(_load(key)), 5, key)

    def test_new_libraries_render_curated_content(self):
        self.assertIn("Partner play", render_pe_reference_page("motivations"))
        self.assertIn("Partner counter", render_pe_reference_page("bidders"))
        self.assertIn("What the banker says",
                      render_pe_reference_page("narratives"))
        self.assertIn("Why it breaks", render_pe_reference_page("archetypes"))

    def test_premium_badge_is_one_decimal_pct(self):
        # Standards: percentages at 1dp. Bidder premium badge must comply.
        import re
        h = render_pe_reference_page("bidders")
        self.assertRegex(h, r"\+\d+\.\d% premium")

    def test_honest_corpus_label(self):
        h = render_pe_reference_page()
        self.assertIn("Illustrative template", h)
        self.assertIn("not live data", h.lower())

    def test_unknown_library_falls_back(self):
        h = render_pe_reference_page("nope")
        self.assertIn("Historical Failures", h)
        self.assertIn("Envision", h)

    def test_route_wired(self):
        src = _SERVER.read_text()
        self.assertIn('path == "/diligence/pe-reference"', src)
        self.assertIn("render_pe_reference_page", src)

    def test_classified_and_ranked_and_linked(self):
        from rcm_mc.diligence.surface_status import classify_surface
        from rcm_mc.ui._surface_rankings import RANKINGS
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        self.assertEqual(
            classify_surface("/diligence/pe-reference")["tier"], "navy")
        self.assertIn("/diligence/pe-reference",
                      {r["route"] for r in RANKINGS.get("diligence", [])})
        self.assertIn("/diligence/pe-reference",
                      {m["route"] for m in _DEFAULT_PALETTE_MODULES})

    def test_library_catalog_links_reference(self):
        # The two reference libraries show as LIVE in the catalog, linking here.
        from rcm_mc.ui.pe_library_page import render_pe_library_page
        h = render_pe_library_page()
        self.assertIn("/diligence/pe-reference?library=failures", h)
        self.assertIn("/diligence/pe-reference?library=traps", h)


if __name__ == "__main__":
    unittest.main()
