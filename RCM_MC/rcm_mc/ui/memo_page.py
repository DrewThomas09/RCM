"""PE Desk IC Memo — browser-rendered investment committee memo.

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


def _memo_integrity_svg(sections: List[Dict[str, Any]]) -> str:
    """The memo's shape and trust state in one strip.

    Each section is a block sized by its share of the memo's words
    and toned by fact-check status (green verified / red check
    required) — so "the two longest sections are the unverified ones"
    is visible before reading. Caption totals sections, verified
    count, and words. No sections renders nothing.
    """
    rows = []
    for sec in sections:
        title = str(sec.get("title", sec.get("heading", "")) or "—")
        content = str(sec.get("content", sec.get("body", "")) or "")
        words = max(1, len(content.split()))
        rows.append((title, words, bool(sec.get("fact_checks_passed", True))))
    if not rows:
        return ""
    total_words = sum(w for _, w, _ in rows)
    n_verified = sum(1 for _, _, ok in rows if ok)

    width, bar_h = 720, 34
    height = bar_h + 22
    min_w = 26.0
    # Proportional widths with a readability floor, renormalized.
    raw = [max(min_w, width * w / total_words) for _, w, _ in rows]
    scale = width / sum(raw)
    segs, x = [], 0.0
    for (title, words, ok), rw in zip(rows, raw):
        w = rw * scale
        tone = "#0a8a5f" if ok else "#b5321e"
        segs.append(
            f'<rect x="{x:.1f}" y="0" width="{max(w - 2, 1):.1f}" '
            f'height="{bar_h}" rx="2" fill="{tone}" '
            f'fill-opacity="{0.85 if ok else 0.9}"/>'
        )
        if w >= 64:
            short = title if len(title) <= int(w / 7) else title[: int(w / 7) - 1] + "…"
            segs.append(
                f'<text x="{x + w / 2:.1f}" y="{bar_h / 2 + 3.5}" '
                f'text-anchor="middle" font-size="9.5" fill="#ffffff">'
                f'{html.escape(short)}</text>'
            )
        x += w
    caption = (
        f"{len(rows)} SECTIONS · {n_verified} VERIFIED · "
        f"{len(rows) - n_verified} CHECK REQUIRED · "
        f"{total_words:,} WORDS · BLOCK WIDTH = SHARE OF MEMO"
    )
    svg = (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img" '
        f'aria-label="Memo sections by length and fact-check status">'
        + "".join(segs)
        + f'<text x="0" y="{height - 4}" font-size="9" letter-spacing="1" '
        f'fill="{PALETTE["text_muted"]}">{caption}</text>'
        "</svg>"
    )
    return (
        '<div class="ck-memo-integrity" style="margin:0 0 14px;">'
        + svg + "</div>"
    )


def render_memo_page(deal_id: str, deal_name: str, memo: Dict[str, Any]) -> str:
    """Render the IC memo as a browser page."""
    sections = memo.get("sections", [])
    warnings = memo.get("fact_check_warnings", [])
    llm_used = memo.get("llm_used", False)

    # KPIs — ck_kpi_strip
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Memo Sections", f"{len(sections)}",
            help={
                "definition": (
                    "Distinct sections in the assembled IC memo: "
                    "thesis, market, comparables, risks, financial "
                    "model summary, value-creation plan, exit plan. "
                    "A complete memo runs 7-9 sections; partial "
                    "memos are draft-state and should be flagged at IC."
                ),
            },
        )
        + ck_kpi_block(
            "Fact-Check Warnings", f"{len(warnings)}",
            help={
                "definition": (
                    "Statements in the memo that the validator could "
                    "not confirm against the underlying packet data. "
                    "Common: claims with no source citation, numbers "
                    "that differ between memo and packet, or "
                    "narratives that contradict packet flags. Resolve "
                    "every warning before sending the memo to IC: "
                    "untraceable claims kill credibility."
                ),
            },
        )
        + ck_kpi_block(
            "Generation Method",
            "AI" if llm_used else "Template",
            help={
                "definition": (
                    "AI = LLM-drafted from the packet (faster, varied "
                    "phrasing, requires read-through). Template = "
                    "deterministic from packet fields (repeatable, "
                    "no hallucination risk, but stiffer prose). Both "
                    "use the same underlying numbers: only the "
                    "narrative wrapping differs."
                ),
            },
        )
        + '</div>'
    )

    # Sections — each becomes a ck_panel
    sections_html = _memo_integrity_svg(sections)
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
        eyebrow="Up next",
        italic_word="packet",
    )
    # 2026-05-28 batch 25 · Group D sweep · universal strict 5-block
    # head. Replaces the shell's editorial_intro= auto-inject (which
    # produced a stack: shell h1 + ck_section_intro h2 deck) with a
    # single unified header.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="IC MEMO",
        title=f"IC Memo · {html.escape(deal_name)}",
        meta=(
            f"{len(sections)} SECTION"
            f"{'S' if len(sections) != 1 else ''} · "
            f"{len(warnings)} FACT-CHECK WARNING"
            f"{'S' if len(warnings) != 1 else ''} · "
            f"{'AI-GENERATED' if llm_used else 'TEMPLATE-BASED'}"
        ),
        lede_italic_phrase="Where the deal earns its hour at IC.",
        lede_body=(
            "Auto-assembled IC memo with thesis, comps, "
            "exit, and bear case. Use as a draft anchor; "
            "the partner adds judgment in the gaps the "
            "platform can't reason about."
        ),
    )
    body = f'{head}{nav}{kpis}{sections_html}{warning_html}{actions}{next_up}'

    return chartis_shell(body, f"IC Memo · {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(sections)} sections | {'AI-generated' if llm_used else 'Template-based'}")


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
        + ck_kpi_block(
            "Validation Status", status_badge,
            help={
                "definition": (
                    "Aggregate state of the deal's data + assumption "
                    "checks. Valid = no issues, ready for IC; Issues "
                    "Found = at least one blocker (missing required "
                    "field, contradictory inputs, out-of-band "
                    "assumption). Resolve issues before IC; warnings "
                    "can be acknowledged but should be named in the "
                    "memo."
                ),
            },
        )
        + ck_kpi_block(
            "Issues", f"{len(issues)}",
            help={
                "definition": (
                    "Blocking validation failures: missing required "
                    "fields, contradictory inputs, assumption values "
                    "outside the band (e.g. terminal growth > 5%). "
                    "Cannot send to IC with unresolved issues; the "
                    "memo's downstream numbers are unreliable."
                ),
            },
        )
        + ck_kpi_block(
            "Warnings", f"{len(warnings)}",
            help={
                "definition": (
                    "Non-blocking but reviewable: assumption values "
                    "near band edges, fields populated from defaults, "
                    "comparables thinner than usual. Acknowledge each "
                    "in the IC discussion; partners shouldn't be "
                    "surprised by them mid-meeting."
                ),
            },
        )
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

    return chartis_shell(body, f"Validation · {html.escape(deal_name)}",
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
        + ck_kpi_block(
            "Completeness Grade", grade_badge,
            help={
                "definition": (
                    "A-F letter grade rolled up from coverage + "
                    "data-source-quality + cross-field consistency. "
                    "A = ready for IC; B = workable, name gaps in "
                    "memo; C = partial, escalate to deal team; D-F = "
                    "do not send to IC, the underlying analysis won't "
                    "hold up to scrutiny."
                ),
            },
        )
        + ck_kpi_block(
            "Coverage", f"{pct:.0f}%",
            help={
                "definition": (
                    "Share of the 38-metric canonical registry "
                    "populated for this deal. Above 80% = strong "
                    "diligence posture; 60-80% = workable with "
                    "imputation; below 60% = imputation dominates "
                    "and the downstream packet carries wide conformal "
                    "bands."
                ),
            },
        )
        + ck_kpi_block(
            "Fields Populated", f"{present}/{total}",
            help={
                "definition": (
                    "Absolute count of registry fields with real "
                    "(non-imputed) values. The 38-metric registry is "
                    "the platform's canonical KPI surface: every "
                    "missing field becomes a Bayesian-prior fallback "
                    "downstream, widening uncertainty bands on the "
                    "MOIC / IRR distribution."
                ),
            },
        )
        + '</div>'
    )

    bar = ck_panel(
        '<div class="memo-coverage-bar">'
        f'<div class="memo-coverage-fill" style="width:{pct:.0f}%;background:{bar_color};"></div>'
        '</div>'
        '<p class="ck-section-body">'
        f'{present} of {total} metrics in the 38-metric registry are populated. '
        f'{"Excellent coverage: ready for full analysis." if pct > 80 else "Good coverage." if pct > 60 else "Request additional data from the seller to improve analysis accuracy."}'
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

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, f"Completeness · {html.escape(deal_name)}",
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
