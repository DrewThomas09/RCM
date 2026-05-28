"""PE Desk Market Analysis — browser-rendered competitive analysis.

Renders the market analysis (HHI, moat, competitors) as a visual page.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_fmt_num, ck_kpi_block, ck_next_section,
    ck_provenance_tooltip, ck_value_anchor,
)
from .models_page import _model_nav
from .brand import PALETTE


def _competitor_share_chart(
    competitors: List[Dict[str, Any]], width: int = 720, row_h: int = 24
) -> str:
    """Horizontal bars of revenue market share across the competitive set.

    Reads the same ``market_share_revenue`` the table below shows, so
    the figure can never disagree with the rows. Bars are tone-graded:
    the market leader (largest share) is teal-deep, the rest fade by
    rank so concentration reads at a glance. Empty input returns "".
    """
    rows = [c for c in (competitors or [])[:10]
            if c.get("name")]
    if not rows:
        return ""
    rows = sorted(rows, key=lambda c: c.get("market_share_revenue", 0),
                  reverse=True)
    max_share = max((c.get("market_share_revenue", 0) for c in rows),
                    default=0)
    if max_share <= 0:
        max_share = 1.0

    pad_l, pad_r, pad_t = 200, 64, 10
    bar_max = width - pad_l - pad_r
    height = pad_t + row_h * len(rows) + 8

    lead = PALETTE.get("brand_accent", "#155752")
    rule = PALETTE.get("border", "#BFB6A2")
    txt = PALETTE.get("text_secondary", "#4a5568")

    parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Revenue market share by competitor" '
        f'style="width:100%;max-width:{width}px;height:auto;'
        f'print-color-adjust:exact;-webkit-print-color-adjust:exact;">'
    ]
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t - 2}" x2="{pad_l}" '
        f'y2="{height - 6}" stroke="{rule}" stroke-width="1"/>'
    )
    for i, c in enumerate(rows):
        name = html.escape(str(c.get("name", ""))[:32])
        share = c.get("market_share_revenue", 0)
        y = pad_t + i * row_h
        w = share / max_share * bar_max
        # Fade by rank: leader fully opaque, tail muted.
        op = 0.9 - (i / max(len(rows), 1)) * 0.55
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + row_h / 2 + 3:.1f}" '
            f'text-anchor="end" font-size="11" '
            f'font-family="Inter Tight,system-ui,sans-serif" '
            f'fill="{txt}">{name}</text>'
        )
        beds = c.get("beds", 0)
        rev = c.get("revenue", 0)
        tip = html.escape(
            f"{c.get('name', '')}: {share:.1%} revenue share · "
            f"${rev/1e6:,.0f}M NPR · {beds:,.0f} beds"
        )
        parts.append(
            f'<rect x="{pad_l}" y="{y + 3:.1f}" width="{max(w, 0.5):.1f}" '
            f'height="{row_h - 8}" rx="2" fill="{lead}" '
            f'opacity="{op:.2f}"><title>{tip}</title></rect>'
        )
        parts.append(
            f'<text x="{pad_l + w + 6:.1f}" y="{y + row_h / 2 + 3:.1f}" '
            f'text-anchor="start" font-size="10.5" '
            f'font-family="JetBrains Mono,ui-monospace,monospace" '
            f'fill="{txt}">{share:.1%}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


_MKT_CHART_CAPTION_CSS = (
    ".mkt-figcap{font-size:11px;color:#6b6456;margin:8px 0 4px;"
    "font-family:'JetBrains Mono',ui-monospace,monospace;"
    "letter-spacing:0.02em;}"
)


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
    # Readable verdict label — "none".title() would render the
    # null-looking word "None" in the badge; show "No Moat" instead.
    moat_label = {"wide": "Wide", "narrow": "Narrow",
                  "none": "No Moat"}.get(moat_rating, moat_rating.title())
    # Grammatical prose phrase ("a wide moat" / "no competitive moat").
    moat_phrase = {
        "wide": "a <strong>wide moat</strong>",
        "narrow": "a <strong>narrow moat</strong>",
        "none": "<strong>no competitive moat</strong>",
    }.get(moat_rating, f"a <strong>{html.escape(moat_rating)} moat</strong>")

    # The HHI + moat values are pre-formatted HTML (a styled badge
    # span), so we wrap them in SafeHtml so ck_provenance_tooltip
    # doesn't HTML-escape them into literal `<span class="cad-badge
    # ...">Competitive</span>` text on the page. (Helper's default
    # behavior is to escape any non-SafeHtml value — correct security
    # default; this is the documented exit.)
    from ._chartis_kit import SafeHtml
    hhi_value = ck_provenance_tooltip(
        f"Market HHI: {hhi:,.0f}",
        SafeHtml(
            f'<span class="cad-badge {hhi_cls}" '
            f'style="font-size:14px;padding:4px 12px;">'
            f'{html.escape(hhi_label)}</span>'
        ),
        explainer=(
            "Herfindahl-Hirschman Index of market concentration. "
            "DOJ thresholds: <1,500 competitive, 1,500-2,500 "
            "moderately concentrated, >2,500 highly concentrated. "
            "Concentrated markets favor incumbent pricing power."
        ),
    )
    moat_value = ck_provenance_tooltip(
        f"Moat rating ({moat.get('moat_score', 0)}/10)",
        SafeHtml(
            f'<span class="cad-badge {moat_cls}" '
            f'style="font-size:14px;padding:4px 12px;">'
            f'{html.escape(moat_label)}</span>'
        ),
        explainer=(
            "Wide / narrow / none verdict from the moat-scoring "
            "engine: catchment exclusivity, regulatory moats, "
            "scale economies, switching costs. Wide moats are "
            "the underwriting case for premium multiples."
        ),
        inject_css=False,
    )
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Hospitals in Market", ck_fmt_num(market_size.get("hospitals", 0)), "competitive set")
        + ck_kpi_block("Total Beds", ck_fmt_num(market_size.get("total_beds", 0)), "licensed")
        + ck_kpi_block("Market Revenue", f"${market_size.get('total_revenue', 0)/1e9:.1f}B", "annual NPR")
        + ck_kpi_block("Concentration", hhi_value, f"HHI {hhi:,.0f}")
        + ck_kpi_block("Moat", moat_value, f"score {moat.get('moat_score', 0)}/10")
        + ck_kpi_block("Market Share Rank", f"#{moat.get('market_share_rank', 0)}", "in market")
        + '</div>'
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
    _comp_chart = _competitor_share_chart(competitors)
    _comp_fig = (
        f'<style>{_MKT_CHART_CAPTION_CSS}</style>'
        f'<div class="mkt-figcap">Revenue market share &middot; '
        f'longest bar = market leader &middot; bars fade by rank</div>'
        f'{_comp_chart}'
    ) if _comp_chart else ""
    comp_section = (
        f'<div class="cad-card">'
        f'<h2>Top Competitors</h2>'
        f'{_comp_fig}'
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
        f'<p>This hospital has {moat_phrase} — {moat_interp}. '
        f'The {state or "regional"} market is {market_interp} (HHI: {hhi:,.0f}).</p>'
        f'<p style="margin-top:6px;"><strong>Implications:</strong> {implication}'
        f' Compare against peers via '
        f'<a href="/models/comparables/{did_esc}" style="color:{link_col};">comparables</a> '
        f'or see the full <a href="/market-data/state/{st_esc}" style="color:{link_col};">'
        f'{st_esc} market</a>.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "market")
    next_up = ck_next_section(
        "Open the competitive intelligence view",
        f"/models/comparables/{did_esc}",
        eyebrow="Continue —",
        italic_word="competitive",
    )
    # Lead takeaway — surface the market-position read (moat verdict +
    # concentration + addressable market) at the top, before the KPI
    # grid and the "What This Means" card. Tone tracks the moat rating.
    _mkt_tone = (
        "positive" if moat_rating == "wide"
        else "warning" if moat_rating == "narrow"
        else "teal"
    )
    lead_anchor = ck_value_anchor(
        "MARKET POSITION",
        f"{moat_label} moat",
        delta=f"HHI {hhi:,.0f} ({hhi_label})",
        opportunity=f"${market_size.get('total_revenue', 0) / 1e9:.1f}B market",
        target=(
            f"#{moat.get('market_share_rank', 0)} share rank · "
            f"moat {moat.get('moat_score', 0)}/10"
        ),
        tone=_mkt_tone,
    )
    # 2026-05-28 batch 27 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="MARKET ANALYSIS",
        title=f"Market analysis — {html.escape(deal_name)}",
        meta=(
            f"{state.upper()} MARKET · "
            f"{market_size.get('hospitals', 0)} HOSPITALS · "
            f"HHI {hhi:,.0f} ({hhi_label.upper()}) · "
            f"MOAT {moat.get('moat_score', 0)}/10"
        ),
        lede_italic_phrase=(
            "Where this hospital sits in its market."
        ),
        lede_body=(
            "Per-deal market structure: competitive set, "
            "concentration (HHI), moat rating, and market-"
            "share rank. Wide moats in concentrated markets "
            "= structural pricing power; competitive markets "
            "with no moat are commodity hospital economics."
        ),
    )
    body = f'{head}{nav}{lead_anchor}{kpis}{moat_section}{interp}{comp_section}{payer_html}{actions}{next_up}'
    return chartis_shell(
        body, f"Market Analysis — {html.escape(deal_name)}",
        active_nav="/analysis",
        subtitle=f"{state} market | {market_size.get('hospitals', 0)} hospitals | HHI: {hhi:,.0f} ({hhi_label})",
    )
