"""Diligence section landing page — the front door of the diligence area.

Route: ``GET /diligence`` (also served at ``/best/diligence``; the
top-nav DILIGENCE button points here). Was 404 before — the nav
pointed at a path with no handler, so partners hit a dead end.

Renders a flagship editorial catalog of every diligence surface,
grouped into the pillars a partner mentally walks:

  1. Profile & Health      — start-of-diligence reads
  2. Thesis & Playbook     — value-creation framework
  3. Market Sizing & CDD   — size the market, scope the engagement
  4. Audit & Stress        — pressure-test the assumptions
  5. Exit & Synthesis      — convert the diligence into IC output
  6. PE Intelligence Toolkit — codified partner judgment

Every count shown on the page (surfaces, pillars, per-tier coverage)
is derived from ``_PILLARS`` at render time — never hand-written — so
the copy can't drift from the catalog. Each row carries an honesty
dot derived per-route from ``rcm_mc.diligence.surface_status`` so a
partner is never misled about whether a surface runs on live data, a
computed model, or illustrative seed figures.

Contract pins (see tests/test_section_catalog*.py): one ``<h1>`` per
page, a ``class="sc-head"`` masthead with the ``eyebrow``/``dash``
glyph, ``sc-dot`` row dots, the word "Illustrative" in the legend,
the ``#c9a227`` illustrative hex, and every served ``/diligence/*``
route present in ``_PILLARS``.
"""
from __future__ import annotations

import html as _html
from collections import Counter
from collections.abc import Mapping

