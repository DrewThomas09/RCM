"""Medical Real Estate / MOB Tracker — /medical-realestate."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _credit_color(rating: str) -> str:
    r = rating.upper()
    if "A" in r and "AA" in r: return P["positive"]
    if r.startswith("A"): return P["positive"]
    if r.startswith("BBB"): return P["accent"]
    if r.startswith("BB"): return P["warning"]
    if r.startswith("B"): return P["warning"]
    if "N/A" in r: return P["text_dim"]
    return P["text_dim"]


def _properties_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Property","left"),("Sector","left"),("City","left"),("State","center"),
            ("SqFt","right"),("Tenant","left"),("Credit","center"),("Rent ($M)","right"),
            ("Lease Type","center"),("Lease Yrs","right"),("Cap Rate","right"),("Value ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = _credit_color(p.tenant_credit)
        l_c = pos if p.lease_years_remaining >= 10 else (acc if p.lease_years_remaining >= 8 else P["warning"])
        cap_c = pos if p.cap_rate_pct <= 6.5 else (acc if p.cap_rate_pct <= 7.25 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.property_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.city)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.state)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.sqft:,}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.tenant)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c_c};font-weight:700">{_html.escape(p.tenant_credit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.annual_rent_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.nnn_or_gross)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:600">{p.lease_years_remaining:.1f}y</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cap_c};font-weight:700">{p.cap_rate_pct:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${p.value_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sectors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sector","left"),("Properties","right"),("SqFt","right"),("Rent ($M)","right"),
            ("Value ($M)","right"),("Avg Cap","right"),("Avg Lease (yrs)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.property_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.total_sqft:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.total_rent_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.total_value_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{s.avg_cap_rate_pct:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.avg_lease_years:.1f}y</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tenants_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Tenant","left"),("Type","left"),("Credit","center"),("Properties","right"),
            ("SqFt","right"),("Annual Rent ($M)","right"),("% Portfolio Rent","right"),("Relationship (yrs)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = _credit_color(t.credit_rating)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(t.tenant)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.tenant_type)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c_c};font-weight:700">{_html.escape(t.credit_rating)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{t.properties}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.total_sqft:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${t.annual_rent_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{t.pct_portfolio_rent * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.relationship_years}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _expirations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Year","right"),("Expiring Leases","right"),("Expiring Rent ($M)","right"),
            ("Weighted Cap Rate","right"),("Renewal Rate","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if e.renewal_rate_pct >= 0.90 else (acc if e.renewal_rate_pct >= 0.85 else (warn if e.renewal_rate_pct > 0 else text_dim))
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{e.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{e.expiring_leases}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.expiring_rent_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.weighted_avg_cap_rate:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{e.renewal_rate_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmarks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Property Type","left"),("P25","right"),("Median","right"),("P75","right"),
            ("YTD Trend (bps)","right"),("Regional Dispersion (bps)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = warn if b.ytd_trend_bps >= 30 else (acc if b.ytd_trend_bps >= 15 else pos)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(b.property_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{b.p25_cap_rate:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{b.median_cap_rate:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.p75_cap_rate:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">+{b.ytd_trend_bps}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">±{b.regional_dispersion_bps}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _propcos_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Strategy","left"),("Properties","right"),("Value ($M)","right"),
            ("Proceeds ($M)","right"),("OpCo Coverage","right"),("Target Investor","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if p.opco_coverage_x >= 2.5 else (acc if p.opco_coverage_x >= 2.0 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim}">{_html.escape(p.strategy)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.properties_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${p.property_value_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.sale_leaseback_proceeds_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{p.opco_coverage_x:.1f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.target_investor)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_medical_realestate(params: dict = None) -> str:
    from rcm_mc.data_public.medical_realestate import compute_medical_realestate
    r = compute_medical_realestate()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Properties", str(r.total_properties), "", "") +
        ck_kpi_block("SqFt", f"{r.total_sqft_mm:.2f}MM", "", "") +
        ck_kpi_block("Annual Rent", f"${r.total_annual_rent_m:.1f}M", "", "") +
        ck_kpi_block("Total Value", f"${r.total_value_b:.2f}B", "", "") +
        ck_kpi_block("Weighted Cap", f"{r.weighted_cap_rate_pct:.2f}%", "", "") +
        ck_kpi_block("Weighted Lease", f"{r.weighted_lease_years:.1f}y", "", "") +
        ck_kpi_block("NNN %", f"{r.nnn_pct * 100:.0f}%", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_tbl = _properties_table(r.properties)
    s_tbl = _sectors_table(r.sectors)
    t_tbl = _tenants_table(r.tenants)
    e_tbl = _expirations_table(r.expirations)
    b_tbl = _benchmarks_table(r.benchmarks)
    pc_tbl = _propcos_table(r.propcos)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    ig_rent = sum(t.annual_rent_m for t in r.tenants if any(t.credit_rating.startswith(c) for c in ("A", "BBB")))

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Medical Real Estate / MOB Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_properties} properties · {r.total_sqft_mm:.2f}MM sqft · ${r.total_annual_rent_m:.1f}M annual rent · ${r.total_value_b:.2f}B value · weighted {r.weighted_cap_rate_pct:.2f}% cap rate / {r.weighted_lease_years:.1f}y lease · {r.nnn_pct * 100:.0f}% NNN — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Property-Type Rollup</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Individual Properties</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Tenant Concentration & Credit Quality</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Lease Expiration Schedule</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Cap Rate Benchmarks (P25 / Median / P75)</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">PropCo / OpCo Separation Strategies</div>{pc_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Medical Real Estate Summary:</strong> {r.total_properties} properties totaling {r.total_sqft_mm:.2f}MM sqft generate ${r.total_annual_rent_m:.1f}M annual rent on ${r.total_value_b:.2f}B portfolio value.
    Weighted {r.weighted_cap_rate_pct:.2f}% cap rate at {r.weighted_lease_years:.1f}y average remaining lease — tracks NAREIT Healthcare Sub-Index ±25bps; {r.nnn_pct * 100:.0f}% NNN share limits OpEx volatility.
    Investment-grade rent base ~${ig_rent:.1f}M ({ig_rent / r.total_annual_rent_m * 100:.0f}% of portfolio) anchored by Piedmont (A1), Quest (BBB+), Accredo/Cigna (A), HCA CareNow (A3).
    2027-2031 lease expirations manageable at 9 leases / $13.6M total — embedded mark-to-market upside of 3-5% on renewal at prevailing MOB rents.
    Cap rate trend: widening 15-50bps across property types YTD reflecting broader CRE dynamics; behavioral health and SNF widest at 40-50bps; IG MOB and specialty pharma tightest at 15bps.
    PropCo/OpCo separation strategy in flight on 5 platforms ($1,150M property value, ~$1,072M target proceeds) — provides deleveraging + recap optionality at 2.5x OpCo rent coverage.
  </div>
</div>"""

    return chartis_shell(body, "Medical RE Tracker", active_nav="/medical-realestate")
