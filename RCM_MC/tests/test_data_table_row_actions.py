"""tests for ``data_table()`` row-action menus.

PROMPTS.md Phase 3 / Prompt 42: Predictive Screener has a "+ PIPE"
button on every row, always visible. Hospital Screener has
"PROFILE / DILIGENCE" buttons. Always-visible row actions clutter
dense tables. The new ``actions`` parameter renders a hidden ``…``
toggle that reveals the action menu on hover.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import data_table


COLUMNS = [
    {"key": "ccn", "label": "CCN", "kind": "text"},
    {"key": "moic", "label": "MOIC", "kind": "multiple"},
]


ROWS = [
    {"ccn": "010001", "moic": 2.8},
    {"ccn": "020003", "moic": 1.95},
]


class WithoutActions(unittest.TestCase):

    def test_no_extra_column_when_actions_omitted(self) -> None:
        html = data_table(columns=COLUMNS, rows=ROWS)
        self.assertNotIn("row-actions", html)

    def test_no_actions_header_cell(self) -> None:
        html = data_table(columns=COLUMNS, rows=ROWS)
        self.assertNotIn('data-key="__actions"', html)


class WithActions(unittest.TestCase):

    def setUp(self) -> None:
        self.actions = [
            {"label": "Profile",   "href_template": "/profile/{ccn}"},
            {"label": "Diligence", "href_template": "/diligence/checklist?deal_id={ccn}"},
        ]
        self.html = data_table(
            columns=COLUMNS, rows=ROWS, actions=self.actions,
        )

    def test_actions_header_present(self) -> None:
        self.assertIn('data-key="__actions"', self.html)

    def test_one_actions_cell_per_row(self) -> None:
        self.assertEqual(
            self.html.count("row-actions-cell"),
            len(ROWS),
        )

    def test_each_row_has_toggle_and_menu(self) -> None:
        # Two action links per row × two rows = 4 row-action-link tags.
        self.assertEqual(self.html.count("row-action-link"), 4)
        self.assertIn("row-actions-toggle", self.html)
        self.assertIn("row-actions-menu", self.html)

    def test_href_template_substituted_per_row(self) -> None:
        # Both rows' CCNs must appear in expanded hrefs.
        self.assertIn('href="/profile/010001"', self.html)
        self.assertIn('href="/profile/020003"', self.html)
        self.assertIn(
            'href="/diligence/checklist?deal_id=010001"',
            self.html,
        )

    def test_unknown_template_key_renders_template_literal(self) -> None:
        html = data_table(
            columns=COLUMNS, rows=ROWS,
            actions=[{"label": "X",
                      "href_template": "/x/{nonexistent_key}"}],
        )
        # Falls back to the template string verbatim — never crashes.
        self.assertIn("/x/{nonexistent_key}", html)


if __name__ == "__main__":
    unittest.main()
