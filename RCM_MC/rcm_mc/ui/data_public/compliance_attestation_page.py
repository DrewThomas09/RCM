"""Compliance Attestation / Security Posture Tracker — /compliance-attestation."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_data_cell, ck_kpi_block, ck_page_title, ck_illustrative_note, ck_bar_row


def _sev_color(s: str) -> str:
    return {
        "critical": P["negative"],
        "high": P["warning"],
        "medium": P["accent"],
        "low": P["text_dim"],
    }.get(s.lower(), P["text_dim"])


def _status_color(s: str) -> str:
    if "active" in s and "remediation" not in s:
        return P["positive"]
    if "complete" in s:
        return P["positive"]
    if "remediation active" in s:
        return P["accent"]
    if "critical" in s.lower() or "urgent" in s.lower():
        return P["negative"]
    if "in audit" in s or "scheduled" in s:
        return P["accent"]
    if "expired" in s or "not yet" in s:
        return P["warning"]
    return P["text_dim"]


def _tier_color(t: str) -> str:
    return {
        "tier 1": P["positive"],
        "tier 2": P["accent"],
        "tier 2 (post-breach)": P["warning"],
        "tier 3": P["warning"],
    }.get(t, P["text_dim"])


def _attestations_chart(items) -> str:
    """Lead chart — portcos ranked by security posture score (tone by band)."""
    def _tone(a):
        if a.overall_score >= 8.5: return "positive"
        if a.overall_score >= 7.5: return "teal"
        return "warning"
    top = sorted(items, key=lambda a: a.overall_score, reverse=True)
    rows = [ck_bar_row(f"{a.deal} · {a.sector}", f"{a.overall_score:.2f}/10",
            a.overall_score / 10.0 * 100.0, tone=_tone(a)) for a in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = security posture score (0-10 scale) '
            '· tone = score band</div></div>')


def _attestations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Sector","left"),("SOC 2","center"),("SOC 2 Expires","right"),
            ("HITRUST","center"),("HITRUST Expires","right"),("HIPAA","center"),
            ("PCI","center"),("ISO 27001","center"),("Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if a.overall_score >= 8.5 else (acc if a.overall_score >= 7.5 else warn)
        def att_cell(val: str) -> str:
            c = _status_color(val)
            return f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c};font-weight:700">{_html.escape(val)}</td>'
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.deal)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.sector)}</td>',
            att_cell(a.soc2_type),
            f'{ck_data_cell(f"""{_html.escape(a.soc2_expires)}""", align="right", mono=True, tone="dim")}',
            att_cell(a.hitrust_level),
            f'{ck_data_cell(f"""{_html.escape(a.hitrust_expires)}""", align="right", mono=True, tone="dim")}',
            att_cell(a.hipaa_assessment),
            att_cell(a.pci_level),
            att_cell(a.iso_27001),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{a.overall_score:.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pentest_chart(items) -> str:
    """Summary chart — portcos ranked by open critical+high pentest findings."""
    def _tone(p):
        if p.critical_findings > 0: return "negative"
        if p.high_findings > 2: return "warning"
        return "navy"
    scored = [(p, p.critical_findings + p.high_findings) for p in items]
    top = sorted(scored, key=lambda t: t[1], reverse=True)
    total = sum(n for _, n in top) or 1
    rows = [ck_bar_row(f"{p.deal} · {p.firm}",
            f"{p.critical_findings} crit / {p.high_findings} high ({p.remediated_pct * 100:.0f}% fixed)",
            n / total * 100.0, tone=_tone(p)) for p, n in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of critical+high findings '
            '· value = crit / high + remediation · tone = severity</div></div>')


def _pentest_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Deal","left"),("Test Date","right"),("Firm","left"),("Crit","right"),("High","right"),
            ("Med","right"),("Low","right"),("Remediated %","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(p.status)
        r_c = pos if p.remediated_pct >= 0.85 else (acc if p.remediated_pct >= 0.70 else warn)
        c_c = neg if p.critical_findings > 0 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.deal)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(p.test_date)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.firm)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{p.critical_findings}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{p.high_findings}</td>',
            f'{ck_data_cell(f"""{p.medium_findings}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.low_findings}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{p.remediated_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vendors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vendor","left"),("Category","left"),("Deals","right"),("Risk Score","right"),
            ("SOC 2 Current","center"),("Last Review","right"),("Spend ($M)","right"),("Tier","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _tier_color(v.risk_tier)
        s_c = pos if v.risk_score >= 9.0 else (acc if v.risk_score >= 8.5 else P["warning"])
        soc_c = pos if v.soc2_current else P["negative"]
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.vendor)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.category)}</td>',
            f'{ck_data_cell(f"""{v.portfolio_deals}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{v.risk_score:.1f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{soc_c};font-weight:700">{"YES" if v.soc2_current else "NO"}</td>',
            f'{ck_data_cell(f"""{_html.escape(v.last_review)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${v.contract_spend_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(v.risk_tier)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _incidents_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Date","right"),("Deal","left"),("Type","left"),("Severity","center"),
            ("Records (K)","right"),("Downtime (h)","right"),("Cost ($M)","right"),("Root Cause","left"),("Remediation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, inc in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _sev_color(inc.severity)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(inc.incident_date)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(inc.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(inc.incident_type)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(inc.severity)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{inc.records_affected_k:.1f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{inc.downtime_hours}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${inc.cost_m:.2f}M""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(inc.root_cause)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(inc.remediation_status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _frameworks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Framework","left"),("Version","left"),("Deals","right"),("Maturity","right"),
            ("Coverage %","right"),("Gaps","right"),("Remediation Cost ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if f.avg_maturity_score >= 4.0 else (acc if f.avg_maturity_score >= 3.5 else warn)
        c_c = pos if f.avg_coverage_pct >= 0.90 else (acc if f.avg_coverage_pct >= 0.80 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(f.framework)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(f.version)}</td>',
            f'{ck_data_cell(f"""{f.portfolio_deals}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{f.avg_maturity_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{f.avg_coverage_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{f.gaps_identified}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn};font-weight:700">${f.typical_remediation_cost_m:.2f}M</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _calendar_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Auditor","left"),("Audit Type","left"),("Start","right"),
            ("End","right"),("Scope","left"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(c.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.auditor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.audit_type)}</td>',
            f'{ck_data_cell(f"""{_html.escape(c.start_date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(c.end_date)}""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(c.scope)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_compliance_attestation(params: dict = None) -> str:
    from rcm_mc.data_public.compliance_attestation import compute_compliance_attestation
    r = compute_compliance_attestation()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Portfolio Cos", str(r.total_portcos), "", "") +
        ck_kpi_block("SOC 2 Type II", str(r.soc2_type_ii_count), "", "") +
        ck_kpi_block("HITRUST Certified", str(r.hitrust_certified_count), "", "") +
        ck_kpi_block("Avg Posture Score", f"{r.avg_posture_score:.2f}", "/10", "") +
        ck_kpi_block("Active Incidents", str(r.active_incidents), "", "") +
        ck_kpi_block("High-Risk Vendors", str(r.high_risk_vendors), "", "") +
        ck_kpi_block("Audits in Progress", str(r.audits_in_progress), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    a_tbl = _attestations_table(r.attestations)
    a_chart = _attestations_chart(r.attestations)
    p_tbl = _pentest_table(r.pentests)
    p_chart = _pentest_chart(r.pentests)
    v_tbl = _vendors_table(r.vendors)
    i_tbl = _incidents_table(r.incidents)
    f_tbl = _frameworks_table(r.frameworks)
    c_tbl = _calendar_table(r.calendar)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    crit_findings = sum(p.critical_findings for p in r.pentests)
    total_incident_cost = sum(i.cost_m for i in r.incidents)

    # B11 sweep batch 2 PR 7/10 — bespoke .ck-page-h1 → ck_page_title.
    # Portfolio-wide compliance posture page. Pre-fix sub-line was
    # 6+ stats; trimmed to 4 most-load-bearing: portfolio scope
    # (total portcos), the two name-brand attestation counts
    # (SOC 2 Type II + HITRUST — the certifications partners
    # actually ask about), and the average posture score. The
    # dropped stats (audits-in-progress + elevated-risk vendors)
    # remain visible in the KPI strip below.
    page_title = ck_page_title(
        "Compliance Attestation / Security Posture Tracker",
        eyebrow="COMPLIANCE",
        meta=(
            f"{r.total_portcos} portcos · "
            f"{r.soc2_type_ii_count} SOC 2 Type II · "
            f"{r.hitrust_certified_count} HITRUST certified · "
            f"avg {r.avg_posture_score:.2f}/10 posture"
        ),
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Attestation Status — SOC 2, HITRUST, HIPAA, PCI, ISO</div>{a_chart}{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">Penetration Test Findings</div>{p_chart}{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Security Incident History</div>{i_tbl}</div>
  <div style="{cell}"><div style="{h3}">Third-Party Vendor Risk</div>{v_tbl}</div>
  <div style="{cell}"><div style="{h3}">Control Framework Maturity</div>{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Audit Calendar — Next 12 Months</div>{c_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Portfolio Security Posture:</strong> {r.soc2_type_ii_count} of {r.total_portcos} portcos hold SOC 2 Type II ({r.soc2_type_ii_count / r.total_portcos * 100:.0f}%); {r.hitrust_certified_count} hold HITRUST (essentials or r2); average posture score {r.avg_posture_score:.2f}/10.
    Top-tier posture: Oak (RCM SaaS, 9.2) and Fir (Lab, 9.0) — both hold SOC 2 Type II + HITRUST r2 + ISO 27001. Laggards: Sage (Home Health, 6.5 — SOC 2 expired), Aspen (Eye Care, 6.8 — post-breach remediation).
    Penetration testing yielded {crit_findings} critical findings across {len(r.pentests)} portcos YTD; 3 have active critical remediation underway (Redwood, Aspen, Sage) with projected close by Q2 2026.
    Vendor book: 12 tier-1 vendors account for ~70% of portfolio tech spend; Change Healthcare (post-breach tier 2), Iron Mountain (SOC 2 gap), Stericycle (SOC 2 gap) are the 3 flagged vendors — compensating controls in place.
    Incident history YTD: 8 incidents totaling ${total_incident_cost:.1f}M cost — Aspen ransomware (Feb 2024) drives 70% of cost, all subsequent incidents medium-severity or below with contained impact.
    Upcoming audit calendar: 10 engagements valued ~$4.5M across SOC 2, HITRUST upgrades, Type II transitions — Sage SOC 2 Type I urgent (expired) is top priority.
  </div>
</div>"""

    return chartis_shell(body, "Compliance Tracker", active_nav="/compliance-attestation",
        editorial_intro={
            "eyebrow": "COMPLIANCE ATTESTATION",
            "headline": "What the compliance attestation page reveals on this deal.",
            "italic_word": "reveals",
        })
