"""Target Screener — the real Source workbench.

Route: GET /target-screener. The unified target-screening workbench for the
Source workflow:

    Source → Target Screener → evaluate → compare → just-missed scan
            → save screen → open profile / X-Ray → promote to Pipeline

Six screens, server-rendered, driven by ``?view=`` (main | inspector |
columns | compare | missed | saved). Recreated PEdesk-native from the
``workbench-full.html`` design handoff — NO iframe, NO external CDN fonts,
NO square-tile cartogram. The real US map (``render_us_geo_map``), the
vertical provider tables, compare, just-missed and saved-screen logic land in
the follow-up PRs (see docs/TARGET_SCREENER_WORKBENCH.md); this PR is the shell
+ navigation contract with clearly-labeled scaffolds for the not-yet-wired
screens.

Screens it searches: the real CMS/provider universes we have onboarded
(HCRIS hospitals, home health, hospice, SNF, dialysis, IRF, LTCH, provider
supply, market-only geographies). The historical deal corpus is NEVER an
active target universe — only ever a labeled benchmark/research reference.
"""
from __future__ import annotations

from typing import Dict, List, Optional

# ── Six workbench screens (the view= states) ─────────────────────────────
# group: "states" (01-03 workbench states) | "linked" (04-06 linked screens).
_VIEWS = [
    {"key": "main", "num": "01", "label": "Main", "emph": "Main",
     "sub": "SCREEN · MAP · TABLE", "group": "states"},
    {"key": "inspector", "num": "02", "label": "Inspector", "emph": "Inspector",
     "sub": "DRAWER · PEER · MARKET", "group": "states"},
    {"key": "columns", "num": "03", "label": "Columns", "emph": "Columns",
     "sub": "PICKER · METRIC DICT", "group": "states"},
    {"key": "compare", "num": "04", "label": "Compare", "emph": "Compare",
     "sub": "METRIC BY METRIC", "group": "linked"},
    {"key": "missed", "num": "05", "label": "Just missed", "emph": "missed",
     "sub": "MISS-DISTANCE SCAN", "group": "linked"},
    {"key": "saved", "num": "06", "label": "Saved screens", "emph": "Saved",
     "sub": "SHAREABLE · QUERY STATE", "group": "linked"},
]
_VIEW_KEYS = {v["key"] for v in _VIEWS}

# ── Vertical universes (separate screening modes) ────────────────────────
# ``live`` = a real loader is wired today; non-live verticals render an honest
# DATA REQUIRED / coming-soon state rather than fabricated rows.
_VERTICALS = [
    {"key": "hospitals", "label": "Hospitals", "universe": "HCRIS",
     "loader": "data.hcris", "live": True,
     "note": "CMS HCRIS cost-report universe — beds, revenue, margin, payer mix."},
    {"key": "home_health", "label": "Home Health", "universe": "CMS HHA",
     "loader": "data.home_health", "live": True,
     "note": "CMS Home Health Compare — providers, quality, CAHPS."},
    {"key": "hospice", "label": "Hospice", "universe": "CMS Hospice",
     "loader": "data.hospice", "live": True,
     "note": "CMS Hospice Compare — providers, quality, CAHPS."},
    {"key": "snf", "label": "SNF / Nursing", "universe": "CMS SNF",
     "loader": "data.snf", "live": True,
     "note": "CMS Nursing Home Compare — beds, SFF status, CHOW/ownership."},
    {"key": "dialysis", "label": "Dialysis", "universe": "CMS Dialysis",
     "loader": "data.dialysis", "live": True,
     "note": "CMS Dialysis Compare — stations, chain ownership, modalities."},
    {"key": "irf", "label": "IRF", "universe": "CMS IRF",
     "loader": "data.irf", "live": True,
     "note": "Inpatient Rehabilitation Facilities — providers, quality."},
    {"key": "ltch", "label": "LTCH", "universe": "CMS LTCH",
     "loader": "data.ltch", "live": True,
     "note": "Long-Term Care Hospitals — providers, quality."},
    {"key": "provider_supply", "label": "Provider Supply", "universe": "NPPES / supply",
     "loader": "data.provider_supply", "live": True,
     "note": "Physician / provider supply density by geography."},
    {"key": "market", "label": "Market (county/state)", "universe": "Public geo",
     "loader": "geo-intel", "live": True,
     "note": "Screen geographies (demographics, MA, SDOH, shortage) — not a "
             "provider, a market."},
]
_VERTICAL_KEYS = {v["key"] for v in _VERTICALS}

