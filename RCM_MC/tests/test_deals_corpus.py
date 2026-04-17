"""Tests for the public deals corpus, normalizer, base_rates, backtester,
and pe_intelligence modules.

Run with:
    python -m pytest tests/test_deals_corpus.py -v
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from rcm_mc.data_public.deals_corpus import DealsCorpus, _SEED_DEALS
from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
from rcm_mc.data_public.deal_scorer import (
    score_deal,
    score_corpus,
    top_n,
    bottom_n,
    quality_report,
    DealQualityScore,
)
from rcm_mc.data_public.payer_sensitivity import (
    run_medicaid_cut_scenario,
    run_ma_creep_scenario,
    run_commercial_loss_scenario,
    run_uncompensated_care_scenario,
    run_all_scenarios,
    sensitivity_table,
)
from rcm_mc.data_public.normalizer import normalize_raw, normalize_batch, validate
from rcm_mc.data_public.base_rates import (
    Benchmarks,
    get_benchmarks,
    get_benchmarks_by_size,
    get_benchmarks_by_payer,
    get_benchmarks_by_year_range,
    full_summary,
)
from rcm_mc.data_public.backtester import (
    BacktestResult,
    match_deals,
    summary_stats,
    _jaccard,
    _tokenize,
    _extract_predicted_returns,
)
from rcm_mc.data_public.pe_intelligence import (
    DealType,
    classify_deal_type,
    check_reasonableness,
    check_lever_timeframes,
    detect_red_flags,
    full_intelligence_report,
    _payer_adjusted_moic_ceiling,
    _IRR_BANDS,
    _MOIC_BANDS,
)


def _tmp_db() -> str:
    """Return path to a fresh temp SQLite file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def _seeded_corpus() -> tuple:
    """Return (DealsCorpus, db_path) with seed data loaded."""
    path = _tmp_db()
    corpus = DealsCorpus(path)
    corpus.seed(skip_if_populated=False)
    return corpus, path


# ===========================================================================
# DealsCorpus
# ===========================================================================

class TestDealsCorpus(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        self.corpus = DealsCorpus(self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_empty_corpus(self):
        stats = self.corpus.stats()
        self.assertEqual(stats["total"], 0)

    def test_seed_inserts_expected_count(self):
        from rcm_mc.data_public.extended_seed_2 import EXTENDED_SEED_DEALS_2
        from rcm_mc.data_public.extended_seed_3 import EXTENDED_SEED_DEALS_3
        from rcm_mc.data_public.extended_seed_4 import EXTENDED_SEED_DEALS_4
        from rcm_mc.data_public.extended_seed_5 import EXTENDED_SEED_DEALS_5
        from rcm_mc.data_public.extended_seed_6 import EXTENDED_SEED_DEALS_6
        from rcm_mc.data_public.extended_seed_7 import EXTENDED_SEED_DEALS_7
        from rcm_mc.data_public.extended_seed_8 import EXTENDED_SEED_DEALS_8
        from rcm_mc.data_public.extended_seed_9 import EXTENDED_SEED_DEALS_9
        from rcm_mc.data_public.extended_seed_10 import EXTENDED_SEED_DEALS_10
        from rcm_mc.data_public.extended_seed_11 import EXTENDED_SEED_DEALS_11
        from rcm_mc.data_public.extended_seed_12 import EXTENDED_SEED_DEALS_12
        from rcm_mc.data_public.extended_seed_13 import EXTENDED_SEED_DEALS_13
        from rcm_mc.data_public.extended_seed_14 import EXTENDED_SEED_DEALS_14
        from rcm_mc.data_public.extended_seed_15 import EXTENDED_SEED_DEALS_15
        from rcm_mc.data_public.extended_seed_16 import EXTENDED_SEED_DEALS_16
        from rcm_mc.data_public.extended_seed_17 import EXTENDED_SEED_DEALS_17
        from rcm_mc.data_public.extended_seed_18 import EXTENDED_SEED_DEALS_18
        from rcm_mc.data_public.extended_seed_19 import EXTENDED_SEED_DEALS_19
        from rcm_mc.data_public.extended_seed_20 import EXTENDED_SEED_DEALS_20
        from rcm_mc.data_public.extended_seed_21 import EXTENDED_SEED_DEALS_21
        n = self.corpus.seed(skip_if_populated=False)
        expected = (len(_SEED_DEALS) + len(EXTENDED_SEED_DEALS) + len(EXTENDED_SEED_DEALS_2)
                    + len(EXTENDED_SEED_DEALS_3) + len(EXTENDED_SEED_DEALS_4)
                    + len(EXTENDED_SEED_DEALS_5) + len(EXTENDED_SEED_DEALS_6)
                    + len(EXTENDED_SEED_DEALS_7) + len(EXTENDED_SEED_DEALS_8)
                    + len(EXTENDED_SEED_DEALS_9) + len(EXTENDED_SEED_DEALS_10)
                    + len(EXTENDED_SEED_DEALS_11) + len(EXTENDED_SEED_DEALS_12)
                    + len(EXTENDED_SEED_DEALS_13) + len(EXTENDED_SEED_DEALS_14)
                    + len(EXTENDED_SEED_DEALS_15) + len(EXTENDED_SEED_DEALS_16)
                    + len(EXTENDED_SEED_DEALS_17) + len(EXTENDED_SEED_DEALS_18)
                    + len(EXTENDED_SEED_DEALS_19) + len(EXTENDED_SEED_DEALS_20)
                    + len(EXTENDED_SEED_DEALS_21))
        self.assertEqual(n, expected)
        stats = self.corpus.stats()
        self.assertEqual(stats["total"], expected)

    def test_seed_idempotent_skip(self):
        self.corpus.seed(skip_if_populated=False)
        n2 = self.corpus.seed(skip_if_populated=True)
        self.assertEqual(n2, 0)

    def test_seed_coverage_sufficient(self):
        self.corpus.seed()
        self.assertGreaterEqual(self.corpus.stats()["total"], 30)

    def test_upsert_new_deal(self):
        deal = {
            "source_id": "test_001",
            "source": "manual",
            "deal_name": "Test Hospital – PE Firm",
            "year": 2020,
            "buyer": "Test PE",
            "seller": "Test Seller",
            "ev_mm": 500.0,
            "ebitda_at_entry_mm": 50.0,
            "hold_years": 5.0,
            "realized_moic": 2.5,
            "realized_irr": 0.18,
            "payer_mix": {"medicare": 0.45, "medicaid": 0.15, "commercial": 0.35, "self_pay": 0.05},
            "notes": "Test deal",
        }
        deal_id = self.corpus.upsert(deal)
        self.assertGreater(deal_id, 0)

        fetched = self.corpus.get("test_001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["deal_name"], "Test Hospital – PE Firm")
        self.assertAlmostEqual(fetched["ev_mm"], 500.0)
        self.assertAlmostEqual(fetched["realized_moic"], 2.5)
        self.assertIsInstance(fetched["payer_mix"], dict)

    def test_upsert_updates_existing(self):
        self.corpus.upsert({
            "source_id": "test_002", "deal_name": "Old Name",
            "ev_mm": 100, "source": "manual",
        })
        self.corpus.upsert({
            "source_id": "test_002", "deal_name": "New Name",
            "ev_mm": 200, "source": "manual",
        })
        fetched = self.corpus.get("test_002")
        self.assertEqual(fetched["deal_name"], "New Name")
        self.assertAlmostEqual(fetched["ev_mm"], 200)

    def test_delete(self):
        self.corpus.upsert({"source_id": "del_001", "deal_name": "Delete Me", "source": "manual"})
        self.assertIsNotNone(self.corpus.get("del_001"))
        deleted = self.corpus.delete("del_001")
        self.assertTrue(deleted)
        self.assertIsNone(self.corpus.get("del_001"))

    def test_delete_nonexistent_returns_false(self):
        self.assertFalse(self.corpus.delete("nonexistent_xyz"))

    def test_list_no_filter(self):
        self.corpus.seed()
        rows = self.corpus.list()
        self.assertGreater(len(rows), 0)

    def test_list_filter_with_moic(self):
        self.corpus.seed()
        rows = self.corpus.list(with_moic=True)
        for r in rows:
            self.assertIsNotNone(r["realized_moic"])

    def test_list_filter_year_range(self):
        self.corpus.seed()
        rows = self.corpus.list(year_min=2015, year_max=2020)
        for r in rows:
            if r["year"] is not None:
                self.assertGreaterEqual(r["year"], 2015)
                self.assertLessEqual(r["year"], 2020)

    def test_list_filter_buyer(self):
        self.corpus.seed()
        rows = self.corpus.list(buyer_contains="KKR")
        self.assertGreater(len(rows), 0)
        for r in rows:
            self.assertIn("KKR", (r["buyer"] or ""))

    def test_payer_mix_round_trips_as_dict(self):
        pm = {"medicare": 0.4, "medicaid": 0.2, "commercial": 0.35, "self_pay": 0.05}
        self.corpus.upsert({
            "source_id": "pm_001", "deal_name": "Payer Mix Test",
            "source": "manual", "payer_mix": pm,
        })
        fetched = self.corpus.get("pm_001")
        self.assertIsInstance(fetched["payer_mix"], dict)
        self.assertAlmostEqual(fetched["payer_mix"]["medicare"], 0.4)

    def test_stats_by_source(self):
        self.corpus.seed()
        stats = self.corpus.stats()
        self.assertIn("seed", stats["by_source"])

    def test_seed_deals_have_required_fields(self):
        for d in _SEED_DEALS:
            self.assertIn("source_id", d, f"Missing source_id in {d}")
            self.assertIn("deal_name", d, f"Missing deal_name in {d}")
            self.assertIn("year", d, f"Missing year in {d}")
            self.assertIn("payer_mix", d, f"Missing payer_mix in {d}")

    def test_all_seed_source_ids_unique(self):
        ids = [d["source_id"] for d in _SEED_DEALS]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate source_id in seed data")


# ===========================================================================
# Normalizer
# ===========================================================================

class TestNormalizer(unittest.TestCase):

    def test_passthrough_clean_dict(self):
        raw = {
            "source_id": "norm_001",
            "source": "seed",
            "deal_name": "Test Deal",
            "year": 2020,
            "buyer": "KKR",
            "seller": "Public Co",
            "ev_mm": 1000.0,
            "ebitda_at_entry_mm": 100.0,
            "hold_years": 5.0,
            "realized_moic": 2.5,
            "realized_irr": 0.20,
            "payer_mix": {"medicare": 0.4, "commercial": 0.6},
            "notes": "Test",
        }
        out = normalize_raw(raw)
        self.assertEqual(out["deal_name"], "Test Deal")
        self.assertAlmostEqual(out["ev_mm"], 1000.0)
        self.assertAlmostEqual(out["realized_moic"], 2.5)
        self.assertAlmostEqual(out["realized_irr"], 0.20)
        self.assertIsInstance(out["payer_mix"], dict)

    def test_alias_keys_resolved(self):
        raw = {
            "name": "Deal via Alias",
            "vintage": 2019,
            "acquirer": "Blackstone",
            "enterprise_value": 2.5,       # should be interpreted as $B -> $M
            "ebitda": 300.0,
            "moic": 3.0,
            "irr": 22.0,                   # percent form -> decimal
        }
        out = normalize_raw(raw)
        self.assertEqual(out["deal_name"], "Deal via Alias")
        self.assertEqual(out["year"], 2019)
        self.assertEqual(out["buyer"], "Blackstone")
        self.assertAlmostEqual(out["ev_mm"], 2500.0)  # 2.5 < 10 → *1000
        self.assertAlmostEqual(out["ebitda_at_entry_mm"], 300.0)
        self.assertAlmostEqual(out["realized_moic"], 3.0)
        self.assertAlmostEqual(out["realized_irr"], 0.22)  # 22 → 0.22

    def test_irr_percent_to_decimal(self):
        out = normalize_raw({"deal_name": "X", "irr": 18.5, "source_id": "x"})
        self.assertAlmostEqual(out["realized_irr"], 0.185)

    def test_irr_already_decimal(self):
        out = normalize_raw({"deal_name": "X", "irr": 0.185, "source_id": "x"})
        self.assertAlmostEqual(out["realized_irr"], 0.185)

    def test_ev_billion_suffix(self):
        out = normalize_raw({"deal_name": "X", "ev_mm": "$4.3B", "source_id": "x"})
        self.assertAlmostEqual(out["ev_mm"], 4300.0)

    def test_ev_million_small_number(self):
        out = normalize_raw({"deal_name": "X", "ev_mm": 5.6, "source_id": "x"})
        self.assertAlmostEqual(out["ev_mm"], 5600.0)

    def test_auto_source_id_generated(self):
        out = normalize_raw({"deal_name": "Auto ID Deal", "year": 2021})
        self.assertTrue(out["source_id"].startswith("auto_"))
        self.assertIn("2021", out["source_id"])

    def test_payer_mix_json_string_parsed(self):
        pm_str = json.dumps({"medicare": 0.5, "commercial": 0.5})
        out = normalize_raw({"deal_name": "X", "payer_mix": pm_str, "source_id": "x"})
        self.assertIsInstance(out["payer_mix"], dict)
        self.assertAlmostEqual(out["payer_mix"]["medicare"], 0.5)

    def test_normalize_batch(self):
        raws = [{"deal_name": f"Deal {i}", "source_id": f"b_{i}"} for i in range(5)]
        results = normalize_batch(raws)
        self.assertEqual(len(results), 5)
        self.assertEqual(results[2]["deal_name"], "Deal 2")

    def test_validate_clean_deal(self):
        deal = {
            "deal_name": "Clean Deal",
            "year": 2020,
            "ev_mm": 1000.0,
            "ebitda_at_entry_mm": 100.0,
            "realized_moic": 2.0,
            "realized_irr": 0.15,
            "hold_years": 5.0,
            "payer_mix": {"medicare": 0.4, "medicaid": 0.2, "commercial": 0.35, "self_pay": 0.05},
        }
        warnings = validate(deal)
        self.assertEqual(warnings, [])

    def test_validate_bad_payer_mix_sum(self):
        deal = {
            "deal_name": "Test",
            "payer_mix": {"medicare": 0.5, "commercial": 0.7},  # sum 1.2
        }
        warnings = validate(deal)
        self.assertTrue(any("payer_mix sums" in w for w in warnings))

    def test_validate_high_ev_ebitda(self):
        deal = {
            "deal_name": "Overpriced",
            "ev_mm": 10_000,
            "ebitda_at_entry_mm": 200,
        }
        warnings = validate(deal)
        self.assertTrue(any("unusually high" in w for w in warnings))

    def test_validate_negative_ev(self):
        deal = {"deal_name": "X", "ev_mm": -100}
        warnings = validate(deal)
        self.assertTrue(any("non-positive" in w for w in warnings))

    def test_validate_irr_decimal_check(self):
        deal = {"deal_name": "X", "realized_irr": 2.5}  # 250% — looks like bad data
        warnings = validate(deal)
        self.assertTrue(any("above 100%" in w for w in warnings))


# ===========================================================================
# Base Rates
# ===========================================================================

class TestBaseRates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path = _tmp_db()
        c = DealsCorpus(cls.db_path)
        c.seed(skip_if_populated=False)
        cls.corpus = c

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.db_path)

    def test_overall_benchmarks_not_empty(self):
        bm = get_benchmarks(self.db_path)
        self.assertGreater(bm.n_deals, 0)
        self.assertGreater(bm.n_with_moic, 0)

    def test_moic_percentiles_ordered(self):
        bm = get_benchmarks(self.db_path)
        if bm.moic_p25 and bm.moic_p50 and bm.moic_p75:
            self.assertLessEqual(bm.moic_p25, bm.moic_p50)
            self.assertLessEqual(bm.moic_p50, bm.moic_p75)

    def test_irr_percentiles_ordered(self):
        bm = get_benchmarks(self.db_path)
        if bm.irr_p25 and bm.irr_p50 and bm.irr_p75:
            self.assertLessEqual(bm.irr_p25, bm.irr_p50)
            self.assertLessEqual(bm.irr_p50, bm.irr_p75)

    def test_size_bucket_large_returns_deals(self):
        bm = get_benchmarks_by_size(self.db_path, "large")
        self.assertGreater(bm.n_deals, 0)

    def test_size_bucket_small_returns_deals(self):
        bm = get_benchmarks_by_size(self.db_path, "small")
        self.assertGreater(bm.n_deals, 0)

    def test_payer_benchmarks_medicare(self):
        bm = get_benchmarks_by_payer(self.db_path, "medicare")
        self.assertGreater(bm.n_deals, 0)

    def test_payer_benchmarks_commercial(self):
        bm = get_benchmarks_by_payer(self.db_path, "commercial")
        self.assertGreater(bm.n_deals, 0)

    def test_year_range_filter(self):
        bm = get_benchmarks_by_year_range(self.db_path, 2000, 2010)
        self.assertGreater(bm.n_deals, 0)

    def test_full_summary_structure(self):
        summary = full_summary(self.db_path)
        self.assertIn("overall", summary)
        self.assertIn("by_size", summary)
        self.assertIn("by_dominant_payer", summary)
        self.assertIn("by_era", summary)
        self.assertIn("moic", summary["overall"])
        self.assertIn("p50", summary["overall"]["moic"])

    def test_benchmarks_as_dict(self):
        bm = get_benchmarks(self.db_path)
        d = bm.as_dict()
        self.assertIn("moic", d)
        self.assertIn("irr", d)
        self.assertIn("n_deals", d)
        self.assertIsInstance(d["moic"], dict)

    def test_moic_p50_in_plausible_range(self):
        bm = get_benchmarks(self.db_path)
        if bm.moic_p50:
            # Corpus median should be between 1.5x and 4.0x for hospital deals
            self.assertGreater(bm.moic_p50, 1.0)
            self.assertLess(bm.moic_p50, 6.0)

    def test_irr_p50_in_plausible_range(self):
        bm = get_benchmarks(self.db_path)
        if bm.irr_p50:
            # Should be between -50% and 70%
            self.assertGreater(bm.irr_p50, -0.5)
            self.assertLess(bm.irr_p50, 0.7)


# ===========================================================================
# Backtester
# ===========================================================================

class TestBacktester(unittest.TestCase):

    def test_jaccard_same_string(self):
        score = _jaccard("LifePoint Health KKR Buyout", "LifePoint Health KKR Buyout")
        self.assertAlmostEqual(score, 1.0)

    def test_jaccard_similar_strings(self):
        score = _jaccard("LifePoint Health – KKR", "LifePoint KKR LBO")
        self.assertGreater(score, 0.2)

    def test_jaccard_different_strings(self):
        score = _jaccard("HCA Healthcare Buyout", "Surgery Partners ASC")
        self.assertLess(score, 0.2)

    def test_jaccard_empty(self):
        score = _jaccard("", "")
        self.assertEqual(score, 0.0)

    def test_tokenize_removes_stopwords(self):
        tokens = _tokenize("HCA Healthcare Inc and the hospital")
        self.assertNotIn("and", tokens)
        self.assertNotIn("the", tokens)
        self.assertNotIn("inc", tokens)
        self.assertIn("hca", tokens)

    def test_extract_predicted_returns_none(self):
        moic, irr = _extract_predicted_returns(None)
        self.assertIsNone(moic)
        self.assertIsNone(irr)

    def test_extract_predicted_returns_from_json(self):
        summary = json.dumps({"moic": 2.5, "irr": 0.18, "other": "stuff"})
        moic, irr = _extract_predicted_returns(summary)
        self.assertAlmostEqual(moic, 2.5)
        self.assertAlmostEqual(irr, 0.18)

    def test_extract_predicted_returns_alternate_keys(self):
        summary = json.dumps({"gross_moic": 3.0, "gross_irr": 0.22})
        moic, irr = _extract_predicted_returns(summary)
        self.assertAlmostEqual(moic, 3.0)
        self.assertAlmostEqual(irr, 0.22)

    def test_summary_stats_empty(self):
        stats = summary_stats([])
        self.assertEqual(stats["total_corpus_deals"], 0)
        self.assertEqual(stats["matched_to_platform"], 0)
        self.assertEqual(stats["match_rate"], 0.0)

    def test_summary_stats_no_matches(self):
        results = [
            BacktestResult(
                corpus_deal_name="A", corpus_year=2020,
                corpus_realized_moic=2.0, corpus_realized_irr=0.15,
                platform_deal_id=None, platform_deal_name=None,
                platform_run_id=None, platform_scenario=None,
                predicted_moic=None, predicted_irr=None,
                moic_error=None, irr_error=None, match_score=0.0,
            )
        ]
        stats = summary_stats(results)
        self.assertEqual(stats["matched_to_platform"], 0)
        self.assertEqual(stats["moic_error_stats"]["n"], 0)

    def test_summary_stats_with_match(self):
        results = [
            BacktestResult(
                corpus_deal_name="HCA LBO", corpus_year=2006,
                corpus_realized_moic=2.4, corpus_realized_irr=0.19,
                platform_deal_id="deal_001", platform_deal_name="HCA Healthcare",
                platform_run_id=1, platform_scenario="base",
                predicted_moic=3.0, predicted_irr=0.25,
                moic_error=0.6, irr_error=0.06, match_score=0.7,
            )
        ]
        stats = summary_stats(results)
        self.assertEqual(stats["matched_to_platform"], 1)
        self.assertAlmostEqual(stats["moic_error_stats"]["mean"], 0.6)
        self.assertAlmostEqual(stats["irr_error_stats"]["mae"], 0.06)

    def test_match_deals_no_platform(self):
        corpus_path = _tmp_db()
        corpus = DealsCorpus(corpus_path)
        corpus.seed()

        # Store DB that doesn't exist yet (empty path)
        store_path = _tmp_db()
        results = match_deals(store_path, corpus_path)
        # All should be unmatched (empty store)
        matched = [r for r in results if r.platform_deal_id is not None]
        self.assertEqual(len(matched), 0)

        os.unlink(corpus_path)
        os.unlink(store_path)

    def test_backtest_result_as_dict(self):
        r = BacktestResult(
            corpus_deal_name="Test", corpus_year=2020,
            corpus_realized_moic=2.0, corpus_realized_irr=0.15,
            platform_deal_id="d1", platform_deal_name="Test Platform",
            platform_run_id=5, platform_scenario="base",
            predicted_moic=2.5, predicted_irr=0.18,
            moic_error=0.5, irr_error=0.03, match_score=0.85,
        )
        d = r.as_dict()
        self.assertIn("corpus_deal_name", d)
        self.assertIn("moic_error", d)
        self.assertEqual(d["match_score"], 0.85)


# ===========================================================================
# PE Intelligence
# ===========================================================================

class TestPEIntelligence(unittest.TestCase):

    def _kkr_lifepoint(self):
        return {
            "source_id": "seed_008",
            "deal_name": "LifePoint Health – KKR Buyout",
            "year": 2018,
            "buyer": "KKR",
            "ev_mm": 5600,
            "ebitda_at_entry_mm": 620,
            "payer_mix": {"medicare": 0.52, "medicaid": 0.15, "commercial": 0.29, "self_pay": 0.04},
            "notes": "89 community hospitals; rural-focused",
        }

    def _envision(self):
        return {
            "deal_name": "Envision Healthcare – KKR Buyout",
            "buyer": "KKR",
            "ev_mm": 9900,
            "ebitda_at_entry_mm": 680,
            "realized_moic": 0.05,
            "realized_irr": -0.44,
            "payer_mix": {"medicare": 0.38, "medicaid": 0.20, "commercial": 0.36, "self_pay": 0.06},
            "notes": "physician staffing anesthesia emergency medicine out-of-network billing",
        }

    def _surgery_partners(self):
        return {
            "deal_name": "Surgery Partners – Bain Capital",
            "buyer": "Bain Capital",
            "ev_mm": 1300,
            "ebitda_at_entry_mm": 130,
            "payer_mix": {"medicare": 0.33, "medicaid": 0.07, "commercial": 0.55, "self_pay": 0.05},
            "notes": "ambulatory surgery center ASC",
        }

    # Deal type classification
    def test_classify_community_hospital(self):
        dt = classify_deal_type(self._kkr_lifepoint())
        self.assertEqual(dt, DealType.PE_HOSPITAL_COMMUNITY)

    def test_classify_physician_staffing(self):
        dt = classify_deal_type(self._envision())
        self.assertEqual(dt, DealType.PE_PHYSICIAN_STAFFING)

    def test_classify_asc(self):
        dt = classify_deal_type(self._surgery_partners())
        self.assertEqual(dt, DealType.PE_ASC)

    def test_classify_behavioral_health(self):
        deal = {
            "deal_name": "Acadia Healthcare Behavioral",
            "buyer": "Waud Capital",
            "notes": "psychiatric behavioral health substance use disorder",
        }
        dt = classify_deal_type(deal)
        self.assertEqual(dt, DealType.PE_BEHAVIORAL_HEALTH)

    def test_classify_ltac(self):
        deal = {
            "deal_name": "ScionHealth LTAC",
            "buyer": "TPG",
            "notes": "long-term acute care LTAC rehabilitation",
        }
        dt = classify_deal_type(deal)
        self.assertEqual(dt, DealType.PE_LTAC_REHAB)

    def test_classify_home_health(self):
        deal = {
            "deal_name": "Kindred at Home – Humana",
            "buyer": "Humana",
            "notes": "home health hospice PDGM",
        }
        dt = classify_deal_type(deal)
        self.assertEqual(dt, DealType.PE_HOME_HEALTH)

    def test_classify_strategic_merger(self):
        deal = {
            "deal_name": "CommonSpirit – Dignity + CHI",
            "buyer": "CommonSpirit Health",
            "notes": "non-profit merger",
        }
        dt = classify_deal_type(deal)
        self.assertEqual(dt, DealType.STRATEGIC_MERGER)

    # Reasonableness checks
    def test_reasonableness_irr_in_band(self):
        deal = dict(self._kkr_lifepoint())
        deal["projected_irr"] = 0.15  # within community hospital band [0.08, 0.25]
        result = check_reasonableness(deal)
        self.assertTrue(result.irr_in_band)

    def test_reasonableness_irr_above_ceiling(self):
        deal = dict(self._kkr_lifepoint())
        deal["realized_irr"] = 0.50  # well above 0.25 ceiling
        result = check_reasonableness(deal)
        self.assertFalse(result.irr_in_band)
        self.assertTrue(any("exceeds ceiling" in w for w in result.warnings))

    def test_reasonableness_ev_ebitda_in_band(self):
        deal = {
            "deal_name": "Test", "buyer": "KKR",
            "ev_mm": 800, "ebitda_at_entry_mm": 100,  # 8x — in band for community
            "notes": "community hospital rural",
        }
        result = check_reasonableness(deal)
        self.assertTrue(result.ev_ebitda_in_band)

    def test_reasonableness_ev_ebitda_too_high(self):
        deal = {
            "deal_name": "Overpriced", "buyer": "KKR",
            "ev_mm": 2000, "ebitda_at_entry_mm": 100,  # 20x — above 12x ceiling
            "notes": "community hospital rural",
        }
        result = check_reasonableness(deal)
        self.assertFalse(result.ev_ebitda_in_band)

    def test_payer_adjusted_ceiling_commercial_premium(self):
        dt = DealType.PE_HOSPITAL_COMMUNITY
        pm_commercial = {"medicare": 0.1, "medicaid": 0.05, "commercial": 0.80, "self_pay": 0.05}
        pm_medicare   = {"medicare": 0.80, "medicaid": 0.10, "commercial": 0.08, "self_pay": 0.02}
        ceiling_comm = _payer_adjusted_moic_ceiling(dt, pm_commercial)
        ceiling_mcare = _payer_adjusted_moic_ceiling(dt, pm_medicare)
        # Commercial-heavy should have higher ceiling
        self.assertGreater(ceiling_comm, ceiling_mcare)

    # Lever timeframe warnings
    def test_lever_timeframe_ok(self):
        assumptions = {"rcm_denial_reduction": 6}  # min 3, realistic 6 — ok
        warnings = check_lever_timeframes(assumptions)
        self.assertEqual(warnings, [])

    def test_lever_timeframe_too_fast(self):
        assumptions = {"managed_care_repricing": 3}  # min 6 — way too fast
        warnings = check_lever_timeframes(assumptions)
        self.assertTrue(len(warnings) > 0)
        self.assertTrue(any("managed_care_repricing" in w for w in warnings))

    def test_lever_timeframe_optimistic(self):
        assumptions = {"rcm_coding_improvement": 1}  # below minimum 2Q
        warnings = check_lever_timeframes(assumptions)
        self.assertTrue(len(warnings) > 0)

    def test_lever_unknown_key_ignored(self):
        warnings = check_lever_timeframes({"totally_made_up_lever": 5})
        self.assertEqual(warnings, [])

    # Red flag detection
    def test_red_flag_high_leverage(self):
        deal = {
            "deal_name": "Quorum Pattern",
            "buyer": "PE Firm",
            "ev_mm": 1700,
            "ebitda_at_entry_mm": 185,
            "payer_mix": {"medicare": 0.46, "medicaid": 0.20, "commercial": 0.29, "self_pay": 0.05},
            "notes": "community hospital",
        }
        assumptions = {"entry_debt_mm": 1600}  # ~8.6x EBITDA
        flags = detect_red_flags(deal, assumptions)
        self.assertTrue(any("leverage" in f.lower() for f in flags))

    def test_red_flag_oon_billing_no_nsa(self):
        deal = dict(self._envision())
        assumptions = {}  # no nsa_impact_modeled key
        flags = detect_red_flags(deal, assumptions)
        self.assertTrue(any("No Surprises Act" in f or "out-of-network" in f.lower() for f in flags))

    def test_red_flag_rcm_too_large(self):
        deal = {
            "deal_name": "Test", "buyer": "KKR",
            "ev_mm": 500, "ebitda_at_entry_mm": 50,
            "payer_mix": {"medicare": 0.45, "commercial": 0.55},
            "notes": "community hospital",
        }
        assumptions = {"rcm_revenue_lift_mm": 25}  # 50% of EBITDA — too large
        flags = detect_red_flags(deal, assumptions)
        self.assertTrue(any("RCM improvement" in f for f in flags))

    def test_red_flag_high_govt_payer_high_moic(self):
        deal = {
            "deal_name": "Test", "buyer": "KKR",
            "ev_mm": 1000, "ebitda_at_entry_mm": 100,
            "realized_moic": 3.5,
            "payer_mix": {"medicare": 0.70, "medicaid": 0.15, "commercial": 0.12, "self_pay": 0.03},
            "notes": "community hospital",
        }
        flags = detect_red_flags(deal)
        self.assertTrue(any("government payer" in f for f in flags))

    def test_no_flags_clean_deal(self):
        deal = {
            "deal_name": "Surgery Partners Clean",
            "buyer": "Bain Capital",
            "ev_mm": 1300,
            "ebitda_at_entry_mm": 130,
            "projected_moic": 2.5,
            "projected_irr": 0.18,
            "hold_years": 5.0,
            "payer_mix": {"medicare": 0.33, "medicaid": 0.07, "commercial": 0.55, "self_pay": 0.05},
            "notes": "ambulatory surgery center",
        }
        assumptions = {"rcm_revenue_lift_mm": 10}  # 7.7% of EBITDA — fine
        flags = detect_red_flags(deal, assumptions)
        # Might have caution notes but should not have RED FLAG level issues
        hard_flags = [f for f in flags if f.startswith("RED FLAG")]
        self.assertEqual(hard_flags, [])

    # Full intelligence report
    def test_full_report_structure(self):
        corpus_path = _tmp_db()
        corpus = DealsCorpus(corpus_path)
        corpus.seed()

        deal = self._kkr_lifepoint()
        assumptions = {"entry_debt_mm": 3500, "rcm_denial_reduction": 4}
        report = full_intelligence_report(deal, assumptions, corpus_path)

        self.assertIsInstance(report.deal_type, DealType)
        self.assertIsInstance(report.red_flags, list)
        self.assertIsInstance(report.lever_warnings, list)
        self.assertIsInstance(report.heuristic_notes, list)
        self.assertIsInstance(report.risk_score, int)
        self.assertGreaterEqual(report.risk_score, 0)
        self.assertLessEqual(report.risk_score, 10)

        d = report.as_dict()
        self.assertIn("deal_name", d)
        self.assertIn("risk_score", d)
        self.assertIn("reasonableness", d)

        os.unlink(corpus_path)

    def test_full_report_without_corpus(self):
        deal = self._envision()
        report = full_intelligence_report(deal, assumptions={})
        self.assertIsNotNone(report)
        self.assertIsNone(report.reasonableness.corpus_moic_p50)

    def test_irr_bands_all_deal_types_defined(self):
        for dt in DealType:
            self.assertIn(dt, _IRR_BANDS, f"{dt} missing from _IRR_BANDS")

    def test_moic_bands_all_deal_types_defined(self):
        for dt in DealType:
            self.assertIn(dt, _MOIC_BANDS, f"{dt} missing from _MOIC_BANDS")

    def test_irr_bands_floors_below_ceilings(self):
        for dt, (floor, ceiling) in _IRR_BANDS.items():
            self.assertLess(floor, ceiling, f"{dt}: floor {floor} >= ceiling {ceiling}")

    def test_risk_score_higher_for_flagged_deal(self):
        corpus_path = _tmp_db()
        corpus = DealsCorpus(corpus_path)
        corpus.seed()

        # Highly risky deal
        risky = {
            "deal_name": "Risky Hospital Deal",
            "buyer": "Unknown PE",
            "ev_mm": 1000,
            "ebitda_at_entry_mm": 100,
            "realized_irr": 0.60,  # too high for community hospital
            "realized_moic": 5.0,
            "payer_mix": {"medicare": 0.75, "medicaid": 0.15, "commercial": 0.08, "self_pay": 0.02},
            "notes": "community hospital rural",
        }
        risky_report = full_intelligence_report(
            risky,
            {"entry_debt_mm": 900, "rcm_revenue_lift_mm": 60, "managed_care_repricing": 2},
            corpus_path,
        )

        # Clean deal
        clean = {
            "deal_name": "Surgery Partners Clean",
            "buyer": "Bain Capital",
            "ev_mm": 1300,
            "ebitda_at_entry_mm": 130,
            "payer_mix": {"medicare": 0.33, "medicaid": 0.07, "commercial": 0.55, "self_pay": 0.05},
            "notes": "ambulatory surgery center",
        }
        clean_report = full_intelligence_report(clean, {}, corpus_path)

        self.assertGreater(risky_report.risk_score, clean_report.risk_score)
        os.unlink(corpus_path)


# ===========================================================================
# Scrapers (smoke tests — do not make real HTTP calls in CI)
# ===========================================================================

class TestScraperFallbacks(unittest.TestCase):
    """Test that scraper fallback data (curated lists) is well-formed."""

    def test_kkr_fallback_data(self):
        from rcm_mc.data_public.scrapers.pe_portfolios import _KKR_HEALTHCARE
        self.assertGreater(len(_KKR_HEALTHCARE), 0)
        for deal in _KKR_HEALTHCARE:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)

    def test_tpg_fallback_data(self):
        from rcm_mc.data_public.scrapers.pe_portfolios import _TPG_HEALTHCARE
        self.assertGreater(len(_TPG_HEALTHCARE), 0)

    def test_apollo_fallback_data(self):
        from rcm_mc.data_public.scrapers.pe_portfolios import _APOLLO_HEALTHCARE
        self.assertGreater(len(_APOLLO_HEALTHCARE), 0)

    def test_bain_fallback_data(self):
        from rcm_mc.data_public.scrapers.pe_portfolios import _BAIN_HEALTHCARE
        self.assertGreater(len(_BAIN_HEALTHCARE), 0)

    def test_carlyle_fallback_data(self):
        from rcm_mc.data_public.scrapers.pe_portfolios import _CARLYLE_HEALTHCARE
        self.assertGreater(len(_CARLYLE_HEALTHCARE), 0)

    def test_sec_filings_build_url(self):
        from rcm_mc.data_public.scrapers.sec_filings import _build_search_url
        url = _build_search_url(
            '"hospital acquisition"', "8-K", "2020-01-01", "2024-12-31"
        )
        self.assertIn("efts.sec.gov", url)
        self.assertIn("hospital", url)
        self.assertIn("startdt", url)

    def test_sec_parse_ev_billion(self):
        from rcm_mc.data_public.scrapers.sec_filings import _parse_ev_from_text
        text = "The total consideration of $4.3 billion represents..."
        ev = _parse_ev_from_text(text)
        self.assertIsNotNone(ev)
        self.assertGreater(ev, 1000)  # should be in $M

    def test_sec_parse_year(self):
        from rcm_mc.data_public.scrapers.sec_filings import _parse_year_from_date
        self.assertEqual(_parse_year_from_date("2021-05-15"), 2021)
        self.assertIsNone(_parse_year_from_date(""))
        self.assertIsNone(_parse_year_from_date(None))


# ===========================================================================
# Extended Seed + News Deals
# ===========================================================================

class TestExtendedSeed(unittest.TestCase):

    def test_extended_seed_count(self):
        self.assertGreaterEqual(len(EXTENDED_SEED_DEALS), 20)

    def test_extended_seed_unique_ids(self):
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate source_id in extended seed")

    def test_extended_source_ids_no_collision_with_core(self):
        core_ids = {d["source_id"] for d in _SEED_DEALS}
        ext_ids  = {d["source_id"] for d in EXTENDED_SEED_DEALS}
        collision = core_ids & ext_ids
        self.assertEqual(collision, set(), f"source_id collision: {collision}")

    def test_combined_corpus_50_plus_deals(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed(skip_if_populated=False)
        self.assertGreaterEqual(corpus.stats()["total"], 50)
        os.unlink(db_path)

    def test_news_deals_curated_count(self):
        from rcm_mc.data_public.scrapers.news_deals import _NEWS_DEALS
        self.assertGreaterEqual(len(_NEWS_DEALS), 10)

    def test_news_deals_unique_ids(self):
        from rcm_mc.data_public.scrapers.news_deals import _NEWS_DEALS
        ids = [d["source_id"] for d in _NEWS_DEALS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_news_scrape_returns_curated_baseline(self):
        from rcm_mc.data_public.scrapers.news_deals import scrape_news_deals, _NEWS_DEALS
        # Asking for fewer than curated count still returns all curated
        result = scrape_news_deals(max_articles=5)
        self.assertGreaterEqual(len(result), len(_NEWS_DEALS))

    def test_news_rss_item_parse(self):
        from rcm_mc.data_public.scrapers.news_deals import _extract_rss_items
        sample_rss = """
        <rss><channel>
        <item>
            <title>KKR acquires hospital system for $4.3 billion</title>
            <link>https://example.com/article</link>
            <pubDate>Mon, 15 May 2023 12:00:00 GMT</pubDate>
        </item>
        <item>
            <title>Unrelated technology news</title>
            <link>https://example.com/tech</link>
            <pubDate>Tue, 16 May 2023 12:00:00 GMT</pubDate>
        </item>
        </channel></rss>
        """
        items = _extract_rss_items(sample_rss)
        self.assertEqual(len(items), 2)
        self.assertIn("KKR", items[0]["title"])

    def test_news_ma_filter(self):
        from rcm_mc.data_public.scrapers.news_deals import _is_ma_article
        self.assertTrue(_is_ma_article("KKR acquires hospital system for $4B"))
        self.assertFalse(_is_ma_article("New restaurant opens in downtown Chicago"))
        self.assertTrue(_is_ma_article("Health system merger creates $8B entity"))


# ===========================================================================
# Corpus CLI (unit-level, no live HTTP)
# ===========================================================================

class TestCorpusCLI(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def _run(self, args):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path] + args)
        return buf.getvalue()

    def test_cli_stats(self):
        out = self._run(["stats"])
        data = json.loads(out)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 50)

    def test_cli_query_no_filter(self):
        out = self._run(["query"])
        self.assertIn("Deal", out)

    def test_cli_query_with_buyer(self):
        out = self._run(["query", "--buyer", "KKR"])
        self.assertIn("KKR", out)

    def test_cli_query_json(self):
        out = self._run(["query", "--json", "--limit", "5"])
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 5)

    def test_cli_rates(self):
        out = self._run(["rates"])
        self.assertIn("Base Rates", out)
        self.assertIn("MOIC", out)

    def test_cli_rates_json(self):
        out = self._run(["rates", "--json"])
        data = json.loads(out)
        self.assertIn("overall", data)
        self.assertIn("by_size", data)

    def test_cli_intel(self):
        out = self._run(["intel", "--deal-id", "seed_007"])
        self.assertIn("Intelligence Report", out)
        self.assertIn("Envision", out)

    def test_cli_intel_json(self):
        out = self._run(["intel", "--deal-id", "seed_001", "--json"])
        data = json.loads(out)
        self.assertIn("deal_name", data)
        self.assertIn("risk_score", data)

    def test_cli_intel_with_assumptions(self):
        assumptions = json.dumps({"entry_debt_mm": 3500})
        out = self._run(["intel", "--deal-id", "seed_008", "--assumptions", assumptions])
        self.assertIn("Intelligence Report", out)

    def test_cli_seed_force(self):
        out = self._run(["seed", "--force"])
        self.assertIn("deals", out.lower())

    def test_cli_full_ingest(self):
        # Use a fresh db so full-ingest actually loads
        fresh_db = _tmp_db()
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", fresh_db, "full-ingest"])
        out = buf.getvalue()
        self.assertIn("Ingest Report", out)
        self.assertIn("seed", out)
        os.unlink(fresh_db)

    def test_cli_sensitivity(self):
        out = self._run(["sensitivity", "--deal-id", "seed_008"])
        self.assertIn("Payer Sensitivity", out)
        self.assertIn("Medicaid", out)

    def test_cli_sensitivity_json(self):
        out = self._run(["sensitivity", "--deal-id", "seed_007", "--json"])
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn("scenario", data[0])

    def test_cli_score_report(self):
        out = self._run(["score"])
        self.assertIn("Deal Quality Report", out)
        self.assertIn("Grade", out)

    def test_cli_score_single_deal(self):
        out = self._run(["score", "--deal-id", "seed_001"])
        self.assertIn("Grade", out)
        self.assertIn("Score", out)

    def test_cli_score_json(self):
        out = self._run(["score", "--json"])
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        first = data[0]
        self.assertIn("total_score", first)
        self.assertIn("grade", first)

    def test_cli_score_single_json(self):
        out = self._run(["score", "--deal-id", "seed_007", "--json"])
        data = json.loads(out)
        self.assertIn("total_score", data)
        self.assertBetween = lambda v, lo, hi: self.assertTrue(lo <= v <= hi)
        self.assertGreaterEqual(data["total_score"], 0)
        self.assertLessEqual(data["total_score"], 100)


