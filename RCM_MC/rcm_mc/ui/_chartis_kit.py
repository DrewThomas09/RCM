"""SeekingChartis — Chartis Kit (UI v2, editorial rework).

Drop-in replacement for ``rcm_mc/ui/_chartis_kit.py``.

This module is the shared shell used by every page renderer in
``rcm_mc/ui/*.py``. It provides:

- ``chartis_shell(body_html, title, *, active_nav=None, breadcrumbs=None, code=None)``
- ``ck_panel(body_html, *, title=None, code=None)``
- ``ck_table(rows, columns, *, dense=False)``
- ``ck_kpi_block(label, value, *, trend=None, sub=None, code=None)``
- ``ck_signal_badge(text, *, tone='neutral')``  # tone in: positive/warning/negative/critical/neutral
- ``ck_section_header(title, *, eyebrow=None, code=None)``
- ``ck_fmt_currency``, ``ck_fmt_percent``, ``ck_fmt_number``
- ``ck_command_palette(modules)``  # new — ⌘K jump
- Navigation data: ``_CORPUS_NAV`` (active), ``_LEGACY_NAV`` (deprecated)

All public signatures match the previous version. Only the internal
palette, CSS block, top-bar markup, and panel chrome change.
"""

from __future__ import annotations

import html as _html
import os
from typing import Any, Iterable, Mapping, Optional, Sequence

# ---------------------------------------------------------------------------
# Feature flag — set CHARTIS_UI_V2=0 to fall back to the legacy dark shell.
# ---------------------------------------------------------------------------

UI_V2_ENABLED = os.environ.get("CHARTIS_UI_V2", "1") != "0"

# ---------------------------------------------------------------------------
# Palette — editorial navy / teal / parchment
# ---------------------------------------------------------------------------

P = {
    # Surfaces
    "bg":          "#f5f1ea",   # parchment page bg
    "panel":       "#ffffff",   # white data panels
    "panel_alt":   "#ece6db",   # bone tint
    "navy":        "#0b2341",   # primary dark
    "ink":         "#061626",   # deepest
    "navy_2":      "#132e53",   # hover / elevated
    "navy_3":      "#1d3c69",   # divider on navy
    "rule":        "#d6cfc3",   # hairline on parchment
    "rule_2":      "#c5bdae",

    # Text on light
    "text":        "#1a2332",
    "text_dim":    "#465366",
    "text_faint":  "#7a8699",

    # Text on navy
    "on_navy":       "#e9eef5",
    "on_navy_dim":   "#a5b4ca",
    "on_navy_faint": "#6e7e99",

    # Accent
    "teal":     "#2fb3ad",
    "teal_2":   "#66c8c3",
    "teal_ink": "#0f5e5a",

    # Status
    "positive": "#0a8a5f",
    "warning":  "#b8732a",
    "negative": "#b5321e",
    "critical": "#8a1e0e",
}

# Compatibility aliases — every renderer that was written against
# the legacy P dict (border, accent, brand, etc.) keeps working
# without 500ing on KeyError. The aliases map to the closest
# editorial-palette equivalent. Adding new aliases here is the
# right way to unblock pages that were partially-migrated.
P.update({
    "border":        P["rule"],        # legacy hairline → editorial rule
    "border_dim":    P["rule_2"],
    "accent":        P["teal"],        # legacy accent → editorial teal
    "brand":         P["navy"],        # legacy brand   → editorial navy
    "brand_accent":  P["teal"],        # second legacy alias for brand accent
    "bg_secondary":  P["panel_alt"],
    "row_stripe":    P["panel_alt"],
    # Text aliases used by older renderers
    "text_secondary": P["text_dim"],
    "text_muted":    P["text_dim"],
})

# ---------------------------------------------------------------------------
# Navigation — top bar primary + Platform Index secondary
# ---------------------------------------------------------------------------

_CORPUS_NAV = [
    {"label": "Home",      "href": "/home",      "key": "home"},
    {"label": "Pipeline",  "href": "/pipeline",  "key": "pipeline"},
    {"label": "Library",   "href": "/library",   "key": "library"},
    {"label": "Research",  "href": "/research",  "key": "research"},
    {"label": "Portfolio", "href": "/portfolio", "key": "portfolio"},
]

# Legacy navigation kept for callers that haven't migrated.
_LEGACY_NAV = [
    {"label": "Deals",        "href": "/deals",        "key": "deals"},
    {"label": "Analysis",     "href": "/analysis",     "key": "analysis"},
    {"label": "Portfolio",    "href": "/portfolio",    "key": "portfolio"},
    {"label": "Market",       "href": "/market",       "key": "market"},
    {"label": "PE Intel",     "href": "/pe-intelligence", "key": "pe"},
    {"label": "Corpus",       "href": "/corpus-backtest", "key": "corpus"},
    {"label": "Telehealth Econ", "href": "/telehealth-econ", "key": "tele"},
    {"label": "Admin",        "href": "/admin",        "key": "admin"},
]

# ---------------------------------------------------------------------------
# Formatting helpers — signatures unchanged
# ---------------------------------------------------------------------------

