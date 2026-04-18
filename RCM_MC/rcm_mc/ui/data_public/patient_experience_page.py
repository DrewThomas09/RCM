"""Patient Experience page — /patient-experience."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _nps_gauge_svg(nps: int) -> str:
    w, h = 260, 160
    cx, cy = w / 2, h - 30
    r = 90
    import math
    bg = P["panel"]
    # -100 to 100 scale, map to 180° arc
    # Bands: -100..0 red, 0..30 amber, 30..70 accent, 70..100 green
    def _arc(start, end, color):
        sr = math.radians(180 - ((start + 100) / 200 * 180))
        er = math.radians(180 - ((end + 100) / 200 * 180))
        x1 = cx + r * math.cos(sr); y1 = cy - r * math.sin(sr)
        x2 = cx + r * math.cos(er); y2 = cy - r * math.sin(er)
        return (f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 0 0 {x2:.1f} {y2:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="13" opacity="0.9"/>')

    bands = _arc(-100, 0, P["negative"]) + _arc(0, 30, P["warning"]) + _arc(30, 70, P["accent"]) + _arc(70, 100, P["positive"])

    # Needle
    angle_deg = 180 - ((nps + 100) / 200 * 180)
    ar = math.radians(angle_deg)
    nx = cx + (r - 18) * math.cos(ar); ny = cy - (r - 18) * math.sin(ar)
    needle = (f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" '
              f'stroke="{P["text"]}" stroke-width="3" stroke-linecap="round"/>'
              f'<circle cx="{cx}" cy="{cy}" r="5" fill="{P["text"]}"/>')

    color = P["positive"] if nps >= 70 else (P["accent"] if nps >= 30 else (P["warning"] if nps >= 0 else P["negative"]))
    label = "WORLD-CLASS" if nps >= 70 else ("STRONG" if nps >= 30 else ("MEDIOCRE" if nps >= 0 else "POOR"))

    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>'
            + bands + needle +
            f'<text x="{cx}" y="{cy - 22}" text-anchor="middle" fill="{P["text"]}" font-size="26" font-weight="700" font-family="JetBrains Mono,monospace">{nps}</text>'
            f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" fill="{color}" font-size="10" font-weight="600" letter-spacing="0.1em" font-family="Inter,sans-serif">{label}</text>'
            f'<text x="10" y="{h - 5}" fill="{P["text_faint"]}" font-size="9" font-family="JetBrains Mono,monospace">-100</text>'
            f'<text x="{w - 28}" y="{h - 5}" fill="{P["text_faint"]}" font-size="9" font-family="JetBrains Mono,monospace">+100</text>'
            f'</svg>')


def _review_stars_svg(reviews) -> str:
    if not reviews: return ""
    w = 540
    row_h = 26
    h = len(reviews) * row_h + 30
    pad_l = 150
    inner_w = w - pad_l - 100
    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    bars = []
    for i, r in enumerate(reviews):
        y = 20 + i * row_h
        bh = 14
        bw = r.avg_rating / 5.0 * inner_w
        color = P["positive"] if r.avg_rating >= 4.5 else (P["accent"] if r.avg_rating >= 4.0 else P["warning"])
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(r.platform[:22])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" font-family="JetBrains Mono,monospace">{r.avg_rating:.2f} ({r.volume_total:,} rev)</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>'
            + "".join(bars) +
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Avg Rating by Platform</text></svg>')


def _metrics_table(metrics) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    trend_colors = {"up": P["positive"], "flat": P["accent"], "down": P["negative"]}
    cols = [("Category","left"),("Metric","left"),("Current","right"),("Benchmark","right"),("Percentile","right"),("Trend","left"),("Rev Corr","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(metrics):
        rb = panel_alt if i % 2 == 0 else bg
        tc = trend_colors.get(m.trend_90d, text_dim)
        pct_c = P["positive"] if m.percentile >= 70 else (P["accent"] if m.percentile >= 50 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{m.current_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.benchmark:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pct_c};font-weight:600">{m.percentile}th</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.trend_90d}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{m.revenue_correlation:+.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _reviews_table(reviews) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Platform","left"),("Total Volume","right"),("Avg Rating","right"),("Last 90d Volume","right"),("90d Rating","right"),("Positive Sentiment %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(reviews):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = P["positive"] if r.avg_rating >= 4.3 else (P["accent"] if r.avg_rating >= 3.8 else P["warning"])
        r90_c = P["positive"] if r.recent_rating_90d >= r.avg_rating else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.platform)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.volume_total:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:600">{r.avg_rating:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.volume_last_90d:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r90_c}">{r.recent_rating_90d:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{r.sentiment_positive_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _drivers_table(drivers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Driver","left"),("Current","right"),("Unit","left"),("Benchmark","right"),("Impact on Experience","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(drivers):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(d.driver)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.current_value:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{d.benchmark:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{d.impact_on_experience_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _initiatives_table(initiatives) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    risk_colors = {"low": pos, "medium": P["warning"], "high": P["negative"]}
    cols = [("Initiative","left"),("Investment ($M)","right"),("NPS Δ","right"),("Retention Δ","right"),("Revenue Uplift ($M)","right"),("Timeline (mo)","right"),("Risk","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, init in enumerate(initiatives):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(init.risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(init.initiative)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${init.investment_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">+{init.expected_nps_delta:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">+{init.expected_retention_delta_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${init.expected_revenue_uplift_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{init.timeline_months}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{init.risk}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _retention_table(retention) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Cohort","left"),("Current Retention","right"),("Target","right"),("Implied Revenue Uplift ($M)","right"),("EV Impact ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(retention):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.cohort)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.current_retention_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{r.target_retention_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${r.implied_revenue_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${r.implied_ev_impact_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_patient_experience(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.patient_experience import compute_patient_experience
    r = compute_patient_experience(sector=sector, revenue_mm=revenue, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("PEX Composite", f"{r.composite_pex_score}/100", "", "") +
        ck_kpi_block("NPS", str(r.nps_current), "", "") +
        ck_kpi_block("NPS Trend", r.nps_trajectory, "", "") +
        ck_kpi_block("HCAHPS Top-Box", f"{r.hcahps_top_box_pct:.1f}%", "", "") +
        ck_kpi_block("Google Rating", f"{r.google_review_rating:.2f}", "stars", "") +
        ck_kpi_block("Revenue at Risk", f"${r.total_revenue_at_risk_mm:,.1f}M", "", "") +
        ck_kpi_block("EV Uplift Opp", f"${r.total_ev_impact_from_improvement_mm:,.0f}M", "", "") +
        ck_kpi_block("Initiatives", str(len(r.initiatives)), "", "")
    )

    nps_svg = _nps_gauge_svg(r.nps_current)
    review_svg = _review_stars_svg(r.reviews)
    metric_tbl = _metrics_table(r.metrics)
    review_tbl = _reviews_table(r.reviews)
    driver_tbl = _drivers_table(r.drivers)
    init_tbl = _initiatives_table(r.initiatives)
    ret_tbl = _retention_table(r.retention)

    form = f"""
