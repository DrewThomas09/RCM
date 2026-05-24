"""Shared X-Ray design primitives (handoff: ~/Desktop/design_handoff_xray).

PEdesk-native, server-rendered recreation of the HCRIS X-Ray design system —
reusable by BOTH the HCRIS X-Ray and the universal CMS Provider X-Ray so they
share one visual grammar (warm paper, navy ribbons, green accent, Source-Serif
headlines, mono labels, sharp 1px-rule corners, source/provenance visible,
honest empty states).

Pure functions returning HTML strings; CSS scoped to `.xr-*` so nothing else
on the page is affected. No external scripts/CDNs, no fabricated values — the
peer-band and table helpers render exactly the numbers the caller passes.
"""
from __future__ import annotations

import html as _html
from typing import Any, List, Optional, Sequence, Tuple

# Handoff tokens (scoped locals; mirror reference/styles.css).
XRAY_CSS = """
.xr{--xr-page:#ede7d4;--xr-paper:#faf6ec;--xr-paper2:#f3eddb;--xr-paper3:#ebe3c8;
 --xr-navy:#0d2336;--xr-ink:#15202b;--xr-ink2:#2a3a4a;--xr-muted:#6a7480;
 --xr-muted2:#8b94a0;--xr-rule:#c9c1ac;--xr-rule-soft:#d6cfb8;--xr-green:#1f7a5a;
 --xr-green-deep:#18573f;--xr-green-soft:#d6e8df;--xr-amber:#b8842e;
 --xr-amber-soft:#f3e2bc;--xr-red:#b14a3a;--xr-red-soft:#e8d3cd;
 --xr-serif:'Source Serif 4',Georgia,serif;--xr-sans:'Inter Tight',Inter,system-ui,sans-serif;
 --xr-mono:'JetBrains Mono',ui-monospace,monospace;}
.xr *{box-sizing:border-box;}
.xr-crumb{font-family:var(--xr-mono);font-size:10.5px;letter-spacing:.16em;
 text-transform:uppercase;color:var(--xr-muted);margin-bottom:14px;}
.xr-crumb b{color:var(--xr-ink);font-weight:500;}
.xr-eyebrow{font-family:var(--xr-mono);font-size:10.5px;letter-spacing:.16em;
 text-transform:uppercase;color:var(--xr-green);margin-bottom:10px;display:flex;
 align-items:center;gap:8px;}
.xr-eyebrow::before{content:"";width:18px;height:2px;background:var(--xr-green);display:inline-block;}
.xr-h1{font-family:var(--xr-serif);font-weight:400;font-size:40px;line-height:1;
 letter-spacing:-.025em;color:var(--xr-ink);margin:0 0 12px;}
.xr-h1 em,.xr-h2 em,.xr-hero em{font-style:italic;color:var(--xr-green);}
.xr-h2{font-family:var(--xr-serif);font-weight:400;font-size:24px;line-height:1.1;
 letter-spacing:-.015em;color:var(--xr-ink);margin:0 0 10px;}
.xr-lede{font-family:var(--xr-serif);font-size:15px;line-height:1.55;color:var(--xr-ink2);max-width:74ch;margin:0 0 var(--sc-s-5,20px);}
.xr-card{background:var(--xr-paper);border:1px solid var(--xr-rule);padding:20px 24px;margin-bottom:16px;}
.xr-card-title{font-family:var(--xr-serif);font-style:italic;font-size:17px;color:var(--xr-ink);margin:0 0 12px;}
.xr-ribbon{background:var(--xr-navy);color:var(--xr-paper);padding:10px 14px;
 display:flex;align-items:center;justify-content:space-between;gap:12px;}
.xr-ribbon .tag{font-family:var(--xr-mono);font-size:10px;letter-spacing:.14em;
 text-transform:uppercase;font-weight:500;}
.xr-ribbon .ribsub{font-family:var(--xr-mono);font-size:9.5px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--xr-rule);}
.xr-btn{font-family:var(--xr-mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;
 padding:10px 18px;border:1px solid var(--xr-green-deep);background:var(--xr-green-deep);
 color:var(--xr-paper);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;}
.xr-btn.ghost{background:transparent;border-color:var(--xr-rule);color:var(--xr-ink2);}
.xr-btn.ink{background:var(--xr-ink);border-color:var(--xr-ink);color:var(--xr-paper);}
.xr-btn[disabled],.xr-btn[aria-disabled=true]{opacity:.45;cursor:not-allowed;}
.xr-chip{font-family:var(--xr-mono);font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;
 padding:3px 8px;border:1px solid var(--xr-rule);display:inline-block;}
.xr-chip.green{background:var(--xr-green-soft);border-color:var(--xr-green);color:var(--xr-green-deep);}
.xr-chip.red{background:var(--xr-red-soft);border-color:var(--xr-red);color:var(--xr-red);}
.xr-chip.amber{background:var(--xr-amber-soft);border-color:var(--xr-amber);color:var(--xr-amber);}
.xr-chip.neutral{background:var(--xr-paper2);color:var(--xr-muted);}
.xr-tbl{width:100%;border-collapse:collapse;}
.xr-tbl th{background:var(--xr-paper2);border-bottom:1px solid var(--xr-rule);
 font-family:var(--xr-mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;
 color:var(--xr-muted);font-weight:500;text-align:right;padding:9px 13px;}
.xr-tbl th:first-child{text-align:left;}
.xr-tbl td{padding:10px 13px;border-bottom:1px solid var(--xr-rule-soft);
 font-family:var(--xr-serif);font-size:13.5px;color:var(--xr-ink2);text-align:right;}
.xr-tbl td:first-child{text-align:left;}
.xr-tbl td.num{font-family:var(--xr-mono);font-size:12px;font-variant-numeric:tabular-nums;}
.xr-tbl tr:hover td{background:var(--xr-paper2);}
.xr-tbl .section td{background:var(--xr-paper2);font-family:var(--xr-mono);font-size:9.5px;
 letter-spacing:.18em;text-transform:uppercase;color:var(--xr-muted);text-align:left;}
.xr-delta.green{color:var(--xr-green-deep);}
.xr-delta.red{color:var(--xr-red);}
.xr-delta.amber{color:var(--xr-amber);}
.xr-caveat{background:var(--xr-paper2);border-left:2px solid var(--xr-green);
 padding:12px 16px;font-family:var(--xr-serif);font-style:italic;font-size:13px;
 line-height:1.5;color:var(--xr-ink2);margin-top:14px;}
.xr-source{font-family:var(--xr-mono);font-size:9.5px;letter-spacing:.1em;
 text-transform:uppercase;color:var(--xr-muted);margin-top:8px;}
.xr-empty{font-family:var(--xr-serif);font-style:italic;color:var(--xr-muted);}
.xr-band{display:block;}
/* Results A-v2 primitives */
.xr-trend{display:block;}
.xr-trend-svg{display:block;height:auto;}
.xr-trend-empty{padding:8px 0;}
.xr-trend-x{display:flex;justify-content:space-between;font-family:var(--xr-mono);
 font-size:9px;letter-spacing:.1em;color:var(--xr-muted);margin-top:2px;}
.xr-spark{display:inline-block;vertical-align:middle;}
.xr-payer{margin:0 0 12px;}
.xr-payer-lab{font-family:var(--xr-mono);font-size:9.5px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--xr-muted);margin-bottom:4px;display:flex;
 justify-content:space-between;}
.xr-payer-sub{color:var(--xr-muted2);}
.xr-payer-bar{display:flex;height:38px;border:1px solid var(--xr-rule);
 background:var(--xr-paper3);overflow:hidden;}
.xr-payer-seg{display:flex;align-items:center;justify-content:center;
 border-right:1px solid var(--xr-paper);min-width:0;}
.xr-payer-seg:last-child{border-right:0;}
.xr-payer-seg-t{font-family:var(--xr-mono);font-size:11px;color:#fff;}
.xr-payer-legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:6px;
 font-family:var(--xr-mono);font-size:9.5px;letter-spacing:.06em;color:var(--xr-muted);}
.xr-payer-leg i{display:inline-block;width:8px;height:8px;margin-right:5px;vertical-align:baseline;}
.xr-dev{background:var(--xr-paper);border:1px solid var(--xr-rule);padding:14px;}
.xr-dev-state{font-family:var(--xr-mono);font-size:9px;letter-spacing:.14em;
 text-transform:uppercase;color:var(--xr-muted);}
.xr-dev-title{font-family:var(--xr-serif);font-style:italic;font-size:15px;color:var(--xr-ink);margin:2px 0 6px;}
.xr-dev-val{font-family:var(--xr-serif);font-size:26px;line-height:1;color:var(--xr-ink);margin-bottom:8px;}
.xr-dev-delta{font-family:var(--xr-mono);font-size:11px;font-weight:600;margin-left:8px;}
.xr-dev-div{border-top:1px dashed var(--xr-rule);margin:10px 0 6px;}
.xr-dev-trendlab{font-family:var(--xr-mono);font-size:9px;letter-spacing:.14em;
 text-transform:uppercase;color:var(--xr-muted);margin-bottom:4px;}
.xr-dev-cap{font-family:var(--xr-serif);font-style:italic;font-size:11.5px;color:var(--xr-muted);margin-top:4px;}
.xr-bridge{display:block;}
.xr-bridge-rec{font-family:var(--xr-serif);font-size:24px;color:var(--xr-green-deep);
 line-height:1.1;margin:0 0 10px;}
.xr-bridge-row{display:grid;grid-template-columns:190px 1fr 150px;align-items:center;
 gap:10px;padding:6px 0;border-bottom:1px dashed var(--xr-rule);}
.xr-bridge-lab{font-family:var(--xr-serif);font-size:13px;color:var(--xr-ink2);}
.xr-bridge-track{display:block;}
.xr-bridge-val{font-family:var(--xr-mono);font-size:11px;text-align:right;color:var(--xr-ink2);}
"""

