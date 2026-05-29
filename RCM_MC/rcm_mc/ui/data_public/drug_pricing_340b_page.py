"""340B Drug Pricing Analyzer — /drug-pricing-340b."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row, ck_value_anchor, ck_illustrative_note


def _entities_chart(items):
    """Summary chart — covered entities by 340B program margin (tone by audit risk)."""
    def _tone(e):
        if e.audit_risk_score >= 70: return "negative"
        if e.audit_risk_score >= 45: return "warning"
        return "teal"
    top = sorted(items, key=lambda e: e.program_margin_mm, reverse=True)
    total = sum(e.program_margin_mm for e in top) or 1.0
    rows = [ck_bar_row(f"{e.name} · {e.entity_type}",
            f"${e.program_margin_mm:,.1f}M margin · risk {e.audit_risk_score:.0f}",
            e.program_margin_mm / total * 100.0, tone=_tone(e)) for e in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of 340B program margin '
            '· value = margin ($M) + audit risk · tone = audit risk</div></div>')


def _entities_table(entities) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("ID","left"),("Type","center"),("Name","left"),("Drug Spend ($M)","right"),
            ("Ceiling Spread ($M)","right"),("CP Count","right"),("Child Sites","right"),
            ("Margin ($M)","right"),("Audit Risk","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    stat_c = {"clean": pos, "minor finding": warn, "monitoring": warn}
    for i, e in enumerate(entities):
        rb = panel_alt if i % 2 == 0 else bg
        risk_c = neg if e.audit_risk_score >= 60 else (warn if e.audit_risk_score >= 40 else text_dim)
        sc = stat_c.get(e.compliance_status, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.entity_id)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{acc};border:1px solid {acc};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.entity_type)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{_html.escape(e.name)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.annual_drug_spend_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${e.ceiling_price_spread_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{e.contract_pharmacy_count}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{e.child_sites}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.program_margin_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{risk_c};font-weight:600">{e.audit_risk_score}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.compliance_status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _drugs_table(drugs) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Drug Category","left"),("Volume (units)","right"),("WAC $/unit","right"),
            ("Ceiling $/unit","right"),("Discount","right"),("Annual Savings ($M)","right"),("Share of Spend","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(drugs):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{d.annual_volume_units:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${d.wac_per_unit:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${d.ceiling_price_per_unit:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{d.discount_pct * 100:.1f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${d.annual_savings_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{d.share_of_spend_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pharmacy_table(pharms) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Pharmacy Type","left"),("Locations","right"),("Claims/mo","right"),
            ("Spread/Claim","right"),("Monthly Margin ($k)","right"),("Annual ($M)","right"),("Integrity Risk","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    risk_c = {"low": text_dim, "medium": warn, "high": neg}
    for i, p in enumerate(pharms):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(p.integrity_risk, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.pharmacy_type)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{p.location_count:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.claims_per_month:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.avg_spread_per_claim:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${p.monthly_margin_k:,.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${p.annual_margin_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.integrity_risk)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _audits_table(audits) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Audit Area","left"),("Severity","center"),("Exposure ($M)","right"),
            ("Remediation (days)","right"),("Last HRSA Visit","left"),("Status","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    sev_c = {"clean": pos, "minor": text_dim, "moderate": warn, "severe": neg}
    for i, a in enumerate(audits):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(a.finding_severity, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.audit_area)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(a.finding_severity)}</span>""", align="center")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if a.exposure_mm > 0 else text_dim};font-weight:{"600" if a.exposure_mm > 0 else "400"}">${a.exposure_mm / 1000:,.3f}</td>',
            f'{ck_data_cell(f"""{a.remediation_days}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(a.last_hrsa_visit)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(a.status)}""", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _manufacturer_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Manufacturer","left"),("Restricted Products","right"),("Restriction Type","left"),
            ("Annual Impact ($M)","right"),("Workaround","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        w_c = pos if m.workaround_available else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.manufacturer)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{m.restricted_products}""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.restriction_type)}</td>',
            f'{ck_data_cell(f"""${m.annual_impact_mm:,.2f}""", align="right", mono=True, tone="neg", weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{w_c};font-weight:600">{"AVAILABLE" if m.workaround_available else "NONE"}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _medicaid_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("State","left"),("Carve Status","left"),("Avg MAC Rate","right"),
            ("Duplicate Discount Risk","center"),("Gross Margin ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    risk_c = {"low": text_dim, "medium": warn, "high": neg}
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(m.duplicate_discount_risk, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.state)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(m.carve_status)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{m.avg_mac_rate * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.duplicate_discount_risk)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${m.gross_margin_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _drugs_svg(drugs) -> str:
    if not drugs: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 60
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    sorted_d = sorted(drugs, key=lambda d: d.annual_savings_mm, reverse=True)
    max_v = max(d.annual_savings_mm for d in sorted_d) or 1
    bg = P["panel"]; pos = P["positive"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(sorted_d)
    bar_w = (inner_w - (n - 1) * 4) / n
    bars = []
    for i, d in enumerate(sorted_d):
        x = pad_l + i * (bar_w + 4)
        bh = d.annual_savings_mm / max_v * inner_h
        y = (h - pad_b) - bh
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{pos}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{text_dim}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${d.annual_savings_mm:.0f}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="8" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(d.category[:12])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 24}" fill="{text_faint}" font-size="8" text-anchor="middle" font-family="JetBrains Mono,monospace">{d.discount_pct * 100:.0f}% off</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">340B Annual Savings by Drug Category ($M)</text></svg>')


def _partd_drug_panel() -> str:
    """Real CMS Part D drug-spend / price-inflation anchor — 340B economics
    are driven by drug prices and their growth. National Part D spend + the
    most expensive and fastest-inflating drugs are real public CMS data; the
    deal's 340B savings/covered-entity model below is illustrative."""
    from rcm_mc.data import partd_drug as _pd
    summ = _pd.partd_drug_summary()
    if not summ.get("total_spending_2023"):
        return ""
    top = _pd.top_drugs_by_spend(6)

    border = P["border"]; tprim = P["text"]; tdim = P["text_dim"]; acc = P["accent"]
    mx = max((float(t.get("spend_2023") or 0) for t in top), default=1.0) or 1.0
    rows = "".join(
        f'<tr>'
        f'<td style="padding:3px 8px;font-family:JetBrains Mono,monospace;font-size:11px;color:{tprim}">{_html.escape(str(t.get("brand","")))}</td>'
        f'<td style="padding:3px 8px;width:42%">'
        f'<svg width="100%" height="9" preserveAspectRatio="none" viewBox="0 0 100 9">'
        f'<rect x="0" y="1" width="{int(float(t.get("spend_2023") or 0)/mx*100)}" height="7" fill="{acc}" opacity="0.75"/></svg></td>'
        f'<td style="padding:3px 8px;text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;'
        f'font-variant-numeric:tabular-nums;color:{tprim}">${float(t.get("spend_2023") or 0)/1e9:,.1f}B</td>'
        f'</tr>'
        for t in top
    )
    total_b = float(summ.get("total_spending_2023", 0)) / 1e9
    n_drugs = int(summ.get("drugs", 0))
    med_cagr = float(summ.get("median_price_cagr_19_23") or 0) * 100
    n_infl = int(summ.get("drugs_price_up_over_10pct_cagr", 0))
    yr = summ.get("data_year", "")
    return f'''
<div style="background:{P["panel"]};border:1px solid {border};border-left:3px solid {acc};
  padding:14px 16px;margin-bottom:16px">
  <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px">
    Real CMS Part D drug spend &amp; price inflation &mdash; the 340B cost driver
    <span style="color:{acc};font-weight:600"> · LIVE</span>
  </div>
  <div style="display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start">
    <div style="white-space:nowrap">
      <div style="font-family:JetBrains Mono,monospace;font-size:20px;color:{tprim};
        font-variant-numeric:tabular-nums">${total_b:,.0f}B</div>
      <div style="font-size:10px;color:{tdim};margin-bottom:8px">Part D drug spend, {yr}<br>({n_drugs:,} drugs)</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:13px;color:{tprim};
        font-variant-numeric:tabular-nums">{med_cagr:.1f}%</div>
      <div style="font-size:10px;color:{tdim}">median price CAGR '19–'23<br>({n_infl:,} drugs &gt;10%/yr)</div>
    </div>
    <div>
      <div style="font-size:9px;color:{P["text_faint"]};margin-bottom:4px">LARGEST DRUGS BY PART D SPEND</div>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P["text_faint"]}">
    CMS Medicare Part D Spending by Drug ({yr}). Real retail drug spend + per-unit
    price growth &mdash; the cost pressure 340B addresses. NOT 340B ceiling prices
    and NOT this deal's formulary; the savings model below is illustrative.
  </div>
</div>'''


def render_drug_pricing_340b(params: dict = None) -> str:
    params = params or {}

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    platform = params.get("platform", "Health System")
    entities = _i("entities", 25)

    from rcm_mc.data_public.drug_pricing_340b import compute_drug_pricing_340b
    r = compute_drug_pricing_340b(platform_type=platform, total_entities=entities)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("Covered Entities", str(r.total_covered_entities), "", "") +
        ck_kpi_block("Annual Drug Spend", f"${r.total_drug_spend_mm:,.0f}M", "", "") +
        ck_kpi_block("Ceiling Savings", f"${r.total_program_savings_mm:,.0f}M", "", "") +
        ck_kpi_block("Program Margin", f"${r.total_margin_mm:,.0f}M", "", "") +
        ck_kpi_block("Margin %", f"{r.program_margin_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Contract Pharmacy", f"{r.contract_pharmacy_network_size:,}", "", "") +
        ck_kpi_block("Audit Risk (wtd)", f"{r.audit_risk_weighted:.1f}", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _drugs_svg(r.drugs)
    entities_tbl = _entities_table(r.entities)
    entities_chart = _entities_chart(r.entities)
    drugs_tbl = _drugs_table(r.drugs)
    pharms_tbl = _pharmacy_table(r.pharmacies)
    audit_tbl = _audits_table(r.audits)
    manuf_tbl = _manufacturer_table(r.manufacturers)
    medicaid_tbl = _medicaid_table(r.medicaid)

    platforms = ["Health System", "FQHC Network", "Oncology Group", "Community Health"]
    plat_opts = "".join(f'<option value="{_html.escape(s)}"{" selected" if s == platform else ""}>{_html.escape(s)}</option>' for s in platforms)

    form = f"""
<form method="GET" action="/drug-pricing-340b" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Platform Type<select name="platform" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{plat_opts}</select></label>
  <label style="font-size:11px;color:{text_dim}">Total Entities<input name="entities" value="{entities}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    manuf_impact = sum(m.annual_impact_mm for m in r.manufacturers)
    audit_exposure = sum(a.exposure_mm for a in r.audits) / 1000

    page_title = ck_page_title(
        "340B Drug Pricing Analyzer",
        eyebrow="DRUG PRICING 340B",
        meta=f"{r.total_covered_entities} covered entities on {platform} platform · ${r.total_drug_spend_mm:,.0f}M drug spend → ${r.total_program_savings_mm:,.0f}M ceiling savings · ${r.total_margin_mm:,.0f}M program margin at {r.program_margin_pct * 100:.1f}% · {r.audit_risk_weighted:.1f}/100 weighted audit risk",
    )

    # Lead takeaway — surface the computed 340B program value (ceiling
    # savings → program margin), otherwise buried as KPIs #3-4 and in
    # the bottom thesis. All figures come from compute_drug_pricing_340b().
    lead_anchor = ck_value_anchor(
        "340B PROGRAM VALUE",
        f"${r.total_program_savings_mm:,.0f}M ceiling savings",
        delta=f"{r.program_margin_pct * 100:.1f}% program margin",
        opportunity=f"${r.total_margin_mm:,.0f}M program margin",
        target=(
            f"${r.total_drug_spend_mm:,.0f}M spend · "
            f"{r.total_covered_entities} entities"
        ),
        tone="teal",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("340B savings figures")}
  {_partd_drug_panel()}
  {lead_anchor}
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Drug Category Savings Map</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Covered Entity Inventory — DSH / FQHC / SCH / CAH / PED / Ryan White</div>{entities_chart}{entities_tbl}</div>
  <div style="{cell}"><div style="{h3}">Drug Category Economics — WAC vs 340B Ceiling Price</div>{drugs_tbl}</div>
  <div style="{cell}"><div style="{h3}">Contract Pharmacy Network — Spread Capture by Type</div>{pharms_tbl}</div>
  <div style="{cell}"><div style="{h3}">Compliance Audit Inventory — HRSA Program Integrity</div>{audit_tbl}</div>
  <div style="{cell}"><div style="{h3}">Manufacturer Restriction Exposure</div>{manuf_tbl}</div>
  <div style="{cell}"><div style="{h3}">State Medicaid Interaction — Carve-In vs Carve-Out</div>{medicaid_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">340B Thesis:</strong> {r.total_covered_entities} covered entities across {_html.escape(platform)} platform;
    ${r.total_drug_spend_mm:,.0f}M WAC-equivalent drug spend produces ${r.total_program_savings_mm:,.0f}M 340B ceiling-price savings
    ({(r.total_program_savings_mm / r.total_drug_spend_mm) * 100:.0f}% of spend) and ${r.total_margin_mm:,.0f}M net margin ({r.program_margin_pct * 100:.1f}%).
    Contract pharmacy network of {r.contract_pharmacy_network_size:,} retail locations captures spread; weighted audit risk {r.audit_risk_weighted:.1f}/100.
    Manufacturer restrictions (Lilly, Sanofi, Novartis) erode ~${manuf_impact:,.1f}M/yr; audit exposure ${audit_exposure:,.2f}M if findings sustained.
    Diversion and duplicate-discount are material deal-breakers — ongoing compliance program required.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "340B Drug Pricing", active_nav="/drug-pricing-340b",
        editorial_intro={
            "eyebrow": "DRUG PRICING 340B",
            "headline": "What the drug pricing 340b page reveals on this deal.",
            "italic_word": "reveals",
        })
