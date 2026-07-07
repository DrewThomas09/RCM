"""Commercial Due Diligence hub — /cdd.

The desk had strong CDD ingredients (TAM/SAM builder, demand forecast,
geographic market, competitor intel, payer analytics) scattered across
four nav sections with nothing presenting them *as a CDD workflow*. An
associate staffed on a commercial sprint had to already know the
product to find the right page. This hub lays the canonical CDD
structure over the existing surfaces — market, competition, customers,
pricing/reimbursement, deliverables, plus the exhibit engines that
render the underlying analytics — so the sprint has a table of
contents, with each module listing its surfaces in the order the
workstream actually runs.

Pure navigation page: every card links to an existing route. No data
computed here — but the honesty dot on every row IS derived (per-route
from ``rcm_mc.diligence.surface_status``), so a partner sees inline
whether a surface runs on live data, a computed model, or an
illustrative worked example. That is the scent-of-information the hub
owes an associate before they click.

Rendered in the flagship section-landing idiom the /diligence index was
rebuilt to — strict Tier-1 5-block masthead, provenance-wrapped
coverage tiles, a jump-row + type-to-filter over the catalog, and
grouped ``ck_panel`` pillars whose per-row dots come from the
surface-status registry — so the CDD hub and the diligence front door
read as the same publication. Page-scoped CSS only (``cdh-`` prefix),
kit CSS custom properties with their canonical fallbacks — no bespoke
hexes.
"""
from __future__ import annotations

import html as _html
from collections import Counter

# (module title, blurb, [(label, href, one-liner), ...])
_MODULES = [
    ("1 · Market size & growth",
     "How big is the market, and is the growth real or demographic "
     "wishful thinking?",
     [
         ("TAM / SAM / SOM Builder", "/diligence/tam-sam",
          "Driver-tree market sizing with sourced inputs and xlsx export"),
         ("Demand Forecaster", "/demand-forecast",
          "10-year volume projection by age band with payer-mix shift"),
         ("Growth Runway", "/growth-runway",
          "Penetration S-curves and comparable expansion precedents"),
         ("Geographic Market Analyzer", "/geo-market",
          "CBSA-level attractiveness scoring and market-entry tiers"),
         ("Infusion Market Scan", "/diligence/infusion-markets",
          "Worked example: every state ranked for an infusion roll-up"),
     ]),
    ("2 · Competitive landscape",
     "Who else is in the market, how concentrated is it, and where does "
     "the target actually win?",
     [
         ("Competitive Intelligence", "/competitive-intel",
          "Share landscape, strategic moves, capability gap analysis"),
         ("Industry Intelligence", "/industry",
          "Sector deep dives: facility counts, chains, consolidation HHI"),
         ("Win/Loss Analyzer", "/win-loss",
          "Head-to-head conversion record and loss-reason decomposition"),
         ("Find Comps", "/find-comps",
          "Corpus comparables by numeric deal profile"),
     ]),
    ("3 · Customer evidence",
     "What do customers say — and does revenue stay when you stop "
     "asking nicely?",
     [
         ("Voice of Customer / Survey", "/voc-survey",
          "NPS by segment, KPC gap matrix, willingness-to-pay"),
         ("Payer Intelligence", "/payer-intelligence",
          "Payer-mix regimes vs realized MOIC across the corpus"),
         ("Direct-to-Employer Analyzer", "/direct-employer",
          "Employer-contract economics and concentration"),
         ("HCIT / SaaS Analyzer", "/hcit-platform",
          "ARR quality: NRR, gross margin, Rule of 40"),
     ]),
    ("4 · Pricing, reimbursement & cost environment",
     "Who sets the price in this market — the target, the payer, or "
     "CMS — and does the cost side let the margin hold?",
     [
         ("US Payer System", "/payer-system",
          "MA bid/benchmark/rebate, star QBP cliff, Part D IRA redesign, ACA APTC cliff"),
         ("Pricing Power Analyzer", "/pricing-power",
          "Elasticity curves and segment-optimal price moves"),
         ("Medicare Rate Environment", "/rate-environment",
          "Setting-level CMS payment updates with blended dollar impact"),
         ("MA Penetration", "/ma-penetration",
          "State-level Medicare Advantage exposure with footprint scorer"),
         ("Healthcare Labor Market", "/labor-market",
          "Role-level wage inflation and staffing fragility with EBITDA "
          "stress"),
         ("Market Rates", "/market-rates",
          "Negotiated-rate benchmarks"),
         ("Market Intel (Comps & News)", "/market-intel",
          "Public comps, transaction multiples, curated sector news"),
         ("Sector Momentum", "/sector-momentum",
          "Deal-activity acceleration by sector"),
     ]),
    ("5 · Deliverables",
     "Turn the work into the readout: models first, then the memo.",
     [
         ("Excel Model Templates", "/excel-templates",
          "Live-formula workbooks: market model, payer sensitivity, "
          "cohort/NRR, quick LBO"),
         ("IC Memo Generator", "/ic-memo-gen",
          "Investment-committee memo assembly"),
         ("QoE Memo", "/diligence/qoe-memo",
          "Quality-of-earnings memo from the diligence packet"),
         ("Thesis Screening", "/deal-screening",
          "Screen the thesis against the deal corpus"),
         ("Chart Builder", "/chart-builder",
          "Deck-ready CDD charts (waterfall, marimekko, 23 types) from "
          "a pasted table"),
         ("Exhibit Composer", "/exhibit",
          "Lay up to four charts on one 16:9 deck slide"),
     ]),
    ("6 · Analytics engines",
     "The registered CDD exhibit engines themselves, rendered with their "
     "reconciliations, diligence flags, and sourced footnotes.",
     [
         ("CDD Analytics Engines", "/cdd/tools",
          "Every registered exhibit (TAM/SAM, profit pools, benchmarking "
          "reference layer, bolsters) rendered in the partner view"),
     ]),
]

