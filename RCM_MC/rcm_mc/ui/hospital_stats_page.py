"""PE Desk Hospital Statistics — per-hospital regression profile.

Shows where a single hospital falls across every variable relative to
national and state peers, with z-scores, percentiles, and regression
residuals. Highlights statistical outliers for diligence investigation.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_bar_row, ck_fmt_num, ck_fmt_pct, ck_kpi_block,
    ck_next_section, ck_panel, ck_provenance_tooltip,
)
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


def _percentile_profile(profile_data: List[tuple]) -> str:
    """National-percentile profile — one labelled bar per metric showing
    where this hospital ranks against the corpus (bar length = national
    percentile). The table's P-number column hides the shape; the bar
    rows make the hospital's spiky profile (top-decile on size, bottom
    quartile on margin, etc.) scannable at a glance.

    Bars are colored on percentile RANK, matching the table's percentile
    badges — not a value judgment (a high expense percentile is not
    "good"); the caption says so.
    """
    if len(profile_data) < 2:
        return ""
    rows = []
    for label, value_str, pct_nat in profile_data:
        if pct_nat >= 75:
            tone = "positive"
        elif pct_nat <= 25:
            tone = "negative"
        else:
            tone = "teal"
        rows.append(ck_bar_row(label, value_str, pct_nat, tone=tone))
    return ck_panel(
        '<p class="ck-section-body" style="margin-bottom:10px;">'
        "Each bar is this hospital's national percentile rank on the "
        "metric — longer is higher in the corpus distribution. Color "
        "marks rank only (top quartile teal-green, bottom quartile red), "
        "not whether high is favorable.</p>"
        + "".join(rows),
        title="National Percentile Profile",
    )


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
    profile_data: List[tuple] = []  # (label, formatted_value, national_percentile)
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

        profile_data.append((label, _fmt_val(val, fmt), pct_nat))

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

    # Cycle 50 — port to ck_kpi_block + provenance.
    margin_value = ck_provenance_tooltip(
        "Operating margin",
        ck_fmt_pct(margin),
        explainer=(
            "Net patient revenue minus operating expenses, "
            "divided by net patient revenue. Healthcare hospital "
            "median is roughly 2-4%; below 0% flags structural "
            "distress unless the hospital is intentionally "
            "trading margin for share."
        ),
    )
    flags_value = ck_provenance_tooltip(
        "Statistical outlier flags",
        ck_fmt_num(len(outlier_flags)),
        explainer=(
            "Metrics where this hospital is more than 2 standard "
            "deviations from the sector median - either a real "
            "operational anomaly worth investigating or a data-"
            "quality artifact worth disqualifying."
        ),
        inject_css=False,
    )
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Beds", _fmt_val(beds, "count"), "licensed")
        + ck_kpi_block("Net Revenue", _fmt_val(rev, "dollars"), "annual NPR")
        + ck_kpi_block("Op Margin", margin_value, "EBIT/Revenue")
        + ck_kpi_block("Occupancy", ck_fmt_pct(occ), "of licensed beds")
        + ck_kpi_block("Outlier Flags", flags_value, ">=2 stdev from median")
        + '</div>'
    )

    # Regression residuals — run quick regressions for key targets
    residual_rows = ""
    # Per-target driver breakdowns: which features pushed THIS
    # hospital's predicted value above or below the corpus mean.
    # Contribution_i = beta_i × (x_i - mean_i) / std_i in the
    # z-scored OLS we fit below. Sum across features = pred - mean.
    driver_blocks: List[str] = []
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

            # Per-feature contribution to the prediction relative to
            # the corpus mean. beta_aug[0] is the intercept (corpus
            # mean in z-scored fit); contributions[i] = beta[i+1] *
            # hosp_xn[i]. The sum equals (hosp_pred - mean(y)).
            mean_y = float(y.mean())
            contribs = [
                (feats[i], float(beta[i + 1] * hosp_xn[i]))
                for i in range(len(feats))
            ]
            # Sort by absolute contribution and take top 3 — partners
            # don't want to read a wall of small-effect features.
            contribs.sort(key=lambda kv: abs(kv[1]), reverse=True)
            top_contribs = contribs[:3]
            # Render as a compact list under the residual row
            driver_items: List[str] = []
            gap = hosp_pred - mean_y
            for feat_name, contrib in top_contribs:
                if abs(contrib) < 1e-9:
                    continue
                # % share of the (pred - mean) gap accounted for by
                # this feature. Helps partner read "Medicare-heavy
                # mix is 60% of why this hospital is predicted lower
                # margin than the average".
                share = (
                    abs(contrib) / abs(gap) if abs(gap) > 1e-9
                    else 0
                )
                sign_color = (
                    PALETTE["positive"] if contrib > 0
                    else PALETTE["negative"]
                )
                arrow = "▲" if contrib > 0 else "▼"
                feat_disp = feat_name.replace("_", " ").title()
                driver_items.append(
                    f'<li style="margin:2px 0;font-size:12px;">'
                    f'<span style="color:{sign_color};font-weight:600;">'
                    f'{arrow} {_fmt_num(contrib)}</span> '
                    f'<span style="color:{PALETTE["text_secondary"]};">'
                    f'({share:.0%} of gap)</span> '
                    f'· {_html.escape(feat_disp)}'
                    f'</li>'
                )
            if driver_items:
                gap_color = (
                    PALETTE["positive"] if gap > 0
                    else PALETTE["negative"]
                )
                driver_blocks.append(
                    f'<div style="margin:0 0 12px 0;">'
                    f'<div style="font-size:11px;'
                    f'color:{PALETTE["text_secondary"]};'
                    f'margin-bottom:4px;letter-spacing:0.04em;'
                    f'text-transform:uppercase;font-weight:600;">'
                    f'{_html.escape(label)} · '
                    f'<span style="color:{gap_color};">'
                    f'{_fmt_num(gap)} vs corpus mean</span></div>'
                    f'<ul class="rg-drivers" '
                    f'style="margin:0;padding-left:18px;">'
                    f'{"".join(driver_items)}'
                    f'</ul></div>'
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

    drivers_section = ""
    if driver_blocks:
        drivers_section = (
            f'<div class="cad-card">'
            f'<h2>What\'s Driving Each Prediction</h2>'
            f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:12px;">'
            f'Top 3 features pushing this hospital\'s predicted value above '
            f'(▲) or below (▼) the corpus mean, for each regression target. '
            f'"% of gap" is each feature\'s share of the predicted-minus-mean '
            f'distance. Helps explain WHY this hospital looks the way it does '
            f'in the residual table above.</p>'
            f'{"".join(driver_blocks)}</div>'
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

    next_up = ck_next_section(
        "Open the hospital profile",
        f"/hospital/{_html.escape(ccn)}",
        eyebrow="Continue —",
        italic_word="profile",
    )
    profile_section = _percentile_profile(profile_data)

    # 2026-05-28 batch 27 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="STATISTICAL PROFILE",
        title=f"Statistical profile — {_html.escape(name)}",
        meta=(
            # helper escapes meta; pass raw — ccn/county/state are
            # CMS-controlled identifiers (8-digit CCN, US state code,
            # county name) so safe to forward unescaped here.
            f"CCN {ccn} · "
            f"{county.upper()}, {state.upper()} · "
            f"{len(outlier_flags)} OUTLIER FLAG"
            f"{'S' if len(outlier_flags) != 1 else ''}"
        ),
        lede_italic_phrase=(
            "Where this hospital sits in the corpus."
        ),
        lede_body=(
            "Per-metric percentile ranks against the HCRIS "
            "corpus, with outlier flags where this hospital "
            "is more than 2 standard deviations from the "
            "sector median. Use this as the deal-day "
            "anchor on whether the operations are typical "
            "or extraordinary."
        ),
    )
    body = (
        f'{head}{kpis}{flags_html}{profile_section}{metrics_section}'
        f'{residual_section}{drivers_section}{actions}{next_up}'
    )

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        f"Statistical Profile — {_html.escape(name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | {_html.escape(county)}, {_html.escape(state)} | "
            f"{len(outlier_flags)} outlier flags"
        ),
    )
