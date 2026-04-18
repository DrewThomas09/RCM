"""Bolt-on M&A Analyzer page — /bolton-analyzer.

Platform + N bolt-ons roll-up model. Multiple arbitrage, synergy phasing,
MOIC/IRR with vs. without bolt-ons. SVG EBITDA bridge and projection chart.
"""
from __future__ import annotations

import html as _html
from typing import List

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _ebitda_bridge_svg(projections) -> str:
    if not projections:
        return ""
    final = projections[-1]
    components = [
        ("Platform", final.platform_ebitda_mm, P["accent"]),
        ("Bolt-ons", final.bolton_ebitda_mm, P["positive"]),
        ("Synergies", final.synergy_mm, P["warning"]),
        ("Total", final.total_ebitda_mm, P["text"]),
    ]
    w, h = 540, 220
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 50
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    bar_w = 80
    gap = (inner_w - bar_w * len(components)) / max(1, len(components) - 1)

    total = final.total_ebitda_mm
    max_v = max(total, 0.1) * 1.10

    bg = P["panel"]
    text_dim = P["text_dim"]
    text_faint = P["text_faint"]
    border = P["border"]

    bars = []
    for i, (label, val, color) in enumerate(components):
        x = int(pad_l + i * (bar_w + gap))
        bh = int(val / max_v * inner_h)
        y = (h - pad_b) - bh
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" fill="{color}" opacity="0.8"/>'
            f'<text x="{x + bar_w // 2}" y="{y - 6}" fill="{text_dim}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">${val:,.1f}M</text>'
            f'<text x="{x + bar_w // 2}" y="{h - pad_b + 16}" fill="{text_faint}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{label}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars)
        + f'<text x="{pad_l}" y="18" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">'
        f'Exit Year {final.year} EBITDA Composition</text>'
        f'</svg>'
    )


def _projection_svg(projections) -> str:
    if not projections:
        return ""
    w, h = 540, 220
    pad_l, pad_r, pad_t, pad_b = 50, 30, 20, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_v = max((p.total_ebitda_mm for p in projections), default=1.0) * 1.10
    n = len(projections)
    bw = (inner_w - (n - 1) * 6) / n

    bg = P["panel"]
    acc = P["accent"]
    pos = P["positive"]
    warn = P["warning"]
    text_faint = P["text_faint"]
    border = P["border"]

    bars = []
    for i, p in enumerate(projections):
        x = pad_l + i * (bw + 6)
        plat_h = p.platform_ebitda_mm / max_v * inner_h
        bolt_h = p.bolton_ebitda_mm / max_v * inner_h
        syn_h = p.synergy_mm / max_v * inner_h
        y_plat = (h - pad_b) - plat_h
        y_bolt = y_plat - bolt_h
        y_syn = y_bolt - syn_h
        bars.append(
            f'<rect x="{x}" y="{y_plat}" width="{bw}" height="{plat_h}" fill="{acc}" opacity="0.8"/>'
            f'<rect x="{x}" y="{y_bolt}" width="{bw}" height="{bolt_h}" fill="{pos}" opacity="0.8"/>'
            f'<rect x="{x}" y="{y_syn}" width="{bw}" height="{syn_h}" fill="{warn}" opacity="0.8"/>'
            f'<text x="{x + bw / 2}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{p.year}</text>'
            f'<text x="{x + bw / 2}" y="{y_syn - 3}" fill="{P["text_dim"]}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{p.total_ebitda_mm:.0f}</text>'
        )

    # Y-axis ticks
    ticks = []
    for frac in [0, 0.5, 1.0]:
        v = max_v * frac
        yp = (h - pad_b) - frac * inner_h
        ticks.append(
            f'<line x1="{pad_l - 4}" y1="{yp}" x2="{w - pad_r}" y2="{yp}" stroke="{border}" stroke-width="0.5"/>'
            f'<text x="{pad_l - 6}" y="{yp + 3}" fill="{text_faint}" font-size="9" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{v:.0f}</text>'
        )

    legend = (
        f'<rect x="{pad_l}" y="2" width="10" height="10" fill="{acc}" opacity="0.8"/>'
        f'<text x="{pad_l + 14}" y="11" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">Platform</text>'
        f'<rect x="{pad_l + 80}" y="2" width="10" height="10" fill="{pos}" opacity="0.8"/>'
        f'<text x="{pad_l + 94}" y="11" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">Bolt-ons</text>'
        f'<rect x="{pad_l + 160}" y="2" width="10" height="10" fill="{warn}" opacity="0.8"/>'
        f'<text x="{pad_l + 174}" y="11" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">Synergies</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(ticks) + legend + "".join(bars)
        + f'</svg>'
    )