# Legacy modes preserved (backward compatible) — surfaced on Main as the three
# established ways into the SAME public universe; routes unchanged.
_MODES = [
    {"key": "sourcing", "label": "Thesis Sourcing", "href": "/source",
     "how": "Thesis-driven · ranks providers by fit to a thesis profile."},
    {"key": "hospital", "label": "Hospital Screener", "href": "/screen",
     "how": "Manual filters · you set the criteria."},
    {"key": "predictive", "label": "Predictive Screener", "href": "/predictive-screener",
     "how": "Model-ranked · scored over the public HCRIS universe."},
]

_CSS = """
.tsw-tabs{display:flex;gap:0;overflow-x:auto;border:1px solid var(--sc-rule,#c9c1ac);
 border-radius:3px;background:var(--sc-paper-2,#f3eddb);margin:14px 0 18px;}
.tsw-group{display:flex;}
.tsw-group + .tsw-group{border-left:1px solid var(--sc-rule,#c9c1ac);}
.tsw-glabel{padding:0 12px;font-family:var(--sc-mono);font-size:8px;letter-spacing:.14em;
 text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);align-self:center;
 background:var(--sc-paper-3,#ece5d6);border-right:1px solid var(--sc-rule,#c9c1ac);
 line-height:1.3;}
.tsw-tab{padding:11px 16px 9px;border-right:1px solid var(--sc-rule,#c9c1ac);
 display:grid;grid-template-columns:auto 1fr;gap:10px;align-items:center;
 min-width:170px;text-decoration:none;background:var(--sc-paper-2,#f3eddb);}
.tsw-tab:last-child{border-right:0;}
.tsw-tab:hover{background:var(--sc-paper,#faf6ec);}
.tsw-tab.is-active{background:var(--sc-paper,#faf6ec);border-bottom:3px solid var(--sc-teal-deep,#0e3d39);padding-bottom:6px;}
.tsw-num{font-family:var(--sc-serif);font-style:italic;font-size:21px;line-height:1;
 color:var(--sc-teal,#155752);width:22px;text-align:center;}
.tsw-tab.is-active .tsw-num{color:var(--sc-teal-deep,#0e3d39);}
.tsw-t{font-family:var(--sc-serif);font-size:14.5px;color:var(--sc-navy,#15202b);line-height:1.1;}
.tsw-t em{font-style:italic;color:var(--sc-teal,#155752);}
.tsw-s{font-family:var(--sc-mono);font-size:8px;letter-spacing:.1em;text-transform:uppercase;
 color:var(--sc-text-faint,#8b94a0);margin-top:3px;}
.tsw-verticals{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 16px;}
.tsw-vert{font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.04em;
 padding:5px 11px;border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;
 text-decoration:none;color:var(--sc-text,#2a3a4a);background:var(--sc-paper,#faf6ec);}
.tsw-vert:hover{border-color:var(--sc-teal,#155752);}
.tsw-vert.is-active{background:var(--sc-navy,#15202b);color:var(--sc-paper,#faf6ec);border-color:var(--sc-navy,#15202b);}
.tsw-vert .u{opacity:.6;font-size:9px;}
.ts-modes{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:6px 0 var(--sc-s-5);}
@media (max-width:900px){.ts-modes{grid-template-columns:1fr;}.tsw-tab{min-width:140px;}}
.ts-mode{display:flex;flex-direction:column;gap:7px;background:var(--sc-paper,#faf6ec);
 border:1px solid var(--sc-rule,#c9c1ac);border-top:3px solid var(--sc-teal,#155752);
 padding:15px 17px;text-decoration:none;}
.ts-mode:hover{box-shadow:var(--sc-shadow-2,0 8px 24px rgba(11,32,55,.14));}
.ts-mode.is-active{border-top-color:var(--sc-navy,#15202b);background:var(--sc-bone,#f3eddb);}
.ts-mode-label{font-family:var(--sc-serif);font-size:19px;color:var(--sc-navy,#15202b);line-height:1.1;}
.ts-mode-how{font-family:var(--sc-mono);font-size:10px;letter-spacing:.04em;color:var(--sc-text-dim,#6a7480);}
.ts-mode-go{margin-top:auto;font-family:var(--sc-mono);font-size:10px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-teal,#155752);}
.tsw-scaffold{background:var(--sc-paper,#faf6ec);border:1px dashed var(--sc-rule-2,#bfb6a2);
 border-radius:3px;padding:18px 20px;margin:14px 0;}
.tsw-scaffold h3{font-family:var(--sc-serif);font-size:17px;color:var(--sc-navy,#15202b);margin:0 0 6px;}
.tsw-scaffold .tag{font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-warning,#b8732a);}
.tsw-scaffold ul{margin:8px 0 0 18px;font-family:var(--sc-serif);font-size:13.5px;
 line-height:1.6;color:var(--sc-text,#2a3a4a);}
"""


