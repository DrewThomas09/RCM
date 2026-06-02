"""Medicare Advantage / Star Ratings Tracker — /ma-star."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor


def _star_color(s: float) -> str:
    if s >= 4.5: return P["positive"]
    if s >= 4.0: return P["accent"]
    if s >= 3.5: return P["warning"]
    if s >= 3.0: return P["text_dim"]
    return P["negative"]


def _plans_chart(items) -> str:
    """Lead chart for the plan table — MA plans ranked by 2026 Star
    rating so the bonus-eligible (>=4.0) and at-risk plans read at a
    glance. Bar width = rating on the 5-star scale; value = the rating;
    tone matches the table's star bands (>=4.5 green · >=4.0 teal · >=3.5
    amber · below red). Full plan grid stays directly below.
    """
    ranked = sorted(items, key=lambda p: p.star_rating_2026, reverse=True)
    rows = []
    for p in ranked:
        s = p.star_rating_2026
        tone = ("positive" if s >= 4.5 else "teal" if s >= 4.0
                else "warning" if s >= 3.5 else "negative")
        rows.append(ck_bar_row(
            p.plan,
            f"{s:.1f}★",
            s / 5.0 * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = 2026 Star rating (of 5) · value = rating · '
        'tone = band (green &ge;4.5 · teal &ge;4.0 bonus · amber &ge;3.5 · red below)</div>'
        '</div>'
    )


def _traj_color(t: str) -> str:
    return {
        "improving": P["positive"],
        "stable": P["accent"],
        "watching": P["warning"],
        "declining": P["negative"],
        "launching 2027": P["text_dim"],
    }.get(t, P["text_dim"])


def _plans_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Plan","left"),("Parent","left"),("Footprint","center"),("Enrollment (K)","right"),
            ("2025 Stars","right"),("2026 Stars","right"),("Δ","right"),("Rebate %","right"),
            ("Benchmark %","right"),("MBR %","right"),("MLR %","right"),("QBP %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s25 = _star_color(p.star_rating_2025)
        s26 = _star_color(p.star_rating_2026)
        delta = p.star_rating_2026 - p.star_rating_2025
        d_c = pos if delta > 0 else (warn if delta < 0 else text_dim)
        mlr_c = pos if p.mlr_pct <= 0.85 else (acc if p.mlr_pct <= 0.88 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.plan)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.parent)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.states)}</td>',
            f'{ck_data_cell(f"""{p.enrollment_k:,.1f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s25};font-weight:700">{p.star_rating_2025:.1f}★</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s26};font-weight:700">{p.star_rating_2026:.1f}★</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{delta:+.1f}</td>',
            f'{ck_data_cell(f"""{p.rebate_pct * 100:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.benchmark_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{p.mbr_pct * 100:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{mlr_c};font-weight:700">{p.mlr_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{p.quality_bonus_pct * 100:.1f}%""", align="right", mono=True, tone="pos")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposures_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("MA Partners","left"),("At-Risk (K)","right"),
            ("Capitation ($M)","right"),("Shared Savings ($M)","right"),("Quality ($M)","right"),("Total MA Revenue ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    _bar_max = max((e.annual_capitation_m for e in items), default=1.0) or 1.0
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(e.primary_ma_partners)}</td>',
            f'{ck_data_cell(f"""{e.at_risk_lives_k:.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${e.annual_capitation_m:.1f}M""", align="right", mono=True, tone="pos", weight=700, bar=e.annual_capitation_m / _bar_max * 100)}',
            f'{ck_data_cell(f"""${e.shared_savings_m:.1f}M""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${e.quality_incentive_m:.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.total_ma_revenue_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stars_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Measure","left"),("Category","left"),("Weight","center"),("Industry Median","right"),
            ("Top Quartile","right"),("Portfolio","right"),("Trajectory","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _traj_color(s.trajectory)
        pv = s.portfolio_measure
        iv = s.industry_median
        tv = s.top_quartile
        p_c = pos if (pv >= tv and tv > 0) else (acc if pv >= iv else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.measure)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.category)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.weight)}</td>',
            f'{ck_data_cell(f"""{iv:.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{tv:.2f}""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{pv:.2f}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.trajectory)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmarks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Region","left"),("MA Benchmark ($PMPM)","right"),("FFS Spend ($PMPM)","right"),
            ("A/B Revenue ($PMPM)","right"),("Part D ($PMPM)","right"),("Bid vs Benchmark","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.region)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${b.ma_benchmark_pmpm:,.0f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${b.ffs_spend_pmpm:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${b.ab_revenue_pmpm:,.0f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${b.d_revenue_pmpm:,.0f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{b.bid_vs_benchmark_pct * 100:.1f}%""", align="right", mono=True, tone="acc", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _radv_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Plan","left"),("Parent","left"),("Members Audited (K)","right"),("Alleged Recovery ($M)","right"),
            ("Status","center"),("Likely Exposure ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    st_colors = {"DOJ litigation": neg, "DOJ investigation": neg, "CMS extrapolation — challenged": acc,
                 "CMS audit — in review": acc, "CMS audit — ongoing": acc, "CMS audit closed": P["text_dim"]}
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = st_colors.get(r.status, P["text_dim"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.plan)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(r.parent)}</td>',
            f'{ck_data_cell(f"""{r.members_audited_k:.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${r.alleged_recovery_m:,.1f}M""", align="right", mono=True, tone="neg", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.status)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${r.likely_exposure_m:,.1f}M""", align="right", mono=True, tone="neg", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _updates_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Update","left"),("Effective","right"),("Impact","left"),("Industry $B","right"),("Portfolio Impact ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, u in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if u.portfolio_impact_m > 0 else (neg if u.portfolio_impact_m < 0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(u.update)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(u.effective_date)}""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(u.impact)}</td>',
            f'{ck_data_cell(f"""${u.industry_dollar_b:,.1f}B""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">${u.portfolio_impact_m:+.1f}M</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_ma_star_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.ma_star_tracker import compute_ma_star_tracker
    r = compute_ma_star_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("MA Plans", str(r.total_plans), "", "") +
        ck_kpi_block("Total Enrollment", f"{r.total_enrollment_m:.1f}M", "", "") +
        ck_kpi_block("Avg Stars", f"{r.avg_star_rating:.2f}", "★", "") +
        ck_kpi_block("4★+ Share", f"{r.pct_4star_plus * 100:.1f}%", "", "") +
        ck_kpi_block("Portfolio MA Rev", f"${r.total_portfolio_ma_revenue_m:,.1f}M", "", "") +
        ck_kpi_block("RADV Exposure", f"${r.total_radv_exposure_m:,.1f}M", "", "") +
        ck_kpi_block("Policy Updates", str(len(r.updates)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_chart = _plans_chart(r.plans)
    p_tbl = _plans_table(r.plans)
    e_tbl = _exposures_table(r.exposures)
    s_tbl = _stars_table(r.stars)
    b_tbl = _benchmarks_table(r.benchmarks)
    rd_tbl = _radv_table(r.radv)
    u_tbl = _updates_table(r.updates)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    stars_up = sum(1 for p in r.plans if p.star_rating_2026 > p.star_rating_2025)
    stars_down = sum(1 for p in r.plans if p.star_rating_2026 < p.star_rating_2025)

    # 2026-05-30 audit P5 editorial: Star Ratings exist only inside
    # Medicare Advantage — the slash-dual was a category restatement.
    # "MA Star Ratings Tracker" preserves both signals and matches
    # the eyebrow's MA STAR TRACKER form.
    page_title = ck_page_title(
        "MA Star Ratings Tracker",
        eyebrow="MA STAR TRACKER",
        meta=f"{r.total_plans} MA plans tracking {r.total_enrollment_m:.1f}M lives · {r.avg_star_rating:.2f}★ weighted avg · {r.pct_4star_plus * 100:.1f}% in 4+★ plans · {stars_up} improved / {stars_down} declined in 2026 cycle · ${r.total_portfolio_ma_revenue_m:,.0f}M portfolio MA revenue · ${r.total_radv_exposure_m:,.0f}M industry RADV exposure",
    )

    value_anchor = ck_value_anchor(
        "MA Star Ratings",
        f"{r.avg_star_rating:.1f}★ avg",
        delta=f"{r.pct_4star_plus * 100:.0f}% of plans ≥4.0 (bonus) · {r.total_enrollment_m:.1f}M lives",
        opportunity=f"${r.total_radv_exposure_m:,.0f}M RADV exposure",
        tone="teal",
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div style="background:{P['panel']};border:1px solid {P['border']};border-left:3px solid {P['warning']};padding:12px 16px;margin-bottom:16px;font-size:11px;color:{P['text_dim']}"><b style="color:{P['text']};font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:0.08em">REAL DATA DEFERRED &middot; CMS MA STAR RATINGS</b><br>CMS publishes Medicare Advantage &amp; Part D Star Ratings only as a zip-portal download (not a scriptable API), so this page shows <b>illustrative</b> star figures until that staged ingest is built. The real CMS Star Ratings file would activate this page directly. See docs/reports/RED_PAGE_ACTIVATION_PLAN.md.</div>
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">MA Plan Economics — Star Ratings, Rebates, MLR</div>{p_chart}{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Portfolio Exposure — MA Partnership Revenue</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Stars Measures — Portfolio vs Industry</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Regional Rate Benchmarks (PMPM)</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">RADV Exposure — Industry-Wide</div>{rd_tbl}</div>
  <div style="{cell}"><div style="{h3}">2026-2027 Policy Update Calendar</div>{u_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">MA Market Summary:</strong> {r.total_plans} tracked MA plans enroll {r.total_enrollment_m:.1f}M beneficiaries at {r.avg_star_rating:.2f}★ weighted average — {stars_up} plans improved, {stars_down} declined in 2026 cycle.
    {r.pct_4star_plus * 100:.1f}% of lives in 4+★ plans earning QBP bonuses — this is the critical threshold driving rebate eligibility and risk-adjusted revenue.
    Portfolio MA revenue ${r.total_portfolio_ma_revenue_m:,.1f}M across 12 platforms — Cardiology (Cedar, $95M), RCM SaaS (Oak, $65M as enabler), Home Health (Sage, $68M) are the largest exposures.
    RADV exposure: ${r.total_radv_exposure_m:,.1f}M industry-wide with DOJ actions against UHC (~$1.9B), Humana (~$1.1B), Aetna (~$725M) — extrapolation rule effective 2026-04-01 raises stakes.
    Benchmark PMPM spans $925 (rural) to $1,420 (Manhattan) — regional variation 35%+ drives MA margin dispersion; high-bench markets (Miami, NYC) support 5-8% margins vs 2-3% in rural.
    2026-2027 policy calendar stacks 8 material changes: +$32M portfolio tailwind from benchmark growth, offset by $58M V28 risk adjustment phase 3 drag — net positive ~$75M portfolio impact.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "MA / Stars Tracker", active_nav="/ma-star",
        editorial_intro={
            "eyebrow": "MA STAR TRACKER",
            "headline": "What the ma star tracker page reveals on this deal.",
            "italic_word": "reveals",
        })
