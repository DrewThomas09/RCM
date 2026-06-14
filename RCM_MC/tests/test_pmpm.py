"""Tests for the risk-adjusted PMPM trend mart."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.pmpm import (
    PMPMPeriod,
    PMPMVerdict,
    analyze_pmpm,
)


class PMPMPeriodTests(unittest.TestCase):

    def test_risk_adjusted_pmpm(self):
        p = PMPMPeriod("2026Q1", pmpm=1300.0, raf=1.30)
        self.assertAlmostEqual(p.risk_adjusted_pmpm, 1000.0)

    def test_raf_zero_falls_back(self):
        p = PMPMPeriod("x", pmpm=500.0, raf=0.0)
        self.assertEqual(p.risk_adjusted_pmpm, 500.0)


class PMPMTrendTests(unittest.TestCase):

    def _annual_series(self, pmpms, rafs):
        return [
            PMPMPeriod(f"202{i}", pmpm=p, raf=r)
            for i, (p, r) in enumerate(zip(pmpms, rafs))
        ]

    def test_case_mix_drift_explains_growth(self):
        # PMPM rises 10%/yr but entirely because RAF rises 10%/yr →
        # risk-adjusted PMPM is flat → EFFICIENT/IN_LINE.
        periods = self._annual_series(
            pmpms=[1000, 1100, 1210], rafs=[1.0, 1.1, 1.21],
        )
        res = analyze_pmpm(periods, periods_per_year=1.0)
        self.assertGreater(res.nominal_cagr, 0.09)
        self.assertAlmostEqual(res.risk_adjusted_cagr, 0.0, delta=0.005)
        self.assertIn(res.verdict, (PMPMVerdict.IN_LINE, PMPMVerdict.EFFICIENT))

    def test_real_cost_inflation_flagged(self):
        # PMPM rises with flat RAF → real inflation → ELEVATED/OUTLIER.
        periods = self._annual_series(
            pmpms=[1000, 1100, 1210], rafs=[1.0, 1.0, 1.0],
        )
        res = analyze_pmpm(periods, periods_per_year=1.0)
        self.assertGreater(res.risk_adjusted_cagr, 0.08)
        self.assertEqual(res.verdict, PMPMVerdict.OUTLIER)

    def test_declining_cost_efficient(self):
        periods = self._annual_series(
            pmpms=[1200, 1100, 1000], rafs=[1.0, 1.0, 1.0],
        )
        res = analyze_pmpm(periods, periods_per_year=1.0)
        self.assertLess(res.risk_adjusted_cagr, 0.0)
        self.assertEqual(res.verdict, PMPMVerdict.EFFICIENT)

    def test_peer_benchmark_composes(self):
        periods = self._annual_series(
            pmpms=[1000, 1050], rafs=[1.0, 1.0],
        )
        res = analyze_pmpm(
            periods, periods_per_year=1.0,
            peer_risk_adjusted_pmpm=[900, 950, 1000, 980],
            peer_rafs=[1.0, 1.0, 1.0, 1.0],
        )
        self.assertIsNotNone(res.peer_benchmark)
        self.assertGreater(res.peer_benchmark.oe_ratio, 1.0)  # above peers

    def test_ebitda_projection(self):
        periods = self._annual_series(
            pmpms=[1000, 1100], rafs=[1.0, 1.0],   # 10%/yr real
        )
        res = analyze_pmpm(
            periods, periods_per_year=1.0,
            annual_member_months=120_000, projection_years=3.0,
        )
        self.assertIsNotNone(res.projected_ebitda_impact_usd)
        self.assertGreater(res.projected_ebitda_impact_usd, 0)

    def test_insufficient_history(self):
        res = analyze_pmpm([PMPMPeriod("2026", 1000.0, 1.0)])
        self.assertEqual(res.verdict, PMPMVerdict.IN_LINE)
        self.assertEqual(res.years_observed, 0.0)
        self.assertIn("Insufficient", res.headline)

    def test_quarterly_annualization(self):
        # 4 quarters of 2% per-quarter growth ≈ 8.2% annualized over 0.75y.
        periods = [
            PMPMPeriod(f"2026Q{i+1}", pmpm=1000 * (1.02 ** i), raf=1.0)
            for i in range(4)
        ]
        res = analyze_pmpm(periods, periods_per_year=4.0)
        self.assertAlmostEqual(res.years_observed, 0.75)
        self.assertGreater(res.risk_adjusted_cagr, 0.07)

    def test_headline_and_dict(self):
        periods = self._annual_series([1000, 1100], [1.0, 1.05])
        res = analyze_pmpm(periods, periods_per_year=1.0)
        self.assertTrue(res.headline)
        self.assertEqual(res.to_dict()["citation_key"], "PM1")


if __name__ == "__main__":
    unittest.main()
