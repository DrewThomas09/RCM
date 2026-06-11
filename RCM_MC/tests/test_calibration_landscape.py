"""Wave-25 visual: calibration payer landscape.

The calibration page showed one slider card per payer — comparing
payers meant eyeballing slider positions across cards. Pins the
landscape SVG: all payers as dots on the same three fixed axes the
sliders use, value clamping, and the empty state.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.calibration_page import _payer_landscape_svg


def _aggs():
    return {
        "Medicare": {"idr_m": 0.08, "fwr_m": 0.20, "dar_m": 38.0,
                     "n_entries": 12.0},
        "Medicaid": {"idr_m": 0.15, "fwr_m": 0.35, "dar_m": 55.0,
                     "n_entries": 8.0},
        "Commercial": {"idr_m": 0.11, "fwr_m": 0.28, "dar_m": 47.0,
                       "n_entries": 10.0},
    }


class PayerLandscapeTests(unittest.TestCase):
    def test_renders_all_payers_on_three_axes(self):
        svg = _payer_landscape_svg(_aggs())
        self.assertIn("<svg", svg)
        self.assertIn("ck-payer-landscape", svg)
        for payer in ("Medicare", "Medicaid", "Commercial"):
            self.assertIn(payer, svg)
        for axis in ("IDR mean", "FWR mean", "DAR days"):
            self.assertIn(axis, svg)
        # 3 payers × 3 axes = 9 dots.
        self.assertEqual(svg.count("<circle"), 9)

    def test_axis_ticks_match_slider_ranges(self):
        svg = _payer_landscape_svg(_aggs())
        self.assertIn("0.500", svg)   # IDR max
        self.assertIn("0.800", svg)   # FWR max
        self.assertIn("120", svg)     # DAR max

    def test_out_of_range_value_clamped(self):
        svg = _payer_landscape_svg({
            "Weird": {"idr_m": 2.0, "fwr_m": 0.1, "dar_m": 300.0,
                      "n_entries": 1.0},
        })
        # IDR axis ends at x = 110 + 560 = 670; clamped dot sits there.
        self.assertIn('cx="670.0"', svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_payer_landscape_svg({}), "")


if __name__ == "__main__":
    unittest.main()
