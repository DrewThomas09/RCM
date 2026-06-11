"""Wave-23 visual: returns waterfall tier cascade.

The waterfall page had, ironically, no waterfall — tiers lived in a
table and the LP/GP split in a single aggregate bar. Pins the cascade
SVG: cumulative rise, LP/GP split per tier, zero tiers skipped, and
the empty state.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.waterfall_page import _tier_waterfall_svg, render_waterfall_page


def _tiers():
    return [
        {"tier_name": "Return of capital", "lp_amount": 100e6, "gp_amount": 0},
        {"tier_name": "8% preferred", "lp_amount": 40e6, "gp_amount": 0},
        {"tier_name": "GP catch-up", "lp_amount": 0, "gp_amount": 10e6},
        {"tier_name": "80/20 carry", "lp_amount": 40e6, "gp_amount": 10e6},
    ]


class TierWaterfallTests(unittest.TestCase):
    def test_renders_cascade_with_lp_gp_split(self):
        svg = _tier_waterfall_svg(_tiers())
        self.assertIn("<svg", svg)
        self.assertIn("ck-tier-waterfall", svg)
        self.assertIn("Return of capital", svg)
        self.assertIn("GP catch-up", svg)
        self.assertIn("$100.0M", svg)
        self.assertIn("CASCADE OF $200.0M TOTAL DISTRIBUTIONS", svg)

    def test_tier_order_preserved(self):
        svg = _tier_waterfall_svg(_tiers())
        self.assertLess(svg.index("Return of capital"),
                        svg.index("8% preferred"))
        self.assertLess(svg.index("8% preferred"),
                        svg.index("GP catch-up"))

    def test_zero_dollar_tiers_skipped(self):
        svg = _tier_waterfall_svg([
            {"tier_name": "Funded", "lp_amount": 50e6, "gp_amount": 0},
            {"tier_name": "Unreached", "lp_amount": 0, "gp_amount": 0},
        ])
        self.assertIn("Funded", svg)
        self.assertNotIn("Unreached", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_tier_waterfall_svg([]), "")
        self.assertEqual(
            _tier_waterfall_svg([{"tier_name": "Z", "lp_amount": 0,
                                  "gp_amount": 0}]),
            "",
        )

    def test_chart_in_page_before_tier_table(self):
        html_out = render_waterfall_page("d1", "Test Deal", {
            "lp_total": 180e6, "gp_total": 20e6, "lp_moic": 2.0,
            "gp_moic": 4.0, "lp_irr": 0.18, "gross_moic": 2.2,
            "gross_irr": 0.22, "invested": 90e6, "exit_proceeds": 200e6,
            "hold_years": 5.0, "tiers": _tiers(),
        })
        self.assertIn("ck-tier-waterfall", html_out)
        self.assertLess(html_out.index("ck-tier-waterfall"),
                        html_out.index("Waterfall Tiers"))


if __name__ == "__main__":
    unittest.main()
