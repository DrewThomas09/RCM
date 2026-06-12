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
    ("scatter", "Scatter"),
    ("bubble", "Bubble"),
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
    out = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
           f'height="{opts.get("px_h", 470)}" '
           f'preserveAspectRatio="xMidYMid meet" role="img" '
           f'aria-label="{_esc(title or "pie chart")}" '
           f'style="max-width:{W:.0f}px;background:#fff;font-family:{_SANS};">']
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
    bits = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
            f'height="{opts.get("px_h", 450)}" '
            f'preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{_esc(title or "chart")}" '
            f'style="max-width:{W:.0f}px;background:#fff;">']
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


# ── Dispatch ─────────────────────────────────────────────────────────

_DISPATCH = {
    "column": (_bars, {}),
    "column_stacked": (_bars, {"stacked": True}),
    "column_100": (_bars, {"stacked": True, "percent": True}),
    "bar": (_bars, {"horizontal": True}),
    "line": (_lines, {}),
    "area": (_lines, {"area": True}),
    "waterfall": (_waterfall, {}),
    "pie": (_pie, {}),
    "donut": (_pie, {"donut": True}),
    "scatter": (_scatter, {}),
    "bubble": (_scatter, {"bubble": True}),
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
        return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
                f'height="200" style="background:#fff;"><text x="{W/2:.0f}" '
                f'y="{H/2:.0f}" text-anchor="middle" font-family="{_SANS}" '
                f'font-size="13" fill="{_FAINT}">Paste data to render a '
                f'chart</text></svg>')
    return fn(table, o)
