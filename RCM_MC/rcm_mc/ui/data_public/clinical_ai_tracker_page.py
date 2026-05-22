"""Clinical AI / ML Deployment Tracker — /clinical-ai."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_bar_row, ck_value_anchor, ck_scatter


def _outcomes_scatter(items):
    """Quadrant — model accuracy vs revenue impact, so high-accuracy /
    high-value AI systems (upper-right) read straight off the table."""
    import statistics
    pts, ys = [], []
    for o in items:
        x = o.accuracy_pct * 100.0; y = o.revenue_impact_m
        tn = ('positive' if o.accuracy_pct >= 0.92 else 'teal' if o.accuracy_pct >= 0.85 else 'warning')
        pts.append((x, y, o.system, tn)); ys.append(y)
    return ck_scatter(
        pts, x_label='Model accuracy %', y_label='Revenue impact ($M)',
        x_ref=90.0, y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = an AI system · upper-right = high-accuracy + high-value · 90% = clinical-grade line',
    )


def _systems_chart(items) -> str:
    """Lead chart — AI systems ranked by annual license spend (tone by FDA status)."""
    def _tone(st):
        s=(st or "").lower()
        if "clear" in s or "approv" in s: return "positive"
        if "pend" in s or "submit" in s or "investig" in s: return "warning"
        return "teal"
    total = sum(s.annual_license_m for s in items) or 1.0
    rows=[ck_bar_row(s.product, f"${s.annual_license_m:,.1f}M",
          s.annual_license_m/total*100.0, tone=_tone(s.fda_status))
          for s in sorted(items, key=lambda s: s.annual_license_m, reverse=True)]
    return ('<div style="margin-bottom:14px">'+"".join(rows)+
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of total AI license spend '
            '\u00b7 value = annual license ($M) \u00b7 tone = FDA status</div></div>')


_EXPLAINER_CSS = """<style>
.ck-cai-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-cai-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


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
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        f_c = _fda_color(s.fda_status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.deal)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(s.vendor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};max-width:200px">{_html.escape(s.product)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(s.use_case)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{f_c};font-weight:700">{_html.escape(s.fda_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.clinical_domain)}</td>',
            f'{ck_data_cell(f"""{_html.escape(s.deployment_date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.sites_deployed}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.monthly_cases_k}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${s.annual_license_m:.2f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _outcomes_chart(items) -> str:
    """Summary chart — clinical AI systems by revenue impact (tone by accuracy)."""
    def _tone(o):
        if o.accuracy_pct >= 0.92: return "positive"
        if o.accuracy_pct >= 0.85: return "teal"
        return "warning"
    top = sorted(items, key=lambda o: o.revenue_impact_m, reverse=True)
    total = sum(o.revenue_impact_m for o in top) or 1.0
    rows = [ck_bar_row(f"{o.system} · {o.deal}",
            f"${o.revenue_impact_m:,.2f}M · {o.accuracy_pct * 100:.0f}% acc",
            o.revenue_impact_m / total * 100.0, tone=_tone(o)) for o in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of clinical-AI revenue impact '
            '· value = revenue ($M) + accuracy · tone = model accuracy</div></div>')


