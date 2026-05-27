"""Editorial card-grid Tools index (design handoff · Card Grid v2).

Renders BOTH views of every PEdesk surface as cards:

* **By workspace** — cards grouped under the workspace section bars
  (Home, Source, Pipeline, Diligence, Library, Research, Portfolio, Operations).
* **Full A–Z** — the same card component grouped into organizational buckets;
  this view is the completeness contract: EVERY discovered route renders as a
  card here (guarded by tests). No ghost pages.

This module is *pure presentation*. The caller (server `_route_tools_index`)
assembles the data from the live route registry — `_discover_all_routes()` +
the Cmd-K palette for titles + `classify_surface()` for status + the page-
context registry for descriptions — and hands it in. Nothing here invents a
tool, a status, or a description: a card with no real description simply omits
it, exactly like the handoff specifies.

Status buckets map the four honest surface tiers to the handoff's four:
green→live, navy→computed (calculator from your inputs), data_required→needs,
yellow/red→illustrative. The cool-plum "illustrative" stays visually distinct
from warm "needs data" so the two never blur together.
"""
from __future__ import annotations

import html as _html
import json as _json
from typing import Dict, List, Sequence

from ._chartis_kit import chartis_shell

# Tier (surface_status) → handoff status bucket. Kept here so the mapping is
# one obvious table, not scattered conditionals.
TIER_TO_STATUS = {
    "green": "live",
    "navy": "computed",
    "data_required": "needs",
    "yellow": "illustrative",
    "red": "illustrative",
}

# Disambiguation overrides for routes that share a title with a *different*
# page (not aliases — different renderers/data context). These name each by
# what it actually is so two cards never read identically. The canonical
# deal-workspace tool keeps the plain name; the standalone/public variant is
# qualified. Names taken from each page's own description — not invented.
TITLE_OVERRIDES = {
    "/diligence-checklist": "Checklist Dashboard",   # vs deal /diligence/checklist
    "/payer-stress": "Payer-Mix Stress",             # vs deal /diligence/payer-stress
    "/value-creation": "Value Creation Tracker",     # vs deal /diligence/value
}

_STATUS_LABEL = {
    "live": "Live", "computed": "Comp.", "needs": "Needs", "illustrative": "Illus.",
}
_STATUS_FULL = [
    ("live", "Live data"), ("computed", "Computed"),
    ("needs", "Needs data"), ("illustrative", "Illustrative"),
]


def _esc(x) -> str:
    return _html.escape(str(x if x is not None else ""), quote=True)


def _card(tool: Dict, *, show_section: str = "") -> str:
    """One tool card. ``tool`` = {name, path, status, desc, auto}.

    Carries data-* attributes (name/path/status) so the client-side search +
    status filter operate on the DOM without re-fetching, and data-route so the
    completeness tests can assert every route is present."""
    status = tool.get("status") or "live"
    name = tool.get("name") or tool.get("path") or ""
    path = tool.get("path") or ""
    desc = (tool.get("desc") or "").strip()
    auto = bool(tool.get("auto"))
    top = [
        f'<span class="ti-dot {_esc(status)}"></span>',
        f'<span>{_esc(_STATUS_LABEL.get(status, "Live"))}</span>',
    ]
    if auto:
        top.append('<span class="ti-auto">AUTO</span>')
    if show_section:
        top.append(f'<span class="ti-sect">{_esc(show_section)}</span>')
    desc_html = f'<p class="ti-desc">{_esc(desc)}</p>' if desc else ""
    # data-search packs name+path lowercased so the JS filter is a single
    # substring test; data-route is the completeness key.
    search_key = f"{name} {path}".lower()
    return (
        f'<a class="ti-card" href="{_esc(path)}" role="link" tabindex="0" '
        f'data-route="{_esc(path)}" data-status="{_esc(status)}" '
        f'data-search="{_esc(search_key)}">'
        '<span class="ti-arrow" aria-hidden="true">↗</span>'
        f'<span class="ti-top">{"".join(top)}</span>'
        f'<span class="ti-name">{_esc(name)}</span>'
        f'{desc_html}'
        f'<span class="ti-path">{_esc(path)}</span>'
        '</a>'
    )


