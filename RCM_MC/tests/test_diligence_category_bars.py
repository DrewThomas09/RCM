"""Pin for the question-category distribution bars on the diligence page.

The auto-generated diligence questions showed their category mix only as
text chips ("Compliance: 5"). A bar per category makes the distribution
(which diligence areas dominate) scannable; the chips stay beneath.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.diligence_page import render_diligence_questions

_BAR = 'ck-bar-row-fill" style="width:'


class DiligenceCategoryBarsTests(unittest.TestCase):
    def test_one_bar_per_category(self):
        qs = [
            {"category": "Compliance"}, {"category": "Compliance"},
            {"category": "Financial"}, {"category": "Clinical"},
        ]
        html = render_diligence_questions("d1", "Test Deal", qs)
        self.assertEqual(html.count(_BAR), 3)
        self.assertIn("Compliance: 2", html)  # chips retained

    def test_largest_category_full_width(self):
        qs = [{"category": "A"}] * 5 + [{"category": "B"}]
        html = render_diligence_questions("d1", "T", qs)
        self.assertIn("width:100.0%", html)  # A is the max

    def test_empty_questions_no_bars(self):
        html = render_diligence_questions("d1", "T", [])
        self.assertNotIn(_BAR, html)
        self.assertIsInstance(html, str)


if __name__ == "__main__":
    unittest.main()
