"""Editorial chart kit — reusable inline-SVG charts + one-click PNG export.

Server-rendered SVG (no JS charting library, no new runtime deps) styled to
match the Command Center / HCRIS X-Ray editorial look. Used by the geographic
analysis surfaces (State Comparison, State Profile, County Explorer) to turn
dense side-by-side tables into the "easy visuals" partners expect.

Why a dedicated module (not more lines in _chartis_kit): the chart vocabulary
is self-contained and reused across several pages, and it carries one design
constraint that the rest of the kit doesn't — every chart must rasterize to
PNG from a detached clone, so the SVG uses **resolved hex colors and concrete
font stacks** (never bare CSS custom properties, which don't cascade into a
serialized <img>). ck_chart_assets() ships the one-time CSS + the vanilla-JS
SVG→canvas→PNG download helper (event-delegated, idempotent).

Public API:
    ck_bar_chart(title, items, ...)                  vertical categorical bars
    ck_grouped_bar(title, categories, groups, ...)   multi-series bars + legend
    ck_diverging_bar(title, items, ...)              value-vs-reference Δ bars
    ck_chart_card(title, svg, ...)                   editorial frame + Export PNG
    ck_chart_assets()                                <style>+<script>, once/page
"""
from __future__ import annotations

import html as _html
import re as _re
from typing import Callable, List, Optional, Sequence, Tuple

from ._chartis_kit import P

# ── Resolved editorial palette (hex, so PNG export is self-contained) ──
_INK = P.get("text", "#1a2332")
_DIM = P.get("text_dim", "#5b6b7a")
_FAINT = P.get("text_faint", "#7a8699")
_RULE = P.get("border", "#d6cfc0")
_PANEL = P.get("panel", "#ffffff")
_TEAL = P.get("accent", "#155752")
_POS = P.get("positive", "#0a8a5f")
_WARN = P.get("warning", "#b8732a")
_NEG = P.get("negative", "#b5321e")
_NAVY = P.get("navy", "#0b2341")

_SERIF = "Source Serif 4, Georgia, serif"
_MONO = "JetBrains Mono, ui-monospace, monospace"

# Editorial series colors, cycled for grouped charts. Teal-first so a single
# series reads as the platform accent; the rest stay desaturated/print-safe.
_SERIES = [_TEAL, _NAVY, _WARN, _POS, _NEG, _FAINT]

_TONE = {
    "teal": _TEAL, "positive": _POS, "warning": _WARN,
    "negative": _NEG, "navy": _NAVY, "muted": _FAINT,
}


def _tone_hex(tone: Optional[str]) -> str:
    return _TONE.get(tone or "teal", _TEAL)


def _compact(v: float) -> str:
    """Axis/value tick formatter — compact, partner-readable."""
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:.1f}B"
    if a >= 1e6:
        return f"{v / 1e6:.1f}M"
    if a >= 1e3:
        return f"{v / 1e3:.1f}K"
    if a >= 100:
        return f"{v:,.0f}"
    if a >= 1:
        return f"{v:.1f}"
    return f"{v:.2f}"


def _slug(s: str) -> str:
    return _re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "chart"


def _coerce(items: Sequence, want_tone: bool) -> List[Tuple]:
    """Normalize (label, value[, tone]) tuples, dropping non-finite values."""
    out: List[Tuple] = []
    for it in items:
        try:
            val = float(it[1])
        except (TypeError, ValueError, IndexError):
            continue
        if val != val:  # NaN
            continue
        label = str(it[0]) if it[0] is not None else ""
        if want_tone:
            tone = it[2] if len(it) > 2 and it[2] else "teal"
            out.append((label, val, tone))
        else:
            out.append((label, val))
    return out


# ──────────────────────────────────────────────────────────────────────────
# Charts
# ──────────────────────────────────────────────────────────────────────────

