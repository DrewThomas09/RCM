"""IC Memo Generator — corpus-benchmarked investment committee memo section.

Accepts deal inputs via GET form, benchmarks against the 700+ deal corpus,
and renders: percentile ranks, peer comps table, flag summary, and benchmark charts.
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    P, _MONO, _SANS,
    chartis_shell, ck_fmt_moic, ck_fmt_pct, ck_fmt_num,
    ck_section_header, ck_kpi_block,
)
from rcm_mc.ui.chartis._helpers import render_page_explainer


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _pct_gauge(pct: Optional[float], label: str, w: int = 140, h: int = 80) -> str:
    """Semi-circle gauge SVG showing percentile rank."""
    if pct is None:
        return f'<svg width="{w}" height="{h}"><text x="{w//2}" y="{h//2}" fill="{P["text_dim"]}" text-anchor="middle" font-size="11" font-family="{_MONO}">N/A</text></svg>'
    cx, cy, r = w // 2, h - 8, h - 12
    # arc from 180° to 0° (left to right)
    angle = math.radians(180 - pct * 1.8)
    nx = cx + r * math.cos(angle)
    ny = cy - r * math.sin(angle)

    color = P["positive"] if pct >= 60 else (P["warning"] if pct >= 35 else P["negative"])
    return f'''<svg width="{w}" height="{h}" style="overflow:visible">
  <path d="M {cx-r},{cy} A {r},{r} 0 0,1 {cx+r},{cy}" fill="none" stroke="{P['border']}" stroke-width="8"/>
  <path d="M {cx-r},{cy} A {r},{r} 0 0,1 {nx:.1f},{ny:.1f}" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="butt"/>
  <text x="{cx}" y="{cy-4}" fill="{color}" text-anchor="middle" font-size="16" font-family="{_MONO}" font-variant-numeric="tabular-nums">{pct:.0f}</text>
  <text x="{cx}" y="{cy+10}" fill="{P['text_dim']}" text-anchor="middle" font-size="9" font-family="{_SANS}">pctile</text>
  <text x="{cx}" y="{h-2}" fill="{P['text_dim']}" text-anchor="middle" font-size="9" font-family="{_SANS}">{html.escape(label)}</text>
</svg>'''


def _moic_waterfall(
    p25: Optional[float],
    p50: Optional[float],
    p75: Optional[float],
    deal_moic: Optional[float],
    sector_p50: Optional[float],
    w: int = 320,
    h: int = 90,
) -> str:
    """Horizontal bar chart showing MOIC distribution vs deal target."""
    pad_l, pad_r, pad_t, pad_b = 60, 20, 14, 24
    chart_w = w - pad_l - pad_r
    chart_h = h - pad_t - pad_b

    vals = [v for v in [p25, p50, p75, deal_moic, sector_p50] if v is not None]
    if not vals:
        return ""
    vmax = max(vals) * 1.1
    vmin = 0.0

    def xp(v: float) -> float:
        return pad_l + (v - vmin) / (vmax - vmin) * chart_w

    bars = [
        ("P25",       p25,       P["text_faint"], 18),
        ("P50",       p50,       P["text_dim"],   18),
        ("P75",       p75,       P["text"],        18),
        ("Sector P50",sector_p50,P["warning"],     18),
        ("Target",    deal_moic, P["accent"],      18),
    ]
    y = pad_t
    items = []
    for lbl, val, col, bh in bars:
        if val is None:
            continue
        bx = xp(val)
        items.append(
            f'<line x1="{pad_l}" y1="{y+bh//2}" x2="{bx:.1f}" y2="{y+bh//2}" stroke="{col}" stroke-width="6" stroke-linecap="square"/>'
            f'<circle cx="{bx:.1f}" cy="{y+bh//2}" r="4" fill="{col}"/>'
            f'<text x="{pad_l-4}" y="{y+bh//2+4}" fill="{P["text_dim"]}" text-anchor="end" font-size="9" font-family="{_SANS}">{lbl}</text>'
            f'<text x="{bx+6:.1f}" y="{y+bh//2+4}" fill="{col}" font-size="9" font-family="{_MONO}" font-variant-numeric="tabular-nums">{val:.2f}×</text>'
        )
        y += bh + 2

    # x-axis ticks
    ticks = []
    step = 0.5
    v = 0.0
    while v <= vmax:
        tx = xp(v)
        ticks.append(f'<line x1="{tx:.1f}" y1="{h-pad_b}" x2="{tx:.1f}" y2="{h-pad_b+4}" stroke="{P["border"]}" stroke-width="1"/>')
        ticks.append(f'<text x="{tx:.1f}" y="{h-pad_b+13}" fill="{P["text_faint"]}" text-anchor="middle" font-size="8" font-family="{_MONO}" font-variant-numeric="tabular-nums">{v:.1f}×</text>')
        v += step

    return f'<svg width="{w}" height="{h}">{"".join(ticks)}{"".join(items)}</svg>'


def _ev_ebitda_bar(
    p25: Optional[float], p50: Optional[float], p75: Optional[float],
    deal_val: Optional[float], w: int = 280, h: int = 50,
) -> str:
    """Compact horizontal strip showing EV/EBITDA positioning."""
    vals = [v for v in [p25, p50, p75, deal_val] if v is not None]
    if not vals:
        return ""
    vmin, vmax = 0, max(vals) * 1.15
    pad_l, pad_r, pad_t = 8, 8, 10
    cw = w - pad_l - pad_r

    def xp(v: float) -> float:
        return pad_l + (v - vmin) / (vmax - vmin) * cw

    items = []
    if p25 is not None and p75 is not None:
        items.append(f'<rect x="{xp(p25):.1f}" y="{pad_t+6}" width="{xp(p75)-xp(p25):.1f}" height="10" fill="{P["panel_alt"]}" stroke="{P["border"]}" stroke-width="1"/>')
    if p50 is not None:
        items.append(f'<line x1="{xp(p50):.1f}" y1="{pad_t+2}" x2="{xp(p50):.1f}" y2="{pad_t+20}" stroke="{P["text_dim"]}" stroke-width="2"/>')
        items.append(f'<text x="{xp(p50):.1f}" y="{h-2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_MONO}">{p50:.1f}×</text>')
    if deal_val is not None:
        col = P["warning"] if deal_val > (p75 or 999) else (P["positive"] if deal_val < (p50 or 0) else P["text"])
        items.append(f'<line x1="{xp(deal_val):.1f}" y1="{pad_t}" x2="{xp(deal_val):.1f}" y2="{pad_t+22}" stroke="{col}" stroke-width="3"/>')
        items.append(f'<text x="{xp(deal_val):.1f}" y="{pad_t-2}" text-anchor="middle" fill="{col}" font-size="8" font-family="{_MONO}">{deal_val:.1f}×</text>')

    return f'<svg width="{w}" height="{h}">{"".join(items)}</svg>'


# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------

_SECTOR_OPTIONS = [
    "", "Acute Care / Hospital", "Ambulatory Surgery Center",
    "Behavioral Health", "Cardiology", "Dental / DSO",
    "Dermatology", "Dialysis", "Emergency Medicine / EMS",
    "Fertility / Reproductive", "Gastroenterology",
    "GI / Endoscopy", "Health IT / RCM SaaS",
    "Home Health / Hospice", "Hospitalist / IPC",
    "Managed Care / Health Plan", "Nephrology",
    "Neurology", "Oncology", "Ophthalmology",
    "Orthopedics / MSK", "Pediatrics / NICU",
    "Physical Therapy / Rehab", "Primary Care / VBC",
    "Radiology / Imaging", "Sleep Medicine",
    "Urgent Care", "Women's Health",
]


def _input_form(params: Dict[str, str]) -> str:
    def v(k: str, d: str = "") -> str:
        return html.escape(params.get(k, d))

    sector_opts = "".join(
        f'<option value="{html.escape(s)}" {"selected" if v("sector") == s else ""}>{html.escape(s) or "— Any sector —"}</option>'
        for s in _SECTOR_OPTIONS
    )

    return f"""
