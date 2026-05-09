"""tests for the standardized page-title typography.

PROMPTS.md Phase 2 / Prompt 21. The kit now emits two equivalent
CSS rules so any page H1 reads as serif-italic without per-page
wiring: ``.page-title`` (explicit class) and ``.ck-main h1``
(default fallback). A ``.bare-title`` opt-out is available for
H1s that should not adopt the page-title look.
"""
from __future__ import annotations

import os
import re
import sys
import unittest


class PageTitleCSSPresent(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")

    def test_page_title_class_defined(self) -> None:
        # Either of the two equivalent rules must exist as a selector.
        self.assertRegex(
            self.html,
            r"\.page-title\s*,\s*\.ck-main\s+h1",
        )

    def test_page_title_uses_serif_italic(self) -> None:
        # Match the rule body (line-broken across multiple lines) and
        # confirm the four critical declarations are present.
        m = re.search(
            r"\.page-title[^{]*\{([^}]+)\}",
            self.html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(m, "page-title rule missing")
        body = m.group(1)
        self.assertIn("font-family:var(--sc-serif)", body)
        self.assertIn("font-style:italic", body)
        self.assertIn("font-weight:500", body)
        self.assertIn("font-size:2.25rem", body)

    def test_bare_title_optout_defined(self) -> None:
        # The opt-out should exist so a modal-body h1 can avoid the
        # kit's page-title look.
        self.assertIn("h1.bare-title", self.html)


if __name__ == "__main__":
    unittest.main()
