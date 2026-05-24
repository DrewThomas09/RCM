"""Geographic portfolio map.

Route: GET /portfolio/map. Renders a real geographic US state map
(rcm_mc.ui.us_geo_map — vendored Albers-projected Census boundaries),
shading each state by the number of portfolio deals located there and
flagging Certificate-of-Need (CON) jurisdictions, inside the editorial
"investment dossier" layout from the Claude handoff
(~/Desktop/portfolio_map_redesign): a filter bar, a live 4-cell stats strip,
a click-to-select state detail panel, and a Top Exposures ranking.
Local/static — no external map tiles, APIs, or geocoding.

Honesty: every number is computed from real portfolio deals that carry a
state. With no such deals the page renders the handoff's empty states (the
map still draws, every state in the no-data shade). Sector / Revenue / Headcount
controls are shown for layout fidelity but disabled, because portfolio deals
carry no sector / revenue / headcount geography fields today — they are never
faked.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, List, Optional


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


_PM_CSS = """
.ck-pm-top{display:flex;justify-content:space-between;align-items:flex-start;
gap:24px;flex-wrap:wrap;}
.ck-pm-actions{display:flex;gap:10px;align-items:center;margin-top:6px;}
.ck-pm-btn{background:var(--sc-paper,#faf6ec);border:1px solid var(--sc-rule,#c9c1ac);
padding:8px 14px;font-family:var(--sc-mono);font-size:11px;letter-spacing:.08em;
text-transform:uppercase;color:var(--sc-text,#2a3a4a);cursor:pointer;border-radius:2px;
text-decoration:none;display:inline-flex;align-items:center;gap:6px;}
.ck-pm-btn.primary{background:var(--sc-navy,#15202b);color:var(--sc-paper,#faf6ec);
border-color:var(--sc-navy,#15202b);}
.ck-pm-btn.primary:hover{background:var(--sc-teal,#18573f);border-color:var(--sc-teal,#18573f);}
.ck-pm-btn[disabled],.ck-pm-btn[aria-disabled="true"]{opacity:.45;cursor:not-allowed;}
.ck-pm-explainer{font-family:var(--sc-serif);font-size:16px;line-height:1.55;
color:var(--sc-text-dim);max-width:74ch;margin:var(--sc-s-3) 0 var(--sc-s-5);}
.ck-pm-explainer em{color:var(--sc-teal-ink);font-style:italic;}
/* Filter bar */
.ck-pm-filters{display:flex;align-items:center;gap:14px;flex-wrap:wrap;
background:var(--sc-paper,#faf6ec);border:1px solid var(--sc-rule,#c9c1ac);
padding:12px 16px;margin-bottom:14px;}
.ck-pm-flab{font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;
text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);}
.ck-pm-seg{display:flex;border:1px solid var(--sc-rule,#c9c1ac);background:var(--sc-bone,#f3eddb);}
.ck-pm-seg button{background:transparent;border:0;border-right:1px solid var(--sc-rule,#c9c1ac);
padding:6px 12px;font-family:var(--sc-mono);font-size:11px;letter-spacing:.06em;
text-transform:uppercase;color:var(--sc-text-faint,#6a7480);cursor:pointer;}
.ck-pm-seg button:last-child{border-right:0;}
.ck-pm-seg button.on{background:var(--sc-navy,#15202b);color:var(--sc-paper,#faf6ec);}
.ck-pm-seg button[disabled]{opacity:.4;cursor:not-allowed;}
.ck-pm-toggle{display:inline-flex;align-items:center;gap:7px;cursor:pointer;
font-family:var(--sc-mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;
color:var(--sc-text,#2a3a4a);background:none;border:0;padding:0;}
.ck-pm-toggle .box{width:30px;height:16px;background:var(--sc-bone,#f3eddb);
border:1px solid var(--sc-rule,#c9c1ac);position:relative;border-radius:9px;transition:background .15s;}
.ck-pm-toggle .box::after{content:"";position:absolute;top:1px;left:1px;width:12px;height:12px;
background:var(--sc-text-faint,#8b94a0);border-radius:50%;transition:transform .15s,background .15s;}
.ck-pm-toggle.on .box{background:var(--sc-mint,#d6e8df);border-color:var(--sc-teal,#1f7a5a);}
.ck-pm-toggle.on .box::after{transform:translateX(14px);background:var(--sc-teal,#1f7a5a);}
.ck-pm-search{flex:1;min-width:180px;display:flex;align-items:center;gap:8px;
background:var(--sc-bone,#f3eddb);border:1px solid var(--sc-rule,#c9c1ac);padding:6px 12px;}
.ck-pm-search input{flex:1;background:transparent;border:0;outline:none;
font-family:var(--sc-serif);font-style:italic;font-size:14px;color:var(--sc-text);}
.ck-pm-divider{width:1px;align-self:stretch;background:var(--sc-rule,#c9c1ac);}
/* Stats strip */
.ck-pm-stats{display:grid;grid-template-columns:repeat(4,1fr);
background:var(--sc-paper,#faf6ec);border:1px solid var(--sc-rule,#c9c1ac);margin-bottom:18px;}
.ck-pm-stat{padding:14px 18px;border-right:1px solid var(--sc-rule,#c9c1ac);}
.ck-pm-stat:last-child{border-right:0;}
.ck-pm-stat .lab{font-family:var(--sc-mono);font-size:10px;letter-spacing:.12em;
text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);margin-bottom:6px;}
.ck-pm-stat .v{font-family:var(--sc-serif);font-size:30px;line-height:1;color:var(--sc-navy,#15202b);
font-variant-numeric:tabular-nums;}
.ck-pm-stat .v em{font-style:italic;color:var(--sc-teal,#1f7a5a);}
.ck-pm-stat .v.amber{color:var(--sc-warning,#b8842e);}
.ck-pm-stat .sub{font-family:var(--sc-mono);font-size:10.5px;color:var(--sc-text-dim,#6a7480);margin-top:6px;}
/* Layout: map + right rail */
.ck-pm-grid{display:grid;grid-template-columns:1fr 360px;gap:20px;align-items:start;}
@media (max-width:1100px){.ck-pm-grid{grid-template-columns:1fr;}}
.ck-pm-rail{display:flex;flex-direction:column;gap:16px;}
.ck-pm-card{background:var(--sc-paper,#faf6ec);border:1px solid var(--sc-rule,#c9c1ac);padding:18px;}
.ck-pm-card h3{font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;
text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);margin:0 0 12px;}
.ck-pm-detail-name{font-family:var(--sc-serif);font-size:28px;line-height:1.05;
color:var(--sc-navy,#15202b);margin:0 0 4px;}
.ck-pm-detail-sub{font-family:var(--sc-serif);font-style:italic;font-size:14px;
color:var(--sc-text-dim,#6a7480);margin:0 0 14px;}
.ck-pm-con-pill{display:inline-block;font-family:var(--sc-mono);font-size:9.5px;
letter-spacing:.1em;text-transform:uppercase;color:var(--sc-warning,#b8842e);
background:var(--sc-amber-soft,#f3e2bc);border:1px solid var(--sc-warning,#b8842e);
padding:2px 7px;margin-left:8px;vertical-align:middle;}
.ck-pm-kpis{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;}
.ck-pm-kpi .k{font-family:var(--sc-mono);font-size:9.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);}
.ck-pm-kpi .n{font-family:var(--sc-serif);font-size:22px;color:var(--sc-navy,#15202b);
font-variant-numeric:tabular-nums;}
.ck-pm-deal{display:flex;align-items:baseline;gap:8px;padding:8px 0;
border-top:1px dashed var(--sc-rule,#c9c1ac);font-family:var(--sc-serif);font-size:14px;}
.ck-pm-deal .dot{width:7px;height:7px;border-radius:50%;background:var(--sc-teal,#1f7a5a);
flex:none;align-self:center;}
.ck-pm-deal .stg{margin-left:auto;font-family:var(--sc-mono);font-size:9.5px;
letter-spacing:.08em;text-transform:uppercase;color:var(--sc-text-dim,#6a7480);
background:var(--sc-bone,#f3eddb);padding:2px 7px;}
.ck-pm-empty{font-family:var(--sc-serif);font-style:italic;font-size:14px;
color:var(--sc-text-dim,#6a7480);margin:6px 0 0;}
.ck-pm-note{background:var(--sc-bone,#f3eddb);padding:12px 14px;margin-top:14px;
font-family:var(--sc-serif);font-style:italic;font-size:13px;line-height:1.5;
color:var(--sc-text-dim,#6a7480);}
/* Top exposures */
.ck-pm-exp-row{display:grid;grid-template-columns:26px 1fr 64px 28px;align-items:center;
column-gap:10px;padding:9px 0;cursor:pointer;}
.ck-pm-exp-row + .ck-pm-exp-row{border-top:1px dashed var(--sc-rule,#c9c1ac);}
.ck-pm-exp-row:hover{background:var(--sc-bone,#f3eddb);}
.ck-pm-exp-row .rank{font-family:var(--sc-serif);font-style:italic;font-size:17px;
color:var(--sc-teal,#1f7a5a);}
.ck-pm-exp-row .lbl{font-family:var(--sc-serif);font-size:14px;color:var(--sc-navy,#15202b);}
.ck-pm-exp-row .lbl small{display:block;font-family:var(--sc-mono);font-size:9.5px;
letter-spacing:.04em;color:var(--sc-text-dim,#6a7480);margin-top:2px;}
.ck-pm-exp-row .bar{height:6px;background:var(--sc-bone,#f3eddb);border:1px solid var(--sc-rule,#c9c1ac);}
.ck-pm-exp-row .bar > span{display:block;height:100%;background:var(--sc-teal,#1f7a5a);}
.ck-pm-exp-row .n{font-family:var(--sc-mono);font-size:12px;color:var(--sc-navy,#15202b);text-align:right;}
"""


def render_portfolio_map(
    deals: List[Dict[str, Any]],
    *,
    con_states: Optional[Dict[str, bool]] = None,
) -> str:
    """Full-page HTML with the editorial dossier portfolio map (handoff)."""
    from ._chartis_kit import chartis_shell, ck_next_section, ck_page_title
    from .us_map import STATE_NAMES
    from .us_geo_map import render_us_geo_map

    # ── Real per-state aggregation (never fabricated) ───────────────────────
    state_counts: Dict[str, int] = {}
    state_deals: Dict[str, List[Dict[str, str]]] = {}
    for d in deals:
        st = str(d.get("state") or "").upper()
        if not st:
            continue
        state_counts[st] = state_counts.get(st, 0) + 1
        state_deals.setdefault(st, []).append({
            "name": str(d.get("name") or d.get("deal_id") or "Deal"),
            "stage": str(d.get("stage") or "—"),
        })

    con_set = {str(s).upper() for s, v in (con_states or {}).items() if v}
    notes = {st: "Certificate-of-Need (CON) jurisdiction" for st in con_set}
    n_states = len(state_counts)
    n_con = len(con_set)
    total_mapped = sum(state_counts.values())
    coverage_pct = round(100 * n_states / 51) if n_states else 0

    map_html = render_us_geo_map(
        {k: float(v) for k, v in state_counts.items()},
        metric_label="deals",
        state_notes=notes,
        accent_states=con_set,
        accent_label="Certificate-of-Need (CON) state",
        empty_message=(
            "No state-level portfolio data yet. When deals carry a state "
            "(or facility geography), this map shades each state by deal "
            "count and concentration across markets."
        ),
    )

    # ── Page top ────────────────────────────────────────────────────────────
    title_block = ck_page_title(
        "Portfolio Map", eyebrow="PORTFOLIO · /portfolio/map",
        meta=(f"{total_mapped} deals · {n_states} states · {n_con} CON "
              "jurisdictions" if deals else "no state geography yet"),
    )
    actions = (
        '<div class="ck-pm-actions">'
        '<button class="ck-pm-btn" type="button" aria-disabled="true" disabled '
        'title="Export of the current view — not wired yet">Export</button>'
        '<button class="ck-pm-btn" type="button" aria-disabled="true" disabled '
        'title="Pivot to a deal-major view — not wired yet">Pivot</button>'
        '<a class="ck-pm-btn primary" href="/pipeline" '
        'title="Start a new deal in the pipeline">+ Add deal</a>'
        '</div>'
    )
    explainer = (
        '<p class="ck-pm-explainer">'
        '<em>Where the portfolio sits, state by state.</em> '
        "Each state is drawn in its <em>real geographic shape</em> and shaded "
        "by how many portfolio deals sit there. States outlined in "
        "<em>amber</em> are Certificate-of-Need (CON) jurisdictions, where new "
        "market entry needs regulatory approval. Hover a state for detail; "
        "click to select it. Alaska and Hawaii appear as bottom-left insets — "
        "an Albers projection of US Census boundaries, not a coastline-precise "
        "or facility-location map."
        '</p>'
    )

    # ── Filter bar (Sector/View disabled honestly; CON + Search live) ───────
    filters = (
        '<div class="ck-pm-filters" data-pm-filters>'
        '<span class="ck-pm-flab">Sector</span>'
        '<div class="ck-pm-seg">'
        '<button type="button" class="on">All</button>'
        '<button type="button" disabled title="Portfolio deals carry no sector tag yet">ASC</button>'
        '<button type="button" disabled title="Portfolio deals carry no sector tag yet">Physician</button>'
        '<button type="button" disabled title="Portfolio deals carry no sector tag yet">Hospital</button>'
        '</div>'
        '<span class="ck-pm-divider"></span>'
        '<span class="ck-pm-flab">View</span>'
        '<div class="ck-pm-seg">'
        '<button type="button" class="on">Concentration</button>'
        '<button type="button" disabled title="No per-state revenue field on deals yet">Revenue</button>'
        '<button type="button" disabled title="No headcount field on deals yet">Headcount</button>'
        '</div>'
        '<span class="ck-pm-divider"></span>'
        '<button type="button" class="ck-pm-toggle" data-pm-con-toggle aria-pressed="false">'
        '<span class="box"></span>CON only</button>'
        '<div class="ck-pm-search">'
        '<input type="search" data-pm-search placeholder="Search states…" '
        'aria-label="Search states by name or code" />'
        '</div>'
        '</div>'
    )

    # ── Live stats strip ────────────────────────────────────────────────────
    def _stat(lab: str, val: str, sub: str, amber: bool = False) -> str:
        cls = "v amber" if amber else "v"
        return (f'<div class="ck-pm-stat"><div class="lab">{_esc(lab)}</div>'
                f'<div class="{cls}">{val}</div>'
                f'<div class="sub">{_esc(sub)}</div></div>')

    stats = (
        '<div class="ck-pm-stats">'
        + _stat("Deals mapped", f'<em>{total_mapped}</em>', "with state data")
        + _stat("States · presence", f'<em>{n_states}</em>/51',
                f"{coverage_pct}% national coverage")
        + _stat("Total concentration", f'{total_mapped}',
                "deal-state pairs")
        + _stat("CON states", f'{n_con}', "regulated entry", amber=True)
        + '</div>'
    )

    # ── Top exposures (real, top 6 by deal count) ───────────────────────────
    top = sorted(state_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    if top:
        max_c = top[0][1]
        rows = "".join(
            f'<div class="ck-pm-exp-row" data-pm-exp="{_esc(st)}" tabindex="0" role="button" '
            f'aria-label="Select {_esc(STATE_NAMES.get(st, st))}">'
            f'<span class="rank">{i+1:02d}.</span>'
            f'<span class="lbl">{_esc(STATE_NAMES.get(st, st))}'
            f'<small>{_esc(st)} · {"CON" if st in con_set else "non-CON"}</small></span>'
            f'<span class="bar"><span style="width:{round(100*c/max_c)}%"></span></span>'
            f'<span class="n">{c}</span></div>'
            for i, (st, c) in enumerate(top)
        )
        exposures = f'<div class="ck-pm-card"><h3>Top exposures</h3>{rows}</div>'
    else:
        exposures = ('<div class="ck-pm-card"><h3>Top exposures</h3>'
                     '<p class="ck-pm-empty">No exposure to rank yet.</p></div>')

    # Detail panel (server-rendered default; JS re-renders on select).
    detail = (
        '<div class="ck-pm-card" data-pm-detail>'
        '<h3>Selected state</h3>'
        '<p class="ck-pm-empty" data-pm-detail-body>'
        'Click a state on the map to see its portfolio detail.</p>'
        '</div>'
    )

    # Data for the JS detail panel — real per-state deals + CON flags only.
    pm_data = {
        "names": {st: STATE_NAMES.get(st, st)
                  for st in set(list(state_counts) + list(con_set))},
        "con": sorted(con_set),
        "counts": state_counts,
        "deals": state_deals,
    }
    data_json = json.dumps(pm_data, separators=(",", ":"))

    grid = (
        '<div class="ck-pm-grid">'
        f'<div class="ck-pm-map">{map_html}</div>'
        f'<div class="ck-pm-rail">{detail}{exposures}</div>'
        '</div>'
    )

    next_up = ck_next_section(
        "Open the portfolio heatmap", "/portfolio/heatmap",
        eyebrow="Continue —", italic_word="heatmap",
    )

    body = (
        '<div class="ck-pm-top"><div>' + title_block + '</div>' + actions + '</div>'
        + explainer + filters + stats + grid + next_up
        + f'<script type="application/json" data-pm-json>{data_json}</script>'
        + _PM_JS
    )
    return chartis_shell(body, "Portfolio Map", active_nav="/portfolio",
                         extra_css=_PM_CSS)


# Vanilla JS: CON-only dim, search dim, click-select → detail panel.
# Reads the real per-state data blob; never invents values.
_PM_JS = """
<script>(function(){
 var blob=document.querySelector('[data-pm-json]');
 if(!blob) return;
 var D={}; try{D=JSON.parse(blob.textContent||'{}');}catch(e){return;}
 var con=new Set(D.con||[]);
 var detail=document.querySelector('[data-pm-detail-body]');
 function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
 function render(st){
   if(!detail) return;
   var name=(D.names&&D.names[st])||st;
   var deals=(D.deals&&D.deals[st])||[];
   var isCon=con.has(st);
   var h='<div class="ck-pm-detail-name">'+esc(name)+
     (isCon?'<span class="ck-pm-con-pill">CON state</span>':'')+'</div>';
   h+='<div class="ck-pm-detail-sub">'+(deals.length?
     ('Holding '+deals.length+' active deal-state pair'+(deals.length===1?'':'s')+' here.'):
     'No portfolio presence in this state yet.')+'</div>';
   h+='<div class="ck-pm-kpis"><div class="ck-pm-kpi"><div class="k">Deal-state pairs</div>'+
     '<div class="n">'+deals.length+'</div></div>'+
     '<div class="ck-pm-kpi"><div class="k">CON jurisdiction</div>'+
     '<div class="n">'+(isCon?'Yes':'No')+'</div></div></div>';
   if(deals.length){
     deals.forEach(function(d){
       h+='<div class="ck-pm-deal"><span class="dot"></span>'+esc(d.name)+
          '<span class="stg">'+esc(d.stage)+'</span></div>';
     });
   } else {
     h+='<p class="ck-pm-empty">No deals with presence here.</p>';
   }
   if(isCon){
     h+='<div class="ck-pm-note">Certificate-of-Need jurisdiction — new market '+
        'entry or expansion requires state regulatory approval. Factor CON '+
        'timelines into any greenfield or de novo thesis here.</div>';
   }
   detail.outerHTML='<div class="ck-pm-detail-body-rendered" data-pm-detail-body>'+h+'</div>';
   detail=document.querySelector('[data-pm-detail-body]');
 }
 // Map emits us-map-select on cell click (see us_map.py).
 document.addEventListener('us-map-select',function(e){
   if(e.detail&&e.detail.state) render(e.detail.state.toUpperCase());
 });
 // Top-exposure rows select a state too.
 document.querySelectorAll('[data-pm-exp]').forEach(function(r){
   function go(){render(r.getAttribute('data-pm-exp'));}
   r.addEventListener('click',go);
   r.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();go();}});
 });
 // CON-only toggle + search: dim non-matching cells, preserve grid shape.
 var toggle=document.querySelector('[data-pm-con-toggle]');
 var search=document.querySelector('[data-pm-search]');
 function applyDim(){
   var conOnly=toggle&&toggle.getAttribute('aria-pressed')==='true';
   var q=(search&&search.value||'').trim().toUpperCase();
   document.querySelectorAll('.usgeo-state').forEach(function(c){
     var st=(c.getAttribute('data-state')||'').toUpperCase();
     var nm=((D.names&&D.names[st])||st).toUpperCase();
     var ok=true;
     if(conOnly && !con.has(st)) ok=false;
     if(q && st.indexOf(q)<0 && nm.indexOf(q)<0) ok=false;
     c.style.opacity = ok? '' : '0.22';
   });
 }
 if(toggle){toggle.addEventListener('click',function(){
   var on=toggle.getAttribute('aria-pressed')==='true';
   toggle.setAttribute('aria-pressed',(!on).toString());
   toggle.classList.toggle('on',!on);applyDim();});}
 if(search){search.addEventListener('input',applyDim);}
 // Segmented controls: visual active state only (single live option each).
 document.querySelectorAll('.ck-pm-seg').forEach(function(seg){
   seg.querySelectorAll('button:not([disabled])').forEach(function(b){
     b.addEventListener('click',function(){
       seg.querySelectorAll('button').forEach(function(o){o.classList.remove('on');});
       b.classList.add('on');});
   });
 });
})();</script>
"""
