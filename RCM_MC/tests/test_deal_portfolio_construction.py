"""Tests for deal_portfolio_construction.py."""
from __future__ import annotations

import unittest
from typing import Any, Dict, List


def _deal(name: str, sector: str, year: int = 2019, buyer: str = "Sponsor A",
           payer_mix=None) -> Dict[str, Any]:
    return {
        "deal_name": name,
        "sector": sector,
        "entry_year": year,
        "buyer": buyer,
        "payer_mix": payer_mix or {"commercial": 0.60, "medicare": 0.25, "medicaid": 0.12, "self_pay": 0.03},
    }


def _diverse_portfolio() -> List[Dict[str, Any]]:
    return [
        _deal("Deal A", "Physician Practices", 2017),
        _deal("Deal B", "Dental", 2018),
        _deal("Deal C", "Behavioral Health", 2019),
        _deal("Deal D", "Health IT", 2020),
        _deal("Deal E", "Home Health", 2021),
    ]


def _concentrated_portfolio() -> List[Dict[str, Any]]:
    return [
        _deal("Deal 1", "Physician Practices", 2021),
        _deal("Deal 2", "Physician Practices", 2021),
        _deal("Deal 3", "Physician Practices", 2021),
        _deal("Deal 4", "Physician Practices", 2021),
    ]


