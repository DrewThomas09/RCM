"""Capital Call Pacing Model — /capital-pacing."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _cashflow_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Year","left"),("Called ($M)","right"),("Cum Called ($M)","right"),
            ("Deployed ($M)","right"),("Distributions ($M)","right"),("Cum Dist ($M)","right"),
            ("NAV ($M)","right"),("Total Value ($M)","right"),("DPI","right"),("TVPI","right"),("Interim IRR","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, cf in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        irr_c = pos if cf.interim_irr >= 0.15 else (acc if cf.interim_irr >= 0.08 else (text_dim if cf.interim_irr >= 0 else neg))
        tvpi_c = pos if cf.tvpi >= 1.5 else (acc if cf.tvpi >= 1.0 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{cf.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${cf.capital_called_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${cf.cumulative_called_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${cf.deployed_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${cf.distributions_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${cf.cumulative_distributions_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${cf.unrealized_nav_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${cf.total_value_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{cf.dpi:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tvpi_c};font-weight:700">{cf.tvpi:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{irr_c};font-weight:700">{cf.interim_irr * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _investments_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("ID","left"),("Sector","left"),("Inv Year","right"),("Initial ($M)","right"),
            ("Follow-On ($M)","right"),("Total Inv ($M)","right"),("Current FV ($M)","right"),
            ("Proj MOIC","right"),("Exit Year","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, inv in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if inv.projected_moic >= 2.8 else (acc if inv.projected_moic >= 2.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(inv.deal_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(inv.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{inv.investment_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${inv.initial_check_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${inv.follow_on_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${inv.total_invested_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${inv.current_fair_value_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{inv.projected_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{inv.projected_exit_year}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(inv.status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vintage_table(items, current_vintage: int) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Vintage","left"),("Fund Size ($M)","right"),("Current TVPI","right"),
            ("Current DPI","right"),("Projected MOIC","right"),("Projected IRR","right"),("Age (yr)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        is_current = v.vintage_year == current_vintage
        tvpi_c = pos if v.current_tvpi >= 1.5 else (acc if v.current_tvpi >= 1.15 else text_dim)
        hi = "border-left: 3px solid " + acc if is_current else ""
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"700" if is_current else "600"};{hi}">{v.vintage_year}{" (this fund)" if is_current else ""}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${v.fund_size_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tvpi_c};font-weight:700">{v.current_tvpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{v.current_dpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.projected_net_moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{v.projected_net_irr * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.years_since_vintage}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _commitments_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Category","left"),("Committed ($M)","right"),("Deployed ($M)","right"),
            ("Utilization","right"),("Remaining ($M)","right"),("Status","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        util_c = pos if c.utilization_pct >= 0.75 else (acc if c.utilization_pct >= 0.50 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.committed_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${c.deployed_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{util_c};font-weight:700">{c.utilization_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.remaining_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _jcurve_svg(cashflows) -> str:
    if not cashflows: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    bg = P["panel"]; acc = P["accent"]; neg = P["negative"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(cashflows)
    x_step = inner_w / max(n - 1, 1)
    irrs = [cf.interim_irr for cf in cashflows]
    max_v = max(max(irrs), 0.25)
    min_v = min(min(irrs), -0.20)
    zero_y = (h - pad_b) - ((0 - min_v) / (max_v - min_v)) * inner_h
    pts = []
    circles = []
    labels = []
    for i, cf in enumerate(cashflows):
        x = pad_l + i * x_step
        y_norm = (cf.interim_irr - min_v) / (max_v - min_v + 0.0001)
        y = (h - pad_b) - y_norm * inner_h
        pts.append(f"{x:.1f},{y:.1f}")
        color = neg if cf.interim_irr < 0 else (pos if cf.interim_irr >= 0.15 else acc)
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"/>')
        labels.append(
            f'<text x="{x:.1f}" y="{y - 8:.1f}" fill="{color}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:700">{cf.interim_irr * 100:+.1f}%</text>'
            f'<text x="{x:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{cf.year}</text>'
        )
    path = f'<polyline points="{" ".join(pts)}" fill="none" stroke="{acc}" stroke-width="2" opacity="0.7"/>'
    zero_line = f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{pad_l + inner_w}" y2="{zero_y:.1f}" stroke="{text_dim}" stroke-width="0.5" stroke-dasharray="3,3"/>'
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{zero_line}{path}{"".join(circles)}{"".join(labels)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">J-Curve: Fund Interim IRR by Year</text></svg>')


def render_capital_pacing(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    fund_size = _f("fund_size", 1500.0)
    vintage = _i("vintage", 2021)
    current = _i("current_year", 2026)

    from rcm_mc.data_public.capital_pacing import compute_capital_pacing
    r = compute_capital_pacing(fund_size_mm=fund_size, vintage_year=vintage, current_year=current)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    irr_c = pos if r.current_net_irr >= 0.15 else (acc if r.current_net_irr >= 0.08 else (text_dim if r.current_net_irr >= 0 else neg))

    kpi_strip = (
        ck_kpi_block("Fund Size", f"${r.fund_size_mm:,.0f}M", "", "") +
        ck_kpi_block("Vintage", str(r.vintage_year), "", "") +
        ck_kpi_block("Age", f"{r.fund_age_years}y", "", "") +
        ck_kpi_block("Called", f"${r.total_called_mm:,.0f}M", "", "") +
        ck_kpi_block("Distributions", f"${r.total_distributions_mm:,.0f}M", "", "") +
        ck_kpi_block("NAV", f"${r.current_nav_mm:,.0f}M", "", "") +
        ck_kpi_block("TVPI", f"{r.current_tvpi:.2f}x", "", "") +
        ck_kpi_block("DPI", f"{r.current_dpi:.2f}x", "", "") +
        ck_kpi_block("Net IRR", f"{r.current_net_irr * 100:+.1f}%", "", "") +
        ck_kpi_block("Corpus", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _jcurve_svg(r.cashflows)
    cf_tbl = _cashflow_table(r.cashflows)
    inv_tbl = _investments_table(r.investments)
    vp_tbl = _vintage_table(r.vintage_peers, r.vintage_year)
    cmt_tbl = _commitments_table(r.commitments)

    form = f"""