# Peer-band target states → diamond fill.
_STATE_FILL = {
    "above": "var(--xr-green-deep)", "below": "var(--xr-red)",
    "aboveRed": "var(--xr-red)", "inband": "var(--xr-paper)",
}


def _e(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def xr_eyebrow(text: str) -> str:
    return f'<div class="xr-eyebrow">{_e(text)}</div>'


def xr_crumb(*parts: str) -> str:
    inner = " / ".join(_e(p) for p in parts[:-1])
    last = f'<b>{_e(parts[-1])}</b>' if parts else ""
    sep = " / " if inner else ""
    return f'<div class="xr-crumb">{inner}{sep}{last}</div>'


def xr_ribbon(tag: str, ribsub: str = "") -> str:
    sub = f'<span class="ribsub">{_e(ribsub)}</span>' if ribsub else ""
    return f'<div class="xr-ribbon"><span class="tag">{_e(tag)}</span>{sub}</div>'


def xr_chip(label: str, tone: str = "neutral") -> str:
    tone = tone if tone in ("green", "red", "amber", "neutral") else "neutral"
    return f'<span class="xr-chip {tone}">{_e(label)}</span>'


def xr_caveat(text: str) -> str:
    return f'<div class="xr-caveat">{_e(text)}</div>'


def xr_source(text: str) -> str:
    return f'<div class="xr-source">{_e(text)}</div>'


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def xr_peer_band(lo: float, hi: float, p25: Optional[float], median: Optional[float],
                 p75: Optional[float], target: Optional[float], state: str,
                 height: int = 18) -> str:
    """Horizontal box-plot: P25–P75 IQR box, median tick, target diamond.

    Positions map values onto a 0–100% axis via (v-lo)/(hi-lo). Returns an
    honest empty band when the inputs can't be placed (no fabricated geometry).
    """
    if hi <= lo or p25 is None or p75 is None:
        return ('<svg class="xr-band" width="100%" height="' + str(height) +
                '" role="img" aria-label="peer band unavailable">'
                '<line x1="0" y1="50%" x2="100%" y2="50%" stroke="var(--xr-rule)" '
                'stroke-dasharray="3 3"/></svg>')
    def px(v):  # → percentage along the axis
        return round(100 * _clamp01((v - lo) / (hi - lo)), 2)
    x25, x75 = px(p25), px(p75)
    box_w = max(x75 - x25, 0.5)
    fill = _STATE_FILL.get(state, "var(--xr-paper)")
    stroke = "var(--xr-ink)" if state == "inband" else fill
    parts = [
        f'<svg class="xr-band" width="100%" height="{height}" viewBox="0 0 100 {height}" '
        f'preserveAspectRatio="none" role="img" '
        f'aria-label="peer band P25 to P75 with target">',
        f'<line x1="0" y1="{height/2}" x2="100" y2="{height/2}" stroke="var(--xr-rule)" stroke-width="0.5"/>',
        f'<rect x="{x25}" y="{height*0.28:.1f}" width="{box_w}" height="{height*0.44:.1f}" '
        f'fill="var(--xr-green-soft)" stroke="var(--xr-rule)" stroke-width="0.5"/>',
    ]
    if median is not None:
        xm = px(median)
        parts.append(f'<line x1="{xm}" y1="{height*0.22:.1f}" x2="{xm}" y2="{height*0.78:.1f}" '
                     f'stroke="var(--xr-ink2)" stroke-width="1"/>')
    if target is not None:
        xt = px(target)
        s = height * 0.34
        cy = height / 2
        parts.append(
            f'<polygon points="{xt},{cy-s} {xt+2.2},{cy} {xt},{cy+s} {xt-2.2},{cy}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="0.8"/>')
    parts.append("</svg>")
    return "".join(parts)


def xr_benchmark_table(rows: Sequence[dict], headers: Sequence[str]) -> str:
    """Benchmark table. Each row dict: {cells: [...], section: bool, delta_tone}.

    A row with ``section=True`` renders a full-width section divider using its
    first cell as the label. Cells are rendered as-is (caller pre-escapes/marks
    numeric); pass plain values and they're escaped.
    """
    thead = "".join(f"<th>{_e(h)}</th>" for h in headers)
    body = ""
    for r in rows:
        if r.get("section"):
            body += (f'<tr class="section"><td colspan="{len(headers)}">'
                     f'{_e(r.get("label",""))}</td></tr>')
            continue
        tds = ""
        for i, c in enumerate(r.get("cells", [])):
            cls = "" if i == 0 else "num"
            tds += f'<td class="{cls}">{c}</td>'  # caller controls markup/escaping
        body += f"<tr>{tds}</tr>"
    return (f'<table class="xr-tbl"><thead><tr>{thead}</tr></thead>'
            f'<tbody>{body}</tbody></table>')


# ────────────────────────────────────────────────────────────────────
# Results-page primitives (handoff Results A-v2). All pure SVG/HTML, scoped
# `.xr-*`, honest empty states, no fabricated geometry — they plot exactly the
# values the caller passes (which come from the real HCRIS engine).
# ────────────────────────────────────────────────────────────────────

def _series_minmax(*series: Sequence[float]) -> Tuple[float, float]:
    vals = [v for s in series for v in s if v is not None]
    if not vals:
        return 0.0, 1.0
    lo, hi = min(vals), max(vals)
    if hi == lo:
        hi = lo + 1.0
    pad = (hi - lo) * 0.18
    return lo - pad, hi + pad


def _poly_points(pts: Sequence[float], lo: float, hi: float,
                 w: float, h: float, pad: float = 4.0) -> str:
    n = len(pts)
    if n < 2 or hi <= lo:
        return ""
    span = (w - 2 * pad) / (n - 1)
    out = []
    for i, v in enumerate(pts):
        if v is None:
            continue
        x = pad + i * span
        y = h - pad - (h - 2 * pad) * _clamp01((v - lo) / (hi - lo))
        out.append(f"{x:.1f},{y:.1f}")
    return " ".join(out)


def xr_trend_chart(target: Sequence[float], peer: Optional[Sequence[float]] = None,
                   *, unit: str = "", w: int = 460, h: int = 150,
                   show_axes: bool = True, labels: Optional[Sequence[str]] = None) -> str:
    """Two-line trend: target (red solid) + optional peer-median (ink dashed).

    Renders target-only when ``peer`` is absent/too sparse and surfaces a
    "peer trend unavailable" note — never a fabricated peer line. Empty target
    series → honest empty state.
    """
    tgt = [v for v in (target or [])]
    if len([v for v in tgt if v is not None]) < 2:
        return ('<div class="xr-trend xr-trend-empty">'
                '<span class="xr-source">Trend unavailable — need ≥2 periods.</span></div>')
    peer_ok = peer is not None and len([v for v in peer if v is not None]) >= 2
    lo, hi = _series_minmax(tgt, peer if peer_ok else [])
    pad = 6.0
    parts = [f'<svg class="xr-trend-svg" viewBox="0 0 {w} {h}" width="100%" '
             f'preserveAspectRatio="none" role="img" aria-label="3-year trend">']
    if show_axes and lo < 0 < hi:                       # zero line if span crosses 0
        zy = h - pad - (h - 2 * pad) * _clamp01((0 - lo) / (hi - lo))
        parts.append(f'<line x1="{pad}" y1="{zy:.1f}" x2="{w-pad}" y2="{zy:.1f}" '
                     f'stroke="var(--xr-rule)" stroke-dasharray="2 3" stroke-width="0.7"/>')
    if peer_ok:
        pp = _poly_points(peer, lo, hi, w, h, pad)
        if pp:
            parts.append(f'<polyline points="{pp}" fill="none" stroke="var(--xr-ink2)" '
                         f'stroke-width="1.4" stroke-dasharray="3 3"/>')
    tp = _poly_points(tgt, lo, hi, w, h, pad)
    parts.append(f'<polyline points="{tp}" fill="none" stroke="var(--xr-red)" stroke-width="2.2"/>')
    # end dot on target
    last = tp.split(" ")[-1] if tp else ""
    if last:
        lx, ly = last.split(",")
        parts.append(f'<circle cx="{lx}" cy="{ly}" r="2.6" fill="var(--xr-red)"/>')
    parts.append("</svg>")
    note = ("" if peer_ok else
            '<span class="xr-source">Peer trend unavailable for this metric/year set.</span>')
    xlabels = ""
    if labels:
        xlabels = ('<div class="xr-trend-x">' +
                   "".join(f"<span>{_e(l)}</span>" for l in labels) + "</div>")
    return f'<div class="xr-trend">{"".join(parts)}{xlabels}{note}</div>'


def xr_row_spark(pts: Sequence[float], state: str = "inband",
                 *, w: int = 82, h: int = 22) -> str:
    """Tiny single-line sparkline for table rows; faint dash when too sparse."""
    vals = [v for v in (pts or [])]
    if len([v for v in vals if v is not None]) < 2:
        return (f'<svg class="xr-spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
                f'role="img" aria-label="trend unavailable">'
                f'<line x1="2" y1="{h/2}" x2="{w-2}" y2="{h/2}" stroke="var(--xr-rule)" '
                f'stroke-dasharray="2 2" stroke-width="0.8"/></svg>')
    lo, hi = _series_minmax(vals)
    color = _STATE_FILL.get(state, "var(--xr-ink2)")
    pp = _poly_points(vals, lo, hi, w, h, 3.0)
    sx, sy = pp.split(" ")[0].split(",")
    ex, ey = pp.split(" ")[-1].split(",")
    return (f'<svg class="xr-spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="3-year trend sparkline">'
            f'<polyline points="{pp}" fill="none" stroke="{color}" stroke-width="1.4"/>'
            f'<circle cx="{sx}" cy="{sy}" r="1.4" fill="var(--xr-rule)"/>'
            f'<circle cx="{ex}" cy="{ey}" r="2" fill="{color}"/></svg>')


_PAYER_SEG = [("medicare", "Medicare", "var(--xr-ink2)"),
              ("medicaid", "Medicaid", "var(--xr-red)"),
              ("commercial", "Commercial", "var(--xr-green)")]


def xr_payer_stack(label: str, mix: dict, sub: str = "") -> str:
    """Horizontal stacked payer-day-mix bar + dot legend. ``mix`` keys:
    medicare / medicaid / commercial (percentages, 0–100). Honest empty when
    the mix doesn't sum to a usable total."""
    total = sum(float(mix.get(k, 0) or 0) for k, _, _ in _PAYER_SEG)
    if total <= 0:
        return (f'<div class="xr-payer"><div class="xr-payer-lab">{_e(label)}</div>'
                '<span class="xr-source">Payer mix unavailable.</span></div>')
    segs, legend = [], []
    for key, name, color in _PAYER_SEG:
        pct = float(mix.get(key, 0) or 0)
        w = 100 * pct / total
        if w > 0:
            txt = (f'<span class="xr-payer-seg-t">{pct:.1f}%</span>' if w >= 8 else "")
            segs.append(f'<span class="xr-payer-seg" style="width:{w:.2f}%;background:{color};">{txt}</span>')
        legend.append(f'<span class="xr-payer-leg"><i style="background:{color}"></i>'
                      f'{_e(name)} {pct:.1f}%</span>')
    sub_html = f'<span class="xr-payer-sub">{_e(sub)}</span>' if sub else ""
    return (f'<div class="xr-payer"><div class="xr-payer-lab">{_e(label)}{sub_html}</div>'
            f'<div class="xr-payer-bar">{"".join(segs)}</div>'
            f'<div class="xr-payer-legend">{"".join(legend)}</div></div>')


def xr_dev_card(title: str, *, state: str, value_html: str, delta_html: str = "",
                band: Optional[dict] = None, trend: Optional[Sequence[float]] = None,
                caption: str = "") -> str:
    """A flagged-metric deviation tile: state-colored top border, metric name,
    big value, delta, peer-band box-plot, mini trend, caption."""
    border = _STATE_FILL.get(state, "var(--xr-ink2)")
    band_html = xr_peer_band(**band) if band else ""
    trend_html = (xr_trend_chart(trend or [], show_axes=False, h=70, w=260)
                  if trend is not None else "")
    cap = f'<div class="xr-dev-cap">{_e(caption)}</div>' if caption else ""
    delta = f'<span class="xr-dev-delta">{delta_html}</span>' if delta_html else ""
    return (
        f'<div class="xr-dev" style="border-top:3px solid {border};">'
        f'<div class="xr-dev-state">{_e(state).upper()}</div>'
        f'<div class="xr-dev-title">{_e(title)}</div>'
        f'<div class="xr-dev-val">{value_html}{delta}</div>'
        f'{band_html}'
        f'<div class="xr-dev-div"></div>'
        f'<div class="xr-dev-trendlab">3Y TREND</div>{trend_html}{cap}</div>'
    )


def xr_ebitda_bridge(rows: Sequence[dict], *, recoverable_html: str = "",
                     assumption_note: str = "") -> str:
    """Margin waterfall. Each row: {label, pp (float), kind, value_label}.
    ``kind`` ∈ target/peer/comp (solid bar) | step (dashed overlay). The EV /
    cap-multiple is NOT computed here — pass ``assumption_note`` to surface it
    as an explicit, labeled assumption (never as a valuation)."""
    if not rows:
        return ('<div class="xr-bridge"><span class="xr-source">'
                'EBITDA bridge unavailable — insufficient margin data.</span></div>')
    pps = [float(r.get("pp", 0) or 0) for r in rows]
    lo, hi = min(pps + [0.0]), max(pps + [0.0])
    if hi == lo:
        hi = lo + 1.0
    span = hi - lo
    def x0(): return 100 * _clamp01((0 - lo) / span)
    bars = ""
    kind_fill = {"target": "var(--xr-red)", "peer": "var(--xr-ink2)",
                 "comp": "var(--xr-green)", "step": "var(--xr-green-deep)"}
    for r in rows:
        pp = float(r.get("pp", 0) or 0)
        xv = 100 * _clamp01((pp - lo) / span)
        zx = x0()
        left, w = (min(zx, xv), abs(xv - zx))
        fill = kind_fill.get(r.get("kind", "target"), "var(--xr-ink2)")
        dashed = ' stroke-dasharray="3 2" fill-opacity="0.35"' if r.get("kind") == "step" else ""
        bars += (
            f'<div class="xr-bridge-row">'
            f'<span class="xr-bridge-lab">{_e(r.get("label",""))}</span>'
            f'<span class="xr-bridge-track">'
            f'<svg viewBox="0 0 100 14" width="100%" height="14" preserveAspectRatio="none">'
            f'<line x1="{zx:.1f}" y1="0" x2="{zx:.1f}" y2="14" stroke="var(--xr-rule)" stroke-width="0.6"/>'
            f'<rect x="{left:.1f}" y="3" width="{max(w,0.6):.1f}" height="8" fill="{fill}"'
            f' stroke="{fill}"{dashed}/></svg></span>'
            f'<span class="xr-bridge-val">{_e(r.get("value_label",""))}</span>'
            f'</div>'
        )
    rec = (f'<div class="xr-bridge-rec">{recoverable_html}</div>' if recoverable_html else "")
    note = (xr_caveat(assumption_note) if assumption_note else "")
    return f'<div class="xr-bridge">{rec}{bars}{note}</div>'
