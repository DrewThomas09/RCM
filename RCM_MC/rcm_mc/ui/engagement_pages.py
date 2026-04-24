"""HTTP page renderers for the engagement model.

Three surfaces:

- ``/engagements``            — list of active engagements (internal)
- ``/engagements/<eid>``      — engagement detail (members, deliverables,
                                 comments). Shown to internal users (PARTNER,
                                 LEAD, ANALYST).
- ``/portal/<eid>``           — client portal read-only view. Filters
                                 drafts + internal comments. Shown to
                                 CLIENT_VIEWER.

These renderers DO NOT enforce authorisation on their own — that's the
server's job via ``_auth_ok`` + engagement-role lookup. They accept the
viewer username + role so the same module renders both the internal
and the portal view; the filter logic lives in
``rcm_mc.engagement.store``.
"""
from __future__ import annotations

import html
from typing import Iterable, List, Optional

from ..engagement import (
    Comment, Deliverable, Engagement, EngagementMember, EngagementRole,
)
from ._chartis_kit import P, chartis_shell


# ── List ───────────────────────────────────────────────────────────

def render_engagement_list(
    engagements: Iterable[Engagement],
) -> str:
    rows: List[str] = []
    for e in engagements:
        rows.append(
            '<tr>'
            f'<td class="mono"><a href="/engagements/{html.escape(e.engagement_id)}" '
            f'style="color:{P["accent"]};">{html.escape(e.engagement_id)}</a></td>'
            f'<td>{html.escape(e.name)}</td>'
            f'<td>{html.escape(e.client_name)}</td>'
            f'<td>{html.escape(e.status)}</td>'
            f'<td class="mono" style="font-size:10px;color:{P["text_faint"]};">'
            f'{html.escape(e.created_at[:10])}</td>'
            '</tr>'
        )
    empty_msg = (
        f'<tr><td colspan="5" style="padding:14px;color:{P["text_faint"]};'
        f'font-style:italic;">No engagements yet. Create one from the '
        f'CLI or the API.</td></tr>'
        if not rows else ""
    )
    body = (
        f'<div style="padding:24px 0 12px 0;">'
        f'  <div style="font-size:11px;color:{P["text_faint"]};letter-spacing:.75px;'
        f'text-transform:uppercase;margin-bottom:6px;">Engagement Workspace</div>'
        f'  <div style="font-size:20px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:8px;">Engagements</div>'
        f'  <div style="font-size:13px;color:{P["text_dim"]};max-width:720px;'
        f'line-height:1.55;">Each engagement carries its own members, '
        f'deliverables, and comment stream. Client viewers use the '
        f'<code>/portal/&lt;engagement_id&gt;</code> route to see only '
        f'published deliverables.</div>'
        f'</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:12px;'
        f'margin-top:12px;">'
        f'<thead><tr style="color:{P["text_dim"]};">'
        f'<th style="text-align:left;padding:8px 10px;border-bottom:1px solid {P["border"]};">ID</th>'
        f'<th style="text-align:left;padding:8px 10px;border-bottom:1px solid {P["border"]};">Name</th>'
        f'<th style="text-align:left;padding:8px 10px;border-bottom:1px solid {P["border"]};">Client</th>'
        f'<th style="text-align:left;padding:8px 10px;border-bottom:1px solid {P["border"]};">Status</th>'
        f'<th style="text-align:left;padding:8px 10px;border-bottom:1px solid {P["border"]};">Created</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}{empty_msg}</tbody></table>'
    )
    return chartis_shell(body, "RCM Diligence — Engagements",
                         subtitle="Cross-engagement workspace")


# ── Detail (internal view) ─────────────────────────────────────────

def render_engagement_detail(
    engagement: Engagement,
    *,
    members: Iterable[EngagementMember],
    deliverables: Iterable[Deliverable],
    comments: Iterable[Comment],
    viewer_role: Optional[EngagementRole] = None,
) -> str:
    body_parts: List[str] = [
        _detail_hero(engagement),
        _members_section(members),
        _deliverables_section(deliverables, viewer_role=viewer_role),
        _comments_section(comments, viewer_role=viewer_role),
    ]
    return chartis_shell(
        "\n".join(body_parts),
        f"Engagement — {engagement.engagement_id}",
        subtitle=f"{engagement.name} · {engagement.client_name}",
    )


