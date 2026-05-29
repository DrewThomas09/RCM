"""Value-Creation Backtester — /backtester."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_paired_block, ck_page_title, ck_bar_row, ck_illustrative_note
from rcm_mc.ui.chartis._helpers import render_page_explainer


def _levers_chart(items):
    """Summary chart — value-creation levers by risk-adjusted value (tone by realization)."""
    def _tone(v):
        if v.realization_rate_pct >= 0.80: return "positive"
        if v.realization_rate_pct >= 0.55: return "teal"
        return "warning"
    top = sorted(items, key=lambda v: v.risk_adjusted_mm, reverse=True)
    total = sum(v.risk_adjusted_mm for v in top) or 1.0
    rows = [ck_bar_row(f"{v.lever}",
            f"${v.risk_adjusted_mm:,.1f}M risk-adj · ${v.target_contribution_mm:,.1f}M target · {v.realization_rate_pct * 100:.0f}%",
            v.risk_adjusted_mm / total * 100.0, tone=_tone(v)) for v in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of risk-adjusted value '
            '· value = risk-adj ($M) + target + realization · tone = realization rate</div></div>')


def _levers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Lever","left"),("Target ($M)","right"),("Base Rate P50 ($M)","right"),
            ("Base Rate P75 ($M)","right"),("Realization %","right"),("Risk-Adj ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, lv in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        real_c = pos if lv.realization_rate_pct >= 0.70 else (warn if lv.realization_rate_pct >= 0.55 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(lv.lever)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${lv.target_contribution_mm:,.2f}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""${lv.base_rate_p50_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${lv.base_rate_p75_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{real_c};font-weight:700">{lv.realization_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${lv.risk_adjusted_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _buckets_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sector","left"),("Vintage","center"),("Size","center"),("N","right"),
            ("Realized MOIC P25","right"),("P50","right"),("P75","right"),("Mean","right"),("IRR P50","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items[:40]):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if b.realized_moic_p50 >= 2.5 else (acc if b.realized_moic_p50 >= 2.0 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.sector[:26])}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(b.vintage_range)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(b.size_bucket)}</td>',
            f'{ck_data_cell(f"""{b.n_deals}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{b.realized_moic_p25:.2f}x""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{b.realized_moic_p50:.2f}x</td>',
            f'{ck_data_cell(f"""{b.realized_moic_p75:.2f}x""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{b.realized_moic_mean:.2f}x""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{b.realized_irr_p50 * 100:.1f}%""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _calibration_paired_rows(items) -> tuple:
    headers = [
        "Predicted MOIC", "Realized P25", "Realized P50",
        "Realized P75", "N Deals", "Calibration Error",
    ]
    rows: list = []
    errs: list = []
    for c in items:
        rows.append([
            f"{c.predicted_moic:.2f}x",
            f"{c.realized_moic_p25:.2f}x",
            f"{c.realized_moic_p50:.2f}x",
            f"{c.realized_moic_p75:.2f}x",
            str(c.n_deals),
            f"{c.calibration_error * 100:+.1f}%",
        ])
        errs.append(abs(c.calibration_error))
    hot = [errs.index(max(errs))] if errs else []
    return headers, rows, hot


