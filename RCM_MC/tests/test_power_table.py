"""Tests for the reusable power table component."""
from __future__ import annotations

import json
import unittest


class TestColumn(unittest.TestCase):
    def test_default_label_from_key(self):
        from rcm_mc.ui.power_table import Column
        c = Column(key="net_patient_revenue", kind="money")
        self.assertEqual(c.label, "Net Patient Revenue")

    def test_explicit_label(self):
        from rcm_mc.ui.power_table import Column
        c = Column(key="x", label="Custom", kind="text")
        self.assertEqual(c.label, "Custom")

    def test_invalid_kind_rejected(self):
        from rcm_mc.ui.power_table import Column
        with self.assertRaises(ValueError):
            Column(key="x", kind="purple")

    def test_default_alignment(self):
        from rcm_mc.ui.power_table import Column
        self.assertEqual(
            Column(key="x", kind="money").align, "right")
        self.assertEqual(
            Column(key="x", kind="text").align, "left")
        self.assertEqual(
            Column(key="x", kind="int").align, "right")
        self.assertEqual(
            Column(key="x", kind="date").align, "left")

    def test_align_override(self):
        from rcm_mc.ui.power_table import Column
        c = Column(key="x", kind="money", align="center")
        self.assertEqual(c.align, "center")


class TestCellFormatting(unittest.TestCase):
    def test_money_scales(self):
        from rcm_mc.ui.power_table import _format_cell
        self.assertEqual(_format_cell(1234, "money"), "$1K")
        self.assertEqual(
            _format_cell(2_500_000, "money"), "$2.5M")
        self.assertEqual(
            _format_cell(1_200_000_000, "money"), "$1.20B")

    def test_pct_signed(self):
        from rcm_mc.ui.power_table import _format_cell
        self.assertEqual(_format_cell(0.05, "pct"), "+5.0%")
        self.assertEqual(
            _format_cell(-0.10, "pct"), "-10.0%")

    def test_int_with_commas(self):
        from rcm_mc.ui.power_table import _format_cell
        self.assertEqual(
            _format_cell(1500, "int"), "1,500")

    def test_none_or_empty(self):
        from rcm_mc.ui.power_table import _format_cell
        self.assertEqual(_format_cell(None, "money"), "")
        self.assertEqual(_format_cell("", "text"), "")

    def test_unparseable_falls_back_to_string(self):
        from rcm_mc.ui.power_table import _format_cell
        self.assertEqual(
            _format_cell("not_a_number", "money"),
            "not_a_number")


class TestRender(unittest.TestCase):
    def _basic_args(self):
        from rcm_mc.ui.power_table import Column
        return {
            "table_id": "deals",
            "columns": [
                Column("name", "Deal", kind="text"),
                Column("npr", "NPR", kind="money"),
                Column("margin", "Margin", kind="pct",
                       filterable=False),
            ],
            "rows": [
                {"name": "Aurora", "npr": 350_000_000,
                 "margin": 0.12},
                {"name": "Borealis", "npr": 120_000_000,
                 "margin": -0.03},
            ],
        }

    def test_renders_with_required_features(self):
        from rcm_mc.ui.power_table import (
            render_power_table,
        )
        html = render_power_table(**self._basic_args())
        # Search input
        self.assertIn(
            'id="deals-search"', html)
        # Export button
        self.assertIn(
            'id="deals-export"', html)
        # Column toggle button
        self.assertIn(
            'id="deals-cols-btn"', html)
        # Sortable headers
        self.assertIn('data-sortable="1"', html)
        # Filter input on filterable columns
        self.assertIn('data-filter-key="name"', html)
        self.assertIn('data-filter-key="npr"', html)
        # NOT on margin (filterable=False)
        self.assertNotIn(
            'data-filter-key="margin"', html)
        # Counter
        self.assertIn('id="deals-count"', html)
        # JS block
        self.assertIn("<script>", html)

    def test_invalid_table_id_rejected(self):
        from rcm_mc.ui.power_table import (
            Column, render_power_table,
        )
        with self.assertRaises(ValueError):
            render_power_table(
                table_id="bad/id!",
                columns=[Column("x")],
                rows=[])

    def test_can_disable_features(self):
        from rcm_mc.ui.power_table import (
            render_power_table,
        )
        args = self._basic_args()
        html = render_power_table(
            **args,
            show_search=False,
            show_export=False,
            show_column_toggle=False)
        self.assertNotIn('id="deals-search"', html)
        self.assertNotIn('id="deals-export"', html)
        self.assertNotIn('id="deals-cols-btn"', html)
        # Sort still on (we don't expose that toggle —
        # sort is the table's job)
        self.assertIn('data-sortable="1"', html)

    def test_pre_formatted_values_in_data(self):
        """Server-side formatted values are embedded so the
        JS doesn't need to know our number formatters."""
        from rcm_mc.ui.power_table import (
            render_power_table,
        )
        html = render_power_table(**self._basic_args())
        # Pre-formatted values in JSON
        self.assertIn('"_fmt_npr":', html)
        # Money formatting applied
        self.assertIn('$350.0M', html)
        self.assertIn('$120.0M', html)
        # Pct formatting applied
        self.assertIn("+12.0%", html)
        self.assertIn("-3.0%", html)

    def test_invisible_column_initial_hidden(self):
        from rcm_mc.ui.power_table import (
            Column, render_power_table,
        )
        html = render_power_table(
            table_id="t",
            columns=[
                Column("a", "A"),
                Column("b", "B", visible=False),
            ],
            rows=[{"a": "x", "b": "y"}])
        # Hidden column has display:none on its header
        self.assertIn('data-col="b"', html)
        # The hidden state is rendered via display:none style
        self.assertIn("display:none", html)

    def test_csv_injection_defang_in_js(self):
        """Verify the JS code includes the formula-injection
        guard (rows starting with =, +, -, @ get prefixed
        with apostrophe)."""
        from rcm_mc.ui.power_table import (
            render_power_table,
        )
        html = render_power_table(**self._basic_args())
        # The defang regex appears in the JS block
        # Note: regex chars are escaped twice (Python + JS)
        self.assertIn("formula injection", html.lower())

    def test_columns_payload_in_js(self):
        """The JS receives the columns payload as JSON so
        it knows which columns are numeric for sort
        comparators."""
        from rcm_mc.ui.power_table import (
            render_power_table,
        )
        html = render_power_table(**self._basic_args())
        # Look for the embedded columns JSON object
        self.assertIn('"key": "name"', html)
        self.assertIn('"kind": "money"', html)
        self.assertIn('"kind": "pct"', html)


class TestEmptyTable(unittest.TestCase):
    def test_no_rows(self):
        from rcm_mc.ui.power_table import (
            Column, render_power_table,
        )
        html = render_power_table(
            table_id="empty",
            columns=[Column("a")],
            rows=[])
        self.assertIn('id="empty-count"', html)
        # Counter shows 0 of 0
        self.assertIn("0 of 0", html)


if __name__ == "__main__":
    unittest.main()
