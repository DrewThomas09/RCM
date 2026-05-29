"""Management Compensation Analyzer page — /mgmt-comp.

Rollover equity, options, MIP economics, and alignment scoring with
LP/GP/Mgmt waterfall across exit MOIC scenarios.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_source_purpose
from rcm_mc.ui.data_public._benchmark_panels import data_required_panel

_MGMT_COMP_NEEDED = [
    ("executive_name", "executive / role (PII — handle per policy)"),
    ("base_salary", "annual base $"),
    ("bonus_target_pct", "target bonus % of base"),
    ("equity_value", "equity / options value $"),
    ("fmv_benchmark", "FMV benchmark $ for the role"),
]


def _alignment_gauge_svg(score: float) -> str:
    w, h = 280, 140
    cx, cy = w / 2, h - 20
    r = 100
    bg = P["panel"]

    # Segments: 0-40 red, 40-70 amber, 70-100 green
    import math
    def _arc(start_deg, end_deg, color):
        sr = math.radians(180 - start_deg)
        er = math.radians(180 - end_deg)
        x1, y1 = cx + r * math.cos(sr), cy - r * math.sin(sr)
        x2, y2 = cx + r * math.cos(er), cy - r * math.sin(er)
        large = 1 if (end_deg - start_deg) > 180 else 0
        return (f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 0 {x2:.1f} {y2:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="12" opacity="0.85"/>')

    arcs = (
        _arc(0, 72, P["negative"]) +
        _arc(72, 126, P["warning"]) +
        _arc(126, 180, P["positive"])
    )

    # Needle
    needle_deg = score / 100 * 180
    needle_r = math.radians(180 - needle_deg)
    nx = cx + (r - 20) * math.cos(needle_r)
    ny = cy - (r - 20) * math.sin(needle_r)
    needle = (
        f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" '
        f'stroke="{P["text"]}" stroke-width="3" stroke-linecap="round"/>'
        f'<circle cx="{cx}" cy="{cy}" r="5" fill="{P["text"]}"/>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + arcs + needle +
        f'<text x="{cx}" y="{cy - 20}" text-anchor="middle" fill="{P["text"]}" '
        f'font-size="24" font-weight="700" font-family="JetBrains Mono,monospace">{score:.0f}</text>'
        f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" fill="{P["text_dim"]}" '
        f'font-size="9" letter-spacing="0.1em" font-family="Inter,sans-serif">ALIGNMENT SCORE</text>'
        f'<text x="10" y="{h - 5}" fill="{P["text_faint"]}" font-size="9" font-family="JetBrains Mono,monospace">0</text>'
        f'<text x="{w - 18}" y="{h - 5}" fill="{P["text_faint"]}" font-size="9" font-family="JetBrains Mono,monospace">100</text>'
        f'</svg>'
    )


def _waterfall_svg(scenarios) -> str:
    if not scenarios:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 30, 30, 40
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_v = max(s.exit_equity_mm for s in scenarios) * 1.10

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    warn = P["warning"]; text_faint = P["text_faint"]; text_dim = P["text_dim"]
    border = P["border"]

    n = len(scenarios)
    group_w = inner_w / n - 10
    bar_w = group_w / 3

    bars = []
    for i, s in enumerate(scenarios):
        x_base = pad_l + i * (inner_w / n)

        # Stacked columns: LP / GP carry / Mgmt
        def _col(xi, val, color):
            bh = val / max_v * inner_h
            y = (h - pad_b) - bh
            return (f'<rect x="{xi:.1f}" y="{y:.1f}" width="{bar_w * 2:.1f}" height="{bh:.1f}" '
                    f'fill="{color}" opacity="0.85"/>'), y

        # LP on bottom, GP middle, Mgmt top (stacked)
        lp_bh = s.lp_net_mm * 0.82 / max_v * inner_h  # subtract mgmt portion of lp
        lp_y = (h - pad_b) - lp_bh
        gp_bh = s.gp_carry_mm / max_v * inner_h
        gp_y = lp_y - gp_bh
        mgmt_bh = s.total_mgmt_payout_mm / max_v * inner_h
        mgmt_y = gp_y - mgmt_bh

        bars.append(
            f'<rect x="{x_base:.1f}" y="{lp_y:.1f}" width="{bar_w * 2:.1f}" height="{lp_bh:.1f}" fill="{acc}" opacity="0.85"/>'
            f'<rect x="{x_base:.1f}" y="{gp_y:.1f}" width="{bar_w * 2:.1f}" height="{gp_bh:.1f}" fill="{warn}" opacity="0.85"/>'
            f'<rect x="{x_base:.1f}" y="{mgmt_y:.1f}" width="{bar_w * 2:.1f}" height="{mgmt_bh:.1f}" fill="{pos}" opacity="0.85"/>'
            f'<text x="{x_base + bar_w:.1f}" y="{mgmt_y - 4:.1f}" fill="{text_dim}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">${s.exit_equity_mm:,.0f}M</text>'
            f'<text x="{x_base + bar_w:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario)}</text>'
        )

    legend = (
        f'<rect x="{pad_l}" y="4" width="10" height="10" fill="{acc}" opacity="0.85"/>'
        f'<text x="{pad_l + 14}" y="13" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">LP Net</text>'
        f'<rect x="{pad_l + 70}" y="4" width="10" height="10" fill="{warn}" opacity="0.85"/>'
        f'<text x="{pad_l + 84}" y="13" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">GP Carry</text>'
        f'<rect x="{pad_l + 150}" y="4" width="10" height="10" fill="{pos}" opacity="0.85"/>'
        f'<text x="{pad_l + 164}" y="13" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">Management Payout</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + legend + "".join(bars)
        + f'</svg>'
    )


def _exec_table(executives) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Role","left"),("Base ($K)","right"),("Bonus %","right"),("Target Bonus ($K)","right"),
            ("Total Cash ($K)","right"),("Rollover %","right"),("Rollover Value ($M)","right"),
            ("Options %","right"),("Options FV ($M)","right"),("Total At-Risk ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, e in enumerate(executives):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"600" if e.role == "CEO" else "400"}">{_html.escape(e.role)}</td>',
            f'{ck_data_cell(f"""${e.base_salary_k:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{e.target_bonus_pct * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.target_bonus_k:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.total_cash_k:,.0f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{e.rollover_equity_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.rollover_value_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{e.options_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.options_fair_value_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${e.total_at_risk_mm:,.2f}""", align="right", mono=True, weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _mip_table(tranches) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Tranche","left"),("Allocation","right"),("Vesting","left"),("Hurdle","left"),
            ("Payout @ 2x","right"),("Payout @ 3x","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, t in enumerate(tranches):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.tranche)}""", mono=True)}',
            f'{ck_data_cell(f"""{t.allocation_pct * 100:.2f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{_html.escape(t.vesting_type)}""", tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(t.hurdle)}""", tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos if t.expected_payout_moic2 else text_dim}">{t.expected_payout_moic2:.2f}%</td>',
            f'{ck_data_cell(f"""{t.expected_payout_moic3:.2f}%""", align="right", mono=True, tone="pos")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenario_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Scenario","left"),("Exit Equity","right"),("LP Net","right"),("GP Carry","right"),
            ("Rollover","right"),("Options","right"),("MIP Pool","right"),("Total Mgmt","right"),("% to Mgmt","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.scenario)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${s.exit_equity_mm:,.1f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">${s.lp_net_mm:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${s.gp_carry_mm:,.1f}</td>',
            f'{ck_data_cell(f"""${s.mgmt_rollover_payout_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${s.mgmt_options_payout_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${s.mip_pool_payout_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${s.total_mgmt_payout_mm:,.2f}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.pct_going_to_mgmt * 100:.1f}%""", align="right", mono=True)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_mgmt_comp(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    ev = _f("ev", 300.0)
    eq_pct = _f("equity_pct", 0.45)

    from rcm_mc.data_public.mgmt_comp import compute_mgmt_comp
    r = compute_mgmt_comp(ev_mm=ev, equity_pct=eq_pct)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("EV", f"${r.ev_mm:,.0f}M", "", "") +
        ck_kpi_block("Equity", f"${r.equity_mm:,.0f}M", "", "") +
        ck_kpi_block("Size Bucket", r.size_bucket, "", "") +
        ck_kpi_block("Total Rollover", f"${r.total_rollover_mm:,.2f}M", "", "") +
        ck_kpi_block("Option Pool FV", f"${r.total_option_pool_mm:,.2f}M", "", "") +
        ck_kpi_block("MIP Pool", f"${r.total_mip_pool_mm:,.2f}M", "", "") +
        ck_kpi_block("Alignment Score", f"{r.blended_alignment_score:.0f}", "/100", "") +
        ck_kpi_block("CEO At-Risk", f"${r.executives[0].total_at_risk_mm:,.2f}M", "", "")
    )

    gauge_svg = _alignment_gauge_svg(r.blended_alignment_score)
    waterfall_svg = _waterfall_svg(r.exit_scenarios)
    exec_tbl = _exec_table(r.executives)
    mip_tbl = _mip_table(r.mip_tranches)
    scen_tbl = _scenario_table(r.exit_scenarios)

    form = f"""
<form method="GET" action="/mgmt-comp" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EV ($M)
    <input name="ev" value="{ev}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Equity %
    <input name="equity_pct" value="{eq_pct}" type="number" step="0.05"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Management Compensation Analyzer",
        eyebrow="MGMT COMP",
        meta=f"""Rollover equity, options, MIP economics &amp; sponsor alignment — {r.size_bucket} deal — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">

  {page_title}
  {data_required_panel(P, title="Management Compensation", needed=_MGMT_COMP_NEEDED,
      template="management_compensation_template.csv", request_from="CFO / HR / comp consultant",
      activates="comp-vs-FMV benchmarking, retention-risk and Stark/AKS overlap flags",
      guide_hint="What compensation data do I need to activate this page?")}
  {ck_illustrative_note("figures")}

  {form}

  <div class="ck-kpi-grid" style="margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 2fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Sponsor-Mgmt Alignment</div>
      {gauge_svg}
      <p style="font-size:10px;color:{text_dim};margin-top:12px;line-height:1.5">
        Blends CEO rollover-to-cash ratio (55%) with total mgmt at-risk as % of equity (45%).
        Target: &gt;70 for PE-backed deals.
      </p>
    </div>
    <div style="{cell}">
      <div style="{h3}">Exit Scenario Waterfall (LP / GP / Management)</div>
      {waterfall_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Executive Compensation ({len(r.executives)} roles)</div>
    {exec_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Management Incentive Plan (MIP) — {len(r.mip_tranches)} Tranches</div>
    {mip_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Exit Scenario Payouts</div>
    {scen_tbl}
  </div>

</div>"""

    body = ck_source_purpose(
        purpose="Benchmark management compensation vs comparable roles.",
        universe="illustrative", source="Hardcoded benchmark figures",
        next_action="Wire to IRS 990 exec comp (non-profits)") + body
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Mgmt Compensation Analyzer", active_nav="/mgmt-comp",
        editorial_intro={
            "eyebrow": "MGMT COMP",
            "headline": "What the mgmt comp page reveals on this deal.",
            "italic_word": "reveals",
        })
