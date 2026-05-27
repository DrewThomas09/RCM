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
        short_description="A Monday-morning brief — five short editorial "
        "sections (alerts, portfolio health, where you left off, this week's "
        "pipeline, onboarding) in the order partners check them.",
        primary_purpose="Give the team a single start-of-week orientation "
        "before they dive into individual deals.",
        common_questions=["What changed over the weekend?",
                         "What needs attention first this week?"],
        inputs=["Live portfolio state (active alerts, health scores, recent "
                "activity, last-7-day pipeline) from the store."],
        outputs=["Per page labels: top alerts by severity, a portfolio "
                 "health-mix read, recent activity, this week's new/advanced "
                 "deals, and an onboarding checklist."],
        key_metrics=["Top alerts", "Portfolio health mix",
                     "New / advanced deals (7d)"],
        data_sources=["The live portfolio store (alerts, health, activity, "
                      "pipeline)."],
        model_logic_summary="Composes existing reads (active alerts, health "
        "scores, recent activity, recent packets) into a brief; it summarizes, "
        "it does not run a model.",
        why_it_matters="Concentrates the week's signal so nothing urgent is "
        "missed.",
        diligence_use_cases=["The weekly portfolio-monitoring starting point."],
        interpretation_guidance=[
            "This is a snapshot brief, not a trend analyzer — it shows current "
            "state, not multi-week slopes.",
            "Empty sections are an affirmative 'nothing this week', not "
            "missing data.",
        ],
        limitations=["Reflects current live-store state; only as complete as "
                     "what's tracked."],
        related_routes=["/app", "/alerts", "/escalations"],
        metric_ids=["risk_score"],
        data_source_ids=["portfolio_snapshot", "audit_log"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/my/AT", "My Dashboard",
        short_description="A personal dashboard scoped to one owner's deals — "
        "their pulse, alerts, deadlines, and health mix.",
        primary_purpose="Show an individual team member their own deals, "
        "alerts, deadlines, and returns in one read.",
        common_questions=["What's on my plate this week?",
                         "Which of my deals have red alerts or overdue "
                         "deadlines?"],
        inputs=["The owner key in the path; deals owned by that owner + their "
                "alerts, deadlines, and latest snapshots."],
        outputs=["Per page labels: a pulse strip (My Deals, Red/Amber Alerts, "
                 "Overdue/Upcoming Deadlines), a health-mix bar, alert and "
                 "deadline cards, and a deals table (Health, Stage, Covenant, "
                 "MOIC, IRR)."],
        key_metrics=["My deals", "Red / amber alerts", "Overdue / upcoming "
                     "deadlines", "MOIC", "IRR"],
        data_sources=["The portfolio store filtered to the owner (deals, "
                      "alerts, deadlines, snapshots)."],
        model_logic_summary="Filters portfolio data to one owner and "
        "aggregates counts + latest-snapshot figures; health scores are "
        "computed per deal. No model runs here.",
        why_it_matters="Gives each partner/associate a personal operating "
        "view without trawling the whole book.",
        diligence_use_cases=["Personal weekly triage of owned deals."],
        interpretation_guidance=[
            "Owner assignment and deadline labels are user-entered; MOIC / IRR "
            "/ covenant come from the latest snapshot, not live.",
            "Scoped to one owner — it is not the whole portfolio.",
        ],
        limitations=["Only as current as each deal's latest snapshot and the "
                     "owner/deadline data entered."],
        related_routes=["/app", "/portfolio", "/alerts"],
        metric_ids=["moic", "irr", "covenant_cushion", "risk_score"],
        data_source_ids=["portfolio_snapshot"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
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
        short_description="Every red alert that has been open at least N days "
        "(default 30) — the aged-risk view a partner reviews before an LP "
        "update or weekly check-in.",
        primary_purpose="Surface unresolved red alerts that have persisted, so "
        "they get a decision rather than sitting open.",
        common_questions=["What red alerts are still open and for how long?",
                         "What needs a partner decision before the LP update?"],
        inputs=["A days-open threshold (7/14/30/60/90); red alerts from alert "
                "history that meet it."],
        outputs=["Per page labels: a table of aged red alerts (Deal, Title, "
                 "Age in days + first-seen date, Detail, Acked badge); a CSV "
                 "download."],
        key_metrics=["Aged red alerts", "Days open"],
        data_sources=["Alert history over the portfolio store (red alerts, "
                      "first-seen/last-seen, ack status)."],
        model_logic_summary="Filters alert history to red alerts older than "
        "the threshold and flags ack status; it surfaces aged alerts, it does "
        "not compute new ones.",
        why_it_matters="Persistence is the signal — a red alert open for weeks "
        "is the thing most likely to be slipping.",
        diligence_use_cases=["Pre-LP-update / weekly review of unresolved "
                            "portfolio risks."],
        interpretation_guidance=[
            "'Days open' measures persistence, not severity escalation; an "
            "acked alert can still be open.",
            "The page shows how long an alert has been red, not what was tried "
            "to resolve it.",
        ],
        limitations=["Only red alerts past the threshold; reflects what the "
                     "alert evaluators fired, not root cause."],
        related_routes=["/alerts", "/app", "/lp-update"],
        data_source_ids=["portfolio_snapshot", "audit_log"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
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
        short_description="The deal pipeline — YOUR real opportunities moving "
        "through stages (screening → outreach → LOI → diligence → IC → closed "
        "/ passed). This is USER DEAL data, not the market or the corpus.",
        primary_purpose="Track your actual opportunities through the deal "
        "funnel and advance them stage by stage. Deals enter here by being "
        "promoted from Source, created, or imported — the full lifecycle is: "
        "Discover (Source) → Evaluate (X-Ray / Deal Quality) → Promote → "
        "Manage (Pipeline) → Diligence → Decide → Monitor (Portfolio).",
        common_questions=["What is the difference between Source and Pipeline?",
                         "How do I promote a target into a deal?",
                         "Is this my deals or the market/corpus?",
                         "What's in the pipeline?",
                         "What stage is each hospital at?",
                         "How many are in diligence right now?",
                         "Which candidates are highest priority to advance?",
                         "Where is the funnel bottlenecking by stage?",
                         "How do I advance a hospital to the next stage?",
                         "Which pipeline hospitals have the best HCRIS margin?",
                         "How do I jump from a candidate to its bridge or memo?",
                         "What does each stage in the funnel mean?"],
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
        "/target-screener", "Target Screener",
        short_description="The Source workbench: a six-screen, server-rendered "
        "target-screening surface (Main · Inspector · Columns · Compare · Just "
        "missed · Saved screens) over every public CMS/provider universe — "
        "hospitals/HCRIS, home health, hospice, SNF, dialysis, IRF, LTCH, "
        "provider supply, and markets. Driven by ?view= and shareable query "
        "params; a real US map (not squares) shades states by provider count.",
        primary_purpose="Find acquisition targets across every onboarded CMS/"
        "provider universe — by filter, map, score, compare, and just-missed "
        "scan — then open a target's X-Ray and promote it to Pipeline. One "
        "workflow: Source → Target Screener → evaluate → compare → just-missed "
        "→ save → X-Ray → promote.",
        common_questions=[
            "What is Target Screener for?",
            "Which vertical/universe should I use?",
            "What data powers this result?",
            "How is the opportunity/quality score computed?",
            "What does the map layer mean?",
            "Why did this target just miss my filters?",
            "Which filters are excluding targets?",
            "Can I compare targets across verticals?",
            "What should I open next?",
            "What data is missing for this target?",
            "Is this investment advice?",
            "How do I promote a target to Pipeline?"],
        inputs=["Vertical/universe selection; query-param filters (state, "
                "min_quality, min_size, …); compare basket (CCNs); map state "
                "clicks. All read public CMS/provider data, never your deals."],
        outputs=["Real US provider-density map (click a state to filter); a "
                 "ranked provider table from the live loader with source + "
                 "missingness per row; metric-by-metric Compare; a just-missed "
                 "scan; shareable saved-screen URLs; X-Ray / Inspector links."],
        key_metrics=["Provider count by state (per vertical)",
                     "Vertical-specific quality (HH star, SNF overall rating, "
                     "dialysis five-star, hospice care index, IRF/LTCH "
                     "discharge-to-community, hospital operating margin)",
                     "Size (beds / stations / certified beds)"],
        data_sources=["Real CMS public universes via the live loaders: HCRIS, "
                      "Home Health / Hospice / SNF / Dialysis / IRF / LTCH "
                      "Compare, provider supply; geo/market intelligence for "
                      "map layers. The historical deal corpus is NEVER an "
                      "active target universe (research/benchmark label only)."],
        model_logic_summary="Counts and quality come straight from the CMS "
        "loaders (no model). Scores, where shown, are formula-documented, "
        "missingness-aware blends of real metrics — never AI black boxes — and "
        "show DATA REQUIRED when they cannot be computed.",
        why_it_matters="Replaces three overlapping screeners with one workbench "
        "that screens every real provider universe, keeps market data distinct "
        "from your deals, and is honest about what is missing.",
        interpretation_guidance=[
            "This is CMS PUBLIC DATA (the market), not your pipeline/portfolio; "
            "promote a result into the Pipeline to track it.",
            "A '—' means the metric is not reported for that provider — it was "
            "not fabricated, and (on Just missed) it is 'missing, not failed'.",
            "Cross-vertical Compare only shares identity/size/quality columns, "
            "and those use each vertical's own metric — they are not directly "
            "comparable across verticals.",
            "Nothing here is investment advice; it is a screening signal.",
        ],
        related_routes=["/diligence/xray", "/diligence/hcris-xray", "/geo-intel",
                        "/market-intel/geo", "/pipeline", "/source", "/screen",
                        "/predictive-screener"],
    ),
    _ctx(
        "/source", "Deal Sourcing",
        short_description="Thesis-matched sourcing — scores the public HCRIS "
        "hospital universe against predefined investment theses and ranks the "
        "best fits.",
        primary_purpose="Surface hospitals that fit a chosen investment thesis "
        "(e.g. rural consolidation, margin turnaround, commercial-payer mix).",
        common_questions=["Which hospitals fit my thesis?",
                         "What scores highest for this strategy?"],
        inputs=["A selected thesis from the library; the public HCRIS hospital "
                "universe."],
        outputs=["Per page labels: a ranked match table (Hospital, State, "
                 "Beds, fit Score 0-100) with a 'Screen →' link per row."],
        key_metrics=["Fit score (0-100)", "Bed count", "Operating margin",
                     "Commercial payer share"],
        data_sources=["CMS HCRIS public hospital data; derived payer-mix and "
                      "margin fields."],
        model_logic_summary="Appears to score each hospital per-criterion "
        "(bed ranges, payer-mix thresholds, margin, revenue), weight and "
        "composite to 0-100 with a region bonus. The score is a thesis-FIT "
        "ranking, not a prediction of returns. Exact weights: see "
        "deal_sourcer.py — treat specifics as needing source confirmation.",
        why_it_matters="Top-of-funnel sourcing aimed at a strategy rather than "
        "raw size.",
        diligence_use_cases=["Building a thesis-aligned candidate list before "
                            "deeper screening."],
        interpretation_guidance=[
            "The fit score ranks alignment to the selected thesis — it is not "
            "a predicted MOIC, denial rate, or uplift.",
            "All inputs are public HCRIS figures, not target-reported data.",
        ],
        limitations=["Public HCRIS only; a high fit score is a sourcing "
                     "signal, not deal-level diligence."],
        related_routes=["/screen", "/predictive-screener", "/pipeline"],
        metric_ids=["bed_count", "operating_margin", "commercial_payer_exposure"],
        data_source_ids=["cms_hcris"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/screen", "Hospital Screener",
        short_description="Metric-based filter over the public HCRIS hospital "
        "universe by region, size, revenue, and margin.",
        primary_purpose="Surface candidate hospitals from public data by "
        "user-set metric ranges (with quick presets like turnaround / "
        "large-cap / margin-expansion).",
        common_questions=["Which hospitals match these financial criteria?",
                         "Show me large turnaround candidates."],
        inputs=["User filters (min/max beds, min revenue, max margin, state) "
                "or a preset; the public HCRIS universe."],
        outputs=["Per page labels: a matches table (Hospital, State, Beds, "
                 "NPR $M, Margin %) with profile / diligence links."],
        key_metrics=["Bed count", "Net patient revenue", "Operating margin"],
        data_sources=["CMS HCRIS public hospital data (latest per CCN)."],
        model_logic_summary="Filters HCRIS rows by the supplied metric ranges "
        "(or hardcoded preset ranges) and returns matches — a metric filter, "
        "not a model or ranking.",
        why_it_matters="Top-of-funnel sourcing over the public universe by "
        "explicit financial criteria.",
        diligence_use_cases=["Free-form candidate search when you know the "
                            "financial profile you want."],
        interpretation_guidance=[
            "Figures are public HCRIS, not target-reported data.",
            "This is a filter — it does not score or predict; see /source for "
            "thesis-fit ranking and /predictive-screener for estimates.",
        ],
        limitations=["Public HCRIS only; reflects filing data, which lags and "
                     "has artifacts."],
        related_routes=["/source", "/predictive-screener", "/find-comps"],
        metric_ids=["bed_count", "revenue", "operating_margin"],
        data_source_ids=["cms_hcris"],
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
                     "deal-level diligence.",
                     "Point estimates with no stated confidence interval; not "
                     "validated against realized RCM outcomes."],
        related_routes=["/screen", "/source", "/find-comps"],
        metric_ids=["denial_rate", "days_in_ar", "rcm_uplift",
                    "operating_margin", "bed_count", "model_estimate"],
        data_source_ids=["cms_hcris", "model_output"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/find-comps", "Find Comps",
        short_description="Comparable-deal finder — user enters a target's "
        "characteristics; the page returns ranked corpus comparables with "
        "similarity scores and a peer benchmark block.",
        primary_purpose="Identify peer deals for benchmarking and valuation by "
        "profile similarity.",
        common_questions=["What deals are comparable to this target?",
                         "What's the peer MOIC / EV/EBITDA?"],
        inputs=["Target characteristics the user enters (sector, EV, EV/EBITDA, "
                "payer mix, vintage)."],
        outputs=["Per page labels: a ranked comps table (Rank, Deal, Sector, "
                 "Buyer, Year, EV, EV/EBITDA, MOIC, IRR, Hold, Comm%, "
                 "Similarity) plus peer/corpus MOIC P50 summary."],
        key_metrics=["Similarity score", "EV/EBITDA", "MOIC", "IRR",
                     "Hold period", "Peer MOIC P50"],
        data_sources=["A seeded realized-deal corpus (comparison context, not "
                      "the target's own data)."],
        model_logic_summary="Scores corpus deals by weighted similarity to the "
        "entered profile (per source: sector + EV + EV/EBITDA + payer mix + "
        "vintage) and ranks them. Pure matching — no approved/locked comp-set "
        "governance.",
        why_it_matters="Peers anchor a valuation and a returns expectation.",
        diligence_use_cases=["Assembling a quick comparable set to sanity-check "
                            "entry multiple and return expectations."],
        interpretation_guidance=[
            "This finds comparables by similarity; it is not an approved or "
            "signed-off comp set — verify the peer set before IC use.",
            "Peer/corpus MOIC figures are realized-corpus comparison context, "
            "not the target's own outcomes.",
            "The corpus here is a seeded deal set, not live market data.",
        ],
        limitations=["Similarity weights and the corpus seed determine the "
                     "matches; no governance over which comps are 'allowed'."],
        related_routes=["/comparables", "/comparable-outcomes",
                       "/diligence/compare"],
        metric_ids=["ev_to_ebitda", "moic", "irr", "hold_period",
                    "commercial_payer_exposure"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/deal-screening", "Deal Screening",
        short_description="Runs every corpus deal through a rules-based screen "
        "(composite risk, EV/EBITDA, MOIC floor, Medicaid exposure, heuristic "
        "signal, data completeness) and returns PASS / WATCH / FAIL.",
        primary_purpose="Apply tunable screening rules across the historical "
        "deal corpus and see how the pass/watch/fail mix shifts.",
        common_questions=["Which corpus deals pass the screen?",
                         "What happens if I tighten the thresholds?"],
        inputs=["The historical deal corpus; tunable thresholds via query "
                "params (max composite risk, EV/EBITDA, MOIC floor, max "
                "Medicaid %, min EV)."],
        outputs=["Per page labels: KPI tiles (Corpus Deals, Pass/Watch/Fail "
                 "rates) and a table (Deal, Decision, Risk, Heuristic, Data %, "
                 "Top Reason)."],
        key_metrics=["Pass / watch / fail rate", "Composite risk score",
                     "EV/EBITDA", "MOIC", "Medicaid exposure",
                     "Data completeness"],
        data_sources=["The historical deal corpus (analysis packets / modeled "
                      "financials), screened by rules."],
        model_logic_summary="Applies deterministic rules with the supplied "
        "thresholds to each corpus deal and emits PASS/WATCH/FAIL with reasons. "
        "Rules-based, not a new prediction. Exact rule cutoffs: see "
        "deal_screening_engine — treat specifics as needing source "
        "confirmation.",
        why_it_matters="Turns the corpus into a tunable screen so you can see "
        "which deals clear a given risk bar.",
        diligence_use_cases=["Calibrating a screening bar and seeing which "
                            "historical deals would clear it."],
        interpretation_guidance=[
            "PASS/WATCH/FAIL are rule outcomes at the chosen thresholds, not "
            "predictions or recommendations.",
            "Operates on the historical corpus, not the public hospital "
            "universe or a live target.",
        ],
        limitations=["Outcomes move with the thresholds you set; corpus "
                     "coverage and data completeness bound the result."],
        related_routes=["/deals-library", "/diligence/risk-workbench",
                       "/comparable-outcomes"],
        metric_ids=["risk_score", "ev_to_ebitda", "moic", "medicaid_exposure",
                    "data_coverage_score"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/pe-intelligence", "PE Intelligence",
        short_description="A hub/landing page for the PE-intelligence module "
        "library — surfaces the partner 'reflexes' and links to the archetype, "
        "reasonableness, red-flag, and bear-book inventories.",
        primary_purpose="Orient users on what the codified PE-judgment library "
        "can do and route them to per-deal reads.",
        common_questions=["What can the PE-intelligence brain do?",
                         "Where do I run it on a specific deal?"],
        inputs=["None on the hub itself — it is a catalog / methodology "
                "overview; per-deal output runs from deal routes."],
        outputs=["Per page labels: a reflexes card grid, inventory links "
                 "(archetype library, reasonableness matrix, red-flag catalog, "
                 "bear book), and per-deal route links; counts like modules / "
                 "reflexes."],
        key_metrics=["Not applicable — this is a methodology/registry hub, not "
                     "an analytic-metric page."],
        data_sources=["The module registry / methodology itself (a catalog of "
                      "decision logic), not deal or market data."],
        model_logic_summary="Catalogs the partner-judgment modules and "
        "reflexes and links to inventories; it does not itself screen deals or "
        "produce predictions.",
        why_it_matters="It's the map of the codified judgment layer — useful "
        "for understanding what reads are available before opening a deal.",
        diligence_use_cases=["Learning the available reflex/archetype reads "
                            "and jumping to a deal's partner-review."],
        interpretation_guidance=[
            "This is a module registry and methodology overview — it codifies "
            "judgment patterns; it does not produce validated predictions.",
            "Actual per-deal output lives on deal routes (e.g. partner-review "
            "/ red-flags), not on this hub.",
        ],
        limitations=["Descriptive hub only; nothing here is a deal-specific "
                     "result."],
        related_routes=["/diligence/deal", "/bear-cases"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.UNKNOWN,
    ),
    _ctx(
        "/conferences", "Conferences",
        short_description="A curated calendar of healthcare investment "
        "conferences, PE summits, and industry events relevant to hospital "
        "M&A teams.",
        primary_purpose="Give diligence/sourcing teams a reference roadmap of "
        "relevant industry events.",
        common_questions=["What conferences are coming up?",
                         "Which events matter for healthcare PE?"],
        inputs=["A category filter (the events themselves are a curated list)."],
        outputs=["Per page labels: events grouped by quarter with name, date, "
                 "location, category, tier, and relevance."],
        key_metrics=["Not applicable — this is a reference calendar, not an "
                     "analytic-metric page."],
        data_sources=["A curated, static healthcare-events list maintained in "
                      "the page."],
        model_logic_summary="Renders and filters a curated events list; no "
        "model or computation.",
        why_it_matters="Keeps the team's sourcing/relationship calendar in one "
        "reference place.",
        diligence_use_cases=["Planning sourcing/networking around the "
                            "healthcare-PE event calendar."],
        interpretation_guidance=[
            "This is curated reference content, not deal data or a personal "
            "attendance tracker.",
        ],
        limitations=["Static curated list — only as current as the page's "
                     "maintained content."],
        related_routes=["/pipeline", "/source"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.UNKNOWN,
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
        short_description="A nine-panel risk panorama — runs the Tier-1/2/3 "
        "diligence engines against the supplied deal metadata and shows a "
        "severity band per panel.",
        primary_purpose="Pressure-test a deal's structural risks (regulatory, "
        "real-estate, physician, cyber, MA, labor, patient-pay) in one view.",
        common_questions=["Where does this deal carry structural risk?",
                         "What does the Steward precedent look like here?"],
        inputs=["Deal metadata via query params (states, specialty, legal "
                "structure, landlord, lease terms, etc.); panels without "
                "inputs render 'not supplied' rather than fabricating numbers."],
        outputs=["Per page labels: a metadata strip and a 9-panel grid, each "
                 "panel showing a severity band (GREEN / YELLOW / RED / "
                 "CRITICAL) with a headline number."],
        key_metrics=["Per-panel severity band", "Risk score"],
        data_sources=["The supplied deal metadata, run through the diligence "
                      "engines; a hardcoded Steward replay in demo mode."],
        model_logic_summary="Each panel runs its own engine on the metadata "
        "and emits a severity band. No CCD/claims data is required. Exact "
        "per-engine rules: see risk_workbench_page.py — treat specifics as "
        "needing source confirmation.",
        why_it_matters="Forces the structural downside into view before IC.",
        diligence_use_cases=["A fast structural-risk read across many vectors "
                            "early in diligence."],
        interpretation_guidance=[
            "Severity bands are rule-derived signals on the inputs, not a "
            "verdict — should be verified before IC use.",
            "Panels with no inputs say 'not supplied'; absence is not safety.",
        ],
        limitations=["Runs on metadata only; quality depends on what's "
                     "supplied. A clean panorama is not proof of no risk."],
        related_routes=["/diligence/payer-stress", "/diligence/covenant-stress",
                       "/bear-cases"],
        notes_for_assistant=[
            "?demo=steward is a SPECIFIC named historical replay (the Steward "
            "Health 2016 pattern), not a generic example dataset — figures in "
            "demo mode are a precedent reconstruction, not a live deal. There "
            "is also a ?print=1 print-preview mode.",
        ],
        metric_ids=["risk_score"],
        data_source_ids=["model_output", "demo_fixture"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
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
        short_description="Side-by-side comparison of two datasets — each side "
        "runs the QoR waterfall + KPI bundle + counterfactual advisor, with "
        "delta badges on the headline metrics.",
        primary_purpose="Put two specimens next to each other for an 'IC "
        "bake-off / which do we lead with' read.",
        common_questions=["How do these two deals compare?",
                         "Which is the stronger lead?"],
        inputs=["Two datasets chosen via query params (?left=…&right=…) from "
                "the available fixtures."],
        outputs=["Per page labels: two columns (KPIs, QoR waterfall, "
                 "counterfactual / bridge levers) with delta badges between "
                 "them."],
        key_metrics=["Denial rate", "Days in A/R", "Net collection rate",
                     "Headline deltas"],
        data_sources=["Two demo fixtures, each run through the analysis "
                      "pipeline."],
        model_logic_summary="Runs the same pipeline on each side and diffs the "
        "headline metrics; it is an ad-hoc side-by-side, not a governed "
        "comp-set.",
        why_it_matters="Makes a head-to-head choice between two candidates "
        "explicit.",
        diligence_use_cases=["Deciding which of two deals to lead with; "
                            "pressure-testing one against the other."],
        interpretation_guidance=[
            "On this page both sides are demo fixtures — not target-uploaded "
            "data; read it as a comparison method, not observed deal results.",
            "This is matching/comparison, not an approved or locked comp set.",
        ],
        limitations=["Fixture-driven; no approval/governance over the pairing."],
        related_routes=["/comparables", "/find-comps", "/pipeline"],
        metric_ids=["denial_rate", "days_in_ar", "net_collection_rate"],
        data_source_ids=["canonical_claims_dataset", "demo_fixture"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
    _ctx(
        "/diligence/thesis-pipeline", "Thesis Pipeline",
        short_description="A one-button orchestrator that runs the full "
        "diligence chain end-to-end and reports each step's headline result.",
        primary_purpose="Run the whole diligence analytic chain on a deal in "
        "one pass and surface the headline numbers with deep links to each "
        "individual analytic.",
        common_questions=["What does the full diligence run say?",
                         "Which step flagged the biggest issue?"],
        inputs=["A claims dataset (fixture) plus deal metadata (EV, equity, "
                "debt, revenue, EBITDA, lease terms, EHR vendor, roster, "
                "market category, HCRIS CCN)."],
        outputs=["Per page labels: a step-by-step execution log with headline "
                 "numbers (e.g. P50 MOIC, P(sub-1x), denial recoverable $, "
                 "attrition EBITDA-at-risk $, counterfactual lever $, Steward "
                 "tier, bankruptcy verdict) and deep links to each analytic."],
        key_metrics=["P50 MOIC", "P(sub-1x)", "Denial recoverable $",
                     "Attrition EBITDA-at-risk $", "Bankruptcy verdict"],
        data_sources=["A claims dataset (fixture on this page) + deal "
                      "metadata; downstream analytics add model outputs and "
                      "corpus lookups."],
        model_logic_summary="Appears to chain multiple analytics (ingest, "
        "benchmarks, denial prediction, bankruptcy scan, counterfactual, "
        "attrition, autopsy, market intel, scenario assembly, Monte Carlo, "
        "checklist) where each step is optional and failures short-circuit "
        "only that step. Exact step math: needs source documentation.",
        why_it_matters="Collapses the multi-tool diligence workflow into one "
        "orchestrated run with a single headline read.",
        diligence_use_cases=["A fast full-chain pass early in diligence, then "
                            "drilling into the steps that flag risk."],
        interpretation_guidance=[
            "Each headline comes from a different analytic with its own "
            "caveats — treat them as that tool's output, not a combined "
            "verdict.",
            "On this page the claims data are fixtures and several inputs are "
            "user-entered; Monte Carlo outputs are simulated, not realized.",
        ],
        limitations=["Orchestration only — it does not add new math beyond the "
                     "underlying analytics; fixture-driven here."],
        related_routes=["/diligence/benchmarks", "/diligence/denial-prediction",
                       "/diligence/counterfactual"],
        metric_ids=["moic", "rcm_uplift", "physician_attrition",
                    "value_creation_opportunity", "bankruptcy_pattern_match"],
        data_source_ids=["canonical_claims_dataset", "model_output",
                         "public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/benchmarks", "Benchmarks",
        short_description="Shows the target's revenue-cycle KPIs (from claims) "
        "against external peer benchmark bands.",
        primary_purpose="Place each of the target's RCM KPIs next to peer "
        "quartile bands so off-benchmark gaps stand out.",
        common_questions=["How does this target compare to peers?",
                         "Which KPIs are off-benchmark?"],
        inputs=["A claims dataset (fixture on this page) the KPIs are computed "
                "from; built-in peer benchmark bands."],
        outputs=["Per page labels: KPI cards (Days in A/R, First-Pass Denial "
                 "Rate, A/R Aging >90d, Cost to Collect, Net Revenue "
                 "Realization, Service→Bill and Bill→Cash lag), each with the "
                 "target value and a delta vs the peer median."],
        key_metrics=["Days in A/R", "First-pass denial rate",
                     "Net revenue realization", "A/R aging >90 days",
                     "Cost to collect"],
        data_sources=["Target claims (computed KPIs) + external peer benchmark "
                      "bands (e.g. HFMA-style quartiles)."],
        model_logic_summary="Computes KPIs from the claims dataset and "
        "compares each to peer bands, showing the signed delta to the peer "
        "median. Exact KPI definitions: needs source documentation.",
        why_it_matters="Benchmarking turns raw KPIs into a 'better or worse "
        "than peers' read that frames where the RCM upside is.",
        diligence_use_cases=["Spotting which revenue-cycle metrics lag peers "
                            "and warrant a root-cause look."],
        interpretation_guidance=[
            "Two data types are mixed: the KPI VALUES are the target's own "
            "(observed from claims), while the BANDS are external peer "
            "benchmarks — don't read the bands as the target's data.",
            "On this page the claims are a fixture; with a real upload the "
            "values would be the target's observed data.",
        ],
        limitations=["Benchmark bands are peer references, not the target; "
                     "comparison validity depends on the peer set."],
        related_routes=["/diligence/root-cause", "/diligence/qoe-memo",
                       "/rcm-benchmarks"],
        metric_ids=["days_in_ar", "denial_rate", "net_collection_rate",
                    "benchmark_percentile"],
        data_source_ids=["canonical_claims_dataset", "benchmark_prior"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/root-cause", "Root Cause",
        short_description="Decomposes off-benchmark denials into driver "
        "categories (a Pareto) and surfaces zero-balance write-off claims from "
        "the claims data.",
        primary_purpose="Attribute denial dollars to their root-cause "
        "categories so the recoverable opportunity is concrete and traceable.",
        common_questions=["What's driving the denials?",
                         "Where are the recoverable write-offs?"],
        inputs=["A claims dataset (fixture on this page) the analysis is "
                "computed from."],
        outputs=["Per page labels: a denial Pareto (category, dollars, claim "
                 "count) and a zero-balance-account autopsy table (claim, "
                 "payer, charge, allowed, adjustment, denial codes)."],
        key_metrics=["Denial dollars by category", "Recoverable write-offs",
                     "Denial rate"],
        data_sources=["Target claims (the page computes the decomposition "
                      "directly from them)."],
        model_logic_summary="Stratifies observed denials in the claims data "
        "into driver categories and lists the underlying write-off rows — an "
        "attribution/decomposition of what already happened, not a forward "
        "projection.",
        why_it_matters="Moves from 'denials are high' to 'here is exactly "
        "what's driving them and what's recoverable'.",
        diligence_use_cases=["Sizing and substantiating the recoverable RCM "
                            "opportunity behind a denial gap."],
        interpretation_guidance=[
            "This decomposes ALREADY-OBSERVED denials in the data — it is not "
            "a prediction of future denials.",
            "On this page the claims are a fixture; recoverable $ are "
            "directional until validated on the real claims.",
        ],
        limitations=["Only as complete as the claims data; categories depend "
                     "on the denial-code mapping used."],
        related_routes=["/diligence/benchmarks", "/diligence/denial-prediction",
                       "/diligence/value"],
        metric_ids=["denial_rate", "collections_leakage", "bad_debt_rate"],
        data_source_ids=["canonical_claims_dataset"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/value", "Value Creation",
        short_description="Maps RCM initiative levers to their expected EBITDA "
        "contribution on the deal, to underwrite the value bridge.",
        primary_purpose="Estimate what each RCM lever could be worth on this "
        "deal's size / payer mix / denial profile, to prioritize the 100-day "
        "plan and underwrite the bridge.",
        common_questions=["What's the RCM upside worth on this deal?",
                         "Which levers should the 100-day plan prioritize?"],
        inputs=["A claims dataset (fixture) and the deal's size / payer-mix / "
                "denial profile; payer-rate and CMS-regime schedules (demo on "
                "this page)."],
        outputs=["Per page labels: per-lever expected EBITDA contribution, a "
                 "contract re-pricer view, and a CMS advisory regime read that "
                 "feed the value bridge."],
        key_metrics=["Expected EBITDA contribution per lever",
                     "Recoverable EBITDA", "Payer leverage"],
        data_sources=["Target claims (fixture here) + synthetic contract / CMS "
                      "schedules + model outputs."],
        model_logic_summary="Appears to map each RCM lever to an expected "
        "EBITDA contribution given the deal shape and feed it into the value "
        "bridge / IC memo. Exact lever math: needs source documentation.",
        why_it_matters="It's the underwriting of the upside case — the bridge "
        "that justifies the entry price.",
        diligence_use_cases=["Underwriting the value-creation bridge and "
                            "prioritizing the 100-day plan."],
        interpretation_guidance=[
            "These are UNDERWRITTEN / forward opportunity estimates, NOT "
            "realized value creation — read them as what a lever COULD be "
            "worth, to be verified before IC use.",
            "On this page contract/CMS rates are synthetic demo inputs, not "
            "the deal's actual contracts.",
        ],
        limitations=["Forward estimates on demo schedules; realized value "
                     "depends on execution and actual contracts."],
        related_routes=["/diligence/bridge-audit", "/diligence/root-cause",
                       "/diligence/ic-packet"],
        metric_ids=["value_creation_opportunity", "rcm_uplift", "ebitda_bridge",
                    "adjusted_ebitda", "payer_mix"],
        data_source_ids=["canonical_claims_dataset", "model_output"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/counterfactual", "Counterfactual",
        short_description="For each lever, the smallest shift that would flip "
        "the deal's verdict — a 'what would change your mind' / 'what we're "
        "waiting for' surface.",
        primary_purpose="Identify the minimum change on each lever (rate, "
        "denial, AR, structure) that would move a RED/YELLOW band to GREEN, "
        "and how feasible that change is.",
        common_questions=["What would change the conclusion on this deal?",
                         "Which lever is the binding constraint?"],
        inputs=["A claims dataset (fixture) + deal metadata (legal structure, "
                "states, specialty, landlord, lease terms, etc.)."],
        outputs=["Per page labels: per-lever cards (module, action, original→"
                 "target band, feasibility HIGH/MED/LOW, estimated $ impact); "
                 "a JSON download of the same."],
        key_metrics=["Minimum lever shift to flip the band", "Feasibility",
                     "Estimated $ impact"],
        data_sources=["Target claims (fixture here) + caller-supplied "
                      "metadata; model outputs."],
        model_logic_summary="Appears to solve, per lever, the smallest change "
        "that flips the verdict band, tagging feasibility and dollar impact. "
        "A sensitivity / what-if analysis. Exact solver logic: needs source "
        "documentation.",
        why_it_matters="Turns a verdict into an action map — it names the "
        "binding constraints that diligence should target.",
        diligence_use_cases=["Staging the 'what we're waiting for' list — the "
                            "levers whose movement would change the call."],
        interpretation_guidance=[
            "This is a what-if / sensitivity read, NOT a guaranteed action or "
            "recommendation — if a lever's feasibility is low, the verdict "
            "holds.",
            "On this page the claims are fixtures; treat $ impacts as "
            "directional, to be verified before IC use.",
        ],
        limitations=["Only as good as the inputs and the bands it tests; it "
                     "describes what WOULD change a conclusion, not what will."],
        related_routes=["/diligence/risk-workbench", "/diligence/value",
                       "/diligence/bridge-audit"],
        metric_ids=["denial_rate", "days_in_ar", "value_creation_opportunity"],
        data_source_ids=["canonical_claims_dataset", "model_output"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/deal-mc", "Deal Monte Carlo",
        short_description="Monte Carlo over a deal's full 5-year hold — "
        "distributions of EBITDA, MOIC, and IRR, not a single point estimate.",
        primary_purpose="Show the spread of outcomes by simulating many "
        "stochastic paths across the deal's value-creation levers.",
        common_questions=["What's the range of outcomes, not just the base "
                         "case?", "How likely is a sub-1x result?"],
        inputs=["Capital structure + assumption inputs (EV, equity, debt, "
                "entry multiple, revenue/EBITDA, growth mean/σ, denial "
                "improvement, regulatory headwind, lease, cyber, exit multiple "
                "mean/σ, hold years, #runs); a fixture hydrates a scenario."],
        outputs=["Per page labels: P50/P75 MOIC, P50 IRR, P(MOIC<1x), "
                 "P(MOIC≥3x), and per-hold-year EBITDA/return bands."],
        key_metrics=["P50 MOIC", "P75 MOIC", "P50 IRR", "P(MOIC<1x)",
                     "P(MOIC≥3x)"],
        data_sources=["User-supplied assumptions + model-simulated paths "
                      "(CCD-native when a fixture is picked)."],
        model_logic_summary="Appears to draw stochastic paths over each lever "
        "and aggregate to MOIC/IRR/EBITDA distributions. Exact driver "
        "distributions: needs source documentation.",
        why_it_matters="Communicates uncertainty around the base case — the "
        "tail, not just the median.",
        diligence_use_cases=["Stress-reading the downside distribution before "
                            "underwriting a return."],
        interpretation_guidance=[
            "Outputs are SIMULATED distributions from the supplied "
            "assumptions, NOT a forecast or a guarantee — change the inputs "
            "and the distribution moves.",
            "Read the downside tail (P(MOIC<1x)), not only the median.",
        ],
        limitations=["Only as good as the input assumptions and the (model) "
                     "driver distributions; should be verified before IC use."],
        related_routes=["/diligence/risk-workbench", "/diligence/exit-timing",
                       "/diligence/covenant-stress"],
        metric_ids=["moic", "irr", "ebitda", "exit_multiple"],
        data_source_ids=["model_output", "canonical_claims_dataset"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/diligence/deal-autopsy", "Deal Autopsy",
        short_description="Reduces a target to a 9-dimension signature and "
        "ranks a curated library of historical PE-healthcare deals by "
        "similarity, surfacing their outcomes.",
        primary_purpose="Flag historical-analogue risk — 'whose playbook does "
        "this deal most resemble, and how did theirs end?'",
        common_questions=["Which historical deals does this most resemble?",
                         "Are we about to repeat a known failure?"],
        inputs=["A target signature (from a CCD fixture or query params) over "
                "9 risk dimensions; the curated historical deal library."],
        outputs=["Per page labels: a ranked matches table (Rank, Deal, "
                 "Sponsor, Sector, Outcome, Year, Similarity, Distance) and a "
                 "library table with each deal's primary driver."],
        key_metrics=["Similarity %", "Signature distance", "Match outcomes"],
        data_sources=["The target's 9-dim signature + a curated historical "
                      "deal library (public precedents)."],
        model_logic_summary="Ranks library deals by Euclidean distance in a "
        "9-dimension signature space; outputs similarity, not a risk "
        "probability.",
        why_it_matters="Surfaces the historical-analogue risk the bull case "
        "tends to ignore.",
        diligence_use_cases=["Framing the bear case around the closest "
                            "historical precedents."],
        interpretation_guidance=[
            "This is RETROSPECTIVE pattern matching — a similar historical "
            "outcome is a signal to investigate, NOT causal proof the target "
            "shares that fate.",
            "Similarity % is geometric closeness of signatures, not a "
            "probability of repeating the outcome.",
        ],
        limitations=["Bounded by the curated library and the 9 chosen "
                     "dimensions; a near match still needs deal-level "
                     "diligence."],
        related_routes=["/bear-cases", "/screening/bankruptcy-survivor",
                       "/diligence/risk-workbench"],
        data_source_ids=["public_transaction_corpus", "canonical_claims_dataset"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/covenant-stress", "Covenant Stress",
        short_description="A covenant & capital-structure stress lab — "
        "quantifies per-covenant breach probability across simulated EBITDA "
        "paths and quarters.",
        primary_purpose="Stress-test how much headroom a deal's covenants have "
        "under a range of EBITDA paths, not predict an actual breach.",
        common_questions=["How much covenant headroom does this structure "
                         "have?", "Under stress, when might a covenant get "
                         "tight?"],
        inputs=["Capital-structure inputs (total debt, EBITDA Y0, growth, "
                "volatility) and covenant definitions; simulated EBITDA paths."],
        outputs=["Per page labels: KPIs (Max Breach Prob, Earliest 50% "
                 "Breach, Simulated Paths, Quarters Tested) and a per-covenant "
                 "table (Peak Breach %, Peak Quarter, 50%/25% first-at, median "
                 "cure $, interpretation)."],
        key_metrics=["Max breach probability", "Earliest 50%-breach quarter",
                     "Simulated paths", "Covenant cushion"],
        data_sources=["User capital-structure inputs + model-simulated EBITDA "
                      "paths."],
        model_logic_summary="Appears to compose simulated EBITDA paths with "
        "per-covenant breach-probability curves by quarter. Exact path/curve "
        "math: needs source documentation.",
        why_it_matters="Covenant headroom is a primary downside-risk lens in a "
        "levered deal.",
        diligence_use_cases=["Pressure-testing leverage and covenant package "
                            "before committing to a structure."],
        interpretation_guidance=[
            "These are STRESS-TEST probabilities over simulated paths — a "
            "'breach probability' is a what-if under the assumptions, NOT a "
            "prediction that a covenant will actually breach.",
            "Change the debt/EBITDA/volatility inputs and the probabilities "
            "move; verify before IC use.",
        ],
        limitations=["Only as good as the input structure and the (model) "
                     "EBITDA-path assumptions."],
        related_routes=["/diligence/deal-mc", "/diligence/bridge-audit",
                       "/regulatory-calendar"],
        metric_ids=["covenant_cushion", "leverage", "ebitda"],
        data_source_ids=["model_output"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/exit-timing", "Exit Timing",
        short_description="Exit-timing + buyer-type fit — varies the hold year "
        "(2–7) and buyer archetype to find the return-maximizing exit path.",
        primary_purpose="Explore which hold year and buyer type look best for "
        "a deal, as a scenario read — not a market-timing call.",
        common_questions=["When might be the best time to exit?",
                         "Which buyer type fits this deal?"],
        inputs=["Capital structure + assumptions (equity, debt, EBITDA, "
                "growth, peer multiple, regulatory verdict, payer share, "
                "management score); Deal-MC year bands, market-intel peer "
                "multiples, and historical buyer-fit patterns."],
        outputs=["Per page labels: KPIs (optimal Year, Expected MOIC, Expected "
                 "IRR, probability-weighted proceeds) and buyer-fit cards "
                 "(multiple delta, close certainty, time to close)."],
        key_metrics=["Optimal hold year", "Expected MOIC", "Expected IRR",
                     "Probability-weighted proceeds"],
        data_sources=["User inputs + model-simulated year bands + market-intel "
                      "peer multiples + historical buyer patterns."],
        model_logic_summary="Appears to combine Deal-MC year-band "
        "distributions with buyer-type multiple/closing assumptions to rank "
        "exit paths. Exact scoring: needs source documentation.",
        why_it_matters="Exit timing and buyer fit are major IRR levers late in "
        "the hold.",
        diligence_use_cases=["Framing a base exit plan and the buyer "
                            "archetypes to cultivate."],
        interpretation_guidance=[
            "This is SCENARIO analysis over hold years and buyer types — NOT a "
            "prediction of market timing or a guaranteed exit multiple.",
            "Expected proceeds are probability-weighted model outputs, to be "
            "verified before IC use.",
        ],
        limitations=["Depends on input assumptions and the model/market peer "
                     "data; not a market forecast."],
        related_routes=["/diligence/deal-mc", "/diligence/deal-autopsy",
                       "/hold-analysis"],
        metric_ids=["moic", "irr", "exit_multiple", "hold_period"],
        data_source_ids=["model_output", "public_market_data",
                         "public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/ingest", "Ingestion",
        short_description="Phase 1 — ingestion & normalization: raw 837/835 "
        "EDI, EHR exports, and spreadsheets funneled into a single versioned "
        "Canonical Claims Dataset (CCD).",
        primary_purpose="Turn messy multi-source claims data into one "
        "normalized CCD, with a row-level transformation log.",
        common_questions=["How is the claims data normalized?",
                         "What was changed or flagged during ingest?"],
        inputs=["Claims source files (837/835 EDI, EHR exports, CSV/XLSX). On "
                "this page these are demo fixtures; production uploads are "
                "deferred per source."],
        outputs=["Per page labels: a transformation log (ccd_row_id, source "
                 "file, row, rule, target field, severity) plus the resulting "
                 "Canonical Claims Dataset."],
        key_metrics=["Rows ingested", "Transformation rules applied",
                     "Validation flags"],
        data_sources=["Claims source files normalized into the Canonical "
                      "Claims Dataset (837 / 835 / EHR exports)."],
        model_logic_summary="Per source, dispatches readers by file type and "
        "normalizes — it validates CPT/HCPCS and ICD-10 codes, reconciles "
        "835↔837 remittances, dedups across EHRs, and row-logs every "
        "coercion. No predictive model.",
        why_it_matters="Every downstream KPI/QoE/bridge read sits on top of "
        "this CCD — its normalization quality bounds everything after it.",
        diligence_use_cases=["Confirming the claims data is clean and "
                            "auditable before relying on derived KPIs."],
        interpretation_guidance=[
            "Based on source, ingest validates codes and reconciles 835/837 — "
            "but on this page it runs on demo fixtures, so it is not target "
            "data and not an auth-gated production upload.",
            "The transformation log is an audit trail of coercions, not a "
            "guarantee the source data was complete.",
        ],
        limitations=["Fixture-driven here; production / authenticated uploads "
                     "are deferred per the page's own note."],
        related_routes=["/diligence/benchmarks", "/diligence/qoe-memo",
                       "/diligence/root-cause"],
        data_source_ids=["canonical_claims_dataset", "edi_837", "edi_835",
                         "ehr_export"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
    _ctx(
        "/diligence/management", "Management",
        short_description="A management scorecard — per-executive scored cards "
        "across four dimensions, a roster aggregate, and a named EBITDA-bridge "
        "haircut.",
        primary_purpose="Support a structured read on management quality and "
        "translate it into a bridge haircut input — not pass a definitive "
        "verdict.",
        common_questions=["How does this management team score?",
                         "What haircut does management risk imply?"],
        inputs=["An executive roster (demo team on this page) scored on "
                "forecast reliability, comp structure, tenure, and prior-role "
                "reputation; optional target name + guidance EBITDA."],
        outputs=["Per page labels: per-exec cards (four dimension scores + "
                 "weighted overall, with a red-flag override), a roster "
                 "aggregate, a recommended haircut, and a JSON export."],
        key_metrics=["Per-executive scores", "Overall management score",
                     "Recommended EBITDA haircut"],
        data_sources=["A demo executive roster (illustrative) + user-supplied "
                      "target name / guidance EBITDA."],
        model_logic_summary="Scores each executive on four dimensions, applies "
        "a red-flag override, aggregates, and derives a bridge haircut. The "
        "scoring inputs are the judgment; exact weights: needs source "
        "documentation.",
        why_it_matters="Management quality is a core qualitative diligence "
        "axis and a real EBITDA-bridge input.",
        diligence_use_cases=["Structuring the management assessment and its "
                            "haircut into the value bridge."],
        interpretation_guidance=[
            "This SUPPORTS a management assessment via a scoring framework — "
            "it is not a definitive management-quality judgment.",
            "On this page the roster is an illustrative demo; real rosters "
            "(CIM / reference notes) are not yet wired, per the page's banner.",
        ],
        limitations=["Demo-data driven; scores reflect the inputs entered, "
                     "and should be verified before IC use."],
        related_routes=["/diligence/bridge-audit", "/diligence/ic-packet"],
        data_source_ids=["demo_fixture", "deal_profile"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
    _ctx(
        "/diligence/physician-attrition", "Physician Attrition",
        short_description="Scores each provider's 18-month flight-risk and "
        "surfaces the EBITDA at risk from potential departures.",
        primary_purpose="Quantify physician flight-risk as a diligence signal "
        "and size the revenue/EBITDA exposure it implies.",
        common_questions=["Which providers are flight risks?",
                         "How much EBITDA is exposed to attrition?"],
        inputs=["A provider roster (demo fixture on this page) with tenure, "
                "age, collections trend, local competition, employment type."],
        outputs=["Per page labels: total EBITDA-at-risk, band counts "
                 "(Critical/High/Medium/Low), and a flight-risk roster "
                 "(Provider, Specialty, Employment, Flight prob, Band, "
                 "Collections, $ at risk, Top driver)."],
        key_metrics=["Flight-risk probability", "EBITDA at risk",
                     "Provider productivity"],
        data_sources=["A provider roster (demo fixture) scored by a model."],
        model_logic_summary="Appears to extract per-provider features and "
        "score an 18-month flight-risk probability (logistic regression), with "
        "feature contributions. Exact coefficients: needs source "
        "documentation.",
        why_it_matters="In provider-group deals, physician retention is a "
        "first-order driver of post-close revenue.",
        diligence_use_cases=["Prioritizing retention/comp focus on the highest "
                            "flight-risk, highest-value providers."],
        interpretation_guidance=[
            "Flight-risk is a model-estimated RISK SIGNAL, NOT a prediction "
            "that a given provider will leave.",
            "On this page the roster is a demo fixture, not the target's "
            "actual providers — verify before IC use.",
        ],
        limitations=["Demo-roster driven; scores are model estimates bounded "
                     "by the inputs."],
        related_routes=["/diligence/physician-eu", "/diligence/value",
                       "/diligence/deal-mc"],
        metric_ids=["physician_attrition", "provider_productivity"],
        data_source_ids=["provider_roster", "model_output", "demo_fixture"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/screening/bankruptcy-survivor", "Bankruptcy Scan",
        short_description="A rapid pre-screen of a deal's structure against 12 "
        "patterns drawn from PE-healthcare bankruptcies (Steward / Envision / "
        "Mednax precedents).",
        primary_purpose="Flag, early, whether a deal's structure matches the "
        "moves that have already broken comparable deals.",
        common_questions=["Does this deal match a known failure playbook?",
                         "What structural patterns fire here?"],
        inputs=["Deal structure inputs (specialty, states, legal structure, "
                "landlord, lease terms, EBITDAR coverage, OON revenue share, "
                "geography); no CCD/claims required."],
        outputs=["Per page labels: a verdict band (GREEN / YELLOW / RED / "
                 "CRITICAL) and a pattern-check table (Category, Check, "
                 "Status, narrative) citing the named historical precedent."],
        key_metrics=["Verdict band", "Patterns fired (of 12)",
                     "Named-case matches"],
        data_sources=["Named-case fingerprints from the public-deals corpus "
                      "(entry EV + outcome) + the user's structure inputs."],
        model_logic_summary="Deterministic, rule-based pattern matching (per "
        "source: 0 fired = GREEN, 1-2 = YELLOW, 3+ or any critical = RED, full "
        "named-case replay = CRITICAL). Not ML, not probabilistic.",
        why_it_matters="Surfaces structural distress analogues the bull case "
        "may overlook, with a named precedent attached.",
        diligence_use_cases=["A fast pre-screen before committing diligence "
                            "resources; framing the bear case."],
        interpretation_guidance=[
            "Each fired pattern is a falsifiable structural CLAIM and a "
            "diligence signal — not a prediction or a verdict that the deal "
            "will fail.",
            "Per the page: pre-screening only, not a legal opinion and not a "
            "replacement for the full analysis packet — verify before IC use.",
        ],
        limitations=["Matches structure to historical precedent; it cannot see "
                     "deal-specific facts the inputs don't capture."],
        related_routes=["/diligence/risk-workbench", "/diligence/deal-autopsy",
                       "/bear-cases"],
        metric_ids=["bankruptcy_pattern_match"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    # ── Library & Reference ─────────────────────────────────────────
    _ctx(
        "/metric-glossary", "Metric Glossary",
        short_description="A reference glossary defining every metric used "
        "across PEdesk — definition, why it matters, and how it's calculated, "
        "grouped by category.",
        primary_purpose="Give each metric a single authoritative definition so "
        "interpretation stays consistent across the platform.",
        common_questions=["What does this metric mean?",
                         "How is this number calculated?"],
        inputs=["None — it renders a curated definition set (no deal data)."],
        outputs=["Per page labels: per-metric cards (label, units, typical "
                 "range, definition, why it matters, how calculated) with a "
                 "category table of contents."],
        key_metrics=["Metrics defined", "Categories"],
        data_sources=["A curated definition set (HFMA MAP keys + "
                      "platform-supplied definitions)."],
        model_logic_summary="Renders static definitions; no computation, no "
        "deal data.",
        why_it_matters="A shared vocabulary keeps interpretation consistent "
        "across pages and partners.",
        diligence_use_cases=["Looking up exactly what a metric means before "
                            "relying on it."],
        interpretation_guidance=[
            "This is a REFERENCE page — definitions only, never a "
            "target-specific conclusion.",
            "Typical ranges are reference bands, not a given deal's values.",
        ],
        limitations=["Definitions are reference content; some 'how calculated' "
                     "entries may still need source documentation."],
        related_routes=["/methodology", "/rcm-benchmarks"],
        metric_ids=["denial_rate", "days_in_ar", "net_collection_rate",
                    "clean_claim_rate", "moic", "irr", "ev_to_ebitda"],
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
        short_description="Given a query deal's characteristics, finds the "
        "most similar realized deals in the corpus and shows peer benchmark "
        "statistics.",
        primary_purpose="Benchmark a target against similar realized-deal "
        "comps by profile similarity.",
        common_questions=["What deals are comparable to this profile?",
                         "Where does the target sit vs the peer set?"],
        inputs=["Query-deal characteristics via URL (sector, EV, EBITDA, hold, "
                "commercial mix) or a free-text search; with no query it shows "
                "recent realized corpus deals."],
        outputs=["Per page labels: a comparable-transactions table (Deal, "
                 "Sector, Year, EV, EV/EBITDA, MOIC, IRR, Hold, Payer Mix, "
                 "Match) and peer stats (P25/P50/P75 MOIC, loss rate, 3×+ "
                 "rate, target MOIC percentile)."],
        key_metrics=["Peer P25/P50/P75 MOIC", "Peer loss rate", "3×+ rate",
                     "Target MOIC percentile", "Comparables found"],
        data_sources=["The realized-deal corpus (similarity-ranked)."],
        model_logic_summary="Ranks corpus deals by distance-based similarity "
        "(sector, size, entry multiple, payer mix) and summarizes the peer "
        "set. Exact similarity weights: see comparables_page.py.",
        why_it_matters="Comps anchor valuation in observed outcomes.",
        diligence_use_cases=["Sanity-checking entry multiple and return "
                            "expectations against a peer set."],
        interpretation_guidance=[
            "These are algorithmically MATCHED comparables, not an approved or "
            "locked comp set — verify the peer set before IC use.",
            "Thin comp sets are directional only — check the count.",
        ],
        limitations=["Matches are similarity proximity over the corpus; no "
                     "governance over which comps are 'allowed'."],
        related_routes=["/find-comps", "/market-rates", "/comparable-outcomes"],
        metric_ids=["moic", "irr", "ev_to_ebitda", "hold_period", "payer_mix",
                    "benchmark_percentile"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/market-rates", "Market Rates",
        short_description="Corpus percentile reference — P25/P50/P75 MOIC and "
        "IRR by sector, payer-mix bucket, hold period, or region.",
        primary_purpose="Show where realized returns sit by segment, computed "
        "from the corpus.",
        common_questions=["What's the typical MOIC/IRR for this segment?",
                         "How wide is the spread (P25–P75) by sector?",
                         "How do returns vary by payer-mix bucket?",
                         "How does hold period relate to realized MOIC/IRR?",
                         "Which region shows the strongest realized returns?",
                         "Is this segment's sample large enough to trust?",
                         "Are these realized or marked returns?",
                         "What are the caveats on these corpus percentiles?"],
        inputs=["A grouping choice (sector / payer-mix bucket / hold period / "
                "region); the realized-deal corpus."],
        outputs=["Per page labels: corpus P50 MOIC and loss-rate KPIs and a "
                 "distribution table (N, P25/P50/P75 MOIC, P50 IRR, loss rate, "
                 "3×+ rate, avg EV, avg hold) per group."],
        key_metrics=["P25/P50/P75 MOIC by segment", "P50 IRR", "Loss rate",
                     "3×+ rate"],
        data_sources=["The realized-deal corpus (closed deals only; "
                      "percentiles, not means)."],
        model_logic_summary="Computes percentiles of realized MOIC/IRR within "
        "each segment from the corpus; excludes unrealized deals.",
        why_it_matters="Anchors pricing/return expectations in observed "
        "segment distributions.",
        diligence_use_cases=["Placing a deal's expected return inside its "
                            "segment's realized distribution."],
        interpretation_guidance=[
            "These are CORPUS benchmark percentiles, NOT live market pricing "
            "or real-time trading multiples.",
            "Percentiles over a thin segment swing on individual deals — read "
            "the N.",
        ],
        limitations=["Reflects the corpus composition and vintage; not a live "
                     "market quote."],
        related_routes=["/comparables", "/comparable-outcomes",
                       "/irr-dispersion"],
        metric_ids=["moic", "irr", "ev_to_ebitda", "benchmark_percentile"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/rcm-benchmarks", "RCM Benchmarks",
        short_description="A revenue-cycle benchmark reference — P25/P50/P75 "
        "bands for seven RCM metrics across eight facility segments.",
        primary_purpose="Provide industry benchmark bands so a target's RCM "
        "metrics can be read against peers of the same segment.",
        common_questions=["What's a good denial rate / days in A/R for this "
                         "segment?", "Where do peers sit on these metrics?"],
        inputs=["A facility segment selection; the curated benchmark set."],
        outputs=["Per page labels: per-metric tables (Metric with better-"
                 "direction arrow, P25, P50 median, P75) across segments like "
                 "community / academic / critical-access / ASC / behavioral."],
        key_metrics=["Initial denial rate", "Clean claim rate", "Days in A/R",
                     "Net collection rate", "Write-off %", "Cost to collect",
                     "Denial overturn rate"],
        data_sources=["Curated industry benchmarks (per page: HFMA MAP, "
                      "Advisory Board, MGMA, CMS HCRIS aggregates, payer "
                      "denial surveys)."],
        model_logic_summary="Renders curated benchmark bands by segment; no "
        "target computation here.",
        why_it_matters="Benchmarks turn a raw RCM metric into a 'better or "
        "worse than peers' read.",
        diligence_use_cases=["Setting expectations for a target's RCM metrics "
                            "against the right peer segment."],
        interpretation_guidance=[
            "This is a REFERENCE page — peer bands, NOT a target-specific "
            "conclusion. Apply them to a target on /diligence/benchmarks.",
            "Bands depend on the source surveys and the segment chosen.",
        ],
        limitations=["Curated third-party benchmarks; vintage and segment "
                     "definitions vary by source."],
        related_routes=["/metric-glossary", "/diligence/benchmarks",
                       "/comparables"],
        metric_ids=["denial_rate", "clean_claim_rate", "days_in_ar",
                    "net_collection_rate", "bad_debt_rate",
                    "benchmark_percentile"],
        data_source_ids=["benchmark_prior", "cms_hcris"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/library", "Deals Library",
        short_description="A dense, sortable browser over the realized-deal "
        "corpus (600+ deals) that powers the platform's benchmarks and comps.",
        primary_purpose="Browse and filter the corpus of deals behind the "
        "benchmarks, comps, and backtests.",
        common_questions=["What deals are in the corpus?",
                         "Show me realized deals in this sector / regime."],
        inputs=["Sector / regime / MOIC-bucket filters and name search."],
        outputs=["Per page labels: KPIs (Total Deals, Realized, Corpus P50 "
                 "MOIC, Loss Rate, Sectors) and a table (Deal, Sector, Year, "
                 "Regime, EV, EV/EBITDA, MOIC, IRR, Hold, Lev%, Comm%, "
                 "Sponsor, Region, data-quality Grade)."],
        key_metrics=["Corpus P50 MOIC", "Loss rate", "MOIC", "IRR",
                     "EV/EBITDA", "Data-quality grade"],
        data_sources=["The realized-deal corpus (a seeded set of public deals "
                      "plus extended seed data)."],
        model_logic_summary="Renders and filters the corpus rows; the Grade "
        "reflects per-deal data completeness (per source).",
        why_it_matters="It's the reference universe everything else benchmarks "
        "against — knowing its scope frames every comp/benchmark.",
        diligence_use_cases=["Exploring realized precedents and the corpus's "
                            "sector/regime composition."],
        interpretation_guidance=[
            "This is a reference/benchmarking corpus, not a governed deal-room "
            "or source-of-truth for your live deals.",
            "The corpus blends real public deals with seeded data — read it as "
            "calibration context, not a live market feed.",
        ],
        limitations=["Coverage and grades bound what comps/benchmarks can "
                     "say; not a live or exhaustive market database."],
        related_routes=["/comparables", "/market-rates", "/portfolio-analytics"],
        metric_ids=["moic", "irr", "ev_to_ebitda", "hold_period", "leverage",
                    "commercial_payer_exposure"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/deals-library", "Deals Library (alt)",
        short_description="A legacy URL that redirects to /library (the deals "
        "corpus browser).",
        primary_purpose="Preserve the older path; it points at the same corpus "
        "library.",
        common_questions=["Is this different from /library?"],
        inputs=["None — it redirects."],
        outputs=["A redirect to /library (query string preserved)."],
        key_metrics=["Not applicable — redirect."],
        data_sources=["None of its own — see /library."],
        model_logic_summary="A 301 redirect to /library; no rendering of its "
        "own.",
        why_it_matters="Same content as /library under an older URL.",
        diligence_use_cases=["Use /library — this alias resolves there."],
        interpretation_guidance=["Treat this as identical to /library."],
        limitations=["No independent page; it forwards to /library."],
        related_routes=["/library"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
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
        "/research", "Research Hub",
        short_description="A curated index of the platform's research surfaces "
        "— methodology hubs, frameworks, healthcare-PE deep-dives, and the "
        "conference roadmap.",
        primary_purpose="Help users discover the reference/analysis pages "
        "scattered across the platform from one searchable list.",
        common_questions=["What research is available?",
                         "Where's the methodology / a given framework?"],
        inputs=["Topic and format filters; a keyword search over a curated "
                "entry list."],
        outputs=["Per page labels: a filtered, searchable list of research "
                 "entries linking out to each surface."],
        key_metrics=["Not applicable — this is a navigation/index page, not "
                     "an analytic-metric page."],
        data_sources=["A code-curated list of research entries (no stored "
                      "documents)."],
        model_logic_summary="Filters and renders a curated entry list; it "
        "does not store, version, or compute anything.",
        why_it_matters="It's the front door to the platform's reference "
        "material.",
        diligence_use_cases=["Finding the right methodology / framework page "
                            "before a deep dive."],
        interpretation_guidance=[
            "This is a discovery/search index, not a governed diligence "
            "record — it links to pages, it does not store or version content.",
        ],
        limitations=["As current as the curated entry list in code; no "
                     "persistence layer."],
        related_routes=["/methodology", "/conferences", "/market-intel"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.UNKNOWN,
    ),
    _ctx(
        "/notes", "Notes",
        short_description="Full-text and tag-filtered search across the "
        "analyst notes saved on deals.",
        primary_purpose="Find and review the notes the team has recorded "
        "across deals.",
        common_questions=["What did we note on this deal / topic?",
                         "Show notes tagged X."],
        inputs=["A keyword query and/or tag filters (and an optional deal "
                "scope)."],
        outputs=["Per page labels: matching notes with deal link, timestamp, "
                 "author, tags, and a highlighted body excerpt."],
        key_metrics=["Not applicable — this is a notes-search page, not an "
                     "analytic-metric page."],
        data_sources=["The server-stored deal-notes table (persisted; "
                      "soft-deleted rather than hard-removed)."],
        model_logic_summary="Full-text + tag-AND search over stored notes; "
        "soft-delete preserves history.",
        why_it_matters="Keeps the analyst voice/searchable across the book "
        "rather than buried per deal.",
        diligence_use_cases=["Recovering prior observations on a deal or "
                            "theme during diligence."],
        interpretation_guidance=[
            "Notes are user-entered analyst commentary, not computed findings.",
            "They persist server-side with soft-delete, but this is a search "
            "utility — treat it as an archive, not a formal sign-off record.",
        ],
        limitations=["Only surfaces what analysts have written; coverage is "
                     "uneven by deal."],
        related_routes=["/diligence/questions", "/diligence/deal"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    _ctx(
        "/sector-momentum", "Sector Momentum",
        short_description="Compares recent vs prior deal activity (and MOIC) "
        "by sector across the corpus to show acceleration / deceleration.",
        primary_purpose="Show which healthcare sectors have been picking up or "
        "cooling in corpus deal activity and returns.",
        common_questions=["Which sectors are heating up or cooling?",
                         "How has MOIC moved by sector?"],
        inputs=["A window size (?years=N); the realized-deal corpus."],
        outputs=["Per page labels: per-sector tables (Recent count, Prior "
                 "count, Change %, momentum arrow, MOIC P50 recent vs prior)."],
        key_metrics=["Recent vs prior deal count", "Change %",
                     "MOIC P50 recent vs prior"],
        data_sources=["The realized-deal corpus (sliced by sector and "
                      "vintage)."],
        model_logic_summary="Counts corpus deals (and MOIC P50) in a recent "
        "window vs the prior window per sector; a backward-looking comparison.",
        why_it_matters="Sector activity trends frame where sourcing attention "
        "has been flowing.",
        diligence_use_cases=["Framing a sector thesis against where corpus "
                            "activity has trended."],
        interpretation_guidance=[
            "This describes HISTORICAL corpus activity — it is not a forecast "
            "of future sector performance.",
        ],
        limitations=["Reflects corpus composition, which may not mirror the "
                     "live market; thin sectors are noisy."],
        related_routes=["/market-intel", "/irr-dispersion",
                       "/portfolio-analytics"],
        metric_ids=["moic"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/irr-dispersion", "IRR Dispersion",
        short_description="The distribution of realized IRRs across the corpus "
        "— histogram, IRR-vs-MOIC scatter, and sector benchmarks.",
        primary_purpose="Show the spread of realized returns, not just the "
        "median.",
        common_questions=["How wide is the realized IRR spread?",
                         "What share clears a 20% hurdle?"],
        inputs=["The realized-deal corpus (deals with realized IRR + MOIC)."],
        outputs=["Per page labels: KPIs (With IRR Data, IRR P25/P50/P75, "
                 "≥20% hurdle share) and a per-sector table (N, MOIC "
                 "P25/P50/P75, loss %, 3×+ %)."],
        key_metrics=["IRR P25/P50/P75", "≥20% hurdle share", "Loss rate",
                     "3×+ rate"],
        data_sources=["The realized-deal corpus."],
        model_logic_summary="Computes the realized IRR/MOIC distribution and "
        "sector cuts from the corpus; describes outcomes that already "
        "happened.",
        why_it_matters="A good median can hide a wide tail — dispersion is the "
        "point.",
        diligence_use_cases=["Setting return expectations with the realized "
                            "spread, not just a point estimate."],
        interpretation_guidance=[
            "This is a HISTORICAL corpus distribution — not a forward "
            "prediction of returns.",
            "Dispersion is the signal; read the tail, not just the median.",
        ],
        limitations=["Only realized deals; corpus composition shapes the "
                     "distribution."],
        related_routes=["/market-rates", "/comparable-outcomes",
                       "/hold-analysis"],
        metric_ids=["irr", "moic", "benchmark_percentile"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/hold-analysis", "Hold Analysis",
        short_description="The relationship between hold period and realized "
        "returns across the corpus — distribution, MOIC-vs-hold scatter, "
        "buckets, and outliers.",
        primary_purpose="Show how realized returns vary with hold duration in "
        "the corpus.",
        common_questions=["How does hold length relate to realized MOIC?",
                         "What's the typical hold for this sector?"],
        inputs=["The realized-deal corpus (deals with hold + MOIC)."],
        outputs=["Per page labels: hold KPIs (P25/P50/P75/mean), a hold-vs-"
                 "MOIC scatter, hold-bucket stats (MOIC P25/P50/P75, IRR P50, "
                 "win %), and long-hold/poor-return outliers."],
        key_metrics=["Hold P25/P50/P75", "MOIC by hold bucket", "Win rate"],
        data_sources=["The realized-deal corpus."],
        model_logic_summary="Computes percentiles and buckets of realized "
        "hold vs realized MOIC and flags outliers; a backward-looking "
        "association, not an optimizer.",
        why_it_matters="Hold duration is a major return lever; the corpus "
        "shows how it has actually played out.",
        diligence_use_cases=["Setting a realistic hold expectation against "
                            "corpus norms for the sector."],
        interpretation_guidance=[
            "This describes the HISTORICAL hold/return association in the "
            "corpus — it does not prescribe an optimal hold or predict a "
            "deal's outcome.",
        ],
        limitations=["Association, not causation; corpus composition and "
                     "survivorship shape the picture."],
        related_routes=["/irr-dispersion", "/comparable-outcomes",
                       "/diligence/exit-timing"],
        metric_ids=["hold_period", "moic", "irr"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/comparable-outcomes", "Comparable Outcomes",
        short_description="Given a sector + EV (or a corpus deal id), returns "
        "the top-N most-similar realized deals and their MOIC / IRR "
        "distribution.",
        primary_purpose="Provide an underwriting reality check from the "
        "realized outcomes of comparable deals.",
        common_questions=["What did comparable deals actually return?",
                         "Is the projected MOIC above what comps achieved?"],
        inputs=["Sector, entry EV, year, optional sponsor (or a corpus "
                "deal_id)."],
        outputs=["Per page labels: an outcome strip (median MOIC and IRR with "
                 "P25/P75, median hold, win rate ≥2.5×) and a comparable "
                 "table (Match, Deal, Year, Buyer, EV, MOIC, IRR, Hold); a "
                 "CSV / memo-bullet export."],
        key_metrics=["Comp P50 MOIC", "Win rate (≥2.5×)", "Median IRR",
                     "Comparable count"],
        data_sources=["The realized-deal corpus (top-N by match score)."],
        model_logic_summary="Ranks corpus deals by a weighted match score "
        "(sector, size, year, payer mix, sponsor) and summarizes their "
        "realized outcomes. Match weights are per source.",
        why_it_matters="Realized comp outcomes are the reality check on an "
        "underwriting case.",
        diligence_use_cases=["Testing whether a projected return is supported "
                            "by what comparable deals actually delivered."],
        interpretation_guidance=[
            "Comps are similarity-MATCHED, not an approved/locked comp set — "
            "verify the peer set before IC use.",
            "If a target's projected MOIC sits above comp P75, the bear case "
            "must refute that.",
        ],
        limitations=["Thin matches are directional; outcomes are realized "
                     "corpus history, not a forward guarantee."],
        related_routes=["/comparables", "/market-rates",
                       "/sponsor-track-record"],
        metric_ids=["moic", "irr", "hold_period", "benchmark_percentile"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/bear-cases", "Bear Cases",
        short_description="Auto-synthesizes a deal's bear case — ranked "
        "evidence cards by theme, EBITDA-at-risk, and an IC-memo drop-in — "
        "from the deal's module outputs.",
        primary_purpose="Make the downside thesis explicit, ranked, and cited "
        "back to its source modules.",
        common_questions=["What's the bear case on this deal?",
                         "How much EBITDA is at risk and why?"],
        inputs=["A deal's pipeline / module outputs (regulatory, credit, "
                "operational, market, structural, pattern signals)."],
        outputs=["Per page labels: KPIs (EBITDA at Risk, Critical/High/Medium "
                 "items, Modules Pulled), themed evidence cards, and an "
                 "IC-memo drop-in block with deep links to each source."],
        key_metrics=["EBITDA at risk", "Critical / high / medium counts",
                     "Modules pulled"],
        data_sources=["Synthesized from the deal's analytic module outputs."],
        model_logic_summary="Pulls the deal's module outputs and composes them "
        "into ranked, themed downside evidence; it aggregates other engines "
        "rather than computing new findings.",
        why_it_matters="A defensible, cited bear case is expected at IC.",
        diligence_use_cases=["Assembling the downside narrative and the "
                            "EBITDA-at-risk tally for the deck."],
        interpretation_guidance=[
            "This is a counter-narrative SYNTHESIS that ranks downside "
            "evidence — it is not a final verdict that the deal fails.",
            "Each card inherits its source module's caveats; verify before "
            "IC use.",
        ],
        limitations=["Only as complete as the modules it pulls; absence of a "
                     "card is not absence of risk."],
        related_routes=["/diligence/risk-workbench", "/diligence/deal-autopsy",
                       "/screening/bankruptcy-survivor"],
        metric_ids=["risk_score"],
        data_source_ids=["model_output"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/regulatory-calendar", "Regulatory Calendar",
        short_description="A curated timeline of regulatory events (CMS / OIG "
        "/ FTC / DOJ) mapped to the thesis drivers each could 'kill'.",
        primary_purpose="Track regulatory dates that could move or break a "
        "thesis, tied to named events.",
        common_questions=["What regulatory events are coming?",
                         "Which thesis drivers does an event threaten?"],
        inputs=["A curated event set (publish/effective dates, affected "
                "specialties, thesis-driver kill map)."],
        outputs=["Per page labels: a timeline of events with KPIs (events "
                 "scanned, kill-switch events) and the thesis drivers each "
                 "event affects."],
        key_metrics=["Regulatory events scanned", "Kill-switch events"],
        data_sources=["A curated list compiled from Federal Register / CMS "
                      "rules / FTC-DOJ actions (a maintained snapshot)."],
        model_logic_summary="Renders the curated events and maps each to the "
        "thesis drivers it could affect; no live computation.",
        why_it_matters="Regulatory timing can invalidate a thesis driver on a "
        "specific date — this surfaces those dates.",
        diligence_use_cases=["Stress-testing a thesis against upcoming "
                            "regulatory events."],
        interpretation_guidance=[
            "This is a CURATED snapshot, not a live feed — per source it needs "
            "quarterly refresh, so confirm dates against primary sources "
            "before relying on them.",
        ],
        limitations=["Manually maintained; may lag the latest rulemaking "
                     "between refreshes."],
        related_routes=["/market-intel", "/bear-cases"],
        data_source_ids=["regulatory_calendar_sources"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/market-intel", "Market Intelligence",
        short_description="A curated market overlay — public operator comps "
        "(EV/EBITDA, EV/Revenue, payer mix), private transaction multiples, "
        "and a context-filtered healthcare-PE news feed.",
        primary_purpose="Give a target's category some public-market and "
        "transaction context.",
        common_questions=["How are public operators priced?",
                         "What are private multiples for this specialty?"],
        inputs=["The target's category / specialty / size (to filter the "
                "curated comps, multiples, and news)."],
        outputs=["Per page labels: a public-comp table (ticker, name, revenue, "
                 "EV/EBITDA) with an EV/EBITDA-vs-revenue scatter, private "
                 "transaction multiples, and a filtered news feed."],
        key_metrics=["Public-operator EV/EBITDA", "Private transaction "
                     "multiples"],
        data_sources=["Curated public data — operator 10-K/10-Q filings and "
                      "published transaction aggregates, plus curated news "
                      "headlines."],
        model_logic_summary="Filters and renders curated YAML content to the "
        "target's context; it does not fetch live data.",
        why_it_matters="Public comps and private multiples frame a deal's "
        "pricing against the market.",
        diligence_use_cases=["Sanity-checking entry pricing against public "
                            "operators and recent transactions."],
        interpretation_guidance=[
            "This is CURATED public data, NOT a live data feed — per source it "
            "is refreshed quarterly from filings, so verify recency before "
            "IC use.",
        ],
        limitations=["Snapshot content; multiples and news lag between "
                     "refreshes."],
        related_routes=["/market-rates", "/regulatory-calendar", "/research"],
        metric_ids=["ev_to_ebitda"],
        data_source_ids=["public_market_data", "sec_edgar"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/corpus-backtest", "Corpus Backtest",
        short_description="Cross-matches the platform's predicted outcomes "
        "against the realized-deal corpus and scores forecast accuracy "
        "(falling back to corpus self-analysis when no predictions match).",
        primary_purpose="Validate how well the platform's deal predictions "
        "lined up with realized corpus outcomes.",
        common_questions=["How accurate were the platform's predictions?",
                         "What's the match rate against the corpus?"],
        inputs=["Platform predictions (where available) + the realized-deal "
                "corpus."],
        outputs=["Per page labels: KPIs (Corpus Deals, Matched %, Realized, "
                 "Vintages) and a predictions-vs-realized panel; a corpus "
                 "self-analysis fallback (realized MOIC by vintage / "
                 "subsector) when no predictions match."],
        key_metrics=["Match rate", "Realized MOIC by vintage / subsector"],
        data_sources=["Platform predictions + the realized-deal corpus."],
        model_logic_summary="Matches predicted deals to corpus realized "
        "outcomes and scores accuracy; this is backward-looking validation, "
        "not a forward forecast.",
        why_it_matters="Backtesting is how forecast quality is checked before "
        "anyone leans on a prediction.",
        diligence_use_cases=["Gauging how much confidence the platform's "
                            "forecasts have earned historically."],
        interpretation_guidance=[
            "This is VALIDATION / accuracy-scoring against past outcomes — not "
            "a decision-ready forward prediction.",
            "Distinct from /backtest (the corpus-formula calibration); this "
            "scores platform predictions vs realized.",
        ],
        limitations=["Limited by how many predictions match the corpus; falls "
                     "back to descriptive corpus stats otherwise."],
        related_routes=["/backtest", "/comparable-outcomes"],
        metric_ids=["moic", "irr"],
        data_source_ids=["public_transaction_corpus", "model_output"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/backtest", "Backtest",
        short_description="Corpus-calibrated model validation — how well "
        "entry-level signals (multiple, leverage, payer mix, sector) "
        "retrodict realized MOIC across the corpus.",
        primary_purpose="Validate that a simple corpus-fitted model tracks "
        "realized returns (R² / MAE), as a calibration check.",
        common_questions=["Do entry signals explain realized MOIC?",
                         "What's the model's fit (R²/MAE)?"],
        inputs=["The realized-deal corpus (no platform DB required)."],
        outputs=["Per page labels: KPIs (N realized deals, P50 MOIC, model "
                 "R², MAE), predicted-vs-realized and signal-vs-MOIC "
                 "scatters, and a per-sector breakdown."],
        key_metrics=["Model R²", "MAE", "P50 MOIC", "MOIC by sector"],
        data_sources=["The realized-deal corpus."],
        model_logic_summary="Fits/applies a simple corpus formula and compares "
        "predicted vs realized MOIC; the page itself notes it retrodicts the "
        "corpus (in-sample).",
        why_it_matters="Calibration tells you whether the entry signals carry "
        "real explanatory weight on outcomes.",
        diligence_use_cases=["Judging how much to trust entry-signal-based "
                            "expectations."],
        interpretation_guidance=[
            "Backtests here are IN-SAMPLE to the corpus — treat as validation "
            "/ calibration, not a forward promise.",
            "Distinct from /corpus-backtest (which scores platform "
            "predictions vs realized).",
        ],
        limitations=["In-sample fit can overstate out-of-sample accuracy; "
                     "simple formula only."],
        related_routes=["/corpus-backtest", "/comparable-outcomes",
                       "/market-rates"],
        metric_ids=["moic", "ev_to_ebitda", "hold_period", "leverage"],
        data_source_ids=["public_transaction_corpus", "model_output"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
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
                         "Which deals are unhealthy and why?",
                         "What's the average denial / AR / collection?",
                         "How is the portfolio's health mix distributed?",
                         "Which deals are dragging the portfolio averages?",
                         "What's total net revenue across active deals?",
                         "Where should I focus operating attention first?",
                         "How do I export this for an LP or IC update?",
                         "What are the caveats on these portfolio-level averages?"],
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
        "/portfolio/map", "Portfolio Map",
        short_description="A geographic map of portfolio deals — markers at "
        "state centroids colored by stage and sized by EBITDA opportunity, "
        "with state shading for CON status.",
        primary_purpose="Visualize where the portfolio's deals sit "
        "geographically and how they cluster by stage and size.",
        common_questions=["Where are our deals geographically?",
                         "Which states carry the most opportunity?"],
        inputs=["Portfolio deals (deal_id, name, state, EBITDA opportunity, "
                "stage) from analysis packets."],
        outputs=["Per page labels: an inline US SVG map with deal markers "
                 "(color = stage, size = EBITDA opportunity), CON-state "
                 "shading, and KPIs (Deals Mapped, States, CON States)."],
        key_metrics=["Deals mapped", "States", "CON states",
                     "EBITDA opportunity (marker size)"],
        data_sources=["The portfolio store / analysis packets; CON-status "
                      "shading from public state data."],
        model_logic_summary="Places deals at state centroids and styles "
        "markers by stage/opportunity; CON shading marks Certificate-of-Need "
        "states. A visualization, not an analysis.",
        why_it_matters="Geographic concentration is a portfolio-risk lens "
        "partners read quickly on a map.",
        diligence_use_cases=["Spotting geographic concentration across the "
                            "book at a glance."],
        interpretation_guidance=[
            "This is a geographic VISUALIZATION — CON shading is a status "
            "marker only; it is NOT a market-access / CON-barrier analysis.",
        ],
        limitations=["Markers sit at state centroids (not exact locations); "
                     "shows distribution, not synergy or access analysis."],
        related_routes=["/portfolio", "/portfolio-analytics",
                       "/portfolio/risk-scan"],
        metric_ids=["value_creation_opportunity"],
        data_source_ids=["portfolio_snapshot", "analysis_run"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/deal-corpus-analytics", "Deal Corpus Analytics",
        short_description="Benchmark-corpus analytics across the realized-deal "
        "universe — scorecard, vintage cohorts, concentration, return "
        "distribution, outliers, and payer-mix sensitivity. (Renamed/moved "
        "from 'Portfolio Analytics'; /portfolio-analytics redirects here.)",
        primary_purpose="Provide benchmark views over the 655-deal CORPUS "
        "(NOT the user's live fund/portfolio): what has worked across "
        "vintages, sectors, sponsors, and geographies.",
        common_questions=["Is this my portfolio or a benchmark corpus?",
                         "What does the corpus say worked?",
                         "Where is return concentration / outlier risk?"],
        inputs=["The realized-deal corpus (655+ deals)."],
        outputs=["Per page labels: a scorecard (MOIC/IRR quartiles, home-run "
                 "rate, loss rate, outliers), vintage cohorts, deal-type mix, "
                 "sector/geography/sponsor concentration, and realized-MOIC "
                 "outliers."],
        key_metrics=["MOIC P25/P50/P75", "IRR quartiles", "Home-run rate",
                     "Loss rate", "Concentration", "Outliers (z≥2)"],
        data_sources=["The realized-deal corpus."],
        model_logic_summary="Aggregates the corpus into scorecard / cohort / "
        "concentration views; describes historical corpus outcomes.",
        why_it_matters="It's the 'what has worked' read across the reference "
        "universe that frames a new thesis.",
        diligence_use_cases=["Benchmarking a thesis against corpus-wide "
                            "vintage and concentration patterns."],
        interpretation_guidance=[
            "Scope is the 655-deal CORPUS (historical reference), NOT your "
            "actual fund/portfolio — read it as market history, not your "
            "book's performance.",
            "Concentration/outlier reads describe the corpus composition.",
        ],
        limitations=["Corpus composition and survivorship shape every figure; "
                     "not your fund's actuals."],
        related_routes=["/library", "/irr-dispersion", "/sponsor-track-record"],
        metric_ids=["moic", "irr", "enterprise_value", "benchmark_percentile"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/sponsor-track-record", "Sponsor Track Record",
        short_description="A sortable league table of every PE sponsor in the "
        "corpus — MOIC quartiles, IRR, hold, loss rate, home-run rate, and a "
        "0–1 consistency score.",
        primary_purpose="Benchmark sponsors on their realized corpus outcomes "
        "and outcome consistency.",
        common_questions=["How has this sponsor performed historically?",
                         "Which sponsors are consistent vs lottery-like?"],
        inputs=["The realized-deal corpus, aggregated by sponsor."],
        outputs=["Per page labels: KPIs (Sponsors Tracked, Deals Counted, "
                 "Realized, Overall Median MOIC) and a league table (Med MOIC, "
                 "P25/P75, Med IRR, Hold, Loss %, HR %, Consistency, Avg EV); "
                 "a consistency-vs-MOIC scatter."],
        key_metrics=["Median MOIC", "Median IRR", "Loss rate", "Home-run rate",
                     "Consistency score (0–1)"],
        data_sources=["The realized-deal corpus (sponsor-level aggregation)."],
        model_logic_summary="Aggregates realized outcomes per sponsor and "
        "blends MOIC + IRR dispersion into a 0–1 consistency score. Exact "
        "score formula: see sponsor_track_record.py.",
        why_it_matters="Sponsor history and consistency frame how much weight "
        "to put on a sponsor's stated case.",
        diligence_use_cases=["Reference-checking a sponsor's realized record "
                            "before co-investing or competing."],
        interpretation_guidance=[
            "This is a HISTORICAL corpus reference — past outcomes and "
            "consistency, NOT a guarantee or prediction of future "
            "performance.",
        ],
        limitations=["Bounded by corpus coverage per sponsor; thin records "
                     "are noisy."],
        related_routes=["/comparable-outcomes", "/irr-dispersion",
                       "/portfolio-analytics"],
        metric_ids=["moic", "irr", "hold_period"],
        data_source_ids=["public_transaction_corpus"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/payer-intelligence", "Payer Intelligence",
        short_description="Corpus-wide payer-mix analysis — average mix, the "
        "rank correlation of commercial / Medicaid / self-pay share with "
        "realized MOIC, and four payer-regime bands.",
        primary_purpose="Show how realized returns vary across payer-mix "
        "regimes and how strongly payer share co-moves with MOIC.",
        common_questions=["Does payer mix relate to returns?",
                         "How do returns differ by payer regime?"],
        inputs=["The realized-deal corpus (payer mix + realized MOIC)."],
        outputs=["Per page labels: corpus payer-mix averages, commercial/"
                 "Medicaid ↔ MOIC correlation readouts, and a four-regime "
                 "table (Gov-heavy / Balanced / Commercial-mix / Commercial) "
                 "with MOIC quartiles, IRR, and loss rate."],
        key_metrics=["Commercial / Medicare / Medicaid %",
                     "Commercial%↔MOIC correlation", "MOIC quartiles by "
                     "regime"],
        data_sources=["The realized-deal corpus."],
        model_logic_summary="Computes payer-mix averages and a rank "
        "(Spearman) correlation of payer share vs realized MOIC, plus "
        "per-regime outcome bands.",
        why_it_matters="Payer mix is widely treated as a major returns driver; "
        "this shows whether the corpus bears that out.",
        diligence_use_cases=["Judging whether payer mix is load-bearing or "
                            "incidental to a thesis."],
        interpretation_guidance=[
            "These are CORRELATIONS (rank-based), not causal claims — payer "
            "mix co-moving with MOIC does not establish that it causes "
            "returns.",
            "Regime bands are corpus averages, not a target's outcome.",
        ],
        limitations=["Correlation over the corpus; confounders (sector, "
                     "vintage, sponsor) are not controlled here."],
        related_routes=["/diligence/payer-stress", "/market-rates",
                       "/portfolio-analytics"],
        metric_ids=["payer_mix", "commercial_payer_exposure",
                    "medicaid_exposure", "moic"],
        data_source_ids=["public_transaction_corpus"],
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
    # ── Engagements + market data ───────────────────────────────────
    _ctx(
        "/engagements", "Engagements",
        short_description="The cross-engagement workspace — a list of "
        "consulting engagements with their client, status, and deliverables.",
        primary_purpose="Manage consulting engagements (members, deliverables, "
        "comment stream) in the Chartis-consulting workspace.",
        common_questions=["What engagements are active?",
                         "What's the status of this client engagement?"],
        inputs=["Engagement records (id, name, client, status, created) from "
                "the store; per-engagement members / deliverables / comments."],
        outputs=["Per page labels: a table (ID, Name, Client, Status, Created) "
                 "linking to each engagement's detail page."],
        key_metrics=["Engagements", "Status mix"],
        data_sources=["The engagement records store (engagement metadata, "
                      "roles, deliverables, comments)."],
        model_logic_summary="Lists engagement records and routes to detail "
        "pages; role-based access governs members and deliverable visibility. "
        "No analytic model.",
        why_it_matters="It's the operational home for client-facing consulting "
        "work, distinct from the PE deal pipeline.",
        diligence_use_cases=["Tracking consulting engagements and their "
                            "deliverable status."],
        interpretation_guidance=[
            "These are user-entered engagement records, not deal analytics.",
            "Client-facing viewers see a filtered read-only portal "
            "(/portal/<id>), not this internal workspace.",
        ],
        limitations=["Reflects what's been entered; the list does not link "
                     "engagements to specific deals."],
        related_routes=["/app", "/diligence/qoe-memo"],
        data_source_ids=["engagement_record"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    _ctx(
        "/market-data/state/CA", "Market Data · State (CA)",
        short_description="Per-state hospital market data from CMS HCRIS — the "
        "Medicare-participating hospitals in one state, by revenue.",
        primary_purpose="Show the hospital landscape in a given state (count, "
        "beds, net patient revenue, margin) from public cost-report data.",
        common_questions=["What hospitals are in this state?",
                         "How big is this state's hospital market?"],
        inputs=["The state code in the path (e.g. CA); CMS HCRIS hospital "
                "filings filtered to that state."],
        outputs=["Per page labels: KPIs (Hospitals, Total Beds, Total NPR) and "
                 "a top-50-by-NPR table (Hospital, Beds, NPR, Margin) with "
                 "profile / DCF links."],
        key_metrics=["Hospital count", "Total beds", "Total net patient "
                     "revenue", "Operating margin"],
        data_sources=["CMS HCRIS public hospital cost reports (latest filed "
                      "fiscal year), filtered to the state."],
        model_logic_summary="Filters the latest HCRIS rows to the state and "
        "aggregates count / beds / NPR; margin is (revenue − opex) / revenue. "
        "No model.",
        why_it_matters="A quick public read on a state's hospital market for "
        "sourcing and market-context.",
        diligence_use_cases=["Sizing a state market and finding candidate "
                            "hospitals before deeper screening."],
        interpretation_guidance=[
            "Figures are public HCRIS, which lags 1-2 years and covers only "
            "Medicare-participating hospitals — not a live or complete market "
            "feed.",
            "The state code is a path filter, not a different page type; "
            "top-50-by-NPR is a partial view.",
        ],
        limitations=["HCRIS coverage excludes non-Medicare hospitals; filing "
                     "lag and cost-report artifacts apply."],
        related_routes=["/screen", "/market-rates", "/pipeline"],
        metric_ids=["bed_count", "revenue", "operating_margin"],
        data_source_ids=["cms_hcris"],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
        notes_for_assistant=["The trailing path segment (e.g. 'CA') is a "
                             "state code filter, not part of the page name."],
    ),

    # ── Sector Intelligence (multi-sector expansion) ────────────────
    _ctx(
        "/sector-intelligence", "Sector Intelligence",
        short_description="An honest coverage map of the healthcare-services "
        "sectors PEdesk covers. Live today: Hospitals, Home Health, Hospice, "
        "SNF / Nursing Home, Dialysis, IRF, and LTCH; Outpatient/ASC, "
        "Physician Groups, Dental/DSO and Infusion/DME remain roadmap.",
        primary_purpose="Give the team one honest coverage map of which "
        "sectors have real data/pages now versus which are planned, with the "
        "public-data basis (and limits) of each — and the live screeners to "
        "jump to.",
        common_questions=["Which sectors does PEdesk cover today?",
                          "Which post-acute verticals are live and where are "
                          "their screeners?",
                          "What CMS data backs each live sector?",
                          "Why are ASC, Dental and DMEPOS still roadmap?",
                          "Which sectors have outcome quality vs supply-only data?",
                          "Where do I start for a SNF / dialysis / home-health deal?",
                          "How do I compare operators across these sectors in one state?",
                          "What does 'Live' guarantee about a sector's data depth?",
                          "What's the difference between a live screener and a "
                          "roadmap proxy?"],
        inputs=["A static, hand-maintained sector status list (no data load)."],
        outputs=["Sector cards tagged Live or Roadmap, each with its data "
                 "status; live sectors link to their pages."],
        key_metrics=[_NEEDS],
        data_sources=["Navigation/status surface — links to sector pages; "
                      "underlying data is CMS Provider Data Catalog per sector."],
        model_logic_summary="Static directory; no computation.",
        why_it_matters="Keeps the platform honest about coverage — only "
        "sectors with real data are presented as live.",
        diligence_use_cases=["Orientation: where to start for a given sector "
                             "deal type."],
        interpretation_guidance=[
            "Roadmap sectors are not yet built — no page is linked until its "
            "data is sourced.",
            "'Live' means a real screener backed by vendored CMS data; it does "
            "NOT mean commercial revenue, payer mix, or census are visible.",
            "Sectors differ in data depth: post-acute verticals carry outcome/"
            "quality measures, while roadmap proxies (e.g. DMEPOS, Dental) "
            "would be supply-only — read the per-sector data-status note.",
        ],
        limitations=["A directory, not an analytic page; it carries no data "
                     "of its own. Cross-sector comparison still happens on the "
                     "individual screeners, not here."],
        related_routes=["/home-health", "/hospice", "/nursing-homes",
                        "/dialysis", "/inpatient-rehab",
                        "/long-term-care-hospital"],
        data_source_ids=["cms_provider_data_catalog"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.UNKNOWN,
    ),
    _ctx(
        "/home-health", "Home Health Agencies",
        short_description="A screener of Medicare-certified home health "
        "agencies with publicly reported quality, a state tile-grid map, and "
        "per-state provider tables.",
        primary_purpose="Provide market and provider diligence context for "
        "home-health deals — agency density by state and public quality "
        "(star rating, timely care, functional improvement, discharge to "
        "community).",
        common_questions=["How many home health agencies are in this state?",
                          "What does the home health star rating mean here?",
                          "How does this agency compare to same-state / "
                          "same-city peers?",
                          "How concentrated is this local market and who owns "
                          "the most agencies?",
                          "Is a star-rating or DTC gap an investable signal or "
                          "just variance?",
                          "What share of agencies are proprietary vs non-profit "
                          "vs government?",
                          "What should I ask management given these quality "
                          "measures?",
                          "What's missing from CMS home health data that I'd "
                          "diligence separately?",
                          "Where does this data come from and how fresh is it?"],
        inputs=["Vendored CMS 'Home Health Care Agencies' snapshot (6jpm-sxkc)."],
        outputs=["KPI cards, a state tile-grid map shaded by agency count, "
                 "per-state summaries, and provider/quality tables.",
                 "Picking a state opens a market-intelligence view: a market "
                 "summary (agency count, cities represented, median star "
                 "rating, ownership leader), the star-rating distribution "
                 "(quartiles), an ownership mix, and a city-competition table "
                 "(the CMS HH file carries city, not county) that filters the "
                 "agency list. Each agency profile adds same-state and "
                 "same-city peers plus the agency's state percentile per "
                 "measure."],
        key_metrics=["Home Health Star Rating", "Timely Initiation of Care",
                     "Discharge to Community (HH)"],
        data_sources=["CMS Provider Data Catalog — Home Health Care Agencies "
                      "(6jpm-sxkc)."],
        model_logic_summary="Counts and simple per-state averages over the "
        "vendored CMS file; no composite scores are invented.",
        why_it_matters="Home health is a common, fragmented PE deal type; this "
        "is the public market/quality read to frame a target before diligence.",
        diligence_use_cases=["Sizing the local agency market; spotting quality "
                             "outliers; framing a target's competitive set.",
                             "Reading state/city competition: how concentrated "
                             "the market is, the ownership mix (proprietary vs "
                             "non-profit vs government), and where a target sits "
                             "in the state's quality distribution."],
        interpretation_guidance=[
            "Public benchmark data — NOT the target company's own outcomes or "
            "financials.",
            "Medicare-certified agencies only; commercial/private-pay home "
            "care is not represented.",
            "It is market/provider context, not a final investment "
            "recommendation.",
        ],
        limitations=["Medicare-certified only; public quality not financials; "
                     "claims-based acute-care-hospitalization / ED-use are a "
                     "separate CMS dataset not shown here."],
        related_routes=["/sector-intelligence", "/hospice", "/market-data/map"],
        metric_ids=["home_health_star_rating", "timely_initiation_of_care",
                    "discharge_to_community"],
        data_source_ids=["cms_home_health_provider_data",
                         "cms_provider_data_catalog"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/hospice", "Hospice Providers",
        short_description="A screener of Medicare-certified hospices with "
        "publicly reported HIS quality, a state tile-grid map, and per-state "
        "provider tables.",
        primary_purpose="Provide market and provider diligence context for "
        "hospice deals — hospice density by state and public quality (Hospice "
        "Care Index, composite process measure, visits in last days).",
        common_questions=["How many hospices are in this state?",
                          "What does the Hospice Care Index mean here?",
                          "How does this hospice compare to same-state / "
                          "same-county peers?",
                          "How concentrated is this local market and who owns "
                          "the most hospices?",
                          "Is a Care-Index gap an investable signal or just "
                          "variance?",
                          "What share of hospices are for-profit vs non-profit?",
                          "What compliance risks should I probe given these "
                          "quality measures?",
                          "What's missing from CMS hospice data (CAHPS, "
                          "length-of-stay, live-discharge) that I'd diligence "
                          "separately?",
                          "Where does this data come from and how fresh is it?"],
        inputs=["Vendored CMS 'Hospice - General Information' (yc9t-dgbk) + "
                "'Hospice - Provider Data' HIS measures (252m-zfp9)."],
        outputs=["KPI cards, a state tile-grid map shaded by hospice count, "
                 "per-state summaries, and provider/quality tables.",
                 "Picking a state opens a market-intelligence view: a market "
                 "summary (hospice count, counties represented, median Care "
                 "Index, ownership leader), the Care-Index distribution "
                 "(quartiles), an ownership mix, and a county-competition "
                 "table that filters the hospice list. Each hospice profile "
                 "adds same-state and same-county peers plus the hospice's "
                 "state percentile per measure."],
        key_metrics=["Hospice Care Index", "Hospice Composite Process Measure",
                     "Hospice Visits in Last Days of Life"],
        data_sources=["CMS Provider Data Catalog — Hospice General Information "
                      "(yc9t-dgbk) + Hospice Provider Data (252m-zfp9)."],
        model_logic_summary="Counts and simple per-state averages over the "
        "vendored CMS files; no composite scores are invented.",
        why_it_matters="Hospice is fragmented and referral-dependent with "
        "heavy compliance scrutiny; public quality is a key early diligence "
        "signal.",
        diligence_use_cases=["Sizing the local hospice market; flagging "
                             "quality/compliance outliers via the Care Index.",
                             "Reading state/county competition: market "
                             "concentration, ownership mix (for-profit vs "
                             "non-profit), and where a target sits in the "
                             "state's Care-Index distribution."],
        interpretation_guidance=[
            "Public benchmark data — NOT the target's own outcomes or "
            "financials.",
            "Medicare-certified hospices only.",
            "It is market/provider context, not a final investment "
            "recommendation.",
        ],
        limitations=["Medicare-certified only; public quality not financials; "
                     "CAHPS survey + length-of-stay / live-discharge economics "
                     "are not in these files."],
        related_routes=["/sector-intelligence", "/home-health", "/market-data/map"],
        metric_ids=["hospice_care_index", "hospice_composite_process",
                    "visits_in_last_days"],
        data_source_ids=["cms_hospice_provider_data",
                         "cms_provider_data_catalog"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── 8h loop Phase 1: high-priority CMS / data pages (fallback → curated) ──
    _ctx(
        "/market-data", "Market Data",
        short_description="National hospital market intelligence — heatmaps, "
        "state comparisons, regression views, and hospital density maps over "
        "the CMS HCRIS cost-report universe.",
        primary_purpose="Explore the U.S. hospital market: where hospitals "
        "cluster, how states compare on size/margin, and which markets are "
        "concentrated — the data-exploration surface that frames a target's "
        "geography before diligence.",
        common_questions=[
            "What does this page do and where does its data come from?",
            "Which metrics here are observed CMS data versus derived?",
            "How concentrated is the hospital market in this state?",
            "How should I read these state comparisons in diligence?",
            "What does the regression actually show — correlation, not cause?",
            "What's the freshness/lag on HCRIS cost-report data?",
            "What is NOT visible here that I'd diligence separately?",
            "What would make a market signal investable versus noise?",
        ],
        inputs=["CMS HCRIS hospital cost reports (vendored); state/geography "
                "rollups computed locally."],
        outputs=["State heatmaps, state comparison tables, density maps, and "
                 "regression/scatter views."],
        key_metrics=["Net patient revenue", "Operating margin",
                     "Hospital count / density by state", "Beds"],
        data_sources=["CMS HCRIS (Healthcare Cost Report Information System)."],
        model_logic_summary="Counts, per-state aggregates, and simple "
        "regressions over the vendored HCRIS universe — no fabricated values; "
        "regressions are associational, not causal.",
        why_it_matters="Hospital geography + market structure frame a deal's "
        "competitive set and reimbursement exposure before target diligence.",
        diligence_use_cases=["Sizing a target's local hospital market; "
                             "spotting concentrated vs fragmented geographies; "
                             "benchmarking a state's margin profile."],
        interpretation_guidance=[
            "Medicare cost-report data — NOT commercial revenue or payer mix.",
            "Regression/scatter views are associational; do not infer causation.",
            "HCRIS lags ~1–2 years; treat as structural, not real-time.",
            "Market context, not an investment recommendation.",
        ],
        limitations=["HCRIS Medicare cost reports only; commercial rates, "
                     "payer mix, and real-time volume are not represented."],
        related_routes=["/sector-intelligence", "/portfolio/map", "/cms-sources"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/cms-sources", "CMS Data Sources",
        short_description="Registry of the CMS Open Data / Provider Data "
        "Catalog endpoints PEdesk draws on — dataset IDs, granularity, update "
        "cadence, and key columns.",
        primary_purpose="Make every CMS dataset behind the product "
        "explainable: what it is, its grain, its refresh cadence, and which "
        "fields drive the analytics — the provenance backbone for diligence.",
        common_questions=[
            "Which CMS datasets power PEdesk and how fresh are they?",
            "What is the grain (row meaning) of each dataset?",
            "What are the key columns used for benchmarking?",
            "How often does each source update, and what's the lag?",
            "Which datasets are observed data versus provider-supply proxies?",
            "What can these CMS sources NOT tell me?",
            "Is any of this commercial revenue or payer-specific?",
            "Which dataset backs a given vertical's screener and benchmarks?",
            "How do I cite a specific figure's source and vintage in IC?",
        ],
        inputs=["Static registry of CMS Open Data / Provider Data Catalog "
                "dataset descriptors."],
        outputs=["Source table: name, dataset ID, description, update cadence, "
                 "granularity, key columns."],
        key_metrics=["Dataset ID", "Update cadence", "Granularity",
                     "Record count (where known)"],
        data_sources=["CMS Open Data API + CMS Provider Data Catalog (data.cms.gov)."],
        model_logic_summary="Display-only registry; no computation. Surfaces "
        "provenance so partners can judge each number's source level.",
        why_it_matters="Diligence credibility depends on knowing exactly which "
        "public dataset (and vintage) every figure came from.",
        diligence_use_cases=["Citing a number's source in IC; judging whether "
                             "a metric is observed data vs a Medicare proxy."],
        interpretation_guidance=[
            "Public CMS data — Medicare slice; not commercial volume/rates.",
            "Cadence/lag varies per dataset — read the cadence column.",
            "Provider-supply datasets count providers, not revenue or share.",
        ],
        limitations=["Medicare/Medicaid public data only; no commercial payer "
                     "data, no private-pay visibility."],
        related_routes=["/market-data", "/cms-data-browser", "/data/catalog"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/cms-data-browser", "CMS Public Data Browser",
        short_description="Catalog of the public CMS datasets ingested into "
        "PEdesk, ranked by record count with ingestion status.",
        primary_purpose="Browse the ingested CMS corpus — which datasets "
        "carry the most records, what each covers, and whether each is "
        "current or stale.",
        common_questions=[
            "Which CMS datasets are ingested and how big is each?",
            "Which sources are current versus stale?",
            "What does each dataset cover and at what grain?",
            "Where does this data come from originally?",
            "What's missing from the ingested corpus?",
            "Which datasets feed the live sector verticals?",
            "How stale is too stale for a given analytic?",
            "Are any of these commercial-payer or private-pay datasets?",
        ],
        inputs=["Ingested CMS public-dataset inventory (local)."],
        outputs=["Dataset catalog grid + record-count chart + ingestion status."],
        key_metrics=["Record count per dataset", "Ingestion status",
                     "Dataset coverage"],
        data_sources=["CMS Provider Data Catalog + CMS Open Data (vendored locally)."],
        model_logic_summary="Inventory display + record-count ranking; no "
        "fabricated counts — reflects what is actually ingested locally.",
        why_it_matters="Shows the breadth and freshness of the public-data "
        "foundation the diligence product is built on.",
        diligence_use_cases=["Confirming a dataset is present and current "
                             "before relying on its analytics."],
        interpretation_guidance=[
            "Record counts reflect the vendored snapshot, not a live feed.",
            "Public CMS data only; not commercial performance.",
        ],
        limitations=["Snapshot-based; no runtime CMS API calls. Medicare/"
                     "public scope only."],
        related_routes=["/cms-sources", "/data/catalog", "/market-data"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/data/catalog", "Data Catalog",
        short_description="Every public-data source PEdesk has ingested — a "
        "KPI strip (sources / records / freshness) and a category-grouped "
        "inventory table.",
        primary_purpose="One place to see the full public-data foundation: "
        "what's ingested, how many records, how fresh, grouped by category.",
        common_questions=[
            "What data sources does PEdesk have and how fresh are they?",
            "How many records does each source carry?",
            "Which sources are stale and need a refresh?",
            "What categories of data are covered?",
            "What is the provenance of a given source?",
            "Which sources underpin the sector screeners and benchmarks?",
            "What does the data-quality flag on a source mean?",
            "Is any of this commercial or private-pay data?",
        ],
        inputs=["PortfolioStore data-source inventory (local metadata)."],
        outputs=["KPI strip (sources, records, avg quality, fresh/stale) + "
                 "category-grouped source table."],
        key_metrics=["Source count", "Record count", "Freshness",
                     "Data quality flag"],
        data_sources=["Local PortfolioStore data-source inventory."],
        model_logic_summary="Inventory metadata display; portfolio-wide "
        "infrastructure metadata (not deal analytics).",
        why_it_matters="Establishes which public sources underpin every "
        "analytic surface — the audit trail for diligence.",
        diligence_use_cases=["Verifying source coverage + freshness before "
                             "trusting a downstream metric."],
        interpretation_guidance=[
            "Catalog metadata, not analytics; counts are of ingested records.",
            "All sources are public/official; none are commercial-payer data.",
        ],
        limitations=["Metadata only; reflects the local ingested snapshot."],
        related_routes=["/cms-sources", "/cms-data-browser", "/market-data"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/benchmarks", "RCM Benchmarks",
        short_description="HFMA revenue-cycle KPI scorecard vs benchmark "
        "bands, payer-class liquidation curves, and a denial-driver Pareto — "
        "rendered from an attached engagement's KPI bundle.",
        primary_purpose="Benchmark a target's revenue-cycle KPIs against HFMA "
        "bands and surface the dollar-weighted denial drivers — the RCM "
        "diligence read.",
        common_questions=[
            "How does this target's revenue cycle compare to HFMA benchmarks?",
            "Which KPIs are observed from the engagement data vs missing?",
            "What are the biggest denial drivers by dollars?",
            "How should I read the liquidation curves by payer class?",
            "What's strong evidence here versus thin/insufficient data?",
            "What should I ask management about these denial root causes?",
            "What are the caveats on these benchmark bands?",
            "How much EBITDA upside do the KPI gaps to benchmark imply?",
            "Which denial drivers are quickest to remediate post-close?",
        ],
        inputs=["An attached engagement KPIBundle + CohortLiquidationReport "
                "(no live re-ingest from this page)."],
        outputs=["KPI scorecard vs bands, per-payer liquidation curves, "
                 "denial-driver Pareto. 'Insufficient data' + reason when a "
                 "KPI is absent — never a fabricated number."],
        key_metrics=["Initial denial rate", "Final write-off", "Clean DAR",
                     "Net collection rate"],
        data_sources=["Engagement-supplied RCM data (KPI bundle); HFMA "
                      "benchmark bands."],
        model_logic_summary="Compares supplied KPIs to documented HFMA bands; "
        "missing KPIs render 'Insufficient data' with the reason, not a guess.",
        why_it_matters="Revenue-cycle performance vs peer bands is a core "
        "value-creation lever in healthcare RCM diligence.",
        diligence_use_cases=["Quantifying RCM upside vs benchmark; prioritizing "
                             "denial root-cause remediation by dollars."],
        interpretation_guidance=[
            "Bands are HFMA reference ranges, not the target's covenant.",
            "A missing KPI means data wasn't supplied — not zero.",
            "Liquidation curves are descriptive, not a forecast.",
        ],
        limitations=["Requires an attached engagement bundle; with none, the "
                     "page explains how to attach a CCD rather than inventing "
                     "numbers."],
        related_routes=["/diligence", "/comps", "/methodology"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    # ── 8h loop Phase 1 batch 2: portfolio / diligence / source pages ──
    _ctx(
        "/diligence", "Diligence Workspace",
        short_description="The diligence section index — the playbook of "
        "per-target workbenches (deal profile, ingestion, benchmarks, HCRIS "
        "X-ray, QoE memo, checklist, questions ledger).",
        primary_purpose="Orient a deal team to the diligence surfaces for a "
        "target and route into the right workbench.",
        common_questions=[
            "What diligence tools are available for a target?",
            "Where do I start a new target's diligence?",
            "How do the benchmark / QoE / HCRIS surfaces fit together?",
            "What is observed target data versus public benchmark here?",
            "What should the open-questions ledger capture?",
        ],
        inputs=["Navigation index; per-target data loads in the linked "
                "workbenches, not this page."],
        outputs=["Links/cards to the diligence workbenches + open-questions tracker."],
        key_metrics=["(index page — metrics live on the linked workbenches)"],
        data_sources=["Routes into HCRIS, engagement RCM data, corpus comps."],
        model_logic_summary="Index/navigation page; no computation of its own.",
        why_it_matters="A single entry point keeps the diligence workflow "
        "coherent across per-target surfaces.",
        diligence_use_cases=["Launching + tracking a target's diligence across "
                             "benchmarks, QoE, and the questions ledger."],
        interpretation_guidance=[
            "This is a launcher; each workbench states its own data scope.",
            "Not an investment recommendation.",
        ],
        limitations=["No analytics here — see each linked workbench's caveats."],
        related_routes=["/benchmarks", "/diligence/questions", "/library"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/concentration-risk", "Concentration Risk",
        short_description="Portfolio diversification analysis — HHI plus "
        "CR3 / CR5 concentration ratios across the corpus by category.",
        primary_purpose="Quantify how concentrated the portfolio/corpus is "
        "(subsector, geography, sponsor) so single-point risk is visible "
        "before committing a new deal.",
        common_questions=[
            "How concentrated is the portfolio by subsector / geography?",
            "What do HHI and CR3/CR5 mean here?",
            "Is this composition concentration or market share?",
            "Which categories drive the concentration?",
            "What is a healthy versus risky concentration level?",
            "What are the caveats on these concentration measures?",
            "How would a prospective new deal shift the HHI?",
            "Which single-point exposures should I hedge or diversify first?",
        ],
        inputs=["Corpus deal list (subsector, geography, sponsor categories)."],
        outputs=["HHI + CR3/CR5 by category with diversification commentary."],
        key_metrics=["HHI (sum of squared shares)", "CR3", "CR5"],
        data_sources=["Corpus deal universe (local)."],
        model_logic_summary="HHI = sum(share^2); CRn = top-n share sum — over "
        "COMPOSITION shares (portfolio mix), not market volume.",
        why_it_matters="Concentration is a core portfolio-construction risk; a "
        "single subsector/geography shock hits a concentrated book harder.",
        diligence_use_cases=["Stress-testing single-point exposure before "
                             "adding a correlated deal."],
        interpretation_guidance=[
            "Portfolio COMPOSITION concentration, NOT market share — the "
            "denominator is the corpus, not a real addressable market.",
            "High HHI = concentrated mix, not a valuation claim.",
        ],
        limitations=["Composition-only; says nothing about true market share "
                     "or competitive position."],
        related_routes=["/portfolio-analytics", "/portfolio/heatmap"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/competitive-intel", "Competitive Intelligence",
        short_description="Per-hospital percentile rank on every metric across "
        "four peer groups (national, state, size-matched, system type), with "
        "gaps to P75 / P90 quantifying value-creation headroom.",
        primary_purpose="Show where a hospital sits versus peers on each "
        "metric and how much improvement reaches the top quartile/decile.",
        common_questions=[
            "How does this hospital rank versus peers on each metric?",
            "Which peer group is most relevant — state, size, or system?",
            "How big is the gap to P75 / P90?",
            "Is a percentile gap an investable signal or just variance?",
            "What should I ask management about the largest gaps?",
            "What are the limitations of CMS-based peer ranking?",
            "Which peer group's gap is most defensible to underwrite against?",
            "How does a percentile here differ from the sector-screener percentile?",
        ],
        inputs=["CMS HCRIS hospital metrics; peer groups computed locally."],
        outputs=["Percentile ranks per metric per peer group + gap-to-P75/P90."],
        key_metrics=["Percentile rank", "Gap to P75", "Gap to P90"],
        data_sources=["CMS HCRIS hospital cost reports."],
        model_logic_summary="Ranks the hospital within each peer set; gaps are "
        "distance to peer P75/P90 — descriptive, not a forecast.",
        why_it_matters="Peer gaps are the starting hypothesis for operational "
        "value creation; large, stable gaps flag the biggest levers.",
        diligence_use_cases=["Sizing improvement headroom by metric; framing "
                             "management questions on underperformance."],
        interpretation_guidance=[
            "Percentile is peer deviation, NOT a causal/investment conclusion.",
            "A gap can be structural (case mix), not addressable — verify.",
            "Medicare cost-report metrics; not commercial performance.",
        ],
        limitations=["HCRIS Medicare data only; peer groups are CMS-derived, "
                     "not commercial market peers."],
        related_routes=["/market-data", "/benchmarks", "/methodology"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/lp-dashboard", "LP Portfolio Dashboard",
        short_description="Fund-level LP reporting view — TVPI / DPI / RVPI, "
        "gross/net MOIC, IRR, loss rate, a vintage J-curve, sector exposure, "
        "and top/bottom performers.",
        primary_purpose="A partner-ready, fund-level read of returns and "
        "exposure for LP reporting.",
        common_questions=[
            "What are the fund's TVPI / DPI / RVPI and net MOIC/IRR?",
            "What does the J-curve show about pacing?",
            "Where is the fund concentrated by sector?",
            "Which deals are the top and bottom performers?",
            "Are these realized or marked (unrealized) returns?",
            "What are the caveats on these LP metrics?",
            "How much of TVPI is DPI (realized) versus RVPI (still marked)?",
            "Which sector exposures are driving the fund's loss rate?",
        ],
        inputs=["Portfolio/corpus deal returns + vintages (local)."],
        outputs=["Fund KPI strip, vintage J-curve, sector exposure table, "
                 "performer leaderboard."],
        key_metrics=["TVPI", "DPI", "RVPI", "Net MOIC", "IRR", "Loss rate"],
        data_sources=["Portfolio deal data (local store / corpus)."],
        model_logic_summary="Standard fund-return roll-ups over the deal set; "
        "no fabricated marks — realized vs unrealized distinguished.",
        why_it_matters="LP-facing returns + exposure are the headline fund "
        "narrative; pacing and concentration drive LP questions.",
        diligence_use_cases=["Fund-level performance review; LP-meeting prep."],
        interpretation_guidance=[
            "Distinguish realized (DPI) from marked (RVPI) — marks are estimates.",
            "Sector exposure is composition, not market share.",
            "Not an investment recommendation.",
        ],
        limitations=["Return marks depend on supplied data; unrealized values "
                     "are estimates, not cash."],
        related_routes=["/lp-reporting", "/lp-update", "/portfolio-analytics"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/admin/data-sources", "Data Source Admin",
        short_description="Operational health view of PEdesk's ingested public "
        "data sources — presence, freshness, and ingestion status.",
        primary_purpose="Let an operator verify which public datasets are "
        "loaded and current (admin / infrastructure view).",
        common_questions=[
            "Which data sources are loaded and are they fresh?",
            "Which sources are stale or missing?",
            "Where does each source come from?",
            "When was each source last ingested?",
        ],
        inputs=["Local data-source inventory + ingestion metadata."],
        outputs=["Source health table (presence, freshness, status)."],
        key_metrics=["Source presence", "Freshness", "Ingestion status"],
        data_sources=["Local ingested-source inventory (public CMS data)."],
        model_logic_summary="Status/metadata display; no analytics.",
        why_it_matters="Operators must confirm the data foundation is present "
        "and current before partners rely on downstream analytics.",
        diligence_use_cases=["Operational check that a source is loaded/current."],
        interpretation_guidance=[
            "Admin/infrastructure metadata, not deal analytics.",
            "All sources are public/official; no commercial data.",
        ],
        limitations=["Reflects the local ingested snapshot; no live feeds."],
        related_routes=["/data/catalog", "/cms-sources"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── 8h loop Phase 4: SNF / Nursing Home vertical ──
    _ctx(
        "/nursing-homes", "Nursing Homes (SNF)",
        short_description="A screener of Medicare/Medicaid-certified nursing "
        "homes with CMS five-star ratings (overall, health inspection, "
        "staffing, quality measures), staffing hours, certified beds, Special "
        "Focus status, ownership, and the enforcement-penalty summary — a "
        "state tile-grid map, per-state market intelligence, and county "
        "competition.",
        primary_purpose="Provide market + provider diligence context for SNF "
        "deals: facility density by state, the quality/staffing/survey-risk "
        "profile, ownership mix, and county-level competition.",
        common_questions=[
            "How many nursing homes are in this state and how do they rate?",
            "What do the four CMS star ratings mean and how are they set?",
            "How does this facility compare to same-state / same-county peers?",
            "Is a star-rating gap an investable signal or just variance?",
            "What does the enforcement-penalty summary tell me — and what not?",
            "What is a Special Focus Facility and why does it matter?",
            "What should I ask management given this staffing / turnover read?",
            "What's missing from CMS data that I'd diligence separately?",
            "Where does this data come from and how fresh is it?",
            "Why are 'total fines' not the same as facility revenue?",
        ],
        inputs=["Vendored CMS Nursing Home Care Compare 'Provider Information' "
                "snapshot (NH_ProviderInfo, Apr 2026)."],
        outputs=["KPI cards, a state tile-grid map shaded by facility count, "
                 "per-state market summary (ownership mix, rating "
                 "distribution, county competition), provider tables, and "
                 "per-facility profiles with state percentile + peers."],
        key_metrics=["Overall 5-star rating", "Health-inspection rating",
                     "Staffing rating", "Quality-measure rating",
                     "Certified beds", "RN hours per resident per day"],
        data_sources=["CMS Nursing Home Care Compare — Provider Information."],
        model_logic_summary="Counts, per-state averages, ownership-mix HHI, "
        "rating quartiles, and same-state/county peer percentiles over the "
        "vendored CMS file — no composite scores invented.",
        why_it_matters="SNF is a rich, scrutinized post-acute sector; CMS "
        "ratings, staffing (PBJ-based), survey results, and penalties are key "
        "early quality + compliance signals before target diligence.",
        diligence_use_cases=["Sizing the local SNF market; flagging "
                             "quality/staffing/SFF/penalty outliers; framing a "
                             "target's competitive set + value-creation levers."],
        interpretation_guidance=[
            "Public CMS quality/staffing/survey data — NOT commercial revenue "
            "or payer mix. 'Total fines' is a regulatory penalty, not income.",
            "Star ratings are CMS's methodology; the health-inspection "
            "component is state-survey-driven and can lag.",
            "Staffing is largely PBJ payroll-based but treat as a screening "
            "signal, not audited truth.",
            "A rating/staffing gap may be structural (case mix) — verify; it "
            "is peer deviation, not an investment conclusion.",
            "Market/provider context, not a final investment recommendation.",
        ],
        limitations=["Medicare/Medicaid-certified facilities only; private-"
                     "pay-only facilities, commercial rates, and real-time "
                     "census are not represented. Enforcement detail "
                     "(per-penalty, per-deficiency) is a separate CMS file, "
                     "not in this snapshot."],
        related_routes=["/sector-intelligence", "/home-health", "/hospice"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── 8h loop Phase 4b: Dialysis vertical ──
    _ctx(
        "/dialysis", "Dialysis Facilities",
        short_description="A screener of Medicare-certified dialysis "
        "facilities with the CMS overall five-star rating, dialysis-station "
        "count, ownership/chain, modality offerings, and risk-adjusted "
        "outcome rates (mortality, hospitalization, readmission, transfusion) "
        "— a state tile-grid map, per-state market intelligence, and county "
        "competition.",
        primary_purpose="Provide market + provider diligence context for "
        "dialysis deals: facility density by state, the five-star + "
        "outcome-rate profile, ownership/chain mix, and county competition.",
        common_questions=[
            "How many dialysis facilities are in this state and how do they rate?",
            "What does the dialysis five-star rating capture?",
            "How does this facility compare to same-state / same-county peers?",
            "How should I read the mortality / hospitalization / readmission rates?",
            "Is a rating or outcome gap an investable signal or just variance?",
            "What share of the market is chain-owned (e.g. DaVita / Fresenius)?",
            "What should I ask management given these outcome rates?",
            "What's missing from CMS dialysis data that I'd diligence separately?",
            "Where does this data come from and how fresh is it?",
        ],
        inputs=["Vendored CMS Dialysis Facility Compare 'Listing by Facility' "
                "snapshot (DFC_FACILITY, Mar 2026)."],
        outputs=["KPI cards, a state tile-grid map shaded by facility count, "
                 "per-state market summary (ownership mix, five-star "
                 "distribution, county competition), provider tables, and "
                 "per-facility profiles with state percentile + peers."],
        key_metrics=["Overall five-star rating", "Dialysis stations",
                     "Mortality rate", "Hospitalization rate",
                     "Readmission rate"],
        data_sources=["CMS Dialysis Facility Compare — Listing by Facility."],
        model_logic_summary="Counts, per-state averages, ownership-mix HHI, "
        "five-star quartiles, and same-state/county peer percentiles over the "
        "vendored CMS file — no composite scores invented.",
        why_it_matters="Dialysis is a consolidated, CMS-rich post-acute "
        "sector (two national chains dominate); five-star + outcome rates + "
        "chain mix are strong early diligence signals.",
        diligence_use_cases=["Sizing the local dialysis market; reading "
                             "chain concentration; flagging outcome-rate "
                             "outliers; framing the competitive set."],
        interpretation_guidance=[
            "Public CMS quality data — NOT commercial revenue or payer mix.",
            "Outcome rates are LOWER-is-better, risk-adjusted ESTIMATES with "
            "confidence intervals — read as risk signals, not verdicts, and "
            "not under a 'higher percentile = better' frame.",
            "Five-star availability varies; some facilities are unrated.",
            "A rating/outcome gap may be case-mix driven — verify; it is peer "
            "deviation, not an investment conclusion.",
            "Market/provider context, not a final investment recommendation.",
        ],
        limitations=["Medicare-certified dialysis facilities only; commercial "
                     "rates and real-time census are not represented. ESRD "
                     "QIP / NHSN / ICH-CAHPS detail are separate CMS files, "
                     "not in this snapshot."],
        related_routes=["/sector-intelligence", "/nursing-homes", "/home-health"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/inpatient-rehab", "Inpatient Rehab (IRF)",
        short_description="A screener of Medicare-certified inpatient "
        "rehabilitation facilities with publicly reported CMS measures — "
        "discharge to community (risk-standardized), potentially-preventable "
        "readmissions, and Medicare spending per beneficiary — plus a state "
        "tile-grid map, per-state market intelligence, and county competition.",
        primary_purpose="Provide market + provider diligence context for IRF "
        "deals: facility density by state, the discharge-to-community + "
        "readmission + spending profile, ownership mix, and county competition.",
        common_questions=[
            "How many IRFs are in this state and how do they perform?",
            "What does discharge-to-community (risk-standardized) capture?",
            "How does this facility compare to same-state / same-county peers?",
            "How should I read the readmission and Medicare-spending measures?",
            "Is a performance gap an investable signal or just small-sample noise?",
            "What share of the local IRF market is for-profit vs nonprofit?",
            "What should I ask management given these quality measures?",
            "What's missing from CMS IRF data that I'd diligence separately?",
            "Where does this data come from and how fresh is it?",
        ],
        inputs=["Vendored CMS IRF Compare snapshot — General Information + "
                "Provider Data (headline measures pivoted, Feb 2026)."],
        outputs=["KPI cards, a state tile-grid map shaded by facility count, "
                 "per-state market summary (ownership mix, county competition), "
                 "provider tables, and per-facility profiles with state "
                 "percentile + peers."],
        key_metrics=["Discharge to community (risk-standardized)",
                     "Potentially-preventable readmission rate",
                     "Medicare spending per beneficiary"],
        data_sources=["CMS Inpatient Rehabilitation Facility Compare — "
                      "General Information + Provider Data."],
        model_logic_summary="Counts, per-state discharge-to-community "
        "averages, ownership-mix HHI, and same-state/county peer percentiles "
        "over the vendored CMS file — no composite scores invented.",
        why_it_matters="IRF is a small, CMS-measured post-acute sector; "
        "discharge-to-community, readmissions, and spend are useful early "
        "diligence signals when read with the small-universe caveat.",
        diligence_use_cases=["Sizing the local IRF market; reading ownership "
                             "concentration; flagging quality outliers; framing "
                             "the competitive set."],
        interpretation_guidance=[
            "Public CMS quality data — NOT commercial revenue or payer mix.",
            "Small national universe (~1,200 facilities); per-state samples can "
            "be very small, so treat peer comparisons cautiously.",
            "Readmission (PPR) and Medicare-spending-per-beneficiary are "
            "LOWER-is-better, risk-standardized ESTIMATES — read as risk "
            "signals, not verdicts, and not under a 'higher percentile = "
            "better' frame.",
            "A performance gap may be case-mix driven — verify; it is peer "
            "deviation, not an investment conclusion.",
            "Market/provider context, not a final investment recommendation.",
        ],
        limitations=["Medicare-certified inpatient rehabilitation facilities "
                     "only; commercial rates and real-time census are not "
                     "represented. Measure availability varies by facility."],
        related_routes=["/sector-intelligence", "/nursing-homes", "/dialysis"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/long-term-care-hospital", "Long-Term Care Hospitals (LTCH)",
        short_description="A screener of Medicare-certified long-term care "
        "hospitals with publicly reported CMS measures — discharge to "
        "community (risk-standardized), potentially-preventable readmissions, "
        "Medicare spending per beneficiary, and bed counts — plus a state "
        "tile-grid map, per-state market intelligence, and county competition.",
        primary_purpose="Provide market + provider diligence context for LTCH "
        "deals: facility density and bed capacity by state, the discharge-to-"
        "community + readmission + spending profile, ownership mix, and county "
        "competition.",
        common_questions=[
            "How many LTCHs are in this state and how do they perform?",
            "What does discharge-to-community (risk-standardized) capture?",
            "How does this hospital compare to same-state / same-county peers?",
            "How should I read the readmission and Medicare-spending measures?",
            "Is a performance gap an investable signal or just small-sample noise?",
            "What share of the local LTCH market is for-profit vs nonprofit?",
            "How many beds does this hospital operate?",
            "What's missing from CMS LTCH data that I'd diligence separately?",
            "Where does this data come from and how fresh is it?",
        ],
        inputs=["Vendored CMS LTCH Compare snapshot — General Information + "
                "Provider Data (headline measures pivoted, Feb 2026)."],
        outputs=["KPI cards, a state tile-grid map shaded by facility count, "
                 "per-state market summary (ownership mix, county competition), "
                 "provider tables (with bed counts), and per-facility profiles "
                 "with state percentile + peers."],
        key_metrics=["Discharge to community (risk-standardized)",
                     "Potentially-preventable readmission rate",
                     "Medicare spending per beneficiary", "Total beds"],
        data_sources=["CMS Long-Term Care Hospital Compare — General "
                      "Information + Provider Data."],
        model_logic_summary="Counts, per-state discharge-to-community "
        "averages, ownership-mix HHI, and same-state/county peer percentiles "
        "over the vendored CMS file — no composite scores invented.",
        why_it_matters="LTCH is a very small, CMS-measured post-acute sector; "
        "discharge-to-community, readmissions, spend, and bed capacity are "
        "useful early diligence signals when read with the tiny-universe caveat.",
        diligence_use_cases=["Sizing the local LTCH market and bed capacity; "
                             "reading ownership concentration; flagging quality "
                             "outliers; framing the competitive set."],
        interpretation_guidance=[
            "Public CMS quality data — NOT commercial revenue or payer mix.",
            "Very small national universe (~320 facilities); per-state samples "
            "are often single-digit, so treat peer comparisons very cautiously.",
            "Readmission (PPR) and Medicare-spending-per-beneficiary are "
            "LOWER-is-better, risk-standardized ESTIMATES — read as risk "
            "signals, not verdicts, and not under a 'higher percentile = "
            "better' frame.",
            "A performance gap may be case-mix driven — verify; it is peer "
            "deviation, not an investment conclusion.",
            "Market/provider context, not a final investment recommendation.",
        ],
        limitations=["Medicare-certified long-term care hospitals only; "
                     "commercial rates and real-time census are not "
                     "represented. Measure availability varies by facility."],
        related_routes=["/sector-intelligence", "/inpatient-rehab", "/nursing-homes"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/diligence/xray", "CMS X-Ray",
        short_description="The universal CMS provider diligence scanner: enter "
        "a CCN, provider ID, or facility name and PEdesk resolves the provider "
        "across every live CMS vertical (Hospital, SNF, Home Health, Hospice, "
        "Dialysis, IRF, LTCH), benchmarks it against peers, and renders a "
        "transparent diligence report with red/amber/green/gray signals.",
        primary_purpose="Turn any single CMS provider identifier into a "
        "benchmarked diligence read — identity, detected vertical, source "
        "datasets, peer percentiles, market context, risk signals, and "
        "suggested questions — composing the cross-sector benchmark and "
        "investable-evidence layers in one place.",
        common_questions=[
            "What is the strongest diligence signal for this provider?",
            "What should I ask management given the weak metrics?",
            "How does this provider compare to same-state peers?",
            "What data is missing, and would it change the read?",
            "Can I treat this as investment evidence?",
            "Which benchmarks here are most reliable (sample size)?",
            "Why did this CCN resolve to more than one vertical?",
            "Is this provider an outlier or within normal variance?",
            "How is the peer-relative quality index computed?",
        ],
        inputs=["A CCN / provider id / facility name (optional state), "
                "resolved across the six cross-sector verticals + HCRIS."],
        outputs=["A resolver table (ambiguous matches), or a benchmarked "
                 "report: identity header, diligence signal strip, peer "
                 "benchmark table (percentile + guarded z-score), market "
                 "context, suggested questions, and evidence/limitations."],
        key_metrics=["Peer-relative quality index", "Peer percentile",
                     "z-score (n>=5, sd>0)", "Ownership / locality HHI",
                     "Peer sample size", "Missingness"],
        data_sources=["Reuses the six vertical CMS loaders + HCRIS via the "
                      "cross-sector benchmark and investable-evidence layers."],
        model_logic_summary="Composes existing layers only: percentile + "
        "guarded z-score from investable_evidence, market context + HHI from "
        "cross_sector. Signals are transparent and component-traceable; no "
        "composite black-box score, no new math.",
        why_it_matters="Diligence happens provider-by-provider; the X-Ray is "
        "the analyst workflow that unifies the vertical libraries into one "
        "benchmarked read.",
        diligence_use_cases=["Screening a target by CCN; framing peer position "
                             "and red flags before management meetings; finding "
                             "the local competitive set."],
        interpretation_guidance=[
            "CMS public data only — NOT commercial revenue (except HCRIS "
            "hospital cost-report fields), payer mix, or private-pay volume.",
            "Percentile is peer deviation; the quality index is peer-relative "
            "evidence, never an investment recommendation or a causal claim.",
            "Concentration (HHI) is provider-count composition, NOT market share.",
            "Below n=5 rated peers, percentile and z-score are suppressed "
            "(insufficient sample).",
            "Metrics benchmark across four peer sets — national, state, "
            "locality (county; city for Home Health), and ownership type — "
            "each with its own peer count.",
            "Risk indicators are transparent, rule-based LEADING SIGNALS from "
            "the current snapshot — NOT trained models, probabilities, or "
            "forecasts (the data is single-snapshot; see the prediction-"
            "readiness audit). Each shows the components it is built from.",
            "A CCN can resolve to multiple verticals (hospital-based IRF/LTCH "
            "units share the HCRIS CCN) — the resolver shows all, never guesses.",
        ],
        limitations=["Benchmarks depend on source completeness; hospital "
                     "(HCRIS) financials are not peer-benchmarked in this "
                     "post-acute view — use the native hospital profile."],
        related_routes=["/diligence/hcris-xray", "/sector-intelligence",
                        "/nursing-homes", "/diligence"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── Diligence analyzer pages reformed in the honesty stack (PRs 4/5/8) ──
    # These carry a nuanced real/derived/illustrative data story; the Guide
    # must state it accurately so a deal team never reads an illustrative
    # model as live evidence.
    _ctx(
        "/payer-stress", "Payer Stress",
        short_description="Payer-mix stress model. When a target CCN is "
        "attached it seeds the mix from the target's REAL HCRIS payer-day "
        "split; with no/invalid CCN it falls back to illustrative slider "
        "defaults.",
        primary_purpose="Stress a target's revenue against shifts in "
        "Medicare / Medicaid / commercial payer mix.",
        common_questions=["How exposed is this target to a payer-mix shift?",
                         "Where does the starting mix come from?",
                         "Is this the target's real mix or a placeholder?"],
        inputs=["Optional target CCN / name (?ccn=, ?name=) resolved via "
                "HCRIS find_hospital; payer-mix sliders."],
        outputs=["A stressed revenue/margin view and the seeded payer mix, "
                 "with a header chip flipping to HCRIS / DERIVED when a CCN "
                 "resolves."],
        key_metrics=["Medicare / Medicaid / commercial day %", "Stressed "
                     "revenue delta"],
        data_sources=["HCRIS hospital cost reports (real) when a CCN is "
                      "attached — medicare_day_pct / medicaid_day_pct / "
                      "other_day_pct; illustrative slider defaults otherwise."],
        model_logic_summary="Seeds base_mcare / base_mcaid / base_comm from "
        "the resolved HCRIS day-mix, then applies the user's stress sliders. "
        "Commercial is approximated by the HCRIS 'other' bucket "
        "(commercial + self-pay). See payer_stress_page.py.",
        why_it_matters="Payer mix is a first-order driver of revenue "
        "durability and reimbursement risk.",
        diligence_use_cases=["Testing a target's sensitivity to Medicaid "
                            "expansion/contraction or a commercial-rate step-down."],
        interpretation_guidance=[
            "Real ONLY when a CCN resolves to a HCRIS hospital — otherwise the "
            "starting mix is an illustrative default, not the target's data.",
            "'Commercial' is the HCRIS 'other' day bucket (commercial + "
            "self-pay), a labeled proxy, not a pure commercial figure.",
        ],
        limitations=["HCRIS is hospital-level; non-hospital targets have no "
                     "CCN and stay illustrative.",
                     "Day-mix is a volume proxy, not a revenue-mix measure."],
        related_routes=["/diligence/hcris-xray", "/cost-structure",
                        "/debt-service"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/cost-structure", "Cost Structure",
        short_description="Operating-cost view. With a target CCN attached it "
        "shows REAL HCRIS opex/bed, opex/patient-day and operating margin; the "
        "COGS / SG&A / labor split stays illustrative-labeled.",
        primary_purpose="Frame a target's cost base and operating efficiency "
        "against real HCRIS aggregates where available.",
        common_questions=["What is this target's operating cost per bed / "
                         "patient-day?", "Which figures are real vs modeled?"],
        inputs=["Optional target CCN (?ccn=) resolved via HCRIS; the "
                "illustrative cost-split assumptions otherwise."],
        outputs=["A real HCRIS fact strip (opex/bed, opex/patient-day, "
                 "operating margin) with an HCRIS PUBLIC DATA / DERIVED header "
                 "when a CCN resolves; an illustrative COGS/SG&A/labor split."],
        key_metrics=["Opex per bed", "Opex per patient-day", "Operating margin"],
        data_sources=["HCRIS hospital cost reports (real opex / bed / "
                      "patient-day / margin) when a CCN is attached; "
                      "illustrative constants for the cost-category split."],
        model_logic_summary="Pulls real HCRIS opex aggregates for the resolved "
        "hospital; the COGS/SG&A/labor breakdown is an illustrative template, "
        "not derived from the target. See cost_structure_page.py.",
        why_it_matters="Cost efficiency vs peers is a core lever in the EBITDA "
        "bridge.",
        diligence_use_cases=["Comparing a target's opex intensity to peer "
                            "bands before underwriting cost-out theses."],
        interpretation_guidance=[
            "Only the opex aggregates + operating margin are real HCRIS; the "
            "COGS/SG&A/labor split is illustrative and labeled as such.",
            "Degrades to fully illustrative when no/invalid CCN.",
        ],
        limitations=["HCRIS opex is an aggregate; it does not decompose into "
                     "the cost categories shown in the split."],
        related_routes=["/diligence/hcris-xray", "/payer-stress",
                        "/debt-service"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/debt-service", "Debt Service",
        short_description="Debt-capacity view. With a target CCN attached it "
        "shows a REAL HCRIS operating-cash PROXY (operating margin × net "
        "patient revenue); actual debt balances and covenants are DATA "
        "REQUIRED (no public source).",
        primary_purpose="Frame a target's ability to service debt from "
        "operations, using a clearly-labeled HCRIS proxy.",
        common_questions=["Can this target cover debt service from "
                         "operations?", "Which numbers are real vs required?"],
        inputs=["Optional target CCN (?ccn=) resolved via HCRIS; user-entered "
                "debt terms (not publicly sourced)."],
        outputs=["A real HCRIS operating-cash proxy (labeled a proxy) and "
                 "DATA REQUIRED placeholders for debt balances, rate and "
                 "covenant tests."],
        key_metrics=["Operating-cash proxy (margin × NPR)", "DSCR (only once "
                     "real debt terms are supplied)"],
        data_sources=["HCRIS hospital cost reports (operating margin × net "
                      "patient revenue, a labeled operating-cash PROXY) when a "
                      "CCN is attached; debt balances / covenants are DATA "
                      "REQUIRED — no public source."],
        model_logic_summary="Approximates operating cash as operating_margin × "
        "NPR from HCRIS; it is NOT measured operating cash flow. Debt-side "
        "inputs must be supplied to compute a real DSCR. See debt_service_page.py.",
        why_it_matters="Debt serviceability gates leverage capacity and "
        "covenant headroom.",
        diligence_use_cases=["A first-pass read on operating-cash adequacy "
                            "before real debt terms are loaded."],
        interpretation_guidance=[
            "The operating-cash figure is a PROXY (margin × NPR), not measured "
            "cash flow — treat as directional.",
            "DSCR / covenant headroom are not real until actual debt terms are "
            "entered; the page labels these DATA REQUIRED.",
        ],
        limitations=["No public source for a target's debt stack; the page "
                     "cannot compute a real DSCR without user-entered terms."],
        related_routes=["/diligence/hcris-xray", "/cost-structure",
                        "/covenant-headroom"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/cms-apm", "CMS APM Tracker",
        short_description="CMS Innovation Center (CMMI) alternative-payment-"
        "model tracker. The program catalog / timelines are REAL public "
        "reference (curated); the portfolio-exposure and commercial-adjacency "
        "figures are an ILLUSTRATIVE worked example.",
        primary_purpose="Track which CMS APMs a target participates in and the "
        "policy calendar that moves its value-based revenue.",
        common_questions=["Which CMS APMs are active and when do they sunset?",
                         "Is the portfolio exposure shown my real data?"],
        inputs=["None required — renders the curated CMMI program catalog; "
                "attach a real deal to map its actual APM participation."],
        outputs=["A real CMMI program catalog (MSSP, ACO REACH, PCF, MCP, "
                 "BPCI-A, TEAM, …) with structures and sunset dates, plus an "
                 "explicitly-labeled ILLUSTRATIVE portfolio-exposure overlay."],
        key_metrics=["Active programs", "Lives covered", "Annual CMS payments",
                     "Avg savings rate"],
        data_sources=["CMS Innovation Center (CMMI) program descriptions — "
                      "public reference, curated approximations (not a live "
                      "CMS feed); the portfolio-exposure / commercial-adjacency "
                      "figures are illustrative, not the user's deals."],
        model_logic_summary="Surfaces a curated CMMI program catalog + policy "
        "calendar (public fact); the 'Project …' portfolio exposures are a "
        "worked example scoped under an Illustrative-template marker. See "
        "cms_apm_tracker.py / cms_apm_tracker_page.py.",
        why_it_matters="APM participation and sunsets directly move a target's "
        "value-based revenue and risk.",
        diligence_use_cases=["Mapping a target's value-based-care exposure and "
                            "the 2026–27 policy overhang."],
        interpretation_guidance=[
            "Program names, structures and timelines are public fact; the "
            "figures are curated approximations, not a live CMS pull.",
            "The portfolio-exposure / commercial-adjacency sections are a "
            "worked example — attach a real deal for actual participation.",
        ],
        limitations=["No live CMS feed wired yet; figures are curated.",
                     "Portfolio overlay is illustrative until a deal is attached."],
        related_routes=["/payer-rate-trends", "/diligence/checklist",
                        "/regulatory-calendar"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    # ── Deal Library (licensed Capital IQ company universe) ──
    _ctx(
        "/deal-library", "Deal Library",
        short_description="A benchmark universe of sponsor-backed healthcare "
        "companies ingested from user-licensed Capital IQ screening exports "
        "(~12.3k companies). Browse / sort / filter / search.",
        primary_purpose="Reference the sponsor-backed healthcare company "
        "universe for sourcing and sponsor intelligence — NOT your live "
        "Pipeline and NOT your Portfolio.",
        common_questions=["What companies has sponsor X backed?",
                         "Which healthcare companies are sponsor-owned in state Y?",
                         "Is this real or illustrative? Where's it from?"],
        inputs=["Filters via URL: ?sponsor= / ?state= / ?search=. Data loaded "
                "by scripts/ingest_deal_library_exports.py from licensed exports."],
        outputs=["Total count, source breakdown, per-field missingness, Top "
                 "sponsors/verticals/states, and a paged company table."],
        key_metrics=["Company count", "Sponsor coverage", "Per-field missingness"],
        data_sources=["Capital IQ company screening exports (LICENSED, "
                      "user-provided) — not scraped, not public. Distinct from "
                      "/library (the illustrative seed corpus)."],
        model_logic_summary="No model — a normalized directory. Sponsor is "
        "parsed from CapIQ Ownership Status; state from the address. See "
        "rcm_mc/data/deal_library.py + scripts/ingest_deal_library_exports.py.",
        why_it_matters="Maps which investors back which healthcare companies — "
        "a sourcing and sponsor-activity graph.",
        diligence_use_cases=["Sourcing targets by sponsor / vertical / geography; "
                            "mapping a sponsor's healthcare footprint."],
        interpretation_guidance=[
            "Financials are sparse (EV/EBITDA ~97% blank, revenue ~74% blank — "
            "private companies). Missing shows as '—', never 0.",
            "This is the broad SPONSOR-BACKED universe (VC / accelerator / REIT "
            "/ PE), not a PE-buyout-only set.",
        ],
        limitations=["Licensed export, not a live feed; reflects the export "
                     "date. The industry field is coarse (no fine verticals). "
                     "Most companies do not map to CMS provider registries."],
        related_routes=["/deal-library/sponsors", "/deal-library/comps", "/library"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/deal-library/sponsors", "Deal Library — Sponsors",
        short_description="Searchable index of every sponsor in the licensed "
        "universe (~4,900), ranked by # of healthcare companies backed, with "
        "the current/prior split. Each links to its filtered company list.",
        primary_purpose="See which investors are most active across the "
        "sponsor-backed healthcare universe.",
        common_questions=["Which sponsors back the most healthcare companies?",
                         "How many of sponsor X's are current vs prior?"],
        inputs=["?q= sponsor-name search; pagination via ?offset="],
        outputs=["Ranked sponsor table: companies / current / prior."],
        key_metrics=["Companies per sponsor", "Current vs prior ownership"],
        data_sources=["Aggregated from the Deal Library (licensed Capital IQ "
                      "exports); sponsor parsed from Ownership Status."],
        model_logic_summary="GROUP BY parsed sponsor over the company table. "
        "No model.",
        why_it_matters="Sponsor activity is the densest, most reliable signal "
        "in this dataset (~99% coverage).",
        diligence_use_cases=["Identifying active healthcare sponsors; building "
                            "a sponsor-relationship map for sourcing."],
        interpretation_guidance=[
            "Sponsors span VC, accelerators, healthcare REITs and PE — not a "
            "PE-buyout-only league table.",
        ],
        limitations=["Counts reflect the export's coverage, not the full market."],
        related_routes=["/deal-library", "/deal-library/comps"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/deal-library/comps", "Deal Library — Multiples",
        short_description="EV/Revenue and EV/EBITDA distributions over the small "
        "subset of the universe that discloses both (mostly public companies; "
        "~274 / ~135 of ~12.3k).",
        primary_purpose="A benchmark multiples distribution from disclosed "
        "financials — for sanity-checking, not a curated comp set or forecast.",
        common_questions=["What EV/Revenue / EV/EBITDA do disclosed healthcare "
                         "companies trade at?", "How big is the sample?"],
        inputs=["None; pagination via ?offset="],
        outputs=["P25/median/P75 + sample size for EV/Revenue & EV/EBITDA, and "
                 "a company table with computed multiples."],
        key_metrics=["EV/Revenue P25/median/P75", "EV/EBITDA P25/median/P75",
                     "Sample size n"],
        data_sources=["Deal Library companies disclosing EV + a positive "
                      "denominator (licensed Capital IQ exports)."],
        model_logic_summary="EV/Revenue = EV / revenue; EV/EBITDA = EV / EBITDA, "
        "computed only where both are present and the denominator is positive. "
        "Percentiles over that subset.",
        why_it_matters="The only financial-multiple view this export honestly "
        "supports.",
        diligence_use_cases=["Sanity-checking a target's multiple against "
                            "disclosed-financial healthcare companies."],
        interpretation_guidance=[
            "Small, mostly-public sample (~2% of the universe) — directional, "
            "not a governed comp set.",
            "Missing financials are EXCLUDED, never treated as 0; negative "
            "EBITDA is excluded (no fake 0x).",
            "This is a benchmark distribution, NOT a prediction.",
        ],
        limitations=["~98% of companies disclose no usable financials, so the "
                     "sample is small and skews public/large-cap."],
        related_routes=["/deal-library", "/comparables", "/market-rates"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/market-intel/geo", "Market Intelligence — Geographic",
        short_description="Geographic market intelligence — ranks/scores US "
        "markets by senior demand and real CMS supply/consolidation signals, "
        "from licensed SimplyAnalytics exports plus public CMS data.",
        primary_purpose="Frame whether a geographic market is attractive "
        "(senior demand, provider supply, consolidation velocity) before "
        "screening targets in it — then validate with CMS/HCRIS.",
        common_questions=[
            "Which states have the highest senior (65+) demand?",
            "Is this market over- or under-supplied with providers?",
            "How active is nursing-home / hospital consolidation here?",
            "Is this market data or provider-specific?",
        ],
        inputs=["?var= (variable selector); /market-intel/geo/<FIPS> for a "
                "state profile."],
        outputs=["State choropleth + ranked markets by the selected variable; "
                 "per-state profile with demographic, provider-supply, and "
                 "consolidation KPIs + a documented partial market score."],
        key_metrics=["% Age 65+ (national percentile)", "Provider supply "
                     "(CMS FFS enrollment)", "SNF/Hospital ownership-change "
                     "counts", "Partial market score"],
        data_sources=["Licensed SimplyAnalytics exports (% Age 65+, FIPS-keyed); "
                      "CMS FFS Provider Enrollment (supply); CMS SNF/Hospital "
                      "Change-of-Ownership (consolidation)."],
        model_logic_summary="Real values only; national percentiles computed "
        "over states with data. Market score = mean of AVAILABLE percentile "
        "components; un-exported components are flagged EXPORT REQUIRED, never "
        "invented.",
        why_it_matters="Turns demographic + supply + M&A data into a real, "
        "honest market-attractiveness read for sourcing and diligence.",
        diligence_use_cases=["Rank markets by senior demand; spot over/under-"
                            "supply; gauge consolidation velocity by state."],
        interpretation_guidance=[
            "Market/area context — NOT provider-specific; combine with "
            "CMS/HCRIS/provider data before a decision.",
            "Screenshots are design references only; only variables with a "
            "real export are shown (rest are EXPORT REQUIRED).",
            "Consolidation counts are a signal, NOT a PE-specific flag.",
        ],
        limitations=["Only % Age 65+ is exported so far (state level); income/"
                     "insurance/uninsured and county detail are export-required. "
                     "Provider supply is FFS-Medicare-enrolled only."],
        related_routes=["/target-screener", "/industry", "/market-data/map"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/industry", "Industry Intelligence",
        short_description="Licensed-IBISWorld-derived industry intelligence for "
        "five healthcare industries, connected to PEdesk's real CMS/HCRIS data.",
        primary_purpose="Ground a deal's sector thesis in licensed industry "
        "context (market size, mix, drivers, cost structure), then validate it "
        "against real public/provider data.",
        common_questions=[
            "What does the industry report say about growth and margins?",
            "Which public CMS datasets can validate this thesis?",
            "Which metrics are report-derived vs provider-specific?",
            "What should I ask management about this sector?",
        ],
        inputs=["/industry/<slug> for a dossier; /industry/<slug>/brief for a "
                "PEdesk-generated brief."],
        outputs=["Per-industry at-a-glance metrics, segment mix, drivers, "
                 "cost-structure benchmarks, definition, diligence questions, "
                 "and a Public Data Connections panel to real CMS/HCRIS surfaces."],
        key_metrics=["Industry revenue / profit margin / employment",
                     "Segment revenue share", "Cost structure (% of revenue)"],
        data_sources=["Licensed IBISWorld reports (structured derived facts; "
                      "raw PDFs never committed/served)."],
        model_logic_summary="Structured extraction (metrics/segments/drivers/"
        "benchmarks), non-verbatim. Forecasts are report-derived. The brief "
        "synthesizes report facts with the CMS/HCRIS validation layer.",
        why_it_matters="Connects licensed industry context to real provider "
        "data so the sector thesis can be confirmed or challenged.",
        diligence_use_cases=["Frame a sector's size/growth/margins; build the "
                            "management-question and data-request list."],
        interpretation_guidance=[
            "Report-derived industry context — NOT provider-specific unless "
            "joined to CMS/HCRIS/user data.",
            "Forecasts are report-derived, not PEdesk predictions.",
            "Industry context is not a final investment conclusion.",
        ],
        limitations=["Five industries only (62 / 621111 / 621112 / 62149 / "
                     "622110); derived facts, not the full reports."],
        related_routes=["/market-intel/geo", "/diligence/hcris-xray", "/research"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    # ── Diligence calculators converted with real CMS/FDA/CIVHC anchors ──
    _ctx(
        "/physician-productivity", "Physician Productivity",
        short_description="An input-driven productivity calculator (wRVU / panel "
        "vs specialty benchmark ranges), anchored to real CMS MIPS physician-"
        "quality and HRSA workforce-shortage context.",
        primary_purpose="Gauge a physician group's productivity against "
        "representative benchmarks, framed by real physician-quality and "
        "shortage data.",
        data_sources=["Representative MGMA/AMGA-style benchmark ranges "
                      "(illustrative); real CMS MIPS distribution; real HRSA HPSA."],
        interpretation_guidance=[
            "Computes off YOUR inputs; benchmark ranges are illustrative.",
            "MIPS/HRSA panels are national/market context — NOT this group's "
            "providers and NOT a payment figure.",
        ],
        limitations=["Benchmark ranges are representative, not licensed MGMA."],
        related_routes=["/quality-scorecard", "/clinical-outcomes", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/provider-retention", "Provider Retention",
        short_description="A retention/churn calculator on your inputs, anchored "
        "to the real CMS Care Compare nurse-staff turnover benchmark.",
        primary_purpose="Frame provider/staff churn risk and cost, against a "
        "real sector turnover benchmark.",
        data_sources=["Representative role-level churn assumptions (illustrative) "
                      "+ real CMS nurse-staff turnover (median ~45%)."],
        interpretation_guidance=[
            "Calculator on your inputs; the at-risk watchlist is illustrative "
            "scaffold — connect an HR roster for real individuals.",
            "CMS turnover is a sector benchmark, NOT this deal's roster.",
        ],
        limitations=["Deal-specific retention requires the target's HR roster."],
        related_routes=["/physician-productivity", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/quality-scorecard", "Quality Scorecard",
        short_description="A quality-adjusted value calculator on your inputs, "
        "anchored to a sector-aware real CMS benchmark (MIPS for physician "
        "sectors, Care Compare 5-star for nursing).",
        primary_purpose="Frame quality posture and EV uplift against a real "
        "CMS quality distribution.",
        data_sources=["Illustrative quality model + real CMS MIPS (physician) / "
                      "Care Compare 5-star (nursing) distribution."],
        interpretation_guidance=[
            "Calculator on your inputs; benchmark is real CMS sector data, NOT "
            "this deal's score.",
        ],
        limitations=["Benchmark picked by sector; deal-specific quality needs "
                     "the target's measure data."],
        related_routes=["/clinical-outcomes", "/physician-productivity"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/clinical-outcomes", "Clinical Outcomes",
        short_description="An outcomes/EV calculator on your inputs, anchored to "
        "the real CMS Care Compare quality-measure distribution.",
        primary_purpose="Frame clinical-quality value against a real CMS "
        "quality-measure benchmark.",
        data_sources=["Illustrative outcomes model + real CMS quality-measure "
                      "rating distribution."],
        interpretation_guidance=["Calculator on your inputs; CMS benchmark is "
                                "sector context, not this deal's outcomes."],
        limitations=["Deal-specific outcomes need the target's measure data."],
        related_routes=["/quality-scorecard", "/physician-productivity"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/regulatory-risk", "Regulatory Risk",
        short_description="A regulatory-risk calculator on your inputs; for "
        "nursing/post-acute it shows the real CMS enforcement base rate.",
        primary_purpose="Frame regulatory exposure, anchored (for SNF) to real "
        "CMS enforcement data.",
        data_sources=["Illustrative risk model + real CMS SNF enforcement "
                      "(45% fined, $467M total)."],
        interpretation_guidance=["Calculator on your inputs; CMS enforcement is "
                                "a sector base rate, not this deal's exposure."],
        limitations=["Enforcement anchor is nursing-sector only."],
        related_routes=["/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/supply-chain", "Supply Chain",
        short_description="A supply-savings calculator on your inputs, anchored "
        "to the real FDA drug-shortage signal.",
        primary_purpose="Frame supply-chain savings/risk against real active "
        "drug shortages.",
        data_sources=["Illustrative savings model + real FDA drug shortages "
                      "(1,156 active across 58 categories)."],
        interpretation_guidance=["Calculator on your inputs; FDA shortage is a "
                                "national product-level signal, not this deal's book."],
        limitations=["Shortage data is product-level, not provider-specific."],
        related_routes=["/drug-shortage", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/payer-shift", "Payer Shift",
        short_description="A payer-mix economics calculator on your inputs, "
        "anchored to the real CIVHC Colorado payer-cost trend.",
        primary_purpose="Frame payer-mix shift economics against a real "
        "all-payer cost trend.",
        data_sources=["Illustrative shift model + real CIVHC CO payer-cost "
                      "trend by payer type."],
        interpretation_guidance=["Calculator on your inputs; CIVHC is Colorado "
                                "all-payer market context, NOT this deal's mix."],
        limitations=["CIVHC anchor is Colorado-only."],
        related_routes=["/payer-rate-trends", "/cost-structure"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/ma-contracts", "MA Contracts",
        short_description="An MA-contract economics calculator on your inputs, "
        "anchored to the real CMS MA enrollment market size.",
        primary_purpose="Frame MA contract economics against the real MA market.",
        data_sources=["Illustrative PMPM/risk model + real CMS MA Geographic "
                      "Variation enrollment (29.7M across 53 states)."],
        interpretation_guidance=["Calculator on your inputs; MA enrollment is "
                                "market context, not this deal's contract."],
        limitations=["No Star Ratings / risk scores in the anchor (enrollment "
                     "+ demographics only)."],
        related_routes=["/risk-adjustment", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/risk-adjustment", "Risk Adjustment",
        short_description="An illustrative RAF model (fixed, not input-driven) "
        "with a real CMS MA population-context panel (dual-eligible/age mix).",
        primary_purpose="Frame risk-adjustment intensity, with the real "
        "population drivers shown as context.",
        data_sources=["Illustrative RAF model + real CMS MA dual-eligible / age "
                      "population mix by state."],
        interpretation_guidance=[
            "The RAF figures are illustrative (fixed model); the MA population "
            "panel is real CMS context — NOT a Star Rating, NOT a risk score, "
            "NOT this deal.",
        ],
        limitations=["RAF model is illustrative; real coding intensity needs "
                     "the target's encounter data."],
        related_routes=["/ma-contracts", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    # ── LIVE real-data pages (public sources) ───────────────────────────
    _ctx(
        "/drug-shortage", "Drug Shortage",
        short_description="Live national drug-shortage tracker from FDA/openFDA "
        "— current active shortages by therapeutic category.",
        primary_purpose="Surface real drug-shortage exposure for pharmacy-"
        "dependent operations and supply-chain risk framing.",
        data_sources=["openFDA drug shortages (committed snapshot; no runtime "
                      "network)."],
        key_metrics=["Active shortages", "Therapeutic categories",
                     "Resolved count"],
        interpretation_guidance=[
            "Real FDA data; product-level and national — NOT provider-specific.",
            "Availability field is ~31% blank (preserved, not zero-filled).",
        ],
        limitations=["Product-level; build-time snapshot refreshed on re-ingest."],
        related_routes=["/supply-chain", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/payer-rate-trends", "Payer Rate Trends",
        short_description="Live Colorado payer cost trend (CIVHC / CO All-Payer "
        "Claims) — per-person-per-year spend by payer type over time.",
        primary_purpose="Show how payer economics actually shifted in a real "
        "all-payer market, as context for payer-mix diligence.",
        data_sources=["CIVHC CO APCD public cost-of-care (committed snapshot)."],
        key_metrics=["PPPY spend by payer type", "% change over years"],
        interpretation_guidance=[
            "Real Colorado all-payer market data — NOT this deal's payer mix "
            "and NOT national.",
            "Missing values preserved as NaN, never zero.",
        ],
        limitations=["Colorado-only; all-payer aggregate, not provider-level."],
        related_routes=["/payer-shift", "/cost-structure", "/ref-pricing"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/ref-pricing", "Reference-Based Pricing",
        short_description="Live Colorado provider reimbursement as a % of "
        "Medicare (CIVHC / CO APCD) — by organization, county, claim type.",
        primary_purpose="Show real commercial-vs-Medicare reimbursement ratios "
        "for benchmarking provider pricing posture.",
        data_sources=["CIVHC CO Medicare Reference-Based Pricing (committed "
                      "snapshot)."],
        key_metrics=["Hospital % of Medicare", "Claims", "Payer min/median/max"],
        interpretation_guidance=[
            "Real Colorado provider-level data (resolvable to CCN by name); "
            "% of Medicare = commercial/Medicare ratio.",
            "CO-only; ~1% missing on URF/payer fields (preserved).",
        ],
        limitations=["Colorado-only; provider names resolve to CCN imperfectly."],
        related_routes=["/payer-rate-trends", "/cost-structure", "/payer-stress"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── Core deal/portfolio workflow pages (operate on the live deal store) ──
    _ctx(
        "/pipeline", "Deal Pipeline",
        short_description="The deal pipeline — deals by stage (sourcing → LOI → "
        "diligence → IC → close) on the live deal store.",
        primary_purpose="Track and move deals through the funnel; saved searches "
        "re-run against the corpus.",
        data_sources=["Live SQLite deal store (the user's real deals)."],
        interpretation_guidance=["Operates on YOUR tracked deals; empty/— means "
                                "no deals at that stage, not zero value."],
        related_routes=["/deal-pipeline", "/portfolio", "/diligence/checklist"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/diligence/checklist", "Diligence Checklist",
        short_description="Per-deal diligence checklist — items, status, owners.",
        primary_purpose="Track diligence completeness for a deal.",
        data_sources=["Live deal store (per-deal checklist items)."],
        interpretation_guidance=["Per-deal workflow state; reflects what's been "
                                "entered for the selected deal."],
        related_routes=["/diligence-checklist", "/diligence/questions", "/diligence/ic-packet"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/diligence/ingest", "Diligence Ingest",
        short_description="Ingest a deal's documents/financials into the deal "
        "store for analysis.",
        primary_purpose="Load deal-specific data (the user's own) for diligence.",
        data_sources=["User-uploaded deal data → live deal store."],
        interpretation_guidance=["USER DATA REQUIRED — outputs reflect what you "
                                "ingest for the deal."],
        related_routes=["/diligence/checklist", "/import", "/new-deal/upload"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    _ctx(
        "/diligence/questions", "Diligence Questions",
        short_description="Generated + tracked diligence questions for a deal.",
        primary_purpose="Build and manage the management-question / data-request "
        "list for a deal.",
        data_sources=["Live deal store + packet-derived question generation."],
        interpretation_guidance=["Per-deal; combine with real CMS/HCRIS data "
                                "when answering."],
        related_routes=["/diligence/checklist", "/diligence/ic-packet"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/diligence/ic-packet", "IC Packet Assembler",
        short_description="One-click investment-committee packet for a deal from "
        "the live analysis packet.",
        primary_purpose="Assemble an IC-ready memo/packet for a tracked deal.",
        data_sources=["Live deal store + the deal's analysis packet."],
        interpretation_guidance=["Per-deal; honest empty states where inputs "
                                "are missing."],
        related_routes=["/diligence/questions", "/ic-memo", "/exports"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/watchlist", "Watchlist",
        short_description="Starred/watched deals for quick monitoring.",
        primary_purpose="Track a focused subset of deals.",
        data_sources=["Live deal store (watchlist flags)."],
        interpretation_guidance=["Operates on YOUR watched deals."],
        related_routes=["/pipeline", "/alerts", "/portfolio/monitor"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/escalations", "Escalations",
        short_description="Escalated alerts/issues across the portfolio.",
        primary_purpose="Surface deals/issues that need partner attention.",
        data_sources=["Live deal store + alerts lifecycle."],
        interpretation_guidance=["Reflects current alert/escalation state of "
                                "tracked deals."],
        related_routes=["/alerts", "/portfolio/monitor", "/watchlist"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    # (/portfolio/monitor already documented earlier with metric/data-source
    #  links — no duplicate here.)
    # ── More live-deal-store workflow pages (Queue 6, batch 2) ──
    _ctx(
        "/cohorts", "Cohorts",
        short_description="Group deals into cohorts for slicing and comparison.",
        primary_purpose="Define and review deal cohorts across the book.",
        data_sources=["Live deal store (cohort membership)."],
        interpretation_guidance=["Operates on YOUR tracked deals."],
        related_routes=["/pipeline", "/portfolio", "/owners"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/deadlines", "Deadlines",
        short_description="Deal deadlines and key dates across the portfolio.",
        primary_purpose="Track upcoming deal/portfolio deadlines.",
        data_sources=["Live deal store (deadlines)."],
        interpretation_guidance=["Reflects deadlines entered for your deals; "
                                "empty means none recorded."],
        related_routes=["/alerts", "/pipeline", "/day-one"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/owners", "Owners",
        short_description="Deal owner assignments — who owns which deal.",
        primary_purpose="Manage deal ownership across the team.",
        data_sources=["Live deal store (owner assignments)."],
        interpretation_guidance=["Operates on YOUR tracked deals/team."],
        related_routes=["/pipeline", "/cohorts", "/my/AT"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/notes", "Notes",
        short_description="Deal notes (searchable, taggable) on the live store.",
        primary_purpose="Capture and search deal notes.",
        data_sources=["Live deal store (notes; soft-deleted rows filtered)."],
        interpretation_guidance=["Your entered notes; search/tag filter applies."],
        related_routes=["/pipeline", "/research", "/cohorts"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/engagements", "Engagements",
        short_description="Consulting/operating engagements tracked per deal.",
        primary_purpose="Track engagement work tied to deals.",
        data_sources=["Live deal store (engagement tables)."],
        interpretation_guidance=["Per-deal engagement records you've entered."],
        related_routes=["/engagements/create", "/portfolio", "/initiatives"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/exports", "Exports",
        short_description="Generated exports (LP updates, CSVs, packets).",
        primary_purpose="Produce partner/LP-ready exports from live data.",
        data_sources=["Live deal store + generated export artifacts."],
        interpretation_guidance=["Exports reflect current live data at "
                                "generation time."],
        related_routes=["/lp-update", "/exports/lp-update", "/diligence/ic-packet"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    # ── Analytic calculators / corpus analytics (Guide-coverage batch) ──
    _ctx(
        "/aco-economics", "ACO Economics",
        short_description="ACO shared-savings economics calculator on your inputs.",
        primary_purpose="Model ACO/value-based shared-savings economics for a deal.",
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs; defaults are "
                                "illustrative, not a specific ACO's results."],
        related_routes=["/cms-apm", "/risk-adjustment"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/acq-timing", "Acquisition Timing",
        short_description="Acquisition-timing model on your inputs.",
        primary_purpose="Frame timing trade-offs for an acquisition.",
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs; illustrative defaults."],
        related_routes=["/entry-multiple", "/hold-optimizer"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/bolton-analyzer", "Bolt-on Analyzer",
        short_description="Bolt-on / roll-up accretion calculator on your inputs.",
        primary_purpose="Model accretion/dilution from a bolt-on acquisition.",
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs; illustrative defaults, "
                                "not a specific deal."],
        related_routes=["/rollup-economics", "/entry-multiple"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/cap-structure", "Capital Structure",
        short_description="Capital-structure calculator on your inputs.",
        primary_purpose="Model debt/equity structure and leverage for a deal.",
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs."],
        related_routes=["/debt-service", "/covenant-headroom"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/capital-efficiency", "Capital Efficiency",
        short_description="Capital-efficiency calculator on your inputs.",
        primary_purpose="Frame capital efficiency / returns on invested capital.",
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs."],
        related_routes=["/cap-structure", "/reinvestment"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/covenant-headroom", "Covenant Headroom",
        short_description="Covenant-headroom calculator on your inputs.",
        primary_purpose="Model covenant cushion under your assumptions.",
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs; not a live covenant feed."],
        related_routes=["/covenant-monitor", "/debt-service", "/cap-structure"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/covenant-monitor", "Covenant Monitor",
        short_description="Covenant-monitoring calculator on your inputs.",
        primary_purpose="Track covenant posture under your assumptions.",
        data_sources=["Calculator: your inputs (+ live deal data where attached)."],
        interpretation_guidance=["Reflects your inputs / attached deal data."],
        related_routes=["/covenant-headroom", "/debt-service"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/deal-quality", "Deal Quality Scorer",
        short_description="Quality grade across the illustrative seed-deal corpus.",
        primary_purpose="Benchmark a deal's data-completeness/credibility grade "
        "against the corpus.",
        data_sources=["Bundled ILLUSTRATIVE seed-deal corpus (labeled)."],
        interpretation_guidance=["Scores the illustrative corpus — not this "
                                "market's real deals; use as a structural benchmark."],
        related_routes=["/deal-risk-scores", "/corpus-dashboard"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
    _ctx(
        "/deal-risk-scores", "Deal Risk Scores",
        short_description="Risk scores across the illustrative seed-deal corpus.",
        primary_purpose="Benchmark deal risk dimensions against the corpus.",
        data_sources=["Bundled ILLUSTRATIVE seed-deal corpus (labeled)."],
        interpretation_guidance=["Illustrative corpus, not real realized deals."],
        related_routes=["/deal-quality", "/corpus-dashboard"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
    _ctx(
        "/deal-postmortem", "Deal Postmortem",
        short_description="Post-mortem analytics over the illustrative seed-deal corpus.",
        primary_purpose="Frame lessons/attribution from corpus deal outcomes.",
        data_sources=["Bundled ILLUSTRATIVE seed-deal corpus (labeled)."],
        interpretation_guidance=["Illustrative corpus — directional, not real outcomes."],
        related_routes=["/fund-learning", "/deal-quality"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),

    # ── Pages converted RED→NAVY this session: input-driven model/illustrative
    #    corpus + a real LIVE public-data anchor panel (honest, labeled). ──
    _ctx(
        "/provider-network", "Provider Network Intelligence",
        short_description="Payer-mix HHI / network-concentration calculator on your "
        "inputs, anchored to the real CMS FFS provider-supply universe.",
        primary_purpose="Gauge network payer concentration and the real provider-"
        "supply backdrop a deal acquires into.",
        data_sources=["Illustrative corpus peers/regime stats (labeled) + real CMS "
                      "FFS provider enrollment (2.98M)."],
        interpretation_guidance=["HHI/regime compute off YOUR payer mix.",
                                 "Supply panel is the market backdrop, NOT this deal's roster."],
        limitations=["Peer/regime comps are illustrative seed-corpus."],
        related_routes=["/workforce-planning", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/msa-concentration", "MSA Provider Market Concentration",
        short_description="MSA-level HHI/CR3/CR5 framework (illustrative MSA detail) "
        "anchored to real CMS change-of-ownership consolidation by state.",
        primary_purpose="Frame market concentration / rollup whitespace against real "
        "observed consolidation activity.",
        data_sources=["Illustrative MSA HHI/operator detail (labeled) + real CMS CHOW "
                      "(5,141 SNF + 755 hospital)."],
        interpretation_guidance=["MSA tables are the structural lens (illustrative).",
                                 "CHOW panel is real observed consolidation by state."],
        limitations=["MSA-level HHI/operators are illustrative, not this market."],
        related_routes=["/concentration-risk", "/competitive-intel", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/payer-concentration", "Payer Concentration Tracker",
        short_description="CR1/CR3/CR5/HHI payer-concentration calculator on your "
        "revenue + top-payer inputs, anchored to real CMS MA enrollment.",
        primary_purpose="Frame payer concentration and the real MA-market backdrop.",
        data_sources=["Illustrative payer roster/renewals/denials (labeled) + real "
                      "CMS MA geographic enrollment (29.7M)."],
        interpretation_guidance=["Concentration metrics compute off YOUR inputs.",
                                 "MA panel is the observed market, NOT this deal's roster."],
        limitations=["Payer roster/renewal/denial detail is illustrative."],
        related_routes=["/payer-contracts", "/payer-rate-trends", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/gpo-supply", "GPO / Supply Chain Savings Tracker",
        short_description="Supply-chain savings model (illustrative) anchored to the "
        "real CMS Open Payments device/pharma vendor landscape.",
        primary_purpose="Frame GPO savings against the real manufacturer-vendor scale.",
        data_sources=["Illustrative GPO savings/contracts/bulk-buys (labeled) + real "
                      "CMS Open Payments ($3.31bn, top vendors)."],
        interpretation_guidance=["Savings/contract figures are illustrative scaffold.",
                                 "Open Payments panel is real industry vendor scale."],
        limitations=["Deal GPO savings require the target's actual spend data."],
        related_routes=["/cost-structure"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/medicaid-unwinding", "Medicaid Unwinding Tracker",
        short_description="Medicaid redetermination impact model (illustrative) "
        "anchored to the real CMS dual-eligible population by state.",
        primary_purpose="Frame disenrollment / coverage-shift exposure against the "
        "real at-risk dual-eligible cohort.",
        data_sources=["Illustrative disenrollment/coverage-shift/bad-debt (labeled) + "
                      "real CMS dual-eligible share by state."],
        interpretation_guidance=["Deal-level impact figures are illustrative.",
                                 "Dual-eligible panel is the real at-risk population."],
        limitations=["Deal exposure requires the target's real payer mix."],
        related_routes=["/payer-concentration", "/risk-adjustment"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/payer-contracts", "Payer Contracts",
        short_description="Payer contract-book / negotiation model (illustrative) "
        "anchored to the real CIVHC commercial-vs-Medicare rate benchmark.",
        primary_purpose="Frame contract rates against the real commercial-%-of-"
        "Medicare benchmark contracts negotiate against.",
        data_sources=["Illustrative contract book/negotiations/escalators (labeled) + "
                      "real CIVHC / CO APCD reference-based pricing."],
        interpretation_guidance=["Contract book is illustrative scaffold.",
                                 "CIVHC ratio is a real Colorado rate benchmark."],
        limitations=["Deal contracts require the target's actual rate sheets."],
        related_routes=["/payer-concentration", "/ref-pricing", "/payer-rate-trends"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/health-equity", "Health Equity / SDOH Scorecard",
        short_description="HEI / Star-bonus model (illustrative) anchored to real CDC "
        "PLACES full-population social-determinants prevalence.",
        primary_purpose="Frame health-equity posture against real SDOH burden.",
        data_sources=["Illustrative HEI/Star scorecard (labeled) + real CDC PLACES SDOH "
                      "(uninsured, food/transport insecurity)."],
        interpretation_guidance=["HEI/Star figures are illustrative, scaled to inputs.",
                                 "PLACES panel is real full-population SDOH (not patients)."],
        limitations=["Model-based estimates; area-level, not this deal's panel."],
        related_routes=["/risk-adjustment", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/telehealth-econ", "Telehealth Economics Analyzer",
        short_description="Telehealth visit-economics model (illustrative) anchored to "
        "real CDC PLACES access barriers (transportation, uninsured).",
        primary_purpose="Frame telehealth demand against real access-barrier prevalence.",
        data_sources=["Illustrative visit P&L / parity / productivity (labeled) + real "
                      "CDC PLACES access barriers."],
        interpretation_guidance=["Visit economics are illustrative.",
                                 "PLACES panel is real access-barrier prevalence by state."],
        limitations=["Model-based estimates; area-level."],
        related_routes=["/health-equity"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/patient-experience", "Patient Experience",
        short_description="NPS/complaint/service-recovery model (illustrative) anchored "
        "to the real CMS HCAHPS patient-survey top-box by state.",
        primary_purpose="Frame patient-experience posture against the real HCAHPS "
        "benchmark.",
        data_sources=["Illustrative NPS/complaint model (labeled) + real CMS HCAHPS "
                      "state top-box (overall 9-10, would-recommend)."],
        interpretation_guidance=["NPS/complaint figures are illustrative.",
                                 "HCAHPS panel is the real survey benchmark (not this facility)."],
        limitations=["State-level HCAHPS; national figure = state mean."],
        related_routes=["/quality-scorecard", "/clinical-outcomes"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/locum-tracker", "Locum / Contract-Labor Tracker",
        short_description="Locum spend/coverage model (illustrative) anchored to real "
        "HRSA Health Professional Shortage Areas — the locum-demand driver.",
        primary_purpose="Frame locum/temp-staffing demand against real shortage-area data.",
        data_sources=["Illustrative locum spend/coverage/rates (labeled) + real HRSA "
                      "HPSA (7,635 designated PC shortage areas)."],
        interpretation_guidance=["Locum figures are illustrative.",
                                 "HPSA panel is real shortage-area designations by state."],
        limitations=["Deal locum spend requires the target's actuals."],
        related_routes=["/workforce-planning", "/workforce-retention"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/workforce-retention", "Workforce Turnover / Retention Tracker",
        short_description="Turnover/engagement/retention model (illustrative) anchored "
        "to real HRSA shortage areas — the retention-pressure backdrop.",
        primary_purpose="Frame retention difficulty against real labor-shortage data.",
        data_sources=["Illustrative turnover/engagement/programs (labeled) + real HRSA "
                      "HPSA shortage designations."],
        interpretation_guidance=["Turnover/engagement figures are illustrative.",
                                 "HPSA panel is real shortage data (deeper shortage = harder retention)."],
        limitations=["Deal turnover requires the target's HR roster."],
        related_routes=["/locum-tracker", "/workforce-planning"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/antitrust-screener", "Anti-Trust Screener",
        short_description="HHI / HSR / market-overlap screen computed off your deal-"
        "size input, anchored to real CMS change-of-ownership consolidation.",
        primary_purpose="Frame antitrust/HSR risk against real observed consolidation.",
        data_sources=["Illustrative HHI/HSR/overlap/precedent model (labeled) + real "
                      "CMS CHOW consolidation activity."],
        interpretation_guidance=["HHI/HSR/overlap compute off your deal-size input.",
                                 "CHOW panel is the real serial-acquisition backdrop FTC scrutinizes."],
        limitations=["Market-overlap specifics are illustrative."],
        related_routes=["/concentration-risk", "/msa-concentration", "/competitive-intel"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/cin-analyzer", "Clinically Integrated Network Analyzer",
        short_description="CIN shared-savings/quality model on your inputs, anchored "
        "to the real CMS MSSP ACO landscape.",
        primary_purpose="Frame a CIN's value-based posture against the real ACO landscape.",
        data_sources=["Illustrative CIN roster/contracts/quality (labeled) + real CMS "
                      "MSSP ACO landscape (511 ACOs, 15,293 orgs)."],
        interpretation_guidance=["CIN roster/contract figures are illustrative.",
                                 "MSSP panel is the real ACO/value-based benchmark."],
        limitations=["Deal CIN data requires the target's network roster."],
        related_routes=["/aco-economics", "/quality-scorecard"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/nsa-tracker", "No Surprises Act / OON Tracker",
        short_description="OON volume / balance-bill / IDR model (illustrative) "
        "anchored to the real CIVHC commercial-vs-Medicare OON/QPA benchmark.",
        primary_purpose="Frame NSA OON/IDR exposure against the real rate benchmark "
        "disputes reference.",
        data_sources=["Illustrative OON volume/balance-bill/IDR (labeled) + real CIVHC "
                      "commercial-%-of-Medicare distribution."],
        interpretation_guidance=["OON/IDR figures are illustrative.",
                                 "CIVHC ratio is the real OON/QPA rate benchmark (Colorado APCD)."],
        limitations=["Deal OON exposure requires the target's claims."],
        related_routes=["/payer-contracts", "/ref-pricing"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),

    # ── Workflow + Tools pages: real user-DB / system / catalog surfaces ──
    _ctx(
        "/activity", "Activity Feed",
        category=PageContextCategory.HOME_OPERATIONS,
        short_description="A chronological feed of YOUR real workspace activity — "
        "deals created, notes, stage changes, alerts, escalations.",
        primary_purpose="See what's changed across your deals/portfolio recently.",
        data_sources=["Your real workspace audit/event log (SQLite)."],
        interpretation_guidance=["This is your own real activity, not market/corpus data."],
        related_routes=["/app", "/alerts", "/escalations"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/deal-pipeline", "Deal Pipeline",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Your real deal pipeline by stage (alias of /pipeline).",
        primary_purpose="Track your actual opportunities through the deal funnel.",
        data_sources=["Your real deal records (SQLite)."],
        interpretation_guidance=["YOUR deals, not the market or seed corpus."],
        related_routes=["/pipeline", "/app", "/deals"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/deals", "Deals",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="The list/management view of YOUR real deals.",
        primary_purpose="Browse, filter, and open your actual deal records.",
        data_sources=["Your real deal records (SQLite)."],
        interpretation_guidance=["YOUR deals — real workspace data."],
        related_routes=["/pipeline", "/deal-search", "/app"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/deal-search", "Deal Search",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Search across YOUR real deals by name, stage, sector, owner.",
        primary_purpose="Quickly locate a specific deal in your workspace.",
        data_sources=["Your real deal records (SQLite)."],
        interpretation_guidance=["Searches your own deals, not the market/corpus."],
        related_routes=["/deals", "/pipeline", "/global-search"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/initiatives", "Initiatives",
        category=PageContextCategory.PORTFOLIO_LP,
        short_description="Value-creation initiatives tracked against YOUR real deals/"
        "portfolio companies.",
        primary_purpose="Track operating initiatives and their progress per company.",
        data_sources=["Your real initiative records (SQLite)."],
        interpretation_guidance=["Your own initiatives — real workspace data."],
        related_routes=["/portfolio", "/value-creation-plan", "/app"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/pipeline/bridge", "Pipeline Bridge",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Jump from a pipeline deal into its EBITDA bridge / analysis.",
        primary_purpose="Connect a pipeline opportunity to its value-creation bridge.",
        data_sources=["Your real deal records + the bridge model on your inputs."],
        interpretation_guidance=["Operates on YOUR deal; bridge math is model output."],
        related_routes=["/pipeline", "/ebitda-bridge/", "/diligence/bridge-audit"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/screening", "Screening",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Screen targets against your criteria (alias surface of the "
        "screening workflow).",
        primary_purpose="Filter the candidate universe to a prioritized shortlist.",
        data_sources=["Your real candidate/target records + screening criteria."],
        interpretation_guidance=["Operates on your workspace candidates."],
        related_routes=["/screening/dashboard", "/target-screener", "/pipeline"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/screening/dashboard", "Screening Dashboard",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Dashboard view of your screening funnel and shortlist.",
        primary_purpose="Monitor screening progress and surface top candidates.",
        data_sources=["Your real candidate/target records + screening criteria."],
        interpretation_guidance=["Your workspace screening, not the market/corpus."],
        related_routes=["/screening", "/target-screener", "/pipeline"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/data-intelligence", "Data Intelligence",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="Catalog/overview of the real public data sources wired into "
        "PEdesk (CMS/HCRIS/CDC/HRSA/CIVHC, etc.) and what they power.",
        primary_purpose="Understand which real datasets back the analytics and where.",
        data_sources=["The data-source registry (real public datasets)."],
        interpretation_guidance=["A catalog of real sources — see each source's card for detail."],
        related_routes=["/cms-sources", "/data", "/data/catalog"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/data-room", "Data Room",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="The diligence data room for a deal — YOUR uploaded documents "
        "and extracts.",
        primary_purpose="Organize and reference the target's diligence documents.",
        data_sources=["Your uploaded deal documents (real, your workspace)."],
        interpretation_guidance=["Your real deal documents — not market data."],
        related_routes=["/diligence/ingest", "/diligence/deal", "/upload"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/methodology/calculations", "Methodology — Calculations",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="Reference documentation of how PEdesk's metrics and models "
        "are calculated.",
        primary_purpose="Explain the formulas/assumptions behind the analytics.",
        data_sources=["Documentation of PEdesk's own calculation methods."],
        interpretation_guidance=["Reference/methodology, not a data surface."],
        related_routes=["/methodology", "/metric-glossary"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/module-index", "Module Index",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="A navigable index of every PEdesk module/surface.",
        primary_purpose="Find and jump to any tool or page.",
        data_sources=["The route/module manifest (system metadata)."],
        interpretation_guidance=["A navigation index, not a data surface."],
        related_routes=["/tools", "/library"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/verticals", "Healthcare Verticals",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="Index of the CMS-data-backed healthcare vertical pages "
        "(dialysis, home health, hospice, SNF, IRF, LTCH, hospital).",
        primary_purpose="Navigate to the real-data vertical analytics by care setting.",
        data_sources=["Real CMS public vertical datasets (per linked page)."],
        interpretation_guidance=["Each linked vertical uses real CMS public data."],
        related_routes=["/dialysis", "/home-health", "/hospice", "/nursing-homes"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── Geographic Intelligence trio (real public data, shared metric layer) ──
    _ctx(
        "/geo-intel", "Geographic Intelligence",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Landing hub for the three real-data state-analysis "
        "modes: State Comparison, State Rankings, and State Profile.",
        primary_purpose="Help a partner pick the right way to read U.S. "
        "healthcare markets by state for origination/screening.",
        common_questions=["How do I compare states?",
                          "Which states lead/lag on a metric?",
                          "What does the data say about one state?"],
        data_sources=["Navigation surface only — links to the three modes; "
                      "renders no data itself."],
        key_metrics=["(none — hub page)"],
        interpretation_guidance=["A navigation surface; the linked modes carry "
                                 "the real data and the source labels."],
        why_it_matters="Makes the all-real-data state trio discoverable from "
        "the Source nav for origination screening.",
        related_routes=["/state-compare", "/state-rankings", "/state-profile"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/state-compare", "State Comparison",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Compare 2–4 states side by side across every real "
        "state-keyed public dataset PEdesk has ingested.",
        primary_purpose="Give a head-to-head read on a shortlist of target "
        "geographies in one table.",
        common_questions=["How does CA compare to TX and FL?",
                          "Which of these states has the most providers / "
                          "highest uninsured rate?"],
        inputs=["?states=CA,TX,FL — up to 4 validated US states (50 + DC)."],
        outputs=["A metric×state comparison table (15 metrics)."],
        key_metrics=["Population", "Median HH income", "Uninsured rate",
                     "Provider supply", "HRSA HPSA shortage areas",
                     "MA enrollment + dual %", "CDC PLACES SDOH", "HCAHPS"],
        data_sources=["Census/ACS (via County Health Rankings), CMS FFS "
                      "provider enrollment, HRSA HPSA, CMS SNF CHOW, CMS MA "
                      "geographic enrollment, CDC PLACES, CMS HCAHPS — all "
                      "real public data."],
        model_logic_summary="Each metric is pulled per state from a committed "
        "public-data loader; a missing value renders '—' (never fabricated).",
        why_it_matters="Area-level market structure is a first-pass screen on "
        "where a healthcare thesis is more/less supported.",
        diligence_use_cases=["Comparing target markets before prioritizing "
                             "outreach or underwriting."],
        interpretation_guidance=["Area-level public data — combine with "
                                 "deal-specific data before a decision.",
                                 "'—' means no value on record, not zero."],
        limitations=["State-level aggregates; not the deal's own catchment."],
        related_routes=["/geo-intel", "/state-rankings", "/state-profile"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/state-rankings", "State Rankings",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Rank all 50 states + DC on any single real metric, "
        "best-first, with an inline bar for scale.",
        primary_purpose="Origination screening — see where opportunity or risk "
        "concentrates on one metric.",
        common_questions=["Which states have the most provider-shortage areas?",
                          "Where is MA penetration / the uninsured rate highest?"],
        inputs=["?metric=<key> — one of the 15 registered metrics."],
        outputs=["A ranked leaderboard of states for the chosen metric."],
        key_metrics=["Any one of the 15 shared geo metrics."],
        data_sources=["Same real public datasets as State Comparison "
                      "(Census/ACS · CMS · HRSA · CDC PLACES)."],
        model_logic_summary="Sort direction is metric-aware: 'lower is better' "
        "metrics (uninsured, shortage areas) rank lowest-first; size/quality "
        "metrics rank highest-first. States with no value are listed "
        "separately and never ranked or estimated.",
        why_it_matters="A fast cross-state screen to build or narrow a target "
        "geography list.",
        diligence_use_cases=["Building a shortlist of states to investigate."],
        interpretation_guidance=["States with no value on record are listed "
                                 "as 'no data on record', not ranked.",
                                 "Area-level signal, not a deal-level figure."],
        related_routes=["/geo-intel", "/state-compare", "/state-profile"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/state-profile", "State Profile",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="A single-state dossier: every real metric for one "
        "state, each with that state's national rank (#k of n).",
        primary_purpose="Give a quick, ranked read on a single market being "
        "underwritten.",
        common_questions=["What does the data say about California?",
                          "Where does this state rank nationally on each metric?"],
        inputs=["?state=CA — one validated US state (50 + DC)."],
        outputs=["A metric table with the state's value and national rank per row."],
        key_metrics=["All 15 shared geo metrics, each with a national rank."],
        data_sources=["Same real public datasets as State Comparison "
                      "(Census/ACS · CMS · HRSA · CDC PLACES)."],
        model_logic_summary="Ranks are computed once over the 51 jurisdictions "
        "in each metric's natural direction; metrics with no value show '—' "
        "and are left 'unranked' (never fabricated).",
        why_it_matters="Puts one market in national context at a glance.",
        diligence_use_cases=["A first-look dossier on a single target market."],
        interpretation_guidance=["'unranked' means no value on record for that "
                                 "metric — not a zero or a bottom rank.",
                                 "Area-level public data, not the deal's catchment."],
        related_routes=["/geo-intel", "/state-compare", "/state-rankings"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/state-peers", "Similar States",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Finds the states whose real public-data profile is "
        "most similar to a chosen state — a comp-set read for origination.",
        primary_purpose="Answer 'if the thesis works in state X, where else "
        "looks like X?' for building a target-geography comp set.",
        common_questions=["Which states are most like Ohio?",
                          "Where else resembles this market?"],
        inputs=["?state=OH — one validated US state (50 + DC)."],
        outputs=["States ranked by similarity (closest-first) with a distance."],
        key_metrics=["Standardized (z-score) Euclidean distance over the 15 "
                     "shared geo metrics, normalized by the number shared."],
        data_sources=["Derived from the same real public datasets as the rest "
                      "of the geo trio (Census/ACS · CMS · HRSA · CDC PLACES · "
                      "HCAHPS)."],
        model_logic_summary="Each metric is standardized across reporting "
        "states; distance is the RMS of per-metric z-score gaps over the "
        "metrics both states report. Smaller = more alike. States sharing "
        "fewer than 6 metrics are listed separately, not scored.",
        why_it_matters="A fast, transparent comp-set heuristic for deciding "
        "where a working thesis might travel.",
        diligence_use_cases=["Building a comparable-market set from a known "
                             "good market."],
        interpretation_guidance=["Similarity is a DERIVED screening heuristic "
                                 "from real data — not a fabricated score and "
                                 "not a deal-level judgment.",
                                 "States with too few shared metrics are listed "
                                 "separately, never given a misleading score."],
        related_routes=["/geo-intel", "/state-profile", "/state-compare"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/county-explorer", "County Explorer",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Drills into one state's counties on real Census/ACS "
        "demographics — the sub-state level of the geo suite.",
        primary_purpose="Sub-state targeting: see which counties carry a "
        "state's population, age mix, income, uninsured rate and rural share.",
        common_questions=["Which Ohio counties are largest / oldest / poorest?",
                          "What does this state look like county by county?"],
        inputs=["?state=OH and ?sort=<column> — validated state + sort key."],
        outputs=["A sortable county table with a state-total + population-"
                 "weighted-mean footer."],
        key_metrics=["Population", "Age 65+", "Median HH income",
                     "Uninsured rate", "Rural share"],
        data_sources=["County Health Rankings & Roadmaps (republishing U.S. "
                      "Census Bureau ACS / SAHIE / SAIPE), keyless — 3,143 "
                      "counties; the same real source as State Profile."],
        model_logic_summary="Real per-county rows; the footer is the state "
        "total population and population-weighted means over the counties that "
        "report each measure. Counties missing a value show '—'.",
        why_it_matters="Markets are local — county detail shows where a "
        "state's opportunity actually concentrates.",
        diligence_use_cases=["Narrowing a state thesis to specific counties/"
                             "metros for outreach."],
        interpretation_guidance=["Area-level survey estimates, not deal-level "
                                 "figures.",
                                 "'—' means no value on record for that county."],
        related_routes=["/geo-intel", "/state-profile", "/state-compare"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── Model / scenario diligence pages — Guide must state method + limits ──
    _ctx(
        "/diligence/bear-case", "Bear Case",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="Auto-assembles the downside / bear-case risk thesis "
        "from the deal's evidence so IC sees the strongest objections first.",
        primary_purpose="Surface the critical risks and EBITDA-at-risk a deal "
        "must withstand, for the IC memo's bear case.",
        common_questions=["What's the bear case for this deal?",
                          "Which risks put the most EBITDA at risk?",
                          "Is this real or illustrative?"],
        inputs=["A dataset fixture (full pipeline) OR live deal inputs "
                "(standalone regulatory/covenant/bridge/HCRIS extractors)."],
        outputs=["Ranked risk evidence by theme + an IC-memo bear-case preview."],
        data_sources=["Fixture-driven runs are ILLUSTRATIVE; standalone runs "
                      "use real public extractors (HCRIS, regulatory). Mixed."],
        model_logic_summary="Aggregates evidence from the thesis pipeline / "
        "standalone extractors; EBITDA-at-risk sums per-theme impacts.",
        why_it_matters="Forces the downside into IC before committing capital.",
        interpretation_guidance=[
            "Fixture figures are illustrative — re-run against the target's own data before IC.",
            "It surfaces objections; it does not prove they will occur.",
        ],
        limitations=["Evidence quality depends on the inputs supplied; not a forecast."],
        related_routes=["/diligence/ic-packet", "/diligence/payer-stress", "/diligence/risk-workbench"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/deal-mc", "Deal Monte Carlo",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="Monte Carlo of the deal's RCM initiatives + base "
        "business to produce a 5-year EBITDA cone (base / downside / upside).",
        primary_purpose="Size the spread between base, downside and upside "
        "EBITDA for IC and LP reporting.",
        common_questions=["What's the EBITDA range?",
                          "How wide is the downside?",
                          "What assumptions drive the cone?"],
        inputs=["The deal's RCM initiative assumptions + base-business inputs (user/deal data)."],
        outputs=["A 5-year EBITDA distribution cone + assumption sensitivity."],
        data_sources=["USER/DEAL inputs + assumed distributions — a model, not observed outcomes."],
        model_logic_summary="N simulations over the initiative + base assumptions; "
        "the cone is the simulated EBITDA percentile band.",
        why_it_matters="Quantifies uncertainty around the base case for underwriting.",
        interpretation_guidance=[
            "Runs on YOUR assumptions — the cone is only as good as the inputs.",
            "Distribution width reflects assumed volatility, not a guarantee.",
        ],
        limitations=["Not a forecast; no model-accuracy claim — it propagates assumptions."],
        related_routes=["/diligence/payer-stress", "/diligence/bridge-audit", "/diligence/ic-packet"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    _ctx(
        "/diligence/denial-prediction", "Denial Prediction",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="Trains a per-claim denial model on a CCD claims feed "
        "and sizes the recoverable revenue from denial management.",
        primary_purpose="Estimate recoverable denied revenue to underwrite an "
        "RCM denial-management initiative into the EBITDA bridge.",
        common_questions=["How much denied revenue is recoverable?",
                          "How good is the model?",
                          "Is this the deal's real claims?"],
        inputs=["A CCD (consolidated clinical document) claims feed — a fixture "
                "sample unless the deal's own CCD is provided."],
        outputs=["Per-claim denial probabilities, AUC, denial Pareto, recoverable $."],
        data_sources=["Selected CCD FIXTURE (sample claims) + a denial model trained live on it — methodology, not a live per-deal feed."],
        model_logic_summary="Naive Bayes per-claim denial model fit on the CCD; "
        "AUC reports separation; recoverable $ sums avoidable denials.",
        why_it_matters="Sizes a concrete RCM value-creation lever for the bridge.",
        interpretation_guidance=[
            "Fixture data is for methodology — verify against the target's own CCD before IC use.",
            "AUC describes the model on this sample, not a guaranteed live result.",
        ],
        limitations=["Model performance is sample-specific; requires the deal's real claims to be actionable."],
        related_routes=["/diligence/payer-stress", "/diligence/bridge-audit", "/revenue-leakage"],
        data_source_ids=["canonical_claims_dataset", "edi_837"],
        metric_ids=["denial_rate", "clean_claim_rate", "rcm_uplift"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
]

# ── DATA REQUIRED pages: DOCUMENTED Guide contexts (table-driven). Each page
#    activates on the user's own uploaded deal/fund data; the Guide explains
#    what to upload, who to request it from, and what it computes once live —
#    and that current figures are an illustrative scaffold, not fabricated.
#    (route, title, upload-what, request-from, once-activated, import-template)
_DATA_REQUIRED_GUIDE = [
    ("/mgmt-comp", "Management Compensation", "executive comp (base/bonus/equity/FMV)", "CFO / HR / comp consultant", "comp-vs-FMV benchmarking + Stark/AKS overlap flags", "management_compensation_template.csv"),
    ("/partner-economics", "Partner Economics", "partner points/carry/draws/distributions", "Fund CFO / fund administrator", "carry waterfall + partner economics roll-up", "partner_economics_template.csv"),
    ("/mgmt-fee-tracker", "Management Fee Tracker", "fund mgmt-fee schedule + basis + offsets", "Fund CFO / fund administrator", "fee drag + offset tracking", "mgmt_fee_schedule_template.csv"),
    ("/key-person", "Key Person", "key execs, tenure, succession, dependency", "Management / HR", "key-person dependency + succession-gap risk", "key_person_template.csv"),
    ("/treasury", "Treasury", "cash, debt schedule, facilities, covenants", "Portfolio-company CFO", "liquidity runway + covenant headroom + refi timing", "treasury_debt_schedule_template.csv"),
    ("/fundraising", "Fundraising", "fund target, LP commitments, pipeline", "IR / fundraising team", "fund-close tracking + LP pipeline coverage", "fundraising_template.csv"),
    ("/nav-loan-tracker", "NAV Loan Tracker", "NAV facilities, advance rate, LTV, cost", "Fund CFO / NAV lender", "advance-rate headroom, LTV, all-in cost", "nav_loan_template.csv"),
    ("/secondaries-tracker", "Secondaries Tracker", "secondary offers, NAV, discount, buyer", "Fund CFO / secondary advisor", "offer-vs-NAV discount + buyer pipeline", "secondaries_template.csv"),
    ("/continuation-vehicle", "Continuation Vehicle", "CV assets, NAV, rollover %, terms", "Fund CFO / CV advisor", "rollover-vs-new-capital mix + CV terms", "continuation_vehicle_template.csv"),
    ("/coinvest-pipeline", "Co-Invest Pipeline", "co-invest opportunities, sizing, LP demand", "Deal team / IR", "co-invest sizing vs LP-demand coverage", "coinvest_pipeline_template.csv"),
    ("/board-governance", "Board Governance", "board roster, committees, cadence", "Corporate secretary / GC", "board independence + committee coverage", "board_governance_template.csv"),
    ("/capex-budget", "Capex Budget", "capex projects, budget/actual, ROI", "Portfolio-company CFO / FP&A", "budget-vs-actual + maintenance/growth split + ROI", "capex_budget_template.csv"),
    ("/operating-partners", "Operating Partners", "OP roster, assignments, value-add KPIs", "Operating-partner team", "OP coverage + value-add KPI tracking", "operating_partners_template.csv"),
    ("/compliance-attestation", "Compliance Attestation", "attestations, owners, due dates, status", "Compliance officer / GC", "attestation completion + overdue tracking", "compliance_attestation_template.csv"),
    ("/transition-services", "Transition Services (TSA)", "TSA scope, duration, cost, exit plan", "Seller / integration management office", "TSA cost + exit-timeline tracking", "tsa_template.csv"),
    ("/pmi-integration", "PMI Integration", "integration workstreams, milestones, synergy", "Integration lead / IMO", "milestone + synergy-capture tracking", "pmi_integration_template.csv"),
    ("/pmi-playbook", "PMI Playbook", "playbook tasks by function, owners, timing", "Integration lead / IMO", "100-day playbook task tracking", "pmi_integration_template.csv"),
    ("/sellside-process", "Sell-Side Process", "process timeline, buyer list, bids", "Sell-side advisor / banker", "process timeline + bid tracking", "sellside_process_template.csv"),
    ("/diligence-vendors", "Diligence Vendors", "vendor list, scope, fees, status", "Deal team", "vendor scope + fee + deliverable tracking", "diligence_vendors_template.csv"),
    ("/vdr-tracker", "VDR Tracker", "data-room index, request log, Q&A", "Deal team / seller", "data-room completeness + outstanding requests", "vdr_tracker_template.csv"),
    ("/vcp-tracker", "Value-Creation Plan Tracker", "VCP initiatives, owners, $ impact", "Value-creation lead / deal team", "VCP progress + EBITDA-impact roll-up", "vcp_tracker_template.csv"),
    ("/zbb-tracker", "Zero-Based Budget Tracker", "cost lines, baseline, target, savings", "FP&A / portfolio-company CFO", "zero-based savings vs baseline", "zbb_tracker_template.csv"),
    ("/platform-maturity", "Platform Maturity", "maturity dimensions, self-scores, evidence", "Management / portfolio operations", "maturity self-assessment vs target", "platform_maturity_template.csv"),
    ("/ai-operating-model", "AI Operating Model", "AI use-cases, adoption, ROI, risk", "CIO / digital transformation lead", "AI use-case adoption + ROI + risk tracking", "ai_operating_model_template.csv"),
    ("/direct-lending", "Direct Lending", "loan book, spreads, covenants, defaults", "Credit / private-credit team", "loan-book spread, covenant, default tracking", "direct_lending_template.csv"),
    ("/revenue-leakage", "Revenue Leakage", "charge master, 835 remittance, denial codes, AR aging", "RCM / revenue-cycle lead", "denial-driven leakage + underpayment detection", "claims_denials_template.csv"),
    ("/rcm-red-flags", "RCM Red Flags", "claims extract, denial codes, AR aging, encounter volume", "RCM / revenue-cycle lead", "RCM red-flag detection (denials, DAR, aged AR)", "claims_denials_template.csv"),
    ("/redflag-scanner", "Red-Flag Scanner", "financials, KPIs, payer mix, AR aging", "CFO / FP&A / deal team", "cross-financial red-flag scan", "ar_aging_template.csv"),
    ("/risk-matrix", "Risk Matrix", "risk register (likelihood/impact/owner/mitigation)", "Deal team / risk owners", "likelihood×impact risk heatmap", "risk_register_template.csv"),
    ("/insurance-tracker", "Insurance Tracker", "policy schedule, limits, premiums, claims history", "Risk manager / insurance broker", "coverage adequacy + premium trend + renewal calendar", "insurance_schedule_template.csv"),
    ("/rw-insurance", "RW Insurance", "policy list, coverage, renewal, loss runs", "Risk manager / broker", "coverage + loss-run review", "insurance_schedule_template.csv"),
    ("/litigation", "Litigation", "matter list, status, exposure, reserves", "General counsel / litigation counsel", "litigation exposure + reserve adequacy", "litigation_matters_template.csv"),
    ("/cyber-risk", "Cyber Risk", "controls inventory, frameworks, incidents", "CISO / IT security", "control-framework coverage + gap assessment", "cyber_controls_template.csv"),
    ("/medical-realestate", "Medical Real Estate", "lease schedule, rent, term, options, owned RE", "Real estate / facilities", "lease cost, term, renewal-option exposure", "lease_schedule_template.csv"),
    ("/real-estate", "Real Estate", "property list, lease/own, value, NOI", "Real estate / facilities", "owned-vs-leased mix, NOI, lease exposure", "lease_schedule_template.csv"),
    ("/hcit-platform", "HCIT Platform", "EHR/RCM vendor stack, contracts, modules", "CIO / IT", "EHR/RCM stack cost + contract-renewal map", "ehr_vendor_stack_template.csv"),
    ("/tech-stack", "Tech Stack", "application inventory, spend, contracts", "CIO / IT", "application inventory + spend + renewals", "ehr_vendor_stack_template.csv"),
    ("/clinical-ai", "Clinical AI", "AI tools, vendors, use-cases, validation", "CMIO / clinical informatics", "clinical-AI tool inventory + adoption + validation", "ai_operating_model_template.csv"),
    ("/digital-front-door", "Digital Front Door", "patient-access channels, volumes, conversion", "Patient access / marketing", "access-channel volume + conversion + leakage", "digital_front_door_template.csv"),
    ("/direct-employer", "Direct Employer", "employer contracts, lives, PEPM, services", "Sales / employer-contracting", "direct-employer roster + PEPM economics", "direct_employer_template.csv"),
    ("/diligence/physician-eu", "Physician Economic Unit", "provider roster, wRVU, collections, comp, payer mix", "CFO / practice management / RCM", "real per-provider P&L + roster optimization", "management_compensation_template.csv"),
    ("/diligence/risk-workbench", "Risk Workbench", "risk register / regulatory inputs", "Deal team / risk owners", "the nine-panel risk panorama from your real inputs", "risk_register_template.csv"),
]

# HIGH_PRIORITY pages must keep metric/data-source links (test_pedesk_guide_metric_data_context).
_DR_DATA_SOURCE_IDS = {
    "/diligence/physician-eu": ["compensation_file", "provider_roster"],
}
for _route, _title, _upload, _who, _activates, _tmpl in _DATA_REQUIRED_GUIDE:
    _MANUAL.append(_ctx(
        _route, _title,
        short_description=(f"{_title} activates on YOUR uploaded {_upload}; until "
                           "then it shows an illustrative scaffold (no fabricated "
                           "values), with a panel listing exactly what to provide."),
        primary_purpose=f"Once your data is uploaded: {_activates}.",
        data_sources=[f"USER DATA REQUIRED — upload {_upload} (import template: {_tmpl})."],
        data_source_ids=_DR_DATA_SOURCE_IDS.get(_route, []),
        interpretation_guidance=[
            "Not live until you upload your own data — the page shows what to provide.",
            f"Request the data from: {_who}.",
            "Figures currently shown are an illustrative scaffold, NOT this deal's values.",
        ],
        why_it_matters=f"{_activates} — but only once it runs on your real data, not a fabricated default.",
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ))

# ── Quant / modeling surfaces (documented from the live handlers) ──────
# High-traffic analytic pages where partners ask hard quantitative
# questions; documented by reading the real route handlers + page modules
# so the Guide can explain the method honestly (and flag illustrative vs
# real-data surfaces correctly).
_MANUAL.extend([
    _ctx(
        "/quant-lab", "Quant Lab",
        category=PageContextCategory.RESEARCH_BACKTESTING,
        short_description="The full quant stack on one page — Bayesian "
        "calibration, DEA efficiency frontier, queueing theory, and margin "
        "survival analysis, all computed live over public CMS HCRIS data.",
        primary_purpose="Give the deal team a single analytical surface that "
        "applies the platform's statistical models to the latest hospital "
        "cost-report universe, so a partner can sanity-check a target against "
        "rigorously-computed peer benchmarks rather than rules of thumb.",
        intended_users=["Principals/associates doing quantitative diligence "
                        "and benchmarking."],
        common_questions=[
            "How is the margin survival probability computed?",
            "What does the efficiency frontier say about this hospital?",
            "How does Bayesian calibration shrink a thin-data KPI toward peers?",
            "Is the denial-rate estimate observed or a prior?",
        ],
        inputs=["Latest-per-CCN CMS HCRIS cost reports with computed features "
                "(_get_latest_per_ccn + _add_computed_features)."],
        outputs=["Bayesian KPI posteriors with credible intervals, a DEA "
                 "efficiency frontier scatter + scores, M/M/c queueing "
                 "metrics, and a margin survival curve with years-to-distress."],
        key_metrics=["Operating margin", "Days in AR", "Denial rate",
                     "Net collection rate", "Clean claim rate",
                     "Occupancy rate", "Efficiency score", "Survival probability"],
        data_sources=["CMS HCRIS (Medicare cost reports), latest filed year "
                      "per provider."],
        model_logic_summary=(
            "Several distinct models, each honest about its method: "
            "(1) Bayesian calibration — a real Beta-Binomial conjugate "
            "posterior for rate metrics (denial/collection/clean-claim) and a "
            "Normal-Normal conjugate mean update for continuous metrics (AR "
            "days, cost-to-collect) where the dispersion is read from the "
            "spread of the hospital-type priors, not a magic constant. "
            "(2) DEA — an output-oriented data-envelopment efficiency frontier. "
            "(3) Queueing — M/M/c (Erlang-C) wait-time/SLA math on RCM "
            "operations. (4) Survival — NOT Kaplan-Meier/Cox (no time-to-event "
            "data); it fits operating margin vs. year by OLS on the provider's "
            "HCRIS history and reports P(margin>0) at horizon t as the normal "
            "CDF of the OLS prediction interval, so uncertainty widens with the "
            "forecast horizon. See rcm_mc/ml/{bayesian_calibration,"
            "efficiency_frontier,queueing_model,survival_analysis}.py."),
        why_it_matters="Turns a raw public cost-report universe into "
        "defensible, uncertainty-aware benchmarks — the analytical moat over "
        "a Bloomberg trailing-financials read.",
        diligence_use_cases=[
            "Benchmarking a target's RCM KPIs against a calibrated peer "
            "posterior instead of a point peer median.",
            "Reading a target's margin runway / distress odds before IC."],
        interpretation_guidance=[
            "A Bayesian posterior labeled 'prior_only' or 'weak' is shrunk "
            "toward the peer prior — the credible interval is wide on purpose; "
            "it is not a measured value.",
            "Survival probabilities are model estimates from the margin trend, "
            "not actuarial life-table figures.",
            "Everything here is computed over public HCRIS, not a specific "
            "deal's internal data."],
        limitations=[
            "HCRIS lags (cost reports are filed with a delay), so the 'latest' "
            "year is not the current quarter.",
            "Survival/queueing/DEA outputs are model estimates and inherit the "
            "noise and gaps in HCRIS."],
        related_routes=["/portfolio/regression", "/data-intelligence",
                        "/target-screener", "/state-compare"],
        metric_ids=["operating_margin", "days_in_ar", "denial_rate",
                    "net_collection_rate", "clean_claim_rate", "occupancy_rate"],
        data_source_ids=["cms_hcris"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/portfolio/regression", "Regression Analysis",
        category=PageContextCategory.RESEARCH_BACKTESTING,
        short_description="Interactive OLS regression over the CMS HCRIS "
        "universe with built-in multicollinearity diagnostics (VIF, Belsley "
        "condition number) and a VIF-pruned optimized model.",
        primary_purpose="Let the team fit and interpret a transparent linear "
        "model of a hospital financial outcome on operating drivers, while "
        "actively guarding against the high-R²-but-meaningless trap that "
        "multicollinearity creates.",
        intended_users=["Quantitatively-inclined principals/associates."],
        common_questions=[
            "Which features actually drive the target, net of collinearity?",
            "Why was a feature dropped from the optimized model?",
            "Is this R² real or inflated by multicollinearity?",
            "What does the condition number tell me?",
        ],
        inputs=["CMS HCRIS latest-per-CCN data; query controls for target "
                "variable, universe filter, log-target, and segmented "
                "regression. Honest-by-default on first load: leaky features "
                "are dropped and dollar targets log-transformed."],
        outputs=["Coefficient table with significance, R²/adjusted R², an F "
                 "test, per-feature VIF, the Belsley condition number with a "
                 "verdict banner, and a VIF-pruned optimized model."],
        key_metrics=["R² / adjusted R²", "F statistic", "VIF",
                     "Condition number", "Coefficient significance"],
        data_sources=["CMS HCRIS (Medicare cost reports)."],
        model_logic_summary=(
            "Ordinary least squares fit in-page (the page has its own _run_ols), "
            "plus rcm_mc/finance/regression.py for VIF, the Belsley condition "
            "number, prune_collinear, and a multicollinearity verdict. The "
            "F-test p-value uses an incomplete-beta implementation (no scipy). "
            "The default view is the defensible model: algebraically-leaky "
            "features removed and dollar targets log-transformed; an explicit "
            "form submit lets a partner inspect the leaky/raw-dollar version."),
        why_it_matters="A high R² from a collinear model is a classic "
        "diligence false-positive; this page makes the model honest and the "
        "dropped-feature reasoning explicit.",
        diligence_use_cases=[
            "Identifying which operating levers move a financial outcome.",
            "Pressure-testing a thesis claim that 'X drives Y' for collinearity."],
        interpretation_guidance=[
            "A high condition number (or red verdict banner) means coefficients "
            "are unstable — read the optimized/pruned model, not the raw one.",
            "A feature dropped for collinearity is not 'unimportant'; it is "
            "redundant with another feature already in the model.",
            "This fits public HCRIS, not a single deal's financials."],
        limitations=[
            "Cross-sectional HCRIS only — no causal claim, just association.",
            "OLS assumptions (linearity, homoskedasticity) are not fully "
            "tested on the page."],
        related_routes=["/quant-lab", "/data-intelligence", "/target-screener"],
        metric_ids=["operating_margin", "revenue", "occupancy_rate", "payer_mix"],
        data_source_ids=["cms_hcris"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/lbo-stress", "LBO Stress Test",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="An ILLUSTRATIVE LBO model stress test — sweeps "
        "exit multiple, leverage and growth assumptions and reports the "
        "resulting equity outcomes (MOIC, IRR, proceeds) and break-even "
        "leverage.",
        primary_purpose="Show how an LBO's returns flex under different "
        "entry/exit/leverage assumptions, so a partner can see where the "
        "deal breaks rather than reading a single base-case number.",
        intended_users=["Deal team underwriting or pressure-testing a thesis."],
        common_questions=[
            "How sensitive is MOIC to the exit multiple?",
            "At what leverage does this deal stop working?",
            "What IRR do these assumptions imply?",
        ],
        inputs=["Scenario assumptions from query parameters (entry/exit "
                "multiple, leverage, EBITDA growth). With no parameters it "
                "renders a clearly-labeled illustrative example."],
        outputs=["Scenario table and chart of exit EBITDA → EV → net debt → "
                 "equity proceeds → MOIC/IRR, plus an exit-multiple "
                 "sensitivity grid and a break-even leverage read."],
        key_metrics=["MOIC", "IRR", "Equity proceeds", "Exit multiple",
                     "Leverage", "EV/EBITDA"],
        data_sources=["No external data — computes outcomes deterministically "
                      "from the entered/illustrative assumptions."],
        model_logic_summary=(
            "Standard LBO arithmetic: exit EV = exit EBITDA × exit multiple; "
            "equity proceeds = exit EV − net debt at exit; MOIC = proceeds / "
            "entry equity; IRR annualizes MOIC over the hold. Run across a grid "
            "of exit-multiple/leverage scenarios. Page carries an explicit "
            "illustrative-note banner (ck_illustrative_note)."),
        why_it_matters="Returns are dominated by entry/exit multiple and "
        "leverage; making the sensitivity explicit prevents anchoring on a "
        "single base case.",
        diligence_use_cases=[
            "Bounding the return range before committing to an underwriting.",
            "Finding the leverage/exit-multiple combination that breaks the deal."],
        interpretation_guidance=[
            "These are ILLUSTRATIVE scenario outputs from assumptions, NOT a "
            "specific portfolio deal's modeled returns unless you supply its "
            "parameters.",
            "MOIC/IRR move mechanically with the assumptions — read the grid, "
            "not one cell."],
        limitations=[
            "Deterministic point scenarios — no probability distribution over "
            "outcomes (use the Monte Carlo surfaces for that).",
            "Illustrative assumptions unless overridden via parameters."],
        related_routes=["/portfolio/monte-carlo", "/scenarios", "/quant-lab"],
        metric_ids=["moic", "irr", "exit_multiple", "leverage", "ev_to_ebitda",
                    "enterprise_value", "ebitda"],
        data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/scenarios", "Scenario Explorer",
        category=PageContextCategory.RESEARCH_BACKTESTING,
        short_description="A library of preset macro/operational shock "
        "scenarios (payer rate cuts, volume shocks, etc.) that can be layered "
        "onto a simulation.",
        primary_purpose="Give the team a curated set of named, reusable shock "
        "definitions so scenario analysis is consistent and explainable rather "
        "than ad hoc.",
        intended_users=["Deal team doing scenario / downside analysis."],
        common_questions=[
            "What preset shocks are available?",
            "What does the 'payer rate cut' scenario actually change?",
            "How do I stress a deal's payer mix?",
        ],
        inputs=["Preset shock definitions (PRESET_SHOCKS from "
                "scenarios/scenario_shocks.py)."],
        outputs=["A catalog of each preset's shocks — e.g. per-payer rate "
                 "deltas and volume adjustments — with descriptions."],
        key_metrics=["Payer rate shock", "Volume shock", "EBITDA impact"],
        data_sources=["In-repo preset shock library (definitions, not deal "
                      "data)."],
        model_logic_summary=(
            "Renders the PRESET_SHOCKS definitions. Each preset is a structured "
            "set of multiplicative/additive shocks (payer-level rate deltas, "
            "volume adjustments) intended to be applied to a deal's simulation "
            "via the scenario overlay layer. This page is the catalog/explainer; "
            "the impact materializes when a preset is applied to a specific "
            "simulation."),
        why_it_matters="Consistent, named downside scenarios make IC "
        "discussions comparable across deals.",
        diligence_use_cases=[
            "Selecting a standard downside scenario to apply to a target's model.",
            "Explaining to IC exactly what a stress case assumes."],
        interpretation_guidance=[
            "These are scenario TEMPLATES — the dollar impact depends entirely "
            "on the deal they are applied to; the page itself shows definitions, "
            "not a specific deal's results."],
        limitations=[
            "A catalog of assumptions, not live results; presets are "
            "illustrative templates, not predictions."],
        related_routes=["/lbo-stress", "/portfolio/monte-carlo", "/quant-lab"],
        metric_ids=["ebitda", "payer_mix"],
        data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
    _ctx(
        "/portfolio/monte-carlo", "Portfolio Monte Carlo",
        category=PageContextCategory.PORTFOLIO_LP,
        short_description="Fund-level correlated Monte Carlo that aggregates "
        "the per-deal EBITDA simulations stored in saved analysis packets into "
        "a portfolio-wide outcome distribution.",
        primary_purpose="Show the fund-level return distribution and downside "
        "risk that emerges from the individual deal simulations, accounting for "
        "correlation between deals rather than summing point estimates.",
        intended_users=["Partners and LP-reporting staff assessing fund-level "
                        "risk."],
        common_questions=[
            "What's the fund-level EBITDA / return distribution?",
            "How much does cross-deal correlation widen the downside?",
            "Which deals drive portfolio risk?",
        ],
        inputs=["Saved analysis packets (one per deal) from the analysis store; "
                "each carries its own EBITDA simulation p50/std."],
        outputs=["A correlated fund-level Monte Carlo outcome distribution "
                 "built from the per-deal simulations."],
        key_metrics=["EBITDA", "MOIC", "IRR", "Portfolio downside"],
        data_sources=["Stored analysis packets (model output over each deal's "
                      "observed/entered inputs)."],
        model_logic_summary=(
            "Loads the latest analysis packet per deal (analysis_store), pulls "
            "each deal's EBITDA simulation summary, and runs a correlated "
            "portfolio Monte Carlo (mc/portfolio_monte_carlo.run_portfolio_mc) "
            "to combine them into a fund-level distribution."),
        why_it_matters="Portfolio risk is not the sum of point estimates; "
        "correlation can fatten the downside materially, which matters for LP "
        "reporting and reserve planning.",
        diligence_use_cases=[
            "Fund-level downside and reserve discussions.",
            "Seeing how concentration/correlation shapes portfolio risk."],
        interpretation_guidance=[
            "Only as meaningful as the saved deal packets — if few deals have "
            "been analyzed, the portfolio view is sparse.",
            "Outputs are model estimates built on each deal's own assumptions, "
            "not realized returns."],
        limitations=[
            "Requires saved analysis packets; empty/sparse if deals haven't "
            "been run through the analysis builder.",
            "Correlation assumptions drive the aggregate downside — read them "
            "before quoting a fund-level number."],
        related_routes=["/lbo-stress", "/scenarios", "/analysis", "/lp-dashboard"],
        metric_ids=["ebitda", "moic", "irr"],
        data_source_ids=["analysis_run", "portfolio_snapshot"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
])


# ── Illustrative PE analytic tools (data_public family) ────────────────
# Scenario/assumption-driven calculators (no live CMS data); a few summarise
# the licensed deal corpus. Documented from each module's docstring + the
# shared data_public pattern (query-param driven, ck_illustrative_note). Tuple:
# (route, title, short_desc, purpose, common_qs, key_metrics, metric_ids,
#  data_source_ids, model_logic, why, data_conf)
_DC = DataConfidence
_ILLUSTRATIVE_TOOLS = [
    ("/value-creation-plan", "Value Creation Plan",
     "Post-close 100-day / value-creation plan tracker — initiatives, owners, "
     "EBITDA-impact targets and status.",
     "Track the operational value-creation initiatives that turn the deal "
     "thesis into realized EBITDA after close.",
     ["What's in the 100-day plan?", "How much EBITDA do the initiatives target?",
      "Which initiatives are behind?"],
     ["Initiative count", "Targeted EBITDA impact", "% complete"],
     ["value_creation_opportunity", "ebitda", "synergy_estimate"], [],
     "Composes a plan from initiative inputs and sums their targeted EBITDA "
     "impact against status; the figures shown are an illustrative scaffold "
     "until populated for a specific deal.",
     "Disciplined post-close execution is where PE returns are actually made.",
     _DC.MODEL_ESTIMATE),
    ("/qoe-analyzer", "Quality of Earnings Analyzer",
     "Structures a quality-of-earnings review — adjusted-EBITDA bridge, "
     "add-backs, and one-time / run-rate normalization.",
     "Move from reported to adjusted EBITDA transparently so the team can "
     "pressure-test the earnings a valuation rests on.",
     ["What are the EBITDA add-backs?", "How does reported bridge to adjusted "
      "EBITDA?", "Which adjustments are aggressive?"],
     ["Reported EBITDA", "Adjusted EBITDA", "Add-backs", "EBITDA margin"],
     ["ebitda", "adjusted_ebitda", "ebitda_margin", "revenue"], [],
     "Builds a reported→adjusted EBITDA bridge from entered add-backs/"
     "normalizations; values are illustrative until a deal's actuals are "
     "supplied.",
     "QoE add-backs directly move the purchase price; making them explicit "
     "is core diligence.",
     _DC.MODEL_ESTIMATE),
    ("/portfolio-optimizer", "Portfolio Construction Optimizer",
     "Analyzes a selected set of corpus deals for portfolio construction — "
     "return/risk trade-offs and concentration.",
     "Help think about which combination of deals balances return, risk and "
     "concentration at the fund level.",
     ["What mix optimizes return vs risk?", "Where is the portfolio "
      "concentrated?", "How diversified is this construction?"],
     ["MOIC", "IRR", "Concentration", "Hold period"],
     ["moic", "irr", "hold_period"], ["public_transaction_corpus"],
     "Optimization/heuristic over selected corpus deals' return profiles; "
     "benchmarks come from the licensed corpus, scenario weightings are "
     "illustrative.",
     "Fund-level construction, not single-deal underwriting, drives realized "
     "fund returns.",
     _DC.MIXED),
    ("/hold-optimizer", "Hold Period Optimizer",
     "Given an entry profile, models how MOIC/IRR trade off across different "
     "hold periods.",
     "Surface the hold-period sweet spot where compounding EBITDA growth still "
     "beats the IRR drag of a longer hold.",
     ["What's the optimal hold period?", "How does IRR change if we hold "
      "longer?", "When does MOIC stop compensating for time?"],
     ["Hold period", "IRR", "MOIC", "Exit multiple"],
     ["hold_period", "irr", "moic", "exit_multiple"], [],
     "Projects exit value across candidate hold lengths from the entry profile "
     "(sector, EV, EV/EBITDA, payer mix) and reports IRR/MOIC by year; "
     "illustrative assumptions unless overridden.",
     "Time is a first-order IRR driver; the optimal hold is rarely the "
     "default five years.",
     _DC.MODEL_ESTIMATE),
    ("/exit-readiness", "Exit Readiness Index",
     "Multi-dimensional exit-readiness scoring across Financial / Operational "
     "/ Commercial / Governance axes.",
     "Give a structured read on whether an asset is actually ready to go to "
     "market, not just whether the numbers look good.",
     ["Is this asset ready to exit?", "What's weakest for a sale process?",
      "What should we fix before going to market?"],
     ["Readiness score", "Per-axis scores", "Gaps"],
     ["ebitda_margin", "revenue_growth"], [],
     "Weighted scorecard across readiness dimensions; the inputs are "
     "illustrative until scored against a real asset.",
     "Going to market unprepared destroys value; a readiness gap list is "
     "actionable pre-exit.",
     _DC.MODEL_ESTIMATE),
    ("/refi-optimizer", "Refinance Optimizer",
     "Models refinancing scenarios — new leverage, rate, and the cash-out / "
     "rate-savings trade-off.",
     "Evaluate whether and when to refinance a portfolio company's debt.",
     ["Should we refinance now?", "How much can we cash out?", "What's the "
      "rate-savings impact?"],
     ["Leverage", "Interest rate", "Cash-out", "EV/EBITDA"],
     ["leverage", "debt", "ev_to_ebitda"], [],
     "Computes new debt service and cash-out across entered refi assumptions; "
     "illustrative unless deal-specific terms are supplied.",
     "Refinancings can return capital to LPs mid-hold and reset the cost of "
     "debt.",
     _DC.MODEL_ESTIMATE),
    ("/working-capital", "Working Capital Analyzer",
     "AR / AP / DSO / cash-conversion-cycle diligence with payer-level AR and "
     "RCM levers.",
     "Quantify the cash tied up in working capital and the RCM levers that "
     "free it — a recurring source of hidden value in healthcare deals.",
     ["How much cash is trapped in AR?", "What's the cash conversion cycle?",
      "Which payers drive DSO?"],
     ["Days in AR", "DSO", "Cash conversion cycle", "Net collection rate"],
     ["days_in_ar", "net_collection_rate"], [],
     "Computes AR/AP/DSO/CCC and payer-level AR from entered balances; "
     "illustrative until a target's actuals are loaded.",
     "Working-capital release is often the fastest post-close cash win in "
     "provider businesses.",
     _DC.MODEL_ESTIMATE),
    ("/unit-economics", "Unit Economics Analyzer",
     "Per-location / per-provider unit economics — revenue, ramp curves, and "
     "visit / provider profitability.",
     "Get under the platform average to the economics of a single site or "
     "provider, where roll-up value is actually created.",
     ["What does one location earn?", "How long is the ramp to maturity?",
      "Which providers are profitable?"],
     ["Revenue/location", "Contribution margin", "Ramp curve"],
     ["provider_contribution_margin", "revenue", "ebitda_margin"], [],
     "Builds per-unit P&L and ramp curves from entered location/provider "
     "inputs; illustrative unless populated with real site data.",
     "A platform is only as good as the repeatable economics of its next "
     "unit.",
     _DC.MODEL_ESTIMATE),
    ("/rollup-economics", "Roll-Up / Platform Economics",
     "Models roll-up math — multiple arbitrage, synergy capture, and "
     "platform-vs-add-on blended multiples.",
     "Show how buying add-ons below the platform multiple and capturing "
     "synergies compounds equity value.",
     ["What's the multiple-arbitrage value?", "How much synergy is needed?",
      "What blended multiple results?"],
     ["EV/EBITDA", "Synergy", "Blended multiple", "MOIC"],
     ["ev_to_ebitda", "synergy_estimate", "ebitda", "moic"], [],
     "Computes blended entry multiple and equity build from platform + add-on "
     "assumptions; illustrative scenario math, not a specific program.",
     "Multiple arbitrage + synergy is the core healthcare-services roll-up "
     "thesis.",
     _DC.MODEL_ESTIMATE),
    ("/sponsor-league", "Sponsor League Table",
     "Ranks healthcare PE sponsors by realized returns across the licensed "
     "deal corpus.",
     "Benchmark sponsors against each other on realized performance to inform "
     "co-invest and competitive dynamics.",
     ["Which sponsors perform best?", "How does a sponsor rank?", "Who's "
      "active in this sector?"],
     ["MOIC", "IRR", "Deal count", "Hold period"],
     ["moic", "irr", "hold_period"], ["public_transaction_corpus"],
     "Aggregates realized-return metrics per sponsor from the licensed deal "
     "corpus; rankings reflect corpus coverage, not the full market.",
     "Knowing who wins in a sector shapes co-invest, competition, and exit "
     "buyer lists.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/growth-runway", "Growth Runway Analyzer",
     "TAM / SAM / SOM sizing, penetration curve, and share-expansion drivers.",
     "Pressure-test how much room a thesis has to grow before the market "
     "caps it.",
     ["How big is the addressable market?", "What penetration is assumed?",
      "How much runway is left?"],
     ["TAM/SAM/SOM", "Penetration %", "Revenue growth"],
     ["revenue_growth", "revenue"], [],
     "Builds market-sizing and penetration curves from entered assumptions; "
     "illustrative unless grounded in real market data.",
     "A thesis without runway is a value trap; sizing the ceiling matters.",
     _DC.MODEL_ESTIMATE),
    ("/return-attribution", "Return Attribution",
     "MOIC decomposition (P25/P50/P75) by deal dimensions — sector, vintage, "
     "payer mix — from the deal corpus.",
     "Attribute realized returns to the factors that produced them so the "
     "team learns what actually drives MOIC.",
     ["What drives MOIC in the corpus?", "Which sectors/vintages return best?",
      "How dispersed are returns?"],
     ["MOIC P25/P50/P75", "IRR"],
     ["moic", "irr"], ["public_transaction_corpus"],
     "Groups corpus deals by dimension and reports the MOIC distribution; "
     "reflects corpus coverage, not a forecast.",
     "Return attribution turns a track record into a repeatable playbook.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/entry-multiple", "Entry Multiple Analysis",
     "EV/EBITDA entry multiples across sectors and their correlation with "
     "realized returns, from the deal corpus.",
     "Ground an entry-price view in what comparable deals actually paid and "
     "how that related to returns.",
     ["What's the typical entry multiple here?", "Do lower entries return "
      "better?", "How do sectors compare on entry price?"],
     ["EV/EBITDA", "Exit multiple", "EBITDA"],
     ["ev_to_ebitda", "exit_multiple", "ebitda"], ["public_transaction_corpus"],
     "Summarizes entry EV/EBITDA by sector and its correlation to outcomes "
     "from the licensed corpus; descriptive, not predictive.",
     "Entry multiple is the single biggest controllable return lever.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/exit-multiple", "Exit Multiple Analysis",
     "Exit EV/EBITDA multiples by sector and the multiple-expansion vs "
     "EBITDA-growth split of returns.",
     "See how much of corpus returns came from paying-up vs growing the "
     "business.",
     ["What exit multiples are realistic?", "How much return is multiple "
      "expansion?", "Which sectors re-rate on exit?"],
     ["Exit multiple", "EV/EBITDA", "Multiple expansion"],
     ["exit_multiple", "ev_to_ebitda"], ["public_transaction_corpus"],
     "Summarizes exit multiples and decomposes returns into expansion vs "
     "growth from corpus data; descriptive.",
     "Underwriting flat-to-down exit multiples is the discipline that "
     "survives a re-rating.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/dividend-recap", "Dividend Recap",
     "Capital-structure recap scenarios — incremental leverage, timing, and "
     "the carry / DPI impact of returning capital early.",
     "Evaluate pulling capital out via a dividend recap and what it does to "
     "leverage and returns.",
     ["Can we do a dividend recap?", "How much can we distribute?", "What's "
      "the IRR/DPI impact?"],
     ["Leverage", "Distribution", "MOIC", "IRR"],
     ["leverage", "debt", "moic", "irr"], [],
     "Models incremental debt capacity and the distribution's return impact "
     "across entered scenarios; illustrative unless deal terms are supplied.",
     "Recaps return capital to LPs mid-hold and boost DPI/IRR without an "
     "exit.",
     _DC.MODEL_ESTIMATE),
]

_ILLUS_GUIDANCE = [
    "Figures are ILLUSTRATIVE scenario outputs from the entered/default "
    "assumptions — not a specific deal's modeled result unless you supply its "
    "inputs.",
    "Read the assumptions before quoting any number; the outputs move "
    "mechanically with them.",
]
for (_r, _t, _sd, _pp, _cq, _km, _mids, _dsids, _ml, _why, _dc) in _ILLUSTRATIVE_TOOLS:
    _corpus = "public_transaction_corpus" in _dsids
    _MANUAL.append(_ctx(
        _r, _t,
        short_description=_sd,
        primary_purpose=_pp,
        common_questions=_cq,
        inputs=(["Deal benchmarks from the licensed deal corpus, plus scenario "
                 "assumptions."] if _corpus else
                ["Scenario assumptions (query parameters); renders an "
                 "illustrative example with no inputs."]),
        outputs=["Computed tables/charts for the analysis above."],
        key_metrics=_km,
        data_sources=(["Licensed PE deal corpus (public_transaction_corpus)."]
                      if _corpus else
                      ["None — computed deterministically from the "
                       "entered/illustrative assumptions."]),
        model_logic_summary=_ml,
        why_it_matters=_why,
        diligence_use_cases=[_pp],
        interpretation_guidance=(
            ["Benchmarks reflect the licensed corpus's coverage, not the full "
             "market; scenario overlays are illustrative."] if _corpus
            else list(_ILLUS_GUIDANCE)),
        limitations=(
            ["Corpus coverage is a sample of disclosed deals — not exhaustive."]
            if _corpus else
            ["Deterministic point scenarios, no probability distribution.",
             "Illustrative assumptions unless overridden via parameters."]),
        related_routes=["/quant-lab", "/lbo-stress", "/portfolio/monte-carlo"],
        metric_ids=_mids,
        data_source_ids=_dsids,
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=_dc,
    ))


# ── Corpus intelligence + fund-ops tools (data_public family, batch 3) ──
# (route, title, short_desc, purpose, common_qs, key_metrics, metric_ids,
#  data_source_ids, model_logic, why, data_conf)
_PE_TOOLS_3 = [
    ("/deal-flow-heatmap", "Deal Flow Heatmap",
     "Year × sector deal-activity matrix from the licensed deal corpus.",
     "See where and when deal activity concentrated, to read sector cycles.",
     ["Which sectors are most active?", "How has activity shifted by year?",
      "Where is deal flow heating up or cooling?"],
     ["Deal count by year × sector"], [], ["public_transaction_corpus"],
     "Counts corpus deals per (year, sector) cell and renders a heatmap; "
     "reflects the corpus's disclosed-deal coverage.",
     "Activity cycles signal entry timing and competitive intensity.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/sponsor-heatmap", "Sponsor × Sector Heatmap",
     "Realized-performance heatmap of sponsors against sectors, from the deal "
     "corpus.",
     "See which sponsors win in which sectors.",
     ["Who's strong in this sector?", "Where does a sponsor concentrate?",
      "Which sponsor/sector cells outperform?"],
     ["MOIC", "IRR", "Deal count"], ["moic", "irr"],
     ["public_transaction_corpus"],
     "Aggregates corpus realized returns per (sponsor, sector); reflects "
     "corpus coverage, not the full market.",
     "Sponsor specialization shapes competition and co-invest decisions.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/sector-intel", "Sector Intelligence",
     "Corpus-calibrated performance benchmarks by sector — returns, multiples, "
     "and margins.",
     "Ground a sector view in how comparable deals actually performed.",
     ["How does this sector perform?", "What multiples are typical here?",
      "Which sectors return best?"],
     ["MOIC", "IRR", "EV/EBITDA", "EBITDA margin"],
     ["moic", "irr", "ev_to_ebitda", "ebitda_margin"],
     ["public_transaction_corpus"],
     "Summarizes corpus deals by sector into benchmark distributions; "
     "descriptive, not predictive.",
     "Sector base rates anchor underwriting and pattern-match new deals.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/sector-correlation", "Sector Correlation Matrix",
     "Pairwise correlations of sector returns across the deal corpus.",
     "See which sectors move together — for portfolio diversification.",
     ["Which sectors are correlated?", "What diversifies this book?",
      "Are these two sectors a hedge or a double-down?"],
     ["Pairwise return correlation"], [], ["public_transaction_corpus"],
     "Pearson correlations of sector return series from the corpus; sample-"
     "limited by corpus coverage.",
     "Correlation drives true portfolio diversification, not sector labels.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/leverage-intel", "Leverage Intelligence",
     "Corpus-calibrated capital-structure analysis — leverage levels and their "
     "relationship to returns.",
     "Ground a leverage view in what comparable deals used and how it related "
     "to outcomes.",
     ["What leverage is typical here?", "Does more leverage help returns?",
      "How levered are peer deals?"],
     ["Leverage", "Debt/EBITDA", "EV/EBITDA"],
     ["leverage", "debt", "ev_to_ebitda"], ["public_transaction_corpus"],
     "Summarizes corpus leverage and its correlation with returns; "
     "descriptive.",
     "Leverage amplifies returns and risk; base rates discipline structuring.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/size-intel", "Deal Size Intelligence",
     "EV distribution across the corpus and performance by deal-size band.",
     "See whether smaller or larger deals returned better in comparable data.",
     ["What deal sizes are typical?", "Do small deals out-return large?",
      "Where does this deal sit on size?"],
     ["Enterprise value", "MOIC by size band"],
     ["enterprise_value", "moic"], ["public_transaction_corpus"],
     "Bins corpus deals by EV and compares return distributions; descriptive.",
     "Size correlates with competition, multiple, and the return ceiling.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/payer-intel", "Payer Intelligence",
     "Corpus-calibrated payer-mix analysis — exposure bands and their link to "
     "outcomes.",
     "Ground payer-mix risk in how comparable provider deals fared.",
     ["What payer mix is typical?", "Does Medicare exposure hurt returns?",
      "How risky is this payer profile?"],
     ["Payer mix", "Medicare exposure", "Commercial exposure"],
     ["payer_mix", "medicare_exposure", "commercial_payer_exposure"],
     ["public_transaction_corpus"],
     "Summarizes corpus payer-mix bands vs outcomes; descriptive.",
     "Payer mix is the dominant reimbursement-risk axis in healthcare deals.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/vintage-perf", "Vintage Performance",
     "Year-by-year corpus performance — P50 MOIC and IRR by vintage.",
     "See how each entry vintage performed, to read cycle timing.",
     ["Which vintages performed best?", "How does my vintage compare?",
      "Is this a good year to deploy?"],
     ["MOIC by vintage", "IRR by vintage"], ["moic", "irr"],
     ["public_transaction_corpus"],
     "Groups corpus deals by entry year and reports the MOIC/IRR distribution; "
     "descriptive.",
     "Vintage is a major, largely-exogenous return driver.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/gp-benchmarking", "GP Benchmarking",
     "Compare a chosen GP's portfolio performance against corpus peers.",
     "Benchmark a manager objectively for co-invest / LP diligence.",
     ["How does this GP rank?", "Is their track record corpus-validated?",
      "Where do they out/underperform?"],
     ["MOIC", "IRR", "Hold period"], ["moic", "irr", "hold_period"],
     ["public_transaction_corpus"],
     "Computes the selected GP's corpus deals vs peer distribution; reflects "
     "corpus coverage, not audited fund returns.",
     "GP selection is the LP's primary lever; objective benchmarks cut "
     "through marketing.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/multiple-decomp", "Acquisition Multiple Decomposition",
     "Breaks entry EV/EBITDA into its drivers (sector, size, growth, quality).",
     "Understand WHY a multiple is what it is, not just its level.",
     ["Why is this multiple high?", "What drives entry pricing?",
      "Is the premium justified?"],
     ["EV/EBITDA", "EBITDA"], ["ev_to_ebitda", "ebitda"],
     ["public_transaction_corpus"],
     "Attributes entry-multiple variation to deal attributes across the "
     "corpus; descriptive decomposition.",
     "Knowing what you're paying for separates a fair price from a stretch.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/peer-transactions", "Peer Transaction Database",
     "Comparable-transaction (comps) library drawn from the licensed deal "
     "corpus.",
     "Pull precedent transactions to triangulate valuation.",
     ["What did comparable deals trade at?", "Any recent precedents here?",
      "What multiples are defensible?"],
     ["EV/EBITDA", "Exit multiple"], ["ev_to_ebitda", "exit_multiple"],
     ["public_transaction_corpus"],
     "Filters the corpus to comparable transactions; coverage is disclosed "
     "deals only.",
     "Precedent transactions are the market's own valuation evidence.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/vintage-cohorts", "Vintage Cohort Tracker",
     "Tracks performance of entry-year cohorts over time from the corpus.",
     "Follow how cohorts mature, to calibrate j-curve and hold expectations.",
     ["How do cohorts mature?", "Where is my cohort on the j-curve?",
      "Which cohorts have realized?"],
     ["MOIC", "IRR", "Hold period"], ["moic", "irr", "hold_period"],
     ["public_transaction_corpus"],
     "Groups corpus deals into entry-year cohorts and tracks realized metrics; "
     "descriptive.",
     "Cohort maturation sets realistic DPI/TVPI expectations.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/fund-attribution", "Fund Performance Attribution",
     "Decomposes fund IRR into operational, multiple-expansion, and leverage "
     "components.",
     "Show where a fund's returns actually came from.",
     ["What drove this fund's IRR?", "How much was multiple expansion?",
      "Was it operations or leverage?"],
     ["IRR", "MOIC", "Leverage"], ["irr", "moic", "leverage"],
     ["public_transaction_corpus"],
     "Bridges IRR into operational / multiple / leverage contributions from "
     "corpus or entered fund data; descriptive.",
     "Attribution distinguishes repeatable skill from market beta.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/peer-valuation", "Peer Valuation Analyzer",
     "Football-field valuation range from trading comps and precedent "
     "transactions.",
     "Triangulate a defensible valuation range, not a single point.",
     ["What's the valuation range?", "What do comps imply?",
      "Where's the midpoint?"],
     ["EV/EBITDA", "Enterprise value", "EBITDA"],
     ["ev_to_ebitda", "enterprise_value", "ebitda"],
     ["public_transaction_corpus"],
     "Builds a football-field from comp/precedent multiples applied to the "
     "target's metrics; ranges reflect corpus coverage.",
     "A range with method beats a precise number with none.",
     _DC.PUBLIC_BENCHMARK_DATA),
    # Illustrative scenario tools
    ("/capital-pacing", "Capital Call Pacing Model",
     "Models the pace of capital calls and deployment over a fund's life.",
     "Plan commitment pacing so capital is deployed without over/under-calling.",
     ["How fast should we call capital?", "When is the fund fully deployed?",
      "What's the pacing curve?"],
     ["Commitment", "Called %", "Pacing curve"], [], [],
     "Projects a call schedule from entered commitment/deployment assumptions; "
     "illustrative unless populated with a real fund plan.",
     "Pacing errors strand capital or force rushed deals.",
     _DC.MODEL_ESTIMATE),
    ("/reinvestment", "Reinvestment Analyzer",
     "Models reinvesting realized proceeds — recycling and its return impact.",
     "Evaluate whether recycling proceeds improves fund-level returns.",
     ["Should we recycle proceeds?", "What's the return impact?",
      "How much can we reinvest?"],
     ["MOIC", "IRR"], ["moic", "irr"], [],
     "Computes recycled-capital return impact across entered scenarios; "
     "illustrative.",
     "Recycling can lift net returns but tightens liquidity timing.",
     _DC.MODEL_ESTIMATE),
    ("/underwriting-model", "Underwriting Model",
     "Entry-to-exit underwriting — builds MOIC/IRR from entry, growth, "
     "leverage, and exit assumptions.",
     "Underwrite a base-case return from explicit assumptions.",
     ["What return does this underwrite to?", "How sensitive is it?",
      "What has to be true to hit target?"],
     ["MOIC", "IRR", "EV/EBITDA", "Leverage", "EBITDA"],
     ["moic", "irr", "ev_to_ebitda", "leverage", "ebitda"], [],
     "Standard LBO underwriting arithmetic over entered assumptions; "
     "illustrative unless a deal's inputs are supplied.",
     "The base-case underwrite is the spine every other analysis hangs on.",
     _DC.MODEL_ESTIMATE),
    # Workflow trackers (user-entered pipeline / LP data)
    ("/deal-sourcing", "Deal Sourcing Tracker",
     "Proprietary deal-flow / sourcing tracker — leads, stages, and channels.",
     "Manage the top of the funnel: where leads come from and how they "
     "progress.",
     ["What's in the sourcing funnel?", "Which channels produce leads?",
      "What needs follow-up?"],
     ["Lead count", "By channel", "By stage"], [], [],
     "Tracks entered sourcing leads through channels/stages; seed figures are "
     "illustrative until you add your own pipeline.",
     "Proprietary flow is the cheapest, least-competitive deal source.",
     _DC.MIXED),
    ("/deal-origination", "Deal Origination Tracker",
     "M&A origination / pipeline tracker — targets, outreach, and status.",
     "Manage active origination targets and outreach status.",
     ["What's in the origination pipeline?", "Which targets are warm?",
      "What's the next action?"],
     ["Target count", "By status"], [], [],
     "Tracks entered origination targets and outreach; seed figures "
     "illustrative until populated.",
     "Disciplined origination tracking keeps a thesis-driven pipeline alive.",
     _DC.MIXED),
    ("/capital-call", "Capital Call / LP Tracker",
     "Capital-call and LP-communication tracker — calls, distributions, and "
     "notices.",
     "Keep LP capital calls and communications organized and auditable.",
     ["What calls are outstanding?", "What have we distributed?",
      "What's due to LPs?"],
     ["Called", "Distributed", "Outstanding"], [], [],
     "Tracks entered call/distribution records; seed figures illustrative "
     "until populated with the fund's actuals.",
     "Clean LP-capital records are table stakes for fund operations.",
     _DC.MIXED),
]
for (_r, _t, _sd, _pp, _cq, _km, _mids, _dsids, _ml, _why, _dc2) in _PE_TOOLS_3:
    _is_corpus = "public_transaction_corpus" in _dsids
    _is_tracker = _dc2 == _DC.MIXED
    if _is_corpus:
        _inputs = ["Licensed PE deal corpus (public_transaction_corpus); some "
                   "tools also take a selection/filter."]
        _guidance = ["Benchmarks reflect the licensed corpus's disclosed-deal "
                     "coverage, not the full market — descriptive, not a "
                     "forecast."]
        _limits = ["Corpus is a sample of disclosed deals; private/undisclosed "
                   "transactions are absent."]
        _srcs = ["Licensed PE deal corpus (public_transaction_corpus)."]
    elif _is_tracker:
        _inputs = ["Your entered pipeline / LP records; renders illustrative "
                   "seed data until you add your own."]
        _guidance = ["Tracks YOUR entered data; any figures shown before you "
                     "populate it are an illustrative scaffold, not real "
                     "activity."]
        _limits = ["Only as complete as what you enter; not a market dataset."]
        _srcs = ["User-entered pipeline / LP data."]
    else:
        _inputs = ["Scenario assumptions (query parameters); renders an "
                   "illustrative example with no inputs."]
        _guidance = list(_ILLUS_GUIDANCE)
        _limits = ["Deterministic point scenarios, no probability distribution.",
                   "Illustrative assumptions unless overridden via parameters."]
        _srcs = ["None — computed from the entered/illustrative assumptions."]
    _MANUAL.append(_ctx(
        _r, _t,
        short_description=_sd, primary_purpose=_pp, common_questions=_cq,
        inputs=_inputs,
        outputs=["Computed tables/charts for the analysis above."],
        key_metrics=_km, data_sources=_srcs, model_logic_summary=_ml,
        why_it_matters=_why, diligence_use_cases=[_pp],
        interpretation_guidance=_guidance, limitations=_limits,
        related_routes=["/quant-lab", "/sponsor-league", "/return-attribution"],
        metric_ids=_mids, data_source_ids=_dsids,
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=_dc2,
    ))


# ── Financing / tax / fund-structure tools (data_public family, batch 4) ──
# (route, title, short_desc, purpose, common_qs, key_metrics, metric_ids,
#  data_source_ids, model_logic, why, data_conf)
_PE_TOOLS_4 = [
    ("/capital-efficiency", "Capital Efficiency",
     "Corpus-calibrated capital-efficiency benchmarks — return per dollar "
     "invested across the deal corpus.",
     "Benchmark how efficiently capital converts to return vs comparable deals.",
     ["How capital-efficient is this profile?", "What's typical return per "
      "dollar?", "Where does this deal rank?"],
     ["MOIC", "IRR", "EV/EBITDA"], ["moic", "irr", "ev_to_ebitda"],
     ["public_transaction_corpus"],
     "Summarizes corpus return-per-capital metrics into benchmark bands; "
     "descriptive, reflects corpus coverage.",
     "Capital efficiency, not just gross return, is what compounds a fund.",
     _DC.PUBLIC_BENCHMARK_DATA),
    ("/tax-structure", "Tax Structure Analyzer",
     "Models acquisition tax-structure scenarios (asset vs stock, step-up, "
     "entity choice) and their after-tax return impact.",
     "See how deal structure changes after-tax returns before lawyers do.",
     ["Asset or stock deal?", "What's the step-up benefit?", "How does "
      "structure change IRR?"],
     ["After-tax IRR"], ["irr"], [],
     "Computes after-tax return deltas across entered structure assumptions; "
     "illustrative, NOT tax advice.",
     "Structure can swing after-tax returns by hundreds of bps.",
     _DC.MODEL_ESTIMATE),
    ("/tax-structure-analyzer", "Tax Structure Analyzer",
     "Acquisition tax-structure scenario analyzer (asset vs stock, step-up, "
     "entity choice).",
     "Compare tax structures' after-tax return impact.",
     ["Which structure is most tax-efficient?", "What's the step-up worth?",
      "Asset vs stock trade-off?"],
     ["After-tax IRR"], ["irr"], [],
     "Same engine as /tax-structure; computes after-tax deltas from entered "
     "assumptions. Illustrative, NOT tax advice.",
     "Structure choice is a controllable, material return lever.",
     _DC.MODEL_ESTIMATE),
    ("/earnout", "Earnout & Contingent Consideration",
     "Models earnout / contingent-consideration structures and their expected "
     "cost vs the seller's targets.",
     "Quantify what an earnout is likely to cost and how it bridges a "
     "valuation gap.",
     ["What will the earnout cost?", "How likely is it to pay out?",
      "Does it bridge the bid-ask?"],
     ["Enterprise value", "EBITDA"], ["enterprise_value", "ebitda"], [],
     "Computes expected earnout cost across entered targets/probabilities; "
     "illustrative.",
     "Earnouts bridge valuation gaps but create alignment and accounting risk.",
     _DC.MODEL_ESTIMATE),
    ("/cap-structure", "Capital Structure Optimizer",
     "Optimizes the debt/equity mix — leverage, cost of capital, and the "
     "return/risk trade-off.",
     "Find the capital structure that maximizes returns within covenant and "
     "risk limits.",
     ["What's the optimal leverage?", "How much debt can this support?",
      "What's the WACC trade-off?"],
     ["Leverage", "Debt/EBITDA", "EV/EBITDA"],
     ["leverage", "debt", "ev_to_ebitda"], [],
     "Sweeps debt/equity mixes and reports return/risk across entered "
     "assumptions; illustrative.",
     "Structure sets both the return amplification and the downside risk.",
     _DC.MODEL_ESTIMATE),
    ("/capital-schedule", "Capital Schedule",
     "Builds a sources-and-uses / capital deployment schedule for a deal.",
     "Lay out exactly how capital is sourced and deployed at close.",
     ["What are the sources and uses?", "How much equity is needed?",
      "What's the funding schedule?"],
     ["Sources", "Uses", "Equity check"], [], [],
     "Composes a sources-and-uses schedule from entered figures; illustrative "
     "until a deal's terms are supplied.",
     "A clean sources-and-uses is the backbone of the funding plan.",
     _DC.MODEL_ESTIMATE),
    ("/platform-maturity", "Platform Maturity / Exit Readiness",
     "Scores a platform's maturity across operational / commercial / "
     "financial / governance dimensions.",
     "Gauge how built-out a platform is and what's left before exit.",
     ["How mature is this platform?", "What's left to build?", "Is it "
      "exit-ready?"],
     ["Maturity score", "EBITDA margin", "Revenue growth"],
     ["ebitda_margin", "revenue_growth"], [],
     "Weighted maturity scorecard from entered dimension inputs; illustrative "
     "until scored against a real platform.",
     "Maturity gaps are the value-creation runway before exit.",
     _DC.MODEL_ESTIMATE),
    # Trackers (user-entered fund / deal data)
    ("/tax-credits", "Tax Credits / Incentives Tracker",
     "Tracks available tax credits and incentives relevant to a deal/platform.",
     "Keep tax credits and incentives organized so none are left on the table.",
     ["What credits are available?", "What's the incentive value?",
      "What's the filing status?"],
     ["Credit value", "By type"], [], [],
     "Tracks entered credit/incentive records; illustrative seed until "
     "populated. NOT tax advice.",
     "Unclaimed incentives are free return; tracking them is pure upside.",
     _DC.MIXED),
    ("/escrow-earnout", "Escrow & Earnout Tracker",
     "Tracks escrow balances and earnout milestones / payouts post-close.",
     "Monitor escrow releases and earnout milestones so obligations are met "
     "and recoveries claimed.",
     ["What's in escrow?", "When does it release?", "What earnouts are due?"],
     ["Escrow balance", "Earnout milestones"], [], [],
     "Tracks entered escrow/earnout records; illustrative seed until "
     "populated.",
     "Escrow and earnout slip-ups leak real money post-close.",
     _DC.MIXED),
    ("/debt-financing", "Debt Financing Tracker",
     "Tracks LBO debt commitments, lenders, terms, and the financing process.",
     "Manage the debt-financing process from term sheets to commitment.",
     ["Who are the lenders?", "What terms are committed?", "Where's the "
      "financing process?"],
     ["Commitment", "Leverage", "Terms"], ["leverage", "debt"], [],
     "Tracks entered financing commitments/terms; illustrative seed until "
     "populated.",
     "Financing certainty and terms make or break a leveraged deal.",
     _DC.MIXED),
    ("/direct-lending", "Private Credit / Direct Lending Tracker",
     "Tracks direct-lending / private-credit positions, terms, and yields.",
     "Manage a direct-lending book's positions and economics.",
     ["What positions are held?", "What yields are we earning?", "What's "
      "the risk profile?"],
     ["Yield", "Leverage", "Position size"], ["leverage", "debt"], [],
     "Tracks entered credit positions; illustrative seed until populated.",
     "Private credit economics hinge on terms, yield, and downside protection.",
     _DC.MIXED),
    ("/continuation-vehicle", "Continuation Vehicle",
     "Models / tracks a GP-led continuation-vehicle transaction and its "
     "economics.",
     "Evaluate moving an asset into a continuation vehicle and the LP/GP "
     "economics.",
     ["Should we use a CV?", "What are the economics?", "What's the LP "
      "rollover option?"],
     ["MOIC", "IRR", "Carry reset"], ["moic", "irr"], [],
     "Models CV economics from entered assumptions / tracks a live CV; "
     "illustrative seed until populated.",
     "CVs extend hold on winners but carry conflict and pricing scrutiny.",
     _DC.MIXED),
    ("/secondaries-tracker", "Secondaries / GP-Led Tracker",
     "Tracks secondary-market and GP-led transaction opportunities and "
     "pricing.",
     "Manage secondary opportunities and their pricing/discounts.",
     ["What secondaries are available?", "What discounts to NAV?", "What's "
      "the pipeline?"],
     ["NAV discount", "Deal count"], [], [],
     "Tracks entered secondary opportunities; illustrative seed until "
     "populated.",
     "Secondaries can buy quality NAV at a discount and manage liquidity.",
     _DC.MIXED),
    ("/nav-loan-tracker", "NAV Loan / Fund Financing Tracker",
     "Tracks fund-level NAV loans and other fund financing facilities.",
     "Monitor fund-level financing, covenants, and cost.",
     ["What NAV financing is outstanding?", "What's the cost?", "What "
      "covenants apply?"],
     ["Facility size", "Leverage", "Cost"], ["leverage", "debt"], [],
     "Tracks entered fund-financing facilities; illustrative seed until "
     "populated.",
     "NAV loans add fund-level leverage — useful but scrutinized by LPs.",
     _DC.MIXED),
    ("/dpi-tracker", "DPI / Distribution Tracker",
     "Tracks distributions to paid-in (DPI) and realized return progress over "
     "fund life.",
     "Monitor realized returns and DPI as the fund matures.",
     ["What's our DPI?", "How much have we distributed?", "How realized is "
      "the fund?"],
     ["DPI", "Distributions", "MOIC"], ["moic"], [],
     "Tracks entered distribution/contribution records to compute DPI; "
     "illustrative seed until populated.",
     "DPI is the realized-cash truth LPs ultimately judge a fund on.",
     _DC.MIXED),
    ("/lp-reporting", "LP Reporting Dashboard",
     "Assembles LP-facing reporting — performance, holdings, and "
     "distributions.",
     "Produce consistent, LP-ready performance reporting from fund data.",
     ["What do we report to LPs?", "What's portfolio performance?", "What's "
      "been distributed?"],
     ["MOIC", "IRR", "DPI"], ["moic", "irr"], [],
     "Assembles reporting from portfolio/fund data; reflects whatever has "
     "been entered, illustrative until populated.",
     "Clear, consistent LP reporting is core to the GP-LP relationship.",
     _DC.MIXED),
    ("/fundraising", "Fundraising / LP Pipeline Tracker",
     "Tracks the fundraising pipeline — LP prospects, commitments, and close "
     "status.",
     "Manage a fund's capital-raising pipeline to a close.",
     ["Where's the raise?", "Which LPs are committed?", "What's the gap to "
      "target?"],
     ["Committed", "Target", "By LP"], [], [],
     "Tracks entered LP prospects/commitments; illustrative seed until "
     "populated.",
     "A disciplined raise pipeline is how a fund actually closes.",
     _DC.MIXED),
    ("/coinvest-pipeline", "Co-Investment Pipeline Tracker",
     "Tracks co-investment opportunities and LP allocation.",
     "Manage co-invest opportunities and allocate them across LPs.",
     ["What co-invests are available?", "Who gets allocation?", "What's the "
      "pipeline?"],
     ["Opportunity count", "Allocation"], [], [],
     "Tracks entered co-invest opportunities/allocations; illustrative seed "
     "until populated.",
     "Co-invest is a key LP-relationship and fee-economics lever.",
     _DC.MIXED),
    ("/pmi-integration", "PMI / Post-Merger Integration Scorecard",
     "Tracks post-merger integration progress against a scorecard of "
     "workstreams and synergies.",
     "Run the 100-day+ integration: workstreams, owners, and synergy capture.",
     ["How's integration tracking?", "Which workstreams are behind?", "Are "
      "synergies being captured?"],
     ["Integration %", "Synergy capture", "EBITDA impact"],
     ["synergy_estimate", "ebitda"], [],
     "Tracks entered integration workstreams/synergies; illustrative seed "
     "until populated.",
     "Most M&A value is won or lost in integration execution.",
     _DC.MIXED),
]
# Never clobber a route already documented elsewhere (several of these are
# also DATA-REQUIRED pages with their own upload-instruction contexts).
_existing_routes_b4 = {c.route for c in _MANUAL}
for (_r, _t, _sd, _pp, _cq, _km, _mids, _dsids, _ml, _why, _dc2) in _PE_TOOLS_4:
    if _r in _existing_routes_b4:
        continue
    _is_corpus = "public_transaction_corpus" in _dsids
    _is_tracker = _dc2 == _DC.MIXED
    if _is_corpus:
        _inputs = ["Licensed PE deal corpus (public_transaction_corpus)."]
        _guidance = ["Benchmarks reflect the licensed corpus's disclosed-deal "
                     "coverage, not the full market — descriptive."]
        _limits = ["Corpus is a sample of disclosed deals."]
        _srcs = ["Licensed PE deal corpus (public_transaction_corpus)."]
    elif _is_tracker:
        _inputs = ["Your entered fund / deal records; renders illustrative "
                   "seed data until you add your own."]
        _guidance = ["Tracks YOUR entered data; figures shown before you "
                     "populate it are an illustrative scaffold, not real "
                     "activity."]
        _limits = ["Only as complete as what you enter; not a market dataset."]
        _srcs = ["User-entered fund / deal data."]
    else:
        _inputs = ["Scenario assumptions (query parameters); renders an "
                   "illustrative example with no inputs."]
        _guidance = list(_ILLUS_GUIDANCE)
        _limits = ["Deterministic point scenarios, no probability distribution.",
                   "Illustrative assumptions unless overridden via parameters."]
        _srcs = ["None — computed from the entered/illustrative assumptions."]
    _MANUAL.append(_ctx(
        _r, _t,
        short_description=_sd, primary_purpose=_pp, common_questions=_cq,
        inputs=_inputs,
        outputs=["Computed tables/charts for the analysis above."],
        key_metrics=_km, data_sources=_srcs, model_logic_summary=_ml,
        why_it_matters=_why, diligence_use_cases=[_pp],
        interpretation_guidance=_guidance, limitations=_limits,
        related_routes=["/quant-lab", "/lbo-stress", "/lp-dashboard"],
        metric_ids=_mids, data_source_ids=_dsids,
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=_dc2,
    ))


# ── Per-deal model family (/models/<type>/<deal_id>, batch 5) ──────────
# Each renders one section of the selected deal's analysis packet (model
# output over that deal's observed/entered inputs). Parameterized routes; the
# Guide resolves /models/<type>/<deal_id> back to the /models/<type> context.
# (route, title, short_desc, key_metrics, metric_ids, extra_data_source)
_MODEL_FAMILY = [
    ("/models/lbo", "LBO Model", "Leveraged-buyout returns model for the deal "
     "— entry/exit, leverage, and the resulting MOIC/IRR.",
     ["MOIC", "IRR", "Leverage", "EV/EBITDA"],
     ["moic", "irr", "leverage", "ev_to_ebitda", "ebitda"], None),
    ("/models/dcf", "DCF Valuation", "Discounted-cash-flow valuation of the "
     "deal — projected FCF, WACC, terminal value.",
     ["Enterprise value", "EV/EBITDA"],
     ["enterprise_value", "ev_to_ebitda", "ebitda"], None),
    ("/models/returns", "Returns Model", "MOIC/IRR returns bridge for the deal "
     "across the hold.",
     ["MOIC", "IRR", "Hold period"], ["moic", "irr", "hold_period"], None),
    ("/models/waterfall", "Distribution Waterfall", "Carry / distribution "
     "waterfall — how proceeds split between LPs and GP.",
     ["MOIC", "IRR", "Carry"], ["moic", "irr"], None),
    ("/models/bridge", "EBITDA Bridge", "Seven-lever EBITDA value-creation "
     "bridge from entry to exit for the deal.",
     ["EBITDA", "EBITDA bridge", "RCM uplift", "Synergy"],
     ["ebitda", "ebitda_bridge", "rcm_uplift", "synergy_estimate"], None),
    ("/models/debt", "Debt & Covenant Model", "Debt schedule, leverage, and "
     "covenant headroom for the deal.",
     ["Leverage", "Debt/EBITDA", "Covenant cushion"],
     ["leverage", "debt", "covenant_cushion"], None),
    ("/models/financials", "Financial Statements", "Normalized financial "
     "statements view for the deal.",
     ["Revenue", "EBITDA", "EBITDA margin"],
     ["revenue", "ebitda", "ebitda_margin"], None),
    ("/models/predicted", "Predicted KPIs", "Predicted RCM KPI outcomes for "
     "the deal (ridge predictor + conformal interval).",
     ["Denial rate", "Days in AR", "Net collection rate", "Clean claim rate"],
     ["denial_rate", "days_in_ar", "net_collection_rate", "clean_claim_rate"],
     None),
    ("/models/denial", "Denial-Rate Model", "Predicted initial-denial rate for "
     "the deal and its drivers.",
     ["Denial rate"], ["denial_rate"], None),
    ("/models/comparables", "Comparable Deals", "Comparable deals / companies "
     "for the deal, from the licensed corpus.",
     ["Benchmark percentile", "EV/EBITDA"],
     ["benchmark_percentile", "ev_to_ebitda"], "public_transaction_corpus"),
    ("/models/market", "Market Model", "Market context for the deal — size, "
     "growth, and competitive position.",
     ["Revenue", "Benchmark percentile"],
     ["revenue", "benchmark_percentile"], None),
    ("/models/service-lines", "Service-Line Profitability", "Per-service-line "
     "profitability decomposition for the deal.",
     ["Contribution margin", "EBITDA margin"],
     ["provider_contribution_margin", "ebitda_margin"], None),
    ("/models/causal", "Causal Impact", "Causal-inference estimate of an "
     "initiative's impact for the deal (not just correlation).",
     ["RCM uplift", "Value-creation opportunity"],
     ["rcm_uplift", "value_creation_opportunity"], None),
    ("/models/counterfactual", "Counterfactual", "What-if counterfactual "
     "scenario for the deal — outcome under an alternative path.",
     ["EBITDA", "MOIC"], ["ebitda", "moic"], None),
    ("/models/anomalies", "Anomaly Detection", "Statistical anomaly flags on "
     "the deal's data — outliers worth a closer look.",
     ["Risk score"], ["risk_score"], None),
    ("/models/trends", "Trend Forecast", "Temporal trend / forecast of the "
     "deal's key series (Mann-Kendall trend + projection).",
     ["Revenue growth"], ["revenue_growth"], None),
    ("/models/quality", "Model Quality", "Held-out quality metrics for the "
     "deal's models — cross-validated R²/AUC and conformal coverage.",
     ["CV R²/AUC", "Confidence tier"],
     ["model_estimate", "confidence_tier"], None),
    ("/models/importance", "Feature Importance", "Which features drive the "
     "deal's model predictions, ranked.",
     ["Feature importance"], ["model_estimate"], None),
    ("/models/validate", "Model Validation", "Validation / backtest of the "
     "deal's predictive models against held-out data.",
     ["Validation score", "Confidence tier"],
     ["model_estimate", "confidence_tier"], None),
    ("/models/completeness", "Data Completeness", "Data-completeness grade for "
     "the deal — what's present, missing, or imputed.",
     ["Data coverage score"], ["data_coverage_score"], None),
    ("/models/challenge", "Thesis Challenge", "Red-team challenge of the deal "
     "thesis — the bear case and key risks.",
     ["Risk score"], ["risk_score"], None),
    ("/models/questions", "Diligence Questions", "Auto-generated diligence "
     "questions for the deal, prioritized by risk.",
     ["Open questions"], [], None),
    ("/models/memo", "IC / Exit Memo", "Drafted investment-committee / exit "
     "memo for the deal from its packet.",
     ["MOIC", "IRR"], ["moic", "irr"], None),
    ("/models/playbook", "Value-Creation Playbook", "Value-creation playbook "
     "for the deal — the prioritized initiative set.",
     ["Value-creation opportunity", "RCM uplift"],
     ["value_creation_opportunity", "rcm_uplift"], None),
    ("/models/irs990", "IRS 990 Financials", "IRS Form 990 financials view for "
     "the deal (nonprofit / tax-exempt provider).",
     ["Revenue", "EBITDA"], ["revenue", "ebitda"], "irs_form_990"),
]
_existing_routes_b5 = {c.route for c in _MANUAL}
for (_r, _t, _sd, _km, _mids, _extra_ds) in _MODEL_FAMILY:
    if _r in _existing_routes_b5:
        continue
    _dsids = ["analysis_run", "model_output"] + ([_extra_ds] if _extra_ds else [])
    _MANUAL.append(_ctx(
        _r, _t,
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description=_sd,
        primary_purpose=f"Give the deal team the {_t.lower()} for a specific "
        "deal, built from its analysis packet, as one section of the modeling "
        "workbench.",
        intended_users=["Deal team analyzing a specific deal."],
        common_questions=[f"What does the {_t.lower()} show for this deal?",
                          "What assumptions drive it?",
                          "How confident is this output?"],
        inputs=["The selected deal's analysis packet (deal_id in the URL) — "
                "model output over that deal's observed / entered inputs."],
        outputs=[f"The {_t.lower()} for the selected deal."],
        key_metrics=_km,
        data_sources=["The deal's stored analysis packet (model output)."]
        + (["IRS Form 990 (nonprofit financials)."] if _extra_ds == "irs_form_990"
           else ["Licensed PE deal corpus."] if _extra_ds else []),
        model_logic_summary=f"Renders the {_t.lower()} section of the deal's "
        "analysis packet (rcm_mc/analysis), which is built once per deal and "
        "cached; figures are model output over that deal's inputs, not "
        "realized results.",
        why_it_matters="Per-deal models turn the universe-level analytics into "
        "a concrete underwriting view for the deal in hand.",
        diligence_use_cases=[f"Reviewing the {_t.lower()} during diligence / "
                            "IC prep for a specific deal."],
        interpretation_guidance=[
            "Outputs are model estimates for THIS deal from its packet inputs, "
            "not realized or audited figures.",
            "Requires the deal to have a built analysis packet; otherwise the "
            "page prompts to build one."],
        limitations=[
            "Only as good as the deal's input data and the packet's "
            "assumptions.",
            "Per-deal — needs a deal_id; the bare route has no deal context."],
        related_routes=["/analysis", "/quant-lab", "/diligence"],
        metric_ids=_mids,
        data_source_ids=_dsids,
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ))


# ── Analytics / diligence / corpus pages (batch 6) ─────────────────────
# Heterogeneous real pages. bucket controls inputs/guidance/limitations:
#   "corpus"=licensed deal corpus benchmark · "model"=illustrative scenario ·
#   "user"=user-entered/ingested data · "deal"=per-deal packet model output.
# (route, title, short_desc, purpose, common_qs, key_metrics, metric_ids,
#  data_source_ids, model_logic, why, data_conf, bucket)
_BATCH6 = [
    ("/diligence/comparable-outcomes", "Comparable Outcomes",
     "Benchmarks a deal against comparable-deal outcomes from the licensed "
     "corpus.",
     "Ground an outcome expectation in how genuinely comparable deals fared.",
     ["How did comparable deals do?", "What outcome is realistic here?",
      "Where does this sit vs peers?"],
     ["Benchmark percentile", "MOIC", "EV/EBITDA"],
     ["benchmark_percentile", "moic", "ev_to_ebitda"],
     ["public_transaction_corpus"],
     "Matches the deal to corpus comparables and summarizes their realized "
     "outcomes; descriptive, reflects corpus coverage.",
     "Comparable outcomes are the empirical prior for an underwrite.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/backtester", "Value-Creation Backtester",
     "Backtests value-creation theses against realized corpus outcomes.",
     "Check whether a value-creation thesis has actually worked in comparable "
     "deals before betting on it.",
     ["Has this thesis worked before?", "What's the historical hit rate?",
      "Which levers backtest well?"],
     ["MOIC", "Value-creation opportunity", "Hit rate"],
     ["moic", "value_creation_opportunity"], ["public_transaction_corpus"],
     "Replays value-creation theses over corpus deals and reports realized "
     "outcomes; descriptive backtest, not a forecast.",
     "A thesis that never backtested is a hope, not a plan.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/base-rates", "Base-Rate Engine",
     "Outcome base rates (frequencies) from the deal corpus — how often "
     "things actually happen.",
     "Anchor judgment in base rates instead of the inside view of one deal.",
     ["What's the base rate for this outcome?", "How often does this work?",
      "What are the odds historically?"],
     ["Outcome frequency", "MOIC", "Benchmark percentile"],
     ["moic", "irr", "benchmark_percentile"], ["public_transaction_corpus"],
     "Computes empirical outcome frequencies across corpus deals; descriptive.",
     "Base rates are the single best antidote to deal-team optimism.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/portfolio-sim", "Portfolio Scenario Simulator",
     "Simulates portfolio-level outcomes by drawing from corpus return "
     "distributions.",
     "See the range of fund-level outcomes a portfolio construction could "
     "produce.",
     ["What's the portfolio outcome range?", "What's the downside?",
      "How does construction change the distribution?"],
     ["MOIC", "IRR", "Downside"], ["moic", "irr"],
     ["public_transaction_corpus"],
     "Monte-Carlo draws from corpus return distributions to build a "
     "portfolio outcome distribution; reflects corpus coverage.",
     "Fund outcomes are a distribution, not a point — sizing the tails "
     "matters.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/corpus-coverage", "Corpus Coverage Report",
     "Data-completeness and field-coverage report for the licensed deal "
     "corpus.",
     "Show how complete and trustworthy the corpus is, field by field, before "
     "anyone relies on it.",
     ["How complete is the corpus?", "Which fields are sparse?", "Can I trust "
      "this benchmark?"],
     ["Field coverage %", "Data coverage score"], ["data_coverage_score"],
     ["public_transaction_corpus"],
     "Computes per-field non-null/quality rates across the corpus; this is a "
     "data-quality surface, not an analytic one.",
     "A benchmark is only as good as the coverage behind it; this makes the "
     "gaps explicit.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/corpus-dashboard", "Corpus Intelligence Dashboard",
     "Overview dashboard of the licensed deal corpus — counts, sectors, "
     "sponsors, and return summaries.",
     "Give a single read on what the corpus contains and what it says.",
     ["What's in the corpus?", "What does it say about the market?", "Where's "
      "the coverage strong?"],
     ["Deal count", "MOIC", "IRR", "EV/EBITDA"],
     ["moic", "irr", "ev_to_ebitda"], ["public_transaction_corpus"],
     "Aggregates corpus counts and return summaries; descriptive.",
     "The corpus is the empirical backbone under the benchmarking tools.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/diligence/snapshot", "Snapshot Ingestion",
     "Upload UI for the V2 healthcare data snapshot (835/837 claims) — "
     "ingestion, validation, and a data-quality summary.",
     "Turn an uploaded claims/financial snapshot into normalized, "
     "quality-checked records the rest of diligence runs on.",
     ["How do I upload a snapshot?", "What's the data quality?", "What rows "
      "failed validation?"],
     ["Rows ingested", "Valid/invalid", "Data quality"], [],
     ["edi_835", "edi_837"],
     "Parses, validates, normalizes and summarizes an uploaded snapshot "
     "(rcm_mc/diligence ingestion); surfaces row-level errors/warnings rather "
     "than hiding them.",
     "Clean, versioned, quality-scored ingestion is the foundation every "
     "downstream module depends on.",
     _DC.USER_ENTERED_DATA, "user"),
    ("/ic-memo-gen", "IC Memo Generator",
     "Generates a standardized investment-committee memo from a deal's "
     "analysis packet.",
     "Produce a consistent, packet-backed IC memo draft instead of a "
     "from-scratch document.",
     ["Draft the IC memo", "What goes in the memo?", "What's missing for IC?"],
     ["MOIC", "IRR"], ["moic", "irr"], ["analysis_run"],
     "Composes memo sections from the deal's packet; surfaces missing data "
     "rather than inventing conclusions.",
     "A standardized, evidence-linked memo speeds and de-risks IC.",
     _DC.MIXED, "deal"),
    ("/corpus-ic-memo", "Corpus IC Memo",
     "IC memo draft enriched with corpus benchmarks for the deal.",
     "Draft an IC memo that situates the deal against comparable corpus "
     "evidence.",
     ["Draft a benchmarked IC memo", "How does this compare to the corpus?",
      "What's the peer context?"],
     ["MOIC", "IRR", "Benchmark percentile"],
     ["moic", "irr"], ["analysis_run", "public_transaction_corpus"],
     "Composes a memo from the deal's packet plus corpus comparables; "
     "benchmarks reflect corpus coverage.",
     "Peer-anchored memos are harder to wave away at IC.",
     _DC.MIXED, "deal"),
    ("/ic-memo", "IC Memo",
     "Investment-committee memo view for a deal.",
     "Review the IC memo for a deal in one place.",
     ["Show the IC memo", "What's the recommendation?", "What are the risks?"],
     ["MOIC", "IRR"], ["moic", "irr"], ["analysis_run"],
     "Renders the deal's IC memo from its packet; surfaces gaps honestly.",
     "The IC memo is where the thesis is made or broken.",
     _DC.MIXED, "deal"),
    ("/surrogate", "Surrogate Model",
     "A fast surrogate that approximates the Monte-Carlo EBITDA-drag without "
     "the full simulation.",
     "Get an instant approximate read where running the full MC would be too "
     "slow.",
     ["What's the quick EBITDA-drag estimate?", "How close is it to the full "
      "MC?", "When should I run the real sim?"],
     ["EBITDA drag (approx)"], [], [],
     "A trained/stubbed surrogate approximating the MC's mean output; an "
     "approximation, not the full simulation — use the MC for decisions.",
     "Surrogates make interactive what-ifs cheap; the MC remains the "
     "decision-grade tool.",
     _DC.MODEL_ESTIMATE, "model"),
    ("/pressure", "Pressure Test",
     "Stress / target-assessment that pressure-tests a deal against adverse "
     "assumptions.",
     "See where a deal breaks under stress before committing capital.",
     ["How does this hold up under stress?", "What breaks the deal?",
      "Where's the fragility?"],
     ["EBITDA under stress", "Risk score"], ["ebitda", "risk_score"], [],
     "Applies adverse-scenario shocks to entered assumptions and reports the "
     "outcome; illustrative unless deal inputs are supplied.",
     "A thesis you haven't stressed is a thesis you don't understand.",
     _DC.MODEL_ESTIMATE, "model"),
    ("/demand-forecast", "Demand Forecast",
     "Projects future demand / volume from entered trend assumptions.",
     "Stress-test the volume assumptions a revenue thesis rests on.",
     ["What demand is assumed?", "How sensitive is revenue to volume?",
      "Is the growth realistic?"],
     ["Revenue growth", "Volume"], ["revenue_growth"], [],
     "Projects demand from entered trend/seasonality assumptions; "
     "illustrative.",
     "Volume assumptions silently drive most revenue models.",
     _DC.MODEL_ESTIMATE, "model"),
    ("/exit-timing", "Exit Timing & Buyer Fit",
     "Models exit timing and buyer-type fit (strategic vs sponsor vs "
     "public).",
     "Think about when to exit and to whom, not just at what multiple.",
     ["When should we exit?", "Who's the natural buyer?", "Strategic or "
      "sponsor exit?"],
     ["Exit multiple", "MOIC", "Buyer fit"], ["exit_multiple", "moic"], [],
     "Scores exit timing/buyer fit from entered assumptions; illustrative.",
     "The right buyer at the right time can out-matter the entry price.",
     _DC.MODEL_ESTIMATE, "model"),
    ("/hold", "Hold-Period Dashboard",
     "Tracks portfolio holdings by hold period — age, value progression, and "
     "exit readiness.",
     "See where each holding is in its hold and which are nearing exit.",
     ["How long have we held each deal?", "Which are near exit?", "How's "
      "value progressing?"],
     ["Hold period", "MOIC", "IRR"], ["hold_period", "moic", "irr"],
     ["portfolio_snapshot"],
     "Reads portfolio holdings and computes hold age / value progression from "
     "stored snapshots.",
     "Hold discipline — not holding winners too short or losers too long — "
     "drives realized returns.",
     _DC.MIXED, "deal"),
    ("/value-tracker", "Value Creation Tracker",
     "Tracks actual vs plan, lever by lever, for value-creation initiatives.",
     "Hold post-close execution accountable against the value-creation plan.",
     ["Are we hitting the plan?", "Which levers are behind?", "What's the "
      "EBITDA gap to plan?"],
     ["Value-creation opportunity", "EBITDA", "Actual vs plan"],
     ["value_creation_opportunity", "ebitda"], ["monthly_actuals"],
     "Compares entered monthly actuals against the plan per lever; only "
     "meaningful once actuals are loaded.",
     "Plans don't create value; tracked execution against them does.",
     _DC.USER_ENTERED_DATA, "user"),
]
_existing_b6 = {c.route for c in _MANUAL}
for (_r, _t, _sd, _pp, _cq, _km, _mids, _dsids, _ml, _why, _dc2, _bucket) in _BATCH6:
    if _r in _existing_b6:
        continue
    if _bucket == "corpus":
        _inputs = ["Licensed PE deal corpus (public_transaction_corpus); some "
                   "tools also take a deal/selection."]
        _guidance = ["Benchmarks reflect the corpus's disclosed-deal coverage, "
                     "not the full market — descriptive, not a forecast."]
        _limits = ["Corpus is a sample of disclosed deals."]
        _srcs = ["Licensed PE deal corpus (public_transaction_corpus)."]
    elif _bucket == "user":
        _inputs = ["Your uploaded / entered data; until you provide it the "
                   "page shows an illustrative scaffold."]
        _guidance = ["Runs on YOUR data — figures before you upload are an "
                     "illustrative scaffold, not real values."]
        _limits = ["Only as complete/correct as the data you provide."]
        _srcs = ["User-uploaded / entered data."]
    elif _bucket == "deal":
        _inputs = ["The selected deal's analysis packet / portfolio data "
                   "(model output over its inputs)."]
        _guidance = ["Outputs are model estimates / tracked figures for the "
                     "deal, not realized or audited results.",
                     "Requires a built analysis packet for the deal."]
        _limits = ["Only as good as the deal's inputs and packet assumptions."]
        _srcs = ["The deal's stored analysis packet / portfolio snapshots."]
    else:  # model
        _inputs = ["Scenario assumptions (query parameters); illustrative "
                   "example with no inputs."]
        _guidance = list(_ILLUS_GUIDANCE)
        _limits = ["Deterministic point scenarios, no probability distribution.",
                   "Illustrative assumptions unless overridden."]
        _srcs = ["None — computed from the entered/illustrative assumptions."]
    _MANUAL.append(_ctx(
        _r, _t,
        short_description=_sd, primary_purpose=_pp, common_questions=_cq,
        inputs=_inputs,
        outputs=["Computed tables/charts for the analysis above."],
        key_metrics=_km, data_sources=_srcs, model_logic_summary=_ml,
        why_it_matters=_why, diligence_use_cases=[_pp],
        interpretation_guidance=_guidance, limitations=_limits,
        related_routes=["/quant-lab", "/analysis", "/corpus-dashboard"],
        metric_ids=_mids, data_source_ids=_dsids,
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=_dc2,
    ))


# ── Sector / specialty analytic tools (batch 7) ────────────────────────
# (route, title, short_desc, common_qs, key_metrics, metric_ids, why, bucket)
# bucket: "model" = illustrative analyzer · "user" = entered-data tracker.
_BATCH7 = [
    ("/biosimilars", "Biosimilars Opportunity Analyzer",
     "Models the savings opportunity from biosimilar substitution for a "
     "drug-spend base.",
     ["What's the biosimilar savings?", "Which molecules switch?",
      "How big is the opportunity?"],
     ["Savings opportunity"], [],
     "Biosimilar substitution is a concrete, near-term drug-cost lever.", "model"),
    ("/drug-pricing-340b", "340B Drug Pricing Analyzer",
     "Estimates 340B program savings vs non-340B acquisition cost.",
     ["What's the 340B savings?", "Which sites qualify?", "How much margin "
      "does 340B add?"],
     ["340B savings"], [],
     "340B economics materially change pharmacy margin for eligible providers.",
     "model"),
    ("/reit-analyzer", "REIT / Sale-Leaseback Analyzer",
     "Models a healthcare sale-leaseback / REIT scenario — cap rate, proceeds, "
     "and rent drag.",
     ["What does a sale-leaseback yield?", "What's the rent drag on EBITDA?",
      "Is the cap rate attractive?"],
     ["Proceeds", "EBITDA", "Enterprise value"], ["ebitda", "enterprise_value"],
     "Real-estate monetization can fund a deal but burdens future EBITDA.",
     "model"),
    ("/trial-site-econ", "Clinical Trial Site Economics",
     "Models the economics of running clinical-trial sites — per-site revenue "
     "and contribution.",
     ["What does a trial site earn?", "Is the contribution positive?",
      "How many sites to break even?"],
     ["Revenue/site", "Contribution margin"],
     ["revenue", "provider_contribution_margin"],
     "Trial revenue is a distinct, often-overlooked provider income stream.",
     "model"),
    ("/specialty-benchmarks", "Specialty Benchmarks Library",
     "A library of operating benchmarks by clinical specialty.",
     ["What are typical margins for this specialty?", "How does this specialty "
      "benchmark?", "What's the productivity norm?"],
     ["EBITDA margin", "Revenue"], ["ebitda_margin", "revenue"],
     "Specialty norms anchor what 'good' looks like for a target.", "model"),
    ("/phys-comp-plan", "Physician Compensation Plan Designer",
     "Models physician compensation plan structures (wRVU, base+incentive) and "
     "their cost.",
     ["What does this comp plan cost?", "Is comp aligned to production?",
      "How does wRVU-based pay compare?"],
     ["Comp-to-collections", "Productivity"],
     ["compensation_to_collections", "provider_productivity"],
     "Physician comp is the largest cost line and the key retention lever.",
     "model"),
    ("/workforce-planning", "Workforce Planning Analyzer",
     "Models staffing levels, labor cost, and workforce gaps.",
     ["What's the labor cost ratio?", "Where are staffing gaps?", "What's the "
      "right staffing level?"],
     ["Labor cost ratio", "FTE gap"], ["labor_cost_ratio"],
     "Labor is the dominant operating cost in provider businesses.", "model"),
    ("/esg-dashboard", "ESG Dashboard",
     "Summarizes ESG metrics and scores for a platform.",
     ["What's the ESG profile?", "Where are the ESG gaps?", "What do LPs "
      "want here?"],
     ["ESG score"], [],
     "ESG posture increasingly affects LP appetite and exit buyer lists.",
     "model"),
    ("/fraud-detection", "Fraud / Waste / Abuse Detection",
     "Flags potential fraud, waste, and abuse patterns in claims/operations "
     "data.",
     ["Any FWA red flags?", "Which patterns look anomalous?", "What needs a "
      "compliance look?"],
     ["Risk score", "Flag count"], ["risk_score"],
     "Undetected FWA is a compliance and valuation landmine.", "model"),
    ("/geo-market", "Geographic Market Analyzer",
     "Analyzes a geographic market — demand, competition, and positioning.",
     ["What's this market like?", "Who competes here?", "Is there room to "
      "grow?"],
     ["Market size", "Competitor count"], [],
     "Geography shapes demand, competition, and reimbursement.", "model"),
    # Trackers (user-entered)
    ("/denovo-expansion", "De Novo Expansion Tracker",
     "Tracks de novo (greenfield) site openings — pipeline, ramp, and "
     "economics.",
     ["What de novos are planned?", "How are they ramping?", "What's the "
      "expansion economics?"],
     ["Site count", "Revenue", "Ramp"], ["revenue", "ebitda_margin"],
     "Organic de novo growth complements M&A in a platform thesis.", "user"),
    ("/tracker-340b", "340B Pharmacy Program Tracker",
     "Tracks 340B program participation, contract pharmacies, and compliance.",
     ["What's our 340B footprint?", "Which contract pharmacies?", "Any "
      "compliance gaps?"],
     ["Site count", "Savings"], [],
     "340B compliance is high-scrutiny; tracking it protects the savings.",
     "user"),
    ("/physician-labor", "Physician Labor Market Tracker",
     "Tracks physician supply, attrition, and recruiting in target markets.",
     ["What's physician attrition?", "Is the market tight?", "What's the "
      "recruiting pipeline?"],
     ["Attrition", "Productivity"],
     ["physician_attrition", "provider_productivity"],
     "Physician supply/retention is a first-order risk in provider deals.",
     "user"),
    ("/hospital-anchor", "Hospital Anchor Contract Tracker",
     "Tracks anchor hospital / health-system contracts and their terms.",
     ["What anchor contracts exist?", "When do they renew?", "What's the "
      "concentration risk?"],
     ["Contract count", "Concentration"], [],
     "Anchor-contract concentration is a major revenue-durability risk.",
     "user"),
    ("/ma-star", "Medicare Advantage / Star Ratings Tracker",
     "Tracks Medicare Advantage Star ratings and their revenue impact.",
     ["What are the Star ratings?", "How do they affect revenue?", "Where's "
      "the bonus risk?"],
     ["Star rating", "Bonus impact"], [],
     "Star ratings drive MA bonus payments and plan competitiveness.", "user"),
    ("/esg-impact", "ESG / Impact Reporting Tracker",
     "Tracks ESG / impact metrics and reporting commitments over time.",
     ["What ESG do we report?", "Are we hitting commitments?", "What's due "
      "to LPs?"],
     ["ESG metrics", "Commitments"], [],
     "Impact reporting is increasingly an LP requirement, not a nicety.",
     "user"),
]
_existing_b7 = {c.route for c in _MANUAL}
for (_r, _t, _sd, _cq, _km, _mids, _why, _bucket) in _BATCH7:
    if _r in _existing_b7:
        continue
    if _bucket == "user":
        _inputs = ["Your entered records; illustrative scaffold until "
                   "populated."]
        _guidance = ["Tracks YOUR entered data; figures before you populate it "
                     "are an illustrative scaffold, not real activity."]
        _limits = ["Only as complete as what you enter."]
        _srcs = ["User-entered data."]
        _dc2 = _DC.MIXED
    else:
        _inputs = ["Scenario assumptions (query parameters); illustrative "
                   "example with no inputs."]
        _guidance = list(_ILLUS_GUIDANCE)
        _limits = ["Deterministic point scenarios, no probability distribution.",
                   "Illustrative assumptions unless overridden."]
        _srcs = ["None — computed from the entered/illustrative assumptions."]
        _dc2 = _DC.MODEL_ESTIMATE
    _MANUAL.append(_ctx(
        _r, _t,
        short_description=_sd,
        primary_purpose=_sd,
        common_questions=_cq,
        inputs=_inputs,
        outputs=["Computed tables/charts for the analysis above."],
        key_metrics=_km, data_sources=_srcs,
        model_logic_summary=("Computes the analysis above from entered/"
                             "illustrative assumptions (data_public tool); "
                             "no live external data."),
        why_it_matters=_why, diligence_use_cases=[_sd],
        interpretation_guidance=_guidance, limitations=_limits,
        related_routes=["/quant-lab", "/verticals", "/industry"],
        metric_ids=_mids, data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=_dc2,
    ))


# ── Final coverage: analytic _route_ pages + system surfaces (batch 8) ──
# Analytic/diligence pages (real contexts). bucket: corpus/model/deal.
_BATCH8_ANALYTIC = [
    ("/analysis", "Analysis Landing", PageContextCategory.DILIGENCE_WORKSPACE,
     "Hub for all per-deal analytical tools — links into a deal's analysis "
     "packet sections.",
     ["What can I analyze for this deal?", "Where's the LBO/DCF/bridge?",
      "How do I build a packet?"],
     ["MOIC", "IRR", "EBITDA"], ["moic", "irr", "ebitda"],
     ["analysis_run"],
     "Navigation hub over the deal's analysis packet (rcm_mc/analysis); the "
     "per-model views live under /models/<type>/<deal_id>.",
     "One entry point to every model keeps deal analysis coherent.",
     _DC.MIXED, "deal"),
    ("/ml-insights", "ML Insights", PageContextCategory.RESEARCH_BACKTESTING,
     "Machine-learning analysis over the public hospital universe — predicted "
     "KPIs and drivers.",
     ["What does ML say about this universe?", "Which features drive "
      "outcomes?", "How confident are the predictions?"],
     ["Predicted KPIs", "Feature importance"],
     ["denial_rate", "operating_margin", "model_estimate"], ["cms_hcris"],
     "Runs the ML stack (ridge/conformal, feature importance) over HCRIS; "
     "outputs are model estimates with honest confidence tiers.",
     "ML surfaces patterns across thousands of providers a human can't eyeball.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/model-validation", "Model Validation",
     PageContextCategory.RESEARCH_BACKTESTING,
     "Validation dashboard for the predictive models — held-out accuracy, "
     "calibration, and drift.",
     ["Are the models accurate?", "What's the held-out error?", "Are "
      "predictions calibrated?"],
     ["CV R²/AUC", "Calibration", "Confidence tier"],
     ["model_estimate", "confidence_tier"], ["cms_hcris"],
     "Reports cross-validated/held-out metrics for the models; numbers are "
     "out-of-sample, not in-sample, so they don't overstate accuracy.",
     "A model you haven't validated out-of-sample is a model you can't trust.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/value-creation", "Value Creation",
     PageContextCategory.PORTFOLIO_LP,
     "Value-creation view — initiative impact and progress toward the EBITDA "
     "plan.",
     ["What value are we creating?", "Which levers matter most?", "Are we on "
      "plan?"],
     ["Value-creation opportunity", "EBITDA"],
     ["value_creation_opportunity", "ebitda"], ["monthly_actuals"],
     "Aggregates initiative impact vs plan; meaningful once a deal's plan and "
     "actuals are loaded.",
     "Tracked value creation is where the return thesis becomes real.",
     _DC.MIXED, "deal"),
    ("/underwriting", "Underwriting",
     PageContextCategory.DILIGENCE_WORKSPACE,
     "Underwriting view — base-case return from entry, growth, leverage, and "
     "exit assumptions.",
     ["What does this underwrite to?", "What has to be true?", "How sensitive "
      "is the return?"],
     ["MOIC", "IRR", "EV/EBITDA", "Leverage"],
     ["moic", "irr", "ev_to_ebitda", "leverage"], [],
     "LBO underwriting arithmetic over entered assumptions; illustrative "
     "unless a deal's inputs are supplied.",
     "The base-case underwrite is the spine of the investment decision.",
     _DC.MODEL_ESTIMATE, "model"),
    ("/scenario-mc", "Scenario Monte Carlo",
     PageContextCategory.RESEARCH_BACKTESTING,
     "Monte-Carlo scenario analyzer — outcome distribution under stochastic "
     "assumptions.",
     ["What's the outcome distribution?", "What's the P10/P90?", "How risky "
      "is this scenario?"],
     ["EBITDA distribution", "P10/P50/P90"], ["ebitda", "moic"], [],
     "Draws many scenarios from entered distributions and reports the outcome "
     "spread; illustrative unless deal inputs are supplied.",
     "A distribution shows the risk a single point estimate hides.",
     _DC.MODEL_ESTIMATE, "model"),
    ("/diligence/synthesis", "Diligence Synthesis",
     PageContextCategory.DILIGENCE_WORKSPACE,
     "Synthesizes a deal's diligence findings into a thesis-level view — "
     "strengths, risks, and open questions.",
     ["What's the diligence synthesis?", "What are the key risks?", "What's "
      "still open?"],
     ["Risk score", "Open questions"], ["risk_score"], ["analysis_run"],
     "Composes findings from the deal's packet into a synthesis; surfaces "
     "gaps rather than papering over them.",
     "Synthesis turns scattered findings into an IC-ready point of view.",
     _DC.MIXED, "deal"),
    ("/diligence/sponsor-detail", "Sponsor Detail",
     PageContextCategory.DILIGENCE_WORKSPACE,
     "Single-sponsor drill-down — a sponsor's deal history and performance "
     "from the corpus.",
     ["What's this sponsor's track record?", "What have they done in this "
      "sector?", "How do they perform?"],
     ["MOIC", "IRR", "Deal count"], ["moic", "irr"],
     ["public_transaction_corpus"],
     "Filters the corpus to one sponsor and summarizes their realized record; "
     "reflects corpus coverage.",
     "Sponsor track record shapes competition and co-invest decisions.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/diligence/regulatory-calendar", "Regulatory Calendar",
     PageContextCategory.RESEARCH_BACKTESTING,
     "Regulatory calendar with thesis kill-switch flags — upcoming rule "
     "changes that could break a thesis.",
     ["What regulation is coming?", "Could a rule break this thesis?", "What "
      "should we watch?"],
     ["Upcoming rules", "Kill-switch flags"], [],
     ["regulatory_calendar_sources"],
     "Curated regulatory events mapped to thesis-risk flags from public "
     "rulemaking sources.",
     "A single CMS rule can erase a thesis; watching the calendar is risk "
     "management.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/diligence-checklist", "Diligence Checklist",
     PageContextCategory.DILIGENCE_WORKSPACE,
     "Diligence checklist dashboard — workstreams, status, owners, and "
     "evidence.",
     ["What's left to diligence?", "What's blocked?", "Who owns what?"],
     ["Items complete", "By status"], [], ["checklist_state"],
     "Tracks entered checklist items through status/owner; reflects what the "
     "team has populated.",
     "A live checklist is how a deal team avoids diligence gaps.",
     _DC.MIXED, "deal"),
    ("/diligence/ic-memo", "Diligence IC Memo",
     PageContextCategory.DILIGENCE_WORKSPACE,
     "IC memo view within the diligence workspace for a deal.",
     ["Show the IC memo", "What's the recommendation?", "What's missing?"],
     ["MOIC", "IRR"], ["moic", "irr"], ["analysis_run"],
     "Renders the deal's IC memo from its packet; surfaces gaps honestly.",
     "The IC memo is where the diligence lands as a decision.",
     _DC.MIXED, "deal"),
    ("/calibration", "Prior Calibration",
     PageContextCategory.LIBRARY_REFERENCE,
     "Per-payer prior-calibration view — the Bayesian priors the models shrink "
     "thin data toward.",
     ["What priors does the model use?", "How are priors calibrated?", "Why "
      "this prior for this payer?"],
     ["Prior mean", "Prior strength"], ["benchmark_percentile"],
     ["benchmark_prior"],
     "Shows the calibrated priors (rcm_mc calibration) by payer that the "
     "Bayesian layer uses; reference, not a per-deal output.",
     "Transparent priors are what make the Bayesian estimates defensible.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/portfolio-analytics", "Deal Corpus Analytics",
     PageContextCategory.RESEARCH_BACKTESTING,
     "Analytics across the licensed deal corpus — distributions, drivers, and "
     "cross-cuts.",
     ["What does the corpus say overall?", "What drives returns?", "How do "
      "cuts compare?"],
     ["MOIC", "IRR", "EV/EBITDA"], ["moic", "irr", "ev_to_ebitda"],
     ["public_transaction_corpus"],
     "Cross-sectional analytics over the corpus; descriptive, reflects "
     "coverage.",
     "Corpus-wide analytics turn a deal database into market intelligence.",
     _DC.PUBLIC_BENCHMARK_DATA, "corpus"),
    ("/variance", "Variance Drill-Down",
     PageContextCategory.PORTFOLIO_LP,
     "Actual-vs-plan / actual-vs-benchmark variance drill-down for portfolio "
     "deals.",
     ["Where are we off plan?", "What's driving the variance?", "Which deals "
      "are behind?"],
     ["Variance", "EBITDA", "Actual vs plan"], ["ebitda"],
     ["monthly_actuals", "portfolio_snapshot"],
     "Computes variance between entered actuals and plan/benchmark from stored "
     "snapshots; meaningful once actuals are loaded.",
     "Variance is the early-warning signal that a thesis is slipping.",
     _DC.MIXED, "deal"),
]
_existing_b8 = {c.route for c in _MANUAL}
for (_r, _t, _cat, _sd, _cq, _km, _mids, _dsids, _ml, _why, _dc2, _bucket) in _BATCH8_ANALYTIC:
    if _r in _existing_b8:
        continue
    if _bucket == "corpus":
        _inputs = ["Licensed PE deal corpus / public data; some views take a "
                   "selection."]
        _guidance = ["Descriptive — reflects the corpus/public-data coverage, "
                     "not a forecast or the full market."]
        _limits = ["Coverage-limited; descriptive only."]
    elif _bucket == "deal":
        _inputs = ["The selected deal's analysis packet / entered data."]
        _guidance = ["Outputs are model estimates / tracked figures for the "
                     "deal, not realized results; needs a built packet / "
                     "loaded actuals."]
        _limits = ["Only as good as the deal's inputs and packet assumptions."]
    else:
        _inputs = ["Scenario assumptions (query parameters); illustrative "
                   "with no inputs."]
        _guidance = list(_ILLUS_GUIDANCE)
        _limits = ["Deterministic point scenarios; illustrative unless "
                   "overridden."]
    _MANUAL.append(_ctx(
        _r, _t, category=_cat,
        short_description=_sd, primary_purpose=_sd, common_questions=_cq,
        inputs=_inputs, outputs=["Computed tables/charts for the analysis."],
        key_metrics=_km, data_sources=["See data_source_ids."],
        model_logic_summary=_ml, why_it_matters=_why,
        diligence_use_cases=[_sd], interpretation_guidance=_guidance,
        limitations=_limits,
        related_routes=["/quant-lab", "/analysis", "/corpus-dashboard"],
        metric_ids=_mids, data_source_ids=_dsids,
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=_dc2,
    ))

# System / utility surfaces — concise, honest contexts (not analytic).
# (route, title, category, short_desc, common_qs)
_SYS = PageContextCategory.ADMIN_SYSTEM
_HOME = PageContextCategory.HOME_OPERATIONS
_BATCH8_SYSTEM = [
    ("/settings", _SYS, "Settings — workspace and application preferences.",
     ["How do I change settings?", "Where are my preferences?"]),
    ("/settings/ai", _SYS, "AI / Guide settings — controls for the local "
     "Ollama Guide and RAG (enable, model, index).",
     ["How do I configure the Guide?", "Which model does the assistant use?"]),
    ("/settings/workspace", _SYS, "Workspace-mode settings — switch between PE "
     "Partner and Chartis Consulting interface modes.",
     ["How do I switch workspace mode?", "What does PE Partner mode change?"]),
    ("/jobs", _SYS, "Background job queue — status of queued/running simulation "
     "and analysis jobs.",
     ["What jobs are running?", "Did my simulation finish?"]),
    ("/runs", _SYS, "Simulation run history — past Monte-Carlo / analysis runs "
     "with parameters and results.",
     ["What runs have I done?", "Can I re-open a past run?"]),
    ("/cli-runs", _SYS, "CLI run history — records of analyses launched via the "
     "rcm-mc command line.",
     ["What CLI runs happened?", "What did the cron jobs do?"]),
    ("/ops", _SYS, "Operations / system status surface for the deployment.",
     ["Is the system healthy?", "What's the operational status?"]),
    ("/outputs", _SYS, "Generated outputs index — exports, reports, and "
     "artifacts produced by the app.",
     ["Where are my exports?", "What outputs were generated?"]),
    ("/search", _HOME, "Global search across deals, hospitals, and routes.",
     ["How do I search?", "Where do I find a deal/hospital?"]),
    ("/global-search", _HOME, "Global search results across the app's "
     "entities and surfaces.",
     ["Search everything", "Find a deal or page"]),
    ("/query", _SYS, "Ad-hoc query tool over the app's data.",
     ["How do I query the data?", "Can I run a custom query?"]),
    ("/admin/audit-chain", _SYS, "Audit-log chain — the tamper-evident record "
     "of state-changing actions.",
     ["What changed and who did it?", "Is the audit chain intact?"]),
    ("/v3-status", _SYS, "Build / phase status page (v3 milestone tracking).",
     ["What's the v3 status?", "What shipped in this phase?"]),
    ("/v5-status", _SYS, "Build / phase status page (v5 milestone tracking).",
     ["What's the v5 status?", "What shipped in this phase?"]),
    ("/guide/context-debug", _SYS, "Debug view of the Guide's own page-context "
     "packet for a route — what the assistant knows about a page.",
     ["What context does the Guide have for this page?", "Why did the Guide "
      "answer that way?"]),
    ("/team", _HOME, "Team dashboard — members, ownership, and activity.",
     ["Who's on the team?", "Who owns which deals?"]),
    ("/news", _HOME, "News / activity feed relevant to the portfolio and "
     "pipeline.",
     ["What's new?", "Any relevant news?"]),
    ("/insights", _HOME, "Insights feed — surfaced highlights across the "
     "portfolio and universe.",
     ["What should I look at?", "Any notable insights?"]),
    ("/new-deal", PageContextCategory.PIPELINE_SOURCING,
     "New-deal entry — create a deal in the pipeline (manual or import).",
     ["How do I add a deal?", "How do I import a deal?"]),
    ("/market-data/map", PageContextCategory.RESEARCH_BACKTESTING,
     "Geographic market-data map — public market indicators by location.",
     ["What's the geographic picture?", "How do markets compare on the map?"]),
    ("/market-intel/seeking-alpha", PageContextCategory.RESEARCH_BACKTESTING,
     "Market-intelligence reading view (Seeking-Alpha-style) over licensed "
     "research exports.",
     ["What's the market view?", "What does the research say?"]),
    ("/fund-learning", _HOME, "Fund-learning / day-one playbook surface — "
     "lessons and standard plays for new holdings.",
     ["What's the day-one playbook?", "What have we learned across deals?"]),
]
for (_r, _cat, _sd, _cq) in _BATCH8_SYSTEM:
    if _r in {c.route for c in _MANUAL}:
        continue
    _MANUAL.append(_ctx(
        _r, _r.strip("/").replace("/", " ").replace("-", " ").title() or "Home",
        category=_cat,
        short_description=_sd,
        primary_purpose=_sd,
        common_questions=_cq,
        inputs=["App / system state."],
        outputs=["The surface described above."],
        key_metrics=[],
        data_sources=["Application state (not an analytic dataset)."],
        model_logic_summary="A system / navigation / admin surface, not an "
        "analytic model — it shows app state or controls, so there are no "
        "computed figures to interpret.",
        why_it_matters="Supports the workflow around the analytics rather than "
        "producing analysis itself.",
        diligence_use_cases=[_sd],
        interpretation_guidance=["This is a system/utility surface, not an "
                                "analytic output — don't read figures here as "
                                "diligence findings."],
        limitations=["Not an analytic dataset; reflects current app state."],
        related_routes=[],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=_DC.MIXED,
    ))


if "/compare" not in {c.route for c in _MANUAL}:
    _MANUAL.append(_ctx(
        "/compare", "Compare Deals",
        category=PageContextCategory.PORTFOLIO_LP,
        short_description="Side-by-side, column-per-deal comparison of selected "
        "deals (?deals=a,b,c) — KPIs, returns, and trajectory.",
        primary_purpose="Put two or more deals next to each other so the team "
        "can see where they differ at a glance.",
        common_questions=["How do these deals compare?", "Which has the better "
                          "returns?", "Where do they diverge?"],
        inputs=["The selected deals (deals= query param) and their stored "
                "packets / snapshots."],
        outputs=["A column-per-deal table of KPIs/returns plus an EBITDA "
                 "trajectory comparison."],
        key_metrics=["MOIC", "IRR", "EBITDA", "EV/EBITDA"],
        data_sources=["The selected deals' analysis packets / portfolio "
                      "snapshots."],
        model_logic_summary="Renders a side-by-side comparison from each "
        "selected deal's stored figures (rcm_mc/ui/deal_comparison); values are "
        "whatever each deal's packet/snapshot holds, not recomputed live.",
        why_it_matters="Relative comparison is how allocation and "
        "prioritization decisions actually get made.",
        diligence_use_cases=["Comparing shortlisted targets or portfolio deals "
                            "head-to-head."],
        interpretation_guidance=["Figures are each deal's stored values; a deal "
                                "with a thinner packet shows fewer/older "
                                "numbers — not a true zero."],
        limitations=["Only as current as each deal's last packet/snapshot; "
                     "deals must be selected via the deals= parameter."],
        related_routes=["/diligence/compare", "/analysis", "/app"],
        metric_ids=["moic", "irr", "ebitda", "ev_to_ebitda"],
        data_source_ids=["analysis_run", "portfolio_snapshot"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ))


# ── Metric-link enrichment ─────────────────────────────────────────────
# Wire real metric_ids onto core analytic pages that had prose key_metrics but
# no registry link, so the Guide context packet resolves each metric's formula
# + caveats (lifts these pages toward STRONG). Only UNAMBIGUOUS links — pages
# whose metrics aren't in the registry (HHI, star ratings, TVPI/RVPI) are left
# unlinked rather than mapped to a loose proxy. Applied post-build; never
# overrides an existing link.
_METRIC_LINK_PATCHES: Dict[str, List[str]] = {
    "/benchmarks": ["denial_rate", "net_collection_rate", "days_in_ar",
                    "bad_debt_rate", "clean_claim_rate"],
    "/cost-structure": ["operating_margin", "cost_per_adjusted_discharge",
                        "labor_cost_ratio"],
    "/debt-service": ["covenant_cushion", "leverage", "debt"],
    "/payer-stress": ["medicare_exposure", "medicaid_exposure",
                     "commercial_payer_exposure", "payer_stress_impact"],
    "/lp-dashboard": ["moic", "irr", "hold_period"],
    "/market-data": ["revenue", "operating_margin", "bed_count",
                    "occupancy_rate"],
    "/competitive-intel": ["benchmark_percentile"],
    "/diligence/xray": ["benchmark_percentile", "operating_margin"],
    "/diligence/deal-autopsy": ["bankruptcy_pattern_match", "risk_score"],
    "/industry": ["revenue", "ebitda_margin"],
    "/inpatient-rehab": ["discharge_to_community"],
    "/long-term-care-hospital": ["discharge_to_community"],
}
for _c in _MANUAL:
    _patch = _METRIC_LINK_PATCHES.get(_c.route)
    if _patch and not _c.metric_ids:
        _c.metric_ids = list(_patch)

# Newly-added registry metrics (hhi, dscr, tvpi/dpi/rvpi, cms_star_rating, …)
# — APPEND to each page's links (dedup), so pages that already had links also
# pick up the now-documentable metric.
_METRIC_LINK_EXTEND: Dict[str, List[str]] = {
    "/concentration-risk": ["hhi", "concentration_ratio"],
    "/msa-concentration": ["hhi", "concentration_ratio"],
    "/payer-concentration": ["hhi", "concentration_ratio"],
    "/debt-service": ["dscr", "days_cash_on_hand"],
    "/covenant-headroom": ["dscr"],
    "/covenant-monitor": ["dscr"],
    "/treasury": ["days_cash_on_hand"],
    "/lp-dashboard": ["tvpi", "dpi", "rvpi"],
    "/dpi-tracker": ["dpi", "tvpi"],
    "/nursing-homes": ["cms_star_rating"],
    "/dialysis": ["cms_star_rating"],
    "/ma-star": ["cms_star_rating"],
}
for _c in _MANUAL:
    _ext = _METRIC_LINK_EXTEND.get(_c.route)
    if _ext:
        _have = list(_c.metric_ids or [])
        for _mid in _ext:
            if _mid not in _have:
                _have.append(_mid)
        _c.metric_ids = _have

# Data-source links for data-backed analytic pages that had a metric link but
# no source link, so the Guide can answer "where does this come from / how
# fresh / what are its limits". Only HIGH-confidence, unambiguous provenance —
# illustrative scenario tools are correctly left source-less, and pages whose
# provenance is ambiguous are skipped rather than mislabeled.
_DATA_SOURCE_LINK_PATCHES: Dict[str, List[str]] = {
    "/cost-structure": ["cms_hcris"],
    "/debt-service": ["cms_hcris"],
    "/diligence/xray": ["cms_hcris"],
    "/market-data": ["cms_hcris"],
    "/payer-stress": ["cms_hcris"],
    "/competitive-intel": ["cms_hcris"],
    "/dialysis": ["cms_care_compare"],
    "/nursing-homes": ["cms_care_compare"],
    "/inpatient-rehab": ["cms_care_compare"],
    "/long-term-care-hospital": ["cms_care_compare"],
    "/lp-reporting": ["portfolio_snapshot"],
    "/deal-library/comps": ["public_transaction_corpus"],
    "/diligence/bear-case": ["analysis_run"],
}
for _c in _MANUAL:
    _sp = _DATA_SOURCE_LINK_PATCHES.get(_c.route)
    if _sp and not _c.data_source_ids:
        _c.data_source_ids = list(_sp)

# Batch-2 metric links (length_of_stay, FCCR, interest_coverage, CCC, net_debt,
# current_ratio, gross_margin, capex_intensity, cost_to_charge_ratio,
# readmission_rate). Append (dedup); only applies to routes already documented.
_METRIC_LINK_EXTEND_2: Dict[str, List[str]] = {
    "/working-capital": ["cash_conversion_cycle", "current_ratio"],
    "/debt-service": ["fixed_charge_coverage", "interest_coverage", "net_debt"],
    "/covenant-headroom": ["fixed_charge_coverage", "interest_coverage"],
    "/covenant-monitor": ["interest_coverage"],
    "/cost-structure": ["cost_to_charge_ratio"],
    "/unit-economics": ["gross_margin"],
    "/cap-structure": ["net_debt"],
    "/treasury": ["current_ratio"],
    "/capex-budget": ["capex_intensity"],
    "/inpatient-rehab": ["length_of_stay", "readmission_rate"],
    "/long-term-care-hospital": ["length_of_stay", "readmission_rate"],
    "/deal-library/comps": ["ev_to_ebitda", "benchmark_percentile"],
    "/diligence/bear-case": ["risk_score", "bankruptcy_pattern_match"],
}
for _c in _MANUAL:
    _ext2 = _METRIC_LINK_EXTEND_2.get(_c.route)
    if _ext2:
        _have2 = list(_c.metric_ids or [])
        for _mid in _ext2:
            if _mid not in _have2:
                _have2.append(_mid)
        _c.metric_ids = _have2


MANUAL_PAGE_CONTEXTS: Dict[str, PageContext] = {c.route: c for c in _MANUAL}
