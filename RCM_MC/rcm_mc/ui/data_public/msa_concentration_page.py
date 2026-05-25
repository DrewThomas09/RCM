"""MSA Provider Market Concentration — /msa-concentration."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor, ck_scatter, ck_illustrative_note


def _msas_scatter(items):
    """Quadrant — market size (providers) vs concentration (HHI), so
    large + fragmented MSAs (lower-right) read as rollup targets."""
    import statistics
    pts, sz = [], []
    for m in items:
        s = (m.market_structure or '').lower()
        tn = ('positive' if 'fragment' in s
              else 'warning' if ('concentrat' in s or 'consolidat' in s) else 'teal')
        pts.append((m.providers, m.hhi, m.msa, tn)); sz.append(m.providers)
    return ck_scatter(
        pts, x_label='Providers (market size)', y_label='HHI (concentration)',
        x_ref=(statistics.median(sz) if sz else None), y_ref=2500.0,
        caption='Each dot = an MSA · lower-right = large + fragmented (rollup target) · HHI 2500 = DOJ-concentrated line',
    )

def _msas_chart(items) -> str:
    """Lead chart for the MSA-concentration table — MSAs ranked by HHI.
    Bar = CR3 top-3 share; value = HHI; tone marks market structure
    (highly concentrated red, moderately amber, fragmented green)."""
    def _tone(struct):
        s = (struct or "").lower()
        if "highly" in s: return "negative"
        if "moderately" in s: return "warning"
        if "fragmented" in s or "competitive" in s: return "positive"
        return "teal"
    rows = []
    for m in sorted(items, key=lambda m: m.hhi, reverse=True):
        rows.append(ck_bar_row(m.msa, f"{m.hhi:,.0f}", m.cr3_pct * 100.0, tone=_tone(m.market_structure)))
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = CR3 top-3 share \u00b7 value = HHI '
            '\u00b7 tone = market structure</div></div>')



def _msas_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("MSA","left"),("Specialty","center"),("Providers","right"),("HHI","right"),
            ("CR3","right"),("CR5","right"),("Structure","center"),("Top Operator","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    s_c = {"fragmented": pos, "moderately concentrated": warn, "highly concentrated": neg}
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = s_c.get(m.market_structure, text_dim)
        hhi_c = neg if m.hhi >= 2500 else (warn if m.hhi >= 1500 else pos)
        cr3_c = neg if m.cr3_pct >= 0.50 else (warn if m.cr3_pct >= 0.30 else pos)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(m.msa)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.specialty)}</td>',
            f'{ck_data_cell(f"""{m.providers:,}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hhi_c};font-weight:700">{m.hhi:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cr3_c};font-weight:700">{m.cr3_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{m.cr5_pct * 100:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.market_structure)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{_html.escape(m.top_operator)}""", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _regimes_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Regime","left"),("Description","left"),("HHI Range","right"),("CR3 Range","right"),
            ("Typical MOIC","right"),("Typical Hold (yr)","right"),("MSAs in Sample","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if r.typical_moic >= 2.8 else (acc if r.typical_moic >= 2.4 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.regime)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.description)}</td>',
            f'{ck_data_cell(f"""{_html.escape(r.hhi_range)}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{_html.escape(r.cr3_range)}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{r.typical_moic:.2f}x</td>',
            f'{ck_data_cell(f"""{r.typical_hold_years:.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{r.msa_count_in_sample}""", align="right", mono=True)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _whitespace_chart(items) -> str:
    """Summary chart — whitespace markets ranked by rollup opportunity score."""
    def _tone(w):
        p = (w.rollup_priority or "").lower()
        if "high" in p: return "positive"
        if "medium" in p or "mod" in p: return "teal"
        return "navy"
    top = sorted(items, key=lambda w: w.whitespace_score, reverse=True)
    mx = max((w.whitespace_score for w in top), default=0.0) or 1.0
    rows = [ck_bar_row(f"{w.msa}, {w.state}",
            f"score {w.whitespace_score:.0f} · {w.total_providers:,} providers",
            w.whitespace_score / mx * 100.0, tone=_tone(w)) for w in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = whitespace score vs top market '
            '· value = score + providers · tone = rollup priority</div></div>')


def _whitespace_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("MSA","left"),("State","center"),("Pop (000)","right"),("Providers","right"),
            ("Top Share","right"),("CR3","right"),("Whitespace Score","right"),("Priority","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    p_c = {"priority expansion": pos, "active target": acc, "fill-in": warn, "selective": text_dim}
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = p_c.get(w.rollup_priority, text_dim)
        ws_c = pos if w.whitespace_score >= 80 else (acc if w.whitespace_score >= 70 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(w.msa)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(w.state)}</td>',
            f'{ck_data_cell(f"""{w.population_000:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{w.total_providers:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{w.top_operator_share_pct * 100:.1f}%""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{w.top3_combined_pct * 100:.1f}%""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ws_c};font-weight:700">{w.whitespace_score}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(w.rollup_priority)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _stress_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Scenario","left"),("HHI Delta","right"),("CR3 Delta","right"),
            ("Likely FTC Action","center"),("Value at Risk ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        h_c = neg if s.hhi_delta >= 500 else (warn if s.hhi_delta >= 200 else text_dim)
        v_c = neg if s.estimated_value_at_risk_mm > 0 else pos
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.scenario)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{h_c};font-weight:700">+{s.hhi_delta}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">+{s.cr3_delta_pp * 100:.1f}pp</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.likely_ftc_action)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:700">${s.estimated_value_at_risk_mm:,.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _operators_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Operator","left"),("Markets Active","right"),("Practices","right"),
            ("Providers","right"),("Median HHI Contribution","right"),("Strategy","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(o.operator)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{o.markets_active}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{o.total_practices:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{o.total_providers:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{o.median_hhi_contribution:,}""", align="right", mono=True, tone="acc", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.growth_strategy)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _chow_state_panel() -> str:
    """Real CMS change-of-ownership anchor at the state level — the
    observable consolidation behind market concentration. The MSA HHI
    detail below is illustrative; this panel is real public CMS CHOW
    data, so the page grounds its rollup/concentration thesis in
    actual ownership-change behaviour."""
    from rcm_mc.data import snf_chow as _c
    snf = _c.chow_summary()
    if not snf.get("total_chows"):
        return ""
    hosp = _c.hospital_chow_summary()
    top = _c.top_chow_states(10)

    border = P["border"]; tprim = P["text"]; tdim = P["text_dim"]; acc = P["accent"]
    mx = max((int(r["chow_count"]) for r in top), default=1) or 1
    rows = "".join(
        f'<tr>'
        f'<td style="padding:3px 8px;font-family:JetBrains Mono,monospace;font-size:11px;color:{tprim}">{_html.escape(str(r["state"]))}</td>'
        f'<td style="padding:3px 8px;width:60%">'
        f'<svg width="100%" height="9" preserveAspectRatio="none" viewBox="0 0 100 9">'
        f'<rect x="0" y="1" width="{int(int(r["chow_count"])/mx*100)}" height="7" fill="{acc}" opacity="0.75"/></svg></td>'
        f'<td style="padding:3px 8px;text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;'
        f'font-variant-numeric:tabular-nums;color:{tprim}">{int(r["chow_count"]):,}</td>'
        f'</tr>'
        for r in top
    )
    snf_n = int(snf.get("total_chows", 0)); hosp_n = int(hosp.get("total_chows", 0))
    y0, y1 = snf.get("year_min"), snf.get("year_max")
    return f'''
<div style="background:{P["panel"]};border:1px solid {border};border-left:3px solid {acc};
  padding:14px 16px;margin-bottom:16px">
  <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px">
    Real CMS consolidation by state &mdash; change-of-ownership
    <span style="color:{acc};font-weight:600"> · LIVE</span>
  </div>
  <div style="display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start">
    <div style="white-space:nowrap">
      <div style="font-family:JetBrains Mono,monospace;font-size:18px;color:{tprim};
        font-variant-numeric:tabular-nums">{snf_n:,}</div>
      <div style="font-size:10px;color:{tdim};margin-bottom:8px">SNF CHOWs {y0}&ndash;{y1}</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:18px;color:{tprim};
        font-variant-numeric:tabular-nums">{hosp_n:,}</div>
      <div style="font-size:10px;color:{tdim}">Hospital CHOWs {y0}&ndash;{y1}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{P["text_faint"]};margin-bottom:4px">TOP CONSOLIDATING STATES (SNF CHOW COUNT)</div>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P["text_faint"]}">
    CMS public ownership/CHOW files. State-level real consolidation &mdash; the
    MSA HHI / operator detail below is illustrative; use this panel as the
    observed-market reality, the MSA tables as the structural framework.
  </div>
</div>'''


