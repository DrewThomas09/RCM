"""Portfolio-wide alert review page (/alerts).

Phase 2 migration of the inline ``_route_alerts`` body in
``rcm_mc/server.py`` to a dedicated chartis_shell renderer. Logic is
preserved verbatim — same alert ordering (red → amber → info), same
ack/snooze form, same owner filter, same active/all toggle.

Module exposes a single entry point:

    render_alerts(store, *, show_all, owner_filter) -> str

Returns a full HTML string ready for ``_send_html``. Caller is
responsible for parsing the query string and constructing the
``store`` (the route handler in ``server.py`` does both).
"""
from __future__ import annotations

import html
import urllib.parse
from typing import Dict, List, Optional

from ..alerts.alerts import evaluate_active, evaluate_all
from ..alerts.alert_acks import trigger_key_for
from ..alerts.alert_history import age_hint
from ..deals.deal_owners import deals_by_owner
from ..portfolio.store import PortfolioStore
from ._chartis_kit import chartis_shell


_SEV_META = {
    "red":   ("badge-red",   "RED"),
    "amber": ("badge-amber", "AMBER"),
    "info":  ("badge-blue",  "INFO"),
}


def _toggle_link(show_all: bool, owner_filter: Optional[str]) -> str:
    base_qs: Dict[str, str] = {}
    if owner_filter:
        base_qs["owner"] = owner_filter
    if show_all:
        href = "/alerts" + (
            "?" + urllib.parse.urlencode(base_qs) if base_qs else ""
        )
        label = "← active only"
    else:
        toggle_qs = dict(base_qs, show="all")
        href = "/alerts?" + urllib.parse.urlencode(toggle_qs)
        label = "show acked / all →"
    return (
        f'<a href="{href}" style="color: var(--accent); '
        f'font-size: 0.85rem;">{label}</a>'
    )


def _owner_form(show_all: bool, owner_filter: Optional[str]) -> str:
    return (
        f'<form method="GET" action="/alerts" '
        f'style="display: inline-flex; gap: 0.3rem; align-items: center; '
        f'font-size: 0.85rem; margin-bottom: 0.75rem;">'
        f'<label class="muted">Owner</label>'
        f'<input type="text" name="owner" '
        f'value="{html.escape(owner_filter or "")}" '
        f'placeholder="e.g. AT" maxlength="40" '
        f'style="font-size: 0.85rem; padding: 0.15rem; width: 6rem;">'
        f'{"<input type=hidden name=show value=all>" if show_all else ""}'
        f'<button type="submit" class="btn" '
        f'style="font-size: 0.85rem; padding: 0.15rem 0.6rem;">Filter</button>'
        f'{"<a href=/alerts style=color:var(--accent);font-size:0.85rem;margin-left:0.5rem;>× clear</a>" if owner_filter else ""}'
        f'</form>'
    )


