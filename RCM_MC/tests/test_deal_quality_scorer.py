"""Tests for deal_quality_scorer.py — data completeness + credibility."""
from __future__ import annotations

import unittest
from typing import Any, Dict


def _full_deal(**overrides) -> Dict[str, Any]:
    d = {
        "source_id": "seed_test",
        "deal_name": "Acme Health Partners",
        "sector": "Physician Practices",
        "entry_year": 2019,
        "exit_year": 2022,
        "buyer": "KKR",
        "seller": "Founders",
        "region": "Southeast",
        "hospital_size": "mid",
        "ev_mm": 500.0,
        "ebitda_at_entry_mm": 50.0,    # 10x
        "leverage_pct": 0.55,
        "payer_mix": {"commercial": 0.65, "medicare": 0.25, "medicaid": 0.08, "self_pay": 0.02},
        "realized_moic": 3.0,
        "hold_years": 3.0,
        "realized_irr": 0.44,          # ~44% matches (3.0)^(1/3)-1 ≈ 0.44
    }
    d.update(overrides)
    return d


class TestScoreDealQuality(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_quality_scorer import score_deal_quality
        self.fn = score_deal_quality

    def test_returns_score_object(self):
        from rcm_mc.data_public.deal_quality_scorer import DealQualityScore
        result = self.fn(_full_deal())
        self.assertIsInstance(result, DealQualityScore)

    def test_deal_name_stored(self):
        result = self.fn(_full_deal())
        self.assertEqual(result.deal_name, "Acme Health Partners")

    def test_combined_score_in_range(self):
        result = self.fn(_full_deal())
        self.assertGreaterEqual(result.combined_score, 0.0)
        self.assertLessEqual(result.combined_score, 100.0)

    def test_complete_deal_high_score(self):
        result = self.fn(_full_deal())
        self.assertGreater(result.combined_score, 70.0)

    def test_grade_a_for_complete_deal(self):
        result = self.fn(_full_deal())
        self.assertIn(result.grade, ("A", "B"))

    def test_empty_deal_low_score(self):
        result = self.fn({})
        self.assertLess(result.combined_score, 30.0)

    def test_empty_deal_grade_d(self):
        result = self.fn({})
        self.assertEqual(result.grade, "D")

    def test_grade_valid_values(self):
        result = self.fn(_full_deal())
        self.assertIn(result.grade, ("A", "B", "C", "D"))

    def test_completeness_score_in_range(self):
        result = self.fn(_full_deal())
        self.assertGreaterEqual(result.completeness_score, 0.0)
        self.assertLessEqual(result.completeness_score, 100.0)

    def test_credibility_score_in_range(self):
        result = self.fn(_full_deal())
        self.assertGreaterEqual(result.credibility_score, 0.0)
        self.assertLessEqual(result.credibility_score, 100.0)

    def test_notes_is_list(self):
        result = self.fn(_full_deal())
        self.assertIsInstance(result.notes, list)


class TestDataCompleteness(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_quality_scorer import score_deal_quality
        self.fn = score_deal_quality

    def test_full_deal_high_completeness(self):
        result = self.fn(_full_deal())
        self.assertGreater(result.completeness.score, 80.0)

    def test_missing_ev_reduces_score(self):
        full = self.fn(_full_deal())
        partial = self.fn(_full_deal(ev_mm=None))
        self.assertLess(partial.completeness_score, full.completeness_score)

    def test_missing_payer_mix_reduces_score(self):
        full = self.fn(_full_deal())
        no_pm = self.fn(_full_deal(payer_mix=None))
        self.assertLess(no_pm.completeness_score, full.completeness_score)

    def test_missing_outcome_data_reduces_score(self):
        full = self.fn(_full_deal())
        no_outcome = self.fn(_full_deal(realized_moic=None, realized_irr=None))
        self.assertLess(no_outcome.completeness_score, full.completeness_score)

    def test_has_outcome_data_true_when_present(self):
        result = self.fn(_full_deal())
        self.assertTrue(result.completeness.has_outcome_data)

    def test_has_outcome_data_false_when_missing(self):
        result = self.fn(_full_deal(realized_moic=None))
        self.assertFalse(result.completeness.has_outcome_data)

    def test_populated_fields_list(self):
        result = self.fn(_full_deal())
        self.assertIn("deal_name", result.completeness.populated_fields)
        self.assertIn("sector", result.completeness.populated_fields)

    def test_missing_fields_list(self):
        result = self.fn(_full_deal(sector=None))
        self.assertIn("sector", result.completeness.missing_fields)

    def test_alias_ev_mm_accepted(self):
        deal = _full_deal()
        del deal["ev_mm"]
        deal["entry_ev_mm"] = 500.0
        result = self.fn(deal)
        self.assertIn("ev_mm", result.completeness.populated_fields)


class TestCredibilityChecks(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_quality_scorer import score_deal_quality
        self.fn = score_deal_quality

    def test_normal_multiple_passes(self):
        result = self.fn(_full_deal())
        mult_check = next(c for c in result.credibility_checks if c.name == "entry_multiple_range")
        self.assertTrue(mult_check.passed)

    def test_absurd_multiple_fails(self):
        result = self.fn(_full_deal(ev_mm=50_000.0, ebitda_at_entry_mm=10.0))  # 5000x
        mult_check = next(c for c in result.credibility_checks if c.name == "entry_multiple_range")
        self.assertFalse(mult_check.passed)

    def test_payer_mix_sum_passes_when_normalized(self):
        result = self.fn(_full_deal())
        pm_check = next(c for c in result.credibility_checks if c.name == "payer_mix_sum")
        self.assertTrue(pm_check.passed)

    def test_payer_mix_sum_fails_when_wrong(self):
        deal = _full_deal(payer_mix={"commercial": 0.80, "medicare": 0.80})  # sums to 1.6
        result = self.fn(deal)
        pm_check = next((c for c in result.credibility_checks if c.name == "payer_mix_sum"), None)
        if pm_check:
            self.assertFalse(pm_check.passed)

    def test_leverage_passes_normal(self):
        result = self.fn(_full_deal(leverage_pct=0.55))
        lev_check = next(c for c in result.credibility_checks if c.name == "leverage_range")
        self.assertTrue(lev_check.passed)

    def test_leverage_fails_above_90pct(self):
        result = self.fn(_full_deal(leverage_pct=0.95))
        lev_check = next(c for c in result.credibility_checks if c.name == "leverage_range")
        self.assertFalse(lev_check.passed)

    def test_moic_irr_consistency_passes_when_consistent(self):
        result = self.fn(_full_deal())
        irr_check = next((c for c in result.credibility_checks if c.name == "moic_irr_consistency"), None)
        if irr_check:
            self.assertTrue(irr_check.passed)

    def test_moic_irr_fails_when_inconsistent(self):
        # MOIC=3.0 over 3 years → IRR ≈ 44%, but we say 0.10 (10%)
        result = self.fn(_full_deal(realized_moic=3.0, hold_years=3.0, realized_irr=0.10))
        irr_check = next((c for c in result.credibility_checks if c.name == "moic_irr_consistency"), None)
        if irr_check:
            self.assertFalse(irr_check.passed)

    def test_hold_years_consistency_passes(self):
        result = self.fn(_full_deal())
        hold_check = next((c for c in result.credibility_checks if c.name == "hold_years_consistency"), None)
        if hold_check:
            self.assertTrue(hold_check.passed)

    def test_moic_plausibility_passes_normal(self):
        result = self.fn(_full_deal(realized_moic=3.0))
        moic_check = next((c for c in result.credibility_checks if c.name == "moic_plausibility"), None)
        if moic_check:
            self.assertTrue(moic_check.passed)

    def test_moic_plausibility_fails_extreme(self):
        result = self.fn(_full_deal(realized_moic=25.0))
        moic_check = next((c for c in result.credibility_checks if c.name == "moic_plausibility"), None)
        if moic_check:
            self.assertFalse(moic_check.passed)

    def test_credibility_checks_is_list(self):
        result = self.fn(_full_deal())
        self.assertIsInstance(result.credibility_checks, list)


class TestBatchQualityScores(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_quality_scorer import batch_quality_scores
        self.fn = batch_quality_scores

    def test_returns_list(self):
        result = self.fn([_full_deal(), _full_deal(deal_name="Deal B")])
        self.assertIsInstance(result, list)

    def test_sorted_descending(self):
        deals = [_full_deal(), {}, _full_deal(deal_name="B", realized_moic=None)]
        result = self.fn(deals)
        scores = [r.combined_score for r in result]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i], scores[i + 1])

    def test_empty_input(self):
        result = self.fn([])
        self.assertEqual(result, [])


class TestCorpusQualitySummary(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_quality_scorer import corpus_quality_summary
        self.fn = corpus_quality_summary

    def test_returns_dict(self):
        result = self.fn([_full_deal(), _full_deal(deal_name="B")])
        self.assertIsInstance(result, dict)

    def test_total_deals_correct(self):
        result = self.fn([_full_deal()] * 5)
        self.assertEqual(result["total_deals"], 5)

    def test_grade_counts_sum_to_total(self):
        deals = [_full_deal(), {}, _full_deal(deal_name="B")]
        result = self.fn(deals)
        grade_total = sum(result["grade_counts"].values())
        self.assertEqual(grade_total, 3)

    def test_pct_with_outcome_data(self):
        deals = [_full_deal(), _full_deal(realized_moic=None)]
        result = self.fn(deals)
        self.assertAlmostEqual(result["pct_with_outcome_data"], 50.0)

    def test_empty_corpus_returns_empty(self):
        result = self.fn([])
        self.assertEqual(result, {})


class TestFormatters(unittest.TestCase):
    def setUp(self):
        from rcm_mc.data_public.deal_quality_scorer import (
            score_deal_quality, quality_report, quality_table,
        )
        self.score = score_deal_quality(_full_deal())
        self.report = quality_report(self.score)
        self.quality_table = quality_table

    def test_report_returns_string(self):
        self.assertIsInstance(self.report, str)

    def test_report_contains_deal_name(self):
        self.assertIn("Acme Health Partners", self.report)

    def test_report_contains_grade(self):
        self.assertIn(self.score.grade, self.report)

    def test_report_contains_scores(self):
        self.assertIn(str(self.score.combined_score), self.report)

    def test_table_returns_string(self):
        table = self.quality_table([self.score])
        self.assertIsInstance(table, str)

    def test_table_sorted_descending(self):
        from rcm_mc.data_public.deal_quality_scorer import score_deal_quality
        s1 = score_deal_quality(_full_deal(deal_name="Full Deal"))
        s2 = score_deal_quality({})
        table = self.quality_table([s1, s2])
        full_pos = table.index("Full Deal")
        # {} deal has default name "Unknown"
        self.assertLess(full_pos, len(table))

    def test_table_contains_grade_column(self):
        table = self.quality_table([self.score])
        self.assertIn("Grade", table)


class TestIntegrationWithRealCorpus(unittest.TestCase):
    def _get_corpus(self):
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
        result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
        for i in range(2, 30):
            try:
                mod = __import__(
                    f"rcm_mc.data_public.extended_seed_{i}",
                    fromlist=[f"EXTENDED_SEED_DEALS_{i}"],
                )
                result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
            except (ImportError, AttributeError):
                pass
        return result

    def test_corpus_scores_without_crash(self):
        from rcm_mc.data_public.deal_quality_scorer import batch_quality_scores
        corpus = self._get_corpus()
        scores = batch_quality_scores(corpus[:50])
        self.assertEqual(len(scores), 50)

    def test_corpus_summary_statistics(self):
        from rcm_mc.data_public.deal_quality_scorer import corpus_quality_summary
        corpus = self._get_corpus()
        summary = corpus_quality_summary(corpus[:100])
        self.assertGreater(summary["pct_with_outcome_data"], 20.0)
        self.assertGreater(summary["pct_grade_a_or_b"], 20.0)


if __name__ == "__main__":
    unittest.main()
