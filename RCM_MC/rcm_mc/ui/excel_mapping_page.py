"""Excel mapping — a configurable US-state choropleth you drive from
Python (or paste from Excel).

The point of this page is to be a *generic* mapping utility, separate
from any one analysis: set three gradient colors (low / mid / high),
hand it a ``{state: percentage}`` dict, and it colours every state by
interpolating the gradient across the values, printing each percentage
in black serif text on the tile.

Two ways to drive it:

  1. **In Python** — edit ``DEFAULT_STATE_VALUES`` and the three
     ``DEFAULT_*_COLOR`` constants below. That dict is the source of
     truth when no form input is supplied.
  2. **In the page** — the form accepts three colour pickers, an
     optional low/mid/high domain, and a textarea you can paste
     Excel rows into (``TX  61`` / ``TX,61`` / ``Texas 61`` — tab,
     comma, or whitespace separated).

Nothing here is a data claim: the default values are clearly-labelled
example placeholders meant to be overwritten with your own numbers.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from .cdd_chart_kit import chart_export_toolbar

# ── Editable config (drive the map from Python here) ─────────────────

#: Gradient stops — low value → mid value → high value.
DEFAULT_LOW_COLOR = "#fde0dd"     # light
DEFAULT_MID_COLOR = "#fa9fb5"     # midpoint
DEFAULT_HIGH_COLOR = "#7a0177"    # high

#: EXAMPLE values — edit this dict / paste your own per state (percent).
#: Placeholders only; replace with your real numbers.
DEFAULT_STATE_VALUES: Dict[str, float] = {
    "AL": 38, "AK": 30, "AZ": 55, "AR": 36, "CA": 63, "CO": 58,
    "CT": 61, "DE": 57, "DC": 64, "FL": 62, "GA": 49, "HI": 44,
    "ID": 41, "IL": 56, "IN": 50, "IA": 47, "KS": 46, "KY": 43,
    "LA": 39, "ME": 45, "MD": 60, "MA": 62, "MI": 54, "MN": 57,
    "MS": 34, "MO": 50, "MT": 40, "NE": 48, "NV": 55, "NH": 52,
    "NJ": 61, "NM": 47, "NY": 60, "NC": 51, "ND": 42, "OH": 53,
    "OK": 44, "OR": 56, "PA": 58, "RI": 60, "SC": 48, "SD": 43,
    "TN": 47, "TX": 61, "UT": 50, "VT": 42, "VA": 55, "WA": 58,
    "WV": 41, "WI": 52, "WY": 39,
}

# ── US tile grid (schematic; labelled, not a geographic projection) ──
_STATE_TILE: Dict[str, Tuple[int, int]] = {
    "AK": (0, 0), "ME": (0, 10),
    "VT": (1, 9), "NH": (1, 10),
    "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4),
    "IL": (2, 5), "WI": (2, 6), "MI": (2, 7), "NY": (2, 8), "MA": (2, 9),
    "RI": (2, 10),
    "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4),
    "IN": (3, 5), "OH": (3, 6), "PA": (3, 7), "NJ": (3, 8), "CT": (3, 9),
    "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4),
    "KY": (4, 5), "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9),
    "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5),
    "NC": (5, 6), "SC": (5, 7), "DC": (5, 8),
    "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6), "GA": (6, 7),
    "HI": (7, 0), "TX": (7, 3), "FL": (7, 8),
}

_NAME_TO_CODE = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "district of columbia": "DC", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY",
    "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")


# ── Gradient ─────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = (h or "").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (200, 200, 200)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (200, 200, 200)


def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c))) for c in rgb)


def _lerp(c0: Tuple[int, int, int], c1: Tuple[int, int, int],
          t: float) -> str:
    t = max(0.0, min(1.0, t))
    return _rgb_to_hex(tuple(c0[i] + (c1[i] - c0[i]) * t for i in range(3)))


def gradient_color(
    value: Optional[float], lo: float, mid: float, hi: float,
    c_low: str, c_mid: str, c_high: str,
) -> str:
    """Three-stop gradient: ``lo``→``c_low``, ``mid``→``c_mid``,
    ``hi``→``c_high``, linearly interpolated each side of the midpoint.
    ``None`` value → neutral grey (no data)."""
    if value is None:
        return "#e6e3dc"
    rl, rm, rh = _hex_to_rgb(c_low), _hex_to_rgb(c_mid), _hex_to_rgb(c_high)
    if hi <= lo:
        return c_mid
    if value <= mid:
        denom = (mid - lo) or 1.0
        return _lerp(rl, rm, (value - lo) / denom)
    denom = (hi - mid) or 1.0
    return _lerp(rm, rh, (value - mid) / denom)


# ── Input parsing ────────────────────────────────────────────────────

def parse_values_text(text: str) -> Dict[str, float]:
    """Parse pasted 'STATE<sep>VALUE' rows (tab / comma / whitespace
    separated; 2-letter code or full state name; trailing % ok) into a
    ``{code: value}`` dict. Bad rows are skipped."""
    out: Dict[str, float] = {}
    for raw in (text or "").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if "," in line:
            parts = [p.strip() for p in line.split(",")]
        elif "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        else:
            parts = line.rsplit(None, 1)
        if len(parts) < 2:
            continue
        key, val = parts[0], parts[-1]
        code = key.strip().upper()
        if code not in _STATE_TILE:
            code = _NAME_TO_CODE.get(key.strip().lower(), "")
        if not code:
            continue
        try:
            out[code] = float(val.replace("%", "").strip())
        except ValueError:
            continue
    return out


def _values_to_text(values: Dict[str, float]) -> str:
    return "\n".join(f"{k}\t{_fmt(v)}"
                     for k, v in sorted(values.items()))


def _fmt(v: float) -> str:
    return f"{v:g}"


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


# ── Render ───────────────────────────────────────────────────────────

def resolve_inputs(
    qs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve the effective colours / domain / values from the form
    (qs) with the Python module defaults as the fallback."""
    c_low = _qs1(qs, "low", DEFAULT_LOW_COLOR)
    c_mid = _qs1(qs, "mid", DEFAULT_MID_COLOR)
    c_high = _qs1(qs, "high", DEFAULT_HIGH_COLOR)
    data_text = _qs1(qs, "data", "")
    values = parse_values_text(data_text) if data_text.strip() \
        else dict(DEFAULT_STATE_VALUES)
    nums = [v for v in values.values() if v is not None]
    auto_lo = min(nums) if nums else 0.0
    auto_hi = max(nums) if nums else 100.0

    def _num(key: str, fallback: float) -> float:
        raw = _qs1(qs, key, "")
        try:
            return float(raw) if raw.strip() != "" else fallback
        except ValueError:
            return fallback
    lo = _num("lo", auto_lo)
    hi = _num("hi", auto_hi)
    mid = _num("midv", (lo + hi) / 2.0)
    return {
        "c_low": c_low, "c_mid": c_mid, "c_high": c_high,
        "lo": lo, "mid": mid, "hi": hi,
        "values": values, "data_text": data_text or _values_to_text(values),
    }