def render_msa_concentration(params: dict = None) -> str:
    from rcm_mc.data_public.msa_concentration import compute_msa_concentration
    r = compute_msa_concentration()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("MSAs Analyzed", str(r.total_msas_analyzed), "", "") +
        ck_kpi_block("Fragmented", str(r.fragmented_count), "", "") +
        ck_kpi_block("Moderately Concentrated", str(r.moderately_concentrated_count), "", "") +
        ck_kpi_block("Highly Concentrated", str(r.highly_concentrated_count), "", "") +
        ck_kpi_block("Avg HHI", f"{r.avg_hhi:,}", "", "") +
        ck_kpi_block("Avg CR3", f"{r.avg_cr3_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Whitespace MSAs", str(sum(1 for w in r.whitespace if w.whitespace_score >= 75)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    m_chart = _msas_chart(r.msa_details)
    m_scatter = _msas_scatter(r.msa_details)
    m_tbl = _msas_table(r.msa_details)
    value_anchor = ck_value_anchor(
        "MSA Concentration",
        f"{r.avg_hhi:,.0f} avg HHI",
        delta=f"{r.total_msas_analyzed} MSAs \u00b7 {r.avg_cr3_pct * 100:.0f}% avg CR3 \u00b7 {r.highly_concentrated_count} highly concentrated",
        tone="teal",
    )
    r_tbl = _regimes_table(r.regimes)
    w_tbl = _whitespace_table(r.whitespace)
    w_chart = _whitespace_chart(r.whitespace)
    s_tbl = _stress_table(r.stress_scenarios)
    o_tbl = _operators_table(r.top_operators)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "MSA Provider Market Concentration",
        eyebrow="MSA CONCENTRATION",
        meta=f"""HHI · CR3 · CR5 · regime classification · whitespace scoring · stress scenarios · top operators — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("concentration figures")}
  {_chow_state_panel()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">MSA-Level Concentration Analysis</div>{m_chart}{m_scatter}{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Regime Classification &amp; Expected Returns</div>{r_tbl}</div>
  <div style="{cell}"><div style="{h3}">Whitespace Markets — Rollup Priority</div>{w_chart}{w_tbl}</div>
  <div style="{cell}"><div style="{h3}">Stress-Test Scenarios — FTC Action Likelihood</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Active Healthcare Platform Operators</div>{o_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Market Concentration Thesis:</strong> {r.total_msas_analyzed} MSAs profiled.
    Avg HHI {r.avg_hhi:,} places portfolio in <strong>moderately concentrated</strong> zone — sweet spot for PE rollups (CR3 &lt;50%, typical MOIC 2.62x).
    {r.fragmented_count} markets remain fragmented — platform opportunities in NY/LA dermatology and Miami/Tampa home health.
    {r.highly_concentrated_count} highly concentrated markets (Austin anesthesia, SF fertility, Philadelphia anesthesia) face FTC scrutiny and should be avoided without remediation.
    Whitespace scoring surfaces Raleigh, Charlotte, and Jacksonville as highest-priority expansion targets.
    Use /antitrust-screener for deal-level FTC screening.
  </div>
</div>"""

    return chartis_shell(body, "MSA Concentration", active_nav="/msa-concentration",
        editorial_intro={
            "eyebrow": "MSA CONCENTRATION",
            "headline": "What the msa concentration page reveals on this deal.",
            "italic_word": "reveals",
        })
