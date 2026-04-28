"""Provider Retention page — /provider-retention."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _cohort_svg(cohorts) -> str:
    if not cohorts: return ""
    w = 540; row_h = 30
    h = len(cohorts) * row_h + 30
    pad_l = 190; pad_r = 90
    inner_w = w - pad_l - pad_r
    max_churn = max(c.turnover_12mo_pct for c in cohorts) or 1
    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    sev_colors = {"critical": P["negative"], "high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    bars = []
    for i, c in enumerate(cohorts):
        y = 25 + i * row_h
        bh = 16
        bw = c.turnover_12mo_pct / max_churn * inner_w
        color = sev_colors.get(c.severity, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 2}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(c.role[:22])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 2}" fill="{P["text_dim"]}" font-size="10" font-family="JetBrains Mono,monospace">{c.turnover_12mo_pct * 100:.1f}% · {c.expected_departures} dep.</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Turnover Rate by Role</text></svg>')


def _roi_svg(levers) -> str:
    if not levers: return ""
    sorted_l = sorted(levers, key=lambda l: -l.roi_multiple)
    w = 540; row_h = 22
    h = len(sorted_l) * row_h + 30
    pad_l = 240; pad_r = 80
    inner_w = w - pad_l - pad_r
    max_v = max(l.roi_multiple for l in sorted_l) or 1
    bg = P["panel"]; pos = P["positive"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    prio_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    bars = []
    for i, l in enumerate(sorted_l):
        y = 20 + i * row_h
        bh = 12
        bw = min(l.roi_multiple / max_v, 1) * inner_w
        pc = prio_colors.get(l.priority, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(l.lever[:34])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{pos}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" font-family="JetBrains Mono,monospace">{l.roi_multiple:.1f}x</text>'
            f'<text x="{w - 4}" y="{y + bh - 1}" fill="{pc}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace">{l.priority}</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Retention Lever ROI</text></svg>')


def _cohort_table(cohorts) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    sev_colors = {"critical": P["negative"], "high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Role","left"),("Headcount","right"),("Turnover %","right"),("Expected Dep","right"),("Replacement Cost ($M)","right"),("Revenue/Provider ($M)","right"),("Lost Revenue ($M)","right"),("Severity","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(cohorts):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_colors.get(c.severity, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.headcount}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sc};font-weight:600">{c.turnover_12mo_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">{c.expected_departures}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${c.replacement_cost_per_dept_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.annual_revenue_per_provider_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]};font-weight:600">${c.annual_lost_revenue_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{c.severity}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _drivers_table(drivers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    trend_colors = {"rising": P["negative"], "stable": P["accent"], "declining": P["positive"]}
    cols = [("Driver","left"),("Contribution %","right"),("Trend","left"),("Addressable","left"),("Fix Timeline","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(drivers):
        rb = panel_alt if i % 2 == 0 else bg
        tc = trend_colors.get(d.trend, text_dim)
        addr_c = P["positive"] if d.addressable else P["text_faint"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.driver)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.contribution_pct * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{d.trend}</span></td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{addr_c};border:1px solid {addr_c};border-radius:2px">{"yes" if d.addressable else "no"}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.typical_fix_timeline)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _at_risk_table(at_risk) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("ID","left"),("Role","left"),("Tenure (yr)","right"),("wRVU %ile","right"),("Rev Contribution ($M)","right"),("Retention Score","right"),("Flight-Risk Factors","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(at_risk):
        rb = panel_alt if i % 2 == 0 else bg
        score_c = P["positive"] if p.retention_score >= 70 else (P["warning"] if p.retention_score >= 45 else P["negative"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(p.anon_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.tenure_yrs:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.wrvu_pctile}th</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${p.revenue_contribution_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{score_c};font-weight:600">{p.retention_score}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.flight_risk_factors)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _levers_table(levers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    prio_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Lever","left"),("One-Time Cost ($M)","right"),("Annual Cost ($M)","right"),("Retention Lift","right"),("Addressable HC","right"),("Retained Rev ($M)","right"),("ROI","right"),("Priority","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, l in enumerate(levers):
        rb = panel_alt if i % 2 == 0 else bg
        pc = prio_colors.get(l.priority, text_dim)
        roi_c = pos if l.roi_multiple >= 2 else (P["accent"] if l.roi_multiple >= 1 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(l.lever)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${l.one_time_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${l.annual_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">+{l.retention_lift_pp * 100:.1f}pp</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{l.addressable_headcount}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${l.expected_retained_revenue_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{roi_c};font-weight:600">{l.roi_multiple:.1f}x</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{l.priority}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _succession_table(succession) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    gap_colors = {"critical": P["negative"], "high": P["negative"], "medium": P["warning"], "low": P["positive"]}
    succ_colors = {"yes": P["positive"], "developing": P["warning"], "no": P["negative"]}
    cols = [("Role","left"),("Current Tenure (yr)","right"),("Successor","left"),("Gap Severity","left"),("Readiness %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(succession):
        rb = panel_alt if i % 2 == 0 else bg
        gc = gap_colors.get(s.gap_severity, text_dim)
        sc = succ_colors.get(s.successor_identified, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.current_holder_tenure_yrs:.1f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.successor_identified)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{gc};border:1px solid {gc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{s.gap_severity}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gc};font-weight:600">{s.readiness_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_provider_retention(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    providers = _i("providers", 250)
    revenue = _f("revenue", 80.0)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.provider_retention import compute_provider_retention
    r = compute_provider_retention(sector=sector, total_providers=providers, revenue_mm=revenue, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total Providers", f"{r.total_providers:,}", "", "") +
        ck_kpi_block("Turnover %", f"{r.overall_turnover_pct * 100:.1f}%", "12mo", "") +
        ck_kpi_block("Expected Departures", str(r.expected_12mo_departures), "", "") +
        ck_kpi_block("Cost of Churn", f"${r.cost_of_churn_mm:,.1f}M", "", "") +
        ck_kpi_block("Cost / Departure", f"${r.cost_per_departure_k:,.0f}K", "", "") +
        ck_kpi_block("Retention Investment", f"${r.total_retention_investment_mm:,.1f}M", "", "") +
        ck_kpi_block("Retained Revenue", f"${r.total_savings_from_retention_mm:,.1f}M", "", "") +
        ck_kpi_block("EV Impact", f"${r.ev_impact_mm:,.0f}M", "", "")
    )

    cohort_svg = _cohort_svg(r.cohorts)
    roi_svg = _roi_svg(r.levers)
    cohort_tbl = _cohort_table(r.cohorts)
    driver_tbl = _drivers_table(r.drivers)
    risk_tbl = _at_risk_table(r.at_risk)
    lever_tbl = _levers_table(r.levers)
    succ_tbl = _succession_table(r.succession)

    form = f"""
