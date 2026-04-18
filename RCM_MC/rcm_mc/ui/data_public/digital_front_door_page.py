"""Digital Front Door / Patient Experience Tracker — /digital-front-door."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _adoption_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("Portal Reg %","right"),("Active 90d %","right"),
            ("Online Sched %","right"),("Mobile App %","right"),("Ambient AI %","right"),("Digital Onboard %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if a.portal_active_90d_pct >= 0.55 else (acc if a.portal_active_90d_pct >= 0.40 else P["warning"])
        s_c = pos if a.online_scheduling_pct >= 0.65 else (acc if a.online_scheduling_pct >= 0.50 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(a.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{a.portal_registration_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{a.portal_active_90d_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{a.online_scheduling_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.mobile_app_adoption_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{a.ambient_ai_visits_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.digital_onboarding_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _experience_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]; neg = P["negative"]
    cols = [("Deal","left"),("NPS","right"),("HCAHPS","right"),("Google Rating","right"),
            ("Review Count","right"),("Complaints/1K","right"),("Response (hr)","right"),("Resolution %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        n_c = pos if e.nps >= 65 else (acc if e.nps >= 55 else (warn if e.nps >= 45 else neg))
        h_c = pos if e.hcahps_composite >= 4.5 else (acc if e.hcahps_composite >= 4.3 else warn)
        g_c = pos if e.google_rating >= 4.5 else (acc if e.google_rating >= 4.3 else warn)
        c_c = warn if e.complaints_per_1k >= 4.0 else (acc if e.complaints_per_1k >= 2.5 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{n_c};font-weight:700">+{e.nps}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{h_c};font-weight:700">{e.hcahps_composite:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{e.google_rating:.2f}★</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.google_reviews_count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{e.complaints_per_1k:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{e.response_time_hours:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{e.resolution_rate_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _telehealth_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Monthly Visits (K)","right"),("% of Total","right"),("Revenue ($M)","right"),
            ("Completion %","right"),("Avg Duration (min)","right"),("Satisfaction","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if t.completion_rate_pct >= 0.90 else (acc if t.completion_rate_pct >= 0.85 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(t.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{t.telehealth_visits_monthly_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{t.pct_of_total_visits * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${t.telehealth_revenue_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{t.completion_rate_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.avg_duration_min:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{t.patient_satisfaction:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _spend_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Category","left"),("Spend ($M)","right"),("YoY Growth","right"),("Vendors","left"),("Typical ROI","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        g_c = pos if s.yoy_growth_pct >= 0.30 else (acc if s.yoy_growth_pct >= 0.15 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.portfolio_spend_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">+{s.yoy_growth_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(s.vendors)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(s.typical_roi)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vendors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vendor","left"),("Category","left"),("Deals","right"),("Users (K)","right"),("Cost ($M)","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if v.status == "live production" else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(v.vendor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(v.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{v.portfolio_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{v.users_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${v.annual_cost_m:.2f}M</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{s_c}">{_html.escape(v.status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _funnel_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Web Visits (K/mo)","right"),("New Patient Inquiries","right"),
            ("Inquiry→Book %","right"),("Book→Visit %","right"),("No-Show %","right"),("Cost per Acquired","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        b_c = pos if f.inquiry_to_booking_pct >= 0.55 else (acc if f.inquiry_to_booking_pct >= 0.45 else P["warning"])
        v_c = pos if f.book_to_visit_pct >= 0.85 else (acc if f.book_to_visit_pct >= 0.78 else P["warning"])
        n_c = pos if f.no_show_rate_pct <= 0.075 else (acc if f.no_show_rate_pct <= 0.10 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{f.web_visits_monthly_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{f.new_patient_inquiries:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">{f.inquiry_to_booking_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:700">{f.book_to_visit_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{n_c};font-weight:700">{f.no_show_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${f.cost_per_acquired:.0f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_digital_front_door(params: dict = None) -> str:
    from rcm_mc.data_public.digital_front_door import compute_digital_front_door
    r = compute_digital_front_door()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Portfolio Cos", str(r.total_portcos), "", "") +
        ck_kpi_block("Active Portal %", f"{r.weighted_portal_adoption_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg NPS", f"+{r.avg_nps}", "", "") +
        ck_kpi_block("Monthly Telehealth", f"{r.total_telehealth_visits_monthly_k:,}K", "", "") +
        ck_kpi_block("Digital Spend", f"${r.total_digital_spend_m:.1f}M", "", "") +
        ck_kpi_block("Google Rating", f"{r.avg_google_rating:.2f}★", "", "") +
        ck_kpi_block("Vendors Live", str(sum(1 for v in r.vendors if v.status == "live production")), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    a_tbl = _adoption_table(r.adoption)
    e_tbl = _experience_table(r.experience)
    t_tbl = _telehealth_table(r.telehealth)
    s_tbl = _spend_table(r.spend)
    v_tbl = _vendors_table(r.vendors)
    f_tbl = _funnel_table(r.funnels)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_th_rev = sum(t.telehealth_revenue_m for t in r.telehealth)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Digital Front Door / Patient Experience Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_portcos} portcos · {r.weighted_portal_adoption_pct * 100:.1f}% active portal · avg NPS +{r.avg_nps} · {r.avg_google_rating:.2f}★ Google · {r.total_telehealth_visits_monthly_k:,}K monthly telehealth visits · ${total_th_rev:.1f}M telehealth revenue — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Digital Channel Adoption</div>{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">Patient Experience Metrics</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Telehealth Utilization</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Digital Spend Categories</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">New Patient Acquisition Funnel</div>{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Vendor Deployment Status</div>{v_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Digital Front Door Summary:</strong> {r.weighted_portal_adoption_pct * 100:.1f}% average active-portal adoption tracks industry benchmark ~50% — Fertility (78%), Derma (58%), Specialty Pharm (65%), Infusion (58%) are top performers.
    Online scheduling at 62% portfolio average — favorable above industry benchmark; consumer-facing specialties (Derma, Fertility, Eye Care) lead adoption, hospital-based / home health lag.
    Average NPS +{r.avg_nps} with Willow (Fertility +72), Laurel (Derma +68), Oak (RCM +62) top performers; Sage (Home Health +45), Linden (Behavioral +48) drag reflects operational / access challenges.
    Telehealth volume: {r.total_telehealth_visits_monthly_k:,}K monthly visits generating ${total_th_rev:.1f}M revenue — behavioral health (Redwood 48%, Linden 52%) and home health (Sage 22%) carry highest share.
    Digital spend ${r.total_digital_spend_m:.1f}M portfolio-wide with ambient AI growing +85% YoY (highest category); Epic MyChart (18.5M spend, 850K users, 10 deals) is the largest single vendor.
    Funnel conversion: inquiry→booking averages 52%, booking→visit 82%, no-show 8.5% — Derma (62% booking, 88% show) best-in-class; Fertility high-consideration patients drive lower initial conversion but higher LTV.
  </div>
</div>"""

    return chartis_shell(body, "Digital Front Door", active_nav="/digital-front-door")
