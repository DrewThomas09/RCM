"""tests for ``variance_tornado`` (P70)."""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._ui_kit import variance_tornado


SAMPLE = {
    "Multiple compression": 0.41,
    "Denial improvement":   0.29,
    "Cyber probability":    0.16,
    "Regulatory headwind":  0.09,
    "Other":                0.05,
}


class StructureAndOrdering(unittest.TestCase):

    def test_each_driver_renders(self) -> None:
        html = variance_tornado(SAMPLE)
        for name in SAMPLE:
            with self.subTest(name=name):
                self.assertIn(name, html)

    def test_sorted_descending(self) -> None:
        html = variance_tornado(SAMPLE)
        positions = [
            html.find(name) for name in (
                "Multiple compression", "Denial improvement",
                "Cyber probability", "Regulatory headwind", "Other",
            )
        ]
        self.assertEqual(sorted(positions), positions)

    def test_percentages_sum_to_about_100(self) -> None:
        html = variance_tornado(SAMPLE)
        pct_strs = re.findall(r"vt-pct[^>]*>(\d+)%", html)
        total = sum(int(p) for p in pct_strs)
        self.assertGreaterEqual(total, 99)
        self.assertLessEqual(total, 101)


class BarScaling(unittest.TestCase):

    def test_leading_driver_fills_track(self) -> None:
        html = variance_tornado(SAMPLE)
        # Leading driver scaled against itself → 100%.
        self.assertIn("width:100%", html)

    def test_min_2_pct_floor(self) -> None:
        html = variance_tornado({"a": 0.999, "b": 0.001})
        # b's relative bar width would round to 0; floor at 2.
        self.assertIn("width:2%", html)


class GracefulInput(unittest.TestCase):

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(variance_tornado({}), "")

    def test_none_values_filtered(self) -> None:
        # ``None`` contributions are dropped rather than crashing.
        html = variance_tornado({"a": 0.5, "b": None, "c": 0.5})
        self.assertIn("a", html)
        self.assertNotIn(">b<", html)


if __name__ == "__main__":
    unittest.main()
