"""Tests for the provenance tag system."""
from __future__ import annotations

import unittest


class TestSourceTag(unittest.TestCase):

    def test_hcris_tag(self):
        from rcm_mc.ui.provenance import source_tag, Source
        tag = source_tag(Source.HCRIS)
        self.assertIn("HCRIS", tag)
        self.assertIn("span", tag)

    def test_ml_tag(self):
        from rcm_mc.ui.provenance import source_tag, Source
        tag = source_tag(Source.ML_PREDICTION)
        self.assertIn("ML", tag)

    def test_seller_tag_with_detail(self):
        from rcm_mc.ui.provenance import source_tag, Source
        tag = source_tag(Source.SELLER, "Q4 2025")
        self.assertIn("SELLER", tag)
        self.assertIn("Q4 2025", tag)

    def test_tag_with_n(self):
        from rcm_mc.ui.provenance import source_tag_with_n, Source
        tag = source_tag_with_n(Source.HCRIS, n=5808, period="FY2022")
        self.assertIn("5,808", tag)
        self.assertIn("FY2022", tag)


class TestClassifySource(unittest.TestCase):

    def test_calibrated_wins(self):
        from rcm_mc.ui.provenance import classify_metric_source, Source
        src, val, _ = classify_metric_source(
            "denial_rate", hcris_value=0.10,
            ml_predicted=0.11, seller_value=0.09, calibrated_value=0.095)
        self.assertEqual(src, Source.CALIBRATED)

    def test_seller_over_hcris(self):
        from rcm_mc.ui.provenance import classify_metric_source, Source
        src, _, _ = classify_metric_source(
            "denial_rate", hcris_value=0.10, seller_value=0.09)
        self.assertEqual(src, Source.SELLER)

    def test_hcris_over_ml(self):
        from rcm_mc.ui.provenance import classify_metric_source, Source
        src, _, _ = classify_metric_source(
            "beds", hcris_value=200, ml_predicted=180)
        self.assertEqual(src, Source.HCRIS)

    def test_ml_fallback(self):
        from rcm_mc.ui.provenance import classify_metric_source, Source
        src, _, _ = classify_metric_source("denial_rate", ml_predicted=0.11)
        self.assertEqual(src, Source.ML_PREDICTION)

    def test_default_when_nothing(self):
        from rcm_mc.ui.provenance import classify_metric_source, Source
        src, _, _ = classify_metric_source("unknown")
        self.assertEqual(src, Source.DEFAULT)


class TestFreshness(unittest.TestCase):

    def test_footer(self):
        from rcm_mc.ui.provenance import data_freshness_footer
        html = data_freshness_footer(hcris_year=2022, n_hospitals=6123)
        self.assertIn("HCRIS FY2022", html)
        self.assertIn("6,123", html)

    def test_footer_with_seller(self):
        from rcm_mc.ui.provenance import data_freshness_footer
        html = data_freshness_footer(has_seller_data=True, n_seller_metrics=3)
        self.assertIn("3 seller", html)


class TestLegend(unittest.TestCase):

    def test_all_sources(self):
        from rcm_mc.ui.provenance import provenance_legend
        html = provenance_legend()
        for src in ["HCRIS", "ML", "SELLER", "CALIBRATED", "BENCHMARK"]:
            self.assertIn(src, html)


class TestProfile(unittest.TestCase):

    def test_builds_from_hcris_and_ml(self):
        from rcm_mc.ui.provenance import build_provenance_profile, Source
        hcris = {"net_patient_revenue": 400e6, "beds": 200, "medicare_day_pct": 0.4}
        ml = {"denial_rate": 0.10}
        profile = build_provenance_profile("010001", hcris, ml)
        self.assertEqual(profile["net_patient_revenue"]["source"], Source.HCRIS)
        self.assertEqual(profile["denial_rate"]["source"], Source.ML_PREDICTION)


class TestBridgeIntegration(unittest.TestCase):

    def test_bridge_has_tags(self):
        import pandas as pd
        from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge
        df = pd.DataFrame({
            "ccn": ["000001"], "name": ["Test"], "state": ["CA"],
            "beds": [200.0], "net_patient_revenue": [400e6],
            "operating_expenses": [380e6], "gross_patient_revenue": [1e9],
            "medicare_day_pct": [0.4], "medicaid_day_pct": [0.15],
            "total_patient_days": [50000.0], "bed_days_available": [73000.0],
        })
        html = render_ebitda_bridge("000001", df)
        self.assertIn("HCRIS", html)
        self.assertIn("DEFAULT", html)
        self.assertIn("BENCHMARK", html)


if __name__ == "__main__":
    unittest.main()