# Mono-caps pillar eyebrows, aligned 1:1 with _MODULES above. Kept as a
# parallel constant (not a fourth tuple element) so the test that unpacks
# ``for title, _, _ in _MODULES`` keeps its exact 3-tuple shape. Each
# names the workstream step the module answers — the scent-of-information
# above the serif pillar title, and the label used in the jump-row.
_PILLAR_EYEBROWS = (
    "SIZE THE MARKET",
    "MAP THE COMPETITION",
    "TEST THE CUSTOMERS",
    "PRESSURE-TEST PRICING",
    "ASSEMBLE THE READOUT",
    "RUN THE ENGINES",
)

# ── Honesty tiers ───────────────────────────────────────────────────
# surface_status tier key → (css-class stem, partner label, short mono
# tag). The css classes paint the SAME four canonical legend tokens the
# kit uses (green-deep / ink-deep / coral / gold-bright) so the CDD hub
# tiers a route the same color as the 48 pages on the kit legend and the
# /diligence index. Derived per-route — never hand-set — so the catalog
# can't overstate what is real.
_TIER_INFO: dict[str, tuple[str, str, str]] = {
    "green": ("live", "Live data", "LIVE"),
    "navy": ("computed", "Computed", "COMPUTED"),
    "data_required": ("needs", "Needs data", "NEEDS DATA"),
    "yellow": ("illustrative", "Illustrative", "ILLUSTRATIVE"),
    "red": ("placeholder", "Placeholder", "PLACEHOLDER"),
    "unknown": ("unknown", "Status unavailable", "UNVERIFIED"),
}
_TIER_ORDER = ("green", "navy", "data_required", "yellow", "red", "unknown")
# The four buckets always shown in the legend (matches the kit's canonical
# 4-bucket legend); rare tiers surface only when actually present.
_LEGEND_TIERS = ("green", "navy", "data_required", "yellow")


