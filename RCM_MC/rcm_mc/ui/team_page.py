"""SeekingChartis Team Dashboard — activity feed and assignments.

Shows who is working on what, recent activity across the fund,
and comment threads on pipeline hospitals.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell
from ..portfolio.store import PortfolioStore
from .brand import PALETTE


def render_team_dashboard(db_path: str) -> str:
    """Render the team activity dashboard."""
    from ..data.team import (
        get_activity_feed, get_entity_url, _ensure_tables,
    )
    from ..data.pipeline import list_pipeline, _ensure_tables as _pipe_ensure

    # Route through PortfolioStore (campaign target 4E) so this
    # portfolio-scope read inherits busy_timeout=5000,
    # foreign_keys=ON, and Row factory the same way every other
    # deal-aware UI page does. Read-only — no commit needed.
    with PortfolioStore(db_path).connect() as con:
        _ensure_tables(con)
        _pipe_ensure(con)

        activity = get_activity_feed(con, limit=30)
        hospitals = list_pipeline(con)

    # Unique actors
    actors = sorted(set(a["actor"] for a in activity if a["actor"]))
    n_hospitals = len(hospitals)

    # KPIs
    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(4,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(actors)}</div>'
        f'<div class="cad-kpi-label">Team Members</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(activity)}</div>'
        f'<div class="cad-kpi-label">Recent Actions</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_hospitals}</div>'
        f'<div class="cad-kpi-label">Pipeline Hospitals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{sum(1 for a in activity if a["action"] == "comment")}</div>'
        f'<div class="cad-kpi-label">Comments</div></div>'
        f'</div>'
    )

    # Activity feed
    activity_items = ""
    for a in activity[:20]:
        action = a["action"]
        action_colors = {
            "comment": "var(--cad-accent)", "assign": "var(--cad-warn)",
            "stage_change": "var(--cad-pos)", "added": "var(--cad-pos)",
        }
        color = action_colors.get(action, "var(--cad-text3)")
        url = get_entity_url(a["entity_type"], a["entity_id"])
        detail = _html.escape(a["detail"][:60]) if a["detail"] else ""

        activity_items += (
            f'<div style="display:flex;gap:8px;padding:6px 0;font-size:12px;'
            f'border-bottom:1px solid var(--cad-border);">'
            f'<span style="color:var(--cad-text3);width:60px;font-size:10px;flex-shrink:0;">'
            f'{a["created_at"][5:16]}</span>'
            f'<span style="font-weight:600;color:var(--cad-text);width:40px;">'
            f'{_html.escape(a["actor"][:6])}</span>'
            f'<span style="color:{color};width:60px;font-size:10px;text-transform:uppercase;'
            f'font-weight:600;">{_html.escape(action[:10])}</span>'
            f'<a href="{_html.escape(url)}" style="color:var(--cad-link);text-decoration:none;'
            f'width:60px;">{_html.escape(a["entity_id"][:8])}</a>'
            f'<span style="color:var(--cad-text2);flex:1;">{detail}</span>'
            f'</div>'
        )

    feed_section = (
        f'<div class="cad-card">'
        f'<h2>Team Activity Feed</h2>'
        + (activity_items if activity_items else
           '<p style="color:var(--cad-text3);font-size:12px;">No team activity yet. '
           'Add comments to pipeline hospitals to get started.</p>') +
        f'</div>'
    )

    # Pipeline with assignment info
    pipe_rows = ""
    for h in hospitals[:12]:
        ccn = _html.escape(h.ccn)
        name = _html.escape(h.hospital_name[:25])
        assigned = _html.escape(h.assigned_to[:8]) if h.assigned_to else "—"
        pipe_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{ccn}" style="color:var(--cad-link);'
            f'text-decoration:none;font-weight:500;">{name}</a></td>'
            f'<td style="font-size:10px;">{_html.escape(h.stage)}</td>'
            f'<td style="font-size:11px;">{assigned}</td>'
            f'<td style="font-size:10px;color:var(--cad-text3);">{h.updated_at[:10]}</td>'
            f'</tr>'
        )

    pipe_section = (
        f'<div class="cad-card">'
        f'<h2>Pipeline Assignments</h2>'
        + (f'<table class="cad-table"><thead><tr>'
           f'<th>Hospital</th><th>Stage</th><th>Owner</th><th>Updated</th>'
           f'</tr></thead><tbody>{pipe_rows}</tbody></table>'
           if pipe_rows else
           '<p style="color:var(--cad-text3);font-size:12px;">No pipeline hospitals.</p>') +
        f'</div>'
    )

    # Nav
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/pipeline" class="cad-btn cad-btn-primary" style="text-decoration:none;">Pipeline</a>'
        f'<a href="/portfolio/monitor" class="cad-btn" style="text-decoration:none;">Portfolio Monitor</a>'
        f'<a href="/home" class="cad-btn" style="text-decoration:none;">Home</a>'
        f'</div>'
    )

    body = (
        f'{kpis}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div>{feed_section}</div><div>{pipe_section}</div></div>'
        f'{nav}'
    )

    return chartis_shell(
        body, "Team",
        active_nav="/pipeline",
        subtitle=f"{len(actors)} members | {len(activity)} actions | {n_hospitals} pipeline deals",
    )