<form method="GET" action="/capital-pacing" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Fund Size ($M)<input name="fund_size" value="{fund_size}" type="number" step="100" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:100px"/></label>
  <label style="font-size:11px;color:{text_dim}">Vintage Year<input name="vintage" value="{vintage}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Current Year<input name="current_year" value="{current}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Capital Call Pacing Model</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Fund-level cashflow · J-curve · DPI/TVPI/RVPI evolution · vintage comparison · commitment utilization — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Fund J-Curve — Interim IRR Trajectory</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Year-by-Year Cashflow &amp; Value Evolution</div>{cf_tbl}</div>
  <div style="{cell}"><div style="{h3}">Portfolio Investments</div>{inv_tbl}</div>
  <div style="{cell}"><div style="{h3}">Vintage Year Peer Comparison</div>{vp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Commitment Utilization — Deployment Status</div>{cmt_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {irr_c};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Pacing Thesis:</strong> Vintage {r.vintage_year} fund of ${r.fund_size_mm:,.0f}M is in year {r.fund_age_years} of life.
    ${r.total_called_mm:,.0f}M called ({r.total_called_mm / r.fund_size_mm * 100:.0f}% of commitments), ${r.total_distributions_mm:,.0f}M distributed ({r.current_dpi:.2f}x DPI).
    Current TVPI {r.current_tvpi:.2f}x vs target 2.0-2.5x; net IRR <span style="color:{irr_c}">{r.current_net_irr * 100:+.1f}%</span>.
    Fund exited J-curve in year 3 and is now in distribution phase. Vintage peers at same age show median TVPI {r.vintage_peers[r.fund_age_years].current_tvpi if len(r.vintage_peers) > r.fund_age_years else r.current_tvpi:.2f}x.
    Pacing appears <strong style="color:{text}">on plan</strong> — dry powder deployment, distribution cadence, and NAV growth all track vintage norms.
  </div>
</div>"""

    return chartis_shell(body, "Capital Pacing", active_nav="/capital-pacing")