def _tier(href: str) -> str:
    """Honesty tier for a route, from the surface-status registry.

    A classification failure maps to an explicit ``unknown`` bucket
    (neutral dot, "Status unavailable") rather than silently defaulting
    into a confident tier — the honesty signal must not lie under
    failure.
    """
    try:
        from ..diligence.surface_status import classify_surface
        return classify_surface(href.split("?")[0]).get("tier", "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


def _tier_counts(modules) -> Counter:
    return Counter(
        _tier(href) for _t, _b, links in modules for _l, href, _d in links
    )


# ── Page CSS (kit vars with canonical fallbacks only — no new hexes) ──
_CSS = (
    '<style>'
    # -- masthead: strict Tier-1 5-block head --
    '.cdh-head{padding:0 0 30px;margin:0 0 26px;'
    'border-bottom:1px solid var(--rule-soft,#ddd1ac);}'
    '.cdh-head .eyebrow{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.18em;text-transform:uppercase;'
    'color:var(--green-deep,#154e36);display:flex;align-items:center;'
    'gap:12px;margin:0 0 18px;}'
    '.cdh-head .eyebrow .dash{width:24px;height:1px;'
    'background:var(--green-deep,#154e36);}'
    '.cdh-head h1{font:400 44px/1.05 var(--sc-serif,Georgia),serif;'
    'letter-spacing:-.015em;color:var(--ink,#16263a);margin:0 0 14px;}'
    '.cdh-head .meta{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.14em;text-transform:uppercase;'
    'color:var(--muted,#7a8595);margin:0 0 18px;}'
    '.cdh-head .lede{font:400 italic 16.5px/1.6 var(--sc-serif,Georgia),serif;'
    'color:var(--ink-2,#2b3e54);max-width:68ch;margin:0 0 14px;}'
    '.cdh-head .lede em{color:var(--green-deep,#154e36);font-style:italic;}'
    '.cdh-head .lede.roman{font-style:normal;}'
    '.cdh-head .source-note{font:500 10px/1.4 var(--sc-mono,monospace);'
    'letter-spacing:.14em;text-transform:uppercase;'
    'color:var(--muted-2,#9a9e8a);margin:0 0 18px;max-width:72ch;}'
    # -- merged legend-with-counts --
    '.cdh-legend{display:flex;gap:22px;list-style:none;padding:0;margin:0;'
    'font:400 12.5px/1 var(--sc-sans,Inter),sans-serif;'
    'color:var(--ink-2,#2b3e54);flex-wrap:wrap;}'
    '.cdh-legend li{display:flex;align-items:center;gap:8px;}'
    '.cdh-legend .cdh-legend-n{font:500 12px/1 var(--sc-mono,monospace);'
    'color:var(--muted,#7a8595);}'
    # -- honesty dots: class-based, kit legend tokens (no inline colors) --
    '.cdh-dot{width:8px;height:8px;border-radius:50%;flex:none;'
    'display:inline-block;position:relative;top:1px;}'
    '.cdh-dot.live{background:var(--green-deep,#154e36);}'
    '.cdh-dot.computed{background:var(--ink-deep,#0e1a29);}'
    '.cdh-dot.needs{background:var(--coral,#b04a3a);}'
    '.cdh-dot.illustrative{background:var(--gold-bright,#c9a227);}'
    '.cdh-dot.placeholder{background:var(--sc-negative,#b5321e);}'
    '.cdh-dot.unknown{background:var(--sc-text-faint,#8b94a0);}'
    # -- coverage KPI strip --
    '.cdh-kpis{grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;'
    'margin:0 0 24px;}'
    '@media (max-width:960px){.cdh-kpis{grid-template-columns:'
    'repeat(2,minmax(0,1fr));}}'
    '@media (max-width:560px){.cdh-kpis{grid-template-columns:1fr;}}'
    # -- toolbar: mono jump-row + type-to-filter --
    '.cdh-toolbar{display:flex;align-items:center;'
    'justify-content:space-between;gap:14px 24px;flex-wrap:wrap;'
    'margin:0 0 22px;}'
    '.cdh-jump{display:flex;flex-wrap:wrap;gap:6px 18px;}'
    '.cdh-jump a{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.12em;text-transform:uppercase;'
    'color:var(--ink-2,#2b3e54);text-decoration:none;display:inline-flex;'
    'align-items:center;gap:7px;padding:6px 0;'
    'border-bottom:1px solid transparent;}'
    '.cdh-jump a .n{color:var(--green-deep,#154e36);}'
    '.cdh-jump a:hover{border-bottom-color:var(--green-deep,#154e36);'
    'color:var(--ink,#16263a);}'
    '.cdh-jump a:focus-visible{outline:2px solid var(--green-deep,#154e36);'
    'outline-offset:2px;}'
    '.cdh-filter{display:flex;align-items:center;gap:10px;}'
    '.cdh-filter input{font:400 13px/1.2 var(--sc-sans,Inter),sans-serif;'
    'color:var(--ink,#16263a);background:var(--paper-card,#fefcf3);'
    'border:1px solid var(--rule,#c9bf9c);border-radius:2px;'
    'padding:8px 12px;min-width:230px;}'
    '.cdh-filter input:focus-visible{outline:2px solid '
    'var(--green-deep,#154e36);outline-offset:-1px;}'
    '.cdh-filter-count{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.08em;text-transform:uppercase;'
    'color:var(--muted,#7a8595);}'
    '.cdh-no-match{font:400 italic 14px/1.5 var(--sc-serif,Georgia),serif;'
    'color:var(--sc-text-dim,#465366);padding:18px 0;}'
    '.cdh-no-match button{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.08em;text-transform:uppercase;cursor:pointer;'
    'color:var(--green-deep,#154e36);background:none;border:none;'
    'border-bottom:1px solid var(--green-deep,#154e36);padding:0 0 2px;}'
    '.cdh-no-match button:focus-visible{outline:2px solid '
    'var(--green-deep,#154e36);outline-offset:2px;}'
    # -- pillar catalog: two self-balancing columns so an uneven pillar
    #    (module 6 has one surface, module 4 has eight) never stretches
    #    its neighbour into dead whitespace --
    '.cdh-catalog{columns:2;column-gap:24px;margin:0 0 24px;}'
    '@media (max-width:1100px){.cdh-catalog{columns:1;}}'
    '.cdh-catalog .ck-panel{break-inside:avoid;'
    '-webkit-column-break-inside:avoid;page-break-inside:avoid;'
    'margin:0 0 24px;scroll-margin-top:86px;}'
    '.cdh-pillar-head{display:flex;flex-direction:column;gap:8px;'
    'border-bottom:1px solid var(--sc-rule,#d6cfc0);padding-bottom:16px;}'
    '.cdh-pillar-title{font-family:var(--sc-serif,Georgia,serif);'
    'font-weight:500;font-size:22px;color:var(--sc-navy,#0b2341);'
    'margin:2px 0 0;letter-spacing:-0.01em;}'
    '.cdh-pillar-meta{font:500 10.5px/1.5 var(--sc-mono,monospace);'
    'letter-spacing:.12em;text-transform:uppercase;'
    'color:var(--muted,#7a8595);}'
    '.cdh-pillar-body{font-family:var(--sc-serif,Georgia,serif);'
    'font-size:13.5px;line-height:1.6;color:var(--sc-text-dim,#465366);'
    'margin:0;max-width:48ch;}'
    # -- link rows: non-reflowing hover (background + arrow nudge) with a
    #    keyboard-parallel focus-visible state --
    '.cdh-link-list{display:flex;flex-direction:column;}'
    '.cdh-link{display:block;text-decoration:none;color:inherit;'
    'padding:12px;margin:0 -12px;border-radius:2px;'
    'border-bottom:1px solid var(--sc-rule,#d6cfc0);'
    'transition:background .12s;}'
    '.cdh-link:last-child{border-bottom:0;}'
    '.cdh-link:hover{background:var(--sc-bone,#ece5d6);}'
    '.cdh-link:focus-visible{background:var(--sc-bone,#ece5d6);'
    'outline:2px solid var(--green-deep,#154e36);outline-offset:-2px;}'
    '.cdh-link:hover .cdh-arrow,.cdh-link:focus-visible .cdh-arrow{'
    'color:var(--sc-teal,#155752);transform:translateX(2px);}'
    '.cdh-row{display:flex;align-items:baseline;gap:9px;}'
    '.cdh-label{font-family:var(--sc-sans,Inter,sans-serif);'
    'font-weight:600;font-size:14px;color:var(--sc-navy,#0b2341);}'
    '.cdh-tag{font:500 9.5px/1 var(--sc-mono,monospace);'
    'letter-spacing:.1em;text-transform:uppercase;padding:3px 6px;'
    'border-radius:2px;flex:none;position:relative;top:-1px;}'
    '.cdh-tag.needs{color:var(--coral,#b04a3a);'
    'border:1px solid var(--coral,#b04a3a);}'
    '.cdh-tag.illustrative{color:var(--gold,#a08227);'
    'border:1px solid var(--gold-bright,#c9a227);}'
    '.cdh-tag.placeholder{color:var(--sc-negative,#b5321e);'
    'border:1px solid var(--sc-negative,#b5321e);}'
    '.cdh-tag.unknown{color:var(--sc-text-faint,#8b94a0);'
    'border:1px solid var(--sc-text-faint,#8b94a0);}'
    '.cdh-arrow{margin-left:auto;'
    'font-family:var(--sc-sans,Inter,sans-serif);font-size:14px;'
    'color:var(--sc-text-faint,#7a8699);'
    'transition:color .12s,transform .12s;}'
    '.cdh-blurb{font-family:var(--sc-serif,Georgia,serif);'
    'font-size:12.5px;color:var(--sc-text-dim,#465366);line-height:1.45;'
    'margin-top:4px;padding-left:17px;}'
    '.cdh-hidden{display:none !important;}'
    '@media (max-width:960px){.cdh-head h1{font-size:36px;}}'
    '@media (prefers-reduced-motion:reduce){'
    '.cdh-link,.cdh-arrow{transition:none;}'
    '.cdh-link:hover .cdh-arrow,'
    '.cdh-link:focus-visible .cdh-arrow{transform:none;}}'
    '</style>'
)

# Type-to-filter over the catalog rows. Vanilla, self-contained,
# idempotent install guard; hides any pillar whose rows all filtered out.
_FILTER_JS = (
    '<script>(function(){"use strict";'
    'var input=document.getElementById("cdh-filter-input");'
    'if(!input||window.__cdhFilterInstalled){return;}'
    'window.__cdhFilterInstalled=true;'
    'var links=Array.prototype.slice.call('
    'document.querySelectorAll(".cdh-catalog .cdh-link"));'
    'var panels=Array.prototype.slice.call('
    'document.querySelectorAll(".cdh-catalog .ck-panel"));'
    'var count=document.getElementById("cdh-filter-count");'
    'var noMatch=document.getElementById("cdh-no-match");'
    'var clearBtn=document.getElementById("cdh-filter-clear");'
    'var total=links.length;'
    'function apply(){'
    'var q=input.value.trim().toLowerCase();'
    'var shown=0;'
    'links.forEach(function(a){'
    'var hit=!q||a.textContent.toLowerCase().indexOf(q)!==-1;'
    'a.classList.toggle("cdh-hidden",!hit);'
    'if(hit){shown+=1;}});'
    'panels.forEach(function(p){'
    'var any=p.querySelector(".cdh-link:not(.cdh-hidden)");'
    'p.classList.toggle("cdh-hidden",!any);});'
    'if(count){count.textContent=q?shown+" of "+total+" shown":"";}'
    'if(noMatch){noMatch.hidden=!(q&&shown===0);}}'
    'input.addEventListener("input",apply);'
    'if(clearBtn){clearBtn.addEventListener("click",function(){'
    'input.value="";apply();input.focus();});}'
    '})();</script>'
)


def _legend(tiers: Counter) -> str:
    """Single legend row with real per-tier counts — the four canonical
    buckets always shown, rare tiers appended only when present."""
    from ._chartis_kit import ck_fmt_number
    keys = list(_LEGEND_TIERS) + [
        k for k in _TIER_ORDER
        if k not in _LEGEND_TIERS and tiers.get(k)
    ]
    items = []
    for key in keys:
        cls, label, _short = _TIER_INFO[key]
        items.append(
            f'<li><span class="cdh-dot {cls}" aria-hidden="true"></span>'
            f'{_html.escape(label)}'
            f'<span class="cdh-legend-n">· '
            f'{ck_fmt_number(tiers.get(key, 0))}</span></li>'
        )
    return '<ul class="cdh-legend">' + "".join(items) + '</ul>'


def _head(n_surfaces: int, n_pillars: int, tiers: Counter) -> str:
    """Strict Tier-1 5-block masthead: eyebrow+dash → serif h1 → mono
    meta with real counts → italic-first-phrase lede in green-deep →
    roman explainer → source note → legend-with-counts."""
    return (
        '<header class="cdh-head">'
        '<div class="eyebrow"><span class="dash"></span>DILIGENCE · '
        'CDD WORKFLOW</div>'
        '<h1>Commercial Due Diligence Hub</h1>'
        f'<div class="meta">{n_surfaces} SURFACES · {n_pillars} PILLARS'
        '</div>'
        '<p class="lede"><em>The commercial sprint, in running order.</em> '
        'This hub lays the desk\'s surfaces over the flow a commercial '
        'sprint actually runs, so an associate starts here instead of '
        'trawling the nav — size the market, map the competition, test the '
        'customer evidence, pressure-test pricing and reimbursement, '
        'assemble the deliverables, then run the exhibit engines that '
        'render the underlying analytics.</p>'
        '<p class="lede roman">Each row names a surface and the one-line '
        'job it does. The status dot is derived from the surface-status '
        'registry on every render — green for live data, ink for a model '
        'computed off your inputs, coral where your data upload is still '
        'needed, gold for an illustrative worked example — so this catalog '
        'can never overstate what is real.</p>'
        '<p class="source-note">Source: curated catalog of CDD surfaces '
        'across six workstream modules · honesty tiers derived per-route '
        'from rcm_mc.diligence.surface_status</p>'
        f'{_legend(tiers)}'
        '</header>'
    )


def _kpi_strip(n_surfaces: int, n_pillars: int, tiers: Counter) -> str:
    """Coverage stat tiles under the head — every value computed from
    ``_MODULES`` + the surface-status registry and wrapped in a
    provenance tooltip so a partner can ask "where does this number come
    from?" without leaving the page."""
    from ._chartis_kit import (
        ck_fmt_number,
        ck_fmt_percent,
        ck_kpi_block,
        ck_provenance_tooltip,
    )
    live = tiers.get("green", 0)
    computed = tiers.get("navy", 0)
    needs = tiers.get("data_required", 0)
    illus = tiers.get("yellow", 0)
    not_live = n_surfaces - live
    surfaces_value = ck_provenance_tooltip(
        "CDD surfaces",
        f'<span class="mn">{ck_fmt_number(n_surfaces)}</span>',
        explainer=(
            "Counted from the curated module catalog on every render — "
            "the same list the panels below draw from, so the number can "
            "never drift from what is actually linked."
        ),
    )
    live_share_value = ck_provenance_tooltip(
        "Live-data share",
        f'<span class="mn">'
        f'{ck_fmt_percent(live / n_surfaces if n_surfaces else None)}</span>',
        explainer=(
            f"{ck_fmt_number(live)} of {ck_fmt_number(n_surfaces)} "
            "surfaces run on live data (CMS/HCRIS public sources or your "
            "own deal and portfolio records). Derived per-route from "
            "rcm_mc.diligence.surface_status; recomputed on every render."
        ),
        inject_css=False,
    )
    computed_value = ck_provenance_tooltip(
        "Computed models",
        f'<span class="mn">{ck_fmt_number(computed)}</span>',
        explainer=(
            "Legitimate diligence calculators: illustrative defaults, but "
            "the output reflects the inputs you give them. Honest as "
            "tools; classified per-route by surface_status."
        ),
        inject_css=False,
    )
    not_live_value = ck_provenance_tooltip(
        "Not yet live",
        f'<span class="mn">{ck_fmt_number(not_live)}</span>',
        explainer=(
            f"Surfaces not running on live data: {ck_fmt_number(computed)} "
            f"computed models, {ck_fmt_number(needs)} awaiting a data "
            f"upload, {ck_fmt_number(illus)} on an illustrative worked "
            "example. The per-row dots below say which is which."
        ),
        inject_css=False,
    )
    return (
        '<div class="ck-kpi-grid cdh-kpis">'
        + ck_kpi_block(
            "Surfaces", surfaces_value,
            f"across {ck_fmt_number(n_pillars)} modules")
        + ck_kpi_block(
            "Live-Data Share", live_share_value,
            f"{ck_fmt_number(live)} surfaces on real data")
        + ck_kpi_block(
            "Computed Models", computed_value,
            "calculators off your inputs")
        + ck_kpi_block(
            "Not Yet Live", not_live_value,
            f"{ck_fmt_number(needs)} need data · "
            f"{ck_fmt_number(illus)} illustrative")
        + '</div>'
    )


def _toolbar(n_surfaces: int) -> str:
    """Mono jump-row (module ordinal → panel anchor) + type-to-filter."""
    jumps = []
    for i, eyebrow in enumerate(_PILLAR_EYEBROWS, start=1):
        jumps.append(
            f'<a href="#cdd-{i:02d}">'
            f'<span class="n">{i:02d}</span>'
            f'{_html.escape(eyebrow)}</a>'
        )
    return (
        '<div class="cdh-toolbar">'
        '<nav class="cdh-jump" aria-label="Jump to a module">'
        + "".join(jumps)
        + '</nav>'
        '<div class="cdh-filter">'
        '<input type="search" id="cdh-filter-input" autocomplete="off" '
        f'placeholder="Filter {n_surfaces} surfaces…" '
        'aria-label="Filter surfaces by name or description">'
        '<span class="cdh-filter-count" id="cdh-filter-count" '
        'aria-live="polite"></span>'
        '</div>'
        '</div>'
        '<div class="cdh-no-match" id="cdh-no-match" hidden>'
        'No surfaces match that filter. '
        '<button type="button" id="cdh-filter-clear">Clear the filter'
        '</button></div>'
    )


def _link_row(label: str, href: str, blurb: str) -> str:
    """One catalog row: honesty dot (accessible name, class-based color)
    + label + a mono tier tag for the decision-relevant rare tiers +
    arrow, with the one-line blurb underneath."""
    cls, tier_label, short = _TIER_INFO.get(_tier(href),
                                            _TIER_INFO["unknown"])
    tag = ""
    if cls in ("needs", "illustrative", "placeholder", "unknown"):
        tag = f'<span class="cdh-tag {cls}">{_html.escape(short)}</span>'
    return (
        f'<a class="cdh-link" href="{_html.escape(href, quote=True)}">'
        '<div class="cdh-row">'
        f'<span class="cdh-dot {cls}" role="img" '
        f'aria-label="{_html.escape(tier_label, quote=True)}" '
        f'title="{_html.escape(tier_label, quote=True)}"></span>'
        f'<span class="cdh-label">{_html.escape(label)}</span>'
        f'{tag}'
        '<span class="cdh-arrow" aria-hidden="true">&rarr;</span>'
        '</div>'
        f'<div class="cdh-blurb">{_html.escape(blurb)}</div>'
        '</a>'
    )


def _pillar_panel(index: int, title: str, eyebrow: str, blurb: str,
                  links) -> str:
    """One module as an anchored ``ck_panel``: category eyebrow → serif
    title → per-module coverage meta → blurb → honesty-dotted link rows."""
    from ._chartis_kit import ck_panel
    counts = Counter(_tier(href) for _l, href, _d in links)
    meta_parts = [f"{len(links)} SURFACES"]
    for key in _TIER_ORDER:
        if counts.get(key):
            meta_parts.append(f"{counts[key]} {_TIER_INFO[key][2]}")
    rows = "".join(_link_row(label, href, desc) for label, href, desc in links)
    inner = (
        '<header class="cdh-pillar-head">'
        f'<div class="ck-eyebrow">{_html.escape(eyebrow)}</div>'
        f'<h2 class="cdh-pillar-title">{_html.escape(title)}</h2>'
        f'<div class="cdh-pillar-meta">'
        f'{_html.escape(" · ".join(meta_parts))}</div>'
        f'<p class="cdh-pillar-body">{_html.escape(blurb)}</p>'
        '</header>'
        f'<div class="cdh-link-list">{rows}</div>'
    )
    return ck_panel(inner, anchor_id=f"cdd-{index:02d}")


def render_cdd_hub() -> str:
    """Render the /cdd section landing — the CDD workflow table of
    contents in the flagship grouped-catalog idiom: strict editorial
    masthead, provenance-wrapped coverage tiles, a jump-row + filter over
    the module panels, and an honesty dot on every row derived from the
    surface-status registry."""
    from ._chartis_kit import (
        chartis_shell,
        ck_next_section,
        ck_page_actions,
    )
    n_surfaces = sum(len(links) for _t, _b, links in _MODULES)
    n_pillars = len(_MODULES)
    tiers = _tier_counts(_MODULES)
    panels = "".join(
        _pillar_panel(i, title, eyebrow, blurb, links)
        for i, ((title, blurb, links), eyebrow)
        in enumerate(zip(_MODULES, _PILLAR_EYEBROWS), start=1)
    )
    next_up = ck_next_section(
        "Run the CDD exhibit engines",
        "/cdd/tools",
        eyebrow="Up next",
        italic_word="engines",
    )
    body = (
        _CSS
        + _head(n_surfaces, n_pillars, tiers)
        + _kpi_strip(n_surfaces, n_pillars, tiers)
        + _toolbar(n_surfaces)
        + f'<div class="cdh-catalog">{panels}</div>'
        + next_up
        + ck_page_actions()
        + _FILTER_JS
    )
    return chartis_shell(body, "Commercial Due Diligence Hub",
                         active_nav="/cdd")
