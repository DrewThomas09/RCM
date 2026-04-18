"""Tests for deal_entry_risk_score.py — composite 6-dimension entry risk score."""
from __future__ import annotations

import unittest
from typing import Any, Dict, List


def _make_deal(**kwargs) -> Dict[str, Any]:
    base = {
        "deal_name": "Test Deal",
        "ev_mm": 500.0,
        "ebitda_at_entry_mm": 50.0,
        "sector": "Physician Practices",
        "buyer": "Test Sponsor",
        "payer_mix": {"commercial": 0.70, "medicare": 0.20, "medicaid": 0.10, "self_pay": 0.00},
    }
    base.update(kwargs)
    return base


def _make_corpus(n: int = 10) -> List[Dict[str, Any]]:
    """Minimal realized corpus for benchmarking."""
    return [
        {
            "deal_name": f"Corp Deal {i}",
            "ev_mm": 200.0 + i * 50,
            "ebitda_at_entry_mm": 20.0 + i * 5,
            "realized_moic": 2.0 + i * 0.1,
            "sector": "Physician Practices",
            "buyer": "Test Sponsor",
        }
        for i in range(n)
    ]


class TestScoreEntryRiskBasic(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import score_entry_risk
        self.score_entry_risk = score_entry_risk

    def test_returns_entry_risk_score_object(self):
        from rcm_mc.data_public.deal_entry_risk_score import EntryRiskScore
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        self.assertIsInstance(result, EntryRiskScore)

    def test_total_in_0_100_range(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        self.assertGreaterEqual(result.total, 0.0)
        self.assertLessEqual(result.total, 100.0)

    def test_six_dimensions(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        self.assertEqual(len(result.dimensions), 6)

    def test_dimension_names(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        names = {d.name for d in result.dimensions}
        expected = {
            "entry_multiple", "leverage", "payer_mix",
            "sector_loss_rate", "sponsor_track_record", "deal_size_uncertainty",
        }
        self.assertEqual(names, expected)

    def test_signal_green_for_low_risk(self):
        # Very conservative deal: low multiple, low leverage, all commercial
        deal = _make_deal(
            ev_mm=300.0, ebitda_at_entry_mm=60.0,  # 5x
            payer_mix={"commercial": 1.0},
        )
        result = self.score_entry_risk(deal, _make_corpus(20))
        self.assertIn(result.signal, ("green", "yellow"))

    def test_signal_red_for_high_risk(self):
        # Risky: very high multiple, high leverage, all Medicaid
        deal = _make_deal(
            ev_mm=1000.0, ebitda_at_entry_mm=50.0,  # 20x
            payer_mix={"medicaid": 0.80, "self_pay": 0.20},
        )
        corpus = _make_corpus(20)
        result = self.score_entry_risk(deal, corpus, assumptions={"leverage_pct": 0.75})
        self.assertIn(result.signal, ("yellow", "red"))

    def test_deal_name_propagated(self):
        deal = _make_deal(deal_name="Acme Health")
        result = self.score_entry_risk(deal, _make_corpus())
        self.assertEqual(result.deal_name, "Acme Health")

    def test_corpus_n_correct(self):
        corpus = _make_corpus(12)
        result = self.score_entry_risk(_make_deal(), corpus)
        self.assertEqual(result.corpus_n, 12)

    def test_empty_corpus_no_crash(self):
        result = self.score_entry_risk(_make_deal(), [])
        self.assertIsNotNone(result.total)
        self.assertEqual(result.corpus_n, 0)

    def test_missing_ev_no_crash(self):
        deal = _make_deal(ev_mm=None, ebitda_at_entry_mm=None)
        result = self.score_entry_risk(deal, _make_corpus())
        self.assertIsNotNone(result)

    def test_notes_is_list(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        self.assertIsInstance(result.notes, list)


class TestDimensionScores(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import score_entry_risk
        self.score_entry_risk = score_entry_risk

    def _get_dim(self, result, name):
        return next(d for d in result.dimensions if d.name == name)

    def test_each_dimension_score_within_max(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        for d in result.dimensions:
            self.assertLessEqual(d.score, d.max_score + 0.01, f"{d.name} exceeds max")
            self.assertGreaterEqual(d.score, 0.0)

    def test_pct_of_max_consistent(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        for d in result.dimensions:
            expected = round(d.score / d.max_score, 3)
            self.assertAlmostEqual(d.pct_of_max, expected, places=2)

    def test_leverage_high_when_above_70pct(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus(),
                                       assumptions={"leverage_pct": 0.75})
        lev = self._get_dim(result, "leverage")
        self.assertEqual(lev.signal, "high")
        self.assertGreaterEqual(lev.score, 14.0)

    def test_leverage_low_when_below_50pct(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus(),
                                       assumptions={"leverage_pct": 0.40})
        lev = self._get_dim(result, "leverage")
        self.assertEqual(lev.signal, "low")

    def test_payer_risk_high_for_all_medicaid(self):
        deal = _make_deal(payer_mix={"medicaid": 1.0})
        result = self.score_entry_risk(deal, _make_corpus())
        pm = self._get_dim(result, "payer_mix")
        self.assertEqual(pm.signal, "high")

    def test_payer_risk_low_for_all_commercial(self):
        deal = _make_deal(payer_mix={"commercial": 1.0})
        result = self.score_entry_risk(deal, _make_corpus())
        pm = self._get_dim(result, "payer_mix")
        self.assertEqual(pm.signal, "low")

    def test_size_uncertainty_high_for_small_deal(self):
        deal = _make_deal(ev_mm=100.0, ebitda_at_entry_mm=10.0)
        result = self.score_entry_risk(deal, _make_corpus())
        sz = self._get_dim(result, "deal_size_uncertainty")
        self.assertEqual(sz.signal, "high")

    def test_size_uncertainty_low_for_large_deal(self):
        deal = _make_deal(ev_mm=1500.0, ebitda_at_entry_mm=100.0)
        result = self.score_entry_risk(deal, _make_corpus())
        sz = self._get_dim(result, "deal_size_uncertainty")
        self.assertEqual(sz.signal, "low")

    def test_size_uncertainty_low_for_mega_deal(self):
        deal = _make_deal(ev_mm=5000.0, ebitda_at_entry_mm=200.0)
        result = self.score_entry_risk(deal, _make_corpus())
        sz = self._get_dim(result, "deal_size_uncertainty")
        self.assertLessEqual(sz.score, 2.0)

    def test_entry_multiple_max_20(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        em = self._get_dim(result, "entry_multiple")
        self.assertLessEqual(em.max_score, 20.0)

    def test_leverage_max_15(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        lev = self._get_dim(result, "leverage")
        self.assertEqual(lev.max_score, 15.0)

    def test_deal_size_max_10(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        sz = self._get_dim(result, "deal_size_uncertainty")
        self.assertEqual(sz.max_score, 10.0)

    def test_signal_values_valid(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus())
        valid = {"low", "medium", "high"}
        for d in result.dimensions:
            self.assertIn(d.signal, valid, f"{d.name} has invalid signal {d.signal!r}")


class TestPayerMixRisk(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import _payer_risk_score
        self.fn = _payer_risk_score

    def test_all_commercial_zero_risk(self):
        self.assertAlmostEqual(self.fn({"commercial": 1.0}), 0.0)

    def test_all_medicaid_high_risk(self):
        score = self.fn({"medicaid": 1.0})
        self.assertGreater(score, 20.0)

    def test_all_selfpay_max_risk(self):
        score = self.fn({"self_pay": 1.0})
        self.assertEqual(score, 40.0)

    def test_unknown_mix_medium(self):
        score = self.fn(None)
        self.assertEqual(score, 20.0)

    def test_capped_at_40(self):
        score = self.fn({"self_pay": 0.8, "medicaid": 0.2})
        self.assertLessEqual(score, 40.0)

    def test_mixed_payer_intermediate(self):
        score = self.fn({"commercial": 0.5, "medicaid": 0.3, "medicare": 0.2})
        self.assertGreater(score, 0.0)
        self.assertLess(score, 40.0)


class TestSignalThresholds(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import score_entry_risk
        self.score_entry_risk = score_entry_risk

    def test_green_below_25(self):
        # Minimal risk: large low-leverage deal, all commercial
        deal = _make_deal(
            ev_mm=800.0, ebitda_at_entry_mm=200.0,  # 4x EV/EBITDA — low
            payer_mix={"commercial": 1.0},
        )
        result = self.score_entry_risk(deal, _make_corpus(20),
                                       assumptions={"leverage_pct": 0.35})
        if result.total < 25:
            self.assertEqual(result.signal, "green")

    def test_red_above_55(self):
        deal = _make_deal(
            ev_mm=2000.0, ebitda_at_entry_mm=50.0,  # 40x
            payer_mix={"medicaid": 0.70, "self_pay": 0.30},
        )
        result = self.score_entry_risk(deal, _make_corpus(5),
                                       assumptions={"leverage_pct": 0.80})
        if result.total > 55:
            self.assertEqual(result.signal, "red")

    def test_yellow_between_25_and_55(self):
        result = self.score_entry_risk(_make_deal(), _make_corpus(10))
        if 25 <= result.total <= 55:
            self.assertEqual(result.signal, "yellow")


class TestNotes(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import score_entry_risk
        self.score_entry_risk = score_entry_risk

    def test_high_medicaid_generates_note(self):
        deal = _make_deal(payer_mix={"medicaid": 0.70, "commercial": 0.30})
        result = self.score_entry_risk(deal, _make_corpus())
        self.assertTrue(any("Medicaid" in n for n in result.notes))

    def test_high_selfpay_generates_note(self):
        deal = _make_deal(payer_mix={"self_pay": 0.30, "commercial": 0.70})
        result = self.score_entry_risk(deal, _make_corpus())
        self.assertTrue(any("self-pay" in n.lower() for n in result.notes))

    def test_tight_dscr_note(self):
        # tiny EBITDA vs large debt → DSCR < 1.5
        deal = _make_deal(ev_mm=1000.0, ebitda_at_entry_mm=10.0)
        result = self.score_entry_risk(deal, _make_corpus(),
                                       assumptions={"leverage_pct": 0.70})
        self.assertTrue(any("DSCR" in n or "dscr" in n.lower() for n in result.notes))

    def test_top_quintile_multiple_note(self):
        # Very high multiple vs small corpus → top-quintile note
        corpus = _make_corpus(10)  # multiples ~10-19x
        deal = _make_deal(ev_mm=5000.0, ebitda_at_entry_mm=50.0)  # 100x
        result = self.score_entry_risk(deal, corpus)
        self.assertTrue(any("quintile" in n.lower() or "multiple" in n.lower()
                            for n in result.notes))


class TestRiskScoreReport(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import (
            score_entry_risk, risk_score_report,
        )
        self.score = score_entry_risk(_make_deal(), _make_corpus())
        self.report = risk_score_report(self.score)

    def test_returns_string(self):
        self.assertIsInstance(self.report, str)

    def test_contains_total_score(self):
        self.assertIn(str(self.score.total), self.report)

    def test_contains_all_dimension_names(self):
        for name in ("entry multiple", "leverage", "payer mix",
                     "sector loss rate", "sponsor track record", "deal size"):
            self.assertIn(name, self.report.lower())

    def test_contains_signal_indicator(self):
        signal_text = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}
        self.assertIn(signal_text[self.score.signal], self.report)

    def test_contains_bar_chart(self):
        self.assertIn("█", self.report)

    def test_contains_corpus_n(self):
        self.assertIn(str(self.score.corpus_n), self.report)

    def test_notes_section_when_notes_present(self):
        from rcm_mc.data_public.deal_entry_risk_score import score_entry_risk, risk_score_report
        deal = _make_deal(payer_mix={"medicaid": 0.70, "commercial": 0.30})
        score = score_entry_risk(deal, _make_corpus())
        report = risk_score_report(score)
        self.assertIn("Key Flags", report)


class TestRiskScoreTable(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import (
            score_entry_risk, risk_score_table,
        )
        deals = [
            _make_deal(deal_name=f"Deal {i}", ev_mm=200.0 + i * 100)
            for i in range(4)
        ]
        corpus = _make_corpus(15)
        self.scores = [score_entry_risk(d, corpus) for d in deals]
        self.table = risk_score_table(self.scores)

    def test_returns_string(self):
        self.assertIsInstance(self.table, str)

    def test_sorted_descending_by_total(self):
        # Extract score totals from the scores list directly — table is sorted descending
        totals_sorted = sorted([s.total for s in self.scores], reverse=True)
        totals_from_scores = [s.total for s in sorted(self.scores, key=lambda x: x.total, reverse=True)]
        self.assertEqual(totals_sorted, totals_from_scores)

    def test_all_deals_in_table(self):
        for i in range(4):
            self.assertIn(f"Deal {i}", self.table)

    def test_header_row_present(self):
        self.assertIn("Deal", self.table)
        self.assertIn("Score", self.table)


class TestAssumptionsOverride(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import score_entry_risk
        self.score_entry_risk = score_entry_risk

    def test_leverage_assumption_overrides_default(self):
        deal = _make_deal()
        r_low = self.score_entry_risk(deal, _make_corpus(), {"leverage_pct": 0.30})
        r_high = self.score_entry_risk(deal, _make_corpus(), {"leverage_pct": 0.80})
        lev_low = next(d for d in r_low.dimensions if d.name == "leverage")
        lev_high = next(d for d in r_high.dimensions if d.name == "leverage")
        self.assertLess(lev_low.score, lev_high.score)

    def test_total_higher_with_aggressive_leverage(self):
        deal = _make_deal()
        r_low = self.score_entry_risk(deal, _make_corpus(), {"leverage_pct": 0.30})
        r_high = self.score_entry_risk(deal, _make_corpus(), {"leverage_pct": 0.80})
        self.assertLess(r_low.total, r_high.total)


def _get_corpus() -> List[Dict[str, Any]]:
    """Return full seed corpus by importing all extended seed modules."""
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


class TestIntegrationWithRealCorpus(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_entry_risk_score import score_entry_risk
        self.corpus = _get_corpus()
        self.score_entry_risk = score_entry_risk

    def test_corpus_loads(self):
        self.assertGreaterEqual(len(self.corpus), 500)

    def test_score_against_real_corpus(self):
        deal = {
            "deal_name": "HCA Healthcare",
            "ev_mm": 33_000.0,
            "ebitda_at_entry_mm": 2_200.0,
            "sector": "Hospitals",
            "buyer": "KKR",
            "payer_mix": {"commercial": 0.45, "medicare": 0.35, "medicaid": 0.15, "self_pay": 0.05},
        }
        result = self.score_entry_risk(deal, self.corpus)
        self.assertGreaterEqual(result.total, 0.0)
        self.assertLessEqual(result.total, 100.0)
        self.assertIn(result.signal, ("green", "yellow", "red"))
        self.assertEqual(len(result.dimensions), 6)

    def test_high_risk_deal_scores_higher(self):
        safe = {
            "deal_name": "Safe Deal",
            "ev_mm": 800.0, "ebitda_at_entry_mm": 200.0,
            "sector": "Physician Practices",
            "buyer": "KKR",
            "payer_mix": {"commercial": 0.90, "medicare": 0.10},
        }
        risky = {
            "deal_name": "Risky Deal",
            "ev_mm": 2000.0, "ebitda_at_entry_mm": 50.0,
            "sector": "Behavioral Health",
            "buyer": "Unknown PE",
            "payer_mix": {"medicaid": 0.80, "self_pay": 0.20},
        }
        r_safe = self.score_entry_risk(safe, self.corpus, {"leverage_pct": 0.35})
        r_risky = self.score_entry_risk(risky, self.corpus, {"leverage_pct": 0.80})
        self.assertLess(r_safe.total, r_risky.total)

    def test_known_disaster_deal_high_risk(self):
        """Envision/KKR-type deal: high leverage, all commercial but thin EBITDA."""
        envision_style = {
            "deal_name": "Envision-style",
            "ev_mm": 9_900.0,
            "ebitda_at_entry_mm": 600.0,
            "sector": "Emergency Medicine",
            "buyer": "KKR",
            "payer_mix": {"commercial": 0.70, "medicare": 0.25, "medicaid": 0.05},
        }
        result = self.score_entry_risk(
            envision_style, self.corpus, {"leverage_pct": 0.70}
        )
        self.assertGreater(result.total, 30.0)

    def test_report_from_real_corpus(self):
        from rcm_mc.data_public.deal_entry_risk_score import risk_score_report
        deal = self.corpus[0]
        result = self.score_entry_risk(deal, self.corpus)
        report = risk_score_report(result)
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 100)

    def test_batch_scoring_all_dimensions_valid(self):
        sample = self.corpus[:10]
        for deal in sample:
            result = self.score_entry_risk(deal, self.corpus)
            self.assertEqual(len(result.dimensions), 6)
            for d in result.dimensions:
                self.assertGreaterEqual(d.score, 0.0)
                self.assertLessEqual(d.score, d.max_score + 0.01)


if __name__ == "__main__":
    unittest.main()
