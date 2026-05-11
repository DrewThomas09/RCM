"""SeekingChartis IC Memo — browser-rendered investment committee memo.

Renders the auto-generated IC memo with sections and fact-check status.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_signal_badge,
)
from .models_page import _model_nav
from .brand import PALETTE


def render_memo_page(deal_id: str, deal_name: str, memo: Dict[str, Any]) -> str:
    """Render the IC memo as a browser page."""
    sections = memo.get("sections", [])
    warnings = memo.get("fact_check_warnings", [])
    llm_used = memo.get("llm_used", False)

    # KPIs — ck_kpi_strip
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Memo Sections", f"{len(sections)}")
        + ck_kpi_block("Fact-Check Warnings", f"{len(warnings)}")
        + ck_kpi_block(
            "Generation Method",
            "AI" if llm_used else "Template",
        )
        + '</div>'
    )

    # Sections — each becomes a ck_panel
    sections_html = ""
    for sec in sections:
        title = html.escape(str(sec.get("title", sec.get("heading", ""))))
        content = html.escape(str(sec.get("content", sec.get("body", ""))))
        passed = sec.get("fact_checks_passed", True)
        badge = ck_signal_badge(
            "Verified" if passed else "Check Required",
            tone="positive" if passed else "negative",
        )
        sec_inner = (
            f'<p class="ck-section-body">{badge}</p>'
            f'<div class="memo-section-content">{content}</div>'
        )
        sections_html += ck_panel(sec_inner, title=title)

    # Warnings
    warning_html = ""
    if warnings:
        w_items = "".join(
            f'<li>{html.escape(str(w))}</li>' for w in warnings
        )
        warning_html = ck_panel(
            f'<ul class="ck-list">{w_items}</ul>',
            title="Fact-Check Warnings",
        )

    # Actions
    actions = ck_panel(
        '<p class="ck-section-body">'
        f'<a href="/api/deals/{html.escape(deal_id)}/memo" class="cad-btn">Download JSON</a> '
        f'<a href="/models/questions/{html.escape(deal_id)}" class="cad-btn">Diligence Questions</a> '
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary">Deal Dashboard</a>'
        '</p>',
        title="Cross-links",
    )

    nav = _model_nav(deal_id, "")
    next_up = ck_next_section(
        "Open the IC packet",
        "/diligence/ic-packet",
        eyebrow="Continue —",
        italic_word="packet",
    )
    body = f'{nav}{kpis}{sections_html}{warning_html}{actions}{next_up}'

    return chartis_shell(body, f"IC Memo — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(sections)} sections | {'AI-generated' if llm_used else 'Template-based'}",
        editorial_intro={
            "eyebrow": "IC MEMO",
            "headline": "Where the deal earns its hour at IC.",
            "italic_word": "earns",
            "body": (
                "Auto-assembled IC memo with thesis, comps, "
                "exit, and bear case. Use as a draft anchor; "
                "the partner adds judgment in the gaps the "
                "platform can't reason about."
            ),
        })


def render_validation_page(deal_id: str, deal_name: str, validation: Dict[str, Any]) -> str:
    """Render deal validation results."""
    is_valid = validation.get("valid", True)
    issues = validation.get("issues", [])
    warnings = validation.get("warnings", [])
    fields = validation.get("profile_fields", 0)

    status_badge = ck_signal_badge(
        "Valid" if is_valid else "Issues Found",
        tone="positive" if is_valid else "negative",
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Validation Status", status_badge)
        + ck_kpi_block("Issues", f"{len(issues)}")
        + ck_kpi_block("Warnings", f"{len(warnings)}")
        + ck_kpi_block("Profile Fields", f"{fields}")
        + '</div>'
    )

    issues_html = ""
    if issues:
        rows = "".join(
            f'<tr><td><span class="cad-badge cad-badge-red">Error</span></td>'
            f'<td>{html.escape(str(i))}</td></tr>'
            for i in issues
        )
        issues_html = ck_panel(
            '<table class="cad-table"><thead><tr>'
            '<th>Severity</th><th>Description</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Issues (must fix)",
        )

    warnings_html = ""
    if warnings:
        rows = "".join(
            f'<tr><td><span class="cad-badge cad-badge-amber">Warning</span></td>'
            f'<td>{html.escape(str(w))}</td></tr>'
            for w in warnings
        )
        warnings_html = ck_panel(
            '<table class="cad-table"><thead><tr>'
            '<th>Severity</th><th>Description</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            title="Warnings (review)",
        )

    nav = _model_nav(deal_id, "")
    body = f'{nav}{kpis}{issues_html}{warnings_html}'

    return chartis_shell(body, f"Validation — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{'Valid' if is_valid else f'{len(issues)} issues'} | {len(warnings)} warnings | {fields} fields",
        editorial_intro={
            "eyebrow": "DEAL VALIDATION",
            "headline": "Where the deal record fails its checks.",
            "italic_word": "fails",
            "body": (
                "Hard validation issues + soft warnings against "
                "the deal record. Issues block analysis runs; "
                "warnings flag suspicious values that may "
                "compromise the predictions."
            ),
        })


def render_completeness_page(deal_id: str, deal_name: str, completeness: Dict[str, Any]) -> str:
    """Render deal data completeness assessment."""
    grade = completeness.get("grade", "—")
    coverage = completeness.get("coverage_pct", 0)
    present = completeness.get("present_count", 0)
    total = completeness.get("total_registry", 38)

    grade_color = {
        "A": PALETTE["positive"], "B": PALETTE["brand_accent"],
        "C": PALETTE["warning"], "D": PALETTE["negative"],
    }.get(grade, PALETTE["text_muted"])

    pct = coverage * 100 if coverage < 1 else coverage
    bar_color = PALETTE["positive"] if pct > 70 else (PALETTE["warning"] if pct > 40 else PALETTE["negative"])

    grade_tone = (
        "positive" if grade == "A"
        else "neutral" if grade == "B"
        else "warning" if grade == "C"
        else "negative" if grade == "D"
        else "neutral"
    )
    grade_badge = ck_signal_badge(f"Grade {grade}", tone=grade_tone)

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Completeness Grade", grade_badge)
        + ck_kpi_block("Coverage", f"{pct:.0f}%")
        + ck_kpi_block("Fields Populated", f"{present}/{total}")
        + '</div>'
    )

    bar = ck_panel(
        '<div class="memo-coverage-bar">'
        f'<div class="memo-coverage-fill" style="width:{pct:.0f}%;background:{bar_color};"></div>'
        '</div>'
        '<p class="ck-section-body">'
        f'{present} of {total} metrics in the 38-metric registry are populated. '
        f'{"Excellent coverage — ready for full analysis." if pct > 80 else "Good coverage." if pct > 60 else "Request additional data from the seller to improve analysis accuracy."}'
        '</p>',
        title="Data Coverage",
    )

    actions = ck_panel(
        '<p class="ck-section-body">'
        f'<a href="/models/questions/{html.escape(deal_id)}" class="cad-btn cad-btn-primary">Generate Data Request</a> '
        '<a href="/import" class="cad-btn">Update Deal Profile</a> '
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn">Deal Dashboard</a>'
        '</p>',
        title="Cross-links",
    )

    nav = _model_nav(deal_id, "")
    body = f'{nav}{kpis}{bar}{actions}'

    return chartis_shell(body, f"Completeness — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Grade: {grade} | {pct:.0f}% coverage | {present}/{total} fields",
        editorial_intro={
            "eyebrow": "DATA COMPLETENESS",
            "headline": "Where the deal record has gaps.",
            "italic_word": "gaps",
            "body": (
                "Field-by-field completeness against the canonical "
                "data model. Lower grades mean the analyses below "
                "lean more on Bayesian priors than observed data; "
                "fix the gaps via the Data Request action."
            ),
        })