def _detail_hero(e: Engagement) -> str:
    status_colour = (
        P["positive"] if e.status == "ACTIVE"
        else P["text_faint"]
    )
    return (
        f'<div style="padding:24px 0 12px 0;">'
        f'  <div style="font-size:11px;color:{P["text_faint"]};letter-spacing:.75px;'
        f'text-transform:uppercase;margin-bottom:6px;">Engagement</div>'
        f'  <div style="display:flex;align-items:baseline;gap:12px;">'
        f'    <div style="font-size:22px;color:{P["text"]};font-weight:600;">'
        f'{html.escape(e.name)}</div>'
        f'    <div class="mono" style="color:{P["text_dim"]};font-size:12px;">'
        f'{html.escape(e.engagement_id)}</div>'
        f'    <div style="background:{P["panel_alt"]};color:{status_colour};'
        f'padding:2px 10px;border-radius:3px;font-size:10px;font-weight:600;'
        f'letter-spacing:.5px;text-transform:uppercase;">{html.escape(e.status)}</div>'
        f'  </div>'
        f'  <div style="font-size:12px;color:{P["text_dim"]};margin-top:4px;">'
        f'Client: {html.escape(e.client_name)}  ·  '
        f'Created {html.escape(e.created_at[:10])} by '
        f'{html.escape(e.created_by)}</div>'
        f'</div>'
    )


def _members_section(members: Iterable[EngagementMember]) -> str:
    rows: List[str] = []
    for m in members:
        role_colour = {
            EngagementRole.PARTNER:       P["accent"],
            EngagementRole.LEAD:          P["text"],
            EngagementRole.ANALYST:       P["text_dim"],
            EngagementRole.CLIENT_VIEWER: P["text_faint"],
        }.get(m.role, P["text_dim"])
        rows.append(
            '<tr>'
            f'<td class="mono">{html.escape(m.username)}</td>'
            f'<td style="color:{role_colour};font-weight:500;">'
            f'{html.escape(m.role.value)}</td>'
            f'<td class="mono" style="font-size:10px;color:{P["text_faint"]};">'
            f'{html.escape(m.added_at[:10])}</td>'
            f'<td class="mono" style="font-size:10px;color:{P["text_faint"]};">'
            f'{html.escape(m.added_by)}</td>'
            '</tr>'
        )
    empty = (
        f'<tr><td colspan="4" style="padding:10px;color:{P["text_faint"]};'
        f'font-style:italic;">No members. Add the partner + lead + '
        f'analyst before working on this engagement.</td></tr>'
        if not rows else ""
    )
    return (
        f'<h2 style="font-size:11px;letter-spacing:1px;text-transform:uppercase;'
        f'color:{P["text_dim"]};margin:28px 0 10px 0;">Members</h2>'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px;">'
        f'<thead><tr style="color:{P["text_dim"]};">'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">User</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Role</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Added</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">By</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}{empty}</tbody></table>'
    )