def _section(sec: Dict, idx: int, *, dense: bool, show_section: bool) -> str:
    """A section bar + its card grid. ``sec`` = {id,label,blurb,route,tools}."""
    tools = sec.get("tools") or []
    label = sec.get("label") or sec.get("id") or ""
    # Headline: last word italic-green, like the section bars elsewhere.
    parts = label.split()
    if len(parts) > 1:
        head = (" ".join(_esc(w) for w in parts[:-1])
                + f' <em>{_esc(parts[-1])}</em>')
    else:
        head = f'<em>{_esc(label)}</em>'
    blurb = sec.get("blurb") or ""
    blurb_html = (f'<span class="ti-sec-blurb">{_esc(blurb)}</span>'
                  if blurb and not dense else "")
    route = sec.get("route") or ""
    open_html = (
        f'<a class="ti-open" href="{_esc(route)}">Open {_esc(label)} '
        '<span class="ti-open-arr">→</span></a>'
    ) if route else ""
    cards = "".join(_card(t, show_section=(label if show_section else ""))
                    for t in tools)
    return (
        f'<section class="ti-section" data-section="{_esc(sec.get("id", ""))}" '
        f'data-total="{len(tools)}">'
        '<div class="ti-sec-bar">'
        f'<div class="ti-sec-num">{idx:02d} / {_esc(label)}</div>'
        f'<div class="ti-sec-title"><h2>{head}</h2>{blurb_html}'
        f'<span class="ti-sec-meta"><b data-count>{len(tools)}</b> tools</span></div>'
        f'{open_html}'
        '</div>'
        f'<div class="ti-cards">{cards}</div>'
        '</section>'
    )


def _view(view_id: str, sections: Sequence[Dict], *, dense: bool,
          show_section: bool, hidden: bool) -> str:
    body = "".join(
        _section(s, i + 1, dense=dense, show_section=show_section)
        for i, s in enumerate(sections) if (s.get("tools"))
    )
    cls = "ti-main mode-index" if dense else "ti-main"
    hid = " hidden" if hidden else ""
    return (f'<div class="{cls}{hid}" data-view="{view_id}">{body}'
            '<div class="ti-empty hidden" data-empty>'
            '<h3>No tools match your filter</h3>'
            '<p>Try a shorter query, switch the status filter, or clear '
            'filters to see everything.</p></div></div>')


def render_tools_index(
    *,
    workspaces: List[Dict],
    index: List[Dict],
    total_ws: int,
    total_idx: int,
) -> str:
    """Assemble the full Tools page: sticky controls + masthead + legend +
    both views + footer. ``workspaces`` and ``index`` are lists of section
    dicts (see ``_section``)."""
    legend_chips = "".join(
        f'<button type="button" class="ti-chip" data-status-chip="{sid}" '
        f'aria-pressed="false">'
        f'<span class="ti-dot {sid}"></span>'
        f'<span><b>{_esc(label)}</b> · <span data-chip-count="{sid}">0</span></span>'
        '</button>'
        for sid, label in _STATUS_FULL
    )
    ws_view = _view("workspace", workspaces, dense=False,
                    show_section=False, hidden=False)
    idx_view = _view("index", index, dense=True,
                     show_section=True, hidden=True)
    body = (
        '<div class="ti-page" data-mode="workspace">'
        # ── sticky controls: search + view toggle ──
        '<div class="ti-controls">'
        '<div class="ti-controls-inner">'
        '<label class="ti-search">'
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" aria-hidden="true">'
        '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>'
        '<input type="search" placeholder="Search tools by name or route…" '
        'data-ti-search aria-label="Search tools" />'
        '<span class="ti-kbd">⌘K</span>'
        '<span class="ti-count"><b data-ti-visible>0</b> · '
        '<span data-ti-countlabel>tools</span></span>'
        '</label>'
        '<div class="ti-tabs" role="tablist">'
        '<button type="button" class="ti-tab on" data-view-btn="workspace" '
        'role="tab" aria-selected="true">By workspace</button>'
        '<button type="button" class="ti-tab" data-view-btn="index" '
        'role="tab" aria-selected="false">Full A–Z</button>'
        '</div>'
        '</div></div>'
        # ── masthead + legend ──
        '<header class="ti-mast">'
        '<div class="ti-mast-l">'
        '<div class="ti-eyebrow"><span class="ti-eyebrow-dot"></span>'
        '<span data-ti-eyebrow>Everything you can do</span></div>'
        '<h1 data-ti-headline>Every tool, <em>on one page</em>.</h1>'
        '<p class="ti-standfirst" data-ti-standfirst>Browse every PEdesk tool, '
        'grouped by workspace. Click any card to open it. Press <em>⌘K</em> to '
        'search the full set.</p>'
        '</div>'
        '<div class="ti-legend">'
        f'{legend_chips}'
        '<span class="ti-clear hidden" data-ti-clear>Clear filters →</span>'
        '</div>'
        '</header>'
        f'{ws_view}{idx_view}'
        # ── footer ──
        '<footer class="ti-foot">'
        f'<span data-ti-footcount>{total_ws} tools · {len([s for s in workspaces if s.get("tools")])} workspaces</span>'
        '<span class="ti-foot-cta" data-ti-foot-toggle>Full A–Z index →</span>'
        '</footer>'
        '</div>'
    )
    meta = _json.dumps({
        "totalWs": total_ws, "totalIdx": total_idx,
        "wsSections": len([s for s in workspaces if s.get("tools")]),
        "idxSections": len([s for s in index if s.get("tools")]),
    })
    return chartis_shell(
        body + f'<script>window.__TI_META__={meta};</script>' + _TOOLS_JS,
        "Tools", active_nav="/tools", extra_css=_TOOLS_CSS,
    )


