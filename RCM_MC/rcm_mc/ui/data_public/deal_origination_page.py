"""Deal Origination / M&A Pipeline Tracker — /deal-origination."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _pipeline_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Deal","left"),("Sector","left"),("Stage","center"),("Est EV ($M)","right"),
            ("Target EBITDA ($M)","right"),("Entry Mult","right"),("Prob","right"),
            ("Weighted EV ($M)","right"),("Source","left"),("Owner","center"),("Next Milestone","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    stage_c = {"Screening": text_dim, "Diligence": acc, "IC Review": warn, "LOI": pos, "Closing": pos}
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stage_c.get(p.stage, text_dim)
        prob_c = pos if p.probability_pct >= 0.60 else (acc if p.probability_pct >= 0.40 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.deal_name[:30])}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(p.sector[:22])}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.est_ev_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.target_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{p.entry_multiple_proposed:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{prob_c};font-weight:700">{p.probability_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.weighted_ev_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(p.source)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(p.owner)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.next_milestone_date)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _bankers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Banker Firm","left"),("Type","left"),("Seen LTM","right"),("Engaged","right"),
            ("Won","right"),("Win Rate","right"),("Avg Deal ($M)","right"),("Relationship","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rel_c = pos if b.relationship_score >= 80 else (acc if b.relationship_score >= 70 else text_dim)
        wr_c = pos if b.win_rate_pct >= 0.22 else (acc if b.win_rate_pct >= 0.18 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.banker_firm)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(b.banker_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{b.deals_seen_ltm}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.deals_engaged_ltm}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{b.deals_won_ltm}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{wr_c};font-weight:600">{b.win_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${b.avg_deal_size_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rel_c};font-weight:700">{b.relationship_score}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _whitespace_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Sector","left"),("Active Targets","right"),("Platforms Deployed","right"),
            ("Concentration","right"),("Whitespace Score","right"),("Priority","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    pri_c = {"high": pos, "medium": acc, "low": text_dim}
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = pri_c.get(w.priority, text_dim)
        ws_c = pos if w.whitespace_score >= 75 else (acc if w.whitespace_score >= 55 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(w.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{w.active_targets}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{w.platforms_deployed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{w.concentration_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ws_c};font-weight:700">{w.whitespace_score}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(w.priority)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _winloss_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Category","left"),("Won","right"),("Lost - Price","right"),("Lost - Strategy","right"),
            ("Lost - Relationship","right"),("Rate","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, wl in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(wl.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{wl.won}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{wl.lost_price}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{wl.lost_strategy}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{wl.lost_seller_relationship}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{wl.pass_rate_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _velocity_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Quarter","left"),("Screened","right"),("Diligenced","right"),
            ("LOI Signed","right"),("Closed","right"),("Conversion","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(v.quarter)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.deals_screened}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.deals_diligenced}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{v.loi_signed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{v.closed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{v.conversion_rate_pct * 100:.2f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _funnel_svg(vel) -> str:
    if not vel: return ""
    w, h = 560, 200
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 40
    inner_w = w - pad_l - pad_r
    bg = P["panel"]; acc = P["accent"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    latest = vel[-1]
    funnel = [("Screened", latest.deals_screened), ("Diligenced", latest.deals_diligenced),
              ("LOI Signed", latest.loi_signed), ("Closed", latest.closed)]
    max_v = funnel[0][1]
    bar_h = 25
    gap = 12
    elts = [f'<rect width="{w}" height="{h}" fill="{bg}"/>',
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Latest Quarter Funnel ({_html.escape(latest.quarter)})</text>']
    for i, (label, val) in enumerate(funnel):
        y = 40 + i * (bar_h + gap)
        bw = val / max_v * inner_w
        x = pad_l + (inner_w - bw) / 2
        elts.append(f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="{bar_h}" fill="{acc}" opacity="{0.85 - i * 0.15}"/>')
        elts.append(f'<text x="{x + bw / 2:.1f}" y="{y + bar_h * 0.7}" fill="#fff" font-size="11" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:700">{val} {label}</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">{"".join(elts)}</svg>'


def render_deal_origination(params: dict = None) -> str:
    from rcm_mc.data_public.deal_origination import compute_deal_origination
    r = compute_deal_origination()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Active Pipeline", f"${r.total_pipeline_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Weighted Pipeline", f"${r.weighted_pipeline_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Active Deals", str(r.active_deals), "", "") +
        ck_kpi_block("LOI Stage", str(r.loi_stage), "", "") +
        ck_kpi_block("Closing", str(r.closing_stage), "", "") +
        ck_kpi_block("Bankers", str(len(r.bankers)), "", "") +
        ck_kpi_block("Whitespace Sectors", str(len([w for w in r.whitespace if w.whitespace_score >= 75])), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    funnel_svg = _funnel_svg(r.velocity)
    pl_tbl = _pipeline_table(r.pipeline)
    bk_tbl = _bankers_table(r.bankers)
    ws_tbl = _whitespace_table(r.whitespace)
    wl_tbl = _winloss_table(r.winloss)
    vl_tbl = _velocity_table(r.velocity)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Deal Origination / M&amp;A Pipeline Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Active pipeline · probability-weighted EV · banker relationship matrix · sector whitespace · sourcing velocity — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Sourcing Funnel — Latest Quarter</div>{funnel_svg}</div>
  <div style="{cell}"><div style="{h3}">Active Pipeline — Stage, Probability, Weighted EV</div>{pl_tbl}</div>
  <div style="{cell}"><div style="{h3}">Banker Relationship Matrix — LTM Performance</div>{bk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector Whitespace &amp; Expansion Targets</div>{ws_tbl}</div>
  <div style="{cell}"><div style="{h3}">Win/Loss Analysis</div>{wl_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sourcing Velocity — Quarterly Trend</div>{vl_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Origination Thesis:</strong> ${r.total_pipeline_ev_mm:,.0f}M active pipeline EV weights to ${r.weighted_pipeline_ev_mm:,.0f}M probability-adjusted.
    Top 3 banker relationships (Jefferies, Harris Williams, William Blair) represent ~42% of deal flow and 60% of closed transactions.
    Sector whitespace concentrates in Fertility / IVF, Women's Health, Behavioral, and Pediatric Therapy — lowest platform saturation.
    Win/loss skews toward price-driven losses (42 in LTM) — suggests upward multiple pressure in competitive auctions.
    Velocity stable at ~2-3 closes per quarter; conversion rate 1.4-2.0% from screen to close (industry norm).
    Recommend focused pursuit of Fertility and Behavioral Health bolt-ons where whitespace is open and multiples are entering reset.
  </div>
</div>"""

    return chartis_shell(body, "Deal Origination", active_nav="/deal-origination")
