"""Anti-Trust / FTC Review Screener — /antitrust-screener."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor, ck_illustrative_note


def _hhi_chart(items) -> str:
    """Lead chart for the HHI table — markets ranked by post-merger
    concentration so the most antitrust-exposed MSAs surface first. Bar
    width = CR3 (top-3) market share, value = the merger's HHI delta
    (the DOJ/FTC presumption trigger at +200), tone tracks the table's
    concentration flag (highly red · moderately amber · unconcentrated
    green). Full MSA-level grid stays directly below.
    """
    tone_for = {"highly concentrated": "negative",
                "moderately concentrated": "warning",
                "unconcentrated": "positive"}
    ranked = sorted(items, key=lambda h: h.post_merger_hhi, reverse=True)
    rows = []
    for h in ranked:
        rows.append(ck_bar_row(
            h.market,
            f"+{h.delta_hhi}",
            h.cr3_share_pct * 100.0,
            tone=tone_for.get(h.concentration_flag, "teal"),
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = CR3 top-3 market share · value = HHI delta from merger '
        '(+200 = DOJ/FTC presumption) · tone = concentration flag</div>'
        '</div>'
    )


_EXPLAINER_CSS = """<style>
.ck-as-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-as-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


def _hhi_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Market","left"),("MSA","left"),("Pre-Merger HHI","right"),("Post-Merger HHI","right"),
            ("Δ HHI","right"),("CR3 Share","right"),("Flag","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    flag_c = {"highly concentrated": neg, "moderately concentrated": warn, "unconcentrated": pos}
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        fc = flag_c.get(h.concentration_flag, text_dim)
        d_c = neg if h.delta_hhi >= 200 else (warn if h.delta_hhi >= 100 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(h.market)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(h.msa)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{h.pre_merger_hhi:,}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{h.post_merger_hhi:,}""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">+{h.delta_hhi}</td>',
            f'{ck_data_cell(f"""{h.cr3_share_pct * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{fc};border:1px solid {fc};border-radius:2px;letter-spacing:0.06em">{_html.escape(h.concentration_flag)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hsr_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Threshold","left"),("Current Value ($M)","right"),("Threshold Value ($M)","right"),
            ("Filing Required","center"),("Waiting Period (days)","right"),("Filing Fee ($k)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    _bar_max = max((t.current_value_mm for t in items), default=1.0) or 1.0
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        f_c = neg if t.filing_required else pos
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.threshold)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${t.current_value_mm:,.2f}""", align="right", mono=True, weight=700, bar=t.current_value_mm / _bar_max * 100)}',
            f'{ck_data_cell(f"""${t.threshold_value_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{f_c};font-weight:700">{"REQUIRED" if t.filing_required else "No"}</td>',
            f'{ck_data_cell(f"""{t.waiting_period_days}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${t.filing_fee_k:,.1f}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
            f'<div style="font-size:10px;color:{P.get("text_faint", text_dim)};'
            f'margin-top:6px;font-family:JetBrains Mono,monospace">'
            f'Bar = transaction value relative to the largest threshold shown — '
            f'a longer bar clears a bigger HSR tier.</div>')


def _overlaps_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Geography","left"),("Platform Share","right"),("Target Share","right"),("Combined","right"),
            ("Next Competitor","right"),("Severity","center"),("Remediation","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    sev_c = {"severe — likely 2R": neg, "material — monitor": warn, "moderate": warn, "low": text_dim}
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(o.overlap_severity, text_dim)
        cb_c = neg if o.combined_share_pct >= 50 else (warn if o.combined_share_pct >= 35 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(o.geography)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{o.platform_share_pct:.1f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{o.target_share_pct:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cb_c};font-weight:700">{o.combined_share_pct:.1f}%</td>',
            f'{ck_data_cell(f"""{o.next_competitor_pct:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(o.overlap_severity)}</span>""", align="center")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.remediation_required)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _case_law_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Case","left"),("Year","right"),("Parties","left"),("Outcome","left"),("Precedent","left"),("Relevance","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = P["negative"] if c.relevance_score >= 85 else (P["warning"] if c.relevance_score >= 65 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.case)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.year}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{_html.escape(c.parties)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.outcome)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.precedent_for_platform)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{c.relevance_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _states_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("State","left"),("Trigger","left"),("Notice (days)","right"),("Fee ($k)","right"),
            ("AG Posture","center"),("Challenge Rate","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    post_c = {"active scrutiny": neg, "active review": warn, "standard review": text_dim, "minimal scrutiny": pos}
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = post_c.get(s.state_ag_posture, text_dim)
        cr_c = neg if s.historical_challenge_rate_pct >= 0.15 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.state)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.review_trigger)}</td>',
            f'{ck_data_cell(f"""{s.notice_days}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${s.notification_fee_k:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.state_ag_posture)}</span>""", align="center")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cr_c};font-weight:600">{s.historical_challenge_rate_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _remediations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Option","left"),("Description","left"),("Timeline (mo)","right"),
            ("Cost ($M)","right"),("Deal Value Impact","right"),("Probability of Approval","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if r.probability_of_approval >= 0.80 else (acc if r.probability_of_approval >= 0.55 else neg)
        v_c = neg if r.deal_value_impact_pct >= 0.10 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.option)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.description)}</td>',
            f'{ck_data_cell(f"""{r.timeline_months}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${r.financial_cost_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:700">{r.deal_value_impact_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{r.probability_of_approval * 100:.0f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _chow_antitrust_panel() -> str:
    """Real CMS change-of-ownership anchor — antitrust review IS consolidation
    review, and CHOW is the observed consolidation it scrutinizes. National +
    most-active states are real public CMS data; the HHI/HSR/overlap model
    below is illustrative (computed off your deal-size input)."""
    from rcm_mc.data import snf_chow as _c
    snf = _c.chow_summary()
    if not snf.get("total_chows"):
        return ""
    hosp = _c.hospital_chow_summary()
    top = _c.top_chow_states(6)

    border = P["border"]; tprim = P["text"]; tdim = P["text_dim"]; acc = P["accent"]
    mx = max((int(r["chow_count"]) for r in top), default=1) or 1
    rows = "".join(
        f'<tr>'
        f'<td style="padding:3px 8px;font-family:JetBrains Mono,monospace;font-size:11px;color:{tprim}">{_html.escape(str(r["state"]))}</td>'
        f'<td style="padding:3px 8px;width:50%">'
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
    Real CMS ownership-change activity &mdash; the consolidation antitrust scrutinizes
    <span style="color:{acc};font-weight:600"> · LIVE</span>
  </div>
  <div style="display:grid;grid-template-columns:auto auto 1fr;gap:18px;align-items:start">
    <div><div style="font-family:JetBrains Mono,monospace;font-size:18px;color:{tprim};
      font-variant-numeric:tabular-nums">{snf_n:,}</div>
      <div style="font-size:10px;color:{tdim}">SNF ownership changes<br>{y0}&ndash;{y1}</div></div>
    <div><div style="font-family:JetBrains Mono,monospace;font-size:18px;color:{tprim};
      font-variant-numeric:tabular-nums">{hosp_n:,}</div>
      <div style="font-size:10px;color:{tdim}">Hospital ownership changes<br>{y0}&ndash;{y1}</div></div>
    <div>
      <div style="font-size:9px;color:{P["text_faint"]};margin-bottom:4px">MOST ACTIVE CONSOLIDATION STATES (SNF CHOW)</div>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P["text_faint"]}">
    CMS public ownership/CHOW files. Real consolidation activity &mdash; the serial-
    acquisition theory FTC pursues post-USAP. The HHI / HSR / market-overlap figures
    below are illustrative and computed off your deal-size input.
  </div>
</div>'''


def render_antitrust_screener(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    deal_size = _f("deal_size", 485.0)
    acquirer_size = _f("acquirer_size", 1850.0)
    combined_share = _f("combined_share", 50.0)
    state = str(params.get("state", "TX") or "TX")[:24]

    from rcm_mc.data_public.antitrust_screener import compute_antitrust_screener
    r = compute_antitrust_screener(
        deal_size_mm=deal_size, acquirer_size_mm=acquirer_size,
        combined_share_pct=combined_share, state=state,
    )

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    score_c = neg if r.overall_risk_score >= 65 else (warn if r.overall_risk_score >= 40 else pos)

    kpi_strip = (
        ck_kpi_block("Deal Size", f"${r.deal_size_mm:,.0f}M", "", "") +
        ck_kpi_block("HSR Required", "YES" if r.hsr_required else "NO", "", "") +
        ck_kpi_block("2R Probability", f"{r.second_request_probability * 100:.0f}%", "", "") +
        ck_kpi_block("Overall Risk", f"{r.overall_risk_score}/100", "", "") +
        ck_kpi_block("Timeline (mo)", str(r.recommended_timeline_months), "", "") +
        ck_kpi_block("Markets Screened", str(len(r.hhi_analysis)), "", "") +
        ck_kpi_block("State Reviews", str(len(r.state_reviews)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    _inp = (f"background:{panel};border:1px solid {border};color:{text};"
            f"padding:5px 8px;font-size:11px;font-family:JetBrains Mono,monospace")
    _state_opts = "".join(
        f'<option value="{_html.escape(sv)}"{" selected" if state.upper() == sv else ""}>{_html.escape(sv)} · {_html.escape(lbl)}</option>'
        for sv, lbl in (
            ("CA", "active scrutiny"), ("OR", "active scrutiny"), ("NY", "active scrutiny"),
            ("MA", "active review"), ("WA", "standard"), ("CT", "standard"),
            ("IL", "standard"), ("CO", "standard"), ("TX", "minimal"), ("FL", "minimal"),
        )
    )
    form = f"""
<form method="GET" action="/antitrust-screener" style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim};display:flex;flex-direction:column;gap:3px">Deal size ($M)<input name="deal_size" value="{deal_size:.0f}" type="number" step="25" min="0" style="{_inp};width:96px"/></label>
  <label style="font-size:11px;color:{text_dim};display:flex;flex-direction:column;gap:3px">Acquirer size ($M)<input name="acquirer_size" value="{acquirer_size:.0f}" type="number" step="100" min="0" style="{_inp};width:104px"/></label>
  <label style="font-size:11px;color:{text_dim};display:flex;flex-direction:column;gap:3px">Top-market combined share (%)<input name="combined_share" value="{combined_share:.0f}" type="number" step="5" min="0" max="100" style="{_inp};width:130px"/></label>
  <label style="font-size:11px;color:{text_dim};display:flex;flex-direction:column;gap:3px">Primary review state<select name="state" style="{_inp};min-width:150px">{_state_opts}</select></label>
  <button type="submit" style="background:{acc};color:#fff;border:1px solid {acc};padding:7px 16px;font-size:11px;font-weight:600;font-family:JetBrains Mono,monospace;cursor:pointer">Screen &rarr;</button>
</form>
<div style="font-size:10.5px;color:{text_dim};margin:-8px 0 16px;line-height:1.5;max-width:74ch">
  Risk responds to all four levers: <strong style="color:{text}">combined market share</strong> is the dominant
  driver (&gt;50% is presumptively anticompetitive under the 2023 Merger Guidelines), then deal size (scrutiny + HSR
  fee tier), acquirer footprint (post-USAP serial-acquisition theory), and the primary review state&rsquo;s AG posture.
</div>"""

    h_chart = _hhi_chart(r.hhi_analysis)
    h_tbl = _hhi_table(r.hhi_analysis)
    hsr_tbl = _hsr_table(r.hsr_thresholds)
    o_tbl = _overlaps_table(r.overlaps)
    c_tbl = _case_law_table(r.case_law)
    s_tbl = _states_table(r.state_reviews)
    rem_tbl = _remediations_table(r.remediations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    best_remediation = min(r.remediations, key=lambda x: x.timeline_months + x.financial_cost_mm * 0.5 + x.deal_value_impact_pct * 100 - x.probability_of_approval * 50)
    # 2026-05-30 audit P5 editorial: FTC review is THE mechanism of
    # antitrust review for the deal sizes the page screens — the
    # slash-dual was a restatement. "Antitrust Screener" matches the
    # eyebrow and the route /antitrust-screener.
    page_title = ck_page_title(
        "Antitrust Screener",
        eyebrow="ANTITRUST SCREENER",
        meta=(
            f"Risk score {r.overall_risk_score}/100 · "
            f"Second Request probability {r.second_request_probability * 100:.0f}% · "
            f"{r.corpus_deal_count:,} corpus deals"
        ),
    )
    as_explainer = (
        '<p class="ck-as-explainer">'
        "<em>What the antitrust screener reveals on this deal.</em> "
        "HSR thresholds, HHI/CR3 concentration, market overlap, FTC case law, "
        "state-AG posture, and remediation options — drawn from corpus deal history."
        "</p>"
    )
    _at_tone = ("negative" if r.overall_risk_score >= 70
                else "warning" if r.overall_risk_score >= 50 else "teal")
    value_anchor = ck_value_anchor(
        "Antitrust Risk",
        f"{r.overall_risk_score}/100 risk",
        delta=f"${r.deal_size_mm:,.0f}M deal · {r.second_request_probability * 100:.0f}% second-request prob · {r.recommended_timeline_months}mo timeline",
        tone=_at_tone,
    )
    body = page_title + as_explainer + f"""
<div class="ck-page-wrap">
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  {_chow_antitrust_panel()}
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {score_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Screening Verdict</div>
    <div style="color:{score_c};font-weight:700;font-size:14px">Risk {r.overall_risk_score}/100 · Second Request probability {r.second_request_probability * 100:.0f}% · Recommended timeline {r.recommended_timeline_months} months</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Recommended remediation: <strong style="color:{text}">{_html.escape(best_remediation.option)}</strong></div>
  </div>
  <div style="{cell}"><div style="{h3}">HHI / Market Concentration Analysis (MSA-Level)</div>{h_chart}{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">HSR Threshold Analysis</div>{hsr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Overlap (Platform + Target)</div>{o_tbl}</div>
  <div style="{cell}"><div style="{h3}">FTC Case Law Precedents</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">State-Level Review Exposure</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Remediation Options Matrix</div>{rem_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Anti-Trust Thesis:</strong> ${r.deal_size_mm:,.0f}M deal triggers HSR filing; Second Request probability {r.second_request_probability * 100:.0f}% given {sum(1 for o in r.overlaps if 'severe' in o.overlap_severity)} severe market overlaps in Texas MSAs.
    Post-USAP / Welsh Carson (2023) enforcement era, FTC is scrutinizing serial-acquisition theories against PE platform sponsors — relevance score 95.
    Recommended path: "Restructure deal (exclude 2 overlap markets)" — 92% approval probability, 6-month timeline, 25.8% deal value reduction.
    Alternative divestiture path preserves more value but extends timeline to 12-18 months and introduces execution risk.
    California, New York, Oregon, and Massachusetts notifications required given deal size; Colorado SB 21-003 also applies.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(ck_illustrative_note("antitrust / HHI screening figures") + body, "Anti-Trust Screener", active_nav="/antitrust-screener",
        extra_css=_EXPLAINER_CSS)
