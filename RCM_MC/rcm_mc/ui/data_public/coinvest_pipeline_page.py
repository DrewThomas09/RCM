"""Co-Investment Pipeline / LP Allocation Tracker — /coinvest-pipeline."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_data_cell, ck_kpi_block, ck_page_title, ck_illustrative_note, ck_bar_row, ck_value_anchor
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel

_COINVEST_NEEDED = [
    ("opportunity", "co-invest opportunity"), ("sponsor", "lead sponsor"),
    ("size", "co-invest size $"), ("lp_demand", "indicated LP demand $"),
    ("status", "status"),
]


def _deals_chart(items) -> str:
    """Lead chart — co-invest deals ranked by allocation."""
    total = sum(d.coinvest_allocation_m for d in items) or 1.0
    rows = [ck_bar_row(d.deal, f"${d.coinvest_allocation_m:,.0f}M",
            d.coinvest_allocation_m / total * 100.0, tone="teal")
            for d in sorted(items, key=lambda d: d.coinvest_allocation_m, reverse=True)]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of total co-invest '
            'allocation \u00b7 value = allocation ($M)</div></div>')



def _status_color(status: str) -> str:
    return {
        "closed": P["positive"],
        "allocation": P["accent"],
        "in marketing": P["warning"],
    }.get(status, P["text_dim"])


def _appetite_color(app: str) -> str:
    return {
        "very active": P["positive"],
        "active": P["accent"],
        "selective": P["warning"],
        "inactive": P["text_dim"],
    }.get(app, P["text_dim"])


def _deals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("Sponsor","left"),("Equity ($M)","right"),
            ("Coinvest ($M)","right"),("Status","center"),("Mgmt Fee","right"),("Carry","right"),
            ("Hurdle","right"),("Expected Close","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(d.allocation_status)
        f_c = pos if d.management_fee_pct <= 0.25 else acc
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.deal)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(d.sponsor)}</td>',
            f'{ck_data_cell(f"""${d.equity_check_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${d.coinvest_allocation_m:.1f}M""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(d.allocation_status)}</span>""", align="center")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{f_c};font-weight:600">{d.management_fee_pct:.2f}%</td>',
            f'{ck_data_cell(f"""{d.carry_pct:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{d.hurdle_pct:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(d.expected_close)}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lps_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("LP","left"),("Type","left"),("Commitment ($M)","right"),("Active","right"),
            ("Total Coinvests","right"),("Avg Check ($M)","right"),("AUM ($B)","right"),("Appetite","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, l in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = _appetite_color(l.appetite)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(l.lp_name)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.lp_type)}</td>',
            f'{ck_data_cell(f"""${l.commitment_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{l.coinvests_active}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{l.coinvests_total}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${l.avg_check_m:.1f}M""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${l.aum_b:.1f}B""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{a_c};border:1px solid {a_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(l.appetite)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sectors_chart(items) -> str:
    """Summary chart — co-invest sector allocation by total equity."""
    def _tone(s):
        if s.total_equity_m and s.unallocated_m / s.total_equity_m > 0.30: return "warning"
        return "teal"
    top = sorted(items, key=lambda s: s.total_equity_m, reverse=True)
    total = sum(s.total_equity_m for s in top) or 1.0
    rows = [ck_bar_row(f"{s.sector} ({s.active_opportunities} opps)",
            f"${s.total_equity_m:,.0f}M equity",
            s.total_equity_m / total * 100.0, tone=_tone(s)) for s in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of co-invest equity by sector '
            '· value = total equity ($M) · tone = unallocated &gt; 30%</div></div>')


def _sectors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sector","left"),("Active Opps","right"),("Total Equity ($M)","right"),
            ("Allocated ($M)","right"),("Unallocated ($M)","right"),("Avg Fee","right"),("Avg Carry","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.sector)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.active_opportunities}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${s.total_equity_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${s.allocated_m:.1f}M""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${s.unallocated_m:.1f}M</td>',
            f'{ck_data_cell(f"""{s.avg_fee_pct:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.avg_carry_pct:.1f}%""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _realizations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("Sponsor","left"),("Vintage","right"),
            ("Exit","right"),("Invested ($M)","right"),("Realized ($M)","right"),
            ("Gross MOIC","right"),("Net MOIC","right"),("Gross IRR","right"),("DPI","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if r.gross_moic >= 2.5 else acc
        i_c = pos if r.gross_irr_pct >= 22 else acc
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.deal)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(r.sponsor)}</td>',
            f'{ck_data_cell(f"""{r.vintage}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{r.exit_year}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${r.coinvest_invested_m:.1f}M""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${r.coinvest_realized_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{r.gross_moic:.2f}x</td>',
            f'{ck_data_cell(f"""{r.net_moic:.2f}x""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:700">{r.gross_irr_pct:.1f}%</td>',
            f'{ck_data_cell(f"""{r.dpi:.2f}x""", align="right", mono=True, tone="pos")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _fees_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Tier","left"),("Description","left"),("Mgmt Fee Discount","right"),
            ("Carry Reduction","right"),("Hurdle Concession","right"),("Realized Savings","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(f.lp_tier)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.tiers_description)}</td>',
            f'{ck_data_cell(f"""{f.mgmt_fee_discount * 100:.0f}%""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{f.carry_reduction * 100:.0f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{f.hurdle_concession_pct:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${f.realized_savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _capacity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Total Equity","right"),("Sponsor","right"),("Anchor","right"),
            ("Remaining","right"),("Demand","right"),("Oversub","right"),("Methodology","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        o_c = pos if c.oversubscribed >= 2.0 else (acc if c.oversubscribed >= 1.5 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${c.total_equity_m:.1f}M""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.sponsor_check_m:.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.anchor_coinvest_m:.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.remaining_capacity_m:.1f}M""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""${c.indicative_demand_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{c.oversubscribed:.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.allocation_methodology)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_coinvest_pipeline(params: dict = None) -> str:
    from rcm_mc.data_public.coinvest_pipeline import compute_coinvest_pipeline
    r = compute_coinvest_pipeline()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Active Opps", str(r.active_opportunities), "", "") +
        ck_kpi_block("Equity Pipeline", f"${r.total_equity_pipeline_m:,.1f}M", "", "") +
        ck_kpi_block("Coinvest Available", f"${r.total_coinvest_available_m:,.1f}M", "", "") +
        ck_kpi_block("Allocated", f"${r.total_coinvest_allocated_m:,.1f}M", "", "") +
        ck_kpi_block("Historical MOIC", f"{r.historical_avg_moic:.2f}x", "", "") +
        ck_kpi_block("Historical IRR", f"{r.historical_avg_irr_pct:.1f}%", "", "") +
        ck_kpi_block("Active LPs", str(r.active_lp_count), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    d_chart = _deals_chart(r.deals)
    d_tbl = _deals_table(r.deals)
    value_anchor = ck_value_anchor(
        "Co-Invest Pipeline",
        f"${r.total_equity_pipeline_m:,.0f}M equity pipeline",
        delta=f"{r.active_opportunities} opportunities \u00b7 ${r.total_coinvest_allocated_m:,.0f}M allocated \u00b7 {r.historical_avg_moic:.2f}x hist MOIC",
        opportunity=f"${r.total_coinvest_available_m:,.0f}M co-invest capacity available",
        tone="positive",
    )
    c_tbl = _capacity_table(r.capacity)
    lp_tbl = _lps_table(r.lps)
    s_tbl = _sectors_table(r.sectors)
    s_chart = _sectors_chart(r.sectors)
    re_tbl = _realizations_table(r.realizations)
    f_tbl = _fees_table(r.fees)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    avg_oversub = sum(c.oversubscribed for c in r.capacity) / len(r.capacity) if r.capacity else 0
    total_savings = sum(f.realized_savings_m for f in r.fees)

    # B11 sweep batch 2 PR 2/10 — replace bespoke .ck-page-h1 inline
    # HTML with editorial-kit ck_page_title primitive. Pre-fix sub-line
    # was 6 stats long ("X active · $YM pipeline · $ZM capacity · N LPs
    # · historical Mx MOIC / I% IRR — N corpus deals") — denser than
    # the editorial register meta typically carries. Trimmed to 4
    # most-load-bearing: pipeline-side count + dollar volume +
    # coinvest capacity + LP count. Historical performance stats
    # drop from meta — partners can read them in the KPI strip
    # below.
    page_title = ck_page_title(
        "Co-Investment Pipeline / LP Allocation Tracker",
        eyebrow="CO-INVEST PIPELINE",
        meta=(
            f"{r.active_opportunities} active opportunities · "
            f"${r.total_equity_pipeline_m:,.1f}M equity pipeline · "
            f"${r.total_coinvest_available_m:,.1f}M coinvest capacity · "
            f"{r.active_lp_count} active LPs"
        ),
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {data_required_panel(P, title="Co-Invest Pipeline", needed=_COINVEST_NEEDED,
      template="coinvest_pipeline_template.csv", request_from="Deal team / IR",
      activates="co-invest sizing vs LP demand coverage",
      guide_hint="What co-invest pipeline data do I need to upload?")}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Active Pipeline — {r.active_opportunities} Opportunities</div>{d_chart}{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Deal Capacity & LP Demand</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector Allocation Summary</div>{s_chart}{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">LP Participation — {len(r.lps)} Institutional Investors</div>{lp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Historical Co-Invest Realizations</div>{re_tbl}</div>
  <div style="{cell}"><div style="{h3}">Fee Structure by LP Tier</div>{f_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Co-Investment Program Summary:</strong> {r.active_opportunities} active opportunities representing ${r.total_equity_pipeline_m:,.1f}M equity pipeline with ${r.total_coinvest_available_m:,.1f}M in coinvest capacity available to {r.active_lp_count} active LPs.
    Average oversubscription {avg_oversub:.2f}x across capacity-disclosed deals — demand firmly outpaces supply; allocation methodology favors cornerstone / preferred-tier LPs.
    Historical track record across 10 realized positions: {r.historical_avg_moic:.2f}x gross MOIC / {r.historical_avg_irr_pct:.1f}% gross IRR with 3.60x top decile (RCM SaaS exit). Healthcare coinvest returns continue to outperform buyout fund net returns by ~100-150bps.
    Public pensions (CalPERS, CPPIB) and sovereign wealth (GIC, Temasek) drive 52% of total commitments; endowment / family-office activity remains selective with preference for growth-equity over buyout.
    Fee savings via cornerstone tier ($125M realized) + no-fee/no-carry structures (${total_savings:.1f}M total) deliver ~180-220bps of net return enhancement vs standard fund participation.
    Deal pipeline skews to GI, MSK, fertility, infusion — sector concentration consistent with broader healthcare buyout market; 4 of 12 deals in marketing phase with 60-day close windows.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Co-Invest Pipeline", active_nav="/coinvest-pipeline",
        editorial_intro={
            "eyebrow": "COINVEST PIPELINE",
            "headline": "What the coinvest pipeline page reveals on this deal.",
            "italic_word": "reveals",
        })