def _map_svg(cfg: Dict[str, Any]) -> str:
    cell, gap = 10.0, 0.8
    ncol, nrow = 11, 8
    vals, lo, mid, hi = (cfg["values"], cfg["lo"], cfg["mid"], cfg["hi"])
    tiles = ""
    for code, (r, c) in _STATE_TILE.items():
        v = vals.get(code)
        x, y = c * cell, r * cell
        fill = gradient_color(v, lo, mid, hi, cfg["c_low"], cfg["c_mid"],
                              cfg["c_high"])
        label = _fmt(v) if v is not None else ""
        tiles += (
            f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{cell-gap:.1f}" '
            f'height="{cell-gap:.1f}" rx="1.3" fill="{fill}" '
            f'stroke="#ffffff" stroke-width="0.5">'
            f'<title>{html.escape(code)}: {html.escape(label or "—")}</title>'
            f'</rect>'
            # Black serif text "above" (on top of) the gradient.
            f'<text x="{x+(cell-gap)/2:.1f}" y="{y+3.7:.1f}" '
            f'text-anchor="middle" font-family="{_SERIF}" font-size="2.9" '
            f'font-weight="700" fill="#000000">{html.escape(code)}</text>'
            f'<text x="{x+(cell-gap)/2:.1f}" y="{y+6.9:.1f}" '
            f'text-anchor="middle" font-family="{_SERIF}" font-size="3.0" '
            f'fill="#000000" style="paint-order:stroke;stroke:#ffffff;'
            f'stroke-width:0.5px;">{html.escape(label)}</text></g>')
    return (
        f'<svg viewBox="-1 -1 {ncol*cell+1:.0f} {nrow*cell+1:.0f}" '
        f'width="100%" height="430" role="img" '
        f'aria-label="US state choropleth" style="max-width:760px;">'
        f'{tiles}</svg>')


