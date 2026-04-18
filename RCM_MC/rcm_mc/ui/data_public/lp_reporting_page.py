"""LP Reporting Dashboard — /lp-reporting."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _funds_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Fund","left"),("Vintage","right"),("Fund Size ($M)","right"),("Called %","right"),
            ("TVPI","right"),("DPI","right"),("RVPI","right"),("Net IRR","right"),("Quartile","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    q_c = {"top quartile": pos, "top decile": pos, "second quartile": acc, "third quartile": warn, "fourth quartile": P["negative"], "too early": text_dim}
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        qc = q_c.get(f.quartile, text_dim)
        tvpi_c = pos if f.tvpi >= 2.0 else (acc if f.tvpi >= 1.5 else text_dim)
        irr_c = pos if f.net_irr_pct >= 16 else (acc if f.net_irr_pct >= 12 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(f.fund)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{f.vintage}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${f.fund_size_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.called_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tvpi_c};font-weight:700">{f.tvpi:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{f.dpi:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{f.rvpi:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{irr_c};font-weight:700">{f.net_irr_pct:+.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{qc};border:1px solid {qc};border-radius:2px;letter-spacing:0.06em">{_html.escape(f.quartile)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _marks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Quarter","left"),("NAV ($M)","right"),("Δ %","right"),("Contribs ($M)","right"),
            ("Distribs ($M)","right"),("Cum DPI","right"),("Cum TVPI","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if m.quarterly_value_change_pct >= 0.03 else (acc if m.quarterly_value_change_pct >= 0.02 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.quarter)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${m.nav_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:600">{m.quarterly_value_change_pct * 100:+.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${m.contributions_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${m.distributions_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{m.cumulative_dpi:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{m.cumulative_tvpi:,.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _attribution_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Driver","left"),("Q Contribution ($M)","right"),("YTD Contribution ($M)","right"),
            ("% of Value Δ","right"),("Commentary","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if a.ytd_contribution_mm > 0 else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(a.driver)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c}">${a.quarterly_contribution_mm:+,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">${a.ytd_contribution_mm:+,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{a.pct_of_value_change * 100:+.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.commentary)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmarks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Metric","left"),("Fund","right"),("Q1 Bench","right"),("Q2 Bench","right"),
            ("Q3 Bench","right"),("Q4 Bench","right"),("Quartile","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
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
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{fmt(b.fund)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{fmt(b.q1_benchmark)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{fmt(b.q2_benchmark)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{fmt(b.q3_benchmark)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{fmt(b.q4_benchmark)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{qc};border:1px solid {qc};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.fund_quartile)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _companies_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Company","left"),("Sector","left"),("Cost Basis ($M)","right"),
            ("Current FV ($M)","right"),("Marked MOIC","right"),("YTD Δ","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    s_c = {"Active": pos, "Closing Q2 exit": pos, "Watch list": warn, "Held": acc}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = s_c.get(c.status, text_dim)
        m_c = pos if c.marked_moic >= 2.0 else (acc if c.marked_moic >= 1.5 else (warn if c.marked_moic >= 1.0 else neg))
        ytd_c = pos if c.ytd_valuation_change_pct > 0.08 else (acc if c.ytd_valuation_change_pct >= 0 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.company)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.cost_basis_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.current_fair_value_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{c.marked_moic:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ytd_c};font-weight:700">{c.ytd_valuation_change_pct * 100:+.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comms_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Date","left"),("Type","center"),("Topic","left"),("Status","center"),("Recipients","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    s_c = {"sent": pos, "completed": pos, "scheduled": acc, "in progress": warn}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = s_c.get(c.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{_html.escape(c.date)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.topic)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.recipients_count}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    f_tbl = _funds_table(r.funds)
    m_tbl = _marks_table(r.marks)
    a_tbl = _attribution_table(r.attribution)
    b_tbl = _benchmarks_table(r.benchmarks)
    c_tbl = _companies_table(r.companies)
    cm_tbl = _comms_table(r.communications)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    top_quartile = sum(1 for f in r.funds if f.quartile == "top quartile")
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">LP Reporting Dashboard</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{_html.escape(r.reporting_quarter)} · {r.fund_count} active funds · ${r.total_aum_mm:,.0f}M AUM · blended {r.blended_tvpi:.2f}x TVPI — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Fund-Level Performance Summary</div>{f_tbl}</div>
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

    return chartis_shell(body, "LP Reporting", active_nav="/lp-reporting")
