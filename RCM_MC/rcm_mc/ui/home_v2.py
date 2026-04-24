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


def _quickstart_block() -> str:
    """Empty-state quick-start — shown when no deals are in portfolio.

    A first-time visitor needs a visible "try the tool" path.
    Four pre-seeded fixture cards with one-click Run Pipeline CTAs
    and partner-speak characterization of what each fixture tests.
    """
    fixtures = [
        {
            "id": "hospital_01_clean_acute",
            "name": "Clean acute baseline",
            "tagline": "Healthy reference hospital",
            "description": (
                "Baseline acute-care profile — denial rate ~4%, "
                "A/R ~42 days, peer-norm operating metrics. Run "
                "this first to see what the tool outputs against "
                "a well-run target."
            ),
            "badge": "BASELINE",
            "badge_tone": "positive",
        },
        {
            "id": "hospital_02_denial_heavy",
            "name": "Denial-heavy outpatient",
            "tagline": "High audit-recovery opportunity",
            "description": (
                "Denial rate ~20%, systematic-misses drive the "
                "EBITDA bridge. Typical roll-up target profile — "
                "shows denial prediction + counterfactual advisor "
                "in action."
            ),
            "badge": "OPPORTUNITY",
            "badge_tone": "warning",
        },
        {
            "id": "hospital_07_waterfall_concordant",
            "name": "QoR concordant",
            "tagline": "Quality-of-Revenue low-divergence",
            "description": (
                "Management revenue and claims-side accrual waterfall "
                "agree within IMMATERIAL threshold — clean QoE target. "
                "Good reference for a no-surprise QoR deliverable."
            ),
            "badge": "CLEAN QoR",
            "badge_tone": "positive",
        },
        {
            "id": "hospital_08_waterfall_critical",
            "name": "QoR critical divergence",
            "tagline": "7% revenue divergence — walkaway candidate",
            "description": (
                "Management revenue overstates claims-side accrual "
                "by ~7%. Triggers CRITICAL QoR finding + IC Packet "
                "walkaway memo. Shows the tool catching a revenue "
                "miss that spreadsheets miss."
            ),
            "badge": "CRITICAL",
            "badge_tone": "negative",
        },
    ]
    tone_colors = {
        "positive": PALETTE["positive"],
        "warning": PALETTE["accent_amber"],
        "negative": PALETTE["negative"],
    }
    # Default deal structure so the pipeline output has meaningful
    # Deal MC numbers — acute-hospital typical.
    base_qs = (
        "&deal_name=Demo+Target"
        "&specialty=HOSPITAL"
        "&states=TX"
        "&landlord=Medical+Properties+Trust"
        "&lease_term_years=20"
        "&lease_escalator_pct=0.035"
        "&ebitdar_coverage=1.3"
        "&annual_rent_usd=30000000"
        "&revenue_year0_usd=250000000"
        "&ebitda_year0_usd=35000000"
        "&enterprise_value_usd=350000000"
        "&equity_check_usd=150000000"
        "&debt_usd=200000000"
        "&entry_multiple=10.0"
        "&market_category=MULTI_SITE_ACUTE_HOSPITAL"
        "&oon_revenue_share=0.08"
        "&ehr_vendor=EPIC"
        "&n_runs=1000"
    )
    cards = []
    for fx in fixtures:
        tone_color = tone_colors.get(fx["badge_tone"], PALETTE["text_muted"])
        pipeline_url = (
            f'/diligence/thesis-pipeline?dataset={fx["id"]}{base_qs}'
        )
        profile_url = f'/diligence/benchmarks?dataset={fx["id"]}'
        cards.append(
            f'<div style="background:{PALETTE["bg_secondary"]};'
            f'border:1px solid {PALETTE["border"]};border-radius:4px;'
            f'padding:16px 18px;display:flex;flex-direction:column;'
            f'gap:10px;transition:border-color 140ms ease;" '
            f'onmouseover="this.style.borderColor=\'{tone_color}\'" '
            f'onmouseout="this.style.borderColor=\'{PALETTE["border"]}\'">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:baseline;gap:10px;">'
            f'<div style="font-size:10px;letter-spacing:1.4px;'
            f'text-transform:uppercase;font-weight:700;color:{tone_color};'
            f'border:1px solid {tone_color};padding:2px 8px;border-radius:3px;">'
            f'{html.escape(fx["badge"])}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:15px;color:{PALETTE["text_primary"]};'
            f'font-weight:600;line-height:1.25;">'
            f'{html.escape(fx["name"])}</div>'
            f'<div style="font-size:11px;color:{PALETTE["text_muted"]};'
            f'margin-top:2px;font-style:italic;">'
            f'{html.escape(fx["tagline"])}</div>'
            f'</div>'
            f'<div style="font-size:11.5px;color:{PALETTE["text_muted"]};'
            f'line-height:1.55;flex-grow:1;">'
            f'{html.escape(fx["description"])}</div>'
            f'<div style="display:flex;gap:8px;margin-top:4px;">'
            f'<a href="{html.escape(pipeline_url)}" '
            f'style="display:inline-block;padding:7px 14px;'
            f'background:{PALETTE["accent_amber"]};color:{PALETTE["bg"]};'
            f'border:0;font-size:10px;letter-spacing:1.3px;'
            f'text-transform:uppercase;font-weight:700;text-decoration:none;'
            f'border-radius:3px;">▶ Run Pipeline</a>'
            f'<a href="{html.escape(profile_url)}" '
            f'style="display:inline-block;padding:7px 14px;'
            f'background:transparent;color:{PALETTE["text_link"]};'
            f'border:1px solid {PALETTE["border"]};font-size:10px;'
            f'letter-spacing:1.3px;text-transform:uppercase;'
            f'font-weight:600;text-decoration:none;border-radius:3px;">'
            f'Benchmarks Only</a>'
            f'</div>'
            f'</div>'
        )
    return (
        f'<div class="cad-card" style="border:1px solid '
        f'{PALETTE["accent_amber"]};position:relative;overflow:hidden;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'background:linear-gradient(90deg,{PALETTE["accent_amber"]},'
        f'{PALETTE["positive"]});"></div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:6px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">Try the tool</h2>'
        f'<span class="cad-section-code">QSX</span></div>'
        f'<span style="font-size:10.5px;font-family:var(--cad-mono);'
        f'letter-spacing:0.06em;text-transform:uppercase;'
        f'color:{PALETTE["text_muted"]};">no portfolio data yet</span>'
        f'</div>'
        f'<div style="font-size:13px;color:{PALETTE["text_muted"]};'
        f'line-height:1.6;max-width:880px;margin-bottom:14px;">'
        f'Your portfolio is empty. Run the full diligence chain against '
        f'one of four demo hospitals to see what the tool produces. '
        f'<strong style="color:{PALETTE["text_primary"]};">'
        f'▶ Run Pipeline</strong> executes bankruptcy scan → CCD ingest '
        f'→ HFMA benchmarks → denial prediction → physician attrition → '
        f'counterfactual → Steward → cyber → deal autopsy → Deal MC '
        f'and emits every headline number in ~120ms.'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));'
        f'gap:12px;">{"".join(cards)}</div>'
        f'</div>'
    )


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

    # Empty-state quick-start block — shown only when the portfolio
    # is empty.  Points a first-time user at the demo fixtures so
    # they can run the pipeline and see real output immediately.
    quickstart = _quickstart_block() if deals.empty else ""

    body = (
        f'{quickstart}{pulse_section}{portfolio_summary}'
        f'{insights_section}{deals_section}'
        f'{freshness_section}{links_section}'
    )

    return chartis_shell(
        body, "Home",
        active_nav="/home",
        subtitle="Healthcare PE diligence, instrument-grade",
    )
