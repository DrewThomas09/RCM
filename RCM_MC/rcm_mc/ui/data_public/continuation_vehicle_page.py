"""Continuation Vehicle page — /continuation-vehicle.

GP-led secondary economics: structures, pricing, LP elections, GP carry.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _pricing_svg(pricing, current_nav: float) -> str:
    if not pricing:
        return ""
    w = 540
    row_h = 34
    h = len(pricing) * row_h + 40
    pad_l = 190
    pad_r = 40
    inner_w = w - pad_l - pad_r

    max_price = current_nav * 1.10
    min_price = current_nav * 0.85

    bg = P["panel"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    border = P["border"]

    def _x(v):
        return pad_l + (v - min_price) / (max_price - min_price) * inner_w

    # NAV reference line
    nav_x = _x(current_nav)
    nav_line = (
        f'<line x1="{nav_x:.1f}" y1="25" x2="{nav_x:.1f}" y2="{h - 15}" '
        f'stroke="{P["text"]}" stroke-width="1.5" stroke-dasharray="3,3"/>'
        f'<text x="{nav_x:.1f}" y="20" fill="{P["text"]}" font-size="10" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">NAV ${current_nav:,.0f}M</text>'
    )

    markers = []
    for i, p in enumerate(pricing):
        y = 35 + i * row_h
        x = _x(p.implied_price_mm)
        color = pos if p.implied_price_mm >= current_nav else (neg if p.implied_price_mm < current_nav * 0.95 else acc)
        markers.append(
            f'<text x="{pad_l - 6}" y="{y + 8}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(p.methodology[:24])}</text>'
            f'<circle cx="{x:.1f}" cy="{y + 4}" r="6" fill="{color}" opacity="0.85"/>'
            f'<text x="{x:.1f}" y="{y - 2}" fill="{P["text_dim"]}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">${p.implied_price_mm:,.0f}M</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + nav_line + "".join(markers) +
        f'</svg>'
    )


def _gp_waterfall_svg(gp_econ) -> str:
    if not gp_econ:
        return ""
    w, h = 540, 200
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_abs = max(abs(g.delta_mm) for g in gp_econ) or 1

    bg = P["panel"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    n = len(gp_econ)
    bar_w = (inner_w - (n - 1) * 10) / n

    zero_y = (h - pad_b) - ((0 + max_abs) / (2 * max_abs)) * inner_h

    bars = []
    for i, g in enumerate(gp_econ):
        x = pad_l + i * (bar_w + 10)
        color = pos if g.delta_mm >= 0 else neg
        bh = abs(g.delta_mm) / (2 * max_abs) * inner_h
        y = zero_y - bh if g.delta_mm >= 0 else zero_y
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4 if g.delta_mm >= 0 else y + bh + 12:.1f}" fill="{color}" '
            f'font-size="10" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">'
            f'{"+" if g.delta_mm >= 0 else ""}${g.delta_mm:,.1f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(g.item[:22])}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{w - pad_r}" y2="{zero_y:.1f}" stroke="{border}" stroke-width="1"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">GP Economic Impact from CV ($M)</text>'
        f'</svg>'
    )


def _structures_table(structures, recommended) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Structure","left"),("CV Size ($M)","right"),("LP Rollover","right"),
            ("New Investor ($M)","right"),("GP Commit","right"),("Hurdle","right"),
            ("Carry","right"),("Mgmt Fee","right"),("Close (mo)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(structures):
        rb = panel_alt if i % 2 == 0 else bg
        is_rec = s.structure_type == recommended
        row_style = f"background:{rb}" + (f";outline:2px solid {P['positive']};outline-offset:-2px" if is_rec else "")
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"700" if is_rec else "400"}">{_html.escape(s.structure_type)}{" ★" if is_rec else ""}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.cv_size_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.existing_lp_rollover_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">${s.new_investor_commitment_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.gp_commitment_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.new_hurdle * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.new_carry_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.management_fee * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.time_to_close_mo}</td>',
        ]
        trs.append(f'<tr style="{row_style}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _pricing_table(pricing, current_nav: float) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Methodology","left"),("Implied Price ($M)","right"),("Discount to NAV","right"),
            ("Premium to NAV","right"),("Rationale","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(pricing):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.methodology)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.implied_price_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"] if p.discount_to_nav else text_dim}">{p.discount_to_nav * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"] if p.premium_to_nav else text_dim}">{p.premium_to_nav * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.rationale)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _lp_table(lp) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("LP Class","left"),("Commitment ($M)","right"),("Status Quo","left"),
            ("Rollover Option","left"),("Sell Option","left"),("Typical Election","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, l in enumerate(lp):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(l.lp_class)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${l.commitment_mm:,.1f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.option_status_quo)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.option_rollover)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.option_sell)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["accent"]}">{_html.escape(l.typical_election)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _gp_table(gp) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Item","left"),("Existing Fund ($M)","right"),("CV New ($M)","right"),("Δ ($M)","right"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, g in enumerate(gp):
        rb = panel_alt if i % 2 == 0 else bg
        dc = pos if g.delta_mm > 0 else (neg if g.delta_mm < 0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(g.item)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${g.existing_fund_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${g.cv_new_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dc};font-weight:600">{"+" if g.delta_mm >= 0 else ""}${g.delta_mm:,.1f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(g.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _exits_table(exits) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Exit Year","left"),("EBITDA ($M)","right"),("Exit Mult","right"),
            ("Exit EV ($M)","right"),("CV Equity ($M)","right"),("MOIC","right"),
            ("IRR","right"),("LP Rollover Return","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, e in enumerate(exits):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if e.cv_moic >= 2.0 else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">Year {e.exit_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${e.ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.exit_multiple:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${e.exit_ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">${e.cv_net_equity_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:600">{e.cv_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c}">{e.cv_irr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${e.lp_rollover_return_mm:,.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_continuation_vehicle(params: dict = None) -> str:
    params = params or {}
    asset = params.get("asset", "Sample Healthcare Platform")

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    nav = _f("nav", 450.0)
    hold = _i("hold_years", 5)

    from rcm_mc.data_public.continuation_vehicle import compute_continuation_vehicle
    r = compute_continuation_vehicle(asset_name=asset, current_nav_mm=nav, hold_years_elapsed=hold)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Asset", r.asset_name[:18], "", "") +
        ck_kpi_block("Current NAV", f"${r.current_nav_mm:,.0f}M", "", "") +
        ck_kpi_block("Hold Elapsed", f"{r.hold_years_elapsed} yrs", "", "") +
        ck_kpi_block("Remaining Potential", f"{r.remaining_hold_potential} yrs", "", "") +
        ck_kpi_block("Structures", str(len(r.structures)), "", "") +
        ck_kpi_block("Tx Cost", f"{r.total_transaction_cost_pct * 100:.1f}%", "", "") +
        ck_kpi_block("ILPA Alignment", f"{r.ilpa_alignment_score}/100", "", "") +
        ck_kpi_block("Recommended", r.recommended_structure.split(" ")[0], "", "")
    )

    pricing_svg = _pricing_svg(r.pricing, r.current_nav_mm)
    gp_svg = _gp_waterfall_svg(r.gp_economics)
    struct_tbl = _structures_table(r.structures, r.recommended_structure)
    pricing_tbl = _pricing_table(r.pricing, r.current_nav_mm)
    lp_tbl = _lp_table(r.lp_elections)
    gp_tbl = _gp_table(r.gp_economics)
    exit_tbl = _exits_table(r.exit_scenarios)

    form = f"""
