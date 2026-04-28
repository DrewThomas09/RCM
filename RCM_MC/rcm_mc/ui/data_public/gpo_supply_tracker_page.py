"""GPO / Supply Chain Savings Tracker — /gpo-supply."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell


def _tier_color(t: str) -> str:
    return {
        "national tier-1": P["positive"],
        "national tier-2": P["accent"],
        "regional": P["accent"],
        "PE specialist": P["positive"],
        "direct": P["warning"],
    }.get(t, P["text_dim"])


def _status_color(s: str) -> str:
    return {
        "active": P["accent"],
        "renewed": P["positive"],
        "renewing (favorable)": P["positive"],
        "renewing (flat)": P["accent"],
        "renewing (slight inflation)": P["warning"],
        "executing": P["accent"],
        "executed": P["positive"],
        "closing": P["accent"],
    }.get(s, P["text_dim"])


def _affiliations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("GPO","left"),("Parent","left"),("Deals","right"),("Annual Spend ($M)","right"),
            ("Realized Savings ($M)","right"),("Savings %","right"),("Rebate %","right"),
            ("Contracts","right"),("Tier","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _tier_color(a.tier)
        s_c = pos if a.savings_rate_pct >= 0.15 else (acc if a.savings_rate_pct >= 0.12 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.gpo_name)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.parent)}</td>',
            f'{ck_data_cell(f"""{a.portfolio_deals}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${a.annual_spend_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${a.realized_savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{a.savings_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{a.rebate_rate_pct * 100:.1f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{a.contract_count}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(a.tier)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _categories_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Category","left"),("Annual Spend ($M)","right"),("Savings Rate","right"),
            ("Portfolio Savings ($M)","right"),("Rebate %","right"),("Top Contract","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.category)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.annual_spend_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.savings_rate_pct * 100:.1f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${c.portfolio_savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{c.rebate_pct * 100:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.top_contract)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _deals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Sector","left"),("Spend ($M)","right"),("GPO","left"),
            ("Gross Savings ($M)","right"),("Rebates ($M)","right"),("Net Savings ($M)","right"),
            ("% vs Benchmark","right"),("Compliance","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if d.compliance_pct >= 0.93 else (acc if d.compliance_pct >= 0.90 else warn)
        s_c = pos if d.savings_vs_benchmark_pct >= 0.17 else (acc if d.savings_vs_benchmark_pct >= 0.13 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'{ck_data_cell(f"""${d.annual_spend_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(d.gpo)}</td>',
            f'{ck_data_cell(f"""${d.gross_savings_m:.1f}M""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${d.rebate_capture_m:.1f}M""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${d.net_savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{d.savings_vs_benchmark_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{d.compliance_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _contracts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Contract","left"),("Vendor","left"),("Category","left"),("Annual Spend ($M)","right"),
            ("Deals","right"),("Δ vs Reference","right"),("Expires","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(c.renewal_status)
        d_c = pos if c.reference_price_delta_pct <= -0.15 else (acc if c.reference_price_delta_pct <= -0.10 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.contract)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.vendor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.category)}</td>',
            f'{ck_data_cell(f"""${c.annual_spend_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.portfolio_deals}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{c.reference_price_delta_pct * 100:+.1f}%</td>',
            f'{ck_data_cell(f"""{_html.escape(c.expires)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.renewal_status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _bulk_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Initiative","left"),("Sector","left"),("Deals","right"),("Aggregated Volume ($M)","right"),
            ("Incremental Savings ($M)","right"),("Cycle (days)","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(b.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.initiative)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.sector)}</td>',
            f'{ck_data_cell(f"""{b.deals_participating}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${b.aggregated_volume_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${b.incremental_savings_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{b.cycle_days}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _inflation_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Category","left"),("YTD Price Δ","right"),("Expected YTD","right"),
            ("Hedging Strategy","left"),("Portfolio Exposure ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        delta = p.ytd_price_change_pct - p.expected_ytd_change_pct
        y_c = pos if delta <= -1.0 else (acc if delta <= 0 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.category)}""", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{y_c};font-weight:700">+{p.ytd_price_change_pct:.1f}%</td>',
            f'{ck_data_cell(f"""+{p.expected_ytd_change_pct:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.hedging_strategy)}</td>',
            f'{ck_data_cell(f"""${p.portfolio_exposure_m:.1f}M""", align="right", mono=True, weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_gpo_supply_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.gpo_supply_tracker import compute_gpo_supply_tracker
    r = compute_gpo_supply_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Annual Spend", f"${r.total_annual_spend_m:,.1f}M", "", "") +
        ck_kpi_block("Net Savings", f"${r.total_realized_savings_m:.1f}M", "", "") +
        ck_kpi_block("Savings Rate", f"{r.average_savings_rate_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Rebate Capture", f"${r.total_rebates_m:.1f}M", "", "") +
        ck_kpi_block("Deals Covered", str(r.portfolio_deals_covered), "", "") +
        ck_kpi_block("Active Contracts", str(r.contracts_active), "", "") +
        ck_kpi_block("Bulk Buys", str(len(r.bulk_buys)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    a_tbl = _affiliations_table(r.affiliations)
    c_tbl = _categories_table(r.categories)
    d_tbl = _deals_table(r.deals)
    ct_tbl = _contracts_table(r.contracts)
    b_tbl = _bulk_table(r.bulk_buys)
    i_tbl = _inflation_table(r.inflation)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    bulk_incremental = sum(b.incremental_savings_m for b in r.bulk_buys)

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">GPO / Supply Chain Savings Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">${r.total_annual_spend_m:,.1f}M annual supply-chain spend across {r.portfolio_deals_covered} deals · ${r.total_realized_savings_m:.1f}M net savings ({r.average_savings_rate_pct * 100:.1f}% rate) · ${r.total_rebates_m:.1f}M rebate capture · {r.contracts_active} active contracts — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">GPO Affiliations — Scale, Savings, Rebates</div>{a_tbl}</div>
  <div style="{cell}"><div style="{h3}">Spend Categories — Savings Rate by Category</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Deal-Level Savings & Compliance</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Key Contracts — Reference Price, Renewal</div>{ct_tbl}</div>
  <div style="{cell}"><div style="{h3}">Cross-Portfolio Bulk-Buy Initiatives</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Inflation Watch — Category Price Pressure</div>{i_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Supply Chain Program Summary:</strong> ${r.total_annual_spend_m:,.1f}M aggregated supply-chain spend captures ${r.total_realized_savings_m:.1f}M in net savings at {r.average_savings_rate_pct * 100:.1f}% blended rate — materially above 11-13% industry benchmark for single-platform PE scale.
    PE-Specific GPO (Umbrella) and Vizient drive 75%+ of portfolio savings — Umbrella at 16.0% savings rate vs 13.5% for Vizient standard contracts reflects bulk-buy aggregation power.
    Implants / Devices (16.5% savings) and Medical/Surgical Supplies (14.5%) are the highest-value categories; pharmacy (8.5%) benefits from rebate economics but thinner gross savings.
    Bulk-buy initiatives incremental ${bulk_incremental:.1f}M on top of base GPO savings — ortho implant bulk purchase ($6.5M) and Epic licensing consolidation ($5.5M) are the two largest cross-portfolio wins.
    Inflation watch: staffing (+8.5%), insurance (+9.5%), and utilities (+6.8%) running above expected; hedging via direct contracts, captive insurance, and fixed-price energy ceilings largely in place.
    Compliance averages 92% across portfolio — Cedar (95.5%), Laurel (95.0%), and Aspen (94.0%) highest; Linden and Redwood (89-89.5%) present remediation opportunity worth ~$1.5M.
  </div>
</div>"""

    return chartis_shell(body, "GPO / Supply Tracker", active_nav="/gpo-supply",
        editorial_intro={
            "eyebrow": "GPO SUPPLY TRACKER",
            "headline": "What the gpo supply tracker page reveals on this deal.",
            "italic_word": "reveals",
        })
