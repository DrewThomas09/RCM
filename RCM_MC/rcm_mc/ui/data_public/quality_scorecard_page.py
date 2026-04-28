"""Clinical Quality Scorecard page — /quality-scorecard.

HEDIS, Stars, readmission, VBC participation with quality-adjusted EBITDA.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _score_ring_svg(score: float, tier: str) -> str:
    import math
    w, h = 260, 170
    cx, cy = w / 2, h / 2 + 10
    r_outer, r_inner = 80, 58
    bg = P["panel"]

    # Background arc
    def _arc(start_deg, end_deg, color, width):
        sr = math.radians(start_deg)
        er = math.radians(end_deg)
        x1 = cx + r_outer * math.cos(sr)
        y1 = cy + r_outer * math.sin(sr)
        x2 = cx + r_outer * math.cos(er)
        y2 = cy + r_outer * math.sin(er)
        large = 1 if (end_deg - start_deg) > 180 else 0
        return (f'<path d="M {x1:.1f} {y1:.1f} A {r_outer} {r_outer} 0 {large} 1 {x2:.1f} {y2:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="{width}" opacity="0.9"/>')

    # Background ring
    bg_ring = _arc(-90, 270, P["border"], 14)

    # Score arc
    color = P["positive"] if score >= 75 else (P["accent"] if score >= 55 else (P["warning"] if score >= 35 else P["negative"]))
    end_deg = -90 + (score / 100) * 360 - 0.1
    score_arc = _arc(-90, end_deg, color, 14)

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + bg_ring + score_arc +
        f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" fill="{P["text"]}" '
        f'font-size="32" font-weight="700" font-family="JetBrains Mono,monospace">{score:.0f}</text>'
        f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" fill="{color}" '
        f'font-size="10" font-weight="600" letter-spacing="0.12em" font-family="Inter,sans-serif">{_html.escape(tier.upper())}</text>'
        f'<text x="{cx}" y="16" text-anchor="middle" fill="{P["text_dim"]}" '
        f'font-size="9" letter-spacing="0.1em" font-family="Inter,sans-serif">QUALITY SCORE / 100</text>'
        f'</svg>'
    )


def _metrics_table(metrics) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    status_colors = {
        "top_decile": P["positive"], "above_median": P["accent"],
        "below_median": P["warning"], "bottom_decile": P["negative"],
    }
    cols = [("Metric","left"),("Value","right"),("Unit","left"),("Benchmark","right"),
            ("Percentile","right"),("Status","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(metrics):
        rb = panel_alt if i % 2 == 0 else bg
        sc = status_colors.get(m.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{m.value:.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.benchmark:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sc};font-weight:600">{m.percentile:.0f}th</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.status.replace("_", " "))}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _hedis_table(hedis) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("HEDIS Code","left"),("Measure","left"),("Current","right"),("Benchmark","right"),
            ("Gap","right"),("Applies","left"),("Patients Affected","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, h in enumerate(hedis):
        rb = panel_alt if i % 2 == 0 else bg
        gc = pos if h.gap_pct >= 0 else neg
        applies_c = pos if h.applies else P["text_faint"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(h.code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim}">{_html.escape(h.name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{h.current_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{h.benchmark * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gc};font-weight:600">{h.gap_pct * 100:+.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{applies_c};border:1px solid {applies_c};border-radius:2px;letter-spacing:0.06em">{"yes" if h.applies else "no"}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{h.est_patients_affected:,}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _vbc_table(vbc) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    risk_colors = {
        "upside-only": P["positive"], "two-sided": P["warning"],
        "full-risk": P["negative"], "none": P["text_faint"],
    }
    cols = [("Program","left"),("Participating","left"),("Downside Risk","left"),
            ("Annual Bonus ($M)","right"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, v in enumerate(vbc):
        rb = panel_alt if i % 2 == 0 else bg
        pc = pos if v.participation else P["text_faint"]
        rc = risk_colors.get(v.downside_risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(v.program)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{"yes" if v.participation else "no"}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{rc}">{_html.escape(v.downside_risk)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos if v.annual_bonus_mm else text_dim}">${v.annual_bonus_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _impact_table(impacts) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Quality Lever","left"),("Annual ($M)","right"),("Multi-year ($M)","right"),("EV Impact ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, imp in enumerate(impacts):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(imp.component)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${imp.annual_impact_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${imp.multi_year_impact_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${imp.ev_impact_mm:,.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_quality_scorecard(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    margin = _f("margin", 0.18)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.quality_scorecard import compute_quality_scorecard
    r = compute_quality_scorecard(sector=sector, revenue_mm=revenue, ebitda_margin=margin, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Quality Score", f"{r.overall_score:.0f}", "/100", "") +
        ck_kpi_block("Tier", r.tier.replace("_", " ").title(), "", "") +
        ck_kpi_block("Sector", sector, "", "") +
        ck_kpi_block("Metrics Tracked", str(len(r.metrics)), "", "") +
        ck_kpi_block("HEDIS Measures", str(sum(1 for h in r.hedis if h.applies)), "", "") +
        ck_kpi_block("VBC Programs", str(sum(1 for v in r.vbc_programs if v.participation)), "", "") +
        ck_kpi_block("Annual Q Bonus", f"${r.total_annual_quality_bonus_mm:,.2f}M", "", "") +
        ck_kpi_block("EV Quality Uplift", f"${r.total_ev_uplift_from_quality_mm:,.1f}M", "", "")
    )

    ring_svg = _score_ring_svg(r.overall_score, r.tier)
    metrics_tbl = _metrics_table(r.metrics)
    hedis_tbl = _hedis_table(r.hedis)
    vbc_tbl = _vbc_table(r.vbc_programs)
    impact_tbl = _impact_table(r.value_impacts)

    form = f"""
<form method="GET" action="/quality-scorecard" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin
    <input name="margin" value="{margin}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Mult
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Clinical Quality Scorecard</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      HEDIS, Stars, readmission, VBC participation — with quality-adjusted EBITDA and EV uplift modeling
      for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 2fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Overall Quality Score</div>
      {ring_svg}
      <p style="font-size:10px;color:{text_dim};margin-top:12px;line-height:1.5">
        Composite of HEDIS, readmissions, satisfaction, VBC coverage, and Star ratings vs sector benchmarks.
      </p>
    </div>
    <div style="{cell}">
      <div style="{h3}">Quality Metric Detail</div>
      {metrics_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">HEDIS Measure Performance ({sum(1 for h in r.hedis if h.applies)} applicable of {len(r.hedis)} tracked)</div>
    {hedis_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Value-Based Care Program Participation</div>
    {vbc_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Quality-Adjusted Value Creation Levers</div>
    {impact_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Quality Thesis:</strong>
    Current score {r.overall_score:.0f} ({r.tier.replace("_", " ")}). Total annual VBC quality bonus
    opportunity ${r.total_annual_quality_bonus_mm:,.2f}M, with ${r.total_ev_uplift_from_quality_mm:,.1f}M
    of EV uplift from closing quality gaps. Quality is directly monetizable in MA, MSSP, and commercial P4P.
  </div>

</div>"""

    return chartis_shell(body, "Quality Scorecard", active_nav="/quality-scorecard")
