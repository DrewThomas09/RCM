"""Tests for ``ck_inline_diff`` — compact text-only old → new diff cell.

Smaller, denser sibling to ``ck_arrow_bridge``. Where bridge is a
full-tile transition with eyebrow labels and SVG arrow, this is the
lean single-line diff that lives inside table cells.

Use anywhere a row already has dense text and a partner needs to see
a 'changed from X to Y' in a single line: variance audit deltas,
plan-vs-actual rows, before-after overrides, calibration diffs.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_inline_diff


class EmptyCasesTests(unittest.TestCase):

    def test_none_old_returns_empty(self):
        self.assertEqual(ck_inline_diff(None, 100), "")

    def test_none_new_returns_empty(self):
        self.assertEqual(ck_inline_diff(100, None), "")

    def test_both_none_returns_empty(self):
        self.assertEqual(ck_inline_diff(None, None), "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_inline_span(self):
        out = ck_inline_diff(100, 120)
        self.assertIn('class="ck-inline-diff"', out)

    def test_renders_arrow_glyph(self):
        out = ck_inline_diff(100, 120)
        self.assertIn("→", out)
        self.assertIn("ck-diff-arrow", out)

    def test_old_value_appears_first(self):
        out = ck_inline_diff(100, 120)
        idx_old = out.index("ck-diff-old")
        idx_arrow = out.index("ck-diff-arrow")
        idx_new = out.index("ck-diff-new")
        self.assertLess(idx_old, idx_arrow)
        self.assertLess(idx_arrow, idx_new)

    def test_old_value_rendered(self):
        out = ck_inline_diff("100.0", "120.0")
        self.assertIn(">100.0<", out)

    def test_new_value_rendered(self):
        out = ck_inline_diff("100.0", "120.0")
        self.assertIn(">120.0<", out)

    def test_role_text_accessibility(self):
        out = ck_inline_diff(100, 120)
        self.assertIn('role="text"', out)


class StrikethroughTests(unittest.TestCase):

    def test_old_value_strikethrough_by_default(self):
        out = ck_inline_diff(100, 120)
        # Strikethrough applies to old span.
        self.assertIn("text-decoration:line-through", out)

    def test_strikethrough_can_be_disabled(self):
        out = ck_inline_diff(100, 120, strikethrough_old=False)
        self.assertNotIn("text-decoration:line-through", out)


class ToneByNumericalDirectionTests(unittest.TestCase):
    """When both values are numeric, tone follows direction-of-
    improvement signal."""

    def test_increase_in_positive_direction_is_green(self):
        # revenue up = good → green
        out = ck_inline_diff(100, 120, direction="positive")
        self.assertIn("#0a8a5f", out)

    def test_decrease_in_positive_direction_is_red(self):
        # revenue down = bad → red
        out = ck_inline_diff(120, 100, direction="positive")
        self.assertIn("#b5321e", out)

    def test_increase_in_negative_direction_is_red(self):
        # denial_rate up = bad → red
        out = ck_inline_diff(0.10, 0.12, direction="negative")
        self.assertIn("#b5321e", out)

    def test_decrease_in_negative_direction_is_green(self):
        # denial_rate down = good → green
        out = ck_inline_diff(0.12, 0.10, direction="negative")
        self.assertIn("#0a8a5f", out)

    def test_zero_change_uses_neutral_tone(self):
        # No editorial signal → teal/neutral.
        out = ck_inline_diff(100, 100, direction="positive")
        self.assertIn("#155752", out)

    def test_warning_direction_uses_amber(self):
        # All transitions show amber (e.g. 'something changed, watch')
        out = ck_inline_diff(100, 120, direction="warning")
        self.assertIn("#b8732a", out)


class DeltaCaptionTests(unittest.TestCase):

    def test_default_delta_shows_abs_and_pct(self):
        out = ck_inline_diff(100, 120)
        # +20.00, +20.0%
        self.assertIn("+20.00", out)
        self.assertIn("+20.0%", out)

    def test_default_delta_negative_signs(self):
        out = ck_inline_diff(120, 100)
        self.assertIn("-20.00", out)
        self.assertIn("-16.7%", out)

    def test_precision_arg(self):
        out = ck_inline_diff(100.123, 120.567, precision=4)
        self.assertIn("+20.4440", out)

    def test_show_delta_false_hides_caption(self):
        out = ck_inline_diff(100, 120, show_delta=False)
        self.assertNotIn("ck-diff-delta", out)

    def test_custom_delta_template(self):
        out = ck_inline_diff(
            100, 120,
            delta_template="changed by {diff:+.2f}",
        )
        self.assertIn("changed by +20.00", out)

    def test_zero_baseline_omits_pct_in_delta(self):
        # old=0 → pct undefined → only abs diff shown
        out = ck_inline_diff(0, 50)
        # Should NOT contain a percent figure for the delta.
        self.assertIn("+50.00", out)
        # Caption should be just (+50.00), no comma + pct.
        self.assertNotIn("+50.00, ", out)


class NonNumericValuesTests(unittest.TestCase):

    def test_string_values_render_without_delta(self):
        out = ck_inline_diff("Pending", "Approved")
        self.assertIn(">Pending<", out)
        self.assertIn(">Approved<", out)
        self.assertNotIn("ck-diff-delta", out)

    def test_string_values_use_neutral_tone(self):
        # Non-numeric → can't determine direction → neutral teal.
        out = ck_inline_diff("Old", "New", direction="positive")
        self.assertIn("#155752", out)


class TrustedMarkupTests(unittest.TestCase):
    """Like ck_arrow_bridge: both values are trusted markup. Caller
    must escape partner-supplied strings upstream."""

    def test_value_html_not_escaped(self):
        out = ck_inline_diff(
            '<span class="num">$100</span>',
            '<span class="num">$120</span>',
        )
        self.assertIn('<span class="num">$100</span>', out)
        self.assertIn('<span class="num">$120</span>', out)


class AriaAndTooltipTests(unittest.TestCase):

    def test_aria_label_carries_both_values(self):
        out = ck_inline_diff(100, 120)
        self.assertIn('aria-label="100 to 120', out)

    def test_aria_label_includes_delta_when_numeric(self):
        out = ck_inline_diff(100, 120)
        # 'to 120 (+20.00, +20.0%)'
        self.assertIn("(+20.00, +20.0%)", out)

    def test_tooltip_matches_aria_label(self):
        out = ck_inline_diff(100, 120)
        self.assertIn('title="100 to 120', out)


class StylingTests(unittest.TestCase):

    def test_uses_inter_tight(self):
        out = ck_inline_diff(100, 120)
        self.assertIn("Inter Tight", out)

    def test_uses_tabular_nums(self):
        out = ck_inline_diff(100, 120)
        self.assertIn("tabular-nums", out)

    def test_inline_flex_baseline_layout(self):
        out = ck_inline_diff(100, 120)
        self.assertIn("display:inline-flex", out)
        self.assertIn("align-items:baseline", out)

    def test_old_value_dimmed_gray(self):
        out = ck_inline_diff(100, 120)
        # Dim gray #7a7468 on old span
        self.assertIn("color:#7a7468", out)


class CaseInsensitiveDirectionTests(unittest.TestCase):

    def test_uppercase_direction_resolves(self):
        out = ck_inline_diff(100, 120, direction="POSITIVE")
        self.assertIn("#0a8a5f", out)

    def test_unknown_direction_uses_neutral_teal(self):
        out = ck_inline_diff(100, 120, direction="sideways")
        # Neutral tone (teal) — neither pos nor neg branches apply
        self.assertIn("#155752", out)


if __name__ == "__main__":
    unittest.main()
