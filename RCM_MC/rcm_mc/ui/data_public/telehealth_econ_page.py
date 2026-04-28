"""Telehealth Economics Analyzer — /telehealth-econ."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell


def _visits_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Visit Type","left"),("Reimbursement","right"),("Direct Cost","right"),("Gross Margin","right"),
            ("GM %","right"),("Duration (min)","right"),("Annual Volume","right"),("Annual Revenue ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gm_c = pos if v.gross_margin_pct >= 0.65 else (acc if v.gross_margin_pct >= 0.55 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.visit_type)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${v.avg_reimbursement:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${v.direct_cost:,.2f}</td>',
            f'{ck_data_cell(f"""${v.gross_margin:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gm_c};font-weight:700">{v.gross_margin_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{v.avg_duration_min}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{v.annual_volume:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${v.annual_revenue_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _prod_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Specialty","left"),("FTE","right"),("Visits/Provider/Day","right"),("Utilization","right"),
            ("Avg Rev/Provider ($k)","right"),("Attrition","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        att_c = pos if p.attrition_rate_pct < 0.15 else (acc if p.attrition_rate_pct < 0.20 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.specialty)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{p.providers_fte:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.visits_per_provider_day}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{p.utilization_pct * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${p.avg_rev_per_provider_k:,.0f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{att_c};font-weight:600">{p.attrition_rate_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _parity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("State","left"),("Parity","left"),("Medicaid","left"),("Medicare","left"),("Commercial","left"),("Sunset Risk","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    risk_c = {"low": pos, "medium": warn, "high": neg}
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(p.sunset_risk, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.state)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(p.parity_status)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(p.medicaid_coverage)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(p.medicare_extension)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(p.commercial_parity)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.sunset_risk)}</span>""", align="center")}',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tech_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    cols = [("Component","left"),("Annual Cost ($M)","right"),("% of Revenue","right"),("Vendor","left"),("Renewal","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.component)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${t.annual_cost_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{t.pct_of_revenue * 100:.2f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{_html.escape(t.vendor)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.renewal_status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cliffs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    cols = [("Policy","left"),("Status","left"),("Expiration","left"),("Revenue at Risk ($M)","right"),("Mitigation","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.policy)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.current_status)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(c.expiration_date)}""", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if c.revenue_at_risk_mm > 0 else text_dim};font-weight:700">${c.revenue_at_risk_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.mitigation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comp_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Company","left"),("Visit Type","left"),("Price/Visit","right"),("Subscription/mo","right"),("Status","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.company)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.visit_type)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.price_per_visit:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.subscription_monthly:,.2f}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_telehealth_econ(params: dict = None) -> str:
    from rcm_mc.data_public.telehealth_econ import compute_telehealth_econ
    r = compute_telehealth_econ()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Annual Visits", f"{r.total_visits_annual:,}", "", "") +
        ck_kpi_block("Annual Revenue", f"${r.annual_revenue_mm:,.1f}M", "", "") +
        ck_kpi_block("Blended GM", f"{r.blended_gross_margin_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Provider FTE", f"{r.total_provider_fte:,.0f}", "", "") +
        ck_kpi_block("States Operating", str(r.states_operating), "", "") +
        ck_kpi_block("Visit Types", str(len(r.visits)), "", "") +
        ck_kpi_block("Reg Cliffs", str(sum(1 for c in r.cliffs if c.revenue_at_risk_mm > 0)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    v_tbl = _visits_table(r.visits)
    p_tbl = _prod_table(r.productivity)
    pa_tbl = _parity_table(r.parity)
    t_tbl = _tech_table(r.tech_stack)
    c_tbl = _cliffs_table(r.cliffs)
    co_tbl = _comp_table(r.competitors)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_cliff_risk = sum(c.revenue_at_risk_mm for c in r.cliffs)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Telehealth Economics Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Visit-level P&amp;L · provider productivity · state parity · tech stack · PHE cliff exposure · DTC comparables — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Visit-Type Economics (P&amp;L by Visit Category)</div>{v_tbl}</div>
  <div style="{cell}"><div style="{h3}">Provider Productivity by Specialty</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">State-Level Payer Parity Status</div>{pa_tbl}</div>
  <div style="{cell}"><div style="{h3}">Technology Stack Cost Structure</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Regulatory Cliff Exposure (PHE / Ryan Haight / Home Originating)</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Comparable DTC / Telehealth Platforms</div>{co_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Telehealth Thesis:</strong> {r.total_visits_annual:,} annual visits produce ${r.annual_revenue_mm:,.1f}M at {r.blended_gross_margin_pct * 100:.1f}% gross margin.
    Behavioral health and specialty consult are highest-margin visit types; async primary care has highest volume.
    {r.total_provider_fte:,.0f} provider FTE across {r.states_operating} states with IMLC coverage. Cumulative regulatory cliff exposure ${total_cliff_risk:,.1f}M
    concentrated in PHE-era Medicare flexibilities and DEA Ryan Haight telecontrolled-substance prescribing. Mitigation via bipartisan TCEA legislative push
    and in-person touchpoint model for DEA compliance. Behavioral-health telehealth parity is now permanent — the safest revenue stream post-PHE.
  </div>
</div>"""

    return chartis_shell(body, "Telehealth Econ", active_nav="/telehealth-econ",
        editorial_intro={
            "eyebrow": "TELEHEALTH ECON",
            "headline": "What the telehealth econ page reveals on this deal.",
            "italic_word": "reveals",
        })
