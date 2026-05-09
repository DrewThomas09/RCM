"""tests for mobile responsive CSS (P90)."""
from __future__ import annotations

import os
import re
import sys
import unittest


class MobileBreakpointRulesPresent(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")

    def test_768_breakpoint_for_topbar(self) -> None:
        self.assertRegex(
            self.html,
            r"@media\s*\(max-width:768px\)\s*\{[^}]*\.ck-topbar-inner",
        )

    def test_tables_scroll_horizontally(self) -> None:
        self.assertRegex(
            self.html,
            r"@media\s*\(max-width:768px\)[\s\S]*?"
            r"\.data-table-wrap[^{]*\{[^}]*overflow-x:auto",
        )

    def test_preview_panel_hidden_on_mobile(self) -> None:
        # Right-rail preview is desktop-only; mobile drops it.
        self.assertRegex(
            self.html,
            r"@media\s*\(max-width:768px\)[\s\S]*?"
            r"\.preview-panel[^{]*\{[^}]*display:none",
        )


if __name__ == "__main__":
    unittest.main()
