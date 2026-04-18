"""Tests for corpus_vintage_risk_model.py — vintage risk by entry year."""
from __future__ import annotations

import unittest
from typing import Any, Dict, List


def _make_realized_deal(year: int, moic: float, **kwargs) -> Dict[str, Any]:
    d = {
        "source_id": f"deal_{year}_{moic}",
        "entry_year": year,
        "realized_moic": moic,
        "deal_name": f"Deal {year} {moic}x",
    }
    d.update(kwargs)
    return d


def _make_corpus() -> List[Dict[str, Any]]:
    """Synthetic corpus spanning 2010-2022 with realistic MOIC spread."""
    deals = []
    vintage_data = {
        2010: [2.5, 3.1, 2.8, 1.9, 4.2],
        2012: [3.0, 3.5, 2.2, 4.0, 2.9],
        2014: [2.8, 3.2, 2.6, 3.8, 1.5],
        2015: [1.8, 2.1, 1.5, 0.8, 2.4],
        2017: [3.5, 2.9, 4.1, 3.2, 2.7],
        2019: [2.5, 2.8, 3.0, 2.2, 1.9],
        2020: [0.4, 0.9, 1.8, 2.2, 1.2],
        2021: [0.3, 0.9, 1.5, 2.0, 1.1],
    }
    for year, moics in vintage_data.items():
        for moic in moics:
            deals.append(_make_realized_deal(year, moic))
    return deals


