"""Secondaries / GP-Led Tracker — /secondaries-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _transactions_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Transaction","left"),("Structure","center"),("GP Sponsor","left"),("Asset","left"),
            ("Vintage","right"),("Close Year","right"),("Size ($M)","right"),("NAV Premium/Disc","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if t.nav_premium_discount_pct >= 0 else (neg if t.nav_premium_discount_pct <= -0.08 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(t.transaction)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(t.structure)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(t.gp_sponsor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.asset)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{t.vintage}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.close_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${t.transaction_size_mm:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:600">{t.nav_premium_discount_pct * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _buyers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Buyer","left"),("Type","center"),("AUM ($B)","right"),("Typical Check ($M)","right"),
            ("Focus","left"),("Recent Close","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        aum_c = pos if b.aum_b >= 50 else acc
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.buyer)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(b.buyer_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{aum_c};font-weight:700">${b.aum_b:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${b.typical_check_mm:,.0f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.focus)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos}">{_html.escape(b.recent_close)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cv_econ_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Component","left"),("Mechanics","left"),("Typical Value","left"),("Key Consideration","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.component)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.mechanics)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(c.typical_value)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.key_consideration)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _conflicts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Conflict Area","left"),("Description","left"),("Mitigation","left"),("LPAC Vote Needed","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        v_c = neg if c.lpac_vote_needed else pos
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.conflict_area)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["accent"]}">{_html.escape(c.mitigation)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{v_c};font-weight:700">{"YES" if c.lpac_vote_needed else "NO"}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _deals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Deal","left"),("Type","center"),("Sector","left"),("NAV ($M)","right"),
            ("LP Options","left"),("Close Date","center"),("Lead Buyers","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.deal_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.deal_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(d.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${d.nav_mm:,.0f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.holder_offered_options)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{_html.escape(d.close_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.lead_buyers)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _trends_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Metric","left"),("2020","right"),("2022","right"),("2024","right"),("Trend","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    t_c = {"expanding": pos, "dominant": pos, "rising": pos, "improved": pos, "now standard": pos}
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = t_c.get(t.trend, text_dim)
        is_pct = t.y2024 < 1.5 and t.y2024 > 0
        def fmt(v):
            if is_pct: return f"{v * 100:.1f}%"
            if v >= 1: return f"{v:,.1f}"
            return f"{v:,.2f}"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(t.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{fmt(t.y2020)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{fmt(t.y2022)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{fmt(t.y2024)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.trend)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_secondaries_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.secondaries_tracker import compute_secondaries_tracker
    r = compute_secondaries_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("GP-Led 2024", f"${r.total_gp_led_volume_2024_b:.0f}B", "", "") +
        ck_kpi_block("Single-Asset CV Share", f"{r.single_asset_cv_share_pct * 100:.0f}%", "", "") +
        ck_kpi_block("Avg NAV Discount", f"{r.typical_nav_premium_discount_pct * 100:+.1f}%", "", "") +
        ck_kpi_block("Active Transactions", str(len(r.transactions)), "", "") +
        ck_kpi_block("Active Buyers", str(len(r.buyers)), "", "") +
        ck_kpi_block("Recent Deals", str(len(r.deals)), "", "") +
        ck_kpi_block("Conflict Areas", str(len(r.conflicts)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    t_tbl = _transactions_table(r.transactions)
    b_tbl = _buyers_table(r.buyers)
    ce_tbl = _cv_econ_table(r.cv_economics)
    cf_tbl = _conflicts_table(r.conflicts)
    d_tbl = _deals_table(r.deals)
    tr_tbl = _trends_table(r.trends)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    lpac_required = sum(1 for c in r.conflicts if c.lpac_vote_needed)
    total_vol = sum(t.transaction_size_mm for t in r.transactions)

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Secondaries / GP-Led Market Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Continuation vehicles · strip sales · tender offers · buyer landscape · CV economics · LP conflicts — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Recent Healthcare Secondaries Transactions</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Secondary Buyer Landscape</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">CV Economics Structure</div>{ce_tbl}</div>
  <div style="{cell}"><div style="{h3}">LP/GP Conflict Areas</div>{cf_tbl}</div>
  <div style="{cell}"><div style="{h3}">Active GP-Led Deal Calendar</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Trends 2020-2024</div>{tr_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Secondaries Thesis:</strong> GP-led market has grown from ~$48B (2020) to ~$98B (2024);
    single-asset CVs now dominate 52% of GP-led volume vs 22% in 2020. Average NAV discount {r.typical_nav_premium_discount_pct * 100:+.1f}% across the sample set.
    Healthcare is ~28% of total GP-led activity — dialysis, HCIT/SaaS, behavioral, specialty pharmacy leading sectors.
    CV structures allow sponsors to extend hold on winning assets while providing existing LPs liquidity optionality (roll/sell/strip).
    Fairness opinions now standard; LPAC consent required for {lpac_required} of {len(r.conflicts)} material conflict areas.
    Total recent transaction volume across tracked deals ${total_vol:,.0f}M; buyer demand remains strong, though pricing has softened -2% to -5% NAV discount.
    Use as exit alternative alongside strategic sale, sponsor-to-sponsor, and IPO paths in /platform-maturity.
  </div>
</div>"""

    return chartis_shell(body, "Secondaries", active_nav="/secondaries-tracker")
