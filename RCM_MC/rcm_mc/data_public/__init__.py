"""Public deals corpus and calibration data for SeekingChartis.

Submodules:
    deals_corpus      – SQLite schema + CRUD for public_deals table (55 seed deals)
    extended_seed     – second batch of 20 seed deals
    normalizer        – normalize raw deal dicts to canonical schema
    base_rates        – P25/P50/P75 MOIC benchmarks by hospital size + payer mix
    backtester        – backtest platform predictions vs realized outcomes
    pe_intelligence   – IRR bands, red flags, heuristics by deal type
    payer_sensitivity – Medicaid cut / MA creep / commercial loss scenarios
    deal_scorer       – 0-100 data quality + credibility score per deal
    ingest_pipeline   – full corpus ingest from all sources in one call
    corpus_cli        – CLI: seed/stats/query/rates/intel/sensitivity/full-ingest
    scrapers          – SEC EDGAR and PE portfolio page scrapers

Quick start:
    from rcm_mc.data_public import DealsCorpus, full_intelligence_report
    corpus = DealsCorpus("corpus.db")
    corpus.seed()
    deal = corpus.get("seed_007")
    report = full_intelligence_report(deal, corpus_db_path="corpus.db")
    print(report.as_dict())
"""
from __future__ import annotations

from .deals_corpus import DealsCorpus
from .normalizer import normalize_raw, normalize_batch, validate
from .base_rates import get_benchmarks, get_benchmarks_by_size, get_benchmarks_by_payer, full_summary
from .backtester import match_deals, summary_stats as backtest_summary
from .pe_intelligence import full_intelligence_report, classify_deal_type, detect_red_flags
from .payer_sensitivity import run_all_scenarios, sensitivity_table
from .deal_scorer import score_deal, score_corpus, quality_report
from .ingest_pipeline import run_full_ingest

__all__ = [
    "DealsCorpus",
    "normalize_raw",
    "normalize_batch",
    "validate",
    "get_benchmarks",
    "get_benchmarks_by_size",
    "get_benchmarks_by_payer",
    "full_summary",
    "match_deals",
    "backtest_summary",
    "full_intelligence_report",
    "classify_deal_type",
    "detect_red_flags",
    "run_all_scenarios",
    "sensitivity_table",
    "score_deal",
    "score_corpus",
    "quality_report",
    "run_full_ingest",
]
