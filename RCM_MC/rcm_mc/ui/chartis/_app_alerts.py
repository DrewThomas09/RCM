"""Alerts — stacked alert cards + paired triage table.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.10
Reference: docs/design-handoff/reference/04-command-center.html (alerts section)

Stacked alert cards with tone (red / amber / info), icon, title,
description, CTA on the right. Cross-deal — does NOT filter on the
focused deal (alerts surface portfolio-level concerns).

Justification for taking ``store`` directly (per Convention #1):

  ``alerts.evaluate_active(store)`` is itself the canonical aggregate
  query. Pre-computing it in the orchestrator only saves work if
  multiple helpers consume it; only this helper does. Taking ``store``
  directly is the right shape — alternatively, the orchestrator could
  compute alerts once and pass them in, but that adds a kwarg with
  no perf benefit since the call is single-use.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

Empty / sparse states (per Phase 2 review):
  - Zero active alerts → editorial "All clear" affirmative state with
    green hairline (NOT a hidden block — affirmative emptiness is a
    feature). Wording: "No active alerts. Last evaluated <timestamp>."
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui._chartis_kit_editorial import pair_block


_TONE_ICONS: Dict[str, str] = {
    "red": "✕",
    "amber": "▲",
    "info": "ℹ",
}


def _alert_cta_for(alert: Any) -> Optional[Dict[str, str]]:
    """Map an alert kind to a CTA. Returns None for kinds without one."""
    kind = getattr(alert, "kind", "") or ""
    deal_id = getattr(alert, "deal_id", "") or ""
    # Conservative subset of named CTAs from spec §9 deep-link table.
    # Phase 2 wires the obvious ones; future kinds get default "Open deal".
    if kind == "covenant_tripped":
        return {
            "label": "Open Variance →",
            "href": f"/app?deal={_html.escape(deal_id)}&ui=v3",
        }
    if kind in ("plan_drift", "lagging_initiative"):
        return {
            "label": "Inspect Playbook →",
            "href": f"/app?deal={_html.escape(deal_id)}&ui=v3",
        }
    if kind in ("source_stale", "ingest_error"):
        return {
            "label": "View Source →",
            "href": "/diligence/ingest",
        }
    if deal_id:
        return {
            "label": "Open Deal →",
            "href": f"/app?deal={_html.escape(deal_id)}&ui=v3",
        }
    return None


def _render_alert_card(alert: Any) -> str:
    severity = getattr(alert, "severity", "info") or "info"
    if severity not in _TONE_ICONS:
        severity = "info"
    icon = _TONE_ICONS[severity]
    title = str(getattr(alert, "title", "") or "")
    detail = str(getattr(alert, "detail", "") or "")
    deal_id = str(getattr(alert, "deal_id", "") or "")
    cta = _alert_cta_for(alert)
    cta_html = (
        f'<a class="cta" href="{cta["href"]}">{cta["label"]}</a>'
        if cta else ""
    )
    meta_html = ""
    if deal_id:
        meta_html = (
            f'<div class="meta">{_html.escape(deal_id)}</div>'
        )
    return (
        f'<div class="app-alert {severity}">'
        f'<div class="ico">{icon}</div>'
        '<div class="body">'
        f'<div class="title">{_html.escape(title)}</div>'
        f'<div class="desc">{_html.escape(detail)}</div>'
        f'{meta_html}'
        '</div>'
        f'{cta_html}'
        '</div>'
    )


def _render_triage_table(alerts: List[Any]) -> str:
    """Paired right-side: red / amber / info counts."""
    red = sum(1 for a in alerts if getattr(a, "severity", "") == "red")
    amber = sum(1 for a in alerts if getattr(a, "severity", "") == "amber")
    info = sum(1 for a in alerts if getattr(a, "severity", "") == "info")
    body = (
        f'<tr><td class="lbl">Red — immediate</td>'
        f'<td class="r">{red}</td></tr>'
        f'<tr><td class="lbl">Amber — monitor</td>'
        f'<td class="r">{amber}</td></tr>'
        f'<tr><td class="lbl">Info — context</td>'
        f'<td class="r">{info}</td></tr>'
    )
    return (
        '<table>'
        '<thead><tr><th>Severity</th><th class="r">Count</th></tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table>'
    )


def render_alerts(store: PortfolioStore) -> str:
    """Stacked alert cards + paired triage-counts table.

    Args:
        store: PortfolioStore handle. (Per Convention #1: justified
            because alerts.evaluate_active() is itself the canonical
            aggregate query.)
    """
    try:
        from rcm_mc.alerts.alerts import evaluate_active
        alerts = evaluate_active(store) or []
    except Exception:  # noqa: BLE001 — alerts must never break the page
        alerts = []

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if not alerts:
        viz_html = (
            '<div class="app-alerts-clear">'
            '<strong style="font-style:normal;color:var(--green);">'
            'All clear.</strong> No active alerts. '
            f'Last evaluated <span class="mono" style="color:var(--green);'
            f'font-style:normal;font-size:.85em">{_html.escape(now_iso)}</span>.'
            '</div>'
        )
    else:
        cards = "".join(_render_alert_card(a) for a in alerts)
        viz_html = f'<div class="app-alerts">{cards}</div>'

    return pair_block(
        viz_html,
        label="ACTIVE ALERTS · CROSS-DEAL",
        source="alerts",
        data_table=_render_triage_table(alerts),
    )
