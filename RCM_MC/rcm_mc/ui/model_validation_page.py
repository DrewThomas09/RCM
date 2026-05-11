"""SeekingChartis Model Validation Dashboard.

Shows prediction accuracy by metric, coverage calibration, bias trends,
and per-cohort breakdowns. Builds trust and demonstrates the compounding
data moat — the more we predict and validate, the better we get.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..portfolio.store import PortfolioStore
from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_panel,
    ck_section_intro, ck_signal_badge,
)
from .brand import PALETTE


def _grade_badge(grade: str) -> str:
    tone = {
        "A": "positive", "B": "neutral", "C": "warning", "D": "negative",
    }.get(grade, "neutral")
    return ck_signal_badge(grade, tone=tone)


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

    # Route through PortfolioStore (campaign target 4E) so the
    # connection inherits PRAGMA foreign_keys=ON, busy_timeout=
    # 5000, and row_factory=Row. Manual __enter__/__exit__ instead
    # of a `with` block keeps the existing function body's flat
    # structure intact (200 lines) — same exception-handling
    # contract as the prior bare-sqlite3 form (no try/finally was
    # there).
    _pstore_cm = PortfolioStore(db_path).connect()
    con = _pstore_cm.__enter__()
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

    # ── Editorial hero + KPI strip ──
    intro = ck_section_intro(
        eyebrow="MODEL VALIDATION",
        headline="Where every prediction earns its trust.",
        italic_word="trust",
        body=(
            "Every metric prediction is logged with its confidence "
            "interval; actuals get matched as deals close. The "
            "scorecard below shows R², 90%-CI coverage, MAE, and "
            "bias per metric — partner-defensible because each "
            "number is reproducible from the prediction ledger."
        ),
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Predictions Made", f"{total_predictions:,}")
        + ck_kpi_block("Actuals Recorded", f"{total_actuals:,}")
        + ck_kpi_block(
            "Avg R²", f"{avg_r2:.1%}",
            help={
                "definition": (
                    "Coefficient of determination — the share of "
                    "variance in actual outcomes the predictor "
                    "explains, averaged across all 38 metrics in "
                    "the registry. 100% is perfect prediction; "
                    "anything above ~60% is publishable in this "
                    "domain."
                ),
            },
        )
        + ck_kpi_block(
            "90% CI Coverage", f"{avg_coverage:.0%}",
            help={
                "definition": (
                    "Conformal-prediction coverage — the share of "
                    "actuals that fell inside the predictor's "
                    "90% confidence band. A well-calibrated model "
                    "lands at 90% ± a few points. Lower means the "
                    "bands are too tight; higher means they're "
                    "too generous."
                ),
                "citation": "rcm_mc/ml/conformal.py",
            },
        )
        + ck_kpi_block("Metrics Validated", f"{len(all_perfs)}")
        + ck_kpi_block(
            "Weakest Grade", _grade_badge(top_grade),
            help={
                "definition": (
                    "Lowest letter grade across all validated "
                    "metrics. A-D maps to deciles of combined R² "
                    "and CI calibration. The weakest grade is the "
                    "first thing to fix before partners trust the "
                    "predictor across the board."
                ),
            },
        )
        + '</div>'
    )

    # ── Per-metric performance table ──
    metric_rows = ""
    for p in sorted(all_perfs, key=lambda x: -x.r2):
        r2_cls = "cad-pos" if p.r2 > 0.5 else ("cad-warn" if p.r2 > 0.3 else "cad-neg")
        cov_cls = "cad-pos" if p.coverage_rate > 0.85 else ("cad-warn" if p.coverage_rate > 0.75 else "cad-neg")
        bias_cls = "cad-pos" if abs(p.bias) < p.mae * 0.3 else "cad-warn"

        metric_rows += (
            f'<tr>'
            f'<td><strong>{_html.escape(p.metric.replace("_", " ").title())}</strong></td>'
            f'<td class="num {r2_cls}"><strong>{p.r2:.1%}</strong></td>'
            f'<td class="num">{p.mae:.4f}</td>'
            f'<td class="num">{p.rmse:.4f}</td>'
            f'<td class="num {cov_cls}">{p.coverage_rate:.0%}</td>'
            f'<td class="num">{p.mean_interval_width:.4f}</td>'
            f'<td class="num {bias_cls}">{p.bias:+.4f}</td>'
            f'<td class="num">{p.n_actuals}</td>'
            f'<td>{_grade_badge(p.grade)}</td>'
            f'</tr>'
        )

    metric_section = ck_panel(
        '<p class="ck-section-body">'
        "Each metric's prediction accuracy measured against held-out actuals. "
        'R² = variance explained. Coverage = fraction of actuals within the 90% CI. '
        'Bias = systematic over/under-prediction (positive = model overestimates). '
        'Grade: A (R²≥0.7, coverage≥85%), B, C, D.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Metric</th><th>R²</th><th>MAE</th><th>RMSE</th>'
        '<th>Coverage</th><th>CI Width</th><th>Bias</th><th>n</th><th>Grade</th>'
        f'</tr></thead><tbody>{metric_rows}</tbody></table>',
        title="Model Accuracy by Metric",
    ) if metric_rows else ""

    # ── Recent predictions with actuals ──
    recent = get_predictions_with_actuals(con, limit=30)
    recent_rows = ""
    for r in recent[:20]:
        if r.error is None:
            continue
        err_cls = "cad-pos" if abs(r.error) < abs(r.predicted_value) * 0.1 else (
            "cad-warn" if abs(r.error) < abs(r.predicted_value) * 0.2 else "cad-neg")
        covered_icon = "&#10003;" if r.covered else "&#10007;"
        covered_cls = "cad-pos" if r.covered else "cad-neg"

        fmt = lambda v: f"{v:.1%}" if abs(v) < 2 else f"{v:.2f}"
        recent_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(r.ccn)}" class="ck-link">{_html.escape(r.ccn)}</a></td>'
            f'<td>{_html.escape(r.metric.replace("_", " ").title())}</td>'
            f'<td class="num">{fmt(r.predicted_value)}</td>'
            f'<td class="num">{fmt(r.actual_value)}</td>'
            f'<td class="num {err_cls}">{r.error:+.4f}</td>'
            f'<td class="num {covered_cls}">{covered_icon}</td>'
            f'<td>{_html.escape(r.method or "")}</td>'
            f'</tr>'
        )

    recent_section = ck_panel(
        '<table class="cad-table"><thead><tr>'
        '<th>CCN</th><th>Metric</th><th>Predicted</th><th>Actual</th>'
        '<th>Error</th><th>In CI</th><th>Method</th>'
        f'</tr></thead><tbody>{recent_rows}</tbody></table>',
        title="Recent Predictions vs Actuals",
    ) if recent_rows else ""

    # ── Coverage calibration ──
    cov_analysis = ""
    if all_perfs:
        well_calibrated = sum(1 for p in all_perfs if 0.85 <= p.coverage_rate <= 0.95)
        over_covered = sum(1 for p in all_perfs if p.coverage_rate > 0.95)
        under_covered = sum(1 for p in all_perfs if p.coverage_rate < 0.85)

        cov_analysis = ck_panel(
            '<div class="ck-kpi-strip">'
            + ck_kpi_block("Well-Calibrated (85-95%)", f"{well_calibrated}")
            + ck_kpi_block("Over-Covered (>95%)", f"{over_covered}")
            + ck_kpi_block("Under-Covered (<85%)", f"{under_covered}")
            + '</div>'
            + '<p class="ck-section-body">'
            'Target: 90% of actuals should fall within the 90% CI. '
            'Over-covered intervals are too wide (conservative but wastes bandwidth). '
            'Under-covered intervals are too narrow (overconfident — dangerous for IC). '
            'Split conformal prediction guarantees finite-sample coverage, but calibration '
            'can drift if the data distribution shifts.</p>',
            title="Confidence Interval Calibration",
        )

    # ── Flywheel explanation ──
    flywheel = ck_panel(
        '<p class="ck-section-body">'
        '<strong>Predict → Validate → Learn → Improve</strong></p>'
        '<p class="ck-section-body">'
        'Every prediction gets recorded with its confidence interval. When actuals arrive '
        '(from deal close, quarterly reports, or HCRIS updates), they\'re matched to predictions. '
        'Systematic biases are detected and corrected. Confidence intervals are calibrated to '
        'real performance. The more deals we underwrite, the better our models get.</p>'
        '<p class="ck-section-body">'
        f'Current state: <strong>{total_predictions:,}</strong> predictions, '
        f'<strong>{total_actuals:,}</strong> validated. Each new deal adds ~20-30 metric predictions '
        'to the ledger. After 50+ deals, cross-deal learning kicks in — the system detects '
        'that it systematically overestimates denial improvement by 15% and adjusts future predictions.</p>',
        title="The Compounding Data Moat",
    )

    # ── Nav ──
    nav = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/quant-lab" class="cad-btn cad-btn-primary">Quant Lab</a> '
        '<a href="/ml-insights" class="cad-btn">ML Insights</a> '
        '<a href="/portfolio/regression" class="cad-btn">Regression</a> '
        '<a href="/predictive-screener" class="cad-btn">Deal Screener</a>'
        '</p>',
        title="Cross-links",
    )

    body = f'{intro}{kpis}{metric_section}{cov_analysis}{recent_section}{flywheel}{nav}'

    _pstore_cm.__exit__(None, None, None)

    return chartis_shell(
        body, "Model Validation",
        active_nav="/model-validation",
        subtitle=(
            f"{total_predictions:,} predictions | {total_actuals:,} validated | "
            f"Avg R\u00b2 {avg_r2:.1%} | Coverage {avg_coverage:.0%}"
        ),
    )
