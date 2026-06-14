"""Accessibility of the client-side table row-filter (_TABLE_FILTER_JS).

The filter input must be labelled, and the live match count must be an
aria-live region so a screen-reader user hears "5 of 20" as they type
rather than filtering blind.
"""

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class TableFilterA11yTests(unittest.TestCase):
    def setUp(self):
        self.html = chartis_shell("<p>x</p>", "T", active_nav="/research")

    def test_filter_input_is_labelled(self):
        self.assertIn("setAttribute('aria-label','Filter table rows')", self.html)

    def test_match_count_is_a_live_region(self):
        self.assertIn("count.setAttribute('aria-live','polite')", self.html)


if __name__ == "__main__":
    unittest.main()
