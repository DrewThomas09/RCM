"""Clinical AI / ML Deployment Tracker — /clinical-ai."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _fda_color(s: str) -> str:
    if "cleared" in s.lower(): return P["positive"]
    if "de novo" in s.lower(): return P["positive"]
    if "pending" in s.lower(): return P["warning"]
    if "n/a" in s.lower(): return P["text_dim"]
    return P["text_dim"]


def _stage_color(s: str) -> str:
    return {
        "pilot": P["accent"],
        "evaluation": P["warning"],
        "production": P["positive"],
    }.get(s, P["text_dim"])


def _systems_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Vendor","left"),("Product","left"),("Use Case","left"),
            ("FDA Status","center"),("Clinical Domain","left"),("Deployed","right"),
            ("Sites","right"),("Monthly Cases (K)","right"),("License ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        f_c = _fda_color(s.fda_status)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(s.vendor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};max-width:200px">{_html.escape(s.product)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(s.use_case)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{f_c};font-weight:700">{_html.escape(s.fda_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.clinical_domain)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.deployment_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.sites_deployed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{s.monthly_cases_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.annual_license_m:.2f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _outcomes_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("System","left"),("Deal","left"),("Accuracy","right"),("Sensitivity","right"),
            ("Specificity","right"),("Time Saved (min)","right"),("Revenue ($M)","right"),("Satisfaction","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = pos if o.accuracy_pct >= 0.92 else (acc if o.accuracy_pct >= 0.88 else P["warning"])
        s_c = pos if o.clinician_satisfaction >= 4.5 else (acc if o.clinician_satisfaction >= 4.0 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(o.system)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(o.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{o.accuracy_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{o.sensitivity_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{o.specificity_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{o.time_saved_min_per_case:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${o.revenue_impact_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{o.clinician_satisfaction:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _adoption_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Total Clinicians","right"),("Trained","right"),("Active","right"),
            ("Daily Usage","right"),("Override Rate","right"),("Complaints","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        u_c = pos if a.daily_usage_pct >= 0.85 else (acc if a.daily_usage_pct >= 0.70 else warn)
        o_c = pos if a.override_rate_pct <= 0.08 else (acc if a.override_rate_pct <= 0.15 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(a.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.total_clinicians}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{a.trained_clinicians}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{a.active_users}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{u_c};font-weight:700">{a.daily_usage_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{a.override_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if a.complaint_count > 0 else text_dim}">{a.complaint_count}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _fda_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vendor","left"),("Product","left"),("Type","center"),("K Number","center"),
            ("Cleared","right"),("Intended Use","left"),("Predicate","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.vendor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text}">{_html.escape(f.product)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:700">{_html.escape(f.submission_type)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(f.k_number)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{_html.escape(f.cleared_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(f.intended_use)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.predicate)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _eval_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vendor","left"),("Product","left"),("Stage","center"),("Deals","right"),
            ("Expected Close","right"),("Competitors","left"),("Risk","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(e.evaluation_stage)
        r_c = P["negative"] if "high" in e.risk_assessment.lower() else (P["warning"] if "medium" in e.risk_assessment.lower() else P["text_dim"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.vendor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(e.product)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.evaluation_stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{e.deals_piloting}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(e.expected_close)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(e.competitor_products)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{r_c}">{_html.escape(e.risk_assessment)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _gov_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("AIACE Framework","center"),("Audit Freq","center"),
            ("Bias Monitoring","center"),("Clinical Oversight","center"),("Patient Disclosure","center"),
            ("HIPAA BAA","center"),("Compliance Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    def yn(b):
        c = pos if b else P["warning"]
        return f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c};font-weight:700">{"YES" if b else "NO"}</td>'
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if g.compliance_score >= 9.0 else (acc if g.compliance_score >= 8.5 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(g.deal)}</td>',
            yn(g.aiace_framework),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(g.algorithmic_audit_freq)}</td>',
            yn(g.bias_monitoring),
            yn(g.clinical_oversight_committee),
            yn(g.patient_disclosure),
            yn(g.hipaa_baa),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{g.compliance_score:.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_clinical_ai_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.clinical_ai_tracker import compute_clinical_ai_tracker
    r = compute_clinical_ai_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("AI Systems", str(r.total_systems), "", "") +
        ck_kpi_block("Deals w/ AI", str(r.total_deals_with_ai), "", "") +
        ck_kpi_block("Annual Spend", f"${r.total_annual_spend_m:.1f}M", "", "") +
        ck_kpi_block("Monthly Cases", f"{r.total_cases_monthly_k:,}K", "", "") +
        ck_kpi_block("Avg Adoption", f"{r.avg_adoption_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Accuracy", f"{r.avg_accuracy_pct * 100:.1f}%", "", "") +
        ck_kpi_block("FDA Cleared", str(sum(1 for f in r.fda if "cleared" in f.cleared_date.lower() or "-" in f.cleared_date)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    s_tbl = _systems_table(r.systems)
    o_tbl = _outcomes_table(r.outcomes)
    a_tbl = _adoption_table(r.adoption)
    f_tbl = _fda_table(r.fda)
    e_tbl = _eval_table(r.evaluations)
    g_tbl = _gov_table(r.governance)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_revenue = sum(o.revenue_impact_m for o in r.outcomes)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Clinical AI / ML Deployment Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_systems} AI systems deployed across {r.total_deals_with_ai} portcos · ${r.total_annual_spend_m:.1f}M annual license spend · {r.total_cases_monthly_k:,}K monthly case volume · {r.avg_adoption_pct * 100:.1f}% daily usage · {r.avg_accuracy_pct * 100:.1f}% avg accuracy — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">AI Systems in Production</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Clinical Outcomes & ROI</div>{o_tbl}</div>
  <div style="{cell}"><div style="{h3}">Adoption Metrics</div>{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">FDA Clearances</div>{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Vendor Evaluation Pipeline</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">AI Governance & Compliance</div>{g_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">AI Portfolio Summary:</strong> {r.total_systems} AI systems generate ${total_revenue:.1f}M revenue / workflow impact against ${r.total_annual_spend_m:.1f}M license cost — {total_revenue / r.total_annual_spend_m if r.total_annual_spend_m else 0:.1f}x net ROI.
    Highest-value deployments: Notable Autopilot ($38.5M, Oak), Nuance DAX ($32.0M, Cypress), Enter ML ($28.5M, Oak), Abridge Scribe ($25.5M, Oak) — all ambient scribes + operational ML.
    Radiology AI stack 3 systems (Aidoc ICH + PE, Viz.ai ANEURYSM) covering stroke + PE triage + aneurysm detection — high accuracy (91-95%) and strong time savings (12-18 min/case).
    Adoption distribution: GI Network 94%, RCM SaaS 92%, Radiology 92% top tier; Behavioral Health 52% bottom with 18.5% override rate and 5 complaints — requires UX redesign.
    FDA clearance path: 7 FDA-cleared 510(k), 3 De Novo, 1 pending (Ellipsis Voice) — all deployed systems have regulatory clearance or operational exemption.
    9 active vendor evaluations covering ambient scribes, radiology alternatives, genomics, pathology, scribe assistants — $8M+ incremental spend probable by 2026 year-end.
    Governance: all 8 portcos with AI systems maintain bias monitoring, clinical oversight committees, and HIPAA BAAs; average compliance score 8.9/10.
  </div>
</div>"""

    return chartis_shell(body, "Clinical AI Tracker", active_nav="/clinical-ai")
