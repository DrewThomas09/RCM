"""Wave-17 visual: archetype confidence ladder.

The archetype page printed each match's confidence inside its own
card — the separation between a dominant primary and a marginal
runner-up was invisible. Pins the fixed-axis ladder: band tones from
the page's own _confidence_band, threshold guides, sort order,
clamping, and the empty state.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.chartis.archetype_page import (
    _confidence_band,
    _confidence_ladder_svg,
)


def _hit(name, conf):
    return SimpleNamespace(archetype=name, confidence=conf)


class ConfidenceLadderTests(unittest.TestCase):
    def test_renders_bars_with_band_tones_and_guides(self):
        svg = _confidence_ladder_svg([
            _hit("Sponsor roll-up platform", 0.78),
            _hit("Margin turnaround", 0.31),
        ])
        self.assertIn("<svg", svg)
        self.assertIn("ck-arch-ladder", svg)
        self.assertIn("0.78 HIGH", svg)
        self.assertIn("0.31 LOW", svg)
        self.assertIn(_confidence_band(0.78)[0], svg)
        self.assertIn(_confidence_band(0.31)[0], svg)
        self.assertIn("0.25 floor", svg)

    def test_sorted_by_confidence(self):
        svg = _confidence_ladder_svg([
            _hit("Weak match", 0.30),
            _hit("Strong match", 0.80),
        ])
        self.assertLess(svg.index("Strong match"), svg.index("Weak match"))

    def test_confidence_clamped(self):
        svg = _confidence_ladder_svg([_hit("Overshoot", 1.4)])
        self.assertIn("1.00 HIGH", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_confidence_ladder_svg([]), "")


if __name__ == "__main__":
    unittest.main()
