"""Test the ck_data_table helper added in cycle 27.

Wraps an editorial data table — scroll wrapper, table container,
thead row with class-based chrome, body — replacing the ~5 inline-
styled wrappers per table that ~120 data_public pages hand-roll.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_data_table


class CkDataTableTests(unittest.TestCase):
    def test_minimal_render_emits_chrome(self):
        html = ck_data_table(
            headers=[{"label": "Deal"}, {"label": "MOIC"}],
            rows_html="<tr><td>x</td><td>1.5x</td></tr>",
        )
        self.assertIn('class="ck-data-table-scroll"', html)
        self.assertIn('class="ck-data-table"', html)
        self.assertIn("<thead>", html)
        self.assertIn("<tbody>", html)
        self.assertIn(">Deal</th>", html)
        self.assertIn(">MOIC</th>", html)

    def test_header_alignment_classes(self):
        html = ck_data_table(
            headers=[
                {"label": "L", "align": "left"},
                {"label": "R", "align": "right"},
                {"label": "C", "align": "center"},
            ],
            rows_html="",
        )
        # Right alignment → ck-cell-r class on th
        self.assertIn("ck-cell-r", html)
        self.assertIn("ck-cell-c", html)
        # Default left has no alignment class
        # (we just look for the L header without extra align modifier)
        self.assertIn(">L</th>", html)

    def test_scrollable_wrap_default(self):
        html = ck_data_table(
            headers=[{"label": "X"}],
            rows_html="",
        )
        self.assertTrue(html.startswith('<div class="ck-data-table-scroll">'))

    def test_scrollable_off_omits_wrap(self):
        html = ck_data_table(
            headers=[{"label": "X"}],
            rows_html="",
            scrollable=False,
        )
        self.assertNotIn("ck-data-table-scroll", html)
        self.assertTrue(html.startswith('<table'))

    def test_header_label_html_escape(self):
        html = ck_data_table(
            headers=[{"label": "<script>x</script>"}],
            rows_html="",
        )
        self.assertNotIn("<script>x</script>", html)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", html)

    def test_body_rows_pass_through_verbatim(self):
        # Helper does NOT escape the rows — caller is responsible
        # (typically rows are already-escaped ck_data_cell output).
        custom_rows = '<tr class="x"><td>a</td><td>b</td></tr>'
        html = ck_data_table(
            headers=[{"label": "L"}, {"label": "R"}],
            rows_html=custom_rows,
        )
        self.assertIn(custom_rows, html)


if __name__ == "__main__":
    unittest.main()