_PILLARS: list[Mapping[str, object]] = [
    {
        "title": "Profile & Health",
        "slug": "profile-health",
        "eyebrow": "START OF DILIGENCE",
        "body": (
            "First-pass reads on a target — financials, claims, "
            "physician footprint, payer mix. Open these to build "
            "the baseline picture before forming a thesis."
        ),
        "links": [
            {"href": "/diligence/deal",
             "label": "Deal Profile",
             "blurb": "Unified per-deal source of truth."},
            {"href": "/diligence/hcris-xray",
             "label": "HCRIS X-Ray",
             "blurb": "Full filing-level cost-report drill-down."},
            {"href": "/diligence/benchmarks",
             "label": "Benchmarks",
             "blurb": "Target vs vintage / sector / size cohort."},
            {"href": "/diligence/physician-attrition",
             "label": "Physician Attrition",
             "blurb": "MD-Compass turnover risk by specialty."},
            {"href": "/diligence/physician-eu",
             "label": "Provider Economics",
             "blurb": "Encounter mix + per-physician profitability."},
            {"href": "/diligence/management",
             "label": "Management",
             "blurb": "Leadership tenure, comp, change history."},
            {"href": "/diligence/xray",
             "label": "CMS X-Ray",
             "blurb": "Provider-level CMS quality + utilization drill-down."},
            {"href": "/diligence/sponsor-detail",
             "label": "Sponsor Detail",
             "blurb": "Single-sponsor realized-MOIC + vintage drill-down."},
        ],
    },
    {
        "title": "Thesis & Playbook",
        "slug": "thesis-playbook",
        "eyebrow": "VALUE-CREATION FRAMEWORK",
        "body": (
            "Where the deal makes money. Each surface ladders the "
            "RCM levers (denial reduction, AR compression, payer "
            "negotiation, capacity) into bridge dollars — plus the "
            "checklist and ingestion workflow that keep the "
            "work moving."
        ),
        "links": [
            {"href": "/diligence/thesis-pipeline",
             "label": "Thesis Pipeline",
             "blurb": "One-button full diligence chain."},
            {"href": "/diligence/checklist",
             "label": "Checklist",
             "blurb": "Track open questions through to resolution."},
            {"href": "/diligence/ingest",
             "label": "Ingestion",
             "blurb": "Upload data-room files, parse to fixtures."},
            {"href": "/diligence/value",
             "label": "Value Creation",
             "blurb": "RCM-lever EBITDA bridge per initiative."},
            {"href": "/diligence/root-cause",
             "label": "Root Cause",
             "blurb": "Why the metric is off — denial reasons drilled."},
            {"href": "/diligence/denial-prediction",
             "label": "Denial Prediction",
             "blurb": "ML scores future denials by claim line."},
            {"href": "/diligence/snapshot",
             "label": "VDR Snapshot",
             "blurb": "Upload 835/837 → revenue-leakage findings + memo."},
        ],
    },
    {
        "title": "Market Sizing & CDD",
        "slug": "market-sizing-cdd",
        "eyebrow": "SIZE THE MARKET",
        "body": (
            "Commercial-diligence surfaces: driver-tree market "
            "sizing, infusion-market scans and rate atlases, plus "
            "the expert-call program and engagement scoping that "
            "shape the CDD workplan."
        ),
        "links": [
            {"href": "/diligence/tam-sam",
             "label": "TAM / SAM Builder",
             "blurb": "Driver-tree market sizing with formatted "
                      "Excel export."},
            {"href": "/diligence/texas-infusion",
             "label": "TX Infusion Market",
             "blurb": "Texas infusion CDD: sizing, segmentation, "
                      "metro attractiveness."},
            {"href": "/diligence/texas-infusion-continued",
             "label": "TX Infusion Rates & Access",
             "blurb": "CPT-level rates by site and city, drug mix, "
                      "network access."},
            {"href": "/diligence/infusion-markets",
             "label": "Infusion Market Scan",
             "blurb": "National scan ranking every state for a roll-up."},
            {"href": "/diligence/jcode-atlas",
             "label": "J-Code Atlas",
             "blurb": "Infusion J-codes by site of care, tied to "
                      "disease + demand."},
            {"href": "/diligence/expert-calls",
             "label": "Expert Calls",
             "blurb": "CDD call program: mix plan, per-lens guides, "
                      "coverage read."},
            {"href": "/diligence/cdd-scope",
             "label": "CDD Scope",
             "blurb": "Four engagement depths: screen, red-flag, "
                      "full-scope, bring-down."},
        ],
    },
    {
        "title": "Audit & Stress",
        "slug": "audit-stress",
        "eyebrow": "PRESSURE-TEST THE ASSUMPTIONS",
        "body": (
            "Before IC, hammer the model. Counterfactuals, "
            "covenant stress, payer concentration, bankruptcy "
            "exposure. Anything that reveals downside that the "
            "base case quietly assumed away."
        ),
        "links": [
            {"href": "/diligence/risk-workbench?demo=steward",
             "label": "Risk Workbench",
             "blurb": "Multi-axis sensitivity scenarios (opens the "
                      "Steward demo)."},
            {"href": "/diligence/counterfactual",
             "label": "Counterfactual",
             "blurb": "What if the lever didn't work?"},
            {"href": "/diligence/compare",
             "label": "Compare",
             "blurb": "Two deals side-by-side on every metric."},
            {"href": "/screening/bankruptcy-survivor",
             "label": "Bankruptcy Scan",
             "blurb": "Distress signals across your watchlist."},
            {"href": "/diligence/payer-stress",
             "label": "Payer Stress",
             "blurb": "Top-payer concentration → revenue at risk."},
            {"href": "/diligence/covenant-stress",
             "label": "Covenant Stress",
             "blurb": "EBITDA cushion before leverage covenant trips."},
            {"href": "/diligence/bridge-audit",
             "label": "Bridge Audit",
             "blurb": "Tie every bridge lever to a source row."},
            {"href": "/diligence/cim-crosscheck",
             "label": "CIM Cross-Check",
             "blurb": "Management's claims vs independent HCRIS estimates."},
            {"href": "/diligence/deal-mc",
             "label": "Deal Monte Carlo",
             "blurb": "Per-deal Monte Carlo with overlay shocks."},
            {"href": "/diligence/bear-case",
             "label": "Bear Case",
             "blurb": "The defensible bear case on any target."},
        ],
    },
    {
        "title": "Exit & Synthesis",
        "slug": "exit-synthesis",
        "eyebrow": "CONVERT TO IC OUTPUT",
        "body": (
            "Diligence ends when it lands on a partner's desk. "
            "QoE memo, IC packet, exit-timing read, regulatory "
            "calendar — plus the retrospectives that test how "
            "underwriting held up."
        ),
        "links": [
            {"href": "/diligence/qoe-memo",
             "label": "QoE Memo",
             "blurb": "Quality-of-earnings narrative + drivers."},
            {"href": "/diligence/ic-packet",
             "label": "IC Packet",
             "blurb": "Partner-ready memo + exhibits in one click."},
            {"href": "/diligence/exit-timing",
             "label": "Exit Timing",
             "blurb": "Hold-period optimal exit window."},
            {"href": "/diligence/regulatory-calendar",
             "label": "Regulatory Calendar",
             "blurb": "CMS rule cycles overlaid on the hold."},
            {"href": "/diligence/cliff-calendar",
             "label": "Cliff Calendar",
             "blurb": "2026-29 Medicare/340B rate events on the hold window."},
            {"href": "/diligence/deal-autopsy",
             "label": "Deal Autopsy",
             "blurb": "Decompose realized return vs underwriting."},
            {"href": "/diligence/comparable-outcomes",
             "label": "Comparable Outcomes",
             "blurb": "How similar deals actually played out."},
            {"href": "/engagements",
             "label": "Engagements",
             "blurb": "Track active diligence engagements."},
        ],
    },
    {
        "title": "PE Intelligence Toolkit",
        "slug": "pe-toolkit",
        "eyebrow": "CODIFIED PARTNER JUDGMENT",
        "body": (
            "The codified partner-judgment layer — a searchable "
            "toolkit of analytic modules, runnable against a real "
            "deal, plus the curated reference libraries and the "
            "open-question ledger."
        ),
        "links": [
            {"href": "/diligence/pe-library",
             "label": "PE Intelligence Library",
             "blurb": "Hundreds of analytic modules, searchable by task."},
            {"href": "/diligence/pe-tool",
             "label": "Run a Tool on a Deal",
             "blurb": "Run an analytic module against a real deal's packet."},
            {"href": "/diligence/pe-reference",
             "label": "Reference Libraries",
             "blurb": "Historical failures, partner traps, archetypes, more."},
            {"href": "/diligence/advanced-analytics",
             "label": "Advanced Analytics",
             "blurb": "Native analytics marts on an illustrative "
                      "worked example."},
            {"href": "/diligence/questions",
             "label": "Questions Ledger",
             "blurb": "Open diligence questions across the portfolio."},
        ],
    },
]


