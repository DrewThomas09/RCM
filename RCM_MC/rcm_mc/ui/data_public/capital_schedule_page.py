"""Capital Schedule page — /capital-schedule.

Capital calls/distributions, J-curve, DPI/TVPI, LP waterfall by quarter.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _jcurve_svg(quarters) -> str:
    """J-curve: cumulative net cash flow by quarter."""
    if not quarters:
        return ""
    w, h = 600, 240
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    # Compute cumulative net cash flow
    cum_cf = [0]
    c = 0
    for q in quarters:
        c += q.net_cash_flow_mm
        cum_cf.append(c)
    cum_cf = cum_cf[1:]

    max_cf = max(cum_cf) or 1
    min_cf = min(cum_cf)
    range_cf = max_cf - min_cf or 1

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    zero_y = (h - pad_b) - ((0 - min_cf) / range_cf) * inner_h

    # Line
    pts = []
    for i, cf in enumerate(cum_cf):
        x = pad_l + (i / max(len(cum_cf) - 1, 1)) * inner_w
        y = (h - pad_b) - ((cf - min_cf) / range_cf) * inner_h
        pts.append(f"{x:.1f},{y:.1f}")

    # Fill area under curve
    poly_pts = pts + [f"{pad_l + inner_w},{zero_y:.1f}", f"{pad_l},{zero_y:.1f}"]
    fill = f'<polygon points="{" ".join(poly_pts)}" fill="{acc}" opacity="0.18"/>'

    line = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'

    # Zero line
    zero_line = (f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{w - pad_r}" y2="{zero_y:.1f}" '
                 f'stroke="{border}" stroke-width="1" stroke-dasharray="3,3"/>')

    # Year labels
    labels = []
    for y in [1, 3, 5, 7, 10]:
        if y <= len(quarters) // 4:
            x = pad_l + ((y - 1) * 4 / max(len(quarters) - 1, 1)) * inner_w
            labels.append(
                f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="10" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{y}</text>'
            )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + fill + zero_line + line + "".join(labels) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Cumulative Net Cash Flow ($M) — The J-Curve</text>'
        f'<text x="{w - pad_r}" y="{20}" fill="{pos}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">Peak: +${max(cum_cf):,.0f}M</text>'
        f'<text x="{w - pad_r}" y="{35}" fill="{neg}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">Trough: ${min(cum_cf):,.0f}M</text>'
        f'</svg>'
    )


def _tvpi_dpi_svg(quarters) -> str:
    """TVPI and DPI over time."""
    if not quarters:
        return ""
    w, h = 600, 220
    pad_l, pad_r, pad_t, pad_b = 55, 30, 30, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_v = max(q.tvpi for q in quarters) * 1.1 or 3

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    def _line(values, color, label):
        pts = []
        for i, v in enumerate(values):
            x = pad_l + (i / max(len(values) - 1, 1)) * inner_w
            y = (h - pad_b) - (v / max_v) * inner_h
            pts.append(f"{x:.1f},{y:.1f}")
        return f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>'

    tvpi_line = _line([q.tvpi for q in quarters], acc, "TVPI")
    dpi_line = _line([q.dpi for q in quarters], pos, "DPI")

    # 1x reference
    y_1x = (h - pad_b) - (1 / max_v) * inner_h
    ref = (f'<line x1="{pad_l}" y1="{y_1x:.1f}" x2="{w - pad_r}" y2="{y_1x:.1f}" '
           f'stroke="{border}" stroke-width="1" stroke-dasharray="2,3"/>'
           f'<text x="{pad_l - 4}" y="{y_1x + 3:.1f}" fill="{text_faint}" font-size="9" text-anchor="end" '
           f'font-family="JetBrains Mono,monospace">1.00x</text>')

    # Ticks
    ticks = []
    for v in [0.5, 1.5, 2.0, 2.5, 3.0]:
        if v <= max_v:
            yp = (h - pad_b) - (v / max_v) * inner_h
            ticks.append(
                f'<line x1="{pad_l - 4}" y1="{yp:.1f}" x2="{w - pad_r}" y2="{yp:.1f}" stroke="{border}" stroke-width="0.5" opacity="0.4"/>'
                f'<text x="{pad_l - 4}" y="{yp + 3:.1f}" fill="{text_faint}" font-size="9" text-anchor="end" '
                f'font-family="JetBrains Mono,monospace">{v:.1f}x</text>'
            )

    legend = (
        f'<line x1="{pad_l}" y1="12" x2="{pad_l + 20}" y2="12" stroke="{acc}" stroke-width="2"/>'
        f'<text x="{pad_l + 24}" y="15" fill="{text_dim}" font-size="10" font-family="JetBrains Mono,monospace">TVPI</text>'
        f'<line x1="{pad_l + 75}" y1="12" x2="{pad_l + 95}" y2="12" stroke="{pos}" stroke-width="2"/>'
        f'<text x="{pad_l + 99}" y="15" fill="{text_dim}" font-size="10" font-family="JetBrains Mono,monospace">DPI</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks) + ref + tvpi_line + dpi_line + legend +
        f'</svg>'
    )


def _quarters_table(quarters) -> str:
    """Show annual summary (group by year)."""
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]

    # Aggregate to yearly
    by_year: Dict[int, List] = {}
    for q in quarters:
        by_year.setdefault(q.year, []).append(q)

    cols = [("Year","left"),("Calls","right"),("Distributions","right"),("Net CF","right"),
            ("Cumulative Called","right"),("Cumulative Dist","right"),("NAV","right"),
            ("DPI","right"),("TVPI","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, (yr, qs) in enumerate(sorted(by_year.items())):
        rb = panel_alt if i % 2 == 0 else bg
        total_call = sum(q.call_mm for q in qs)
        total_dist = sum(q.distribution_mm for q in qs)
        net_cf = total_dist - total_call
        last = qs[-1]
        cf_color = pos if net_cf >= 0 else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">Year {yr}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${total_call:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${total_dist:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cf_color};font-weight:600">${net_cf:+,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${last.cumulative_called_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${last.cumulative_distributed_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${last.nav_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{last.dpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{last.tvpi:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _lp_table(lps) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("LP Class","left"),("Commitment ($M)","right"),("% of Fund","right"),
            ("Hurdle","right"),("Mgmt Fee","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, lp in enumerate(lps):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(lp.name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${lp.commitment_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{lp.pct_of_fund * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{lp.hurdle_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{lp.mgmt_fee * 100:.2f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _waterfall_table(tiers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Waterfall Tier","left"),("Threshold","left"),("LP Share","right"),
            ("GP Share","right"),("Est Timing (yr)","right"),("Est Amount ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, t in enumerate(tiers):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(t.tier)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.threshold)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{t.lp_share * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{t.gp_share * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">Y{t.est_timing_year:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${t.est_amount_mm:,.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_capital_schedule(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    fund = _f("fund", 500.0)
    inv_yrs = _i("investment_years", 5)
    total_yrs = _i("total_years", 10)

    from rcm_mc.data_public.capital_schedule import compute_capital_schedule
    r = compute_capital_schedule(fund_size_mm=fund, investment_years=inv_yrs, total_years=total_yrs)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Fund Size", f"${r.fund_size_mm:,.0f}M", "", "") +
        ck_kpi_block("Gross MOIC", f"{r.gross_moic:.2f}x", "", "") +
        ck_kpi_block("Net MOIC", f"{r.net_moic:.2f}x", "", "") +
        ck_kpi_block("Gross IRR", f"{r.gross_irr * 100:.1f}%", "", "") +
        ck_kpi_block("Net IRR", f"{r.net_irr * 100:.1f}%", "", "") +
        ck_kpi_block("Final DPI", f"{r.final_dpi:.2f}x", "", "") +
        ck_kpi_block("Trough (J-curve)", f"${r.trough_jcurve_mm:,.0f}M", "", "") +
        ck_kpi_block("Peak NAV", f"${r.peak_nav_mm:,.0f}M", "", "")
    )

    jcurve_svg = _jcurve_svg(r.quarters)
    tvpi_svg = _tvpi_dpi_svg(r.quarters)
    qtr_tbl = _quarters_table(r.quarters)
    lp_tbl = _lp_table(r.lp_classes)
    wf_tbl = _waterfall_table(r.waterfall_tiers)

    form = f"""
