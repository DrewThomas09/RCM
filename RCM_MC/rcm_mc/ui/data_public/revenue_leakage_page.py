"""Revenue Leakage Analyzer page — /revenue-leakage.

Leakage buckets, denial reasons, payer-level leakage, recovery initiatives.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _leakage_bars_svg(buckets) -> str:
    if not buckets:
        return ""
    w = 560
    pad_l, pad_r, pad_t, pad_b = 210, 120, 20, 20
    row_h = 22
    h = len(buckets) * row_h + pad_t + pad_b
    inner_w = w - pad_l - pad_r

    max_v = max(b.annual_leakage_mm for b in buckets) or 1

    bg = P["panel"]; neg = P["negative"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]

    bars = []
    for i, b in enumerate(buckets):
        y = pad_t + i * row_h
        bh = 12
        # Leakage bar (negative)
        leak_w = b.annual_leakage_mm / max_v * inner_w
        # Recoverable portion overlaid in green
        recov_w = b.recoverable_mm / max_v * inner_w
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(b.category[:28])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{leak_w:.1f}" height="{bh}" fill="{neg}" opacity="0.65"/>'
            f'<rect x="{pad_l}" y="{y}" width="{recov_w:.1f}" height="{bh}" fill="{pos}" opacity="0.85"/>'
            f'<text x="{pad_l + leak_w + 6:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">${b.annual_leakage_mm:,.2f}M ({b.annual_leakage_pct * 100:.2f}%)</text>'
        )

    legend = (
        f'<rect x="{pad_l}" y="4" width="10" height="10" fill="{neg}" opacity="0.65"/>'
        f'<text x="{pad_l + 14}" y="13" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Total leakage</text>'
        f'<rect x="{pad_l + 100}" y="4" width="10" height="10" fill="{pos}" opacity="0.85"/>'
        f'<text x="{pad_l + 114}" y="13" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Recoverable portion</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + legend + "".join(bars) +
        f'</svg>'
    )


def _denial_pie_svg(denials) -> str:
    if not denials:
        return ""
    import math
    w, h = 280, 200
    cx, cy = w / 2, h / 2
    r_outer, r_inner = 78, 50

    bg = P["panel"]; text_dim = P["text_dim"]
    colors = [P["accent"], "#8b5cf6", "#14b8a6", P["warning"], "#f97316",
              P["negative"], "#b8732a", P["positive"], "#06b6d4", "#b5321e"]

    total = sum(d.pct_of_denials for d in denials) or 1
    segs = []
    start = -90
    for i, d in enumerate(denials):
        frac = d.pct_of_denials / total
        end = start + frac * 360
        sr = math.radians(start)
        er = math.radians(end)
        x1o = cx + r_outer * math.cos(sr)
        y1o = cy + r_outer * math.sin(sr)
        x2o = cx + r_outer * math.cos(er)
        y2o = cy + r_outer * math.sin(er)
        x1i = cx + r_inner * math.cos(er)
        y1i = cy + r_inner * math.sin(er)
        x2i = cx + r_inner * math.cos(sr)
        y2i = cy + r_inner * math.sin(sr)
        large = 1 if (end - start) > 180 else 0
        color = colors[i % len(colors)]
        path = (f'M {x1o:.1f} {y1o:.1f} A {r_outer} {r_outer} 0 {large} 1 {x2o:.1f} {y2o:.1f} '
                f'L {x1i:.1f} {y1i:.1f} A {r_inner} {r_inner} 0 {large} 0 {x2i:.1f} {y2i:.1f} Z')
        segs.append(f'<path d="{path}" fill="{color}" opacity="0.88"/>')
        start = end

    center = (
        f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" fill="{P["text"]}" '
        f'font-size="13" font-weight="700" font-family="JetBrains Mono,monospace">{len(denials)}</text>'
        f'<text x="{cx}" y="{cy + 11}" text-anchor="middle" fill="{text_dim}" '
        f'font-size="9" letter-spacing="0.08em" font-family="Inter,sans-serif">DENIAL CODES</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(segs) + center +
        f'</svg>'
    )


def _buckets_table(buckets) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; pos = P["positive"]
    cols = [("Leakage Bucket","left"),("Description","left"),("Annual ($M)","right"),
            ("% of Rev","right"),("Recoverable %","right"),("Recoverable ($M)","right"),("vs Best-in-class","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, b in enumerate(buckets):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(b.description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">${b.annual_leakage_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.annual_leakage_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.recoverable_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${b.recoverable_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${b.gap_vs_best_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _denials_table(denials) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; pos = P["positive"]
    cols = [("Code","left"),("Reason","left"),("% of Denials","right"),
            ("Recovery Rate","right"),("Annual Impact ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, d in enumerate(denials):
        rb = panel_alt if i % 2 == 0 else bg
        rc = pos if d.recovery_rate >= 0.6 else (P["warning"] if d.recovery_rate >= 0.3 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.reason_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim}">{_html.escape(d.name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.pct_of_denials * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rc}">{d.recovery_rate * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${d.annual_impact_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _payer_table(payers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    cols = [("Payer","left"),("Denial Rate","right"),("Underpayment Rate","right"),
            ("Total Leakage ($M)","right"),("Top Reason","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(payers):
        rb = panel_alt if i % 2 == 0 else bg
        dc = neg if p.denial_rate >= 0.15 else (P["warning"] if p.denial_rate >= 0.10 else P["positive"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(p.payer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dc}">{p.denial_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.underpayment_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">${p.total_leakage_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.top_reason)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _initiatives_table(initiatives) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    prio_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Initiative","left"),("Target Bucket","left"),("Recovery ($M)","right"),
            ("One-Time Cost","right"),("Annual Cost","right"),("Timeline (mo)","right"),
            ("ROI","right"),("Priority","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, init in enumerate(initiatives):
        rb = panel_alt if i % 2 == 0 else bg
        pc = prio_colors.get(init.priority, text_dim)
        rc = P["positive"] if init.roi >= 2 else (P["accent"] if init.roi >= 0.5 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(init.initiative)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(init.target_bucket)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${init.expected_recovery_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${init.one_time_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${init.annual_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{init.timeline_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rc};font-weight:600">{init.roi:.1f}x</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{init.priority}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_revenue_leakage(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    margin = _f("margin", 0.18)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.revenue_leakage import compute_revenue_leakage
    r = compute_revenue_leakage(sector=sector, net_revenue_mm=revenue, ebitda_margin=margin, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Net Revenue", f"${r.net_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Gross Charges", f"${r.gross_charges_mm:,.0f}M", "", "") +
        ck_kpi_block("Total Leakage", f"${r.total_leakage_mm:,.2f}M", "", "") +
        ck_kpi_block("Leakage % of Rev", f"{r.total_leakage_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Recoverable", f"${r.recoverable_mm:,.2f}M", "", "") +
        ck_kpi_block("Year 1 Net", f"${r.net_recovery_yr1_mm:,.2f}M", "", "") +
        ck_kpi_block("Annual Uplift", f"${r.annualized_ebitda_uplift_mm:,.2f}M", "", "") +
        ck_kpi_block("EV Impact", f"${r.ev_impact_mm:,.1f}M", "", "")
    )

    bars_svg = _leakage_bars_svg(r.buckets)
    pie_svg = _denial_pie_svg(r.denial_reasons)
    buckets_tbl = _buckets_table(r.buckets)
    denials_tbl = _denials_table(r.denial_reasons)
    payer_tbl = _payer_table(r.payer_leakage)
    init_tbl = _initiatives_table(r.initiatives)

    form = f"""
<form method="GET" action="/revenue-leakage" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Net Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin
    <input name="margin" value="{margin}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Revenue Leakage Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Denials, underpayment, charge-capture, bad debt — {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Leakage by Bucket (red = total, green = recoverable)</div>
      {bars_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Denial Reason Distribution</div>
      {pie_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Leakage Bucket Detail</div>
    {buckets_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Denial Code Breakdown</div>
      {denials_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Payer-Level Leakage</div>
      {payer_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Recovery Initiatives</div>
    {init_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Revenue Leakage Thesis:</strong>
    ${r.total_leakage_mm:,.2f}M annual leakage ({r.total_leakage_pct * 100:.1f}% of net revenue). ${r.recoverable_mm:,.2f}M
    realistically recoverable via RCM initiatives. Year 1 net impact ${r.net_recovery_yr1_mm:,.2f}M; steady-state
    annual EBITDA uplift ${r.annualized_ebitda_uplift_mm:,.2f}M worth ${r.ev_impact_mm:,.1f}M of EV at {mult:.1f}x exit.
  </div>

</div>"""

    return chartis_shell(body, "Revenue Leakage", active_nav="/revenue-leakage")
