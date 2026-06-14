"""Accessibility of the client-side table-sort enhancer (_SORT_JS).

A sortable column must announce its sort state to assistive tech via
aria-sort, which is only honored on a columnheader — so the enhancer must
NOT override the <th> role to "button" (the prior behavior silently
discarded the announcement), and must keep aria-sort in sync as the user
sorts.
"""

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class TableSortA11yTests(unittest.TestCase):
    def setUp(self):
        self.html = chartis_shell("<p>x</p>", "T", active_nav="/research")

    def test_enhancer_keeps_native_columnheader_role(self):
        # Overriding to role=button would strip the columnheader semantics
        # aria-sort attaches to.
        self.assertNotIn("setAttribute('role','button')", self.html)

    def test_enhancer_initialises_aria_sort_none(self):
        self.assertIn("setAttribute('aria-sort','none')", self.html)

    def test_enhancer_sets_directional_aria_sort_on_sort(self):
        self.assertIn(
            "setAttribute('aria-sort',dir==='asc'?'ascending':'descending')",
            self.html,
        )

    def test_headers_stay_keyboard_operable(self):
        # tabindex + Enter/Space keydown keep the columnheader operable.
        self.assertIn("setAttribute('tabindex','0')", self.html)
        self.assertIn("e.key==='Enter'||e.key===' '", self.html)


if __name__ == "__main__":
    unittest.main()