def ck_fmt_currency(v: Optional[float], *, precision: int = 0, dash: str = "—") -> str:
    if v is None:
        return dash
    try:
        if abs(v) >= 1e9:
            return f"${v / 1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v / 1e6:.1f}M"
        if abs(v) >= 1e3:
            return f"${v / 1e3:.0f}K"
        return f"${v:,.{precision}f}"
    except Exception:
        return dash


def ck_fmt_percent(v: Optional[float], *, precision: int = 1, dash: str = "—") -> str:
    if v is None:
        return dash
    try:
        return f"{v * 100:.{precision}f}%"
    except Exception:
        return dash


def ck_fmt_number(v: Optional[float], *, precision: int = 0, dash: str = "—") -> str:
    if v is None:
        return dash
    try:
        return f"{v:,.{precision}f}"
    except Exception:
        return dash


# ---------------------------------------------------------------------------
# Panel primitives
# ---------------------------------------------------------------------------

def _esc(x) -> str:
    return _html.escape(str(x), quote=True) if x is not None else ""


def ck_panel(body_html: str, *, title: Optional[str] = None, code: Optional[str] = None) -> str:
    """White panel with navy header strip and optional [CODE] tag."""
    head = ""
    if title or code:
        head = (
            '<div class="ck-panel-head">'
            f'<div class="ck-panel-title">{_esc(title) if title else ""}</div>'
            f'{"<div class=\"ck-panel-code\">[" + _esc(code) + "]</div>" if code else ""}'
            "</div>"
        )
    return f'<section class="ck-panel">{head}<div class="ck-panel-body">{body_html}</div></section>'


def ck_section_header(title: str, *, eyebrow: Optional[str] = None, code: Optional[str] = None) -> str:
    eb = f'<div class="sc-eyebrow">{_esc(eyebrow)}</div>' if eyebrow else ""
    cd = f'<div class="ck-section-code">[{_esc(code)}]</div>' if code else ""
    return (
        '<header class="ck-section-header">'
        f'{eb}<h2 class="sc-h2">{_esc(title)}</h2>{cd}'
        "</header>"
    )


def ck_table(
    rows: Sequence[Mapping[str, object]],
    columns: Sequence[Mapping[str, str]],
    *,
    dense: bool = False,
) -> str:
    """Emit a Bloomberg-density table with tabular-nums numerics.

    ``columns`` is a list of ``{"key": "ebitda", "label": "EBITDA",
    "align": "right", "kind": "currency"}`` dicts. ``kind`` is optional
    and hints at cell formatting.
    """
    cls = "ck-table" + (" ck-dense" if dense else "")
    header_cells = "".join(
        f'<th class="align-{_esc(c.get("align", "left"))}">{_esc(c.get("label", ""))}</th>'
        for c in columns
    )
    body_rows = []
    for r in rows:
        cells = []
        for c in columns:
            key = c.get("key", "")
            raw = r.get(key) if hasattr(r, "get") else None
            kind = c.get("kind", "")
            if kind == "currency":
                val = ck_fmt_currency(raw)
            elif kind == "percent":
                val = ck_fmt_percent(raw)
            elif kind == "number":
                val = ck_fmt_number(raw)
            else:
                val = _esc(raw if raw is not None else "—")
            num_cls = " sc-num" if kind in ("currency", "percent", "number") else ""
            cells.append(
                f'<td class="align-{_esc(c.get("align", "left"))}{num_cls}">{val}</td>'
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        f'<table class="{cls}">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def ck_kpi_block(
    label: str,
    value: str,
    *,
    trend: Optional[str] = None,
    sub: Optional[str] = None,
    code: Optional[str] = None,
) -> str:
    trend_html = ""
    if trend:
        tone = "positive" if trend.startswith("+") else "negative" if trend.startswith("-") else "neutral"
        trend_html = f'<span class="ck-kpi-trend tone-{tone}">{_esc(trend)}</span>'
    sub_html = f'<div class="ck-kpi-sub">{_esc(sub)}</div>' if sub else ""
    code_html = f'<div class="ck-kpi-code">[{_esc(code)}]</div>' if code else ""
    return (
        '<div class="ck-kpi">'
        f'{code_html}'
        f'<div class="ck-kpi-label">{_esc(label)}</div>'
        f'<div class="ck-kpi-value sc-num">{_esc(value)}{trend_html}</div>'
        f'{sub_html}'
        "</div>"
    )


def ck_signal_badge(text: str, *, tone: str = "neutral") -> str:
    tone = tone if tone in ("positive", "warning", "negative", "critical", "neutral") else "neutral"
    return f'<span class="ck-badge tone-{tone}">{_esc(text)}</span>'


# ---------------------------------------------------------------------------
# Editorial primitives — eyebrow, section intro, arrow link, image card.
# These mirror the patterns on chartis.com so partner-facing pages
# feel continuous with the marketing landing.
# ---------------------------------------------------------------------------

def ck_eyebrow(text: str, *, on_navy: bool = False) -> str:
    """Caps eyebrow + thin teal rule. Primary section anchor pattern."""
    cls = "ck-eyebrow on-navy" if on_navy else "ck-eyebrow"
    return f'<div class="{cls}">{_esc(text)}</div>'


