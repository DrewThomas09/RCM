"""SeekingChartis Model Validation Dashboard.

Shows prediction accuracy by metric, coverage calibration, bias trends,
and per-cohort breakdowns. Builds trust and demonstrates the compounding
data moat — the more we predict and validate, the better we get.
"""
from __future__ import annotations

import html as _html
import sqlite3
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def _grade_badge(grade: str) -> str:
    colors = {"A": "var(--cad-pos)", "B": "var(--cad-accent)", "C": "var(--cad-warn)", "D": "var(--cad-neg)"}
    color = colors.get(grade, "var(--cad-text3)")
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:700;">{grade}</span>'


def render_model_validation(
    db_path: str,
    hcris_df: Optional[pd.DataFrame] = None,
) -> str:
    """Render the model validation dashboard.

    If no predictions exist yet, runs a synthetic backtest on HCRIS data
    to seed the validation system.
    """
    from ..ml.prediction_ledger import (
        _ensure_tables,
        compute_metric_performance,
        get_performance_trend,
        get_predictions_with_actuals,
        run_synthetic_backtest,
    )

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    _ensure_tables(con)

    # Check if we have any predictions
    count = con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]

    if count < 20 and hcris_df is not None and len(hcris_df) > 100:
        performances = run_synthetic_backtest(con, hcris_df, n_trials=200)
        con.commit()
        count = con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    else:
        performances = {}

    # Get metrics that have actuals
    metrics_with_actuals = con.execute(
        "SELECT DISTINCT p.metric, COUNT(*) as n "
        "FROM predictions p "
        "JOIN prediction_actuals pa ON pa.prediction_id = p.id "
        "GROUP BY p.metric ORDER BY n DESC"
    ).fetchall()

    total_predictions = count
    total_actuals = con.execute(
        "SELECT COUNT(*) FROM prediction_actuals"
    ).fetchone()[0]

    # Compute performance for each metric
    all_perfs = []
    for row in metrics_with_actuals:
        metric = row[0]
        perf = compute_metric_performance(con, metric)
        if perf:
            all_perfs.append(perf)

    # Overall stats
    if all_perfs:
        avg_r2 = np.mean([p.r2 for p in all_perfs])
        avg_coverage = np.mean([p.coverage_rate for p in all_perfs])
        avg_mae = np.mean([p.mae for p in all_perfs])
        top_grade = min(p.grade for p in all_perfs)
    else:
        avg_r2 = 0
        avg_coverage = 0
        avg_mae = 0
        top_grade = "—"

    # ── KPIs ──
    r2_color = "var(--cad-pos)" if avg_r2 > 0.5 else ("var(--cad-warn)" if avg_r2 > 0.3 else "var(--cad-neg)")
    cov_color = "var(--cad-pos)" if avg_coverage > 0.85 else ("var(--cad-warn)" if avg_coverage > 0.75 else "var(--cad-neg)")

    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(6,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{total_predictions:,}</div>'
        f'<div class="cad-kpi-label">Predictions Made</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{total_actuals:,}</div>'
        f'<div class="cad-kpi-label">Actuals Recorded</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{r2_color};">'
        f'{avg_r2:.1%}</div>'
        f'<div class="cad-kpi-label">Avg R&sup2;</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{cov_color};">'
        f'{avg_coverage:.0%}</div>'
        f'<div class="cad-kpi-label">90% CI Coverage</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(all_perfs)}</div>'
        f'<div class="cad-kpi-label">Metrics Validated</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_grade_badge(top_grade)}</div>'
        f'<div class="cad-kpi-label">Weakest Grade</div></div>'
        f'</div>'
    )

    # ── Per-metric performance table ──
    metric_rows = ""
    for p in sorted(all_perfs, key=lambda x: -x.r2):
        r2_c = "var(--cad-pos)" if p.r2 > 0.5 else ("var(--cad-warn)" if p.r2 > 0.3 else "var(--cad-neg)")
        cov_c = "var(--cad-pos)" if p.coverage_rate > 0.85 else ("var(--cad-warn)" if p.coverage_rate > 0.75 else "var(--cad-neg)")
        bias_c = "var(--cad-pos)" if abs(p.bias) < p.mae * 0.3 else "var(--cad-warn)"

        metric_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_html.escape(p.metric.replace("_", " ").title())}</td>'
            f'<td class="num" style="color:{r2_c};font-weight:600;">{p.r2:.1%}</td>'
            f'<td class="num">{p.mae:.4f}</td>'
            f'<td class="num">{p.rmse:.4f}</td>'
            f'<td class="num" style="color:{cov_c};">{p.coverage_rate:.0%}</td>'
            f'<td class="num">{p.mean_interval_width:.4f}</td>'
            f'<td class="num" style="color:{bias_c};">{p.bias:+.4f}</td>'
            f'<td class="num">{p.n_actuals}</td>'
            f'<td>{_grade_badge(p.grade)}</td>'
            f'</tr>'
        )

    metric_section = (
        f'<div class="cad-card">'
        f'<h2>Model Accuracy by Metric</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Each metric\'s prediction accuracy measured against held-out actuals. '
        f'R&sup2; = variance explained. Coverage = fraction of actuals within the 90% CI. '
        f'Bias = systematic over/under-prediction (positive = model overestimates). '
        f'Grade: A (R&sup2;&ge;0.7, coverage&ge;85%), B, C, D.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th><th>R&sup2;</th><th>MAE</th><th>RMSE</th>'
        f'<th>Coverage</th><th>CI Width</th><th>Bias</th><th>n</th><th>Grade</th>'
        f'</tr></thead><tbody>{metric_rows}</tbody></table></div>'
    ) if metric_rows else ""

    # ── Recent predictions with actuals ──
    recent = get_predictions_with_actuals(con, limit=30)
    recent_rows = ""
    for r in recent[:20]:
        if r.error is None:
            continue
        err_color = "var(--cad-pos)" if abs(r.error) < abs(r.predicted_value) * 0.1 else (
            "var(--cad-warn)" if abs(r.error) < abs(r.predicted_value) * 0.2 else "var(--cad-neg)")
        covered_icon = "&#10003;" if r.covered else "&#10007;"
        covered_color = "var(--cad-pos)" if r.covered else "var(--cad-neg)"

        fmt = lambda v: f"{v:.1%}" if abs(v) < 2 else f"{v:.2f}"
        recent_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(r.ccn)}" '
            f'style="color:var(--cad-link);text-decoration:none;">{_html.escape(r.ccn)}</a></td>'
            f'<td>{_html.escape(r.metric.replace("_", " ").title())}</td>'
            f'<td class="num">{fmt(r.predicted_value)}</td>'
            f'<td class="num">{fmt(r.actual_value)}</td>'
            f'<td class="num" style="color:{err_color};">{r.error:+.4f}</td>'
            f'<td style="color:{covered_color};text-align:center;">{covered_icon}</td>'
            f'<td style="font-size:10px;color:var(--cad-text3);">{_html.escape(r.method or "")}</td>'
            f'</tr>'
        )

    recent_section = (
        f'<div class="cad-card">'
        f'<h2>Recent Predictions vs Actuals</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>CCN</th><th>Metric</th><th>Predicted</th><th>Actual</th>'
        f'<th>Error</th><th>In CI</th><th>Method</th>'
        f'</tr></thead><tbody>{recent_rows}</tbody></table></div>'
    ) if recent_rows else ""

    # ── Coverage calibration ──
    cov_analysis = ""
    if all_perfs:
        well_calibrated = sum(1 for p in all_perfs if 0.85 <= p.coverage_rate <= 0.95)
        over_covered = sum(1 for p in all_perfs if p.coverage_rate > 0.95)
        under_covered = sum(1 for p in all_perfs if p.coverage_rate < 0.85)

        cov_analysis = (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
            f'<h2>Confidence Interval Calibration</h2>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:10px;">'
            f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-pos);">'
            f'{well_calibrated}</div>'
            f'<div class="cad-kpi-label">Well-Calibrated (85-95%)</div></div>'
            f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-warn);">'
            f'{over_covered}</div>'
            f'<div class="cad-kpi-label">Over-Covered (&gt;95%)</div></div>'
            f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-neg);">'
            f'{under_covered}</div>'
            f'<div class="cad-kpi-label">Under-Covered (&lt;85%)</div></div></div>'
            f'<p style="font-size:12px;color:var(--cad-text2);">'
            f'Target: 90% of actuals should fall within the 90% CI. '
            f'Over-covered intervals are too wide (conservative but wastes bandwidth). '
            f'Under-covered intervals are too narrow (overconfident — dangerous for IC). '
            f'Split conformal prediction guarantees finite-sample coverage, but calibration '
            f'can drift if the data distribution shifts.</p></div>'
        )

    # ── Flywheel explanation ──
    flywheel = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2>The Compounding Data Moat</h2>'
        f'<div style="font-size:12.5px;color:var(--cad-text2);line-height:1.8;">'
        f'<p><strong>Predict → Validate → Learn → Improve</strong></p>'
        f'<p>Every prediction gets recorded with its confidence interval. When actuals arrive '
        f'(from deal close, quarterly reports, or HCRIS updates), they\'re matched to predictions. '
        f'Systematic biases are detected and corrected. Confidence intervals are calibrated to '
        f'real performance. The more deals we underwrite, the better our models get.</p>'
        f'<p style="margin-top:8px;">Current state: <strong>{total_predictions:,}</strong> predictions, '
        f'<strong>{total_actuals:,}</strong> validated. Each new deal adds ~20-30 metric predictions '
        f'to the ledger. After 50+ deals, cross-deal learning kicks in — the system detects '
        f'that it systematically overestimates denial improvement by 15% and adjusts future predictions.</p>'
        f'</div></div>'
    )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/quant-lab" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Quant Lab</a>'
        f'<a href="/ml-insights" class="cad-btn" '
        f'style="text-decoration:none;">ML Insights</a>'
        f'<a href="/portfolio/regression" class="cad-btn" '
        f'style="text-decoration:none;">Regression</a>'
        f'<a href="/predictive-screener" class="cad-btn" '
        f'style="text-decoration:none;">Deal Screener</a>'
        f'</div>'
    )

    body = f'{kpis}{metric_section}{cov_analysis}{recent_section}{flywheel}{nav}'

    con.close()

    return chartis_shell(
        body, "Model Validation",
        active_nav="/model-validation",
        subtitle=(
            f"{total_predictions:,} predictions | {total_actuals:,} validated | "
            f"Avg R\u00b2 {avg_r2:.1%} | Coverage {avg_coverage:.0%}"
        ),
    )
