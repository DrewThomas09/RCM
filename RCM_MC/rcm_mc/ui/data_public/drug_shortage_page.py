"""Drug Shortage / Supply-Chain Risk Tracker — /drug-shortage."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_bar_row, ck_value_anchor, ck_source_purpose


def _drugs_chart(items) -> str:
    """Lead chart — critical drugs ranked by platform spend (tone by status)."""
    def _tone(status):
        s = (status or "").lower()
        if "active" in s: return "negative"
        if "resolv" in s or "watch" in s: return "warning"
        return "teal"
    total = sum(d.platform_spend_mm for d in items) or 1.0
    rows = [ck_bar_row(d.drug, f"${d.platform_spend_mm:,.1f}M",
            d.platform_spend_mm / total * 100.0, tone=_tone(d.shortage_status))
            for d in sorted(items, key=lambda d: d.platform_spend_mm, reverse=True)]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of platform drug spend '
            '\u00b7 value = spend ($M) \u00b7 tone = shortage status</div></div>')



def _drugs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Drug","left"),("Therapy","center"),("Shortage Status","left"),("Sole-Source","center"),
            ("Annual Volume","right"),("Substitute","center"),("Spend ($M)","right"),("Days on Hand","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = neg if "active" in d.shortage_status or "intermittent" in d.shortage_status or "rolling" in d.shortage_status else (warn if "resolved" in d.shortage_status else pos)
        ss_c = neg if d.sole_source else pos
        sub_c = pos if d.substitution_available else neg
        doh_c = neg if d.days_on_hand < 30 else (warn if d.days_on_hand < 60 else pos)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.drug)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.therapy_area)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{s_c}">{_html.escape(d.shortage_status)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{ss_c};font-weight:700">{"YES" if d.sole_source else "NO"}</td>',
            f'{ck_data_cell(f"""{d.annual_volume_doses:,}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{sub_c}">{"YES" if d.substitution_available else "NO"}</td>',
            f'{ck_data_cell(f"""${d.platform_spend_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{doh_c};font-weight:600">{d.days_on_hand}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _suppliers_chart(items) -> str:
    """Summary chart — suppliers ranked by annual spend (tone by risk score)."""
    def _tone(s):
        if s.risk_score >= 70: return "negative"
        if s.risk_score >= 45: return "warning"
        return "teal"
    top = sorted(items, key=lambda s: s.annual_spend_mm, reverse=True)
    total = sum(s.annual_spend_mm for s in top) or 1.0
    rows = [ck_bar_row(f"{s.supplier} · {s.country_of_manufacture}",
            f"${s.annual_spend_mm:,.1f}M · risk {s.risk_score:.0f}",
            s.annual_spend_mm / total * 100.0, tone=_tone(s)) for s in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of supplier spend '
            '· value = spend ($M) + risk score · tone = supply risk</div></div>')


