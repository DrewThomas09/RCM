"""Excel mapping — a configurable real-geography US choropleth you
drive from Python (or paste from Excel).

The point of this page is to be a *generic* mapping utility, separate
from any one analysis: set three gradient colors (low / mid / high),
hand it a ``{state: percentage}`` dict, and it colours every state by
interpolating the gradient across the values, printing each value in
black serif text on the state.

The map is the real United States — the same vendored Albers-projected
US Census state boundaries that power /portfolio/map
(``_us_geo_paths.py``; public domain, no runtime network) — not a
square-tile cartogram. Alaska and Hawaii render as bottom-left insets;
the nine small Northeast jurisdictions (VT NH MA RI CT NJ DE MD DC)
are labelled in a swatch column beside the Atlantic seaboard because
their shapes are too small to hold text.

Two ways to drive it:

  1. **In Python** — edit ``DEFAULT_STATE_VALUES`` and the three
     ``DEFAULT_*_COLOR`` constants below. That dict is the source of
     truth when no form input is supplied.
  2. **In the page** — the form accepts three colour pickers, an
     optional low/mid/high domain, a map title, and a textarea you can
     paste Excel rows into (``TX  61`` / ``TX,61`` / ``Texas 61`` —
     tab, comma, or whitespace separated). The whole configuration
     lives in the URL, so the rendered map is shareable as a link.

Nothing here is a data claim: the default values are clearly-labelled
example placeholders meant to be overwritten with your own numbers.
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional, Tuple

from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from ._us_geo_paths import US_STATE_PATHS
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

#: code → full name, straight from the vendored Census geometry, so the
#: set of valid codes and the drawn shapes can never disagree.
STATE_NAMES: Dict[str, str] = {
    code: rec["name"] for code, rec in US_STATE_PATHS.items()}

_NAME_TO_CODE = {name.lower(): code for code, name in STATE_NAMES.items()}

#: Northeast jurisdictions too small to hold an on-shape label — they
#: get a swatch column in the Atlantic gutter instead (north → south).
_CALLOUT_STATES: Tuple[str, ...] = (
    "VT", "NH", "MA", "RI", "CT", "NJ", "DE", "MD", "DC")

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")

#: Monotonic counter for per-render SVG element ids (gradient defs).
_uid = [0]


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
        if code not in STATE_NAMES:
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


# ── Geometry: on-shape label anchors ─────────────────────────────────

_PAIR_RE = re.compile(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)")

#: Hand nudges (dx, dy) where the polygon centroid sits awkwardly —
#: Louisiana's delta pulls it east, Hawaii's label reads better beside
#: the island chain than on top of it.
_ANCHOR_NUDGE: Dict[str, Tuple[float, float]] = {
    "LA": (-5.0, -5.0),
    "HI": (14.0, -16.0),
    "AK": (-14.0, -8.0),
    # PR is a sliver inset at the very bottom-right corner; lift the
    # label above it so the value line doesn't clip the viewBox edge.
    "PR": (0.0, -12.0),
}

_anchor_cache: Dict[str, Tuple[float, float]] = {}


def _label_anchors() -> Dict[str, Tuple[float, float]]:
    """Shoelace centroid of each state's largest subpath (so Michigan
    labels its lower peninsula, Hawaii its biggest island), cached."""
    if _anchor_cache:
        return _anchor_cache
    for code, rec in US_STATE_PATHS.items():
        best: Optional[Tuple[float, float, float]] = None  # area, cx, cy
        for seg in rec["d"].split("M"):
            pts = [(float(x), float(y)) for x, y in _PAIR_RE.findall(seg)]
            if len(pts) < 3:
                continue
            a = cx = cy = 0.0
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                cross = x0 * y1 - x1 * y0
                a += cross
                cx += (x0 + x1) * cross
                cy += (y0 + y1) * cross
            if abs(a) < 1e-9:
                continue
            if best is None or abs(a) / 2 > best[0]:
                best = (abs(a) / 2, cx / (3 * a), cy / (3 * a))
        if best is None:
            continue
        dx, dy = _ANCHOR_NUDGE.get(code, (0.0, 0.0))
        _anchor_cache[code] = (best[1] + dx, best[2] + dy)
    return _anchor_cache


# ── Render ───────────────────────────────────────────────────────────

def resolve_inputs(
    qs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve the effective colours / domain / values / title from the
    form (qs) with the Python module defaults as the fallback."""
    c_low = _qs1(qs, "low", DEFAULT_LOW_COLOR)
    c_mid = _qs1(qs, "mid", DEFAULT_MID_COLOR)
    c_high = _qs1(qs, "high", DEFAULT_HIGH_COLOR)
    data_text = _qs1(qs, "data", "")
    title = _qs1(qs, "title", "").strip()
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
        "lo": lo, "mid": mid, "hi": hi, "title": title,
        "values": values, "data_text": data_text or _values_to_text(values),
    }


