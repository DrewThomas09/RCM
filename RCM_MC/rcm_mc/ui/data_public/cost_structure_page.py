"""Cost Structure Analyzer page — /cost-structure.

COGS vs SG&A decomposition, labor breakdown, operating leverage sensitivity.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _cost_stack_svg(cost_lines, ebitda_margin: float) -> str:
    """Horizontal 100% stacked bar of cost categories + EBITDA."""
    w, h = 560, 100
    pad_l, pad_r, pad_t, pad_b = 20, 20, 30, 20
    inner_w = w - pad_l - pad_r
    bar_h = 30
    y = pad_t

    bg = P["panel"]
    colors_rotating = [
        P["accent"], "#8b5cf6", P["warning"], "#14b8a6",
        "#f97316", P["negative"], "#64748b",
    ]

    x = pad_l
    segs = []
    for i, cl in enumerate(cost_lines):
        w_seg = cl.pct_of_revenue * inner_w
        color = colors_rotating[i % len(colors_rotating)]
        segs.append(
            f'<rect x="{x:.1f}" y="{y}" width="{w_seg:.1f}" height="{bar_h}" fill="{color}" opacity="0.88"/>'
        )
        if w_seg > 40:
            segs.append(
                f'<text x="{x + w_seg / 2:.1f}" y="{y + bar_h / 2 + 4}" fill="{P["text"]}" font-size="10" '
                f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{cl.pct_of_revenue * 100:.1f}%</text>'
            )
        x += w_seg

    # EBITDA segment
    eb_w = ebitda_margin * inner_w
    segs.append(
        f'<rect x="{x:.1f}" y="{y}" width="{eb_w:.1f}" height="{bar_h}" fill="{P["positive"]}" opacity="0.92"/>'
    )
    segs.append(
        f'<text x="{x + eb_w / 2:.1f}" y="{y + bar_h / 2 + 4}" fill="{P["text"]}" font-size="10" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">EBITDA {ebitda_margin * 100:.1f}%</text>'
    )

    # Legend
    legend = f'<text x="{pad_l}" y="{pad_t - 10}" fill="{P["text_dim"]}" font-size="10" font-family="Inter,sans-serif">Revenue composition (% of $1 revenue)</text>'

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + legend + "".join(segs)
        + f'</svg>'
    )


def _leverage_svg(scenarios) -> str:
    """Revenue vs EBITDA sensitivity."""
    if not scenarios:
        return ""
    w, h = 540, 200
    pad_l, pad_r, pad_t, pad_b = 60, 30, 20, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_ebitda = max(s.implied_ebitda_mm for s in scenarios) * 1.10
    min_ebitda = min(min(s.implied_ebitda_mm for s in scenarios), 0)

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    n = len(scenarios)
    bar_w = (inner_w - (n - 1) * 8) / n

    zero_y = (h - pad_b) - (0 - min_ebitda) / (max_ebitda - min_ebitda) * inner_h

    bars = []
    for i, s in enumerate(scenarios):
        x = pad_l + i * (bar_w + 8)
        bh = abs(s.implied_ebitda_mm) / (max_ebitda - min_ebitda) * inner_h
        y = zero_y - (s.implied_ebitda_mm / (max_ebitda - min_ebitda) * inner_h) if s.implied_ebitda_mm >= 0 else zero_y
        color = pos if s.expected_ebitda_delta_pct >= 0 else neg
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.88"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">${s.implied_ebitda_mm:,.1f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario)}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{color}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Δ {s.expected_ebitda_delta_pct * 100:+.1f}%</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{w - pad_r}" y2="{zero_y:.1f}" stroke="{border}" stroke-width="1"/>'
        + "".join(bars)
        + f'</svg>'
    )


def _cost_table(cost_lines, revenue_mm: float) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Category","left"),("Type","left"),("Amount ($M)","right"),("% of Revenue","right"),("Benchmark","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, cl in enumerate(cost_lines):
        rb = panel_alt if i % 2 == 0 else bg
        tcolor = P["warning"] if cl.is_variable else P["text_faint"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(cl.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tcolor};border:1px solid {tcolor};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{"variable" if cl.is_variable else "fixed"}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${cl.amount_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{cl.pct_of_revenue * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{cl.benchmark_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _labor_table(labor) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Role Type","left"),("Headcount","right"),("Avg Comp ($K)","right"),("Total Cost ($M)","right"),("% of Revenue","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, l in enumerate(labor):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(l.role_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{l.headcount:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${l.avg_comp_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${l.total_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{l.pct_of_revenue * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenario_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Scenario","left"),("Revenue Δ","right"),("EBITDA Δ","right"),("Op Leverage","right"),("Implied EBITDA","right"),("Implied EV","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        ec = pos if s.expected_ebitda_delta_pct >= 0 else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.revenue_delta_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ec};font-weight:600">{s.expected_ebitda_delta_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.leverage_ratio:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.implied_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${s.implied_ev_mm:,.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_cost_structure(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.cost_structure import compute_cost_structure
    r = compute_cost_structure(sector=sector, revenue_mm=revenue, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Revenue", f"${r.revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("EBITDA", f"${r.ebitda_mm:,.2f}M", "", "") +
        ck_kpi_block("EBITDA Margin", f"{r.ebitda_margin * 100:.1f}%", "", "") +
        ck_kpi_block("COGS", f"${r.total_cogs_mm:,.1f}M", "", "") +
        ck_kpi_block("SG&A", f"${r.total_sga_mm:,.1f}M", "", "") +
        ck_kpi_block("Variable Cost %", f"{r.variable_cost_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Op Leverage", f"{r.operating_leverage:.2f}x", "", "") +
        ck_kpi_block("Labor / Rev", f"{r.labor_pct_of_revenue * 100:.1f}%", "", "")
    )

    stack_svg = _cost_stack_svg(r.cost_lines, r.ebitda_margin)
    lev_svg = _leverage_svg(r.leverage_scenarios)
    cost_tbl = _cost_table(r.cost_lines, r.revenue_mm)
    labor_tbl = _labor_table(r.labor_breakdown)
    scen_tbl = _scenario_table(r.leverage_scenarios)

    form = f"""
<form method="GET" action="/cost-structure" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Cost Structure Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      COGS vs SG&amp;A decomposition, labor breakdown, and operating leverage for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Revenue Composition ($1 Waterfall)</div>
    {stack_svg}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Cost Line Items</div>
      {cost_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Labor Breakdown ({sum(l.headcount for l in r.labor_breakdown):,} FTEs)</div>
      {labor_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Operating Leverage Sensitivity</div>
    {lev_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">Revenue → EBITDA Scenarios</div>
    {scen_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Operating Leverage Thesis:</strong>
    {r.variable_cost_pct * 100:.1f}% variable cost structure means every $1 of incremental revenue drops
    $${(1 - r.variable_cost_pct):.2f} to EBITDA. Current leverage coefficient {r.operating_leverage:.2f}x —
    a 10% top-line expansion implies {r.operating_leverage * 10:.0f}% EBITDA growth without margin compression.
  </div>

</div>"""

    return chartis_shell(body, "Cost Structure Analyzer", active_nav="/cost-structure")
