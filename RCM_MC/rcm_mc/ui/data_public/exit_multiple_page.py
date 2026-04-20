"""Exit Multiple Analysis page — /exit-multiple."""
from __future__ import annotations

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


_SECTORS = [
    "Physician Group", "Behavioral Health", "Dental", "Dermatology",
    "Urgent Care", "Ambulatory Surgery", "Home Health", "Hospice",
    "Radiology", "Laboratory", "Orthopedics", "Cardiology",
    "Gastroenterology", "Ophthalmology", "Physical Therapy",
    "Health IT", "Revenue Cycle Management",
]

_SCENARIO_COLORS = {
    "Bear": "#ef4444",
    "Base": "#3b82f6",
    "Bull": "#22c55e",
    "Strategic Exit": "#a855f7",
}


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _scenario_chart_svg(scenarios, entry_multiple: float) -> str:
    W, H = 700, 160
    pad_l, pad_r, pad_t, pad_b = 50, 120, 20, 40
    chart_w = W - pad_l - pad_r
    chart_h = H - pad_t - pad_b

    max_mult = max(s.exit_multiple for s in scenarios) * 1.1
    bar_h = 18
    row_h = 28
    n = len(scenarios)

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    # Entry multiple line
    entry_x = pad_l + (entry_multiple / max_mult) * chart_w
    lines.append(f'<line x1="{entry_x:.1f}" y1="{pad_t}" x2="{entry_x:.1f}" '
                 f'y2="{pad_t + chart_h}" stroke="{P["text_faint"]}" stroke-width="1" stroke-dasharray="3 3"/>')
    lines.append(f'<text x="{entry_x:.1f}" y="{pad_t - 4}" text-anchor="middle" '
                 f'fill="{P["text_faint"]}" font-size="9">Entry {entry_multiple:.1f}x</text>')

    for i, s in enumerate(scenarios):
        y = pad_t + i * row_h + 4
        bw = (s.exit_multiple / max_mult) * chart_w
        c = _SCENARIO_COLORS.get(s.label, P["accent"])
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
                     f'fill="{c}" opacity="0.8"/>')
        lines.append(f'<text x="{pad_l - 4}" y="{y + bar_h - 4}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{s.label}</text>')
        lines.append(f'<text x="{pad_l + bw + 4:.1f}" y="{y + bar_h - 4}" '
                     f'fill="{c}">{s.exit_multiple:.1f}x · {s.moic:.2f}x MOIC</text>')

    lines.append('</svg>')
    return "\n".join(lines)


