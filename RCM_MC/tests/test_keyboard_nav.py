"""tests for vim-style keyboard navigation (P89)."""
from __future__ import annotations

import os
import sys
import unittest


class KeyboardNavJSPresent(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")

    def test_g_prefix_targets_present(self) -> None:
        # All six g-prefixed targets reachable via JS.
        for target in (
            "/diligence", "/pipeline", "/library",
            "/research", "/home", "/portfolio",
        ):
            with self.subTest(target=target):
                self.assertIn(f"'{target}'", self.html)

    def test_bracket_keys_step_tabs(self) -> None:
        self.assertIn("'['", self.html)
        self.assertIn("']'", self.html)
        self.assertIn("stepSecondaryTab", self.html)

    def test_question_opens_help(self) -> None:
        self.assertIn("'?'", self.html)
        self.assertIn("kbd-help", self.html)

    def test_slash_focuses_search(self) -> None:
        self.assertIn("'/'", self.html)
        self.assertIn("input[type=search]", self.html)

    def test_escape_dismisses_modals(self) -> None:
        self.assertIn("'Escape'", self.html)

    def test_help_overlay_default_hidden(self) -> None:
        self.assertIn('id="kbd-help"', self.html)
        self.assertIn('id="kbd-help" hidden', self.html)


if __name__ == "__main__":
    unittest.main()
