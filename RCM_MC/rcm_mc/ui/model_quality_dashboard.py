"""Model quality dashboard — `/models/quality`.

Renders a panel of trained-model backtest results: R² + MAE +
MAPE + grade + CI calibration (observed vs nominal coverage).

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
from .colors import STATUS


# Grade colors anchor to the semantic palette: A/B = good (green/info),
# C = watch (amber), D/F = bad (red).
_GRADE_COLORS = {
    "A": (STATUS["positive_bg"], STATUS["positive_fg"]),
    "B": (STATUS["info_bg"], STATUS["info_fg"]),
    "C": (STATUS["watch_bg"], STATUS["watch_fg"]),
    "D": ("#7c2d12", "#fed7aa"),
    "F": (STATUS["negative_bg"], STATUS["negative_fg"]),
}

_CALIB_COLORS = {
    "well_calibrated": (STATUS["positive_bg"],
                        STATUS["positive_fg"]),
    "overconfident": (STATUS["negative_bg"],
                      STATUS["negative_fg"]),
    "underconfident": (STATUS["watch_bg"],
                       STATUS["watch_fg"]),
    "no_data": (STATUS["neutral_bg"], STATUS["neutral_fg"]),
    "failed": (STATUS["negative_bg"],
               STATUS["negative_fg"]),
}


def _grade_badge(grade: str) -> str:
    bg, fg = _GRADE_COLORS.get(grade, ("#374151", "#9ca3af"))
    return (
        f'<span style="display:inline-block;padding:2px 10px;'
        f'border-radius:4px;background:{bg};color:{fg};'
        f'font-size:13px;font-weight:600;">{_html.escape(grade)}'
        f'</span>')


def _calib_badge(label: str, observed: float,
                 nominal: float) -> str:
    bg, fg = _CALIB_COLORS.get(
        label, ("#374151", "#9ca3af"))
    text = (f"{label.replace('_', ' ')} · "
            f"{observed:.0%}/{nominal:.0%}")
    return (
        f'<span style="display:inline-block;padding:2px 8px;'
        f'border-radius:4px;background:{bg};color:{fg};'
        f'font-size:11px;font-variant-numeric:tabular-nums;">'
        f'{_html.escape(text)}</span>')


def _kpi_card(label: str, value: str, sub: str = "") -> str:
    return (
        '<div style="background:#1f2937;border:1px solid #374151;'
        'border-radius:8px;padding:14px 18px;flex:1;'
        'min-width:170px;">'
        f'<div style="font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:#9ca3af;'
        f'margin-bottom:6px;">{_html.escape(label)}</div>'
        f'<div style="font-size:22px;font-weight:600;'
        f'color:#f3f4f6;font-variant-numeric:tabular-nums;">'
        f'{_html.escape(value)}</div>'
        + (f'<div style="font-size:11px;color:#6b7280;'
           f'margin-top:4px;">{_html.escape(sub)}</div>'
           if sub else "")
        + "</div>")


def _row(r: ModelBacktestResult) -> str:
    cv_r2 = (f"{r.cv_r2:.3f}"
             if not math.isnan(r.cv_r2) else "—")
    cv_mae = (f"{r.cv_mae:,.3f}"
              if not math.isnan(r.cv_mae) else "—")
    mape = (f"{r.cv_mape:.1%}"
            if r.cv_mape is not None
            and not math.isnan(r.cv_mape) else "—")
    notes_html = ""
    if r.notes:
        notes_html = ('<div style="margin-top:6px;">'
                      + "".join(
                          f'<div style="font-size:11px;'
                          f'color:#9ca3af;margin-top:2px;">'
                          f'{_html.escape(n)}</div>'
                          for n in r.notes)
                      + "</div>")
    return (
        '<tr>'
        f'<td style="padding:12px 14px;color:#f3f4f6;">'
        f'<div style="font-weight:500;">'
        f'{_html.escape(r.model_name)}</div>'
        f'<div style="font-size:11px;color:#9ca3af;'
        f'margin-top:2px;">target: '
        f'{_html.escape(r.target_metric)} · '
        f'{r.feature_count} features</div>'
        f'{notes_html}'
        f'</td>'
        f'<td style="padding:12px 14px;text-align:center;">'
        f'{_grade_badge(r.grade)}</td>'
        f'<td style="padding:12px 14px;text-align:right;'
        f'color:#d1d5db;font-variant-numeric:tabular-nums;">'
        f'{cv_r2}</td>'
        f'<td style="padding:12px 14px;text-align:right;'
        f'color:#d1d5db;font-variant-numeric:tabular-nums;">'
        f'{cv_mae}</td>'
        f'<td style="padding:12px 14px;text-align:right;'
        f'color:#d1d5db;font-variant-numeric:tabular-nums;">'
        f'{mape}</td>'
        f'<td style="padding:12px 14px;text-align:center;">'
        f'{_calib_badge(r.calibration.quality_label, r.calibration.observed_coverage, r.calibration.nominal_coverage)}'
        f'</td>'
        f'<td style="padding:12px 14px;text-align:right;'
        f'color:#d1d5db;font-variant-numeric:tabular-nums;">'
        f'{r.calibration.calibration_factor:.2f}'
        f'</td>'
        f'<td style="padding:12px 14px;text-align:right;'
        f'color:#9ca3af;font-variant-numeric:tabular-nums;">'
        f'{r.n_train:,} / {r.n_holdout:,}</td>'
        '</tr>')


def render_model_quality_dashboard(
    results: List[ModelBacktestResult],
) -> str:
    """Render the panel of model backtest results."""
    if not results:
        return (
            '<div style="max-width:1200px;margin:0 auto;'
            'padding:24px;">'
            '<h1 style="font-size:24px;color:#f3f4f6;'
            'margin:0 0 8px 0;">Model Quality</h1>'
            '<div style="background:#111827;border:1px solid '
            '#374151;border-radius:8px;padding:40px;'
            'text-align:center;color:#9ca3af;">'
            'No backtest results — run '
            '<code>run_model_quality_panel(...)</code> first.'
            '</div></div>')

    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for r in results:
        grade_counts[r.grade] = (
            grade_counts.get(r.grade, 0) + 1)

    well_calibrated = sum(
        1 for r in results
        if r.calibration.quality_label == "well_calibrated")
    overconfident = sum(
        1 for r in results
        if r.calibration.quality_label == "overconfident")

    valid_r2 = [r.cv_r2 for r in results
                if not math.isnan(r.cv_r2)]
    avg_r2 = (sum(valid_r2) / len(valid_r2)
              if valid_r2 else 0.0)

    kpi_html = (
        '<div style="display:flex;gap:12px;flex-wrap:wrap;'
        'margin-bottom:18px;">'
        + _kpi_card("Models tracked",
                    str(len(results)))
        + _kpi_card("Avg CV R²", f"{avg_r2:.3f}")
        + _kpi_card("Grade A/B",
                    f"{grade_counts['A'] + grade_counts['B']}",
                    f"of {len(results)}")
        + _kpi_card("Well-calibrated",
                    f"{well_calibrated} / "
                    f"{len(results)}",
                    "CI within ±5pp of nominal")
        + _kpi_card("Overconfident",
                    str(overconfident),
                    "CI tighter than reality")
        + "</div>"
    )

    rows = "".join(_row(r) for r in results)

    table_html = (
        '<table style="width:100%;border-collapse:collapse;'
        'background:#1f2937;border:1px solid #374151;'
        'border-radius:8px;overflow:hidden;">'
        '<thead><tr style="background:#111827;'
        'border-bottom:1px solid #374151;">'
        '<th style="padding:10px 14px;text-align:left;'
        'font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;color:#9ca3af;">Model</th>'
        '<th style="padding:10px 14px;text-align:center;'
        'font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;color:#9ca3af;">Grade</th>'
        '<th style="padding:10px 14px;text-align:right;'
        'font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;color:#9ca3af;">CV R²</th>'
        '<th style="padding:10px 14px;text-align:right;'
        'font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;color:#9ca3af;">MAE</th>'
        '<th style="padding:10px 14px;text-align:right;'
        'font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;color:#9ca3af;">MAPE</th>'
        '<th style="padding:10px 14px;text-align:center;'
        'font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;color:#9ca3af;">Calibration</th>'
        '<th style="padding:10px 14px;text-align:right;'
        'font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;color:#9ca3af;">CI Factor</th>'
        '<th style="padding:10px 14px;text-align:right;'
        'font-size:11px;text-transform:uppercase;'
        'letter-spacing:0.05em;color:#9ca3af;">Train/Test</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>')

    return (
        '<div style="max-width:1280px;margin:0 auto;'
        'padding:24px;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:baseline;margin-bottom:16px;">'
        '<h1 style="font-size:24px;color:#f3f4f6;margin:0;">'
        'Model Quality</h1>'
        '<a href="/data/catalog" style="color:#60a5fa;'
        'font-size:13px;">Data sources →</a></div>'
        '<p style="color:#9ca3af;font-size:13px;'
        'margin:0 0 18px 0;max-width:720px;">'
        'CV R² + MAE + MAPE + grade per trained predictor, plus '
        'CI calibration: observed coverage vs the claimed 90% '
        'nominal. Overconfident models flag where claimed '
        'precision exceeds reality — multiply CI width by the '
        'CI Factor to fix.</p>'
        + kpi_html + table_html + '</div>')
