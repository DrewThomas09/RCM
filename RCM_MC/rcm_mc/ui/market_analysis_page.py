"""SeekingChartis Market Analysis — browser-rendered competitive analysis.

Renders the market analysis (HHI, moat, competitors) as a visual page.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from .shell_v2 import shell_v2
from .models_page import _model_nav
from .brand import PALETTE


def render_market_analysis_page(deal_id: str, deal_name: str, analysis: Dict[str, Any]) -> str:
    """Render market analysis as a browser page."""
    target = analysis.get("target", {})
    market_size = analysis.get("market_size", {})
    moat = analysis.get("moat", {})
    competitors = analysis.get("competitors", [])
    payer_mix = analysis.get("payer_mix_region", {})
    trends = analysis.get("market_trends", {})

    # KPIs
    hhi = moat.get("hhi_index", 0)
    hhi_label = "Concentrated" if hhi > 2500 else ("Moderate" if hhi > 1500 else "Competitive")
    hhi_cls = "cad-badge-red" if hhi > 2500 else ("cad-badge-amber" if hhi > 1500 else "cad-badge-green")
    moat_rating = moat.get("moat_rating", "none")
    moat_cls = "cad-badge-green" if moat_rating == "wide" else ("cad-badge-amber" if moat_rating == "narrow" else "cad-badge-muted")

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{market_size.get("hospitals", 0)}</div>'
        f'<div class="cad-kpi-label">Hospitals in Market</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{market_size.get("total_beds", 0):,}</div>'
        f'<div class="cad-kpi-label">Total Beds</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${market_size.get("total_revenue", 0)/1e9:.1f}B</div>'
        f'<div class="cad-kpi-label">Market Revenue</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'<span class="cad-badge {hhi_cls}" style="font-size:14px;padding:4px 12px;">{hhi_label}</span></div>'
        f'<div class="cad-kpi-label">HHI: {hhi:,.0f}</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'<span class="cad-badge {moat_cls}" style="font-size:14px;padding:4px 12px;">'
        f'{moat_rating.title()}</span></div>'
        f'<div class="cad-kpi-label">Moat Rating ({moat.get("moat_score", 0)}/10)</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">#{moat.get("market_share_rank", 0)}</div>'
        f'<div class="cad-kpi-label">Market Share Rank</div></div>'
        f'</div>'
    )

    # Moat breakdown
    moat_items = ""
    moat_fields = [
        ("Scale Advantage", moat.get("scale_advantage", "unknown")),
        ("Switching Costs", moat.get("switching_cost_indicator", "unknown")),
        ("Market Share", f"{moat.get('market_share_pct', 0):.1%}"),
        ("Top 3 Concentration", f"{moat.get('top3_concentration', 0):.1%}"),
        ("Network Density", f"{moat.get('network_density', 0):.2f}"),
        ("Margin vs Market", f"{moat.get('margin_vs_market', 0):+.1%}"),
        ("Bed Util vs Market", f"{moat.get('bed_utilization_vs_market', 0):+.1%}"),
    ]
    for label, val in moat_fields:
        color = PALETTE["positive"] if "strong" in str(val).lower() or "high" in str(val).lower() else (
            PALETTE["negative"] if "weak" in str(val).lower() or "low" in str(val).lower() else PALETTE["text_primary"])
        moat_items += (
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px solid {PALETTE["border"]};">'
            f'<span style="color:{PALETTE["text_secondary"]};">{html.escape(label)}</span>'
            f'<span class="cad-mono" style="color:{color};">{html.escape(str(val))}</span></div>'
        )
    moat_section = (
        f'<div class="cad-card">'
        f'<h2>Competitive Moat (Mauboussin Framework)</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Based on "Measuring the Moat" adapted for healthcare. Score 0-10: '
        f'wide (8+), narrow (5-7), none (&lt;5).</p>'
        f'{moat_items}</div>'
    )

    # Competitors
    comp_rows = ""
    for c in competitors[:10]:
        comp_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{html.escape(str(c.get("ccn", "")))}">'
            f'{html.escape(str(c.get("name", ""))[:40])}</a></td>'
            f'<td class="num">{c.get("beds", 0)}</td>'
            f'<td class="num">${c.get("revenue", 0)/1e6:,.0f}M</td>'
            f'<td class="num">{c.get("market_share_revenue", 0):.1%}</td>'
            f'<td class="num">{c.get("market_share_beds", 0):.1%}</td>'
            f'</tr>'
        )
    comp_section = (
        f'<div class="cad-card">'
        f'<h2>Top Competitors</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>Beds</th><th>Revenue</th>'
        f'<th>Rev Share</th><th>Bed Share</th>'
        f'</tr></thead><tbody>{comp_rows}</tbody></table></div>'
    ) if comp_rows else ""

    # Payer mix
    med = payer_mix.get("medicare", 0)
    mcd = payer_mix.get("medicaid", 0)
    comm = payer_mix.get("commercial", 0)
    payer_html = (
        f'<div class="cad-card">'
        f'<h2>Regional Payer Mix</h2>'
        f'<div style="display:flex;gap:4px;height:24px;border-radius:6px;overflow:hidden;margin-bottom:8px;">'
        f'<div style="width:{med*100:.0f}%;background:{PALETTE["brand_accent"]};" '
        f'title="Medicare {med:.0%}"></div>'
        f'<div style="width:{mcd*100:.0f}%;background:{PALETTE["warning"]};" '
        f'title="Medicaid {mcd:.0%}"></div>'
        f'<div style="width:{comm*100:.0f}%;background:{PALETTE["positive"]};" '
        f'title="Commercial {comm:.0%}"></div></div>'
        f'<div style="display:flex;gap:16px;font-size:12px;">'
        f'<span style="color:{PALETTE["brand_accent"]};">&#9632; Medicare {med:.0%}</span>'
        f'<span style="color:{PALETTE["warning"]};">&#9632; Medicaid {mcd:.0%}</span>'
        f'<span style="color:{PALETTE["positive"]};">&#9632; Commercial {comm:.0%}</span>'
        f'</div></div>'
    )

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/market" class="cad-btn" '
        f'style="text-decoration:none;">Raw JSON</a>'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">DCF Model</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation
    state = target.get("state", "")
    moat_interp = (
        "wide moat — strong competitive position, high barriers to entry" if moat_rating == "wide"
        else "narrow moat — some competitive advantages, but vulnerable to new entrants" if moat_rating == "narrow"
        else "no moat — commoditized market position, pricing power limited"
    )
    market_interp = (
        "highly concentrated — few dominant players, potential antitrust concerns" if hhi > 2500
        else "moderately concentrated — oligopoly dynamics, negotiating leverage exists" if hhi > 1500
        else "competitive — many players, value creation must come from operations not market power"
    )
    did_esc = html.escape(deal_id)
    st_esc = html.escape(state)
    link_col = PALETTE["text_link"]
    implication = (
        "Market position supports pricing power — check payer contract terms."
        if moat_rating == "wide"
        else f'Operational improvements are the primary value driver — see the '
             f'<a href="/models/bridge/{did_esc}" style="color:{link_col};">EBITDA bridge</a>.'
    )
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>This hospital has a <strong>{moat_rating} moat</strong> — {moat_interp}. '
        f'The {state or "regional"} market is {market_interp} (HHI: {hhi:,.0f}).</p>'
        f'<p style="margin-top:6px;"><strong>Implications:</strong> {implication}'
        f' Compare against peers via '
        f'<a href="/models/comparables/{did_esc}" style="color:{link_col};">comparables</a> '
        f'or see the full <a href="/market-data/state/{st_esc}" style="color:{link_col};">'
        f'{st_esc} market</a>.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "market")
    body = f'{nav}{kpis}{moat_section}{interp}{comp_section}{payer_html}{actions}'
    return shell_v2(
        body, f"Market Analysis — {html.escape(deal_name)}",
        active_nav="/analysis",
        subtitle=f"{state} market | {market_size.get('hospitals', 0)} hospitals | HHI: {hhi:,.0f} ({hhi_label})",
    )
