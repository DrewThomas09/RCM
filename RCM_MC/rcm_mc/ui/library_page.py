"""PE Desk Methodology Hub — research library and reference materials.

Central hub for PE diligence frameworks, benchmark data, model
documentation, and methodology references. Served at /methodology.
The legacy /library route now surfaces the 655-deal corpus.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_page_title, ck_provenance_tooltip,
)
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
                       "PE Desk Score for each match.",
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
                "endpoint": "/portfolio/regression",
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
                "endpoint": "/market-intel",
                "doc": "Used for market pulse indicators: 10-year Treasury yield (DGS10), "
                       "healthcare CPI, national health expenditure estimates. API key optional "
                       "(falls back to static benchmarks). The Market Intelligence page "
                       "surfaces the live values.",
                "badge": "Data Source",
            },
            {
                "title": "PE Desk Score",
                "description": "Composite 0-100 rating: market (35%) + financial (25%) + operational (20%) + moat (20%)",
                "endpoint": "/hospital/010001",
                "doc": "Every hospital gets a PE Desk Score computed from HCRIS data. "
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


def render_library(q: str = "") -> str:
    """Render the PE Desk research library page.

    ``q`` (from ``?q=``) keyword-filters the library entries by
    title / description / doc body. Empty string shows the full
    catalog. The filter operates server-side so it works without
    JavaScript and is back-button safe.
    """
    n_sections = len(_LIBRARY_SECTIONS)
    total_entries = sum(len(s.get("items", [])) for s in _LIBRARY_SECTIONS)

    # ── Keyword filter (Phase 2 — functionality lift) ──
    # Filter happens BEFORE the section render so empty sections
    # drop out entirely (cleaner than hiding individual items).
    # Match is case-insensitive on title + description + doc body
    # so partner can search by metric name, model class, or a phrase
    # from the rationale text.
    q_clean = (q or "").strip()
    if q_clean:
        q_lower = q_clean.lower()
        filtered_sections: List[Dict[str, Any]] = []
        for section in _LIBRARY_SECTIONS:
            kept_items = [
                it for it in section.get("items", [])
                if q_lower in (
                    str(it.get("title", "")) + " "
                    + str(it.get("description", "")) + " "
                    + str(it.get("doc", ""))
                ).lower()
            ]
            if kept_items:
                filtered_sections.append({**section, "items": kept_items})
        n_matched_entries = sum(
            len(s.get("items", [])) for s in filtered_sections
        )
        n_matched_sections = len(filtered_sections)
        sections_for_render = filtered_sections
    else:
        n_matched_entries = total_entries
        n_matched_sections = n_sections
        sections_for_render = _LIBRARY_SECTIONS

    sections = "".join(_library_section(s) for s in sections_for_render)

    # ── 2026-05-28 style-sweep · strict Tier-1 5-block head ──
    # Replaces the legacy dual editorial_intro + ck_page_title combo
    # (which produced both an h2 deck and a separate h1, creating
    # visual stacking confusion at the masthead). Single head block
    # with eyebrow + dash + h1 + mono meta + italic lede + legend,
    # same shape as /portfolio, /pipeline, regression.
    _lib_head_css = """