def _attribution_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Driver","left"),("Correlation","right"),("P50 Realized MOIC","right"),
            ("P75 Realized MOIC","right"),("Signal","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    sig_c = {"strong": pos, "moderate": warn, "negative": neg}
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sig_c.get(a.signal_strength, text_dim)
        corr_c = pos if a.correlation > 0.40 else (text_dim if a.correlation > 0 else neg)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(a.driver)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{corr_c};font-weight:700">{a.correlation:+.2f}</td>',
            f'{ck_data_cell(f"""{a.p50_realized_moic:.2f}x""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{a.p75_realized_moic:.2f}x""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(a.signal_strength)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comparables_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Comparable Deal","left"),("Sector","left"),("Year","right"),
            ("Entry Mult","right"),("Realized MOIC","right"),("Hold (yr)","right"),("Similarity","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if c.realized_moic >= 2.5 else (acc if c.realized_moic >= 1.8 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal_name[:30])}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.sector[:24])}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.year}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.entry_multiple:.2f}x""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{c.realized_moic:.2f}x</td>',
            f'{ck_data_cell(f"""{c.hold_years:.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.similarity_score:.3f}""", align="right", mono=True, tone="acc")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _calibration_svg(items) -> str:
    if not items: return ""
    w, h = 560, 240
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 50
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    all_vals = []
    for c in items:
        all_vals.extend([c.predicted_moic, c.realized_moic_p25, c.realized_moic_p75])
    max_v = max(all_vals) + 0.3
    min_v = min(all_vals) - 0.3
    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]
    # 45-degree perfect-calibration line
    elts = [f'<rect width="{w}" height="{h}" fill="{bg}"/>',
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Calibration: Predicted vs Realized MOIC (perfect line = 45°)</text>']

    def _xy(px, py):
        x = pad_l + ((px - min_v) / (max_v - min_v)) * inner_w
        y = (h - pad_b) - ((py - min_v) / (max_v - min_v)) * inner_h
        return x, y

    # Diagonal
    x1, y1 = _xy(min_v, min_v)
    x2, y2 = _xy(max_v, max_v)
    elts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{text_dim}" stroke-width="0.7" stroke-dasharray="4,4"/>')

    for c in items:
        # P25-P75 range bar
        _, y25 = _xy(c.predicted_moic, c.realized_moic_p25)
        _, y75 = _xy(c.predicted_moic, c.realized_moic_p75)
        x, y50 = _xy(c.predicted_moic, c.realized_moic_p50)
        elts.append(f'<line x1="{x}" y1="{y25}" x2="{x}" y2="{y75}" stroke="{acc}" stroke-width="3" opacity="0.5"/>')
        elts.append(f'<circle cx="{x}" cy="{y50}" r="4" fill="{pos}" stroke="{bg}" stroke-width="1"/>')
        elts.append(f'<text x="{x}" y="{y50 - 10}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{c.realized_moic_p50:.2f}x (n={c.n_deals})</text>')

    # Axis labels
    elts.append(f'<text x="{w / 2}" y="{h - 8}" fill="{text_dim}" font-size="10" text-anchor="middle" font-family="Inter,sans-serif">Predicted MOIC →</text>')
    elts.append(f'<text x="{15}" y="{h / 2}" fill="{text_dim}" font-size="10" text-anchor="middle" font-family="Inter,sans-serif" transform="rotate(-90 15 {h / 2})">Realized MOIC →</text>')

    return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">{"".join(elts)}</svg>'


def render_value_backtester(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    sector = params.get("sector", "ASC")
    pred_moic = _f("pred_moic", 2.65)
    ev = _f("ev", 225.0)
    entry_mult = _f("entry_mult", 11.5)
    ebitda_growth = _f("ebitda_growth", 35.0)
    margin_exp = _f("margin_exp", 12.0)
    multiple_arb = _f("multiple_arb", 45.0)
    synergy = _f("synergy", 8.0)

    from rcm_mc.data_public.value_backtester import compute_value_backtester
    r = compute_value_backtester(
        target_sector=sector, target_predicted_moic=pred_moic,
        target_ev_mm=ev, target_entry_multiple=entry_mult,
        ebitda_growth_target_mm=ebitda_growth,
        margin_exp_target_mm=margin_exp,
        multiple_arb_target_mm=multiple_arb,
        synergy_target_mm=synergy,
    )

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    rec_c = pos if "IN LINE" in r.recommendation or "CONSERVATIVE" in r.recommendation else (warn if "STRETCH" in r.recommendation else neg)

    kpi_strip = (
        ck_kpi_block("Target Sector", r.target_sector[:14], "", "") +
        ck_kpi_block("Predicted MOIC", f"{r.target_predicted_moic:.2f}x", "", "") +
        ck_kpi_block("Entry Multiple", f"{r.target_entry_multiple:.2f}x", "", "") +
        ck_kpi_block("Sector P50 Realized", f"{r.realized_base_rate_p50:.2f}x", "", "") +
        ck_kpi_block("Sector P90 Realized", f"{r.realized_base_rate_p90:.2f}x", "", "") +
        ck_kpi_block("Calibration Gap", f"{r.calibration_gap_pct * 100:+.1f}%", "", "") +
        ck_kpi_block("Comparable Deals", str(len(r.comparables)), "", "") +
        ck_kpi_block("Corpus", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _calibration_svg(r.calibration_points)
    cal_headers, cal_rows, cal_hot = _calibration_paired_rows(r.calibration_points)
    calibration_paired = ck_paired_block(
        svg,
        data_label="MOIC Calibration · Predicted vs Realized",
        headers=cal_headers,
        rows=cal_rows,
        data_source=f"{len(r.calibration_points)} buckets · worst-calibrated marked",
        hot_rows=cal_hot,
    )
    lv_tbl = _levers_table(r.levers)
    lv_chart = _levers_chart(r.levers)
    bk_tbl = _buckets_table(r.buckets)
    at_tbl = _attribution_table(r.attribution)
    comp_tbl = _comparables_table(r.comparables)

    sectors = ["ASC", "Primary Care", "Behavioral Health", "Dental DSO", "Dermatology",
               "Orthopedics", "Physical Therapy", "Cardiology", "Home Health", "Hospice",
               "Ophthalmology", "Fertility / IVF", "Telehealth Platform", "Oncology"]
    sector_opts = "".join(f'<option value="{_html.escape(s)}"{" selected" if s == sector else ""}>{_html.escape(s)}</option>' for s in sectors)

    disambig = (
        f'<div style="background:{panel};border:1px solid {border};'
        f'border-left:3px solid {acc};padding:10px 14px;margin-bottom:14px;'
        f'border-radius:3px;">'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:9.5px;'
        f'letter-spacing:0.15em;color:{text_dim};">VALUE BRIDGE BACKTEST</span>'
        f'<div style="color:{text};font-size:12px;margin-top:4px;">'
        f'This page backtests an <em>individual deal model</em> — '
        f'predicted MOIC vs corpus calibration + lever attribution. '
        f'For the <strong>platform prediction audit</strong> (how well '
        f'platform outputs matched realized outcomes across the 655-deal '
        f'corpus) see '
        f'<a href="/corpus-backtest" style="color:{acc};">/corpus-backtest</a>.'
        f'</div></div>'
    )
    form = disambig + f"""
<form method="GET" action="/backtester" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector<select name="sector" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{sector_opts}</select></label>
  <label style="font-size:11px;color:{text_dim}">Predicted MOIC<input name="pred_moic" value="{pred_moic}" type="number" step="0.1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">EV ($M)<input name="ev" value="{ev}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Entry Mult<input name="entry_mult" value="{entry_mult}" type="number" step="0.5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Growth Target ($M)<input name="ebitda_growth" value="{ebitda_growth}" type="number" step="5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <label style="font-size:11px;color:{text_dim}">Multiple Arb ($M)<input name="multiple_arb" value="{multiple_arb}" type="number" step="5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Backtest</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Value-Creation Backtester",
        eyebrow="VALUE BACKTESTER",
        meta=f"""Predicted MOIC vs realized base rates · lever attribution · calibration chart · comparable deal cohort — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {rec_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Backtest Verdict</div>
    <div style="color:{rec_c};font-weight:700;font-size:14px">{_html.escape(r.recommendation)}</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Predicted {r.target_predicted_moic:.2f}x vs sector P50 realized {r.realized_base_rate_p50:.2f}x (gap {r.calibration_gap_pct * 100:+.1f}%)</div>
  </div>
  {calibration_paired}
  <div style="{cell}"><div style="{h3}">Value-Creation Lever Attribution — Target vs Base Rate</div>{lv_chart}{lv_tbl}</div>
  <div style="{cell}"><div style="{h3}">Corpus Base-Rate Buckets — Sector × Vintage × Size</div>{bk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Driver Attribution — What Predicts Realized MOIC</div>{at_tbl}</div>
  <div style="{cell}"><div style="{h3}">Most Similar Corpus Deals</div>{comp_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Backtester Methodology:</strong> Corpus of {r.corpus_deal_count:,} deals partitioned into {len([d for d in r.buckets if d.n_deals >= 3])} bucketed realized-outcome cohorts (n≥3).
    Base rates computed at P25/P50/P75 of realized MOIC. Predicted MOIC compared to sector-level P50 realized base rate to produce calibration gap.
    Lever-level realization rates derived from corpus observation — multiple arbitrage and exit re-rating have historically underperformed targets (~48%),
    while organic growth and operating leverage are more reliable (~80%).
    Use this to interrogate any proposed value-creation plan: which levers are overweighted relative to base rate?
  </div>
</div>"""

    explainer = render_page_explainer(
        what=(
            "Value-creation backtester: compares a proposed "
            "bridge-by-lever plan against corpus P50/P75 base rates, "
            "applies lever-level realization rates from the corpus "
            "(multiple arbitrage and exit re-rating historically "
            "~48% realized; organic growth and operating leverage "
            "~80%), and returns a risk-adjusted bridge. Distinct from "
            "/corpus-backtest (deal-level prediction vs realized)."
        ),
        source="data_public/value_backtester.py; base_rates.py.",
        page_key="value-backtester",
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        ck_illustrative_note("backtest figures (illustrative seed corpus)") + explainer + body, "Value Backtester", active_nav="/backtester",
        editorial_intro={
            "eyebrow": "VALUE BACKTESTER",
            "headline": "What the bridge looked like in retrospect.",
            "italic_word": "retrospect",
        },
    )
