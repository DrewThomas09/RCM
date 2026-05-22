"""Module Index — /module-index.

Editorial module directory, ported from the Claude Design
module-directory handoff (``DirectoryPage.jsx``). Applies the
handoff's visual system — oversize letterform group headers,
featured cards with inline mini-visualizations, compact rows,
and an instant client-side filter+search — to the codebase's
*real* module catalog (``data_public/module_index.py``).

Design decision: rather than force the codebase's 8 real
categories into the handoff's 5 group codes (which would
fabricate a taxonomy), the handoff's *style* is applied to the
real categories. Every module, route, and category here is real
— no dead links, no invented modules.

The mini-visualizations on featured cards are decorative
editorial flourish (illustrative fixed data), matching the
handoff's own ``FEATURED_VIZ`` intent — this is a navigation
surface, not a live-data view.

Stays inside ``chartis_shell`` (signed-in app chrome). The
filter/search is a small scoped vanilla-JS shim — modules carry
``data-cat`` / ``data-q`` attributes and the shim toggles
visibility; no server round-trip, no new route.
"""
from __future__ import annotations

import html as _html
from typing import List, Sequence

from rcm_mc.ui._chartis_kit import P, chartis_shell
from rcm_mc.ui.chartis._helpers import render_page_explainer


# ── Category metadata — blurb + accent tint per real category ────────
# Ordered roughly along the deal lifecycle. Tints are drawn from the
# editorial palette family; each category's letterform + section
# label + featured-card top-rule use its tint.
_CATEGORY_META = {
    "Sourcing": (
        "var(--sc-teal-ink)",
        "Active pipeline, sponsor heatmaps, base-rate percentiles, "
        "and MSA concentration — where deals come from.",
    ),
    "Data": (
        "#2a5d8f",
        "CMS datasets and source catalogs — the raw public feeds "
        "behind every benchmark on the platform.",
    ),
    "Diligence": (
        "var(--sc-navy)",
        "Red-flag screening, anti-trust thresholds, payer "
        "concentration, cyber maturity, FWA detection.",
    ),
    "Sector": (
        "#6d4b97",
        "Sector-specific analyzers — physician comp, MA contracts, "
        "340B, ACO economics, HCIT, telehealth, trial sites.",
    ),
    "Value Creation": (
        "#b36a2e",
        "Roll-up economics, PMI playbooks, de novo expansion, CIN, "
        "and zero-based budgeting — the hold-period levers.",
    ),
    "Capital": (
        "var(--sc-positive)",
        "Capital-call pacing, covenant headroom, direct lending, "
        "REIT / sale-leaseback, exit-readiness scoring.",
    ),
    "IC": (
        "var(--sc-navy)",
        "Investment-committee memo generation — thesis, findings, "
        "levers, risks, scenarios, structure.",
    ),
    "Performance": (
        "var(--sc-teal-ink)",
        "Sponsor league tables and exit-timing analysis — track "
        "record across sectors and vintages.",
    ),
}
_CATEGORY_ORDER = list(_CATEGORY_META.keys())


# ── Mini-visualization primitives — ported from DirectoryPage.jsx ────
# Decorative editorial flourish for featured cards. Illustrative
# fixed data (same intent as the handoff's FEATURED_VIZ block).

def _dir_sparkline(values: Sequence[float], color: str = "var(--sc-teal)") -> str:
    vmax, vmin = max(values), min(values)
    rng = (vmax - vmin) or 1.0
    pts = " ".join(
        f"{(i / (len(values) - 1)) * 100:.1f},"
        f"{100 - ((v - vmin) / rng) * 100:.1f}"
        for i, v in enumerate(values)
    )
    return (
        '<svg viewBox="0 0 100 100" preserveAspectRatio="none" '
        'style="width:100%;height:34px;display:block;">'
        f'<polyline points="{pts}" fill="none" stroke="{color}" '
        'stroke-width="2" vector-effect="non-scaling-stroke"/>'
        f'<polyline points="0,100 {pts} 100,100" fill="{color}" '
        'fill-opacity="0.12" stroke="none"/>'
        '</svg>'
    )


