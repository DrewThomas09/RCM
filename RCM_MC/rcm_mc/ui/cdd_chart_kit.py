"""CDD chart kit — the charts consultants build in Excel, rendered as
clean, centered, Chartis-styled SVG from a simple pasted table.

One ``render_cdd_chart(chart_type, table, opts)`` entry dispatches to the
common commercial-due-diligence chart family: column (grouped / stacked /
100%), horizontal bar, line, stacked area, waterfall (bridge), pie,
donut, scatter / bubble, marimekko, and combo (bar + line). Every chart
shares one frame — centered serif title, Chartis palette, gridlines,
value labels, centered legend — so they all look like they came from the
same deck.

The data model is whatever ``parse_table`` returns from an Excel paste:
a header row (category-axis name + one name per series) and rows of
``(label, [values])``. Each chart interprets that table the way it needs.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

# ── Chartis palettes ─────────────────────────────────────────────────
_NAVY = "#0b2341"
_INK = "#1a2332"
_DIM = "#465366"
_FAINT = "#7a8699"
_GRID = "#e4ddca"

PALETTES: Dict[str, List[str]] = {
    "Chartis": ["#0b2341", "#1F7A75", "#b8732a", "#6e5b9e", "#0a8a5f",
                "#b5321e", "#3d6e8f", "#b8943f", "#557a5a", "#9c6b8e"],
    "Navy–Teal": ["#0b2341", "#155752", "#1F7A75", "#3d6e8f", "#5a9e96",
                  "#8bbab4", "#b8943f", "#6e5b9e", "#7a8699", "#b5321e"],
    "Sequential teal": ["#d6e8e6", "#a9d2ce", "#7bbcb5", "#4ea69d",
                        "#1F7A75", "#155752", "#0e3f3b", "#0b2341",
                        "#3d6e8f", "#6e5b9e"],
    "Diverging": ["#b5321e", "#cf7a4e", "#e0b48a", "#ece5d6", "#9bc1bc",
                  "#4ea69d", "#1F7A75", "#155752", "#0b2341", "#6e5b9e"],
}
_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")
_SANS = "'Inter Tight', system-ui, sans-serif"

CHART_TYPES = [
    ("column", "Column (grouped)"),
    ("column_stacked", "Stacked column"),
    ("column_100", "100% stacked column"),
    ("bar", "Horizontal bar"),
    ("line", "Line"),
    ("area", "Stacked area"),
    ("waterfall", "Waterfall (bridge)"),
    ("pie", "Pie"),
    ("donut", "Donut"),
    ("funnel", "Funnel"),
    ("tornado", "Tornado (sensitivity)"),
    ("scatter", "Scatter"),
    ("bubble", "Bubble"),
    ("matrix", "2×2 matrix"),
    ("radar", "Radar (spider)"),
    ("bullet", "Bullet (vs target)"),
    ("dot", "Dot / lollipop"),
    ("gauge", "Gauge (KPI)"),
    ("heatmap", "Heatmap grid"),
    ("marimekko", "Marimekko"),
    ("combo", "Combo (bars + line)"),
]

_W, _H = 720.0, 450.0
_M = {"top": 60.0, "right": 28.0, "bottom": 76.0, "left": 60.0}


# ── Presentation-grade pie / donut (per-slice colours, no table) ─────

def presentable_pie(
    slices: List[Dict[str, Any]],
    opts: "Dict[str, Any] | None" = None,
) -> str:
    """A polished, client-ready pie/donut from explicit slices.

    ``slices`` is a list of ``{"label", "value", "color"}`` (colour
    optional — falls back to the Chartis palette by index). ``opts``:
    title, subtitle, donut (bool), label_mode ('percent'|'value'|'both'|
    'none'), value_suffix, hole_total (donut centre text). Pie on the
    left, a swatch/label/value/% legend on the right, both centred in a
    760×470 frame — built for a slide, not a dashboard."""
    import math
    opts = dict(opts or {})
    pal = PALETTES.get(opts.get("palette", "Chartis"), PALETTES["Chartis"])
    clean = [s for s in slices
             if s.get("value") not in (None, "")
             and (s.get("value") or 0) > 0]
    W, H = 760.0, 470.0
    title = opts.get("title", "")
    sub = opts.get("subtitle", "")
    donut = opts.get("donut", False)
    mode = opts.get("label_mode", "percent")
    suffix = opts.get("value_suffix", "")
    out = [_svg_open(W, H, opts, title or "pie chart",
                     f"font-family:{_SANS};")]
    if title:
        out.append(f'<text x="{W/2:.0f}" y="34" text-anchor="middle" '
                   f'font-family="{_SERIF}" font-size="20" font-weight="700" '
                   f'fill="{_NAVY}">{_esc(title)}</text>')
    if sub:
        out.append(f'<text x="{W/2:.0f}" y="54" text-anchor="middle" '
                   f'font-size="12" fill="{_FAINT}">{_esc(sub)}</text>')
    if not clean:
        out.append(f'<text x="{W/2:.0f}" y="{H/2:.0f}" text-anchor="middle" '
                   f'font-size="13" fill="{_FAINT}">Enter slice values to '
                   f'render the pie</text></svg>')
        return "".join(out)

    total = sum(s["value"] for s in clean) or 1
    cx, cy, R = 232.0, 268.0, 150.0
    ang = -math.pi / 2
    legend_y = max(96.0, cy - len(clean) * 13)
    for i, s in enumerate(clean):
        v = s["value"]
        frac = v / total
        color = s.get("color") or pal[i % len(pal)]
        a2 = ang + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x1p, y1p = cx + R * math.cos(ang), cy + R * math.sin(ang)
        x2p, y2p = cx + R * math.cos(a2), cy + R * math.sin(a2)
        if frac >= 0.9999:
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" '
                       f'fill="{color}" stroke="#fff" stroke-width="2"/>')
        else:
            out.append(
                f'<path d="M {cx:.1f} {cy:.1f} L {x1p:.1f} {y1p:.1f} '
                f'A {R:.1f} {R:.1f} 0 {large} 1 {x2p:.1f} {y2p:.1f} Z" '
                f'fill="{color}" stroke="#fff" stroke-width="2"/>')
        # On-slice label for big-enough slices.
        if mode != "none" and frac >= 0.05:
            mid = (ang + a2) / 2
            lr = R * (0.62 if not donut else 0.78)
            lx, ly = cx + lr * math.cos(mid), cy + lr * math.sin(mid)
            txt = (f'{frac*100:.0f}%' if mode == "percent" else
                   _fmt(v, suffix) if mode == "value" else
                   f'{_fmt(v, suffix)} · {frac*100:.0f}%')
            out.append(
                f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="middle" '
                f'font-size="12.5" font-weight="700" fill="#fff" '
                f'style="paint-order:stroke;stroke:rgba(0,0,0,0.18);'
                f'stroke-width:2px;">{_esc(txt)}</text>')
        ang = a2
    if donut:
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R*0.58:.1f}" '
                   f'fill="#fff"/>')
        ht = opts.get("hole_total")
        if ht:
            out.append(f'<text x="{cx:.1f}" y="{cy-2:.1f}" '
                       f'text-anchor="middle" font-family="{_SERIF}" '
                       f'font-size="22" font-weight="700" fill="{_NAVY}">'
                       f'{_esc(ht)}</text>')
        elif ht is None:
            out.append(f'<text x="{cx:.1f}" y="{cy-4:.1f}" '
                       f'text-anchor="middle" font-family="{_SERIF}" '
                       f'font-size="20" font-weight="700" fill="{_NAVY}">'
                       f'{_fmt(total, suffix)}</text>'
                       f'<text x="{cx:.1f}" y="{cy+13:.1f}" '
                       f'text-anchor="middle" font-size="10" '
                       f'fill="{_FAINT}">TOTAL</text>')
    # Legend — swatch · label · value · %.
    lx0 = 452.0
    ly = legend_y
    for i, s in enumerate(clean):
        v = s["value"]
        frac = v / total
        color = s.get("color") or pal[i % len(pal)]
        out.append(
            f'<rect x="{lx0:.0f}" y="{ly-9:.0f}" width="12" height="12" '
            f'rx="2.5" fill="{color}"/>'
            f'<text x="{lx0+19:.0f}" y="{ly:.0f}" font-size="12.5" '
            f'fill="{_INK}">{_esc(s.get("label") or f"Slice {i+1}")}</text>'
            f'<text x="{W-30:.0f}" y="{ly:.0f}" text-anchor="end" '
            f'font-size="12.5" font-weight="700" fill="{_DIM}" '
            f'font-family="{_SERIF}">{_fmt(v, suffix)} '
            f'<tspan fill="{_FAINT}" font-weight="400">'
            f'({frac*100:.0f}%)</tspan></text>')
        ly += 26
    note = opts.get("footnote") or opts.get("source")
    if note:
        out.append(f'<text x="16" y="{H-12:.1f}" font-family="{_SANS}" '
                   f'font-size="10" fill="{_FAINT}">{_esc(note)}</text>')
    out.append("</svg>")
    return "".join(out)


# ── Parsing ──────────────────────────────────────────────────────────

def parse_table(text: str) -> Dict[str, Any]:
    """Parse a pasted Excel table — first row = headers (category name +
    series names), each later row = label + numeric cells. Tab, comma,
    or 2+-space separated. Non-numeric cells become ``None``."""
    lines = [ln for ln in (text or "").replace("\r", "\n").split("\n")
             if ln.strip()]
    if not lines:
        return {"headers": [], "rows": []}

    def _split(ln: str) -> List[str]:
        if "\t" in ln:
            return [c.strip() for c in ln.split("\t")]
        if "," in ln:
            return [c.strip() for c in ln.split(",")]
        import re
        return [c.strip() for c in re.split(r"\s{2,}", ln.strip())] \
            if re.search(r"\s{2,}", ln) else ln.split()

    headers = _split(lines[0])
    rows: List[Tuple[str, List[Optional[float]]]] = []
    for ln in lines[1:]:
        cells = _split(ln)
        if not cells:
            continue
        label = cells[0]
        vals: List[Optional[float]] = []
        for c in cells[1:]:
            c2 = c.replace("%", "").replace("$", "").replace(",", "").strip()
            try:
                vals.append(float(c2))
            except ValueError:
                vals.append(None)
        rows.append((label, vals))
    return {"headers": headers, "rows": rows}


def _series(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Column-major series from the table: one per non-label header."""
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    n = max((len(v) for _, v in rows), default=0)
    out = []
    for i in range(n):
        name = headers[i + 1] if i + 1 < len(headers) else f"Series {i+1}"
        out.append({"name": name,
                    "values": [(v[i] if i < len(v) else None)
                               for _, v in rows]})
    return out


