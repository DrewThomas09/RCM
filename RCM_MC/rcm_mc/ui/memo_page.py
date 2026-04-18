"""SeekingChartis IC Memo — browser-rendered investment committee memo.

Renders the auto-generated IC memo with sections and fact-check status.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import chartis_shell
from .models_page import _model_nav
from .brand import PALETTE


def render_memo_page(deal_id: str, deal_name: str, memo: Dict[str, Any]) -> str:
    """Render the IC memo as a browser page."""
    sections = memo.get("sections", [])
    warnings = memo.get("fact_check_warnings", [])
    llm_used = memo.get("llm_used", False)

    # KPIs
    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(sections)}</div>'
        f'<div class="cad-kpi-label">Memo Sections</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(warnings)}</div>'
        f'<div class="cad-kpi-label">Fact-Check Warnings</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{"AI" if llm_used else "Template"}</div>'
        f'<div class="cad-kpi-label">Generation Method</div></div>'
        f'</div>'
    )

    # Sections
    sections_html = ""
    for sec in sections:
        title = html.escape(str(sec.get("title", sec.get("heading", ""))))
        content = html.escape(str(sec.get("content", sec.get("body", ""))))
        passed = sec.get("fact_checks_passed", True)
        badge_cls = "cad-badge-green" if passed else "cad-badge-red"
        badge_text = "Verified" if passed else "Check Required"
        sections_html += (
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<h2>{title}</h2>'
            f'<span class="cad-badge {badge_cls}">{badge_text}</span>'
            f'</div>'
            f'<div style="font-size:13px;color:{PALETTE["text_secondary"]};line-height:1.8;'
            f'white-space:pre-wrap;">{content}</div>'
            f'</div>'
        )

    # Warnings
    warning_html = ""
    if warnings:
        w_items = "".join(
            f'<li style="margin-bottom:4px;color:{PALETTE["warning"]};">{html.escape(str(w))}</li>'
            for w in warnings
        )
        warning_html = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["warning"]};">'
            f'<h2>Fact-Check Warnings</h2>'
            f'<ul style="font-size:12.5px;padding-left:20px;">{w_items}</ul></div>'
        )

    # Actions
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/memo" class="cad-btn" '
        f'style="text-decoration:none;">Download JSON</a>'
        f'<a href="/models/questions/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">Diligence Questions</a>'
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Deal Dashboard</a></div>'
    )

    nav = _model_nav(deal_id, "")
    body = f'{nav}{kpis}{sections_html}{warning_html}{actions}'

    return chartis_shell(body, f"IC Memo — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(sections)} sections | {'AI-generated' if llm_used else 'Template-based'}")


def render_validation_page(deal_id: str, deal_name: str, validation: Dict[str, Any]) -> str:
    """Render deal validation results."""
    is_valid = validation.get("valid", True)
    issues = validation.get("issues", [])
    warnings = validation.get("warnings", [])
    fields = validation.get("profile_fields", 0)

    status_cls = "cad-badge-green" if is_valid else "cad-badge-red"
    status_text = "Valid" if is_valid else "Issues Found"

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'<span class="cad-badge {status_cls}" style="font-size:14px;padding:4px 12px;">'
        f'{status_text}</span></div>'
        f'<div class="cad-kpi-label">Validation Status</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{PALETTE["negative"]};">'
        f'{len(issues)}</div>'
        f'<div class="cad-kpi-label">Issues</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{PALETTE["warning"]};">'
        f'{len(warnings)}</div>'
        f'<div class="cad-kpi-label">Warnings</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{fields}</div>'
        f'<div class="cad-kpi-label">Profile Fields</div></div>'
        f'</div>'
    )

    issues_html = ""
    if issues:
        rows = "".join(
            f'<tr><td><span class="cad-badge cad-badge-red">Error</span></td>'
            f'<td>{html.escape(str(i))}</td></tr>'
            for i in issues
        )
        issues_html = (
            f'<div class="cad-card">'
            f'<h2>Issues (must fix)</h2>'
            f'<table class="cad-table"><thead><tr><th>Severity</th><th>Description</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    warnings_html = ""
    if warnings:
        rows = "".join(
            f'<tr><td><span class="cad-badge cad-badge-amber">Warning</span></td>'
            f'<td>{html.escape(str(w))}</td></tr>'
            for w in warnings
        )
        warnings_html = (
            f'<div class="cad-card">'
            f'<h2>Warnings (review)</h2>'
            f'<table class="cad-table"><thead><tr><th>Severity</th><th>Description</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    nav = _model_nav(deal_id, "")
    body = f'{nav}{kpis}{issues_html}{warnings_html}'

    return chartis_shell(body, f"Validation — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{'Valid' if is_valid else f'{len(issues)} issues'} | {len(warnings)} warnings | {fields} fields")


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

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{grade_color};font-size:36px;">'
        f'{grade}</div>'
        f'<div class="cad-kpi-label">Completeness Grade</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{pct:.0f}%</div>'
        f'<div class="cad-kpi-label">Coverage</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{present}/{total}</div>'
        f'<div class="cad-kpi-label">Fields Populated</div></div>'
        f'</div>'
    )

    bar = (
        f'<div class="cad-card">'
        f'<h2>Data Coverage</h2>'
        f'<div style="background:{PALETTE["bg_tertiary"]};border-radius:6px;height:16px;margin-bottom:8px;">'
        f'<div style="width:{pct:.0f}%;background:{bar_color};border-radius:6px;height:16px;"></div>'
        f'</div>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};">'
        f'{present} of {total} metrics in the 38-metric registry are populated. '
        f'{"Excellent coverage — ready for full analysis." if pct > 80 else "Good coverage." if pct > 60 else "Request additional data from the seller to improve analysis accuracy."}'
        f'</p></div>'
    )

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/models/questions/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Generate Data Request</a>'
        f'<a href="/import" class="cad-btn" style="text-decoration:none;">Update Deal Profile</a>'
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">'
        f'Deal Dashboard</a></div>'
    )

    nav = _model_nav(deal_id, "")
    body = f'{nav}{kpis}{bar}{actions}'

    return chartis_shell(body, f"Completeness — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Grade: {grade} | {pct:.0f}% coverage | {present}/{total} fields")
