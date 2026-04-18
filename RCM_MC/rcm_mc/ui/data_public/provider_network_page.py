"""Provider Network Intelligence page — /provider-network."""
from __future__ import annotations

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


_SECTORS = [
    "Physician Group", "Behavioral Health", "Dental", "Dermatology",
    "Urgent Care", "Ambulatory Surgery", "Home Health", "Hospice",
    "Radiology", "Orthopedics", "Cardiology", "Gastroenterology",
    "Ophthalmology", "Physical Therapy", "Laboratory",
    "Staffing", "Revenue Cycle Management", "Health IT",
    "Pediatric", "Addiction Medicine",
]


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _hhi_gauge_svg(hhi: float, regime_color: str) -> str:
    W, H = 260, 80
    cx, cy, r_out, r_in = 130, 70, 60, 38

    # Arc from 180° to 360° (left to right half-circle)
    def _pt(angle_deg: float, radius: float):
        rad = math.radians(angle_deg)
        x = cx + radius * math.cos(rad)
        y = cy - radius * math.sin(rad)
        return x, y

    def _arc(a_start: float, a_end: float, r: float, color: str, width: float = 10) -> str:
        x1, y1 = _pt(a_start, r)
        x2, y2 = _pt(a_end, r)
        large = 1 if abs(a_end - a_start) > 180 else 0
        return (
            f'<path d="M {x1:.1f},{y1:.1f} A {r},{r} 0 {large},0 {x2:.1f},{y2:.1f}"'
            f' stroke="{color}" stroke-width="{width}" fill="none" stroke-linecap="butt"/>'
        )

    import math as _math
    math = _math

    # Background track
    bg_arc = _arc(180, 0, r_out - 5, P["border"], 12)

    # Fill based on HHI (0-10000 → 180°-0°)
    fill_angle = 180 - (hhi / 10000) * 180
    fill_arc = _arc(180, fill_angle, r_out - 5, regime_color, 12)

    # Labels
    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;background:{P["panel"]};border:1px solid {P["border"]}">',
        bg_arc, fill_arc,
        f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="16" '
        f'fill="{regime_color}" font-weight="600" font-variant-numeric="tabular-nums">{hhi:.0f}</text>',
        f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" font-size="9" fill="{P["text_dim"]}">HHI Score</text>',
        f'<text x="20" y="{cy + 6}" font-size="8" fill="{P["text_faint"]}">Divers.</text>',
        f'<text x="{W-50}" y="{cy + 6}" font-size="8" fill="{P["text_faint"]}">Captive</text>',
        '</svg>',
    ]
    return "\n".join(lines)


