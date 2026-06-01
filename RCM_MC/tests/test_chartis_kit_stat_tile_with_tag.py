"""Tests for ``ck_stat_tile_with_tag`` — compact stat tile + tag.

Densest 'KPI block' variant in the chartis family. Where
``ck_kpi_block`` is hero-sized for section headers, this tile is
~80px and fits four-across in a dashboard row. The tag is the
differentiating feature — a small categorical pill (Tier A, Stage
III, IC-ready, Top quartile) that adds context the value alone
can't carry.

Not yet wired to any partner-facing page. Tests lock the
contract + tag tone palette before integration.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_stat_tile_with_tag


class EmptyCasesTests(unittest.TestCase):
    """A tile without a label can't communicate its identity in a
    dashboard row — return empty so the caller can drop it."""

    def test_none_label_returns_empty(self):
        self.assertEqual(ck_stat_tile_with_tag(None, "$5.0M"), "")

    def test_empty_label_returns_empty(self):
        self.assertEqual(ck_stat_tile_with_tag("", "$5.0M"), "")

    def test_whitespace_only_label_returns_empty(self):
        self.assertEqual(ck_stat_tile_with_tag("   ", "$5.0M"), "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_div(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertIn("<div", out)
        self.assertIn("ck-stat-tile", out)

    def test_label_text_appears(self):
        out = ck_stat_tile_with_tag("EBITDA Drag", "$5.0M")
        self.assertIn(">EBITDA Drag<", out)

    def test_value_text_appears(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertIn(">$5.0M<", out)

    def test_strips_label_whitespace(self):
        out = ck_stat_tile_with_tag("  EBITDA  ", "$5.0M")
        self.assertIn(">EBITDA<", out)

    def test_value_none_renders_em_dash(self):
        # value=None → em-dash placeholder.
        out = ck_stat_tile_with_tag("EBITDA", None)
        self.assertIn(">—<", out)

    def test_parchment_background(self):
        # Sits on editorial parchment by default.
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertIn("background:#f5f1ea", out)


class StylingTests(unittest.TestCase):

    def test_label_uses_inter_tight(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertIn("Inter Tight", out)

    def test_value_uses_source_serif(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertIn("Source Serif 4", out)

    def test_value_uses_tabular_nums(self):
        # So the big number aligns across tiles in a row.
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertIn("tabular-nums", out)

    def test_label_caps_with_letter_spacing(self):
        # Label is small-caps eyebrow style.
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertIn("text-transform:uppercase", out)
        self.assertIn("letter-spacing:0.08em", out)


class SubLineTests(unittest.TestCase):

    def test_sub_renders_when_provided(self):
        out = ck_stat_tile_with_tag(
            "EBITDA", "$5.0M", sub="vs $4.2M benchmark",
        )
        self.assertIn("ck-stat-tile-sub", out)
        self.assertIn("vs $4.2M benchmark", out)

    def test_sub_omitted_by_default(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertNotIn("ck-stat-tile-sub", out)

    def test_sub_html_escaped(self):
        out = ck_stat_tile_with_tag(
            "EBITDA", "$5.0M", sub="<script>x</script>",
        )
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


class TagTests(unittest.TestCase):

    def test_no_tag_by_default(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertNotIn("ck-stat-tile-tag", out)

    def test_tag_renders_when_provided(self):
        out = ck_stat_tile_with_tag(
            "EBITDA", "$5.0M", tag="Tier A",
        )
        self.assertIn("ck-stat-tile-tag", out)
        self.assertIn(">Tier A<", out)

    def test_default_tag_tone_is_neutral(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M", tag="Tier A")
        # Neutral palette: bg #ece8df, fg #5a544c
        self.assertIn("background:#ece8df", out)
        self.assertIn("color:#5a544c", out)
        self.assertIn("ck-tile-tag-neutral", out)

    def test_positive_tag_tone(self):
        out = ck_stat_tile_with_tag(
            "EBITDA", "$5.0M", tag="Top quartile", tag_tone="positive",
        )
        self.assertIn("background:#dff2e7", out)
        self.assertIn("color:#0a6b48", out)
        self.assertIn("ck-tile-tag-positive", out)

    def test_warning_tag_tone(self):
        out = ck_stat_tile_with_tag(
            "Margin", "8.4%", tag="Watch", tag_tone="warning",
        )
        self.assertIn("background:#fbeed1", out)
        self.assertIn("color:#7a4f12", out)

    def test_negative_tag_tone(self):
        out = ck_stat_tile_with_tag(
            "Denial Rate", "14.2%", tag="Off Target", tag_tone="negative",
        )
        self.assertIn("background:#fbe1da", out)
        self.assertIn("color:#7a1f10", out)

    def test_info_tag_tone(self):
        out = ck_stat_tile_with_tag(
            "Beta", "$5M", tag="New", tag_tone="info",
        )
        self.assertIn("background:#dde9f5", out)
        self.assertIn("color:#143560", out)

    def test_unknown_tone_falls_back_to_neutral(self):
        out = ck_stat_tile_with_tag(
            "X", "Y", tag="Z", tag_tone="strawberry",
        )
        self.assertIn("background:#ece8df", out)

    def test_tag_html_escaped(self):
        out = ck_stat_tile_with_tag(
            "X", "Y", tag="<script>alert(1)</script>",
        )
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


class HrefTests(unittest.TestCase):

    def test_no_href_no_anchor_wrapper(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertNotIn("<a ", out)

    def test_with_href_wraps_in_anchor(self):
        out = ck_stat_tile_with_tag(
            "EBITDA", "$5.0M", href="/analysis/deal-123",
        )
        self.assertTrue(out.startswith("<a "))
        self.assertIn('href="/analysis/deal-123"', out)
        # Tile chrome preserved inside the anchor.
        self.assertIn("ck-stat-tile", out)

    def test_href_html_escaped(self):
        # Defense against href injection.
        out = ck_stat_tile_with_tag(
            "X", "Y", href='" onclick="alert(1)',
        )
        self.assertNotIn('" onclick="alert', out)
        self.assertIn("&quot;", out)


class WidthTests(unittest.TestCase):

    def test_default_uses_min_width(self):
        # Default — min-width:120px (lets tile expand to its content).
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M")
        self.assertIn("min-width:120px", out)

    def test_custom_width_overrides_default(self):
        out = ck_stat_tile_with_tag("EBITDA", "$5.0M", width="200px")
        self.assertIn("width:200px", out)
        # Custom width replaces the min-width default.
        self.assertNotIn("min-width:120px", out)


class TrustedValueMarkupTests(unittest.TestCase):
    """value is treated as trusted markup (per ck_kpi_block precedent
    documented in CLAUDE.md). Caller must escape any partner-supplied
    string upstream."""

    def test_value_html_not_escaped(self):
        # Caller passes pre-formatted markup → preserved verbatim.
        out = ck_stat_tile_with_tag(
            "EBITDA", '<span class="mn">$5.0M</span>',
        )
        self.assertIn('<span class="mn">$5.0M</span>', out)

    def test_label_still_escaped(self):
        # Even though value is trusted, label is NOT.
        out = ck_stat_tile_with_tag(
            "<script>", "value",
        )
        self.assertNotIn("<script>", out.split("ck-stat-tile-value")[0])
        self.assertIn("&lt;script&gt;", out)


if __name__ == "__main__":
    unittest.main()
