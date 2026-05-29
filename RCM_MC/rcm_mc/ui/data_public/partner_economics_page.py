"""Partner Economics page — /partner-economics."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_bar_row, ck_value_anchor, ck_source_purpose
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel

_PARTNER_ECON_NEEDED = [
    ("partner_name", "partner (PII)"),
    ("points_pct", "carry points %"),
    ("commitment", "GP commitment $"),
    ("draws_ytd", "draws YTD $"),
    ("distributions_ytd", "distributions YTD $"),
    ("vesting_pct", "vested %"),
]


def _exit_chart(items):
    """Summary chart — net exit proceeds by role (tone by MOIC on buy-in)."""
    def _tone(e):
        if e.moic_on_buy_in >= 3.0: return "positive"
        if e.moic_on_buy_in >= 2.0: return "teal"
        return "warning"
    top = sorted(items, key=lambda e: e.net_proceeds_mm, reverse=True)
    total = sum(e.net_proceeds_mm for e in top) or 1.0
    rows = [ck_bar_row(f"{e.role}",
            f"${e.net_proceeds_mm:,.2f}M net · {e.moic_on_buy_in:.2f}x",
            e.net_proceeds_mm / total * 100.0, tone=_tone(e)) for e in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of net exit proceeds '
            '· value = net ($M) + MOIC · tone = MOIC on buy-in</div></div>')


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
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(tiers):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.tier)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{t.target_partners}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${t.base_salary_k:,.0f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${t.quarterly_distributions_mm:,.3f}</td>',
            f'{ck_data_cell(f"""{t.equity_pct * 100:.3f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">${t.buy_in_value_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${t.annual_total_comp_k:,.0f}""", align="right", mono=True, weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cash_flow_table(cf) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Year","left"),("Salary ($K)","right"),("Distributions ($M)","right"),("Pretax Total ($M)","right"),("Fed Tax","right"),("State","right"),("SE Tax","right"),("Total Tax","right"),("After-Tax Take-Home ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, f in enumerate(cf):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""Year {f.year}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${f.salary_k:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${f.distributions_mm:,.3f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${f.total_cash_pretax_mm:,.3f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.federal_tax_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.state_tax_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.se_tax_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${f.total_tax_mm:,.3f}</td>',
            f'{ck_data_cell(f"""${f.after_tax_take_home_mm:,.3f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _buy_in_table(structures) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    cols = [("Structure","left"),("Buy-in ($M)","right"),("Source","left"),("Annual Cost ($M)","right"),("Years to Recoup","right"),("Risk","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(structures):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(s.risk, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.structure)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${s.buy_in_amount_mm:,.2f}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.financing_source)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if s.annual_cost_mm else text_dim}">${s.annual_cost_mm:,.3f}</td>',
            f'{ck_data_cell(f"""{s.years_to_recoup:.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{s.risk}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vs_table(rows) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    fav_colors = {"partner": P["positive"], "employee": P["negative"], "even": P["text_faint"]}
    cols = [("Metric","left"),("Employee","left"),("Partner","left"),("Delta","left"),("Favors","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        fc = fav_colors.get(r.favorable, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.metric)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.employee_value)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["accent"]}">{_html.escape(r.partner_value)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.delta)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{fc};border:1px solid {fc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{r.favorable}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exit_table(exits) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Role","left"),("Equity %","right"),("Gross Proceeds ($M)","right"),("Carry Paid ($M)","right"),("Tax ($M)","right"),("Net Proceeds ($M)","right"),("MOIC on Buy-in","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(exits):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if e.moic_on_buy_in >= 3 else (P["accent"] if e.moic_on_buy_in >= 2 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.role)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{e.equity_pct * 100:.3f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.gross_proceeds_mm:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${e.carry_paid_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${e.tax_on_proceeds_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${e.net_proceeds_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:600">{e.moic_on_buy_in:.2f}x</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _recruit_table(recruits) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    ret_colors = {
        "high — immediate equity": P["positive"], "high — defined path": P["positive"],
        "medium — longer runway": P["accent"], "low — high churn risk": P["negative"],
        "very low — gap coverage": P["negative"],
    }
    cols = [("Scenario","left"),("Years to Partner","right"),("Comp Y1 ($K)","right"),("Comp Partnership ($K)","right"),("5-yr Value ($M)","right"),("Retention Impact","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(recruits):
        rb = panel_alt if i % 2 == 0 else bg
        rc = ret_colors.get(r.retention_impact, text_dim)
        yr_str = f"{r.years_to_partner}" if r.years_to_partner < 10 else "never"
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.scenario)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{yr_str}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${r.all_in_comp_y1_k:,.0f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${r.all_in_comp_partnership_k:,.0f}</td>',
            f'{ck_data_cell(f"""${r.total_5yr_value_mm:,.2f}""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{rc}">{_html.escape(r.retention_impact)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    exit_chart = _exit_chart(r.exit_proceeds)
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

    page_title = ck_page_title(
        "Partner Economics / Physician Buy-in",
        eyebrow="PARTNER ECONOMICS",
        meta=f"""Partnership tiers, buy-in structures, tax flow, exit proceeds, recruitment economics — {r.corpus_deal_count:,} corpus deals""",
    )
    
    value_anchor = ck_value_anchor(
        "Partner Economics",
        f"${r.practice_ebitda_mm:,.1f}M practice EBITDA",
        delta=f"${r.practice_revenue_mm:,.0f}M revenue · {r.total_partners} partners · ${r.avg_partner_comp_k:,.0f}k avg comp",
        tone="teal",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {data_required_panel(P, title="Partner Economics", needed=_PARTNER_ECON_NEEDED,
      template="partner_economics_template.csv", request_from="Fund CFO / fund administrator",
      activates="carry waterfall, partner points roll-up, draws vs distributions",
      guide_hint="What partner-economics data do I need to upload?")}
  {ck_illustrative_note("figures")}
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Partner Compensation by Tier</div>{tier_svg}</div>
  <div style="{cell}"><div style="{h3}">Tier Structure Detail</div>{tiers_tbl}</div>
  <div style="{cell}"><div style="{h3}">Partner Cash Flow (Mid-Tier, After Tax)</div>{cf_tbl}</div>
  <div style="{cell}"><div style="{h3}">Buy-in Financing Structures</div>{buy_tbl}</div>
  <div style="{cell}"><div style="{h3}">Employee vs Partner Comparison</div>{vs_tbl}</div>
  <div style="{cell}"><div style="{h3}">Exit Proceeds at Sale ({hold}-yr hold)</div>{exit_chart}{exit_tbl}</div>
  <div style="{cell}"><div style="{h3}">Recruitment Pathway Economics</div>{rec_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Partner Thesis:</strong> {r.total_partners} partners with {r.physician_equity_pool_pct * 100:.0f}% equity pool.
    Avg partner comp ${r.avg_partner_comp_k:,.0f}K (salary + distributions). Mid-tier buy-in ${r.tiers[1].buy_in_value_mm if len(r.tiers) > 1 else 0:,.2f}M.
    Annual partner economics total ${r.annual_gp_cost_mm:,.1f}M — critical to structure correctly for recruitment AND retention.
  </div>
</div>"""

    body = ck_source_purpose(
        purpose="Model partner/physician buy-in economics and alignment.",
        universe="data-required", source="Illustrative model — no deal model attached",
        next_action="Enter the deal's partner-economics model") + body
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Partner Economics", active_nav="/partner-economics",
        editorial_intro={
            "eyebrow": "PARTNER ECONOMICS",
            "headline": "What the partner economics page reveals on this deal.",
            "italic_word": "reveals",
        })
