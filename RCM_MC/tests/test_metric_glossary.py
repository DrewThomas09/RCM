"""Tests for the metric glossary + contextual tooltips."""
from __future__ import annotations

import unittest


class TestRegistry(unittest.TestCase):
    def test_core_metrics_present(self):
        from rcm_mc.ui.metric_glossary import list_metrics
        keys = list_metrics()
        for required in [
            "denial_rate", "days_in_ar",
            "net_collection_rate", "clean_claim_rate",
            "cost_to_collect", "operating_margin",
            "ebitda_margin", "case_mix_index",
            "days_cash_on_hand", "occupancy_rate",
            "fte_per_aob", "labor_pct_of_npsr",
            "medicare_day_pct", "medicaid_day_pct",
        ]:
            self.assertIn(required, keys)

    def test_definition_fields_populated(self):
        from rcm_mc.ui.metric_glossary import (
            get_metric_definition, list_metrics,
        )
        for key in list_metrics():
            d = get_metric_definition(key)
            self.assertIsNotNone(d)
            self.assertTrue(d.label)
            self.assertTrue(d.definition)
            self.assertTrue(d.why_it_matters)
            self.assertTrue(d.how_calculated)

    def test_unknown_returns_none(self):
        from rcm_mc.ui.metric_glossary import (
            get_metric_definition,
        )
        self.assertIsNone(
            get_metric_definition("not_a_real_metric"))

    def test_define_metric_at_runtime(self):
        from rcm_mc.ui.metric_glossary import (
            define_metric, get_metric_definition,
        )
        define_metric(
            "ma_penetration_test",
            label="MA Penetration",
            definition="Share of Medicare lives in MA plans.",
            why_it_matters=(
                "Drives prior-auth + bad-debt risk."),
            how_calculated="MA enrollment / eligible pop.",
            units="%", typical_range="20-65%")
        d = get_metric_definition("ma_penetration_test")
        self.assertIsNotNone(d)
        self.assertEqual(d.label, "MA Penetration")


class TestMetricTooltip(unittest.TestCase):
    def test_renders_label_and_icon(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip("denial_rate")
        self.assertIn("Denial Rate", html)
        self.assertIn("metric-tt-icon", html)
        # Card content present
        self.assertIn("Why it matters", html)
        self.assertIn("How it", html)
        self.assertIn("calculated", html)

    def test_with_value(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip(
            "denial_rate", value="12.0%")
        self.assertIn("12.0%", html)

    def test_label_override(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip(
            "denial_rate", label="Denial")
        # The override label appears in the outer span as
        # the visible text (before the tooltip card markup)
        self.assertIn(
            '<span>Denial</span><span class="metric-tt-icon"',
            html)

    def test_unknown_metric_graceful_fallback(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip(
            "nonexistent_metric")
        # Should still render the title-cased key
        self.assertIn("Nonexistent Metric", html)
        # No tooltip card
        self.assertNotIn("metric-tt-icon", html)

    def test_unknown_metric_with_value(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip(
            "nonexistent_metric", value="42%")
        self.assertIn("Nonexistent Metric", html)
        self.assertIn("42%", html)

    def test_typical_range_in_card(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip("denial_rate")
        self.assertIn("Typical range", html)
        self.assertIn("5-15%", html)

    def test_inject_css_default(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip("denial_rate")
        self.assertIn("<style>", html)
        self.assertIn(".metric-tt", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.metric_glossary import metric_tooltip
        html = metric_tooltip(
            "denial_rate", inject_css=False)
        self.assertNotIn("<style>", html)
        # But the structure is still there
        self.assertIn("metric-tt-icon", html)

    def test_html_escape_in_card(self):
        from rcm_mc.ui.metric_glossary import (
            define_metric, metric_tooltip,
        )
        define_metric(
            "xss_test_metric",
            label="<script>alert('x')</script>",
            definition="Bad <script>.",
            why_it_matters="Bad.",
            how_calculated="Bad.")
        html = metric_tooltip("xss_test_metric")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestLabelWithInfo(unittest.TestCase):
    def test_renders_without_value(self):
        from rcm_mc.ui.metric_glossary import (
            metric_label_with_info,
        )
        html = metric_label_with_info("days_in_ar")
        self.assertIn("Days in A/R", html)
        self.assertIn("metric-tt-icon", html)


if __name__ == "__main__":
    unittest.main()
