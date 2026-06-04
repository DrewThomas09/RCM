"""Command Center — dossier-card grid layout (parallel preview at
``/app?layout=grid``).

A 12-column modular dossier grid recreating the "PE Desk — Command Center
Redesign" handoff, shipped BEHIND a query flag so the live flat-scroll /app
(``render_app_page``) is untouched and the flagship page can be compared /
de-risked before any default switch.

Honest by construction: KPI/funnel/roster cards render from the real
``portfolio_rollup`` + ``latest_per_deal`` data with the handoff's empty
states (``—`` + italic "awaiting data") when a metric isn't computed — no
fabricated MOIC/IRR/deal values. The heavier analytic cards (morning brief,
quick access, covenant heatmap, EBITDA drag, initiative variance, alerts,
deliverables) reuse the existing ``_app_*`` block renderers verbatim inside
scrollable card bodies, so their real data + empty states carry over with no
duplication. No new queries (same rollup + deals_df), no persistence, no
external calls.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ._app_alerts import render_alerts
from ._app_covenant_heatmap import render_covenant_heatmap
from ._app_deals_table import render_deals_table
from ._app_deliverables import render_deliverables
from ._app_ebitda_drag import render_ebitda_drag
from ._app_initiative_tracker import render_initiative_tracker
from ._app_morning_brief import render_morning_brief
from ._app_pipeline_funnel import render_pipeline_funnel
from ._app_quick_access import render_quick_access


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


# Scoped grid CSS (handoff tokens inlined as --cc-* locals). Passed to the
# shell as extra_css for the grid view only — does not affect the default
# flat-scroll /app.
APP_GRID_CSS = """
.cc-page{--cc-page-bg:var(--sc-parchment,#f2ede3);--cc-paper:#faf6ec;--cc-paper2:#f3eddb;
  --cc-ink:#15202b;--cc-ink2:#2a3a4a;--cc-muted:#6a7480;--cc-muted2:#8b94a0;
  --cc-rule:#c9c1ac;--cc-green:#1f7a5a;--cc-amber:#b8842e;--cc-navy:#0d2336;
  --cc-red:#b14a3a;--cc-green-soft:#d6e8df;
  --cc-serif:'Source Serif 4',Georgia,serif;
  --cc-sans:'Inter Tight',Inter,ui-sans-serif,system-ui,sans-serif;
  --cc-mono:'JetBrains Mono',ui-monospace,monospace;
  background:var(--cc-page-bg);padding:36px 48px 80px;max-width:1500px;margin:0 auto;
  box-sizing:border-box;}
.cc-page *{box-sizing:border-box;}
@media (max-width:1280px){ .cc-page{padding:24px 32px 60px;} }
.cc-top{border-bottom:1px solid var(--cc-rule);padding-bottom:18px;margin-bottom:18px;}
.cc-crumb{font-family:var(--cc-mono);font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--cc-muted);margin-bottom:10px;}
.cc-crumb-slug{color:var(--cc-ink);}
.cc-top-row{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}
.cc-h1{font-family:var(--cc-serif);font-weight:400;font-size:50px;letter-spacing:-.02em;
  color:var(--cc-ink);margin:0;line-height:1;}
.cc-h1-em{font-style:italic;color:var(--cc-green);}
.cc-lede{font-family:var(--cc-serif);font-size:16px;line-height:1.5;color:var(--cc-ink2);margin:10px 0 0;max-width:74ch;}
.cc-actions{display:flex;gap:8px;}
.cc-btn{font-family:var(--cc-mono);font-size:11px;font-weight:600;letter-spacing:.08em;
  text-transform:uppercase;color:var(--cc-ink);background:var(--cc-paper);
  border:1px solid var(--cc-ink);border-radius:2px;padding:8px 13px;cursor:pointer;
  text-decoration:none;display:inline-flex;align-items:center;}
