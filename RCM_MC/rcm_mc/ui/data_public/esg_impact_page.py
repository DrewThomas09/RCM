"""ESG / Impact Reporting Tracker — /esg-impact."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _score_color(s: float) -> str:
    if s >= 8.5: return P["positive"]
    if s >= 7.5: return P["accent"]
    if s >= 6.5: return P["warning"]
    return P["negative"]


def _scorecard_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("Environmental","right"),("Social","right"),
            ("Governance","right"),("Composite","right"),("Prior Year","right"),
            ("YoY Δ","right"),("SASB Materiality","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = _score_color(s.environmental_score)
        so_c = _score_color(s.social_score)
        g_c = _score_color(s.governance_score)
        c_c = _score_color(s.composite_score)
        d_c = pos if s.year_over_year_change > 0.3 else (acc if s.year_over_year_change > 0 else text_dim)
        sm_c = pos if s.sasb_materiality_met else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{s.environmental_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{so_c};font-weight:700">{s.social_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{s.governance_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{s.composite_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.prior_year_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{s.year_over_year_change:+.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{sm_c};font-weight:700">{"YES" if s.sasb_materiality_met else "NO"}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _access_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Medicaid %","right"),("Charity Care ($M)","right"),
            ("Sliding-Scale (K)","right"),("Avg Wait (days)","right"),("No-Show %","right"),("Languages","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if a.medicaid_pct >= 0.30 else (acc if a.medicaid_pct >= 0.15 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(a.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{a.medicaid_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${a.uninsured_charity_care_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.sliding_scale_patients_k:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{a.avg_wait_days:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.no_show_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.language_support_count}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _outcomes_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Deal","left"),("Sector","left"),("HEDIS","right"),("Stars Equiv","right"),
            ("Readmission %","right"),("Patient Sat","right"),("Guideline Adherence","right"),("Sentinel Events","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        h_c = pos if o.hedis_composite >= 0.87 else (acc if o.hedis_composite >= 0.84 else P["warning"])
        r_c = pos if o.readmission_rate_pct <= 0.04 else (acc if o.readmission_rate_pct <= 0.07 else P["warning"])
        s_c = pos if o.patient_satisfaction >= 4.5 else acc
        g_c = pos if o.clinical_guideline_adherence_pct >= 0.92 else acc
        sev_c = neg if o.sentinel_events > 0 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(o.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{h_c};font-weight:700">{o.hedis_composite:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{o.cms_stars_equivalent:.1f}★</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{o.readmission_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{o.patient_satisfaction:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{o.clinical_guideline_adherence_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sev_c};font-weight:700">{o.sentinel_events}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _dei_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Employees","right"),("Female %","right"),("POC %","right"),
            ("Female Lead %","right"),("POC Lead %","right"),("Turnover %","right"),
            ("Engagement","right"),("Living Wage","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = pos if d.turnover_rate_pct <= 0.10 else (acc if d.turnover_rate_pct <= 0.15 else P["warning"])
        e_c = pos if d.engagement_score >= 8.0 else (acc if d.engagement_score >= 7.2 else text_dim)
        lw_c = pos if d.living_wage_compliant else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(d.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{d.total_employees:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{d.female_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{d.poc_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{d.female_leadership_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{d.poc_leadership_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{d.turnover_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{d.engagement_score:.1f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{lw_c};font-weight:700">{"YES" if d.living_wage_compliant else "NO"}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _emissions_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Scope 1 (MTCO2e)","right"),("Scope 2 (MTCO2e)","right"),
            ("Scope 3 (MTCO2e)","right"),("Intensity","right"),("Renewable %","right"),
            ("SBTi","center"),("Reduction vs Baseline","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if e.renewable_electricity_pct >= 0.45 else (acc if e.renewable_electricity_pct >= 0.35 else warn)
        sb_c = pos if "validated" in e.sbti_commitment else (acc if "committed" in e.sbti_commitment else warn)
        rd_c = pos if e.reduction_vs_baseline_pct <= -0.15 else (acc if e.reduction_vs_baseline_pct <= -0.08 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.scope_1_mtco2e:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.scope_2_mtco2e:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.scope_3_mtco2e:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{e.intensity_per_patient:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{e.renewable_electricity_pct * 100:.0f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sb_c};border:1px solid {sb_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.sbti_commitment)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rd_c};font-weight:700">{e.reduction_vs_baseline_pct * 100:+.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _governance_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Indep Directors","right"),("Board Diversity","right"),
            ("Ethics Hotline","center"),("CSR Report","center"),("Double Mat","center"),
            ("Whistleblower","right"),("Compliance Training","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        i_c = pos if g.independent_directors_pct >= 0.40 else acc
        d_c = pos if g.board_diversity_pct >= 0.40 else (acc if g.board_diversity_pct >= 0.30 else P["warning"])
        def yn(b):
            c = pos if b else P["warning"]
            return f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c};font-weight:700">{"YES" if b else "NO"}</td>'
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(g.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:700">{g.independent_directors_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{g.board_diversity_pct * 100:.1f}%</td>',
            yn(g.ethics_hotline),
            yn(g.annual_csr_report),
            yn(g.dsh_assessment),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{g.whistleblower_claims_resolved}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{g.compliance_training_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _frameworks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Framework","left"),("Version","left"),("Deals","right"),("Compliant","right"),
            ("Avg Maturity","right"),("Next Reporting","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if f.avg_maturity >= 0.85 else (acc if f.avg_maturity >= 0.70 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.framework)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(f.version)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{f.portfolio_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{f.compliant_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{f.avg_maturity * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(f.next_reporting)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_esg_impact(params: dict = None) -> str:
    from rcm_mc.data_public.esg_impact import compute_esg_impact
    r = compute_esg_impact()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Portfolio Cos", str(r.total_portcos), "", "") +
        ck_kpi_block("Avg ESG Score", f"{r.avg_composite_score:.2f}", "/10", "") +
        ck_kpi_block("YoY Delta", f"{r.prior_year_delta:+.2f}", "", "") +
        ck_kpi_block("Charity Care LTM", f"${r.total_charity_care_m:.1f}M", "", "") +
        ck_kpi_block("Avg Medicaid Mix", f"{r.total_medicaid_patients_k:.1f}%", "", "") +
        ck_kpi_block("Scope 1+2 (MTCO2e)", f"{r.total_scope_12_mtco2e:,.0f}", "", "") +
        ck_kpi_block("Frameworks", str(r.frameworks_tracked), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    s_tbl = _scorecard_table(r.scorecards)
    a_tbl = _access_table(r.access)
    o_tbl = _outcomes_table(r.outcomes)
    d_tbl = _dei_table(r.dei)
    e_tbl = _emissions_table(r.emissions)
    g_tbl = _governance_table(r.governance)
    f_tbl = _frameworks_table(r.frameworks)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    medicaid_ge20 = sum(1 for a in r.access if a.medicaid_pct >= 0.20)
    sbti_validated = sum(1 for e in r.emissions if "validated" in e.sbti_commitment)

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">ESG / Impact Reporting Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_portcos} portcos · {r.avg_composite_score:.2f}/10 average ESG score (+{r.prior_year_delta:.2f} YoY) · ${r.total_charity_care_m:.1f}M charity care · {r.total_scope_12_mtco2e:,.0f} MTCO2e Scope 1+2 · {r.frameworks_tracked} frameworks tracked — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">ESG Composite Scorecards</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Patient Access / Community Benefit</div>{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">Clinical Outcomes</div>{o_tbl}</div>
  <div style="{cell}"><div style="{h3}">Workforce DEI</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Carbon Emissions & SBTi</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Governance Metrics</div>{g_tbl}</div>
  <div style="{cell}"><div style="{h3}">Framework Compliance</div>{f_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">ESG Portfolio Summary:</strong> Portfolio-wide ESG composite {r.avg_composite_score:.2f}/10 — YoY improvement of +{r.prior_year_delta:.2f} driven primarily by social score gains (patient access + clinical quality).
    Community benefit: ${r.total_charity_care_m:.1f}M in uninsured/charity care LTM; {medicaid_ge20} of {len(r.access)} portcos serve ≥20% Medicaid patients — strong access alignment with healthcare-as-social-infrastructure thesis.
    Clinical outcomes: HEDIS composite range 0.81-0.90; 2 sentinel events YTD (Sage, Linden) both fully investigated and root-cause remediated.
    Workforce: DEI strong on gender (68% female workforce average); POC representation 47% workforce / 41% leadership — tracks above S&P 500 healthcare benchmarks ±3pp.
    Climate: {sbti_validated} portcos with SBTi-validated targets, 5 committed, 3 not yet committed — Fund VI fundraising materials commit to full SBTi coverage by 2027.
    Frameworks: 14/16 PRI-compliant; 15/16 SASB-aligned; CSRD applies to 3 EU-exposure portcos (2 compliant, 1 in progress); SEC climate rule on hold pending litigation.
  </div>
</div>"""

    return chartis_shell(body, "ESG / Impact", active_nav="/esg-impact")
