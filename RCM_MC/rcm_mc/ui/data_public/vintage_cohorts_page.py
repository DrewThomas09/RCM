"""Vintage Cohort Performance Tracker — /vintage-cohorts."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell
from rcm_mc.ui.chartis._helpers import render_page_explainer


def _quartile_color(q: int) -> str:
    return {1: P["positive"], 2: P["accent"], 3: P["warning"], 4: P["negative"]}.get(q, P["text_dim"])


def _regime_color(r: str) -> str:
    if "ZIRP" in r or "stimulus" in r.lower(): return P["warning"]
    if "peak" in r.lower() or "aggressive" in r.lower(): return P["negative"]
    if "easing" in r.lower() or "tightening" in r.lower(): return P["accent"]
    return P["text_dim"]


def _cohorts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vintage","right"),("Deals","right"),("Deployed ($M)","right"),("NAV ($M)","right"),
            ("Distributed ($M)","right"),("DPI","right"),("RVPI","right"),("TVPI","right"),
            ("Net IRR","right"),("Gross IRR","right"),("Benchmark TVPI","right"),("Quartile","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        q_c = _quartile_color(c.quartile_vs_cambridge)
        t_c = pos if c.tvpi >= 2.20 else (acc if c.tvpi >= 1.80 else P["warning"])
        ir_c = pos if c.net_irr_pct >= 17.0 else (acc if c.net_irr_pct >= 13.0 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{c.vintage_year}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.deals}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${c.total_deployed_m:,.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.total_nav_m:,.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.total_distributed_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos if c.dpi >= 1.0 else acc};font-weight:700">{c.dpi:.2f}x</td>',
            f'{ck_data_cell(f"""{c.rvpi:.2f}x""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{c.tvpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ir_c};font-weight:700">{c.net_irr_pct:.1f}%</td>',
            f'{ck_data_cell(f"""{c.gross_irr_pct:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{c.benchmark_tvpi:.2f}x""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{q_c};font-weight:700">Q{c.quartile_vs_cambridge if c.quartile_vs_cambridge else "—"}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sector_vintages_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sector","left"),("Vintage","right"),("Deals","right"),("Deployed ($M)","right"),
            ("Current TVPI","right"),("Realized ($M)","right"),("Best Deal","left"),("Best MOIC","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = pos if s.current_tvpi >= 2.25 else (acc if s.current_tvpi >= 1.85 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.sector)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.vintage_year}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.deals}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${s.deployed_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{s.current_tvpi:.2f}x</td>',
            f'{ck_data_cell(f"""${s.realized_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(s.best_deal)}</td>',
            f'{ck_data_cell(f"""{s.best_moic:.2f}x""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _holds_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vintage","right"),("Median Hold (y)","right"),("Earliest Exit","right"),("Latest Exit","right"),
            ("Hold Target","right"),("Exits Complete","right"),("Exits Pending","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        hc_c = P["warning"] if h.median_hold_years > h.hold_target_years + 0.5 else (acc if h.median_hold_years > h.hold_target_years else pos)
        cells = [
            f'{ck_data_cell(f"""{h.vintage_year}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hc_c};font-weight:700">{h.median_hold_years:.1f}</td>',
            f'{ck_data_cell(f"""{h.earliest_exit:.1f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{h.latest_exit:.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{h.hold_target_years:.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{h.exits_complete}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{h.exits_pending}""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exits_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Vintage","right"),("Strategic","right"),("Secondary Buyout","right"),("Continuation","right"),
            ("IPO","right"),("Recap","right"),("Total Exits","right"),("Median Multiple","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if e.median_exit_multiple >= 2.40 else (acc if e.median_exit_multiple >= 2.00 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{e.vintage_year}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{e.strategic_sale_count}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{e.secondary_buyout_count}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{e.continuation_vehicle_count}</td>',
            f'{ck_data_cell(f"""{e.ipo_count}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{e.recap_count}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{e.total_exits}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{e.median_exit_multiple:.2f}x</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _envs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Vintage","right"),("10Y Yield","right"),("HC PE SOFR+ (bps)","right"),
            ("Entry ×","right"),("Leverage","right"),("Fed Regime","center"),("Overlay","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = _regime_color(e.fed_regime)
        cells = [
            f'{ck_data_cell(f"""{e.vintage_year}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{e.ma_yield_curve_10y:.2f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{e.sofr_spread_hc_pe}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{e.typical_entry_multiple:.1f}x""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{e.typical_leverage:.1f}x""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{r_c};border:1px solid {r_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.fed_regime)}</span>""", align="center")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(e.macro_overlay)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pacing_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Vintage","right"),("Target ($M)","right"),("Actual ($M)","right"),("Rate","right"),
            ("Deals in Market","right"),("Deals Closed","right"),("Missed Deals","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if 0.95 <= p.deployment_rate_pct <= 1.08 else (acc if p.deployment_rate_pct >= 0.85 else warn)
        cells = [
            f'{ck_data_cell(f"""{p.vintage_year}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${p.target_deployment_m:,.1f}M""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${p.actual_deployment_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{p.deployment_rate_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{p.deals_in_market}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.deals_closed_lib}""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{p.missed_deals}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_vintage_cohorts(params: dict = None) -> str:
    from rcm_mc.data_public.vintage_cohorts import compute_vintage_cohorts
    r = compute_vintage_cohorts()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Vintages", str(r.vintages_tracked), "", "") +
        ck_kpi_block("Total Deployed", f"${r.total_deployed_b:.2f}B", "", "") +
        ck_kpi_block("Portfolio DPI", f"{r.portfolio_dpi:.2f}x", "", "") +
        ck_kpi_block("Portfolio TVPI", f"{r.portfolio_tvpi:.2f}x", "", "") +
        ck_kpi_block("Best Vintage", str(r.best_vintage), "", "") +
        ck_kpi_block("Worst Vintage", str(r.worst_vintage), "", "") +
        ck_kpi_block("Sector Cohorts", str(len(r.sector_vintages)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    c_tbl = _cohorts_table(r.cohorts)
    sv_tbl = _sector_vintages_table(r.sector_vintages)
    h_tbl = _holds_table(r.holds)
    e_tbl = _exits_table(r.exits)
    env_tbl = _envs_table(r.environments)
    p_tbl = _pacing_table(r.pacings)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    q1q2 = sum(1 for c in r.cohorts if c.quartile_vs_cambridge in (1, 2))
    body = f"""
<div class="ck-page-wrap">
  <div class="ck-page-head">
    <h1 class="ck-page-h1">Vintage Cohort Performance Tracker</h1>
    <p class="ck-page-sub">{r.vintages_tracked} vintages · ${r.total_deployed_b:.2f}B deployed · {r.portfolio_dpi:.2f}x aggregate DPI · {r.portfolio_tvpi:.2f}x aggregate TVPI · {q1q2}/{r.vintages_tracked} top-half Cambridge Associates — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Vintage Cohort Performance</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector × Vintage Performance</div>{sv_tbl}</div>
  <div style="{cell}"><div style="{h3}">Hold Period Trends</div>{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">Exit Mix by Vintage</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Environment by Vintage</div>{env_tbl}</div>
  <div style="{cell}"><div style="{h3}">Deployment Pacing vs Plan</div>{p_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Vintage Cohort Summary:</strong> ${r.total_deployed_b:.2f}B deployed across {r.vintages_tracked} vintages — {q1q2} cohorts top-half of Cambridge Associates healthcare buyout benchmarks.
    Vintage {r.best_vintage} leads at 2.69x TVPI / 19.5% net IRR — healthcare rollup wave pre-COVID captured accretive multiple arbitrage + mature exit environment.
    2021-2022 vintages pressured by peak entry multiples (16.8x-14.2x EV/EBITDA) + subsequent multiple compression — mid-cycle reset now working through portfolio (Q2/Q3 quartile positioning).
    2020 pandemic vintage (Q2 position) deployed opportunistically through COVID — defensive sector tilt (home health, behavioral, infusion) delivered 2.04x TVPI / 15.2% net IRR.
    Exit mix evolution: 2015-2017 vintages favored strategic sale (55-60%); 2018-2020 saw secondary buyout rise to 35-40%; 2021+ continuation vehicle + dividend recap emerge as liquidity alternatives given exit drought.
    Hold period extension: 5.5yr (2015) → 6.5yr (2019) → 4.5yr (2021 — too early to exit); median hold running 1.0-1.5 years above target across 2017-2019 cohorts — driving DPI pressure.
    2025 deployment running 52% of target (${r.cohorts[-1].total_deployed_m:,.0f}M vs $3,000M) reflects deal flow recovery still early + sponsor discipline; easing cycle begins deployment pickup.
  </div>
</div>"""

    explainer = render_page_explainer(
        what=(
            "Per-vintage cohort roll-up: deployed capital, NAV, "
            "distributions, DPI/RVPI/TVPI, net and gross IRR, plus "
            "Cambridge-Associates benchmark quartile and the "
            "macro/rate regime for each vintage year."
        ),
        source="data_public/vintage_cohorts.py; Cambridge Associates US PE benchmarks.",
        page_key="vintage-cohorts",
    )
    return chartis_shell(explainer + body, "Vintage Cohorts", active_nav="/vintage-cohorts",
        editorial_intro={
            "eyebrow": "VINTAGE COHORTS",
            "headline": "What the vintage cohorts page reveals on this deal.",
            "italic_word": "reveals",
        })
