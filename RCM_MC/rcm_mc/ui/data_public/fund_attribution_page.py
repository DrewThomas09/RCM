"""Fund Performance Attribution page — /fund-attribution.

Decomposes fund IRR into operational, multiple expansion, leverage,
market timing, and bolt-on components. Deal-level attribution table.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _waterfall_svg(components, fund_moic: float) -> str:
    if not components:
        return ""
    w, h = 620, 220
    pad_l, pad_r, pad_t, pad_b = 50, 30, 30, 60
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    # Waterfall: start at 1.0x (invested capital), add each contribution, end at fund_moic
    bg = P["panel"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    max_v = max(fund_moic, 1.0) * 1.15
    min_v = 0

    n_bars = len(components) + 2    # Start + components + End
    bar_w = (inner_w - (n_bars - 1) * 8) / n_bars

    colors = [P["accent"], "#14b8a6", "#a78bfa", "#b8732a", "#f97316"]

    # Build running values
    running = 1.0
    bars = []

    # Start bar (1.0x invested)
    def _y(v):
        return (h - pad_b) - (v / max_v) * inner_h

    x = pad_l
    h_start = (1.0 / max_v) * inner_h
    y_start = (h - pad_b) - h_start
    bars.append(
        f'<rect x="{x:.1f}" y="{y_start:.1f}" width="{bar_w:.1f}" height="{h_start:.1f}" fill="{P["text_faint"]}" opacity="0.7"/>'
        f'<text x="{x + bar_w / 2:.1f}" y="{y_start - 4:.1f}" fill="{P["text_dim"]}" font-size="10" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace">1.00x</text>'
        f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace">Invested</text>'
    )

    # Contribution bars (floating)
    for i, c in enumerate(components):
        x += bar_w + 8
        contrib = c.contribution_moic_x
        color = colors[i % len(colors)]
        if contrib >= 0:
            # Floating up
            y_top = _y(running + contrib)
            y_bot = _y(running)
            height = y_bot - y_top
            bars.append(
                f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{height:.1f}" fill="{color}" opacity="0.88"/>'
            )
        else:
            y_top = _y(running)
            y_bot = _y(running + contrib)
            height = y_bot - y_top
            bars.append(
                f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{height:.1f}" fill="{P["negative"]}" opacity="0.88"/>'
            )

        # Value label above bar
        center_y = _y(running + contrib / 2)
        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{_y(running + contrib) - 4:.1f}" fill="{P["text_dim"]}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">+{contrib:.2f}x</text>'
        )
        # Short label
        short = c.component[:12]
        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(short)}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{color}" font-size="8" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{c.pct_of_total_return * 100:.0f}%</text>'
        )
        running += contrib

    # End bar (fund_moic)
    x += bar_w + 8
    h_end = (running / max_v) * inner_h
    y_end = (h - pad_b) - h_end
    bars.append(
        f'<rect x="{x:.1f}" y="{y_end:.1f}" width="{bar_w:.1f}" height="{h_end:.1f}" fill="{P["positive"]}" opacity="0.88"/>'
        f'<text x="{x + bar_w / 2:.1f}" y="{y_end - 4:.1f}" fill="{P["text"]}" font-size="11" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{running:.2f}x</text>'
        f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace">Realized</text>'
    )

    # Y ticks
    ticks = []
    for v in [0, 1.0, 2.0, max_v * 0.75]:
        if v <= max_v:
            yp = _y(v)
            ticks.append(
                f'<line x1="{pad_l - 4}" y1="{yp}" x2="{w - pad_r}" y2="{yp}" stroke="{border}" stroke-width="0.5" stroke-dasharray="2,3"/>'
                f'<text x="{pad_l - 6}" y="{yp + 3}" fill="{text_faint}" font-size="9" '
                f'text-anchor="end" font-family="JetBrains Mono,monospace">{v:.1f}x</text>'
            )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">MOIC Attribution Waterfall</text>'
        + "".join(ticks) + "".join(bars)
        + f'</svg>'
    )


def _vintage_table(vintages) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    env_colors = {
        "expansion": P["positive"], "peak": P["warning"],
        "recession": P["negative"], "recovery": P["accent"],
    }
    cols = [("Vintage","left"),("Deals","right"),("Median MOIC","right"),
            ("Median IRR","right"),("Market Env","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, v in enumerate(vintages):
        rb = panel_alt if i % 2 == 0 else bg
        ec = env_colors.get(v.market_env, text_dim)
        moic_color = P["positive"] if v.median_moic >= 2.0 else (P["warning"] if v.median_moic >= 1.0 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.vintage_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.deal_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_color};font-weight:600">{v.median_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.median_irr * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ec};border:1px solid {ec};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{v.market_env}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _component_table(components) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Attribution Component","left"),("MOIC Contribution","right"),
            ("IRR Contribution","right"),("% of Return","right"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(components):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.component)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{c.contribution_moic_x:+.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.contribution_irr_pct:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.pct_of_total_return * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(c.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _deal_attr_table(attrs) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Company","left"),("Sector","left"),("Vintage","right"),("Hold","right"),
            ("Entry EV","right"),("Exit EV","right"),("EBITDA Gr.","right"),
            ("Mult. Exp.","right"),("Leverage","right"),("MOIC","right"),("IRR","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, a in enumerate(attrs[:30]):   # top 30 deals
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if a.total_moic >= 2.0 else (P["warning"] if a.total_moic >= 1.0 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(a.company)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(a.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.vintage}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.hold_years:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${a.entry_ev_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${a.exit_ev_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos if a.ebitda_growth_pct > 0 else neg}">{a.ebitda_growth_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.multiple_expansion_x:+.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.leverage_contribution_x:+.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:600">{a.total_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.total_irr * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_fund_attribution(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "")
    vintage_from = int(params["vintage_from"]) if params.get("vintage_from", "").isdigit() else 0
    vintage_to = int(params["vintage_to"]) if params.get("vintage_to", "").isdigit() else 9999

    from rcm_mc.data_public.fund_attribution import compute_fund_attribution
    r = compute_fund_attribution(sector_filter=sector, vintage_from=vintage_from, vintage_to=vintage_to)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    best = r.best_performer or {}
    worst = r.worst_performer or {}

    kpi_strip = (
        ck_kpi_block("Fund MOIC", f"{r.fund_moic:.2f}x", "", "") +
        ck_kpi_block("Fund IRR", f"{r.fund_irr * 100:.1f}%", "", "") +
        ck_kpi_block("Avg EBITDA Growth", f"{r.avg_ebitda_growth_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Mult. Expansion", f"{r.avg_multiple_expansion_x:+.2f}x", "", "") +
        ck_kpi_block("Best Performer", str(best.get("company", "—"))[:18], f"{best.get('moic', 0):.2f}x", "") +
        ck_kpi_block("Worst Performer", str(worst.get("company", "—"))[:18], f"{worst.get('moic', 0):.2f}x", "") +
        ck_kpi_block("Vintages", str(len(r.vintage_effects)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    water_svg = _waterfall_svg(r.components, r.fund_moic)
    comp_tbl = _component_table(r.components)
    vintage_tbl = _vintage_table(r.vintage_effects)
    deal_tbl = _deal_attr_table(r.deal_attributions)

    form = f"""
