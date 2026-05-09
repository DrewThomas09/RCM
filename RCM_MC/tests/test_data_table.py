"""tests for ``rcm_mc.ui._ui_kit.data_table``.

PROMPTS.md Phase 2 / Prompt 15: standardised table primitive used by
every dense list across the platform. Tests cover:

* numeric columns are right-aligned and tabular-nums
* sortable headers carry the click hook (the actual sort runs in
  the browser via the kit JS — pinned separately)
* sticky-header / striped / hover toggles emit the right classes
* every cell value passes through ``format_value`` (so missing data
  reads as "not yet computed", not ``—``)
* the kit-shipped JS sort handler is reachable from a shell render
"""
from __future__ import annotations

import os
import sys
import unittest

from rcm_mc.ui._ui_kit import data_table


def _cols() -> list[dict]:
    return [
        {"key": "name",   "label": "Deal",      "kind": "text"},
        {"key": "moic",   "label": "MOIC",      "kind": "multiple"},
        {"key": "revenue", "label": "Revenue",  "kind": "money"},
        {"key": "denial", "label": "Denial",    "kind": "percent"},
        {"key": "n",      "label": "N",          "kind": "count"},
    ]


def _rows() -> list[dict]:
    return [
        {"name": "Aurora", "moic": 2.8, "revenue": 450_250_000,
         "denial": 0.092, "n": 6024},
        {"name": "Meadowbrook", "moic": 1.95, "revenue": None,
         "denial": 0.121, "n": 1},
    ]


class StructureAndAlignment(unittest.TestCase):

    def setUp(self) -> None:
        self.html = data_table(columns=_cols(), rows=_rows())

    def test_numeric_columns_right_aligned(self) -> None:
        # MOIC, Revenue, Denial, N — all numeric → align-right.
        # Pull the header row to count alignments.
        # 1 left ("Deal") + 4 right.
        self.assertEqual(self.html.count('class="align-right'), 4 + 4 * 2)
        # 1 header + 2*4 body cells = 9 right-aligned cells.

    def test_text_column_left_aligned(self) -> None:
        self.assertIn('class="align-left', self.html)

    def test_numeric_cells_carry_sc_num_class(self) -> None:
        # 4 numeric cols × 2 rows = 8 sc-num cells.
        self.assertEqual(self.html.count("sc-num"), 8)

    def test_format_value_used_for_missing(self) -> None:
        # Meadowbrook's revenue is None → renders as the missing span.
        self.assertIn('class="muted unpopulated"', self.html)
        self.assertIn("not yet computed", self.html)

    def test_format_value_used_for_money(self) -> None:
        # Aurora revenue 450_250_000 → "$450.25M".
        self.assertIn("$450.25M", self.html)

    def test_format_value_used_for_percent(self) -> None:
        self.assertIn("9.2%", self.html)


class SortableAffordance(unittest.TestCase):

    def test_data_sortable_attribute_present(self) -> None:
        html = data_table(columns=_cols(), rows=_rows())
        self.assertIn('data-sortable="true"', html)

    def test_sortable_header_class_per_column(self) -> None:
        html = data_table(columns=_cols(), rows=_rows())
        self.assertEqual(html.count("th class=\"align-"), 5)
        # All five columns are sortable by default.
        self.assertEqual(html.count("sortable"), 6)  # 5 column heads + 1 attribute

    def test_per_column_sort_optout(self) -> None:
        cols = _cols()
        cols[0]["sortable"] = False  # Deal column not sortable
        html = data_table(columns=cols, rows=_rows())
        # The Deal column header must carry data-key="name" without
        # the "sortable" class — match the literal opening of that
        # specific <th>.
        self.assertIn(
            'data-key="name"',
            html,
        )
        # Find the th for "name" and verify it has no sortable class.
        idx = html.find('data-key="name"')
        # Walk back to the opening <th .
        start = html.rfind("<th ", 0, idx)
        end = html.find(">", start)
        th_tag = html[start:end]
        self.assertNotIn("sortable", th_tag)

    def test_sortable_off_drops_attribute(self) -> None:
        html = data_table(columns=_cols(), rows=_rows(), sortable=False)
        self.assertNotIn("data-sortable", html)


class BehaviourFlags(unittest.TestCase):

    def test_default_flags_emit_classes(self) -> None:
        html = data_table(columns=_cols(), rows=_rows())
        for cls in ("sticky-header", "striped", "hover"):
            with self.subTest(cls=cls):
                self.assertIn(cls, html)
        self.assertNotIn(' dense"', html)

    def test_dense_flag(self) -> None:
        html = data_table(columns=_cols(), rows=_rows(), dense=True)
        self.assertIn("dense", html)

    def test_each_flag_can_be_disabled(self) -> None:
        html = data_table(
            columns=_cols(), rows=_rows(),
            sticky_header=False, striped=False, hover=False,
        )
        self.assertNotIn("sticky-header", html)
        self.assertNotIn("striped", html)
        self.assertNotIn("hover", html)


class JSAttachedFromShell(unittest.TestCase):
    """The kit-shipped data-table JS must reach every page via the
    shell — no per-page wiring required."""

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T")

    def test_data_table_js_binds_on_dom_content_loaded(self) -> None:
        self.assertIn("data-sortable", self.html)
        self.assertIn("DOMContentLoaded", self.html)
        self.assertIn("table.data-table", self.html)


if __name__ == "__main__":
    unittest.main()