<form method="GET" action="/corpus-ic-memo" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;align-items:end;">
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">DEAL NAME</label>
    <input name="deal_name" value="{v('deal_name')}" style="{_input_css()}" placeholder="e.g. Acme Physician Group">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">SECTOR</label>
    <select name="sector" style="{_input_css()}">{sector_opts}</select>
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">EV ($M)</label>
    <input name="ev_mm" value="{v('ev_mm')}" type="number" step="0.1" min="0" style="{_input_css()}" placeholder="e.g. 350">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">EBITDA AT ENTRY ($M)</label>
    <input name="ebitda_mm" value="{v('ebitda_mm')}" type="number" step="0.1" min="0" style="{_input_css()}" placeholder="e.g. 40">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">HOLD (YEARS)</label>
    <input name="hold_years" value="{v('hold_years')}" type="number" step="0.5" min="0" style="{_input_css()}" placeholder="e.g. 5">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">TARGET MOIC</label>
    <input name="moic" value="{v('moic')}" type="number" step="0.1" min="0" style="{_input_css()}" placeholder="e.g. 3.0">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">TARGET IRR (%)</label>
    <input name="irr" value="{v('irr')}" type="number" step="0.1" min="0" style="{_input_css()}" placeholder="e.g. 25">
  </div>
  <div>
    <label style="display:block;font-size:10px;color:{P['text_dim']};margin-bottom:3px;font-family:{_SANS}">COMMERCIAL MIX (%)</label>
    <input name="comm_pct" value="{v('comm_pct')}" type="number" step="1" min="0" max="100" style="{_input_css()}" placeholder="e.g. 55">
  </div>
  <div style="display:flex;align-items:flex-end;">
    <button type="submit" style="background:{P['accent']};color:#fff;border:none;padding:7px 20px;font-family:{_MONO};font-size:12px;cursor:pointer;letter-spacing:.05em;">RUN ANALYSIS</button>
  </div>