def _row(a) -> str:
    cls, label = _SEV_META.get(a.severity, ("badge-blue", a.severity.upper()))
    tk = trigger_key_for(a)
    age = age_hint(a.first_seen_at)
    age_span = (
        f'<span class="muted" style="font-size: 0.75rem;">'
        f'seen {html.escape(age)}</span>' if age else ""
    )
    ack_form = (
        f'<form method="POST" action="/api/alerts/ack" '
        f'style="display: inline-flex; gap: 0.3rem; '
        f'align-items: center; margin-left: 1rem;">'
        f'<input type="hidden" name="kind" value="{html.escape(a.kind)}">'
        f'<input type="hidden" name="deal_id" value="{html.escape(a.deal_id)}">'
        f'<input type="hidden" name="trigger_key" value="{html.escape(tk)}">'
        f'<select name="snooze_days" '
        f'style="font-size: 0.75rem; padding: 0.1rem;">'
        f'<option value="0">Ack (until state changes)</option>'
        f'<option value="7">Snooze 7d</option>'
        f'<option value="30">Snooze 30d</option>'
        f'</select>'
        f'<button type="submit" class="btn" '
        f'style="font-size: 0.75rem; padding: 0.15rem 0.5rem;">'
        f'Ack</button>'
        f'</form>'
    )
    returning_badge = (
        '<span class="badge badge-amber" '
        'style="font-size: 0.7rem;" '
        'title="Returned after snooze expired">'
        '↩ returning</span>'
        if getattr(a, "returning", False) else ""
    )
    return (
        f'<li style="padding: 0.6rem 0; '
        f'border-bottom: 1px solid var(--border);">'
        f'<div style="display: flex; gap: 0.5rem; '
        f'align-items: center; flex-wrap: wrap;">'
        f'<span class="badge {cls}">{label}</span>'
        f'{returning_badge}'
        f'<a href="/deal/{urllib.parse.quote(a.deal_id)}" '
        f'style="color: var(--accent); text-decoration: none; '
        f'font-weight: 600;">{html.escape(a.deal_id)}</a>'
        f'<span style="color: var(--text);">— '
        f'{html.escape(a.title)}</span>'
        f'{age_span}'
        f'{ack_form}'
        f'</div>'
        f'<div class="muted" style="font-size: 0.85rem; '
        f'margin-top: 0.2rem; margin-left: 1rem;">'
        f'{html.escape(a.detail)}</div>'
        f'</li>'
    )


def render_alerts(
    store: PortfolioStore,
    *,
    show_all: bool = False,
    owner_filter: Optional[str] = None,
) -> str:
    """Full HTML for /alerts via chartis_shell.

    Migrated from ``server._route_alerts`` (Phase 2). Behavior is
    unchanged: red → amber → info ordering, ack/snooze POST form,
    optional owner filter, active/all toggle.
    """
    alerts = evaluate_all(store) if show_all else evaluate_active(store)
    if owner_filter:
        try:
            scope = set(deals_by_owner(store, owner_filter))
        except ValueError:
            scope = set()
        alerts = [a for a in alerts if a.deal_id in scope]

    toggle = _toggle_link(show_all, owner_filter)
    owner_form = _owner_form(show_all, owner_filter)

    if not alerts:
        # html.escape the user-supplied owner filter before reflecting
        # it into the empty-state copy. Pre-migration the inline route
        # used f"{owner_filter!r}" which is Python repr — not safe for
        # HTML and bypassed the global escape contract.
        scope_prefix = (
            f"No '{html.escape(owner_filter)}' " if owner_filter
            else "No active "
        )
        body = (
            f"{owner_form}"
            '<div class="card">'
            '<p style="color: var(--green-text); font-weight: 600;">'
            f'{scope_prefix}alerts. Portfolio looks clean.</p>'
            '<p class="muted" style="font-size: 0.85rem;">'
            'Evaluators run on every page load. They check covenant '
            'status, latest-quarter EBITDA variance, concerning-signal '
            'clusters, and stage regress. Acked alerts are hidden until '
            'their underlying state changes or snooze expires.'
            f'</p><p>{toggle}</p></div>'
        )
    else:
        grouped: Dict[str, List] = {"red": [], "amber": [], "info": []}
        for a in alerts:
            grouped.setdefault(a.severity, []).append(a)
        blocks: List[str] = []
        for sev in ("red", "amber", "info"):
            bucket = grouped.get(sev) or []
            if not bucket:
                continue
            _, label = _SEV_META[sev]
            rows = "".join(_row(a) for a in bucket)
            blocks.append(
                f'<div class="card"><h2>{label} ({len(bucket)})</h2>'
                f'<ul style="list-style: none; padding: 0; margin: 0;">'
                f'{rows}</ul></div>'
            )
        blocks.append(f'<p style="margin-top: 1rem;">{toggle}</p>')
        body = owner_form + "".join(blocks)

    subtitle = (
        f"{len(alerts)} "
        f"{'total' if show_all else 'active'} "
        f"alert{'s' if len(alerts) != 1 else ''}"
        f"{f' · owner = {owner_filter}' if owner_filter else ''}"
    )
    return chartis_shell(body, "Alerts", subtitle=subtitle)
