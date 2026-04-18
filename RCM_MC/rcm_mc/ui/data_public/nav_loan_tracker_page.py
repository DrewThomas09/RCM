"""NAV Loan / Fund-Level Financing Tracker — /nav-loan-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {"tier 1 specialist": P["positive"], "tier 1 diversified": P["accent"], "tier 2": P["warning"]}.get(t, P["text_dim"])


def _trend_color(tr: str) -> str:
    if "widening" in tr: return P["warning"]
    if "flat" in tr: return P["text_dim"]
    return P["positive"]


def _loans_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Fund","left"),("Sponsor","left"),("Vintage","right"),("NAV ($B)","right"),
            ("Loan ($M)","right"),("LTV","right"),("SOFR+","right"),("Tenor","right"),
            ("Closed","right"),("Use of Proceeds","left"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, l in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        lt_c = pos if l.ltv_pct <= 0.10 else (acc if l.ltv_pct <= 0.14 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(l.fund)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(l.sponsor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{l.vintage}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${l.nav_at_close_b:.2f}B</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${l.loan_size_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{lt_c};font-weight:700">{l.ltv_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{l.sofr_spread_bps}bps</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{l.maturity_years}y</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(l.closed_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.use_of_proceeds)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pos};border:1px solid {pos};border-radius:2px;letter-spacing:0.06em">{_html.escape(l.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lenders_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Lender","left"),("Total Committed ($M)","right"),("Loans","right"),("Median LTV","right"),
            ("Sector Focus","left"),("Tier","center"),("Avg Spread","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, l in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _tier_color(l.tier)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(l.lender)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${l.total_commitments_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{l.loans}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{l.median_ltv_pct:.2f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.sector_focus)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(l.tier)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{l.avg_spread_bps}bps</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _uses_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Use of Proceeds","left"),("Loan Count","right"),("Total Volume ($M)","right"),
            ("Median Check ($M)","right"),("Typical Structure","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, u in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(u.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{u.loan_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${u.total_volume_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${u.median_check_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(u.typical_structure)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _coverage_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Fund","left"),("Current NAV ($B)","right"),("Loan Out ($M)","right"),("Current LTV","right"),
            ("Maint Covenant","right"),("Headroom","right"),("Collateral","right"),("Stress Headroom","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        h_c = pos if c.headroom_pct >= 0.35 else (acc if c.headroom_pct >= 0.25 else warn)
        sh_c = pos if c.liquidity_stress_headroom_pct >= 0.25 else (acc if c.liquidity_stress_headroom_pct >= 0.20 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.fund)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${c.nav_current_b:.2f}B</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.loan_outstanding_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{c.current_ltv_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.maintenance_covenant_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{h_c};font-weight:700">{c.headroom_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.collateral_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sh_c};font-weight:700">{c.liquidity_stress_headroom_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stress_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Scenario","left"),("NAV Markdown","right"),("Resulting LTV","right"),("Cov Trip","center"),
            ("Required Cure ($M)","right"),("Portfolio Impact","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = neg if s.covenant_trip else pos
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.nav_markdown_pct * 100:+.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{s.resulting_ltv_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{t_c};font-weight:700">{"TRIP" if s.covenant_trip else "SAFE"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if s.required_cure_m > 0 else text_dim};font-weight:700">${s.required_cure_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.impact_on_portfolio)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmarks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Loan Type","left"),("Typical LTV","right"),("Spread (bps)","right"),
            ("Tenor (y)","right"),("Market Vol 2024 ($B)","right"),("Trend","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tr_c = _trend_color(b.pricing_trend)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(b.loan_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{b.typical_ltv_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{b.typical_spread_bps}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.typical_tenor_years}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${b.market_volume_24_b:.1f}B</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tr_c};border:1px solid {tr_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.pricing_trend)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_nav_loan_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.nav_loan_tracker import compute_nav_loan_tracker
    r = compute_nav_loan_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    kpi_strip = (
        ck_kpi_block("Active Loans", str(r.total_loans), "", "") +
        ck_kpi_block("Outstanding", f"${r.total_outstanding_m:,.1f}M", "", "") +
        ck_kpi_block("Weighted LTV", f"{r.weighted_ltv_pct * 100:.2f}%", "", "") +
        ck_kpi_block("Weighted SOFR+", f"{r.weighted_spread_bps}", "bps", "") +
        ck_kpi_block("Near Maturity", str(r.loans_near_maturity), "", "") +
        ck_kpi_block("Trip Scenarios", str(r.covenant_trip_scenarios), "/6", "") +
        ck_kpi_block("Lenders", str(len(r.lenders)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    l_tbl = _loans_table(r.loans)
    lend_tbl = _lenders_table(r.lenders)
    u_tbl = _uses_table(r.uses)
    c_tbl = _coverage_table(r.coverage)
    s_tbl = _stress_table(r.stress)
    b_tbl = _benchmarks_table(r.benchmarks)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    avg_headroom = sum(c.headroom_pct for c in r.coverage) / len(r.coverage) if r.coverage else 0

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">NAV Loan / Fund-Level Financing Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_loans} active NAV loans · ${r.total_outstanding_m:,.1f}M outstanding · {r.weighted_ltv_pct * 100:.2f}% weighted LTV · SOFR+{r.weighted_spread_bps}bps · {r.loans_near_maturity} loans within 4-year maturity window — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Active NAV Loan Book</div>{l_tbl}</div>
  <div style="{cell}"><div style="{h3}">Coverage Analysis — Current LTV vs Covenants</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Stress Testing — NAV Markdown Scenarios</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Use of Proceeds Distribution</div>{u_tbl}</div>
  <div style="{cell}"><div style="{h3}">Lender Book — Concentration & Pricing</div>{lend_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Benchmarks — NAV Loans & Adjacent</div>{b_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">NAV Loan Book Summary:</strong> ${r.total_outstanding_m:,.1f}M outstanding across {r.total_loans} healthcare PE funds — weighted {r.weighted_ltv_pct * 100:.2f}% LTV well inside 20% typical maintenance covenants with {avg_headroom * 100:.1f}% headroom.
    Primary use of proceeds: LP distribution bridges (8 loans, ${sum(u.total_volume_m for u in r.uses if "distribution" in u.category.lower() or "liquidity" in u.category.lower()):.0f}M) during protracted exit drought; capex / add-on M&A use secondary.
    Weighted SOFR+{r.weighted_spread_bps}bps pricing tracks market; healthcare PE NAV loans 25-50bps inside multi-sector NAV loans on stronger collateral coverage and lower NAV volatility.
    Stress testing: base through -30% NAV markdown scenarios retain covenant compliance; -40% markdown triggers 3-fund covenant trip (${sum(s.required_cure_m for s in r.stress if s.covenant_trip):.0f}M aggregate cure capacity needed).
    Lender concentration: top-2 specialists (17Capital, Hark Capital) hold 44% of loans; broader tier-1 participation ensures refinancing optionality at 4-5yr maturities.
    Pricing trend widening +25bps YTD reflects market repricing of PE NAV loan risk given exit drought, LP liquidity pressure, and secondary market compression.
  </div>
</div>"""

    return chartis_shell(body, "NAV Loan Tracker", active_nav="/nav-loan-tracker")
