"""Target Screener — unified entry to target discovery (Source section).

Route: GET /target-screener. One clear surface that unifies the three
overlapping screeners (Deal Sourcing, Hospital Screener, Predictive Screener),
which all search the SAME public CMS / HCRIS hospital universe — they differ
only in *how* you find targets, not in what they search. This page explains the
three modes and routes to each; the underlying screener routes are preserved
unchanged (backward compatible) and deepened later. No data computed here.
"""
from __future__ import annotations

from typing import Dict, List, Optional


# Each mode reuses an existing, unchanged screener route.
_MODES = [
    {"key": "sourcing", "label": "Thesis Sourcing", "href": "/source",
     "when": "Start from a saved investment thesis and match it to the "
             "universe.",
     "how": "Thesis-driven · ranks providers by fit to a thesis profile."},
    {"key": "hospital", "label": "Hospital Screener", "href": "/screen",
     "when": "Hand-filter the hospital universe by region, beds, and margin.",
     "how": "Manual filters · you set the criteria."},
    {"key": "predictive", "label": "Predictive Screener", "href": "/predictive-screener",
     "when": "Surface candidates an ML model ranks by predicted RCM uplift.",
     "how": "Model-ranked · scored over the public HCRIS universe."},
]

_CSS = """
.ts-modes{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:18px 0 var(--sc-s-5);}
@media (max-width:900px){.ts-modes{grid-template-columns:1fr;}}
.ts-mode{display:flex;flex-direction:column;gap:8px;background:var(--sc-paper,#faf6ec);
 border:1px solid var(--sc-rule,#c9c1ac);border-top:3px solid var(--sc-teal,#155752);
 padding:18px 20px;text-decoration:none;transition:box-shadow .12s,transform .12s;}
.ts-mode:hover{box-shadow:var(--sc-shadow-2,0 8px 24px rgba(11,32,55,.14));}
.ts-mode.is-active{border-top-color:var(--sc-navy,#15202b);background:var(--sc-bone,#f3eddb);}
.ts-mode-eyebrow{font-family:var(--sc-mono);font-size:10px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);}
.ts-mode-label{font-family:var(--sc-serif);font-size:21px;color:var(--sc-navy,#15202b);line-height:1.1;}
.ts-mode-when{font-family:var(--sc-serif);font-size:14px;line-height:1.5;color:var(--sc-text,#2a3a4a);}
.ts-mode-how{font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.04em;color:var(--sc-text-dim,#6a7480);}
.ts-mode-go{margin-top:auto;font-family:var(--sc-mono);font-size:10px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-teal,#155752);}
.ts-note{font-family:var(--sc-serif);font-style:italic;font-size:13px;line-height:1.5;
 color:var(--sc-text-dim,#6a7480);background:var(--sc-bone,#f3eddb);padding:12px 16px;
 border-left:3px solid var(--sc-teal,#155752);max-width:80ch;}
"""


def render_target_screener(qs: Optional[Dict[str, List[str]]] = None) -> str:
    from ._chartis_kit import (chartis_shell, ck_data_universe, ck_page_title,
                               ck_panel, ck_source_purpose)
    qs = qs or {}
    active = (qs.get("mode") or [""])[0].strip().lower()

    title = ck_page_title(
        "Target Screener", eyebrow="SOURCE · /target-screener",
        meta="one entry · three modes · same CMS/HCRIS universe",
    ) + '<div style="margin:8px 0 0;">' + ck_data_universe("cms") + '</div>'

    source_purpose = ck_source_purpose(
        purpose="Find acquisition targets in the public hospital universe — by thesis, filters, or model rank — before committing diligence effort.",
        universe="cms",
        source="CMS / HCRIS public hospital universe (market data, not your deals).",
        next_action="Promote a result into the Pipeline to track it",
        next_href="/pipeline",
    )

    explainer = (
        '<p class="ck-section-body" style="max-width:74ch;margin:14px 0 0;">'
        '<em>One place to find targets.</em> Pick how you want to search the '
        'public hospital universe — by <strong>thesis</strong>, by '
        '<strong>hand-set filters</strong>, or by <strong>model rank</strong>. '
        'All three read the same CMS / HCRIS data; they differ only in how you '
        'surface candidates.</p>'
    )

    cards = "".join(
        f'<a class="ts-mode{" is-active" if m["key"] == active else ""}" '
        f'href="{m["href"]}">'
        f'<span class="ts-mode-eyebrow">Mode</span>'
        f'<span class="ts-mode-label">{m["label"]}</span>'
        f'<span class="ts-mode-when">{m["when"]}</span>'
        f'<span class="ts-mode-how">{m["how"]}</span>'
        f'<span class="ts-mode-go">Open {m["label"]} &rarr;</span>'
        '</a>'
        for m in _MODES
    )
    note = (
        '<p class="ts-note">All three modes search the same public CMS / HCRIS '
        'hospital universe — this is market data, not your deals. Promote a '
        'result into the Pipeline to start tracking it as an opportunity.</p>'
    )

    market_link = ck_panel(
        'Rank and score geographic markets on real public data before screening '
        'targets in them — <a href="/geo-intel" style="font-weight:600">Geographic '
        'Intelligence</a> (state/metro/county demographics, provider supply, MA, '
        'shortage areas, SDOH — all real) and '
        '<a href="/market-intel/geo" style="font-weight:600">Geographic Market '
        'Intelligence &rarr;</a> '
        '<span style="opacity:0.7">Market/area context, not provider-specific.</span>',
        title="Screen the market, not just the target")
    next_actions = ck_panel(
        '<p class="ck-section-body">Each mode answers a different sourcing '
        'question: <b>Thesis Sourcing</b> — "where does my thesis fit?"; '
        '<b>filters</b> — "which hospitals match hard criteria?"; '
        '<b>model rank</b> — "which look most investable by the public signals?" '
        'Next: open a candidate\'s <a href="/diligence/hcris-xray" class="ck-link">'
        'HCRIS X-Ray</a> or <a href="/diligence/xray" class="ck-link">CMS X-Ray</a>, '
        'check its <a href="/geo-intel" class="ck-link">market</a>, then '
        '<a href="/pipeline" class="ck-link">promote it to Pipeline</a>.</p>',
        title="What each mode answers · next steps")
    body = (
        title + source_purpose + explainer
        + f'<div class="ts-modes">{cards}</div>'
        + market_link
        + next_actions
        + ck_panel(note, title="Same universe, three ways in")
    )
    return chartis_shell(body, "Target Screener", active_nav="/target-screener",
                         extra_css=_CSS)