# ── Shared frame ─────────────────────────────────────────────────────

def _esc(s: Any) -> str:
    return html.escape(str(s))


def _svg_open(W: float, H: float, opts: Dict[str, Any], aria: str,
              extra_style: str = "") -> str:
    """Open an <svg> sized by ``width_px`` (default = the viewBox width),
    scaling proportionally to the container — the size control. Height is
    auto from the viewBox aspect so charts never distort."""
    wpx = opts.get("width_px") or W
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
            f'preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{_esc(aria)}" '
            f'style="max-width:{wpx:.0f}px;width:100%;height:auto;'
            f'background:#fff;{extra_style}">')


def _fmt(v: Optional[float], suffix: str = "") -> str:
    if v is None:
        return ""
    if abs(v) >= 1000:
        return f"{v:,.0f}{suffix}"
    if v == int(v):
        return f"{int(v)}{suffix}"
    return f"{v:g}{suffix}"


def _nice_max(v: float) -> float:
    if v <= 0:
        return 1.0
    import math
    exp = math.floor(math.log10(v))
    base = 10 ** exp
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10):
        if m * base >= v:
            return m * base
    return 10 * base


def _frame_open(opts: Dict[str, Any]) -> str:
    W, H = opts.get("W", _W), opts.get("H", _H)
    title = opts.get("title", "")
    sub = opts.get("subtitle", "")
    bits = [_svg_open(W, H, opts, title or "chart")]
    if title:
        bits.append(
            f'<text x="{W/2:.0f}" y="26" text-anchor="middle" '
            f'font-family="{_SERIF}" font-size="17" font-weight="700" '
            f'fill="{_NAVY}">{_esc(title)}</text>')
    if sub:
        bits.append(
            f'<text x="{W/2:.0f}" y="43" text-anchor="middle" '
            f'font-family="{_SANS}" font-size="11" fill="{_FAINT}">'
            f'{_esc(sub)}</text>')
    return "".join(bits)


def _legend(series: List[Dict[str, Any]], colors: List[str],
            opts: Dict[str, Any]) -> str:
    W, H = opts.get("W", _W), opts.get("H", _H)
    if not opts.get("legend", True) or len(series) <= 1:
        return ""
    # Estimate widths and center the row.
    items = [(s["name"], colors[i % len(colors)])
             for i, s in enumerate(series)]
    widths = [len(name) * 6.2 + 18 for name, _ in items]
    total = sum(widths) + 14 * (len(items) - 1)
    x = (W - total) / 2
    y = H - 18
    out = ""
    for (name, color), w in zip(items, widths):
        out += (
            f'<rect x="{x:.0f}" y="{y-8:.0f}" width="10" height="10" '
            f'rx="2" fill="{color}"/>'
            f'<text x="{x+15:.0f}" y="{y+1:.0f}" font-family="{_SANS}" '
            f'font-size="11" fill="{_DIM}">{_esc(name)}</text>')
        x += w + 14
    return out


def _plot(opts: Dict[str, Any]) -> Tuple[float, float, float, float]:
    W, H = opts.get("W", _W), opts.get("H", _H)
    legend_pad = 0 if opts.get("legend", True) else -18
    return (_M["left"], _M["top"], W - _M["right"],
            H - _M["bottom"] - legend_pad)


def _y_axis(x0, y0, x1, y1, vmax, vmin, opts, suffix=""):
    """Gridlines + y labels; returns svg + a value→y mapper."""
    span = (vmax - vmin) or 1
    def yof(v):
        return y1 - (v - vmin) / span * (y1 - y0)
    svg = ""
    for i in range(6):
        v = vmin + span * i / 5
        y = yof(v)
        svg += (f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" '
                f'y2="{y:.1f}" stroke="{_GRID}" stroke-width="0.8"/>'
                f'<text x="{x0-6:.1f}" y="{y+3:.1f}" text-anchor="end" '
                f'font-family="{_SANS}" font-size="10" fill="{_FAINT}">'
                f'{_fmt(v, suffix)}</text>')
    return svg, yof


