"""340B Pharmacy Program Tracker — /tracker-340b."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _status_color(s: str) -> str:
    return {
        "active": P["positive"],
        "repaid": P["positive"],
        "repaid + CAP complete": P["positive"],
        "resolved": P["positive"],
        "clean": P["positive"],
        "finalized": P["accent"],
        "repayment in progress": P["warning"],
        "litigation ongoing": P["warning"],
        "HRSA enforcement on hold": P["warning"],
    }.get(s, P["text_dim"])


def _entity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Entity","left"),("Type","center"),("Basis","left"),
            ("Enrolled","right"),("CE ID","center"),("Spend ($M)","right"),("Savings ($M)","right"),("Compliance","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if e.compliance_score >= 8.8 else (acc if e.compliance_score >= 8.3 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:260px">{_html.escape(e.entity_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:700">{_html.escape(e.entity_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(e.eligibility_basis)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(e.enrolled_date)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.ce_id)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${e.annual_340b_spend_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.annual_savings_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{e.compliance_score:.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pharmacy_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Covered Entity","left"),("Pharmacy","left"),("Arrangement","center"),
            ("Dispense Vol (K)","right"),("Admin Fee","right"),("Share to CE","right"),("Savings ($M)","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(p.status)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.covered_entity)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.pharmacy_chain)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text}">{_html.escape(p.arrangement_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{p.dispense_volume_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.admin_fee_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{p.share_to_ce_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.annual_savings_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _restriction_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Manufacturer","left"),("Effective","right"),("Scope","left"),("Deals","right"),
            ("Exposure ($M)","right"),("Litigation Status","left"),("Workaround","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.manufacturer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.effective_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(r.scope)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{r.affected_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${r.annual_exposure_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{P["warning"]}">{_html.escape(r.litigation_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.workaround)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _audit_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Covered Entity","left"),("Audit Type","left"),("Date","right"),("Auditor","left"),
            ("Findings","right"),("Repayment ($M)","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(a.status)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(a.covered_entity)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.audit_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(a.audit_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.auditor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if a.findings > 0 else text_dim};font-weight:700">{a.findings}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if a.repayment_m > 1 else text_dim};font-weight:700">${a.repayment_m:.2f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(a.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _breakdown_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Drug Category","left"),("Utilizers","right"),("Gross WAC ($M)","right"),
            ("Net Cost ($M)","right"),("Savings ($M)","right"),("Savings %","right"),("Rebates ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sp_c = pos if s.savings_pct >= 0.30 else (acc if s.savings_pct >= 0.25 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.drug_category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.utilizers:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${s.gross_wac_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.net_cost_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.savings_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sp_c};font-weight:700">{s.savings_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${s.rebate_capture_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _update_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Topic","left"),("Effective","right"),("Description","left"),("Portfolio Impact ($M)","right"),("Action","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, u in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if u.portfolio_impact_m > 0 else (neg if u.portfolio_impact_m < 0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700;max-width:320px">{_html.escape(u.topic)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{_html.escape(u.effective_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(u.description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">${u.portfolio_impact_m:+.2f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(u.action_required)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_tracker_340b(params: dict = None) -> str:
    from rcm_mc.data_public.tracker_340b import compute_tracker_340b
    r = compute_tracker_340b()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Covered Entities", str(r.total_entities), "", "") +
        ck_kpi_block("Annual Spend", f"${r.total_annual_spend_m:,.1f}M", "", "") +
        ck_kpi_block("Annual Savings", f"${r.total_annual_savings_m:,.1f}M", "", "") +
        ck_kpi_block("Savings Rate", f"{r.effective_savings_rate * 100:.1f}%", "", "") +
        ck_kpi_block("Contract Pharmacies", str(r.total_contract_pharmacies), "", "") +
        ck_kpi_block("Avg Compliance", f"{r.avg_compliance_score:.2f}", "/10", "") +
        ck_kpi_block("Mfr Restrictions", str(r.restricted_manufacturers), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    e_tbl = _entity_table(r.entities)
    p_tbl = _pharmacy_table(r.pharmacies)
    res_tbl = _restriction_table(r.restrictions)
    a_tbl = _audit_table(r.audits)
    b_tbl = _breakdown_table(r.breakdown)
    u_tbl = _update_table(r.updates)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_restriction_exposure = sum(r2.annual_exposure_m for r2 in r.restrictions)
    total_audit_repayment = sum(a.repayment_m for a in r.audits)

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">340B Pharmacy Program Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_entities} covered entities · ${r.total_annual_spend_m:,.1f}M 340B spend · ${r.total_annual_savings_m:,.1f}M savings ({r.effective_savings_rate * 100:.1f}%) · {r.total_contract_pharmacies} contract pharmacies · {r.restricted_manufacturers} mfr restrictions — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Covered Entities — Portfolio Registration</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Contract Pharmacy Arrangements</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Manufacturer Restrictions — Active</div>{res_tbl}</div>
  <div style="{cell}"><div style="{h3}">Drug-Category Savings Breakdown</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Audit History — HRSA + Manufacturer</div>{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">Regulatory Outlook</div>{u_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">340B Program Summary:</strong> {r.total_entities} covered entities across portfolio generate ${r.total_annual_savings_m:,.1f}M annual savings against ${r.total_annual_spend_m:,.1f}M 340B-eligible spend — effective {r.effective_savings_rate * 100:.1f}% blended savings rate.
    Highest-value entities: Oncology Specialty ($28.5M), Oncology Infusion Center ($32.0M), Regional Infusion Network ($22.5M) — oncology and specialty drug categories drive 80%+ of savings dollars.
    CE-owned in-house pharmacies capture 100% savings vs 72-85% for contract pharmacy arrangements; in-house dispensing deployed across Oncology, Infusion, and Derma platforms.
    Manufacturer restriction exposure: ${total_restriction_exposure:.1f}M annual revenue at risk from J&J, Merck, BMS, Lilly, AZ, Sanofi, Novartis, BI, Pfizer, Takeda conditions — 3rd Circuit 2025 ruling against HRSA expanded manufacturer leverage.
    Audit history clean: 11 audits YTD with ${total_audit_repayment:.2f}M total repayments (0.4% of program spend); top-quartile compliance vs industry benchmarks.
    Regulatory outlook mixed: Medicare Part B ASP+6% reinstatement (+$3.8M benefit), state non-discrimination laws (+$7M), offset by proposed patient definition narrowing (-$3.2M) and Medicaid duplicate prohibition (-$1.5M).
  </div>
</div>"""

    return chartis_shell(body, "340B Tracker", active_nav="/tracker-340b")
