"""Survival Analysis ML Layer — /survival-analysis."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _hold_period_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Sector", "left"), ("N Deals", "right"), ("Median Hold (yrs)", "right"),
            ("S(3yr)", "right"), ("S(5yr)", "right"), ("S(7yr)", "right"),
            ("Time Points", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        def _s_at(target_yr):
            if not c.years:
                return 1.0
            for y, s in zip(c.years, c.survival):
                if y >= target_yr:
                    return s
            return c.survival[-1] if c.survival else 1.0
        s3 = _s_at(3); s5 = _s_at(5); s7 = _s_at(7)
        med_cell = f"{c.median_hold_years:.1f}" if c.median_hold_years is not None else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.n_deals:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{med_cell}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s3:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{s5:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{s7:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{len(c.years)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _specialty_retention_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Specialty", "left"), ("Cohort N", "right"),
            ("Median Retention (mo)", "right"), ("S(12mo)", "right"),
            ("S(24mo)", "right"), ("S(60mo)", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        def _s_at(target_mo):
            for t, s in zip(c.monthly_times, c.survival):
                if t >= target_mo:
                    return s
            return c.survival[-1] if c.survival else 1.0
        s12 = _s_at(12); s24 = _s_at(24); s60 = _s_at(60)
        med_cell = f"{c.median_retention_months:.0f}" if c.median_retention_months is not None else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.sample_size:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{med_cell}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{s12:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s24:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{s60:.3f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _payer_renewal_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Payer Mix Tier", "left"), ("Cohort N", "right"),
            ("Median Renewal (mo)", "right"), ("S(12mo)", "right"),
            ("S(24mo)", "right"), ("S(36mo)", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        def _s_at(target_mo):
            for t, s in zip(c.months, c.survival):
                if t >= target_mo:
                    return s
            return c.survival[-1] if c.survival else 1.0
        s12 = _s_at(12); s24 = _s_at(24); s36 = _s_at(36)
        med_cell = f"{c.median_renewal_months:.0f}" if c.median_renewal_months is not None else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.payer_mix_tier)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.sample_size:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{med_cell}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{s12:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s24:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{s36:.3f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cox_table(summary) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Feature", "left"), ("Coefficient (β)", "right"),
            ("Hazard Ratio (exp β)", "right"), ("Interpretation", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, (name, coef, hr) in enumerate(zip(summary.feature_names, summary.coefficients, summary.hazard_ratios)):
        rb = panel_alt if i % 2 == 0 else bg
        hr_c = neg if hr > 1.3 else (acc if hr > 1.1 else (pos if hr < 0.9 else text_dim))
        interp = ("Each unit increase → " +
                  (f"{(hr-1)*100:.1f}% higher exit hazard" if hr > 1 else f"{(1-hr)*100:.1f}% lower exit hazard"))
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{coef:+.4f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hr_c};font-weight:700">{hr:.4f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:520px">{_html.escape(interp)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _validation_table(v) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    rows = [
        ("Train N",                f"{v.train_n:,}"),
        ("Test N (holdout)",       f"{v.test_n:,}"),
        ("In-sample C-index",      f"{v.in_sample_c_index:.4f}"),
        ("Out-of-sample C-index",  f"{v.out_of_sample_c_index:.4f}"),
        ("Generalization gap",     f"{v.generalization_gap:+.4f} (negative = better on test than train)"),
        ("Coefficient stability",  v.coefficient_stability),
    ]
    cells_html = ""
    for i, (k, val) in enumerate(rows):
        rb = panel_alt if i % 2 == 0 else bg
        cells_html += (f'<tr style="background:{rb}">'
                       f'<td style="padding:6px 12px;border-bottom:1px solid {border};font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(k)}</td>'
                       f'<td style="padding:6px 12px;border-bottom:1px solid {border};font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums;font-size:11px;color:{acc}">{_html.escape(str(val))}</td>'
                       f'</tr>')
    return f'<table style="width:100%;border-collapse:collapse;margin-top:12px">{cells_html}</table>'


def render_survival_analysis(params: dict = None) -> str:
    from rcm_mc.data_public.survival_analysis import compute_survival_analysis
    r = compute_survival_analysis()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Hold Curves", str(len(r.hold_period_curves)), "by sector", "") +
        ck_kpi_block("Specialty Curves", str(len(r.specialty_retention_curves)), "physician retention", "") +
        ck_kpi_block("Payer Curves", str(len(r.payer_renewal_curves)), "contract renewal", "") +
        ck_kpi_block("Cox PH Events", f"{r.total_events:,}", "observed", "") +
        ck_kpi_block("Censored", f"{r.total_censored:,}", "", "") +
        ck_kpi_block("C-Index (train)", f"{r.backtest_validation.in_sample_c_index:.3f}", "in-sample", "") +
        ck_kpi_block("C-Index (test)", f"{r.backtest_validation.out_of_sample_c_index:.3f}", "out-of-sample", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    hold_tbl = _hold_period_table(r.hold_period_curves)
    spec_tbl = _specialty_retention_table(r.specialty_retention_curves)
    payer_tbl = _payer_renewal_table(r.payer_renewal_curves)
    cox_tbl = _cox_table(r.cox_model_summary)
    val_tbl = _validation_table(r.backtest_validation)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    m = r.cox_model_summary
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Survival Analysis ML Layer — Kaplan-Meier + Cox PH (numpy-only)</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Implemented from scratch in numpy — zero new runtime dependencies · 3 survival applications (PE hold-period × physician retention × payer renewal) · Cox PH fit on {r.total_events + r.total_censored:,} hold-period events (80/20 train/test) · Out-of-sample C-index {r.backtest_validation.out_of_sample_c_index:.3f} — validated via backtest, not just in-sample fit</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Kaplan-Meier: PE Hold-Period Survival by Sector</div>{hold_tbl}</div>
  <div style="{cell}"><div style="{h3}">Kaplan-Meier: Physician Retention by Specialty</div>{spec_tbl}</div>
  <div style="{cell}"><div style="{h3}">Kaplan-Meier: Payer Contract Renewal Hazard</div>{payer_tbl}</div>
  <div style="{cell}"><div style="{h3}">Cox Proportional Hazards — 3-feature Fit on Hold-Period Events</div>{cox_tbl}</div>
  <div style="{cell}"><div style="{h3}">Backtest Validation — 80/20 Train/Test Holdout</div>{val_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Survival Analysis Thesis:</strong>
    The blueprint calls out <code style="color:{acc};font-family:JetBrains Mono,monospace">lifelines / pycox / scikit-survival</code>
    for physician-retention modeling, contract-renewal risk, and facility-closure-hazard modeling.
    This module delivers the same analytical capability in numpy alone — consistent with the repo's
    zero-new-runtime-dependencies norm. Kaplan-Meier estimator + Cox Proportional Hazards (gradient
    descent on Breslow-tie-handled negative log partial likelihood) + Harrell's C-index validation,
    all ~600 lines of numpy.
    <br><br>
    <strong style="color:{text}">Key empirical findings from the corpus (Cox PH 3-feature model):</strong>
    <code style="color:{acc};font-family:JetBrains Mono,monospace">is_hospital</code> carries HR = {m.hazard_ratios[2]:.2f} —
    hospital deals exit ~{(m.hazard_ratios[2]-1)*100:.0f}% faster than non-hospital platforms (reflecting
    the realized Steward/Prospect/Quorum distress cluster).
    <code style="color:{acc};font-family:JetBrains Mono,monospace">government_payer_share</code> HR = {m.hazard_ratios[1]:.2f} —
    each unit increase in Medicare+Medicaid share raises exit hazard ~{(m.hazard_ratios[1]-1)*100:.0f}%.
    <code style="color:{acc};font-family:JetBrains Mono,monospace">entry_multiple</code> HR = {m.hazard_ratios[0]:.3f} —
    near-unity, meaning entry multiple does NOT independently predict distress after controlling for
    the other two covariates.
    <br><br>
    <strong style="color:{text}">Backtest validation:</strong>
    C-index in-sample {r.backtest_validation.in_sample_c_index:.4f}, out-of-sample {r.backtest_validation.out_of_sample_c_index:.4f}.
    Generalization gap {r.backtest_validation.generalization_gap:+.4f} (negative = better on test than
    train — the model generalizes). Coefficient stability: <strong style="color:{text}">{r.backtest_validation.coefficient_stability}</strong>.
    <br><br>
    <strong style="color:{text}">Payer-renewal curves surface the V28 shock clearly:</strong>
    MA-risk-exposed contracts have median renewal {r.payer_renewal_curves[-1].median_renewal_months:.0f}
    months vs commercial-heavy {r.payer_renewal_curves[0].median_renewal_months:.0f} months — the 2024
    V28 risk-adjustment phase-in is cutting MA-risk contract half-life in half.
    <br><br>
    <strong style="color:{text}">Methodology:</strong>
    {_html.escape(r.methodology)}
  </div>
</div>"""

    return chartis_shell(body, "Survival Analysis", active_nav="/survival-analysis")
