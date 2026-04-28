"""Earnout & Contingent Consideration page — /earnout.

Milestone-based payouts, probability-weighted value, fair-value accounting, IRR impact.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _milestone_waterfall_svg(milestones) -> str:
    if not milestones:
        return ""
    w = 540
    row_h = 28
    h = len(milestones) * row_h + 30
    pad_l = 220
    pad_r = 40
    inner_w = w - pad_l - pad_r

    max_v = max(m.max_payout_mm for m in milestones) or 1

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    pos = P["positive"]; warn = P["warning"]

    bars = []
    for i, m in enumerate(milestones):
        y = 20 + i * row_h
        bh = 16
        # Max payout bar (bg)
        max_w = inner_w
        # Expected payout (fg)
        exp_w = m.expected_payout_mm / max_v * max_w
        full_w = m.max_payout_mm / max_v * max_w
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 2}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(m.milestone[:28])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{full_w:.1f}" height="{bh}" fill="{warn}" opacity="0.35"/>'
            f'<rect x="{pad_l}" y="{y}" width="{exp_w:.1f}" height="{bh}" fill="{pos}" opacity="0.85"/>'
            f'<text x="{pad_l + full_w + 4:.1f}" y="{y + bh - 2}" fill="{P["text_dim"]}" font-size="9" '
            f'font-family="JetBrains Mono,monospace">${m.max_payout_mm:.1f}M / {m.probability_of_achievement * 100:.0f}%</text>'
        )

    legend = (
        f'<rect x="{pad_l}" y="4" width="10" height="10" fill="{pos}" opacity="0.85"/>'
        f'<text x="{pad_l + 14}" y="12" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Expected</text>'
        f'<rect x="{pad_l + 80}" y="4" width="10" height="10" fill="{warn}" opacity="0.35"/>'
        f'<text x="{pad_l + 94}" y="12" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Max Payout</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + legend + "".join(bars) +
        f'</svg>'
    )


def _scenario_dist_svg(scenarios) -> str:
    if not scenarios:
        return ""
    w, h = 540, 200
    pad_l, pad_r, pad_t, pad_b = 50, 30, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_total = max(s.total_consideration_mm for s in scenarios) or 1
    min_total = min(s.total_consideration_mm for s in scenarios)

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    acc = P["accent"]; pos = P["positive"]

    n = len(scenarios)
    bar_w = (inner_w - (n - 1) * 10) / n

    bars = []
    for i, s in enumerate(scenarios):
        x = pad_l + i * (bar_w + 10)
        bh = (s.total_consideration_mm - min_total * 0.85) / (max_total - min_total * 0.85) * inner_h
        y = (h - pad_b) - bh
        alpha = 0.4 + s.probability * 1.5   # probability dictates opacity
        alpha = min(0.95, alpha)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{acc}" opacity="{alpha:.2f}"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${s.total_consideration_mm:,.0f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario[:12])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{pos}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{s.probability * 100:.0f}% prob</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Total Consideration by Scenario ($M)</text>'
        f'</svg>'
    )


def _milestones_table(milestones) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"seller": P["negative"], "buyer": P["accent"], "shared": P["warning"]}
    cols = [("Milestone","left"),("Metric","left"),("Target","left"),("Period","left"),
            ("Max Payout ($M)","right"),("P(Achieve)","right"),("Expected ($M)","right"),("Risk Allocation","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(milestones):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(m.risk_allocation, text_dim)
        prob_c = P["positive"] if m.probability_of_achievement >= 0.7 else (P["accent"] if m.probability_of_achievement >= 0.5 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.milestone)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.target)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.measurement_period)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${m.max_payout_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{prob_c}">{m.probability_of_achievement * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">${m.expected_payout_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.risk_allocation}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenarios_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Scenario","left"),("Probability","right"),("Base Price ($M)","right"),
            ("Earnout ($M)","right"),("Total ($M)","right"),("Implied Multiple","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{s.probability * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.base_purchase_price_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${s.earnout_payout_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${s.total_consideration_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]};font-weight:600">{s.implied_multiple_x:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _fair_value_table(fv) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Period","left"),("Discount Rate","right"),("Expected Payout ($M)","right"),
            ("Present Value ($M)","right"),("Accounting","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, f in enumerate(fv):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(f.period)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.discount_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${f.expected_payout_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${f.present_value_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.accounting_classification)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _irr_table(irr) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Scenario","left"),("Seller Gross EV","right"),("Seller Net Proceeds","right"),
            ("Buyer Eff. Multiple","right"),("Buyer IRR @ 12x Exit","right"),("Preference","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, r in enumerate(irr):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.seller_gross_ev_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${r.seller_net_proceeds_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{r.buyer_effective_mult:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{r.buyer_irr_if_exit_at_12x * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.seller_pref_vs_buyer)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _risk_table(risk) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Risk Factor","left"),("Seller Burden","right"),("Buyer Burden","right"),("Guidance","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, r in enumerate(risk):
        rb = panel_alt if i % 2 == 0 else bg
        sc = P["negative"] if r.seller_burden >= 0.60 else (P["warning"] if r.seller_burden >= 0.45 else P["text_dim"])
        bc = P["negative"] if r.buyer_burden >= 0.60 else (P["warning"] if r.buyer_burden >= 0.45 else P["text_dim"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(r.factor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sc};font-weight:600">{r.seller_burden * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{bc};font-weight:600">{r.buyer_burden * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.guidance)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_earnout(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    base = _f("base", 250.0)
    ebitda = _f("ebitda", 20.0)

    from rcm_mc.data_public.earnout import compute_earnout
    r = compute_earnout(base_purchase_price_mm=base, current_ebitda_mm=ebitda)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Base Price", f"${r.base_purchase_price_mm:,.0f}M", "", "") +
        ck_kpi_block("Max Earnout", f"${r.max_earnout_mm:,.1f}M", "", "") +
        ck_kpi_block("Expected Earnout", f"${r.expected_earnout_mm:,.1f}M", "", "") +
        ck_kpi_block("Expected PV", f"${r.total_expected_payout_pv_mm:,.1f}M", "", "") +
        ck_kpi_block("Headline Mult", f"{r.effective_headline_multiple:.2f}x", "EBITDA", "") +
        ck_kpi_block("Paid Mult (Exp.)", f"{r.effective_paid_multiple:.2f}x", "EBITDA", "") +
        ck_kpi_block("Milestones", str(len(r.milestones)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    milestone_svg = _milestone_waterfall_svg(r.milestones)
    scen_svg = _scenario_dist_svg(r.scenarios)
    ms_tbl = _milestones_table(r.milestones)
    scen_tbl = _scenarios_table(r.scenarios)
    fv_tbl = _fair_value_table(r.fair_value_timeline)
    irr_tbl = _irr_table(r.irr_impacts)
    risk_tbl = _risk_table(r.risk_allocation)

    form = f"""
