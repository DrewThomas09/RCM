"""SeekingChartis Hospital Statistics — per-hospital regression profile.

Shows where a single hospital falls across every variable relative to
national and state peers, with z-scores, percentiles, and regression
residuals. Highlights statistical outliers for diligence investigation.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import chartis_shell
from .brand import PALETTE
from .regression_page import _add_computed_features, _fmt_num, _COLLINEAR_PAIRS


_DISPLAY_METRICS = [
    ("beds", "Beds", "count"),
    ("net_patient_revenue", "Net Patient Revenue", "dollars"),
    ("operating_expenses", "Operating Expenses", "dollars"),
    ("net_income", "Net Income", "dollars"),
    ("gross_patient_revenue", "Gross Patient Revenue", "dollars"),
    ("total_patient_days", "Total Patient Days", "count"),
    ("medicare_day_pct", "Medicare Day %", "pct"),
    ("medicaid_day_pct", "Medicaid Day %", "pct"),
    ("operating_margin", "Operating Margin", "pct"),
    ("revenue_per_bed", "Revenue per Bed", "dollars"),
    ("occupancy_rate", "Occupancy Rate", "pct"),
    ("commercial_pct", "Commercial Payer %", "pct"),
    ("net_to_gross_ratio", "Net-to-Gross Ratio", "pct"),
    ("expense_per_bed", "Expense per Bed", "dollars"),
    ("revenue_per_day", "Revenue per Patient Day", "dollars"),
    ("payer_diversity", "Payer Diversity Index", "index"),
]


def _fmt_val(val: float, fmt: str) -> str:
    if pd.isna(val):
        return "—"
    if fmt == "dollars":
        return _fmt_num(val)
    if fmt == "pct":
        return f"{val:.1%}" if abs(val) < 2 else f"{val:.1f}%"
    if fmt == "count":
        return f"{val:,.0f}"
    return f"{val:.3f}"


def _percentile_badge(pct: float) -> str:
    if pct >= 90:
        return f'<span style="color:{PALETTE["positive"]};font-weight:600;">P{pct:.0f} &#9650;</span>'
    if pct >= 75:
        return f'<span style="color:{PALETTE["positive"]};">P{pct:.0f}</span>'
    if pct <= 10:
        return f'<span style="color:{PALETTE["negative"]};font-weight:600;">P{pct:.0f} &#9660;</span>'
    if pct <= 25:
        return f'<span style="color:{PALETTE["negative"]};">P{pct:.0f}</span>'
    return f'<span style="color:{PALETTE["text_secondary"]};">P{pct:.0f}</span>'


def render_hospital_stats(ccn: str, hcris_df: pd.DataFrame) -> str:
    """Render per-hospital statistical profile."""
    df = _add_computed_features(hcris_df)
    match = df[df["ccn"] == ccn]
    if match.empty:
        return chartis_shell(
            f'<div class="cad-card"><p>Hospital {_html.escape(ccn)} not found in HCRIS.</p></div>',
            f"Hospital Stats — {_html.escape(ccn)}",
        )

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))
    county = str(hospital.get("county", ""))

    state_df = df[df["state"] == state] if state else df

    # Build metrics table
    metric_rows = ""
    outlier_flags = []
    for col, label, fmt in _DISPLAY_METRICS:
        if col not in df.columns:
            continue
        val = hospital.get(col)
        if pd.isna(val):
            continue
        val = float(val)

        nat_series = df[col].dropna()
        st_series = state_df[col].dropna() if state else nat_series

        if len(nat_series) < 10:
            continue

        nat_mean = float(nat_series.mean())
        nat_std = float(nat_series.std())
        nat_median = float(nat_series.median())
        st_mean = float(st_series.mean()) if len(st_series) >= 5 else nat_mean
        st_median = float(st_series.median()) if len(st_series) >= 5 else nat_median

        z_nat = (val - nat_mean) / nat_std if nat_std > 0 else 0
        pct_nat = float((nat_series < val).mean() * 100)
        pct_st = float((st_series < val).mean() * 100) if len(st_series) >= 5 else pct_nat

        z_color = PALETTE["negative"] if abs(z_nat) > 2 else (PALETTE["warning"] if abs(z_nat) > 1.5 else PALETTE["text_secondary"])

        if abs(z_nat) > 2:
            direction = "above" if z_nat > 0 else "below"
            outlier_flags.append(f"{label}: {z_nat:+.1f}σ {direction} national mean")

        metric_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_html.escape(label)}</td>'
            f'<td class="num">{_fmt_val(val, fmt)}</td>'
            f'<td class="num">{_fmt_val(nat_median, fmt)}</td>'
            f'<td class="num">{_fmt_val(st_median, fmt)}</td>'
            f'<td class="num" style="color:{z_color};font-weight:600;">{z_nat:+.2f}σ</td>'
            f'<td class="num">{_percentile_badge(pct_nat)}</td>'
            f'<td class="num">{_percentile_badge(pct_st)}</td>'
            f'</tr>'
        )

    metrics_section = (
        f'<div class="cad-card">'
        f'<h2>Statistical Profile — All Variables</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
        f'Each metric compared to national (n={len(df):,}) and {_html.escape(state)} '
        f'(n={len(state_df):,}) peers. Z-score shows standard deviations from national mean.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th><th>Hospital</th><th>Nat\'l Median</th><th>{_html.escape(state)} Median</th>'
        f'<th>Z-Score</th><th>Nat\'l %ile</th><th>State %ile</th>'
        f'</tr></thead><tbody>{metric_rows}</tbody></table></div>'
    )

    # Outlier flags
    flags_html = ""
    if outlier_flags:
        flag_items = "".join(
            f'<li style="margin-bottom:4px;">{_html.escape(f)}</li>'
            for f in outlier_flags
        )
        flags_html = (
            f'<div class="cad-card" style="border-left:3px solid {PALETTE["warning"]};">'
            f'<h2 style="color:{PALETTE["warning"]};">Statistical Outliers ({len(outlier_flags)})</h2>'
            f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:8px;">'
            f'Metrics where this hospital is &gt;2 standard deviations from the national mean. '
            f'Investigate in diligence — could signal operational issues or data quality problems.</p>'
            f'<ul style="font-size:12.5px;line-height:1.8;padding-left:20px;">{flag_items}</ul></div>'
        )

    # Peer comparison KPIs
    beds = hospital.get("beds", 0)
    rev = hospital.get("net_patient_revenue", 0)
    margin = hospital.get("operating_margin", 0)
    occ = hospital.get("occupancy_rate", 0)

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_val(beds, "count")}</div>'
        f'<div class="cad-kpi-label">Beds</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_val(rev, "dollars")}</div>'
        f'<div class="cad-kpi-label">Net Revenue</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{margin:.1%}</div>'
        f'<div class="cad-kpi-label">Op Margin</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{occ:.1%}</div>'
        f'<div class="cad-kpi-label">Occupancy</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(outlier_flags)}</div>'
        f'<div class="cad-kpi-label">Outlier Flags</div></div>'
        f'</div>'
    )

    # Regression residuals — run quick regressions for key targets
    residual_rows = ""
    key_targets = [
        "net_patient_revenue", "operating_margin", "occupancy_rate",
        "revenue_per_bed", "net_to_gross_ratio",
    ]
    for tgt in key_targets:
        if tgt not in df.columns or pd.isna(hospital.get(tgt)):
            continue
        feats = [c for c in df.select_dtypes(include=[np.number]).columns
                 if c != tgt and c not in ("ccn",) and c not in _COLLINEAR_PAIRS.get(tgt, set())
                 and df[c].notna().sum() > len(df) * 0.5][:8]
        if len(feats) < 2:
            continue
        try:
            clean = df.dropna(subset=[tgt] + feats)
            if len(clean) < 20:
                continue
            X = clean[feats].fillna(0).values.astype(float)
            y = clean[tgt].fillna(0).values.astype(float)
            X_mean, X_std = X.mean(0), X.std(0)
            X_std[X_std == 0] = 1
            X_n = (X - X_mean) / X_std
            X_aug = np.column_stack([np.ones(len(X_n)), X_n])
            beta = np.linalg.lstsq(X_aug, y, rcond=None)[0]
            ss_res = np.sum((y - X_aug @ beta) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # Predict for this hospital
            hosp_x = np.array([float(hospital.get(f, 0) or 0) for f in feats])
            hosp_xn = (hosp_x - X_mean) / X_std
            hosp_pred = float(np.concatenate([[1], hosp_xn]) @ beta)
            actual = float(hospital.get(tgt))
            residual = actual - hosp_pred
            rmse = np.sqrt(ss_res / max(1, len(y) - len(feats) - 1))
            std_resid = residual / rmse if rmse > 0 else 0

            label = tgt.replace("_", " ").title()
            resid_color = PALETTE["negative"] if abs(std_resid) > 2 else (
                PALETTE["warning"] if abs(std_resid) > 1 else PALETTE["positive"])
            residual_rows += (
                f'<tr>'
                f'<td>{_html.escape(label)}</td>'
                f'<td class="num">{r2:.1%}</td>'
                f'<td class="num">{_fmt_num(actual)}</td>'
                f'<td class="num">{_fmt_num(hosp_pred)}</td>'
                f'<td class="num" style="color:{resid_color};font-weight:600;">{std_resid:+.2f}σ</td>'
                f'</tr>'
            )
        except Exception:
            continue

    residual_section = ""
    if residual_rows:
        residual_section = (
            f'<div class="cad-card">'
            f'<h2>Multi-Variable Regression Residuals</h2>'
            f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:10px;">'
            f'For each key metric, the national regression model predicts a value. The residual '
            f'shows how much this hospital over/under-performs after controlling for all other variables.</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Target</th><th>Model R&sup2;</th><th>Actual</th><th>Predicted</th><th>Residual</th>'
            f'</tr></thead><tbody>{residual_rows}</tbody></table></div>'
        )

    # Actions
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/hospital/{_html.escape(ccn)}/demand" class="cad-btn" '
        f'style="text-decoration:none;">Demand Analysis</a>'
        f'<a href="/hospital/{_html.escape(ccn)}/history" class="cad-btn" '
        f'style="text-decoration:none;">3-Year History</a>'
        f'<a href="/portfolio/regression" class="cad-btn" '
        f'style="text-decoration:none;">National Regression</a>'
        f'<a href="/market-data/state/{_html.escape(state)}" class="cad-btn" '
        f'style="text-decoration:none;">{_html.escape(state)} Market</a>'
        f'</div>'
    )

    body = f'{kpis}{flags_html}{metrics_section}{residual_section}{actions}'

    return chartis_shell(
        body,
        f"Statistical Profile — {_html.escape(name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | {_html.escape(county)}, {_html.escape(state)} | "
            f"{len(outlier_flags)} outlier flags"
        ),
    )
