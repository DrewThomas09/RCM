"""Self-contained world choropleth map (SVG) for international market views.

Renders the vendored Natural Earth country boundaries (``_world_geo_paths.py``,
equirectangular, public domain) as an SVG choropleth shaded by a per-country
metric. 100% local — no map tiles, no GeoJSON fetch, no external APIs at
runtime. Mirrors the spirit of ``us_geo_map.render_us_geo_map`` but for the
world: shade ``{ISO2: value}`` on a cream→teal scale, outline accent
countries, and surface name + value on hover.

Honesty: countries with no value render in the muted no-data shade — never
fabricated. The equirectangular projection trades shape fidelity for a clean,
dependency-free render; it is a market-orientation map, not a survey map.
"""
from __future__ import annotations

import html as _html
from typing import Callable, Dict, Optional

from ._world_geo_paths import WORLD_COUNTRY_PATHS, WORLD_GEO_VIEWBOX

_NODATA = "#e7dfca"       # muted cream — no value
_LO = (214, 232, 223)     # light green
_HI = (24, 87, 63)        # deep teal-green
_ACCENT = "#b8842e"       # amber outline
_uid = [0]


def _esc(s) -> str:
    return _html.escape("" if s is None else str(s))


def _shade(v: Optional[float], lo: float, hi: float) -> str:
    if v is None:
        return _NODATA
    if hi <= lo:
        t = 1.0
    else:
        t = (v - lo) / (hi - lo)
    t = max(0.0, min(1.0, t))
    r = round(_LO[0] + (_HI[0] - _LO[0]) * t)
    g = round(_LO[1] + (_HI[1] - _LO[1]) * t)
    b = round(_LO[2] + (_HI[2] - _LO[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def render_world_map(
    values: Dict[str, float],
    *,
    metric_label: str = "",
    value_format: Optional[Callable[[float], str]] = None,
    notes: Optional[Dict[str, str]] = None,
    accent: Optional[set] = None,
    accent_label: str = "accent market",
    empty_message: str = "No country-level data yet.",
    legend_label: str = "low → high",
    caveat_text: str = (
        "Equirectangular SVG world map (Natural Earth 1:110m boundaries, "
        "public domain). Country shading reflects the metric named in the "
        "legend; outlined countries are the accent markets. A market-"
        "orientation map, not a survey-grade or coastline-precise map."
    ),
) -> str:
    """Return a self-contained SVG world choropleth + legend.

    ``values`` maps ISO-3166 alpha-2 codes (upper-case) → metric value.
    """
    _uid[0] += 1
    cid = f"wgeo{_uid[0]}"
    values = {str(k).upper(): float(v) for k, v in (values or {}).items()}
    accent = {str(s).upper() for s in (accent or set())}
    notes = {str(k).upper(): v for k, v in (notes or {}).items()}
    fmt = value_format or (lambda v: f"{v:g}")
    has_data = bool(values)
    lo = min(values.values()) if values else 0.0
    hi = max(values.values()) if values else 1.0
    vbw, vbh = WORLD_GEO_VIEWBOX[2], WORLD_GEO_VIEWBOX[3]

    paths = []
    for iso2, rec in WORLD_COUNTRY_PATHS.items():
        v = values.get(iso2)
        fill = _shade(v, lo, hi)
        cls = "wgeo-c" + (" wgeo-accent" if iso2 in accent else "")
        if v is not None:
            vlabel = f"{fmt(v)}{(' ' + metric_label) if metric_label else ''}"
        else:
            vlabel = "no data"
        alabel = f"{rec['name']} — {vlabel}"
        if iso2 in accent:
            alabel += f"; {accent_label}"
        note = notes.get(iso2, "")
        title = _esc(alabel + (f" · {note}" if note else ""))
        paths.append(
            f'<path class="{cls}" data-iso="{iso2}" d="{rec["d"]}" fill="{fill}">'
            f"<title>{title}</title></path>"
        )

    # Legend gradient (only meaningful with data).
    if has_data:
        legend = (
            f'<div class="wgeo-legend"><span class="wgeo-lg-lab">{_esc(legend_label)}</span>'
            '<span class="wgeo-lg-bar"></span>'
            f'<span class="wgeo-lg-ends">{_esc(fmt(lo))}</span>'
            f'<span class="wgeo-lg-ends">{_esc(fmt(hi))}</span></div>'
        )
    else:
        legend = f'<div class="wgeo-empty">{_esc(empty_message)}</div>'
    accent_legend = (
        f'<span class="wgeo-accent-key">▢ {_esc(accent_label)}</span>'
        if accent else ""
    )

    css = (
        f"#{cid} .wgeo-wrap{{border:1px solid var(--sc-rule,#c9c1ac);"
        "background:var(--sc-paper,#faf6ec);padding:10px;border-radius:3px;}"
        f"#{cid} svg{{width:100%;height:auto;display:block;}}"
        f"#{cid} .wgeo-c{{stroke:#fff;stroke-width:.4;transition:opacity .12s;}}"
        f"#{cid} .wgeo-c:hover{{opacity:.78;}}"
        f"#{cid} .wgeo-accent{{stroke:{_ACCENT};stroke-width:1.1;}}"
        f"#{cid} .wgeo-legend{{display:flex;align-items:center;gap:8px;margin-top:8px;"
        "font-family:var(--sc-mono,monospace);font-size:10px;color:var(--sc-text-dim,#6a7480);}"
        f"#{cid} .wgeo-lg-bar{{flex:0 0 140px;height:9px;border:1px solid var(--sc-rule,#c9c1ac);"
        f"background:linear-gradient(90deg,rgb{_LO},rgb{_HI});}}"
        f"#{cid} .wgeo-lg-lab{{text-transform:uppercase;letter-spacing:.1em;}}"
        f"#{cid} .wgeo-accent-key{{color:{_ACCENT};margin-left:10px;}}"
        f"#{cid} .wgeo-empty{{font-family:var(--sc-serif,serif);font-style:italic;"
        "color:var(--sc-text-dim,#6a7480);margin-top:8px;}"
        f"#{cid} .wgeo-caveat{{font-size:10px;color:var(--sc-text-faint,#8b94a0);margin-top:6px;}}"
    )

    return (
        f'<div id="{cid}"><style>{css}</style><div class="wgeo-wrap">'
        f'<svg viewBox="0 0 {vbw} {vbh}" role="img" '
        f'aria-label="World choropleth map">{"".join(paths)}</svg>'
        f'<div style="display:flex;flex-wrap:wrap;align-items:center;">{legend}{accent_legend}</div>'
        f'<div class="wgeo-caveat">{_esc(caveat_text)}</div>'
        "</div></div>"
    )
