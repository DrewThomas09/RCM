"""SeekingChartis Quick Import — create deals directly from the browser.

Renders a form that POSTs to /api/deals/import, so users never
need to use curl or edit files.
"""
from __future__ import annotations

import html
from typing import Any

from .shell_v2 import shell_v2
from .brand import PALETTE


def render_quick_import(success_msg: str = "", error_msg: str = "") -> str:
    """Render the quick import form page."""

    alert = ""
    if success_msg:
        alert = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["positive"]};">'
            f'<p style="color:{PALETTE["positive"]};font-weight:600;">'
            f'{html.escape(success_msg)}</p></div>'
        )
    if error_msg:
        alert = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["negative"]};">'
            f'<p style="color:{PALETTE["negative"]};font-weight:600;">'
            f'{html.escape(error_msg)}</p></div>'
        )

    form = (
        f'{alert}'
        f'<div class="cad-card">'
        f'<h2>Create a New Deal</h2>'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:16px;">'
        f'Fill in the fields below to create a new deal in your portfolio. '
        f'Only Deal ID and Name are required — add more fields for richer analysis.</p>'
        f'<form method="POST" action="/quick-import" id="quick-import-form">'

        # Required fields
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">'
        f'<div>'
        f'<label style="font-size:12px;color:{PALETTE["text_secondary"]};display:block;margin-bottom:4px;">'
        f'Deal ID *</label>'
        f'<input name="deal_id" required placeholder="e.g. southeast_health" '
        f'style="width:100%;padding:8px 12px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'<div>'
        f'<label style="font-size:12px;color:{PALETTE["text_secondary"]};display:block;margin-bottom:4px;">'
        f'Hospital Name *</label>'
        f'<input name="name" required placeholder="e.g. Southeast Health Medical Center" '
        f'style="width:100%;padding:8px 12px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'</div>'

        # RCM metrics
        f'<h3 style="font-size:13px;color:{PALETTE["text_secondary"]};margin-bottom:8px;'
        f'padding-bottom:4px;border-bottom:1px solid {PALETTE["border"]};">'
        f'RCM Metrics (Optional)</h3>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px;">'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Denial Rate (%)</label>'
        f'<input name="denial_rate" type="number" step="0.1" placeholder="e.g. 14.2" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Days in AR</label>'
        f'<input name="days_in_ar" type="number" step="1" placeholder="e.g. 52" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Net Collection Rate (%)</label>'
        f'<input name="net_collection_rate" type="number" step="0.1" placeholder="e.g. 94.5" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Clean Claim Rate (%)</label>'
        f'<input name="clean_claim_rate" type="number" step="0.1" placeholder="e.g. 88" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Cost to Collect (%)</label>'
        f'<input name="cost_to_collect" type="number" step="0.1" placeholder="e.g. 5.1" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Claims Volume</label>'
        f'<input name="claims_volume" type="number" step="1000" placeholder="e.g. 180000" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'</div>'

        # Financial metrics
        f'<h3 style="font-size:13px;color:{PALETTE["text_secondary"]};margin-bottom:8px;'
        f'padding-bottom:4px;border-bottom:1px solid {PALETTE["border"]};">'
        f'Financial Metrics (Optional)</h3>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px;">'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Net Revenue ($)</label>'
        f'<input name="net_revenue" type="number" step="1000000" placeholder="e.g. 386000000" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'Bed Count</label>'
        f'<input name="bed_count" type="number" step="1" placeholder="e.g. 332" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
        f'State</label>'
        f'<input name="state" maxlength="2" placeholder="e.g. AL" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        f'</div>'

        f'<div style="display:flex;gap:8px;margin-top:8px;">'
        f'<button type="submit" class="cad-btn cad-btn-primary">Create Deal</button>'
        f'<a href="/portfolio" class="cad-btn" style="text-decoration:none;">Cancel</a>'
        f'</div>'
        f'</form></div>'

        # JSON import option
        f'<div class="cad-card">'
        f'<h2>Bulk Import (JSON)</h2>'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Paste a JSON array of deals to import multiple at once.</p>'
        f'<form method="POST" action="/quick-import-json">'
        f'<textarea name="json_data" rows="8" '
        f'placeholder=\'[{{"deal_id": "southeast", "name": "Southeast Health", '
        f'"profile": {{"denial_rate": 14.2, "days_in_ar": 52, "net_revenue": 386000000}}}}]\' '
        f'style="width:100%;background:var(--cad-bg3);color:var(--cad-text);'
        f'border:1px solid var(--cad-border);padding:12px;font-family:var(--cad-mono);'
        f'font-size:12px;border-radius:6px;resize:vertical;"></textarea>'
        f'<div style="margin-top:8px;">'
        f'<button type="submit" class="cad-btn cad-btn-primary">Import JSON</button>'
        f'</div></form></div>'
    )

    return shell_v2(
        form, "Import Deals",
        subtitle="Create deals directly in your browser",
    )
