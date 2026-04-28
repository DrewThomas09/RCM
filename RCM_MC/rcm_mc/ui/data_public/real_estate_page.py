"""Real Estate / Sale-Leaseback page — /real-estate.

Property inventory, lease term summary, SLB scenario analysis.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _ownership_svg(total_sqft: int, owned_sqft: int, leased_sqft: int) -> str:
    w, h = 540, 80
    pad_l, pad_r, pad_t = 20, 20, 30
    inner_w = w - pad_l - pad_r
    bar_h = 28

    if total_sqft <= 0:
        return ""

    own_w = owned_sqft / total_sqft * inner_w
    leased_w = leased_sqft / total_sqft * inner_w

    bg = P["panel"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        f'<rect x="{pad_l}" y="{pad_t}" width="{own_w:.1f}" height="{bar_h}" fill="{pos}" opacity="0.85"/>'
        f'<rect x="{pad_l + own_w:.1f}" y="{pad_t}" width="{leased_w:.1f}" height="{bar_h}" fill="{acc}" opacity="0.55"/>'
        f'<text x="{pad_l + own_w / 2:.1f}" y="{pad_t + bar_h / 2 + 4}" fill="{P["text"]}" font-size="11" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">Owned {owned_sqft:,} sqft ({owned_sqft / total_sqft * 100:.0f}%)</text>'
        f'<text x="{pad_l + own_w + leased_w / 2:.1f}" y="{pad_t + bar_h / 2 + 4}" fill="{P["text"]}" font-size="11" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">Leased {leased_sqft:,} sqft ({leased_sqft / total_sqft * 100:.0f}%)</text>'
        f'<text x="{pad_l}" y="18" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Real Estate Portfolio Ownership ({total_sqft:,} sqft total)</text>'
        f'</svg>'
    )


def _slb_waterfall_svg(scenarios) -> str:
    if not scenarios:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 30, 30, 60
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_v = max(s.total_slb_proceeds_mm for s in scenarios) * 1.1 or 1

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]

    n = len(scenarios)
    bar_w = (inner_w - (n - 1) * 10) / n

    bars = []
    for i, s in enumerate(scenarios):
        x = pad_l + i * (bar_w + 10)
        bh = (s.total_slb_proceeds_mm / max_v) * inner_h
        y = (h - pad_b) - bh
        color = pos if i == len(scenarios) - 1 else acc
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.88"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="11" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${s.total_slb_proceeds_mm:,.1f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario[:22])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{pos}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">+{s.implied_moic_lift * 100:.1f}% MOIC</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">SLB Scenarios — Cash Proceeds ($M)</text>'
        f'</svg>'
    )


def _assets_table(assets) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    own_colors = {
        "owned": P["positive"], "third_party_leased": P["accent"],
        "leased_from_related": P["warning"],
    }
    cols = [("Property","left"),("Type","left"),("Sqft","right"),
            ("Ownership","left"),("Annual Rent/NOI","right"),("Cap Rate","right"),
            ("Implied Value","right"),("SLB Proceeds","right"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, a in enumerate(assets[:30]):
        rb = panel_alt if i % 2 == 0 else bg
        oc = own_colors.get(a.current_ownership, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(a.property_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.property_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.sqft:,}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{oc};border:1px solid {oc};border-radius:2px;letter-spacing:0.06em">{_html.escape(a.current_ownership.replace("_", " "))}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${a.annual_rent_mm:,.3f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.implied_cap_rate * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">${a.implied_value_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"] if a.slb_proceeds_mm > 0 else text_dim};font-weight:600">${a.slb_proceeds_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _leases_table(leases) -> str:
    if not leases:
        return f'<p style="color:{P["text_dim"]};font-size:11px;padding:12px 0">No active leases.</p>'
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    cols = [("Property","left"),("Lease Type","left"),("Years Remaining","right"),
            ("Escalator","right"),("Renewal Options","left"),("Current/Market","right"),("Risk","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, l in enumerate(leases[:20]):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(l.renewal_risk, text_dim)
        mkt_c = P["positive"] if l.market_rent_vs_current < 0.98 else (P["warning"] if l.market_rent_vs_current < 1.05 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(l.property_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.lease_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{l.years_remaining:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{l.annual_escalator_pct * 100:.2f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.renewal_options)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{mkt_c}">{l.market_rent_vs_current:.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{l.renewal_risk}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenarios_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Scenario","left"),("Properties","right"),("SLB Proceeds","right"),
            ("Incremental Rent","right"),("Net EBITDA Δ","right"),("Debt Paydown","right"),
            ("Equity Return","right"),("MOIC Lift","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        eb_c = pos if s.net_ebitda_impact_mm >= 0 else neg
        mc = pos if s.implied_moic_lift >= 0.02 else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.properties_in_scope}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${s.total_slb_proceeds_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.incremental_rent_mm:+,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{eb_c}">${s.net_ebitda_impact_mm:+,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.debt_paydown_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.equity_return_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{mc};font-weight:600">+{s.implied_moic_lift * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_real_estate(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    ev = _f("ev", 300.0)
    ebitda = _f("ebitda", 25.0)
    locations = _i("locations", 18)
    sqft = _i("sqft", 6500)

    from rcm_mc.data_public.real_estate import compute_real_estate
    r = compute_real_estate(sector=sector, revenue_mm=revenue, ev_mm=ev, ebitda_mm=ebitda,
                              n_locations=locations, avg_sqft_per_location=sqft)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Locations", str(len(r.assets)), "", "") +
        ck_kpi_block("Total Sqft", f"{r.total_sqft:,}", "", "") +
        ck_kpi_block("Owned %", f"{r.owned_sqft / r.total_sqft * 100:.0f}%" if r.total_sqft else "0%", "", "") +
        ck_kpi_block("Avg Cap Rate", f"{r.weighted_avg_cap_rate * 100:.2f}%", "", "") +
        ck_kpi_block("Realizable RE", f"${r.realizable_re_value_mm:,.1f}M", "", "") +
        ck_kpi_block("Annual Rent", f"${r.current_annual_rent_mm:,.2f}M", "", "") +
        ck_kpi_block("Occupancy % Rev", f"{r.annual_occupancy_cost_pct_rev * 100:.1f}%", "", "") +
        ck_kpi_block("Rent Savings (C)", f"${r.annual_rent_saved_mm:,.2f}M", "", "")
    )

    own_svg = _ownership_svg(r.total_sqft, r.owned_sqft, r.leased_sqft)
    slb_svg = _slb_waterfall_svg(r.slb_scenarios)
    assets_tbl = _assets_table(r.assets)
    leases_tbl = _leases_table(r.leases)
    scen_tbl = _scenarios_table(r.slb_scenarios)

    form = f"""
