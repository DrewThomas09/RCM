"""Pressure Test page renderer — chartis_shell version."""
from __future__ import annotations

import html
from typing import Any, List, Optional

import pandas as pd

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def render_pressure_page(
    deals: pd.DataFrame,
    selected_deal_id: str = "",
    packet: Any = None,
) -> str:
    options = ""
    if not deals.empty and "deal_id" in deals.columns:
        for _, r in deals.iterrows():
            did = html.escape(str(r.get("deal_id", "")))
            nm = html.escape(str(r.get("name", did)))
            sel = " selected" if did == selected_deal_id else ""
            options += f'<option value="{did}"{sel}>{nm}</option>'

    form = (
        f'<div class="cad-card">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Select a deal to view risk flags and EBITDA pressure analysis.</p>'
        f'<form method="GET" action="/pressure" style="display:flex;gap:8px;align-items:center;">'
        f'<select name="deal_id" style="padding:7px 12px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;'
        f'min-width:250px;">'
        f'<option value="">— select deal —</option>'
        f'{options}</select>'
        f'<button type="submit" class="cad-btn cad-btn-primary">Analyze</button>'
        f'</form></div>'
    )

    results_html = ""
    if packet is not None:
        risk_count = len(packet.risk_flags) if packet.risk_flags else 0
        bridge = packet.ebitda_bridge
        impact = bridge.total_ebitda_impact if bridge else 0

        results_html = (
            f'<div class="cad-kpi-grid">'
            f'<div class="cad-kpi"><div class="cad-kpi-value">'
            f'{html.escape(packet.deal_name or selected_deal_id)}</div>'
            f'<div class="cad-kpi-label">Deal</div></div>'
            f'<div class="cad-kpi"><div class="cad-kpi-value">{risk_count}</div>'
            f'<div class="cad-kpi-label">Risk Flags</div></div>'
            f'<div class="cad-kpi"><div class="cad-kpi-value">${impact/1e6:.1f}M</div>'
            f'<div class="cad-kpi-label">EBITDA Impact</div></div>'
            f'</div>'
        )

        if packet.risk_flags:
            flag_rows = ""
            for rf in packet.risk_flags[:20]:
                sev = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
                badge_cls = {
                    "critical": "cad-badge-red",
                    "high": "cad-badge-amber",
                    "medium": "cad-badge-blue",
                }.get(sev, "cad-badge-muted")
                explanation = getattr(rf, "explanation", "") or getattr(rf, "detail", "")
                flag_rows += (
                    f'<tr>'
                    f'<td><span class="cad-badge {badge_cls}">{html.escape(sev)}</span></td>'
                    f'<td>{html.escape(explanation)}</td>'
                    f'</tr>'
                )
            results_html += (
                f'<div class="cad-card">'
                f'<h2>Risk Flags</h2>'
                f'<table class="cad-table"><thead><tr>'
                f'<th>Severity</th><th>Description</th>'
                f'</tr></thead><tbody>{flag_rows}</tbody></table></div>'
            )

        results_html += (
            f'<div class="cad-card" style="display:flex;gap:8px;">'
            f'<a href="/analysis/{html.escape(selected_deal_id)}" class="cad-btn cad-btn-primary" '
            f'style="text-decoration:none;">Full Analysis</a>'
            f'<a href="/api/deals/{html.escape(selected_deal_id)}/market" class="cad-btn" '
            f'style="text-decoration:none;">Market Analysis</a>'
            f'<a href="/api/deals/{html.escape(selected_deal_id)}/denial-drivers" class="cad-btn" '
            f'style="text-decoration:none;">Denial Drivers</a></div>'
        )

    body = f'{form}{results_html}'

    subtitle = f"Pressure test: {selected_deal_id}" if selected_deal_id else "Stress scenarios with risk flags"
    return chartis_shell(body, "Pressure Test", subtitle=subtitle)
