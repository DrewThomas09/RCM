"""Pin for the band-position bullet on /partner-review.

The reasonableness-bands table compared an observed value against a
numeric [lo, hi] band as two mono numbers. The bullet shows the position
visually — shaded acceptable band + observed marker, green inside / red
outside — so in-band vs out-of-band reads at a glance. Falls back to the
text band when the inputs aren't numeric.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis.partner_review_page import _band_bullet


class BandBulletTests(unittest.TestCase):
    def test_in_band_marker_is_positive(self):
        svg = _band_bullet(1.5, 1.0, 2.0)
        self.assertIn("<svg", svg)
        self.assertIn("sc-positive", svg)
        self.assertNotIn("sc-negative", svg)

    def test_out_of_band_marker_is_negative(self):
        self.assertIn("sc-negative", _band_bullet(3.0, 1.0, 2.0))   # above
        self.assertIn("sc-negative", _band_bullet(0.2, 1.0, 2.0))   # below

    def test_reversed_bounds_normalized(self):
        # hi < lo should still classify 1.5 as in-band [1,2].
        self.assertIn("sc-positive", _band_bullet(1.5, 2.0, 1.0))

    def test_non_numeric_returns_empty(self):
        self.assertEqual(_band_bullet("n/a", None, None), "")
        self.assertEqual(_band_bullet(1.0, "x", 2.0), "")

    def test_band_rect_and_marker_present(self):
        svg = _band_bullet(1.5, 1.0, 2.0)
        self.assertIn("<rect", svg)   # shaded acceptable band
        self.assertIn("<line", svg)   # observed marker + baseline


if __name__ == "__main__":
    unittest.main()
