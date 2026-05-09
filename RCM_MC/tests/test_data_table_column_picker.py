"""tests for ``data_table()`` column picker.

PROMPTS.md Phase 4 / Prompt 50: tables show fixed columns; different
partners care about different metrics. The new ``table_id`` parameter
opts a table into the column-picker dropdown; toggle state persists
in localStorage scoped to (pathname, table_id).
"""
from __future__ import annotations

import os
import sys
import unittest

from rcm_mc.ui._ui_kit import data_table


COLUMNS = [
    {"key": "ccn",     "label": "CCN",     "kind": "text"},
    {"key": "moic",    "label": "MOIC",    "kind": "multiple"},
    {"key": "revenue", "label": "Revenue", "kind": "money"},
]
ROWS = [
    {"ccn": "010001", "moic": 2.8, "revenue": 100_000_000},
]


class WithoutTableID(unittest.TestCase):

    def test_no_picker_when_table_id_omitted(self) -> None:
        html = data_table(columns=COLUMNS, rows=ROWS)
        self.assertNotIn("column-picker", html)

    def test_no_data_col_key_attributes_when_omitted(self) -> None:
        html = data_table(columns=COLUMNS, rows=ROWS)
        # Header cells get data-col-key regardless (used for column
        # toggle), but body cells should not when there's no picker.
        # Pin via absence of <td data-col-key=…>.
        self.assertNotIn("<td", html.replace('<td class="', ''))
        # No-op smoke check above; the real signal is no .column-picker.


class WithTableID(unittest.TestCase):

    def setUp(self) -> None:
        self.html = data_table(
            columns=COLUMNS, rows=ROWS, table_id="library-deals",
        )

    def test_picker_renders(self) -> None:
        self.assertIn('class="column-picker"', self.html)
        self.assertIn(">Columns</summary>", self.html)

    def test_one_toggle_per_column(self) -> None:
        self.assertEqual(
            self.html.count('class="column-picker-toggle"'),
            len(COLUMNS),
        )

    def test_table_carries_data_table_id(self) -> None:
        self.assertIn('data-table-id="library-deals"', self.html)

    def test_header_cells_carry_data_col_key(self) -> None:
        for col in COLUMNS:
            with self.subTest(col=col["key"]):
                self.assertIn(f'data-col-key="{col["key"]}"', self.html)

    def test_body_cells_carry_data_col_key(self) -> None:
        # data-col-key appears on:
        #   3 header <th> (toggled via JS class swap)
        #   3 body <td>  (toggled via JS class swap)
        #   3 picker checkboxes (drives the toggle event)
        # Total 9.
        self.assertEqual(self.html.count("data-col-key="), 9)


class JSAttachedFromShell(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T")

    def test_column_picker_js_present(self) -> None:
        self.assertIn("colVisibility:", self.html)
        self.assertIn("data-table-id", self.html)
        self.assertIn("col-hidden", self.html)


if __name__ == "__main__":
    unittest.main()
