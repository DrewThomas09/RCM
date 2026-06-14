"""Hover-revealed table controls must also reveal on keyboard focus.

The Copy button and the Σ totals toggle sit at opacity:0 and were revealed
only on mouse :hover — so a keyboard user could Tab onto an invisible
control with no focus cue. They must reveal (and ring) on focus too.
"""

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class TableControlFocusTests(unittest.TestCase):
    def setUp(self):
        self.html = chartis_shell("<p>x</p>", "T", active_nav="/research")

    def test_copy_button_reveals_and_rings_on_focus(self):
        self.assertIn(".ck-data-table-scroll:focus-within .ck-tcopy", self.html)
        self.assertIn(".ck-tcopy:focus-visible", self.html)

    def test_totals_toggle_reveals_and_rings_on_focus(self):
        self.assertIn(".ck-data-table-scroll:focus-within .ck-ttotals", self.html)
        self.assertIn(".ck-ttotals:focus-visible", self.html)


if __name__ == "__main__":
    unittest.main()