# Honesty tiers — surface_status tier key → (css class, partner label,
# short mono label for per-pillar coverage strips). The css classes map
# onto the kit's canonical 4-bucket legend tokens (see ck_editorial_head
# in _chartis_kit.py) so /diligence paints the SAME tier the same color
# as the 48 pages using the kit legend. The illustrative fallback hex
# #c9a227 is pinned by tests/test_section_catalog.py.
_TIER_INFO: dict[str, tuple[str, str, str]] = {
    "green": ("live", "Live data", "LIVE"),
    "navy": ("computed", "Computed", "COMPUTED"),
    "data_required": ("needs", "Needs data", "NEEDS DATA"),
    "yellow": ("illustrative", "Illustrative", "ILLUSTRATIVE"),
    "red": ("placeholder", "Placeholder", "PLACEHOLDER"),
    "unknown": ("unknown", "Status unavailable", "UNVERIFIED"),
}
_TIER_ORDER = ("green", "navy", "data_required", "yellow", "red", "unknown")
# The four canonical buckets always shown in the legend (matches the
# kit's ck_editorial_head legend); rare tiers appear only when present.
_LEGEND_TIERS = ("green", "navy", "data_required", "yellow")


def _tier(href: str) -> str:
    """Honesty tier for a route, from the surface-status registry.

    Unlike the shared catalog renderer, a classification FAILURE maps
    to an explicit ``unknown`` bucket (neutral gray dot, "Status
    unavailable") rather than defaulting into the confident Computed
    tier — the honesty feature must not lie under failure.
    """
    try:
        from ..diligence.surface_status import classify_surface
        return classify_surface(href.split("?")[0]).get("tier", "unknown")
    except Exception:
        return "unknown"


def _tier_counts(pillars: list[Mapping[str, object]]) -> Counter:
    return Counter(
        _tier(link["href"])  # type: ignore[index]
        for p in pillars for link in p["links"]  # type: ignore[index]
    )


# ── Page CSS (kit vars with canonical fallbacks only — no new hexes) ──

