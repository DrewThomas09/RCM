"""tests for ``metric_with_percentile`` (P74)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import metric_with_percentile


class StandardRendering(unittest.TestCase):

    def test_full_context_renders(self) -> None:
        out = metric_with_percentile(
            0.449, kind="percent",
            percentile=78,
            segment="ASC, vintage 2020-2024",
            n=84,
        )
        self.assertIn("44.9%", out)
        self.assertIn("P78 in ASC, vintage 2020-2024, n=84", out)

    def test_no_n_omits_n(self) -> None:
        out = metric_with_percentile(
            0.092, kind="percent",
            percentile=25,
            segment="Community Hospital",
        )
        self.assertIn("P25 in Community Hospital", out)
        self.assertNotIn("n=", out)


class MissingInput(unittest.TestCase):

    def test_missing_percentile_drops_context(self) -> None:
        out = metric_with_percentile(
            0.449, kind="percent",
            percentile=None, segment="anywhere",
        )
        self.assertEqual(out, "44.9%")

    def test_missing_value_no_context(self) -> None:
        out = metric_with_percentile(
            None, kind="percent",
            percentile=78, segment="x",
        )
        self.assertIn("muted unpopulated", out)
        self.assertNotIn("metric-percentile", out)


class Clamping(unittest.TestCase):

    def test_p100_clamped_to_99(self) -> None:
        out = metric_with_percentile(
            1.0, kind="percent", percentile=100, segment="x",
        )
        self.assertIn("P99", out)

    def test_p0_clamped_to_1(self) -> None:
        out = metric_with_percentile(
            0.0, kind="percent", percentile=0, segment="x",
        )
        self.assertIn("P1", out)


class HtmlEscaping(unittest.TestCase):

    def test_segment_escaped(self) -> None:
        out = metric_with_percentile(
            0.5, kind="percent",
            percentile=50, segment="<script>",
        )
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


if __name__ == "__main__":
    unittest.main()
