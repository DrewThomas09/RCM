"""Health Equity / SDOH Scorecard — /health-equity."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title


def _components_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Measure","left"),("Domain","center"),("LIS/Dual","right"),("Non-LIS","right"),
            ("Gap","right"),("Weight","right"),("Points","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        gap_c = pos if abs(c.gap_pct) < 0.08 else (warn if abs(c.gap_pct) < 0.15 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.measure)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.domain)}</td>',
            f'{ck_data_cell(f"""{c.lis_dual_performance * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{c.non_lis_performance * 100:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gap_c};font-weight:700">{c.gap_pct * 100:+.1f}pp</td>',
            f'{ck_data_cell(f"""{c.weight_in_hei * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{c.points_available}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sdoh_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Domain","left"),("Screened","right"),("Positive Screen","right"),("Closed-Loop Referral","right"),
            ("Intervention PMPY","right"),("ROI Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        roi_c = pos if s.roi_score >= 70 else (acc if s.roi_score >= 60 else warn)
        cl_c = pos if s.referral_closed_loop_pct >= 0.50 else (warn if s.referral_closed_loop_pct >= 0.35 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.domain)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.screened_pct * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.positive_screen_pct * 100:.1f}%""", align="right", mono=True, tone="neg")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cl_c};font-weight:700">{s.referral_closed_loop_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${s.intervention_cost_pmpy:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{roi_c};font-weight:700">{s.roi_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _investments_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Initiative","left"),("Category","center"),("Annual Cost ($M)","right"),("Lives Impacted","right"),
            ("Outcome","left"),("HEI Δ","right"),("Star Bonus Impact ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, inv in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(inv.initiative)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(inv.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${inv.annual_cost_mm:,.2f}</td>',
            f'{ck_data_cell(f"""{inv.lives_impacted:,}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(inv.measurable_outcome)}</td>',
            f'{ck_data_cell(f"""+{inv.hei_points_delta:.2f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""${inv.star_bonus_impact_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _demographics_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Segment","left"),("Pop (000)","right"),("Avg RAF","right"),("Preventive Util","right"),
            ("ED/1000","right"),("HEDIS Composite","right"),("Disparity Flag","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ed_c = neg if d.ed_utilization_per_1000 >= 450 else (warn if d.ed_utilization_per_1000 >= 350 else text_dim)
        h_c = pos if d.hedis_composite >= 0.78 else (warn if d.hedis_composite >= 0.70 else neg)
        f_c = neg if d.disparity_flag else pos
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.segment)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{d.population_000:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{d.avg_raf:.2f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{d.preventive_utilization_pct * 100:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ed_c}">{d.ed_utilization_per_1000}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{h_c};font-weight:700">{d.hedis_composite:.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{f_c};font-weight:700">{"YES" if d.disparity_flag else "NO"}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_health_equity(params: dict = None) -> str:
    from rcm_mc.data_public.health_equity import compute_health_equity
    r = compute_health_equity()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Attributed Lives", f"{r.total_attributed_lives:,.0f}", "", "") +
        ck_kpi_block("LIS/Dual %", f"{r.lis_dual_pct * 100:.1f}%", "", "") +
        ck_kpi_block("HEI Score", f"{r.overall_hei_score:.3f}", "", "") +
        ck_kpi_block("HEI Points", f"{r.hei_points_current:.1f}", "", "") +
        ck_kpi_block("Bonus Potential", f"${r.hei_bonus_potential_mm:,.1f}M", "", "") +
        ck_kpi_block("HEI Measures", str(len(r.hei_components)), "", "") +
        ck_kpi_block("SDOH Domains", str(len(r.sdoh)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    c_tbl = _components_table(r.hei_components)
    s_tbl = _sdoh_table(r.sdoh)
    i_tbl = _investments_table(r.investments)
    d_tbl = _demographics_table(r.demographics)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_inv_cost = sum(i.annual_cost_mm for i in r.investments)
    disparity_segments = sum(1 for d in r.demographics if d.disparity_flag)

    page_title = ck_page_title(
        "Health Equity / SDOH Scorecard",
        eyebrow="HEALTH EQUITY",
        meta=f"{r.total_attributed_lives:,.0f} attributed lives ({r.lis_dual_pct * 100:.1f}% LIS/Dual) · HEI score {r.overall_hei_score:.3f} ({r.hei_points_current:.0f} pts) · ${total_inv_cost:,.1f}M equity investment → ${r.hei_bonus_potential_mm:,.1f}M Star bonus potential · {disparity_segments} of {len(r.demographics)} segments flagged for disparity",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">HEI Measure Components — LIS/Dual vs Non-LIS Performance</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">SDOH Screening Completion &amp; Closed-Loop Referral</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Equity Investment Portfolio &amp; ROI</div>{i_tbl}</div>
  <div style="{cell}"><div style="{h3}">Demographic Segment Performance &amp; Disparity Flags</div>{d_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Equity Thesis:</strong> HEI score {r.overall_hei_score:.3f} ({r.hei_points_current:.0f}/100 points).
    LIS/Dual population is {r.lis_dual_pct * 100:.1f}% of book; {disparity_segments} of {len(r.demographics)} demographic segments show measurable disparity.
    Equity investment ${total_inv_cost:,.1f}M yields estimated ${r.hei_bonus_potential_mm:,.1f}M Star bonus impact — positive ROI.
    Diabetes care and osteoporosis management show the widest gaps; transportation and community health worker investments have highest demonstrated ROI.
    CMS 2027 Stars calculation replaces the Reward Factor with HEI — making this scorecard directly tied to MA plan bonus payments and cut points.
  </div>
</div>"""

    return chartis_shell(body, "Health Equity", active_nav="/health-equity",
        editorial_intro={
            "eyebrow": "HEALTH EQUITY",
            "headline": "What the health equity page reveals on this deal.",
            "italic_word": "reveals",
        })
