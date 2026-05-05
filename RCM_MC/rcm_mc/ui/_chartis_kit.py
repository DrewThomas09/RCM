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

# Always-on editorial chrome. The legacy sidebar shell (which the
# CHARTIS_UI_V2=0 env path used to switch to) is no longer reachable
# through the dispatcher — kept as the constant ``True`` so any
# downstream code that still reads the flag for a different purpose
# (e.g. brand.py palette resolution) continues to read True.
UI_V2_ENABLED = True

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
# Font-family constants — referenced by SVG text elements that
# need a font-family attr (CSS classes don't apply inside SVG
# unless the document's CSS reaches into it). Cycle 29 restores
# these constants that 12 data_public pages still import.
# ---------------------------------------------------------------------------

_MONO = "JetBrains Mono,monospace"
_SANS = "Inter Tight,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif"


# Cycle 29 — backward-compat helpers for pre-cycle-22 helper names
# that 12+ data_public pages still import directly. ``ck_fmt_moic``
# is a thin formatter; ``ck_fmt_num`` / ``ck_fmt_pct`` aliases get
# defined later (after the underlying ``ck_fmt_number`` /
# ``ck_fmt_percent`` are defined further down in this file).


def ck_fmt_moic(v: Optional[float], *, dash: str = "—") -> str:
    """Backward-compat MOIC formatter — pre-cycle-22 helper name.

    Several data_public pages (ic_memo_page, lp_dashboard_page, and
    siblings) call ``ck_fmt_moic(value)`` to produce ``2.40x`` style
    multiplier text. The helper got renamed during the cycle 6 kit
    refresh; cycle 29 restores it as a thin alias on top of
    ``ck_fmt_number``.
    """
    if v is None:
        return dash
    try:
        return f"{float(v):.2f}x"
    except (TypeError, ValueError):
        return dash

# ---------------------------------------------------------------------------
# Navigation — top bar primary + Platform Index secondary
# ---------------------------------------------------------------------------

_CORPUS_NAV = [
    {"label": "Home",      "href": "/home",      "key": "home"},
    {"label": "Pipeline",  "href": "/pipeline",  "key": "pipeline"},
    {"label": "Diligence", "href": "/diligence", "key": "diligence"},
    {"label": "Library",   "href": "/library",   "key": "library"},
    {"label": "Research",  "href": "/research",  "key": "research"},
    {"label": "Portfolio", "href": "/portfolio", "key": "portfolio"},
]

# Per-section sub-nav. Surfaces the most-clicked second-level pages
# directly under the topbar so a partner doesn't have to drill into
# section landing pages to find common surfaces.
_SUB_NAV = {
    "home": [
        {"label": "Command Center",      "href": "/app"},
        {"label": "My Dashboard",        "href": "/my/AT"},
        {"label": "Alerts",              "href": "/alerts"},
        {"label": "Escalations",         "href": "/escalations"},
        {"label": "Watchlist",           "href": "/watchlist"},
    ],
    "pipeline": [
        {"label": "Deal Sourcing",       "href": "/source"},
        {"label": "Hospital Screener",   "href": "/screen"},
        {"label": "Predictive Screener", "href": "/predictive-screener"},
        {"label": "PE Intelligence",     "href": "/pe-intelligence"},
        {"label": "Deal Screening",      "href": "/deal-screening"},
        {"label": "Find Comps",          "href": "/find-comps"},
        {"label": "Conferences",         "href": "/conferences"},
    ],
    "library": [
        {"label": "Deals Library",       "href": "/deals-library"},
        {"label": "Methodology",         "href": "/methodology"},
        {"label": "Metric Glossary",     "href": "/metric-glossary"},
        {"label": "RCM Benchmarks",      "href": "/rcm-benchmarks"},
        {"label": "Data Catalog",        "href": "/data"},
        {"label": "Comparables",         "href": "/comparables"},
        {"label": "Market Rates",        "href": "/market-rates"},
    ],
    "research": [
        {"label": "Notes",               "href": "/notes"},
        {"label": "Sector Momentum",     "href": "/sector-momentum"},
        {"label": "IRR Dispersion",      "href": "/irr-dispersion"},
        {"label": "Hold Analysis",       "href": "/hold-analysis"},
        {"label": "Comparable Outcomes", "href": "/comparable-outcomes"},
        {"label": "Bear Cases",          "href": "/bear-cases"},
        {"label": "Reg Calendar",        "href": "/regulatory-calendar"},
        {"label": "Market Intel",        "href": "/market-intel"},
        {"label": "Corpus Backtest",     "href": "/corpus-backtest"},
        {"label": "Backtest",            "href": "/backtest"},
    ],
    "portfolio": [
        {"label": "Portfolio Map",       "href": "/portfolio/map"},
        {"label": "Heatmap",             "href": "/portfolio/heatmap"},
        {"label": "Risk Scan",           "href": "/portfolio/risk-scan"},
        {"label": "Portfolio Analytics", "href": "/portfolio-analytics"},
        {"label": "Sponsor Track Record","href": "/sponsor-track-record"},
        {"label": "Payer Intelligence",  "href": "/payer-intelligence"},
        {"label": "LP Update",           "href": "/lp-update"},
    ],
    # Diligence — RCM analyst playbook surfaces. The 24 pages here
    # span the four-phase diligence flow (intake → analysis → risk
    # → output). Heavy daily-driver workspace; partner can dip in
    # ad-hoc but the analyst lives here for a 3-week sprint.
    "diligence": [
        {"label": "Deal Profile",        "href": "/diligence/deal"},
        {"label": "Thesis Pipeline",     "href": "/diligence/thesis-pipeline"},
        {"label": "Checklist",           "href": "/diligence/checklist"},
        {"label": "Ingestion",           "href": "/diligence/ingest"},
        {"label": "Benchmarks",          "href": "/diligence/benchmarks"},
        {"label": "HCRIS X-Ray",         "href": "/diligence/hcris-xray"},
        {"label": "Root Cause",          "href": "/diligence/root-cause"},
        {"label": "Value Creation",      "href": "/diligence/value"},
        {"label": "Risk Workbench",      "href": "/diligence/risk-workbench?demo=steward"},
        {"label": "Counterfactual",      "href": "/diligence/counterfactual"},
        {"label": "Compare",             "href": "/diligence/compare"},
        {"label": "Bankruptcy Scan",     "href": "/screening/bankruptcy-survivor"},
        {"label": "QoE Memo",            "href": "/diligence/qoe-memo"},
        {"label": "Denial Predict",      "href": "/diligence/denial-prediction"},
        {"label": "Deal Autopsy",        "href": "/diligence/deal-autopsy"},
        {"label": "Physician Attrition", "href": "/diligence/physician-attrition"},
        {"label": "Provider Economics",  "href": "/diligence/physician-eu"},
        {"label": "Management",          "href": "/diligence/management"},
        {"label": "Deal MC",             "href": "/diligence/deal-mc"},
        {"label": "Exit Timing",         "href": "/diligence/exit-timing"},
        {"label": "Covenant Stress",     "href": "/diligence/covenant-stress"},
        {"label": "Bridge Audit",        "href": "/diligence/bridge-audit"},
        {"label": "Payer Stress",        "href": "/diligence/payer-stress"},
        {"label": "IC Packet",           "href": "/diligence/ic-packet"},
        {"label": "Engagements",         "href": "/engagements"},
    ],
}

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


# Cycle 29 — backward-compat aliases for pre-cycle-22 names. Defined
# AFTER the underlying functions so the rebind succeeds. 12+
# data_public pages import these names directly; renaming each call
# site is a future-cycle cleanup.
ck_fmt_num = ck_fmt_number
ck_fmt_pct = ck_fmt_percent


# ---------------------------------------------------------------------------
# Panel primitives
# ---------------------------------------------------------------------------

class SafeHtml(str):
    """Marker that says: this string is already safe HTML — skip escape.

    Kit helpers that emit pre-escaped markup (provenance tooltip,
    arrow links, etc.) return this so downstream call sites that pass
    the value through ``_esc`` don't double-escape the inner tags.
    """


def _esc(x) -> str:
    if x is None:
        return ""
    if isinstance(x, SafeHtml):
        return str(x)
    return _html.escape(str(x), quote=True)


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


def ck_section_header(
    title: str,
    eyebrow: Optional[str] = None,
    count: Optional[Any] = None,
    *,
    code: Optional[str] = None,
) -> str:
    """Editorial section header — eyebrow + title + optional count badge.

    Accepts the legacy 3-positional form
    ``ck_section_header(title, subtitle, count)`` used by ~30 page
    renderers carried over from the Bloomberg-era kit (the legacy
    ``subtitle`` argument is rendered as the editorial eyebrow row),
    plus the keyword form ``ck_section_header(title, eyebrow=..., count=...)``.
    ``code`` remains keyword-only for debug overlays.
    """
    eb = f'<div class="sc-eyebrow">{_esc(eyebrow)}</div>' if eyebrow else ""
    cd = f'<div class="ck-section-code">[{_esc(code)}]</div>' if code else ""
    count_html = (
        f'<span class="ck-section-count">{_esc(count)}</span>'
        if count is not None and count != "" else ""
    )
    return (
        '<header class="ck-section-header">'
        f'{eb}<h2 class="sc-h2">{_esc(title)}{count_html}</h2>{cd}'
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
    sub: Optional[str] = None,
    trend: Optional[str] = None,
    *,
    code: Optional[str] = None,
    unit: Optional[str] = None,    # legacy alias for ``sub``
    delta: Optional[str] = None,   # legacy alias for ``trend``
) -> str:
    """Editorial KPI block — label / value / optional sub / optional trend.

    Accepts the legacy 4-positional form ``ck_kpi_block(label, value,
    sub, trend)`` used by ~80 page renderers carried over from the
    Bloomberg-era kit, as well as the keyword form
    ``ck_kpi_block(label, value, sub=..., trend=...)``. Empty strings
    in ``sub`` / ``trend`` render as no-ops — legacy callers pass ``""``
    rather than ``None`` when a slot is unused. ``code`` remains
    keyword-only; only debug overlays use it.

    A handful of legacy callers used ``unit=``/``delta=`` instead of
    ``sub=``/``trend=`` (cycle 40-45 prod-bug fixes). Accept both so a
    forgotten file doesn't 500 the page — sub/trend take precedence
    when both are provided.
    """
    if sub is None and unit is not None:
        sub = unit
    if trend is None and delta is not None:
        trend = delta
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

    A small ``×`` close button in the corner hides the block; the
    dismissal is persisted in ``localStorage`` keyed off the eyebrow
    so it stays dismissed across page navigation.
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
    # Stable per-section key so dismissals don't bleed across pages
    # (a partner who hides /app's intro should still see /pipeline's).
    dismiss_key = _esc(eyebrow.lower().replace(" ", "-"))
    return (
        f'<div class="ck-section-intro" data-ck-intro="{dismiss_key}">'
        '<button type="button" class="ck-section-intro-dismiss" '
        'aria-label="Hide section intro" '
        f'data-ck-intro-dismiss="{dismiss_key}">&times;</button>'
        f'{ck_eyebrow(eyebrow, on_navy=on_navy)}'
        f'<h2>{h}</h2>'
        f'{body_html}'
        '</div>'
    )


def ck_arrow_link(text: str, href: str, *, on_navy: bool = False) -> str:
    """Teal "VIEW MORE ↗" arrow link, the primary editorial CTA."""
    cls = "ck-arrow on-navy" if on_navy else "ck-arrow"
    return f'<a class="{cls}" href="{_esc(href)}">{_esc(text)}</a>'


