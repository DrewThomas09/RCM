"""Reinvestment page — /reinvestment."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _scenario_bars_svg(scenarios, entry_equity: float) -> str:
    if not scenarios: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 60, 40, 30, 50
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(s.equity_moic for s in scenarios) * 1.10
    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]
    n = len(scenarios)
    bar_w = (inner_w - (n - 1) * 12) / n
    bars = []
    for i, s in enumerate(scenarios):
        x = pad_l + i * (bar_w + 12)
        bh = (s.equity_moic / max_v) * inner_h
        y = (h - pad_b) - bh
        color = pos if s.equity_moic >= 2.5 else (acc if s.equity_moic >= 2.0 else P["warning"])
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="12" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{s.equity_moic:.2f}x</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario[:18])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 28}" fill="{P["positive"]}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">IRR {s.equity_irr * 100:.1f}%</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 40}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{s.boltons_acquired} bolt-on(s)</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Equity MOIC by Capital Allocation Strategy</text></svg>')


def _yearly_stack_svg(yearly) -> str:
    if not yearly: return ""
    w, h = 540, 220
    pad_l, pad_r, pad_t, pad_b = 50, 30, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(y.available_fcf_mm for y in yearly) * 1.1 or 1
    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    colors = {
        "boltons": P["positive"], "organic": P["accent"],
        "debt": P["warning"], "div": "#8b5cf6", "retained": P["text_faint"],
    }
    n = len(yearly)
    bar_w = (inner_w - (n - 1) * 12) / n
    bars = []
    for i, y_row in enumerate(yearly):
        x = pad_l + i * (bar_w + 12)
        total_h = (y_row.available_fcf_mm / max_v) * inner_h
        y0 = (h - pad_b)
        # Stack: bolt-ons, organic, debt, div, retained
        stack = [
            (y_row.boltons_mm, colors["boltons"]),
            (y_row.organic_mm, colors["organic"]),
            (y_row.debt_paydown_mm, colors["debt"]),
            (y_row.dividend_mm, colors["div"]),
            (y_row.retained_cash_mm, colors["retained"]),
        ]
        cy = y0
        for val, color in stack:
            bh = (val / max_v) * inner_h
            cy -= bh
            bars.append(f'<rect x="{x:.1f}" y="{cy:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.88"/>')

        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y0 - total_h - 4:.1f}" fill="{P["text_dim"]}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">${y_row.available_fcf_mm:,.1f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="10" text-anchor="middle" font-family="JetBrains Mono,monospace">Y{y_row.year}</text>'
        )

    # Legend
    legend_items = [
        ("Bolt-on", colors["boltons"]), ("Organic", colors["organic"]),
        ("Debt", colors["debt"]), ("Dividend", colors["div"]), ("Retained", colors["retained"]),
    ]
    leg_x = pad_l
    legend = ""
    for label, color in legend_items:
        legend += (f'<rect x="{leg_x}" y="4" width="10" height="10" fill="{color}" opacity="0.88"/>'
                   f'<text x="{leg_x + 14}" y="13" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">{label}</text>')
        leg_x += 70

    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{legend}{"".join(bars)}'
            f'</svg>')


def _flow_table(flow) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Year","left"),("EBITDA","right"),("Interest","right"),("Taxes","right"),("Capex","right"),("FCF","right"),("Cum FCF","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(flow):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">Year {f.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${f.ebitda_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.interest_paid_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.taxes_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.capex_maintenance_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">${f.free_cash_flow_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${f.cumulative_fcf_mm:,.2f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _options_table(options) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    risk_colors = {"low": pos, "medium": P["warning"], "high": P["negative"]}
    cols = [("Option","left"),("Capital ($M)","right"),("Expected IRR","right"),("MOIC","right"),("Risk","left"),("Strategic Value","left"),("Exit Impact ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(options):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(o.risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.option)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${o.capital_deployed_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{o.expected_roi_irr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{o.expected_moic:.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{o.risk}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.strategic_value)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${o.marginal_impact_on_exit_mm:,.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _scenarios_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Scenario","left"),("Bolt-ons","right"),("Organic ($M)","right"),("Debt Paydown ($M)","right"),("Dividend ($M)","right"),("Terminal EBITDA","right"),("Exit EV","right"),("MOIC","right"),("IRR","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if s.equity_moic >= 2.5 else (P["accent"] if s.equity_moic >= 2.0 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.boltons_acquired}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.organic_capex_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.debt_paydown_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.dividends_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.terminal_ebitda_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.terminal_ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:600">{s.equity_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c}">{s.equity_irr * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _yearly_table(yearly) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Year","left"),("Available FCF ($M)","right"),("Bolt-ons","right"),("Organic","right"),("Debt Paydown","right"),("Dividend","right"),("Retained","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, y in enumerate(yearly):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">Year {y.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${y.available_fcf_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${y.boltons_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">${y.organic_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${y.debt_paydown_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${y.dividend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${y.retained_cash_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_reinvestment(params: dict = None) -> str:
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

    from rcm_mc.data_public.reinvestment import compute_reinvestment
    r = compute_reinvestment(entry_ev_mm=ev, entry_ebitda_mm=ebitda, hold_years=hold, ebitda_growth_pct=growth)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Entry EV", f"${r.entry_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Entry Equity", f"${r.entry_equity_mm:,.0f}M", "", "") +
        ck_kpi_block("Hold", f"{r.hold_years} yrs", "", "") +
        ck_kpi_block("Cumulative FCF", f"${r.cumulative_fcf_mm:,.1f}M", "", "") +
        ck_kpi_block("Base Case MOIC", f"{r.base_case_moic:.2f}x", "", "") +
        ck_kpi_block("Compounded MOIC", f"{r.compounded_moic:.2f}x", "", "") +
        ck_kpi_block("MOIC Lift", f"{r.moic_lift_from_reinvestment:+.2f}x", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    scen_svg = _scenario_bars_svg(r.scenarios, r.entry_equity_mm)
    yearly_svg = _yearly_stack_svg(r.yearly_allocation)
    flow_tbl = _flow_table(r.cash_flow_years)
    opt_tbl = _options_table(r.allocation_options)
    scen_tbl = _scenarios_table(r.scenarios)
    yr_tbl = _yearly_table(r.yearly_allocation)

    form = f"""
