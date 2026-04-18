"""Drug Shortage / Supply-Chain Risk Tracker — /drug-shortage."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _drugs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Drug","left"),("Therapy","center"),("Shortage Status","left"),("Sole-Source","center"),
            ("Annual Volume","right"),("Substitute","center"),("Spend ($M)","right"),("Days on Hand","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = neg if "active" in d.shortage_status or "intermittent" in d.shortage_status or "rolling" in d.shortage_status else (warn if "resolved" in d.shortage_status else pos)
        ss_c = neg if d.sole_source else pos
        sub_c = pos if d.substitution_available else neg
        doh_c = neg if d.days_on_hand < 30 else (warn if d.days_on_hand < 60 else pos)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.drug)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.therapy_area)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{s_c}">{_html.escape(d.shortage_status)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{ss_c};font-weight:700">{"YES" if d.sole_source else "NO"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.annual_volume_doses:,}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{sub_c}">{"YES" if d.substitution_available else "NO"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${d.platform_spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{doh_c};font-weight:600">{d.days_on_hand}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _suppliers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Supplier","left"),("Category","left"),("Spend ($M)","right"),("Category Share","right"),
            ("Country","left"),("Audit History","left"),("Risk Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = neg if s.risk_score >= 60 else (warn if s.risk_score >= 45 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.supplier)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.annual_spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{s.share_of_category * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.country_of_manufacture)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.audit_history)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{s.risk_score}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _geo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Country","left"),("Product Categories","right"),("Spend Exposure ($M)","right"),
            ("Tariff Risk","right"),("Geopolitical Risk","center"),("Diversification Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    gr_c = {"very low": pos, "low": pos, "moderate": warn, "elevated": neg, "hurricane risk": warn}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gc = gr_c.get(g.geopolitical_risk, text_dim)
        d_c = pos if g.diversification_score >= 85 else (warn if g.diversification_score >= 65 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(g.country)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{g.product_categories}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${g.spend_exposure_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn if g.tariff_risk_pct > 0.10 else text_dim}">{g.tariff_risk_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{gc};border:1px solid {gc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.geopolitical_risk)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{g.diversification_score}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _playbooks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Scenario","left"),("Probability","right"),("Financial Impact ($M)","right"),
            ("Operational Impact","left"),("Mitigation","center"),("Lead Time (days)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pr_c = neg if p.probability_pct >= 0.40 else (warn if p.probability_pct >= 0.20 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pr_c};font-weight:700">{p.probability_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${p.financial_impact_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.operational_impact)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.mitigation_status)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.lead_time_days}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _gpo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("GPO","left"),("Contracts","right"),("Annual Volume ($M)","right"),
            ("On-Time Fill","right"),("Backorder Rate","right"),("Price Stability","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ot_c = pos if g.on_time_fill_rate_pct >= 0.95 else (P["warning"] if g.on_time_fill_rate_pct >= 0.93 else neg)
        bo_c = pos if g.backorder_rate_pct <= 0.03 else (P["warning"] if g.backorder_rate_pct <= 0.035 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(g.gpo_partner)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{g.contracts_count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${g.annual_volume_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ot_c};font-weight:700">{g.on_time_fill_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{bo_c}">{g.backorder_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{g.price_stability_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_drug_shortage(params: dict = None) -> str:
    from rcm_mc.data_public.drug_shortage import compute_drug_shortage
    r = compute_drug_shortage()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    tier_c = neg if r.risk_tier == "elevated" else (warn if r.risk_tier == "moderate" else pos)

    kpi_strip = (
        ck_kpi_block("Critical Drugs", str(r.total_critical_drugs), "", "") +
        ck_kpi_block("Active Shortages", str(r.active_shortages), "", "") +
        ck_kpi_block("Platform Spend", f"${r.total_platform_spend_mm:,.1f}M", "", "") +
        ck_kpi_block("Sole-Source Exposure", f"${r.sole_source_exposure_mm:,.2f}M", "", "") +
        ck_kpi_block("Supply Risk Score", f"{r.overall_supply_risk_score}/100", "", "") +
        ck_kpi_block("Risk Tier", r.risk_tier.upper(), "", "") +
        ck_kpi_block("GPO Partners", str(len(r.gpos)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    d_tbl = _drugs_table(r.drugs)
    s_tbl = _suppliers_table(r.suppliers)
    g_tbl = _geo_table(r.geography)
    p_tbl = _playbooks_table(r.playbooks)
    gpo_tbl = _gpo_table(r.gpos)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    weighted_impact = sum(p.probability_pct * p.financial_impact_mm for p in r.playbooks)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Drug Shortage / Supply-Chain Risk</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">FDA shortage list · supplier concentration · geographic exposure · shortage playbooks · GPO reliability — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {tier_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Supply Chain Posture</div>
    <div style="color:{tier_c};font-weight:700;font-size:14px">Risk tier {_html.escape(r.risk_tier.upper())} · {r.active_shortages} active shortages · ${weighted_impact:,.2f}M probability-weighted shortfall exposure</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Sole-source exposure ${r.sole_source_exposure_mm:,.2f}M · highest-risk drugs in oncology (5-FU, Cisplatin)</div>
  </div>
  <div style="{cell}"><div style="{h3}">Critical Drug Inventory &amp; Shortage Status</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Supplier Concentration &amp; Audit History</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Geographic Exposure &amp; Tariff Risk</div>{g_tbl}</div>
  <div style="{cell}"><div style="{h3}">Shortage Scenario Playbooks</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">GPO Partner Performance</div>{gpo_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Supply Chain Thesis:</strong> {r.active_shortages} of {r.total_critical_drugs} critical drugs in active or intermittent shortage.
    Sole-source exposure ${r.sole_source_exposure_mm:,.2f}M (Adenosine, Regadenoson — cardiac stress testing).
    China sterile-injectables tariff escalation is the highest-probability / highest-impact scenario at 45% likelihood and ${max(p.financial_impact_mm for p in r.playbooks if 'tariff' in p.scenario.lower()):,.1f}M downside.
    Vizient and Premier GPO performance is strong (95-96% fill rate, 2.5-2.8% backorder) — dual-sourcing strategy mitigates single-GPO risk.
    Recommend: activate compounding-pharmacy partnerships for oncology drugs, pre-position 90 days inventory on sole-source drugs, and establish secondary GPO contract for bottom-tercile drugs.
  </div>
</div>"""

    return chartis_shell(body, "Drug Shortage", active_nav="/drug-shortage")