def _dir_distribution(bins: Sequence[float], color: str = "var(--sc-teal)") -> str:
    bmax = max(bins) or 1.0
    bars = "".join(
        f'<div style="flex:1;height:{(v / bmax) * 100:.0f}%;'
        f'background:{color};opacity:{0.35 + (v / bmax) * 0.65:.2f};"></div>'
        for v in bins
    )
    return (
        '<div style="display:flex;align-items:flex-end;gap:2px;height:34px;">'
        f'{bars}</div>'
    )


def _dir_bridge_bars(steps: Sequence[float]) -> str:
    smax = max((abs(s) for s in steps), default=1.0) or 1.0
    cells = ""
    for s in steps:
        h = (abs(s) / smax) * 100
        is_up = s >= 0
        col = "var(--sc-positive)" if is_up else "var(--sc-negative)"
        align = "flex-start" if is_up else "flex-end"
        cells += (
            '<div style="flex:1;display:flex;align-items:center;height:100%;">'
            f'<div style="width:100%;height:{h:.0f}%;background:{col};'
            f'opacity:0.85;align-self:{align};"></div></div>'
        )
    return (
        '<div style="display:flex;align-items:center;gap:3px;height:34px;">'
        f'{cells}</div>'
    )


def _dir_heatmap_pips(values: Sequence[float], cols: int = 8) -> str:
    def _c(v: float) -> str:
        if v >= 0.7:
            return "#2d8f5a"
        if v >= 0.55:
            return "#5aa37a"
        if v >= 0.4:
            return "#d4a13b"
        if v >= 0.25:
            return "#c5603a"
        return "#a13b2a"
    cells = "".join(
        f'<div style="background:{_c(v)};"></div>' for v in values[:cols * 4]
    )
    return (
        f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);'
        f'gap:2px;height:34px;">{cells}</div>'
    )


def _dir_donut(pct: float, color: str = "var(--sc-teal)") -> str:
    r = 16
    c = 2 * 3.14159265 * r
    dash = (pct / 100.0) * c
    return (
        '<svg width="34" height="34" viewBox="0 0 40 40" '
        'style="display:block;">'
        f'<circle cx="20" cy="20" r="{r}" fill="none" '
        'stroke="var(--sc-rule)" stroke-width="4"/>'
        f'<circle cx="20" cy="20" r="{r}" fill="none" stroke="{color}" '
        f'stroke-width="4" stroke-dasharray="{dash:.1f} {c:.1f}" '
        'transform="rotate(-90 20 20)"/>'
        '</svg>'
    )


# Deterministic illustrative viz + pinned stats, rotated by the
# featured card's index within its category so the directory looks
# alive without claiming live data.
_VIZ_ROTATION = [
    lambda t: (
        _dir_sparkline([52, 48, 55, 61, 58, 66, 72, 68, 74, 81], t),
        [("Trend", "+12%"), ("Coverage", "19/24"), ("Updated", "2d")],
    ),
    lambda t: (
        _dir_distribution([1, 2, 4, 7, 10, 12, 10, 7, 4, 2, 1], t),
        [("Corpus n", "5,808"), ("Median", "P50"), ("Spread", "IQR")],
    ),
    lambda t: (
        _dir_bridge_bars([1, 0.6, -0.3, 0.8, 0.4, -0.2]),
        [("Entry", "$14.2M"), ("Y-5 P50", "$26.8M"), ("CAGR", "13.6%")],
    ),
    lambda t: (
        _dir_heatmap_pips([
            0.82, 0.78, 0.72, 0.68, 0.61, 0.55, 0.48, 0.42,
            0.76, 0.71, 0.66, 0.59, 0.52, 0.45, 0.38, 0.31,
            0.69, 0.63, 0.58, 0.51, 0.44, 0.36, 0.29, 0.24,
            0.58, 0.52, 0.46, 0.39, 0.33, 0.27, 0.22, 0.18,
        ]),
        [("Green", "14"), ("Watch", "7"), ("At risk", "3")],
    ),
    lambda t: (
        _dir_donut(72, t),
        [("Complete", "72%"), ("Sources", "32"), ("Ready", "4")],
    ),
]


# ── Scoped CSS + filter/search JS shim ───────────────────────────────
# Everything is prefixed `.dir-` so it cannot leak into the rest of
# the editorial shell (same scoping discipline as the bankruptcy
# CSS-leak fix).

