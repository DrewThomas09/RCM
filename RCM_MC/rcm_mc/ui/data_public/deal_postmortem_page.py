"""Deal Post-Mortem — /deal-postmortem."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_data_cell, ck_kpi_block, ck_page_title, ck_value_anchor, ck_illustrative_note


def _plan_vs_actual_chart(items) -> str:
    """Lead chart for the plan-vs-actual table — operating metrics ranked
    by realization variance so beats and misses against the underwriting
    case read at a glance. Bar width = magnitude of the variance; value =
    signed variance %; tone marks beat/miss (>=0 green · within -10%
    amber · worse red), matching the table. Full grid stays below.
    """
    ranked = sorted(items, key=lambda p: p.variance_pct, reverse=True)
    rows = []
    for p in ranked:
        v = p.variance_pct
        tone = "positive" if v >= 0 else ("warning" if v >= -0.10 else "negative")
        rows.append(ck_bar_row(
            p.metric,
            f"{v * 100:+.1f}%",
            min(100.0, abs(v) * 100.0),
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = magnitude of variance vs underwriting · value = signed '
        'variance % · tone = beat/miss (green beat · amber within -10% · red worse)</div>'
        '</div>'
    )


def _plan_vs_actual_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Metric","left"),("Underwritten","right"),("Realized","right"),("Variance %","right"),("Commentary","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        v_c = pos if p.variance_pct >= 0 else (warn if p.variance_pct >= -0.10 else neg)
        # Display format
        if abs(p.underwritten) < 1.5 and p.underwritten > 0:
            u_disp = f"{p.underwritten * 100:.1f}%"
            r_disp = f"{p.realized * 100:.1f}%"
        elif abs(p.underwritten) < 20 and p.underwritten > 0:
            u_disp = f"{p.underwritten:.2f}"
            r_disp = f"{p.realized:.2f}"
        else:
            u_disp = f"{p.underwritten:.1f}"
            r_disp = f"{p.realized:.1f}"
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.metric)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{u_disp}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{r_disp}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:700">{p.variance_pct * 100:+.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.commentary)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _attribution_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Lever","left"),("Planned ($M)","right"),("Realized ($M)","right"),("Capture Rate","right"),
            ("What Went Right","left"),("What Went Wrong","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    _bar_max = max((a.realized_mm for a in items), default=1.0) or 1.0
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if a.capture_rate_pct >= 0.80 else (acc if a.capture_rate_pct >= 0.65 else (warn if a.capture_rate_pct >= 0.50 else neg))
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.lever)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${a.planned_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${a.realized_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700, bar=a.realized_mm / _bar_max * 100)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{a.capture_rate_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{pos}">{_html.escape(a.what_went_right)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{neg}">{_html.escape(a.what_went_wrong)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _milestones_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Milestone","left"),("Planned","left"),("Actual","left"),("Slipped (days)","right"),("Impact","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if m.slipped_days <= 30 else (warn if m.slipped_days <= 90 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.milestone)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(m.planned_date)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{_html.escape(m.actual_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{m.slipped_days}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.impact)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lessons_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Category","left"),("Lesson","left"),("Change for Next Deal","left"),("Priority","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    p_c = {"critical": neg, "high": warn, "medium": acc, "low": text_dim}
    for i, l in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = p_c.get(l.priority, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(l.category)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.lesson)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(l.change_for_next)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(l.priority)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _bridge_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Component","left"),("Underwritten ($M)","right"),("Realized ($M)","right"),
            ("Delta ($M)","right"),("Delta %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if b.delta_mm >= 0 else neg
        delta_pct_str = f"{b.delta_pct * 100:+.1f}%" if abs(b.delta_pct) < 5 else "n/a"
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.component)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${b.underwritten_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${b.realized_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">${b.delta_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c}">{delta_pct_str}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _counter_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Scenario","left"),("Change from Actual","left"),("Est MOIC Delta","right"),("Feasibility","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    f_c = {"high": pos, "medium": acc, "speculative": text_dim, "counterfactual": text_dim, "hypothetical ceiling": acc}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        fc = f_c.get(c.feasibility, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.scenario)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.change_from_actual)}</td>',
            f'{ck_data_cell(f"""+{c.estimated_moic_delta:.2f}x""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{fc};border:1px solid {fc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.feasibility)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_deal_postmortem(params: dict = None) -> str:
    from rcm_mc.data_public.deal_postmortem import compute_deal_postmortem
    r = compute_deal_postmortem()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    grade_c = pos if "A" in r.overall_grade else (acc if "B" in r.overall_grade else (warn if "C" in r.overall_grade else neg))
    moic_delta = (r.realized_moic - r.underwritten_moic) / r.underwritten_moic
    irr_delta = r.realized_irr - r.underwritten_irr

    # B2: ck_kpi_block dropped _esc on value/sub/trend (trusted-markup
    # contract). Escape partner-supplied deal_name at the call site so
    # it can't carry HTML into the trusted seam.
    kpi_strip = (
        ck_kpi_block("Deal", _html.escape(r.deal_name[:20]), "", "") +
        ck_kpi_block("Entry → Exit", f"{r.entry_year}→{r.exit_year}", "", "") +
        ck_kpi_block("Hold Years", f"{r.hold_years:.1f}y", "", "") +
        ck_kpi_block("Underwritten MOIC", f"{r.underwritten_moic:.2f}x", "", "") +
        ck_kpi_block("Realized MOIC", f"{r.realized_moic:.2f}x", f"({moic_delta * 100:+.0f}%)", "") +
        ck_kpi_block("Underwritten IRR", f"{r.underwritten_irr * 100:.1f}%", "", "") +
        ck_kpi_block("Realized IRR", f"{r.realized_irr * 100:.1f}%", f"({irr_delta * 100:+.1f}pp)", "") +
        ck_kpi_block("Grade", r.overall_grade.split(" ")[-1], "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    pva_chart = _plan_vs_actual_chart(r.plan_vs_actual)
    pva_tbl = _plan_vs_actual_table(r.plan_vs_actual)
    att_tbl = _attribution_table(r.attribution)
    m_tbl = _milestones_table(r.milestones)
    l_tbl = _lessons_table(r.lessons)
    b_tbl = _bridge_table(r.value_bridge)
    c_tbl = _counter_table(r.counterfactuals)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    # B11 — replace bespoke .ck-page-h1 inline HTML with the editorial-
    # kit ck_page_title primitive (same anti-pattern as deal_pipeline +
    # deal_origination, PRs #160-#161). Title preserves "Deal Post-Mortem"
    # identity from the inline h1. Meta is deal-specific rather than
    # corpus-wide: deal name + letter grade + realized-vs-underwritten
    # MOIC comparison. ck_page_title internally HTML-escapes meta so
    # the raw r.deal_name is safe to pass (matches what the underlying
    # _esc(meta) call did pre-fix with the inline subtitle).
    grade_letter = r.overall_grade.split(" ")[-1]
    page_title = ck_page_title(
        "Deal Post-Mortem",
        eyebrow="DEAL POSTMORTEM",
        meta=(
            f"{r.deal_name} · grade {grade_letter} · "
            f"realized {r.realized_moic:.2f}x vs underwritten "
            f"{r.underwritten_moic:.2f}x"
        ),
    )

    value_anchor = ck_value_anchor(
        "Realized vs Underwritten",
        f"{r.realized_moic:.2f}x MOIC",
        delta=f"vs {r.underwritten_moic:.2f}x underwritten · {r.realized_irr * 100:.1f}% IRR · grade {r.overall_grade}",
        tone="positive" if r.realized_moic >= r.underwritten_moic else "warning",
    )
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {grade_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Deal Grade</div>
    <div style="color:{grade_c};font-weight:700;font-size:14px">{_html.escape(r.overall_grade)} · {r.realized_moic:.2f}x vs {r.underwritten_moic:.2f}x underwritten ({moic_delta * 100:+.0f}%)</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">IRR {r.realized_irr * 100:.1f}% vs {r.underwritten_irr * 100:.1f}% underwritten ({irr_delta * 100:+.1f}pp)</div>
  </div>
  <div style="{cell}"><div style="{h3}">Plan vs Actual — Operating Metrics</div>{pva_chart}{pva_tbl}</div>
  <div style="{cell}"><div style="{h3}">Lever Attribution — Planned vs Realized</div>{att_tbl}</div>
  <div style="{cell}"><div style="{h3}">Milestone Slippage Analysis</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Lessons Learned — Changes for Next Deal</div>{l_tbl}</div>
  <div style="{cell}"><div style="{h3}">Value Bridge — Underwritten to Realized</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Counterfactual Scenarios</div>{c_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Post-Mortem Summary:</strong> {_html.escape(r.deal_name)} — grade <strong style="color:{grade_c}">{_html.escape(r.overall_grade)}</strong>.
    Realized MOIC {r.realized_moic:.2f}x vs {r.underwritten_moic:.2f}x underwritten ({moic_delta * 100:+.0f}%); IRR {r.realized_irr * 100:.1f}% vs {r.underwritten_irr * 100:.1f}% ({irr_delta * 100:+.1f}pp).
    Primary attribution miss: multiple arbitrage (40% capture vs 14.5x→13.2x compression) and bolt-on M&A (67% vs 85% conversion).
    Organic growth and payer rate uplift underperformed but RCM/back-office/debt-paydown levers delivered at or above plan.
    Key lessons for next deal: include labor escalator (critical); extend integration timeline +$2M contingency; model exit multiple stress case at -1.5x;
    underwrite payer uplift at 60% of negotiated target. Best-case counterfactual ceiling: +0.78x MOIC if all levers captured at plan.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(ck_illustrative_note("deal post-mortem figures") + body, "Deal Post-Mortem", active_nav="/deal-postmortem",
        editorial_intro={
            "eyebrow": "DEAL POSTMORTEM",
            "headline": "What the deal postmortem page reveals on this deal.",
            "italic_word": "reveals",
        })
