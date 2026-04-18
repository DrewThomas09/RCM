"""Scenario Monte Carlo Analyzer page — /scenario-mc.

MOIC outcome distribution, percentile table, driver tornado, probability matrix.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _histogram_svg(distribution, base_case: float, median: float) -> str:
    if not distribution:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 30, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_count = max(b.count for b in distribution)
    n = len(distribution)
    bar_w = (inner_w - (n - 1) * 3) / n

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    neg = P["negative"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    bars = []
    for i, b in enumerate(distribution):
        x = pad_l + i * (bar_w + 3)
        bh = b.count / max_count * inner_h
        y = (h - pad_b) - bh
        # color: red below 1x, amber 1-2x, green above 2x
        if b.moic_bin_high <= 1.0:
            color = neg
        elif b.moic_bin_high <= 2.0:
            color = P["warning"]
        elif b.moic_bin_high <= 3.0:
            color = acc
        else:
            color = pos
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{b.moic_bin_low:.1f}</text>'
        )

    # Median line
    def _moic_to_x(m):
        # Map using log-ish positioning
        total_range = distribution[-1].moic_bin_high - distribution[0].moic_bin_low
        if total_range <= 0:
            return pad_l
        return pad_l + ((m - distribution[0].moic_bin_low) / total_range) * inner_w

    med_x = _moic_to_x(median)
    base_x = _moic_to_x(base_case)

    marker_lines = (
        f'<line x1="{med_x:.1f}" y1="{pad_t - 5}" x2="{med_x:.1f}" y2="{h - pad_b}" '
        f'stroke="{P["text"]}" stroke-width="2" stroke-dasharray="4,3"/>'
        f'<text x="{med_x:.1f}" y="{pad_t - 8}" fill="{P["text"]}" font-size="10" text-anchor="middle" '
        f'font-family="JetBrains Mono,monospace;font-weight:600">MEDIAN {median:.2f}x</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) + marker_lines +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">MOIC Outcome Distribution ({sum(b.count for b in distribution):,} sims)</text>'
        f'</svg>'
    )


def _tornado_svg(sensitivities) -> str:
    if not sensitivities:
        return ""
    w, h = 540, 200
    pad_l, pad_r, pad_t, pad_b = 170, 40, 30, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    row_h = (inner_h - 10) / len(sensitivities)

    max_abs = max(abs(s.tornado_range_mm) for s in sensitivities) or 1
    center_x = pad_l + inner_w / 2

    bg = P["panel"]; acc = P["accent"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    bars = []
    for i, s in enumerate(sensitivities):
        y = pad_t + i * row_h + 2
        bh = row_h - 8
        bw = abs(s.tornado_range_mm) / max_abs * (inner_w / 2)
        xr = center_x if s.tornado_range_mm >= 0 else center_x - bw
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh / 2 + 3}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(s.driver)}</text>'
            f'<rect x="{xr:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{acc}" opacity="0.85"/>'
            f'<text x="{xr + bw + 4:.1f}" y="{y + bh / 2 + 3}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace;font-weight:600">±${s.tornado_range_mm:,.0f}M</text>'
        )

    axis = (
        f'<line x1="{center_x:.1f}" y1="{pad_t}" x2="{center_x:.1f}" y2="{h - pad_b}" '
        f'stroke="{border}" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + axis + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Tornado — Equity Value Range ($M) by Driver (P10/P90)</text>'
        f'</svg>'
    )


def _inputs_table(inputs) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Input Driver","left"),("Base Case","right"),("Low (P5)","right"),("High (P95)","right"),("Unit","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, inp in enumerate(inputs):
        rb = panel_alt if i % 2 == 0 else bg
        fmt = "{:+.2%}" if inp.unit == "%" or inp.unit == "pp" else ("{:.2f}" if inp.unit == "x" else "{:.2%}")
        # Just use .2f for simplicity
        def _fmt(v, u):
            if u == "%":
                return f"{v * 100:+.1f}%"
            if u == "pp":
                return f"{v * 100:+.1f}pp"
            if u == "x":
                return f"{v:.2f}x"
            return f"{v * 100:.0f}%"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(inp.driver)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_fmt(inp.base_case, inp.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_fmt(inp.low, inp.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_fmt(inp.high, inp.unit)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(inp.unit)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _percentile_table(percentiles) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Metric","left"),("P5","right"),("P25","right"),("Median","right"),
            ("P75","right"),("P95","right"),("Mean","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, r in enumerate(percentiles):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">{r.p5:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{r.p25:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{r.p50:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{r.p75:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{r.p95:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.mean:.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _probability_table(probs) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Outcome","left"),("Probability","right"),("Description","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(probs):
        rb = panel_alt if i % 2 == 0 else bg
        color = neg if "Loss" in p.outcome or "Downside" in p.outcome else pos
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(p.outcome)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{color};font-weight:600">{p.probability * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.description)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _sensitivity_table(sensitivities) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Driver","left"),("Correlation to MOIC","right"),("Elasticity","right"),("Equity Value Range ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(sensitivities):
        rb = panel_alt if i % 2 == 0 else bg
        color = P["positive"] if abs(s.correlation_to_moic) >= 0.5 else (P["accent"] if abs(s.correlation_to_moic) >= 0.3 else P["text_dim"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.driver)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{color}">{s.correlation_to_moic:+.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.elasticity:+.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">±${s.tornado_range_mm:,.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_scenario_mc(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    ev = _f("ev", 300.0)
    margin = _f("margin", 0.18)
    ev_ebitda = _f("ev_ebitda", 12.0)
    hold = _i("hold_years", 5)
    eq_pct = _f("equity_pct", 0.45)
    n_sims = _i("n_sims", 5000)

    from rcm_mc.data_public.scenario_mc import compute_scenario_mc
    r = compute_scenario_mc(ev_mm=ev, ebitda_margin=margin, ev_ebitda=ev_ebitda,
                             hold_years=hold, equity_pct=eq_pct, n_sims=n_sims)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Simulations", f"{r.n_simulations:,}", "", "") +
        ck_kpi_block("Base Case MOIC", f"{r.base_case_moic:.2f}x", "", "") +
        ck_kpi_block("Median MOIC", f"{r.median_moic:.2f}x", "", "") +
        ck_kpi_block("P5 (Downside)", f"{r.p5_moic:.2f}x", "", "") +
        ck_kpi_block("P95 (Upside)", f"{r.p95_moic:.2f}x", "", "") +
        ck_kpi_block("P(MOIC ≥ 2x)", f"{r.prob_moic_gt_2x * 100:.1f}%", "", "") +
        ck_kpi_block("P(MOIC ≥ 3x)", f"{r.prob_moic_gt_3x * 100:.1f}%", "", "") +
        ck_kpi_block("P(Loss)", f"{r.prob_loss * 100:.1f}%", "", "")
    )

    hist_svg = _histogram_svg(r.moic_distribution, r.base_case_moic, r.median_moic)
    tornado_svg = _tornado_svg(r.sensitivities)
    input_tbl = _inputs_table(r.inputs)
    pct_tbl = _percentile_table(r.percentiles)
    prob_tbl = _probability_table(r.probabilities)
    sens_tbl = _sensitivity_table(r.sensitivities)

    form = f"""
