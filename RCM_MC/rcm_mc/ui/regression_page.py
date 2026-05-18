"""PE Desk Regression Page — interactive statistical analysis.

Full-featured OLS regression with per-hospital residual analysis,
state-level breakdowns, feature importance ranking, variance inflation
factors, and hospital-specific outlier detection.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro,
)
from .brand import PALETTE
from ..data.hospital_taxonomy import (
    derive_taxonomy, filter_to_universe, SEGMENT_LABELS,
)
from ..finance.regression import run_segmented_regression as _run_segmented
from ..finance.leakage import (
    audit_features as _audit_leakage,
    forecasting_safe_features as _safe_features,
)


_AVAILABLE_METRICS = [
    ("denial_rate", "Denial Rate"),
    ("days_in_ar", "Days in AR"),
    ("net_collection_rate", "Net Collection Rate"),
    ("clean_claim_rate", "Clean Claim Rate"),
    ("cost_to_collect", "Cost to Collect"),
    ("ebitda_margin", "EBITDA Margin"),
    ("net_revenue", "Net Revenue"),
    ("bed_count", "Bed Count"),
    ("claims_volume", "Claims Volume"),
]

_HCRIS_METRICS = [
    ("beds", "Beds"),
    ("net_patient_revenue", "Net Patient Revenue"),
    ("operating_expenses", "Operating Expenses"),
    ("medicare_day_pct", "Medicare Day %"),
    ("medicaid_day_pct", "Medicaid Day %"),
    ("total_patient_days", "Total Patient Days"),
    ("medicare_days", "Medicare Days"),
    ("medicaid_days", "Medicaid Days"),
    ("bed_days_available", "Bed Days Available"),
    ("net_income", "Net Income"),
    ("gross_patient_revenue", "Gross Patient Revenue"),
    ("contractual_allowances", "Contractual Allowances"),
]

_COMPUTED_HCRIS = [
    ("revenue_per_bed", "Revenue per Bed"),
    ("occupancy_rate", "Occupancy Rate"),
    ("commercial_pct", "Commercial Payer %"),
    ("operating_margin", "Operating Margin"),
    ("net_to_gross_ratio", "Net-to-Gross Ratio"),
    ("expense_per_bed", "Expense per Bed"),
    ("revenue_per_day", "Revenue per Patient Day"),
    ("medicare_intensity", "Medicare Intensity"),
    ("payer_diversity", "Payer Diversity Index"),
    ("size_quartile", "Size Quartile"),
]

_COLLINEAR_PAIRS = {
    "net_income": {"net_patient_revenue", "operating_expenses", "gross_patient_revenue", "contractual_allowances"},
    "operating_expenses": {"net_income", "net_patient_revenue", "gross_patient_revenue", "contractual_allowances"},
    "net_patient_revenue": {"net_income", "operating_expenses", "gross_patient_revenue", "contractual_allowances"},
    "gross_patient_revenue": {"net_patient_revenue", "contractual_allowances", "operating_expenses", "net_income"},
    "contractual_allowances": {"gross_patient_revenue", "net_patient_revenue"},
}


def _add_computed_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add all computed regression features to HCRIS DataFrame."""
    df = df.copy()
    if "beds" in df.columns and "net_patient_revenue" in df.columns:
        df["revenue_per_bed"] = df["net_patient_revenue"] / df["beds"].replace(0, np.nan)
    if "total_patient_days" in df.columns and "bed_days_available" in df.columns:
        df["occupancy_rate"] = df["total_patient_days"] / df["bed_days_available"].replace(0, np.nan)
    if "medicare_day_pct" in df.columns and "medicaid_day_pct" in df.columns:
        mc = df["medicare_day_pct"].fillna(0)
        md = df["medicaid_day_pct"].fillna(0)
        df["commercial_pct"] = (1.0 - mc - md).clip(0, 1)
        df["payer_diversity"] = 1 - (mc**2 + md**2 + df["commercial_pct"]**2)
        df["medicare_intensity"] = mc * df.get("beds", pd.Series(1, index=df.index))
    if "net_patient_revenue" in df.columns and "operating_expenses" in df.columns:
        rev = df["net_patient_revenue"]
        opex = df["operating_expenses"]
        safe_rev = rev.where(rev > 1e5)
        raw_margin = (safe_rev - opex) / safe_rev
        # Flag: if opex > 2x revenue, margin is unreliable (state-funded,
        # psychiatric, or partial-year filing). Cap at -50%.
        df["operating_margin"] = raw_margin.clip(-0.5, 1.0)
        df["margin_unreliable"] = (opex > rev * 2) & (rev > 1e5)
    if "net_patient_revenue" in df.columns and "gross_patient_revenue" in df.columns:
        df["net_to_gross_ratio"] = (
            df["net_patient_revenue"] /
            df["gross_patient_revenue"].replace(0, np.nan)
        ).clip(0, 1)
    if "operating_expenses" in df.columns and "beds" in df.columns:
        df["expense_per_bed"] = df["operating_expenses"] / df["beds"].replace(0, np.nan)
    if "net_patient_revenue" in df.columns and "total_patient_days" in df.columns:
        df["revenue_per_day"] = (
            df["net_patient_revenue"] /
            df["total_patient_days"].replace(0, np.nan)
        )
    if "beds" in df.columns:
        try:
            df["size_quartile"] = pd.qcut(
                df["beds"].fillna(0), q=4, labels=[1, 2, 3, 4], duplicates="drop"
            ).astype(float)
        except Exception:
            df["size_quartile"] = 2.0
    return df


def _compute_vif(X: np.ndarray, features: List[str]) -> List[Dict[str, Any]]:
    """Variance Inflation Factors for multicollinearity detection."""
    vifs = []
    for i in range(X.shape[1]):
        others = np.delete(X, i, axis=1)
        if others.shape[1] == 0:
            vifs.append({"feature": features[i], "vif": 1.0})
            continue
        others_aug = np.column_stack([np.ones(len(others)), others])
        beta = np.linalg.lstsq(others_aug, X[:, i], rcond=None)[0]
        y_hat = others_aug @ beta
        ss_res = np.sum((X[:, i] - y_hat) ** 2)
        ss_tot = np.sum((X[:, i] - X[:, i].mean()) ** 2)
        r2_i = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        vif = 1 / (1 - r2_i) if r2_i < 1 else 999
        vifs.append({"feature": features[i], "vif": round(vif, 2)})
    return sorted(vifs, key=lambda x: -x["vif"])


