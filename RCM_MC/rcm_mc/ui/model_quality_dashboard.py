"""Model quality dashboard — `/models/quality`.

Renders a panel of trained-model backtest results: R² + MAE + MAPE
+ grade + CI calibration (observed vs nominal coverage).

Why this page is exempt from the DealAnalysisPacket invariant:
    Model quality is a property of trained ML predictors across the
    codebase, not of any specific deal. Same shape as
    /models/importance — model-wide metadata exempt from the per-
    deal packet invariant. Source of truth is the
    ModelBacktestResult dict the caller assembles from rcm_mc/ml/
    backtest helpers.

Caller passes in the panel of ModelBacktestResult objects; this
module is rendering-only so it doesn't take a hard dependency on
the specific predictors.

Public API::

    render_model_quality_dashboard(results) -> str
"""
from __future__ import annotations

import html as _html
import math
from typing import Any, Dict, List

from ..ml.model_quality import ModelBacktestResult
from ._chartis_kit import chartis_shell
from ._ui_kit import fmt_num
from .colors import STATUS


# Grade colors anchor to the semantic palette: A/B = good (green/info),
# C = watch (amber), D/F = bad (red). These are inline because the
# grade itself IS the data — decoupling from semantic palette would
# lose signal (same rationale as the SVG chart in feature_importance_viz).
_GRADE_COLORS = {
    "A": (STATUS["positive_bg"], STATUS["positive_fg"]),
    "B": (STATUS["info_bg"], STATUS["info_fg"]),
    "C": (STATUS["watch_bg"], STATUS["watch_fg"]),
    "D": ("#7c2d12", "#fed7aa"),
    "F": (STATUS["negative_bg"], STATUS["negative_fg"]),
}

_CALIB_COLORS = {
    "well_calibrated": (STATUS["positive_bg"], STATUS["positive_fg"]),
    "overconfident":   (STATUS["negative_bg"], STATUS["negative_fg"]),
    "underconfident":  (STATUS["watch_bg"], STATUS["watch_fg"]),
    "no_data":         (STATUS["neutral_bg"], STATUS["neutral_fg"]),
    "failed":          (STATUS["negative_bg"], STATUS["negative_fg"]),
}


def _grade_badge(grade: str) -> str:
    bg, fg = _GRADE_COLORS.get(grade, ("#374151", "#9ca3af"))
    return (
        f'<span style="display:inline-block;padding:.15rem .65rem;'
        f'border-radius:4px;background:{bg};color:{fg};'
        f'font-size:.85rem;font-weight:600;">{_html.escape(grade)}</span>'
    )


def _calib_badge(label: str, observed: float, nominal: float) -> str:
    bg, fg = _CALIB_COLORS.get(label, ("#374151", "#9ca3af"))
    text = f"{label.replace('_', ' ')} · {observed:.0%}/{nominal:.0%}"
    return (
        f'<span class="num" style="display:inline-block;'
        f'padding:.15rem .55rem;border-radius:4px;'
        f'background:{bg};color:{fg};font-size:.7rem;">'
        f'{_html.escape(text)}</span>'
    )


def _kpi_card(label: str, value_html: str, sub: str = "") -> str:
    """Editorial KPI card — paper background, border, eyebrow label.

    Mirrors the pattern in data_catalog_page._kpi_card so future
    consolidation into a shared kit helper is straightforward (3
    near-identical implementations is the threshold to extract).
    """
    sub_html = (
        f'<div class="micro" style="margin-top:.35rem;color:var(--muted,#9ca3af);">'
        f'{_html.escape(sub)}</div>' if sub else ""
    )
    return (
        '<div style="border:1px solid var(--border,#374151);'
        'background:var(--paper,#1f2937);border-radius:8px;'
        'padding:.9rem 1.1rem;flex:1;min-width:170px;">'
        f'<div class="micro">{_html.escape(label)}</div>'
        f'<div style="font-size:1.4rem;font-weight:600;margin-top:.4rem;">'
        f'{value_html}</div>{sub_html}</div>'
    )


def _row(r: ModelBacktestResult) -> str:
    cv_r2 = (f'<span class="num mono">{r.cv_r2:.3f}</span>'
             if not math.isnan(r.cv_r2)
             else '<span class="num">—</span>')
    cv_mae = (f'<span class="num mono">{r.cv_mae:,.3f}</span>'
              if not math.isnan(r.cv_mae)
              else '<span class="num">—</span>')
    if r.cv_mape is not None and not math.isnan(r.cv_mape):
        mape = f'<span class="num">{r.cv_mape:.1%}</span>'
    else:
        mape = '<span class="num">—</span>'

    notes_html = ""
    if r.notes:
        notes_html = (
            '<div style="margin-top:.4rem;">'
            + "".join(
                f'<div style="font-size:.7rem;color:var(--muted,#9ca3af);'
                f'margin-top:.1rem;">{_html.escape(n)}</div>'
                for n in r.notes
            )
            + '</div>'
        )

    return (
        '<tr>'
        '<td style="padding:.8rem 1rem;">'
        f'<div style="font-weight:500;">{_html.escape(r.model_name)}</div>'
        '<div class="micro" style="margin-top:.15rem;font-weight:400;'
        'letter-spacing:.04em;text-transform:none;">'
        f'target: {_html.escape(r.target_metric)} · '
        f'{r.feature_count} features</div>'
        f'{notes_html}'
        '</td>'
        f'<td style="padding:.8rem 1rem;text-align:center;">{_grade_badge(r.grade)}</td>'
        f'<td style="padding:.8rem 1rem;text-align:right;">{cv_r2}</td>'
        f'<td style="padding:.8rem 1rem;text-align:right;">{cv_mae}</td>'
        f'<td style="padding:.8rem 1rem;text-align:right;">{mape}</td>'
        f'<td style="padding:.8rem 1rem;text-align:center;">'
        f'{_calib_badge(r.calibration.quality_label, r.calibration.observed_coverage, r.calibration.nominal_coverage)}'
        f'</td>'
        f'<td style="padding:.8rem 1rem;text-align:right;">'
        f'<span class="num mono">{r.calibration.calibration_factor:.2f}</span></td>'
        f'<td style="padding:.8rem 1rem;text-align:right;color:var(--muted,#9ca3af);">'
        f'{fmt_num(r.n_train)} / {fmt_num(r.n_holdout)}</td>'
        '</tr>'
    )


