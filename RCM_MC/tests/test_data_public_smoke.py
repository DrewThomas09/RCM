"""Regression smoke tests for rcm_mc/data_public/* modules shipped on
the feature/deals-corpus branch.

Each test:
  1. Imports the module
  2. Calls compute_*()
  3. Asserts the result is a dataclass with key invariants populated

These are genuine regression guards — they catch any silent breakage
a future module addition might introduce via cross-module imports.

Plus per-module UI-render smoke tests: calls render_*({}) and asserts
the HTML is non-empty and contains the expected nav href.

Plus IC Brief edge-case coverage on 6 degenerate target inputs.

Written per REFLECT_PRUNE.md §6.2 recommendation.

Run with:
    pytest tests/test_data_public_smoke.py -q
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Backend smoke tests — one per data_public module
# ---------------------------------------------------------------------------

BACKEND_MODULES = [
    # (module_name, compute_fn_name, invariant_checker)
    # invariant_checker takes the result and returns a dict of properties
    # that should be truthy
    ("ncci_edits", "compute_ncci_scanner",
     lambda r: {"ptp_edits": r.total_ptp_edits > 0,
                "mue_limits": r.total_mue_limits > 0,
                "specialties": r.total_specialties_profiled > 0,
                "corpus": r.corpus_deal_count > 1000}),
    ("hfma_map_keys", "compute_hfma_map_keys",
     lambda r: {"kpis": r.total_keys > 0,
                "categories": len(r.category_stats) == 5,
                "corpus": r.corpus_deal_count > 1000}),
    ("medicare_utilization", "compute_medicare_utilization",
     lambda r: {"rows": r.warehouse_row_count > 0,
                "npis": r.distinct_npis > 0,
                "hcpcs": r.distinct_hcpcs > 0,
                "corpus": r.corpus_deal_count > 1000}),
    ("named_failure_library", "compute_named_failure_library",
     lambda r: {"patterns": r.total_patterns >= 16,
                "signals": r.total_signals > 0,
                "corpus": r.corpus_deal_count > 1000}),
    ("benchmark_curve_library", "compute_benchmark_library",
     lambda r: {"families": r.total_curve_families >= 8,
                "rows": r.total_curve_rows >= 388,
                "specialties": r.total_unique_specialties > 0}),
    ("backtest_harness", "compute_backtest_harness",
     lambda r: {"scored": r.metrics.total_deals_scored > 1000,
                "matrix": (r.confusion.true_positive + r.confusion.true_negative +
                           r.confusion.false_positive + r.confusion.false_negative) > 0}),
    ("adversarial_engine", "compute_adversarial_engine",
     lambda r: {"memos": r.total_memos > 0,
                "recommendations": (r.deals_stop_recommendation +
                                    r.deals_proceed_with_conditions +
                                    r.deals_proceed) > 0}),
    ("team_calculator", "compute_team_calculator",
     lambda r: {"cbsas": r.total_cbsas_tracked > 0,
                "episodes": len(r.episodes) == 5,
                "py5_exposure": r.total_programwide_downside_exposure_py5_b > 0}),
    ("survival_analysis", "compute_survival_analysis",
     lambda r: {"hold_curves": len(r.hold_period_curves) > 0,
                "specialty_curves": len(r.specialty_retention_curves) > 0,
                "cox_converged_or_ran": r.cox_model_summary.iterations_run > 0}),
    ("tuva_duckdb_integration", "compute_tuva_duckdb_integration",
     lambda r: {"ccd_fields": len(r.ccd_contract.fields) >= 25,
                "tuva_models": len(r.tuva_models) > 0,
                "migration_status": len(r.migration_status) > 0}),
    ("workbench_tooling", "compute_workbench_tooling",
     lambda r: {"features": len(r.features) > 0,
                "dimensions": len(r.interpretability_dimensions) == 6,
                "demo_rows": len(r.demo_rows) > 0}),
    ("doj_fca_tracker", "compute_doj_fca_tracker",
     lambda r: {"settlements": r.total_settlements >= 40,
                "total_amount_b": r.total_settlement_amount_b > 0,
                "provider_rollup": len(r.provider_type_rollup) > 0}),
    ("oig_workplan", "compute_oig_workplan",
     lambda r: {"items": r.total_items > 0,
                "aggregate_recovery": r.aggregate_recovery_mid_mm > 0}),
    ("qoe_deliverable", "compute_qoe_deliverable",
     lambda r: {"sections": len(r.sections) == 12,
                "ebitda_walk": len(r.ebitda_walk) > 0,
                "recommendation": r.overall_recommendation in ("GREEN", "YELLOW", "RED")}),
    ("cms_program_integrity_manual", "compute_program_integrity_manual",
     lambda r: {"chapters": r.total_chapters > 0,
                "sections": r.total_sections > 0,
                "contractors": r.total_contractors >= 6}),
    ("cpom_state_lattice", "compute_cpom_state_lattice",
     lambda r: {"states": r.total_states == 51,
                "strict": r.strict_tier_count > 0,
                "enforcement": len(r.enforcement_actions) > 0}),
    ("document_rag", "compute_document_rag",
     lambda r: {"passages": r.total_passages > 200,
                "sources": len(r.passages_by_source) > 5,
                "demo_queries": len(r.demo_queries) > 0}),
    ("track_record", "compute_track_record",
     lambda r: {"cases": r.aggregate.total_cases == 10,
                "all_flagged": (r.aggregate.correctly_flagged +
                                r.aggregate.partially_flagged) == r.aggregate.total_cases,
                "claims": len(r.buyer_pitch_claims) > 0}),
    ("cms_claims_processing_manual", "compute_claims_processing_manual",
     lambda r: {"chapters": r.total_chapters_documented > 0,
                "sections": r.total_sections > 0,
                "high_rel": r.high_pe_relevance_sections > 0}),
    ("site_neutral_simulator", "compute_site_neutral_simulator",
     lambda r: {"codes": r.total_codes_tracked > 0,
                "events": len(r.expansion_events) > 0,
                "corpus_exposure_mm": r.total_corpus_sn_cut_exposure_mm > 0}),
    ("nlrb_elections", "compute_nlrb_elections",
     lambda r: {"cases": r.total_cases > 0,
                "unions": r.total_unions_tracked > 0,
                "bargaining_unit": r.total_bargaining_unit_covered > 0}),
    ("velocity_metrics", "compute_velocity_metrics",
     lambda r: {"modules": r.total_shipped_modules > 0,
                "items": r.total_knowledge_items > 0,
                "moat_status": len(r.moat_status) == 7}),
    ("causal_inference", "compute_causal_inference",
     lambda r: {"questions": r.total_questions == 3,
                "estimates": len(r.estimates) > 0,
                "validations": len(r.validations) > 0}),
]


@pytest.mark.parametrize("module_name,fn_name,invariant_checker", BACKEND_MODULES)
def test_backend_compute_contract(module_name, fn_name, invariant_checker):
    """Every data_public module's compute_*() must return a dataclass with
    the key invariants populated. Catches silent breakage across
    refactors."""
    mod = __import__(f"rcm_mc.data_public.{module_name}", fromlist=[fn_name])
    fn = getattr(mod, fn_name)
    result = fn()
    assert result is not None, f"{module_name}.{fn_name}() returned None"
    invariants = invariant_checker(result)
    for key, passed in invariants.items():
        assert passed, f"{module_name}: invariant '{key}' failed"


# ---------------------------------------------------------------------------
# IC Brief — separate because it takes an argument
# ---------------------------------------------------------------------------

def test_ic_brief_with_default_target():
    from rcm_mc.data_public.ic_brief import compute_ic_brief, DEFAULT_DEMO_TARGET
    result = compute_ic_brief(DEFAULT_DEMO_TARGET)
    assert result is not None
    assert result.verdict.verdict in ("GREEN", "YELLOW", "RED")
    assert 0 <= result.verdict.composite_score <= 100
    assert 0 <= result.verdict.distress_probability <= 1
    assert result.corpus_deal_count > 1000


@pytest.mark.parametrize("deal_params", [
    {},
    {"ev_mm": "", "ebitda_mm": ""},
    {"ev_mm": "0", "ebitda_mm": "0"},
    {"ev_mm": "1000", "ebitda_mm": "-50"},
    {"commercial_share": "0", "medicare_share": "0",
     "medicaid_share": "0", "self_pay_share": "0"},
    {"sector": "Unknown / Not Listed", "deal_name": "X"},
])
def test_ic_brief_edge_cases(deal_params):
    """IC Brief UI should render without exception on degenerate inputs."""
    from rcm_mc.ui.data_public.ic_brief_page import render_ic_brief
    html = render_ic_brief(deal_params)
    assert len(html) > 5000
    assert "IC Brief" in html


# ---------------------------------------------------------------------------
# UI render smoke tests
# ---------------------------------------------------------------------------

UI_PAGES = [
    ("ncci_scanner_page", "render_ncci_scanner", "/ncci-scanner"),
    ("hfma_map_keys_page", "render_hfma_map_keys", "/hfma-map-keys"),
    ("medicare_utilization_page", "render_medicare_utilization", "/medicare-utilization"),
    ("named_failure_library_page", "render_named_failure_library", "/named-failures"),
    ("benchmark_curve_library_page", "render_benchmark_curves", "/benchmark-curves"),
    ("backtest_harness_page", "render_backtest_harness", "/backtest-harness"),
    ("adversarial_engine_page", "render_adversarial_engine", "/adversarial-engine"),
    ("team_calculator_page", "render_team_calculator", "/team-calculator"),
    ("survival_analysis_page", "render_survival_analysis", "/survival-analysis"),
    ("tuva_duckdb_integration_page", "render_tuva_duckdb_integration", "/tuva-duckdb"),
    ("workbench_tooling_page", "render_workbench_tooling", "/workbench-tooling"),
    ("ic_brief_page", "render_ic_brief", "/ic-brief"),
    ("doj_fca_tracker_page", "render_doj_fca_tracker", "/doj-fca"),
    ("cms_program_integrity_manual_page", "render_program_integrity_manual", "/cms-pim"),
    ("cpom_state_lattice_page", "render_cpom_lattice", "/cpom-lattice"),
    ("document_rag_page", "render_document_rag", "/rag"),
    ("track_record_page", "render_track_record", "/track-record"),
    ("cms_claims_processing_manual_page", "render_claims_processing_manual",
     "/cms-claims-manual"),
    ("site_neutral_simulator_page", "render_site_neutral_simulator", "/site-neutral"),
    ("nlrb_elections_page", "render_nlrb_elections", "/nlrb-elections"),
    ("velocity_metrics_page", "render_velocity_metrics", "/velocity"),
    ("causal_inference_page", "render_causal_inference", "/causal"),
]


@pytest.mark.parametrize("module_name,fn_name,expected_route", UI_PAGES)
def test_ui_page_renders(module_name, fn_name, expected_route):
    """Every UI page should render valid HTML > 1KB with its nav route present."""
    mod = __import__(f"rcm_mc.ui.data_public.{module_name}", fromlist=[fn_name])
    fn = getattr(mod, fn_name)
    html = fn({})
    assert len(html) > 1000, f"{module_name} HTML too small ({len(html)})"
    assert "<html" in html.lower(), f"{module_name} HTML missing root element"
    assert expected_route in html, (
        f"{module_name} does not reference its own route {expected_route}"
    )


# ---------------------------------------------------------------------------
# Cross-module integration sanity
# ---------------------------------------------------------------------------

def test_ic_brief_composes_all_modules():
    """IC Brief should pull in outputs from every moat-layer module.
    If any dependency breaks, IC Brief breaks first."""
    from rcm_mc.data_public.ic_brief import compute_ic_brief, DEFAULT_DEMO_TARGET
    result = compute_ic_brief(DEFAULT_DEMO_TARGET)
    assert result.verdict is not None
    assert result.ncci_exposure_summary.get("density") is not None
    assert result.oig_exposure_summary.get("provider_type") is not None
    assert result.bear_case_memo_narrative  # non-empty
    assert len(result.management_questions) > 0
    assert len(result.conditions_precedent) > 0
    assert len(result.red_flags) > 0


def test_track_record_composes_named_failures_and_ic_brief():
    """Track Record synthesizes a TargetInput per NF pattern and runs
    IC Brief scoring. Both must work end-to-end."""
    from rcm_mc.data_public.track_record import compute_track_record
    r = compute_track_record()
    assert r.aggregate.total_cases == 10
    # Each case must have a verdict from the live scoring stack
    for c in r.cases:
        assert c.platform_verdict in ("GREEN", "YELLOW", "RED")
        assert 0 <= c.platform_composite_score <= 100


def test_document_rag_indexes_all_knowledge_modules():
    """Document RAG should auto-index passages from all shipped knowledge
    modules. If a knowledge module's compute_*() changes shape, the RAG
    indexer must continue to work."""
    from rcm_mc.data_public.document_rag import compute_document_rag
    r = compute_document_rag()
    # Should include at least 5 distinct source labels
    assert len(r.passages_by_source) >= 5
    # Demo queries should all return something
    for q in r.demo_queries:
        assert len(q.retrieved_passage_ids) > 0


def test_velocity_reads_all_modules_live():
    """Velocity Metrics depends on calling compute_*() on every shipped
    knowledge module. If any crashes, Velocity's library_metrics drops
    an entry or zero-ships."""
    from rcm_mc.data_public.velocity_metrics import compute_velocity_metrics
    r = compute_velocity_metrics()
    assert r.total_shipped_modules > 0
    assert r.total_knowledge_items > 100
    assert len(r.moat_status) == 7
