"""De Novo Expansion Tracker — /denovo-expansion."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _sites_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Site Type","left"),("Capex ($M)","right"),("Working Cap ($M)","right"),("Total Inv ($M)","right"),
            ("Stab EBITDA ($M)","right"),("Ramp (mo)","right"),("Payback (yr)","right"),("Y1 Rev ($M)","right"),("Y3 Rev ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pb_c = pos if s.payback_years <= 2.7 else (acc if s.payback_years <= 3.2 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.site_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.buildout_capex_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.working_cap_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]};font-weight:600">${s.total_investment_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.stabilized_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.ramp_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pb_c};font-weight:700">{s.payback_years:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${s.y1_revenue_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${s.y3_revenue_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _markets_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Market","left"),("Region","center"),("Population (000)","right"),("Competitors","right"),
            ("Demand Score","right"),("Target Sites","right"),("Investment ($M)","right"),("Expected EBITDA ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if m.demand_score >= 85 else (acc if m.demand_score >= 78 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.market)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.region)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.population_000:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.competitor_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{m.demand_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{m.target_sites}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${m.total_investment_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${m.expected_ebitda_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _ramp_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Month","right"),("Visits/Day","right"),("Revenue ($M)","right"),("Expense ($M)","right"),
            ("EBITDA ($M)","right"),("Cumulative FCF ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = pos if r.ebitda_mm > 0 else (neg if r.ebitda_mm < -0.05 else text_dim)
        fcf_c = pos if r.cumulative_fcf_mm > 0 else (neg if r.cumulative_fcf_mm < -5 else text_dim)
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{r.month}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{r.visits_per_day}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.revenue_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${r.expense_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">${r.ebitda_mm:+,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{fcf_c};font-weight:700">${r.cumulative_fcf_mm:+,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lease_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Scenario","left"),("Upfront ($M)","right"),("Annual Cost ($M)","right"),("Tenure (yr)","right"),
            ("NPV 10yr ($M)","right"),("Flexibility","right"),("Exit Value ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, lb in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        npv_c = pos if lb.npv_10yr_mm > 0 else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(lb.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${lb.upfront_cash_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${lb.annual_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{lb.tenure_years}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{npv_c};font-weight:700">${lb.npv_10yr_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{lb.flexibility_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${lb.ownership_exit_value_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _blend_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Category","left"),("Deals","right"),("Investment ($M)","right"),("EBITDA Added ($M)","right"),
            ("Avg Multiple","right"),("Payback (yr)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if b.avg_multiple <= 3.5 else (acc if b.avg_multiple <= 7.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{b.deals_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${b.total_investment_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${b.ebitda_added_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{b.avg_multiple:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{b.payback_years:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _ramp_svg(ramp) -> str:
    if not ramp: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    max_v = max(r.cumulative_fcf_mm for r in ramp)
    min_v = min(r.cumulative_fcf_mm for r in ramp)
    span = max_v - min_v
    x_step = inner_w / max(len(ramp) - 1, 1)
    zero_y = (h - pad_b) - ((0 - min_v) / span) * inner_h
    pts = []
    for i, r in enumerate(ramp):
        x = pad_l + i * x_step
        y_norm = (r.cumulative_fcf_mm - min_v) / span
        y = (h - pad_b) - y_norm * inner_h
        pts.append(f"{x:.1f},{y:.1f}")
    path = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'
    zero_line = f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{pad_l + inner_w}" y2="{zero_y:.1f}" stroke="{text_dim}" stroke-width="0.5" stroke-dasharray="3,3"/>'
    break_even = next((r.month for r in ramp if r.cumulative_fcf_mm >= 0), None)
    be_txt = f'<text x="{pad_l + inner_w - 5}" y="{zero_y - 4}" fill="{pos}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace;font-weight:700">break-even month {break_even or ">24"}</text>'
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{zero_line}{be_txt}{path}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">De Novo ASC Ramp — Cumulative FCF (24-month window)</text></svg>')


def render_denovo_expansion(params: dict = None) -> str:
    from rcm_mc.data_public.denovo_expansion import compute_denovo_expansion
    r = compute_denovo_expansion()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Active Sites", str(r.total_active_sites), "", "") +
        ck_kpi_block("Planned Sites", str(r.total_sites_planned), "", "") +
        ck_kpi_block("Investment", f"${r.total_investment_committed_mm:,.0f}M", "", "") +
        ck_kpi_block("Stab EBITDA Target", f"${r.expected_stabilized_ebitda_mm:,.0f}M", "", "") +
        ck_kpi_block("Portfolio Payback", f"{r.portfolio_payback_years:.2f}y", "", "") +
        ck_kpi_block("Site Types", str(len(r.site_types)), "", "") +
        ck_kpi_block("Markets in Plan", str(len(r.markets)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _ramp_svg(r.ramp)
    st_tbl = _sites_table(r.site_types)
    mk_tbl = _markets_table(r.markets)
    rp_tbl = _ramp_table(r.ramp)
    lb_tbl = _lease_table(r.lease_buy)
    bl_tbl = _blend_table(r.blend)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">De Novo Expansion Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Greenfield buildout economics · site-type unit economics · market expansion queue · ramp curves · lease vs buy · organic/inorganic blend — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">De Novo ASC Ramp Curve</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Site-Type Unit Economics</div>{st_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Expansion Queue</div>{mk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Month-by-Month Ramp — Representative ASC</div>{rp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Lease vs Buy Decision Matrix (10-Year NPV)</div>{lb_tbl}</div>
  <div style="{cell}"><div style="{h3}">Organic vs Inorganic Growth Blend</div>{bl_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">De Novo Thesis:</strong> {r.total_sites_planned} sites planned across {len(r.markets)} markets requires ${r.total_investment_committed_mm:,.0f}M investment for ${r.expected_stabilized_ebitda_mm:,.0f}M stabilized EBITDA —
    portfolio payback {r.portfolio_payback_years:.2f} years. De novo is a lower-multiple alternative to bolt-on M&A (2.5-3.0x vs 8-10x) but has longer ramp.
    Sun Belt markets (Austin, Phoenix, Nashville, Raleigh) show strongest demand scores and lowest competitor density. ASC de novo is the highest-margin site type at 4.2x payback at scale.
    Lease-to-own structures are most attractive for de novos — preserves capital during ramp and enables sale-leaseback at stabilization.
  </div>
</div>"""

    return chartis_shell(body, "De Novo Expansion", active_nav="/denovo-expansion")
