"""Dividend Recap page — /dividend-recap.

Capital structure recap scenarios, timing analysis, carry impact, market context.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _scenarios_svg(scenarios) -> str:
    if not scenarios:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 50
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_v = max(s.net_dividend_mm for s in scenarios) * 1.1 or 1

    bg = P["panel"]; pos = P["positive"]; text_dim = P["text_dim"]
    text_faint = P["text_faint"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}

    n = len(scenarios)
    bar_w = (inner_w - (n - 1) * 12) / n

    bars = []
    for i, s in enumerate(scenarios):
        x = pad_l + i * (bar_w + 12)
        bh = (s.net_dividend_mm / max_v) * inner_h
        y = (h - pad_b) - bh
        color = risk_colors.get(s.execution_risk, pos)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.88"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="11" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${s.net_dividend_mm:,.1f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{s.target_leverage:.1f}x</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{color}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{s.execution_risk}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 38}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{s.pct_of_invested_returned * 100:.0f}% ret</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Net Dividend by Recap Scenario ($M)</text>'
        f'</svg>'
    )


def _timing_svg(timing) -> str:
    if not timing:
        return ""
    w, h = 540, 180
    pad_l, pad_r, pad_t, pad_b = 50, 30, 25, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_v = max(t.potential_dividend_mm for t in timing) * 1.10 or 1

    bg = P["panel"]; pos = P["positive"]; acc = P["accent"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    n = len(timing)
    bar_w = (inner_w - (n - 1) * 8) / n

    bars = []
    for i, t in enumerate(timing):
        x = pad_l + i * (bar_w + 8)
        bh = (t.potential_dividend_mm / max_v) * inner_h
        y = (h - pad_b) - bh
        # Color by recommendation
        if "Optimal" in t.recommendation:
            color = pos
        elif "Consider" in t.recommendation:
            color = acc
        else:
            color = P["warning"]
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 3:.1f}" fill="{P["text_dim"]}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">${t.potential_dividend_mm:,.0f}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{t.year}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">DSCR {t.dscr:.1f}x</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Potential Dividend by Year</text>'
        f'</svg>'
    )


def _scenarios_table(scenarios, recommended) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    cols = [("Scenario","left"),("Target Lev","right"),("New Debt ($M)","right"),
            ("Net Dividend ($M)","right"),("Post-Recap DSCR","right"),("Headroom","right"),
            ("MOIC on Original","right"),("% of Capital Returned","right"),("Risk","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        is_rec = s.scenario == recommended
        row_style = f"background:{rb}" + (f";outline:2px solid {P['positive']};outline-offset:-2px" if is_rec else "")
        rc = risk_colors.get(s.execution_risk, text_dim)
        dscr_c = P["positive"] if s.post_recap_dscr >= 1.5 else (P["warning"] if s.post_recap_dscr >= 1.2 else P["negative"])
        head_c = P["positive"] if s.covenant_headroom_pct >= 0.15 else (P["warning"] if s.covenant_headroom_pct >= 0.05 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"700" if is_rec else "400"}">{_html.escape(s.scenario)}{" ★" if is_rec else ""}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.target_leverage:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${s.new_debt_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">${s.net_dividend_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dscr_c}">{s.post_recap_dscr:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{head_c}">{s.covenant_headroom_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.moic_on_original_equity:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{s.pct_of_invested_returned * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{s.execution_risk}</span></td>',
        ]
        trs.append(f'<tr style="{row_style}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _timing_table(timing) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Year","left"),("EBITDA","right"),("Current Debt","right"),
            ("Available Capacity","right"),("Potential Dividend","right"),("DSCR","right"),
            ("Post-Recap Lev","right"),("Recommendation","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, t in enumerate(timing):
        rb = panel_alt if i % 2 == 0 else bg
        rec_color = P["positive"] if "Optimal" in t.recommendation else (
            P["accent"] if "Consider" in t.recommendation else P["warning"]
        )
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">Year {t.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${t.ebitda_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${t.current_debt_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${t.available_capacity_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">${t.potential_dividend_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.dscr:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.post_recap_leverage:.1f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{rec_color}">{_html.escape(t.recommendation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _carry_table(carry) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Item","left"),("Pre-Recap","right"),("Post-Recap","right"),("Δ","right"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(carry):
        rb = panel_alt if i % 2 == 0 else bg
        dc = pos if c.delta_mm > 0 else (neg if c.delta_mm < 0 else text_dim)
        is_rate = "IRR" in c.item or "MOIC" in c.item
        fmt = lambda v: f"{v * 100:.1f}%" if "IRR" in c.item else (f"{v:.2f}x" if "MOIC" in c.item else f"${v:,.1f}M")
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.item)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{fmt(c.pre_recap_mm)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{fmt(c.post_recap_mm)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dc};font-weight:600">{"+" if c.delta_mm >= 0 else ""}{fmt(c.delta_mm)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _market_table(market) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    trend_colors = {"rising": P["negative"], "improving": P["positive"],
                    "tightening": P["negative"], "stable": P["accent"],
                    "elevated": P["warning"], "active": P["accent"],
                    "selective": P["warning"]}
    cols = [("Market Metric","left"),("Value","right"),("Trend","left"),("Implication","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(market):
        rb = panel_alt if i % 2 == 0 else bg
        tc = trend_colors.get(m.trend, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.value)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{m.trend}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.implication)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_dividend_recap(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    ev = _f("ev", 300.0)
    entry_ebitda = _f("entry_ebitda", 25.0)
    entry_lev = _f("entry_lev", 5.0)
    current_yr = _i("current_year", 3)
    growth = _f("growth", 0.07)
    hold = _i("hold_years", 5)

    from rcm_mc.data_public.dividend_recap import compute_dividend_recap
    r = compute_dividend_recap(ev_mm=ev, entry_ebitda_mm=entry_ebitda, entry_leverage=entry_lev,
                                 current_year=current_yr, ebitda_growth_pct=growth, hold_years=hold)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("EV at Close", f"${r.ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Entry EBITDA", f"${r.entry_ebitda_mm:,.1f}M", "", "") +
        ck_kpi_block("Current EBITDA", f"${r.current_ebitda_mm:,.1f}M", "Y" + str(current_yr), "") +
        ck_kpi_block("Entry Leverage", f"{r.entry_leverage:.1f}x", "", "") +
        ck_kpi_block("Current Leverage", f"{r.current_leverage:.1f}x", "", "") +
        ck_kpi_block("Invested Equity", f"${r.total_invested_equity_mm:,.1f}M", "", "") +
        ck_kpi_block("Recap Dividend", f"${r.max_recap_dividend_mm:,.1f}M", "", "") +
        ck_kpi_block("Cash Return", f"{r.cash_multiple_from_recap * 100:.0f}%", "of equity", "")
    )

    scen_svg = _scenarios_svg(r.scenarios)
    time_svg = _timing_svg(r.timing_analysis)
    scen_tbl = _scenarios_table(r.scenarios, r.recommended_scenario)
    time_tbl = _timing_table(r.timing_analysis)
    carry_tbl = _carry_table(r.carry_impact)
    market_tbl = _market_table(r.market_context)

    form = f"""
