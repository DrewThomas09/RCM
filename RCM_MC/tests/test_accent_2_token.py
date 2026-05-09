"""tests for the --accent-2 (clinical teal) token.

PROMPTS.md Phase 2 / Prompt 23. The kit must declare a third palette
accent so callers can reference clinical-teal explicitly rather than
guessing at hex values.
"""
from __future__ import annotations

import os
import sys
import unittest


class Accent2InCSS(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")

    def test_accent_2_token_declared(self) -> None:
        self.assertIn("--accent-2", self.html)

    def test_accent_2_ink_token_declared(self) -> None:
        self.assertIn("--accent-2-ink", self.html)


class Accent2InPalette(unittest.TestCase):

    def setUp(self) -> None:
        # The ``accent_2`` palette key only exists on the v2 path —
        # legacy uses a different palette schema. Force the v2 path
        # then re-import the dispatcher.
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)

    def test_palette_exposes_accent_2_key(self) -> None:
        from rcm_mc.ui._chartis_kit import P
        self.assertIn("accent_2", P)
        self.assertEqual(P["accent_2"], "#2fb3ad")

    def test_palette_exposes_accent_2_ink_key(self) -> None:
        from rcm_mc.ui._chartis_kit import P
        self.assertIn("accent_2_ink", P)


if __name__ == "__main__":
    unittest.main()