<form method="GET" action="/real-estate" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EV ($M)
    <input name="ev" value="{ev}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Locations
    <input name="locations" value="{locations}" type="number" min="1" max="100"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Avg Sqft
    <input name="sqft" value="{sqft}" type="number" step="500"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Real Estate &amp; Sale-Leaseback Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Property inventory, lease terms, SLB scenarios for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Portfolio Ownership Mix</div>
    {own_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">SLB Scenarios — Cash Proceeds &amp; MOIC Lift</div>
    {slb_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">SLB Scenario Detail</div>
    {scen_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Property Inventory</div>
    {assets_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Lease Term Summary</div>
    {leases_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Real Estate Thesis:</strong>
    {r.owned_sqft:,} sqft owned + {r.leased_sqft:,} sqft leased = ${r.realizable_re_value_mm:,.1f}M realizable value.
    SLB at {r.weighted_avg_cap_rate * 100:.2f}% cap rate extracts trapped equity. Owned + related-party
    restructure unlocks ${r.slb_scenarios[1].total_slb_proceeds_mm:,.1f}M for debt paydown / equity distribution.
    Lease renegotiation adds ${r.annual_rent_saved_mm:,.2f}M/yr in EBITDA.
  </div>

</div>"""

    return chartis_shell(body, "Real Estate", active_nav="/real-estate")
