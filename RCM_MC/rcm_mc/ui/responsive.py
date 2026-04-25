"""Responsive layout utilities — large monitors → tablets.

Recent UI surfaces use inline styles with sensible flex defaults
(``flex-wrap: wrap`` on KPI strips, ``max-width: 1100px``
containers). They mostly work on a 27" monitor and a 13" laptop.
Tablets and narrow laptop windows expose four recurring failures:

  • **Tables overflow horizontally** — power_table's many columns
    push past the viewport. Need explicit ``overflow-x:auto`` on
    the wrapper.
  • **Toolbars wrap awkwardly** — search input + export button
    + columns toggle stack vertically on narrow widths instead
    of cleanly wrapping.
  • **Charts don't shrink** — power_chart's SVG uses a fixed
    viewBox; the ``width="100%"`` attribute helps but the
    ``height`` stays absolute.
  • **Touch targets are too small** — 11px buttons fine on
    desktop, hard to tap on a tablet.

This module ships:

  • A **responsive viewport** ``<meta>`` tag (every page should
    have it; some recent ones don't).
  • A **responsive stylesheet** with the breakpoints + utilities
    we use most: ``.rs-container`` (max-width 1100px, scaling
    horizontal padding), ``.rs-grid`` (auto-fit columns down to
    a min width), ``.rs-table-wrap`` (horizontal scroll wrapper),
    ``.rs-touch-target`` (raises hit area on small screens).
  • Helpers ``responsive_container``, ``responsive_grid``,
    ``responsive_table_wrap`` that emit the right wrapper HTML.

Public API::

    from rcm_mc.ui.responsive import (
        viewport_meta,
        responsive_stylesheet,
        responsive_container,
        responsive_grid,
        responsive_table_wrap,
        BREAKPOINTS,
    )
"""
from __future__ import annotations

import html as _html
from typing import Any, Optional


# Standard breakpoints. Mirror the Tailwind defaults so any
# future migration stays compatible. Tablet is the partner-
# relevant lower bound — we don't need to support phone.
BREAKPOINTS = {
    "tablet_min": "640px",
    "laptop_min": "1024px",
    "desktop_min": "1280px",
    "large_min": "1536px",
}


# ── Viewport meta ────────────────────────────────────────────

def viewport_meta() -> str:
    """The standard responsive viewport meta tag.

    Drop into <head>. Without this, mobile browsers render at
    a virtual 980px width and the page looks tiny.
    """
    return (
        '<meta name="viewport" '
        'content="width=device-width, '
        'initial-scale=1, viewport-fit=cover">')


# ── Stylesheet ──────────────────────────────────────────────

# Single stylesheet covering all responsive utilities. Embedded
# once per page (idempotent because it uses class selectors).
_RESPONSIVE_CSS = """
<style>
/* Base container with scaling padding */
.rs-container{max-width:1280px;margin:0 auto;
  padding:24px;}
@media (max-width: 1024px){
  .rs-container{padding:20px 18px;}
}
@media (max-width: 640px){
  .rs-container{padding:16px 12px;}
}

/* Auto-fit grid — pass --rs-min via inline style */
.rs-grid{display:grid;
  grid-template-columns:
    repeat(auto-fit, minmax(var(--rs-min, 220px), 1fr));
  gap:14px;}

/* Horizontal-scroll wrapper for wide tables */
.rs-table-wrap{overflow-x:auto;
  -webkit-overflow-scrolling:touch;
  background:#1f2937;border:1px solid #374151;
  border-radius:8px;}
.rs-table-wrap > table{min-width:max-content;}

/* Raise touch-target hit area on small screens */
@media (max-width: 1024px){
  .rs-touch-target{min-height:36px;min-width:36px;
    padding:8px 14px;}
}

/* Toolbar that wraps neatly */
.rs-toolbar{display:flex;flex-wrap:wrap;gap:10px;
  align-items:center;}
.rs-toolbar > .rs-toolbar-spacer{flex:1;
  min-width:0;}

/* KPI strip that stacks below tablet */
.rs-kpi-strip{display:flex;flex-wrap:wrap;}
.rs-kpi-strip > *{flex:1 1 200px;
  min-width:0;}

/* Hide-on-small / show-on-small utilities */
@media (max-width: 640px){
  .rs-hide-mobile{display:none !important;}
}
@media (min-width: 641px){
  .rs-show-mobile{display:none !important;}
}

/* Two-column → single column below laptop */
.rs-split-2{display:grid;
  grid-template-columns:repeat(2, 1fr);gap:18px;}
@media (max-width: 1024px){
  .rs-split-2{grid-template-columns:1fr;}
}

/* Body resets to ensure no horizontal overflow */
html, body{max-width:100%;overflow-x:hidden;}
</style>"""


def responsive_stylesheet() -> str:
    """Return the responsive utility stylesheet.

    Drop into <head> (or top of <body>). Idempotent — duplicate
    inclusions are harmless because all selectors are class-based.
    """
    return _RESPONSIVE_CSS


# ── Helpers ──────────────────────────────────────────────────

def responsive_container(
    inner_html: str,
    *,
    max_width: str = "1280px",
) -> str:
    """Wrap content in a responsive container with scaling
    padding.

    Use as the outermost wrapper for page bodies. Replaces the
    inline ``max-width:1100px;margin:0 auto;padding:32px 24px;``
    pattern with a class that adapts padding to viewport width:
    24px on desktop, 18px on laptop, 12px on tablet.
    """
    style = (f' style="max-width:{max_width};"'
             if max_width != "1280px" else "")
    return (
        f'<div class="rs-container"{style}>'
        f'{inner_html}</div>')


def responsive_grid(
    inner_html: str,
    *,
    min_column_width: str = "220px",
) -> str:
    """Auto-fit grid that drops columns below the min width.

    On a 27" monitor it might show 4 columns; on a 13" laptop
    3; on a tablet 2 or 1. No JS, no manual breakpoint math —
    CSS Grid's ``auto-fit minmax`` does the work.
    """
    return (
        f'<div class="rs-grid" '
        f'style="--rs-min:{min_column_width};">'
        f'{inner_html}</div>')


def responsive_table_wrap(table_html: str) -> str:
    """Wrap a wide table in a horizontal-scroll container.

    Use around any table with ≥6 columns or a known wide column
    (e.g. long deal names). The wrapper is identical-looking on
    desktop (table fits, no scroll) but allows touch-scroll on
    tablet without breaking the layout.
    """
    return (
        f'<div class="rs-table-wrap">{table_html}</div>')