</form>"""


def _input_css() -> str:
    return (
        f"width:100%;background:{P['panel_alt']};color:{P['text']};"
        f"border:1px solid {P['border']};padding:5px 8px;"
        f"font-family:{_MONO};font-size:12px;font-variant-numeric:tabular-nums;"
    )


# ---------------------------------------------------------------------------
# Result renderer
# ---------------------------------------------------------------------------

def _peers_table(peers: list) -> str:
    if not peers:
        return f'<p style="color:{P["text_dim"]};font-size:11px;padding:8px 0">No peers found in corpus matching sector/size profile.</p>'

    rows = ""
    for i, p in enumerate(peers):
        bg = P["row_stripe"] if i % 2 else P["panel"]
        ev = f"${p.ev_mm:,.0f}M" if p.ev_mm else "—"
        mult = f"{p.ev_ebitda:.1f}×" if p.ev_ebitda else "—"
        moic = f"{p.moic:.2f}×" if p.moic else "—"
        irr = f"{p.irr*100:.1f}%" if p.irr else "—"
        hold = f"{p.hold_years:.1f}y" if p.hold_years else "—"
        sector = html.escape(p.sector or "—")
        name = html.escape(p.deal_name[:42])
        buyer = html.escape((p.buyer or "—")[:28])
        yr = str(p.year) if p.year else "—"
        rows += f"""<tr style="background:{bg}">
  <td style="padding:5px 8px;font-size:11px;font-family:{_MONO}">{yr}</td>
  <td style="padding:5px 8px;font-size:11px;white-space:nowrap">{name}</td>
  <td style="padding:5px 8px;font-size:10px;color:{P['text_dim']}">{sector}</td>
  <td style="padding:5px 8px;font-size:10px;color:{P['text_dim']}">{buyer}</td>
  <td style="padding:5px 8px;font-size:11px;font-family:{_MONO};text-align:right">{ev}</td>
  <td style="padding:5px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{mult}</td>
  <td style="padding:5px 8px;font-size:12px;font-family:{_MONO};text-align:right;font-weight:600;color:{P['positive'] if p.moic and p.moic >= 2.5 else P['text']};font-variant-numeric:tabular-nums">{moic}</td>
  <td style="padding:5px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{irr}</td>
  <td style="padding:5px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{hold}</td>