_STYLE = """
<style>
.dir-controls { display:flex; gap:12px; align-items:center; flex-wrap:wrap;
  border-top:1px solid var(--sc-rule); border-bottom:1px solid var(--sc-rule);
  padding:14px 0; margin-bottom:8px; }
.dir-chips { display:flex; gap:6px; flex-wrap:wrap; }
.dir-chip { background:#fff; color:var(--sc-text); border:1px solid var(--sc-rule);
  padding:6px 12px; font-family:var(--sc-mono); font-size:10.5px;
  letter-spacing:0.1em; text-transform:uppercase; font-weight:600;
  cursor:pointer; }
.dir-chip.active { background:var(--sc-navy); color:#fff; border-color:var(--sc-navy); }
.dir-search { flex:1 1 220px; min-width:220px; margin-left:auto;
  padding:9px 12px; border:1px solid var(--sc-rule); background:#fff;
  font-family:var(--sc-mono); font-size:12px; color:var(--sc-text);
  outline:none; }
.dir-group { margin-top:44px; padding-top:16px; }
.dir-group-head { display:grid; grid-template-columns:auto minmax(0,1fr) auto;
  gap:20px; align-items:center; border-bottom:1px solid var(--sc-rule);
  padding:0 0 16px; }
.dir-letterform { font-family:var(--sc-serif); font-size:60px; line-height:0.9;
  letter-spacing:-0.02em; font-weight:400; font-style:italic; padding-right:6px; }
.dir-group-label { font-family:var(--sc-mono); font-size:10px;
  letter-spacing:0.18em; text-transform:uppercase; font-weight:700;
  margin-bottom:4px; }
.dir-group-name { font-family:var(--sc-serif); font-size:26px; line-height:1.1;
  font-weight:500; color:var(--sc-navy); margin:0; }
.dir-group-blurb { margin:6px 0 0; font-family:var(--sc-sans); font-size:13.5px;
  color:var(--sc-text-dim); max-width:640px; line-height:1.5; }
.dir-group-count { font-family:var(--sc-mono); font-size:11px;
  letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint);
  white-space:nowrap; }
.dir-body { display:grid; gap:28px; margin-top:18px; }
.dir-body.has-featured { grid-template-columns:minmax(0,1.15fr) minmax(0,1fr); }
.dir-featured { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.dir-card { display:flex; flex-direction:column; text-align:left; background:#fff;
  border:1px solid var(--sc-rule); padding:16px 16px 14px;
  text-decoration:none; min-height:212px;
  transition:box-shadow 120ms ease, transform 120ms ease; }
.dir-card:hover { box-shadow:0 10px 30px -18px rgba(11,35,65,0.35);
  transform:translateY(-1px); }
.dir-card-kicker { font-family:var(--sc-mono); font-size:9.5px;
  letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint);
  margin-bottom:6px; }
.dir-card-title { font-family:var(--sc-serif); font-size:19px; font-weight:500;
  color:var(--sc-navy); line-height:1.2; margin-bottom:4px; }
.dir-card-route { font-family:var(--sc-mono); font-size:10.5px;
  margin-bottom:10px; letter-spacing:0.04em; }
.dir-src { display:inline-block; margin-left:7px; padding:1px 6px;
  font-family:var(--sc-mono); font-size:8.5px; font-weight:700;
  letter-spacing:0.08em; text-transform:uppercase; border-radius:2px;
  vertical-align:middle; color:var(--src-c); border:1px solid var(--src-c);
  background:color-mix(in srgb, var(--src-c) 8%, transparent); }
.dir-trust-legend { display:flex; gap:14px; flex-wrap:wrap;
  font-family:var(--sc-sans); font-size:11px; color:var(--sc-text-dim);
  margin:2px 0 4px; align-items:center; }
.dir-trust-legend .dir-src { margin-left:0; }
.dir-card-viz { background:var(--sc-parchment); border:1px solid var(--sc-rule);
  padding:10px 12px; margin-bottom:10px; }
.dir-card-stats { display:grid; gap:8px; border-top:1px solid var(--sc-rule);
  padding-top:8px; margin-top:8px; }
.dir-card-stat-l { font-family:var(--sc-mono); font-size:8.5px;
  letter-spacing:0.12em; text-transform:uppercase; color:var(--sc-text-faint); }
.dir-card-stat-v { font-family:var(--sc-mono); font-size:13px; font-weight:600;
  color:var(--sc-navy); margin-top:2px; }
.dir-card-purpose { font-family:var(--sc-sans); font-size:12.5px;
  color:var(--sc-text-dim); line-height:1.5; margin-top:auto; }
.dir-rest-label { font-family:var(--sc-mono); font-size:10px;
  letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-faint);
  margin-bottom:8px; }
.dir-rows { border-top:1px solid var(--sc-rule); }
.dir-row { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:12px;
  align-items:baseline; width:100%; background:transparent;
  border-bottom:1px solid var(--sc-rule); padding:12px 0;
  text-decoration:none; transition:background 100ms ease, padding-left 100ms ease; }
.dir-row:hover { background:rgba(47,179,173,0.06); padding-left:8px; }
.dir-row-title { font-family:var(--sc-serif); font-size:15px; font-weight:500;
  color:var(--sc-navy); line-height:1.2; }
.dir-row-route { font-family:var(--sc-mono); font-size:10.5px;
  letter-spacing:0.04em; margin-top:3px; overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap; }
.dir-row-persona { font-family:var(--sc-mono); font-size:9.5px;
  letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint);
  white-space:nowrap; }
.dir-empty { padding:40px 0; text-align:center; font-family:var(--sc-mono);
  font-size:12px; color:var(--sc-text-faint); }
@media (max-width:1000px) {
  .dir-body.has-featured { grid-template-columns:1fr; }
  .dir-featured { grid-template-columns:1fr; }
}
</style>
"""

