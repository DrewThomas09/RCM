"""Reusable, local, interactive US state map for PEdesk.

Phase 1: a **state tile-grid cartogram** — every state + DC is a labeled
cell placed in its approximate geographic position, shaded by a per-state
metric, with hover tooltips, click selection, a legend, and an honest
empty state. 100% local: inline SVG, no external map tiles, no GeoJSON
asset, no CDN, no runtime network.

Why a tile grid (not boundary outlines): it is fully local and tiny,
needs no geometry asset, is equal-area (big states don't dominate a
metric read), and never fabricates coastlines. Real boundary geometry is
a documented future upgrade (see docs/PEDESK_INTERACTIVE_MAPS.md) that
requires vendoring a simplified us-states GeoJSON/TopoJSON asset.

Public API:
    render_us_state_map(state_values=None, *, metric_label=..., ...)
"""
from __future__ import annotations

import html as _html
import itertools
from typing import Callable, Dict, Iterable, Optional

# Standard US state tile-grid positions (row, col) — north→south = low→high
# row, west→east = low→high col. Approximate geographic arrangement (tile
# grids are inherently stylized); all 50 states + DC, each a unique cell.
_TILE: Dict[str, tuple] = {
    "ME": (0, 10),
    "VT": (1, 9), "NH": (1, 10),
    "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4),
    "IL": (2, 5), "WI": (2, 6), "MI": (2, 7), "NY": (2, 8), "RI": (2, 9),
    "MA": (2, 10),
    "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4),
    "IN": (3, 5), "OH": (3, 6), "PA": (3, 7), "NJ": (3, 8), "CT": (3, 9),
    "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4),
    "KY": (4, 5), "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9),
    "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5),
    "NC": (5, 6), "SC": (5, 7), "DC": (5, 8),
    "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6), "GA": (6, 7),
    "HI": (7, 0), "TX": (7, 3), "FL": (7, 8),
    "AK": (8, 0),
}

STATE_NAMES: Dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

_CELL = 46          # cell size (px)
_PAD = 6            # gap between cells
_STEP = _CELL + _PAD
_MAX_ROW = max(r for r, _ in _TILE.values())
_MAX_COL = max(c for _, c in _TILE.values())
_NO_DATA_FILL = "var(--sc-parchment-2,#efe9dd)"
_ACCENT = "var(--sc-warning,#b8732a)"
_uid = itertools.count(1)


def _default_format(v: float) -> str:
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.1f}"


def _shade(value: Optional[float], lo: float, hi: float) -> str:
    """Quiet teal sequential shade. No data -> neutral parchment."""
    if value is None:
        return _NO_DATA_FILL
    if hi <= lo:
        frac = 1.0
    else:
        frac = (value - lo) / (hi - lo)
    frac = max(0.0, min(1.0, frac))
    opacity = 0.16 + frac * 0.78
    return f"rgba(21,87,82,{opacity:.3f})"  # --sc-teal base


def _map_css(cid: str) -> str:
    return (
        "<style>"
        f"#{cid}{{font-family:var(--sc-sans,sans-serif);}}"
        f"#{cid} .usm-cell{{cursor:default;transition:filter .12s;}}"
        f"#{cid} .usm-cell[data-clickable='1']{{cursor:pointer;}}"
        f"#{cid} .usm-cell[data-clickable='1']:hover .usm-rect{{filter:brightness(1.08);}}"
        f"#{cid} .usm-rect{{stroke:var(--sc-rule,#d6cfc0);stroke-width:1;rx:3;}}"
        f"#{cid} .usm-cell.usm-accent .usm-rect{{stroke:{_ACCENT};stroke-width:2;}}"
        f"#{cid} .usm-cell.usm-selected .usm-rect{{stroke:var(--sc-navy,#0b2341);stroke-width:3;}}"
        f"#{cid} .usm-abbr{{font-family:var(--sc-mono,monospace);font-size:13px;"
        "font-weight:700;fill:var(--sc-navy,#0b2341);pointer-events:none;}}"
        f"#{cid} .usm-tip{{position:absolute;z-index:30;pointer-events:none;"
        "background:var(--sc-navy,#0b2341);color:#fff;font-size:12px;line-height:1.4;"
        "padding:6px 9px;border-radius:3px;max-width:240px;display:none;"
        "box-shadow:0 2px 10px rgba(11,35,65,.25);}}"
        f"#{cid} .usm-legend{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;"
        "font-size:11px;color:var(--sc-text-dim,#465366);margin-top:10px;}}"
        f"#{cid} .usm-legend-bar{{width:120px;height:10px;border-radius:2px;"
        "background:linear-gradient(to right,rgba(21,87,82,.16),rgba(21,87,82,.94));}}"
        f"#{cid} .usm-legend-swatch{{display:inline-block;width:10px;height:10px;"
        "border-radius:2px;vertical-align:middle;margin-right:4px;}}"
        f"#{cid} .usm-empty{{font-style:italic;color:var(--sc-text-dim,#465366);"
        "margin:8px 0 0;font-size:13px;}}"
        "</style>"
    )