<form method="GET" action="/dividend-recap" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EV ($M)
    <input name="ev" value="{ev}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Entry EBITDA
    <input name="entry_ebitda" value="{entry_ebitda}" type="number" step="1"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Entry Lev
    <input name="entry_lev" value="{entry_lev}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Year in Hold
    <input name="current_year" value="{current_yr}" type="number" min="1" max="8"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Dividend Recap Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Interim capital distribution via refinancing — scenarios, timing, carry impact — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Recap Scenarios by Target Leverage</div>
      {scen_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Dividend Capacity by Hold Year</div>
      {time_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Recap Scenario Detail (Recommended: {_html.escape(r.recommended_scenario)})</div>
    {scen_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Timing Analysis — When to Recap</div>
    {time_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Carry / Waterfall Impact</div>
    {carry_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Market Context — Financing Conditions</div>
    {market_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Recap Thesis:</strong>
    At year {current_yr} with EBITDA up to ${r.current_ebitda_mm:,.1f}M (from ${r.entry_ebitda_mm:,.1f}M) and
    leverage down to {r.current_leverage:.1f}x (from {r.entry_leverage:.1f}x), recommended structure is
    <strong style="color:{text}">{_html.escape(r.recommended_scenario)}</strong>.
    Potential net dividend: ${r.max_recap_dividend_mm:,.1f}M ({r.cash_multiple_from_recap * 100:.0f}% of invested equity).
    Action lifts LP IRR ~400 bps without materially impacting total MOIC.
  </div>

</div>"""

    return chartis_shell(body, "Dividend Recap", active_nav="/dividend-recap")
