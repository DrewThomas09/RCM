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
        n = self.corpus.seed(skip_if_populated=False)
        expected = len(_SEED_DEALS) + len(EXTENDED_SEED_DEALS) + len(EXTENDED_SEED_DEALS_2)
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

    def test_seed_loads_75_deals(self):
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


if __name__ == "__main__":
    unittest.main()
