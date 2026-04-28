"""340B Drug Pricing Analyzer — /drug-pricing-340b."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _entities_table(entities) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("ID","left"),("Type","center"),("Name","left"),("Drug Spend ($M)","right"),
            ("Ceiling Spread ($M)","right"),("CP Count","right"),("Child Sites","right"),
            ("Margin ($M)","right"),("Audit Risk","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    stat_c = {"clean": pos, "minor finding": warn, "monitoring": warn}
    for i, e in enumerate(entities):
        rb = panel_alt if i % 2 == 0 else bg
        risk_c = neg if e.audit_risk_score >= 60 else (warn if e.audit_risk_score >= 40 else text_dim)
        sc = stat_c.get(e.compliance_status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.entity_id)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{acc};border:1px solid {acc};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.entity_type)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(e.name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${e.annual_drug_spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${e.ceiling_price_spread_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.contract_pharmacy_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.child_sites}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.program_margin_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{risk_c};font-weight:600">{e.audit_risk_score}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.compliance_status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _drugs_table(drugs) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Drug Category","left"),("Volume (units)","right"),("WAC $/unit","right"),
            ("Ceiling $/unit","right"),("Discount","right"),("Annual Savings ($M)","right"),("Share of Spend","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(drugs):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.annual_volume_units:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${d.wac_per_unit:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${d.ceiling_price_per_unit:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{d.discount_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${d.annual_savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.share_of_spend_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pharmacy_table(pharms) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Pharmacy Type","left"),("Locations","right"),("Claims/mo","right"),
            ("Spread/Claim","right"),("Monthly Margin ($k)","right"),("Annual ($M)","right"),("Integrity Risk","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    risk_c = {"low": text_dim, "medium": warn, "high": neg}
    for i, p in enumerate(pharms):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(p.integrity_risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.pharmacy_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.location_count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.claims_per_month:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.avg_spread_per_claim:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.monthly_margin_k:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.annual_margin_mm:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.integrity_risk)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _audits_table(audits) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Audit Area","left"),("Severity","center"),("Exposure ($M)","right"),
            ("Remediation (days)","right"),("Last HRSA Visit","left"),("Status","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sev_c = {"clean": pos, "minor": text_dim, "moderate": warn, "severe": neg}
    for i, a in enumerate(audits):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(a.finding_severity, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(a.audit_area)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(a.finding_severity)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if a.exposure_mm > 0 else text_dim};font-weight:{"600" if a.exposure_mm > 0 else "400"}">${a.exposure_mm / 1000:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.remediation_days}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(a.last_hrsa_visit)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(a.status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _manufacturer_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Manufacturer","left"),("Restricted Products","right"),("Restriction Type","left"),
            ("Annual Impact ($M)","right"),("Workaround","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        w_c = pos if m.workaround_available else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.manufacturer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{m.restricted_products}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.restriction_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">${m.annual_impact_mm:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{w_c};font-weight:600">{"AVAILABLE" if m.workaround_available else "NONE"}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _medicaid_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("State","left"),("Carve Status","left"),("Avg MAC Rate","right"),
            ("Duplicate Discount Risk","center"),("Gross Margin ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    risk_c = {"low": text_dim, "medium": warn, "high": neg}
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(m.duplicate_discount_risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(m.carve_status)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{m.avg_mac_rate * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.duplicate_discount_risk)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${m.gross_margin_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">340B Drug Pricing Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Covered entities · ceiling price · contract pharmacy · HRSA audits · V28 &amp; V24 · Medicaid carve-in/out — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Drug Category Savings Map</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Covered Entity Inventory — DSH / FQHC / SCH / CAH / PED / Ryan White</div>{entities_tbl}</div>
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

    return chartis_shell(body, "340B Drug Pricing", active_nav="/drug-pricing-340b")