_SCRIPT = """
<script>
(function () {
  var chips = document.querySelectorAll('.dir-chip');
  var search = document.getElementById('dir-search');
  var groups = document.querySelectorAll('.dir-group');
  var empty = document.getElementById('dir-empty');
  var activeCat = '';
  function apply() {
    var q = (search && search.value || '').trim().toLowerCase();
    var anyVisible = false;
    groups.forEach(function (g) {
      var cat = g.getAttribute('data-cat');
      var catOk = !activeCat || cat === activeCat;
      var items = g.querySelectorAll('[data-q]');
      var groupHasVisible = false;
      items.forEach(function (it) {
        var hay = it.getAttribute('data-q') || '';
        var match = catOk && (!q || hay.indexOf(q) !== -1);
        it.style.display = match ? '' : 'none';
        if (match) { groupHasVisible = true; }
      });
      g.style.display = groupHasVisible ? '' : 'none';
      if (groupHasVisible) { anyVisible = true; }
    });
    if (empty) { empty.style.display = anyVisible ? 'none' : ''; }
  }
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      activeCat = c.getAttribute('data-cat') || '';
      chips.forEach(function (x) { x.classList.remove('active'); });
      c.classList.add('active');
      apply();
    });
  });
  if (search) { search.addEventListener('input', apply); }
})();
</script>
"""


# ── Section + card builders ──────────────────────────────────────────

# ── Data-trust source classification ─────────────────────────────────
#
# Per-route data-source tag from docs/PEDESK_UNDERSTANDING/08, so a
# partner sees at a glance which modules are computed from real data
# vs illustrative templates. Routes left UNMAPPED render no badge —
# honest silence beats a wrong label (only confident classifications
# are tagged). Conservative: anything ambiguous is omitted.
_SOURCE_META = {
    "live":  ("var(--sc-positive,#0a8a5f)", "Live",
              "Computed live from the realized-deal corpus"),
    "cms":   ("var(--sc-teal,#155752)", "CMS",
              "Computed from CMS public datasets"),
    "illus": ("var(--sc-warning,#b8732a)", "Illustrative",
              "Illustrative template — representative figures, not live data"),
}
_MODULE_SOURCE = {
    # Live — realized-deal corpus
    "/base-rates": "live", "/market-rates": "live", "/redflag-scanner": "live",
    "/backtester": "live", "/antitrust-screener": "live",
    "/rollup-economics": "live", "/sponsor-league": "live",
    "/sponsor-heatmap": "live",
    # CMS public data
    "/cms-data-browser": "cms", "/cms-sources": "cms", "/msa-concentration": "cms",
    # Illustrative templates — hardcoded representative data
    "/deal-origination": "illus", "/payer-concentration": "illus",
    "/fraud-detection": "illus", "/drug-shortage": "illus", "/cyber-risk": "illus",
    "/ai-operating-model": "illus", "/health-equity": "illus",
    "/physician-labor": "illus", "/phys-comp-plan": "illus",
    "/locum-tracker": "illus", "/ma-contracts": "illus",
    "/drug-pricing-340b": "illus", "/aco-economics": "illus",
    "/denovo-expansion": "illus", "/pmi-playbook": "illus",
    "/direct-employer": "illus", "/cin-analyzer": "illus", "/zbb-tracker": "illus",
    "/capital-pacing": "illus", "/covenant-headroom": "illus",
    "/direct-lending": "illus", "/reit-analyzer": "illus",
    "/telehealth-econ": "illus", "/hcit-platform": "illus",
    "/biosimilars": "illus", "/trial-site-econ": "illus",
}


