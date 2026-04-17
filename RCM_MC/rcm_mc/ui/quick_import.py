"""SeekingChartis Quick Import — create deals directly from the browser.

Renders a form that POSTs to /api/deals/import, so users never
need to use curl or edit files.
"""
from __future__ import annotations

import html
from typing import Any

from .shell_v2 import shell_v2
from .brand import PALETTE


def _field(
    name: str,
    label: str,
    *,
    placeholder: str = "",
    required: bool = False,
    type_: str = "text",
    step: str = "",
    maxlength: str = "",
) -> str:
    req = " required" if required else ""
    req_mark = ' <span style="color:var(--cad-amber);">*</span>' if required else ""
    ml = f' maxlength="{maxlength}"' if maxlength else ""
    st = f' step="{step}"' if step else ""
    return (
        f'<div class="cad-field">'
        f'<label>{html.escape(label)}{req_mark}</label>'
        f'<input class="cad-input" type="{type_}" name="{name}" '
        f'placeholder="{html.escape(placeholder)}"{req}{st}{ml}>'
        f'</div>'
    )


def render_quick_import(success_msg: str = "", error_msg: str = "") -> str:
    """Render the quick import form page."""

    alert = ""
    if success_msg:
        alert = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["positive"]};'
            f'padding:10px 14px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<span class="cad-section-code" style="color:{PALETTE["positive"]};'
            f'border-color:{PALETTE["positive"]};">OK</span>'
            f'<p style="margin:0;color:{PALETTE["positive"]};font-family:var(--cad-mono);'
            f'font-size:11.5px;letter-spacing:0.04em;text-transform:uppercase;">'
            f'{html.escape(success_msg)}</p></div></div>'
        )
    if error_msg:
        alert = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["negative"]};'
            f'padding:10px 14px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<span class="cad-section-code" style="color:{PALETTE["negative"]};'
            f'border-color:{PALETTE["negative"]};">ERR</span>'
            f'<p style="margin:0;color:{PALETTE["negative"]};font-family:var(--cad-mono);'
            f'font-size:11.5px;letter-spacing:0.04em;text-transform:uppercase;">'
            f'{html.escape(error_msg)}</p></div></div>'
        )

    # Required section
    required_fields = (
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h3 style="margin:0;font-size:11.5px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">Required Identity</h3>'
        f'<span class="cad-section-code">IDN</span></div>'
        f'<div class="cad-form-row" style="margin-bottom:18px;">'
        + _field("deal_id", "Deal ID", placeholder="e.g. southeast_health", required=True)
        + _field("name", "Hospital Name", placeholder="e.g. Southeast Health Medical Ctr", required=True)
        + '</div>'
    )

    rcm_fields = (
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h3 style="margin:0;font-size:11.5px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">RCM Metrics</h3>'
        f'<span class="cad-section-code">RCM</span>'
        f'<span style="font-family:var(--cad-mono);font-size:9.5px;'
        f'letter-spacing:0.1em;color:{PALETTE["text_muted"]};text-transform:uppercase;">Optional</span>'
        f'</div>'
        f'<div class="cad-form-row" style="margin-bottom:18px;">'
        + _field("denial_rate", "Denial Rate (%)", placeholder="14.2", type_="number", step="0.1")
        + _field("days_in_ar", "Days in AR", placeholder="52", type_="number", step="1")
        + _field("net_collection_rate", "Net Collection (%)", placeholder="94.5", type_="number", step="0.1")
        + _field("clean_claim_rate", "Clean Claim (%)", placeholder="88", type_="number", step="0.1")
        + _field("cost_to_collect", "Cost to Collect (%)", placeholder="5.1", type_="number", step="0.1")
        + _field("claims_volume", "Claims Volume", placeholder="180000", type_="number", step="1000")
        + '</div>'
    )

    fin_fields = (
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h3 style="margin:0;font-size:11.5px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">Financial Metrics</h3>'
        f'<span class="cad-section-code">FIN</span>'
        f'<span style="font-family:var(--cad-mono);font-size:9.5px;'
        f'letter-spacing:0.1em;color:{PALETTE["text_muted"]};text-transform:uppercase;">Optional</span>'
        f'</div>'
        f'<div class="cad-form-row" style="margin-bottom:18px;">'
        + _field("net_revenue", "Net Revenue ($)", placeholder="386000000", type_="number", step="1000000")
        + _field("bed_count", "Bed Count", placeholder="332", type_="number", step="1")
        + _field("state", "State", placeholder="AL", maxlength="2")
        + '</div>'
    )

    form = (
        f'{alert}'
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">New Deal</h2>'
        f'<span class="cad-section-code">IMP</span></div>'
        f'<p style="font-family:var(--cad-mono);font-size:10.5px;'
        f'letter-spacing:0.04em;color:{PALETTE["text_muted"]};'
        f'text-transform:uppercase;margin-bottom:16px;">'
        f'Only Deal ID and Name required · more fields = richer analysis</p>'
        f'<form method="POST" action="/quick-import" id="quick-import-form">'
        + required_fields
        + rcm_fields
        + fin_fields
        + '<div style="display:flex;gap:8px;padding-top:12px;'
          f'border-top:1px solid {PALETTE["border"]};">'
        + '<button type="submit" class="cad-btn cad-btn-primary">Create Deal &rarr;</button>'
        + '<a href="/portfolio" class="cad-btn" style="text-decoration:none;">Cancel</a>'
        + '</div>'
        + '</form></div>'

        # JSON bulk-import
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Bulk Import</h2>'
        f'<span class="cad-section-code">JSON</span></div>'
        f'<p style="font-family:var(--cad-mono);font-size:10.5px;'
        f'letter-spacing:0.04em;color:{PALETTE["text_muted"]};'
        f'text-transform:uppercase;margin-bottom:12px;">'
        f'Paste a JSON array of deals to import multiple at once</p>'
        f'<form method="POST" action="/quick-import-json">'
        f'<textarea name="json_data" rows="8" class="cad-input" '
        f'placeholder=\'[{{"deal_id": "southeast", "name": "Southeast Health", '
        f'"profile": {{"denial_rate": 14.2, "days_in_ar": 52, "net_revenue": 386000000}}}}]\' '
        f'style="width:100%;resize:vertical;line-height:1.5;"></textarea>'
        f'<div style="display:flex;gap:8px;margin-top:10px;">'
        f'<button type="submit" class="cad-btn cad-btn-primary">Import JSON &rarr;</button>'
        f'<a href="/api/docs" class="cad-btn" style="text-decoration:none;">Schema Docs</a>'
        f'</div></form></div>'
    )

    return shell_v2(
        form, "Import Deals",
        subtitle="Create deals directly in your browser",
    )
