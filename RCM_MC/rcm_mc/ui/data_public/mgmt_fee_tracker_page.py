"""Management Fee Tracker page — /mgmt-fee-tracker."""
from __future__ import annotations

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _fee_waterfall_svg(fee_calcs) -> str:
    W, H = 600, 30 + len(fee_calcs) * 26 + 30
    pad_l, pad_r, pad_t = 160, 80, 20

    max_fee = max(f.total_annual_fees_mm for f in fee_calcs) * 1.2 or 1.0
    chart_w = W - pad_l - pad_r
    bar_h = 14

    lines = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    for i, f in enumerate(fee_calcs):
        y = pad_t + i * 22
        # Gross fee bar
        gross_w = (f.total_annual_fees_mm / max_fee) * chart_w
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{gross_w:.1f}" height="{bar_h}" '
                     f'fill="{P["warning"]}" opacity="0.6"/>')
        # Offset (reduction)
        offset_w = (f.lp_offset_mm / max_fee) * chart_w
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{offset_w:.1f}" height="{bar_h}" '
                     f'fill="{P["positive"]}" opacity="0.5"/>')

        co = f.company[:22]
        lines.append(f'<text x="{pad_l - 6}" y="{y + bar_h - 2}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{co}</text>')
        net_str = f"${f.net_fee_to_lp_mm:.3f}M net"
        lines.append(f'<text x="{pad_l + gross_w + 4:.1f}" y="{y + bar_h - 2}" '
                     f'fill="{P["warning"]}">{net_str}</text>')

    lines.append('</svg>')
    return "\n".join(lines)