def _decomp_svg(decomp) -> str:
    W, H = 500, 30 + len(decomp) * 28
    pad_l, pad_r = 180, 80

    max_turns = max(abs(d.contribution_turns) for d in decomp if d.contribution_turns != 0) * 1.2 or 1.0
    chart_w = W - pad_l - pad_r

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    for i, d in enumerate(decomp):
        y = 16 + i * 28
        bw = abs(d.contribution_turns) / max_turns * chart_w if max_turns > 0 else 0
        c = P["positive"] if d.contribution_turns >= 0 else P["negative"]
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="16" fill="{c}" opacity="0.75"/>')
        lines.append(f'<text x="{pad_l - 6}" y="{y + 12}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{d.label}</text>')
        sign = "+" if d.contribution_turns >= 0 else ""
        lines.append(f'<text x="{pad_l + bw + 4:.1f}" y="{y + 12}" '
                     f'fill="{c}">{sign}{d.contribution_turns:.2f}x</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _scenario_table(scenarios) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, s in enumerate(scenarios):
        rbg = bg2 if i % 2 else bg
        c = _SCENARIO_COLORS.get(s.label, P["accent"])
        exp_str = f"+{s.multiple_expansion:.1f}x" if s.multiple_expansion >= 0 else f"{s.multiple_expansion:.1f}x"
        exp_c = P["positive"] if s.multiple_expansion >= 0 else P["negative"]
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{c};font-weight:600">{s.label}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{s.exit_multiple:.1f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{exp_c}">{exp_str}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${s.ev_at_exit_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{s.moic:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{s.irr*100:.1f}%</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{s.probability*100:.0f}%</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Scenario</th>'
        f'<th {hdr_r}>Exit EV/EBITDA</th>'
        f'<th {hdr_r}>Multiple Exp.</th>'
        f'<th {hdr_r}>Exit EV</th>'
        f'<th {hdr_r}>MOIC</th>'
        f'<th {hdr_r}>IRR</th>'
        f'<th {hdr_r}>Prob.</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _comps_table(comparables) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, c in enumerate(comparables):
        rbg = bg2 if i % 2 else bg
        exp_c = P["positive"] if c.multiple_expansion >= 0 else P["negative"]
        exp_str = f"+{c.multiple_expansion:.1f}x" if c.multiple_expansion >= 0 else f"{c.multiple_expansion:.1f}x"
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{c.company}</td>'
            f'<td style="padding:5px 8px;color:{tdim}">{c.sector[:18]}</td>'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">{c.year}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{c.entry_multiple:.1f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{c.exit_multiple_implied:.1f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{exp_c}">{exp_str}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{c.moic:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{c.hold_years:.1f}yr</td>'
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
        f'<th {hdr_r}>Implied Exit</th>'
        f'<th {hdr_r}>Expansion</th>'
        f'<th {hdr_r}>MOIC</th>'
        f'<th {hdr_r}>Hold</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _input_form(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    entry = params.get("entry", "10.0")
    ebitda = params.get("ebitda", "25.0")
    hold = params.get("hold", "5.0")
    growth = params.get("growth", "8.0")
    comm = params.get("comm", "0.55")
    year = params.get("year", "2020")

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

    return f'''<form method="get" action="/exit-multiple" style="
    background:{P["panel"]};border:1px solid {P["border"]};
    padding:14px 16px;display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr 1fr auto;
    gap:10px;align-items:end">
  <div><label style="{lbl}">Sector</label>
    <select name="sector" style="{inp}">{options}</select></div>
  <div><label style="{lbl}">Entry EV/EBITDA</label>
    <input name="entry" type="number" step="0.5" value="{entry}" style="{inp}"></div>
  <div><label style="{lbl}">EBITDA ($M)</label>
    <input name="ebitda" type="number" step="0.5" value="{ebitda}" style="{inp}"></div>
  <div><label style="{lbl}">Hold (yrs)</label>
    <input name="hold" type="number" step="0.5" value="{hold}" style="{inp}"></div>
  <div><label style="{lbl}">EBITDA Growth %</label>
    <input name="growth" type="number" step="0.5" value="{growth}" style="{inp}"></div>
  <div><label style="{lbl}">Commercial %</label>
    <input name="comm" type="number" step="0.01" value="{comm}" style="{inp}"></div>
  <div><label style="{lbl}">Entry Year</label>
    <input name="year" type="number" step="1" value="{year}" style="{inp}"></div>
  <div><button type="submit" style="{btn}">Model</button></div>
</form>'''


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_exit_multiple(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    try:
        entry = float(params.get("entry", "10.0"))
    except (ValueError, TypeError):
        entry = 10.0
    try:
        ebitda_mm = float(params.get("ebitda", "25.0"))
    except (ValueError, TypeError):
        ebitda_mm = 25.0
    try:
        hold = float(params.get("hold", "5.0"))
    except (ValueError, TypeError):
        hold = 5.0
    try:
        growth = float(params.get("growth", "8.0"))
    except (ValueError, TypeError):
        growth = 8.0
    try:
        comm = float(params.get("comm", "0.55"))
    except (ValueError, TypeError):
        comm = 0.55
    try:
        year = int(params.get("year", "2020"))
    except (ValueError, TypeError):
        year = 2020

    from rcm_mc.data_public.exit_multiple import compute_exit_multiple
    r = compute_exit_multiple(sector, entry, ebitda_mm, hold, growth, comm, year)

    base_sc = next((s for s in r.scenarios if s.label == "Base"), r.scenarios[1])
    bull_sc = next((s for s in r.scenarios if s.label == "Bull"), r.scenarios[2])

    timing_str = (f"+{r.timing_premium:.1f}x timing premium" if r.timing_premium >= 0
                  else f"{r.timing_premium:.1f}x timing drag")

    kpis = ck_kpi_block("Entry EV/EBITDA", f"{r.entry_multiple:.1f}x",
                         unit=f"EV: ${r.ev_mm:.0f}M")
    kpis += ck_kpi_block("Base Exit Multiple", f"{r.base_exit_multiple:.1f}x",
                          unit=timing_str)
    kpis += ck_kpi_block("Sector P25/P50/P75",
                          f"{r.sector_p25:.1f}x / {r.sector_p50:.1f}x / {r.sector_p75:.1f}x")
    kpis += ck_kpi_block("Base MOIC", f"{base_sc.moic:.2f}x",
                          unit=f"IRR: {base_sc.irr*100:.1f}%")
    kpis += ck_kpi_block("Bull MOIC", f"{bull_sc.moic:.2f}x",
                          unit=f"IRR: {bull_sc.irr*100:.1f}%")
    kpis += ck_kpi_block("MOIC/Turn Sensitivity", f"{r.moic_sensitivity_per_turn:.2f}x",
                          unit="per 1x multiple turn")

    chart = _scenario_chart_svg(r.scenarios, r.entry_multiple)
    decomp_svg = _decomp_svg(r.decomp)
    sc_tbl = _scenario_table(r.scenarios)
    comp_tbl = _comps_table(r.comparables)

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
    Exit Scenario Range
  </div>
  {chart}
</div>

<div style="display:grid;grid-template-columns:3fr 2fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Scenario Detail
    </div>
    {sc_tbl}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Multiple Expansion Decomposition
    </div>
    {decomp_svg}
  </div>
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Corpus Comparables — Implied Exit Multiples
  </div>
  {comp_tbl}
</div>
'''

    return chartis_shell(
        body=content,
        title=f"Exit Multiple Analysis — {sector}",
        active_nav="/exit-multiple",
    )
