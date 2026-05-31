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
    # 2026-05-28 waves A-H: every PEdesk page now ships the same six
    # standard page-action affordances via the shared ck_page_actions
    # helper. If a partner asks how to share / print / look up / jump
    # / find shortcuts, point at these.
    "Every PEdesk page now has SEVEN standard actions wired by the "
    "shared ck_page_actions helper: (1) Copy share link — captures "
    "the current URL with every filter, sort, and scope param "
    "encoded so the partner can share or bookmark the exact view; "
    "(2) Print this view — sends the page to the browser print "
    "dialog; many editorial panels already carry @media print rules "
    "so the output is partner-presentable; (3) ? Shortcuts — opens "
    "the keyboard shortcut overlay; (4) ⌘K Quick jump — opens the "
    "command palette so the partner can navigate to any route by "
    "typing; (5) 📖 Glossary — direct link to /metric-glossary "
    "where every metric has its definition, rationale, formula, "
    "and source documents; (6) 🔬 Methodology — direct link to "
    "/methodology where every model has its inputs, assumptions, "
    "formulas, and validation references documented; (7) Back to "
    "top — floating pill that appears after the partner scrolls "
    "more than 600px down.",
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
            "How is the weighted MOIC computed — entry-EV weighted, NAV weighted, or per-deal averaged?",
            "How does Command Center differ from /portfolio and /day-one?",
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
        common_questions=[
            "What changed over the weekend?",
            "What needs attention first this week?",
            "Which deals advanced or were added in the last 7 days?",
            "Are there any red alerts I haven't seen yet?",
            "What's the overall portfolio-health mix this morning?",
        ],
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
        common_questions=[
            "What's on my plate this week?",
            "Which of my deals have red alerts or overdue deadlines?",
            "How many deals do I own across the book?",
            "What's the health-mix across my assigned deals?",
            "Which of my deals had a stage change recently?",
        ],
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
                         "Which deals tripped a covenant or missed plan?",
                         "How does snoozing or acknowledging affect the lifecycle "
                         "— does it suppress re-fire, and for how long?",
                         "How does /alerts differ from /escalations and /portfolio/risk-scan?"],
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
        common_questions=[
            "What red alerts are still open and for how long?",
            "What needs a partner decision before the LP update?",
            "How many alerts have been red for more than 30 days?",
            "Are any escalations acknowledged but still open?",
            "Which deal carries the most aged alerts?",
        ],
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
        common_questions=[
            "Which deals am I watching?",
            "How are my pinned deals trending?",
            "Did any pinned deal trip a covenant?",
            "What's the average MOIC / IRR across my watchlist?",
            "How do I add a deal to / remove from the watchlist?",
        ],
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
        common_questions=[
            "What questions are still open across my deals?",
            "Can I send these to the seller / put them in the IC binder?",
            "How do I export the open questions as CSV or print-binder?",
            "Are these questions saved server-side or browser-local?",
            "Why don't I see questions from a deal I opened on another machine?",
        ],
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
        common_questions=[
            "Who acknowledged this alert and when?",
            "Who changed this deal's owner?",
            "Which users have logged in recently?",
            "Did any user delete data they shouldn't have?",
            "How far back does this audit window go?",
        ],
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
        common_questions=[
            "Who has access?",
            "How do I add or remove a user?",
            "How do I rotate a user's password?",
            "What's the difference between analyst and admin roles?",
            "How do I revoke access without deleting the user?",
        ],
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
        common_questions=[
            "How do I add a deal?",
            "Can I bulk-load deals?",
            "What format does the bulk JSON payload need?",
            "Which fields are required vs prior-filled?",
            "Why is my imported deal showing prior-filled values?",
        ],
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
        limitations=["Two import paths only — a single-deal form and a "
                     "JSON-array bulk path; partners with CSV exports "
                     "need to convert to JSON first.",
                     "Prior-filled fields use platform-wide Bayesian "
                     "priors, not target-specific defaults — verify each "
                     "imported deal's filled values before underwriting."],
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
        diligence_use_cases=[
            "Building a thesis-driven shortlist across every onboarded CMS "
            "provider universe in one workflow (Source → Screener → "
            "Just-missed → Saved → X-Ray → Pipeline).",
            "Comparing candidates across or within a vertical on quality + "
            "size before opening an X-Ray.",
            "Auditing what data is missing for a target before promoting it.",
        ],
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
        limitations=[
            "Public CMS data only — universes are filing-derived and lag "
            "real-time by a quarter to a year depending on the loader.",
            "A target's score depends on which filters and view you have "
            "active; tighter filters can hide otherwise-relevant providers."],
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
        common_questions=[
            "Which hospitals fit my thesis?",
            "What scores highest for this strategy?",
            "What weights does the fit score use (beds vs payer mix vs margin)?",
            "Is the fit score a predicted return or a thesis-fit ranking?",
            "Which preset theses are available?",
        ],
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
        common_questions=[
            "Which hospitals match these financial criteria?",
            "Show me large turnaround candidates.",
            "What presets are available — turnaround, large-cap, margin-expansion?",
            "How does this differ from /source's thesis-fit screen?",
            "Where can I see the HCRIS data this filter runs against?",
        ],
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
        common_questions=[
            "Which hospitals look like the biggest RCM-improvement bets?",
            "How much EBITDA uplift does the model estimate "
            "for a target with these characteristics?",
            "What signal is the model picking up — denial rate, "
            "AR days, payer mix?",
            "How do I narrow the screen to my fund's region or "
            "size band?",
            "Is the model's uplift estimate validated against any "
            "realized RCM outcomes?",
        ],
        inputs=["Region / bed / margin / minimum-uplift filters."],
        outputs=["Matching hospitals with estimated denial rate, AR days, "
                 "and total EBITDA-uplift opportunity; an aggregate uplift."],
        key_metrics=["Total estimated uplift", "Matching hospitals",
                     "Avg estimated denial rate", "Avg margin"],
        data_sources=["CMS HCRIS public data + the platform's RCM "
                      "quant/ML estimators."],
        model_logic_summary=(
            "Per HCRIS hospital row, applies the platform's RCM "
            "estimators to predict denial_rate, days_in_AR, and "
            "clean_claim_rate from public HCRIS attributes; computes "
            "RCM uplift = (current gap vs benchmark) × revenue × "
            "contribution margin. Filters narrow the set; the aggregate "
            "is the sum of per-hospital uplift estimates."),
        diligence_use_cases=[
            "Building a thesis-driven sourcing shortlist where the "
            "estimated RCM uplift exceeds a minimum bar.",
            "Pre-screening a target geography or size band before "
            "spending diligence hours on individual hospitals.",
        ],
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
        common_questions=[
            "What deals are comparable to this target?",
            "What's the peer MOIC / EV/EBITDA?",
            "How is the similarity score weighted (sector vs EV vs vintage)?",
            "Are the comps from real realized deals or illustrative?",
            "How does this differ from /comparables and /diligence/comparable-outcomes?",
        ],
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
        common_questions=[
            "Which corpus deals pass the screen?",
            "What happens if I tighten the thresholds?",
            "What rules drive PASS / WATCH / FAIL?",
            "How does this differ from /screening (workspace) and /target-screener (public)?",
            "What's the data completeness threshold a deal needs to pass?",
        ],
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
        common_questions=[
            "What can the PE-intelligence brain do?",
            "Where do I run it on a specific deal?",
            "What's the difference between reflexes, archetypes, and red-flag catalogs?",
            "Is the PE-intelligence output a prediction or codified judgment?",
            "Which deal routes consume these modules?",
        ],
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
        common_questions=[
            "What conferences are coming up?",
            "Which events matter for healthcare PE?",
            "Where can I filter by category — provider, payer, investing?",
            "Is the calendar a live feed or a curated list?",
            "Which conferences focus on hospital M&A?",
        ],
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
        common_questions=[
            "What deal am I working on?",
            "Where do I set the deal's parameters?",
            "Why does the profile reset when I open a new browser?",
            "How do I move a deal profile to a teammate's machine?",
            "Which downstream tools read this profile?",
        ],
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
        "data with peer-percentile benchmarking and outlier flags.",
        primary_purpose="Expose the public-filing financials underlying a "
        "target so partners can sanity-check the seller's CIM against the "
        "audited cost report.",
        common_questions=[
            "What does HCRIS say about this hospital's margin?",
            "How does this hospital's cost-per-discharge compare to peers?",
            "What's the Medicare exposure for this target?",
            "Which line items are outliers vs the CMS HCRIS peer group?",
            "Is the labor cost ratio normal for this size hospital?",
            "What year of HCRIS is this from? Is the data stale?",
            "What's the bed count and how does it scale revenue?",
        ],
        inputs=[
            "Hospital CCN (CMS Certification Number).",
            "Optional: peer set definition (size band + state).",
        ],
        outputs=[
            "Filed HCRIS line items (revenue, cost, labor, supplies, bed-day "
            "metrics), per-metric peer percentile rank against the corpus, "
            "outlier flags (>2 standard deviations from peer median), "
            "year-over-year trend sparklines, residual decomposition.",
        ],
        key_metrics=[
            "Operating margin, Cost per adjusted discharge, "
            "Labor cost ratio, Medicare exposure %, Bed count, "
            "Outpatient revenue share, Days cash on hand",
        ],
        data_sources=[
            "CMS HCRIS cost-report filings (Form 2552-10) from the latest "
            "available filing year (typically 18-24 months in arrears).",
        ],
        model_logic_summary=(
            "Loads the hospital's filing rows from data.hcris, computes "
            "derived ratios (margin = (revenue - cost) / revenue, etc.), "
            "joins to the corpus peer set, computes percentile rank per "
            "metric, flags >2σ outliers. Residual decomposition uses "
            "OLS against bed_count + payer_mix + region to isolate the "
            "size-adjusted margin."
        ),
        why_it_matters="HCRIS is the public ground truth for hospital "
        "financials in diligence. If the seller's CIM EBITDA differs "
        "from the HCRIS-derived number, the gap needs explaining before IC.",
        diligence_use_cases=[
            "Pre-LOI: confirm the seller's claimed EBITDA reconciles "
            "with the HCRIS filing.",
            "IC: cite the peer-percentile rank for margin/cost discipline.",
            "Operational diligence: target the outlier-flagged line items "
            "for management Q&A.",
        ],
        interpretation_guidance=[
            "HCRIS lags real-time and has filing artifacts; treat as a "
            "public baseline.",
            "Cost-per-discharge varies by case mix; compare same-CMI peer "
            "sets, not raw cost.",
            "Operating margin includes Medicaid DSH and supplemental "
            "payments that may not recur post-close.",
            "A 'normal' margin vs peers does not preclude operational "
            "problems below the surface — pair with management Q&A.",
        ],
        limitations=[
            "Filings lag 18-24 months; recent operational changes may "
            "not be in this data.",
            "Peer-percentile rank depends on the corpus year-cohort; "
            "off-cycle filers may compare against a different vintage.",
            "Some HCRIS rows are self-reported and known to have "
            "data-quality issues (e.g. wage-index components).",
        ],
        related_routes=["/diligence/deal", "/comparables",
                        "/diligence/payer-stress", "/diligence/xray"],
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
        "levers from current to target EBITDA and how achievable each is, "
        "with probability-weighting and a realization-rate cross-check "
        "against the realized-deal corpus.",
        primary_purpose="Pressure-test the adjusted-EBITDA bridge and the "
        "probability-weighting behind the value-creation case; flag bridges "
        "that depend on a single big lever or on unweighted gross impacts.",
        common_questions=[
            "What does the EBITDA bridge look like for this deal?",
            "Which levers contribute the most upside?",
            "How realistic is the bridge given the realized-deal corpus?",
            "What's the probability-weighted bridge value?",
            "Are any levers double-counted across categories?",
            "What's the largest concentration risk in the bridge?",
            "How does the realization probability compare to similar deals?",
        ],
        inputs=[
            "Deal ID with a populated value-creation bridge.",
            "The seller's claimed add-backs to bridge to adjusted EBITDA.",
            "Lever definitions (RCM uplift, pricing, supply, labor, "
            "synergy, growth) with gross impact and probability weights.",
        ],
        outputs=[
            "Waterfall chart of levers from current EBITDA to target.",
            "Probability-weighted total opportunity.",
            "Realization-rate benchmark vs corpus median for each lever type.",
            "Concentration warning if any single lever > 40% of bridge.",
            "Cross-check vs PE corpus realized bridges.",
        ],
        key_metrics=[
            "Current EBITDA, Adjusted EBITDA, Target EBITDA, "
            "Bridge gross impact, Bridge probability-weighted impact, "
            "Lever realization rate, Concentration risk",
        ],
        data_sources=[
            "Seller CIM (lever definitions + gross impact)",
            "QoE report (adjusted-EBITDA reconciliation)",
            "Corpus realized-bridge data (rcm_mc.pe.rcm_ebitda_bridge)",
            "Model output (probability prior from the realized corpus)",
        ],
        model_logic_summary=(
            "Loads the bridge structure for the deal, validates that "
            "lever sums equal target EBITDA - current EBITDA, joins "
            "each lever to its corpus realization-rate distribution, "
            "computes probability-weighted impact = gross × realization "
            "rate. Flags bridge concentration via Herfindahl index on "
            "lever shares. Concentration > 40% on one lever or > 70% "
            "on top two raises an amber/red flag."
        ),
        why_it_matters="The bridge is the upside thesis; the audit checks it "
        "isn't built on optimistic add-backs or unweighted gross impacts. "
        "If 80% of the bridge sits in one lever, that's the diligence priority.",
        diligence_use_cases=[
            "IC defense: show the probability-weighted bridge, not the "
            "gross.",
            "Lever validation: identify which 1-2 levers warrant a deep dive.",
            "Sensitivity: model what happens if the largest lever delivers "
            "at 50% of plan.",
        ],
        interpretation_guidance=[
            "Distinguish gross lever impact from probability-weighted impact.",
            "Add-backs into adjusted EBITDA are judgmental — see the QoE.",
            "Realization rates in the corpus are HISTORICAL — use them as "
            "priors not predictions.",
            "Bridge concentration warnings are heuristics, not hard limits.",
        ],
        limitations=[
            "Realization-rate priors are pulled from a limited corpus and "
            "may not reflect the specific market or sponsor playbook.",
            "Probability weighting assumes lever independence; correlated "
            "levers will overstate the de-risking.",
            "Does not model the cost of capture (capex/opex required to "
            "realize each lever).",
        ],
        metric_ids=["adjusted_ebitda", "ebitda_bridge",
                    "bridge_realization_probability",
                    "value_creation_opportunity"],
        data_source_ids=["seller_cim", "qoe_report", "model_output",
                         "public_transaction_corpus"],
        related_routes=["/diligence/value", "/diligence/qoe-memo",
                        "/diligence/risk-workbench", "/ebitda-bridge"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/denial-prediction", "Denial Prediction",
        short_description="Predicts claim denials and the recoverable "
        "revenue-cycle opportunity from the target's claims data.",
        primary_purpose="Quantify denial-driven leakage and the RCM uplift a "
        "buyer could capture.",
        common_questions=[
            "What's the predicted denial rate on the target's claims?",
            "How much revenue is recoverable via denial reduction?",
            "Is the prediction trained on the target's data or a corpus?",
            "Initial vs final denial rate — which one does this show?",
            "How does this connect to /predictive-screener?",
        ],
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
        "compensation, contribution, and the comp-redesign opportunity. "
        "DATA REQUIRED: activates once you upload your provider roster + "
        "compensation file (template: management_compensation_template.csv).",
        primary_purpose="Show which providers/sites are economically "
        "additive and where comp is out of line with output; surface the "
        "comp-redesign opportunity as a value-creation lever. Upload your "
        "provider roster + compensation file via /import to activate.",
        common_questions=[
            "Which providers are most productive (wRVU)?",
            "Where is comp out of line with collections?",
            "What's the compensation-to-collections ratio by provider?",
            "Which providers have the highest contribution margin?",
            "What's the comp-redesign opportunity?",
            "Are there providers with comp > collections (subsidies)?",
            "What's the productivity distribution vs MGMA benchmarks?",
        ],
        inputs=[
            "Provider roster (NPI, specialty, hire date, employment "
            "status).",
            "Compensation file (per-provider base + incentive + benefits).",
            "Activity data: wRVU, encounters, panel size, "
            "collections per provider.",
            "Optional: MGMA / SullivanCotter benchmark set for the "
            "specialty.",
        ],
        outputs=[
            "Per-provider table: wRVU, comp, collections, "
            "comp-to-collections ratio, contribution margin, "
            "percentile vs MGMA.",
            "Specialty roll-up: average wRVU, median comp, "
            "comp-redesign opportunity in $.",
            "Subsidized-provider list: providers whose comp exceeds "
            "their collections.",
            "Scatter: comp vs wRVU with the specialty benchmark line.",
        ],
        key_metrics=[
            "wRVU (work RVU), Comp-to-collections ratio, "
            "Contribution margin per provider, "
            "Productivity percentile vs specialty benchmark, "
            "Comp-redesign opportunity ($)",
        ],
        data_sources=[
            "Provider roster (target's HR file, sometimes via NPPES join) "
            "— DATA REQUIRED: upload via /import (template: "
            "management_compensation_template.csv).",
            "Compensation file (target's payroll/comp system export) — "
            "uploaded alongside the roster.",
            "Monthly actuals (collections, encounters per provider)",
            "Optional: MGMA / SullivanCotter benchmark set",
        ],
        model_logic_summary=(
            "For each provider, joins comp + collections + wRVU on NPI. "
            "Computes comp-to-collections (comp / collections), "
            "contribution margin (collections - direct cost - allocated "
            "overhead). Productivity percentile uses MGMA tables when "
            "supplied, otherwise the corpus distribution. Comp-redesign "
            "opportunity = comp paid above the 75th-percentile MGMA "
            "comp-to-collections ratio — partner can decide to redesign "
            "or accept."
        ),
        why_it_matters="Physician economics drive group margin and the "
        "retention / comp-redesign value lever. A subsidized-provider "
        "list of 20% of the panel can represent millions in EBITDA "
        "opportunity but also retention risk if redesigned aggressively.",
        diligence_use_cases=[
            "Pre-LOI: scan for subsidized providers — they're the "
            "comp-redesign EBITDA lever.",
            "Lever sizing: compute the comp-redesign opportunity for "
            "the bridge.",
            "Retention risk: identify high-producer providers whose "
            "comp exceeds local market — they're the flight risks.",
        ],
        interpretation_guidance=[
            "wRVU is work-RVU only; comp-to-collections benchmarks vary "
            "by specialty.",
            "Shared-cost allocation changes contribution-margin answers.",
            "Subsidized providers may carry strategic value (referrals, "
            "coverage, geography) — don't redesign without operational "
            "review.",
            "MGMA percentiles depend on the specialty match; "
            "subspecialists may need an alternate benchmark.",
        ],
        limitations=[
            "Only as good as the comp file — bonuses paid as benefits "
            "may not show.",
            "wRVU does not capture cognitive work or admin time.",
            "MGMA benchmarks lag and vary in sample size per specialty.",
            "Does not model retention probability after comp redesign.",
        ],
        metric_ids=["wrvu", "provider_productivity",
                    "compensation_to_collections",
                    "provider_contribution_margin"],
        data_source_ids=["provider_roster", "compensation_file",
                         "monthly_actuals"],
        related_routes=["/diligence/physician-attrition",
                        "/diligence/value", "/provider-supply"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/diligence/risk-workbench", "Risk Workbench",
        short_description="A nine-panel risk panorama — runs the Tier-1/2/3 "
        "diligence engines against the supplied deal metadata and shows a "
        "severity band per panel. DATA REQUIRED: supply deal metadata via "
        "query params or upload your risk-register template "
        "(risk_register_template.csv).",
        primary_purpose="Pressure-test a deal's structural risks (regulatory, "
        "real-estate, physician, cyber, MA, labor, patient-pay) in one view; "
        "upload your risk-register to activate the missing panels.",
        common_questions=[
            "Where does this deal carry structural risk?",
            "What does the Steward precedent look like here?",
            "What inputs does each risk panel need?",
            "Why is this panel showing 'not supplied'?",
            "What's the severity band scale (GREEN / YELLOW / RED / CRITICAL)?",
            "How do I add risks to the register?",
            "Can I export the 9-panel view for IC?",
        ],
        inputs=["Deal metadata via query params (states, specialty, legal "
                "structure, landlord, lease terms, etc.); panels without "
                "inputs render 'not supplied' rather than fabricating numbers. "
                "Or upload a full risk register via /import "
                "(risk_register_template.csv)."],
        outputs=["Per page labels: a metadata strip and a 9-panel grid, each "
                 "panel showing a severity band (GREEN / YELLOW / RED / "
                 "CRITICAL) with a headline number."],
        key_metrics=["Per-panel severity band", "Risk score"],
        data_sources=["The supplied deal metadata, run through the diligence "
                      "engines; OR you can upload a risk register via "
                      "/import for the per-panel deep-dive. A hardcoded "
                      "Steward replay is available in demo mode "
                      "(?demo=steward)."],
        model_logic_summary="Each panel runs its own engine on the metadata "
        "and emits a severity band. No CCD/claims data is required. Exact "
        "per-engine rules: see risk_workbench_page.py — treat specifics as "
        "needing source confirmation.",
        why_it_matters="Forces the structural downside into view before IC.",
        diligence_use_cases=[
            "A fast structural-risk read across many vectors "
            "early in diligence.",
            "IC preparation: cite the per-panel severity bands.",
            "Lender discussion: walk through the structural exposures.",
        ],
        interpretation_guidance=[
            "Severity bands are rule-derived signals on the inputs, not a "
            "verdict — should be verified before IC use.",
            "Panels with no inputs say 'not supplied'; absence is not safety. "
            "Upload the missing data via /import to activate them.",
            "?demo=steward replays the Steward 2016 pattern as a precedent "
            "— do NOT cite as a current deal.",
        ],
        limitations=["Runs on metadata only; quality depends on what's "
                     "supplied. A clean panorama is not proof of no risk."],
        related_routes=["/diligence/payer-stress", "/diligence/covenant-stress",
                       "/bear-cases"],
        source_confidence=SourceConfidence.DOCUMENTED,
        notes_for_assistant=[
            "?demo=steward is a SPECIFIC named historical replay (the Steward "
            "Health 2016 pattern), not a generic example dataset — figures in "
            "demo mode are a precedent reconstruction, not a live deal. There "
            "is also a ?print=1 print-preview mode.",
        ],
        metric_ids=["risk_score"],
        data_source_ids=["model_output", "demo_fixture"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/payer-stress", "Payer Stress",
        short_description="Stress the deal's economics against payer-mix / "
        "reimbursement shifts — what happens to EBITDA if commercial rates "
        "cut 5%, Medicare Advantage penetration jumps 10pts, or the largest "
        "commercial contract walks.",
        primary_purpose="Quantify sensitivity to payer concentration and "
        "rate pressure so partners can size the downside before IC and "
        "structure protections (rate floors, term length, MFN clauses).",
        common_questions=[
            "What happens to EBITDA if the largest commercial payer "
            "cuts rates 5%?",
            "How concentrated is the payer mix?",
            "What's the commercial vs Medicare vs Medicaid exposure?",
            "Which payers are the biggest single-payer concentration risk?",
            "What's the MA penetration risk in this market?",
            "How does this payer mix compare to peer hospitals?",
            "What protections should we ask for given this concentration?",
        ],
        inputs=[
            "Deal payer-contract schedule (payer, contract term, "
            "rate-base index, recent renewal).",
            "Optional: claims volume by payer for weighting.",
            "Scenario shock parameters (rate cut %, MA shift, "
            "single-payer walkout).",
        ],
        outputs=[
            "Per-payer share of net revenue with concentration index.",
            "Stress-scenario EBITDA waterfall under each shock.",
            "Verdict band (PASS / CAUTION / WARNING / FAIL) per "
            "scenario based on covenant headroom impact.",
            "Comparable-deal cross-check on similar payer mixes.",
        ],
        key_metrics=[
            "Payer concentration (Herfindahl)", "Commercial exposure %",
            "Medicare exposure %", "Medicaid exposure %",
            "Stress-scenario EBITDA delta",
            "Verdict band per scenario",
        ],
        data_sources=[
            "Payer contracts (target supplied)",
            "Benchmark prior (commercial rate-cut frequencies from corpus)",
            "Model output (covenant-headroom impact per scenario)",
        ],
        model_logic_summary=(
            "Loads the payer mix, computes shares of net revenue. "
            "For each scenario, applies the shock to per-payer "
            "revenue, recomputes EBITDA assuming variable-cost "
            "ratio holds, computes covenant ratio under stress, "
            "compares to the threshold, assigns verdict band. "
            "Concentration uses Herfindahl on revenue shares; >0.25 "
            "= high concentration. Logic in finance/payer_stress.py."
        ),
        why_it_matters="Payer mix is a top driver of healthcare deal "
        "risk. A 60% commercial payer mix looks beautiful at LOI "
        "and terrible if the largest commercial walks. Pre-IC "
        "stress testing sizes that downside.",
        diligence_use_cases=[
            "Pre-IC: confirm worst-case payer scenario still clears "
            "covenant.",
            "Lender discussion: cite the stress-test headroom impact.",
            "Contract negotiation: size the MFN / rate-floor protection.",
        ],
        interpretation_guidance=[
            "Concentration uses revenue, not lives — payer rates "
            "vary, so high lives don't always mean high revenue share.",
            "MA penetration risk is market-level, not deal-level — "
            "shocks reflect general MA trends, not specific contracts.",
            "Variable-cost assumption breaks at extreme shocks; "
            "FAIL scenarios should be cross-checked with operating "
            "leverage modeling.",
            "Stress is a snapshot — multi-year contracts may push "
            "the impact 2-3 years out, not immediately.",
        ],
        limitations=[
            "Shock parameters are deterministic, not probabilistic "
            "— treats a 5% cut as certain, not as one of many.",
            "Does not model offsetting volume / mix shifts that "
            "often accompany rate changes.",
            "Payer-contract data is only as good as the schedule "
            "provided.",
        ],
        related_routes=["/payer-intelligence", "/diligence/risk-workbench",
                        "/payer-stress", "/diligence/covenant-stress"],
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
                         "Is this packet finalized / signed off?",
                         "Which sections pull from /diligence/qoe-memo, comps, "
                         "and the bankruptcy-survivor scan?",
                         "Are the claims figures from the deal's real data or a fixture?"],
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
        model_logic_summary=(
            "Composes the IC packet from the deal's analysis-packet "
            "stages (RCM KPIs + cash waterfall, bankruptcy-survivor "
            "scan, counterfactual advisor, peer comps + transaction "
            "multiple, historical deal-autopsy match). Each section "
            "renders the same underlying outputs the standalone "
            "diligence pages show — packet orchestration, not new math."),
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
                     "Packet sections stitch together fixtures/inputs from "
                     "across the deal — a 'consistent IC packet' depends on "
                     "the partner verifying each section's source first."],
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
                         "Which items still need an owner or evidence?",
                         "How does coverage % differ from total-done %?",
                         "Can a partner override an auto-tracked status, and "
                         "where would that show up?"],
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
                         "Is this memo finalized / signed?",
                         "What KPIs and waterfall show in the memo, and where "
                         "do the numbers come from?",
                         "How does this differ from /diligence/ic-packet and "
                         "/diligence/bridge-audit?"],
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
        model_logic_summary=(
            "Reads claims rows, computes the standard RCM KPI bundle "
            "(NCR, GCR, days_in_AR, denial_rate, clean_claim_rate) "
            "using the metric definitions on each MetricContext card, "
            "and builds a cash-waterfall from charges → adjustments → "
            "payments → AR over the cohort months in the dataset. "
            "Optional counterfactual scenarios reapply the KPIs with "
            "the entered shock."),
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
        common_questions=[
            "How do these two deals compare?",
            "Which is the stronger lead?",
            "What deltas does the page show — KPIs, QoR, counterfactual?",
            "How do I switch the left/right datasets?",
            "How does this differ from /compare and /find-comps?",
        ],
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
        common_questions=[
            "What does the full diligence run say?",
            "Which step flagged the biggest issue?",
            "How long does the full chain take to run end-to-end?",
            "How do I rerun just one analytic when an input changes?",
            "Which analytics are chained — ingest, denial, MC, counterfactual, bankruptcy?",
        ],
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
        model_logic_summary=(
            "Pipelines the deal through 10 analytic stages in order: "
            "ingest → benchmarks → denial prediction → bankruptcy "
            "scan → counterfactual → attrition → autopsy → market "
            "intel → scenario assembly → Monte Carlo. Each stage's "
            "output feeds the next; a stage failure short-circuits "
            "only that stage and logs it. Final output is a "
            "single-page deep-link map plus headline numbers."),
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
        common_questions=[
            "How does this target compare to peers?",
            "Which KPIs are off-benchmark?",
            "Where do the peer quartile bands come from (HFMA, MGMA)?",
            "How does Days in A/R / denial rate / NCR map to MOIC upside?",
            "What's a good vs bad cost-to-collect ratio?",
        ],
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
        model_logic_summary=(
            "Computes RCM KPIs from the claims dataset using the same "
            "definitions documented on each metric's MetricContext "
            "card (denial_rate, days_in_ar, clean_claim_rate, "
            "net_collection_rate, cost_to_collect). For each, "
            "compares against built-in HFMA-style peer-quartile bands "
            "and shows the signed delta to the peer median."),
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
        common_questions=[
            "What's driving the denials?",
            "Where are the recoverable write-offs?",
            "What's the dollar volume in the biggest denial category?",
            "How are denial codes mapped to root-cause categories?",
            "Which payer has the most write-offs?",
        ],
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
        common_questions=[
            "What's the RCM upside worth on this deal?",
            "Which levers should the 100-day plan prioritize?",
            "How does denial-rate reduction translate into EBITDA dollars?",
            "What's the typical realization rate on these levers in year 1?",
            "How does the EBITDA contribution flow into the value bridge?",
        ],
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
        model_logic_summary=(
            "For each of the seven RCM levers (denial, AR, "
            "clean-claim, underpayment, cost-to-collect, payer-mix, "
            "working capital), applies the lever's benchmark delta to "
            "the deal's claims to estimate the recoverable revenue, "
            "then × the deal's contribution margin = expected EBITDA "
            "contribution. The lever-by-lever stack feeds the value-"
            "bridge."),
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
        common_questions=[
            "What would change the conclusion on this deal?",
            "Which lever is the binding constraint?",
            "How much rate / denial / AR improvement do we need to flip the band?",
            "How feasibly can each lever realistically be moved?",
            "What's the $ impact of moving each lever to GREEN?",
        ],
        inputs=["A claims dataset (fixture) + deal metadata (legal structure, "
                "states, specialty, landlord, lease terms, etc.)."],
        outputs=["Per page labels: per-lever cards (module, action, original→"
                 "target band, feasibility HIGH/MED/LOW, estimated $ impact); "
                 "a JSON download of the same."],
        key_metrics=["Minimum lever shift to flip the band", "Feasibility",
                     "Estimated $ impact"],
        data_sources=["Target claims (fixture here) + caller-supplied "
                      "metadata; model outputs."],
        model_logic_summary=(
            "Per lever, performs a 1-D root-find on the current "
            "verdict band's edge (RED/YELLOW threshold or "
            "YELLOW/GREEN threshold) holding all other levers fixed; "
            "reports the minimum lever shift, an entered feasibility "
            "tag, and the $ impact at the shifted lever. Sensitivity, "
            "not joint-optimization."),
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
        common_questions=[
            "What's the range of outcomes, not just the base case?",
            "How likely is a sub-1x result?",
            "How many simulated paths does the run use by default?",
            "Which assumptions have the biggest impact on the spread?",
            "How does this differ from /scenarios and /portfolio/monte-carlo?",
        ],
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
        model_logic_summary=(
            "Draws N simulated paths (default ~10k) where each path "
            "samples revenue growth, EBITDA margin, denial "
            "improvement, regulatory headwind, and exit multiple "
            "from their entered mean/σ; the deal LBO math computes "
            "MOIC/IRR/EBITDA per path. Distributions aggregate "
            "across paths into P50/P75 and tail bands."),
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
        common_questions=[
            "Which historical deals does this most resemble?",
            "Are we about to repeat a known failure?",
            "What 9 risk dimensions define the signature?",
            "What outcomes did the top-similar deals have?",
            "Is the historical library curated or auto-generated?",
        ],
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
        common_questions=[
            "How much covenant headroom does this structure have?",
            "Under stress, when might a covenant get tight?",
            "What's the simulated peak breach probability per covenant?",
            "Which quarter is most likely to trip under the stress paths?",
            "How does this differ from /covenant-monitor and /covenant-headroom?",
        ],
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
        model_logic_summary=(
            "Simulates per-quarter EBITDA paths from entered Y0 + "
            "growth + volatility (geometric Brownian draws). For each "
            "covenant, computes the share of paths breaching at each "
            "quarter, reports the peak-breach % and the earliest "
            "quarter where ≥50% of paths breach. Cure $ is "
            "median path EBITDA gap × covenant denominator."),
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
        common_questions=[
            "When might be the best time to exit?",
            "Which buyer type fits this deal?",
            "What expected MOIC does each hold-year scenario produce?",
            "How does buyer-type affect the multiple at exit?",
            "Is this a market-timing call or just a scenario read?",
        ],
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
        model_logic_summary=(
            "For each hold-year (Y3-Y7), takes the Deal-MC EBITDA "
            "distribution and applies peer multiples per buyer type "
            "(strategic, sponsor, public) plus close-certainty "
            "discounts. Ranks the year × buyer pairs by "
            "probability-weighted proceeds. The 'optimal' year "
            "maximizes proceeds × close-certainty."),
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
        common_questions=[
            "How is the claims data normalized?",
            "What was changed or flagged during ingest?",
            "What's the schema of the Canonical Claims Dataset (CCD)?",
            "Why is some data 'modified' vs 'unchanged' during ingest?",
            "How do I see the row-level transformation log?",
        ],
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
        common_questions=[
            "How does this management team score?",
            "What haircut does management risk imply?",
            "Which dimensions does the scorecard cover — forecast reliability, comp, tenure, reputation?",
            "How does a red-flag override affect the per-exec score?",
            "How is the bridge haircut computed from the aggregate score?",
        ],
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
        model_logic_summary=(
            "Per executive: weighted average across the four "
            "dimension scores (forecast reliability, comp structure, "
            "tenure, reputation); a red-flag override caps the "
            "per-exec score regardless of the average. Roster "
            "aggregate is the weighted mean of per-exec scores, then "
            "mapped through a 0-100 → 0-X% haircut function."),
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
        common_questions=[
            "Which providers are flight risks?",
            "How much EBITDA is exposed to attrition?",
            "Which factors drive the 18-month flight-risk score?",
            "How does this differ from /provider-retention (DATA REQUIRED)?",
            "Are these flight-risk probabilities trained on real outcomes?",
        ],
        inputs=["A provider roster (demo fixture on this page) with tenure, "
                "age, collections trend, local competition, employment type."],
        outputs=["Per page labels: total EBITDA-at-risk, band counts "
                 "(Critical/High/Medium/Low), and a flight-risk roster "
                 "(Provider, Specialty, Employment, Flight prob, Band, "
                 "Collections, $ at risk, Top driver)."],
        key_metrics=["Flight-risk probability", "EBITDA at risk",
                     "Provider productivity"],
        data_sources=["A provider roster (demo fixture) scored by a model."],
        model_logic_summary=(
            "Logistic regression on entered per-provider features "
            "(tenure, age, collections trend, local competition, "
            "employment type) → 18-month flight-risk probability; "
            "per-provider feature contributions are returned. EBITDA-"
            "at-risk = flight-prob × provider collections × margin. "
            "Coefficients are platform defaults; real-deal scoring "
            "would calibrate against the target's historical attrition."),
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
        common_questions=[
            "Does this deal match a known failure playbook?",
            "What structural patterns fire here?",
            "Which 12 patterns are scanned (Steward, Envision, Mednax)?",
            "What does each verdict band (GREEN/YELLOW/RED) trigger?",
            "Is the scan predictive or pattern-matching?",
        ],
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
        common_questions=[
            "What does this metric mean?",
            "How is this number calculated?",
            "What's the typical range for this metric in a healthcare deal?",
            "How does this metric differ across sectors?",
            "Which category does this metric belong to?",
        ],
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
        short_description="The canonical methodology hub — every model on the "
        "platform with its inputs, assumptions, formulas, and validation "
        "references in one place.",
        primary_purpose="Cite the underlying methodology when answering "
        "partner / IC / LP questions about how a number was computed; check "
        "an assumption before defending it.",
        common_questions=[
            "How does PEdesk compute MOIC / IRR / EBITDA bridge?",
            "What are the modeling assumptions behind the value-creation bridge?",
            "Which models are validated and which are still illustrative?",
            "What inputs does the predictive screener use?",
            "How is the conformal prediction interval constructed?",
            "Where can I cite this methodology for an IC packet?",
            "Has the methodology been updated since last quarter?",
        ],
        inputs=[
            "Model inputs are listed per-model on the page — packet data, "
            "HCRIS rows, scenario shocks, etc.",
        ],
        outputs=[
            "Per-model documentation: inputs list, assumptions, formula, "
            "calibration references, validation diagnostics, citations.",
        ],
        key_metrics=[
            "MOIC, IRR, EBITDA bridge, adjusted EBITDA, RCM uplift, "
            "leverage, confidence tier, benchmark percentile",
        ],
        data_sources=[
            "Source-code-derived: every model's formula and parameter "
            "set live in finance/, mc/, pe/, ml/, calibration/. The page "
            "renders the documented surface.",
        ],
        model_logic_summary=(
            "Hub page — does not compute on the fly. Renders documented "
            "model summaries built from finance.regression, mc.ebitda_mc, "
            "pe.rcm_ebitda_bridge, ml.ridge_predictor, ml.conformal, "
            "calibration. Each section explains a single model: its "
            "inputs, the formula or fit procedure, the validation "
            "diagnostic, and where in the codebase it lives. The "
            "/methodology/calculations sub-page expands on the math."
        ),
        why_it_matters=(
            "Defensibility. Partners citing a number in IC or to LPs "
            "need to point at the underlying methodology. This page is "
            "the single source of truth for 'how was this computed'."
        ),
        diligence_use_cases=[
            "Pre-IC: confirm the modeling assumption set for the bridge.",
            "LP discussion: cite the validation diagnostic for the "
            "predictive screener.",
            "Audit: trace a number back to its formula.",
        ],
        interpretation_guidance=[
            "If a model is marked 'illustrative' it has not been "
            "validated against held-out data — describe it as a "
            "structural framework, not a prediction.",
            "Conformal intervals are coverage guarantees under "
            "exchangeability — describe them as 'X% of similar deals "
            "fall within this interval', not 'X% probability'.",
            "Document version + last-update date are at the top of "
            "each section — cite both in IC packets.",
        ],
        limitations=[
            "Methodology page is descriptive, not prescriptive — does "
            "not modify any computation.",
            "Some models (e.g. RCM uplift bridge) describe a structural "
            "decomposition rather than a fitted prediction; this is "
            "called out explicitly.",
        ],
        related_routes=["/metric-glossary", "/methodology/calculations",
                        "/diligence/model-validation", "/methodology/sources"],
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
        common_questions=[
            "What deals are comparable to this profile?",
            "Where does the target sit vs the peer set?",
            "What's the loss rate / 3x+ rate in the peer set?",
            "Is the peer set drawn from real realized deals or illustrative?",
            "How does this differ from /find-comps and /comparable-outcomes?",
        ],
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
        common_questions=[
            "What's a good denial rate / days in A/R for this segment?",
            "Where do peers sit on these metrics?",
            "Which segments are covered (community, academic, ASC, etc.)?",
            "Are these bands from HFMA, MGMA, or proprietary data?",
            "Which direction is better (e.g. lower denial rate)?",
        ],
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
        common_questions=[
            "What deals are in the corpus?",
            "Show me realized deals in this sector / regime.",
            "What's the corpus P50 MOIC / loss rate?",
            "Is the corpus real public-data deals or illustrative?",
            "How big is the corpus (600+ deals)?",
        ],
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
        common_questions=[
            "Is this different from /library?",
            "Why does it redirect — is the route deprecated?",
            "Will my query string params survive the redirect?",
            "Should I update my bookmark to /library?",
            "When was the rename from /deals-library to /library?",
        ],
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
        short_description="Catalog of every public / CMS / commercial "
        "dataset feeding the platform — name, source URL, refresh "
        "cadence, last-loaded timestamp, row count, license terms.",
        primary_purpose="Document what external data is loaded, where "
        "it comes from, when it was last refreshed, and what it costs "
        "partners to cite — the platform's source-of-truth provenance "
        "page.",
        common_questions=[
            "What data is loaded on the platform?",
            "When was HCRIS last refreshed?",
            "What's the source URL for the CMS Care Compare data?",
            "What's the refresh cadence for each dataset?",
            "Can I cite this dataset for an IC packet?",
            "Are there license restrictions on any dataset?",
            "How big is each dataset (rows / GB)?",
            "Which datasets are stale?",
        ],
        inputs=[
            "data_source_status table (refresh history per dataset).",
            "Per-dataset registry entry (source URL, cadence, license).",
        ],
        outputs=[
            "Per-dataset row: name, source, refresh cadence, "
            "last-loaded timestamp, row count, license terms.",
            "Staleness flag when a dataset is past its refresh cadence.",
            "Filter by category (public / CMS / commercial / licensed).",
        ],
        key_metrics=[
            "Datasets loaded (count)", "Stale-dataset count",
            "Total platform row count", "Days since last full refresh",
        ],
        data_sources=[
            "data_source_status SQLite table (per-dataset metadata)",
            "Per-dataset loader modules in rcm_mc.data.* and "
            "rcm_mc.data_public.* which register their freshness "
            "stats here",
        ],
        model_logic_summary=(
            "Read-only catalog page. Reads data_source_status table, "
            "joins to per-dataset registry (source URL, cadence, "
            "license), computes staleness flag (now - last_loaded > "
            "cadence). No external API call at render time. Refresh "
            "actually happens via the CLI `rcm-mc data refresh` "
            "commands or the GitHub Actions data-refresh workflow."
        ),
        why_it_matters="Provenance. Every number on every page needs "
        "to be defensible. This page is where partners answer 'where "
        "did this come from' and 'is it current'. Without it, "
        "citing data in an IC packet becomes a research project.",
        diligence_use_cases=[
            "Pre-IC: confirm the source datasets backing the analysis "
            "are fresh enough.",
            "LP discussion: cite the source + last-refresh date.",
            "Operational: identify datasets that need a refresh "
            "before a critical analysis.",
        ],
        interpretation_guidance=[
            "Last-loaded timestamp is the platform's load time, not "
            "the dataset's publication date — some datasets are "
            "loaded months after they're published.",
            "Stale doesn't mean wrong — it means past the expected "
            "refresh cadence; the data is still valid for "
            "longer-tenured analyses.",
            "License terms matter for citations — some commercial "
            "datasets prohibit redistribution.",
        ],
        limitations=[
            "Refresh happens out-of-band (CLI / GitHub Actions); the "
            "page only reads status, doesn't trigger.",
            "Row counts are approximate for very large datasets.",
        ],
        related_routes=["/methodology", "/cms-sources",
                        "/data-refresh", "/admin/data-sources"],
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
        common_questions=[
            "What research is available?",
            "Where's the methodology / a given framework?",
            "How do I filter research by topic or format?",
            "How is this different from /library?",
            "Where's the conference roadmap?",
        ],
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
        common_questions=[
            "What did we note on this deal / topic?",
            "Show notes tagged X.",
            "How do I add a note to a deal?",
            "Are notes shared across the team or per-user?",
            "Can I search notes by author?",
        ],
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
        common_questions=[
            "Which sectors are heating up or cooling?",
            "How has MOIC moved by sector?",
            "What's the default window — 3 years, 5 years?",
            "Is sector momentum predictive or descriptive?",
            "Which sectors have seen the biggest deal-count drop?",
        ],
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
        common_questions=[
            "How wide is the realized IRR spread?",
            "What share clears a 20% hurdle?",
            "How does sector affect the IRR distribution?",
            "What's the historical loss rate (sub-1x) in the corpus?",
            "Is this prediction or historical observation?",
        ],
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
        common_questions=[
            "How does hold length relate to realized MOIC?",
            "What's the typical hold for this sector?",
            "Are longer holds correlated with higher MOIC or just more risk?",
            "Which hold-bucket has the best risk-adjusted returns?",
            "Which deals are outliers — long hold + sub-1x?",
        ],
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
        common_questions=[
            "What did comparable deals actually return?",
            "Is the projected MOIC above what comps achieved?",
            "What's the win rate (≥2.5×) in the comp set?",
            "How is similarity ranked — sector + EV + year, or more?",
            "How does this differ from /comparables and /find-comps?",
        ],
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
        common_questions=[
            "What's the bear case on this deal?",
            "How much EBITDA is at risk and why?",
            "Which modules contributed the critical-tier evidence?",
            "Can I drop the bear case into the IC memo?",
            "Are these evidence items predictions or codified observations?",
        ],
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
        common_questions=[
            "What regulatory events are coming?",
            "Which thesis drivers does an event threaten?",
            "What's a 'kill-switch' event?",
            "How does this differ from /diligence/regulatory-calendar?",
            "How is the calendar refreshed — manual, automated?",
        ],
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
        common_questions=[
            "How are public operators priced?",
            "What are private multiples for this specialty?",
            "Which news is the feed filtered to?",
            "How fresh are the multiples — quarterly, real-time?",
            "How does this differ from /market-intel/geo and /market-data/map?",
        ],
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
        common_questions=[
            "How accurate were the platform's predictions?",
            "What's the match rate against the corpus?",
            "What does the fallback show when no predictions exist?",
            "Which vintage / sector cohorts have the strongest fit?",
            "How is this different from /backtest?",
        ],
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
        common_questions=[
            "Do entry signals explain realized MOIC?",
            "What's the model's fit (R²/MAE)?",
            "Which entry signals correlate most with realized return?",
            "How does fit vary by sector?",
            "Is this corpus real or illustrative?",
        ],
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
                         "Which deals have stale data or overdue deadlines?",
                         "How does the aggregate risk rank combine covenant, "
                         "alerts, freshness, and CMS quality?",
                         "How does this differ from /alerts and /escalations?"],
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
        common_questions=[
            "Where does each deal stand vs benchmarks?",
            "Which deals are weak on which metrics?",
            "Which metrics are shown — denial, AR, payer mix?",
            "How is the cell color computed — quartile, percentile?",
            "How does this differ from /portfolio/risk-scan?",
        ],
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
        "against plan — daily-driver dashboard for partners in post-close.",
        primary_purpose="Track each portfolio company's actuals (revenue, "
        "EBITDA) against the value-creation plan over the hold; surface "
        "deals that are drifting behind so they get an action plan.",
        common_questions=[
            "Which portfolio companies are behind plan this quarter?",
            "What's the EBITDA realization rate across the portfolio?",
            "Which deals have triggered red alerts recently?",
            "How is hospital X tracking vs its underwriting plan?",
            "Where is the biggest miss vs synergy plan?",
            "What's the health score trend for my watchlist?",
            "Which deals need a partner check-in before LP update?",
            "What's the covenant headroom across the portfolio?",
        ],
        inputs=[
            "Live deal store (all tracked deals); latest monthly actuals; "
            "saved value-creation plan per deal; alert history.",
        ],
        outputs=[
            "Per-deal cards/rows with: health score (0-100 + sparkline), "
            "EBITDA % of plan, revenue % of plan, covenant cushion %, "
            "active alert count, last-actuals-as-of date, stage chip.",
        ],
        key_metrics=[
            "Health score (composite 0-100)", "EBITDA realization %",
            "Revenue realization %", "Covenant headroom %",
            "Days since last actuals", "Active red/amber alert counts",
        ],
        data_sources=[
            "Live SQLite deal store (rcm_mc.portfolio.store.PortfolioStore)",
            "monthly_actuals table (uploaded actuals)",
            "audit_log + alerts lifecycle for the alert counts",
        ],
        model_logic_summary=(
            "Aggregates the latest snapshot per tracked deal: pulls "
            "value-creation plan from deal_plan, monthly actuals from "
            "the actuals table, computes plan vs actual percentages, "
            "joins active alert counts from the alerts module, and "
            "computes a composite health score via "
            "rcm_mc.deals.health_score. Does not run a Monte Carlo — "
            "summary read of the most-recent state."
        ),
        why_it_matters="Post-close, the question shifts from 'should we buy' "
        "to 'are we realizing the plan' — this is that read. Partners use "
        "it as the morning-check dashboard before the weekly portfolio "
        "review.",
        diligence_use_cases=[
            "Pre-LP-update: scan for deals that need a status update.",
            "Weekly partner review: confirm every red deal has an owner.",
            "Monthly underwriting check: compare actual EBITDA % of plan "
            "across deals.",
        ],
        interpretation_guidance=[
            "Monthly actuals are unaudited and can be reclassified; read "
            "trends, not single months.",
            "Plan vs actual gaps are the signal — model/synergy estimates "
            "are the plan, not realized results.",
            "Health score 80+ = green, 60-79 = amber, <60 = red. Below 60 "
            "should have an active alert.",
            "If 'days since last actuals' > 60 the EBITDA % is stale; "
            "treat it as the last-known-state, not current.",
        ],
        limitations=[
            "Only shows deals the user has loaded into the deal store; "
            "doesn't see market deals.",
            "Plan vs actual depends on a saved plan; deals without a "
            "plan show '—' on those columns.",
            "Health score is a heuristic — does not replace partner "
            "judgment.",
        ],
        metric_ids=["ebitda", "adjusted_ebitda", "revenue", "synergy_estimate",
                    "health_score", "covenant_cushion"],
        data_source_ids=["monthly_actuals", "portfolio_snapshot",
                         "model_output", "audit_log"],
        related_routes=["/portfolio", "/portfolio/risk-scan", "/lp-update",
                        "/alerts", "/escalations", "/watchlist"],
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/portfolio/map", "Portfolio Map",
        short_description="A geographic map of portfolio deals — markers at "
        "state centroids colored by stage and sized by EBITDA opportunity, "
        "with state shading for CON status.",
        primary_purpose="Visualize where the portfolio's deals sit "
        "geographically and how they cluster by stage and size.",
        common_questions=[
            "Where are our deals geographically?",
            "Which states carry the most opportunity?",
            "What does the marker color (stage) mean?",
            "What does the state-shading CON status indicate?",
            "How does this differ from /portfolio/heatmap?",
        ],
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
                         "Where is return concentration / outlier risk?",
                         "What vintages and sectors are over- or under-represented?",
                         "How is MOIC P25/P50/P75 computed across the 655-deal corpus?"],
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
        common_questions=[
            "How has this sponsor performed historically?",
            "Which sponsors are consistent vs lottery-like?",
            "How is the 0-1 consistency score computed?",
            "What's the home-run rate definition?",
            "Are these realized corpus outcomes or current marks?",
        ],
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
        common_questions=[
            "Does payer mix relate to returns?",
            "How do returns differ by payer regime?",
            "What are the four payer-regime bands?",
            "What's the commercial-share / MOIC correlation?",
            "How does this differ from /payer-rate-trends?",
        ],
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
                         "What changed this period?",
                         "What window does 'this period' use, and can I pick it?",
                         "Is the downloaded HTML safe to send to LPs as-is, or does it need review?"],
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
        common_questions=[
            "What engagements are active?",
            "What's the status of this client engagement?",
            "Who's on the engagement team?",
            "How does engagement access (members/deliverables) work?",
            "How is this different from the PE deal pipeline?",
        ],
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
        common_questions=[
            "What hospitals are in this state?",
            "How big is this state's hospital market?",
            "What HCRIS fields does each row show?",
            "How does this differ from /state-profile and /county-explorer?",
            "Why does the URL hardcode CA — is there per-state routing?",
        ],
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
        key_metrics=["Live-sector count", "Roadmap-sector count",
                     "Per-sector CMS data status"],
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
            "How is freshness defined per source — and what triggers a re-ingest?",
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
                         "Is this the target's real mix or a placeholder?",
                         "How does the model translate a mix shift into a "
                         "revenue / margin delta?",
                         "How does this differ from /diligence/payer-stress and /payer-intelligence?"],
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
        common_questions=[
            "What is this target's operating cost per bed / patient-day?",
            "Which figures are real vs modeled?",
            "How does opex per bed compare to HCRIS sector medians?",
            "Is the COGS / SG&A / labor split from real HCRIS or modeled?",
            "How do I attach a CCN to get real HCRIS values?",
        ],
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
        common_questions=[
            "Can this target cover debt service from operations?",
            "Which numbers are real vs required?",
            "What's the HCRIS operating-cash proxy formula?",
            "What debt-term inputs do I need to upload to get a real DSCR?",
            "How does this connect to /cap-structure and /covenant-headroom?",
        ],
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
        common_questions=[
            "Which CMS APMs are active and when do they sunset?",
            "Is the portfolio exposure shown my real data?",
            "What APMs is the target eligible to participate in?",
            "How do APM risk-track choices affect the deal economics?",
            "Where can I see live CMMI program updates?",
        ],
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
                         "Is this real or illustrative? Where's it from?",
                         "How does /deal-library differ from /library and /deal-library/comps?",
                         "How fresh is the CapIQ data, and which sponsors are most thinly covered?"],
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
        common_questions=[
            "Which sponsors back the most healthcare companies?",
            "How many of sponsor X's are current vs prior?",
            "Does the index include VC and REITs, not just PE buyouts?",
            "What's the coverage rate on sponsor parsing (~99%?)?",
            "How does this differ from /sponsor-league?",
        ],
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
        common_questions=[
            "What EV/Revenue / EV/EBITDA do disclosed healthcare companies trade at?",
            "How big is the sample?",
            "Are these multiples from public-company filings or private deals?",
            "Why is the sample much smaller than the full company list?",
            "How does this differ from /find-comps and /comparables?",
        ],
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
            "How is the partial market score weighted across the demand / "
            "supply / consolidation signals?",
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
            "Which of the five healthcare industries is covered, and how stale "
            "is each report's vintage?",
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
        common_questions=[
            "What's a top-quartile wRVU figure for this specialty?",
            "How does this group's productivity compare to MGMA-style ranges?",
            "Is the area a designated HPSA (shortage area)?",
            "Are these benchmark figures licensed MGMA or representative?",
            "How does panel size affect wRVU productivity reading?",
        ],
        inputs=["Entered per-provider wRVU, visits, and panel "
                "size for each provider in the group's roster.",
                "Specialty and state scope so the benchmark "
                "bands and HPSA overlay anchor to the right "
                "market."],
        outputs=["Each provider's quartile percentile vs the "
                 "specialty benchmark + the group's quartile "
                 "mix; real CMS MIPS and HRSA HPSA panels as the "
                 "local context layer."],
        key_metrics=["wRVU percentile (entered)",
                     "Group quartile mix",
                     "MIPS distribution by state (real)",
                     "HRSA HPSA designations (real)"],
        diligence_use_cases=[
            "Spotting productivity outliers (top-decile vs "
            "bottom-quartile) within a physician-group deal.",
            "Sizing the productivity-uplift lever from moving the "
            "bottom quartile to median wRVU.",
        ],
        data_sources=["Representative MGMA/AMGA-style benchmark ranges "
                      "(illustrative); real CMS MIPS distribution; real HRSA HPSA."],
        interpretation_guidance=[
            "Computes off YOUR inputs; benchmark ranges are illustrative.",
            "MIPS/HRSA panels are national/market context — NOT this group's "
            "providers and NOT a payment figure.",
        ],
        limitations=["Benchmark ranges are representative, not licensed MGMA."],
        model_logic_summary=(
            "Reads entered per-provider wRVU/visit/panel inputs; "
            "compares each to representative MGMA-style specialty "
            "quartile bands and reports each provider's percentile + "
            "the group's quartile mix. Overlays the real CMS MIPS "
            "distribution and HRSA HPSA designation as the local "
            "context layer."),
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
        common_questions=[
            "What's the cost of losing a key provider?",
            "How does the target's turnover compare to the ~45% nurse-sector median?",
            "Is the at-risk watchlist real names or illustrative scaffold?",
            "How does retention spend translate into EBITDA?",
            "Where do I plug in the target's actual HR roster?",
        ],
        inputs=["Entered role-level churn assumptions (annual %), "
                "replacement-cost per role, and the target's role "
                "mix.",
                "State / facility scope so the CMS Care Compare "
                "nurse-turnover overlay anchors to the right "
                "market."],
        outputs=["EBITDA drag estimate from replacement cost + "
                 "productivity-dip on entered assumptions + the "
                 "real CMS nurse-staff turnover sector benchmark "
                 "(median ~45%)."],
        key_metrics=["Annual provider churn % (entered)",
                     "EBITDA drag from churn ($)",
                     "CMS nurse-staff turnover (real, sector)"],
        diligence_use_cases=[
            "Sizing provider/staff retention risk for a deal in a "
            "high-turnover sector (skilled nursing, dialysis).",
            "Pressure-testing whether a retention-bonus program "
            "pays back through reduced replacement cost.",
        ],
        data_sources=["Representative role-level churn assumptions (illustrative) "
                      "+ real CMS nurse-staff turnover (median ~45%)."],
        interpretation_guidance=[
            "Calculator on your inputs; the at-risk watchlist is illustrative "
            "scaffold — connect an HR roster for real individuals.",
            "CMS turnover is a sector benchmark, NOT this deal's roster.",
        ],
        limitations=["Deal-specific retention requires the target's HR roster."],
        model_logic_summary=(
            "Applies entered role-level churn assumptions to the "
            "target's role mix to estimate EBITDA drag (replacement "
            "cost + productivity dip) and projects an at-risk "
            "watchlist. Overlays the real CMS nurse-staff turnover "
            "(median ~45%) as the sector benchmark."),
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
        common_questions=[
            "What MIPS score is competitive for this physician sector?",
            "How much EV would a one-star improvement add for a SNF?",
            "Is the benchmark MIPS or Care Compare for this sector?",
            "Does the page show this deal's quality or a sector frame?",
            "Where do I plug in the target's actual measure scores?",
        ],
        inputs=["Sector (physician vs nursing/post-acute), "
                "entered current quality posture, and quality-to-"
                "revenue conversion rate.",
                "State scope so the right benchmark (MIPS or "
                "Care Compare 5-star) anchors to the right "
                "market."],
        outputs=["Sector-aware quality percentile + EV uplift "
                 "estimate for moving up one quality band on the "
                 "entered conversion."],
        key_metrics=["Quality percentile vs benchmark",
                     "EV uplift per band move ($)",
                     "MIPS / Care Compare 5-star distribution (real)"],
        diligence_use_cases=[
            "Sizing the quality-uplift lever for a physician-group "
            "deal whose MIPS scores trail the sector median.",
            "Sizing the Star-rating-bonus lever for a SNF deal "
            "moving from 3-star to 4-star.",
        ],
        data_sources=["Illustrative quality model + real CMS MIPS (physician) / "
                      "Care Compare 5-star (nursing) distribution."],
        interpretation_guidance=[
            "Calculator on your inputs; benchmark is real CMS sector data, NOT "
            "this deal's score.",
        ],
        limitations=["Benchmark picked by sector; deal-specific quality needs "
                     "the target's measure data."],
        model_logic_summary=(
            "Maps entered quality posture into the right CMS "
            "distribution per sector (MIPS for physician groups, "
            "Care Compare 5-star for nursing/post-acute); computes "
            "EV uplift via entered quality-to-revenue conversion. "
            "Benchmark is real; the conversion is the entered model."),
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
        common_questions=[
            "What CMS quality measures matter for this sector?",
            "How does the target's clinical-outcomes profile compare "
            "to the sector benchmark?",
            "What EV uplift does the calculator suggest for moving "
            "outcomes one quartile?",
            "Is the EV uplift figure from real outcomes data or "
            "modeled from my inputs?",
            "Where do I see the actual measure-by-measure CMS data?",
        ],
        inputs=["Sector, entered current outcomes posture, "
                "outcome-to-revenue conversion rate."],
        outputs=["Sector quartile placement + EV uplift to move "
                 "outcomes one quartile."],
        key_metrics=["Outcome quartile", "EV uplift per quartile",
                     "Sector benchmark band"],
        diligence_use_cases=["Sizing clinical-quality value-creation "
                             "for the deal's bridge."],
        data_sources=["Illustrative outcomes model + real CMS quality-measure "
                      "rating distribution."],
        interpretation_guidance=["Calculator on your inputs; CMS benchmark is "
                                "sector context, not this deal's outcomes."],
        limitations=["Deal-specific outcomes need the target's measure data."],
        model_logic_summary=(
            "Maps entered current outcomes against the real CMS Care "
            "Compare quartile distribution, then computes a directional "
            "EV uplift for moving one quartile via an entered "
            "outcome-to-revenue conversion. Benchmark is real; the "
            "uplift conversion is the entered model assumption."),
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
        common_questions=[
            "What's the base-rate enforcement risk for this sector?",
            "How much does the average fine cost — and what's max exposure?",
            "Is the CMS enforcement anchor SNF-only or broader?",
            "How does this differ from /antitrust-screener?",
            "What enforcement vectors are NOT captured by this model?",
        ],
        inputs=["Entered violation-frequency, average fine, and "
                "compliance-cost assumptions for the deal's "
                "facility footprint.",
                "Sector + state scope so the CMS SNF enforcement "
                "overlay (where applicable) anchors to the right "
                "market."],
        outputs=["Annual regulatory-risk dollar exposure on the "
                 "entered assumptions + the real CMS SNF "
                 "enforcement base rate (45% of facilities fined, "
                 "$467M total) where the sector is SNF."],
        key_metrics=["Annual fine exposure ($)",
                     "Compliance cost ($)",
                     "CMS SNF enforcement base rate (real)"],
        diligence_use_cases=[
            "Sizing regulatory/enforcement exposure for a SNF or "
            "post-acute deal where the base-rate fines are real.",
            "Stress-testing how a doubling of violation rate "
            "reprices the EBITDA bridge.",
        ],
        data_sources=["Illustrative risk model + real CMS SNF enforcement "
                      "(45% fined, $467M total)."],
        interpretation_guidance=["Calculator on your inputs; CMS enforcement is "
                                "a sector base rate, not this deal's exposure."],
        limitations=["Enforcement anchor is nursing-sector only."],
        model_logic_summary=(
            "Applies entered violation-frequency, avg-fine, and "
            "compliance-cost assumptions to the deal's facility "
            "count; for SNF, overlays the real CMS enforcement base "
            "rate (45% of facilities fined, $467M total). For non-"
            "SNF sectors, only the calculator runs — no public "
            "enforcement anchor."),
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
        common_questions=[
            "What supply-savings rate is achievable in this sector?",
            "How does FDA drug-shortage exposure factor into the model?",
            "Are the savings figures real or modeled from my inputs?",
            "Which therapeutic categories have the most active shortages?",
            "Does the calculator account for GPO membership?",
        ],
        inputs=["Entered savings-rate, GPO membership flag, and "
                "spend base for the deal's supply categories.",
                "Therapeutic-category mix so the FDA drug-"
                "shortage overlay anchors to the deal's exposure."],
        outputs=["Annual supply-savings estimate on the entered "
                 "assumptions + the real FDA drug-shortage panel "
                 "(1,156 active products across 58 categories) "
                 "highlighting risk concentration."],
        key_metrics=["Annual supply savings ($)",
                     "Savings rate (entered)",
                     "Active FDA shortages by category (real)"],
        diligence_use_cases=[
            "Sizing the supply-savings lever for a deal with "
            "meaningful drug or device spend.",
            "Flagging therapeutic-category shortage exposure when "
            "the target depends on at-risk products.",
        ],
        data_sources=["Illustrative savings model + real FDA drug shortages "
                      "(1,156 active across 58 categories)."],
        interpretation_guidance=["Calculator on your inputs; FDA shortage is a "
                                "national product-level signal, not this deal's book."],
        limitations=["Shortage data is product-level, not provider-specific."],
        model_logic_summary=(
            "Applies entered savings-rate, GPO membership, and spend "
            "base to compute supply savings; overlays the real FDA "
            "drug-shortage panel (1,156 active across 58 categories) "
            "so risk concentration in the deal's therapeutic mix is "
            "visible alongside the savings estimate."),
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
        common_questions=[
            "What's the EV impact of shifting 10pp from Medicaid to commercial?",
            "How fast is the payer trend changing nationally?",
            "Is the CIVHC anchor representative outside Colorado?",
            "Where does the model assume the shifted lives go?",
            "How does this connect to /payer-rate-trends?",
        ],
        inputs=["Entered Δ-percentage-point shift between payer "
                "types (e.g. −10pp Medicaid, +10pp commercial) "
                "plus the deal's current payer mix and per-payer "
                "rate factors.",
                "State scope so the CIVHC CO payer-cost trend "
                "overlay anchors to the right reference market."],
        outputs=["Revenue / EV impact of the entered payer-mix "
                 "shift + the real CIVHC Colorado all-payer cost "
                 "trend by payer type as the directional reference."],
        key_metrics=["Revenue Δ from payer-mix shift ($)",
                     "EV impact at deal multiple",
                     "CIVHC CO PPPY trend by payer (real)"],
        diligence_use_cases=[
            "Sizing the EV upside (or downside) of a deliberate "
            "payer-mix shift over the hold period.",
            "Stress-testing how a Medicaid-share decline (e.g. "
            "unwinding tailwind) reprices a deal's revenue.",
        ],
        data_sources=["Illustrative shift model + real CIVHC CO payer-cost "
                      "trend by payer type."],
        interpretation_guidance=["Calculator on your inputs; CIVHC is Colorado "
                                "all-payer market context, NOT this deal's mix."],
        limitations=["CIVHC anchor is Colorado-only."],
        model_logic_summary=(
            "Applies entered shift Δ-percentage points (e.g. -10pp "
            "Medicaid, +10pp commercial) to the deal's payer mix and "
            "recomputes revenue using each payer's rate factor. "
            "Overlays the real CIVHC Colorado all-payer cost trend "
            "by payer type as the directional reference."),
        related_routes=["/payer-rate-trends", "/cost-structure"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/ma-contracts", "MA Contracts",
        short_description="An MA-contract economics calculator on your inputs, "
        "anchored to the real CMS MA enrollment market size.",
        primary_purpose="Frame MA contract economics against the real MA market.",
        common_questions=[
            "What PMPM is competitive for this MA contract structure?",
            "How big is the MA market in this state?",
            "Does the model account for Star Ratings or risk scores?",
            "Where are CMS MA enrollment figures from?",
            "How does this connect to /risk-adjustment?",
        ],
        inputs=["Entered PMPM, attribution share, risk-track haircut, "
                "and the deal's MA-exposed lives.",
                "State scope so the real CMS MA enrollment overlay "
                "anchors to the right market."],
        outputs=["Expected revenue per contract on the entered "
                 "structure + the CMS MA enrollment panel "
                 "(29.7M lives across 53 states) as market-scale "
                 "context."],
        key_metrics=["Expected MA revenue per contract ($)",
                     "PMPM (entered)", "MA enrollment by state (real)"],
        diligence_use_cases=[
            "Pressure-testing an MA contract economics assumption "
            "against the state's real MA market size.",
            "Framing how much of the state's MA pool the deal "
            "captures (or could capture) under a proposed contract.",
        ],
        data_sources=["Illustrative PMPM/risk model + real CMS MA Geographic "
                      "Variation enrollment (29.7M across 53 states)."],
        interpretation_guidance=["Calculator on your inputs; MA enrollment is "
                                "market context, not this deal's contract."],
        limitations=["No Star Ratings / risk scores in the anchor (enrollment "
                     "+ demographics only)."],
        model_logic_summary=(
            "Applies entered PMPM, attribution share, and risk-track "
            "haircut to the deal's MA-exposed lives to compute "
            "expected revenue per contract; overlays the real CMS MA "
            "enrollment panel (29.7M lives across 53 states) as "
            "market-scale context. Contract terms are illustrative; "
            "the enrollment overlay is real."),
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
        common_questions=[
            "What's a normal RAF score for a Medicare Advantage population?",
            "How much does dual-eligible mix shift RAF?",
            "Are the RAF numbers on this page from real data or illustrative?",
            "What CMS population data drives the right-side panel?",
            "Where do I get the target's actual coding intensity?",
        ],
        inputs=["No user inputs into the RAF scaffold itself "
                "(it is a fixed illustrative model).",
                "State scope so the real CMS MA population panel "
                "(dual-eligible share, age 65+ mix) anchors to "
                "the right market."],
        outputs=["A scaffold RAF read with the real CMS MA "
                 "population panel — the demographic drivers of "
                 "RAF (dual-eligible share, age 65+ mix by state) "
                 "shown alongside the illustrative RAF figure."],
        key_metrics=["Illustrative RAF (fixed)",
                     "Dual-eligible share by state (real)",
                     "Age 65+ mix by state (real)"],
        diligence_use_cases=[
            "Framing the demographic backdrop driving RAF — "
            "where dual-eligible share is high, RAF and coding "
            "intensity matter more.",
            "Pointing diligence at the right ask: the target's "
            "actual encounter data is what unlocks a real RAF read.",
        ],
        data_sources=["Illustrative RAF model + real CMS MA dual-eligible / age "
                      "population mix by state."],
        interpretation_guidance=[
            "The RAF figures are illustrative (fixed model); the MA population "
            "panel is real CMS context — NOT a Star Rating, NOT a risk score, "
            "NOT this deal.",
        ],
        limitations=["RAF model is illustrative; real coding intensity needs "
                     "the target's encounter data."],
        model_logic_summary=(
            "Illustrative fixed-RAF scaffold for MA risk-adjustment "
            "intensity; overlays the real CMS MA population panel "
            "(dual-eligible share, age 65+ mix by state) so the "
            "demographic drivers of RAF — not RAF itself — are "
            "anchored in observed CMS data. Real coding intensity "
            "needs the target's encounter file."),
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
        common_questions=[
            "Which drug categories are in active shortage right now?",
            "How does the page get from FDA data to a portfolio risk score?",
            "Is the FDA data live or a snapshot?",
            "Why do some products have a blank availability field?",
            "How does drug-shortage exposure affect pharmacy / 340B operations?",
        ],
        inputs=["The openFDA drug-shortage snapshot (committed); "
                "therapeutic-category filter."],
        outputs=["Active-shortage product list grouped by category, "
                 "with availability/status flag per product."],
        diligence_use_cases=["Reading drug-shortage exposure for a "
                             "pharmacy-dependent target during diligence."],
        data_sources=["openFDA drug shortages (committed snapshot; no runtime "
                      "network)."],
        key_metrics=["Active shortages", "Therapeutic categories",
                     "Resolved count"],
        interpretation_guidance=[
            "Real FDA data; product-level and national — NOT provider-specific.",
            "Availability field is ~31% blank (preserved, not zero-filled).",
        ],
        limitations=["Product-level; build-time snapshot refreshed on re-ingest."],
        model_logic_summary=(
            "No model — reads the committed openFDA drug-shortage "
            "snapshot, groups products by therapeutic category, and "
            "ranks by active-shortage count. Availability field is "
            "preserved verbatim (blanks not filled). The 'portfolio "
            "risk' framing is editorial overlay; the data itself is "
            "national/product-level, not provider-specific."),
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
        common_questions=[
            "How has commercial PPPY trended vs Medicaid in this market?",
            "What years are covered by the trend data?",
            "Is this data Colorado-only or national?",
            "Why are some values missing — should I impute them?",
            "How does this differ from /payer-shift?",
        ],
        inputs=["No user inputs — this is a transparency view on "
                "the committed CIVHC CO APCD cost-of-care snapshot."],
        outputs=["PPPY spend by payer type and year as a time "
                 "series, with NaNs preserved (never zero-imputed)."],
        diligence_use_cases=[
            "Showing IC how commercial vs Medicaid PPPY actually "
            "moved in a real all-payer market over the trend window.",
            "Anchoring a payer-rate forecast to the observed CO "
            "APCD trajectory rather than a national average.",
        ],
        data_sources=["CIVHC CO APCD public cost-of-care (committed snapshot)."],
        key_metrics=["PPPY spend by payer type", "% change over years"],
        interpretation_guidance=[
            "Real Colorado all-payer market data — NOT this deal's payer mix "
            "and NOT national.",
            "Missing values preserved as NaN, never zero.",
        ],
        limitations=["Colorado-only; all-payer aggregate, not provider-level."],
        model_logic_summary=(
            "No model — reads the committed CIVHC CO APCD cost-of-"
            "care snapshot, groups PPPY spend by payer type and year, "
            "and renders the time series. Missing values stay NaN. "
            "The page is a transparency view on real all-payer data."),
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
        common_questions=[
            "What % of Medicare is the target getting from commercial payers?",
            "Is 200% of Medicare high or normal for this market?",
            "Can I look up a specific provider's ratio by name?",
            "How does this connect to the deal's negotiating leverage?",
            "Why does the ratio vary by claim type or payer?",
        ],
        inputs=["No user inputs — this is a transparency view on "
                "the committed CIVHC Colorado Reference-Based "
                "Pricing snapshot.",
                "Provider-name / county filter so a partner can "
                "drill to a specific organization or geography."],
        outputs=["A provider-level commercial-vs-Medicare ratio "
                 "table (resolvable to CMS CCN by name), with "
                 "claim-type and payer min/median/max breakouts."],
        diligence_use_cases=[
            "Looking up a Colorado target's real commercial-%-of-"
            "Medicare ratio to anchor negotiating-leverage "
            "diligence.",
            "Comparing peer providers' ratios at the county / "
            "claim-type level to size a payer-renegotiation "
            "thesis.",
        ],
        data_sources=["CIVHC CO Medicare Reference-Based Pricing (committed "
                      "snapshot)."],
        key_metrics=["Hospital % of Medicare", "Claims", "Payer min/median/max"],
        interpretation_guidance=[
            "Real Colorado provider-level data (resolvable to CCN by name); "
            "% of Medicare = commercial/Medicare ratio.",
            "CO-only; ~1% missing on URF/payer fields (preserved).",
        ],
        limitations=["Colorado-only; provider names resolve to CCN imperfectly."],
        model_logic_summary=(
            "No model — reads the CIVHC CO Reference-Based Pricing "
            "snapshot, joins each provider's commercial-vs-Medicare "
            "ratio at claim-type granularity, and resolves names "
            "to CMS CCN where possible. Missing rows stay NaN; "
            "the percentages are the real provider-vs-Medicare ratio."),
        related_routes=["/payer-rate-trends", "/cost-structure", "/payer-stress"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    # ── Core deal/portfolio workflow pages (operate on the live deal store) ──
    # (/portfolio/monitor already documented earlier with metric/data-source
    #  links — no duplicate here.)
    # ── More live-deal-store workflow pages (Queue 6, batch 2) ──
    _ctx(
        "/cohorts", "Cohorts",
        short_description="Group deals into cohorts for slicing and comparison.",
        primary_purpose="Define and review deal cohorts across the book.",
        common_questions=[
            "Which deals are in the cohort I just created?",
            "How do my SaaS / hospital / ASC cohorts compare on "
            "health score?",
            "Can I tag a deal into multiple cohorts?",
            "How do cohorts differ from tags or watchlists?",
            "Why is my cohort empty — did I forget to tag deals?",
        ],
        inputs=["Cohort definitions and deal-tag assignments from "
                "the deal store."],
        outputs=["Per-cohort summary cards (deal count, weighted "
                 "MOIC/IRR, health-score distribution)."],
        key_metrics=["Cohort size", "Weighted MOIC", "Health-score mix"],
        diligence_use_cases=["Comparing strategic groupings of deals "
                             "to spot performance/risk patterns."],
        data_sources=["Live deal store (cohort membership)."],
        interpretation_guidance=["Operates on YOUR tracked deals."],
        limitations=[
            "Cohorts aggregate whatever's currently tracked in the deal "
            "store; an empty cohort reflects tagging gaps, not absence "
            "of activity in that segment.",
            "Cohort membership is partner-defined — there's no automatic "
            "rule engine that adds new deals to existing cohorts."],
        model_logic_summary=(
            "Reads cohort-tag membership from the deal store; for each "
            "cohort, aggregates the deals' summary metrics (MOIC, IRR, "
            "health score) and ranks/compares them. No model — pure "
            "set membership + aggregation."),
        related_routes=["/pipeline", "/portfolio", "/owners"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/deadlines", "Deadlines",
        short_description="Deal deadlines and key dates across the portfolio.",
        primary_purpose="Track upcoming deal/portfolio deadlines.",
        common_questions=[
            "What's overdue across the book right now?",
            "Which deadlines hit in the next 7 days?",
            "How do I filter to just my owned deals' deadlines?",
            "Where do these deadlines come from — manual entry or "
            "auto-generated?",
            "Can I mark a deadline complete from this page?",
        ],
        inputs=["Deal-store deadlines (entered title, due_date, "
                "owner, deal); time-window filter."],
        outputs=["Sorted deadline list with overdue/next-7-days "
                 "flagging; per-owner breakdown."],
        key_metrics=["Overdue count", "Next-7-days count", "By owner"],
        diligence_use_cases=["Pre-IC / pre-LP-update deadline "
                             "review across the portfolio."],
        data_sources=["Live deal store (deadlines)."],
        interpretation_guidance=["Reflects deadlines entered for your deals; "
                                "empty means none recorded."],
        limitations=[
            "Shows only deadlines a partner has entered into the deal "
            "store — this is not a calendar feed; undocumented "
            "obligations don't appear here.",
            "'Overdue' is computed against today's date relative to the "
            "stored due date; timezone differences can shift edge cases."],
        model_logic_summary=(
            "Reads deadlines from the deal store, sorted by due date; "
            "'overdue' = due_date < today; 'next 7 days' = today < "
            "due_date ≤ today+7. No projection — partners must enter "
            "deadlines manually for them to appear here."),
        related_routes=["/alerts", "/pipeline", "/day-one"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/owners", "Owners",
        short_description="Deal owner assignments across the team — who's "
        "responsible for which deals, with the per-owner book size and "
        "active alert load.",
        primary_purpose="Manage deal ownership across the team so every "
        "deal has a clear partner-of-record and no owner is overloaded; "
        "balance the book on volume + complexity + alert load.",
        common_questions=[
            "Who owns this deal?",
            "Which partner has the largest book?",
            "Which owner has the most active red alerts?",
            "Who's the partner for hospital X?",
            "How do I reassign a deal to a different owner?",
            "Which deals don't have an owner assigned?",
            "What's the owner workload distribution?",
        ],
        inputs=[
            "Live deal store with owner assignment table.",
            "Optional: alert load per owner from the alerts module.",
        ],
        outputs=[
            "Per-owner table: book size, active red/amber alerts, "
            "average deal age, deal stage breakdown.",
            "Unassigned-deals list (deals with no owner).",
            "Workload distribution chart.",
        ],
        key_metrics=[
            "Deals per owner", "Active alerts per owner",
            "Unassigned deal count", "Average deal age per owner",
        ],
        data_sources=["Live deal store (owner assignments)",
                      "Alerts module (active counts per owner)"],
        model_logic_summary=(
            "Joins deals to their assigned owner (deal_owners table), "
            "aggregates count + average age + alert load per owner. "
            "Unassigned deals = deals with NULL owner_id. Logic in "
            "rcm_mc.deals.deal_owners. Pure read; reassignment goes "
            "via the POST /api/deals/<id>/owner endpoint."
        ),
        why_it_matters="Clear partner-of-record drives accountability. "
        "Without it, deals slip — the worst portfolio outcomes "
        "frequently trace to a deal that had no clear owner during "
        "a tough stretch.",
        diligence_use_cases=[
            "Weekly portfolio review: confirm every deal has an owner.",
            "Team load-balancing: identify overloaded partners.",
            "New-hire onboarding: reassign a chunk of the book.",
        ],
        interpretation_guidance=[
            "Operates on YOUR tracked deals/team.",
            "An owner with zero alerts may mean a clean book OR a "
            "stale book — check deal age before celebrating.",
            "Reassignment audit-logs in /audit; reviewable if a "
            "partner asks why ownership changed.",
        ],
        limitations=[
            "Single-owner model — does not support co-leads or "
            "specialist support roles natively.",
            "Workload heuristic; partner judgment on capacity wins.",
        ],
        related_routes=["/pipeline", "/cohorts", "/my/AT",
                        "/audit", "/users"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/exports", "Exports",
        short_description="Generated exports (LP updates, CSVs, IC packets) "
        "with status, age, and a download history — the audit trail of "
        "everything sent to LPs or stakeholders.",
        primary_purpose="Produce partner/LP-ready exports from live data "
        "AND keep an audit trail of what was generated when so partners "
        "can re-share or revert if a number changed.",
        common_questions=[
            "What exports have I generated?",
            "When was the last LP update produced?",
            "How do I generate a new IC packet?",
            "Can I download a previous LP update?",
            "What format is the export in (PDF / DOCX / CSV)?",
            "How do I know if an export is stale?",
            "Where do exports live (storage)?",
        ],
        inputs=[
            "Live deal store (current state for the export).",
            "Export type (LP update, IC packet, deal CSV, "
            "portfolio CSV).",
            "Optional: as-of date for historical re-run.",
        ],
        outputs=[
            "Generated artifact (PDF / DOCX / CSV / XLSX depending on type).",
            "Download history table: artifact, type, deal/portfolio "
            "scope, generated-at, partner-of-record, file size.",
            "Stale-export flag when the underlying data has changed "
            "since generation.",
        ],
        key_metrics=[
            "Generated exports (count by type)",
            "Days since last LP update",
            "Stale-export count",
        ],
        data_sources=[
            "Live deal store (current data for exports)",
            "generated_exports table (audit trail of past exports)",
        ],
        model_logic_summary=(
            "Two surfaces: (1) generation — calls the appropriate "
            "renderer (lp_update, ic_packet_builder, csv_exporter) "
            "and writes the artifact to disk + audit row. (2) Browse "
            "— lists past artifacts from generated_exports table with "
            "download links. Stale check compares export's "
            "data_as_of vs current portfolio_snapshot timestamp."
        ),
        why_it_matters="Exports are the deliverable. LP updates, IC "
        "packets, board books — partners are judged on their quality "
        "and timeliness. The audit trail prevents 're-share confusion' "
        "when an export becomes stale.",
        diligence_use_cases=[
            "Monthly LP cycle: generate + send the LP update.",
            "Pre-IC: produce the latest IC packet for the deal.",
            "Audit: re-download a prior period's export.",
        ],
        interpretation_guidance=[
            "Exports reflect current live data at generation time.",
            "If an export is flagged stale, re-generate before sharing.",
            "Download history is permanent — never deleted, but "
            "individual artifacts can be archived for storage hygiene.",
        ],
        limitations=[
            "Generation can be slow for portfolio-wide exports; "
            "expect 30-60s for an LP update.",
            "Stale flag is based on data_as_of comparison; doesn't "
            "detect content changes within a stable as-of.",
        ],
        related_routes=["/lp-update", "/exports/lp-update",
                        "/diligence/ic-packet", "/audit"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    # ── Analytic calculators / corpus analytics (Guide-coverage batch) ──
    _ctx(
        "/aco-economics", "ACO Economics",
        short_description="ACO shared-savings economics calculator on your inputs.",
        primary_purpose="Model ACO/value-based shared-savings economics for a deal.",
        common_questions=[
            "What shared-savings rate does the ACO model assume?",
            "How does benchmark-vs-spend translate into provider revenue?",
            "What's the break-even attribution count for an ACO?",
            "How sensitive is the deal economics to risk-track choice?",
            "Where are the inputs vs the defaults documented?",
        ],
        inputs=["Benchmark spending, actual spending, attribution "
                "count, shared-savings rate, risk-track choice."],
        outputs=["Estimated ACO revenue, savings opportunity, break-"
                 "even attribution count, sensitivity to risk track."],
        key_metrics=["Shared savings", "Provider revenue",
                     "Break-even attribution"],
        diligence_use_cases=["Sizing the ACO/value-based contribution "
                             "to deal economics under different "
                             "risk-track assumptions."],
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs; defaults are "
                                "illustrative, not a specific ACO's results."],
        limitations=[
            "Calculator only — no live MSSP / REACH benchmark feed; "
            "the savings rate is whatever assumption is entered.",
            "Quality bonus and risk-track economics are simplified — "
            "consult the CMS APM specifications for the production formula."],
        model_logic_summary=(
            "Reads entered benchmark spending, actual spending, and "
            "attribution count; applies the entered shared-savings rate "
            "and risk-track haircut to compute provider revenue. The "
            "math is straightforward — savings = benchmark − spend, "
            "provider take = savings × rate; the assumptions, not the "
            "formula, drive variance."),
        related_routes=["/cms-apm", "/risk-adjustment"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/acq-timing", "Acquisition Timing",
        short_description="Acquisition-timing model on your inputs.",
        primary_purpose="Frame timing trade-offs for an acquisition.",
        common_questions=[
            "Is now a good time to acquire in this sector?",
            "What's the trade-off between buying earlier vs waiting for a cycle bottom?",
            "What multiple-cycle do the defaults assume?",
            "How does interest-rate forecast affect the timing answer?",
            "Where do I see the macro / sector signals feeding the model?",
        ],
        inputs=["Sector, entry multiple, leverage, expected hold, "
                "macro/rate forecast assumptions."],
        outputs=["Buy-now vs wait recommendation band + structured "
                 "cost-of-waiting vs cost-of-buying-now read."],
        key_metrics=["Cost of waiting", "Cost of buying now",
                     "Recommended action band"],
        diligence_use_cases=["Pressure-testing entry timing for a "
                             "specific deal against current macro signals."],
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs; illustrative defaults."],
        limitations=[
            "Frames a trade-off using entered macro/sector assumptions — "
            "the answer mechanically reflects those defaults unless they "
            "are overridden with current rate/multiple expectations.",
            "Not a forecast — useful as a structured timing prompt, not "
            "as a market call."],
        model_logic_summary=(
            "Weighs the cost of waiting (extra hold years, opportunity "
            "cost) against the cost of buying now (multiple, leverage) "
            "from entered macro/sector signals. The output is a "
            "timing prompt with a recommended-action band, not a "
            "single 'yes/no' forecast."),
        related_routes=["/entry-multiple", "/hold-optimizer"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/bolton-analyzer", "Bolt-on Analyzer",
        short_description="Bolt-on / roll-up accretion calculator on your inputs.",
        primary_purpose="Model accretion/dilution from a bolt-on acquisition.",
        common_questions=[
            "Is this bolt-on accretive at the platform's entry multiple?",
            "What synergy run-rate makes the deal break even?",
            "How much multiple-arb is captured at platform exit?",
            "What's a realistic integration timeline assumption?",
            "How does the bolt-on affect platform leverage?",
        ],
        inputs=["Platform entry multiple, bolt-on multiple, bolt-on "
                "EBITDA, synergy run-rate, integration timeline, "
                "leverage assumptions."],
        outputs=["Blended-multiple accretion $, break-even synergy, "
                 "multiple-arb at exit, post-deal leverage change."],
        key_metrics=["Multiple-arbitrage accretion", "Break-even synergy",
                     "Post-deal leverage"],
        diligence_use_cases=["Underwriting a bolt-on candidate against "
                             "the platform's economics."],
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs; illustrative defaults, "
                                "not a specific deal."],
        limitations=[
            "Accretion math is mechanical on entered platform-multiple, "
            "bolt-on multiple, and synergy run-rate; integration risk "
            "and disynergies are not modeled.",
            "Multiple-arb at exit assumes the platform multiple holds — "
            "doesn't model a multiple compression scenario by default."],
        model_logic_summary=(
            "Computes blended-multiple accretion = (platform multiple − "
            "bolt-on multiple) × bolt-on EBITDA, then layers entered "
            "synergy run-rate against the platform's exit multiple to "
            "size the equity-value uplift. Integration timeline drives "
            "when synergies start hitting the bridge."),
        related_routes=["/rollup-economics", "/entry-multiple"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/cap-structure", "Capital Structure",
        short_description="Capital-structure calculator on your inputs.",
        primary_purpose="Model debt/equity structure and leverage for a deal.",
        common_questions=[
            "What's the leverage ratio under the base case?",
            "How does adding $50M of mezz change the all-in cost of capital?",
            "What does the structure look like at refinance?",
            "What's the equity contribution required to hit a target IRR?",
            "How does this map to the /debt-service / /covenant-headroom views?",
        ],
        inputs=["Tranche sizes (senior, sub, mezz, equity), pricing "
                "per tranche, EBITDA Y0, refi assumptions."],
        outputs=["Leverage (debt/EBITDA), WACC, equity-check, refi-"
                 "case capital structure."],
        key_metrics=["Leverage ratio", "WACC", "Equity check",
                     "Senior/sub/mezz mix"],
        diligence_use_cases=["Sketching a financing structure before "
                             "engaging lenders, or comparing two "
                             "competing structure proposals."],
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs."],
        limitations=[
            "Structure illustrative — the actual senior/sub/mezz pricing "
            "and OID economics depend on lender quotes; this page lets you "
            "sketch a structure, not negotiate it.",
            "Doesn't model refinancing frictions (call premia, makewhole) "
            "or covenant ratchets explicitly."],
        model_logic_summary=(
            "Sums entered tranches (senior, sub, mezz, equity) to get "
            "total sources; matches against entered uses; reports "
            "leverage = total debt / EBITDA, WACC = weighted cost of "
            "each tranche, and equity-check = sources − non-equity. "
            "Pricing is whatever's entered — no lender feed."),
        related_routes=["/debt-service", "/covenant-headroom"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/capital-efficiency", "Capital Efficiency",
        short_description="Capital-efficiency calculator on your inputs.",
        primary_purpose="Frame capital efficiency / returns on invested capital.",
        inputs=["Operating margin, tax rate, capex intensity, "
                "reinvestment / distribution-path assumptions."],
        outputs=["ROIC band, reinvest-vs-distribute path comparison."],
        key_metrics=["ROIC", "Capital efficiency ratio", "NOPAT"],
        diligence_use_cases=["Framing how capital-efficient a target "
                             "is before underwriting return uplift."],
        common_questions=[
            "What's the ROIC the model implies for this deal?",
            "How does the page compare reinvestment vs distribution paths?",
            "What's a healthy capital-efficiency ratio for this sector?",
            "How sensitive is the result to capex assumptions?",
            "Where do I see the underlying cash-flow waterfall?",
        ],
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs."],
        limitations=[
            "Aggregate efficiency view — sector benchmarks for ROIC are "
            "narrow and vary by sub-vertical; reading the result against "
            "a peer cohort matters more than the absolute number.",
            "Cash conversion and capex assumptions drive most of the "
            "swing; small input changes can move the ratio materially."],
        model_logic_summary=(
            "Computes ROIC = NOPAT / invested capital from entered "
            "operating-margin, tax-rate, and capex assumptions; "
            "compares reinvestment vs distribution paths by rolling "
            "the resulting cash flow forward. The result is a "
            "structural read, not a forecast."),
        related_routes=["/cap-structure", "/reinvestment"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/covenant-headroom", "Covenant Headroom",
        short_description="Covenant-headroom calculator on your inputs.",
        primary_purpose="Model covenant cushion under your assumptions.",
        common_questions=[
            "What's the leverage covenant cushion under the base case?",
            "How tight is the deal's covenant headroom right now?",
            "When does the headroom shrink below 15% in my projection?",
            "What EBITDA swing would breach the covenant?",
            "What's the recommended action when headroom is under 15%?",
        ],
        inputs=["Current leverage, EBITDA, covenant threshold "
                "(default = max leverage), projection assumptions."],
        outputs=["Cushion % band, swing-to-breach $, recommended-"
                 "action flag at the 15% early-warning band."],
        key_metrics=["Covenant cushion %", "Swing to breach",
                     "Quarter to first-trip"],
        diligence_use_cases=["Pressure-testing the proposed financing "
                             "structure's headroom before signing."],
        data_sources=["Calculator: your inputs + illustrative defaults."],
        interpretation_guidance=["Computes off YOUR inputs; not a live covenant feed."],
        limitations=[
            "Illustrative covenant model from entered assumptions — the "
            "actual covenant grid, basket math, and step-down schedule "
            "live in the credit agreement and must be supplied for a "
            "real read.",
            "Cushion is point-in-time on the entered numbers; doesn't "
            "automatically reflect intra-quarter EBITDA volatility."],
        model_logic_summary=(
            "Cushion = (covenant max − current ratio) / covenant max, "
            "computed against the entered covenant threshold (default "
            "leverage). The page sweeps EBITDA down until breach to "
            "report the swing-to-breach figure. No external covenant "
            "feed — assumptions drive the cushion."),
        related_routes=["/covenant-monitor", "/debt-service", "/cap-structure"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/covenant-monitor", "Covenant Monitor",
        short_description="Covenant-monitoring calculator on your inputs.",
        primary_purpose="Track covenant posture under your assumptions.",
        common_questions=[
            "Which deals are in the 0-15% covenant cushion early-warning band?",
            "Are any deals in technical breach?",
            "How does covenant posture trend across the book this quarter?",
            "What's the difference between this page and /covenant-headroom?",
            "Where do covenant ratios come from — actuals upload or projection?",
        ],
        inputs=["Entered/attached covenant ratios + thresholds per "
                "deal; period window."],
        outputs=["Per-deal cushion band (TRIPPED / 0-15% warning / "
                 "safe) + trend over the chosen window."],
        key_metrics=["Cushion %", "Trip count", "Warning-band count"],
        diligence_use_cases=["Portfolio-wide covenant-posture review "
                             "before LP update or board meeting."],
        data_sources=["Calculator: your inputs (+ live deal data where attached)."],
        interpretation_guidance=["Reflects your inputs / attached deal data."],
        limitations=[
            "Monitors covenant posture from entered/attached actuals, "
            "not a live lender feed — a fresh actuals upload or input "
            "is needed each period to keep the view current.",
            "The early-warning band threshold (e.g. 15% cushion) is "
            "platform-default; partners should align it with the "
            "specific deal's credit agreement."],
        model_logic_summary=(
            "Computes per-deal cushion via the /covenant-headroom "
            "formula, then bands deals (TRIPPED / 0-15% warning / "
            "safe). Trend uses the entered/attached actuals over the "
            "last N periods. No external lender feed — refresh "
            "requires a fresh actuals upload."),
        related_routes=["/covenant-headroom", "/debt-service"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MODEL_ESTIMATE,
    ),
    _ctx(
        "/deal-quality", "Deal Quality Scorer",
        short_description="Quality grade across the illustrative seed-deal corpus.",
        primary_purpose="Benchmark a deal's data-completeness/credibility grade "
        "against the corpus.",
        common_questions=[
            "What does a 'grade A' deal look like in this scorer?",
            "Which factors most affect the deal quality grade?",
            "How does the corpus distribution skew across grades?",
            "Is the grade benchmarked against real deals or illustrative ones?",
            "How should I use this score in IC vs underwriting?",
        ],
        inputs=["Illustrative seed corpus (each row carries the "
                "fields used in the grade)."],
        outputs=["Per-deal A-D grade + corpus grade distribution."],
        key_metrics=["Grade distribution", "Weight of each grade "
                     "dimension"],
        diligence_use_cases=["Teaching what 'grade A vs C' looks "
                             "like to a junior team member before "
                             "they grade a real deal."],
        data_sources=["Bundled ILLUSTRATIVE seed-deal corpus (labeled)."],
        interpretation_guidance=["Scores the illustrative corpus — not this "
                                "market's real deals; use as a structural benchmark."],
        limitations=[
            "Scores an ILLUSTRATIVE seed corpus, not your live pipeline "
            "— use as a structural benchmark for what 'grade A vs C' "
            "looks like; not a live deal grader.",
            "Grade weights are heuristic and stable across the corpus; "
            "a real-deal scorer would need calibration against partner "
            "judgment on a labeled sample."],
        model_logic_summary=(
            "For each corpus deal, computes a weighted blend of "
            "data-completeness scores (presence of key fields, "
            "evidence depth, scenario coverage) and maps to A-D "
            "grade bands. Weights are platform defaults; the page is "
            "a teaching benchmark, not a calibrated scorer."),
        related_routes=["/deal-risk-scores", "/corpus-dashboard"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
    _ctx(
        "/deal-risk-scores", "Deal Risk Scores",
        short_description="Risk scores across the illustrative seed-deal corpus.",
        primary_purpose="Benchmark deal risk dimensions against the corpus.",
        common_questions=[
            "Which risk dimensions are scored — covenant, payer, regulatory?",
            "How does this deal's risk profile compare to the corpus distribution?",
            "Are the risk scores from real realized outcomes or illustrative?",
            "Which corpus deals were the highest-risk outliers?",
            "How should I use this in IC discussion vs underwriting?",
        ],
        inputs=["Illustrative seed corpus deal rows with risk-"
                "dimension flags (covenant, payer, regulatory, "
                "execution, market)."],
        outputs=["Per-deal 0-100 composite risk score + dimension "
                 "decomposition + corpus distribution."],
        key_metrics=["Composite risk score", "Per-dimension score",
                     "Outlier list"],
        diligence_use_cases=["Teaching risk-dimension reading "
                             "against the corpus before applying to "
                             "a real deal."],
        data_sources=["Bundled ILLUSTRATIVE seed-deal corpus (labeled)."],
        interpretation_guidance=["Illustrative corpus, not real realized deals."],
        limitations=[
            "Scores the illustrative seed corpus, not your live "
            "pipeline — use to learn risk-dimension patterns, not as "
            "a real-deal scorer.",
            "Composite score depends on dimension weights that are "
            "stable defaults; a real underwriter would calibrate them "
            "to their own loss-experience."],
        model_logic_summary=(
            "Scores each corpus deal on each risk dimension "
            "(covenant, payer, regulatory, execution, market) using "
            "platform-default weightings, then composes a 0-100 "
            "composite. The output is a structural risk-pattern read, "
            "not a calibrated probability of distress."),
        related_routes=["/deal-quality", "/corpus-dashboard"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.DEMO_OR_FIXTURE,
    ),
    _ctx(
        "/deal-postmortem", "Deal Postmortem",
        short_description="Post-mortem analytics over the illustrative seed-deal corpus.",
        primary_purpose="Frame lessons/attribution from corpus deal outcomes.",
        common_questions=[
            "What killed value on the underperforming deals?",
            "Which lever drove the most attribution variance?",
            "How does the corpus distribution skew on EBITDA realization?",
            "What did the top-quartile deals do differently?",
            "Is this corpus illustrative or backed by real fund data?",
        ],
        inputs=["Illustrative seed-deal corpus + outcome labels."],
        outputs=["Attribution patterns by outcome band; top-quartile "
                 "vs bottom-quartile lever comparison."],
        key_metrics=["Lever attribution variance", "Outcome distribution"],
        diligence_use_cases=["Teaching the value-creation playbook "
                             "from corpus patterns to apply to "
                             "future deals."],
        data_sources=["Bundled ILLUSTRATIVE seed-deal corpus (labeled)."],
        interpretation_guidance=["Illustrative corpus — directional, not real outcomes."],
        limitations=[
            "Attribution patterns reflect the seed corpus's labels, not a "
            "real fund's deals; useful for teaching the playbook, not for "
            "rendering verdicts on the user's own portfolio.",
            "Lever attribution depends on the corpus's modeled bridges — "
            "the page can't disentangle correlated drivers reliably with "
            "this sample size."],
        model_logic_summary=(
            "Groups corpus deals by realized-outcome band, then ranks "
            "the bridge levers that varied most between bands. The "
            "result is descriptive attribution against an illustrative "
            "corpus — useful as a playbook pattern, not as causal "
            "inference on real funds."),
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
        common_questions=[
            "What HHI level is considered concentrated for a payer mix?",
            "How concentrated is this deal's payer book?",
            "What does the CMS provider-supply panel tell me about the market?",
            "How do I read the regime classification?",
            "Are the peer comparison numbers from real deals?",
        ],
        inputs=["Entered payer-mix shares for the deal (one row "
                "per payer; CR1/CR3/HHI compute off these).",
                "State scope so the CMS FFS provider-supply "
                "panel anchors to the right market."],
        outputs=["Payer HHI with a DOJ-style regime classification "
                 "(concentrated / moderate / fragmented) + the real "
                 "CMS FFS provider-enrollment supply backdrop "
                 "(2.98M providers)."],
        key_metrics=["Payer HHI (DOJ bands)",
                     "Network concentration regime",
                     "CMS FFS provider enrollment by state (real)"],
        diligence_use_cases=[
            "Diagnosing whether a deal's payer book is structurally "
            "fragile (high HHI / single-payer dependence).",
            "Framing acquisition-into-supply context: how thin or "
            "dense is provider supply in the deal's geography.",
        ],
        data_sources=["Illustrative corpus peers/regime stats (labeled) + real CMS "
                      "FFS provider enrollment (2.98M)."],
        interpretation_guidance=["HHI/regime compute off YOUR payer mix.",
                                 "Supply panel is the market backdrop, NOT this deal's roster."],
        limitations=["Peer/regime comps are illustrative seed-corpus."],
        model_logic_summary=(
            "Computes payer-HHI on entered payer-mix shares; "
            "classifies into network regimes (concentrated / "
            "moderate / fragmented) using DOJ-style thresholds. "
            "Overlays the real CMS FFS provider-enrollment panel "
            "(2.98M providers) as the market-supply context."),
        related_routes=["/workforce-planning", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/msa-concentration", "MSA Provider Market Concentration",
        short_description="MSA-level HHI/CR3/CR5 framework (illustrative MSA detail) "
        "anchored to real CMS change-of-ownership consolidation by state.",
        primary_purpose="Frame market concentration / rollup whitespace against real "
        "observed consolidation activity.",
        common_questions=[
            "Which MSAs have the lowest HHI — best rollup whitespace?",
            "How does CR3 differ from CR5 / HHI as a concentration measure?",
            "What does the CMS CHOW panel tell me about consolidation pace?",
            "Are the MSA-level operators in this page real or illustrative?",
            "How do I use this for thesis-driven sourcing?",
        ],
        inputs=["Illustrative MSA-operator shares used as the "
                "structural lens (HHI/CR3/CR5 compute off these).",
                "State scope so the real CMS CHOW consolidation "
                "panel anchors to the right market."],
        outputs=["HHI / CR3 / CR5 with a DOJ concentration band "
                 "(unconcentrated / moderate / concentrated) + the "
                 "real CMS CHOW consolidation backdrop by state."],
        key_metrics=["HHI (DOJ bands)", "CR3", "CR5",
                     "CMS CHOW filings by state (real)"],
        diligence_use_cases=[
            "Screening MSAs for rollup whitespace where structure "
            "is fragmented and CHOW activity confirms a roll-up "
            "is feasible.",
            "Framing antitrust risk for a planned MSA-level "
            "consolidation against the real CHOW backdrop.",
        ],
        data_sources=["Illustrative MSA HHI/operator detail (labeled) + real CMS CHOW "
                      "(5,141 SNF + 755 hospital)."],
        interpretation_guidance=["MSA tables are the structural lens (illustrative).",
                                 "CHOW panel is real observed consolidation by state."],
        limitations=["MSA-level HHI/operators are illustrative, not this market."],
        model_logic_summary=(
            "Computes Herfindahl on the illustrative MSA-operator "
            "shares to flag concentrated/moderate/unconcentrated "
            "structures (DOJ bands); overlays the real CMS CHOW "
            "panel (5,141 SNF + 755 hospital change-of-ownership "
            "filings by state) as the real consolidation backdrop."),
        related_routes=["/concentration-risk", "/competitive-intel", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/payer-concentration", "Payer Concentration Tracker",
        short_description="CR1/CR3/CR5/HHI payer-concentration calculator on your "
        "revenue + top-payer inputs, anchored to real CMS MA enrollment.",
        primary_purpose="Frame payer concentration and the real MA-market backdrop.",
        common_questions=[
            "What's the payer-concentration risk on this deal — single largest payer share?",
            "How does CR3 vs HHI tell a different story?",
            "Where does the CMS MA enrollment panel come from?",
            "What's a healthy payer mix to underwrite to?",
            "How does this differ from /provider-network's payer HHI?",
        ],
        inputs=["Entered top-payer revenue shares (one per payer) "
                "for the deal — these are what CR1/CR3/HHI compute "
                "off of.",
                "State scope so the CMS MA enrollment overlay "
                "anchors to the right market."],
        outputs=["CR1 (top-payer share), CR3 (top-3 sum), and HHI "
                 "(× 10,000) for the entered roster + the real CMS "
                 "MA geographic enrollment market backdrop."],
        key_metrics=["CR1 (top-payer concentration)",
                     "CR3 (top-3 concentration)",
                     "HHI (sum of squared shares × 10,000)",
                     "MA enrollment by state (real)"],
        diligence_use_cases=[
            "Sizing single-payer-loss revenue risk on a deal whose "
            "top payer is >30% of revenue.",
            "Comparing the deal's payer concentration to the real "
            "MA-market structure of the state it operates in.",
        ],
        data_sources=["Illustrative payer roster/renewals/denials (labeled) + real "
                      "CMS MA geographic enrollment (29.7M)."],
        interpretation_guidance=["Concentration metrics compute off YOUR inputs.",
                                 "MA panel is the observed market, NOT this deal's roster."],
        limitations=["Payer roster/renewal/denial detail is illustrative."],
        model_logic_summary=(
            "Sorts entered payer revenue shares descending; reports "
            "CR1 (top payer), CR3 (top 3 sum), and HHI (sum of "
            "squared shares × 10,000). Overlays the real CMS MA "
            "geographic enrollment (29.7M lives) as the market "
            "backdrop. Concentration math is yours; backdrop is real."),
        related_routes=["/payer-contracts", "/payer-rate-trends", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/gpo-supply", "GPO / Supply Chain Savings Tracker",
        short_description="Supply-chain savings model (illustrative) anchored to the "
        "real CMS Open Payments device/pharma vendor landscape.",
        primary_purpose="Frame GPO savings against the real manufacturer-vendor scale.",
        common_questions=[
            "What savings rate do platform GPOs typically achieve?",
            "Who are the top device/pharma vendors by industry payments?",
            "Are the savings numbers from real deals or illustrative?",
            "How do bulk-buys and rebate-capture differ?",
            "Where can I plug in the target's actual spend?",
        ],
        inputs=["Entered target spend categories + savings-rate, "
                "bulk-buy %, rebate-capture assumptions."],
        outputs=["Estimated GPO savings $ + Open Payments vendor-"
                 "landscape context."],
        key_metrics=["GPO savings $", "Top device/pharma vendors "
                     "($3.31bn)"],
        diligence_use_cases=["Sizing the GPO/supply-chain value-"
                             "creation lever for a deal with "
                             "meaningful product spend."],
        data_sources=["Illustrative GPO savings/contracts/bulk-buys (labeled) + real "
                      "CMS Open Payments ($3.31bn, top vendors)."],
        interpretation_guidance=["Savings/contract figures are illustrative scaffold.",
                                 "Open Payments panel is real industry vendor scale."],
        limitations=["Deal GPO savings require the target's actual spend data."],
        model_logic_summary=(
            "Applies entered savings-rate, bulk-buy %, and rebate-"
            "capture assumptions to the target's spend categories to "
            "estimate GPO savings; overlays the real CMS Open "
            "Payments vendor landscape ($3.31bn, top device/pharma "
            "vendors) so the savings figure has a plausible vendor-"
            "scale context."),
        related_routes=["/cost-structure"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/medicaid-unwinding", "Medicaid Unwinding Tracker",
        short_description="Medicaid redetermination impact model (illustrative) "
        "anchored to the real CMS dual-eligible population by state.",
        primary_purpose="Frame disenrollment / coverage-shift exposure against the "
        "real at-risk dual-eligible cohort.",
        common_questions=[
            "How exposed is this deal to Medicaid disenrollment?",
            "What % of the dual-eligible population is at risk in this state?",
            "How do disenrolled patients shift — back to Medicaid, ACA, self-pay?",
            "Are the bad-debt figures from real data or modeled?",
            "When does the unwinding pace normalize?",
        ],
        inputs=["Entered disenrollment rate and coverage-shift "
                "splits (back-to-Medicaid / ACA / self-pay / "
                "uninsured) and the deal's Medicaid lives.",
                "State scope so the real CMS dual-eligible "
                "at-risk-cohort panel anchors to the right market."],
        outputs=["Revenue-shift and bad-debt exposure estimates on "
                 "the entered assumptions + the real CMS dual-"
                 "eligible share-by-state at-risk-cohort panel."],
        key_metrics=["Revenue shift from disenrollment ($)",
                     "Bad-debt exposure ($)",
                     "Dual-eligible share by state (real)"],
        diligence_use_cases=[
            "Sizing Medicaid-redetermination revenue exposure for "
            "a deal in a state with elevated dual-eligible share.",
            "Stress-testing the bad-debt ramp under faster or "
            "slower disenrollment scenarios.",
        ],
        data_sources=["Illustrative disenrollment/coverage-shift/bad-debt (labeled) + "
                      "real CMS dual-eligible share by state."],
        interpretation_guidance=["Deal-level impact figures are illustrative.",
                                 "Dual-eligible panel is the real at-risk population."],
        limitations=["Deal exposure requires the target's real payer mix."],
        model_logic_summary=(
            "Applies entered disenrollment rate and coverage-shift "
            "splits (back-to-Medicaid / ACA / self-pay / uninsured) "
            "to the deal's Medicaid lives to estimate revenue "
            "shift and bad-debt exposure; overlays the real CMS "
            "dual-eligible share by state as the at-risk-cohort "
            "anchor."),
        related_routes=["/payer-concentration", "/risk-adjustment"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/payer-contracts", "Payer Contracts",
        short_description="Payer contract-book / negotiation model (illustrative) "
        "anchored to the real CIVHC commercial-vs-Medicare rate benchmark.",
        primary_purpose="Frame contract rates against the real commercial-%-of-"
        "Medicare benchmark contracts negotiate against.",
        common_questions=[
            "What rate should I negotiate as % of Medicare?",
            "Which contracts have escalator clauses worth modeling?",
            "When do the top contracts come up for renegotiation?",
            "Is the contract book on this page real or illustrative scaffold?",
            "Where do I find the actual rate sheets?",
        ],
        inputs=["Entered contract roster (payer, %-of-Medicare, "
                "escalator clause, renewal date) for each top "
                "payer in the deal's book.",
                "State scope so the CIVHC %-of-Medicare benchmark "
                "anchors to the right market."],
        outputs=["A renegotiation-leverage ranking of the entered "
                 "contracts (upcoming-renewal × escalator gap) + "
                 "the real CIVHC %-of-Medicare benchmark for "
                 "negotiation anchor."],
        key_metrics=["Contract %-of-Medicare (entered)",
                     "Escalator gap vs benchmark",
                     "Upcoming-renewal leverage",
                     "CIVHC %-of-Medicare benchmark (real)"],
        diligence_use_cases=[
            "Prioritizing which payer renegotiation creates the "
            "most rate uplift over the hold.",
            "Anchoring negotiation asks to the observed CIVHC "
            "commercial-%-of-Medicare distribution.",
        ],
        data_sources=["Illustrative contract book/negotiations/escalators (labeled) + "
                      "real CIVHC / CO APCD reference-based pricing."],
        interpretation_guidance=["Contract book is illustrative scaffold.",
                                 "CIVHC ratio is a real Colorado rate benchmark."],
        limitations=["Deal contracts require the target's actual rate sheets."],
        model_logic_summary=(
            "Reads entered contract roster (payer, %-of-Medicare, "
            "escalator, renewal date) and ranks by upcoming-renewal "
            "leverage + escalator gap; overlays the real CIVHC "
            "Colorado %-of-Medicare benchmark so negotiation targets "
            "anchor to observed market rates."),
        related_routes=["/payer-concentration", "/ref-pricing", "/payer-rate-trends"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/health-equity", "Health Equity / SDOH Scorecard",
        short_description="HEI / Star-bonus model (illustrative) anchored to real CDC "
        "PLACES full-population social-determinants prevalence.",
        primary_purpose="Frame health-equity posture against real SDOH burden.",
        common_questions=[
            "What's the Star-bonus value of moving HEI one band?",
            "Which SDOH factors are heaviest in this market?",
            "How does CDC PLACES data come into the scorecard?",
            "Is the HEI figure for this deal or a sector scaffold?",
            "What's a realistic timeline for moving HEI metrics?",
        ],
        inputs=["Entered HEI-band assumption, deal MA Star-bonus "
                "revenue, sector context."],
        outputs=["Star-bonus uplift estimate + CDC PLACES SDOH "
                 "prevalence panel."],
        key_metrics=["Star-bonus uplift $", "HEI band", "SDOH burden"],
        diligence_use_cases=["Sizing the equity/Star uplift "
                             "opportunity for a value-based-care "
                             "thesis."],
        data_sources=["Illustrative HEI/Star scorecard (labeled) + real CDC PLACES SDOH "
                      "(uninsured, food/transport insecurity)."],
        interpretation_guidance=["HEI/Star figures are illustrative, scaled to inputs.",
                                 "PLACES panel is real full-population SDOH (not patients)."],
        limitations=["Model-based estimates; area-level, not this deal's panel."],
        model_logic_summary=(
            "Applies entered HEI-band assumptions to the deal's MA "
            "Star-bonus revenue to estimate the bonus uplift from "
            "moving up an equity band; overlays the real CDC PLACES "
            "SDOH-prevalence panel (uninsured, food/transport "
            "insecurity) as the local population context. The lift "
            "is modeled; the prevalence panel is observed."),
        related_routes=["/risk-adjustment", "/market-intel/geo"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/telehealth-econ", "Telehealth Economics Analyzer",
        short_description="Telehealth visit-economics model (illustrative) anchored to "
        "real CDC PLACES access barriers (transportation, uninsured).",
        primary_purpose="Frame telehealth demand against real access-barrier prevalence.",
        common_questions=[
            "What's the unit economics of a telehealth visit vs in-person?",
            "How big is the addressable telehealth demand in this market?",
            "Does payment parity hold post-PHE for this state?",
            "Where do the access-barrier figures come from?",
            "How sensitive is the EV to parity / reimbursement assumptions?",
        ],
        inputs=["Entered telehealth visit P&L assumptions (rate-"
                "parity factor, duration, no-show rate, panel "
                "growth) for the deal's footprint.",
                "State scope so the CDC PLACES access-barrier "
                "panel (transportation, uninsured) anchors to "
                "the right market."],
        outputs=["Incremental EV estimate from telehealth visit "
                 "economics on the entered assumptions + the real "
                 "CDC PLACES access-barrier prevalence as the "
                 "demand-side signal."],
        key_metrics=["Telehealth EV uplift ($)",
                     "Rate parity (entered, %)",
                     "CDC PLACES access barriers by state (real)"],
        diligence_use_cases=[
            "Sizing the telehealth value-creation thesis for a "
            "deal in a market with high access-barrier prevalence.",
            "Pressure-testing how a post-PHE parity reset reprices "
            "the visit-economics opportunity.",
        ],
        data_sources=["Illustrative visit P&L / parity / productivity (labeled) + real "
                      "CDC PLACES access barriers."],
        interpretation_guidance=["Visit economics are illustrative.",
                                 "PLACES panel is real access-barrier prevalence by state."],
        limitations=["Model-based estimates; area-level."],
        model_logic_summary=(
            "Applies entered telehealth visit P&L (rate-parity, "
            "duration, no-show rate, panel growth) to estimate "
            "incremental EV per market; overlays the real CDC PLACES "
            "access-barrier prevalence (transportation, uninsured) "
            "as the demand-side signal."),
        related_routes=["/health-equity"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/patient-experience", "Patient Experience",
        short_description="NPS/complaint/service-recovery model (illustrative) anchored "
        "to the real CMS HCAHPS patient-survey top-box by state.",
        primary_purpose="Frame patient-experience posture against the real HCAHPS "
        "benchmark.",
        common_questions=[
            "What's the HCAHPS top-box norm for this state?",
            "How does NPS map to HCAHPS for benchmarking?",
            "What's the revenue uplift from moving HCAHPS one band?",
            "Where are this facility's actual scores in the body?",
            "What drives complaint volume — is it specialty-specific?",
        ],
        inputs=["Entered NPS, complaint-rate, and service-recovery-"
                "cost assumptions plus the deal's volume.",
                "State scope so the CMS HCAHPS top-box benchmark "
                "panel anchors to the right market."],
        outputs=["Revenue-uplift estimate from moving up one HCAHPS "
                 "experience band on the entered assumptions + the "
                 "real CMS HCAHPS top-box panel by state."],
        key_metrics=["Revenue uplift per HCAHPS band move ($)",
                     "NPS (entered)",
                     "HCAHPS top-box by state (real)"],
        diligence_use_cases=[
            "Sizing the experience-uplift value-creation lever for "
            "a facility with below-state HCAHPS scores.",
            "Stress-testing a service-recovery investment against "
            "the band-move it would have to deliver.",
        ],
        data_sources=["Illustrative NPS/complaint model (labeled) + real CMS HCAHPS "
                      "state top-box (overall 9-10, would-recommend)."],
        interpretation_guidance=["NPS/complaint figures are illustrative.",
                                 "HCAHPS panel is the real survey benchmark (not this facility)."],
        limitations=["State-level HCAHPS; national figure = state mean."],
        model_logic_summary=(
            "Applies entered NPS / complaint-rate / recovery-cost "
            "assumptions to the deal's volume to estimate revenue "
            "uplift from moving up an experience band; overlays the "
            "real CMS HCAHPS state top-box panel so the band targets "
            "are grounded in observed survey norms."),
        related_routes=["/quality-scorecard", "/clinical-outcomes"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/locum-tracker", "Locum / Contract-Labor Tracker",
        short_description="Locum spend/coverage model (illustrative) anchored to real "
        "HRSA Health Professional Shortage Areas — the locum-demand driver.",
        primary_purpose="Frame locum/temp-staffing demand against real shortage-area data.",
        common_questions=[
            "How much of the deal's labor cost is going to locum / agency?",
            "Is the area a designated HPSA driving locum demand?",
            "What's a typical locum rate-to-permanent ratio for this specialty?",
            "How does locum spend translate into EBITDA drag?",
            "Where can I plug in the target's actual locum invoices?",
        ],
        inputs=["Entered locum spend, locum-share-of-labor, and "
                "rate-premium-over-permanent assumptions for the "
                "deal's labor base.",
                "State / county scope so the HRSA HPSA overlay "
                "ties demand to the right shortage geography."],
        outputs=["EBITDA-drag estimate from locum reliance on the "
                 "entered assumptions + the real HRSA HPSA panel "
                 "(7,635 designated primary-care shortage areas)."],
        key_metrics=["EBITDA drag from locum spend ($)",
                     "Locum % of labor (entered)",
                     "HPSA designations by state (real)"],
        diligence_use_cases=[
            "Sizing locum/agency reliance as a margin risk for a "
            "deal in HPSA-heavy geography.",
            "Pressure-testing the EBITDA impact of converting "
            "locum coverage to permanent hires.",
        ],
        data_sources=["Illustrative locum spend/coverage/rates (labeled) + real HRSA "
                      "HPSA (7,635 designated PC shortage areas)."],
        interpretation_guidance=["Locum figures are illustrative.",
                                 "HPSA panel is real shortage-area designations by state."],
        limitations=["Deal locum spend requires the target's actuals."],
        model_logic_summary=(
            "Applies entered locum spend / locum-share / rate-"
            "premium assumptions to the deal's labor base to estimate "
            "EBITDA drag from agency reliance; overlays the real "
            "HRSA HPSA panel (7,635 PC shortage areas) so the demand "
            "side is grounded in observed shortage geography."),
        related_routes=["/workforce-planning", "/workforce-retention"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/workforce-retention", "Workforce Turnover / Retention Tracker",
        short_description="Turnover/engagement/retention model (illustrative) anchored "
        "to real HRSA shortage areas — the retention-pressure backdrop.",
        primary_purpose="Frame retention difficulty against real labor-shortage data.",
        common_questions=[
            "How much harder is retention in HPSA-designated areas?",
            "What's a healthy turnover ratio for this sector?",
            "Which roles drive the largest turnover cost?",
            "What's the EBITDA hit from a 5pp turnover increase?",
            "Are the retention programs on this page illustrative or real?",
        ],
        inputs=["Entered role-level turnover rates and "
                "replacement-cost assumptions for the deal's "
                "labor base.",
                "State scope so the HRSA HPSA overlay anchors "
                "retention difficulty to the right shortage "
                "geography."],
        outputs=["EBITDA-drag estimate from a turnover delta "
                 "on the entered assumptions + the real HRSA "
                 "HPSA shortage panel as the retention-"
                 "difficulty backdrop."],
        key_metrics=["Annual turnover rate (entered)",
                     "EBITDA drag from turnover ($)",
                     "HRSA HPSA shortage by state (real)"],
        diligence_use_cases=[
            "Sizing workforce-retention risk for a labor-"
            "intensive deal in HPSA-heavy geography.",
            "Pressure-testing whether a retention program's "
            "cost is justified by the avoided replacement cost.",
        ],
        data_sources=["Illustrative turnover/engagement/programs (labeled) + real HRSA "
                      "HPSA shortage designations."],
        interpretation_guidance=["Turnover/engagement figures are illustrative.",
                                 "HPSA panel is real shortage data (deeper shortage = harder retention)."],
        limitations=["Deal turnover requires the target's HR roster."],
        model_logic_summary=(
            "Applies entered role-turnover and replacement-cost "
            "assumptions to the deal's labor base to estimate EBITDA "
            "drag from a turnover delta; overlays the real HRSA "
            "shortage-area panel so retention difficulty is grounded "
            "in observed labor scarcity by geography."),
        related_routes=["/locum-tracker", "/workforce-planning"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/antitrust-screener", "Anti-Trust Screener",
        short_description="HHI / HSR / market-overlap screen computed off your deal-"
        "size input, anchored to real CMS change-of-ownership consolidation.",
        primary_purpose="Frame antitrust/HSR risk against real observed consolidation.",
        common_questions=[
            "Does this deal trigger an HSR filing threshold?",
            "What's the HHI delta from this acquisition?",
            "Is the second-request risk material here?",
            "What CMS CHOW data signals about consolidation in this market?",
            "What precedent deals were challenged in this sector?",
        ],
        inputs=["Deal size, current/post-deal market shares, sector."],
        outputs=["HSR filing-requirement flag, directional HHI delta, "
                 "CMS CHOW serial-acquisition context."],
        key_metrics=["HSR threshold trip", "HHI delta", "Serial-CHOW count"],
        diligence_use_cases=["Early antitrust risk read before an HSR "
                             "filing decision."],
        data_sources=["Illustrative HHI/HSR/overlap/precedent model (labeled) + real "
                      "CMS CHOW consolidation activity."],
        interpretation_guidance=["HHI/HSR/overlap compute off your deal-size input.",
                                 "CHOW panel is the real serial-acquisition backdrop FTC scrutinizes."],
        limitations=["Market-overlap specifics are illustrative."],
        model_logic_summary=(
            "Applies HSR threshold rules (size-of-transaction, "
            "size-of-person) to entered deal size to flag filing "
            "requirements; computes a directional HHI delta from "
            "entered current/post-deal market shares; overlays the "
            "real CMS CHOW serial-acquisition map for FTC-style "
            "scrutiny context."),
        related_routes=["/concentration-risk", "/msa-concentration", "/competitive-intel"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/cin-analyzer", "Clinically Integrated Network Analyzer",
        short_description="CIN shared-savings/quality model on your inputs, anchored "
        "to the real CMS MSSP ACO landscape.",
        primary_purpose="Frame a CIN's value-based posture against the real ACO landscape.",
        common_questions=[
            "What's the shared-savings opportunity for this CIN size?",
            "How does the target's quality stack up vs the 511 MSSP ACOs?",
            "Is a CIN the right structure vs ACO vs IPA?",
            "What's the minimum scale for shared-savings to work?",
            "Where can I see the underlying MSSP performance data?",
        ],
        inputs=["CIN size (attributed lives), entered quality score, "
                "structure choice (CIN/ACO/IPA)."],
        outputs=["Directional savings opportunity + MSSP-landscape "
                 "context band."],
        key_metrics=["Shared-savings opportunity $", "MSSP percentile",
                     "Min scale for savings"],
        diligence_use_cases=["Sizing the value-based-care thesis for "
                             "a clinically-integrated network deal."],
        data_sources=["Illustrative CIN roster/contracts/quality (labeled) + real CMS "
                      "MSSP ACO landscape (511 ACOs, 15,293 orgs)."],
        interpretation_guidance=["CIN roster/contract figures are illustrative.",
                                 "MSSP panel is the real ACO/value-based benchmark."],
        limitations=["Deal CIN data requires the target's network roster."],
        model_logic_summary=(
            "Computes a directional shared-savings opportunity from "
            "entered CIN size, attribution, and quality score, then "
            "overlays the real MSSP ACO landscape (511 ACOs across "
            "15,293 organizations) so a partner can see where the "
            "CIN sits relative to active value-based peers."),
        related_routes=["/aco-economics", "/quality-scorecard"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/nsa-tracker", "No Surprises Act / OON Tracker",
        short_description="OON volume / balance-bill / IDR model (illustrative) "
        "anchored to the real CIVHC commercial-vs-Medicare OON/QPA benchmark.",
        primary_purpose="Frame NSA OON/IDR exposure against the real rate benchmark "
        "disputes reference.",
        common_questions=[
            "How much OON exposure does the target have post-NSA?",
            "What's the typical IDR award outcome — provider or payer?",
            "How does QPA (qualifying payment amount) cap revenue?",
            "Where does the CIVHC OON/QPA benchmark come from?",
            "Which specialties face the highest NSA exposure?",
        ],
        inputs=["Entered OON volume, balance-bill rate, and IDR-"
                "win-probability assumptions for the deal.",
                "State / specialty scope so the CIVHC %-of-Medicare "
                "QPA benchmark anchors to the right market."],
        outputs=["Post-NSA OON exposure estimate ($) under the "
                 "entered assumptions + the real CIVHC commercial-"
                 "%-of-Medicare benchmark IDR arbitrators reference."],
        key_metrics=["Post-NSA OON exposure ($)",
                     "IDR-win probability (entered)",
                     "QPA benchmark from CIVHC (real)"],
        diligence_use_cases=[
            "Sizing No-Surprises-Act revenue risk for an OON-"
            "heavy specialty (anesthesia, ED, radiology) deal.",
            "Pressure-testing the IDR strategy against the real "
            "CIVHC QPA distribution arbitrators benchmark to.",
        ],
        data_sources=["Illustrative OON volume/balance-bill/IDR (labeled) + real CIVHC "
                      "commercial-%-of-Medicare distribution."],
        interpretation_guidance=["OON/IDR figures are illustrative.",
                                 "CIVHC ratio is the real OON/QPA rate benchmark (Colorado APCD)."],
        limitations=["Deal OON exposure requires the target's claims."],
        model_logic_summary=(
            "Applies entered OON volume × balance-bill rate × IDR-win "
            "probability to estimate post-NSA exposure; the QPA cap "
            "is anchored to the real CIVHC commercial-%-of-Medicare "
            "distribution (Colorado APCD) as the benchmark IDR-"
            "arbitrators reference."),
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
        common_questions=[
            "What happened on the book over the weekend?",
            "Which deals had stage changes in the last 7 days?",
            "Who made the last edit to deal X?",
            "Is this feed audit-grade — can I cite it in IC?",
            "How far back does the activity log go?",
        ],
        inputs=["Workspace audit/event log; entity-type and time-"
                "window filters."],
        outputs=["Reverse-chronological event stream with timestamp, "
                 "actor, entity, and action."],
        key_metrics=["Events per day", "Top actors", "Top entities"],
        diligence_use_cases=["Reviewing what changed before an IC "
                             "or LP update."],
        data_sources=["Your real workspace audit/event log (SQLite)."],
        interpretation_guidance=["This is your own real activity, not market/corpus data."],
        limitations=[
            "Activity feed reflects events the app emits — actions that "
            "bypass the standard flow (direct DB edits, file imports) may "
            "not appear here.",
            "Audit-grade for the local workspace, but not a system-of-"
            "record for legal/regulatory purposes."],
        model_logic_summary=(
            "No model — reads the workspace audit log in reverse "
            "chronological order, filtering on entity type (deal/note/"
            "alert/escalation) and the chosen time window. Events are "
            "the same ones the app's hash-chained audit table records."),
        related_routes=["/app", "/alerts", "/escalations"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/deal-pipeline", "Deal Pipeline",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Your real deal pipeline by stage (alias of /pipeline).",
        primary_purpose="Track your actual opportunities through the deal funnel.",
        common_questions=[
            "How many active deals are at each pipeline stage right now?",
            "Which deals are stalled in their stage past the SLA?",
            "What's the funnel conversion stage-by-stage?",
            "How does this differ from /pipeline?",
            "Can I filter by owner or sector here?",
        ],
        inputs=["Active deals from the deal store with stage + "
                "stage_entered_at + owner/sector filters."],
        outputs=["Stage-by-stage funnel counts + SLA-flag list."],
        key_metrics=["Active deal count", "Stage conversion rate",
                     "SLA-stalled count"],
        diligence_use_cases=["Weekly partner-of-record review of the "
                             "active deal funnel."],
        data_sources=["Your real deal records (SQLite)."],
        interpretation_guidance=["YOUR deals, not the market or seed corpus."],
        limitations=[
            "An alias of /pipeline — same backing data, slightly "
            "different UI emphasis on funnel/stage; if a deal is missing "
            "here, it's missing from /pipeline too.",
            "SLA flags use the entered stage_entered_at; deals without "
            "that timestamp don't flag stalled."],
        model_logic_summary=(
            "Groups active deals from the deal store by stage; "
            "computes per-stage count, conversion to next stage "
            "(closed-won / closed-lost / advanced) over the chosen "
            "window, and flags deals exceeding the per-stage SLA. "
            "No projection — descriptive only."),
        related_routes=["/pipeline", "/app", "/deals"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/deals", "Deals",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="The list/management view of YOUR real deals.",
        primary_purpose="Browse, filter, and open your actual deal records.",
        common_questions=[
            "How many deals are in my workspace right now?",
            "How do I filter by stage / sector / owner?",
            "Can I bulk-archive cold deals from here?",
            "Where do I add a new deal?",
            "How does this differ from /pipeline?",
        ],
        inputs=["Deal records from the deal store; filter inputs "
                "(stage, sector, owner, archive flag)."],
        outputs=["Filtered/sorted deal list + bulk-action toolbar."],
        key_metrics=["Deal count", "By stage / sector / owner"],
        diligence_use_cases=["Day-to-day pipeline management: "
                             "filtering to a slice for an owner "
                             "review or bulk-archive sweep."],
        data_sources=["Your real deal records (SQLite)."],
        interpretation_guidance=["YOUR deals — real workspace data."],
        limitations=[
            "Shows only deals tracked in the local store; archived/"
            "deleted records are filtered out by default — toggle "
            "show-all to see them.",
            "Filters work over what's been entered; sparse tags or "
            "missing stage labels make filters silently exclude deals."],
        model_logic_summary=(
            "No model — a list/filter/sort view over the deals "
            "table. Filters are SQL WHERE clauses on entered "
            "stage/sector/owner; bulk operations write to the same "
            "store with an audit-log entry per change."),
        related_routes=["/pipeline", "/deal-search", "/app"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/deal-search", "Deal Search",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Search across YOUR real deals by name, stage, sector, owner.",
        primary_purpose="Quickly locate a specific deal in your workspace.",
        common_questions=[
            "How do I find a deal by partial name?",
            "Can I search by tag or sector?",
            "Does the search include archived deals?",
            "How is this different from /global-search?",
            "Why aren't my recent deals appearing?",
        ],
        inputs=["Search query; archive-toggle; column scope "
                "(name, sponsor, sector, owner)."],
        outputs=["Ranked deal hits with quick-open links."],
        key_metrics=["Hit count", "Result rank"],
        diligence_use_cases=["Quickly opening a specific deal "
                             "page from the keyboard."],
        data_sources=["Your real deal records (SQLite)."],
        interpretation_guidance=["Searches your own deals, not the market/corpus."],
        limitations=[
            "Searches workspace-tracked deals only — archived/deleted "
            "records are excluded by default; use show-all or "
            "/global-search if the deal isn't appearing.",
            "Matches over indexed columns (name, sponsor, sector, "
            "owner) — full-text search across notes is not done here."],
        model_logic_summary=(
            "Substring + indexed-column matches against the deals "
            "table; results are ranked by exact prefix > substring > "
            "fuzzy. No semantic matching — for searching inside "
            "notes/documents see /global-search."),
        related_routes=["/deals", "/pipeline", "/global-search"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/initiatives", "Initiatives",
        category=PageContextCategory.PORTFOLIO_LP,
        short_description="Value-creation initiatives tracked against YOUR real deals/"
        "portfolio companies.",
        primary_purpose="Track operating initiatives and their progress per company.",
        common_questions=[
            "Which value-creation initiatives are behind plan?",
            "What's the total realized EBITDA uplift from initiatives this quarter?",
            "Which initiatives are flagged at-risk across the portfolio?",
            "How do I add a new initiative to a deal?",
            "Where does this data come from — manual entry or actuals upload?",
        ],
        inputs=["Your real initiative records (target EBITDA "
                "uplift, owner, deal scope, tolerance band).",
                "Any monthly actuals uploaded against each "
                "initiative — the actual-vs-plan engine needs "
                "these to flag behind/on/at-risk."],
        outputs=["Per-initiative target-vs-actual EBITDA uplift, "
                 "rolled up to per-deal and portfolio totals, "
                 "with status (behind / on plan / at risk) flags."],
        key_metrics=["Realized EBITDA uplift from initiatives ($)",
                     "% of initiatives on/ahead of plan",
                     "% of initiatives at-risk"],
        diligence_use_cases=[
            "Reporting realized initiative value to the IC at the "
            "quarterly portfolio review.",
            "Spotting which value-creation theses are slipping in "
            "time to intervene with the operator.",
        ],
        data_sources=["Your real initiative records (SQLite)."],
        interpretation_guidance=["Your own initiatives — real workspace data."],
        limitations=[
            "Tracks entered initiative records plus any monthly actuals "
            "attached — an empty view reflects what's been logged, not "
            "absence of operational work.",
            "Realized EBITDA uplift requires monthly actuals to be "
            "uploaded; without them the page shows targets only."],
        model_logic_summary=(
            "Reads initiative records from the deal store, joins to "
            "any attached monthly actuals, and computes target-vs-"
            "actual EBITDA uplift per initiative and per deal. "
            "Status (behind / on plan / at risk) is flagged from "
            "the actual-vs-plan delta against an entered tolerance."),
        related_routes=["/portfolio", "/value-creation-plan", "/app"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/pipeline/bridge", "Pipeline Bridge",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Jump from a pipeline deal into its EBITDA bridge / analysis.",
        primary_purpose="Connect a pipeline opportunity to its value-creation bridge.",
        common_questions=[
            "How do I see the EBITDA bridge for a specific pipeline deal?",
            "What levers does the bridge break value creation into?",
            "How does the bridge map to /diligence/bridge-audit?",
            "Where do the bridge model inputs come from — manual or auto?",
            "Why is the bridge empty for some deals?",
        ],
        inputs=["A selected pipeline deal — the page resolves "
                "from its deal_id to the bridge-engine inputs.",
                "Entered 7-lever targets on the deal (denial, AR, "
                "payer mix, labor, supply, leverage, refi) — same "
                "targets that drive /ebitda-bridge."],
        outputs=["The per-lever EBITDA-contribution stack for the "
                 "pipeline deal, identical to /ebitda-bridge math."],
        key_metrics=["EBITDA contribution per lever ($)",
                     "Total bridged uplift ($)",
                     "Lever ranking by impact"],
        diligence_use_cases=[
            "Jumping from a pipeline opportunity into its full "
            "EBITDA-bridge view without leaving the pipeline flow.",
            "Comparing two pipeline deals on lever mix to choose "
            "which carries the cleaner value-creation thesis.",
        ],
        data_sources=["Your real deal records + the bridge model on your inputs."],
        interpretation_guidance=["Operates on YOUR deal; bridge math is model output."],
        limitations=[
            "Bridge model output is only as good as the entered lever "
            "targets — empty bridges mean the deal lacks initiative "
            "scoping, not that there's no value to create.",
            "Probability-weighting on levers is not done by default; "
            "raw lever impact may overstate realized uplift."],
        model_logic_summary=(
            "Routes from a pipeline deal to the bridge engine: "
            "reads entered lever targets (denial, AR, payer mix, "
            "labor, supply, leverage, refi) for the deal, runs the "
            "same 7-lever bridge math as /ebitda-bridge, and renders "
            "the per-lever EBITDA contribution stack."),
        related_routes=["/pipeline", "/ebitda-bridge/", "/diligence/bridge-audit"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/screening", "Screening",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Screen targets against your criteria (alias surface of the "
        "screening workflow).",
        primary_purpose="Filter the candidate universe to a prioritized shortlist.",
        common_questions=[
            "How do I set criteria for a custom screen?",
            "Can I save a screen for reuse?",
            "How is this different from /target-screener?",
            "What workspace data do my screens run against?",
            "Where do I export shortlisted candidates?",
        ],
        inputs=["Your workspace candidate/target records + entered "
                "screen criteria (sector, size band, geography, "
                "score thresholds).",
                "Saved-screen identifier when re-running a "
                "previously saved screen."],
        outputs=["A filtered candidate list with one row per match "
                 "and the option to save the criteria as a reusable "
                 "screen."],
        key_metrics=["Matching candidate count",
                     "Saved-screen count",
                     "Criteria filters applied"],
        diligence_use_cases=[
            "Building a custom workspace-scoped shortlist before a "
            "sourcing conversation.",
            "Saving a sector / size band as a reusable screen for "
            "weekly pipeline review.",
        ],
        data_sources=["Your real candidate/target records + screening criteria."],
        interpretation_guidance=["Operates on your workspace candidates."],
        limitations=[
            "Workspace-only — screens here run against tracked candidates "
            "in your store; for a market-wide universe screen use "
            "/target-screener.",
            "Saved screens are per-workspace; not shared across users "
            "or environments by default."],
        model_logic_summary=(
            "Filter engine over the workspace candidates table — "
            "entered criteria become SQL WHERE clauses (sector, "
            "size, geography, score thresholds), and matching "
            "candidates can be saved as a reusable screen. No model — "
            "deterministic set membership."),
        related_routes=["/screening/dashboard", "/target-screener", "/pipeline"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/screening/dashboard", "Screening Dashboard",
        category=PageContextCategory.PIPELINE_SOURCING,
        short_description="Dashboard view of your screening funnel and shortlist.",
        primary_purpose="Monitor screening progress and surface top candidates.",
        common_questions=[
            "How many candidates am I screening across all active screens?",
            "Which screens have the most movement this week?",
            "What's the conversion rate from screen to shortlist?",
            "How does this compare to /screening?",
            "Where do I act on a top-scoring candidate?",
        ],
        inputs=["Your workspace screening tables (saved screens, "
                "candidates, stage assignments).",
                "Optional time-window filter so weekly / monthly "
                "movement can be isolated."],
        outputs=["Funnel counts per screening stage (screened / "
                 "shortlisted / advanced / closed), stage-to-stage "
                 "conversion rates, and per-screen movement deltas."],
        key_metrics=["Candidates per stage",
                     "Stage-to-stage conversion rate",
                     "Per-screen weekly movement"],
        diligence_use_cases=[
            "Weekly pipeline review — spotting which screens are "
            "moving and which have stalled.",
            "Reporting conversion-rate efficiency to IC over a "
            "chosen time window.",
        ],
        data_sources=["Your real candidate/target records + screening criteria."],
        interpretation_guidance=["Your workspace screening, not the market/corpus."],
        limitations=[
            "Dashboard view of YOUR screening activity — empty/sparse "
            "panels mean few candidates have moved through, not that "
            "the market is dry.",
            "Conversion-rate metrics need enough screen-volume to be "
            "stable; thin pipelines make the rate noisy week-to-week."],
        model_logic_summary=(
            "Aggregates across all saved screens: counts at each "
            "stage (screened / shortlisted / advanced / closed), "
            "stage-to-stage conversion rates over the chosen window, "
            "and per-screen movement. No model — workflow aggregation "
            "over the screening tables."),
        related_routes=["/screening", "/target-screener", "/pipeline"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/data-intelligence", "Data Intelligence",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="Catalog/overview of the real public data sources wired into "
        "PEdesk (CMS/HCRIS/CDC/HRSA/CIVHC, etc.) and what they power.",
        primary_purpose="Understand which real datasets back the analytics and where.",
        common_questions=[
            "Which CMS datasets does PEdesk pull from?",
            "How fresh is the HRSA HPSA data?",
            "Is the CIVHC data Colorado-only or broader?",
            "Where do I see the refresh cadence per dataset?",
            "What's the difference between this page and /data?",
        ],
        inputs=["The data-source registry; category filter."],
        outputs=["A grouped catalog of real public datasets with "
                 "consumer-page links."],
        key_metrics=["Source count by category", "Pages per source"],
        diligence_use_cases=["Tracing a Guide-cited number back to "
                             "its public-data source."],
        data_sources=["The data-source registry (real public datasets)."],
        interpretation_guidance=["A catalog of real sources — see each source's card for detail."],
        limitations=[
            "Catalog only — this page lists data sources; their "
            "freshness and ingestion status live on /admin/data-sources.",
            "Public datasets here lag their underlying filings (e.g. "
            "HCRIS by 1-2+ years, HPSA by quarter); refresh cadence "
            "varies per source."],
        model_logic_summary=(
            "No model — enumerates the data_source_registry entries, "
            "groups them by category (CMS/HRSA/CDC/CIVHC/Census), and "
            "links each to the pages that consume it. Freshness/"
            "ingestion status is delegated to /admin/data-sources."),
        related_routes=["/cms-sources", "/data", "/data/catalog"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/data-room", "Data Room",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="The diligence data room for a deal — YOUR uploaded documents "
        "and extracts.",
        primary_purpose="Organize and reference the target's diligence documents.",
        common_questions=[
            "What documents has the target uploaded so far?",
            "How do I add a new document to the data room?",
            "What file types does the room support?",
            "Can the Guide search inside uploaded documents?",
            "How is access controlled per deal?",
        ],
        inputs=["Uploaded deal documents (PDF, XLSX, CSV); deal-tag "
                "assignment."],
        outputs=["Document list with deal/tag, type, upload date, "
                 "and extraction status."],
        key_metrics=["Document count", "Extraction coverage %"],
        diligence_use_cases=["Document-by-document review during a "
                             "diligence sweep — locating the source "
                             "behind a packet figure."],
        data_sources=["Your uploaded deal documents (real, your workspace)."],
        interpretation_guidance=["Your real deal documents — not market data."],
        limitations=[
            "Stores your uploaded documents in the local workspace; "
            "not a multi-party data-room product, no permissioning by "
            "external counsel/banker out of the box.",
            "Document-level search depends on each file's extractable "
            "text; image-only PDFs and scans won't be searchable until "
            "OCR is run upstream."],
        model_logic_summary=(
            "No model — a document-management surface. Lists uploaded "
            "deal documents from the local workspace, tags them by "
            "deal, and exposes extracted text for the Guide's "
            "downstream retrieval where extraction succeeded."),
        related_routes=["/diligence/ingest", "/diligence/deal", "/upload"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/methodology/calculations", "Methodology — Calculations",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="Reference documentation of how PEdesk's metrics and models "
        "are calculated.",
        primary_purpose="Explain the formulas/assumptions behind the analytics.",
        common_questions=[
            "How is the EBITDA bridge actually computed?",
            "What's the formula for the covenant cushion?",
            "Where do the health-score weights come from?",
            "Is the IRR calculated with annual or quarterly compounding?",
            "How does the Monte Carlo simulation seed work?",
        ],
        inputs=["No user inputs — a reference/methodology surface "
                "that documents the formulas wired into the "
                "calculation modules elsewhere in PEdesk."],
        outputs=["Narrative documentation of each formula "
                 "(EBITDA bridge, covenant cushion, health "
                 "score, IRR/MOIC, Monte Carlo seed) with "
                 "pointers to the modules that implement it."],
        key_metrics=["No metrics computed here — links to the "
                     "metric glossary and to each computing page."],
        diligence_use_cases=[
            "Sharing the methodology read with IC / LP / auditor "
            "to defend a number's derivation.",
            "Cross-referencing a formula against the code path "
            "that implements it (rcm_mc.pe / rcm_mc.mc / "
            "rcm_mc.calibration / rcm_mc.deals).",
        ],
        data_sources=["Documentation of PEdesk's own calculation methods."],
        interpretation_guidance=["Reference/methodology, not a data surface."],
        limitations=[
            "Documentation surface — the methods themselves live in "
            "code (rcm_mc.calibration, finance.regression, pe_math, "
            "mc.ebitda_mc); this page is the human read on them.",
            "Calibration parameters drift over time as priors are "
            "re-fit; the page captures the current method, not a "
            "historical methodology."],
        model_logic_summary=(
            "No model — narrative reference page that documents the "
            "formulas in code (EBITDA bridge in rcm_mc/pe/, MC seed "
            "in rcm_mc/mc/, health-score in rcm_mc/deals/, "
            "covenant cushion in rcm_mc/portfolio/). Each section is "
            "a description, not a computation."),
        related_routes=["/methodology", "/metric-glossary"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/module-index", "Module Index",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="A navigable index of every PEdesk module/surface.",
        primary_purpose="Find and jump to any tool or page.",
        common_questions=[
            "What pages does PEdesk have for portfolio monitoring?",
            "Where do I find the deal-pipeline tools?",
            "Is there a covenant-monitoring page?",
            "How does this differ from /tools?",
            "Where do I see only the green-tier pages?",
        ],
        inputs=["The route registration manifest (auto-populated "
                "by server startup; no user inputs).",
                "Optional client-side filter / search to narrow "
                "the index."],
        outputs=["A searchable index of every registered route, "
                 "grouped by category, with deep-links to each "
                 "page."],
        key_metrics=["Registered route count",
                     "Category counts"],
        diligence_use_cases=[
            "Locating a page when only the rough topic is known "
            "(faster than guessing URLs).",
            "Auditing the surface area of the platform during a "
            "review or hand-off.",
        ],
        data_sources=["The route/module manifest (system metadata)."],
        interpretation_guidance=["A navigation index, not a data surface."],
        limitations=[
            "Module index, not a data surface — for the data tools "
            "themselves use /tools (with honesty-tier colors) or the "
            "per-section /best/<section> rankings.",
            "Manifest-driven — newly added routes appear here once "
            "registered in the route table, but won't appear if a "
            "page is shipped without one."],
        model_logic_summary=(
            "No model — reads the route registration manifest, "
            "groups routes by category, and renders a searchable "
            "index. Filtering and sort happen client-side over the "
            "registered set."),
        related_routes=["/tools", "/library"],
        source_confidence=SourceConfidence.DOCUMENTED, data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/verticals", "Healthcare Verticals",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="Index of the CMS-data-backed healthcare vertical pages "
        "(dialysis, home health, hospice, SNF, IRF, LTCH, hospital).",
        primary_purpose="Navigate to the real-data vertical analytics by care setting.",
        common_questions=[
            "Which healthcare verticals does PEdesk have analytics for?",
            "Where's the SNF / nursing-home data?",
            "How fresh is each vertical's CMS data?",
            "How do I compare verticals on common metrics?",
            "Which verticals share the same CMS Care Compare source?",
        ],
        inputs=["No user inputs — a vertical-navigation hub.",
                "The vertical-page registry (which Care-Compare-"
                "backed verticals are live)."],
        outputs=["Vertical cards (dialysis, home health, hospice, "
                 "SNF, IRF, LTCH, hospital) linking to each "
                 "vertical's analytic page."],
        key_metrics=["Live vertical count",
                     "CMS Care-Compare verticals (real)"],
        diligence_use_cases=[
            "Choosing the right vertical entry point at the "
            "start of a sector-specific diligence sweep.",
            "Auditing which post-acute and acute verticals "
            "have real CMS data live in PEdesk before assuming "
            "coverage.",
        ],
        data_sources=["Real CMS public vertical datasets (per linked page)."],
        interpretation_guidance=["Each linked vertical uses real CMS public data."],
        limitations=[
            "Vertical hub — the linked pages carry the real data and "
            "source labels; this page just routes.",
            "Verticals covered are the CMS-Care-Compare set; private "
            "settings (e.g. ASCs, multi-specialty groups) are not "
            "directly covered as standalone verticals here."],
        model_logic_summary=(
            "No model — a vertical-navigation hub. Lists the CMS-"
            "Care-Compare-anchored verticals (dialysis, home health, "
            "hospice, SNF, IRF, LTCH, hospital) with deep-link cards "
            "to each vertical's analytic page. Each linked page does "
            "the real-data work; this page is just routing."),
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
                          "What does the data say about one state?",
                          "What public data backs the three state modes — and "
                          "what's the vintage of each source?",
                          "How does /geo-intel differ from /market-intel/geo?"],
        inputs=["No inputs of its own — the three linked verb pages "
                "each take state/metric query params."],
        outputs=["Navigation cards linking to /state-compare, "
                 "/state-rankings, /state-profile."],
        diligence_use_cases=["Picking the right state-analysis verb "
                             "at the start of a geographic-thesis "
                             "diligence pass."],
        data_sources=["Navigation surface only — links to the three modes; "
                      "renders no data itself."],
        key_metrics=["(none — hub page)"],
        interpretation_guidance=["A navigation surface; the linked modes carry "
                                 "the real data and the source labels."],
        why_it_matters="Makes the all-real-data state trio discoverable from "
        "the Source nav for origination screening.",
        limitations=[
            "Hub page — no data of its own; for state-level reads use "
            "/state-compare (head-to-head), /state-rankings (one "
            "metric, all states), or /state-profile (one state).",
            "Three modes share the same metric layer but expose "
            "different verbs; what's missing is missing from all three."],
        model_logic_summary=(
            "No model — a navigation hub with deep-link cards into "
            "/state-compare, /state-rankings, and /state-profile. "
            "The three modes share the same metric registry; the "
            "hub just picks which verb to apply."),
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
        common_questions=[
            "How does CA compare to TX and FL?",
            "Which of these states has the most providers / highest uninsured rate?",
            "What 15 metrics does the comparison cover?",
            "How does this differ from /state-rankings?",
            "Can I compare more than 4 states?",
        ],
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
        common_questions=[
            "Which states have the most provider-shortage areas?",
            "Where is MA penetration / the uninsured rate highest?",
            "How is sort direction handled for 'lower is better' metrics?",
            "Which metrics can I rank by?",
            "How does this differ from /state-compare and /state-profile?",
        ],
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
        limitations=[
            "Ranks one metric at a time — for a multi-metric read "
            "use /state-compare (head-to-head) or /state-profile "
            "(one state, all metrics).",
            "State-level only; no county or CBSA cuts here. Use "
            "/county-explorer for sub-state targeting."],
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
        common_questions=[
            "What does the data say about California?",
            "Where does this state rank nationally on each metric?",
            "Why is one metric listed as 'unranked'?",
            "Which state has the highest dual-eligible share?",
            "How does this differ from /state-rankings?",
        ],
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
        limitations=[
            "Single-state dossier — for a head-to-head between two or "
            "more states use /state-compare; for one metric across "
            "all states use /state-rankings.",
            "State-level only; no sub-state cuts. Use /county-explorer "
            "for county-level demographics on a chosen state."],
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
        common_questions=[
            "Which states are most like Ohio?",
            "Where else resembles this market?",
            "How is similarity defined (RMS of z-score gaps)?",
            "How many shared metrics are needed for a state to score?",
            "Are these comp-states from real public data or a model?",
        ],
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
        limitations=[
            "RMS-distance heuristic on standardized z-scores — "
            "captures structural similarity but not regulatory or "
            "competitive context (e.g. one-payer dominance, CON laws).",
            "States with fewer than 6 shared metrics are excluded "
            "from scoring rather than given a low-confidence number."],
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
        common_questions=[
            "Which Ohio counties are largest / oldest / poorest?",
            "What does this state look like county by county?",
            "Which counties have the highest uninsured rate?",
            "How is rural share computed for a county?",
            "Where does the data come from — keyless ACS / SAHIE / SAIPE?",
        ],
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
        limitations=[
            "ACS/SAHIE/SAIPE survey-based — county estimates carry "
            "margins of error (especially in small-population counties) "
            "that the page doesn't surface inline; consult the upstream "
            "source for MOEs.",
            "Demographics only here — no provider supply or quality "
            "cuts at county level; use /geo-intel and /target-screener "
            "for those views."],
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
                          "Is this real or illustrative?",
                          "How is EBITDA-at-risk computed — and what does it assume?",
                          "How does /diligence/bear-case differ from "
                          "/diligence/risk-workbench and /diligence/payer-stress?"],
        inputs=["A dataset fixture (full pipeline) OR live deal inputs "
                "(standalone regulatory/covenant/bridge/HCRIS extractors)."],
        outputs=["Ranked risk evidence by theme + an IC-memo bear-case preview."],
        key_metrics=["EBITDA-at-risk $", "Risk-theme rank",
                     "Bear-case headline"],
        diligence_use_cases=["Forcing the downside view into the IC "
                             "memo before the committee meeting."],
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
        "/diligence/denial-prediction", "Denial Prediction",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="Trains a per-claim denial model on a CCD claims feed "
        "and sizes the recoverable revenue from denial management.",
        primary_purpose="Estimate recoverable denied revenue to underwrite an "
        "RCM denial-management initiative into the EBITDA bridge.",
        common_questions=["How much denied revenue is recoverable?",
                          "How good is the model (AUC) on this sample?",
                          "Is this the deal's real claims, or a fixture?",
                          "Which denial categories drive most of the recoverable $?",
                          "How does this number feed the EBITDA bridge in /diligence/value?"],
        inputs=["A CCD (consolidated clinical document) claims feed — a fixture "
                "sample unless the deal's own CCD is provided."],
        outputs=["Per-claim denial probabilities, AUC, denial Pareto, recoverable $."],
        key_metrics=["AUC", "Recoverable $", "Top denial categories"],
        diligence_use_cases=["Sizing the denial-management lever for "
                             "the deal's value-creation bridge."],
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
    # /diligence/physician-eu intentionally NOT auto-generated here — it
    # has a rich hand-written context at the top of _MANUAL that covers
    # the same data-required content plus common_questions, model_logic,
    # interpretation_guidance, etc. Auto-generating a second thin entry
    # would silently override the rich one via the dict construction.
    # /diligence/risk-workbench intentionally NOT auto-generated — it
    # has a rich hand-written context at line ~1158 that covers the
    # nine-panel structural risk read, Steward precedent demo mode,
    # interpretation guidance, and limitations. Auto-generating a
    # thin entry would silently override the rich one via the dict
    # construction.
]

# HIGH_PRIORITY pages must keep metric/data-source links (test_pedesk_guide_metric_data_context).
_DR_DATA_SOURCE_IDS = {
    "/diligence/physician-eu": ["compensation_file", "provider_roster"],
}
for _route, _title, _upload, _who, _activates, _tmpl in _DATA_REQUIRED_GUIDE:
    # 2026-05-30 audit follow-up: every DATA_REQUIRED page shares the
    # same shape of partner questions ("what do I upload", "who do I
    # ask", "what does this compute once live", "where's the import
    # template"). The Guide answers each more crisply when those
    # questions are wired in explicitly instead of falling back to the
    # generic _ctx default ("What does this page do? Where does its
    # data come from?"). The strings interpolate the per-page upload
    # type, requester, activates summary, and template filename — so
    # each generated entry's questions reference its specific data slot.
    _dr_common_questions = [
        f"What data do I need to upload to activate {_title}?",
        f"Where do I get the {_upload} data from? ({_who} typically owns it.)",
        f"What does {_title} compute once my data is uploaded?",
        f"Where's the import template ({_tmpl})?",
        f"Why is {_title} DATA REQUIRED — what data is missing?",
    ]
    _MANUAL.append(_ctx(
        _route, _title,
        short_description=(f"{_title} activates on YOUR uploaded {_upload}; until "
                           "then it shows an illustrative scaffold (no fabricated "
                           "values), with a panel listing exactly what to provide."),
        primary_purpose=f"Once your data is uploaded: {_activates}.",
        common_questions=_dr_common_questions,
        # 2026-05-31: real defaults for the four list-shaped fields
        # the loop wasn't passing (was inheriting [_NEEDS] for each).
        # Every DR page's inputs/outputs/key_metrics/diligence_use_cases
        # share the same shape once you frame them around the upload
        # and the activated computation.
        inputs=[
            f"YOUR {_upload}, uploaded via /import or the page's "
            f"upload widget using template {_tmpl}.",
            f"Optional metadata that scopes the analysis to one "
            "deal or fund (e.g. deal_id, fund_id) — see the page's "
            "request panel for which scopes apply.",
        ],
        outputs=[
            f"Once data is loaded: {_activates}.",
            "Until then: an illustrative scaffold + a request panel "
            "describing exactly what to upload.",
        ],
        key_metrics=[
            f"Driven by the loaded {_upload} — the analytic surfaces "
            "the metrics that the upload makes computable.",
        ],
        diligence_use_cases=[
            f"Activating {_title} for a deal/fund as part of the "
            "DATA_REQUIRED diligence sweep.",
            f"Requesting {_upload} from {_who} as a P0 diligence task.",
        ],
        data_sources=[f"USER DATA REQUIRED — upload {_upload} (import template: {_tmpl})."],
        data_source_ids=_DR_DATA_SOURCE_IDS.get(_route, []),
        interpretation_guidance=[
            "Not live until you upload your own data — the page shows what to provide.",
            f"Request the data from: {_who}.",
            "Figures currently shown are an illustrative scaffold, NOT this deal's values.",
        ],
        # 2026-05-30: every DATA_REQUIRED page shares two real
        # limitations. The earlier loop default left [_NEEDS] —
        # replace it with the same template that the rest of the
        # fields use, so the Guide can honestly answer "what should
        # I be careful about here" without the placeholder string.
        limitations=[
            f"Only as complete as the uploaded {_upload} — sparse or "
            "stale data degrades every downstream computation on this "
            "page.",
            f"Until that data lands, the values shown are an "
            "illustrative scaffold — they are NOT this deal's "
            "figures and must not be cited as such.",
        ],
        # 2026-05-30: every DATA_REQUIRED page benefits from the same two
        # universal siblings — /diligence/checklist is where outstanding
        # uploads register as P0 blockers, and /tools is the index where
        # a partner finds the next surface to populate.
        related_routes=["/diligence/checklist", "/tools"],
        # 2026-05-31: every DATA_REQUIRED page shares the same shape
        # for model_logic. Until the upload lands the page is a
        # scaffold; once it lands the platform parses the uploaded
        # CSV against the published import template, joins it to the
        # deal/fund context, and lights up the analytics the
        # "activates" string describes.
        model_logic_summary=(
            f"DATA_REQUIRED scaffold until the partner uploads "
            f"{_upload} (template: {_tmpl}); on upload, the platform "
            f"parses the CSV against the template schema, joins the "
            f"rows to the deal/fund context, and computes "
            f"{_activates}. No values are fabricated before that — "
            "the panel describes what to provide rather than running "
            "a model on empty input."
        ),
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
            "How fresh is the HCRIS universe powering these models, and which "
            "peer cohort defines 'peers'?",
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
        "universe with a full classical inference + diagnostic suite: "
        "heteroskedasticity-robust (HC1) standard errors, exact Student-t "
        "p-values and t-based CIs, multicollinearity diagnostics (VIF, Belsley "
        "condition number) with a VIF-pruned optimized model, residual tests "
        "(Breusch–Pagan, Ramsey RESET, Jarque–Bera), AIC/BIC, a Shapley R² "
        "driver-importance decomposition, and a heteroskedasticity-robust "
        "joint F-test.",
        primary_purpose="Let the team fit and interpret a transparent linear "
        "model of a hospital financial outcome on operating drivers, while "
        "actively guarding against the high-R²-but-meaningless trap that "
        "multicollinearity creates and reporting honestly whether the OLS "
        "assumptions actually hold for this fit.",
        intended_users=["Quantitatively-inclined principals/associates."],
        common_questions=[
            "Which features actually drive the target, net of collinearity?",
            "Why was a feature dropped from the optimized model?",
            "Is this R² real or inflated by multicollinearity?",
            "What does the condition number tell me?",
            "Are the standard errors robust to heteroskedasticity?",
            "Does Breusch–Pagan / Ramsey RESET / Jarque–Bera flag a problem?",
            "Which driver owns the most explained variance (Shapley R²)?",
            "Why is the robust F different from the classical F?",
        ],
        inputs=["CMS HCRIS latest-per-CCN data; query controls for target "
                "variable, universe filter, log-target, and segmented "
                "regression. Honest-by-default on first load: leaky features "
                "are dropped and dollar targets log-transformed."],
        outputs=["Coefficient table with HC1-robust SEs, exact Student-t "
                 "p-values and t-based 95% CIs; R²/adjusted R², classical and "
                 "heteroskedasticity-robust joint F tests; AIC/BIC; per-feature "
                 "VIF and the Belsley condition number with a verdict banner; a "
                 "VIF-pruned optimized model; residual diagnostics (Breusch–"
                 "Pagan heteroskedasticity, Ramsey RESET functional form, "
                 "Jarque–Bera normality) with plain-language verdicts; and a "
                 "Shapley R² driver-importance panel."],
        key_metrics=["R² / adjusted R²", "Classical & robust F statistic",
                     "HC1-robust coefficient SEs", "Exact Student-t p-values",
                     "VIF", "Condition number", "AIC / BIC",
                     "Breusch–Pagan", "Ramsey RESET", "Jarque–Bera",
                     "Shapley R² share"],
        data_sources=["CMS HCRIS (Medicare cost reports)."],
        model_logic_summary=(
            "Ordinary least squares fit in-page (the page has its own _run_ols), "
            "with the statistics implemented in rcm_mc/finance/regression.py and "
            "no scipy. Inference uses HC1 (White sandwich) robust standard errors "
            "and EXACT Student-t p-values + t critical values via the incomplete "
            "beta (F(1,df)=t²(df)), so it's honest at small sample sizes. "
            "Diagnostics: VIF + Belsley condition number + multicollinearity "
            "verdict + prune_collinear; Breusch–Pagan (variance), Ramsey RESET "
            "(functional form) and Jarque–Bera (residual normality, exact χ²(2)); "
            "AIC/BIC for model selection; a Shapley/LMG decomposition that splits "
            "R² fairly across correlated drivers; and a robust (HC1 Wald) joint "
            "F-test that stays valid when Breusch–Pagan finds heteroskedasticity. "
            "The default view is the defensible model: algebraically-leaky "
            "features removed and dollar targets log-transformed; an explicit "
            "form submit lets a partner inspect the leaky/raw-dollar version."),
        why_it_matters="A high R² from a collinear model is a classic "
        "diligence false-positive; this page makes the model honest, reports "
        "whether its assumptions hold, and makes the dropped-feature reasoning "
        "explicit.",
        diligence_use_cases=[
            "Identifying which operating levers move a financial outcome.",
            "Pressure-testing a thesis claim that 'X drives Y' for collinearity."],
        interpretation_guidance=[
            "A high condition number (or red verdict banner) means coefficients "
            "are unstable — read the optimized/pruned model, not the raw one.",
            "A feature dropped for collinearity is not 'unimportant'; it is "
            "redundant with another feature already in the model.",
            "Standard errors are HC1-robust; if Breusch–Pagan flags "
            "heteroskedasticity, trust the robust SEs and the robust F over the "
            "classical ones. If Ramsey RESET fires, the linear shape is missing "
            "curvature — try the log toggle. If Jarque–Bera flags non-normal "
            "residuals, lean on the robust SEs and the effect direction rather "
            "than a borderline p-value.",
            "Shapley R² shares are the fair, additive split of explained "
            "variance across drivers and sum to the model's R² — use them, not "
            "univariate correlations, to say which lever matters most.",
            "This fits public HCRIS, not a single deal's financials."],
        limitations=[
            "Cross-sectional HCRIS only — no causal claim, just association.",
            "Out-of-sample (cross-validated) performance is only shown when the "
            "Cross-validate toggle is on; the default metrics are in-sample."],
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
            "What are the illustrative inputs (entry EV, debt, growth, margin) "
            "and what should I replace with the deal's real figures?",
            "How does /lbo-stress differ from /scenarios and /portfolio/monte-carlo?",
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
            "Where does a preset get applied — is this page the catalog, or does it run anything?",
            "How does /scenarios differ from /lbo-stress and /portfolio/monte-carlo?",
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
            "How many deal packets need to be saved before this page is meaningful?",
            "Where are the correlation assumptions defined and how can they be inspected?",
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
      "Which initiatives are behind?",
      "How is targeted EBITDA impact rolled up across initiatives, and is double-counting checked?",
      "How does /value-creation-plan differ from /portfolio and /diligence/value?"],
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
      "EBITDA?", "Which adjustments are aggressive?",
      "Which add-back categories does the analyzer split out, and how is each labeled (one-time, normalization, owner)?",
      "How does /qoe-analyzer differ from /diligence/qoe-memo and /diligence/bridge-audit?"],
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
      "concentrated?", "How diversified is this construction?",
      "What corpus is the deal universe drawn from, and how many deals make a meaningful optimization?",
      "How does this differ from /portfolio/monte-carlo and /hold-optimizer?"],
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
      "longer?", "When does MOIC stop compensating for time?",
      "What entry profile does the model assume — and which inputs should I override for a real deal?",
      "How does /hold-optimizer differ from /portfolio-optimizer and /exit-readiness?"],
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
      "What should we fix before going to market?",
      "How are the Financial / Operational / Commercial / Governance axes weighted in the composite score?",
      "How does /exit-readiness differ from /hold-optimizer and /qoe-analyzer?"],
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
      "rate-savings impact?",
      "What rate / leverage / fees does the model assume — and which should I override for a real refi?",
      "How does the cash-out vs rate-savings trade-off feed MOIC and IRR?"],
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
      "Which payers drive DSO?",
      "How does releasing AR translate to a one-time cash benefit vs ongoing margin?",
      "How does /working-capital differ from /diligence/qoe-memo and /rcm-benchmarks?"],
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
      "Which providers are profitable?",
      "What does the ramp curve assume about visit/wRVU growth, payer mix, and overhead allocation?",
      "How does /unit-economics differ from /diligence/physician-eu and /rollup-economics?"],
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
      "What blended multiple results?",
      "How is synergy capture phased in, and what realization haircut is reasonable?",
      "How does /rollup-economics differ from /unit-economics and /portfolio-optimizer?"],
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
      "active in this sector?",
      "What deal corpus drives the rank, and is sponsor coverage even across the universe?",
      "How does /sponsor-league differ from /deal-library/sponsors and /return-attribution?"],
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
      "How much runway is left?",
      "How is TAM vs SAM vs SOM defined here, and what bounds the SOM?",
      "How does /growth-runway differ from /industry and /market-intel/geo?"],
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
      "How dispersed are returns?",
      "Which dimensions (sector, vintage, payer mix) is the decomposition cut on, and is interaction handled?",
      "How does /return-attribution differ from /deal-corpus-analytics and /sponsor-league?"],
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
      "better?", "How do sectors compare on entry price?",
      "Is the entry-multiple-vs-return correlation causal or selection-driven (better businesses sell for more)?",
      "How does /entry-multiple differ from /exit-multiple and /comparables?"],
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
      "expansion?", "Which sectors re-rate on exit?",
      "What's the disciplined assumption — flat-to-entry, sector median, or paid?",
      "How does /exit-multiple differ from /entry-multiple and /sponsor-league?"],
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
      "the IRR/DPI impact?",
      "What leverage covenants and rate environment does the page assume — and how should I override them?",
      "How does /dividend-recap differ from /refi-optimizer and /hold-optimizer?"],
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
      "Where is deal flow heating up or cooling?",
      "What deal corpus underlies the heatmap, and how complete is its sector coverage?",
      "How does /deal-flow-heatmap differ from /sponsor-heatmap and /sector-intel?"],
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
      "Which sponsor/sector cells outperform?",
      "What minimum deal-count per cell is needed before a cell's MOIC means something?",
      "How does /sponsor-heatmap differ from /sponsor-league and /deal-flow-heatmap?"],
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
      "Which sectors return best?",
      "Is the sector taxonomy mine or the corpus's, and how is each deal classified?",
      "How does /sector-intel differ from /sector-intelligence and /industry?"],
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
      "Are these two sectors a hedge or a double-down?",
      "Are these correlations of realized MOIC, IRR, or revenue/EBITDA growth — and on what time window?",
      "How sample-thin is each pair (low n inflates apparent correlation)?"],
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
      "How levered are peer deals?",
      "Is the corpus leverage measured at entry, refi-adjusted, or at exit?",
      "How does /leverage-intel differ from /size-intel and /entry-multiple?"],
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
      "Where does this deal sit on size?",
      "How are the size bands cut, and how thin is the smallest/largest band?",
      "How does /size-intel differ from /entry-multiple and /sector-intel?"],
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
      "How risky is this payer profile?",
      "Is the corpus payer mix self-reported, derived from HCRIS, or imputed when missing?",
      "How does /payer-intel differ from /payer-intelligence and /diligence/payer-stress?"],
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
      "Is this a good year to deploy?",
      "How many corpus deals back each vintage's P50 — and when is the tail of recent vintages too unrealized to compare?",
      "How does /vintage-perf differ from /vintage-cohorts and /deal-corpus-analytics?"],
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
      "Where do they out/underperform?",
      "How many of the GP's actual deals are in the corpus — and what fraction are realized?",
      "How does /gp-benchmarking differ from /sponsor-league and /sponsor-heatmap?"],
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
      "Is the premium justified?",
      "Which drivers (sector, size, growth, quality) carry the most weight, and how is the residual handled?",
      "How does /multiple-decomp differ from /entry-multiple and /peer-transactions?"],
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
      "What multiples are defensible?",
      "How is 'comparable' defined here (sector, size, geography, payer mix), and is that filter exposed?",
      "How does /peer-transactions differ from /comparables and /peer-valuation?"],
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
      "Which cohorts have realized?",
      "How does the page handle partial realization — does the maturity curve mix realized and unrealized marks?",
      "How does /vintage-cohorts differ from /vintage-perf and /fund-attribution?"],
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
      "Was it operations or leverage?",
      "Are the operational / multiple / leverage components additive, multiplicative, or path-dependent?",
      "How does /fund-attribution differ from /return-attribution and /gp-benchmarking?"],
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
      "Where's the midpoint?",
      "Which comps and precedents feed each band of the football-field, and where can I exclude outliers?",
      "How does /peer-valuation differ from /peer-transactions and /comparables?"],
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
      "What's the pacing curve?",
      "What pacing benchmark does the model lean on — vintage average, commitment-based, or a custom schedule?",
      "How does /capital-pacing differ from /capital-call and /reinvestment?"],
     ["Commitment", "Called %", "Pacing curve"], [], [],
     "Projects a call schedule from entered commitment/deployment assumptions; "
     "illustrative unless populated with a real fund plan.",
     "Pacing errors strand capital or force rushed deals.",
     _DC.MODEL_ESTIMATE),
    ("/reinvestment", "Reinvestment Analyzer",
     "Models reinvesting realized proceeds — recycling and its return impact.",
     "Evaluate whether recycling proceeds improves fund-level returns.",
     ["Should we recycle proceeds?", "What's the return impact?",
      "How much can we reinvest?",
      "What recycling caps and LPA limits should I check before believing the page's optimal answer?",
      "How does /reinvestment differ from /capital-pacing and /dividend-recap?"],
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
      "What has to be true to hit target?",
      "Which entry, growth, leverage and exit assumptions drive most of the MOIC variance?",
      "How does /underwriting-model differ from /lbo-stress and /hold-optimizer?"],
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
      "What needs follow-up?",
      "Where is the data entered, and is it persisted across sessions or session-scoped?",
      "How does /deal-sourcing differ from /deal-origination and /pipeline?"],
     ["Lead count", "By channel", "By stage"], [], [],
     "Tracks entered sourcing leads through channels/stages; seed figures are "
     "illustrative until you add your own pipeline.",
     "Proprietary flow is the cheapest, least-competitive deal source.",
     _DC.MIXED),
    ("/deal-origination", "Deal Origination Tracker",
     "M&A origination / pipeline tracker — targets, outreach, and status.",
     "Manage active origination targets and outreach status.",
     ["What's in the origination pipeline?", "Which targets are warm?",
      "What's the next action?",
      "Is target/status data session-scoped or persisted, and how do owners and dates show up?",
      "How does /deal-origination differ from /deal-sourcing and /pipeline?"],
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
      "What's due to LPs?",
      "Are calls / distributions persisted across sessions, and is there an audit trail?",
      "How does /capital-call differ from /capital-pacing and /lp-update?"],
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
      "structure change IRR?",
      "Does the model assume current federal rates only, or are state and entity-level effects included?",
      "How does /tax-structure differ from /tax-structure-analyzer (the alias) and /tax-credits?"],
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
      "Asset vs stock trade-off?",
      "This page is an alias of /tax-structure — is there any behavioral difference between the two routes?",
      "What rate, basis, and entity assumptions should I override to match a real deal?"],
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
      "Does it bridge the bid-ask?",
      "How does the expected-cost calc treat correlation between earnout targets and the deal's base-case path?",
      "How does /earnout differ from /escrow-earnout and /capital-schedule?"],
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
      "What's the funding schedule?",
      "Which fees, OID, and reserves are included in the uses, and where can I override them?",
      "How does /capital-schedule differ from /capital-call and /cap-structure?"],
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
      "What's the filing status?",
      "Is the credit list seeded from a static catalog or scoped by sector/state, and how should I override it for a real platform?",
      "How does /tax-credits differ from /tax-structure (structural choice) and /tax-structure-analyzer?"],
     ["Credit value", "By type"], [], [],
     "Tracks entered credit/incentive records; illustrative seed until "
     "populated. NOT tax advice.",
     "Unclaimed incentives are free return; tracking them is pure upside.",
     _DC.MIXED),
    ("/escrow-earnout", "Escrow & Earnout Tracker",
     "Tracks escrow balances and earnout milestones / payouts post-close.",
     "Monitor escrow releases and earnout milestones so obligations are met "
     "and recoveries claimed.",
     ["What's in escrow?", "When does it release?", "What earnouts are due?",
      "Are milestones / payouts persisted, and is there an event log when a release fires?",
      "How does /escrow-earnout differ from /earnout (modeling) and /capital-call (LP cash)?"],
     ["Escrow balance", "Earnout milestones"], [], [],
     "Tracks entered escrow/earnout records; illustrative seed until "
     "populated.",
     "Escrow and earnout slip-ups leak real money post-close.",
     _DC.MIXED),
    ("/debt-financing", "Debt Financing Tracker",
     "Tracks LBO debt commitments, lenders, terms, and the financing process.",
     "Manage the debt-financing process from term sheets to commitment.",
     ["Who are the lenders?", "What terms are committed?", "Where's the "
      "financing process?",
      "Are covenants and pricing grids captured per-tranche, or just headline leverage?",
      "How does /debt-financing differ from /direct-lending and /nav-loan-tracker?"],
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
      "the fund?",
      "Is DPI here gross or net of fees and carry, and does the realization include unrealized marks?",
      "How does /dpi-tracker differ from /lp-reporting and /capital-call?"],
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
      "been distributed?",
      "Which performance measures (gross/net, fund-level/deal-level) does the report show, and is the period selectable?",
      "How does /lp-reporting differ from /lp-update and /dpi-tracker?"],
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
                          "How confident is this output?",
                          "Which packet inputs (CIM, claims, financials, public "
                          "data) feed this section, and which are observed vs "
                          "illustrative?",
                          "How does this connect to the other /models/<type> "
                          "views on the same deal's packet?"],
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
      "Where does this sit vs peers?",
      "How is 'comparable' computed — distance on which numeric features, and is the cohort size shown?",
      "How does /diligence/comparable-outcomes differ from /comparable-outcomes and /models/comparables?"],
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
      "Which levers backtest well?",
      "How is a thesis defined for replay — and does the backtest control for sector and vintage?",
      "How does /backtester differ from /base-rates and /portfolio-sim?"],
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
      "What are the odds historically?",
      "How is the outcome defined — and how is the comparable cohort cut so the rate isn't inflated by selection?",
      "How does /base-rates differ from /backtester and /corpus-dashboard?"],
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
      "How does construction change the distribution?",
      "How many draws does the simulator use, and is the seed deterministic across reloads?",
      "How does /portfolio-sim differ from /portfolio/monte-carlo and /lbo-stress?"],
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
      "this benchmark?",
      "Which downstream tools degrade most when a specific field is sparse?",
      "How does /corpus-coverage differ from /corpus-dashboard and /diligence/snapshot?"],
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
      "the coverage strong?",
      "What time window and licensing scope does the corpus span — and how does that bound the read?",
      "How does /corpus-dashboard differ from /corpus-coverage and /deal-corpus-analytics?"],
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
      "failed validation?",
      "Which 835/837 fields are required vs optional for downstream analytics to light up?",
      "How does /diligence/snapshot differ from /upload, /new-deal/upload and /diligence/checklist?"],
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
     ["Draft the IC memo", "What goes in the memo?", "What's missing for IC?",
      "What template/sections does the generator use, and can the partner override section order or hide a section?",
      "How does /ic-memo-gen differ from /ic-memo, /diligence/ic-memo, /corpus-ic-memo, and /diligence/ic-packet?"],
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
      "What's the peer context?",
      "Which sections pull from the deal's packet vs from corpus benchmarks?",
      "How does /corpus-ic-memo differ from /ic-memo, /ic-memo-gen, and /diligence/ic-packet?"],
     ["MOIC", "IRR", "Benchmark percentile"],
     ["moic", "irr"], ["analysis_run", "public_transaction_corpus"],
     "Composes a memo from the deal's packet plus corpus comparables; "
     "benchmarks reflect corpus coverage.",
     "Peer-anchored memos are harder to wave away at IC.",
     _DC.MIXED, "deal"),
    ("/ic-memo", "IC Memo",
     "Investment-committee memo view for a deal.",
     "Review the IC memo for a deal in one place.",
     ["Show the IC memo", "What's the recommendation?", "What are the risks?",
      "Which packet sections produce the recommendation, and how is the rec text generated vs partner-entered?",
      "How does /ic-memo differ from /diligence/ic-memo, /ic-memo-gen, /corpus-ic-memo, and /diligence/ic-packet?"],
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
      "MC?", "When should I run the real sim?",
      "What was the surrogate trained on, and is the calibration error reported alongside the estimate?",
      "How does /surrogate differ from /portfolio/monte-carlo and /scenario-mc?"],
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
      "Where's the fragility?",
      "Which preset shocks does it apply by default, and can I layer multiple shocks at once?",
      "How does /pressure differ from /lbo-stress, /scenarios, and /diligence/payer-stress?"],
     ["EBITDA under stress", "Risk score"], ["ebitda", "risk_score"], [],
     "Applies adverse-scenario shocks to entered assumptions and reports the "
     "outcome; illustrative unless deal inputs are supplied.",
     "A thesis you haven't stressed is a thesis you don't understand.",
     _DC.MODEL_ESTIMATE, "model"),
    ("/demand-forecast", "Demand Forecast",
     "Projects future demand / volume from entered trend assumptions.",
     "Stress-test the volume assumptions a revenue thesis rests on.",
     ["What demand is assumed?", "How sensitive is revenue to volume?",
      "Is the growth realistic?",
      "What seasonality and saturation curves does the projection use, and how should I override them?",
      "How does /demand-forecast differ from /growth-runway and /denovo-expansion?"],
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
      "sponsor exit?",
      "What signals (multiple regime, EBITDA growth slowdown, buyer interest) drive the timing score?",
      "How does /exit-timing differ from /exit-readiness, /hold, and /hold-optimizer?"],
     ["Exit multiple", "MOIC", "Buyer fit"], ["exit_multiple", "moic"], [],
     "Scores exit timing/buyer fit from entered assumptions; illustrative.",
     "The right buyer at the right time can out-matter the entry price.",
     _DC.MODEL_ESTIMATE, "model"),
    ("/hold", "Hold-Period Dashboard",
     "Tracks portfolio holdings by hold period — age, value progression, and "
     "exit readiness.",
     "See where each holding is in its hold and which are nearing exit.",
     ["How long have we held each deal?", "Which are near exit?", "How's "
      "value progressing?",
      "What 'near exit' threshold does the dashboard use, and is value progression based on marks or modeled?",
      "How does /hold differ from /hold-optimizer and /exit-readiness?"],
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
      "EBITDA gap to plan?",
      "How is 'plan' versioned, and does the page diff against the entry plan, the latest re-plan, or both?",
      "How does /value-tracker differ from /value-creation, /value-creation-plan, and /variance?"],
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
      "How big is the opportunity?",
      "What switch rate, discount, and rebate assumptions does the analyzer use, and how should I override them?",
      "How does /biosimilars differ from /drug-pricing-340b and the broader QoE add-back tools?"],
     ["Savings opportunity"], [],
     "Biosimilar substitution is a concrete, near-term drug-cost lever.", "model"),
    ("/drug-pricing-340b", "340B Drug Pricing Analyzer",
     "Estimates 340B program savings vs non-340B acquisition cost.",
     ["What's the 340B savings?", "Which sites qualify?", "How much margin "
      "does 340B add?",
      "What discount, mix, and contract-pharmacy assumptions does the analyzer use, and how should I override them for a real platform?",
      "How does /drug-pricing-340b differ from /tracker-340b and /biosimilars?"],
     ["340B savings"], [],
     "340B economics materially change pharmacy margin for eligible providers.",
     "model"),
    ("/reit-analyzer", "REIT / Sale-Leaseback Analyzer",
     "Models a healthcare sale-leaseback / REIT scenario — cap rate, proceeds, "
     "and rent drag.",
     ["What does a sale-leaseback yield?", "What's the rent drag on EBITDA?",
      "Is the cap rate attractive?",
      "What rent-escalator and tenor does the page assume, and how do master-lease vs single-property structures change the answer?",
      "How does /reit-analyzer differ from /capital-schedule and /cap-structure?"],
     ["Proceeds", "EBITDA", "Enterprise value"], ["ebitda", "enterprise_value"],
     "Real-estate monetization can fund a deal but burdens future EBITDA.",
     "model"),
    ("/trial-site-econ", "Clinical Trial Site Economics",
     "Models the economics of running clinical-trial sites — per-site revenue "
     "and contribution.",
     ["What does a trial site earn?", "Is the contribution positive?",
      "How many sites to break even?",
      "What study mix, enrollment rate, and per-patient revenue does the model assume — and how should I override them?",
      "How does /trial-site-econ differ from /unit-economics and /denovo-expansion?"],
     ["Revenue/site", "Contribution margin"],
     ["revenue", "provider_contribution_margin"],
     "Trial revenue is a distinct, often-overlooked provider income stream.",
     "model"),
    ("/specialty-benchmarks", "Specialty Benchmarks Library",
     "A library of operating benchmarks by clinical specialty.",
     ["What are typical margins for this specialty?", "How does this specialty "
      "benchmark?", "What's the productivity norm?",
      "What's the source vintage of these benchmarks (MGMA, AAMC, corpus-derived), and how often is the library refreshed?",
      "How does /specialty-benchmarks differ from /diligence/benchmarks and /diligence/physician-eu?"],
     ["EBITDA margin", "Revenue"], ["ebitda_margin", "revenue"],
     "Specialty norms anchor what 'good' looks like for a target.", "model"),
    ("/phys-comp-plan", "Physician Compensation Plan Designer",
     "Models physician compensation plan structures (wRVU, base+incentive) and "
     "their cost.",
     ["What does this comp plan cost?", "Is comp aligned to production?",
      "How does wRVU-based pay compare?",
      "Which specialty benchmarks does the designer use, and how should I override the wRVU conversion factor?",
      "How does /phys-comp-plan differ from /diligence/physician-eu and /workforce-planning?"],
     ["Comp-to-collections", "Productivity"],
     ["compensation_to_collections", "provider_productivity"],
     "Physician comp is the largest cost line and the key retention lever.",
     "model"),
    ("/workforce-planning", "Workforce Planning Analyzer",
     "Models staffing levels, labor cost, and workforce gaps.",
     ["What's the labor cost ratio?", "Where are staffing gaps?", "What's the "
      "right staffing level?",
      "Does the page model agency / locum reliance separately from employed FTEs, and what target ratio does it use?",
      "How does /workforce-planning differ from /diligence/physician-eu and /physician-labor?"],
     ["Labor cost ratio", "FTE gap"], ["labor_cost_ratio"],
     "Labor is the dominant operating cost in provider businesses.", "model"),
    ("/esg-dashboard", "ESG Dashboard",
     "Summarizes ESG metrics and scores for a platform.",
     ["What's the ESG profile?", "Where are the ESG gaps?", "What do LPs "
      "want here?",
      "Which ESG framework (SASB, TCFD, custom) does the score map to, and are the inputs partner-entered or imputed?",
      "How does /esg-dashboard differ from /esg-impact and /pmi-integration?"],
     ["ESG score"], [],
     "ESG posture increasingly affects LP appetite and exit buyer lists.",
     "model"),
    ("/fraud-detection", "Fraud / Waste / Abuse Detection",
     "Flags potential fraud, waste, and abuse patterns in claims/operations "
     "data.",
     ["Any FWA red flags?", "Which patterns look anomalous?", "What needs a "
      "compliance look?",
      "Which detection patterns (upcoding, modifier abuse, duplicate billing) does the page run, and at what z-threshold?",
      "How does /fraud-detection differ from /models/anomalies and /diligence/risk-workbench?"],
     ["Risk score", "Flag count"], ["risk_score"],
     "Undetected FWA is a compliance and valuation landmine.", "model"),
    ("/geo-market", "Geographic Market Analyzer",
     "Analyzes a geographic market — demand, competition, and positioning.",
     ["What's this market like?", "Who competes here?", "Is there room to "
      "grow?",
      "What public data backs the demand and competitor counts, and at what geographic granularity (CBSA, county, state)?",
      "How does /geo-market differ from /market-intel/geo and /geo-intel?"],
     ["Market size", "Competitor count"], [],
     "Geography shapes demand, competition, and reimbursement.", "model"),
    # Trackers (user-entered)
    ("/denovo-expansion", "De Novo Expansion Tracker",
     "Tracks de novo (greenfield) site openings — pipeline, ramp, and "
     "economics.",
     ["What de novos are planned?", "How are they ramping?", "What's the "
      "expansion economics?",
      "How does the tracker model ramp lag, payer enrollment, and breakeven month — and are those overridable?",
      "How does /denovo-expansion differ from /unit-economics and /rollup-economics?"],
     ["Site count", "Revenue", "Ramp"], ["revenue", "ebitda_margin"],
     "Organic de novo growth complements M&A in a platform thesis.", "user"),
    ("/tracker-340b", "340B Pharmacy Program Tracker",
     "Tracks 340B program participation, contract pharmacies, and compliance.",
     ["What's our 340B footprint?", "Which contract pharmacies?", "Any "
      "compliance gaps?",
      "Are program audit logs and HRSA recertification dates captured, with alerting on lapses?",
      "How does /tracker-340b differ from /drug-pricing-340b and /tax-credits?"],
     ["Site count", "Savings"], [],
     "340B compliance is high-scrutiny; tracking it protects the savings.",
     "user"),
    ("/physician-labor", "Physician Labor Market Tracker",
     "Tracks physician supply, attrition, and recruiting in target markets.",
     ["What's physician attrition?", "Is the market tight?", "What's the "
      "recruiting pipeline?",
      "Is attrition computed from the entered roster or imputed from market data, and what defines 'tight'?",
      "How does /physician-labor differ from /diligence/physician-attrition and /workforce-planning?"],
     ["Attrition", "Productivity"],
     ["physician_attrition", "provider_productivity"],
     "Physician supply/retention is a first-order risk in provider deals.",
     "user"),
    ("/hospital-anchor", "Hospital Anchor Contract Tracker",
     "Tracks anchor hospital / health-system contracts and their terms.",
     ["What anchor contracts exist?", "When do they renew?", "What's the "
      "concentration risk?",
      "Are renewal dates and terms persisted with an audit trail, and does the page flag concentration above a threshold?",
      "How does /hospital-anchor differ from /diligence/hcris-xray and /payer-stress?"],
     ["Contract count", "Concentration"], [],
     "Anchor-contract concentration is a major revenue-durability risk.",
     "user"),
    ("/ma-star", "Medicare Advantage / Star Ratings Tracker",
     "Tracks Medicare Advantage Star ratings and their revenue impact.",
     ["What are the Star ratings?", "How do they affect revenue?", "Where's "
      "the bonus risk?",
      "Which Star year and CMS methodology is the page on, and how is bonus impact computed (QBP + rebate share)?",
      "How does /ma-star differ from /diligence/payer-stress and /payer-intelligence?"],
     ["Star rating", "Bonus impact"], [],
     "Star ratings drive MA bonus payments and plan competitiveness.", "user"),
    ("/esg-impact", "ESG / Impact Reporting Tracker",
     "Tracks ESG / impact metrics and reporting commitments over time.",
     ["What ESG do we report?", "Are we hitting commitments?", "What's due "
      "to LPs?",
      "Is the commitment tracker persisted, and does the page diff current vs prior period for trend?",
      "How does /esg-impact differ from /esg-dashboard and /lp-reporting?"],
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
      "How do I build a packet?",
      "How fresh is a deal's packet, and what triggers a rebuild vs a cache read?",
      "How does /analysis differ from /models/<type>/<deal_id> and /diligence?"],
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
      "outcomes?", "How confident are the predictions?",
      "How is the universe filtered (year, geography, bed band) before training, and is the page deterministic across reloads?",
      "How does /ml-insights differ from /quant-lab and /model-validation?"],
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
      "predictions calibrated?",
      "How is the CV split done (random, time-aware, group-aware), and how is calibration measured (reliability diagram, Brier)?",
      "How does /model-validation differ from /models/quality, /models/validate, and /ml-insights?"],
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
      "plan?",
      "How is initiative impact attributed — claimed by initiative, normalized for overlap, or simple sum?",
      "How does /value-creation differ from /value-tracker and /value-creation-plan?"],
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
      "is the return?",
      "What sensitivity ranges does the page show by default, and where can I override the bands?",
      "How does /underwriting differ from /underwriting-model and /lbo-stress?"],
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
      "is this scenario?",
      "What input distributions and correlation structure does the page assume, and is the seed deterministic?",
      "How does /scenario-mc differ from /portfolio/monte-carlo, /scenarios, and /pressure?"],
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
      "still open?",
      "Which packet findings drive the synthesis, and how does the page flag a gap (missing data vs unresolved opinion)?",
      "How does /diligence/synthesis differ from /diligence/ic-memo and /diligence/ic-packet?"],
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
      "sector?", "How do they perform?",
      "What fraction of this sponsor's deals are in the corpus, and how many are realized vs unrealized?",
      "How does /diligence/sponsor-detail differ from /gp-benchmarking, /sponsor-league, and /sponsor-heatmap?"],
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
      "should we watch?",
      "How current is the rulemaking feed, and which sources (Federal Register, CMS, state) are wired in?",
      "How does /diligence/regulatory-calendar differ from /diligence/payer-stress and /industry?"],
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
     ["What's left to diligence?", "What's blocked?", "Who owns what?",
      "Is the checklist state persisted across sessions, and where are partner overrides logged?",
      "How does /diligence-checklist (this route alias) differ from /diligence/checklist?"],
     ["Items complete", "By status"], [], ["checklist_state"],
     "Tracks entered checklist items through status/owner; reflects what the "
     "team has populated.",
     "A live checklist is how a deal team avoids diligence gaps.",
     _DC.MIXED, "deal"),
    ("/diligence/ic-memo", "Diligence IC Memo",
     PageContextCategory.DILIGENCE_WORKSPACE,
     "IC memo view within the diligence workspace for a deal.",
     ["Show the IC memo", "What's the recommendation?", "What's missing?",
      "How are 'missing' items detected — required packet sections, blocked checklist P0s, or both?",
      "How does /diligence/ic-memo differ from /ic-memo, /ic-memo-gen, and /diligence/ic-packet?"],
     ["MOIC", "IRR"], ["moic", "irr"], ["analysis_run"],
     "Renders the deal's IC memo from its packet; surfaces gaps honestly.",
     "The IC memo is where the diligence lands as a decision.",
     _DC.MIXED, "deal"),
    ("/calibration", "Prior Calibration",
     PageContextCategory.LIBRARY_REFERENCE,
     "Per-payer prior-calibration view — the Bayesian priors the models shrink "
     "thin data toward.",
     ["What priors does the model use?", "How are priors calibrated?", "Why "
      "this prior for this payer?",
      "How much does each payer's prior shrink thin data — what's the effective sample-size weight?",
      "How does /calibration differ from /models/quality and /corpus-coverage?"],
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
      "cuts compare?",
      "This route is a legacy alias that redirects to /deal-corpus-analytics — should I use the canonical one?",
      "How does /portfolio-analytics differ from /portfolio and /deal-corpus-analytics?"],
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
      "are behind?",
      "Is the variance shown vs the original entry plan, the most recent re-plan, or against a peer benchmark?",
      "How does /variance differ from /value-tracker and /portfolio/risk-scan?"],
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
     ["How do I change settings?",
      "Where are my preferences?",
      "Where do I configure auth / users?",
      "How do I switch between Chartis and PE Partner mode?",
      "Where do I enable the Ollama Guide?"]),
    ("/settings/ai", _SYS, "AI / Guide settings — controls for the local "
     "Ollama Guide and RAG (enable, model, index).",
     ["How do I configure the Guide?",
      "Which model does the assistant use?",
      "How do I rebuild the RAG index?",
      "What's the difference between enabling and the inline-question flow?",
      "Where does the Ollama runtime live (local, Tailscale)?"]),
    ("/settings/workspace", _SYS, "Workspace-mode settings — switch between PE "
     "Partner and Chartis Consulting interface modes.",
     ["How do I switch workspace mode?",
      "What does PE Partner mode change?",
      "What does Chartis Consulting mode change?",
      "Are saved deals shared between modes?",
      "Does mode affect available routes?"]),
    ("/jobs", _SYS, "Background job queue — status of queued/running simulation "
     "and analysis jobs.",
     ["What jobs are running?",
      "Did my simulation finish?",
      "How long does a typical Monte-Carlo job take?",
      "What happens to in-flight jobs on server restart?",
      "Where are job logs and output?"]),
    ("/runs", _SYS, "Simulation run history — past Monte-Carlo / analysis runs "
     "with parameters and results.",
     ["What runs have I done?",
      "Can I re-open a past run?",
      "How are runs different from /jobs (background queue)?",
      "Where do run inputs / outputs live?",
      "Can I clone and rerun with tweaked parameters?"]),
    ("/cli-runs", _SYS, "CLI run history — records of analyses launched via the "
     "rcm-mc command line.",
     ["What CLI runs happened?",
      "What did the cron jobs do?",
      "How does this differ from /jobs (web-triggered runs)?",
      "Where does the run history get persisted?",
      "Can I re-launch a past CLI run from this page?"]),
    ("/ops", _SYS, "Operations / system status surface for the deployment.",
     ["Is the system healthy?",
      "What's the operational status?",
      "How many deals / snapshots are in the store right now?",
      "What's the DB size on disk?",
      "Is auth enabled in this deployment?"]),
    ("/outputs", _SYS, "Generated outputs index — exports, reports, and "
     "artifacts produced by the app.",
     ["Where are my exports?",
      "What outputs were generated?",
      "How do I re-download an artifact?",
      "How long are outputs retained?",
      "What output formats are supported (PDF, CSV, JSON)?"]),
    ("/search", _HOME, "Global search across deals, hospitals, and routes.",
     ["How do I search?",
      "Where do I find a deal/hospital?",
      "What entities are searchable?",
      "How does this differ from /global-search and /deal-search?",
      "Does search support fuzzy matching?"]),
    ("/global-search", _HOME, "Global search results across the app's "
     "entities and surfaces.",
     ["Search everything",
      "Find a deal or page",
      "What entities are searchable — deals, hospitals, sponsors?",
      "How does this differ from /search and /deal-search?",
      "Can I search inside uploaded documents?"]),
    ("/query", _SYS, "Ad-hoc query tool over the app's data.",
     ["How do I query the data?",
      "Can I run a custom query?",
      "What's the query DSL syntax (denial_rate > 15, days_in_ar < 50)?",
      "Which deal fields are queryable?",
      "How does this differ from /search and /deal-search?"]),
    ("/admin/audit-chain", _SYS, "Audit-log chain — the tamper-evident record "
     "of state-changing actions.",
     ["What changed and who did it?",
      "Is the audit chain intact?",
      "How is tamper-evidence implemented — hash chain, signatures?",
      "What gets logged vs not logged?",
      "How does this differ from /audit?"]),
    ("/v3-status", _SYS, "Build / phase status page (v3 milestone tracking).",
     ["What's the v3 status?",
      "What shipped in this phase?",
      "What is the v3 migration in PE Desk's history?",
      "Is this an internal dev page or partner-facing?",
      "How does v3 status differ from v5 status?"]),
    ("/v5-status", _SYS, "Build / phase status page (v5 milestone tracking).",
     ["What's the v5 status?",
      "What shipped in this phase?",
      "What is the v5 migration in PE Desk's history?",
      "Is this an internal dev page or partner-facing?",
      "Where can I see overall completion progress?"]),
    ("/guide/context-debug", _SYS, "Debug view of the Guide's own page-context "
     "packet for a route — what the assistant knows about a page.",
     ["What context does the Guide have for this page?",
      "Why did the Guide answer that way?",
      "Where does each field come from — manual_page_contexts.py or auto-discovered?",
      "Which metrics and data sources are linked to this page?",
      "Why is some context missing — INFERRED_FROM_PAGE vs DOCUMENTED?"]),
    ("/team", _HOME, "Team dashboard — members, ownership, and activity.",
     ["Who's on the team?",
      "Who owns which deals?",
      "What activity has the team logged?",
      "How do I add a team member?",
      "Where can I see per-owner deal load?"]),
    ("/news", _HOME, "Healthcare-PE news feed relevant to the portfolio and "
     "pipeline.",
     ["What's new?",
      "Any relevant news?",
      "How is the news feed filtered — sector, sponsor, deal?",
      "Where do the news items come from?",
      "How fresh is the feed — minutes, hours, days?"]),
    ("/insights", _HOME, "Insights feed — surfaced highlights across the "
     "portfolio and universe.",
     ["What should I look at?",
      "Any notable insights?",
      "What detectors fire into this feed?",
      "How is 'priority' ordered across insights?",
      "How does this differ from /alerts?"]),
    ("/new-deal", PageContextCategory.PIPELINE_SOURCING,
     "New-deal entry — create a deal in the pipeline (manual or import).",
     ["How do I add a deal?",
      "How do I import a deal?",
      "What's the difference between /new-deal and /new-deal/manual?",
      "Can I bulk-import many deals at once?",
      "Which fields are required vs prior-filled?"]),
    ("/market-data/map", PageContextCategory.RESEARCH_BACKTESTING,
     "Geographic market-data map — public market indicators by location.",
     ["What's the geographic picture?",
      "How do markets compare on the map?",
      "Which public market indicators can be plotted?",
      "How does this differ from /geo-map and /market-intel/geo?",
      "What's the underlying data refresh cadence?"]),
    ("/market-intel/seeking-alpha", PageContextCategory.RESEARCH_BACKTESTING,
     "Market-intelligence reading view (Seeking-Alpha-style) over licensed "
     "research exports.",
     ["What's the market view?", "What does the research say?"]),
    ("/fund-learning", _HOME, "Fund-learning / day-one playbook surface — "
     "lessons and standard plays for new holdings.",
     ["What's the day-one playbook?",
      "What have we learned across deals?",
      "Which standard plays have the highest realization rate?",
      "How does this differ from /diligence/pe-reference (codified knowledge)?",
      "How are lessons captured into the playbook?"]),
]
# Sibling routes per system/admin/home surface — keeps the Guide's "see also"
# suggestion useful instead of dead-ending on these utility pages. Picked from
# the natural workflow neighbours (settings family, status pages, search peers,
# admin / audit family, etc.). Falls back to /tools + /app for any surface not
# listed.
_BATCH8_SIBLINGS = {
    "/settings": ["/settings/ai", "/settings/workspace", "/users", "/audit"],
    "/settings/ai": ["/settings", "/settings/workspace", "/guide/context-debug"],
    "/settings/workspace": ["/settings", "/settings/ai"],
    "/jobs": ["/runs", "/cli-runs", "/ops", "/outputs"],
    "/runs": ["/jobs", "/cli-runs", "/outputs"],
    "/cli-runs": ["/jobs", "/runs", "/outputs"],
    "/ops": ["/jobs", "/admin/audit-chain", "/settings"],
    "/outputs": ["/runs", "/jobs", "/exports"],
    "/search": ["/global-search", "/deal-search", "/target-screener"],
    "/global-search": ["/search", "/deal-search"],
    "/query": ["/global-search", "/search", "/admin/audit-chain"],
    "/admin/audit-chain": ["/audit", "/users", "/ops", "/settings"],
    "/v3-status": ["/v5-status", "/ops", "/tools"],
    "/v5-status": ["/v3-status", "/ops", "/tools"],
    "/guide/context-debug": ["/settings/ai", "/module-index", "/tools"],
    "/team": ["/users", "/audit", "/app"],
    "/news": ["/insights", "/sector-momentum", "/portfolio"],
    "/insights": ["/news", "/alerts", "/portfolio"],
    "/new-deal": ["/pipeline", "/import", "/target-screener"],
    "/market-data/map": ["/geo-map", "/market-intel/geo", "/geo-intel"],
    "/market-intel/seeking-alpha": ["/market-intel/geo", "/news", "/sector-momentum"],
    "/fund-learning": ["/diligence/pe-reference", "/portfolio", "/initiatives"],
}

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
        related_routes=_BATCH8_SIBLINGS.get(_r, ["/tools", "/app"]),
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=_DC.MIXED,
    ))


