"""Tests for ``ck_signal_chip`` — compact tone-colored pill.

Smaller, denser sibling to ``ck_signal_badge``. Where badge is for
page-header callouts, chip is for tight table cells, inline-flow
text, and metric row gutters where a 14-20px tone-colored marker
is enough.

Not yet wired to any partner-facing page. Tests lock the contract
+ palette before integration.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_signal_chip


class EmptyCasesTests(unittest.TestCase):

    def test_none_label_returns_empty(self):
        self.assertEqual(ck_signal_chip(None), "")

    def test_empty_string_returns_empty(self):
        self.assertEqual(ck_signal_chip(""), "")

    def test_whitespace_only_returns_empty(self):
        self.assertEqual(ck_signal_chip("   "), "")
        self.assertEqual(ck_signal_chip("\t\n"), "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_html_span(self):
        out = ck_signal_chip("Live")
        self.assertTrue(out.startswith("<span"))
        self.assertTrue(out.endswith("</span>"))

    def test_label_text_appears(self):
        out = ck_signal_chip("Calibrated")
        self.assertIn(">Calibrated<", out)

    def test_strips_whitespace_around_label(self):
        out = ck_signal_chip("  Live  ")
        self.assertIn(">Live<", out)

    def test_class_carries_signal_chip(self):
        out = ck_signal_chip("X")
        self.assertIn('class="ck-signal-chip', out)

    def test_role_status_for_accessibility(self):
        out = ck_signal_chip("Live")
        self.assertIn('role="status"', out)

    def test_pill_shape_via_border_radius(self):
        out = ck_signal_chip("Live")
        self.assertIn("border-radius:999px", out)

    def test_inline_flex_layout(self):
        out = ck_signal_chip("Live")
        self.assertIn("display:inline-flex", out)


class ToneTests(unittest.TestCase):
    """The five-tone palette is the editorial contract."""

    def test_positive_uses_mint_and_deep_green(self):
        out = ck_signal_chip("OK", tone="positive")
        self.assertIn("background:#dff2e7", out)
        self.assertIn("color:#0a6b48", out)
        self.assertIn("ck-chip-positive", out)

    def test_warning_uses_amber_and_sepia(self):
        out = ck_signal_chip("Watch", tone="warning")
        self.assertIn("background:#fbeed1", out)
        self.assertIn("color:#7a4f12", out)
        self.assertIn("ck-chip-warning", out)

    def test_negative_uses_blush_and_brick(self):
        out = ck_signal_chip("Stop", tone="negative")
        self.assertIn("background:#fbe1da", out)
        self.assertIn("color:#7a1f10", out)
        self.assertIn("ck-chip-negative", out)

    def test_info_uses_sky_and_navy(self):
        out = ck_signal_chip("Note", tone="info")
        self.assertIn("background:#dde9f5", out)
        self.assertIn("color:#143560", out)

    def test_neutral_default_uses_parchment_gray(self):
        # No tone arg → neutral palette
        out = ck_signal_chip("idle")
        self.assertIn("background:#ece8df", out)
        self.assertIn("color:#5a544c", out)

    def test_unknown_tone_falls_back_to_neutral(self):
        out = ck_signal_chip("X", tone="strawberry")
        self.assertIn("background:#ece8df", out)

    def test_none_tone_falls_back_to_neutral(self):
        out = ck_signal_chip("X", tone=None)  # type: ignore
        self.assertIn("background:#ece8df", out)

    def test_case_insensitive_tone(self):
        out = ck_signal_chip("OK", tone="POSITIVE")
        self.assertIn("background:#dff2e7", out)


class DotTests(unittest.TestCase):

    def test_dot_renders_by_default(self):
        out = ck_signal_chip("Live")
        self.assertIn("ck-chip-dot", out)
        self.assertIn("border-radius:50%", out)

    def test_dot_can_be_hidden(self):
        out = ck_signal_chip("Live", show_dot=False)
        self.assertNotIn("ck-chip-dot", out)

    def test_dot_color_matches_foreground(self):
        # Dot color = fg color (consistent with palette).
        out = ck_signal_chip("OK", tone="positive")
        # Dot background uses #0a6b48 (the fg color for positive).
        self.assertIn("background:#0a6b48", out)


class IconTests(unittest.TestCase):

    def test_no_icon_by_default(self):
        out = ck_signal_chip("Live")
        self.assertNotIn("ck-chip-icon", out)

    def test_icon_prefixes_label(self):
        out = ck_signal_chip("Up", icon="↑")
        self.assertIn("ck-chip-icon", out)
        self.assertIn("↑", out)
        # Icon appears before label.
        self.assertLess(out.index("ck-chip-icon"),
                         out.index("ck-chip-label"))

    def test_icon_html_escaped(self):
        # Defense against injection in icon arg.
        out = ck_signal_chip("X", icon="<script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


class SizeTests(unittest.TestCase):

    def test_default_size_sm(self):
        out = ck_signal_chip("Live")
        self.assertIn("ck-chip-sm", out)
        self.assertIn("font-size:11px", out)

    def test_md_size_uses_12px(self):
        out = ck_signal_chip("Live", size="md")
        self.assertIn("ck-chip-md", out)
        self.assertIn("font-size:12px", out)

    def test_unknown_size_falls_back_to_sm(self):
        out = ck_signal_chip("Live", size="huge")
        self.assertIn("font-size:11px", out)


class TooltipAndAriaTests(unittest.TestCase):

    def test_default_aria_uses_label(self):
        out = ck_signal_chip("Live")
        self.assertIn('aria-label="Live"', out)
        self.assertIn('title="Live"', out)

    def test_custom_title_overrides_tooltip(self):
        out = ck_signal_chip("LIVE", title="Calibrated 2h ago")
        self.assertIn('aria-label="Calibrated 2h ago"', out)
        self.assertIn('title="Calibrated 2h ago"', out)
        # But label text still says LIVE
        self.assertIn(">LIVE<", out)

    def test_label_html_escaped(self):
        out = ck_signal_chip("<script>alert(1)</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_title_html_escaped(self):
        out = ck_signal_chip("X", title="<img onerror=z>")
        self.assertNotIn("<img onerror=z>", out)
        self.assertIn("&lt;img", out)


class StylingTests(unittest.TestCase):

    def test_uses_inter_tight_font(self):
        # Inter Tight is the editorial UI sans (per CLAUDE.md).
        out = ck_signal_chip("Live")
        self.assertIn("Inter Tight", out)

    def test_uses_tabular_nums(self):
        out = ck_signal_chip("Live")
        self.assertIn("tabular-nums", out)

    def test_vertical_align_middle(self):
        # Chips sit inline with text — must align vertically center.
        out = ck_signal_chip("Live")
        self.assertIn("vertical-align:middle", out)


if __name__ == "__main__":
    unittest.main()