def _run_ols(
    df: pd.DataFrame,
    target: str,
    features: List[str],
    log_target: bool = False,
) -> Optional[Dict[str, Any]]:
    """Run OLS regression with comprehensive diagnostics.

    ``log_target=True`` fits ``ln(target)`` instead of raw values.
    Targets like net_patient_revenue span six orders of magnitude
    (rural CAH ~ $400K → academic ~ $9B); raw-dollar OLS gives the
    biggest hospitals overwhelming weight on the loss. Log space
    makes the model reason in percentage terms. Coefficients on a
    log fit are semi-elasticities — a one-unit feature change
    produces a ``β`` fractional change in the target.
    """
    available = [f for f in features if f in df.columns and df[f].notna().sum() >= 3]
    if not available or target not in df.columns or df[target].notna().sum() < 3:
        return None

    clean = df.dropna(subset=[target] + available)
    # Log fit needs strictly-positive target — drop rows where the
    # target is 0 or negative so np.log doesn't produce -inf/NaN.
    if log_target:
        clean = clean[clean[target] > 0]
    if len(clean) < max(3, len(available) + 1):
        return None

    try:
        X = clean[available].fillna(0).values.astype(float)
        y_raw = clean[target].fillna(0).values.astype(float)
        y = np.log(y_raw) if log_target else y_raw

        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)
        X_std[X_std == 0] = 1
        X_norm = (X - X_mean) / X_std
        y_mean = y.mean()
        y_std = y.std()
        y_std = y_std if y_std > 0 else 1
        X_aug = np.column_stack([np.ones(len(X_norm)), X_norm])

        beta = np.linalg.lstsq(X_aug, y, rcond=None)[0]
        y_hat = X_aug @ beta
        resid = y - y_hat
        ss_res = np.sum(resid ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        n = len(y)
        p = len(available)
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1) if n > p + 1 else r2

        mse = ss_res / (n - p - 1) if n > p + 1 else 0
        rmse = np.sqrt(mse)
        se = np.sqrt(np.diag(mse * np.linalg.pinv(X_aug.T @ X_aug)))
        t_stats = beta / np.where(se > 0, se, 1)

        # P-values from t-distribution (approximation via normal for large n)
        from math import erfc, sqrt
        def _pval(t, df_):
            return erfc(abs(t) / sqrt(2))

        dof = max(1, n - p - 1)

        coefficients = []
        for i, feat in enumerate(available):
            coef = beta[i + 1]
            se_i = se[i + 1] if i + 1 < len(se) else 0
            t_val = t_stats[i + 1]
            p_val = _pval(t_val, dof)
            sig = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else ("*" if p_val < 0.05 else ""))
            # Unstandardized coefficient (in original units)
            unstd_coef = coef * y_std / X_std[i] if X_std[i] > 0 else 0
            coefficients.append({
                "feature": feat,
                "coefficient": coef,
                "unstd_coefficient": unstd_coef,
                "std_error": se_i,
                "t_stat": t_val,
                "p_value": p_val,
                "significance": sig,
                "ci_low": coef - 1.96 * se_i,
                "ci_high": coef + 1.96 * se_i,
            })

        # Intercept interpretation
        intercept_raw = beta[0]
        intercept_se = se[0] if len(se) > 0 else 0

        # Correlation matrix
        corr_data = clean[available + [target]].corr()
        top_corrs = []
        for i, c1 in enumerate(corr_data.columns):
            for j, c2 in enumerate(corr_data.columns):
                if i < j:
                    top_corrs.append((c1, c2, corr_data.iloc[i, j]))
        top_corrs.sort(key=lambda x: -abs(x[2]))

        # Pairwise correlations with target
        target_corrs = []
        for feat in available:
            r = corr_data.loc[feat, target] if target in corr_data.columns and feat in corr_data.index else 0
            target_corrs.append({"feature": feat, "correlation": r})
        target_corrs.sort(key=lambda x: -abs(x["correlation"]))

        # VIF
        vifs = _compute_vif(X_norm, available)

        # F-statistic
        f_stat = ((ss_tot - ss_res) / p) / (ss_res / (n - p - 1)) if p > 0 and n > p + 1 and ss_res > 0 else 0

        # Residual analysis — top outliers
        std_resid = resid / rmse if rmse > 0 else resid
        outlier_idx = np.argsort(-np.abs(std_resid))[:20]
        outliers = []
        ccn_col = "ccn" if "ccn" in clean.columns else None
        name_col = "name" if "name" in clean.columns else None
        state_col = "state" if "state" in clean.columns else None
        segment_col = (
            "segment_label" if "segment_label" in clean.columns else None
        )
        for idx in outlier_idx:
            # Show actual/predicted in raw target units (dollars/etc)
            # even when the fit is in log space — a partner reading
            # "Stanford: actual $4.5B, predicted $3.2B, residual
            # +0.42σ" is doing the right diagnostic; reading log
            # values would be confusing.
            actual_disp = (
                float(np.exp(y[idx])) if log_target else float(y[idx])
            )
            predicted_disp = (
                float(np.exp(y_hat[idx])) if log_target else float(y_hat[idx])
            )
            row_data = {
                "index": int(idx),
                "actual": actual_disp,
                "predicted": predicted_disp,
                "residual": float(resid[idx]),
                "std_residual": float(std_resid[idx]),
            }
            if ccn_col:
                row_data["ccn"] = str(clean.iloc[idx].get("ccn", ""))
            if name_col:
                row_data["name"] = str(clean.iloc[idx].get("name", ""))[:40]
            if state_col:
                row_data["state"] = str(clean.iloc[idx].get("state", ""))
            if segment_col:
                row_data["segment"] = str(
                    clean.iloc[idx].get("segment_label", "")
                )
            outliers.append(row_data)

        # State-level R² (if state column exists)
        state_r2 = []
        if state_col and "state" in clean.columns:
            for st in sorted(clean["state"].unique()):
                st_mask = clean["state"] == st
                n_st = st_mask.sum()
                if n_st < 5:
                    continue
                y_st = y[st_mask]
                yhat_st = y_hat[st_mask]
                ss_res_st = np.sum((y_st - yhat_st) ** 2)
                ss_tot_st = np.sum((y_st - y_st.mean()) ** 2)
                r2_st = 1 - ss_res_st / ss_tot_st if ss_tot_st > 0 else 0
                mean_resid = float(np.mean(y_st - yhat_st))
                state_r2.append({
                    "state": st, "n": int(n_st),
                    "r2": round(r2_st, 3),
                    "mean_residual": round(mean_resid, 1),
                    "mean_actual": round(float(y_st.mean()), 1),
                })
            state_r2.sort(key=lambda x: -x["r2"])

        # Phase-2 helper: when fitting log(y) we want partner-facing
        # error metrics in log space (per the Phase-1 decision to
        # avoid biased exp() back-transforms). exp(rmse_log) - 1 is
        # the "typical fractional miss" — interpretable as a
        # multiplicative prediction error.
        import math as _math
        typical_fractional_error = (
            _math.exp(rmse) - 1.0 if log_target else 0.0
        )

        return {
            "r2": r2,
            "adj_r2": adj_r2,
            "n": n,
            "p": p,
            "f_stat": f_stat,
            "rmse": rmse,
            "intercept": intercept_raw,
            "intercept_se": intercept_se,
            "intercept_meaning": (
                f"When all features are at their mean values, the predicted "
                f"{'log ' if log_target else ''}"
                f"{target.replace('_', ' ')} is {intercept_raw:,.2f}"
            ),
            "coefficients": coefficients,
            "target_correlations": target_corrs,
            "top_correlations": top_corrs[:15],
            "vifs": vifs,
            "outliers": outliers,
            "state_r2": state_r2[:20],
            "target": target,
            "features": available,
            # y/y_raw split so the UI can show "Target mean = $254M"
            # (raw $) even when the fit happens in log space.
            "y_mean": float(y.mean()),
            "y_std": float(y.std()),
            "y_min": float(y.min()),
            "y_max": float(y.max()),
            "y_raw_mean": float(y_raw.mean()),
            "y_raw_min": float(y_raw.min()),
            "y_raw_max": float(y_raw.max()),
            "log_target": log_target,
            "typical_fractional_error": typical_fractional_error,
        }
    except Exception:
        return None


