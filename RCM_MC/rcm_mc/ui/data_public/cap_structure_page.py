"""Capital Structure Optimizer page — /cap-structure.

Leverage sensitivity analysis, WACC curve, MOIC by leverage, breach probabilities.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _moic_curve_svg(ret_scenarios, lev_scenarios, optimal_lev: float) -> str:
    if not ret_scenarios:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 30, 25, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_moic = max(r.moic for r in ret_scenarios) * 1.10 or 3
    min_lev = min(r.leverage for r in ret_scenarios)
    max_lev = max(r.leverage for r in ret_scenarios)
    lev_range = max_lev - min_lev or 1

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    def _x(lev):
        return pad_l + (lev - min_lev) / lev_range * inner_w

    def _y(moic):
        return (h - pad_b) - (moic / max_moic) * inner_h

    # MOIC line
    pts = [f"{_x(r.leverage):.1f},{_y(r.moic):.1f}" for r in ret_scenarios]
    line = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'

    # Dots
    dots = []
    for r in ret_scenarios:
        x = _x(r.leverage)
        y = _y(r.moic)
        color = pos if r.leverage == optimal_lev else acc
        r_size = 6 if r.leverage == optimal_lev else 3
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_size}" fill="{color}" stroke="{P["text"]}" stroke-width="0.5"/>')

    # Breach zones (DSCR < 1.3, headroom < 12%)
    breach_rects = []
    for ls in lev_scenarios:
        if ls.dscr < 1.3 or ls.covenant_headroom_pct < 0.12:
            x = _x(ls.total_leverage)
            breach_rects.append(
                f'<rect x="{x - 10}" y="{pad_t}" width="20" height="{inner_h}" fill="{neg}" opacity="0.08"/>'
            )

    # Optimal marker
    opt_x = _x(optimal_lev)
    opt_marker = (
        f'<line x1="{opt_x:.1f}" y1="{pad_t}" x2="{opt_x:.1f}" y2="{h - pad_b}" stroke="{pos}" stroke-width="1" stroke-dasharray="3,3"/>'
        f'<text x="{opt_x:.1f}" y="{pad_t - 5}" fill="{pos}" font-size="10" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">OPTIMAL</text>'
    )

    # Axes
    axes = []
    for lev in [3.0, 4.0, 5.0, 6.0, 7.0]:
        if min_lev <= lev <= max_lev:
            x = _x(lev)
            axes.append(
                f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="10" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace">{lev:.1f}x</text>'
            )
    for m in [1.0, 2.0, 3.0, 4.0]:
        if m <= max_moic:
            y = _y(m)
            axes.append(
                f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w - pad_r}" y2="{y:.1f}" stroke="{border}" stroke-width="0.5" opacity="0.4"/>'
                f'<text x="{pad_l - 4}" y="{y + 3:.1f}" fill="{text_faint}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace">{m:.1f}x</text>'
            )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(breach_rects) + "".join(axes) + opt_marker + line + "".join(dots) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">MOIC by Total Leverage</text>'
        f'</svg>'
    )


def _wacc_curve_svg(scenarios) -> str:
    if not scenarios:
        return ""
    w, h = 500, 180
    pad_l, pad_r, pad_t, pad_b = 50, 30, 25, 35
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_wacc = max(s.wacc for s in scenarios) * 1.1
    min_wacc = min(s.wacc for s in scenarios) * 0.9
    range_wacc = max_wacc - min_wacc or 0.01

    min_lev = min(s.total_leverage for s in scenarios)
    max_lev = max(s.total_leverage for s in scenarios)
    lev_range = max_lev - min_lev or 1

    bg = P["panel"]; acc = P["accent"]; text_dim = P["text_dim"]
    text_faint = P["text_faint"]; border = P["border"]

    pts = []
    for s in scenarios:
        x = pad_l + (s.total_leverage - min_lev) / lev_range * inner_w
        y = (h - pad_b) - (s.wacc - min_wacc) / range_wacc * inner_h
        pts.append(f"{x:.1f},{y:.1f}")

    line = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'

    dots = []
    for s in scenarios:
        x = pad_l + (s.total_leverage - min_lev) / lev_range * inner_w
        y = (h - pad_b) - (s.wacc - min_wacc) / range_wacc * inner_h
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{acc}"/>')
        dots.append(
            f'<text x="{x:.1f}" y="{y - 7:.1f}" fill="{P["text_dim"]}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{s.wacc * 100:.2f}%</text>'
        )

    # x-axis labels
    axes = []
    for lev in [3.0, 4.0, 5.0, 6.0, 7.0]:
        if min_lev <= lev <= max_lev:
            x = pad_l + (lev - min_lev) / lev_range * inner_w
            axes.append(
                f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="10" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace">{lev:.1f}x</text>'
            )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(axes) + line + "".join(dots) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">WACC by Total Leverage</text>'
        f'</svg>'
    )


def _leverage_table(scenarios, optimal_lev) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Total Leverage","right"),("Senior","right"),("Sub/Mezz","right"),
            ("Debt ($M)","right"),("Equity ($M)","right"),("Eq %","right"),
            ("Cost of Debt","right"),("WACC","right"),("Interest ($M)","right"),
            ("DSCR","right"),("Cov Headroom","right"),("Availability","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        is_opt = abs(s.total_leverage - optimal_lev) < 0.01
        row_style = f"background:{rb}" + (f";outline:2px solid {P['positive']};outline-offset:-2px" if is_opt else "")
        dscr_c = P["positive"] if s.dscr >= 1.5 else (P["warning"] if s.dscr >= 1.2 else P["negative"])
        head_c = P["positive"] if s.covenant_headroom_pct >= 0.20 else (P["warning"] if s.covenant_headroom_pct >= 0.10 else P["negative"])
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"700" if is_opt else "400"}">{s.total_leverage:.1f}x{" ★" if is_opt else ""}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.senior_leverage:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.sub_leverage:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.debt_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.equity_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.equity_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{s.blended_cost_of_debt * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{s.wacc * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.year1_interest_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dscr_c};font-weight:600">{s.dscr:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{head_c}">{s.covenant_headroom_pct * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.market_availability)}</td>',
        ]
        trs.append(f'<tr style="{row_style}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _return_table(returns, optimal_lev) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Leverage","right"),("Exit EBITDA","right"),("Exit EV","right"),
            ("Remaining Debt","right"),("Exit Equity","right"),("MOIC","right"),("IRR","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, r in enumerate(returns):
        rb = panel_alt if i % 2 == 0 else bg
        is_opt = abs(r.leverage - optimal_lev) < 0.01
        row_style = f"background:{rb}" + (f";outline:2px solid {pos};outline-offset:-2px" if is_opt else "")
        moic_c = pos if r.moic >= 2.5 else (P["warning"] if r.moic >= 1.5 else P["negative"])
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"700" if is_opt else "400"}">{r.leverage:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.exit_ebitda_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.exit_ev_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${r.remaining_debt_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${r.exit_equity_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:600">{r.moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c}">{r.irr * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="{row_style}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _breach_table(probs) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Leverage","right"),("EBITDA -5%","right"),("EBITDA -10%","right"),
            ("EBITDA -15%","right"),("EBITDA -20%","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, b in enumerate(probs):
        rb = panel_alt if i % 2 == 0 else bg
        def _pc(v):
            if v < 0.20: return P["positive"]
            if v < 0.50: return P["warning"]
            return P["negative"]
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{b.leverage:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{_pc(b.ebitda_drop_5pct)}">{b.ebitda_drop_5pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{_pc(b.ebitda_drop_10pct)}">{b.ebitda_drop_10pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{_pc(b.ebitda_drop_15pct)}">{b.ebitda_drop_15pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{_pc(b.ebitda_drop_20pct)}">{b.ebitda_drop_20pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_cap_structure(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    ev = _f("ev", 300.0)
    ebitda = _f("ebitda", 25.0)
    hold = _i("hold_years", 5)
    growth = _f("growth", 0.06)
    exit_mult = _f("exit_mult", 12.0)

    from rcm_mc.data_public.cap_structure import compute_cap_structure
    r = compute_cap_structure(ev_mm=ev, ebitda_mm=ebitda, hold_years=hold,
                               ebitda_growth_pct=growth, exit_multiple=exit_mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("EV", f"${r.ev_mm:,.0f}M", "", "") +
        ck_kpi_block("EBITDA", f"${r.ebitda_mm:,.2f}M", "", "") +
        ck_kpi_block("Current Entry Mult", f"{r.ev_mm / r.ebitda_mm:.2f}x", "", "") +
        ck_kpi_block("Optimal Leverage", f"{r.optimal_leverage:.1f}x", "", "") +
        ck_kpi_block("Optimal MOIC", f"{r.optimal_moic:.2f}x", "", "") +
        ck_kpi_block("Hold Years", f"{hold}", "", "") +
        ck_kpi_block("Exit Multiple", f"{exit_mult:.1f}x", "", "") +
        ck_kpi_block("Scenarios", str(len(r.leverage_scenarios)), "", "")
    )

    moic_svg = _moic_curve_svg(r.return_scenarios, r.leverage_scenarios, r.optimal_leverage)
    wacc_svg = _wacc_curve_svg(r.leverage_scenarios)
    lev_tbl = _leverage_table(r.leverage_scenarios, r.optimal_leverage)
    ret_tbl = _return_table(r.return_scenarios, r.optimal_leverage)
    breach_tbl = _breach_table(r.breach_probabilities)

    form = f"""
