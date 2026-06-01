"""Tests for ``ck_data_freshness_pill`` — colored age pill.

The most universal partner-facing 'is this number current?' signal.
Drops into any cell or KPI block where a value carries a refresh
timestamp; encodes age into a three-tier color (fresh/stale/very
stale) + a humanized 'Updated Xh ago' string.

Not yet wired to any partner-facing page. Tests lock the contract
before integration so consumers (every CMS-loader card, snapshot
ingest banner, payer-mix freshness gutter) get a stable surface.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_data_freshness_pill


HR = 3600
DAY = 86400


class NoneCasesTests(unittest.TestCase):
    """Unlike most ck_* helpers, freshness NEVER returns empty —
    partner needs a 'never updated' cell, not an invisible gap."""

    def test_none_renders_neutral_gray_pill(self):
        out = ck_data_freshness_pill(None)
        self.assertNotEqual(out, "")
        self.assertIn("ck-freshness-none", out)
        self.assertIn("Never updated", out)

    def test_non_numeric_renders_neutral_gray_pill(self):
        out = ck_data_freshness_pill("junk")
        self.assertIn("ck-freshness-none", out)

    def test_nan_renders_neutral_gray_pill(self):
        out = ck_data_freshness_pill(float("nan"))
        self.assertIn("ck-freshness-none", out)

    def test_inf_renders_neutral_gray_pill(self):
        out = ck_data_freshness_pill(float("inf"))
        self.assertIn("ck-freshness-none", out)

    def test_custom_none_label(self):
        out = ck_data_freshness_pill(None, none_label="No refresh data")
        self.assertIn("No refresh data", out)


class FreshZoneTests(unittest.TestCase):
    """≤ fresh_threshold_hours (default 24h) → mint pill with deep green."""

    def test_just_now_under_1m(self):
        out = ck_data_freshness_pill(30)  # 30 seconds
        self.assertIn("just now", out)
        self.assertIn("ck-freshness-fresh", out)

    def test_minutes_branch(self):
        out = ck_data_freshness_pill(8 * 60)  # 8 minutes
        self.assertIn("8m", out)
        self.assertIn("ck-freshness-fresh", out)

    def test_hours_under_10_uses_decimal(self):
        out = ck_data_freshness_pill(5.5 * HR)
        self.assertIn("5.5h", out)
        self.assertIn("ck-freshness-fresh", out)

    def test_hours_10_to_24_uses_integer(self):
        out = ck_data_freshness_pill(18 * HR)
        self.assertIn("18h", out)
        self.assertIn("ck-freshness-fresh", out)

    def test_at_fresh_threshold_boundary_is_fresh(self):
        # Exactly 24h → still fresh (inclusive)
        out = ck_data_freshness_pill(24 * HR)
        self.assertIn("ck-freshness-fresh", out)

    def test_negative_age_clamps_to_fresh(self):
        # Clock skew (timestamp in the future) → just now / fresh
        out = ck_data_freshness_pill(-500)
        self.assertIn("ck-freshness-fresh", out)
        self.assertIn("just now", out)


class StaleZoneTests(unittest.TestCase):
    """fresh < age ≤ stale (default 24h..168h) → amber."""

    def test_2_days_is_stale(self):
        out = ck_data_freshness_pill(2 * DAY)
        self.assertIn("2.0d", out)
        self.assertIn("ck-freshness-stale", out)

    def test_just_past_fresh_boundary(self):
        # 24h + 1s → stale
        out = ck_data_freshness_pill(24 * HR + 1)
        self.assertIn("ck-freshness-stale", out)

    def test_at_stale_boundary_is_stale(self):
        # 168h exactly → still stale (inclusive)
        out = ck_data_freshness_pill(168 * HR)
        self.assertIn("ck-freshness-stale", out)


class VeryStaleZoneTests(unittest.TestCase):
    """age > stale_threshold (default 7 days) → red."""

    def test_14_days_is_very_stale(self):
        out = ck_data_freshness_pill(14 * DAY)
        self.assertIn("14d", out)
        self.assertIn("ck-freshness-very-stale", out)

    def test_past_30_days_uses_months(self):
        out = ck_data_freshness_pill(60 * DAY)
        self.assertIn("2mo", out)
        self.assertIn("ck-freshness-very-stale", out)

    def test_past_365_days_uses_years(self):
        out = ck_data_freshness_pill(500 * DAY)
        self.assertIn("1.4y", out)
        self.assertIn("ck-freshness-very-stale", out)


class CustomThresholdTests(unittest.TestCase):

    def test_tight_fresh_threshold(self):
        # CMS-loader case: fresh ≤ 1h → 2h is already stale
        out = ck_data_freshness_pill(
            2 * HR, fresh_threshold_hours=1.0,
        )
        self.assertIn("ck-freshness-stale", out)

    def test_loose_stale_threshold(self):
        # Snapshot-ingest case: stale = 30d → 14d still amber
        out = ck_data_freshness_pill(
            14 * DAY, stale_threshold_hours=30 * 24,
        )
        self.assertIn("ck-freshness-stale", out)

    def test_both_thresholds_custom(self):
        # 6h with fresh=4h + stale=48h → stale band
        out = ck_data_freshness_pill(
            6 * HR,
            fresh_threshold_hours=4.0,
            stale_threshold_hours=48.0,
        )
        self.assertIn("ck-freshness-stale", out)


class LabelTests(unittest.TestCase):

    def test_default_label_prefix(self):
        out = ck_data_freshness_pill(5 * HR)
        self.assertIn("Updated 5.0h ago", out)

    def test_custom_label_prefix(self):
        out = ck_data_freshness_pill(5 * HR, label_prefix="Refreshed")
        self.assertIn("Refreshed 5.0h ago", out)

    def test_no_ago_suffix(self):
        out = ck_data_freshness_pill(5 * HR, show_ago_suffix=False)
        self.assertIn("Updated 5.0h", out)
        self.assertNotIn("ago", out)

    def test_just_now_skips_prefix_and_suffix(self):
        out = ck_data_freshness_pill(20)  # 20 seconds → just now
        # 'just now' renders as itself, no 'Updated ... ago'.
        self.assertIn("just now", out)
        self.assertNotIn("Updated just now", out)


class StylingTests(unittest.TestCase):

    def test_renders_inline_flex_pill(self):
        out = ck_data_freshness_pill(5 * HR)
        self.assertIn("display:inline-flex", out)
        self.assertIn("border-radius:999px", out)

    def test_renders_color_dot(self):
        # 6px dot + 4px gap convention.
        out = ck_data_freshness_pill(5 * HR)
        self.assertIn("ck-freshness-dot", out)
        self.assertIn("width:6px", out)
        self.assertIn("border-radius:50%", out)

    def test_uses_tabular_nums(self):
        # So pills align across rows.
        out = ck_data_freshness_pill(5 * HR)
        self.assertIn("tabular-nums", out)

    def test_zone_color_palette(self):
        # fresh → mint bg + deep-green fg
        out_fresh = ck_data_freshness_pill(2 * HR)
        self.assertIn("#dff2e7", out_fresh)
        self.assertIn("#0a6b48", out_fresh)
        # stale → parchment-amber + sepia
        out_stale = ck_data_freshness_pill(3 * DAY)
        self.assertIn("#fbeed1", out_stale)
        self.assertIn("#7a4f12", out_stale)
        # very stale → blush + brick
        out_red = ck_data_freshness_pill(14 * DAY)
        self.assertIn("#fbe1da", out_red)
        self.assertIn("#7a1f10", out_red)

    def test_tooltip_includes_zone_for_non_fresh(self):
        out = ck_data_freshness_pill(3 * DAY)
        self.assertIn("(stale)", out)
        out_red = ck_data_freshness_pill(14 * DAY)
        self.assertIn("(very stale)", out_red)

    def test_tooltip_omits_zone_for_fresh(self):
        # Don't annoy the partner with '(fresh)' when it's, well, fresh.
        out = ck_data_freshness_pill(5 * HR)
        self.assertNotIn("(fresh)", out)


class XssTests(unittest.TestCase):
    """All injected labels go through _esc."""

    def test_custom_none_label_escaped(self):
        out = ck_data_freshness_pill(
            None, none_label='<script>alert(1)</script>',
        )
        self.assertNotIn('<script>', out)
        self.assertIn('&lt;script&gt;', out)

    def test_custom_label_prefix_escaped(self):
        out = ck_data_freshness_pill(
            5 * HR, label_prefix='<img onerror=x>',
        )
        self.assertNotIn('<img onerror=x>', out)
        # Escaped form appears in either body or title.
        self.assertIn('&lt;img', out)


if __name__ == "__main__":
    unittest.main()
