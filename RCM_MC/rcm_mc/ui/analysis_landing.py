"""SeekingChartis Analysis Landing — hub for all analytical tools.

When the user clicks "Analysis" in the nav without a deal selected,
this page shows deals with one-click access to every model.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

import pandas as pd

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def render_analysis_landing(
    deals: pd.DataFrame,
    recent_runs: List[Dict[str, Any]] = None,
) -> str:
    """Render the analysis hub page."""

    # Deal cards with model links
    deal_cards = ""
    if not deals.empty:
        for _, d in deals.head(20).iterrows():
            did = html.escape(str(d.get("deal_id", "")))
            name = html.escape(str(d.get("name", did)))
            dr = d.get("denial_rate")
            ar = d.get("days_in_ar")
            rev = d.get("net_revenue")

            metrics = ""
            if dr is not None:
                dr_v = float(dr)
                dr_cls = "cad-badge-red" if dr_v > 15 else ("cad-badge-amber" if dr_v > 12 else "cad-badge-green")
                metrics += f'<span class="cad-badge {dr_cls}" style="font-size:10px;">DR: {dr_v:.1f}%</span> '
            if ar is not None:
                ar_v = float(ar)
                ar_cls = "cad-badge-red" if ar_v > 55 else ("cad-badge-amber" if ar_v > 48 else "cad-badge-green")
                metrics += f'<span class="cad-badge {ar_cls}" style="font-size:10px;">AR: {ar_v:.0f}d</span> '
            if rev is not None:
                metrics += f'<span class="cad-badge cad-badge-muted" style="font-size:10px;">${float(rev)/1e6:.0f}M</span>'

            # Quick estimates if revenue available
            quick_est = ""
            if rev is not None:
                rev_f = float(rev)
                margin = float(d.get("ebitda_margin", 0.10))
                ebitda_est = rev_f * margin
                ev_est = ebitda_est * 11.0
                quick_est = (
                    f'<div style="display:flex;gap:16px;font-size:11px;color:{PALETTE["text_muted"]};'
                    f'margin-top:4px;font-family:var(--cad-mono);">'
                    f'<span>Est. EBITDA: ${ebitda_est/1e6:.0f}M</span>'
                    f'<span>Est. EV: ${ev_est/1e6:.0f}M (@11x)</span>'
                    f'</div>'
                )

            deal_cards += (
                f'<div class="cad-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:10px;">'
                f'<div>'
                f'<div style="font-weight:600;font-size:14px;">{name}</div>'
                f'<div style="font-size:11px;margin-top:2px;">{metrics}</div>'
                f'{quick_est}'
                f'</div>'
                f'<a href="/analysis/{did}" class="cad-btn cad-btn-primary" '
                f'style="text-decoration:none;font-size:12px;">Full Analysis</a>'
                f'</div>'
                f'<div style="display:flex;gap:6px;flex-wrap:wrap;">'
                f'<a href="/models/dcf/{did}" class="cad-badge cad-badge-blue" '
                f'style="text-decoration:none;padding:4px 10px;">DCF</a>'
                f'<a href="/models/lbo/{did}" class="cad-badge cad-badge-blue" '
                f'style="text-decoration:none;padding:4px 10px;">LBO</a>'
                f'<a href="/models/financials/{did}" class="cad-badge cad-badge-green" '
                f'style="text-decoration:none;padding:4px 10px;">3-Statement</a>'
                f'<a href="/models/market/{did}" class="cad-badge cad-badge-green" '
                f'style="text-decoration:none;padding:4px 10px;">Market</a>'
                f'<a href="/models/denial/{did}" class="cad-badge cad-badge-amber" '
                f'style="text-decoration:none;padding:4px 10px;">Denial Drivers</a>'
                f'<a href="/pressure?deal_id={did}" class="cad-badge cad-badge-red" '
                f'style="text-decoration:none;padding:4px 10px;">Pressure Test</a>'
                f'<a href="/models/bridge/{did}" class="cad-badge cad-badge-green" '
                f'style="text-decoration:none;padding:4px 10px;">EBITDA Bridge</a>'
                f'<a href="/models/waterfall/{did}" class="cad-badge cad-badge-blue" '
                f'style="text-decoration:none;padding:4px 10px;">Waterfall</a>'
                f'<a href="/models/questions/{did}" class="cad-badge cad-badge-muted" '
                f'style="text-decoration:none;padding:4px 10px;">Diligence Q&amp;s</a>'
                f'<a href="/models/playbook/{did}" class="cad-badge cad-badge-muted" '
                f'style="text-decoration:none;padding:4px 10px;">Playbook</a>'
                f'<a href="/api/deals/{did}/package" class="cad-badge cad-badge-muted" '
                f'style="text-decoration:none;padding:4px 10px;">Download ZIP</a>'
                f'</div></div>'
            )

    if not deal_cards:
        deal_cards = (
            f'<div class="cad-card" style="text-align:center;padding:32px;">'
            f'<h2 style="margin-bottom:8px;">No Deals Yet</h2>'
            f'<p style="color:{PALETTE["text_secondary"]};margin-bottom:16px;">'
            f'Import deals to run DCF, LBO, market analysis, and more.</p>'
            f'<div style="display:flex;gap:8px;justify-content:center;">'
            f'<a href="/import" class="cad-btn cad-btn-primary" style="text-decoration:none;">'
            f'Import Deals</a>'
            f'<a href="/screen" class="cad-btn" style="text-decoration:none;">'
            f'Screen Hospitals</a></div></div>'
        )

    deals_section = (
        f'<div class="cad-card" style="padding:12px 20px;">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;">'
        f'Select a deal to run any model. Click a badge for a specific analysis, '
        f'or "Full Analysis" for the 7-tab workbench.</p></div>'
        f'{deal_cards}'
    )

    # Market-level tools (no deal required) — compact 6-tile grid.
    # Tightened per UX feedback: the original cards took too much vertical
    # space and used a saturated turquoise heading color that read as garish
    # against the parchment background.
    tools = [
        ("/market-data/map",       "Market Heatmap", "National hospital data with regression"),
        ("/portfolio/regression",  "Regression",     "OLS on HCRIS data or portfolio"),
        ("/screen",                "Screener",       "Filter 6,000+ hospitals by metrics"),
        ("/source",                "Deal Sourcing",  "Thesis-driven hospital matching"),
        ("/scenarios",             "Scenarios",      "Preset payer shock scenarios"),
        ("/news",                  "News",           "Healthcare PE market intelligence"),
    ]
    tools_html = "".join(
        f'<a href="{href}" class="market-tool-card">'
        f'<div class="mt-title">{html.escape(title)}</div>'
        f'<div class="mt-desc">{html.escape(desc)}</div>'
        f'</a>'
        for href, title, desc in tools
    )
    market_tools = (
        '<div class="sect" style="padding:1.5rem 0 .85rem;">'
        '<div>'
        '<div class="micro">MARKET TOOLS</div>'
        '<h2 style="font-size:1.5rem;">No deal <em>required</em>.</h2>'
        '</div>'
        '<p class="desc" style="font-size:.9rem;">'
        'Cross-portfolio analytics that operate on the public HCRIS / APCD '
        'corpus — useful for sourcing, sector context, scenarios, and news.'
        '</p>'
        '</div>'
        f'<div class="market-tools-grid">{tools_html}</div>'
    )

    n = len(deals) if not deals.empty else 0
    deals_label = f"{n} deal" + ("s" if n != 1 else "")

    # Editorial section header — eyebrow + serif h2 + descriptor
    page_head = (
        '<div class="sect">'
        '<div>'
        '<div class="micro">ANALYSIS HUB</div>'
        '<h2>Pick a deal,<br/><em>run any model</em>.</h2>'
        '</div>'
        '<p class="desc">'
        f'{deals_label} in the workspace. Click a model badge for a single '
        'analysis, or <strong>Full Analysis</strong> to open the 7-tab '
        'workbench. Market tools below run without a selected deal.'
        '</p>'
        '</div>'
    )

    body = f'{page_head}{deals_section}{market_tools}'

    return chartis_shell(
        body, "Analysis",
        active_nav="/analysis",
        subtitle=f"{deals_label} — click any model to run it instantly",
    )
