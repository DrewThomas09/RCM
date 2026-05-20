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
from ._chartis_kit import (
    chartis_shell, ck_fmt_num, ck_kpi_block, ck_next_section,
    ck_provenance_tooltip,
)
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
    "D": ("#f0dcd0", "#8a3a18"),
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
    bg, fg = _GRADE_COLORS.get(grade, ("#ece5d6", "#7a8699"))
    return (
        f'<span style="display:inline-block;padding:.15rem .65rem;'
        f'border-radius:4px;background:{bg};color:{fg};'
        f'font-size:.85rem;font-weight:600;">{_html.escape(grade)}</span>'
    )


def _calib_badge(label: str, observed: float, nominal: float) -> str:
    bg, fg = _CALIB_COLORS.get(label, ("#ece5d6", "#7a8699"))
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
        f'<div class="micro" style="margin-top:.35rem;color:var(--muted,#9b9382);">'
        f'{_html.escape(sub)}</div>' if sub else ""
    )
    return (
        '<div style="border:1px solid var(--border,#465366);'
        'background:var(--paper,#F2EDE3);border-radius:8px;'
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
                f'<div style="font-size:.7rem;color:var(--muted,#9b9382);'
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
        f'<td style="padding:.8rem 1rem;text-align:right;color:var(--muted,#9b9382);">'
        f'{fmt_num(r.n_train)} / {fmt_num(r.n_holdout)}</td>'
        '</tr>'
    )


