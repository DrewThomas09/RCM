"""Physician Labor Market Tracker — /physician-labor."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _specialties_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Specialty","left"),("Active","right"),("Grad Supply","right"),("Retirements","right"),
            ("Net Change","right"),("Median Age","right"),("2030 Shortage","right"),("Wage Inflation","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        net_c = pos if s.net_annual_change > 0 else neg
        short_c = neg if s.projected_2030_shortage >= 15000 else (warn if s.projected_2030_shortage >= 5000 else text_dim)
        wage_c = neg if s.wage_inflation_ltm_pct >= 0.07 else (warn if s.wage_inflation_ltm_pct >= 0.055 else text_dim)
        age_c = warn if s.median_age >= 55 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.active_physicians:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{s.annual_grad_supply:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{s.annual_retirements:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{net_c};font-weight:700">{s.net_annual_change:+,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{age_c};font-weight:700">{s.median_age}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{short_c};font-weight:700">{s.projected_2030_shortage:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{wage_c};font-weight:600">{s.wage_inflation_ltm_pct * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _wages_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Specialty","left"),("2019 Median ($k)","right"),("2024 Median ($k)","right"),
            ("CAGR","right"),("Locum Premium","right"),("Signing Bonus ($k)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(w.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${w.median_comp_2019_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${w.median_comp_2024_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">{w.cagr_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{w.locum_premium_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${w.signing_bonus_median_k:,.0f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _extenders_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Category","left"),("FTE Supply","right"),("Productivity vs MD","right"),
            ("Cost Ratio vs MD","right"),("Scope","left"),("Full-Practice States","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if e.productivity_vs_md >= 0.85 else acc
        c_c = pos if e.cost_ratio_vs_md <= 0.55 else acc
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.fte_supply:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{e.productivity_vs_md * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{e.cost_ratio_vs_md * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.scope_of_practice)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{e.state_practice_authority}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _burnout_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Specialty","left"),("Burnout Rate","right"),("3-Yr Attrition","right"),("Reduced Hours","right"),("Retention Invest PMPY ($k)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        b_c = neg if b.burnout_rate_pct >= 0.55 else (warn if b.burnout_rate_pct >= 0.45 else text_dim)
        a_c = neg if b.attrition_3yr_pct >= 0.18 else (warn if b.attrition_3yr_pct >= 0.14 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">{b.burnout_rate_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{b.attrition_3yr_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.reduced_hours_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">${b.retention_investment_pmpy_k:,.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _geo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Region Type","left"),("Phys/100k","right"),("Severity","center"),("HPSA Score","right"),("Loan Repayment","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sev_c = {"no shortage": pos, "mild shortage": text_dim, "moderate shortage": warn, "severe shortage": neg, "critical shortage": neg}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(g.shortage_severity, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(g.region_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{g.physician_per_100k}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.shortage_severity)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn if g.hpsa_score > 15 else text_dim}">{g.hpsa_score if g.hpsa_score else "—"}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos if g.loan_repayment_available else text_dim}">{"YES" if g.loan_repayment_available else "NO"}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_physician_labor(params: dict = None) -> str:
    from rcm_mc.data_public.physician_labor import compute_physician_labor
    r = compute_physician_labor()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Active Physicians", f"{r.total_active_physicians:,}", "", "") +
        ck_kpi_block("Median Age", f"{r.avg_median_age:.1f}", "", "") +
        ck_kpi_block("Specialties in Shortage", str(r.specialties_in_shortage), "", "") +
        ck_kpi_block("Wage Inflation LTM", f"{r.blended_wage_inflation_pct * 100:+.1f}%", "", "") +
        ck_kpi_block("Specialties Covered", str(len(r.specialties)), "", "") +
        ck_kpi_block("Extender FTE", f"{sum(e.fte_supply for e in r.extenders):,}", "", "") +
        ck_kpi_block("Burnout Specialties", str(len(r.burnout)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    s_tbl = _specialties_table(r.specialties)
    w_tbl = _wages_table(r.wages)
    e_tbl = _extenders_table(r.extenders)
    b_tbl = _burnout_table(r.burnout)
    g_tbl = _geo_table(r.geography)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_shortage_2030 = sum(s.projected_2030_shortage for s in r.specialties)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Physician Labor Market Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Supply/demand by specialty · wage inflation · NP/PA extender economics · burnout index · geographic HPSA mapping — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Specialty-Level Supply/Demand &amp; 2030 Shortage Projection</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Wage Growth 2019-2024 &amp; Locum Premia</div>{w_tbl}</div>
  <div style="{cell}"><div style="{h3}">NP / PA / CRNA Extender Economics</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Burnout &amp; Retention Index</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Geographic Physician Density &amp; HPSA Designation</div>{g_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Labor Market Thesis:</strong> {r.total_active_physicians:,} active physicians; median age {r.avg_median_age:.1f}; {r.specialties_in_shortage} specialties in shortage by 2030.
    Aggregate 2030 shortage projected at {total_shortage_2030:,} physicians — primary care, psychiatry, and anesthesiology are the most acute gaps.
    Wage inflation running at {r.blended_wage_inflation_pct * 100:.1f}% blended; psychiatry, hospitalist, and GI specialties see 7-9% annual wage growth.
    NP/PA extender strategy delivers 68-92% of MD productivity at 48-62% of cost — a critical labor-arbitrage lever, especially in full-practice-authority states.
    Rural/frontier markets offer HPSA loan-repayment programs and premium-rate negotiating leverage. Post-COVID burnout drives 16-22% 3-year attrition in front-line specialties.
  </div>
</div>"""

    return chartis_shell(body, "Physician Labor", active_nav="/physician-labor")