def _carry_svg(carry_calcs) -> str:
    W = 500
    bar_h = 14
    row_h = 22
    pad_l, pad_r, pad_t = 160, 80, 20
    chart_w = W - pad_l - pad_r
    total_h = pad_t + len(carry_calcs) * row_h + 20

    max_distr = max(c.distributions_mm for c in carry_calcs) * 1.1 or 1.0

    lines = [
        f'<svg viewBox="0 0 {W} {total_h}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    for i, c in enumerate(carry_calcs):
        y = pad_t + i * row_h
        # LP net bar
        lp_w = (c.lp_net_proceeds_mm / max_distr) * chart_w
        carry_w = (c.carry_amount_mm / max_distr) * chart_w
        lines.append(f'<rect x="{pad_l}" y="{y}" width="{lp_w:.1f}" height="{bar_h}" '
                     f'fill="{P["accent"]}" opacity="0.75"/>')
        lines.append(f'<rect x="{pad_l + lp_w:.1f}" y="{y}" width="{carry_w:.1f}" height="{bar_h}" '
                     f'fill="{P["warning"]}" opacity="0.7"/>')
        lines.append(f'<text x="{pad_l - 6}" y="{y + bar_h - 2}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{c.company[:22]}</text>')
        lines.append(f'<text x="{pad_l + lp_w + carry_w + 4:.1f}" y="{y + bar_h - 2}" '
                     f'fill="{P["text_dim"]}">{c.gross_moic:.2f}x gross</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _positions_table(positions) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, p in enumerate(positions):
        rbg = bg2 if i % 2 else bg
        moic_c = P["positive"] if p.moic_current >= 3.0 else (P["warning"] if p.moic_current >= 2.0 else P["negative"])
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{p.company}</td>'
            f'<td style="padding:5px 8px;color:{tdim}">{p.sector[:18]}</td>'
            f'<td style="padding:5px 8px;text-align:center;color:{tdim}">{p.entry_year}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${p.invested_equity_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">${p.current_nav_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{moic_c}">{p.moic_current:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{p.irr_current*100:.1f}%</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{p.hold_years:.1f}yr</td>'
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
        f'<th {hdr_c}>Entry Yr</th>'
        f'<th {hdr_r}>Invested</th>'
        f'<th {hdr_r}>NAV</th>'
        f'<th {hdr_r}>MOIC</th>'
        f'<th {hdr_r}>IRR</th>'
        f'<th {hdr_r}>Hold</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _carry_table(carry_calcs) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, c in enumerate(carry_calcs):
        rbg = bg2 if i % 2 else bg
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;color:{tprim}">{c.company}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">${c.invested_equity_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">${c.distributions_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">${c.preferred_return_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{P["warning"]}">${c.carry_amount_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{P["accent"]}">${c.lp_net_proceeds_mm:.0f}M</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tprim}">{c.gross_moic:.2f}x</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim}">{c.net_moic_to_lp:.2f}x</td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Company</th>'
        f'<th {hdr_r}>Invested</th>'
        f'<th {hdr_r}>Distrib.</th>'
        f'<th {hdr_r}>Pref. Return</th>'
        f'<th {hdr_r}>Carry (GP)</th>'
        f'<th {hdr_r}>LP Net</th>'
        f'<th {hdr_r}>Gross MOIC</th>'
        f'<th {hdr_r}>LP Net MOIC</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def _input_form(params: dict) -> str:
    fund = params.get("fund", "500.0")
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
    return f'''<form method="get" action="/mgmt-fee-tracker" style="
    background:{P["panel"]};border:1px solid {P["border"]};
    padding:14px 16px;display:grid;grid-template-columns:1fr auto;
    gap:12px;align-items:end;max-width:400px">
  <div><label style="{lbl}">Fund Size ($M)</label>
    <input name="fund" type="number" step="50" value="{fund}" style="{inp}"></div>
  <div><button type="submit" style="{btn}">Load Portfolio</button></div>
</form>'''


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_mgmt_fee_tracker(params: dict) -> str:
    try:
        fund_mm = float(params.get("fund", "500.0"))
    except (ValueError, TypeError):
        fund_mm = 500.0

    from rcm_mc.data_public.mgmt_fee_tracker import compute_mgmt_fee_tracker
    r = compute_mgmt_fee_tracker(fund_mm)
    fe = r.fund_economics

    kpis = ck_kpi_block("Fund Size", f"${fe.fund_size_mm:.0f}M")
    kpis += ck_kpi_block("Deployed Capital", f"${fe.invested_capital_mm:.0f}M",
                          unit=f"{fe.deployment_pct*100:.0f}% deployed")
    kpis += ck_kpi_block("Annual Mgmt. Fees", f"${fe.total_annual_fees_mm:.2f}M",
                          unit=f"Net to LP after offset")
    kpis += ck_kpi_block("Total Carry (GP)", f"${fe.total_carry_paid_mm:.0f}M",
                          unit="20% carry above 8% hurdle")
    kpis += ck_kpi_block("LP Net MOIC", f"{fe.lp_net_moic:.2f}x",
                          unit=f"Fee drag: {fe.fee_drag_on_moic:.2f}x")
    kpis += ck_kpi_block("Portfolio Positions", str(len(r.positions)))

    fee_svg = _fee_waterfall_svg(r.fee_calculations)
    carry_svg_chart = _carry_svg(r.carry_calculations)
    pos_tbl = _positions_table(r.positions)
    carry_tbl = _carry_table(r.carry_calculations)

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
      Annual Fee Burden by Position
      <span style="color:{P["positive"]};margin-left:8px">&#9632; LP Offset</span>
      <span style="color:{P["warning"]};margin-left:8px">&#9632; Gross Fee</span>
    </div>
    {fee_svg}
  </div>
  <div style="background:{bg_sec};border:1px solid {border};padding:12px">
    <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
      Carry Distribution by Position
      <span style="color:{P["accent"]};margin-left:8px">&#9632; LP Net</span>
      <span style="color:{P["warning"]};margin-left:8px">&#9632; GP Carry</span>
    </div>
    {carry_svg_chart}
  </div>
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Portfolio Positions
  </div>
  {pos_tbl}
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Carry &amp; LP Economics
  </div>
  {carry_tbl}
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Fund-Level Economics Summary
  </div>
  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px">
    <div style="padding:8px;background:{bg_tert};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">Deployment</div>
      <div style="font-size:16px;color:{tprim};font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace">{fe.deployment_pct*100:.0f}%</div>
    </div>
    <div style="padding:8px;background:{bg_tert};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">Annual Fees</div>
      <div style="font-size:16px;color:{P["warning"]};font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace">${fe.total_annual_fees_mm:.1f}M</div>
    </div>
    <div style="padding:8px;background:{bg_tert};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">GP Carry</div>
      <div style="font-size:16px;color:{P["warning"]};font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace">${fe.total_carry_paid_mm:.0f}M</div>
    </div>
    <div style="padding:8px;background:{bg_tert};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">LP Net MOIC</div>
      <div style="font-size:16px;color:{P["positive"]};font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace">{fe.lp_net_moic:.2f}x</div>
    </div>
    <div style="padding:8px;background:{bg_tert};border:1px solid {border}">
      <div style="font-size:10px;color:{tdim};font-family:\'JetBrains Mono\',monospace">Fee Drag</div>
      <div style="font-size:16px;color:{P["negative"]};font-variant-numeric:tabular-nums;
        font-family:\'JetBrains Mono\',monospace">{fe.fee_drag_on_moic:.2f}x</div>
    </div>
  </div>
</div>
'''

    return chartis_shell(
        body=content,
        title="Management Fee Tracker",
        active_nav="/mgmt-fee-tracker",
    )
