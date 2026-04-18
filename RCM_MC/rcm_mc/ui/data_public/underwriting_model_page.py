"""Underwriting Model page — /underwriting-model."""
from __future__ import annotations

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


_SECTORS = [
    "Physician Group", "Behavioral Health", "Dental", "Dermatology",
    "Urgent Care", "Ambulatory Surgery", "Home Health", "Hospice",
    "Radiology", "Laboratory", "Orthopedics", "Cardiology",
    "Health IT", "Revenue Cycle Management", "Staffing",
]

_HOLD_YEARS = [3, 4, 5, 6, 7]


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _sources_uses_svg(sources, uses) -> str:
    W, H = 400, 130
    bar_h = 30
    pad_l, pad_r, pad_t = 10, 10, 20
    chart_w = W - pad_l - pad_r

    def _segment(x, w, color, label, amount, y) -> str:
        out = f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{color}" opacity="0.85"/>'
        if w > 40:
            out += (f'<text x="{x + w/2:.1f}" y="{y + bar_h - 8}" text-anchor="middle" '
                    f'fill="{P["bg"]}" font-size="9">{label}</text>')
            out += (f'<text x="{x + w/2:.1f}" y="{y + bar_h - 1}" text-anchor="middle" '
                    f'fill="{P["bg"]}" font-size="8" font-variant-numeric="tabular-nums">${amount:.0f}M</text>')
        return out

    total = uses.total_mm
    y_src = pad_t
    y_use = pad_t + bar_h + 10

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
        f'<text x="{pad_l}" y="{pad_t - 4}" fill="{P["text_dim"]}" font-size="9">SOURCES</text>',
        f'<text x="{pad_l}" y="{y_use - 4}" fill="{P["text_dim"]}" font-size="9">USES</text>',
    ]

    # Sources bar
    x = pad_l
    for label, amt, color in [
        ("Senior", sources.senior_debt_mm, P["accent"]),
        ("Sub", sources.sub_debt_mm, "#a855f7"),
        ("Equity", sources.equity_mm, P["positive"]),
    ]:
        w = (amt / total) * chart_w
        lines.append(_segment(x, w, color, label, amt, y_src))
        x += w

    # Uses bar
    x = pad_l
    for label, amt, color in [
        ("Purchase Price", uses.purchase_price_mm, P["warning"]),
        ("Fees", uses.financing_fees_mm, "#64748b"),
        ("Txn Costs", uses.transaction_costs_mm, "#475569"),
    ]:
        w = (amt / total) * chart_w
        lines.append(_segment(x, w, color, label, amt, y_use))
        x += w

    lines.append('</svg>')
    return "\n".join(lines)


