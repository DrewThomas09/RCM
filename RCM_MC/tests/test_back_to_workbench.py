"""tests for ``back_to_workbench`` (P78)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import back_to_workbench


class LinkRendering(unittest.TestCase):

    def test_renders_with_deal_id(self) -> None:
        html = back_to_workbench("aurora")
        self.assertIn('href="/analysis/aurora"', html)
        self.assertIn("Back to workbench", html)
        self.assertIn("btn-tertiary", html)

    def test_empty_deal_returns_empty(self) -> None:
        self.assertEqual(back_to_workbench(""), "")

    def test_special_chars_escaped(self) -> None:
        html = back_to_workbench('aurora"&hack')
        self.assertNotIn('aurora"&hack', html)


if __name__ == "__main__":
    unittest.main()