def _outcomes_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("System","left"),("Deal","left"),("Accuracy","right"),("Sensitivity","right"),
            ("Specificity","right"),("Time Saved (min)","right"),("Revenue ($M)","right"),("Satisfaction","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = pos if o.accuracy_pct >= 0.92 else (acc if o.accuracy_pct >= 0.88 else P["warning"])
        s_c = pos if o.clinician_satisfaction >= 4.5 else (acc if o.clinician_satisfaction >= 4.0 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(o.system)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(o.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{o.accuracy_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{o.sensitivity_pct * 100:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{o.specificity_pct * 100:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{o.time_saved_min_per_case:.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${o.revenue_impact_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{o.clinician_satisfaction:.1f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _adoption_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Total Clinicians","right"),("Trained","right"),("Active","right"),
            ("Daily Usage","right"),("Override Rate","right"),("Complaints","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        u_c = pos if a.daily_usage_pct >= 0.85 else (acc if a.daily_usage_pct >= 0.70 else warn)
        o_c = pos if a.override_rate_pct <= 0.08 else (acc if a.override_rate_pct <= 0.15 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.deal)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{a.total_clinicians}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{a.trained_clinicians}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{a.active_users}""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{u_c};font-weight:700">{a.daily_usage_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{a.override_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if a.complaint_count > 0 else text_dim}">{a.complaint_count}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _fda_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vendor","left"),("Product","left"),("Type","center"),("K Number","center"),
            ("Cleared","right"),("Intended Use","left"),("Predicate","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(f.vendor)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text}">{_html.escape(f.product)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:700">{_html.escape(f.submission_type)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(f.k_number)}</td>',
            f'{ck_data_cell(f"""{_html.escape(f.cleared_date)}""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(f.intended_use)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.predicate)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _eval_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vendor","left"),("Product","left"),("Stage","center"),("Deals","right"),
            ("Expected Close","right"),("Competitors","left"),("Risk","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(e.evaluation_stage)
        r_c = P["negative"] if "high" in e.risk_assessment.lower() else (P["warning"] if "medium" in e.risk_assessment.lower() else P["text_dim"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.vendor)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(e.product)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.evaluation_stage)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{e.deals_piloting}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{_html.escape(e.expected_close)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(e.competitor_products)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{r_c}">{_html.escape(e.risk_assessment)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _gov_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("AIACE Framework","center"),("Audit Freq","center"),
            ("Bias Monitoring","center"),("Clinical Oversight","center"),("Patient Disclosure","center"),
            ("HIPAA BAA","center"),("Compliance Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    def yn(b):
        c = pos if b else P["warning"]
        return f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c};font-weight:700">{"YES" if b else "NO"}</td>'
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if g.compliance_score >= 9.0 else (acc if g.compliance_score >= 8.5 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(g.deal)}""", mono=True, weight=700)}',
            yn(g.aiace_framework),
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(g.algorithmic_audit_freq)}</td>',
            yn(g.bias_monitoring),
            yn(g.clinical_oversight_committee),
            yn(g.patient_disclosure),
            yn(g.hipaa_baa),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{g.compliance_score:.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    s_chart = _systems_chart(r.systems)
    s_tbl = _systems_table(r.systems)
    value_anchor = ck_value_anchor(
        "Clinical AI",
        f"${r.total_annual_spend_m:,.1f}M AI spend",
        delta=f"{r.total_systems} systems \u00b7 {r.avg_accuracy_pct * 100:.0f}% avg accuracy \u00b7 {r.avg_adoption_pct * 100:.0f}% adoption \u00b7 {r.total_cases_monthly_k:,}K cases/mo",
        tone="teal",
    )
    o_tbl = _outcomes_table(r.outcomes)
    o_chart = _outcomes_chart(r.outcomes)
    o_scatter = _outcomes_scatter(r.outcomes)
    a_tbl = _adoption_table(r.adoption)
    f_tbl = _fda_table(r.fda)
    e_tbl = _eval_table(r.evaluations)
    g_tbl = _gov_table(r.governance)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_revenue = sum(o.revenue_impact_m for o in r.outcomes)
    page_title = ck_page_title(
        "Clinical AI / ML Deployment Tracker",
        eyebrow="CLINICAL AI TRACKER",
        meta=(
            f"{r.total_systems} AI systems · {r.total_deals_with_ai} portcos · "
            f"${r.total_annual_spend_m:.1f}M license spend · {r.corpus_deal_count:,} corpus deals"
        ),
    )
    cai_explainer = (
        '<p class="ck-cai-explainer">'
        "<em>What the clinical AI tracker reveals on this deal.</em> "
        "AI systems in production, clinical outcomes and ROI, adoption metrics, "
        "FDA clearances, vendor evaluation pipeline, and governance compliance."
        "</p>"
    )
    body = page_title + ck_illustrative_note("figures") + cai_explainer + f"""
<div class="ck-page-wrap">
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">AI Systems in Production</div>{s_chart}{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Clinical Outcomes & ROI</div>{o_chart}{o_scatter}{o_tbl}</div>
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

    return chartis_shell(body, "Clinical AI Tracker", active_nav="/clinical-ai",
        extra_css=_EXPLAINER_CSS)