<form method="GET" action="/capital-schedule" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Fund Size ($M)
    <input name="fund" value="{fund}" type="number" step="50"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Investment Period (yr)
    <input name="investment_years" value="{inv_yrs}" type="number" min="3" max="8"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Total Fund Life (yr)
    <input name="total_years" value="{total_yrs}" type="number" min="8" max="15"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Capital Call &amp; Distribution Schedule</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Fund lifecycle cash flows — J-curve, DPI/TVPI trajectory, LP waterfall — ${r.fund_size_mm:,.0f}M fund / {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">J-Curve — Cumulative Net Cash Flow</div>
      {jcurve_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">TVPI &amp; DPI Trajectory</div>
      {tvpi_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Annual Capital Schedule</div>
    {qtr_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">LP Investor Base</div>
      {lp_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">European Waterfall</div>
      {wf_tbl}
    </div>
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Capital Thesis:</strong>
    ${r.fund_size_mm:,.0f}M fund with {r.investment_period_years}-year investment period and
    {r.total_years}-year life. J-curve trough ${r.trough_jcurve_mm:,.0f}M at Year {r.trough_jcurve_year:.1f},
    peak NAV ${r.peak_nav_mm:,.0f}M at Year {r.peak_nav_year}. Gross IRR {r.gross_irr * 100:.1f}% / Net IRR {r.net_irr * 100:.1f}%.
    Final TVPI {r.final_tvpi:.2f}x, DPI {r.final_dpi:.2f}x.
  </div>

</div>"""

    return chartis_shell(body, "Capital Schedule", active_nav="/capital-schedule")
