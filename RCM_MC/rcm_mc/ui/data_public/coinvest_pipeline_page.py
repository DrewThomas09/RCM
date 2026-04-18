"""Co-Investment Pipeline / LP Allocation Tracker — /coinvest-pipeline."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


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
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(d.allocation_status)
        f_c = pos if d.management_fee_pct <= 0.25 else acc
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(d.sponsor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${d.equity_check_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">${d.coinvest_allocation_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(d.allocation_status)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{f_c};font-weight:600">{d.management_fee_pct:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.carry_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.hurdle_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(d.expected_close)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lps_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("LP","left"),("Type","left"),("Commitment ($M)","right"),("Active","right"),
            ("Total Coinvests","right"),("Avg Check ($M)","right"),("AUM ($B)","right"),("Appetite","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, l in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = _appetite_color(l.appetite)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(l.lp_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.lp_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${l.commitment_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{l.coinvests_active}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{l.coinvests_total}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${l.avg_check_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${l.aum_b:.1f}B</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{a_c};border:1px solid {a_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(l.appetite)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sectors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sector","left"),("Active Opps","right"),("Total Equity ($M)","right"),
            ("Allocated ($M)","right"),("Unallocated ($M)","right"),("Avg Fee","right"),("Avg Carry","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.active_opportunities}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.total_equity_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${s.allocated_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${s.unallocated_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.avg_fee_pct:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.avg_carry_pct:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _realizations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("Sponsor","left"),("Vintage","right"),
            ("Exit","right"),("Invested ($M)","right"),("Realized ($M)","right"),
            ("Gross MOIC","right"),("Net MOIC","right"),("Gross IRR","right"),("DPI","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if r.gross_moic >= 2.5 else acc
        i_c = pos if r.gross_irr_pct >= 22 else acc
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(r.sponsor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.vintage}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.exit_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.coinvest_invested_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${r.coinvest_realized_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{r.gross_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.net_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:700">{r.gross_irr_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{r.dpi:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _fees_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Tier","left"),("Description","left"),("Mgmt Fee Discount","right"),
            ("Carry Reduction","right"),("Hurdle Concession","right"),("Realized Savings","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.lp_tier)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.tiers_description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{f.mgmt_fee_discount * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{f.carry_reduction * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.hurdle_concession_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${f.realized_savings_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _capacity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Total Equity","right"),("Sponsor","right"),("Anchor","right"),
            ("Remaining","right"),("Demand","right"),("Oversub","right"),("Methodology","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        o_c = pos if c.oversubscribed >= 2.0 else (acc if c.oversubscribed >= 1.5 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.total_equity_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.sponsor_check_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.anchor_coinvest_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">${c.remaining_capacity_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.indicative_demand_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{c.oversubscribed:.2f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.allocation_methodology)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    d_tbl = _deals_table(r.deals)
    c_tbl = _capacity_table(r.capacity)
    lp_tbl = _lps_table(r.lps)
    s_tbl = _sectors_table(r.sectors)
    re_tbl = _realizations_table(r.realizations)
    f_tbl = _fees_table(r.fees)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    avg_oversub = sum(c.oversubscribed for c in r.capacity) / len(r.capacity) if r.capacity else 0
    total_savings = sum(f.realized_savings_m for f in r.fees)

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Co-Investment Pipeline / LP Allocation Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.active_opportunities} active opportunities · ${r.total_equity_pipeline_m:,.1f}M equity pipeline · ${r.total_coinvest_available_m:,.1f}M coinvest capacity · {r.active_lp_count} active LPs · historical {r.historical_avg_moic:.2f}x MOIC / {r.historical_avg_irr_pct:.1f}% IRR — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Active Pipeline — {r.active_opportunities} Opportunities</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Deal Capacity & LP Demand</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector Allocation Summary</div>{s_tbl}</div>
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

    return chartis_shell(body, "Co-Invest Pipeline", active_nav="/coinvest-pipeline", data_source="synthetic")