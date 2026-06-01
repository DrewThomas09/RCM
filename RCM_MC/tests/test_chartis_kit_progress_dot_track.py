"""Tests for ``ck_progress_dot_track`` — N-of-M discrete progress.

Sibling primitive to ``ck_progress_checklist`` (the multi-row
checklist) and ``ck_data_freshness_pill`` (the freshness signal).
Where checklist is a full-row layout and freshness is a colored
status pill, this is the inline N-of-M visualization: a row of
dots (filled vs empty) + a compact 'N/M' caption that fits in a
table cell.

Use anywhere a partner-facing cell tracks 'how far along': diligence
docs received, IC checklist items, deal-stage progression, tour
walkthroughs done, integration items shipped.

Not wired to a partner-facing page yet. Tests lock the contract
before integration.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_progress_dot_track


class EmptyCasesTests(unittest.TestCase):

    def test_none_completed_returns_empty(self):
        self.assertEqual(ck_progress_dot_track(None, 5), "")

    def test_none_total_returns_empty(self):
        self.assertEqual(ck_progress_dot_track(3, None), "")

    def test_zero_total_returns_empty(self):
        # No track to draw.
        self.assertEqual(ck_progress_dot_track(0, 0), "")

    def test_negative_total_returns_empty(self):
        self.assertEqual(ck_progress_dot_track(0, -3), "")

    def test_non_numeric_returns_empty(self):
        self.assertEqual(ck_progress_dot_track("three", 5), "")
        self.assertEqual(ck_progress_dot_track(3, "five"), "")

    def test_float_non_integer_coercible_returns_empty(self):
        # int() of 'abc' raises → empty.
        self.assertEqual(ck_progress_dot_track("abc", "def"), "")


class ClampingTests(unittest.TestCase):

    def test_completed_above_total_clamps_to_total(self):
        # 7 of 5 → renders as 5/5
        out = ck_progress_dot_track(7, 5)
        self.assertIn(">5/5<", out)

    def test_completed_negative_clamps_to_zero(self):
        out = ck_progress_dot_track(-3, 5)
        self.assertIn(">0/5<", out)

    def test_total_above_50_caps_at_50(self):
        # 100 dots would overflow any cell — cap.
        out = ck_progress_dot_track(50, 100)
        # Caption clamps to 50/50.
        self.assertIn(">50/50<", out)
        # And exactly 50 dot spans render.
        self.assertEqual(out.count("ck-dot-on"), 50)
        self.assertEqual(out.count("ck-dot-off"), 0)

    def test_float_completed_coerced_to_int(self):
        # int(3.7) = 3
        out = ck_progress_dot_track(3.7, 5)
        self.assertIn(">3/5<", out)


class DotRenderTests(unittest.TestCase):

    def test_dots_count_matches_total(self):
        out = ck_progress_dot_track(3, 5)
        self.assertEqual(out.count("ck-dot-on"), 3)
        self.assertEqual(out.count("ck-dot-off"), 2)

    def test_zero_completed_all_empty(self):
        out = ck_progress_dot_track(0, 5)
        self.assertEqual(out.count("ck-dot-on"), 0)
        self.assertEqual(out.count("ck-dot-off"), 5)

    def test_full_completed_all_filled(self):
        out = ck_progress_dot_track(5, 5)
        self.assertEqual(out.count("ck-dot-on"), 5)
        self.assertEqual(out.count("ck-dot-off"), 0)

    def test_default_diameter_and_gap(self):
        out = ck_progress_dot_track(1, 3)
        self.assertIn("width:8px", out)
        self.assertIn("height:8px", out)
        self.assertIn("margin-right:4px", out)

    def test_custom_diameter_and_gap(self):
        out = ck_progress_dot_track(1, 3, diameter=12, gap=6)
        self.assertIn("width:12px", out)
        self.assertIn("height:12px", out)
        self.assertIn("margin-right:6px", out)

    def test_diameter_floor_at_4px(self):
        out = ck_progress_dot_track(1, 3, diameter=1)
        self.assertIn("width:4px", out)


class DirectionToneTests(unittest.TestCase):
    """Filled dot color encodes editorial direction. Empty dots are
    always parchment-gray."""

    def test_positive_default_is_teal(self):
        out = ck_progress_dot_track(3, 5)
        # Default is teal #155752
        self.assertIn("background:#155752", out)

    def test_negative_is_red(self):
        out = ck_progress_dot_track(3, 5, direction="negative")
        self.assertIn("background:#b5321e", out)

    def test_warning_is_amber(self):
        out = ck_progress_dot_track(3, 5, direction="warning")
        self.assertIn("background:#b8732a", out)

    def test_unknown_direction_falls_back_to_positive(self):
        out = ck_progress_dot_track(3, 5, direction="weird")
        self.assertIn("background:#155752", out)

    def test_empty_dots_always_parchment_gray(self):
        out = ck_progress_dot_track(2, 5, direction="negative")
        # 3 empty dots → parchment gray
        self.assertEqual(out.count("background:#d5cdbf"), 3)
        # 2 filled dots → red (negative)
        self.assertEqual(out.count("background:#b5321e"), 2)


class CaptionTests(unittest.TestCase):

    def test_default_shows_caption(self):
        out = ck_progress_dot_track(3, 5)
        self.assertIn(">3/5<", out)
        self.assertIn("ck-progress-caption", out)

    def test_hide_caption(self):
        out = ck_progress_dot_track(3, 5, show_caption=False)
        self.assertNotIn("ck-progress-caption", out)
        # Aria + tooltip still carry the count info.
        self.assertIn("3 of 5", out)

    def test_caption_below_position(self):
        out = ck_progress_dot_track(
            3, 5, caption_position="below",
        )
        self.assertIn("ck-progress-stacked", out)
        self.assertIn("flex-direction:column", out)

    def test_caption_right_position_default(self):
        out = ck_progress_dot_track(3, 5)
        self.assertNotIn("ck-progress-stacked", out)
        self.assertNotIn("flex-direction:column", out)


class AccessibilityTests(unittest.TestCase):

    def test_role_img(self):
        out = ck_progress_dot_track(3, 5)
        self.assertIn('role="img"', out)

    def test_aria_label_carries_plain_text_caption(self):
        out = ck_progress_dot_track(3, 5)
        self.assertIn('aria-label="3 of 5 steps complete (60%)"', out)

    def test_aria_label_uses_singular_label(self):
        out = ck_progress_dot_track(1, 1, label_singular="doc",
                                       label_plural="docs")
        # total == 1 → singular
        self.assertIn("1 of 1 doc complete", out)

    def test_aria_label_uses_plural_label_when_total_gt_1(self):
        out = ck_progress_dot_track(2, 5, label_singular="doc",
                                       label_plural="docs")
        self.assertIn("2 of 5 docs complete", out)

    def test_pct_formatted_in_aria_label(self):
        out = ck_progress_dot_track(2, 7)
        # 2/7 = 28.57% → rounds to 29% in zero-decimal format
        self.assertIn("(29%)", out)

    def test_tooltip_matches_aria_label(self):
        out = ck_progress_dot_track(3, 5)
        self.assertIn('title="3 of 5 steps complete (60%)"', out)

    def test_dots_are_aria_hidden(self):
        # Dots are decorative — aria-label on the wrapper carries the
        # semantic; dots shouldn't double-announce.
        out = ck_progress_dot_track(3, 5)
        self.assertGreater(out.count('aria-hidden="true"'), 0)


class LayoutTests(unittest.TestCase):

    def test_renders_inline_flex(self):
        out = ck_progress_dot_track(3, 5)
        self.assertIn("display:inline-flex", out)

    def test_uses_tabular_nums_in_caption(self):
        out = ck_progress_dot_track(3, 5)
        self.assertIn("tabular-nums", out)

    def test_caption_uses_jetbrains_mono(self):
        out = ck_progress_dot_track(3, 5)
        self.assertIn("JetBrains Mono", out)


class XssTests(unittest.TestCase):

    def test_custom_label_escaped(self):
        out = ck_progress_dot_track(
            1, 1, label_singular='<script>x</script>',
        )
        self.assertNotIn('<script>', out)
        self.assertIn('&lt;script&gt;', out)


if __name__ == "__main__":
    unittest.main()
