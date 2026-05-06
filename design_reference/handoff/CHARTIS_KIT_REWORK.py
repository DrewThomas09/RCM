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
from typing import Iterable, Mapping, Optional, Sequence

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
    if include_palette and palette_modules:
        palette_html = ck_command_palette(palette_modules)
    debug_tag = f'<div class="ck-debug-code">[{_esc(code)}]</div>' if code else ""
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
        f'<main class="ck-main">{debug_tag}{body_html}</main>'
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
