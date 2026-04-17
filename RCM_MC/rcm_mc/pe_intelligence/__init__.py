"""PE Intelligence Brain — senior-partner judgment layer over a packet.

This package does not modify any existing calculation. It consumes a
``DealAnalysisPacket`` and emits a ``PartnerReview`` with three kinds
of findings:

1. **Reasonableness bands** — sanity-check IRRs, EBITDA margins, and
   lever realizability against size / payer-mix peer ranges. Flags when
   a model output drifts outside the band a senior partner would
   accept without a very good story.
2. **Heuristics** — codified PE rules of thumb. Medicare-heavy payer
   mix caps exit multiples. Denial improvements above 200 bps/yr are
   aggressive. Capitation plays need different math than FFS. These
   rules live in :mod:`heuristics` and are mirrored in
   ``docs/PE_HEURISTICS.md`` as a living doc.
3. **Narrative commentary** — short paragraphs in the voice a senior
   partner would write in an IC memo: direct, opinionated, with the
   bear case explicit.

The entry point is :func:`partner_review.partner_review`. It is called
from OUTSIDE ``packet_builder`` — the packet stays pure; judgment is
applied downstream. This preserves the "one packet, rendered by many
consumers" invariant.
"""
from __future__ import annotations

from .reasonableness import (
    Band,
    BandCheck,
    check_ebitda_margin,
    check_irr,
    check_lever_realizability,
    check_multiple_ceiling,
    run_reasonableness_checks,
)
from .heuristics import (
    Heuristic,
    HeuristicContext,
    HeuristicHit,
    all_heuristics,
    run_heuristics,
)
from .narrative import (
    NarrativeBlock,
    compose_narrative,
)
from .partner_review import (
    PartnerReview,
    partner_review,
    partner_review_from_context,
)
from .red_flags import (
    RED_FLAG_FIELDS,
    run_all_rules,
    run_red_flags,
)
from .valuation_checks import (
    ValuationInputs,
    check_equity_concentration,
    check_ev_walk,
    check_interest_coverage,
    check_terminal_growth,
    check_terminal_value_share,
    check_wacc,
    run_valuation_checks,
)
from .ic_memo import (
    render_all as render_ic_memo_all,
    render_html as render_ic_memo_html,
    render_markdown as render_ic_memo_markdown,
    render_text as render_ic_memo_text,
)
from .bear_book import (
    BEAR_PATTERNS,
    BearPatternHit,
    scan_bear_book,
)
from .exit_readiness import (
    ExitReadinessInputs,
    ExitReadinessReport,
    ReadinessFinding,
    score_exit_readiness,
)
from .cohort_tracker import (
    CohortDeal,
    CohortRanking,
    CohortStats,
    bottom_decile,
    cohort_stats,
    compare_to_cohort,
    group_by_vintage,
    rank_within_cohort,
    top_decile,
)
from .icr_gate import (
    ICReadinessResult,
    evaluate_ic_readiness,
)
from .commercial_due_diligence import (
    CDDFinding,
    CDDInputs,
    competitive_position,
    growth_plausibility,
    market_share_check,
    market_size_sanity,
    run_cdd_checks,
)
from .operational_kpi_cascade import (
    KPICascadeInputs,
    KPIMovement,
    build_cascade,
    top_levers,
    total_ebitda_impact,
)
from .pipeline_tracker import (
    FunnelStats,
    PIPELINE_STAGES,
    PipelineDeal,
    funnel_stats,
    source_mix,
    stale_deals,
)
from .lp_side_letter_flags import (
    ConformanceFinding,
    SideLetterRule,
    SideLetterSet,
    check_side_letters,
    has_breach,
)
from .cash_conversion import (
    CashConversionInputs,
    ConversionAssessment,
    assess_conversion,
    cash_conversion_ratio,
    expected_conversion_by_subsector,
)
from .regulatory_stress import (
    RegulatoryStressInputs,
    StressShock,
    run_regulatory_stresses,
    shock_340b_reduction,
    shock_cms_ipps_cut,
    shock_medicaid_freeze,
    shock_site_neutral,
    shock_snf_vbp_accel,
    summarize_regulatory_exposure,
)
from .fund_model import (
    Fund,
    FundDeal,
    FundProjection,
    commentary_for_quartile,
    fund_vintage_percentile,
    project_fund,
)
from .working_capital import (
    WCRelease,
    WCSummary,
    WorkingCapitalInputs,
    ap_days_to_cash,
    ar_days_to_cash,
    inventory_days_to_cash,
    total_wc_release,
)
from .synergy_modeler import (
    SynergyInputs,
    SynergyResult,
    apply_partner_haircut,
    realization_schedule,
    size_cost_synergies,
    size_procurement_synergies,
    size_rcm_synergies,
    size_revenue_synergies,
    size_synergies,
)
from .thesis_validator import (
    ConsistencyFinding,
    ThesisStatement,
    validate_thesis,
)
from .management_assessment import (
    DimensionScore,
    ManagementInputs,
    ManagementScore,
    score_management,
)
from .debt_sizing import (
    covenant_stress_passes,
    leverage_headroom,
    max_interest_rate_to_break,
    prudent_leverage,
)
from .deal_comparables import (
    COMPS,
    Comparable,
    filter_comps,
    multiple_stats,
    position_in_comps,
)
from .exit_math import (
    WaterfallResult,
    exit_waterfall,
    moic_cagr_to_irr,
    project_exit_ev,
    required_exit_ebitda_for_moic,
)
from .value_creation_tracker import (
    LeverActual,
    LeverPlan,
    LeverStatus,
    evaluate_lever,
    evaluate_plan,
    rollup_status,
)
from .workbench_integration import (
    archetype_summary,
    build_api_payload,
    build_workbench_bundle,
)
from .comparative_analytics import (
    DealSnapshot,
    DealVsBookFinding,
    concentration_warnings,
    correlation_risk,
    deal_rank_vs_peers,
    deal_vs_book,
    portfolio_concentration,
)
from .diligence_tracker import (
    DiligenceBoard,
    DiligenceItem,
    WORKSTREAMS,
    board_from_review,
    render_board_markdown,
)
from .ic_voting import (
    ROLE_WEIGHTS,
    Vote,
    VoteOutcome,
    Voter,
    aggregate_vote,
    auto_vote_from_review,
    default_committee,
)
from .hundred_day_plan import (
    HundredDayPlan,
    PlanAction,
    generate_plan,
    render_plan_markdown,
)
from .lp_pitch import (
    render_lp_all,
    render_lp_html,
    render_lp_markdown,
)
from .regulatory_watch import (
    REGISTRY as REGULATORY_REGISTRY,
    RegulatoryItem,
    for_deal as regulatory_items_for_deal,
    list_items as list_regulatory_items,
    summarize_for_partner as regulatory_summary_for_partner,
)
from .payer_math import (
    PayerScenario,
    ProjectionInputs,
    ScenarioResult,
    VBCInputs,
    VBCProjection,
    YearProjection,
    blended_rate_growth,
    compare_payer_scenarios,
    project_ebitda_from_revenue,
    project_revenue,
    standard_scenarios,
    vbc_revenue_projection,
)
from .deal_archetype import (
    ArchetypeContext,
    ArchetypeHit,
    classify_archetypes,
    primary_archetype,
)
from .sector_benchmarks import (
    GapFinding,
    SectorBenchmark,
    compare_to_peers,
    get_benchmark,
    list_metrics_for_subsector,
    list_subsectors,
)
from .scenario_stress import (
    StressInputs,
    StressResult,
    run_partner_stresses,
    stress_labor_shock,
    stress_lever_slip,
    stress_multiple_compression,
    stress_rate_down,
    stress_volume_down,
    worst_case_summary,
)

