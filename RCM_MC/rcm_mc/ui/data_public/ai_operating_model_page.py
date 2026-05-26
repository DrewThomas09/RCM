"""AI / ML Operating Model — /ai-operating-model."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_bar_row
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel

_EXPLAINER_CSS = """<style>
.ck-aim-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-aim-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


def _init_chart(items) -> str:
    """Lead chart — AI initiatives ranked by annual savings (tone by stage/ROI)."""
    def _tone(it):
        st = (it.deployment_stage or "").lower()
        if st == "production" and it.net_roi_pct >= 3.0: return "positive"
        if st == "production": return "teal"
        if st == "pilot": return "warning"
        return "navy"
    top = sorted(items, key=lambda it: it.annual_savings_mm, reverse=True)
    total = sum(it.annual_savings_mm for it in top) or 1.0
    rows = [ck_bar_row(f"{it.use_case} · {it.category}", f"${it.annual_savings_mm:,.2f}M",
            it.annual_savings_mm / total * 100.0, tone=_tone(it)) for it in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of annual AI savings '
            '· value = savings ($M) · tone = deployment stage / ROI</div></div>')


def _init_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Use Case","left"),("Category","center"),("Stage","center"),("Spend ($M)","right"),
            ("Savings ($M)","right"),("Rev Lift ($M)","right"),("Net ROI","right"),
            ("Adoption","right"),("P2P (mo)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    stg_c = {"production": pos, "pilot": acc, "concept": text_dim}
    for i, it in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stg_c.get(it.deployment_stage, text_dim)
        roi_c = pos if it.net_roi_pct >= 3.0 else (acc if it.net_roi_pct >= 1.5 else warn)
        adopt_c = pos if it.adoption_pct >= 0.70 else (acc if it.adoption_pct >= 0.45 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(it.use_case)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(it.category)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(it.deployment_stage)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${it.annual_spend_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""${it.annual_savings_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${it.annual_revenue_lift_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{roi_c};font-weight:700">{it.net_roi_pct:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{adopt_c};font-weight:700">{it.adoption_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{it.pilot_to_prod_months}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vendors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Vendor","left"),("Category","left"),("Contract ($M)","right"),("Integration","left"),
            ("Clinical Accuracy","right"),("User NPS","right"),("Tier","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    tier_c = {"platinum": pos, "gold": acc, "silver": text_dim, "divested": neg}
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = tier_c.get(v.retention_tier, text_dim)
        a_c = pos if v.clinical_accuracy_pct >= 0.92 else (acc if v.clinical_accuracy_pct >= 0.85 else text_dim)
        nps_c = pos if v.user_nps >= 75 else (acc if v.user_nps >= 65 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.vendor)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(v.category)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${v.annual_contract_mm:,.2f}""", align="right", mono=True, tone="neg", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.integration_depth)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{v.clinical_accuracy_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{nps_c};font-weight:700">{v.user_nps}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(v.retention_tier)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _governance_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Model","left"),("Use Case","left"),("FDA Class","center"),("Bias Audit","left"),
            ("Drift Monitoring","left"),("Last Validation","left"),("Risk Tier","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    r_c = {"low": pos, "medium": warn, "high": neg}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = r_c.get(g.risk_tier, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(g.model)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(g.use_case)}""", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(g.fda_class)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(g.bias_audit_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(g.drift_monitoring)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(g.last_validation_date)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.risk_tier)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _roi_chart(items) -> str:
    """Summary chart — strategic-value buckets ranked by savings (tone by ROI multiple)."""
    def _tone(b):
        if b.roi_multiple >= 3.5: return "positive"
        if b.roi_multiple >= 2.0: return "teal"
        return "warning"
    top = sorted(items, key=lambda b: b.savings_mm, reverse=True)
    total = sum(b.savings_mm for b in top) or 1.0
    rows = [ck_bar_row(f"{b.bucket}", f"${b.savings_mm:,.2f}M ({b.roi_multiple:.2f}x)",
            b.savings_mm / total * 100.0, tone=_tone(b)) for b in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of AI savings by value bucket '
            '· value = savings ($M) + ROI · tone = ROI multiple</div></div>')


def _roi_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Bucket","left"),("Spend ($M)","right"),("Savings ($M)","right"),("ROI Multiple","right"),
            ("Payback (mo)","right"),("Strategic Value","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    sv_c = {"high": pos, "medium": acc, "low": text_dim}
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        svc = sv_c.get(b.strategic_value, text_dim)
        roi_c = pos if b.roi_multiple >= 3.5 else (acc if b.roi_multiple >= 2.0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.bucket)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${b.spend_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${b.savings_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{roi_c};font-weight:700">{b.roi_multiple:.2f}x</td>',
            f'{ck_data_cell(f"""{b.payback_months}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{svc};border:1px solid {svc};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.strategic_value)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _regulation_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; pos = P["positive"]
    cols = [("Regulation","left"),("Applicability","left"),("Compliance","left"),
            ("Gap","left"),("Remediation ($M)","right"),("Deadline","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if "compliant" in r.current_compliance or "passed" in r.current_compliance else (P["warning"] if "implementing" in r.current_compliance or "monitoring" in r.current_compliance else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.regulation)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.applicability)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{c_c}">{_html.escape(r.current_compliance)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.gap_description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if r.remediation_cost_mm > 0 else text_dim}">${r.remediation_cost_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{P["accent"]}">{_html.escape(r.deadline)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_ai_operating_model(params: dict = None) -> str:
    from rcm_mc.data_public.ai_operating_model import compute_ai_operating_model
    r = compute_ai_operating_model()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    gov_c = pos if r.governance_risk_tier == "well-governed" else (warn if r.governance_risk_tier == "moderate" else neg)

    kpi_strip = (
        ck_kpi_block("Annual AI Spend", f"${r.total_annual_ai_spend_mm:,.1f}M", "", "") +
        ck_kpi_block("Annual Savings", f"${r.total_annual_savings_mm:,.1f}M", "", "") +
        ck_kpi_block("Revenue Lift", f"${r.total_revenue_lift_mm:,.1f}M", "", "") +
        ck_kpi_block("Blended ROI", f"{r.blended_roi_pct:.1f}x", "", "") +
        ck_kpi_block("In Production", f"{r.initiatives_in_prod}/{len(r.initiatives)}", "", "") +
        ck_kpi_block("Governance", r.governance_risk_tier.upper()[:14], "", "") +
        ck_kpi_block("Vendors", str(len(r.vendors)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    i_tbl = _init_table(r.initiatives)
    i_chart = _init_chart(r.initiatives)
    v_tbl = _vendors_table(r.vendors)
    g_tbl = _governance_table(r.governance)
    roi_tbl = _roi_table(r.roi_buckets)
    roi_chart = _roi_chart(r.roi_buckets)
    reg_tbl = _regulation_table(r.regulation)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_reg_cost = sum(rr.remediation_cost_mm for rr in r.regulation)
    page_title = ck_page_title(
        "AI Operating Model",
        eyebrow="AI OPERATING MODEL",
        meta=f"{r.corpus_deal_count:,} corpus deals · {r.initiatives_in_prod} initiatives in production · governance {_html.escape(r.governance_risk_tier)}",
    )
    aim_explainer = (
        '<p class="ck-aim-explainer">'
        "<em>AI initiative portfolio, vendor landscape, model governance.</em> "
        "ROI by bucket and regulatory exposure — what the AI operating "
        "model reveals on this deal."
        "</p>"
    )
    body = page_title + data_required_panel(P, title="AI Operating Model", needed=[("use_case","AI use-case"),("function","function"),("adoption_status","pilot / scaled / none"),("roi_estimate","ROI $/yr"),("risk_level","high / med / low")], template="ai_operating_model_template.csv", request_from="CIO / digital transformation lead", activates="AI use-case adoption + ROI + risk tracking", guide_hint="What AI operating-model data do I need to upload?") + ck_illustrative_note("figures") + aim_explainer + f"""
<div class="ck-page-wrap">
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {gov_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">AI Portfolio Health</div>
    <div style="color:{gov_c};font-weight:700;font-size:14px">Blended ROI {r.blended_roi_pct:.1f}x · {r.initiatives_in_prod} initiatives in production · Governance posture {_html.escape(r.governance_risk_tier.upper())}</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Net annual value ${r.total_annual_savings_mm + r.total_revenue_lift_mm - r.total_annual_ai_spend_mm:,.1f}M · Regulatory remediation ${total_reg_cost:,.2f}M outstanding</div>
  </div>
  <div style="{cell}"><div style="{h3}">AI Initiative Portfolio</div>{i_chart}{i_tbl}</div>
  <div style="{cell}"><div style="{h3}">Vendor Landscape &amp; Contract Economics</div>{v_tbl}</div>
  <div style="{cell}"><div style="{h3}">Model Governance &amp; Validation</div>{g_tbl}</div>
  <div style="{cell}"><div style="{h3}">ROI by Bucket — Strategic Value</div>{roi_chart}{roi_tbl}</div>
  <div style="{cell}"><div style="{h3}">Regulatory Exposure — FDA SaMD, HHS, AB 3030, HTI-1</div>{reg_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">AI Operating Thesis:</strong> ${r.total_annual_ai_spend_mm:,.1f}M annual spend returns ${r.total_annual_savings_mm + r.total_revenue_lift_mm:,.1f}M value at {r.blended_roi_pct:.1f}x ROI.
    Highest-ROI initiatives: RCM claim scrubbing (6.59x), CDI AI (6.14x), ambient scribing (4.00x) — all production-deployed with 72-88% adoption.
    Radiology AI ROI (1.92x) is modest given infrastructure dependency; pilots in dermatology and LLM navigation showing promise but not yet validated.
    Model governance tier is <strong style="color:{gov_c}">{_html.escape(r.governance_risk_tier)}</strong> — dermatology image model pilot and LLM-based prior auth letter generation flagged for accelerated validation.
    Regulatory horizon: FDA SaMD Class II clearance for 2 pending models and California AB 3030 patient disclosure compliance by Q2 2026.
  </div>
</div>"""

    return chartis_shell(body, "AI Operating Model", active_nav="/ai-operating-model",
        extra_css=_EXPLAINER_CSS)