<form method="GET" action="/fund-attribution" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}" placeholder="All"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:140px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Vintage From
    <input name="vintage_from" value="{vintage_from if vintage_from else ''}" placeholder="2015" type="number"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Vintage To
    <input name="vintage_to" value="{vintage_to if vintage_to < 9999 else ''}" placeholder="2024" type="number"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Filter</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Fund Performance Attribution</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      IRR decomposition — operational, multiple expansion, leverage, bolt-on, vintage — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">MOIC Attribution Waterfall</div>
    {water_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">Component Contribution Detail</div>
    {comp_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 2fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Vintage Year Environments</div>
      {vintage_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Deal-Level Attribution (Top 30)</div>
      {deal_tbl}
    </div>
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Attribution Thesis:</strong>
    Fund realized {r.fund_moic:.2f}x MOIC / {r.fund_irr * 100:.1f}% IRR. Operational improvements contributed
    {r.components[0].pct_of_total_return * 100:.0f}% of return, leverage {r.components[3].pct_of_total_return * 100:.0f}%,
    multiple expansion {r.components[2].pct_of_total_return * 100:.0f}%. A healthy attribution mix — returns come
    from operational execution, not just entry/exit multiple arbitrage.
  </div>

</div>"""

    return chartis_shell(body, "Fund Attribution", active_nav="/fund-attribution")
