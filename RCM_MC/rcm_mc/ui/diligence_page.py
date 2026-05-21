"""PE Desk Diligence Tools — questions, playbook, challenge solver.

Connects analysis/diligence_questions.py, analysis/playbook.py, and
analysis/challenge.py to the browser.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_bar_row, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_header,
)
from .models_page import _model_nav
from .brand import PALETTE


def render_diligence_questions(deal_id: str, deal_name: str, questions: List[Dict[str, Any]]) -> str:
    """Render auto-generated diligence questions."""
    rows = ""
    for i, q in enumerate(questions, 1):
        category = html.escape(str(q.get("category", "")))
        question = html.escape(str(q.get("question", q.get("text", ""))))
        rationale = html.escape(str(q.get("rationale", q.get("reason", ""))))
        priority = q.get("priority", q.get("severity", "medium"))
        pri_cls = {"high": "cad-badge-red", "critical": "cad-badge-red",
                   "medium": "cad-badge-amber"}.get(priority, "cad-badge-muted")
        rows += (
            f'<tr>'
            f'<td class="num" style="color:{PALETTE["text_muted"]};">{i}</td>'
            f'<td><span class="cad-badge {pri_cls}">{html.escape(str(priority))}</span></td>'
            f'<td><span class="cad-badge cad-badge-blue">{category}</span></td>'
            f'<td style="font-weight:500;">{question}</td>'
            f'<td style="font-size:12px;color:{PALETTE["text_secondary"]};">{rationale}</td>'
            f'</tr>'
        )

    by_category: Dict[str, int] = {}
    for q in questions:
        cat = str(q.get("category", "Other"))
        by_category[cat] = by_category.get(cat, 0) + 1

    _sorted_cats = sorted(by_category.items(), key=lambda x: -x[1])
    cat_badges = " ".join(
        f'<span class="cad-badge cad-badge-muted" style="margin:2px;">{html.escape(c)}: {n}</span>'
        for c, n in _sorted_cats
    )
    # Distribution bars make the question mix scannable — which diligence
    # areas dominate the auto-generated set — instead of a row of chips.
    _cat_max = max((n for _, n in _sorted_cats), default=0) or 1
    cat_bars = "".join(
        ck_bar_row(c, str(n), n / _cat_max * 100.0)
        for c, n in _sorted_cats
    )
    cat_body = (cat_bars + cat_badges) if cat_bars else cat_badges

    nav = _model_nav(deal_id, "questions")
    kpi_strip = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Questions Generated", f"{len(questions)}")
        + ck_kpi_block("Categories", f"{len(by_category)}")
        + "</div>"
    )
    questions_table = (
        '<p class="ck-section-body">'
        'Auto-generated from deal profile and risk flags. Export as CSV '
        'for the data room request.</p>'
        '<table class="ck-table"><thead><tr>'
        '<th>#</th><th>Priority</th><th>Category</th>'
        '<th>Question</th><th>Rationale</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
    )
    how_to_use = (
        f'<p class="ck-section-body">'
        f'Send these {len(questions)} questions to the seller as your '
        f'initial data room request. High-priority items should be '
        f'addressed before the IC meeting. Download as CSV and paste '
        f'into your standard diligence tracker.</p>'
        f'<p class="ck-section-body">'
        f'Once you have answers, update the deal profile via '
        f'<a href="/import" class="ck-link">Import</a> and re-run the '
        f'<a href="/models/denial/{html.escape(deal_id)}" class="ck-link">'
        f'denial analysis</a> with actual payer-level data.</p>'
    )
    actions = (
        '<p class="ck-section-body">'
        f'<a href="/api/analysis/{html.escape(deal_id)}/diligence-questions" '
        f'class="cad-btn cad-btn-primary">Download CSV for Data Room</a> '
        f'<a href="/models/playbook/{html.escape(deal_id)}" class="cad-btn">'
        f'Value Creation Playbook</a> '
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn">'
        f'Full Analysis</a></p>'
    )
    body = (
        f"{nav}"
        + kpi_strip
        + ck_panel(cat_body, title="Categories")
        + ck_panel(questions_table, title="Diligence Questions")
        + ck_panel(how_to_use, title="How to Use This")
        + ck_panel(actions, title="Next steps")
        + ck_next_section(
            "Open the portfolio-wide question ledger",
            "/diligence/questions",
            eyebrow="Continue —",
            italic_word="ledger",
        )
    )

    return chartis_shell(body, f"Diligence Questions — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(questions)} questions across {len(by_category)} categories",
        editorial_intro={
            "eyebrow": "DILIGENCE QUESTIONS",
            "headline": "What you should be asking next.",
            "italic_word": "next",
            "body": (
                "Auto-generated diligence question list keyed off "
                "this deal's outstanding gaps - missing data, "
                "unresolved findings, model-flagged inconsistencies. "
                "Each question carries a category and rationale "
                "so you know why it matters."
            ),
        })


def render_playbook(deal_id: str, deal_name: str, entries: List[Dict[str, Any]]) -> str:
    """Render the operational playbook."""
    rows = ""
    total_impact = 0
    for e in entries:
        title = html.escape(str(e.get("title", e.get("initiative", ""))))
        category = html.escape(str(e.get("category", "")))
        timeline = html.escape(str(e.get("timeline", e.get("timeframe", ""))))
        impact = e.get("ebitda_impact", e.get("impact", 0))
        total_impact += float(impact) if impact else 0
        owner = html.escape(str(e.get("owner", "")))
        priority = e.get("priority", "medium")
        pri_cls = {"high": "cad-badge-red", "critical": "cad-badge-red",
                   "medium": "cad-badge-amber"}.get(priority, "cad-badge-muted")
        rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{title}</td>'
            f'<td><span class="cad-badge cad-badge-blue">{category}</span></td>'
            f'<td><span class="cad-badge {pri_cls}">{html.escape(str(priority))}</span></td>'
            f'<td class="num">${float(impact)/1e6:.1f}M</td>'
            f'<td>{timeline}</td>'
            f'<td>{owner}</td>'
            f'</tr>'
        )

    nav = _model_nav(deal_id, "playbook")
    body = (
        f'{nav}'
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(entries)}</div>'
        f'<div class="cad-kpi-label">Initiatives</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${total_impact/1e6:.1f}M</div>'
        f'<div class="cad-kpi-label">Total EBITDA Impact</div></div>'
        f'</div>'

        f'<div class="cad-card">'
        f'<h2>Value Creation Playbook</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Prioritized operational initiatives with estimated EBITDA impact and timeline.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Initiative</th><th>Category</th><th>Priority</th>'
        f'<th>Impact</th><th>Timeline</th><th>Owner</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'

        f'<div class="cad-card" style="border-left:3px solid {PALETTE["positive"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>{len(entries)} initiatives totaling <strong>${total_impact/1e6:.1f}M</strong> in annual EBITDA improvement. '
        f'At an 11x exit multiple, this represents <strong>${total_impact * 11 / 1e6:.0f}M</strong> in equity value creation.</p>'
        f'<p style="margin-top:6px;">Present this as the 100-day plan at IC. Track execution against the '
        f'<a href="/models/bridge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">EBITDA bridge</a> '
        f'and monitor trends via '
        f'<a href="/models/trends/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">trend forecast</a>.</p>'
        f'</div></div>'

        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/models/bridge/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">'
        f'EBITDA Bridge</a>'
        f'<a href="/models/denial/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">'
        f'Denial Drivers</a>'
        f'<a href="/models/questions/{html.escape(deal_id)}" class="cad-btn" style="text-decoration:none;">'
        f'Diligence Questions</a>'
        f'<a href="/deal/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Deal Dashboard</a></div>'
    )

    return chartis_shell(body, f"Playbook — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(entries)} initiatives | ${total_impact/1e6:.1f}M total impact",
        editorial_intro={
            "eyebrow": "OPERATIONAL PLAYBOOK",
            "headline": "What the operator does in year one.",
            "italic_word": "does",
            "body": (
                "Sequenced value-creation initiatives with EBITDA "
                "impact estimates and timelines. The playbook "
                "anchors hold-period diligence; partner reviews "
                "use this to read whether actuals are tracking "
                "plan."
            ),
        })