def _x_labels(cats, x0, x1, y1, opts):
    n = len(cats)
    if not n:
        return ""
    band = (x1 - x0) / n
    rot = n > 8
    out = ""
    for i, c in enumerate(cats):
        cx = x0 + band * (i + 0.5)
        if rot:
            out += (f'<text x="{cx:.1f}" y="{y1+14:.1f}" '
                    f'text-anchor="end" font-family="{_SANS}" '
                    f'font-size="10" fill="{_DIM}" '
                    f'transform="rotate(-35 {cx:.1f} {y1+14:.1f})">'
                    f'{_esc(c)}</text>')
        else:
            out += (f'<text x="{cx:.1f}" y="{y1+15:.1f}" '
                    f'text-anchor="middle" font-family="{_SANS}" '
                    f'font-size="10.5" fill="{_DIM}">{_esc(c)}</text>')
    return out


# ── Bars (column / stacked / 100% / horizontal) ──────────────────────

def _bars(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    stacked = opts.get("stacked", False)
    percent = opts.get("percent", False)
    horizontal = opts.get("horizontal", False)
    suffix = "%" if percent else opts.get("suffix", "")
    x0, y0, x1, y1 = _plot(opts)
    show_vals = opts.get("show_values", True)

    # Compute stack totals / max.
    if percent:
        totals = [sum(abs(s["values"][i] or 0) for s in series)
                  for i in range(len(cats))]
        vmax = 100.0
    elif stacked:
        vmax = _nice_max(max((sum(max(s["values"][i] or 0, 0)
                                  for s in series)
                              for i in range(len(cats))), default=1))
    else:
        vmax = _nice_max(max((max((v or 0) for v in s["values"])
                              for s in series), default=1))
    vmin = 0.0

    body = _frame_open(opts)
    if horizontal:
        # Horizontal single/grouped bars (no stacking variant here).
        n = len(cats)
        band = (y1 - y0) / max(n, 1)
        body += (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x0:.1f}" '
                 f'y2="{y1:.1f}" stroke="{_GRID}" stroke-width="0.8"/>')
        ns = len(series)
        for i, c in enumerate(cats):
            gy = y0 + band * i
            inner = band * 0.78
            bh = inner / max(ns, 1)
            for si, s in enumerate(series):
                v = s["values"][i] or 0
                w = (v / vmax) * (x1 - x0)
                yy = gy + band * 0.11 + si * bh
                body += (f'<rect x="{x0:.1f}" y="{yy:.1f}" '
                         f'width="{max(0, w):.1f}" height="{bh*0.92:.1f}" '
                         f'fill="{colors[si % len(colors)]}" rx="1"/>')
                if show_vals and ns == 1:
                    body += (f'<text x="{x0+w+4:.1f}" y="{yy+bh*0.7:.1f}" '
                             f'font-family="{_SANS}" font-size="10" '
                             f'fill="{_DIM}">{_fmt(v, suffix)}</text>')
            body += (f'<text x="{x0-6:.1f}" y="{gy+band*0.55:.1f}" '
                     f'text-anchor="end" font-family="{_SANS}" '
                     f'font-size="10.5" fill="{_DIM}">{_esc(c)}</text>')
        body += _legend(series, colors, opts) + "</svg>"
        return body

    grid, yof = _y_axis(x0, y0, x1, y1, vmax, vmin, opts, suffix)
    body += grid
    n = len(cats)
    band = (x1 - x0) / max(n, 1)
    ns = len(series)
    for i, c in enumerate(cats):
        gx = x0 + band * i
        if stacked or percent:
            cum = 0.0
            tot = totals[i] if percent else 1
            for si, s in enumerate(series):
                raw = s["values"][i] or 0
                v = (raw / tot * 100) if percent and tot else raw
                h = (v / vmax) * (y1 - y0)
                yy = yof(cum + v)
                body += (f'<rect x="{gx+band*0.18:.1f}" y="{yy:.1f}" '
                         f'width="{band*0.64:.1f}" height="{max(0,h):.1f}" '
                         f'fill="{colors[si % len(colors)]}"/>')
                if show_vals and v > vmax * 0.06:
                    body += (f'<text x="{gx+band*0.5:.1f}" '
                             f'y="{yy+h/2+3:.1f}" text-anchor="middle" '
                             f'font-family="{_SANS}" font-size="9.5" '
                             f'fill="#fff">{_fmt(v, suffix)}</text>')
                cum += v
        else:
            bw = band * 0.7 / max(ns, 1)
            for si, s in enumerate(series):
                v = s["values"][i] or 0
                h = (v / vmax) * (y1 - y0)
                xx = gx + band * 0.15 + si * bw
                yy = yof(v)
                body += (f'<rect x="{xx:.1f}" y="{yy:.1f}" '
                         f'width="{bw*0.9:.1f}" height="{max(0,h):.1f}" '
                         f'fill="{colors[si % len(colors)]}" rx="1"/>')
                if show_vals and ns <= 3:
                    body += (f'<text x="{xx+bw*0.45:.1f}" y="{yy-3:.1f}" '
                             f'text-anchor="middle" font-family="{_SANS}" '
                             f'font-size="9.5" fill="{_DIM}">'
                             f'{_fmt(v, suffix)}</text>')
    body += _x_labels(cats, x0, x1, y1, opts)
    body += _legend(series, colors, opts) + "</svg>"
    return body


# ── Lines / area ─────────────────────────────────────────────────────

