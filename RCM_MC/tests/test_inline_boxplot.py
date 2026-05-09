"""tests for ``inline_boxplot`` (P72)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import inline_boxplot


class StructureAndShape(unittest.TestCase):

    def test_emits_svg(self) -> None:
        svg = inline_boxplot(
            p10=1.5, p25=2.0, p50=2.8, p75=3.4, p90=4.1,
        )
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("inline-boxplot", svg)

    def test_default_dimensions(self) -> None:
        svg = inline_boxplot(
            p10=1.5, p25=2.0, p50=2.8, p75=3.4, p90=4.1,
        )
        # Width 50 + 2*pad(1) = 52; height 12.
        self.assertIn('width="52"', svg)
        self.assertIn('height="12"', svg)

    def test_custom_dimensions(self) -> None:
        svg = inline_boxplot(
            p10=1, p25=2, p50=3, p75=4, p90=5,
            width=120, height=24,
        )
        self.assertIn('width="122"', svg)
        self.assertIn('height="24"', svg)


class DegenerateRange(unittest.TestCase):

    def test_p10_eq_p90_does_not_crash(self) -> None:
        # All quantiles equal → no x-range; helper still renders.
        svg = inline_boxplot(p10=2.0, p25=2.0, p50=2.0, p75=2.0, p90=2.0)
        self.assertTrue(svg.startswith("<svg"))


class MissingValuesDropChart(unittest.TestCase):

    def test_any_none_returns_empty(self) -> None:
        self.assertEqual(
            inline_boxplot(p10=None, p25=2, p50=3, p75=4, p90=5),
            "",
        )

    def test_all_present_renders(self) -> None:
        self.assertNotEqual(
            inline_boxplot(p10=1, p25=2, p50=3, p75=4, p90=5),
            "",
        )


class ColumnWideBoundsForConsistentScaling(unittest.TestCase):

    def test_explicit_lo_hi_used(self) -> None:
        # Pass lo=0, hi=10 so the chart scales against the column,
        # not against this row's own quantiles.
        svg = inline_boxplot(
            p10=2, p25=3, p50=5, p75=7, p90=9,
            lo=0, hi=10,
        )
        # Median at value=5 with range 0..10 falls at width/2 = 25
        # (after padding offset 1).
        self.assertIn("26.0", svg)


if __name__ == "__main__":
    unittest.main()