def _q1(qs: Dict[str, List[str]], key: str, default: str = "") -> str:
    return (qs.get(key) or [default])[0].strip()


def _href(view: str, qs: Dict[str, List[str]]) -> str:
    """Build a /target-screener link that switches view= but preserves the
    other shareable params (vertical/state/etc) — server-rendered state."""
    keep = {}
    for k in ("vertical", "state", "county", "metric", "layer", "ccn",
              "compare", "sort", "direction", "ownership", "provider_type"):
        v = _q1(qs, k)
        if v:
            keep[k] = v
    parts = [f"view={view}"] + [f"{k}={v}" for k, v in keep.items()]
    return "/target-screener?" + "&".join(parts)


def _vhref(vertical: str, qs: Dict[str, List[str]]) -> str:
    keep = {"vertical": vertical, "view": _q1(qs, "view", "main") or "main"}
    st = _q1(qs, "state")
    if st:
        keep["state"] = st
    return "/target-screener?" + "&".join(f"{k}={v}" for k, v in keep.items())


def _tab_bar(active_view: str, qs: Dict[str, List[str]]) -> str:
    groups = {"states": "Workbench<br>states", "linked": "Linked<br>screens"}
    html = ['<nav class="tsw-tabs" aria-label="Target Screener workbench screens">']
    for gkey, glabel in groups.items():
        html.append(f'<div class="tsw-group"><div class="tsw-glabel">{glabel}</div>')
        for v in (x for x in _VIEWS if x["group"] == gkey):
            cls = "tsw-tab is-active" if v["key"] == active_view else "tsw-tab"
            t = v["label"]
            if v["emph"] in t:
                t = t.replace(v["emph"], f'<em>{v["emph"]}</em>', 1)
            else:
                t = f'<em>{t}</em>'
            html.append(
                f'<a class="{cls}" href="{_href(v["key"], qs)}" '
                f'aria-current="{"page" if v["key"] == active_view else "false"}">'
                f'<span class="tsw-num">{v["num"]}</span>'
                f'<span class="tsw-meta"><span class="tsw-t">{t}</span>'
                f'<span class="tsw-s">{v["sub"]}</span></span></a>'
            )
        html.append('</div>')
    html.append('</nav>')
    return "".join(html)


