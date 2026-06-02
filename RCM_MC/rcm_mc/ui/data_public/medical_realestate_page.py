"""Medical Real Estate / MOB Tracker — /medical-realestate."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel

def _properties_chart(items) -> str:
    """Lead chart for the property table — properties ranked by value so
    the biggest assets surface first. Bar = share of total portfolio
    value; value = property value ($M); tone teal. Full grid below.
    """
    total = sum(p.value_m for p in items) or 1.0
    ranked = sorted(items, key=lambda p: p.value_m, reverse=True)
    rows = []
    for p in ranked:
        rows.append(ck_bar_row(p.property_name, f"${p.value_m:,.1f}M",
                               p.value_m / total * 100.0, tone="teal"))
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of total portfolio '
            'value \u00b7 value = property value ($M)</div></div>')



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
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    _bar_max = max((p.annual_rent_m for p in items), default=1.0) or 1.0
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = _credit_color(p.tenant_credit)
        l_c = pos if p.lease_years_remaining >= 10 else (acc if p.lease_years_remaining >= 8 else P["warning"])
        cap_c = pos if p.cap_rate_pct <= 6.5 else (acc if p.cap_rate_pct <= 7.25 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.property_name)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.city)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.state)}</td>',
            f'{ck_data_cell(f"""{p.sqft:,}""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.tenant)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c_c};font-weight:700">{_html.escape(p.tenant_credit)}</td>',
            f'{ck_data_cell(f"""${p.annual_rent_m:.1f}M""", align="right", mono=True, tone="pos", weight=700, bar=p.annual_rent_m / _bar_max * 100)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.nnn_or_gross)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:600">{p.lease_years_remaining:.1f}y</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cap_c};font-weight:700">{p.cap_rate_pct:.2f}%</td>',
            f'{ck_data_cell(f"""${p.value_m:.1f}M""", align="right", mono=True, weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sectors_chart(items) -> str:
    """Summary chart — property value by type (tone by cap rate / quality)."""
    def _tone(s):
        if s.avg_cap_rate_pct <= 0.070: return "positive"
        if s.avg_cap_rate_pct <= 0.085: return "teal"
        return "warning"
    top = sorted(items, key=lambda s: s.total_value_m, reverse=True)
    total = sum(s.total_value_m for s in top) or 1.0
    rows = [ck_bar_row(f"{s.sector} ({s.property_count} props)",
            f"${s.total_value_m:,.0f}M @ {s.avg_cap_rate_pct * 100:.1f}% cap",
            s.total_value_m / total * 100.0, tone=_tone(s)) for s in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of portfolio value by property type '
            '· value = value ($M) @ cap rate · tone = cap rate (lower = premium)</div></div>')


