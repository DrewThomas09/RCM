"""Clinical Trial Site Economics — /trial-site-econ."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell


def _sites_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Site ID","left"),("Therapeutic Area","left"),("Active Trials","right"),
            ("Screens","right"),("Enrollment Rate","right"),("Revenue ($M)","right"),
            ("Op Margin","right"),("ROI / Study ($k)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items[:30]):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if s.operating_margin_pct >= 0.25 else (acc if s.operating_margin_pct >= 0.20 else warn)
        r_c = pos if s.enrollment_rate_pct >= 0.08 else (acc if s.enrollment_rate_pct >= 0.05 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.site_id)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(s.therapeutic_area)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.active_trials}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.patient_screen_volume:,}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{s.enrollment_rate_pct * 100:.2f}%</td>',
            f'{ck_data_cell(f"""${s.annual_revenue_mm:,.2f}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{s.operating_margin_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${s.roi_per_study_k:,.1f}""", align="right", mono=True, tone="pos")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tas_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Therapeutic Area","left"),("Sites","right"),("Active Trials","right"),
            ("Med Revenue / Site ($M)","right"),("Med Enrollment Rate","right"),("Growth","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    grow_c = {"accelerating": pos, "accelerating (GLP-1)": pos, "accelerating (psychedelics)": pos, "stable": text_dim}
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gc = grow_c.get(t.growth_trajectory, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.area)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{t.site_count}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{t.active_trials}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${t.median_revenue_per_site_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{t.median_enrollment_rate_pct * 100:.2f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{gc};border:1px solid {gc};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.growth_trajectory)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _phase_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Phase","left"),("Site Payment ($k)","right"),("Patients/Site","right"),
            ("Duration (mo)","right"),("Total Revenue ($k)","right"),("Typical Margin","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if p.typical_margin_pct >= 0.24 else acc
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.phase)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${p.avg_site_payment_k:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.avg_patients_per_site}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{p.avg_trial_duration_months}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.avg_total_revenue_k:,.0f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{p.typical_margin_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sponsors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Sponsor","left"),("Type","left"),("Active Trials","right"),("Completed LTM","right"),
            ("Avg Fee ($k)","right"),("On-Time","right"),("Engagement","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    eng_c = {"repeat": pos, "growing": acc, "pass-through": text_dim}
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ec = eng_c.get(s.repeat_engagement, text_dim)
        on_c = pos if s.on_time_delivery_pct >= 0.85 else (warn if s.on_time_delivery_pct >= 0.75 else P["negative"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.sponsor)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(s.sponsor_type)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.active_trials}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{s.trials_completed_ltm}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${s.avg_per_study_fee_k:,.0f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{on_c};font-weight:600">{s.on_time_delivery_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ec};border:1px solid {ec};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.repeat_engagement)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cost_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Category","left"),("% of Revenue","right"),("Annual Cost ($M)","right"),("Trend","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = neg if "rising" in c.trend else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.pct_of_revenue * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.annual_cost_mm:,.2f}""", align="right", mono=True, tone="neg", weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{tc}">{_html.escape(c.trend)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_trial_site_econ(params: dict = None) -> str:
    from rcm_mc.data_public.trial_site_econ import compute_trial_site_econ
    r = compute_trial_site_econ()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Total Sites", str(r.total_sites), "", "") +
        ck_kpi_block("Active Trials", str(r.total_active_trials), "", "") +
        ck_kpi_block("Annual Revenue", f"${r.annual_revenue_mm:,.2f}M", "", "") +
        ck_kpi_block("Blended Margin", f"{r.blended_margin_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Enrollment", f"{r.avg_enrollment_rate_pct * 100:.2f}%", "", "") +
        ck_kpi_block("Therapeutic Areas", str(len(r.therapeutic_areas)), "", "") +
        ck_kpi_block("Active Sponsors", str(len(r.sponsors)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    s_tbl = _sites_table(r.sites)
    ta_tbl = _tas_table(r.therapeutic_areas)
    p_tbl = _phase_table(r.phase_econ)
    sp_tbl = _sponsors_table(r.sponsors)
    c_tbl = _cost_table(r.cost_structure)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Clinical Trial Site Economics</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Site-level P&amp;L · therapeutic area mix · phase economics · sponsor relationship · cost structure — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Site Roster (Top 30 by Revenue)</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Therapeutic Area Rollup</div>{ta_tbl}</div>
  <div style="{cell}"><div style="{h3}">Phase Economics — Per-Site Revenue &amp; Margin</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sponsor Relationship Matrix</div>{sp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Cost Structure</div>{c_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Trial Site Thesis:</strong> {r.total_sites} sites running {r.total_active_trials} active trials at ${r.annual_revenue_mm:,.2f}M revenue, {r.blended_margin_pct * 100:.1f}% operating margin.
    Oncology and rare-disease therapeutic areas lead on revenue-per-site and enrollment rate; metabolic (GLP-1) and CNS (psychedelics) are fastest-growing. Phase IV and DCT drive highest margins at {max(p.typical_margin_pct for p in r.phase_econ) * 100:.0f}%.
    Large pharma direct relationships (Pfizer, Merck, Lilly) generate highest per-study fees; CRO pass-through adds volume but lower margin.
    Rising wage pressure on CRC/physician investigators and recruitment cost compression are the material operating headwinds to monitor.
  </div>
</div>"""

    return chartis_shell(body, "Trial Site Econ", active_nav="/trial-site-econ",
        editorial_intro={
            "eyebrow": "TRIAL SITE ECON",
            "headline": "What the trial site econ page reveals on this deal.",
            "italic_word": "reveals",
        })
