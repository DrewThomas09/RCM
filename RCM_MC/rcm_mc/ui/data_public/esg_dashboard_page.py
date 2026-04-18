"""ESG Dashboard page — /esg-dashboard.

Environmental, Social, Governance scorecard with ILPA / SASB / TCFD disclosures
and workforce diversity, patient access, compliance maturity metrics.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _esg_ring_svg(overall: float, e: float, s: float, g: float, tier: str) -> str:
    import math
    w, h = 300, 200
    cx, cy = w / 2, h / 2 + 5
    bg = P["panel"]

    def _ring(r, score, color, label, angle_offset):
        end_deg = -90 + (score / 100) * 360
        start = math.radians(-90)
        end = math.radians(end_deg)
        x1 = cx + r * math.cos(start)
        y1 = cy + r * math.sin(start)
        x2 = cx + r * math.cos(end)
        y2 = cy + r * math.sin(end)
        large = 1 if (end_deg + 90) > 180 else 0
        return (
            f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{P["border"]}" stroke-width="9" opacity="0.3"/>'
            f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="9" opacity="0.92"/>'
        )

    overall_color = P["positive"] if overall >= 70 else (P["accent"] if overall >= 50 else P["warning"])

    # 3 concentric rings
    rings = (
        _ring(85, e, "#14b8a6", "E", 0) +      # Environmental (teal)
        _ring(68, s, P["accent"], "S", 0) +    # Social (blue)
        _ring(51, g, "#a78bfa", "G", 0)        # Governance (purple)
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + rings +
        f'<text x="{cx}" y="{cy + 2}" text-anchor="middle" fill="{P["text"]}" '
        f'font-size="28" font-weight="700" font-family="JetBrains Mono,monospace">{overall:.0f}</text>'
        f'<text x="{cx}" y="{cy + 17}" text-anchor="middle" fill="{overall_color}" '
        f'font-size="9" font-weight="600" letter-spacing="0.10em" font-family="Inter,sans-serif">{_html.escape(tier.upper())}</text>'
        # Legend
        f'<rect x="10" y="{h - 18}" width="8" height="8" fill="#14b8a6"/>'
        f'<text x="22" y="{h - 10}" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">E {e:.0f}</text>'
        f'<rect x="70" y="{h - 18}" width="8" height="8" fill="{P["accent"]}"/>'
        f'<text x="82" y="{h - 10}" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">S {s:.0f}</text>'
        f'<rect x="130" y="{h - 18}" width="8" height="8" fill="#a78bfa"/>'
        f'<text x="142" y="{h - 10}" fill="{P["text_dim"]}" font-size="9" font-family="JetBrains Mono,monospace">G {g:.0f}</text>'
        f'</svg>'
    )


def _metrics_by_cat_svg(metrics, category: str, color: str) -> str:
    items = [m for m in metrics if m.category == category]
    if not items:
        return ""
    w = 280
    row_h = 26
    h = len(items) * row_h + 25
    pad_l = 140
    inner_w = w - pad_l - 30

    bg = P["panel"]; text_dim = P["text_dim"]

    bars = []
    for i, m in enumerate(items):
        y = 18 + i * row_h
        bw = m.score / 100 * inner_w
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + 8}" fill="{text_dim}" font-size="9" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(m.metric[:22])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="10" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + 8}" fill="{P["text_dim"]}" font-size="9" '
            f'font-family="JetBrains Mono,monospace">{m.score:.0f}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        f'<text x="10" y="12" fill="{text_dim}" font-size="10" letter-spacing="0.08em" font-family="Inter,sans-serif">{category}</text>'
        + "".join(bars) +
        f'</svg>'
    )


def _metric_table(metrics) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cat_colors = {"E": "#14b8a6", "S": P["accent"], "G": "#a78bfa"}
    cols = [("Cat","left"),("Metric","left"),("Value","right"),("Unit","left"),
            ("Benchmark","right"),("Score","right"),("Weight","right"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(metrics):
        rb = panel_alt if i % 2 == 0 else bg
        cc = cat_colors.get(m.category, text_dim)
        score_color = P["positive"] if m.score >= 75 else (P["accent"] if m.score >= 55 else P["warning"] if m.score >= 35 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 6px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px">{m.category}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{m.value:.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.benchmark:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{score_color};font-weight:600">{m.score:.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.weight * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _diversity_table(diversity) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"strong": P["positive"], "adequate": P["accent"], "gap": P["warning"], "lagging": P["negative"]}
    cols = [("Dimension","left"),("% Women","right"),("% Minority","right"),("Women & Min. %","right"),
            ("Benchmark W","right"),("Benchmark M","right"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, d in enumerate(diversity):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(d.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(d.dimension)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.pct_women * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.pct_minority * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.pct_women_minority * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.benchmark_women * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.benchmark_minority * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(d.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _access_table(access) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Population","left"),("% Patients","right"),("Revenue ($M)","right"),
            ("Community Hours","right"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, a in enumerate(access):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(a.population)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.pct_patients * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${a.revenue_contribution_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{a.community_benefit_hours:,}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _disclosure_table(disclosures) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"compliant": P["positive"], "partial": P["warning"], "gap": P["negative"]}
    cols = [("Framework","left"),("Category","left"),("Requirement","left"),("Status","left"),("Evidence","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, d in enumerate(disclosures):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(d.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(d.framework)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text}">{_html.escape(d.requirement)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{d.status}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.evidence)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_esg_dashboard(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)

    from rcm_mc.data_public.esg_dashboard import compute_esg_dashboard
    r = compute_esg_dashboard(sector=sector, revenue_mm=revenue)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("ESG Score", f"{r.overall_score:.0f}", "/100", "") +
        ck_kpi_block("Tier", r.tier, "", "") +
        ck_kpi_block("E Score", f"{r.e_score:.0f}", "", "") +
        ck_kpi_block("S Score", f"{r.s_score:.0f}", "", "") +
        ck_kpi_block("G Score", f"{r.g_score:.0f}", "", "") +
        ck_kpi_block("Metrics", str(len(r.metrics)), "", "") +
        ck_kpi_block("LP Disclosures", str(len(r.lp_disclosures)), "", "") +
        ck_kpi_block("Gaps", str(r.total_disclosure_gaps), "", "")
    )

    ring_svg = _esg_ring_svg(r.overall_score, r.e_score, r.s_score, r.g_score, r.tier)
    e_svg = _metrics_by_cat_svg(r.metrics, "E", "#14b8a6")
    s_svg = _metrics_by_cat_svg(r.metrics, "S", acc)
    g_svg = _metrics_by_cat_svg(r.metrics, "G", "#a78bfa")

    metric_tbl = _metric_table(r.metrics)
    div_tbl = _diversity_table(r.diversity)
    access_tbl = _access_table(r.access)
    disc_tbl = _disclosure_table(r.lp_disclosures)

    form = f"""
<form method="GET" action="/esg-dashboard" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
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
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">ESG / Sustainability Dashboard</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      LP-facing ESG diligence — environmental, social, governance metrics with ILPA / SASB / TCFD framework
      alignment — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">ESG Composite Scorecard</div>
      {ring_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Environmental Metrics</div>
      {e_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Social Metrics</div>
      {s_svg}
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Governance Metrics</div>
      {g_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Workforce Diversity</div>
      {div_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Patient Access / Community Benefit</div>
    {access_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">LP Framework Disclosures (ILPA / SASB / TCFD / UN PRI)</div>
    {disc_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">All ESG Metrics</div>
    {metric_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">ESG Thesis:</strong>
    Current ESG score {r.overall_score:.0f} ({r.tier}). Environmental needs attention ({r.e_score:.0f}),
    Social strong ({r.s_score:.0f}), Governance adequate ({r.g_score:.0f}).
    {r.total_disclosure_gaps} LP framework disclosure gap(s) identified. A {r.tier}-tier ESG profile
    is attractive to ILPA-aligned LPs and can compress cost of capital in fundraise.
  </div>

</div>"""

    return chartis_shell(body, "ESG Dashboard", active_nav="/esg-dashboard")
