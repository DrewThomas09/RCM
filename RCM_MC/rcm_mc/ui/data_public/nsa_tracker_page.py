"""No Surprises Act / IDR Tracker — /nsa-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row, ck_value_anchor


def _cases_chart(items) -> str:
    """Lead chart — top IDR cases ranked by claim amount (tone by award)."""
    def _tone(c):
        s = (c.idr_selected or "").lower()
        if "provider" in s: return "positive"
        if "payer" in s: return "negative"
        return "teal"
    top = sorted(items, key=lambda c: c.claim_amount, reverse=True)[:12]
    total = sum(c.claim_amount for c in top) or 1.0
    rows = [ck_bar_row(f"{c.case_id} · {c.specialty}", f"${c.claim_amount:,.0f}",
            c.claim_amount / total * 100.0, tone=_tone(c)) for c in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of top-12 claim value '
            '· value = claim ($) · tone = IDR award (green provider / red payer)</div></div>')


def _selected_color(s: str) -> str:
    return {"provider": P["positive"], "payer": P["warning"], "in progress": P["accent"]}.get(s, P["text_dim"])


def _status_color(s: str) -> str:
    if "provider" in s and "awarded" in s: return P["positive"]
    if "payer" in s and "awarded" in s: return P["warning"]
    if "pending" in s: return P["accent"]
    return P["text_dim"]


def _posture_color(p: str) -> str:
    if "aggressive" in p.lower(): return P["negative"]
    if "restrictive" in p.lower(): return P["negative"]
    if "moderate" in p.lower(): return P["accent"]
    if "improving" in p.lower(): return P["positive"]
    return P["text_dim"]


def _cases_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Case ID","left"),("Deal","left"),("Specialty","left"),("Payer","left"),
            ("Claim ($)","right"),("QPA ($)","right"),("Provider Offer","right"),("Payer Offer","right"),
            ("Selected","center"),("Days","right"),("Status","center"),("Admin Fee","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _selected_color(c.idr_selected)
        st_c = _status_color(c.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.case_id)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.specialty)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.payer)}</td>',
            f'{ck_data_cell(f"""${c.claim_amount:,.0f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.qpa:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.offer_provider:,.0f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${c.offer_payer:,.0f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{s_c};font-weight:700">{_html.escape(c.idr_selected).upper()}</td>',
            f'{ck_data_cell(f"""{c.decision_days if c.decision_days else "—"}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{st_c};border:1px solid {st_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${c.admin_fee:,.2f}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _payers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Payer","left"),("Cases","right"),("Provider Wins","right"),("Provider Win %","right"),
            ("Median Delta","right"),("QPA / Claim","right"),("Posture","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        po_c = _posture_color(p.posture)
        w_c = pos if p.provider_win_rate_pct >= 0.72 else (acc if p.provider_win_rate_pct >= 0.68 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.payer)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{p.cases_submitted:,}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.cases_won_by_provider:,}""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{w_c};font-weight:700">{p.provider_win_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{p.median_award_delta_pct * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.avg_qpa_vs_claim_ratio * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{po_c};border:1px solid {po_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.posture)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _deals_chart(items) -> str:
    """Summary chart — deals ranked by NSA revenue at risk (concentration view)."""
    def _tone(d):
        if d.revenue_at_risk_m >= 5: return "negative"
        if d.revenue_at_risk_m >= 2: return "warning"
        return "navy"
    top = sorted(items, key=lambda d: d.revenue_at_risk_m, reverse=True)
    total = sum(d.revenue_at_risk_m for d in top) or 1.0
    rows = [ck_bar_row(f"{d.deal} · {d.sector}", f"${d.revenue_at_risk_m:.1f}M",
            d.revenue_at_risk_m / total * 100.0, tone=_tone(d)) for d in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of portfolio NSA revenue at risk '
            '· value = at-risk ($M) · tone = exposure size</div></div>')


def _deals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Deal","left"),("Sector","left"),("OON Revenue ($M)","right"),("Annual IDR Cases","right"),
            ("Avg Case ($M)","right"),("Revenue at Risk ($M)","right"),("QPA vs Charge","right"),("Strategy","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'{ck_data_cell(f"""${d.out_of_network_revenue_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{d.annual_idr_cases:,}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${d.avg_case_value_m / 1000:,.2f}K""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${d.revenue_at_risk_m:.1f}M""", align="right", mono=True, tone="neg", weight=700)}',
            f'{ck_data_cell(f"""{d.qpa_vs_median_charge_pct * 100:.1f}%""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.strategy)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _emergency_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Entity","left"),("ED Visits","right"),("OON %","right"),("Avg Charge ($)","right"),
            ("Avg QPA ($)","right"),("Avg Collected ($)","right"),("Bad Debt %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        o_c = P["warning"] if e.oon_rate_pct >= 0.30 else (acc if e.oon_rate_pct >= 0.22 else text_dim)
        b_c = P["warning"] if e.bad_debt_pct >= 0.15 else (acc if e.bad_debt_pct >= 0.12 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.entity)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{e.ed_visits_annual:,}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{e.oon_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${e.avg_charge:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${e.avg_qpa:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.avg_collected:,.0f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">{e.bad_debt_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _reg_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Event","left"),("Date","right"),("Impact","left"),("Portfolio Impact ($M)","right"),("Status","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if r.portfolio_impact_m > 0 else (neg if r.portfolio_impact_m < 0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700;max-width:320px">{_html.escape(r.event)}</td>',
            f'{ck_data_cell(f"""{_html.escape(r.event_date)}""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(r.impact_description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">${r.portfolio_impact_m:+.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_nsa_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.nsa_tracker import compute_nsa_tracker
    r = compute_nsa_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("IDR Cases (Tracked)", str(r.total_cases), "", "") +
        ck_kpi_block("Total Disputed", f"${r.total_revenue_disputed_m:.3f}M", "", "") +
        ck_kpi_block("Revenue at Risk", f"${r.total_revenue_at_risk_m:,.1f}M", "", "") +
        ck_kpi_block("Provider Win Rate", f"{r.provider_win_rate_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Admin Fee", f"${r.avg_admin_fee_m:.2f}", "", "") +
        ck_kpi_block("Active Strategies", str(r.active_strategies), "", "") +
        ck_kpi_block("Payers Tracked", str(len(r.payer_postures)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    c_tbl = _cases_table(r.cases)
    c_chart = _cases_chart(r.cases)
    d_chart = _deals_chart(r.deals)
    value_anchor = ck_value_anchor(
        "NSA / IDR Exposure",
        f"${r.total_revenue_at_risk_m:,.1f}M revenue at risk",
        delta=f"{r.total_cases} IDR cases · ${r.total_revenue_disputed_m:.2f}M disputed · {r.provider_win_rate_pct * 100:.1f}% provider win rate",
        tone="teal",
    )
    p_tbl = _payers_table(r.payer_postures)
    d_tbl = _deals_table(r.deals)
    e_tbl = _emergency_table(r.emergency)
    r_tbl = _reg_table(r.regulatory)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    provider_won = sum(1 for c in r.cases if "provider" in c.status.lower() and "awarded" in c.status.lower())
    payer_won = sum(1 for c in r.cases if "payer" in c.status.lower() and "awarded" in c.status.lower())

    page_title = ck_page_title(
        "No Surprises Act / IDR Tracker",
        eyebrow="NSA TRACKER",
        meta=f"""{r.total_cases} active/resolved IDR cases · ${r.total_revenue_at_risk_m:,.1f}M revenue at risk across {r.active_strategies} strategies · {r.provider_win_rate_pct * 100:.1f}% provider win rate · {provider_won} awarded provider / {payer_won} awarded payer — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Portfolio NSA / IDR Exposure by Deal</div>{d_chart}{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Emergency Department Portfolio Economics</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">IDR Case Detail</div>{c_chart}{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Payer Posture Analytics</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Regulatory Developments Calendar</div>{r_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">NSA / IDR Portfolio Summary:</strong> {r.total_cases} IDR cases tracked across emergency, anesthesia, radiology, hospitalist, NICU, and ambulance services — ${r.total_revenue_at_risk_m:,.1f}M total revenue at risk.
    Provider win rate {r.provider_win_rate_pct * 100:.1f}% on submitted cases — above CMS-reported industry average ~70% due to disciplined QPA-vs-claim documentation and batched IDR strategy.
    Payer dispersion: Kaiser (51.4% provider win) most restrictive; UHC (69.4%) slightly below average (aggressive QPA strategy); Centene, BCBS Michigan, Aetna, Humana, Cigna, Elevance track 72-74% (moderate posture).
    Emergency department portfolio: 3 of 4 ED groups track sub-26% OON rate and &lt;12% bad debt; Group 3 (Kaiser-concentrated) at 38.5% OON and 18.5% bad debt — remediation in progress.
    Regulatory momentum favorable: 4 TMA rulings since 2024 have narrowed QPA presumption and broadened batching eligibility — Q1 2026 CMS advance notice proposes further specialty adjustments.
    State NSA laws (NY, CA, WA, TX) occasionally more provider-friendly than federal; federal preemption challenged in multi-state litigation — $18.5M cumulative favorable impact anticipated.
  </div>
</div>"""

    return chartis_shell(body, "NSA / IDR Tracker", active_nav="/nsa-tracker",
        editorial_intro={
            "eyebrow": "NSA TRACKER",
            "headline": "What the nsa tracker page reveals on this deal.",
            "italic_word": "reveals",
        })
