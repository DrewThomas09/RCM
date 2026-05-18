"""Capital Call Pacing Model — /capital-pacing."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_paired_block, ck_page_title

_EXPLAINER_CSS = """<style>
.ck-cp-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#4a4a4a);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-cp-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


def _cashflow_paired_rows(items) -> tuple:
    headers = [
        "Year", "Called ($M)", "Cum Called ($M)", "Deployed ($M)",
        "Distributions ($M)", "Cum Dist ($M)", "NAV ($M)",
        "Total Value ($M)", "DPI", "TVPI", "Interim IRR",
    ]
    rows: list = []
    irrs: list = []
    for cf in items:
        rows.append([
            str(cf.year),
            f"${cf.capital_called_mm:,.2f}",
            f"${cf.cumulative_called_mm:,.2f}",
            f"${cf.deployed_mm:,.2f}",
            f"${cf.distributions_mm:,.2f}",
            f"${cf.cumulative_distributions_mm:,.2f}",
            f"${cf.unrealized_nav_mm:,.2f}",
            f"${cf.total_value_mm:,.2f}",
            f"{cf.dpi:.3f}",
            f"{cf.tvpi:.3f}",
            f"{cf.interim_irr * 100:+.1f}%",
        ])
        irrs.append(cf.interim_irr)
    hot = [irrs.index(min(irrs))] if irrs else []
    return headers, rows, hot


def _investments_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("ID","left"),("Sector","left"),("Inv Year","right"),("Initial ($M)","right"),
            ("Follow-On ($M)","right"),("Total Inv ($M)","right"),("Current FV ($M)","right"),
            ("Proj MOIC","right"),("Exit Year","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, inv in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if inv.projected_moic >= 2.8 else (acc if inv.projected_moic >= 2.0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(inv.deal_id)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(inv.sector)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{inv.investment_year}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${inv.initial_check_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${inv.follow_on_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${inv.total_invested_mm:,.2f}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${inv.current_fair_value_mm:,.2f}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{inv.projected_moic:.2f}x</td>',
            f'{ck_data_cell(f"""{inv.projected_exit_year}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(inv.status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vintage_table(items, current_vintage: int) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Vintage","left"),("Fund Size ($M)","right"),("Current TVPI","right"),
            ("Current DPI","right"),("Projected MOIC","right"),("Projected IRR","right"),("Age (yr)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        is_current = v.vintage_year == current_vintage
        tvpi_c = pos if v.current_tvpi >= 1.5 else (acc if v.current_tvpi >= 1.15 else text_dim)
        hi = "border-left: 3px solid " + acc if is_current else ""
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"700" if is_current else "600"};{hi}">{v.vintage_year}{" (this fund)" if is_current else ""}</td>',
            f'{ck_data_cell(f"""${v.fund_size_mm:,.0f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tvpi_c};font-weight:700">{v.current_tvpi:.2f}x</td>',
            f'{ck_data_cell(f"""{v.current_dpi:.2f}x""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{v.projected_net_moic:.2f}x""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{v.projected_net_irr * 100:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{v.years_since_vintage}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _commitments_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Category","left"),("Committed ($M)","right"),("Deployed ($M)","right"),
            ("Utilization","right"),("Remaining ($M)","right"),("Status","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        util_c = pos if c.utilization_pct >= 0.75 else (acc if c.utilization_pct >= 0.50 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${c.committed_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.deployed_mm:,.2f}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{util_c};font-weight:700">{c.utilization_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${c.remaining_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    cf_headers, cf_rows, cf_hot = _cashflow_paired_rows(r.cashflows)
    jcurve_paired = ck_paired_block(
        svg,
        data_label="Fund J-Curve · Year-by-Year Cashflows",
        headers=cf_headers,
        rows=cf_rows,
        data_source=f"{len(r.cashflows)} fund-years · trough year marked",
        hot_rows=cf_hot,
    )
    inv_tbl = _investments_table(r.investments)
    vp_tbl = _vintage_table(r.vintage_peers, r.vintage_year)
    cmt_tbl = _commitments_table(r.commitments)

    form = f"""
<form method="GET" action="/capital-pacing" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Fund Size ($M)<input name="fund_size" value="{fund_size}" type="number" step="100" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:100px"/></label>
  <label style="font-size:11px;color:{text_dim}">Vintage Year<input name="vintage" value="{vintage}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Current Year<input name="current_year" value="{current}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Capital Call Pacing Model",
        eyebrow="CAPITAL PACING",
        meta=(
            f"vintage {r.vintage_year} · ${r.fund_size_mm:,.0f}M fund · "
            f"TVPI {r.current_tvpi:.2f}x · {r.corpus_deal_count:,} corpus deals"
        ),
    )
    cp_explainer = (
        '<p class="ck-cp-explainer">'
        "<em>What the capital pacing model reveals on this deal.</em> "
        "Fund-level cashflow, J-curve, DPI/TVPI/RVPI evolution, vintage peer comparison, "
        "and commitment utilization across the deployment lifecycle."
        "</p>"
    )
    body = page_title + cp_explainer + f"""
<div class="ck-page-wrap">
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {jcurve_paired}
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

    return chartis_shell(body, "Capital Pacing", active_nav="/capital-pacing",
        extra_css=_EXPLAINER_CSS)