<form method="GET" action="/earnout" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Base Price ($M)
    <input name="base" value="{base}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Current EBITDA ($M)
    <input name="ebitda" value="{ebitda}" type="number" step="1"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Earnout &amp; Contingent Consideration Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Milestone-based payouts, probability-weighted value, fair-value accounting, IRR impact — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Milestone Payouts — Expected vs Max</div>
      {milestone_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Scenario Distribution</div>
      {scen_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Earnout Milestone Detail</div>
    {ms_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Scenario Analysis</div>
    {scen_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Fair Value / ASC 805 Accounting Timeline</div>
    {fv_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">IRR Impact — Buyer vs Seller</div>
    {irr_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Risk Allocation Matrix</div>
    {risk_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Earnout Thesis:</strong>
    ${r.base_purchase_price_mm:,.0f}M base + up to ${r.max_earnout_mm:,.1f}M earnout. Probability-weighted
    expected additional consideration ${r.expected_earnout_mm:,.1f}M (PV ${r.total_expected_payout_pv_mm:,.1f}M).
    Headline multiple {r.effective_headline_multiple:.2f}x vs. effective paid multiple {r.effective_paid_multiple:.2f}x —
    {((r.effective_headline_multiple - r.effective_paid_multiple) / r.effective_paid_multiple * 100):.1f}% gap reflects
    risk-sharing benefit to buyer.
  </div>

</div>"""

    return chartis_shell(body, "Earnout Analyzer", active_nav="/earnout")
