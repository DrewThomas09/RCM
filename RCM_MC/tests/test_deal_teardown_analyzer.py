"""Tests for deal_teardown_analyzer.py — MOIC attribution decomposer."""
from __future__ import annotations

import unittest


def _deal(source_id="t001", deal_name="Test Deal", ev_mm=1000.0,
          ebitda_mm=100.0, moic=3.0, hold=5.0, irr=0.25, **kw):
    d = {
        "source_id": source_id,
        "deal_name": deal_name,
        "ev_mm": ev_mm,
        "ebitda_at_entry_mm": ebitda_mm,
        "realized_moic": moic,
        "hold_years": hold,
        "realized_irr": irr,
    }
    d.update(kw)
    return d


class TestDecomposeDeal(unittest.TestCase):

    def test_returns_teardown_result(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal, TeardownResult
        r = decompose_deal(_deal())
        self.assertIsInstance(r, TeardownResult)

    def test_returns_none_for_missing_moic(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        d = _deal()
        del d["realized_moic"]
        self.assertIsNone(decompose_deal(d))

    def test_returns_none_for_zero_hold(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        self.assertIsNone(decompose_deal(_deal(hold=0)))

    def test_gross_moic_preserved(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal(moic=3.5))
        self.assertAlmostEqual(r.gross_moic, 3.5, places=4)

    def test_entry_multiple_computed(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal(ev_mm=1200.0, ebitda_mm=100.0))
        self.assertAlmostEqual(r.entry_multiple, 12.0, places=2)

    def test_lever_contributions_sum_to_total_gain(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal(moic=3.0))
        total_gain = 3.0 - 1.0
        summed = (
            r.multiple_expansion_contribution.moic_contribution
            + r.ebitda_growth_contribution.moic_contribution
            + r.leverage_contribution.moic_contribution
            + r.debt_paydown_contribution.moic_contribution
        )
        self.assertAlmostEqual(summed, total_gain, places=2)

    def test_pct_of_gain_sums_to_one(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal(moic=2.5))
        total_pct = (
            r.multiple_expansion_contribution.pct_of_gain
            + r.ebitda_growth_contribution.pct_of_gain
            + r.leverage_contribution.pct_of_gain
            + r.debt_paydown_contribution.pct_of_gain
        )
        self.assertAlmostEqual(total_pct, 1.0, places=2)

    def test_primary_driver_set(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal())
        self.assertIn(r.primary_driver, [
            "multiple_expansion", "ebitda_growth", "leverage", "debt_paydown"
        ])

    def test_verdict_set(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal())
        self.assertIsInstance(r.verdict, str)
        self.assertTrue(len(r.verdict) > 0)

    def test_disaster_verdict(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal(moic=0.3))
        self.assertEqual(r.verdict, "value_destruction")

    def test_ebitda_cagr_positive_for_growing_deal(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal(moic=4.0, hold=5.0))
        self.assertGreater(r.ebitda_cagr, 0.0)

    def test_hold_years_preserved(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal(hold=7.0))
        self.assertEqual(r.hold_years, 7.0)

    def test_long_hold_note(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        r = decompose_deal(_deal(hold=8.0))
        self.assertIn("long hold", r.notes)


class TestBatchTeardown(unittest.TestCase):

    def test_returns_list(self):
        from rcm_mc.data_public.deal_teardown_analyzer import batch_teardown
        deals = [_deal(source_id=f"d{i}", moic=2.0+i*0.5) for i in range(5)]
        results = batch_teardown(deals)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 5)

    def test_skips_deals_without_moic(self):
        from rcm_mc.data_public.deal_teardown_analyzer import batch_teardown
        deals = [
            _deal(source_id="d1", moic=2.0),
            {"source_id": "d2", "deal_name": "incomplete"},
        ]
        results = batch_teardown(deals)
        self.assertEqual(len(results), 1)

    def test_source_ids_preserved(self):
        from rcm_mc.data_public.deal_teardown_analyzer import batch_teardown
        deals = [_deal(source_id=f"deal_{i}", moic=float(i+1)) for i in range(3)]
        results = batch_teardown(deals)
        ids = [r.source_id for r in results]
        self.assertEqual(sorted(ids), ["deal_0", "deal_1", "deal_2"])


class TestTeardownVsCorpus(unittest.TestCase):

    def _corpus(self):
        return [
            _deal(source_id=f"c{i}", moic=1.5 + i * 0.4, hold=5.0,
                  ev_mm=500.0 + i * 100, ebitda_mm=50.0 + i * 5)
            for i in range(10)
        ]

    def test_returns_dict(self):
        from rcm_mc.data_public.deal_teardown_analyzer import teardown_vs_corpus
        result = teardown_vs_corpus(_deal(), self._corpus())
        self.assertIsInstance(result, dict)

    def test_corpus_n_populated(self):
        from rcm_mc.data_public.deal_teardown_analyzer import teardown_vs_corpus
        result = teardown_vs_corpus(_deal(), self._corpus())
        self.assertGreater(result["corpus_n"], 0)

    def test_moic_signal_present(self):
        from rcm_mc.data_public.deal_teardown_analyzer import teardown_vs_corpus
        result = teardown_vs_corpus(_deal(moic=4.5), self._corpus())
        self.assertIn(result["moic_vs_corpus"], ["above_median", "below_median", "unknown"])

    def test_teardown_in_result(self):
        from rcm_mc.data_public.deal_teardown_analyzer import teardown_vs_corpus, TeardownResult
        result = teardown_vs_corpus(_deal(), self._corpus())
        self.assertIsInstance(result["teardown"], TeardownResult)

    def test_error_on_insufficient_data(self):
        from rcm_mc.data_public.deal_teardown_analyzer import teardown_vs_corpus
        d = {"source_id": "bad", "deal_name": "nope"}
        result = teardown_vs_corpus(d, [])
        self.assertIn("error", result)


class TestTeardownReport(unittest.TestCase):

    def test_report_is_string(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal, teardown_report
        r = decompose_deal(_deal())
        text = teardown_report(r)
        self.assertIsInstance(text, str)

    def test_report_contains_deal_name(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal, teardown_report
        r = decompose_deal(_deal(deal_name="Acme Health Partners LBO"))
        text = teardown_report(r)
        self.assertIn("Acme Health", text)

    def test_report_contains_moic(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal, teardown_report
        r = decompose_deal(_deal(moic=3.7))
        text = teardown_report(r)
        self.assertIn("3.70", text)

    def test_report_contains_levers(self):
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal, teardown_report
        r = decompose_deal(_deal())
        text = teardown_report(r)
        for lever in ["multiple_expansion", "ebitda_growth", "leverage", "debt_paydown"]:
            self.assertIn(lever, text)

    def test_report_with_corpus_check(self):
        from rcm_mc.data_public.deal_teardown_analyzer import (
            decompose_deal, teardown_report, teardown_vs_corpus,
        )
        corpus = [_deal(source_id=f"c{i}", moic=2.0+i*0.2) for i in range(8)]
        check = teardown_vs_corpus(_deal(), corpus)
        r = check["teardown"]
        text = teardown_report(r, corpus_check=check)
        self.assertIn("Corpus", text)


class TestTeardownTable(unittest.TestCase):

    def test_table_is_string(self):
        from rcm_mc.data_public.deal_teardown_analyzer import batch_teardown, teardown_table
        deals = [_deal(source_id=f"d{i}", moic=2.0+i*0.3) for i in range(4)]
        results = batch_teardown(deals)
        text = teardown_table(results)
        self.assertIsInstance(text, str)

    def test_table_has_header(self):
        from rcm_mc.data_public.deal_teardown_analyzer import batch_teardown, teardown_table
        deals = [_deal(source_id="d1", moic=3.0)]
        results = batch_teardown(deals)
        text = teardown_table(results)
        self.assertIn("MOIC", text)
        self.assertIn("IRR", text)

    def test_table_has_one_row_per_deal(self):
        from rcm_mc.data_public.deal_teardown_analyzer import batch_teardown, teardown_table
        deals = [_deal(source_id=f"d{i}", deal_name=f"Acme {i}", moic=2.0) for i in range(5)]
        results = batch_teardown(deals)
        text = teardown_table(results)
        # Each data row starts with the unique deal name "Acme N"
        rows = [l for l in text.splitlines() if l.startswith("Acme ")]
        self.assertEqual(len(rows), 5)


class TestTeardownWithRealCorpus(unittest.TestCase):
    """Integration test against the real seed corpus."""

    def setUp(self):
        import tempfile, os
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = tmp.name
        tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def _all_seeds(self):
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
        from rcm_mc.data_public.extended_seed_2 import EXTENDED_SEED_DEALS_2
        from rcm_mc.data_public.extended_seed_16 import EXTENDED_SEED_DEALS_16
        from rcm_mc.data_public.extended_seed_21 import EXTENDED_SEED_DEALS_21
        return _SEED_DEALS + EXTENDED_SEED_DEALS + EXTENDED_SEED_DEALS_2 + EXTENDED_SEED_DEALS_16 + EXTENDED_SEED_DEALS_21

    def test_batch_teardown_on_real_corpus(self):
        from rcm_mc.data_public.deal_teardown_analyzer import batch_teardown
        deals = self._all_seeds()
        results = batch_teardown(deals)
        self.assertGreater(len(results), 20)

    def test_hca_lbo_teardown(self):
        """HCA 2006 LBO — 2.4x, 5-year hold — should decompose cleanly."""
        from rcm_mc.data_public.deal_teardown_analyzer import decompose_deal
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        hca = next(d for d in _SEED_DEALS if d["source_id"] == "seed_001")
        r = decompose_deal(hca)
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r.gross_moic, 2.4, places=4)

    def test_teardown_table_multi_deal(self):
        from rcm_mc.data_public.deal_teardown_analyzer import batch_teardown, teardown_table
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        results = batch_teardown(_SEED_DEALS)
        text = teardown_table(results)
        self.assertIn("MOIC", text)
        self.assertGreater(text.count("\n"), 3)


if __name__ == "__main__":
    unittest.main()
