"""Tests for ``ck_arrow_bridge`` — start → end transition cell.

Two-state transition: start → arrow → end with optional intermediate
label. Use anywhere a partner-facing cell needs to read 'this went
from A to B' without consuming a chart:

  * baseline → target ($4.0M → $5.5M)
  * pre-deal → post-deal margin (8% → 14%)
  * Q1 ranking → Q4 ranking (Bottom quartile → Top quartile)
  * IC-ready → Signed (with months-elapsed mid_label)

Not yet wired to a partner-facing page. Tests lock the contract
before integration.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_arrow_bridge


class EmptyCasesTests(unittest.TestCase):

    def test_none_start_returns_empty(self):
        self.assertEqual(ck_arrow_bridge(None, "$5M"), "")

    def test_none_end_returns_empty(self):
        self.assertEqual(ck_arrow_bridge("$4M", None), "")

    def test_both_none_returns_empty(self):
        self.assertEqual(ck_arrow_bridge(None, None), "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_div_with_class(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn('class="ck-arrow-bridge"', out)

    def test_start_value_appears(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn(">$4M<", out)

    def test_end_value_appears(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn(">$5.5M<", out)

    def test_renders_arrow_svg(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn("<svg", out)
        self.assertIn("ck-bridge-arrow", out)

    def test_arrow_has_shaft_and_head(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        # Shaft line + polyline chevron head
        self.assertIn("<line", out)
        self.assertIn("<polyline", out)

    def test_role_img(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn('role="img"', out)


class DirectionToneTests(unittest.TestCase):
    """Arrow color encodes direction-of-improvement."""

    def test_positive_default_is_green(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        # Positive green #0a8a5f appears in stroke color.
        self.assertIn('stroke="#0a8a5f"', out)

    def test_explicit_positive_is_green(self):
        out = ck_arrow_bridge("8%", "14%", direction="positive")
        self.assertIn('stroke="#0a8a5f"', out)

    def test_negative_is_red(self):
        out = ck_arrow_bridge("10%", "15%", direction="negative")
        self.assertIn('stroke="#b5321e"', out)

    def test_warning_is_amber(self):
        out = ck_arrow_bridge("$4M", "$3M", direction="warning")
        self.assertIn('stroke="#b8732a"', out)

    def test_neutral_is_teal(self):
        out = ck_arrow_bridge("A", "B", direction="neutral")
        self.assertIn('stroke="#155752"', out)

    def test_unknown_direction_falls_back_to_teal_neutral(self):
        # 'sideways' → falls to neutral teal
        out = ck_arrow_bridge("A", "B", direction="sideways")
        self.assertIn('stroke="#155752"', out)

    def test_none_direction_falls_back_to_positive(self):
        # direction=None → default 'positive' → green
        out = ck_arrow_bridge("$4M", "$5M", direction=None)  # type: ignore
        self.assertIn('stroke="#0a8a5f"', out)

    def test_case_insensitive_direction(self):
        out = ck_arrow_bridge("10%", "15%", direction="NEGATIVE")
        self.assertIn('stroke="#b5321e"', out)


class EyebrowLabelsTests(unittest.TestCase):

    def test_no_eyebrows_by_default(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertNotIn("ck-bridge-eyebrow", out)

    def test_start_label_renders_eyebrow(self):
        out = ck_arrow_bridge("$4M", "$5.5M", start_label="Baseline")
        self.assertIn("ck-bridge-eyebrow", out)
        self.assertIn(">Baseline<", out)

    def test_end_label_renders_eyebrow(self):
        out = ck_arrow_bridge("$4M", "$5.5M", end_label="Target")
        self.assertIn(">Target<", out)

    def test_both_eyebrows_render(self):
        out = ck_arrow_bridge(
            "$4M", "$5.5M",
            start_label="Baseline", end_label="Target",
        )
        self.assertEqual(out.count("ck-bridge-eyebrow"), 2)

    def test_start_label_html_escaped(self):
        out = ck_arrow_bridge(
            "$4M", "$5.5M", start_label="<script>",
        )
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


class MidLabelTests(unittest.TestCase):

    def test_no_mid_by_default(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertNotIn("ck-bridge-mid", out)

    def test_mid_label_renders_above_arrow(self):
        out = ck_arrow_bridge(
            "$4M", "$5.5M", mid_label="+18mo",
        )
        self.assertIn("ck-bridge-mid", out)
        self.assertIn(">+18mo<", out)

    def test_mid_label_color_matches_arrow_tone(self):
        # Positive direction → mid label uses green color.
        out = ck_arrow_bridge(
            "$4M", "$5.5M", mid_label="+37%", direction="positive",
        )
        # mid_label color should be the positive arrow color.
        self.assertIn("color:#0a8a5f", out)

    def test_mid_label_uses_mono_font(self):
        out = ck_arrow_bridge(
            "$4M", "$5.5M", mid_label="+18mo",
        )
        self.assertIn("JetBrains Mono", out)

    def test_mid_label_html_escaped(self):
        out = ck_arrow_bridge(
            "$4M", "$5.5M", mid_label="<img onerror=x>",
        )
        self.assertNotIn("<img onerror=x>", out)
        self.assertIn("&lt;img", out)


class StylingTests(unittest.TestCase):

    def test_uses_source_serif_for_values(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn("Source Serif 4", out)

    def test_uses_tabular_nums_for_values(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn("tabular-nums", out)

    def test_start_value_uses_dimmed_color(self):
        # Start value gets dim gray; end value gets full ink.
        out = ck_arrow_bridge("$4M", "$5.5M")
        # Dim color = #7a7468; full ink = #1a2332
        self.assertIn("color:#7a7468", out)
        self.assertIn("color:#1a2332", out)

    def test_inline_flex_layout(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn("display:inline-flex", out)


class TrustedValueMarkupTests(unittest.TestCase):
    """Both values are rendered as trusted markup (per ck_kpi_block
    precedent). Caller must escape any partner-supplied string."""

    def test_value_html_not_escaped(self):
        # Caller pre-formats — preserved verbatim.
        out = ck_arrow_bridge(
            '<span class="num">$4M</span>',
            '<span class="num">$5.5M</span>',
        )
        self.assertIn('<span class="num">$4M</span>', out)


class AriaTests(unittest.TestCase):

    def test_aria_label_carries_both_values(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        self.assertIn("$4M", out)
        self.assertIn("$5.5M", out)
        # Aria label format: 'start: $4M → end: $5.5M' (fallback labels)
        self.assertIn("aria-label=", out)
        self.assertIn("→", out)

    def test_aria_label_uses_custom_labels(self):
        out = ck_arrow_bridge(
            "$4M", "$5.5M",
            start_label="Baseline", end_label="Target",
        )
        self.assertIn('aria-label="Baseline: $4M → Target: $5.5M"', out)


class DimensionsTests(unittest.TestCase):

    def test_default_dimensions_meet_floor(self):
        out = ck_arrow_bridge("$4M", "$5.5M")
        # Arrow SVG default 28×height
        self.assertIn('width="28"', out)

    def test_custom_height_above_floor(self):
        out = ck_arrow_bridge("$4M", "$5.5M", height=40)
        # Arrow SVG height matches the custom height.
        self.assertIn('height="40"', out)

    def test_minimum_height_floor(self):
        # Below 18 → floored to 18.
        out = ck_arrow_bridge("$4M", "$5.5M", height=4)
        self.assertIn('height="18"', out)


if __name__ == "__main__":
    unittest.main()
