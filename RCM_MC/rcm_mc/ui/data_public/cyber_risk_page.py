"""Cyber Risk / HIPAA Scorecard — /cyber-risk."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _domains_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Domain","left"),("Maturity","right"),("Benchmark","right"),("Gap","right"),
            ("NIST Tier","center"),("Last Audit","left"),("Findings","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gap = d.maturity_score - d.industry_benchmark
        m_c = pos if d.maturity_score >= 80 else (warn if d.maturity_score >= 65 else neg)
        g_c = pos if gap >= 0 else neg
        f_c = neg if d.findings_count >= 7 else (warn if d.findings_count >= 4 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.domain)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{d.maturity_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.industry_benchmark}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:600">{gap:+d}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.nist_csf_tier)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(d.last_audit_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{f_c};font-weight:600">{d.findings_count}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _incidents_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Date","left"),("Incident Type","left"),("Scope","left"),("Records","right"),
            ("HHS Reportable","center"),("Cost ($M)","right"),("Status","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, inc in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        hhs_c = neg if inc.hhs_reportable else pos
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:700">{_html.escape(inc.date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(inc.incident_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(inc.scope)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{inc.records_affected:,}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{hhs_c};font-weight:700">{"YES" if inc.hhs_reportable else "NO"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">${inc.remediation_cost_mm:,.3f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(inc.status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _ransomware_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Capability","left"),("Maturity","center"),("RTO (hr)","right"),("RPO (hr)","right"),
            ("Last Tabletop","left"),("Gap","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    m_c = {"strong": pos, "moderate": warn, "weak": neg}
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        mc = m_c.get(r.maturity, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.capability)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{mc};border:1px solid {mc};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.maturity)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.rto_hours}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.rpo_hours}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(r.last_tabletop)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.gap_description)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _threats_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Threat Vector","left"),("Probability","center"),("Financial Impact ($M)","right"),
            ("Industry Incidence","right"),("Mitigation","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    p_c = {"very high": neg, "high": neg, "medium": warn, "low": text_dim}
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = p_c.get(t.probability_ltm, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(t.vector)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.probability_ltm)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${t.financial_impact_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{t.industry_incidence_pct * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(t.mitigation_status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _compliance_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Framework","left"),("Scope","left"),("Status","left"),("Coverage","right"),
            ("Last Assessment","left"),("Remediation ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if ("compliant" in c.status or "passed" in c.status or "certified" in c.status) else (P["warning"] if "aligned" in c.status else text_dim)
        cov_c = pos if c.coverage_pct >= 0.95 else (P["warning"] if c.coverage_pct >= 0.80 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.framework)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.scope)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{s_c}">{_html.escape(c.status)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cov_c};font-weight:700">{c.coverage_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(c.last_assessment)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if c.remediation_cost_mm > 0 else text_dim}">${c.remediation_cost_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vendors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Third Party","left"),("Access Scope","left"),("BAA","center"),
            ("SOC 2 Status","left"),("Last Review","left"),("Risk Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = neg if v.risk_score >= 50 else (warn if v.risk_score >= 30 else text_dim)
        s_c = pos if "Type II current" in v.soc2_status else (warn if "Type I" in v.soc2_status else text_dim)
        b_c = pos if "current" in v.bah_coverage else warn
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(v.third_party)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(v.access_scope)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{b_c};font-weight:700">{_html.escape(v.bah_coverage)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{s_c}">{_html.escape(v.soc2_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(v.last_review)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{v.risk_score}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_cyber_risk(params: dict = None) -> str:
    from rcm_mc.data_public.cyber_risk import compute_cyber_risk
    r = compute_cyber_risk()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    tier_c = pos if r.risk_tier == "strong" else (acc if r.risk_tier == "adequate" else (warn if r.risk_tier == "developing" else neg))

    kpi_strip = (
        ck_kpi_block("Cyber Score", f"{r.overall_cyber_score}/100", "", "") +
        ck_kpi_block("Risk Tier", r.risk_tier.upper()[:14], "", "") +
        ck_kpi_block("Records in Scope", f"{r.total_records_in_scope:,}", "", "") +
        ck_kpi_block("Insurance", f"${r.cyber_insurance_coverage_mm:,.0f}M", "", "") +
        ck_kpi_block("Annual Spend", f"${r.annual_cyber_spend_mm:,.1f}M", "", "") +
        ck_kpi_block("Control Domains", str(len(r.domains)), "", "") +
        ck_kpi_block("Vendors at Risk", str(sum(1 for v in r.vendors if v.risk_score >= 50)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    d_tbl = _domains_table(r.domains)
    i_tbl = _incidents_table(r.incidents)
    rw_tbl = _ransomware_table(r.ransomware)
    t_tbl = _threats_table(r.threats)
    c_tbl = _compliance_table(r.compliance)
    v_tbl = _vendors_table(r.vendors)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_rem = sum(c.remediation_cost_mm for c in r.compliance)
    hhs_incidents = sum(1 for inc in r.incidents if inc.hhs_reportable)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Cybersecurity / HIPAA Risk Scorecard</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">12-domain control maturity · incident history · ransomware preparedness · threat vectors · compliance frameworks · 3P vendor risk — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {tier_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Cyber Posture</div>
    <div style="color:{tier_c};font-weight:700;font-size:14px">Score {r.overall_cyber_score}/100 · Tier {_html.escape(r.risk_tier.upper())} · {r.total_records_in_scope:,} PHI records in scope</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">${r.cyber_insurance_coverage_mm:,.0f}M insurance tower · ${r.annual_cyber_spend_mm:,.1f}M annual spend · {hhs_incidents} HHS-reportable incidents LTM</div>
  </div>
  <div style="{cell}"><div style="{h3}">Control Domain Maturity vs Industry Benchmark</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Incident History (LTM)</div>{i_tbl}</div>
  <div style="{cell}"><div style="{h3}">Ransomware Preparedness</div>{rw_tbl}</div>
  <div style="{cell}"><div style="{h3}">Threat Vector Exposure</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Compliance Framework Coverage</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Third-Party / Vendor Exposure</div>{v_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Cyber Risk Thesis:</strong> Overall score {r.overall_cyber_score}/100 (tier: {_html.escape(r.risk_tier)}).
    Strong controls on endpoint, data protection, and training; underinvested in SOC/SIEM, BCP/DR, and third-party risk management.
    Ransomware readiness is strong — immutable backups, EDR everywhere, $50M cyber tower. Post-Change Healthcare (Feb 2024), the sector-wide ransomware impact benchmark is $22B — platform exposure proportional to PHI footprint and vendor density.
    Most material third-party risk: offshore RCM BPO (SOC 2 Type I only — upgrade required) and Salesforce Health Cloud (high-access PHI scope).
    Compliance posture solid — HIPAA, HITRUST r2, SOC 2 Type II, PCI-DSS, ISO 27001 all current.
    Remediation budget required ${total_rem:,.2f}M to close gaps over next 6-9 months.
  </div>
</div>"""

    return chartis_shell(body, "Cyber Risk", active_nav="/cyber-risk")
