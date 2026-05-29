"""Tax Structure Analyzer — /tax-structure-analyzer."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row


def _scenarios_chart(items) -> str:
    """Lead chart — exit structures ranked by after-tax proceeds (tone by MOIC)."""
    def _tone(s):
        if s.after_tax_moic >= 3.0: return "positive"
        if s.after_tax_moic >= 2.6: return "teal"
        return "warning"
    top = sorted(items, key=lambda s: s.after_tax_proceeds_mm, reverse=True)
    mx = max((s.after_tax_proceeds_mm for s in top), default=0.0) or 1.0
    rows = [ck_bar_row(s.structure, f"${s.after_tax_proceeds_mm:,.1f}M ({s.after_tax_moic:.2f}x)",
            s.after_tax_proceeds_mm / mx * 100.0, tone=_tone(s)) for s in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = after-tax proceeds vs best structure '
            '· value = net ($M) + MOIC · tone = after-tax MOIC</div></div>')


def _structures_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Structure","left"),("Description","left"),("Tax Treatment","left"),
            ("Gain Recognition","left"),("Complexity","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    c_c = {"low": pos, "medium": acc, "high": warn}
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cc = c_c.get(s.complexity, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.structure)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.tax_treatment)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.gain_recognition)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.complexity)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _scenarios_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Structure","left"),("Gross ($M)","right"),("Federal Tax ($M)","right"),("State Tax ($M)","right"),
            ("Net ($M)","right"),("After-Tax MOIC","right"),("After-Tax IRR","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if s.after_tax_moic >= 3.0 else (acc if s.after_tax_moic >= 2.6 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.structure)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${s.gross_proceeds_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${s.federal_tax_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""${s.state_tax_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""${s.after_tax_proceeds_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{s.after_tax_moic:,.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{s.after_tax_irr * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _rollovers_chart(items) -> str:
    """Summary chart — rollover mechanics by typical equity rolled (tone by tax deferral)."""
    def _tone(r):
        if str(r.tax_deferred).lower() in ("yes", "true", "full"): return "positive"
        if "partial" in str(r.tax_deferred).lower(): return "teal"
        return "warning"
    top = sorted(items, key=lambda r: r.typical_rollover_pct, reverse=True)
    rows = [ck_bar_row(f"{r.rollover_type} · {r.typical_structure}",
            f"{r.typical_rollover_pct * 100:.0f}% rolled · {r.lock_up_months}mo lock",
            r.typical_rollover_pct * 100.0, tone=_tone(r)) for r in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = typical equity rolled '
            '· value = rollover % + lock-up · tone = tax deferral</div></div>')


def _rollovers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Rollover Type","left"),("Structure","left"),("Tax-Deferred","center"),
            ("Lock-Up (mo)","right"),("Typical %","right"),("Notes","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = pos if r.tax_deferred else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.rollover_type)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.typical_structure)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{t_c};font-weight:700">{"YES" if r.tax_deferred else "NO"}</td>',
            f'{ck_data_cell(f"""{r.lock_up_months}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]};font-weight:600">{r.typical_rollover_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.notes)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _blockers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Blocker Type","left"),("Purpose","left"),("Jurisdiction","center"),("Annual Cost ($k)","right"),("Investors","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.blocker_type)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.purpose)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(b.jurisdiction)}</td>',
            f'{ck_data_cell(f"""${b.annual_cost_k:,.1f}""", align="right", mono=True, tone="neg")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.affected_investors)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _state_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("State","left"),("Tax","left"),("Rate","right"),("Apportionment","left"),("Notable","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = neg if s.rate >= 0.08 else (warn if s.rate >= 0.05 else pos)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.state)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(s.relevant_tax)}""", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{s.rate * 100:.2f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.apportionment_method)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.notable_items)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sor_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Topic","left"),("Relevance","left"),("Diligence Action","left"),("Timeline (days pre-close)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = warn if s.timeline_pre_close_days >= 90 else pos
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.topic)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.relevance)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(s.diligence_action)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">{s.timeline_pre_close_days}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_tax_structure_analyzer(params: dict = None) -> str:
    from rcm_mc.data_public.tax_structure_analyzer import compute_tax_structure_analyzer
    r = compute_tax_structure_analyzer()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Recommended Structure", r.recommended_structure[:20], "", "") +
        ck_kpi_block("Tax Savings", f"${r.estimated_tax_savings_mm:,.1f}M", "", "") +
        ck_kpi_block("After-Tax MOIC Uplift", f"+{r.after_tax_moic_uplift:.2f}x", "", "") +
        ck_kpi_block("Structures Evaluated", str(len(r.structures)), "", "") +
        ck_kpi_block("Rollover Mechanics", str(len(r.rollovers)), "", "") +
        ck_kpi_block("Blocker Options", str(len(r.blockers)), "", "") +
        ck_kpi_block("States Diligenced", str(len(r.state_diligence)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    s_tbl = _structures_table(r.structures)
    sc_tbl = _scenarios_table(r.after_tax_scenarios)
    sc_chart = _scenarios_chart(r.after_tax_scenarios)
    ro_tbl = _rollovers_table(r.rollovers)
    ro_chart = _rollovers_chart(r.rollovers)
    b_tbl = _blockers_table(r.blockers)
    st_tbl = _state_table(r.state_diligence)
    sor_tbl = _sor_table(r.sor_items)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Tax Structure Analyzer",
        eyebrow="TAX STRUCTURE ANALYZER",
        meta=f"""Exit-structure options · after-tax scenarios · rollover mechanics · blocker structures · state-by-state diligence — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {pos};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Structuring Recommendation</div>
    <div style="color:{pos};font-weight:700;font-size:14px">{_html.escape(r.recommended_structure)} · +${r.estimated_tax_savings_mm:,.1f}M savings · +{r.after_tax_moic_uplift:.2f}x MOIC uplift</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Recommended holding jurisdiction: {_html.escape(r.recommended_jurisdiction)}</div>
  </div>
  <div style="{cell}"><div style="{h3}">Structure Options Evaluated</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">After-Tax Scenario Comparison</div>{sc_chart}{sc_tbl}</div>
  <div style="{cell}"><div style="{h3}">Rollover Mechanics</div>{ro_chart}{ro_tbl}</div>
  <div style="{cell}"><div style="{h3}">Blocker Structures by Investor Type</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">State-Level Tax Diligence</div>{st_tbl}</div>
  <div style="{cell}"><div style="{h3}">Structure of Review (SOR) Checklist</div>{sor_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Tax Structure Thesis:</strong> Structure choice is a material after-tax value lever — {r.after_tax_moic_uplift:.2f}x MOIC uplift achievable via structural optimization.
    Stock-for-stock merger ({r.recommended_structure}) delivers fully tax-deferred treatment — best for non-cash strategic exits.
    CV rollover approach offers similar tax efficiency with continuation vehicle benefits.
    F-reorg pre-close allows S-corp sellers to optimize; 338(h)(10) best when buyer wants step-up and seller is C-corp.
    State-level nexus diligence is material in multi-state operations — California, Illinois, and New Jersey burden rates exceed 9%; Texas and Nevada favorable for holding structures.
    SOR checklist requires 30-180 day pre-close lead time across 10 workstreams; most time-consuming is TRA structure (180 days) if pursuing IPO path.
  </div>
</div>"""

    from rcm_mc.ui._chartis_kit import ck_illustrative_note as _ckn
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(_ckn("tax-structure model (illustrative defaults; computes off your inputs)") + body, "Tax Structure", active_nav="/tax-structure-analyzer",
        editorial_intro={
            "eyebrow": "TAX STRUCTURE ANALYZER",
            "headline": "What the tax structure analyzer page reveals on this deal.",
            "italic_word": "reveals",
        })