<form method="GET" action="/provider-retention" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Total Providers
    <input name="providers" value="{providers}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
    <input name="mult" value="{mult}" type="number" step="0.5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Provider Retention / Churn Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Churn cohorts, driver diagnosis, at-risk individuals, retention levers, succession — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}"><div style="{h3}">Turnover by Role</div>{cohort_svg}</div>
    <div style="{cell}"><div style="{h3}">Lever ROI Ranking</div>{roi_svg}</div>
  </div>
  <div style="{cell}"><div style="{h3}">Cohort Detail</div>{cohort_tbl}</div>
  <div style="{cell}"><div style="{h3}">Churn Driver Diagnosis</div>{driver_tbl}</div>
  <div style="{cell}"><div style="{h3}">At-Risk Provider Watchlist (Top 10)</div>{risk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Retention Lever Portfolio</div>{lever_tbl}</div>
  <div style="{cell}"><div style="{h3}">Leadership Succession Readiness</div>{succ_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {P['negative']};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Retention Thesis:</strong> {r.overall_turnover_pct * 100:.1f}% overall churn costs ${r.cost_of_churn_mm:,.1f}M annually
    (~${r.cost_per_departure_k:,.0f}K per departure). ${r.total_retention_investment_mm:,.1f}M investment in high-priority
    levers retains ${r.total_savings_from_retention_mm:,.1f}M of revenue → ${r.ev_impact_mm:,.0f}M EV impact at exit.
  </div>
</div>"""

    return chartis_shell(body, "Provider Retention", active_nav="/provider-retention")
