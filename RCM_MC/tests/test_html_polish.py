"""Tests for the numeric-alignment HTML polish (UI-1)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._html_polish import (
    _is_numeric_cell,
    polish_tables_in_html,
)


class TestIsNumericCell(unittest.TestCase):
    def test_plain_integer(self):
        self.assertTrue(_is_numeric_cell("1234"))

    def test_formatted_money(self):
        self.assertTrue(_is_numeric_cell("$1,234.56"))
        self.assertTrue(_is_numeric_cell("$5.4B"))
        self.assertTrue(_is_numeric_cell("-$4.5M"))
        self.assertTrue(_is_numeric_cell("$20K"))

    def test_percent(self):
        self.assertTrue(_is_numeric_cell("+12.3%"))
        self.assertTrue(_is_numeric_cell("-4.5 pts"))
        self.assertTrue(_is_numeric_cell("20.6%"))

    def test_multiple_suffix(self):
        self.assertTrue(_is_numeric_cell("5.4x"))
        self.assertTrue(_is_numeric_cell("2.55x"))

    def test_accounting_negative_parens(self):
        self.assertTrue(_is_numeric_cell("(1,234)"))
        self.assertTrue(_is_numeric_cell("($1.5M)"))

    def test_nested_strong_tag_stripped(self):
        self.assertTrue(_is_numeric_cell("<strong>$50M</strong>"))

    def test_dash_placeholder_is_numeric(self):
        self.assertTrue(_is_numeric_cell("—"))

    def test_empty_is_not_numeric(self):
        self.assertFalse(_is_numeric_cell(""))
        self.assertFalse(_is_numeric_cell("   "))

    def test_text_is_not_numeric(self):
        self.assertFalse(_is_numeric_cell("Cleveland Clinic"))
        self.assertFalse(_is_numeric_cell("Medicare"))
        self.assertFalse(_is_numeric_cell("on_track"))

    def test_form_controls_veto(self):
        """Cells with inputs must not be marked numeric even if text is a number."""
        self.assertFalse(_is_numeric_cell('<input value="123"/>'))
        self.assertFalse(_is_numeric_cell('123<select><option>a</option></select>'))

    def test_nested_table_veto(self):
        self.assertFalse(_is_numeric_cell("<table><tr><td>1</td></tr></table>"))


class TestPolishTables(unittest.TestCase):
    def test_adds_num_class_to_numeric_cells(self):
        html = '<table><tr><td>Medicare</td><td>$1.5M</td></tr></table>'
        out = polish_tables_in_html(html)
        self.assertIn('<td class="num">$1.5M</td>', out)
        # Non-numeric cell left alone
        self.assertIn('<td>Medicare</td>', out)

    def test_preserves_existing_attributes(self):
        html = '<table><tr><td style="color:red">$100K</td></tr></table>'
        out = polish_tables_in_html(html)
        self.assertIn('style="color:red"', out)
        self.assertIn('class="num"', out)

    def test_merges_with_existing_class(self):
        html = '<table><tr><td class="big">$100K</td></tr></table>'
        out = polish_tables_in_html(html)
        self.assertIn('class="big num"', out)

    def test_idempotent(self):
        """Running twice must produce the same output — safe to re-apply."""
        html = '<table><tr><td>Medicare</td><td>$1.5M</td></tr></table>'
        once = polish_tables_in_html(html)
        twice = polish_tables_in_html(once)
        self.assertEqual(once, twice)

    def test_already_tagged_cell_untouched(self):
        html = '<table><tr><td class="num">$1.5M</td></tr></table>'
        out = polish_tables_in_html(html)
        # Same text; no double-class
        self.assertEqual(html, out)

    def test_multiple_tables_in_document(self):
        html = """
        <table><tr><td>A</td><td>1</td></tr></table>
        <p>Between tables.</p>
        <table><tr><td>B</td><td>$2M</td></tr></table>
        """
        out = polish_tables_in_html(html)
        # Both numeric cells tagged
        self.assertEqual(out.count('class="num"'), 2)

    def test_nested_strong_gets_polished(self):
        html = '<table><tr><td><strong>$50M</strong></td></tr></table>'
        out = polish_tables_in_html(html)
        self.assertIn('class="num"', out)
        # Strong tag preserved inside
        self.assertIn('<strong>$50M</strong>', out)

    def test_non_table_td_not_matched(self):
        """Cells outside a <table> must not be affected (defensive)."""
        html = '<p>Some <td>orphan</td> text.</p>'
        out = polish_tables_in_html(html)
        self.assertEqual(html, out)

    def test_header_cells_not_affected(self):
        """<th> cells are layout/label; only <td> gets the num class."""
        html = '<table><tr><th>$100M</th><td>$200M</td></tr></table>'
        out = polish_tables_in_html(html)
        self.assertIn('<th>$100M</th>', out)
        self.assertIn('<td class="num">$200M</td>', out)
