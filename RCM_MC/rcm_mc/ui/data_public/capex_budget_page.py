"""Capex Planning / Capital Budget Tracker — /capex-budget."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell


def _status_color(s: str) -> str:
    return {
        "on track": P["positive"],
        "behind": P["warning"],
        "at risk": P["negative"],
        "construction": P["accent"],
        "pre-construction": P["warning"],
        "permitting": P["warning"],
        "site selection": P["text_dim"],
    }.get(s, P["text_dim"])


def _projects_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("ID","left"),("Deal","left"),("Category","left"),("Description","left"),
            ("Budget ($M)","right"),("Spent ($M)","right"),("% Complete","right"),
            ("Finish","right"),("ROI","right"),("Payback (mo)","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(p.status)
        c_c = pos if p.percent_complete >= 0.65 else (acc if p.percent_complete >= 0.40 else text_dim)
        r_c = pos if p.roi_pct >= 0.35 else (acc if p.roi_pct >= 0.25 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.project_id)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(p.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(p.description)}</td>',
            f'{ck_data_cell(f"""${p.budget_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${p.spent_m:.1f}M""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{p.percent_complete * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{_html.escape(p.planned_finish)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{p.roi_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{p.payback_months}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _categories_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Category","left"),("Projects","right"),("Total Budget ($M)","right"),("Deployed ($M)","right"),
            ("Avg ROI","right"),("Avg Payback (mo)","right"),("Typical Lifespan (yrs)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if c.avg_roi_pct >= 0.35 else (acc if c.avg_roi_pct >= 0.25 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.category)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.projects}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${c.total_budget_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.deployed_m:.1f}M""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{c.avg_roi_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{c.avg_payback_months:.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.typical_lifespan_years}y""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _deal_budgets_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Annual Capex ($M)","right"),("Maint ($M)","right"),("Growth ($M)","right"),
            ("IT ($M)","right"),("YoY Change","right"),("Capex / Revenue","right"),("Capex / EBITDA","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        g_c = pos if d.yoy_change_pct >= 0.15 else (acc if d.yoy_change_pct >= 0.05 else text_dim)
        r_c = pos if d.capex_as_pct_of_revenue <= 0.05 else (acc if d.capex_as_pct_of_revenue <= 0.08 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.deal)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${d.annual_capex_budget_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${d.mx_capex_m:.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${d.growth_capex_m:.1f}M""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""${d.it_capex_m:.1f}M""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">+{d.yoy_change_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{d.capex_as_pct_of_revenue * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{d.capex_as_pct_of_ebitda * 100:.1f}%""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _approvals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Project","left"),("Deal","left"),("Budget ($M)","right"),("Approver","left"),
            ("Date","right"),("Committee","left"),("Conditions","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.project)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.deal)}</td>',
            f'{ck_data_cell(f"""${a.budget_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.approver)}</td>',
            f'{ck_data_cell(f"""{_html.escape(a.approval_date)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.committee)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(a.conditions)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tech_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Category","left"),("Projects","right"),("Budget ($M)","right"),("Impl (mo)","right"),
            ("Annual Savings ($M)","right"),("Deals Deployed","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.category)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{t.project_count}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${t.total_budget_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{t.typical_implementation_months}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${t.typical_annual_savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{t.deployed_deals}""", align="right", mono=True, tone="acc", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _denovo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Project","left"),("Deal","left"),("Market","left"),("Build Type","left"),
            ("Budget ($M)","right"),("Planned Open","right"),("Y1 Revenue ($M)","right"),
            ("Y3 EBITDA ($M)","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(d.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.project)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(d.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(d.market)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.build_type)}</td>',
            f'{ck_data_cell(f"""${d.budget_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(d.planned_open)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${d.projected_year_1_revenue_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${d.projected_year_3_ebitda_m:.1f}M""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(d.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_capex_budget(params: dict = None) -> str:
    from rcm_mc.data_public.capex_budget import compute_capex_budget
    r = compute_capex_budget()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Annual Budget", f"${r.total_annual_budget_m:,.1f}M", "", "") +
        ck_kpi_block("YTD Deployed", f"${r.total_ytd_spent_m:,.1f}M", "", "") +
        ck_kpi_block("Active Projects", str(r.total_projects), "", "") +
        ck_kpi_block("Weighted ROI", f"{r.weighted_avg_roi_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Capex / Revenue", f"{r.portfolio_capex_ratio_pct * 100:.2f}%", "", "") +
        ck_kpi_block("At Risk", str(r.projects_at_risk), "", "") +
        ck_kpi_block("De Novo Pipeline", str(len(r.denovo)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_tbl = _projects_table(r.projects)
    c_tbl = _categories_table(r.categories)
    d_tbl = _deal_budgets_table(r.deal_budgets)
    a_tbl = _approvals_table(r.approvals)
    t_tbl = _tech_table(r.tech)
    dn_tbl = _denovo_table(r.denovo)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    pct_deployed = r.total_ytd_spent_m / r.total_annual_budget_m * 100 if r.total_annual_budget_m else 0
    denovo_budget = sum(d.budget_m for d in r.denovo)
    denovo_yr1_rev = sum(d.projected_year_1_revenue_m for d in r.denovo)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Capex Planning / Capital Budget Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">${r.total_annual_budget_m:,.1f}M annual budget · ${r.total_ytd_spent_m:,.1f}M deployed ({pct_deployed:.0f}%) · {r.total_projects} projects · weighted {r.weighted_avg_roi_pct * 100:.1f}% ROI · {r.portfolio_capex_ratio_pct * 100:.2f}% avg capex / revenue — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Active Capex Projects</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Category Rollup</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Deal-Level Budget Mix</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Recent Capex Approvals</div>{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">Technology Investment by Category</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">De Novo Construction Pipeline</div>{dn_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Capex Portfolio Summary:</strong> ${r.total_annual_budget_m:,.1f}M annual capex budget — ${r.total_ytd_spent_m:,.1f}M deployed YTD ({pct_deployed:.0f}%) across {r.total_projects} projects at weighted {r.weighted_avg_roi_pct * 100:.1f}% ROI.
    Portfolio capex intensity {r.portfolio_capex_ratio_pct * 100:.2f}% of revenue — tracks healthcare services benchmark (5-6%). Consumer-facing specialties (fertility 9.5%, eye care 8.2%) highest; home health (2.2%) and specialty pharma (2.5%) lowest.
    Highest-ROI categories: Clinical AI deployment (55%, 12-month payback), Route optimization (55%, 15 mo), AI platform expansion, Mohs + Laser upgrade (38%), Platform modernization.
    De novo pipeline: 10 projects, ${denovo_budget:.1f}M budget, projected ${denovo_yr1_rev:.1f}M Year-1 revenue; Atlanta + Nashville GI ASCs (~$60M combined) deliver fastest payback (24 mo).
    Tech investment 29% of total capex budget (${sum(t.total_budget_m for t in r.tech):.1f}M) across EHR consolidation, clinical AI, RCM automation, cybersecurity, digital front door — high-ROI with 9-24 month paybacks.
    Only 1 project at risk (Redwood telehealth platform "behind" — corrective action via resource augmentation already approved by sponsor).
  </div>
</div>"""

    return chartis_shell(body, "Capex Budget", active_nav="/capex-budget",
        editorial_intro={
            "eyebrow": "CAPEX BUDGET",
            "headline": "What the capex budget page reveals on this deal.",
            "italic_word": "reveals",
        })
