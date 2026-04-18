"""Value Creation Tracker page — /value-creation."""
from __future__ import annotations

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


_SECTORS = [
    "Physician Group", "Behavioral Health", "Dental", "Dermatology",
    "Urgent Care", "Ambulatory Surgery", "Home Health", "Hospice",
    "Radiology", "Laboratory", "Orthopedics", "Cardiology",
    "Health IT", "Revenue Cycle Management",
]

_LEVER_COLORS = {
    "revenue_growth":         "#22c55e",
    "ebitda_margin_expansion": "#3b82f6",
    "add_on_acquisitions":    "#a855f7",
    "multiple_expansion":     "#f59e0b",
    "leverage_paydown":       "#64748b",
}


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _bridge_svg(r) -> str:
    W, H = 760, 160
    pad_l, pad_r, pad_t, pad_b = 50, 60, 20, 40
    chart_w = W - pad_l - pad_r
    chart_h = H - pad_t - pad_b

    max_val = r.exit_ev_mm * 1.05
    bar_h = 22
    row_h = 30
    n = len(r.levers) + 2
    total_h = pad_t + n * row_h + pad_b

    def _bx(val: float) -> float:
        return pad_l + (val / max_val) * chart_w

    lines = [
        f'<svg viewBox="0 0 {W} {total_h}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    # Entry EV bar
    y = pad_t
    bw = _bx(r.entry_ev_mm) - pad_l
    lines.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
                 f'fill="{P["accent"]}" opacity="0.85"/>')
    lines.append(f'<text x="{pad_l - 4}" y="{y + bar_h - 5}" text-anchor="end" '
                 f'fill="{P["text_dim"]}">Entry EV</text>')
    lines.append(f'<text x="{_bx(r.entry_ev_mm) + 4:.1f}" y="{y + bar_h - 5}" '
                 f'fill="{P["text"]}">${r.entry_ev_mm:.0f}M</text>')

    running = r.entry_ev_mm
    for i, lev in enumerate(r.levers):
        y = pad_t + (i + 1) * row_h
        start_x = _bx(running)
        end_x = _bx(running + lev.ev_contribution_mm)
        bw = end_x - start_x
        c = _LEVER_COLORS.get(lev.lever_id, P["text_dim"])
        lines.append(f'<rect x="{start_x:.1f}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
                     f'fill="{c}" opacity="0.75"/>')
        lines.append(f'<text x="{pad_l - 4}" y="{y + bar_h - 5}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{lev.label[:22]}</text>')
        pct_s = f"+{lev.contribution_pct*100:.0f}%"
        lines.append(f'<text x="{end_x + 4:.1f}" y="{y + bar_h - 5}" fill="{c}">{pct_s}</text>')
        running += lev.ev_contribution_mm

    # Exit EV
    y = pad_t + (len(r.levers) + 1) * row_h
    bw = _bx(r.exit_ev_mm) - pad_l
    lines.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
                 f'fill="{P["positive"]}" opacity="0.9"/>')
    lines.append(f'<text x="{pad_l - 4}" y="{y + bar_h - 5}" text-anchor="end" '
                 f'fill="{P["text"]}" font-weight="600">Exit EV</text>')
    lines.append(f'<text x="{_bx(r.exit_ev_mm) + 4:.1f}" y="{y + bar_h - 5}" '
                 f'fill="{P["positive"]}" font-weight="600">${r.exit_ev_mm:.0f}M</text>')

    lines.append('</svg>')
    return "\n".join(lines)


