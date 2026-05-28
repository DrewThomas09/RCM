"""Editorial-head cascade for render_section_best (sweep batch 8).

The ranked /best/<section> landing page powers seven routes:
  /best/source · /best/pipeline · /best/library · /best/research
  /best/portfolio · /best/diligence · /best/home

The shared renderer falls back to this page whenever `_SECTIONS` in
section_landings doesn't have a curated pillar list for a section.

Pins:
  · Strict Tier-1 5-block head replaces the legacy ck_page_title +
    ck_source_purpose 2-block stack.
  · ONE <h1> per page (#1036 a11y invariant).
  · Eyebrow + 24×1px green-dash glyph.
  · Mono uppercase meta-line with REAL counts + per-tier coverage.
  · Italic-first-phrase serif lede.
  · 4-bucket status-dot legend in the head block.
  · Spec-forbidden tropes REMOVED from .sb-card rules:
      · `border-left:3px solid var(--sc-teal)` (Tier-4 don'ts —
        no left-border-accent cards). Verified by reading the
        actual CSS rule body, not the explanatory comment text.
      · `box-shadow:var(--sc-shadow-2...)` on hover (Tier-4 don'ts
        — no shadows; depth by paper-tone).
"""
from __future__ import annotations

import re
import unittest


_SECTIONS = (
    "source", "pipeline", "library", "research",
    "portfolio", "diligence",
)


def _render(section: str) -> str:
    # Module-level wrapper so the test classes don't accidentally
    # bind ``render_section_best`` as a method (which would then
    # receive ``self`` as the ``section`` arg).
    from rcm_mc.ui.section_best_page import render_section_best
    return render_section_best(section)


class SectionBestCascadeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._rs = staticmethod(_render)

    def test_all_routes_single_h1(self) -> None:
        for sec in _SECTIONS:
            with self.subTest(section=sec):
                html = self._rs(sec)
                self.assertEqual(
                    len(re.findall(r"<h1[ >]", html)), 1,
                    f"/best/{sec}: expected exactly one <h1>",
                )

    def test_all_routes_head_block(self) -> None:
        for sec in _SECTIONS:
            with self.subTest(section=sec):
                html = self._rs(sec)
                self.assertIn('class="sb-head"', html)

    def test_all_routes_eyebrow_with_dash(self) -> None:
        for sec in _SECTIONS:
            with self.subTest(section=sec):
                html = self._rs(sec)
                self.assertRegex(
                    html,
                    r'<div class="eyebrow"><span class="dash"></span>',
                )

    def test_all_routes_status_dot_legend(self) -> None:
        for sec in _SECTIONS:
            with self.subTest(section=sec):
                html = self._rs(sec)
                for cls_name in ("live", "computed", "needs", "illustrative"):
                    self.assertRegex(
                        html,
                        rf'<span class="dot {cls_name}"></span>',
                    )

    def test_all_routes_lede_italic_first_phrase(self) -> None:
        for sec in _SECTIONS:
            with self.subTest(section=sec):
                html = self._rs(sec)
                # First lede paragraph carries <em>...</em>.
                m = re.search(r'<p class="lede">(.*?)</p>', html)
                self.assertIsNotNone(m, f"/best/{sec}: missing lede")
                self.assertIn("<em>", m.group(1))

    def test_meta_line_quotes_real_tool_count(self) -> None:
        # Either "N TOOLS · K LIVE · ..." or "NO TOOLS YET" honestly.
        for sec in _SECTIONS:
            with self.subTest(section=sec):
                html = self._rs(sec)
                self.assertRegex(
                    html,
                    r'class="meta">(\s*\d+\s+TOOLS?|NO TOOLS YET)',
                )

    def test_no_left_border_accent_on_sb_card(self) -> None:
        # The spec-forbidden left-border accent must be gone from
        # the actual .sb-card rule body (the explanatory comment in
        # the CSS still mentions it for traceability — we read the
        # rule, not the comment).
        for sec in _SECTIONS:
            with self.subTest(section=sec):
                html = self._rs(sec)
                # Match the .sb-card rule that immediately follows
                # the @media line (the main rule, not :hover or
                # :focus-visible).
                m = re.search(r"\.sb-card\{([^}]+)\}", html)
                self.assertIsNotNone(m)
                self.assertNotIn(
                    "border-left:3px solid var(--sc-teal)",
                    m.group(1),
                    f"/best/{sec}: .sb-card still carries forbidden "
                    "left-border accent",
                )

    def test_no_shadow_on_sb_card_hover(self) -> None:
        # Tier-4 don'ts: no shadows anywhere. Hover effect must use
        # background-fill only.
        for sec in _SECTIONS:
            with self.subTest(section=sec):
                html = self._rs(sec)
                m = re.search(r"\.sb-card:hover\{([^}]+)\}", html)
                self.assertIsNotNone(m)
                self.assertNotIn("box-shadow", m.group(1))


if __name__ == "__main__":
    unittest.main()
