"""Growth Runway Analyzer page — /growth-runway.

TAM/SAM/SOM, penetration curve, share expansion drivers, market comparables.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _market_nested_svg(sizes) -> str:
    """Nested bars showing TAM > SAM > SOM."""
    if not sizes:
        return ""
    w, h = 540, 180
    pad_l, pad_r, pad_t = 170, 20, 35
    inner_w = w - pad_l - pad_r
    row_h = 34

    max_size = max(s.size_mm for s in sizes) or 1

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    colors = [P["accent"], "#8b5cf6", P["positive"]]

    bars = []
    for i, s in enumerate(sizes):
        y = pad_t + i * row_h
        bh = 22
        bw = s.size_mm / max_size * inner_w
        color = colors[i % len(colors)]
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh / 2 + 4}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(s.level)}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + 6}" y="{y + bh / 2 + 4}" fill="{P["text"]}" font-size="11" '
            f'font-family="JetBrains Mono,monospace;font-weight:600">${s.size_mm:,.0f}M</text>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{y + bh / 2 + 4}" fill="{text_dim}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">Current share: {s.current_capture_pct:.2f}%</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="20" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Market Sizing: TAM → SAM → SOM</text>'
        f'</svg>'
    )


def _penetration_svg(curve) -> str:
    if not curve:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 40, 25, 35
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_rev = max(p.revenue_mm for p in curve) * 1.08

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    pts = []
    for i, p in enumerate(curve):
        x = pad_l + (i / max(len(curve) - 1, 1)) * inner_w
        y = (h - pad_b) - (p.revenue_mm / max_rev) * inner_h
        pts.append(f"{x:.1f},{y:.1f}")

    # Fill area
    poly = pts + [f"{pad_l + inner_w},{h - pad_b}", f"{pad_l},{h - pad_b}"]
    fill = f'<polygon points="{" ".join(poly)}" fill="{acc}" opacity="0.2"/>'
    line = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'

    circles = []
    labels = []
    for i, p in enumerate(curve):
        x = pad_l + (i / max(len(curve) - 1, 1)) * inner_w
        y = (h - pad_b) - (p.revenue_mm / max_rev) * inner_h
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{acc}"/>')
        if i % 2 == 0 or i == len(curve) - 1:
            labels.append(
                f'<text x="{x:.1f}" y="{y - 8:.1f}" fill="{P["text_dim"]}" font-size="9" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace">${p.revenue_mm:,.0f}</text>'
            )
            labels.append(
                f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{p.year}</text>'
            )

    # Y-axis ticks
    ticks = []
    for frac in [0.25, 0.5, 0.75, 1.0]:
        v = max_rev * frac
        yp = (h - pad_b) - frac * inner_h
        ticks.append(
            f'<line x1="{pad_l}" y1="{yp:.1f}" x2="{w - pad_r}" y2="{yp:.1f}" stroke="{border}" stroke-width="0.5" opacity="0.3"/>'
            f'<text x="{pad_l - 4}" y="{yp + 3:.1f}" fill="{text_faint}" font-size="9" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace">${v:,.0f}M</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks) + fill + line + "".join(circles) + "".join(labels) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">10-Year Revenue Penetration Curve</text>'
        f'</svg>'
    )


def _driver_svg(drivers) -> str:
    if not drivers:
        return ""
    sorted_d = sorted(drivers, key=lambda d: -d.implied_revenue_uplift_mm)
    w = 540
    row_h = 22
    h = len(sorted_d) * row_h + 30
    pad_l = 220
    pad_r = 40
    inner_w = w - pad_l - pad_r

    max_v = max(d.implied_revenue_uplift_mm for d in sorted_d) or 1

    bg = P["panel"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    conf_colors = {"high": pos, "medium": P["accent"], "low": P["warning"]}

    bars = []
    for i, d in enumerate(sorted_d):
        y = 20 + i * row_h
        bh = 14
        bw = d.implied_revenue_uplift_mm / max_v * inner_w
        cc = conf_colors.get(d.confidence, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(d.driver[:30])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{cc}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">${d.implied_revenue_uplift_mm:,.0f}M</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Revenue Uplift by Driver ($M over 5 years)</text>'
        f'</svg>'
    )


def _sizes_table(sizes) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Level","left"),("Size ($M)","right"),("Current Share","right"),
            ("Headroom ($M)","right"),("Definition","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(sizes):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.level)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.size_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{s.current_capture_pct:.3f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${s.headroom_mm:,.0f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.definition)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _drivers_table(drivers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    conf_colors = {"high": pos, "medium": P["accent"], "low": P["warning"]}
    cols = [("Driver","left"),("Current %","right"),("Potential %","right"),
            ("Revenue Uplift ($M)","right"),("Timeline (yrs)","right"),("Confidence","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, d in enumerate(drivers):
        rb = panel_alt if i % 2 == 0 else bg
        cc = conf_colors.get(d.confidence, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.driver)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.current_contrib_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{d.potential_contrib_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${d.implied_revenue_uplift_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.timeline_years:.1f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{d.confidence}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _penetration_table(curve) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Year","left"),("Market Share","right"),("Revenue ($M)","right"),
            ("Incremental ($M)","right"),("Cumulative Capture ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(curve):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">Year {p.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{p.market_share_pct:.3f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${p.revenue_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${p.incremental_rev_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.cumulative_capture_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _comparables_table(comps) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Comparable","left"),("Median CAGR","right"),("Top-Quartile CAGR","right"),
            ("Typical Share Shift","right"),("TAM Headroom %","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(comps):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{c.median_cagr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">{c.top_quartile_cagr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.typical_share_shift_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.tam_headroom_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_growth_runway(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    footprint = _f("footprint", 0.02)
    target_share = _f("target_share", 0.035)
    margin = _f("margin", 0.18)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.growth_runway import compute_growth_runway
    r = compute_growth_runway(sector=sector, revenue_mm=revenue, footprint_pct=footprint,
                                target_share_of_footprint=target_share, ebitda_margin=margin,
                                exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Sector TAM", f"${r.tam_b:,.0f}B", "", "") +
        ck_kpi_block("SAM", f"${r.sam_mm:,.0f}M", "", "") +
        ck_kpi_block("SOM", f"${r.som_mm:,.0f}M", "", "") +
        ck_kpi_block("Current Share", f"{r.current_share_pct:.3f}%", "of SAM", "") +
        ck_kpi_block("Target Share", f"{r.target_share_pct:.2f}%", "", "") +
        ck_kpi_block("Market Growth", f"{r.market_growth_pct * 100:.1f}%", "p.a.", "") +
        ck_kpi_block("Terminal Rev", f"${r.implied_terminal_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("MOIC Lift", f"{r.moic_lift_from_growth:.2f}x", "", "")
    )

    sizes_svg = _market_nested_svg(r.market_sizes)
    pen_svg = _penetration_svg(r.penetration_curve)
    driver_svg = _driver_svg(r.growth_drivers)
    sizes_tbl = _sizes_table(r.market_sizes)
    drivers_tbl = _drivers_table(r.growth_drivers)
    pen_tbl = _penetration_table(r.penetration_curve)
    comp_tbl = _comparables_table(r.comparables)

    form = f"""