def _vertical_bar(active_vertical: str, qs: Dict[str, List[str]]) -> str:
    chips = []
    for v in _VERTICALS:
        cls = "tsw-vert is-active" if v["key"] == active_vertical else "tsw-vert"
        chips.append(
            f'<a class="{cls}" href="{_vhref(v["key"], qs)}" title="{v["note"]}">'
            f'{v["label"]} <span class="u">{v["universe"]}</span></a>'
        )
    return ('<div style="font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;'
            'text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);margin-bottom:5px;">'
            'Vertical / universe</div><div class="tsw-verticals">' + "".join(chips) + '</div>')


def _scaffold(title: str, pr: str, bullets: List[str]) -> str:
    items = "".join(f"<li>{b}</li>" for b in bullets)
    return (
        f'<div class="tsw-scaffold"><span class="tag">Scaffold · wires in {pr}</span>'
        f'<h3>{title}</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:13.5px;color:var(--sc-text-dim,#6a7480);'
        f'margin:4px 0 0;">This workbench screen is structurally in place; its live data and '
        f'controls land in {pr}. Nothing fabricated is shown until then.</p>'
        f'<ul>{items}</ul></div>'
    )


def _screen_main(vertical: str, qs: Dict[str, List[str]], ck) -> str:
    active_mode = _q1(qs, "mode").lower()
    cards = "".join(
        f'<a class="ts-mode{" is-active" if m["key"] == active_mode else ""}" '
        f'href="{m["href"]}">'
        f'<span class="ts-mode-label">{m["label"]}</span>'
        f'<span class="ts-mode-how">{m["how"]}</span>'
        f'<span class="ts-mode-go">Open {m["label"]} &rarr;</span></a>'
        for m in _MODES
    )
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    return (
        _vertical_bar(vertical, qs)
        + ck["panel"](
            f'<p class="ck-section-body" style="margin:0;">Screening '
            f'<strong>{vinfo["label"]}</strong> &middot; <span style="font-family:var(--sc-mono);'
            f'font-size:11px;">{vinfo["universe"]}</span>. {vinfo["note"]} '
            f'This is market data, not your deals.</p>',
            title="Active universe")
        + _scaffold("Real US map + ranked provider table", "PR 3 & PR 4", [
            "Real SVG US map (reuses render_us_geo_map — the /portfolio/map "
            "renderer, not squares); click a state to filter.",
            "Layer selector + legend shaded by the chosen metric.",
            "Ranked provider table from the live loader with source + "
            "missingness chips and profile / X-Ray / compare / save actions.",
        ])
        + ck["panel"](
            '<p class="ck-section-body">Three established ways into the SAME '
            'public universe — preserved and unchanged:</p>'
            f'<div class="ts-modes">{cards}</div>',
            title="Same universe, three ways in")
        + ck["panel"](
            'Rank and score geographic markets first — '
            '<a href="/geo-intel" style="font-weight:600">Geographic Intelligence</a> '
            'and <a href="/market-intel/geo" style="font-weight:600">Geographic Market '
            'Intelligence &rarr;</a>. Then open a candidate\'s '
            '<a href="/diligence/hcris-xray" class="ck-link">HCRIS X-Ray</a> or '
            '<a href="/diligence/xray" class="ck-link">CMS X-Ray</a>, check its '
            'market, and <a href="/pipeline" class="ck-link">promote it to '
            'Pipeline</a>.',
            title="Screen the market, then the target · next steps")
    )


def _screen_inspector(qs, ck) -> str:
    ccn = _q1(qs, "ccn")
    sel = (f' for <code>{ccn}</code>' if ccn else " — no target selected "
           "(open a row from Main)")
    return _scaffold(f"Inspector drawer{sel}", "PR 8", [
        "Selected provider/market identity + source/status chips.",
        "Key metrics, market context, peer context, data caveats.",
        "Links: provider profile, HCRIS / CMS X-Ray, market profile.",
        "Guide suggested questions. No fabricated notes.",
    ])