<style>
.lib-head{padding:0 0 32px;margin:0 0 28px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac);}
.lib-head .eyebrow{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.18em;text-transform:uppercase;
  color:var(--green-deep,#154e36);display:flex;align-items:center;
  gap:12px;margin:0 0 18px;}
.lib-head .eyebrow .dash{width:24px;height:1px;
  background:var(--green-deep,#154e36);}
.lib-head h1{font:400 44px/1.05 var(--sc-serif,Georgia),serif;
  letter-spacing:-.015em;color:var(--ink,#16263a);margin:0 0 14px;}
.lib-head .meta{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted,#7a8595);margin:0 0 20px;}
.lib-head .lede{font:400 italic 16.5px/1.55 var(--sc-serif,Georgia),serif;
  color:var(--ink-2,#2b3e54);max-width:64ch;margin:0 0 20px;}
.lib-head .lede em{color:var(--green-deep,#154e36);font-style:italic;}
.lib-head .legend{display:flex;gap:24px;list-style:none;padding:0;
  margin:0;font:400 12.5px/1 var(--sc-sans,Inter),sans-serif;
  color:var(--ink-2,#2b3e54);flex-wrap:wrap;}
.lib-head .legend li{display:flex;align-items:center;}
.lib-head .legend .dot{width:8px;height:8px;border-radius:50%;
  display:inline-block;margin-right:10px;}
.lib-head .legend .dot.live{background:var(--green-deep,#154e36);}
.lib-head .legend .dot.computed{background:var(--ink-deep,#0e1a29);}
.lib-head .legend .dot.needs{background:var(--coral,#b04a3a);}
.lib-head .legend .dot.illustrative{background:var(--gold,#a08227);}
@media (max-width:960px){
  .lib-head h1{font-size:36px;}
}
/* Keyword-search bar (Phase 2 functionality lift). */
.lib-search{display:flex;gap:8px;margin:0 0 36px;}
.lib-search input{flex:1;font:400 14px var(--sc-sans,Inter),sans-serif;
  color:var(--ink,#16263a);background:var(--paper-card,#fefcf3);
  border:1px solid var(--rule,#c9bf9c);border-radius:2px;
  padding:11px 14px;min-height:42px;}
.lib-search input:focus{outline:2px solid var(--green-deep,#154e36);
  outline-offset:-1px;border-color:var(--green-deep,#154e36);}
.lib-search input::placeholder{color:var(--muted-2,#9a9e8a);}
.lib-search button{font:500 12px/1 var(--sc-sans,Inter),sans-serif;
  color:#fff;background:var(--green-deep,#154e36);border:0;
  border-radius:2px;padding:0 22px;letter-spacing:.08em;
  text-transform:uppercase;cursor:pointer;}
.lib-search button:hover{background:var(--green-2,#2d8964);}
.lib-search .ghost{background:transparent;border:1px solid var(--ink,#16263a);
  color:var(--ink,#16263a);padding:0 14px;text-decoration:none;
  display:inline-flex;align-items:center;}
.lib-search .ghost:hover{background:var(--paper-hi,#fbf6e8);}
/* No-results card — same shape as the editorial empty state. */
.lib-empty{padding:36px 32px;background:var(--paper-card,#fefcf3);
  border:1px solid var(--rule,#c9bf9c);text-align:center;margin:0 0 32px;}
.lib-empty .eyebrow{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.18em;text-transform:uppercase;
  color:var(--coral,#b04a3a);margin:0 0 14px;}
.lib-empty h3{font:400 22px/1.2 var(--sc-serif,Georgia),serif;
  color:var(--ink,#16263a);margin:0 0 8px;}
.lib-empty p{font:400 14px/1.55 var(--sc-sans,Inter),sans-serif;
  color:var(--ink-2,#2b3e54);margin:0;}
</style>
"""
    # Meta-line quotes both totals AND the filtered counts (when a
    # filter is active) so the partner sees what the keyword matched.
    if q_clean:
        meta_line = (
            f'{n_matched_entries} OF {total_entries} ENTRIES MATCH '
            f'"{html.escape(q_clean)}" · {n_matched_sections} OF '
            f'{n_sections} SECTIONS'
        )
    else:
        meta_line = (
            f'{n_sections} SECTIONS · {total_entries} DOCUMENTED ENTRIES'
        )
    head_block = (
        _lib_head_css
        + '<header class="lib-head">'
        '<div class="eyebrow"><span class="dash"></span>METHODOLOGY</div>'
        '<h1>Research Library</h1>'
        f'<div class="meta">{meta_line}</div>'
        '<p class="lede">'
        '<em>Where the platform shows its work.</em> '
        'Reference documentation for every metric, formula, model, '
        'and scoring rubric in the platform — with citations to the '
        'source documents and assumptions that back each one.</p>'
        '<ul class="legend">'
        '<li><span class="dot live"></span>Live data</li>'
        '<li><span class="dot computed"></span>Computed</li>'
        '<li><span class="dot needs"></span>Needs data</li>'
        '<li><span class="dot illustrative"></span>Illustrative</li>'
        '</ul>'
        '</header>'
    )
    # Keyword search bar — GET form, no JavaScript needed.
    q_escaped = html.escape(q_clean, quote=True)
    search_bar = (
        '<form class="lib-search" method="GET" action="/methodology" '
        'role="search" aria-label="Search the methodology library">'
        f'<input type="search" name="q" value="{q_escaped}" '
        'placeholder="Search by metric, model, or phrase from the docs…" '
        'autocomplete="off" />'
        '<button type="submit">Search</button>'
        + (
            '<a class="ghost" href="/methodology">Clear</a>'
            if q_clean else ""
        )
        + '</form>'
    )
    # Honest no-results state when a filter is active and matched
    # nothing — sets the eyebrow to coral and quotes the real query
    # so the partner knows what was searched (not editorial filler).
    if q_clean and not sections_for_render:
        empty_state = (
            '<div class="lib-empty">'
            '<div class="eyebrow">No results · adjust filters</div>'
            f'<h3>Nothing matches "{html.escape(q_clean)}".</h3>'
            f'<p>The library has {total_entries} entries across '
            f'{n_sections} sections — try a broader keyword, or '
            '<a href="/methodology" style="color:var(--green-deep);">'
            'clear the filter</a> to see the full catalog.</p>'
            '</div>'
        )
    else:
        empty_state = ""

    # ── Cross-links to sibling reference surfaces ──
    # Replaces the legacy `cad-card h3 color:brand_accent` trio with
    # the editorial link-list pattern (Tier-2 §2.6): hairline card,
    # mono eyebrow, sans title + desc, mono arrow.
    extra_links = (
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);'
        'gap:16px;margin:32px 0;">'
        '<a href="/data" style="display:block;padding:22px 24px;'
        'background:var(--paper-card,#fefcf3);'
        'border:1px solid var(--rule,#c9bf9c);text-decoration:none;'
        'color:inherit;">'
        '<div style="font:500 10px/1 var(--sc-mono,monospace);'
        'letter-spacing:.14em;text-transform:uppercase;'
        'color:var(--green-deep,#154e36);margin-bottom:8px;">'
        'Sibling reference</div>'
        '<div style="font:600 15px/1.3 var(--sc-sans,Inter),sans-serif;'
        'color:var(--ink,#16263a);margin-bottom:6px;">'
        'Data Explorer →</div>'
        '<div style="font:400 13px/1.5 var(--sc-sans,Inter),sans-serif;'
        'color:var(--ink-3,#506478);">'
        'Browse all public data sources powering the platform.</div></a>'
        '<a href="/verticals" style="display:block;padding:22px 24px;'
        'background:var(--paper-card,#fefcf3);'
        'border:1px solid var(--rule,#c9bf9c);text-decoration:none;'
        'color:inherit;">'
        '<div style="font:500 10px/1 var(--sc-mono,monospace);'
        'letter-spacing:.14em;text-transform:uppercase;'
        'color:var(--green-deep,#154e36);margin-bottom:8px;">'
        'Sibling reference</div>'
        '<div style="font:600 15px/1.3 var(--sc-sans,Inter),sans-serif;'
        'color:var(--ink,#16263a);margin-bottom:6px;">'
        'Healthcare Verticals →</div>'
        '<div style="font:400 13px/1.5 var(--sc-sans,Inter),sans-serif;'
        'color:var(--ink-3,#506478);">'
        'ASC, Behavioral Health, MSO bridges — sector-level lenses.</div></a>'
        '<a href="/metric-glossary" style="display:block;padding:22px 24px;'
        'background:var(--paper-card,#fefcf3);'
        'border:1px solid var(--rule,#c9bf9c);text-decoration:none;'
        'color:inherit;">'
        '<div style="font:500 10px/1 var(--sc-mono,monospace);'
        'letter-spacing:.14em;text-transform:uppercase;'
        'color:var(--green-deep,#154e36);margin-bottom:8px;">'
        'Sibling reference</div>'
        '<div style="font:600 15px/1.3 var(--sc-sans,Inter),sans-serif;'
        'color:var(--ink,#16263a);margin-bottom:6px;">'
        'Metric Glossary →</div>'
        '<div style="font:400 13px/1.5 var(--sc-sans,Inter),sans-serif;'
        'color:var(--ink-3,#506478);">'
        'Plain-language definitions for every KPI the platform reads.</div></a>'
        '</div>'
    )

    next_up = ck_next_section(
        "Open the metric glossary",
        "/metric-glossary",
        eyebrow="Continue —",
        italic_word="glossary",
    )
    body = (
        head_block + search_bar + empty_state
        + sections + extra_links + next_up
    )

    return chartis_shell(
        body, "Methodology",
        active_nav="/methodology",
        subtitle="Research library, model documentation & methodology references",
    )