<form method="GET" action="/scenario-mc" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EV ($M)
    <input name="ev" value="{ev}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin
    <input name="margin" value="{margin}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Entry EV/EBITDA
    <input name="ev_ebitda" value="{ev_ebitda}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Hold Years
    <input name="hold_years" value="{hold}" type="number" min="2" max="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:50px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Equity %
    <input name="equity_pct" value="{eq_pct}" type="number" step="0.05"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Simulations
    <input name="n_sims" value="{n_sims}" type="number" min="1000" max="25000" step="1000"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run MC</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Scenario Monte Carlo Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Multi-driver MOIC distribution — revenue growth, margin expansion, exit multiple, debt paydown —
      {r.n_simulations:,} sims / {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">MOIC Outcome Distribution</div>
    {hist_svg}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Percentile Summary</div>
      {pct_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Probability Matrix</div>
      {prob_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Driver Tornado</div>
    {tornado_svg}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Input Distributions</div>
      {input_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Driver Sensitivity Detail</div>
      {sens_tbl}
    </div>
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Monte Carlo Thesis:</strong>
    {r.n_simulations:,} Monte Carlo paths — median MOIC {r.median_moic:.2f}x (P5: {r.p5_moic:.2f}x,
    P95: {r.p95_moic:.2f}x). {r.prob_moic_gt_2x * 100:.0f}% probability of ≥2x, {r.prob_moic_gt_3x * 100:.0f}% of ≥3x.
    Downside risk: {r.prob_loss * 100:.1f}% probability of principal loss. Revenue growth is the dominant driver;
    exit multiple is next-most-material.
  </div>

</div>"""

    return chartis_shell(body, "Scenario Monte Carlo", active_nav="/scenario-mc")