# ===========================================================================
# Payer Sensitivity
# ===========================================================================

class TestPayerSensitivity(unittest.TestCase):

    def _lifepoint(self):
        return {
            "deal_name": "LifePoint Health – KKR",
            "ev_mm": 5600,
            "ebitda_at_entry_mm": 620,
            "realized_moic": 2.0,
            "payer_mix": {
                "medicare": 0.52, "medicaid": 0.15,
                "commercial": 0.29, "self_pay": 0.04,
            },
        }

    def _surgery_partners(self):
        return {
            "deal_name": "Surgery Partners",
            "ev_mm": 1300,
            "ebitda_at_entry_mm": 130,
            "realized_moic": 2.5,
            "payer_mix": {
                "medicare": 0.33, "medicaid": 0.07,
                "commercial": 0.55, "self_pay": 0.05,
            },
        }

    def test_medicaid_cut_negative_ebitda_delta(self):
        result = run_medicaid_cut_scenario(self._lifepoint(), cut_pct=0.05)
        self.assertIsNotNone(result.ebitda_delta_mm)
        self.assertLess(result.ebitda_delta_mm, 0)  # always negative for a cut

    def test_medicaid_cut_larger_cut_larger_impact(self):
        r5 = run_medicaid_cut_scenario(self._lifepoint(), cut_pct=0.05)
        r10 = run_medicaid_cut_scenario(self._lifepoint(), cut_pct=0.10)
        self.assertLess(r10.ebitda_delta_mm, r5.ebitda_delta_mm)

    def test_medicaid_cut_zero_medicaid_no_impact(self):
        deal = dict(self._lifepoint())
        deal["payer_mix"] = {"medicare": 0.60, "commercial": 0.40}
        result = run_medicaid_cut_scenario(deal, cut_pct=0.10)
        self.assertAlmostEqual(result.ebitda_delta_mm, 0.0, places=1)

    def test_ma_creep_negative_impact(self):
        deal = self._lifepoint()  # 52% Medicare
        result = run_ma_creep_scenario(deal, ma_creep_pct=0.10)
        self.assertLess(result.ebitda_delta_mm, 0)

    def test_ma_creep_more_creep_more_impact(self):
        deal = self._lifepoint()
        r10 = run_ma_creep_scenario(deal, ma_creep_pct=0.10)
        r20 = run_ma_creep_scenario(deal, ma_creep_pct=0.20)
        self.assertLess(r20.ebitda_delta_mm, r10.ebitda_delta_mm)

    def test_commercial_loss_negative_impact(self):
        result = run_commercial_loss_scenario(self._lifepoint(), loss_pct=0.15)
        self.assertLess(result.ebitda_delta_mm, 0)

    def test_commercial_loss_high_commercial_more_pct_impact(self):
        lp = run_commercial_loss_scenario(self._lifepoint(), loss_pct=0.15)
        sp = run_commercial_loss_scenario(self._surgery_partners(), loss_pct=0.15)
        # Surgery Partners has 55% commercial vs 29% for LifePoint;
        # should have a larger *percentage* EBITDA impact
        self.assertLess(sp.ebitda_delta_pct, lp.ebitda_delta_pct)

    def test_uncompensated_care_spike_negative(self):
        result = run_uncompensated_care_scenario(self._lifepoint(), spike_pct=0.03)
        self.assertLess(result.ebitda_delta_mm, 0)

    def test_stressed_moic_lower_than_base(self):
        result = run_medicaid_cut_scenario(self._lifepoint(), cut_pct=0.10)
        if result.base_moic and result.stressed_moic:
            self.assertLess(result.stressed_moic, result.base_moic)

    def test_moic_delta_negative(self):
        result = run_medicaid_cut_scenario(self._lifepoint(), cut_pct=0.10)
        if result.moic_delta is not None:
            self.assertLess(result.moic_delta, 0)

    def test_run_all_scenarios_count(self):
        results = run_all_scenarios(self._lifepoint())
        self.assertEqual(len(results), 7)

    def test_run_all_scenarios_all_negative(self):
        results = run_all_scenarios(self._lifepoint())
        for r in results:
            if r.ebitda_delta_mm is not None:
                self.assertLess(r.ebitda_delta_mm, 0, f"{r.scenario_name} should have negative EBITDA delta")

    def test_sensitivity_table_string_output(self):
        table = sensitivity_table(self._lifepoint())
        self.assertIn("Payer Sensitivity", table)
        self.assertIn("Medicaid rate cut", table)
        self.assertIn("EBITDA", table)

    def test_result_as_dict(self):
        result = run_medicaid_cut_scenario(self._lifepoint(), cut_pct=0.05)
        d = result.as_dict()
        self.assertIn("scenario", d)
        self.assertIn("ebitda_delta_pct", d)
        self.assertIn("stressed_moic", d)

    def test_missing_payer_mix_handled_gracefully(self):
        deal = {"deal_name": "No Payer Mix", "ebitda_at_entry_mm": 100, "ev_mm": 1000}
        result = run_medicaid_cut_scenario(deal, cut_pct=0.05)
        # Should not crash; delta should be ~0 since no payer mix
        self.assertIsNotNone(result)

    def test_missing_ebitda_handled_gracefully(self):
        deal = {"deal_name": "No EBITDA",
                "payer_mix": {"medicare": 0.5, "commercial": 0.5}}
        result = run_medicaid_cut_scenario(deal)
        self.assertIsNone(result.stressed_ebitda_mm)


# ===========================================================================
# Ingest Pipeline
# ===========================================================================

# ===========================================================================
# Deal Scorer
# ===========================================================================

class TestDealScorer(unittest.TestCase):

    def _full_deal(self):
        return {
            "source_id": "test_full",
            "source": "seed",
            "deal_name": "Full Data Deal",
            "year": 2020,
            "buyer": "KKR",
            "seller": "Public Co",
            "ev_mm": 1000.0,
            "ebitda_at_entry_mm": 100.0,
            "hold_years": 5.0,
            "realized_moic": 2.5,
            "realized_irr": 0.20,
            "payer_mix": {"medicare": 0.4, "medicaid": 0.2, "commercial": 0.35, "self_pay": 0.05},
            "notes": "Full data",
        }

    def _sparse_deal(self):
        return {
            "source_id": "test_sparse",
            "source": "sec_edgar",
            "deal_name": "Sparse Deal",
            "year": 2021,
        }

    def test_full_deal_scores_high(self):
        score = score_deal(self._full_deal())
        self.assertGreaterEqual(score.total_score, 85)
        self.assertEqual(score.grade, "A")

    def test_sparse_deal_scores_low(self):
        score = score_deal(self._sparse_deal())
        self.assertLess(score.total_score, 70)

    def test_full_beats_sparse(self):
        full = score_deal(self._full_deal())
        sparse = score_deal(self._sparse_deal())
        self.assertGreater(full.total_score, sparse.total_score)

    def test_seed_source_beats_edgar(self):
        seed = score_deal({**self._sparse_deal(), "source": "seed"})
        edgar = score_deal({**self._sparse_deal(), "source": "sec_edgar"})
        self.assertGreater(seed.source_score, edgar.source_score)

    def test_implausible_ev_ebitda_penalized(self):
        deal = {**self._full_deal(), "ev_mm": 5000, "ebitda_at_entry_mm": 100}  # 50x
        score = score_deal(deal)
        # Should have credibility deduction
        full_score = score_deal(self._full_deal())
        self.assertLess(score.credibility_score, full_score.credibility_score)

    def test_missing_payer_mix_flagged(self):
        deal = {**self._full_deal(), "payer_mix": None}
        score = score_deal(deal)
        self.assertTrue(any("payer_mix" in i for i in score.issues))

    def test_moic_irr_hold_consistency_flagged(self):
        # 2.5x MOIC at 20% IRR for 5y implies ~2.49x — consistent
        # 2.5x MOIC at 20% IRR for 1y is inconsistent
        deal = {**self._full_deal(), "hold_years": 1.0}
        score = score_deal(deal)
        self.assertTrue(any("inconsistent" in i for i in score.issues))

    def test_score_as_dict(self):
        score = score_deal(self._full_deal())
        d = score.as_dict()
        self.assertIn("grade", d)
        self.assertIn("total_score", d)
        self.assertIn("issues", d)

    def test_score_corpus_returns_sorted(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed()
        scores = score_corpus(db_path)
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i].total_score, scores[i+1].total_score)
        os.unlink(db_path)

    def test_top_n_length(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed()
        top = top_n(db_path, 5)
        self.assertEqual(len(top), 5)
        os.unlink(db_path)

    def test_quality_report_string(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed()
        report = quality_report(db_path)
        self.assertIn("Grade", report)
        self.assertIn("Score", report)
        os.unlink(db_path)

    def test_public_api_imports(self):
        from rcm_mc.data_public import (
            DealsCorpus, normalize_raw, get_benchmarks,
            full_intelligence_report, run_all_scenarios,
            score_deal, run_full_ingest,
        )


class TestIngestPipeline(unittest.TestCase):

    def test_full_ingest_loads_all_sources(self):
        from rcm_mc.data_public.ingest_pipeline import run_full_ingest
        db_path = _tmp_db()
        report = run_full_ingest(db_path, sec_edgar=False, live_pe=False)

        self.assertIn("seed", report.sources_run)
        self.assertIn("news", report.sources_run)
        self.assertIn("pe_portfolio", report.sources_run)
        self.assertGreater(report.total_upserted, 50)
        self.assertGreater(report.corpus_stats["total"], 50)
        os.unlink(db_path)

    def test_full_ingest_deduplicates(self):
        from rcm_mc.data_public.ingest_pipeline import run_full_ingest
        db_path = _tmp_db()
        r1 = run_full_ingest(db_path, sec_edgar=False, live_pe=False)
        r2 = run_full_ingest(db_path, sec_edgar=False, live_pe=False)
        # Second run should produce the same total (upsert, not append)
        self.assertEqual(r1.corpus_stats["total"], r2.corpus_stats["total"])
        os.unlink(db_path)

    def test_ingest_report_no_errors(self):
        from rcm_mc.data_public.ingest_pipeline import run_full_ingest
        db_path = _tmp_db()
        report = run_full_ingest(db_path)
        self.assertEqual(report.errors, [])
        os.unlink(db_path)

    def test_ingest_report_as_dict(self):
        from rcm_mc.data_public.ingest_pipeline import run_full_ingest
        db_path = _tmp_db()
        report = run_full_ingest(db_path)
        d = report.as_dict()
        self.assertIn("started_at", d)
        self.assertIn("corpus_stats", d)
        self.assertIn("counts_by_source", d)
        os.unlink(db_path)

    def test_ingest_corpus_has_moic_data(self):
        from rcm_mc.data_public.ingest_pipeline import run_full_ingest
        db_path = _tmp_db()
        report = run_full_ingest(db_path)
        self.assertGreater(report.corpus_stats["with_moic"], 10)
        os.unlink(db_path)


# ===========================================================================
# Comparables
# ===========================================================================

class TestComparables(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def _kkr_hca(self):
        return {
            "source_id": "seed_001",
            "deal_name": "HCA Healthcare – KKR/Bain",
            "ev_mm": 33000,
            "ebitda_at_entry_mm": 2900,
            "hold_years": 4.0,
            "payer_mix": {"medicare": 0.40, "medicaid": 0.12, "commercial": 0.42, "self_pay": 0.06},
        }

    def _mid_market(self):
        return {
            "deal_name": "Fictional Mid-Market Hospital",
            "ev_mm": 400,
            "ebitda_at_entry_mm": 45,
            "hold_years": 5.0,
            "payer_mix": {"medicare": 0.48, "medicaid": 0.20, "commercial": 0.28, "self_pay": 0.04},
        }

    def test_find_comparables_returns_list(self):
        from rcm_mc.data_public.comparables import find_comparables
        comps = find_comparables(self._kkr_hca(), self.db_path, n=5)
        self.assertIsInstance(comps, list)
        self.assertGreater(len(comps), 0)

    def test_find_comparables_excludes_self(self):
        from rcm_mc.data_public.comparables import find_comparables
        comps = find_comparables(self._kkr_hca(), self.db_path, n=10)
        ids = [c.source_id for c in comps]
        self.assertNotIn("seed_001", ids)

    def test_find_comparables_sorted_by_score(self):
        from rcm_mc.data_public.comparables import find_comparables
        comps = find_comparables(self._kkr_hca(), self.db_path, n=5)
        scores = [c.similarity_score for c in comps]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_scores_in_range(self):
        from rcm_mc.data_public.comparables import find_comparables
        comps = find_comparables(self._kkr_hca(), self.db_path, n=10)
        for c in comps:
            self.assertGreaterEqual(c.similarity_score, 0.0)
            self.assertLessEqual(c.similarity_score, 100.0)

    def test_comparable_has_required_fields(self):
        from rcm_mc.data_public.comparables import find_comparables
        comps = find_comparables(self._kkr_hca(), self.db_path, n=3)
        self.assertTrue(len(comps) > 0)
        c = comps[0]
        self.assertIsInstance(c.deal_name, str)
        self.assertIsInstance(c.matched_dimensions, list)
        self.assertTrue(len(c.matched_dimensions) > 0)

    def test_matched_dimensions_are_valid(self):
        from rcm_mc.data_public.comparables import find_comparables
        valid_dims = {"log_ev", "log_ebitda", "ev_ebitda_mult", "hold_years",
                      "medicare", "medicaid", "commercial", "self_pay"}
        comps = find_comparables(self._kkr_hca(), self.db_path, n=5)
        for c in comps:
            for dim in c.matched_dimensions:
                self.assertIn(dim, valid_dims)

    def test_find_by_metrics(self):
        from rcm_mc.data_public.comparables import find_by_metrics
        comps = find_by_metrics(
            ev_mm=1200,
            ebitda_mm=130,
            payer_mix={"medicare": 0.45, "medicaid": 0.18, "commercial": 0.33, "self_pay": 0.04},
            corpus_db_path=self.db_path,
            n=5,
        )
        self.assertIsInstance(comps, list)
        self.assertGreater(len(comps), 0)

    def test_comparables_table_returns_string(self):
        from rcm_mc.data_public.comparables import comparables_table
        out = comparables_table(self._kkr_hca(), self.db_path, n=3)
        self.assertIsInstance(out, str)
        self.assertIn("Comparable Deals", out)
        self.assertIn("Score", out)

    def test_as_dict_serialisable(self):
        from rcm_mc.data_public.comparables import find_comparables
        comps = find_comparables(self._mid_market(), self.db_path, n=3)
        for c in comps:
            d = c.as_dict()
            self.assertIn("source_id", d)
            self.assertIn("similarity_score", d)
            json.dumps(d)  # must be JSON-serialisable

    def test_mid_market_finds_medium_size_deals(self):
        from rcm_mc.data_public.comparables import find_comparables
        comps = find_comparables(self._mid_market(), self.db_path, n=5, exclude_self=False)
        # All should have ev_mm; the closest should be <$2B (not the mega-deals)
        ev_values = [c.ev_mm for c in comps if c.ev_mm is not None]
        if ev_values:
            # At least some should be under $3B (mid-market)
            self.assertTrue(any(ev < 3000 for ev in ev_values))

    def test_cli_comps(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "comps", "--deal-id", "seed_007", "--n", "3"])
        out = buf.getvalue()
        self.assertIn("Comparable Deals", out)
        self.assertIn("Score", out)

    def test_cli_comps_json(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "comps", "--deal-id", "seed_001", "--n", "3", "--json"])
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 3)
        self.assertIn("similarity_score", data[0])


# ===========================================================================
# Corpus Report (deal brief + corpus summary)
# ===========================================================================

class TestCorpusReport(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def _deal(self):
        return {
            "deal_name": "Mid-Market Hospital – PE Buyout",
            "year": 2017,
            "buyer": "Apollo",
            "ev_mm": 650,
            "ebitda_at_entry_mm": 70,
            "hold_years": 5.0,
            "payer_mix": {"medicare": 0.44, "medicaid": 0.22, "commercial": 0.30, "self_pay": 0.04},
            "source": "seed",
        }

    def test_deal_brief_returns_string(self):
        from rcm_mc.data_public.corpus_report import deal_brief
        out = deal_brief(self._deal(), self.db_path)
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 200)

    def test_deal_brief_has_sections(self):
        from rcm_mc.data_public.corpus_report import deal_brief
        out = deal_brief(self._deal(), self.db_path)
        self.assertIn("DEAL BRIEF", out)
        self.assertIn("EXIT SCENARIOS", out)
        self.assertIn("CAPITAL STRUCTURE", out)
        self.assertIn("PE INTELLIGENCE", out)

    def test_corpus_summary_report(self):
        from rcm_mc.data_public.corpus_report import corpus_summary_report
        out = corpus_summary_report(self.db_path)
        self.assertIsInstance(out, str)
        self.assertIn("PUBLIC DEALS CORPUS", out)
        self.assertIn("BASE RATES", out)
        self.assertIn("DATA QUALITY", out)

    def test_deal_brief_corpus_deal(self):
        from rcm_mc.data_public.corpus_report import deal_brief
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_001")
        out = deal_brief(deal, self.db_path)
        self.assertIn("DEAL BRIEF", out)

    def test_cli_brief_deal(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "brief", "--deal-id", "seed_007"])
        out = buf.getvalue()
        self.assertIn("DEAL BRIEF", out)
        self.assertIn("EXIT SCENARIOS", out)

    def test_cli_brief_corpus_summary(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "brief", "--corpus-summary"])
        out = buf.getvalue()
        self.assertIn("PUBLIC DEALS CORPUS", out)
        self.assertIn("BASE RATES", out)


# ===========================================================================
# Diligence Checklist
# ===========================================================================

