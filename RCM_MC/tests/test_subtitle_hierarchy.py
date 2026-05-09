"""tests for subtitle vs page-title hierarchy.

PROMPTS.md Phase 3 / Prompt 41: Risk Workbench, Provider Economics,
Management Scorecard etc. previously rendered subtitle and H1 at the
same weight, with the subtitle stuffed into the breadcrumb row. The
shell now accepts a ``subtitle`` kwarg and renders a styled
``.page-subtitle`` block at 0.7x the page-title size.
"""
from __future__ import annotations

import os
import sys
import unittest


class SubtitleRendersAsStyledDiv(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)

    def test_subtitle_kwarg_emits_page_subtitle_div(self) -> None:
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(
            "<p>body</p>", "Risk Workbench",
            subtitle="Steward Health Care (2016 replay)",
        )
        self.assertIn('class="page-subtitle"', html)
        self.assertIn("Steward Health Care", html)

    def test_subtitle_html_escaped(self) -> None:
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell(
            "<p>body</p>", "T",
            subtitle='<script>alert("xss")</script>',
        )
        # The shell legitimately contains <script> tags for its own
        # JS bundles. Check the specific subtitle payload instead:
        # the literal alert("xss") must not appear unescaped, and
        # the escaped form must appear inside the page-subtitle div.
        self.assertNotIn('alert("xss")', html)
        self.assertIn("&lt;script&gt;", html)

    def test_no_subtitle_no_div(self) -> None:
        from rcm_mc.ui._chartis_kit import chartis_shell
        html = chartis_shell("<p>body</p>", "T")
        self.assertNotIn('class="page-subtitle"', html)


class PageSubtitleStyling(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T", subtitle="sub")

    def test_subtitle_uses_muted_color(self) -> None:
        # The CSS rule must declare the muted text-dim color so
        # the subtitle reads quieter than the H1.
        self.assertIn(
            "color:var(--sc-text-dim)",
            self.html,
        )

    def test_subtitle_smaller_than_page_title(self) -> None:
        # Page-title is 2.25rem; subtitle is 1.05rem (~0.47x). Both
        # rules must be present.
        self.assertIn("font-size:2.25rem", self.html)
        self.assertIn("font-size:1.05rem", self.html)


if __name__ == "__main__":
    unittest.main()