def ck_section_intro(
    eyebrow: str,
    headline: str,
    *,
    body: Optional[str] = None,
    italic_word: Optional[str] = None,
    on_navy: bool = False,
) -> str:
    """Editorial section intro — eyebrow + serif headline + optional body.

    If ``italic_word`` is provided it is wrapped in ``<em>`` inside the
    headline (case-insensitive substring match), reproducing the
    "Reasons to *believe* in better" cadence on chartis.com.
    """
    h = _esc(headline)
    if italic_word:
        for cand in (italic_word, italic_word.capitalize(), italic_word.upper()):
            e_cand = _esc(cand)
            if e_cand in h:
                h = h.replace(e_cand, f"<em>{e_cand}</em>", 1)
                break
    body_html = (
        f'<p class="ck-section-body">{_esc(body)}</p>' if body else ""
    )
    return (
        '<div class="ck-section-intro">'
        f'{ck_eyebrow(eyebrow, on_navy=on_navy)}'
        f'<h2>{h}</h2>'
        f'{body_html}'
        '</div>'
    )


def ck_arrow_link(text: str, href: str, *, on_navy: bool = False) -> str:
    """Teal "VIEW MORE ↗" arrow link, the primary editorial CTA."""
    cls = "ck-arrow on-navy" if on_navy else "ck-arrow"
    return f'<a class="{cls}" href="{_esc(href)}">{_esc(text)}</a>'


def ck_image_card(
    *,
    image_html: str,
    eyebrow: str,
    title: str,
    body: str,
    cta_text: str = "Read more",
    cta_href: str = "#",
) -> str:
    """Image-top editorial card — eyebrow / title / body / arrow CTA.

    ``image_html`` is the inner ``<img>`` or SVG; the card wrapper
    supplies the 4:3 aspect frame and the bottom teal border that
    pairs cards across a row visually.
    """
    return (
        '<article class="ck-image-card">'
        f'<div class="ck-image-card-img">{image_html}</div>'
        '<div class="ck-image-card-body">'
        f'{ck_eyebrow(eyebrow)}'
        f'<h3 class="ck-image-card-title">{_esc(title)}</h3>'
        f'<p>{_esc(body)}</p>'
        f'{ck_arrow_link(cta_text, cta_href)}'
        '</div>'
        '</article>'
    )


def ck_severity_panel(
    *,
    tone: str,
    label: str,
    count: int,
    rows_html: str,
) -> str:
    """Severity-toned panel for /alerts and /escalations.

    Replaces the legacy ``<div class="card"><h2>RED (1)</h2>`` pattern
    with a Chartis-style left-rule-toned panel. ``rows_html`` is the
    pre-rendered ``<li>`` content.
    """
    valid = {"red", "amber", "info", "positive", "neutral"}
    t = tone if tone in valid else "neutral"
    return (
        f'<section class="ck-severity-panel tone-{t}">'
        '<header class="ck-severity-panel-head">'
        f'<h3>{_esc(label)}</h3>'
        f'<span class="count">{int(count):d} item{"" if count == 1 else "s"}</span>'
        '</header>'
        f'<ul class="ck-severity-list">{rows_html}</ul>'
        '</section>'
    )


def ck_search_hero(
    *,
    label: str = "Search",
    placeholder: str = "Keyword",
    action: str,
    name: str = "q",
    initial: Optional[str] = None,
    method: str = "GET",
) -> str:
    """Navy search hero with italic-serif label + circular submit
    + teal chevron-cut bottom-right corner. Mirrors the Chartis
    Insights page hero exactly. Drop above any content-listing
    page (``/library``, ``/research``, ``/notes``, ``/search``)
    so the partner's first read is the same as on chartis.com.

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` pattern 01.
    """
    initial_attr = (
        f' value="{_esc(initial)}"' if initial else ""
    )
    return (
        '<section class="ck-search-hero">'
        '<div class="ck-search-hero-inner">'
        f'<span class="ck-search-hero-label">{_esc(label)}</span>'
        f'<form class="ck-search-hero-form" method="{_esc(method)}" '
        f'action="{_esc(action)}" role="search">'
        f'<input class="ck-search-hero-input" type="search" '
        f'name="{_esc(name)}" placeholder="{_esc(placeholder)}" '
        f'aria-label="{_esc(label)}"{initial_attr}>'
        '<button class="ck-search-hero-submit" type="submit" '
        'aria-label="Run search">'
        '<svg viewBox="0 0 24 24" width="18" height="18" '
        'aria-hidden="true">'
        '<circle cx="10" cy="10" r="6" fill="none" '
        'stroke="currentColor" stroke-width="1.5"/>'
        '<line x1="14.5" y1="14.5" x2="20" y2="20" '
        'stroke="currentColor" stroke-width="1.5"/>'
        '</svg>'
        '</button>'
        '</form>'
        '</div>'
        '<span class="ck-search-hero-chevron" aria-hidden="true"></span>'
        '</section>'
    )