.cc-btn:disabled{opacity:.45;cursor:not-allowed;}
.cc-btn-primary{background:var(--cc-ink);color:var(--cc-paper);}
.cc-btn:focus-visible{outline:2px solid var(--cc-green);outline-offset:2px;}
/* 12-column dossier grid */
.cc-grid{display:grid;grid-template-columns:repeat(12,1fr);grid-auto-rows:minmax(140px,auto);gap:14px;}
.cc-5x2{grid-column:span 5;grid-row:span 2;}
.cc-4x1{grid-column:span 4;grid-row:span 1;}
.cc-3x1{grid-column:span 3;grid-row:span 1;}
.cc-7x3{grid-column:span 7;grid-row:span 3;}
.cc-5x3{grid-column:span 5;grid-row:span 3;}
.cc-12x2{grid-column:span 12;grid-row:span 2;}
.cc-12x3{grid-column:span 12;grid-row:span 3;}
.cc-6x2{grid-column:span 6;grid-row:span 2;}
@media (max-width:1024px){
  .cc-grid{grid-template-columns:repeat(6,1fr);}
  .cc-5x2,.cc-7x3,.cc-5x3,.cc-12x2,.cc-12x3,.cc-6x2{grid-column:span 6;}
  .cc-4x1,.cc-3x1{grid-column:span 3;}
}
@media (max-width:768px){
  .cc-grid{grid-template-columns:1fr;grid-auto-rows:auto;}
  /* min-width:0 lets the single 1fr column actually shrink to the
     viewport: grid items default to min-width:auto, so a card whose
     content has a wide min-content size (a KPI hero, a chart) would
     otherwise force the column — and the whole page — wider than the
     screen (the prior ~856px blow-out at 375px). overflow-x:auto then
     keeps any genuinely-wide card content scrolling INSIDE the card. */
  .cc-grid>*{grid-column:1/-1 !important;grid-row:auto !important;min-height:140px;min-width:0;}
  .cc-card{min-width:0;}
  .cc-body{overflow-x:auto;}
}
/* Dossier card */
.cc-card{position:relative;background:var(--cc-paper);border:1px solid var(--cc-rule);
  display:flex;flex-direction:column;overflow:visible;min-height:0;}
.cc-tag{position:absolute;top:0;left:0;padding:4px 12px 4px 14px;font-family:var(--cc-mono);
  font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--cc-paper);
  background:var(--cc-ink);}
.cc-tag-green{background:var(--cc-green);}
.cc-tag-amber{background:var(--cc-amber);}
.cc-tag-navy{background:var(--cc-navy);}
.cc-tag-red{background:var(--cc-red);}
.cc-ch{display:flex;align-items:center;justify-content:space-between;
  padding:30px 20px 12px;border-bottom:1px solid var(--cc-ink);}
.cc-title{font-family:var(--cc-serif);font-style:italic;font-weight:400;font-size:17px;
  color:var(--cc-ink2);margin:0;}
.cc-title-em{font-style:normal;color:var(--cc-green);}
.cc-pin{color:var(--cc-muted2);opacity:.35;font-size:14px;}
.cc-body{flex:1;padding:16px 20px;overflow:visible;min-height:0;}
.cc-body-scroll{overflow:auto;}
.cc-body-scroll::-webkit-scrollbar{width:7px;}
.cc-body-scroll::-webkit-scrollbar-thumb{background:var(--cc-rule);border-radius:4px;}
/* KPI */
.cc-kpi{font-family:var(--cc-serif);font-size:36px;color:var(--cc-ink);line-height:1;}
.cc-kpi-hero{font-size:96px;}
.cc-kpi-em{font-style:italic;color:var(--cc-green);}
.cc-kpi-x{font-family:var(--cc-mono);font-size:18px;color:var(--cc-muted);}
.cc-kpi-of{font-family:var(--cc-mono);font-size:13px;color:var(--cc-muted);margin-left:8px;}
.cc-kpi-sub{font-family:var(--cc-serif);font-style:italic;font-size:13px;color:var(--cc-muted);margin-top:8px;}
.cc-kpi-empty{font-family:var(--cc-serif);font-size:36px;color:var(--cc-muted2);}
.cc-kpi-await{font-family:var(--cc-serif);font-style:italic;font-size:13px;color:var(--cc-muted2);}
/* Funnel */
.cc-funnel-row{display:flex;align-items:center;gap:12px;margin-bottom:10px;}
.cc-funnel-lbl{width:64px;font-family:var(--cc-serif);font-size:13px;color:var(--cc-ink2);}
.cc-funnel-track{flex:1;height:12px;background:var(--cc-paper2);border:1px solid var(--cc-rule);}
.cc-funnel-bar{display:block;height:100%;background:var(--cc-ink);}
.cc-funnel-bar-green{background:var(--cc-green);}
.cc-funnel-n{width:32px;text-align:right;font-family:var(--cc-mono);font-size:12px;color:var(--cc-ink);}
/* Roster */
.cc-roster-row{display:flex;align-items:center;gap:12px;padding:12px 0;
  border-top:1px dashed var(--cc-rule);}