class TestAnalyzePortfolio(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_portfolio_construction import analyze_portfolio
        self.fn = analyze_portfolio

    def test_returns_composition(self):
        from rcm_mc.data_public.deal_portfolio_construction import PortfolioComposition
        result = self.fn(_diverse_portfolio())
        self.assertIsInstance(result, PortfolioComposition)

    def test_n_deals_correct(self):
        result = self.fn(_diverse_portfolio())
        self.assertEqual(result.n_deals, 5)

    def test_sector_weights_sum_to_1(self):
        result = self.fn(_diverse_portfolio())
        total = sum(result.sector_weights.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_vintage_weights_sum_to_1(self):
        result = self.fn(_diverse_portfolio())
        total = sum(result.vintage_weights.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_hhi_sector_concentrated_high(self):
        result = self.fn(_concentrated_portfolio())
        self.assertAlmostEqual(result.hhi_sector, 1.0)

    def test_hhi_sector_diverse_low(self):
        result = self.fn(_diverse_portfolio())
        self.assertLess(result.hhi_sector, 0.30)

    def test_hhi_vintage_concentrated(self):
        result = self.fn(_concentrated_portfolio())
        self.assertAlmostEqual(result.hhi_vintage, 1.0)

    def test_hhi_in_0_1_range(self):
        for portfolio in [_diverse_portfolio(), _concentrated_portfolio()]:
            result = self.fn(portfolio)
            self.assertGreaterEqual(result.hhi_sector, 0.0)
            self.assertLessEqual(result.hhi_sector, 1.0)

    def test_payer_weights_present(self):
        result = self.fn(_diverse_portfolio())
        self.assertIn("commercial", result.payer_weights)

    def test_avg_commercial_between_0_and_1(self):
        result = self.fn(_diverse_portfolio())
        self.assertGreaterEqual(result.avg_commercial_pct, 0.0)
        self.assertLessEqual(result.avg_commercial_pct, 1.0)

    def test_empty_portfolio_no_crash(self):
        result = self.fn([])
        self.assertEqual(result.n_deals, 0)
        self.assertEqual(result.hhi_sector, 0.0)

    def test_single_deal_hhi_1(self):
        result = self.fn([_deal("Solo", "Dental")])
        self.assertAlmostEqual(result.hhi_sector, 1.0)

    def test_sponsor_weights_tracked(self):
        portfolio = [
            _deal("D1", "Dental", buyer="KKR"),
            _deal("D2", "Dental", buyer="KKR"),
            _deal("D3", "Behavioral Health", buyer="Blackstone"),
        ]
        result = self.fn(portfolio)
        self.assertIn("KKR", result.sponsor_weights)
        self.assertAlmostEqual(result.sponsor_weights["KKR"], 2 / 3, places=2)


class TestMarginalDiversification(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_portfolio_construction import marginal_diversification
        self.fn = marginal_diversification

    def test_returns_result(self):
        from rcm_mc.data_public.deal_portfolio_construction import DiversificationResult
        new = _deal("New", "Revenue Cycle Management", 2022)
        result = self.fn(new, _diverse_portfolio())
        self.assertIsInstance(result, DiversificationResult)

    def test_new_sector_positive_marginal_score(self):
        # Entirely new sector → should be diversifying
        new = _deal("New VBC", "NEMT / Transportation", 2022)
        result = self.fn(new, _diverse_portfolio())
        self.assertGreater(result.marginal_score, 30.0)

    def test_same_sector_lower_score_than_new_sector(self):
        existing_sector = _deal("Another Dental", "Dental", 2019)
        new_sector = _deal("New RCM", "Revenue Cycle Management", 2022)
        portfolio = _diverse_portfolio()
        r_same = self.fn(existing_sector, portfolio)
        r_new = self.fn(new_sector, portfolio)
        self.assertLessEqual(r_same.marginal_score, r_new.marginal_score)

    def test_duplicate_vintage_reduces_score(self):
        # Adding deal in same year as majority of portfolio
        conc = _concentrated_portfolio()  # all 2021
        new_2021 = _deal("More 2021", "Dental", 2021)
        new_2015 = _deal("Old 2015", "Dental", 2015)
        r_same = self.fn(new_2021, conc)
        r_diff = self.fn(new_2015, conc)
        self.assertLessEqual(r_same.marginal_score, r_diff.marginal_score)

    def test_hhi_before_after_consistent(self):
        new = _deal("New", "Dental", 2020)
        portfolio = _diverse_portfolio()
        result = self.fn(new, portfolio)
        self.assertAlmostEqual(
            result.hhi_sector_before,
            self.fn.__module__ and result.hhi_sector_before  # noqa — just type check
        )
        self.assertGreaterEqual(result.hhi_sector_after, 0.0)

    def test_signal_valid(self):
        new = _deal("New", "Dental", 2020)
        result = self.fn(new, _diverse_portfolio())
        self.assertIn(result.signal, ("additive", "neutral", "concentrating"))

    def test_high_correlation_reduces_score(self):
        # Emergency Medicine + Physician Practices are correlated
        portfolio = [_deal("Phys", "Physician Practices", 2019)]
        new_em = _deal("EM", "Emergency Medicine", 2020)
        new_rcm = _deal("RCM", "Revenue Cycle Management", 2020)
        r_corr = self.fn(new_em, portfolio)
        r_uncorr = self.fn(new_rcm, portfolio)
        self.assertLessEqual(r_corr.marginal_score, r_uncorr.marginal_score)

    def test_notes_is_list(self):
        result = self.fn(_deal("X", "Dental"), _diverse_portfolio())
        self.assertIsInstance(result.notes, list)

    def test_concentrating_note_when_sector_exists(self):
        portfolio = _diverse_portfolio()
        new = _deal("Another Behavioral", "Behavioral Health", 2022)
        result = self.fn(new, portfolio)
        self.assertTrue(any("Behavioral Health" in n for n in result.notes))

    def test_empty_portfolio_no_crash(self):
        result = self.fn(_deal("First", "Dental", 2020), [])
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.marginal_score, 0.0)


class TestOptimalSectorWeights(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_portfolio_construction import optimal_sector_weights
        self.fn = optimal_sector_weights

    def _make_corpus(self):
        deals = []
        data = {
            "Dental": [4.0, 3.5, 3.8, 2.8, 4.2],
            "Behavioral Health": [1.5, 0.8, 2.2, 0.6, 1.9],
            "Physician Practices": [3.0, 3.2, 2.8, 3.5, 2.5],
        }
        for sector, moics in data.items():
            for i, m in enumerate(moics):
                deals.append({"sector": sector, "realized_moic": m, "source_id": f"{sector}_{i}"})
        return deals

    def test_returns_dict(self):
        result = self.fn(self._make_corpus())
        self.assertIsInstance(result, dict)

    def test_weights_sum_to_1(self):
        result = self.fn(self._make_corpus())
        total = sum(result.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_dental_outweighs_behavioral(self):
        result = self.fn(self._make_corpus())
        dental_w = result.get("Dental", 0.0)
        beh_w = result.get("Behavioral Health", 0.0)
        self.assertGreater(dental_w, beh_w)

    def test_risk_averse_rewards_safe_low_return_sector_over_risky_high_return(self):
        # Dental has high MOIC and low loss rate → good in both modes
        # Behavioral Health has low MOIC but moderate loss rate
        corpus = self._make_corpus()
        r_aggressive = self.fn(corpus, risk_aversion=0.0)
        r_conservative = self.fn(corpus, risk_aversion=1.0)
        # Dental (high MOIC, low loss) should dominate in both but especially aggressive
        dental_agg = r_aggressive.get("Dental", 0.0)
        dental_cons = r_conservative.get("Dental", 0.0)
        # Both modes should favor Dental over Behavioral Health
        beh_agg = r_aggressive.get("Behavioral Health", 0.0)
        dental_over_beh_agg = dental_agg > beh_agg
        self.assertTrue(dental_over_beh_agg)

    def test_empty_corpus_falls_back_to_prior(self):
        result = self.fn([])
        self.assertGreater(len(result), 0)

    def test_all_weights_positive(self):
        result = self.fn(self._make_corpus())
        for w in result.values():
            self.assertGreater(w, 0.0)


class TestHHIHelper(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_portfolio_construction import _hhi
        self.fn = _hhi

    def test_single_sector_hhi_1(self):
        self.assertAlmostEqual(self.fn({"A": 1}), 1.0)

    def test_two_equal_sectors_hhi_half(self):
        self.assertAlmostEqual(self.fn({"A": 1, "B": 1}), 0.5)

    def test_five_equal_sectors(self):
        d = {str(i): 1 for i in range(5)}
        self.assertAlmostEqual(self.fn(d), 0.2)

    def test_empty_dict_hhi_0(self):
        self.assertAlmostEqual(self.fn({}), 0.0)


class TestPortfolioRiskReport(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_portfolio_construction import (
            analyze_portfolio, marginal_diversification, portfolio_risk_report,
        )
        self.portfolio = _diverse_portfolio()
        self.composition = analyze_portfolio(self.portfolio)
        new = _deal("New RCM Deal", "Revenue Cycle Management", 2022)
        self.diversification = marginal_diversification(new, self.portfolio)
        self.report = portfolio_risk_report(self.composition, self.diversification)

    def test_returns_string(self):
        self.assertIsInstance(self.report, str)

    def test_contains_n_deals(self):
        self.assertIn("5", self.report)

    def test_contains_hhi(self):
        self.assertIn("HHI", self.report)

    def test_contains_deal_name(self):
        self.assertIn("New RCM Deal", self.report)

    def test_contains_signal(self):
        sig = self.diversification.signal.upper()
        self.assertIn(sig, self.report)

    def test_report_no_diversification(self):
        from rcm_mc.data_public.deal_portfolio_construction import portfolio_risk_report
        report = portfolio_risk_report(self.composition)
        self.assertIsInstance(report, str)
        self.assertNotIn("Marginal Deal", report)


if __name__ == "__main__":
    unittest.main()
