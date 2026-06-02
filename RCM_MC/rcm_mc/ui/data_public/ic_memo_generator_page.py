"""IC Memo Generator (Standardized) — /ic-memo-gen."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor, ck_illustrative_note
from rcm_mc.ui.chartis._helpers import render_page_explainer


def _levers_chart(items) -> str:
    """Lead chart for the value-creation lever table — levers ranked by
    probability-weighted expected contribution so the IC sees where the
    value actually comes from before the target-vs-expected detail grid.
    Bar width = share of total expected contribution, value = expected
    ($M), tone marks execution probability (>=80% green · >=65% teal ·
    below amber). Full lever grid stays directly below.
    """
    total = sum(lv.expected_contribution_mm for lv in items) or 1.0
    ranked = sorted(items, key=lambda lv: lv.expected_contribution_mm, reverse=True)
    rows = []
    for lv in ranked:
        tone = ("positive" if lv.probability_pct >= 0.80
                else "teal" if lv.probability_pct >= 0.65 else "warning")
        rows.append(ck_bar_row(
            lv.lever,
            f"${lv.expected_contribution_mm:,.1f}M",
            lv.expected_contribution_mm / total * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of total expected contribution · value = '
        'probability-weighted expected ($M) · tone = execution '
        'probability (green &ge;80% · teal &ge;65% · amber below)</div>'
        '</div>'
    )


def _thesis_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Thesis Element","left"),("Description","left"),("Evidence","center"),("Validation Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    e_c = {"strong": pos, "moderate": acc, "weak": warn}
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ec = e_c.get(t.evidence_strength, text_dim)
        v_c = pos if t.validation_score >= 82 else (acc if t.validation_score >= 72 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.thesis_element)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.description)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ec};border:1px solid {ec};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.evidence_strength)}</span>""", align="center")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:700">{t.validation_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _findings_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Workstream","left"),("Finding","left"),("Severity","center"),("Mitigation","left"),("Impact","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    s_c = {"clean": pos, "minor": text_dim, "medium": warn, "high": neg, "critical": neg}
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = s_c.get(f.severity, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(f.workstream)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.finding)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(f.severity)}</span>""", align="center")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{P["accent"]}">{_html.escape(f.mitigation)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.impact_on_thesis)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _levers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Value Creation Lever","left"),("Target ($M)","right"),("Base Rate ($M)","right"),
            ("Probability","right"),("Timeline (mo)","right"),("Expected ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, lv in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if lv.probability_pct >= 0.80 else (acc if lv.probability_pct >= 0.65 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(lv.lever)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${lv.target_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${lv.base_rate_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{lv.probability_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{lv.timeline_months}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${lv.expected_contribution_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _risks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; pos = P["positive"]
    cols = [("Risk","left"),("Category","center"),("Probability","center"),("Impact ($M)","right"),
            ("Mitigation","left"),("Residual","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    p_c = {"high": neg, "medium": warn, "low": text_dim}
    r_c = {"mitigated": pos, "monitor": text_dim, "residual": warn, "minimal": pos}
    for i, rk in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = p_c.get(rk.probability, text_dim)
        rc = r_c.get(rk.residual_risk, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(rk.risk)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(rk.category)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(rk.probability)}</span>""", align="center")}',
            f'{ck_data_cell(f"""${rk.impact_mm:,.2f}""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(rk.mitigation_plan)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{rc};font-weight:600">{_html.escape(rk.residual_risk)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _scenarios_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Scenario","left"),("Exit EBITDA ($M)","right"),("Exit Multiple","right"),
            ("Equity Proceeds ($M)","right"),("MOIC","right"),("IRR","right"),("Probability","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    _bar_max = max((s.equity_proceeds_mm for s in items), default=1.0) or 1.0
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if s.moic >= 2.5 else (acc if s.moic >= 1.8 else neg)
        i_c = pos if s.irr >= 0.20 else (acc if s.irr >= 0.12 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.scenario)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${s.ebitda_at_exit_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.exit_multiple:.2f}x""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""${s.equity_proceeds_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700, bar=s.equity_proceeds_mm / _bar_max * 100)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{s.moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:700">{s.irr * 100:+.1f}%</td>',
            f'{ck_data_cell(f"""{s.probability_pct * 100:.0f}%""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _structure_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Component","left"),("Amount ($M)","right"),("Terms","left"),("Notes","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, ds in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(ds.component)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${ds.amount_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(ds.terms)}""", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(ds.notes)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_ic_memo_generator(params: dict = None) -> str:
    from rcm_mc.data_public.ic_memo import compute_ic_memo
    r = compute_ic_memo()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    # B2: ck_kpi_block dropped _esc on value/sub/trend (trusted-markup
    # contract). Escape partner-supplied strings (deal_name, sector)
    # at the call site so they can't carry HTML into the trusted seam.
    kpi_strip = (
        ck_kpi_block("Deal", _html.escape(r.summary.deal_name[:16]), "", "") +
        ck_kpi_block("Sector", _html.escape(r.summary.sector[:14]), "", "") +
        ck_kpi_block("EV", f"${r.summary.ev_mm:,.0f}M", "", "") +
        ck_kpi_block("EV/EBITDA", f"{r.summary.ev_ebitda_multiple:.2f}x", "", "") +
        ck_kpi_block("Projected MOIC", f"{r.summary.projected_moic:.2f}x", "", "") +
        ck_kpi_block("Projected IRR", f"{r.summary.projected_irr * 100:.1f}%", "", "") +
        ck_kpi_block("Expected MOIC", f"{r.expected_moic:.2f}x", "(prob-wtd)", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    th_tbl = _thesis_table(r.thesis)
    fi_tbl = _findings_table(r.findings)
    lv_chart = _levers_chart(r.levers)
    lv_tbl = _levers_table(r.levers)
    rk_tbl = _risks_table(r.risks)
    sc_tbl = _scenarios_table(r.scenarios)
    st_tbl = _structure_table(r.structure)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Investment Committee Memo Generator",
        eyebrow="IC MEMO GENERATOR",
        meta=f"{r.summary.deal_name} ({r.summary.sector}) · ${r.summary.ev_mm:,.0f}M EV at {r.summary.ev_ebitda_multiple:.1f}x EBITDA · base {r.summary.projected_moic:.2f}x MOIC / {r.summary.projected_irr * 100:.1f}% IRR → probability-weighted {r.expected_moic:.2f}x / {r.expected_irr * 100:.1f}% · v{r.memo_version} for IC meeting {r.committee_meeting_date}",
    )

    _lever_value = sum(lv.expected_contribution_mm for lv in r.levers)
    value_anchor = ck_value_anchor(
        "Base-Case Return",
        f"{r.expected_moic:.2f}x MOIC",
        delta=f"{r.expected_irr * 100:.1f}% expected IRR",
        opportunity=f"${_lever_value:,.1f}M probability-weighted value creation",
        tone="positive",
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {pos};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">IC Recommendation</div>
    <div style="color:{pos};font-weight:700;font-size:14px">{_html.escape(r.summary.recommendation)}</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">{_html.escape(r.summary.committee_vote_needed)}</div>
  </div>
  <div style="{cell}"><div style="{h3}">Investment Thesis</div>{th_tbl}</div>
  <div style="{cell}"><div style="{h3}">Diligence Findings</div>{fi_tbl}</div>
  <div style="{cell}"><div style="{h3}">Value Creation Levers — Target vs Probability-Weighted Expected</div>{lv_chart}{lv_tbl}</div>
  <div style="{cell}"><div style="{h3}">Risk Register</div>{rk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Scenario Outcomes</div>{sc_tbl}</div>
  <div style="{cell}"><div style="{h3}">Deal Structure</div>{st_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">IC Memo Summary:</strong> {_html.escape(r.summary.deal_name)} — {_html.escape(r.summary.sector)} platform at ${r.summary.ev_mm:,.0f}M / {r.summary.ev_ebitda_multiple:.1f}x LTM EBITDA.
    Base case {r.summary.projected_moic:.2f}x MOIC / {r.summary.projected_irr * 100:.1f}% IRR over {r.summary.hold_years:.1f}y hold; probability-weighted expected {r.expected_moic:.2f}x / {r.expected_irr * 100:.1f}%.
    Investment thesis validates to {sum(t.validation_score for t in r.thesis) / len(r.thesis):.0f}/100 — strong on platform positioning, operating leverage, exit optionality.
    Material findings mitigated via management transition, W-2 conversion budget, BCBS 2nd-payer development.
    Expected value creation ${sum(lv.expected_contribution_mm for lv in r.levers):,.1f}M across 7 levers; multiple arbitrage (13x→14.5x) adds $9.2M; bolt-on M&A adds $9.4M.
    Recommend proceeding to final bid with submission authorization.
  </div>
</div>"""

    explainer = render_page_explainer(
        what=(
            "Standardized IC-memo builder: thesis-element scoring with "
            "validation scores, diligence findings with "
            "severity/mitigation, the seven-lever value-creation "
            "bridge, and a final recommendation block suitable for "
            "submission authorization."
        ),
        source="data_public/ic_memo_generator.py (standardized memo template).",
        page_key="ic-memo-gen",
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(explainer + ck_illustrative_note("IC memo figures (benchmark corpus)") + body, "IC Memo Generator", active_nav="/ic-memo-gen",
        editorial_intro={
            "eyebrow": "IC MEMO GENERATOR",
            "headline": "What the ic memo generator page reveals on this deal.",
            "italic_word": "reveals",
        })
