"""Bear-case page visuals — the diligence-page upgrade wave.

The severity matrix renders the bear case at a glance BEFORE the
evidence cards: a severity-stacked bar (CRITICAL→LOW, semantic tones)
plus a theme × severity dot matrix.
"""
from __future__ import annotations

import unittest


class SeverityMatrixTests(unittest.TestCase):
    def test_matrix_renders_with_evidence(self):
        from rcm_mc.ui.bear_case_page import render_bear_case_page
        h = render_bear_case_page({
            "deal_name": ["Meadowbrook"], "specialty": ["hospital"],
            "revenue_year0_usd": ["450000000"],
            "ebitda_year0_usd": ["60000000"],
            "medicare_share": ["0.45"],
            "hopd_revenue_annual_usd": ["30000000"]})
        self.assertIn("Evidence severity mix", h)
        self.assertIn("reads worst-first below", h)

    def test_empty_report_no_matrix(self):
        from rcm_mc.diligence.bear_case import generate_bear_case
        from rcm_mc.ui.bear_case_page import _severity_matrix_svg
        empty = generate_bear_case(target_name="X")
        self.assertEqual(_severity_matrix_svg(empty), "")


if __name__ == "__main__":
    unittest.main()
