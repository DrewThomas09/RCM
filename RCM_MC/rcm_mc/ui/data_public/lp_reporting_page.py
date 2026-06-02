"""LP Reporting Dashboard — /lp-reporting."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor


def _funds_chart(items) -> str:
    """Lead chart for the fund-summary table — funds ranked by TVPI so
    total value creation reads before the detailed metrics grid. Bar
    width = TVPI relative to the strongest fund; value = TVPI; tone marks
    the table's Cambridge quartile (top green · second teal · third
    amber · fourth red). Full fund grid stays directly below.
    """
    tone_for = {"top quartile": "positive", "top decile": "positive",
                "second quartile": "teal", "third quartile": "warning",
                "fourth quartile": "negative", "too early": "teal"}
    hi = max((f.tvpi for f in items), default=1.0) or 1.0
    ranked = sorted(items, key=lambda f: f.tvpi, reverse=True)
    rows = []
    for f in ranked:
        rows.append(ck_bar_row(
            f.fund,
            f"{f.tvpi:.2f}x",
            f.tvpi / hi * 100.0,
            tone=tone_for.get(f.quartile, "teal"),
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = TVPI relative to strongest fund · value = TVPI · '
        'tone = Cambridge quartile (green top · teal second · amber third · red fourth)</div>'
        '</div>'
    )


def _funds_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Fund","left"),("Vintage","right"),("Fund Size ($M)","right"),("Called %","right"),
            ("TVPI","right"),("DPI","right"),("RVPI","right"),("Net IRR","right"),("Quartile","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    q_c = {"top quartile": pos, "top decile": pos, "second quartile": acc, "third quartile": warn, "fourth quartile": P["negative"], "too early": text_dim}
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        qc = q_c.get(f.quartile, text_dim)
        tvpi_c = pos if f.tvpi >= 2.0 else (acc if f.tvpi >= 1.5 else text_dim)
        irr_c = pos if f.net_irr_pct >= 16 else (acc if f.net_irr_pct >= 12 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(f.fund)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{f.vintage}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${f.fund_size_mm:,.1f}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{f.called_pct * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tvpi_c};font-weight:700">{f.tvpi:,.2f}x</td>',
            f'{ck_data_cell(f"""{f.dpi:,.2f}x""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{f.rvpi:,.2f}x""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{irr_c};font-weight:700">{f.net_irr_pct:+.1f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{qc};border:1px solid {qc};border-radius:2px;letter-spacing:0.06em">{_html.escape(f.quartile)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _marks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Quarter","left"),("NAV ($M)","right"),("Δ %","right"),("Contribs ($M)","right"),
            ("Distribs ($M)","right"),("Cum DPI","right"),("Cum TVPI","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    _bar_max = max((m.nav_mm for m in items), default=1.0) or 1.0
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if m.quarterly_value_change_pct >= 0.03 else (acc if m.quarterly_value_change_pct >= 0.02 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.quarter)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${m.nav_mm:,.1f}""", align="right", mono=True, weight=700, bar=m.nav_mm / _bar_max * 100)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:600">{m.quarterly_value_change_pct * 100:+.2f}%</td>',
            f'{ck_data_cell(f"""${m.contributions_mm:,.1f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""${m.distributions_mm:,.1f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{m.cumulative_dpi:,.2f}x""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{m.cumulative_tvpi:,.2f}x""", align="right", mono=True, tone="acc", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _attribution_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Driver","left"),("Q Contribution ($M)","right"),("YTD Contribution ($M)","right"),
            ("% of Value Δ","right"),("Commentary","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if a.ytd_contribution_mm > 0 else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.driver)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c}">${a.quarterly_contribution_mm:+,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">${a.ytd_contribution_mm:+,.1f}</td>',
            f'{ck_data_cell(f"""{a.pct_of_value_change * 100:+.1f}%""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.commentary)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmarks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Metric","left"),("Fund","right"),("Q1 Bench","right"),("Q2 Bench","right"),
            ("Q3 Bench","right"),("Q4 Bench","right"),("Quartile","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    q_c = {"top decile": pos, "top quartile": pos, "second quartile": acc, "third quartile": warn}
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        qc = q_c.get(b.fund_quartile, text_dim)
        is_pct = "%" in b.metric or "IRR" in b.metric or "Ratio" in b.metric
        def fmt(v):
            if is_pct:
                return f"{v * 100:.1f}%" if abs(v) < 1 else f"{v:,.1f}%"
            return f"{v:,.2f}x"
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.metric)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{fmt(b.fund)}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{fmt(b.q1_benchmark)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{fmt(b.q2_benchmark)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{fmt(b.q3_benchmark)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{fmt(b.q4_benchmark)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{qc};border:1px solid {qc};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.fund_quartile)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _companies_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Company","left"),("Sector","left"),("Cost Basis ($M)","right"),
            ("Current FV ($M)","right"),("Marked MOIC","right"),("YTD Δ","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    s_c = {"Active": pos, "Closing Q2 exit": pos, "Watch list": warn, "Held": acc}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = s_c.get(c.status, text_dim)
        m_c = pos if c.marked_moic >= 2.0 else (acc if c.marked_moic >= 1.5 else (warn if c.marked_moic >= 1.0 else neg))
        ytd_c = pos if c.ytd_valuation_change_pct > 0.08 else (acc if c.ytd_valuation_change_pct >= 0 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.company)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.sector)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.cost_basis_mm:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.current_fair_value_mm:,.1f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{c.marked_moic:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ytd_c};font-weight:700">{c.ytd_valuation_change_pct * 100:+.1f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comms_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Date","left"),("Type","center"),("Topic","left"),("Status","center"),("Recipients","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    s_c = {"sent": pos, "completed": pos, "scheduled": acc, "in progress": warn}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = s_c.get(c.status, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.date)}""", mono=True, tone="acc")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.topic)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{c.recipients_count}""", align="right", mono=True)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_lp_reporting(params: dict = None) -> str:
    from rcm_mc.data_public.lp_reporting import compute_lp_reporting
    r = compute_lp_reporting()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Reporting Q", r.reporting_quarter, "", "") +
        ck_kpi_block("Funds", str(r.fund_count), "", "") +
        ck_kpi_block("Total AUM", f"${r.total_aum_mm:,.0f}M", "", "") +
        ck_kpi_block("Blended TVPI", f"{r.blended_tvpi:.2f}x", "", "") +
        ck_kpi_block("Blended DPI", f"{r.blended_dpi:.2f}x", "", "") +
        ck_kpi_block("Blended IRR", f"{r.blended_irr_pct:.1f}%", "", "") +
        ck_kpi_block("Active Companies", str(len(r.companies)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    f_chart = _funds_chart(r.funds)
    f_tbl = _funds_table(r.funds)
    m_tbl = _marks_table(r.marks)
    a_tbl = _attribution_table(r.attribution)
    b_tbl = _benchmarks_table(r.benchmarks)
    c_tbl = _companies_table(r.companies)
    cm_tbl = _comms_table(r.communications)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    top_quartile = sum(1 for f in r.funds if f.quartile == "top quartile")
    page_title = ck_page_title(
        "LP Reporting Dashboard",
        eyebrow="LP REPORTING",
        meta=f"{r.reporting_quarter} · {r.fund_count} funds at ${r.total_aum_mm:,.0f}M AUM · blended {r.blended_tvpi:.2f}x TVPI / {r.blended_dpi:.2f}x DPI at {r.blended_irr_pct:.1f}% IRR · {top_quartile} of {r.fund_count} funds tracking top-quartile vs PitchBook",
    )

    value_anchor = ck_value_anchor(
        "Portfolio NAV",
        f"${r.total_aum_mm:,.0f}M AUM",
        delta=f"{r.blended_tvpi:.2f}x TVPI · {r.blended_dpi:.2f}x DPI · {r.blended_irr_pct:.1f}% net IRR",
        tone="positive",
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Fund-Level Performance Summary</div>{f_chart}{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Quarterly NAV Evolution (9 quarters)</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Value Change Attribution — Q1 vs YTD</div>{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">Benchmark vs PitchBook Quartile</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Portfolio Company Marks &amp; Status</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">LP Communications Calendar</div>{cm_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">LP Reporting Thesis:</strong> ${r.total_aum_mm:,.0f}M AUM across {r.fund_count} funds;
    blended TVPI {r.blended_tvpi:.2f}x / DPI {r.blended_dpi:.2f}x / IRR {r.blended_irr_pct:.1f}%.
    {top_quartile} of {r.fund_count} funds tracking top-quartile vs PitchBook benchmarks.
    Q1 2026 value change driven primarily by EBITDA growth (54%) and multiple expansion (22%); realization gains added $45M from two exits.
    Upcoming LP communications: Q1 2026 audited financials (in progress), Q2 portfolio review call scheduled May 2026.
    Watch list: Everest Behavioral Health (negative YTD mark, strategic review in progress), Harbor Urgent Care (flat trajectory).
    Kestrel Fertility exit closing Q2 2026 will materially move Fund IV DPI.
  </div>
</div>"""

    from rcm_mc.ui._chartis_kit import ck_illustrative_note as _ckn
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(_ckn("LP figures (illustrative seed corpus)") + body, "LP Reporting", active_nav="/lp-reporting",
        editorial_intro={
            "eyebrow": "LP REPORTING",
            "headline": "What the lp reporting page reveals on this deal.",
            "italic_word": "reveals",
        })