def _lines(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    area = opts.get("area", False)
    x0, y0, x1, y1 = _plot(opts)
    n = len(cats)
    if area:
        vmax = _nice_max(max((sum(max(s["values"][i] or 0, 0)
                                  for s in series)
                              for i in range(n)), default=1))
    else:
        vmax = _nice_max(max((max((v or 0) for v in s["values"])
                              for s in series), default=1))
    body = _frame_open(opts)
    grid, yof = _y_axis(x0, y0, x1, y1, vmax, 0, opts, opts.get("suffix", ""))
    body += grid
    def xof(i):
        return x0 + (x1 - x0) * (i / max(n - 1, 1))
    if area:
        cum = [0.0] * n
        for si, s in enumerate(series):
            top = [cum[i] + (s["values"][i] or 0) for i in range(n)]
            pts_top = " ".join(f"{xof(i):.1f},{yof(top[i]):.1f}"
                               for i in range(n))
            pts_bot = " ".join(f"{xof(i):.1f},{yof(cum[i]):.1f}"
                               for i in range(n - 1, -1, -1))
            body += (f'<polygon points="{pts_top} {pts_bot}" '
                     f'fill="{colors[si % len(colors)]}" '
                     f'fill-opacity="0.85"/>')
            cum = top
    else:
        for si, s in enumerate(series):
            pts = " ".join(f"{xof(i):.1f},{yof(s['values'][i] or 0):.1f}"
                           for i in range(n))
            body += (f'<polyline points="{pts}" fill="none" '
                     f'stroke="{colors[si % len(colors)]}" '
                     f'stroke-width="2.4" stroke-linejoin="round"/>')
            for i in range(n):
                body += (f'<circle cx="{xof(i):.1f}" '
                         f'cy="{yof(s["values"][i] or 0):.1f}" r="2.6" '
                         f'fill="{colors[si % len(colors)]}"/>')
    body += _x_labels(cats, x0, x1, y1, opts)
    body += _legend(series, colors, opts) + "</svg>"
    return body


# ── Waterfall (bridge) ───────────────────────────────────────────────

def _waterfall(table, opts):
    cats = [r[0] for r in table["rows"]]
    deltas = [(r[1][0] if r[1] else 0) or 0 for r in table["rows"]]
    colors = opts["colors"]
    pos, neg, tot = "#0a8a5f", "#b5321e", _NAVY
    x0, y0, x1, y1 = _plot(opts)
    # Cumulative path; a row labelled total/net/= renders as an absolute
    # bar from zero.
    cum = 0.0
    bars = []
    running = 0.0
    for c, d in zip(cats, deltas):
        is_total = any(k in c.lower() for k in ("total", "net", "="))
        if is_total:
            start, end = 0.0, (d if d else running)
        else:
            start, end = running, running + d
            running = end
        bars.append((c, start, end, is_total))
    vals = [v for _, s, e, _ in bars for v in (s, e)]
    vmax = _nice_max(max(vals + [1]))
    vmin = min(vals + [0])
    body = _frame_open(opts)
    grid, yof = _y_axis(x0, y0, x1, y1, vmax, min(vmin, 0), opts,
                        opts.get("suffix", ""))
    body += grid
    n = len(bars)
    band = (x1 - x0) / max(n, 1)
    prev_x = None
    for i, (c, start, end, is_total) in enumerate(bars):
        gx = x0 + band * i + band * 0.18
        bw = band * 0.64
        top, bot = max(start, end), min(start, end)
        yy, h = yof(top), abs(yof(bot) - yof(top))
        col = tot if is_total else (pos if end >= start else neg)
        body += (f'<rect x="{gx:.1f}" y="{yy:.1f}" width="{bw:.1f}" '
                 f'height="{max(h,1):.1f}" fill="{col}" rx="1"/>')
        body += (f'<text x="{gx+bw/2:.1f}" y="{yy-3:.1f}" '
                 f'text-anchor="middle" font-family="{_SANS}" '
                 f'font-size="9.5" fill="{_DIM}">'
                 f'{_fmt(end if is_total else (end-start), opts.get("suffix",""))}'
                 f'</text>')
        if prev_x is not None and not is_total:
            body += (f'<line x1="{prev_x:.1f}" y1="{yof(start):.1f}" '
                     f'x2="{gx:.1f}" y2="{yof(start):.1f}" '
                     f'stroke="{_FAINT}" stroke-width="0.7" '
                     f'stroke-dasharray="2 2"/>')
        prev_x = gx + bw
    body += _x_labels(cats, x0, x1, y1, dict(opts, legend=False)) + "</svg>"
    return body


# ── Pie / donut ──────────────────────────────────────────────────────

def _pie(table, opts):
    import math
    labels = [r[0] for r in table["rows"]]
    vals = [(r[1][0] if r[1] else 0) or 0 for r in table["rows"]]
    colors = opts["colors"]
    donut = opts.get("donut", False)
    W, H = opts.get("W", _W), opts.get("H", _H)
    cx, cy, R = W / 2, H / 2 + 6, 130.0
    total = sum(vals) or 1
    body = _frame_open(opts)
    ang = -math.pi / 2
    for i, (lab, v) in enumerate(zip(labels, vals)):
        frac = v / total
        a2 = ang + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x1p, y1p = cx + R * math.cos(ang), cy + R * math.sin(ang)
        x2p, y2p = cx + R * math.cos(a2), cy + R * math.sin(a2)
        col = colors[i % len(colors)]
        body += (f'<path d="M {cx:.1f} {cy:.1f} L {x1p:.1f} {y1p:.1f} '
                 f'A {R:.1f} {R:.1f} 0 {large} 1 {x2p:.1f} {y2p:.1f} Z" '
                 f'fill="{col}" stroke="#fff" stroke-width="1.5"/>')
        mid = (ang + a2) / 2
        lx, ly = cx + R * 0.62 * math.cos(mid), cy + R * 0.62 * math.sin(mid)
        if frac > 0.04:
            body += (f'<text x="{lx:.1f}" y="{ly+3:.1f}" '
                     f'text-anchor="middle" font-family="{_SANS}" '
                     f'font-size="11" font-weight="600" fill="#fff">'
                     f'{frac*100:.0f}%</text>')
        ang = a2
    if donut:
        body += (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R*0.55:.1f}" '
                 f'fill="#fff"/>')
    body += _legend([{"name": l} for l in labels], colors,
                    dict(opts, legend=True)) + "</svg>"
    return body


# ── Scatter / bubble ─────────────────────────────────────────────────

def _scatter(table, opts):
    rows = table["rows"]
    colors = opts["colors"]
    bubble = opts.get("bubble", False)
    pts = []
    for lab, vals in rows:
        if len(vals) >= 2 and vals[0] is not None and vals[1] is not None:
            size = vals[2] if (bubble and len(vals) >= 3
                               and vals[2] is not None) else None
            pts.append((lab, vals[0], vals[1], size))
    x0, y0, x1, y1 = _plot(opts)
    xs = [p[1] for p in pts] or [0, 1]
    ys = [p[2] for p in pts] or [0, 1]
    xmin, xmax = min(xs + [0]), _nice_max(max(xs + [1]))
    ymax = _nice_max(max(ys + [1]))
    body = _frame_open(opts)
    grid, yof = _y_axis(x0, y0, x1, y1, ymax, 0, opts, opts.get("ysuffix", ""))
    body += grid
    body += (f'<line x1="{x0:.1f}" y1="{y1:.1f}" x2="{x1:.1f}" '
             f'y2="{y1:.1f}" stroke="{_FAINT}" stroke-width="0.8"/>')
    def xof(v):
        return x0 + (v - xmin) / ((xmax - xmin) or 1) * (x1 - x0)
    sizes = [p[3] for p in pts if p[3]] or [1]
    smax = max(sizes)
    for i, (lab, xv, yv, sz) in enumerate(pts):
        r = (6 + 22 * ((sz / smax) ** 0.5)) if (bubble and sz) else 5
        col = colors[i % len(colors)]
        body += (f'<circle cx="{xof(xv):.1f}" cy="{yof(yv):.1f}" '
                 f'r="{r:.1f}" fill="{col}" fill-opacity="0.72" '
                 f'stroke="#fff" stroke-width="1"><title>{_esc(lab)}: '
                 f'({_fmt(xv)}, {_fmt(yv)})</title></circle>'
                 f'<text x="{xof(xv):.1f}" y="{yof(yv)-r-2:.1f}" '
                 f'text-anchor="middle" font-family="{_SANS}" '
                 f'font-size="9.5" fill="{_DIM}">{_esc(lab)}</text>')
    # x ticks
    for i in range(6):
        v = xmin + (xmax - xmin) * i / 5
        body += (f'<text x="{xof(v):.1f}" y="{y1+14:.1f}" '
                 f'text-anchor="middle" font-family="{_SANS}" '
                 f'font-size="10" fill="{_FAINT}">'
                 f'{_fmt(v, opts.get("xsuffix",""))}</text>')
    body += "</svg>"
    return body


# ── Marimekko (variable-width stacked) ───────────────────────────────

