"""Risk Adjustment / HCC Tracker — /risk-adjustment."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor


def _portfolios_chart(items) -> str:
    """Lead chart for the portfolio table — deals ranked by average RAF
    score so the highest-acuity (and highest-revenue-per-point) books
    surface first. Bar width = avg RAF relative to the highest book;
    value = avg RAF; tone marks the table's RAF-trend tiers (YoY lift
    >=0.05 green · >=0.03 teal · below amber). Full grid stays below.
    """
    hi = max((p.avg_raf for p in items), default=1.0) or 1.0
    ranked = sorted(items, key=lambda p: p.avg_raf, reverse=True)
    rows = []
    for p in ranked:
        tone = ("positive" if p.raf_trend >= 0.05 else "teal"
                if p.raf_trend >= 0.03 else "warning")
        rows.append(ck_bar_row(
            p.deal,
            f"{p.avg_raf:.3f}",
            p.avg_raf / hi * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = average RAF relative to highest book · value = avg RAF · '
        'tone = YoY RAF trend (green &ge;+0.05 · teal &ge;+0.03 · amber below)</div>'
        '</div>'
    )


def _intensity_color(i: str) -> str:
    return {
        "disciplined": P["positive"],
        "standard": P["accent"],
        "high intensity": P["warning"],
        "aggressive": P["negative"],
    }.get(i, P["text_dim"])


def _priority_color(p: str) -> str:
    return {
        "high": P["negative"],
        "medium": P["warning"],
        "low": P["text_dim"],
    }.get(p, P["text_dim"])


def _portfolios_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("MA Lives (K)","right"),("Avg RAF","right"),
            ("Prior RAF","right"),("RAF Trend","right"),("MA Rev ($M)","right"),
            ("$ per RAF pt","right"),("Coding Intensity","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ci_c = _intensity_color(p.coding_intensity)
        t_c = pos if p.raf_trend >= 0.05 else (acc if p.raf_trend >= 0.03 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector)}</td>',
            f'{ck_data_cell(f"""{p.ma_lives_k:.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{p.avg_raf:.3f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{p.prior_year_raf:.3f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">+{p.raf_trend * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${p.ma_revenue_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${p.revenue_per_raf_point_m:.2f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ci_c};border:1px solid {ci_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.coding_intensity)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hcc_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("HCC","left"),("Description","left"),("Members (K)","right"),("Open Suspects","right"),
            ("Closure Rate","right"),("Opportunity ($M)","right"),("Priority","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = _priority_color(h.clinical_priority)
        c_c = pos if h.gap_closure_rate_pct >= 0.80 else (acc if h.gap_closure_rate_pct >= 0.70 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(h.hcc)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(h.hcc_description)}</td>',
            f'{ck_data_cell(f"""{h.portfolio_members_k}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn};font-weight:700">{h.open_suspects:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{h.gap_closure_rate_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""${h.revenue_opportunity_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{p_c};border:1px solid {p_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(h.clinical_priority)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _coding_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Documentation Score","right"),("MRA Quality","right"),
            ("Auto-Adjudicated %","right"),("Provider Training","right"),
            ("Chart Review Cov","right"),("Prospective Coding","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if c.documentation_score >= 8.5 else (acc if c.documentation_score >= 8.0 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{c.documentation_score:.2f}</td>',
            f'{ck_data_cell(f"""{c.mra_quality_pct * 100:.0f}%""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{c.auto_adjudicated_pct * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{c.provider_coding_training_pct * 100:.0f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{c.chart_review_coverage_pct * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{c.prospective_coding_pct * 100:.0f}%""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _radv_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Deal","left"),("Current RAF","right"),("Extrap Recovery ($M)","right"),
            ("Sample","right"),("Error %","right"),("Likely Payback ($M)","right"),("Max Exposure ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = P["warning"] if r.error_rate_pct >= 0.06 else (acc if r.error_rate_pct >= 0.04 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.deal)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{r.current_raf:.3f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""${r.radv_extrapolation_recovery_m:.1f}M""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{r.audit_sample_size}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{r.error_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${r.likely_payback_m:.1f}M""", align="right", mono=True, tone="neg", weight=700)}',
            f'{ck_data_cell(f"""${r.max_exposure_m:.1f}M""", align="right", mono=True, tone="neg", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></name></table></div>').replace('</name>', '')


def _v28_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Category","left"),("Members (K)","right"),("V24 RAF","right"),("V28 RAF","right"),
            ("Delta","right"),("Revenue Impact ($M)","right"),("Mitigation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.category)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{v.members_affected_k}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{v.v24_raf:.3f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{v.v28_raf:.3f}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{v.raf_delta:+.3f}""", align="right", mono=True, tone="neg", weight=700)}',
            f'{ck_data_cell(f"""${v.revenue_impact_m:+.1f}M""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.mitigation)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _programs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Program","left"),("Deals","right"),("Members Engaged (K)","right"),("Gaps Closed","right"),
            ("RAF Uplift","right"),("Revenue Captured ($M)","right"),("Cost per Gap ($K)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.program)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{p.portfolio_deals}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.members_engaged_k}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{p.gaps_closed:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""+{p.raf_uplift:.3f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""${p.revenue_captured_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${p.cost_per_gap_closed:.2f}K""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_risk_adjustment(params: dict = None) -> str:
    from rcm_mc.data_public.risk_adjustment import compute_risk_adjustment
    r = compute_risk_adjustment()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("MA Lives (Total)", f"{r.total_ma_lives_k:,.1f}K", "", "") +
        ck_kpi_block("Weighted RAF", f"{r.weighted_avg_raf:.3f}", "", "") +
        ck_kpi_block("MA Revenue", f"${r.total_ma_revenue_m:,.1f}M", "", "") +
        ck_kpi_block("Gap Opportunity", f"${r.total_raf_gap_opportunity_m:.1f}M", "", "") +
        ck_kpi_block("RADV Max Exposure", f"${r.radv_total_exposure_m:.1f}M", "", "") +
        ck_kpi_block("Avg Coding Discipline", f"{r.avg_coding_intensity_score:.2f}", "/10", "") +
        ck_kpi_block("Deals Exposed", str(r.portfolio_deals_exposed), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_chart = _portfolios_chart(r.portfolios)
    p_tbl = _portfolios_table(r.portfolios)
    h_tbl = _hcc_table(r.hcc_gaps)
    c_tbl = _coding_table(r.coding)
    rd_tbl = _radv_table(r.radv_sim)
    v_tbl = _v28_table(r.v28)
    pr_tbl = _programs_table(r.programs)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    v28_total_impact = sum(v.revenue_impact_m for v in r.v28)
    program_revenue = sum(p.revenue_captured_m for p in r.programs)
    page_title = ck_page_title(
        "Risk Adjustment / HCC Tracker",
        eyebrow="RISK ADJUSTMENT",
        meta=f"""{r.total_ma_lives_k:,.1f}K MA lives · weighted RAF {r.weighted_avg_raf:.3f} · ${r.total_ma_revenue_m:,.1f}M MA revenue · ${r.total_raf_gap_opportunity_m:.1f}M gap opportunity · ${r.radv_total_exposure_m:.1f}M max RADV exposure — {r.corpus_deal_count:,} corpus deals""",
    )
    
    value_anchor = ck_value_anchor(
        "Risk Adjustment",
        f"{r.weighted_avg_raf:.3f} wtd RAF",
        delta=f"{r.total_ma_lives_k:,.0f}K MA lives · ${r.total_ma_revenue_m:,.0f}M revenue",
        opportunity=f"${r.total_raf_gap_opportunity_m:,.1f}M RAF-gap opportunity",
        tone="positive",
    )
    # Real CMS Medicare Advantage population context (Geographic Variation PUF)
    # — the demographic drivers of risk adjustment (dual %, age), by state.
    cms_panel = ""
    try:
        from rcm_mc.data import ma_data as _ma
        _s = _ma.ma_summary()
        _dual = _ma.top_dual_states(8)
        if _s.get("total_ma_enrollment"):
            _rows = "".join(
                f'<tr><td style="padding:3px 10px">{_html.escape(str(d["state"]))}</td>'
                f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums">{d["dual_eligible_pct"]*100:.1f}%</td>'
                f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums">{int(d["ma_enrollment"]):,}</td></tr>'
                for d in _dual)
            cms_panel = (
                f'<div style="background:{panel};border:1px solid {border};'
                f'border-left:3px solid {acc};padding:14px 16px;margin-bottom:16px">'
                f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
                f'text-transform:uppercase;color:{text_dim};margin-bottom:6px">'
                f'MA population context · LIVE (CMS MA Geographic Variation, {_html.escape(str(_s.get("data_year","")))})</div>'
                f'<p style="font-size:12px;color:{text_dim};margin:0 0 8px">'
                f'<b style="color:{text}">{_s["total_ma_enrollment"]:,}</b> MA enrollees '
                f'across {_s["states"]} states; median dual-eligible share '
                f'<b style="color:{text}">{_s["median_dual_pct"]*100:.1f}%</b>, median age '
                f'{_s["median_avg_age"]:.0f}. Dual-eligible and age mix are the real '
                f'population drivers of risk-adjustment intensity. Highest-dual states:</p>'
                f'<table style="border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
                f'<thead><tr style="border-bottom:1px solid {border};color:{text_dim}">'
                f'<th style="padding:3px 10px;text-align:left">State</th>'
                f'<th style="padding:3px 10px;text-align:right">Dual %</th>'
                f'<th style="padding:3px 10px;text-align:right">MA enrollees</th></tr></thead>'
                f'<tbody>{_rows}</tbody></table>'
                f'<p style="font-size:11px;color:{text_dim};margin:8px 0 0">'
                f'Real CMS MA market/population data — <b>not</b> a Star Rating, '
                f'<b>not</b> a risk score, and not this deal. The RAF model below is '
                f'illustrative, scaled by your inputs.</p></div>')
    except Exception:
        cms_panel = ""

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  {cms_panel}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Portfolio RAF Roll-up</div>{p_chart}{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">HCC Gap Analysis — Top Opportunities</div>{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">V28 Model Impact Analysis</div>{v_tbl}</div>
  <div style="{cell}"><div style="{h3}">Gap-Closure Program Performance</div>{pr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Coding Quality & Infrastructure</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">RADV Audit Exposure Simulation</div>{rd_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Risk Adjustment Portfolio Summary:</strong> {r.total_ma_lives_k:,.1f}K MA lives generate ${r.total_ma_revenue_m:,.1f}M revenue at weighted RAF {r.weighted_avg_raf:.3f} — portfolio RAF elevated vs national MA average 1.02 driven by chronic-heavy portfolios (Sage 2.12, Ash 1.95).
    Gap analysis: ${r.total_raf_gap_opportunity_m:.1f}M in unclosed HCC opportunity across 15 top-priority categories; diabetes w/ complications ($18.5M), CHF ($15.8M), COPD ($14.5M) are top three.
    V28 phase-in impact: ${v28_total_impact:.1f}M portfolio headwind — diabetes, CHF, and SUD categories hit hardest; mitigation via specificity coding and documentation uplift.
    Gap-closure programs capture ${program_revenue:.1f}M annual revenue — prospective chart review ($65M) and retrospective chart review ($32M) are highest-ROI programs.
    RADV exposure ${r.radv_total_exposure_m:.1f}M max across {r.portfolio_deals_exposed} portcos — Sage ($22M), Redwood ($12.5M), Linden ($10.5M) concentrated in behavioral + home health.
    Coding intensity distribution: 4 disciplined, 4 standard, 2 high-intensity, 2 aggressive — "aggressive" profiles (Sage, Linden) raise RADV risk; coding discipline initiative scheduled Q2 2026.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Risk Adj / HCC", active_nav="/risk-adjustment",
        editorial_intro={
            "eyebrow": "RISK ADJUSTMENT",
            "headline": "What the risk adjustment page reveals on this deal.",
            "italic_word": "reveals",
        })