# ───────────────────────────── styles ─────────────────────────────
_TOOLS_CSS = """
<style>
.ti-page{--ti-paper:#faf6ec;--ti-paper2:#f3eddb;--ti-ink:#15202b;
  --ti-ink2:#2a3a4a;--ti-muted:#6a7480;--ti-muted2:#8b94a0;--ti-rule:#c9c1ac;
  --ti-green:#1f7a5a;--ti-green2:#2e8c6c;--ti-green-deep:#18573f;
  --ti-green-soft:#d6e8df;--ti-amber:#b8842e;--ti-ochre:#7a4f6e;
  --ti-max:1320px;}
/* sticky controls (filter toolbar — contextual to this page, not global nav) */
.ti-controls{position:sticky;top:76px;z-index:20;background:var(--sc-bg,#ebe5d3);
  border-bottom:1px solid var(--ti-rule);margin:0 0 0;}
.ti-controls-inner{max-width:var(--ti-max);margin:0 auto;padding:12px 0;
  display:flex;gap:24px;align-items:center;justify-content:space-between;}
.ti-search{flex:1;max-width:520px;background:var(--ti-paper);
  border:1px solid var(--ti-rule);padding:8px 12px;display:flex;
  align-items:center;gap:10px;color:var(--ti-muted);}
.ti-search:focus-within{border-color:var(--ti-ink);}
.ti-search input{flex:1;border:0;outline:0;background:transparent;
  font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);font-style:italic;
  font-size:14.5px;color:var(--ti-ink);min-width:0;}
.ti-search input::placeholder{color:var(--ti-muted);}
.ti-kbd{font-family:var(--sc-mono,monospace);font-size:10.5px;
  color:var(--ti-muted);background:var(--ti-paper2);border:1px solid var(--ti-rule);
  padding:1px 6px;letter-spacing:.04em;}
.ti-count{font-family:var(--sc-mono,monospace);font-size:10px;
  color:var(--ti-muted2);letter-spacing:.1em;text-transform:uppercase;
  border-left:1px solid var(--ti-rule);padding-left:10px;white-space:nowrap;}
.ti-count b{color:var(--ti-green);font-weight:500;}
.ti-tabs{display:flex;flex-shrink:0;}
.ti-tab{background:transparent;border:1px solid var(--ti-rule);border-right:0;
  padding:8px 16px;font-family:var(--sc-mono,monospace);font-size:10.5px;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ti-muted);
  cursor:pointer;font-weight:500;}
.ti-tab:last-child{border-right:1px solid var(--ti-rule);}
.ti-tab.on{background:var(--ti-ink);color:var(--ti-paper);border-color:var(--ti-ink);}
.ti-tab:hover:not(.on){color:var(--ti-ink);background:var(--ti-paper);}
/* masthead */
.ti-mast{max-width:var(--ti-max);margin:0 auto;padding:40px 0 28px;
  display:grid;grid-template-columns:1.6fr 1fr;gap:56px;align-items:end;}
.ti-eyebrow{font-family:var(--sc-mono,monospace);font-size:10.5px;
  letter-spacing:.2em;text-transform:uppercase;color:var(--ti-green);
  margin-bottom:14px;display:flex;align-items:center;gap:10px;}
.ti-eyebrow-dot{width:5px;height:5px;border-radius:50%;background:var(--ti-green);}
.ti-mast h1{font-family:var(--sc-serif,Georgia,serif);font-weight:400;
  font-size:64px;line-height:.95;letter-spacing:-.03em;margin:0 0 14px;
  color:var(--ti-ink);}
.ti-mast h1 em{font-style:italic;color:var(--ti-green);}
.ti-standfirst{font-family:var(--sc-serif,Georgia,serif);font-size:16.5px;
  line-height:1.5;color:var(--ti-ink2);margin:0;max-width:52ch;}
.ti-standfirst em{font-style:italic;color:var(--ti-green-deep);}
/* legend = clickable status filter */
.ti-legend{background:var(--ti-paper);border:1px solid var(--ti-rule);
  padding:14px 16px;display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;}
.ti-chip{display:flex;align-items:center;gap:8px;padding:6px 12px 6px 10px;
  background:var(--ti-paper);border:1px solid var(--ti-rule);cursor:pointer;
  font-family:var(--sc-mono,monospace);font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ti-muted);transition:border-color .12s,
  background .12s,color .12s;}
.ti-chip b{color:var(--ti-ink);font-weight:500;}
.ti-chip:hover{border-color:var(--ti-ink);color:var(--ti-ink);}
.ti-chip.on{border-color:var(--ti-ink);background:var(--ti-ink);color:var(--ti-paper);}
.ti-chip.on b{color:var(--ti-paper);}
.ti-clear{font-family:var(--sc-mono,monospace);font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ti-green);cursor:pointer;padding:6px 4px;
  margin-left:auto;}
.ti-clear:hover{color:var(--ti-green-deep);}
/* sections */
.ti-main{max-width:var(--ti-max);margin:0 auto;}
.ti-section{padding:28px 0 0;}
.ti-section.hidden{display:none;}
.ti-sec-bar{display:grid;grid-template-columns:auto 1fr auto;align-items:center;
  gap:24px;padding:16px 20px;background:var(--ti-paper);border:1px solid var(--ti-rule);
  margin-bottom:14px;}
.ti-sec-num{font-family:var(--sc-mono,monospace);font-size:11px;letter-spacing:.18em;
  text-transform:uppercase;color:var(--ti-green);font-weight:500;padding-right:16px;
  border-right:1px solid var(--ti-rule);white-space:nowrap;}
.ti-sec-title{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;min-width:0;}
.ti-sec-title h2{font-family:var(--sc-serif,Georgia,serif);font-weight:400;
  font-size:26px;line-height:1;letter-spacing:-.018em;margin:0;color:var(--ti-ink);}
.ti-sec-title h2 em{font-style:italic;color:var(--ti-green);}
.ti-sec-blurb{font-family:var(--sc-serif,Georgia,serif);font-style:italic;
  font-size:14px;color:var(--ti-muted);line-height:1.4;}
.ti-sec-meta{font-family:var(--sc-mono,monospace);font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ti-muted);padding:4px 10px;
  border:1px solid var(--ti-rule);white-space:nowrap;}
.ti-sec-meta b{color:var(--ti-green);font-weight:500;}
.ti-open{font-family:var(--sc-mono,monospace);font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ti-ink);text-decoration:none;
  display:inline-flex;align-items:center;gap:8px;padding:7px 12px;
  border:1px solid var(--ti-ink);background:var(--ti-paper);white-space:nowrap;}
.ti-open:hover{background:var(--ti-ink);color:var(--ti-paper);}
.ti-open-arr{font-family:var(--sc-serif,Georgia,serif);font-style:italic;font-size:13px;}
/* card grid */
.ti-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;}
.mode-index .ti-cards{grid-template-columns:repeat(6,minmax(0,1fr));}
.ti-card{background:var(--ti-paper);border:1px solid var(--ti-rule);
  padding:14px 14px 12px;min-height:96px;display:flex;flex-direction:column;
  gap:8px;cursor:pointer;text-decoration:none;position:relative;min-width:0;
  transition:border-color .12s,transform .12s,box-shadow .12s;}
.ti-card.hidden{display:none;}
.ti-card:hover{border-color:var(--ti-ink);transform:translateY(-2px);
  box-shadow:0 8px 24px -12px rgba(13,35,54,.18);}
.ti-card:focus-visible{outline:2px solid var(--ti-green);outline-offset:2px;}
.ti-top{display:flex;align-items:center;gap:8px;font-family:var(--sc-mono,monospace);
  font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--ti-muted);
  min-width:0;}
.ti-sect{margin-left:auto;color:var(--ti-muted2);font-size:9px;letter-spacing:.1em;
  padding-left:8px;border-left:1px solid var(--ti-rule);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;max-width:45%;}
.ti-auto{padding:1px 5px;border:1px solid var(--ti-rule);background:var(--ti-paper2);
  font-size:8.5px;}
.ti-arrow{position:absolute;top:12px;right:12px;color:var(--ti-green);
  font-family:var(--sc-serif,Georgia,serif);font-size:16px;line-height:1;opacity:0;
  transform:translateX(-4px);transition:opacity .15s,transform .15s;
  pointer-events:none;}
.ti-card:hover .ti-arrow{opacity:1;transform:translateX(0);}
.ti-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;display:inline-block;}
.ti-dot.live{background:var(--ti-green);}
.ti-dot.computed{background:var(--ti-green2);}
.ti-dot.needs{background:var(--ti-amber);}
.ti-dot.illustrative{background:var(--ti-ochre);}
.ti-name{font-family:var(--sc-serif,Georgia,serif);font-size:17px;line-height:1.15;
  letter-spacing:-.005em;color:var(--ti-ink);word-wrap:break-word;overflow-wrap:anywhere;}
.ti-card:hover .ti-name{color:var(--ti-green);}
.ti-name mark{background:var(--ti-green-soft);color:var(--ti-green-deep);padding:0 1px;}
.ti-desc{font-family:var(--sc-serif,Georgia,serif);font-style:italic;font-size:12.5px;
  line-height:1.4;color:var(--ti-muted);margin:0;flex:1;overflow-wrap:anywhere;}
.ti-path{font-family:var(--sc-mono,monospace);font-size:9.5px;color:var(--ti-muted2);
  letter-spacing:.02em;border-top:1px dashed var(--ti-rule);padding-top:8px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.ti-card:hover .ti-path{color:var(--ti-ink2);}
.mode-index .ti-card{min-height:76px;padding:10px 11px;gap:6px;}
.mode-index .ti-card .ti-name{font-size:14px;}
.mode-index .ti-card .ti-desc{display:none;}
.mode-index .ti-card .ti-path{padding-top:6px;font-size:9px;}
/* empty + footer */
.ti-empty{padding:72px 0;text-align:center;}
.ti-empty.hidden{display:none;}
.ti-empty h3{font-family:var(--sc-serif,Georgia,serif);font-weight:400;font-size:28px;
  letter-spacing:-.015em;color:var(--ti-ink);margin:0 0 8px;}
.ti-empty p{font-family:var(--sc-serif,Georgia,serif);font-style:italic;font-size:15px;
  color:var(--ti-muted);margin:0;}
.ti-foot{max-width:var(--ti-max);margin:48px auto 0;padding:24px 0 8px;
  border-top:1px solid var(--ti-rule);display:flex;justify-content:space-between;
  align-items:center;font-family:var(--sc-mono,monospace);font-size:10.5px;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ti-muted);}
.ti-foot-cta{color:var(--ti-green);cursor:pointer;}
.ti-foot-cta:hover{color:var(--ti-green-deep);}
@media (max-width:1180px){
  .ti-cards{grid-template-columns:repeat(3,minmax(0,1fr));}
  .mode-index .ti-cards{grid-template-columns:repeat(4,minmax(0,1fr));}
  .ti-mast{grid-template-columns:1fr;gap:28px;}
  .ti-mast h1{font-size:48px;}
  .ti-sec-bar{grid-template-columns:1fr;gap:10px;}
}
@media (max-width:720px){
  .ti-cards,.mode-index .ti-cards{grid-template-columns:1fr 1fr;}
  .ti-controls-inner{flex-direction:column;align-items:stretch;gap:12px;}
  .ti-search{max-width:none;}
}
@media (prefers-reduced-motion:reduce){
  .ti-card:hover{transform:none;}
  .ti-arrow{transition:none;}
}
</style>
"""

