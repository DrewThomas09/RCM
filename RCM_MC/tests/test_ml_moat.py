"""Tests for ML moat features: clustering, distress prediction, RCM opportunity."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n: int = 100) -> pd.DataFrame:
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY", "FL", "IL"], n),
        "county": ["County"] * n,
        "beds": rng.randint(20, 600, n).astype(float),
        "net_patient_revenue": rng.uniform(1e7, 5e9, n),
        "operating_expenses": rng.uniform(1e7, 5e9, n),
        "gross_patient_revenue": rng.uniform(5e7, 1e10, n),
        "medicare_day_pct": rng.uniform(0.1, 0.7, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.3, n),
        "total_patient_days": rng.randint(1000, 100000, n).astype(float),
        "bed_days_available": rng.randint(5000, 200000, n).astype(float),
    })


class TestHospitalClustering(unittest.TestCase):

    def test_clusters_hospitals(self):
        from rcm_mc.ml.hospital_clustering import cluster_hospitals
        df = _sample_hcris(200)
        result_df, profiles = cluster_hospitals(df, k=5)
        self.assertGreater(len(profiles), 0)
        self.assertIn("cluster_id", result_df.columns)
        total = sum(p.n_hospitals for p in profiles)
        self.assertGreater(total, 50)

    def test_cluster_profiles_have_labels(self):
        from rcm_mc.ml.hospital_clustering import cluster_hospitals
        df = _sample_hcris(200)
        _, profiles = cluster_hospitals(df, k=5)
        for p in profiles:
            self.assertIsInstance(p.label, str)
            self.assertIsInstance(p.archetype, str)
            self.assertGreater(p.n_hospitals, 0)
            self.assertIn("beds", p.centroid)

    def test_get_hospital_cluster(self):
        from rcm_mc.ml.hospital_clustering import get_hospital_cluster
        df = _sample_hcris(200)
        result = get_hospital_cluster("000001", df, k=5)
        self.assertIsNotNone(result)
        self.assertEqual(result.ccn, "000001")
        self.assertIsInstance(result.nearest_peers, list)

    def test_kmeans_convergence(self):
        from rcm_mc.ml.hospital_clustering import _kmeans
        X = np.random.RandomState(0).randn(100, 3)
        labels, centroids = _kmeans(X, 3)
        self.assertEqual(len(labels), 100)
        self.assertEqual(centroids.shape, (3, 3))
        self.assertTrue(all(0 <= l < 3 for l in labels))


class TestDistressPredictor(unittest.TestCase):

    def test_train_model(self):
        from rcm_mc.ml.distress_predictor import train_distress_model
        df = _sample_hcris(200)
        beta, X_mean, X_std, auc, n_train, feats = train_distress_model(df)
        self.assertGreater(n_train, 50)
        self.assertGreater(auc, 0.4)
        self.assertGreater(len(feats), 2)

    def test_predict_distress(self):
        from rcm_mc.ml.distress_predictor import predict_distress
        df = _sample_hcris(200)
        result = predict_distress("000001", df)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.distress_probability, 0)
        self.assertLessEqual(result.distress_probability, 1)
        self.assertIn(result.risk_label, ["Low", "Moderate", "Elevated", "High", "Critical"])

    def test_contributing_factors(self):
        from rcm_mc.ml.distress_predictor import predict_distress
        df = _sample_hcris(200)
        result = predict_distress("000001", df)
        self.assertIsNotNone(result)
        self.assertGreater(len(result.contributing_factors), 0)
        for f in result.contributing_factors:
            self.assertIn("feature", f)
            self.assertIn("contribution", f)

    def test_screen_distressed(self):
        from rcm_mc.ml.distress_predictor import screen_distressed
        df = _sample_hcris(200)
        results = screen_distressed(df, top_n=10)
        self.assertLessEqual(len(results), 10)
        if len(results) >= 2:
            self.assertGreaterEqual(results[0]["distress_prob"], results[1]["distress_prob"])

    def test_sigmoid(self):
        from rcm_mc.ml.distress_predictor import _sigmoid
        self.assertAlmostEqual(float(_sigmoid(np.array([0]))[0]), 0.5)
        self.assertGreater(float(_sigmoid(np.array([5]))[0]), 0.99)
        self.assertLess(float(_sigmoid(np.array([-5]))[0]), 0.01)


class TestRCMOpportunityScorer(unittest.TestCase):

    def test_compute_opportunity(self):
        from rcm_mc.ml.rcm_opportunity_scorer import compute_rcm_opportunity
        df = _sample_hcris(200)
        result = compute_rcm_opportunity("000001", df)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.opportunity_score, 0)
        self.assertLessEqual(result.opportunity_score, 100)
        self.assertIn(result.grade, ["A", "B", "C", "D"])

    def test_levers_have_impact(self):
        from rcm_mc.ml.rcm_opportunity_scorer import compute_rcm_opportunity
        df = _sample_hcris(200)
        result = compute_rcm_opportunity("000001", df)
        self.assertIsNotNone(result)
        self.assertGreater(len(result.levers), 0)
        for lever in result.levers:
            self.assertIsInstance(lever.lever, str)
            self.assertGreaterEqual(lever.confidence, 0)
            self.assertLessEqual(lever.confidence, 1)

    def test_projected_margin_positive(self):
        from rcm_mc.ml.rcm_opportunity_scorer import compute_rcm_opportunity
        df = _sample_hcris(200)
        result = compute_rcm_opportunity("000001", df)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.projected_margin, result.current_margin)

    def test_nonexistent_hospital(self):
        from rcm_mc.ml.rcm_opportunity_scorer import compute_rcm_opportunity
        df = _sample_hcris(50)
        result = compute_rcm_opportunity("999999", df)
        self.assertIsNone(result)


class TestMLInsightsPage(unittest.TestCase):

    def test_national_page_renders(self):
        from rcm_mc.ui.ml_insights_page import render_ml_insights
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris(200))
        html = render_ml_insights(df)
        self.assertIn("SeekingChartis", html)
        self.assertIn("Archetype", html)
        self.assertIn("Distress", html)

    def test_hospital_page_renders(self):
        from rcm_mc.ui.ml_insights_page import render_hospital_ml
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris(200))
        html = render_hospital_ml("000001", df)
        self.assertIn("SeekingChartis", html)
        self.assertIn("RCM", html)


if __name__ == "__main__":
    unittest.main()
