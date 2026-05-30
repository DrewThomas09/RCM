"""Deal Sourcing / Proprietary Flow Tracker — /deal-sourcing."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor


def _funnel_chart(items) -> str:
    """Lead chart for the sourcing funnel — LTM volume by stage in funnel
    order so the narrowing from top-of-funnel to close reads at a glance.
    Bar width = stage count relative to the widest stage; value = LTM
    count; tone marks stage-to-next conversion (>=50% green · >=40% teal
    · below amber). Full funnel table stays directly below.
    """
    hi = max((f.count_ltm for f in items), default=1) or 1
    rows = []
    for f in items:
        tone = ("positive" if f.conversion_to_next_pct >= 0.50 else "teal"
                if f.conversion_to_next_pct >= 0.40 else "warning")
        rows.append(ck_bar_row(
            f.stage,
            f"{f.count_ltm:,}",
            f.count_ltm / hi * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = LTM count relative to widest stage · value = count · '
        'tone = conversion to next stage (green &ge;50% · teal &ge;40% · amber below)</div>'
        '</div>'
    )


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
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(f.stage)
        c_c = pos if f.conversion_to_next_pct >= 0.50 else (acc if f.conversion_to_next_pct >= 0.40 else text_dim)
        cells = [
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:11px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(f.stage)}</span>""")}',
            f'{ck_data_cell(f"""{f.count_ltm}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${f.avg_size_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{f.cycle_time_days}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{f.conversion_to_next_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{f.annualized_run_rate}""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _channels_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Channel","left"),("Leads LTM","right"),("Qualified %","right"),("Deals Closed","right"),
            ("Close Rate","right"),("Closed Value ($M)","right"),("Median Size ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cl_c = pos if c.close_rate_pct >= 0.20 else (acc if c.close_rate_pct >= 0.05 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.channel)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.leads_ltm}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.qualified_pct * 100:.1f}%""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{c.deals_closed}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cl_c};font-weight:700">{c.close_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${c.total_closed_value_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${c.median_close_size_m:.1f}M""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _intermediaries_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Firm","left"),("Type","left"),("Primary Contacts","right"),("Deals Shown LTM","right"),
            ("Deals Closed","right"),("Conv Rate","right"),("Reverse Inq","right"),("Relationship Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if m.relationship_score >= 9.0 else (acc if m.relationship_score >= 8.5 else text_dim)
        c_c = pos if m.conversion_rate_pct >= 0.05 else (acc if m.conversion_rate_pct >= 0.02 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.firm)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(m.firm_type)}</td>',
            f'{ck_data_cell(f"""{m.contacts_primary}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{m.deals_shown_ltm}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{m.deals_closed}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{m.conversion_rate_pct * 100:.2f}%</td>',
            f'{ck_data_cell(f"""{m.reverse_inquiry_count}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{m.relationship_score:.1f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _proprietary_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Target","left"),("Sector","left"),("Introducer","left"),("Stage","center"),
            ("Est Size ($M)","right"),("Proprietary Advantage","left"),("Days Since Intro","right"),("Probability","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(p.stage)
        pr_c = pos if p.probability_pct >= 60 else (acc if p.probability_pct >= 45 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.target)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.introducer)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.stage)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${p.estimated_size_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(p.proprietary_advantage)}</td>',
            f'{ck_data_cell(f"""{p.days_since_intro}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pr_c};font-weight:700">{p.probability_pct}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _team_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Partner","left"),("Coverage","left"),("Sourced LTM","right"),("Closed LTM","right"),
            ("Closed Value ($M)","right"),("Avg Markup %","right"),("Proprietary %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if t.proprietary_deal_pct >= 0.50 else (acc if t.proprietary_deal_pct >= 0.35 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.partner)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(t.coverage)}</td>',
            f'{ck_data_cell(f"""{t.deals_sourced_ltm}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{t.deals_closed_ltm}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${t.total_closed_value_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{t.avg_markup_pct:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{t.proprietary_deal_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _closed_bridge_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("Source","left"),("Introducer","left"),
            ("Process Type","center"),("Value ($M)","right"),("Deal Date","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.source)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.introducer)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.process_type)}</td>',
            f'{ck_data_cell(f"""${c.deal_value_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(c.deal_date)}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    f_chart = _funnel_chart(r.funnel)
    f_tbl = _funnel_table(r.funnel)
    value_anchor = ck_value_anchor(
        "Sourcing Pipeline",
        f"${r.total_closed_value_m:,.0f}M closed LTM",
        delta=f"{r.total_closed_ltm} deals closed · {r.weighted_close_rate_pct * 100:.1f}% weighted close rate · {r.total_proprietary_opportunities} proprietary",
        opportunity=f"{r.total_annualized_pipeline} annualized pipeline ops",
        tone="teal",
    )
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
    # 2026-05-30 audit P5 editorial: proprietary flow is one cut of
    # deal sourcing; the page tracks proprietary mix alongside broker
    # leads + auction processes. Eyebrow already reads DEAL SOURCING.
    page_title = ck_page_title(
        "Deal Sourcing Tracker",
        eyebrow="DEAL SOURCING",
        meta=f"{r.total_annualized_pipeline:,} annualized leads · {r.total_closed_ltm} closed LTM at ${r.total_closed_value_m:,.1f}M · {r.weighted_close_rate_pct * 100:.2f}% close rate · {prop_pct * 100:.0f}% proprietary mix on close",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Sourcing Funnel — LTM Activity</div>{f_chart}{f_tbl}</div>
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

    from rcm_mc.ui._chartis_kit import ck_illustrative_note as _ckn
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(_ckn("sourcing figures (illustrative seed corpus)") + body, "Deal Sourcing", active_nav="/deal-sourcing",
        editorial_intro={
            "eyebrow": "DEAL SOURCING",
            "headline": "What the deal sourcing page reveals on this deal.",
            "italic_word": "reveals",
        })