def _ranks(values: Dict[str, float]) -> Dict[str, int]:
    ordered = sorted(values.items(), key=lambda kv: -kv[1])
    return {code: i + 1 for i, (code, _) in enumerate(ordered)}


def _label_text(x: float, y: float, code: str, label: str,
                cls: str = "em-label", scale: float = 1.0,
                mode: str = "full") -> str:
    """Two-line black serif label (code over value) with a white halo so
    it stays legible on the dark end of the gradient. The halo is a
    separate underlying stroke-only copy (not paint-order) so exported
    SVGs survive renderers that ignore paint-order (Office, cairosvg).
    ``mode="value"`` drops the code line — compact embeds (infusion
    pages) read the state from the geography and need the number big."""
    def _line(yy: float, size: float, weight: str, text: str) -> str:
        common = (f'class="{cls}" x="{x:.1f}" y="{yy:.1f}" '
                  f'text-anchor="middle" font-family="{_SERIF}" '
                  f'font-size="{size * scale:g}" font-weight="{weight}" '
                  f'pointer-events="none"')
        t = html.escape(text)
        return (f'<text {common} fill="none" stroke="#ffffff" '
                f'stroke-width="{1.7 * scale:g}" stroke-linejoin="round">'
                f'{t}</text><text {common} fill="#000000">{t}</text>')
    if mode == "value":
        return _line(y + 3.5 * scale, 9.5, "700", label) if label else ""
    out = _line(y - 1.5 * scale, 9, "700", code)
    if label:
        out += _line(y + 8.5 * scale, 9.5, "400", label)
    return out


def _svg_legend(cfg: Dict[str, Any]) -> str:
    """Gradient legend drawn inside the SVG (bottom-right gutter) so
    SVG/PNG exports are self-contained."""
    x, y, w, h = 700.0, 508.0, 220.0, 12.0
    sfx = cfg.get("legend_suffix", "")
    stops = (
        f'<stop offset="0%" stop-color="{html.escape(cfg["c_low"])}"/>'
        f'<stop offset="50%" stop-color="{html.escape(cfg["c_mid"])}"/>'
        f'<stop offset="100%" stop-color="{html.escape(cfg["c_high"])}"/>')
    tick = (f'font-family="{_SERIF}" font-size="11" fill="#1a2332" '
            f'pointer-events="none"')
    # Per-render gradient id: two compact maps on one page (or a page
    # plus the visuals-hub thumbnail) must not share a <defs> id.
    _uid[0] += 1
    gid = f"emGrad{_uid[0]}"
    return (
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
        f'{stops}</linearGradient></defs>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" '
        f'fill="url(#{gid})" stroke="#c9c1ac" stroke-width="0.6"/>'
        f'<text x="{x}" y="{y + h + 12}" text-anchor="start" {tick}>'
        f'{_fmt(cfg["lo"])}{sfx}</text>'
        f'<text x="{x + w / 2}" y="{y + h + 12}" text-anchor="middle" {tick}>'
        f'{_fmt(cfg["mid"])}{sfx}</text>'
        f'<text x="{x + w}" y="{y + h + 12}" text-anchor="end" {tick}>'
        f'{_fmt(cfg["hi"])}{sfx}</text>'
        f'<rect x="{x}" y="{y - 22}" width="11" height="11" rx="2" '
        f'fill="#e6e3dc" stroke="#c9c1ac" stroke-width="0.6"/>'
        f'<text x="{x + 16}" y="{y - 13}" text-anchor="start" {tick}>'
        f'no data</text>')