def _screen_columns(qs, ck) -> str:
    return _scaffold("Column picker + metric dictionary", "PR 7", [
        "Columns grouped by category: identity, geography, quality, "
        "financial/HCRIS, payer/reimbursement, market intelligence, "
        "ownership/consolidation, SDOH/access, source/provenance.",
        "Per-metric description, source, and data-availability count.",
        "Visibility toggles persisted via query params.",
        "A metric with no source is never displayed.",
    ])


def _screen_compare(qs, ck) -> str:
    comp = _q1(qs, "compare")
    n = len([c for c in comp.split(",") if c]) if comp else 0
    return _scaffold(f"Compare basket ({n} selected)", "PR 5", [
        "Add/remove targets via ?compare=ccn1,ccn2,…",
        "Metric-by-metric comparison with source/status chips per target.",
        "Same-vertical targets compare fully; cross-vertical only on shared "
        "metrics — non-comparable metrics show “not comparable”, never fake values.",
        "Percentile/rank + market context where available.",
    ])


def _screen_missed(qs, ck) -> str:
    return _scaffold("Just-missed scan", "PR 6", [
        "Providers/markets that failed the active filters by one or two "
        "criteria — with which criteria and how far off.",
        "“Relax this filter to include N”, recomputed server-side from query params.",
        "“Data missing, not failed” when exclusion was a missing value.",
        "Open in Compare · Save screen.",
    ])


def _screen_saved(qs, ck) -> str:
    return _scaffold("Saved screens", "PR 9", [
        "Screens captured as shareable /target-screener?… URLs (server-first "
        "state) so a screen is a link you can paste.",
        "Title, vertical, filters, last-run — when real persistence exists.",
        "Until storage is wired: an honest “persistence not wired yet” "
        "state, plus a documented schema for future storage. No fake alerts.",
    ])


_SCREENS = {
    "inspector": _screen_inspector, "columns": _screen_columns,
    "compare": _screen_compare, "missed": _screen_missed, "saved": _screen_saved,
}


def render_target_screener(qs: Optional[Dict[str, List[str]]] = None) -> str:
    from ._chartis_kit import (chartis_shell, ck_data_universe, ck_page_title,
                               ck_panel, ck_source_purpose)
    qs = qs or {}
    view = _q1(qs, "view", "main")
    if view not in _VIEW_KEYS:
        view = "main"
    vertical = _q1(qs, "vertical", "hospitals")
    if vertical not in _VERTICAL_KEYS:
        vertical = "hospitals"
    ck = {"panel": ck_panel}

    title = ck_page_title(
        "Target Screener", eyebrow="SOURCE · /target-screener · WORKBENCH",
        meta="six screens · every public CMS/provider universe · same data, not your deals",
    ) + '<div style="margin:8px 0 0;">' + ck_data_universe("cms") + '</div>'

    source_purpose = ck_source_purpose(
        purpose="Find acquisition targets across every public CMS/provider "
                "universe — hospitals, home health, hospice, SNF, dialysis, IRF, "
                "LTCH, provider supply, and markets — by filter, map, score, and "
                "just-missed scan, before committing diligence effort.",
        universe="cms",
        source="Real CMS / HCRIS / provider public universes (market data, not "
               "your deals). The historical deal corpus is never an active target.",
        next_action="Promote a result into the Pipeline to track it",
        next_href="/pipeline",
    )

    tab_bar = _tab_bar(view, qs)
    if view == "main":
        screen = _screen_main(vertical, qs, ck)
    else:
        screen = _SCREENS[view](qs, ck)

    note = (
        '<p class="ck-section-body" style="font-style:italic;max-width:80ch;">'
        'All screening runs over the same public CMS/provider universes — this '
        'is market data, not your deals. Promote a result into the Pipeline to '
        'start tracking it. (Six screens; press a tab to switch.)</p>'
    )

    body = (
        title + source_purpose + tab_bar + screen
        + ck_panel(note, title="One universe, one workbench")
    )
    return chartis_shell(body, "Target Screener", active_nav="/target-screener",
                         extra_css=_CSS)
