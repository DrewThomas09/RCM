"""PR D — nav reorg: Research moves + the new Source section.

- Sponsor Track Record, Payer Intelligence, Find Comps → Research (they are
  reference/benchmark data, not the user's portfolio/pipeline).
- Conferences → Source (a sourcing/origination surface); Source becomes a
  top-nav section anchored by Deal Sourcing.
- Routes do NOT change (only nav placement), so no redirects are needed — the
  pages keep their URLs and just resolve to the correct section.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import (
    _CORPUS_NAV, _SUB_NAV, _resolve_sub_section,
)


class NavPlacementTests(unittest.TestCase):
    def test_source_is_a_top_nav_section(self):
        keys = [n["key"] for n in _CORPUS_NAV]
        self.assertIn("source", keys)
        # Order: Home · Source · Pipeline · …
        self.assertLess(keys.index("source"), keys.index("pipeline"))
        self.assertIn("source", _SUB_NAV)

    def test_source_holds_sourcing_surfaces(self):
        # /conferences moved in from Pipeline in this IA pass and was
        # hidden on 2026-08-16 (a networking planner, not a dataset), so
        # Deal Sourcing is what anchors Source now.
        from rcm_mc.ui._surface_visibility import is_hidden
        hrefs = [i["href"] for i in _SUB_NAV["source"]]
        self.assertIn("/source", hrefs)        # Deal Sourcing anchors Source
        self.assertTrue(is_hidden("/conferences"))
        self.assertNotIn("/conferences", hrefs)

    def test_research_reference_pages_are_now_hidden(self):
        # These three moved INTO Research in an earlier IA pass, then went
        # registry-hidden on 2026-08-16 — all three run on the seeded
        # sponsor corpus rather than a public filing. The move itself is
        # still recorded by test_portfolio_loses_reference_pages below;
        # what changed is that Research no longer carries them either.
        from rcm_mc.ui._surface_visibility import is_hidden
        hrefs = [i["href"] for i in _SUB_NAV["research"]]
        for moved in ("/sponsor-track-record", "/payer-intelligence", "/find-comps"):
            self.assertTrue(is_hidden(moved), moved)
            self.assertNotIn(moved, hrefs)

    def test_pipeline_loses_discovery_pages(self):
        hrefs = [i["href"] for i in _SUB_NAV["pipeline"]]
        for gone in ("/source", "/conferences", "/find-comps"):
            self.assertNotIn(gone, hrefs)

    def test_portfolio_loses_reference_pages(self):
        # This IA pass moved four reference pages OUT of Portfolio. The
        # bloat sweep then removed the Portfolio section altogether —
        # portfolio ops is neither provider data, a scanner, nor deal
        # tracking in the space — so the strongest form of "Portfolio does
        # not hold these" is that there is no portfolio rail at all.
        self.assertNotIn("portfolio", _SUB_NAV)


class SectionResolutionTests(unittest.TestCase):
    def test_routes_resolve_to_new_sections(self):
        self.assertEqual(_resolve_sub_section("/source"), "source")
        self.assertEqual(_resolve_sub_section("/conferences"), "source")
        self.assertEqual(_resolve_sub_section("/find-comps"), "research")
        self.assertEqual(_resolve_sub_section("/sponsor-track-record"), "research")
        self.assertEqual(_resolve_sub_section("/payer-intelligence"), "research")


if __name__ == "__main__":
    unittest.main()
