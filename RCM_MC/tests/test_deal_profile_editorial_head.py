"""Editorial-head + forbidden-trope contract for /diligence/deal/<slug>
(sweep batch 11).

Pins the strict Tier-1 5-block head on the deal-profile drill-in
plus the removal of three spec-forbidden CSS tropes (left-border
accents, oversized border-radius, hover box-shadow).

Pins:
  · ONE <h1> per page (#1036 a11y invariant).
  · Eyebrow + 24×1px green-dash glyph.
  · Mono uppercase meta-line.
  · Italic-first-phrase serif lede.
  · 4-bucket status-dot legend.
  · `.ck-dp-phase-head` and `.ck-dp-life-seg` CSS rule bodies are
    free of `border-left:3px solid` accent.
  · `.ck-dp-life-seg` rule uses `border-radius:2px` (Tier-0 cap).
  · `.ck-dp-life-seg:hover` rule has no `box-shadow`.
  (All trope-removal pins read the rule BODY, not the CSS comment
  that may still mention the removed pattern for traceability.)
"""
from __future__ import annotations

import re
import unittest


class DealProfileEditorialHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.deal_profile_page import render_deal_profile_page
        cls.html = render_deal_profile_page("aurora")

    def test_one_h1_per_page(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block_present(self) -> None:
        self.assertIn('class="dp-head"', self.html)

    def test_eyebrow_with_dash(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*DEAL PROFILE',
        )

    def test_h1_carries_slug_span(self) -> None:
        # The H1 wraps a `data-rcm-deal-display-name` span so the
        # inline JS that swaps the display name to a partner-chosen
        # label still works (the span landmark is preserved through
        # the sweep).
        self.assertIn("data-rcm-deal-display-name", self.html)
        self.assertIn("aurora", self.html)

    def test_meta_line_quotes_slug(self) -> None:
        # Meta-line carries the real slug + the localStorage note.
        self.assertRegex(
            self.html,
            r'class="meta">\s*SLUG <code>aurora</code>',
        )

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>One slug, every analytic.</em>",
            self.html,
        )

    def test_status_dot_legend(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )


class DealProfileForbiddenTropesRemovedTests(unittest.TestCase):
    """Three CSS tropes that the spec forbids — all gone from the
    relevant rule bodies."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.deal_profile_page import render_deal_profile_page
        cls.html = render_deal_profile_page("aurora")

    def test_phase_head_no_left_border_accent(self) -> None:
        m = re.search(r"\.ck-dp-phase-head\{([^}]+)\}", self.html)
        self.assertIsNotNone(m, "phase-head rule not found")
        self.assertNotIn("border-left:3px solid", m.group(1))

    def test_life_seg_no_left_border_accent(self) -> None:
        m = re.search(r"\.ck-dp-life-seg\{([^}]+)\}", self.html)
        self.assertIsNotNone(m, "life-seg rule not found")
        self.assertNotIn("border-left:3px solid", m.group(1))

    def test_life_seg_radius_capped_at_2px(self) -> None:
        # Tier-0: radius is 0 by default, 2px on inputs/buttons,
        # cards are SQUARE. The life-seg used to render at 4px.
        m = re.search(r"\.ck-dp-life-seg\{([^}]+)\}", self.html)
        self.assertIsNotNone(m)
        self.assertIn("border-radius:2px", m.group(1))
        # And explicitly NOT 4px.
        self.assertNotIn("border-radius:4px", m.group(1))

    def test_life_seg_hover_no_box_shadow(self) -> None:
        # Tier-4: no shadows anywhere. Hover depth is by background-
        # tone, not elevation.
        m = re.search(r"\.ck-dp-life-seg:hover\{([^}]+)\}", self.html)
        self.assertIsNotNone(m, "life-seg:hover rule not found")
        self.assertNotIn("box-shadow", m.group(1))


if __name__ == "__main__":
    unittest.main()