def _legend(cfg: Dict[str, Any]) -> str:
    grad = (f'linear-gradient(90deg,{cfg["c_low"]},{cfg["c_mid"]} 50%,'
            f'{cfg["c_high"]})')
    return (
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'font-family:{_SERIF};font-size:13px;color:#1a2332;margin-top:6px;">'
        f'<span>{_fmt(cfg["lo"])}</span>'
        f'<span style="flex:0 0 240px;height:14px;border-radius:3px;'
        f'background:{grad};border:1px solid #c9c1ac;"></span>'
        f'<span>{_fmt(cfg["mid"])}</span>'
        f'<span style="flex:0 0 0;"></span>'
        f'<span>{_fmt(cfg["hi"])}</span></div>')


def _form(cfg: Dict[str, Any]) -> str:
    def _color(label, name, val):
        return (
            f'<label style="display:flex;flex-direction:column;gap:3px;'
            f'font-size:11px;color:#465366;">{label}'
            f'<input type="color" name="{name}" value="{html.escape(val)}" '
            f'style="width:54px;height:30px;border:1px solid #c9c1ac;'
            f'border-radius:4px;padding:0;background:#fff;"></label>')

    def _num(label, name, val):
        return (
            f'<label style="display:flex;flex-direction:column;gap:3px;'
            f'font-size:11px;color:#465366;">{label}'
            f'<input type="text" name="{name}" value="{html.escape(_fmt(val))}" '
            f'inputmode="decimal" style="width:70px;height:28px;'
            f'border:1px solid #c9c1ac;border-radius:4px;padding:0 6px;'
            f'font-family:{_SERIF};"></label>')
    return (
        f'<form method="get" action="/excel-mapping" '
        f'style="border:1px solid #d6cfc0;border-radius:6px;padding:14px 16px;'
        f'background:#fbf9f4;margin-bottom:16px;">'
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;">'
        + _color("Low colour", "low", cfg["c_low"])
        + _color("Mid colour", "mid", cfg["c_mid"])
        + _color("High colour", "high", cfg["c_high"])
        + _num("Low value", "lo", cfg["lo"])
        + _num("Mid value", "midv", cfg["mid"])
        + _num("High value", "hi", cfg["hi"])
        + '</div>'
        + f'<div style="margin-top:12px;"><label style="font-size:11px;'
        f'color:#465366;">Percentages (paste from Excel — '
        f'<code>STATE&nbsp;VALUE</code> per line; tab, comma, or space)'
        f'<textarea name="data" rows="5" style="width:100%;margin-top:4px;'
        f'font-family:ui-monospace,Menlo,monospace;font-size:12px;'
        f'border:1px solid #c9c1ac;border-radius:4px;padding:8px;" '
        f'placeholder="TX\t61&#10;CA\t63&#10;New York\t60">'
        f'{html.escape(cfg["data_text"])}</textarea></label></div>'
        + f'<button type="submit" style="margin-top:10px;padding:8px 18px;'
        f'background:#0b2341;color:#fff;border:none;border-radius:4px;'
        f'font-weight:600;cursor:pointer;">Render map</button>'
        f'<a href="/excel-mapping" style="margin-left:10px;font-size:12px;'
        f'color:#1F7A75;">Reset to defaults</a>'
        f'</form>')


