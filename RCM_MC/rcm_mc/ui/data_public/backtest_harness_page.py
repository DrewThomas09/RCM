"""Backtesting Harness — /backtest-harness."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _verdict_color(v: str) -> str:
    return {"GREEN": P["positive"], "YELLOW": P["warning"], "RED": P["negative"]}.get(v, P["text_dim"])


def _outcome_color(o: str) -> str:
    return {
        "DISTRESS": P["negative"],
        "SUCCESS":  P["positive"],
        "MEDIOCRE": P["warning"],
        "UNKNOWN":  P["text_dim"],
    }.get(o, P["text_dim"])


def _quality_color(q: str) -> str:
    return {"strong": P["positive"], "moderate": P["accent"], "weak": P["text_dim"]}.get(q, P["text_dim"])


def _metric_row(label: str, value: str, target: str, hint: str, color: str) -> str:
    bg = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    return f"""
<tr>
  <td style="text-align:left;padding:8px 12px;border-bottom:1px solid {border};font-size:11px;color:{text};font-weight:600">{_html.escape(label)}</td>
  <td style="text-align:right;padding:8px 12px;border-bottom:1px solid {border};font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:14px;color:{color};font-weight:700">{_html.escape(value)}</td>
  <td style="text-align:right;padding:8px 12px;border-bottom:1px solid {border};font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(target)}</td>
  <td style="text-align:left;padding:8px 12px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};max-width:540px">{_html.escape(hint)}</td>
