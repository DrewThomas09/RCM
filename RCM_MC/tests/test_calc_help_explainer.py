"""Regression: the circled "?" calculation-explainer for predicted values.

Every modeled number should be auditable — a partner can click the small "?"
circle next to it and see EXACTLY how it was computed (formula + inputs) and
the reasonable range it's benchmarked/clamped to. See _chartis_kit.ck_calc_help
and the predictive screener.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_calc_help


class CalcHelpPrimitiveTests(unittest.TestCase):
    def test_renders_question_circle_and_popover(self):
        h = ck_calc_help("Est. Uplift", ["uplift = NPR × gap × 0.6"],
                         benchmark="Capped at 15% of revenue")
        self.assertIn("ck-help-trigger", h)      # the circular "?" button
        self.assertIn(">?<", h)
        self.assertIn("How this is calculated", h)  # aria-label
        self.assertIn("uplift = NPR", h)          # the formula
        self.assertIn("Capped at 15% of revenue", h)  # the benchmark

    def test_escapes_inputs(self):
        h = ck_calc_help("<x>", ["<script>alert(1)</script>"], benchmark="<b>")
        self.assertNotIn("<script>", h)
        self.assertNotIn("<x>", h)

    def test_multiline_formula_joined(self):
        h = ck_calc_help("M", ["line one", "line two"])
        self.assertIn("line one<br>line two", h)


class PredictiveScreenerCalcHelpTests(unittest.TestCase):
    def test_predicted_columns_and_kpis_have_calc_help(self):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.predictive_screener import render_predictive_screener
        html = render_predictive_screener(_get_latest_per_ccn(), "")
        # 2 predicted columns (Est. Denial / Est. Uplift) + 2 predicted KPIs.
        self.assertGreaterEqual(html.count("ck-calc-help"), 4)
        # The actual formulas/benchmarks are present and auditable.
        self.assertIn("Medicare-day% × 0.15", html)
        self.assertIn("Capped at 15% of revenue", html)
        self.assertIn("2%–25% industry initial-denial range", html)

    def test_calc_help_circle_css_shipped(self):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.predictive_screener import render_predictive_screener
        html = render_predictive_screener(_get_latest_per_ccn(), "")
        # The "?" renders as a circle (shell ships .ck-help-trigger styling).
        self.assertIn("ck-help-trigger", html)
        self.assertIn("border-radius: 50%", html)


class ThesisCardCalcHelpTests(unittest.TestCase):
    def test_predicted_kpis_have_calc_help(self):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.thesis_card import render_thesis_card
        df = _get_latest_per_ccn()
        html = render_thesis_card(str(df.iloc[0]["ccn"]), df)
        # Investability score, EBITDA uplift, Margin Δ — all three modeled.
        self.assertGreaterEqual(html.count("ck-calc-help"), 3)
        self.assertIn("five equally-weighted pillars", html)
        self.assertTrue("RCM EBITDA bridge" in html or "7 levers" in html)


if __name__ == "__main__":
    unittest.main()
