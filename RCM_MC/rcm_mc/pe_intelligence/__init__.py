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
]