def _bolton_table(boltons) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]

    header_cols = [
        ("Acquisition", "left"), ("Year", "right"), ("EBITDA ($M)", "right"),
        ("Mult.", "right"), ("Price ($M)", "right"), ("Rev Syn", "right"),
        ("Cost Syn", "right"), ("Synergy Run-rate", "right"), ("Integr. ($M)", "right"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em;white-space:nowrap">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
    trs = []
    for i, b in enumerate(boltons):
        row_bg = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(b.label)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">Y{b.acquire_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{b.ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.purchase_mult:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{b.purchase_price_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.revenue_synergy_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.cost_synergy_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{b.run_rate_synergy_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.integration_cost_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}<tbody>{"".join(trs)}</tbody></table></div>'
    )


def _projection_table(projections) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]

    header_cols = [
        ("Year", "left"), ("Platform", "right"), ("Bolt-ons", "right"),
        ("Synergy", "right"), ("Total EBITDA", "right"), ("# Bolt-ons", "right"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
    trs = []
    for i, p in enumerate(projections):
        row_bg = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">Year {p.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.platform_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${p.bolton_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${p.synergy_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${p.total_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.cumulative_boltons}</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}<tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenario_table(scenarios) -> str:
    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    pos = P["positive"]

    header_cols = [
        ("Scenario", "left"), ("Exit Yr", "right"), ("Exit EBITDA", "right"),
        ("Exit Mult.", "right"), ("Exit EV", "right"), ("Invested Eq.", "right"),
        ("Exit Eq.", "right"), ("MOIC", "right"), ("IRR", "right"),
    ]
    ths = "".join(
        f'<th style="text-align:{align};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{col}</th>'
        for col, align in header_cols
    )
    header = f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
    trs = []
    for i, s in enumerate(scenarios):
        row_bg = panel_alt if i % 2 == 0 else bg
        moic_color = pos if s.moic >= 2.5 else (P["warning"] if s.moic >= 1.5 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"600" if "With" in s.label else "400"}">{_html.escape(s.label)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">Y{s.exit_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.exit_ebitda_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.exit_multiple:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.exit_ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.invested_equity_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.exit_equity_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_color};font-weight:600">{s.moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_color};font-weight:600">{s.irr * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{row_bg}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'{header}<tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_bolton_analyzer(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Dermatology") or "Dermatology"

    def _f(name, default):
        try:
            return float(params.get(name, default))
        except (ValueError, TypeError):
            return default

    def _i(name, default):
        try:
            return int(params.get(name, default))
        except (ValueError, TypeError):
            return default

    platform_ebitda = _f("platform_ebitda", 25.0)
    n_boltons = _i("n_boltons", 6)
    organic = _f("organic", 0.06)
    rev_syn = _f("rev_syn", 0.03)
    cost_syn = _f("cost_syn", 0.08)
    hold_years = _i("hold_years", 5)

    from rcm_mc.data_public.bolton_analyzer import compute_bolton_analyzer
    r = compute_bolton_analyzer(
        sector=sector,
        platform_ebitda_mm=platform_ebitda,
        n_boltons=n_boltons,
        organic_growth_pct=organic,
        revenue_synergy_pct=rev_syn,
        cost_synergy_pct=cost_syn,
        hold_years=hold_years,
    )

    bg = P["bg"]
    panel = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    pos = P["positive"]
    neg = P["negative"]
    warn = P["warning"]
    acc = P["accent"]

    arb = r.multiple_arbitrage
    with_scen = r.scenarios[1] if len(r.scenarios) > 1 else None
    no_scen = r.scenarios[0]

    moic_lift = (with_scen.moic - no_scen.moic) if with_scen else 0.0
    irr_lift = (with_scen.irr - no_scen.irr) if with_scen else 0.0

    kpi_strip = (
        ck_kpi_block("Platform EV", f"${r.platform_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Platform Mult", f"{r.platform_mult:.2f}x", "", "") +
        ck_kpi_block("Avg Bolt-on Mult", f"{arb.avg_bolton_mult:.2f}x", "", "") +
        ck_kpi_block("Mult Arbitrage", f"{arb.mult_arbitrage:+.2f}x", "", "") +
        ck_kpi_block("Blended Entry", f"{arb.blended_entry_mult:.2f}x", "", "") +
        ck_kpi_block("Value Uplift", f"${arb.value_uplift_mm:,.0f}M", "", "") +
        ck_kpi_block("MOIC Lift", f"{moic_lift:+.2f}x", "", "") +
        ck_kpi_block("IRR Lift", f"{irr_lift * 100:+.1f}%", "", "")
    )

    bridge_svg = _ebitda_bridge_svg(r.projections)
    proj_svg = _projection_svg(r.projections)
    bolton_tbl = _bolton_table(r.bolt_ons)
    proj_tbl = _projection_table(r.projections)
    scen_tbl = _scenario_table(r.scenarios)

    form = f"""
<form method="GET" action="/bolton-analyzer" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:140px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Platform EBITDA ($M)
    <input name="platform_ebitda" value="{platform_ebitda}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Bolt-ons (1-10)
    <input name="n_boltons" value="{n_boltons}" type="number" min="0" max="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Organic (%)
    <input name="organic" value="{organic}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Rev Syn (%)
    <input name="rev_syn" value="{rev_syn}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Cost Syn (%)
    <input name="cost_syn" value="{cost_syn}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Hold (yrs)
    <input name="hold_years" value="{hold_years}" type="number" min="2" max="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:50px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">
    Run
  </button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Bolt-on M&amp;A Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Buy-and-build roll-up economics — platform + {n_boltons} bolt-ons across {hold_years} years in {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Exit Year EBITDA Bridge</div>
      {bridge_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">EBITDA Projection (Platform + Bolt-ons + Synergy)</div>
      {proj_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Return Scenarios: No Bolt-ons vs. With Bolt-ons</div>
    {scen_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Bolt-on Acquisition Pipeline ({len(r.bolt_ons)} transactions)</div>
    {bolton_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Year-by-Year EBITDA Build</div>
    {proj_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {P['accent']};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Multiple Arbitrage:</strong>
    Platform trades at {r.platform_mult:.2f}x vs. bolt-ons at {arb.avg_bolton_mult:.2f}x (spread {arb.mult_arbitrage:+.2f}x).
    Blended entry {arb.blended_entry_mult:.2f}x. Total immediate value uplift: ${arb.value_uplift_mm:,.0f}M.
    Total equity deployed: ${r.total_capital_deployed_mm:,.1f}M.
  </div>

</div>"""

    return chartis_shell(body, "Bolt-on M&A Analyzer", active_nav="/bolton-analyzer")