def ck_page_title(
    title: str,
    *,
    eyebrow: Optional[str] = None,
    meta: Optional[str] = None,
) -> str:
    """Editorial page title — small mono eyebrow, navy serif title,
    optional mono meta line. Sits at the top of a content page above
    KPIs / search / table to give the page a clear identity. Bigger
    than ck_section_intro's headline (which acts more like an article
    deck) — this is the equivalent of an H1.

    ``meta`` renders as a faint mono row beneath the title, useful for
    "655 deals · 99 sectors · sorted by entry_year desc" style page
    state without ballooning the title block.
    """
    eyebrow_html = (
        f'<div class="ck-eyebrow">{_esc(eyebrow)}</div>' if eyebrow else ""
    )
    meta_html = (
        f'<div class="ck-page-title-meta">{_esc(meta)}</div>' if meta else ""
    )
    return (
        '<header class="ck-page-title">'
        f'{eyebrow_html}'
        f'<h1>{_esc(title)}</h1>'
        f'{meta_html}'
        '</header>'
    )


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
    extra_hidden: Optional[Mapping[str, str]] = None,
) -> str:
    """Navy search hero with italic-serif label + circular submit
    + teal chevron-cut bottom-right corner. Mirrors the Chartis
    Insights page hero exactly. Drop above any content-listing
    page (``/library``, ``/research``, ``/notes``, ``/search``)
    so the partner's first read is the same as on chartis.com.

    ``extra_hidden`` round-trips other URL state (current filter
    selections etc.) through the search form so submitting the
    keyword input doesn't drop the active filter sidebar state.

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` pattern 01.
    """
    initial_attr = (
        f' value="{_esc(initial)}"' if initial else ""
    )
    hidden_html = ""
    if extra_hidden:
        hidden_html = "".join(
            f'<input type="hidden" name="{_esc(k)}" value="{_esc(v)}">'
            for k, v in extra_hidden.items() if v
        )
    return (
        '<section class="ck-search-hero">'
        '<div class="ck-search-hero-inner">'
        f'<span class="ck-search-hero-label">{_esc(label)}</span>'
        f'<form class="ck-search-hero-form" method="{_esc(method)}" '
        f'action="{_esc(action)}" role="search">'
        f'{hidden_html}'
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


def ck_filter_sidebar(
    *,
    groups: Sequence[Mapping[str, Any]],
    title: str = "Filter",
    form_action: Optional[str] = None,
    form_method: str = "GET",
    extra_hidden: Optional[Mapping[str, str]] = None,
    submit_label: Optional[str] = None,
    auto_submit: bool = True,
    more_threshold: int = 8,
) -> str:
    """Editorial filter sidebar — eyebrow rail with grouped checkbox
    or radio rows and a ``<details>`` 'More' expander when a group
    exceeds ``more_threshold`` options. Mirrors the chartis.com
    Insights left rail.

    Each group is a mapping with:
      - ``title`` (str) — group header label, e.g. ``"By sector"``
      - ``name`` (str) — input ``name`` attribute
      - ``input_type`` (str) — ``"radio"`` or ``"checkbox"``
        (defaults to ``"checkbox"``)
      - ``options`` (Sequence) — each ``{"label": str, "value": str,
        "checked": bool}``

    When ``form_action`` is provided the sidebar wraps in a ``<form>``
    so the partner can change facets without leaving the page; the
    inputs auto-submit on change unless ``submit_label`` is provided
    or ``auto_submit=False``. Pass ``extra_hidden`` to round-trip
    URL state that lives on a sibling form (e.g. the search hero's
    ``q`` parameter) so toggling a filter doesn't drop the keyword.

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` pattern 02.
    """
    title_html = f'<h2 class="ck-filter-rail-title">{_esc(title)}</h2>'

    auto_attr = (
        ' onchange="this.form.submit()"'
        if (form_action and auto_submit and not submit_label)
        else ""
    )

    def _render_li(opt: Mapping[str, Any], gtype: str, gname: str) -> str:
        ovalue = _esc(opt.get("value", ""))
        olabel = _esc(opt.get("label", ""))
        checked = " checked" if opt.get("checked") else ""
        return (
            '<li><label>'
            f'<input type="{gtype}" name="{gname}" '
            f'value="{ovalue}"{checked}{auto_attr}>'
            f'<span>{olabel}</span>'
            '</label></li>'
        )

    group_parts = []
    for grp in groups:
        gtitle = _esc(grp.get("title", ""))
        gname = _esc(grp.get("name", ""))
        gtype = grp.get("input_type", "checkbox")
        if gtype not in ("checkbox", "radio"):
            gtype = "checkbox"
        options = list(grp.get("options", []))
        head = options[:more_threshold]
        tail = options[more_threshold:]
        head_lis = "".join(_render_li(o, gtype, gname) for o in head)
        overflow_html = ""
        if tail:
            tail_lis = "".join(_render_li(o, gtype, gname) for o in tail)
            overflow_html = (
                '<details class="ck-filter-overflow">'
                '<summary>More</summary>'
                f'<ul class="ck-filter-list">{tail_lis}</ul>'
                '</details>'
            )
        group_parts.append(
            '<section class="ck-filter-group">'
            f'<header class="ck-filter-group-head">{gtitle}</header>'
            f'<ul class="ck-filter-list">{head_lis}</ul>'
            f'{overflow_html}'
            '</section>'
        )

    submit_html = (
        f'<button class="ck-filter-submit" type="submit">{_esc(submit_label)}</button>'
        if submit_label and form_action else ""
    )

    hidden_html = ""
    if extra_hidden and form_action:
        hidden_html = "".join(
            f'<input type="hidden" name="{_esc(k)}" value="{_esc(v)}">'
            for k, v in extra_hidden.items() if v
        )

    inner = f'{title_html}{"".join(group_parts)}{submit_html}'

    if form_action:
        return (
            '<aside class="ck-filter-rail">'
            f'<form method="{_esc(form_method)}" action="{_esc(form_action)}">'
            f'{hidden_html}{inner}'
            '</form>'
            '</aside>'
        )
    return f'<aside class="ck-filter-rail">{inner}</aside>'


def ck_results_header(
    *,
    count: Any,
    label: str = "Results",
    chips: Optional[Sequence[Mapping[str, str]]] = None,
    clear_all_href: Optional[str] = None,
) -> str:
    """Editorial N-RESULTS header with active-filter chips + clear-all.

    Mirrors the chartis.com/insights ``46 RESULTS`` row above the
    results list — serif count + caps RESULTS label + a row of chips
    showing active facets, each chip an anchor that drops just that
    one facet on click. ``clear_all_href`` should point at the same
    page with all filter params stripped so partner can reset to the
    full corpus in one click. Drop in below ck_filter_sidebar +
    ck_search_hero on /library, /research, /notes for the full
    Insights pattern triplet.

    Each chip dict supports:
      - ``label`` (str) — visible chip text, e.g. ``"Behavioral Health"``
      - ``remove_href`` (str) — anchor href that drops the facet

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` pattern 03.
    """
    chips_html = ""
    if chips:
        chip_parts = []
        for ch in chips:
            chip_parts.append(
                f'<a class="ck-chip" href="{_esc(ch.get("remove_href", "#"))}">'
                f'{_esc(ch.get("label", ""))} '
                '<span class="ck-chip-x" aria-hidden="true">×</span>'
                '<span class="sr-only"> remove filter</span>'
                '</a>'
            )
        clear_html = (
            f'<a class="ck-arrow" href="{_esc(clear_all_href)}">Clear all</a>'
            if clear_all_href else ""
        )
        chips_html = (
            '<div class="ck-results-chips">'
            f'{"".join(chip_parts)}{clear_html}'
            '</div>'
        )
    return (
        '<header class="ck-results-header">'
        '<div class="ck-results-count">'
        f'<span class="ck-results-num sc-num">{_esc(count)}</span>'
        f'<span class="ck-results-label">{_esc(label)}</span>'
        '</div>'
        f'{chips_html}'
        '</header>'
    )


def render_insights_page(
    *,
    action: str,
    state: Mapping[str, str],
    facets: Sequence[Mapping[str, Any]],
    count: Any,
    body_html: str,
    title: str,
    keyword_name: str = "q",
    keyword_label: str = "Search",
    keyword_placeholder: str = "Keyword",
    intro: Optional[Mapping[str, Any]] = None,
    section_title: Optional[str] = None,
    section_eyebrow: Optional[str] = None,
    count_label: str = "Results",
    active_nav: Optional[str] = None,
    subtitle: Optional[str] = None,
    breadcrumbs: Optional[Sequence[Any]] = None,
    chip_label_overrides: Optional[Mapping[str, Any]] = None,
    extra_chips: Optional[Sequence[Mapping[str, str]]] = None,
    omit_auto_chips: Optional[Sequence[str]] = None,
    prelude_html: str = "",
    prelude_position: str = "after",
) -> str:
    """Compose the chartis Insights triplet around a body of items.

    Replaces the ~200 LOC of triplet wiring that cycles 6, 8, 9
    each shipped (search hero + filter sidebar + results header +
    chip URL building + extra_hidden round-trip + Clear all)
    with one call. The caller pre-renders the items as
    ``body_html`` (table / cards / list) and passes:

      - ``action``    — page URL, e.g. ``"/library"``
      - ``state``     — current URL params as a ``{name: value}``
                        dict; empty values are dropped
      - ``facets``    — list of facet specs, each a mapping with
                        ``name`` / ``label`` / ``input_type`` /
                        ``options`` per ``ck_filter_sidebar``
      - ``count``     — the row count to surface in the results
                        header
      - ``intro``     — optional ``{eyebrow, headline, ...}`` kwargs
                        passed to ``ck_section_intro``

    For each active facet (state value present), a chip is added
    to the results header whose ``remove_href`` reconstructs the
    URL with that facet stripped. The keyword (default ``q``)
    becomes a chip too when set, with a wrapping ``"value"``
    label. ``chip_label_overrides`` lets the caller swap the
    default chip label for a specific facet — e.g. /notes uses
    ``deal: hca-001`` for the deal-id chip rather than the bare
    value.

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` patterns 01-03 composed.
    """
    facet_names = {f["name"] for f in facets}
    overrides = chip_label_overrides or {}
    skip_auto = set(omit_auto_chips or ())

    # Build extra_hidden for the search hero — every state field
    # except the keyword itself round-trips so submitting q
    # preserves active filters.
    state_except_kw = {
        k: v for k, v in state.items()
        if k != keyword_name and v
    }
    search_hero = ck_search_hero(
        action=action,
        name=keyword_name,
        initial=state.get(keyword_name, ""),
        label=keyword_label,
        placeholder=keyword_placeholder,
        extra_hidden=state_except_kw,
    )

    # Filter sidebar — caller provides the facet groups directly;
    # extra_hidden round-trips q (and any non-facet state).
    state_except_facets = {
        k: v for k, v in state.items()
        if k not in facet_names and v
    }
    filter_rail = ck_filter_sidebar(
        title="Filter",
        form_action=action,
        groups=list(facets),
        extra_hidden=state_except_facets,
    )

    # Build chips: one per active facet + one for active keyword.
    # Each chip's remove_href reconstructs ``action?...`` with that
    # one field stripped, so partner can drop facets one at a time.
    chips: List[Mapping[str, str]] = []
    nonempty = {k: v for k, v in state.items() if v}

    def _url_omit(name: str) -> str:
        kept = [(k, v) for k, v in nonempty.items() if k != name]
        if not kept:
            return action
        import urllib.parse as _up
        return action + "?" + _up.urlencode(kept)

    for name, value in nonempty.items():
        if name in skip_auto:
            # Caller supplies its own chip(s) for this name via
            # ``extra_chips`` (e.g. multi-value tag filters where
            # each tag drops independently — the auto-builder can't
            # know how to drop one tag from a list-valued URL state).
            continue
        if name == keyword_name:
            label = f'"{value}"'
        elif name in facet_names or name in overrides:
            # Either a facet or a name with an explicit chip-label
            # override (e.g. /notes' ``deal_id`` — not a sidebar
            # facet but partner sees it as an active scope chip).
            override = overrides.get(name)
            if callable(override):
                label = override(value)
            elif override:
                label = override
            else:
                label = value
        else:
            # Non-facet state (e.g. sort_by) doesn't surface as a
            # chip — partner controls those via column headers,
            # not the chip row.
            continue
        chips.append({
            "label": label,
            "remove_href": _url_omit(name),
        })

    # Caller-supplied chips for cases the auto-builder can't handle
    # (multi-value facets, computed labels, etc.). Appended after
    # auto-chips so the visual order is "main facets → extras → q".
    if extra_chips:
        chips.extend(extra_chips)

    results_head = ck_results_header(
        count=count,
        label=count_label,
        chips=chips or None,
        clear_all_href=action if chips else None,
    )

    intro_html = ""
    if intro:
        intro_html = ck_section_intro(**intro)

    section_html = ""
    if section_title:
        section_html = ck_section_header(
            section_title, eyebrow=section_eyebrow,
        )

    rail_layout = (
        '<div class="ck-rail-layout">'
        f'{filter_rail}'
        '<div class="ck-rail-content">'
        f'{section_html}{results_head}{body_html}'
        '</div>'
        '</div>'
    )

    # ``prelude_html`` is full-width content the caller wants between
    # the search hero and the rail layout (default) — e.g. a KPI
    # strip + explainer card. Set ``prelude_position="before"`` to
    # render it above the search bar instead, which makes the search
    # feel like part of one continuous header that flows into the
    # results table.
    if prelude_position == "before":
        full_body = (
            intro_html + prelude_html + search_hero + rail_layout
        )
    else:
        full_body = (
            intro_html + search_hero + prelude_html + rail_layout
        )

    return chartis_shell(
        full_body,
        title=title,
        active_nav=active_nav,
        subtitle=subtitle,
        breadcrumbs=breadcrumbs,
    )


def ck_data_cell(
    value: str,
    *,
    align: str = "left",
    mono: bool = False,
    tone: Optional[str] = None,
    weight: Optional[int] = None,
    is_header: bool = False,
) -> str:
    """One styled ``<td>`` (or ``<th>``) for the data_public table
    archetype. Replaces the ~1200 hand-rolled inline-styled cells
    that the cycle-22 audit identified as the dominant inline-style
    source.

    Each cell is rendered with utility classes:
      - ``ck-cell``               — base padding + 11px font
      - ``ck-cell-mono``          — JetBrains Mono + tabular-nums
      - ``ck-cell-r`` / ``ck-cell-c`` — right / center alignment
      - ``tone-dim`` / ``tone-pos`` / ``tone-neg`` / ``tone-acc`` —
        dim / positive / negative / accent text color
      - ``ck-cell-w-700`` / ``ck-cell-w-600`` — weight modifiers

    The caller supplies ``value`` already pre-formatted (with $, %,
    x suffixes etc.) — the cell wrapper does not format. For
    auto-formatted cells use the existing ``ck_fmt_*`` helpers.

    Args:
      value: HTML-safe pre-formatted display string.
      align: ``left`` / ``right`` / ``center``.
      mono: Use mono font + tabular-nums.
      tone: Optional ``dim`` / ``pos`` / ``neg`` / ``acc``.
      weight: Optional 600 or 700 (CSS font-weight).
      is_header: Render as ``<th>`` instead of ``<td>``.
    """
    cls_parts = ["ck-cell"]
    if is_header:
        # Header cells get the cycle-27 ck-data-table-head class
        # which carries: caps + 10px + letter-spacing + border-bottom.
        # Lets ck_data_cell(..., is_header=True) replace the
        # ~720 hand-rolled <th style="..."> attributes that the
        # cycle-30 audit identified as the next inline-style hotspot.
        cls_parts.append("ck-data-table-head")
    if mono:
        cls_parts.append("ck-cell-mono")
    if align == "right":
        cls_parts.append("ck-cell-r")
    elif align == "center":
        cls_parts.append("ck-cell-c")
    if tone in ("dim", "pos", "neg", "acc"):
        cls_parts.append(f"tone-{tone}")
    if weight in (600, 700):
        cls_parts.append(f"ck-cell-w-{weight}")
    tag = "th" if is_header else "td"
    cls = " ".join(cls_parts)
    return f'<{tag} class="{cls}">{value}</{tag}>'


def ck_data_table(
    *,
    headers: Sequence[Mapping[str, str]],
    rows_html: str,
    scrollable: bool = True,
) -> str:
    """Wrap an editorial data table in chartis-grade chrome.

    Cycle 27 helper for the second-most-common inline-style cluster
    (after the cycle 22 cell migration): the table container,
    scroll wrapper, header row, and alternating-row background
    boilerplate that ~120 data_public pages still hand-roll. Each
    page emits ~5 inline-styled wrappers per table; this helper
    replaces all of them with class-based markup.

    Caller supplies the body via ``rows_html`` — typically a string
    of ``<tr>`` elements built from ``ck_data_cell`` calls in the
    page's render loop (so each row's tone-coloring stays at the
    caller's discretion). The helper handles the surrounding chrome:
    scroll wrapper, ``<table>`` + class, ``<thead>`` row, alternating
    body-row backgrounds via CSS.

    Args:
      headers: list of ``{"label": "Deal", "align": "left"}`` dicts.
        ``align`` ∈ ``left`` / ``right`` / ``center`` (default
        ``left``).
      rows_html: pre-rendered ``<tr>...</tr>`` strings concatenated.
        The helper wraps these in ``<tbody>``.
      scrollable: wrap in ``<div class="ck-data-table-scroll">``.
        Set False to skip the wrapper for inline / non-overflow
        contexts.
    """
    head_cells = []
    for h in headers:
        align = h.get("align", "left")
        align_cls = (
            f" ck-cell-r" if align == "right"
            else f" ck-cell-c" if align == "center"
            else ""
        )
        head_cells.append(
            f'<th class="ck-cell ck-data-table-head{align_cls}">'
            f'{_esc(h.get("label", ""))}</th>'
        )
    head_html = "<thead><tr>" + "".join(head_cells) + "</tr></thead>"
    body_html = f"<tbody>{rows_html}</tbody>"
    table = (
        '<table class="ck-data-table">'
        + head_html + body_html + "</table>"
    )
    if scrollable:
        return f'<div class="ck-data-table-scroll">{table}</div>'
    return table


def ck_provenance_tooltip(
    label: str,
    value: str,
    *,
    explainer: Optional[str] = None,
    graph: Optional[Any] = None,
    metric_key: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Wrap a partner-facing value in an "explain this number" hover.

    Cycle 34 entry point — the kit-level helper that pages should
    call. Two paths:

    1. ``explainer`` provided: renders a simple hover card with the
       methodology string. Useful for any page (data_public,
       editorial ports) where each numeric has a fixed "what it
       means / where it came from" sentence. No per-deal graph
       needed.

    2. ``graph`` + ``metric_key`` provided: defers to
       ``rcm_mc/ui/_provenance_tooltip.py::provenance_tooltip``
       which pulls the explanation from a real provenance graph
       (Phase 4C of the v3 transformation).

    With neither, the value is returned escape-safely without a
    tooltip — same fall-through pattern as the existing helper.

    Args:
        label: User-visible name of the metric (HTML-escaped).
        value: Pre-formatted display string (HTML-escaped).
        explainer: Optional plain-text methodology / source line.
            When set, a hover card with this text appears on the
            value's info icon.
        graph: Optional provenance graph for graph-driven mode.
        metric_key: Optional metric key for graph-driven mode.
        inject_css: When True, inline the tooltip <style> on first
            call. Pass False on subsequent calls in one render.
    """
    if graph is not None and metric_key:
        # Defer to the graph-driven implementation. This is the
        # Phase 4C path used by /alerts, /my/<owner>, etc.
        from rcm_mc.ui._provenance_tooltip import provenance_tooltip
        return provenance_tooltip(
            label, value,
            graph=graph, metric_key=metric_key,
            inject_css=inject_css,
        )
    # Honour SafeHtml: callers that pass already-escaped markup (e.g.
    # `<span class="mn neg">14.8%</span>`) shouldn't have it re-
    # escaped into literal text on the page.
    safe_value = (
        str(value) if isinstance(value, SafeHtml)
        else _html.escape(value)
    )
    if not explainer:
        return SafeHtml(safe_value)
    safe_label = _html.escape(label)
    safe_explainer = _html.escape(explainer)
    css = ""
    if inject_css:
        css = (
            '<style>'
            '.ck-prov-tt{position:relative;display:inline-flex;'
            'align-items:baseline;gap:4px;}'
            '.ck-prov-tt-icon{display:inline-flex;align-items:center;'
            'justify-content:center;width:14px;height:14px;border-radius:50%;'
            'border:1px solid var(--sc-text-faint);'
            'color:var(--sc-text-faint);font-size:10px;font-weight:600;'
            'cursor:help;font-family:var(--sc-mono);}'
            '.ck-prov-tt-card{position:absolute;left:0;top:calc(100% + 6px);'
            'min-width:240px;max-width:340px;padding:12px 14px;'
            'background:#fff;border:1px solid var(--sc-rule);'
            'box-shadow:var(--sc-shadow-2);border-radius:2px;'
            'font-family:var(--sc-sans);font-size:12px;line-height:1.5;'
            'color:var(--sc-text);z-index:50;'
            'visibility:hidden;opacity:0;transition:opacity 0.1s;}'
            '.ck-prov-tt:hover .ck-prov-tt-card,'
            '.ck-prov-tt:focus-within .ck-prov-tt-card{visibility:visible;'
            'opacity:1;}'
            '.ck-prov-tt-label{font-family:var(--sc-mono);font-size:11px;'
            'font-weight:600;letter-spacing:0.06em;text-transform:uppercase;'
            'color:var(--sc-text-dim);margin-bottom:4px;display:block;}'
            '</style>'
        )
    return SafeHtml(
        f'{css}'
        '<span class="ck-prov-tt" tabindex="0">'
        f'<span class="ck-prov-tt-value">{safe_value}</span>'
        '<span class="ck-prov-tt-icon" aria-hidden="true">i</span>'
        '<span class="ck-prov-tt-card" role="tooltip">'
        f'<span class="ck-prov-tt-label">{safe_label}</span>'
        f'{safe_explainer}'
        '</span>'
        '</span>'
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

# Default Cmd+K palette — the full platform tools index. Lets a
# partner jump to ANY surface (the long-tail of ~70 analytic
# tools beyond the editorial top-nav) without trawling URLs.
# Every entry must resolve to a real route; verified by the audit
# in tests/test_palette_routes.py.
_DEFAULT_PALETTE_MODULES = [
    # Home + ops
    {"id": "home",        "title": "Command Center",       "route": "/app"},
    {"id": "my",          "title": "My Dashboard",         "route": "/my/AT"},
    {"id": "alerts",      "title": "Alerts",               "route": "/alerts"},
    {"id": "escalations", "title": "Escalations",          "route": "/escalations"},
    {"id": "watchlist",   "title": "Watchlist",            "route": "/watchlist"},
    # Pipeline / sourcing
    {"id": "pipeline",    "title": "Pipeline",             "route": "/pipeline"},
    {"id": "source",      "title": "Deal Sourcing",        "route": "/source"},
    {"id": "screen",      "title": "Hospital Screener",    "route": "/screen"},
    {"id": "predictive",  "title": "Predictive Screener",  "route": "/predictive-screener"},
    {"id": "pe-intel",    "title": "PE Intelligence",      "route": "/pe-intelligence"},
    {"id": "deal-screen", "title": "Deal Screening",       "route": "/deal-screening"},
    {"id": "find-comps",  "title": "Find Comps",           "route": "/find-comps"},
    {"id": "conferences", "title": "Conferences",          "route": "/conferences"},
    # Diligence playbook
    {"id": "deal-profile",  "title": "Deal Profile",       "route": "/diligence/deal"},
    {"id": "thesis-pipe",   "title": "Thesis Pipeline",    "route": "/diligence/thesis-pipeline"},
    {"id": "checklist",     "title": "Diligence Checklist","route": "/diligence/checklist"},
    {"id": "ingest",        "title": "Ingestion",          "route": "/diligence/ingest"},
    {"id": "benchmarks",    "title": "Benchmarks",         "route": "/diligence/benchmarks"},
    {"id": "hcris-xray",    "title": "HCRIS X-Ray",        "route": "/diligence/hcris-xray"},
    {"id": "root-cause",    "title": "Root Cause",         "route": "/diligence/root-cause"},
    {"id": "value-create",  "title": "Value Creation",     "route": "/diligence/value"},
    {"id": "risk-bench",    "title": "Risk Workbench",     "route": "/diligence/risk-workbench?demo=steward"},
    {"id": "counterfact",   "title": "Counterfactual",     "route": "/diligence/counterfactual"},
    {"id": "compare",       "title": "Compare Deals",      "route": "/diligence/compare"},
    {"id": "bankruptcy",    "title": "Bankruptcy Scan",    "route": "/screening/bankruptcy-survivor"},
    {"id": "qoe-memo",      "title": "QoE Memo",           "route": "/diligence/qoe-memo"},
    {"id": "denial-pred",   "title": "Denial Prediction",  "route": "/diligence/denial-prediction"},
    {"id": "deal-autopsy",  "title": "Deal Autopsy",       "route": "/diligence/deal-autopsy"},
    {"id": "phys-attr",     "title": "Physician Attrition","route": "/diligence/physician-attrition"},
    {"id": "phys-eu",       "title": "Provider Economics", "route": "/diligence/physician-eu"},
    {"id": "management",    "title": "Management",         "route": "/diligence/management"},
    {"id": "deal-mc",       "title": "Deal Monte Carlo",   "route": "/diligence/deal-mc"},
    {"id": "exit-timing",   "title": "Exit Timing",        "route": "/diligence/exit-timing"},
    {"id": "covenant-stress","title":"Covenant Stress",    "route": "/diligence/covenant-stress"},
    {"id": "bridge-audit",  "title": "Bridge Audit",       "route": "/diligence/bridge-audit"},
    {"id": "payer-stress",  "title": "Payer Stress",       "route": "/diligence/payer-stress"},
    {"id": "ic-packet",     "title": "IC Packet",          "route": "/diligence/ic-packet"},
    {"id": "engagements",   "title": "Engagements",        "route": "/engagements"},
    # Library / reference
    {"id": "library",       "title": "Deals Library",      "route": "/library"},
    {"id": "deals-library", "title": "Deals Library (alt)","route": "/deals-library"},
    {"id": "methodology",   "title": "Methodology",        "route": "/methodology"},
    {"id": "metric-glos",   "title": "Metric Glossary",    "route": "/metric-glossary"},
    {"id": "rcm-bench",     "title": "RCM Benchmarks",     "route": "/rcm-benchmarks"},
    {"id": "data",          "title": "Data Catalog",       "route": "/data"},
    {"id": "comparables",   "title": "Comparables",        "route": "/comparables"},
    {"id": "market-rates",  "title": "Market Rates",       "route": "/market-rates"},
    # Research
    {"id": "research",      "title": "Research Hub",       "route": "/research"},
    {"id": "notes",         "title": "Notes",              "route": "/notes"},
    {"id": "sector-mom",    "title": "Sector Momentum",    "route": "/sector-momentum"},
    {"id": "irr-disp",      "title": "IRR Dispersion",     "route": "/irr-dispersion"},
    {"id": "hold-analysis", "title": "Hold Analysis",      "route": "/hold-analysis"},
    {"id": "comp-outcomes", "title": "Comparable Outcomes","route": "/comparable-outcomes"},
    {"id": "bear-cases",    "title": "Bear Cases",         "route": "/bear-cases"},
    {"id": "reg-cal",       "title": "Regulatory Calendar","route": "/regulatory-calendar"},
    {"id": "market-intel",  "title": "Market Intelligence","route": "/market-intel"},
    {"id": "corpus-back",   "title": "Corpus Backtest",    "route": "/corpus-backtest"},
    {"id": "backtest",      "title": "Backtest",           "route": "/backtest"},
    # Portfolio
    {"id": "portfolio",     "title": "Portfolio",          "route": "/portfolio"},
    {"id": "port-map",      "title": "Portfolio Map",      "route": "/portfolio/map"},
    {"id": "port-heat",     "title": "Portfolio Heatmap",  "route": "/portfolio/heatmap"},
    {"id": "port-risk",     "title": "Portfolio Risk Scan","route": "/portfolio/risk-scan"},
    {"id": "port-mon",      "title": "Portfolio Monitor",  "route": "/portfolio/monitor"},
    {"id": "port-an",       "title": "Portfolio Analytics","route": "/portfolio-analytics"},
    {"id": "sponsor-tr",    "title": "Sponsor Track Record","route": "/sponsor-track-record"},
    {"id": "payer-intel",   "title": "Payer Intelligence", "route": "/payer-intelligence"},
    {"id": "lp-update",     "title": "LP Update",          "route": "/lp-update"},
    # Admin / system
    {"id": "audit",         "title": "Audit Log",          "route": "/audit"},
    {"id": "users",         "title": "Users",              "route": "/users"},
    {"id": "import",        "title": "Import Deal",        "route": "/import"},
]


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

# Two stylesheets:
#   chartis_tokens.css — CSS custom-property tokens (--sc-navy, --cad-bg, ...)
#   v3/chartis.css — actual class definitions (.cad-card, .cad-kpi, .cad-btn,
#                    .cad-table, etc.) that ~25 pages still emit. Without
#                    this second link, those pages fall back to unstyled
#                    browser defaults and look broken under the editorial
#                    chrome wrapper.
_CSS_LINK = (
    '<link rel="stylesheet" href="/static/chartis_tokens.css">'
    '<link rel="stylesheet" href="/static/v3/chartis.css">'
)

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
  .ck-section-count { display:inline-block; font-family:var(--sc-mono); font-size:13px; font-weight:500; color:var(--sc-text-faint); margin-left:12px; vertical-align:baseline; letter-spacing:0.04em; }

  /* Top bar — navy + white + teal accent rule, mirrors chartis.com */
  .ck-topbar { position:sticky; top:0; z-index:50; background:var(--sc-navy); border-bottom:2px solid var(--sc-teal); }
  .ck-topbar-inner { display:flex; align-items:center; gap:var(--sc-s-6); padding:18px var(--sc-s-7); max-width:1720px; margin:0 auto; }
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
  .ck-user-chip { width:34px; height:34px; border-radius:50%; background:var(--sc-teal); color:var(--sc-navy); display:flex; align-items:center; justify-content:center; font-family:var(--sc-sans); font-weight:700; font-size:12px; letter-spacing:0.04em; cursor:pointer; border:0; padding:0; }
  .ck-user-chip:hover { background:var(--sc-teal-2,var(--sc-teal)); }
  .ck-search-form { margin:0; }
  .ck-user-menu { position:relative; }
  .ck-user-dropdown { position:absolute; top:calc(100% + 10px); right:0; min-width:200px; background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-2,0 8px 24px rgba(11,32,55,0.14)); border-radius:2px; padding:6px 0; z-index:60; }
  .ck-user-dropdown[hidden] { display:none !important; }
  .ck-user-dropdown-item { display:block; width:100%; text-align:left; padding:9px 16px; font-family:var(--sc-sans); font-size:13px; color:var(--sc-text); text-decoration:none; background:transparent; border:0; cursor:pointer; letter-spacing:0; text-transform:none; font-weight:500; }
  .ck-user-dropdown-item:hover { background:var(--sc-bone,#f5f1ea); color:var(--sc-teal-ink); }
  .ck-user-dropdown-divider { height:1px; background:var(--sc-rule); margin:4px 0; }
  .ck-user-recent { padding:6px 0 4px; border-bottom:1px solid var(--sc-rule); margin-bottom:4px; }
  .ck-user-recent[hidden] { display:none !important; }
  .ck-user-recent-head { padding:4px 16px 6px; font-family:var(--sc-mono); font-size:10px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint); }
  .ck-user-recent-item { display:flex; flex-direction:column; padding:6px 16px; text-decoration:none; color:var(--sc-text); font-size:13px; }
  .ck-user-recent-item:hover { background:var(--sc-bone); color:var(--sc-teal-ink); }
  .ck-user-recent-name { font-weight:500; color:var(--sc-navy); }
  .ck-user-recent-item:hover .ck-user-recent-name { color:var(--sc-teal-ink); }
  .ck-user-recent-slug { font-family:var(--sc-mono); font-size:10.5px; color:var(--sc-text-faint); letter-spacing:0.04em; }
  .ck-user-dropdown-form { margin:0; }
  .ck-user-dropdown-logout { color:var(--sc-negative,#c0392b); }
  /* Sub-nav rail — parchment strip with section pills, sits sticky
   * just below the navy topbar. Lets a partner click into a common
   * second-level page (Alerts, Heatmap, Find Comps, etc.) without
   * landing on a section index first. */
  .ck-subnav { background:var(--sc-bone,#f5f1ea); border-bottom:1px solid var(--sc-rule); position:sticky; top:60px; z-index:40; }
  .ck-subnav-inner { display:flex; gap:var(--sc-s-5); align-items:center; padding:10px var(--sc-s-7); max-width:1720px; margin:0 auto; overflow-x:auto; }
  .ck-subnav-link { font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.04em; color:var(--sc-text-dim); text-decoration:none; padding:5px 10px; border-radius:2px; white-space:nowrap; transition:color 0.15s, background 0.15s; }
  .ck-subnav-link:hover { color:var(--sc-teal-ink); background:#fff; }
  .ck-subnav-link.active { color:var(--sc-navy); background:#fff; box-shadow:inset 0 -2px 0 var(--sc-teal); }
  .ck-breadcrumbs { display:flex; gap:8px; padding:14px var(--sc-s-7); max-width:1720px; margin:0 auto; font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.08em; text-transform:uppercase; border-bottom:1px solid var(--sc-rule); }
  .ck-breadcrumbs a { color:var(--sc-text-dim); text-decoration:none; }
  .ck-breadcrumbs a:hover { color:var(--sc-teal-ink); }
  .ck-breadcrumbs .sep { color:var(--sc-rule-2); }

  /* Editorial primitives — eyebrow + section intro + arrow link */
  .ck-eyebrow { display:inline-flex; align-items:center; gap:12px; font-family:var(--sc-mono); font-size:11px; font-weight:600; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-dim); }
  .ck-eyebrow::before { content:''; display:inline-block; width:24px; height:2px; background:var(--sc-teal); }
  .ck-eyebrow.on-navy { color:var(--sc-on-navy-dim); }
  .ck-eyebrow.on-navy::before { background:var(--sc-teal); }
  .ck-section-intro { position:relative; margin:var(--sc-s-6) 0 var(--sc-s-5); padding-right:32px; }
  .ck-section-intro h2 { font-family:var(--sc-serif); font-weight:400; font-size:clamp(20px, 2.2vw, 26px); line-height:1.2; letter-spacing:-0.01em; color:var(--sc-navy); margin:var(--sc-s-3) 0 0; max-width:32ch; }
  .ck-section-intro h2 em { font-style:italic; font-weight:400; color:var(--sc-teal-ink); }
  .ck-section-intro .ck-section-body { font-family:var(--sc-serif); font-size:14px; line-height:1.55; color:var(--sc-text-dim); margin-top:var(--sc-s-3); max-width:64ch; }
  .ck-section-intro-dismiss { position:absolute; top:0; right:0; width:24px; height:24px; padding:0; background:transparent; border:0; color:var(--sc-text-faint); font-size:20px; line-height:1; cursor:pointer; border-radius:50%; transition:color 0.12s, background 0.12s; }
  .ck-section-intro-dismiss:hover { color:var(--sc-navy); background:var(--sc-bone,#ece6db); }
  .ck-section-intro[hidden] { display:none !important; }
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
  /* Page title — H1-equivalent header for content pages
   * (/library, /research, /pipeline). Sits above KPIs and search. */
  .ck-page-title { margin:0 0 var(--sc-s-6); display:flex; flex-direction:column; gap:8px; }
  .ck-page-title h1 { font-family:var(--sc-serif); font-weight:400; font-size:clamp(28px, 3.4vw, 40px); line-height:1.1; letter-spacing:-0.015em; color:var(--sc-navy); margin:0; }
  .ck-page-title h1 em { font-style:italic; font-weight:400; color:var(--sc-teal-ink); }
  .ck-page-title-meta { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.08em; text-transform:uppercase; }

  /* Search hero — full-bleed navy panel with italic-serif label and
   * teal chevron. Sits in the page-header stack, between the KPI
   * strip (above) and the filter rail + table (below). */
  .ck-search-hero { position:relative; background:var(--sc-navy); color:var(--sc-on-navy); padding:48px 0 56px; margin:0 0 var(--sc-s-7); overflow:hidden; }
  .ck-search-hero-inner { max-width:1720px; margin:0 auto; padding:0 var(--sc-s-7); display:flex; align-items:baseline; gap:var(--sc-s-7); }
  .ck-search-hero-label { font-family:var(--sc-serif); font-size:36px; font-weight:400; font-style:italic; letter-spacing:-0.01em; color:var(--sc-on-navy); flex-shrink:0; }
  .ck-search-hero-form { flex:1; display:flex; align-items:center; gap:14px; border-bottom:1px solid var(--sc-on-navy-dim); padding-bottom:8px; transition:border-color 0.15s; }
  .ck-search-hero-form:focus-within { border-bottom-color:var(--sc-teal); }
  .ck-search-hero-input { flex:1; background:transparent; border:0; font-family:var(--sc-serif); font-size:22px; color:var(--sc-on-navy); padding:8px 0; outline:none; min-width:0; }
  .ck-search-hero-input::placeholder { color:var(--sc-on-navy-faint); font-style:italic; }
  .ck-search-hero-submit { background:transparent; border:1px solid var(--sc-on-navy-dim); border-radius:50%; width:36px; height:36px; display:inline-flex; align-items:center; justify-content:center; color:var(--sc-on-navy); cursor:pointer; flex-shrink:0; transition:color 0.15s, border-color 0.15s; }
  .ck-search-hero-submit:hover { color:var(--sc-teal); border-color:var(--sc-teal); }
  .ck-search-hero-chevron { position:absolute; right:0; bottom:0; width:0; height:0; border-style:solid; border-width:0 0 64px 64px; border-color:transparent transparent var(--sc-teal) transparent; pointer-events:none; }

  /* Filter sidebar — chartis.com/insights left rail. Eyebrow-style
   * group headers, radio/checkbox rows, progressive-disclosure More
   * expander when a group has more than ~8 options. Pairs with
   * ck-search-hero (above) and ck-rail-layout (below) for the full
   * Insights triplet on /library, /research, /notes. */
  .ck-rail-layout { display:grid; grid-template-columns:240px 1fr; gap:var(--sc-s-7); align-items:start; margin:0 0 var(--sc-s-6); }
  @media (max-width: 880px) { .ck-rail-layout { grid-template-columns:1fr; } }
  .ck-filter-rail { font-family:var(--sc-sans); position:sticky; top:88px; }
  .ck-filter-rail form { margin:0; }
  .ck-filter-rail-title { font-family:var(--sc-mono); font-size:11px; font-weight:600; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-dim); margin:0 0 var(--sc-s-5); display:flex; align-items:center; gap:12px; }
  .ck-filter-rail-title::before { content:''; display:inline-block; width:24px; height:2px; background:var(--sc-teal); flex-shrink:0; }
  .ck-filter-group { margin:0 0 var(--sc-s-6); border-top:1px solid var(--sc-rule); padding-top:var(--sc-s-4); }
  .ck-filter-group:first-of-type { border-top:0; padding-top:0; }
  .ck-filter-group-head { font-family:var(--sc-sans); font-size:11px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-navy); margin:0 0 var(--sc-s-3); }
  .ck-filter-list { list-style:none; padding:0; margin:0; }
  .ck-filter-list li { padding:5px 0; }
  .ck-filter-list label { display:flex; align-items:center; gap:8px; cursor:pointer; font-family:var(--sc-sans); font-size:13px; line-height:1.35; color:var(--sc-text); }
  .ck-filter-list label:hover { color:var(--sc-teal-ink); }
  .ck-filter-list input[type="radio"], .ck-filter-list input[type="checkbox"] { accent-color:var(--sc-teal); cursor:pointer; flex-shrink:0; margin:0; }
  .ck-filter-overflow { margin-top:4px; }
  .ck-filter-overflow > summary { font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:var(--sc-teal-ink); cursor:pointer; padding:6px 0; list-style:none; outline:none; }
  .ck-filter-overflow > summary::-webkit-details-marker { display:none; }
  .ck-filter-overflow > summary::after { content:' \\25BC'; font-size:9px; margin-left:4px; }
  .ck-filter-overflow[open] > summary::after { content:' \\25B2'; }
  .ck-filter-overflow > summary:hover { color:var(--sc-navy); }
  .ck-filter-submit { font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; padding:8px 14px; border:1px solid var(--sc-navy); background:var(--sc-navy); color:var(--sc-on-navy); border-radius:2px; cursor:pointer; margin-top:var(--sc-s-4); width:100%; transition:background 0.15s, color 0.15s; }
  .ck-filter-submit:hover { background:var(--sc-teal); border-color:var(--sc-teal); color:var(--sc-navy); }

  /* Results header — N RESULTS + active-filter chips + Clear all.
   * Sits between the filter sidebar / search hero and the results
   * table on /library, /research, /notes. Mirrors chartis.com/insights. */
  .ck-results-header { display:flex; align-items:baseline; justify-content:space-between; gap:var(--sc-s-5); margin:0 0 var(--sc-s-4); padding-bottom:var(--sc-s-3); border-bottom:1px solid var(--sc-rule); flex-wrap:wrap; }
  .ck-results-count { font-family:var(--sc-serif); font-weight:500; color:var(--sc-navy); display:inline-flex; align-items:baseline; gap:10px; }
  .ck-results-num { font-size:28px; font-variant-numeric:tabular-nums; letter-spacing:-0.01em; }
  .ck-results-label { font-family:var(--sc-mono); font-size:11px; font-weight:600; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-dim); }
  .ck-results-chips { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .ck-chip { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; background:var(--sc-bone); border:1px solid var(--sc-rule); border-radius:14px; font-family:var(--sc-sans); font-size:12px; color:var(--sc-text); text-decoration:none; transition:background 0.15s, border-color 0.15s, color 0.15s; }
  .ck-chip:hover { background:#fff; border-color:var(--sc-teal); color:var(--sc-navy); }
  .ck-chip-x { font-size:14px; line-height:1; color:var(--sc-text-faint); }
  .ck-chip:hover .ck-chip-x { color:var(--sc-teal-ink); }
  .sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); border:0; }

  /* Notes list — used by /notes editorial port. ck-chip pills here
   * double as tag-filter shortcuts. */
  .ck-note-list { list-style:none; padding:0; margin:0; }
  .ck-note-row { padding:14px 0; border-bottom:1px solid var(--sc-rule); display:flex; flex-direction:column; gap:6px; }
  .ck-note-row:last-child { border-bottom:0; }
  .ck-note-meta { display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-family:var(--sc-sans); font-size:12px; color:var(--sc-text-faint); }
  .ck-note-deal { font-weight:600; color:var(--sc-teal-ink); text-decoration:none; }
  .ck-note-deal:hover { color:var(--sc-navy); text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:3px; }
  .ck-note-ts { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); }
  .ck-note-author { color:var(--sc-text-dim); }
  .ck-note-pills { display:inline-flex; gap:6px; margin-left:auto; flex-wrap:wrap; }
  .ck-note-body { font-family:var(--sc-serif); font-size:14px; line-height:1.5; color:var(--sc-text); white-space:pre-wrap; }
  .ck-mark { background:#fff5d6; padding:0 2px; border-radius:1px; }

  /* Data table cells — utility classes that replace the ~1200
   * hand-rolled inline-styled <td> attrs across data_public/.
   * Use ck_data_cell() to emit cells; or apply classes directly
   * for one-off cases. The cycle-22 lift consolidates these so
   * future cycles can mechanically migrate inline-styled tables. */
  .ck-cell { padding:5px 10px; font-size:11px; color:var(--sc-text); }
  .ck-cell-mono { font-family:var(--sc-mono); font-variant-numeric:tabular-nums; }
  .ck-cell-r { text-align:right; }
  .ck-cell-c { text-align:center; }
  .ck-cell.tone-dim { color:var(--sc-text-dim); }
  .ck-cell.tone-pos { color:var(--sc-positive); }
  .ck-cell.tone-neg { color:var(--sc-negative); }
  .ck-cell.tone-acc { color:var(--sc-teal-ink); }
  .ck-cell-w-600 { font-weight:600; }
  .ck-cell-w-700 { font-weight:700; }

  /* Page-header chrome — replaces the per-page page-wrapper that
   * data_public pages roll by hand:
   *   <div style="padding:20px;max-width:1400px;margin:0 auto">
   *     <div style="margin-bottom:20px">
   *       <h1 style="font-size:18px;font-weight:700;...">Title</h1>
   *       <p style="font-size:12px;...">Subtitle</p>
   * Cycle 31 migration replaces those inline styles with these
   * utility classes. ~500 inline-style instances eliminated. */
  .ck-page-wrap { padding:20px; max-width:1720px; margin:0 auto; }
  .ck-page-head { margin-bottom:20px; }
  .ck-page-h1 { font-size:18px; font-weight:700; color:var(--sc-text); letter-spacing:0.02em; }
  .ck-page-sub { font-size:12px; color:var(--sc-text-dim); margin-top:4px; }

  /* Data-table chrome — wraps the second-most-common inline-style
   * cluster (cycle 27): the <table>+<thead>+<tbody> container with
   * scroll-wrapper + alternating row backgrounds. Use ck_data_table
   * to compose the chrome around ck_data_cell rows. */
  .ck-data-table-scroll { overflow-x:auto; margin-top:12px; }
  .ck-data-table { width:100%; border-collapse:collapse; font-size:11px; }
  .ck-data-table thead tr { background:var(--sc-bone); }
  .ck-data-table tbody tr:nth-child(even) { background:var(--sc-panel-alt, #ece6db); }
  .ck-data-table-head { padding:6px 10px; border-bottom:1px solid var(--sc-rule); font-size:10px; color:var(--sc-text-dim); letter-spacing:0.05em; font-weight:600; text-transform:uppercase; }

  /* Personal dashboard /my/<owner> — pulse strip uses the existing
   * ck-kpi-grid; health-mix bar is the only bespoke chrome. */
  .ck-pulse-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:0; border-top:1px solid var(--sc-rule); }
  .ck-pulse-grid .ck-kpi { padding:14px 18px; border-right:1px solid var(--sc-rule); }
  .ck-pulse-grid .ck-kpi:last-child { border-right:0; }
  .ck-pulse-grid .ck-kpi-value .neg { color:var(--sc-negative); }
  .ck-pulse-grid .ck-kpi-value .warn { color:var(--sc-warning); }
  .ck-health-mix { background:#fff; border:1px solid var(--sc-rule); border-radius:2px; box-shadow:var(--sc-shadow-1); margin:0 0 var(--sc-s-5); padding:18px; }
  .ck-health-mix-head { display:flex; align-items:baseline; justify-content:space-between; gap:var(--sc-s-4); margin-bottom:14px; }
  .ck-health-mix-head h3 { font-family:var(--sc-sans); font-weight:700; font-size:13px; letter-spacing:0.12em; text-transform:uppercase; color:var(--sc-navy); margin:0; }
  .ck-health-mix-head .count { font-family:var(--sc-mono); font-size:13px; color:var(--sc-text-faint); }
  .ck-health-bar { display:flex; height:18px; border-radius:2px; overflow:hidden; border:1px solid var(--sc-rule); margin-bottom:10px; }
  .ck-health-bar .seg.green { background:var(--sc-positive); }
  .ck-health-bar .seg.amber { background:var(--sc-warning); }
  .ck-health-bar .seg.red   { background:var(--sc-negative); }
  .ck-health-legend { display:flex; gap:18px; font-family:var(--sc-mono); font-size:11px; letter-spacing:0.06em; }
  .ck-health-legend .lg.green { color:var(--sc-positive); }
  .ck-health-legend .lg.amber { color:var(--sc-warning); }
  .ck-health-legend .lg.red   { color:var(--sc-negative); }
  .ck-health-cell.tone-positive { color:var(--sc-positive); font-weight:700; }
  .ck-health-cell.tone-warning  { color:var(--sc-warning); font-weight:700; }
  .ck-health-cell.tone-negative { color:var(--sc-negative); font-weight:700; }
  .ck-health-cell.tone-neutral  { color:var(--sc-text-faint); font-weight:600; }
  .ck-health-cell.faint { color:var(--sc-text-faint); }
  .ck-deal-link { color:var(--sc-teal-ink); font-weight:600; text-decoration:none; }
  .ck-deal-link:hover { color:var(--sc-navy); text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:3px; }

  /* Research grid — one editorial card per research entry. Pairs
   * with the Insights triplet on /research. */
  .ck-research-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:var(--sc-s-6) var(--sc-s-7); margin:0 0 var(--sc-s-6); }
  .ck-research-card { display:flex; flex-direction:column; gap:var(--sc-s-3); padding:0 0 var(--sc-s-5); border-bottom:1px solid var(--sc-rule); }
  .ck-research-card .ck-eyebrow { margin-bottom:var(--sc-s-2); }
  .ck-research-card-title { font-family:var(--sc-serif); font-weight:500; font-size:22px; line-height:1.2; margin:0; color:var(--sc-navy); }
  .ck-research-card-title a { color:inherit; text-decoration:none; transition:color 0.15s; }
  .ck-research-card-title a:hover { color:var(--sc-teal-ink); }
  .ck-research-card-body { font-family:var(--sc-serif); font-size:15px; line-height:1.55; color:var(--sc-text-dim); margin:0; max-width:48ch; }

  /* Command palette */
  .ck-palette { position:fixed; inset:0; background:rgba(6,22,38,0.4); display:flex; align-items:flex-start; justify-content:center; padding-top:12vh; z-index:100; }
  .ck-palette[hidden] { display:none; }
  .ck-palette-box { width:min(680px, 92vw); background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-3); border-radius:2px; }
  .ck-palette-input { width:100%; padding:16px 20px; font-family:var(--sc-serif); font-size:18px; border:0; border-bottom:1px solid var(--sc-rule); outline:none; }
  .ck-palette-list { list-style:none; margin:0; padding:0; max-height:52vh; overflow:auto; }
  .ck-palette-list li { display:flex; justify-content:space-between; padding:10px 20px; font-size:13px; cursor:pointer; border-bottom:1px solid var(--sc-bone); }
  .ck-palette-list li:hover { background:var(--sc-bone); }
  .ck-palette-list li.cp-section { display:block; padding:10px 20px 6px; cursor:default; background:transparent; border-bottom:0; font-family:var(--sc-mono); font-size:10px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint); }
  .ck-palette-list li.cp-section:hover { background:transparent; }
  .ck-palette-list li.cp-recent { background:linear-gradient(90deg, rgba(21,87,82,0.04) 0%, transparent 100%); }
  .ck-palette-list li.cp-recent:hover { background:var(--sc-bone); }
  .cp-route { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); }

  /* Toast / flash notifications — bottom-right slide-in stack */
  .ck-toast-host { position:fixed; bottom:24px; right:24px; display:flex; flex-direction:column; gap:10px; z-index:120; pointer-events:none; max-width:380px; }
  .ck-toast { pointer-events:auto; display:flex; align-items:center; gap:14px; padding:13px 18px; background:#fff; border:1px solid var(--sc-rule); border-left:3px solid var(--sc-teal); border-radius:2px; box-shadow:var(--sc-shadow-2); font-family:var(--sc-sans); font-size:13.5px; color:var(--sc-text); transform:translateX(20px); opacity:0; transition:transform 0.22s ease-out, opacity 0.22s ease-out; }
  .ck-toast.ck-toast-show { transform:translateX(0); opacity:1; }
  .ck-toast-success { border-left-color:var(--sc-positive); }
  .ck-toast-info    { border-left-color:var(--sc-teal); }
  .ck-toast-warning { border-left-color:var(--sc-warning); }
  .ck-toast-error   { border-left-color:var(--sc-negative); }
  .ck-toast-close { margin-left:auto; flex-shrink:0; width:22px; height:22px; padding:0; background:transparent; border:0; color:var(--sc-text-faint); font-size:16px; line-height:1; cursor:pointer; border-radius:50%; }
  .ck-toast-close:hover { background:var(--sc-bone); color:var(--sc-navy); }

  /* Keyboard shortcut help dialog (press ?) */
  .ck-shortcuts { position:fixed; inset:0; background:rgba(11,35,65,0.45); display:flex; align-items:flex-start; justify-content:center; padding-top:10vh; z-index:110; }
  .ck-shortcuts[hidden] { display:none; }
  .ck-shortcuts-box { width:min(540px, 92vw); background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-3); border-radius:2px; max-height:80vh; overflow:auto; }
  .ck-shortcuts-head { display:flex; align-items:baseline; gap:14px; padding:18px 22px 10px; border-bottom:1px solid var(--sc-rule); position:relative; }
  .ck-shortcuts-eyebrow { font-family:var(--sc-mono); font-size:11px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-teal-ink, var(--sc-teal)); }
  .ck-shortcuts-title { font-family:var(--sc-serif); font-weight:500; font-size:24px; color:var(--sc-navy); margin:0; letter-spacing:-0.01em; }
  .ck-shortcuts-close { position:absolute; top:14px; right:14px; width:28px; height:28px; border:0; background:transparent; font-size:22px; line-height:1; color:var(--sc-text-faint); cursor:pointer; border-radius:50%; }
  .ck-shortcuts-close:hover { background:var(--sc-bone); color:var(--sc-navy); }
  .ck-shortcuts-body { padding:18px 22px 22px; display:grid; gap:18px; }
  .ck-shortcuts-body section h3 { font-family:var(--sc-mono); font-size:11px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); margin:0 0 8px; }
  .ck-shortcuts-body dl { display:grid; grid-template-columns:max-content 1fr; gap:6px 16px; margin:0; }
  .ck-shortcuts-body dt { display:flex; align-items:center; gap:4px; font-family:var(--sc-sans); font-size:12px; color:var(--sc-text-dim); }
  .ck-shortcuts-body dd { font-family:var(--sc-serif); font-size:13.5px; line-height:1.45; color:var(--sc-text); margin:0; }
  .ck-shortcuts-body kbd { display:inline-block; padding:2px 7px; background:var(--sc-bone); border:1px solid var(--sc-rule); border-bottom-width:2px; border-radius:3px; font-family:var(--sc-mono); font-size:11px; font-weight:600; color:var(--sc-navy); min-width:14px; text-align:center; }

  /* Main content frame */
  .ck-main { padding:var(--sc-s-7); max-width:1720px; margin:0 auto; }

  /* Print — for /memo/<id>, /ic-packet/<id> */
  @media print {
    .ck-topbar, .ck-breadcrumbs, .ck-palette { display:none !important; }
    body { background:#fff !important; }
    .ck-panel { box-shadow:none; break-inside:avoid; page-break-inside:avoid; }
    .ck-main { max-width:none; padding:0; }
  }
</style>
"""

_CSRF_JS = """
<script>
/* CSRF token patcher — reads rcm_csrf cookie and:
 *   1. Injects csrf_token hidden input into every POST form
 *   2. Sets X-CSRF-Token header on every non-GET fetch()
 * Without this, every "Acknowledge alert", "Save note", "Create deal",
 * etc. fails silently with 403. Drop-in safe — harmless if cookie absent.
 */
(function(){
  function c(n){var m=document.cookie.match(new RegExp('(?:^|; )'+n+'=([^;]*)'));
    return m?decodeURIComponent(m[1]):null;}
  document.addEventListener('submit',function(e){
    var t=c('rcm_csrf');if(!t)return;
    var f=e.target;if(!f||f.tagName!=='FORM')return;
    if(f.method&&f.method.toLowerCase()!=='post')return;
    var x=f.querySelector('input[name=csrf_token]');
    if(!x){x=document.createElement('input');x.type='hidden';
      x.name='csrf_token';f.appendChild(x);}
    x.value=t;
  },true);
  var of=window.fetch;
  if(of){window.fetch=function(u,o){
    o=o||{};var t=c('rcm_csrf');
    if(t&&o.method&&o.method.toUpperCase()!=='GET'){
      o.headers=o.headers||{};
      if(!o.headers['X-CSRF-Token'])o.headers['X-CSRF-Token']=t;
    }
    return of(u,o);
  };}
})();
</script>
"""


_TOAST_HTML = """
<div class="ck-toast-host" id="ck-toast-host" aria-live="polite"></div>
"""


_TOAST_JS = """
<script>
/* Toast / flash notification system.
 *   Any page can fire one via:
 *     window.ckToast('Saved', 'success')   // success | info | warning | error
 *   Or embed a one-shot at render time:
 *     <meta name="ck-flash" content="Alert acknowledged">
 *     <meta name="ck-flash-kind" content="success">
 *   Or via query string after a redirect:
 *     /alerts?flash=Acknowledged&kind=success
 *   The query-string variant scrubs ?flash + ?kind from history so a
 *   partner refreshing the page doesn't see the toast again. */
(function(){
  var host = document.getElementById('ck-toast-host');
  if (!host) return;

  function show(msg, kind){
    if (!msg) return;
    var t = document.createElement('div');
    t.className = 'ck-toast ck-toast-' + (kind || 'info');
    t.setAttribute('role', 'status');
    t.textContent = msg;
    var x = document.createElement('button');
    x.type = 'button';
    x.className = 'ck-toast-close';
    x.setAttribute('aria-label', 'Dismiss');
    x.innerHTML = '&times;';
    x.addEventListener('click', function(){ dismiss(t); });
    t.appendChild(x);
    host.appendChild(t);
    /* Slide in on next frame so transition fires */
    requestAnimationFrame(function(){ t.classList.add('ck-toast-show'); });
    /* Auto-dismiss after 3.6s (5.5s for warning/error) */
    var ms = (kind === 'warning' || kind === 'error') ? 5500 : 3600;
    setTimeout(function(){ dismiss(t); }, ms);
  }
  function dismiss(t){
    if (!t || !t.parentNode) return;
    t.classList.remove('ck-toast-show');
    setTimeout(function(){
      if (t.parentNode) t.parentNode.removeChild(t);
    }, 220);
  }
  window.ckToast = show;

  /* Render meta-tag flashes on load */
  var meta = document.querySelector('meta[name="ck-flash"]');
  if (meta && meta.getAttribute('content')) {
    var kind = (document.querySelector('meta[name="ck-flash-kind"]') || {}).content || 'info';
    show(meta.getAttribute('content'), kind);
  }

  /* Render query-string flashes on load + clean history */
  try {
    var sp = new URLSearchParams(window.location.search);
    var qmsg = sp.get('flash');
    if (qmsg) {
      var qkind = sp.get('kind') || 'info';
      show(qmsg, qkind);
      sp.delete('flash');
      sp.delete('kind');
      var qs = sp.toString();
      var newUrl = window.location.pathname + (qs ? ('?' + qs) : '') + window.location.hash;
      window.history.replaceState({}, '', newUrl);
    }
  } catch (e) {}
})();
</script>
"""


_SHORTCUTS_HTML = """
<div class="ck-shortcuts" id="ck-shortcuts" hidden>
  <div class="ck-shortcuts-box" role="dialog" aria-label="Keyboard shortcuts">
    <header class="ck-shortcuts-head">
      <span class="ck-shortcuts-eyebrow">Keyboard</span>
      <h2 class="ck-shortcuts-title">Shortcuts</h2>
      <button type="button" class="ck-shortcuts-close" aria-label="Close">&times;</button>
    </header>
    <div class="ck-shortcuts-body">
      <section>
        <h3>Navigation</h3>
        <dl>
          <dt><kbd>⌘</kbd><kbd>K</kbd> &middot; <kbd>Ctrl</kbd><kbd>K</kbd></dt>
            <dd>Open command palette &mdash; jump to any tool</dd>
          <dt><kbd>Enter</kbd></dt>
            <dd>In palette: open the first matching tool</dd>
          <dt><kbd>Esc</kbd></dt>
            <dd>Close palette / dialog / dropdown</dd>
        </dl>
      </section>
      <section>
        <h3>Quick jump (vim-style)</h3>
        <dl>
          <dt><kbd>g</kbd> <kbd>h</kbd></dt><dd>Home</dd>
          <dt><kbd>g</kbd> <kbd>p</kbd></dt><dd>Pipeline</dd>
          <dt><kbd>g</kbd> <kbd>d</kbd></dt><dd>Diligence (deal profile)</dd>
          <dt><kbd>g</kbd> <kbd>l</kbd></dt><dd>Library</dd>
          <dt><kbd>g</kbd> <kbd>r</kbd></dt><dd>Research</dd>
          <dt><kbd>g</kbd> <kbd>o</kbd></dt><dd>Portfolio</dd>
          <dt><kbd>g</kbd> <kbd>a</kbd></dt><dd>Alerts</dd>
          <dt><kbd>g</kbd> <kbd>w</kbd></dt><dd>Watchlist</dd>
          <dt><kbd>g</kbd> <kbd>m</kbd></dt><dd>My Dashboard</dd>
        </dl>
      </section>
      <section>
        <h3>Workbench</h3>
        <dl>
          <dt><kbd>1</kbd>&ndash;<kbd>8</kbd></dt>
            <dd>Switch tabs on /analysis/&lt;deal&gt; (Overview &rarr; Provenance)</dd>
          <dt><kbd>Alt</kbd><kbd>&larr;</kbd> / <kbd>Alt</kbd><kbd>&rarr;</kbd></dt>
            <dd>Previous / next tab</dd>
        </dl>
      </section>
      <section>
        <h3>This dialog</h3>
        <dl>
          <dt><kbd>?</kbd></dt><dd>Show / hide this list</dd>
        </dl>
      </section>
    </div>
  </div>
</div>
"""


_SHORTCUTS_JS = """
<script>
/* Keyboard shortcut help dialog: press '?' to toggle, Esc to close.
 * Shift+/ (the unshifted "?" key on most US keyboards) is what the
 * browser actually delivers — listen for it explicitly so the
 * shortcut works without relying on e.key === '?'.
 *
 * Also implements vim/Linear-style "g + letter" jump:
 *   g h → /home          g p → /pipeline       g d → /diligence/deal
 *   g l → /library       g r → /research       g o → /portfolio
 *   g a → /alerts        g w → /watchlist      g k → opens palette
 */
(function(){
  /* g+letter prefix-jump table. Keep separate from shortcut dialog
   * so future expansion (g + I = ic packet, etc.) lives in one place. */
  var GO_TARGETS = {
    h: '/home', p: '/pipeline', d: '/diligence/deal',
    l: '/library', r: '/research', o: '/portfolio',
    a: '/alerts', w: '/watchlist', m: '/my/AT',
  };
  var goPending = false;
  var goTimer = null;
  function clearGo(){ goPending = false; if (goTimer){clearTimeout(goTimer); goTimer=null;} }
  document.addEventListener('keydown', function(e){
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (goPending) {
      var k = (e.key || '').toLowerCase();
      if (GO_TARGETS[k]) {
        e.preventDefault();
        clearGo();
        window.location.href = GO_TARGETS[k];
        return;
      }
      if (k === 'k') {
        /* Alias g+k → command palette to match the docs */
        clearGo();
        var p = document.getElementById('ck-palette');
        if (p) { p.hidden = false; var inp = p.querySelector('.ck-palette-input'); if (inp) setTimeout(function(){ inp.focus(); }, 0); }
        e.preventDefault();
        return;
      }
      clearGo();
      return;
    }
    if (e.key === 'g' && !e.shiftKey) {
      goPending = true;
      goTimer = setTimeout(clearGo, 1500);
      e.preventDefault();
    }
  });
})();

(function(){
  var dlg = document.getElementById('ck-shortcuts');
  if (!dlg) return;
  function show(){ dlg.hidden = false; }
  function hide(){ dlg.hidden = true; }
  document.addEventListener('keydown', function(e){
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
    if (e.key === '?' || (e.shiftKey && e.key === '/')) {
      e.preventDefault();
      if (dlg.hidden) show(); else hide();
    }
    if (e.key === 'Escape' && !dlg.hidden) { e.preventDefault(); hide(); }
  });
  /* Close button + click-outside */
  var close = dlg.querySelector('.ck-shortcuts-close');
  if (close) close.addEventListener('click', hide);
  dlg.addEventListener('click', function(e){
    if (e.target === dlg) hide();
  });
  /* Open from the user-dropdown menu item */
  document.addEventListener('click', function(e){
    var btn = e.target && e.target.closest && e.target.closest('[data-ck-shortcuts-open]');
    if (btn) { e.preventDefault(); show(); }
  });
})();
</script>
"""


_INTRO_DISMISS_JS = """
<script>
/* Editorial section-intro behaviour:
 *   - Hidden by default. A partner only sees them when they opt into
 *     "tutorial mode" via the user dropdown → "Tutorial intros".
 *   - When tutorial mode IS on, the × button still dismisses an
 *     individual intro per-page (writes ck-intro-dismissed:<key>).
 *   - The global toggle is the localStorage flag `ck-intro-mode`;
 *     value "on" shows intros, anything else hides them. */
(function(){
  var GLOBAL_KEY = 'ck-intro-mode';
  var STORAGE_PREFIX = 'ck-intro-dismissed:';
  var enabled = (function(){
    try { return localStorage.getItem(GLOBAL_KEY) === 'on'; }
    catch (e) { return false; }
  })();
  var intros = document.querySelectorAll('[data-ck-intro]');
  intros.forEach(function(el){
    if (!enabled) { el.hidden = true; return; }
    var key = el.getAttribute('data-ck-intro');
    if (key && localStorage.getItem(STORAGE_PREFIX + key) === '1') {
      el.hidden = true;
    }
  });
  document.addEventListener('click', function(e){
    var btn = e.target.closest && e.target.closest('[data-ck-intro-dismiss]');
    if (btn) {
      var key = btn.getAttribute('data-ck-intro-dismiss');
      var host = btn.closest('[data-ck-intro]');
      if (host) host.hidden = true;
      if (key) {
        try { localStorage.setItem(STORAGE_PREFIX + key, '1'); } catch (e) {}
      }
      return;
    }
    var tog = e.target.closest && e.target.closest('[data-ck-intro-toggle]');
    if (tog) {
      e.preventDefault();
      try {
        var now = localStorage.getItem(GLOBAL_KEY) === 'on' ? 'off' : 'on';
        localStorage.setItem(GLOBAL_KEY, now);
        // Reflect in the menu label without a full reload
        tog.textContent = (now === 'on'
          ? 'Tutorial intros: on'
          : 'Tutorial intros: off');
        // Show / hide intros immediately
        document.querySelectorAll('[data-ck-intro]').forEach(function(el){
          el.hidden = (now !== 'on');
        });
      } catch (e) {}
    }
  });
  /* On load, set the menu-item label to match current state. */
  var label = document.querySelector('[data-ck-intro-toggle]');
  if (label) {
    label.textContent = enabled ? 'Tutorial intros: on'
                                : 'Tutorial intros: off';
  }
})();
</script>
"""


_USER_MENU_JS = """
<script>
/* User dropdown — click chip to open, click-outside or Escape to close.
 * Marks aria-expanded for screen readers. Drop-in safe; renders nothing
 * if a page omits the chip entirely.
 *
 * Also populates the "Recent deals" group from localStorage on every
 * page load. Storage key: rcm-mc-recent-deals-v1, written by the deal
 * page (server.py) as [{id, name}, ...] (legacy entries are bare strings;
 * we tolerate both shapes). */
(function(){
  var btn = document.querySelector('[data-ck-user-toggle]');
  if (!btn) return;
  var menu = btn.parentElement.querySelector('.ck-user-dropdown');
  if (!menu) return;
  function open(){ menu.hidden = false; btn.setAttribute('aria-expanded','true'); }
  function close(){ menu.hidden = true; btn.setAttribute('aria-expanded','false'); }
  btn.addEventListener('click', function(e){
    e.stopPropagation();
    if (menu.hidden) open(); else close();
  });
  document.addEventListener('click', function(e){
    if (menu.hidden) return;
    if (!menu.contains(e.target) && e.target !== btn) close();
  });
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && !menu.hidden) close();
  });

  /* Hydrate recent-deals group */
  try {
    var REC_KEY = 'rcm-mc-recent-deals-v1';
    var MAX_DROPDOWN = 5;
    var box = menu.querySelector('[data-ck-recent-deals]');
    var list = menu.querySelector('[data-ck-recent-list]');
    if (box && list) {
      var arr = [];
      try { arr = JSON.parse(localStorage.getItem(REC_KEY) || '[]'); }
      catch (e) { arr = []; }
      arr = arr.map(function(x) {
        return (typeof x === 'string') ? {id: x, name: x} : x;
      }).filter(function(x) { return x && x.id; });
      if (arr.length) {
        box.hidden = false;
        list.innerHTML = '';
        arr.slice(0, MAX_DROPDOWN).forEach(function(d) {
          var a = document.createElement('a');
          a.className = 'ck-user-recent-item';
          a.href = '/deal/' + encodeURIComponent(d.id);
          var nm = document.createElement('span');
          nm.className = 'ck-user-recent-name';
          nm.textContent = d.name || d.id;
          a.appendChild(nm);
          if (d.name && d.name !== d.id) {
            var sl = document.createElement('span');
            sl.className = 'ck-user-recent-slug';
            sl.textContent = d.id;
            a.appendChild(sl);
          }
          list.appendChild(a);
        });
      }
    }
  } catch (e) { /* storage unavailable — skip */ }
})();
</script>
"""


_PALETTE_JS = """
<script>
/* Cmd+K palette behaviour:
 *   - Cmd/Ctrl+K opens, Esc closes.
 *   - Recent visits (last 8) bubble to the top with a "Recent" header
 *     so a partner can grab yesterday's tool in one keystroke.
 *   - Arrow keys move the highlight; Enter navigates.
 *   - Selecting an item records it in localStorage.ck-palette-recent.
 */
(function(){
  var p = document.getElementById('ck-palette');
  if (!p) return;
  var RECENT_KEY = 'ck-palette-recent';
  var MAX_RECENT = 8;
  var input = p.querySelector('.ck-palette-input');
  var list  = p.querySelector('.ck-palette-list');
  var allItems = Array.from(p.querySelectorAll('li'));
  function loadRecent(){
    try {
      var s = localStorage.getItem(RECENT_KEY);
      return s ? JSON.parse(s) : [];
    } catch (e) { return []; }
  }
  function saveRecent(routes){
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(routes.slice(0, MAX_RECENT))); }
    catch (e) {}
  }
  function rebuild(){
    var recent = loadRecent();
    if (!list) return;
    /* Remove any prior recent header + clones */
    Array.from(list.querySelectorAll('[data-recent-marker]')).forEach(function(el){
      el.parentNode.removeChild(el);
    });
    if (!recent.length) return;
    var header = document.createElement('li');
    header.className = 'cp-section';
    header.setAttribute('data-recent-marker', 'header');
    header.textContent = 'Recent';
    var firstChild = list.firstChild;
    list.insertBefore(header, firstChild);
    /* Insert a clone of each recent item right after header, in order */
    var cursor = header;
    recent.slice().reverse().forEach(function(route){
      var src = allItems.filter(function(li){ return li.getAttribute('data-route') === route; })[0];
      if (!src) return;
      var clone = src.cloneNode(true);
      clone.setAttribute('data-recent-marker', 'item');
      clone.classList.add('cp-recent');
      header.parentNode.insertBefore(clone, header.nextSibling);
    });
    /* Wire clones to the same click + nav behaviour */
    Array.from(list.querySelectorAll('[data-recent-marker="item"]')).forEach(function(li){
      li.addEventListener('click', function(){ navTo(li); });
    });
  }
  function navTo(li){
    var r = li.getAttribute('data-route');
    if (!r) return;
    var rec = loadRecent().filter(function(x){ return x !== r; });
    rec.unshift(r);
    saveRecent(rec);
    window.location.href = r;
  }
  function show(){ rebuild(); p.hidden = false; setTimeout(function(){ input.focus(); }, 0); }
  function hide(){ p.hidden = true; input.value = ''; filter(''); }
  function filter(q){
    q = (q || '').toLowerCase();
    Array.from(p.querySelectorAll('li')).forEach(function(li){
      if (li.classList.contains('cp-section')) {
        /* Show the "Recent" header only when no query is active */
        li.style.display = q ? 'none' : '';
        return;
      }
      var t = li.textContent.toLowerCase();
      li.style.display = t.indexOf(q) >= 0 ? '' : 'none';
    });
  }
  input.addEventListener('input', function(e){ filter(e.target.value); });
  allItems.forEach(function(li){
    li.addEventListener('click', function(){ navTo(li); });
  });
  document.addEventListener('keydown', function(e){
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); show(); }
    if (e.key === 'Escape' && !p.hidden) { e.preventDefault(); hide(); }
    if (e.key === 'Enter' && !p.hidden) {
      /* Pick first visible item */
      var first = Array.from(p.querySelectorAll('li:not([style*="display: none"])'))
        .find(function(li){ return !li.classList.contains('cp-section'); });
      if (first) { e.preventDefault(); navTo(first); }
    }
  });
})();
</script>
"""


# Map raw active_nav values (as passed by page renderers) to a sub-nav
# section key. Keys can arrive as bare-key ("home"), leading-slash
# ("/portfolio"), or a sub-path ("/portfolio/monitor", "/analysis").
# Mapping is intentionally explicit so a typo doesn't silently route to
# the wrong section.
_SUB_SECTION_MAP = {
    # bare keys
    "home": "home", "pipeline": "pipeline", "library": "library",
    "research": "research", "portfolio": "portfolio",
    "diligence": "diligence",
    "alerts": "home", "escalations": "home", "watchlist": "home",
    # All /diligence/* sub-paths land in the Diligence section so
    # the RCM playbook flow keeps a consistent active subnav.
    "/diligence": "diligence",
    "/screening/bankruptcy-survivor": "diligence",
    "/engagements": "diligence",
    # leading-slash forms
    "/home": "home", "/app": "home", "/alerts": "home",
    "/escalations": "home", "/watchlist": "home", "/my": "home",
    "/pipeline": "pipeline", "/source": "pipeline",
    "/screen": "pipeline", "/predictive-screener": "pipeline",
    "/find-comps": "pipeline", "/conferences": "pipeline",
    "/pe-intelligence": "pipeline", "/deal-screening": "pipeline",
    "/library": "library", "/deals-library": "library",
    "/methodology": "library", "/metric-glossary": "library",
    "/data": "library", "/comparables": "library",
    "/market-rates": "library", "/data-catalog": "library",
    "/rcm-benchmarks": "library",
    "/research": "research", "/notes": "research",
    "/sector-momentum": "research", "/irr-dispersion": "research",
    "/hold-analysis": "research", "/backtest": "research",
    "/comparable-outcomes": "research", "/bear-cases": "research",
    "/regulatory-calendar": "research", "/market-intel": "research",
    "/corpus-backtest": "research",
    # Some renderers still pass legacy /diligence/* active_nav values;
    # map them to the same editorial section the wired URL belongs to.
    "/diligence/comparable-outcomes": "research",
    "/diligence/regulatory-calendar": "research",
    "/diligence/bear-case": "research",
    "/diligence/bear-cases": "research",
    "/portfolio": "portfolio", "/lp-update": "portfolio",
    "/portfolio-analytics": "portfolio",
    "/sponsor-track-record": "portfolio",
    "/payer-intelligence": "portfolio",
    # cross-section common deep paths
    "/analysis": "research", "/quant-lab": "research",
    "/market-data/map": "library",
}


def _resolve_sub_section(active_nav: Optional[str]) -> Optional[str]:
    """Pick the sub-nav section key for an active_nav value.

    Resolution order:
      1. Exact match in ``_SUB_SECTION_MAP``.
      2. First path segment match (``/portfolio/monitor`` → ``/portfolio``).
      3. Path-prefix match — any path starting with a key in the map
         resolves to that section. Used so every ``/diligence/*``
         renderer lands the user in the Diligence subnav without
         each file having to enumerate the active_nav string.
    """
    if not active_nav:
        return None
    key = str(active_nav).strip().lower()
    if key in _SUB_SECTION_MAP:
        return _SUB_SECTION_MAP[key]
    if key.startswith("/"):
        first = "/" + key.lstrip("/").split("/", 1)[0]
        if first in _SUB_SECTION_MAP:
            return _SUB_SECTION_MAP[first]
        # Path-prefix fallback (longest match wins) so e.g.
        # "/diligence/deal-mc" → "/diligence" → "diligence" without
        # listing every sub-path.
        for prefix in sorted(
            (k for k in _SUB_SECTION_MAP if k.startswith("/") and "/" in k[1:]),
            key=len, reverse=True,
        ):
            if key.startswith(prefix):
                return _SUB_SECTION_MAP[prefix]
    return None


def _topbar(active_nav: Optional[str], user_initials: str = "AT") -> str:
    """Editorial topbar mirroring chartis.com chrome.

    Navy background, white wordmark with italic ``Chartis``, uppercase
    nav links with teal active underline, search anchored to the
    right with a teal-on-navy user chip. The thin teal stripe on the
    bottom edge is a Chartis signature.

    When ``active_nav`` matches a key in ``_SUB_NAV``, a parchment
    sub-nav rail renders directly below with the section's most-clicked
    second-level pages — saves a partner the click into a section
    landing page just to find a common surface.
    """
    links = "".join(
        f'<a href="{_esc(item["href"])}" class="{"active" if item["key"] == active_nav else ""}">{_esc(item["label"])}</a>'
        for item in _CORPUS_NAV
    )

    # Sub-nav rail. Page renderers historically pass active_nav in
    # mixed conventions: bare key ("home"), leading-slash path
    # ("/portfolio"), or a sub-path ("/portfolio/monitor",
    # "/analysis"). Normalise to a section key so we can look up
    # _SUB_NAV regardless of caller. Falls back to nothing if the
    # section has no entry (e.g. /login, /admin, debug pages).
    sub_section = _resolve_sub_section(active_nav)
    sub_links_html = ""
    if sub_section and sub_section in _SUB_NAV:
        sub_links = "".join(
            f'<a href="{_esc(item["href"])}" class="ck-subnav-link">'
            f'{_esc(item["label"])}</a>'
            for item in _SUB_NAV[sub_section]
        )
        sub_links_html = (
            '<nav class="ck-subnav" aria-label="Section">'
            f'<div class="ck-subnav-inner">{sub_links}</div>'
            '</nav>'
        )

    return (
        '<header class="ck-topbar">'
        '<div class="ck-topbar-inner">'
        '<a href="/" class="ck-wordmark" aria-label="SeekingChartis home">'
        '<span class="ck-wordmark-mark"></span>'
        '<span class="ck-wordmark-text">Seeking<em>Chartis</em></span>'
        '</a>'
        f'<nav class="ck-nav" aria-label="Primary">{links}</nav>'
        '<div class="ck-topbar-right">'
        '<form class="ck-search-form" action="/search" method="get" role="search">'
        '<input class="ck-search" type="search" name="q" '
        'placeholder="Search deals, hospitals, routes — ⌘K" '
        'aria-label="Search" />'
        '</form>'
        '<div class="ck-user-menu">'
        f'<button class="ck-user-chip" type="button" aria-haspopup="true" '
        f'aria-expanded="false" title="Signed in" '
        f'data-ck-user-toggle>{_esc(user_initials)}</button>'
        '<div class="ck-user-dropdown" hidden>'
        # Recently-viewed deals — populated client-side from
        # localStorage by _USER_MENU_JS. Hidden when empty.
        '<div class="ck-user-recent" data-ck-recent-deals hidden>'
        '<div class="ck-user-recent-head">Recent deals</div>'
        '<div class="ck-user-recent-list" data-ck-recent-list></div>'
        '</div>'
        '<a href="/my/AT" class="ck-user-dropdown-item">My Dashboard</a>'
        '<a href="/tools" class="ck-user-dropdown-item">All Tools &middot; ⌘K</a>'
        '<a href="/methodology" class="ck-user-dropdown-item">Methodology</a>'
        '<a href="/admin" class="ck-user-dropdown-item">Admin</a>'
        '<a href="/audit" class="ck-user-dropdown-item">Audit Log</a>'
        '<div class="ck-user-dropdown-divider"></div>'
        '<button type="button" class="ck-user-dropdown-item" '
        'data-ck-intro-toggle>Tutorial intros: off</button>'
        '<button type="button" class="ck-user-dropdown-item" '
        'data-ck-shortcuts-open>Keyboard shortcuts &middot; ?</button>'
        '<div class="ck-user-dropdown-divider"></div>'
        '<form action="/api/logout" method="post" class="ck-user-dropdown-form">'
        '<button type="submit" class="ck-user-dropdown-item ck-user-dropdown-logout">'
        'Sign out</button>'
        '</form>'
        '</div>'
        '</div>'
        "</div>"
        "</div>"
        f"{sub_links_html}"
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
    body_html: Optional[str] = None,
    title: Optional[str] = None,
    *,
    body: Optional[str] = None,  # legacy alias for body_html — accept
                                  # so partially-migrated callers don't
                                  # 500 with "missing positional argument"
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
    # Page-specific JS injected before </body>. analysis_workbench
    # ships its tab-switching + scenario-form + explain-panel
    # handlers via this kwarg — without it the RCM Profile tab
    # (and every other workbench tab) was inert.
    extra_js: Optional[str] = None,
    # Editorial PHI-banner toggle (consumed by the editorial
    # variant). No-op in this v2 shell.
    show_phi_banner: bool = False,
    phi_mode: Optional[str] = None,
    # Cycle 20 — convenience kwarg that auto-prepends
    # ``ck_section_intro(**editorial_intro)`` to ``body_html`` so a
    # page can adopt the chartis cadence (italic-serif headline +
    # eyebrow + body) with one kwarg instead of restructuring its
    # render function. Use cases: every legacy renderer that's
    # already on chartis_shell but missing the editorial-cadence
    # intro signal.
    editorial_intro: Optional[Mapping[str, Any]] = None,
    **_extra: Any,
) -> str:
    """Render a full page. Drop-in replacement for the legacy dark shell.

    All kwargs are optional and match or extend the previous signature.
    Unknown kwargs (\\*\\*_extra) are accepted silently for forward-compat
    with partially-migrated callers — every page renders rather than 500.
    """
    # Accept legacy ``body=`` kwarg as an alias for ``body_html``.
    # A handful of pages were ported with the wrong kwarg name and
    # 500'd with "missing positional argument" until 2026-04-29.
    if body_html is None and body is not None:
        body_html = body
    if body_html is None:
        body_html = ""
    if title is None:
        title = "SeekingChartis"

    fonts = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Source+Serif+4:ital,wght@0,400;0,500;0,600;1,400&'
        'family=Inter+Tight:wght@400;500;600;700&'
        'family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    palette_html = ""
    if include_palette:
        # Use the platform-wide default tools index if the caller
        # didn't pass a curated list. Lets every editorial page jump
        # to any tool via Cmd+K without each renderer having to
        # re-enumerate the palette.
        modules_to_use = palette_modules or _DEFAULT_PALETTE_MODULES
        palette_html = ck_command_palette(modules_to_use)
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
    # ``editorial_intro`` auto-prepends a ck_section_intro block to
    # the page body. Lets a legacy renderer adopt the chartis cadence
    # (italic-serif headline) with a single kwarg instead of
    # restructuring its render function — much lower-friction port
    # for the 60-69 fidelity-tier.
    intro_html = ""
    if editorial_intro:
        intro_html = ck_section_intro(**editorial_intro)
    body_html = intro_html + body_html
    # Page-specific CSS goes AFTER the kit's CSS so page styles
    # win specificity ties — matches the contract login_page.py
    # and forgot_page.py expect (grid layout, panel chrome, etc.)
    extra_css_html = (
        f"<style>{extra_css}</style>" if extra_css else ""
    )
    # Page-specific JS sits at the end of body so the kit's
    # standard handlers (CSRF, user-menu, etc.) load first and
    # the page can rely on the DOM being parsed.
    extra_js_html = (
        f"<script>{extra_js}</script>" if extra_js else ""
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
        f"{_SHORTCUTS_HTML}"
        f"{_TOAST_HTML}"
        f"{_CSRF_JS}"
        f"{_USER_MENU_JS}"
        f"{_INTRO_DISMISS_JS}"
        f"{_PALETTE_JS}"
        f"{_SHORTCUTS_JS}"
        f"{_TOAST_JS}"
        f"{extra_js_html}"
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
    "ck_page_title",
    "ck_signal_badge",
    "ck_command_palette",
    "ck_fmt_currency",
    "ck_fmt_percent",
    "ck_fmt_number",
]

# Compatibility alias for partially-migrated chartis pages
editorial_chartis_shell = chartis_shell
