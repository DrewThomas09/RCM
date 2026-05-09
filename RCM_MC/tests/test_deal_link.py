"""tests for ``deal_link`` (P76)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import deal_link


class CanonicalShape(unittest.TestCase):

    def test_default_targets_workbench(self) -> None:
        self.assertEqual(deal_link("aurora"), "/analysis/aurora")

    def test_with_tab_appended_as_query(self) -> None:
        self.assertEqual(
            deal_link("aurora", tab="ebitda-bridge"),
            "/analysis/aurora?tab=ebitda-bridge",
        )

    def test_empty_deal_returns_dead_anchor(self) -> None:
        # Return "#" rather than an obviously-broken /analysis/ URL
        # so a list with a missing deal_id still renders.
        self.assertEqual(deal_link(""), "#")


class HtmlEscaping(unittest.TestCase):

    def test_special_chars_escaped(self) -> None:
        # Deal IDs can contain user-controlled text.
        out = deal_link('a"&b')
        self.assertNotIn('a"&b', out)


if __name__ == "__main__":
    unittest.main()