<form method="GET" action="/reinvestment" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EV ($M)<input name="ev" value="{ev}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Entry EBITDA<input name="ebitda" value="{ebitda}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Hold Years<input name="hold_years" value="{hold}" type="number" min="3" max="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:50px"/></label>
  <label style="font-size:11px;color:{text_dim}">Growth<input name="growth" value="{growth}" type="number" step="0.01" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Reinvestment / Compounding Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Operating cash reinvestment strategy: bolt-ons, organic capex, debt paydown, dividends — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}"><div style="{h3}">Equity MOIC by Strategy</div>{scen_svg}</div>
    <div style="{cell}"><div style="{h3}">Yearly FCF Allocation Stack</div>{yearly_svg}</div>
  </div>
  <div style="{cell}"><div style="{h3}">Free Cash Flow Build</div>{flow_tbl}</div>
  <div style="{cell}"><div style="{h3}">Capital Allocation Options</div>{opt_tbl}</div>
  <div style="{cell}"><div style="{h3}">Strategy Scenarios</div>{scen_tbl}</div>
  <div style="{cell}"><div style="{h3}">Year-by-Year Allocation (Balanced)</div>{yr_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Reinvestment Thesis:</strong> ${r.cumulative_fcf_mm:,.1f}M of FCF generated over {r.hold_years} years.
    Balanced allocation (35/20/25/10/10) delivers {r.compounded_moic:.2f}x vs {r.base_case_moic:.2f}x for pure deleveraging.
    Bolt-on M&amp;A is the highest-marginal-impact use of FCF (2.4x MOIC on deployed capital).
  </div>
</div>"""

    return chartis_shell(body, "Reinvestment", active_nav="/reinvestment")
