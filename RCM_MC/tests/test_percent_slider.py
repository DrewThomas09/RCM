"""tests for ``percent_slider`` (P84)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import percent_slider


class StructureAndContent(unittest.TestCase):

    def test_renders_input_and_label(self) -> None:
        html = percent_slider(
            "medicare_share",
            label="Medicare share",
            default=0.45,
        )
        self.assertIn('name="medicare_share"', html)
        self.assertIn('Medicare share', html)
        self.assertIn('type="range"', html)
        self.assertIn('value="0.45"', html)

    def test_initial_output_renders_as_pct(self) -> None:
        html = percent_slider(
            "x", label="X", default=0.45,
        )
        self.assertIn(">45.0%<", html)

    def test_min_max_step_pass_through(self) -> None:
        html = percent_slider(
            "x", label="X", default=0.5,
            min_value=0.0, max_value=1.0, step=0.05,
        )
        self.assertIn('min="0.0"', html)
        self.assertIn('max="1.0"', html)
        self.assertIn('step="0.05"', html)


class DistributionPreview(unittest.TestCase):

    def test_no_distribution_no_preview(self) -> None:
        html = percent_slider("x", label="X", default=0.5)
        self.assertNotIn("ps-distribution", html)

    def test_distribution_renders_histogram(self) -> None:
        html = percent_slider(
            "x", label="X", default=0.5,
            distribution=[5, 12, 20, 14, 7, 2],
        )
        self.assertIn("ps-distribution", html)
        # One <rect> per bucket.
        self.assertEqual(html.count("<rect"), 6)


class HtmlEscaping(unittest.TestCase):

    def test_label_escaped(self) -> None:
        html = percent_slider(
            "x", label="<script>alert(1)</script>", default=0,
        )
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
