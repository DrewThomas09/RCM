"""SeekingChartis Diligence Tools — questions, playbook, challenge solver.

Connects analysis/diligence_questions.py, analysis/playbook.py, and
analysis/challenge.py to the browser.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from .shell_v2 import shell_v2
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

    cat_badges = " ".join(
        f'<span class="cad-badge cad-badge-muted" style="margin:2px;">{html.escape(c)}: {n}</span>'
        for c, n in sorted(by_category.items(), key=lambda x: -x[1])
    )

    nav = _model_nav(deal_id, "questions")
    body = (
        f'{nav}'
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(questions)}</div>'
        f'<div class="cad-kpi-label">Questions Generated</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(by_category)}</div>'
        f'<div class="cad-kpi-label">Categories</div></div>'
        f'</div>'

        f'<div class="cad-card">'
        f'<h2>Categories</h2>'
        f'<div>{cat_badges}</div></div>'

        f'<div class="cad-card">'
        f'<h2>Diligence Questions</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Auto-generated from deal profile and risk flags. Export as CSV for the data room request.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>#</th><th>Priority</th><th>Category</th><th>Question</th><th>Rationale</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'

        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<h2>How to Use This</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>Send these {len(questions)} questions to the seller as your initial data room request. '
        f'High-priority items should be addressed before the IC meeting. '
        f'Download as CSV and paste into your standard diligence tracker.</p>'
        f'<p style="margin-top:6px;">Once you have answers, update the deal profile via '
        f'<a href="/import" style="color:{PALETTE["text_link"]};">Import</a> and re-run the '
        f'<a href="/models/denial/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">denial analysis</a> '
        f'with actual payer-level data.</p>'
        f'</div></div>'

        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/analysis/{html.escape(deal_id)}/diligence-questions" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Download CSV for Data Room</a>'
        f'<a href="/models/playbook/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">Value Creation Playbook</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    return shell_v2(body, f"Diligence Questions — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(questions)} questions across {len(by_category)} categories")


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

    return shell_v2(body, f"Playbook — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"{len(entries)} initiatives | ${total_impact/1e6:.1f}M total impact")