</tr>"""

    th_css = f"padding:5px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};font-weight:600;border-bottom:1px solid {P['border']};white-space:nowrap"
    return f"""<table style="width:100%;border-collapse:collapse;">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th_css}">YEAR</th>
  <th style="{th_css}">DEAL</th>
  <th style="{th_css}">SECTOR</th>
  <th style="{th_css}">BUYER</th>
  <th style="{th_css};text-align:right">EV</th>
  <th style="{th_css};text-align:right">EV/EBITDA</th>
  <th style="{th_css};text-align:right">MOIC</th>
  <th style="{th_css};text-align:right">IRR</th>
  <th style="{th_css};text-align:right">HOLD</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>"""


def _flags_panel(flags: list) -> str:
    if not flags:
        return f"""<div style="background:{P['panel_alt']};border:1px solid {P['positive']};padding:10px 14px;margin-bottom:12px;">
  <span style="font-size:10px;color:{P['positive']};font-family:{_SANS};letter-spacing:.08em;">NO FLAGS — DEAL WITHIN NORMAL CORPUS PARAMETERS</span>
</div>"""
    items = "".join(
        f'<li style="padding:4px 0;font-size:12px;color:{P["warning"]};border-bottom:1px solid {P["border_dim"]};font-family:{_SANS}">&#9654; {html.escape(f)}</li>'
        for f in flags
    )
    return f"""<div style="background:{P['panel_alt']};border:1px solid {P['warning']};padding:10px 14px;margin-bottom:12px;">
  <div style="font-size:9px;color:{P['warning']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:6px;">IC FLAGS ({len(flags)})</div>
  <ul style="list-style:none;padding:0">{items}</ul>