def _data_table(cfg: Dict[str, Any]) -> str:
    rows = ""
    for code, v in sorted(cfg["values"].items(),
                          key=lambda kv: -(kv[1] if kv[1] is not None else -1)):
        sw = gradient_color(v, cfg["lo"], cfg["mid"], cfg["hi"],
                            cfg["c_low"], cfg["c_mid"], cfg["c_high"])
        rows += (
            f'<tr style="border-bottom:1px solid #e8e1d0;">'
            f'<td style="padding:3px 8px;"><span style="display:inline-block;'
            f'width:11px;height:11px;border-radius:2px;background:{sw};'
            f'border:1px solid #c9c1ac;margin-right:6px;vertical-align:-1px;">'
            f'</span>{html.escape(code)}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-family:{_SERIF};font-weight:600;">{_fmt(v)}</td></tr>')
    return (
        f'<table style="border-collapse:collapse;font-size:12px;width:100%;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;color:#7a8699;">'
        f'<th style="text-align:left;padding:3px 8px;">State</th>'
        f'<th style="text-align:right;padding:3px 8px;">Value</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>')


def render_excel_mapping_page(qs: "Dict[str, Any] | None" = None) -> str:
    """Render the Excel-mapping choropleth page from the form inputs (or
    the Python defaults)."""
    cfg = resolve_inputs(qs)
    body = (
        ck_page_title(
            "Excel Mapping",
            eyebrow="UTILITY · STATE CHOROPLETH",
            meta="Set low / mid / high colours + a value per state — "
                 "gradient + black serif labels.",
        )
        + ck_source_purpose(
            purpose="A generic US-state choropleth you drive from a "
                    "{state: percentage} dict or an Excel paste.",
            universe="user-supplied",
            source="Your inputs. Default values are example placeholders "
                   "— overwrite them with your own numbers.",
        )
        + '<div class="ts-wrap" style="max-width:980px;">'
        + _form(cfg)
        + f'<div id="mapOut" style="font-family:{_SERIF};">{_map_svg(cfg)}'
        f'</div>'
        + _legend(cfg)
        + chart_export_toolbar("mapOut", "state-map")
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;'
          'margin-top:18px;align-items:start;">'
        + '<div><div style="font-size:10px;letter-spacing:0.06em;'
          'color:#7a8699;font-weight:700;margin-bottom:4px;">VALUES BY '
          'STATE</div>'
        + _data_table(cfg) + '</div>'
        + '<div style="font-size:12px;color:#465366;line-height:1.7;">'
          '<div style="font-size:10px;letter-spacing:0.06em;color:#7a8699;'
          'font-weight:700;margin-bottom:4px;">HOW TO USE</div>'
          '<p><strong>In Python:</strong> edit '
          '<code>DEFAULT_STATE_VALUES</code> and the three '
          '<code>DEFAULT_*_COLOR</code> constants in '
          '<code>excel_mapping_page.py</code>.</p>'
          '<p style="margin-top:6px;"><strong>In the page:</strong> pick '
          'the three colours, optionally set the low/mid/high value '
          'domain (blank = auto from your data), and paste '
          '<code>STATE&nbsp;VALUE</code> rows from Excel. The gradient '
          'interpolates low→mid→high; each state shows its value in black '
          'serif text.</p></div>'
        + '</div></div>')
    return chartis_shell(
        body, "Excel Mapping", active_nav="/research",
        subtitle="State choropleth utility")
