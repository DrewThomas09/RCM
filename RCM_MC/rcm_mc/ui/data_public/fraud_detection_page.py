"""Fraud / Waste / Abuse Detection Panel — /fraud-detection."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor


def _billing_chart(items) -> str:
    """Lead chart for the provider billing-anomaly table — providers
    ranked by anomaly score so the highest-risk billers surface before
    the dense per-provider grid. Bar width = anomaly score (0-100),
    value = dollar exposure ($k), tone tracks the table's severity
    coloring (critical/high red · medium amber · low teal).
    """
    tone_for = {"critical": "negative", "high": "negative",
                "medium": "warning", "low": "teal"}
    ranked = sorted(items, key=lambda b: b.anomaly_score, reverse=True)
    rows = []
    for b in ranked:
        rows.append(ck_bar_row(
            b.provider_id,
            f"${b.dollar_exposure_k:,.0f}k",
            float(b.anomaly_score),
            tone=tone_for.get(b.severity, "teal"),
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = anomaly score (0–100) · value = dollar exposure ($k) · '
        'tone = severity (red critical/high · amber medium · teal low)</div>'
        '</div>'
    )


def _billing_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Provider","left"),("Specialty","left"),("Pattern","left"),("Anomaly Score","right"),
            ("Peer Percentile","right"),("Exposure ($k)","right"),("Severity","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    sev_c = {"critical": neg, "high": neg, "medium": warn, "low": text_dim}
    _max_exp = max((b.dollar_exposure_k for b in items), default=1.0) or 1.0
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(b.severity, text_dim)
        s_c = neg if b.anomaly_score >= 85 else (warn if b.anomaly_score >= 70 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.provider_id)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(b.specialty)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.billing_pattern)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{b.anomaly_score}</td>',
            f'{ck_data_cell(f"""P{b.peer_comparison_percentile}""", align="right", mono=True, tone="neg", weight=600)}',
            f'{ck_data_cell(f"""${b.dollar_exposure_k:,.1f}""", align="right", mono=True, tone="neg", weight=700, bar=b.dollar_exposure_k / _max_exp * 100)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.severity)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _upcoding_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("CPT","left"),("Description","left"),("Platform %","right"),("Peer %","right"),
            ("Delta","right"),("Volume","right"),("Clawback ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, u in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = neg if u.delta_pp >= 0.15 else (warn if u.delta_pp >= 0.10 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(u.cpt_code)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(u.description)}</td>',
            f'{ck_data_cell(f"""{u.platform_pct_high_level * 100:.1f}%""", align="right", mono=True, tone="neg", weight=700)}',
            f'{ck_data_cell(f"""{u.peer_pct_high_level * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">+{u.delta_pp * 100:.1f}pp</td>',
            f'{ck_data_cell(f"""{u.annual_volume:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${u.potential_clawback_mm:,.2f}""", align="right", mono=True, tone="neg", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _referrals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Referring Provider","left"),("Referred To","left"),("Referrals LTM","right"),
            ("Ownership Overlap","center"),("Stark Exception","left"),("AKS Risk Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        o_c = neg if r.ownership_overlap else pos
        r_c = neg if r.aks_risk_score >= 75 else (warn if r.aks_risk_score >= 55 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.referring_provider)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(r.referred_to)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{r.referral_count_ltm:,}""", align="right", mono=True)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{o_c};font-weight:700">{"YES" if r.ownership_overlap else "NO"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.stark_exception)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{r.aks_risk_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _fingerprints_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Pattern","left"),("Description","left"),("Claims Flagged","right"),
            ("Dollar Impact ($M)","right"),("Payback Likelihood","right"),("Remediation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(f.pattern)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.description)}</td>',
            f'{ck_data_cell(f"""{f.claims_flagged}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${f.dollar_impact_mm:,.2f}""", align="right", mono=True, tone="neg", weight=700)}',
            f'{ck_data_cell(f"""{f.likelihood_of_payback * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.remediation)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _geo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("ZIP","left"),("Provider Count","right"),("Volume vs Pop (norm)","right"),
            ("Cluster Severity","center"),("Service Line","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    sev_c = {"severe": neg, "moderate": warn, "mild": text_dim}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(g.cluster_severity, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(g.zip_code)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{g.provider_count}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{g.volume_vs_pop_norm:.2f}x""", align="right", mono=True, tone="neg", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.cluster_severity)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{_html.escape(g.service_line)}""", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _events_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; pos = P["positive"]
    cols = [("Event","left"),("Date","left"),("Type","center"),("Resolution","left"),("Financial Impact ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if e.resolution.startswith("dismissed") or e.resolution.startswith("closed") or "declined" in e.resolution else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.event)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(e.date)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{r_c}">{_html.escape(e.resolution)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if e.financial_impact_mm > 0 else text_dim}">${e.financial_impact_mm:,.3f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _leie_panel() -> str:
    """Real OIG LEIE exclusions anchor — the realized Medicare/Medicaid
    fraud-&-abuse / sanction record (excluded providers). PII-free counts;
    the deal's fraud-risk scoring model below is illustrative."""
    from rcm_mc.data import oig_leie as _l
    s = _l.leie_summary()
    if not s.get("total_exclusions"):
        return ""
    types = _l.by_exclusion_type(6)
    states = _l.top_states(6)
    border = P["border"]; tp = P["text"]; td = P["text_dim"]; ac = P["accent"]
    fa = P.get("text_faint", td)
    mx = max((int(t["count"]) for t in types), default=1) or 1
    rows = "".join(
        f'<tr><td style="padding:3px 8px;font-size:11px;color:{tp}">{_html.escape(t["label"])}</td>'
        f'<td style="padding:3px 8px;width:38%"><svg width="100%" height="9" preserveAspectRatio="none" viewBox="0 0 100 9">'
        f'<rect x="0" y="1" width="{int(int(t["count"])/mx*100)}" height="7" fill="{ac}" opacity="0.75"/></svg></td>'
        f'<td style="padding:3px 8px;text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;'
        f'font-variant-numeric:tabular-nums;color:{tp}">{int(t["count"]):,}</td></tr>'
        for t in types
    )
    st_chips = "".join(
        f'<span style="display:inline-block;margin-right:10px;font-family:JetBrains Mono,monospace;'
        f'font-size:11px;color:{tp}">{_html.escape(s2["state"])} '
        f'<span style="color:{ac};font-variant-numeric:tabular-nums">{int(s2["count"]):,}</span></span>'
        for s2 in states
    )
    total = int(s["total_exclusions"]); nst = int(s.get("states", 0))
    return (
        f'<div style="background:{P["panel"]};border:1px solid {border};border-left:3px solid {ac};'
        f'padding:14px 16px;margin-bottom:16px">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{td};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px">'
        f'Real OIG LEIE exclusions &mdash; the realized fraud/abuse record'
        f'<span style="color:{ac};font-weight:600"> · LIVE</span></div>'
        f'<div style="display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start">'
        f'<div style="white-space:nowrap"><div style="font-family:JetBrains Mono,monospace;font-size:20px;'
        f'color:{tp};font-variant-numeric:tabular-nums">{total:,}</div>'
        f'<div style="font-size:10px;color:{td}">excluded individuals/entities<br>({nst} states)</div></div>'
        f'<div><div style="font-size:9px;color:{fa};margin-bottom:4px">TOP EXCLUSION TYPES</div>'
        f'<table style="width:100%;border-collapse:collapse">{rows}</table></div></div>'
        f'<div style="margin-top:8px;font-size:10px;color:{td}"><span style="color:{fa}">Most exclusions:</span> {st_chips}</div>'
        f'<div style="margin-top:6px;font-size:10px;color:{fa}">HHS OIG LEIE (PII dropped at ingest). '
        f'Real realized exclusions &mdash; the fraud/abuse base rate. NOT this deal\'s providers and NOT a '
        f'prediction; the fraud-risk scores below are illustrative.</div></div>'
    )


def render_fraud_detection(params: dict = None) -> str:
    from rcm_mc.data_public.fraud_detection import compute_fraud_detection
    r = compute_fraud_detection()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    tier_c = neg if r.risk_tier == "elevated" else (warn if r.risk_tier == "moderate" else pos)

    kpi_strip = (
        ck_kpi_block("Total Anomalies", str(r.total_anomalies_flagged), "", "") +
        ck_kpi_block("High Severity", str(r.high_severity_count), "", "") +
        ck_kpi_block("Total Exposure", f"${r.total_exposure_mm:,.1f}M", "", "") +
        ck_kpi_block("FWA Risk Score", f"{r.platform_fwa_risk_score}/100", "", "") +
        ck_kpi_block("Risk Tier", r.risk_tier.upper(), "", "") +
        ck_kpi_block("Upcoding CPTs", str(len(r.upcoding)), "", "") +
        ck_kpi_block("Compliance Events", str(len(r.events)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    b_chart = _billing_chart(r.billing_anomalies)
    b_tbl = _billing_table(r.billing_anomalies)
    u_tbl = _upcoding_table(r.upcoding)
    r_tbl = _referrals_table(r.referrals)
    f_tbl = _fingerprints_table(r.fingerprints)
    g_tbl = _geo_table(r.geography)
    e_tbl = _events_table(r.events)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    # 2026-05-30 audit P5 editorial: "FWA" (Fraud / Waste / Abuse) is
    # the compliance acronym; "fraud" is the common-vocabulary umbrella.
    # Eyebrow keeps FRAUD DETECTION; FWA framing continues to appear
    # in the meta line and body.
    page_title = ck_page_title(
        "Fraud Detection Panel",
        eyebrow="FRAUD DETECTION",
        meta=f"{r.total_anomalies_flagged} anomalies flagged ({r.high_severity_count} high severity) · ${r.total_exposure_mm:,.1f}M total exposure if findings sustained · {r.platform_fwa_risk_score}/100 FWA risk score ({r.risk_tier.upper()} tier) · {len(r.events)} compliance events on record",
    )

    _fwa_tone = {"elevated": "negative", "moderate": "warning"}.get(r.risk_tier, "positive")
    value_anchor = ck_value_anchor(
        "FWA Risk",
        f"{r.platform_fwa_risk_score}/100",
        delta=f"{r.risk_tier.upper()} tier · {r.high_severity_count} high-severity anomalies",
        opportunity=f"${r.total_exposure_mm:,.1f}M exposure if findings sustained",
        target="Zero high-severity",
        tone=_fwa_tone,
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  {_leie_panel()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {tier_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">FWA Risk Posture</div>
    <div style="color:{tier_c};font-weight:700;font-size:14px">Risk tier: {_html.escape(r.risk_tier.upper())} · {r.total_anomalies_flagged} anomalies · ${r.total_exposure_mm:,.1f}M total exposure</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">{r.high_severity_count} high-severity flags warrant immediate compliance review</div>
  </div>
  <div style="{cell}"><div style="{h3}">Provider-Level Billing Anomalies</div>{b_chart}{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Upcoding Risk — Platform vs Peer</div>{u_tbl}</div>
  <div style="{cell}"><div style="{h3}">Referral Pattern Analysis — Stark / Anti-Kickback</div>{r_tbl}</div>
  <div style="{cell}"><div style="{h3}">Claim Fingerprint Patterns</div>{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Geographic Cluster Anomalies</div>{g_tbl}</div>
  <div style="{cell}"><div style="{h3}">Compliance Event History</div>{e_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">FWA Detection Thesis:</strong> {r.total_anomalies_flagged} distinct anomalies surfaced across billing, coding, referral, and geographic pattern-matching.
    Aggregate financial exposure ${r.total_exposure_mm:,.1f}M if all findings sustained.
    Highest-concentration risks: upcoding on E/M codes 99214/99215 (85% pattern across network) and modifier stacking in surgical sub-specialties.
    Ownership-overlap referral patterns trigger AKS / Stark review for 6 of 8 intra-platform chains.
    Immediate remediation: audit top-10 anomaly-score providers, roll out documentation training, and implement real-time claim-edit rules before next submission cycle.
    OIG/DOJ engagement on current matters has resulted in no material financial impact — active compliance program demonstrates good-faith effort.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "FWA Detection", active_nav="/fraud-detection",
        editorial_intro={
            "eyebrow": "FRAUD DETECTION",
            "headline": "What the fraud detection page reveals on this deal.",
            "italic_word": "reveals",
        })