def ck_affirm_empty(
    *,
    headline: str,
    body: str,
    cta_text: Optional[str] = None,
    cta_href: Optional[str] = None,
) -> str:
    """Editorial 'all clear' empty state — affirmative, not blank.

    Chartis-style positive band with optional teal arrow CTA. Used
    when /alerts has zero active items so the partner sees a real
    signal of health, not a void.
    """
    cta = (
        ck_arrow_link(cta_text, cta_href)
        if cta_text and cta_href else ""
    )
    return (
        '<section class="ck-affirm-empty">'
        f'<h3>{_esc(headline)}</h3>'
        f'<p>{_esc(body)}</p>'
        f'{cta}'
        '</section>'
    )


# ---------------------------------------------------------------------------
# Command palette (⌘K) — feed it the module catalog
# ---------------------------------------------------------------------------

def ck_command_palette(modules: Iterable[Mapping[str, str]]) -> str:
    items = "".join(
        f'<li data-key="{_esc(m.get("id", ""))}" data-route="{_esc(m.get("route", ""))}">'
        f'<span class="cp-title">{_esc(m.get("title", ""))}</span>'
        f'<span class="cp-route">{_esc(m.get("route", ""))}</span>'
        "</li>"
        for m in modules
    )
    return (
        '<div class="ck-palette" id="ck-palette" hidden>'
        '<div class="ck-palette-box">'
        '<input class="ck-palette-input" type="text" placeholder="Jump to… (⌘K)" />'
        f'<ul class="ck-palette-list">{items}</ul>'
        "</div></div>"
    )


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------

_CSS_LINK = '<link rel="stylesheet" href="/static/chartis_tokens.css">'

