"""Connectivity sweep: corpus-deal tables drill through to /library.

Several corpus-deal tables rendered the deal name as plain text. They
now link to the deal's /library detail (keyed by source_id, TEXT).
Pins the link helpers + one end-to-end render so the drill-through
can't silently regress.
"""
from __future__ import annotations

import unittest


class CorpusDealLinkHelperTests(unittest.TestCase):
    def test_gp_benchmarking_cell_links_when_source_id(self):
        from rcm_mc.ui.data_public.gp_benchmarking_page import _deal_name_cell
        out = _deal_name_cell({"deal_name": "Acme", "source_id": "seed_001"}, 44)
        self.assertIn('href="/library/seed_001"', out)
        self.assertIn("Acme", out)

    def test_hold_analysis_cell_links_when_source_id(self):
        from rcm_mc.ui.data_public.hold_analysis_page import _deal_name_cell
        out = _deal_name_cell({"deal_name": "Beta", "source_id": "seed_009"}, 40)
        self.assertIn('href="/library/seed_009"', out)

    def test_cell_is_plain_text_without_source_id(self):
        from rcm_mc.ui.data_public.hold_analysis_page import _deal_name_cell
        out = _deal_name_cell({"deal_name": "NoId"}, 40)
        self.assertNotIn("<a href", out)
        self.assertIn("NoId", out)

    def test_source_id_is_url_quoted(self):
        from rcm_mc.ui.data_public.gp_benchmarking_page import _deal_name_cell
        out = _deal_name_cell({"deal_name": "X", "source_id": "seed 01"}, 44)
        self.assertIn("seed%2001", out)  # space url-quoted


class CorpusDealRenderTests(unittest.TestCase):
    def test_hold_analysis_renders_library_links(self):
        from rcm_mc.ui.data_public.hold_analysis_page import render_hold_analysis
        html = render_hold_analysis()
        self.assertIn("/library/", html)

    def test_comparable_outcomes_row_links_deal_name(self):
        from rcm_mc.ui.comparable_outcomes_page import _comparable_row
        cells = _comparable_row({
            "deal_name": "Cypress Health", "source_id": "seed_042",
            "deal_id": "42", "match_score": 80, "year": 2021,
        })
        joined = "".join(str(c) for c in cells)
        self.assertIn('href="/library/seed_042"', joined)
        self.assertIn("Cypress Health", joined)


if __name__ == "__main__":
    unittest.main()
