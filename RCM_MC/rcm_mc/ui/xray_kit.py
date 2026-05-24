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
