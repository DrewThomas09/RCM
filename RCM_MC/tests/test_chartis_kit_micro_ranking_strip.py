"""Tests for ``ck_micro_ranking_strip`` — peer-rank inline visualization.

Generalizes the 'where does this target sit in its peer set?' answer
into a reusable strip. Use anywhere a row needs to say 'Top 12% of
47 peers' or 'Bottom quartile, 9 of 32' without consuming a chart:

  * Care Compare 5-star: 'rank 3 of 4500 hospitals'
  * MIPS percentile: 'top 8% of physician group cohort'
  * SimplyAnalytics market score: 'rank 42 of 312 ZIPs'
  * Just-missed screener: 'closest 17 of 423 targets'

Not yet wired to a partner-facing page. Tests lock the contract
before integration so consumers get a stable surface.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_micro_ranking_strip


class EmptyCasesTests(unittest.TestCase):

    def test_none_rank_returns_empty(self):
        self.assertEqual(ck_micro_ranking_strip(None, 100), "")

    def test_none_cohort_returns_empty(self):
        self.assertEqual(ck_micro_ranking_strip(5, None), "")

    def test_zero_cohort_returns_empty(self):
        self.assertEqual(ck_micro_ranking_strip(0, 0), "")

    def test_negative_cohort_returns_empty(self):
        self.assertEqual(ck_micro_ranking_strip(1, -5), "")

    def test_non_numeric_returns_empty(self):
        self.assertEqual(ck_micro_ranking_strip("one", 100), "")
        self.assertEqual(ck_micro_ranking_strip(5, "hundred"), "")

    def test_rank_zero_or_negative_returns_empty(self):
        # Rank must be 1-indexed.
        self.assertEqual(ck_micro_ranking_strip(0, 100), "")
        self.assertEqual(ck_micro_ranking_strip(-3, 100), "")

    def test_rank_above_cohort_returns_empty(self):
        # rank > cohort_size is structurally invalid.
        self.assertEqual(ck_micro_ranking_strip(101, 100), "")


class BasicRenderTests(unittest.TestCase):

    def test_returns_html_with_svg(self):
        out = ck_micro_ranking_strip(3, 100)
        self.assertIn("<svg", out)
        self.assertIn("</svg>", out)

    def test_default_dimensions(self):
        out = ck_micro_ranking_strip(3, 100)
        self.assertIn('width="100"', out)
        self.assertIn('height="14"', out)

    def test_custom_dimensions(self):
        out = ck_micro_ranking_strip(3, 100, width=160, height=20)
        self.assertIn('width="160"', out)
        self.assertIn('height="20"', out)

    def test_minimum_dimensions_enforced(self):
        # Floors at 40×8.
        out = ck_micro_ranking_strip(3, 100, width=10, height=2)
        self.assertIn('width="40"', out)
        self.assertIn('height="8"', out)

    def test_class_and_accessibility(self):
        out = ck_micro_ranking_strip(3, 100)
        self.assertIn('class="ck-micro-ranking"', out)
        self.assertIn('role="img"', out)
        # Aria carries 'rank N of M (caption)' format.
        self.assertIn('aria-label="rank 3 of 100', out)

    def test_renders_background_ribbon(self):
        out = ck_micro_ranking_strip(3, 100)
        self.assertIn('fill="#e8e1d3"', out)

    def test_renders_marker_solid_bold(self):
        out = ck_micro_ranking_strip(3, 100)
        # Marker line — solid, linecap round, width 2.5
        self.assertIn('stroke-width="2.5"', out)
        self.assertIn('stroke-linecap="round"', out)

    def test_renders_quartile_anchor_ticks(self):
        # Three small ticks at the 25/50/75 quartile boundaries help
        # the eye anchor.
        out = ck_micro_ranking_strip(3, 100)
        self.assertEqual(out.count('stroke-width="0.6"'), 3)


class PositiveDirectionToneTests(unittest.TestCase):
    """direction='positive': lower rank = better. Top quartile → green."""

    def test_top_quartile_is_positive_green(self):
        # rank 10 of 100 → pct=9% (within top 25) → #0a8a5f
        out = ck_micro_ranking_strip(10, 100, direction="positive")
        self.assertIn("#0a8a5f", out)

    def test_second_quartile_is_mid_teal(self):
        # rank 40 of 100 → pct=39% (Q2) → #155752
        out = ck_micro_ranking_strip(40, 100, direction="positive")
        self.assertIn("#155752", out)

    def test_third_quartile_is_amber(self):
        # rank 60 of 100 → pct=59% (Q3) → #b8732a
        out = ck_micro_ranking_strip(60, 100, direction="positive")
        self.assertIn("#b8732a", out)

    def test_bottom_quartile_is_red(self):
        # rank 90 of 100 → pct=89% (Q4) → #b5321e
        out = ck_micro_ranking_strip(90, 100, direction="positive")
        self.assertIn("#b5321e", out)


class NegativeDirectionToneTests(unittest.TestCase):
    """direction='negative': lower rank = worse. Top quartile inverts
    to red, bottom inverts to green."""

    def test_top_quartile_negative_is_red(self):
        # Low rank in negative direction = worst tone.
        out = ck_micro_ranking_strip(10, 100, direction="negative")
        self.assertIn("#b5321e", out)

    def test_bottom_quartile_negative_is_green(self):
        out = ck_micro_ranking_strip(90, 100, direction="negative")
        self.assertIn("#0a8a5f", out)


class DirectionFallbackTests(unittest.TestCase):

    def test_unknown_direction_falls_back_to_positive(self):
        # 'weird' → positive → top quartile → green
        out = ck_micro_ranking_strip(10, 100, direction="weird")
        self.assertIn("#0a8a5f", out)

    def test_none_direction_falls_back_to_positive(self):
        out = ck_micro_ranking_strip(
            10, 100, direction=None,  # type: ignore
        )
        self.assertIn("#0a8a5f", out)

    def test_case_insensitive_direction(self):
        out = ck_micro_ranking_strip(90, 100, direction="NEGATIVE")
        self.assertIn("#0a8a5f", out)


class CaptionTests(unittest.TestCase):

    def test_top_half_uses_top_pct_phrasing(self):
        # rank 10 of 100 → top 10% → 'Top 10% of 100'
        out = ck_micro_ranking_strip(10, 100, direction="positive")
        self.assertIn(">Top 10% of 100<", out)

    def test_bottom_half_uses_count_phrasing(self):
        # rank 75 of 100 → top 75% (above 50% cutoff) → fallback to count
        out = ck_micro_ranking_strip(75, 100, direction="positive")
        self.assertIn(">75 of 100<", out)

    def test_negative_direction_bottom_half_phrasing(self):
        # Negative direction: rank 95 of 100 means BOTTOM 6% (which is
        # actually 'good' under negative semantics) → 'Bottom 6% of 100'
        out = ck_micro_ranking_strip(95, 100, direction="negative")
        self.assertIn(">Bottom 6% of 100<", out)

    def test_custom_label_template(self):
        # Template gets named fields: rank, n, pct, top_pct, bottom_pct
        out = ck_micro_ranking_strip(
            42, 312, label_template="Position {rank}/{n}",
        )
        self.assertIn(">Position 42/312<", out)

    def test_hide_caption(self):
        # show_caption=False → just the SVG, no inline-flex wrapper.
        out = ck_micro_ranking_strip(3, 100, show_caption=False)
        self.assertNotIn("ck-micro-ranking-caption", out)
        self.assertTrue(out.startswith("<svg"))


class MarkerPositionTests(unittest.TestCase):
    """The marker line x-position is the visual contract — verify it
    sits where the rank says it does."""

    def test_rank_1_marker_at_left_edge(self):
        import re
        out = ck_micro_ranking_strip(1, 100, width=100)
        m = re.search(r'<line x1="([\d.]+)"[^>]*stroke-width="2.5"', out)
        self.assertIsNotNone(m)
        # Rank 1 → pos_frac = 0 → x = 0.5
        self.assertAlmostEqual(float(m.group(1)), 0.5, places=1)

    def test_rank_n_marker_at_right_edge(self):
        import re
        out = ck_micro_ranking_strip(100, 100, width=100)
        m = re.search(r'<line x1="([\d.]+)"[^>]*stroke-width="2.5"', out)
        self.assertAlmostEqual(float(m.group(1)), 99.5, places=1)

    def test_middle_rank_marker_at_midpoint(self):
        import re
        # rank 51 of 101 → exact midpoint
        out = ck_micro_ranking_strip(51, 101, width=100)
        m = re.search(r'<line x1="([\d.]+)"[^>]*stroke-width="2.5"', out)
        x = float(m.group(1))
        # Middle ± a couple px tolerance
        self.assertGreater(x, 45)
        self.assertLess(x, 55)

    def test_singleton_cohort_at_left_edge(self):
        # n=1 → marker pinned to left edge (no division by zero).
        import re
        out = ck_micro_ranking_strip(1, 1, width=100)
        m = re.search(r'<line x1="([\d.]+)"[^>]*stroke-width="2.5"', out)
        self.assertAlmostEqual(float(m.group(1)), 0.5, places=1)


class TooltipTests(unittest.TestCase):

    def test_tooltip_includes_rank_and_cohort(self):
        out = ck_micro_ranking_strip(42, 312)
        self.assertIn("<title>", out)
        self.assertIn("rank 42 of 312", out)


class LayoutTests(unittest.TestCase):

    def test_caption_uses_tabular_nums(self):
        out = ck_micro_ranking_strip(42, 312)
        self.assertIn("tabular-nums", out)

    def test_caption_uses_jetbrains_mono(self):
        out = ck_micro_ranking_strip(42, 312)
        self.assertIn("JetBrains Mono", out)

    def test_caption_color_matches_tone(self):
        # Top quartile (rank 1 of 100) → green tone in caption text.
        out = ck_micro_ranking_strip(1, 100)
        self.assertIn("color:#0a8a5f", out)


if __name__ == "__main__":
    unittest.main()