def _map_svg(cfg: Dict[str, Any]) -> str:
    """Geographic US choropleth from a cfg dict. Required keys:
    ``values`` / ``lo`` / ``mid`` / ``hi`` / ``c_low`` / ``c_mid`` /
    ``c_high``. Optional keys (read with .get so minimal callers like
    ma_penetration_page keep working): ``title``, ``accent`` (codes
    outlined in ``accent_color``), ``notes`` ({code: hover suffix}),
    ``legend_suffix``, ``label_mode`` ("full" | "value" | "none"),
    ``label_scale``, ``max_width_px``, ``aria_label``."""
    vals, lo, mid, hi = cfg["values"], cfg["lo"], cfg["mid"], cfg["hi"]
    anchors = _label_anchors()
    ranks = _ranks(vals)
    n_ranked = len(ranks)
    accent = {str(c).upper() for c in (cfg.get("accent") or ())}
    accent_color = cfg.get("accent_color", "#b5321e")
    notes = cfg.get("notes") or {}
    label_mode = cfg.get("label_mode", "full")
    label_scale = float(cfg.get("label_scale", 1.0))
    max_width = int(cfg.get("max_width_px", 980))

    shapes, accents, labels = "", "", ""
    for code, rec in US_STATE_PATHS.items():
        v = vals.get(code)
        fill = gradient_color(v, lo, mid, hi, cfg["c_low"], cfg["c_mid"],
                              cfg["c_high"])
        label = _fmt(v) if v is not None else ""
        name = rec["name"]
        tip = f"{name} — {label or 'no data'}"
        if code in notes:
            tip += f" · {notes[code]}"
        rank_attr = (f' data-rank="{ranks[code]}" data-n="{n_ranked}"'
                     if code in ranks else "")
        if code in accent:
            stroke, sw = accent_color, "1.8"
        else:
            stroke, sw = "#ffffff", "0.7"
        path = (
            f'<path class="em-state" data-state="{code}" '
            f'data-name="{html.escape(name)}" '
            f'data-value="{html.escape(label)}"{rank_attr} '
            f'd="{rec["d"]}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" tabindex="0" role="button" '
            f'aria-label="{html.escape(tip)}">'
            f'<title>{html.escape(tip)}</title></path>')
        # Accent-outlined states paint after their neighbours so the
        # coloured stroke isn't half-covered by adjacent white borders.
        if code in accent:
            accents += path
        else:
            shapes += path
        if (label_mode != "none" and code not in _CALLOUT_STATES
                and code in anchors):
            ax, ay = anchors[code]
            labels += _label_text(ax, ay, code, label,
                                  scale=label_scale, mode=label_mode)

    # Small-Northeast swatch column in the Atlantic gutter.
    callouts = ""
    if label_mode != "none":
        cx, cy0, step = 812.0, 96.0, 26.0
        for i, code in enumerate(_CALLOUT_STATES):
            v = vals.get(code)
            fill = gradient_color(v, lo, mid, hi, cfg["c_low"], cfg["c_mid"],
                                  cfg["c_high"])
            label = _fmt(v) if v is not None else "—"
            y = cy0 + i * step
            callouts += (
                f'<g class="em-callout" data-state="{code}">'
                f'<rect x="{cx}" y="{y}" width="15" height="15" rx="2.5" '
                f'fill="{fill}" stroke="#ffffff" stroke-width="0.7">'
                f'<title>{html.escape(STATE_NAMES[code])}: '
                f'{html.escape(label)}</title></rect>'
                f'<text x="{cx + 22}" y="{y + 11.5}" text-anchor="start" '
                f'font-family="{_SERIF}" font-size="11" font-weight="700" '
                f'fill="#000000" pointer-events="none">{html.escape(code)}'
                f'</text><text x="{cx + 52}" y="{y + 11.5}" '
                f'text-anchor="start" '
                f'font-family="{_SERIF}" font-size="11" fill="#000000" '
                f'pointer-events="none">{html.escape(label)}</text></g>')

    title_el = ""
    if cfg.get("title"):
        title_el = (
            f'<text x="952" y="22" text-anchor="end" '
            f'font-family="{_SERIF}" font-size="18" font-weight="700" '
            f'fill="#0b2341" pointer-events="none">'
            f'{html.escape(cfg["title"])}</text>')

    aria = cfg.get("aria_label", "US state choropleth (geographic)")
    return (
        f'<svg viewBox="0 0 960 553" width="100%" role="img" '
        f'aria-label="{html.escape(aria)}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="max-width:{max_width}px;display:block;background:#fdfcf9;'
        f'border:1px solid #d6cfc0;border-radius:6px;">'
        f'{title_el}{shapes}{accents}'
        f'<g id="emLabels">{labels}{callouts}</g>'
        f'{_svg_legend(cfg)}</svg>')


