"""Payer Mix Shift Simulator page — /payer-shift.

Models MOIC impact of payer re-mix: rate index, collection rate, weighted yield,
multi-year revenue/EBITDA projection.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _mix_bar_svg(start_mix, target_mix) -> str:
    if not start_mix or not target_mix:
        return ""
    w, h = 560, 200
    pad_l, pad_r, pad_t, pad_b = 20, 20, 30, 20
    inner_w = w - pad_l - pad_r
    bar_h = 36

    bg = P["panel"]; text_dim = P["text_dim"]; text = P["text"]
    colors = [P["accent"], "#8b5cf6", "#14b8a6", P["warning"], "#f97316", P["negative"]]

    def _render_bar(mix, y, label):
        segs = []
        x = pad_l
        for i, m in enumerate(mix):
            if m.pct <= 0:
                continue
            seg_w = m.pct * inner_w
            color = colors[i % len(colors)]
            segs.append(
                f'<rect x="{x:.1f}" y="{y}" width="{seg_w:.1f}" height="{bar_h}" fill="{color}" opacity="0.85"/>'
            )
            if seg_w > 45:
                segs.append(
                    f'<text x="{x + seg_w / 2:.1f}" y="{y + bar_h / 2 + 4:.1f}" fill="{P["text"]}" '
                    f'font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{m.pct * 100:.0f}%</text>'
                )
            x += seg_w
        segs.append(
            f'<text x="{pad_l}" y="{y - 4}" fill="{text_dim}" font-size="10" '
            f'font-family="Inter,sans-serif">{_html.escape(label)}</text>'
        )
        return "".join(segs)

    start_bar = _render_bar(start_mix, pad_t, "Entry Mix (Year 0)")
    target_bar = _render_bar(target_mix, pad_t + bar_h + 40, "Target Mix (Exit)")

    # Legend
    legend = ""
    for i, m in enumerate(start_mix[:6]):
        lx = pad_l + i * 90
        ly = h - 5
        legend += (
            f'<rect x="{lx}" y="{ly - 9}" width="8" height="8" fill="{colors[i % len(colors)]}" opacity="0.85"/>'
            f'<text x="{lx + 12}" y="{ly - 2}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">{_html.escape(m.payer[:10])}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + start_bar + target_bar + legend
        + f'</svg>'
    )


def _scenario_svg(scenarios) -> str:
    if not scenarios:
        return ""
    w, h = 540, 210
    pad_l, pad_r, pad_t, pad_b = 180, 40, 20, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    row_h = (inner_h - 10) / len(scenarios)

    max_abs = max((abs(s.ev_impact_mm) for s in scenarios), default=1)

    bg = P["panel"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    center_x = pad_l + inner_w / 2

    bars = []
    for i, s in enumerate(scenarios):
        y = pad_t + i * row_h + 2
        bh = row_h - 8
        color = pos if s.ev_impact_mm >= 0 else neg
        bw = abs(s.ev_impact_mm) / max_abs * (inner_w / 2)
        xr = center_x if s.ev_impact_mm >= 0 else center_x - bw
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh / 2 + 3}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(s.label[:26])}</text>'
            f'<rect x="{xr:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{xr + bw + 4 if s.ev_impact_mm >= 0 else xr - 4:.1f}" y="{y + bh / 2 + 3}" fill="{color}" '
            f'font-size="10" text-anchor="{"start" if s.ev_impact_mm >= 0 else "end"}" '
            f'font-family="JetBrains Mono,monospace;font-weight:600">${s.ev_impact_mm:+,.1f}M</text>'
        )

    axis = (
        f'<line x1="{center_x:.1f}" y1="{pad_t}" x2="{center_x:.1f}" y2="{h - pad_b}" '
        f'stroke="{border}" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + axis + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">EV Impact ($M) by Payer Shift Scenario</text>'
        f'</svg>'
    )


def _projection_svg(yearly) -> str:
    if not yearly:
        return ""
    w, h = 560, 200
    pad_l, pad_r, pad_t, pad_b = 50, 30, 20, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_rev = max(y.revenue_mm for y in yearly) * 1.10
    min_rev = min(y.revenue_mm for y in yearly) * 0.85

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    # Revenue line
    pts = []
    for i, y in enumerate(yearly):
        x = pad_l + (i / max(len(yearly) - 1, 1)) * inner_w
        y_coord = (h - pad_b) - ((y.revenue_mm - min_rev) / (max_rev - min_rev)) * inner_h
        pts.append(f"{x:.1f},{y_coord:.1f}")

    line = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'

    # Yield bar chart below
    circles = []
    for i, y in enumerate(yearly):
        x = pad_l + (i / max(len(yearly) - 1, 1)) * inner_w
        y_coord = (h - pad_b) - ((y.revenue_mm - min_rev) / (max_rev - min_rev)) * inner_h
        circles.append(
            f'<circle cx="{x:.1f}" cy="{y_coord:.1f}" r="3" fill="{acc}"/>'
            f'<text x="{x:.1f}" y="{y_coord - 8:.1f}" fill="{text_dim}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">${y.revenue_mm:,.0f}M</text>'
            f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{y.year}</text>'
            f'<text x="{x:.1f}" y="{h - pad_b + 26}" fill="{pos}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{y.weighted_yield:.3f}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + line + "".join(circles) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Revenue &amp; Yield Projection</text>'
        f'</svg>'
    )


def _mix_table(mix, title: str) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Payer","left"),("% Mix","right"),("Rate Index","right"),
            ("Collection %","right"),("Weighted Yield","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(mix):
        rb = panel_alt if i % 2 == 0 else bg
        rate_c = P["positive"] if m.rate_index >= 0.9 else (P["warning"] if m.rate_index >= 0.6 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.payer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{m.pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rate_c}">{m.rate_index:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.collection_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">{m.weighted_yield:.3f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenario_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Scenario","left"),("Description","left"),("Comm Start→End","left"),
            ("Medicaid Start→End","left"),("Yield Δ","right"),("Revenue Δ","right"),
            ("EBITDA Δ","right"),("EV Δ","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        ec = pos if s.ev_impact_mm >= 0 else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.label)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(s.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{s.start_commercial_pct * 100:.0f}% → {s.end_commercial_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{s.start_medicaid_pct * 100:.0f}% → {s.end_medicaid_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ec}">{s.yield_change_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ec}">${s.revenue_impact_mm:+,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ec}">${s.ebitda_impact_mm:+,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ec};font-weight:600">${s.ev_impact_mm:+,.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _projection_table(yearly) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Year","left"),("Commercial","right"),("Medicare","right"),("Medicaid","right"),
            ("Self-Pay","right"),("Yield","right"),("Revenue ($M)","right"),("EBITDA ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, y in enumerate(yearly):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">Year {y.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{y.commercial_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{y.medicare_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{y.medicaid_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{y.self_pay_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{y.weighted_yield:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${y.revenue_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${y.ebitda_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_payer_shift(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    margin = _f("margin", 0.18)
    mult = _f("mult", 11.0)
    hold = _i("hold_years", 5)
    growth = _f("growth", 0.04)

    from rcm_mc.data_public.payer_shift import compute_payer_shift
    r = compute_payer_shift(sector=sector, revenue_mm=revenue, ebitda_margin=margin,
                             exit_multiple=mult, hold_years=hold, growth_pct=growth)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; acc = P["accent"]

    start_yield = r.yearly_projection[0].weighted_yield if r.yearly_projection else 0
    end_yield = r.yearly_projection[-1].weighted_yield if r.yearly_projection else 0
    yield_chg = (end_yield / start_yield - 1) if start_yield else 0
    ev_color = pos if r.total_ev_impact_mm >= 0 else neg

    kpi_strip = (
        ck_kpi_block("Base Revenue", f"${r.base_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Terminal Rev", f"${r.terminal_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Entry Yield", f"{start_yield:.3f}", "", "") +
        ck_kpi_block("Exit Yield", f"{end_yield:.3f}", "", "") +
        ck_kpi_block("Yield Δ", f"{yield_chg * 100:+.1f}%", "", "") +
        ck_kpi_block("EBITDA Impact", f"${r.total_ebitda_impact_mm:+,.1f}M", "", "") +
        ck_kpi_block("EV Impact", f"${r.total_ev_impact_mm:+,.1f}M", "", "") +
        ck_kpi_block("Scenarios", str(len(r.scenarios)), "", "")
    )

    mix_svg = _mix_bar_svg(r.starting_mix, r.target_mix)
    scen_svg = _scenario_svg(r.scenarios)
    proj_svg = _projection_svg(r.yearly_projection)
    start_tbl = _mix_table(r.starting_mix, "Starting")
    target_tbl = _mix_table(r.target_mix, "Target")
    scen_tbl = _scenario_table(r.scenarios)
    proj_tbl = _projection_table(r.yearly_projection)

    form = f"""
<form method="GET" action="/payer-shift" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="5"
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
  <label style="font-size:11px;color:{text_dim}">Hold Years
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
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Payer Mix Shift Simulator</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Rate index, collection rate, weighted yield — modeled across {hold}-year hold in {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Entry → Target Payer Mix</div>
    {mix_svg}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Entry Mix Detail</div>
      {start_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Target Mix Detail</div>
      {target_tbl}
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Scenario EV Impact</div>
      {scen_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Revenue &amp; Yield Projection</div>
      {proj_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Payer Shift Scenarios</div>
    {scen_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Year-by-Year Projection ({_html.escape(sector)})</div>
    {proj_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {ev_color};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Payer Mix Thesis:</strong>
    Entry weighted yield {start_yield:.3f} → Exit {end_yield:.3f} ({yield_chg * 100:+.1f}%).
    Cumulative EBITDA impact ${r.total_ebitda_impact_mm:+,.1f}M, EV impact ${r.total_ev_impact_mm:+,.1f}M.
    Medicare Advantage penetration + commercial erosion are headwinds; sponsor-led payer renegotiation is
    the most actionable offset.
  </div>

</div>"""

    return chartis_shell(body, "Payer Mix Shift", active_nav="/payer-shift")
