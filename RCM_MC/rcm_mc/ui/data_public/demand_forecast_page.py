"""Demand Forecast page — /demand-forecast."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _volume_svg(volume) -> str:
    if not volume: return ""
    w, h = 560, 200
    pad_l, pad_r, pad_t, pad_b = 60, 30, 25, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(v.patient_visits_k for v in volume) * 1.1
    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    n = len(volume)
    bar_w = (inner_w - (n - 1) * 4) / n
    bars = []
    for i, v in enumerate(volume):
        x = pad_l + i * (bar_w + 4)
        bh = v.patient_visits_k / max_v * inner_h
        y = (h - pad_b) - bh
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{acc}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{v.year}</text>'
        )
        if i == 0 or i == n - 1:
            bars.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{v.patient_visits_k:,.0f}K</text>')

    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Annual Visit Volume Projection (thousands)</text></svg>')


def _population_svg(pop) -> str:
    if not pop: return ""
    w = 540; row_h = 28
    h = len(pop) * row_h + 30
    pad_l = 80; pad_r = 80
    inner_w = w - pad_l - pad_r
    max_v = max(p.pop_2035_mm for p in pop) or 1
    bg = P["panel"]; acc = P["accent"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    bars = []
    for i, p in enumerate(pop):
        y = 20 + i * row_h
        bh = 16
        # Show 2025 vs 2035 as stacked
        w_25 = p.pop_2025_mm / max_v * inner_w
        w_35 = p.pop_2035_mm / max_v * inner_w
        age_c = P["accent"] if "65" in p.age_band or "75" in p.age_band or "85" in p.age_band else text_faint
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 2}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(p.age_band)}</text>'
            # 2035 background
            f'<rect x="{pad_l}" y="{y}" width="{w_35:.1f}" height="{bh}" fill="{age_c}" opacity="0.35"/>'
            # 2025 foreground
            f'<rect x="{pad_l}" y="{y}" width="{w_25:.1f}" height="{bh}" fill="{age_c}" opacity="0.85"/>'
            f'<text x="{pad_l + w_35 + 4:.1f}" y="{y + bh - 2}" fill="{P["text_dim"]}" font-size="10" font-family="JetBrains Mono,monospace">{p.pop_2035_mm:.1f}M ({p.cagr_5yr * 100:+.1f}%)</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Population by Age Band — 2025 (solid) / 2035 (faded)</text></svg>')


def _population_table(pop) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Age Band","left"),("2025 (M)","right"),("2030 (M)","right"),("2035 (M)","right"),("5-yr CAGR","right"),("Share 2025","right"),("Share 2035","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(pop):
        rb = panel_alt if i % 2 == 0 else bg
        cagr_c = P["positive"] if p.cagr_5yr >= 0.03 else P["accent"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.age_band)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.pop_2025_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.pop_2030_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{p.pop_2035_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cagr_c}">{p.cagr_5yr * 100:+.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.share_2025 * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.share_2035 * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _util_table(util) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Year","left"),("Total Pop (M)","right"),("Expected Visits (M)","right"),("vs 2025 Baseline","right"),("Medicare Share","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, u in enumerate(util):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{u.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{u.total_pop_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{u.expected_visits_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{u.pct_vs_baseline * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{u.medicare_share_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _disease_table(disease) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Disease","left"),("Prevalence 2025","right"),("Prevalence 2035","right"),("Patients 2025 (M)","right"),("Patients 2035 (M)","right"),("10-yr CAGR","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(disease):
        rb = panel_alt if i % 2 == 0 else bg
        cagr_c = P["positive"] if d.cagr_10yr >= 0.02 else P["accent"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.disease)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.prevalence_2025_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{d.prevalence_2035_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.patients_2025_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{d.patients_2035_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cagr_c}">{d.cagr_10yr * 100:+.2f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _volume_table(vol) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Year","left"),("Patient Visits (K)","right"),("Growth vs PY","right"),("Medicare Share","right"),("Commercial Share","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(vol):
        rb = panel_alt if i % 2 == 0 else bg
        gc = P["positive"] if v.growth_vs_py > 0 else P["text_faint"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{v.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.patient_visits_k:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gc}">{v.growth_vs_py * 100:+.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{v.medicare_share * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.commercial_share * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _opps_table(opps) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    feas_colors = {"high": pos, "medium": P["accent"], "low": P["warning"]}
    cols = [("Opportunity","left"),("Addressable Pop (M)","right"),("Current Pen.","right"),("Target Pen.","right"),("Revenue Opp ($M)","right"),("Feasibility","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(opps):
        rb = panel_alt if i % 2 == 0 else bg
        fc = feas_colors.get(o.feasibility, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.opportunity)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{o.addressable_pop_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.current_penetration * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{o.target_penetration * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${o.revenue_opportunity_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{fc};border:1px solid {fc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{o.feasibility}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_demand_forecast(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Primary Care") or "Primary Care"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    visits = _f("visits", 380.0)
    revenue = _f("revenue", 80.0)

    from rcm_mc.data_public.demand_forecast import compute_demand_forecast
    r = compute_demand_forecast(sector=sector, baseline_visits_k=visits, revenue_mm=revenue)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("US Pop 2025", f"{r.baseline_market_mm:,.0f}M", "", "") +
        ck_kpi_block("10-yr CAGR", f"{r.ten_yr_cagr * 100:.2f}%", "visits", "") +
        ck_kpi_block("Aging Tailwind", f"+{r.aging_tailwind_pct * 100:.1f}%", "", "") +
        ck_kpi_block("MA Share 2025", f"{r.medicare_share_2025 * 100:.1f}%", "", "") +
        ck_kpi_block("MA Share 2035", f"{r.medicare_share_2035 * 100:.1f}%", "", "") +
        ck_kpi_block("Age Bands", str(len(r.population)), "", "") +
        ck_kpi_block("Diseases Tracked", str(len(r.disease)), "", "") +
        ck_kpi_block("Growth Opps", str(len(r.opportunities)), "", "")
    )

    vol_svg = _volume_svg(r.volume_forecast)
    pop_svg = _population_svg(r.population)
    pop_tbl = _population_table(r.population)
    util_tbl = _util_table(r.utilization)
    dis_tbl = _disease_table(r.disease)
    vol_tbl = _volume_table(r.volume_forecast)
    opps_tbl = _opps_table(r.opportunities)

    form = f"""
