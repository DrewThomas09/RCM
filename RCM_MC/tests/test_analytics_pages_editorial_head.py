"""Editorial-head cascade for analytics_pages (sweep batch 13).

Four analytics routes share rcm_mc/ui/analytics_pages.py:
  /models/causal/<deal>          render_causal_page
  /models/counterfactual/<deal>  render_counterfactual_page
  /benchmarks                    render_benchmark_drift
  /models/predicted-actual/<deal> render_predicted_vs_actual

A new local helper `_ap_head` composes the strict Tier-1 5-block head
once; the four renderers call it with their own eyebrow / meta /
italic-first-phrase / lede body. Pre-sweep each renderer called
ck_section_intro at the top (h2 deck), and the shell auto-injected a
ck_page_title above that — two title blocks stacked. Now: one head,
one h1.

Pins (across all four routes):
  · ONE <h1> per page (#1036 a11y invariant).
  · Eyebrow with 24×1px green-dash glyph.
  · Mono uppercase meta-line quoting REAL counts (estimates,
    periods, benchmarks, metrics) — derived from the live data
    each renderer receives.
  · Italic-first-phrase serif lede in --green-deep.
  · 4-bucket status-dot legend.
"""
from __future__ import annotations

import re
import unittest


class CausalPageHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.analytics_pages import render_causal_page
        cls.html = render_causal_page(
            "alpha-001",
            "Alpha Hospital",
            [
                {"method": "ITS", "estimated_effect": 0.5,
                 "ci_low": 0.1, "ci_high": 0.9,
                 "p_value": 0.02, "confidence": "high"},
                {"method": "DiD", "estimated_effect": 0.3,
                 "ci_low": -0.1, "ci_high": 0.7,
                 "p_value": 0.10, "confidence": "medium"},
            ],
        )

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="ap-head"', self.html)

    def test_eyebrow_dash_causal(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*CAUSAL INFERENCE',
        )

    def test_meta_quotes_real_counts(self) -> None:
        # 2 estimates, 1 significant (p<0.05) — both quoted in meta.
        self.assertIn("2 ESTIMATES", self.html)
        self.assertIn("1 SIGNIFICANT", self.html)
        self.assertIn("ALPHA-001", self.html)  # deal id uppercase

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>What actually moved the needle.</em>",
            self.html,
        )


class CounterfactualPageHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.analytics_pages import render_counterfactual_page
        cls.html = render_counterfactual_page(
            "beta-002",
            "Beta Health",
            {
                "actual_trajectory": [100e6, 110e6, 125e6],
                "counterfactual_trajectory": [100e6, 95e6, 90e6],
                "delta_per_period": [0, 15e6, 35e6],
                "cumulative_delta": 50e6,
                "methodology": "pre-post with ramp adjustment",
            },
        )

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="ap-head"', self.html)

    def test_meta_quotes_periods_and_cumulative(self) -> None:
        self.assertIn("3 PERIODS", self.html)
        # Cumulative delta is $50M and positive → "$50.0M HIGHER"
        self.assertIn("$50.0M HIGHER", self.html)

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>What would have happened without the initiative.</em>",
            self.html,
        )


class BenchmarkDriftHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.analytics_pages import render_benchmark_drift
        cls.html = render_benchmark_drift([
            {"metric_key": "margin", "current_p50": 12, "prior_p50": 10,
             "drift_pp": 2, "direction": "improving"},
            {"metric_key": "ar_days", "current_p50": 55, "prior_p50": 48,
             "drift_pp": 7, "direction": "declining"},
            {"metric_key": "denial", "current_p50": 9, "prior_p50": 9,
             "drift_pp": 0, "direction": "stable"},
        ])

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="ap-head"', self.html)

    def test_meta_quotes_real_drift_counts(self) -> None:
        # 3 benchmarks, 1 improving, 1 declining
        self.assertIn("3 BENCHMARKS", self.html)
        self.assertIn("1 IMPROVING", self.html)
        self.assertIn("1 DECLINING", self.html)

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>How the bar is moving on you, year over year.</em>",
            self.html,
        )


class PredictedVsActualHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.analytics_pages import render_predicted_vs_actual
        cls.html = render_predicted_vs_actual(
            "gamma-003",
            "Gamma Medical",
            [],
            {
                "pct_within_ci": 0.75,
                "mean_absolute_error": 0.15,
                "n_metrics": 8,
            },
        )

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="ap-head"', self.html)

    def test_meta_quotes_real_calibration(self) -> None:
        self.assertIn("8 METRICS", self.html)
        self.assertIn("75% WITHIN CI", self.html)
        self.assertIn("MAE 0.15", self.html)

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>How the diligence-era forecast aged.</em>",
            self.html,
        )


class CommonStatusLegendTests(unittest.TestCase):
    """All four pages carry the 4-bucket status-dot legend."""

    def test_all_four_routes_carry_legend(self) -> None:
        from rcm_mc.ui.analytics_pages import (
            render_causal_page, render_counterfactual_page,
            render_benchmark_drift, render_predicted_vs_actual,
        )
        renders = [
            render_causal_page("d", "n", []),
            render_counterfactual_page("d", "n", {
                "actual_trajectory": [], "counterfactual_trajectory": [],
                "delta_per_period": [], "cumulative_delta": 0,
                "methodology": "x",
            }),
            render_benchmark_drift([]),
            render_predicted_vs_actual("d", "n", [], {
                "pct_within_ci": 0, "mean_absolute_error": 0, "n_metrics": 0,
            }),
        ]
        for i, html in enumerate(renders):
            with self.subTest(renderer_index=i):
                for cls_name in ("live", "computed", "needs",
                                 "illustrative"):
                    self.assertRegex(
                        html,
                        rf'<span class="dot {cls_name}"></span>',
                    )


if __name__ == "__main__":
    unittest.main()
