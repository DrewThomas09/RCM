"""tests for the marketing-page engine bento grid (P99)."""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis.marketing_page import render_marketing_page


class BentoGridRenders(unittest.TestCase):

    def setUp(self) -> None:
        self.html = render_marketing_page()

    def test_section_eyebrow_present(self) -> None:
        self.assertIn("The four engines", self.html)

    def test_all_four_engine_cards_render(self) -> None:
        # Each engine's card renders its label.
        for label in (
            "Monte Carlo", "PE-math",
            "Health &amp; completeness", "AI memos",
        ):
            with self.subTest(label=label):
                self.assertIn(label, self.html)

    def test_grid_uses_two_column_layout(self) -> None:
        # The bento section sets a 2-column grid for desktop.
        self.assertIn("grid-template-columns:1fr 1fr", self.html)


if __name__ == "__main__":
    unittest.main()