<form method="GET" action="/growth-runway" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Footprint % of TAM
    <input name="footprint" value="{footprint}" type="number" step="0.005"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Target Share (SAM)
    <input name="target_share" value="{target_share}" type="number" step="0.005"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin
    <input name="margin" value="{margin}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Mult
    <input name="mult" value="{mult}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Growth Runway Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      TAM / SAM / SOM sizing, penetration curve, share gain drivers — {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Market Sizing: TAM → SAM → SOM</div>
    {sizes_svg}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">10-Year Penetration Curve (S-Curve)</div>
      {pen_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Growth Drivers — Revenue Uplift</div>
      {driver_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Market Size Detail</div>
    {sizes_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Growth Driver Decomposition</div>
    {drivers_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Year-by-Year Penetration</div>
      {pen_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Industry Comparable Expansions</div>
      {comp_tbl}
    </div>
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Growth Runway Thesis:</strong>
    ${r.tam_b:,.0f}B TAM, ${r.sam_mm:,.0f}M SAM within footprint, ${r.som_mm:,.0f}M obtainable.
    Current {r.current_share_pct:.3f}% SAM share → target {r.target_share_pct:.2f}% implies
    ${r.total_addressable_upside_mm:,.0f}M of revenue uplift over 10 years. {r.moic_lift_from_growth:.2f}x MOIC lift
    from compounded organic + share-gain + M&amp;A. Confidence: market growth (high), M&amp;A (high),
    geographic expansion (medium).
  </div>

</div>"""

    return chartis_shell(body, "Growth Runway", active_nav="/growth-runway")
