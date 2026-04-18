"""Fundraising / LP Pipeline Tracker — /fundraising."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


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
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(t.status)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(t.fund_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${t.target_size_b:.2f}B</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${t.hard_cap_b:.2f}B</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(t.strategy)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(t.launch_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(t.first_close)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(t.final_close_target)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">${t.committed_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${t.hard_circled_m:,.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pipeline_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("LP","left"),("Type","left"),("Prior","center"),("Target ($M)","right"),
            ("Likelihood","right"),("Stage","center"),("Last Activity","right"),("Owner","left"),("Notes","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, lp in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _stage_color(lp.stage)
        p_c = pos if lp.prior_relationship else text_dim
        l_c = pos if lp.likelihood_pct >= 85 else (acc if lp.likelihood_pct >= 65 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(lp.lp_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(lp.lp_type)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{p_c};font-weight:700">{"YES" if lp.prior_relationship else "NO"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${lp.target_commitment_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:700">{lp.likelihood_pct:.0f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(lp.stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(lp.last_activity)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(lp.owner)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(lp.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stages_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Stage","left"),("LPs","right"),("Target ($M)","right"),("Weighted ($M)","right"),("Avg Likelihood","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        st_c = _stage_color(s.stage)
        cells = [
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:11px;font-family:JetBrains Mono,monospace;color:{st_c};border:1px solid {st_c};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(s.stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.lps}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.target_commitment_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.weighted_commitment_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.avg_likelihood_pct:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _terms_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Term","left"),("Main Fund","left"),("Benchmark Market","left"),("Negotiation Status","center"),("LP Pressure","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        n_c = _neg_color(t.negotiation_status)
        p_c = P["warning"] if "favoring" in t.lp_pressure_direction.lower() or "up" in t.lp_pressure_direction.lower() else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(t.term)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:320px">{_html.escape(t.main_fund)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:240px">{_html.escape(t.benchmark_market)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{n_c};border:1px solid {n_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.negotiation_status)}</span></td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{p_c}">{_html.escape(t.lp_pressure_direction)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _agents_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Agent","left"),("Fund","left"),("Retainer ($M)","right"),("Success Fee (bps)","right"),
            ("Regions","left"),("Deals Sourced","right"),("Committed ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(a.agent)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(a.fund)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${a.retainer_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a.success_fee_bps}bps</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(a.regions)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{a.deals_sourced}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${a.committed_m:,.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _schedule_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Fund","left"),("Close","left"),("Target Date","right"),("Target ($M)","right"),
            ("Committed ($M)","right"),("On Track","center"),("Risk Factors","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = pos if s.on_track else neg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.fund)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(s.close)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.target_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.target_commitment_m:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.committed_m:,.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{t_c};font-weight:700">{"ON TRACK" if s.on_track else "AT RISK"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(s.risk_factors)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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

    t_tbl = _targets_table(r.targets)
    s_tbl = _stages_table(r.stages)
    p_tbl = _pipeline_table(r.pipeline)
    tr_tbl = _terms_table(r.terms)
    a_tbl = _agents_table(r.agents)
    sc_tbl = _schedule_table(r.schedule)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    hard_circle = sum(s.weighted_commitment_m for s in r.stages if s.stage in ("hard circled", "due diligence complete"))

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Fundraising / LP Pipeline Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.active_funds} active funds · ${r.total_target_b:.2f}B aggregate target · ${r.total_hard_circled_b:.2f}B hard circled · {r.pct_fundraised * 100:.1f}% fundraised · {r.lps_in_pipeline} LPs in pipeline · {len(r.agents)} placement agents — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Active Funds Under Fundraising</div>{t_tbl}</div>
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

    return chartis_shell(body, "Fundraising Tracker", active_nav="/fundraising", data_source="synthetic")