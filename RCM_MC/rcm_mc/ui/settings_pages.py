"""Settings pages: custom KPIs, automations, integrations.

Route: GET /settings/custom-kpis, /settings/automations, /settings/integrations.
All use chartis_shell for consistent PE Desk branding.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_provenance_tooltip,
)
from .brand import PALETTE


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def render_workspace_mode_page() -> str:
    """Settings page: choose the workspace mode (audience framing).

    Two cards — PE Partner (fund-level deal operations) and Chartis
    Consulting (commercial diligence for client engagements). The
    selected card POSTs to /settings/workspace which sets the
    ck_workspace_mode cookie; the whole platform's copy then swaps
    via ui._workspace_mode.term().
    """
    from ._chartis_kit import ck_page_title
    from ._workspace_mode import (
        current_workspace_mode, MODE_LABELS, MODE_TAGLINES,
        PARTNER, CONSULTING,
    )

    active = current_workspace_mode()

    def _card(mode: str, summary: str, bullets: List[str]) -> str:
        is_active = mode == active
        radio = "&#9679;" if is_active else "&#9675;"  # ● / ○
        active_cls = " ws-card-active" if is_active else ""
        bullets_html = "".join(
            f'<li>{_esc(b)}</li>' for b in bullets
        )
        return (
            f'<form method="POST" action="/settings/workspace" '
            f'class="ws-card-form">'
            f'<input type="hidden" name="mode" value="{_esc(mode)}">'
            f'<button type="submit" class="ws-card{active_cls}">'
            f'<div class="ws-card-head">'
            f'<span class="ws-radio">{radio}</span>'
            f'<span class="ws-card-label">{_esc(MODE_LABELS[mode])}</span>'
            + ('<span class="ws-badge">ACTIVE</span>' if is_active else '')
            + '</div>'
            f'<div class="ws-card-tagline">&ldquo;{_esc(MODE_TAGLINES[mode])}&rdquo;</div>'
            f'<div class="ws-card-summary">{_esc(summary)}</div>'
            f'<ul class="ws-card-bullets">{bullets_html}</ul>'
            f'</button></form>'
        )

    cards = (
        _card(
            PARTNER,
            "The fund-level operating view. Deals, sponsors, IC memos, "
            "MOIC / IRR / covenant math, and portfolio operations.",
            ["Deal profiles + IC memos", "Portfolio operations + alerts",
             "Returns math (MOIC / IRR / covenants)"],
        )
        + _card(
            CONSULTING,
            "The commercial-diligence consulting view. Client engagements, "
            "target profiles, market sizing, and source-backed readouts.",
            ["Engagement profiles + diligence readouts",
             "Market + competitive + customer intelligence",
             "Client briefings replace LP updates"],
        )
    )

    styles = (
        '<style>'
        '.ws-grid{display:grid;grid-template-columns:repeat(auto-fit,'
        'minmax(320px,1fr));gap:18px;margin:8px 0 24px;}'
        '.ws-card-form{margin:0;}'
        '.ws-card{display:block;width:100%;text-align:left;cursor:pointer;'
        'background:#FAF7F0;border:1px solid #D6CFC0;border-radius:2px;'
        'padding:20px 22px;font-family:inherit;transition:border-color .18s '
        'ease,box-shadow .18s ease,transform .18s ease;}'
        '.ws-card:hover{border-color:#155752;transform:translateY(-1px);'
        'box-shadow:0 6px 16px -10px rgba(21,87,82,.45);}'
        # 2026-05-28 batch 31 · Tier-4 trope removal — drops the
        # 135° gradient on the active workspace card in favor of a
        # flat brand tint. The semantic 3px green stripe stays (it
        # marks the currently-selected workspace).
        '.ws-card-active{border-color:#155752;border-left:3px solid #155752;'
        'background:#E8F0EF;}'
        '.ws-card-head{display:flex;align-items:center;gap:10px;'
        'margin-bottom:8px;}'
        '.ws-radio{color:#155752;font-size:15px;}'
        '.ws-card-label{font-family:"Source Serif 4",Georgia,serif;'
        'font-size:1.3rem;font-weight:600;color:#0b2341;}'
        '.ws-badge{margin-left:auto;font-family:"JetBrains Mono",monospace;'
        'font-size:9.5px;font-weight:700;letter-spacing:.12em;'
        'background:#155752;color:#FAF7F0;padding:2px 8px;border-radius:2px;}'
        '.ws-card-tagline{font-family:"Source Serif 4",Georgia,serif;'
        'font-style:italic;font-size:1.02rem;color:#155752;margin-bottom:10px;}'
        '.ws-card-summary{font-family:"Inter Tight","Inter",sans-serif;'
        'font-size:.92rem;line-height:1.55;color:#5C6878;margin-bottom:10px;}'
        '.ws-card-bullets{margin:0;padding-left:18px;'
        'font-family:"Inter Tight","Inter",sans-serif;font-size:.85rem;'
        'color:#1a2332;line-height:1.7;}'
        '</style>'
    )

    title = ck_page_title(
        "Workspace Mode",
        eyebrow="SETTINGS · AUDIENCE",
        meta="Switch between the PE-partner deal view and the Chartis "
             "commercial-diligence consulting view. Changes copy and "
             "framing across the platform — not the underlying data.",
    )

    body = (
        styles
        + title
        + f'<div class="ws-grid">{cards}</div>'
        + '<p class="ck-eyebrow" style="color:#8A92A0;max-width:70ch;">'
        'This is a per-browser preference stored in a cookie. It changes '
        'vocabulary (e.g. &ldquo;Deal&rdquo; &harr; &ldquo;Engagement&rdquo;, '
        '&ldquo;Sponsor&rdquo; &harr; &ldquo;Client&rdquo;, &ldquo;IC Memo&rdquo; '
        '&harr; &ldquo;Diligence Readout&rdquo;) and not the analytics, '
        'routes, or stored records. Public marketing + login pages keep the '
        'commercial-diligence framing regardless.</p>'
    )
    return chartis_shell(body, "Workspace Mode", active_nav="/settings")


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
    # Cycle 49 — KPI strip with provenance.
    metrics_value = ck_provenance_tooltip(
        "Custom KPIs defined",
        ck_fmt_num(len(metrics)),
        explainer=(
            "Fund-specific metrics that extend the canonical "
            "38-metric registry. Each one carries a unit, "
            "directionality, and category so the platform can "
            "render it consistently across portfolio screens."
        ),
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Custom KPIs", metrics_value, "fund-defined")
        + ck_kpi_block("Built-in Registry", "38", "canonical metrics")
        + '</div>'
    )
    body = (
        ck_eyebrow("Custom KPIs")
        + kpi_strip
        + f'<div class="cad-card">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Define custom metrics your fund tracks beyond the 38-metric registry.</p>'
        f'{table}'
        f'<div style="margin-top:16px;">'
        f'<a href="/api/metrics/custom" class="cad-btn" style="text-decoration:none;">'
        f'API: GET /api/metrics/custom</a></div></div>'
        + ck_next_section(
            "Open automation rules",
            "/settings/automations",
            eyebrow="Continue —",
            italic_word="automation",
        )
    )
    return chartis_shell(body, "Custom KPIs", active_nav="/settings",
                    subtitle="Define custom metrics for your fund",
        editorial_intro={
            "eyebrow": "CUSTOM KPIS",
            "headline": "Where the fund's vocabulary expands.",
            "italic_word": "expands",
            "body": (
                "Custom KPIs that extend the canonical 38-metric "
                "registry. Each entry maps a fund-specific name "
                "to a formula and a rationale - useful when an "
                "LP report needs a metric the platform doesn't "
                "ship by default."
            ),
        })


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
        + ck_next_section(
            "Open integrations",
            "/settings/integrations",
            eyebrow="Continue —",
            italic_word="integrations",
        )
    )
    return chartis_shell(body, "Automation Rules", active_nav="/settings",
                    subtitle="Event-driven workflow automation",
        editorial_intro={
            "eyebrow": "AUTOMATION RULES",
            "headline": "Where the platform acts on its own.",
            "italic_word": "acts",
            "body": (
                "Event-driven rules that fire on alerts, deadlines, "
                "stage changes, or new analysis runs. Use these "
                "to escalate critical-severity alerts via webhook "
                "or to auto-generate IC packets when a deal hits "
                "diligence."
            ),
        })


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
        + ck_next_section(
            "Open custom KPIs",
            "/settings/custom-kpis",
            eyebrow="Continue —",
            italic_word="KPIs",
        )
    )
    return chartis_shell(body, "Integrations", active_nav="/settings",
                    subtitle="Webhooks, exports & third-party connections",
        editorial_intro={
            "eyebrow": "INTEGRATIONS",
            "headline": "Where the platform connects out.",
            "italic_word": "connects",
            "body": (
                "Webhooks, CRM connectors, and export pipelines. "
                "Use this to push deal events to DealCloud, "
                "Salesforce, or Google Sheets, or to wire a "
                "Slack channel for critical alerts."
            ),
        })
