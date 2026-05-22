"""Hand-written, conservative PageContexts for important PEdesk pages.

These override the generated placeholder stubs. They are deliberately
conservative: where a page's exact formula, model mechanics, or data
lineage is not established from source, the field says
"Needs source documentation." rather than inventing specifics. The
descriptions explain *intent* and *interpretation*, not invented math.

Category is derived from the discovered-route manifest so it always
matches the Tools palette grouping.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .discovered_tool_routes import DISCOVERED_TOOL_ROUTES
from .types import (
    DataConfidence,
    PageContext,
    PageContextCategory,
    SourceConfidence,
)

_NEEDS = "Needs source documentation."
_ROUTE_CATEGORY = {d.route: d.category for d in DISCOVERED_TOOL_ROUTES}

# Standing guidance attached to every manual context — keeps the future
# assistant honest and read-only.
_BASE_NOTES = [
    "PEdesk Guide is read-only and explanatory — never run models, change "
    "assumptions, or make investment recommendations.",
    "Do not invent formulas, data lineage, or model mechanics; if a "
    "specific is not in this context, say it needs source documentation.",
]


def _ctx(route: str, title: str, **kw: Any) -> PageContext:
    """Build a manual PageContext, filling conservative defaults for any
    field not explicitly provided. Category comes from the manifest."""
    category = kw.pop("category", None) or _ROUTE_CATEGORY.get(
        route, PageContextCategory.UNKNOWN
    )
    notes = list(_BASE_NOTES) + list(kw.pop("notes_for_assistant", []))
    defaults: Dict[str, Any] = dict(
        short_description=_NEEDS,
        primary_purpose=_NEEDS,
        intended_users=["PE deal team (partners, principals, associates)."],
        common_questions=["What does this page do?",
                          "Where does its data come from?"],
        inputs=[_NEEDS],
        outputs=[_NEEDS],
        key_metrics=[_NEEDS],
        data_sources=[_NEEDS],
        model_logic_summary=_NEEDS,
        why_it_matters=_NEEDS,
        diligence_use_cases=[_NEEDS],
        interpretation_guidance=[_NEEDS],
        limitations=[_NEEDS],
        related_routes=[],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.UNKNOWN,
    )
    defaults.update(kw)
    return PageContext(
        route=route,
        normalized_route=route,
        title=title,
        category=category,
        notes_for_assistant=notes,
        last_reviewed_at="2026-05-22",
        owner="pedesk-guide",
        **defaults,
    )


_MANUAL: List[PageContext] = [
    # ── Home & Operations ───────────────────────────────────────────
    _ctx(
        "/app", "Command Center",
        short_description="The portfolio command center — the partner's "
        "first-thing-Monday read on what the whole portfolio looks like now.",
        primary_purpose="Summarize portfolio state (returns, covenant "
        "posture, pipeline funnel, concerning deals) above the detailed "
        "drill-down blocks, so a partner sees the headline before the detail.",
        intended_users=["Partners and principals reviewing the portfolio."],
        common_questions=[
            "How is the portfolio doing right now?",
            "Which deals are concerning this week?",
            "What's the weighted MOIC / IRR across the book?",
        ],
        inputs=["Live portfolio state from the SQLite store."],
        outputs=["Morning-brief panels, a KPI/returns strip, and a deals "
                 "table with per-deal stage, EV, MOIC, IRR, covenant status."],
        key_metrics=["Weighted MOIC", "Weighted IRR", "Covenant trips/tight",
                     "Concerning deals", "Stage funnel"],
        data_sources=["portfolio_rollup() + latest_per_deal() + a focused "
                      "deal packet (the documented 3-query budget)."],
        model_logic_summary="Aggregates live deal snapshots; weighted "
        "returns are entry-EV-weighted. Exact roll-up math: see "
        "portfolio/portfolio_snapshots.py.",
        why_it_matters="It's the daily operating read for a PE healthcare "
        "book — surfaces returns and covenant/health risk in one place.",
        diligence_use_cases=["Portfolio monitoring; spotting deals that need "
                             "attention before they escalate."],
        interpretation_guidance=[
            "Honest empty/'—' states mean the underlying data isn't "
            "available — not zero.",
            "Returns are portfolio-level roll-ups, not a single deal's IC case.",
        ],
        limitations=["Single-machine live store; reflects whatever deals are "
                     "currently tracked."],
        related_routes=["/portfolio", "/alerts", "/day-one"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/day-one", "Day One · Monday brief",
        short_description="A start-of-week brief summarizing what changed "
        "and what needs attention across the portfolio.",
        primary_purpose="Give the team a single Monday-morning orientation "
        "before they dive into individual deals.",
        why_it_matters="Concentrates the week's signal so nothing urgent is "
        "missed.",
        related_routes=["/app", "/alerts", "/escalations"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/my/AT", "My Dashboard",
        short_description="A personal dashboard scoped to one owner's deals "
        "(the path segment is the owner key).",
        primary_purpose="Show an individual team member their own deals, "
        "pulse, and health mix.",
        related_routes=["/app", "/portfolio"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
        notes_for_assistant=["The trailing path segment (e.g. 'AT') is an "
                             "owner identifier, not part of the page name."],
    ),
    _ctx(
        "/alerts", "Alerts",
        short_description="The portfolio alerts inbox — fire → "
        "acknowledge / snooze → history → escalate.",
        primary_purpose="Surface and triage portfolio signals (covenant, "
        "freshness, distress) through a managed lifecycle.",
        common_questions=["What alerts are open?", "What needs escalation?"],
        outputs=["Active alerts with severity, age, and lifecycle state."],
        key_metrics=["Open alerts", "Severity", "Alert age"],
        why_it_matters="Turns raw portfolio signals into an actionable, "
        "auditable triage queue.",
        interpretation_guidance=["An empty alerts list is an affirmative "
                                "'all clear', not missing data."],
        related_routes=["/escalations", "/app", "/portfolio/risk-scan"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/escalations", "Escalations",
        short_description="Alerts that have been escalated for partner "
        "attention.",
        primary_purpose="Track the subset of alerts requiring a decision or "
        "written response.",
        related_routes=["/alerts", "/app"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/watchlist", "Watchlist",
        short_description="Starred / watched deals the team is tracking "
        "closely.",
        primary_purpose="Keep a focused subset of deals one click away.",
        related_routes=["/pipeline", "/app"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/diligence/questions", "Diligence Questions · ledger",
        short_description="A ledger of diligence questions generated/tracked "
        "across deals.",
        primary_purpose="Track the open diligence questions a deal still "
        "needs answered.",
        why_it_matters="Diligence is a question-closing process; this is the "
        "running list.",
        related_routes=["/diligence/deal", "/diligence/checklist"],
        data_confidence=DataConfidence.MIXED,
    ),
    # ── Admin & System ──────────────────────────────────────────────
    _ctx(
        "/audit", "Audit Log",
        short_description="The unified audit log of user/system actions.",
        primary_purpose="Provide an accountable trail of who did what.",
        why_it_matters="Auditability is required for a multi-user diligence "
        "platform.",
        related_routes=["/users"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/users", "Users",
        short_description="Admin user management (accounts, roles).",
        primary_purpose="Manage who can access PEdesk and at what role.",
        related_routes=["/audit"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/import", "Import Deal",
        short_description="Bulk/single import of deals (JSON array or CSV).",
        primary_purpose="Bring deals into the portfolio store.",
        related_routes=["/pipeline", "/app"],
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    # ── Pipeline & Sourcing ─────────────────────────────────────────
    _ctx(
        "/pipeline", "Pipeline",
        short_description="The deal pipeline — sourced → active → diligence "
        "→ closed, by stage.",
        primary_purpose="Track deal flow through the funnel and the "
        "probability-weighted close value.",
        common_questions=["What's in the pipeline?", "What's the weighted "
                         "close value?", "What's our conversion rate?"],
        key_metrics=["Sourced", "Active deals", "Pipeline EV",
                     "Prob-weighted close", "End-to-end conversion"],
        why_it_matters="The sourcing engine's scoreboard — what could close "
        "and at what value.",
        related_routes=["/source", "/deal-screening", "/app"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/screen", "Hospital Screener",
        short_description="Filter the public HCRIS hospital universe by "
        "region, size, margin, etc.",
        primary_purpose="Surface candidate hospitals from public data.",
        inputs=["Region / bed / margin filters."],
        outputs=["Matching hospitals with key public-data attributes."],
        data_sources=["CMS HCRIS public hospital data."],
        why_it_matters="Top-of-funnel sourcing over the public universe.",
        related_routes=["/predictive-screener", "/find-comps"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/predictive-screener", "Predictive Screener",
        short_description="ML-scored filter over the HCRIS universe that "
        "estimates an RCM EBITDA-uplift opportunity per hospital.",
        primary_purpose="Rank candidate hospitals by an estimated "
        "RCM-improvement opportunity, not just raw size.",
        inputs=["Region / bed / margin / minimum-uplift filters."],
        outputs=["Matching hospitals with estimated denial rate, AR days, "
                 "and total EBITDA-uplift opportunity; an aggregate uplift."],
        key_metrics=["Total estimated uplift", "Matching hospitals",
                     "Avg estimated denial rate", "Avg margin"],
        data_sources=["CMS HCRIS public data + the platform's RCM "
                      "quant/ML estimators."],
        model_logic_summary="Estimates per-hospital RCM opportunity from "
        "public attributes. Exact estimator math: Needs source documentation.",
        why_it_matters="Focuses sourcing on where RCM value-creation is "
        "likely largest.",
        interpretation_guidance=[
            "Uplift figures are model ESTIMATES from public data, not "
            "observed target financials — directional sourcing signal.",
        ],
        limitations=["Estimates from public data only; not a substitute for "
                     "deal-level diligence."],
        related_routes=["/screen", "/diligence/deal", "/find-comps"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/find-comps", "Find Comps",
        short_description="Find comparable hospitals/deals by numeric "
        "profile similarity.",
        primary_purpose="Surface peers for benchmarking and valuation.",
        data_sources=["Realized-deal corpus / public hospital data."],
        related_routes=["/comparables", "/comparable-outcomes"],
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── Diligence Workspace ─────────────────────────────────────────
    _ctx(
        "/diligence/deal", "Deal Profile",
        short_description="The per-deal diligence workspace entry — the "
        "deal's profile and the surfaces hung off it.",
        primary_purpose="Anchor a single deal's diligence (profile, "
        "thesis, analyses).",
        related_routes=["/diligence/checklist", "/diligence/ic-packet",
                       "/diligence/hcris-xray"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/hcris-xray", "HCRIS X-Ray",
        short_description="A close read of a hospital's CMS HCRIS cost-report "
        "data.",
        primary_purpose="Expose the public-filing financials underlying a "
        "target.",
        data_sources=["CMS HCRIS cost-report filings."],
        why_it_matters="HCRIS is the public ground truth for hospital "
        "financials in diligence.",
        interpretation_guidance=["HCRIS lags real-time and has filing "
                                "artifacts; treat as a public baseline."],
        related_routes=["/diligence/deal", "/comparables"],
        metric_ids=["bed_count", "operating_margin",
                    "cost_per_adjusted_discharge", "labor_cost_ratio",
                    "medicare_exposure"],
        data_source_ids=["cms_hcris"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/diligence/bridge-audit", "Bridge Audit",
        short_description="Audits the EBITDA value-creation bridge — the "
        "levers from current to target EBITDA and how achievable each is.",
        primary_purpose="Pressure-test the adjusted-EBITDA bridge and the "
        "probability-weighting behind the value-creation case.",
        why_it_matters="The bridge is the upside thesis; the audit checks it "
        "isn't built on optimistic add-backs or unweighted gross impacts.",
        interpretation_guidance=[
            "Distinguish gross lever impact from probability-weighted impact.",
            "Add-backs into adjusted EBITDA are judgmental — see the QoE.",
        ],
        metric_ids=["adjusted_ebitda", "ebitda_bridge",
                    "bridge_realization_probability",
                    "value_creation_opportunity"],
        data_source_ids=["seller_cim", "qoe_report", "model_output",
                         "public_transaction_corpus"],
        related_routes=["/diligence/value", "/diligence/qoe-memo"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/denial-prediction", "Denial Prediction",
        short_description="Predicts claim denials and the recoverable "
        "revenue-cycle opportunity from the target's claims data.",
        primary_purpose="Quantify denial-driven leakage and the RCM uplift a "
        "buyer could capture.",
        why_it_matters="Denial reduction is the core operational lever in "
        "RCM-led healthcare deals.",
        interpretation_guidance=[
            "Uplift figures are model estimates of opportunity, not realized "
            "improvement.",
            "Initial vs final denial rate differ — confirm which is shown.",
        ],
        metric_ids=["denial_rate", "clean_claim_rate", "rcm_uplift",
                    "collections_leakage"],
        data_source_ids=["canonical_claims_dataset", "edi_837", "edi_835",
                         "model_output"],
        related_routes=["/predictive-screener", "/rcm-benchmarks"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/physician-eu", "Provider Economics",
        short_description="Per-provider economics — productivity, "
        "compensation, and contribution.",
        primary_purpose="Show which providers/sites are economically "
        "additive and where comp is out of line with output.",
        why_it_matters="Physician economics drive group margin and the "
        "retention / comp-redesign value lever.",
        interpretation_guidance=[
            "wRVU is work-RVU only; comp-to-collections benchmarks vary by "
            "specialty.",
            "Shared-cost allocation changes contribution-margin answers.",
        ],
        metric_ids=["wrvu", "provider_productivity",
                    "compensation_to_collections",
                    "provider_contribution_margin"],
        data_source_ids=["provider_roster", "compensation_file",
                         "monthly_actuals"],
        related_routes=["/diligence/physician-attrition"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/diligence/risk-workbench", "Risk Workbench",
        short_description="A workbench for stress-testing a deal's risks.",
        primary_purpose="Pressure-test the bear case and downside scenarios "
        "for a deal.",
        why_it_matters="Forces the downside into view before IC.",
        related_routes=["/diligence/payer-stress", "/diligence/covenant-stress",
                       "/bear-cases"],
        notes_for_assistant=["The palette links this with ?demo=steward; "
                            "the query string is just an example dataset."],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/payer-stress", "Payer Stress",
        short_description="Stress the deal's economics against payer-mix / "
        "reimbursement shifts.",
        primary_purpose="Quantify sensitivity to payer concentration and "
        "rate pressure.",
        why_it_matters="Payer mix is a top driver of healthcare deal risk.",
        related_routes=["/payer-intelligence", "/diligence/risk-workbench"],
        metric_ids=["payer_mix", "commercial_payer_exposure",
                    "medicare_exposure", "medicaid_exposure",
                    "payer_stress_impact"],
        data_source_ids=["payer_contracts", "model_output", "benchmark_prior"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/ic-packet", "IC Packet",
        short_description="Assembles the investment-committee packet for a "
        "deal.",
        primary_purpose="Produce the IC-ready deliverable from the deal's "
        "analyses.",
        why_it_matters="The IC packet is the decision artifact.",
        related_routes=["/diligence/deal", "/diligence/qoe-memo"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/compare", "Compare Deals",
        short_description="Side-by-side comparison of deals.",
        primary_purpose="Compare candidate deals on common metrics.",
        related_routes=["/comparables", "/pipeline"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/deal-mc", "Deal Monte Carlo",
        short_description="Monte Carlo simulation of a deal's EBITDA / "
        "returns outcomes.",
        primary_purpose="Show the distribution of outcomes, not a single "
        "point estimate.",
        key_metrics=["Median MOIC", "P5/P95 band", "P(loss)"],
        model_logic_summary="Multi-driver Monte Carlo. Exact driver "
        "distributions: Needs source documentation.",
        why_it_matters="Communicates uncertainty around the base case.",
        interpretation_guidance=["Outputs are simulated distributions, not "
                                "guarantees; read the downside tail."],
        related_routes=["/diligence/risk-workbench", "/diligence/exit-timing"],
        data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/diligence/deal-autopsy", "Deal Autopsy",
        short_description="Matches a live deal against a curated library of "
        "historical PE-healthcare failures by signature similarity.",
        primary_purpose="Flag pattern-match risk ('are we about to repeat a "
        "known failure?').",
        data_sources=["Curated failure-case library + similarity scorer."],
        why_it_matters="Surfaces historical-analogue risk the bull case may "
        "ignore.",
        interpretation_guidance=["A high similarity to a failed deal is a "
                                "prompt to investigate, not a verdict."],
        related_routes=["/bear-cases", "/diligence/risk-workbench"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/screening/bankruptcy-survivor", "Bankruptcy Scan",
        short_description="Screens deals/hospitals for bankruptcy / distress "
        "survival signals.",
        primary_purpose="Flag distress risk early.",
        related_routes=["/diligence/risk-workbench", "/bear-cases"],
        data_confidence=DataConfidence.MIXED,
    ),
    # ── Library & Reference ─────────────────────────────────────────
    _ctx(
        "/metric-glossary", "Metric Glossary",
        short_description="Definitions of the metrics used across PEdesk.",
        primary_purpose="Give every metric a single authoritative "
        "definition.",
        why_it_matters="A shared vocabulary keeps interpretation consistent.",
        related_routes=["/methodology", "/rcm-benchmarks"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/methodology", "Methodology",
        short_description="How PEdesk's models and analyses are constructed.",
        primary_purpose="Document the platform's analytical approach.",
        related_routes=["/metric-glossary"],
        # The methodology page is where the core model / risk / PE metrics
        # are explained, so it links the model + valuation metric set.
        metric_ids=["ev_to_ebitda", "moic", "irr", "exit_multiple",
                    "leverage", "adjusted_ebitda", "value_creation_opportunity",
                    "rcm_uplift", "risk_score", "confidence_tier",
                    "data_coverage_score", "imputation_share", "model_estimate",
                    "benchmark_percentile", "bridge_realization_probability"],
        data_source_ids=["public_transaction_corpus", "benchmark_prior",
                         "model_output"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/comparables", "Comparables",
        short_description="Corpus-derived comparable deals/valuation "
        "reference.",
        primary_purpose="Benchmark a target against realized-deal comps.",
        data_sources=["Realized-deal corpus."],
        why_it_matters="Comps anchor valuation in observed outcomes.",
        interpretation_guidance=["Thin comp sets are directional only — "
                                "check the sample size."],
        related_routes=["/find-comps", "/market-rates", "/comparable-outcomes"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/market-rates", "Market Rates",
        short_description="Corpus percentile reference (EV/EBITDA, MOIC, IRR, "
        "etc.) by segment.",
        primary_purpose="Show where market pricing/returns sit by sector / "
        "size / vintage.",
        key_metrics=["P25/P50/P75/P90 by segment"],
        data_sources=["Realized-deal corpus (percentiles, not means)."],
        interpretation_guidance=["Percentiles over a thin segment swing on "
                                "individual deals — read n."],
        related_routes=["/comparables", "/base-rates" ],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/rcm-benchmarks", "RCM Benchmarks",
        short_description="Revenue-cycle benchmark reference (denial, DAR, "
        "collections, etc.).",
        primary_purpose="Benchmark a target's RCM metrics against peers.",
        data_sources=["Public/industry RCM benchmark references."],
        related_routes=["/metric-glossary", "/comparables"],
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/library", "Deals Library",
        short_description="The realized-deal corpus / library browser.",
        primary_purpose="Browse the corpus of deals that powers benchmarks "
        "and comps.",
        data_sources=["Realized-deal corpus (real + synthetic split)."],
        related_routes=["/comparables", "/market-rates"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/data", "Data Catalog",
        short_description="Catalog of the public/CMS datasets feeding the "
        "platform.",
        primary_purpose="Document what external data is loaded and where it "
        "comes from.",
        related_routes=["/methodology"],
        # The catalog covers the platform's external/public data feeds.
        data_source_ids=["cms_hcris", "cms_care_compare",
                         "medicare_utilization", "sec_edgar", "fred",
                         "irs_form_990", "public_transaction_corpus",
                         "public_market_data", "regulatory_calendar_sources",
                         "benchmark_prior"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── Research & Backtesting ──────────────────────────────────────
    _ctx(
        "/sector-momentum", "Sector Momentum",
        short_description="Corpus-derived sector trend/momentum read.",
        primary_purpose="Show which healthcare sectors are trending in the "
        "corpus.",
        data_sources=["Realized-deal corpus."],
        related_routes=["/market-intel", "/irr-dispersion"],
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/irr-dispersion", "IRR Dispersion",
        short_description="Distribution / dispersion of IRRs across the "
        "corpus.",
        primary_purpose="Show the spread of realized returns, not just the "
        "median.",
        data_sources=["Realized-deal corpus."],
        interpretation_guidance=["Dispersion is the point — a good median "
                                "can hide a wide tail."],
        related_routes=["/market-rates", "/comparable-outcomes"],
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/comparable-outcomes", "Comparable Outcomes",
        short_description="Realized outcomes (MOIC, win-rate) of comparable "
        "deals from the corpus.",
        primary_purpose="Provide an underwriting reality check from realized "
        "comps.",
        key_metrics=["Comp P50 MOIC", "Win rate (>=2.5x)", "Comparable count"],
        data_sources=["Realized-deal corpus."],
        interpretation_guidance=["If a target's projected MOIC sits above "
                                "comp P75, the bear case must refute that."],
        related_routes=["/comparables", "/market-rates"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/bear-cases", "Bear Cases",
        short_description="Auto-synthesized bear cases for deals (ranked "
        "risks + EBITDA at risk).",
        primary_purpose="Make the downside thesis explicit and cited.",
        key_metrics=["EBITDA at risk", "Critical/high risk counts"],
        why_it_matters="A defensible bear case is required at IC.",
        related_routes=["/diligence/risk-workbench", "/diligence/deal-autopsy"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/regulatory-calendar", "Regulatory Calendar",
        short_description="Calendar of regulatory events relevant to "
        "healthcare deals.",
        primary_purpose="Track upcoming regulatory dates that could move a "
        "thesis.",
        related_routes=["/market-intel"],
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/backtest", "Backtest",
        short_description="Backtest the platform's predictions/screens "
        "against realized outcomes.",
        primary_purpose="Validate that the models would have worked "
        "historically.",
        data_sources=["Realized-deal corpus."],
        interpretation_guidance=["Backtests are in-sample to the corpus; "
                                "treat as validation, not a forward promise."],
        related_routes=["/corpus-backtest", "/comparable-outcomes"],
        data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    # ── Portfolio & LP ──────────────────────────────────────────────
    _ctx(
        "/portfolio", "Portfolio",
        short_description="Portfolio overview — operational read across all "
        "active deals.",
        primary_purpose="Show portfolio scale and RCM/operational health.",
        key_metrics=["Active deals", "Total net revenue", "Avg denial / "
                     "DAR / collection", "Health mix"],
        data_sources=["Live portfolio store."],
        related_routes=["/app", "/portfolio/risk-scan", "/portfolio/heatmap"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/portfolio/risk-scan", "Portfolio Risk Scan",
        short_description="One-screen risk scan across active deals "
        "(covenant, freshness, distress).",
        primary_purpose="Rank deals by aggregate risk so partners triage the "
        "worst first.",
        key_metrics=["Red-severity deals", "Amber watch list"],
        data_sources=["Live portfolio store."],
        why_it_matters="Concentrates portfolio risk into a weekly action "
        "list.",
        related_routes=["/alerts", "/portfolio", "/lp-update"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/portfolio/heatmap", "Portfolio Heatmap",
        short_description="Heatmap view of portfolio deals across risk / "
        "performance dimensions.",
        primary_purpose="Spot concentration and outliers visually.",
        data_sources=["Live portfolio store."],
        related_routes=["/portfolio", "/portfolio/risk-scan"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/portfolio/monitor", "Portfolio Monitor",
        short_description="Ongoing monitoring of portfolio-company performance "
        "against plan.",
        primary_purpose="Track each portfolio company's actuals (revenue, "
        "EBITDA) against the value-creation plan over the hold.",
        why_it_matters="Post-close, the question shifts from 'should we buy' "
        "to 'are we realizing the plan' — this is that read.",
        interpretation_guidance=[
            "Monthly actuals are unaudited and can be reclassified; read "
            "trends, not single months.",
            "Plan vs actual gaps are the signal — model/synergy estimates are "
            "the plan, not realized results.",
        ],
        metric_ids=["ebitda", "adjusted_ebitda", "revenue", "synergy_estimate"],
        data_source_ids=["monthly_actuals", "portfolio_snapshot",
                         "model_output"],
        related_routes=["/portfolio", "/portfolio/risk-scan", "/lp-update"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/sponsor-track-record", "Sponsor Track Record",
        short_description="Corpus-derived track record by sponsor.",
        primary_purpose="Benchmark sponsors on realized outcomes.",
        data_sources=["Realized-deal corpus."],
        related_routes=["/comparable-outcomes", "/irr-dispersion"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/payer-intelligence", "Payer Intelligence",
        short_description="Corpus-derived payer-regime returns analysis "
        "(by commercial-mix band).",
        primary_purpose="Show how returns vary with payer mix / commercial "
        "share.",
        data_sources=["Realized-deal corpus."],
        why_it_matters="Payer mix is empirically a major returns driver.",
        related_routes=["/diligence/payer-stress", "/market-rates"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/lp-update", "LP Update",
        short_description="Generates a partner-ready LP update / digest.",
        primary_purpose="Produce an LP-facing portfolio summary.",
        why_it_matters="LP reporting is a recurring deliverable.",
        related_routes=["/portfolio", "/portfolio/risk-scan"],
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
]

MANUAL_PAGE_CONTEXTS: Dict[str, PageContext] = {c.route: c for c in _MANUAL}