<form method="GET" action="/continuation-vehicle" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Asset Name
    <input name="asset" value="{_html.escape(asset)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:220px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">NAV ($M)
    <input name="nav" value="{nav}" type="number" step="25"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Hold Elapsed (yrs)
    <input name="hold_years" value="{hold}" type="number" min="3" max="10"
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Continuation Vehicle Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      GP-led secondary economics — structures, pricing, LP elections, carry reset — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Pricing Methodologies (vs NAV)</div>
      {pricing_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">GP Economic Impact</div>
      {gp_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">CV Structure Options (Recommended: {_html.escape(r.recommended_structure)})</div>
    {struct_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Pricing Detail</div>
    {pricing_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">LP Election Framework</div>
    {lp_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">GP Economics Detail</div>
    {gp_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">CV Exit Scenarios</div>
    {exit_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">CV Thesis:</strong>
    ${r.current_nav_mm:,.0f}M NAV asset at year {r.hold_years_elapsed} of hold. Single-asset CV structure
    offers cleanest LP optionality, fresh carry reset for GP, and ~{r.remaining_hold_potential}-year extended runway for upside.
    Total transaction cost ~{r.total_transaction_cost_pct * 100:.1f}% of NAV. ILPA alignment score
    {r.ilpa_alignment_score}/100 — conflicts managed with fairness opinion + independent LP advisory process.
  </div>

</div>"""

    return chartis_shell(body, "Continuation Vehicle", active_nav="/continuation-vehicle")
