"""Fraud / Waste / Abuse Detection Panel — /fraud-detection."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _billing_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Provider","left"),("Specialty","left"),("Pattern","left"),("Anomaly Score","right"),
            ("Peer Percentile","right"),("Exposure ($k)","right"),("Severity","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sev_c = {"critical": neg, "high": neg, "medium": warn, "low": text_dim}
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(b.severity, text_dim)
        s_c = neg if b.anomaly_score >= 85 else (warn if b.anomaly_score >= 70 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.provider_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(b.specialty)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.billing_pattern)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{b.anomaly_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">P{b.peer_comparison_percentile}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${b.dollar_exposure_k:,.1f}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.severity)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _upcoding_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("CPT","left"),("Description","left"),("Platform %","right"),("Peer %","right"),
            ("Delta","right"),("Volume","right"),("Clawback ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, u in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = neg if u.delta_pp >= 0.15 else (warn if u.delta_pp >= 0.10 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(u.cpt_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(u.description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{u.platform_pct_high_level * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{u.peer_pct_high_level * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">+{u.delta_pp * 100:.1f}pp</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{u.annual_volume:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${u.potential_clawback_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _referrals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Referring Provider","left"),("Referred To","left"),("Referrals LTM","right"),
            ("Ownership Overlap","center"),("Stark Exception","left"),("AKS Risk Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        o_c = neg if r.ownership_overlap else pos
        r_c = neg if r.aks_risk_score >= 75 else (warn if r.aks_risk_score >= 55 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.referring_provider)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.referred_to)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.referral_count_ltm:,}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{o_c};font-weight:700">{"YES" if r.ownership_overlap else "NO"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.stark_exception)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{r.aks_risk_score}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _fingerprints_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Pattern","left"),("Description","left"),("Claims Flagged","right"),
            ("Dollar Impact ($M)","right"),("Payback Likelihood","right"),("Remediation","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(f.pattern)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{f.claims_flagged}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${f.dollar_impact_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{f.likelihood_of_payback * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.remediation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _geo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("ZIP","left"),("Provider Count","right"),("Volume vs Pop (norm)","right"),
            ("Cluster Severity","center"),("Service Line","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sev_c = {"severe": neg, "moderate": warn, "mild": text_dim}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(g.cluster_severity, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(g.zip_code)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{g.provider_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{g.volume_vs_pop_norm:.2f}x</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.cluster_severity)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(g.service_line)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _events_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; pos = P["positive"]
    cols = [("Event","left"),("Date","left"),("Type","center"),("Resolution","left"),("Financial Impact ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if e.resolution.startswith("dismissed") or e.resolution.startswith("closed") or "declined" in e.resolution else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.event)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(e.date)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{r_c}">{_html.escape(e.resolution)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if e.financial_impact_mm > 0 else text_dim}">${e.financial_impact_mm:,.3f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    b_tbl = _billing_table(r.billing_anomalies)
    u_tbl = _upcoding_table(r.upcoding)
    r_tbl = _referrals_table(r.referrals)
    f_tbl = _fingerprints_table(r.fingerprints)
    g_tbl = _geo_table(r.geography)
    e_tbl = _events_table(r.events)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Fraud / Waste / Abuse Detection</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Billing anomaly surveillance · upcoding risk · Stark/AKS referral patterns · claim fingerprints · geographic anomalies · compliance events — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {tier_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">FWA Risk Posture</div>
    <div style="color:{tier_c};font-weight:700;font-size:14px">Risk tier: {_html.escape(r.risk_tier.upper())} · {r.total_anomalies_flagged} anomalies · ${r.total_exposure_mm:,.1f}M total exposure</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">{r.high_severity_count} high-severity flags warrant immediate compliance review</div>
  </div>
  <div style="{cell}"><div style="{h3}">Provider-Level Billing Anomalies</div>{b_tbl}</div>
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

    return chartis_shell(body, "FWA Detection", active_nav="/fraud-detection")
