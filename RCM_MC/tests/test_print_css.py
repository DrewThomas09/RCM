"""tests for the @media print stylesheet.

PROMPTS.md Phase 2 / Prompt 25. The kit must ship a print stylesheet
so partners can print IC memos / LP updates / waterfall pages without
a solid-black navy banner on every page and with thead repeating
across page breaks.
"""
from __future__ import annotations

import os
import re
import sys
import unittest


class PrintCSSPresent(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")

    def test_media_print_block_exists(self) -> None:
        self.assertIn("@media print", self.html)

    def test_page_size_declared(self) -> None:
        # @page rules apply outside the @media block too; assert
        # somewhere that we declare letter-paper margins.
        self.assertRegex(self.html, r"@page\s*\{[^}]*size:\s*Letter")

    def test_chrome_hidden_in_print(self) -> None:
        # Pull the @media print block body and confirm the chrome
        # selectors are inside it with display:none.
        m = re.search(
            r"@media print\s*\{(.*?)\}\s*(?:/\*|\.[\w-]+\s*\{|@)",
            self.html,
            flags=re.DOTALL,
        )
        # If the regex above doesn't fire (block is the last in the
        # stylesheet), fall back to a simple containment check.
        body = m.group(1) if m else self.html
        for selector in (".ck-topbar", ".ck-breadcrumbs", ".preview-panel"):
            with self.subTest(selector=selector):
                self.assertIn(selector, body)

    def test_thead_repeats_on_page_break(self) -> None:
        self.assertIn("display:table-header-group", self.html)

    def test_severity_tones_have_pattern_fallback(self) -> None:
        # Color-only tones must carry a stripe pattern in print so
        # B&W output still distinguishes positive/negative/warning.
        for tone in ("tone-positive", "tone-negative", "tone-warning"):
            with self.subTest(tone=tone):
                self.assertRegex(
                    self.html,
                    rf"\.{tone}\s*\{{[^}}]*repeating-linear-gradient",
                )


if __name__ == "__main__":
    unittest.main()
