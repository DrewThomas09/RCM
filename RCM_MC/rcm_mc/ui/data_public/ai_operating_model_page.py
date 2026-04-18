"""AI / ML Operating Model — /ai-operating-model."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _init_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Use Case","left"),("Category","center"),("Stage","center"),("Spend ($M)","right"),
            ("Savings ($M)","right"),("Rev Lift ($M)","right"),("Net ROI","right"),
            ("Adoption","right"),("P2P (mo)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    stg_c = {"production": pos, "pilot": acc, "concept": text_dim}
    for i, it in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stg_c.get(it.deployment_stage, text_dim)
        roi_c = pos if it.net_roi_pct >= 3.0 else (acc if it.net_roi_pct >= 1.5 else warn)
        adopt_c = pos if it.adoption_pct >= 0.70 else (acc if it.adoption_pct >= 0.45 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(it.use_case)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(it.category)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(it.deployment_stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${it.annual_spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${it.annual_savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${it.annual_revenue_lift_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{roi_c};font-weight:700">{it.net_roi_pct:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{adopt_c};font-weight:700">{it.adoption_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{it.pilot_to_prod_months}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vendors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Vendor","left"),("Category","left"),("Contract ($M)","right"),("Integration","left"),
            ("Clinical Accuracy","right"),("User NPS","right"),("Tier","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    tier_c = {"platinum": pos, "gold": acc, "silver": text_dim, "divested": neg}
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = tier_c.get(v.retention_tier, text_dim)
        a_c = pos if v.clinical_accuracy_pct >= 0.92 else (acc if v.clinical_accuracy_pct >= 0.85 else text_dim)
        nps_c = pos if v.user_nps >= 75 else (acc if v.user_nps >= 65 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(v.vendor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(v.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">${v.annual_contract_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.integration_depth)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{v.clinical_accuracy_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{nps_c};font-weight:700">{v.user_nps}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(v.retention_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _governance_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Model","left"),("Use Case","left"),("FDA Class","center"),("Bias Audit","left"),
            ("Drift Monitoring","left"),("Last Validation","left"),("Risk Tier","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    r_c = {"low": pos, "medium": warn, "high": neg}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = r_c.get(g.risk_tier, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(g.model)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(g.use_case)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(g.fda_class)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(g.bias_audit_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(g.drift_monitoring)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(g.last_validation_date)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.risk_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _roi_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Bucket","left"),("Spend ($M)","right"),("Savings ($M)","right"),("ROI Multiple","right"),
            ("Payback (mo)","right"),("Strategic Value","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sv_c = {"high": pos, "medium": acc, "low": text_dim}
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        svc = sv_c.get(b.strategic_value, text_dim)
        roi_c = pos if b.roi_multiple >= 3.5 else (acc if b.roi_multiple >= 2.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.bucket)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${b.spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${b.savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{roi_c};font-weight:700">{b.roi_multiple:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{b.payback_months}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{svc};border:1px solid {svc};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.strategic_value)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _regulation_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; pos = P["positive"]
    cols = [("Regulation","left"),("Applicability","left"),("Compliance","left"),
            ("Gap","left"),("Remediation ($M)","right"),("Deadline","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if "compliant" in r.current_compliance or "passed" in r.current_compliance else (P["warning"] if "implementing" in r.current_compliance or "monitoring" in r.current_compliance else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.regulation)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.applicability)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{c_c}">{_html.escape(r.current_compliance)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.gap_description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if r.remediation_cost_mm > 0 else text_dim}">${r.remediation_cost_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{P["accent"]}">{_html.escape(r.deadline)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    v_tbl = _vendors_table(r.vendors)
    g_tbl = _governance_table(r.governance)
    roi_tbl = _roi_table(r.roi_buckets)
    reg_tbl = _regulation_table(r.regulation)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_reg_cost = sum(rr.remediation_cost_mm for rr in r.regulation)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">AI / ML Operating Model</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">AI initiative portfolio · vendor landscape · model governance · ROI by bucket · regulatory exposure — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {gov_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">AI Portfolio Health</div>
    <div style="color:{gov_c};font-weight:700;font-size:14px">Blended ROI {r.blended_roi_pct:.1f}x · {r.initiatives_in_prod} initiatives in production · Governance posture {_html.escape(r.governance_risk_tier.upper())}</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Net annual value ${r.total_annual_savings_mm + r.total_revenue_lift_mm - r.total_annual_ai_spend_mm:,.1f}M · Regulatory remediation ${total_reg_cost:,.2f}M outstanding</div>
  </div>
  <div style="{cell}"><div style="{h3}">AI Initiative Portfolio</div>{i_tbl}</div>
  <div style="{cell}"><div style="{h3}">Vendor Landscape &amp; Contract Economics</div>{v_tbl}</div>
  <div style="{cell}"><div style="{h3}">Model Governance &amp; Validation</div>{g_tbl}</div>
  <div style="{cell}"><div style="{h3}">ROI by Bucket — Strategic Value</div>{roi_tbl}</div>
  <div style="{cell}"><div style="{h3}">Regulatory Exposure — FDA SaMD, HHS, AB 3030, HTI-1</div>{reg_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">AI Operating Thesis:</strong> ${r.total_annual_ai_spend_mm:,.1f}M annual spend returns ${r.total_annual_savings_mm + r.total_revenue_lift_mm:,.1f}M value at {r.blended_roi_pct:.1f}x ROI.
    Highest-ROI initiatives: RCM claim scrubbing (6.59x), CDI AI (6.14x), ambient scribing (4.00x) — all production-deployed with 72-88% adoption.
    Radiology AI ROI (1.92x) is modest given infrastructure dependency; pilots in dermatology and LLM navigation showing promise but not yet validated.
    Model governance tier is <strong style="color:{gov_c}">{_html.escape(r.governance_risk_tier)}</strong> — dermatology image model pilot and LLM-based prior auth letter generation flagged for accelerated validation.
    Regulatory horizon: FDA SaMD Class II clearance for 2 pending models and California AB 3030 patient disclosure compliance by Q2 2026.
  </div>
</div>"""

    return chartis_shell(body, "AI Operating Model", active_nav="/ai-operating-model")
