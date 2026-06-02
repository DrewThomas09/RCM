"""Capex Planning / Capital Budget Tracker — /capex-budget."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor, ck_scatter
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel

_CAPEX_NEEDED = [
    ("project", "capex project"), ("category", "maintenance / growth"),
    ("budget", "budget $"), ("actual", "actual-to-date $"),
    ("expected_roi_pct", "expected ROI %"), ("status", "status"),
]


def _projects_scatter(items):
    """Quadrant — payback vs ROI per capex project, so high-ROI fast-payback
    projects (upper-left) and slow low-ROI ones separate."""
    import statistics
    pts, ys = [], []
    for p in items:
        y = p.roi_pct * 100.0
        tn = ('positive' if p.roi_pct >= 0.20 else 'teal' if p.roi_pct >= 0.10 else 'warning')
        pts.append((p.payback_months, y, p.project_id, tn)); ys.append(y)
    return ck_scatter(
        pts, x_label='Payback (months)', y_label='ROI %',
        y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = a project · upper-left = high ROI + fast payback (best) · tone = ROI',
    )

_EXPLAINER_CSS = """<style>
.ck-cx-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-cx-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


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


def _projects_chart(items) -> str:
    """Lead chart for the project table — capex projects ranked by ROI
    so the highest-return investments surface before the detail grid.
    Bar width = projected ROI; value = budget ($M); tone marks the
    table's ROI tiers (>=35% green · >=25% teal · below amber). Full
    project grid stays directly below.
    """
    ranked = sorted(items, key=lambda p: p.roi_pct, reverse=True)
    rows = []
    for p in ranked:
        tone = ("positive" if p.roi_pct >= 0.35 else "teal"
                if p.roi_pct >= 0.25 else "warning")
        rows.append(ck_bar_row(
            p.project_id,
            f"${p.budget_m:,.1f}M",
            p.roi_pct * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = projected ROI · value = project budget ($M) · '
        'tone = return tier (green &ge;35% · teal &ge;25% · amber below)</div>'
        '</div>'
    )


def _projects_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("ID","left"),("Deal","left"),("Category","left"),("Description","left"),
            ("Budget ($M)","right"),("Spent ($M)","right"),("% Complete","right"),
            ("Finish","right"),("ROI","right"),("Payback (mo)","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    _maxbar = max((p.budget_m for p in items), default=1.0) or 1.0
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
            f'{ck_data_cell(f"""${p.budget_m:.1f}M""", align="right", mono=True, weight=700, bar=p.budget_m / _maxbar * 100)}',
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

    p_chart = _projects_chart(r.projects)
    p_scatter = _projects_scatter(r.projects)
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
    # 2026-05-30 audit P5 editorial: capex planning and capital
    # budget tracking are the same activity. "Capex Budget Tracker"
    # matches the eyebrow (CAPEX BUDGET) and the route /capex-budget.
    page_title = ck_page_title(
        "Capex Budget Tracker",
        eyebrow="CAPEX BUDGET",
        meta=(
            f"${r.total_annual_budget_m:,.1f}M budget · "
            f"{r.total_projects} projects · "
            f"weighted {r.weighted_avg_roi_pct * 100:.1f}% ROI · "
            f"{r.corpus_deal_count:,} corpus deals"
        ),
    )
    cx_explainer = (
        '<p class="ck-cx-explainer">'
        "<em>What the capex budget reveals on this deal.</em> "
        "Active projects, category rollups, deal-level budget mix, tech investment, "
        "and de novo construction pipeline — with deployment pacing and ROI benchmarks."
        "</p>"
    )
    value_anchor = ck_value_anchor(
        "Capex Program",
        f"${r.total_annual_budget_m:,.1f}M budget",
        delta=f"${r.total_ytd_spent_m:,.1f}M spent YTD · {r.weighted_avg_roi_pct * 100:.1f}% wtd ROI · {r.projects_at_risk} at risk",
        tone="teal",
    )
    body = page_title + data_required_panel(P, title="Capex Budget", needed=_CAPEX_NEEDED,
        template="capex_budget_template.csv", request_from="Portfolio-company CFO / FP&A",
        activates="budget-vs-actual, maintenance-vs-growth split, ROI ranking",
        guide_hint="What capex data do I need to upload?") + ck_illustrative_note("figures") + cx_explainer + f"""
<div class="ck-page-wrap">
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Active Capex Projects</div>{p_chart}{p_scatter}{p_tbl}</div>
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

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Capex Budget", active_nav="/capex-budget",
        extra_css=_EXPLAINER_CSS)