_CSS = (
    '<style>'
    # -- masthead (strict Tier-1 5-block head; .sc-head anatomy pinned
    #    by tests/test_section_catalog_editorial_head.py) --
    '.sc-head{padding:0 0 30px;margin:0 0 26px;'
    'border-bottom:1px solid var(--rule-soft,#ddd1ac);}'
    '.sc-head .eyebrow{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.18em;text-transform:uppercase;'
    'color:var(--green-deep,#154e36);display:flex;align-items:center;'
    'gap:12px;margin:0 0 18px;}'
    '.sc-head .eyebrow .dash{width:24px;height:1px;'
    'background:var(--green-deep,#154e36);}'
    '.sc-head h1{font:400 44px/1.05 var(--sc-serif,Georgia),serif;'
    'letter-spacing:-.015em;color:var(--ink,#16263a);margin:0 0 14px;}'
    '.sc-head .meta{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.14em;text-transform:uppercase;'
    'color:var(--muted,#7a8595);margin:0 0 18px;}'
    # Whole-lede italic with the green-deep <em> phrase — same idiom as
    # ck_editorial_head and the sibling section landings; the second
    # (explainer) paragraph drops to roman via .roman, mirroring the
    # shared head's explainer treatment.
    '.sc-head .lede{font:400 italic 16.5px/1.6 var(--sc-serif,Georgia),serif;'
    'color:var(--ink-2,#2b3e54);max-width:68ch;margin:0 0 14px;}'
    '.sc-head .lede em{color:var(--green-deep,#154e36);font-style:italic;}'
    '.sc-head .lede.roman{font-style:normal;}'
    '.sc-head .source-note{font:500 10px/1.4 var(--sc-mono,monospace);'
    'letter-spacing:.14em;text-transform:uppercase;'
    'color:var(--muted-2,#9a9e8a);margin:0 0 18px;max-width:72ch;}'
    # -- merged legend-with-counts (replaces the countless 10.5px twin) --
    '.dlx-legend{display:flex;gap:22px;list-style:none;padding:0;margin:0;'
    'font:400 12.5px/1 var(--sc-sans,Inter),sans-serif;'
    'color:var(--ink-2,#2b3e54);flex-wrap:wrap;}'
    '.dlx-legend li{display:flex;align-items:center;gap:8px;}'
    '.dlx-legend .dlx-legend-n{font:500 12px/1 var(--sc-mono,monospace);'
    'color:var(--muted,#7a8595);}'
    # -- honesty dots: class-based, kit legend tokens (no inline styles).
    #    .illustrative keeps the pinned #c9a227 byte as the fallback.
    '.sc-dot{width:8px;height:8px;border-radius:50%;flex:none;'
    'display:inline-block;position:relative;top:1px;}'
    '.sc-dot.live{background:var(--green-deep,#154e36);}'
    '.sc-dot.computed{background:var(--ink-deep,#0e1a29);}'
    '.sc-dot.needs{background:var(--coral,#b04a3a);}'
    '.sc-dot.illustrative{background:var(--gold-bright,#c9a227);}'
    '.sc-dot.placeholder{background:var(--sc-negative,#b5321e);}'
    '.sc-dot.unknown{background:var(--sc-text-faint,#8b94a0);}'
    # -- KPI strip --
    '.dlx-kpis{grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;'
    'margin:0 0 24px;}'
    '@media (max-width:960px){.dlx-kpis{grid-template-columns:'
    'repeat(2,minmax(0,1fr));}}'
    '@media (max-width:560px){.dlx-kpis{grid-template-columns:1fr;}}'
    # -- toolbar: mono jump-row + type-to-filter --
    '.dlx-toolbar{display:flex;align-items:center;'
    'justify-content:space-between;gap:14px 24px;flex-wrap:wrap;'
    'margin:0 0 22px;}'
    '.dlx-jump{display:flex;flex-wrap:wrap;gap:6px 18px;}'
    '.dlx-jump a{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.12em;text-transform:uppercase;'
    'color:var(--ink-2,#2b3e54);text-decoration:none;display:inline-flex;'
    'align-items:center;gap:7px;padding:6px 0;'
    'border-bottom:1px solid transparent;}'
    '.dlx-jump a .n{color:var(--green-deep,#154e36);}'
    '.dlx-jump a:hover{border-bottom-color:var(--green-deep,#154e36);'
    'color:var(--ink,#16263a);}'
    '.dlx-jump a:focus-visible{outline:2px solid var(--green-deep,#154e36);'
    'outline-offset:2px;}'
    '.dlx-filter{display:flex;align-items:center;gap:10px;}'
    '.dlx-filter input{font:400 13px/1.2 var(--sc-sans,Inter),sans-serif;'
    'color:var(--ink,#16263a);background:var(--paper-card,#fefcf3);'
    'border:1px solid var(--rule,#c9bf9c);border-radius:2px;'
    'padding:8px 12px;min-width:230px;}'
    '.dlx-filter input:focus-visible{outline:2px solid '
    'var(--green-deep,#154e36);outline-offset:-1px;}'
    '.dlx-filter-count{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.08em;text-transform:uppercase;'
    'color:var(--muted,#7a8595);}'
    '.dlx-no-match{font:400 italic 14px/1.5 var(--sc-serif,Georgia),serif;'
    'color:var(--sc-text-dim,#465366);padding:18px 0;}'
    '.dlx-no-match button{font:500 11px/1 var(--sc-mono,monospace);'
    'letter-spacing:.08em;text-transform:uppercase;cursor:pointer;'
    'color:var(--green-deep,#154e36);background:none;border:none;'
    'border-bottom:1px solid var(--green-deep,#154e36);padding:0 0 2px;}'
    '.dlx-no-match button:focus-visible{outline:2px solid '
    'var(--green-deep,#154e36);outline-offset:2px;}'
    # -- pillar catalog: two self-balancing columns (CSS multicol) so a
    #    long pillar never stretches its neighbour into dead whitespace
    #    and an odd pillar count never orphans a grid cell --
    '.dlx-catalog{columns:2;column-gap:24px;margin:0 0 24px;}'
    '@media (max-width:1100px){.dlx-catalog{columns:1;}}'
    '.dlx-catalog .ck-panel{break-inside:avoid;'
    '-webkit-column-break-inside:avoid;page-break-inside:avoid;'
    'margin:0 0 24px;scroll-margin-top:86px;}'
    '.dlx-pillar-head{display:flex;flex-direction:column;gap:8px;'
    'border-bottom:1px solid var(--sc-rule,#d6cfc0);padding-bottom:16px;}'
    '.dlx-pillar-title{font-family:var(--sc-serif,Georgia,serif);'
    'font-weight:500;font-size:22px;color:var(--sc-navy,#0b2341);'
    'margin:2px 0 0;letter-spacing:-0.01em;}'
    '.dlx-pillar-meta{font:500 10.5px/1.5 var(--sc-mono,monospace);'
    'letter-spacing:.12em;text-transform:uppercase;'
    'color:var(--muted,#7a8595);}'
    '.dlx-pillar-body{font-family:var(--sc-serif,Georgia,serif);'
    'font-size:13.5px;line-height:1.6;color:var(--sc-text-dim,#465366);'
    'margin:0;max-width:48ch;}'
    # -- link rows: non-reflowing hover (background + arrow nudge, no
    #    padding shift) with a keyboard-parallel focus-visible state --
    '.dlx-link-list{display:flex;flex-direction:column;}'
    '.dlx-link{display:block;text-decoration:none;color:inherit;'
    'padding:12px;margin:0 -12px;border-radius:2px;'
    'border-bottom:1px solid var(--sc-rule,#d6cfc0);'
    'transition:background .12s;}'
    '.dlx-link:last-child{border-bottom:0;}'
    '.dlx-link:hover{background:var(--sc-bone,#ece5d6);}'
    '.dlx-link:focus-visible{background:var(--sc-bone,#ece5d6);'
    'outline:2px solid var(--green-deep,#154e36);outline-offset:-2px;}'
    '.dlx-link:hover .dlx-arrow,.dlx-link:focus-visible .dlx-arrow{'
    'color:var(--sc-teal,#155752);transform:translateX(2px);}'
    '.dlx-row{display:flex;align-items:baseline;gap:9px;}'
    '.dlx-label{font-family:var(--sc-sans,Inter,sans-serif);'
    'font-weight:600;font-size:14px;color:var(--sc-navy,#0b2341);}'
    '.dlx-tag{font:500 9.5px/1 var(--sc-mono,monospace);'
    'letter-spacing:.1em;text-transform:uppercase;padding:3px 6px;'
    'border-radius:2px;flex:none;position:relative;top:-1px;}'
    '.dlx-tag.needs{color:var(--coral,#b04a3a);'
    'border:1px solid var(--coral,#b04a3a);}'
    '.dlx-tag.illustrative{color:var(--gold,#a08227);'
    'border:1px solid var(--gold-bright,#c9a227);}'
    '.dlx-tag.placeholder{color:var(--sc-negative,#b5321e);'
    'border:1px solid var(--sc-negative,#b5321e);}'
    '.dlx-tag.unknown{color:var(--sc-text-faint,#8b94a0);'
    'border:1px solid var(--sc-text-faint,#8b94a0);}'
    '.dlx-arrow{margin-left:auto;'
    'font-family:var(--sc-sans,Inter,sans-serif);font-size:14px;'
    'color:var(--sc-text-faint,#7a8699);'
    'transition:color .12s,transform .12s;}'
    '.dlx-blurb{font-family:var(--sc-serif,Georgia,serif);'
    'font-size:12.5px;color:var(--sc-text-dim,#465366);line-height:1.45;'
    'margin-top:4px;padding-left:17px;}'
    '.dlx-hidden{display:none !important;}'
    '@media (max-width:960px){.sc-head h1{font-size:36px;}}'
    '@media (prefers-reduced-motion:reduce){'
    '.dlx-link,.dlx-arrow{transition:none;}'
    '.dlx-link:hover .dlx-arrow,'
    '.dlx-link:focus-visible .dlx-arrow{transform:none;}}'
    '</style>'
)

