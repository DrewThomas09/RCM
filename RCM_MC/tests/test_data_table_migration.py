"""tests for the canary data_table migration.

PROMPTS.md Phase 3 / Prompt 28: migrate every table to data_table().
The CMS-sources page's static "Key Functions" reference table is the
canary — pure scalar text, no per-row coloring, an ideal data_table
fit. Subsequent rich tables (Hospital Screener, Predictive Screener,
Library deal table, etc.) carry custom inline rendering and will
migrate piecewise in follow-up sweeps.
"""
from __future__ import annotations

import unittest


class CMSKeyFunctionsTableMigrated(unittest.TestCase):

    def setUp(self) -> None:
        from rcm_mc.ui.data_public.cms_sources_page import _key_functions_table
        self.html = _key_functions_table()

    def test_uses_data_table_class(self) -> None:
        self.assertIn('class="data-table', self.html)

    def test_six_function_rows_present(self) -> None:
        # Six rows in the body — one per function.
        self.assertEqual(self.html.count("<tr>"), 1 + 6)
        # 1 thead row + 6 tbody rows.

    def test_function_names_pass_through(self) -> None:
        # Spot-check three of the six functions by name.
        for fn in (
            "fetch_pages",
            "fetch_provider_utilization",
            "winsorize_column",
        ):
            with self.subTest(fn=fn):
                self.assertIn(fn, self.html)

    def test_static_reference_not_sortable(self) -> None:
        # A static reference table doesn't need column sort. Verify
        # the migration opted out so headers don't carry the click
        # affordance.
        self.assertNotIn("data-sortable", self.html)

    def test_kit_styling_applied_via_class(self) -> None:
        # Striped + hover rules apply because data_table defaults
        # turn them on. Pin that the migration kept defaults.
        self.assertIn("striped", self.html)
        self.assertIn("hover", self.html)


if __name__ == "__main__":
    unittest.main()
