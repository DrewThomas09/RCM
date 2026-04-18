"""Quality of Earnings Analyzer page — /qoe-analyzer."""
from __future__ import annotations

from typing import Dict

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block
from rcm_mc.ui.chartis._helpers import render_page_explainer


_SECTORS = [
    "Physician Group", "Behavioral Health", "Dental", "Dermatology",
    "Urgent Care", "Ambulatory Surgery", "Home Health", "Hospice",
    "Radiology", "Orthopedics", "Cardiology", "Gastroenterology",
    "Ophthalmology", "Physical Therapy", "Laboratory",
]


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _waterfall_svg(breakdowns, reported: float, adjusted: float) -> str:
    W, H = 760, 220
    pad_l, pad_r, pad_t, pad_b = 140, 20, 20, 40
    chart_w = W - pad_l - pad_r
    chart_h = H - pad_t - pad_b

    max_val = adjusted * 1.05
    def _x(val: float) -> float:
        return pad_l + (val / max_val) * chart_w

    bar_h = 16
    row_h = 26
    n_bars = len(breakdowns) + 2  # reported + addbacks + adjusted
    total_h = pad_t + n_bars * row_h + pad_b + 20

    lines = [
        f'<svg viewBox="0 0 {W} {total_h}" width="100%" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    # Zero line
    zero_x = _x(0)
    lines.append(f'<line x1="{zero_x}" y1="{pad_t}" x2="{zero_x}" '
                 f'y2="{total_h - pad_b}" stroke="{P["border_dim"]}" stroke-width="1"/>')

    # Reported EBITDA bar
    y0 = pad_t + 4
    bx = _x(0)
    bw = _x(reported) - bx
    lines.append(f'<rect x="{bx:.1f}" y="{y0}" width="{bw:.1f}" height="{bar_h}" '
                 f'fill="{P["accent"]}" opacity="0.85"/>')
    lines.append(f'<text x="{pad_l - 6}" y="{y0 + bar_h - 3}" text-anchor="end" '
                 f'fill="{P["text_dim"]}">Reported EBITDA</text>')
    lines.append(f'<text x="{_x(reported) + 4:.1f}" y="{y0 + bar_h - 3}" '
                 f'fill="{P["text"]}">${reported:.1f}M</text>')

    # Add-back bars
    running = reported
    for i, b in enumerate(breakdowns):
        y = pad_t + (i + 1) * row_h + 4
        bx = _x(running)
        bw = _x(running + b.amount_mm) - bx
        color = P["positive"] if b.quality_flag == "Defensible" else \
                P["warning"] if b.quality_flag == "Scrutinize" else P["negative"]
        lines.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
                     f'fill="{color}" opacity="0.75"/>')
        label = b.label[:28]
        lines.append(f'<text x="{pad_l - 6}" y="{y + bar_h - 3}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{label}</text>')
        pct_str = f"{b.pct_of_reported * 100:.1f}%"
        lines.append(f'<text x="{_x(running + b.amount_mm) + 4:.1f}" y="{y + bar_h - 3}" '
                     f'fill="{color}">{pct_str}</text>')
        running += b.amount_mm

    # Adjusted EBITDA bar
    y_adj = pad_t + (len(breakdowns) + 1) * row_h + 4
    bx = _x(0)
    bw = _x(adjusted) - bx
    lines.append(f'<rect x="{bx:.1f}" y="{y_adj}" width="{bw:.1f}" height="{bar_h}" '
                 f'fill="{P["positive"]}" opacity="0.9"/>')
    lines.append(f'<text x="{pad_l - 6}" y="{y_adj + bar_h - 3}" text-anchor="end" '
                 f'fill="{P["text"]}" font-weight="600">Adjusted EBITDA</text>')
    lines.append(f'<text x="{_x(adjusted) + 4:.1f}" y="{y_adj + bar_h - 3}" '
                 f'fill="{P["positive"]}" font-weight="600">${adjusted:.1f}M</text>')

    lines.append('</svg>')
    return "\n".join(lines)