def _segments_svg(segments) -> str:
    W, H = 500, 30 + len(segments) * 28
    pad_l = 160
    pad_r = 80

    max_share = max((s.market_share for s in segments), default=1.0)
    chart_w = W - pad_l - pad_r

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    risk_colors = {"Low": P["positive"], "Medium": P["warning"], "High": P["negative"]}

    for i, seg in enumerate(segments):
        y = 16 + i * 28
        bw = (seg.market_share / max_share) * chart_w if max_share > 0 else 0
        c = risk_colors.get(seg.risk_flag, P["text_dim"])
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="16" fill="{c}" opacity="0.7"/>')
        lines.append(f'<text x="{pad_l - 6}" y="{y + 12}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{seg.segment}</text>')
        pct = f"{seg.market_share * 100:.1f}%"
        lines.append(f'<text x="{pad_l + bw + 4:.1f}" y="{y + 12}" fill="{c}">{pct}</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _regime_table(regime_stats) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, rs in enumerate(regime_stats):
        rbg = bg2 if i % 2 else bg
        mult_c = P["positive"] if rs.moic_mult >= 1.0 else P["negative"]
        mult_str = f"+{(rs.moic_mult-1)*100:.0f}%" if rs.moic_mult >= 1.0 else f"{(rs.moic_mult-1)*100:.0f}%"
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{rs.label[:40]}</td>'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">{rs.n_deals}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{rs.p25_moic:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{rs.median_moic:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{rs.p75_moic:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{rs.median_ev_ebitda:.1f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{mult_c}">{mult_str}</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_c = f'style="padding:5px 8px;text-align:center;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Regime</th>'
        f'<th {hdr_c}>Deals</th>'
        f'<th {hdr_r}>P25 MOIC</th>'
        f'<th {hdr_r}>P50 MOIC</th>'
        f'<th {hdr_r}>P75 MOIC</th>'
        f'<th {hdr_r}>EV/EBITDA</th>'
        f'<th {hdr_r}>MOIC Adj.</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _peers_table(peers, title: str) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, p in enumerate(peers):
        rbg = bg2 if i % 2 else bg
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{p.company}</td>'
            f'<td style="padding:5px 8px;color:{tdim}">{p.sector[:20]}</td>'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">{p.year}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${p.ev_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{p.payer_commercial*100:.0f}%</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{p.moic:.2f}x</td>'
            f'<td style="padding:5px 8px;color:{tdim};font-size:10px">{p.implied_regime}</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_c = f'style="padding:5px 8px;text-align:center;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};'
        f'padding:6px 0 4px;text-transform:uppercase;letter-spacing:0.08em">{title}</div>'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Company</th>'
        f'<th {hdr_l}>Sector</th>'
        f'<th {hdr_c}>Year</th>'
        f'<th {hdr_r}>EV</th>'
        f'<th {hdr_r}>Comm%</th>'
        f'<th {hdr_r}>MOIC</th>'
        f'<th {hdr_l}>Regime</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _input_form(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    comm = params.get("comm", "0.55")
    mcare = params.get("mcare", "0.25")
    mcaid = params.get("mcaid", "0.15")
    sp = params.get("sp", "0.05")

    options = "".join(
        f'<option value="{s}" {"selected" if s == sector else ""}>{s}</option>'
        for s in _SECTORS
    )
    inp = (
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};padding:6px 8px;'
        f'font-family:\'JetBrains Mono\',monospace;font-size:12px;'
        f'border-radius:2px;width:100%;box-sizing:border-box'
    )
    lbl = (
        f'display:block;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{P["text_dim"]};'
        f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px'
    )
    btn = (
        f'background:{P["accent"]};color:{P["text"]};'
        f'border:none;padding:8px 20px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:12px;cursor:pointer;border-radius:2px'
    )

    return f'''<form method="get" action="/provider-network" style="
    background:{P["panel"]};border:1px solid {P["border"]};
    padding:14px 16px;display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr auto;
    gap:12px;align-items:end">
  <div><label style="{lbl}">Sector</label>
    <select name="sector" style="{inp}">{options}</select></div>
  <div><label style="{lbl}">Commercial %</label>
    <input name="comm" type="number" step="0.01" min="0" max="1" value="{comm}" style="{inp}"></div>
  <div><label style="{lbl}">Medicare %</label>
    <input name="mcare" type="number" step="0.01" min="0" max="1" value="{mcare}" style="{inp}"></div>
  <div><label style="{lbl}">Medicaid %</label>
    <input name="mcaid" type="number" step="0.01" min="0" max="1" value="{mcaid}" style="{inp}"></div>
  <div><label style="{lbl}">Self-Pay %</label>
    <input name="sp" type="number" step="0.01" min="0" max="1" value="{sp}" style="{inp}"></div>
  <div><button type="submit" style="{btn}">Analyze</button></div>
</form>'''


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_provider_network(params: dict) -> str:
    import math

    sector = params.get("sector", "Physician Group")

    payer_mix = None
    try:
        comm = float(params.get("comm", 0))
        mcare = float(params.get("mcare", 0))
        mcaid = float(params.get("mcaid", 0))
        sp = float(params.get("sp", 0))
        total = comm + mcare + mcaid + sp
        if total > 0:
            payer_mix = {
                "commercial": round(comm / total, 4),
                "medicare": round(mcare / total, 4),
                "medicaid": round(mcaid / total, 4),
                "self_pay": round(sp / total, 4),
            }
    except (ValueError, TypeError):
        pass

    from rcm_mc.data_public.provider_network import compute_provider_network
    r = compute_provider_network(sector, payer_mix)

    # KPIs
    adj_sign = f"+{r.implied_moic_adj:.1f}%" if r.implied_moic_adj >= 0 else f"{r.implied_moic_adj:.1f}%"
    kpis = ck_kpi_block("Network Regime",
                        f'<span style="color:{r.regime_color}">{r.network_regime.capitalize()}</span>')
    kpis += ck_kpi_block("HHI Score", f"{r.network_hhi:.0f}",
                         unit=f"Concentration: {r.concentration_risk}",
                         delta="0 = diversified, 10k = monopoly")
    kpis += ck_kpi_block("Conc. Risk",
                         f'<span style="color:{r.concentration_color}">{r.concentration_risk}</span>')
    kpis += ck_kpi_block("Corpus Median MOIC", f"{r.corpus_median_moic:.2f}x")
    kpis += ck_kpi_block("Adj. MOIC Estimate", f"{r.adjusted_moic_estimate:.2f}x",
                         delta=adj_sign)
    kpis += ck_kpi_block("Corpus Deals", str(r.corpus_deal_count))

    gauge = _hhi_gauge_svg(r.network_hhi, r.regime_color)
    seg_svg = _segments_svg(r.segments)
    regime_tbl = _regime_table(r.regime_stats)
    peers_div = _peers_table(r.peers_diversified, "Diversified Payer Mix Peers")
    peers_conc = _peers_table(r.peers_concentrated, "Concentrated Commercial Peers")

    bg_sec = P["panel"]
    bg_tert = P["panel_alt"]
    border = P["border"]
    tprim = P["text"]
    tdim = P["text_dim"]

    content = f'''
{_input_form(params)}

<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:12px">
{kpis}
</div>

<div style="display:grid;grid-template-columns:1fr 2fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      HHI Concentration Gauge
    </div>
    {gauge}
    <div style="margin-top:8px;padding:8px;background:{bg_tert};border:1px solid {border}">
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim}">
        Network Regime
      </div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:14px;
        color:{r.regime_color};margin-top:4px">{r.regime_label}</div>
    </div>
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Payer Channel Breakdown
    </div>
    {seg_svg}
  </div>
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    MOIC by Network Regime — Corpus Analysis
  </div>
  {regime_tbl}
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    {peers_div}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    {peers_conc}
  </div>
</div>
'''

    return chartis_shell(
        body=content,
        title=f"Provider Network Intelligence — {sector}",
        active_nav="/provider-network",
    )
