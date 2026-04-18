"""Hospital Anchor Contract Tracker — /hospital-anchor."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _renewal_color(s: str) -> str:
    if "in negotiation" in s.lower(): return P["warning"]
    if "proposal submitted" in s.lower(): return P["accent"]
    if "negotiations started" in s.lower(): return P["accent"]
    if "pre-negotiation" in s.lower(): return P["text_dim"]
    if "early-stage" in s.lower(): return P["text_dim"]
    if "scheduled" in s.lower(): return P["text_dim"]
    return P["text_dim"]


def _trend_color(t: str) -> str:
    return {
        "stable": P["accent"],
        "slightly widening": P["warning"],
        "widening": P["negative"],
        "tightening (pressure)": P["negative"],
    }.get(t, P["text_dim"])


def _contracts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Hospital System","left"),("Service Line","left"),("Start","right"),
            ("End","right"),("Annual Value ($M)","right"),("Stipend ($M)","right"),("Guaranteed ($M)","right"),
            ("Prod-Based %","right"),("Exclusive","center"),("Renewal Prob %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ex_c = pos if c.exclusivity else warn
        rp_c = pos if c.renewal_probability_pct >= 0.85 else (acc if c.renewal_probability_pct >= 0.75 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.hospital_system)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.service_line)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.contract_start)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(c.contract_end)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.contract_value_annual_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${c.stipend_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.guaranteed_compensation_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.productivity_based_pct * 100:.0f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{ex_c};font-weight:700">{"YES" if c.exclusivity else "NO"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rp_c};font-weight:700">{c.renewal_probability_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _renewals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Contract","left"),("Expires","right"),("Months Out","right"),
            ("Revenue at Risk ($M)","right"),("Status","center"),("Incumbent Advantage","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _renewal_color(r.renewal_status)
        m_c = warn if r.months_until_expiry <= 12 else (acc if r.months_until_expiry <= 24 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(r.contract)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.expires)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{r.months_until_expiry}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${r.revenue_at_risk_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.renewal_status)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(r.incumbent_advantage)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stipends_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Hospital System","left"),("Service Line","left"),("Stipend / Prod Ratio","right"),
            ("$/wRVU","right"),("Total Stipend ($M)","right"),("Benchmark","center"),("Trend","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _trend_color(s.trend)
        b_c = pos if "P75" in s.benchmark_percentile else (acc if "P60" in s.benchmark_percentile else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.hospital_system)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.service_line)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{s.stipend_vs_productivity_ratio * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.stipend_per_wrvu:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.total_stipend_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{b_c};font-weight:700">{_html.escape(s.benchmark_percentile)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.trend)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _counterparties_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Hospital System","left"),("Credit Rating","center"),("Contracts","right"),
            ("Total Revenue ($M)","right"),("Geographic Markets","left"),("Strategic Direction","left"),("Financial Health","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if c.rating.startswith(("AA", "A+")) else (acc if c.rating.startswith(("A-", "BBB")) else P["warning"])
        h_c = pos if "strong" in c.financial_health.lower() else (acc if "stable" in c.financial_health.lower() else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.hospital_system)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{r_c};font-weight:700">{_html.escape(c.rating)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.contracts_with_portfolio}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.total_revenue_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(c.geographic_markets)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(c.strategic_direction)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{h_c}">{_html.escape(c.financial_health)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _service_lines_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Service Line","left"),("Deals","right"),("Contracts","right"),("Revenue ($M)","right"),
            ("Avg Size ($M)","right"),("Weighted Renewal %","right"),("Typical Term","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.service_line)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.portfolio_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.total_contracts}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.revenue_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.avg_contract_size_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{s.weighted_renewal_prob * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.typical_term_years}y</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _at_risk_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Deal","left"),("Hospital System","left"),("Service Line","left"),("Risk Factors","left"),
            ("Revenue at Risk ($M)","right"),("Mitigation","left"),("Owner","left"),("Action Date","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(a.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(a.hospital_system)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.service_line)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(a.risk_factors)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${a.at_risk_revenue_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(a.mitigation_strategy)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.owner)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(a.action_date)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_hospital_anchor(params: dict = None) -> str:
    from rcm_mc.data_public.hospital_anchor import compute_hospital_anchor
    r = compute_hospital_anchor()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("Contracts", str(r.total_contracts), "", "") +
        ck_kpi_block("Contract Value", f"${r.total_contract_value_m:,.1f}M", "", "") +
        ck_kpi_block("Stipend", f"${r.total_stipend_m:.1f}M", "", "") +
        ck_kpi_block("Renewal Prob", f"{r.weighted_renewal_probability_pct * 100:.0f}%", "", "") +
        ck_kpi_block("Exclusive %", f"{r.exclusive_contracts}/{r.total_contracts}", "", "") +
        ck_kpi_block("Expiring ≤12 mo", str(r.contracts_expiring_12mo), "", "") +
        ck_kpi_block("At Risk", f"${r.at_risk_revenue_m:.1f}M", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    c_tbl = _contracts_table(r.contracts)
    rn_tbl = _renewals_table(r.renewals)
    st_tbl = _stipends_table(r.stipends)
    cp_tbl = _counterparties_table(r.counterparties)
    sl_tbl = _service_lines_table(r.service_lines)
    ar_tbl = _at_risk_table(r.at_risk)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Hospital Anchor Contract Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_contracts} contracts · ${r.total_contract_value_m:,.1f}M annual value · ${r.total_stipend_m:.1f}M stipend · {r.weighted_renewal_probability_pct * 100:.0f}% weighted renewal · {r.exclusive_contracts}/{r.total_contracts} exclusive · ${r.at_risk_revenue_m:.1f}M at risk — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Renewal Schedule — Next 36 Months</div>{rn_tbl}</div>
  <div style="{cell}"><div style="{h3}">At-Risk Contracts (Active Watchlist)</div>{ar_tbl}</div>
  <div style="{cell}"><div style="{h3}">Active Hospital Contract Book</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Service Line Concentration</div>{sl_tbl}</div>
  <div style="{cell}"><div style="{h3}">Stipend Economics</div>{st_tbl}</div>
  <div style="{cell}"><div style="{h3}">Hospital Counterparties — Credit & Strategy</div>{cp_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Hospital Anchor Contract Summary:</strong> {r.total_contracts} active contracts generate ${r.total_contract_value_m:,.1f}M annual revenue with ${r.total_stipend_m:.1f}M hospital-paid stipends — 29% stipend-to-total mix supports productivity gap during ramp / volatility.
    Renewal profile: {r.weighted_renewal_probability_pct * 100:.0f}% weighted renewal probability; {r.contracts_expiring_12mo} contracts expiring within 12 months (${sum(r2.revenue_at_risk_m for r2 in r.renewals if r2.months_until_expiry <= 12):.1f}M revenue at renewal).
    Counterparty concentration: HCA Healthcare ($283M across 5 contracts) is the single largest relationship — represents 30% of contract book; diversified across anesthesia, radiology, ED, hospitalist, pathology.
    Credit quality: 60% of contracted revenue from A-/better counterparties (HCA BBB+, Kaiser AA+, Ascension A+, CommonSpirit A-, Baylor AA-, AdventHealth AA-, Methodist AA); Tenet (B+) and UHS (BB+) at weaker end.
    Stipend benchmarking: HCA contracts at P75, CommonSpirit/Ascension at P60, Tenet at P75 (under anesthesia pressure); AdventHealth stipend "tightening" flags risk ahead of Dec 2025 renewal.
    At-risk watchlist: $149.0M revenue at risk across 5 contracts (Envision-UHS $58M, Envision-Tenet $28.5M, USAP-AdventHealth $32M, Pediatrix $18.5M, Spruce-Ascension $12M) — active mitigation in place with senior partner ownership.
  </div>
</div>"""

    return chartis_shell(body, "Hospital Anchor", active_nav="/hospital-anchor")
