"""Tools — the curated default view of /tools.

Shows everything PE Desk can do, grouped by workspace, each group ordered
best-first by the surface ranking. The ranking is used only to *order* the
list — no scores, no "scored by usefulness" methodology, no hero/"#1" framing.
The point is an intuitive catalogue (like the Diligence index, but across every
workspace), not a leaderboard. The exhaustive raw route index lives behind
``/tools?view=all``.

Honesty dots stay (LIVE / computed / illustrative) so a partner can see at a
glance what's real — that's labelling, not a ranking.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List

# Workspaces in deal order; diligence first (the heart of the product). Only
# sections that have a /best/<section> index.
_WORKSPACES = [
    ("diligence", "Diligence"),
    ("source", "Source"),
    ("pipeline", "Pipeline"),
    ("portfolio", "Portfolio"),
    ("research", "Research"),
    ("library", "Library"),
]
_TIER_DOT = {
    "green": ("#0a8a5f", "Live data"),
    "navy": ("#15324f", "Computed"),
    "data_required": ("#b8732a", "Needs data"),
    "yellow": ("#c9a227", "Illustrative"),
    "red": ("#b5321e", "Placeholder"),
}

_CSS = """
.tx-intro{font-family:var(--sc-serif);font-size:15px;line-height:1.55;
 color:var(--sc-text-dim,#465366);max-width:70ch;margin:6px 0 4px;}
.tx-legend{display:flex;flex-wrap:wrap;gap:14px;margin:10px 0 20px;
 font-family:var(--sc-mono);font-size:10.5px;color:var(--sc-text-dim,#465366);}
.tx-legend span{display:inline-flex;align-items:center;gap:5px;}
.tx-dot{width:8px;height:8px;border-radius:50%;display:inline-block;}
.tx-sec{margin:0 0 26px;}
.tx-sec-head{display:flex;align-items:baseline;justify-content:space-between;
 gap:12px;border-bottom:2px solid var(--sc-rule,#c9c1ac);padding:0 2px 7px;
 margin-bottom:2px;}
.tx-sec-head h2{font-family:var(--sc-serif);font-weight:500;font-size:21px;
 color:var(--sc-navy,#0b2341);margin:0;letter-spacing:-0.01em;}
.tx-sec-more{font-family:var(--sc-mono);font-size:11px;color:var(--sc-teal,#155752);
 text-decoration:none;letter-spacing:.03em;}
.tx-row{display:flex;align-items:baseline;gap:11px;padding:9px 6px;
 border-bottom:1px solid var(--sc-rule,#e4ddcd);text-decoration:none;
 font-family:var(--sc-sans);font-size:13.5px;color:var(--sc-text,#1a2332);}
.tx-row:hover{background:var(--sc-bone,#ece5d6);}
.tx-row .tx-dot{flex:none;align-self:center;}
.tx-row-label{font-weight:600;color:var(--sc-navy,#0b2341);}
.tx-row-route{margin-left:auto;font-family:var(--sc-mono);font-size:10.5px;
 color:var(--sc-text-faint,#8b94a0);}
.tx-allbar{margin:8px 0 0;padding:13px 16px;background:var(--sc-parchment-2,#efe9dd);
 border:1px solid var(--sc-rule,#d6cfc0);border-radius:3px;display:flex;
 align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;
 font-family:var(--sc-sans);font-size:13px;color:var(--sc-text-dim,#465366);}
.tx-allbar a{font-family:var(--sc-mono);font-size:12px;color:var(--sc-teal,#155752);
 text-decoration:none;font-weight:600;}
.tx-filter{width:100%;max-width:430px;padding:9px 13px;margin:2px 0 4px;
 border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;font-size:13.5px;
 font-family:var(--sc-sans);background:#fff;color:var(--sc-text,#1a2332);}
.tx-filter:focus{outline:2px solid var(--sc-teal,#155752);outline-offset:-1px;}
.tx-filter-count{font-family:var(--sc-mono);font-size:11px;
 color:var(--sc-text-dim,#465366);min-height:16px;margin:0 0 6px;}
"""


def _ranked() -> Dict[str, List[Dict]]:
    try:
        from ._surface_rankings import RANKINGS
        return RANKINGS
    except Exception:  # noqa: BLE001
        return {}


def _row(r: Dict) -> str:
    color, tip = _TIER_DOT.get(r.get("tier", ""), ("#8b94a0", ""))
    # data-tx-search powers the instant filter — label + route, lowercased,
    # one attribute → cheap selector lookup in the JS handler (same pattern
    # as the screener's data-ts-search).
    blob = f'{r.get("label", "")} {r["route"]}'.lower()
    return (
        f'<a class="tx-row" href="{_html.escape(r["route"])}" '
        f'data-tx-search="{_html.escape(blob, quote=True)}">'
        f'<span class="tx-dot" style="background:{color}" title="{_html.escape(tip)}">'
        f'</span>'
        f'<span class="tx-row-label">{_html.escape(r.get("label",""))}</span>'
        f'<span class="tx-row-route">{_html.escape(r["route"])}</span></a>'
    )


def _section(key: str, label: str, rows: List[Dict],
             seen_labels: "set | None" = None) -> str:
    # Ranked order (best-first), but the score itself is never shown.
    # curate_rows drops internal routes, sentinel "All X →" rows, and
    # alias duplicates — a partner-facing catalog shows each real
    # destination exactly once (see _surface_visibility).
    from ._surface_visibility import curate_rows
    rows = curate_rows(sorted(rows, key=lambda r: -r.get("total", 0.0)))
    if seen_labels is not None:
        # Global de-dup across workspaces: curate_rows only de-dups WITHIN a
        # section, but a destination can live in two (e.g. "Benchmarks" in
        # both Diligence and Library; "Exit Timing" once Wave 2 surfaced the
        # bare /exit-timing alongside /diligence/exit-timing). Carry a shared
        # label set so the first workspace to show a label keeps it — the
        # _WORKSPACES order puts the canonical/flagship section first.
        kept = []
        for r in rows:
            lab = str(r.get("label", "")).strip().lower()
            if lab and lab in seen_labels:
                continue
            if lab:
                seen_labels.add(lab)
            kept.append(r)
        rows = kept
    if not rows:
        return ""  # emptied by global de-dup — don't render a bare header
    body = "".join(_row(r) for r in rows)
    return (
        f'<section class="tx-sec"><div class="tx-sec-head">'
        f'<h2>{_html.escape(label)}</h2>'
        f'<a class="tx-sec-more" href="/best/{key}">open {label.lower()} &rarr;</a>'
        f'</div>{body}</section>'
    )


def render_tools_showcase(total_surfaces: int = 0) -> str:
    from ._chartis_kit import chartis_shell, ck_page_title

    ranks = _ranked()
    head = ck_page_title(
        "Tools",
        eyebrow="EVERYTHING YOU CAN DO",
        meta="grouped by workspace · press Cmd+K to jump to any one",
    )
    intro = (
        '<p class="tx-intro">Every tool, grouped by workspace and ordered '
        'best-first. Open any one — or press Cmd+K to search them all.</p>'
    )
    # Instant filter — 170+ tools is too many to scan ("a lot of good
    # stuff in there but it is hard to get it out"). Type to narrow by
    # name or route; sections with zero matches collapse; Esc clears.
    filter_box = (
        '<input type="search" id="tx-filter" class="tx-filter" '
        'placeholder="Filter tools… (name or route)" autocomplete="off" '
        'aria-label="Filter tools"/>'
        '<div id="tx-filter-count" class="tx-filter-count"></div>'
        '<script>(function(){'
        "var inp=document.getElementById('tx-filter');if(!inp)return;"
        "var cnt=document.getElementById('tx-filter-count');"
        "inp.addEventListener('input',function(){"
        "var q=inp.value.trim().toLowerCase();var n=0;"
        "document.querySelectorAll('[data-tx-search]').forEach(function(a){"
        "var hit=!q||a.getAttribute('data-tx-search').indexOf(q)!==-1;"
        "a.style.display=hit?'':'none';if(hit)n++;});"
        "document.querySelectorAll('.tx-sec').forEach(function(s){"
        "var any=Array.prototype.some.call("
        "s.querySelectorAll('[data-tx-search]'),"
        "function(a){return a.style.display!=='none';});"
        "s.style.display=any?'':'none';});"
        "cnt.textContent=q?(n+' tool'+(n===1?'':'s')+' match'):'';});"
        "inp.addEventListener('keydown',function(e){"
        "if(e.key==='Escape'){inp.value='';"
        "inp.dispatchEvent(new Event('input'));}});"
        '})();</script>'
    )
    legend = (
        '<div class="tx-legend">'
        + "".join(
            f'<span><span class="tx-dot" style="background:{c}"></span>{_html.escape(t)}</span>'
            for c, t in [("#0a8a5f", "Live data"), ("#15324f", "Computed"),
                         ("#b8732a", "Needs data"), ("#c9a227", "Illustrative")])
        + '</div>'
    )

    sections = []
    seen_labels: set = set()
    for key, label in _WORKSPACES:
        rows = ranks.get(key, [])
        if rows:
            sec = _section(key, label, rows, seen_labels)
            if sec:
                sections.append(sec)

    all_bar = (
        '<div class="tx-allbar"><span>Looking for an admin page or a rarely-used '
        f'route? The full index lists all {total_surfaces} surfaces.</span>'
        '<a href="/tools?view=all">Full A–Z index &rarr;</a></div>'
    )

    body = head + intro + filter_box + legend + "".join(sections) + all_bar
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Tools", active_nav="/tools", extra_css=_CSS)
