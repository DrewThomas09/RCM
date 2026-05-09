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
import re as _re
from typing import Iterable, Mapping, Optional, Sequence

# ---------------------------------------------------------------------------
# Backend HTML-tag sanitizer (PEDESK Phase 1, Week 1).
# ---------------------------------------------------------------------------
#
# Page renderers historically pre-wrapped numeric values in styled markup
# (e.g. f'<span class="mn neg">{loss_pct}</span>') and passed the wrapped
# string into ck_kpi_block. The v2 contract html-escapes that argument,
# so the angle brackets surfaced as literal text in the Library / Research
# / Portfolio / Backtest tabs of pedesk.app.
#
# The fix is a single chokepoint: every value that flows into a ck_*
# primitive gets stripped of every HTML tag here, so the helper only
# ever sees raw text/numbers. Visual formatting belongs to the parent
# container's CSS class (.ck-kpi-value.sc-num, .ck-table .sc-num, etc.),
# never to injected HTML strings on the data path.
_HTML_TAG_RE = _re.compile(r"<[^>]*>")


def ck_sanitize_value(value: object) -> str:
    """Strip every HTML tag from a data value before it reaches the DOM.

    Use this at any backend → response boundary where the payload may
    have been built by a renderer that mixed raw markup into numeric
    fields. The output is plain text (no angle brackets, no entities
    introduced) and is safe to feed into html.escape().
    """
    if value is None:
        return ""
    return _HTML_TAG_RE.sub("", str(value))

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
    # P23: accent-2 — third palette token. Aliases the clinical teal
    # so callers can use the spec-vocabulary name without coupling
    # to the historical "teal" key.
    "accent_2":     "#2fb3ad",
    "accent_2_ink": "#0f5e5a",

    # Status
    "positive": "#0a8a5f",
    "warning":  "#b8732a",
    "negative": "#b5321e",
    "critical": "#8a1e0e",

    # Legacy-compatibility aliases — every page renderer in
    # rcm_mc/ui/data_public/* and rcm_mc/ui/chartis/home_page.py
    # references these keys directly. The v2 rework re-named them
    # (rule, rule_2, text_faint) but left the legacy lookups unfixed,
    # which manifested as KeyError crashes inside table renderers
    # and the home page's Pipeline Funnel panel. Aliasing here keeps
    # the dispatcher contract intact without rewriting every caller.
    "border":      "#d6cfc3",   # alias of "rule"
    "border_dim":  "#c5bdae",   # alias of "rule_2"
    "row_stripe":  "#ece6db",   # alias of "panel_alt"
    "accent":      "#1F4E78",   # Chartis blue from CLAUDE.md spec
    "text_muted":  "#7a8699",   # alias of "text_faint"
    "text_link":   "#1F4E78",   # alias of "accent"
    "text_secondary": "#465366",  # alias of "text_dim"
    "bg_tertiary": "#ece6db",   # alias of "panel_alt"
    "brand_accent":"#1F4E78",   # alias of "accent"
    "brand_primary":"#0b2341",  # alias of "navy"
}

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
    """White panel with navy header strip and optional [CODE] tag.

    ``body_html`` is treated as authored markup and passed through
    untouched — it is the panel's content area and is built by the
    surrounding renderer. ``title`` and ``code`` are data labels: they
    are sanitized + escaped because they regularly come from upstream
    formatters that may have wrapped a value in <span> markup.
    """
    head = ""
    if title or code:
        title_html = f'<div class="ck-panel-title">{_esc(ck_sanitize_value(title))}</div>' if title else '<div class="ck-panel-title"></div>'
        code_html = f'<div class="ck-panel-code">[{_esc(ck_sanitize_value(code))}]</div>' if code else ""
        head = f'<div class="ck-panel-head">{title_html}{code_html}</div>'
    return f'<section class="ck-panel">{head}<div class="ck-panel-body">{body_html}</div></section>'


def ck_section_header(
    title: str,
    eyebrow: Optional[str] = None,
    count: Optional[int] = None,
    *,
    code: Optional[str] = None,
) -> str:
    """Render a section header.

    Positional contract preserves the legacy ``(title, subtitle, count)``
    shape; v2 had renamed ``subtitle`` to ``eyebrow`` and made it
    keyword-only, which broke every existing call site under
    CHARTIS_UI_V2=1. ``count`` is rendered as a small badge after the
    title.
    """
    eb = f'<div class="sc-eyebrow">{_esc(ck_sanitize_value(eyebrow))}</div>' if eyebrow else ""
    cd = f'<div class="ck-section-code">[{_esc(ck_sanitize_value(code))}]</div>' if code else ""
    cnt = f'<span class="ck-section-count">{int(count)}</span>' if count is not None else ""
    return (
        '<header class="ck-section-header">'
        f'{eb}<h2 class="sc-h2">{_esc(ck_sanitize_value(title))}{cnt}</h2>{cd}'
        "</header>"
    )