.cc-roster-row:first-child{border-top:0;}
.cc-dot{width:8px;height:8px;border-radius:50%;flex:none;}
.cc-dot-green{background:var(--cc-green);}
.cc-dot-amber{background:var(--cc-amber);}
.cc-dot-red{background:var(--cc-red);}
.cc-roster-name{flex:1;font-family:var(--cc-serif);font-size:16px;color:var(--cc-ink);text-decoration:none;}
.cc-roster-name:hover{color:var(--cc-green);}
.cc-stage-chip{font-family:var(--cc-mono);font-size:11px;color:var(--cc-ink2);
  background:var(--cc-paper2);border:1px solid var(--cc-rule);padding:2px 8px;text-transform:uppercase;}
.cc-roster-arr{color:var(--cc-muted2);}
.cc-empty-row{font-family:var(--cc-serif);font-style:italic;color:var(--cc-muted);text-align:center;margin:18px 0;}
.cc-empty-sub{color:var(--cc-muted2);}
/* Source registry footer */
.cc-sources{margin-top:18px;padding-top:14px;border-top:1px solid var(--cc-rule);
  font-family:var(--cc-mono);font-size:10.5px;letter-spacing:.06em;color:var(--cc-muted);}
.cc-sources-k{text-transform:uppercase;letter-spacing:.14em;color:var(--cc-muted2);margin-right:10px;}
.cc-sources code{color:var(--cc-ink2);}
/* Add-card placeholders */
.cc-addcard{grid-column:span 3;grid-row:span 1;background:transparent;
  border:1px dashed var(--cc-rule);color:var(--cc-muted);font-family:var(--cc-serif);
  font-style:italic;font-size:14px;cursor:not-allowed;}