# Inline fallback — if static serving of chartis_tokens.css isn't wired up,
# the class names defined here keep pages readable. Prefer the linked file.
_CSS_INLINE_FALLBACK = """
<style>
  /* Panel + data chrome layered on top of chartis_tokens.css */
  .ck-panel { background:#fff; border:1px solid var(--sc-rule); border-radius:2px; box-shadow:var(--sc-shadow-1); margin:0 0 var(--sc-s-5); }
  .ck-panel-head { display:flex; align-items:center; justify-content:space-between; background:var(--sc-navy); color:var(--sc-on-navy); padding:10px 16px; border-radius:2px 2px 0 0; }
  .ck-panel-title { font-family:var(--sc-sans); font-weight:600; font-size:13px; letter-spacing:0.04em; text-transform:uppercase; }
  .ck-panel-code { font-family:var(--sc-mono); font-size:10px; letter-spacing:0.1em; color:var(--sc-on-navy-dim); }
  .ck-panel-body { padding:var(--sc-s-6); }
  .ck-table { width:100%; border-collapse:collapse; font-size:13px; }
  .ck-table thead th { background:var(--sc-bone); color:var(--sc-text-dim); font-family:var(--sc-sans); font-weight:600; font-size:11px; letter-spacing:0.1em; text-transform:uppercase; padding:8px 12px; border-bottom:1px solid var(--sc-rule); text-align:left; }
  .ck-table tbody td { padding:8px 12px; border-bottom:1px solid var(--sc-rule); }
  .ck-table.ck-dense tbody td { padding:5px 10px; font-size:12px; }
  .ck-table .sc-num { font-family:var(--sc-mono); font-variant-numeric:tabular-nums; }
  .ck-table .align-right { text-align:right; }
  .ck-table .align-center { text-align:center; }
  .ck-kpi { padding:var(--sc-s-4) 0; border-top:1px solid var(--sc-rule); position:relative; }
  .ck-kpi-label { font-family:var(--sc-sans); font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); margin-bottom:4px; }
  .ck-kpi-value { font-family:var(--sc-serif); font-size:28px; font-weight:500; color:var(--sc-navy); display:flex; align-items:baseline; gap:8px; }
  .ck-kpi-trend { font-family:var(--sc-mono); font-size:12px; }
  .ck-kpi-trend.tone-positive { color:var(--sc-positive); }
  .ck-kpi-trend.tone-negative { color:var(--sc-negative); }
  .ck-kpi-trend.tone-neutral  { color:var(--sc-text-faint); }
  .ck-kpi-sub { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); margin-top:4px; }
  .ck-kpi-code { position:absolute; top:var(--sc-s-4); right:0; font-family:var(--sc-mono); font-size:10px; color:var(--sc-text-faint); letter-spacing:0.1em; }
  .ck-badge { display:inline-flex; align-items:center; padding:3px 8px; font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; border:1px solid currentColor; border-radius:2px; }
  .ck-badge.tone-positive { color:var(--sc-positive); }
  .ck-badge.tone-warning  { color:var(--sc-warning); }
  .ck-badge.tone-negative { color:var(--sc-negative); }
  .ck-badge.tone-critical { color:var(--sc-critical); }
  .ck-badge.tone-neutral  { color:var(--sc-text-dim); }
  .ck-section-header { display:flex; align-items:flex-end; justify-content:space-between; gap:var(--sc-s-5); margin:var(--sc-s-8) 0 var(--sc-s-5); }
  .ck-section-code { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.1em; }

  /* Top bar — navy + white + teal accent rule, mirrors chartis.com */
  .ck-topbar { position:sticky; top:0; z-index:50; background:var(--sc-navy); border-bottom:2px solid var(--sc-teal); }
  .ck-topbar-inner { display:flex; align-items:center; gap:var(--sc-s-6); padding:18px var(--sc-s-6); max-width:1440px; margin:0 auto; }
  .ck-wordmark { display:flex; align-items:center; gap:10px; font-family:var(--sc-serif); font-weight:500; font-size:19px; color:var(--sc-on-navy); letter-spacing:-0.005em; text-decoration:none; }
  .ck-wordmark em { font-style:italic; font-weight:400; color:var(--sc-teal-2); }
  .ck-wordmark-mark { width:28px; height:28px; border-radius:50%; background:transparent; border:1.5px solid var(--sc-on-navy); position:relative; flex-shrink:0; }
  .ck-wordmark-mark::after { content:''; position:absolute; inset:5px; border:2px solid var(--sc-teal); border-right-color:transparent; border-bottom-color:transparent; border-radius:50%; transform:rotate(-45deg); }
  .ck-nav { display:flex; gap:var(--sc-s-7); margin-left:var(--sc-s-6); }
  .ck-nav a { font-family:var(--sc-sans); font-size:13px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:var(--sc-on-navy-dim); padding:6px 0; border-bottom:2px solid transparent; text-decoration:none; transition:color 0.15s; }
  .ck-nav a:hover { color:var(--sc-on-navy); }
  .ck-nav a.active { color:var(--sc-on-navy); border-bottom-color:var(--sc-teal); }
  .ck-topbar-right { margin-left:auto; display:flex; align-items:center; gap:var(--sc-s-4); }
  .ck-search { border:1px solid var(--sc-navy-3); padding:7px 12px; font-size:12px; min-width:240px; border-radius:2px; background:var(--sc-navy-2); font-family:var(--sc-sans); color:var(--sc-on-navy); letter-spacing:0.02em; }
  .ck-search::placeholder { color:var(--sc-on-navy-faint); }
  .ck-search:focus { outline:none; border-color:var(--sc-teal); background:var(--sc-navy); }
  .ck-cta { display:inline-flex; align-items:center; gap:8px; font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:var(--sc-on-navy); border:1px solid var(--sc-on-navy); padding:8px 14px; border-radius:2px; text-decoration:none; transition:background 0.15s, color 0.15s; }
  .ck-cta:hover { background:var(--sc-teal); border-color:var(--sc-teal); color:var(--sc-navy); }
  .ck-cta-arrow { display:inline-block; width:10px; height:10px; }
  .ck-user-chip { width:34px; height:34px; border-radius:50%; background:var(--sc-teal); color:var(--sc-navy); display:flex; align-items:center; justify-content:center; font-family:var(--sc-sans); font-weight:700; font-size:12px; letter-spacing:0.04em; cursor:pointer; }
  .ck-breadcrumbs { display:flex; gap:8px; padding:14px var(--sc-s-6); max-width:1440px; margin:0 auto; font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.08em; text-transform:uppercase; border-bottom:1px solid var(--sc-rule); }
  .ck-breadcrumbs a { color:var(--sc-text-dim); text-decoration:none; }
  .ck-breadcrumbs a:hover { color:var(--sc-teal-ink); }
  .ck-breadcrumbs .sep { color:var(--sc-rule-2); }

  /* Editorial primitives — eyebrow + section intro + arrow link */
  .ck-eyebrow { display:inline-flex; align-items:center; gap:12px; font-family:var(--sc-mono); font-size:11px; font-weight:600; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-dim); }
  .ck-eyebrow::before { content:''; display:inline-block; width:24px; height:2px; background:var(--sc-teal); }
  .ck-eyebrow.on-navy { color:var(--sc-on-navy-dim); }
  .ck-eyebrow.on-navy::before { background:var(--sc-teal); }
  .ck-section-intro { margin:var(--sc-s-9) 0 var(--sc-s-7); }
  .ck-section-intro h2 { font-family:var(--sc-serif); font-weight:400; font-size:clamp(28px, 3.4vw, 40px); line-height:1.1; letter-spacing:-0.015em; color:var(--sc-navy); margin:var(--sc-s-5) 0 0; max-width:24ch; }
  .ck-section-intro h2 em { font-style:italic; font-weight:400; color:var(--sc-teal-ink); }
  .ck-section-intro .ck-section-body { font-family:var(--sc-serif); font-size:17px; line-height:1.6; color:var(--sc-text-dim); margin-top:var(--sc-s-5); max-width:54ch; }
  .ck-arrow { display:inline-flex; align-items:center; gap:6px; font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:var(--sc-teal-ink); text-decoration:none; }
  .ck-arrow::after { content:'\\2197'; font-size:14px; line-height:1; }
  .ck-arrow:hover { color:var(--sc-navy); }
  .ck-arrow.on-navy { color:var(--sc-teal); }
  .ck-arrow.on-navy:hover { color:var(--sc-on-navy); }

  /* Editorial card — image-top with eyebrow / title / body / arrow */
  .ck-card-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:var(--sc-s-7); margin:var(--sc-s-6) 0; }
  .ck-image-card { display:flex; flex-direction:column; gap:var(--sc-s-4); padding:0; background:transparent; border:0; }
  .ck-image-card-img { width:100%; aspect-ratio:4/3; background:var(--sc-bone); border-bottom:2px solid var(--sc-teal); object-fit:cover; }
  .ck-image-card-body { padding:var(--sc-s-4) 0 var(--sc-s-3); }
  .ck-image-card-title { font-family:var(--sc-serif); font-weight:500; font-size:21px; line-height:1.25; color:var(--sc-navy); margin:var(--sc-s-3) 0 var(--sc-s-3); }
  .ck-image-card-body p { font-family:var(--sc-sans); font-size:14px; line-height:1.6; color:var(--sc-text-dim); margin:0 0 var(--sc-s-4); }

  /* Severity panels — replace legacy <div class="card"> in alerts/etc. */
  .ck-severity-panel { background:#fff; border:1px solid var(--sc-rule); border-left:4px solid var(--sc-rule-2); border-radius:2px; box-shadow:var(--sc-shadow-1); margin:0 0 var(--sc-s-5); }
  .ck-severity-panel.tone-red { border-left-color:var(--sc-negative); }
  .ck-severity-panel.tone-amber { border-left-color:var(--sc-warning); }
  .ck-severity-panel.tone-info { border-left-color:var(--sc-teal); }
  .ck-severity-panel.tone-positive { border-left-color:var(--sc-positive); }
  .ck-severity-panel-head { display:flex; align-items:baseline; justify-content:space-between; gap:var(--sc-s-4); padding:14px 18px 6px; border-bottom:1px solid var(--sc-rule); }
  .ck-severity-panel-head h3 { font-family:var(--sc-sans); font-weight:700; font-size:13px; letter-spacing:0.12em; text-transform:uppercase; color:var(--sc-navy); }
  .ck-severity-panel-head .count { font-family:var(--sc-mono); font-size:13px; color:var(--sc-text-faint); }
  .ck-severity-list { list-style:none; padding:0; margin:0; }
  .ck-severity-list li { padding:14px 18px; border-bottom:1px solid var(--sc-rule); display:flex; flex-direction:column; gap:6px; }
  .ck-severity-list li:last-child { border-bottom:0; }
  .ck-severity-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .ck-severity-row .deal { font-family:var(--sc-sans); font-weight:600; color:var(--sc-teal-ink); text-decoration:none; }
  .ck-severity-row .deal:hover { color:var(--sc-navy); text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:3px; }
  .ck-severity-row .title { color:var(--sc-text); font-size:14px; }
  .ck-severity-row .age { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); margin-left:auto; }
  .ck-severity-detail { font-family:var(--sc-sans); font-size:13px; line-height:1.5; color:var(--sc-text-dim); margin-left:0; }
  .ck-severity-actions { display:flex; align-items:center; gap:8px; margin-top:4px; }
  .ck-severity-actions select { font-family:var(--sc-sans); font-size:12px; padding:4px 8px; border:1px solid var(--sc-rule); border-radius:2px; background:#fff; color:var(--sc-text); }
  .ck-severity-actions button { font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; padding:6px 12px; border:1px solid var(--sc-navy); background:var(--sc-navy); color:var(--sc-on-navy); border-radius:2px; cursor:pointer; }
  .ck-severity-actions button:hover { background:var(--sc-navy-2); border-color:var(--sc-navy-2); }
  .ck-affirm-empty { background:#fff; border:1px solid var(--sc-rule); border-left:4px solid var(--sc-positive); border-radius:2px; box-shadow:var(--sc-shadow-1); padding:20px 24px; }
  .ck-affirm-empty h3 { font-family:var(--sc-serif); font-weight:500; font-size:20px; color:var(--sc-positive); margin:0 0 6px; }
  .ck-affirm-empty p { font-family:var(--sc-sans); font-size:14px; line-height:1.6; color:var(--sc-text-dim); margin:0; max-width:64ch; }
  .ck-affirm-empty .ck-arrow { margin-top:var(--sc-s-4); }

  /* Search hero — navy panel + italic-serif label + circular submit
   * + teal chevron-cut bottom-right corner. Mirrors chartis.com/insights. */
  .ck-search-hero { position:relative; background:var(--sc-navy); color:var(--sc-on-navy); padding:56px 0 64px; margin:0 0 var(--sc-s-9); overflow:hidden; }
  .ck-search-hero-inner { max-width:1280px; margin:0 auto; padding:0 var(--sc-s-7); display:flex; align-items:baseline; gap:var(--sc-s-7); }
  .ck-search-hero-label { font-family:var(--sc-serif); font-size:36px; font-weight:400; font-style:italic; letter-spacing:-0.01em; color:var(--sc-on-navy); flex-shrink:0; }
  .ck-search-hero-form { flex:1; display:flex; align-items:center; gap:14px; border-bottom:1px solid var(--sc-on-navy-dim); padding-bottom:8px; transition:border-color 0.15s; }
  .ck-search-hero-form:focus-within { border-bottom-color:var(--sc-teal); }
  .ck-search-hero-input { flex:1; background:transparent; border:0; font-family:var(--sc-serif); font-size:22px; color:var(--sc-on-navy); padding:8px 0; outline:none; min-width:0; }
  .ck-search-hero-input::placeholder { color:var(--sc-on-navy-faint); font-style:italic; }
  .ck-search-hero-submit { background:transparent; border:1px solid var(--sc-on-navy-dim); border-radius:50%; width:36px; height:36px; display:inline-flex; align-items:center; justify-content:center; color:var(--sc-on-navy); cursor:pointer; flex-shrink:0; transition:color 0.15s, border-color 0.15s; }
  .ck-search-hero-submit:hover { color:var(--sc-teal); border-color:var(--sc-teal); }
  .ck-search-hero-chevron { position:absolute; right:0; bottom:0; width:0; height:0; border-style:solid; border-width:0 0 64px 64px; border-color:transparent transparent var(--sc-teal) transparent; pointer-events:none; }

  /* Command palette */
  .ck-palette { position:fixed; inset:0; background:rgba(6,22,38,0.4); display:flex; align-items:flex-start; justify-content:center; padding-top:12vh; z-index:100; }
  .ck-palette[hidden] { display:none; }
  .ck-palette-box { width:min(680px, 92vw); background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-3); border-radius:2px; }
  .ck-palette-input { width:100%; padding:16px 20px; font-family:var(--sc-serif); font-size:18px; border:0; border-bottom:1px solid var(--sc-rule); outline:none; }
  .ck-palette-list { list-style:none; margin:0; padding:0; max-height:52vh; overflow:auto; }
  .ck-palette-list li { display:flex; justify-content:space-between; padding:10px 20px; font-size:13px; cursor:pointer; border-bottom:1px solid var(--sc-bone); }
  .ck-palette-list li:hover { background:var(--sc-bone); }
  .cp-route { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); }

  /* Main content frame */
  .ck-main { padding:var(--sc-s-7) var(--sc-s-6); max-width:1440px; margin:0 auto; }

  /* Print — for /memo/<id>, /ic-packet/<id> */
  @media print {
    .ck-topbar, .ck-breadcrumbs, .ck-palette { display:none !important; }
    body { background:#fff !important; }
    .ck-panel { box-shadow:none; break-inside:avoid; page-break-inside:avoid; }
    .ck-main { max-width:none; padding:0; }
  }
</style>
"""