def ck_bar_chart(
    title: str,
    items: Sequence,
    *,
    value_fmt: Optional[Callable[[float], str]] = None,
    reference: Optional[Tuple[str, float]] = None,
    source: str = "",
    subtitle: str = "",
    height: int = 230,
    chart_id: Optional[str] = None,
) -> str:
    """Vertical categorical bar chart, wrapped in an editorial export card.

    ``items``: ``(label, value, tone)`` tuples (tone ∈ teal/positive/warning/
    negative/navy/muted). ``reference``: optional ``(label, value)`` drawn as
    a dashed horizontal line — the US-median benchmark on the geo pages. Values
    are assumed non-negative (state metrics); a negative slips to width 0.
    Returns '' when no finite item exists so the caller can fall back to the
    table alone. ``value_fmt`` formats the on-bar value (defaults to compact)."""
    pts = _coerce(items, want_tone=True)
    if not pts:
        return ""
    fmt = value_fmt or _compact
    W, H = 520.0, float(height)
    L, R, T, B = 12.0, 12.0, 30.0, 42.0
    plotw = W - L - R
    ploth = H - T - B
    vals = [v for _, v, _ in pts]
    ref_v = None
    if reference is not None:
        try:
            ref_v = float(reference[1])
        except (TypeError, ValueError):
            ref_v = None
    top = max(vals + ([ref_v] if ref_v is not None else []))
    if top <= 0:
        top = 1.0
    n = len(pts)
    band = plotw / n
    bw = min(64.0, band * 0.62)

    def bar_h(v: float) -> float:
        return max(0.0, v) / top * ploth

    parts = [
        f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
        f'style="max-width:560px;display:block" preserveAspectRatio="xMidYMid meet" '
        f'role="img" aria-label="{_html.escape(title)}">',
        f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="{_PANEL}"/>',
        # baseline
        f'<line x1="{L:.1f}" y1="{T + ploth:.1f}" x2="{W - R:.1f}" '
        f'y2="{T + ploth:.1f}" stroke="{_RULE}" stroke-width="1"/>',
    ]
    for i, (label, val, tone) in enumerate(pts):
        cx = L + band * i + band / 2.0
        bh = bar_h(val)
        by = T + ploth - bh
        bx = cx - bw / 2.0
        color = _tone_hex(tone)
        parts.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
            f'rx="1.5" fill="{color}"><title>{_html.escape(label)}: '
            f'{_html.escape(fmt(val))}</title></rect>'
        )
        # value on top
        parts.append(
            f'<text x="{cx:.1f}" y="{by - 6:.1f}" text-anchor="middle" '
            f'font-family="{_MONO}" font-size="10.5" font-weight="600" '
            f'fill="{_INK}">{_html.escape(fmt(val))}</text>'
        )
        # category label below baseline
        parts.append(
            f'<text x="{cx:.1f}" y="{T + ploth + 16:.1f}" text-anchor="middle" '
            f'font-family="{_MONO}" font-size="11" fill="{_DIM}">'
            f'{_html.escape(label[:14])}</text>'
        )
    # reference line (US median)
    if ref_v is not None and ref_v > 0:
        ry = T + ploth - bar_h(ref_v)
        ref_label = str(reference[0]) if reference and reference[0] else "ref"
        parts.append(
            f'<line x1="{L:.1f}" y1="{ry:.1f}" x2="{W - R:.1f}" y2="{ry:.1f}" '
            f'stroke="{_FAINT}" stroke-width="1" stroke-dasharray="4 3"/>'
        )
        parts.append(
            f'<text x="{W - R:.1f}" y="{ry - 4:.1f}" text-anchor="end" '
            f'font-family="{_MONO}" font-size="8.5" fill="{_FAINT}">'
            f'{_html.escape(ref_label)} {_html.escape(fmt(ref_v))}</text>'
        )
    parts.append("</svg>")
    return ck_chart_card(
        title, "".join(parts), source=source, subtitle=subtitle,
        chart_id=chart_id,
    )


