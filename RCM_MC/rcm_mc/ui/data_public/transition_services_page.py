"""Transition Services Tracker page — /transition-services.

TSA catalog, standalone cost bridge, milestones, integration phases for carve-out
and bolt-on scenarios.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _cost_stack_svg(tsa_cost: float, standup_cost: float, integration_cost: float) -> str:
    w, h = 560, 180
    pad_l, pad_r, pad_t, pad_b = 40, 30, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    total = tsa_cost + standup_cost + integration_cost or 1
    bars = [
        ("TSA Services", tsa_cost, P["accent"]),
        ("Stand-up CapEx", standup_cost, P["warning"]),
        ("Integration", integration_cost, P["negative"] if integration_cost > 0 else P["positive"]),
        ("Total", total, P["text_faint"]),
    ]

    max_v = max(total, tsa_cost, standup_cost, integration_cost) * 1.15
    n = len(bars)
    bar_w = (inner_w - (n - 1) * 12) / n

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]

    rects = []
    for i, (label, val, color) in enumerate(bars):
        x = pad_l + i * (bar_w + 12)
        bh = (abs(val) / max_v) * inner_h if max_v else 0
        y = (h - pad_b) - bh
        rects.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="11" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${val:,.2f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(label)}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(rects) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Transition Cost Summary ($M)</text>'
        f'</svg>'
    )


def _timeline_svg(milestones) -> str:
    if not milestones:
        return ""
    w, h = 620, 260
    pad_l, pad_r, pad_t, pad_b = 30, 30, 25, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_days = max(m.days_from_close for m in milestones)

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]
    stat_colors = {"complete": P["positive"], "on-track": P["accent"], "at-risk": P["warning"], "delayed": P["negative"]}

    row_h = inner_h / len(milestones)

    items = []
    for i, m in enumerate(milestones):
        y = pad_t + i * row_h + row_h / 2
        x = pad_l + (m.days_from_close / max_days) * inner_w
        color = stat_colors.get(m.status, text_dim)
        items.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{border}" stroke-width="1"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>'
            f'<text x="{x + 8:.1f}" y="{y + 3:.1f}" fill="{P["text_dim"]}" font-size="9" '
            f'font-family="JetBrains Mono,monospace">{_html.escape(m.milestone[:36])}</text>'
            f'<text x="{x + 8:.1f}" y="{y + 14:.1f}" fill="{color}" font-size="8" '
            f'font-family="JetBrains Mono,monospace">{_html.escape(m.status)}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(items) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Milestone Timeline (days from close)</text>'
        f'</svg>'
    )


def _services_table(services) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    comp_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    spar_colors = {"clean": P["positive"], "at_risk": P["warning"], "critical": P["negative"]}
    cols = [("Service","left"),("Baseline (mo)","right"),("Extension (mo)","right"),
            ("Monthly Cost ($K)","right"),("Total ($M)","right"),("Complexity","left"),
            ("Termination Risk","left"),("Owner","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(services):
        rb = panel_alt if i % 2 == 0 else bg
        cc = comp_colors.get(s.transition_complexity, text_dim)
        sc = spar_colors.get(s.sparrow_of_termination, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.function)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.baseline_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">+{s.extension_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.monthly_cost_k:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]};font-weight:600">${s.total_cost_mm:,.3f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{s.transition_complexity}</span></td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.sparrow_of_termination.replace("_", " "))}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.owner)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _bridge_table(bridge) -> str:
    if not bridge:
        return f'<p style="color:{P["text_dim"]};font-size:11px;padding:12px 0">No standalone cost bridge (bolt-on scenario — integrated into parent operations).</p>'
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    cols = [("Function","left"),("Shared Baseline ($K)","right"),("Standalone ($K)","right"),
            ("Δ ($K)","right"),("% Increase","right"),("One-time Stand-up ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, b in enumerate(bridge):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(b.function)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${b.shared_cost_baseline_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${b.standalone_cost_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">+${b.delta_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">+{b.pct_increase * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${b.one_time_stand_up_mm:,.3f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _milestones_table(milestones) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"complete": P["positive"], "on-track": P["accent"], "at-risk": P["warning"], "delayed": P["negative"]}
    cols = [("Milestone","left"),("Target Date","right"),("Days from Close","right"),
            ("Dependencies","right"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(milestones):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(m.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.milestone)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(m.target_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.days_from_close}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.dependencies}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.status}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _phases_table(phases) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    cols = [("Phase","left"),("Months","left"),("Focus","left"),
            ("Cost ($M)","right"),("Headcount Δ","right"),("Risk","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(phases):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(p.risk_level, text_dim)
        cost_c = P["positive"] if p.cost_mm < 0 else P["warning"]
        hc_c = P["positive"] if p.headcount_impact < 0 else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.phase)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">M{p.start_month} → M{p.end_month}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(p.focus)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cost_c}">${p.cost_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hc_c}">{p.headcount_impact:+d}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{p.risk_level}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_transition_services(params: dict = None) -> str:
    params = params or {}
    scenario = params.get("scenario", "Carve-out") or "Carve-out"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)

    from rcm_mc.data_public.transition_services import compute_transition_services
    r = compute_transition_services(revenue_mm=revenue, scenario=scenario)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Scenario", scenario, "", "") +
        ck_kpi_block("TSA Cost", f"${r.total_tsa_cost_mm:,.2f}M", "", "") +
        ck_kpi_block("Stand-up CapEx", f"${r.total_standup_cost_mm:,.2f}M", "", "") +
        ck_kpi_block("Integration", f"${r.total_integration_cost_mm:,.2f}M", "", "") +
        ck_kpi_block("TSA Duration", f"{r.tsa_duration_months} mo", "", "") +
        ck_kpi_block("Complexity", f"{r.tsa_complexity_score}/10", "", "") +
        ck_kpi_block("Services", str(len(r.services)), "", "") +
        ck_kpi_block("Annual Standalone Δ", f"${r.total_delta_mm:,.2f}M", "", "")
    )

    cost_svg = _cost_stack_svg(r.total_tsa_cost_mm, r.total_standup_cost_mm, r.total_integration_cost_mm)
    timeline_svg = _timeline_svg(r.milestones)
    svc_tbl = _services_table(r.services)
    bridge_tbl = _bridge_table(r.standalone_bridge)
    mile_tbl = _milestones_table(r.milestones)
    phase_tbl = _phases_table(r.integration_phases)

    form = f"""
