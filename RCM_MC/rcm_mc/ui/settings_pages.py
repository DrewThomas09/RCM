"""Settings pages: custom KPIs, automations, integrations.

Route: GET /settings/custom-kpis, /settings/automations, /settings/integrations.
All use shell_v2 for consistent SeekingChartis branding.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from .shell_v2 import shell_v2
from .brand import PALETTE


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def render_custom_kpis_page(store: Any) -> str:
    from ..domain.custom_metrics import list_custom_metrics

    try:
        metrics = list_custom_metrics(store)
    except Exception:
        metrics = []
    rows = ""
    for m in metrics:
        mk = getattr(m, "metric_key", "") if hasattr(m, "metric_key") else m.get("metric_key", "")
        dn = getattr(m, "display_name", "") if hasattr(m, "display_name") else m.get("display_name", "")
        un = getattr(m, "unit", "") if hasattr(m, "unit") else m.get("unit", "")
        dr = getattr(m, "directionality", "") if hasattr(m, "directionality") else m.get("directionality", "")
        ca = getattr(m, "category", "") if hasattr(m, "category") else m.get("category", "")
        rows += (
            f'<tr><td>{_esc(mk)}</td>'
            f'<td>{_esc(dn)}</td>'
            f'<td>{_esc(un)}</td>'
            f'<td>{_esc(dr)}</td>'
            f'<td>{_esc(ca)}</td></tr>'
        )
    table = (
        '<table class="cad-table">'
        '<thead><tr><th>Key</th>'
        '<th>Display Name</th><th>Unit</th><th>Direction</th><th>Category</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        if rows else f'<p style="color:{PALETTE["text_muted"]};">No custom KPIs defined yet. Use the API to create one.</p>'
        f'<a href="/api/metrics/custom" class="cad-btn" style="text-decoration:none;margin-top:8px;display:inline-block;">API Reference &rarr;</a>'
    )
    body = (
        f'<div class="cad-card">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Define custom metrics your fund tracks beyond the 38-metric registry.</p>'
        f'{table}'
        f'<div style="margin-top:16px;">'
        f'<a href="/api/metrics/custom" class="cad-btn" style="text-decoration:none;">'
        f'API: GET /api/metrics/custom</a></div></div>'
    )
    return shell_v2(body, "Custom KPIs", active_nav="/settings",
                    subtitle="Define custom metrics for your fund")


def render_automations_page(store: Any) -> str:
    from ..infra.automation_engine import list_rules

    try:
        rules = list_rules(store)
    except Exception:
        rules = []
    rows = ""
    for r in rules:
        def _val(obj, key):
            if hasattr(obj, key):
                return getattr(obj, key)
            if isinstance(obj, dict):
                return obj.get(key)
            return None
        active_val = _val(r, "active")
        badge_cls = "cad-badge-green" if active_val else "cad-badge-red"
        badge_text = "Active" if active_val else "Inactive"
        rows += (
            f'<tr><td>{_esc(_val(r, "name") or "")}</td>'
            f'<td>{_esc(_val(r, "trigger") or "")}</td>'
            f'<td><span class="cad-badge {badge_cls}">{badge_text}</span></td>'
            f'<td>{_esc(_val(r, "created_by") or "system")}</td></tr>'
        )
    table = (
        '<table class="cad-table">'
        '<thead><tr><th>Rule</th>'
        '<th>Trigger</th><th>Status</th><th>Created By</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        if rows else f'<p style="color:{PALETTE["text_muted"]};">No automation rules configured.</p>'
    )
    body = (
        f'<div class="cad-card">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'When-this-then-that rules that execute automatically on deal events.</p>'
        f'{table}'
        f'<div style="margin-top:16px;">'
        f'<a href="/api/automations" class="cad-btn" style="text-decoration:none;">'
        f'API: GET /api/automations</a></div></div>'
    )
    return shell_v2(body, "Automation Rules", active_nav="/settings",
                    subtitle="Event-driven workflow automation")


def _render_webhook_deliveries(store: Any) -> str:
    try:
        from ..infra.webhooks import _ensure_tables, list_webhooks
        _ensure_tables(store)
        with store.connect() as con:
            deliveries = con.execute(
                "SELECT d.id, w.url, d.event_type, d.status_code, "
                "d.attempts, d.delivered_at, d.error "
                "FROM webhook_deliveries d "
                "LEFT JOIN webhooks w ON w.id = d.webhook_id "
                "ORDER BY d.id DESC LIMIT 20",
            ).fetchall()
    except Exception:
        return ""
    if not deliveries:
        return ""
    rows = ""
    for d in deliveries:
        code = d["status_code"] or 0
        ok = 200 <= code < 300
        badge_cls = "cad-badge-green" if ok else "cad-badge-red"
        url_short = _esc(str(d["url"] or "")[:40])
        ts = _esc(str(d["delivered_at"] or "")[:19])
        err = _esc(str(d["error"] or "")[:60])
        rows += (
            f'<tr><td>{url_short}</td>'
            f'<td>{_esc(d["event_type"] or "")}</td>'
            f'<td><span class="cad-badge {badge_cls}">{code or "ERR"}</span></td>'
            f'<td class="num" style="font-size:11px;">{ts}</td>'
            f'<td style="font-size:11px;color:{PALETTE["text_muted"]};">{err}</td></tr>'
        )
    return (
        f'<div class="cad-card" style="margin-top:16px;">'
        f'<h2>Recent Webhook Deliveries</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>URL</th><th>Event</th><th>Status</th><th>Time</th><th>Error</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def render_integrations_page(store: Any) -> str:
    from ..integrations.integration_hub import list_integrations
    from ..infra.webhooks import list_webhooks

    try:
        configs = list_integrations(store)
    except Exception:
        configs = []
    rows = ""
    for c in configs:
        active = c.get("active")
        badge_cls = "cad-badge-green" if active else "cad-badge-muted"
        badge_text = "Active" if active else "Inactive"
        rows += (
            f'<tr><td>{_esc(c.get("provider") or "")}</td>'
            f'<td><span class="cad-badge {badge_cls}">{badge_text}</span></td>'
            f'<td class="num" style="font-size:11px;">'
            f'{_esc(str(c.get("created_at") or "")[:19])}</td></tr>'
        )
    int_table = (
        '<table class="cad-table">'
        '<thead><tr><th>Provider</th><th>Status</th><th>Created</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        if rows else f'<p style="color:{PALETTE["text_muted"]};">No integrations configured.</p>'
    )

    try:
        webhooks = list_webhooks(store)
    except Exception:
        webhooks = []
    wh_rows = ""
    for w in webhooks:
        events = _esc(str(w.get("events") or ""))
        active = w.get("active", 0)
        badge_cls = "cad-badge-green" if active else "cad-badge-red"
        badge_text = "Active" if active else "Off"
        wh_rows += (
            f'<tr><td>{_esc(str(w.get("url") or "")[:50])}</td>'
            f'<td>{events}</td>'
            f'<td><span class="cad-badge {badge_cls}">{badge_text}</span></td>'
            f'<td class="num" style="font-size:11px;">'
            f'{_esc(str(w.get("created_at") or "")[:19])}</td></tr>'
        )
    wh_table = (
        f'<div class="cad-card" style="margin-top:16px;">'
        f'<h2>Webhooks</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>URL</th><th>Events</th><th>Status</th><th>Created</th>'
        f'</tr></thead><tbody>{wh_rows}</tbody></table></div>'
        if wh_rows else
        f'<div class="cad-card" style="margin-top:16px;">'
        f'<h2>Webhooks</h2>'
        f'<p style="color:{PALETTE["text_muted"]};">No webhooks configured.</p></div>'
    )

    delivery_log = _render_webhook_deliveries(store)

    body = (
        f'<div class="cad-card">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Connect to DealCloud, Salesforce, or Google Sheets.</p>'
        f'{int_table}</div>'
        f'{wh_table}'
        f'{delivery_log}'
        f'<div class="cad-card" style="margin-top:16px;display:flex;gap:8px;">'
        f'<a href="/api/export/portfolio.csv" class="cad-btn" style="text-decoration:none;">'
        f'Download Portfolio CSV</a>'
        f'<a href="/api/webhooks" class="cad-btn" style="text-decoration:none;">'
        f'API: GET /api/webhooks</a></div>'
    )
    return shell_v2(body, "Integrations", active_nav="/settings",
                    subtitle="Webhooks, exports & third-party connections")
