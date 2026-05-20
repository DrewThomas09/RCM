"""Medicaid Redetermination / Coverage Unwinding Tracker — /medicaid-unwinding."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor


def _deals_chart(items) -> str:
    """Lead chart for the deal-exposure table — deals ranked by revenue
    at risk from Medicaid unwinding so the most exposed books surface
    first. Bar width = share of total revenue impact; value = revenue
    impact ($M, signed); tone flags bad-debt risk by the share of lost
    coverage shifting to self-pay (>=35% red · otherwise amber). Full
    exposure grid stays directly below.
    """
    total = sum(abs(d.revenue_impact_m) for d in items) or 1.0
    ranked = sorted(items, key=lambda d: abs(d.revenue_impact_m), reverse=True)
    rows = []
    for d in ranked:
        self_pay = d.coverage_shift_pct.get("self_pay", 0.0)
        tone = "negative" if self_pay >= 0.35 else "warning"
        rows.append(ck_bar_row(
            d.deal,
            f"${d.revenue_impact_m:,.1f}M",
            abs(d.revenue_impact_m) / total * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of total revenue impact · value = revenue impact '
        '($M) · tone = bad-debt risk (red if &ge;35% of lost coverage '
        'goes self-pay)</div>'
        '</div>'
    )


def _pace_color(p: str) -> str:
    return {
        "slow": P["positive"],
        "moderating": P["accent"],
        "accelerated": P["warning"],
    }.get(p, P["text_dim"])


def _posture_color(p: str) -> str:
    if "pro-beneficiary" in p: return P["positive"]
    if "balanced" in p: return P["accent"]
    if "high" in p: return P["warning"]
    return P["text_dim"]


def _deals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Deal","left"),("Sector","left"),("Pre-PHE Medicaid %","right"),("Current Medicaid %","right"),
            ("Medicaid Lost (K)","right"),("→ ACA %","right"),("→ Commercial %","right"),
            ("→ Self-Pay %","right"),("→ Back Medicaid %","right"),("Rev Impact ($M)","right"),("Mitigation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'{ck_data_cell(f"""{d.pre_phe_medicaid_pct * 100:.1f}%""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{d.current_medicaid_pct * 100:.1f}%""", align="right", mono=True, tone="acc", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]};font-weight:700">{d.medicaid_patients_lost_k:.1f}</td>',
            f'{ck_data_cell(f"""{d.coverage_shift_pct.get("aca", 0) * 100:.0f}%""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{d.coverage_shift_pct.get("commercial_employer", 0) * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{d.coverage_shift_pct.get("self_pay", 0) * 100:.0f}%""", align="right", mono=True, tone="neg", weight=600)}',
            f'{ck_data_cell(f"""{d.coverage_shift_pct.get("back_medicaid", 0) * 100:.0f}%""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""${d.revenue_impact_m:+.1f}M""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(d.mitigation)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _states_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("State","left"),("Disenrolled (M)","right"),("Pre-PHE (M)","right"),("Disenroll %","right"),
            ("Procedural %","right"),("Gain ACA %","right"),("Back to Medicaid %","right"),("Portfolio Deals","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = warn if s.disenroll_rate_pct >= 0.30 else (acc if s.disenroll_rate_pct >= 0.22 else text_dim)
        pr_c = warn if s.procedural_disenroll_pct >= 0.40 else (acc if s.procedural_disenroll_pct >= 0.28 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.state)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.disenrolled_m:.1f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.total_medicaid_pre_phe_m:,.1f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{s.disenroll_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pr_c};font-weight:700">{s.procedural_disenroll_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{s.coverage_gain_aca_pct * 100:.0f}%""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{s.back_to_medicaid_pct * 100:.0f}%""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{s.portfolio_deals}""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _shifts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("From","left"),("To","left"),("Members Shifted (M)","right"),
            ("Rev/Patient Δ","right"),("Portfolio Impact ($M)","right"),("Retention Strategy","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if s.revenue_per_patient_delta > 0 else (neg if s.revenue_per_patient_delta < 0 else text_dim)
        p_c = pos if s.portfolio_impact_m > 0 else (neg if s.portfolio_impact_m < 0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.from_coverage)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(s.to_coverage)}""", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{s.members_shifted_m:.2f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">${s.revenue_per_patient_delta:+,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">${s.portfolio_impact_m:+.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(s.retention_strategy)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _ops_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Self-Pay AR Days","right"),("Self-Pay Coll %","right"),("Charity Care Growth","right"),
            ("Fin Assist Apps","right"),("Settlement %","right"),("Bad Debt Growth","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ar_c = warn if o.self_pay_ar_days >= 90 else (acc if o.self_pay_ar_days >= 70 else pos)
        c_c = warn if o.self_pay_collection_pct <= 0.40 else (acc if o.self_pay_collection_pct <= 0.55 else pos)
        b_c = warn if o.bad_debt_growth_pct >= 0.30 else (acc if o.bad_debt_growth_pct >= 0.18 else pos)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(o.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ar_c};font-weight:700">{o.self_pay_ar_days}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{o.self_pay_collection_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn};font-weight:600">+{o.charity_care_growth_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{o.financial_assistance_apps:,}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{o.average_settlement_pct * 100:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">+{o.bad_debt_growth_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _programs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Program","left"),("Deals","right"),("Members Assisted (K)","right"),("Re-enrolled Medicaid %","right"),
            ("ACA %","right"),("Self-Pay %","right"),("Cost/Member ($)","right"),("Revenue Preserved ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.program)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{p.portfolio_deals}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.members_assisted_k}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.re_enrolled_medicaid_pct * 100:.0f}%""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{p.aca_enrolled_pct * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.self_pay_converted_pct * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.cost_per_member:.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${p.revenue_preserved_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _timelines_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("State","left"),("Unwinding Start","right"),("First Renewals","right"),
            ("Projected End","right"),("Total Disenrolled (K)","right"),("Pace","center"),("Posture","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = _pace_color(t.current_pace)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.state)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(t.unwinding_start)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(t.first_renewals)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(t.projected_end)}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{t.total_disenrolled_k:,}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{p_c};border:1px solid {p_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.current_pace)}</span>""", align="center")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.policy_posture)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_medicaid_unwinding(params: dict = None) -> str:
    from rcm_mc.data_public.medicaid_unwinding import compute_medicaid_unwinding
    r = compute_medicaid_unwinding()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("Deals Exposed", str(r.total_deals_exposed), "", "") +
        ck_kpi_block("Pre-PHE Lives", f"{r.total_medicaid_lives_pre_phe_m:.1f}M", "", "") +
        ck_kpi_block("Disenrolled", f"{r.total_disenrolled_m:.1f}M", "", "") +
        ck_kpi_block("Revenue Impact", f"${r.total_revenue_impact_m:.1f}M", "", "") +
        ck_kpi_block("Back-to-Medicaid Avg", f"{r.avg_coverage_shift_back_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Retention Programs", str(r.active_retention_programs), "", "") +
        ck_kpi_block("States Tracked", str(len(r.states)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    d_chart = _deals_chart(r.deals)
    d_tbl = _deals_table(r.deals)
    s_tbl = _states_table(r.states)
    sh_tbl = _shifts_table(r.shifts)
    o_tbl = _ops_table(r.operational)
    p_tbl = _programs_table(r.programs)
    t_tbl = _timelines_table(r.timelines)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    revenue_preserved = sum(p.revenue_preserved_m for p in r.programs)
    accel_states = sum(1 for t in r.timelines if t.current_pace == "accelerated")
    disenroll_rate = r.total_disenrolled_m / r.total_medicaid_lives_pre_phe_m if r.total_medicaid_lives_pre_phe_m else 0

    page_title = ck_page_title(
        "Medicaid Redetermination / Coverage Unwinding Tracker",
        eyebrow="MEDICAID UNWINDING",
        meta=f"{r.total_deals_exposed} portcos exposed · {r.total_medicaid_lives_pre_phe_m:.1f}M pre-PHE Medicaid lives → {r.total_disenrolled_m:.1f}M disenrolled ({disenroll_rate * 100:.0f}% rate) · ${r.total_revenue_impact_m:.1f}M net revenue impact offset by ${revenue_preserved:.1f}M preserved through {r.active_retention_programs} retention programs",
    )

    value_anchor = ck_value_anchor(
        "Medicaid Unwinding",
        f"{r.total_deals_exposed} deals exposed",
        delta=f"{r.total_disenrolled_m:.1f}M lives disenrolled · {r.avg_coverage_shift_back_pct * 100:.0f}% reshifting to coverage",
        opportunity=f"${abs(r.total_revenue_impact_m):,.1f}M revenue at risk",
        tone="negative",
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Portfolio Deal Impact</div>{d_chart}{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">State-Level Unwinding Activity</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Coverage Shift Analysis</div>{sh_tbl}</div>
  <div style="{cell}"><div style="{h3}">Operational Metrics — Self-Pay + Bad Debt + Charity</div>{o_tbl}</div>
  <div style="{cell}"><div style="{h3}">Retention Programs</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">State-by-State Unwinding Timelines</div>{t_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Medicaid Unwinding Portfolio Summary:</strong> {r.total_disenrolled_m:.1f}M disenrolled from {r.total_medicaid_lives_pre_phe_m:.1f}M pre-PHE Medicaid lives — portfolio net revenue impact ${r.total_revenue_impact_m:.1f}M across {r.total_deals_exposed} portcos.
    Highest-exposure deals: Project Sage (Home Health, $18.5M revenue drag, 28.5K patients lost), Project Redwood (Behavioral, $12.5M, 18.5K), Project Linden (Behavioral, $10.5M, 18.2K).
    Coverage shift pattern: 42% to ACA (subsidized/favorable), 18% to commercial employer ($485/patient lift), 28-45% to self-pay ($650/patient drop), 12% back to Medicaid after outreach.
    Retention programs have preserved ~${revenue_preserved:.1f}M portfolio revenue — back-to-Medicaid re-enrollment ($22.5M preserved) and in-house enrollment assistance ($18.5M) are top performers.
    State dispersion: {accel_states} states accelerated (TX, FL, GA, AZ with high procedural disenrollment); NY, IL, MA slow + pro-beneficiary; CA moderating after initial acceleration.
    Operational pressure: Sage self-pay AR at 115 days / 32.5% collection rate; behavioral portfolio (Redwood, Linden) bad debt growth 35-43% — requires targeted remediation Q2 2026.
  </div>
</div>"""

    return chartis_shell(body, "Medicaid Unwinding", active_nav="/medicaid-unwinding",
        editorial_intro={
            "eyebrow": "MEDICAID UNWINDING",
            "headline": "What the medicaid unwinding page reveals on this deal.",
            "italic_word": "reveals",
        })
