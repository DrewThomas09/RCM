"""Clinical Outcomes page — /clinical-outcomes.

Star progression, readmission, complications, VBC contracts, quality ROI.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row


def _roi_chart(items):
    """Summary chart — quality initiatives by EV impact (tone by payback)."""
    def _tone(r):
        if r.payback_months <= 12: return "positive"
        if r.payback_months <= 24: return "teal"
        return "warning"
    top = sorted(items, key=lambda r: r.ev_impact_mm, reverse=True)
    total = sum(r.ev_impact_mm for r in top) or 1.0
    rows = [ck_bar_row(f"{r.initiative}",
            f"${r.ev_impact_mm:,.1f}M EV · ${r.annual_benefit_mm:,.1f}M/yr · {r.payback_months:.0f}mo payback",
            r.ev_impact_mm / total * 100.0, tone=_tone(r)) for r in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of EV impact from quality initiatives '
            '· value = EV impact ($M) + annual benefit + payback · tone = payback period</div></div>')

_EXPLAINER_CSS = """
.ck-co-explainer{font-size:13px;line-height:1.6;color:var(--ck-text-dim);
  max-width:720px;margin:0 0 24px}
.ck-co-explainer em{color:var(--ck-text);font-style:italic}
"""


def _star_trajectory_svg(progression) -> str:
    if not progression:
        return f'<div style="padding:20px;color:{P["text_dim"]};font-size:11px">No MA Star trajectory for this sector</div>'
    w, h = 540, 200
    pad_l, pad_r, pad_t, pad_b = 50, 30, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    bg = P["panel"]; pos = P["positive"]; acc = P["accent"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    max_stars = 5.0
    n = len(progression)

    pts = []
    for i, s in enumerate(progression):
        x = pad_l + (i / max(n - 1, 1)) * inner_w
        y = (h - pad_b) - (s.star_rating / max_stars) * inner_h
        pts.append(f"{x:.1f},{y:.1f}")

    line = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2"/>'

    # Threshold lines
    y_35 = (h - pad_b) - (3.5 / max_stars) * inner_h
    y_4 = (h - pad_b) - (4.0 / max_stars) * inner_h
    y_45 = (h - pad_b) - (4.5 / max_stars) * inner_h
    thresholds = (
        f'<line x1="{pad_l}" y1="{y_4:.1f}" x2="{w - pad_r}" y2="{y_4:.1f}" stroke="{pos}" stroke-width="1" stroke-dasharray="4,3"/>'
        f'<text x="{w - pad_r + 2}" y="{y_4 + 3:.1f}" fill="{pos}" font-size="9" font-family="JetBrains Mono,monospace">4.0 — Bonus</text>'
        f'<line x1="{pad_l}" y1="{y_45:.1f}" x2="{w - pad_r}" y2="{y_45:.1f}" stroke="{pos}" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>'
    )

    dots = []
    for i, s in enumerate(progression):
        x = pad_l + (i / max(n - 1, 1)) * inner_w
        y = (h - pad_b) - (s.star_rating / max_stars) * inner_h
        color = pos if s.ma_bonus_eligible else text_faint
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>'
            f'<text x="{x:.1f}" y="{y - 8:.1f}" fill="{P["text"]}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{s.star_rating:.1f}</text>'
            f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Y{s.year}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + thresholds + line + "".join(dots) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">MA Star Rating Trajectory</text>'
        f'</svg>'
    )


def _metrics_table(metrics) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    trend_colors = {"improving": P["positive"], "stable": P["accent"], "declining": P["negative"]}
    cols = [("Metric","left"),("Current","right"),("Benchmark","right"),("Target","right"),
            ("Percentile","right"),("Trend","left"),("Quality Bonus","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(metrics):
        rb = panel_alt if i % 2 == 0 else bg
        tc = trend_colors.get(m.trend, text_dim)
        pct_c = P["positive"] if m.percentile >= 70 else (P["accent"] if m.percentile >= 50 else P["warning"])
        trigger_c = P["positive"] if m.quality_bonus_trigger else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.metric)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{m.current_value:,.2f} {_html.escape(m.unit)}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{m.benchmark:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{m.target:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pct_c};font-weight:600">{m.percentile:.0f}th</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.trend}</span>""")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{trigger_c};border:1px solid {trigger_c};border-radius:2px;letter-spacing:0.06em">{"yes" if m.quality_bonus_trigger else "no"}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _stars_table(stars) -> str:
    if not stars:
        return f'<p style="color:{P["text_dim"]};font-size:11px;padding:12px 0">Sector does not carry MA Star ratings.</p>'
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Year","left"),("Star Rating","right"),("MA Bonus Eligible","left"),
            ("Bonus (bps)","right"),("PMPM Bonus","right"),("Annual Bonus ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(stars):
        rb = panel_alt if i % 2 == 0 else bg
        elig_c = pos if s.ma_bonus_eligible else P["text_faint"]
        cells = [
            f'{ck_data_cell(f"""Year {s.year}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{s.star_rating:.2f}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{elig_c};border:1px solid {elig_c};border-radius:2px;letter-spacing:0.06em">{"yes" if s.ma_bonus_eligible else "no"}</span>""")}',
            f'{ck_data_cell(f"""{s.bonus_bps}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.pmpm_bonus:.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.annual_bonus_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _complications_table(comps) -> str:
    if not comps:
        return f'<p style="color:{P["text_dim"]};font-size:11px;padding:12px 0">Sector is non-procedural.</p>'
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    cols = [("Complication","left"),("Current Rate","right"),("Benchmark","right"),
            ("Cost/Event","right"),("Annual Events","right"),("Annual Cost ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(comps):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.complication)}""", mono=True)}',
            f'{ck_data_cell(f"""{c.current_rate * 100:.2f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{c.benchmark_rate * 100:.2f}%</td>',
            f'{ck_data_cell(f"""${c.avg_cost_per_event:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.annual_events:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.annual_cost_mm:,.2f}""", align="right", mono=True, tone="neg", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _vbc_table(vbc) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    type_colors = {"Upside-only": P["positive"], "Two-sided": P["warning"], "Full risk": P["negative"]}
    cols = [("Payer","left"),("Contract Type","left"),("Covered Lives","right"),
            ("Upside ($M)","right"),("Downside Risk ($M)","right"),("Expected ($M)","right"),("Performance","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, v in enumerate(vbc):
        rb = panel_alt if i % 2 == 0 else bg
        tc = type_colors.get(v.contract_type, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.payer)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(v.contract_type)}</span>""")}',
            f'{ck_data_cell(f"""{v.covered_lives:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${v.upside_quality_pool_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if v.downside_risk_mm else text_dim}">${v.downside_risk_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${v.expected_payout_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.current_performance)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _roi_table(roi) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Initiative","left"),("One-Time Cost ($M)","right"),("Annual Benefit ($M)","right"),
            ("Payback (mo)","right"),("EV Impact ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, r in enumerate(roi):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.initiative)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${r.one_time_cost_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${r.annual_benefit_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{r.payback_months}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${r.ev_impact_mm:,.1f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_clinical_outcomes(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.clinical_outcomes import compute_clinical_outcomes
    r = compute_clinical_outcomes(sector=sector, revenue_mm=revenue, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Composite Score", f"{r.composite_quality_score:.0f}", "/100", "") +
        ck_kpi_block("MA Star Rating", f"{r.ma_star_rating:.1f}" if r.ma_star_rating else "N/A", "", "") +
        ck_kpi_block("Star Bonus Opp.", f"${r.star_bonus_opportunity_mm:,.1f}M", "", "") +
        ck_kpi_block("Readmit Δ", f"{r.readmission_vs_benchmark_bp} bp", "gap", "") +
        ck_kpi_block("Metrics Tracked", str(len(r.metrics)), "", "") +
        ck_kpi_block("VBC Contracts", str(len(r.vbc_contracts)), "", "") +
        ck_kpi_block("Annual Quality Bonus", f"${r.total_annual_quality_bonus_mm:,.2f}M", "", "") +
        ck_kpi_block("EV Impact", f"${r.total_ev_impact_mm:,.0f}M", "", "")
    )

    star_svg = _star_trajectory_svg(r.star_progression)
    metric_tbl = _metrics_table(r.metrics)
    stars_tbl = _stars_table(r.star_progression)
    comp_tbl = _complications_table(r.complications)
    vbc_tbl = _vbc_table(r.vbc_contracts)
    roi_tbl = _roi_table(r.quality_roi)
    roi_chart = _roi_chart(r.quality_roi)

    form = f"""
<form method="GET" action="/clinical-outcomes" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
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

    page_title = ck_page_title(
        "Clinical Outcomes Tracker",
        eyebrow="CLINICAL OUTCOMES",
        meta=f"MA Stars · readmissions · complications · VBC contracts · quality ROI · {_html.escape(sector)} · {r.corpus_deal_count:,} corpus deals",
    )
    co_explainer = (
        '<p class="ck-co-explainer">'
        "<em>What the clinical outcomes page reveals on this deal.</em> "
        "MA Stars trajectory, readmission and complication benchmarks, value-based care contracts, "
        "and quality-initiative ROI — drawn from corpus deal history."
        "</p>"
    )

    body = page_title + co_explainer + f"""
<div class="ck-page-wrap">

  {form}

  <div class="ck-kpi-grid" style="margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="{cell}">
    <div style="{h3}">MA Star Trajectory &amp; Bonus Thresholds</div>
    {star_svg}
  </div>

  <div style="{cell}">
    <div style="{h3}">Outcome Metrics</div>
    {metric_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Star Progression &amp; Bonus Capture</div>
    {stars_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Complication Breakdown &amp; Avoidable Cost</div>
    {comp_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Value-Based Care Contract Portfolio</div>
    {vbc_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Quality Initiative ROI</div>
    {roi_chart}{roi_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Clinical Outcomes Thesis:</strong>
    Composite score {r.composite_quality_score:.0f}/100. {len(r.vbc_contracts)} VBC contracts generate
    ${r.total_annual_quality_bonus_mm:,.2f}M annual quality bonus. Star Rating trajectory
    {r.ma_star_rating:.1f} → projected 4.0+ unlocks MA bonus eligibility. Total quality-driven
    EV uplift ${r.total_ev_impact_mm:,.0f}M — monetizes outcomes into valuation.
  </div>

</div>"""

    return chartis_shell(body, "Clinical Outcomes", active_nav="/clinical-outcomes",
        extra_css=_EXPLAINER_CSS)