def ck_hbar_chart(
    title: str,
    items: Sequence,
    *,
    value_fmt: Optional[Callable[[float], str]] = None,
    reference: Optional[Tuple[str, float]] = None,
    source: str = "",
    subtitle: str = "",
    chart_id: Optional[str] = None,
    label_w: float = 150.0,
) -> str:
    """Horizontal ranked bar chart — label on the left, bar extending right,
    value at the bar end. The right shape for many rows with long labels
    (county rankings, screener results) where vertical bars would collide.
    ``items``: ``(label, value, tone)``. ``reference``: optional ``(label,
    value)`` dashed vertical line (e.g. a state weighted-mean). '' if empty."""
    pts = _coerce(items, want_tone=True)
    if not pts:
        return ""
    fmt = value_fmt or _compact
    rowh = 21.0
    W = 560.0
    L, R, T, B = label_w, 56.0, 14.0, 14.0
    H = T + B + rowh * len(pts)
    plotw = W - L - R
    vals = [v for _, v, _ in pts]
    ref_v = None
    if reference is not None:
        try:
            ref_v = float(reference[1])
        except (TypeError, ValueError):
            ref_v = None
    top = max(vals + ([ref_v] if ref_v is not None else []) + [0.0]) or 1.0

    parts = [
        f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
        f'style="max-width:600px;display:block" preserveAspectRatio="xMidYMid meet" '
        f'role="img" aria-label="{_html.escape(title)}">',
        f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="{_PANEL}"/>',
    ]
    for i, (label, val, tone) in enumerate(pts):
        cy = T + rowh * i + rowh / 2.0
        w = max(0.0, val) / top * plotw
        color = _tone_hex(tone)
        parts.append(
            f'<rect x="{L:.1f}" y="{cy - 7:.1f}" width="{max(1.0, w):.1f}" height="14" '
            f'rx="1.5" fill="{color}"><title>{_html.escape(label)}: '
            f'{_html.escape(fmt(val))}</title></rect>'
        )
        parts.append(
            f'<text x="{L - 7:.1f}" y="{cy + 3.5:.1f}" text-anchor="end" '
            f'font-family="{_MONO}" font-size="10.5" fill="{_DIM}">'
            f'{_html.escape(label[:22])}</text>'
        )
        parts.append(
            f'<text x="{L + w + 5:.1f}" y="{cy + 3.5:.1f}" font-family="{_MONO}" '
            f'font-size="9.5" font-weight="600" fill="{_INK}">'
            f'{_html.escape(fmt(val))}</text>'
        )
    if ref_v is not None and ref_v > 0:
        rx = L + ref_v / top * plotw
        ref_label = str(reference[0]) if reference and reference[0] else "ref"
        parts.append(
            f'<line x1="{rx:.1f}" y1="{T - 2:.1f}" x2="{rx:.1f}" y2="{H - B + 2:.1f}" '
            f'stroke="{_FAINT}" stroke-width="1" stroke-dasharray="4 3"/>'
        )
        parts.append(
            f'<text x="{rx:.1f}" y="{T - 4:.1f}" text-anchor="middle" '
            f'font-family="{_MONO}" font-size="8" fill="{_FAINT}">'
            f'{_html.escape(ref_label)}</text>'
        )
    parts.append("</svg>")
    return ck_chart_card(
        title, "".join(parts), source=source, subtitle=subtitle, chart_id=chart_id,
    )