# Type-to-filter over the catalog rows. Vanilla, self-contained,
# idempotent install guard; hides pillars whose rows all filtered out.
_FILTER_JS = (
    '<script>(function(){"use strict";'
    'var input=document.getElementById("dlx-filter-input");'
    'if(!input||window.__dlxFilterInstalled){return;}'
    'window.__dlxFilterInstalled=true;'
    'var links=Array.prototype.slice.call('
    'document.querySelectorAll(".dlx-catalog .dlx-link"));'
    'var panels=Array.prototype.slice.call('
    'document.querySelectorAll(".dlx-catalog .ck-panel"));'
    'var count=document.getElementById("dlx-filter-count");'
    'var noMatch=document.getElementById("dlx-no-match");'
    'var clearBtn=document.getElementById("dlx-filter-clear");'
    'var total=links.length;'
    'function apply(){'
    'var q=input.value.trim().toLowerCase();'
    'var shown=0;'
    'links.forEach(function(a){'
    'var hit=!q||a.textContent.toLowerCase().indexOf(q)!==-1;'
    'a.classList.toggle("dlx-hidden",!hit);'
    'if(hit){shown+=1;}});'
    'panels.forEach(function(p){'
    'var any=p.querySelector(".dlx-link:not(.dlx-hidden)");'
    'p.classList.toggle("dlx-hidden",!any);});'
    'if(count){count.textContent=q?shown+" of "+total+" shown":"";}'
    'if(noMatch){noMatch.hidden=!(q&&shown===0);}}'
    'input.addEventListener("input",apply);'
    'if(clearBtn){clearBtn.addEventListener("click",function(){'
    'input.value="";apply();input.focus();});}'
    '})();</script>'
)


