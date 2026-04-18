"""Unit Economics Analyzer page — /unit-economics.

Per-location revenue, ramp curves, visit/provider profitability, site scenarios.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _ramp_svg(ramp) -> str:
    if not ramp:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_cum = max((r.cumulative_cash_mm for r in ramp), default=1.0)
    min_cum = min((r.cumulative_cash_mm for r in ramp), default=-1.0)
    max_rev_pct = 1.0

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    # Revenue % line
    rev_pts = []
    for i, r in enumerate(ramp):
        x = pad_l + (i / max(len(ramp) - 1, 1)) * inner_w
        y = (h - pad_b) - r.revenue_pct_of_mature * inner_h * 0.55
        rev_pts.append(f"{x:.1f},{y:.1f}")

    rev_line = f'<polyline points="{" ".join(rev_pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'

    # Cum cash line (dual axis)
    cash_range = max_cum - min_cum
    cash_pts = []
    for i, r in enumerate(ramp):
        x = pad_l + (i / max(len(ramp) - 1, 1)) * inner_w
        y = (h - pad_b) - ((r.cumulative_cash_mm - min_cum) / cash_range) * inner_h
        cash_pts.append(f"{x:.1f},{y:.1f}")

    cash_line = f'<polyline points="{" ".join(cash_pts)}" fill="none" stroke="{pos}" stroke-width="2" stroke-dasharray="4,3"/>'

    # Zero cash line
    zero_y = (h - pad_b) - ((0 - min_cum) / cash_range) * inner_h
    zero_line = f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{w - pad_r}" y2="{zero_y:.1f}" stroke="{neg}" stroke-width="1" stroke-dasharray="3,3" opacity="0.6"/>'

    # Breakeven marker
    breakeven = next((r for r in ramp if r.breakeven_reached), None)
    be_marker = ""
    if breakeven:
        be_idx = ramp.index(breakeven)
        be_x = pad_l + (be_idx / max(len(ramp) - 1, 1)) * inner_w
        be_marker = (
            f'<line x1="{be_x:.1f}" y1="{pad_t}" x2="{be_x:.1f}" y2="{h - pad_b}" stroke="{P["warning"]}" stroke-width="1" stroke-dasharray="3,3" opacity="0.5"/>'
            f'<text x="{be_x:.1f}" y="{pad_t - 5}" fill="{P["warning"]}" font-size="9" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace">Breakeven M{breakeven.month}</text>'
        )

    # Axis ticks (month)
    ticks = []
    for m in [1, len(ramp) // 3, len(ramp) * 2 // 3, len(ramp)]:
        x = pad_l + ((m - 1) / max(len(ramp) - 1, 1)) * inner_w
        ticks.append(
            f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">M{m}</text>'
        )

    legend = (
        f'<line x1="{pad_l}" y1="10" x2="{pad_l + 20}" y2="10" stroke="{acc}" stroke-width="2"/>'
        f'<text x="{pad_l + 24}" y="14" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Revenue % of mature</text>'
        f'<line x1="{pad_l + 140}" y1="10" x2="{pad_l + 160}" y2="10" stroke="{pos}" stroke-width="2" stroke-dasharray="4,3"/>'
        f'<text x="{pad_l + 164}" y="14" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Cumulative cash ($M)</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + legend + zero_line + be_marker + rev_line + cash_line + "".join(ticks)
        + f'</svg>'
    )


def _site_scenario_svg(scenarios) -> str:
    if not scenarios:
        return ""
    w, h = 480, 200
    pad_l, pad_r, pad_t, pad_b = 120, 30, 20, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    row_h = (inner_h - 10) / len(scenarios)

    max_v = max((s.contribution_mm for s in scenarios), default=1)
    min_v = min((s.contribution_mm for s in scenarios), default=0)
    if min_v > 0:
        min_v = 0
    span = max_v - min_v or 1

    bg = P["panel"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    center_x = pad_l + ((0 - min_v) / span) * inner_w

    bars = []
    for i, s in enumerate(scenarios):
        y = pad_t + i * row_h + 2
        bh = row_h - 8
        if s.contribution_mm >= 0:
            xr = center_x
            bw = (s.contribution_mm / span) * inner_w
            color = pos
        else:
            bw = (abs(s.contribution_mm) / span) * inner_w
            xr = center_x - bw
            color = neg
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh / 2 + 3}" fill="{text_dim}" font-size="11" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario)}</text>'
            f'<rect x="{xr:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{xr + bw + 6:.1f}" y="{y + bh / 2 + 3}" fill="{color}" '
            f'font-size="10" font-family="JetBrains Mono,monospace;font-weight:600">${s.contribution_mm:+,.2f}M</text>'
        )

    axis = (
        f'<line x1="{center_x:.1f}" y1="{pad_t}" x2="{center_x:.1f}" y2="{h - pad_b}" '
        f'stroke="{border}" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + axis + "".join(bars) +
        f'</svg>'
    )


def _metric_table(metrics) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"above": P["positive"], "benchmark": P["accent"], "below": P["negative"]}
    cols = [("Location Metric","left"),("Value","right"),("Unit","left"),("Benchmark","right"),
            ("Δ vs Bench","right"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(metrics):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(m.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{m.value:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.benchmark:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sc}">{m.delta_vs_bench * 100:+.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _visit_table(visits) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Visit Category","left"),("% Mix","right"),("Annual Volume","right"),
            ("Avg Reimb ($)","right"),("Avg Cost ($)","right"),("Contribution ($)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, v in enumerate(visits):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(v.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.pct_of_visits * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.annual_volume:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${v.avg_reimbursement:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${v.avg_cost:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${v.contribution_per_visit:.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _provider_table(providers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Role","left"),("Annual Visits","right"),("Revenue ($M)","right"),
            ("Comp ($K)","right"),("Net Margin ($M)","right"),("ROI","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(providers):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(p.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.annual_visits_per_provider:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.annual_revenue_per_provider_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.comp_per_provider_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${p.net_margin_per_provider_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{p.roi_multiple:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenario_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Scenario","left"),("Revenue ($M)","right"),("Contribution ($M)","right"),
            ("CM %","right"),("Cash Flow ($M)","right"),("Payback (yrs)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        cm_c = pos if s.contribution_margin_pct >= 0.25 else (P["warning"] if s.contribution_margin_pct >= 0.15 else neg)
        cash_c = pos if s.cash_flow_mm >= 0 else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.revenue_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.contribution_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cm_c};font-weight:600">{s.contribution_margin_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cash_c}">${s.cash_flow_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.years_to_payback:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_unit_economics(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Dermatology") or "Dermatology"

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    locs = _i("locations", 25)

    from rcm_mc.data_public.unit_economics import compute_unit_economics
    r = compute_unit_economics(sector=sector, num_locations=locs)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Sector", sector, "", "") +
        ck_kpi_block("Locations", str(r.num_locations), "", "") +
        ck_kpi_block("Total Revenue", f"${r.total_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Revenue / Loc", f"${r.revenue_per_location_mm:,.2f}M", "", "") +
        ck_kpi_block("Payback", f"{r.payback_years:.1f} yrs", "", "") +
        ck_kpi_block("De Novo IRR", f"{r.de_novo_irr * 100:.1f}%", "", "") +
        ck_kpi_block("Visits / New Site", f"{r.new_site_annual_capacity:,}", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    ramp_svg = _ramp_svg(r.ramp_curve)
    scen_svg = _site_scenario_svg(r.site_scenarios)
    metric_tbl = _metric_table(r.location_metrics)
    visit_tbl = _visit_table(r.visit_profile)
    provider_tbl = _provider_table(r.provider_yield)
    scen_tbl = _scenario_table(r.site_scenarios)

    form = f"""
<form method="GET" action="/unit-economics" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Locations
    <input name="locations" value="{locs}" type="number" min="1" max="500"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Unit Economics Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Per-location, per-visit, per-provider economics with ramp curves and de novo IRR for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">New Site Ramp Curve &amp; Payback</div>
      {ramp_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Site Contribution Scenarios</div>
      {scen_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Location-Level Metrics vs Sector Benchmark</div>
    {metric_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Per-Visit Profitability</div>
      {visit_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Per-Provider Yield</div>
      {provider_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Site Scenarios (Mature / New / Underperforming)</div>
    {scen_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Unit Economics Thesis:</strong>
    {_html.escape(sector)} average site: ${r.revenue_per_location_mm:,.2f}M revenue, payback {r.payback_years:.1f} years,
    de novo IRR {r.de_novo_irr * 100:.1f}%. Strong unit economics drive roll-up returns — every new site
    contributes independently to the bolt-on accretion thesis.
  </div>

</div>"""

    return chartis_shell(body, "Unit Economics", active_nav="/unit-economics")