<form method="GET" action="/transition-services" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Scenario
    <select name="scenario"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">
      <option value="Carve-out" {"selected" if scenario == "Carve-out" else ""}>Carve-out</option>
      <option value="Bolt-on" {"selected" if scenario == "Bolt-on" else ""}>Bolt-on</option>
    </select>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10"
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Transition Services Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      TSA catalog, standalone cost bridge, milestones, integration phases — {scenario} scenario — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1.2fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Transition Cost Summary</div>
      {cost_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Milestone Timeline</div>
      {timeline_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">TSA Service Catalog</div>
    {svc_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Standalone Cost Bridge ({scenario})</div>
    {bridge_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Milestones Detail</div>
    {mile_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Integration Phase Plan</div>
    {phase_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">TSA Thesis:</strong>
    {scenario} transition: ${r.total_tsa_cost_mm:,.2f}M in TSA fees over {r.tsa_duration_months} months,
    ${r.total_standup_cost_mm:,.2f}M one-time stand-up,
    ${r.total_delta_mm:,.2f}M annual standalone run-rate step-up. Complexity score {r.tsa_complexity_score}/10.
    Clinical IT and RCM separation are the critical-path items for healthcare carve-outs.
  </div>

</div>"""

    return chartis_shell(body, "Transition Services", active_nav="/transition-services")