def _legend(tiers: Counter) -> str:
    """Single legend row with real counts — replaces the old twin rows
    (mono coverage text + countless dot legend) that carried the same
    information at half strength."""
    keys = list(_LEGEND_TIERS) + [
        k for k in _TIER_ORDER
        if k not in _LEGEND_TIERS and tiers.get(k)
    ]
    from ._chartis_kit import ck_fmt_number
    items = []
    for key in keys:
        cls, label, _short = _TIER_INFO[key]
        items.append(
            f'<li><span class="sc-dot {cls}" aria-hidden="true"></span>'
            f'{_html.escape(label)}'
            f'<span class="dlx-legend-n">· '
            f'{ck_fmt_number(tiers.get(key, 0))}</span></li>'
        )
    return '<ul class="dlx-legend">' + "".join(items) + '</ul>'


def _head(n_surfaces: int, n_pillars: int, tiers: Counter) -> str:
    """Strict Tier-1 5-block masthead (anatomy pinned by tests):
    eyebrow+dash → serif h1 → mono meta → italic-first-phrase lede →
    explainer → source note → legend-with-counts."""
    return (
        '<header class="sc-head">'
        '<div class="eyebrow"><span class="dash"></span>RCM PLAYBOOK</div>'
        '<h1>Diligence</h1>'
        f'<div class="meta">{n_surfaces} SURFACES · {n_pillars} PILLARS'
        '</div>'
        '<p class="lede"><em>Where the diligence work lives.</em> '
        'The pillars below trace the walk a partner makes — profile '
        'the target, frame the thesis, size the market, stress the '
        'assumptions, then synthesize for IC — with the codified '
        'partner-judgment toolkit alongside.</p>'
        '<p class="lede roman">Each row names a surface and the one-line job '
        'it does. The status dot is derived from the surface-status '
        'registry on every render — green for live data, ink for a '
        'model computed off your inputs, coral where your data upload '
        'is still needed, gold for illustrative seed figures — so this '
        'catalog can never overstate what is real.</p>'
        '<p class="source-note">Source: curated catalog of /diligence/* '
        'routes · honesty tiers derived per-route from '
        'rcm_mc.diligence.surface_status</p>'
        f'{_legend(tiers)}'
        '</header>'
    )