def _stats(cfg: Dict[str, Any]) -> str:
    vals = {k: v for k, v in cfg["values"].items() if v is not None}
    if not vals:
        return ""
    nums = sorted(vals.values())
    n = len(nums)
    mean = sum(nums) / n
    median = (nums[n // 2] if n % 2 else (nums[n // 2 - 1] + nums[n // 2]) / 2)
    hi_code = max(vals, key=lambda k: vals[k])
    lo_code = min(vals, key=lambda k: vals[k])

    def _cell(label: str, value: str) -> str:
        return (
            f'<div style="border:1px solid #d6cfc0;border-radius:6px;'
            f'background:#fbf9f4;padding:8px 14px;min-width:108px;">'
            f'<div style="font-size:10px;letter-spacing:0.06em;'
            f'color:#7a8699;font-weight:700;">{label}</div>'
            f'<div class="num" style="font-family:{_SERIF};font-size:17px;'
            f'font-weight:700;color:#1a2332;">{value}</div></div>')
    return (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">'
        + _cell("STATES", f"{n} / {len(STATE_NAMES)}")
        + _cell("HIGHEST", f"{html.escape(hi_code)} · {_fmt(vals[hi_code])}")
        + _cell("LOWEST", f"{html.escape(lo_code)} · {_fmt(vals[lo_code])}")
        + _cell("MEAN", _fmt(round(mean, 1)))
        + _cell("MEDIAN", _fmt(median))
        + '</div>')


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
        + f'<label style="display:flex;flex-direction:column;gap:3px;'
        f'font-size:11px;color:#465366;flex:1 1 180px;">Map title (optional, '
        f'drawn on the export)'
        f'<input type="text" name="title" value="{html.escape(cfg["title"])}" '
        f'maxlength="80" placeholder="e.g. MA penetration by state, 2025" '
        f'style="height:28px;border:1px solid #c9c1ac;border-radius:4px;'
        f'padding:0 8px;font-family:{_SERIF};"></label>'
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


def _map_css_js() -> str:
    css = (
        '<style>'
        '#mapOut{position:relative;}'
        '#mapOut .em-state{transition:filter .12s,stroke .12s;cursor:pointer;}'
        '#mapOut .em-state:hover{filter:brightness(.9);stroke:#0b2341;'
        'stroke-width:1.4;}'
        '#mapOut .em-state:focus-visible{outline:none;stroke:#1F7A75;'
        'stroke-width:2;}'
        '#mapOut .em-state.em-selected{stroke:#0b2341;stroke-width:2.4;}'
        '#emTip{display:none;position:absolute;pointer-events:none;'
        'background:#0b2341;color:#fff;font-size:12px;padding:5px 10px;'
        'border-radius:4px;white-space:nowrap;z-index:5;'
        'box-shadow:0 2px 8px rgba(11,35,65,.25);}'
        '</style>')
    js = (
        "<script>(function(){"
        "var root=document.getElementById('mapOut');if(!root)return;"
        "var tip=document.getElementById('emTip');"
        "var chip=document.getElementById('emSel');"
        "function tipText(p){var v=p.dataset.value;"
        "var t=p.dataset.name+' \\u2014 '+(v||'no data');"
        "if(p.dataset.rank)t+='  (rank '+p.dataset.rank+' of '+p.dataset.n+')';"
        "return t;}"
        "root.querySelectorAll('.em-state').forEach(function(p){"
        "p.addEventListener('mousemove',function(e){"
        "tip.textContent=tipText(p);tip.style.display='block';"
        "var r=root.getBoundingClientRect();"
        "tip.style.left=(e.clientX-r.left+16)+'px';"
        "tip.style.top=(e.clientY-r.top-8)+'px';});"
        "p.addEventListener('mouseleave',function(){"
        "tip.style.display='none';});"
        "function pick(){var was=p.classList.contains('em-selected');"
        "root.querySelectorAll('.em-selected').forEach(function(o){"
        "o.classList.remove('em-selected');});"
        "if(was){chip.style.display='none';return;}"
        "p.classList.add('em-selected');"
        "chip.textContent=tipText(p);chip.style.display='inline-block';}"
        "p.addEventListener('click',pick);"
        "p.addEventListener('keydown',function(e){"
        "if(e.key==='Enter'||e.key===' '){e.preventDefault();pick();}});});"
        "var cb=document.getElementById('emLabelsToggle');"
        "if(cb)cb.addEventListener('change',function(){"
        "var g=root.querySelector('#emLabels');"
        "if(g)g.style.display=cb.checked?'':'none';});"
        "})();</script>")
    return css + js


def _data_table(cfg: Dict[str, Any]) -> str:
    rows = ""
    ordered = sorted(cfg["values"].items(),
                     key=lambda kv: -(kv[1] if kv[1] is not None else -1))
    for rank, (code, v) in enumerate(ordered, start=1):
        sw = gradient_color(v, cfg["lo"], cfg["mid"], cfg["hi"],
                            cfg["c_low"], cfg["c_mid"], cfg["c_high"])
        rows += (
            f'<tr style="border-bottom:1px solid #e8e1d0;">'
            f'<td class="num" style="padding:3px 8px;color:#7a8699;'
            f'text-align:right;">{rank}</td>'
            f'<td style="padding:3px 8px;"><span style="display:inline-block;'
            f'width:11px;height:11px;border-radius:2px;background:{sw};'
            f'border:1px solid #c9c1ac;margin-right:6px;vertical-align:-1px;">'
            f'</span>{html.escape(code)} '
            f'<span style="color:#7a8699;">'
            f'{html.escape(STATE_NAMES.get(code, ""))}</span></td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-family:{_SERIF};font-weight:600;">{_fmt(v)}</td></tr>')
    return (
        f'<table style="border-collapse:collapse;font-size:12px;width:100%;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;color:#7a8699;">'
        f'<th style="text-align:right;padding:3px 8px;">#</th>'
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
            meta="Real-geography US map — set low / mid / high colours + a "
                 "value per state; gradient fills + black serif labels.",
        )
        + ck_source_purpose(
            purpose="A generic US-state choropleth (real Census geography, "
                    "Albers projection) you drive from a "
                    "{state: percentage} dict or an Excel paste.",
            universe="user-supplied",
            source="Your inputs. Default values are example placeholders "
                   "— overwrite them with your own numbers.",
        )
        + '<div class="ts-wrap" style="max-width:1010px;">'
        + _form(cfg)
        + '<div style="display:flex;gap:14px;align-items:center;'
          'flex-wrap:wrap;margin-bottom:6px;">'
          '<label style="font-size:12px;color:#465366;display:inline-flex;'
          'align-items:center;gap:6px;cursor:pointer;">'
          '<input type="checkbox" id="emLabelsToggle" checked>Show labels'
          '</label>'
          '<span id="emSel" style="display:none;font-size:12px;'
          'font-weight:600;color:#0b2341;background:#fbf9f4;'
          'border:1px solid #d6cfc0;border-radius:4px;padding:3px 10px;">'
          '</span>'
          '<span style="font-size:11px;color:#7a8699;">Hover a state for '
          'detail · click to pin · the URL captures this exact map, so '
          'copy it to share.</span></div>'
        + f'<div id="mapOut" style="font-family:{_SERIF};">{_map_svg(cfg)}'
        f'<div id="emTip"></div></div>'
        + _map_css_js()
        + _stats(cfg)
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
          'domain (blank = auto from your data) and a map title, and '
          'paste <code>STATE&nbsp;VALUE</code> rows from Excel. The '
          'gradient interpolates low→mid→high; each state shows its '
          'value in black serif text.</p>'
          '<p style="margin-top:6px;"><strong>Geography:</strong> real US '
          'Census state boundaries (Albers projection, public domain). '
          'Alaska and Hawaii are bottom-left insets, Puerto Rico a '
          'bottom-right inset; the nine small Northeast jurisdictions '
          '(VT NH MA RI CT NJ DE MD DC) are labelled in the swatch '
          'column beside the Atlantic coast because their shapes are '
          'too small to hold text.</p>'
          '<p style="margin-top:6px;"><strong>Export:</strong> the '
          'SVG/PNG downloads include the legend and title, so the file '
          'drops straight into a deck.</p></div>'
        + '</div></div>')
    return chartis_shell(
        body, "Excel Mapping", active_nav="/research",
        subtitle="State choropleth utility")
