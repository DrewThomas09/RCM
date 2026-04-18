"""Covenant Monitor page — /covenant-monitor."""
from __future__ import annotations

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


_SECTORS = [
    "Physician Group", "Behavioral Health", "Dental", "Dermatology",
    "Urgent Care", "Ambulatory Surgery", "Home Health", "Hospice",
    "Radiology", "Orthopedics", "Cardiology", "Gastroenterology",
    "Ophthalmology", "Physical Therapy", "Laboratory",
    "Staffing", "Revenue Cycle Management", "Health IT",
]


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _leverage_timeline_svg(projections, thresholds_lev: float, thresholds_icr: float) -> str:
    W, H = 760, 180
    pad_l, pad_r, pad_t, pad_b = 50, 80, 20, 40
    chart_w = W - pad_l - pad_r
    chart_h = H - pad_t - pad_b

    years = [p.year for p in projections]
    levs = [p.debt_ebitda for p in projections]
    icrs = [p.interest_coverage for p in projections]

    max_lev = max(max(levs) * 1.15, thresholds_lev * 1.05)
    max_icr = max(max(icrs) * 1.15, thresholds_icr * 1.05)

    def _px(yr: int) -> float:
        return pad_l + ((yr - 1) / max(len(years) - 1, 1)) * chart_w

    def _py_lev(v: float) -> float:
        return pad_t + (1 - v / max_lev) * chart_h

    def _py_icr(v: float) -> float:
        return pad_t + (1 - v / max_icr) * chart_h

    border = P["border"]
    text_dim = P["text_dim"]
    text = P["text"]
    pos = P["positive"]
    neg = P["negative"]
    warn = P["warning"]
    accent = P["accent"]
    bg = P["panel"]

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;background:{bg};border:1px solid {border}">',
        # Axes
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + chart_h}" stroke="{border}" stroke-width="1"/>',
        f'<line x1="{pad_l}" y1="{pad_t + chart_h}" x2="{pad_l + chart_w}" y2="{pad_t + chart_h}" stroke="{border}" stroke-width="1"/>',
    ]

    # Covenant threshold lines (leverage)
    thresh_y = _py_lev(thresholds_lev)
    lines.append(f'<line x1="{pad_l}" y1="{thresh_y:.1f}" x2="{pad_l + chart_w}" '
                 f'y2="{thresh_y:.1f}" stroke="{neg}" stroke-width="1" stroke-dasharray="4 3"/>')
    lines.append(f'<text x="{pad_l + chart_w + 4}" y="{thresh_y + 4:.1f}" '
                 f'fill="{neg}" font-size="9">Max {thresholds_lev:.1f}x</text>')

    # Leverage line
    for i in range(len(projections)):
        p = projections[i]
        x = _px(p.year)
        y = _py_lev(p.debt_ebitda)
        c = neg if p.debt_ebitda >= thresholds_lev else (warn if p.debt_ebitda >= thresholds_lev * 0.85 else pos)
        r = 3
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}"/>')
        if i > 0:
            pp = projections[i - 1]
            xp = _px(pp.year)
            yp = _py_lev(pp.debt_ebitda)
            lines.append(f'<line x1="{xp:.1f}" y1="{yp:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                         f'stroke="{accent}" stroke-width="1.5"/>')
        lines.append(f'<text x="{x:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
                     f'fill="{c}">{p.debt_ebitda:.1f}x</text>')
        lines.append(f'<text x="{x:.1f}" y="{pad_t + chart_h + 16}" text-anchor="middle" '
                     f'fill="{text_dim}">Yr {p.year}</text>')

    # Legend
    lines.append(f'<text x="{pad_l + 4}" y="{pad_t + 12}" fill="{accent}" font-size="9">Debt/EBITDA</text>')
    lines.append(f'<text x="{pad_l + 4}" y="{pad_t + 22}" fill="{neg}" font-size="9">--- Covenant threshold</text>')

    lines.append('</svg>')
    return "\n".join(lines)


def _moic_leverage_svg(moic_by_lev: dict) -> str:
    buckets = ["<4x", "4-5x", "5-6x", ">6x"]
    colors_map = {
        "<4x": P["positive"],
        "4-5x": P["accent"],
        "5-6x": P["warning"],
        ">6x": P["negative"],
    }
    W, H = 340, 120
    pad_l, pad_r, pad_t, pad_b = 60, 60, 16, 28
    chart_w = W - pad_l - pad_r

    max_moic = max((v for v in moic_by_lev.values() if v > 0), default=4.0) * 1.1
    bar_h = 16
    row_h = 24

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;background:{P["panel"]};border:1px solid {P["border"]}">',
    ]
    for i, b in enumerate(buckets):
        moic = moic_by_lev.get(b, 0.0)
        if moic <= 0:
            continue
        y = pad_t + i * row_h
        bw = (moic / max_moic) * chart_w
        c = colors_map[b]
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h}" fill="{c}" opacity="0.8"/>')
        lines.append(f'<text x="{pad_l - 6}" y="{y + bar_h - 4}" text-anchor="end" fill="{P["text_dim"]}">{b}</text>')
        lines.append(f'<text x="{pad_l + bw + 4:.1f}" y="{y + bar_h - 4}" fill="{c}">{moic:.2f}x</text>')
    lines.append('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _covenant_table(covenants) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, c in enumerate(covenants):
        rbg = bg2 if i % 2 else bg
        hp = f"{c.headroom_pct * 100:.1f}%" if c.headroom >= 0 else "BREACH"
        hp_color = c.status_color
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{c.label}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{c.current_value:.2f}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{c.threshold:.2f}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{hp_color}">{hp}</td>'
            f'<td style="padding:5px 8px;text-align:center"><span style="color:{c.status_color}">{c.status}</span></td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_c = f'style="padding:5px 8px;text-align:center;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Covenant</th>'
        f'<th {hdr_r}>Current</th>'
        f'<th {hdr_r}>Threshold</th>'
        f'<th {hdr_r}>Headroom</th>'
        f'<th {hdr_c}>Status</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _projection_table(projections) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, p in enumerate(projections):
        rbg = bg2 if i % 2 else bg
        lev_c = P["negative"] if not p.is_compliant else (P["warning"] if p.debt_ebitda > 5.5 else tprim)
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">Year {p.year}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{lev_c}">{p.debt_ebitda:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{p.interest_coverage:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${p.ebitda_mm:.1f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">${p.debt_mm:.1f}M</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_c = f'style="padding:5px 8px;text-align:center;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_c}>Year</th>'
        f'<th {hdr_r}>Debt/EBITDA</th>'
        f'<th {hdr_r}>Int. Coverage</th>'
        f'<th {hdr_r}>EBITDA</th>'
        f'<th {hdr_r}>Total Debt</th>'
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
        lev_c = P["negative"] if p.implied_leverage > 6.0 else (P["warning"] if p.implied_leverage > 5.0 else tprim)
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{p.company}</td>'
            f'<td style="padding:5px 8px;color:{tdim}">{p.sector[:20]}</td>'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">{p.year}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${p.ev_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{lev_c}">{p.implied_leverage:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{p.moic:.2f}x</td>'
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
        f'<th {hdr_l}>Company</th><th {hdr_l}>Sector</th>'
        f'<th {hdr_c}>Year</th><th {hdr_r}>EV</th>'
        f'<th {hdr_r}>Leverage</th><th {hdr_r}>MOIC</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _input_form(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    ev = params.get("ev", "250.0")
    ebitda = params.get("ebitda", "28.0")
    hold = params.get("hold", "1")
    growth = params.get("growth", "5.0")

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

    return f'''<form method="get" action="/covenant-monitor" style="
    background:{P["panel"]};border:1px solid {P["border"]};
    padding:14px 16px;display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr auto;
    gap:12px;align-items:end">
  <div><label style="{lbl}">Sector</label>
    <select name="sector" style="{inp}">{options}</select></div>
  <div><label style="{lbl}">EV ($M)</label>
    <input name="ev" type="number" step="1" value="{ev}" style="{inp}"></div>
  <div><label style="{lbl}">EBITDA ($M)</label>
    <input name="ebitda" type="number" step="0.5" value="{ebitda}" style="{inp}"></div>
  <div><label style="{lbl}">Hold Year</label>
    <input name="hold" type="number" step="1" min="1" max="8" value="{hold}" style="{inp}"></div>
  <div><label style="{lbl}">EBITDA Growth %/yr</label>
    <input name="growth" type="number" step="0.5" value="{growth}" style="{inp}"></div>
  <div><button type="submit" style="{btn}">Monitor</button></div>
</form>'''


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_covenant_monitor(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    try:
        ev_mm = float(params.get("ev", "250.0"))
    except (ValueError, TypeError):
        ev_mm = 250.0
    try:
        ebitda_mm = float(params.get("ebitda", "28.0"))
    except (ValueError, TypeError):
        ebitda_mm = 28.0
    try:
        hold_yr = int(params.get("hold", "1"))
    except (ValueError, TypeError):
        hold_yr = 1
    try:
        growth = float(params.get("growth", "5.0"))
    except (ValueError, TypeError):
        growth = 5.0

    from rcm_mc.data_public.covenant_monitor import compute_covenant_monitor
    r = compute_covenant_monitor(sector, ev_mm, ebitda_mm, hold_yr, ebitda_growth_pct=growth)

    # KPIs
    lev_cov = r.covenants[0]
    icr_cov = r.covenants[1]

    kpis = ck_kpi_block("Overall Status",
                        f'<span style="color:{r.overall_color}">{r.overall_status}</span>')
    kpis += ck_kpi_block("Entry Leverage", f"{r.entry_leverage:.2f}x",
                         unit=f"Sz bucket: {r.size_bucket}")
    kpis += ck_kpi_block("Current Leverage", f"{r.current_leverage:.2f}x",
                         unit=f"Threshold: {lev_cov.threshold:.1f}x",
                         delta=f"{lev_cov.headroom_pct * 100:.1f}% headroom")
    kpis += ck_kpi_block("Int. Coverage", f"{r.interest_coverage:.2f}x",
                         unit=f"Min: {icr_cov.threshold:.1f}x",
                         delta=f"{icr_cov.headroom_pct * 100:.1f}% headroom")
    kpis += ck_kpi_block("Sector Med. Leverage", f"{r.sector_median_leverage:.2f}x",
                         unit=f"P75: {r.sector_p75_leverage:.2f}x")
    kpis += ck_kpi_block("Corpus Deals", str(r.corpus_deal_count), unit="")

    thresholds_lev = r.covenants[0].threshold
    thresholds_icr = r.covenants[1].threshold

    timeline_svg = _leverage_timeline_svg(r.projections, thresholds_lev, thresholds_icr)
    moic_lev_svg = _moic_leverage_svg(r.moic_by_leverage_bucket)
    cov_tbl = _covenant_table(r.covenants)
    proj_tbl = _projection_table(r.projections)
    peers_tight_tbl = _peers_table(r.peers_tight, "Tightly Leveraged Peers")
    peers_comf_tbl = _peers_table(r.peers_comfortable, "Conservatively Leveraged Peers")

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

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Leverage Trajectory — 6-Year Projection
  </div>
  {timeline_svg}
</div>

<div style="display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Covenant Status
    </div>
    {cov_tbl}
    <div style="margin-top:10px">
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
        text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px">
        Annual Projection
      </div>
      {proj_tbl}
    </div>
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      MOIC by Entry Leverage Bucket
    </div>
    {moic_lev_svg}
    <div style="margin-top:12px;padding:8px;background:{bg_tert};border:1px solid {border}">
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim}">
        Sector Leverage Benchmarks
      </div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:13px;
        color:{tprim};margin-top:6px;font-variant-numeric:tabular-nums">
        Median: {r.sector_median_leverage:.2f}x &nbsp;|&nbsp; P75: {r.sector_p75_leverage:.2f}x
      </div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};margin-top:4px">
        Based on {r.corpus_deal_count} corpus deals
      </div>
    </div>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    {peers_tight_tbl}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    {peers_comf_tbl}
  </div>
</div>
'''

    return chartis_shell(
        body=content,
        title=f"Covenant Monitor — {sector}",
        active_nav="/covenant-monitor",
    )