_PALETTE_JS = """
<script>
(function(){
  var p = document.getElementById('ck-palette');
  if (!p) return;
  var input = p.querySelector('.ck-palette-input');
  var items = Array.from(p.querySelectorAll('li'));
  function show() { p.hidden = false; setTimeout(function(){ input.focus(); }, 0); }
  function hide() { p.hidden = true; input.value = ''; filter(''); }
  function filter(q) {
    q = (q || '').toLowerCase();
    items.forEach(function(li){
      var t = li.textContent.toLowerCase();
      li.style.display = t.indexOf(q) >= 0 ? '' : 'none';
    });
  }
  input.addEventListener('input', function(e){ filter(e.target.value); });
  items.forEach(function(li){
    li.addEventListener('click', function(){
      var r = li.getAttribute('data-route');
      if (r) window.location.href = r;
    });
  });
  document.addEventListener('keydown', function(e){
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); show(); }
    if (e.key === 'Escape' && !p.hidden) { e.preventDefault(); hide(); }
  });
})();
</script>
"""


def _topbar(active_nav: Optional[str], user_initials: str = "AT") -> str:
    """Editorial topbar mirroring chartis.com chrome.

    Navy background, white wordmark with italic ``Chartis``, uppercase
    nav links with teal active underline, search anchored to the
    right with a teal-on-navy user chip. The thin teal stripe on the
    bottom edge is a Chartis signature.
    """
    links = "".join(
        f'<a href="{_esc(item["href"])}" class="{"active" if item["key"] == active_nav else ""}">{_esc(item["label"])}</a>'
        for item in _CORPUS_NAV
    )
    return (
        '<header class="ck-topbar">'
        '<div class="ck-topbar-inner">'
        '<a href="/" class="ck-wordmark" aria-label="SeekingChartis home">'
        '<span class="ck-wordmark-mark"></span>'
        'Seeking<em>Chartis</em>'
        '</a>'
        f'<nav class="ck-nav" aria-label="Primary">{links}</nav>'
        '<div class="ck-topbar-right">'
        '<input class="ck-search" type="search" '
        'placeholder="Search deals, hospitals, routes — ⌘K" '
        'aria-label="Open command palette" />'
        f'<span class="ck-user-chip" title="Signed in">{_esc(user_initials)}</span>'
        "</div>"
        "</div>"
        "</header>"
    )


