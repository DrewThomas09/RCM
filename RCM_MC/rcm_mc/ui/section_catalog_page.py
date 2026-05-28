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


_HEAD_CSS = (
    '<style>'
    # 2026-05-28 style-sweep · strict Tier-1 5-block head. Same shape
    # now lives on /portfolio, /pipeline, /methodology — every
    # section landing rendered through this helper inherits it.
    '.sc-head{padding:0 0 28px;margin:0 0 24px;'
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
    '.sc-head .lede{font:400 italic 16.5px/1.55 var(--sc-serif,Georgia),serif;'
    'color:var(--ink-2,#2b3e54);max-width:64ch;margin:0 0 18px;}'
    '.sc-head .lede em{color:var(--green-deep,#154e36);font-style:italic;}'
    '.sc-head .source-note{font:500 10px/1.4 var(--sc-mono,monospace);'
    'letter-spacing:.14em;text-transform:uppercase;'
    'color:var(--muted-2,#9a9e8a);margin:0 0 16px;max-width:62ch;}'
    '@media (max-width:960px){.sc-head h1{font-size:36px;}}'
    '</style>'
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
    from ._chartis_kit import chartis_shell, ck_next_section, ck_panel

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
    # Real, computed honesty coverage across the section's surfaces — so a
    # partner sees at a glance how much of the section runs on live data vs a
    # computed model vs illustrative figures (derived from surface_status, can't
    # drift from truth).
    from collections import Counter
    tiers = Counter(_tier(l["href"]) for p in pillars for l in p["links"])
    parts = []
    for key, word in (("green", "live"), ("navy", "computed"),
                      ("data_required", "need data"), ("yellow", "illustrative")):
        if tiers.get(key):
            parts.append(f"{tiers[key]} {word}")
    coverage = " · ".join(parts)
    # ── 2026-05-28 style-sweep · strict 5-block head ──
    # Replaces the legacy ck_page_title + ck_page_explainer +
    # ck_section_intro triple stack (which produced two h2 headers
    # above the page h1 — visual stacking confusion). Single header
    # block with eyebrow + dash + h1 + meta + italic lede + source-
    # note + status-dot legend (the existing _legend()). One h1.
    intro_h = intro_headline
    if intro_italic and intro_italic in intro_h:
        intro_h = intro_h.replace(
            intro_italic,
            f"<em>{intro_italic}</em>",
            1,
        )
    elif intro_italic and intro_italic.capitalize() in intro_h:
        intro_h = intro_h.replace(
            intro_italic.capitalize(),
            f"<em>{intro_italic.capitalize()}</em>",
            1,
        )
    else:
        # Fall back to italicizing the first phrase up to the first
        # period (Tier-2 §2.3 — italic FIRST PHRASE in green-deep).
        if "." in intro_h:
            first, rest = intro_h.split(".", 1)
            intro_h = f"<em>{_html.escape(first.strip())}.</em>{_html.escape(rest)}"
        else:
            intro_h = f"<em>{_html.escape(intro_h)}</em>"
    head = (
        _HEAD_CSS
        + '<header class="sc-head">'
        f'<div class="eyebrow"><span class="dash"></span>'
        f'{_html.escape(eyebrow)}</div>'
        f'<h1>{_html.escape(title)}</h1>'
        f'<div class="meta">{n} SURFACES · {len(pillars)} PILLARS'
        f'{(" · " + coverage.upper()) if coverage else ""}</div>'
        f'<p class="lede">{intro_h}</p>'
        + (
            f'<p class="lede" style="font-style:normal;color:var(--ink-2,#2b3e54);">'
            f'{_html.escape(explainer_body)}</p>'
            if explainer_body and explainer_body != intro_body else ""
        )
        + (
            f'<p class="source-note">Source: {_html.escape(explainer_source)}</p>'
            if explainer_source else ""
        )
        + _legend()
        + '</header>'
    )
    nxt = ""
    if next_label and next_href:
        nxt = ck_next_section(next_label, next_href, eyebrow="Continue —",
                              italic_word=next_italic or None)
    body = (
        _CSS + head
        + '<div class="sc-grid">' + "".join(pillars_html) + '</div>' + nxt
    )
    return chartis_shell(body, title, active_nav="/" + section,
                         subtitle=subtitle or f"{title} · {n} surfaces")
