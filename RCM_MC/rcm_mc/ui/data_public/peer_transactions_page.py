"""Peer Transaction Database / Comps Library — /peer-transactions."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell


def _trend_color(t: str) -> str:
    return {
        "expanding": P["positive"],
        "stable": P["accent"],
        "compressing": P["warning"],
    }.get(t, P["text_dim"])


def _deals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Date","right"),("Target","left"),("Buyer","left"),("Sector","left"),
            ("Size ($M)","right"),("Revenue ($M)","right"),("EBITDA ($M)","right"),
            ("EV / Rev","right"),("EV / EBITDA","right"),("D/E","right"),("Type","center"),("Advisor","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = pos if d.ev_ebitda_x >= 16 else (acc if d.ev_ebitda_x >= 13 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.announce_date)}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{_html.escape(d.target)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(d.buyer)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'{ck_data_cell(f"""${d.deal_size_m:,.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${d.revenue_m:,.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${d.ebitda_m:,.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{d.ev_revenue_x:.2f}x""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{d.ev_ebitda_x:.2f}x</td>',
            f'{ck_data_cell(f"""{d.debt_equity_ratio:.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(d.deal_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.advisor)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _multiples_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sector","left"),("Transactions","right"),("Median EV/EBITDA","right"),
            ("P25","right"),("P75","right"),("Median EV/Rev","right"),("Growth %","right"),("Trend","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _trend_color(s.trend)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.sector)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.transactions}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{s.median_ev_ebitda_x:.2f}x""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{s.p25_ev_ebitda_x:.2f}x""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.p75_ev_ebitda_x:.2f}x""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.median_ev_revenue_x:.2f}x""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{s.median_growth_rate_pct * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.trend)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _types_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal Type","left"),("Transactions","right"),("Median Size ($M)","right"),
            ("Median EV/EBITDA","right"),("Hold Period","right"),("Leverage","right"),("Typical Exit","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m = t.median_ev_ebitda_x if isinstance(t.median_ev_ebitda_x, (int, float)) else "n/a"
        m_str = f"{m:.2f}x" if isinstance(m, (int, float)) else m
        h = t.typical_holding_period if isinstance(t.typical_holding_period, (int, float)) else "n/a"
        h_str = f"{h:.1f}y" if isinstance(h, (int, float)) else h
        lev = t.typical_leverage if isinstance(t.typical_leverage, (int, float)) else 0
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.deal_type)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{t.transactions}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${t.median_size_m:,.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{m_str}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{h_str}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{lev:.2f}x""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.typical_exit)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _buyers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Buyer Category","left"),("Transactions","right"),("Median Size ($M)","right"),
            ("Median EV/EBITDA","right"),("Most Active Sectors","left"),("Typical Structure","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.buyer_category)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{b.transactions}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${b.median_deal_size_m:,.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{b.median_ev_ebitda_x:.2f}x""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(b.sectors_most_active)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(b.typical_structure)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _trends_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Period","left"),("Deals","right"),("Volume ($B)","right"),
            ("Median Multiple","right"),("Strategic %","right"),("Sponsor %","right"),("Cross-Border %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.period)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{t.total_deals}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${t.total_volume_b:.2f}B""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{t.median_multiple:.2f}x""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{t.strategic_pct * 100:.0f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{t.sponsor_pct * 100:.0f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{t.cross_border_pct * 100:.0f}%""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _advisors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Advisor","left"),("Type","left"),("Transactions LTM","right"),
            ("Total Volume ($B)","right"),("Median Deal ($M)","right"),("Sector Strengths","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.advisor)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.advisor_type)}</td>',
            f'{ck_data_cell(f"""{a.transactions_ltm}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${a.total_volume_b:.2f}B""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${a.median_deal_size_m:,.1f}M""", align="right", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(a.sector_strengths)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_peer_transactions(params: dict = None) -> str:
    from rcm_mc.data_public.peer_transactions import compute_peer_transactions
    r = compute_peer_transactions()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Comparable Deals", str(r.total_transactions), "", "") +
        ck_kpi_block("Total Volume", f"${r.total_volume_b:.2f}B", "", "") +
        ck_kpi_block("Median EV/EBITDA", f"{r.median_ev_ebitda:.2f}x", "", "") +
        ck_kpi_block("Median EV/Revenue", f"{r.median_ev_revenue:.2f}x", "", "") +
        ck_kpi_block("Sectors Tracked", str(len(r.sector_multiples)), "", "") +
        ck_kpi_block("Buyer Categories", str(len(r.buyers)), "", "") +
        ck_kpi_block("Advisor League", str(len(r.advisors)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    d_tbl = _deals_table(r.deals)
    s_tbl = _multiples_table(r.sector_multiples)
    t_tbl = _types_table(r.deal_types)
    b_tbl = _buyers_table(r.buyers)
    tr_tbl = _trends_table(r.trends)
    a_tbl = _advisors_table(r.advisors)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    expanding = sum(1 for s in r.sector_multiples if s.trend == "expanding")
    compressing = sum(1 for s in r.sector_multiples if s.trend == "compressing")
    latest = r.trends[-1] if r.trends else None
    latest_info = f"{latest.period}: {latest.total_deals} deals, ${latest.total_volume_b:.2f}B, {latest.median_multiple:.2f}x median" if latest else "n/a"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Peer Transaction Database / Comps Library</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_transactions} comparable transactions · ${r.total_volume_b:.2f}B aggregate value · median {r.median_ev_ebitda:.2f}x EV/EBITDA · {r.median_ev_revenue:.2f}x EV/Revenue · {latest_info} — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Recent Comparable Transactions</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector Multiples — 2022-2025 Aggregated</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Deal Type Breakdown</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Buyer Category Analysis</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Quarterly Market Trends</div>{tr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Advisor League Tables — Healthcare PE</div>{a_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Peer Comparables Summary:</strong> {r.total_transactions} comparable transactions aggregate ${r.total_volume_b:.2f}B with median {r.median_ev_ebitda:.2f}x EV/EBITDA and {r.median_ev_revenue:.2f}x EV/Revenue.
    Multiple expanding in {expanding} sectors (Primary Care VBC, Infusion, Women's Health / Fertility) driven by demographic tailwinds + value-based care conviction.
    Multiple compressing in {compressing} sectors (Dermatology, Dental DSO, Home Health, Radiology, Hospital-based) as market sentiment re-rates.
    Top-multiple transactions: ChenMed (Humana minority, 43.9x) and Privia (Blackstone secondary, 20.8x) — both VBC primary care plays with growth equity economics.
    Most active buyers: mid-market PE (125 deals, 13.85x median), large PE (52 deals, 15.25x), lower middle-market PE (95 deals, 12.25x); strategic payers pay 18.25x premium.
    Advisor landscape: bulge bracket (Goldman, JPM, MS, BofA) dominates >$1B deals; Jefferies, Houlihan, Edgemont, Triple Tree, Cain Brothers specialty-strong in middle market.
  </div>
</div>"""

    return chartis_shell(body, "Peer Transactions", active_nav="/peer-transactions",
        editorial_intro={
            "eyebrow": "PEER TRANSACTIONS",
            "headline": "What the peer transactions page reveals on this deal.",
            "italic_word": "reveals",
        })
