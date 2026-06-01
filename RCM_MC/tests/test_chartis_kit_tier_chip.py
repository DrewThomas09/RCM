"""Tests for ``ck_tier_chip`` — pill-shaped graded tier indicator.

Sibling primitive to ``ck_band_dot`` (single colored circle) — this
is the next density tier up: a small pill that shows the tier letter
plus a leading colored dot. Keeps the letter readable while still
fitting in a row gutter where ``ck_signal_badge`` would be too tall.

Shares the same palette aliases as ck_band_dot (letter/star/tertile/
quartile/yesno + custom dict).
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import (
    _BAND_PALETTE_LETTER_GRADE,
    _BAND_PALETTE_QUARTILE,
    _BAND_PALETTE_STAR_RATING,
    _BAND_PALETTE_TERTILE,
    _BAND_PALETTE_YESNO,
    ck_tier_chip,
)


class BasicRenderTests(unittest.TestCase):

    def test_renders_pill_with_class(self):
        out = ck_tier_chip("A")
        self.assertIn('class="ck-tier-chip', out)

    def test_pill_shape_via_border_radius(self):
        out = ck_tier_chip("A")
        self.assertIn("border-radius:999px", out)

    def test_includes_colored_dot(self):
        out = ck_tier_chip("A")
        self.assertIn("ck-tier-chip-dot", out)
        # Dot is the colored marker — letter-grade A → green.
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)

    def test_includes_label_by_default(self):
        out = ck_tier_chip("A")
        self.assertIn("ck-tier-chip-label", out)
        self.assertIn(">A<", out)

    def test_role_img(self):
        out = ck_tier_chip("A")
        self.assertIn('role="img"', out)


class LetterGradePaletteTests(unittest.TestCase):

    def test_each_letter_tier_uses_palette_color(self):
        for letter in ("A", "B", "C", "D", "F"):
            out = ck_tier_chip(letter)
            self.assertIn(_BAND_PALETTE_LETTER_GRADE[letter], out,
                          f"missing palette color for {letter}")

    def test_case_insensitive_lookup(self):
        out_lower = ck_tier_chip("a")
        # 'a' upper-cases to 'A' → green
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out_lower)

    def test_grade_alias_works(self):
        out = ck_tier_chip("A", palette="grade")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)


class StarPaletteTests(unittest.TestCase):

    def test_5_star_resolves(self):
        out = ck_tier_chip("5", palette="star")
        self.assertIn(_BAND_PALETTE_STAR_RATING["5"], out)

    def test_1_star_resolves(self):
        out = ck_tier_chip("1", palette="star")
        self.assertIn(_BAND_PALETTE_STAR_RATING["1"], out)

    def test_integer_star_accepted(self):
        # int(5) → str → resolves
        out = ck_tier_chip(5, palette="star")
        self.assertIn(_BAND_PALETTE_STAR_RATING["5"], out)


class TertileAndQuartilePaletteTests(unittest.TestCase):

    def test_tertile_high(self):
        out = ck_tier_chip("high", palette="tertile")
        self.assertIn(_BAND_PALETTE_TERTILE["high"], out)

    def test_tertile_low(self):
        out = ck_tier_chip("low", palette="tertile")
        self.assertIn(_BAND_PALETTE_TERTILE["low"], out)

    def test_quartile_top(self):
        out = ck_tier_chip("top", palette="quartile")
        self.assertIn(_BAND_PALETTE_QUARTILE["top"], out)

    def test_quartile_bottom(self):
        out = ck_tier_chip("bottom", palette="quartile")
        self.assertIn(_BAND_PALETTE_QUARTILE["bottom"], out)


class YesNoPaletteTests(unittest.TestCase):

    def test_yes_resolves(self):
        out = ck_tier_chip("yes", palette="yesno")
        self.assertIn(_BAND_PALETTE_YESNO["yes"], out)

    def test_no_resolves(self):
        out = ck_tier_chip("no", palette="yesno")
        self.assertIn(_BAND_PALETTE_YESNO["no"], out)

    def test_na_resolves(self):
        out = ck_tier_chip("n/a", palette="yesno")
        self.assertIn(_BAND_PALETTE_YESNO["n/a"], out)

    def test_binary_alias(self):
        out = ck_tier_chip("yes", palette="binary")
        self.assertIn(_BAND_PALETTE_YESNO["yes"], out)


class CustomDictPaletteTests(unittest.TestCase):

    def test_dict_palette_resolves(self):
        out = ck_tier_chip(
            "alpha",
            palette={"alpha": "#123456", "beta": "#abcdef"},
        )
        self.assertIn("#123456", out)

    def test_dict_palette_unknown_falls_back_to_neutral_gray(self):
        out = ck_tier_chip(
            "gamma", palette={"alpha": "#123456"},
        )
        self.assertIn("#a8a8a8", out)


class FallbackTests(unittest.TestCase):
    """Unknown tier / None / unknown palette degrade to neutral gray —
    NEVER empty string (partner needs visible 'no signal'). Mirrors
    ck_band_dot's opt-out from the empty-string contract."""

    def test_unknown_tier_is_neutral_gray(self):
        out = ck_tier_chip("xyz_unrecognized")
        self.assertIn("#a8a8a8", out)

    def test_none_tier_is_neutral_gray(self):
        out = ck_tier_chip(None)
        self.assertIn("#a8a8a8", out)
        self.assertNotEqual(out, "")

    def test_empty_string_tier_is_neutral_gray(self):
        out = ck_tier_chip("")
        self.assertIn("#a8a8a8", out)

    def test_whitespace_tier_is_neutral_gray(self):
        out = ck_tier_chip("   ")
        self.assertIn("#a8a8a8", out)

    def test_unknown_palette_string_falls_back_to_letter(self):
        # palette='weird' → letter palette → 'A' resolves
        out = ck_tier_chip("A", palette="weird")
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)

    def test_non_string_non_dict_palette_falls_back_to_letter(self):
        out = ck_tier_chip("A", palette=12345)
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)

    def test_none_tier_uses_dash_when_no_label(self):
        # Default display text is em-dash for None when no label given
        out = ck_tier_chip(None)
        self.assertIn(">—<", out)


