"""Payer Contract Renewal Tracker — /payer-contracts."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor


def _concentration_chart(items) -> str:
    """Lead chart for the payer-concentration table — payers ranked by
    share of portfolio revenue so concentration risk reads at a glance.
    Bar width = % of portfolio revenue; value = annual revenue ($M);
    tone flags concentration risk (>=20% amber, otherwise teal),
    matching the table. Full concentration grid stays directly below.
    """
    ranked = sorted(items, key=lambda c: c.pct_of_portfolio_rev, reverse=True)
    rows = []
    for c in ranked:
        tone = "warning" if c.pct_of_portfolio_rev >= 0.20 else "teal"
        rows.append(ck_bar_row(
            c.payer,
            f"${c.annual_revenue_m:,.0f}M",
            c.pct_of_portfolio_rev * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of portfolio revenue · value = annual revenue ($M) · '
        'tone = concentration risk (amber &ge;20% of portfolio)</div>'
        '</div>'
    )


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
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    _bar_max = max((c.annual_revenue_m for c in items), default=1.0) or 1.0
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(c.renegotiation_stage)
        e_c = pos if c.rate_escalator_pct >= 0.030 else (acc if c.rate_escalator_pct >= 0.020 else P["warning"])
        f_c = pos if c.cpi_floor else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(c.payer)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.contract_type)}</td>',
            f'{ck_data_cell(f"""${c.annual_revenue_m:.1f}M""", align="right", mono=True, tone="pos", weight=700, bar=c.annual_revenue_m / _bar_max * 100)}',
            f'{ck_data_cell(f"""{_html.escape(c.effective_date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(c.expires)}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">+{c.rate_escalator_pct * 100:.2f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{f_c};font-weight:700">{"YES" if c.cpi_floor else "NO"}</td>',
            f'{ck_data_cell(f"""{c.cpi_cap_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.renegotiation_stage)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{c.lives_covered_k}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _history_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Payer","left"),("Sector","left"),("2022","right"),("2023","right"),("2024","right"),
            ("2025","right"),("2026 Requested","right"),("Trend","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _trend_color(h.trend)
        r_c = pos if h.py_2026_requested_pct >= 0.028 else (acc if h.py_2026_requested_pct >= 0.022 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(h.payer)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(h.sector)}</td>',
            f'{ck_data_cell(f"""+{h.py_2022_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""+{h.py_2023_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""+{h.py_2024_pct * 100:.2f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""+{h.py_2025_pct * 100:.2f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">+{h.py_2026_requested_pct * 100:.2f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(h.trend)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _concentration_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Payer","left"),("Contracts","right"),("Annual Revenue ($M)","right"),("% of Portfolio","right"),
            ("Sectors Covered","left"),("Avg Tenure (yrs)","right"),("Network Status","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = warn if c.pct_of_portfolio_rev >= 0.20 else (acc if c.pct_of_portfolio_rev >= 0.10 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.payer)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.contracts}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${c.annual_revenue_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{c.pct_of_portfolio_rev * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(c.sectors_covered)}</td>',
            f'{ck_data_cell(f"""{c.relationship_tenure_avg_years:.1f}y""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.network_status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _negotiations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Payer","left"),("Target Close","right"),("Our Ask","right"),
            ("Payer Counter","right"),("Gap","right"),("Risk","center"),("Revenue at Stake ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, n in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = _risk_color(n.risk_level)
        g_c = warn if n.gap_pct >= 0.025 else (acc if n.gap_pct >= 0.015 else pos)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(n.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(n.payer)}</td>',
            f'{ck_data_cell(f"""{_html.escape(n.target_close)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""+{n.current_ask_pct * 100:.1f}%""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""+{n.payer_counter_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{n.gap_pct * 100:.1f}pp</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{r_c};border:1px solid {r_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(n.risk_level)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${n.revenue_at_stake_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _network_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Payer","left"),("Market","left"),("Providers","right"),("T/D Compliance %","right"),
            ("Waived Members","right"),("Network Gaps","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, n in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if n.time_distance_compliance_pct >= 0.95 else (acc if n.time_distance_compliance_pct >= 0.90 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(n.payer)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(n.market)}</td>',
            f'{ck_data_cell(f"""{n.provider_count:,}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{n.time_distance_compliance_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn if n.waived_members > 0 else text_dim};font-weight:700">{n.waived_members:,}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(n.network_gaps)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _optimization_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Initiative","left"),("Deals","right"),("Rate Lift %","right"),("Implementation (mo)","right"),
            ("Annualized Value ($M)","right"),("Prerequisite","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        l_c = pos if o.typical_rate_lift_pct >= 3.5 else (acc if o.typical_rate_lift_pct >= 2.0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(o.initiative)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{o.deals}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:700">+{o.typical_rate_lift_pct:.1f}pp</td>',
            f'{ck_data_cell(f"""{o.implementation_months}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${o.annualized_value_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(o.prerequisite)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _rbp_benchmark_panel() -> str:
    """Real CIVHC / Colorado APCD commercial-vs-Medicare benchmark — the
    'hospital % of Medicare' ratio is the canonical rate benchmark payer
    contracts are negotiated against. Provider-level public data; the
    deal's contract book below is illustrative. Grounds the rate thesis
    in an observed commercial-rate benchmark, not the seed corpus."""
    try:
        from rcm_mc.data import payer_data as _pd
        df = _pd.reference_pricing_summary(claim_type="All")
    except Exception:
        return ""
    if df is None or not len(df):
        return ""
    med = df["hospital_pct_medicare"].dropna()
    if not len(med):
        return ""
    statewide_median = float(med.median())
    p25 = float(med.quantile(0.25)); p75 = float(med.quantile(0.75))
    n_prov = int(df["organization_name"].nunique())
    n_cty = int(df["county"].nunique())

    border = P["border"]; tprim = P["text"]; tdim = P["text_dim"]; acc = P["accent"]
    top = df.sort_values("hospital_pct_medicare", ascending=False).head(6)
    rows = "".join(
        f'<tr>'
        f'<td style="padding:3px 8px;font-family:JetBrains Mono,monospace;font-size:11px;color:{tprim}">{_html.escape(str(t.organization_name)[:32])}</td>'
        f'<td style="padding:3px 8px;font-family:JetBrains Mono,monospace;font-size:10px;color:{tdim}">{_html.escape(str(t.county))}</td>'
        f'<td style="padding:3px 8px;text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;'
        f'font-variant-numeric:tabular-nums;color:{tprim}">{t.hospital_pct_medicare:.2f}x</td>'
        f'</tr>'
        for t in top.itertuples() if t.hospital_pct_medicare == t.hospital_pct_medicare
    )
    return f'''
<div style="background:{P["panel"]};border:1px solid {border};border-left:3px solid {acc};
  padding:14px 16px;margin-bottom:16px">
  <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px">
    Real commercial-vs-Medicare benchmark &mdash; CIVHC / Colorado APCD
    <span style="color:{acc};font-weight:600"> · LIVE</span>
  </div>
  <div style="display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start">
    <div style="white-space:nowrap">
      <div style="font-family:JetBrains Mono,monospace;font-size:20px;color:{tprim};
        font-variant-numeric:tabular-nums">{statewide_median:.2f}x</div>
      <div style="font-size:10px;color:{tdim};margin-bottom:8px">median commercial price<br>as % of Medicare</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:12px;color:{tdim};
        font-variant-numeric:tabular-nums">{p25:.2f}x &ndash; {p75:.2f}x IQR</div>
      <div style="font-size:10px;color:{tdim}">{n_prov} providers · {n_cty} counties</div>
    </div>
    <div>
      <div style="font-size:9px;color:{P["text_faint"]};margin-bottom:4px">HIGHEST COMMERCIAL-%-OF-MEDICARE PROVIDERS</div>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P["text_faint"]}">
    CIVHC / CO all-payer claims database (2021&ndash;2024). The commercial-%-of-Medicare
    ratio is the real rate benchmark contracts negotiate against &mdash; the deal's
    contract book, negotiations, and escalators below are illustrative.
  </div>
</div>'''


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
    con_chart = _concentration_chart(r.concentration)
    con_tbl = _concentration_table(r.concentration)
    n_tbl = _negotiations_table(r.negotiations)
    nt_tbl = _network_table(r.network)
    o_tbl = _optimization_table(r.optimization)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    opt_value = sum(o.annualized_value_m for o in r.optimization)
    page_title = ck_page_title(
        "Payer Contract Renewal Tracker",
        eyebrow="PAYER CONTRACTS",
        meta=f"""{r.total_contracts} contracts · ${r.total_annual_revenue_m:,.1f}M annual revenue · weighted {r.weighted_avg_escalator_pct * 100:.2f}% escalator · {r.contracts_expiring_12mo} expiring ≤12 months · ${r.revenue_at_renegotiation_m:.1f}M at renegotiation — {r.corpus_deal_count:,} corpus deals""",
    )
    
    value_anchor = ck_value_anchor(
        "Payer Contracts",
        f"${r.total_annual_revenue_m:,.0f}M annual revenue",
        delta=f"{r.total_contracts} contracts · {r.contracts_expiring_12mo} expiring <12mo",
        opportunity=f"${r.revenue_at_renegotiation_m:,.1f}M revenue at renegotiation",
        tone="teal",
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  {_rbp_benchmark_panel()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Active Negotiations Pipeline</div>{n_tbl}</div>
  <div style="{cell}"><div style="{h3}">Payer Contract Book</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Historical Rate Change by Payer</div>{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">Payer Concentration</div>{con_chart}{con_tbl}</div>
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

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Payer Contracts", active_nav="/payer-contracts",
        editorial_intro={
            "eyebrow": "PAYER CONTRACTS",
            "headline": "What the payer contracts page reveals on this deal.",
            "italic_word": "reveals",
        })
