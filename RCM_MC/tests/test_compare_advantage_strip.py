"""Wave-22 visual: deal-compare advantage strip.

The compare page's table showed a delta badge per row, but the
bake-off verdict — who wins more rows, and by how much — required
tallying badges by eye. Pins the diverging strip: direction-aware
winners, relative-gap sizing with clamp marker, win tallies, zero
rows skipped, and the empty state.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.compare_page import _advantage_strip_svg


class AdvantageStripTests(unittest.TestCase):
    def test_direction_aware_winners_and_tally(self):
        svg = _advantage_strip_svg(
            [
                ("Total paid", 120.0, 100.0, True),    # left wins
                ("OON share", 12.0, 8.0, False),       # right wins (lower)
            ],
            "Alpha", "Beta",
        )
        self.assertIn("<svg", svg)
        self.assertIn("cp-advantage-strip", svg)
        self.assertIn("ALPHA WINS 1", svg)
        self.assertIn("BETA WINS 1", svg)

    def test_gap_label_and_clamp_marker(self):
        svg = _advantage_strip_svg(
            [("Huge gap", 100.0, 10.0, True)], "L", "R",
        )
        self.assertIn("90%›", svg)

    def test_zero_rows_skipped_and_tie_dot(self):
        svg = _advantage_strip_svg(
            [
                ("Both zero", 0.0, 0.0, True),
                ("Tie", 50.0, 50.0, True),
                ("Real", 10.0, 5.0, True),
            ],
            "L", "R",
        )
        self.assertNotIn("Both zero", svg)
        self.assertIn("Tie", svg)
        self.assertIn("<circle", svg)  # tie renders a neutral dot
        self.assertIn("L WINS 1", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_advantage_strip_svg([], "L", "R"), "")
        self.assertEqual(
            _advantage_strip_svg([("Z", 0.0, 0.0, True)], "L", "R"), "")


if __name__ == "__main__":
    unittest.main()