<form method="GET" action="/patient-experience" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
    <input name="mult" value="{mult}" type="number" step="0.5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Patient Experience / NPS Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">HCAHPS, Press Ganey, NPS, online reviews, retention drivers — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="display:grid;grid-template-columns:1fr 2fr;gap:16px;margin-bottom:16px">
    <div style="{cell}"><div style="{h3}">NPS Position</div>{nps_svg}</div>
    <div style="{cell}"><div style="{h3}">Review Platform Ratings</div>{review_svg}</div>
  </div>
  <div style="{cell}"><div style="{h3}">Experience Metrics Detail</div>{metric_tbl}</div>
  <div style="{cell}"><div style="{h3}">Online Review Platforms</div>{review_tbl}</div>
  <div style="{cell}"><div style="{h3}">Operational Drivers</div>{driver_tbl}</div>
  <div style="{cell}"><div style="{h3}">Experience Initiative Portfolio</div>{init_tbl}</div>
  <div style="{cell}"><div style="{h3}">Retention Cohort Opportunities</div>{ret_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Experience Thesis:</strong> Composite {r.composite_pex_score}/100, NPS {r.nps_current} ({r.nps_trajectory}).
    Online reputation strong (Google {r.google_review_rating:.2f}); HCAHPS top-box {r.hcahps_top_box_pct:.1f}% at 68th percentile.
    Current ${r.total_revenue_at_risk_mm:,.1f}M at risk from detractors. Total EV uplift from initiatives + retention:
    ${r.total_ev_impact_from_improvement_mm:,.0f}M.
  </div>
</div>"""

    return chartis_shell(body, "Patient Experience", active_nav="/patient-experience")