def _marimekko(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(opts)
    col_tot = [sum(max(s["values"][i] or 0, 0) for s in series)
               for i in range(len(cats))]
    grand = sum(col_tot) or 1
    body = _frame_open(opts)
    cx = x0
    for i, c in enumerate(cats):
        w = (col_tot[i] / grand) * (x1 - x0)
        cum = 0.0
        t = col_tot[i] or 1
        for si, s in enumerate(series):
            v = max(s["values"][i] or 0, 0)
            frac = v / t
            h = frac * (y1 - y0)
            yy = y0 + cum
            body += (f'<rect x="{cx:.1f}" y="{yy:.1f}" '
                     f'width="{max(w-1.2,0):.1f}" height="{h:.1f}" '
                     f'fill="{colors[si % len(colors)]}"/>')
            if frac > 0.08 and w > 26:
                body += (f'<text x="{cx+w/2:.1f}" y="{yy+h/2+3:.1f}" '
                         f'text-anchor="middle" font-family="{_SANS}" '
                         f'font-size="9.5" fill="#fff">{frac*100:.0f}%</text>')
            cum += h
        body += (f'<text x="{cx+w/2:.1f}" y="{y1+14:.1f}" '
                 f'text-anchor="middle" font-family="{_SANS}" '
                 f'font-size="10" fill="{_DIM}">{_esc(c)}</text>')
        cx += w
    body += _legend(series, colors, opts) + "</svg>"
    return body


# ── Combo (bars + line) ──────────────────────────────────────────────

def _combo(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(opts)
    n = len(cats)
    if not series:
        return _frame_open(opts) + "</svg>"
    bar_s = series[0]
    line_s = series[1] if len(series) > 1 else None
    vmax = _nice_max(max((v or 0) for v in bar_s["values"]) or 1)
    body = _frame_open(opts)
    grid, yof = _y_axis(x0, y0, x1, y1, vmax, 0, opts, opts.get("suffix", ""))
    body += grid
    band = (x1 - x0) / max(n, 1)
    for i in range(n):
        v = bar_s["values"][i] or 0
        h = (v / vmax) * (y1 - y0)
        gx = x0 + band * i + band * 0.2
        body += (f'<rect x="{gx:.1f}" y="{yof(v):.1f}" '
                 f'width="{band*0.6:.1f}" height="{max(h,0):.1f}" '
                 f'fill="{colors[0]}" rx="1"/>')
    if line_s:
        lmax = _nice_max(max((v or 0) for v in line_s["values"]) or 1)
        def xof(i):
            return x0 + band * (i + 0.5)
        def yl(v):
            return y1 - (v / lmax) * (y1 - y0)
        pts = " ".join(f"{xof(i):.1f},{yl(line_s['values'][i] or 0):.1f}"
                       for i in range(n))
        body += (f'<polyline points="{pts}" fill="none" '
                 f'stroke="{colors[1 % len(colors)]}" stroke-width="2.4"/>')
        for i in range(n):
            body += (f'<circle cx="{xof(i):.1f}" '
                     f'cy="{yl(line_s["values"][i] or 0):.1f}" r="3" '
                     f'fill="{colors[1 % len(colors)]}"/>')
    body += _x_labels(cats, x0, x1, y1, opts)
    body += _legend(series[:2], colors, opts) + "</svg>"
    return body


# ── Funnel (TAM/SAM/SOM, conversion) ─────────────────────────────────

def _funnel(table, opts):
    cats = [r[0] for r in table["rows"]]
    vals = [(r[1][0] if r[1] else 0) or 0 for r in table["rows"]]
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    body = _frame_open(opts)
    n = len(cats)
    if not n:
        return body + "</svg>"
    vmax = max(vals) or 1
    cx = (x0 + x1) / 2
    sh = (y1 - y0) / n
    suffix = opts.get("suffix", "")
    for i, (c, v) in enumerate(zip(cats, vals)):
        w_top = (v / vmax) * (x1 - x0)
        v_next = vals[i + 1] if i + 1 < n else v
        w_bot = (v_next / vmax) * (x1 - x0)
        yt, yb = y0 + sh * i + 3, y0 + sh * (i + 1) - 3
        pts = (f"{cx-w_top/2:.1f},{yt:.1f} {cx+w_top/2:.1f},{yt:.1f} "
               f"{cx+w_bot/2:.1f},{yb:.1f} {cx-w_bot/2:.1f},{yb:.1f}")
        body += (f'<polygon points="{pts}" fill="{colors[i % len(colors)]}" '
                 f'fill-opacity="0.92"/>')
        conv = f" · {v/vals[0]*100:.0f}%" if vals[0] else ""
        body += (f'<text x="{cx:.1f}" y="{(yt+yb)/2+4:.1f}" '
                 f'text-anchor="middle" font-family="{_SANS}" '
                 f'font-size="12" font-weight="700" fill="#fff">'
                 f'{_esc(c)}: {_fmt(v, suffix)}{conv}</text>')
    body += "</svg>"
    return body


# ── Tornado (sensitivity, diverging) ─────────────────────────────────

def _tornado(table, opts):
    rows = sorted(table["rows"],
                  key=lambda r: -abs((r[1][0] if r[1] else 0) or 0))
    colors = opts["colors"]
    pos, neg = "#0a8a5f", "#b5321e"
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    body = _frame_open(opts)
    vmax = max((abs((r[1][0] if r[1] else 0) or 0) for r in rows),
               default=1) or 1
    cxx = (x0 + x1) / 2
    half = (x1 - x0) / 2
    n = len(rows)
    band = (y1 - y0) / max(n, 1)
    suffix = opts.get("suffix", "")
    body += (f'<line x1="{cxx:.1f}" y1="{y0:.1f}" x2="{cxx:.1f}" '
             f'y2="{y1:.1f}" stroke="{_FAINT}" stroke-width="1"/>')
    for i, (lab, v) in enumerate(rows):
        val = (v[0] if v else 0) or 0
        w = abs(val) / vmax * half
        yy = y0 + band * i + band * 0.2
        bx = cxx if val >= 0 else cxx - w
        body += (f'<rect x="{bx:.1f}" y="{yy:.1f}" width="{w:.1f}" '
                 f'height="{band*0.6:.1f}" fill="{pos if val>=0 else neg}" '
                 f'rx="1"/>')
        tx = cxx + w + 4 if val >= 0 else cxx - w - 4
        anc = "start" if val >= 0 else "end"
        body += (f'<text x="{tx:.1f}" y="{yy+band*0.42:.1f}" '
                 f'text-anchor="{anc}" font-family="{_SANS}" '
                 f'font-size="10" fill="{_DIM}">{_fmt(val, suffix)}</text>'
                 f'<text x="{x0-4:.1f}" y="{yy+band*0.42:.1f}" '
                 f'text-anchor="end" font-family="{_SANS}" font-size="10.5" '
                 f'fill="{_DIM}">{_esc(lab)}</text>')
    body += "</svg>"
    return body


# ── Radar (spider) ───────────────────────────────────────────────────

def _radar(table, opts):
    import math
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    W, H = opts.get("W", _W), opts.get("H", _H)
    cx, cy, R = W / 2, H / 2 + 8, 150.0
    n = len(cats)
    if n < 3:
        return _frame_open(opts) + '</svg>'
    vmax = _nice_max(max((max((v or 0) for v in s["values"])
                          for s in series), default=1))
    body = _frame_open(opts)
    def pt(i, frac):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return (cx + R * frac * math.cos(a), cy + R * frac * math.sin(a))
    for ring in (0.25, 0.5, 0.75, 1.0):
        rp = " ".join(f"{x:.1f},{y:.1f}"
                      for x, y in (pt(i, ring) for i in range(n)))
        body += (f'<polygon points="{rp}" fill="none" stroke="{_GRID}" '
                 f'stroke-width="0.8"/>')
    for i, c in enumerate(cats):
        ex, ey = pt(i, 1.0)
        lx, ly = pt(i, 1.13)
        body += (f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ex:.1f}" '
                 f'y2="{ey:.1f}" stroke="{_GRID}" stroke-width="0.6"/>'
                 f'<text x="{lx:.1f}" y="{ly+3:.1f}" text-anchor="middle" '
                 f'font-family="{_SANS}" font-size="10" fill="{_DIM}">'
                 f'{_esc(c)}</text>')
    for si, s in enumerate(series):
        poly = " ".join(
            f"{x:.1f},{y:.1f}" for x, y in
            (pt(i, (s["values"][i] or 0) / vmax) for i in range(n)))
        col = colors[si % len(colors)]
        body += (f'<polygon points="{poly}" fill="{col}" '
                 f'fill-opacity="0.18" stroke="{col}" stroke-width="2"/>')
    body += _legend(series, colors, opts) + "</svg>"
    return body


# ── Bullet (actual vs target) ────────────────────────────────────────

def _bullet(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    body = _frame_open(opts)
    actual = series[0]["values"] if series else []
    target = series[1]["values"] if len(series) > 1 else [None] * len(cats)
    allv = [v for v in (actual + [t for t in target if t is not None])
            if v is not None]
    vmax = _nice_max(max(allv) if allv else 1)
    n = len(cats)
    band = (y1 - y0) / max(n, 1)
    suffix = opts.get("suffix", "")
    for i, c in enumerate(cats):
        yy = y0 + band * i + band * 0.25
        bh = band * 0.5
        body += (f'<rect x="{x0:.1f}" y="{yy:.1f}" width="{x1-x0:.1f}" '
                 f'height="{bh:.1f}" fill="#ece5d6" rx="2"/>')
        a = actual[i] or 0
        body += (f'<rect x="{x0:.1f}" y="{yy+bh*0.2:.1f}" '
                 f'width="{a/vmax*(x1-x0):.1f}" height="{bh*0.6:.1f}" '
                 f'fill="{colors[0]}" rx="1"/>')
        t = target[i]
        if t is not None:
            tx = x0 + t / vmax * (x1 - x0)
            body += (f'<line x1="{tx:.1f}" y1="{yy-2:.1f}" x2="{tx:.1f}" '
                     f'y2="{yy+bh+2:.1f}" stroke="#b5321e" '
                     f'stroke-width="2.5"/>')
        body += (f'<text x="{x0-4:.1f}" y="{yy+bh*0.7:.1f}" '
                 f'text-anchor="end" font-family="{_SANS}" font-size="10.5" '
                 f'fill="{_DIM}">{_esc(c)}</text>'
                 f'<text x="{x1+2:.1f}" y="{yy+bh*0.7:.1f}" '
                 f'font-family="{_SANS}" font-size="10" fill="{_DIM}">'
                 f'{_fmt(a, suffix)}</text>')
    body += "</svg>"
    return body


# ── Dot / lollipop (ranking) ─────────────────────────────────────────

def _dot(table, opts):
    rows = sorted(table["rows"],
                  key=lambda r: (r[1][0] if r[1] else 0) or 0)
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    body = _frame_open(opts)
    vals = [(r[1][0] if r[1] else 0) or 0 for r in rows]
    vmax = _nice_max(max(vals) if vals else 1)
    n = len(rows)
    band = (y1 - y0) / max(n, 1)
    suffix = opts.get("suffix", "")
    for i, (lab, v) in enumerate(rows):
        val = (v[0] if v else 0) or 0
        yy = y0 + band * (i + 0.5)
        vx = x0 + val / vmax * (x1 - x0)
        body += (f'<line x1="{x0:.1f}" y1="{yy:.1f}" x2="{vx:.1f}" '
                 f'y2="{yy:.1f}" stroke="{_GRID}" stroke-width="2"/>'
                 f'<circle cx="{vx:.1f}" cy="{yy:.1f}" r="5.5" '
                 f'fill="{colors[0]}"/>'
                 f'<text x="{x0-4:.1f}" y="{yy+3.5:.1f}" text-anchor="end" '
                 f'font-family="{_SANS}" font-size="10.5" fill="{_DIM}">'
                 f'{_esc(lab)}</text>'
                 f'<text x="{vx+9:.1f}" y="{yy+3.5:.1f}" '
                 f'font-family="{_SANS}" font-size="10" fill="{_DIM}">'
                 f'{_fmt(val, suffix)}</text>')
    body += "</svg>"
    return body


# ── Gauge (single KPI) ───────────────────────────────────────────────

def _gauge(table, opts):
    import math
    rows = table["rows"]
    if not rows:
        return _frame_open(opts) + "</svg>"
    label = rows[0][0]
    vals = rows[0][1] if rows[0][1] else [0]
    value = vals[0] or 0
    vmax = (vals[1] if len(vals) > 1 and vals[1] else None) or \
        _nice_max(value * 1.25 if value else 100)
    colors = opts["colors"]
    suffix = opts.get("suffix", "")
    W, H = opts.get("W", _W), opts.get("H", _H)
    cx, cy, R = W / 2, H / 2 + 70, 165.0
    body = _frame_open(opts)
    frac = max(0.0, min(1.0, value / vmax if vmax else 0))

    def arc(a0, a1, color, width):
        x0a, y0a = cx + R * math.cos(a0), cy + R * math.sin(a0)
        x1a, y1a = cx + R * math.cos(a1), cy + R * math.sin(a1)
        large = 1 if (a1 - a0) > math.pi else 0
        return (f'<path d="M {x0a:.1f} {y0a:.1f} A {R:.1f} {R:.1f} 0 '
                f'{large} 1 {x1a:.1f} {y1a:.1f}" fill="none" '
                f'stroke="{color}" stroke-width="{width}" '
                f'stroke-linecap="round"/>')
    # 180° gauge from left (π) to right (2π).
    body += arc(math.pi, 2 * math.pi, "#ece5d6", 26)
    body += arc(math.pi, math.pi + frac * math.pi, colors[0], 26)
    body += (f'<text x="{cx:.1f}" y="{cy-8:.1f}" text-anchor="middle" '
             f'font-family="{_SERIF}" font-size="46" font-weight="700" '
             f'fill="{_NAVY}">{_fmt(value, suffix)}</text>'
             f'<text x="{cx:.1f}" y="{cy+18:.1f}" text-anchor="middle" '
             f'font-family="{_SANS}" font-size="13" fill="{_FAINT}">'
             f'{_esc(label)} · of {_fmt(vmax, suffix)}</text>'
             f'<text x="{cx-R:.1f}" y="{cy+20:.1f}" text-anchor="middle" '
             f'font-family="{_SANS}" font-size="10" fill="{_FAINT}">0</text>'
             f'<text x="{cx+R:.1f}" y="{cy+20:.1f}" text-anchor="middle" '
             f'font-family="{_SANS}" font-size="10" fill="{_FAINT}">'
             f'{_fmt(vmax, suffix)}</text>')
    body += "</svg>"
    return body


# ── 2×2 matrix (positioning) ─────────────────────────────────────────

def _matrix(table, opts):
    rows = table["rows"]
    colors = opts["colors"]
    pts = []
    for lab, vals in rows:
        if len(vals) >= 2 and vals[0] is not None and vals[1] is not None:
            sz = vals[2] if len(vals) >= 3 and vals[2] is not None else None
            pts.append((lab, vals[0], vals[1], sz))
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    body = _frame_open(opts)
    xs = [p[1] for p in pts] or [0, 1]
    ys = [p[2] for p in pts] or [0, 1]
    xmin, xmax = min(xs), max(xs) or 1
    ymin, ymax = min(ys), max(ys) or 1
    xmin -= (xmax - xmin) * 0.12 or 1
    xmax += (xmax - xmin) * 0.08 or 1
    ymin -= (ymax - ymin) * 0.12 or 1
    ymax += (ymax - ymin) * 0.08 or 1
    def xof(v):
        return x0 + (v - xmin) / ((xmax - xmin) or 1) * (x1 - x0)
    def yof(v):
        return y1 - (v - ymin) / ((ymax - ymin) or 1) * (y1 - y0)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    body += (f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1-x0:.1f}" '
             f'height="{y1-y0:.1f}" fill="#fbf9f4" stroke="{_GRID}"/>'
             f'<line x1="{mx:.1f}" y1="{y0:.1f}" x2="{mx:.1f}" y2="{y1:.1f}" '
             f'stroke="{_FAINT}" stroke-dasharray="3 3" stroke-width="0.8"/>'
             f'<line x1="{x0:.1f}" y1="{my:.1f}" x2="{x1:.1f}" y2="{my:.1f}" '
             f'stroke="{_FAINT}" stroke-dasharray="3 3" stroke-width="0.8"/>')
    sizes = [p[3] for p in pts if p[3]] or [1]
    smax = max(sizes)
    for i, (lab, xv, yv, sz) in enumerate(pts):
        r = (7 + 20 * ((sz / smax) ** 0.5)) if sz else 7
        body += (f'<circle cx="{xof(xv):.1f}" cy="{yof(yv):.1f}" r="{r:.1f}" '
                 f'fill="{colors[i % len(colors)]}" fill-opacity="0.72" '
                 f'stroke="#fff" stroke-width="1.2"/>'
                 f'<text x="{xof(xv):.1f}" y="{yof(yv)-r-3:.1f}" '
                 f'text-anchor="middle" font-family="{_SANS}" '
                 f'font-size="10" font-weight="600" fill="{_INK}">'
                 f'{_esc(lab)}</text>')
    # Axis titles from headers.
    h = table.get("headers", [])
    xlab = h[1] if len(h) > 1 else "X"
    ylab = h[2] if len(h) > 2 else "Y"
    body += (f'<text x="{(x0+x1)/2:.1f}" y="{y1+18:.1f}" '
             f'text-anchor="middle" font-family="{_SANS}" font-size="11" '
             f'fill="{_FAINT}">{_esc(xlab)} →</text>'
             f'<text x="{x0-14:.1f}" y="{(y0+y1)/2:.1f}" '
             f'text-anchor="middle" font-family="{_SANS}" font-size="11" '
             f'fill="{_FAINT}" transform="rotate(-90 {x0-14:.1f} '
             f'{(y0+y1)/2:.1f})">{_esc(ylab)} →</text>')
    body += "</svg>"
    return body


# ── Heatmap grid (scoring matrix) ────────────────────────────────────

def _heat_color(frac: float) -> str:
    frac = max(0.0, min(1.0, frac))
    c0, c1 = (0xE9, 0xF1, 0xF0), (0x12, 0x5E, 0x59)
    rgb = tuple(round(c0[i] + (c1[i] - c0[i]) * frac) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _heatmap(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    headers = table.get("headers", [])
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    y0 += 14   # room for column headers
    nrow, ncol = len(cats), len(series)
    if not nrow or not ncol:
        return _frame_open(opts) + "</svg>"
    allv = [v for s in series for v in s["values"] if v is not None]
    lo, hi = (min(allv), max(allv)) if allv else (0, 1)
    rng = (hi - lo) or 1
    body = _frame_open(opts)
    cw = (x1 - x0) / ncol
    ch = (y1 - y0) / nrow
    suffix = opts.get("suffix", "")
    for j, s in enumerate(series):
        hx = x0 + cw * (j + 0.5)
        name = headers[j + 1] if j + 1 < len(headers) else s["name"]
        body += (f'<text x="{hx:.1f}" y="{y0-5:.1f}" text-anchor="middle" '
                 f'font-family="{_SANS}" font-size="10" font-weight="600" '
                 f'fill="{_DIM}">{_esc(name)}</text>')
    for i, c in enumerate(cats):
        ry = y0 + ch * i
        body += (f'<text x="{x0-6:.1f}" y="{ry+ch/2+3:.1f}" '
                 f'text-anchor="end" font-family="{_SANS}" font-size="10.5" '
                 f'fill="{_DIM}">{_esc(c)}</text>')
        for j, s in enumerate(series):
            v = s["values"][i]
            cx = x0 + cw * j
            fill = _heat_color((v - lo) / rng) if v is not None else "#f3efe4"
            tcol = "#fff" if (v is not None and (v - lo) / rng > 0.55) \
                else _INK
            body += (f'<rect x="{cx+1:.1f}" y="{ry+1:.1f}" '
                     f'width="{cw-2:.1f}" height="{ch-2:.1f}" rx="2" '
                     f'fill="{fill}"/>')
            if v is not None:
                body += (f'<text x="{cx+cw/2:.1f}" y="{ry+ch/2+3.5:.1f}" '
                         f'text-anchor="middle" font-family="{_SANS}" '
                         f'font-size="10.5" font-weight="600" fill="{tcol}">'
                         f'{_fmt(v, suffix)}</text>')
    body += "</svg>"
    return body


# ── Export toolbar (download SVG / PNG, copy) ────────────────────────

def chart_export_toolbar(target_id: str, filename: str = "chart") -> str:
    """Buttons to download the rendered SVG / a 2× PNG, or copy the SVG —
    pure vanilla JS, no dependencies. ``target_id`` is the id of the
    container holding the <svg>."""
    fn = html.escape(filename, quote=True)
    tid = html.escape(target_id, quote=True)
    btn = ("padding:6px 13px;border:1px solid #c9c1ac;border-radius:5px;"
           "background:#fff;color:#0b2341;font-size:12px;font-weight:600;"
           "cursor:pointer;")
    return (
        f'<div style="display:flex;gap:8px;justify-content:center;'
        f'margin-top:10px;flex-wrap:wrap;">'
        f'<button type="button" style="{btn}" '
        f'onclick="ckDlSvg(\'{tid}\',\'{fn}\')">⬇ SVG</button>'
        f'<button type="button" style="{btn}" '
        f'onclick="ckDlPng(\'{tid}\',\'{fn}\')">⬇ PNG (2×)</button>'
        f'<button type="button" style="{btn}" '
        f'onclick="ckCopySvg(\'{tid}\',this)">⧉ Copy SVG</button></div>'
        '<script>'
        'function ckSvgStr(id){var c=document.getElementById(id);'
        'if(!c)return"";var s=c.querySelector("svg");if(!s)return"";'
        'var n=s.cloneNode(true);n.setAttribute("xmlns",'
        '"http://www.w3.org/2000/svg");'
        'return "<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>\\n"'
        '+new XMLSerializer().serializeToString(n);}'
        'function ckDlSvg(id,fn){var str=ckSvgStr(id);if(!str)return;'
        'var b=new Blob([str],{type:"image/svg+xml;charset=utf-8"});'
        'var a=document.createElement("a");a.href=URL.createObjectURL(b);'
        'a.download=fn+".svg";document.body.appendChild(a);a.click();'
        'a.remove();}'
        'function ckCopySvg(id,btn){var str=ckSvgStr(id);if(!str)return;'
        'navigator.clipboard.writeText(str).then(function(){'
        'var t=btn.textContent;btn.textContent="✓ Copied";'
        'setTimeout(function(){btn.textContent=t;},1200);});}'
        'function ckDlPng(id,fn){var c=document.getElementById(id);'
        'if(!c)return;var s=c.querySelector("svg");if(!s)return;'
        'var vb=s.viewBox.baseVal;var w=(vb&&vb.width)||720;'
        'var h=(vb&&vb.height)||450;var sc=2;'
        'var cv=document.createElement("canvas");cv.width=w*sc;cv.height=h*sc;'
        'var ctx=cv.getContext("2d");ctx.fillStyle="#fff";'
        'ctx.fillRect(0,0,cv.width,cv.height);ctx.scale(sc,sc);'
        'var img=new Image();img.onload=function(){ctx.drawImage(img,0,0,w,h);'
        'cv.toBlob(function(bl){var a=document.createElement("a");'
        'a.href=URL.createObjectURL(bl);a.download=fn+".png";'
        'document.body.appendChild(a);a.click();a.remove();});};'
        'img.src="data:image/svg+xml;base64,"+btoa(unescape('
        'encodeURIComponent(ckSvgStr(id))));}'
        '</script>')


# Size presets (display width in px).
SIZE_PRESETS = [("S", 520), ("M", 720), ("L", 920), ("XL", 1120)]


# ── Dispatch ─────────────────────────────────────────────────────────

_DISPATCH = {
    "column": (_bars, {}),
    "column_stacked": (_bars, {"stacked": True}),
    "column_100": (_bars, {"stacked": True, "percent": True}),
    "bar": (_bars, {"horizontal": True}),
    "line": (_lines, {}),
    "area": (_lines, {"area": True}),
    "waterfall": (_waterfall, {}),
    "funnel": (_funnel, {}),
    "tornado": (_tornado, {}),
    "pie": (_pie, {}),
    "donut": (_pie, {"donut": True}),
    "scatter": (_scatter, {}),
    "bubble": (_scatter, {"bubble": True}),
    "matrix": (_matrix, {}),
    "radar": (_radar, {}),
    "bullet": (_bullet, {}),
    "dot": (_dot, {}),
    "gauge": (_gauge, {}),
    "heatmap": (_heatmap, {}),
    "marimekko": (_marimekko, {}),
    "combo": (_combo, {}),
}


def render_cdd_chart(
    chart_type: str, table: Dict[str, Any],
    opts: "Dict[str, Any] | None" = None,
) -> str:
    """Render one CDD chart as a centered, Chartis-styled SVG string.

    ``chart_type`` is one of ``CHART_TYPES``; ``table`` is a
    ``parse_table`` result; ``opts`` carries title / subtitle / palette /
    suffix / show_values / legend."""
    opts = dict(opts or {})
    fn, preset = _DISPATCH.get(chart_type, _DISPATCH["column"])
    o = {**preset, **opts}
    pal_name = o.get("palette", "Chartis")
    o["colors"] = o.get("colors") or PALETTES.get(pal_name,
                                                  PALETTES["Chartis"])
    if not table.get("rows"):
        W, H = o.get("W", _W), o.get("H", _H)
        return (_svg_open(W, H, o, "empty chart")
                + f'<text x="{W/2:.0f}" y="{H/2:.0f}" text-anchor="middle" '
                f'font-family="{_SANS}" font-size="13" fill="{_FAINT}">'
                f'Paste data to render a chart</text></svg>')
    return _with_footnote(fn(table, o), o)


def _with_footnote(svg: str, opts: Dict[str, Any]) -> str:
    """Inject a small bottom-left source/footnote line before </svg> —
    every client chart wants one."""
    note = opts.get("footnote") or opts.get("source")
    if not note or "</svg>" not in svg:
        return svg
    H = opts.get("H", _H)
    el = (f'<text x="14" y="{H-7:.1f}" font-family="{_SANS}" '
          f'font-size="9.5" fill="{_FAINT}">{_esc(note)}</text>')
    idx = svg.rfind("</svg>")
    return svg[:idx] + el + svg[idx:]


# ── Exhibit / slide composer ─────────────────────────────────────────

def _embed(svg: str, x: float, y: float, w: float, h: float) -> str:
    """Rewrite a chart's opening <svg> tag so it nests inside a parent
    SVG at (x, y) with the given box — the viewBox scales the chart in."""
    import re
    m = re.search(r'viewBox="([^"]*)"', svg[:400])
    vb = m.group(1) if m else "0 0 720 450"
    body = svg[svg.find(">") + 1:]
    return (f'<svg x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" '
            f'viewBox="{vb}" preserveAspectRatio="xMidYMid meet">{body}')


def _exhibit_layout(n: int, x0, y0, x1, y1, gap=22.0):
    """Panel boxes for n charts inside the content area."""
    if n <= 1:
        return [(x0, y0, x1 - x0, y1 - y0)]
    if n == 2:
        w = (x1 - x0 - gap) / 2
        return [(x0, y0, w, y1 - y0), (x0 + w + gap, y0, w, y1 - y0)]
    # 3–4 → 2×2 grid (3 leaves the last cell empty).
    w = (x1 - x0 - gap) / 2
    h = (y1 - y0 - gap) / 2
    cells = [(x0, y0, w, h), (x0 + w + gap, y0, w, h),
             (x0, y0 + h + gap, w, h), (x0 + w + gap, y0 + h + gap, w, h)]
    return cells[:n]


def compose_exhibit(
    panels: List[Dict[str, Any]],
    *, title: str = "", eyebrow: str = "", source: str = "",
    width_px: float = 1120,
) -> str:
    """Compose up to 4 charts onto one deck slide (16:9) with a title
    block + source line — exported as a single SVG. ``panels`` is a list
    of ``{type, table, title, palette}``."""
    W, H = 1280.0, 720.0
    panels = [p for p in panels if p.get("table", {}).get("rows")][:4]
    out = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
           f'preserveAspectRatio="xMidYMid meet" role="img" '
           f'aria-label="{_esc(title or "exhibit")}" '
           f'style="max-width:{width_px:.0f}px;width:100%;height:auto;'
           f'background:#fff;">'
           f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" '
           f'fill="#fff"/>']
    if eyebrow:
        out.append(f'<text x="40" y="40" font-family="{_SANS}" '
                   f'font-size="13" font-weight="700" letter-spacing="1.5" '
                   f'fill="{PALETTES["Chartis"][1]}">'
                   f'{_esc(eyebrow.upper())}</text>')
    if title:
        out.append(f'<text x="40" y="70" font-family="{_SERIF}" '
                   f'font-size="28" font-weight="700" fill="{_NAVY}">'
                   f'{_esc(title)}</text>')
    out.append(f'<line x1="40" y1="84" x2="{W-40:.0f}" y2="84" '
               f'stroke="{_GRID}" stroke-width="1.2"/>')
    boxes = _exhibit_layout(len(panels) or 1, 36, 96, W - 36, H - 44)
    for p, (x, y, w, h) in zip(panels, boxes):
        chart = render_cdd_chart(
            p.get("type", "column"), p["table"],
            {"title": p.get("title", ""), "palette": p.get("palette",
                                                            "Chartis"),
             "W": 720, "H": 460})
        out.append(_embed(chart, x, y, w, h))
    src = source or ""
    out.append(f'<line x1="40" y1="{H-34:.0f}" x2="{W-40:.0f}" '
               f'y2="{H-34:.0f}" stroke="{_GRID}" stroke-width="0.8"/>')
    if src:
        out.append(f'<text x="40" y="{H-16:.0f}" font-family="{_SANS}" '
                   f'font-size="11" fill="{_FAINT}">{_esc(src)}</text>')
    out.append(f'<text x="{W-40:.0f}" y="{H-16:.0f}" text-anchor="end" '
               f'font-family="{_SERIF}" font-size="11" fill="{_FAINT}">'
               f'Chartis · PEdesk</text>')
    out.append("</svg>")
    return "".join(out)
