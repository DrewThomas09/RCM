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
from .comparables import find_comparables, find_by_metrics, comparables_table
from .vintage_analysis import (
    get_vintage_stats,
    get_all_vintages,
    macro_cycle_summary,
    vintage_report,
    entry_timing_assessment,
    vintage_table,
)
from .leverage_analysis import (
    model_leverage,
    debt_capacity,
    coverage_ratio,
    covenant_headroom,
    stress_leverage,
    leverage_table,
)
from .exit_modeling import (
    ExitRoute,
    ExitAssumptions,
    model_exit,
    model_all_exits,
    build_value_bridge,
    exit_table,
    irr_sensitivity,
)
from .diligence_checklist import build_checklist, checklist_text, checklist_json
from .corpus_report import deal_brief, corpus_summary_report
from .rcm_benchmarks import (
    RCMBenchmark,
    get_benchmarks as get_rcm_benchmarks,
    get_all_benchmarks as get_all_rcm_benchmarks,
    benchmark_deal,
    rcm_opportunity,
    benchmarks_table as rcm_benchmarks_table,
)
from .regional_analysis import (
    classify_region,
    get_region_stats,
    get_all_regions,
    region_report,
    region_table,
    find_regional_comps,
)
from .cms_api_client import (
    fetch_pages,
    fetch_provider_utilization,
    fetch_geographic_variation,
    normalize_row,
    normalize_rows,
    resolve_column,
    safe_float,
    safe_int,
    CmsApiError,
    COLUMN_ALIASES,
    DATASET_IDS,
)
from .market_concentration import (
    market_concentration_summary,
    provider_geo_dependency,
    state_volatility_summary,
    state_growth_summary,
    state_portfolio_fit,
    concentration_table,
)
from .provider_regime import (
    yearly_trends,
    provider_volatility,
    provider_momentum_profile,
    growth_volatility_watchlist,
    provider_regime_classification,
    regime_table,
)
from .scrapers.cms_data import (
    fetch_cms_market_intelligence,
    cms_ingest_summary,
)
from .cms_market_analysis import (
    MarketAnalysisReport,
    run_market_analysis,
    white_space_opportunities,
    top_regimes,
    analysis_summary_text,
)
from .cms_stress_test import (
    provider_value_summary,
    provider_investability_summary,
    provider_stress_test,
    stress_scenario_grid,
    provider_operating_posture,
    stress_table,
    posture_table,
)
from .cms_opportunity_scoring import (
    enrich_features,
    state_provider_opportunities,
    provider_state_benchmark_flags,
    provider_screen,
    opportunity_table,
)
from .cms_advisory_memo import (
    build_advisory_memo,
    quick_memo,
)
from .cms_data_quality import (
    data_quality_report,
    cms_run_summary,
    winsorize_metrics,
    quality_report_text,
)
from .cms_white_space_map import (
    WhiteSpaceOpportunity,
    compute_white_space_map,
    top_white_space,
    white_space_table,
    white_space_summary,
)
from .deal_memo_generator import (
    PartnerMemo,
    generate_deal_memo,
    memo_text,
    memo_markdown,
    quick_deal_memo,
)
from .senior_partner_heuristics import (
    EntryMultipleBand,
    get_entry_band,
    multiple_flag,
    hold_period_flag,
    healthcare_trap_scan,
    return_plausibility_check,
    full_heuristic_assessment,
    heuristic_report,
)
from .deal_momentum import (
    sector_deal_volume,
    sector_momentum_score,
    multiple_compression_trend,
    return_compression_trend,
    hot_sectors,
    timing_assessment,
    momentum_report,
)
from .cms_benchmark_calibration import (
    CalibrationResult,
    calibrate_from_cms,
    apply_calibration,
    calibration_text,
)
from .deal_comparables_enhanced import (
    similarity_score,
    find_enhanced_comps,
    peer_group_percentiles,
    comp_table_enhanced,
    leverage_adj_moic,
)
from .portfolio_analytics import (
    return_distribution,
    deals_by_sponsor,
    deals_by_type,
    deals_by_year,
    vintage_cohort_summary,
    payer_mix_sensitivity,
    outlier_deals,
    corpus_scorecard,
    scorecard_text,
    loss_rate,
    home_run_rate,
)

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
    "find_comparables",
    "find_by_metrics",
    "comparables_table",
    "get_vintage_stats",
    "get_all_vintages",
    "macro_cycle_summary",
    "vintage_report",
    "entry_timing_assessment",
    "vintage_table",
    "model_leverage",
    "debt_capacity",
    "coverage_ratio",
    "covenant_headroom",
    "stress_leverage",
    "leverage_table",
    "ExitRoute",
    "ExitAssumptions",
    "model_exit",
    "model_all_exits",
    "build_value_bridge",
    "exit_table",
    "irr_sensitivity",
    "build_checklist",
    "checklist_text",
    "checklist_json",
    "deal_brief",
    "corpus_summary_report",
    "RCMBenchmark",
    "get_rcm_benchmarks",
    "get_all_rcm_benchmarks",
    "benchmark_deal",
    "rcm_opportunity",
    "rcm_benchmarks_table",
    "classify_region",
    "get_region_stats",
    "get_all_regions",
    "region_report",
    "region_table",
    "find_regional_comps",
    "fetch_pages",
    "fetch_provider_utilization",
    "fetch_geographic_variation",
    "normalize_row",
    "normalize_rows",
    "resolve_column",
    "safe_float",
    "safe_int",
    "CmsApiError",
    "COLUMN_ALIASES",
    "DATASET_IDS",
    "market_concentration_summary",
    "provider_geo_dependency",
    "state_volatility_summary",
    "state_growth_summary",
    "state_portfolio_fit",
    "concentration_table",
    "yearly_trends",
    "provider_volatility",
    "provider_momentum_profile",
    "growth_volatility_watchlist",
    "provider_regime_classification",
    "regime_table",
    "fetch_cms_market_intelligence",
    "cms_ingest_summary",
    "MarketAnalysisReport",
    "run_market_analysis",
    "white_space_opportunities",
    "top_regimes",
    "analysis_summary_text",
    "provider_value_summary",
    "provider_investability_summary",
    "provider_stress_test",
    "stress_scenario_grid",
    "provider_operating_posture",
    "stress_table",
    "posture_table",
    "enrich_features",
    "state_provider_opportunities",
    "provider_state_benchmark_flags",
    "provider_screen",
    "opportunity_table",
    "build_advisory_memo",
    "quick_memo",
    "data_quality_report",
    "cms_run_summary",
    "winsorize_metrics",
    "quality_report_text",
    "WhiteSpaceOpportunity",
    "compute_white_space_map",
    "top_white_space",
    "white_space_table",
    "white_space_summary",
    "PartnerMemo",
    "generate_deal_memo",
    "memo_text",
    "memo_markdown",
    "quick_deal_memo",
    "EntryMultipleBand",
    "get_entry_band",
    "multiple_flag",
    "hold_period_flag",
    "healthcare_trap_scan",
    "return_plausibility_check",
    "full_heuristic_assessment",
    "heuristic_report",
    "sector_deal_volume",
    "sector_momentum_score",
    "multiple_compression_trend",
    "return_compression_trend",
    "hot_sectors",
    "timing_assessment",
    "momentum_report",
    "CalibrationResult",
    "calibrate_from_cms",
    "apply_calibration",
    "calibration_text",
    "similarity_score",
    "find_enhanced_comps",
    "peer_group_percentiles",
    "comp_table_enhanced",
    "leverage_adj_moic",
    "return_distribution",
    "deals_by_sponsor",
    "deals_by_type",
    "deals_by_year",
    "vintage_cohort_summary",
    "payer_mix_sensitivity",
    "outlier_deals",
    "corpus_scorecard",
    "scorecard_text",
    "loss_rate",
    "home_run_rate",
]