def _suppliers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Supplier","left"),("Category","left"),("Spend ($M)","right"),("Category Share","right"),
            ("Country","left"),("Audit History","left"),("Risk Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = neg if s.risk_score >= 60 else (warn if s.risk_score >= 45 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.supplier)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(s.category)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.annual_spend_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{s.share_of_category * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{_html.escape(s.country_of_manufacture)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.audit_history)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{s.risk_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _geo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Country","left"),("Product Categories","right"),("Spend Exposure ($M)","right"),
            ("Tariff Risk","right"),("Geopolitical Risk","center"),("Diversification Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    gr_c = {"very low": pos, "low": pos, "moderate": warn, "elevated": neg, "hurricane risk": warn}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gc = gr_c.get(g.geopolitical_risk, text_dim)
        d_c = pos if g.diversification_score >= 85 else (warn if g.diversification_score >= 65 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(g.country)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{g.product_categories}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${g.spend_exposure_mm:,.2f}""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn if g.tariff_risk_pct > 0.10 else text_dim}">{g.tariff_risk_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{gc};border:1px solid {gc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.geopolitical_risk)}</span>""", align="center")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{g.diversification_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _playbooks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Scenario","left"),("Probability","right"),("Financial Impact ($M)","right"),
            ("Operational Impact","left"),("Mitigation","center"),("Lead Time (days)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pr_c = neg if p.probability_pct >= 0.40 else (warn if p.probability_pct >= 0.20 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.scenario)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pr_c};font-weight:700">{p.probability_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""${p.financial_impact_mm:,.2f}""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.operational_impact)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.mitigation_status)}</td>',
            f'{ck_data_cell(f"""{p.lead_time_days}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _gpo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("GPO","left"),("Contracts","right"),("Annual Volume ($M)","right"),
            ("On-Time Fill","right"),("Backorder Rate","right"),("Price Stability","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ot_c = pos if g.on_time_fill_rate_pct >= 0.95 else (P["warning"] if g.on_time_fill_rate_pct >= 0.93 else neg)
        bo_c = pos if g.backorder_rate_pct <= 0.03 else (P["warning"] if g.backorder_rate_pct <= 0.035 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(g.gpo_partner)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{g.contracts_count:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${g.annual_volume_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ot_c};font-weight:700">{g.on_time_fill_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{bo_c}">{g.backorder_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{g.price_stability_pct * 100:.0f}%""", align="right", mono=True)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _fda_shortage_section(params: dict) -> str:
    """REAL FDA (openFDA) drug-shortage landscape — LIVE, product-level. Build-
    time snapshot; not provider-specific. Optional ?drug= search."""
    try:
        from rcm_mc.data import drug_shortage_data as _ds
        summ = _ds.drug_shortage_summary()
        cats = _ds.shortages_by_category(current_only=True, limit=12)
        search = (params.get("drug") or "").strip()
        tbl = _ds.current_shortages(search=search, limit=30)
    except Exception:
        return ""
    if not summ.get("total"):
        return ""
    hdr = ck_source_purpose(
        purpose=("See the current national drug-shortage landscape (FDA) and "
                 "which therapeutic categories are most affected — context for a "
                 "target's pharmacy/infusion supply risk."),
        universe="cms", confidence="derived",
        source=f"openFDA drug/shortages (public domain) · snapshot {summ.get('snapshot_date','')}",
        next_action="Search a drug to check its current FDA shortage status")
    cat_rows = "".join(
        f'<tr><td style="padding:3px 10px">{_html.escape(str(c["category"]))}</td>'
        f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums">{c["n"]:,}</td></tr>'
        for c in cats)
    form = (
        f'<form method="get" action="/drug-shortage" style="margin:8px 0;display:flex;gap:8px">'
        f'<input type="text" name="drug" value="{_html.escape(params.get("drug",""))}" '
        f'placeholder="Search drug / company" style="padding:6px 9px;border:1px solid '
        f'{P["border"]};border-radius:2px;min-width:240px;font-size:13px">'
        f'<button type="submit" style="padding:6px 14px;background:{P["accent"]};color:#fff;'
        f'border:none;border-radius:2px;font-size:12px;cursor:pointer">Search</button></form>')
    drug_rows = "".join(
        f'<tr><td style="padding:3px 10px">{_html.escape(str(t.generic_name))}</td>'
        f'<td style="padding:3px 10px">{_html.escape(str(t.company_name)[:32])}</td>'
        f'<td style="padding:3px 10px">{_html.escape(str(t.therapeutic_category)[:28])}</td>'
        f'<td style="padding:3px 10px">{_html.escape(str(t.availability) or "—")}</td></tr>'
        for t in tbl.itertuples())
    # 2026-05-28 batch 32 · Tier-4 trope removal — strip 3px accent.
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:2px;padding:14px 16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:8px">'
        f'FDA Drug Shortages · LIVE (openFDA)</div>{hdr}'
        f'<p style="font-size:12px;color:{P["text_dim"]};margin:4px 0 8px">'
        f'<b style="color:{P["text"]}">{summ["current"]:,}</b> current shortages across '
        f'<b style="color:{P["text"]}">{summ["categories"]}</b> therapeutic categories '
        f'(FDA, national).</p>'
        f'<div style="display:flex;gap:18px;flex-wrap:wrap">'
        f'<div style="flex:1;min-width:240px"><div style="font-size:10px;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:4px">'
        f'Most-affected categories (current)</div>'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<tbody>{cat_rows}</tbody></table></div>'
        f'<div style="flex:1.4;min-width:300px"><div style="font-size:10px;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:4px">Current shortages</div>'
        f'{form}<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr style="border-bottom:1px solid {P["border"]};color:{P["text_dim"]}">'
        f'<th style="padding:3px 10px;text-align:left">Drug</th>'
        f'<th style="padding:3px 10px;text-align:left">Company</th>'
        f'<th style="padding:3px 10px;text-align:left">Category</th>'
        f'<th style="padding:3px 10px;text-align:left">Availability</th></tr></thead>'
        f'<tbody>{drug_rows}</tbody></table></div></div>'
        f'<p style="font-size:11px;color:{P["text_dim"]};margin:8px 0 0">'
        f'National FDA shortage data — <b>product-level, not provider-specific</b>; '
        f'a listed shortage does not by itself imply impact on a given target. The '
        f'supplier / GPO / scenario model below is an illustrative planning '
        f'calculator.</p></div>')


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

    d_chart = _drugs_chart(r.drugs)
    d_tbl = _drugs_table(r.drugs)
    value_anchor = ck_value_anchor(
        "Drug Shortage Risk",
        f"{r.overall_supply_risk_score}/100 supply risk",
        delta=f"{r.total_critical_drugs} critical drugs \u00b7 {r.active_shortages} active shortages \u00b7 ${r.total_platform_spend_mm:,.1f}M spend \u00b7 {r.risk_tier} tier",
        opportunity=f"${r.sole_source_exposure_mm:,.1f}M sole-source exposure",
        tone="warning",
    )
    s_tbl = _suppliers_table(r.suppliers)
    s_chart = _suppliers_chart(r.suppliers)
    g_tbl = _geo_table(r.geography)
    p_tbl = _playbooks_table(r.playbooks)
    gpo_tbl = _gpo_table(r.gpos)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    weighted_impact = sum(p.probability_pct * p.financial_impact_mm for p in r.playbooks)
    # 2026-05-30 audit P5 editorial: drug shortages ARE the supply-
    # chain risk the page tracks — the slash-dual was a paraphrase.
    # "Drug Shortage Tracker" matches the eyebrow + route.
    page_title = ck_page_title(
        "Drug Shortage Tracker",
        eyebrow="DRUG SHORTAGE",
        meta=f"{r.active_shortages} of {r.total_critical_drugs} critical drugs in active shortage · ${r.sole_source_exposure_mm:,.2f}M sole-source exposure · ${weighted_impact:,.2f}M probability-weighted shortfall exposure · {r.overall_supply_risk_score}/100 supply risk score ({r.risk_tier.upper()} tier)",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {_fda_shortage_section(params or {})}
  <div style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{text_dim};margin:18px 0 4px">Illustrative supply-chain planning model (calculator below)</div>
  {ck_illustrative_note("supplier concentration, GPO performance, and scenario figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {tier_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Supply Chain Posture</div>
    <div style="color:{tier_c};font-weight:700;font-size:14px">Risk tier {_html.escape(r.risk_tier.upper())} · {r.active_shortages} active shortages · ${weighted_impact:,.2f}M probability-weighted shortfall exposure</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Sole-source exposure ${r.sole_source_exposure_mm:,.2f}M · highest-risk drugs in oncology (5-FU, Cisplatin)</div>
  </div>
  <div style="{cell}"><div style="{h3}">Critical Drug Inventory &amp; Shortage Status</div>{d_chart}{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Supplier Concentration &amp; Audit History</div>{s_chart}{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Geographic Exposure &amp; Tariff Risk</div>{g_tbl}</div>
  <div style="{cell}"><div style="{h3}">Shortage Scenario Playbooks</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">GPO Partner Performance</div>{gpo_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-radius:2px;padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Supply Chain Thesis:</strong> {r.active_shortages} of {r.total_critical_drugs} critical drugs in active or intermittent shortage.
    Sole-source exposure ${r.sole_source_exposure_mm:,.2f}M (Adenosine, Regadenoson — cardiac stress testing).
    China sterile-injectables tariff escalation is the highest-probability / highest-impact scenario at 45% likelihood and ${max(p.financial_impact_mm for p in r.playbooks if 'tariff' in p.scenario.lower()):,.1f}M downside.
    Vizient and Premier GPO performance is strong (95-96% fill rate, 2.5-2.8% backorder) — dual-sourcing strategy mitigates single-GPO risk.
    Recommend: activate compounding-pharmacy partnerships for oncology drugs, pre-position 90 days inventory on sole-source drugs, and establish secondary GPO contract for bottom-tercile drugs.
  </div>
</div>"""

    body = ck_source_purpose(
        purpose="Flag drug-shortage / supply-chain exposure: real national FDA "
                "shortage landscape (live) above; an illustrative supplier/GPO "
                "planning model below.",
        universe="cms", confidence="derived",
        source="openFDA drug shortages (live snapshot) + illustrative model",
        next_action="Search a drug in the FDA section") + body
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Drug Shortage", active_nav="/drug-shortage",
        editorial_intro={
            "eyebrow": "DRUG SHORTAGE",
            "headline": "What the drug shortage page reveals on this deal.",
            "italic_word": "reveals",
        })
