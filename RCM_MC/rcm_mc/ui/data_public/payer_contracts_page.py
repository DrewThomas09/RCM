"""Payer Contract Renewal Tracker — /payer-contracts."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _stage_color(s: str) -> str:
    return {
        "active": P["positive"],
        "pre-negotiation": P["accent"],
        "in negotiation": P["warning"],
        "state-directed": P["text_dim"],
    }.get(s, P["text_dim"])


def _trend_color(t: str) -> str:
    return {
        "accelerating": P["positive"],
        "stable": P["accent"],
        "moderating": P["warning"],
        "cooling": P["warning"],
    }.get(t, P["text_dim"])


def _risk_color(r: str) -> str:
    return {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}.get(r, P["text_dim"])


def _contracts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Payer","left"),("Type","left"),("Annual Rev ($M)","right"),
            ("Effective","right"),("Expires","right"),("Escalator %","right"),("CPI Floor","center"),
            ("CPI Cap %","right"),("Stage","center"),("Lives (K)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(c.renegotiation_stage)
        e_c = pos if c.rate_escalator_pct >= 0.030 else (acc if c.rate_escalator_pct >= 0.020 else P["warning"])
        f_c = pos if c.cpi_floor else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(c.payer)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.contract_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.annual_revenue_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.effective_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(c.expires)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">+{c.rate_escalator_pct * 100:.2f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{f_c};font-weight:700">{"YES" if c.cpi_floor else "NO"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.cpi_cap_pct * 100:.2f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.renegotiation_stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.lives_covered_k}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _history_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Payer","left"),("Sector","left"),("2022","right"),("2023","right"),("2024","right"),
            ("2025","right"),("2026 Requested","right"),("Trend","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _trend_color(h.trend)
        r_c = pos if h.py_2026_requested_pct >= 0.028 else (acc if h.py_2026_requested_pct >= 0.022 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(h.payer)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(h.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">+{h.py_2022_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">+{h.py_2023_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">+{h.py_2024_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">+{h.py_2025_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">+{h.py_2026_requested_pct * 100:.2f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(h.trend)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _concentration_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Payer","left"),("Contracts","right"),("Annual Revenue ($M)","right"),("% of Portfolio","right"),
            ("Sectors Covered","left"),("Avg Tenure (yrs)","right"),("Network Status","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = warn if c.pct_of_portfolio_rev >= 0.20 else (acc if c.pct_of_portfolio_rev >= 0.10 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.payer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.contracts}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.annual_revenue_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{c.pct_of_portfolio_rev * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(c.sectors_covered)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.relationship_tenure_avg_years:.1f}y</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.network_status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _negotiations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Payer","left"),("Target Close","right"),("Our Ask","right"),
            ("Payer Counter","right"),("Gap","right"),("Risk","center"),("Revenue at Stake ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, n in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = _risk_color(n.risk_level)
        g_c = warn if n.gap_pct >= 0.025 else (acc if n.gap_pct >= 0.015 else pos)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(n.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(n.payer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(n.target_close)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">+{n.current_ask_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">+{n.payer_counter_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{n.gap_pct * 100:.1f}pp</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{r_c};border:1px solid {r_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(n.risk_level)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${n.revenue_at_stake_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _network_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Payer","left"),("Market","left"),("Providers","right"),("T/D Compliance %","right"),
            ("Waived Members","right"),("Network Gaps","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, n in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if n.time_distance_compliance_pct >= 0.95 else (acc if n.time_distance_compliance_pct >= 0.90 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(n.payer)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(n.market)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{n.provider_count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{n.time_distance_compliance_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn if n.waived_members > 0 else text_dim};font-weight:700">{n.waived_members:,}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(n.network_gaps)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _optimization_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Initiative","left"),("Deals","right"),("Rate Lift %","right"),("Implementation (mo)","right"),
            ("Annualized Value ($M)","right"),("Prerequisite","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        l_c = pos if o.typical_rate_lift_pct >= 3.5 else (acc if o.typical_rate_lift_pct >= 2.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(o.initiative)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{o.deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:700">+{o.typical_rate_lift_pct:.1f}pp</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.implementation_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${o.annualized_value_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(o.prerequisite)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_payer_contracts(params: dict = None) -> str:
    from rcm_mc.data_public.payer_contracts import compute_payer_contracts
    r = compute_payer_contracts()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Payer Contracts", str(r.total_contracts), "", "") +
        ck_kpi_block("Annual Revenue", f"${r.total_annual_revenue_m:,.1f}M", "", "") +
        ck_kpi_block("In Negotiation", str(r.contracts_in_negotiation), "", "") +
        ck_kpi_block("Weighted Escalator", f"{r.weighted_avg_escalator_pct * 100:.2f}%", "", "") +
        ck_kpi_block("Expiring ≤12 mo", str(r.contracts_expiring_12mo), "", "") +
        ck_kpi_block("Revenue @ Renegotiation", f"${r.revenue_at_renegotiation_m:.1f}M", "", "") +
        ck_kpi_block("Payers Tracked", str(len(r.concentration)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    c_tbl = _contracts_table(r.contracts)
    h_tbl = _history_table(r.history)
    con_tbl = _concentration_table(r.concentration)
    n_tbl = _negotiations_table(r.negotiations)
    nt_tbl = _network_table(r.network)
    o_tbl = _optimization_table(r.optimization)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    opt_value = sum(o.annualized_value_m for o in r.optimization)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Payer Contract Renewal Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_contracts} contracts · ${r.total_annual_revenue_m:,.1f}M annual revenue · weighted {r.weighted_avg_escalator_pct * 100:.2f}% escalator · {r.contracts_expiring_12mo} expiring ≤12 months · ${r.revenue_at_renegotiation_m:.1f}M at renegotiation — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Active Negotiations Pipeline</div>{n_tbl}</div>
  <div style="{cell}"><div style="{h3}">Payer Contract Book</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Historical Rate Change by Payer</div>{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">Payer Concentration</div>{con_tbl}</div>
  <div style="{cell}"><div style="{h3}">Network Adequacy by Payer / Market</div>{nt_tbl}</div>
  <div style="{cell}"><div style="{h3}">Contract Optimization Opportunities</div>{o_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Payer Contract Portfolio Summary:</strong> {r.total_contracts} active contracts sum ${r.total_annual_revenue_m:,.1f}M annual revenue with weighted {r.weighted_avg_escalator_pct * 100:.2f}% escalator — tracks CPI ±50bps.
    Concentration watchlist: UnitedHealthcare 25.8% of contracted revenue ($425M) — top single-payer exposure; Anthem/Elevance (17.3%), Aetna (11.8%), Cigna (11.2%) provide diversification.
    {r.contracts_in_negotiation} contracts in active negotiation with $341.5M revenue at stake — UHC-Cypress (GI), UHC-Cedar (Cardiology), UHC-Spruce (Radiology) are the three major negotiations.
    Rate trend 2026 requested +3.0% average (up from +2.6% average in 2025); UHG accelerating (+0.3pp vs prior year), Humana moderating from peak 2024, Medicaid cooling.
    Network adequacy: 9/10 tracked markets ≥92% compliance; DFW (UHC ortho sports) and San Antonio (BCBS TX behavioral) show meaningful waived-member pressure = 760+ members — remediation targets.
    Contract optimization runway: ${opt_value:.1f}M annualized value across 10 initiatives — clinical integration (+$15.8M), VBC add-ons (+$12.5M), ASC conversion (+$8.5M) top 3 by $$ value.
  </div>
</div>"""

    return chartis_shell(body, "Payer Contracts", active_nav="/payer-contracts")