@media (max-width:1024px){ .cc-addcard{grid-column:span 3;} }
"""


# ── Dossier-card primitive ──────────────────────────────────────────────────

def _title_html(title: str, em: str) -> str:
    """Card title. Rendered as a contiguous label (italic via CSS) so the
    full section name stays searchable + screen-reader friendly; the green
    "brand moment" is carried by the KPI numerals + tag strip instead of
    splitting the title with an inner span."""
    return _esc(title)


def _card(*, tag: str, color: str, title: str, em: str = "", body: str,
          span: str, scroll: bool = False, idx: int = 0) -> str:
    lid = f"cc-h-{idx}"
    body_cls = "cc-body cc-body-scroll" if scroll else "cc-body"
    return (
        f'<article class="cc-card {span}" aria-labelledby="{lid}">'
        f'<span class="cc-tag cc-tag-{color}">{_esc(tag)}</span>'
        '<div class="cc-ch">'
        f'<h4 class="cc-title" id="{lid}">{_title_html(title, em)}</h4>'
        '<span class="cc-pin" aria-hidden="true" title="Pin (visual only)">★</span>'
        '</div>'
        f'<div class="{body_cls}">{body}</div>'
        '</article>'
    )


def _kpi_card(*, tag: str, color: str, title: str, em: str,
              value: Optional[str], sub: str, span: str, hero: bool = False,
              idx: int = 0) -> str:
    """KPI card. ``value=None`` → honest empty state (— + 'awaiting data')."""
    if value is None:
        val = '<span class="cc-kpi-empty">—</span>'
        sub_html = '<span class="cc-kpi-await">awaiting data</span>'
    else:
        val = value
        sub_html = _esc(sub)
    big = " cc-kpi-hero" if hero else ""
    body = (f'<div class="cc-kpi{big}">{val}</div>'
            f'<div class="cc-kpi-sub">{sub_html}</div>')
    return _card(tag=tag, color=color, title=title, em=em, body=body,
                 span=span, idx=idx)


# ── Page ────────────────────────────────────────────────────────────────────

def _page_top(crumb_slug: str, *, section_label: str = "PORTFOLIO & DILIGENCE",
              kicker_label: str = "FUND II", lede: str = "",
              customize: bool = False) -> str:
    # Mono eyebrow carries the two-view lexicon (section · kicker · slug) so
    # the dossier grid frames partner vs consulting identically to the flat
    # page. Section/kicker are rendered uppercase exactly as passed.
    eyebrow = (
        '<div class="cc-crumb">'
        f'{_esc(section_label)} <span class="cc-crumb-slug">&middot; '
        f'{_esc(kicker_label)} &middot; {_esc(crumb_slug)}</span></div>'
    )
    lede_html = f'<p class="cc-lede">{_esc(lede)}</p>' if lede else ''
    # Customize / Add card are now live: they enter the customize panel
    # (/app?customize=1) where cards are shown/hidden (persisted in a cookie).
    if customize:
        actions = (
            '<a class="cc-btn cc-btn-primary" href="/app" '
            'title="Finish customizing">&#10003; Done</a>'
            '<a class="cc-btn" href="/app" title="Reload data">&#8635; Refresh</a>'
        )
    else:
        actions = (
            '<a class="cc-btn" href="/app?customize=1" '
            'title="Show, hide and add cards">&#8862; Customize</a>'
            '<a class="cc-btn" href="/app" title="Reload data">&#8635; Refresh</a>'
            '<a class="cc-btn cc-btn-primary" href="/app?customize=1" '
            'title="Add a card to the dashboard">+ Add card</a>'
        )
    return (
        '<div class="cc-top">'
        + eyebrow
        + '<div class="cc-top-row">'
        '<h1 class="cc-h1">Command <span class="cc-h1-em">center</span>.</h1>'
        f'<div class="cc-actions">{actions}</div>'
        '</div>'
        + lede_html
        + '</div>'
    )


def _funnel_card(rollup: Dict[str, Any], idx: int) -> str:
    """Pipeline funnel from real stage counts (0-bars when empty)."""
    funnel = (rollup or {}).get("stage_funnel") or {}
    rows = [("Sourced", "sourced"), ("IOI", "ioi"), ("LOI", "loi"),
            ("SPA", "spa"), ("Closed", "closed"), ("Exit", "exit")]
    counts = {k: int(funnel.get(k, 0)) for _, k in rows}
    mx = max(counts.values()) if counts else 0
    bars = ""
    for label, key in rows:
        n = counts[key]
        pct = int(100 * n / mx) if mx else 0
        closing = key in ("closed", "exit")
        bars += (
            '<div class="cc-funnel-row">'
            f'<span class="cc-funnel-lbl">{_esc(label)}</span>'
            '<span class="cc-funnel-track">'
            f'<span class="cc-funnel-bar{" cc-funnel-bar-green" if closing else ""}" '
            f'style="width:{pct}%"></span></span>'
            f'<span class="cc-funnel-n">{n}</span>'
            '</div>'
        )
    return _card(tag="Flow", color="green", title="Pipeline funnel",
                 em="funnel", body=bars, span="cc-5x3", idx=idx)


def _roster_card(deals_df: pd.DataFrame, idx: int) -> str:
    """Active deals roster from real deals_df (honest empty state)."""
    if deals_df is None or deals_df.empty:
        body = ('<p class="cc-empty-row">No deals yet '
                '<span class="cc-empty-sub">&middot; Add a deal to populate</span></p>')
        return _card(tag="Roster", color="ink", title="Active deals", em="deals",
                     body=body, span="cc-7x3", idx=idx)
    rows = ""
    dot = {"hold": "green", "exit": "green", "spa": "amber", "loi": "amber"}
    for _, d in deals_df.head(6).iterrows():
        name = _esc(d.get("name") or d.get("deal_id") or "—")
        stage = _esc(str(d.get("stage") or "—"))
        tone = dot.get(str(d.get("stage")), "amber")
        ccn = _esc(str(d.get("deal_id") or ""))
        rows += (
            '<div class="cc-roster-row">'
            f'<span class="cc-dot cc-dot-{tone}"></span>'
            f'<a class="cc-roster-name" href="/app?deal={ccn}">{name}</a>'
            f'<span class="cc-stage-chip">{stage}</span>'
            '<span class="cc-roster-arr">&rarr;</span>'
            '</div>'
        )
    return _card(tag="Roster", color="ink", title="Active deals", em="deals",
                 body=rows, span="cc-7x3", idx=idx)


# Canonical command-center card registry: (card_id, human label). Order is the
# render order; the customize panel and the ck_cards_hidden cookie key off the
# ids. Adding a card here (and building it in render_app_grid) makes it appear
# in the customize toggles automatically.
_CARD_ORDER = [
    ("moic", "Weighted MOIC"),
    ("irr", "Weighted IRR"),
    ("covenants", "Covenants at risk"),
    ("days_cash", "Days cash"),
    ("active_deals", "Active deals (KPI)"),
    ("initiatives", "Initiatives tracked"),
    ("roster", "Active deals roster"),
    ("funnel", "Pipeline funnel"),
    ("morning_brief", "Morning brief"),
    ("quick_access", "Quick access"),
    ("covenant_heatmap", "Covenant heatmap"),
    ("ebitda_drag", "EBITDA drag"),
    ("initiative_variance", "Initiative variance"),
    ("alerts", "Active alerts"),
    ("deliverables", "Deliverables"),
]
_CARD_IDS = frozenset(cid for cid, _ in _CARD_ORDER)


def _customize_panel(hidden: set) -> str:
    """The customize-cards control: a checkbox per card (checked = shown).
    Submitting POSTs the visible set to /app/cards, which persists the hidden
    set in the ck_cards_hidden cookie. Unchecking hides a card; re-checking a
    hidden card adds it back — that's the 'add card' path."""
    n_shown = sum(1 for cid, _ in _CARD_ORDER if cid not in hidden)
    toggles = "".join(
        '<label class="cc-cz-row">'
        f'<input type="checkbox" name="card" value="{_esc(cid)}"'
        f'{" checked" if cid not in hidden else ""}>'
        f'<span>{_esc(label)}</span></label>'
        for cid, label in _CARD_ORDER
    )
    return (
        '<style>'
        '.cc-cz{border:1px solid var(--sc-rule,#c9c1ac);background:var(--sc-paper,#faf6ec);'
        'border-radius:4px;padding:14px 18px;margin:0 0 16px;}'
        '.cc-cz h3{font-family:var(--sc-mono,monospace);font-size:11px;letter-spacing:.1em;'
        'text-transform:uppercase;color:#5c6878;margin:0 0 4px;}'
        '.cc-cz .cc-cz-sub{font-size:12px;color:#465366;margin:0 0 12px;}'
        '.cc-cz-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:6px 16px;}'
        '.cc-cz-row{display:flex;align-items:center;gap:8px;font-size:12.5px;color:#1a2332;cursor:pointer;}'
        '.cc-cz-row input{accent-color:var(--sc-teal,#155752);}'
        '.cc-cz-actions{margin-top:14px;display:flex;gap:10px;align-items:center;}'
        '.cc-cz-save{background:#0b2341;color:#fff;border:none;padding:8px 18px;border-radius:3px;'
        'font-size:12px;font-weight:600;cursor:pointer;}'
        '.cc-cz-cancel{color:#155752;text-decoration:none;font-size:12px;padding:8px 4px;}'
        '</style>'
        '<form class="cc-cz" method="post" action="/app/cards">'
        '<h3>Customize cards</h3>'
        f'<p class="cc-cz-sub">Check the cards to show on your command center '
        f'({n_shown} of {len(_CARD_ORDER)} shown). Unchecking hides a card; '
        'check a hidden one to add it back. Saved to this browser.</p>'
        f'<div class="cc-cz-grid">{toggles}</div>'
        '<div class="cc-cz-actions">'
        '<button type="submit" class="cc-cz-save">Save layout</button>'
        '<a class="cc-cz-cancel" href="/app">Cancel</a>'
        '</div></form>'
    )


