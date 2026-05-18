"""Direct-to-Employer Contract Analyzer — /direct-employer."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title


def _contracts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Employer","left"),("Industry","left"),("Covered Lives","right"),("Contract Type","left"),
            ("Revenue ($M)","right"),("Utilization","right"),("PMPY","right"),("Renewal","right"),("Churn Risk","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    risk_c = {"low": pos, "medium": warn, "high": neg}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(c.churn_risk, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.employer)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.industry)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.covered_lives:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{_html.escape(c.contract_type)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.annual_revenue_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{c.utilization_rate * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.pmpy_rev:,.0f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{c.renewal_year}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.churn_risk)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _coe_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Procedure","left"),("Bundled Price ($k)","right"),("FFS Benchmark ($k)","right"),
            ("Gross Margin","right"),("Annual Volume","right"),("Revenue ($M)","right"),("Travel ($k)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if c.gross_margin_pct >= 0.40 else (acc if c.gross_margin_pct >= 0.32 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.procedure)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${c.bundled_price_k:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.ffs_benchmark_k:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{c.gross_margin_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{c.case_volume_annual:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.annual_revenue_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""${c.travel_reimbursement_k:,.2f}""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _onsite_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Location","left"),("Employer","left"),("Employee Lives","right"),("Annual Visits","right"),
            ("Annual Fee ($M)","right"),("Capacity Util","right"),("NPS","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cap_c = pos if o.capacity_utilization_pct >= 0.80 else (acc if o.capacity_utilization_pct >= 0.65 else warn)
        nps_c = pos if o.nps_score >= 75 else (acc if o.nps_score >= 65 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(o.location)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(o.employer)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{o.employee_lives:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{o.annual_visits:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${o.annual_fee_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cap_c};font-weight:600">{o.capacity_utilization_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{nps_c};font-weight:700">{o.nps_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _erisa_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    cols = [("Topic","left"),("Description","left"),("Exposure ($M)","right"),("Mitigation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.topic)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if e.exposure_mm > 0 else text_dim}">${e.exposure_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["accent"]}">{_html.escape(e.mitigation)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pipeline_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Market","left"),("Employer Count","right"),("Employee Lives","right"),
            ("RFP Pipeline ($M)","right"),("Win Probability","right"),("Expected Rev ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        wp_c = pos if p.win_probability_pct >= 0.40 else (acc if p.win_probability_pct >= 0.30 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.market)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{p.employer_count}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.employee_lives:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.rfp_pipeline_mm:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{wp_c};font-weight:700">{p.win_probability_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${p.expected_revenue_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_direct_employer(params: dict = None) -> str:
    params = params or {}

    from rcm_mc.data_public.direct_employer import compute_direct_employer
    r = compute_direct_employer()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Employers", str(r.total_employers), "", "") +
        ck_kpi_block("Covered Lives", f"{r.total_lives:,}", "", "") +
        ck_kpi_block("Annual Revenue", f"${r.total_annual_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Blended PMPY", f"${r.blended_pmpy:,.0f}", "", "") +
        ck_kpi_block("COE Margin", f"{r.coe_margin_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Onsite Capacity", f"{r.onsite_capacity_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Pipeline Markets", str(len(r.pipeline)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    c_tbl = _contracts_table(r.contracts)
    coe_tbl = _coe_table(r.coes)
    os_tbl = _onsite_table(r.onsites)
    er_tbl = _erisa_table(r.erisa)
    pp_tbl = _pipeline_table(r.pipeline)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    pipeline_value = sum(p.expected_revenue_mm for p in r.pipeline)
    page_title = ck_page_title(
        "Direct-to-Employer Contract Analyzer",
        eyebrow="DIRECT EMPLOYER",
        meta=f"{r.total_employers} employer contracts covering {r.total_lives:,} lives · ${r.total_annual_revenue_mm:,.0f}M annual revenue at ${r.blended_pmpy:,.0f} PMPY · {r.coe_margin_pct * 100:.1f}% COE margin · ${pipeline_value:,.1f}M expected pipeline revenue across {len(r.pipeline)} markets",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Employer Contract Portfolio</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Centers of Excellence (COE) — Bundled Procedures</div>{coe_tbl}</div>
  <div style="{cell}"><div style="{h3}">On-Site Clinic Operations</div>{os_tbl}</div>
  <div style="{cell}"><div style="{h3}">ERISA Structural Considerations</div>{er_tbl}</div>
  <div style="{cell}"><div style="{h3}">RFP Pipeline — Direct-Primary-Care Market Expansion</div>{pp_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Direct-Employer Thesis:</strong> {r.total_employers} employer contracts covering {r.total_lives:,} lives produce ${r.total_annual_revenue_mm:,.0f}M annual revenue at ${r.blended_pmpy:,.0f} PMPY.
    COE bundled pricing delivers {r.coe_margin_pct * 100:.1f}% gross margin vs fee-for-service benchmark — a premium the employer captures as overall plan cost savings.
    Onsite clinic capacity averages {r.onsite_capacity_pct * 100:.1f}% utilization; additional ${pipeline_value:,.1f}M in expected revenue from active RFP pipeline.
    Direct-to-employer is a durable revenue stream (3-5 year contracts, low churn for high-performing providers) with ERISA preemption protecting against state-mandated network rules.
    Stop-loss pre-clearance and fiduciary indemnification are standard but require early diligence.
  </div>
</div>"""

    return chartis_shell(body, "Direct Employer", active_nav="/direct-employer",
        editorial_intro={
            "eyebrow": "DIRECT EMPLOYER",
            "headline": "What the direct employer page reveals on this deal.",
            "italic_word": "reveals",
        })
