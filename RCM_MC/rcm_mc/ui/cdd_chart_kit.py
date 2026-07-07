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
import itertools
import re as _re2
from typing import Any, Dict, List, Optional, Tuple

from ._chart_kit import DATA_SERIES_EXTENDED, _trunc

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
    # The house --sc-data-1..5 tokens (see chartis_tokens.css), shared with
    # _chart_kit so builder charts can match the platform's analysis pages.
    "House data": list(DATA_SERIES_EXTENDED),
}
_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")
_SANS = "'Inter Tight', system-ui, sans-serif"

CHART_TYPES = [
    ("column", "Column (grouped)"),
    ("column_stacked", "Stacked column"),
    ("column_100", "100% stacked column"),
    ("bar", "Horizontal bar"),
    ("bar_stacked", "Stacked bar (horiz.)"),
    ("pareto", "Pareto (80/20)"),
    ("line", "Line"),
    ("area", "Stacked area"),
    ("histogram", "Histogram"),
    ("boxplot", "Box plot"),
    ("waterfall", "Waterfall (bridge)"),
    ("pie", "Pie"),
    ("donut", "Donut"),
    ("waffle", "Waffle (share)"),
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
    ("slope", "Slope (before→after)"),
    ("dumbbell", "Dumbbell (range)"),
    ("gantt", "Gantt / timeline"),
    ("marimekko", "Marimekko"),
    ("combo", "Combo (bars + line)"),
    ("smallmult", "Small multiples"),
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
    uid = _uid_of(opts)
    # Shadow plate under the pie (hidden by the slices) for slide-ready depth.
    out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" '
               f'fill="#ffffff" filter="url(#cdsh{uid})"/>')
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
    # Spherical sheen overlay for dimensional lift.
    out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" '
               f'fill="url(#cdrg{uid})" pointer-events="none"/>')
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
    or 2+-space separated. Non-numeric cells become ``None``.

    Comma lines go through the stdlib ``csv`` reader so a quoted CSV
    export ("Los Angeles, CA",5) keeps its label in one cell instead of
    shearing into two columns. Accounting-style negatives — ``(1,234)``,
    ``($2,500)`` — coerce to negative numbers rather than silently
    dropping to ``None`` (which was deleting the negative rows of pasted
    P&L bridges)."""
    lines = [ln for ln in (text or "").replace("\r", "\n").split("\n")
             if ln.strip()]
    if not lines:
        return {"headers": [], "rows": []}

    def _split(ln: str) -> List[str]:
        if "\t" in ln:
            return [c.strip() for c in ln.split("\t")]
        if "," in ln:
            import csv
            import io
            try:
                return [c.strip() for c in
                        next(csv.reader(io.StringIO(ln)))]
            except (csv.Error, StopIteration):
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
            neg = False
            if len(c2) > 2 and c2.startswith("(") and c2.endswith(")"):
                neg = True
                c2 = c2[1:-1].strip()
            try:
                v = float(c2)
                vals.append(-v if neg else v)
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


def table_to_tsv(table: Dict[str, Any]) -> str:
    """Serialize a (possibly shaped) table back to the paste format —
    the bridge that lets a configured chart travel between pages
    (builder → exhibit) as a plain qs param. None cells become empty
    strings so a round-trip through parse_table is lossless."""
    lines = ["\t".join(str(h) for h in table.get("headers", []))]
    for lab, vals in table.get("rows", []):
        cells = [str(lab)]
        for v in vals:
            cells.append("" if v is None else
                         (str(int(v)) if v == int(v) else f"{v:g}"))
        lines.append("\t".join(cells))
    return "\n".join(ln for ln in lines if ln)


# ── Data shaping (aggregate → sort → top-N → calc) ───────────────────

TRANSFORM_GROUPS = ["sum", "mean", "max", "min", "count"]
TRANSFORM_CALCS = [
    ("pct_total", "% of total"),
    ("cumulative", "Cumulative"),
    ("moving_avg", "Moving avg (3)"),
    ("growth", "Growth % vs prior"),
    ("index", "Index (first = 100)"),
]


def transform_table(table: Dict[str, Any],
                    tf: Dict[str, Any]) -> Dict[str, Any]:
    """Shape a parsed table before charting — the Excel prep steps
    (SUMIF, sort, top-N + Other, running %, …) folded into the builder
    so a raw export can be pasted as-is.

    ``tf`` keys (all optional): ``group`` (sum|mean|max|min|count —
    aggregate duplicate labels), ``sort`` (asc|desc by first series),
    ``top_n`` (int — keep N rows, lump the rest into "Other"),
    ``calc`` (pct_total|cumulative|moving_avg|growth|index — applied
    per series). Returns a new table; the input is not mutated."""
    headers = list(table.get("headers", []))
    rows: List[Tuple[str, List[Optional[float]]]] = \
        [(lab, list(vals)) for lab, vals in table.get("rows", [])]
    ncol = max((len(v) for _, v in rows), default=0)

    group = tf.get("group")
    if group in TRANSFORM_GROUPS and rows:
        order: List[str] = []
        bucket: Dict[str, List[List[Optional[float]]]] = {}
        for lab, vals in rows:
            if lab not in bucket:
                bucket[lab] = []
                order.append(lab)
            bucket[lab].append(vals)
        rows = []
        for lab in order:
            cols: List[Optional[float]] = []
            for i in range(ncol):
                cell = [v[i] for v in bucket[lab]
                        if i < len(v) and v[i] is not None]
                if group == "count":
                    cols.append(float(len(cell)))
                elif not cell:
                    cols.append(None)
                elif group == "sum":
                    cols.append(sum(cell))
                elif group == "mean":
                    cols.append(sum(cell) / len(cell))
                elif group == "max":
                    cols.append(max(cell))
                else:
                    cols.append(min(cell))
            rows.append((lab, cols))

    sort = tf.get("sort")
    if sort in ("asc", "desc"):
        rows.sort(key=lambda r: (r[1][0] if r[1] and r[1][0] is not None
                                 else float("-inf")),
                  reverse=(sort == "desc"))

    top_n = tf.get("top_n")
    if top_n and 0 < int(top_n) < len(rows):
        keep, rest = rows[:int(top_n)], rows[int(top_n):]
        other: List[Optional[float]] = []
        for i in range(ncol):
            cell = [v[i] for _, v in rest if i < len(v) and v[i] is not None]
            other.append(sum(cell) if cell else None)
        rows = keep + [(f"Other ({len(rest)})", other)]

    calc = tf.get("calc")
    if calc in dict(TRANSFORM_CALCS) and rows:
        ncol = max((len(v) for _, v in rows), default=0)
        for i in range(ncol):
            col = [(v[i] if i < len(v) else None) for _, v in rows]
            new: List[Optional[float]]
            if calc == "pct_total":
                tot = sum(abs(v) for v in col if v is not None) or 1
                new = [None if v is None else v / tot * 100 for v in col]
            elif calc == "cumulative":
                run = 0.0
                new = []
                for v in col:
                    run += v or 0
                    new.append(None if v is None else run)
            elif calc == "moving_avg":
                new = []
                for j, v in enumerate(col):
                    win = [w for w in col[max(0, j - 2):j + 1]
                           if w is not None]
                    new.append(sum(win) / len(win) if win else None)
            elif calc == "growth":
                new = [None]
                for j in range(1, len(col)):
                    prev, cur = col[j - 1], col[j]
                    new.append((cur - prev) / abs(prev) * 100
                               if prev not in (None, 0) and cur is not None
                               else None)
            else:   # index — first non-None value = 100
                base = next((v for v in col if v not in (None, 0)), None)
                new = [None if (v is None or base is None)
                       else v / base * 100 for v in col]
            for r, v in zip(rows, new):
                if i < len(r[1]):
                    r[1][i] = v
    return {"headers": headers, "rows": rows}


# ── Shared frame ─────────────────────────────────────────────────────

def _esc(s: Any) -> str:
    return html.escape(str(s))


# ── Visual depth (gradients + soft shadow) ───────────────────────────
#
# Flat fills read as "beginner"; presentation-grade charts carry depth.
# Every chart SVG ships a tiny <defs> block (unique id per render so two
# charts on one page never collide): a soft navy drop-shadow that lifts
# bars/marks off the plate, plus vertical/horizontal "sheen" gradients
# (white at the lit edge → faint shade at the far edge) overlaid on each
# bar so a solid hue reads as a rounded, dimensional surface. The base
# colour is still a solid <rect> underneath, so palette assertions and
# colour legibility are unchanged — the gradient is a translucent overlay.

_UID = itertools.count(1)


def _depth_defs(uid: int) -> str:
    return (
        f'<defs>'
        f'<filter id="cdsh{uid}" x="-25%" y="-25%" width="150%" height="160%">'
        f'<feDropShadow dx="0" dy="1.3" stdDeviation="1.7" '
        f'flood-color="#0b2341" flood-opacity="0.22"/></filter>'
        f'<linearGradient id="cdvg{uid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.30"/>'
        f'<stop offset="0.5" stop-color="#ffffff" stop-opacity="0.06"/>'
        f'<stop offset="1" stop-color="#000000" stop-opacity="0.10"/>'
        f'</linearGradient>'
        f'<linearGradient id="cdhg{uid}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.26"/>'
        f'<stop offset="0.55" stop-color="#ffffff" stop-opacity="0.05"/>'
        f'<stop offset="1" stop-color="#000000" stop-opacity="0.11"/>'
        f'</linearGradient>'
        f'<radialGradient id="cdrg{uid}" cx="0.38" cy="0.34" r="0.85">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.26"/>'
        f'<stop offset="0.55" stop-color="#ffffff" stop-opacity="0.03"/>'
        f'<stop offset="1" stop-color="#000000" stop-opacity="0.12"/>'
        f'</radialGradient>'
        f'</defs>'
    )


def _uid_of(opts: Dict[str, Any]) -> int:
    """The depth-defs id for this render (set by ``_svg_open``)."""
    uid = opts.get("_uid")
    if uid is None:
        uid = next(_UID)
        opts["_uid"] = uid
    return uid


def _depth_bar(opts: Dict[str, Any], x: float, y: float, w: float, h: float,
               fill: str, *, rx: float = 1.5, vertical: bool = True,
               shadow: bool = True, title: str = "") -> str:
    """A bar with depth: solid colour + a sheen-gradient overlay (+ optional
    soft drop-shadow). Width/height are clamped non-negative by the caller.
    ``title`` (optional) becomes an SVG ``<title>`` child of the base rect —
    the native hover tooltip, so a bar whose value label is suppressed
    (small segment, show_values off) is still recoverable, matching the
    hover affordance the sibling kits already carry."""
    uid = opts.get("_uid", 0)
    flt = f' filter="url(#cdsh{uid})"' if shadow else ""
    grad = f"cdvg{uid}" if vertical else f"cdhg{uid}"
    if title:
        base = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                f'height="{h:.1f}" rx="{rx:g}" fill="{fill}"{flt}>'
                f'<title>{_esc(title)}</title></rect>')
    else:
        base = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                f'height="{h:.1f}" rx="{rx:g}" fill="{fill}"{flt}/>')
    return (
        base
        + f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{rx:g}" fill="url(#{grad})" pointer-events="none"/>')


def _svg_open(W: float, H: float, opts: Dict[str, Any], aria: str,
              extra_style: str = "") -> str:
    """Open an <svg> sized by ``width_px`` (default = the viewBox width),
    scaling proportionally to the container — the size control. Height is
    auto from the viewBox aspect so charts never distort. Emits a per-render
    <defs> with the depth (shadow + sheen) primitives every chart shares."""
    wpx = opts.get("width_px") or W
    uid = _uid_of(opts)
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
            f'preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{_esc(aria)}" '
            f'style="max-width:{wpx:.0f}px;width:100%;height:auto;'
            f'background:#fff;{extra_style}">'
            + _depth_defs(uid))


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


def _hint(opts: Dict[str, Any], msg: str) -> str:
    """Frame + a centered, faint what-to-do hint for degenerate inputs.

    The empty-TABLE path already tells the user 'Paste data to render a
    chart', but six chart types used to return a silent blank frame when
    the table parsed fine yet lacked the shape that chart needs (slope
    with one value column, radar with two rows, …) — in the builder that
    reads as 'my paste broke'. Same styling as the empty-table
    placeholder so the two failure modes speak with one voice."""
    W, H = opts.get("W", _W), opts.get("H", _H)
    return (_frame_open(opts)
            + f'<text x="{W/2:.0f}" y="{H/2:.0f}" text-anchor="middle" '
            f'font-family="{_SANS}" font-size="13" fill="{_FAINT}">'
            f'{_esc(msg)}</text></svg>')


def _legend(series: List[Dict[str, Any]], colors: List[str],
            opts: Dict[str, Any]) -> str:
    W, H = opts.get("W", _W), opts.get("H", _H)
    if not opts.get("legend", True) or len(series) <= 1:
        return ""
    # Long series names used to walk straight off the 720px frame (no
    # truncation, and the centered start-x could go negative). Mirror
    # _chart_kit's treatment: ellipsize past 18 chars with the full name in
    # a <title>, and wrap to a second row when one row won't fit.
    items = [(str(s["name"]), colors[i % len(colors)])
             for i, s in enumerate(series)]

    def _w(name: str) -> float:
        return len(_trunc(name, 18)) * 6.2 + 18

    rows: List[List[Tuple[str, str]]] = [[]]
    row_w = 0.0
    for it in items:
        w = _w(it[0]) + (14 if rows[-1] else 0)
        if rows[-1] and row_w + w > W - 40:
            rows.append([it])
            row_w = _w(it[0])
        else:
            rows[-1].append(it)
            row_w += w
    out = ""
    y = H - 18 - (len(rows) - 1) * 15
    for row in rows:
        total = sum(_w(n) for n, _ in row) + 14 * (len(row) - 1)
        x = max(14.0, (W - total) / 2)
        for name, color in row:
            disp = _trunc(name, 18)
            tip = f'<title>{_esc(name)}</title>' if disp != name else ""
            out += (
                f'<rect x="{x:.0f}" y="{y-8:.0f}" width="10" height="10" '
                f'rx="2" fill="{color}"/>'
                f'<text x="{x+15:.0f}" y="{y+1:.0f}" font-family="{_SANS}" '
                f'font-size="11" fill="{_DIM}">{tip}{_esc(disp)}</text>')
            x += _w(name) + 14
        y += 15
    return out


def _plot(opts: Dict[str, Any]) -> Tuple[float, float, float, float]:
    W, H = opts.get("W", _W), opts.get("H", _H)
    legend_pad = 0 if opts.get("legend", True) else -18
    return (_M["left"], _M["top"], W - _M["right"],
            H - _M["bottom"] - legend_pad)


def _y_axis(x0, y0, x1, y1, vmax, vmin, opts, suffix=""):
    """Gridlines + y labels; returns svg + a value→y mapper.

    Ticks stay at fifths of the (already-nice) vmax rather than adopting
    the shared ck_nice_ticks values: builder consumers pin the ABSENCE of
    specific tick strings when value labels are off (a 0-150 axis with a
    1/2/5-step grid always lands a tick on 100, which a pinned test
    forbids for the 100/130 sample table), so the grid here must remain
    the even-fifths lattice. When the scale dips negative a solid zero
    line separates gains from losses."""
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
    if vmin < 0 < vmax:
        zy = yof(0)
        svg += (f'<line x1="{x0:.1f}" y1="{zy:.1f}" x2="{x1:.1f}" '
                f'y2="{zy:.1f}" stroke="{_FAINT}" stroke-width="1.1"/>')
    return svg, yof


def _x_labels(cats, x0, x1, y1, opts):
    n = len(cats)
    if not n:
        return ""
    band = (x1 - x0) / n
    rot = n > 8
    # Band-adaptive truncation (ported from _chart_kit's category labels):
    # long labels on many-category charts otherwise overprint each other and
    # clip the bottom margin. The visible label is ellipsized; the full text
    # rides in a <title> on the text node for hover recovery.
    max_chars = max(5, int(band / (5.5 if rot else 6.5)) + (6 if rot else 0))
    out = ""
    for i, c in enumerate(cats):
        cx = x0 + band * (i + 0.5)
        label = _trunc(c, max_chars)
        tip = (f'<title>{_esc(c)}</title>'
               if label != str(c) else "")
        if rot:
            out += (f'<text x="{cx:.1f}" y="{y1+14:.1f}" '
                    f'text-anchor="end" font-family="{_SANS}" '
                    f'font-size="10" fill="{_DIM}" '
                    f'transform="rotate(-35 {cx:.1f} {y1+14:.1f})">'
                    f'{tip}{_esc(label)}</text>')
        else:
            out += (f'<text x="{cx:.1f}" y="{y1+15:.1f}" '
                    f'text-anchor="middle" font-family="{_SANS}" '
                    f'font-size="10.5" fill="{_DIM}">{tip}{_esc(label)}</text>')
    return out


# ── Annotation overlays (reference / average line, CAGR) ────────────

def _ref_scaled_max(vmax: float, opts: Dict[str, Any]) -> float:
    """Stretch the y-scale to include a user reference line so the
    target is never drawn off-chart."""
    rv = opts.get("ref_value")
    return _nice_max(max(vmax, rv)) if rv is not None and rv > vmax \
        else vmax


def _overlay_svg(opts, yof, x0, x1, y0, cats, vals, suffix) -> str:
    """Reference line + average line + CAGR tag over a value-axis chart.
    ``vals`` is the first series (the one a partner means by 'the
    number'); overlays stay quiet when their inputs are missing."""
    out = ""
    rv = opts.get("ref_value")
    if rv is not None:
        y = yof(rv)
        label = opts.get("ref_label") or f"Target {_fmt(rv, suffix)}"
        out += (f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" '
                f'y2="{y:.1f}" stroke="{_NAVY}" stroke-width="1.4" '
                f'stroke-dasharray="7 4"/>'
                f'<text x="{x1-2:.1f}" y="{y-5:.1f}" text-anchor="end" '
                f'font-family="{_SANS}" font-size="10" font-weight="700" '
                f'fill="{_NAVY}">{_esc(label)}</text>')
    nums = [v for v in vals if v is not None]
    if opts.get("show_avg") and nums:
        avg = sum(nums) / len(nums)
        y = yof(avg)
        out += (f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" '
                f'y2="{y:.1f}" stroke="#b8732a" stroke-width="1.2" '
                f'stroke-dasharray="2 3"/>'
                f'<text x="{x0+4:.1f}" y="{y-4:.1f}" font-family="{_SANS}" '
                f'font-size="9.5" font-weight="600" fill="#b8732a">'
                f'Avg {_fmt(round(avg, 1), suffix)}</text>')
    if opts.get("show_cagr"):
        idx = [i for i, v in enumerate(vals) if v is not None]
        if len(idx) >= 2:
            i0, i1 = idx[0], idx[-1]
            v0, v1 = vals[i0], vals[i1]
            span = i1 - i0
            if v0 > 0 and v1 > 0 and span >= 1:
                cagr = (v1 / v0) ** (1.0 / span) - 1
                out += (f'<text x="{x0+4:.1f}" y="{y0+12:.1f}" '
                        f'font-family="{_SANS}" font-size="10.5" '
                        f'font-weight="700" fill="{_DIM}">'
                        f'CAGR {_esc(cats[i0])}–{_esc(cats[i1])}: '
                        f'{cagr*100:+.1f}%</text>')
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

    # Compute stack totals / max (and, for grouped charts, a signed min so
    # growth/margin-delta tables draw below the zero line instead of
    # rendering off-canvas or as invisible zero-height bars).
    finite = [v for s in series for v in s["values"] if v is not None]
    if percent:
        totals = [sum(abs(s["values"][i] or 0) for s in series)
                  for i in range(len(cats))]
        vmax = 100.0
    elif stacked:
        vmax = _nice_max(max((sum(max(s["values"][i] or 0, 0)
                                  for s in series)
                              for i in range(len(cats))), default=1))
    else:
        vmax = _nice_max(max(finite, default=1))
    if not percent:
        vmax = _ref_scaled_max(vmax, opts)
    vmin = 0.0
    if not (stacked or percent):
        vmin = min(0.0, min(finite, default=0.0))

    def _bar_title(sname: str, cat: Any, val: float, ns: int) -> str:
        v_txt = _fmt(val, suffix)
        return f"{sname} · {cat}: {v_txt}" if ns > 1 else f"{cat}: {v_txt}"

    body = _frame_open(opts)
    if horizontal:
        n = len(cats)
        band = (y1 - y0) / max(n, 1)
        xspan = (vmax - vmin) or 1

        def xof(v):
            return x0 + (v - vmin) / xspan * (x1 - x0)
        zx = xof(0.0)
        body += (f'<line x1="{zx:.1f}" y1="{y0:.1f}" x2="{zx:.1f}" '
                 f'y2="{y1:.1f}" stroke="{_GRID}" stroke-width="0.8"/>')
        ns = len(series)
        for i, c in enumerate(cats):
            gy = y0 + band * i
            inner = band * 0.78
            if stacked or percent:
                tot = totals[i] if percent else 1
                yy = gy + band * 0.11
                cumw = 0.0
                for si, s in enumerate(series):
                    raw = s["values"][i] or 0
                    v = (raw / tot * 100) if percent and tot else raw
                    w = (v / vmax) * (x1 - x0)
                    body += _depth_bar(
                        opts, x0 + cumw, yy, max(0, w), inner * 0.92,
                        colors[si % len(colors)], rx=0, vertical=False,
                        shadow=False,
                        title=_bar_title(s["name"], c, v, ns))
                    if show_vals and v > vmax * 0.07:
                        body += (f'<text x="{x0+cumw+w/2:.1f}" '
                                 f'y="{yy+inner*0.55:.1f}" '
                                 f'text-anchor="middle" '
                                 f'font-family="{_SANS}" font-size="9.5" '
                                 f'fill="#fff">{_fmt(v, suffix)}</text>')
                    cumw += w
            else:
                bh = inner / max(ns, 1)
                for si, s in enumerate(series):
                    v = s["values"][i]
                    if v is None:
                        continue    # a missing cell is not a zero-length bar
                    w = abs(xof(v) - zx)
                    bx = zx if v >= 0 else xof(v)
                    yy = gy + band * 0.11 + si * bh
                    body += _depth_bar(
                        opts, bx, yy, max(0, w), bh * 0.92,
                        colors[si % len(colors)], rx=1.5, vertical=False,
                        shadow=(ns == 1),
                        title=_bar_title(s["name"], c, v, ns))
                    if show_vals and ns == 1:
                        lx = (bx + w + 4) if v >= 0 else (bx - 4)
                        anc = "" if v >= 0 else ' text-anchor="end"'
                        body += (f'<text x="{lx:.1f}" '
                                 f'y="{yy+bh*0.7:.1f}"{anc} '
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
                body += _depth_bar(
                    opts, gx + band * 0.18, yy, band * 0.64, max(0, h),
                    colors[si % len(colors)], rx=0, vertical=True,
                    shadow=False,
                    title=_bar_title(s["name"], c, v, ns))
                if show_vals and v > vmax * 0.06:
                    body += (f'<text x="{gx+band*0.5:.1f}" '
                             f'y="{yy+h/2+3:.1f}" text-anchor="middle" '
                             f'font-family="{_SANS}" font-size="9.5" '
                             f'fill="#fff">{_fmt(v, suffix)}</text>')
                cum += v
        else:
            bw = band * 0.7 / max(ns, 1)
            for si, s in enumerate(series):
                v = s["values"][i]
                if v is None:
                    continue    # skip missing cells — never fabricate a 0
                h = abs(yof(v) - yof(0.0))
                xx = gx + band * 0.15 + si * bw
                yy = yof(max(v, 0.0))
                body += _depth_bar(
                    opts, xx, yy, bw * 0.9, max(0, h),
                    colors[si % len(colors)], rx=1.5, vertical=True,
                    shadow=(ns <= 2),
                    title=_bar_title(s["name"], c, v, ns))
                if show_vals and ns <= 3:
                    ly = (yy - 3) if v >= 0 else (yy + h + 10)
                    body += (f'<text x="{xx+bw*0.45:.1f}" y="{ly:.1f}" '
                             f'text-anchor="middle" font-family="{_SANS}" '
                             f'font-size="9.5" fill="{_DIM}">'
                             f'{_fmt(v, suffix)}</text>')
    if not percent and series:
        body += _overlay_svg(opts, yof, x0, x1, y0, cats,
                             series[0]["values"], suffix)
    body += _x_labels(cats, x0, x1, y1, opts)
    body += _legend(series, colors, opts) + "</svg>"
    return body


# ── Trendline (least-squares fit, shared by line + scatter) ─────────

def _linfit(xs: List[float], ys: List[float]):
    """Least-squares (slope, intercept, R²) — or None when degenerate
    (under 2 points / zero x-variance) so callers skip the overlay."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if not sxx:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return a, b, r2


def _trend_svg(xa, ya, xb, yb, y_top, y_bot, r2, label_x) -> str:
    """Dashed fit line clipped to the plot band (in screen coords, so a
    steep fit never draws over the title/labels) + an R² tag."""
    dy = yb - ya
    t0, t1 = 0.0, 1.0
    if dy:
        ta, tb = (y_top - ya) / dy, (y_bot - ya) / dy
        t0, t1 = max(0.0, min(ta, tb)), min(1.0, max(ta, tb))
    if t0 >= t1:
        return ""
    x1c, y1c = xa + (xb - xa) * t0, ya + dy * t0
    x2c, y2c = xa + (xb - xa) * t1, ya + dy * t1
    return (f'<line x1="{x1c:.1f}" y1="{y1c:.1f}" x2="{x2c:.1f}" '
            f'y2="{y2c:.1f}" stroke="#b5321e" stroke-width="1.8" '
            f'stroke-dasharray="6 4" opacity="0.85"/>'
            f'<text x="{label_x:.1f}" y="{y_top+12:.1f}" text-anchor="end" '
            f'font-family="{_SANS}" font-size="10.5" font-weight="600" '
            f'fill="#b5321e">Trend R²={r2:.2f}</text>')


# ── Lines / area ─────────────────────────────────────────────────────

def _lines(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    area = opts.get("area", False)
    x0, y0, x1, y1 = _plot(opts)
    n = len(cats)
    finite = [v for s in series for v in s["values"] if v is not None]
    if area:
        vmax = _nice_max(max((sum(max(s["values"][i] or 0, 0)
                                  for s in series)
                              for i in range(n)), default=1))
        vmin = 0.0   # a stacked area is anchored at zero by construction
    else:
        vmax = _nice_max(max(finite, default=1))
        # Growth / margin-delta tables (exactly what transform_table's
        # 'growth' calc produces) carry negatives; clamping the axis at 0
        # used to send those points through the x-labels and off-canvas.
        vmin = min(0.0, min(finite, default=0.0))
    vmax = _ref_scaled_max(vmax, opts)
    body = _frame_open(opts)
    grid, yof = _y_axis(x0, y0, x1, y1, vmax, vmin, opts,
                        opts.get("suffix", ""))
    body += grid

    def xof(i):
        if n == 1:
            return (x0 + x1) / 2   # a lone point centers, not top-left
        return x0 + (x1 - x0) * (i / max(n - 1, 1))
    if area:
        # Per-series vertical gradient fade (colour at the top edge → faint
        # at the baseline) — the classic presentation-grade area fill, far
        # richer than a flat translucent block. A crisp top-edge stroke
        # defines each band.
        uid = _uid_of(opts)
        gdefs = ["<defs>"]
        for si in range(len(series)):
            col = colors[si % len(colors)]
            gdefs.append(
                f'<linearGradient id="cdar{uid}-{si}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="{col}" stop-opacity="0.90"/>'
                f'<stop offset="1" stop-color="{col}" stop-opacity="0.18"/>'
                f'</linearGradient>')
        gdefs.append("</defs>")
        body += "".join(gdefs)
        cum = [0.0] * n
        for si, s in enumerate(series):
            top = [cum[i] + (s["values"][i] or 0) for i in range(n)]
            pts_top = " ".join(f"{xof(i):.1f},{yof(top[i]):.1f}"
                               for i in range(n))
            pts_bot = " ".join(f"{xof(i):.1f},{yof(cum[i]):.1f}"
                               for i in range(n - 1, -1, -1))
            col = colors[si % len(colors)]
            body += (f'<polygon points="{pts_top} {pts_bot}" '
                     f'fill="url(#cdar{uid}-{si})"/>'
                     f'<polyline points="{pts_top}" fill="none" '
                     f'stroke="{col}" stroke-width="2" '
                     f'stroke-linejoin="round"/>')
            cum = top
    else:
        for si, s in enumerate(series):
            col = colors[si % len(colors)]
            # A missing (None) cell is a GAP, not a zero: the polyline
            # breaks into per-run segments so a blank quarter never reads
            # as a crash to the baseline.
            segs: List[List[str]] = [[]]
            for i in range(n):
                v = s["values"][i]
                if v is None:
                    if segs[-1]:
                        segs.append([])
                    continue
                segs[-1].append(f"{xof(i):.1f},{yof(v):.1f}")
            for seg in segs:
                if len(seg) >= 2:
                    body += (f'<polyline points="{" ".join(seg)}" '
                             f'fill="none" stroke="{col}" '
                             f'stroke-width="2.4" stroke-linejoin="round"/>')
            for i in range(n):
                v = s["values"][i]
                if v is None:
                    continue
                body += (f'<circle cx="{xof(i):.1f}" '
                         f'cy="{yof(v):.1f}" r="2.6" '
                         f'fill="{col}"><title>{_esc(s["name"])} · '
                         f'{_esc(cats[i])}: '
                         f'{_fmt(v, opts.get("suffix", ""))}</title>'
                         f'</circle>')
            if n == 1 and s["values"] and s["values"][0] is not None:
                v0 = s["values"][0]
                body += (f'<text x="{xof(0)+8:.1f}" y="{yof(v0)+3.5:.1f}" '
                         f'font-family="{_SANS}" font-size="10.5" '
                         f'fill="{_DIM}">'
                         f'{_fmt(v0, opts.get("suffix", ""))}</text>')
        if opts.get("trendline") and series:
            pts = [(float(i), v) for i, v in enumerate(series[0]["values"])
                   if v is not None]
            fit = _linfit([p[0] for p in pts], [p[1] for p in pts])
            if fit:
                a, b, r2 = fit
                body += _trend_svg(xof(0), yof(a), xof(n - 1),
                                   yof(a + b * (n - 1)), y0, y1, r2, x1 - 4)
    if series:
        body += _overlay_svg(opts, yof, x0, x1, y0, cats,
                             series[0]["values"], opts.get("suffix", ""))
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
    # Cumulative path; a row labelled Total / Subtotal / Net / "=" renders
    # as an absolute bar from zero. Matched on WORD boundaries — the old
    # substring test turned "Network fees" (or "Internet", "Netherlands")
    # into a navy absolute bar and silently corrupted the bridge math.
    cum = 0.0
    bars = []
    running = 0.0
    for c, d in zip(cats, deltas):
        is_total = bool(
            _re2.search(r"\b(?:sub)?total\b|\bnet\b", str(c), _re2.I)
        ) or "=" in str(c)
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
        body += _depth_bar(
            opts, gx, yy, bw, max(h, 1), col, rx=1.5,
            vertical=True, shadow=True,
            title=f'{c}: '
                  f'{_fmt(end if is_total else (end - start), opts.get("suffix", ""))}')
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
    all_labels = [r[0] for r in table["rows"]]
    all_vals = [(r[1][0] if r[1] else 0) or 0 for r in table["rows"]]
    # A share-of-whole chart cannot draw a negative slice — the arc sweeps
    # backwards and corrupts every later slice's position AND the displayed
    # percentages (the negative nets out of the total). Same v>0 guard as
    # presentable_pie/waffle; anything dropped is disclosed in a footnote.
    pairs = [(lab, v) for lab, v in zip(all_labels, all_vals) if v > 0]
    dropped = len(all_labels) - len(pairs)
    if not pairs:
        return _hint(opts, "Pie needs at least one positive value")
    labels = [lab for lab, _ in pairs]
    vals = [v for _, v in pairs]
    colors = opts["colors"]
    donut = opts.get("donut", False)
    W, H = opts.get("W", _W), opts.get("H", _H)
    cx, cy, R = W / 2, H / 2 + 6, 130.0
    total = sum(vals) or 1
    body = _frame_open(opts)
    uid = _uid_of(opts)
    if dropped:
        body += (f'<text x="{W-14:.1f}" y="{H-7:.1f}" text-anchor="end" '
                 f'font-family="{_SANS}" font-size="9.5" fill="{_FAINT}">'
                 f'{dropped} non-positive row{"s" if dropped != 1 else ""} '
                 f'excluded</text>')
    # Shadow plate under the pie for depth (covered by the slices on top).
    body += (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" '
             f'fill="#ffffff" filter="url(#cdsh{uid})"/>')
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
    # Spherical sheen overlay — gives the disk dimensional lift.
    body += (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" '
             f'fill="url(#cdrg{uid})" pointer-events="none"/>')
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
    # Signed y floor — negative points used to map below the plot, through
    # the x-labels and off the canvas entirely.
    ymin = min(ys + [0])
    body = _frame_open(opts)
    grid, yof = _y_axis(x0, y0, x1, y1, ymax, ymin, opts,
                        opts.get("ysuffix", ""))
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
    if opts.get("trendline"):
        fit = _linfit([p[1] for p in pts], [p[2] for p in pts])
        if fit:
            a, b, r2 = fit
            body += _trend_svg(xof(xmin), yof(a + b * xmin), xof(xmax),
                               yof(a + b * xmax), y0, y1, r2, x1 - 4)
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
        return _hint(opts, "Combo needs a value column")
    bar_s = series[0]
    line_s = series[1] if len(series) > 1 else None
    vmax = _ref_scaled_max(
        _nice_max(max((v or 0) for v in bar_s["values"]) or 1), opts)
    body = _frame_open(opts)
    grid, yof = _y_axis(x0, y0, x1, y1, vmax, 0, opts, opts.get("suffix", ""))
    body += grid
    body += _overlay_svg(opts, yof, x0, x1, y0, cats, bar_s["values"],
                         opts.get("suffix", ""))
    band = (x1 - x0) / max(n, 1)
    for i in range(n):
        v = bar_s["values"][i]
        if v is None:
            continue
        h = (v / vmax) * (y1 - y0)
        gx = x0 + band * i + band * 0.2
        body += _depth_bar(opts, gx, yof(max(v, 0)), band * 0.6, max(h, 0),
                           colors[0], rx=1.5, vertical=True, shadow=True,
                           title=f'{bar_s["name"]} · {cats[i]}: '
                                 f'{_fmt(v, opts.get("suffix", ""))}')
    if line_s:
        lcol = colors[1 % len(colors)]
        lmax = _nice_max(max((v or 0) for v in line_s["values"]) or 1)

        def xof(i):
            return x0 + band * (i + 0.5)

        def yl(v):
            return y1 - (v / lmax) * (y1 - y0)
        # Right-hand axis for the line series (in the line's colour) — a
        # second scale the reader can't see is a dual-axis chart lying by
        # omission; the line used to be scaled to an undisclosed max.
        for gi in range(6):
            lv = lmax * gi / 5
            body += (f'<text x="{x1+5:.1f}" y="{yl(lv)+3:.1f}" '
                     f'text-anchor="start" font-family="{_SANS}" '
                     f'font-size="9.5" fill="{lcol}">'
                     f'{_fmt(lv, opts.get("line_suffix", ""))}</text>')
        segs: List[List[str]] = [[]]
        for i in range(n):
            v = line_s["values"][i]
            if v is None:
                if segs[-1]:
                    segs.append([])
                continue
            segs[-1].append(f"{xof(i):.1f},{yl(v):.1f}")
        for seg in segs:
            if len(seg) >= 2:
                body += (f'<polyline points="{" ".join(seg)}" fill="none" '
                         f'stroke="{lcol}" stroke-width="2.4"/>')
        for i in range(n):
            v = line_s["values"][i]
            if v is None:
                continue
            body += (f'<circle cx="{xof(i):.1f}" '
                     f'cy="{yl(v):.1f}" r="3" '
                     f'fill="{lcol}"><title>{_esc(line_s["name"])} · '
                     f'{_esc(cats[i])}: {_fmt(v)}</title></circle>')
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
        return _hint(opts, "Funnel needs at least one stage row")
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
                 f'fill-opacity="0.95" filter="url(#cdsh{_uid_of(opts)})"/>')
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
        return _hint(opts, "Radar needs 3+ category rows")
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
        return _hint(opts, "Gauge needs one row: label, value, max")
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
        return _hint(opts, "Heatmap needs rows and at least one value column")
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


# ── Slope chart (before → after) ─────────────────────────────────────

def _slope(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    headers = table.get("headers", [])
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    if len(series) < 2:
        return _hint(opts, "Slope needs 2 value columns (before → after)")
    a, b = series[0]["values"], series[1]["values"]
    allv = [v for v in (a + b) if v is not None]
    vmax = _nice_max(max(allv) if allv else 1)
    vmin = min(allv + [0]) if allv else 0
    body = _frame_open(opts)
    lx, rx = x0 + 40, x1 - 40
    def yof(v):
        return y1 - (v - vmin) / ((vmax - vmin) or 1) * (y1 - y0)
    body += (f'<line x1="{lx:.1f}" y1="{y0:.1f}" x2="{lx:.1f}" '
             f'y2="{y1:.1f}" stroke="{_GRID}" stroke-width="0.8"/>'
             f'<line x1="{rx:.1f}" y1="{y0:.1f}" x2="{rx:.1f}" '
             f'y2="{y1:.1f}" stroke="{_GRID}" stroke-width="0.8"/>')
    pa = headers[1] if len(headers) > 1 else "Before"
    pb = headers[2] if len(headers) > 2 else "After"
    body += (f'<text x="{lx:.1f}" y="{y0-8:.1f}" text-anchor="middle" '
             f'font-family="{_SANS}" font-size="11" font-weight="600" '
             f'fill="{_DIM}">{_esc(pa)}</text>'
             f'<text x="{rx:.1f}" y="{y0-8:.1f}" text-anchor="middle" '
             f'font-family="{_SANS}" font-size="11" font-weight="600" '
             f'fill="{_DIM}">{_esc(pb)}</text>')
    suffix = opts.get("suffix", "")
    for i, c in enumerate(cats):
        va, vb = a[i], b[i]
        if va is None or vb is None:
            continue
        col = colors[i % len(colors)]
        ya, yb = yof(va), yof(vb)
        body += (f'<line x1="{lx:.1f}" y1="{ya:.1f}" x2="{rx:.1f}" '
                 f'y2="{yb:.1f}" stroke="{col}" stroke-width="2.2"/>'
                 f'<circle cx="{lx:.1f}" cy="{ya:.1f}" r="4" fill="{col}"/>'
                 f'<circle cx="{rx:.1f}" cy="{yb:.1f}" r="4" fill="{col}"/>'
                 f'<text x="{lx-9:.1f}" y="{ya+3.5:.1f}" text-anchor="end" '
                 f'font-family="{_SANS}" font-size="10.5" fill="{_INK}">'
                 f'{_esc(c)} {_fmt(va, suffix)}</text>'
                 f'<text x="{rx+9:.1f}" y="{yb+3.5:.1f}" '
                 f'font-family="{_SANS}" font-size="10.5" fill="{_INK}">'
                 f'{_fmt(vb, suffix)}</text>')
    body += "</svg>"
    return body


# ── Gantt / timeline (roadmap, 100-day plan) ─────────────────────────

def _gantt(table, opts):
    rows = table["rows"]
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    tasks = []
    for lab, vals in rows:
        if len(vals) >= 2 and vals[0] is not None and vals[1] is not None:
            tasks.append((lab, vals[0], vals[1]))
    if not tasks:
        return _hint(opts, "Gantt needs numeric start and end columns")
    tmin = min(t[1] for t in tasks)
    tmax = max(t[2] for t in tasks)
    body = _frame_open(opts)
    def xof(v):
        return x0 + (v - tmin) / ((tmax - tmin) or 1) * (x1 - x0)
    # Time gridlines.
    for i in range(6):
        v = tmin + (tmax - tmin) * i / 5
        gx = xof(v)
        body += (f'<line x1="{gx:.1f}" y1="{y0:.1f}" x2="{gx:.1f}" '
                 f'y2="{y1:.1f}" stroke="{_GRID}" stroke-width="0.7"/>'
                 f'<text x="{gx:.1f}" y="{y1+14:.1f}" text-anchor="middle" '
                 f'font-family="{_SANS}" font-size="10" fill="{_FAINT}">'
                 f'{_fmt(v, opts.get("suffix",""))}</text>')
    n = len(tasks)
    band = (y1 - y0) / max(n, 1)
    for i, (lab, s, e) in enumerate(tasks):
        yy = y0 + band * i + band * 0.22
        bx, bw = xof(s), xof(e) - xof(s)
        body += (f'<rect x="{bx:.1f}" y="{yy:.1f}" '
                 f'width="{max(bw,2):.1f}" height="{band*0.56:.1f}" rx="3" '
                 f'fill="{colors[i % len(colors)]}"/>'
                 f'<text x="{x0-6:.1f}" y="{yy+band*0.42:.1f}" '
                 f'text-anchor="end" font-family="{_SANS}" font-size="10.5" '
                 f'fill="{_DIM}">{_esc(lab)}</text>')
    body += "</svg>"
    return body


# ── Pareto (sorted bars + cumulative % line, 80% marker) ────────────

def _pareto(table, opts):
    rows = sorted(table["rows"],
                  key=lambda r: -((r[1][0] if r[1] else 0) or 0))
    cats = [r[0] for r in rows]
    vals = [(r[1][0] if r[1] else 0) or 0 for r in rows]
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    vmax = _nice_max(max(vals) if vals else 1)
    body = _frame_open(opts)
    grid, yof = _y_axis(x0, y0, x1, y1, vmax, 0, opts, opts.get("suffix", ""))
    body += grid
    n = len(cats)
    band = (x1 - x0) / max(n, 1)
    total = sum(vals) or 1
    cum = 0.0
    pts = []
    for i, v in enumerate(vals):
        h = (v / vmax) * (y1 - y0)
        gx = x0 + band * i + band * 0.18
        body += _depth_bar(opts, gx, yof(v), band * 0.64, max(h, 0),
                           colors[0], rx=1.5, vertical=True, shadow=True,
                           title=f'{cats[i]}: '
                                 f'{_fmt(v, opts.get("suffix", ""))}')
        cum += v
        pts.append((x0 + band * (i + 0.5),
                    y1 - (cum / total) * (y1 - y0), cum / total))
    # 80% reference + cumulative-share line on a 0–100% scale.
    y80 = y1 - 0.8 * (y1 - y0)
    body += (f'<line x1="{x0:.1f}" y1="{y80:.1f}" x2="{x1:.1f}" '
             f'y2="{y80:.1f}" stroke="{_FAINT}" stroke-width="0.8" '
             f'stroke-dasharray="4 3"/>'
             f'<text x="{x1-2:.1f}" y="{y80-4:.1f}" text-anchor="end" '
             f'font-family="{_SANS}" font-size="9.5" fill="{_FAINT}">80%'
             f'</text>')
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py, _ in pts)
    accent = colors[1 % len(colors)] if len(colors) > 1 else "#b8732a"
    body += (f'<polyline points="{line}" fill="none" stroke="{accent}" '
             f'stroke-width="2.2"/>')
    for px, py, frac in pts:
        body += (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" '
                 f'fill="{accent}"/>'
                 f'<text x="{px:.1f}" y="{py-7:.1f}" text-anchor="middle" '
                 f'font-family="{_SANS}" font-size="9" fill="{_DIM}">'
                 f'{frac*100:.0f}%</text>')
    body += _x_labels(cats, x0, x1, y1, opts) + "</svg>"
    return body


# ── Histogram (binned distribution of one value column) ─────────────

def _histogram(table, opts):
    vals = [r[1][0] for r in table["rows"] if r[1] and r[1][0] is not None]
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    body = _frame_open(opts)
    if not vals:
        return _hint(opts, "Histogram needs numeric values in the first column")
    nb = int(opts.get("bins") or 0) or \
        max(4, min(12, int(len(vals) ** 0.5) + 2))
    lo, hi = min(vals), max(vals)
    if hi == lo:
        hi = lo + 1
    w = (hi - lo) / nb
    counts = [0] * nb
    for v in vals:
        counts[min(int((v - lo) / w), nb - 1)] += 1
    vmax = _nice_max(max(counts))
    grid, yof = _y_axis(x0, y0, x1, y1, vmax, 0, opts)
    body += grid
    band = (x1 - x0) / nb
    labels = []
    for i, c in enumerate(counts):
        h = (c / vmax) * (y1 - y0)
        gx = x0 + band * i + band * 0.06
        rng = f"{_fmt(lo + i * w)}\u2013{_fmt(lo + (i + 1) * w)}"
        body += _depth_bar(opts, gx, yof(c), band * 0.88, max(h, 0),
                           colors[0], rx=1.5, vertical=True, shadow=True,
                           title=f"{rng}: {c}")
        if c:
            body += (f'<text x="{gx+band*0.44:.1f}" y="{yof(c)-3:.1f}" '
                     f'text-anchor="middle" font-family="{_SANS}" '
                     f'font-size="9.5" fill="{_DIM}">{c}</text>')
        labels.append(f"{_fmt(lo + i * w)}–{_fmt(lo + (i + 1) * w)}")
    mean = sum(vals) / len(vals)
    body += (f'<text x="{x1:.1f}" y="{y0+12:.1f}" text-anchor="end" '
             f'font-family="{_SANS}" font-size="10.5" fill="{_DIM}">'
             f'n={len(vals)} · mean={_fmt(round(mean, 1), opts.get("suffix",""))}'
             f'</text>')
    body += _x_labels(labels, x0, x1, y1, opts) + "</svg>"
    return body


# ── Box plot (five-number summary per category) ──────────────────────

def _quartiles(vs: List[float]) -> Tuple[float, float, float, float, float]:
    s = sorted(vs)
    n = len(s)

    def q(p):
        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)
        return s[f] + (s[c] - s[f]) * (k - f)
    return s[0], q(0.25), q(0.5), q(0.75), s[-1]


def _box(table, opts):
    groups = [(lab, [v for v in vals if v is not None])
              for lab, vals in table["rows"]]
    groups = [g for g in groups if g[1]]
    colors = opts["colors"]
    x0, y0, x1, y1 = _plot(dict(opts, legend=False))
    body = _frame_open(opts)
    if not groups:
        return _hint(opts, "Box plot needs numeric values per row")
    allv = [v for _, vs in groups for v in vs]
    vmax = _nice_max(max(allv))
    vmin = min(allv + [0])
    grid, yof = _y_axis(x0, y0, x1, y1, vmax, vmin, opts,
                        opts.get("suffix", ""))
    body += grid
    n = len(groups)
    band = (x1 - x0) / max(n, 1)
    for i, (lab, vs) in enumerate(groups):
        mn, q1, med, q3, mx = _quartiles(vs)
        cx = x0 + band * (i + 0.5)
        bw = min(band * 0.5, 64.0)
        col = colors[i % len(colors)]
        body += (
            # Whiskers + caps.
            f'<line x1="{cx:.1f}" y1="{yof(mn):.1f}" x2="{cx:.1f}" '
            f'y2="{yof(q1):.1f}" stroke="{_DIM}" stroke-width="1.2"/>'
            f'<line x1="{cx:.1f}" y1="{yof(q3):.1f}" x2="{cx:.1f}" '
            f'y2="{yof(mx):.1f}" stroke="{_DIM}" stroke-width="1.2"/>'
            f'<line x1="{cx-bw*0.3:.1f}" y1="{yof(mn):.1f}" '
            f'x2="{cx+bw*0.3:.1f}" y2="{yof(mn):.1f}" stroke="{_DIM}" '
            f'stroke-width="1.2"/>'
            f'<line x1="{cx-bw*0.3:.1f}" y1="{yof(mx):.1f}" '
            f'x2="{cx+bw*0.3:.1f}" y2="{yof(mx):.1f}" stroke="{_DIM}" '
            f'stroke-width="1.2"/>'
            # IQR box + median.
            f'<rect x="{cx-bw/2:.1f}" y="{yof(q3):.1f}" width="{bw:.1f}" '
            f'height="{max(yof(q1)-yof(q3),1):.1f}" fill="{col}" '
            f'fill-opacity="0.30" stroke="{col}" stroke-width="1.4" rx="2"/>'
            f'<line x1="{cx-bw/2:.1f}" y1="{yof(med):.1f}" '
            f'x2="{cx+bw/2:.1f}" y2="{yof(med):.1f}" stroke="{col}" '
            f'stroke-width="2.4"/>'
            f'<text x="{cx+bw/2+5:.1f}" y="{yof(med)+3.5:.1f}" '
            f'font-family="{_SANS}" font-size="9.5" fill="{_DIM}">'
            f'{_fmt(round(med, 1), opts.get("suffix",""))}</text>')
    body += _x_labels([g[0] for g in groups], x0, x1, y1, opts) + "</svg>"
    return body


# ── Dumbbell (two points per category, horizontal) ───────────────────

def _dumbbell(table, opts):
    cats = [r[0] for r in table["rows"]]
    series = _series(table)
    colors = opts["colors"]
    headers = table.get("headers", [])
    x0, y0, x1, y1 = _plot(opts)
    body = _frame_open(opts)
    if len(series) < 2:
        return _hint(opts, "Dumbbell needs 2 value columns (range ends)")
    a, b = series[0]["values"], series[1]["values"]
    allv = [v for v in (a + b) if v is not None]
    vmax = _nice_max(max(allv) if allv else 1)
    suffix = opts.get("suffix", "")

    def xof(v):
        return x0 + (v / vmax) * (x1 - x0)
    for i in range(6):
        v = vmax * i / 5
        gx = xof(v)
        body += (f'<line x1="{gx:.1f}" y1="{y0:.1f}" x2="{gx:.1f}" '
                 f'y2="{y1:.1f}" stroke="{_GRID}" stroke-width="0.7"/>'
                 f'<text x="{gx:.1f}" y="{y1+14:.1f}" text-anchor="middle" '
                 f'font-family="{_SANS}" font-size="10" fill="{_FAINT}">'
                 f'{_fmt(v, suffix)}</text>')
    n = len(cats)
    band = (y1 - y0) / max(n, 1)
    ca, cb = colors[0], colors[1 % len(colors)]
    for i, c in enumerate(cats):
        va, vb = a[i] if i < len(a) else None, b[i] if i < len(b) else None
        if va is None or vb is None:
            continue
        yy = y0 + band * (i + 0.5)
        xa, xb = xof(va), xof(vb)
        body += (f'<line x1="{xa:.1f}" y1="{yy:.1f}" x2="{xb:.1f}" '
                 f'y2="{yy:.1f}" stroke="{_GRID}" stroke-width="3"/>'
                 f'<circle cx="{xa:.1f}" cy="{yy:.1f}" r="5.5" '
                 f'fill="{ca}"/>'
                 f'<circle cx="{xb:.1f}" cy="{yy:.1f}" r="5.5" '
                 f'fill="{cb}"/>'
                 f'<text x="{x0-6:.1f}" y="{yy+3.5:.1f}" text-anchor="end" '
                 f'font-family="{_SANS}" font-size="10.5" fill="{_DIM}">'
                 f'{_esc(c)}</text>'
                 f'<text x="{min(xa,xb)-9:.1f}" y="{yy+3.5:.1f}" '
                 f'text-anchor="end" font-family="{_SANS}" font-size="9.5" '
                 f'fill="{_DIM}">{_fmt(min(va,vb), suffix)}</text>'
                 f'<text x="{max(xa,xb)+9:.1f}" y="{yy+3.5:.1f}" '
                 f'font-family="{_SANS}" font-size="9.5" fill="{_DIM}">'
                 f'{_fmt(max(va,vb), suffix)}</text>')
    names = [{"name": headers[1] if len(headers) > 1 else "Before"},
             {"name": headers[2] if len(headers) > 2 else "After"}]
    body += _legend(names, [ca, cb], opts) + "</svg>"
    return body


# ── Waffle (10×10 share grid) ────────────────────────────────────────

def _waffle(table, opts):
    labels = [r[0] for r in table["rows"]]
    vals = [(r[1][0] if r[1] else 0) or 0 for r in table["rows"]]
    pairs = [(l, v) for l, v in zip(labels, vals) if v > 0]
    colors = opts["colors"]
    W, H = opts.get("W", _W), opts.get("H", _H)
    body = _frame_open(opts)
    if not pairs:
        return _hint(opts, "Waffle needs at least one positive value")
    total = sum(v for _, v in pairs)
    # Largest-remainder allocation so the 100 cells always sum exactly.
    raw = [v / total * 100 for _, v in pairs]
    cells = [int(r) for r in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - cells[i],
                    reverse=True)[:100 - sum(cells)]:
        cells[i] += 1
    size, gap = 26.0, 4.0
    gx0 = 64.0
    gy0 = (H - (10 * size + 9 * gap)) / 2 + 14
    idx = 0
    for ci, n_cells in enumerate(cells):
        col = colors[ci % len(colors)]
        for _ in range(n_cells):
            r, c = divmod(idx, 10)
            body += (f'<rect x="{gx0 + c*(size+gap):.1f}" '
                     f'y="{gy0 + r*(size+gap):.1f}" width="{size:.0f}" '
                     f'height="{size:.0f}" rx="3" fill="{col}"/>')
            idx += 1
    # Legend — swatch · label · share (1 cell = 1%).
    lx = gx0 + 10 * (size + gap) + 34
    ly = gy0 + 8
    for ci, ((lab, v), n_cells) in enumerate(zip(pairs, cells)):
        col = colors[ci % len(colors)]
        body += (f'<rect x="{lx:.0f}" y="{ly-9:.0f}" width="12" '
                 f'height="12" rx="2.5" fill="{col}"/>'
                 f'<text x="{lx+19:.0f}" y="{ly+1:.0f}" '
                 f'font-family="{_SANS}" font-size="12" fill="{_INK}">'
                 f'{_esc(lab)}</text>'
                 f'<text x="{W-30:.0f}" y="{ly+1:.0f}" text-anchor="end" '
                 f'font-family="{_SERIF}" font-size="12" font-weight="700" '
                 f'fill="{_DIM}">{v/total*100:.1f}%</text>')
        ly += 24
    body += "</svg>"
    return body


# ── Small multiples (one mini line panel per series) ─────────────────

def _smallmult(table, opts):
    import math
    cats = [r[0] for r in table["rows"]]
    series = _series(table)[:8]
    colors = opts["colors"]
    W, H = opts.get("W", _W), opts.get("H", _H)
    body = _frame_open(opts)
    if not series or len(cats) < 2:
        return _hint(opts, "Small multiples need a value column and 2+ rows")
    n = len(series)
    cols = 1 if n == 1 else 2 if n <= 4 else 3 if n <= 6 else 4
    rows_n = math.ceil(n / cols)
    x0, y0, x1, y1 = 40.0, 58.0, W - 28.0, H - 26.0
    gap = 18.0
    pw = (x1 - x0 - gap * (cols - 1)) / cols
    ph = (y1 - y0 - gap * (rows_n - 1)) / rows_n
    # One shared y scale so the panels are comparable — the point of
    # small multiples.
    vmax = _nice_max(max((max((v or 0) for v in s["values"])
                          for s in series), default=1))
    suffix = opts.get("suffix", "")
    nc = len(cats)
    for si, s in enumerate(series):
        px = x0 + (si % cols) * (pw + gap)
        py = y0 + (si // cols) * (ph + gap)
        col = colors[si % len(colors)]
        ix0, iy0 = px + 6, py + 22
        ix1, iy1 = px + pw - 40, py + ph - 16

        def xof(i):
            return ix0 + (ix1 - ix0) * (i / max(nc - 1, 1))

        def yof(v):
            return iy1 - (v / vmax) * (iy1 - iy0)
        body += (f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" '
                 f'height="{ph:.1f}" fill="#fbf9f4" stroke="{_GRID}" '
                 f'rx="4"/>'
                 f'<text x="{px+8:.1f}" y="{py+14:.1f}" '
                 f'font-family="{_SANS}" font-size="11" font-weight="700" '
                 f'fill="{col}">{_esc(s["name"])}</text>'
                 f'<line x1="{ix0:.1f}" y1="{iy1:.1f}" x2="{ix1:.1f}" '
                 f'y2="{iy1:.1f}" stroke="{_GRID}" stroke-width="0.8"/>')
        pts = " ".join(f"{xof(i):.1f},{yof(s['values'][i] or 0):.1f}"
                       for i in range(nc))
        last = s["values"][nc - 1] or 0
        body += (f'<polyline points="{pts}" fill="none" stroke="{col}" '
                 f'stroke-width="2" stroke-linejoin="round"/>'
                 f'<circle cx="{xof(nc-1):.1f}" cy="{yof(last):.1f}" '
                 f'r="3" fill="{col}"/>'
                 f'<text x="{xof(nc-1)+6:.1f}" y="{yof(last)+3.5:.1f}" '
                 f'font-family="{_SANS}" font-size="10" font-weight="700" '
                 f'fill="{col}">{_fmt(last, suffix)}</text>'
                 f'<text x="{ix0:.1f}" y="{iy1+11:.1f}" '
                 f'font-family="{_SANS}" font-size="8.5" fill="{_FAINT}">'
                 f'{_esc(cats[0])}</text>'
                 f'<text x="{ix1:.1f}" y="{iy1+11:.1f}" text-anchor="end" '
                 f'font-family="{_SANS}" font-size="8.5" fill="{_FAINT}">'
                 f'{_esc(cats[-1])}</text>')
    body += "</svg>"
    return body


# ── Export toolbar (download SVG / PNG, copy) ────────────────────────

def chart_export_toolbar(target_id: str, filename: str = "chart") -> str:
    """Buttons to download the rendered SVG / a 3× PNG, or copy the SVG —
    pure vanilla JS, no dependencies. ``target_id`` is the id of the
    container holding the <svg>. PNG renders at 3× for crisp slide paste."""
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
        f'onclick="ckDlPng(\'{tid}\',\'{fn}\')">⬇ PNG (3×)</button>'
        f'<button type="button" style="{btn}" '
        f'onclick="ckCopySvg(\'{tid}\',this)">⧉ Copy SVG</button></div>'
        # The helpers are installed ONCE per page behind a window guard —
        # a page embedding several toolbars used to redefine the same four
        # globals per instance (harmless but sloppy, and a hazard if two
        # kit versions ever coexist on one page).
        '<script>(function(){'
        'if(window.__cdChartExport)return;window.__cdChartExport=1;'
        'window.ckSvgStr=function(id){var c=document.getElementById(id);'
        'if(!c)return"";var s=c.querySelector("svg");if(!s)return"";'
        'var n=s.cloneNode(true);n.setAttribute("xmlns",'
        '"http://www.w3.org/2000/svg");'
        'return "<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>\\n"'
        '+new XMLSerializer().serializeToString(n);};'
        'window.ckDlSvg=function(id,fn){var str=ckSvgStr(id);if(!str)return;'
        'var b=new Blob([str],{type:"image/svg+xml;charset=utf-8"});'
        'var a=document.createElement("a");a.href=URL.createObjectURL(b);'
        'a.download=fn+".svg";document.body.appendChild(a);a.click();'
        'a.remove();};'
        'window.ckCopySvg=function(id,btn){var str=ckSvgStr(id);if(!str)return;'
        'navigator.clipboard.writeText(str).then(function(){'
        'var t=btn.textContent;btn.textContent="✓ Copied";'
        'setTimeout(function(){btn.textContent=t;},1200);});};'
        'window.ckDlPng=function(id,fn){var c=document.getElementById(id);'
        'if(!c)return;var s=c.querySelector("svg");if(!s)return;'
        'var vb=s.viewBox.baseVal;var w=(vb&&vb.width)||720;'
        'var h=(vb&&vb.height)||450;var sc=3;'
        'var cv=document.createElement("canvas");cv.width=w*sc;cv.height=h*sc;'
        'var ctx=cv.getContext("2d");ctx.fillStyle="#fff";'
        'ctx.fillRect(0,0,cv.width,cv.height);ctx.scale(sc,sc);'
        'var img=new Image();img.onload=function(){ctx.drawImage(img,0,0,w,h);'
        'cv.toBlob(function(bl){var a=document.createElement("a");'
        'a.href=URL.createObjectURL(bl);a.download=fn+".png";'
        'document.body.appendChild(a);a.click();a.remove();});};'
        'img.src="data:image/svg+xml;base64,"+btoa(unescape('
        'encodeURIComponent(ckSvgStr(id))));};'
        '})();</script>')


# Size presets (display width in px).
SIZE_PRESETS = [("S", 520), ("M", 720), ("L", 920), ("XL", 1120)]


# ── Dispatch ─────────────────────────────────────────────────────────

_DISPATCH = {
    "column": (_bars, {}),
    "column_stacked": (_bars, {"stacked": True}),
    "column_100": (_bars, {"stacked": True, "percent": True}),
    "bar": (_bars, {"horizontal": True}),
    "bar_stacked": (_bars, {"horizontal": True, "stacked": True}),
    "pareto": (_pareto, {}),
    "line": (_lines, {}),
    "area": (_lines, {"area": True}),
    "histogram": (_histogram, {}),
    "boxplot": (_box, {}),
    "waterfall": (_waterfall, {}),
    "funnel": (_funnel, {}),
    "tornado": (_tornado, {}),
    "pie": (_pie, {}),
    "donut": (_pie, {"donut": True}),
    "waffle": (_waffle, {}),
    "scatter": (_scatter, {}),
    "bubble": (_scatter, {"bubble": True}),
    "matrix": (_matrix, {}),
    "radar": (_radar, {}),
    "bullet": (_bullet, {}),
    "dot": (_dot, {}),
    "gauge": (_gauge, {}),
    "heatmap": (_heatmap, {}),
    "slope": (_slope, {}),
    "dumbbell": (_dumbbell, {}),
    "gantt": (_gantt, {}),
    "marimekko": (_marimekko, {}),
    "combo": (_combo, {}),
    "smallmult": (_smallmult, {}),
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
