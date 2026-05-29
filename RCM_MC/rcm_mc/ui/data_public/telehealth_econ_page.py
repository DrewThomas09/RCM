"""Telehealth Economics Analyzer — /telehealth-econ."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor, ck_scatter


def _prod_scatter(items):
    """Quadrant — visits/provider/day vs revenue/provider, so high-volume
    high-revenue specialties (upper-right) and sub-scale ones separate."""
    import statistics
    pts, xs, ys = [], [], []
    for p in items:
        tn = ('positive' if p.attrition_rate_pct < 0.12 else 'teal' if p.attrition_rate_pct < 0.20 else 'warning')
        pts.append((p.visits_per_provider_day, p.avg_rev_per_provider_k, getattr(p, 'specialty', ''), tn))
        xs.append(p.visits_per_provider_day); ys.append(p.avg_rev_per_provider_k)
    return ck_scatter(
        pts, x_label='Visits / provider / day', y_label='Revenue / provider ($k)',
        x_ref=(statistics.median(xs) if xs else None), y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = a specialty · upper-right = high volume + high revenue · tone = attrition',
    )


def _visits_chart(items) -> str:
    """Lead chart for visit-type economics — annual revenue contribution
    per visit category, ranked, so a partner sees where the revenue
    concentrates before reading the per-line P&L. Bar width = share of
    total revenue; tone tracks the table's gross-margin coloring
    (>=65% high / >=55% mid / else low) so the read is "where the money
    is" overlaid with "how profitable it is".
    """
    total = sum(v.annual_revenue_mm for v in items) or 1.0
    ranked = sorted(items, key=lambda v: v.annual_revenue_mm, reverse=True)
    rows = []
    for v in ranked:
        tone = ("positive" if v.gross_margin_pct >= 0.65
                else "teal" if v.gross_margin_pct >= 0.55 else "warning")
        rows.append(ck_bar_row(
            v.visit_type,
            f"${v.annual_revenue_mm:,.1f}M",
            v.annual_revenue_mm / total * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of annual revenue · value = revenue ($M) · '
        'tone = gross-margin tier (green &ge;65% · teal &ge;55% · amber below)</div>'
        '</div>'
    )


def _visits_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Visit Type","left"),("Reimbursement","right"),("Direct Cost","right"),("Gross Margin","right"),
            ("GM %","right"),("Duration (min)","right"),("Annual Volume","right"),("Annual Revenue ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gm_c = pos if v.gross_margin_pct >= 0.65 else (acc if v.gross_margin_pct >= 0.55 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.visit_type)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${v.avg_reimbursement:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${v.direct_cost:,.2f}</td>',
            f'{ck_data_cell(f"""${v.gross_margin:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gm_c};font-weight:700">{v.gross_margin_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{v.avg_duration_min}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{v.annual_volume:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${v.annual_revenue_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _prod_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Specialty","left"),("FTE","right"),("Visits/Provider/Day","right"),("Utilization","right"),
            ("Avg Rev/Provider ($k)","right"),("Attrition","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        att_c = pos if p.attrition_rate_pct < 0.15 else (acc if p.attrition_rate_pct < 0.20 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.specialty)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{p.providers_fte:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.visits_per_provider_day}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{p.utilization_pct * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${p.avg_rev_per_provider_k:,.0f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{att_c};font-weight:600">{p.attrition_rate_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _parity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("State","left"),("Parity","left"),("Medicaid","left"),("Medicare","left"),("Commercial","left"),("Sunset Risk","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    risk_c = {"low": pos, "medium": warn, "high": neg}
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(p.sunset_risk, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.state)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(p.parity_status)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(p.medicaid_coverage)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(p.medicare_extension)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(p.commercial_parity)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.sunset_risk)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tech_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    cols = [("Component","left"),("Annual Cost ($M)","right"),("% of Revenue","right"),("Vendor","left"),("Renewal","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.component)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${t.annual_cost_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{t.pct_of_revenue * 100:.2f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{_html.escape(t.vendor)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.renewal_status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cliffs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    cols = [("Policy","left"),("Status","left"),("Expiration","left"),("Revenue at Risk ($M)","right"),("Mitigation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.policy)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.current_status)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(c.expiration_date)}""", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if c.revenue_at_risk_mm > 0 else text_dim};font-weight:700">${c.revenue_at_risk_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.mitigation)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comp_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Company","left"),("Visit Type","left"),("Price/Visit","right"),("Subscription/mo","right"),("Status","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.company)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.visit_type)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.price_per_visit:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.subscription_monthly:,.2f}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _places_access_panel() -> str:
    """Real CDC PLACES access-barrier anchor — telehealth's core value
    proposition is overcoming transportation and access barriers, which
    PLACES measures directly (lack of transportation, uninsured, fair/poor
    health) at full-population scale. The visit-economics model below is
    illustrative; this panel is real public CDC data, grounding the
    telehealth demand thesis in observed access barriers."""
    from rcm_mc.data import cdc_places_agg as _c
    summ = _c.places_equity_summary()
    if not summ.get("national_prevalence_pct"):
        return ""
    nat = summ["national_prevalence_pct"]
    labels = _c.measure_labels()

    border = P["border"]; tprim = P["text"]; tdim = P["text_dim"]; acc = P["accent"]
    show = ["lack_transportation", "uninsured_18_64", "fair_poor_health", "routine_checkup"]
    cards = "".join(
        f'<div style="text-align:center;padding:0 10px">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:18px;color:{tprim};'
        f'font-variant-numeric:tabular-nums">{nat.get(k,0):.1f}%</div>'
        f'<div style="font-size:9px;color:{tdim}">{_html.escape(labels.get(k,k))}</div></div>'
        for k in show if nat.get(k) is not None
    )
    # states with the worst transportation access = highest telehealth demand
    top = _c.top_states_by("lack_transportation", 6)
    mx = max((float(t["lack_transportation"]) for t in top), default=1.0) or 1.0
    rows = "".join(
        f'<tr>'
        f'<td style="padding:3px 8px;font-family:JetBrains Mono,monospace;font-size:11px;color:{tprim}">{_html.escape(str(t["state"]))}</td>'
        f'<td style="padding:3px 8px;width:50%">'
        f'<svg width="100%" height="9" preserveAspectRatio="none" viewBox="0 0 100 9">'
        f'<rect x="0" y="1" width="{int(float(t["lack_transportation"])/mx*100)}" height="7" fill="{acc}" opacity="0.75"/></svg></td>'
        f'<td style="padding:3px 8px;text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;'
        f'font-variant-numeric:tabular-nums;color:{tprim}">{float(t["lack_transportation"]):.1f}%</td>'
        f'</tr>'
        for t in top
    )
    rel = summ.get("release", ""); n_cty = int(summ.get("counties", 0))
    return f'''
<div style="background:{P["panel"]};border:1px solid {border};border-left:3px solid {acc};
  padding:14px 16px;margin-bottom:16px">
  <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px">
    Real CDC PLACES access barriers &mdash; the telehealth demand driver
    <span style="color:{acc};font-weight:600"> · LIVE</span>
  </div>
  <div style="display:flex;gap:6px;justify-content:space-between;margin-bottom:12px;
    border-bottom:1px solid {border};padding-bottom:10px">{cards}</div>
  <div>
    <div style="font-size:9px;color:{P["text_faint"]};margin-bottom:4px">HIGHEST TRANSPORTATION-BARRIER STATES (% OF ADULTS) &mdash; TOP TELEHEALTH DEMAND</div>
    <table style="width:100%;border-collapse:collapse">{rows}</table>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P["text_faint"]}">
    CDC PLACES {rel} ({n_cty:,} counties, model-based, population-weighted).
    Real FULL-POPULATION access-barrier prevalence &mdash; the visit-type
    economics, parity, and productivity figures below are illustrative.
  </div>
</div>'''


def render_telehealth_econ(params: dict = None) -> str:
    from rcm_mc.data_public.telehealth_econ import compute_telehealth_econ
    r = compute_telehealth_econ()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Annual Visits", f"{r.total_visits_annual:,}", "", "") +
        ck_kpi_block("Annual Revenue", f"${r.annual_revenue_mm:,.1f}M", "", "") +
        ck_kpi_block("Blended GM", f"{r.blended_gross_margin_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Provider FTE", f"{r.total_provider_fte:,.0f}", "", "") +
        ck_kpi_block("States Operating", str(r.states_operating), "", "") +
        ck_kpi_block("Visit Types", str(len(r.visits)), "", "") +
        ck_kpi_block("Reg Cliffs", str(sum(1 for c in r.cliffs if c.revenue_at_risk_mm > 0)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    v_chart = _visits_chart(r.visits)
    v_tbl = _visits_table(r.visits)
    p_tbl = _prod_table(r.productivity)
    p_scatter = _prod_scatter(r.productivity)
    pa_tbl = _parity_table(r.parity)
    t_tbl = _tech_table(r.tech_stack)
    c_tbl = _cliffs_table(r.cliffs)
    co_tbl = _comp_table(r.competitors)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_cliff_risk = sum(c.revenue_at_risk_mm for c in r.cliffs)
    page_title = ck_page_title(
        "Telehealth Economics Analyzer",
        eyebrow="TELEHEALTH ECON",
        meta=f"""Visit-level P&amp;L · provider productivity · state parity · tech stack · PHE cliff exposure · DTC comparables — {r.corpus_deal_count:,} corpus deals""",
    )
    
    value_anchor = ck_value_anchor(
        "Telehealth Economics",
        f"${r.annual_revenue_mm:,.1f}M revenue",
        delta=f"{r.blended_gross_margin_pct * 100:.1f}% blended GM · {r.total_visits_annual:,} annual visits",
        opportunity=f"${total_cliff_risk:,.1f}M regulatory-cliff exposure",
        tone="teal",
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  {_places_access_panel()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Visit-Type Economics (P&amp;L by Visit Category)</div>{v_chart}{v_tbl}</div>
  <div style="{cell}"><div style="{h3}">Provider Productivity by Specialty</div>{p_scatter}{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">State-Level Payer Parity Status</div>{pa_tbl}</div>
  <div style="{cell}"><div style="{h3}">Technology Stack Cost Structure</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Regulatory Cliff Exposure (PHE / Ryan Haight / Home Originating)</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Comparable DTC / Telehealth Platforms</div>{co_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Telehealth Thesis:</strong> {r.total_visits_annual:,} annual visits produce ${r.annual_revenue_mm:,.1f}M at {r.blended_gross_margin_pct * 100:.1f}% gross margin.
    Behavioral health and specialty consult are highest-margin visit types; async primary care has highest volume.
    {r.total_provider_fte:,.0f} provider FTE across {r.states_operating} states with IMLC coverage. Cumulative regulatory cliff exposure ${total_cliff_risk:,.1f}M
    concentrated in PHE-era Medicare flexibilities and DEA Ryan Haight telecontrolled-substance prescribing. Mitigation via bipartisan TCEA legislative push
    and in-person touchpoint model for DEA compliance. Behavioral-health telehealth parity is now permanent — the safest revenue stream post-PHE.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Telehealth Econ", active_nav="/telehealth-econ",
        editorial_intro={
            "eyebrow": "TELEHEALTH ECON",
            "headline": "What the telehealth econ page reveals on this deal.",
            "italic_word": "reveals",
        })