def _source_badge(route: str) -> str:
    key = _MODULE_SOURCE.get(route)
    if not key:
        return ""
    color, label, title = _SOURCE_META[key]
    return (
        f'<span class="dir-src" style="--src-c:{color};" '
        f'title="{_html.escape(title, quote=True)}">{_html.escape(label)}</span>'
    )


def _featured_card(mod, idx: int, tint: str) -> str:
    viz_html, stats = _VIZ_ROTATION[idx % len(_VIZ_ROTATION)](tint)
    stats_cells = "".join(
        f'<div><div class="dir-card-stat-l">{_html.escape(lbl)}</div>'
        f'<div class="dir-card-stat-v">{_html.escape(val)}</div></div>'
        for lbl, val in stats
    )
    haystack = _html.escape(
        f"{mod.name} {mod.description} {mod.route} {mod.category}".lower(),
        quote=True,
    )
    return (
        f'<a class="dir-card" href="{_html.escape(mod.route, quote=True)}" '
        f'data-q="{haystack}" '
        f'style="border-top:3px solid {tint};">'
        f'<div class="dir-card-kicker">{_html.escape(mod.category)} '
        f'<span style="color:{tint};">&middot; featured</span>'
        f'{_source_badge(mod.route)}</div>'
        f'<div class="dir-card-title">{_html.escape(mod.name)}</div>'
        f'<div class="dir-card-route" style="color:{tint};">'
        f'{_html.escape(mod.route)}</div>'
        '<div class="dir-card-viz">'
        f'<div>{viz_html}</div>'
        f'<div class="dir-card-stats" '
        f'style="grid-template-columns:repeat({len(stats)},1fr);">'
        f'{stats_cells}</div>'
        '</div>'
        f'<div class="dir-card-purpose">{_html.escape(mod.description)}</div>'
        '</a>'
    )


def _compact_row(mod, tint: str) -> str:
    haystack = _html.escape(
        f"{mod.name} {mod.description} {mod.route} {mod.category}".lower(),
        quote=True,
    )
    return (
        f'<a class="dir-row" href="{_html.escape(mod.route, quote=True)}" '
        f'data-q="{haystack}">'
        '<div style="min-width:0;">'
        f'<div class="dir-row-title">{_html.escape(mod.name)}'
        f'{_source_badge(mod.route)}</div>'
        f'<div class="dir-row-route" style="color:{tint};">'
        f'{_html.escape(mod.route)}</div>'
        '</div>'
        f'<div class="dir-row-persona">{_html.escape(mod.primary_persona)} '
        '&rarr;</div>'
        '</a>'
    )


def _group_section(category: str, modules: list) -> str:
    tint, blurb = _CATEGORY_META.get(
        category, ("var(--sc-teal-ink)", "Platform modules."),
    )
    # Feature the first 2 modules when the category is large enough to
    # warrant a left rail; otherwise everything goes in the compact list.
    featured = modules[:2] if len(modules) >= 3 else []
    rest = modules[len(featured):]
    has_featured = bool(featured)

    featured_html = ""
    if has_featured:
        cards = "".join(
            _featured_card(m, i, tint) for i, m in enumerate(featured)
        )
        featured_html = f'<div class="dir-featured">{cards}</div>'

    rows = "".join(_compact_row(m, tint) for m in rest)
    rest_label = (
        f"Also in {category.lower()}" if has_featured
        else f"All {category.lower()}"
    )
    rest_html = (
        f'<div><div class="dir-rest-label">{_html.escape(rest_label)}</div>'
        f'<div class="dir-rows">{rows}</div></div>'
    )

    body_cls = "dir-body has-featured" if has_featured else "dir-body"
    n = len(modules)
    return (
        f'<div class="dir-group" data-cat="{_html.escape(category, quote=True)}">'
        '<div class="dir-group-head">'
        f'<div class="dir-letterform" style="color:{tint};">'
        f'{_html.escape(category[:1].lower())}</div>'
        '<div style="min-width:0;">'
        f'<div class="dir-group-label" style="color:{tint};">'
        f'{_html.escape(category)} &middot; section</div>'
        f'<h2 class="dir-group-name">{_html.escape(category)}</h2>'
        f'<p class="dir-group-blurb">{blurb}</p>'
        '</div>'
        f'<div class="dir-group-count">{n} surface{"" if n == 1 else "s"}</div>'
        '</div>'
        f'<div class="{body_cls}">{featured_html}{rest_html}</div>'
        '</div>'
    )


