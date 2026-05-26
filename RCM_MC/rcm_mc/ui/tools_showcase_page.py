"""Tools showcase — the curated default view of /tools.

The full /tools index lists every one of ~355 routes, which overwhelms a
partner who just wants the best surface for the job. This view leads instead
with the *best of the platform* (the top-6 ranked surfaces), spotlights the
top diligence layers, and gives a compact per-workspace strip — each linking
to its ranked ``/best/<section>`` index. The exhaustive flat index moves to a
secondary tab (``/tools?view=all``) so nothing is lost but nothing crowds.

Ranking source is ``_surface_rankings.RANKINGS`` (scripts/rank_surfaces.py).
Only front-facing tiers (green/navy/data-required) appear here — illustrative
and placeholder surfaces stay in the full index, not the showcase.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List

_GATE = {"green", "navy", "data_required"}
_TIER_DOT = {
    "green": ("#0a8a5f", "LIVE"),
    "navy": ("#15324f", "Computed"),
    "data_required": ("#b8732a", "Data needed"),
}
# Workspaces in the order a deal actually moves; diligence first (the heart of
# the product). Only sections that have a /best/<section> index.
_WORKSPACES = [
    ("diligence", "Diligence"),
    ("source", "Source"),
    ("pipeline", "Pipeline"),
    ("portfolio", "Portfolio"),
    ("research", "Research"),
    ("library", "Library"),
]

_CSS = """
.tsh-hero{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0 6px;}
@media (max-width:900px){.tsh-hero{grid-template-columns:1fr;}}
.tsh-card{display:flex;flex-direction:column;gap:6px;background:var(--sc-paper,#faf6ec);
 border:1px solid var(--sc-rule,#c9c1ac);border-left:3px solid var(--sc-teal,#155752);
 padding:13px 15px;text-decoration:none;}
.tsh-card:hover{box-shadow:var(--sc-shadow-2,0 8px 24px rgba(11,32,55,.14));}
.tsh-meta{display:flex;align-items:center;gap:7px;font-family:var(--sc-mono);font-size:10px;
 letter-spacing:.04em;color:var(--sc-text-dim,#6a7480);}
.tsh-rank{font-family:var(--sc-serif);font-style:italic;font-size:17px;color:var(--sc-teal,#155752);}
.tsh-dot{width:9px;height:9px;border-radius:50%;display:inline-block;}
.tsh-score{margin-left:auto;font-weight:600;color:var(--sc-navy,#15202b);}
.tsh-label{font-family:var(--sc-serif);font-size:16px;color:var(--sc-navy,#15202b);line-height:1.15;}
.tsh-route{font-family:var(--sc-mono);font-size:10px;color:var(--sc-text-faint,#8b94a0);}
.tsh-sec{font-family:var(--sc-mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;
 color:var(--sc-text-faint,#8b94a0);}
.tsh-strip{margin:8px 0 0;border-top:1px solid var(--sc-rule,#d6cfc0);}
.tsh-strip-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;
 padding:12px 2px 6px;}
.tsh-strip-head h3{font-family:var(--sc-serif);font-weight:500;font-size:17px;
 color:var(--sc-navy,#0b2341);margin:0;}
.tsh-strip-more{font-family:var(--sc-mono);font-size:11px;color:var(--sc-teal,#155752);
 text-decoration:none;letter-spacing:.03em;}
.tsh-row{display:flex;align-items:baseline;gap:10px;padding:7px 2px;
 border-bottom:1px solid var(--sc-rule,#e4ddcd);text-decoration:none;
 font-family:var(--sc-sans);font-size:13px;color:var(--sc-text,#1a2332);}
.tsh-row:hover{background:var(--sc-bone,#ece5d6);}
.tsh-row .tsh-dot{flex:none;}
.tsh-row-label{font-weight:600;color:var(--sc-navy,#0b2341);}
.tsh-row-route{margin-left:auto;font-family:var(--sc-mono);font-size:10px;
 color:var(--sc-text-faint,#8b94a0);}
.tsh-allbar{margin:22px 0 0;padding:14px 16px;background:var(--sc-parchment-2,#efe9dd);
 border:1px solid var(--sc-rule,#d6cfc0);border-radius:3px;display:flex;
 align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;}
.tsh-allbar a{font-family:var(--sc-mono);font-size:12px;color:var(--sc-teal,#155752);
 text-decoration:none;font-weight:600;}
"""


def _ranked() -> Dict[str, List[Dict]]:
    try:
        from ._surface_rankings import RANKINGS
        return RANKINGS
    except Exception:  # noqa: BLE001
        return {}


def _gated_sorted(rows: List[Dict]) -> List[Dict]:
    return sorted((r for r in rows if r.get("tier") in _GATE),
                  key=lambda r: -r.get("total", 0.0))


def _hero_card(rank: int, r: Dict, section: str) -> str:
    color, tlabel = _TIER_DOT.get(r.get("tier", ""), ("#8b94a0", "—"))
    return (
        f'<a class="tsh-card" href="{_html.escape(r["route"])}">'
        f'<div class="tsh-meta"><span class="tsh-rank">{rank:02d}</span>'
        f'<span class="tsh-dot" style="background:{color}"></span>'
        f'<span>{_html.escape(tlabel)}</span>'
        f'<span class="tsh-score">{r.get("total",0):.1f}/10</span></div>'
        f'<div class="tsh-label">{_html.escape(r.get("label",""))}</div>'
        f'<div class="tsh-sec">{_html.escape(section)}</div>'
        f'<div class="tsh-route">{_html.escape(r["route"])}</div></a>'
    )


def _row(r: Dict) -> str:
    color, _ = _TIER_DOT.get(r.get("tier", ""), ("#8b94a0", "—"))
    return (
        f'<a class="tsh-row" href="{_html.escape(r["route"])}">'
        f'<span class="tsh-dot" style="background:{color}"></span>'
        f'<span class="tsh-row-label">{_html.escape(r.get("label",""))}</span>'
        f'<span class="tsh-row-route">{_html.escape(r["route"])}</span></a>'
    )


def render_tools_showcase(total_surfaces: int = 0) -> str:
    from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose

    ranks = _ranked()
    # Flatten with section tags for the overall top-6.
    flat: List[Dict] = []
    section_of: Dict[str, str] = {}
    for sec, rows in ranks.items():
        for r in rows:
            flat.append(r)
            section_of[r["route"]] = sec
    top_overall = sorted((r for r in flat if r.get("tier") in _GATE),
                         key=lambda r: -r.get("total", 0.0))[:6]

    head = ck_page_title(
        "Tools",
        eyebrow="THE BEST OF PEDESK",
        meta=(f"top surfaces, ranked · {total_surfaces} total · "
              "press Cmd+K anywhere to jump"),
    )
    src = ck_source_purpose(
        purpose="Start here: the highest-value surfaces for deal work, ranked. "
                "The top diligence layers and a strip per workspace are below; "
                "the full index of every surface is one click away.",
        universe="derived",
        confidence="derived",
        source="Ranking from scripts/rank_surfaces.py (data-honesty tier + "
               "deal-workflow fit + real-data wiring + renderer depth)",
        next_action="Open the #1 surface",
        next_href=(top_overall[0]["route"] if top_overall else "/home"),
    )

    hero = (
        '<div class="tsh-hero">'
        + "".join(_hero_card(i, r, section_of.get(r["route"], ""))
                  for i, r in enumerate(top_overall, 1))
        + '</div>'
    )

    # Spotlight: top diligence layers (the heart of the product).
    dil = _gated_sorted(ranks.get("diligence", []))[:6]
    dil_strip = (
        '<div class="tsh-strip"><div class="tsh-strip-head">'
        '<h3>Top diligence layers</h3>'
        '<a class="tsh-strip-more" href="/best/diligence">all diligence, ranked &rarr;</a>'
        '</div>' + "".join(_row(r) for r in dil) + '</div>'
    )

    # Compact per-workspace strips (top 3 each).
    strips = []
    for key, label in _WORKSPACES:
        if key == "diligence":
            continue
        rows = _gated_sorted(ranks.get(key, []))[:3]
        if not rows:
            continue
        strips.append(
            f'<div class="tsh-strip"><div class="tsh-strip-head">'
            f'<h3>{_html.escape(label)}</h3>'
            f'<a class="tsh-strip-more" href="/best/{key}">all {label.lower()}, '
            f'ranked &rarr;</a></div>'
            + "".join(_row(r) for r in rows) + '</div>'
        )

    all_bar = (
        '<div class="tsh-allbar">'
        f'<span style="font-family:var(--sc-sans);font-size:13px;'
        f'color:var(--sc-text-dim,#465366);">Looking for something specific? '
        f'Browse the complete index of all {total_surfaces} surfaces, grouped '
        f'by workspace with data-honesty dots.</span>'
        '<a href="/tools?view=all">Browse the full index &rarr;</a>'
        '</div>'
    )

    body = (head + src + hero + dil_strip + "".join(strips) + all_bar)
    return chartis_shell(body, "Tools", active_nav="/tools", extra_css=_CSS)
