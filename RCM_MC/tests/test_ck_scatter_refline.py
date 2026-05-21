"""ck_scatter quadrant reference lines stay inside the plot frame.

A quadrant chart's value is reading points as above/below a threshold
(2.0x MOIC, 0.90 coverage, break-even 1.0x). If every point sits on one
side of the reference, the ref must still render *inside* the axes — so
the data range is expanded to include x_ref / y_ref before scaling.
Regression guard for the audit finding (ref drawn off-frame).
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._chartis_kit import ck_scatter

# Plot frame from ck_scatter constants: L=46, R=14, T=14, B=30, W=480, H=230 (default).
_TOP, _BOTTOM = 14.0, 200.0   # H-B with default height 230 → 200
_LEFT, _RIGHT = 46.0, 466.0   # W-R


class ScatterRefLineTests(unittest.TestCase):
    def _dashed_lines(self, html):
        return re.findall(
            r'<line x1="([0-9.]+)" y1="([0-9.]+)" x2="([0-9.]+)" '
            r'y2="([0-9.]+)"[^>]*stroke-dasharray',
            html,
        )

    def test_yref_above_all_points_renders_inside_frame(self):
        # All MOICs >> 2.0; the y_ref=2.0 line must still be on-plot.
        html = ck_scatter(
            [(60, 3.4, "A", "positive"), (70, 2.9, "B", "positive")],
            y_ref=2.0,
        )
        lines = self._dashed_lines(html)
        self.assertTrue(lines, "no reference line drawn")
        for x1, y1, x2, y2 in lines:
            self.assertGreaterEqual(float(y1), _TOP - 0.5)
            self.assertLessEqual(float(y1), _BOTTOM + 0.5)

    def test_xref_below_all_points_renders_inside_frame(self):
        # All consistency scores >> 30; x_ref=30 must stay on-plot.
        html = ck_scatter(
            [(78, 3.4, "A", "positive"), (66, 2.1, "B", "teal")],
            x_ref=30.0,
        )
        lines = self._dashed_lines(html)
        self.assertTrue(lines)
        for x1, y1, x2, y2 in lines:
            self.assertGreaterEqual(float(x1), _LEFT - 0.5)
            self.assertLessEqual(float(x1), _RIGHT + 0.5)

    def test_refs_within_data_range_still_work(self):
        html = ck_scatter(
            [(1.0, 1.0, "A", "teal"), (3.0, 3.0, "B", "teal")],
            x_ref=2.0, y_ref=2.0,
        )
        self.assertEqual(len(self._dashed_lines(html)), 2)


if __name__ == "__main__":
    unittest.main()
