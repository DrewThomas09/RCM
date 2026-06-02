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
  .cc-grid>*{grid-column:1/-1 !important;grid-row:auto !important;min-height:140px;}
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
              kicker_label: str = "FUND II", lede: str = "") -> str:
    # Mono eyebrow carries the two-view lexicon (section · kicker · slug) so
    # the dossier grid frames partner vs consulting identically to the flat
    # page. Section/kicker are rendered uppercase exactly as passed.
    eyebrow = (
        '<div class="cc-crumb">'
        f'{_esc(section_label)} <span class="cc-crumb-slug">&middot; '
        f'{_esc(kicker_label)} &middot; {_esc(crumb_slug)}</span></div>'
    )
    lede_html = f'<p class="cc-lede">{_esc(lede)}</p>' if lede else ''
    return (
        '<div class="cc-top">'
        + eyebrow
        + '<div class="cc-top-row">'
        '<h1 class="cc-h1">Command <span class="cc-h1-em">center</span>.</h1>'
        '<div class="cc-actions">'
        # No customize/add-card modes exist yet → safe disabled (honest);
        # Refresh is a real reload of the page's data.
        '<button type="button" class="cc-btn" disabled '
        'title="Customize coming soon">&#8862; Customize</button>'
        '<a class="cc-btn" href="/app" title="Reload data">&#8635; Refresh</a>'
        '<button type="button" class="cc-btn cc-btn-primary" disabled '
        'title="Add a card coming soon">+ Add card</button>'
        '</div>'
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
) -> str:
    """Render the dossier-card grid body (caller wraps it in the shell)."""
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

    cards: List[str] = []
    cards.append(_kpi_card(tag="Fund return", color="green", title="Weighted MOIC",
                           em="MOIC", value=moic_v, sub="equity-weighted",
                           span="cc-5x2", hero=True, idx=1))
    cards.append(_kpi_card(tag="Return", color="ink", title="Weighted IRR",
                           em="IRR", value=irr_v, sub="equity-weighted",
                           span="cc-4x1", idx=2))
    cards.append(_kpi_card(tag="Risk", color="amber", title="Covenants at risk",
                           em="risk", value=cov_v, sub=cov_sub,
                           span="cc-3x1", idx=3))
    # Days cash has no rollup source → honest empty state (never fabricated).
    cards.append(_kpi_card(tag="Liquidity", color="ink", title="Days cash",
                           em="cash", value=None, sub="", span="cc-4x1", idx=4))
    cards.append(_kpi_card(tag="Pipeline", color="ink", title="Active deals",
                           em="deals", value=(str(dc) if dc else None),
                           sub="tracked", span="cc-4x1", idx=5))
    # Initiatives tracked: no cross-fund rollup count → honest empty.
    cards.append(_kpi_card(tag="Operations", color="ink", title="Initiatives tracked",
                           em="Initiatives", value=None, sub="", span="cc-4x1", idx=6))

    # Roster + funnel from real data.
    cards.append(_roster_card(deals_df, idx=7))
    cards.append(_funnel_card(r, idx=8))

    # Heavier analytic cards — reuse the existing real renderers (data + empty
    # states intact) inside scrollable dossier cards. Full-width by design.
    def _embed(tag, color, title, em, html, span, idx):
        cards.append(_card(tag=tag, color=color, title=title, em=em,
                           body=html, span=span, scroll=True, idx=idx))

    _embed("Morning brief", "amber", "Morning brief", "brief",
           render_morning_brief(r, deals_df), "cc-12x2", 9)
    _embed("Quick access", "ink", "Quick access", "access",
           render_quick_access(), "cc-12x3", 10)
    _embed("Watchlist", "amber", "Covenant heatmap", "heatmap",
           render_covenant_heatmap(store, focused_deal_id), "cc-7x3", 11)
    _embed("Bridge", "ink", "EBITDA drag", "drag",
           render_ebitda_drag(focused_packet), "cc-5x3", 12)
    _embed("Operations", "ink", "Initiative variance", "variance",
           render_initiative_tracker(store, focused_deal_id), "cc-6x2", 13)
    _embed("Alerts", "amber", "Active alerts", "alerts",
           render_alerts(store), "cc-6x2", 14)
    _embed("Deliverables", "navy", "Deliverables", "Deliverables",
           render_deliverables(store, deal_id=focused_deal_id), "cc-12x2", 15)

    # + Add a card placeholders (visual only).
    addcards = "".join(
        '<button type="button" class="cc-addcard" disabled '
        'title="Add a card coming soon">&#65291; Add a card</button>'
        for _ in range(4)
    )

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
                    kicker_label=kicker_label, lede=lede)
        + '<div class="cc-grid">' + "".join(cards) + addcards + '</div>'
        + src_footer
        + '</div>'
    )