def render_app_grid(
    *,
    store: Any,
    rollup: Dict[str, Any],
    deals_df: pd.DataFrame,
    focused_deal_id: Optional[str] = None,
    selected_stage: Optional[str] = None,
    focused_packet: Any = None,
    section_label: str = "PORTFOLIO & DILIGENCE",
    kicker_label: str = "FUND II",
    lede: str = "",
    hidden_cards: Optional[frozenset] = None,
    customize: bool = False,
) -> str:
    """Render the dossier-card grid body (caller wraps it in the shell).

    ``hidden_cards`` is the set of card ids the viewer has hidden (from the
    ``ck_cards_hidden`` cookie); they're filtered out of the grid. ``customize``
    renders the customize panel (toggle each card on/off) above the grid."""
    hidden = set(hidden_cards or frozenset())
    r = rollup or {}
    dc = int(r.get("deal_count") or 0)
    moic = r.get("weighted_moic")
    irr = r.get("weighted_irr")
    trips = int(r.get("covenant_trips") or 0)
    tight = int(r.get("covenant_tight") or 0)
    at_risk = trips + tight

    # KPI hero + strip — real values, honest empty states.
    moic_v = (f'<span class="cc-kpi-em">{moic:.2f}</span>'
              '<span class="cc-kpi-x">x</span>') if moic is not None else None
    irr_v = (f'<span class="cc-kpi-em">{irr*100:.1f}</span>%'
             if irr is not None else None)
    # "of N" is real when we have deals; the risk count is real from rollup.
    cov_v = (f'{at_risk}<span class="cc-kpi-of">of {dc}</span>'
             if dc else None)
    # Literal "·" (not the &middot; entity): _kpi_card html-escapes ``sub``,
    # so an entity would render as the literal text "&middot;".
    cov_sub = (f"{trips} tripped · {tight} tight" if dc else "")

    # Build every card keyed by a stable card_id (the customize layout + the
    # ck_cards_hidden cookie reference these ids). _CARD_ORDER below is the
    # canonical render order.
    built: Dict[str, str] = {}
    built["moic"] = _kpi_card(tag="Fund return", color="green", title="Weighted MOIC",
                              em="MOIC", value=moic_v, sub="equity-weighted",
                              span="cc-5x2", hero=True, idx=1)
    built["irr"] = _kpi_card(tag="Return", color="ink", title="Weighted IRR",
                             em="IRR", value=irr_v, sub="equity-weighted",
                             span="cc-4x1", idx=2)
    built["covenants"] = _kpi_card(tag="Risk", color="amber", title="Covenants at risk",
                                   em="risk", value=cov_v, sub=cov_sub,
                                   span="cc-3x1", idx=3)
    # Days cash has no rollup source → honest empty state (never fabricated).
    built["days_cash"] = _kpi_card(tag="Liquidity", color="ink", title="Days cash",
                                   em="cash", value=None, sub="", span="cc-4x1", idx=4)
    built["active_deals"] = _kpi_card(tag="Pipeline", color="ink", title="Active deals",
                                      em="deals", value=(str(dc) if dc else None),
                                      sub="tracked", span="cc-4x1", idx=5)
    # Initiatives tracked: no cross-fund rollup count → honest empty.
    built["initiatives"] = _kpi_card(tag="Operations", color="ink", title="Initiatives tracked",
                                     em="Initiatives", value=None, sub="", span="cc-4x1", idx=6)
    # Roster + funnel from real data.
    built["roster"] = _roster_card(deals_df, idx=7)
    built["funnel"] = _funnel_card(r, idx=8)

    # Heavier analytic cards — reuse the existing real renderers (data + empty
    # states intact) inside scrollable dossier cards. Full-width by design.
    def _embed(cid, tag, color, title, em, html, span, idx):
        built[cid] = _card(tag=tag, color=color, title=title, em=em,
                           body=html, span=span, scroll=True, idx=idx)

    _embed("morning_brief", "Morning brief", "amber", "Morning brief", "brief",
           render_morning_brief(r, deals_df), "cc-12x2", 9)
    _embed("quick_access", "Quick access", "ink", "Quick access", "access",
           render_quick_access(), "cc-12x3", 10)
    _embed("covenant_heatmap", "Watchlist", "amber", "Covenant heatmap", "heatmap",
           render_covenant_heatmap(store, focused_deal_id), "cc-7x3", 11)
    _embed("ebitda_drag", "Bridge", "ink", "EBITDA drag", "drag",
           render_ebitda_drag(focused_packet), "cc-5x3", 12)
    _embed("initiative_variance", "Operations", "ink", "Initiative variance", "variance",
           render_initiative_tracker(store, focused_deal_id), "cc-6x2", 13)
    _embed("alerts", "Alerts", "amber", "Active alerts", "alerts",
           render_alerts(store), "cc-6x2", 14)
    _embed("deliverables", "Deliverables", "navy", "Deliverables", "Deliverables",
           render_deliverables(store, deal_id=focused_deal_id), "cc-12x2", 15)

    # Visible cards in canonical order, minus any the viewer has hidden.
    visible = [built[cid] for cid, _ in _CARD_ORDER
               if cid in built and cid not in hidden]

    # Customize panel — toggle each card on/off (persisted via /app/cards).
    panel = _customize_panel(hidden) if customize else ""

    # Source registry footer — same labels the flat-scroll what-block shows,
    # so the page still declares where its numbers come from.
    sources = ["portfolio.db", "deal_snapshots", "covenant_metrics",
               "initiative_actuals", "analysis_runs", "generated_exports"]
    src_footer = (
        '<div class="cc-sources">'
        '<span class="cc-sources-k">Sources</span>'
        + " &middot; ".join(f'<code>{_esc(s)}</code>' for s in sources)
        + '</div>'
    )

    return (
        '<div class="cc-page" data-cc-grid>'
        + _page_top("/command-center", section_label=section_label,
                    kicker_label=kicker_label, lede=lede, customize=customize)
        + panel
        + '<div class="cc-grid">' + "".join(visible) + '</div>'
        + src_footer
        + '</div>'
    )