<form method="GET" action="/demand-forecast" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:180px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Baseline Visits (K)
    <input name="visits" value="{visits}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Demand Forecaster</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Demographic-driven 10-year utilization projections for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}"><div style="{h3}">10-Year Volume Projection</div>{vol_svg}</div>
    <div style="{cell}"><div style="{h3}">Population by Age Band</div>{pop_svg}</div>
  </div>
  <div style="{cell}"><div style="{h3}">US Population Projection</div>{pop_tbl}</div>
  <div style="{cell}"><div style="{h3}">Utilization Demand Model ({_html.escape(sector)})</div>{util_tbl}</div>
  <div style="{cell}"><div style="{h3}">Disease Prevalence — 2025 vs 2035</div>{dis_tbl}</div>
  <div style="{cell}"><div style="{h3}">Patient Visit Volume Forecast</div>{vol_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Growth Opportunities</div>{opps_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Demand Thesis:</strong> Demographic aging drives {r.ten_yr_cagr * 100:.2f}% 10-year visit CAGR,
    +{r.aging_tailwind_pct * 100:.1f}% cumulative. Medicare share climbs from {r.medicare_share_2025 * 100:.1f}% to {r.medicare_share_2035 * 100:.1f}%.
    Senior care, chronic disease, and behavioral health open material white-space opportunities.
  </div>
</div>"""

    return chartis_shell(body, "Demand Forecast", active_nav="/demand-forecast")