# Vanilla-JS controller: search (name+route substring), status-chip filter,
# view toggle, ⌘K focus, Esc clear, per-section hide-when-empty, live counts,
# and <mark> match highlighting. No framework; operates on the data-* attrs.
_TOOLS_JS = """
<script>
(function(){
  var page=document.querySelector('.ti-page'); if(!page) return;
  var META=window.__TI_META__||{};
  var search=page.querySelector('[data-ti-search]');
  var visEl=page.querySelector('[data-ti-visible]');
  var countLabel=page.querySelector('[data-ti-countlabel]');
  var clearEl=page.querySelector('[data-ti-clear]');
  var footCount=page.querySelector('[data-ti-footcount]');
  var headline=page.querySelector('[data-ti-headline]');
  var eyebrow=page.querySelector('[data-ti-eyebrow]');
  var standfirst=page.querySelector('[data-ti-standfirst]');
  var footToggle=page.querySelector('[data-ti-foot-toggle]');
  var mode='workspace', q='', statusFilter=null;

  function mains(){return page.querySelectorAll('.ti-main');}
  function activeMain(){return page.querySelector('.ti-main[data-view="'+mode+'"]');}
  function esc(s){return s.replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});}

  function applyHighlight(card){
    var nameEl=card.querySelector('.ti-name');
    if(!nameEl) return;
    var raw=nameEl.getAttribute('data-raw')||nameEl.textContent;
    nameEl.setAttribute('data-raw',raw);
    if(!q){ nameEl.textContent=raw; return; }
    var i=raw.toLowerCase().indexOf(q);
    if(i<0){ nameEl.textContent=raw; return; }
    nameEl.innerHTML=esc(raw.slice(0,i))+'<mark>'+esc(raw.slice(i,i+q.length))
      +'</mark>'+esc(raw.slice(i+q.length));
  }

  function refresh(){
    var main=activeMain(); if(!main) return;
    var visible=0;
    var chipCounts={live:0,computed:0,needs:0,illustrative:0};
    main.querySelectorAll('.ti-section').forEach(function(sec){
      var shown=0;
      sec.querySelectorAll('.ti-card').forEach(function(card){
        var st=card.getAttribute('data-status');
        chipCounts[st]=(chipCounts[st]||0); // ensure key
      });
      sec.querySelectorAll('.ti-card').forEach(function(card){
        var hay=card.getAttribute('data-search')||'';
        var st=card.getAttribute('data-status');
        var ok=(!statusFilter||st===statusFilter)&&(!q||hay.indexOf(q)>=0);
        card.classList.toggle('hidden',!ok);
        if(ok){ shown++; visible++; applyHighlight(card); }
      });
      var cnt=sec.querySelector('[data-count]');
      var total=sec.getAttribute('data-total');
      if(cnt) cnt.textContent=(q||statusFilter)?(shown+' / '+total):total;
      sec.classList.toggle('hidden',(q||statusFilter)&&shown===0);
    });
    // chip counts = totals for this view (not filtered), computed once per view
    main.querySelectorAll('.ti-card').forEach(function(card){
      var st=card.getAttribute('data-status');
      if(chipCounts[st]!==undefined) chipCounts[st]++;
    });
    Object.keys(chipCounts).forEach(function(k){
      var el=page.querySelector('[data-chip-count="'+k+'"]');
      if(el) el.textContent=chipCounts[k];
    });
    if(visEl) visEl.textContent=visible;
    if(countLabel) countLabel.textContent=(q||statusFilter)?'matched':'tools';
    var filterActive=!!q||!!statusFilter;
    if(clearEl) clearEl.classList.toggle('hidden',!filterActive);
    var emptyEl=main.querySelector('[data-empty]');
    if(emptyEl) emptyEl.classList.toggle('hidden',visible>0);
    if(footCount){
      var tot=(mode==='workspace')?META.totalWs:META.totalIdx;
      var secs=(mode==='workspace')?META.wsSections:META.idxSections;
      footCount.textContent=filterActive?(visible+' of '+tot+' tools shown')
        :(tot+' tools · '+secs+(mode==='workspace'?' workspaces':' buckets'));
    }
  }

  function setMode(m){
    if(m===mode) return;
    mode=m; q=''; statusFilter=null;
    if(search) search.value='';
    mains().forEach(function(el){el.classList.toggle('hidden',el.getAttribute('data-view')!==m);});
    page.querySelectorAll('[data-view-btn]').forEach(function(b){
      var on=b.getAttribute('data-view-btn')===m;
      b.classList.toggle('on',on); b.setAttribute('aria-selected',on?'true':'false');
    });
    page.querySelectorAll('[data-status-chip]').forEach(function(c){
      c.classList.remove('on'); c.setAttribute('aria-pressed','false');});
    if(m==='index'){
      if(eyebrow) eyebrow.textContent='Platform index';
      if(headline) headline.innerHTML='Tools — <em>full A–Z</em>.';
      if(standfirst) standfirst.innerHTML='Every surface in the product, grouped into buckets. Every route is reachable from here.';
      if(footToggle) footToggle.textContent='← Back to grouped view';
    }else{
      if(eyebrow) eyebrow.textContent='Everything you can do';
      if(headline) headline.innerHTML='Every tool, <em>on one page</em>.';
      if(standfirst) standfirst.innerHTML='Browse every PEdesk tool, grouped by workspace. Click any card to open it. Press <em>⌘K</em> to search the full set.';
      if(footToggle) footToggle.textContent='Full A–Z index →';
    }
    refresh();
  }

  if(search){
    search.addEventListener('input',function(){q=search.value.trim().toLowerCase();refresh();});
  }
  page.querySelectorAll('[data-view-btn]').forEach(function(b){
    b.addEventListener('click',function(){setMode(b.getAttribute('data-view-btn'));});
  });
  page.querySelectorAll('[data-status-chip]').forEach(function(c){
    c.addEventListener('click',function(){
      var s=c.getAttribute('data-status-chip');
      statusFilter=(statusFilter===s)?null:s;
      page.querySelectorAll('[data-status-chip]').forEach(function(x){
        var on=x.getAttribute('data-status-chip')===statusFilter;
        x.classList.toggle('on',on); x.setAttribute('aria-pressed',on?'true':'false');
      });
      refresh();
    });
  });
  if(clearEl) clearEl.addEventListener('click',function(){
    q='';statusFilter=null;if(search)search.value='';
    page.querySelectorAll('[data-status-chip]').forEach(function(x){
      x.classList.remove('on');x.setAttribute('aria-pressed','false');});
    refresh();
  });
  if(footToggle) footToggle.addEventListener('click',function(){
    setMode(mode==='workspace'?'index':'workspace');
    window.scrollTo({top:0,behavior:'smooth'});
  });
  window.addEventListener('keydown',function(e){
    if((e.metaKey||e.ctrlKey)&&(e.key==='k'||e.key==='K')){
      e.preventDefault(); if(search){search.focus();search.select();}
    }
    if(e.key==='Escape'&&document.activeElement===search){
      q='';search.value='';refresh();search.blur();
    }
  });
  refresh();
})();
</script>
"""
