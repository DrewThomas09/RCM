"""Cyber Risk / HIPAA Scorecard — /cyber-risk."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_data_cell, ck_kpi_block, ck_page_title, ck_illustrative_note, ck_value_anchor
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel


def _domains_chart(items) -> str:
    """Lead chart for the control-domain table — maturity score per
    domain, ranked, so a partner reads the strongest/weakest controls
    before scanning the dataset. Bar width is absolute maturity (0-100);
    tone tracks the table's tier coloring (>=80 strong, >=65 developing,
    else lagging); the value label carries the signed gap to the
    industry benchmark so the "vs benchmark" read is at-a-glance.
    """
    ranked = sorted(items, key=lambda d: d.maturity_score, reverse=True)
    rows = []
    for d in ranked:
        tone = ("positive" if d.maturity_score >= 80
                else "warning" if d.maturity_score >= 65 else "negative")
        gap = d.maturity_score - d.industry_benchmark
        rows.append(ck_bar_row(
            d.domain,
            f"{gap:+d}",
            float(d.maturity_score),
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = control maturity (0–100) · value = gap vs industry '
        'benchmark · % = maturity score</div>'
        '</div>'
    )


def _domains_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Domain","left"),("Maturity","right"),("Benchmark","right"),("Gap","right"),
            ("NIST Tier","center"),("Last Audit","left"),("Findings","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gap = d.maturity_score - d.industry_benchmark
        m_c = pos if d.maturity_score >= 80 else (warn if d.maturity_score >= 65 else neg)
        g_c = pos if gap >= 0 else neg
        f_c = neg if d.findings_count >= 7 else (warn if d.findings_count >= 4 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.domain)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{d.maturity_score}</td>',
            f'{ck_data_cell(f"""{d.industry_benchmark}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:600">{gap:+d}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.nist_csf_tier)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(d.last_audit_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{f_c};font-weight:600">{d.findings_count}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _incidents_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Date","left"),("Incident Type","left"),("Scope","left"),("Records","right"),
            ("HHS Reportable","center"),("Cost ($M)","right"),("Status","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, inc in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        hhs_c = neg if inc.hhs_reportable else pos
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:700">{_html.escape(inc.date)}</td>',
            f'{ck_data_cell(f"""{_html.escape(inc.incident_type)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(inc.scope)}</td>',
            f'{ck_data_cell(f"""{inc.records_affected:,}""", align="right", mono=True)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{hhs_c};font-weight:700">{"YES" if inc.hhs_reportable else "NO"}</td>',
            f'{ck_data_cell(f"""${inc.remediation_cost_mm:,.3f}""", align="right", mono=True, tone="neg", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(inc.status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _ransomware_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Capability","left"),("Maturity","center"),("RTO (hr)","right"),("RPO (hr)","right"),
            ("Last Tabletop","left"),("Gap","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    m_c = {"strong": pos, "moderate": warn, "weak": neg}
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        mc = m_c.get(r.maturity, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.capability)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{mc};border:1px solid {mc};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.maturity)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{r.rto_hours}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{r.rpo_hours}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(r.last_tabletop)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.gap_description)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _threats_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Threat Vector","left"),("Probability","center"),("Financial Impact ($M)","right"),
            ("Industry Incidence","right"),("Mitigation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    p_c = {"very high": neg, "high": neg, "medium": warn, "low": text_dim}
    _bar_max = max((t.financial_impact_mm for t in items), default=1.0) or 1.0
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = p_c.get(t.probability_ltm, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.vector)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.probability_ltm)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${t.financial_impact_mm:,.2f}""", align="right", mono=True, tone="neg", weight=700, bar=t.financial_impact_mm / _bar_max * 100)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{t.industry_incidence_pct * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(t.mitigation_status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _compliance_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Framework","left"),("Scope","left"),("Status","left"),("Coverage","right"),
            ("Last Assessment","left"),("Remediation ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if ("compliant" in c.status or "passed" in c.status or "certified" in c.status) else (P["warning"] if "aligned" in c.status else text_dim)
        cov_c = pos if c.coverage_pct >= 0.95 else (P["warning"] if c.coverage_pct >= 0.80 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.framework)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.scope)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{s_c}">{_html.escape(c.status)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cov_c};font-weight:700">{c.coverage_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(c.last_assessment)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if c.remediation_cost_mm > 0 else text_dim}">${c.remediation_cost_mm:,.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vendors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Third Party","left"),("Access Scope","left"),("BAA","center"),
            ("SOC 2 Status","left"),("Last Review","left"),("Risk Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = neg if v.risk_score >= 50 else (warn if v.risk_score >= 30 else text_dim)
        s_c = pos if "Type II current" in v.soc2_status else (warn if "Type I" in v.soc2_status else text_dim)
        b_c = pos if "current" in v.bah_coverage else warn
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.third_party)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(v.access_scope)}""", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{b_c};font-weight:700">{_html.escape(v.bah_coverage)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{s_c}">{_html.escape(v.soc2_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(v.last_review)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{v.risk_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_cyber_risk(params: dict = None) -> str:
    from rcm_mc.data_public.cyber_risk import compute_cyber_risk
    r = compute_cyber_risk()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

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

    d_chart = _domains_chart(r.domains)
    d_tbl = _domains_table(r.domains)
    i_tbl = _incidents_table(r.incidents)
    rw_tbl = _ransomware_table(r.ransomware)
    t_tbl = _threats_table(r.threats)
    c_tbl = _compliance_table(r.compliance)
    v_tbl = _vendors_table(r.vendors)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_rem = sum(c.remediation_cost_mm for c in r.compliance)
    _va_tone = {"strong": "positive", "adequate": "teal",
                "developing": "warning"}.get(r.risk_tier, "negative")
    _avg_gap = (
        sum(d.maturity_score - d.industry_benchmark for d in r.domains)
        / len(r.domains)
    ) if r.domains else 0.0
    value_anchor = ck_value_anchor(
        "Cyber Posture",
        f"{r.overall_cyber_score}/100",
        delta=f"{_avg_gap:+.0f} pts vs industry avg · tier {r.risk_tier.upper()}",
        opportunity=f"${total_rem:,.1f}M to close gaps",
        target="Tier 'strong'",
        tone=_va_tone,
    )
    # B11 sweep batch 2 PR 8/10 — bespoke .ck-page-h1 → ck_page_title.
    # Cybersecurity scorecard page. Pre-fix sub-line described what the
    # page COVERS (12-domain maturity, incidents, ransomware, threats,
    # compliance, vendors) — useful as a TOC, but doesn't read at-a-
    # glance for a partner who already knows what the page is.
    # Replaced with score + risk tier + records-in-scope (the
    # quantitative read on cyber risk magnitude) which is what
    # partners scanning the page actually want to see.
    # 2026-05-30 audit P5 editorial: HIPAA is one of the frameworks
    # the scorecard tracks (alongside NIST CSF, HITRUST, SOC 2).
    # "Cybersecurity Risk Scorecard" is the broader, accurate header;
    # framework breakdowns continue to appear in the body tables.
    page_title = ck_page_title(
        "Cybersecurity Risk Scorecard",
        eyebrow="CYBER RISK",
        meta=(
            f"cyber score {r.overall_cyber_score}/100 · "
            f"risk tier {r.risk_tier.upper()} · "
            f"{r.total_records_in_scope:,} records in scope · "
            f"${r.cyber_insurance_coverage_mm:,.0f}M insurance"
        ),
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {data_required_panel(P, title="Cyber Risk", needed=[("control","control / framework item"),("framework","NIST / HITRUST / SOC2"),("status","implemented / partial / none"),("last_tested","last tested (YYYY-MM-DD)"),("owner","owner")], template="cyber_controls_template.csv", request_from="CISO / IT security", activates="control-framework coverage + gap assessment", guide_hint="What cyber-controls data do I need to upload?")}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Control Domain Maturity vs Industry Benchmark</div>{d_chart}{d_tbl}</div>
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

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Cyber Risk", active_nav="/cyber-risk",
        editorial_intro={
            "eyebrow": "CYBER RISK",
            "headline": "What the cyber risk page reveals on this deal.",
            "italic_word": "reveals",
        })