def _breadcrumbs(crumbs: Optional[Sequence[Any]]) -> str:
    """Render breadcrumb nav from either tuple-shape or dict-shape crumbs.

    Callers pass either ``[("Home", "/"), ("Page", None)]`` (login_page,
    app_page) or ``[{"label": "Home", "href": "/"}, ...]`` (older
    convention). Normalise to a label/href pair before rendering so
    GET /app stops 500ing on tuple-shaped breadcrumbs.
    """
    if not crumbs:
        return ""
    parts = []
    for i, c in enumerate(crumbs):
        # Normalise to (label, href)
        if isinstance(c, tuple) or isinstance(c, list):
            label = c[0] if len(c) > 0 else ""
            href = c[1] if len(c) > 1 else None
        elif isinstance(c, Mapping):
            label = c.get("label", "")
            href = c.get("href")
        else:
            # Unknown shape — render as plain text rather than crash
            label, href = str(c), None
        if i:
            parts.append('<span class="sep">/</span>')
        if href:
            parts.append(f'<a href="{_esc(href)}">{_esc(label)}</a>')
        else:
            parts.append(_esc(label))
    return f'<nav class="ck-breadcrumbs">{"".join(parts)}</nav>'


def chartis_shell(
    body_html: str,
    title: str,
    *,
    active_nav: Optional[str] = None,
    breadcrumbs: Optional[Sequence[Mapping[str, str]]] = None,
    code: Optional[str] = None,           # e.g. "[EBT-07]" for debug overlay
    user_initials: str = "AT",
    include_palette: bool = True,
    palette_modules: Optional[Iterable[Mapping[str, str]]] = None,
    # Compatibility kwargs accepted by partially-migrated callers.
    # Forwarded to the legacy shell when v2 is off; rendered as
    # best-effort no-ops or simple chrome additions in v2 mode.
    subtitle: Optional[str] = None,
    show_chrome: bool = True,
    show_sidebar: bool = False,
    # Page-specific styles injected into <head>. login_page and
    # forgot_page rely on this to land their grid + panel CSS;
    # without it, content stacks as one unstyled column.
    extra_css: Optional[str] = None,
    # Editorial PHI-banner toggle (consumed by the editorial
    # variant). No-op in this v2 shell.
    show_phi_banner: bool = False,
    phi_mode: Optional[str] = None,
    **_extra: Any,
) -> str:
    """Render a full page. Drop-in replacement for the legacy dark shell.

    All kwargs are optional and match or extend the previous signature.
    Unknown kwargs (\\*\\*_extra) are accepted silently for forward-compat
    with partially-migrated callers — every page renders rather than 500.
    """
    if not UI_V2_ENABLED:
        # Lazy-import the legacy shell so we don't pay the cost when v2 is on.
        try:
            from . import _chartis_kit_legacy as _legacy  # type: ignore
            return _legacy.chartis_shell(
                body_html, title,
                active_nav=active_nav, breadcrumbs=breadcrumbs, code=code,
            )
        except Exception:
            pass  # fall through to v2

    fonts = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Source+Serif+4:ital,wght@0,400;0,500;0,600;1,400&'
        'family=Inter+Tight:wght@400;500;600;700&'
        'family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    palette_html = ""
    if include_palette and palette_modules:
        palette_html = ck_command_palette(palette_modules)
    debug_tag = f'<div class="ck-debug-code">[{_esc(code)}]</div>' if code else ""
    # show_chrome=False: bare pages (login / forgot) without topnav
    chrome_html = (
        f"{_topbar(active_nav, user_initials)}"
        f"{_breadcrumbs(breadcrumbs)}"
    ) if show_chrome else ""
    # subtitle: render under the page heading inside <main>
    subtitle_html = (
        f'<div class="ck-subtitle" style="font-size:13px;'
        f'color:var(--ck-text-muted,#5C6878);margin:0 0 14px;'
        f'font-style:italic;">{_esc(subtitle)}</div>'
    ) if subtitle else ""
    main_class = "ck-main ck-with-sidebar" if show_sidebar else "ck-main"
    # Page-specific CSS goes AFTER the kit's CSS so page styles
    # win specificity ties — matches the contract login_page.py
    # and forgot_page.py expect (grid layout, panel chrome, etc.)
    extra_css_html = (
        f"<style>{extra_css}</style>" if extra_css else ""
    )
    return (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(title)} · SeekingChartis</title>"
        f"{fonts}"
        f"{_CSS_LINK}"
        f"{_CSS_INLINE_FALLBACK}"
        f"{extra_css_html}"
        "</head><body>"
        f"{chrome_html}"
        f'<main class="{main_class}">{debug_tag}{subtitle_html}{body_html}</main>'
        f"{palette_html}"
        f"{_PALETTE_JS}"
        "</body></html>"
    )


__all__ = [
    "P",
    "UI_V2_ENABLED",
    "_CORPUS_NAV",
    "_LEGACY_NAV",
    "chartis_shell",
    "ck_panel",
    "ck_section_header",
    "ck_table",
    "ck_kpi_block",
    "ck_signal_badge",
    "ck_command_palette",
    "ck_fmt_currency",
    "ck_fmt_percent",
    "ck_fmt_number",
]

# Compatibility alias for partially-migrated chartis pages
editorial_chartis_shell = chartis_shell
