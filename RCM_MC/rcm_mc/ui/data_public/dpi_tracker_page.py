"""DPI / Distribution Tracker — /dpi-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _quartile_color(q: int) -> str:
    return {1: P["positive"], 2: P["accent"], 3: P["warning"], 4: P["negative"]}.get(q, P["text_dim"])


def _confidence_color(c: str) -> str:
    return {"high": P["positive"], "medium": P["accent"], "low": P["warning"]}.get(c, P["text_dim"])


def _funds_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Sponsor","left"),("Fund","left"),("Vintage","right"),("Size ($B)","right"),
            ("Called %","right"),("DPI","right"),("RVPI","right"),("TVPI","right"),
            ("Net IRR","right"),("Qtile","center"),("Benchmark DPI","right"),("Gap","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        q_c = _quartile_color(f.quartile)
        gap = f.dpi - f.benchmark_dpi
        g_c = pos if gap >= 0 else (warn if gap >= -0.10 else neg)
        ir_c = pos if f.net_irr_pct >= 18 else (acc if f.net_irr_pct >= 13 else warn)
        dp_c = pos if f.dpi >= 1.0 else (acc if f.dpi >= 0.5 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.sponsor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(f.fund_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.vintage}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${f.fund_size_b:.1f}B</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.called_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dp_c};font-weight:700">{f.dpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{f.rvpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{f.tvpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ir_c};font-weight:700">{f.net_irr_pct:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{q_c};font-weight:700">Q{f.quartile if f.quartile else "—"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.benchmark_dpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{gap:+.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _distributions_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sponsor","left"),("Fund","left"),("Date","right"),("Portfolio Co.","left"),
            ("Distribution ($M)","right"),("Event Type","center"),("Hold (yrs)","right"),("MOIC","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if d.moic >= 2.5 else (acc if d.moic >= 1.8 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(d.sponsor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.fund)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(d.event_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600">{_html.escape(d.portfolio_company)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${d.distribution_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(d.event_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{d.hold_years:.1f}y</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{d.moic:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sectors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sector","left"),("Sponsors","right"),("Funds","right"),("Committed ($B)","right"),
            ("Aggregate DPI","right"),("Median Hold","right"),("Exit Volume","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if s.aggregate_dpi >= 1.5 else (acc if s.aggregate_dpi >= 1.3 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.sponsors}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.funds}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.total_commitment_b:.1f}B</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{s.aggregate_dpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.median_hold_years:.1f}y</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${s.exit_volume_m:,.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _drought_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Metric","left"),("Current","right"),("Prior Year","right"),("Delta","right"),("LP Impact","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = neg if m.delta.startswith("-") else (acc if m.delta.startswith("+") else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.current_value)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(m.prior_year)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{_html.escape(m.delta)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.impact_on_lps)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lp_requests_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("LP","left"),("Type","left"),("Request","left"),("Commitment ($M)","right"),
            ("DPI Shortfall ($M)","right"),("Date","right"),("Sponsor Response","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.lp_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.lp_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(r.request_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${r.commitment_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${r.dpi_shortfall_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.request_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{pos}">{_html.escape(r.sponsor_response)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exit_paths_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Portfolio Co.","left"),("Sector","left"),("Sponsor","left"),("Hold (yrs)","right"),
            ("Target Exit","right"),("Path","left"),("Projected MOIC","right"),("Confidence","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = _confidence_color(p.confidence)
        m_c = pos if p.projected_moic >= 2.75 else (acc if p.projected_moic >= 2.25 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600">{_html.escape(p.portfolio_company)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.sponsor)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.hold_years:.1f}y</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.target_exit_year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.exit_path)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{p.projected_moic:.2f}x</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{c_c};border:1px solid {c_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.confidence)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_dpi_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.dpi_tracker import compute_dpi_tracker
    r = compute_dpi_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    kpi_strip = (
        ck_kpi_block("Funds Tracked", str(r.total_funds), "", "") +
        ck_kpi_block("Weighted DPI", f"{r.weighted_dpi:.2f}x", "", "") +
        ck_kpi_block("Weighted TVPI", f"{r.weighted_tvpi:.2f}x", "", "") +
        ck_kpi_block("Distributions (12mo)", f"${r.total_distributions_b:.2f}B", "", "") +
        ck_kpi_block("Pending Exits", f"${r.pending_exits_m:,.1f}M", "", "") +
        ck_kpi_block("Below Benchmark", str(r.below_benchmark_funds), "", "") +
        ck_kpi_block("Sectors", str(len(r.sectors)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    f_tbl = _funds_table(r.funds)
    d_tbl = _distributions_table(r.distributions)
    s_tbl = _sectors_table(r.sectors)
    dr_tbl = _drought_table(r.drought_metrics)
    lp_tbl = _lp_requests_table(r.lp_requests)
    p_tbl = _exit_paths_table(r.exit_paths)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    q1q2_count = sum(1 for f in r.funds if f.quartile in (1, 2))
    active_requests = len(r.lp_requests)
    high_conf_exits = sum(1 for p in r.exit_paths if p.confidence == "high")

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">DPI / Distribution Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_funds} funds · weighted DPI {r.weighted_dpi:.2f}x / TVPI {r.weighted_tvpi:.2f}x · ${r.total_distributions_b:.2f}B distributions LTM · {r.below_benchmark_funds} funds below vintage benchmark · {active_requests} LP liquidity requests active — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Fund Vintage Performance — DPI, RVPI, TVPI, Benchmark Gap</div>{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Exit Drought — Market Metrics</div>{dr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Recent Distributions — Last 4 Quarters</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Path to Exit — Active Portfolio</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">LP Liquidity Requests</div>{lp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector DPI Rollup</div>{s_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">DPI Report Card:</strong> Weighted {r.weighted_dpi:.2f}x DPI across {r.total_funds} tracked funds — below the 1.20x needed at 7-year average hold to deliver median vintage returns.
    {r.below_benchmark_funds} of {r.total_funds} funds below their vintage DPI benchmark ({r.below_benchmark_funds / r.total_funds * 100:.0f}%) — concentrated in 2021-2023 vintages as exit market compressed.
    {q1q2_count} of {r.total_funds} tracked funds are top-half performers by TVPI — defensibility of healthcare alpha intact despite drought.
    {r.total_distributions_b:.2f}B in LTM distributions across portfolio — 48% secondary-buyout, 22% strategic sale, 18% dividend recap, 12% continuation vehicle — secondary/CV taking growing share vs historical 30% share.
    {active_requests} LP liquidity requests active; GPs responding with mix of continuation vehicles, dividend recaps, and accelerated exit sequencing — granular LP engagement is elevated.
    Pending path-to-exit pipeline ${r.pending_exits_m:,.1f}M projected value at weighted 2.55x MOIC; {high_conf_exits} of {len(r.exit_paths)} classified high-confidence — supports 2026-2027 distribution recovery thesis.
    Exit drought watchlist: dividend recaps +62% YoY (interim liquidity valve); secondary-buyout 48% (up 10pts); continuation vehicle $24.5B (up 119%) — mechanism mix shifts away from strategic sale.
  </div>
</div>"""

    return chartis_shell(body, "DPI Tracker", active_nav="/dpi-tracker", data_source="synthetic")