def _fcf_chart_svg(projections) -> str:
    W, H = 500, 120
    pad_l, pad_r, pad_t, pad_b = 50, 20, 16, 30
    chart_w = W - pad_l - pad_r
    chart_h = H - pad_t - pad_b

    fcfs = [p.fcf_mm for p in projections]
    max_fcf = max(fcfs) * 1.15 or 1.0
    bar_w = chart_w / len(projections) * 0.7
    gap = chart_w / len(projections)

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
        f'<line x1="{pad_l}" y1="{pad_t + chart_h}" x2="{pad_l + chart_w}" '
        f'y2="{pad_t + chart_h}" stroke="{P["border"]}" stroke-width="1"/>',
    ]

    for i, p in enumerate(projections):
        x = pad_l + i * gap + gap * 0.15
        bh = (p.fcf_mm / max_fcf) * chart_h if max_fcf > 0 else 0
        y = pad_t + chart_h - bh
        c = P["positive"] if p.fcf_mm >= 0 else P["negative"]
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" '
                     f'fill="{c}" opacity="0.8"/>')
        lines.append(f'<text x="{x + bar_w/2:.1f}" y="{pad_t + chart_h + 16}" '
                     f'text-anchor="middle" fill="{P["text_dim"]}">Yr {p.year}</text>')
        lines.append(f'<text x="{x + bar_w/2:.1f}" y="{y - 3:.1f}" '
                     f'text-anchor="middle" fill="{c}" font-size="9">${p.fcf_mm:.1f}M</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _projection_table(projections) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, p in enumerate(projections):
        rbg = bg2 if i % 2 else bg
        lev_c = P["negative"] if p.leverage_ratio > 6.5 else (P["warning"] if p.leverage_ratio > 5.0 else tprim)
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">Yr {p.year}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${p.revenue_mm:.1f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${p.ebitda_mm:.1f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{p.ebitda_margin*100:.1f}%</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">${p.interest_mm:.1f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${p.fcf_mm:.1f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{lev_c}">{p.leverage_ratio:.2f}x</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_c = f'style="padding:5px 8px;text-align:center;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_c}>Year</th>'
        f'<th {hdr_r}>Revenue</th>'
        f'<th {hdr_r}>EBITDA</th>'
        f'<th {hdr_r}>Margin</th>'
        f'<th {hdr_r}>Interest</th>'
        f'<th {hdr_r}>FCF</th>'
        f'<th {hdr_r}>Lev.</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _returns_table(scenarios) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, s in enumerate(scenarios):
        rbg = bg2 if i % 2 else bg
        moic_c = P["positive"] if s.moic >= 3.0 else (P["warning"] if s.moic >= 2.0 else P["negative"])
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">Year {s.hold_years}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{s.exit_multiple:.1f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${s.exit_ev_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${s.exit_equity_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{moic_c}">{s.moic:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{s.irr*100:.1f}%</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{s.cash_yield_pct:.1f}%</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_c = f'style="padding:5px 8px;text-align:center;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_c}>Exit Year</th>'
        f'<th {hdr_r}>Exit Mult.</th>'
        f'<th {hdr_r}>Exit EV</th>'
        f'<th {hdr_r}>Exit Equity</th>'
        f'<th {hdr_r}>MOIC</th>'
        f'<th {hdr_r}>IRR</th>'
        f'<th {hdr_r}>Cash Yield</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _sensitivity_table(sensitivity_table, entry_multiple: float) -> str:
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]
    bg = P["bg"]
    bg2 = P["panel"]

    hold_cols = [k for k in sensitivity_table[0].keys() if k.startswith("hold_")]
    hold_labels = [k.replace("hold_", "Yr ") for k in hold_cols]

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    header = f'<tr><th {hdr_l}>Exit Mult.</th>' + "".join(f'<th {hdr_r}>{lbl}</th>' for lbl in hold_labels) + '</tr>'

    rows = []
    for i, row in enumerate(sensitivity_table):
        rbg = bg2 if i % 2 else bg
        em = row["exit_multiple"]
        em_label = f'{em:.1f}x'
        cells = [f'<td style="padding:5px 8px;color:{tdim};font-variant-numeric:tabular-nums">{em_label}</td>']
        for col in hold_cols:
            val = row.get(col)
            if val is None:
                cells.append(f'<td style="padding:5px 8px;text-align:right;color:{tdim}">—</td>')
            else:
                c = P["positive"] if val >= 3.0 else (P["warning"] if val >= 2.0 else P["negative"])
                cells.append(f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{c}">{val:.2f}x</td>')
        rows.append(f'<tr style="background:{rbg}">{"".join(cells)}</tr>')

    return (
        f'<table style="border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead>{header}</thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _input_form(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    ev = params.get("ev", "250.0")
    ebitda = params.get("ebitda", "25.0")
    rev = params.get("rev", "")
    growth = params.get("growth", "8.0")
    margin_exp = params.get("margin_exp", "2.0")
    exit_mult = params.get("exit_mult", "")

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

    return f'''<form method="get" action="/underwriting-model" style="
    background:{P["panel"]};border:1px solid {P["border"]};
    padding:14px 16px;display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr 1fr auto;
    gap:10px;align-items:end">
  <div><label style="{lbl}">Sector</label>
    <select name="sector" style="{inp}">{options}</select></div>
  <div><label style="{lbl}">EV ($M)</label>
    <input name="ev" type="number" step="5" value="{ev}" style="{inp}"></div>
  <div><label style="{lbl}">EBITDA ($M)</label>
    <input name="ebitda" type="number" step="0.5" value="{ebitda}" style="{inp}"></div>
  <div><label style="{lbl}">Revenue ($M)</label>
    <input name="rev" type="number" step="5" value="{rev}" placeholder="auto" style="{inp}"></div>
  <div><label style="{lbl}">Rev. Growth %</label>
    <input name="growth" type="number" step="0.5" value="{growth}" style="{inp}"></div>
  <div><label style="{lbl}">Margin Exp. pp</label>
    <input name="margin_exp" type="number" step="0.5" value="{margin_exp}" style="{inp}"></div>
  <div><label style="{lbl}">Exit Mult.</label>
    <input name="exit_mult" type="number" step="0.5" value="{exit_mult}" placeholder="entry+1" style="{inp}"></div>
  <div><button type="submit" style="{btn}">Model</button></div>
</form>'''


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_underwriting_model(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    try:
        ev_mm = float(params.get("ev", "250.0"))
    except (ValueError, TypeError):
        ev_mm = 250.0
    try:
        ebitda_mm = float(params.get("ebitda", "25.0"))
    except (ValueError, TypeError):
        ebitda_mm = 25.0
    rev_mm = None
    try:
        rv = params.get("rev", "")
        if rv:
            rev_mm = float(rv)
    except (ValueError, TypeError):
        pass
    try:
        growth = float(params.get("growth", "8.0"))
    except (ValueError, TypeError):
        growth = 8.0
    try:
        margin_exp = float(params.get("margin_exp", "2.0"))
    except (ValueError, TypeError):
        margin_exp = 2.0
    exit_mult = None
    try:
        em = params.get("exit_mult", "")
        if em:
            exit_mult = float(em)
    except (ValueError, TypeError):
        pass

    from rcm_mc.data_public.underwriting_model import compute_underwriting_model
    r = compute_underwriting_model(sector, ev_mm, ebitda_mm, rev_mm, None, growth, margin_exp, None, exit_mult)

    base_sc = next((s for s in r.return_scenarios if s.hold_years == 5), r.return_scenarios[-1]) if r.return_scenarios else None
    base_moic = f"{base_sc.moic:.2f}x" if base_sc else "—"
    base_irr = f"{base_sc.irr*100:.1f}%" if base_sc else "—"

    kpis = ck_kpi_block("Entry EV/EBITDA", f"{r.entry_multiple:.1f}x",
                         unit=f"EV: ${r.ev_mm:.0f}M / Size: {r.size_bucket}")
    kpis += ck_kpi_block("Total Leverage", f"{r.sources.leverage_ratio:.2f}x",
                          unit=f"Equity: {r.sources.equity_pct*100:.0f}% / ${r.sources.equity_mm:.0f}M")
    kpis += ck_kpi_block("Base MOIC (5yr)", base_moic, unit=f"IRR: {base_irr}")
    kpis += ck_kpi_block("Corpus P50 MOIC", f"{r.corpus_p50_moic:.2f}x",
                          unit=f"P25: {r.corpus_p25_moic:.2f}x / P75: {r.corpus_p75_moic:.2f}x")
    kpis += ck_kpi_block("Interest Rate", f"{r.sources.senior_debt_mm:.0f}M sr / {r.sources.sub_debt_mm:.0f}M sub")
    kpis += ck_kpi_block("Corpus Deals", str(r.corpus_deal_count))

    src_uses_svg = _sources_uses_svg(r.sources, r.uses)
    fcf_svg = _fcf_chart_svg(r.projections)
    proj_tbl = _projection_table(r.projections)
    ret_tbl = _returns_table(r.return_scenarios)
    sens_tbl = _sensitivity_table(r.sensitivity_table, r.entry_multiple)

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

<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Sources &amp; Uses
    </div>
    {src_uses_svg}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Free Cash Flow by Year
    </div>
    {fcf_svg}
  </div>
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Income Statement Projections
  </div>
  {proj_tbl}
</div>

<div style="display:grid;grid-template-columns:3fr 2fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Returns by Exit Year
    </div>
    {ret_tbl}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      MOIC Sensitivity — Exit Multiple × Hold Year
    </div>
    {sens_tbl}
    <div style="margin-top:10px;padding:8px;background:{bg_tert};border:1px solid {border};
      font-family:\'JetBrains Mono\',monospace;font-size:9px;color:{tdim}">
      Color: <span style="color:{P["positive"]}">&#9632;</span> ≥3.0x &nbsp;
      <span style="color:{P["warning"]}">&#9632;</span> ≥2.0x &nbsp;
      <span style="color:{P["negative"]}">&#9632;</span> &lt;2.0x
    </div>
  </div>
</div>
'''

    return chartis_shell(
        body=content,
        title=f"Underwriting Model — {sector}",
        active_nav="/underwriting-model",
    )
