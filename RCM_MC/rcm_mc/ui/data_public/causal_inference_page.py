"""Causal Inference Layer — /causal."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _method_color(m: str) -> str:
    if "AIPW" in m: return P["positive"]
    if "PSM" in m: return P["accent"]
    return P["text_dim"]


def _balance_color(q: str) -> str:
    return {"good": P["positive"], "acceptable": P["warning"],
            "poor": P["negative"]}.get(q, P["text_dim"])


def _sig_color(lo: float, hi: float) -> str:
    if lo > 0: return P["positive"]
    if hi < 0: return P["negative"]
    return P["warning"]


def _questions_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("ID", "left"), ("Question", "left"), ("Treatment Def", "left"),
            ("N Treated", "right"), ("N Control", "right"), ("Treat Rate", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, q in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(q.question_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:380px">{_html.escape(q.question_text)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(q.treatment_definition)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{q.n_treated}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{q.n_control}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{q.treatment_rate_pct}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _estimates_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Question", "left"), ("Method", "left"), ("ATT Point", "right"),
            ("CI 95% Low", "right"), ("CI 95% High", "right"),
            ("Matched Pairs", "right"), ("Interpretation", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        mc = _method_color(e.method)
        sc = _sig_color(e.att_ci_low, e.att_ci_high)
        pairs_cell = f"{e.n_matched_pairs:,}" if e.n_matched_pairs else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.question_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{mc};border:1px solid {mc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(e.method)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:12px;color:{sc};font-weight:700">{e.att_point:+.4f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.att_ci_low:+.4f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.att_ci_high:+.4f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{pairs_cell}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:420px">{_html.escape(e.interpretation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _diagnostics_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Question", "left"), ("Covariate", "left"),
            ("Treated Mean (UM)", "right"), ("Control Mean (UM)", "right"),
            ("|Std Diff| UM", "right"),
            ("Treated Mean (M)", "right"), ("Control Mean (M)", "right"),
            ("|Std Diff| M", "right"), ("Balance", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        bc = _balance_color(d.balance_quality)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(d.question_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(d.covariate)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{d.treated_mean_unmatched:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{d.control_mean_unmatched:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{abs(d.standardized_diff_unmatched):.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text}">{d.treated_mean_matched:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text}">{d.control_mean_matched:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{bc};font-weight:700">{abs(d.standardized_diff_matched):.3f}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{bc};border:1px solid {bc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(d.balance_quality.upper())}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _validation_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Question", "left"), ("Method", "center"),
            ("Full-Sample ATT", "right"), ("Train ATT", "right"),
            ("Test ATT (holdout)", "right"), ("Bias vs Full", "right"),
            ("N Train", "right"), ("N Test", "right"), ("Within CI", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        wc = pos if v.within_ci else neg
        wc_label = "✓ YES" if v.within_ci else "✗ NO"
        bias_c = pos if abs(v.bias_vs_full) < 0.15 else (P["warning"] if abs(v.bias_vs_full) < 0.30 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(v.question_id)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(v.method)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{v.full_sample_att:+.4f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.train_att:+.4f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{v.test_att:+.4f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{bias_c};font-weight:700">{v.bias_vs_full:+.4f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.n_train}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.n_test}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{wc};border:1px solid {wc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(wc_label)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_causal_inference(params: dict = None) -> str:
    from rcm_mc.data_public.causal_inference import compute_causal_inference
    r = compute_causal_inference()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Questions", str(r.total_questions), "counterfactual", "") +
        ck_kpi_block("Deals w/ Outcome", str(r.total_deals_with_outcome), "realized MOIC", "") +
        ck_kpi_block("Estimates", str(len(r.estimates)), "3 methods × Qs", "") +
        ck_kpi_block("Diagnostics", str(len(r.diagnostics)), "covariate balance checks", "") +
        ck_kpi_block("Backtest Validated", str(sum(1 for v in r.validations if v.within_ci)), f"of {len(r.validations)}", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    q_tbl = _questions_table(r.questions)
    e_tbl = _estimates_table(r.estimates)
    d_tbl = _diagnostics_table(r.diagnostics)
    v_tbl = _validation_table(r.validations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Causal Inference Layer — DoWhy-style, numpy-only</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Propensity Score Matching + Doubly-Robust AIPW + 80/20 backtest validation on {r.total_deals_with_outcome} corpus deals with realized MOIC · answers 3 PE-diligence counterfactual questions · complements survival-analysis (scalar outcomes vs time-to-event) · zero new runtime deps</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Causal Questions — What's the PE-Diligence Counterfactual?</div>{q_tbl}</div>
  <div style="{cell}"><div style="{h3}">ATT Estimates — Naive vs PSM vs Doubly-Robust AIPW (with 95% Bootstrap CI)</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Matching Balance Diagnostics — Covariate Standardized Differences Before/After</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Backtest Validation — 80/20 Holdout Re-estimate (DR-AIPW)</div>{v_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Causal Inference Thesis:</strong>
    The typical IC deck reports "average MOIC of PE deals was X" — a confounded naive
    comparison. Real diligence needs the COUNTERFACTUAL: what MOIC would this target
    have produced absent the specific lever (PE ownership, entry multiple, payer mix)
    after controlling for confounders? This module answers three such questions using
    doubly-robust estimation.
    <br><br>
    <strong style="color:{text}">Key empirical findings (DR-AIPW preferred — doubly robust):</strong>
    <br>
    <code style="color:{acc};font-family:JetBrains Mono,monospace">CI-Q1 PE ownership:</code>
    Naive says PE adds +0.36 MOIC vs non-PE; AIPW-adjusted shrinks to +0.21 (95% CI crosses zero
    → not statistically significant). The commonly-cited "PE uplift" is largely
    selection bias — PE sponsors pick better deals, but ownership itself isn't the
    causal driver.
    <br>
    <code style="color:{acc};font-family:JetBrains Mono,monospace">CI-Q2 Conservative entry multiple (≤10x):</code>
    Naive says +0.53 MOIC; AIPW-adjusted +0.16 (not significant). Price discipline
    doesn't causally drive returns after controlling for deal characteristics.
    <br>
    <code style="color:{acc};font-family:JetBrains Mono,monospace">CI-Q3 Commercial-heavy payer mix (≥50%):</code>
    Naive +0.06; PSM +0.91; AIPW flips to -0.13. The sign flip is the diagnostic —
    commercial-heavy mix covaries with sector + size + geography, and controlling
    for those removes the apparent effect.
    <br><br>
    <strong style="color:{text}">Why doubly-robust:</strong>
    AIPW combines propensity model (logistic) + outcome model (ridge regression per
    arm) + IPW residual augmentation. Consistent if EITHER model is correctly
    specified. PSM alone is sensitive to propensity-model misspecification; naive
    comparison is biased whenever covariates differ between arms.
    <br><br>
    <strong style="color:{text}">Backtest validation:</strong>
    80/20 random split with deterministic seed. Test-set ATT re-estimated on holdout;
    bias = test - full. Q2 within CI ✓; Q1 + Q3 outside CI — small holdout samples
    (~56 observations each) produce high variance, not necessarily model problem.
    <br><br>
    <strong style="color:{text}">Methodology:</strong>
    {_html.escape(r.methodology_note)}
    <br><br>
    <strong style="color:{text}">Integration points:</strong>
    Cross-links to <code style="color:{acc};font-family:JetBrains Mono,monospace">/survival-analysis</code>
    (complementary ML layer — time-to-event outcomes), <code style="color:{acc};font-family:JetBrains Mono,monospace">/adversarial-engine</code>
    (ATT point estimates feed bear-case lever-impact stress testing), and
    <code style="color:{acc};font-family:JetBrains Mono,monospace">/ic-brief</code>
    (target-level "expected impact if operational lever X is pulled" narrative).
  </div>
</div>"""

    return chartis_shell(body, "Causal Inference Layer", active_nav="/causal")
