"""Wave-12 visual: market-structure 100% composition strip.

The shares table ranked each player against its own bar, but the
unallocated remainder — the fragmented tail that IS the roll-up
whitespace the verdict talks about — was invisible. Pins the strip:
proportional segments, target highlighting, the fragmented-remainder
block, no remainder invented when shares already sum to 100%, and the
empty state rendering nothing.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis.market_structure_page import _market_composition_svg


class MarketCompositionStripTests(unittest.TestCase):
    def test_renders_players_and_fragmented_remainder(self):
        svg = _market_composition_svg(
            {"Alpha Health": 0.30, "Beta Care": 0.20, "Gamma": 0.10},
            target_name="Alpha Health",
        )
        self.assertIn("<svg", svg)
        self.assertIn("ck-mkt-composition", svg)
        self.assertIn("Alpha Health", svg)
        self.assertIn("fragmented 40%", svg)
        self.assertIn("ROLL-UP WHITESPACE", svg)

    def test_fully_allocated_market_has_no_remainder(self):
        svg = _market_composition_svg(
            {"Duo A": 0.6, "Duo B": 0.4}, target_name=None,
        )
        self.assertNotIn("fragmented", svg)
        self.assertNotIn("ROLL-UP WHITESPACE", svg)

    def test_segments_sorted_largest_first(self):
        svg = _market_composition_svg(
            {"Small": 0.10, "Big": 0.50}, target_name=None,
        )
        self.assertLess(svg.index("Big"), svg.index("Small"))

    def test_zero_and_negative_shares_skipped(self):
        svg = _market_composition_svg(
            {"Real": 0.4, "Ghost": 0.0, "Bad": -0.1}, target_name=None,
        )
        self.assertIn("Real", svg)
        self.assertNotIn("Ghost", svg)
        self.assertNotIn("Bad", svg)

    def test_empty_shares_render_nothing(self):
        self.assertEqual(_market_composition_svg({}, target_name=None), "")
        self.assertEqual(
            _market_composition_svg({"Ghost": 0.0}, target_name=None), "")


if __name__ == "__main__":
    unittest.main()