def ck_table(
    rows: Sequence[Mapping[str, object]],
    columns: Sequence[Mapping[str, str]],
    *,
    dense: bool = False,
    caption: str = "",
    sortable: bool = False,
    id: str = "ck-tbl",
) -> str:
    """Emit a Bloomberg-density table with tabular-nums numerics.

    ``columns`` is a list of ``{"key": "ebitda", "label": "EBITDA",
    "align": "right", "kind": "currency"}`` dicts. ``kind`` is optional
    and hints at cell formatting.

    The legacy kit accepted ``caption``, ``sortable``, and ``id`` kwargs;
    they are kept here for call-site compatibility — caption renders as
    a <caption> element, sortable adds a hint class, and id sets the
    table's HTML id.
    """
    cls = "ck-table" + (" ck-dense" if dense else "") + (" ck-sortable" if sortable else "")
    cap = f"<caption>{_esc(ck_sanitize_value(caption))}</caption>" if caption else ""
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
                val = _esc(ck_sanitize_value(raw) if raw is not None else "—")
            num_cls = " sc-num" if kind in ("currency", "percent", "number") else ""
            cells.append(
                f'<td class="align-{_esc(c.get("align", "left"))}{num_cls}">{val}</td>'
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        f'<table class="{cls}" id="{_esc(id)}">'
        f"{cap}"
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def ck_kpi_block(
    label: str,
    value: object,
    sub: Optional[str] = None,
    trend: Optional[str] = None,
    *,
    code: Optional[str] = None,
) -> str:
    """Render a KPI tile.

    Positional contract preserves the legacy ``(label, value, unit, delta)``
    shape: the third positional was historically a short subtitle string
    (e.g. "in corpus", "MOIC < 1.0x"), and the fourth a delta indicator.
    The v2 rework renamed them to ``sub`` and ``trend`` and made them
    keyword-only — but every page renderer in ``rcm_mc/ui/data_public/``
    still calls with three positional args, which raised TypeError under
    CHARTIS_UI_V2=1. Restoring positional acceptance keeps existing
    call sites working unchanged.
    """
    trend_html = ""
    if trend:
        clean_trend = ck_sanitize_value(trend)
        tone = (
            "positive" if clean_trend.startswith("+")
            else "negative" if clean_trend.startswith("-")
            else "neutral"
        )
        trend_html = f'<span class="ck-kpi-trend tone-{tone}">{_esc(clean_trend)}</span>'
    sub_html = f'<div class="ck-kpi-sub">{_esc(ck_sanitize_value(sub))}</div>' if sub else ""
    code_html = f'<div class="ck-kpi-code">[{_esc(ck_sanitize_value(code))}]</div>' if code else ""
    return (
        '<div class="ck-kpi">'
        f'{code_html}'
        f'<div class="ck-kpi-label">{_esc(ck_sanitize_value(label))}</div>'
        f'<div class="ck-kpi-value sc-num">{_esc(ck_sanitize_value(value))}{trend_html}</div>'
        f'{sub_html}'
        "</div>"
    )


def ck_signal_badge(text: str, *, tone: str = "neutral") -> str:
    tone = tone if tone in ("positive", "warning", "negative", "critical", "neutral") else "neutral"
    return f'<span class="ck-badge tone-{tone}">{_esc(ck_sanitize_value(text))}</span>'


# ---------------------------------------------------------------------------
# Command palette (⌘K) — feed it the module catalog
# ---------------------------------------------------------------------------

# P46: default route catalog so cmd-K works on every page without
# per-page wiring. Entries cover the main partner-facing surfaces;
# pages that want to ship deeper search (deals by name, glossary,
# audit events) pass a richer ``palette_modules`` to chartis_shell
# and override this default.
_DEFAULT_PALETTE_ROUTES: list[Mapping[str, str]] = [
    {"id": "home",         "title": "Home",                 "route": "/home"},
    {"id": "now",          "title": "30-second view",       "route": "/now"},
    {"id": "library",      "title": "Library — Corpus",     "route": "/library"},
    {"id": "pipeline",     "title": "Pipeline",             "route": "/pipeline"},
    {"id": "alerts",       "title": "Alerts",               "route": "/alerts"},
    {"id": "watchlist",    "title": "Watchlist",            "route": "/watchlist"},
    {"id": "escalations",  "title": "Escalations",          "route": "/escalations"},
    {"id": "portfolio",    "title": "Portfolio overview",   "route": "/portfolio"},
    {"id": "diligence",    "title": "Diligence (Checklist)","route": "/diligence"},
    {"id": "checklist",    "title": "Checklist",            "route": "/diligence/checklist"},
    {"id": "ingest",       "title": "Ingestion",            "route": "/diligence/ingest"},
    {"id": "benchmarks",   "title": "Benchmarks",           "route": "/diligence/benchmarks"},
    {"id": "risk",         "title": "Risk Workbench",       "route": "/diligence/risk-workbench"},
    {"id": "bridge",       "title": "Bridge Audit",         "route": "/diligence/bridge-audit"},
    {"id": "deal_mc",      "title": "Deal Monte Carlo",     "route": "/diligence/deal-mc"},
    {"id": "bear",         "title": "Bear Case",            "route": "/diligence/bear-case"},
    {"id": "covenant",     "title": "Covenant Stress",      "route": "/diligence/covenant-stress"},
    {"id": "payer",        "title": "Payer Stress",         "route": "/diligence/payer-stress"},
    {"id": "exit",         "title": "Exit Timing",          "route": "/diligence/exit-timing"},
    {"id": "ic_packet",    "title": "IC Packet",            "route": "/diligence/ic-packet"},
    {"id": "lp_update",    "title": "LP Update",            "route": "/lp-update"},
    {"id": "audit",        "title": "Audit log",            "route": "/audit"},
    {"id": "methodology",  "title": "Methodology",          "route": "/methodology"},
    {"id": "data_catalog", "title": "Data catalog",         "route": "/data/catalog"},
    {"id": "data_refresh", "title": "Data refresh",         "route": "/data/refresh"},
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

_CSS_LINK = '<link rel="stylesheet" href="/static/chartis_tokens.css">'

# Inline fallback — if static serving of chartis_tokens.css isn't wired up,
# the class names defined here keep pages readable. Prefer the linked file.
_CSS_INLINE_FALLBACK = """
<style>
  /* P19: motion tokens. The shared timing/easing language for the
     platform. Three durations:
       fast (120ms) → microinteractions like a button press
       base (200ms) → state transitions like a modal open
       slow (360ms) → ambient movement like a page entrance
     Three easings: standard for everything; decelerate for elements
     entering view; accelerate for elements leaving view. Components
     should reach for these tokens instead of hardcoding times. */
  :root {
    --motion-fast: 120ms;
    --motion-base: 200ms;
    --motion-slow: 360ms;
    --ease-standard: cubic-bezier(0.2, 0.0, 0, 1.0);
    --ease-decelerate: cubic-bezier(0, 0, 0, 1);
    --ease-accelerate: cubic-bezier(0.3, 0, 1, 1);
    /* P23: third palette accent — clinical teal. Reads as
       "healthcare" and complements the navy/parchment chrome.
       Use sparingly: eyebrow tags, hero-section corner triangles,
       section-divider underlines, primary-button hover. NEVER on
       body text, table backgrounds, or major surface fills. */
    --accent-2: var(--sc-teal);
    --accent-2-ink: var(--sc-teal-ink);
  }
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
  /* P9: format_value()'s missing-data marker. ``muted`` alone keeps
     the dim foreground; ``unpopulated`` adds italics + a slightly
     reduced font-size so the partner can spot at a glance which
     metrics are not yet computed (vs. a real zero or a real number). */
  .muted { color:var(--sc-text-faint); }
  .unpopulated { font-style:italic; font-size:0.92em; letter-spacing:0; text-transform:none; }
  /* P11: kpi_strip() — horizontal KPI row.
     The grid-template-columns is set inline by the helper because
     the column count is a function of the items list. CSS here owns
     typography, tone coloring, and the responsive breakpoints. */
  .kpi-strip { display:grid; gap:24px; align-items:start; padding:18px 0; }
  .kpi-strip .kpi-item { display:flex; flex-direction:column; gap:4px; min-width:0; }
  .kpi-strip .kpi-label { font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); }
  .kpi-strip .kpi-value { font-family:var(--sc-serif); font-size:30px; font-weight:500; line-height:1.1; color:var(--sc-navy); font-variant-numeric:tabular-nums; }
  .kpi-strip .kpi-sublabel { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); margin-top:2px; }
  .kpi-strip .kpi-item.tone-positive .kpi-value { color:var(--sc-positive); }
  .kpi-strip .kpi-item.tone-negative .kpi-value { color:var(--sc-negative); }
  .kpi-strip .kpi-item.tone-warning  .kpi-value { color:var(--sc-warning); }
  .kpi-strip-dense { gap:16px; padding:12px 0; }
  .kpi-strip-dense .kpi-value { font-size:22px; }
  .kpi-strip-dense .kpi-label { font-size:10px; letter-spacing:0.12em; }
  @media (max-width:768px) { .kpi-strip { grid-template-columns:repeat(2,1fr) !important; } }
  @media (max-width:480px) { .kpi-strip { grid-template-columns:1fr !important; } }
  /* P90: mobile read-only responsive layout. LP Update, Portfolio
     overview, deal page, alerts list, /now all need to stay
     readable on iPhone-class viewports. Below 768px: nav collapses
     to a single row, tables scroll horizontally (don't wrap), and
     the main column drops its outer padding. */
  @media (max-width:768px) {
    .ck-topbar-inner { flex-wrap:wrap; gap:10px; padding:10px 16px; }
    .ck-nav { gap:14px; flex-wrap:wrap; }
    .ck-nav a { padding:4px 0; }
    .ck-search { min-width:0; flex:1; }
    .ck-main { padding:16px 12px; }
    .ck-breadcrumbs { padding:8px 12px; flex-wrap:wrap; }
    .data-table-wrap, .ck-table-wrap { overflow-x:auto; }
    .data-table, .ck-table { min-width:560px; }
    .recommendation-block { grid-template-columns:6px 1fr; }
    .recommendation-block .rec-dollars { grid-column:2; align-self:start; margin-top:8px; }
    .freshness-rail { flex-wrap:wrap; gap:8px; }
    .activity-rail { padding:10px 12px; }
    .preview-panel { display:none; }  /* preview is desktop-only */
  }
  /* P13: preview_panel() — right-rail ghosted output preview.
     The 50% opacity is on .preview-ghost, not the panel chrome, so
     the title and caption stay legible while the body reads as
     "this is what you'll see, not a real run". */
  .preview-panel { border:1px solid var(--sc-rule); padding:18px 20px; background:var(--sc-bone); border-radius:2px; }
  .preview-panel .preview-title { font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); margin-bottom:12px; }
  .preview-panel .preview-ghost { opacity:0.5; pointer-events:none; }
  .preview-panel .preview-caption { font-family:var(--sc-serif); font-style:italic; font-size:13px; color:var(--sc-text-faint); margin-top:14px; line-height:1.55; }
  /* P14: recent_runs() — per-module continuity rail. */
  .recent-runs { margin-top:24px; }
  .recent-runs-header { font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); margin-bottom:10px; }
  .recent-runs-empty { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); padding:8px 0; }
  .recent-runs-list { display:flex; flex-direction:column; }
  .recent-runs-row { display:flex; gap:12px; align-items:baseline; padding:8px 0; border-bottom:1px solid var(--sc-rule); text-decoration:none; color:var(--sc-text); }
  .recent-runs-row:hover { background:var(--sc-bone); }
  .recent-runs-deal { font-family:var(--sc-sans); font-weight:500; min-width:140px; color:var(--sc-navy); }
  .recent-runs-ts { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); min-width:120px; }
  .recent-runs-summary { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-dim); }
  /* P15: data_table() — standardised table body. */
  .data-table { width:100%; border-collapse:collapse; font-size:13px; }
  .data-table thead th { background:var(--sc-bone); color:var(--sc-text-dim); font-family:var(--sc-sans); font-weight:600; font-size:11px; letter-spacing:0.1em; text-transform:uppercase; padding:8px 12px; border-bottom:1px solid var(--sc-rule); text-align:left; }
  .data-table.sticky-header thead th { position:sticky; top:0; z-index:1; }
  .data-table tbody td { padding:8px 12px; border-bottom:1px solid var(--sc-rule); }
  .data-table.striped tbody tr:nth-child(odd) { background:var(--sc-panel_alt); }
  .data-table.hover tbody tr:hover { background:var(--sc-bone); }
  .data-table.dense thead th, .data-table.dense tbody td { padding:5px 10px; font-size:12px; }
  .data-table .align-right { text-align:right; }
  .data-table .align-center { text-align:center; }
  .data-table .sc-num { font-family:var(--sc-mono); font-variant-numeric:tabular-nums; }
  .data-table th.sortable { cursor:pointer; user-select:none; }
  .data-table th .sort-marker { color:var(--sc-text-faint); margin-left:6px; font-size:9px; letter-spacing:0; }
  .data-table th.sort-asc .sort-marker::before { content:"\\25B2"; color:var(--sc-navy); }
  .data-table th.sort-asc .sort-marker { font-size:0; }
  .data-table th.sort-asc .sort-marker::before { font-size:11px; }
  .data-table th.sort-desc .sort-marker::before { content:"\\25BC"; color:var(--sc-navy); }
  .data-table th.sort-desc .sort-marker { font-size:0; }
  .data-table th.sort-desc .sort-marker::before { font-size:11px; }
  /* P62: platform health footer — version, tests, freshness, etc. */
  .platform-health-footer { padding:10px 16px; margin-top:24px; border-top:1px solid var(--sc-rule); font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); display:flex; flex-wrap:wrap; gap:6px; justify-content:center; }
  .platform-health-footer .ph-item { color:var(--sc-text-faint); font-variant-numeric:tabular-nums; }
  /* P61: packet metadata footer. */
  .packet-footer { display:flex; flex-wrap:wrap; gap:10px 14px; align-items:center; padding:12px 0; margin-top:30px; border-top:1px solid var(--sc-rule); font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); }
  .packet-footer code { font-family:var(--sc-mono); color:var(--sc-text-dim); background:var(--sc-bone); padding:2px 6px; border-radius:2px; }
  .packet-footer .packet-hash, .packet-footer .packet-rebuilt { color:var(--sc-text-dim); font-variant-numeric:tabular-nums; }
  .packet-footer .packet-action { margin:0; }
  .packet-footer .btn-tertiary { font-family:var(--sc-sans); font-size:11px; padding:2px 0; }
  .packet-footer .packet-download { margin-left:auto; }
  /* P91: demo-mode banner. Warm orange accent so demo data reads
     visually distinct from real data. */
  .demo-mode-banner { display:flex; align-items:center; gap:12px; padding:8px 16px; background:#fff7ed; border-bottom:1px solid #fed7aa; color:#9a3412; font-family:var(--sc-mono); font-size:11px; letter-spacing:0.06em; }
  .demo-mode-banner .demo-mode-eyebrow { font-weight:700; letter-spacing:0.16em; text-transform:uppercase; }
  .demo-mode-banner .demo-mode-detail { color:#7c2d12; }
  .demo-mode-banner .demo-reset { margin-left:auto; }
  .demo-mode-banner .demo-reset button { font-family:var(--sc-sans); font-size:11px; padding:4px 10px; background:transparent; color:#9a3412; border:1px solid #fed7aa; border-radius:2px; cursor:pointer; }
  /* P89: keyboard-shortcut help overlay. */
  .kbd-help { position:fixed; inset:0; background:rgba(6,22,38,0.4); display:flex; align-items:center; justify-content:center; z-index:130; }
  .kbd-help[hidden] { display:none; }
  .kbd-help-card { background:#fff; border:1px solid var(--sc-rule); padding:24px 28px; min-width:380px; max-width:560px; box-shadow:var(--sc-shadow-3); }
  .kbd-help-card h4 { font-family:var(--sc-serif); font-style:italic; font-size:18px; color:var(--sc-navy); margin:0 0 14px; }
  .kbd-help-card dl { display:grid; grid-template-columns:auto 1fr; gap:8px 18px; font-size:13px; margin:0; }
  .kbd-help-card dt { font-family:var(--sc-mono); color:var(--sc-navy); }
  .kbd-help-card dd { color:var(--sc-text-dim); margin:0; }
  /* P98: per-severity glyph for color-blind / B&W readability. */
  .severity-glyph { display:inline-block; font-size:0.85em; margin-right:6px; vertical-align:baseline; }
  .severity-glyph.tone-positive { color:var(--sc-positive); }
  .severity-glyph.tone-warning  { color:var(--sc-warning); }
  .severity-glyph.tone-negative { color:var(--sc-negative); }
  .severity-glyph.tone-muted    { color:var(--sc-text-faint); }
  /* P88: next-action nudge. */
  .next-action-nudge { display:flex; align-items:baseline; gap:10px; padding:10px 16px; margin:18px 0; background:var(--sc-bone); border-left:3px solid var(--accent-2); }
  .next-action-nudge .nan-eyebrow { font-family:var(--sc-mono); font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint); }
  .next-action-nudge .nan-link { font-family:var(--sc-serif); font-style:italic; font-size:15px; color:var(--sc-navy); text-decoration:none; }
  .next-action-nudge .nan-link:hover { color:var(--accent-2-ink); }
  /* P87: inline-validation pill. */
  .validation-pill { display:inline-block; padding:2px 8px; font-family:var(--sc-mono); font-size:11px; border-radius:2px; margin-left:8px; border:1px solid currentColor; }
  .validation-pill.tone-warning  { color:var(--sc-warning); }
  .validation-pill.tone-negative { color:var(--sc-negative); }
  /* P84: percent slider with distribution preview. */
  .percent-slider { margin:14px 0; }
  .percent-slider .ps-label { font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); display:block; margin-bottom:6px; }
  .percent-slider .ps-row { display:flex; align-items:center; gap:14px; }
  .percent-slider .ps-input { flex:1; accent-color:var(--sc-navy); }
  .percent-slider .ps-output { font-family:var(--sc-mono); font-variant-numeric:tabular-nums; font-size:13px; min-width:60px; color:var(--sc-navy); }
  .percent-slider .ps-distribution { color:var(--sc-text-faint); margin-top:4px; }
  /* P77: tour overlay. */
  .tour-overlay { position:fixed; right:32px; bottom:32px; max-width:360px; padding:18px 22px; background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-3); z-index:120; }
  .tour-overlay[hidden] { display:none; }
  .tour-overlay .tour-steps { list-style:none; padding:0; margin:0; }
  .tour-overlay .tour-step-title { font-family:var(--sc-serif); font-size:16px; color:var(--sc-navy); margin:0 0 6px; }
  .tour-overlay .tour-step-body { font-size:13px; color:var(--sc-text-dim); line-height:1.55; margin:0; }
  .tour-overlay .tour-controls { display:flex; align-items:center; gap:10px; margin-top:14px; }
  .tour-overlay .tour-progress { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); margin-left:auto; }
  .tour-overlay button { font-family:var(--sc-sans); font-size:12px; padding:6px 12px; cursor:pointer; }
  .tour-overlay .tour-skip { background:transparent; border:0; color:var(--sc-text-faint); }
  .tour-overlay .tour-prev { background:transparent; border:1px solid var(--sc-rule); color:var(--sc-text-dim); }
  .tour-overlay .tour-next { background:var(--sc-navy); color:#fff; border:0; }
  /* P60: entity activity rail. */
  .activity-rail { margin:24px 0 0; padding:14px 18px; background:var(--sc-bone); border:1px solid var(--sc-rule); border-radius:2px; }
  .activity-rail-header { font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); margin:0 0 8px; }
  .activity-rail-list { list-style:none; padding:0; margin:0 0 8px; font-family:var(--sc-mono); font-size:11.5px; color:var(--sc-text-dim); line-height:1.85; }
  .activity-rail-list .activity-ts { color:var(--sc-text-faint); font-variant-numeric:tabular-nums; }
  .activity-rail-list .activity-actor { color:var(--sc-navy); font-weight:600; }
  .activity-rail-list .activity-action { color:var(--sc-text); }
  .activity-rail-empty { font-family:var(--sc-mono); font-size:12px; }
  .activity-rail-more { font-family:var(--sc-sans); font-size:12px; color:var(--accent-2-ink); text-decoration:none; }
  .activity-rail-more:hover { color:var(--sc-navy); }
  /* P58: per-page freshness rail. */
  .freshness-rail { display:flex; align-items:center; gap:18px; padding:8px 0; font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); border-bottom:1px dashed var(--sc-rule); }
  .freshness-rail .freshness-item { display:inline-flex; align-items:baseline; gap:4px; }
  .freshness-rail .freshness-label { color:var(--sc-text-faint); }
  .freshness-rail .freshness-value { color:var(--sc-text-dim); font-variant-numeric:tabular-nums; }
  .freshness-rail .freshness-rebuild { margin-left:auto; }
  /* P57: engine flagship cards. */
  .engine-flagship { background:#fff; border:1px solid var(--sc-rule); padding:24px 28px; display:flex; flex-direction:column; gap:10px; }
  .engine-flagship-eyebrow { font-family:var(--sc-mono); font-size:11px; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-faint); }
  .engine-flagship-headline { font-family:var(--sc-serif); font-style:italic; font-size:22px; color:var(--sc-navy); margin:0; line-height:1.2; max-width:18ch; }
  .engine-flagship-blurb { font-size:13px; color:var(--sc-text-dim); line-height:1.55; margin:0; max-width:48ch; }
  .engine-flagship-link { font-family:var(--sc-sans); font-size:13px; font-weight:600; color:var(--accent-2-ink); text-decoration:none; margin-top:auto; }
  .engine-flagship-link:hover { color:var(--sc-navy); }
  /* P50: column picker on dense tables. */
  .data-table-wrap { position:relative; }
  .column-picker { position:absolute; top:6px; right:6px; z-index:2; }
  .column-picker > summary { cursor:pointer; font-family:var(--sc-sans); font-size:11px; color:var(--sc-text-dim); padding:4px 10px; border:1px solid var(--sc-rule); background:#fff; list-style:none; user-select:none; border-radius:2px; }
  .column-picker > summary::-webkit-details-marker { display:none; }
  .column-picker[open] > summary { color:var(--sc-navy); border-color:var(--sc-navy); }
  .column-picker .column-picker-menu { position:absolute; top:28px; right:0; background:#fff; border:1px solid var(--sc-rule); padding:8px 12px; min-width:180px; box-shadow:var(--sc-shadow-1); }
  .column-picker .column-picker-item { display:block; font-family:var(--sc-sans); font-size:12px; color:var(--sc-text); padding:3px 0; cursor:pointer; }
  .data-table th.col-hidden, .data-table td.col-hidden { display:none; }
  /* P49: bulk-actions sticky bar. */
  .bulk-actions-bar { position:fixed; left:50%; bottom:24px; transform:translateX(-50%); display:flex; align-items:center; gap:18px; padding:12px 22px; background:var(--sc-navy); color:var(--sc-on-navy); border-radius:4px; box-shadow:var(--sc-shadow-3); z-index:50; font-family:var(--sc-sans); font-size:13px; }
  .bulk-actions-bar[hidden] { display:none; }
  .bulk-actions-bar .bulk-count { font-weight:600; }
  .bulk-actions-bar .bulk-count-n { font-family:var(--sc-mono); font-variant-numeric:tabular-nums; margin-right:4px; }
  .bulk-actions-bar .bulk-actions-buttons { display:flex; gap:10px; }
  .bulk-actions-bar .bulk-action-btn { color:var(--sc-on-navy); padding:6px 12px; border:1px solid var(--sc-on-navy-faint); border-radius:2px; cursor:pointer; text-decoration:none; }
  .bulk-actions-bar .bulk-action-btn:hover { background:var(--sc-navy_2); }
  .bulk-actions-bar .bulk-clear { background:transparent; border:0; color:var(--sc-on-navy); font-size:18px; cursor:pointer; padding:0 4px; }
  /* P42: row-action menus on dense tables. Hidden until row hover or
     keyboard focus so the dense view isn't visually polluted. On
     touch (no hover) the toggle button is always shown. */
  .data-table .row-actions { position:relative; display:inline-block; }
  .data-table .row-actions-toggle { background:transparent; border:0; cursor:pointer; color:var(--sc-text-faint); padding:2px 8px; opacity:0; transition:opacity var(--motion-fast) var(--ease-standard); font-size:18px; }
  .data-table tbody tr:hover .row-actions-toggle,
  .data-table tbody tr:focus-within .row-actions-toggle { opacity:1; }
  .data-table .row-actions-menu { display:none; position:absolute; right:0; top:24px; background:#fff; border:1px solid var(--sc-rule); padding:6px 0; min-width:140px; z-index:5; box-shadow:var(--sc-shadow-1); }
  .data-table .row-actions:hover .row-actions-menu,
  .data-table .row-actions:focus-within .row-actions-menu { display:block; }
  .data-table .row-action-link { display:block; padding:6px 14px; font-family:var(--sc-sans); font-size:12px; color:var(--sc-text); text-decoration:none; }
  .data-table .row-action-link:hover { background:var(--sc-bone); color:var(--sc-navy); }
  @media (hover:none) {
    .data-table .row-actions-toggle { opacity:1; }
  }
  /* P16: recommendation_block() — banded conclusion card. */
  .recommendation-block { display:grid; grid-template-columns:6px 1fr auto; gap:18px; margin:32px 0 0; padding:20px 24px; background:var(--sc-bone); border:1px solid var(--sc-rule); }
  .recommendation-block .rec-rail { background:var(--sc-text-faint); }
  .recommendation-block.confidence-high  .rec-rail { background:var(--sc-positive); }
  .recommendation-block.confidence-medium .rec-rail { background:var(--sc-warning); }
  .recommendation-block.confidence-low   .rec-rail { background:var(--sc-negative); }
  .recommendation-block .rec-verdict { font-family:var(--sc-serif); font-style:italic; font-size:18px; color:var(--sc-navy); margin-bottom:6px; }
  .recommendation-block .rec-action  { font-family:var(--sc-sans); font-size:15px; font-weight:600; color:var(--sc-text); margin-bottom:10px; line-height:1.45; }
  .recommendation-block .rec-reasoning { margin:0; padding-left:18px; color:var(--sc-text-dim); font-size:13px; line-height:1.6; }
  .recommendation-block .rec-reasoning li { margin:2px 0; }
  .recommendation-block .rec-dollars { font-family:var(--sc-serif); font-size:24px; font-weight:500; color:var(--sc-navy); align-self:center; font-variant-numeric:tabular-nums; }
  /* P74: metric_with_percentile() — corpus-percentile context. */
  .metric-percentile { font-family:var(--sc-mono); font-size:0.78em; color:var(--sc-text-faint); margin-left:6px; }
  /* P73: metric_with_delta() — Δ vs prior snapshot. */
  .metric-delta { font-family:var(--sc-mono); font-size:0.78em; margin-left:6px; font-variant-numeric:tabular-nums; }
  .metric-delta.tone-positive { color:var(--sc-positive); }
  .metric-delta.tone-negative { color:var(--sc-negative); }
  .metric-delta-period { color:var(--sc-text-faint); margin-left:4px; }
  /* P71: conformal-coverage calibration badge. */
  .calibration-badge { display:inline-flex; align-items:baseline; gap:8px; padding:6px 12px; border:1px solid var(--sc-rule); font-family:var(--sc-mono); font-size:11.5px; color:var(--sc-text-dim); border-radius:2px; }
  .calibration-badge.tone-positive { border-color:var(--sc-positive); color:var(--sc-positive); }
  .calibration-badge.tone-warning  { border-color:var(--sc-warning); color:var(--sc-warning); }
  .calibration-badge.tone-negative { border-color:var(--sc-negative); color:var(--sc-negative); }
  .calibration-badge .cb-label { color:var(--sc-text-faint); }
  .calibration-badge .cb-value { font-weight:600; font-variant-numeric:tabular-nums; }
  .calibration-badge .cb-target { color:var(--sc-text-faint); }
  .calibration-badge .cb-detail { color:var(--sc-text-faint); }
  /* P70: variance-decomposition tornado. */
  .variance-tornado { margin:18px 0; }
  .variance-tornado .vt-header { font-family:var(--sc-serif); font-style:italic; font-size:15px; color:var(--sc-navy); margin:0 0 12px; }
  .variance-tornado .vt-row { display:grid; grid-template-columns:200px 1fr 48px; gap:12px; align-items:center; padding:4px 0; font-family:var(--sc-mono); font-size:11.5px; }
  .variance-tornado .vt-label { color:var(--sc-text-dim); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .variance-tornado .vt-track { background:var(--sc-rule_2); height:8px; border-radius:1px; overflow:hidden; }
  .variance-tornado .vt-bar { display:block; height:100%; background:var(--sc-navy); }
  .variance-tornado .vt-pct { text-align:right; color:var(--sc-text); font-variant-numeric:tabular-nums; }
  /* P69: "diligence is complete enough" banner. */
  .diligence-complete-banner { display:flex; flex-direction:column; gap:6px; padding:18px 22px; margin:18px 0; background:linear-gradient(90deg, rgba(10,138,95,0.08), transparent); border-left:6px solid var(--sc-positive); }
  .diligence-complete-banner .dcb-eyebrow { font-family:var(--sc-mono); font-size:11px; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-positive); }
  .diligence-complete-banner .dcb-headline { font-family:var(--sc-serif); font-style:italic; font-size:20px; color:var(--sc-navy); }
  .diligence-complete-banner .dcb-detail { font-family:var(--sc-sans); font-size:13px; color:var(--sc-text-dim); }
  /* P68: model verdict header — top-of-page banner on Risk Workbench. */
  .model-verdict { display:grid; grid-template-columns:auto auto 1fr; gap:14px; align-items:baseline; padding:14px 20px; margin:18px 0; background:var(--sc-bone); border-left:6px solid var(--sc-text-faint); }
  .model-verdict.tone-positive { border-left-color:var(--sc-positive); }
  .model-verdict.tone-warning  { border-left-color:var(--sc-warning); }
  .model-verdict.tone-negative { border-left-color:var(--sc-negative); }
  .model-verdict.tone-critical { border-left-color:var(--sc-critical); }
  .model-verdict-eyebrow { font-family:var(--sc-mono); font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint); }
  .model-verdict-label { font-family:var(--sc-serif); font-style:italic; font-size:18px; color:var(--sc-navy); font-weight:500; }
  .model-verdict-summary { font-family:var(--sc-sans); font-size:13px; color:var(--sc-text-dim); }
  /* P65: metric_with_dollars() — muted dollar-context span. */
  .dollar-context { font-family:var(--sc-mono); font-size:0.78em; color:var(--sc-text-faint); margin-left:6px; font-variant-numeric:tabular-nums; }
  /* P33: metric_with_interval() — conformal P10/P90 inline band. */
  .metric-interval { font-family:var(--sc-mono); font-size:0.75em; color:var(--sc-text-faint); margin-left:6px; font-variant-numeric:tabular-nums; }
  /* P17: provenance_marker() — inline source glyph next to a number. */
  .prov { font-size:0.7em; vertical-align:baseline; margin-left:4px; cursor:help; }
  .prov-observed  { color:var(--sc-positive); }
  .prov-predicted { color:var(--sc-warning); }
  .prov-simulated { color:var(--sc-teal-ink); }
  .prov-derived   { color:var(--sc-text-dim); }
  .prov-benchmark { color:var(--sc-text-faint); }
  .prov-unknown   { color:var(--sc-text-faint); }
  /* P18: caveats_disclosure() — collapsed-by-default modeling caveats. */
  .caveats-disclosure { margin:24px 0 0; color:var(--sc-text-dim); }
  .caveats-disclosure > summary { cursor:pointer; font-family:var(--sc-serif); font-style:italic; font-size:13px; color:var(--sc-text-dim); padding:6px 0; list-style:none; }
  .caveats-disclosure > summary::-webkit-details-marker { display:none; }
  .caveats-disclosure > summary::before { content:"›"; display:inline-block; margin-right:8px; transition:transform var(--motion-fast) var(--ease-standard); }
  .caveats-disclosure[open] > summary::before { transform:rotate(90deg); }
  .caveats-disclosure > ul { margin:8px 0 0 22px; padding:0; font-size:12.5px; line-height:1.6; }
  .caveats-disclosure > ul > li { margin:4px 0; }
  /* P75: "Not yet modeled" subsection inside the caveats. */
  .caveats-disclosure .caveats-not-modeled-header { font-family:var(--sc-mono); font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint); margin:14px 0 4px 22px; }
  .caveats-disclosure .caveats-not-modeled li { color:var(--sc-text-dim); font-style:italic; }
  /* P20: action_button() — three weight tiers + busy/duration. */
  .btn-primary, .btn-secondary, .btn-tertiary {
    display:inline-flex; align-items:center; gap:8px;
    font-family:var(--sc-sans); font-size:13px; font-weight:600;
    letter-spacing:0.04em; text-decoration:none; cursor:pointer;
    border-radius:2px;
    transition:background var(--motion-fast) var(--ease-standard),
               color var(--motion-fast) var(--ease-standard);
  }
  .btn-primary { padding:10px 20px; background:var(--sc-teal); color:#fff; border:1px solid var(--sc-teal); }
  .btn-primary:hover { background:var(--sc-teal-ink); border-color:var(--sc-teal-ink); }
  .btn-secondary { padding:10px 18px; background:transparent; color:var(--sc-navy); border:1px solid var(--sc-navy); }
  .btn-secondary:hover { background:var(--sc-bone); }
  .btn-tertiary { padding:6px 0; background:transparent; color:var(--sc-accent); border:0; }
  .btn-tertiary:hover { color:var(--sc-navy); text-decoration:underline; }
  .btn-primary[data-busy="true"], .btn-secondary[data-busy="true"], .btn-tertiary[data-busy="true"] { opacity:0.6; pointer-events:none; }
  .btn-duration { font-family:var(--sc-mono); font-size:11px; font-weight:400; color:currentColor; opacity:0.7; }
  .btn-consequential { box-shadow:0 0 0 1px var(--sc-warning); }
  /* P21: page-title typography — serif italic is the strongest
     typographic move the kit has and now applies platform-wide.
     Two equivalent rules so pages get the typography either way:
     explicit ``class="page-title"`` on the h1, or any h1 inside
     the main shell column. */
  .page-title, .ck-main h1 {
    font-family:var(--sc-serif);
    font-style:italic;
    font-weight:500;
    font-size:2.25rem;
    line-height:1.15;
    color:var(--sc-navy);
    letter-spacing:-0.01em;
    margin:0 0 8px 0;
  }
  .ck-main h1.bare-title, .ck-main h1[data-no-title-style] {
    /* Opt-out: pages that need a non-page-title h1 (e.g. modal body)
       can carry the bare-title class to bypass the kit typography. */
    font-family:var(--sc-sans); font-style:normal;
    font-weight:600; font-size:1.4rem; letter-spacing:0;
  }
  /* P41: subtitle slot. Rendered at 0.7x the page-title size, muted,
     no italic — the subtitle is descriptive context, not an equal-
     weight billing line. Sits directly below the H1 inside the main
     column. */
  .ck-main .page-subtitle {
    font-family:var(--sc-sans);
    font-style:normal;
    font-weight:400;
    font-size:1.05rem;
    color:var(--sc-text-dim);
    margin:-2px 0 16px 0;
    line-height:1.4;
  }
  /* P43: form_section() — italic-serif subheader for input groups. */
  .form-section { margin:18px 0 22px; }
  .form-section .form-section-label {
    font-family:var(--sc-serif);
    font-style:italic;
    font-weight:500;
    font-size:15px;
    color:var(--sc-navy);
    margin:0 0 10px 0;
    letter-spacing:0;
  }
  .form-section .form-section-body { display:block; }
  /* P22: section_header() — PE Intelligence's serif-caps divider. */
  .section-header { margin:32px 0 16px; border-bottom:1px solid var(--sc-rule); padding-bottom:6px; display:flex; }
  .section-header.section-align-left   { justify-content:flex-start; }
  .section-header.section-align-center { justify-content:center; }
  .section-header.section-align-right  { justify-content:flex-end; }
  .section-header .section-header-label {
    font-family:var(--sc-serif);
    font-size:13px;
    font-weight:600;
    letter-spacing:0.18em;
    text-transform:uppercase;
    color:var(--sc-text-dim);
  }
  /* P36: diligence_phase_nav() — two-row tab strip. */
  .diligence-phase-nav { margin:14px 0 20px; }
  .diligence-phase-nav .phase-row { display:flex; gap:0; border-bottom:1px solid var(--sc-rule); }
  .diligence-phase-nav .phase-link { flex:1; text-align:center; padding:10px 12px; font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:var(--sc-text-dim); text-decoration:none; border-bottom:2px solid transparent; transition:color var(--motion-fast) var(--ease-standard); }
  .diligence-phase-nav .phase-link:hover { color:var(--sc-navy); }
  .diligence-phase-nav .phase-link.active { color:var(--sc-navy); border-bottom-color:var(--accent-2); }
  .diligence-phase-nav .child-row { display:flex; gap:24px; padding:10px 0 0; flex-wrap:wrap; }
  .diligence-phase-nav .child-link { font-family:var(--sc-sans); font-size:12px; color:var(--sc-text-dim); text-decoration:none; padding:4px 0; border-bottom:1px solid transparent; }
  .diligence-phase-nav .child-link:hover { color:var(--sc-navy); }
  .diligence-phase-nav .child-link.active { color:var(--sc-navy); border-bottom-color:var(--sc-navy); font-weight:600; }
  /* P24: subtle paper texture on parchment surfaces. The dot grid
     is a 40×40 inline SVG with two near-transparent dots, repeated
     across the body. Felt, not seen — if a partner notices it on
     first read it's too strong. Disable on dark surfaces (.on-navy
     containers handle their own backgrounds). */
  body, .cream-surface {
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'><circle cx='10' cy='10' r='0.7' fill='%23000' fill-opacity='0.025'/><circle cx='30' cy='30' r='0.7' fill='%23000' fill-opacity='0.025'/></svg>");
    background-repeat:repeat;
    background-size:40px 40px;
  }
  .ck-section-header { display:flex; align-items:flex-end; justify-content:space-between; gap:var(--sc-s-5); margin:var(--sc-s-8) 0 var(--sc-s-5); }
  .ck-section-code { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.1em; }

  /* Top bar */
  .ck-topbar { position:sticky; top:0; z-index:50; background:#fff; border-bottom:1px solid var(--sc-rule); }
  .ck-topbar-inner { display:flex; align-items:center; gap:var(--sc-s-6); padding:14px var(--sc-s-6); max-width:1440px; margin:0 auto; }
  .ck-wordmark { display:flex; align-items:center; gap:10px; font-family:var(--sc-serif); font-weight:500; font-size:19px; color:var(--sc-navy); letter-spacing:-0.005em; }
  .ck-wordmark-mark { width:28px; height:28px; border-radius:50%; background:var(--sc-navy); position:relative; }
  .ck-wordmark-mark::after { content:''; position:absolute; inset:6px; border:2px solid var(--sc-teal); border-right-color:transparent; border-bottom-color:transparent; border-radius:50%; transform:rotate(-45deg); }
  .ck-nav { display:flex; gap:var(--sc-s-6); margin-left:var(--sc-s-4); }
  .ck-nav a { font-family:var(--sc-sans); font-size:13px; font-weight:500; letter-spacing:0.04em; color:var(--sc-text-dim); padding:6px 0; border-bottom:2px solid transparent; }
  .ck-nav a:hover { color:var(--sc-navy); }
  .ck-nav a.active { color:var(--sc-navy); border-bottom-color:var(--sc-teal); }
  .ck-topbar-right { margin-left:auto; display:flex; align-items:center; gap:var(--sc-s-4); }
  .ck-search { border:1px solid var(--sc-rule); padding:6px 12px; font-size:13px; min-width:220px; border-radius:2px; background:var(--sc-bone); font-family:var(--sc-sans); }
  .ck-user-chip { width:32px; height:32px; border-radius:50%; background:var(--sc-navy); color:var(--sc-on-navy); display:flex; align-items:center; justify-content:center; font-family:var(--sc-sans); font-weight:600; font-size:12px; }
  .ck-breadcrumbs { display:flex; gap:8px; padding:10px var(--sc-s-6); max-width:1440px; margin:0 auto; font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.08em; text-transform:uppercase; }
  .ck-breadcrumbs a { color:var(--sc-text-dim); }
  .ck-breadcrumbs .sep { color:var(--sc-rule-2); }

  /* Command palette */
  .ck-palette { position:fixed; inset:0; background:rgba(6,22,38,0.4); display:flex; align-items:flex-start; justify-content:center; padding-top:12vh; z-index:100; }
  .ck-palette[hidden] { display:none; }
  .ck-palette-box { width:min(680px, 92vw); background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-3); border-radius:2px; }
  .ck-palette-input { width:100%; padding:16px 20px; font-family:var(--sc-serif); font-size:18px; border:0; border-bottom:1px solid var(--sc-rule); outline:none; }
  .ck-palette-input:focus-visible { box-shadow:0 2px 0 0 var(--accent-2); }
  /* P96: visible focus state for every other interactive element.
     Defaults to a 2px accent-2 outline with 2px offset so the
     ring sits clear of rounded corners. */
  :focus-visible { outline:2px solid var(--accent-2); outline-offset:2px; }
  .ck-palette-list { list-style:none; margin:0; padding:0; max-height:52vh; overflow:auto; }
  .ck-palette-list li { display:flex; justify-content:space-between; padding:10px 20px; font-size:13px; cursor:pointer; border-bottom:1px solid var(--sc-bone); }
  .ck-palette-list li:hover { background:var(--sc-bone); }
  .cp-route { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); }

  /* Main content frame */
  .ck-main { padding:var(--sc-s-7) var(--sc-s-6); max-width:1440px; margin:0 auto; }

  /* Print — for /memo/<id>, /ic-packet/<id> */
  /* P25: print stylesheet. Partners print IC memos, LP updates,
     bridge waterfalls. The default page layout is screen-shaped
     and would render the dark navy nav as a solid black banner on
     every page if not disabled. This block strips chrome, repeats
     table headers, paginates inside cards, and adds a stripe
     pattern to severity tones so a B&W printout still distinguishes
     RED from GREEN cells. */
  @page { size:Letter; margin:0.75in 0.5in; }
  @media print {
    .ck-topbar, .ck-breadcrumbs, .ck-palette,
    .preview-panel, .recent-runs,
    [data-preview="true"] { display:none !important; }
    body, body.cream-surface {
      background:#fff !important;
      background-image:none !important;
      color:#000 !important;
    }
    .ck-panel { box-shadow:none; break-inside:avoid; page-break-inside:avoid; }
    .ck-main { max-width:none; padding:0; }
    /* Repeat <thead> on every page break for long tables. */
    thead, .data-table thead { display:table-header-group; }
    tr, .data-table tr { break-inside:avoid; page-break-inside:avoid; }
    .data-table.sticky-header thead th { position:static; }
    .data-table.hover tbody tr:hover { background:transparent !important; }
    /* Color-only severity gets a pattern fallback so grayscale
       printouts still read GREEN vs RED. */
    .tone-positive { background:repeating-linear-gradient(45deg, transparent 0 4px, rgba(0,0,0,0.08) 4px 5px); }
    .tone-negative { background:repeating-linear-gradient(135deg, transparent 0 4px, rgba(0,0,0,0.18) 4px 5px); }
    .tone-warning  { background:repeating-linear-gradient(90deg, transparent 0 4px, rgba(0,0,0,0.12) 4px 5px); }
    /* Action buttons in print read as plain text — no fill. */
    .btn-primary, .btn-secondary, .btn-tertiary {
      background:transparent !important; color:#000 !important; border:0 !important;
    }
  }

  /* ── Legacy cad-* compat layer ──────────────────────────────────
     Existing page renderers reference Bloomberg-style .cad-* class
     names. Rather than migrate every page's class names (40+ pages,
     heavy churn), this compat block redefines the same names with
     editorial-palette values. Pages keep working; the visual flips
     with the CHARTIS_UI_V2 flag. */
  .cad-main { padding: var(--sc-s-7) var(--sc-s-6); max-width:1440px; margin:0 auto; }
  .cad-card {
    background: var(--sc-panel); border:1px solid var(--sc-rule);
    border-radius:2px; padding: var(--sc-s-5) var(--sc-s-6);
    margin-bottom: var(--sc-s-5); box-shadow: var(--sc-shadow-1);
  }
  .cad-card h1 { font-family: var(--sc-serif); font-weight:500; font-size:24px;
                 color: var(--sc-navy); margin-bottom: var(--sc-s-3); letter-spacing:-0.005em; }
  .cad-card h2 { font-family: var(--sc-serif); font-weight:500; font-size:18px;
                 color: var(--sc-navy); margin-bottom: var(--sc-s-3); letter-spacing:-0.005em; }
  .cad-card p  { font-size:13px; color: var(--sc-text); line-height:1.55; }
  .cad-h1 { font-family: var(--sc-serif); font-weight:500; font-size:28px;
            color: var(--sc-navy); letter-spacing:-0.01em; }

  .cad-text       { color: var(--sc-text); }
  .cad-text-dim   { color: var(--sc-text-dim); }
  .cad-text-muted { color: var(--sc-text-faint); }
  .cad-link       { color: var(--sc-teal-ink); text-decoration:none; }
  .cad-link:hover { color: var(--sc-navy); }
  .cad-mono       { font-family: var(--sc-mono); font-variant-numeric: tabular-nums; }
  .cad-accent     { color: var(--sc-teal-ink); }
  .cad-amber      { color: var(--sc-warning); }
  .cad-pos        { color: var(--sc-positive); }
  .cad-neg        { color: var(--sc-negative); }
  .cad-warn       { color: var(--sc-warning); }
  .cad-bg         { background: var(--sc-bg); }
  .cad-border     { border-color: var(--sc-rule); }
  .cad-border-lt  { border-color: var(--sc-rule-2); }

  /* P26 follow-up: legacy .cad-kpi/.cad-kpi-* rules removed.
     The kpi_strip primitive (.kpi-strip / .kpi-item / .kpi-label /
     .kpi-value / .kpi-sublabel) replaced every consumer; the dead
     selectors were shipping ~700 bytes of CSS on every page. */

  .cad-badge {
    display: inline-flex; align-items: center; padding: 2px 8px;
    font-family: var(--sc-sans); font-size: 10px; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase;
    border: 1px solid currentColor; border-radius: 2px;
  }
  .cad-badge-blue   { color: var(--sc-teal-ink); }
  .cad-badge-green  { color: var(--sc-positive); }
  .cad-badge-amber  { color: var(--sc-warning); }
  .cad-badge-red    { color: var(--sc-negative); }
  .cad-badge-muted  { color: var(--sc-text-faint); }
  .cad-section-code {
    font-family: var(--sc-mono); font-size: 10px;
    color: var(--sc-text-faint); letter-spacing: 0.14em;
  }

  .cad-btn {
    display: inline-block; padding: 6px 12px;
    font-family: var(--sc-sans); font-size: 12px; font-weight: 600;
    letter-spacing: 0.04em; color: var(--sc-navy);
    background: var(--sc-bone); border: 1px solid var(--sc-rule);
    border-radius: 2px; text-decoration: none; cursor: pointer;
  }
  .cad-btn:hover { background: var(--sc-rule); }
  .cad-btn-primary {
    color: var(--sc-on-navy); background: var(--sc-navy);
    border-color: var(--sc-navy);
  }
  .cad-btn-primary:hover { background: var(--sc-navy-2); color: var(--sc-on-navy); }

  .cad-table {
    width: 100%; border-collapse: collapse; font-size: 13px;
    margin-top: var(--sc-s-3);
  }
  .cad-table thead th {
    background: var(--sc-bone); color: var(--sc-text-dim);
    font-family: var(--sc-sans); font-weight: 600; font-size: 11px;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 8px 12px; text-align: left;
    border-bottom: 1px solid var(--sc-rule);
  }
  .cad-table tbody td { padding: 8px 12px; border-bottom: 1px solid var(--sc-rule); }
  .cad-table .num { font-family: var(--sc-mono); font-variant-numeric: tabular-nums;
                    text-align: right; }

  .cad-input, .cad-field {
    padding: 8px 12px; border: 1px solid var(--sc-rule);
    font-family: var(--sc-sans); font-size: 13px;
    background: var(--sc-panel); color: var(--sc-text);
    border-radius: 2px; width: 100%;
  }
  .cad-input:focus, .cad-field:focus {
    outline: none; border-color: var(--sc-teal); box-shadow: 0 0 0 2px rgba(47, 179, 173, 0.15);
  }

  .cad-status-item { display: flex; gap: 6px; font-size: 11px; font-family: var(--sc-mono); }
  .cad-status-key  { color: var(--sc-text-faint); text-transform: uppercase; letter-spacing: 0.1em; }
  .cad-status-val  { color: var(--sc-text); font-weight: 600; }
  .cad-deal-ident  { font-family: var(--sc-mono); font-size: 11px; color: var(--sc-text-dim); letter-spacing: 0.08em; }
  .cad-ticker-id   { font-family: var(--sc-mono); font-size: 10px; letter-spacing: 0.14em; color: var(--sc-text-faint); }

  /* Generic .mn wrapper used by ck_fmt_num / ck_fmt_pct */
  .mn { font-family: var(--sc-mono); font-variant-numeric: tabular-nums; }
  .mn.pos, .ck-kpi-value.tone-pos { color: var(--sc-positive); }
  .mn.neg, .ck-kpi-value.tone-neg { color: var(--sc-negative); }
  .mn.warn, .ck-kpi-value.tone-warn { color: var(--sc-warning); }
  .faint, .ck-kpi-value.tone-faint { color: var(--sc-text-faint); }
</style>
"""

_COLUMN_PICKER_JS = """
<script>
/* P50: column picker on data_table[data-table-id]. Per-table, per-
   user column visibility persists in localStorage keyed by
   (pathname, table_id). Restore on page load; save on toggle. */
(function(){
  if (!window.localStorage) return;
  function keyFor(table) {
    var id = table.getAttribute('data-table-id');
    if (!id) return null;
    return 'colVisibility:' + window.location.pathname + ':' + id;
  }
  function applyState(table, hidden) {
    table.querySelectorAll('th[data-col-key], td[data-col-key]')
      .forEach(function(c){
        var k = c.getAttribute('data-col-key');
        if (hidden.indexOf(k) >= 0) c.classList.add('col-hidden');
        else c.classList.remove('col-hidden');
      });
    // Sync the picker checkboxes to match.
    var wrap = table.closest('.data-table-wrap');
    if (!wrap) return;
    wrap.querySelectorAll('.column-picker-toggle').forEach(function(box){
      box.checked = hidden.indexOf(box.getAttribute('data-col-key')) < 0;
    });
  }
  function restore(table) {
    try {
      var raw = window.localStorage.getItem(keyFor(table));
      if (!raw) return;
      applyState(table, JSON.parse(raw));
    } catch (e) {}
  }
  function bindPicker(wrap, table) {
    wrap.addEventListener('change', function(e){
      if (!e.target.classList.contains('column-picker-toggle')) return;
      var hidden = [];
      wrap.querySelectorAll('.column-picker-toggle').forEach(function(b){
        if (!b.checked) hidden.push(b.getAttribute('data-col-key'));
      });
      applyState(table, hidden);
      try {
        window.localStorage.setItem(keyFor(table), JSON.stringify(hidden));
      } catch (e) {}
    });
  }
  document.addEventListener('DOMContentLoaded', function(){
    var tables = document.querySelectorAll(
      'table.data-table[data-table-id]'
    );
    Array.prototype.forEach.call(tables, function(table){
      var wrap = table.closest('.data-table-wrap');
      if (!wrap) return;
      restore(table);
      bindPicker(wrap, table);
    });
  });
})();
</script>
"""

_KEYBOARD_NAV_JS = """
<script>
/* P89: vim-style keyboard navigation. ``g`` arms a 1.5-second
   prefix; the next key picks a destination (d=Diligence,
   p=Pipeline, l=Library, r=Research, h=Home, f=Portfolio).
   ``[``/``]`` step the secondary-nav child tabs. ``?`` opens a
   shortcut help overlay. ``/`` focuses the page's first
   ``input[type=search]`` if any. ``Escape`` dismisses any open
   modal (palette, tour, help). */
(function(){
  var GO_TARGETS = {
    d: '/diligence', p: '/pipeline', l: '/library',
    r: '/research', h: '/home', f: '/portfolio',
  };
  var prefixUntil = 0;

  function isFormFocused() {
    var el = document.activeElement;
    if (!el) return false;
    var tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select'
      || el.isContentEditable;
  }

  function stepSecondaryTab(dir) {
    var active = document.querySelector('.child-link.active');
    if (!active) return;
    var siblings = Array.prototype.slice.call(
      active.parentNode.querySelectorAll('.child-link')
    );
    var idx = siblings.indexOf(active);
    if (idx < 0) return;
    var nxt = siblings[idx + dir];
    if (nxt && nxt.href) window.location.href = nxt.href;
  }

  function showHelp() {
    var help = document.getElementById('kbd-help');
    if (!help) return;
    help.removeAttribute('hidden');
  }

  document.addEventListener('keydown', function(e){
    if (isFormFocused()) return;
    var now = Date.now();
    if (e.key === 'g') {
      prefixUntil = now + 1500;
      e.preventDefault();
      return;
    }
    if (now < prefixUntil) {
      prefixUntil = 0;
      var target = GO_TARGETS[e.key];
      if (target) {
        e.preventDefault();
        window.location.href = target;
      }
      return;
    }
    if (e.key === '[') { e.preventDefault(); stepSecondaryTab(-1); return; }
    if (e.key === ']') { e.preventDefault(); stepSecondaryTab(1);  return; }
    if (e.key === '?') { e.preventDefault(); showHelp(); return; }
    if (e.key === '/') {
      var search = document.querySelector('input[type=search]');
      if (search) { e.preventDefault(); search.focus(); }
      return;
    }
    if (e.key === 'Escape') {
      var palette = document.getElementById('ck-palette');
      if (palette && !palette.hidden) palette.hidden = true;
      var tour = document.getElementById('tour-overlay');
      if (tour && !tour.hidden) tour.setAttribute('hidden', '');
      var help = document.getElementById('kbd-help');
      if (help && !help.hidden) help.setAttribute('hidden', '');
    }
  });
})();
</script>
<div class="kbd-help" id="kbd-help" hidden>
  <div class="kbd-help-card">
    <h4>Keyboard shortcuts</h4>
    <dl>
      <dt>g d / g p / g l / g r / g h / g f</dt>
      <dd>Diligence · Pipeline · Library · Research · Home · Portfolio</dd>
      <dt>[ / ]</dt><dd>Previous · next secondary-nav tab</dd>
      <dt>⌘K · /</dt><dd>Open palette · focus search</dd>
      <dt>?</dt><dd>This help · Escape dismisses any modal</dd>
    </dl>
  </div>
</div>
"""

_TOUR_JS = """
<script>
/* P77: tour overlay. Activates when <body data-tour="active"> is
   set (typically server-side when ?tour=1 is in the URL). Cycles
   through .tour-step elements; current step un-hides; prev/next
   buttons step; skip button dismisses. */
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    var overlay = document.getElementById('tour-overlay');
    if (!overlay) return;
    if (document.body.getAttribute('data-tour') !== 'active') return;
    overlay.removeAttribute('hidden');
    var steps = Array.prototype.slice.call(
      overlay.querySelectorAll('.tour-step')
    );
    if (steps.length === 0) return;
    var idx = 0;
    var prev = overlay.querySelector('.tour-prev');
    var next = overlay.querySelector('.tour-next');
    var skip = overlay.querySelector('.tour-skip');
    var progress = overlay.querySelector('.tour-progress');
    function show() {
      steps.forEach(function(s, i){
        if (i === idx) s.removeAttribute('hidden');
        else s.setAttribute('hidden', '');
      });
      prev.disabled = (idx === 0);
      next.textContent = (idx === steps.length - 1) ? 'Done' : 'Next';
      if (progress) {
        progress.textContent = (idx + 1) + ' / ' + steps.length;
      }
    }
    next.addEventListener('click', function(){
      if (idx === steps.length - 1) {
        overlay.setAttribute('hidden', '');
        return;
      }
      idx += 1;
      show();
    });
    prev.addEventListener('click', function(){
      if (idx > 0) idx -= 1;
      show();
    });
    skip.addEventListener('click', function(){
      overlay.setAttribute('hidden', '');
    });
    show();
  });
})();
</script>
"""

_SHARE_BUTTON_JS = """
<script>
/* P59: Share button. Click → copy URL to clipboard, dispatch a
   custom 'share' event the page can hook to surface a richer
   modal. Falls back to a plain confirm() prompt if the Clipboard
   API is unavailable (older browsers). */
(function(){
  document.addEventListener('click', function(e){
    var btn = e.target.closest('.share-button');
    if (!btn) return;
    e.preventDefault();
    var url = btn.getAttribute('data-share-url') || window.location.href;
    var doneCopy = function(){
      btn.textContent = '✓ Copied';
      setTimeout(function(){ btn.textContent = '↗ Share'; }, 2200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(doneCopy, function(){
        window.prompt('Copy this URL:', url);
      });
    } else {
      window.prompt('Copy this URL:', url);
    }
    document.dispatchEvent(new CustomEvent('share-button-click', {
      detail: {
        entityType: btn.getAttribute('data-share-entity-type'),
        entityId:   btn.getAttribute('data-share-entity-id'),
        url:        url,
      },
    }));
  });
})();
</script>
"""

_BULK_ACTIONS_JS = """
<script>
/* P49: bulk-actions sticky bar. Listens to .bulk-select checkbox
   changes anywhere on the page, updates the count, shows/hides the
   bar. On action-button click, gathers data-bulk-id values from
   checked rows and either:
     - if data-bulk-href-template contains "{ids}", expands and
       window.location.href = result.
     - otherwise prepends ?ids=<csv> to the template. */
(function(){
  function selectedIds() {
    var boxes = document.querySelectorAll('.bulk-select:checked');
    return Array.prototype.map.call(boxes, function(b){
      return b.getAttribute('data-bulk-id');
    });
  }
  function refresh() {
    var bar = document.getElementById('bulk-actions-bar');
    if (!bar) return;
    var ids = selectedIds();
    var n = ids.length;
    var nEl = bar.querySelector('.bulk-count-n');
    if (nEl) nEl.textContent = String(n);
    if (n > 0) bar.removeAttribute('hidden');
    else bar.setAttribute('hidden', '');
  }
  function clearAll() {
    var boxes = document.querySelectorAll('.bulk-select:checked');
    Array.prototype.forEach.call(boxes, function(b){ b.checked = false; });
    refresh();
  }
  document.addEventListener('change', function(e){
    if (e.target && e.target.classList &&
        e.target.classList.contains('bulk-select')) {
      refresh();
    }
  });
  document.addEventListener('click', function(e){
    var t = e.target;
    if (!t || !t.classList) return;
    if (t.classList.contains('bulk-clear')) {
      e.preventDefault(); clearAll(); return;
    }
    if (t.classList.contains('bulk-action-btn')) {
      var tpl = t.getAttribute('data-bulk-href-template') || '#';
      var ids = selectedIds();
      if (ids.length === 0) { e.preventDefault(); return; }
      var url;
      if (tpl.indexOf('{ids}') >= 0) {
        url = tpl.replace('{ids}', encodeURIComponent(ids.join(',')));
      } else if (tpl === '#') {
        e.preventDefault();
        // Surface ids on the document for handler hooks; do NOT
        // navigate when the template was the no-op anchor.
        document.dispatchEvent(new CustomEvent('bulk-action', {
          detail: { ids: ids, source: t },
        }));
        return;
      } else {
        var sep = tpl.indexOf('?') >= 0 ? '&' : '?';
        url = tpl + sep + 'ids=' + encodeURIComponent(ids.join(','));
      }
      window.location.href = url;
    }
  });
  document.addEventListener('DOMContentLoaded', refresh);
})();
</script>
"""

_ACTION_BUTTON_JS = """
<script>
/* P20: when a button declares an expected-seconds duration, swap
   its label to "Running…" and disable it on form submit so the
   partner doesn't double-click during the wait. The original label
   is captured in data-original-label and restored on pageshow
   (browser back-forward cache). */
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    var btns = document.querySelectorAll('button[data-expected-seconds]');
    Array.prototype.forEach.call(btns, function(btn){
      var form = btn.closest('form');
      if (!form) return;
      form.addEventListener('submit', function(){
        btn.setAttribute('data-busy', 'true');
        if (!btn.getAttribute('data-original-label')) {
          btn.setAttribute('data-original-label', btn.innerHTML);
        }
        btn.innerHTML = 'Running…';
      });
    });
    window.addEventListener('pageshow', function(){
      var busy = document.querySelectorAll('button[data-busy="true"]');
      Array.prototype.forEach.call(busy, function(btn){
        var orig = btn.getAttribute('data-original-label');
        if (orig) btn.innerHTML = orig;
        btn.removeAttribute('data-busy');
      });
    });
  });
})();
</script>
"""

_DATA_TABLE_JS = """
<script>
/* P15: data_table() client-side sort. Vanilla JS, no library.
   Bound on every table.data-table[data-sortable="true"]. Numeric
   columns (kind in money/percent/count/multiple) sort by parseFloat
   after stripping non-numeric chars; text columns sort by
   localeCompare. Clicking a header cycles asc → desc → asc. */
(function(){
  function sortBy(table, header) {
    var idx = Array.prototype.indexOf.call(header.parentNode.children, header);
    var kind = header.getAttribute('data-kind') || 'text';
    var numeric = (kind === 'money' || kind === 'percent' ||
                   kind === 'count' || kind === 'multiple');
    var asc = !header.classList.contains('sort-asc');
    // Clear all header sort states.
    Array.prototype.forEach.call(
      header.parentNode.querySelectorAll('th'),
      function(th){ th.classList.remove('sort-asc','sort-desc'); }
    );
    header.classList.add(asc ? 'sort-asc' : 'sort-desc');
    var tbody = table.querySelector('tbody');
    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
    rows.sort(function(a, b){
      var av = (a.children[idx].textContent || '').trim();
      var bv = (b.children[idx].textContent || '').trim();
      if (numeric) {
        var an = parseFloat(av.replace(/[^0-9eE+\\-.]/g, ''));
        var bn = parseFloat(bv.replace(/[^0-9eE+\\-.]/g, ''));
        if (isNaN(an)) an = asc ? Infinity : -Infinity;
        if (isNaN(bn)) bn = asc ? Infinity : -Infinity;
        return asc ? an - bn : bn - an;
      }
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    rows.forEach(function(r){ tbody.appendChild(r); });
  }
  document.addEventListener('DOMContentLoaded', function(){
    var tables = document.querySelectorAll(
      'table.data-table[data-sortable="true"]'
    );
    Array.prototype.forEach.call(tables, function(table){
      var headers = table.querySelectorAll('thead th.sortable');
      Array.prototype.forEach.call(headers, function(th){
        th.addEventListener('click', function(){ sortBy(table, th); });
      });
    });
  });
})();
</script>
"""

_FORM_PERSIST_JS = """
<script>
/* P10: long-form input persistence across page reloads + session
   expiry. Bridge Audit, Thesis Pipeline, Deal Monte Carlo etc. take
   12-18 inputs to fill out. If the partner's session dies mid-form
   (sessions invalidate on server restart per CLAUDE.md), the POST
   bounces to /login?next=<path> — and if they re-land on the form
   we want their values back. localStorage survives navigations and
   is keyed off pathname + form action + field name so two pages
   don't collide.

   Skipped: passwords, CSRF tokens, hidden fields, file uploads. */
(function(){
  if (!window.localStorage) return;
  var prefix = 'formPersist:' + window.location.pathname + ':';
  function shouldPersist(el) {
    if (!el.name) return false;
    var t = (el.type || '').toLowerCase();
    if (t === 'password' || t === 'hidden' || t === 'file' || t === 'submit') return false;
    if (el.name === 'csrf_token' || el.name === '_csrf') return false;
    return true;
  }
  function keyFor(form, el) {
    var formKey = form.getAttribute('id') || form.getAttribute('action') || 'form';
    return prefix + formKey + ':' + el.name;
  }
  function restore(form) {
    var fields = form.querySelectorAll('input,textarea,select');
    Array.prototype.forEach.call(fields, function(el){
      if (!shouldPersist(el)) return;
      try {
        var v = window.localStorage.getItem(keyFor(form, el));
        if (v === null) return;
        if (el.type === 'checkbox' || el.type === 'radio') {
          el.checked = (v === 'true');
        } else {
          el.value = v;
        }
      } catch (e) { /* ignore quota / parse errors */ }
    });
  }
  function bind(form) {
    var fields = form.querySelectorAll('input,textarea,select');
    Array.prototype.forEach.call(fields, function(el){
      if (!shouldPersist(el)) return;
      var save = function(){
        try {
          var v = (el.type === 'checkbox' || el.type === 'radio')
            ? String(!!el.checked) : el.value;
          window.localStorage.setItem(keyFor(form, el), v);
        } catch (e) { /* ignore */ }
      };
      el.addEventListener('input', save);
      el.addEventListener('change', save);
    });
  }
  document.addEventListener('DOMContentLoaded', function(){
    var forms = document.querySelectorAll('form');
    Array.prototype.forEach.call(forms, function(form){
      restore(form);
      bind(form);
    });
  });
})();
</script>
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
    links = "".join(
        f'<a href="{_esc(item["href"])}" class="{"active" if item["key"] == active_nav else ""}">{_esc(item["label"])}</a>'
        for item in _CORPUS_NAV
    )
    return (
        '<header class="ck-topbar">'
        '<div class="ck-topbar-inner">'
        '<a href="/" class="ck-wordmark"><span class="ck-wordmark-mark"></span>SeekingChartis</a>'
        f'<nav class="ck-nav">{links}</nav>'
        '<div class="ck-topbar-right">'
        '<input class="ck-search" type="search" placeholder="Search deals, hospitals, routes… (⌘K)" />'
        f'<span class="ck-user-chip">{_esc(user_initials)}</span>'
        "</div>"
        "</div>"
        "</header>"
    )


def _breadcrumbs(crumbs: Optional[Sequence[Mapping[str, str]]]) -> str:
    if not crumbs:
        return ""
    parts = []
    for i, c in enumerate(crumbs):
        if i:
            parts.append('<span class="sep">/</span>')
        if c.get("href"):
            parts.append(f'<a href="{_esc(c["href"])}">{_esc(c["label"])}</a>')
        else:
            parts.append(_esc(c["label"]))
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
    subtitle: Optional[str] = None,
) -> str:
    """Render a full page. Drop-in replacement for the legacy dark shell.

    All kwargs are optional and match or extend the previous signature.
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
    if include_palette:
        # P46: every shelled page gets cmd-K out of the box. Caller
        # can pass a richer ``palette_modules`` (e.g. with deal names
        # appended) — otherwise we fall back to the default route
        # catalog so the keyboard shortcut is never a dead key.
        palette_html = ck_command_palette(
            palette_modules if palette_modules else _DEFAULT_PALETTE_ROUTES,
        )
    debug_tag = f'<div class="ck-debug-code">[{_esc(code)}]</div>' if code else ""
    # P41: subtitle slot. When the page passes a subtitle the shell
    # renders it inside the main column at 0.7x the page-title size
    # so the subtitle stops competing with the H1 for visual weight
    # (Risk Workbench, Provider Economics, Management Scorecard
    # all suffered from same-weight title + subtitle competition).
    subtitle_html = (
        f'<div class="page-subtitle">{_esc(subtitle)}</div>'
        if subtitle else ""
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
        "</head><body>"
        f"{_topbar(active_nav, user_initials)}"
        f"{_breadcrumbs(breadcrumbs)}"
        f'<main class="ck-main">{debug_tag}{subtitle_html}{body_html}</main>'
        f"{palette_html}"
        f"{_FORM_PERSIST_JS}"
        f"{_DATA_TABLE_JS}"
        f"{_ACTION_BUTTON_JS}"
        f"{_BULK_ACTIONS_JS}"
        f"{_COLUMN_PICKER_JS}"
        f"{_SHARE_BUTTON_JS}"
        f"{_TOUR_JS}"
        f"{_KEYBOARD_NAV_JS}"
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
    "ck_sanitize_value",
]
