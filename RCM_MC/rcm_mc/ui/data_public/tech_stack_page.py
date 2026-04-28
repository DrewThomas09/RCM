"""Technology Stack Analyzer page — /tech-stack.

Systems inventory, modernization projects, cybersecurity posture, IT spend benchmarking.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _modernness_heatmap_svg(systems) -> str:
    if not systems:
        return ""
    w = 560
    row_h = 22
    h = len(systems) * row_h + 30
    pad_l = 210
    pad_r = 60
    inner_w = w - pad_l - pad_r

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]

    bars = []
    for i, s in enumerate(systems):
        y = 20 + i * row_h
        bh = 14
        # Color gradient from red (low modern) to green (high)
        if s.modernness_score >= 85:
            color = P["positive"]
        elif s.modernness_score >= 70:
            color = P["accent"]
        elif s.modernness_score >= 50:
            color = P["warning"]
        else:
            color = P["negative"]

        bw = s.modernness_score / 100 * inner_w
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(s.system_type[:26])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">{s.modernness_score}</text>'
            f'<text x="{w - 4}" y="{y + bh - 1}" fill="{text_faint}" font-size="9" text-anchor="end" '
            f'font-family="JetBrains Mono,monospace">${s.annual_cost_mm:,.2f}M</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">System Modernness Score (0-100) &amp; Annual Cost</text>'
        f'</svg>'
    )


def _roi_bubbles_svg(projects) -> str:
    """Cost vs EV uplift bubble chart."""
    if not projects:
        return ""
    w, h = 540, 280
    pad_l, pad_r, pad_t, pad_b = 50, 30, 25, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_cost = max(p.one_time_cost_mm for p in projects) or 1
    max_lift = max(p.moic_lift_pct for p in projects) or 0.01

    bg = P["panel"]; pos = P["positive"]; acc = P["accent"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]
    prio_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}

    bubbles = []
    for p in projects:
        x = pad_l + (p.one_time_cost_mm / max_cost) * inner_w
        y = (h - pad_b) - (p.moic_lift_pct / max_lift) * inner_h
        r = 8 + min(10, p.timeline_months / 3)
        color = prio_colors.get(p.priority, text_dim)
        bubbles.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}" opacity="0.65" stroke="{P["text"]}" stroke-width="0.5"/>'
            f'<text x="{x:.1f}" y="{y + r + 11:.1f}" fill="{text_dim}" font-size="9" text-anchor="middle" '
            f'font-family="JetBrains Mono,monospace">{_html.escape(p.project[:20])}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bubbles) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Modernization ROI (cost × MOIC lift; size = timeline)</text>'
        f'<text x="{pad_l}" y="{h - 5}" fill="{text_faint}" font-size="9" font-family="Inter,sans-serif">One-time Cost →</text>'
        f'</svg>'
    )


def _systems_table(systems) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"modern": P["positive"], "stable": P["accent"], "aging": P["warning"], "legacy": P["negative"]}
    cols = [("System","left"),("Vendor","left"),("Sites","right"),("Version","right"),
            ("Annual Cost ($M)","right"),("Modern","right"),("Interop","right"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(systems):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(s.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.system_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.vendor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.sites_using}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.version_vintage)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.annual_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sc};font-weight:600">{s.modernness_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.interop_score}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{s.status}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _projects_table(projects) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    prio_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Project","left"),("Scope","left"),("One-Time Cost ($M)","right"),
            ("Annual Run-Rate Δ ($M)","right"),("Timeline (mo)","right"),
            ("MOIC Lift","right"),("Risk","left"),("Priority","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(projects):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(p.risk, text_dim)
        pc = prio_colors.get(p.priority, text_dim)
        rr_c = P["positive"] if p.annual_run_rate_delta_mm <= 0 else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.project)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(p.scope)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${p.one_time_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rr_c};font-weight:600">${p.annual_run_rate_delta_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.timeline_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]};font-weight:600">+{p.moic_lift_pct * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{p.risk}</span></td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{p.priority}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _cyber_table(cyber) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    urg_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Metric","left"),("Current","left"),("Target","left"),("Gap","left"),
            ("Remediation ($M)","right"),("Urgency","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(cyber):
        rb = panel_alt if i % 2 == 0 else bg
        uc = urg_colors.get(c.urgency, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.metric)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.current_state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.target_state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["warning"]}">{_html.escape(c.gap)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${c.remediation_cost_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{uc};border:1px solid {uc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{c.urgency}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _buckets_table(buckets) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    var_colors = {"above": P["negative"], "benchmark": P["accent"], "below": P["positive"]}
    cols = [("Category","left"),("Annual Spend ($M)","right"),("% of Revenue","right"),
            ("Benchmark %","right"),("Variance","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, b in enumerate(buckets):
        rb = panel_alt if i % 2 == 0 else bg
        vc = var_colors.get(b.variance, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(b.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${b.annual_spend_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{vc};font-weight:600">{b.pct_of_revenue * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.benchmark_pct * 100:.2f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{vc};border:1px solid {vc};border-radius:2px;letter-spacing:0.06em">{b.variance}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_tech_stack(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    providers = _i("providers", 45)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.tech_stack import compute_tech_stack
    r = compute_tech_stack(sector=sector, revenue_mm=revenue, n_providers=providers, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Primary EHR", r.ehr_vendor, "", "") +
        ck_kpi_block("EHR Fragmentation", f"{r.ehr_fragmentation_score}/100", "", "") +
        ck_kpi_block("Modernness Score", f"{r.modernness_composite}/100", "", "") +
        ck_kpi_block("Cyber Posture", f"{r.cyber_posture_score}/100", "", "") +
        ck_kpi_block("IT Spend", f"${r.total_it_spend_mm:,.1f}M", "", "") +
        ck_kpi_block("IT % of Rev", f"{r.it_spend_pct_revenue * 100:.1f}%", "", "") +
        ck_kpi_block("Mod. Cost", f"${r.total_modernization_cost_mm:,.2f}M", "", "") +
        ck_kpi_block("EV Uplift", f"${r.total_ev_uplift_mm:,.0f}M", "", "")
    )

    heat_svg = _modernness_heatmap_svg(r.systems)
    roi_svg = _roi_bubbles_svg(r.modernization_projects)
    sys_tbl = _systems_table(r.systems)
    proj_tbl = _projects_table(r.modernization_projects)
    cyber_tbl = _cyber_table(r.cyber_metrics)
    bkt_tbl = _buckets_table(r.spend_buckets)

    form = f"""
