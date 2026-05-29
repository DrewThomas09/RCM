"""Workforce Turnover / Retention Tracker — /workforce-retention."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor, ck_scatter


def _roles_scatter(items):
    """Quadrant — turnover vs replacement cost by role, so high-turnover
    high-cost roles (upper-right) are the retention priority."""
    import statistics
    pts, ys = [], []
    for x in items:
        xt = x.annual_turnover_pct * 100.0
        tn = ('negative' if x.annual_turnover_pct > x.industry_benchmark_pct else 'teal')
        pts.append((xt, x.replacement_cost_k, getattr(x, 'role', ''), tn)); ys.append(x.replacement_cost_k)
    return ck_scatter(
        pts, x_label='Annual turnover %', y_label='Replacement cost ($k)',
        y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = a role · upper-right = high turnover + high replacement cost (priority) · red = above industry benchmark',
    )


def _roles_chart(items) -> str:
    """Lead chart for the role-turnover table — roles ranked by annual
    turnover so the worst retention problems surface first. Bar width =
    turnover rate; value = signed gap vs the industry benchmark; tone
    marks severity (>=35% red · >=25% amber · >=15% teal · below green),
    matching the table's coloring. Full roster stays directly below.
    """
    ranked = sorted(items, key=lambda r: r.annual_turnover_pct, reverse=True)
    rows = []
    for r in ranked:
        t = r.annual_turnover_pct
        tone = ("negative" if t >= 0.35 else "warning" if t >= 0.25
                else "teal" if t >= 0.15 else "positive")
        gap = (r.annual_turnover_pct - r.industry_benchmark_pct) * 100.0
        rows.append(ck_bar_row(
            r.role,
            f"{gap:+.1f}pp",
            r.annual_turnover_pct * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = annual turnover rate · value = gap vs industry benchmark · '
        'tone = severity (red &ge;35% · amber &ge;25% · teal &ge;15% · green below)</div>'
        '</div>'
    )


def _roles_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]; neg = P["negative"]
    cols = [("Role","left"),("Headcount","right"),("Turnover %","right"),("Industry Benchmark","right"),
            ("Delta","right"),("Replacement Cost ($K)","right"),("Time to Fill (d)","right"),("Critical","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d = r.annual_turnover_pct - r.industry_benchmark_pct
        d_c = pos if d <= -0.02 else (acc if d <= 0.01 else warn)
        t_c = neg if r.annual_turnover_pct >= 0.35 else (warn if r.annual_turnover_pct >= 0.25 else (acc if r.annual_turnover_pct >= 0.15 else pos))
        cr_c = neg if r.critical else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.role)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{r.total_headcount:,}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{r.annual_turnover_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{r.industry_benchmark_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{d * 100:+.1f}pp</td>',
            f'{ck_data_cell(f"""${r.replacement_cost_k:,.1f}K""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{r.replacement_time_days}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{cr_c};font-weight:700">{"YES" if r.critical else "—"}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _deals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]; neg = P["negative"]
    cols = [("Deal","left"),("Sector","left"),("Headcount","right"),("Overall Turn %","right"),
            ("Clinical %","right"),("Support %","right"),("Contract Labor %","right"),
            ("Engagement","right"),("Retention Spend ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = neg if d.overall_turnover_pct >= 0.30 else (warn if d.overall_turnover_pct >= 0.22 else (acc if d.overall_turnover_pct >= 0.15 else pos))
        e_c = pos if d.engagement_score >= 8.0 else (acc if d.engagement_score >= 7.5 else (warn if d.engagement_score >= 7.0 else neg))
        cl_c = warn if d.contract_labor_pct >= 0.10 else (acc if d.contract_labor_pct >= 0.05 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'{ck_data_cell(f"""{d.total_headcount:,}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{d.overall_turnover_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{d.clinical_turnover_pct * 100:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{d.support_turnover_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cl_c};font-weight:700">{d.contract_labor_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{d.engagement_score:.1f}</td>',
            f'{ck_data_cell(f"""${d.retention_spend_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _programs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Program","left"),("Deals","right"),("Employees","right"),("Annual Cost ($M)","right"),
            ("Turnover Impact","right"),("Rationale","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        i_c = pos if p.turnover_impact_pp <= -3.0 else (acc if p.turnover_impact_pp <= -2.0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.program)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{p.portfolio_deals}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.employees_covered:,}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${p.annual_cost_m:.1f}M""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:700">{p.turnover_impact_pp:+.1f}pp</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(p.rationale)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _contract_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Agency Spend ($M)","right"),("% of Labor","right"),("Premium vs Staff","right"),
            ("Peak Quarters","center"),("Transition to Staff (K)","right"),("Savings Opp ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = warn if c.agency_pct_of_labor >= 0.10 else (acc if c.agency_pct_of_labor >= 0.05 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.agency_spend_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{c.agency_pct_of_labor * 100:.1f}%</td>',
            f'{ck_data_cell(f"""+{c.premium_vs_staff_pct * 100:.0f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.peak_quarters)}</td>',
            f'{ck_data_cell(f"""{c.transition_to_staff_k}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.savings_opportunity_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _surveys_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Response %","right"),("Engagement","right"),("eNPS","right"),
            ("Burnout %","right"),("Would Recommend %","right"),("Top Concerns","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = pos if s.engagement_score >= 8.0 else (acc if s.engagement_score >= 7.5 else (warn if s.engagement_score >= 7.0 else P["negative"]))
        n_c = pos if s.ennp_score >= 40 else (acc if s.ennp_score >= 25 else warn)
        b_c = warn if s.burnout_rate_pct >= 0.25 else (acc if s.burnout_rate_pct >= 0.15 else pos)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.deal)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.response_rate_pct * 100:.0f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{s.engagement_score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{n_c};font-weight:700">+{s.ennp_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">{s.burnout_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{s.would_recommend_pct * 100:.0f}%""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(s.top_3_concerns)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benefits_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Benefit","left"),("P25","center"),("Median","center"),("P75","center"),("Portfolio","center"),("Adoption %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = pos if b.adoption_rate_pct >= 0.90 else (acc if b.adoption_rate_pct >= 0.60 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.benefit)}""", mono=True, weight=700)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(b.p25)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(b.median)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos}">{_html.escape(b.p75)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:700">{_html.escape(b.portfolio_median)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{b.adoption_rate_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hpsa_retention_panel() -> str:
    """Real HRSA shortage-area anchor — provider retention is structurally
    harder where the labor market is already short. Designated HPSAs and
    their shortage scores are real public HRSA data; the deal's turnover /
    engagement / retention-program model below is illustrative."""
    from rcm_mc.data import hrsa_data as _h
    summ = _h.hpsa_summary()
    if not summ.get("total_designated"):
        return ""
    top = _h.top_shortage_states(6)

    border = P["border"]; tprim = P["text"]; tdim = P["text_dim"]; acc = P["accent"]
    mx = max((int(t["designated_pc_hpsas"]) for t in top), default=1) or 1
    rows = "".join(
        f'<tr>'
        f'<td style="padding:3px 8px;font-family:JetBrains Mono,monospace;font-size:11px;color:{tprim}">{_html.escape(str(t["state"]))}</td>'
        f'<td style="padding:3px 8px;width:50%">'
        f'<svg width="100%" height="9" preserveAspectRatio="none" viewBox="0 0 100 9">'
        f'<rect x="0" y="1" width="{int(int(t["designated_pc_hpsas"])/mx*100)}" height="7" fill="{acc}" opacity="0.75"/></svg></td>'
        f'<td style="padding:3px 8px;text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;'
        f'font-variant-numeric:tabular-nums;color:{tprim}">{int(t["designated_pc_hpsas"]):,}</td>'
        f'</tr>'
        for t in top
    )
    total = int(summ.get("total_designated", 0))
    med = summ.get("national_median_score", "")
    snap = summ.get("snapshot_date", "")
    return f'''
<div style="background:{P["panel"]};border:1px solid {border};border-left:3px solid {acc};
  padding:14px 16px;margin-bottom:16px">
  <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px">
    Real HRSA shortage areas &mdash; the retention-pressure backdrop
    <span style="color:{acc};font-weight:600"> · LIVE</span>
  </div>
  <div style="display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start">
    <div style="white-space:nowrap">
      <div style="font-family:JetBrains Mono,monospace;font-size:20px;color:{tprim};
        font-variant-numeric:tabular-nums">{total:,}</div>
      <div style="font-size:10px;color:{tdim};margin-bottom:8px">designated primary-care<br>shortage areas (HPSAs)</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:13px;color:{tprim};
        font-variant-numeric:tabular-nums">{med}</div>
      <div style="font-size:10px;color:{tdim}">national median HPSA score</div>
    </div>
    <div>
      <div style="font-size:9px;color:{P["text_faint"]};margin-bottom:4px">MOST PRIMARY-CARE SHORTAGE AREAS BY STATE</div>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P["text_faint"]}">
    HRSA HPSA designations{(" (" + str(snap) + ")") if snap else ""}. Real labor-shortage
    signal &mdash; deeper shortage = harder retention. The deal's turnover, engagement,
    and retention-program figures below are illustrative.
  </div>
</div>'''


def render_workforce_retention(params: dict = None) -> str:
    from rcm_mc.data_public.workforce_retention import compute_workforce_retention
    r = compute_workforce_retention()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total Headcount", f"{r.total_headcount:,}", "", "") +
        ck_kpi_block("Weighted Turnover", f"{r.weighted_turnover_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Engagement", f"{r.avg_engagement_score:.2f}", "/10", "") +
        ck_kpi_block("Contract Labor Spend", f"${r.total_contract_labor_spend_m:.1f}M", "", "") +
        ck_kpi_block("Retention Spend", f"${r.total_retention_spend_m:.1f}M", "", "") +
        ck_kpi_block("Critical Roles", str(r.critical_roles), "", "") +
        ck_kpi_block("Active Programs", str(len(r.programs)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    r_chart = _roles_chart(r.roles)
    r_tbl = _roles_table(r.roles)
    r_scatter = _roles_scatter(r.roles)
    d_tbl = _deals_table(r.deals)
    p_tbl = _programs_table(r.programs)
    cl_tbl = _contract_table(r.contract_labor)
    s_tbl = _surveys_table(r.surveys)
    b_tbl = _benefits_table(r.benefits)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    program_cost = sum(p.annual_cost_m for p in r.programs)
    savings_opp = sum(c.savings_opportunity_m for c in r.contract_labor)
    page_title = ck_page_title(
        "Workforce Turnover / Retention Tracker",
        eyebrow="WORKFORCE RETENTION",
        meta=f"""{r.total_headcount:,} headcount · {r.weighted_turnover_pct * 100:.1f}% weighted turnover · {r.avg_engagement_score:.2f}/10 engagement · ${r.total_contract_labor_spend_m:.1f}M contract labor · ${r.total_retention_spend_m:.1f}M retention spend · {r.critical_roles} critical roles — {r.corpus_deal_count:,} corpus deals""",
    )
    
    value_anchor = ck_value_anchor(
        "Workforce Retention",
        f"{r.weighted_turnover_pct * 100:.1f}% turnover",
        delta=f"{r.total_headcount:,} headcount · {r.critical_roles} critical roles flagged",
        opportunity=f"${r.total_contract_labor_spend_m:,.1f}M agency-labor spend",
        tone="warning",
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  {_hpsa_retention_panel()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Turnover by Role (portfolio aggregate)</div>{r_chart}{r_scatter}{r_tbl}</div>
  <div style="{cell}"><div style="{h3}">Deal-Level Turnover & Engagement</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Contract Labor / Agency Dependency</div>{cl_tbl}</div>
  <div style="{cell}"><div style="{h3}">Retention Programs</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Engagement Survey Results</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Benefits Benchmarking</div>{b_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Workforce Retention Summary:</strong> {r.total_headcount:,} portfolio employees at {r.weighted_turnover_pct * 100:.1f}% weighted turnover — 2-3pp inside industry benchmarks for most roles.
    Highest-risk roles: Housekeeping/EVS (48.5%), Food Service (42.5%), Medical Assistant (34.5%), Phlebotomy (38.5%) — all non-clinical support roles with highest replacement volume but lower unit cost.
    Critical roles to prioritize: RN bedside (22.5% turnover), behavioral tech (32.5%), OR/specialty RNs, and allied-health technicians (cath lab, echo, radiology) — replacement cost $62-135K per FTE.
    Deal watchlist: Project Sage (Home Health, 38.5% turnover, 16.5% contract labor, $48.5M agency spend, $28.5M savings opportunity), Project Redwood (28.5%/12.5%), Project Linden (32.5%/12.5%).
    Retention programs spending ${program_cost:.1f}M annually — top-ROI programs: flexible scheduling (-4.5pp, $0 cost), loan repayment (-4.2pp), sign-on bonus (-3.5pp for critical roles).
    Contract labor savings opportunity ${savings_opp:.1f}M via structured agency-to-staff conversion — Sage alone $28.5M opportunity through in-home care workforce pipeline expansion.
    Benefits vs benchmarks: health insurance contribution (72% — between median/P75), 401(k) match (4% — at median), parental leave (12 weeks — between median/P75); childcare and student loan at P25 — upgrade opportunities.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Workforce Retention", active_nav="/workforce-retention",
        editorial_intro={
            "eyebrow": "WORKFORCE RETENTION",
            "headline": "What the workforce retention page reveals on this deal.",
            "italic_word": "reveals",
        })