def _fmt_num(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"{val:,.0f}"
    return f"{val:.4f}"


def render_regression_page(
    data_source: str = "hcris",
    target: str = "net_patient_revenue",
    features: Optional[List[str]] = None,
    hcris_df: Optional[pd.DataFrame] = None,
    deals_df: Optional[pd.DataFrame] = None,
    hospital_ccn: Optional[str] = None,
    *,
    universe: str = "all",
    log_target: bool = False,
    segmented: bool = False,
    drop_leakage: bool = False,
) -> str:
    """Render the interactive regression analysis page.

    Phase 2 of the regression rebuild adds three controls:
      - ``universe`` filter (all / acquisition_targets / community /
        rural / academic_teaching / or an explicit segment label).
        Applied via ``hospital_taxonomy.filter_to_universe`` before
        the regression runs.
      - ``log_target`` toggle — fits ln(y) so the model reasons in
        percentage terms rather than raw dollars; essential for
        targets like net_patient_revenue that span six orders of
        magnitude across hospital regimes.
      - ``segmented`` toggle — also runs ``run_segmented_regression``
        from finance.regression alongside the main fit and renders
        a per-segment R² / RMSE / typical-error comparison so the
        partner can see whether one slope-set fits every regime or
        whether the regimes really do follow different equations.

    All three controls are diagnostic. Per the Phase-1 docs, the
    R² / RMSE / VIF numbers here are IN-SAMPLE explanatory fits;
    cross-validation lands in a later PR.
    """

    # ── Universe selector (Phase 2) ──
    # Apply the universe filter BEFORE the regression runs so all
    # downstream panels reflect the filtered slice.
    _UNIVERSE_OPTIONS = [
        ("all",                  "All hospitals"),
        ("acquisition_targets",  "Acquisition targets"),
        ("community",            "Community"),
        ("rural",                "Rural / CAH"),
        ("academic_teaching",    "Academic & teaching"),
    ]
    # Also add explicit segment labels as options so a partner can
    # drill into one regime
    for seg in SEGMENT_LABELS:
        _UNIVERSE_OPTIONS.append((seg, seg))

    universe_pills = ""
    for u_key, u_label in _UNIVERSE_OPTIONS:
        active = "rg-pill-active" if u_key == universe else ""
        # Preserve other query params when switching universe
        href_params = [
            f"source={_html.escape(data_source, quote=True)}",
            f"target={_html.escape(target, quote=True)}",
            f"universe={_html.escape(u_key, quote=True)}",
        ]
        if log_target:
            href_params.append("log=1")
        if segmented:
            href_params.append("segmented=1")
        if drop_leakage:
            href_params.append("drop_leakage=1")
        href = "/portfolio/regression?" + "&amp;".join(href_params)
        universe_pills += (
            f'<a href="{href}" class="rg-pill {active}">'
            f'{_html.escape(u_label)}</a>'
        )

    # Data source + target + log + segmented controls
    selector_form = (
        '<form method="GET" action="/portfolio/regression" class="rg-selector-form">'
        '<div>'
        '<label class="rg-selector-label">Data Source</label>'
        '<select name="source" class="rg-selector-input">'
        f'<option value="hcris" {"selected" if data_source == "hcris" else ""}>'
        f'HCRIS National ({len(hcris_df) if hcris_df is not None else "~6000"} hospitals)</option>'
        f'<option value="portfolio" {"selected" if data_source == "portfolio" else ""}>'
        f'Portfolio Deals ({len(deals_df) if deals_df is not None else 0} deals)</option>'
        '</select></div>'
        '<div>'
        '<label class="rg-selector-label">Target Variable</label>'
        '<select name="target" class="rg-selector-input">'
    )

    metrics = (_HCRIS_METRICS + _COMPUTED_HCRIS) if data_source == "hcris" else _AVAILABLE_METRICS
    for key, label in metrics:
        sel = "selected" if key == target else ""
        selector_form += f'<option value="{key}" {sel}>{_html.escape(label)}</option>'

    selector_form += (
        '</select></div>'
        # Preserve the universe choice across form submits
        f'<input type="hidden" name="universe" value="{_html.escape(universe, quote=True)}">'
        '<div class="rg-selector-toggles">'
        '<label class="rg-selector-checkbox">'
        f'<input type="checkbox" name="log" value="1" '
        f'{"checked" if log_target else ""}> Fit ln(target)'
        '</label>'
        '<label class="rg-selector-checkbox">'
        f'<input type="checkbox" name="segmented" value="1" '
        f'{"checked" if segmented else ""}> Segmented regression '
        '(per regime)'
        '</label>'
        '<label class="rg-selector-checkbox">'
        f'<input type="checkbox" name="drop_leakage" value="1" '
        f'{"checked" if drop_leakage else ""}> Drop leakage features '
        '(forecasting-safe only)'
        '</label>'
        '</div>'
        '<div class="rg-selector-submit">'
        '<button type="submit" class="cad-btn cad-btn-primary">Run Regression</button>'
        '</div></form>'
    )
    source_selector = ck_panel(
        '<div class="rg-pills-row">'
        '<div class="rg-pills-label">UNIVERSE</div>'
        f'<div class="rg-pills">{universe_pills}</div>'
        '</div>'
        + selector_form,
        title="Regression inputs",
    )

    # DIAGNOSTIC banner — every metric on this page is in-sample
    # explanatory fit, not an out-of-sample prediction claim. This
    # is the single most important thing for a partner to read
    # before drawing a sourcing conclusion off the numbers.
    diagnostic_banner = (
        '<div class="rg-diagnostic-banner">'
        '<span class="rg-diagnostic-tag">DIAGNOSTIC</span>'
        '<span class="rg-diagnostic-text">'
        'Every R² / RMSE / VIF / coefficient on this page is an '
        '<em>in-sample explanatory fit</em> — it describes how well '
        'the model fits the data it was trained on, not how it will '
        'predict an unseen hospital. Cross-validation lands in a '
        'later phase of the rebuild. Use these numbers for '
        'hypothesis generation and feature selection, not for '
        'sourcing decisions or LP-facing forecasts.'
        '</span></div>'
    )

    # Pick dataframe
    collinear_exclude = _COLLINEAR_PAIRS.get(target, set())
    if data_source == "portfolio" and deals_df is not None and not deals_df.empty:
        df = deals_df
        all_features = [k for k, _ in _AVAILABLE_METRICS if k != target and k not in collinear_exclude]
    elif hcris_df is not None and not hcris_df.empty:
        df = _add_computed_features(hcris_df)
        # Phase-2: tag every row with the hospital taxonomy so
        # universe filters, segmented regression, and the segment
        # column on outliers all work off a single source of truth.
        df = derive_taxonomy(df)
        base = [k for k, _ in _HCRIS_METRICS if k != target and k not in collinear_exclude]
        computed = [k for k, _ in _COMPUTED_HCRIS if k != target and k in df.columns]
        all_features = base + computed
    else:
        body = (
            f'{source_selector}'
            + ck_panel(
                '<p class="ck-section-body">'
                'No data available. '
                f'{"Import deals first." if data_source == "portfolio" else "HCRIS data not loaded."}'
                '</p>',
                title="Regression Analysis",
            )
        )
        return chartis_shell(body, "Regression Analysis", subtitle="No data available")

    # Phase-2: apply universe filter. Falls back to "all" if the
    # frame doesn't carry a segment_label (e.g. portfolio source).
    if "segment_label" in df.columns and universe != "all":
        df = filter_to_universe(df, universe)
        if df.empty:
            body = (
                f'{source_selector}'
                + ck_panel(
                    '<p class="ck-section-body">'
                    f'No rows in universe <code>{_html.escape(universe)}</code>. '
                    'Pick a different universe from the pills above.</p>',
                    title="Regression Analysis",
                )
            )
            return chartis_shell(
                body, "Regression Analysis",
                subtitle=f"Empty universe: {universe}",
            )

    if features is None:
        features = all_features

    # Phase 3: leakage audit. Run on the full candidate feature list
    # BEFORE optionally dropping leaks so the panel can show every
    # candidate with its verdict (partner gets context on what was
    # excluded and why). When ``drop_leakage`` is True, filter the
    # OLS input down to forecasting-safe features only.
    leakage_verdicts = _audit_leakage(features, target)
    if drop_leakage:
        features = _safe_features(features, target)

    result = _run_ols(df, target, features, log_target=log_target)

    if result is None:
        body = (
            f'{source_selector}'
            + ck_panel(
                '<p class="ck-section-body">'
                'Insufficient data for regression. Need at least 3 observations with '
                'non-null values for target and features.</p>',
                title="Regression Analysis",
            )
        )
        return chartis_shell(body, "Regression Analysis", subtitle="Insufficient data")

    # ── Editorial intro + KPI strip ──
    intro = ck_section_intro(
        eyebrow=f"REGRESSION · {_html.escape(target.replace('_', ' ').upper())}",
        headline=f"OLS regression on {result['n']:,} observations.",
        italic_word="regression",
        body=(
            f"R² = {result['r2']:.1%} · Adj R² = {result['adj_r2']:.1%} · "
            f"{result['p']} features · F = {min(result['f_stat'], 9999):.1f}. "
            "RMSE measures average prediction miss in target units; "
            "F-statistic tests whether the model explains more than "
            "random chance."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "R²", f"{result['r2']:.1%}",
            help={
                "definition": (
                    "Coefficient of determination — the share of "
                    "variance in the target the regression explains. "
                    "100% is perfect fit; 0% is no better than the "
                    "mean. >60% is publishable in healthcare RCM; "
                    "above 80% on cross-hospital data warrants "
                    "skepticism (possible leakage)."
                ),
            },
        )
        + ck_kpi_block(
            "Adj R²", f"{result['adj_r2']:.1%}",
            help={
                "definition": (
                    "R² penalised for the number of features in the "
                    "model. Always lower than R²; rises only when a "
                    "new feature contributes more than chance. Use "
                    "this — not raw R² — when comparing model "
                    "specifications side-by-side."
                ),
            },
        )
        + ck_kpi_block("Observations", f"{result['n']:,}")
        + ck_kpi_block("Features", f"{result['p']}")
        + ck_kpi_block(
            "F-Statistic", f"{min(result['f_stat'], 9999):.1f}",
            help={
                "definition": (
                    "Joint significance of all features taken "
                    "together vs the null model (intercept only). "
                    "Higher F means the regression as a whole is "
                    "statistically meaningful. Compare to the F "
                    "p-value below — F is the test statistic, the "
                    "p-value is the verdict."
                ),
            },
        )
        + ck_kpi_block(
            "RMSE (avg error)", _fmt_num(result["rmse"]),
            help={
                "definition": (
                    "Root-mean-square error — the standard deviation "
                    "of residuals in target units. Read as 'the "
                    "average miss the regression makes when "
                    "predicting one hospital.' RMSE around or below "
                    "the target's natural variability suggests the "
                    "model is well-calibrated."
                ),
            },
        )
        + '</div>'
    )

    # ── Intercept interpretation ──
    intercept_section = ck_panel(
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Value", _fmt_num(result["intercept"]))
        + ck_kpi_block("SE", _fmt_num(result["intercept_se"]))
        + ck_kpi_block("Target Mean", _fmt_num(result["y_mean"]))
        + ck_kpi_block(
            "Target Range",
            f'{_fmt_num(result["y_min"])} — {_fmt_num(result["y_max"])}',
        )
        + '</div>'
        f'<p class="ck-section-body">{_html.escape(result["intercept_meaning"])}</p>',
        title="Intercept Interpretation",
    )

    # ── Coefficients table ──
    max_abs = max((abs(c["coefficient"]) for c in result["coefficients"]), default=1)
    coef_rows = ""
    for c in sorted(result["coefficients"], key=lambda x: -abs(x["coefficient"])):
        cls = "cad-pos" if c["coefficient"] > 0 else "cad-neg"
        raw = c["coefficient"]
        relative = raw / max_abs if max_abs > 0 else 0
        sign = "+" if relative > 0 else ""
        bar_w = min(100, abs(relative) * 100)
        sig = c["significance"]
        sig_cls = "cad-pos" if sig else ""
        coef_rows += (
            f'<tr>'
            f'<td><strong>{_html.escape(c["feature"].replace("_", " ").title())}</strong></td>'
            f'<td class="num {cls}"><strong>{sign}{relative:.3f}</strong></td>'
            f'<td class="num">{min(abs(c["t_stat"]), 999):.1f}</td>'
            f'<td class="num">{c["p_value"]:.4f}</td>'
            f'<td class="num {sig_cls}"><strong>{sig or "ns"}</strong></td>'
            f'<td class="num">[{c["ci_low"]:.3f}, {c["ci_high"]:.3f}]</td>'
            f'<td><div class="rg-bar-track">'
            f'<div class="rg-bar-fill" style="width:{bar_w:.0f}%;background:var(--cad-{"pos" if c["coefficient"] > 0 else "neg"});"></div></div></td>'
            f'</tr>'
        )

    coef_section = ck_panel(
        '<p class="ck-section-body">'
        f'Target: <strong>{_html.escape(target.replace("_", " ").title())}</strong>. '
        'Standardized coefficients (-1.0 to +1.0): a one-SD increase in the feature produces '
        'this fraction of the strongest effect. '
        '*** p&lt;0.001, ** p&lt;0.01, * p&lt;0.05.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Variable</th><th>Strength</th><th>t</th><th>p-value</th>'
        '<th>Sig</th><th>95% CI</th><th>Impact</th>'
        f'</tr></thead><tbody>{coef_rows}</tbody></table>',
        title="Coefficients (Standardized)",
    )

    # ── Target correlations ──
    tcorr_rows = ""
    for tc in result["target_correlations"]:
        r = tc["correlation"]
        cls = "cad-pos" if r > 0 else "cad-neg"
        bar_w = min(100, abs(r) * 100)
        strength = "Strong" if abs(r) > 0.7 else ("Moderate" if abs(r) > 0.4 else "Weak")
        tcorr_rows += (
            f'<tr>'
            f'<td>{_html.escape(tc["feature"].replace("_", " ").title())}</td>'
            f'<td class="num {cls}"><strong>{r:.3f}</strong></td>'
            f'<td>{strength}</td>'
            f'<td><div class="rg-bar-track rg-bar-track-sm">'
            f'<div class="rg-bar-fill rg-bar-fill-sm" style="width:{bar_w:.0f}%;background:var(--cad-{"pos" if r > 0 else "neg"});"></div></div></td>'
            f'</tr>'
        )

    tcorr_section = ck_panel(
        '<p class="ck-section-body">'
        f'Pearson r for each feature vs {_html.escape(target.replace("_", " ").title())}. '
        'Shows raw linear relationship before controlling for other variables.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Feature</th><th>r</th><th>Strength</th><th></th>'
        f'</tr></thead><tbody>{tcorr_rows}</tbody></table>',
        title="Univariate Correlations with Target",
    ) if tcorr_rows else ""

    # ── VIF (multicollinearity) ──
    vif_rows = ""
    for v in result["vifs"][:12]:
        vif_val = v["vif"]
        vif_cls = "cad-neg" if vif_val > 10 else ("cad-warn" if vif_val > 5 else "cad-pos")
        flag = "High" if vif_val > 10 else ("Moderate" if vif_val > 5 else "OK")
        vif_rows += (
            f'<tr>'
            f'<td>{_html.escape(v["feature"].replace("_", " ").title())}</td>'
            f'<td class="num {vif_cls}"><strong>{vif_val:.1f}</strong></td>'
            f'<td class="{vif_cls}">{flag}</td>'
            f'</tr>'
        )

    vif_section = ck_panel(
        '<p class="ck-section-body">'
        'VIF &gt; 10 = severe multicollinearity (coefficient estimates unreliable). '
        'VIF &gt; 5 = moderate. Consider removing high-VIF features.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Feature</th><th>VIF</th><th>Status</th>'
        f'</tr></thead><tbody>{vif_rows}</tbody></table>',
        title="Variance Inflation Factors",
    ) if vif_rows else ""

    # ── Hospital outliers (residual analysis) ──
    # Phase-2: surface segment_label so the partner immediately
    # sees that the biggest residuals tend to be Academic / Flagship
    # Specialty — those rows aren't errors, they're a different
    # economic regime. This is the visual the Phase-1 review
    # specifically called for ("legitimate but different class",
    # not "delete").
    has_segments = bool(
        result["outliers"] and "segment" in result["outliers"][0]
    )
    outlier_rows = ""
    for o in result["outliers"][:15]:
        resid_val = o["std_residual"]
        resid_cls = "cad-neg" if abs(resid_val) > 2 else ("cad-warn" if abs(resid_val) > 1.5 else "")
        name = _html.escape(o.get("name", "")[:35])
        ccn = o.get("ccn", "")
        state = o.get("state", "")
        link = f'<a href="/hospital/{_html.escape(ccn)}" class="ck-link">{name}</a>' if ccn else name
        seg_cell = (
            f'<td><span class="rg-segment-chip">'
            f'{_html.escape(o.get("segment", ""))}</span></td>'
            if has_segments else ""
        )
        outlier_rows += (
            f'<tr>'
            f'<td>{link}</td>'
            f'{seg_cell}'
            f'<td>{_html.escape(state)}</td>'
            f'<td class="num">{_fmt_num(o["actual"])}</td>'
            f'<td class="num">{_fmt_num(o["predicted"])}</td>'
            f'<td class="num {resid_cls}"><strong>{resid_val:+.2f}σ</strong></td>'
            f'</tr>'
        )

    seg_header = '<th>Segment</th>' if has_segments else ''
    # Make the residual-space-vs-display-space contract explicit
    # when log mode is on: residuals (and the σ ranking) are
    # computed in log space because that's what the model fits;
    # the Actual / Predicted columns are back-transformed to raw
    # target units so the partner reads dollars / etc. instead of
    # log values.
    log_note = (
        ' <strong>Log mode:</strong> the residual σ ranking is '
        'computed in <em>log space</em> (where the model fits); '
        'Actual and Predicted are back-transformed to raw '
        f'<em>{_html.escape(target.replace("_", " "))}</em> units '
        'so the rows read in their natural scale.'
        if log_target else ''
    )
    outlier_section = ck_panel(
        '<p class="ck-section-body">'
        'Hospitals with the largest standardized residuals. &gt;2σ = model underpredicts/overpredicts. '
        + (
            'The <strong>Segment</strong> column shows the hospital\'s '
            'economic regime — large positive residuals concentrated in '
            'one segment (e.g. Academic) usually mean that segment '
            'follows a different revenue equation than the baseline, '
            'not that the rows are errors. Try toggling '
            '<em>Segmented regression</em> to fit a separate model per '
            f'regime.{log_note}</p>'
            if has_segments else
            f'Investigate for deal opportunities or data quality issues.{log_note}</p>'
        )
        + '<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th>{seg_header}<th>State</th>'
        '<th>Actual</th><th>Predicted</th><th>Residual</th>'
        f'</tr></thead><tbody>{outlier_rows}</tbody></table>',
        title="Hospital Outliers (Residual Analysis)",
    ) if outlier_rows else ""

    # ── Segmented comparison panel (Phase 2) ──
    # ── Feature Leakage Audit panel (Phase 3) ──
    # Built unconditionally so a partner can see WHICH of their
    # features algebraically leak the target before they decide to
    # drop them. When drop_leakage is on, the panel reflects that
    # the leaky rows have been excluded from the fit (separate
    # "Dropped from fit" section). Same registry-driven verdicts
    # the tests pin in test_leakage_audit.py.
    _LEAK_BADGE_CLASS = {
        "LEAKS":   "rg-leak-critical",
        "SELF":    "rg-leak-critical",
        "SAFE":    "rg-leak-ok",
        "UNKNOWN": "rg-leak-info",
    }
    leak_rows = []
    # Order: critical first (LEAKS / SELF), then info (UNKNOWN),
    # then warnings, then ok — partners read top-down for risks
    severity_order = {"critical": 0, "info": 1, "warning": 2, "ok": 3}
    for v in sorted(leakage_verdicts,
                    key=lambda x: (severity_order.get(x.severity, 99),
                                   x.feature)):
        badge_cls = _LEAK_BADGE_CLASS.get(v.verdict, "rg-leak-info")
        # Show whether this feature actually ended up in the fit
        # (drop_leakage on → leaky features were excluded)
        in_fit = v.feature in result["features"]
        in_fit_mark = (
            '<span class="cad-pos">in fit</span>' if in_fit
            else '<span class="cad-text2">dropped</span>'
        )
        leak_rows.append(
            f'<tr>'
            f'<td><strong>{_html.escape(v.feature.replace("_", " ").title())}</strong></td>'
            f'<td><span class="rg-leak-badge {badge_cls}">'
            f'{_html.escape(v.verdict)}</span></td>'
            f'<td style="font-size:12px;color:var(--cad-text2);">'
            f'{_html.escape(v.reason)}</td>'
            f'<td>{in_fit_mark}</td>'
            f'</tr>'
        )

    # Count critical leaks for the panel header
    leak_count = sum(
        1 for v in leakage_verdicts if v.severity == "critical"
    )
    leak_header_note = (
        f' · <strong class="cad-warn">{leak_count} leaky</strong>'
        if leak_count else ''
    )
    drop_state_note = (
        ' · <span class="cad-pos"><strong>drop_leakage ON</strong></span> '
        '— leaky features excluded from this fit'
        if drop_leakage else
        ' · <em>drop_leakage off — leaky features are STILL in the fit '
        'and inflating R². Toggle "Drop leakage features" above.</em>'
        if leak_count else ''
    )
    leakage_section = ck_panel(
        '<p class="ck-section-body">'
        f'Per-feature leakage classification for target = '
        f'<strong>{_html.escape(target.replace("_", " ").title())}</strong>'
        f'{leak_header_note}{drop_state_note}. '
        '<strong>LEAKS</strong> = feature is mathematically derived '
        'from the target (or vice-versa) per its registered formula '
        '— fitting target ~ this feature inflates R² without '
        'predicting anything. <strong>SAFE</strong> = no algebraic '
        'path. <strong>SELF</strong> = feature IS the target. '
        '<strong>UNKNOWN</strong> = no provenance record (caller '
        'decides; defaults to staying in the fit).</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Feature</th><th>Verdict</th>'
        '<th>Reason</th><th>Status</th>'
        f'</tr></thead><tbody>{"".join(leak_rows)}</tbody></table>',
        title="Feature Leakage Audit",
    )

    # ── Segmented comparison panel (Phase 2) ──
    # Only built when the partner explicitly toggles "Segmented
    # regression". Calls the Phase-1 run_segmented_regression on the
    # same (universe-filtered) frame and renders per-regime R² /
    # RMSE / typical-error alongside the all-segments baseline.
    segmented_section = ""
    if segmented and "segment_label" in df.columns:
        try:
            seg_res = _run_segmented(
                df, target, result["features"],
                segment_column="segment_label",
                log_transform_target=log_target,
                min_segment_rows=30,
                dof_safety_margin=10,
            )
        except Exception as exc:
            segmented_section = ck_panel(
                f'<p class="ck-section-body cad-warn">'
                f'Segmented regression failed: {_html.escape(str(exc))}'
                f'</p>',
                title="Segmented Regression (per regime)",
            )
            seg_res = None

        if seg_res is not None:
            # Header row = pooled baseline on the CURRENTLY SELECTED
            # universe (not the global "all hospitals" baseline). If
            # the partner has filtered to e.g. acquisition_targets,
            # this row is the pooled OLS fit on that subset. Labeling
            # it ambiguously would let a reader think the comparison
            # is segment-vs-global, when in fact it's segment-vs-
            # this-universe.
            universe_disp = (
                "all hospitals" if universe == "all"
                else f"universe = {universe}"
            )
            seg_rows = (
                '<tr class="rg-seg-baseline">'
                f'<td><strong>baseline (pooled · {_html.escape(universe_disp)})</strong></td>'
                f'<td class="num">{seg_res.baseline.n_observations:,}</td>'
                f'<td class="num"><strong>{seg_res.baseline.r_squared:.1%}</strong></td>'
                f'<td class="num">{seg_res.baseline.rmse:.3f}</td>'
                f'<td class="num">'
                + (
                    f'{seg_res.baseline.typical_fractional_error * 100:.0f}%'
                    if seg_res.baseline.target_was_log_transformed else '—'
                )
                + '</td>'
                f'<td>—</td>'
                '</tr>'
            )
            # Per-segment rows, sorted by R² descending
            sorted_segs = sorted(
                seg_res.by_segment.items(),
                key=lambda kv: -kv[1].r_squared,
            )
            for seg_name, sr in sorted_segs:
                delta = sr.r_squared - seg_res.baseline.r_squared
                if delta > 0.02:
                    arrow_html = (
                        '<span class="cad-pos"><strong>'
                        f'+{delta * 100:.1f}pp ↑</strong></span>'
                    )
                elif delta < -0.02:
                    arrow_html = (
                        '<span class="cad-neg"><strong>'
                        f'{delta * 100:.1f}pp ↓</strong></span>'
                    )
                else:
                    arrow_html = (
                        f'<span class="cad-text2">'
                        f'{delta * 100:+.1f}pp</span>'
                    )
                seg_rows += (
                    '<tr>'
                    f'<td><span class="rg-segment-chip">'
                    f'{_html.escape(seg_name)}</span></td>'
                    f'<td class="num">{sr.n_observations:,}</td>'
                    f'<td class="num"><strong>{sr.r_squared:.1%}</strong></td>'
                    f'<td class="num">{sr.rmse:.3f}</td>'
                    f'<td class="num">'
                    + (
                        f'{sr.typical_fractional_error * 100:.0f}%'
                        if sr.target_was_log_transformed else '—'
                    )
                    + '</td>'
                    f'<td>{arrow_html}</td>'
                    '</tr>'
                )

            # Insufficient-n surface: segments we explicitly chose NOT
            # to fit, with the reason. Honest reporting beats silent
            # drops — per the Phase-1 review.
            insuf_html = ""
            if seg_res.insufficient_n:
                insuf_rows = ""
                for seg_name, info in seg_res.insufficient_n.items():
                    insuf_rows += (
                        '<tr>'
                        f'<td><span class="rg-segment-chip">'
                        f'{_html.escape(seg_name)}</span></td>'
                        f'<td class="num">{info["n_clean"]}</td>'
                        f'<td class="num">{info["min_required"]}</td>'
                        f'<td class="cad-text2" style="font-size:12px;">'
                        f'{_html.escape(info["reason"])}</td>'
                        '</tr>'
                    )
                insuf_html = (
                    '<h4 class="rg-subhead">Segments not fit '
                    '(insufficient n)</h4>'
                    '<table class="cad-table"><thead><tr>'
                    '<th>Segment</th><th>n</th><th>Required</th>'
                    f'<th>Reason</th></tr></thead><tbody>{insuf_rows}'
                    '</tbody></table>'
                )

            target_disp = target.replace("_", " ").title()
            log_note = (
                ' (target is <em>log</em>-transformed; typical '
                'error = exp(RMSE_log) - 1)'
                if log_target else
                f' (RMSE in {target_disp} units; '
                'typical error column blank for raw-target fits)'
            )
            segmented_section = ck_panel(
                '<p class="ck-section-body">'
                'One OLS fit per hospital regime, plus the all-segments '
                'baseline at the top for comparison. <strong>R² delta '
                '↑</strong> means the segment beats the baseline — '
                'evidence that this regime really does follow a '
                'different equation than the others. <strong>↓</strong> '
                'usually means the segment\'s variance isn\'t captured '
                f'by the current feature set, not that it\'s inherently '
                f'unmodellable.{log_note}</p>'
                '<table class="cad-table"><thead><tr>'
                '<th>Segment</th><th>n</th><th>R²</th>'
                '<th>RMSE</th><th>typ. err</th><th>vs baseline</th>'
                f'</tr></thead><tbody>{seg_rows}</tbody></table>'
                f'{insuf_html}',
                title="Segmented Regression (per regime)",
            )

    # ── State-level R² ──
    state_rows = ""
    for sr in result["state_r2"][:15]:
        r2_st = sr["r2"]
        r2_cls = "cad-pos" if r2_st > 0.5 else ("cad-warn" if r2_st > 0.2 else "cad-neg")
        mean_resid = sr["mean_residual"]
        resid_cls = "cad-pos" if abs(mean_resid) < sr["mean_actual"] * 0.05 else "cad-warn"
        state_rows += (
            f'<tr>'
            f'<td><a href="/market-data/state/{_html.escape(sr["state"])}" class="ck-link">{_html.escape(sr["state"])}</a></td>'
            f'<td class="num">{sr["n"]}</td>'
            f'<td class="num {r2_cls}"><strong>{r2_st:.1%}</strong></td>'
            f'<td class="num {resid_cls}">{_fmt_num(mean_resid)}</td>'
            f'</tr>'
        )

    state_section = ck_panel(
        '<p class="ck-section-body">'
        'How well the national model predicts within each state. Low R² states have unique '
        'market dynamics not captured by national features — consider state-specific models.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>State</th><th>n</th><th>R²</th><th>Mean Residual</th>'
        f'</tr></thead><tbody>{state_rows}</tbody></table>',
        title="Model Fit by State",
    ) if state_rows else ""

    # ── Top pairwise correlations ──
    corr_rows = ""
    for c1, c2, val in result["top_correlations"]:
        cls = "cad-pos" if val > 0 else "cad-neg"
        corr_rows += (
            f'<tr>'
            f'<td>{_html.escape(c1.replace("_", " ").title())}</td>'
            f'<td>{_html.escape(c2.replace("_", " ").title())}</td>'
            f'<td class="num {cls}"><strong>{val:.3f}</strong></td>'
            f'</tr>'
        )
    corr_section = ""
    if corr_rows:
        corr_section = ck_panel(
            '<table class="cad-table"><thead><tr>'
            '<th>Variable 1</th><th>Variable 2</th><th>r</th>'
            f'</tr></thead><tbody>{corr_rows}</tbody></table>',
            title="Top Pairwise Correlations",
        )

    # ── Navigation ──
    nav_section = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/market-data/map" class="cad-btn">Market Heatmap</a> '
        '<a href="/analysis" class="cad-btn">Analysis Hub</a> '
        f'<a href="/api/portfolio/regression?target={target}" class="cad-btn">Regression JSON API</a> '
        '<a href="/portfolio/regression?source=hcris&target=operating_margin" class="cad-btn">Operating Margin</a> '
        '<a href="/portfolio/regression?source=hcris&target=revenue_per_bed" class="cad-btn">Revenue/Bed</a> '
        '<a href="/portfolio/regression?source=hcris&target=occupancy_rate" class="cad-btn">Occupancy</a> '
        '<a href="/portfolio/regression?source=hcris&target=net_to_gross_ratio" class="cad-btn">Net-to-Gross</a>'
        '</p>',
        title="Cross-links",
    )

    # ── Layout: 2-column for some sections ──
    left_col = f'{coef_section}{tcorr_section}{outlier_section}'
    right_col = f'{vif_section}{state_section}{corr_section}'

    rg_styles = """
<style>
.rg-selector-form{display:flex;gap:12px;align-items:center;flex-wrap:wrap;}
.rg-selector-label{font-size:12px;color:var(--cad-text2);
display:block;margin-bottom:4px;}
.rg-selector-input{padding:7px 12px;border:1px solid var(--cad-border);
border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;
transition:border-color 120ms ease, box-shadow 120ms ease;}
.rg-selector-input:focus{outline:none;border-color:var(--cad-link);
box-shadow:0 0 0 2px rgba(21,87,82,0.18);}
.rg-selector-submit{align-self:flex-end;}
.rg-selector-toggles{display:flex;flex-direction:column;gap:4px;
align-self:flex-end;padding-bottom:2px;}
.rg-selector-checkbox{font-size:12px;color:var(--cad-text);
display:flex;align-items:center;gap:6px;cursor:pointer;}
.rg-pills-row{display:flex;align-items:baseline;gap:14px;margin:0 0 14px;
flex-wrap:wrap;}
.rg-pills-label{font-family:var(--sc-mono,monospace);font-size:10px;
font-weight:600;letter-spacing:0.16em;text-transform:uppercase;
color:var(--sc-text-faint,#7a8699);}
.rg-pills{display:flex;flex-wrap:wrap;gap:6px;}
.rg-pill{display:inline-block;padding:5px 12px;font-family:var(--sc-sans,Inter);
font-size:11.5px;font-weight:500;border:1px solid var(--sc-rule,#d6cfc0);
background:#fff;color:var(--sc-navy,#0b2341);text-decoration:none;
border-radius:14px;transition:border-color 120ms ease,background 120ms ease;}
.rg-pill:hover{border-color:var(--sc-teal-ink,#155752);}
.rg-pill-active{background:var(--sc-navy,#0b2341);color:#fff;
border-color:var(--sc-navy,#0b2341);}
.rg-diagnostic-banner{display:flex;align-items:baseline;gap:12px;
padding:12px 16px;margin:0 0 16px;background:#fff;
border:1px solid var(--sc-rule,#d6cfc0);
border-left:3px solid var(--sc-teal-ink,#155752);}
.rg-diagnostic-tag{font-family:var(--sc-mono,monospace);font-size:10px;
font-weight:700;letter-spacing:0.14em;color:var(--sc-teal-ink,#155752);
flex-shrink:0;}
.rg-diagnostic-text{font-size:13px;color:var(--sc-text,#1a2332);
line-height:1.5;}
.rg-diagnostic-text em{color:var(--sc-teal-ink,#155752);font-style:italic;}
.rg-segment-chip{display:inline-block;padding:2px 8px;font-family:var(--sc-mono,monospace);
font-size:10px;font-weight:600;letter-spacing:0.04em;color:var(--sc-teal-ink,#155752);
background:var(--sc-parchment,#f2ede3);border:1px solid var(--sc-rule,#d6cfc0);
border-radius:2px;}
.rg-seg-baseline{background:var(--sc-parchment,#f2ede3);}
.rg-seg-baseline td{border-top:2px solid var(--sc-rule,#d6cfc0);}
.rg-leak-badge{display:inline-block;padding:2px 8px;
font-family:var(--sc-mono,monospace);font-size:10px;font-weight:700;
letter-spacing:0.08em;border-radius:2px;border:1px solid transparent;}
.rg-leak-critical{color:#b5321e;background:#fff;
border-color:#b5321e;}
.rg-leak-ok{color:#0a8a5f;background:#fff;border-color:#0a8a5f;}
.rg-leak-info{color:var(--sc-text-faint,#7a8699);background:#fff;
border-color:var(--sc-rule,#d6cfc0);}
.rg-subhead{font-family:var(--sc-sans,Inter);font-size:13px;font-weight:600;
letter-spacing:0.03em;color:var(--sc-navy,#0b2341);margin:18px 0 8px;}
.rg-bar-track{background:var(--cad-bg3);border-radius:4px;height:10px;}
.rg-bar-track-sm{height:8px;width:120px;}
.rg-bar-fill{border-radius:4px;height:10px;}
.rg-bar-fill-sm{height:8px;border-radius:4px;}
.rg-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
</style>
"""
    next_up = ck_next_section(
        "Open the portfolio for context",
        "/portfolio",
        eyebrow="Continue —",
        italic_word="portfolio",
    )
    body = (
        f'{rg_styles}{intro}{diagnostic_banner}{source_selector}'
        f'{leakage_section}{segmented_section}{kpis}{intercept_section}'
        '<div class="rg-grid">'
        f'<div>{left_col}</div><div>{right_col}</div></div>'
        f'{nav_section}{next_up}'
    )

    sig_count = sum(1 for c in result["coefficients"] if c["significance"])
    # Subtitle reflects universe + log + segmented state so partners
    # can tell at a glance what filter is applied
    subtitle_bits = [
        f"OLS: {_html.escape(target.replace('_', ' ').title())}"
        f"{' (log)' if log_target else ''} ~ {result['p']} features",
        f"R\u00b2 = {result['r2']:.1%}",
        f"n = {result['n']:,}",
    ]
    if universe != "all":
        subtitle_bits.insert(0, f"universe = {universe}")
    if segmented:
        subtitle_bits.append("+segmented")
    if drop_leakage:
        subtitle_bits.append("+leakage-filtered")
    subtitle_bits.append(f"{sig_count} significant")
    return chartis_shell(
        body, "Regression Analysis",
        active_nav="/portfolio/regression",
        subtitle=" | ".join(subtitle_bits),
    )