</div>"""


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_ic_memo_gen(params: Dict[str, str]) -> str:
    """Render the IC Memo Generator page.

    params: dict of query-string values (deal_name, ev_mm, ebitda_mm,
            hold_years, moic, irr, comm_pct, sector).
    Returns full HTML string.
    """
    from rcm_mc.data_public.ic_memo_analytics import compute_ic_benchmarks

    def _flt(k: str) -> Optional[float]:
        try:
            return float(params[k]) if params.get(k, "").strip() else None
        except (ValueError, TypeError):
            return None

    deal_name = params.get("deal_name", "").strip() or "Unnamed Deal"
    sector    = params.get("sector", "").strip() or None
    ev_mm     = _flt("ev_mm")
    ebitda_mm = _flt("ebitda_mm")
    hold      = _flt("hold_years")
    moic      = _flt("moic")
    irr_pct   = _flt("irr")
    irr       = irr_pct / 100 if irr_pct is not None else None
    comm_raw  = _flt("comm_pct")
    comm_pct  = comm_raw / 100 if comm_raw is not None else None

    has_inputs = any(x is not None for x in [ev_mm, ebitda_mm, moic, irr])

    bm = None
    result_html = ""
    if has_inputs:
        bm = compute_ic_benchmarks(
            deal_name=deal_name,
            ev_mm=ev_mm,
            ebitda_mm=ebitda_mm,
            hold_years=hold,
            sector=sector,
            target_moic=moic,
            target_irr=irr,
            payer_comm_pct=comm_pct,
        )

        # KPI strip
        ev_str   = f"${ev_mm:,.1f}M" if ev_mm else "—"
        mult_str = f"{bm.deal_ev_ebitda:.1f}×" if bm.deal_ev_ebitda else "—"
        moic_str = f"{moic:.2f}×" if moic else "—"
        irr_str  = f"{irr*100:.1f}%" if irr else "—"
        hold_str = f"{hold:.1f}y" if hold else "—"

        kpi_items = [
            ("ENTRY EV", ev_str), ("EV/EBITDA", mult_str),
            ("TARGET MOIC", moic_str), ("TARGET IRR", irr_str), ("HOLD", hold_str),
            ("CORPUS N", str(bm.corpus_size)),
            (f"SECTOR N ({bm.sector_label[:14]})", str(bm.sector_size)),
        ]
        kpis = "".join(
            f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:8px 14px;">'
            f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:3px">{lbl}</div>'
            f'<div style="font-size:16px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{P["text"]}">{val}</div>'
            f'</div>'
            for lbl, val in kpi_items
        )
        kpi_strip = f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:16px">{kpis}</div>'

        # Percentile gauges
        gauges = "".join([
            _pct_gauge(bm.moic_pct,        "MOIC vs corpus"),
            _pct_gauge(bm.irr_pct,         "IRR vs corpus"),
            _pct_gauge(bm.ev_ebitda_pct,   "Entry attractive"),
        ])
        gauge_row = (
            f'<div style="display:flex;gap:24px;align-items:flex-end;margin-bottom:16px;padding:12px;background:{P["panel_alt"]};border:1px solid {P["border"]}">'
            f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;writing-mode:vertical-lr;transform:rotate(180deg);margin-right:8px">PERCENTILE RANKS</div>'
            f'{gauges}'
            f'</div>'
        )

        # MOIC chart
        moic_chart = _moic_waterfall(
            bm.moic_p25, bm.moic_p50, bm.moic_p75,
            bm.deal_moic, bm.sector_moic_p50,
        )
        # EV/EBITDA strip
        ev_chart = _ev_ebitda_bar(
            bm.ev_ebitda_p25, bm.ev_ebitda_p50, bm.ev_ebitda_p75,
            bm.deal_ev_ebitda,
        )

        charts_row = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">'
            f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:10px">'
            f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">MOIC BENCHMARK — CORPUS DISTRIBUTION</div>'
            f'{moic_chart}'
            f'</div>'
            f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:10px">'
            f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">EV/EBITDA ENTRY MULTIPLE — CORPUS BAND</div>'
            f'{ev_chart}'
            f'<div style="font-size:9px;color:{P["text_faint"]};font-family:{_SANS};margin-top:6px">Shaded band = P25–P75. Tick = P50. Vertical line = this deal.</div>'
            f'</div>'
            f'</div>'
        )

        result_html = f"""
{kpi_strip}
{_flags_panel(bm.flags)}
{gauge_row}
{charts_row}
<div style="margin-bottom:6px">
  <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:6px;border-bottom:1px solid {P['border']};padding-bottom:4px">
    PEER COMPARABLES — TOP {len(bm.peers)} CORPUS MATCHES (RANKED BY SIMILARITY)
  </div>
  {_peers_table(bm.peers)}
</div>
"""

    empty_msg = "" if has_inputs else f"""
<div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:24px;text-align:center;margin-bottom:16px">
  <div style="font-size:12px;color:{P['text_dim']};font-family:{_SANS}">Enter deal parameters above and click RUN ANALYSIS to generate corpus benchmarks.</div>
  <div style="font-size:10px;color:{P['text_faint']};font-family:{_SANS};margin-top:6px">Benchmarked against {705} publicly disclosed healthcare PE transactions.</div>
</div>"""

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("IC MEMO GENERATOR", f"Corpus-benchmarked investment committee analysis — {705} transactions", None)}
  <div style="background:{P['panel']};border:1px solid {P['border']};padding:14px;margin-bottom:16px">
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:10px">DEAL INPUTS</div>
    {_input_form(params)}
  </div>
  {empty_msg}
  {result_html}
</div>
"""
    explainer = render_page_explainer(
        what=(
            "Corpus-benchmarked IC memo section: takes deal inputs, "
            "scores them against the 700+ deal corpus for percentile "
            "ranks, pulls a peer-comp table, summarizes flags, and "
            "renders benchmark charts suitable for inclusion in an IC "
            "packet."
        ),
        source="data_public/ic_memo.py (corpus-benchmarked memo section).",
        page_key="corpus-ic-memo",
    )
    subtitle = f"Target: {html.escape(deal_name)}" if has_inputs else "Corpus benchmarking"
    return chartis_shell(explainer + body, "IC Memo Generator", active_nav="/corpus-ic-memo", subtitle=subtitle)
