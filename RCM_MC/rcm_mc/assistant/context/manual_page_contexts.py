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
        metric_ids=["moic", "irr", "covenant_cushion"],
        data_source_ids=["portfolio_snapshot"],
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
        common_questions=["What alerts are open?", "What needs escalation?",
                         "Which deals tripped a covenant or missed plan?"],
        inputs=["Live deal snapshots from the portfolio store (optionally "
                "filtered by owner; a show-all toggle includes acknowledged)."],
        outputs=["Active alerts grouped by severity (page labels: Critical / "
                 "Warning / Info) with age and lifecycle state, plus "
                 "acknowledge / snooze / escalate controls."],
        key_metrics=["Total alerts", "Critical", "Warning", "Info",
                     "Alert age"],
        data_sources=["Latest per-deal snapshots in the portfolio store; "
                      "alert evaluators run over them."],
        model_logic_summary="Appears to be rule-based evaluators over the "
        "latest deal snapshots — covenant trip/tight, EBITDA variance misses, "
        "concerning-signal clusters, and stage regressions (the page labels "
        "amber vs red variance bands). Exact thresholds: see "
        "alerts/alerts.py — treat specifics as needing source confirmation.",
        why_it_matters="Turns raw portfolio signals into an actionable, "
        "auditable triage queue.",
        diligence_use_cases=["Post-close monitoring — catching covenant or "
                            "plan-variance problems before they escalate."],
        interpretation_guidance=["An empty alerts list is an affirmative "
                                "'all clear', not missing data.",
                                "Severity is rule-assigned from snapshot "
                                "signals, not a partner judgment."],
        limitations=["Reflects only what the latest snapshots contain; an "
                     "alert not firing is not proof a risk is absent."],
        related_routes=["/escalations", "/app", "/portfolio/risk-scan"],
        metric_ids=["covenant_cushion"],
        data_source_ids=["portfolio_snapshot"],
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
        primary_purpose="Keep a focused subset of deals one click away, with "
        "their headline returns and covenant posture.",
        common_questions=["Which deals am I watching?",
                         "How are my pinned deals trending?"],
        inputs=["The set of deals the user has starred (persisted); latest "
                "snapshot per pinned deal."],
        outputs=["A table of pinned deals — based on page labels: health "
                 "(score + sparkline), stage, covenant status, MOIC, IRR."],
        key_metrics=["Pinned deals", "Avg MOIC", "Avg IRR", "Covenant trips"],
        data_sources=["Starred-deal list + latest portfolio snapshots."],
        model_logic_summary="Filters the portfolio to starred deals and shows "
        "each deal's latest-snapshot figures; no model runs here.",
        why_it_matters="A partner's personal shortlist of the deals that need "
        "the closest eye.",
        diligence_use_cases=["Keeping the few deals under active scrutiny "
                            "together for quick re-checks."],
        interpretation_guidance=["MOIC/IRR/covenant are computed at snapshot "
                                "time, not live — read as of the last snapshot.",
                                "An empty watchlist means nothing is pinned, "
                                "not that the portfolio is empty."],
        limitations=["Only as current as each deal's latest snapshot."],
        related_routes=["/pipeline", "/app", "/portfolio"],
        metric_ids=["moic", "irr", "covenant_cushion"],
        data_source_ids=["portfolio_snapshot"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/diligence/questions", "Diligence Questions · ledger",
        short_description="A portfolio-wide ledger that aggregates the "
        "diligence questions saved across every deal the user has opened.",
        primary_purpose="Show every open diligence question across all deals "
        "in one place, and let the user export the list.",
        common_questions=["What questions are still open across my deals?",
                         "Can I send these to the seller / put them in the "
                         "IC binder?"],
        inputs=["Per-deal question lists the user has saved (the page reads "
                "them from the browser's local storage — no server roundtrip)."],
        outputs=["A consolidated, deal-grouped question ledger; based on page "
                 "copy, it can be copied as Markdown or downloaded as CSV, and "
                 "?print=1 shows a print-preview binder."],
        key_metrics=["Open questions", "Questions per deal"],
        data_sources=["The user's browser-local per-deal question lists "
                      "(client-side only)."],
        model_logic_summary="Pure composition — it concatenates the user's "
        "saved question lists; no model or server computation.",
        why_it_matters="Diligence is a question-closing process; this is the "
        "running cross-deal list.",
        diligence_use_cases=["Building the seller question list and the IC "
                            "binder's open-items section."],
        interpretation_guidance=["These are user-entered notes, not computed "
                                "findings.",
                                "Because the data is browser-local, the ledger "
                                "only reflects deals opened on this machine."],
        limitations=["Browser-local: nothing here is shared server-side or "
                     "synced across machines/users."],
        related_routes=["/diligence/deal", "/diligence/checklist"],
        data_source_ids=["diligence_questions"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    # ── Admin & System ──────────────────────────────────────────────
    _ctx(
        "/audit", "Audit Log",
        short_description="Admin-only review surface for the platform's audit "
        "trail — users, recent alert acknowledgements, and ownership changes.",
        primary_purpose="Provide an accountable, view-only trail of who did "
        "what across the platform.",
        common_questions=["Who acknowledged this alert and when?",
                         "Who changed this deal's owner?"],
        inputs=["Admin session (gated to the admin role when users exist)."],
        outputs=["Based on page sections: a users card, recent alert "
                 "acknowledgements (when / by / deal / kind / snooze / note), "
                 "and recent owner-assignment history."],
        key_metrics=["Not applicable — this is an audit-trail review page, "
                     "not an analytic metric page."],
        data_sources=["The platform's users, alert-ack, and "
                      "deal-owner-history records."],
        model_logic_summary="Not applicable — it lists recorded events; no "
        "model or computation.",
        why_it_matters="Auditability is required for a multi-user diligence "
        "platform.",
        diligence_use_cases=["Compliance / process review — confirming who "
                            "acted on alerts and ownership."],
        interpretation_guidance=["These are recorded platform actions, not "
                                "deal financials.",
                                "View-only — the page itself changes no state."],
        limitations=["Admin-gated; shows a recent window of events, not the "
                     "full history."],
        related_routes=["/users"],
        data_source_ids=["audit_log"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/users", "Users",
        short_description="Admin-only user management — accounts, roles, "
        "password rotation, and deletion.",
        primary_purpose="Manage who can access PEdesk and at what role "
        "(analyst / admin).",
        common_questions=["Who has access?", "How do I add or remove a user?"],
        inputs=["New-user form (username, optional display name, password, "
                "role); admin session."],
        outputs=["A user table (username, display name, role) with "
                 "rotate-password and delete actions, plus a create form."],
        key_metrics=["Not applicable — this is a platform-administration "
                     "page, not an analytic metric page."],
        data_sources=["The platform's user / auth store."],
        model_logic_summary="Not applicable — user CRUD via CSRF-protected "
        "endpoints; no analytic model.",
        why_it_matters="Access control underpins a multi-user diligence "
        "platform.",
        diligence_use_cases=["Not a diligence-analysis page — platform "
                            "administration only."],
        interpretation_guidance=["Admin-gated; nothing here reflects deal "
                                "data."],
        limitations=["Single-machine auth store; admin role required when "
                     "users exist."],
        related_routes=["/audit"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    _ctx(
        "/import", "Import Deal",
        short_description="Quick import of one deal (a form) or many (a JSON "
        "array) into the portfolio store.",
        primary_purpose="Bring deals into the portfolio store with their RCM "
        "and financial profile fields.",
        common_questions=["How do I add a deal?", "Can I bulk-load deals?"],
        inputs=["Single-deal form (deal id, hospital name + optional "
                "denial_rate, days_in_ar, net_collection_rate, "
                "clean_claim_rate, cost_to_collect, claims volume, net "
                "revenue, beds, state) OR a pasted JSON array of deals."],
        outputs=["A created/updated deal row (single import redirects to the "
                 "deal page; bulk import reports the count imported)."],
        key_metrics=["Denial rate", "Days in A/R", "Net collection rate",
                     "Clean claim rate", "Bed count", "Net revenue"],
        data_sources=["User-entered field values; per the page, missing "
                      "RCM/financial fields are filled with Bayesian priors."],
        model_logic_summary="Writes the deal profile to the deals store; "
        "based on page code, absent fields are backfilled from priors. The "
        "JSON path accepts an array of {deal_id, name, profile} objects.",
        why_it_matters="It's the on-ramp — nothing can be analyzed until a "
        "deal exists in the store.",
        diligence_use_cases=["Standing up a new target (or a batch) before "
                            "running any analysis on it."],
        interpretation_guidance=["Values are user-entered, not verified — "
                                "treat imported figures as inputs, not facts.",
                                "Prior-filled fields are estimates, not the "
                                "target's reported numbers."],
        limitations=["Source shows a single-deal form and a JSON-array path; "
                     "CSV support is not established in the page source — "
                     "needs source confirmation."],
        related_routes=["/pipeline", "/app"],
        metric_ids=["denial_rate", "days_in_ar", "net_collection_rate",
                    "clean_claim_rate", "bed_count", "revenue"],
        data_source_ids=["deal_profile"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    # ── Pipeline & Sourcing ─────────────────────────────────────────
    _ctx(
        "/pipeline", "Pipeline",
        short_description="The deal pipeline — hospitals moving through stages "
        "(screening → outreach → LOI → diligence → IC → closed / passed).",
        primary_purpose="Track candidate hospitals through the sourcing funnel "
        "and advance them stage by stage.",
        common_questions=["What's in the pipeline?", "What stage is each "
                         "hospital at?", "How many are in diligence?"],
        inputs=["The pipeline hospital list (ccn, name, stage, priority); "
                "HCRIS public financials joined per hospital."],
        outputs=["Per page labels: a funnel of stage counts (In Pipeline / "
                 "Active / In Diligence / Closed / Saved Searches) and a "
                 "hospital table (state, beds, HCRIS revenue, margin, stage) "
                 "with advance-to-next-stage and Bridge/Memo/Data links."],
        key_metrics=["In pipeline", "Active", "In diligence", "Closed",
                     "Saved searches", "Revenue (HCRIS)", "Margin (HCRIS)"],
        data_sources=["The pipeline-tracking table + CMS HCRIS public hospital "
                      "data (revenue, operating margin)."],
        model_logic_summary="Lists pipeline hospitals by stage and joins HCRIS "
        "revenue/margin per CCN; advancing a stage is a POST. The page source "
        "does not show a probability-weighted close value — treat any "
        "weighting as needing source confirmation.",
        why_it_matters="The sourcing scoreboard — what is in flight and how "
        "far each candidate has progressed.",
        diligence_use_cases=["Top-of-funnel tracking; deciding which "
                            "candidates to advance into diligence."],
        interpretation_guidance=["Revenue/margin shown are HCRIS public "
                                "figures, not target-reported financials.",
                                "Stage is a workflow position the team sets, "
                                "not a model probability."],
        limitations=["HCRIS is a public, lagging baseline; stage data is only "
                     "as current as the team keeps it."],
        related_routes=["/source", "/screen", "/app"],
        metric_ids=["operating_margin", "bed_count", "revenue"],
        data_source_ids=["cms_hcris"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
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
        short_description="The per-deal diligence entry point — a profile form "
        "that captures a deal's identity and shared parameters once, so the "
        "downstream analysis tools all use them.",
        primary_purpose="Capture and persist one deal's profile (dataset, "
        "deal/partner/preparer names, specialty, states, legal structure) as "
        "the shared context for its analyses.",
        common_questions=["What deal am I working on?",
                         "Where do I set the deal's parameters?"],
        inputs=["User-entered profile fields; based on page code these are "
                "saved in the browser's local storage keyed by deal slug."],
        outputs=["A saved deal profile that downstream tools read; the page "
                 "itself is a capture form, not an analytic readout."],
        key_metrics=["Not applicable — this is a profile/metadata form, not "
                     "a metric page."],
        data_sources=["User-entered deal metadata (browser-local)."],
        model_logic_summary="No model — it stores the profile the partner "
        "enters and hands it to the analysis tools.",
        why_it_matters="It establishes the single deal context every other "
        "diligence surface keys off.",
        diligence_use_cases=["Standing up a deal's working context before "
                            "running its analyses."],
        interpretation_guidance=["Everything here is user-entered metadata, "
                                "not verified data.",
                                "Because it's browser-local, the profile lives "
                                "on this machine."],
        limitations=["Profile is browser-local; not a server-side record of "
                     "deal financials."],
        related_routes=["/diligence/checklist", "/diligence/ic-packet",
                       "/diligence/hcris-xray"],
        data_source_ids=["deal_profile"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
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
        short_description="Auto-assembles an investment-committee read for a "
        "deal — thesis, base case, bear case, comparables, exit path, and the "
        "questions partners expect.",
        primary_purpose="Stitch the deal's analyses into a single "
        "committee-style narrative the team can review and print.",
        common_questions=["What will the committee read on this deal?",
                         "What's the base case vs the bear case?",
                         "Is this packet finalized / signed off?"],
        inputs=["A claims dataset (fixture) plus deal metadata supplied via "
                "the query string (specialty, geography, lease terms, EHR "
                "vendor, EV/EBITDA, recommendation, etc.)."],
        outputs=["A rendered packet assembled from a multi-stage pipeline "
                 "(per source): claims KPIs + cash waterfall, "
                 "bankruptcy-survivor scan, counterfactual advisor, comparables "
                 "+ transaction multiple, and a historical deal-autopsy match."],
        key_metrics=["Enterprise value", "EV/EBITDA", "Exit multiple",
                     "Adjusted EBITDA"],
        data_sources=["A canonical claims dataset (fixtures on this page), the "
                      "public transaction/comps corpus, and model outputs; "
                      "deal metadata is user-entered."],
        model_logic_summary="Appears to orchestrate the analysis pipeline and "
        "compose the result into IC sections. Exact stage math: needs source "
        "documentation — do not state specifics not shown in source.",
        why_it_matters="It concentrates the whole deal case into the artifact "
        "a committee actually reads.",
        diligence_use_cases=["Drafting the IC narrative and pressure-testing "
                            "that base/bear/comps/exit hang together."],
        interpretation_guidance=[
            "This is intended to PRODUCE an IC-style read, but the page source "
            "shows only a rendered view (browser Print → Save as PDF) — there "
            "is no finalize / sign-off / publish flow, so it should be "
            "verified before IC use, not treated as signed.",
            "On this page the underlying claims data are fixtures, and several "
            "inputs are user-entered — not observed target financials.",
        ],
        limitations=["No version control, approval, or 'finalized' state in "
                     "the page source; the deliverable is a printable view.",
                     "A separate standalone export path may exist but is not "
                     "invoked by this page — needs source confirmation."],
        related_routes=["/diligence/deal", "/diligence/qoe-memo"],
        metric_ids=["enterprise_value", "ev_to_ebitda", "exit_multiple",
                    "adjusted_ebitda"],
        data_source_ids=["canonical_claims_dataset", "public_transaction_corpus",
                         "model_output"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/checklist", "Diligence Checklist",
        short_description="A diligence-checklist dashboard — coverage %, open "
        "P0/P1 blockers, per-phase progress, and an item table with "
        "auto-tracked status plus partner manual overrides.",
        primary_purpose="Orchestrate diligence completeness: track which "
        "checklist items are done, in progress, or blocking.",
        common_questions=["How complete is diligence?",
                         "What P0 items are still open / blocking?",
                         "Which items still need an owner or evidence?"],
        inputs=["A diligence checklist state (auto-status derived from live "
                "analytics, per source) plus partner overrides supplied via "
                "the URL (mark done / blocked / in-progress / clear)."],
        outputs=["Per page labels: KPI blocks (P0 coverage — labeled 'Ready "
                 "for IC' or 'Blocking IC'; Total done; Open P0; Open P1) and "
                 "an item table (Item, Phase, Category, Priority, Status, "
                 "Owner, Question); a JSON export."],
        key_metrics=["P0 coverage", "Total done", "Open P0", "Open P1",
                     "Total coverage %"],
        data_sources=["The diligence checklist state module (auto-status from "
                      "analytics; the page may use demo observations)."],
        model_logic_summary="Computes coverage and per-phase progress from the "
        "checklist state and applies any partner overrides. Exact "
        "auto-status rules: see the diligence/checklist module — treat "
        "specifics as needing source confirmation.",
        why_it_matters="Diligence is a coverage problem; this is the running "
        "scoreboard of what's done and what's blocking.",
        diligence_use_cases=["Tracking diligence readiness and surfacing P0 "
                            "blockers before a deal advances."],
        interpretation_guidance=[
            "The 'Ready for IC' label reflects P0 COVERAGE only — it is a "
            "completeness signal, not a sign-off or approval.",
            "Statuses are auto-derived and partner-overridable; treat them as "
            "workflow state, not verified findings.",
        ],
        limitations=["Per source the page can run on demo observations and is "
                     "portfolio-wide / stateless unless a URL with overrides "
                     "is bookmarked — verify it reflects a real deal's state."],
        related_routes=["/diligence/questions", "/diligence/deal",
                       "/diligence/ic-packet"],
        metric_ids=["data_coverage_score"],
        data_source_ids=["checklist_state", "analysis_run"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/qoe-memo", "QoE Memo",
        short_description="Renders a Quality-of-Earnings memo as a standalone, "
        "printable HTML document for a chosen claims dataset.",
        primary_purpose="Produce a QoE read (claims KPIs + a cash waterfall, "
        "optionally counterfactuals) the team can print to PDF.",
        common_questions=["What's the quality of this target's earnings?",
                         "How do I generate the QoE memo?",
                         "Is this memo finalized / signed?"],
        inputs=["A canonical claims dataset (fixtures on this page) plus memo "
                "metadata via query string (deal/target name, partner and "
                "preparer names, management-reported revenue by cohort month)."],
        outputs=["A standalone QoE memo page: claims KPIs and a cash "
                 "waterfall (optionally counterfactual scenarios), rendered "
                 "for browser Print → Save as PDF."],
        key_metrics=["Net collection rate", "Gross collection rate",
                     "Days in A/R"],
        data_sources=["A canonical claims dataset (fixture-based here) + "
                      "user-entered memo metadata."],
        model_logic_summary="Ingests the claims dataset, computes a KPI bundle "
        "and a cash waterfall (and optional counterfactuals), then renders the "
        "memo. Exact KPI/waterfall math: needs source documentation.",
        why_it_matters="QoE is the earnings-quality backbone of financial "
        "diligence; this drafts that memo from claims data.",
        diligence_use_cases=["Drafting the QoE deliverable and reviewing "
                            "collection quality / cash conversion."],
        interpretation_guidance=[
            "The docstring frames this as a 'partner-signed' memo, but the "
            "page produces a printable HTML (Print → Save as PDF); when linked "
            "to an engagement it writes only a DRAFT — there is no sign-off "
            "flow in the page source, so verify before treating it as final.",
            "On this page the claims data are fixtures and metadata is "
            "user-entered — not observed target financials.",
        ],
        limitations=["Fixture-driven on this page; no programmatic publish or "
                     "approval step in source — the deliverable is a printable "
                     "view (and at most a DRAFT engagement record)."],
        related_routes=["/diligence/ic-packet", "/diligence/bridge-audit"],
        metric_ids=["net_collection_rate", "gross_collection_rate",
                    "days_in_ar"],
        data_source_ids=["canonical_claims_dataset", "qoe_report"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
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
        short_description="Portfolio overview — an operational read of RCM "
        "health across all active deals.",
        primary_purpose="Show portfolio scale and revenue-cycle health, with a "
        "health-score distribution and a per-deal table.",
        common_questions=["How is the portfolio doing operationally?",
                         "Which deals are unhealthy?",
                         "What's the average denial / AR / collection?"],
        inputs=["The active deal list from the portfolio store."],
        outputs=["Per page labels: a KPI strip (Active Deals, Total Net "
                 "Revenue, Avg Denial Rate, Avg Days in AR, Avg Net "
                 "Collection), a health-distribution bar, and a deals table "
                 "(ID, Name, Stage, Denial, AR, NPR); a CSV export link."],
        key_metrics=["Active deals", "Total net revenue", "Avg denial rate",
                     "Avg days in A/R", "Avg net collection rate",
                     "Health mix"],
        data_sources=["The live portfolio store (per-deal profiles / "
                      "snapshots)."],
        model_logic_summary="Aggregates the active deals — averages the RCM "
        "rates and bins deals into a health distribution (the page colors "
        "bands green/amber/red). Exact health-score formula: see the health "
        "score module; treat the cutoffs as needing source confirmation.",
        why_it_matters="It's the operational health read across the whole book "
        "in one screen.",
        diligence_use_cases=["Portfolio monitoring — spotting operationally "
                            "weak deals across the book."],
        interpretation_guidance=["Figures are portfolio-level roll-ups, not a "
                                "single deal's case.",
                                "Honest empty/'—' states mean the underlying "
                                "data isn't present, not zero.",
                                "This page is RCM-health focused — it does not "
                                "show MOIC/IRR or covenant status (see "
                                "/lp-update and /portfolio/risk-scan)."],
        limitations=["Single-machine live store; reflects whatever active "
                     "deals are currently tracked."],
        related_routes=["/app", "/portfolio/risk-scan", "/portfolio/heatmap"],
        metric_ids=["denial_rate", "days_in_ar", "net_collection_rate",
                    "revenue"],
        data_source_ids=["portfolio_snapshot"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/portfolio/risk-scan", "Portfolio Risk Scan",
        short_description="One-screen Monday-morning risk scan across active "
        "deals — covenant headroom, open alerts, snapshot freshness, "
        "deadlines, and distress signals.",
        primary_purpose="Rank deals by aggregate risk so partners triage the "
        "worst first.",
        common_questions=["Which deals need attention today?",
                         "Who tripped a covenant?",
                         "Which deals have stale data or overdue deadlines?"],
        inputs=["Active deals + latest snapshots, alert evaluations, health "
                "scores, deadlines, and CMS facility/quality/HRRP lookups."],
        outputs=["Per page labels: a summary strip (Covenant TRIPPED, deals "
                 "with open alerts, deals with overdue deadlines, active deals "
                 "scanned) and a per-deal row with health, covenant, alerts, "
                 "snapshot age, deadlines, CMS quality and HRRP; TRIPPED deals "
                 "sort first."],
        key_metrics=["Covenant trips", "Deals with open alerts",
                     "Deals with overdue deadlines", "Health score",
                     "CMS quality rating", "HRRP penalty"],
        data_sources=["Live portfolio store (snapshots, alerts, health, "
                      "deadlines) + CMS facility / quality / readmissions "
                      "data."],
        model_logic_summary="Scans each active deal across several risk "
        "dimensions and color-codes them (safe/tight/tripped, fresh/stale/cold, "
        "etc.), sorting riskiest first. Exact scoring/sort thresholds: see "
        "portfolio_risk_scan_page.py — treat specifics as needing source "
        "confirmation.",
        why_it_matters="Concentrates portfolio risk into a weekly action "
        "list.",
        diligence_use_cases=["Post-close monitoring triage — deciding which "
                            "deals to act on this week."],
        interpretation_guidance=["Covenant status and freshness are "
                                "snapshot-derived, not live.",
                                "CMS quality/HRRP are public facility signals, "
                                "not deal financials.",
                                "Color tiers are rule-assigned, not a partner "
                                "judgment."],
        limitations=["Only as current as each deal's latest snapshot; a clean "
                     "scan is not proof of no risk."],
        related_routes=["/alerts", "/portfolio", "/lp-update"],
        metric_ids=["covenant_cushion", "risk_score"],
        data_source_ids=["portfolio_snapshot", "cms_care_compare"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/portfolio/heatmap", "Portfolio Heatmap",
        short_description="A deals × metrics heatmap — rows are deals, columns "
        "are the top RCM metrics, cells colored by the metric's benchmark "
        "percentile.",
        primary_purpose="Spot, at a glance, where each deal stands against "
        "benchmarks across the key revenue-cycle metrics.",
        common_questions=["Where does each deal stand vs benchmarks?",
                         "Which deals are weak on which metrics?"],
        inputs=["The latest analysis packet per deal (each metric's value + "
                "benchmark percentile)."],
        outputs=["Per page labels: a deal × metric grid (denial rate, final "
                 "denial rate, days in A/R, AR>90%, net collection rate, clean "
                 "claim rate, cost to collect, case mix index), a data-quality "
                 "Grade per deal, and a KPI strip (Deals Mapped, Grade A "
                 "Share, Metrics Tracked, Color Bins)."],
        key_metrics=["Denial rate", "Days in A/R", "Net collection rate",
                     "Clean claim rate", "Case mix index",
                     "Benchmark percentile"],
        data_sources=["Per-deal analysis packets (computed metrics + benchmark "
                      "percentiles)."],
        model_logic_summary="Reads each deal's packet metrics and colors cells "
        "by benchmark percentile rank; the Grade reflects data completeness, "
        "not operational health (per the page).",
        why_it_matters="Turns the portfolio into a single benchmark-relative "
        "picture so outliers pop.",
        diligence_use_cases=["Comparing deals against benchmarks to find which "
                            "need an operational look."],
        interpretation_guidance=["Cell color is a percentile RANK vs "
                                "benchmarks, not an absolute value.",
                                "Grade is a data-quality signal, not deal "
                                "health.",
                                "Percentiles depend on the benchmark set — "
                                "verify the comparison universe before "
                                "drawing conclusions."],
        limitations=["Only covers metrics present in each deal's packet; "
                     "missing data shows as gaps, not zeros."],
        related_routes=["/portfolio", "/portfolio/risk-scan"],
        metric_ids=["denial_rate", "days_in_ar", "net_collection_rate",
                    "clean_claim_rate", "case_mix_index",
                    "benchmark_percentile"],
        data_source_ids=["analysis_run", "portfolio_snapshot"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
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
        short_description="A partner-ready LP update / digest — portfolio "
        "returns, covenant trips, active alerts, recent activity, and a "
        "cohort breakdown, downloadable as HTML.",
        primary_purpose="Produce an LP-facing portfolio summary for a chosen "
        "time window.",
        common_questions=["How do I generate the LP update?",
                         "What's the weighted MOIC/IRR across the book?",
                         "What changed this period?"],
        inputs=["The portfolio store; a window picker (e.g. 7/14/30/60/90 "
                "days) selects the activity period."],
        outputs=["Per page labels: a KPI strip (Active Deals, Weighted MOIC, "
                 "Weighted IRR, Covenant Trips), an active-alerts section, a "
                 "recent-activity table, and a cohort breakdown (W. MOIC / "
                 "W. IRR / Trips); a 'Download HTML' produces an "
                 "lp_update_<date>.html file."],
        key_metrics=["Active deals", "Weighted MOIC", "Weighted IRR",
                     "Covenant trips"],
        data_sources=["Portfolio roll-up + alert evaluation + an activity "
                      "digest + cohort roll-up, all from the live store."],
        model_logic_summary="Stitches a portfolio roll-up (per source, "
        "EV-weighted MOIC/IRR and covenant-trip count), active alerts, a "
        "recent-activity digest over the chosen window, and a per-cohort "
        "roll-up. Exact weighting math: see portfolio_snapshots.py.",
        why_it_matters="LP reporting is a recurring deliverable; this turns "
        "live portfolio state into the summary partners send.",
        diligence_use_cases=["Producing the periodic LP digest / client "
                            "briefing without hand-assembling figures."],
        interpretation_guidance=["MOIC/IRR are EV-weighted roll-ups (per page "
                                "labels), not single-deal returns.",
                                "The activity list is windowed — it shows the "
                                "selected period, not all history.",
                                "The HTML export is a snapshot of current "
                                "state, not a live document."],
        limitations=["Reflects current live-store state at generation time; "
                     "no audited reconciliation."],
        related_routes=["/portfolio", "/portfolio/risk-scan"],
        metric_ids=["moic", "irr", "covenant_cushion"],
        data_source_ids=["portfolio_snapshot", "generated_export"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
]

MANUAL_PAGE_CONTEXTS: Dict[str, PageContext] = {c.route: c for c in _MANUAL}
