"""Tests for ``ck_band_dot`` — categorical band marker.

The smallest reusable signal in the chartis vocabulary: an 8–12px
colored circle for letter-grade, star-rating, tertile, quartile,
or yes/no categorical signals. Designed to sit beside row labels
or in table cells without consuming a full column for text.

Used by the Iter-8 design (per-physician-group MIPS band dot) and
generally everywhere a categorical signal needs a one-glance
visual without a full badge component.

Not yet wired to a partner page. Tests lock the palette contracts
+ the silent-fallback behavior before integration.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import (
    _BAND_PALETTE_LETTER_GRADE,
    _BAND_PALETTE_QUARTILE,
    _BAND_PALETTE_STAR_RATING,
    _BAND_PALETTE_TERTILE,
    _BAND_PALETTE_YESNO,
    ck_band_dot,
)


class BasicRenderTests(unittest.TestCase):

    def test_returns_svg(self):
        out = ck_band_dot("A")
        self.assertTrue(out.startswith("<svg"))
        self.assertTrue(out.endswith("</svg>"))

    def test_default_diameter(self):
        out = ck_band_dot("A")
        self.assertIn('width="10"', out)
        self.assertIn('height="10"', out)

    def test_custom_diameter(self):
        out = ck_band_dot("A", diameter=14)
        self.assertIn('width="14"', out)
        self.assertIn('height="14"', out)

    def test_minimum_diameter_floor(self):
        # Below 4px the dot stops being visible — floor at 4.
        out = ck_band_dot("A", diameter=2)
        self.assertIn('width="4"', out)

    def test_class_and_accessibility(self):
        out = ck_band_dot("A")
        self.assertIn('class="ck-band-dot"', out)
        self.assertIn('role="img"', out)

    def test_renders_circle(self):
        out = ck_band_dot("A")
        self.assertIn('<circle', out)


class LetterGradePaletteTests(unittest.TestCase):

    def test_A_is_positive_green(self):
        out = ck_band_dot("A")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)

    def test_B_uses_b_color(self):
        out = ck_band_dot("B")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["B"], out)

    def test_C_is_warning_amber(self):
        out = ck_band_dot("C")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["C"], out)

    def test_D_is_negative_red(self):
        out = ck_band_dot("D")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["D"], out)

    def test_F_is_deep_red(self):
        out = ck_band_dot("F")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["F"], out)

    def test_case_insensitive_lookup(self):
        out_upper = ck_band_dot("A")
        out_lower = ck_band_dot("a")
        out_mixed = ck_band_dot("A")
        for out in (out_upper, out_lower, out_mixed):
            self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)

    def test_grade_palette_alias_works(self):
        out = ck_band_dot("A", palette="grade")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)


class StarRatingPaletteTests(unittest.TestCase):

    def test_five_star_is_positive(self):
        out = ck_band_dot("5", palette="star")
        self.assertIn(_BAND_PALETTE_STAR_RATING["5"], out)

    def test_one_star_is_deep_red(self):
        out = ck_band_dot("1", palette="star")
        self.assertIn(_BAND_PALETTE_STAR_RATING["1"], out)

    def test_accepts_integer_band(self):
        # Caller passes int; we coerce via str().
        out = ck_band_dot(5, palette="star")
        self.assertIn(_BAND_PALETTE_STAR_RATING["5"], out)


class TertileAndQuartilePaletteTests(unittest.TestCase):

    def test_tertile_high_is_green(self):
        out = ck_band_dot("high", palette="tertile")
        self.assertIn(_BAND_PALETTE_TERTILE["high"], out)

    def test_tertile_low_is_red(self):
        out = ck_band_dot("low", palette="tertile")
        self.assertIn(_BAND_PALETTE_TERTILE["low"], out)

    def test_tertile_case_insensitive(self):
        out = ck_band_dot("HIGH", palette="tertile")
        self.assertIn(_BAND_PALETTE_TERTILE["high"], out)

    def test_quartile_top_is_green(self):
        out = ck_band_dot("top", palette="quartile")
        self.assertIn(_BAND_PALETTE_QUARTILE["top"], out)

    def test_quartile_bottom_is_red(self):
        out = ck_band_dot("bottom", palette="quartile")
        self.assertIn(_BAND_PALETTE_QUARTILE["bottom"], out)


class YesNoBinaryPaletteTests(unittest.TestCase):

    def test_yes_is_positive(self):
        out = ck_band_dot("yes", palette="yesno")
        self.assertIn(_BAND_PALETTE_YESNO["yes"], out)

    def test_no_is_negative(self):
        out = ck_band_dot("no", palette="yesno")
        self.assertIn(_BAND_PALETTE_YESNO["no"], out)

    def test_na_is_gray(self):
        out = ck_band_dot("n/a", palette="yesno")
        self.assertIn(_BAND_PALETTE_YESNO["n/a"], out)

    def test_em_dash_is_gray(self):
        # Em-dash is the partner-visible 'no signal' marker.
        out = ck_band_dot("—", palette="yesno")
        self.assertIn(_BAND_PALETTE_YESNO["—"], out)

    def test_binary_palette_alias(self):
        out = ck_band_dot("yes", palette="binary")
        self.assertIn(_BAND_PALETTE_YESNO["yes"], out)


class FallbackTests(unittest.TestCase):
    """Unknown band / None / unknown palette all degrade to a
    neutral gray dot — caller sees a cell, partner knows to drill
    in. Better than empty (which looks like the column failed)."""

    def test_unknown_band_is_neutral_gray(self):
        out = ck_band_dot("xyz_unrecognized")
        self.assertIn("#a8a8a8", out)

    def test_none_band_is_neutral_gray(self):
        out = ck_band_dot(None)
        self.assertIn("#a8a8a8", out)

    def test_empty_string_band_is_neutral_gray(self):
        out = ck_band_dot("")
        self.assertIn("#a8a8a8", out)

    def test_whitespace_only_band_is_neutral_gray(self):
        out = ck_band_dot("   ")
        self.assertIn("#a8a8a8", out)

    def test_unknown_palette_string_falls_back_to_letter_grade(self):
        # palette='weird' → letter palette → 'A' resolves
        out = ck_band_dot("A", palette="weird_palette_name")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)

    def test_non_string_non_dict_palette_falls_back_to_letter(self):
        out = ck_band_dot("A", palette=12345)
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)


class CustomPaletteTests(unittest.TestCase):

    def test_dict_palette_used(self):
        out = ck_band_dot(
            "alpha", palette={"alpha": "#123456", "beta": "#abcdef"})
        self.assertIn("#123456", out)

    def test_dict_palette_unknown_band_falls_back(self):
        out = ck_band_dot(
            "gamma", palette={"alpha": "#123456"})
        # gamma not in palette → neutral gray fallback
        self.assertIn("#a8a8a8", out)

    def test_dict_palette_supports_arbitrary_keys(self):
        # Custom palettes can encode anything: IC-readiness levels,
        # data-confidence tiers, etc.
        out = ck_band_dot(
            "ic_ready", palette={"ic_ready": "#0a8a5f",
                                  "needs_data": "#b8732a",
                                  "blocked": "#b5321e"})
        self.assertIn("#0a8a5f", out)


class TooltipTests(unittest.TestCase):

    def test_tooltip_defaults_to_band_string(self):
        out = ck_band_dot("A")
        self.assertIn("<title>A</title>", out)

    def test_tooltip_label_override(self):
        out = ck_band_dot("A", label="IC-ready")
        self.assertIn("<title>IC-ready</title>", out)

    def test_none_band_tooltip_says_no_data(self):
        out = ck_band_dot(None)
        self.assertIn("no data", out)

    def test_tooltip_html_escaped(self):
        out = ck_band_dot("A", label="<script>alert(1)</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_aria_label_matches_tooltip(self):
        out = ck_band_dot("A", label="Exceptional MIPS")
        self.assertIn('aria-label="Exceptional MIPS"', out)


class InlineLabelTests(unittest.TestCase):

    def test_off_by_default(self):
        out = ck_band_dot("A")
        self.assertNotIn('ck-band-dot-wrap', out)
        self.assertNotIn('ck-band-dot-label', out)

    def test_on_wraps_in_inline_flex_span(self):
        out = ck_band_dot("A", show_label_inline=True)
        self.assertIn('ck-band-dot-wrap', out)
        self.assertIn('display:inline-flex', out)
        self.assertIn('ck-band-dot-label', out)
        self.assertIn(">A<", out)

    def test_inline_label_uses_mono_font(self):
        # Caption uses JetBrains Mono (per chartis numerical convention)
        out = ck_band_dot("A", show_label_inline=True)
        self.assertIn("JetBrains Mono", out)

    def test_empty_band_with_inline_label_drops_label(self):
        # When the band is empty/None, the inline label is suppressed
        # — caller doesn't get a bare gray dot with empty caption.
        out = ck_band_dot(None, show_label_inline=True)
        self.assertNotIn('ck-band-dot-wrap', out)


if __name__ == "__main__":
    unittest.main()
