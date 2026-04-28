"""Exit Readiness Index page — /exit-readiness.

Multi-dimensional readiness scoring across Financial / Operational /
Commercial / Legal / Management dimensions. Gap inventory, pathway
scenarios, and days-to-ready timeline.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block
from rcm_mc.ui.chartis._helpers import render_page_explainer


def _spider_svg(dimensions) -> str:
    """Radar chart over 5 dimensions."""
    import math
    if not dimensions:
        return ""
    w, h = 360, 260
    cx, cy = w / 2, h / 2 + 5
    r_max = 95

    bg = P["panel"]
    acc = P["accent"]
    text_dim = P["text_dim"]
    text_faint = P["text_faint"]
    border = P["border"]

    n = len(dimensions)
    angles = [(-math.pi / 2) + (2 * math.pi / n) * i for i in range(n)]

    # Grid rings
    grid = []
    for frac in [0.25, 0.5, 0.75, 1.0]:
        pts = []
        for a in angles:
            x = cx + r_max * frac * math.cos(a)
            y = cy + r_max * frac * math.sin(a)
            pts.append(f"{x:.1f},{y:.1f}")
        grid.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="{border}" stroke-width="0.5" opacity="0.6"/>')

    # Data polygon
    data_pts = []
    for d, a in zip(dimensions, angles):
        r = r_max * d.score / 100
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        data_pts.append(f"{x:.1f},{y:.1f}")
    data_poly = f'<polygon points="{" ".join(data_pts)}" fill="{acc}" fill-opacity="0.25" stroke="{acc}" stroke-width="2"/>'

    # Data dots and labels
    dots_labels = []
    for d, a in zip(dimensions, angles):
        r = r_max * d.score / 100
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        dots_labels.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{acc}"/>')
        # label positioned outside the ring
        lx = cx + (r_max + 18) * math.cos(a)
        ly = cy + (r_max + 18) * math.sin(a) + 3
        dots_labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{text_dim}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(d.dimension[:11])}</text>'
            f'<text x="{lx:.1f}" y="{ly + 12:.1f}" fill="{P["text"]}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{d.score:.0f}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(grid) + data_poly + "".join(dots_labels)
        + f'</svg>'
    )


def _readiness_bar_svg(score: float, tier: str) -> str:
    w, h = 520, 80
    pad_l, pad_r, pad_t, pad_b = 20, 20, 28, 20
    inner_w = w - pad_l - pad_r

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    border = P["border"]

    # Tier bands (cumulative): 0-45 red, 45-68 warning, 68-85 accent, 85-100 green
    bands = [
        (0, 45, P["negative"], "Not Ready"),
        (45, 68, P["warning"], "Developing"),
        (68, 85, P["accent"], "Near-Ready"),
        (85, 100, P["positive"], "Ready"),
    ]
    y = 40
    bar_h = 16
    band_svgs = []
    for start, end, color, label in bands:
        x = pad_l + (start / 100) * inner_w
        wd = ((end - start) / 100) * inner_w
        band_svgs.append(
            f'<rect x="{x:.1f}" y="{y}" width="{wd:.1f}" height="{bar_h}" fill="{color}" opacity="0.55"/>'
            f'<text x="{x + wd / 2:.1f}" y="{y + bar_h + 12}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{label}</text>'
        )

    # Marker
    mx = pad_l + (score / 100) * inner_w
    marker = (
        f'<line x1="{mx:.1f}" y1="{y - 8}" x2="{mx:.1f}" y2="{y + bar_h + 4}" '
        f'stroke="{P["text"]}" stroke-width="2"/>'
        f'<polygon points="{mx - 5:.1f},{y - 12} {mx + 5:.1f},{y - 12} {mx:.1f},{y - 4}" fill="{P["text"]}"/>'
        f'<text x="{mx:.1f}" y="{y - 15}" fill="{P["text"]}" font-size="11" '
        f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{score:.0f}</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(band_svgs) + marker
        + f'<text x="{pad_l}" y="14" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Composite Exit Readiness: {score:.1f}/100 — {_html.escape(tier)}</text>'
        f'</svg>'
    )


def _dimension_table(dimensions) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Dimension","left"),("Weight","right"),("Score","right"),("Contribution","right"),
            ("Ready","right"),("Gap","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, d in enumerate(dimensions):
        rb = panel_alt if i % 2 == 0 else bg
        score_color = P["positive"] if d.score >= 80 else (P["accent"] if d.score >= 65 else (P["warning"] if d.score >= 45 else P["negative"]))
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(d.dimension)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.weight * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{score_color};font-weight:600">{d.score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.weighted_contribution:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{d.criteria_ready}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"] if d.criteria_gap else text_dim}">{d.criteria_gap}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _criteria_table(criteria) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"ready": P["positive"], "in-progress": P["warning"], "gap": P["negative"]}
    imp_colors = {"critical": P["negative"], "standard": P["accent"], "nice-to-have": P["text_faint"]}
    cols = [("Dim","left"),("Criterion","left"),("Status","left"),("Importance","left"),
            ("Pts","right"),("Days to Close","right"),("Owner","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(criteria):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(c.status, text_dim)
        ic = imp_colors.get(c.importance, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.dimension[:4])}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text}">{_html.escape(c.criterion)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{c.status}</span></td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ic};border:1px solid {ic};border-radius:2px;letter-spacing:0.06em">{c.importance}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.score_pts:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if c.estimated_days_to_close else text_dim}">{c.estimated_days_to_close}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.owner)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _gap_table(gaps) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    sev_colors = {"critical": P["negative"], "high": P["warning"], "medium": P["accent"], "low": P["text_faint"]}
    cols = [("Dimension","left"),("Gap","left"),("Severity","left"),("Days","right"),("Cost ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    if not gaps:
        return f'<p style="color:{text_dim};font-size:11px;padding:12px 0">No gaps identified — exit-ready.</p>'
    trs = []
    for i, g in enumerate(gaps):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_colors.get(g.severity, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(g.dimension)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text}">{_html.escape(g.criterion)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{g.severity}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{g.days_to_close}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${g.cost_estimate_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenario_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Exit Pathway","left"),("Readiness Bar","right"),("Current vs Bar","right"),
            ("Months to Ready","right"),("Likely Multiple","right"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        pct_color = P["positive"] if s.current_readiness_pct >= 100 else (P["warning"] if s.current_readiness_pct >= 85 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.pathway)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.readiness_bar}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pct_color};font-weight:600">{s.current_readiness_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if s.months_to_ready else P["positive"]}">{s.months_to_ready}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.likely_multiple:.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_exit_readiness(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    hold = _f("hold_years", 4.0)
    pathway = params.get("pathway", "Strategic Sale")

    from rcm_mc.data_public.exit_readiness import compute_exit_readiness
    r = compute_exit_readiness(hold_years=hold, pathway=pathway)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Overall Score", f"{r.overall_score:.1f}", "/100", "") +
        ck_kpi_block("Tier", r.tier, "", "") +
        ck_kpi_block("Financial", f"{r.dimensions[0].score:.0f}", "", "") +
        ck_kpi_block("Operational", f"{r.dimensions[1].score:.0f}", "", "") +
        ck_kpi_block("Commercial", f"{r.dimensions[2].score:.0f}", "", "") +
        ck_kpi_block("Legal", f"{r.dimensions[3].score:.0f}", "", "") +
        ck_kpi_block("Management", f"{r.dimensions[4].score:.0f}", "", "") +
        ck_kpi_block("Critical Gaps", str(r.critical_gap_count), "", "")
    )

    bar_svg = _readiness_bar_svg(r.overall_score, r.tier)
    spider = _spider_svg(r.dimensions)
    dim_tbl = _dimension_table(r.dimensions)
    crit_tbl = _criteria_table(r.criteria)
    gap_tbl = _gap_table(r.gaps)
    scen_tbl = _scenario_table(r.scenarios)

    form = f"""