<form method="GET" action="/tech-stack" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Providers
    <input name="providers" value="{providers}" type="number" step="5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
    <input name="mult" value="{mult}" type="number" step="0.5"
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Technology Stack Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Systems inventory, modernness score, cyber posture, IT spend vs benchmark — {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">System Modernness Heatmap</div>
      {heat_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Modernization ROI Map</div>
      {roi_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">System Inventory ({len(r.systems)} systems)</div>
    {sys_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Modernization Project Portfolio</div>
    {proj_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Cybersecurity Posture Assessment</div>
    {cyber_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">IT Spend by Category (vs Benchmark)</div>
    {bkt_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Tech Stack Thesis:</strong>
    Composite modernness {r.modernness_composite}/100 on ${r.total_it_spend_mm:,.1f}M annual IT spend
    ({r.it_spend_pct_revenue * 100:.1f}% of revenue). EHR fragmentation at {r.ehr_fragmentation_score}/100 is the
    biggest wedge — consolidation unlocks both cost savings and clinical-quality upside. Cyber posture
    {r.cyber_posture_score}/100 needs SOC 2 Type II + HITRUST for exit-readiness.
    ${r.total_modernization_cost_mm:,.1f}M investment drives ${r.total_ev_uplift_mm:,.0f}M EV uplift.
  </div>

</div>"""

    return chartis_shell(body, "Tech Stack", active_nav="/tech-stack")