def render_model_quality_dashboard(
    results: List[ModelBacktestResult],
) -> str:
    """Render the panel of model backtest results.

    Wraps the body in chartis_shell so the page picks up the
    canonical chrome (nav, theme, accent) and the v3 utility
    classes from /static/v3/chartis.css. The grade/calibration
    badges keep their inline semantic colors — those encode the
    backtest outcome and are part of the data, not the chrome.
    """
    if not results:
        body = (
            '<section style="max-width:80rem;">'
            '<h1 style="margin:0 0 .5rem 0;">Model Quality</h1>'
            '<div style="background:var(--paper,#111827);'
            'border:1px solid var(--border,#374151);border-radius:8px;'
            'padding:2.5rem;text-align:center;color:var(--muted,#9ca3af);">'
            'No backtest results — run '
            '<code>run_model_quality_panel(...)</code> first.'
            '</div>'
            '</section>'
        )
        return chartis_shell(
            body,
            "Model Quality",
            subtitle="trained-model backtests",
        )

    grade_counts: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for r in results:
        grade_counts[r.grade] = grade_counts.get(r.grade, 0) + 1

    well_calibrated = sum(
        1 for r in results
        if r.calibration.quality_label == "well_calibrated"
    )
    overconfident = sum(
        1 for r in results
        if r.calibration.quality_label == "overconfident"
    )

    valid_r2 = [r.cv_r2 for r in results if not math.isnan(r.cv_r2)]
    avg_r2 = sum(valid_r2) / len(valid_r2) if valid_r2 else 0.0

    n_results = len(results)
    kpi_html = (
        '<div style="display:flex;gap:.75rem;flex-wrap:wrap;margin:.75rem 0 1.25rem 0;">'
        + _kpi_card("Models tracked", fmt_num(n_results))
        + _kpi_card("Avg CV R²", f'<span class="num mono">{avg_r2:.3f}</span>')
        + _kpi_card(
            "Grade A/B",
            fmt_num(grade_counts['A'] + grade_counts['B']),
            sub=f"of {n_results}",
        )
        + _kpi_card(
            "Well-calibrated",
            f'{fmt_num(well_calibrated)} / {fmt_num(n_results)}',
            sub="CI within ±5pp of nominal",
        )
        + _kpi_card(
            "Overconfident",
            fmt_num(overconfident),
            sub="CI tighter than reality",
        )
        + '</div>'
    )

    rows = "".join(_row(r) for r in results)
    table_html = (
        '<table style="width:100%;border-collapse:collapse;'
        'border:1px solid var(--border,#374151);'
        'background:var(--paper,#1f2937);border-radius:8px;'
        'overflow:hidden;">'
        '<thead>'
        '<tr style="border-bottom:1px solid var(--border,#374151);">'
        '<th class="micro" style="padding:.6rem 1rem;text-align:left;">Model</th>'
        '<th class="micro" style="padding:.6rem 1rem;text-align:center;">Grade</th>'
        '<th class="micro" style="padding:.6rem 1rem;text-align:right;">CV R²</th>'
        '<th class="micro" style="padding:.6rem 1rem;text-align:right;">MAE</th>'
        '<th class="micro" style="padding:.6rem 1rem;text-align:right;">MAPE</th>'
        '<th class="micro" style="padding:.6rem 1rem;text-align:center;">Calibration</th>'
        '<th class="micro" style="padding:.6rem 1rem;text-align:right;">CI Factor</th>'
        '<th class="micro" style="padding:.6rem 1rem;text-align:right;">Train/Test</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )

    body = (
        '<section style="max-width:80rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:baseline;margin-bottom:.75rem;">'
        '<h1 style="margin:0;">Model Quality</h1>'
        '<a href="/data/catalog" class="micro" style="font-weight:400;'
        'letter-spacing:.04em;text-transform:none;">Data sources →</a>'
        '</div>'
        '<p style="max-width:48rem;color:var(--muted,#9ca3af);'
        'margin:0 0 1rem 0;">'
        'CV R² + MAE + MAPE + grade per trained predictor, plus CI '
        'calibration: observed coverage vs the claimed 90% nominal. '
        'Overconfident models flag where claimed precision exceeds '
        'reality — multiply CI width by the CI Factor to fix.</p>'
        + kpi_html
        + table_html
        + '</section>'
    )

    return chartis_shell(
        body,
        "Model Quality",
        subtitle="trained-model backtests",
    )
