"""Tests for advanced ML moat: investability, survival, market intelligence."""
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


class TestInvestabilityScorer(unittest.TestCase):

    def test_compute_score(self):
        from rcm_mc.ml.investability_scorer import compute_investability
        df = _sample_hcris(200)
        result = compute_investability("000001", df)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.total_score, 0)
        self.assertLessEqual(result.total_score, 100)
        self.assertIn(result.grade, ["A", "B", "C", "D", "F"])

    def test_components_sum_to_total(self):
        from rcm_mc.ml.investability_scorer import compute_investability
        df = _sample_hcris(200)
        result = compute_investability("000001", df)
        self.assertIsNotNone(result)
        comp_sum = sum(result.components.values())
        self.assertAlmostEqual(comp_sum, result.total_score, delta=0.5)

    def test_has_recommendation(self):
        from rcm_mc.ml.investability_scorer import compute_investability
        df = _sample_hcris(200)
        result = compute_investability("000001", df)
        self.assertIsNotNone(result)
        self.assertGreater(len(result.recommendation), 10)
        self.assertIsInstance(result.entry_multiple_range, str)
        self.assertGreater(result.estimated_moic, 0)

    def test_nonexistent(self):
        from rcm_mc.ml.investability_scorer import compute_investability
        df = _sample_hcris(50)
        self.assertIsNone(compute_investability("999999", df))


class TestSurvivalAnalysis(unittest.TestCase):

    def test_estimate_runway(self):
        from rcm_mc.ml.survival_analysis import estimate_margin_runway
        df = _sample_hcris(100)
        result = estimate_margin_runway("000001", None, df)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.estimated_years_to_distress, 0)
        self.assertIn(result.risk_tier, ["Critical", "Elevated", "Moderate", "Low"])

    def test_survival_curve(self):
        from rcm_mc.ml.survival_analysis import estimate_margin_runway
        df = _sample_hcris(100)
        result = estimate_margin_runway("000001", None, df)
        self.assertIsNotNone(result)
        self.assertGreater(len(result.survival_curve), 5)
        for pt in result.survival_curve:
            self.assertIn("year", pt)
            self.assertIn("survival_prob", pt)

    def test_hazard_factors(self):
        from rcm_mc.ml.survival_analysis import estimate_margin_runway
        df = _sample_hcris(100)
        result = estimate_margin_runway("000001", None, df)
        self.assertIsNotNone(result)
        self.assertIsInstance(result.hazard_factors, list)


class TestMarketIntelligence(unittest.TestCase):

    def test_compute_state_markets(self):
        from rcm_mc.ml.market_intelligence import compute_state_markets
        df = _sample_hcris(200)
        markets = compute_state_markets(df)
        self.assertGreater(len(markets), 0)
        for m in markets:
            self.assertIsInstance(m.state, str)
            self.assertGreater(m.n_hospitals, 0)
            self.assertIn(m.investability_grade, ["A", "B", "C", "D"])

    def test_hhi_computation(self):
        from rcm_mc.ml.market_intelligence import compute_hhi
        self.assertEqual(compute_hhi([]), 0)
        self.assertAlmostEqual(compute_hhi([100]), 10000)
        hhi = compute_hhi([50, 50])
        self.assertAlmostEqual(hhi, 5000)

    def test_county_market(self):
        from rcm_mc.ml.market_intelligence import compute_county_market
        df = _sample_hcris(200)
        result = compute_county_market("CA", "County", df)
        self.assertIsNotNone(result)
        self.assertIn("n_hospitals", result)
        self.assertIn("hhi", result)

    def test_markets_sorted_by_investability(self):
        from rcm_mc.ml.market_intelligence import compute_state_markets
        df = _sample_hcris(300)
        markets = compute_state_markets(df)
        if len(markets) >= 2:
            self.assertGreaterEqual(
                markets[0].investability_score,
                markets[1].investability_score,
            )


if __name__ == "__main__":
    unittest.main()
