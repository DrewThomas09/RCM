"""Workforce Planning Analyzer page — /workforce-planning.

Role inventory, hiring plan, labor initiatives, agency reduction.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _role_spend_svg(inventory) -> str:
    if not inventory:
        return ""
    sorted_inv = sorted(inventory, key=lambda r: -r.annual_spend_mm)
    w = 540
    row_h = 22
    h = len(sorted_inv) * row_h + 30
    pad_l = 180
    pad_r = 60

    inner_w = w - pad_l - pad_r
    max_v = max(r.annual_spend_mm for r in sorted_inv) or 1

    bg = P["panel"]; acc = P["accent"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]

    bars = []
    for i, r in enumerate(sorted_inv):
        y = 20 + i * row_h
        bh = 14
        bw = r.annual_spend_mm / max_v * inner_w
        turnover_c = P["positive"] if r.turnover_rate < 0.15 else (P["warning"] if r.turnover_rate < 0.25 else P["negative"])
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(r.role[:26])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{acc}" opacity="0.75"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">${r.annual_spend_mm:,.2f}M</text>'
            f'<text x="{w - 4}" y="{y + bh - 1}" fill="{turnover_c}" font-size="9" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{r.turnover_rate * 100:.0f}% T/O</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Annual Labor Spend by Role</text>'
        f'</svg>'
    )


def _initiatives_svg(initiatives) -> str:
    if not initiatives:
        return ""
    w = 540
    row_h = 26
    h = len(initiatives) * row_h + 30
    pad_l = 240
    pad_r = 80

    inner_w = w - pad_l - pad_r
    max_v = max(i.annual_savings_mm for i in initiatives) or 1

    bg = P["panel"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}

    bars = []
    for i, init in enumerate(initiatives):
        y = 20 + i * row_h
        bh = 14
        bw = init.annual_savings_mm / max_v * inner_w
        rc = risk_colors.get(init.risk, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(init.initiative[:34])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{pos}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">${init.annual_savings_mm:,.2f}M</text>'
            f'<text x="{w - 4}" y="{y + bh - 1}" fill="{rc}" font-size="9" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{init.risk}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Annual Savings by Initiative</text>'
        f'</svg>'
    )


def _inventory_table(inventory) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Role","left"),("Current FTE","right"),("Target FTE","right"),("Open","right"),
            ("Agency FTE","right"),("Base Comp ($K)","right"),("All-in ($K)","right"),
            ("Annual Spend ($M)","right"),("Turnover %","right"),("Turnover Cost ($M)","right"),("Infl %","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, inv in enumerate(inventory):
        rb = panel_alt if i % 2 == 0 else bg
        to_c = P["positive"] if inv.turnover_rate < 0.15 else (P["warning"] if inv.turnover_rate < 0.25 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(inv.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{inv.current_fte:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{inv.target_fte:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{inv.open_positions}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if inv.agency_fte else text_dim}">{inv.agency_fte}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${inv.base_comp_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${inv.all_in_comp_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${inv.annual_spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{to_c}">{inv.turnover_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${inv.turnover_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{inv.comp_inflation_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _hiring_table(plan) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Quarter","left"),("Role","left"),("Hires Planned","right"),("Hires to Date","right"),
            ("Cost/Hire ($K)","right"),("Quarter Cost ($M)","right"),("Productivity Lag ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(plan[:25]):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.quarter)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.hires_planned}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{p.hires_to_date}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.cost_per_hire_k:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${p.total_quarter_cost_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${p.productivity_delay_cost_mm:,.3f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _initiatives_table(initiatives) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    risk_colors = {"low": pos, "medium": P["warning"], "high": P["negative"]}
    cols = [("Initiative","left"),("Scope","left"),("Annual Savings ($M)","right"),
            ("One-Time Cost ($M)","right"),("Timeline (mo)","right"),("Risk","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, init in enumerate(initiatives):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(init.risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(init.initiative)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(init.scope_roles)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${init.annual_savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${init.one_time_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{init.timeline_months}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{init.risk}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _agency_table(agency) -> str:
    if not agency:
        return f'<p style="color:{P["text_dim"]};font-size:11px;padding:12px 0">No agency labor in scope.</p>'
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Role","left"),("Current Agency FTE","right"),("Target","right"),
            ("Premium","right"),("Current Cost ($M)","right"),("Target Cost ($M)","right"),("Savings ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, a in enumerate(agency):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(a.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.current_agency_fte}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.target_agency_fte}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">{a.premium_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${a.current_agency_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${a.target_agency_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${a.savings_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_workforce_planning(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    fte = _i("fte", 280)
    revenue = _f("revenue", 80.0)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.workforce_planning import compute_workforce_planning
    r = compute_workforce_planning(sector=sector, total_fte=fte, revenue_mm=revenue, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total FTE", f"{r.total_fte:,}", "", "") +
        ck_kpi_block("Open Positions", str(r.open_positions), "", "") +
        ck_kpi_block("Agency FTE", str(r.agency_fte), "", "") +
        ck_kpi_block("Labor Cost", f"${r.total_labor_cost_mm:,.1f}M", "", "") +
        ck_kpi_block("Labor % Rev", f"{r.labor_pct_of_revenue * 100:.1f}%", "", "") +
        ck_kpi_block("Blended Turnover", f"{r.blended_turnover_rate * 100:.1f}%", "", "") +
        ck_kpi_block("Turnover Cost", f"${r.total_annual_turnover_cost_mm:,.1f}M", "", "") +
        ck_kpi_block("Initiative EV Impact", f"${r.ev_impact_from_labor_mm:,.0f}M", "", "")
    )

    spend_svg = _role_spend_svg(r.role_inventory)
    init_svg = _initiatives_svg(r.initiatives)
    inv_tbl = _inventory_table(r.role_inventory)
    hire_tbl = _hiring_table(r.hiring_plan)
    init_tbl = _initiatives_table(r.initiatives)
    agency_tbl = _agency_table(r.agency_reductions)

    form = f"""
<form method="GET" action="/workforce-planning" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Total FTE
    <input name="fte" value="{fte}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
    <input name="mult" value="{mult}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Workforce Planning Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Role inventory, hiring plan, turnover, agency reduction, labor initiatives — {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Labor Spend by Role</div>
      {spend_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Savings by Initiative</div>
      {init_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Role Inventory &amp; Comp Benchmarks</div>
    {inv_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Hiring Plan (2026)</div>
    {hire_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Labor Initiative Portfolio</div>
    {init_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Agency / Contract Labor Reduction</div>
    {agency_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Workforce Thesis:</strong>
    {r.total_fte:,} FTEs, labor is {r.labor_pct_of_revenue * 100:.1f}% of revenue. Blended turnover
    {r.blended_turnover_rate * 100:.1f}% costs ${r.total_annual_turnover_cost_mm:,.1f}M/yr. Total initiative
    savings ${r.total_initiative_savings_mm:,.1f}M annually → ${r.ev_impact_from_labor_mm:,.0f}M EV uplift.
    Agency elimination and retention program are highest-ROI near-term moves.
  </div>

</div>"""

    return chartis_shell(body, "Workforce Planning", active_nav="/workforce-planning")