def _rcm_initiative_svg(initiatives) -> str:
    W = 500
    bar_h = 14
    row_h = 22
    pad_l = 200
    pad_r = 80
    pad_t = 16
    chart_w = W - pad_l - pad_r
    total_h = pad_t + len(initiatives) * row_h + 16

    max_mm = max(i.ebitda_impact_mm for i in initiatives) * 1.2 or 1.0

    lines = [
        f'<svg viewBox="0 0 {W} {total_h}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    for i, init in enumerate(initiatives):
        y = pad_t + i * row_h
        bw = (init.ebitda_impact_mm / max_mm) * chart_w
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
                     f'fill="{P["positive"]}" opacity="0.7"/>')
        lines.append(f'<text x="{pad_l - 6}" y="{y + bar_h - 2}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{init.label[:28]}</text>')
        lines.append(f'<text x="{pad_l + bw + 4:.1f}" y="{y + bar_h - 2}" '
                     f'fill="{P["positive"]}">${init.ebitda_impact_mm:.2f}M</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _levers_table(levers) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, lev in enumerate(levers):
        rbg = bg2 if i % 2 else bg
        c = _LEVER_COLORS.get(lev.lever_id, tdim)
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{c}">{lev.label}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{lev.contribution_pct*100:.0f}%</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">+${lev.ebitda_contribution_mm:.1f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">+${lev.ev_contribution_mm:.0f}M</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Value Lever</th>'
        f'<th {hdr_r}>% Share</th>'
        f'<th {hdr_r}>EBITDA Contrib.</th>'
        f'<th {hdr_r}>EV Contrib.</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _peers_table(peers) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, p in enumerate(peers[:10]):
        rbg = bg2 if i % 2 else bg
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{p.company}</td>'
            f'<td style="padding:5px 8px;color:{tdim}">{p.sector[:18]}</td>'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">{p.year}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{p.entry_multiple:.1f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{p.moic:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{p.irr*100:.1f}%</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{p.hold_years:.1f}yr</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{p.implied_rev_growth*100:.1f}%</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_c = f'style="padding:5px 8px;text-align:center;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Company</th>'
        f'<th {hdr_l}>Sector</th>'
        f'<th {hdr_c}>Year</th>'
        f'<th {hdr_r}>Entry Mult.</th>'
        f'<th {hdr_r}>MOIC</th>'
        f'<th {hdr_r}>IRR</th>'
        f'<th {hdr_r}>Hold</th>'
        f'<th {hdr_r}>Impl. Rev%</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _input_form(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    ebitda = params.get("ebitda", "25.0")
    mult = params.get("mult", "10.0")
    hold = params.get("hold", "5.0")
    growth = params.get("growth", "8.0")
    mult_exp = params.get("mult_exp", "1.5")

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

    return f'''<form method="get" action="/value-creation" style="
    background:{P["panel"]};border:1px solid {P["border"]};
    padding:14px 16px;display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr auto;
    gap:10px;align-items:end">
  <div><label style="{lbl}">Sector</label>
    <select name="sector" style="{inp}">{options}</select></div>
  <div><label style="{lbl}">Entry EBITDA ($M)</label>
    <input name="ebitda" type="number" step="0.5" value="{ebitda}" style="{inp}"></div>
  <div><label style="{lbl}">Entry EV/EBITDA</label>
    <input name="mult" type="number" step="0.5" value="{mult}" style="{inp}"></div>
  <div><label style="{lbl}">Hold (yrs)</label>
    <input name="hold" type="number" step="0.5" value="{hold}" style="{inp}"></div>
  <div><label style="{lbl}">EBITDA Growth %</label>
    <input name="growth" type="number" step="0.5" value="{growth}" style="{inp}"></div>
  <div><label style="{lbl}">Multiple Expansion</label>
    <input name="mult_exp" type="number" step="0.5" value="{mult_exp}" style="{inp}"></div>
  <div><button type="submit" style="{btn}">Model</button></div>
</form>'''


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_value_creation(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    try:
        ebitda_mm = float(params.get("ebitda", "25.0"))
    except (ValueError, TypeError):
        ebitda_mm = 25.0
    try:
        mult = float(params.get("mult", "10.0"))
    except (ValueError, TypeError):
        mult = 10.0
    try:
        hold = float(params.get("hold", "5.0"))
    except (ValueError, TypeError):
        hold = 5.0
    try:
        growth = float(params.get("growth", "8.0"))
    except (ValueError, TypeError):
        growth = 8.0
    try:
        mult_exp = float(params.get("mult_exp", "1.5"))
    except (ValueError, TypeError):
        mult_exp = 1.5

    from rcm_mc.data_public.value_creation import compute_value_creation
    r = compute_value_creation(sector, ebitda_mm, mult, hold, growth, mult_exp)

    ev_created_pct = r.total_ev_created_mm / r.entry_ev_mm * 100 if r.entry_ev_mm else 0

    kpis = ck_kpi_block("Entry EV", f"${r.entry_ev_mm:.0f}M",
                         unit=f"{r.entry_multiple:.1f}x EV/EBITDA")
    kpis += ck_kpi_block("Exit EV", f"${r.exit_ev_mm:.0f}M",
                          unit=f"{r.exit_multiple:.1f}x EV/EBITDA")
    kpis += ck_kpi_block("EV Created", f"${r.total_ev_created_mm:.0f}M",
                          unit=f"+{ev_created_pct:.0f}% vs entry")
    kpis += ck_kpi_block("MOIC", f"{r.moic:.2f}x",
                          unit=f"IRR: {r.irr*100:.1f}%")
    kpis += ck_kpi_block("Sector Median MOIC", f"{r.sector_median_moic:.2f}x")
    kpis += ck_kpi_block("Corpus Deals", str(r.corpus_deal_count))

    bridge = _bridge_svg(r)
    rcm_svg = _rcm_initiative_svg(r.rcm_initiatives)
    lever_tbl = _levers_table(r.levers)
    peer_tbl = _peers_table(r.peers)

    bg_sec = P["panel"]
    bg_tert = P["panel_alt"]
    border = P["border"]
    tprim = P["text"]
    tdim = P["text_dim"]

    rcm_total = sum(i.ebitda_impact_mm for i in r.rcm_initiatives)
    rcm_total_npv = sum(i.cumulative_npv_mm for i in r.rcm_initiatives)

    content = f'''
{_input_form(params)}

<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:12px">
{kpis}
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    EV Bridge — Entry to Exit
  </div>
  {bridge}
</div>

<div style="display:grid;grid-template-columns:3fr 2fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Value Creation by Lever
    </div>
    {lever_tbl}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      RCM Initiative Upside
    </div>
    {rcm_svg}
    <div style="margin-top:8px;padding:8px;background:{bg_tert};border:1px solid {border}">
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim}">
        Total RCM EBITDA Opportunity
      </div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:16px;
        color:{P["positive"]};font-variant-numeric:tabular-nums;margin-top:4px">
        +${rcm_total:.1f}M
      </div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};margin-top:3px">
        NPV over hold: ${rcm_total_npv:.1f}M
      </div>
    </div>
  </div>
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Top Performing Peers — {sector}
  </div>
  {peer_tbl}
</div>
'''

    return chartis_shell(
        body=content,
        title=f"Value Creation Tracker — {sector}",
        active_nav="/value-creation",
    )
