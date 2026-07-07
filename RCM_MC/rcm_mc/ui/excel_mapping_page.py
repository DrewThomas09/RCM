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

from ._chartis_kit import (
    chartis_shell, ck_copy_share_link_button, ck_editorial_head,
    ck_empty_state, ck_eyebrow, ck_fmt_number, ck_kpi_block,
    ck_print_view_button, ck_provenance_tooltip, ck_section_header,
    ck_signal_badge,
)
from ._us_geo_paths import US_STATE_PATHS
from .cdd_chart_kit import chart_export_toolbar

# ── Editable config (drive the map from Python here) ─────────────────

#: Gradient stops — low value → mid value → high value. The defaults
#: follow the kit's documented sequential chart ramp (see "Inline-SVG
#: editorial charts" in rcm_mc/ui/README.md): soft-green → teal →
#: teal-deep, so a fresh page (and the /visuals hub thumbnail, which
#: inherits these via ``resolve_inputs(None)``) opens on the house
#: palette rather than an ad-hoc one. The pickers still override.
DEFAULT_LOW_COLOR = "#7ED3A8"     # soft-green (low)
DEFAULT_MID_COLOR = "#1F7A75"     # teal (midpoint)
DEFAULT_HIGH_COLOR = "#155752"    # teal-deep (high)

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
    # Literal ink hex (not var()) — the legend is baked into SVG/PNG
    # exports, which must stay self-contained. #16263a is the kit's
    # canonical --ink fallback.
    tick = (f'font-family="{_SERIF}" font-size="11" fill="#16263a" '
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
            f'd="{rec["d"]}" fill="{html.escape(fill)}" stroke="{stroke}" '
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
                f'fill="{html.escape(fill)}" stroke="#ffffff" stroke-width="0.7">'
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
    """Summary KPI strip — ``ck_kpi_block`` row replacing the legacy
    hand-rolled mini-tiles. Mean and median are BOTH formatted to 1dp
    (they used to mix ``round(x, 1)`` with raw ``%g``, so '50.5' could
    sit beside '50'). ``ck_kpi_block`` does not escape value/sub, so
    the two user-derived state codes pass through ``html.escape``
    here, upstream."""
    vals = {k: v for k, v in cfg["values"].items() if v is not None}
    if not vals:
        return ""
    nums = sorted(vals.values())
    n = len(nums)
    mean = sum(nums) / n
    median = (nums[n // 2] if n % 2 else (nums[n // 2 - 1] + nums[n // 2]) / 2)
    hi_code = max(vals, key=lambda k: vals[k])
    lo_code = min(vals, key=lambda k: vals[k])
    coverage = ck_provenance_tooltip(
        "States covered",
        f'{ck_fmt_number(n)}<span class="em-kpi-of"> / '
        f'{len(STATE_NAMES)}</span>',
        explainer=(
            f"Jurisdictions with a supplied value, out of the "
            f"{len(STATE_NAMES)} the map draws (50 states + DC + PR). "
            "States without a value render in neutral grey."),
    )
    mean_v = ck_provenance_tooltip(
        "Mean", f"{ck_fmt_number(mean, precision=1)}%",
        explainer=(
            "Unweighted arithmetic mean of the supplied values — states "
            "are not population-weighted."),
        inject_css=False,
    )
    median_v = ck_provenance_tooltip(
        "Median", f"{ck_fmt_number(median, precision=1)}%",
        explainer=(
            "Middle of the sorted supplied values (mean of the two "
            "middle values when the count is even)."),
        inject_css=False,
    )
    return (
        '<div class="ck-kpi-grid em-kpis">'
        + ck_kpi_block("States", coverage, "with a supplied value")
        + ck_kpi_block(
            "Highest",
            f"{html.escape(hi_code)} · {_fmt(vals[hi_code])}%",
            html.escape(STATE_NAMES.get(hi_code, "")))
        + ck_kpi_block(
            "Lowest",
            f"{html.escape(lo_code)} · {_fmt(vals[lo_code])}%",
            html.escape(STATE_NAMES.get(lo_code, "")))
        + ck_kpi_block("Mean", mean_v, "unweighted")
        + ck_kpi_block("Median", median_v, "50th percentile")
        + '</div>')


def _form(cfg: Dict[str, Any]) -> str:
    """Configure-map panel — kit-styled via the namespaced ``.em-form``
    classes emitted in ``_map_css_js``. The GET method IS the product
    feature (config-in-URL sharing), so the action and every input
    name are contract: ``low``/``mid``/``high`` colour pickers,
    ``lo``/``midv``/``hi`` domain, ``title``, ``data`` paste — as is
    the 'Render map' submit copy (pinned by tests)."""
    def _color(label: str, name: str, val: str) -> str:
        return (
            f'<label class="em-field"><span class="em-field-label">'
            f'{label}</span>'
            f'<input type="color" name="{name}" '
            f'value="{html.escape(val)}"></label>')

    def _num(label: str, name: str, val: float) -> str:
        return (
            f'<label class="em-field"><span class="em-field-label">'
            f'{label}</span>'
            f'<input type="text" class="em-num-input" name="{name}" '
            f'value="{html.escape(_fmt(val))}" inputmode="decimal">'
            f'</label>')
    return (
        '<form method="get" action="/excel-mapping" class="em-form">'
        + ck_eyebrow("Configure map")
        + '<div class="em-form-grid">'
        + _color("Low colour", "low", cfg["c_low"])
        + _color("Mid colour", "mid", cfg["c_mid"])
        + _color("High colour", "high", cfg["c_high"])
        + _num("Low value", "lo", cfg["lo"])
        + _num("Mid value", "midv", cfg["mid"])
        + _num("High value", "hi", cfg["hi"])
        + '<label class="em-field em-title-field">'
          '<span class="em-field-label">Map title · drawn on the '
          'export</span>'
          f'<input type="text" class="em-title-input" name="title" '
          f'value="{html.escape(cfg["title"])}" maxlength="80" '
          f'placeholder="e.g. MA penetration by state, 2025"></label>'
        + '</div>'
        + '<label class="em-data-label">'
          '<span class="em-field-label">Percentages · one state per '
          'line</span> '
          '<span class="em-data-hint">TX&nbsp;61 · TX,61 · '
          'Texas&nbsp;61 · trailing % ok</span>'
          f'<textarea name="data" rows="5" '
          f'placeholder="TX\t61&#10;CA\t63&#10;New York\t60">'
          f'{html.escape(cfg["data_text"])}</textarea></label>'
        + '<div class="em-actions">'
          '<button type="submit" class="em-submit">Render map</button>'
          '<a class="em-reset" href="/excel-mapping">Reset to defaults</a>'
          '</div>'
        + '</form>')


def _map_css_js() -> str:
    """One namespaced ``<style>`` block for the whole page layer (kit
    vars with canonical fallbacks — no page hexes off the palette)
    plus the map's vanilla-JS behaviour. The JS binds by id to
    ``mapOut`` / ``emTip`` / ``emSel`` / ``emLabelsToggle`` — those
    ids are contract with the markup in ``render_excel_mapping_page``.
    Keyboard users get the tooltip on path FOCUS (anchored to the
    state's bounding box), not just on Enter/Space pick."""
    css = (
        '<style>'
        '.em-wrap{max-width:1010px;}'
        # — Configure-map form —
        '.em-form{background:var(--paper-card,#fefcf3);'
        'border:1px solid var(--sc-rule,#d6cfc0);border-radius:6px;'
        'padding:16px 18px 14px;margin:18px 0 16px;}'
        '.em-form .ck-eyebrow{margin-bottom:12px;}'
        '.em-form-grid{display:flex;gap:16px;flex-wrap:wrap;'
        'align-items:flex-end;}'
        '.em-field{display:flex;flex-direction:column;gap:4px;}'
        '.em-field-label{font-family:var(--sc-mono,monospace);'
        'font-size:10px;font-weight:600;letter-spacing:.08em;'
        'text-transform:uppercase;color:var(--sc-text-dim,#465366);}'
        '.em-form input[type=color]{width:54px;height:32px;'
        'border:1px solid var(--sc-rule,#c9c1ac);border-radius:3px;'
        'padding:2px;background:#fff;cursor:pointer;}'
        '.em-num-input{width:78px;height:30px;padding:0 8px;'
        'border:1px solid var(--sc-rule,#c9c1ac);border-radius:3px;'
        'background:#fff;color:var(--ink,#16263a);'
        'font-family:var(--sc-mono,monospace);font-size:12.5px;'
        'font-variant-numeric:tabular-nums;}'
        '.em-title-field{flex:1 1 200px;}'
        '.em-title-input{height:30px;padding:0 10px;'
        'border:1px solid var(--sc-rule,#c9c1ac);border-radius:3px;'
        'background:#fff;color:var(--ink,#16263a);'
        "font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);"
        'font-size:13.5px;}'
        '.em-data-label{display:block;margin-top:14px;}'
        '.em-data-hint{font-family:var(--sc-mono,monospace);'
        'font-size:10.5px;letter-spacing:.03em;'
        'color:var(--sc-text-faint,#7a8699);}'
        '.em-form textarea{width:100%;margin-top:5px;padding:8px 10px;'
        'border:1px solid var(--sc-rule,#c9c1ac);border-radius:3px;'
        'background:#fff;color:var(--ink,#16263a);'
        'font-family:var(--sc-mono,monospace);font-size:12px;'
        'line-height:1.55;box-sizing:border-box;}'
        '.em-form input:focus-visible,.em-form textarea:focus-visible,'
        '.em-form button:focus-visible,.em-form a:focus-visible'
        '{outline:2px solid var(--green-deep,#154e36);outline-offset:2px;}'
        '.em-actions{display:flex;align-items:center;gap:14px;'
        'margin-top:12px;}'
        '.em-submit{padding:8px 20px;background:var(--green-deep,#154e36);'
        'color:#fff;border:none;border-radius:3px;'
        'font-family:var(--sc-sans,Inter,sans-serif);font-size:13px;'
        'font-weight:600;letter-spacing:.02em;cursor:pointer;}'
        '.em-submit:hover{background:var(--sc-teal,#155752);}'
        '.em-reset{font-family:var(--sc-mono,monospace);font-size:10.5px;'
        'font-weight:600;letter-spacing:.06em;text-transform:uppercase;'
        'color:var(--sc-text-dim,#465366);text-decoration:none;'
        'border-bottom:1px solid var(--sc-rule,#d6cfc0);'
        'padding-bottom:1px;}'
        '.em-reset:hover{color:var(--sc-teal,#155752);'
        'border-color:var(--sc-teal,#155752);}'
        # — Parse-confidence strip —
        '.em-parse{display:flex;align-items:center;gap:12px;'
        'flex-wrap:wrap;margin:0 0 12px;}'
        '.em-parse-note{font-family:var(--sc-mono,monospace);'
        'font-size:11px;letter-spacing:.02em;'
        'color:var(--sc-text-dim,#465366);}'
        '.em-parse-note.warn{color:var(--sc-warning,#b8732a);}'
        # — Meta / legend row —
        '.em-metarow{display:flex;gap:14px;align-items:center;'
        'flex-wrap:wrap;margin:0 0 8px;}'
        '.em-toggle{display:inline-flex;align-items:center;gap:6px;'
        'cursor:pointer;font-family:var(--sc-sans,Inter,sans-serif);'
        'font-size:12.5px;color:var(--ink-2,#2b3e54);}'
        '.em-toggle input{accent-color:var(--green-deep,#154e36);}'
        '#emSel{display:none;font-family:var(--sc-mono,monospace);'
        'font-size:11px;font-weight:600;letter-spacing:.04em;'
        'color:var(--green-deep,#154e36);'
        'background:var(--paper-card,#fefcf3);'
        'border:1px solid var(--green-deep,#154e36);border-radius:2px;'
        'padding:3px 10px;}'
        '.em-hint{font-family:var(--sc-mono,monospace);font-size:11px;'
        'letter-spacing:.02em;color:var(--sc-text-dim,#465366);}'
        # — Map card (the SVG keeps its own inline frame so SVG/PNG
        #   exports stay self-contained; the card is the on-page mat) —
        '.em-mapcard{background:var(--paper-card,#fefcf3);'
        'border:1px solid var(--sc-rule,#d6cfc0);border-radius:6px;'
        'padding:14px 14px 10px;}'
        '.em-chart-caption{margin-top:9px;'
        'font-family:var(--sc-mono,monospace);font-size:10px;'
        'letter-spacing:.08em;text-transform:uppercase;'
        'color:var(--sc-text-dim,#5C6878);text-align:center;}'
        '#mapOut{position:relative;'
        "font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);}"
        '#mapOut .em-state{transition:filter .12s,stroke .12s;'
        'cursor:pointer;}'
        '#mapOut .em-state:hover{filter:brightness(.9);'
        'stroke:var(--sc-navy,#0b2341);stroke-width:1.4;}'
        '#mapOut .em-state:focus-visible{outline:none;'
        'stroke:var(--sc-teal,#1F7A75);stroke-width:2;}'
        '#mapOut .em-state.em-selected{stroke:var(--sc-navy,#0b2341);'
        'stroke-width:2.4;}'
        '#emTip{display:none;position:absolute;pointer-events:none;'
        'background:var(--sc-navy,#0b2341);color:#fff;'
        'font-family:var(--sc-sans,Inter,sans-serif);font-size:12px;'
        'padding:5px 10px;border-radius:4px;white-space:nowrap;'
        'z-index:5;box-shadow:0 2px 8px rgba(11,35,65,.25);}'
        # — KPI strip —
        '.em-kpis{margin:16px 0 4px;}'
        '.em-kpi-of{font-size:14px;color:var(--sc-text-faint,#7a8699);'
        'font-weight:400;}'
        # — Values table —
        '.em-tablewrap{max-height:480px;overflow-y:auto;'
        'border:1px solid var(--sc-rule,#d6cfc0);border-radius:4px;'
        'background:var(--paper-card,#fefcf3);margin-top:10px;}'
        '.em-table{border-collapse:collapse;width:100%;font-size:12.5px;'
        'font-family:var(--sc-sans,Inter,sans-serif);}'
        '.em-table thead th{position:sticky;top:0;z-index:1;'
        'background:var(--paper-card,#fefcf3);'
        'font-family:var(--sc-mono,monospace);font-size:9.5px;'
        'font-weight:600;letter-spacing:.08em;text-transform:uppercase;'
        'color:var(--sc-text-dim,#465366);text-align:left;padding:8px;'
        'border-bottom:2px solid var(--sc-rule,#c9c1ac);}'
        '.em-table thead th.num,.em-table td.num{text-align:right;}'
        '.em-table td{padding:4px 8px;'
        'border-bottom:1px solid var(--sc-rule,#d6cfc0);'
        'color:var(--ink,#16263a);}'
        '.em-table tbody tr:nth-child(even){'
        'background:var(--sc-bone,#f2ede3);}'
        '.em-table tbody tr:hover{background:var(--bg,#efeadd);}'
        '.em-td-rank{font-family:var(--sc-mono,monospace);'
        'font-variant-numeric:tabular-nums;'
        'color:var(--sc-text-faint,#7a8699);}'
        '.em-td-val{font-family:var(--sc-mono,monospace);font-weight:600;'
        'font-variant-numeric:tabular-nums;}'
        '.em-swatch{display:inline-block;width:11px;height:11px;'
        'border-radius:2px;border:1px solid var(--sc-rule,#c9c1ac);'
        'margin-right:7px;vertical-align:-1px;}'
        '.em-state-name{color:var(--sc-text-dim,#465366);'
        'font-size:11.5px;}'
        '.em-bar{display:block;width:72px;height:3px;'
        'margin:3px 0 1px auto;border-radius:2px;'
        'background:var(--sc-bone,#f2ede3);overflow:hidden;}'
        '.em-bar-fill{display:block;height:100%;border-radius:2px;}'
        # — Bottom grid + help prose —
        '.em-grid2{display:grid;'
        'grid-template-columns:repeat(auto-fit,minmax(340px,1fr));'
        'gap:28px;margin-top:26px;align-items:start;}'
        '.em-help p{'
        "font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);"
        'font-size:13.5px;line-height:1.65;color:var(--ink,#16263a);'
        'margin:10px 0 0;max-width:64ch;}'
        '.em-help code{font-family:var(--sc-mono,monospace);'
        'font-size:12px;background:var(--sc-bone,#f2ede3);'
        'padding:1px 4px;border-radius:2px;}'
        '.em-help em{color:var(--green-deep,#154e36);}'
        '@media print{.em-form,.em-metarow{display:none;}'
        '#mapOut svg{print-color-adjust:exact;'
        '-webkit-print-color-adjust:exact;}}'
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
        # focus/blur — keyboard parity with the mouse hover readout.
        "p.addEventListener('focus',function(){"
        "tip.textContent=tipText(p);tip.style.display='block';"
        "var r=root.getBoundingClientRect();"
        "var b=p.getBoundingClientRect();"
        "tip.style.left=(b.left-r.left+b.width/2)+'px';"
        "tip.style.top=(b.top-r.top-10)+'px';});"
        "p.addEventListener('blur',function(){"
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
    """Ranked 51-row values table, kit idiom: sticky mono-caps header
    (the wrapper div scrolls, so the header must pin), zebra rows,
    right-aligned mono tabular-nums values, and — per row — the
    gradient swatch plus a proportional micro-bar keyed to the SAME
    gradient, so the column scans without reading every number. The
    two per-row ``style=`` attributes carry the computed gradient
    colour / bar width; everything static lives in ``_map_css_js``."""
    lo, hi = cfg["lo"], cfg["hi"]
    span = (hi - lo) or 1.0
    rows = ""
    ordered = sorted(cfg["values"].items(),
                     key=lambda kv: -(kv[1] if kv[1] is not None else -1))
    for rank, (code, v) in enumerate(ordered, start=1):
        sw = html.escape(gradient_color(
            v, lo, cfg["mid"], hi,
            cfg["c_low"], cfg["c_mid"], cfg["c_high"]))
        if v is None:
            val_txt, pct = "—", 0.0
        else:
            val_txt = _fmt(v)
            pct = max(2.0, min(100.0, (v - lo) / span * 100.0))
        rows += (
            f'<tr><td class="num em-td-rank">{rank}</td>'
            f'<td><span class="em-swatch" style="background:{sw};">'
            f'</span>{html.escape(code)} <span class="em-state-name">'
            f'{html.escape(STATE_NAMES.get(code, ""))}</span></td>'
            f'<td class="num em-td-val">{val_txt}'
            f'<span class="em-bar"><span class="em-bar-fill" '
            f'style="width:{pct:.0f}%;background:{sw};"></span></span>'
            f'</td></tr>')
    return (
        '<table class="em-table"><thead><tr>'
        '<th class="num" scope="col" '
        'title="Rank — highest value first">Rank</th>'
        '<th scope="col">State</th>'
        '<th class="num" scope="col">Value (%)</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>')


def _parse_status(qs: Optional[Dict[str, Any]],
                  cfg: Dict[str, Any]) -> Tuple[str, bool]:
    """Confidence cue for the paste path: how many pasted rows the
    parser recognised, and why the rest were dropped. The silent skip
    in ``parse_values_text`` is deliberate (a stray header row must
    not kill the map) — but the page has to SAY what it skipped, or a
    malformed paste reads as an inexplicably grey map. Returns
    ``(html, zero_parsed)``; ``zero_parsed`` is True when a paste was
    supplied and nothing survived (caller swaps in the empty state)."""
    raw = _qs1(qs, "data", "")
    if not raw.strip():
        return "", False          # defaults path — nothing to report
    supplied = sum(
        1 for ln in raw.replace("\r", "\n").split("\n") if ln.strip())
    parsed = len(cfg["values"])
    if parsed == 0:
        return "", True
    if parsed >= supplied:
        return (
            '<div class="em-parse">'
            + ck_signal_badge(
                f"{parsed} of {supplied} rows recognised", tone="positive")
            + '<span class="em-parse-note">Every pasted row parsed '
              'cleanly.</span></div>', False)
    dropped = supplied - parsed
    noun = "row" if dropped == 1 else "rows"
    return (
        '<div class="em-parse">'
        + ck_signal_badge(
            f"{parsed} of {supplied} rows recognised", tone="warning")
        + f'<span class="em-parse-note warn">{dropped} {noun} dropped '
          '— unrecognised state code, non-numeric value, or duplicate '
          'state (last one wins).</span></div>', False)


def render_excel_mapping_page(qs: "Dict[str, Any] | None" = None) -> str:
    """Render the Excel-mapping choropleth page from the form inputs (or
    the Python defaults)."""
    cfg = resolve_inputs(qs)
    # Page-local unit: the form asks for percentages, so the in-SVG
    # legend says so too. Other _map_svg embeds (infusion, MA
    # penetration) build their own cfg dicts and are unaffected.
    cfg["legend_suffix"] = "%"
    parse_html, zero_parsed = _parse_status(qs, cfg)
    n_vals = len(cfg["values"])
    head = ck_editorial_head(
        "RESEARCH · STATE CHOROPLETH",
        "Excel Mapping",
        meta=(f"{n_vals} OF {len(STATE_NAMES)} JURISDICTIONS · "
              f"DOMAIN {_fmt(cfg['lo'])}–{_fmt(cfg['hi'])} · "
              "CONFIG LIVES IN THE URL"),
        lede_italic_phrase="Paste a column from Excel,",
        lede_body=(
            "pick three gradient stops, and the page colours real "
            "Census geography by interpolating low → mid → high. "
            "Every setting — colours, domain, title, data — lives in "
            "the URL, so the finished map travels as a link and "
            "exports straight into a deck."),
        source_note=("User-supplied values · the defaults are "
                     "illustrative placeholders"),
        actions_html=ck_copy_share_link_button() + ck_print_view_button(),
        show_legend=False,
    )
    if zero_parsed:
        # A paste was supplied but no row parsed: an all-grey map with
        # a blank stats row explains nothing — say what happened and
        # how to fix it instead.
        map_block = ck_empty_state(
            "No rows parsed from that paste.",
            body=("Accepted formats, one state per line: 'TX 61', "
                  "'TX,61', a tab-separated Excel column, or full "
                  "names like 'Texas 61'. A trailing % is fine."),
            eyebrow="NO ROWS PARSED",
            cta_label="Reset to defaults",
            cta_href="/excel-mapping",
            icon="▦",
            tone="warning",
        )
        stats_block = ""
        table_section = ""
    else:
        map_block = (
            '<div class="em-metarow">'
            '<label class="em-toggle">'
            '<input type="checkbox" id="emLabelsToggle" checked>'
            'Show labels</label>'
            '<span id="emSel"></span>'
            '<span class="em-hint">Hover a state for detail · click '
            'to pin</span></div>'
            f'<div class="em-mapcard"><div id="mapOut">{_map_svg(cfg)}'
            '<div id="emTip"></div></div>'
            '<div class="em-chart-caption">US choropleth · Albers '
            'projection · Census state boundaries · values as supplied'
            '</div></div>'
            + chart_export_toolbar("mapOut", "state-map"))
        stats_block = _stats(cfg)
        table_section = (
            '<section>'
            + ck_section_header(
                "Every state, ranked",
                eyebrow="VALUES BY STATE", count=n_vals)
            + f'<div class="em-tablewrap">{_data_table(cfg)}</div>'
            + '</section>')
    help_section = (
        '<section>'
        + ck_section_header(
            "Drive it from a paste — or a URL", eyebrow="HOW TO USE")
        + '<div class="em-help">'
        # Admin note: the map can also be driven from Python by editing
        # DEFAULT_STATE_VALUES and the three DEFAULT_*_COLOR constants
        # in excel_mapping_page.py.
          '<p><strong>In the page:</strong> pick '
          'the three colours, optionally set the low/mid/high value '
          'domain (blank = auto from your data) and a map title, and '
          'paste <code>STATE&nbsp;VALUE</code> rows from Excel. The '
          'gradient interpolates low → mid → high; each state prints '
          'its value in <em>black serif text</em> on the shape.</p>'
          '<p><strong>Geography:</strong> real US '
          'Census state boundaries (Albers projection, public domain). '
          'Alaska and Hawaii are bottom-left insets, Puerto Rico a '
          'bottom-right inset; the nine small Northeast jurisdictions '
          '(VT NH MA RI CT NJ DE MD DC) are labelled in the swatch '
          'column beside the Atlantic coast because their shapes are '
          'too small to hold text.</p>'
          '<p><strong>Export:</strong> the '
          'SVG/PNG downloads include the legend and title, so the file '
          'drops straight into a deck — and the URL captures this '
          'exact map, so copying the link shares it.</p></div>'
        + '</section>')
    body = (
        head
        + '<div class="em-wrap">'
        + _form(cfg)
        + parse_html
        + map_block
        + _map_css_js()
        + stats_block
        + f'<div class="em-grid2">{table_section}{help_section}</div>'
        + '</div>')
    return chartis_shell(
        body, "Excel Mapping", active_nav="/research",
        subtitle="State choropleth utility")