<form method="GET" action="/cap-structure" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EV ($M)
    <input name="ev" value="{ev}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA ($M)
    <input name="ebitda" value="{ebitda}" type="number" step="1"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Hold Years
    <input name="hold_years" value="{hold}" type="number" min="3" max="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:50px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Growth
    <input name="growth" value="{growth}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
    <input name="exit_mult" value="{exit_mult}" type="number" step="0.5"
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Capital Structure Optimizer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Leverage sensitivity analysis — MOIC / WACC / DSCR / covenant headroom / breach probabilities — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">MOIC by Leverage</div>
      {moic_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">WACC Curve</div>
      {wacc_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Leverage Scenario Matrix</div>
    {lev_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Exit Returns by Leverage</div>
    {ret_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Covenant Breach Probability — EBITDA Stress Test</div>
    {breach_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {pos};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Recommendation:</strong>
    {_html.escape(r.recommendation)}.
    Increasing leverage from {r.optimal_leverage - 0.5:.1f}x to {r.optimal_leverage:.1f}x lifts expected MOIC
    meaningfully while maintaining DSCR ≥ 1.3x and covenant headroom &gt; 12%. Beyond {r.optimal_leverage + 0.5:.1f}x,
    cost-of-debt step-ups and breach probabilities materially reduce risk-adjusted returns.
  </div>

</div>"""

    return chartis_shell(body, "Capital Structure", active_nav="/cap-structure")
