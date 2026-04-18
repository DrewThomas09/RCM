"""Working Capital Analyzer page — /working-capital.

AR/AP/DSO/CCC diligence with payer-level AR breakdown, RCM initiative
library, and multi-year cash bridge projection.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _dso_trajectory_svg(bridge) -> str:
    if not bridge:
        return ""
    w, h = 540, 180
    pad_l, pad_r, pad_t, pad_b = 40, 20, 20, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    dsos = [b.dso_days for b in bridge]
    max_dso = max(dsos) * 1.10 if dsos else 60
    min_dso = min(dsos) * 0.85

    bg = P["panel"]
    acc = P["accent"]
    pos = P["positive"]
    text_faint = P["text_faint"]
    border = P["border"]

    # Points
    pts = []
    line_pts = []
    for i, b in enumerate(bridge):
        x = pad_l + (i / max(len(bridge) - 1, 1)) * inner_w
        y_norm = (b.dso_days - min_dso) / (max_dso - min_dso) if max_dso > min_dso else 0.5
        y = (h - pad_b) - y_norm * inner_h
        line_pts.append(f"{x:.1f},{y:.1f}")
        pts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{acc}"/>'
            f'<text x="{x:.1f}" y="{y - 8:.1f}" fill="{P["text_dim"]}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{b.dso_days:.0f}d</text>'
            f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{b.year}</text>'
        )

    line = f'<polyline points="{" ".join(line_pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'

    ticks = []
    for v in [min_dso, (min_dso + max_dso) / 2, max_dso]:
        frac = (v - min_dso) / (max_dso - min_dso) if max_dso > min_dso else 0.5
        yp = (h - pad_b) - frac * inner_h
        ticks.append(
            f'<line x1="{pad_l - 4}" y1="{yp}" x2="{w - pad_r}" y2="{yp}" stroke="{border}" stroke-width="0.5"/>'
            f'<text x="{pad_l - 6}" y="{yp + 3}" fill="{text_faint}" font-size="9" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{v:.0f}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks) + line + "".join(pts)
        + f'<text x="{pad_l}" y="14" fill="{P["text_dim"]}" font-size="10" font-family="Inter,sans-serif">DSO Days by Year</text>'
        + f'</svg>'
    )


def _cash_bridge_svg(bridge) -> str:
    if not bridge:
        return ""
    w, h = 540, 200
    pad_l, pad_r, pad_t, pad_b = 50, 30, 25, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    fcfs = [b.fcf_mm for b in bridge]
    cums = [b.cum_cash_released_mm for b in bridge]
    max_v = max(max(fcfs, default=1), max(cums, default=1)) * 1.15
    min_v = min(min(fcfs, default=0), 0)

    n = len(bridge)
    bar_w = (inner_w - (n - 1) * 8) / n / 2

    bg = P["panel"]
    pos = P["positive"]
    warn = P["warning"]
    text_faint = P["text_faint"]
    border = P["border"]

    zero_y = (h - pad_b) - (0 - min_v) / (max_v - min_v) * inner_h

    bars = []
    for i, b in enumerate(bridge):
        x_base = pad_l + i * ((inner_w) / n)
        # FCF bar
        x1 = x_base
        fh = abs(b.fcf_mm) / (max_v - min_v) * inner_h
        fy = zero_y - fh if b.fcf_mm >= 0 else zero_y
        fcolor = pos if b.fcf_mm >= 0 else P["negative"]
        bars.append(f'<rect x="{x1:.1f}" y="{fy:.1f}" width="{bar_w:.1f}" height="{fh:.1f}" fill="{fcolor}" opacity="0.85"/>')
        # Cum released bar
        x2 = x_base + bar_w + 2
        ch = b.cum_cash_released_mm / (max_v - min_v) * inner_h
        cy = zero_y - ch
        bars.append(f'<rect x="{x2:.1f}" y="{cy:.1f}" width="{bar_w:.1f}" height="{ch:.1f}" fill="{warn}" opacity="0.85"/>')
        # labels
        bars.append(
            f'<text x="{x1 + bar_w:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{b.year}</text>'
        )

    legend = (
        f'<rect x="{pad_l}" y="4" width="10" height="10" fill="{pos}" opacity="0.85"/>'
        f'<text x="{pad_l + 14}" y="13" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">FCF</text>'
        f'<rect x="{pad_l + 50}" y="4" width="10" height="10" fill="{warn}" opacity="0.85"/>'
        f'<text x="{pad_l + 64}" y="13" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">Cum. Cash Released</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        f'<line x1="{pad_l}" y1="{zero_y}" x2="{w - pad_r}" y2="{zero_y}" stroke="{border}" stroke-width="1"/>'
        + legend + "".join(bars)
        + f'</svg>'
    )


def _payer_ar_table(payer_ar) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Payer","left"),("% of AR","right"),("DSO (days)","right"),("AR Balance ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(payer_ar):
        rb = panel_alt if i % 2 == 0 else bg
        dso_color = P["positive"] if p.dso_days < 40 else (P["warning"] if p.dso_days < 65 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(p.payer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.pct_of_ar*100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dso_color}">{p.dso_days:.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.ar_balance_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _improvements_table(improvements) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Initiative","left"),("DSO Δ (days)","right"),("Cash Release ($M)","right"),
            ("Ongoing FCF ($M/yr)","right"),("Timeline (mo)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, im in enumerate(improvements):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(im.initiative)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">-{im.dso_reduction_days:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${im.cash_release_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${im.ongoing_fcf_impact_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{im.timeline_months} mo</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _bridge_table(bridge) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Year","left"),("Revenue","right"),("EBITDA","right"),("DSO","right"),
            ("AR Bal.","right"),("NWC","right"),("FCF","right"),("Cum. Released","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, b in enumerate(bridge):
        rb = panel_alt if i % 2 == 0 else bg
        fcf_color = pos if b.fcf_mm > 0 else P["negative"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">Year {b.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${b.revenue_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${b.ebitda_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.dso_days:.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${b.ar_balance_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${b.nwc_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{fcf_color};font-weight:600">${b.fcf_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${b.cum_cash_released_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_working_capital(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 100.0)
    margin = _f("margin", 0.18)
    hold = _i("hold_years", 5)
    growth = _f("growth", 0.04)

    from rcm_mc.data_public.working_capital import compute_working_capital
    r = compute_working_capital(
        sector=sector, revenue_mm=revenue, ebitda_margin=margin,
        hold_years=hold, organic_growth_pct=growth,
    )
    b = r.baseline

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("DSO", f"{b.dso_days:.0f}d", "", "") +
        ck_kpi_block("DPO", f"{b.dpo_days:.0f}d", "", "") +
        ck_kpi_block("CCC", f"{b.ccc_days:.0f}d", "", "") +
        ck_kpi_block("AR Balance", f"${b.ar_balance_mm:,.1f}M", "", "") +
        ck_kpi_block("NWC", f"${b.nwc_mm:,.1f}M", "", "") +
        ck_kpi_block("NWC / Rev", f"{b.nwc_pct_revenue*100:.1f}%", "", "") +
        ck_kpi_block("One-time Unlock", f"${r.total_cash_unlock_mm:,.1f}M", "", "") +
        ck_kpi_block("Annual FCF Uplift", f"${r.annual_fcf_uplift_mm:,.2f}M", "", "")
    )

    dso_svg = _dso_trajectory_svg(r.cash_bridge)
    cash_svg = _cash_bridge_svg(r.cash_bridge)
    payer_tbl = _payer_ar_table(r.payer_ar)
    init_tbl = _improvements_table(r.improvements)
    bridge_tbl = _bridge_table(r.cash_bridge)

    form = f"""
<form method="GET" action="/working-capital" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="1"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin
    <input name="margin" value="{margin}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Hold (yrs)
    <input name="hold_years" value="{hold}" type="number" min="2" max="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:50px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Growth
    <input name="growth" value="{growth}" type="number" step="0.01"
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Working Capital Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      AR/AP/DSO diligence for {_html.escape(sector)} — cash conversion cycle and RCM-driven FCF uplift
      across {hold} years — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">DSO Trajectory</div>
      {dso_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">FCF &amp; Cumulative Cash Released</div>
      {cash_svg}
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">AR Balance by Payer</div>
      {payer_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">RCM Initiative Library ({len(r.improvements)} levers)</div>
      {init_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Multi-Year Cash Bridge</div>
    {bridge_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Working Capital Thesis:</strong>
    Baseline ${b.ar_balance_mm:,.1f}M tied up in AR at {b.dso_days:.0f}-day DSO. RCM initiatives can unlock
    ~${r.total_cash_unlock_mm:,.1f}M one-time and ${r.annual_fcf_uplift_mm:,.2f}M/year in ongoing FCF —
    a direct accretion to LP cash-on-cash returns.
  </div>

</div>"""

    return chartis_shell(body, "Working Capital Analyzer", active_nav="/working-capital")
