"""De Novo Expansion Tracker — /denovo-expansion."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_paired_block, ck_page_title, ck_illustrative_note, ck_value_anchor


def _sites_chart(items) -> str:
    """Lead chart for the site-economics table — site types ranked by
    capital committed so the biggest build bets surface first. Bar width
    = share of total investment; value = investment ($M); tone marks
    payback speed (<=3y green · <=5y teal · slower amber). Full site
    grid stays directly below.
    """
    total = sum(s.total_investment_mm for s in items) or 1.0
    ranked = sorted(items, key=lambda s: s.total_investment_mm, reverse=True)
    rows = []
    for s in ranked:
        tone = ("positive" if s.payback_years <= 3 else "teal"
                if s.payback_years <= 5 else "warning")
        rows.append(ck_bar_row(
            s.site_type,
            f"${s.total_investment_mm:,.1f}M",
            s.total_investment_mm / total * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of total investment · value = investment ($M) · '
        'tone = payback (green &le;3y · teal &le;5y · amber slower)</div>'
        '</div>'
    )


def _sites_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Site Type","left"),("Capex ($M)","right"),("Working Cap ($M)","right"),("Total Inv ($M)","right"),
            ("Stab EBITDA ($M)","right"),("Ramp (mo)","right"),("Payback (yr)","right"),("Y1 Rev ($M)","right"),("Y3 Rev ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pb_c = pos if s.payback_years <= 2.7 else (acc if s.payback_years <= 3.2 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.site_type)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${s.buildout_capex_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.working_cap_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]};font-weight:600">${s.total_investment_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${s.stabilized_ebitda_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{s.ramp_months}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pb_c};font-weight:700">{s.payback_years:.2f}</td>',
            f'{ck_data_cell(f"""${s.y1_revenue_mm:,.2f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${s.y3_revenue_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _markets_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Market","left"),("Region","center"),("Population (000)","right"),("Competitors","right"),
            ("Demand Score","right"),("Target Sites","right"),("Investment ($M)","right"),("Expected EBITDA ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if m.demand_score >= 85 else (acc if m.demand_score >= 78 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.market)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.region)}</td>',
            f'{ck_data_cell(f"""{m.population_000:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{m.competitor_count}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{m.demand_score}</td>',
            f'{ck_data_cell(f"""{m.target_sites}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${m.total_investment_mm:,.2f}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${m.expected_ebitda_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _ramp_paired_rows(items) -> tuple:
    headers = [
        "Month", "Visits/Day", "Revenue ($M)", "Expense ($M)",
        "EBITDA ($M)", "Cumulative FCF ($M)",
    ]
    rows: list = []
    be_idx: int | None = None
    for i, r in enumerate(items):
        rows.append([
            str(r.month),
            str(r.visits_per_day),
            f"${r.revenue_mm:,.3f}",
            f"${r.expense_mm:,.3f}",
            f"${r.ebitda_mm:+,.3f}",
            f"${r.cumulative_fcf_mm:+,.2f}",
        ])
        if be_idx is None and r.cumulative_fcf_mm >= 0:
            be_idx = i
    hot = [be_idx] if be_idx is not None else []
    return headers, rows, hot


def _lease_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Scenario","left"),("Upfront ($M)","right"),("Annual Cost ($M)","right"),("Tenure (yr)","right"),
            ("NPV 10yr ($M)","right"),("Flexibility","right"),("Exit Value ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, lb in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        npv_c = pos if lb.npv_10yr_mm > 0 else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(lb.scenario)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${lb.upfront_cash_mm:+,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${lb.annual_cost_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{lb.tenure_years}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{npv_c};font-weight:700">${lb.npv_10yr_mm:+,.2f}</td>',
            f'{ck_data_cell(f"""{lb.flexibility_score}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${lb.ownership_exit_value_mm:,.2f}""", align="right", mono=True, tone="pos")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _blend_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Category","left"),("Deals","right"),("Investment ($M)","right"),("EBITDA Added ($M)","right"),
            ("Avg Multiple","right"),("Payback (yr)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if b.avg_multiple <= 3.5 else (acc if b.avg_multiple <= 7.0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{b.deals_count}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${b.total_investment_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${b.ebitda_added_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{b.avg_multiple:,.2f}x</td>',
            f'{ck_data_cell(f"""{b.payback_years:.1f}""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    rp_headers, rp_rows, rp_hot = _ramp_paired_rows(r.ramp)
    ramp_paired = ck_paired_block(
        svg,
        data_label="De Novo ASC Ramp · 24-Month Window",
        headers=rp_headers,
        rows=rp_rows,
        data_source=f"{len(r.ramp)} months · break-even month marked",
        hot_rows=rp_hot,
    )
    st_chart = _sites_chart(r.site_types)
    st_tbl = _sites_table(r.site_types)
    value_anchor = ck_value_anchor(
        "De Novo Expansion",
        f"${r.total_investment_committed_mm:,.1f}M committed",
        delta=f"{r.total_active_sites} active / {r.total_sites_planned} planned sites · {r.portfolio_payback_years:.1f}y payback",
        opportunity=f"${r.expected_stabilized_ebitda_mm:,.1f}M stabilized EBITDA",
        tone="positive",
    )
    mk_tbl = _markets_table(r.markets)
    lb_tbl = _lease_table(r.lease_buy)
    bl_tbl = _blend_table(r.blend)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "De Novo Expansion Tracker",
        eyebrow="DENOVO EXPANSION",
        meta=f"{r.total_sites_planned} sites planned ({r.total_active_sites} active) across {len(r.markets)} markets · ${r.total_investment_committed_mm:,.0f}M investment · ${r.expected_stabilized_ebitda_mm:,.0f}M stabilized EBITDA target · {r.portfolio_payback_years:.2f}-year portfolio payback",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  {ramp_paired}
  <div style="{cell}"><div style="{h3}">Site-Type Unit Economics</div>{st_chart}{st_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Expansion Queue</div>{mk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Lease vs Buy Decision Matrix (10-Year NPV)</div>{lb_tbl}</div>
  <div style="{cell}"><div style="{h3}">Organic vs Inorganic Growth Blend</div>{bl_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">De Novo Thesis:</strong> {r.total_sites_planned} sites planned across {len(r.markets)} markets requires ${r.total_investment_committed_mm:,.0f}M investment for ${r.expected_stabilized_ebitda_mm:,.0f}M stabilized EBITDA —
    portfolio payback {r.portfolio_payback_years:.2f} years. De novo is a lower-multiple alternative to bolt-on M&A (2.5-3.0x vs 8-10x) but has longer ramp.
    Sun Belt markets (Austin, Phoenix, Nashville, Raleigh) show strongest demand scores and lowest competitor density. ASC de novo is the highest-margin site type at 4.2x payback at scale.
    Lease-to-own structures are most attractive for de novos — preserves capital during ramp and enables sale-leaseback at stabilization.
  </div>
</div>"""

    return chartis_shell(body, "De Novo Expansion", active_nav="/denovo-expansion",
        editorial_intro={
            "eyebrow": "DENOVO EXPANSION",
            "headline": "What the denovo expansion page reveals on this deal.",
            "italic_word": "reveals",
        })