# ── Public entry point ──────────────────────────────────────────────

def render_module_index(params: dict = None) -> str:
    """Render the editorial module directory at /module-index."""
    from rcm_mc.data_public.module_index import compute_module_index
    r = compute_module_index()

    # Group the real modules by their real category, in lifecycle order.
    by_cat: dict = {}
    for m in r.modules:
        by_cat.setdefault(m.category, []).append(m)
    ordered_cats = (
        [c for c in _CATEGORY_ORDER if c in by_cat]
        + [c for c in by_cat if c not in _CATEGORY_ORDER]
    )

    # Filter chips — one per category + an "All" reset.
    chips = (
        '<button type="button" class="dir-chip active" data-cat="">'
        f'All ({r.total_modules})</button>'
    )
    for cat in ordered_cats:
        tint = _CATEGORY_META.get(cat, ("var(--sc-teal-ink)", ""))[0]
        chips += (
            f'<button type="button" class="dir-chip" '
            f'data-cat="{_html.escape(cat, quote=True)}" '
            f'style="border-left:3px solid {tint};">'
            f'{_html.escape(cat)} ({len(by_cat[cat])})</button>'
        )

    sections = "".join(
        _group_section(cat, by_cat[cat]) for cat in ordered_cats
    )

    meta_line = (
        f'{r.total_modules} surfaces &middot; {r.categories} categories '
        f'&middot; {r.corpus_deal_count:,} corpus deals'
    )

    body = (
        _STYLE
        + '<div class="ck-page-wrap">'
        # Title / eyebrow / deck come from chartis_shell's editorial_intro
        # below — the bespoke hero here duplicated them (a second <h1>
        # plus a second eyebrow). A small meta line is kept for the
        # live module count.
        + '<div style="font-family:var(--sc-mono);font-size:11px;'
        'letter-spacing:0.18em;text-transform:uppercase;'
        'color:var(--sc-teal-ink);margin:0 0 14px;">'
        f'{meta_line}</div>'
        # Data-trust legend — what the per-module source badges mean.
        '<div class="dir-trust-legend">'
        '<span style="font-weight:600;">Data source:</span>'
        f'{_source_badge("/base-rates")}<span>computed from the realized-deal corpus</span>'
        f'{_source_badge("/cms-data-browser")}<span>CMS public datasets</span>'
        f'{_source_badge("/locum-tracker")}<span>representative template, not live data</span>'
        '</div>'
        # Controls — filter chips + search
        '<div class="dir-controls">'
        f'<div class="dir-chips">{chips}</div>'
        '<input type="text" id="dir-search" class="dir-search" '
        'placeholder="Search name, route, purpose&hellip;" '
        'aria-label="Search modules"/>'
        '</div>'
        '<div class="dir-empty" id="dir-empty" style="display:none;">'
        'No modules match your search.</div>'
        f'{sections}'
        '</div>'
        + _SCRIPT
    )

    explainer = render_page_explainer(
        what=(
            "Browsable directory of every analytical module on the "
            "platform, grouped by diligence category. Each section "
            "leads with featured surfaces, then lists the full "
            "inventory; filter by category or search by name, route, "
            "or purpose."
        ),
        source="data_public/module_index.py (module catalog).",
        page_key="module-index",
    )
    return chartis_shell(
        explainer + body, "Module Index", active_nav="/module-index",
        editorial_intro={
            "eyebrow": "MODULE DIRECTORY",
            "headline": "Every surface in the platform, one jump away.",
            "italic_word": "surface",
        },
    )
