"""SeekingChartis Methodology Hub — research library and reference materials.

Central hub for PE diligence frameworks, benchmark data, model
documentation, and methodology references. Served at /methodology.
The legacy /library route now surfaces the 655-deal corpus.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import chartis_shell
from .brand import PALETTE


_LIBRARY_SECTIONS = [
    {
        "title": "Valuation Models",
        "icon": "&#9672;",
        "items": [
            {
                "title": "DCF Model",
                "description": "5-year discounted cash flow with WACC sensitivity matrix",
                "endpoint": "/api/deals/{deal_id}/dcf",
                "doc": "Projects free cash flow using deal profile inputs. Builds a WACC x terminal "
                       "growth sensitivity table. Requires: net_revenue, ebitda_margin, capex_pct, "
                       "working_capital_change.",
                "badge": "Financial Model",
            },
            {
                "title": "LBO Model",
                "description": "Sources & uses, debt schedule, returns waterfall",
                "endpoint": "/api/deals/{deal_id}/lbo",
                "doc": "Full leveraged buyout model with senior + mezzanine debt, annual P&L "
                       "projection, mandatory/optional repayment schedule, and equity returns at "
                       "multiple exit timings.",
                "badge": "Financial Model",
            },
            {
                "title": "3-Statement Model",
                "description": "Income statement, balance sheet, cash flow reconstructed from HCRIS",
                "endpoint": "/api/deals/{deal_id}/financials",
                "doc": "Reconstructs full financial statements from HCRIS cost report data and "
                       "deal profile. Every line item tagged with source provenance (HCRIS, "
                       "deal_profile, benchmark, computed).",
                "badge": "Financial Model",
            },
            {
                "title": "EBITDA Bridge",
                "description": "7-lever RCM improvement bridge from current to target EBITDA",
                "endpoint": "/api/analysis/{deal_id}",
                "doc": "Models denial reduction, AR acceleration, coding uplift, payer mix "
                       "optimization, cost-to-collect reduction, clean claim improvement, and "
                       "volume/rate growth. Each lever has a probability-weighted impact.",
                "badge": "Analysis",
            },
        ],
    },
    {
        "title": "Market Intelligence",
        "icon": "&#9728;",
        "items": [
            {
                "title": "Market Analysis",
                "description": "HHI concentration, competitive landscape, Mauboussin moat assessment",
                "endpoint": "/api/deals/{deal_id}/market",
                "doc": "Analyzes the regional market using HCRIS peer data. Computes HHI, market "
                       "share rank, top-3 concentration, scale advantage, switching costs, and "
                       "network density. Moat scored 0-10 (wide/narrow/none).",
                "badge": "Market",
            },
            {
                "title": "State Heatmap",
                "description": "National view of hospital margins, concentration, and payer mix",
                "endpoint": "/market-data/map",
                "doc": "Aggregates HCRIS data by state with color-coded heatmap on selectable "
                       "metrics (margin, HHI, Medicare %, bed count). Includes OLS regression "
                       "showing which state-level factors predict hospital margins.",
                "badge": "Market",
            },
            {
                "title": "Hospital Screener",
                "description": "Filter 6,000+ hospitals by any combination of financial/operational metrics",
                "endpoint": "/screen",
                "doc": "5 predefined screens (value, turnaround, large cap, small cap, margin "
                       "expansion) plus custom filter builder. Returns ranked results with "
                       "SeekingChartis Score for each match.",
                "badge": "Screener",
            },
            {
                "title": "Denial Driver Analysis",
                "description": "Decompose denial rates into root causes with dollar-sized impacts",
                "endpoint": "/api/deals/{deal_id}/denial-drivers",
                "doc": "Identifies top denial drivers (prior auth, coding errors, timely filing, "
                       "medical necessity, eligibility) with estimated annual dollar impact. "
                       "Includes expert recommendation database per driver category.",
                "badge": "Operational",
            },
        ],
    },
    {
        "title": "Quantitative Tools",
        "icon": "&#9638;",
        "items": [
            {
                "title": "Monte Carlo Simulation",
                "description": "100K+ simulations projecting EBITDA outcomes with confidence intervals",
                "endpoint": "/api/analysis/{deal_id}",
                "doc": "Two-source MC: (1) kernel density from calibrated priors, (2) Ridge "
                       "predictor with conformal prediction intervals. Returns P10/P50/P90 "
                       "outcomes, probability of downside, and VaR.",
                "badge": "Quantitative",
            },
            {
                "title": "OLS Regression",
                "description": "Multi-variable regression on any hospital dataset with full diagnostics",
                "endpoint": "/api/portfolio/regression",
                "doc": "Ordinary least squares with t-statistics, p-values, significance flags, "
                       "correlation matrix, and top correlated pairs. Numpy-only implementation "
                       "(no sklearn). Can target any metric against any feature set.",
                "badge": "Quantitative",
            },
            {
                "title": "Pressure Test",
                "description": "Stress scenarios with severity-ranked risk flags",
                "endpoint": "/pressure?deal_id={deal_id}",
                "doc": "Applies payer rate shocks, volume declines, and regulatory changes to "
                       "test deal resilience. Generates risk flags with severity scoring and "
                       "auto-generated diligence questions.",
                "badge": "Risk",
            },
            {
                "title": "Scenario Builder",
                "description": "Apply named shock scenarios to any deal",
                "endpoint": "/scenarios",
                "doc": "Preset scenarios: Commercial IDR +20%, Medicare RAC Storm, Labor Crisis, "
                       "Volume Drop, Payer Mix Shift. Each scenario defines metric overrides "
                       "that flow through the full analysis pipeline.",
                "badge": "Quantitative",
            },
        ],
    },
    {
        "title": "Data Sources",
        "icon": "&#9993;",
        "items": [
            {
                "title": "HCRIS (CMS Hospital Cost Reports)",
                "description": "17,974 hospitals, annual financial data from Medicare cost reports",
                "endpoint": "/api/data/sources",
                "doc": "The primary data source: CMS Hospital Cost Report Information System. "
                       "Includes revenue, expenses, bed count, payer days, and geographic data "
                       "for every Medicare-certified hospital. Updated annually with ~1 year lag.",
                "badge": "Data Source",
            },
            {
                "title": "FRED (Federal Reserve Economic Data)",
                "description": "Treasury yields, CPI, healthcare spending macro indicators",
                "endpoint": "/api/market-pulse",
                "doc": "Used for market pulse indicators: 10-year Treasury yield (DGS10), "
                       "healthcare CPI, national health expenditure estimates. API key optional "
                       "(falls back to static benchmarks).",
                "badge": "Data Source",
            },
            {
                "title": "SeekingChartis Score",
                "description": "Composite 0-100 rating: market (35%) + financial (25%) + operational (20%) + moat (20%)",
                "endpoint": "/hospital/010001",
                "doc": "Every hospital gets a SeekingChartis Score computed from HCRIS data. "
                       "Market position (beds, revenue scale), financial health (margin), "
                       "operational quality (denial rate, AR days), and competitive moat "
                       "(HHI, switching costs). Grade scale: A+ to F.",
                "badge": "Composite",
            },
        ],
    },
    {
        "title": "Benchmarks & Methodology",
        "icon": "&#9733;",
        "items": [
            {
                "title": "RCM Benchmarks",
                "description": "Industry-standard KPI targets for revenue cycle management",
                "endpoint": None,
                "doc": "Denial Rate: <8% (excellent), 8-12% (good), >15% (concerning). "
                       "Days in AR: <42 (excellent), 42-48 (good), >55 (slow). "
                       "Clean Claim Rate: >95% (excellent), 90-95% (good). "
                       "Net Collection Rate: >96% (strong). Cost to Collect: <4% (efficient).",
                "badge": "Reference",
            },
            {
                "title": "Hospital Valuation Guide",
                "description": "PE transaction multiples, WACC assumptions, terminal growth rates",
                "endpoint": None,
                "doc": "Current hospital EV/EBITDA: 9-12x (mid-market), 11-14x (large platform). "
                       "WACC range: 8-12% depending on leverage and size. Terminal growth: "
                       "2.0-3.0% (Medicare reimbursement growth proxy). Minority discount: 15-25%.",
                "badge": "Reference",
            },
            {
                "title": "Mauboussin Moat Framework",
                "description": "Competitive advantage assessment adapted for healthcare",
                "endpoint": None,
                "doc": "Based on 'Measuring the Moat' (Mauboussin, 2002). Healthcare adaptation: "
                       "Scale advantage (bed count vs market avg), switching costs (>200 beds = high), "
                       "network density, margin premium vs peers. Moat rating: wide (8+), "
                       "narrow (5-7), none (<5).",
                "badge": "Reference",
            },
        ],
    },
]


def _library_section(section: Dict[str, Any]) -> str:
    items_html = ""
    for item in section["items"]:
        endpoint_link = ""
        if item.get("endpoint"):
            ep = html.escape(item["endpoint"])
            endpoint_link = (
                f'<div style="margin-top:8px;">'
                f'<code style="font-size:11px;color:{PALETTE["text_link"]};'
                f'background:{PALETTE["bg_tertiary"]};padding:2px 6px;border-radius:3px;">'
                f'{ep}</code></div>'
            )

        badge_cls = {
            "Financial Model": "cad-badge-blue",
            "Market": "cad-badge-green",
            "Screener": "cad-badge-amber",
            "Operational": "cad-badge-amber",
            "Quantitative": "cad-badge-blue",
            "Risk": "cad-badge-red",
            "Data Source": "cad-badge-muted",
            "Composite": "cad-badge-green",
            "Reference": "cad-badge-muted",
            "Analysis": "cad-badge-blue",
        }.get(item.get("badge", ""), "cad-badge-muted")

        # Make endpoint clickable — replace {deal_id} placeholder with analysis link
        ep = item.get("endpoint", "")
        if ep and "{deal_id}" not in ep:
            action_link = (
                f'<a href="{html.escape(ep)}" class="cad-btn" '
                f'style="text-decoration:none;font-size:12px;margin-top:8px;display:inline-block;">'
                f'Open &rarr;</a>'
            )
        elif ep:
            action_link = (
                f'<a href="/analysis" class="cad-btn" '
                f'style="text-decoration:none;font-size:12px;margin-top:8px;display:inline-block;">'
                f'Select a deal to run &rarr;</a>'
            )
        else:
            action_link = ""

        items_html += (
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:start;">'
            f'<h2>{html.escape(item["title"])}</h2>'
            f'<span class="cad-badge {badge_cls}">{html.escape(item.get("badge", ""))}</span>'
            f'</div>'
            f'<div style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:8px;">'
            f'{html.escape(item["description"])}</div>'
            f'<p style="font-size:12.5px;line-height:1.65;">{html.escape(item["doc"])}</p>'
            f'{action_link}'
            f'</div>'
        )

    return (
        f'<div style="margin-bottom:24px;">'
        f'<h2 class="cad-h1" style="font-size:16px;margin-bottom:12px;display:flex;'
        f'align-items:center;gap:8px;">'
        f'<span>{section["icon"]}</span> {html.escape(section["title"])}</h2>'
        f'{items_html}</div>'
    )


def render_library() -> str:
    """Render the SeekingChartis research library page."""
    sections = "".join(_library_section(s) for s in _LIBRARY_SECTIONS)

    extra_links = (
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">'
        f'<a href="/data" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">Data Explorer</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'Browse all 6 public data sources</div></a>'
        f'<a href="/verticals" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">Healthcare Verticals</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'ASC, Behavioral Health, MSO bridges</div></a>'
        f'<a href="/methodology" class="cad-card" style="text-decoration:none;color:inherit;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};">Methodology</h3>'
        f'<div style="font-size:12px;color:{PALETTE["text_secondary"]};">'
        f'How every number is calculated</div></a>'
        f'</div>'
    )
    api_link = extra_links

    body = f'{sections}{api_link}'

    return chartis_shell(
        body, "Methodology",
        active_nav="/methodology",
        subtitle="Research library, model documentation & methodology references",
    )
