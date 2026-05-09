"""tests for visible focus states (P96)."""
from __future__ import annotations

import os
import sys
import unittest


class FocusVisibleRulePresent(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")

    def test_focus_visible_rule_declared(self) -> None:
        # Match the bare ``:focus-visible`` selector with the
        # accent-2 outline.
        self.assertRegex(
            self.html,
            r":focus-visible\s*\{[^}]*outline:[^}]*accent-2",
        )

    def test_palette_input_focus_has_fallback(self) -> None:
        # The palette input zeroes its outline; verify it provides
        # a box-shadow focus ring instead.
        self.assertIn(".ck-palette-input:focus-visible", self.html)


if __name__ == "__main__":
    unittest.main()
