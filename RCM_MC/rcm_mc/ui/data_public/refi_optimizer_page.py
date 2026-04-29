"""Refinance Optimizer — /refi-optimizer."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell


def _portfolio_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Holdco","left"),("Sector","left"),("Current Balance ($M)","right"),("Rate","right"),
            ("Maturity","right"),("Yrs Remaining","right"),("Covenant","center"),("Refi Window","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    w_c = {"priority": neg, "in-window": acc, "approaching-window": warn, "long-dated": text_dim}
    c_c = {"maintenance": acc, "cov-lite": pos}
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        wc = w_c.get(p.refi_window_status, text_dim)
        cc = c_c.get(p.covenant_type, text_dim)
        r_c = neg if p.current_rate_pct >= 10.5 else (warn if p.current_rate_pct >= 9.75 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.holdco)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(p.sector)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.current_balance_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{p.current_rate_pct:.2f}%</td>',
            f'{ck_data_cell(f"""{p.maturity_year}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.years_remaining:.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.covenant_type)}</span>""", align="center")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{wc};border:1px solid {wc};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.refi_window_status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _opportunities_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Holdco","left"),("Current Rate","right"),("Achievable","right"),("Δ bps","right"),
            ("Amount ($M)","right"),("Annual Savings ($M)","right"),("NPV Savings ($M)","right"),
            ("Refi Cost ($M)","right"),("Net NPV ($M)","right"),("Priority","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    p_c = {"urgent": neg, "standard": warn, "monitor": text_dim}
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = p_c.get(o.priority, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(o.holdco)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{o.current_rate_pct:.2f}%""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{o.achievable_rate_pct:.2f}%""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""-{o.rate_savings_bps}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${o.amount_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${o.annual_interest_savings_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${o.npv_savings_mm:,.2f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${o.refi_cost_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""${o.net_npv_mm:+,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(o.priority)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _market_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Period","left"),("Spread Trend","center"),("Primary Issuance ($B)","right"),
            ("Direct Lending ($B)","right"),("Investor Demand","center"),("Commentary","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    d_c = {"very strong": pos, "strong": pos, "broad": acc, "moderate": warn, "selective": warn}
    t_c = {"tightening": pos, "stable": acc, "widening": warn}
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        dc = d_c.get(m.investor_demand, text_dim)
        tc = t_c.get(m.spread_trend.split(" ")[0], text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.period)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.spread_trend)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${m.primary_issuance_b:,.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${m.dl_issuance_b:,.1f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{dc};border:1px solid {dc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.investor_demand)}</span>""", align="center")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.commentary)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _quotes_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Lender","left"),("Product","left"),("Size ($M)","right"),("Spread (bps)","right"),
            ("Term (yr)","right"),("Cov-Lite","center"),("OID","right"),("Closing Fee (bps)","right"),("Confidence","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, q in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if q.spread_sofr_bps <= 425 else (acc if q.spread_sofr_bps <= 475 else text_dim)
        c_c = pos if q.confidence == "firm" else acc
        cells = [
            f'{ck_data_cell(f"""{_html.escape(q.lender)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(q.product)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${q.facility_size_mm:,.1f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{q.spread_sofr_bps}</td>',
            f'{ck_data_cell(f"""{q.term_years}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos if q.cov_lite else text_dim};font-weight:700">{"YES" if q.cov_lite else "NO"}</td>',
            f'{ck_data_cell(f"""{q.oid_pct * 100:.2f}%""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{q.closing_fee_bps}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c_c};font-weight:700">{_html.escape(q.confidence)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _maturity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; pos = P["positive"]
    cols = [("Maturity Year","left"),("Holdcos Maturing","right"),("Total Balance ($M)","right"),("Refi Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    s_c = {"near-term": neg, "intermediate": warn, "long-dated": pos}
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = s_c.get(m.refi_status, text_dim)
        cells = [
            f'{ck_data_cell(f"""{m.year}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{m.holdcos_maturing}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${m.total_balance_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.refi_status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _covenant_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Holdco","left"),("Current Leverage","right"),("Covenant Leverage","right"),
            ("Headroom (x)","right"),("Remediation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        h_c = pos if c.headroom_x >= 1.2 else (warn if c.headroom_x >= 0.7 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.holdco)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.current_leverage:,.2f}x""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{c.covenant_leverage:,.2f}x""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{h_c};font-weight:700">+{c.headroom_x:,.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.remediation)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_refi_optimizer(params: dict = None) -> str:
    from rcm_mc.data_public.refi_optimizer import compute_refi_optimizer
    r = compute_refi_optimizer()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("Portfolio Debt", f"${r.total_portfolio_debt_mm:,.0f}M", "", "") +
        ck_kpi_block("Weighted Rate", f"{r.weighted_rate_pct:.2f}%", "", "") +
        ck_kpi_block("Refi Opportunities", str(r.refi_opportunities_identified), "", "") +
        ck_kpi_block("Total Refi NPV", f"${r.total_refi_npv_mm:,.1f}M", "", "") +
        ck_kpi_block("Near-Term Maturities", f"${r.near_term_maturities_mm:,.0f}M", "", "") +
        ck_kpi_block("Holdcos in Portfolio", str(len(r.portfolio)), "", "") +
        ck_kpi_block("Active Quotes", str(len(r.quotes)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_tbl = _portfolio_table(r.portfolio)
    o_tbl = _opportunities_table(r.opportunities)
    m_tbl = _market_table(r.market_windows)
    q_tbl = _quotes_table(r.quotes)
    mt_tbl = _maturity_table(r.maturity)
    c_tbl = _covenant_table(r.covenant)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    urgent_count = sum(1 for o in r.opportunities if o.priority == "urgent")
    body = f"""
<div class="ck-page-wrap">
  <div class="ck-page-head">
    <h1 class="ck-page-h1">Refinance Optimizer</h1>
    <p class="ck-page-sub">Portfolio-wide refi opportunities · market window tracker · lender quote matrix · maturity wall · covenant stress — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {pos};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Portfolio Refi Opportunity</div>
    <div style="color:{pos};font-weight:700;font-size:14px">${r.total_refi_npv_mm:,.1f}M Net NPV · {urgent_count} urgent refi candidates · ${r.near_term_maturities_mm:,.0f}M maturing in next 4 years</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Current weighted rate {r.weighted_rate_pct:.2f}% · market achievable ~8.75% · ~90bps compression available on average</div>
  </div>
  <div style="{cell}"><div style="{h3}">Active Portfolio Debt Stack</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Refi Opportunities (NPV-Ranked)</div>{o_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Window History &amp; Outlook</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Active Lender Quotes</div>{q_tbl}</div>
  <div style="{cell}"><div style="{h3}">Maturity Profile</div>{mt_tbl}</div>
  <div style="{cell}"><div style="{h3}">Covenant Headroom Portfolio-Wide</div>{c_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Refi Thesis:</strong> ${r.total_portfolio_debt_mm:,.0f}M portfolio debt at weighted {r.weighted_rate_pct:.2f}% rate.
    Market achievable is ~8.75% — 90bps compression available across refi-eligible holdcos generating ${r.total_refi_npv_mm:,.1f}M cumulative Net NPV.
    Urgent priority: Project Everest (behavioral health, 10.85% rate + tight covenant) and Project Larkspur (dental, 11.25%, tight covenant).
    Favorable market window: 2025Q2 tightening or 2026Q1 rate-cut anticipation.
    Best active quotes: KKR Credit captive (425 bps), Blue Owl (425 bps), Antares (460 bps). Lower-mid holdcos benefit more from boutique direct lenders (Monroe, Churchill) vs syndicated TL-B.
    Near-term maturity wall ${r.near_term_maturities_mm:,.0f}M must be addressed before 2028; recommend sequence: Larkspur → Everest → Glacier.
  </div>
</div>"""

    return chartis_shell(body, "Refi Optimizer", active_nav="/refi-optimizer",
        editorial_intro={
            "eyebrow": "REFI OPTIMIZER",
            "headline": "What the refi optimizer page reveals on this deal.",
            "italic_word": "reveals",
        })
