"""Reusable grouped section-catalog renderer.

Generalises the /diligence landing — the editorial pattern the user picked as
the gold standard: a section's surfaces grouped into a handful of named pillars,
each surface a row with its one-line job. This module is the single renderer
behind every section landing (Diligence, Source, Pipeline, Library, Research,
Portfolio) so they all look and behave identically.

Adds the honesty tier to every row (a coloured dot + label) so a partner sees,
inline, whether a surface runs on live data, a computed model, or illustrative
figures — the "map real / yellow / live onto it" requirement. Pillars are
curated (ordered, explained); the dot is derived from surface_status so it can
never drift from the page's real data-honesty.
"""
from __future__ import annotations

import html as _html
from typing import List, Mapping, Optional

_TIER_DOT = {
    "green": ("#0a8a5f", "Live data"),
    "navy": ("#15324f", "Computed"),
    "data_required": ("#b8732a", "Needs data"),
    "yellow": ("#c9a227", "Illustrative"),
    "red": ("#b5321e", "Placeholder"),
}

_CSS = (
    '<style>'
    '.sc-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));'
    'gap:24px;margin:0 0 24px;}'
    '@media (max-width:1100px){.sc-grid{grid-template-columns:1fr;}}'
    '.sc-pillar-head{display:flex;flex-direction:column;gap:8px;'
    'border-bottom:1px solid var(--sc-rule,#d6cfc0);padding-bottom:16px;}'
    '.sc-pillar-title{font-family:var(--sc-serif,Georgia,serif);font-weight:500;'
    'font-size:22px;color:var(--sc-navy,#0b2341);margin:4px 0 0;letter-spacing:-0.01em;}'
    '.sc-pillar-body{font-family:var(--sc-serif,Georgia,serif);font-size:13.5px;'
    'line-height:1.6;color:var(--sc-text-dim,#465366);margin:0;max-width:48ch;}'
    '.sc-link-list{display:flex;flex-direction:column;}'
    '.sc-link{display:block;text-decoration:none;color:inherit;padding:12px;'
    'border-bottom:1px solid var(--sc-rule,#d6cfc0);margin:0 -12px;border-radius:2px;'
    'transition:padding-left 0.12s,background 0.12s;}'
    '.sc-link:last-child{border-bottom:0;}'
    '.sc-link:hover{background:var(--sc-bone,#ece5d6);padding-left:16px;}'
    '.sc-link:hover .sc-arrow{color:var(--sc-teal,#155752);}'
    '.sc-row{display:flex;align-items:baseline;gap:9px;}'
    '.sc-dot{width:8px;height:8px;border-radius:50%;flex:none;'
    'position:relative;top:1px;}'
    '.sc-label{font-family:var(--sc-sans,Inter,sans-serif);font-weight:600;'
    'font-size:14px;color:var(--sc-navy,#0b2341);}'
    '.sc-arrow{margin-left:auto;font-family:var(--sc-sans);font-size:14px;'
    'color:var(--sc-text-faint,#7a8699);transition:color 0.12s;}'
    '.sc-blurb{font-family:var(--sc-serif,Georgia,serif);font-size:12.5px;'
    'color:var(--sc-text-dim,#465366);line-height:1.45;margin-top:4px;'
    'padding-left:17px;}'
    '.sc-legend{display:flex;flex-wrap:wrap;gap:14px;margin:2px 0 22px;'
    'font-family:var(--sc-mono,monospace);font-size:10.5px;'
    'color:var(--sc-text-dim,#465366);}'
    '.sc-legend span{display:inline-flex;align-items:center;gap:5px;}'
    '</style>'
)


def _tier(href: str) -> str:
    try:
        from ..diligence.surface_status import classify_surface
        return classify_surface(href.split("?")[0]).get("tier", "navy")
    except Exception:  # noqa: BLE001
        return "navy"


def _link_row(link: Mapping[str, str]) -> str:
    color, tip = _TIER_DOT.get(_tier(link["href"]), ("#8b94a0", ""))
    return (
        f'<a class="sc-link" href="{_html.escape(link["href"], quote=True)}">'
        f'<div class="sc-row">'
        f'<span class="sc-dot" style="background:{color}" '
        f'title="{_html.escape(tip)}"></span>'
        f'<span class="sc-label">{_html.escape(link["label"])}</span>'
        f'<span class="sc-arrow" aria-hidden="true">&rarr;</span></div>'
        f'<div class="sc-blurb">{_html.escape(link["blurb"])}</div></a>'
    )


def _legend() -> str:
    return (
        '<div class="sc-legend">'
        + "".join(
            f'<span><span class="sc-dot" style="background:{c}"></span>{t}</span>'
            for c, t in [("#0a8a5f", "Live data"), ("#15324f", "Computed"),
                         ("#b8732a", "Needs data"), ("#c9a227", "Illustrative")])
        + '</div>'
    )


def render_grouped_catalog(
    *,
    section: str,
    title: str,
    eyebrow: str,
    pillars: List[Mapping[str, object]],
    explainer_head: str,
    explainer_body: str,
    explainer_source: str,
    intro_headline: str,
    intro_body: str,
    intro_italic: str = "",
    next_label: Optional[str] = None,
    next_href: Optional[str] = None,
    next_italic: str = "",
    subtitle: str = "",
) -> str:
    """Render a section landing as grouped pillars with honesty dots."""
    from ._chartis_kit import (
        chartis_shell, ck_next_section, ck_page_title, ck_panel,
        ck_section_intro, ck_page_explainer)

    pillars_html: List[str] = []
    for p in pillars:
        rows = "".join(_link_row(link) for link in p["links"])  # type: ignore[index]
        inner = (
            '<header class="sc-pillar-head">'
            f'<div class="ck-eyebrow">{_html.escape(str(p["eyebrow"]))}</div>'
            f'<h2 class="sc-pillar-title">{_html.escape(str(p["title"]))}</h2>'
            f'<p class="sc-pillar-body">{_html.escape(str(p["body"]))}</p>'
            '</header>'
            f'<div class="sc-link-list">{rows}</div>'
        )
        pillars_html.append(ck_panel(inner))

    n = sum(len(p["links"]) for p in pillars)  # type: ignore[arg-type]
    head = (
        ck_page_title(title, eyebrow=eyebrow,
                      meta=f"{n} surfaces · grouped into {len(pillars)} pillars")
        + ck_page_explainer(explainer_head, explainer_body,
                            source=explainer_source)
    )
    intro = ck_section_intro(eyebrow=f"{eyebrow}", headline=intro_headline,
                             italic_word=intro_italic or None, body=intro_body)
    nxt = ""
    if next_label and next_href:
        nxt = ck_next_section(next_label, next_href, eyebrow="Continue —",
                              italic_word=next_italic or None)
    body = (
        _CSS + head + intro + _legend()
        + '<div class="sc-grid">' + "".join(pillars_html) + '</div>' + nxt
    )
    return chartis_shell(body, title, active_nav="/" + section,
                         subtitle=subtitle or f"{title} · {n} surfaces")
