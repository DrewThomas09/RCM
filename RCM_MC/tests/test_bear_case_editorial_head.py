"""Editorial-head contract for /bear-cases render paths (sweep batch 15).

The bear-case page has three render paths — rendered report, landing
form, and no-CCD fastpath. All three previously called
ck_section_intro at the head; the shell auto-injected ck_page_title
above each, producing two stacked title blocks.

Sweep batch 15 introduces a local `_bc_head` helper that composes the
strict Tier-1 5-block head once; all three paths now use it.

Pins:
  · ONE <h1> on the landing path (the path testable without report
    fixtures + DB seeding).
  · Eyebrow + 24×1px green-dash glyph on each path.
  · Mono uppercase meta-line.
  · Italic-first-phrase serif lede.
  · 4-bucket status-dot legend.
  · The legacy ck_section_intro is gone from the head of each
    render path (its CSS marker absent from the head zone).
"""
from __future__ import annotations

import re
import unittest


class BearCaseLandingHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.bear_case_page import _landing
        cls.html = _landing()

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="bc-head"', self.html)

    def test_eyebrow_with_dash(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>',
        )
        # Landing-path eyebrow carries the "Bear Case Auto-Generator"
        # label.
        self.assertIn("Bear Case Auto-Generator", self.html)

    def test_meta_line_present(self) -> None:
        self.assertRegex(
            self.html,
            r'class="meta">[^<]*7-SOURCE SYNTHESIS',
        )

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>The counter-narrative every IC memo needs.</em>",
            self.html,
        )

    def test_status_dot_legend(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )

    def test_no_legacy_section_intro_at_head(self) -> None:
        # The shell auto-inject path was triggered by the previous
        # ck_section_intro. With the strict head in place, no
        # ck-section-intro should appear in the head zone (where the
        # bc-head wrapper lives).
        head_zone = self.html[: self.html.find("bc-head") + 8000]
        # The head zone covers up through the page-title block; any
        # ck-section-intro inside that range is a regression.
        # (Other parts of the page may still legitimately use
        # ck_section_intro for in-body sub-section intros.)
        # Strict check: the head block itself shouldn't contain it.
        bc_head_html = re.search(
            r'<header class="bc-head">.*?</header>',
            self.html,
            re.DOTALL,
        )
        self.assertIsNotNone(bc_head_html)
        self.assertNotIn(
            'class="ck-section-intro"',
            bc_head_html.group(0),
        )


class BearCaseHelperCascadeTests(unittest.TestCase):
    """The _bc_head helper renders the same shape for any caller."""

    def test_helper_emits_5_block_shape(self) -> None:
        from rcm_mc.ui.bear_case_page import _bc_head
        html = _bc_head(
            eyebrow="Test eyebrow",
            title="Test title",
            meta="Test meta",
            lede_italic_phrase="Test italic.",
            lede_body="Test body.",
        )
        # All 5 blocks present.
        self.assertIn('class="bc-head"', html)
        self.assertIn('class="eyebrow"', html)
        self.assertIn('class="dash"', html)
        self.assertIn("<h1>Test title</h1>", html)
        self.assertIn('class="meta"', html)
        self.assertIn(">Test meta<", html)
        self.assertIn("<em>Test italic.</em>", html)
        # Body text follows the italic phrase inside the same <p>.
        self.assertIn("Test italic.</em> Test body.</p>", html)
        self.assertIn('class="legend"', html)
        # Single h1.
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)

    def test_helper_html_escapes_inputs(self) -> None:
        # Eyebrow / meta / lede_italic_phrase are html.escape()'d.
        from rcm_mc.ui.bear_case_page import _bc_head
        html = _bc_head(
            eyebrow="<script>",
            title="<safe>",  # title is NOT escaped; callers escape
            meta="A & B",
            lede_italic_phrase="C < D.",
            lede_body="raw",
        )
        # Eyebrow is escaped.
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        # Meta and italic phrase are escaped.
        self.assertIn("A &amp; B", html)
        self.assertIn("C &lt; D.", html)


if __name__ == "__main__":
    unittest.main()
