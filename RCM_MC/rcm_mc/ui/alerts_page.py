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
from ._chartis_kit import (
    chartis_shell,
    ck_affirm_empty,
    ck_arrow_link,
    ck_eyebrow,
    ck_severity_panel,
)


_SEV_META = {
    "red":   ("RED", "Critical — covenant breach, covenant tripped, "
                     "or stage regress."),
    "amber": ("AMBER", "Warning — tight covenants, EBITDA miss, or "
                       "concerning-signal cluster."),
    "info":  ("INFO", "Informational — stage advance or new note."),
}


def _toggle_link(show_all: bool, owner_filter: Optional[str]) -> str:
    base_qs: Dict[str, str] = {}
    if owner_filter:
        base_qs["owner"] = owner_filter
    if show_all:
        href = "/alerts" + (
            "?" + urllib.parse.urlencode(base_qs) if base_qs else ""
        )
        return ck_arrow_link("Show active only", href)
    toggle_qs = dict(base_qs, show="all")
    href = "/alerts?" + urllib.parse.urlencode(toggle_qs)
    return ck_arrow_link("Show acknowledged + all", href)


def _owner_form(show_all: bool, owner_filter: Optional[str]) -> str:
    """Editorial filter strip — eyebrow label + monospace input + tonal
    submit. Replaces the inline-styled form from the legacy route."""
    clear_link = (
        f'<a href="/alerts" class="ck-arrow" style="margin-left:8px;">'
        f'Clear filter</a>' if owner_filter else ""
    )
    return (
        '<form method="GET" action="/alerts" class="ck-alerts-filter" '
        'style="display:flex;align-items:center;gap:14px;'
        'padding:14px 18px;background:#fff;border:1px solid var(--sc-rule);'
        'border-radius:2px;margin:0 0 24px;box-shadow:var(--sc-shadow-1);">'
        '<span style="font-family:var(--sc-mono);font-size:11px;'
        'font-weight:600;letter-spacing:0.14em;text-transform:uppercase;'
        'color:var(--sc-text-dim);">Filter by owner</span>'
        f'<input type="text" name="owner" '
        f'value="{html.escape(owner_filter or "")}" '
        'placeholder="initials, e.g. AT" maxlength="40" '
        'style="font-family:var(--sc-mono);font-size:13px;padding:6px 10px;'
        'border:1px solid var(--sc-rule);border-radius:2px;width:14ch;">'
        f'{"<input type=\"hidden\" name=\"show\" value=\"all\">" if show_all else ""}'
        '<button type="submit" '
        'style="font-family:var(--sc-sans);font-size:12px;font-weight:600;'
        'letter-spacing:0.08em;text-transform:uppercase;padding:7px 16px;'
        'border:1px solid var(--sc-navy);background:var(--sc-navy);'
        'color:var(--sc-on-navy);border-radius:2px;cursor:pointer;">'
        'Apply</button>'
        f'{clear_link}'
        '</form>'
    )


def _row(a) -> str:
    """Editorial alert row — severity-toned panel item with deal link,
    title, age, ack form, and detail copy. Replaces the inline-styled
    ``<li>`` from the legacy route."""
    tk = trigger_key_for(a)
    age = age_hint(a.first_seen_at)
    age_html = (
        f'<span class="age">seen {html.escape(age)}</span>' if age else ""
    )
    returning_html = (
        '<span class="ck-badge tone-warning" style="font-size:10px;" '
        'title="Returned after snooze expired">↩ Returning</span>'
        if getattr(a, "returning", False) else ""
    )
    ack_form = (
        f'<form method="POST" action="/api/alerts/ack" '
        f'class="ck-severity-actions">'
        f'<input type="hidden" name="kind" value="{html.escape(a.kind)}">'
        f'<input type="hidden" name="deal_id" '
        f'value="{html.escape(a.deal_id)}">'
        f'<input type="hidden" name="trigger_key" '
        f'value="{html.escape(tk)}">'
        f'<select name="snooze_days" aria-label="Snooze duration">'
        f'<option value="0">Acknowledge — clears on state change</option>'
        f'<option value="7">Snooze for 7 days</option>'
        f'<option value="30">Snooze for 30 days</option>'
        f'</select>'
        f'<button type="submit">Acknowledge</button>'
        f'</form>'
    )
    return (
        '<li>'
        '<div class="ck-severity-row">'
        f'<a class="deal" href="/deal/{urllib.parse.quote(a.deal_id)}">'
        f'{html.escape(a.deal_id)}</a>'
        f'<span class="title">{html.escape(a.title)}</span>'
        f'{returning_html}'
        f'{age_html}'
        '</div>'
        f'<div class="ck-severity-detail">{html.escape(a.detail)}</div>'
        f'{ack_form}'
        '</li>'
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

    intro = (
        '<div style="margin:0 0 24px;">'
        f'{ck_eyebrow("Portfolio alerts")}'
        '<h1 style="font-family:var(--sc-serif);font-weight:400;'
        'font-size:clamp(28px, 3.4vw, 40px);line-height:1.1;'
        'letter-spacing:-0.015em;color:var(--sc-navy);'
        'margin:12px 0 0;">Where the portfolio needs attention</h1>'
        '<p style="font-family:var(--sc-serif);font-size:17px;'
        'line-height:1.6;color:var(--sc-text-dim);margin-top:12px;'
        'max-width:62ch;">Evaluators run on every page load. They '
        'check covenant headroom, latest-quarter EBITDA variance, '
        'concerning-signal clusters, and stage regress. Acknowledged '
        'alerts hide until the underlying state changes or the '
        'snooze expires.</p>'
        '</div>'
    )

    if not alerts:
        if owner_filter:
            empty_headline = (
                f"No alerts for owner '{html.escape(owner_filter)}'"
            )
            empty_body = (
                "Either this owner has no deals assigned, or the deals "
                "they own are all clean. Try clearing the filter to "
                "see the full portfolio view."
            )
        else:
            empty_headline = "Portfolio is clean"
            empty_body = (
                "Zero active alerts across the portfolio. "
                "All covenants in headroom, no quarterly misses outside "
                "tolerance, no concerning-signal clusters."
            )
        if show_all:
            cta_text = "Show active only"
            cta_href = "/alerts" + (
                f"?owner={urllib.parse.quote(owner_filter)}"
                if owner_filter else ""
            )
        else:
            cta_text = "Show acknowledged + all"
            qs = {"show": "all"}
            if owner_filter:
                qs["owner"] = owner_filter
            cta_href = "/alerts?" + urllib.parse.urlencode(qs)
        body = (
            intro
            + owner_form
            + ck_affirm_empty(
                headline=empty_headline,
                body=empty_body,
                cta_text=cta_text,
                cta_href=cta_href,
            )
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
            label, _description = _SEV_META[sev]
            rows = "".join(_row(a) for a in bucket)
            blocks.append(ck_severity_panel(
                tone=sev, label=label, count=len(bucket), rows_html=rows,
            ))
        blocks.append(
            f'<p style="margin-top:24px;">{toggle}</p>'
        )
        body = intro + owner_form + "".join(blocks)

    subtitle = (
        f"{len(alerts)} "
        f"{'total' if show_all else 'active'} "
        f"alert{'s' if len(alerts) != 1 else ''}"
        f"{f' · owner = {html.escape(owner_filter)}' if owner_filter else ''}"
    )
    return chartis_shell(body, "Alerts", subtitle=subtitle)
