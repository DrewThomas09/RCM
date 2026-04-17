"""SeekingChartis Deal Quick View — fallback when full analysis unavailable.

Shows deal profile data with direct links to all available models.
Used when a deal is freshly created and hasn't been through the full
analysis pipeline yet.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Optional

from .shell_v2 import shell_v2
from .brand import PALETTE


def render_deal_quick_view(
    deal_id: str,
    profile: Dict[str, Any],
    error_msg: str = "",
) -> str:
    """Render a deal overview with links to all models."""
    name = html.escape(str(profile.get("name", deal_id)))
    did = html.escape(deal_id)

    # Error banner if workbench failed
    error_html = ""
    if error_msg:
        error_html = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["warning"]};">'
            f'<p style="color:{PALETTE["warning"]};font-size:12.5px;">'
            f'Full analysis workbench unavailable: {html.escape(error_msg[:200])}</p>'
            f'<p style="color:{PALETTE["text_muted"]};font-size:12px;margin-top:4px;">'
            f'The individual models below still work. Run a full analysis to unlock the workbench.</p>'
            f'</div>'
        )

    # Profile KPIs
    kpi_fields = [
        ("Denial Rate", profile.get("denial_rate"), "%", None),
        ("Days in AR", profile.get("days_in_ar"), "", None),
        ("Net Collection", profile.get("net_collection_rate"), "%", None),
        ("Clean Claim Rate", profile.get("clean_claim_rate"), "%", None),
        ("Cost to Collect", profile.get("cost_to_collect"), "%", None),
        ("Net Revenue", profile.get("net_revenue"), "$M", 1e6),
        ("Bed Count", profile.get("bed_count"), "", None),
        ("Claims Volume", profile.get("claims_volume"), "", None),
    ]

    kpi_cards = ""
    populated = 0
    for label, val, suffix, scale in kpi_fields:
        if val is not None:
            populated += 1
            try:
                v = float(val)
                if scale:
                    display = f"${v / scale:,.0f}M"
                elif suffix == "%":
                    display = f"{v:.1f}%"
                else:
                    display = f"{v:,.0f}"
            except (TypeError, ValueError):
                display = str(val)

            kpi_cards += (
                f'<div class="cad-kpi">'
                f'<div class="cad-kpi-value">{html.escape(display)}</div>'
                f'<div class="cad-kpi-label">{html.escape(label)}</div>'
                f'</div>'
            )

    profile_section = (
        f'<div class="cad-kpi-grid">{kpi_cards}</div>'
        if kpi_cards else
        f'<div class="cad-card"><p style="color:{PALETTE["text_muted"]};">'
        f'No profile metrics yet. '
        f'<a href="/import" style="color:{PALETTE["text_link"]};">Edit deal profile</a>.</p></div>'
    )

    # Completeness
    total_fields = 8
    pct = populated / total_fields * 100
    bar_color = PALETTE["positive"] if pct > 70 else (PALETTE["warning"] if pct > 40 else PALETTE["negative"])
    completeness = (
        f'<div class="cad-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<h2>Data Completeness</h2>'
        f'<span class="cad-mono" style="color:{bar_color};">{populated}/{total_fields} fields</span>'
        f'</div>'
        f'<div style="background:{PALETTE["bg_tertiary"]};border-radius:6px;height:10px;">'
        f'<div style="width:{pct:.0f}%;background:{bar_color};border-radius:6px;height:10px;"></div>'
        f'</div></div>'
    )

    # Action cards — these are the money section
    models_section = (
        f'<div class="cad-card"><h2>Available Models & Analysis</h2>'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:16px;">'
        f'Click any model to run it instantly on this deal\'s profile data.</p></div>'

        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">'

        f'<a href="/models/dcf/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">DCF Valuation</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'5-year cash flow projection with WACC sensitivity matrix</div></a>'

        f'<a href="/models/lbo/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">LBO Model</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'Sources & uses, debt schedule, IRR/MOIC returns</div></a>'

        f'<a href="/models/financials/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">3-Statement</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'IS + BS + CF reconstructed from HCRIS + profile</div></a>'

        f'<a href="/models/market/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["positive"]};">Market Analysis</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'HHI, competitors, Mauboussin moat assessment</div></a>'

        f'<a href="/models/denial/{did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["warning"]};">Denial Drivers</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'Root cause decomposition with dollar impacts</div></a>'

        f'<a href="/pressure?deal_id={did}" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["negative"]};">Pressure Test</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'Stress scenarios with risk flags</div></a>'

        f'</div>'
    )

    # Export & API links
    export_section = (
        f'<div class="cad-card">'
        f'<h2>Export & Download</h2>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{did}/dcf" class="cad-btn" style="text-decoration:none;">'
        f'DCF JSON</a>'
        f'<a href="/api/deals/{did}/lbo" class="cad-btn" style="text-decoration:none;">'
        f'LBO JSON</a>'
        f'<a href="/api/deals/{did}/financials" class="cad-btn" style="text-decoration:none;">'
        f'Financials JSON</a>'
        f'<a href="/models/market/{did}" class="cad-btn" style="text-decoration:none;">'
        f'Market JSON</a>'
        f'<a href="/models/denial/{did}" class="cad-btn" style="text-decoration:none;">'
        f'Denial Drivers JSON</a>'
        f'<a href="/api/deals/{did}/memo" class="cad-btn" style="text-decoration:none;">'
        f'IC Memo</a>'
        f'<a href="/api/deals/{did}/validate" class="cad-btn" style="text-decoration:none;">'
        f'Validate</a>'
        f'<a href="/api/deals/{did}/completeness" class="cad-btn" style="text-decoration:none;">'
        f'Completeness</a>'
        f'</div></div>'
    )

    body = f'{error_html}{profile_section}{completeness}{models_section}{export_section}'

    return shell_v2(
        body, name,
        active_nav="/analysis",
        subtitle=f"Deal: {did} — {populated} of {total_fields} profile fields populated",
    )