def _kpi_strip(n_surfaces: int, n_pillars: int, tiers: Counter) -> str:
    """Coverage stat tiles under the head — every value computed from
    ``_PILLARS`` + the surface-status registry, each wrapped in a
    provenance tooltip so a partner can ask "where does this number
    come from?" without leaving the page."""
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
        "Diligence surfaces",
        f'<span class="mn">{ck_fmt_number(n_surfaces)}</span>',
        explainer=(
            "Counted from the curated pillar catalog on every render — "
            "the same list the panels below draw from, so the number "
            "can never drift from what is actually linked."
        ),
    )
    live_share_value = ck_provenance_tooltip(
        "Live-data share",
        f'<span class="mn">{ck_fmt_percent(live / n_surfaces if n_surfaces else None)}</span>',
        explainer=(
            f"{ck_fmt_number(live)} of {ck_fmt_number(n_surfaces)} "
            "surfaces run on live data (CMS/HCRIS public sources or "
            "your own deal and portfolio records). Derived per-route "
            "from rcm_mc.diligence.surface_status; recomputed on every "
            "render."
        ),
        inject_css=False,
    )
    computed_value = ck_provenance_tooltip(
        "Computed models",
        f'<span class="mn">{ck_fmt_number(computed)}</span>',
        explainer=(
            "Legitimate diligence calculators: illustrative defaults, "
            "but the output reflects the inputs you give them. Honest "
            "as tools; classified per-route by surface_status."
        ),
        inject_css=False,
    )
    not_live_value = ck_provenance_tooltip(
        "Not yet live",
        f'<span class="mn">{ck_fmt_number(not_live)}</span>',
        explainer=(
            f"Surfaces not running on live data: {ck_fmt_number(computed)} "
            f"computed models, {ck_fmt_number(needs)} awaiting a data "
            f"upload, {ck_fmt_number(illus)} on illustrative seed "
            "figures. The per-row dots below say which is which."
        ),
        inject_css=False,
    )
    return (
        '<div class="ck-kpi-grid dlx-kpis">'
        + ck_kpi_block(
            "Surfaces", surfaces_value,
            f"across {ck_fmt_number(n_pillars)} pillars")
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
    """Mono jump-row (pillar ordinals → panel anchors) + type-to-filter."""
    jumps = []
    for i, p in enumerate(_PILLARS, start=1):
        jumps.append(
            f'<a href="#{_html.escape(str(p["slug"]), quote=True)}">'
            f'<span class="n">{i:02d}</span>'
            f'{_html.escape(str(p["title"]))}</a>'
        )
    return (
        '<div class="dlx-toolbar">'
        '<nav class="dlx-jump" aria-label="Jump to a pillar">'
        + "".join(jumps)
        + '</nav>'
        '<div class="dlx-filter">'
        '<input type="search" id="dlx-filter-input" autocomplete="off" '
        f'placeholder="Filter {n_surfaces} surfaces…" '
        'aria-label="Filter surfaces by name or description">'
        '<span class="dlx-filter-count" id="dlx-filter-count" '
        'aria-live="polite"></span>'
        '</div>'
        '</div>'
        '<div class="dlx-no-match" id="dlx-no-match" hidden>'
        'No surfaces match that filter. '
        '<button type="button" id="dlx-filter-clear">Clear the filter'
        '</button></div>'
    )


def _link_row(link: Mapping[str, str]) -> str:
    """One catalog row: honesty dot (accessible name, class-based color)
    + label + optional mono tier tag for the decision-relevant rare
    tiers + arrow, with the one-line blurb underneath."""
    cls, label, short = _TIER_INFO.get(_tier(link["href"]),
                                       _TIER_INFO["unknown"])
    tag = ""
    if cls in ("needs", "illustrative", "placeholder", "unknown"):
        tag = f'<span class="dlx-tag {cls}">{_html.escape(short)}</span>'
    return (
        f'<a class="dlx-link" href="{_html.escape(link["href"], quote=True)}">'
        '<div class="dlx-row">'
        f'<span class="sc-dot {cls}" role="img" '
        f'aria-label="{_html.escape(label, quote=True)}" '
        f'title="{_html.escape(label, quote=True)}"></span>'
        f'<span class="dlx-label">{_html.escape(link["label"])}</span>'
        f'{tag}'
        '<span class="dlx-arrow" aria-hidden="true">&rarr;</span>'
        '</div>'
        f'<div class="dlx-blurb">{_html.escape(link["blurb"])}</div>'
        '</a>'
    )


def _pillar_panel(index: int, pillar: Mapping[str, object]) -> str:
    """One pillar as an anchored ck_panel: ordinal eyebrow → serif
    title → per-pillar coverage meta → body → link rows."""
    from ._chartis_kit import ck_panel
    links: list[Mapping[str, str]] = pillar["links"]  # type: ignore[assignment]
    counts = Counter(_tier(link["href"]) for link in links)
    meta_parts = [f"{len(links)} SURFACES"]
    for key in _TIER_ORDER:
        if counts.get(key):
            meta_parts.append(f"{counts[key]} {_TIER_INFO[key][2]}")
    rows = "".join(_link_row(link) for link in links)
    inner = (
        '<header class="dlx-pillar-head">'
        f'<div class="ck-eyebrow">{index:02d} · '
        f'{_html.escape(str(pillar["eyebrow"]))}</div>'
        f'<h2 class="dlx-pillar-title">'
        f'{_html.escape(str(pillar["title"]))}</h2>'
        f'<div class="dlx-pillar-meta">'
        f'{_html.escape(" · ".join(meta_parts))}</div>'
        f'<p class="dlx-pillar-body">{_html.escape(str(pillar["body"]))}</p>'
        '</header>'
        f'<div class="dlx-link-list">{rows}</div>'
    )
    return ck_panel(inner, anchor_id=str(pillar["slug"]))


def render_diligence_index() -> str:
    """Render the /diligence section landing — the flagship grouped
    catalog: strict editorial masthead, provenance-wrapped coverage
    tiles, jump-row + filter over the pillar panels, and an honesty
    dot on every row derived from the surface-status registry."""
    from ._chartis_kit import (
        chartis_shell,
        ck_next_section,
        ck_page_actions,
    )
    n_surfaces = sum(len(p["links"]) for p in _PILLARS)  # type: ignore[arg-type]
    n_pillars = len(_PILLARS)
    tiers = _tier_counts(_PILLARS)
    panels = "".join(
        _pillar_panel(i, p) for i, p in enumerate(_PILLARS, start=1)
    )
    next_up = ck_next_section(
        "Open the portfolio-wide question ledger",
        "/diligence/questions",
        eyebrow="Up next",
        italic_word="question",
    )
    body = (
        _CSS
        + _head(n_surfaces, n_pillars, tiers)
        + _kpi_strip(n_surfaces, n_pillars, tiers)
        + _toolbar(n_surfaces)
        + f'<div class="dlx-catalog">{panels}</div>'
        + next_up
        + ck_page_actions()
        + _FILTER_JS
    )
    return chartis_shell(
        body, "Diligence",
        active_nav="/diligence",
    )
