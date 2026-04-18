"""SeekingChartis Home Page — market-first dashboard.

Seeking Alpha-inspired: market pulse, insights, active deals,
data freshness. Portfolio data is one section, not the whole page.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

import pandas as pd

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def _kpi_card(label: str, value: str, change: str = "", direction: str = "flat", source: str = "") -> str:
    color = {"up": PALETTE["positive"], "down": PALETTE["negative"]}.get(direction, PALETTE["text_muted"])
    delta = f'<div class="cad-kpi-delta" style="color:{color};">{html.escape(change)}</div>' if change else ""
    tooltip = f' title="{html.escape(source)}"' if source else ""
    src_line = (
        f'<div style="font-size:9px;color:{PALETTE["text_muted"]};margin-top:2px;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"'
        f'{tooltip}>{html.escape(source[:50])}</div>'
    ) if source else ""
    return (
        f'<div class="cad-kpi"{tooltip}>'
        f'<div class="cad-kpi-value">{html.escape(value)}</div>'
        f'<div class="cad-kpi-label">{html.escape(label)}</div>'
        f'{delta}{src_line}</div>'
    )


def _insight_card(insight: Dict[str, Any]) -> str:
    sev = insight.get("severity", "info")
    color = {"critical": PALETTE["critical"], "warning": PALETTE["warning"]}.get(sev, PALETTE["brand_accent"])
    deals = [d for d in insight.get("related_deal_ids", []) if d]
    deal_links = " ".join(
        f'<a href="/deal/{html.escape(d)}" class="cad-badge cad-badge-blue" '
        f'style="text-decoration:none;">{html.escape(d)}</a>'
        f'<a href="/models/denial/{html.escape(d)}" class="cad-badge cad-badge-amber" '
        f'style="text-decoration:none;">Denial Analysis</a>'
        for d in deals[:2]
    )
    return (
        f'<div class="cad-card" style="border-left:3px solid {color};">'
        f'<div style="display:flex;justify-content:space-between;align-items:start;">'
        f'<h2>{html.escape(insight.get("title", ""))}</h2>'
        f'<span class="cad-badge cad-badge-muted">{insight.get("reading_time_minutes", 2)} min read</span>'
        f'</div>'
        f'<div style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:8px;">'
        f'{html.escape(insight.get("subtitle", ""))}</div>'
        f'<p style="margin-bottom:8px;">{html.escape(insight.get("body", ""))}</p>'
        f'<div style="display:flex;gap:6px;align-items:center;">'
        f'<span style="font-size:11px;color:{PALETTE["text_muted"]};">'
        f'By {html.escape(insight.get("author", "SeekingChartis Research"))}</span>'
        f'{deal_links}</div></div>'
    )


def _deal_row(d: Dict[str, Any]) -> str:
    did = html.escape(str(d.get("deal_id", "") or ""))
    if not did:
        return ""
    name = html.escape(str(d.get("name", did)))
    stage = html.escape(str(d.get("stage", "pipeline")))
    return (
        f'<tr>'
        f'<td><a href="/deal/{did}">{name}</a></td>'
        f'<td><span class="cad-badge cad-badge-muted">{stage}</span></td>'
        f'<td class="num">{_fmt(d.get("denial_rate"), 1)}%</td>'
        f'<td class="num">{_fmt(d.get("days_in_ar"), 0)}</td>'
        f'<td class="num">{_fmt(d.get("net_revenue"), 0, scale=1e6)}M</td>'
        f'<td>'
        f'<a href="/analysis/{did}" class="cad-badge cad-badge-blue" '
        f'style="text-decoration:none;">Analyze</a> '
        f'<a href="/models/dcf/{did}" class="cad-badge cad-badge-muted" '
        f'style="text-decoration:none;">DCF</a> '
        f'<a href="/models/lbo/{did}" class="cad-badge cad-badge-muted" '
        f'style="text-decoration:none;">LBO</a>'
        f'</td></tr>'
    )


def _fmt(val: Any, dp: int = 1, scale: float = 1.0) -> str:
    if val is None:
        return "—"
    try:
        v = float(val) / scale
        return f"${v:,.{dp}f}" if scale > 1 else f"{v:,.{dp}f}"
    except (TypeError, ValueError):
        return "—"


def render_home(
    market_pulse: Any,
    insights: List[Dict[str, Any]],
    deals: pd.DataFrame,
    store: Any = None,
) -> str:
    """Render the SeekingChartis home page."""

    # Market Pulse KPIs
    pulse_cards = ""
    for ind in (market_pulse.indicators if hasattr(market_pulse, "indicators") else []):
        pulse_cards += _kpi_card(
            ind.label if hasattr(ind, "label") else ind.get("label", ""),
            ind.value if hasattr(ind, "value") else ind.get("value", ""),
            ind.change if hasattr(ind, "change") else ind.get("change", ""),
            ind.direction if hasattr(ind, "direction") else ind.get("direction", "flat"),
            ind.source if hasattr(ind, "source") else ind.get("source", ""),
        )

    pulse_section = (
        f'<div class="cad-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">Market Pulse</h2>'
        f'<span class="cad-section-code">MPX</span></div>'
        f'<a href="/methodology" style="font-size:10.5px;font-family:var(--cad-mono);'
        f'letter-spacing:0.06em;text-transform:uppercase;color:{PALETTE["text_link"]};">'
        f'Methodology &rarr;</a></div>'
        f'<div class="cad-kpi-grid">{pulse_cards}</div>'
        f'</div>'
    )

    # Insights
    insights_section = ""
    if insights:
        cards = "".join(_insight_card(i if isinstance(i, dict) else i.to_dict()) for i in insights[:4])
        insights_section = (
            f'<div style="margin-bottom:24px;">'
            f'<h2 class="cad-h1" style="font-size:16px;margin-bottom:12px;">'
            f'Insights from SeekingChartis</h2>'
            f'{cards}</div>'
        )

    # Portfolio summary KPIs (only when deals exist)
    portfolio_summary = ""
    if not deals.empty:
        n_deals = len(deals)
        p_rev = deals["net_revenue"].dropna().sum() if "net_revenue" in deals.columns else 0
        p_dr = deals["denial_rate"].dropna().mean() if "denial_rate" in deals.columns else None
        p_ar = deals["days_in_ar"].dropna().mean() if "days_in_ar" in deals.columns else None
        p_ebitda = 0
        if p_rev > 0:
            avg_m = float(deals["ebitda_margin"].dropna().mean()) if "ebitda_margin" in deals.columns and deals["ebitda_margin"].notna().any() else 0.10
            p_ebitda = p_rev * avg_m

        portfolio_summary = (
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<h2 style="margin:0;">Portfolio Summary</h2>'
            f'<span class="cad-section-code">PFS</span></div>'
            f'<a href="/portfolio" style="font-size:10.5px;font-family:var(--cad-mono);'
            f'letter-spacing:0.06em;text-transform:uppercase;color:{PALETTE["text_link"]};">'
            f'View All &rarr;</a></div>'
            f'<div class="cad-kpi-grid">'
            f'<div class="cad-kpi"><div class="cad-kpi-value">{n_deals}</div>'
            f'<div class="cad-kpi-label">Active Deals</div></div>'
            f'<div class="cad-kpi"><div class="cad-kpi-value">${p_rev/1e6:,.0f}M</div>'
            f'<div class="cad-kpi-label">Total Revenue</div></div>'
            + (f'<div class="cad-kpi"><div class="cad-kpi-value">${p_ebitda/1e6:,.0f}M</div>'
               f'<div class="cad-kpi-label">Est. EBITDA</div></div>' if p_ebitda > 0 else "")
            + (f'<div class="cad-kpi"><div class="cad-kpi-value">{p_dr:.1f}%</div>'
               f'<div class="cad-kpi-label">Avg Denial Rate</div></div>' if p_dr else "")
            + (f'<div class="cad-kpi"><div class="cad-kpi-value">{p_ar:.0f}</div>'
               f'<div class="cad-kpi-label">Avg AR Days</div></div>' if p_ar else "")
            + f'</div></div>'
        )

    # Active Deals Table
    deal_rows = ""
    if not deals.empty:
        for _, d in deals.head(20).iterrows():
            deal_rows += _deal_row(d.to_dict())

    deals_section = (
        f'<div class="cad-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        f'<h2>Your Active Deals ({len(deals)})</h2>'
        f'<div>'
        f'<a href="/api/export/portfolio.csv" class="cad-btn" style="text-decoration:none;">Export CSV</a> '
        f'<a href="/import" class="cad-btn cad-btn-primary" style="text-decoration:none;">+ Import Deal</a>'
        f'</div></div>'
        f'<table class="cad-table">'
        f'<thead><tr><th>Deal</th><th>Stage</th><th>Denial Rate</th>'
        f'<th>AR Days</th><th>NPR</th><th>Actions</th></tr></thead>'
        f'<tbody>{deal_rows}</tbody></table>'
        f'</div>'
        if deal_rows else
        f'<div class="cad-card">'
        f'<h2>Your Active Deals</h2>'
        f'<p style="color:{PALETTE["text_muted"]};">No deals yet. '
        f'<a href="/import" style="color:{PALETTE["text_link"]};">Create your first deal</a> '
        f'or <a href="/screen" style="color:{PALETTE["text_link"]};">screen hospitals</a>.</p>'
        f'</div>'
    )

    # Data freshness
    try:
        from ..data.hcris import _get_latest_per_ccn
        hcris = _get_latest_per_ccn()
        n_hospitals = len(hcris)
        n_states = hcris["state"].nunique() if "state" in hcris.columns else 0
    except Exception:
        n_hospitals = 0
        n_states = 0

    freshness_section = (
        f'<div class="cad-card" style="font-size:12px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<h2>Data Sources</h2>'
        f'<span class="cad-badge cad-badge-green">Live</span></div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-top:8px;">'
        f'<div>'
        f'<div class="cad-mono" style="font-size:16px;font-weight:700;">{n_hospitals:,}</div>'
        f'<div style="color:{PALETTE["text_muted"]};">HCRIS Hospitals</div></div>'
        f'<div>'
        f'<div class="cad-mono" style="font-size:16px;font-weight:700;">50+</div>'
        f'<div style="color:{PALETTE["text_muted"]};">States &amp; Territories</div></div>'
        f'<div>'
        f'<div class="cad-mono" style="font-size:16px;font-weight:700;">FRED</div>'
        f'<div style="color:{PALETTE["text_muted"]};">Treasury / Macro</div></div>'
        f'<div>'
        f'<div class="cad-mono" style="font-size:16px;font-weight:700;">15+</div>'
        f'<div style="color:{PALETTE["text_muted"]};">Analytical Models</div></div>'
        f'</div></div>'
    ) if n_hospitals > 0 else ""

    # Quick Actions — dense terminal-style launcher grid
    tiles = [
        ("TRN", "/screen?preset=turnaround", "Turnarounds", "High denial & AR hospitals"),
        ("LRG", "/screen?preset=large_cap", "Large Platforms", "300+ beds, $300M+ NPR"),
        ("MAP", "/market-data/map", "Market Heatmap", "National hospital map"),
        ("REG", "/portfolio/regression", "Regression", "Margin driver analysis"),
        ("IMP", "/import", "Import Deal", "Form or JSON upload"),
        ("SRC", "/source", "Source Deals", "Thesis-driven matching"),
        ("DAT", "/data", "Data Explorer", "6 public sources"),
        ("MTH", "/methodology", "Methodology", "Calculation reference"),
        ("VRT", "/verticals", "Verticals", "ASC · BH · MSO bridges"),
        ("SCN", "/scenarios", "Scenarios", "Rate & volume shocks"),
        ("SCR", "/predictive-screener", "Deal Screener", "Metric presets"),
        ("NWS", "/news", "News & Research", "Market intelligence"),
    ]
    tile_html = "".join(
        f'<a href="{href}" class="cad-quicktile">'
        f'<div class="cad-quicktile-code">{code}</div>'
        f'<div class="cad-quicktile-title">{html.escape(title)}</div>'
        f'<div class="cad-quicktile-sub">{html.escape(sub)}</div>'
        f'</a>'
        for code, href, title, sub in tiles
    )
    links_section = (
        f'<div class="cad-card" style="margin-bottom:10px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">Quick Actions</h2>'
        f'<span class="cad-section-code">CMD</span></div>'
        f'<span style="font-size:10.5px;font-family:var(--cad-mono);letter-spacing:0.06em;'
        f'text-transform:uppercase;color:{PALETTE["text_muted"]};">'
        f'&#8984;K for palette</span></div></div>'
        f'<style>.cad-quicktile{{display:block;padding:10px 12px;background:{PALETTE["bg_secondary"]};'
        f'border-right:1px solid {PALETTE["border"]};border-bottom:1px solid {PALETTE["border"]};'
        f'text-decoration:none;color:inherit;'
        f'transition:background 0.1s;position:relative;}}'
        f'.cad-quicktile:hover{{background:{PALETTE["bg_tertiary"]};}}'
        f'.cad-quicktile:hover .cad-quicktile-code{{color:{PALETTE["accent_amber"]};}}'
        f'.cad-quicktile:hover .cad-quicktile-title{{color:{PALETTE["accent_amber"]};}}'
        f'.cad-quicktile-code{{font-family:var(--cad-mono);font-size:9px;font-weight:700;'
        f'letter-spacing:0.18em;color:{PALETTE["text_muted"]};margin-bottom:4px;}}'
        f'.cad-quicktile-title{{font-size:12.5px;font-weight:600;color:{PALETTE["text_primary"]};'
        f'letter-spacing:0.02em;margin-bottom:2px;}}'
        f'.cad-quicktile-sub{{font-size:10.5px;color:{PALETTE["text_muted"]};'
        f'font-family:var(--cad-mono);letter-spacing:0.01em;}}</style>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0;'
        f'border-top:1px solid {PALETTE["border"]};border-left:1px solid {PALETTE["border"]};">'
        f'{tile_html}</div>'
    )

    body = f'{pulse_section}{portfolio_summary}{insights_section}{deals_section}{freshness_section}{links_section}'

    return chartis_shell(
        body, "Home",
        active_nav="/home",
        subtitle="Healthcare PE diligence, instrument-grade",
    )