if "/ebitda-bridge" not in {c.route for c in _MANUAL}:
    _MANUAL.append(_ctx(
        "/ebitda-bridge", "EBITDA Bridge",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="Per-hospital 7-lever RCM EBITDA bridge with returns "
        "math — decomposes current → pro-forma EBITDA lever by lever and runs "
        "the MOIC/IRR. Parameterized: /ebitda-bridge/<ccn>.",
        primary_purpose="Show exactly how revenue-cycle improvement converts to "
        "EBITDA (and therefore returns) for a specific hospital, lever by lever, "
        "so the value-creation thesis is concrete and auditable.",
        intended_users=["Deal team underwriting an RCM value-creation thesis."],
        common_questions=[
            "How does RCM improvement bridge to EBITDA here?",
            "Which lever contributes the most?",
            "What MOIC/IRR does this bridge imply?",
            "How were the lever targets set?",
            "How does /ebitda-bridge differ from /models/bridge and /diligence/value?"],
        inputs=["The hospital's CMS HCRIS data (by CCN in the URL) plus "
                "RCM benchmark targets / any data-room overrides."],
        outputs=["A 7-lever bridge (denial rate, days in AR, clean-claim, "
                 "underpayments, cost, working capital, …) from current to "
                 "pro-forma EBITDA, a ramp curve, peer targets, and a "
                 "MOIC/IRR returns grid."],
        key_metrics=["EBITDA", "EBITDA bridge", "RCM uplift", "MOIC", "IRR",
                     "EV/EBITDA"],
        data_sources=["CMS HCRIS for the hospital + RCM benchmark targets; "
                      "optional data-room overrides."],
        model_logic_summary=(
            "Builds the bridge in rcm_mc/ui/ebitda_bridge_page (_compute_bridge) "
            "+ rcm_mc/pe/rcm_ebitda_bridge: each lever's EBITDA impact = the "
            "KPI gap to a peer/benchmark target × the revenue or cost at risk; "
            "the levers sum onto current EBITDA to a pro-forma figure, which "
            "feeds a standard LBO returns grid. Lever targets are benchmark-"
            "driven assumptions, not realized results."),
        why_it_matters="The bridge is where an RCM thesis becomes a number — it "
        "makes the EBITDA (and return) case explicit and challengeable.",
        diligence_use_cases=[
            "Underwriting the RCM value-creation case for a target hospital.",
            "Pressure-testing which levers actually move EBITDA."],
        interpretation_guidance=[
            "Lever impacts are MODEL ESTIMATES from benchmark gaps × revenue at "
            "risk — assumptions, not realized EBITDA.",
            "Requires a hospital CCN (/ebitda-bridge/<ccn>); the bare route has "
            "no hospital context.",
            "The returns grid inherits the bridge's assumptions — read them "
            "before quoting a MOIC/IRR."],
        limitations=[
            "Only as good as the HCRIS data and the benchmark targets; "
            "hospital-specific reality can differ.",
            "Per-hospital model output, not an audited financial statement."],
        related_routes=["/models/bridge", "/rcm-benchmarks", "/diligence/xray",
                        "/quant-lab"],
        metric_ids=["ebitda", "ebitda_bridge", "rcm_uplift", "moic", "irr",
                    "ev_to_ebitda"],
        data_source_ids=["cms_hcris", "benchmark_prior"],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
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
                          "returns?", "Where do they diverge?",
                          "How are the columns sorted, and can I pin a baseline deal for relative deltas?",
                          "How does /compare differ from /diligence/compare and /similar-deals?"],
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
    # ── 2026-05-31 extension: pages with an illustrative scaffold + a
    #    named real public-data anchor. The data_source_id resolves to the
    #    anchor source (cadence/limits/provenance), not the scaffold. ──
    "/aco-economics": ["cms_mssp_aco"],
    "/cin-analyzer": ["cms_mssp_aco"],
    "/antitrust-screener": ["cms_chow"],
    "/msa-concentration": ["cms_chow"],
    "/clinical-outcomes": ["cms_care_compare"],
    "/quality-scorecard": ["cms_care_compare"],
    "/provider-retention": ["cms_care_compare"],
    "/gpo-supply": ["cms_open_payments"],
    "/health-equity": ["cdc_places"],
    "/telehealth-econ": ["cdc_places"],
    "/locum-tracker": ["hrsa_hpsa"],
    "/workforce-retention": ["hrsa_hpsa"],
    "/physician-productivity": ["hrsa_hpsa"],
    "/ma-contracts": ["cms_ma_geo"],
    "/ma-star": ["cms_ma_geo"],
    "/payer-concentration": ["cms_ma_geo"],
    "/nsa-tracker": ["civhc_rbp"],
    "/payer-contracts": ["civhc_rbp"],
    "/payer-shift": ["civhc_rbp"],
    "/market-intel/geo": ["cms_ffs_provider_enrollment"],
    "/provider-network": ["cms_ffs_provider_enrollment"],
    "/patient-experience": ["cms_hcahps"],
    "/supply-chain": ["openfda_drug_shortages"],
    "/target-screener": ["cms_hcris"],
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


# ── why_it_matters completion ──────────────────────────────────────────
# `why_it_matters` IS sent to the model, so a placeholder degrades answers.
# Fill every page still on the default with honest value-framing derived from
# what the page does (general PE/diligence rationale — no fabricated internals).
_WHY_PATCHES: Dict[str, str] = {
    "/aco-economics": "ACO shared-savings economics can make or break a value-based-care thesis — sizing them early frames the deal.",
    "/acq-timing": "Entry timing materially moves returns; testing it avoids overpaying at a cycle peak.",
    "/activity": "A clean activity trail keeps the deal team coordinated and the audit history intact.",
    "/antitrust-screener": "Market-overlap/HSR risk can block or delay a deal — screening it early avoids a late surprise.",
    "/bolton-analyzer": "Multiple-arbitrage accretion from bolt-ons is the core of a roll-up thesis; quantifying it tests the plan.",
    "/cap-structure": "Capital structure sets both the return amplification and the downside risk of the deal.",
    "/capital-efficiency": "Return per dollar invested — not just gross return — is what compounds a fund.",
    "/cin-analyzer": "CIN shared-savings/quality economics drive value-based upside for clinically-integrated networks.",
    "/clinical-outcomes": "Outcomes increasingly tie to reimbursement and exit attractiveness, not just quality.",
    "/cohorts": "Slicing deals into cohorts surfaces patterns a deal-by-deal view hides.",
    "/covenant-headroom": "Covenant headroom is the early-warning line between a healthy deal and a restructuring.",
    "/covenant-monitor": "Catching a covenant drift before a breach is the difference between a fixable problem and a crisis.",
    "/data": "Knowing exactly which public datasets feed the platform is the basis for trusting any analysis built on them.",
    "/data-intelligence": "Transparency about the real data sources behind the analytics is what makes them defensible.",
    "/data-room": "A well-organized data room is the backbone of efficient, auditable diligence.",
    "/deadlines": "Missed deal deadlines (exclusivity, financing, regulatory) can kill or reprice a transaction.",
    "/deal-pipeline": "A disciplined, staged pipeline is how a thesis-driven sourcing effort actually converts.",
    "/deal-postmortem": "Learning from realized outcomes turns a track record into a repeatable playbook.",
    "/deal-quality": "A consistent quality grade keeps scarce diligence attention on the best opportunities.",
    "/deal-risk-scores": "Comparable risk scoring lets the team triage where to spend diligence effort.",
    "/deal-search": "Fast retrieval across the live deal book keeps the team working from current truth.",
    "/deals": "The deal book is the single source of truth the whole workflow runs on.",
    "/diligence/checklist": "A live checklist is how a deal team avoids diligence gaps under time pressure.",
    "/diligence/ic-packet": "A consistent, packet-backed IC memo speeds and de-risks the investment decision.",
    "/diligence/ingest": "Clean ingestion of a deal's documents/financials is the foundation every later analysis depends on.",
    "/diligence/questions": "A tracked open-questions list prevents diligence items from slipping before IC.",
    "/drug-shortage": "Active drug shortages directly affect provider operations, cost, and continuity of care.",
    "/engagements": "Tracking operating/consulting engagements keeps value-creation work accountable to the thesis.",
    "/escalations": "Surfacing escalated issues across the book ensures the most urgent problems get partner attention.",
    "/exports": "Reliable, repeatable exports are what get analysis in front of IC and LPs.",
    "/gpo-supply": "Group-purchasing/supply savings are a concrete, near-term margin lever in provider deals.",
    "/health-equity": "Health-equity (HEI) performance increasingly affects Star bonuses and payer/LP expectations.",
    "/initiatives": "Tracked value-creation initiatives are where the return thesis becomes realized EBITDA.",
    "/locum-tracker": "Locum/agency spend is a fast-moving cost line that erodes provider margin if unmanaged.",
    "/ma-contracts": "Medicare Advantage contract economics drive a large and growing share of provider revenue.",
    "/medicaid-unwinding": "Medicaid redetermination shifts payer mix and volume — a near-term revenue risk to size.",
    "/methodology": "Transparent methodology is what lets a partner trust and defend the platform's outputs.",
    "/methodology/calculations": "Documented calculations let the team and IC challenge any number on its merits.",
    "/module-index": "A navigable index keeps a large analytic toolkit usable rather than overwhelming.",
    "/msa-concentration": "Market concentration shapes pricing power, antitrust risk, and roll-up runway.",
    "/notes": "Searchable, shared deal notes preserve institutional memory across the team.",
    "/nsa-tracker": "No Surprises Act / out-of-network dynamics directly affect provider reimbursement and risk.",
    "/owners": "Clear deal ownership keeps accountability unambiguous across the portfolio.",
    "/patient-experience": "Patient-experience scores tie to reimbursement, reputation, and volume retention.",
    "/payer-concentration": "Payer concentration is a core revenue-durability risk — one contract loss can reprice a deal.",
    "/payer-contracts": "Payer contracts are the single biggest determinant of provider revenue and margin.",
    "/payer-rate-trends": "Payer rate trends signal where reimbursement — and therefore revenue — is heading.",
    "/payer-shift": "Shifts in payer mix move margin materially because payers reimburse very differently.",
    "/physician-productivity": "Provider productivity drives both revenue capacity and compensation cost.",
    "/pipeline": "The staged pipeline is how sourcing discipline turns into closed deals.",
    "/pipeline/bridge": "Jumping straight from a pipeline deal to its EBITDA bridge keeps underwriting fast and grounded.",
    "/provider-network": "Network/payer concentration shapes negotiating leverage and revenue risk.",
    "/provider-retention": "Provider churn is a first-order risk in provider deals — losing providers loses revenue.",
    "/quality-scorecard": "Quality increasingly converts to reimbursement and exit multiple, not just compliance.",
    "/ref-pricing": "Reimbursement as a % of Medicare benchmarks a provider's true pricing power.",
    "/regulatory-risk": "A single rule change can erase a thesis — sizing regulatory exposure is risk management.",
    "/risk-adjustment": "Risk-adjustment (RAF) coding drives Medicare Advantage revenue and audit exposure.",
    "/screening": "Disciplined screening focuses scarce diligence capacity on the targets that fit the thesis.",
    "/screening/dashboard": "A funnel view keeps the sourcing-to-shortlist process measurable and honest.",
    "/supply-chain": "Supply-cost savings are a concrete, controllable margin lever in provider businesses.",
    "/telehealth-econ": "Telehealth economics affect access, cost, and the durability of visit volume.",
    "/verticals": "Each healthcare vertical has distinct economics; grouping them keeps comparisons honest.",
    "/watchlist": "A watchlist keeps the deals that matter most in front of the team without noise.",
    "/workforce-retention": "Workforce turnover is a major hidden cost and operational risk in labor-intensive providers.",
}
_NEEDS_WHY = "Needs source documentation."
for _c in _MANUAL:
    _w = _WHY_PATCHES.get(_c.route)
    if _w and isinstance(_c.why_it_matters, str) and _NEEDS_WHY in _c.why_it_matters:
        _c.why_it_matters = _w

# /tools is a real, served page (the Cmd-K / all-tools index) that was never
# mapped — add it so the Guide can explain it and cross-links to it resolve.
if "/tools" not in {c.route for c in _MANUAL}:
    _MANUAL.append(_ctx(
        "/tools", "All Tools",
        category=PageContextCategory.HOME_OPERATIONS,
        short_description="The full, searchable index of every PEdesk tool / "
        "analytic surface (the Cmd-K command palette opens the same set).",
        primary_purpose="Let a partner jump straight to any surface without "
        "trawling URLs — the catalog of everything the platform can do.",
        common_questions=["What tools are available?", "Where do I find X?",
                          "How do I open the command palette?",
                          "What does each honesty-circle color (GREEN / NAVY / "
                          "DATA_REQUIRED / RED) mean on this page?",
                          "How does /tools differ from /best/<section> and the top-nav rails?"],
        inputs=["The platform's registered surfaces / command-palette modules."],
        outputs=["A grouped, searchable list of tools with links."],
        key_metrics=[],
        data_sources=["Application surface registry (not an analytic dataset)."],
        model_logic_summary="A navigation index over the registered surfaces; "
        "not an analytic model — no computed figures.",
        why_it_matters="Discoverability — a large toolkit is only useful if you "
        "can find the right surface fast.",
        diligence_use_cases=["Finding the right analytic surface for the "
                            "question at hand."],
        interpretation_guidance=["This is a navigation surface, not an analytic "
                                "output — nothing here is a diligence finding."],
        limitations=["Lists what's registered; not an analytic dataset."],
        related_routes=["/app", "/diligence", "/module-index"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ))

# ── Guide-blindness backfill (2026-05-27) ─────────────────────────────────
# Live /tools pages that had NO page context — the Guide was blind on them.
# Grounded in each page's own module docstring + render (no fabricated data).
_GUIDE_BACKFILL = [
    _ctx(
        "/data-activation", "Data Activation Center",
        category=PageContextCategory.HOME_OPERATIONS,
        short_description="One hub that surfaces every DATA-REQUIRED analysis — "
        "what to upload to activate each one.",
        primary_purpose="Show the partner exactly which analyses need their own "
        "deal/fund data and how to turn each on (upload + template), so no "
        "data-gated surface is left dark.",
        common_questions=[
            "What do I need to upload?",
            "Which analyses aren't active yet?",
            "How many surfaces become active once I upload claims data?",
            "Where do I download the import templates?",
            "Who typically owns each piece of data I need to request?",
        ],
        inputs=["The DATA_REQUIRED PageContext registry; activation "
                "state per page."],
        outputs=["A catalog of data-required surfaces with the input each needs."],
        key_metrics=[
            "Total DR surfaces", "Activated count", "Outstanding requests",
        ],
        diligence_use_cases=[
            "Building the P0 data-request list at the start of a "
            "diligence engagement.",
        ],
        data_sources=["Your uploaded deal/fund data (none is "
                      "fabricated — surfaces stay inert until fed)."],
        why_it_matters="A data-gated tool is useless if you don't know what it "
        "wants — this removes that friction.",
        interpretation_guidance=[
            "This is an index, not an analysis — clicking through to "
            "each entry takes you to the page that needs that upload.",
            "If a category here is empty, every page in that category "
            "is already activated for your workspace."],
        limitations=["A directory of what-to-upload, not an analysis itself."],
        model_logic_summary=(
            "No model — enumerates every DATA_REQUIRED PageContext in "
            "the registry, groups them by the upload type each needs, "
            "and surfaces the import-template filename. The page "
            "doesn't ingest data itself; it tells the partner what to "
            "feed the downstream surfaces."),
        related_routes=["/tools", "/diligence/ingest"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.USER_ENTERED_DATA,
    ),
    _ctx(
        "/diligence/cliff-calendar", "Reimbursement Cliff Calendar",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="The 2026–2029 reimbursement-cliff calendar — dated "
        "regulatory/payment events that can step a target's revenue down.",
        primary_purpose="Put the known reimbursement cliffs (340B, IRF, payer "
        "rate resets, sequestration, etc.) on a timeline against the hold so a "
        "thesis isn't blindsided by a scheduled rate cut.",
        common_questions=[
            "What reimbursement cliffs hit during the hold?",
            "When does the next rate reset land?",
            "Which cliffs affect 340B / IRF / sequestration?",
            "How does a sponsored payer-rate reset translate to revenue?",
            "How does this differ from /diligence/regulatory-calendar?",
        ],
        inputs=["The pe_intelligence reimbursement-cliff library "
                "(curated regulatory schedule); deal hold-period "
                "filter."],
        outputs=["A dated calendar of reimbursement-affecting events with "
                 "magnitude/impact notes."],
        key_metrics=[],
        diligence_use_cases=["Mapping known regulatory rate-cuts "
                             "against the deal's hold window to "
                             "frame underwriting risk."],
        data_sources=["pe_intelligence reimbursement-cliff "
                                      "calendar (public regulatory schedule)."],
        why_it_matters="Entry/exit timing and underwriting both move on when a "
        "revenue cliff lands relative to the hold.",
        interpretation_guidance=[
            "Cliffs are scheduled events; the magnitude shown is "
            "generic — the deal-specific dollar impact depends on "
            "the target's payer mix and revenue base.",
            "An event slipping or being deferred is common — pair "
            "with /diligence/regulatory-calendar for live rulemaking."],
        limitations=["A calendar of scheduled events; the dollar impact on a "
                     "specific target still needs the deal's payer mix."],
        model_logic_summary=(
            "No model — surfaces the curated cliff schedule from "
            "pe_intelligence's reimbursement-cliff library, plots each "
            "event on a timeline, and tags magnitude bands. The "
            "Guide can answer when each cliff hits and the headline "
            "impact category; deal-specific dollar conversion happens "
            "downstream in the bridge."),
        related_routes=["/diligence/regulatory-calendar", "/diligence"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/diligence/pe-library", "PE Intelligence Library",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="The searchable catalog of the pe_intelligence analytic "
        "toolkit (~222 modules).",
        primary_purpose="Let a partner find and open the right PE-intelligence "
        "analytic among the full toolkit, rather than only the handful wired "
        "into the nav.",
        common_questions=[
            "What PE-intelligence tools exist?",
            "Is there a tool for X?",
            "How many modules are in the catalog (~222)?",
            "How do I run a tool on the active deal?",
            "What's the difference between /pe-library and /pe-tool?",
        ],
        inputs=["The pe_intelligence module registry; search query."],
        outputs=["A grouped, searchable index of the toolkit's modules."],
        key_metrics=[],
        diligence_use_cases=["Finding the right pe_intelligence "
                             "analytic for a specific diligence "
                             "question."],
        data_sources=["The pe_intelligence module registry "
                                      "(a catalog, not a dataset)."],
        why_it_matters="A 222-tool toolkit is only useful if you can find the "
        "right analytic fast.",
        interpretation_guidance=[
            "Library is a catalog — open a module via /diligence/pe-tool "
            "to run it against the active deal's packet.",
            "Module groupings reflect the toolkit's authored taxonomy, "
            "not a curation judgment of which tools matter most."],
        limitations=["A catalog/navigation surface — not an analytic output."],
        model_logic_summary=(
            "No model — enumerates the ~222 modules in the "
            "pe_intelligence module registry, groups them by "
            "category and tag, and supports text search across "
            "module names and docstrings. Each result links to "
            "/diligence/pe-tool to execute against the active deal."),
        related_routes=["/diligence/pe-tool", "/diligence/pe-reference",
                        "/diligence"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.MIXED,
    ),
    _ctx(
        "/diligence/pe-reference", "PE Intelligence Reference",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="The deal-independent curated-knowledge libraries from "
        "the pe_intelligence toolkit (playbooks, partner traps, reference sets).",
        primary_purpose="Surface the static reference knowledge — the things "
        "true regardless of a specific deal — so the team can consult vetted "
        "playbooks and watch-outs.",
        common_questions=[
            "What are the known partner traps here?",
            "Is there a playbook for this situation?",
            "Which reference libraries are deal-independent?",
            "How does this differ from /diligence/pe-library?",
            "Where do the curated playbooks come from?",
        ],
        inputs=["The pe_intelligence reference libraries; topic "
                "filter (playbook / partner-trap / reference set)."],
        outputs=["Curated reference libraries (read-only knowledge)."],
        key_metrics=[],
        diligence_use_cases=["Consulting house-codified playbooks "
                             "and traps before applying a "
                             "deal-specific tool."],
        data_sources=["pe_intelligence curated reference "
                                      "libraries (editorial knowledge)."],
        why_it_matters="Codified house knowledge keeps diligence consistent and "
        "stops repeated mistakes.",
        interpretation_guidance=[
            "Reference knowledge — true regardless of the active deal; "
            "for deal-specific analytics, run the same module via "
            "/diligence/pe-tool against the packet.",
            "Playbook/trap entries are editorial — partner judgment "
            "still applies to which apply to this target."],
        limitations=["Reference knowledge, not deal-specific computed output."],
        model_logic_summary=(
            "No model — surfaces the curated reference libraries "
            "marked deal-independent in pe_intelligence (playbooks, "
            "partner-trap catalogs, reference taxonomies). Content "
            "is read-only editorial knowledge curated upstream; the "
            "page does no computation, just retrieval and rendering."),
        related_routes=["/diligence/pe-library", "/diligence/pe-tool"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/diligence/pe-tool", "PE Intelligence Tool Runner",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        short_description="Runs a chosen pe_intelligence analytic against a real "
        "deal's analysis packet.",
        primary_purpose="Execute any toolkit analytic on the active deal's data "
        "(not a sample), so the output reflects this target.",
        common_questions=[
            "Run tool X on this deal.",
            "What does this analytic say for my target?",
            "Why is the output dependent on packet completeness?",
            "How do I switch which tool runs against the active deal?",
            "Where do I see the underlying packet feeding the tool?",
        ],
        inputs=["The selected pe_intelligence module's identifier; "
                "the active deal's analysis packet."],
        outputs=["The selected analytic's output computed on the deal packet."],
        key_metrics=[],
        diligence_use_cases=["Running any of the 222 pe_intelligence "
                             "modules against the active deal's real "
                             "data instead of a sample."],
        data_sources=["The deal's analysis packet (its real "
                                      "ingested/observed data)."],
        why_it_matters="Connects the broad toolkit to the deal in front of you "
        "— the analytic runs on real target data, not a demo.",
        interpretation_guidance=[
            "Output is computed on THIS deal's packet — re-run after "
            "uploading new data to refresh.",
            "If a tool errors or produces a blank result, the active "
            "deal's packet likely lacks a required input — check the "
            "checklist on /diligence/checklist."],
        limitations=["Output is only as good as the deal packet's completeness."],
        model_logic_summary=(
            "Imports the chosen pe_intelligence module dynamically, "
            "passes the active deal's analysis packet as input, and "
            "renders the module's returned dict/list/dataframe in "
            "the page. The page itself does no math — it's the "
            "runner shell; the math lives in the selected module."),
        related_routes=["/diligence/pe-library", "/diligence/deal"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.OBSERVED_TARGET_DATA,
    ),
    _ctx(
        "/geo-map", "Geo Map",
        category=PageContextCategory.RESEARCH_BACKTESTING,
        short_description="A US choropleth (real Albers-projected geographic "
        "map) of the Geographic Intelligence suite — all 50 states + DC shaded "
        "by a real metric.",
        primary_purpose="Give a national, at-a-glance read of where a chosen "
        "metric concentrates, then click a state for its full profile.",
        common_questions=[
            "Which states lead/lag on this metric?",
            "Where is demand/supply concentrated?",
            "Which metrics can I shade the map by?",
            "How is the Albers projection different from a standard mercator?",
            "Where do I click to see a state's full profile?",
        ],
        inputs=["?metric=<key> — one of the 15 registered geo metrics."],
        outputs=["A shaded national map; click-through to per-state profiles."],
        key_metrics=[],
        diligence_use_cases=["Spotting where a metric concentrates "
                             "geographically before drilling into "
                             "a specific state via /state-profile."],
        data_sources=["The shared geo metrics registry "
                                      "(real public CMS/Census-class data)."],
        why_it_matters="Geographic concentration drives sourcing and roll-up "
        "strategy — the map makes it legible fast.",
        interpretation_guidance=[
            "Map color encodes one chosen metric; lighter ≠ better "
            "or worse universally — direction depends on the metric "
            "(see /geo-metrics for each metric's polarity).",
            "States with no value on record render as a neutral shade, "
            "not as the lowest band — read /geo-metrics for coverage."],
        limitations=["A visualization layer; the metric definitions live in "
                     "the geo metrics reference."],
        model_logic_summary=(
            "Pulls the chosen metric from the shared geo-metric "
            "registry, joins to a state FIPS lookup, and renders an "
            "Albers-projected SVG choropleth shaded by metric value. "
            "Click-through routes to /state-profile?state=<code>. "
            "States with no value render neutral, not zero."),
        related_routes=["/geo-intel", "/geo-metrics", "/state-profile",
                        "/metro-markets"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/geo-metrics", "Geographic Intelligence — Metrics & Sources",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description="A transparency reference for the geo suite — every "
        "metric the state-analysis modes use, with its real source and coverage.",
        primary_purpose="Document, for each geo metric, exactly what it measures, "
        "where it comes from, and how complete the coverage is — so the maps and "
        "rankings are auditable, not black boxes.",
        common_questions=[
            "Where does this geo metric come from?",
            "What's the coverage/vintage of this data?",
            "Which metrics are CMS-sourced vs Census/ACS?",
            "How often does each dataset refresh?",
            "Is the coverage gap on this metric material for my thesis?",
        ],
        inputs=["The geo-metric registry; data_source_registry."],
        outputs=["A per-metric table: definition, source, coverage."],
        key_metrics=[],
        diligence_use_cases=["Citing a geographic claim — confirming "
                             "the source and coverage of a metric "
                             "before quoting it to IC."],
        data_sources=["The shared geo metrics registry and its "
                                      "underlying public datasets."],
        why_it_matters="Defensibility — a geographic claim is only usable if you "
        "can cite its source and coverage.",
        interpretation_guidance=[
            "Use this page when reading a /geo-map or a state ranking "
            "— it lets you confirm what the metric actually measures "
            "and which states report it.",
            "Coverage gaps on a metric mean the maps and rankings "
            "render '—' for those states; the gap is in the source, "
            "not in PEdesk's computation."],
        limitations=["A reference/transparency surface, not an analysis."],
        model_logic_summary=(
            "No model — reads the geo-metric registry (definitions + "
            "source IDs) and the data_source_registry (provenance + "
            "refresh cadence), joins them, and renders a per-metric "
            "transparency table. The page describes the data layer "
            "the maps/rankings use; it doesn't compute the metrics."),
        related_routes=["/geo-intel", "/geo-map", "/metro-markets",
                        "/methodology"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
    _ctx(
        "/metro-markets", "Metro Markets",
        category=PageContextCategory.RESEARCH_BACKTESTING,
        short_description="The CBSA (metro/micro) level of the Geographic "
        "Intelligence suite — ranks metro markets by a real metric.",
        primary_purpose="Drop below the state level to the metro market — where "
        "deals actually compete — and rank/compare CBSAs on a chosen metric.",
        common_questions=[
            "Which metros lead on this metric?",
            "How does this metro compare to peers?",
            "What's a CBSA and why is it the right unit?",
            "Which metrics can I rank by?",
            "How does this differ from /county-explorer?",
        ],
        inputs=["Chosen metric from the shared geo-metrics "
                "registry (the same registry as /state-rankings "
                "and /county-explorer).",
                "Optional state / CBSA-tier filter to scope the "
                "ranking."],
        outputs=["A ranked CBSA table on the selected metric."],
        key_metrics=["The selected geo metric, ranked across all "
                     "CBSAs (definitions live on /geo-metrics)."],
        diligence_use_cases=[
            "Identifying the strongest CBSAs for a roll-up thesis "
            "by ranking metros on a single market structure metric.",
            "Comparing a target's home CBSA against metro peers "
            "before sizing geographic expansion.",
        ],
        data_sources=["The shared geo metrics registry at the "
                      "CBSA level (real public data)."],
        why_it_matters="Healthcare markets are local — metro-level structure "
        "matters more than state averages for siting and roll-ups.",
        interpretation_guidance=[
            "CBSAs (Core Based Statistical Areas) are OMB-defined "
            "labor-market regions — closer to where a deal competes "
            "than a state line.",
            "Rural areas outside CBSA boundaries are not represented "
            "here; for non-metro reads use /state-rankings or "
            "/county-explorer."],
        limitations=["CBSA coverage depends on the underlying public dataset."],
        model_logic_summary=(
            "Joins the chosen metric to the CBSA crosswalk and "
            "ranks all CBSAs by metric value; sort direction is "
            "metric-aware (lower-is-better metrics flip). CBSAs "
            "with no value are listed unranked. The metric "
            "definitions and provenance live on /geo-metrics."),
        related_routes=["/geo-intel", "/geo-map", "/geo-metrics",
                        "/state-profile"],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ),
]
for _bf in _GUIDE_BACKFILL:
    if _bf.route not in {c.route for c in _MANUAL}:
        _MANUAL.append(_bf)

# CSV export endpoints (download the data behind a page). Light context so the
# Guide can explain what each is rather than being blind — they're exports,
# not analytic pages.
_CSV_EXPORTS = {
    "/target-screener.csv": ("Target Screener", "/target-screener"),
    "/county-explorer.csv": ("County Explorer", "/county-explorer"),
    "/metro-markets.csv": ("Metro Markets", "/metro-markets"),
    "/state-compare.csv": ("State Compare", "/state-compare"),
    "/state-peers.csv": ("State Peers", "/state-peers"),
    "/state-profile.csv": ("State Profile", "/state-profile"),
    "/state-rankings.csv": ("State Rankings", "/state-rankings"),
}
for _csv, (_parent_label, _parent_route) in _CSV_EXPORTS.items():
    if _csv in {c.route for c in _MANUAL}:
        continue
    _MANUAL.append(_ctx(
        _csv, f"{_parent_label} (CSV export)",
        category=PageContextCategory.LIBRARY_REFERENCE,
        short_description=f"A CSV download of the data shown on the "
        f"{_parent_label} page.",
        primary_purpose=f"Export the {_parent_label} dataset as CSV for offline "
        "analysis (Excel, a model, a memo appendix).",
        common_questions=["What's in this export?",
                          "How do I get this data into Excel?"],
        inputs=[
            f"None — the endpoint serializes the same rows {_parent_route} "
            "would render, using whatever filters / view state are set "
            "on the parent page.",
        ],
        outputs=["A CSV file of the parent page's rows."],
        key_metrics=[], data_sources=[f"The same data as the {_parent_label} "
                                      "page (real public/source data)."],
        diligence_use_cases=[
            f"Pulling the {_parent_label} rows into Excel / a model / "
            "a memo appendix for partner-side analysis.",
        ],
        why_it_matters="Lets the team take the data into their own tools.",
        # 2026-05-31: universal guidance for every CSV export endpoint —
        # the CSV is the raw data from the parent page; for the
        # interpreted view (units, what '—' means, ranking direction),
        # the partner must open the parent route.
        interpretation_guidance=[
            f"This is a CSV download — the interpreted view "
            f"(units, sort direction, what '—' means) lives on "
            f"{_parent_route}.",
            "CSV faithfully reflects whatever the parent page would "
            "render; column meaning matches the parent page's headers "
            "and tooltips.",
        ],
        # 2026-05-31: every CSV export shares the same model logic —
        # serialize the parent page's row set into CSV. No model, no
        # transformation; the columns and ordering match the parent.
        model_logic_summary=(
            f"No model — the endpoint serializes the same row set the "
            f"{_parent_label} page renders, in the same column order, "
            "as CSV. Filters and view state on the parent page carry "
            "through to the export."
        ),
        limitations=["A data export, not an analytic surface — open the parent "
                     "page for the interpreted view."],
        related_routes=[_parent_route],
        metric_ids=[], data_source_ids=[],
        source_confidence=SourceConfidence.DOCUMENTED,
        data_confidence=DataConfidence.PUBLIC_BENCHMARK_DATA,
    ))

# ── Geographic Intelligence data-source lineage ───────────────────────────
# The geo suite renders from a shared metric table (state_compare._METRICS)
# whose every metric carries a real public source — all 9 are registered. Link
# them so the Guide can answer "where does this come from / how fresh is it"
# with real cadence + limitations, instead of going source-blind. Verified
# against the page modules (no fabrication): state-mode pages + county-explorer
# use the full set; metro-markets uses CBSA + Census demographics.
_GEO_SOURCES_9 = [
    "chr_county_demographics", "cdc_places", "cms_hcahps", "cms_ma_geo",
    "cms_mssp_aco", "cms_ffs_provider_enrollment", "cms_chow", "hrsa_hpsa",
    "oig_leie",
]
_GEO_SOURCE_LINKS = {
    "/geo-intel": _GEO_SOURCES_9, "/geo-map": _GEO_SOURCES_9,
    "/geo-metrics": _GEO_SOURCES_9, "/state-compare": _GEO_SOURCES_9,
    "/state-peers": _GEO_SOURCES_9, "/state-profile": _GEO_SOURCES_9,
    "/state-rankings": _GEO_SOURCES_9, "/county-explorer": _GEO_SOURCES_9,
    "/metro-markets": ["cbsa_crosswalk", "chr_county_demographics"],
}
for _c in _MANUAL:
    _sids = _GEO_SOURCE_LINKS.get(_c.route)
    if _sids and not (getattr(_c, "data_source_ids", None) or []):
        _c.data_source_ids = list(_sids)

# ── Other public-data pages: source lineage (verified from each page's own
# ck_source_purpose declaration — no guessing) ────────────────────────────
_PUBLIC_SOURCE_LINKS = {
    "/payer-rate-trends": ["civhc_rbp"],   # CIVHC / CO APCD Cost of Care
    "/ref-pricing": ["civhc_rbp"],         # CIVHC / CO APCD reference pricing
    "/cms-data-browser": ["cms_provider_data_catalog"],
    "/cms-sources": ["cms_provider_data_catalog"],
    "/drug-shortage": ["openfda_drug_shortages"],   # openFDA (now registered)
    "/cms-apm": ["cms_cmmi_apm"],                    # CMMI (now registered)
}
for _c in _MANUAL:
    _sids = _PUBLIC_SOURCE_LINKS.get(_c.route)
    if _sids and not (getattr(_c, "data_source_ids", None) or []):
        _c.data_source_ids = list(_sids)

# ── Related-route hygiene ──────────────────────────────────────────────
# The Guide must never hand the user a cross-link that points nowhere. Repoint
# a few known-wrong/sub-action links to the right mapped page, normalize
# trailing slashes, and DROP any related_route that still doesn't resolve to a
# real context (better an honest shorter list than a dead pointer).
_RELATED_ROUTE_FIXES = {
    "/comps": "/deal-library/comps",
    "/upload": "/diligence/snapshot",
    "/new-deal/upload": "/diligence/snapshot",
    "/engagements/create": "/engagements",
    "/exports/lp-update": "/lp-update",
}
_known_routes_rr = {c.route for c in _MANUAL}
for _c in _MANUAL:
    if not _c.related_routes:
        continue
    _fixed: List[str] = []
    for _rr in _c.related_routes:
        if not _rr:
            continue
        _base = _rr.split("?")[0].rstrip("/") or "/"
        _base = _RELATED_ROUTE_FIXES.get(_base, _base)
        if _base in _known_routes_rr and _base != _c.route and _base not in _fixed:
            _fixed.append(_base)
    _c.related_routes = _fixed


MANUAL_PAGE_CONTEXTS: Dict[str, PageContext] = {c.route: c for c in _MANUAL}
