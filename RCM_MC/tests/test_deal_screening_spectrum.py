"""Wave-14 visual: deal-screening risk distribution strip.

The screening page showed PASS/WATCH/FAIL tile counts and a table,
but never the population on the risk axis — moving a threshold in the
form gave no picture of which deals shift verdict. Pins the strip:
decision tones, the dynamic threshold guides, out-of-range guides
omitted, and the empty state rendering nothing.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.chartis.deal_screening_page import (
    _DECISION_COLORS,
    _risk_distribution_svg,
)


def _r(score, decision):
    return SimpleNamespace(risk_composite=score, decision=decision)


class RiskDistributionTests(unittest.TestCase):
    def test_renders_dots_and_threshold_guides(self):
        svg = _risk_distribution_svg(
            [_r(20, "PASS"), _r(55, "WATCH"), _r(85, "FAIL")],
            watch_thr=50, max_thr=75,
        )
        self.assertIn("<svg", svg)
        self.assertIn("ds-risk-spectrum", svg)
        self.assertIn("WATCH ≥50", svg)
        self.assertIn("REJECT ≥75", svg)
        for d in ("PASS", "WATCH", "FAIL"):
            self.assertIn(_DECISION_COLORS[d], svg)
        self.assertIn("3 DEALS", svg)

    def test_out_of_range_threshold_guide_omitted(self):
        svg = _risk_distribution_svg(
            [_r(20, "PASS")], watch_thr=50, max_thr=250,
        )
        self.assertIn("WATCH ≥50", svg)
        self.assertNotIn("REJECT", svg)

    def test_unscored_results_skipped(self):
        svg = _risk_distribution_svg(
            [_r(None, "PASS"), _r(40, "WATCH")],
            watch_thr=50, max_thr=75,
        )
        self.assertIn("1 DEALS", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(
            _risk_distribution_svg([], watch_thr=50, max_thr=75), "")
        self.assertEqual(
            _risk_distribution_svg(
                [_r(None, "PASS")], watch_thr=50, max_thr=75),
            "",
        )


if __name__ == "__main__":
    unittest.main()
