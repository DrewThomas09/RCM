"""340B Pharmacy Program Tracker — /tracker-340b."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor, ck_scatter


def _entity_scatter(items):
    """Quadrant — 340B spend vs savings captured per covered entity, so
    high-capture (and low-compliance) entities stand out."""
    import statistics
    pts, xs = [], []
    for e in items:
        tn = ('positive' if e.compliance_score >= 9 else 'teal' if e.compliance_score >= 7 else 'warning')
        pts.append((e.annual_340b_spend_m, e.annual_savings_m, e.entity_name, tn)); xs.append(e.annual_340b_spend_m)
    return ck_scatter(
        pts, x_label='340B spend ($M)', y_label='Annual savings ($M)',
        x_ref=(statistics.median(xs) if xs else None),
        caption='Each dot = a covered entity · higher = more savings captured · tone = compliance score',
    )


def _entity_chart(items) -> str:
    """Lead chart for the covered-entity table — entities ranked by
    annual 340B savings so the biggest program value surfaces first. Bar
    width = share of total savings; value = annual savings ($M); tone
    marks compliance health (>=8.8 green · >=8.3 teal · below amber).
    Full entity grid stays directly below.
    """
    total = sum(e.annual_savings_m for e in items) or 1.0
    ranked = sorted(items, key=lambda e: e.annual_savings_m, reverse=True)
    rows = []
    for e in ranked:
        tone = ("positive" if e.compliance_score >= 8.8 else "teal"
                if e.compliance_score >= 8.3 else "warning")
        rows.append(ck_bar_row(
            e.entity_name,
            f"${e.annual_savings_m:,.1f}M",
            e.annual_savings_m / total * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of total 340B savings · value = annual savings ($M) · '
        'tone = compliance score (green &ge;8.8 · teal &ge;8.3 · amber below)</div>'
        '</div>'
    )


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
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if e.compliance_score >= 8.8 else (acc if e.compliance_score >= 8.3 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.deal)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:260px">{_html.escape(e.entity_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:700">{_html.escape(e.entity_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(e.eligibility_basis)}</td>',
            f'{ck_data_cell(f"""{_html.escape(e.enrolled_date)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.ce_id)}</td>',
            f'{ck_data_cell(f"""${e.annual_340b_spend_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${e.annual_savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{e.compliance_score:.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pharmacy_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Covered Entity","left"),("Pharmacy","left"),("Arrangement","center"),
            ("Dispense Vol (K)","right"),("Admin Fee","right"),("Share to CE","right"),("Savings ($M)","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(p.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.covered_entity)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.pharmacy_chain)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text}">{_html.escape(p.arrangement_type)}</td>',
            f'{ck_data_cell(f"""{p.dispense_volume_k}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{p.admin_fee_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{p.share_to_ce_pct * 100:.0f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${p.annual_savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _restriction_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Manufacturer","left"),("Effective","right"),("Scope","left"),("Deals","right"),
            ("Exposure ($M)","right"),("Litigation Status","left"),("Workaround","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.manufacturer)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(r.effective_date)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(r.scope)}</td>',
            f'{ck_data_cell(f"""{r.affected_deals}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${r.annual_exposure_m:.1f}M""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{P["warning"]}">{_html.escape(r.litigation_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.workaround)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _audit_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Covered Entity","left"),("Audit Type","left"),("Date","right"),("Auditor","left"),
            ("Findings","right"),("Repayment ($M)","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(a.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.covered_entity)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.audit_type)}</td>',
            f'{ck_data_cell(f"""{_html.escape(a.audit_date)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.auditor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if a.findings > 0 else text_dim};font-weight:700">{a.findings}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if a.repayment_m > 1 else text_dim};font-weight:700">${a.repayment_m:.2f}M</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(a.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _breakdown_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Drug Category","left"),("Utilizers","right"),("Gross WAC ($M)","right"),
            ("Net Cost ($M)","right"),("Savings ($M)","right"),("Savings %","right"),("Rebates ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sp_c = pos if s.savings_pct >= 0.30 else (acc if s.savings_pct >= 0.25 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.drug_category)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.utilizers:,}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${s.gross_wac_m:.1f}M""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${s.net_cost_m:.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sp_c};font-weight:700">{s.savings_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${s.rebate_capture_m:.1f}M""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _update_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Topic","left"),("Effective","right"),("Description","left"),("Portfolio Impact ($M)","right"),("Action","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, u in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if u.portfolio_impact_m > 0 else (neg if u.portfolio_impact_m < 0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700;max-width:320px">{_html.escape(u.topic)}</td>',
            f'{ck_data_cell(f"""{_html.escape(u.effective_date)}""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(u.description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">${u.portfolio_impact_m:+.2f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(u.action_required)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _partd_drug_panel() -> str:
    """Real CMS Part D drug-spend / price-inflation anchor — the drug-cost
    pressure 340B economics track. National spend + top drugs are real public
    CMS data; the deal's 340B program/savings model below is illustrative."""
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
      <div style="font-size:10px;color:{tdim}">median price CAGR '19–'23</div>
    </div>
    <div>
      <div style="font-size:9px;color:{P["text_faint"]};margin-bottom:4px">LARGEST DRUGS BY PART D SPEND</div>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P["text_faint"]}">
    CMS Medicare Part D Spending by Drug ({yr}). Real retail drug spend &mdash; NOT
    340B ceiling prices and NOT this deal's program; the 340B figures below are illustrative.
  </div>
</div>'''


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

    e_chart = _entity_chart(r.entities)
    e_scatter = _entity_scatter(r.entities)
    e_tbl = _entity_table(r.entities)
    value_anchor = ck_value_anchor(
        "340B Program Value",
        f"${r.total_annual_savings_m:,.1f}M annual savings",
        delta=f"${r.total_annual_spend_m:,.0f}M spend · {r.effective_savings_rate * 100:.0f}% effective savings · {r.total_entities} entities · compliance {r.avg_compliance_score:.1f}",
        tone="positive",
    )
    p_tbl = _pharmacy_table(r.pharmacies)
    res_tbl = _restriction_table(r.restrictions)
    a_tbl = _audit_table(r.audits)
    b_tbl = _breakdown_table(r.breakdown)
    u_tbl = _update_table(r.updates)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_restriction_exposure = sum(r2.annual_exposure_m for r2 in r.restrictions)
    total_audit_repayment = sum(a.repayment_m for a in r.audits)

    page_title = ck_page_title(
        "340B Pharmacy Program Tracker",
        eyebrow="TRACKER 340B",
        meta=f"""{r.total_entities} covered entities · ${r.total_annual_spend_m:,.1f}M 340B spend · ${r.total_annual_savings_m:,.1f}M savings ({r.effective_savings_rate * 100:.1f}%) · {r.total_contract_pharmacies} contract pharmacies · {r.restricted_manufacturers} mfr restrictions — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  {_partd_drug_panel()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Covered Entities — Portfolio Registration</div>{e_chart}{e_scatter}{e_tbl}</div>
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

    return chartis_shell(body, "340B Tracker", active_nav="/tracker-340b",
        editorial_intro={
            "eyebrow": "TRACKER 340B",
            "headline": "What the tracker 340b page reveals on this deal.",
            "italic_word": "reveals",
        })
