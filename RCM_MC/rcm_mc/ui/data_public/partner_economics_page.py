"""Partner Economics page — /partner-economics."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_svg(tiers) -> str:
    if not tiers: return ""
    w, h = 540, 180
    pad_l = 160; pad_r = 60
    row_h = 40
    inner_w = w - pad_l - pad_r
    max_comp = max(t.annual_total_comp_k for t in tiers) or 1
    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]; acc = P["accent"]; pos = P["positive"]
    bars = []
    for i, t in enumerate(tiers):
        y = 20 + i * row_h
        bh = 16
        bw_salary = t.base_salary_k / max_comp * inner_w
        bw_total = t.annual_total_comp_k / max_comp * inner_w
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh + 8}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(t.tier[:22])}</text>'
            f'<text x="{pad_l - 6}" y="{y + bh + 20}" fill="{text_faint}" font-size="9" text-anchor="end" font-family="JetBrains Mono,monospace">{t.target_partners} partners</text>'
            # Total bar (base)
            f'<rect x="{pad_l}" y="{y}" width="{bw_total:.1f}" height="{bh}" fill="{acc}" opacity="0.55"/>'
            # Salary (base) bar
            f'<rect x="{pad_l}" y="{y}" width="{bw_salary:.1f}" height="{bh}" fill="{pos}" opacity="0.85"/>'
            f'<text x="{pad_l + bw_total + 4:.1f}" y="{y + bh - 2}" fill="{P["text_dim"]}" font-size="10" font-family="JetBrains Mono,monospace">${t.annual_total_comp_k:,.0f}K</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<rect x="{pad_l}" y="4" width="10" height="10" fill="{pos}" opacity="0.85"/>'
            f'<text x="{pad_l + 14}" y="13" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Base Salary</text>'
            f'<rect x="{pad_l + 80}" y="4" width="10" height="10" fill="{acc}" opacity="0.55"/>'
            f'<text x="{pad_l + 94}" y="13" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">+ Distributions</text></svg>')


def _tiers_table(tiers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Tier","left"),("Partners","right"),("Base Salary ($K)","right"),("Qtrly Distributions ($M)","right"),("Equity %","right"),("Buy-in Value ($M)","right"),("Total Comp ($K)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(tiers):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(t.tier)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{t.target_partners}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${t.base_salary_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${t.quarterly_distributions_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.equity_pct * 100:.3f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">${t.buy_in_value_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${t.annual_total_comp_k:,.0f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cash_flow_table(cf) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Year","left"),("Salary ($K)","right"),("Distributions ($M)","right"),("Pretax Total ($M)","right"),("Fed Tax","right"),("State","right"),("SE Tax","right"),("Total Tax","right"),("After-Tax Take-Home ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(cf):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">Year {f.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${f.salary_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${f.distributions_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${f.total_cash_pretax_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.federal_tax_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.state_tax_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.se_tax_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${f.total_tax_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${f.after_tax_take_home_mm:,.3f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _buy_in_table(structures) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    cols = [("Structure","left"),("Buy-in ($M)","right"),("Source","left"),("Annual Cost ($M)","right"),("Years to Recoup","right"),("Risk","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(structures):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(s.risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.structure)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${s.buy_in_amount_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.financing_source)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if s.annual_cost_mm else text_dim}">${s.annual_cost_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.years_to_recoup:.1f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{s.risk}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vs_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    fav_colors = {"partner": P["positive"], "employee": P["negative"], "even": P["text_faint"]}
    cols = [("Metric","left"),("Employee","left"),("Partner","left"),("Delta","left"),("Favors","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        fc = fav_colors.get(r.favorable, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.metric)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.employee_value)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["accent"]}">{_html.escape(r.partner_value)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.delta)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{fc};border:1px solid {fc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{r.favorable}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exit_table(exits) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Role","left"),("Equity %","right"),("Gross Proceeds ($M)","right"),("Carry Paid ($M)","right"),("Tax ($M)","right"),("Net Proceeds ($M)","right"),("MOIC on Buy-in","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(exits):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if e.moic_on_buy_in >= 3 else (P["accent"] if e.moic_on_buy_in >= 2 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.equity_pct * 100:.3f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${e.gross_proceeds_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${e.carry_paid_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${e.tax_on_proceeds_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${e.net_proceeds_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:600">{e.moic_on_buy_in:.2f}x</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _recruit_table(recruits) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    ret_colors = {
        "high — immediate equity": P["positive"], "high — defined path": P["positive"],
        "medium — longer runway": P["accent"], "low — high churn risk": P["negative"],
        "very low — gap coverage": P["negative"],
    }
    cols = [("Scenario","left"),("Years to Partner","right"),("Comp Y1 ($K)","right"),("Comp Partnership ($K)","right"),("5-yr Value ($M)","right"),("Retention Impact","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(recruits):
        rb = panel_alt if i % 2 == 0 else bg
        rc = ret_colors.get(r.retention_impact, text_dim)
        yr_str = f"{r.years_to_partner}" if r.years_to_partner < 10 else "never"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.scenario)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{yr_str}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.all_in_comp_y1_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${r.all_in_comp_partnership_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${r.total_5yr_value_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{rc}">{_html.escape(r.retention_impact)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_partner_economics(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    rev = _f("revenue", 100.0)
    ebitda = _f("ebitda", 18.0)
    partners = _i("partners", 20)
    hold = _i("hold_years", 5)
    pool = _f("pool", 0.20)

    from rcm_mc.data_public.partner_economics import compute_partner_economics
    r = compute_partner_economics(practice_revenue_mm=rev, practice_ebitda_mm=ebitda,
                                    total_partners=partners, hold_years=hold,
                                    physician_equity_pool=pool)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Practice Revenue", f"${r.practice_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Practice EBITDA", f"${r.practice_ebitda_mm:,.1f}M", "", "") +
        ck_kpi_block("Partners", str(r.total_partners), "", "") +
        ck_kpi_block("Avg Comp", f"${r.avg_partner_comp_k:,.0f}K", "", "") +
        ck_kpi_block("Phys Equity Pool", f"{r.physician_equity_pool_pct * 100:.0f}%", "", "") +
        ck_kpi_block("Annual GP Cost", f"${r.annual_gp_cost_mm:,.1f}M", "", "") +
        ck_kpi_block("Tiers", str(len(r.tiers)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    tier_svg = _tier_svg(r.tiers)
    tiers_tbl = _tiers_table(r.tiers)
    cf_tbl = _cash_flow_table(r.cash_flow)
    buy_tbl = _buy_in_table(r.buy_in_structures)
    vs_tbl = _vs_table(r.emp_vs_partner)
    exit_tbl = _exit_table(r.exit_proceeds)
    rec_tbl = _recruit_table(r.recruitment)

    form = f"""