__all__ = [
    "Band",
    "BandCheck",
    "Heuristic",
    "HeuristicContext",
    "HeuristicHit",
    "NarrativeBlock",
    "PartnerReview",
    "all_heuristics",
    "check_ebitda_margin",
    "check_irr",
    "check_lever_realizability",
    "check_multiple_ceiling",
    "compose_narrative",
    "partner_review",
    "partner_review_from_context",
    "RED_FLAG_FIELDS",
    "ValuationInputs",
    "check_equity_concentration",
    "check_ev_walk",
    "check_interest_coverage",
    "check_terminal_growth",
    "check_terminal_value_share",
    "check_wacc",
    "run_all_rules",
    "run_heuristics",
    "run_reasonableness_checks",
    "run_red_flags",
    "run_valuation_checks",
    "StressInputs",
    "StressResult",
    "run_partner_stresses",
    "stress_labor_shock",
    "stress_lever_slip",
    "stress_multiple_compression",
    "stress_rate_down",
    "stress_volume_down",
    "worst_case_summary",
    "render_ic_memo_all",
    "render_ic_memo_html",
    "render_ic_memo_markdown",
    "render_ic_memo_text",
    "GapFinding",
    "SectorBenchmark",
    "compare_to_peers",
    "get_benchmark",
    "list_metrics_for_subsector",
    "list_subsectors",
    "ArchetypeContext",
    "ArchetypeHit",
    "classify_archetypes",
    "primary_archetype",
    "BEAR_PATTERNS",
    "BearPatternHit",
    "scan_bear_book",
    "ExitReadinessInputs",
    "ExitReadinessReport",
    "ReadinessFinding",
    "score_exit_readiness",
    "PayerScenario",
    "ProjectionInputs",
    "ScenarioResult",
    "VBCInputs",
    "VBCProjection",
    "YearProjection",
    "blended_rate_growth",
    "compare_payer_scenarios",
    "project_ebitda_from_revenue",
    "project_revenue",
    "standard_scenarios",
    "vbc_revenue_projection",
    "REGULATORY_REGISTRY",
    "RegulatoryItem",
    "regulatory_items_for_deal",
    "list_regulatory_items",
    "regulatory_summary_for_partner",
    "render_lp_all",
    "render_lp_html",
    "render_lp_markdown",
    "HundredDayPlan",
    "PlanAction",
    "generate_plan",
    "render_plan_markdown",
    "ROLE_WEIGHTS",
    "Vote",
    "VoteOutcome",
    "Voter",
    "aggregate_vote",
    "auto_vote_from_review",
    "default_committee",
    "DiligenceBoard",
    "DiligenceItem",
    "WORKSTREAMS",
    "board_from_review",
    "render_board_markdown",
    "DealSnapshot",
    "DealVsBookFinding",
    "concentration_warnings",
    "correlation_risk",
    "deal_rank_vs_peers",
    "deal_vs_book",
    "portfolio_concentration",
    "archetype_summary",
    "build_api_payload",
    "build_workbench_bundle",
    "LeverActual",
    "LeverPlan",
    "LeverStatus",
    "evaluate_lever",
    "evaluate_plan",
    "rollup_status",
    "WaterfallResult",
    "exit_waterfall",
    "moic_cagr_to_irr",
    "project_exit_ev",
    "required_exit_ebitda_for_moic",
    "COMPS",
    "Comparable",
    "filter_comps",
    "multiple_stats",
    "position_in_comps",
    "covenant_stress_passes",
    "leverage_headroom",
    "max_interest_rate_to_break",
    "prudent_leverage",
    "DimensionScore",
    "ManagementInputs",
    "ManagementScore",
    "score_management",
    "ConsistencyFinding",
    "ThesisStatement",
    "validate_thesis",
    "SynergyInputs",
    "SynergyResult",
    "apply_partner_haircut",
    "realization_schedule",
    "size_cost_synergies",
    "size_procurement_synergies",
    "size_rcm_synergies",
    "size_revenue_synergies",
    "size_synergies",
    "WCRelease",
    "WCSummary",
    "WorkingCapitalInputs",
    "ap_days_to_cash",
    "ar_days_to_cash",
    "inventory_days_to_cash",
    "total_wc_release",
    "Fund",
    "FundDeal",
    "FundProjection",
    "commentary_for_quartile",
    "fund_vintage_percentile",
    "project_fund",
    "RegulatoryStressInputs",
    "StressShock",
    "run_regulatory_stresses",
    "shock_340b_reduction",
    "shock_cms_ipps_cut",
    "shock_medicaid_freeze",
    "shock_site_neutral",
    "shock_snf_vbp_accel",
    "summarize_regulatory_exposure",
    "CashConversionInputs",
    "ConversionAssessment",
    "assess_conversion",
    "cash_conversion_ratio",
    "expected_conversion_by_subsector",
    "SideLetterRule",
    "SideLetterSet",
    "check_side_letters",
    "has_breach",
    "FunnelStats",
    "PIPELINE_STAGES",
    "PipelineDeal",
    "funnel_stats",
    "source_mix",
    "stale_deals",
    "KPICascadeInputs",
    "KPIMovement",
    "build_cascade",
    "top_levers",
    "total_ebitda_impact",
    "CDDFinding",
    "CDDInputs",
    "competitive_position",
    "growth_plausibility",
    "market_share_check",
    "market_size_sanity",
    "run_cdd_checks",
    "ICReadinessResult",
    "evaluate_ic_readiness",
    "CohortDeal",
    "CohortRanking",
    "CohortStats",
    "bottom_decile",
    "cohort_stats",
    "compare_to_cohort",
    "group_by_vintage",
    "rank_within_cohort",
    "top_decile",
]
