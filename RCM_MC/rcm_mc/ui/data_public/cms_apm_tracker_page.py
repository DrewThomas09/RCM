"""CMS Innovation Models / APM Tracker — /cms-apm."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row, ck_value_anchor, ck_source_purpose


def _programs_chart(items) -> str:
    """Lead chart — APM programs ranked by total payments (tone by status)."""
    def _tone(st):
        s=(st or "").lower()
        if "sunset" in s or "expir" in s: return "warning"
        if "permanent" in s or "active" in s: return "positive"
        return "teal"
    total = sum(p.total_payments_b for p in items) or 1.0
    rows=[ck_bar_row(p.program, f"${p.total_payments_b:,.1f}B",
          p.total_payments_b/total*100.0, tone=_tone(p.status))
          for p in sorted(items, key=lambda p: p.total_payments_b, reverse=True)]
    return ('<div style="margin-bottom:14px">'+"".join(rows)+
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of total APM payments '
            '\u00b7 value = payments ($B) \u00b7 tone = program status</div></div>')



def _status_color(s: str) -> str:
    return {
        "permanent": P["positive"],
        "active": P["accent"],
        "new / ramping": P["warning"],
        "sunset scheduled": P["warning"],
        "sunset": P["negative"],
        "pilot": P["accent"],
        "retired": P["text_dim"],
    }.get(s, P["text_dim"])


def _impact_color(i: str) -> str:
    s = i.lower()
    if "sunset" in s or "cut" in s or "expansion" in s: return P["warning"]
    if "launch" in s or "new" in s: return P["accent"]
    return P["text_dim"]


def _programs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Program","left"),("Type","left"),("Lives (M)","right"),("Participants","right"),
            ("Payments ($B)","right"),("Risk Structure","left"),("Savings %","right"),
            ("Through","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(p.status)
        sv_c = pos if p.savings_rate_pct >= 3.0 else (acc if p.savings_rate_pct >= 1.5 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.program)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.program_type)}</td>',
            f'{ck_data_cell(f"""{p.lives_covered_m:.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{p.participants:,}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${p.total_payments_b:.1f}B""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.risk_structure)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sv_c};font-weight:700">{p.savings_rate_pct:.2f}%</td>',
            f'{ck_data_cell(f"""{_html.escape(p.active_through)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposures_chart(items) -> str:
    """Summary chart — deals ranked by APM revenue exposure (tone by rev share)."""
    def _tone(e):
        if e.apm_share_of_rev_pct >= 0.15: return "warning"
        if e.apm_share_of_rev_pct >= 0.08: return "teal"
        return "navy"
    top = sorted(items, key=lambda e: e.apm_revenue_m, reverse=True)
    total = sum(e.apm_revenue_m for e in top) or 1.0
    rows = [ck_bar_row(f"{e.deal} · {e.sector}",
            f"${e.apm_revenue_m:.1f}M ({e.apm_share_of_rev_pct * 100:.0f}%)",
            e.apm_revenue_m / total * 100.0, tone=_tone(e)) for e in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of portfolio APM revenue '
            '· value = APM revenue ($M) + rev share · tone = APM dependence</div></div>')


