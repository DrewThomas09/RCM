"""Regression: the MA-contracts revenue/margin bars must not emit
negative SVG rect heights.

A plan with a (near-)zero or negative annual margin produced
``height="-1.7"`` — invalid SVG geometry — because the bar height was
``margin_mm / max_v * inner_h`` with no floor. Heights are now clamped
to >= 0 (a loss simply shows no margin bar).
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui.data_public.ma_contracts_page import render_ma_contracts


class MAContractsGeometryTests(unittest.TestCase):
    def test_no_negative_rect_heights(self):
        html = render_ma_contracts({})
        self.assertNotRegex(html, r'height="-[\d.]')
        self.assertNotRegex(html, r'width="-[\d.]')


if __name__ == "__main__":
    unittest.main()