def _sectors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sector","left"),("Properties","right"),("SqFt","right"),("Rent ($M)","right"),
            ("Value ($M)","right"),("Avg Cap","right"),("Avg Lease (yrs)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.sector)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.property_count}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{s.total_sqft:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.total_rent_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${s.total_value_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.avg_cap_rate_pct:.2f}%""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{s.avg_lease_years:.1f}y""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tenants_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Tenant","left"),("Type","left"),("Credit","center"),("Properties","right"),
            ("SqFt","right"),("Annual Rent ($M)","right"),("% Portfolio Rent","right"),("Relationship (yrs)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = _credit_color(t.credit_rating)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.tenant)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.tenant_type)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{c_c};font-weight:700">{_html.escape(t.credit_rating)}</td>',
            f'{ck_data_cell(f"""{t.properties}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{t.total_sqft:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${t.annual_rent_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{t.pct_portfolio_rent * 100:.1f}%""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{t.relationship_years}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _expirations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Year","right"),("Expiring Leases","right"),("Expiring Rent ($M)","right"),
            ("Weighted Cap Rate","right"),("Renewal Rate","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if e.renewal_rate_pct >= 0.90 else (acc if e.renewal_rate_pct >= 0.85 else (warn if e.renewal_rate_pct > 0 else text_dim))
        cells = [
            f'{ck_data_cell(f"""{e.year}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{e.expiring_leases}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${e.expiring_rent_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{e.weighted_avg_cap_rate:.2f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{e.renewal_rate_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmarks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Property Type","left"),("P25","right"),("Median","right"),("P75","right"),
            ("YTD Trend (bps)","right"),("Regional Dispersion (bps)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = warn if b.ytd_trend_bps >= 30 else (acc if b.ytd_trend_bps >= 15 else pos)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.property_type)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{b.p25_cap_rate:.2f}%""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{b.median_cap_rate:.2f}%""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{b.p75_cap_rate:.2f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">+{b.ytd_trend_bps}</td>',
            f'{ck_data_cell(f"""±{b.regional_dispersion_bps}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _propcos_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Strategy","left"),("Properties","right"),("Value ($M)","right"),
            ("Proceeds ($M)","right"),("OpCo Coverage","right"),("Target Investor","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if p.opco_coverage_x >= 2.5 else (acc if p.opco_coverage_x >= 2.0 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.deal)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(p.strategy)}""", tone="dim")}',
            f'{ck_data_cell(f"""{p.properties_count}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${p.property_value_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${p.sale_leaseback_proceeds_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{p.opco_coverage_x:.1f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.target_investor)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    p_chart = _properties_chart(r.properties)
    p_tbl = _properties_table(r.properties)
    value_anchor = ck_value_anchor(
        "Medical Real Estate",
        f"${r.total_value_b:,.1f}B portfolio value",
        delta=f"{r.total_properties} properties \u00b7 ${r.total_annual_rent_m:,.1f}M annual rent \u00b7 {r.weighted_cap_rate_pct:.1f}% wtd cap \u00b7 {r.weighted_lease_years:.1f}y WALT",
        tone="navy",
    )
    s_tbl = _sectors_table(r.sectors)
    s_chart = _sectors_chart(r.sectors)
    t_tbl = _tenants_table(r.tenants)
    e_tbl = _expirations_table(r.expirations)
    b_tbl = _benchmarks_table(r.benchmarks)
    pc_tbl = _propcos_table(r.propcos)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    ig_rent = sum(t.annual_rent_m for t in r.tenants if any(t.credit_rating.startswith(c) for c in ("A", "BBB")))
    ig_share_pct = ig_rent / r.total_annual_rent_m * 100 if r.total_annual_rent_m else 0

    # 2026-05-30 audit P5 editorial: MOB (Medical Office Building) is
    # the specific real-estate type the page tracks. "Medical Real
    # Estate Tracker" is the umbrella partner-vocab.
    page_title = ck_page_title(
        "Medical Real Estate Tracker",
        eyebrow="MEDICAL REALESTATE",
        meta=f"{r.total_properties} properties at {r.total_sqft_mm:.2f}MM sqft · ${r.total_value_b:.2f}B value generating ${r.total_annual_rent_m:.1f}M annual rent at {r.weighted_cap_rate_pct:.2f}% weighted cap · {r.weighted_lease_years:.1f}y avg lease ({r.nnn_pct * 100:.0f}% NNN) · ${ig_rent:.1f}M investment-grade rent ({ig_share_pct:.0f}% of portfolio)",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {data_required_panel(P, title="Medical Real Estate", needed=[("property","property / site"),("type","lease / own"),("sqft","square feet"),("annual_rent","annual rent $"),("term_end","term end (YYYY-MM-DD)"),("renewal_options","renewal options")], template="lease_schedule_template.csv", request_from="Real estate / facilities", activates="lease cost, term, and renewal-option exposure", guide_hint="What lease-schedule data do I need to upload?")}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Property-Type Rollup</div>{s_chart}{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Individual Properties</div>{p_chart}{p_tbl}</div>
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

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Medical RE Tracker", active_nav="/medical-realestate",
        editorial_intro={
            "eyebrow": "MEDICAL REALESTATE",
            "headline": "What the medical realestate page reveals on this deal.",
            "italic_word": "reveals",
        })