def _r2_bar_chart(results: List["ModelBacktestResult"]) -> str:
    """SVG horizontal-bar chart: CV R² per tracked model.

    Sorted highest-R² on top so the partner sees which models pull
    their weight at a glance. Color-coded by grade (A=green, B=teal,
    C=amber, D/F=red) — overconfident calibration adds a tick-mark
    indicator on the right of the bar.
    """
    plotted = [r for r in results if not math.isnan(r.cv_r2)]
    if not plotted:
        return ""
    plotted.sort(key=lambda r: r.cv_r2, reverse=True)

    width = 720
    row_h = 24
    pad_l, pad_r, pad_t, pad_b = 220, 60, 28, 38
    inner_w = width - pad_l - pad_r
    height = pad_t + len(plotted) * row_h + pad_b

    # X-axis: 0 to max(R²)+0.05, capped at 1.0
    max_r2 = min(1.0, max(r.cv_r2 for r in plotted) + 0.05)

    def sx(v: float) -> float:
        return pad_l + max(0.0, min(v, 1.0)) / max_r2 * inner_w

    grid = []
    for v in (0.25, 0.5, 0.7, 0.9):
        if v > max_r2:
            continue
        x = sx(v)
        grid.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" '
            f'y1="{pad_t}" y2="{pad_t + len(plotted) * row_h}" '
            f'stroke="#d6cfc0" stroke-dasharray="2,4" />'
            f'<text x="{x:.1f}" y="{pad_t + len(plotted) * row_h + 14}" '
            f'fill="#7a8699" text-anchor="middle" font-size="10" '
            f'font-family="JetBrains Mono, monospace">'
            f'{v:.2f}</text>'
        )

    grade_colors = {
        "A": "#0a8a5f",
        "B": "#155752",
        "C": "#b8732a",
        "D": "#b5321e",
        "F": "#7a3478",
    }

    elements = []
    for i, r in enumerate(plotted):
        cy = pad_t + i * row_h + row_h / 2
        color = grade_colors.get(r.grade, "#465366")
        x_right = sx(r.cv_r2)
        bar_w = x_right - pad_l
        elements.append(
            f'<rect x="{pad_l:.1f}" y="{cy - 8:.1f}" '
            f'width="{max(1.0, bar_w):.1f}" height="16" '
            f'fill="{color}" fill-opacity="0.85" '
            f'stroke="{color}" stroke-width="0.5">'
            f'<title>{_html.escape(r.model_name)}: '
            f'CV R² {r.cv_r2:.3f} · grade {r.grade} · '
            f'calibration {r.calibration.quality_label}</title>'
            f'</rect>'
        )
        # Model name (right-aligned in left gutter)
        name = r.model_name
        name_disp = name if len(name) <= 30 else name[:27] + "…"
        elements.append(
            f'<text x="{pad_l - 10:.1f}" y="{cy + 3:.1f}" '
            f'fill="#1a2332" text-anchor="end" font-size="11" '
            f'font-family="Inter, sans-serif">'
            f'{_html.escape(name_disp)}</text>'
        )
        # R² value + grade chip on the right
        elements.append(
            f'<text x="{x_right + 6:.1f}" y="{cy + 3:.1f}" '
            f'fill="{color}" text-anchor="start" font-size="10" '
            f'font-family="JetBrains Mono, monospace" '
            f'font-weight="700">{r.cv_r2:.2f} · {r.grade}</text>'
        )
        # Overconfident indicator (tick on the left edge of the bar)
        if r.calibration.quality_label == "overconfident":
            elements.append(
                f'<line x1="{pad_l:.1f}" x2="{pad_l - 4:.1f}" '
                f'y1="{cy:.1f}" y2="{cy:.1f}" '
                f'stroke="#b5321e" stroke-width="3" />'
            )

    axis_label = (
        f'<text x="{pad_l + inner_w / 2:.1f}" y="{height - 8}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600">'
        f'CV R² (0 = baseline, 1 = perfect)</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;background:transparent;'
        f'margin:8px 0 16px;">'
        f'{"".join(grid)}'
        f'{"".join(elements)}'
        f'{axis_label}'
        f'</svg>'
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
            '<div style="background:var(--paper,#F2EDE3);'
            'border:1px solid var(--border,#465366);border-radius:8px;'
            'padding:2.5rem;text-align:center;color:var(--muted,#9b9382);">'
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
    # Cycle 54 — port to ck_kpi_block + provenance.
    r2_value = ck_provenance_tooltip(
        "Average cross-validated R²",
        f"{avg_r2:.3f}",
        explainer=(
            f"Mean R² across {n_results} tracked models, computed "
            f"on held-out cross-validation folds. Above 0.7 = "
            f"models earning their place; below 0.5 = sector-"
            f"median baseline beats them on average."
        ),
    )
    grade_value = ck_provenance_tooltip(
        "Grade A/B models",
        ck_fmt_num(grade_counts['A'] + grade_counts['B']),
        explainer=(
            f"Models scoring A or B on the composite quality "
            f"grade (R-squared, MAE, calibration). Currently "
            f"{grade_counts['A']} A-grade + {grade_counts['B']} B-"
            f"grade out of {n_results} tracked. C/D grades are "
            f"flagged on dependent pages."
        ),
        inject_css=False,
    )
    kpi_html = (
        '<div class="ck-kpi-grid" style="display:flex;gap:.75rem;flex-wrap:wrap;margin:.75rem 0 1.25rem 0;">'
        + ck_kpi_block("Models Tracked", ck_fmt_num(n_results), "in registry")
        + ck_kpi_block("Avg CV R²", r2_value, "predictive power")
        + ck_kpi_block("Grade A/B", grade_value, f"of {n_results}")
        + ck_kpi_block("Well-calibrated",
                       f"{ck_fmt_num(well_calibrated)} / {ck_fmt_num(n_results)}",
                       "CI within +/-5pp")
        + ck_kpi_block("Overconfident", ck_fmt_num(overconfident),
                       "CI tighter than reality")
        + '</div>'
    )

    r2_chart = _r2_bar_chart(results)
    rows = "".join(_row(r) for r in results)
    table_html = (
        '<table style="width:100%;border-collapse:collapse;'
        'border:1px solid var(--border,#465366);'
        'background:var(--paper,#F2EDE3);border-radius:8px;'
        'overflow:hidden;">'
        '<thead>'
        '<tr style="border-bottom:1px solid var(--border,#465366);">'
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
        # Title / eyebrow / deck come from chartis_shell's editorial_intro
        # below — no hand-rolled header here (it produced a duplicate
        # "Model Quality" <h1>). Keep the inline cross-link only.
        '<section style="max-width:80rem;">'
        '<div style="display:flex;justify-content:flex-end;'
        'align-items:baseline;margin-bottom:.75rem;">'
        '<a href="/data/catalog" class="micro" style="font-weight:400;'
        'letter-spacing:.04em;text-transform:none;">Data sources →</a>'
        '</div>'
        + kpi_html
        + r2_chart
        + table_html
        + '</section>'
        + ck_next_section(
            "Open the feature importance view",
            "/models/importance",
            eyebrow="Continue —",
            italic_word="feature",
        )
    )

    return chartis_shell(
        body,
        "Model Quality",
        subtitle="trained-model backtests",
        editorial_intro={
            "eyebrow": "MODEL QUALITY",
            "headline": "Where each model has earned its keep.",
            "italic_word": "earned",
            "body": (
                "Trained-model backtest scorecards: R-squared, "
                "MAE, calibration, and confidence intervals. "
                "Models below their stated quality threshold "
                "are auto-flagged - pages depending on those "
                "models surface a warning chip."
            ),
        },
    )