def _moic_quality_svg(moic_by_quality: Dict[str, float]) -> str:
    tiers = ["Investment Grade", "Acceptable", "Elevated", "Aggressive"]
    colors = {
        "Investment Grade": P["positive"],
        "Acceptable": P["accent"],
        "Elevated": P["warning"],
        "Aggressive": P["negative"],
    }
    W, H = 400, 140
    pad_l, pad_r, pad_t, pad_b = 130, 60, 20, 30
    chart_w = W - pad_l - pad_r

    max_moic = max((v for v in moic_by_quality.values() if v > 0), default=4.0) * 1.1
    bar_h = 18
    row_h = 26

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;background:{P["panel"]};border:1px solid {P["border"]}">',
    ]
    for i, tier in enumerate(tiers):
        moic = moic_by_quality.get(tier, 0.0)
        if moic <= 0:
            continue
        y = pad_t + i * row_h
        bw = (moic / max_moic) * chart_w
        c = colors[tier]
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
                     f'fill="{c}" opacity="0.8"/>')
        lines.append(f'<text x="{pad_l - 6}" y="{y + bar_h - 4}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{tier}</text>')
        lines.append(f'<text x="{pad_l + bw + 4:.1f}" y="{y + bar_h - 4}" '
                     f'fill="{c}">{moic:.2f}x</text>')
    lines.append('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _breakdown_table(breakdowns) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, b in enumerate(breakdowns):
        rbg = bg2 if i % 2 else bg
        flag_c = P["positive"] if b.quality_flag == "Defensible" else \
                 P["warning"] if b.quality_flag == "Scrutinize" else P["negative"]
        corpus_pct = f"{b.corpus_p50 * 100:.1f}%"
        our_pct = f"{b.pct_of_reported * 100:.1f}%"
        our_mm = f"${b.amount_mm:.2f}M"
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{b.label}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{our_mm}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{our_pct}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{corpus_pct}</td>'
            f'<td style="padding:5px 8px;text-align:center"><span style="color:{flag_c};font-size:11px">{b.quality_flag}</span></td>'
            f'</tr>'
        )

    hdr_style = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Category</th>'
        f'<th {hdr_style}>Amount</th>'
        f'<th {hdr_style}>% Reported</th>'
        f'<th {hdr_style}>Corpus P50</th>'
        f'<th {hdr_style}>Flag</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _peers_table(peers: list, title: str) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, p in enumerate(peers):
        rbg = bg2 if i % 2 else bg
        add_pct = f"{p['addback_pct'] * 100:.1f}%"
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{p["company"]}</td>'
            f'<td style="padding:5px 8px;color:{tdim}">{p["sector"]}</td>'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">{p["year"]}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${p["ev_mm"]:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{p["moic"]:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{add_pct}</td>'
            f'</tr>'
        )

    hdr_style = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};'
        f'padding:6px 0 4px;text-transform:uppercase;letter-spacing:0.08em">{title}</div>'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Company</th>'
        f'<th {hdr_l}>Sector</th>'
        f'<th style="padding:5px 8px;text-align:center;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}">Year</th>'
        f'<th {hdr_style}>EV</th>'
        f'<th {hdr_style}>MOIC</th>'
        f'<th {hdr_style}>Add-Back%</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _input_form(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    ebitda = params.get("ebitda", "25.0")
    ev = params.get("ev", "250.0")

    options = "".join(
        f'<option value="{s}" {"selected" if s == sector else ""}>{s}</option>'
        for s in _SECTORS
    )

    inp_style = (
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};padding:6px 8px;'
        f'font-family:\'JetBrains Mono\',monospace;font-size:12px;'
        f'border-radius:2px;width:100%;box-sizing:border-box'
    )
    lbl_style = (
        f'display:block;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{P["text_dim"]};'
        f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px'
    )
    btn_style = (
        f'background:{P["accent"]};color:{P["text"]};'
        f'border:none;padding:8px 20px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:12px;cursor:pointer;border-radius:2px'
    )

    return f'''
<form method="get" action="/qoe-analyzer" style="
    background:{P["panel"]};border:1px solid {P["border"]};
    padding:14px 16px;display:grid;grid-template-columns:2fr 1fr 1fr auto;
    gap:12px;align-items:end">
  <div>
    <label style="{lbl_style}">Sector</label>
    <select name="sector" style="{inp_style}"><optgroup label="Sectors">{options}</optgroup></select>
  </div>
  <div>
    <label style="{lbl_style}">Reported EBITDA ($M)</label>
    <input name="ebitda" type="number" step="0.1" value="{ebitda}" style="{inp_style}">
  </div>
  <div>
    <label style="{lbl_style}">Enterprise Value ($M)</label>
    <input name="ev" type="number" step="1" value="{ev}" style="{inp_style}">
  </div>
  <div>
    <button type="submit" style="{btn_style}">Analyze</button>
  </div>
</form>'''


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_qoe_analyzer(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    try:
        ebitda_mm = float(params.get("ebitda", "25.0"))
    except (ValueError, TypeError):
        ebitda_mm = 25.0
    try:
        ev_mm = float(params.get("ev", "250.0"))
    except (ValueError, TypeError):
        ev_mm = 250.0

    from rcm_mc.data_public.qoe_analyzer import compute_qoe_analyzer
    r = compute_qoe_analyzer(sector, ebitda_mm, ev_mm)

    # KPI bar
    ev_ebitda_adj = round(ev_mm / r.adjusted_ebitda_mm, 1) if r.adjusted_ebitda_mm else 0.0
    kpis = ck_kpi_block("Reported EBITDA", f"${r.reported_ebitda_mm:.1f}M")
    kpis += ck_kpi_block("Total Add-Backs", f"${r.total_addback_mm:.1f}M",
                         unit=f"{r.addback_pct_of_reported * 100:.1f}% of reported")
    kpis += ck_kpi_block("Adjusted EBITDA", f"${r.adjusted_ebitda_mm:.1f}M")
    kpis += ck_kpi_block("Adj. EV/EBITDA", f"{ev_ebitda_adj:.1f}x",
                         unit=f"Reported: {ev_mm/ebitda_mm:.1f}x")
    kpis += ck_kpi_block("Quality Tier",
                         f'<span style="color:{r.quality_color}">{r.quality_tier}</span>',
                         unit=f"{r.corpus_deal_count} corpus deals")
    kpis += ck_kpi_block("Peer Add-Back P50",
                         f"{r.benchmark.median_total_addback_pct * 100:.1f}%",
                         unit=(f"P25: {r.benchmark.p25_total_addback_pct * 100:.1f}% / "
                               f"P75: {r.benchmark.p75_total_addback_pct * 100:.1f}%"))

    waterfall = _waterfall_svg(r.breakdowns, r.reported_ebitda_mm, r.adjusted_ebitda_mm)
    moic_chart = _moic_quality_svg(r.moic_by_quality)
    breakdown_tbl = _breakdown_table(r.breakdowns)
    peers_low_tbl = _peers_table(r.peers_low_addback, "Low Add-Back Peers (High Quality)")
    peers_high_tbl = _peers_table(r.peers_high_addback, "High Add-Back Peers (Lower Quality)")

    bg_sec = P["panel"]
    border = P["border"]
    tprim = P["text"]
    tdim = P["text_dim"]
    accent = P["accent"]

    moic_premium_str = f"+{r.benchmark.moic_premium_low_addback:.2f}x" if r.benchmark.moic_premium_low_addback >= 0 \
        else f"{r.benchmark.moic_premium_low_addback:.2f}x"

    content = f'''
{_input_form(params)}

<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:12px">
{kpis}
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    EBITDA Bridge — Reported to Adjusted
  </div>
  {waterfall}
</div>

<div style="display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Add-Back Detail
    </div>
    {breakdown_tbl}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Realized MOIC by Quality Tier
    </div>
    {moic_chart}
    <div style="margin-top:10px;padding:8px;background:{P["panel_alt"]};border:1px solid {border}">
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim}">
        MOIC Premium (Low vs High Add-Back)
      </div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:18px;color:{P["positive"]};
        font-variant-numeric:tabular-nums;margin-top:4px">
        {moic_premium_str}
      </div>
      <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};margin-top:4px">
        Corpus peers — {r.benchmark.n_peers} deals in sector
      </div>
    </div>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    {peers_low_tbl}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    {peers_high_tbl}
  </div>
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Benchmark Summary — {sector}
  </div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
    <div style="padding:8px;background:{P["panel_alt"]};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">Peer Deals</div>
      <div style="font-size:16px;color:{tprim};font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace">{r.benchmark.n_peers}</div>
    </div>
    <div style="padding:8px;background:{P["panel_alt"]};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">Add-Back P25/P50/P75</div>
      <div style="font-size:13px;color:{tprim};font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace">
        {r.benchmark.p25_total_addback_pct*100:.1f}% /
        {r.benchmark.median_total_addback_pct*100:.1f}% /
        {r.benchmark.p75_total_addback_pct*100:.1f}%
      </div>
    </div>
    <div style="padding:8px;background:{P["panel_alt"]};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">Median Adj. EBITDA Margin</div>
      <div style="font-size:16px;color:{tprim};font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace">
        {r.benchmark.median_adj_ebitda_margin*100:.1f}%
      </div>
    </div>
    <div style="padding:8px;background:{P["panel_alt"]};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">Quality Tier</div>
      <div style="font-size:16px;font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace;color:{r.quality_color}">{r.quality_tier}</div>
    </div>
  </div>
</div>
'''

    explainer = render_page_explainer(
        what=(
            "Quality-of-Earnings analyzer — walks a target's reported "
            "EBITDA into adjusted EBITDA via add-back / normalization "
            "entries, scores each adjustment's credibility, and "
            "produces a QoE-grade and a cash-EBITDA vs reported-EBITDA "
            "bridge."
        ),
        source="data_public/qoe_analyzer.py (QoE adjustment engine).",
        page_key="qoe-analyzer",
    )
    return chartis_shell(
        body=explainer + content,
        title=f"Quality of Earnings — {sector}",
        active_nav="/qoe-analyzer",
    )