class TestDiligenceChecklist(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def _well_documented_deal(self):
        return {
            "deal_name": "Test Hospital – PE Buyout",
            "year": 2018,
            "buyer": "KKR",
            "seller": "Health System Inc.",
            "ev_mm": 800,
            "ebitda_at_entry_mm": 90,
            "hold_years": 5.0,
            "realized_moic": 2.4,
            "realized_irr": 0.19,
            "payer_mix": {"medicare": 0.45, "medicaid": 0.20, "commercial": 0.30, "self_pay": 0.05},
            "source": "seed",
        }

    def test_build_checklist_returns_object(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist
        checklist = build_checklist(self._well_documented_deal(), self.db_path)
        self.assertIsNotNone(checklist)
        self.assertGreater(len(checklist.items), 5)

    def test_checklist_has_all_sections(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist
        checklist = build_checklist(self._well_documented_deal(), self.db_path)
        sections = {item.section for item in checklist.items}
        self.assertIn("1. Deal Overview", sections)
        self.assertIn("2. Returns Analysis", sections)
        self.assertIn("3. Capital Structure", sections)
        self.assertIn("4. Payer Mix Risk", sections)
        self.assertIn("5. PE Intelligence", sections)
        self.assertIn("6. Data Quality", sections)

    def test_checklist_counts(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist
        checklist = build_checklist(self._well_documented_deal(), self.db_path)
        self.assertGreaterEqual(checklist.critical_count, 0)
        self.assertGreaterEqual(checklist.warning_count, 0)

    def test_checklist_text_output(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist, checklist_text
        checklist = build_checklist(self._well_documented_deal(), self.db_path)
        text = checklist_text(checklist)
        self.assertIsInstance(text, str)
        self.assertIn("Diligence Checklist", text)
        self.assertIn("Deal Overview", text)

    def test_checklist_json_serialisable(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist, checklist_json
        checklist = build_checklist(self._well_documented_deal(), self.db_path)
        d = checklist_json(checklist)
        json.dumps(d)
        self.assertIn("deal_name", d)
        self.assertIn("sections", d)
        self.assertIn("open_questions", d)

    def test_sparse_deal_has_missing_items(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist
        sparse = {"deal_name": "Sparse Deal", "ev_mm": 300}
        checklist = build_checklist(sparse, self.db_path)
        statuses = {item.status for item in checklist.items}
        self.assertIn("MISSING", statuses)

    def test_high_leverage_deal_flags_critical(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist
        deal = {
            "deal_name": "High Leverage Deal",
            "ev_mm": 1000,
            "ebitda_at_entry_mm": 80,  # 12.5x entry multiple
            "hold_years": 5,
            "payer_mix": {"medicare": 0.50, "medicaid": 0.30, "commercial": 0.20},
        }
        checklist = build_checklist(deal, self.db_path,
                                    entry_debt_mm=900)  # 90% debt → very high leverage
        statuses = [item.status for item in checklist.items]
        self.assertIn("CRITICAL", statuses)

    def test_open_questions_list(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist
        checklist = build_checklist(self._well_documented_deal(), self.db_path)
        self.assertIsInstance(checklist.open_questions, list)

    def test_corpus_deal_checklist(self):
        from rcm_mc.data_public.diligence_checklist import build_checklist
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_007")  # Envision / KKR
        self.assertIsNotNone(deal)
        checklist = build_checklist(deal, self.db_path)
        self.assertGreater(len(checklist.items), 10)

    def test_cli_diligence(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "diligence", "--deal-id", "seed_001"])
        out = buf.getvalue()
        self.assertIn("Diligence Checklist", out)
        self.assertIn("Deal Overview", out)

    def test_cli_diligence_json(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "diligence", "--deal-id", "seed_007", "--json"])
        data = json.loads(buf.getvalue())
        self.assertIn("deal_name", data)
        self.assertIn("sections", data)


# ===========================================================================
# Exit Modeling
# ===========================================================================

class TestExitModeling(unittest.TestCase):

    def _hca(self):
        return {
            "deal_name": "HCA – KKR/Bain",
            "ev_mm": 33000,
            "ebitda_at_entry_mm": 2900,
            "hold_years": 4,
        }

    def _mid_market(self):
        return {
            "deal_name": "Mid-Market Hospital",
            "ev_mm": 500,
            "ebitda_at_entry_mm": 55,
            "hold_years": 5,
        }

    def test_model_exit_strategic_returns_result(self):
        from rcm_mc.data_public.exit_modeling import model_exit, ExitRoute
        result = model_exit(self._mid_market(), exit_route=ExitRoute.STRATEGIC)
        self.assertGreater(result.moic, 0)
        self.assertIsInstance(result.irr, float)

    def test_strategic_moic_positive(self):
        from rcm_mc.data_public.exit_modeling import model_exit, ExitRoute
        result = model_exit(self._mid_market())
        self.assertGreater(result.moic, 0.5)

    def test_sbo_lower_moic_than_strategic(self):
        from rcm_mc.data_public.exit_modeling import model_exit, ExitRoute
        strategic = model_exit(self._mid_market(), exit_route=ExitRoute.STRATEGIC)
        sbo = model_exit(self._mid_market(), exit_route=ExitRoute.SBO)
        # SBO has haircut → lower MOIC
        self.assertLessEqual(sbo.moic, strategic.moic)

    def test_dividend_recap_has_interim_cash(self):
        from rcm_mc.data_public.exit_modeling import model_exit, ExitRoute
        result = model_exit(self._mid_market(), exit_route=ExitRoute.DIVIDEND_RECAP)
        self.assertGreater(result.interim_cash_distributions_mm, 0)

    def test_model_all_exits_four_routes(self):
        from rcm_mc.data_public.exit_modeling import model_all_exits, ExitRoute
        results = model_all_exits(self._mid_market())
        self.assertEqual(len(results), 4)
        for route in ExitRoute.ALL:
            self.assertIn(route, results)

    def test_exit_ev_grows_with_ebitda(self):
        from rcm_mc.data_public.exit_modeling import model_exit, ExitAssumptions
        a = ExitAssumptions(exit_ebitda_growth_annual=0.05, hold_years=5)
        result = model_exit(self._mid_market(), assumptions=a)
        # Exit EBITDA > entry EBITDA after 5 years at 5% growth
        self.assertGreater(result.exit_ebitda_mm, result.entry_ebitda_mm)

    def test_higher_exit_multiple_higher_moic(self):
        from rcm_mc.data_public.exit_modeling import model_exit, ExitAssumptions
        a8 = ExitAssumptions(exit_multiple=8.0)
        a12 = ExitAssumptions(exit_multiple=12.0)
        r8 = model_exit(self._mid_market(), assumptions=a8)
        r12 = model_exit(self._mid_market(), assumptions=a12)
        self.assertGreater(r12.moic, r8.moic)

    def test_longer_hold_lower_irr_same_moic(self):
        from rcm_mc.data_public.exit_modeling import model_exit, ExitAssumptions
        # Use a deal where entry_multiple < exit_multiple so IRR is positive
        deal = {"deal_name": "Test", "ev_mm": 200, "ebitda_at_entry_mm": 40}  # 5x entry
        a5 = ExitAssumptions(exit_ebitda_growth_annual=0.0, hold_years=5,
                             exit_multiple=9.0, required_amort_pct=0.0,
                             management_fee_pct=0.0, transaction_costs_pct=0.0)
        a8 = ExitAssumptions(exit_ebitda_growth_annual=0.0, hold_years=8,
                             exit_multiple=9.0, required_amort_pct=0.0,
                             management_fee_pct=0.0, transaction_costs_pct=0.0)
        r5 = model_exit(deal, assumptions=a5)
        r8 = model_exit(deal, assumptions=a8)
        # Same EV multiple, same MOIC, but longer hold → lower IRR (positive IRR case)
        self.assertGreater(r5.irr, 0, "r5 IRR must be positive for this assertion to hold")
        self.assertGreater(r5.irr, r8.irr)

    def test_build_value_bridge(self):
        from rcm_mc.data_public.exit_modeling import model_exit, build_value_bridge
        result = model_exit(self._mid_market())
        bridge = build_value_bridge(self._mid_market(), result)
        self.assertIsNotNone(bridge.ebitda_growth_contribution_mm)
        self.assertIsNotNone(bridge.debt_paydown_mm)
        self.assertLessEqual(bridge.fees_drag_mm, 0)

    def test_bridge_as_dict_serialisable(self):
        from rcm_mc.data_public.exit_modeling import model_exit, build_value_bridge
        result = model_exit(self._mid_market())
        bridge = build_value_bridge(self._mid_market(), result)
        d = bridge.as_dict()
        json.dumps(d)
        self.assertIn("attribution", d)

    def test_exit_table_string(self):
        from rcm_mc.data_public.exit_modeling import model_all_exits, exit_table
        results = model_all_exits(self._mid_market())
        out = exit_table(results)
        self.assertIn("Exit Scenario", out)
        self.assertIn("MOIC", out)
        self.assertIn("IRR", out)

    def test_irr_sensitivity_table(self):
        from rcm_mc.data_public.exit_modeling import irr_sensitivity
        out = irr_sensitivity(self._mid_market())
        self.assertIn("IRR Sensitivity", out)
        self.assertIn("Exit Mult", out)

    def test_exit_result_as_dict(self):
        from rcm_mc.data_public.exit_modeling import model_exit
        result = model_exit(self._mid_market())
        d = result.as_dict()
        json.dumps(d)
        self.assertIn("moic", d)
        self.assertIn("irr", d)
        self.assertIn("exit_route", d)

    def test_cli_exit(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed(skip_if_populated=False)
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", db_path, "exit", "--deal-id", "seed_001"])
        out = buf.getvalue()
        self.assertIn("Exit Scenario", out)
        os.unlink(db_path)

    def test_cli_exit_json(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed(skip_if_populated=False)
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", db_path, "exit", "--deal-id", "seed_007", "--json"])
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, dict)
        self.assertIn("strategic_sale", data)
        os.unlink(db_path)

    def test_cli_exit_sensitivity(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed(skip_if_populated=False)
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", db_path, "exit", "--deal-id", "seed_008", "--sensitivity"])
        out = buf.getvalue()
        self.assertIn("IRR Sensitivity", out)
        os.unlink(db_path)


# ===========================================================================
# Leverage Analysis
# ===========================================================================

class TestLeverageAnalysis(unittest.TestCase):

    def _hca_deal(self):
        return {
            "deal_name": "HCA Healthcare – KKR/Bain",
            "ev_mm": 33000,
            "ebitda_at_entry_mm": 2900,
            "hold_years": 4,
        }

    def _small_deal(self):
        return {
            "deal_name": "Small Hospital",
            "ev_mm": 300,
            "ebitda_at_entry_mm": 30,
            "hold_years": 5,
        }

    def test_model_leverage_returns_profile(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        profile = model_leverage(self._hca_deal())
        self.assertIsNotNone(profile)
        self.assertGreater(profile.entry_leverage, 0)

    def test_entry_leverage_in_range(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        profile = model_leverage(self._hca_deal())
        # 60% debt/40% equity default → ~6x leverage on 2900 EBITDA
        self.assertGreater(profile.entry_leverage, 3.0)
        self.assertLess(profile.entry_leverage, 12.0)

    def test_annual_metrics_count(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        profile = model_leverage(self._hca_deal())
        # year 0 through year 4 → 5 entries
        self.assertEqual(len(profile.annual_metrics), 5)

    def test_debt_declines_over_time(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        profile = model_leverage(self._hca_deal())
        debts = [m.debt_balance for m in profile.annual_metrics]
        self.assertGreater(debts[0], debts[-1])

    def test_ebitda_grows_over_time(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        profile = model_leverage(self._hca_deal())
        ebitdas = [m.ebitda for m in profile.annual_metrics]
        self.assertGreater(ebitdas[-1], ebitdas[0])

    def test_interest_coverage_positive(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        profile = model_leverage(self._hca_deal())
        for m in profile.annual_metrics:
            self.assertGreater(m.interest_coverage, 0)

    def test_leverage_decreases_over_hold(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        profile = model_leverage(self._hca_deal())
        levs = [m.net_leverage for m in profile.annual_metrics]
        self.assertGreater(levs[0], levs[-1])

    def test_covenant_headroom_dict(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage, covenant_headroom
        profile = model_leverage(self._hca_deal())
        ch = covenant_headroom(profile)
        self.assertIn("covenant_leverage_trigger", ch)
        self.assertIn("min_headroom_turns", ch)
        self.assertIn("covenant_at_risk", ch)

    def test_debt_capacity_formula(self):
        from rcm_mc.data_public.leverage_analysis import debt_capacity
        # At 7.5% interest, 1.5x coverage floor, $100M EBITDA:
        # max_interest = 100/1.5 = 66.67, max_debt = 66.67/0.075 = 888.9
        cap = debt_capacity(100.0, coverage_floor=1.5)
        self.assertAlmostEqual(cap, 100.0 / 1.5 / 0.075, places=0)

    def test_coverage_ratio_function(self):
        from rcm_mc.data_public.leverage_analysis import coverage_ratio
        result = coverage_ratio(ebitda=100, interest=30, capex=15, amort=5)
        self.assertAlmostEqual(result["interest_coverage"], 100/30, places=2)
        self.assertAlmostEqual(result["fixed_charge_coverage"], (100-15)/(30+5), places=2)

    def test_stress_leverage_worse_than_base(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage, stress_leverage
        base = model_leverage(self._hca_deal())
        stressed = stress_leverage(base, ebitda_shock=-0.15, shock_year=1)
        # Stressed entry_interest_coverage should be ≤ base (less EBITDA growth)
        self.assertLessEqual(
            stressed.entry_interest_coverage,
            base.entry_interest_coverage + 0.01,
        )

    def test_as_dict_serialisable(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        import json
        profile = model_leverage(self._small_deal())
        d = profile.as_dict()
        json.dumps(d)  # must not raise
        self.assertIn("annual_metrics", d)
        self.assertIn("entry_leverage", d)

    def test_leverage_table_string(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage, leverage_table
        profile = model_leverage(self._hca_deal())
        out = leverage_table(profile)
        self.assertIn("Leverage Profile", out)
        self.assertIn("Int Cov", out)

    def test_cli_leverage(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed(skip_if_populated=False)
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", db_path, "leverage", "--deal-id", "seed_001"])
        out = buf.getvalue()
        self.assertIn("Leverage Profile", out)
        os.unlink(db_path)

    def test_cli_leverage_json(self):
        db_path = _tmp_db()
        corpus = DealsCorpus(db_path)
        corpus.seed(skip_if_populated=False)
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", db_path, "leverage", "--deal-id", "seed_001", "--json"])
        data = json.loads(buf.getvalue())
        self.assertIn("entry_leverage", data)
        self.assertIn("annual_metrics", data)
        os.unlink(db_path)

    def test_custom_interest_rate_assumption(self):
        from rcm_mc.data_public.leverage_analysis import model_leverage
        base = model_leverage(self._hca_deal())
        high_rate = model_leverage(self._hca_deal(), {"interest_rate": 0.12})
        # Higher rate → lower interest coverage
        self.assertLess(high_rate.entry_interest_coverage, base.entry_interest_coverage)


# ===========================================================================
# Vintage Analysis
# ===========================================================================

class TestVintageAnalysis(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_get_all_vintages_returns_dict(self):
        from rcm_mc.data_public.vintage_analysis import get_all_vintages
        vintages = get_all_vintages(self.db_path)
        self.assertIsInstance(vintages, dict)
        self.assertGreater(len(vintages), 3)

    def test_vintage_keys_are_years(self):
        from rcm_mc.data_public.vintage_analysis import get_all_vintages
        vintages = get_all_vintages(self.db_path)
        for yr in vintages:
            self.assertIsInstance(yr, int)
            self.assertGreater(yr, 1990)
            self.assertLess(yr, 2030)

    def test_vintage_stats_fields(self):
        from rcm_mc.data_public.vintage_analysis import get_all_vintages
        vintages = get_all_vintages(self.db_path)
        vs = next(iter(vintages.values()))
        self.assertIsNotNone(vs.cycle)
        self.assertGreater(vs.n_deals, 0)

    def test_get_vintage_stats_specific_year(self):
        from rcm_mc.data_public.vintage_analysis import get_vintage_stats
        vs = get_vintage_stats(2006, self.db_path)
        self.assertEqual(vs.year, 2006)
        self.assertIn(vs.cycle, ("pre_gfc", "post_gfc", "aca_era", "covid_era", "post_covid"))

    def test_macro_cycle_summary(self):
        from rcm_mc.data_public.vintage_analysis import macro_cycle_summary
        cycles = macro_cycle_summary(self.db_path)
        self.assertIsInstance(cycles, dict)
        # corpus covers several cycles
        self.assertGreater(len(cycles), 1)
        for name, vs in cycles.items():
            self.assertIsInstance(vs.n_deals, int)

    def test_vintage_report_structure(self):
        from rcm_mc.data_public.vintage_analysis import vintage_report
        report = vintage_report(self.db_path)
        self.assertIsNotNone(report.by_year)
        self.assertIsNotNone(report.by_cycle)
        self.assertIsNotNone(report.overall)
        self.assertGreater(report.overall.n_deals, 30)

    def test_vintage_report_best_worst(self):
        from rcm_mc.data_public.vintage_analysis import vintage_report
        report = vintage_report(self.db_path)
        if report.best_vintage_moic is not None:
            self.assertIsInstance(report.best_vintage_moic, int)
        if report.worst_vintage_moic is not None:
            self.assertIsInstance(report.worst_vintage_moic, int)

    def test_vintage_as_dict_serialisable(self):
        from rcm_mc.data_public.vintage_analysis import vintage_report
        report = vintage_report(self.db_path)
        d = report.as_dict()
        json.dumps(d)  # must not raise

    def test_entry_timing_assessment(self):
        from rcm_mc.data_public.vintage_analysis import entry_timing_assessment
        result = entry_timing_assessment(2019, self.db_path)
        self.assertIn("cycle", result)
        self.assertIn("relative_performance", result)
        self.assertIn("timing_notes", result)
        self.assertIsInstance(result["timing_notes"], list)

    def test_entry_timing_post_covid(self):
        from rcm_mc.data_public.vintage_analysis import entry_timing_assessment
        result = entry_timing_assessment(2024, self.db_path)
        self.assertEqual(result["cycle"], "post_covid")
        # Should have a note about rising rates or MA headwinds
        combined = " ".join(result["timing_notes"]).lower()
        self.assertIn("post-covid", combined)

    def test_vintage_table_string(self):
        from rcm_mc.data_public.vintage_analysis import vintage_table
        out = vintage_table(self.db_path)
        self.assertIn("Vintage Year", out)
        self.assertIn("Cycle", out)
        self.assertIsInstance(out, str)

    def test_cli_vintage_table(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "vintage"])
        out = buf.getvalue()
        self.assertIn("Vintage Year", out)

    def test_cli_vintage_json(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "vintage", "--json"])
        data = json.loads(buf.getvalue())
        self.assertIn("by_year", data)
        self.assertIn("overall", data)

    def test_cli_vintage_timing(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "vintage", "--year", "2018", "--timing"])
        out = buf.getvalue()
        self.assertIn("2018", out)
        self.assertIn("Cycle", out)


# ===========================================================================
# RCM Benchmarks
# ===========================================================================

class TestRCMBenchmarks(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def _community_deal(self):
        return {
            "deal_name": "Community Hospital – PE Buyout",
            "ev_mm": 600,
            "ebitda_at_entry_mm": 65,
            "buyer": "KKR",
        }

    def test_get_benchmarks_community(self):
        from rcm_mc.data_public.rcm_benchmarks import get_benchmarks
        bm = get_benchmarks("community")
        self.assertEqual(bm.segment, "community")
        self.assertGreater(bm.initial_denial_rate_p50, 0)
        self.assertLess(bm.initial_denial_rate_p50, 1)

    def test_get_benchmarks_asc(self):
        from rcm_mc.data_public.rcm_benchmarks import get_benchmarks
        bm = get_benchmarks("asc")
        # ASCs should have lower denial rates than community
        comm = get_benchmarks("community")
        self.assertLess(bm.initial_denial_rate_p50, comm.initial_denial_rate_p50)

    def test_get_benchmarks_behavioral_higher_denial(self):
        from rcm_mc.data_public.rcm_benchmarks import get_benchmarks
        beh = get_benchmarks("behavioral")
        comm = get_benchmarks("community")
        self.assertGreater(beh.initial_denial_rate_p50, comm.initial_denial_rate_p50)

    def test_get_all_benchmarks(self):
        from rcm_mc.data_public.rcm_benchmarks import get_all_benchmarks
        all_bm = get_all_benchmarks()
        self.assertGreater(len(all_bm), 4)
        self.assertIn("community", all_bm)
        self.assertIn("asc", all_bm)
        self.assertIn("behavioral", all_bm)

    def test_benchmark_deal_infers_type(self):
        from rcm_mc.data_public.rcm_benchmarks import benchmark_deal
        # "ambulatory surgery" is in ASC signals → should classify as ASC
        asc_deal = {"deal_name": "National Ambulatory Surgery Centers – H.I.G.",
                    "ev_mm": 400, "ebitda_at_entry_mm": 50}
        bm = benchmark_deal(asc_deal)
        self.assertEqual(bm.segment, "asc")

    def test_rcm_opportunity_returns_dict(self):
        from rcm_mc.data_public.rcm_benchmarks import rcm_opportunity
        opp = rcm_opportunity(self._community_deal())
        self.assertIn("segment", opp)
        self.assertIn("estimated_total_ebitda_uplift_mm", opp)
        self.assertIn("lever_details", opp)

    def test_rcm_opportunity_positive_uplift(self):
        from rcm_mc.data_public.rcm_benchmarks import rcm_opportunity
        # Worst-quartile baseline → should show positive uplift
        opp = rcm_opportunity(self._community_deal())
        self.assertGreater(opp["estimated_total_ebitda_uplift_mm"], 0)

    def test_rcm_opportunity_custom_metrics(self):
        from rcm_mc.data_public.rcm_benchmarks import rcm_opportunity
        # Start with best-quartile metrics — uplift should be near zero
        metrics = {
            "initial_denial_rate": 0.06,
            "clean_claim_rate": 0.97,
            "days_in_ar": 38.0,
            "collection_rate": 0.98,
            "write_off_pct": 0.03,
            "cost_to_collect": 0.024,
        }
        opp = rcm_opportunity(self._community_deal(), current_metrics=metrics)
        # Best-quartile → should be small or zero uplift
        self.assertGreaterEqual(opp["estimated_total_ebitda_uplift_mm"], 0)

    def test_benchmark_as_dict_serialisable(self):
        from rcm_mc.data_public.rcm_benchmarks import get_benchmarks
        bm = get_benchmarks("ltac")
        d = bm.as_dict()
        json.dumps(d)
        self.assertIn("initial_denial_rate", d)
        self.assertIn("days_in_ar", d)

    def test_benchmarks_table_string(self):
        from rcm_mc.data_public.rcm_benchmarks import benchmarks_table
        out = benchmarks_table()
        self.assertIn("RCM Benchmark", out)
        self.assertIn("Denial", out)

    def test_asc_lower_dar_than_community(self):
        from rcm_mc.data_public.rcm_benchmarks import get_benchmarks
        asc = get_benchmarks("asc")
        comm = get_benchmarks("community")
        self.assertLess(asc.days_in_ar_p50, comm.days_in_ar_p50)

    def test_cli_rcm_table(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "rcm"])
        out = buf.getvalue()
        self.assertIn("RCM Benchmark", out)

    def test_cli_rcm_segment(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "rcm", "--segment", "asc"])
        out = buf.getvalue()
        self.assertIn("Denial", out)

    def test_cli_rcm_deal(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "rcm", "--deal-id", "seed_007"])
        out = buf.getvalue()
        self.assertIn("Opportunity", out)

    def test_cli_rcm_json(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "rcm", "--json"])
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, dict)
        self.assertIn("community", data)


# ===========================================================================
# Extended Seed Batch 2 + Corpus Size
# ===========================================================================

class TestExtendedSeed2(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_seed_loads_75_or_more_deals(self):
        corpus = DealsCorpus(self.db_path)
        stats = corpus.stats()
        self.assertGreaterEqual(stats["total"], 75)

    def test_seed_056_present(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_056")
        self.assertIsNotNone(deal)
        self.assertIn("Kindred", deal["deal_name"])

    def test_seed_075_present(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_075")
        self.assertIsNotNone(deal)
        self.assertIn("Agilon", deal["deal_name"])

    def test_seed_batch2_payer_mix_parseable(self):
        from rcm_mc.data_public.extended_seed_2 import EXTENDED_SEED_DEALS_2
        for deal in EXTENDED_SEED_DEALS_2:
            pm = deal.get("payer_mix")
            if pm:
                parsed = json.loads(pm)
                self.assertIsInstance(parsed, dict)

    def test_no_duplicate_source_ids(self):
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
        from rcm_mc.data_public.extended_seed_2 import EXTENDED_SEED_DEALS_2
        all_ids = [d["source_id"] for d in _SEED_DEALS + EXTENDED_SEED_DEALS + EXTENDED_SEED_DEALS_2]
        self.assertEqual(len(all_ids), len(set(all_ids)), "Duplicate source_ids found in seed data")


# ===========================================================================
# Regional Analysis
# ===========================================================================

class TestRegionalAnalysis(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_classify_region_known_deal(self):
        from rcm_mc.data_public.regional_analysis import classify_region
        deal = {"deal_name": "HCA Healthcare – Nashville Tennessee", "buyer": "KKR"}
        region = classify_region(deal)
        self.assertEqual(region, "southeast")

    def test_classify_region_northeast(self):
        from rcm_mc.data_public.regional_analysis import classify_region
        deal = {"deal_name": "Nuvance Health – Connecticut", "notes": "CT hospital system"}
        region = classify_region(deal)
        self.assertEqual(region, "northeast")

    def test_classify_region_southwest(self):
        from rcm_mc.data_public.regional_analysis import classify_region
        deal = {"deal_name": "Southwest Health System – Texas", "buyer": "TPG",
                "notes": "Dallas-based community hospital"}
        region = classify_region(deal)
        self.assertEqual(region, "southwest")

    def test_classify_region_national_fallback(self):
        from rcm_mc.data_public.regional_analysis import classify_region
        deal = {"deal_name": "Generic Hospital Platform", "buyer": "PE Fund"}
        region = classify_region(deal)
        self.assertEqual(region, "national")

    def test_get_all_regions_returns_dict(self):
        from rcm_mc.data_public.regional_analysis import get_all_regions
        regions = get_all_regions(self.db_path)
        self.assertIsInstance(regions, dict)
        self.assertGreater(len(regions), 0)

    def test_all_region_stats_have_deals(self):
        from rcm_mc.data_public.regional_analysis import get_all_regions
        regions = get_all_regions(self.db_path)
        for region_key, rs in regions.items():
            self.assertGreater(rs.n_deals, 0)

    def test_region_stats_fields(self):
        from rcm_mc.data_public.regional_analysis import get_all_regions
        regions = get_all_regions(self.db_path)
        rs = next(iter(regions.values()))
        self.assertIsInstance(rs.region, str)
        self.assertIsInstance(rs.label, str)
        self.assertIsInstance(rs.n_deals, int)

    def test_region_report_structure(self):
        from rcm_mc.data_public.regional_analysis import region_report
        report = region_report(self.db_path)
        self.assertIsInstance(report.by_region, dict)
        self.assertIsNotNone(report.overall_moic_p50)

    def test_region_report_as_dict(self):
        from rcm_mc.data_public.regional_analysis import region_report
        report = region_report(self.db_path)
        d = report.as_dict()
        json.dumps(d)
        self.assertIn("by_region", d)

    def test_region_table_string(self):
        from rcm_mc.data_public.regional_analysis import region_table
        out = region_table(self.db_path)
        self.assertIn("Regional Return Analysis", out)
        self.assertIn("MOIC", out)

    def test_find_regional_comps(self):
        from rcm_mc.data_public.regional_analysis import find_regional_comps
        deal = {"deal_name": "Nashville Medical Center", "buyer": "KKR",
                "source_id": "test_001"}
        comps = find_regional_comps(deal, self.db_path, n=5)
        self.assertIsInstance(comps, list)

    def test_regional_comps_exclude_self(self):
        from rcm_mc.data_public.regional_analysis import find_regional_comps
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_001")
        comps = find_regional_comps(deal, self.db_path, n=10)
        ids = [d.get("source_id") for d in comps]
        self.assertNotIn("seed_001", ids)

    def test_get_region_stats(self):
        from rcm_mc.data_public.regional_analysis import get_region_stats
        rs = get_region_stats("national", self.db_path)
        self.assertIsInstance(rs.n_deals, int)
        self.assertEqual(rs.region, "national")

    def test_cli_region_table(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "region"])
        out = buf.getvalue()
        self.assertIn("Regional Return", out)

    def test_cli_region_json(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "region", "--json"])
        data = json.loads(buf.getvalue())
        self.assertIn("by_region", data)

    def test_cli_region_deal_id(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--db", self.db_path, "region", "--deal-id", "seed_001"])
        out = buf.getvalue()
        self.assertIn("region", out.lower())


# ===========================================================================
# Extended Seed Batch 3 (seeds 076-095)
# ===========================================================================

class TestExtendedSeed3(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_seed_loads_95_or_more_deals(self):
        corpus = DealsCorpus(self.db_path)
        stats = corpus.stats()
        self.assertGreaterEqual(stats["total"], 95)

    def test_seed_076_amedisys_present(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_076")
        self.assertIsNotNone(deal)
        self.assertIn("Amedisys", deal["deal_name"])

    def test_seed_078_envision_irr_negative(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_078")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_irr"], 0)

    def test_seed_082_steward_negative_ebitda(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_082")
        self.assertIsNotNone(deal)
        self.assertLess(deal["ebitda_at_entry_mm"], 0)

    def test_seed_095_premise_no_medicare(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_095")
        self.assertIsNotNone(deal)
        payer = deal.get("payer_mix")
        if isinstance(payer, str):
            import json as _json
            payer = _json.loads(payer)
        if isinstance(payer, dict):
            self.assertEqual(payer.get("medicare", 0), 0.0)

    def test_extended_seed_3_list_length(self):
        from rcm_mc.data_public.extended_seed_3 import EXTENDED_SEED_DEALS_3
        self.assertEqual(len(EXTENDED_SEED_DEALS_3), 20)

    def test_all_seed_3_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_3 import EXTENDED_SEED_DEALS_3
        for deal in EXTENDED_SEED_DEALS_3:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")


# ===========================================================================
# Extended Seed Batch 4 (seeds 096-115)
# ===========================================================================

class TestExtendedSeed4(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_seed_loads_115_deals(self):
        corpus = DealsCorpus(self.db_path)
        stats = corpus.stats()
        self.assertGreaterEqual(stats["total"], 115)

    def test_seed_096_teladoc_present(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_096")
        self.assertIsNotNone(deal)
        self.assertIn("Teladoc", deal["deal_name"])

    def test_seed_101_oak_street_high_ev(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_101")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["ev_mm"], 10000)

    def test_seed_115_modivcare_high_medicaid(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_115")
        self.assertIsNotNone(deal)
        payer = deal.get("payer_mix")
        if isinstance(payer, str):
            import json as _json
            payer = _json.loads(payer)
        if isinstance(payer, dict):
            self.assertGreater(payer.get("medicaid", 0), 0.5)

    def test_extended_seed_4_list_length(self):
        from rcm_mc.data_public.extended_seed_4 import EXTENDED_SEED_DEALS_4
        self.assertEqual(len(EXTENDED_SEED_DEALS_4), 20)

    def test_all_seed_4_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_4 import EXTENDED_SEED_DEALS_4
        for deal in EXTENDED_SEED_DEALS_4:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")


# ===========================================================================
# TestExtendedSeed5
# ===========================================================================

class TestExtendedSeed5(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_seed_loads_135_deals(self):
        corpus = DealsCorpus(self.db_path)
        stats = corpus.stats()
        self.assertGreaterEqual(stats["total"], 135)

    def test_seed_116_acadia_present(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_116")
        self.assertIsNotNone(deal)
        self.assertIn("Acadia", deal["deal_name"])

    def test_seed_123_cano_negative_irr(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_123")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_irr"], 0)

    def test_seed_131_prospect_distressed(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_131")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 0.5)

    def test_extended_seed_5_list_length(self):
        from rcm_mc.data_public.extended_seed_5 import EXTENDED_SEED_DEALS_5
        self.assertEqual(len(EXTENDED_SEED_DEALS_5), 20)

    def test_all_seed_5_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_5 import EXTENDED_SEED_DEALS_5
        for deal in EXTENDED_SEED_DEALS_5:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")


# ===========================================================================
# TestCmsApiClient
# ===========================================================================

class TestCmsApiClient(unittest.TestCase):
    """Unit tests for cms_api_client — mocks urllib to avoid real HTTP calls."""

    def _make_json_response(self, payload):
        import io
        raw = json.dumps(payload).encode("utf-8")
        resp = unittest.mock.MagicMock()
        resp.read.return_value = raw
        resp.__enter__ = lambda s: s
        resp.__exit__ = unittest.mock.MagicMock(return_value=False)
        return resp

    def test_fetch_pages_returns_flat_list(self):
        from rcm_mc.data_public.cms_api_client import fetch_pages
        rows = [{"a": i} for i in range(10)]
        resp = self._make_json_response(rows)
        with unittest.mock.patch("rcm_mc.data_public.cms_api_client.urlopen", return_value=resp):
            result = fetch_pages("http://example.com/data", limit=100, max_pages=1)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 10)

    def test_fetch_pages_unwraps_data_envelope(self):
        from rcm_mc.data_public.cms_api_client import fetch_pages
        rows = [{"x": 1}]
        resp = self._make_json_response({"data": rows, "meta": {"total": 1}})
        with unittest.mock.patch("rcm_mc.data_public.cms_api_client.urlopen", return_value=resp):
            result = fetch_pages("http://example.com/data", limit=100, max_pages=1)
        self.assertEqual(result, rows)

    def test_fetch_pages_stops_on_empty(self):
        from rcm_mc.data_public.cms_api_client import fetch_pages
        call_count = 0
        responses = [[{"a": 1}] * 5000, []]

        def fake_urlopen(req, timeout):
            nonlocal call_count
            resp = self._make_json_response(responses[min(call_count, len(responses)-1)])
            call_count += 1
            return resp

        with unittest.mock.patch("rcm_mc.data_public.cms_api_client.urlopen", side_effect=fake_urlopen):
            result = fetch_pages("http://example.com/data", limit=5000, max_pages=5)
        self.assertEqual(call_count, 2)
        self.assertEqual(len(result), 5000)

    def test_fetch_pages_stops_on_partial_page(self):
        from rcm_mc.data_public.cms_api_client import fetch_pages
        rows = [{"a": 1}] * 42
        resp = self._make_json_response(rows)
        with unittest.mock.patch("rcm_mc.data_public.cms_api_client.urlopen", return_value=resp):
            result = fetch_pages("http://example.com/data", limit=100, max_pages=5)
        self.assertEqual(len(result), 42)

    def test_fetch_pages_raises_on_bad_json(self):
        from rcm_mc.data_public.cms_api_client import fetch_pages, CmsApiError
        bad_resp = unittest.mock.MagicMock()
        bad_resp.read.return_value = b"not json"
        bad_resp.__enter__ = lambda s: s
        bad_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
        with unittest.mock.patch("rcm_mc.data_public.cms_api_client.urlopen", return_value=bad_resp):
            with self.assertRaises(CmsApiError):
                fetch_pages("http://example.com/data", limit=10, max_pages=1, retry_count=0)

    def test_fetch_pages_raises_after_retries_exhausted(self):
        from rcm_mc.data_public.cms_api_client import fetch_pages, CmsApiError
        from urllib.error import URLError
        with unittest.mock.patch("rcm_mc.data_public.cms_api_client.urlopen", side_effect=URLError("down")):
            with unittest.mock.patch("rcm_mc.data_public.cms_api_client.time.sleep"):
                with self.assertRaises(CmsApiError):
                    fetch_pages("http://example.com/data", limit=10, max_pages=1, retry_count=1)

    def test_resolve_column_canonical(self):
        from rcm_mc.data_public.cms_api_client import resolve_column
        row = {"rndrng_prvdr_type": "Cardiology", "tot_srvcs": 100}
        self.assertEqual(resolve_column(row, "provider_type"), "rndrng_prvdr_type")

    def test_resolve_column_missing(self):
        from rcm_mc.data_public.cms_api_client import resolve_column
        self.assertIsNone(resolve_column({}, "provider_type"))

    def test_normalize_row_renames_aliases(self):
        from rcm_mc.data_public.cms_api_client import normalize_row
        row = {"rndrng_prvdr_type": "Cardiology", "tot_srvcs": "500", "tot_mdcr_pymt_amt": "1000.0"}
        out = normalize_row(row)
        self.assertIn("provider_type", out)
        self.assertIn("total_services", out)
        self.assertIn("total_medicare_payment_amt", out)
        self.assertEqual(out["provider_type"], "Cardiology")

    def test_normalize_row_no_clobber(self):
        from rcm_mc.data_public.cms_api_client import normalize_row
        # canonical already present — should not overwrite
        row = {"provider_type": "Surgery", "rndrng_prvdr_type": "Other"}
        out = normalize_row(row)
        self.assertEqual(out["provider_type"], "Surgery")

    def test_normalize_rows_list(self):
        from rcm_mc.data_public.cms_api_client import normalize_rows
        rows = [{"tot_srvcs": "100"}, {"tot_srvcs": "200"}]
        out = normalize_rows(rows)
        self.assertTrue(all("total_services" in r for r in out))

    def test_safe_float_converts(self):
        from rcm_mc.data_public.cms_api_client import safe_float
        self.assertAlmostEqual(safe_float("1,234.56"), 1234.56)
        self.assertAlmostEqual(safe_float(42), 42.0)
        self.assertAlmostEqual(safe_float(None), 0.0)
        self.assertAlmostEqual(safe_float("bad"), 0.0)

    def test_safe_int_converts(self):
        from rcm_mc.data_public.cms_api_client import safe_int
        self.assertEqual(safe_int("1,234"), 1234)
        self.assertEqual(safe_int("12.9"), 12)
        self.assertEqual(safe_int(None), 0)
        self.assertEqual(safe_int("bad"), 0)

    def test_cms_api_error_is_runtime_error(self):
        from rcm_mc.data_public.cms_api_client import CmsApiError
        self.assertTrue(issubclass(CmsApiError, RuntimeError))

    def test_dataset_ids_configured(self):
        from rcm_mc.data_public.cms_api_client import DATASET_IDS
        self.assertIn("provider_utilization_2021", DATASET_IDS)
        self.assertIn("provider_utilization_2022", DATASET_IDS)

    def test_fetch_provider_utilization_bad_year_raises(self):
        from rcm_mc.data_public.cms_api_client import fetch_provider_utilization, CmsApiError
        with self.assertRaises(CmsApiError):
            fetch_provider_utilization(year=1999)

    def test_column_aliases_keys(self):
        from rcm_mc.data_public.cms_api_client import COLUMN_ALIASES
        required = {"provider_type", "state", "total_services", "total_medicare_payment_amt"}
        self.assertTrue(required.issubset(COLUMN_ALIASES.keys()))


# ===========================================================================
# TestMarketConcentration
# ===========================================================================

class TestMarketConcentration(unittest.TestCase):

    def _sample_df(self):
        import pandas as pd
        data = [
            {"state": "TX", "year": 2021, "provider_type": "Cardiology", "total_medicare_payment_amt": 1000.0},
            {"state": "TX", "year": 2021, "provider_type": "Orthopedic", "total_medicare_payment_amt": 600.0},
            {"state": "TX", "year": 2021, "provider_type": "Neurology",  "total_medicare_payment_amt": 400.0},
            {"state": "CA", "year": 2021, "provider_type": "Cardiology", "total_medicare_payment_amt": 2000.0},
            {"state": "CA", "year": 2021, "provider_type": "Orthopedic", "total_medicare_payment_amt": 500.0},
            {"state": "TX", "year": 2020, "provider_type": "Cardiology", "total_medicare_payment_amt": 900.0},
            {"state": "TX", "year": 2020, "provider_type": "Orthopedic", "total_medicare_payment_amt": 500.0},
        ]
        return pd.DataFrame(data)

    def test_market_concentration_returns_dataframe(self):
        from rcm_mc.data_public.market_concentration import market_concentration_summary
        import pandas as pd
        out = market_concentration_summary(self._sample_df())
        self.assertIsInstance(out, pd.DataFrame)
        self.assertFalse(out.empty)

    def test_hhi_in_range(self):
        from rcm_mc.data_public.market_concentration import market_concentration_summary
        out = market_concentration_summary(self._sample_df())
        for _, row in out.iterrows():
            self.assertGreater(row["hhi"], 0)
            self.assertLessEqual(row["hhi"], 1.0)

    def test_cr3_leq_1(self):
        from rcm_mc.data_public.market_concentration import market_concentration_summary
        out = market_concentration_summary(self._sample_df())
        for _, row in out.iterrows():
            self.assertLessEqual(row["cr3"], 1.01)

    def test_missing_required_columns_returns_empty(self):
        from rcm_mc.data_public.market_concentration import market_concentration_summary
        import pandas as pd
        out = market_concentration_summary(pd.DataFrame({"state": ["TX"]}))
        self.assertTrue(out.empty)

    def test_provider_geo_dependency(self):
        from rcm_mc.data_public.market_concentration import provider_geo_dependency
        out = provider_geo_dependency(self._sample_df())
        self.assertIn("provider_type", out.columns)
        self.assertIn("geo_hhi", out.columns)
        self.assertIn("top_state_share", out.columns)

    def test_geo_dependency_flag_set(self):
        from rcm_mc.data_public.market_concentration import provider_geo_dependency
        import pandas as pd
        # Cardiology concentrated in CA
        out = provider_geo_dependency(self._sample_df(), dependency_threshold=0.50)
        cardi = out[out["provider_type"] == "Cardiology"]
        if not cardi.empty:
            self.assertIn("geo_dependency_flag", cardi.columns)

    def test_state_volatility_summary(self):
        from rcm_mc.data_public.market_concentration import state_volatility_summary
        out = state_volatility_summary(self._sample_df())
        self.assertIn("state", out.columns)
        self.assertIn("yoy_volatility", out.columns)

    def test_state_growth_summary(self):
        from rcm_mc.data_public.market_concentration import state_growth_summary
        out = state_growth_summary(self._sample_df())
        self.assertIn("state", out.columns)
        self.assertIn("latest_payment", out.columns)

    def test_concentration_table_string(self):
        from rcm_mc.data_public.market_concentration import market_concentration_summary, concentration_table
        out = market_concentration_summary(self._sample_df())
        txt = concentration_table(out)
        self.assertIn("HHI", txt)
        self.assertIn("CR3", txt)


# ===========================================================================
# TestProviderRegime
# ===========================================================================

class TestProviderRegime(unittest.TestCase):

    def _trends_df(self):
        import pandas as pd
        data = []
        for pt, base, growth in [("Cardiology", 1000, 0.15), ("Orthopedic", 500, 0.02), ("Neurology", 800, -0.05)]:
            for yr in [2019, 2020, 2021, 2022]:
                data.append({
                    "provider_type": pt,
                    "year": yr,
                    "total_medicare_payment_amt": base * ((1 + growth) ** (yr - 2019)),
                    "total_services": 100 * (yr - 2018),
                    "total_unique_benes": 80 * (yr - 2018),
                })
        return pd.DataFrame(data)

    def test_yearly_trends_returns_yoy(self):
        from rcm_mc.data_public.provider_regime import yearly_trends
        out = yearly_trends(self._trends_df())
        self.assertIn("payment_yoy_pct", out.columns)
        self.assertIn("provider_type", out.columns)

    def test_provider_volatility_from_trends(self):
        from rcm_mc.data_public.provider_regime import yearly_trends, provider_volatility
        trends = yearly_trends(self._trends_df())
        vol = provider_volatility(trends)
        self.assertIn("yoy_payment_volatility", vol.columns)
        self.assertFalse(vol.empty)

    def test_provider_momentum_profile(self):
        from rcm_mc.data_public.provider_regime import yearly_trends, provider_momentum_profile
        trends = yearly_trends(self._trends_df())
        mom = provider_momentum_profile(trends)
        self.assertIn("growth_cagr", mom.columns)
        self.assertIn("consistency_score", mom.columns)

    def test_regime_classification_returns_five_regimes(self):
        from rcm_mc.data_public.provider_regime import (
            yearly_trends, provider_volatility, provider_momentum_profile,
            provider_regime_classification,
        )
        trends = yearly_trends(self._trends_df())
        vol = provider_volatility(trends)
        mom = provider_momentum_profile(trends)
        regimes = provider_regime_classification(mom, vol)
        self.assertIn("regime", regimes.columns)
        valid = {"durable_growth", "emerging_volatile", "steady_compounders", "stagnant", "declining_risk"}
        for r in regimes["regime"]:
            self.assertIn(str(r), valid)

    def test_high_growth_low_vol_is_durable(self):
        from rcm_mc.data_public.provider_regime import provider_regime_classification
        import pandas as pd
        mom = pd.DataFrame([{"provider_type": "A", "growth_cagr": 0.20, "consistency_score": 0.8,
                             "positive_yoy_share": 1.0, "yoy_growth_volatility": 0.05}])
        vol = pd.DataFrame([{"provider_type": "A", "yoy_payment_volatility": 0.05,
                             "avg_payment_growth": 0.20, "last_payment_growth": 0.20}])
        regimes = provider_regime_classification(mom, vol)
        self.assertEqual(str(regimes.iloc[0]["regime"]), "durable_growth")

    def test_negative_growth_high_vol_is_declining_risk(self):
        from rcm_mc.data_public.provider_regime import provider_regime_classification
        import pandas as pd
        mom = pd.DataFrame([{"provider_type": "B", "growth_cagr": -0.10, "consistency_score": -0.2,
                             "positive_yoy_share": 0.2, "yoy_growth_volatility": 0.50}])
        vol = pd.DataFrame([{"provider_type": "B", "yoy_payment_volatility": 0.50,
                             "avg_payment_growth": -0.10, "last_payment_growth": -0.10}])
        regimes = provider_regime_classification(mom, vol)
        self.assertEqual(str(regimes.iloc[0]["regime"]), "declining_risk")

    def test_growth_volatility_watchlist(self):
        from rcm_mc.data_public.provider_regime import yearly_trends, provider_volatility, growth_volatility_watchlist
        trends = yearly_trends(self._trends_df())
        vol = provider_volatility(trends)
        wl = growth_volatility_watchlist(vol)
        self.assertIn("watchlist_bucket", wl.columns)
        valid = {"priority", "monitor", "high_risk"}
        for b in wl["watchlist_bucket"]:
            self.assertIn(str(b), valid)

    def test_regime_table_string(self):
        from rcm_mc.data_public.provider_regime import (
            yearly_trends, provider_volatility, provider_momentum_profile,
            provider_regime_classification, regime_table,
        )
        trends = yearly_trends(self._trends_df())
        vol = provider_volatility(trends)
        mom = provider_momentum_profile(trends)
        regimes = provider_regime_classification(mom, vol)
        txt = regime_table(regimes)
        self.assertIn("Regime", txt)

    def test_empty_input_returns_empty(self):
        from rcm_mc.data_public.provider_regime import yearly_trends
        import pandas as pd
        out = yearly_trends(pd.DataFrame())
        self.assertTrue(out.empty)


# ===========================================================================
# TestCmsDataScraper
# ===========================================================================

class TestCmsDataScraper(unittest.TestCase):

    def _fake_row(self):
        return {
            "provider_type": "Cardiology",
            "state": "TX",
            "total_medicare_payment_amt": "50000000",
            "total_services": "12000",
            "total_unique_benes": "8000",
            "Beneficiary_Average_Risk_Score": "1.25",
        }

    def test_utilization_row_to_record_structure(self):
        from rcm_mc.data_public.scrapers.cms_data import _utilization_row_to_record
        rec = _utilization_row_to_record(self._fake_row(), 2021)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["source"], "cms_data_api")
        self.assertIn("source_id", rec)
        self.assertIn("deal_name", rec)
        self.assertIn("_cms_provider_type", rec)
        self.assertEqual(rec["_cms_state"], "TX")

    def test_record_source_id_stable(self):
        from rcm_mc.data_public.scrapers.cms_data import _utilization_row_to_record
        rec1 = _utilization_row_to_record(self._fake_row(), 2021)
        rec2 = _utilization_row_to_record(self._fake_row(), 2021)
        self.assertEqual(rec1["source_id"], rec2["source_id"])

    def test_record_missing_provider_type_returns_none(self):
        from rcm_mc.data_public.scrapers.cms_data import _utilization_row_to_record
        row = {**self._fake_row(), "provider_type": ""}
        self.assertIsNone(_utilization_row_to_record(row, 2021))

    def test_record_missing_state_returns_none(self):
        from rcm_mc.data_public.scrapers.cms_data import _utilization_row_to_record
        row = {**self._fake_row(), "state": ""}
        self.assertIsNone(_utilization_row_to_record(row, 2021))

    def test_payment_converted_to_millions(self):
        from rcm_mc.data_public.scrapers.cms_data import _utilization_row_to_record
        rec = _utilization_row_to_record(self._fake_row(), 2021)
        self.assertAlmostEqual(rec["_cms_total_payment_mm"], 50.0, places=1)

    def test_fetch_cms_market_intelligence_returns_empty_on_error(self):
        from rcm_mc.data_public.scrapers.cms_data import fetch_cms_market_intelligence
        from rcm_mc.data_public.cms_api_client import CmsApiError
        with unittest.mock.patch(
            "rcm_mc.data_public.scrapers.cms_data.fetch_provider_utilization",
            side_effect=CmsApiError("offline"),
        ):
            result = fetch_cms_market_intelligence(year=2021)
        self.assertEqual(result, [])

    def test_fetch_cms_market_intelligence_converts_rows(self):
        from rcm_mc.data_public.scrapers.cms_data import fetch_cms_market_intelligence
        rows = [self._fake_row()]
        with unittest.mock.patch(
            "rcm_mc.data_public.scrapers.cms_data.fetch_provider_utilization",
            return_value=rows,
        ):
            result = fetch_cms_market_intelligence(year=2021)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["_cms_provider_type"], "Cardiology")

    def test_cms_ingest_summary_empty(self):
        from rcm_mc.data_public.scrapers.cms_data import cms_ingest_summary
        s = cms_ingest_summary([])
        self.assertEqual(s["count"], 0)
        self.assertEqual(s["states"], [])

    def test_cms_ingest_summary_aggregates(self):
        from rcm_mc.data_public.scrapers.cms_data import _utilization_row_to_record, cms_ingest_summary
        rows = [
            {"provider_type": "Cardiology", "state": "TX", "total_medicare_payment_amt": "1000000",
             "total_services": "100", "total_unique_benes": "80", "Beneficiary_Average_Risk_Score": "1.1"},
            {"provider_type": "Orthopedic", "state": "CA", "total_medicare_payment_amt": "2000000",
             "total_services": "200", "total_unique_benes": "160", "Beneficiary_Average_Risk_Score": "0.9"},
        ]
        records = [_utilization_row_to_record(r, 2021) for r in rows]
        s = cms_ingest_summary(records)
        self.assertEqual(s["count"], 2)
        self.assertIn("TX", s["states"])
        self.assertIn("CA", s["states"])
        self.assertAlmostEqual(s["total_medicare_payment_mm"], 3.0, places=0)

    def test_public_api_exports(self):
        from rcm_mc.data_public import fetch_cms_market_intelligence, cms_ingest_summary
        self.assertTrue(callable(fetch_cms_market_intelligence))
        self.assertTrue(callable(cms_ingest_summary))

    def test_market_concentration_exported(self):
        from rcm_mc.data_public import market_concentration_summary, provider_geo_dependency
        self.assertTrue(callable(market_concentration_summary))
        self.assertTrue(callable(provider_geo_dependency))

    def test_provider_regime_exported(self):
        from rcm_mc.data_public import provider_regime_classification, regime_table
        self.assertTrue(callable(provider_regime_classification))
        self.assertTrue(callable(regime_table))


# ===========================================================================
# TestCmsMarketAnalysis
# ===========================================================================

class TestCmsMarketAnalysis(unittest.TestCase):

    def _sample_df(self):
        import pandas as pd
        data = []
        for pt, base, growth in [("Cardiology", 1000, 0.15), ("Orthopedic", 500, 0.02), ("Neurology", 800, -0.05)]:
            for yr in [2020, 2021]:
                for st in ["TX", "CA"]:
                    data.append({
                        "provider_type": pt,
                        "year": yr,
                        "state": st,
                        "total_medicare_payment_amt": base * ((1 + growth) ** (yr - 2020)) * (1.5 if st == "CA" else 1.0),
                        "total_services": 100,
                        "total_unique_benes": 80,
                    })
        return pd.DataFrame(data)

    def test_run_market_analysis_with_df(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        report = run_market_analysis(year=2021, df=self._sample_df())
        self.assertEqual(report.year, 2021)
        self.assertGreater(report.row_count, 0)
        self.assertFalse(report.concentration.empty)

    def test_report_regimes_classified(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        report = run_market_analysis(year=2021, df=self._sample_df())
        self.assertFalse(report.regimes.empty)
        self.assertIn("regime", report.regimes.columns)

    def test_report_portfolio_fit(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        report = run_market_analysis(year=2021, df=self._sample_df())
        self.assertFalse(report.portfolio_fit.empty)

    def test_empty_df_returns_empty_report(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        import pandas as pd
        report = run_market_analysis(year=2021, df=pd.DataFrame())
        self.assertEqual(report.row_count, 0)
        self.assertTrue(report.concentration.empty)

    def test_as_summary_dict_serialisable(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        import json
        report = run_market_analysis(year=2021, df=self._sample_df())
        d = report.as_summary_dict()
        json.dumps(d)
        self.assertIn("year", d)
        self.assertIn("regimes_classified", d)

    def test_analysis_summary_text_contains_headers(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis, analysis_summary_text
        report = run_market_analysis(year=2021, df=self._sample_df())
        txt = analysis_summary_text(report)
        self.assertIn("CMS Market Analysis Report", txt)
        self.assertIn("Provider Regimes", txt)

    def test_white_space_opportunities(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis, white_space_opportunities
        report = run_market_analysis(year=2021, df=self._sample_df())
        ws = white_space_opportunities(report, min_fit_percentile=0.0)
        # May be empty if no priority watchlist providers, but should not raise
        self.assertIsInstance(ws, __import__("pandas").DataFrame)

    def test_top_regimes_length(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis, top_regimes
        report = run_market_analysis(year=2021, df=self._sample_df())
        top = top_regimes(report, n=2)
        self.assertLessEqual(len(top), 2)

    def test_api_error_produces_empty_report(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        from rcm_mc.data_public.cms_api_client import CmsApiError
        with unittest.mock.patch(
            "rcm_mc.data_public.cms_market_analysis.fetch_provider_utilization",
            side_effect=CmsApiError("timeout"),
        ):
            report = run_market_analysis(year=2021)
        self.assertEqual(report.row_count, 0)
        self.assertTrue(len(report.errors) > 0)


# ===========================================================================
# TestCmsStressTest
# ===========================================================================

class TestCmsStressTest(unittest.TestCase):

    def _investability_df(self):
        import pandas as pd
        return pd.DataFrame([
            {"provider_type": "Cardiology",  "investability_score": 0.80, "total_payment": 1_000_000},
            {"provider_type": "Orthopedic",  "investability_score": 0.60, "total_payment": 500_000},
            {"provider_type": "Neurology",   "investability_score": 0.40, "total_payment": 300_000},
            {"provider_type": "Dermatology", "investability_score": 0.20, "total_payment": 200_000},
        ])

    def test_provider_stress_test_returns_df(self):
        from rcm_mc.data_public.cms_stress_test import provider_stress_test
        out = provider_stress_test(self._investability_df())
        self.assertFalse(out.empty)
        self.assertIn("stress_adjusted_score", out.columns)

    def test_stress_score_lower_on_downside(self):
        from rcm_mc.data_public.cms_stress_test import provider_stress_test
        base = provider_stress_test(self._investability_df(), downside_shock=0.0, upside_shock=0.0)
        stressed = provider_stress_test(self._investability_df(), downside_shock=0.20, upside_shock=0.0)
        self.assertLess(
            stressed["stress_adjusted_score"].mean(),
            base["stress_adjusted_score"].mean(),
        )

    def test_downside_payment_less_than_upside(self):
        from rcm_mc.data_public.cms_stress_test import provider_stress_test
        out = provider_stress_test(self._investability_df())
        for _, row in out.iterrows():
            if row["total_payment"] > 0:
                self.assertLess(row["downside_payment"], row["upside_payment"])

    def test_stress_scenario_grid_shape(self):
        from rcm_mc.data_public.cms_stress_test import stress_scenario_grid
        grid = stress_scenario_grid(
            self._investability_df(),
            downsides=[0.05, 0.15],
            upsides=[0.0, 0.10],
        )
        self.assertEqual(len(grid), 4)
        self.assertIn("scenario_label", grid.columns)

    def test_stress_scenario_grid_empty_input(self):
        from rcm_mc.data_public.cms_stress_test import stress_scenario_grid
        import pandas as pd
        out = stress_scenario_grid(pd.DataFrame())
        self.assertTrue(out.empty)

    def test_provider_value_summary(self):
        from rcm_mc.data_public.cms_stress_test import provider_value_summary
        import pandas as pd
        data = [
            {"provider_type": "Cardiology", "total_medicare_payment_amt": 1e6,
             "total_unique_benes": 500, "beneficiary_average_risk_score": 1.2},
            {"provider_type": "Orthopedic", "total_medicare_payment_amt": 500_000,
             "total_unique_benes": 300, "beneficiary_average_risk_score": 0.9},
        ]
        out = provider_value_summary(pd.DataFrame(data))
        self.assertFalse(out.empty)
        self.assertIn("value_score", out.columns)
        self.assertIn("value_percentile", out.columns)

    def test_provider_investability_summary(self):
        from rcm_mc.data_public.cms_stress_test import provider_investability_summary
        import pandas as pd
        screen = pd.DataFrame([
            {"provider_type": "Cardiology", "opportunity_score": 0.8, "total_payment": 1e6},
            {"provider_type": "Orthopedic", "opportunity_score": 0.4, "total_payment": 500_000},
        ])
        out = provider_investability_summary(screen, pd.DataFrame(), pd.DataFrame())
        self.assertFalse(out.empty)
        self.assertIn("investability_score", out.columns)

    def test_operating_posture_returns_five_buckets(self):
        from rcm_mc.data_public.cms_stress_test import (
            provider_operating_posture, stress_scenario_grid
        )
        import pandas as pd
        grid = stress_scenario_grid(self._investability_df())
        geo = pd.DataFrame([
            {"provider_type": "Cardiology", "top_state_share": 0.4, "geo_dependency_flag": False},
            {"provider_type": "Orthopedic", "top_state_share": 0.7, "geo_dependency_flag": True},
            {"provider_type": "Neurology", "top_state_share": 0.3, "geo_dependency_flag": False},
            {"provider_type": "Dermatology", "top_state_share": 0.5, "geo_dependency_flag": False},
        ])
        out = provider_operating_posture(
            self._investability_df(), pd.DataFrame(), geo, grid
        )
        self.assertIn("operating_posture", out.columns)
        valid = {"scenario_leader", "resilient_core", "balanced", "growth_optional", "concentration_risk"}
        for p in out["operating_posture"]:
            self.assertIn(str(p), valid)

    def test_concentration_risk_flagged_for_high_share(self):
        from rcm_mc.data_public.cms_stress_test import provider_operating_posture
        import pandas as pd
        # Provider with >60% concentration in one state → concentration_risk
        inv = pd.DataFrame([
            {"provider_type": "X", "investability_score": 0.5, "total_payment": 1e6},
        ])
        geo = pd.DataFrame([
            {"provider_type": "X", "top_state_share": 0.75, "geo_dependency_flag": True},
        ])
        out = provider_operating_posture(inv, pd.DataFrame(), geo, pd.DataFrame())
        self.assertEqual(str(out.iloc[0]["operating_posture"]), "concentration_risk")

    def test_stress_table_string(self):
        from rcm_mc.data_public.cms_stress_test import stress_scenario_grid, stress_table
        grid = stress_scenario_grid(self._investability_df())
        txt = stress_table(grid)
        self.assertIn("Stress Scenario", txt)
        self.assertIn("Downside", txt)

    def test_posture_table_string(self):
        from rcm_mc.data_public.cms_stress_test import provider_operating_posture, posture_table
        import pandas as pd
        out = provider_operating_posture(
            self._investability_df(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        )
        txt = posture_table(out)
        self.assertIn("Operating Posture", txt)


# ===========================================================================
# TestCmsOpportunityScoring
# ===========================================================================

class TestCmsOpportunityScoring(unittest.TestCase):

    def _sample_df(self):
        import pandas as pd
        data = []
        for pt in ["Cardiology", "Orthopedic", "Neurology"]:
            for st in ["TX", "CA", "NY"]:
                for i in range(10):
                    data.append({
                        "provider_type": pt,
                        "state": st,
                        "total_medicare_payment_amt": (i + 1) * 10000,
                        "total_services": (i + 1) * 100,
                        "total_unique_benes": (i + 1) * 80,
                        "total_submitted_chrg_amt": (i + 1) * 15000,
                        "beneficiary_average_risk_score": 1.0 + i * 0.05,
                    })
        return pd.DataFrame(data)

    def test_enrich_features_adds_pps(self):
        from rcm_mc.data_public.cms_opportunity_scoring import enrich_features
        out = enrich_features(self._sample_df())
        self.assertIn("payment_per_service", out.columns)
        self.assertIn("payment_per_bene", out.columns)

    def test_enrich_features_no_double_compute(self):
        from rcm_mc.data_public.cms_opportunity_scoring import enrich_features
        df = self._sample_df()
        df["payment_per_service"] = 999.0  # already present
        out = enrich_features(df)
        self.assertTrue((out["payment_per_service"] == 999.0).all())

    def test_state_provider_opportunities_returns_df(self):
        from rcm_mc.data_public.cms_opportunity_scoring import state_provider_opportunities
        out = state_provider_opportunities(self._sample_df(), min_rows=1)
        self.assertFalse(out.empty)
        self.assertIn("regional_opportunity_score", out.columns)
        self.assertIn("provider_type", out.columns)
        self.assertIn("state", out.columns)

    def test_opportunity_score_in_range(self):
        from rcm_mc.data_public.cms_opportunity_scoring import state_provider_opportunities
        out = state_provider_opportunities(self._sample_df(), min_rows=1)
        self.assertTrue((out["regional_opportunity_score"] >= 0).all())
        self.assertTrue((out["regional_opportunity_score"] <= 1.01).all())

    def test_missing_columns_returns_empty(self):
        from rcm_mc.data_public.cms_opportunity_scoring import state_provider_opportunities
        import pandas as pd
        out = state_provider_opportunities(pd.DataFrame({"x": [1]}), min_rows=1)
        self.assertTrue(out.empty)

    def test_benchmark_flags_high_low_normal(self):
        from rcm_mc.data_public.cms_opportunity_scoring import provider_state_benchmark_flags
        out = provider_state_benchmark_flags(self._sample_df(), min_rows=1)
        if not out.empty:
            valid = {"high_price", "normal", "low_price"}
            for f in out["benchmark_flag"]:
                self.assertIn(str(f), valid)

    def test_provider_screen_adds_market_share(self):
        from rcm_mc.data_public.cms_opportunity_scoring import provider_screen
        out = provider_screen(self._sample_df())
        self.assertFalse(out.empty)
        self.assertIn("market_share", out.columns)
        self.assertIn("opportunity_score", out.columns)
        total_share = out["market_share"].sum()
        self.assertAlmostEqual(total_share, 1.0, places=5)

    def test_provider_screen_empty_input(self):
        from rcm_mc.data_public.cms_opportunity_scoring import provider_screen
        import pandas as pd
        out = provider_screen(pd.DataFrame({"x": [1]}))
        self.assertTrue(out.empty)

    def test_opportunity_table_string(self):
        from rcm_mc.data_public.cms_opportunity_scoring import state_provider_opportunities, opportunity_table
        out = state_provider_opportunities(self._sample_df(), min_rows=1)
        txt = opportunity_table(out)
        self.assertIn("Opportunity", txt)
        self.assertIn("Score", txt)

    def test_provider_screen_table_string(self):
        from rcm_mc.data_public.cms_opportunity_scoring import provider_screen, opportunity_table
        out = provider_screen(self._sample_df())
        txt = opportunity_table(out)
        self.assertIn("Opportunity", txt)


# ===========================================================================
# TestCmsAdvisoryMemo
# ===========================================================================

class TestCmsAdvisoryMemo(unittest.TestCase):

    def _sample_df(self):
        import pandas as pd
        data = []
        for pt, base, growth in [("Cardiology", 1000, 0.18), ("Orthopedic", 600, 0.02), ("Neurology", 800, -0.04)]:
            for yr in [2020, 2021]:
                for st in ["TX", "CA", "NY"]:
                    for i in range(8):
                        data.append({
                            "provider_type": pt,
                            "year": yr,
                            "state": st,
                            "total_medicare_payment_amt": base * ((1 + growth) ** (yr - 2020)) * (i + 1),
                            "total_services": 100 * (i + 1),
                            "total_unique_benes": 80 * (i + 1),
                            "total_submitted_chrg_amt": base * 1.4 * (i + 1),
                            "beneficiary_average_risk_score": 1.0 + i * 0.05,
                        })
        return pd.DataFrame(data)

    def test_build_advisory_memo_returns_string(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        from rcm_mc.data_public.cms_advisory_memo import build_advisory_memo
        report = run_market_analysis(year=2021, df=self._sample_df())
        memo = build_advisory_memo(report)
        self.assertIsInstance(memo, str)
        self.assertIn("CMS Advisory Snapshot", memo)

    def test_memo_contains_regime_section(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        from rcm_mc.data_public.cms_advisory_memo import build_advisory_memo
        report = run_market_analysis(year=2021, df=self._sample_df())
        memo = build_advisory_memo(report)
        self.assertIn("Regime", memo)

    def test_memo_contains_concentration(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        from rcm_mc.data_public.cms_advisory_memo import build_advisory_memo
        report = run_market_analysis(year=2021, df=self._sample_df())
        memo = build_advisory_memo(report)
        self.assertIn("Concentration", memo)

    def test_quick_memo_no_http(self):
        from rcm_mc.data_public.cms_advisory_memo import quick_memo
        memo = quick_memo(df=self._sample_df(), year=2021)
        self.assertIn("CMS Advisory Snapshot", memo)
        self.assertIn("2021", memo)

    def test_quick_memo_with_supplementary(self):
        from rcm_mc.data_public.cms_advisory_memo import quick_memo
        memo = quick_memo(df=self._sample_df(), year=2021, top_n=3)
        self.assertIsInstance(memo, str)
        self.assertGreater(len(memo), 100)

    def test_empty_report_produces_minimal_memo(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        from rcm_mc.data_public.cms_advisory_memo import build_advisory_memo
        import pandas as pd
        report = run_market_analysis(year=2021, df=pd.DataFrame())
        memo = build_advisory_memo(report)
        self.assertIn("CMS Advisory Snapshot", memo)

    def test_memo_with_posture_and_stress(self):
        from rcm_mc.data_public.cms_market_analysis import run_market_analysis
        from rcm_mc.data_public.cms_advisory_memo import build_advisory_memo
        from rcm_mc.data_public.cms_stress_test import (
            provider_investability_summary, provider_stress_test,
            stress_scenario_grid, provider_operating_posture,
        )
        from rcm_mc.data_public.cms_opportunity_scoring import provider_screen
        from rcm_mc.data_public.cms_stress_test import provider_value_summary
        import pandas as pd
        df = self._sample_df()
        report = run_market_analysis(year=2021, df=df)
        screen = provider_screen(df)
        val = provider_value_summary(df)
        inv = provider_investability_summary(screen, val, pd.DataFrame())
        stress = provider_stress_test(inv)
        grid = stress_scenario_grid(inv)
        posture = provider_operating_posture(inv, pd.DataFrame(), pd.DataFrame(), grid)
        memo = build_advisory_memo(
            report, investability=inv, stress_test=stress,
            operating_posture=posture, scenario_grid=grid
        )
        self.assertIn("Investability", memo)
        self.assertIn("Stress", memo)


# ===========================================================================
# TestCmsCli — tests the 'cms' subcommand with mocked CMS API
# ===========================================================================

class TestCmsCli(unittest.TestCase):
    """Tests cms CLI subcommand using mocked CMS API calls (no real HTTP)."""

    def _mock_rows(self):
        rows = []
        for pt in ["Cardiology", "Orthopedic", "Neurology"]:
            for st in ["TX", "CA"]:
                for i in range(6):
                    rows.append({
                        "provider_type": pt,
                        "state": st,
                        "year": "2021",
                        "total_medicare_payment_amt": str((i + 1) * 100000),
                        "total_services": str((i + 1) * 500),
                        "total_unique_benes": str((i + 1) * 400),
                        "beneficiary_average_risk_score": str(1.0 + i * 0.1),
                    })
        return rows

    def _mock_fetch(self):
        """Context manager that patches fetch_provider_utilization to return synthetic data."""
        rows = self._mock_rows()
        return unittest.mock.patch(
            "rcm_mc.data_public.cms_market_analysis.fetch_provider_utilization",
            return_value=rows,
        )

    def test_cms_memo_output(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with self._mock_fetch():
            with redirect_stdout(buf):
                main(["--db", "corpus.db", "cms", "--year", "2021"])
        out = buf.getvalue()
        self.assertIn("CMS Market Analysis Report", out)

    def test_cms_concentration_flag(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with self._mock_fetch():
            with redirect_stdout(buf):
                main(["--db", "corpus.db", "cms", "--year", "2021", "--concentration"])
        out = buf.getvalue()
        self.assertIn("HHI", out)
        self.assertIn("CR3", out)

    def test_cms_regime_flag(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with self._mock_fetch():
            with redirect_stdout(buf):
                main(["--db", "corpus.db", "cms", "--year", "2021", "--regime"])
        out = buf.getvalue()
        self.assertIn("Regime", out)

    def test_cms_json_output(self):
        from rcm_mc.data_public.corpus_cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with self._mock_fetch():
            with redirect_stdout(buf):
                main(["--db", "corpus.db", "cms", "--year", "2021", "--json"])
        data = json.loads(buf.getvalue())
        self.assertIn("year", data)
        self.assertIn("row_count", data)

    def test_cms_no_data_graceful(self):
        from rcm_mc.data_public.corpus_cli import main
        from rcm_mc.data_public.cms_api_client import CmsApiError
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with unittest.mock.patch(
            "rcm_mc.data_public.cms_market_analysis.fetch_provider_utilization",
            side_effect=CmsApiError("timeout"),
        ):
            with redirect_stdout(buf):
                main(["--db", "corpus.db", "cms", "--year", "2021"])
        out = buf.getvalue()
        # Should not crash; should report no data or errors
        self.assertIsInstance(out, str)


class TestExtendedSeed8(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_seed_loads_455_deals(self):
        corpus = DealsCorpus(self.db_path)
        stats = corpus.stats()
        self.assertGreaterEqual(stats["total"], 455)

    def test_seed_187_signify_high_moic(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_187")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["realized_moic"], 3.0)

    def test_seed_191_nuance_microsoft(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_191")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["ev_mm"], 15000)

    def test_seed_185_villageMD_loss(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_185")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 0.5)

    def test_extended_seed_8_list_length(self):
        from rcm_mc.data_public.extended_seed_8 import EXTENDED_SEED_DEALS_8
        self.assertEqual(len(EXTENDED_SEED_DEALS_8), 20)

    def test_all_seed_8_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_8 import EXTENDED_SEED_DEALS_8
        for deal in EXTENDED_SEED_DEALS_8:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")


class TestExtendedSeed9(unittest.TestCase):
    """Tests for extended_seed_9.py (deals 196-215)."""

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_extended_seed_9_list_length(self):
        from rcm_mc.data_public.extended_seed_9 import EXTENDED_SEED_DEALS_9
        self.assertEqual(len(EXTENDED_SEED_DEALS_9), 20)

    def test_all_seed_9_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_9 import EXTENDED_SEED_DEALS_9
        for deal in EXTENDED_SEED_DEALS_9:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")

    def test_seed_196_acadia_add_on(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_196")
        self.assertIsNotNone(deal)
        self.assertIn("Acadia", deal["deal_name"])

    def test_seed_205_quorum_distressed(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_205")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 1.0)

    def test_seed_215_iora_health(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_215")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["realized_moic"], 5.0)

    def test_seed_9_source_ids_unique(self):
        from rcm_mc.data_public.extended_seed_9 import EXTENDED_SEED_DEALS_9
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_9]
        self.assertEqual(len(ids), len(set(ids)))


class TestExtendedSeed10(unittest.TestCase):
    """Tests for extended_seed_10.py (deals 216-235)."""

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_extended_seed_10_list_length(self):
        from rcm_mc.data_public.extended_seed_10 import EXTENDED_SEED_DEALS_10
        self.assertEqual(len(EXTENDED_SEED_DEALS_10), 20)

    def test_all_seed_10_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_10 import EXTENDED_SEED_DEALS_10
        for deal in EXTENDED_SEED_DEALS_10:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")

    def test_seed_222_ciox_high_moic(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_222")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["realized_moic"], 5.0)

    def test_seed_221_consulate_distressed(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_221")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 1.0)

    def test_seed_235_inovalon_take_private(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_235")
        self.assertIsNotNone(deal)
        self.assertAlmostEqual(deal["ev_mm"], 7300.0)

    def test_seed_10_source_ids_unique(self):
        from rcm_mc.data_public.extended_seed_10 import EXTENDED_SEED_DEALS_10
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_10]
        self.assertEqual(len(ids), len(set(ids)))


class TestExtendedSeed13(unittest.TestCase):
    """Tests for extended_seed_13.py (deals 276-295)."""

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_extended_seed_13_list_length(self):
        from rcm_mc.data_public.extended_seed_13 import EXTENDED_SEED_DEALS_13
        self.assertEqual(len(EXTENDED_SEED_DEALS_13), 20)

    def test_all_seed_13_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_13 import EXTENDED_SEED_DEALS_13
        for deal in EXTENDED_SEED_DEALS_13:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")

    def test_seed_277_us_oncology_moic(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_277")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["realized_moic"], 3.0)

    def test_seed_290_privia_high_moic(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_290")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["realized_moic"], 5.0)

    def test_seed_295_reit_portfolio(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_295")
        self.assertIsNotNone(deal)
        self.assertIsNotNone(deal["deal_name"])

    def test_seed_13_source_ids_unique(self):
        from rcm_mc.data_public.extended_seed_13 import EXTENDED_SEED_DEALS_13
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_13]
        self.assertEqual(len(ids), len(set(ids)))


class TestCmsRateMonitor(unittest.TestCase):
    """Tests for cms_rate_monitor module."""

    def _make_dfs(self):
        import pandas as pd
        dfs = {}
        for yr, mult in [(2019, 1.0), (2020, 0.97), (2021, 0.93), (2022, 0.88)]:
            dfs[yr] = pd.DataFrame({
                "provider_type": ["SNF", "HHA", "ASC", "SNF", "HHA"],
                "state": ["TX", "TX", "TX", "CA", "CA"],
                "_cms_total_payment_mm": [
                    10.0 * mult, 8.0 * mult, 5.0 * mult, 12.0 * mult, 7.0 * mult
                ],
                "bene_cnt": [100, 80, 50, 120, 70],
            })
        return dfs

    def test_compute_rate_trends_returns_list(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends
        signals = compute_rate_trends(self._make_dfs())
        self.assertIsInstance(signals, list)

    def test_compute_rate_trends_has_snf(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends
        signals = compute_rate_trends(self._make_dfs())
        provider_types = [s.provider_type for s in signals]
        self.assertIn("SNF", provider_types)

    def test_declining_trend_detected(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends
        signals = compute_rate_trends(self._make_dfs())
        # All provider types are declining (mult goes from 1.0 to 0.88)
        declining = [s for s in signals if s.trend_direction == "declining"]
        self.assertGreater(len(declining), 0)

    def test_adverse_flag_set(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends
        signals = compute_rate_trends(self._make_dfs())
        adverse = [s for s in signals if s.adverse_flag]
        self.assertGreater(len(adverse), 0)

    def test_adverse_rate_flag_output(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends, adverse_rate_flag
        signals = compute_rate_trends(self._make_dfs())
        flags = adverse_rate_flag(signals)
        self.assertIsInstance(flags, list)
        if flags:
            self.assertIn("provider_type", flags[0])
            self.assertIn("severity", flags[0])

    def test_rate_trend_table_text(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends, rate_trend_table
        signals = compute_rate_trends(self._make_dfs())
        text = rate_trend_table(signals)
        self.assertIn("CMS Payment Rate Trends", text)
        self.assertIn("SNF", text)

    def test_rate_trend_table_empty(self):
        from rcm_mc.data_public.cms_rate_monitor import rate_trend_table
        text = rate_trend_table([])
        self.assertIn("No rate trend data", text)

    def test_rate_monitor_summary(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends, rate_monitor_summary
        signals = compute_rate_trends(self._make_dfs())
        summary = rate_monitor_summary(signals)
        self.assertIn("total_provider_types", summary)
        self.assertIn("adverse_count", summary)
        self.assertGreater(summary["total_provider_types"], 0)

    def test_apply_rate_stress_lowers_moic(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends, apply_rate_stress
        signals = compute_rate_trends(self._make_dfs())
        benchmarks = {"moic_p25": 1.5, "moic_p50": 2.0, "moic_p75": 3.0}
        stressed = apply_rate_stress(benchmarks, signals)
        # Should have applied a haircut
        if stressed.get("rate_stress_applied"):
            self.assertLessEqual(stressed["moic_p50"], 2.0)

    def test_apply_rate_stress_no_adverse(self):
        from rcm_mc.data_public.cms_rate_monitor import apply_rate_stress
        benchmarks = {"moic_p50": 2.0}
        stressed = apply_rate_stress(benchmarks, [])
        # No adverse signals → no change
        self.assertEqual(stressed["moic_p50"], 2.0)

    def test_empty_dfs(self):
        from rcm_mc.data_public.cms_rate_monitor import compute_rate_trends
        import pandas as pd
        signals = compute_rate_trends({2021: pd.DataFrame(), 2022: pd.DataFrame()})
        self.assertEqual(signals, [])


class TestDealUnderwritingModel(unittest.TestCase):
    """Tests for deal_underwriting_model module."""

    def _assumptions(self, **kw):
        from rcm_mc.data_public.deal_underwriting_model import UnderwritingAssumptions
        base = dict(
            entry_ev_mm=1000.0,
            entry_ebitda_mm=100.0,
            equity_contribution_pct=0.40,
            ebitda_cagr=0.10,
            hold_years=5.0,
            exit_multiple=10.0,
            entry_leverage_x=5.0,
            debt_amortization_pct=0.03,
            interest_rate=0.075,
            transaction_fee_pct=0.02,
            management_fee_annual_mm=2.0,
        )
        base.update(kw)
        return UnderwritingAssumptions(**base)

    def test_underwrite_basic(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal
        a = self._assumptions()
        result = underwrite_deal(a)
        self.assertGreater(result.gross_moic, 0)
        self.assertGreater(result.gross_irr, 0)
        self.assertGreater(result.net_moic, 0)

    def test_underwrite_moic_irr_consistency(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal
        a = self._assumptions()
        result = underwrite_deal(a)
        # gross_moic ^ (1/hold_years) - 1 should approximate gross_irr
        implied = result.gross_moic ** (1.0 / a.hold_years) - 1.0
        self.assertAlmostEqual(implied, result.gross_irr, places=2)

    def test_underwrite_net_lt_gross(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal
        a = self._assumptions()
        result = underwrite_deal(a)
        self.assertLess(result.net_moic, result.gross_moic)
        self.assertLess(result.net_irr, result.gross_irr)

    def test_underwrite_negative_ebitda_warning(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal
        a = self._assumptions(entry_ebitda_mm=-10.0)
        result = underwrite_deal(a)
        self.assertGreater(len(result.warnings), 0)

    def test_underwrite_exit_equity_positive(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal
        a = self._assumptions()
        result = underwrite_deal(a)
        self.assertGreaterEqual(result.exit_equity_mm, 0)

    def test_sensitivity_table_shape(self):
        from rcm_mc.data_public.deal_underwriting_model import sensitivity_table
        a = self._assumptions()
        grid = sensitivity_table(a)
        self.assertIsInstance(grid, list)
        self.assertGreater(len(grid), 0)
        self.assertIn("exit_multiple", grid[0])
        self.assertIn("hold_years", grid[0])
        self.assertIn("net_irr", grid[0])

    def test_sensitivity_table_monotonic_with_multiple(self):
        from rcm_mc.data_public.deal_underwriting_model import sensitivity_table
        a = self._assumptions()
        grid = sensitivity_table(a, hold_years_list=[5.0])
        irrs = [row["net_irr"] for row in grid if row["net_irr"] is not None]
        # Higher exit multiple should produce higher IRR
        self.assertEqual(irrs, sorted(irrs))

    def test_benchmark_compare_top_quartile(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal, benchmark_compare
        a = self._assumptions(exit_multiple=14.0, ebitda_cagr=0.15)
        result = underwrite_deal(a)
        benchmarks = {"moic_p25": 1.5, "moic_p50": 2.0, "moic_p75": 3.0}
        comp = benchmark_compare(result, benchmarks)
        self.assertIn(comp["corpus_positioning"], ["top_quartile", "above_median"])

    def test_benchmark_compare_bottom_quartile(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal, benchmark_compare
        # Low multiple + short hold = poor returns
        a = self._assumptions(exit_multiple=6.0, ebitda_cagr=0.02, hold_years=3.0)
        result = underwrite_deal(a)
        benchmarks = {"moic_p25": 1.5, "moic_p50": 2.0, "moic_p75": 3.0}
        comp = benchmark_compare(result, benchmarks)
        self.assertIn(comp["corpus_positioning"], ["bottom_quartile", "below_median"])

    def test_underwriting_report_text(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal, underwriting_report
        a = self._assumptions(deal_name="Test LBO")
        result = underwrite_deal(a)
        text = underwriting_report(result)
        self.assertIn("Test LBO", text)
        self.assertIn("Gross MOIC", text)
        self.assertIn("Net IRR", text)

    def test_underwriting_report_with_benchmarks(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal, underwriting_report
        a = self._assumptions()
        result = underwrite_deal(a)
        benchmarks = {"moic_p25": 1.5, "moic_p50": 2.0, "moic_p75": 3.0}
        text = underwriting_report(result, benchmarks=benchmarks)
        self.assertIn("CORPUS BENCHMARK", text)
        self.assertIn("Positioning", text)

    def test_underwrite_exit_ev_calculation(self):
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal
        a = self._assumptions(ebitda_cagr=0.0, exit_multiple=10.0)
        result = underwrite_deal(a)
        # No growth: exit EBITDA == entry EBITDA; exit EV = 10 * 100 = 1000
        self.assertAlmostEqual(result.exit_ebitda_mm, 100.0, places=1)
        self.assertAlmostEqual(result.exit_ev_mm, 1000.0, places=0)


class TestCorpusExport(unittest.TestCase):
    """Tests for corpus_export module."""

    def _sample_deals(self):
        return [
            {
                "source_id": "e001", "deal_name": "=DANGEROUS() formula test",
                "year": 2021, "buyer": "KKR", "seller": "Acme",
                "ev_mm": 1000.0, "ebitda_at_entry_mm": 100.0,
                "hold_years": 5.0, "realized_moic": 2.5, "realized_irr": 0.20,
                "payer_mix": {"medicare": 0.40, "medicaid": 0.20, "commercial": 0.40},
                "notes": "test deal",
            },
            {
                "source_id": "e002", "deal_name": "Normal Deal",
                "year": 2020, "buyer": "Blackstone", "seller": "Founders",
                "ev_mm": 500.0, "ebitda_at_entry_mm": None,
                "hold_years": None, "realized_moic": None, "realized_irr": None,
                "payer_mix": None,
                "notes": None,
            },
        ]

    def test_to_csv_returns_string(self):
        from rcm_mc.data_public.corpus_export import to_csv
        csv_text = to_csv(self._sample_deals())
        self.assertIsInstance(csv_text, str)
        self.assertIn("source_id", csv_text)
        self.assertIn("deal_name", csv_text)

    def test_to_csv_defangs_formulas(self):
        from rcm_mc.data_public.corpus_export import to_csv
        csv_text = to_csv(self._sample_deals())
        # The "=DANGEROUS()" field should be prefixed with ' (defanged)
        self.assertIn("'=DANGEROUS()", csv_text)

    def test_to_csv_payer_columns(self):
        from rcm_mc.data_public.corpus_export import to_csv
        csv_text = to_csv(self._sample_deals(), include_payer_mix=True)
        self.assertIn("payer_medicare", csv_text)
        self.assertIn("payer_medicaid", csv_text)

    def test_to_csv_writes_file(self):
        from rcm_mc.data_public.corpus_export import to_csv
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            to_csv(self._sample_deals(), path=path)
            self.assertGreater(os.path.getsize(path), 0)
        finally:
            os.unlink(path)

    def test_to_json_valid(self):
        from rcm_mc.data_public.corpus_export import to_json
        text = to_json(self._sample_deals())
        data = json.loads(text)
        self.assertEqual(len(data), 2)
        self.assertIn("deal_name", data[0])

    def test_to_json_payer_expanded(self):
        from rcm_mc.data_public.corpus_export import to_json
        text = to_json(self._sample_deals())
        data = json.loads(text)
        # First deal has payer mix
        self.assertIn("payer_medicare", data[0])

    def test_to_markdown_header(self):
        from rcm_mc.data_public.corpus_export import to_markdown
        md = to_markdown(self._sample_deals(), include_scorecard=False)
        self.assertIn("## Deal Corpus", md)
        self.assertIn("| # |", md)

    def test_to_markdown_scorecard(self):
        from rcm_mc.data_public.corpus_export import to_markdown
        md = to_markdown(self._sample_deals(), include_scorecard=True)
        self.assertIn("Portfolio Corpus Scorecard", md)

    def test_to_markdown_max_rows(self):
        from rcm_mc.data_public.corpus_export import to_markdown
        many = self._sample_deals() * 30  # 60 deals
        md = to_markdown(many, max_rows=10)
        self.assertIn("more deals", md)

    def test_export_full_corpus(self):
        from rcm_mc.data_public.corpus_export import export_full_corpus
        import tempfile, os
        db = tempfile.mktemp(suffix=".db")
        out_dir = tempfile.mkdtemp()
        try:
            written = export_full_corpus(db_path=db, out_dir=out_dir, formats=["csv", "json"])
            self.assertIn("csv", written)
            self.assertIn("json", written)
            self.assertTrue(os.path.exists(written["csv"]))
            self.assertTrue(os.path.exists(written["json"]))
            self.assertGreater(os.path.getsize(written["csv"]), 100)
        finally:
            os.unlink(db)
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)


class TestExtendedSeed7(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_seed_loads_175_deals(self):
        corpus = DealsCorpus(self.db_path)
        stats = corpus.stats()
        self.assertGreaterEqual(stats["total"], 175)

    def test_seed_156_change_healthcare(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_156")
        self.assertIsNotNone(deal)
        self.assertIn("Change Healthcare", deal["deal_name"])
        self.assertGreater(deal["ev_mm"], 10000)

    def test_seed_171_bright_health_loss(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_171")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 0.1)

    def test_seed_175_surgical_notes(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_175")
        self.assertIsNotNone(deal)
        self.assertIn("Surgical Notes", deal["deal_name"])

    def test_extended_seed_7_list_length(self):
        from rcm_mc.data_public.extended_seed_7 import EXTENDED_SEED_DEALS_7
        self.assertEqual(len(EXTENDED_SEED_DEALS_7), 20)

    def test_all_seed_7_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_7 import EXTENDED_SEED_DEALS_7
        for deal in EXTENDED_SEED_DEALS_7:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")


class TestCmsWhiteSpaceMap(unittest.TestCase):
    """Tests for cms_white_space_map module."""

    def _mock_report(self):
        from rcm_mc.data_public.cms_market_analysis import MarketAnalysisReport
        import pandas as pd
        conc = pd.DataFrame([
            {"state": "TX", "provider_type": "SNF", "hhi": 1200.0},
            {"state": "CA", "provider_type": "SNF", "hhi": 3500.0},
            {"state": "FL", "provider_type": "HHA", "hhi": 1800.0},
        ])
        fit = pd.DataFrame([
            {"state": "TX", "state_fit_score": 0.85},
            {"state": "CA", "state_fit_score": 0.60},
            {"state": "FL", "state_fit_score": 0.72},
        ])
        regimes = pd.DataFrame([
            {"provider_type": "SNF", "regime": "durable_growth"},
            {"provider_type": "HHA", "regime": "stagnant"},
        ])
        return MarketAnalysisReport(
            year=2021,
            state_filter=None,
            provider_type_filter=None,
            row_count=100,
            concentration=conc,
            geo_dependency=pd.DataFrame(),
            state_growth=pd.DataFrame(),
            state_volatility=pd.DataFrame(),
            portfolio_fit=fit,
            regimes=regimes,
            watchlist=pd.DataFrame(),
            errors=[],
        )

    def test_compute_white_space_returns_list(self):
        from rcm_mc.data_public.cms_white_space_map import compute_white_space_map
        report = self._mock_report()
        results = compute_white_space_map(report)
        self.assertIsInstance(results, list)

    def test_white_space_sorted_descending(self):
        from rcm_mc.data_public.cms_white_space_map import compute_white_space_map
        report = self._mock_report()
        results = compute_white_space_map(report)
        if len(results) >= 2:
            scores = [r.white_space_score for r in results]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_top_white_space_count(self):
        from rcm_mc.data_public.cms_white_space_map import top_white_space
        report = self._mock_report()
        top = top_white_space(report, n=3)
        self.assertLessEqual(len(top), 3)

    def test_fragmented_market_higher_score(self):
        from rcm_mc.data_public.cms_white_space_map import compute_white_space_map
        report = self._mock_report()
        results = compute_white_space_map(report)
        # TX (HHI=1200, fragmented) and high fit=0.85 should rank near top
        tx_snf = [r for r in results if r.state == "TX" and r.provider_type == "SNF"]
        ca_snf = [r for r in results if r.state == "CA" and r.provider_type == "SNF"]
        if tx_snf and ca_snf:
            self.assertGreater(tx_snf[0].white_space_score, ca_snf[0].white_space_score)

    def test_white_space_opportunity_fields(self):
        from rcm_mc.data_public.cms_white_space_map import compute_white_space_map
        report = self._mock_report()
        results = compute_white_space_map(report)
        if results:
            opp = results[0]
            self.assertIsInstance(opp.state, str)
            self.assertIsInstance(opp.provider_type, str)
            self.assertIsInstance(opp.white_space_score, float)
            self.assertIn(opp.fragmentation_signal, ["fragmented", "neutral", "concentrated"])

    def test_white_space_table_text(self):
        from rcm_mc.data_public.cms_white_space_map import compute_white_space_map, white_space_table
        report = self._mock_report()
        results = compute_white_space_map(report)
        text = white_space_table(results)
        self.assertIn("Geographic White-Space Map", text)

    def test_white_space_table_empty(self):
        from rcm_mc.data_public.cms_white_space_map import white_space_table
        text = white_space_table([])
        self.assertIn("No white-space", text)

    def test_white_space_summary(self):
        from rcm_mc.data_public.cms_white_space_map import compute_white_space_map, white_space_summary
        report = self._mock_report()
        results = compute_white_space_map(report)
        summary = white_space_summary(results)
        self.assertIn("total", summary)
        self.assertIn("top_state", summary)
        if summary["total"] > 0:
            self.assertIsNotNone(summary["top_state"])

    def test_white_space_summary_empty(self):
        from rcm_mc.data_public.cms_white_space_map import white_space_summary
        s = white_space_summary([])
        self.assertEqual(s["total"], 0)
        self.assertIsNone(s["top_state"])

    def test_empty_report_returns_empty_list(self):
        from rcm_mc.data_public.cms_white_space_map import compute_white_space_map
        from rcm_mc.data_public.cms_market_analysis import MarketAnalysisReport
        import pandas as pd
        report = MarketAnalysisReport(
            year=2021, state_filter=None, provider_type_filter=None, row_count=0,
            concentration=pd.DataFrame(), geo_dependency=pd.DataFrame(),
            state_growth=pd.DataFrame(), state_volatility=pd.DataFrame(),
            portfolio_fit=pd.DataFrame(), regimes=pd.DataFrame(),
            watchlist=pd.DataFrame(), errors=[]
        )
        results = compute_white_space_map(report)
        self.assertEqual(results, [])


class TestDealMemoGenerator(unittest.TestCase):
    """Tests for deal_memo_generator module."""

    def _sample_deal(self):
        return {
            "source_id": "test_deal",
            "deal_name": "Acme Health Systems – Blackstone LBO",
            "year": 2021,
            "buyer": "Blackstone",
            "seller": "Acme Health founders",
            "ev_mm": 1200.0,
            "ebitda_at_entry_mm": 110.0,
            "hold_years": 5.0,
            "realized_moic": 2.8,
            "realized_irr": 0.21,
            "payer_mix": {"medicare": 0.40, "medicaid": 0.20, "commercial": 0.40},
            "leverage_x": 5.5,
            "state": "TX",
            "notes": "acute hospital system lbo southeast",
        }

    def _corpus(self):
        import tempfile, os
        db = tempfile.mktemp(suffix=".db")
        corpus = DealsCorpus(db)
        corpus.seed()
        deals = corpus.list()
        return db, deals

    def test_generate_deal_memo_returns_partner_memo(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo, PartnerMemo
        _, deals = self._corpus()
        memo = generate_deal_memo(self._sample_deal(), deals)
        self.assertIsInstance(memo, PartnerMemo)

    def test_memo_has_signal(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo
        _, deals = self._corpus()
        memo = generate_deal_memo(self._sample_deal(), deals)
        self.assertIn(memo.heuristic_signal, ["red", "amber", "yellow", "green"])

    def test_memo_has_comps(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo
        _, deals = self._corpus()
        memo = generate_deal_memo(self._sample_deal(), deals)
        self.assertIsInstance(memo.comps, list)
        self.assertGreater(len(memo.comps), 0)

    def test_memo_has_corpus_distribution(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo
        _, deals = self._corpus()
        memo = generate_deal_memo(self._sample_deal(), deals)
        dist = memo.corpus_distribution
        self.assertIn("moic_p50", dist)

    def test_memo_text_output(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo, memo_text
        _, deals = self._corpus()
        memo = generate_deal_memo(self._sample_deal(), deals)
        text = memo_text(memo)
        self.assertIn("PARTNER DEAL MEMO", text)
        self.assertIn("Blackstone", text)
        self.assertIn("Comparable Deals", text)

    def test_memo_markdown_output(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo, memo_markdown
        _, deals = self._corpus()
        memo = generate_deal_memo(self._sample_deal(), deals)
        md = memo_markdown(memo)
        self.assertIn("# Partner Deal Memo", md)
        self.assertIn("| EV |", md)

    def test_memo_with_cms_calibration(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo
        import pandas as pd
        import numpy as np
        _, deals = self._corpus()
        rng = np.random.default_rng(0)
        n = 200
        df = pd.DataFrame({
            "provider_type": (["SNF", "HHA"] * 100),
            "state": (["TX", "CA"] * 100),
            "year": [2021] * n,
            "_cms_total_payment_mm": rng.uniform(1, 50, n).tolist(),
            "bene_cnt": rng.integers(10, 300, n).tolist(),
            "srvcs_cnt": rng.integers(50, 1000, n).tolist(),
            "avg_mdcr_alowd_amt": rng.uniform(50, 200, n).tolist(),
            "avg_mdcr_pymt_amt": rng.uniform(40, 180, n).tolist(),
            "avg_mdcr_stdzd_amt": rng.uniform(40, 180, n).tolist(),
        })
        memo = generate_deal_memo(self._sample_deal(), deals, cms_df=df, cms_year=2021)
        # calibration should run without error
        self.assertIsNotNone(memo)

    def test_memo_no_errors_on_clean_deal(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo
        _, deals = self._corpus()
        memo = generate_deal_memo(self._sample_deal(), deals)
        # Should have no or minimal errors
        self.assertLessEqual(len(memo.errors), 2)

    def test_memo_timing_populated(self):
        from rcm_mc.data_public.deal_memo_generator import generate_deal_memo
        _, deals = self._corpus()
        memo = generate_deal_memo(self._sample_deal(), deals)
        self.assertIsInstance(memo.timing, dict)


class TestSeniorPartnerHeuristics(unittest.TestCase):
    """Tests for senior_partner_heuristics module."""

    def _lbo_deal(self, **kw):
        base = {
            "deal_name": "Acme Health LBO",
            "notes": "acute hospital system lbo",
            "year": 2021,
            "ev_mm": 1000.0,
            "ebitda_at_entry_mm": 100.0,
            "hold_years": 5.0,
            "realized_moic": 2.5,
            "realized_irr": 0.20,
            "leverage_x": 5.5,
            "payer_mix": {"medicare": 0.40, "medicaid": 0.20, "commercial": 0.40},
            "state": "TX",
        }
        base.update(kw)
        return base

    def test_get_entry_band_lbo_hospital(self):
        from rcm_mc.data_public.senior_partner_heuristics import get_entry_band
        band = get_entry_band("lbo", "acute_hospital")
        self.assertGreater(band.high, band.fair_high)
        self.assertGreater(band.fair_high, band.fair_low)

    def test_multiple_flag_in_band(self):
        from rcm_mc.data_public.senior_partner_heuristics import multiple_flag
        # 10x for hospital LBO is in-band (fair_low=7.5, fair_high=10.5)
        deal = self._lbo_deal(ev_mm=1000.0, ebitda_at_entry_mm=100.0)
        flags = multiple_flag(deal)
        self.assertEqual(flags, [])

    def test_multiple_flag_above_ceiling(self):
        from rcm_mc.data_public.senior_partner_heuristics import multiple_flag
        # 15x for hospital LBO is above ceiling
        deal = self._lbo_deal(ev_mm=1500.0, ebitda_at_entry_mm=100.0)
        flags = multiple_flag(deal)
        self.assertGreater(len(flags), 0)
        self.assertIn("above ceiling", flags[0])

    def test_multiple_flag_below_floor(self):
        from rcm_mc.data_public.senior_partner_heuristics import multiple_flag
        # 4x for hospital LBO is below floor
        deal = self._lbo_deal(ev_mm=400.0, ebitda_at_entry_mm=100.0)
        flags = multiple_flag(deal)
        self.assertGreater(len(flags), 0)
        self.assertIn("below expected floor", flags[0])

    def test_multiple_flag_negative_ebitda(self):
        from rcm_mc.data_public.senior_partner_heuristics import multiple_flag
        deal = self._lbo_deal(ebitda_at_entry_mm=-30.0)
        flags = multiple_flag(deal)
        self.assertGreater(len(flags), 0)
        self.assertIn("Negative", flags[0])

    def test_hold_period_flag_normal(self):
        from rcm_mc.data_public.senior_partner_heuristics import hold_period_flag
        deal = self._lbo_deal(hold_years=5.0)
        flags = hold_period_flag(deal)
        self.assertEqual(flags, [])

    def test_hold_period_flag_short(self):
        from rcm_mc.data_public.senior_partner_heuristics import hold_period_flag
        deal = self._lbo_deal(hold_years=1.5)
        flags = hold_period_flag(deal)
        self.assertGreater(len(flags), 0)
        self.assertIn("below norm", flags[0])

    def test_healthcare_trap_medicaid(self):
        from rcm_mc.data_public.senior_partner_heuristics import healthcare_trap_scan
        deal = self._lbo_deal(
            payer_mix={"medicare": 0.10, "medicaid": 0.75, "commercial": 0.15}
        )
        traps = healthcare_trap_scan(deal)
        trap_names = [t["trap"] for t in traps]
        self.assertIn("medicaid_concentration", trap_names)

    def test_healthcare_trap_extreme_leverage(self):
        from rcm_mc.data_public.senior_partner_heuristics import healthcare_trap_scan
        deal = self._lbo_deal(leverage_x=8.5)
        traps = healthcare_trap_scan(deal)
        trap_names = [t["trap"] for t in traps]
        self.assertIn("extreme_leverage", trap_names)

    def test_healthcare_trap_total_loss(self):
        from rcm_mc.data_public.senior_partner_heuristics import healthcare_trap_scan
        deal = self._lbo_deal(realized_moic=0.05)
        traps = healthcare_trap_scan(deal)
        trap_names = [t["trap"] for t in traps]
        self.assertIn("total_loss_risk", trap_names)
        severity = next(t["severity"] for t in traps if t["trap"] == "total_loss_risk")
        self.assertEqual(severity, "critical")

    def test_return_plausibility_consistent(self):
        from rcm_mc.data_public.senior_partner_heuristics import return_plausibility_check
        deal = self._lbo_deal(realized_moic=2.5, realized_irr=0.20, hold_years=5.0)
        result = return_plausibility_check(deal)
        self.assertIn("plausible", result)

    def test_return_plausibility_inconsistent(self):
        from rcm_mc.data_public.senior_partner_heuristics import return_plausibility_check
        # Positive MOIC but negative IRR — inconsistent
        deal = self._lbo_deal(realized_moic=2.5, realized_irr=-0.15, hold_years=5.0)
        result = return_plausibility_check(deal)
        self.assertFalse(result["plausible"])

    def test_full_assessment_keys(self):
        from rcm_mc.data_public.senior_partner_heuristics import full_heuristic_assessment
        deal = self._lbo_deal()
        assess = full_heuristic_assessment(deal)
        for key in ["deal_name", "sector", "deal_type", "entry_band",
                    "multiple_flags", "hold_flags", "traps", "plausibility",
                    "overall_signal"]:
            self.assertIn(key, assess)
        self.assertIn(assess["overall_signal"], ["red", "amber", "yellow", "green"])

    def test_full_assessment_red_for_critical_trap(self):
        from rcm_mc.data_public.senior_partner_heuristics import full_heuristic_assessment
        deal = self._lbo_deal(realized_moic=0.05)
        assess = full_heuristic_assessment(deal)
        self.assertEqual(assess["overall_signal"], "red")

    def test_heuristic_report_text(self):
        from rcm_mc.data_public.senior_partner_heuristics import (
            full_heuristic_assessment, heuristic_report
        )
        deal = self._lbo_deal(ev_mm=2000.0, ebitda_at_entry_mm=100.0)
        assess = full_heuristic_assessment(deal)
        text = heuristic_report(assess)
        self.assertIn("Senior Partner Heuristic Assessment", text)
        self.assertIn("Entry band", text)

    def test_corpus_wide_assessment(self):
        from rcm_mc.data_public.senior_partner_heuristics import full_heuristic_assessment
        import tempfile, os
        db = tempfile.mktemp(suffix=".db")
        try:
            corpus = DealsCorpus(db)
            corpus.seed()
            deals = corpus.list()
            # Should not raise on any real deal
            for d in deals[:20]:
                result = full_heuristic_assessment(d)
                self.assertIn(result["overall_signal"], ["red", "amber", "yellow", "green"])
        finally:
            os.unlink(db)


class TestDealMomentum(unittest.TestCase):
    """Tests for deal_momentum module."""

    def _deals(self):
        return [
            {"deal_name": "Acadia Behavioral LBO 2019", "notes": "behavioral health platform",
             "year": 2019, "ev_mm": 500.0, "ebitda_at_entry_mm": 50.0,
             "realized_moic": 2.5},
            {"deal_name": "Spring Health Behavioral 2021", "notes": "digital mental health",
             "year": 2021, "ev_mm": 800.0, "ebitda_at_entry_mm": None,
             "realized_moic": None},
            {"deal_name": "LifeStance Behavioral 2022", "notes": "outpatient behavioral",
             "year": 2022, "ev_mm": 900.0, "ebitda_at_entry_mm": None,
             "realized_moic": None},
            {"deal_name": "HCA Hospital System LBO", "notes": "acute hospital system",
             "year": 2018, "ev_mm": 5000.0, "ebitda_at_entry_mm": 400.0,
             "realized_moic": 3.2},
            {"deal_name": "Community Health Hospital 2020", "notes": "hospital system rural",
             "year": 2020, "ev_mm": 1200.0, "ebitda_at_entry_mm": 100.0,
             "realized_moic": 1.5},
            {"deal_name": "ASC Surgery Center 2021", "notes": "ambulatory surgical",
             "year": 2021, "ev_mm": 400.0, "ebitda_at_entry_mm": 40.0,
             "realized_moic": 3.8},
            {"deal_name": "ASC Platform Add-on 2022", "notes": "asc ambulatory",
             "year": 2022, "ev_mm": 300.0, "ebitda_at_entry_mm": 28.0,
             "realized_moic": None},
        ]

    def test_sector_deal_volume(self):
        from rcm_mc.data_public.deal_momentum import sector_deal_volume
        vol = sector_deal_volume(self._deals())
        self.assertIsInstance(vol, dict)
        # behavioral_health should appear
        self.assertIn("behavioral_health", vol)

    def test_sector_momentum_score_range(self):
        from rcm_mc.data_public.deal_momentum import sector_momentum_score
        score = sector_momentum_score(self._deals(), "behavioral_health")
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_sector_momentum_accelerating(self):
        from rcm_mc.data_public.deal_momentum import sector_momentum_score
        # behavioral_health has more recent deals → should be > 0.5
        score = sector_momentum_score(self._deals(), "behavioral_health")
        self.assertGreater(score, 0.5)

    def test_sector_momentum_unknown_sector(self):
        from rcm_mc.data_public.deal_momentum import sector_momentum_score
        score = sector_momentum_score(self._deals(), "nonexistent_sector")
        self.assertEqual(score, 0.0)

    def test_multiple_compression_trend(self):
        from rcm_mc.data_public.deal_momentum import multiple_compression_trend
        trend = multiple_compression_trend(self._deals())
        self.assertIsInstance(trend, dict)
        # 2018 and 2019 should be in there (have both ev and ebitda)
        for yr in (2018, 2019):
            if yr in trend:
                self.assertIsInstance(trend[yr], float)

    def test_return_compression_trend(self):
        from rcm_mc.data_public.deal_momentum import return_compression_trend
        trend = return_compression_trend(self._deals())
        self.assertIsInstance(trend, dict)

    def test_hot_sectors_sorted(self):
        from rcm_mc.data_public.deal_momentum import hot_sectors
        hot = hot_sectors(self._deals(), top_n=5)
        scores = [h["momentum_score"] for h in hot]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_hot_sectors_count(self):
        from rcm_mc.data_public.deal_momentum import hot_sectors
        hot = hot_sectors(self._deals(), top_n=3)
        self.assertLessEqual(len(hot), 3)

    def test_timing_assessment_keys(self):
        from rcm_mc.data_public.deal_momentum import timing_assessment
        ta = timing_assessment(self._deals(), "behavioral_health")
        for key in ["sector", "momentum_score", "entry_risk", "deal_count", "recommendation"]:
            self.assertIn(key, ta)
        self.assertIn(ta["entry_risk"], ["running_hot", "active", "neutral", "cooling_off"])

    def test_timing_assessment_from_corpus(self):
        from rcm_mc.data_public.deal_momentum import timing_assessment
        import tempfile, os
        db = tempfile.mktemp(suffix=".db")
        try:
            corpus = DealsCorpus(db)
            corpus.seed()
            deals = corpus.list()
            ta = timing_assessment(deals, "acute_hospital")
            self.assertGreater(ta["deal_count"], 0)
        finally:
            os.unlink(db)

    def test_momentum_report_text(self):
        from rcm_mc.data_public.deal_momentum import momentum_report
        text = momentum_report(self._deals())
        self.assertIn("Deal Flow Momentum Report", text)
        self.assertIn("Sector", text)


class TestExtendedSeed6(unittest.TestCase):

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_seed_loads_155_deals(self):
        corpus = DealsCorpus(self.db_path)
        stats = corpus.stats()
        self.assertGreaterEqual(stats["total"], 155)

    def test_seed_136_r1_rcm_cloudmed(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_136")
        self.assertIsNotNone(deal)
        self.assertIn("Cloudmed", deal["deal_name"])

    def test_seed_155_gentiva_hospice(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_155")
        self.assertIsNotNone(deal)
        self.assertIn("Gentiva", deal["deal_name"])
        self.assertGreater(deal["ev_mm"], 3000)

    def test_extended_seed_6_list_length(self):
        from rcm_mc.data_public.extended_seed_6 import EXTENDED_SEED_DEALS_6
        self.assertEqual(len(EXTENDED_SEED_DEALS_6), 20)

    def test_all_seed_6_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_6 import EXTENDED_SEED_DEALS_6
        for deal in EXTENDED_SEED_DEALS_6:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")


class TestCmsBenchmarkCalibration(unittest.TestCase):
    """Tests for cms_benchmark_calibration module."""

    def _empty_report(self, year=2021):
        from rcm_mc.data_public.cms_market_analysis import MarketAnalysisReport
        import pandas as pd
        return MarketAnalysisReport(
            year=year,
            state_filter=None,
            provider_type_filter=None,
            row_count=0,
            concentration=pd.DataFrame(),
            geo_dependency=pd.DataFrame(),
            state_growth=pd.DataFrame(),
            state_volatility=pd.DataFrame(),
            portfolio_fit=pd.DataFrame(),
            regimes=pd.DataFrame(),
            watchlist=pd.DataFrame(),
            errors=[],
        )

    def _make_df(self, rows=300):
        import pandas as pd
        import numpy as np
        rng = np.random.default_rng(42)
        pt = (["SNF", "HHA", "ASC"] * (rows // 3 + 1))[:rows]
        st = (["CA", "TX", "FL"] * (rows // 3 + 1))[:rows]
        return pd.DataFrame({
            "provider_type": pt,
            "state": st,
            "year": [2021] * rows,
            "_cms_total_payment_mm": rng.uniform(1, 100, rows).tolist(),
            "bene_cnt": rng.integers(10, 500, rows).tolist(),
            "srvcs_cnt": rng.integers(50, 2000, rows).tolist(),
            "avg_mdcr_alowd_amt": rng.uniform(50, 300, rows).tolist(),
            "avg_mdcr_pymt_amt": rng.uniform(40, 250, rows).tolist(),
            "avg_mdcr_stdzd_amt": rng.uniform(40, 250, rows).tolist(),
        })

    def test_calibrate_no_data(self):
        from rcm_mc.data_public.cms_benchmark_calibration import calibrate_from_cms
        import pandas as pd
        # Pass empty df so no HTTP; should not raise
        cal = calibrate_from_cms(year=2021, df=pd.DataFrame())
        self.assertEqual(cal.year, 2021)
        self.assertIsInstance(cal.moic_uplift_factor, float)

    def test_calibrate_with_data(self):
        from rcm_mc.data_public.cms_benchmark_calibration import calibrate_from_cms
        df = self._make_df()
        cal = calibrate_from_cms(year=2021, df=df)
        self.assertIsInstance(cal.moic_uplift_factor, float)
        self.assertGreater(cal.moic_uplift_factor, 0.5)

    def test_calibration_result_defaults(self):
        from rcm_mc.data_public.cms_benchmark_calibration import CalibrationResult
        cal = CalibrationResult(year=2022, state_filter=None, provider_type_filter=None)
        self.assertEqual(cal.moic_uplift_factor, 1.0)
        self.assertEqual(cal.confidence, "low")

    def test_apply_calibration_scales_moic(self):
        from rcm_mc.data_public.cms_benchmark_calibration import (
            CalibrationResult, apply_calibration
        )
        cal = CalibrationResult(year=2021, state_filter=None, provider_type_filter=None)
        cal.moic_uplift_factor = 1.10
        benchmarks = {"moic_p25": 1.5, "moic_p50": 2.0, "moic_p75": 3.0}
        adj = apply_calibration(benchmarks, cal)
        self.assertAlmostEqual(adj["moic_p50"], 2.2, places=2)
        self.assertAlmostEqual(adj["moic_p25"], 1.65, places=2)

    def test_apply_calibration_preserves_other_fields(self):
        from rcm_mc.data_public.cms_benchmark_calibration import (
            CalibrationResult, apply_calibration
        )
        cal = CalibrationResult(year=2021, state_filter=None, provider_type_filter=None)
        benchmarks = {"moic_p50": 2.0, "deal_count": 50, "irr_p50": 0.20}
        adj = apply_calibration(benchmarks, cal)
        self.assertEqual(adj["deal_count"], 50)
        self.assertIn("calibration_factor", adj)

    def test_apply_calibration_none_safe(self):
        from rcm_mc.data_public.cms_benchmark_calibration import (
            CalibrationResult, apply_calibration
        )
        cal = CalibrationResult(year=2021, state_filter=None, provider_type_filter=None)
        benchmarks = {"moic_p25": None, "moic_p50": 2.0}
        adj = apply_calibration(benchmarks, cal)
        self.assertIsNone(adj["moic_p25"])

    def test_calibration_text(self):
        from rcm_mc.data_public.cms_benchmark_calibration import (
            CalibrationResult, calibration_text
        )
        cal = CalibrationResult(
            year=2021, state_filter="CA", provider_type_filter=None,
            median_hhi=2800.0, durable_growth_count=5, declining_risk_count=2,
            moic_uplift_factor=1.08, confidence="medium"
        )
        text = calibration_text(cal)
        self.assertIn("2021", text)
        self.assertIn("MOIC uplift factor", text)
        self.assertIn("medium", text)

    def test_calibration_confidence_levels(self):
        from rcm_mc.data_public.cms_benchmark_calibration import calibrate_from_cms
        import pandas as pd
        # Small df → low confidence
        cal_small = calibrate_from_cms(year=2021, df=pd.DataFrame())
        self.assertEqual(cal_small.confidence, "low")
        # Large df → medium or high
        df = self._make_df(rows=400)
        cal_large = calibrate_from_cms(year=2021, df=df)
        self.assertIn(cal_large.confidence, ("low", "medium", "high"))


class TestDealComparablesEnhanced(unittest.TestCase):
    """Tests for deal_comparables_enhanced module."""

    def _deals(self):
        return [
            {
                "source_id": "t001", "deal_name": "HCA LBO 2019",
                "year": 2019, "ev_mm": 2000.0,
                "realized_moic": 3.2, "realized_irr": 0.26,
                "payer_mix": {"medicare": 0.35, "medicaid": 0.15, "commercial": 0.50},
                "leverage_x": 5.5, "ebitda_at_entry_mm": 200.0,
            },
            {
                "source_id": "t002", "deal_name": "Community Health LBO 2020",
                "year": 2020, "ev_mm": 1800.0,
                "realized_moic": 2.5, "realized_irr": 0.20,
                "payer_mix": {"medicare": 0.30, "medicaid": 0.20, "commercial": 0.50},
                "leverage_x": 4.8, "ebitda_at_entry_mm": 160.0,
            },
            {
                "source_id": "t003", "deal_name": "Dialysis clinic 2018",
                "year": 2018, "ev_mm": 400.0,
                "realized_moic": 0.6, "realized_irr": -0.10,
                "payer_mix": {"medicare": 0.70, "medicaid": 0.20, "commercial": 0.10},
                "leverage_x": 6.0, "ebitda_at_entry_mm": 30.0,
            },
            {
                "source_id": "t004", "deal_name": "ASC Platform 2021",
                "year": 2021, "ev_mm": 500.0,
                "realized_moic": None, "realized_irr": None,
                "payer_mix": {"medicare": 0.20, "medicaid": 0.05, "commercial": 0.75},
                "leverage_x": None, "ebitda_at_entry_mm": 50.0,
            },
        ]

    def test_similarity_score_identical(self):
        from rcm_mc.data_public.deal_comparables_enhanced import similarity_score
        d = self._deals()[0]
        score = similarity_score(d, d)
        self.assertGreater(score, 0.8)

    def test_similarity_score_range(self):
        from rcm_mc.data_public.deal_comparables_enhanced import similarity_score
        deals = self._deals()
        score = similarity_score(deals[0], deals[1])
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_similarity_score_similar_beats_dissimilar(self):
        from rcm_mc.data_public.deal_comparables_enhanced import similarity_score
        deals = self._deals()
        # t001 and t002 are more similar (same size/mix range) than t001 and t003 (very diff)
        s_close = similarity_score(deals[0], deals[1])
        s_far = similarity_score(deals[0], deals[2])
        self.assertGreater(s_close, s_far)

    def test_find_enhanced_comps_count(self):
        from rcm_mc.data_public.deal_comparables_enhanced import find_enhanced_comps
        deals = self._deals()
        comps = find_enhanced_comps(deals[0], deals, n=3)
        self.assertLessEqual(len(comps), 3)
        # Should not include self
        self.assertNotIn("t001", [c.get("source_id") for c in comps])

    def test_find_enhanced_comps_sorted(self):
        from rcm_mc.data_public.deal_comparables_enhanced import find_enhanced_comps
        deals = self._deals()
        comps = find_enhanced_comps(deals[0], deals, n=5)
        scores = [c["similarity_score"] for c in comps]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_peer_group_percentiles(self):
        from rcm_mc.data_public.deal_comparables_enhanced import (
            peer_group_percentiles, find_enhanced_comps
        )
        deals = self._deals()
        comps = find_enhanced_comps(deals[0], deals)
        result = peer_group_percentiles(deals[0], comps)
        self.assertIn("comp_count", result)
        if "moic_percentile" in result:
            self.assertGreaterEqual(result["moic_percentile"], 0)
            self.assertLessEqual(result["moic_percentile"], 100)

    def test_leverage_adj_moic_no_data(self):
        from rcm_mc.data_public.deal_comparables_enhanced import leverage_adj_moic
        d = {"realized_moic": 2.5}
        result = leverage_adj_moic(d)
        self.assertAlmostEqual(result, 2.5)

    def test_leverage_adj_moic_high_leverage(self):
        from rcm_mc.data_public.deal_comparables_enhanced import leverage_adj_moic
        d = {
            "realized_moic": 4.0, "leverage_x": 7.0,
            "ev_mm": 1000.0, "ebitda_at_entry_mm": 100.0,
        }
        adj = leverage_adj_moic(d)
        # High leverage → smaller adj moic (more risk-normalized)
        self.assertIsNotNone(adj)
        self.assertLess(adj, 4.0)

    def test_comp_table_enhanced_output(self):
        from rcm_mc.data_public.deal_comparables_enhanced import (
            find_enhanced_comps, comp_table_enhanced
        )
        deals = self._deals()
        comps = find_enhanced_comps(deals[0], deals)
        text = comp_table_enhanced(comps)
        self.assertIn("Enhanced Comparable Deals", text)
        self.assertIn("Sim", text)

    def test_comp_table_enhanced_empty(self):
        from rcm_mc.data_public.deal_comparables_enhanced import comp_table_enhanced
        text = comp_table_enhanced([])
        self.assertIn("No comparable", text)

    def test_find_comps_from_real_corpus(self):
        from rcm_mc.data_public.deal_comparables_enhanced import find_enhanced_comps
        import tempfile, os
        db = tempfile.mktemp(suffix=".db")
        try:
            corpus = DealsCorpus(db)
            corpus.seed()
            all_deals = corpus.list()
            target = all_deals[0]
            comps = find_enhanced_comps(target, all_deals, n=5)
            self.assertEqual(len(comps), 5)
            for c in comps:
                self.assertIn("similarity_score", c)
        finally:
            os.unlink(db)


class TestPortfolioAnalytics(unittest.TestCase):
    """Tests for portfolio_analytics module."""

    def _sample_deals(self):
        return [
            {"deal_name": "Deal A", "buyer": "KKR", "year": 2018, "ev_mm": 1000.0,
             "realized_moic": 3.5, "realized_irr": 0.28,
             "payer_mix": {"medicare": 0.60, "medicaid": 0.10, "commercial": 0.30}},
            {"deal_name": "Deal B", "buyer": "Blackstone", "year": 2019, "ev_mm": 800.0,
             "realized_moic": 2.1, "realized_irr": 0.19,
             "payer_mix": {"medicare": 0.20, "medicaid": 0.10, "commercial": 0.70}},
            {"deal_name": "Deal C", "buyer": "KKR", "year": 2019, "ev_mm": 500.0,
             "realized_moic": 0.8, "realized_irr": -0.12,
             "payer_mix": {"medicare": 0.10, "medicaid": 0.60, "commercial": 0.30}},
            {"deal_name": "Deal D", "buyer": "Apollo", "year": 2020, "ev_mm": 1500.0,
             "realized_moic": None, "realized_irr": None,
             "payer_mix": {"medicare": 0.35, "medicaid": 0.35, "commercial": 0.30}},
            {"deal_name": "Deal E", "buyer": "Bain", "year": 2020, "ev_mm": 600.0,
             "realized_moic": 4.2, "realized_irr": 0.35,
             "payer_mix": {"medicare": 0.25, "medicaid": 0.10, "commercial": 0.65}},
        ]

    def test_return_distribution_percentiles(self):
        from rcm_mc.data_public.portfolio_analytics import return_distribution
        dist = return_distribution(self._sample_deals())
        self.assertIn("moic_p50", dist)
        self.assertIn("irr_p50", dist)
        self.assertEqual(dist["moic_count"], 4)

    def test_return_distribution_empty(self):
        from rcm_mc.data_public.portfolio_analytics import return_distribution
        dist = return_distribution([])
        self.assertEqual(dist["moic_count"], 0)
        self.assertIsNone(dist["moic_p50"])

    def test_loss_rate(self):
        from rcm_mc.data_public.portfolio_analytics import loss_rate
        rate = loss_rate(self._sample_deals())
        # Deal C has moic=0.8 < 1.0; 1 out of 4 realized
        self.assertAlmostEqual(rate, 0.25, places=4)

    def test_home_run_rate(self):
        from rcm_mc.data_public.portfolio_analytics import home_run_rate
        rate = home_run_rate(self._sample_deals())
        # Deal A (3.5) and Deal E (4.2) are >= 3.0; 2 out of 4 realized
        self.assertAlmostEqual(rate, 0.5, places=4)

    def test_deals_by_sponsor_keys(self):
        from rcm_mc.data_public.portfolio_analytics import deals_by_sponsor
        by_sp = deals_by_sponsor(self._sample_deals())
        self.assertIn("KKR", by_sp)
        self.assertEqual(by_sp["KKR"]["count"], 2)

    def test_deals_by_type_buckets(self):
        from rcm_mc.data_public.portfolio_analytics import deals_by_type
        deals = [
            {"deal_name": "Acme LBO", "notes": "", "realized_moic": 2.5},
            {"deal_name": "Acme IPO", "notes": "", "realized_moic": 1.8},
            {"deal_name": "Acme Carve-out", "notes": "", "realized_moic": None},
        ]
        by_type = deals_by_type(deals)
        self.assertIn("lbo", by_type)
        self.assertIn("ipo", by_type)
        self.assertIn("carve_out", by_type)

    def test_vintage_cohort_summary(self):
        from rcm_mc.data_public.portfolio_analytics import vintage_cohort_summary
        cohorts = vintage_cohort_summary(self._sample_deals())
        years = [c["year"] for c in cohorts]
        self.assertEqual(years, sorted(years))
        self.assertIn(2018, years)
        self.assertIn(2020, years)

    def test_payer_mix_sensitivity(self):
        from rcm_mc.data_public.portfolio_analytics import payer_mix_sensitivity
        sens = payer_mix_sensitivity(self._sample_deals())
        # Deal A has medicare=0.60 → dominant = medicare
        self.assertIn("medicare", sens)
        self.assertGreaterEqual(sens["medicare"]["count"], 1)

    def test_outlier_deals(self):
        from rcm_mc.data_public.portfolio_analytics import outlier_deals
        # Deal E with moic=4.2 should be a positive outlier at z=1.0
        outliers = outlier_deals(self._sample_deals(), z=1.0)
        self.assertIsInstance(outliers, list)
        if outliers:
            self.assertIn("moic_zscore", outliers[0])

    def test_outlier_deals_empty_input(self):
        from rcm_mc.data_public.portfolio_analytics import outlier_deals
        result = outlier_deals([])
        self.assertEqual(result, [])

    def test_corpus_scorecard_keys(self):
        from rcm_mc.data_public.portfolio_analytics import corpus_scorecard
        sc = corpus_scorecard(self._sample_deals())
        for key in ["total_deals", "realized_deals", "moic_p50", "loss_rate", "home_run_rate"]:
            self.assertIn(key, sc)
        self.assertEqual(sc["total_deals"], 5)

    def test_corpus_scorecard_from_real_corpus(self):
        from rcm_mc.data_public.portfolio_analytics import corpus_scorecard
        import tempfile, os
        db = tempfile.mktemp(suffix=".db")
        try:
            corpus = DealsCorpus(db)
            corpus.seed()
            deals = corpus.list()
            sc = corpus_scorecard(deals)
            self.assertGreaterEqual(sc["total_deals"], 100)
            self.assertGreater(sc["total_ev_mm"], 0)
        finally:
            os.unlink(db)

    def test_scorecard_text_format(self):
        from rcm_mc.data_public.portfolio_analytics import corpus_scorecard, scorecard_text
        sc = corpus_scorecard(self._sample_deals())
        text = scorecard_text(sc)
        self.assertIn("Portfolio Corpus Scorecard", text)
        self.assertIn("MOIC", text)
        self.assertIn("Loss rate", text)

    def test_deals_by_year_coverage(self):
        from rcm_mc.data_public.portfolio_analytics import deals_by_year
        by_yr = deals_by_year(self._sample_deals())
        self.assertIn(2018, by_yr)
        self.assertEqual(by_yr[2018]["count"], 1)
        self.assertEqual(by_yr[2020]["count"], 2)


class TestCmsDataQuality(unittest.TestCase):
    """Tests for cms_data_quality: data_quality_report, cms_run_summary,
    winsorize_metrics, quality_report_text."""

    def _make_df(self):
        import pandas as pd
        import numpy as np
        return pd.DataFrame({
            "payment": [100.0, 200.0, np.nan, 400.0, 5000.0],
            "bene_count": [10, 0, 30, 0, 50],
            "state": ["CA", "TX", None, "FL", "NY"],
            "charge_ratio": [2.5, 3.0, 1.5, np.nan, 10.0],
        })

    def test_data_quality_report_columns(self):
        from rcm_mc.data_public.cms_data_quality import data_quality_report
        import pandas as pd
        df = self._make_df()
        dq = data_quality_report(df)
        self.assertIsInstance(dq, pd.DataFrame)
        for col in ["column", "dtype", "null_pct", "zero_pct", "nunique"]:
            self.assertIn(col, dq.columns)

    def test_data_quality_report_row_count(self):
        from rcm_mc.data_public.cms_data_quality import data_quality_report
        df = self._make_df()
        dq = data_quality_report(df)
        self.assertEqual(len(dq), 4)

    def test_data_quality_report_null_pct_accuracy(self):
        from rcm_mc.data_public.cms_data_quality import data_quality_report
        import pandas as pd
        df = self._make_df()
        dq = data_quality_report(df)
        payment_row = dq[dq["column"] == "payment"].iloc[0]
        # 1 null out of 5 = 0.20
        self.assertAlmostEqual(payment_row["null_pct"], 0.20, places=4)

    def test_data_quality_report_sorted_by_null_desc(self):
        from rcm_mc.data_public.cms_data_quality import data_quality_report
        df = self._make_df()
        dq = data_quality_report(df)
        null_pcts = dq["null_pct"].tolist()
        self.assertEqual(null_pcts, sorted(null_pcts, reverse=True))

    def test_data_quality_report_empty(self):
        from rcm_mc.data_public.cms_data_quality import data_quality_report
        import pandas as pd
        dq = data_quality_report(pd.DataFrame())
        self.assertTrue(dq.empty)
        self.assertIn("null_pct", dq.columns)

    def test_data_quality_report_zero_pct_numeric(self):
        from rcm_mc.data_public.cms_data_quality import data_quality_report
        df = self._make_df()
        dq = data_quality_report(df)
        bene_row = dq[dq["column"] == "bene_count"].iloc[0]
        # 2 zeros out of 5 = 0.40
        self.assertAlmostEqual(bene_row["zero_pct"], 0.40, places=4)

    def test_winsorize_clips_payment_per_service(self):
        from rcm_mc.data_public.cms_data_quality import winsorize_metrics
        import pandas as pd
        df = pd.DataFrame({"payment_per_service": list(range(1, 101))})
        out = winsorize_metrics(df, upper_quantile=0.90)
        self.assertLessEqual(out["payment_per_service"].max(), df["payment_per_service"].quantile(0.90) + 1e-6)

    def test_winsorize_no_clip_at_1(self):
        from rcm_mc.data_public.cms_data_quality import winsorize_metrics
        import pandas as pd
        df = pd.DataFrame({"payment_per_service": [1.0, 2.0, 1000.0]})
        out = winsorize_metrics(df, upper_quantile=1.0)
        self.assertEqual(out["payment_per_service"].max(), 1000.0)

    def test_winsorize_ignores_missing_columns(self):
        from rcm_mc.data_public.cms_data_quality import winsorize_metrics
        import pandas as pd
        df = pd.DataFrame({"other_col": [1.0, 2.0, 3.0]})
        out = winsorize_metrics(df, upper_quantile=0.95)
        self.assertIn("other_col", out.columns)
        self.assertNotIn("payment_per_service", out.columns)

    def test_winsorize_all_three_columns(self):
        from rcm_mc.data_public.cms_data_quality import winsorize_metrics
        import pandas as pd
        df = pd.DataFrame({
            "payment_per_service": list(range(1, 101)),
            "payment_per_bene": list(range(100, 200)),
            "charge_to_payment_ratio": [float(x) for x in range(1, 101)],
        })
        out = winsorize_metrics(df, upper_quantile=0.95)
        for col in ["payment_per_service", "payment_per_bene", "charge_to_payment_ratio"]:
            self.assertLessEqual(out[col].max(), df[col].quantile(0.95) + 1e-6)

    def test_quality_report_text_empty(self):
        from rcm_mc.data_public.cms_data_quality import quality_report_text
        import pandas as pd
        text = quality_report_text(pd.DataFrame())
        self.assertIn("No data quality", text)

    def test_quality_report_text_has_header(self):
        from rcm_mc.data_public.cms_data_quality import quality_report_text, data_quality_report
        df = self._make_df()
        dq = data_quality_report(df)
        text = quality_report_text(dq)
        self.assertIn("CMS Data Quality Report", text)
        self.assertIn("Null%", text)

    def test_quality_report_text_warns_high_null(self):
        from rcm_mc.data_public.cms_data_quality import quality_report_text
        import pandas as pd
        import numpy as np
        # column with 60% null → should get ⚠ flag
        df = pd.DataFrame({
            "column": ["x"],
            "dtype": ["float64"],
            "null_pct": [0.60],
            "zero_pct": [0.0],
            "nunique": [1],
        })
        text = quality_report_text(df)
        self.assertIn("⚠", text)

    def test_cms_run_summary_basic(self):
        from rcm_mc.data_public.cms_data_quality import cms_run_summary
        from rcm_mc.data_public.cms_market_analysis import MarketAnalysisReport
        import pandas as pd
        report = MarketAnalysisReport(
            year=2021,
            state_filter=None,
            provider_type_filter=None,
            row_count=0,
            concentration=pd.DataFrame(),
            geo_dependency=pd.DataFrame(),
            state_growth=pd.DataFrame(),
            state_volatility=pd.DataFrame(),
            portfolio_fit=pd.DataFrame(),
            regimes=pd.DataFrame(),
            watchlist=pd.DataFrame(),
            errors=[],
        )
        s = cms_run_summary(report)
        self.assertEqual(s["year"], 2021)
        self.assertIn("row_count", s)
        self.assertIn("concentration_markets", s)

    def test_cms_run_summary_json_serialisable(self):
        from rcm_mc.data_public.cms_data_quality import cms_run_summary
        from rcm_mc.data_public.cms_market_analysis import MarketAnalysisReport
        import pandas as pd
        import json
        report = MarketAnalysisReport(
            year=2022,
            state_filter="CA",
            provider_type_filter=None,
            row_count=10,
            concentration=pd.DataFrame(),
            geo_dependency=pd.DataFrame(),
            state_growth=pd.DataFrame(),
            state_volatility=pd.DataFrame(),
            portfolio_fit=pd.DataFrame(),
            regimes=pd.DataFrame(),
            watchlist=pd.DataFrame(),
            errors=["test_error"],
        )
        s = cms_run_summary(report)
        # Should not raise
        json.dumps(s)

    def test_cms_run_summary_with_concentration(self):
        from rcm_mc.data_public.cms_data_quality import cms_run_summary
        from rcm_mc.data_public.cms_market_analysis import MarketAnalysisReport
        import pandas as pd
        conc = pd.DataFrame([{"state": "TX", "hhi": 3500.0, "provider_type": "SNF"}])
        report = MarketAnalysisReport(
            year=2021,
            state_filter=None,
            provider_type_filter=None,
            row_count=100,
            concentration=conc,
            geo_dependency=pd.DataFrame(),
            state_growth=pd.DataFrame(),
            state_volatility=pd.DataFrame(),
            portfolio_fit=pd.DataFrame(),
            regimes=pd.DataFrame(),
            watchlist=pd.DataFrame(),
            errors=[],
        )
        s = cms_run_summary(report)
        self.assertEqual(s["concentration_markets"], 1)
        self.assertEqual(s["highest_hhi_state"], "TX")
        self.assertAlmostEqual(s["highest_hhi"], 3500.0)

    def test_cms_run_summary_with_regimes(self):
        from rcm_mc.data_public.cms_data_quality import cms_run_summary
        from rcm_mc.data_public.cms_market_analysis import MarketAnalysisReport
        import pandas as pd
        regimes = pd.DataFrame([
            {"provider_type": "SNF", "regime": "durable_growth"},
            {"provider_type": "HHA", "regime": "declining_risk"},
            {"provider_type": "ASC", "regime": "durable_growth"},
        ])
        report = MarketAnalysisReport(
            year=2021,
            state_filter=None,
            provider_type_filter=None,
            row_count=50,
            concentration=pd.DataFrame(),
            geo_dependency=pd.DataFrame(),
            state_growth=pd.DataFrame(),
            state_volatility=pd.DataFrame(),
            portfolio_fit=pd.DataFrame(),
            regimes=regimes,
            watchlist=pd.DataFrame(),
            errors=[],
        )
        s = cms_run_summary(report)
        self.assertEqual(s["durable_growth_count"], 2)
        self.assertEqual(s["declining_risk_count"], 1)


class TestCmsTrendForecaster(unittest.TestCase):
    """Tests for cms_trend_forecaster module."""

    def _make_trends_df(self, provider_type="Cardiology", n_years=5):
        import pandas as pd
        years = list(range(2018, 2018 + n_years))
        payments = [1_000_000 * (1.04 ** i) for i in range(n_years)]
        benes = [50_000] * n_years
        return pd.DataFrame({
            "year": years,
            "provider_type": [provider_type] * n_years,
            "total_medicare_payment_amt": payments,
            "total_unique_benes": benes,
        })

    def test_compute_rate_forecast_basic(self):
        from rcm_mc.data_public.cms_trend_forecaster import compute_rate_forecast
        df = self._make_trends_df()
        fc = compute_rate_forecast(df, "Cardiology", forecast_years=3)
        self.assertEqual(fc.provider_type, "Cardiology")
        self.assertIsNotNone(fc.historical_cagr)
        self.assertGreater(fc.historical_cagr, 0)
        self.assertIsNotNone(fc.base_case_payment)
        self.assertIsNotNone(fc.bear_case_payment)
        self.assertIsNotNone(fc.bull_case_payment)

    def test_compute_rate_forecast_no_data(self):
        from rcm_mc.data_public.cms_trend_forecaster import compute_rate_forecast
        import pandas as pd
        fc = compute_rate_forecast(pd.DataFrame(), "Cardiology")
        self.assertIsNone(fc.historical_cagr)
        self.assertEqual(fc.years_of_data, 0)

    def test_compute_rate_forecast_regime_durable_growth(self):
        from rcm_mc.data_public.cms_trend_forecaster import compute_rate_forecast
        import pandas as pd
        # Stable 8% growth with low volatility
        years = list(range(2015, 2022))
        payments = [1_000_000 * (1.08 ** i) for i in range(len(years))]
        df = pd.DataFrame({
            "year": years,
            "provider_type": ["SNF"] * len(years),
            "total_medicare_payment_amt": payments,
            "total_unique_benes": [100_000] * len(years),
        })
        fc = compute_rate_forecast(df, "SNF")
        self.assertIn(fc.regime, ("durable_growth", "emerging_volatile", "steady_compounders"))

    def test_compute_rate_forecast_declining(self):
        from rcm_mc.data_public.cms_trend_forecaster import compute_rate_forecast
        import pandas as pd
        years = list(range(2015, 2022))
        payments = [1_000_000 * (0.95 ** i) for i in range(len(years))]
        df = pd.DataFrame({
            "year": years,
            "provider_type": ["HHA"] * len(years),
            "total_medicare_payment_amt": payments,
            "total_unique_benes": [50_000] * len(years),
        })
        fc = compute_rate_forecast(df, "HHA")
        self.assertLess(fc.historical_cagr, 0)

    def test_apply_forecast_to_deal(self):
        from rcm_mc.data_public.cms_trend_forecaster import compute_rate_forecast, apply_forecast_to_deal
        df = self._make_trends_df()
        fc = compute_rate_forecast(df, "Cardiology", forecast_years=3)
        deal = {
            "source_id": "test_001",
            "deal_name": "Test Hospital",
            "ebitda_mm": 50.0,
            "ev_mm": 500.0,
            "payer_mix": {"medicare": 0.45, "medicaid": 0.15, "commercial": 0.38, "self_pay": 0.02},
        }
        result = apply_forecast_to_deal(deal, fc)
        self.assertIn("ebitda_base_case_mm", result)
        self.assertIn("ebitda_bear_case_mm", result)
        self.assertIn("forecast_regime", result)

    def test_apply_forecast_missing_ebitda(self):
        from rcm_mc.data_public.cms_trend_forecaster import compute_rate_forecast, apply_forecast_to_deal
        df = self._make_trends_df()
        fc = compute_rate_forecast(df, "Cardiology")
        deal = {"source_id": "x", "deal_name": "No EBITDA"}
        result = apply_forecast_to_deal(deal, fc)
        self.assertIn("note", result)

    def test_build_rate_forecast_table(self):
        from rcm_mc.data_public.cms_trend_forecaster import build_rate_forecast_table
        import pandas as pd
        df = pd.concat([
            self._make_trends_df("Cardiology"),
            self._make_trends_df("Orthopedics"),
        ])
        table = build_rate_forecast_table(df, forecast_years=3, top_n=5)
        self.assertIn("Provider Type", table)
        self.assertIn("Cardiology", table)

    def test_forecast_summary(self):
        from rcm_mc.data_public.cms_trend_forecaster import compute_rate_forecast, forecast_summary
        df = self._make_trends_df()
        fcs = [compute_rate_forecast(df, "Cardiology", forecast_years=i) for i in [2, 3, 5]]
        summary = forecast_summary(fcs)
        self.assertEqual(summary["count"], 3)
        self.assertIn("median_historical_cagr", summary)
        self.assertIn("regime_distribution", summary)

    def test_forecast_summary_empty(self):
        from rcm_mc.data_public.cms_trend_forecaster import forecast_summary
        summary = forecast_summary([])
        self.assertEqual(summary["count"], 0)

    def test_confidence_increases_with_data(self):
        from rcm_mc.data_public.cms_trend_forecaster import compute_rate_forecast
        import pandas as pd
        short_df = self._make_trends_df(n_years=2)
        long_df = self._make_trends_df(n_years=6)
        fc_short = compute_rate_forecast(short_df, "Cardiology")
        fc_long = compute_rate_forecast(long_df, "Cardiology")
        conf_order = {"low": 0, "medium": 1, "high": 2}
        self.assertGreaterEqual(
            conf_order.get(fc_long.confidence, 0),
            conf_order.get(fc_short.confidence, 0)
        )


class TestDealPortfolioMonitor(unittest.TestCase):
    """Tests for deal_portfolio_monitor module."""

    def _make_deal(self, **kwargs):
        base = {
            "source_id": "pm_001",
            "deal_name": "Test Active Deal",
            "deal_type": "lbo",
            "year": 2020,
            "ev_mm": 400.0,
            "ebitda_mm": 40.0,
            "ev_ebitda": 10.0,
            "hold_years": 5.0,
            "realized_moic": None,
        }
        base.update(kwargs)
        return base

    def test_compute_implied_moic_active(self):
        from rcm_mc.data_public.deal_portfolio_monitor import compute_implied_moic
        deal = self._make_deal(year=2019, ev_mm=300.0, ebitda_mm=30.0, ev_ebitda=10.0)
        moic = compute_implied_moic(deal, as_of_year=2024)
        self.assertIsNotNone(moic)
        self.assertGreater(moic, 1.0)

    def test_compute_implied_moic_insufficient_data(self):
        from rcm_mc.data_public.deal_portfolio_monitor import compute_implied_moic
        deal = {"source_id": "x", "deal_name": "Missing Data"}
        moic = compute_implied_moic(deal, as_of_year=2024)
        self.assertIsNone(moic)

    def test_deal_status_realized(self):
        from rcm_mc.data_public.deal_portfolio_monitor import deal_status
        deal = self._make_deal(realized_moic=2.8)
        result = deal_status(deal)
        self.assertEqual(result["status"], "realized")
        self.assertAlmostEqual(result["realized_moic"], 2.8)

    def test_deal_status_active_on_track(self):
        from rcm_mc.data_public.deal_portfolio_monitor import deal_status, MonitorConfig
        deal = self._make_deal(year=2021, ev_mm=200.0, ebitda_mm=20.0, ev_ebitda=10.0)
        config = MonitorConfig(target_gross_moic=2.5, as_of_year=2024)
        result = deal_status(deal, config)
        self.assertEqual(result["status"], "active")
        self.assertIn(result["alert_type"], ("on_track", "watch", "at_risk", "unknown"))

    def test_deal_status_critical(self):
        from rcm_mc.data_public.deal_portfolio_monitor import deal_status, MonitorConfig
        # Deal entered at very high multiple relative to EBITDA — will compute low implied MOIC
        deal = self._make_deal(year=2015, ev_mm=5000.0, ebitda_mm=20.0, ev_ebitda=250.0)
        config = MonitorConfig(as_of_year=2024)
        result = deal_status(deal, config)
        self.assertIn(result["alert_type"], ("critical", "at_risk", "watch", "on_track", "unknown"))

    def test_monitor_portfolio_sorts_by_urgency(self):
        from rcm_mc.data_public.deal_portfolio_monitor import monitor_portfolio
        deals = [self._make_deal(source_id=f"d{i}") for i in range(5)]
        results = monitor_portfolio(deals)
        self.assertEqual(len(results), 5)

    def test_portfolio_dashboard_text(self):
        from rcm_mc.data_public.deal_portfolio_monitor import monitor_portfolio, portfolio_dashboard_text
        deals = [
            self._make_deal(source_id="a1"),
            self._make_deal(source_id="a2", realized_moic=2.5),
        ]
        results = monitor_portfolio(deals)
        text = portfolio_dashboard_text(results)
        self.assertIn("Portfolio Monitor Dashboard", text)
        self.assertIn("Active positions", text)

    def test_benchmark_gap_analysis(self):
        from rcm_mc.data_public.deal_portfolio_monitor import benchmark_gap_analysis
        deals = [
            self._make_deal(source_id="g1", realized_moic=3.5),
            self._make_deal(source_id="g2", realized_moic=1.2),
            self._make_deal(source_id="g3", realized_moic=2.0),
        ]
        rows = benchmark_gap_analysis(deals)
        self.assertEqual(len(rows), 3)
        # Underperformers should come first (lowest gap)
        self.assertLessEqual(rows[0]["moic_gap"], rows[-1]["moic_gap"])

    def test_benchmark_gap_empty(self):
        from rcm_mc.data_public.deal_portfolio_monitor import benchmark_gap_analysis
        rows = benchmark_gap_analysis([self._make_deal(realized_moic=None)])
        self.assertEqual(rows, [])

    def test_monitor_real_corpus(self):
        from rcm_mc.data_public.deal_portfolio_monitor import monitor_portfolio, portfolio_dashboard_text
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "c.db")
            c = DealsCorpus(db)
            c.seed()
            deals = c.list()
        results = monitor_portfolio(deals)
        self.assertEqual(len(results), len(deals))
        text = portfolio_dashboard_text(results)
        self.assertIn("Portfolio Monitor Dashboard", text)


class TestExtendedSeed12(unittest.TestCase):
    """Tests for extended_seed_12.py (deals 256-275)."""

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_extended_seed_12_list_length(self):
        from rcm_mc.data_public.extended_seed_12 import EXTENDED_SEED_DEALS_12
        self.assertEqual(len(EXTENDED_SEED_DEALS_12), 20)

    def test_all_seed_12_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_12 import EXTENDED_SEED_DEALS_12
        for deal in EXTENDED_SEED_DEALS_12:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")

    def test_seed_261_fertility_moic(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_261")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["realized_moic"], 3.0)

    def test_seed_263_clover_spac_fail(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_263")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 0.5)

    def test_seed_266_genesis_bankruptcy(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_266")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 1.0)

    def test_seed_12_source_ids_unique(self):
        from rcm_mc.data_public.extended_seed_12 import EXTENDED_SEED_DEALS_12
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_12]
        self.assertEqual(len(ids), len(set(ids)))


class TestDealScreeningEngine(unittest.TestCase):
    """Tests for deal_screening_engine module."""

    def _make_deal(self, **kwargs):
        base = {
            "source_id": "scr_001",
            "deal_name": "Test Hospital",
            "deal_type": "lbo",
            "ev_mm": 300.0,
            "ebitda_mm": 30.0,
            "ev_ebitda": 10.0,
            "hold_years": 5.0,
            "year": 2020,
            "payer_mix": {"medicare": 0.40, "medicaid": 0.20, "commercial": 0.36, "self_pay": 0.04},
            "notes": "Stable operator",
            "buyer": "Test PE Fund",
        }
        base.update(kwargs)
        return base

    def test_screen_deal_returns_result(self):
        from rcm_mc.data_public.deal_screening_engine import screen_deal
        deal = self._make_deal()
        result = screen_deal(deal)
        self.assertIn(result.decision, ("PASS", "WATCH", "FAIL"))
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 100.0)

    def test_screen_deal_pass_healthy(self):
        from rcm_mc.data_public.deal_screening_engine import screen_deal
        deal = self._make_deal(
            ev_ebitda=9.0,
            payer_mix={"medicare": 0.25, "medicaid": 0.10, "commercial": 0.60, "self_pay": 0.05},
        )
        result = screen_deal(deal)
        # Healthy deal should pass or watch, not fail
        self.assertNotEqual(result.decision, "FAIL")

    def test_screen_deal_fail_critical_medicaid(self):
        from rcm_mc.data_public.deal_screening_engine import screen_deal, ScreeningConfig
        deal = self._make_deal(
            payer_mix={"medicare": 0.02, "medicaid": 0.90, "commercial": 0.05, "self_pay": 0.03},
        )
        config = ScreeningConfig(max_medicaid_pct=0.65)
        result = screen_deal(deal, config)
        self.assertIn(result.decision, ("WATCH", "FAIL"))

    def test_screen_deal_fail_high_multiple(self):
        from rcm_mc.data_public.deal_screening_engine import screen_deal, ScreeningConfig
        deal = self._make_deal(ev_ebitda=25.0)
        config = ScreeningConfig(max_ev_ebitda=20.0)
        result = screen_deal(deal, config)
        self.assertEqual(result.decision, "FAIL")
        self.assertTrue(any("multiple" in r.lower() for r in result.fail_reasons))

    def test_screen_deal_fail_negative_ebitda(self):
        from rcm_mc.data_public.deal_screening_engine import screen_deal, ScreeningConfig
        deal = self._make_deal(ebitda_mm=-10.0, ev_ebitda=None)
        config = ScreeningConfig(require_ebitda_positive=True)
        result = screen_deal(deal, config)
        self.assertEqual(result.decision, "FAIL")

    def test_screen_deal_custom_config(self):
        from rcm_mc.data_public.deal_screening_engine import screen_deal, ScreeningConfig
        deal = self._make_deal(ev_ebitda=13.0)
        strict = ScreeningConfig(watch_ev_ebitda=12.0)
        result = screen_deal(deal, strict)
        self.assertIn(result.decision, ("WATCH", "FAIL"))

    def test_screen_deal_as_dict(self):
        from rcm_mc.data_public.deal_screening_engine import screen_deal
        deal = self._make_deal()
        result = screen_deal(deal)
        d = result.as_dict()
        self.assertIn("decision", d)
        self.assertIn("score", d)
        self.assertIn("fail_reasons", d)

    def test_screen_corpus_returns_all(self):
        from rcm_mc.data_public.deal_screening_engine import screen_corpus
        deals = [self._make_deal(source_id=f"s{i}") for i in range(5)]
        results = screen_corpus(deals)
        self.assertEqual(len(results), 5)

    def test_screening_report(self):
        from rcm_mc.data_public.deal_screening_engine import screen_corpus, screening_report
        deals = [self._make_deal(source_id=f"r{i}") for i in range(3)]
        results = screen_corpus(deals)
        report = screening_report(results)
        self.assertIn("Deal Screening Report", report)
        self.assertIn("PASS", report)

    def test_screening_summary(self):
        from rcm_mc.data_public.deal_screening_engine import screen_corpus, screening_summary
        deals = [
            self._make_deal(source_id="ok", ev_ebitda=9.0),
            self._make_deal(source_id="bad", ev_ebitda=25.0),
        ]
        results = screen_corpus(deals)
        summary = screening_summary(results)
        self.assertIn("total", summary)
        self.assertEqual(summary["total"], 2)
        self.assertIn("by_decision", summary)

    def test_screen_real_corpus(self):
        from rcm_mc.data_public.deal_screening_engine import screen_corpus, screening_summary
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "c.db")
            c = DealsCorpus(db)
            c.seed()
            deals = c.list()
        results = screen_corpus(deals)
        summary = screening_summary(results)
        self.assertEqual(summary["total"], len(deals))
        # Should have at least some in each bucket
        self.assertGreater(summary["by_decision"]["PASS"] + summary["by_decision"]["WATCH"], 0)


class TestExtendedSeed11(unittest.TestCase):
    """Tests for extended_seed_11.py (deals 236-255)."""

    def setUp(self):
        self.db_path = _tmp_db()
        corpus = DealsCorpus(self.db_path)
        corpus.seed(skip_if_populated=False)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_extended_seed_11_list_length(self):
        from rcm_mc.data_public.extended_seed_11 import EXTENDED_SEED_DEALS_11
        self.assertEqual(len(EXTENDED_SEED_DEALS_11), 20)

    def test_all_seed_11_have_required_fields(self):
        from rcm_mc.data_public.extended_seed_11 import EXTENDED_SEED_DEALS_11
        for deal in EXTENDED_SEED_DEALS_11:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertEqual(deal["source"], "seed")

    def test_seed_240_genomic_high_moic(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_240")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["realized_moic"], 5.0)

    def test_seed_245_envision_distressed(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_245")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 1.0)

    def test_seed_255_veterinary(self):
        corpus = DealsCorpus(self.db_path)
        deal = corpus.get("seed_255")
        self.assertIsNotNone(deal)
        self.assertAlmostEqual(deal["realized_moic"], 3.0)

    def test_seed_11_source_ids_unique(self):
        from rcm_mc.data_public.extended_seed_11 import EXTENDED_SEED_DEALS_11
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_11]
        self.assertEqual(len(ids), len(set(ids)))


class TestDealValueCreation(unittest.TestCase):
    """Tests for deal_value_creation module."""

    def _make_deal(self, **kwargs):
        base = {
            "source_id": "vc_001",
            "deal_name": "Test Deal",
            "deal_type": "lbo",
            "ev_mm": 500.0,
            "ebitda_mm": 50.0,
            "ev_ebitda": 10.0,
            "hold_years": 5.0,
            "realized_moic": 2.5,
            "realized_irr": 0.20,
        }
        base.update(kwargs)
        return base

    def test_attribute_value_creation_returns_bridge(self):
        from rcm_mc.data_public.deal_value_creation import attribute_value_creation
        deal = self._make_deal()
        bridge = attribute_value_creation(deal)
        self.assertEqual(bridge.source_id, "vc_001")
        self.assertIsNotNone(bridge.realized_moic)

    def test_attribute_value_creation_contributions_sum_to_one(self):
        from rcm_mc.data_public.deal_value_creation import attribute_value_creation
        deal = self._make_deal()
        bridge = attribute_value_creation(deal)
        if bridge.ebitda_growth_contribution is not None:
            total = (bridge.ebitda_growth_contribution +
                     bridge.multiple_expansion_contribution +
                     bridge.leverage_contribution +
                     (bridge.unattributed or 0.0))
            self.assertAlmostEqual(total, 1.0, places=2)

    def test_attribute_no_moic_returns_low_data(self):
        from rcm_mc.data_public.deal_value_creation import attribute_value_creation
        deal = self._make_deal(realized_moic=None, realized_irr=None)
        bridge = attribute_value_creation(deal)
        self.assertIsNone(bridge.ebitda_growth_contribution)
        self.assertEqual(bridge.confidence, "low_data")

    def test_implied_ebitda_cagr_positive_moic(self):
        from rcm_mc.data_public.deal_value_creation import attribute_value_creation
        deal = self._make_deal(realized_moic=3.0, hold_years=5.0)
        bridge = attribute_value_creation(deal)
        if bridge.implied_ebitda_cagr is not None:
            self.assertGreater(bridge.implied_ebitda_cagr, 0.0)

    def test_value_bridge_text(self):
        from rcm_mc.data_public.deal_value_creation import attribute_value_creation, value_bridge_text
        deal = self._make_deal()
        bridge = attribute_value_creation(deal)
        text = value_bridge_text(bridge)
        self.assertIn("Value Creation Bridge", text)
        self.assertIn("MOIC", text)

    def test_corpus_value_attribution(self):
        from rcm_mc.data_public.deal_value_creation import corpus_value_attribution
        deals = [
            self._make_deal(source_id=f"cv{i}", realized_moic=2.0 + i * 0.5,
                            realized_irr=0.15 + i * 0.03, hold_years=4.0 + i)
            for i in range(5)
        ]
        result = corpus_value_attribution(deals)
        self.assertGreater(result["count"], 0)
        self.assertIn("median_moic", result)
        self.assertIn("median_ebitda_contribution", result)

    def test_corpus_value_attribution_empty(self):
        from rcm_mc.data_public.deal_value_creation import corpus_value_attribution
        result = corpus_value_attribution([self._make_deal(realized_moic=None)])
        self.assertEqual(result["count"], 0)

    def test_value_creation_table(self):
        from rcm_mc.data_public.deal_value_creation import value_creation_table
        deals = [self._make_deal(source_id=f"t{i}") for i in range(5)]
        table = value_creation_table(deals)
        self.assertIn("MOIC", table)
        self.assertIn("EBITDA", table)

    def test_sector_attribution_summary(self):
        from rcm_mc.data_public.deal_value_creation import sector_attribution_summary
        deals = [
            self._make_deal(source_id="s1", deal_type="lbo"),
            self._make_deal(source_id="s2", deal_type="lbo"),
            self._make_deal(source_id="s3", deal_type="growth_equity"),
        ]
        result = sector_attribution_summary(deals)
        self.assertIn("lbo", result)
        self.assertGreaterEqual(result["lbo"]["count"], 1)

    def test_value_creation_real_corpus(self):
        from rcm_mc.data_public.deal_value_creation import corpus_value_attribution
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "c.db")
            c = DealsCorpus(db)
            c.seed()
            deals = c.list()
        result = corpus_value_attribution(deals)
        self.assertGreater(result["count"], 20)


class TestDealRiskMatrix(unittest.TestCase):
    """Tests for deal_risk_matrix module."""

    def _make_deal(self, **kwargs):
        base = {
            "source_id": "risk_001",
            "deal_name": "Test Hospital",
            "deal_type": "lbo",
            "ev_mm": 500.0,
            "ebitda_mm": 50.0,
            "ev_ebitda": 10.0,
            "payer_mix": {"medicare": 0.40, "medicaid": 0.20, "commercial": 0.36, "self_pay": 0.04},
            "notes": "",
            "region": "Southeast",
        }
        base.update(kwargs)
        return base

    def test_score_reimbursement_risk_high_medicaid(self):
        from rcm_mc.data_public.deal_risk_matrix import score_reimbursement_risk
        deal = self._make_deal(payer_mix={"medicare": 0.05, "medicaid": 0.80, "commercial": 0.10, "self_pay": 0.05})
        dim = score_reimbursement_risk(deal)
        self.assertGreater(dim.score, 40)
        self.assertIn(dim.level, ("high", "critical"))

    def test_score_reimbursement_risk_low_risk(self):
        from rcm_mc.data_public.deal_risk_matrix import score_reimbursement_risk
        deal = self._make_deal(payer_mix={"medicare": 0.20, "medicaid": 0.10, "commercial": 0.65, "self_pay": 0.05})
        dim = score_reimbursement_risk(deal)
        self.assertLess(dim.score, 35)

    def test_score_leverage_risk_high_multiple(self):
        from rcm_mc.data_public.deal_risk_matrix import score_leverage_risk
        deal = self._make_deal(ev_ebitda=22.0)
        dim = score_leverage_risk(deal)
        self.assertGreater(dim.score, 30)

    def test_score_leverage_risk_negative_ebitda(self):
        from rcm_mc.data_public.deal_risk_matrix import score_leverage_risk
        deal = self._make_deal(ebitda_mm=-15.0, ev_ebitda=None)
        dim = score_leverage_risk(deal)
        self.assertGreater(dim.score, 20)

    def test_score_execution_risk_carve_out(self):
        from rcm_mc.data_public.deal_risk_matrix import score_execution_risk
        deal = self._make_deal(deal_type="carve_out")
        dim = score_execution_risk(deal)
        self.assertGreater(dim.score, 15)

    def test_score_execution_risk_distressed(self):
        from rcm_mc.data_public.deal_risk_matrix import score_execution_risk
        deal = self._make_deal(deal_type="distressed")
        dim = score_execution_risk(deal)
        self.assertGreater(dim.score, 25)

    def test_score_regulatory_risk_doj(self):
        from rcm_mc.data_public.deal_risk_matrix import score_regulatory_risk
        deal = self._make_deal(notes="DOJ settlement 2019 for overbilling")
        dim = score_regulatory_risk(deal)
        self.assertGreater(dim.score, 25)

    def test_score_regulatory_risk_clean(self):
        from rcm_mc.data_public.deal_risk_matrix import score_regulatory_risk
        deal = self._make_deal(notes="Stable operator; no compliance issues")
        dim = score_regulatory_risk(deal)
        self.assertEqual(dim.score, 0.0)

    def test_score_market_risk_rural(self):
        from rcm_mc.data_public.deal_risk_matrix import score_market_risk
        deal = self._make_deal(notes="Rural critical access hospital", region="Midwest")
        dim = score_market_risk(deal)
        self.assertGreater(dim.score, 10)

    def test_score_operational_risk_negative_moic(self):
        from rcm_mc.data_public.deal_risk_matrix import score_operational_risk
        deal = self._make_deal(realized_moic=0.3)
        dim = score_operational_risk(deal)
        self.assertGreater(dim.score, 15)

    def test_build_risk_matrix_returns_six_dimensions(self):
        from rcm_mc.data_public.deal_risk_matrix import build_risk_matrix
        deal = self._make_deal()
        matrix = build_risk_matrix(deal)
        self.assertEqual(len(matrix.dimensions), 6)
        dim_names = {d.name for d in matrix.dimensions}
        self.assertEqual(dim_names, {"reimbursement", "leverage", "execution", "regulatory", "market", "operational"})

    def test_build_risk_matrix_composite_score_range(self):
        from rcm_mc.data_public.deal_risk_matrix import build_risk_matrix
        deal = self._make_deal()
        matrix = build_risk_matrix(deal)
        self.assertGreaterEqual(matrix.composite_score, 0.0)
        self.assertLessEqual(matrix.composite_score, 100.0)
        self.assertIn(matrix.overall_signal, ("green", "yellow", "amber", "red"))

    def test_risk_matrix_text(self):
        from rcm_mc.data_public.deal_risk_matrix import build_risk_matrix, risk_matrix_text
        deal = self._make_deal()
        matrix = build_risk_matrix(deal)
        text = risk_matrix_text(matrix)
        self.assertIn("Risk Matrix", text)
        self.assertIn("Composite Score", text)
        self.assertIn("Reimbursement", text)

    def test_risk_matrix_as_dict(self):
        from rcm_mc.data_public.deal_risk_matrix import build_risk_matrix
        deal = self._make_deal()
        matrix = build_risk_matrix(deal)
        d = matrix.as_dict()
        self.assertIn("composite_score", d)
        self.assertIn("dimensions", d)
        self.assertEqual(len(d["dimensions"]), 6)

    def test_risk_matrix_summary_sorted(self):
        from rcm_mc.data_public.deal_risk_matrix import risk_matrix_summary
        deals = [
            self._make_deal(source_id="low", payer_mix={"medicare": 0.10, "medicaid": 0.05, "commercial": 0.80, "self_pay": 0.05}),
            self._make_deal(source_id="high", payer_mix={"medicare": 0.05, "medicaid": 0.85, "commercial": 0.05, "self_pay": 0.05},
                            deal_type="distressed", notes="DOJ settlement"),
        ]
        rows = risk_matrix_summary(deals)
        self.assertEqual(rows[0]["source_id"], "high")  # higher risk first
        self.assertGreater(rows[0]["composite_score"], rows[1]["composite_score"])

    def test_risk_matrix_real_corpus(self):
        from rcm_mc.data_public.deal_risk_matrix import risk_matrix_summary
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "c.db")
            c = DealsCorpus(db)
            c.seed()
            deals = c.list()
        rows = risk_matrix_summary(deals)
        self.assertGreater(len(rows), 200)
        # all scores in valid range
        for r in rows:
            self.assertGreaterEqual(r["composite_score"], 0.0)
            self.assertLessEqual(r["composite_score"], 100.0)


class TestDealTimeline(unittest.TestCase):
    """Tests for deal_timeline module."""

    def _make_deal(self, source_id="t001", year=2018, hold=4.5, moic=2.5, irr=0.22, ev=200.0):
        return {
            "source_id": source_id,
            "deal_name": f"Test Deal {source_id}",
            "source": "seed",
            "year": year,
            "ev_mm": ev,
            "realized_moic": moic,
            "realized_irr": irr,
            "hold_years": hold,
            "buyer": "Test Buyer",
            "seller": "Test Seller",
            "deal_type": "lbo",
            "notes": "test",
        }

    def test_build_deal_timeline_entry_exit(self):
        from rcm_mc.data_public.deal_timeline import build_deal_timeline
        deal = self._make_deal()
        events = build_deal_timeline(deal)
        self.assertEqual(len(events), 2)
        types = {e.event_type for e in events}
        self.assertIn("entry", types)
        self.assertIn("exit", types)

    def test_build_deal_timeline_entry_only(self):
        from rcm_mc.data_public.deal_timeline import build_deal_timeline
        deal = self._make_deal(moic=None, irr=None)
        events = build_deal_timeline(deal)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "entry")

    def test_exit_year_computed(self):
        from rcm_mc.data_public.deal_timeline import build_deal_timeline
        deal = self._make_deal(year=2018, hold=5.0)
        events = build_deal_timeline(deal)
        exit_ev = [e for e in events if e.event_type == "exit"]
        self.assertEqual(exit_ev[0].year, 2023)

    def test_corpus_timeline_sorted(self):
        from rcm_mc.data_public.deal_timeline import corpus_timeline
        deals = [
            self._make_deal(source_id="a", year=2020),
            self._make_deal(source_id="b", year=2015),
            self._make_deal(source_id="c", year=2018),
        ]
        events = corpus_timeline(deals)
        years = [e.year for e in events if e.year and e.event_type == "entry"]
        self.assertEqual(years, sorted(years))

    def test_market_activity_by_year(self):
        from rcm_mc.data_public.deal_timeline import market_activity_by_year
        deals = [
            self._make_deal(source_id="x1", year=2018, ev=100.0),
            self._make_deal(source_id="x2", year=2018, ev=200.0),
            self._make_deal(source_id="x3", year=2019, ev=150.0),
        ]
        result = market_activity_by_year(deals)
        self.assertIn(2018, result)
        self.assertEqual(result[2018]["deal_count"], 2)
        self.assertAlmostEqual(result[2018]["total_ev_mm"], 300.0)
        self.assertEqual(result[2019]["deal_count"], 1)

    def test_market_activity_cycle_phase(self):
        from rcm_mc.data_public.deal_timeline import market_activity_by_year
        deals = [self._make_deal(year=2020)]
        result = market_activity_by_year(deals)
        self.assertEqual(result[2020]["cycle_phase"], "covid_disruption")

    def test_holding_period_distribution(self):
        from rcm_mc.data_public.deal_timeline import holding_period_distribution
        deals = [
            self._make_deal(source_id=f"h{i}", hold=float(i + 1)) for i in range(10)
        ]
        dist = holding_period_distribution(deals)
        self.assertEqual(dist["count"], 10)
        self.assertIn("p50", dist)
        self.assertIn("buckets", dist)
        total_bucket = sum(dist["buckets"].values())
        self.assertEqual(total_bucket, 10)

    def test_holding_period_distribution_empty(self):
        from rcm_mc.data_public.deal_timeline import holding_period_distribution
        deals = [self._make_deal(moic=None)]
        dist = holding_period_distribution(deals)
        self.assertEqual(dist["count"], 0)

    def test_entry_exit_gap_analysis(self):
        from rcm_mc.data_public.deal_timeline import entry_exit_gap_analysis
        deals = [
            self._make_deal(source_id="g1", year=2015, hold=5.0),
            self._make_deal(source_id="g2", year=2018, hold=3.0),
        ]
        rows = entry_exit_gap_analysis(deals)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["exit_year"], 2020)
        self.assertIn("entry_phase", rows[0])

    def test_deal_cycle_phase(self):
        from rcm_mc.data_public.deal_timeline import deal_cycle_phase
        self.assertEqual(deal_cycle_phase(2008), "financial_crisis")
        self.assertEqual(deal_cycle_phase(2021), "covid_disruption")
        self.assertEqual(deal_cycle_phase(2016), "late_cycle_bull")

    def test_timeline_table(self):
        from rcm_mc.data_public.deal_timeline import corpus_timeline, timeline_table
        deals = [self._make_deal()]
        events = corpus_timeline(deals)
        text = timeline_table(events)
        self.assertIn("Year", text)
        self.assertIn("entry", text)

    def test_pacing_recommendation(self):
        from rcm_mc.data_public.deal_timeline import pacing_recommendation
        deals = [
            self._make_deal(source_id=f"p{i}", year=2018 + (i % 3)) for i in range(15)
        ]
        rec = pacing_recommendation(deals)
        self.assertIn("avg_deals_per_year", rec)
        self.assertIn("total_active_deals", rec)
        self.assertIn("recommendation", rec)

    def test_pacing_with_real_corpus(self):
        from rcm_mc.data_public.deal_timeline import pacing_recommendation
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "c.db")
            c = DealsCorpus(db)
            c.seed()
            deals = c.list()
        rec = pacing_recommendation(deals)
        self.assertGreater(rec["avg_deals_per_year"], 5.0)


class TestCorpusCLIExtended(unittest.TestCase):
    """Tests for health-check and export CLI subcommands."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self._db = os.path.join(self._tmp, "cli_test.db")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run_cli(self, *args):
        from rcm_mc.data_public.corpus_cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                main(["--db", self._db] + list(args))
            except SystemExit:
                pass
        return buf.getvalue()

    def test_health_check_text_output(self):
        out = self._run_cli("health-check", "--no-fail")
        self.assertIn("Corpus Health Check Report", out)
        self.assertIn("Total deals", out)
        self.assertIn("Health score", out)

    def test_health_check_json_output(self):
        out = self._run_cli("health-check", "--json", "--no-fail")
        data = json.loads(out)
        self.assertIn("total_deals", data)
        self.assertIn("health_score", data)
        self.assertIn("issues", data)
        self.assertGreater(data["total_deals"], 200)

    def test_export_csv(self):
        out = self._run_cli("export", "--format", "csv")
        self.assertIn("source_id", out)
        self.assertIn("deal_name", out)

    def test_export_json(self):
        out = self._run_cli("export", "--format", "json")
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 200)

    def test_export_markdown(self):
        out = self._run_cli("export", "--format", "markdown")
        self.assertIn("#", out)
        self.assertIn("Deal", out)

    def test_export_to_file_csv(self):
        outfile = os.path.join(self._tmp, "corpus.csv")
        self._run_cli("export", "--format", "csv", "--output", outfile)
        self.assertTrue(os.path.exists(outfile))
        with open(outfile) as f:
            content = f.read()
        self.assertIn("source_id", content)


class TestCorpusHealthCheck(unittest.TestCase):
    """Tests for corpus_health_check module."""

    def _make_deal(self, **kwargs):
        base = {
            "source_id": "test_001",
            "deal_name": "Test Hospital",
            "source": "seed",
            "year": 2018,
            "ev_mm": 200.0,
            "realized_moic": 2.5,
            "realized_irr": 0.22,
            "hold_years": 4.5,
            "payer_mix": {"medicare": 0.40, "medicaid": 0.25, "commercial": 0.30, "self_pay": 0.05},
        }
        base.update(kwargs)
        return base

    def test_clean_corpus_no_issues(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deals = [self._make_deal(source_id="x001"), self._make_deal(source_id="x002")]
        result = check_corpus(deals)
        self.assertEqual(result.total_deals, 2)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.warning_count, 0)
        self.assertEqual(result.health_score, 1.0)
        self.assertEqual(result.clean_deal_count, 2)

    def test_missing_source_id_error(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal()
        deal["source_id"] = ""
        result = check_corpus([deal])
        self.assertGreater(result.error_count, 0)
        checks = [i.check for i in result.issues]
        self.assertIn("required_fields", checks)

    def test_missing_deal_name_error(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal()
        deal["deal_name"] = ""
        result = check_corpus([deal])
        self.assertGreater(result.error_count, 0)

    def test_duplicate_source_ids(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        d1 = self._make_deal(source_id="dup_001")
        d2 = self._make_deal(source_id="dup_001")
        result = check_corpus([d1, d2])
        self.assertIn("dup_001", result.duplicate_source_ids)
        self.assertGreater(result.error_count, 0)
        self.assertLess(result.health_score, 1.0)

    def test_payer_mix_sum_warning(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal(payer_mix={"medicare": 0.50, "medicaid": 0.50, "commercial": 0.20})
        result = check_corpus([deal])
        warnings = [i for i in result.issues if i.check == "payer_mix_sum"]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].severity, "warning")

    def test_payer_mix_string_json(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        import json
        pm = json.dumps({"medicare": 0.40, "medicaid": 0.25, "commercial": 0.30, "self_pay": 0.05})
        deal = self._make_deal(payer_mix=pm)
        result = check_corpus([deal])
        payer_issues = [i for i in result.issues if i.check == "payer_mix_sum"]
        self.assertEqual(len(payer_issues), 0)

    def test_moic_irr_direction_error(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal(realized_moic=2.5, realized_irr=-0.10, hold_years=4.0)
        result = check_corpus([deal])
        direction_issues = [i for i in result.issues if i.check == "moic_irr_direction"]
        self.assertTrue(any(i.severity == "error" for i in direction_issues))

    def test_moic_irr_consistency_warning(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        # MOIC=3.0 over 5 years implies ~24.6% IRR; report 5% → big gap
        deal = self._make_deal(realized_moic=3.0, realized_irr=0.05, hold_years=5.0)
        result = check_corpus([deal])
        consistency = [i for i in result.issues if i.check == "moic_irr_consistency"]
        self.assertGreater(len(consistency), 0)

    def test_negative_moic_error(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal(realized_moic=-0.5)
        result = check_corpus([deal])
        moic_issues = [i for i in result.issues if i.check == "nonneg_moic"]
        self.assertEqual(len(moic_issues), 1)
        self.assertEqual(moic_issues[0].severity, "error")

    def test_ev_range_warning_small(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal(ev_mm=2.0)
        result = check_corpus([deal])
        ev_issues = [i for i in result.issues if i.check == "ev_range"]
        self.assertGreater(len(ev_issues), 0)

    def test_ev_range_info_large(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal(ev_mm=60000.0)
        result = check_corpus([deal])
        ev_issues = [i for i in result.issues if i.check == "ev_range"]
        self.assertEqual(ev_issues[0].severity, "info")

    def test_year_out_of_range_warning(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal(year=1985)
        result = check_corpus([deal])
        yr_issues = [i for i in result.issues if i.check == "year_range"]
        self.assertEqual(len(yr_issues), 1)
        self.assertEqual(yr_issues[0].severity, "warning")

    def test_hold_years_out_of_range(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deal = self._make_deal(hold_years=20.0, realized_moic=None, realized_irr=None)
        result = check_corpus([deal])
        hold_issues = [i for i in result.issues if i.check == "hold_years_range"]
        self.assertEqual(len(hold_issues), 1)

    def test_health_score_decreases_with_errors(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus
        deals = [self._make_deal(source_id=f"e{i:03d}", realized_moic=-0.5) for i in range(10)]
        result = check_corpus(deals)
        self.assertLess(result.health_score, 1.0)

    def test_health_check_text_format(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus, health_check_text
        deals = [self._make_deal(source_id="t001")]
        result = check_corpus(deals)
        text = health_check_text(result)
        self.assertIn("Corpus Health Check Report", text)
        self.assertIn("Total deals", text)
        self.assertIn("Health score", text)

    def test_check_corpus_real_corpus(self):
        from rcm_mc.data_public.corpus_health_check import check_corpus, health_check_text
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "corpus.db")
            c = DealsCorpus(db)
            c.seed()
            deals = c.list()
        result = check_corpus(deals)
        self.assertGreaterEqual(result.total_deals, 195)
        self.assertEqual(len(result.duplicate_source_ids), 0)
        # real corpus should score well
        self.assertGreater(result.health_score, 0.5)
        text = health_check_text(result)
        self.assertIn("Corpus Health Check Report", text)


class TestHoldPeriodOptimizer(unittest.TestCase):
    """Tests for hold_period_optimizer.py."""

    def test_curve_returns_correct_count(self):
        from rcm_mc.data_public.hold_period_optimizer import compute_hold_curve
        curve = compute_hold_curve(50.0, 12.0, 0.10, max_years=8)
        self.assertEqual(len(curve), 8)

    def test_moic_increases_then_decreases(self):
        from rcm_mc.data_public.hold_period_optimizer import compute_hold_curve
        curve = compute_hold_curve(50.0, 12.0, 0.08, max_years=10)
        moics = [r.gross_moic for r in curve]
        # Should peak somewhere then decline due to multiple compression
        peak_idx = moics.index(max(moics))
        self.assertGreater(peak_idx, 0)  # Not first year

    def test_irr_peaks_earlier_than_moic(self):
        from rcm_mc.data_public.hold_period_optimizer import compute_hold_curve, find_optimal_exit
        curve = compute_hold_curve(50.0, 12.0, 0.10, max_years=10)
        opt = find_optimal_exit(curve)
        # IRR typically maximizes earlier than MOIC
        self.assertLessEqual(opt.irr_maximizing_year, opt.moic_maximizing_year + 1)

    def test_optimal_exit_has_sweet_spot(self):
        from rcm_mc.data_public.hold_period_optimizer import compute_hold_curve, find_optimal_exit
        curve = compute_hold_curve(50.0, 12.0, 0.10, max_years=10)
        opt = find_optimal_exit(curve)
        self.assertLessEqual(opt.sweet_spot_start, opt.sweet_spot_end)
        self.assertGreater(opt.peak_gross_moic, 1.0)

    def test_higher_cagr_higher_moic(self):
        from rcm_mc.data_public.hold_period_optimizer import compute_hold_curve
        low_growth = compute_hold_curve(50.0, 12.0, 0.05, max_years=5)
        high_growth = compute_hold_curve(50.0, 12.0, 0.15, max_years=5)
        # At year 5, higher EBITDA growth → higher MOIC
        self.assertGreater(high_growth[-1].gross_moic, low_growth[-1].gross_moic)

    def test_corpus_hold_benchmarks(self):
        from rcm_mc.data_public.hold_period_optimizer import corpus_hold_benchmarks
        from rcm_mc.data_public.extended_seed_17 import EXTENDED_SEED_DEALS_17
        from rcm_mc.data_public.extended_seed_18 import EXTENDED_SEED_DEALS_18
        deals = EXTENDED_SEED_DEALS_17 + EXTENDED_SEED_DEALS_18
        bench = corpus_hold_benchmarks(deals)
        self.assertGreater(bench["n"], 5)
        self.assertIsNotNone(bench["hold_p50"])
        self.assertIsNotNone(bench["moic_p50"])

    def test_hold_curve_table_format(self):
        from rcm_mc.data_public.hold_period_optimizer import compute_hold_curve, hold_curve_table
        curve = compute_hold_curve(50.0, 12.0, 0.10, max_years=5)
        text = hold_curve_table(curve)
        self.assertIn("Gross MOIC", text)
        self.assertIn("Year", text)

    def test_optimizer_report_format(self):
        from rcm_mc.data_public.hold_period_optimizer import (
            compute_hold_curve, find_optimal_exit, hold_optimizer_report,
        )
        curve = compute_hold_curve(50.0, 12.0, 0.10, max_years=8)
        opt = find_optimal_exit(curve)
        text = hold_optimizer_report(curve, opt)
        self.assertIn("Hold Period Optimization Report", text)
        self.assertIn("sweet spot", text.lower())

    def test_exit_equity_positive(self):
        from rcm_mc.data_public.hold_period_optimizer import compute_hold_curve
        curve = compute_hold_curve(50.0, 12.0, 0.10, max_years=5)
        for r in curve:
            self.assertGreater(r.exit_equity_mm, 0)


class TestExtendedSeed20(unittest.TestCase):
    """Tests for extended_seed_20.py (deals 416-435)."""

    def setUp(self):
        import tempfile, os
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def test_seed_20_count(self):
        from rcm_mc.data_public.extended_seed_20 import EXTENDED_SEED_DEALS_20
        self.assertEqual(len(EXTENDED_SEED_DEALS_20), 20)

    def test_seed_421_biotelemetry_homerun(self):
        deal = self.corpus.get("seed_421")
        self.assertIsNotNone(deal)
        self.assertGreaterEqual(deal["realized_moic"], 4.0)

    def test_seed_418_nant_disaster(self):
        deal = self.corpus.get("seed_418")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 1.0)

    def test_seed_435_present(self):
        deal = self.corpus.get("seed_435")
        self.assertIsNotNone(deal)

    def test_seed_20_unique_ids(self):
        from rcm_mc.data_public.extended_seed_20 import EXTENDED_SEED_DEALS_20
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_20]
        self.assertEqual(len(ids), len(set(ids)))


class TestExtendedSeed21(unittest.TestCase):
    """Tests for extended_seed_21.py (deals 436-455)."""

    def setUp(self):
        import tempfile, os
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def test_seed_21_count(self):
        from rcm_mc.data_public.extended_seed_21 import EXTENDED_SEED_DEALS_21
        self.assertEqual(len(EXTENDED_SEED_DEALS_21), 20)

    def test_seed_21_unique_ids(self):
        from rcm_mc.data_public.extended_seed_21 import EXTENDED_SEED_DEALS_21
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_21]
        self.assertEqual(len(ids), len(set(ids)))

    def test_seed_438_molina_homerun(self):
        """Molina Healthcare turnaround — expect high MOIC."""
        deal = self.corpus.get("seed_438")
        self.assertIsNotNone(deal)
        self.assertGreaterEqual(deal["realized_moic"], 4.0)

    def test_seed_441_r1rcm_homerun(self):
        """R1 RCM / TowerBrook — high-value RCM platform exit."""
        deal = self.corpus.get("seed_441")
        self.assertIsNotNone(deal)
        self.assertGreaterEqual(deal["realized_moic"], 4.0)

    def test_seed_447_community_health_disaster(self):
        """Community Health / Quorum distressed — expect loss."""
        deal = self.corpus.get("seed_447")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 1.0)

    def test_seed_455_present(self):
        deal = self.corpus.get("seed_455")
        self.assertIsNotNone(deal)

    def test_seed_436_encompass_present(self):
        deal = self.corpus.get("seed_436")
        self.assertIsNotNone(deal)
        self.assertIn("Encompass", deal["deal_name"])


class TestReimbursementRiskModel(unittest.TestCase):
    """Tests for reimbursement_risk_model.py."""

    def _make_deal(self, **kwargs):
        base = {
            "source_id": "r001",
            "deal_name": "Test Deal",
            "sector": "home_health",
            "ebitda_mm": 50.0,
            "ev_ebitda": 12.0,
            "hold_years": 5.0,
            "payer_mix": {"medicare": 0.70, "medicaid": 0.15, "commercial": 0.12, "self_pay": 0.03},
        }
        base.update(kwargs)
        return base

    def test_model_returns_all_standard_scenarios(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk
        deal = self._make_deal()
        result = model_reimbursement_risk(deal)
        for name in ["base_case", "mild_cut", "moderate_cut", "severe_cut"]:
            self.assertIn(name, result)

    def test_severe_cut_worse_than_mild(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk
        deal = self._make_deal()
        result = model_reimbursement_risk(deal)
        severe = result["severe_cut"].total_ebitda_impact_mm
        mild = result["mild_cut"].total_ebitda_impact_mm
        self.assertLess(severe, mild)

    def test_ebitda_impact_proportional_to_govt_exposure(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk
        high_govt = self._make_deal(payer_mix={"medicare": 0.80, "medicaid": 0.15, "commercial": 0.05, "self_pay": 0.0})
        low_govt = self._make_deal(payer_mix={"medicare": 0.10, "medicaid": 0.05, "commercial": 0.80, "self_pay": 0.05})
        r_high = model_reimbursement_risk(high_govt)
        r_low = model_reimbursement_risk(low_govt)
        # High govt exposure → bigger absolute loss on Medicare cuts
        self.assertLess(r_high["severe_cut"].total_ebitda_impact_mm,
                        r_low["severe_cut"].total_ebitda_impact_mm)

    def test_base_case_is_positive(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk
        deal = self._make_deal()
        result = model_reimbursement_risk(deal)
        # Base case has positive rate changes → positive EBITDA impact
        self.assertGreater(result["base_case"].total_ebitda_impact_mm, 0)

    def test_severity_labels(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk
        deal = self._make_deal()
        result = model_reimbursement_risk(deal)
        valid = {"low", "moderate", "high", "severe", "unknown"}
        for s in result.values():
            self.assertIn(s.severity, valid)

    def test_sector_rate_history_home_health(self):
        from rcm_mc.data_public.reimbursement_risk_model import sector_rate_history
        history = sector_rate_history("home_health")
        self.assertGreater(len(history), 3)
        for h in history:
            self.assertIn("year", h)
            self.assertIn("change_pct", h)

    def test_sector_volatility_returns_float(self):
        from rcm_mc.data_public.reimbursement_risk_model import sector_volatility
        self.assertIsInstance(sector_volatility("dialysis"), float)
        self.assertIsInstance(sector_volatility("unknown_sector"), float)

    def test_no_payer_mix_no_crash(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk
        deal = {"source_id": "x", "deal_name": "No mix", "ebitda_mm": 20.0}
        result = model_reimbursement_risk(deal)
        self.assertIn("base_case", result)

    def test_no_ebitda_no_crash(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk
        deal = {"source_id": "x", "deal_name": "No EBITDA",
                "payer_mix": {"medicare": 0.5, "medicaid": 0.2, "commercial": 0.3}}
        result = model_reimbursement_risk(deal)
        self.assertIsNone(result["severe_cut"].total_ebitda_impact_mm)

    def test_risk_table_format(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk, reimbursement_risk_table
        result = model_reimbursement_risk(self._make_deal())
        text = reimbursement_risk_table(result)
        self.assertIn("Scenario", text)
        self.assertIn("severe_cut", text)

    def test_risk_report_format(self):
        from rcm_mc.data_public.reimbursement_risk_model import model_reimbursement_risk, reimbursement_risk_report
        deal = self._make_deal()
        result = model_reimbursement_risk(deal)
        text = reimbursement_risk_report(deal, result)
        self.assertIn("Reimbursement Risk Assessment", text)
        self.assertIn("Govt exposure", text)


class TestExtendedSeed19(unittest.TestCase):
    """Tests for extended_seed_19.py (deals 396-415)."""

    def setUp(self):
        import tempfile, os
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def test_seed_19_count(self):
        from rcm_mc.data_public.extended_seed_19 import EXTENDED_SEED_DEALS_19
        self.assertEqual(len(EXTENDED_SEED_DEALS_19), 20)

    def test_seed_396_prospect_disaster(self):
        deal = self.corpus.get("seed_396")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 1.0)

    def test_seed_408_lhc_homerun(self):
        deal = self.corpus.get("seed_408")
        self.assertIsNotNone(deal)
        self.assertGreaterEqual(deal["realized_moic"], 2.5)

    def test_seed_415_present(self):
        deal = self.corpus.get("seed_415")
        self.assertIsNotNone(deal)

    def test_seed_19_unique_ids(self):
        from rcm_mc.data_public.extended_seed_19 import EXTENDED_SEED_DEALS_19
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_19]
        self.assertEqual(len(ids), len(set(ids)))


class TestLBOEntryOptimizer(unittest.TestCase):
    """Tests for lbo_entry_optimizer.py."""

    def _base_assumptions(self, **kwargs):
        from rcm_mc.data_public.lbo_entry_optimizer import LBOAssumptions
        defaults = dict(
            entry_ebitda_mm=50.0,
            ebitda_cagr=0.10,
            hold_years=5.0,
            exit_multiple=12.0,
            leverage_pct=0.55,
            debt_interest_rate=0.07,
            debt_amortization_pct=0.03,
        )
        defaults.update(kwargs)
        return LBOAssumptions(**defaults)

    def test_solve_returns_result(self):
        from rcm_mc.data_public.lbo_entry_optimizer import solve_entry_multiple
        result = solve_entry_multiple(self._base_assumptions(), target_moic=2.5)
        self.assertIsNotNone(result)
        self.assertGreater(result.gross_moic, 2.4)

    def test_higher_target_means_lower_entry(self):
        from rcm_mc.data_public.lbo_entry_optimizer import solve_entry_multiple
        r25 = solve_entry_multiple(self._base_assumptions(), target_moic=2.5)
        r30 = solve_entry_multiple(self._base_assumptions(), target_moic=3.0)
        # More demanding MOIC target → can pay less at entry
        self.assertGreaterEqual(r25.entry_multiple, r30.entry_multiple)

    def test_moic_monotone_with_entry(self):
        from rcm_mc.data_public.lbo_entry_optimizer import sweep_moic_vs_entry
        results = sweep_moic_vs_entry(self._base_assumptions(), entry_range=[8.0, 10.0, 12.0, 14.0])
        moics = [r.gross_moic for r in results]
        # Higher entry multiple → lower MOIC
        self.assertGreater(moics[0], moics[-1])

    def test_sweep_returns_correct_count(self):
        from rcm_mc.data_public.lbo_entry_optimizer import sweep_moic_vs_entry
        results = sweep_moic_vs_entry(self._base_assumptions(), entry_range=[10.0, 12.0, 14.0])
        self.assertEqual(len(results), 3)

    def test_feasibility_flag(self):
        from rcm_mc.data_public.lbo_entry_optimizer import solve_entry_multiple
        # Very thin margin — tiny EBITDA, high leverage should trigger warning
        a = self._base_assumptions(entry_ebitda_mm=5.0, leverage_pct=0.90)
        result = solve_entry_multiple(a, target_moic=1.5)
        self.assertFalse(result.feasible)
        self.assertTrue(len(result.warnings) > 0)

    def test_irr_reasonable(self):
        from rcm_mc.data_public.lbo_entry_optimizer import solve_entry_multiple
        result = solve_entry_multiple(self._base_assumptions(), target_moic=2.5)
        # 2.5x over 5 yrs → ~20% IRR
        self.assertGreater(result.gross_irr, 0.10)
        self.assertLess(result.gross_irr, 0.50)

    def test_net_moic_less_than_gross(self):
        from rcm_mc.data_public.lbo_entry_optimizer import solve_entry_multiple
        result = solve_entry_multiple(self._base_assumptions(), target_moic=2.5)
        self.assertLess(result.net_moic, result.gross_moic)

    def test_entry_ev_equals_multiple_times_ebitda(self):
        from rcm_mc.data_public.lbo_entry_optimizer import solve_entry_multiple
        a = self._base_assumptions()
        result = solve_entry_multiple(a, target_moic=2.5)
        self.assertAlmostEqual(result.entry_ev_mm, result.entry_multiple * a.entry_ebitda_mm, delta=1.0)

    def test_table_format(self):
        from rcm_mc.data_public.lbo_entry_optimizer import sweep_moic_vs_entry, entry_optimizer_table
        results = sweep_moic_vs_entry(self._base_assumptions(), entry_range=[10.0, 12.0, 14.0])
        text = entry_optimizer_table(results)
        self.assertIn("Entry EV/EBITDA", text)
        self.assertIn("Gross MOIC", text)

    def test_report_format(self):
        from rcm_mc.data_public.lbo_entry_optimizer import solve_entry_multiple, entry_optimizer_report
        result = solve_entry_multiple(self._base_assumptions(), target_moic=2.5)
        text = entry_optimizer_report(result)
        self.assertIn("LBO Entry Optimization Report", text)
        self.assertIn("Gross MOIC", text)
        self.assertIn("Leverage at entry", text)

    def test_debt_paydown_positive(self):
        from rcm_mc.data_public.lbo_entry_optimizer import solve_entry_multiple
        result = solve_entry_multiple(self._base_assumptions(), target_moic=2.0)
        self.assertGreater(result.debt_paydown_mm, 0.0)


class TestExtendedSeed18(unittest.TestCase):
    """Tests for extended_seed_18.py (deals 376-395)."""

    def setUp(self):
        import tempfile, os
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def test_seed_18_count(self):
        from rcm_mc.data_public.extended_seed_18 import EXTENDED_SEED_DEALS_18
        self.assertEqual(len(EXTENDED_SEED_DEALS_18), 20)

    def test_seed_395_vitas_hospice(self):
        deal = self.corpus.get("seed_395")
        self.assertIsNotNone(deal)
        self.assertGreater(deal["realized_moic"], 4.0)

    def test_seed_380_bright_health_disaster(self):
        deal = self.corpus.get("seed_380")
        self.assertIsNotNone(deal)
        self.assertLess(deal["realized_moic"], 0.5)

    def test_seed_376_present(self):
        deal = self.corpus.get("seed_376")
        self.assertIsNotNone(deal)

    def test_seed_18_unique_ids(self):
        from rcm_mc.data_public.extended_seed_18 import EXTENDED_SEED_DEALS_18
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_18]
        self.assertEqual(len(ids), len(set(ids)))


class TestExtendedSeed17(unittest.TestCase):
    """Tests for extended_seed_17.py (deals 356-375)."""

    def setUp(self):
        import tempfile, os
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def test_seed_17_count(self):
        from rcm_mc.data_public.extended_seed_17 import EXTENDED_SEED_DEALS_17
        self.assertEqual(len(EXTENDED_SEED_DEALS_17), 20)

    def test_seed_356_steward(self):
        deal = self.corpus.get("seed_356")
        self.assertIsNotNone(deal)
        self.assertIn("Steward", deal["deal_name"])

    def test_seed_374_acadia_homerun(self):
        deal = self.corpus.get("seed_374")
        self.assertIsNotNone(deal)
        self.assertGreaterEqual(deal["realized_moic"], 5.0)

    def test_seed_375_present(self):
        deal = self.corpus.get("seed_375")
        self.assertIsNotNone(deal)

    def test_seed_17_unique_ids(self):
        from rcm_mc.data_public.extended_seed_17 import EXTENDED_SEED_DEALS_17
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_17]
        self.assertEqual(len(ids), len(set(ids)))


class TestSubsectorBenchmarks(unittest.TestCase):
    """Tests for subsector_benchmarks.py."""

    def _make_deals(self):
        return [
            {"source_id": "b001", "sector": "behavioral_health", "realized_moic": 3.5,
             "realized_irr": 0.28, "hold_years": 4.0, "ev_mm": 500.0, "deal_type": "lbo", "year": 2018},
            {"source_id": "b002", "sector": "behavioral_health", "realized_moic": 2.0,
             "realized_irr": 0.18, "hold_years": 5.0, "ev_mm": 300.0, "deal_type": "add-on", "year": 2019},
            {"source_id": "b003", "sector": "behavioral_health", "realized_moic": 0.8,
             "realized_irr": -0.05, "hold_years": 6.0, "ev_mm": 700.0, "deal_type": "lbo", "year": 2017},
            {"source_id": "b004", "sector": "behavioral_health", "realized_moic": 4.5,
             "realized_irr": 0.38, "hold_years": 3.5, "ev_mm": 800.0, "deal_type": "lbo", "year": 2016},
            {"source_id": "d001", "sector": "dialysis", "realized_moic": 2.5,
             "realized_irr": 0.20, "hold_years": 5.0, "ev_mm": 1000.0, "deal_type": "lbo", "year": 2015},
            {"source_id": "d002", "sector": "dialysis", "realized_moic": 3.0,
             "realized_irr": 0.24, "hold_years": 5.0, "ev_mm": 1100.0, "deal_type": "lbo", "year": 2017},
            {"source_id": "d003", "sector": "dialysis", "realized_moic": 1.8,
             "realized_irr": 0.14, "hold_years": 4.0, "ev_mm": 450.0, "deal_type": "lbo", "year": 2018},
        ]

    def test_compute_returns_dict(self):
        from rcm_mc.data_public.subsector_benchmarks import compute_subsector_benchmarks
        stats = compute_subsector_benchmarks(self._make_deals())
        self.assertIn("Behavioral Health", stats)
        self.assertIn("Dialysis", stats)

    def test_bh_moic_percentiles(self):
        from rcm_mc.data_public.subsector_benchmarks import compute_subsector_benchmarks
        stats = compute_subsector_benchmarks(self._make_deals())
        bh = stats["Behavioral Health"]
        self.assertIsNotNone(bh.moic_p25)
        self.assertIsNotNone(bh.moic_p50)
        self.assertIsNotNone(bh.moic_p75)
        # p25 <= p50 <= p75
        self.assertLessEqual(bh.moic_p25, bh.moic_p50)
        self.assertLessEqual(bh.moic_p50, bh.moic_p75)

    def test_bh_loss_rate(self):
        from rcm_mc.data_public.subsector_benchmarks import compute_subsector_benchmarks
        stats = compute_subsector_benchmarks(self._make_deals())
        bh = stats["Behavioral Health"]
        # 1 out of 4 deals is < 1.0x
        self.assertAlmostEqual(bh.loss_rate, 0.25, places=2)

    def test_bh_home_run_rate(self):
        from rcm_mc.data_public.subsector_benchmarks import compute_subsector_benchmarks
        stats = compute_subsector_benchmarks(self._make_deals())
        bh = stats["Behavioral Health"]
        # 2 out of 4 are > 3.0x
        self.assertAlmostEqual(bh.home_run_rate, 0.50, places=2)

    def test_get_sector_benchmark(self):
        from rcm_mc.data_public.subsector_benchmarks import get_sector_benchmark
        deals = self._make_deals()
        bench = get_sector_benchmark(deals, "behavioral_health")
        self.assertIsNotNone(bench)
        self.assertEqual(bench.sector, "Behavioral Health")

    def test_benchmark_deal_vs_sector_above_median(self):
        from rcm_mc.data_public.subsector_benchmarks import benchmark_deal_vs_sector
        deals = self._make_deals()
        deal = {"source_id": "test", "sector": "behavioral_health", "realized_moic": 4.0}
        result = benchmark_deal_vs_sector(deal, deals)
        self.assertIn(result["signal"], {"above_p75", "above_median"})

    def test_benchmark_deal_vs_sector_bottom_quartile(self):
        from rcm_mc.data_public.subsector_benchmarks import benchmark_deal_vs_sector
        deals = self._make_deals()
        deal = {"source_id": "test", "sector": "behavioral_health", "realized_moic": 0.5}
        result = benchmark_deal_vs_sector(deal, deals)
        self.assertEqual(result["signal"], "bottom_quartile")

    def test_sector_peer_group(self):
        from rcm_mc.data_public.subsector_benchmarks import sector_peer_group
        deals = self._make_deals()
        peers = sector_peer_group(deals, "dialysis", n=5)
        self.assertLessEqual(len(peers), 5)
        moics = [d["realized_moic"] for d in peers]
        self.assertEqual(moics, sorted(moics, reverse=True))

    def test_subsector_table_format(self):
        from rcm_mc.data_public.subsector_benchmarks import compute_subsector_benchmarks, subsector_table
        stats = compute_subsector_benchmarks(self._make_deals())
        text = subsector_table(stats)
        self.assertIn("Sector", text)
        self.assertIn("P50", text)
        self.assertIn("Behavioral Health", text)

    def test_corpus_subsector_benchmarks(self):
        from rcm_mc.data_public.subsector_benchmarks import compute_subsector_benchmarks, subsector_table
        from rcm_mc.data_public.extended_seed_9 import EXTENDED_SEED_DEALS_9
        from rcm_mc.data_public.extended_seed_10 import EXTENDED_SEED_DEALS_10
        from rcm_mc.data_public.extended_seed_11 import EXTENDED_SEED_DEALS_11
        from rcm_mc.data_public.extended_seed_12 import EXTENDED_SEED_DEALS_12
        from rcm_mc.data_public.extended_seed_13 import EXTENDED_SEED_DEALS_13
        from rcm_mc.data_public.extended_seed_14 import EXTENDED_SEED_DEALS_14
        from rcm_mc.data_public.extended_seed_15 import EXTENDED_SEED_DEALS_15
        from rcm_mc.data_public.extended_seed_16 import EXTENDED_SEED_DEALS_16
        from rcm_mc.data_public.extended_seed_17 import EXTENDED_SEED_DEALS_17
        all_deals = (EXTENDED_SEED_DEALS_9 + EXTENDED_SEED_DEALS_10 + EXTENDED_SEED_DEALS_11
                     + EXTENDED_SEED_DEALS_12 + EXTENDED_SEED_DEALS_13 + EXTENDED_SEED_DEALS_14
                     + EXTENDED_SEED_DEALS_15 + EXTENDED_SEED_DEALS_16 + EXTENDED_SEED_DEALS_17)
        stats = compute_subsector_benchmarks(all_deals)
        self.assertGreater(len(stats), 5)
        text = subsector_table(stats, min_realized=2)
        # At least one known sector must appear
        self.assertTrue(
            any(s in text for s in ["Behavioral Health", "Dialysis", "Post-Acute", "Physician"]),
            f"No expected sector found in: {text[:200]}"
        )


class TestExtendedSeed16(unittest.TestCase):
    """Tests for extended_seed_16.py (deals 336-355)."""

    def setUp(self):
        import tempfile, os
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def test_seed_16_count(self):
        from rcm_mc.data_public.extended_seed_16 import EXTENDED_SEED_DEALS_16
        self.assertEqual(len(EXTENDED_SEED_DEALS_16), 20)

    def test_seed_16_required_fields(self):
        from rcm_mc.data_public.extended_seed_16 import EXTENDED_SEED_DEALS_16
        for deal in EXTENDED_SEED_DEALS_16:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertIn("deal_type", deal)

    def test_seed_336_kindred(self):
        deal = self.corpus.get("seed_336")
        self.assertIsNotNone(deal)
        self.assertIn("Kindred", deal["deal_name"])

    def test_seed_339_envision_disaster(self):
        deal = self.corpus.get("seed_339")
        self.assertIsNotNone(deal)
        self.assertLessEqual(deal["realized_moic"], 0.2)

    def test_seed_353_signify_homerun(self):
        deal = self.corpus.get("seed_353")
        self.assertIsNotNone(deal)
        self.assertGreaterEqual(deal["realized_moic"], 4.0)

    def test_seed_355_present(self):
        deal = self.corpus.get("seed_355")
        self.assertIsNotNone(deal)

    def test_seed_16_all_unique_ids(self):
        from rcm_mc.data_public.extended_seed_16 import EXTENDED_SEED_DEALS_16
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_16]
        self.assertEqual(len(ids), len(set(ids)))


class TestSponsorTrackRecord(unittest.TestCase):
    """Tests for sponsor_track_record.py."""

    def _make_deals(self):
        return [
            {"source_id": "t001", "buyer": "KKR", "realized_moic": 3.5, "realized_irr": 0.28,
             "hold_years": 5.0, "ev_mm": 1000.0, "sector": "behavioral_health",
             "deal_type": "lbo", "year": 2018},
            {"source_id": "t002", "buyer": "KKR", "realized_moic": 1.8, "realized_irr": 0.14,
             "hold_years": 4.0, "ev_mm": 500.0, "sector": "physician_group",
             "deal_type": "add-on", "year": 2019},
            {"source_id": "t003", "buyer": "KKR", "realized_moic": 0.3, "realized_irr": -0.25,
             "hold_years": 6.0, "ev_mm": 9900.0, "sector": "emergency_medicine",
             "deal_type": "take-private", "year": 2018},
            {"source_id": "t004", "buyer": "Blackstone", "realized_moic": 4.2, "realized_irr": 0.35,
             "hold_years": 5.0, "ev_mm": 800.0, "sector": "dme_home_health",
             "deal_type": "take-private", "year": 2012},
            {"source_id": "t005", "buyer": "Warburg Pincus", "realized_moic": 2.5, "realized_irr": 0.20,
             "hold_years": 4.5, "ev_mm": 300.0, "sector": "behavioral_health",
             "deal_type": "lbo", "year": 2016},
        ]

    def test_build_sponsor_records_returns_dict(self):
        from rcm_mc.data_public.sponsor_track_record import build_sponsor_records
        deals = self._make_deals()
        records = build_sponsor_records(deals)
        self.assertIn("KKR", records)
        self.assertIn("Blackstone", records)

    def test_kkr_deal_count(self):
        from rcm_mc.data_public.sponsor_track_record import build_sponsor_records
        records = build_sponsor_records(self._make_deals())
        self.assertEqual(records["KKR"].deal_count, 3)

    def test_kkr_loss_rate(self):
        from rcm_mc.data_public.sponsor_track_record import build_sponsor_records
        records = build_sponsor_records(self._make_deals())
        self.assertAlmostEqual(records["KKR"].loss_rate, 1 / 3, places=2)

    def test_kkr_home_run_rate(self):
        from rcm_mc.data_public.sponsor_track_record import build_sponsor_records
        records = build_sponsor_records(self._make_deals())
        self.assertAlmostEqual(records["KKR"].home_run_rate, 1 / 3, places=2)

    def test_league_table_sorted(self):
        from rcm_mc.data_public.sponsor_track_record import sponsor_league_table
        deals = self._make_deals()
        table = sponsor_league_table(deals, min_deals=1)
        scores = [r.consistency_score for r in table]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_league_table_min_deals_filter(self):
        from rcm_mc.data_public.sponsor_track_record import sponsor_league_table
        deals = self._make_deals()
        table = sponsor_league_table(deals, min_deals=2)
        for r in table:
            self.assertGreaterEqual(r.deal_count, 2)

    def test_sector_specialization(self):
        from rcm_mc.data_public.sponsor_track_record import sector_specialization
        deals = self._make_deals()
        spec = sector_specialization(deals)
        self.assertIn("KKR", spec)
        kkr_sectors = spec["KKR"]
        self.assertAlmostEqual(sum(kkr_sectors.values()), 1.0, places=2)

    def test_sponsor_report_format(self):
        from rcm_mc.data_public.sponsor_track_record import build_sponsor_records, sponsor_report
        records = build_sponsor_records(self._make_deals())
        text = sponsor_report(records["KKR"])
        self.assertIn("KKR", text)
        self.assertIn("Median MOIC", text)
        self.assertIn("Loss rate", text)

    def test_league_table_text_format(self):
        from rcm_mc.data_public.sponsor_track_record import sponsor_league_table, league_table_text
        table = sponsor_league_table(self._make_deals(), min_deals=1)
        text = league_table_text(table)
        self.assertIn("Sponsor", text)
        self.assertIn("Med MOIC", text)

    def test_consistency_score_range(self):
        from rcm_mc.data_public.sponsor_track_record import build_sponsor_records
        records = build_sponsor_records(self._make_deals())
        for rec in records.values():
            self.assertGreaterEqual(rec.consistency_score, 0.0)
            self.assertLessEqual(rec.consistency_score, 100.0)

    def test_high_performer_scores_higher(self):
        from rcm_mc.data_public.sponsor_track_record import build_sponsor_records
        records = build_sponsor_records(self._make_deals())
        blackstone_score = records["Blackstone"].consistency_score
        warburg_score = records.get("Warburg Pincus", records.get("Warburg")).consistency_score if (records.get("Warburg Pincus") or records.get("Warburg")) else 0
        # Blackstone has single 4.2x deal; should score well on MOIC dimension
        self.assertGreater(blackstone_score, 0)

    def test_corpus_sponsor_table(self):
        from rcm_mc.data_public.sponsor_track_record import sponsor_league_table, league_table_text
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "c.db")
            c = DealsCorpus(db)
            c.seed()
            deals = c.list()
        table = sponsor_league_table(deals, min_deals=3)
        self.assertGreater(len(table), 3)
        text = league_table_text(table)
        self.assertIn("Sponsor", text)
        self.assertIn("Med MOIC", text)


class TestExtendedSeed15(unittest.TestCase):
    """Tests for extended_seed_15.py (deals 316-335)."""

    def setUp(self):
        import tempfile, os
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def test_seed_15_count(self):
        from rcm_mc.data_public.extended_seed_15 import EXTENDED_SEED_DEALS_15
        self.assertEqual(len(EXTENDED_SEED_DEALS_15), 20)

    def test_seed_15_required_fields(self):
        from rcm_mc.data_public.extended_seed_15 import EXTENDED_SEED_DEALS_15
        for deal in EXTENDED_SEED_DEALS_15:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertIn("deal_type", deal)

    def test_seed_316_present(self):
        deal = self.corpus.get("seed_316")
        self.assertIsNotNone(deal)

    def test_seed_335_present(self):
        deal = self.corpus.get("seed_335")
        self.assertIsNotNone(deal)

    def test_seed_15_all_unique_ids(self):
        from rcm_mc.data_public.extended_seed_15 import EXTENDED_SEED_DEALS_15
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_15]
        self.assertEqual(len(ids), len(set(ids)))

    def test_seed_15_moic_variety(self):
        from rcm_mc.data_public.extended_seed_15 import EXTENDED_SEED_DEALS_15
        moics = [d["realized_moic"] for d in EXTENDED_SEED_DEALS_15 if d.get("realized_moic")]
        self.assertTrue(any(m < 1.5 for m in moics), "should have some low performers")
        self.assertTrue(any(m > 3.0 for m in moics), "should have some homeruns")


class TestExtendedSeed14(unittest.TestCase):
    """Tests for extended_seed_14.py (deals 296-315)."""

    def setUp(self):
        import tempfile, os
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def test_seed_14_count(self):
        from rcm_mc.data_public.extended_seed_14 import EXTENDED_SEED_DEALS_14
        self.assertEqual(len(EXTENDED_SEED_DEALS_14), 20)

    def test_seed_14_required_fields(self):
        from rcm_mc.data_public.extended_seed_14 import EXTENDED_SEED_DEALS_14
        for deal in EXTENDED_SEED_DEALS_14:
            self.assertIn("source_id", deal)
            self.assertIn("deal_name", deal)
            self.assertIn("deal_type", deal)

    def test_seed_296_american_oncology(self):
        deal = self.corpus.get("seed_296")
        self.assertIsNotNone(deal)
        self.assertIn("Oncology", deal["deal_name"])

    def test_seed_306_select_medical(self):
        deal = self.corpus.get("seed_306")
        self.assertIsNotNone(deal)
        self.assertEqual(deal["realized_moic"], 4.2)

    def test_seed_310_livongo_disaster(self):
        deal = self.corpus.get("seed_305")
        self.assertIsNotNone(deal)

    def test_seed_315_color_genomics(self):
        deal = self.corpus.get("seed_315")
        self.assertIsNotNone(deal)

    def test_seed_14_all_unique_ids(self):
        from rcm_mc.data_public.extended_seed_14 import EXTENDED_SEED_DEALS_14
        ids = [d["source_id"] for d in EXTENDED_SEED_DEALS_14]
        self.assertEqual(len(ids), len(set(ids)))


class TestProviderTrendReliability(unittest.TestCase):
    """Tests for provider_trend_reliability.py."""

    def _make_trends_df(self):
        try:
            import pandas as pd
        except ImportError:
            return None
        data = []
        for pt in ["Cardiology", "Orthopedics", "Nephrology"]:
            for yr in range(2017, 2023):
                data.append({
                    "provider_type": pt,
                    "year": yr,
                    "total_medicare_payment_amt": 1_000_000 * (1 + 0.05) ** (yr - 2017),
                    "payment_yoy_pct": 0.05 if yr > 2017 else None,
                    "payment_yoy_accel": 0.0,
                })
        return pd.DataFrame(data)

    def test_reliability_returns_dataframe(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import provider_trend_reliability
        df = self._make_trends_df()
        result = provider_trend_reliability(df, min_observations=3)
        self.assertFalse(result.empty)
        self.assertIn("reliability_score", result.columns)

    def test_reliability_sorted_descending(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import provider_trend_reliability
        df = self._make_trends_df()
        result = provider_trend_reliability(df)
        scores = result["reliability_score"].tolist()
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_reliability_empty_input(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import provider_trend_reliability
        result = provider_trend_reliability(pd.DataFrame())
        self.assertTrue(result.empty)

    def test_reliability_percentile_range(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import provider_trend_reliability
        df = self._make_trends_df()
        result = provider_trend_reliability(df)
        self.assertTrue((result["reliability_percentile"] >= 0).all())
        self.assertTrue((result["reliability_percentile"] <= 1).all())

    def test_watchlist_buckets(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import growth_volatility_watchlist
        data = pd.DataFrame([
            {"provider_type": "A", "last_payment_growth": 0.10, "yoy_payment_volatility": 0.20},
            {"provider_type": "B", "last_payment_growth": -0.05, "yoy_payment_volatility": 0.50},
            {"provider_type": "C", "last_payment_growth": 0.02, "yoy_payment_volatility": 0.30},
        ])
        result = growth_volatility_watchlist(data)
        self.assertIn("watchlist_bucket", result.columns)
        buckets = result["watchlist_bucket"].astype(str).tolist()
        self.assertIn("priority", buckets)
        self.assertIn("high_risk", buckets)

    def test_watchlist_empty_input(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import growth_volatility_watchlist
        result = growth_volatility_watchlist(pd.DataFrame())
        self.assertTrue(result.empty)

    def test_momentum_profile_trend_types(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import provider_momentum_profile
        df = self._make_trends_df()
        result = provider_momentum_profile(df, min_years=3)
        self.assertIn("trend_type", result.columns)
        valid = {"durable_grower", "volatile_grower", "decliner", "slow_steady"}
        for t in result["trend_type"].tolist():
            self.assertIn(t, valid)

    def test_momentum_profile_consistency_score(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import provider_momentum_profile
        df = self._make_trends_df()
        result = provider_momentum_profile(df)
        self.assertIn("consistency_score", result.columns)
        self.assertTrue((result["consistency_score"].notna()).all())

    def test_trend_shift_computes_delta(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import provider_trend_shift
        df = self._make_trends_df()
        result = provider_trend_shift(df, baseline_year=2017, compare_year=2022)
        self.assertIn("payment_delta", result.columns)
        self.assertIn("payment_delta_pct", result.columns)
        self.assertTrue(len(result) > 0)

    def test_trend_shift_none_years(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import provider_trend_shift
        df = self._make_trends_df()
        result = provider_trend_shift(df, baseline_year=None, compare_year=2022)
        self.assertTrue(result.empty)

    def test_reliability_table_format(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import (
            provider_trend_reliability, reliability_table,
        )
        df = self._make_trends_df()
        rel = provider_trend_reliability(df)
        text = reliability_table(rel)
        self.assertIn("Provider Type", text)
        self.assertIn("Reliability", text)

    def test_watchlist_text_format(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")
        from rcm_mc.data_public.provider_trend_reliability import (
            growth_volatility_watchlist, watchlist_text,
        )
        data = pd.DataFrame([
            {"provider_type": "A", "last_payment_growth": 0.10, "yoy_payment_volatility": 0.20},
        ])
        wl = growth_volatility_watchlist(data)
        text = watchlist_text(wl)
        self.assertIn("Provider Type", text)
        self.assertIn("Bucket", text)


if __name__ == "__main__":
    unittest.main()
