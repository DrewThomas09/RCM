"""Scenario Explorer page renderer — chartis_shell version."""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def render_scenarios_page(presets: List[Dict[str, Any]]) -> str:
    rows_html = ""
    for ps in presets:
        sid = html.escape(str(ps.get("id", "")))
        name = html.escape(str(ps.get("name", "")))
        shocks = ps.get("shocks", {})
        payers = shocks.get("payers", {})
        shock_parts = []
        for p, s in payers.items():
            mult = s.get("idr_mult", 1.0)
            color = PALETTE["negative"] if mult > 1 else PALETTE["positive"]
            shock_parts.append(
                f'<span style="color:{color};">{html.escape(p)}: IDR\u00d7{mult:.2f}</span>'
            )
        shock_desc = ", ".join(shock_parts) if shock_parts else "—"
        rows_html += (
            f'<tr><td><code style="font-size:11px;background:{PALETTE["bg_tertiary"]};'
            f'padding:2px 6px;border-radius:3px;">{sid}</code></td>'
            f'<td>{name}</td>'
            f'<td style="font-size:12px;">{shock_desc}</td></tr>'
        )
    table = (
        '<table class="cad-table"><thead><tr><th>ID</th><th>Name</th>'
        '<th>Shocks</th></tr></thead>'
        f'<tbody>{rows_html}</tbody></table>'
        if rows_html
        else f'<p style="color:{PALETTE["text_muted"]};">No preset scenarios defined.</p>'
    )
    body = (
        f'<div class="cad-card">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Preset payer policy shock scenarios. Select a deal and apply any scenario to '
        f'see how rate changes and volume drops affect EBITDA.</p>'
        f'{table}</div>'

        f'<div class="cad-card">'
        f'<h2>How Scenarios Work</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>Each scenario applies multipliers to payer-specific initial denial rates (IDR). '
        f'An IDR multiplier of 1.20 means denials increase 20% from the baseline. '
        f'Scenarios can also shock volume, reimbursement rates, and cost structure.</p>'
        f'<p style="margin-top:6px;">To test a scenario on a deal: go to '
        f'<a href="/pressure" style="color:{PALETTE["text_link"]};">Pressure Test</a>, '
        f'select your deal, and see the risk flags. Or use the '
        f'<a href="/analysis" style="color:{PALETTE["text_link"]};">Analysis Workbench</a> '
        f'Scenarios tab for custom overrides.</p>'
        f'</div></div>'

        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/pressure" class="cad-btn cad-btn-primary" style="text-decoration:none;">'
        f'Pressure Test a Deal</a>'
        f'<a href="/analysis" class="cad-btn" style="text-decoration:none;">'
        f'Analysis Workbench</a>'
        f'<a href="/models/challenge/se" class="cad-btn" style="text-decoration:none;">'
        f'Challenge Solver</a></div>'
    )
    return chartis_shell(body, "Scenario Explorer",
                    subtitle=f"{len(presets)} preset shock scenarios")
