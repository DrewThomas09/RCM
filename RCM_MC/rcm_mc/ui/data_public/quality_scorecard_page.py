"""Clinical Quality Scorecard page — /quality-scorecard.

HEDIS, Stars, readmission, VBC participation with quality-adjusted EBITDA.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row, ck_value_anchor, ck_illustrative_note


def _impact_chart(items):
    """Summary chart — quality levers by EV impact (all positive value drivers)."""
    def _tone(p):
        if p.ev_impact_mm >= 5.0: return "positive"
        if p.ev_impact_mm >= 1.0: return "teal"
        return "navy"
    top = sorted(items, key=lambda p: p.ev_impact_mm, reverse=True)
    total = sum(p.ev_impact_mm for p in top) or 1.0
    rows = [ck_bar_row(f"{p.component}",
            f"${p.ev_impact_mm:,.1f}M EV · ${p.annual_impact_mm:,.1f}M/yr",
            p.ev_impact_mm / total * 100.0, tone=_tone(p)) for p in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of EV impact from quality levers '
            '· value = EV impact ($M) + annual · tone = EV magnitude</div></div>')


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
            f'{ck_data_cell(f"""{_html.escape(m.metric)}""", mono=True)}',
            f'{ck_data_cell(f"""{m.value:.2f}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.unit)}</td>',
            f'{ck_data_cell(f"""{m.benchmark:.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sc};font-weight:600">{m.percentile:.0f}th</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.status.replace("_", " "))}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
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
            f'{ck_data_cell(f"""{_html.escape(h.code)}""", mono=True)}',
            f'{ck_data_cell(f"""{_html.escape(h.name)}""", tone="dim")}',
            f'{ck_data_cell(f"""{h.current_rate * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{h.benchmark * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gc};font-weight:600">{h.gap_pct * 100:+.1f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{applies_c};border:1px solid {applies_c};border-radius:2px;letter-spacing:0.06em">{"yes" if h.applies else "no"}</span>""")}',
            f'{ck_data_cell(f"""{h.est_patients_affected:,}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
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
            f'{ck_data_cell(f"""{_html.escape(v.program)}""", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{"yes" if v.participation else "no"}</span>""")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{rc}">{_html.escape(v.downside_risk)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos if v.annual_bonus_mm else text_dim}">${v.annual_bonus_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.notes)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
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
            f'{ck_data_cell(f"""{_html.escape(imp.component)}""", mono=True)}',
            f'{ck_data_cell(f"""${imp.annual_impact_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${imp.multi_year_impact_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${imp.ev_impact_mm:,.1f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
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
    impact_chart = _impact_chart(r.value_impacts)

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

    page_title = ck_page_title(
        "Clinical Quality Scorecard",
        eyebrow="QUALITY SCORECARD",
        meta=f"""HEDIS, Stars, readmission, VBC participation — with quality-adjusted EBITDA and EV uplift modeling for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals""",
    )
    
    # Lead takeaway — surface the computed quality value (overall score
    # → EV uplift from quality), otherwise buried as KPIs #1/#8 and in
    # the bottom thesis. All figures come from compute_quality_scorecard().
    lead_anchor = ck_value_anchor(
        "QUALITY VALUE",
        f"{r.overall_score:.0f}/100 quality",
        delta=f"{r.tier.replace('_', ' ').title()} tier",
        opportunity=f"${r.total_ev_uplift_from_quality_mm:,.1f}M EV uplift",
        target=f"${r.total_annual_quality_bonus_mm:,.2f}M annual bonus",
        tone="teal",
    )

    body = f"""
<div class="ck-page-wrap">

  {page_title}

  {ck_illustrative_note("quality figures")}
  {lead_anchor}

  {form}

  <div class="ck-kpi-grid" style="margin-bottom:20px">
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
    {impact_chart}{impact_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Quality Thesis:</strong>
    Current score {r.overall_score:.0f} ({r.tier.replace("_", " ")}). Total annual VBC quality bonus
    opportunity ${r.total_annual_quality_bonus_mm:,.2f}M, with ${r.total_ev_uplift_from_quality_mm:,.1f}M
    of EV uplift from closing quality gaps. Quality is directly monetizable in MA, MSSP, and commercial P4P.
  </div>

</div>"""

    return chartis_shell(body, "Quality Scorecard", active_nav="/quality-scorecard",
        editorial_intro={
            "eyebrow": "QUALITY SCORECARD",
            "headline": "What the quality scorecard page reveals on this deal.",
            "italic_word": "reveals",
        })