def _deliverables_section(
    deliverables: Iterable[Deliverable],
    *,
    viewer_role: Optional[EngagementRole] = None,
) -> str:
    rows: List[str] = []
    for d in deliverables:
        status_colour = {
            "PUBLISHED": P["positive"],
            "DRAFT":     P["warning"],
            "RETRACTED": P["negative"],
        }.get(d.status, P["text_dim"])
        pub_info = (
            f'<td class="mono" style="font-size:10px;color:{P["text_faint"]};">'
            f'{html.escape((d.published_at or "")[:10])} by '
            f'{html.escape(d.published_by or "")}</td>'
            if d.status == "PUBLISHED" else
            f'<td style="color:{P["text_faint"]};font-size:10px;">—</td>'
        )
        rows.append(
            '<tr>'
            f'<td class="mono" style="font-size:10px;color:{P["text_dim"]};">'
            f'#{d.deliverable_id}</td>'
            f'<td>{html.escape(d.title)}</td>'
            f'<td class="mono" style="font-size:10px;color:{P["text_faint"]};">'
            f'{html.escape(d.kind)}</td>'
            f'<td style="color:{status_colour};font-weight:500;">'
            f'{html.escape(d.status)}</td>'
            f'{pub_info}'
            '</tr>'
        )
    empty = (
        f'<tr><td colspan="5" style="padding:10px;color:{P["text_faint"]};'
        f'font-style:italic;">No deliverables yet.</td></tr>'
        if not rows else ""
    )
    return (
        f'<h2 style="font-size:11px;letter-spacing:1px;text-transform:uppercase;'
        f'color:{P["text_dim"]};margin:28px 0 10px 0;">Deliverables</h2>'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px;">'
        f'<thead><tr style="color:{P["text_dim"]};">'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">#</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Title</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Kind</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Status</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Published</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}{empty}</tbody></table>'
    )


def _comments_section(
    comments: Iterable[Comment],
    *,
    viewer_role: Optional[EngagementRole] = None,
) -> str:
    items: List[str] = []
    for c in comments:
        badge = ""
        if c.is_internal:
            badge = (
                f' <span style="background:rgba(245,158,11,.14);'
                f'color:{P["warning"]};padding:1px 6px;border-radius:3px;'
                f'font-size:9px;letter-spacing:.5px;text-transform:uppercase;'
                f'font-weight:600;">internal</span>'
            )
        items.append(
            f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
            f'border-radius:4px;padding:10px 14px;margin-bottom:8px;">'
            f'  <div style="display:flex;gap:8px;align-items:baseline;'
            f'font-size:11px;color:{P["text_dim"]};margin-bottom:4px;">'
            f'    <span class="mono" style="color:{P["text"]};font-weight:600;">'
            f'{html.escape(c.author)}</span>'
            f'    <span style="font-size:10px;color:{P["text_faint"]};">'
            f'{html.escape(c.posted_at[:19])}</span>'
            f'    <span style="font-size:10px;color:{P["text_faint"]};">'
            f'on {html.escape(c.target)}</span>'
            f'{badge}'
            f'  </div>'
            f'  <div style="font-size:12px;color:{P["text"]};white-space:pre-wrap;">'
            f'{html.escape(c.body)}</div>'
            f'</div>'
        )
    empty = (
        f'<div style="padding:10px;color:{P["text_faint"]};'
        f'font-style:italic;font-size:11px;">No comments yet.</div>'
        if not items else ""
    )
    return (
        f'<h2 style="font-size:11px;letter-spacing:1px;text-transform:uppercase;'
        f'color:{P["text_dim"]};margin:28px 0 10px 0;">Comments</h2>'
        f'{"".join(items)}{empty}'
    )


# ── Client portal (published-only view) ────────────────────────────

def render_client_portal(
    engagement: Engagement,
    *,
    deliverables: Iterable[Deliverable],
    comments: Iterable[Comment],
) -> str:
    """Client portal: shown to a CLIENT_VIEWER. The caller (the
    server) is expected to have already filtered drafts + internal
    comments via ``list_deliverables(viewer=...)`` /
    ``list_comments(viewer=...)`` — this renderer just draws them."""
    deliverables = list(deliverables)
    comments = list(comments)
    body = (
        f'<div style="padding:24px 0 12px 0;">'
        f'  <div style="font-size:11px;color:{P["text_faint"]};letter-spacing:.75px;'
        f'text-transform:uppercase;margin-bottom:6px;">Client Portal</div>'
        f'  <div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">{html.escape(engagement.name)}</div>'
        f'  <div style="font-size:12px;color:{P["text_dim"]};">'
        f'{html.escape(engagement.client_name)}</div>'
        f'</div>'
        f'{_deliverables_section(deliverables)}'
        f'{_comments_section(comments)}'
    )
    return chartis_shell(
        body, f"Client Portal — {engagement.name}",
        subtitle="Published deliverables",
    )
