"""Wave-34 visual: returns page covenant runway gauge.

The covenant section described headroom in KPI tiles and prose; the
runway geometry — how close current leverage sits to the ceiling,
and the same risk in EBITDA terms — was never drawn. Pins the gauge:
headroom tones, covenant line, EBITDA strip presence rules, and the
empty state.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.pe_returns_page import _covenant_runway_svg


class CovenantRunwayTests(unittest.TestCase):
    def test_renders_runway_with_headroom_tone(self):
        svg = _covenant_runway_svg(
            actual_lev=4.2, max_lev=6.0,
            cov_ebitda=50e6, trips_at=35e6,
        )
        self.assertIn("<svg", svg)
        self.assertIn("ck-covenant-runway", svg)
        self.assertIn("COVENANT 6.0x", svg)
        self.assertIn("1.8x HEADROOM", svg)
        self.assertIn("#0a8a5f", svg)          # >1.5 turns → green
        self.assertIn("cushion $15M of $50M EBITDA", svg)

    def test_tight_headroom_goes_red(self):
        svg = _covenant_runway_svg(
            actual_lev=5.8, max_lev=6.0,
            cov_ebitda=0, trips_at=0,
        )
        self.assertIn("#b5321e", svg)
        self.assertIn("0.2x HEADROOM", svg)
        # No EBITDA data → no second strip.
        self.assertNotIn("SAME RISK IN EBITDA TERMS", svg)

    def test_amber_band(self):
        svg = _covenant_runway_svg(
            actual_lev=5.0, max_lev=6.0,
            cov_ebitda=0, trips_at=0,
        )
        self.assertIn("#b8732a", svg)

    def test_missing_covenant_renders_nothing(self):
        self.assertEqual(
            _covenant_runway_svg(4.0, 0.0, 0, 0), "")
        self.assertEqual(
            _covenant_runway_svg(-1.0, 6.0, 0, 0), "")


if __name__ == "__main__":
    unittest.main()
