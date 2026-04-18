"""Partner Brain hub — /partner-brain.

Landing page for the PE-partner judgment layer. Groups the 275-module
``rcm_mc.pe_intelligence`` library into 18 partner-task categories
and shows a card per category. Phase 0 ships the hub + the core
``/partner-brain/review`` page; Phase 1 fills in the per-category
pages (each card below links to ``/partner-brain/<slug>`` which
returns a friendly "coming in Phase 1" notice until wired).
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Tuple

from rcm_mc.ui._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)


# ── Category inventory ─────────────────────────────────────────────
# Grouping from the plan at .claude/plans/sharded-floating-mitten.md.
# Counts mirror the audit of rcm_mc/pe_intelligence/ orphans.

_CATEGORIES: List[Dict[str, object]] = [
    {
        "slug": "review",
        "label": "Partner Review",
        "count": 31,
        "phase": "LIVE",
        "note": "Reasonableness bands + named heuristics + partner-voice narrative. Core reflex, always first.",
        "examples": "partner_review · reasonableness · heuristics · narrative · red_flags",
    },
    {
        "slug": "failures",
        "label": "Named Failures & Smell Tests",
        "count": 9,
        "phase": "LIVE",
        "note": "Fingerprint-matches against dated historical failures (MA unwind 2023, NSA 2022, PDGM 2020).",
        "examples": "denial_fix_pace_detector · medicare_advantage_bridge_trap · payer_renegotiation_timing_model · deal_smell_detectors",
    },
    {
        "slug": "ic-decision",
        "label": "IC Decision & Thesis Validation",
        "count": 11,
        "phase": "LIVE",
        "note": "One-page IC read: recommend / pass / price X, plus the three numbers behind the call.",
        "examples": "ic_decision_synthesizer · thesis_validator · red_team_review · ic_dialog_simulator · bear_book",
    },
    {
        "slug": "sniff",
        "label": "Sniff Test & Archetype",
        "count": 9,
        "phase": "LIVE",
        "note": "On-face scorecard run before the math — IRR, EV/revenue, MA bridges without a named contract.",
        "examples": "unrealistic_on_face_check · healthcare_thesis_archetype_recognizer · archetype_heuristic_router",
    },
    {
        "slug": "100-day",
        "label": "100-Day & Operational Readiness",
        "count": 11,
        "phase": "LIVE",
        "note": "Day-one action plan, post-close 90-day reality check, EHR transition risk, integration readiness.",
        "examples": "day_one_action_plan · post_close_90_day_reality_check · ehr_transition_risk_assessor",
    },
    {
        "slug": "regulatory",
        "label": "Regulatory Stress",
        "count": 17,
        "phase": "PHASE 1",
        "note": "Site-neutral, CMS rule cycle, state AG scrutiny, HSR/antitrust — with $-impact rollup.",
        "examples": "site_neutral_specific_impact_calculator · cms_rule_cycle_tracker · hsr_antitrust_healthcare_scanner",
    },
    {
        "slug": "wc",
        "label": "Working Capital & Cash",
        "count": 7,
        "phase": "PHASE 1",
        "note": "WC peg negotiation, cash-conversion drift detection, one-time vs recurring hygiene at the line-item level.",
        "examples": "working_capital_peg_negotiator · cash_conversion_drift_detector",
    },
    {
        "slug": "value",
        "label": "Valuation, Pricing & M&A Economics",
        "count": 27,
        "phase": "PHASE 1",
        "note": "Rollup arbitrage math, exit buyer list, banker pricing tension, secondary sale valuation.",
        "examples": "rollup_arbitrage_math · exit_buyer_short_list_builder · banker_partner_pricing_tension",
    },
    {
        "slug": "team",
        "label": "Management & Team",
        "count": 21,
        "phase": "PHASE 1",
        "note": "C-suite grading, physician retention stress, management forecast haircut.",
        "examples": "c_suite_team_grader · physician_retention_stress_model · management_forecast_haircut_applier",
    },
    {
        "slug": "synthesis",
        "label": "Synthesis & Analysis Tools",
        "count": 36,
        "phase": "PHASE 1",
        "note": "Scenario comparison, sensitivity grids, 6-dim concentration scan, platform-vs-addon classifier.",
        "examples": "scenario_comparison · sensitivity_grid · concentration_risk_multidim",
    },
    {
        "slug": "rcm-payer",
        "label": "RCM / Payer Mix / MA",
        "count": 19,
        "phase": "PHASE 1",
        "note": "VBC risk-share underwriting, MA star-rating revenue impact, full RCM lever cascade.",
        "examples": "vbc_risk_share_underwriter · ma_star_rating_revenue_impact · rcm_lever_cascade",
    },
    {
        "slug": "process",
        "label": "Deal Process & Diligence",
        "count": 17,
        "phase": "PHASE 1",
        "note": "Banker-narrative decoder, commercial due diligence, reverse diligence checklist, LOI drafter.",
        "examples": "banker_narrative_decoder · reverse_diligence_checklist · loi_drafter",
    },
    {
        "slug": "business-model",
        "label": "Business Model Decomposition",
        "count": 14,
        "phase": "PHASE 1",
        "note": "EBITDA quality, recurring-EBITDA line scrubber, service-line analysis, contract diligence.",
        "examples": "ebitda_quality · recurring_ebitda_line_scrubber · contract_diligence",
    },
    {
        "slug": "debt",
        "label": "Debt / Leverage / LBO",
        "count": 11,
        "phase": "PHASE 1",
        "note": "LBO stress scenarios, covenant package designer, debt capacity sizer.",
        "examples": "lbo_stress_scenarios · covenant_package_designer · debt_capacity_sizer",
    },
    {
        "slug": "lp-ops",
        "label": "Portfolio & LP Operations",
        "count": 9,
        "phase": "PHASE 1",
        "note": "LP quarterly-update composer, vintage return curves, fund-level aggregation.",
        "examples": "lp_quarterly_update_composer · vintage_return_curve",
    },
    {
        "slug": "opportunity",
        "label": "Opportunity & White Space",
        "count": 7,
        "phase": "PHASE 1",
        "note": "Outpatient migration cascades, growth-algorithm diagnostic, peer discovery.",
        "examples": "outpatient_migration_cascade · growth_algorithm_diagnostic",
    },
    {
        "slug": "hold",
        "label": "Syndication & Hold",
        "count": 7,
        "phase": "PHASE 1",
        "note": "Continuation-vehicle readiness, hold-period optimizer, earn-out designer.",
        "examples": "continuation_vehicle_readiness_scorer · hold_period_optimizer · earnout_design_advisor",
    },
    {
        "slug": "quality-esg",
        "label": "Quality / ESG / Post-mortem",
        "count": 6,
        "phase": "PHASE 1",
        "note": "Quality metrics, ESG screen, post-mortem learning loop.",
        "examples": "quality_metrics · esg_screen · post_mortem",
    },
    {
        "slug": "vcp",
        "label": "Value Creation Plan",
        "count": 3,
        "phase": "PHASE 1",
        "note": "3-year VCP with quarter-by-quarter lever sequencing; dependency-aware ordering.",
        "examples": "value_creation_plan_generator · value_creation_tracker",
    },
]


def _category_card(cat: Dict[str, object]) -> str:
    bg = P["panel"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]
    pos = P["positive"]
    warn = P["warning"]

    phase = str(cat["phase"])
    is_live = phase == "LIVE"
    phase_color = pos if is_live else warn
    count = int(cat["count"])  # type: ignore[arg-type]
    slug = str(cat["slug"])
    label = str(cat["label"])
    note = str(cat["note"])
    examples = str(cat["examples"])

    href = f"/partner-brain/{slug}"
    header_style = (
        f"display:flex;align-items:center;justify-content:space-between;"
        f"margin-bottom:8px;gap:8px"
    )
    phase_badge = (
        f'<span style="font-size:9px;font-family:JetBrains Mono,monospace;'
        f"color:{phase_color};border:1px solid {phase_color};padding:2px 6px;"
        f'letter-spacing:0.08em;border-radius:2px">{_html.escape(phase)}</span>'
    )
    count_badge = (
        f'<span style="font-size:10px;font-family:JetBrains Mono,monospace;'
        f'color:{text_dim};font-variant-numeric:tabular-nums">{count} module{"s" if count != 1 else ""}</span>'
    )

    title_html = (
        f'<a href="{href}" style="color:{acc};text-decoration:none;font-size:13px;'
        f'font-weight:700;letter-spacing:0.01em">{_html.escape(label)}</a>'
    )
    note_html = (
        f'<div style="font-size:11px;color:{text_dim};line-height:1.5;'
        f'margin-top:6px">{_html.escape(note)}</div>'
    )
    examples_html = (
        f'<div style="font-size:10px;color:{text_dim};opacity:0.7;'
        f"font-family:JetBrains Mono,monospace;margin-top:10px;"
        f'padding-top:8px;border-top:1px solid {border}">{_html.escape(examples)}</div>'
    )

    return (
        f'<div style="background:{bg};border:1px solid {border};padding:14px 16px;'
        f'display:flex;flex-direction:column;min-height:150px">'
        f'<div style="{header_style}">{title_html}{phase_badge}</div>'
        f'<div style="margin-top:-4px">{count_badge}</div>'
        f'{note_html}'
        f'{examples_html}'
        f'</div>'
    )


def render_partner_brain_hub(qp: Dict[str, str] | None = None) -> str:
    """Render the Partner Brain hub landing page.

    qp — query params (unused in Phase 0; accepted for signature
    consistency with other data_public pages).
    """
    _ = qp or {}

    bg = P["bg"]
    panel = P["panel"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    pos = P["positive"]
    warn = P["warning"]

    total_modules = sum(int(c["count"]) for c in _CATEGORIES)  # type: ignore[arg-type]
    live_modules = sum(int(c["count"]) for c in _CATEGORIES if c["phase"] == "LIVE")  # type: ignore[arg-type]
    pending_modules = total_modules - live_modules

    kpi_strip = (
        ck_kpi_block("Categories", str(len(_CATEGORIES)), "", "") +
        ck_kpi_block("Total modules", str(total_modules), "", "") +
        ck_kpi_block("Wired today", str(live_modules), "", "") +
        ck_kpi_block("Pending wiring", str(pending_modules), "", "") +
        ck_kpi_block("Branch", "Phase 0", "", "") +
        ck_kpi_block("Source package", "pe_intelligence", "", "")
    )

    cards_html = "".join(_category_card(c) for c in _CATEGORIES)
    grid = (
        f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));'
        f'gap:14px;margin-top:20px">{cards_html}</div>'
    )

    intro = (
        f'<div style="padding:20px;max-width:1400px;margin:0 auto">'
        f'<div style="margin-bottom:20px">'
        f'<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">'
        f'Partner Brain</h1>'
        f'<p style="font-size:12px;color:{text_dim};margin-top:4px">'
        f"Senior-PE-healthcare-partner judgment layer over the deal packet. "
        f"Seven reflexes, 18 task categories, 275 modules. "
        f"LIVE cards wire the key modules to a partner-usable view; "
        f"remaining categories surface in upcoming phases.</p>"
        f'</div>'
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">'
        f'{kpi_strip}</div>'
        f'<div style="margin-bottom:16px;padding:14px 16px;background:{panel};'
        f'border:1px solid {P["accent"]};border-left:3px solid {P["accent"]}">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap">'
        f'<div>'
        f'<div style="font-size:12px;font-weight:700;color:{text}">'
        f'Every partner-brain module — one page, 264 entries</div>'
        f'<div style="font-size:11px;color:{text_dim};margin-top:3px;line-height:1.5">'
        f'Auto-rendered detail pages for every catalogued module. AUTO-RUN '
        f'modules compute and show a report on default inputs; FN-ONLY '
        f"modules show signature + docstring.</div></div>"
        f'<a href="/partner-brain/modules" style="font-size:11px;color:{P["accent"]};'
        f'border:1px solid {P["accent"]};padding:6px 14px;text-decoration:none;'
        f'font-family:JetBrains Mono,monospace;letter-spacing:0.06em">OPEN DIRECTORY →</a>'
        f"</div></div>"
        f'{ck_section_header("Task categories", "click a LIVE card to run the review now; PHASE 1 cards surface in the next session", len(_CATEGORIES))}'
        f'{grid}'
        f'<div style="margin-top:30px;padding:16px;background:{panel};border:1px solid {border};font-size:11px;color:{text_dim};line-height:1.6">'
        f'<span style="color:{text};font-weight:600">How to read this page.</span> '
        f"Each card is a partner task. LIVE cards are wired to a page you can use today; "
        f"PHASE 1 cards are scheduled for the next build session. "
        f'The module count is how many <code style="color:{pos};background:transparent">pe_intelligence/*.py</code> modules '
        f"feed that category. Clicking a PHASE 1 card now returns a placeholder "
        f"with the module list."
        f'</div>'
        f'</div>'
    )

    return chartis_shell(body=intro, title="Partner Brain", active_nav="/partner-brain")


def render_partner_brain_category_stub(qp: Dict[str, str] | None = None) -> str:
    """Placeholder for /partner-brain/<slug> category pages.

    Until Phase 1 ships the real category pages, visitors land here
    and see what's coming. The slug is inferred from the ``slug``
    query param passed through from server.py.
    """
    qp = qp or {}
    slug = qp.get("slug", "").strip().lower()

    # Find the category metadata; "review" is handled by a different page.
    match = next((c for c in _CATEGORIES if c["slug"] == slug), None)

    bg = P["bg"]
    panel = P["panel"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]
    warn = P["warning"]

    if match is None:
        body = (
            f'<div style="padding:40px;max-width:900px;margin:0 auto">'
            f'<h1 style="font-size:18px;font-weight:700;color:{text}">'
            f'Partner Brain · Unknown category</h1>'
            f'<p style="font-size:12px;color:{text_dim};margin-top:8px">'
            f"No category matches the slug <code>{_html.escape(slug)}</code>. "
            f'Return to the <a href="/partner-brain" style="color:{acc}">hub</a>.</p>'
            f'</div>'
        )
        return chartis_shell(body=body, title="Partner Brain", active_nav="/partner-brain")

    label = str(match["label"])
    count = int(match["count"])  # type: ignore[arg-type]
    note = str(match["note"])
    examples = str(match["examples"])

    body = (
        f'<div style="padding:40px;max-width:1000px;margin:0 auto">'
        f'<div style="margin-bottom:24px">'
        f'<a href="/partner-brain" style="color:{acc};font-size:11px;text-decoration:none">'
        f'← Partner Brain hub</a>'
        f'</div>'
        f'<h1 style="font-size:20px;font-weight:700;color:{text}">{_html.escape(label)}</h1>'
        f'<p style="font-size:12px;color:{text_dim};margin-top:6px;line-height:1.6">'
        f'{_html.escape(note)}</p>'
        f'<div style="margin-top:24px;padding:16px;background:{panel};border:1px solid {border}">'
        f'<div style="font-size:10px;color:{warn};letter-spacing:0.08em;'
        f'text-transform:uppercase">Coming in Phase 1</div>'
        f'<div style="font-size:13px;color:{text};margin-top:8px;line-height:1.5">'
        f'{count} backend modules feed this category. The interactive '
        f'page that runs them on the current deal lands in the next '
        f"build session.</div>"
        f'<div style="font-size:10px;color:{text_dim};'
        f'font-family:JetBrains Mono,monospace;margin-top:16px;padding-top:12px;'
        f'border-top:1px solid {border}">Modules: {_html.escape(examples)}</div>'
        f'</div>'
        f'</div>'
    )
    return chartis_shell(
        body=body, title=f"Partner Brain · {label}", active_nav="/partner-brain"
    )
