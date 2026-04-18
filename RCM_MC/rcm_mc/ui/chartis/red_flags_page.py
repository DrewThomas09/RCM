"""Per-deal Red Flags — /deal/<id>/red-flags.

Focused subset of the PartnerReview surface: only the heuristic hits,
reasonableness violations, and bear-book / critical-flag output. For
the full review (narrative, archetype, regime, investability, stress
grid, white space) the partner can click through to
/deal/<id>/partner-review.

Fleshed out in the commit immediately after partner-review — this
stub wires the route safely so a user hitting /deal/<id>/red-flags
in the intervening window gets a clean placeholder instead of a 500.
"""
from __future__ import annotations

import html as _html
from typing import Any, List, Optional

from .._chartis_kit import P, chartis_shell


def render_red_flags(
    packet: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    label = deal_name or deal_id
    header_links = (
        f'<div style="margin-bottom:14px;">'
        f'<a href="/deal/{_html.escape(deal_id)}" '
        f'style="color:{P["accent"]};font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.10em;">&larr; DEAL DASHBOARD</a>'
        f'<span style="color:{P["text_faint"]};padding:0 8px;">·</span>'
        f'<a href="/deal/{_html.escape(deal_id)}/partner-review" '
        f'style="color:{P["accent"]};font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.10em;">FULL PARTNER REVIEW →</a>'
        f'</div>'
    )
    if error:
        missing = ", ".join(_html.escape(m) for m in (missing_fields or [])) or "—"
        body = header_links + (
            f'<div style="background:rgba(239,68,68,0.10);border:1px solid {P["negative"]};'
            f'border-radius:3px;padding:12px 14px;">'
            f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
            f'color:{P["negative"]};letter-spacing:0.12em;margin-bottom:4px;">'
            f'RED FLAG SCAN UNAVAILABLE</div>'
            f'<div style="color:{P["text"]};font-size:12px;">{_html.escape(error)}</div>'
            f'<div style="color:{P["text_dim"]};font-size:11px;margin-top:6px;">'
            f'Missing: {missing}</div></div>'
        )
    else:
        body = header_links + (
            f'<div class="ck-panel"><div class="ck-panel-title">Red Flag Scan</div>'
            f'<div style="padding:12px 14px;color:{P["text_dim"]};font-size:11.5px;">'
            f'This page renders a focused red-flag view in the next commit. '
            f'For now, the PE brain&rsquo;s full output — including critical and '
            f'high-severity heuristic hits, reasonableness violations, and '
            f'bear-book pattern matches — is at '
            f'<a href="/deal/{_html.escape(deal_id)}/partner-review" '
            f'style="color:{P["accent"]};">Partner Review</a>.'
            f'</div></div>'
        )
    return chartis_shell(
        body,
        title=f"Red Flags · {label}",
        active_nav="/pe-intelligence",
        subtitle=f"{label} · focused red-flag surface",
    )