def ck_grouped_bar(
    title: str,
    categories: Sequence[str],
    groups: Sequence[Tuple[str, Sequence[float], Optional[str]]],
    *,
    value_fmt: Optional[Callable[[float], str]] = None,
    source: str = "",
    subtitle: str = "",
    height: int = 260,
    chart_id: Optional[str] = None,
) -> str:
    """Multi-series grouped vertical bars + legend, in an export card.

    ``categories``: x-axis labels (e.g. metric names, or states). ``groups``:
    list of ``(series_name, values, color_or_None)`` where ``values`` aligns
    to ``categories`` (None/NaN cells are skipped). Use to compare several
    states across one normalized axis, or several metrics across states.
    Returns '' when nothing finite is present."""
    cats = [str(c) for c in categories]
    if not cats or not groups:
        return ""
    fmt = value_fmt or _compact
    series: List[Tuple[str, List[Optional[float]], str]] = []
    for gi, g in enumerate(groups):
        name = str(g[0])
        raw = list(g[1])
        color = g[2] if len(g) > 2 and g[2] else _SERIES[gi % len(_SERIES)]
        vals: List[Optional[float]] = []
        for j in range(len(cats)):
            try:
                v = float(raw[j]) if j < len(raw) and raw[j] is not None else None
            except (TypeError, ValueError):
                v = None
            if v is not None and v != v:
                v = None
            vals.append(v)
        series.append((name, vals, color))
    finite = [v for _, vals, _ in series for v in vals if v is not None]
    if not finite:
        return ""
    top = max(finite + [0.0]) or 1.0

    W, H = 560.0, float(height)
    L, R, T, B = 12.0, 12.0, 40.0, 46.0
    plotw = W - L - R
    ploth = H - T - B
    nc = len(cats)
    ng = len(series)
    band = plotw / nc
    inner = band * 0.78
    bw = inner / max(1, ng)

    def bar_h(v: float) -> float:
        return max(0.0, v) / top * ploth

    parts = [
        f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
        f'style="max-width:620px;display:block" preserveAspectRatio="xMidYMid meet" '
        f'role="img" aria-label="{_html.escape(title)}">',
        f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="{_PANEL}"/>',
        f'<line x1="{L:.1f}" y1="{T + ploth:.1f}" x2="{W - R:.1f}" '
        f'y2="{T + ploth:.1f}" stroke="{_RULE}" stroke-width="1"/>',
    ]
    for ci, cat in enumerate(cats):
        cx0 = L + band * ci + (band - inner) / 2.0
        for si, (name, vals, color) in enumerate(series):
            v = vals[ci]
            if v is None:
                continue
            bx = cx0 + bw * si
            bh = bar_h(v)
            by = T + ploth - bh
            parts.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{max(1.5, bw - 1.5):.1f}" '
                f'height="{bh:.1f}" rx="1" fill="{color}"><title>{_html.escape(name)} · '
                f'{_html.escape(cat)}: {_html.escape(fmt(v))}</title></rect>'
            )
        parts.append(
            f'<text x="{L + band * ci + band / 2.0:.1f}" y="{T + ploth + 16:.1f}" '
            f'text-anchor="middle" font-family="{_MONO}" font-size="10.5" '
            f'fill="{_DIM}">{_html.escape(cat[:12])}</text>'
        )
    # legend (top)
    lx = L
    for name, _vals, color in series:
        parts.append(
            f'<rect x="{lx:.1f}" y="14" width="9" height="9" rx="1.5" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{lx + 13:.1f}" y="22" font-family="{_MONO}" font-size="10" '
            f'fill="{_DIM}">{_html.escape(name[:16])}</text>'
        )
        lx += 22 + min(16, len(name)) * 6.2
    parts.append("</svg>")
    return ck_chart_card(
        title, "".join(parts), source=source, subtitle=subtitle,
        chart_id=chart_id,
    )