<form method="GET" action="/partner-economics" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)<input name="revenue" value="{rev}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">EBITDA ($M)<input name="ebitda" value="{ebitda}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Partners<input name="partners" value="{partners}" type="number" step="5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/></label>
  <label style="font-size:11px;color:{text_dim}">Hold Yrs<input name="hold_years" value="{hold}" type="number" min="3" max="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:50px"/></label>
  <label style="font-size:11px;color:{text_dim}">Equity Pool<input name="pool" value="{pool}" type="number" step="0.05" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Partner Economics / Physician Buy-in</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Partnership tiers, buy-in structures, tax flow, exit proceeds, recruitment economics — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Partner Compensation by Tier</div>{tier_svg}</div>
  <div style="{cell}"><div style="{h3}">Tier Structure Detail</div>{tiers_tbl}</div>
  <div style="{cell}"><div style="{h3}">Partner Cash Flow (Mid-Tier, After Tax)</div>{cf_tbl}</div>
  <div style="{cell}"><div style="{h3}">Buy-in Financing Structures</div>{buy_tbl}</div>
  <div style="{cell}"><div style="{h3}">Employee vs Partner Comparison</div>{vs_tbl}</div>
  <div style="{cell}"><div style="{h3}">Exit Proceeds at Sale ({hold}-yr hold)</div>{exit_tbl}</div>
  <div style="{cell}"><div style="{h3}">Recruitment Pathway Economics</div>{rec_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Partner Thesis:</strong> {r.total_partners} partners with {r.physician_equity_pool_pct * 100:.0f}% equity pool.
    Avg partner comp ${r.avg_partner_comp_k:,.0f}K (salary + distributions). Mid-tier buy-in ${r.tiers[1].buy_in_value_mm if len(r.tiers) > 1 else 0:,.2f}M.
    Annual partner economics total ${r.annual_gp_cost_mm:,.1f}M — critical to structure correctly for recruitment AND retention.
  </div>
</div>"""

    return chartis_shell(body, "Partner Economics", active_nav="/partner-economics")
