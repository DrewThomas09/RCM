"""Workforce Turnover / Retention Tracker — /workforce-retention."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _roles_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]; neg = P["negative"]
    cols = [("Role","left"),("Headcount","right"),("Turnover %","right"),("Industry Benchmark","right"),
            ("Delta","right"),("Replacement Cost ($K)","right"),("Time to Fill (d)","right"),("Critical","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d = r.annual_turnover_pct - r.industry_benchmark_pct
        d_c = pos if d <= -0.02 else (acc if d <= 0.01 else warn)
        t_c = neg if r.annual_turnover_pct >= 0.35 else (warn if r.annual_turnover_pct >= 0.25 else (acc if r.annual_turnover_pct >= 0.15 else pos))
        cr_c = neg if r.critical else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{r.total_headcount:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{r.annual_turnover_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.industry_benchmark_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{d * 100:+.1f}pp</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.replacement_cost_k:,.1f}K</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{r.replacement_time_days}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{cr_c};font-weight:700">{"YES" if r.critical else "—"}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _deals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]; neg = P["negative"]
    cols = [("Deal","left"),("Sector","left"),("Headcount","right"),("Overall Turn %","right"),
            ("Clinical %","right"),("Support %","right"),("Contract Labor %","right"),
            ("Engagement","right"),("Retention Spend ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = neg if d.overall_turnover_pct >= 0.30 else (warn if d.overall_turnover_pct >= 0.22 else (acc if d.overall_turnover_pct >= 0.15 else pos))
        e_c = pos if d.engagement_score >= 8.0 else (acc if d.engagement_score >= 7.5 else (warn if d.engagement_score >= 7.0 else neg))
        cl_c = warn if d.contract_labor_pct >= 0.10 else (acc if d.contract_labor_pct >= 0.05 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(d.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{d.total_headcount:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{d.overall_turnover_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{d.clinical_turnover_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.support_turnover_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cl_c};font-weight:700">{d.contract_labor_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{d.engagement_score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${d.retention_spend_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _programs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Program","left"),("Deals","right"),("Employees","right"),("Annual Cost ($M)","right"),
            ("Turnover Impact","right"),("Rationale","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        i_c = pos if p.turnover_impact_pp <= -3.0 else (acc if p.turnover_impact_pp <= -2.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.program)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.portfolio_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{p.employees_covered:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.annual_cost_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:700">{p.turnover_impact_pp:+.1f}pp</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(p.rationale)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _contract_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Agency Spend ($M)","right"),("% of Labor","right"),("Premium vs Staff","right"),
            ("Peak Quarters","center"),("Transition to Staff (K)","right"),("Savings Opp ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = warn if c.agency_pct_of_labor >= 0.10 else (acc if c.agency_pct_of_labor >= 0.05 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${c.agency_spend_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{c.agency_pct_of_labor * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">+{c.premium_vs_staff_pct * 100:.0f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.peak_quarters)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.transition_to_staff_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.savings_opportunity_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _surveys_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Response %","right"),("Engagement","right"),("eNPS","right"),
            ("Burnout %","right"),("Would Recommend %","right"),("Top Concerns","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = pos if s.engagement_score >= 8.0 else (acc if s.engagement_score >= 7.5 else (warn if s.engagement_score >= 7.0 else P["negative"]))
        n_c = pos if s.ennp_score >= 40 else (acc if s.ennp_score >= 25 else warn)
        b_c = warn if s.burnout_rate_pct >= 0.25 else (acc if s.burnout_rate_pct >= 0.15 else pos)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{s.response_rate_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{s.engagement_score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{n_c};font-weight:700">+{s.ennp_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">{s.burnout_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{s.would_recommend_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(s.top_3_concerns)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benefits_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Benefit","left"),("P25","center"),("Median","center"),("P75","center"),("Portfolio","center"),("Adoption %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = pos if b.adoption_rate_pct >= 0.90 else (acc if b.adoption_rate_pct >= 0.60 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(b.benefit)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(b.p25)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(b.median)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos}">{_html.escape(b.p75)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:700">{_html.escape(b.portfolio_median)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{b.adoption_rate_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    r_tbl = _roles_table(r.roles)
    d_tbl = _deals_table(r.deals)
    p_tbl = _programs_table(r.programs)
    cl_tbl = _contract_table(r.contract_labor)
    s_tbl = _surveys_table(r.surveys)
    b_tbl = _benefits_table(r.benefits)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    program_cost = sum(p.annual_cost_m for p in r.programs)
    savings_opp = sum(c.savings_opportunity_m for c in r.contract_labor)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Workforce Turnover / Retention Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_headcount:,} headcount · {r.weighted_turnover_pct * 100:.1f}% weighted turnover · {r.avg_engagement_score:.2f}/10 engagement · ${r.total_contract_labor_spend_m:.1f}M contract labor · ${r.total_retention_spend_m:.1f}M retention spend · {r.critical_roles} critical roles — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Turnover by Role (portfolio aggregate)</div>{r_tbl}</div>
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

    return chartis_shell(body, "Workforce Retention", active_nav="/workforce-retention", data_source="synthetic")