def ck_diverging_bar(
    title: str,
    items: Sequence,
    *,
    value_fmt: Optional[Callable[[float], str]] = None,
    source: str = "",
    subtitle: str = "",
    height: int = 260,
    chart_id: Optional[str] = None,
    center_label: str = "U.S. median",
) -> str:
    """Horizontal diverging bars around a zero center — each item's signed
    gap vs a benchmark. ``items``: ``(label, delta, tone)`` where ``delta`` is
    the signed value (e.g. % above/below the US median). Positive bars extend
    right, negative left; tone overrides the default green/amber by sign.
    Ideal for a single state's metric profile vs the national median."""
    pts = _coerce(items, want_tone=True)
    if not pts:
        return ""
    fmt = value_fmt or (lambda v: f"{v:+.0f}%")
    mag = max((abs(v) for _, v, _ in pts), default=0.0) or 1.0
    rowh = 22.0
    W = 560.0
    L, R, T, B = 150.0, 64.0, 16.0, 16.0
    H = max(float(height), T + B + rowh * len(pts))
    midx = L + (W - L - R) / 2.0
    halfw = (W - L - R) / 2.0

    parts = [
        f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
        f'style="max-width:600px;display:block" preserveAspectRatio="xMidYMid meet" '
        f'role="img" aria-label="{_html.escape(title)}">',
        f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="{_PANEL}"/>',
        # center line
        f'<line x1="{midx:.1f}" y1="{T:.1f}" x2="{midx:.1f}" y2="{H - B:.1f}" '
        f'stroke="{_RULE}" stroke-width="1"/>',
        f'<text x="{midx:.1f}" y="{H - 3:.1f}" text-anchor="middle" '
        f'font-family="{_MONO}" font-size="8.5" fill="{_FAINT}">'
        f'{_html.escape(center_label)}</text>',
    ]
    for i, (label, val, tone) in enumerate(pts):
        cy = T + rowh * i + rowh / 2.0
        w = abs(val) / mag * (halfw - 6)
        if tone in _TONE and tone != "teal":
            color = _tone_hex(tone)
        else:
            color = _POS if val >= 0 else _WARN
        if val >= 0:
            bx = midx
        else:
            bx = midx - w
        parts.append(
            f'<rect x="{bx:.1f}" y="{cy - 7:.1f}" width="{max(1.0, w):.1f}" '
            f'height="14" rx="1.5" fill="{color}"><title>{_html.escape(label)}: '
            f'{_html.escape(fmt(val))}</title></rect>'
        )
        parts.append(
            f'<text x="{L - 8:.1f}" y="{cy + 3.5:.1f}" text-anchor="end" '
            f'font-family="{_MONO}" font-size="10.5" fill="{_DIM}">'
            f'{_html.escape(label[:22])}</text>'
        )
        vx = (bx + w + 5) if val >= 0 else (bx - 5)
        anchor = "start" if val >= 0 else "end"
        parts.append(
            f'<text x="{vx:.1f}" y="{cy + 3.5:.1f}" text-anchor="{anchor}" '
            f'font-family="{_MONO}" font-size="9.5" font-weight="600" '
            f'fill="{_INK}">{_html.escape(fmt(val))}</text>'
        )
    parts.append("</svg>")
    return ck_chart_card(
        title, "".join(parts), source=source, subtitle=subtitle,
        chart_id=chart_id,
    )


# ──────────────────────────────────────────────────────────────────────────
# Card frame + PNG export assets
# ──────────────────────────────────────────────────────────────────────────

def ck_chart_card(
    title: str,
    svg: str,
    *,
    source: str = "",
    subtitle: str = "",
    chart_id: Optional[str] = None,
    note: str = "",
) -> str:
    """Editorial frame around a chart SVG: kicker title, optional subtitle,
    an Export-PNG button, the SVG, and an optional source/footnote line.
    ``chart_id`` is the DOM id the export helper targets (auto-derived from
    the title when omitted)."""
    cid = chart_id or ("ckc-" + _slug(title))
    sub = (
        f'<div class="ck-chart-sub">{_html.escape(subtitle)}</div>'
        if subtitle else ""
    )
    src = (
        f'<div class="ck-chart-src">{_html.escape(source)}</div>'
        if source else ""
    )
    ftn = (
        f'<div class="ck-chart-note">{_html.escape(note)}</div>'
        if note else ""
    )
    return (
        f'<figure class="ck-chart-card">'
        f'<div class="ck-chart-head">'
        f'<div><div class="ck-chart-title">{_html.escape(title)}</div>{sub}</div>'
        f'<button type="button" class="ck-chart-dl" data-chart-id="{_html.escape(cid)}" '
        f'data-chart-name="{_html.escape(_slug(title))}" '
        f'aria-label="Export {_html.escape(title)} as PNG">Export PNG</button>'
        f'</div>'
        f'<div class="ck-chart-svg" id="{_html.escape(cid)}">{svg}</div>'
        f'{src}{ftn}'
        f'</figure>'
    )