def _map_js(cid: str) -> str:
    # Hover tooltip + click selection. Vanilla, scoped to this container.
    return (
        "<script>(function(){"
        f"var root=document.getElementById('{cid}');if(!root)return;"
        "var tip=root.querySelector('.usm-tip');"
        "var sel=document.querySelector('[data-us-map-selected]');"
        "root.querySelectorAll('.usm-cell').forEach(function(c){"
        "c.addEventListener('mousemove',function(e){"
        "if(!tip)return;tip.textContent=c.getAttribute('data-tip')||'';"
        "tip.style.display='block';var r=root.getBoundingClientRect();"
        "tip.style.left=(e.clientX-r.left+12)+'px';tip.style.top=(e.clientY-r.top+12)+'px';});"
        "c.addEventListener('mouseleave',function(){if(tip)tip.style.display='none';});"
        "if(c.getAttribute('data-clickable')==='1'){"
        "c.addEventListener('click',function(){"
        "root.querySelectorAll('.usm-cell.usm-selected').forEach(function(o){o.classList.remove('usm-selected');});"
        "c.classList.add('usm-selected');"
        "var ab=c.getAttribute('data-state');"
        "if(sel)sel.textContent=c.getAttribute('data-tip')||ab;"
        "root.dispatchEvent(new CustomEvent('us-map-select',{detail:{state:ab},bubbles:true}));"
        "});}"
        "});})();</script>"
    )


def render_us_state_map(
    state_values: Optional[Dict[str, float]] = None,
    *,
    metric_label: str = "value",
    value_format: Optional[Callable[[float], str]] = None,
    state_notes: Optional[Dict[str, str]] = None,
    accent_states: Optional[Iterable[str]] = None,
    accent_label: Optional[str] = None,
    selected_state: Optional[str] = None,
    clickable: bool = True,
    empty_message: Optional[str] = None,
) -> str:
    """Render the state tile-grid cartogram as a self-contained HTML block.

    ``state_values`` maps UPPER-CASE postal abbreviation -> metric value.
    States absent from it render as "no data" (neutral), never invented.
    """
    values = {
        str(k).upper(): float(v)
        for k, v in (state_values or {}).items()
        if k and v is not None and str(k).upper() in _TILE
    }
    fmt = value_format or _default_format
    notes = {str(k).upper(): v for k, v in (state_notes or {}).items()}
    accents = {str(s).upper() for s in (accent_states or [])}
    selected = (selected_state or "").upper() or None
    has_data = bool(values)
    lo = min(values.values()) if values else 0.0
    hi = max(values.values()) if values else 0.0

    cid = f"usm-{next(_uid)}"
    width = (_MAX_COL + 1) * _STEP
    height = (_MAX_ROW + 1) * _STEP

    cells = []
    for abbr, (row, col) in _TILE.items():
        x = col * _STEP
        y = row * _STEP
        val = values.get(abbr)
        name = STATE_NAMES.get(abbr, abbr)
        # Tooltip text (also the accessible label) — never color-only.
        tip = f"{name}: {fmt(val)} {metric_label}" if val is not None \
            else f"{name}: no data"
        if abbr in notes:
            tip += f" · {notes[abbr]}"
        classes = "usm-cell"
        if abbr in accents:
            classes += " usm-accent"
        if abbr == selected:
            classes += " usm-selected"
        clickable_attr = "1" if (clickable and val is not None) else "0"
        tip_esc = _html.escape(tip, quote=True)
        cells.append(
            f'<g class="{classes}" data-state="{abbr}" '
            f'data-clickable="{clickable_attr}" '
            f'data-tip="{tip_esc}" role="img" aria-label="{tip_esc}">'
            f'<rect class="usm-rect" x="{x}" y="{y}" '
            f'width="{_CELL}" height="{_CELL}" fill="{_shade(val, lo, hi)}"/>'
            f'<title>{tip_esc}</title>'
            f'<text class="usm-abbr" x="{x + _CELL/2:.0f}" '
            f'y="{y + _CELL/2 + 4:.0f}" text-anchor="middle">{abbr}</text>'
            f'</g>'
        )

    svg = (
        f'<svg viewBox="0 0 {width} {height}" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;" '
        f'role="img" aria-label="US state map shaded by {_html.escape(metric_label)}">'
        + "".join(cells) +
        '</svg>'
    )

    # Legend — gradient for the metric + an accent swatch if used.
    if has_data:
        legend = (
            '<div class="usm-legend">'
            f'<span>{_html.escape(metric_label)}:</span>'
            f'<span>{_html.escape(fmt(lo))}</span>'
            '<span class="usm-legend-bar"></span>'
            f'<span>{_html.escape(fmt(hi))}</span>'
        )
        if accents:
            lbl = _html.escape(accent_label or "highlighted")
            legend += (
                f'<span style="margin-left:8px;"><span class="usm-legend-swatch" '
                f'style="background:transparent;border:2px solid {_ACCENT};"></span>'
                f'{lbl}</span>'
            )
        legend += (
            '<span style="margin-left:8px;"><span class="usm-legend-swatch" '
            f'style="background:{_NO_DATA_FILL};border:1px solid var(--sc-rule,#d6cfc0);">'
            '</span>no data</span></div>'
        )
    else:
        legend = ""

    empty = ""
    if not has_data and empty_message:
        empty = f'<p class="usm-empty">{_html.escape(empty_message)}</p>'

    return (
        _map_css(cid)
        + f'<div id="{cid}" style="position:relative;">'
        + svg
        + '<div class="usm-tip" role="status" aria-live="polite"></div>'
        + legend
        + empty
        + '</div>'
        + _map_js(cid)
    )
