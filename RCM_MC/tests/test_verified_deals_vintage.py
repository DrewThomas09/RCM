"""Wave-37 visual: verified-deals vintage timeline.

The 445-deal verified catalogue had outcome and sponsor bars but no
time axis — when a sector's consolidation actually happened (and
whether it dried up) was invisible. Pins the column chart: per-year
counts, drought slots preserved, filter awareness via the deals
argument, and the empty states.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public.verified_deals import verified_deals
from rcm_mc.ui.verified_deals_page import _vintage_svg, render_verified_deals


class VintageChartTests(unittest.TestCase):
    def test_renders_real_catalogue(self):
        deals = verified_deals()
        svg = _vintage_svg(deals)
        self.assertIn("<svg", svg)
        self.assertIn("ck-vd-vintage", svg)
        self.assertIn(f"{len([d for d in deals if d.get('year')])} DEALS",
                      svg)

    def test_counts_and_span(self):
        svg = _vintage_svg([
            {"year": 2018}, {"year": 2018}, {"year": 2018},
            {"year": 2021},
        ])
        # Span 2018–2021 keeps the 2019/2020 drought slots (4 year
        # labels for the small span) but draws only 2 columns.
        self.assertIn("2018–2021", svg)
        self.assertEqual(svg.count("<rect"), 2)
        self.assertIn(">2019</text>", svg)
        self.assertIn(">3</text>", svg)   # peak-year count label

    def test_single_year_renders_nothing(self):
        self.assertEqual(_vintage_svg([{"year": 2020}, {"year": 2020}]), "")
        self.assertEqual(_vintage_svg([]), "")

    def test_chart_in_page(self):
        html_out = render_verified_deals({})
        self.assertIn("ck-vd-vintage", html_out)


if __name__ == "__main__":
    unittest.main()
