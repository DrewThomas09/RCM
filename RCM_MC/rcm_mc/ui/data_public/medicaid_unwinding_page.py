"""Medicaid Redetermination / Coverage Unwinding Tracker — /medicaid-unwinding."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


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
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(d.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{d.pre_phe_medicaid_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{d.current_medicaid_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]};font-weight:700">{d.medicaid_patients_lost_k:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{d.coverage_shift_pct.get("aca", 0) * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{d.coverage_shift_pct.get("commercial_employer", 0) * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">{d.coverage_shift_pct.get("self_pay", 0) * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{d.coverage_shift_pct.get("back_medicaid", 0) * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${d.revenue_impact_m:+.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(d.mitigation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _states_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("State","left"),("Disenrolled (M)","right"),("Pre-PHE (M)","right"),("Disenroll %","right"),
            ("Procedural %","right"),("Gain ACA %","right"),("Back to Medicaid %","right"),("Portfolio Deals","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = warn if s.disenroll_rate_pct >= 0.30 else (acc if s.disenroll_rate_pct >= 0.22 else text_dim)
        pr_c = warn if s.procedural_disenroll_pct >= 0.40 else (acc if s.procedural_disenroll_pct >= 0.28 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.state)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{s.disenrolled_m:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.total_medicaid_pre_phe_m:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{s.disenroll_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pr_c};font-weight:700">{s.procedural_disenroll_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{s.coverage_gain_aca_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{s.back_to_medicaid_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.portfolio_deals}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _shifts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("From","left"),("To","left"),("Members Shifted (M)","right"),
            ("Rev/Patient Δ","right"),("Portfolio Impact ($M)","right"),("Retention Strategy","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if s.revenue_per_patient_delta > 0 else (neg if s.revenue_per_patient_delta < 0 else text_dim)
        p_c = pos if s.portfolio_impact_m > 0 else (neg if s.portfolio_impact_m < 0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.from_coverage)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{_html.escape(s.to_coverage)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{s.members_shifted_m:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">${s.revenue_per_patient_delta:+,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">${s.portfolio_impact_m:+.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(s.retention_strategy)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _ops_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Self-Pay AR Days","right"),("Self-Pay Coll %","right"),("Charity Care Growth","right"),
            ("Fin Assist Apps","right"),("Settlement %","right"),("Bad Debt Growth","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ar_c = warn if o.self_pay_ar_days >= 90 else (acc if o.self_pay_ar_days >= 70 else pos)
        c_c = warn if o.self_pay_collection_pct <= 0.40 else (acc if o.self_pay_collection_pct <= 0.55 else pos)
        b_c = warn if o.bad_debt_growth_pct >= 0.30 else (acc if o.bad_debt_growth_pct >= 0.18 else pos)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(o.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ar_c};font-weight:700">{o.self_pay_ar_days}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{o.self_pay_collection_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn};font-weight:600">+{o.charity_care_growth_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{o.financial_assistance_apps:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{o.average_settlement_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">+{o.bad_debt_growth_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _programs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Program","left"),("Deals","right"),("Members Assisted (K)","right"),("Re-enrolled Medicaid %","right"),
            ("ACA %","right"),("Self-Pay %","right"),("Cost/Member ($)","right"),("Revenue Preserved ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.program)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.portfolio_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.members_assisted_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{p.re_enrolled_medicaid_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.aca_enrolled_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.self_pay_converted_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.cost_per_member:.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.revenue_preserved_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _timelines_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("State","left"),("Unwinding Start","right"),("First Renewals","right"),
            ("Projected End","right"),("Total Disenrolled (K)","right"),("Pace","center"),("Posture","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = _pace_color(t.current_pace)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(t.state)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(t.unwinding_start)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(t.first_renewals)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{_html.escape(t.projected_end)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{t.total_disenrolled_k:,}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{p_c};border:1px solid {p_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.current_pace)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.policy_posture)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Medicaid Redetermination / Coverage Unwinding Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_deals_exposed} portcos exposed · {r.total_medicaid_lives_pre_phe_m:.1f}M pre-PHE Medicaid lives → {r.total_disenrolled_m:.1f}M disenrolled · ${r.total_revenue_impact_m:.1f}M net revenue impact · {r.active_retention_programs} active retention programs — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Portfolio Deal Impact</div>{d_tbl}</div>
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

    return chartis_shell(body, "Medicaid Unwinding", active_nav="/medicaid-unwinding")
