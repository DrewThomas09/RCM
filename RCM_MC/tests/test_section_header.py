"""tests for ``rcm_mc.ui._ui_kit.section_header``.

PROMPTS.md Phase 2 / Prompt 22. Promotes PE Intelligence's serif-caps
divider to a kit primitive. Tests cover the three alignments and
graceful fallback on an invalid alignment.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import section_header


class AlignmentClass(unittest.TestCase):

    def test_default_is_right(self) -> None:
        html = section_header("SEVEN PARTNER REFLEXES")
        self.assertIn("section-align-right", html)

    def test_each_alignment(self) -> None:
        for align in ("left", "center", "right"):
            with self.subTest(align=align):
                html = section_header("X", align=align)
                self.assertIn(f"section-align-{align}", html)

    def test_invalid_alignment_falls_back_to_right(self) -> None:
        html = section_header("X", align="diagonal")
        self.assertIn("section-align-right", html)
        self.assertNotIn("section-align-diagonal", html)


class LabelHandling(unittest.TestCase):

    def test_label_in_output(self) -> None:
        html = section_header("BRAIN INVENTORIES")
        self.assertIn("BRAIN INVENTORIES", html)

    def test_label_html_escaped(self) -> None:
        html = section_header("<x>")
        self.assertIn("&lt;x&gt;", html)


if __name__ == "__main__":
    unittest.main()