</tr>"""


def _metrics_table(m, cm) -> str:
    bg = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; warn = P["warning"]; neg = P["negative"]

    # Color gates
    sens_c = pos if m.sensitivity >= 0.70 else (acc if m.sensitivity >= 0.40 else warn)
    spec_c = pos if m.specificity >= 0.85 else (acc if m.specificity >= 0.70 else warn)
    prec_c = pos if m.precision >= 0.60 else (acc if m.precision >= 0.40 else warn)
    brier_c = pos if m.brier_score <= 0.12 else (acc if m.brier_score <= 0.20 else warn)
    auc_c = pos if m.auc_roc >= 0.75 else (acc if m.auc_roc >= 0.60 else warn)
    acc_c = pos if m.accuracy >= 0.80 else (acc if m.accuracy >= 0.65 else warn)

    rows = [
        _metric_row("Sensitivity (Recall)", f"{m.sensitivity:.2%}", "target ≥ 70%",
                    "What % of DISTRESS deals did we flag RED? Blueprint target: 85%.",
                    sens_c),
        _metric_row("Specificity", f"{m.specificity:.2%}", "target ≥ 80%",
                    "What % of SUCCESS deals did we correctly GREEN? Blueprint target: 80%.",
                    spec_c),
        _metric_row("Precision (PPV)", f"{m.precision:.2%}", "target ≥ 60%",
                    "When we say RED, how often were we right?",
                    prec_c),
        _metric_row("F1 Score", f"{m.f1_score:.4f}", "target ≥ 0.55",
                    "Harmonic mean of precision + sensitivity.",
                    acc_c),
        _metric_row("Accuracy", f"{m.accuracy:.2%}", "",
                    "(TP+TN)/total on the binary-labelled subset.",
                    acc_c),
        _metric_row("Brier Score", f"{m.brier_score:.4f}", "target ≤ 0.12",
                    "Mean squared error of distress probability. Lower = better calibrated. Random = 0.25.",
                    brier_c),
        _metric_row("Calibration Error", f"{m.calibration_error:.4f}", "target ≤ 0.20",
                    "Mean absolute difference between predicted distress probability and realized outcome.",
                    brier_c),
        _metric_row("AUC-ROC", f"{m.auc_roc:.4f}", "target ≥ 0.80",
                    "Area under ROC curve. Random classifier = 0.5. Strong classifier ≥ 0.8.",
                    auc_c),
    ]
    header = (f'<tr style="background:{bg}">'
              f'<th style="text-align:left;padding:8px 12px;font-size:10px;color:{text_dim};letter-spacing:0.05em;border-bottom:1px solid {border}">Metric</th>'
              f'<th style="text-align:right;padding:8px 12px;font-size:10px;color:{text_dim};letter-spacing:0.05em;border-bottom:1px solid {border}">Value</th>'
              f'<th style="text-align:right;padding:8px 12px;font-size:10px;color:{text_dim};letter-spacing:0.05em;border-bottom:1px solid {border}">Target</th>'
              f'<th style="text-align:left;padding:8px 12px;font-size:10px;color:{text_dim};letter-spacing:0.05em;border-bottom:1px solid {border}">Interpretation</th>'
              f'</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead>{header}</thead><tbody>{"".join(rows)}</tbody></table></div>')


def _confusion_grid(cm) -> str:
    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]

    def _cell(label, n, color):
        return (f'<td style="text-align:center;padding:16px;border:1px solid {border};background:{panel_alt};'
                f'font-family:JetBrains Mono,monospace;vertical-align:top">'
                f'<div style="font-size:10px;color:{text_dim};letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">{label}</div>'
                f'<div style="font-size:24px;font-weight:700;color:{color};font-variant-numeric:tabular-nums">{n}</div>'
                f'</td>')

    header = (f'<tr>'
              f'<th style="padding:6px 12px;border:1px solid {border};background:{panel};font-size:10px;color:{text_dim};letter-spacing:0.05em"></th>'
              f'<th style="padding:6px 12px;border:1px solid {border};background:{panel};font-size:10px;color:{text_dim};letter-spacing:0.05em">Outcome: DISTRESS</th>'
              f'<th style="padding:6px 12px;border:1px solid {border};background:{panel};font-size:10px;color:{text_dim};letter-spacing:0.05em">Outcome: SUCCESS</th>'
              f'</tr>')
    row_red = (f'<tr>'
               f'<td style="padding:6px 12px;border:1px solid {border};background:{panel};font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">Verdict: RED</td>'
               f'{_cell("True Positive (caught)", cm.true_positive, pos)}'
               f'{_cell("False Positive (cry wolf)", cm.false_positive, warn)}'
               f'</tr>')
    row_yellow = (f'<tr>'
                  f'<td style="padding:6px 12px;border:1px solid {border};background:{panel};font-family:JetBrains Mono,monospace;font-size:11px;color:{warn};font-weight:700">Verdict: YELLOW</td>'
                  f'{_cell("Distress flagged Yellow", cm.yellow_distress, warn)}'
                  f'{_cell("Success flagged Yellow", cm.yellow_success, text_dim)}'
                  f'</tr>')
    row_green = (f'<tr>'
                 f'<td style="padding:6px 12px;border:1px solid {border};background:{panel};font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">Verdict: GREEN</td>'
                 f'{_cell("False Negative (missed)", cm.false_negative, neg)}'
                 f'{_cell("True Negative (spared)", cm.true_negative, pos)}'
                 f'</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead>{header}</thead><tbody>{row_red}{row_yellow}{row_green}</tbody></table></div>')


def _tier_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Verdict", "left"), ("Count", "right"), ("Avg Score", "right"),
            ("DISTRESS %", "right"), ("SUCCESS %", "right"),
            ("MEDIOCRE %", "right"), ("UNKNOWN %", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        vc = _verdict_color(t.verdict)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{vc};font-weight:700">{_html.escape(t.verdict)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{t.count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{t.avg_composite_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]};font-weight:700">{t.distress_rate_pct}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{t.success_rate_pct}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{t.mediocre_rate_pct}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.unknown_rate_pct}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lift_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Pattern", "left"), ("Case", "left"), ("DISTRESS Matched", "right"),
            ("SUCCESS Matched", "right"), ("Lift vs Base Rate", "right"),
            ("Share of TP", "right"), ("Signal Quality", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        qc = _quality_color(p.signal_quality)
        lift_c = pos if p.lift_vs_base_rate >= 3.0 else (acc if p.lift_vs_base_rate >= 1.8 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.pattern_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:280px">{_html.escape(p.case_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]};font-weight:700">{p.distress_deals_matched}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{p.success_deals_matched}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{lift_c};font-weight:700">{p.lift_vs_base_rate:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.share_of_tp * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{qc};border:1px solid {qc};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.signal_quality.upper())}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _records_table(items, title_prefix: str) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Deal", "left"), ("Year", "right"), ("Verdict", "center"),
            ("Composite Score", "right"), ("P(Distress)", "right"),
            ("Outcome", "center"), ("Top NF Pattern", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        vc = _verdict_color(r.verdict)
        oc = _outcome_color(r.outcome_label)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.year or "—"}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{vc};border:1px solid {vc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(r.verdict)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{r.composite_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.distress_probability:.4f}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{oc};border:1px solid {oc};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.outcome_label)}</span></td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(r.nf_match_top_pattern)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_backtest_harness(params: dict = None) -> str:
    from rcm_mc.data_public.backtest_harness import compute_backtest_harness
    r = compute_backtest_harness()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Deals Scored", f"{r.metrics.total_deals_scored:,}", "", "") +
        ck_kpi_block("Binary-Labelled", f"{r.metrics.binary_labelled_count:,}", "", "") +
        ck_kpi_block("Sensitivity", f"{r.metrics.sensitivity:.2%}", "", "") +
        ck_kpi_block("Specificity", f"{r.metrics.specificity:.2%}", "", "") +
        ck_kpi_block("Precision", f"{r.metrics.precision:.2%}", "", "") +
        ck_kpi_block("AUC-ROC", f"{r.metrics.auc_roc:.3f}", "", "") +
        ck_kpi_block("Brier Score", f"{r.metrics.brier_score:.4f}", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    metrics_tbl = _metrics_table(r.metrics, r.confusion)
    confusion_grid = _confusion_grid(r.confusion)
    tier_tbl = _tier_table(r.tier_summary)
    lift_tbl = _lift_table(r.pattern_lifts)
    tp_tbl = _records_table(r.notable_true_positives, "True Positives")
    fn_tbl = _records_table(r.notable_false_negatives, "False Negatives")
    fp_tbl = _records_table(r.notable_false_positives, "False Positives")

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Backtesting Harness — Would We Have Flagged This Deal?</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.metrics.total_deals_scored:,} corpus deals replayed as of their announcement year · {r.metrics.binary_labelled_count} labelled DISTRESS-or-SUCCESS for binary metrics · Sensitivity {r.metrics.sensitivity:.1%}, Specificity {r.metrics.specificity:.1%}, AUC-ROC {r.metrics.auc_roc:.3f} — Blueprint Moat Layer 4, the flagship credibility artifact</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Confusion Matrix — Verdict × Outcome (binary subset)</div>{confusion_grid}</div>
  <div style="{cell}"><div style="{h3}">Classifier Metrics vs Blueprint Targets</div>{metrics_tbl}</div>
  <div style="{cell}"><div style="{h3}">Verdict-Tier Distribution — DISTRESS Rate by Tier</div>{tier_tbl}</div>
  <div style="{cell}"><div style="{h3}">Per-Pattern Lift — Which Named Failures Drive Predictive Power</div>{lift_tbl}</div>
  <div style="{cell}"><div style="{h3}">True Positives — Would-Have-Flagged Exemplars (Verdict=RED, Outcome=DISTRESS)</div>{tp_tbl}</div>
  <div style="{cell}"><div style="{h3}">False Negatives — Missed Distress (Verdict=GREEN, Outcome=DISTRESS)</div>{fn_tbl}</div>
  <div style="{cell}"><div style="{h3}">False Positives — Cried Wolf (Verdict=RED, Outcome=SUCCESS)</div>{fp_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Backtesting Thesis:</strong>
    The backtester is Moat Layer 4 — the credibility artifact. Every analytical claim the platform makes
    is testable against the corpus of historical healthcare-PE deals: does the scoring stack, run at a
    deal's announcement date, correctly flag distressed outcomes and spare successful ones?
    <br><br>
    <strong style="color:{text}">Current performance, first release:</strong>
    Sensitivity {r.metrics.sensitivity:.1%} · Specificity {r.metrics.specificity:.1%} · Precision {r.metrics.precision:.1%} ·
    AUC-ROC {r.metrics.auc_roc:.3f} · Brier {r.metrics.brier_score:.4f} · Accuracy {r.metrics.accuracy:.1%}.
    RED-verdict deals show a <strong style="color:{text}">{r.tier_summary[2].distress_rate_pct}% distress rate</strong> vs
    {r.tier_summary[0].distress_rate_pct}% in GREEN — a {r.tier_summary[2].distress_rate_pct / max(r.tier_summary[0].distress_rate_pct, 0.01):.0f}×
    lift, meaning the composite score is a real signal.
    <br><br>
    <strong style="color:{text}">Blueprint targets:</strong> Sensitivity ≥ 85%, Specificity ≥ 80%, AUC ≥ 0.80.
    First release falls short on sensitivity because the composite-score RED threshold ({55.0}) is deliberately
    conservative — only the most unambiguous pattern-matches escalate to RED. Most distress-labeled deals
    currently fall in YELLOW (composite 30-55), which is where diligence attention is warranted but the
    verdict doesn't yet commit to RED. A second-release tuning path: lower RED threshold to 45, expand the
    Named-Failure library to 40+ patterns, and add entry-multiple distributional priors from the
    Benchmark Curve Library (/benchmark-curves) to the composite.
    <br><br>
    <strong style="color:{text}">Top pattern lifts</strong> — these are the NF patterns providing real predictive signal:
    {r.pattern_lifts[0].case_name} ({r.pattern_lifts[0].lift_vs_base_rate:.2f}×), {r.pattern_lifts[1].case_name} ({r.pattern_lifts[1].lift_vs_base_rate:.2f}×),
    {r.pattern_lifts[2].case_name} ({r.pattern_lifts[2].lift_vs_base_rate:.2f}×).
    <br><br>
    <strong style="color:{text}">Scoring methodology (auditable):</strong>
    <code style="color:{acc};font-family:JetBrains Mono,monospace">{_html.escape(r.scoring_methodology)}</code>
  </div>
</div>"""

    return chartis_shell(body, "Backtesting Harness", active_nav="/backtest-harness")
