"""Diligence Vendor Directory — /diligence-vendors."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row, ck_value_anchor, ck_scatter


def _scorecards_scatter(items):
    """Quadrant — value-for-money vs quality-of-insights, so the best
    vendors (upper-right) and weak ones (lower-left) separate visually."""
    import statistics
    pts, xs, ys = [], [], []
    for s in items:
        tn = ('positive' if s.quality_of_insights >= 88 else 'teal' if s.quality_of_insights >= 80 else 'warning')
        pts.append((s.value_for_money, s.quality_of_insights, s.firm, tn))
        xs.append(s.value_for_money); ys.append(s.quality_of_insights)
    return ck_scatter(
        pts, x_label='Value for money', y_label='Quality of insights',
        x_ref=(statistics.median(xs) if xs else None), y_ref=(statistics.median(ys) if ys else None),
        caption='Each dot = a vendor · upper-right = high quality + high value · tone = quality of insights',
    )


def _vendors_chart(items) -> str:
    """Lead chart — panel vendors ranked by deal engagements (tone by tier)."""
    def _tone(v):
        return {"Tier 1": "positive", "Tier 2": "teal", "Tier 3": "navy"}.get(v.tier, "navy")
    top = sorted(items, key=lambda v: v.deals_last_24mo, reverse=True)[:14]
    total = sum(v.deals_last_24mo for v in top) or 1
    rows = [ck_bar_row(f"{v.firm} · {v.category}", f"{v.deals_last_24mo} deals",
            v.deals_last_24mo / total * 100.0, tone=_tone(v)) for v in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of top-14 deal engagements (LTM) '
            '· value = engagements · tone = vendor tier</div></div>')


def _vendors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Firm","left"),("Category","left"),("Tier","center"),("Deals LTM","right"),
            ("Median Spend ($k)","right"),("Turnaround (days)","right"),("NPS","right"),("Quality","right"),("Partner Contact","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    t_c = {"Tier 1": pos, "Tier 2": acc, "Tier 3": text_dim}
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = t_c.get(v.tier, text_dim)
        q_c = pos if v.quality_score >= 88 else (acc if v.quality_score >= 82 else text_dim)
        nps_c = pos if v.nps_from_deal_teams >= 82 else (acc if v.nps_from_deal_teams >= 75 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.firm)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(v.category)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(v.tier)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{v.deals_last_24mo}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${v.median_spend_per_deal_k:,.1f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{v.turnaround_days}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{nps_c};font-weight:700">{v.nps_from_deal_teams}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{q_c};font-weight:700">{v.quality_score}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(v.partner_contact)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _categories_chart(items) -> str:
    """Summary chart — vendor categories ranked by spend (tone by concentration)."""
    def _tone(c):
        if c.concentration_pct > 0.50: return "warning"
        if c.concentration_pct > 0.35: return "teal"
        return "navy"
    top = sorted(items, key=lambda c: c.total_spend_mm, reverse=True)
    total = sum(c.total_spend_mm for c in top) or 1.0
    rows = [ck_bar_row(f"{c.category} ({c.total_deals} deals)",
            f"${c.total_spend_mm:,.2f}M",
            c.total_spend_mm / total * 100.0, tone=_tone(c)) for c in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of panel spend by category '
            '· value = spend ($M) · tone = vendor concentration</div></div>')


def _categories_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Category","left"),("Total Deals","right"),("Total Spend ($M)","right"),
            ("Median Spend ($k)","right"),("Top Vendor","left"),("Concentration","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cc_c = P["warning"] if c.concentration_pct > 0.50 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.total_deals}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.total_spend_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${c.median_spend_k:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(c.top_vendor)}""", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cc_c};font-weight:600">{c.concentration_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _scorecards_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Firm","left"),("On-Time","right"),("Insights","right"),("Responsiveness","right"),
            ("Value","right"),("Overall","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ot_c = pos if s.on_time_delivery_pct >= 0.92 else acc
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.firm)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ot_c};font-weight:700">{s.on_time_delivery_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{s.quality_of_insights}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.responsiveness}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.value_for_money}""", align="right", mono=True)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos};font-weight:700">{_html.escape(s.overall_rating)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pipeline_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Firm","left"),("Category","left"),("Referred By","left"),("Meeting","left"),("Stage","center"),("Likelihood","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        l_c = pos if p.likelihood_engage_pct >= 0.60 else (acc if p.likelihood_engage_pct >= 0.45 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.firm)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(p.category)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.referred_by)}</td>',
            f'{ck_data_cell(f"""{_html.escape(p.meeting_scheduled)}""", mono=True, tone="acc")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.stage)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:700">{p.likelihood_engage_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _phases_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Deal Phase","left"),("Categories","left"),("Typical Spend ($M)","right"),("Timeline (weeks)","right"),("Notes","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.phase)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.categories)}</td>',
            f'{ck_data_cell(f"""${p.typical_spend_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{p.timeline_weeks}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.notes)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_diligence_vendors(params: dict = None) -> str:
    from rcm_mc.data_public.diligence_vendors import compute_diligence_vendors
    r = compute_diligence_vendors()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    tier_1_count = sum(1 for v in r.vendors if v.tier == "Tier 1")

    kpi_strip = (
        ck_kpi_block("Vendors on Panel", str(r.total_vendors), "", "") +
        ck_kpi_block("Deals Covered LTM", str(r.total_deals_covered), "", "") +
        ck_kpi_block("Total Spend LTM", f"${r.total_spend_ltm_mm:,.1f}M", "", "") +
        ck_kpi_block("Avg NPS", str(r.avg_nps), "", "") +
        ck_kpi_block("Tier 1 Vendors", str(tier_1_count), "", "") +
        ck_kpi_block("Categories", str(len(r.categories)), "", "") +
        ck_kpi_block("Pipeline Vendors", str(len(r.pipeline)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    v_tbl = _vendors_table(r.vendors)
    v_chart = _vendors_chart(r.vendors)
    value_anchor = ck_value_anchor(
        "Diligence Panel Spend",
        f"${r.total_spend_ltm_mm:,.1f}M spend LTM",
        delta=f"{r.total_vendors} vendors · {r.total_deals_covered} engagements · +{r.avg_nps} avg NPS",
        tone="teal",
    )
    c_tbl = _categories_table(r.categories)
    c_chart = _categories_chart(r.categories)
    s_tbl = _scorecards_table(r.scorecards)
    s_scatter = _scorecards_scatter(r.scorecards)
    p_tbl = _pipeline_table(r.pipeline)
    ph_tbl = _phases_table(r.phase_spend)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Diligence Vendor Directory",
        eyebrow="DILIGENCE VENDORS",
        meta=f"{r.total_vendors} vendors across {len(r.categories)} categories ({tier_1_count} Tier 1) · {r.total_deals_covered} deal engagements LTM · ${r.total_spend_ltm_mm:,.1f}M spend at +{r.avg_nps} avg NPS · {len(r.pipeline)} new vendors in pipeline",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Active Vendor Panel</div>{v_chart}{v_tbl}</div>
  <div style="{cell}"><div style="{h3}">Category Spend Analysis</div>{c_chart}{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top Vendor Scorecards</div>{s_scatter}{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">New Vendor Pipeline</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Spend by Deal Phase</div>{ph_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Vendor Directory Thesis:</strong> 30 active vendors across 14 categories; ${r.total_spend_ltm_mm:,.1f}M spend LTM at average NPS {r.avg_nps}.
    Tier 1 partners (A&M, FTI, Chartis, Kirkland, Ropes) carry premium pricing but deliver on-time at 92-95%.
    Mid-market QoE firms (BDO, CohnReznick) offer 40-60% cost savings for lower-mid deals with comparable quality.
    Pipeline of 7 new vendors in vetting; highest-likelihood adds: Charles River Associates (regulatory) at 78%, WTW (HR/benefits, switch from Aon) at 68%, Riveron (QoE alternative to A&M) at 65%.
    Deep diligence phase (pre-SPA) is primary spend concentration at ${r.phase_spend[1].typical_spend_mm:,.2f}M over 6 weeks with 6+ concurrent workstreams.
  </div>
</div>"""

    return chartis_shell(body, "Diligence Vendors", active_nav="/diligence-vendors",
        editorial_intro={
            "eyebrow": "DILIGENCE VENDORS",
            "headline": "What the diligence vendors page reveals on this deal.",
            "italic_word": "reveals",
        })
