"""Deal Sourcing / Proprietary Flow Tracker — /deal-sourcing."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _stage_color(s: str) -> str:
    return {
        "Initial Screen": P["text_dim"],
        "Preliminary DD (CIM review)": P["text_dim"],
        "IOI / LOI Submitted": P["accent"],
        "IOI Submitted": P["accent"],
        "Management Presentation": P["accent"],
        "Confirmatory DD": P["warning"],
        "Signed / Closed": P["positive"],
    }.get(s, P["text_dim"])


def _funnel_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Stage","left"),("Count (LTM)","right"),("Avg Size ($M)","right"),("Cycle (days)","right"),
            ("Conv to Next","right"),("Annualized Run-Rate","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(f.stage)
        c_c = pos if f.conversion_to_next_pct >= 0.50 else (acc if f.conversion_to_next_pct >= 0.40 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:11px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(f.stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{f.count_ltm}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${f.avg_size_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.cycle_time_days}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{f.conversion_to_next_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{f.annualized_run_rate}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _channels_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Channel","left"),("Leads LTM","right"),("Qualified %","right"),("Deals Closed","right"),
            ("Close Rate","right"),("Closed Value ($M)","right"),("Median Size ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cl_c = pos if c.close_rate_pct >= 0.20 else (acc if c.close_rate_pct >= 0.05 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.channel)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{c.leads_ltm}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{c.qualified_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{c.deals_closed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cl_c};font-weight:700">{c.close_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.total_closed_value_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.median_close_size_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _intermediaries_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Firm","left"),("Type","left"),("Primary Contacts","right"),("Deals Shown LTM","right"),
            ("Deals Closed","right"),("Conv Rate","right"),("Reverse Inq","right"),("Relationship Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if m.relationship_score >= 9.0 else (acc if m.relationship_score >= 8.5 else text_dim)
        c_c = pos if m.conversion_rate_pct >= 0.05 else (acc if m.conversion_rate_pct >= 0.02 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.firm)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(m.firm_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{m.contacts_primary}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{m.deals_shown_ltm}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{m.deals_closed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{m.conversion_rate_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.reverse_inquiry_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{m.relationship_score:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _proprietary_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Target","left"),("Sector","left"),("Introducer","left"),("Stage","center"),
            ("Est Size ($M)","right"),("Proprietary Advantage","left"),("Days Since Intro","right"),("Probability","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(p.stage)
        pr_c = pos if p.probability_pct >= 60 else (acc if p.probability_pct >= 45 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.target)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.introducer)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.estimated_size_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(p.proprietary_advantage)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.days_since_intro}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pr_c};font-weight:700">{p.probability_pct}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _team_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Partner","left"),("Coverage","left"),("Sourced LTM","right"),("Closed LTM","right"),
            ("Closed Value ($M)","right"),("Avg Markup %","right"),("Proprietary %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if t.proprietary_deal_pct >= 0.50 else (acc if t.proprietary_deal_pct >= 0.35 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(t.partner)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(t.coverage)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{t.deals_sourced_ltm}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{t.deals_closed_ltm}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${t.total_closed_value_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{t.avg_markup_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{t.proprietary_deal_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _closed_bridge_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("Source","left"),("Introducer","left"),
            ("Process Type","center"),("Value ($M)","right"),("Deal Date","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.source)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.introducer)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.process_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.deal_value_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.deal_date)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_deal_sourcing(params: dict = None) -> str:
    from rcm_mc.data_public.deal_sourcing import compute_deal_sourcing
    r = compute_deal_sourcing()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Annualized Pipeline", f"{r.total_annualized_pipeline:,}", "leads", "") +
        ck_kpi_block("Proprietary Opps", str(r.total_proprietary_opportunities), "", "") +
        ck_kpi_block("Closed LTM", str(r.total_closed_ltm), "", "") +
        ck_kpi_block("Closed Value", f"${r.total_closed_value_m:,.1f}M", "", "") +
        ck_kpi_block("Close Rate", f"{r.weighted_close_rate_pct * 100:.2f}%", "", "") +
        ck_kpi_block("Sourcing Partners", str(len(r.team)), "", "") +
        ck_kpi_block("Intermediaries", str(len(r.intermediaries)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    f_tbl = _funnel_table(r.funnel)
    c_tbl = _channels_table(r.channels)
    i_tbl = _intermediaries_table(r.intermediaries)
    p_tbl = _proprietary_table(r.proprietary)
    t_tbl = _team_table(r.team)
    cb_tbl = _closed_bridge_table(r.closed_bridge)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    prop_closed = sum(1 for c in r.closed_bridge if "Proprietary" in c.source or "Operating Partner" in c.source or "Portfolio" in c.source or "Co-Invest" in c.source)
    prop_value = sum(c.deal_value_m for c in r.closed_bridge if "Proprietary" in c.source or "Operating Partner" in c.source or "Portfolio" in c.source or "Co-Invest" in c.source)
    prop_pct = prop_closed / r.total_closed_ltm if r.total_closed_ltm else 0
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Deal Sourcing / Proprietary Flow Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_annualized_pipeline:,} annualized leads · {r.total_proprietary_opportunities} active proprietary opps · {r.total_closed_ltm} closed LTM ({prop_closed} proprietary = {prop_pct * 100:.0f}%) · ${r.total_closed_value_m:,.1f}M closed value — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Sourcing Funnel — LTM Activity</div>{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Source Channel Performance</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Active Proprietary Opportunities</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Intermediary Relationships</div>{i_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sourcing Team Productivity</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Closed Deals Bridge — Source Attribution</div>{cb_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Deal Sourcing Summary:</strong> 485 annualized-leads pipeline converts at {r.weighted_close_rate_pct * 100:.2f}% to closed deals — {r.total_closed_ltm} transactions / ${r.total_closed_value_m:,.1f}M aggregate value LTM.
    Proprietary deals represent {prop_pct * 100:.0f}% of closed count (${prop_value:,.1f}M value) — operating partner rolodex, portfolio introductions, and sponsor direct sourcing drive higher-conviction proprietary wins.
    Intermediary performance: Edgemont (healthcare specialist) and Jefferies (middle market) top the league table — 3 and 2 closes respectively; 13+ shown by each with strong relationship tenure.
    Funnel conversion: Initial screen → Preliminary DD 48%, Preliminary → IOI 44%, IOI → MP 37%, MP → Confirmatory 51%, Confirmatory → Close 75% — reasonable conversion profile; top-of-funnel quality remains key.
    Active proprietary pipeline ${sum(p.estimated_size_m for p in r.proprietary):,.1f}M total; probability-weighted ${sum(p.estimated_size_m * (p.probability_pct / 100.0) for p in r.proprietary):,.1f}M — Aspen-adjacent Southeast Ophthalmology (72% × $185M) is highest-conviction next close.
    Team productivity: Sr. Partner 1 leads with 3 closes / $1,450M value; Sr. Partner 3 (healthtech) carries highest proprietary rate (55%); Directors are high-activity at screening but have not yet converted in LTM.
  </div>
</div>"""

    return chartis_shell(body, "Deal Sourcing", active_nav="/deal-sourcing")
