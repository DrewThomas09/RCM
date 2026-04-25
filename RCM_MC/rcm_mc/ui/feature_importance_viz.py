"""Feature importance visualization — SVG horizontal bar charts.

Pure SVG, no JS chart libraries. Each feature gets a horizontal
bar with magnitude proportional to relative importance and color
encoding the sign (green = positive driver, red = negative).

Public API::

    render_importance_bar_chart(importances, title) -> str
    render_importance_panel(model_importances) -> str
    render_feature_importance_page(model_importances) -> str
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from ..ml.feature_importance import FeatureImportance
from .colors import STATUS


# Status colors come from the semantic palette
_COLOR_POSITIVE = STATUS["positive"]
_COLOR_NEGATIVE = STATUS["negative"]
_COLOR_NEUTRAL = STATUS["neutral"]
_TEXT_COLOR = "#f3f4f6"
_AXIS_COLOR = "#374151"
_BG_COLOR = "#1f2937"


def _bar_color(direction: str) -> str:
    return {
        "positive": _COLOR_POSITIVE,
        "negative": _COLOR_NEGATIVE,
        "neutral": _COLOR_NEUTRAL,
    }.get(direction, _COLOR_NEUTRAL)


def render_importance_bar_chart(
    importances: List[FeatureImportance],
    *,
    title: Optional[str] = None,
    width: int = 540,
    bar_height: int = 22,
    bar_gap: int = 6,
    max_bars: int = 12,
) -> str:
    """Render one model's feature importance as an SVG bar chart.

    Bars are signed: positive drivers extend right from a center
    axis, negative drivers extend left. Length proportional to
    |raw_value|, colored by direction.
    """
    if not importances:
        return (
            f'<div style="background:{_BG_COLOR};'
            f'border:1px solid {_AXIS_COLOR};border-radius:8px;'
            f'padding:24px;text-align:center;color:#9ca3af;'
            f'font-size:13px;">No feature importance data.</div>')

    items = importances[:max_bars]
    label_col_w = 200
    chart_w = width - label_col_w - 60
    height = (bar_height + bar_gap) * len(items) + 40

    # Magnitude scaling — center axis, bars extend left or right
    max_abs = max((abs(i.raw_value) for i in items),
                  default=1.0)
    if max_abs <= 0:
        max_abs = 1.0
    half_chart = chart_w / 2
    center_x = label_col_w + half_chart

    title_html = ""
    if title:
        title_html = (
            f'<text x="0" y="14" fill="{_TEXT_COLOR}" '
            f'font-size="13" font-weight="600">'
            f'{_html.escape(title)}</text>')

    # Center axis line
    rows = []
    for i, imp in enumerate(items):
        y = 30 + i * (bar_height + bar_gap)
        bar_len = abs(imp.raw_value) / max_abs * half_chart
        if imp.direction == "negative":
            x_start = center_x - bar_len
            x_text = center_x - bar_len - 4
            text_anchor = "end"
        else:
            x_start = center_x
            x_text = center_x + bar_len + 4
            text_anchor = "start"
        color = _bar_color(imp.direction)
        # Label (left)
        label = _html.escape(imp.feature[:30])
        rows.append(
            f'<text x="{label_col_w - 8}" y="{y + 14}" '
            f'fill="{_TEXT_COLOR}" font-size="11" '
            f'text-anchor="end" '
            f'font-family="ui-monospace, monospace">'
            f'{label}</text>')
        # Bar
        rows.append(
            f'<rect x="{x_start}" y="{y}" '
            f'width="{bar_len}" height="{bar_height}" '
            f'fill="{color}" rx="2" />')
        # Value text
        val_text = (f"{imp.raw_value:+.3f} · "
                    f"{imp.relative:.0%}")
        rows.append(
            f'<text x="{x_text}" y="{y + 14}" '
            f'fill="#9ca3af" font-size="10" '
            f'text-anchor="{text_anchor}" '
            f'font-family="ui-monospace, monospace">'
            f'{val_text}</text>')

    # Center axis line
    axis = (
        f'<line x1="{center_x}" y1="22" '
        f'x2="{center_x}" y2="{height - 8}" '
        f'stroke="{_AXIS_COLOR}" stroke-width="1" />')

    return (
        f'<div style="background:{_BG_COLOR};'
        f'border:1px solid {_AXIS_COLOR};border-radius:8px;'
        f'padding:14px;margin-bottom:14px;">'
        f'<svg viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
        f'{title_html}{axis}'
        f'{"".join(rows)}</svg></div>')


def render_importance_panel(
    model_importances: Dict[
        str, List[FeatureImportance]],
) -> str:
    """Render a panel of importance charts, one per model."""
    if not model_importances:
        return (
            '<div style="color:#9ca3af;">No models to '
            'visualize.</div>')
    sections = []
    for model_name, imps in model_importances.items():
        sections.append(render_importance_bar_chart(
            imps, title=model_name))
    return "".join(sections)


def render_feature_importance_page(
    model_importances: Dict[
        str, List[FeatureImportance]],
) -> str:
    """Render the full /models/importance page."""
    if not model_importances:
        body = (
            f'<div style="background:#111827;'
            f'border:1px solid {_AXIS_COLOR};'
            f'border-radius:8px;padding:40px;'
            f'text-align:center;color:#9ca3af;">'
            f'No model importance data — train models '
            f'and build importance via '
            f'<code>importance_from_trained_ridge(...)</code> '
            f'first.</div>')
    else:
        body = render_importance_panel(model_importances)

    return (
        '<div style="max-width:1200px;margin:0 auto;'
        'padding:24px;">'
        '<div style="display:flex;'
        'justify-content:space-between;'
        'align-items:baseline;margin-bottom:16px;">'
        '<h1 style="font-size:24px;color:#f3f4f6;'
        'margin:0;">Feature Importance</h1>'
        '<a href="/models/quality" '
        'style="color:#60a5fa;font-size:13px;">'
        'Model quality →</a></div>'
        '<p style="color:#9ca3af;font-size:13px;'
        'margin:0 0 18px 0;max-width:720px;">'
        'What drives each model\'s predictions. Bars extend '
        'right (positive drivers) or left (negative). Length '
        'proportional to |coefficient|; relative '
        'importance shown as percent.</p>'
        + body + '</div>')


def _build_default_importance_panel(
) -> Dict[str, List[FeatureImportance]]:
    """Build a panel of importance charts for the standard
    trained predictors using synthesized training data.

    Mirrors model_quality._build_default_quality_panel —
    real-deployment partners override with their own trained
    predictors.
    """
    import numpy as np
    from ..ml.trained_rcm_predictor import (
        train_ridge_with_cv,
    )
    from ..ml.feature_importance import (
        importance_from_trained_ridge,
    )

    rng = np.random.default_rng(42)
    out: Dict[str, List[FeatureImportance]] = {}

    # Denial rate
    n = 200
    X = rng.normal(0, 1, size=(n, 13))
    beta = np.array([
        -0.1, 0.05, 0.10, -0.05, -0.05, -0.04, 0.02,
        -0.02, 0.03, 0.02, -0.03, 0.05, 0.05])
    y = X @ beta + 0.10 + rng.normal(0, 0.02, n)
    y = np.clip(y, 0.0, 0.40)
    feature_names = [
        "beds_log", "medicare_pct", "medicaid_pct",
        "occupancy", "n2g_ratio", "operating_margin",
        "case_mix_proxy", "star_rating",
        "readmission_rate", "mortality_rate",
        "hcahps_score", "ma_penetration",
        "state_rcm_factor",
    ]
    try:
        p = train_ridge_with_cv(
            X, y, feature_names=feature_names,
            target_metric="denial_rate",
            sanity_range=(0.0, 0.40))
        out["Denial Rate Predictor"] = (
            importance_from_trained_ridge(p))
    except Exception:
        pass

    # Days in AR
    X2 = rng.normal(0, 1, size=(n, 12))
    beta2 = np.array([
        -3.0, -2.0, 5.0, 8.0, 12.0, 6.0, -4.0, 4.0,
        3.0, 2.0, 5.0, -8.0])
    y2 = X2 @ beta2 + 45 + rng.normal(0, 4, n)
    y2 = np.clip(y2, 15.0, 120.0)
    feature_names_2 = [
        "beds_log", "discharges_log", "medicare_pct",
        "medicaid_pct", "self_pay_pct", "case_mix_proxy",
        "occupancy", "ma_penetration",
        "ma_x_medicaid", "state_rcm_factor",
        "rural_flag", "operating_margin",
    ]
    try:
        p = train_ridge_with_cv(
            X2, y2, feature_names=feature_names_2,
            target_metric="days_in_ar",
            sanity_range=(15.0, 120.0))
        out["Days in AR Predictor"] = (
            importance_from_trained_ridge(p))
    except Exception:
        pass

    # Collection rate
    X3 = rng.normal(0, 1, size=(n, 13))
    beta3 = np.array([
        0.005, -0.003, -0.008, -0.015, 0.010, 0.002,
        0.003, -0.020, -0.005, 0.008, -0.005, -0.005,
        -0.003])
    y3 = X3 @ beta3 + 0.96 + rng.normal(0, 0.005, n)
    y3 = np.clip(y3, 0.70, 1.00)
    feature_names_3 = [
        "beds_log", "medicare_pct", "medicaid_pct",
        "self_pay_pct", "operating_margin",
        "case_mix_proxy", "occupancy",
        "denial_rate_input", "days_in_ar_input",
        "hcahps_score", "ma_penetration",
        "rural_flag", "state_rcm_factor",
    ]
    try:
        p = train_ridge_with_cv(
            X3, y3, feature_names=feature_names_3,
            target_metric="collection_rate",
            sanity_range=(0.70, 1.00))
        out["Collection Rate Predictor"] = (
            importance_from_trained_ridge(p))
    except Exception:
        pass

    return out