<form method="GET" action="/exit-readiness" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Hold Years
    <input name="hold_years" value="{hold}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Pathway
    <select name="pathway"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">
      <option value="Strategic Sale" {"selected" if pathway == "Strategic Sale" else ""}>Strategic Sale</option>
      <option value="Sponsor-to-Sponsor" {"selected" if pathway == "Sponsor-to-Sponsor" else ""}>Sponsor-to-Sponsor</option>
      <option value="IPO / SPAC" {"selected" if pathway == "IPO / SPAC" else ""}>IPO / SPAC</option>
    </select>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Exit Readiness Index</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Multi-dimensional IPO / sale readiness scoring — {len(r.criteria)} criteria across 5 dimensions —
      {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">Composite Readiness</div>
    {bar_svg}
  </div>

  <div style="display:grid;grid-template-columns:1.4fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Dimension Radar</div>
      {spider}
    </div>
    <div style="{cell}">
      <div style="{h3}">Dimension Breakdown</div>
      {dim_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Exit Pathway Scenarios</div>
    {scen_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Outstanding Gap Inventory ({len(r.gaps)} items)</div>
    {gap_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Full Criteria Checklist ({len(r.criteria)} items)</div>
    {crit_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Exit Readiness Thesis:</strong>
    Overall {r.overall_score:.1f}/100 — <strong style="color:{text}">{r.tier}</strong>.
    {r.critical_gap_count} critical gap(s), ~${r.total_gap_cost_mm:,.2f}M of gap-closure spend needed,
    {r.est_days_to_exit_ready} days to fully exit-ready. Strategic Sale pathway most achievable path today.
  </div>

</div>"""

    explainer = render_page_explainer(
        what=(
            "Multi-dimensional exit-readiness scoring across "
            "financial, operational, commercial, legal, and management "
            "dimensions, with a radar chart, a gap inventory (cost + "
            "days to close), and pathway scenarios for strategic sale, "
            "secondary buyout, and IPO."
        ),
        source="data_public/exit_readiness.py (multi-dimensional readiness model).",
        page_key="exit-readiness",
    )
    return chartis_shell(explainer + body, "Exit Readiness Index", active_nav="/exit-readiness")
