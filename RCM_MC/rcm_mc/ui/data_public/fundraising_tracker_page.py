"""Fundraising / LP Pipeline Tracker — /fundraising."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel

_FUNDRAISING_NEEDED = [
    ("lp_name", "LP / prospect"),
    ("status", "committed / soft-circle / pipeline"),
    ("commitment", "commitment $"),
    ("probability_pct", "close probability %"),
    ("close_date", "expected close (YYYY-MM-DD)"),
]


def _targets_chart(items) -> str:
    """Lead chart for the fundraising table — funds ranked by capital
    committed so progress against target reads at a glance. Bar width =
    committed as a share of the fund's target; value = committed ($M);
    tone teal. Full fund grid stays directly below.
    """
    ranked = sorted(items, key=lambda t: t.committed_m, reverse=True)
    rows = []
    for t in ranked:
        target_m = (t.target_size_b or 0) * 1000.0
        progress = (t.committed_m / target_m * 100.0) if target_m else 0.0
        rows.append(ck_bar_row(
            t.fund_name,
            f"${t.committed_m:,.0f}M",
            progress,
            tone="teal",
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = committed as a share of fund target · value = capital '
        'committed ($M)</div>'
        '</div>'
    )


def _stage_color(s: str) -> str:
    return {
        "hard circled": P["positive"],
        "due diligence complete": P["positive"],
        "due diligence active": P["accent"],
        "initial evaluation": P["warning"],
        "introduction": P["text_dim"],
    }.get(s, P["text_dim"])


def _status_color(s: str) -> str:
    return {
        "active fundraising": P["positive"],
        "early fundraising": P["accent"],
        "in pricing": P["warning"],
    }.get(s, P["text_dim"])


def _neg_color(d: str) -> str:
    return {
        "agreed": P["positive"],
        "agreed (cornerstone tier)": P["positive"],
        "agreed (LP strong preference)": P["positive"],
        "negotiated": P["warning"],
    }.get(d, P["text_dim"])


def _targets_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Fund","left"),("Target ($B)","right"),("Hard Cap ($B)","right"),("Strategy","left"),
            ("Launch","right"),("First Close","right"),("Final Close","right"),
            ("Committed ($M)","right"),("Hard Circled ($M)","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(t.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.fund_name)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${t.target_size_b:.2f}B""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${t.hard_cap_b:.2f}B""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(t.strategy)}</td>',
            f'{ck_data_cell(f"""{_html.escape(t.launch_date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(t.first_close)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(t.final_close_target)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${t.committed_m:,.1f}M""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${t.hard_circled_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pipeline_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("LP","left"),("Type","left"),("Prior","center"),("Target ($M)","right"),
            ("Likelihood","right"),("Stage","center"),("Last Activity","right"),("Owner","left"),("Notes","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, lp in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(lp.stage)
        p_c = pos if lp.prior_relationship else text_dim
        l_c = pos if lp.likelihood_pct >= 85 else (acc if lp.likelihood_pct >= 65 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(lp.lp_name)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(lp.lp_type)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{p_c};font-weight:700">{"YES" if lp.prior_relationship else "NO"}</td>',
            f'{ck_data_cell(f"""${lp.target_commitment_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:700">{lp.likelihood_pct:.0f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(lp.stage)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{_html.escape(lp.last_activity)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(lp.owner)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(lp.notes)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stages_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Stage","left"),("LPs","right"),("Target ($M)","right"),("Weighted ($M)","right"),("Avg Likelihood","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        st_c = _stage_color(s.stage)
        cells = [
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:11px;font-family:JetBrains Mono,monospace;color:{st_c};border:1px solid {st_c};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(s.stage)}</span>""")}',
            f'{ck_data_cell(f"""{s.lps}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${s.target_commitment_m:,.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${s.weighted_commitment_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{s.avg_likelihood_pct:.1f}%""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _terms_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Term","left"),("Main Fund","left"),("Benchmark Market","left"),("Negotiation Status","center"),("LP Pressure","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        n_c = _neg_color(t.negotiation_status)
        p_c = P["warning"] if "favoring" in t.lp_pressure_direction.lower() or "up" in t.lp_pressure_direction.lower() else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.term)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:320px">{_html.escape(t.main_fund)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:240px">{_html.escape(t.benchmark_market)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{n_c};border:1px solid {n_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.negotiation_status)}</span>""", align="center")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{p_c}">{_html.escape(t.lp_pressure_direction)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _agents_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Agent","left"),("Fund","left"),("Retainer ($M)","right"),("Success Fee (bps)","right"),
            ("Regions","left"),("Deals Sourced","right"),("Committed ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.agent)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.fund)}</td>',
            f'{ck_data_cell(f"""${a.retainer_m:.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{a.success_fee_bps}bps""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.regions)}</td>',
            f'{ck_data_cell(f"""{a.deals_sourced}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${a.committed_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _schedule_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Fund","left"),("Close","left"),("Target Date","right"),("Target ($M)","right"),
            ("Committed ($M)","right"),("On Track","center"),("Risk Factors","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = pos if s.on_track else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.fund)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(s.close)}</td>',
            f'{ck_data_cell(f"""{_html.escape(s.target_date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.target_commitment_m:,.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${s.committed_m:,.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{t_c};font-weight:700">{"ON TRACK" if s.on_track else "AT RISK"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(s.risk_factors)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_fundraising_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.fundraising_tracker import compute_fundraising_tracker
    r = compute_fundraising_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Active Funds", str(r.active_funds), "", "") +
        ck_kpi_block("Target Raise", f"${r.total_target_b:.2f}B", "", "") +
        ck_kpi_block("Committed", f"${r.total_committed_b:.2f}B", "", "") +
        ck_kpi_block("Hard Circled", f"${r.total_hard_circled_b:.2f}B", "", "") +
        ck_kpi_block("Pct Fundraised", f"{r.pct_fundraised * 100:.1f}%", "", "") +
        ck_kpi_block("LPs in Pipeline", str(r.lps_in_pipeline), "", "") +
        ck_kpi_block("Placement Agents", str(len(r.agents)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    t_chart = _targets_chart(r.targets)
    t_tbl = _targets_table(r.targets)
    value_anchor = ck_value_anchor(
        "Fundraising",
        f"${r.total_committed_b:,.1f}B committed",
        delta=f"{r.pct_fundraised * 100:.0f}% of ${r.total_target_b:,.1f}B target · {r.active_funds} active funds · {r.lps_in_pipeline} LPs in pipeline",
        tone="positive",
    )
    s_tbl = _stages_table(r.stages)
    p_tbl = _pipeline_table(r.pipeline)
    tr_tbl = _terms_table(r.terms)
    a_tbl = _agents_table(r.agents)
    sc_tbl = _schedule_table(r.schedule)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    hard_circle = sum(s.weighted_commitment_m for s in r.stages if s.stage in ("hard circled", "due diligence complete"))

    page_title = ck_page_title(
        "Fundraising / LP Pipeline Tracker",
        eyebrow="FUNDRAISING TRACKER",
        meta=f"{r.active_funds} active funds targeting ${r.total_target_b:.2f}B aggregate · ${r.total_hard_circled_b:.2f}B hard-circled ({r.pct_fundraised * 100:.1f}% complete) · {r.lps_in_pipeline} LPs in pipeline · {len(r.agents)} placement agents engaged",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {data_required_panel(P, title="Fundraising", needed=_FUNDRAISING_NEEDED,
      template="fundraising_template.csv", request_from="IR / fundraising team",
      activates="fund-close tracking, LP pipeline coverage vs target",
      guide_hint="What fundraising / LP-pipeline data do I need to upload?")}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Active Funds Under Fundraising</div>{t_chart}{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Pipeline by Stage</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Close Schedule — All Funds</div>{sc_tbl}</div>
  <div style="{cell}"><div style="{h3}">LP Pipeline Detail ({r.lps_in_pipeline} LPs)</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Fund Terms Matrix — Key Negotiated Provisions</div>{tr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Placement Agent Performance</div>{a_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Fundraising Summary:</strong> ${r.total_target_b:.2f}B aggregate target across {r.active_funds} active funds; ${r.total_hard_circled_b:.2f}B hard-circled ({r.pct_fundraised * 100:.1f}% complete) with additional ${hard_circle - r.total_hard_circled_b * 1000:,.0f}M in advanced-DD pipeline.
    Fund VI leading with $5.1B hard-circled against $6.0B target — tracking above plan and should reach target at second close (June 2026).
    LP pipeline concentrated in existing relationships (60%+ prior-fund LPs); new LP cultivation (ADIA, MIT, KIC, OTPP, QIA) represents $1.1B+ of upside if DD progresses.
    Terms negotiation track: 12 of 14 key provisions agreed with cornerstone LPs; 2 still negotiating (LPAC composition, ESG reporting) — LP pressure manageable, no GP-unfriendly concessions.
    Placement agents: Park Hill ($1.85B sourced), Campbell Lutyens ($485M for CV), Jefferies ($485M for Growth III) — aggregate agent-sourced commitments $4.2B of ${r.total_hard_circled_b:.2f}B.
    Credit Fund is the only AT-RISK close: $320M hard-circled vs $1.0B first-close target; cornerstone LP pursuit accelerated Q2 2026.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Fundraising Tracker", active_nav="/fundraising",
        editorial_intro={
            "eyebrow": "FUNDRAISING TRACKER",
            "headline": "What the fundraising tracker page reveals on this deal.",
            "italic_word": "reveals",
        })
