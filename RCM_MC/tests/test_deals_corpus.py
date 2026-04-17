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
        n = self.corpus.seed(skip_if_populated=False)
        expected = len(_SEED_DEALS) + len(EXTENDED_SEED_DEALS)
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


if __name__ == "__main__":
    unittest.main()