class TestComputeVintageStats(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.corpus_vintage_risk_model import compute_vintage_stats
        self.fn = compute_vintage_stats
        self.corpus = _make_corpus()

    def test_returns_dict_by_year(self):
        stats = self.fn(self.corpus)
        self.assertIsInstance(stats, dict)
        self.assertIn(2010, stats)

    def test_n_correct(self):
        stats = self.fn(self.corpus)
        self.assertEqual(stats[2010].n, 5)

    def test_moic_p50_positive(self):
        stats = self.fn(self.corpus)
        for yr, v in stats.items():
            self.assertGreater(v.moic_p50, 0.0)

    def test_p25_leq_p50_leq_p75(self):
        stats = self.fn(self.corpus)
        for yr, v in stats.items():
            if v.moic_p25 and v.moic_p75:
                self.assertLessEqual(v.moic_p25, v.moic_p50)
                self.assertLessEqual(v.moic_p50, v.moic_p75)

    def test_loss_rate_between_0_and_1(self):
        stats = self.fn(self.corpus)
        for yr, v in stats.items():
            self.assertGreaterEqual(v.loss_rate, 0.0)
            self.assertLessEqual(v.loss_rate, 1.0)

    def test_2020_high_loss_rate(self):
        stats = self.fn(self.corpus)
        # 2020 has 0.4, 0.9 → 2/5 = 40% loss rate
        self.assertGreater(stats[2020].loss_rate, 0.2)

    def test_2012_low_loss_rate(self):
        stats = self.fn(self.corpus)
        # All 2012 deals > 1.0x
        self.assertEqual(stats[2012].loss_rate, 0.0)

    def test_regime_assigned(self):
        stats = self.fn(self.corpus)
        self.assertEqual(stats[2020].regime, "contraction")
        self.assertEqual(stats[2012].regime, "expansion")

    def test_no_realized_moic_excluded(self):
        corpus = [{"entry_year": 2020, "deal_name": "Unrealized"}]
        stats = self.fn(corpus)
        self.assertEqual(len(stats), 0)

    def test_empty_corpus_returns_empty(self):
        stats = self.fn([])
        self.assertEqual(stats, {})


class TestAnalyzeVintage(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.corpus_vintage_risk_model import analyze_vintage, VintageRiskResult
        self.fn = analyze_vintage
        self.VintageRiskResult = VintageRiskResult
        self.corpus = _make_corpus()

    def test_returns_vintage_risk_result(self):
        result = self.fn(2019, self.corpus)
        self.assertIsInstance(result, self.VintageRiskResult)

    def test_entry_year_stored(self):
        result = self.fn(2019, self.corpus)
        self.assertEqual(result.entry_year, 2019)

    def test_regime_correct(self):
        result = self.fn(2020, self.corpus)
        self.assertEqual(result.regime, "contraction")

    def test_signal_valid(self):
        result = self.fn(2019, self.corpus)
        self.assertIn(result.signal, ("green", "yellow", "red"))

    def test_peak_year_higher_risk_than_expansion(self):
        r_peak = self.fn(2021, self.corpus)
        r_exp = self.fn(2012, self.corpus)
        self.assertGreater(r_peak.corpus_adjusted_score, r_exp.corpus_adjusted_score)

    def test_contraction_year_elevated_risk(self):
        result = self.fn(2020, self.corpus)
        self.assertGreater(result.corpus_adjusted_score, 30.0)

    def test_score_in_0_100_range(self):
        for year in [2010, 2015, 2017, 2020, 2021]:
            result = self.fn(year, self.corpus)
            self.assertGreaterEqual(result.corpus_adjusted_score, 0.0)
            self.assertLessEqual(result.corpus_adjusted_score, 100.0)

    def test_notes_is_list(self):
        result = self.fn(2021, self.corpus)
        self.assertIsInstance(result.notes, list)

    def test_peak_year_has_notes(self):
        result = self.fn(2021, self.corpus)
        self.assertTrue(any("peak" in n.lower() for n in result.notes))

    def test_corpus_moic_p50_present(self):
        result = self.fn(2019, self.corpus)
        self.assertIsNotNone(result.corpus_moic_p50)
        self.assertGreater(result.corpus_moic_p50, 0.0)

    def test_comparable_vintage_present(self):
        result = self.fn(2019, self.corpus)
        self.assertIsNotNone(result.comparable_vintage)

    def test_unknown_year_no_crash(self):
        result = self.fn(1999, self.corpus)
        self.assertIsNotNone(result)
        self.assertEqual(result.regime, "unknown")

    def test_empty_corpus_no_crash(self):
        result = self.fn(2019, [])
        self.assertIsNotNone(result)
        self.assertIsNone(result.comparable_vintage)


class TestVintageConcentrationRisk(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.corpus_vintage_risk_model import vintage_concentration_risk
        self.fn = vintage_concentration_risk
        self.corpus = _make_corpus()

    def _make_portfolio(self, years: list) -> List[Dict[str, Any]]:
        return [{"deal_name": f"Deal {i}", "entry_year": yr} for i, yr in enumerate(years)]

    def test_returns_dict(self):
        portfolio = self._make_portfolio([2017, 2018, 2019])
        result = self.fn(portfolio, self.corpus)
        self.assertIsInstance(result, dict)

    def test_vintage_counts_correct(self):
        portfolio = self._make_portfolio([2017, 2017, 2019])
        result = self.fn(portfolio, self.corpus)
        self.assertEqual(result["vintage_counts"][2017], 2)
        self.assertEqual(result["vintage_counts"][2019], 1)

    def test_hhi_between_0_and_1(self):
        portfolio = self._make_portfolio([2017, 2018, 2019, 2020])
        result = self.fn(portfolio, self.corpus)
        self.assertGreaterEqual(result["concentration_hhi"], 0.0)
        self.assertLessEqual(result["concentration_hhi"], 1.0)

    def test_single_vintage_max_hhi(self):
        portfolio = self._make_portfolio([2021, 2021, 2021])
        result = self.fn(portfolio, self.corpus)
        self.assertAlmostEqual(result["concentration_hhi"], 1.0)

    def test_equal_spread_low_hhi(self):
        portfolio = self._make_portfolio([2010, 2012, 2014, 2017, 2019])
        result = self.fn(portfolio, self.corpus)
        self.assertLess(result["concentration_hhi"], 0.35)

    def test_dominant_vintage_identified(self):
        portfolio = self._make_portfolio([2021, 2021, 2021, 2019])
        result = self.fn(portfolio, self.corpus)
        self.assertEqual(result["dominant_vintage"], 2021)

    def test_peak_heavy_portfolio_higher_risk(self):
        peak_portfolio = self._make_portfolio([2021, 2021, 2022, 2022])
        exp_portfolio = self._make_portfolio([2012, 2013, 2014, 2017])
        r_peak = self.fn(peak_portfolio, self.corpus)
        r_exp = self.fn(exp_portfolio, self.corpus)
        self.assertGreater(r_peak["weighted_vintage_risk"], r_exp["weighted_vintage_risk"])

    def test_empty_portfolio_no_crash(self):
        result = self.fn([], self.corpus)
        self.assertEqual(result["concentration_hhi"], 0.0)

    def test_signal_present(self):
        portfolio = self._make_portfolio([2019])
        result = self.fn(portfolio, self.corpus)
        self.assertIn(result["risk_signal"], ("green", "yellow", "red"))


class TestFormatters(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.corpus_vintage_risk_model import (
            analyze_vintage, vintage_heatmap, vintage_risk_report,
        )
        self.corpus = _make_corpus()
        self.result = analyze_vintage(2021, self.corpus)
        self.heatmap = vintage_heatmap
        self.report = vintage_risk_report

    def test_heatmap_returns_string(self):
        s = self.heatmap(self.corpus)
        self.assertIsInstance(s, str)

    def test_heatmap_contains_years(self):
        s = self.heatmap(self.corpus)
        for yr in [2010, 2012, 2021]:
            self.assertIn(str(yr), s)

    def test_heatmap_empty_corpus(self):
        s = self.heatmap([])
        self.assertIn("No realized", s)

    def test_report_returns_string(self):
        s = self.report(self.result, self.corpus)
        self.assertIsInstance(s, str)

    def test_report_contains_year(self):
        s = self.report(self.result, self.corpus)
        self.assertIn("2021", s)

    def test_report_contains_signal(self):
        s = self.report(self.result, self.corpus)
        self.assertIn(self.result.signal.upper(), s)

    def test_report_contains_regime(self):
        s = self.report(self.result, self.corpus)
        self.assertIn("peak", s.lower())


class TestIntegrationWithRealCorpus(unittest.TestCase):
    def _get_corpus(self):
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
        result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
        for i in range(2, 28):
            try:
                mod = __import__(
                    f"rcm_mc.data_public.extended_seed_{i}",
                    fromlist=[f"EXTENDED_SEED_DEALS_{i}"],
                )
                result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
            except (ImportError, AttributeError):
                pass
        return result

    def test_real_corpus_vintage_stats(self):
        from rcm_mc.data_public.corpus_vintage_risk_model import compute_vintage_stats
        corpus = self._get_corpus()
        stats = compute_vintage_stats(corpus)
        self.assertGreater(len(stats), 5)

    def test_real_corpus_2021_elevated_risk(self):
        from rcm_mc.data_public.corpus_vintage_risk_model import analyze_vintage
        corpus = self._get_corpus()
        result = analyze_vintage(2021, corpus)
        # 2021 was peak SPAC/ZIRP; should be elevated risk
        self.assertGreater(result.corpus_adjusted_score, 40.0)

    def test_real_corpus_2017_lower_risk_than_2021(self):
        from rcm_mc.data_public.corpus_vintage_risk_model import analyze_vintage
        corpus = self._get_corpus()
        r2017 = analyze_vintage(2017, corpus)
        r2021 = analyze_vintage(2021, corpus)
        self.assertLess(r2017.corpus_adjusted_score, r2021.corpus_adjusted_score)


if __name__ == "__main__":
    unittest.main()