class LabelOverrideTests(unittest.TestCase):

    def test_label_overrides_displayed_text(self):
        # Tier letter 'A' but label says 'Exceptional MIPS'
        out = ck_tier_chip("A", label="Exceptional MIPS")
        # Color still from tier lookup (green for A).
        self.assertIn(_BAND_PALETTE_LETTER_GRADE["A"], out)
        # Label text displayed instead of raw tier.
        self.assertIn(">Exceptional MIPS<", out)
        # Tier letter 'A' itself NOT in the label span.
        self.assertNotIn(">A<", out)

    def test_label_appears_in_tooltip(self):
        out = ck_tier_chip("A", label="Exceptional")
        self.assertIn('title="Exceptional"', out)
        self.assertIn('aria-label="Exceptional"', out)


class ShowLabelTests(unittest.TestCase):

    def test_show_label_false_hides_label_span(self):
        out = ck_tier_chip("A", show_label=False)
        self.assertNotIn("ck-tier-chip-label", out)
        # Dot still present so the chip remains visible.
        self.assertIn("ck-tier-chip-dot", out)

    def test_show_label_false_keeps_tooltip(self):
        out = ck_tier_chip("A", show_label=False)
        # Hover still tells you the tier.
        self.assertIn('title="A"', out)


class SizeTests(unittest.TestCase):

    def test_default_sm_size(self):
        out = ck_tier_chip("A")
        self.assertIn("ck-tier-chip-sm", out)
        self.assertIn("font-size:11px", out)

    def test_md_size(self):
        out = ck_tier_chip("A", size="md")
        self.assertIn("ck-tier-chip-md", out)
        self.assertIn("font-size:12px", out)

    def test_unknown_size_falls_back_to_sm(self):
        out = ck_tier_chip("A", size="huge")
        self.assertIn("font-size:11px", out)


class StylingTests(unittest.TestCase):

    def test_uses_jetbrains_mono(self):
        # Tier letters are numerical/short tokens — mono for alignment.
        out = ck_tier_chip("A")
        self.assertIn("JetBrains Mono", out)

    def test_inline_flex_layout(self):
        out = ck_tier_chip("A")
        self.assertIn("display:inline-flex", out)

    def test_vertical_align_middle(self):
        # Sits inline with row text.
        out = ck_tier_chip("A")
        self.assertIn("vertical-align:middle", out)


class XssTests(unittest.TestCase):

    def test_label_html_escaped(self):
        out = ck_tier_chip("A", label="<script>x</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_unknown_tier_with_html_escaped(self):
        # Even unknown tiers must be escaped before display.
        out = ck_tier_chip("<img onerror=x>")
        self.assertNotIn("<img onerror=x>", out)
        self.assertIn("&lt;img", out)


if __name__ == "__main__":
    unittest.main()