def ck_chart_grid(*cards: str) -> str:
    """Responsive grid wrapper for a set of chart cards. Empty cards
    (the '' fall-back) are dropped so a missing-data chart leaves no hole."""
    inner = "".join(c for c in cards if c)
    if not inner:
        return ""
    return f'<div class="ck-chart-grid">{inner}</div>'


_ASSETS = """<style>
.ck-chart-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
gap:16px;margin:6px 0 20px;}
.ck-chart-card{margin:0;padding:14px 16px 12px;background:""" + _PANEL + """;
border:1px solid """ + _RULE + """;border-radius:4px;}
.ck-chart-head{display:flex;align-items:flex-start;justify-content:space-between;
gap:10px;margin-bottom:8px;}
.ck-chart-title{font-family:""" + _SERIF + """;font-size:15px;font-weight:600;
color:""" + _INK + """;line-height:1.2;}
.ck-chart-sub{font-family:""" + _MONO + """;font-size:9.5px;letter-spacing:.04em;
text-transform:uppercase;color:""" + _FAINT + """;margin-top:3px;}
.ck-chart-dl{flex-shrink:0;font-family:""" + _MONO + """;font-size:9.5px;
letter-spacing:.04em;text-transform:uppercase;color:""" + _TEAL + """;
background:transparent;border:1px solid """ + _RULE + """;border-radius:3px;
padding:3px 9px;cursor:pointer;transition:background 90ms,color 90ms;white-space:nowrap;}
.ck-chart-dl:hover{background:""" + _TEAL + """;color:#fff;border-color:""" + _TEAL + """;}
.ck-chart-src{font-family:""" + _MONO + """;font-size:9px;color:""" + _FAINT + """;
margin-top:7px;}
.ck-chart-note{font-size:11px;color:""" + _DIM + """;margin-top:6px;line-height:1.5;}
@media (max-width:640px){.ck-chart-grid{grid-template-columns:1fr;}}
</style>
<script>
(function(){
  if (window.__ckChartDL) return; window.__ckChartDL = true;
  document.addEventListener('click', function(e){
    var btn = e.target.closest ? e.target.closest('.ck-chart-dl') : null;
    if(!btn) return;
    var wrap = document.getElementById(btn.getAttribute('data-chart-id'));
    var svg = wrap ? wrap.querySelector('svg') : null;
    if(!svg){ return; }
    var name = (btn.getAttribute('data-chart-name')||'chart') + '.png';
    var vb = (svg.getAttribute('viewBox')||'0 0 560 240').split(/\\s+/);
    var w = parseFloat(vb[2])||560, h = parseFloat(vb[3])||240;
    var clone = svg.cloneNode(true);
    clone.setAttribute('width', w); clone.setAttribute('height', h);
    clone.setAttribute('xmlns','http://www.w3.org/2000/svg');
    var xml = new XMLSerializer().serializeToString(clone);
    var url = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(xml)));
    var img = new Image();
    img.onload = function(){
      var s = 2, c = document.createElement('canvas');
      c.width = w*s; c.height = h*s;
      var ctx = c.getContext('2d');
      ctx.fillStyle = '#ffffff'; ctx.fillRect(0,0,c.width,c.height);
      ctx.scale(s,s); ctx.drawImage(img,0,0);
      c.toBlob(function(blob){
        if(!blob) return;
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = name;
        document.body.appendChild(a); a.click();
        setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 1500);
      }, 'image/png');
    };
    img.onerror = function(){ /* silent — table is still on the page */ };
    img.src = url;
  });
})();
</script>"""


def ck_chart_assets() -> str:
    """One-time <style> + <script> bundle for the chart kit: card styling and
    the event-delegated SVG→canvas→PNG download helper. Safe to include more
    than once per page (the JS self-guards via window.__ckChartDL), but call
    it once per render to keep the payload lean."""
    return _ASSETS