def _exposures_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("APM Programs","left"),("Lives (K)","right"),
            ("APM Revenue ($M)","right"),("APM Share of Revenue","right"),("Net Savings ($M)","right"),("Quality Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sh_c = pos if e.apm_share_of_rev_pct >= 0.15 else (acc if e.apm_share_of_rev_pct >= 0.08 else text_dim)
        q_c = pos if e.quality_score >= 87 else (acc if e.quality_score >= 85 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.deal)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(e.apm_programs)}</td>',
            f'{ck_data_cell(f"""{e.lives_covered_k:.1f}K""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${e.apm_revenue_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sh_c};font-weight:700">{e.apm_share_of_rev_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${e.net_savings_m:.1f}M""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{q_c};font-weight:700">{e.quality_score:.1f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _trends_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Year","right"),("Program","left"),("Participants","right"),("Spend ($B)","right"),
            ("Savings ($B)","right"),("Savings %","right"),("Quality Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{t.year}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(t.program)}</td>',
            f'{ck_data_cell(f"""{t.participants:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${t.gross_spend_b:.1f}B""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${t.gross_savings_b:.2f}B""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{t.savings_rate_pct:.2f}%""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{t.quality_score:.1f}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _risk_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Structure","left"),("Upside Share","right"),("Downside Share","right"),("Participants","right"),
            ("Typical Savings %","right"),("Suitability","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.structure)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{r.upside_share_pct:.0f}%""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{r.downside_share_pct:.0f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{r.typical_participants:,}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{r.typical_savings_rate_pct:.2f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.suitability)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _calendar_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Event","left"),("Date","right"),("Impact","left"),("Affected Programs","left"),("Portfolio Exposure ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        i_c = _impact_color(c.impact)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.event)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(c.event_date)}""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{i_c};max-width:340px">{_html.escape(c.impact)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.affected_programs)}</td>',
            f'{ck_data_cell(f"""${c.portfolio_exposure_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _payer_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Track","left"),("Programs","right"),("Lives (M)","right"),("Commercial Spread (bps)","right"),
            ("Market Pen %","right"),("Sponsor Activity","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sp_c = pos if p.commercial_spread_bps <= -400 else (acc if p.commercial_spread_bps <= -250 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.commercial_ma_track)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{p.programs}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.lives_m:.1f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sp_c};font-weight:700">{p.commercial_spread_bps}</td>',
            f'{ck_data_cell(f"""{p.market_penetration_pct:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sponsor_activity)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_cms_apm_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.cms_apm_tracker import compute_cms_apm_tracker
    r = compute_cms_apm_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Active Programs", str(r.total_programs), "", "") +
        ck_kpi_block("Lives Covered", f"{r.total_lives_covered_m:.1f}M", "", "") +
        ck_kpi_block("CMS Payments", f"${r.total_apm_payments_b:.1f}B", "", "") +
        ck_kpi_block("Avg Savings Rate", f"{r.avg_savings_rate_pct:.2f}%", "", "") +
        ck_kpi_block("Portfolio APM Revenue", f"${r.total_portfolio_apm_revenue_m:.1f}M", "", "") +
        ck_kpi_block("Deals @ Risk (>10%)", str(sum(1 for e in r.exposures if e.apm_share_of_rev_pct > 0.10)), "", "") +
        ck_kpi_block("Policy Events", str(len(r.calendar)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_chart = _programs_chart(r.programs)
    p_tbl = _programs_table(r.programs)
    value_anchor = ck_value_anchor(
        "CMS APM Exposure",
        f"${r.total_apm_payments_b:,.0f}B APM payments",
        delta=f"{r.total_programs} programs \u00b7 {r.avg_savings_rate_pct:.1f}% avg savings \u00b7 {r.total_lives_covered_m:.1f}M lives \u00b7 {r.portfolio_share_at_risk_pct * 100:.0f}% portfolio at risk",
        tone="teal",
    )
    e_tbl = _exposures_table(r.exposures)
    e_chart = _exposures_chart(r.exposures)
    t_tbl = _trends_table(r.trends)
    rs_tbl = _risk_table(r.risk_structures)
    c_tbl = _calendar_table(r.calendar)
    pa_tbl = _payer_table(r.payer_adjacency)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "CMS Innovation Models / APM Tracker",
        eyebrow="CMS APM",
        meta=f"{r.total_programs} active CMS APMs · {r.total_lives_covered_m:.1f}M lives covered · ${r.total_apm_payments_b:.1f}B annual Medicare payments · ${r.total_portfolio_apm_revenue_m:.1f}M portfolio APM revenue at {r.portfolio_share_at_risk_pct * 100:.1f}% share at risk",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Program Catalog — CMMI & CMS APMs</div>{p_chart}{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Portfolio Exposure — Deals in APMs</div>{e_chart}{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Historical Performance — Top Programs</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Risk Structure Options</div>{rs_tbl}</div>
  <div style="{cell}"><div style="{h3}">2026-2027 Policy Calendar & Portfolio Impact</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Commercial / MA Value-Based Adjacency</div>{pa_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">CMS APM Portfolio Summary:</strong> {r.total_programs} active CMS APMs cover {r.total_lives_covered_m:.1f}M lives and route ${r.total_apm_payments_b:.1f}B in annual Medicare payments — avg {r.avg_savings_rate_pct:.2f}% savings rate across active programs.
    Portfolio APM revenue ${r.total_portfolio_apm_revenue_m:.1f}M across {len(r.exposures)} platforms — {sum(1 for e in r.exposures if e.apm_share_of_rev_pct > 0.10)} deals at &gt;10% APM revenue share (Magnolia/MSK, Redwood/Behavioral, Cedar/Cardiology, Sage/Home Health, Linden/Behavioral).
    Risk exposure: {r.portfolio_share_at_risk_pct * 100:.1f}% of portfolio revenue materially dependent on APM outcomes — concentrated in cardiology, home health, behavioral, and MSK.
    Policy overhang: ACO REACH sunset 2026-12-31 ($42.5B program ending), PCF sunset 2026-12-31 ($12.8B), BPCI-A sunset 2025-12-31 ($18.5B) — transition paths to MCP, MSSP, and TEAM identified.
    Commercial MA parallel: 35 commercial MA risk-based programs cover 28.5M lives at SOFR+ tighter to equity-implied cost — major sponsor targets include Humana, Clover, Alignment, Optum Care, ChenMed.
    -2.8% 2026 physician fee schedule cut proposes $850M portfolio pressure (gross) — offset by APM shared savings realization target $40-60M net per year.
  </div>
</div>"""

    body = ck_source_purpose(
        purpose="Track CMS Alternative Payment Model exposure.",
        universe="illustrative", source="Hardcoded figures",
        next_action="Wire to CMS APM participation (public)") + body
    return chartis_shell(body, "CMS APM Tracker", active_nav="/cms-apm",
        editorial_intro={
            "eyebrow": "CMS APM TRACKER",
            "headline": "What the cms apm tracker page reveals on this deal.",
            "italic_word": "reveals",
        })
