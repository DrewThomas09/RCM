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
from ..finance.regression import breusch_pagan_test as _breusch_pagan
from ..finance.regression import hc1_robust_se as _hc1_robust_se
from ..finance.leakage import (
    audit_features as _audit_leakage,
    forecasting_safe_features as _safe_features,
)
from ..finance.cross_validation import run_cv_regression as _run_cv
from ..finance.influence import (
    classify_influence_point as _classify_influence,
    compute_influence as _compute_influence,
)
from ..finance.clustering import (
    cluster_hospitals as _cluster_hospitals,
    render_cluster_scatter as _render_cluster_scatter,
)
from ..finance.buyability import (
    score_buyability_batch as _score_buyability_batch,
    summarize_distribution as _buyability_distribution,
    target_attractiveness as _attractiveness,
    attractiveness_tier as _attractiveness_tier,
)


_REG_CHART_CAPTION_CSS = (
    ".rg-figcap{font-size:11px;color:#6b6456;margin:8px 0 4px;"
    "font-family:'JetBrains Mono',ui-monospace,monospace;"
    "letter-spacing:0.02em;}"
)


def _coefficient_forest_chart(
    coefficients: List[Dict[str, Any]], width: int = 720, row_h: int = 26
) -> str:
    """Diverging coefficient plot with 95% CI whiskers.

    Each feature's standardized coefficient (scaled to the strongest
    effect, matching the table's "Strength" column) is a bar diverging
    from a zero baseline — green right, red left — with a thin whisker
    spanning the 95% CI. Non-significant features fade so the eye lands
    on the load-bearing drivers first. Reads the same coefficients the
    retained table shows; empty input returns "".
    """
    rows = [c for c in (coefficients or []) if c.get("feature")]
    if not rows:
        return ""
    max_abs = max((abs(c.get("coefficient", 0)) for c in rows), default=0)
    if max_abs <= 0:
        max_abs = 1.0
    rows = sorted(rows, key=lambda c: -abs(c.get("coefficient", 0)))[:14]

    pad_l, pad_r, pad_t = 180, 52, 14
    half = (width - pad_l - pad_r) / 2.0
    mid_x = pad_l + half
    height = pad_t + row_h * len(rows) + 22

    pos = PALETTE["positive"]
    neg = PALETTE["negative"]
    rule = PALETTE.get("border", "#BFB6A2")
    txt = PALETTE.get("text_secondary", "#4a5568")
    mut = PALETTE.get("text_muted", "#8a8270")

    def _x(rel: float) -> float:
        return mid_x + max(-1.0, min(1.0, rel)) * half

    parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Standardized regression coefficients with 95% CI" '
        f'style="width:100%;max-width:{width}px;height:auto;'
        f'print-color-adjust:exact;-webkit-print-color-adjust:exact;">'
    ]
    parts.append(
        f'<line x1="{mid_x:.1f}" y1="{pad_t - 4}" x2="{mid_x:.1f}" '
        f'y2="{height - 18}" stroke="{rule}" stroke-width="1"/>'
    )
    for i, c in enumerate(rows):
        name = _html.escape(
            str(c.get("feature", "")).replace("_", " ").title()[:28])
        coef = c.get("coefficient", 0)
        rel = coef / max_abs
        sig = bool(c.get("significance"))
        color = pos if coef > 0 else neg
        op = 0.88 if sig else 0.4
        y = pad_t + i * row_h
        cy = y + row_h / 2
        x_coef = _x(rel)
        x_lo = _x(c.get("ci_low", coef) / max_abs)
        x_hi = _x(c.get("ci_high", coef) / max_abs)
        parts.append(
            f'<text x="{pad_l - 10}" y="{cy + 3:.1f}" text-anchor="end" '
            f'font-size="11" font-family="Inter Tight,system-ui,sans-serif" '
            f'fill="{txt}">{name}</text>'
        )
        # Bar from zero to coefficient.
        bx = min(mid_x, x_coef)
        bw = abs(x_coef - mid_x)
        sig_txt = c.get("significance") or "ns"
        tip = _html.escape(
            f"{str(c.get('feature', '')).replace('_', ' ').title()}: "
            f"β={coef:+.3f} (rel {rel:+.2f}) · 95% CI "
            f"[{c.get('ci_low', coef):.3f}, {c.get('ci_high', coef):.3f}] · {sig_txt}"
        )
        parts.append(
            f'<rect x="{bx:.1f}" y="{y + 5:.1f}" width="{max(bw, 0.5):.1f}" '
            f'height="{row_h - 12}" rx="2" fill="{color}" opacity="{op:.2f}">'
            f'<title>{tip}</title></rect>'
        )
        # 95% CI whisker.
        parts.append(
            f'<line x1="{x_lo:.1f}" y1="{cy:.1f}" x2="{x_hi:.1f}" '
            f'y2="{cy:.1f}" stroke="{txt}" stroke-width="1" opacity="0.6"/>'
            f'<line x1="{x_lo:.1f}" y1="{cy - 3:.1f}" x2="{x_lo:.1f}" '
            f'y2="{cy + 3:.1f}" stroke="{txt}" stroke-width="1" opacity="0.6"/>'
            f'<line x1="{x_hi:.1f}" y1="{cy - 3:.1f}" x2="{x_hi:.1f}" '
            f'y2="{cy + 3:.1f}" stroke="{txt}" stroke-width="1" opacity="0.6"/>'
        )
        lbl_x = (x_coef + 6) if coef >= 0 else (x_coef - 6)
        anchor = "start" if coef >= 0 else "end"
        parts.append(
            f'<text x="{lbl_x:.1f}" y="{cy + 3:.1f}" text-anchor="{anchor}" '
            f'font-size="10" font-family="JetBrains Mono,ui-monospace,monospace" '
            f'fill="{color if sig else mut}">{"+" if rel > 0 else ""}{rel:.2f}</text>'
        )
    parts.append(
        f'<text x="{mid_x:.1f}" y="{height - 4}" text-anchor="middle" '
        f'font-size="9.5" letter-spacing="0.06em" '
        f'font-family="JetBrains Mono,ui-monospace,monospace" '
        f'fill="{mut}">&#9664; NEGATIVE&#160;&#160;|&#160;&#160;POSITIVE &#9654; '
        f'&#183; faded = not significant</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _vif_bar_chart(vifs: List[Dict[str, Any]]) -> str:
    """Horizontal VIF bars with the VIF=5 (caution) and VIF=10 (severe)
    thresholds drawn in, so an over-collinear feature is visually obvious
    instead of buried in a column of numbers. Bars are colour-zoned: green
    below 5, amber 5–10, red above 10 (where coefficients are unreliable)."""
    rows = list(vifs or [])[:12]
    if not rows:
        return ""
    pos = PALETTE["positive"]; warn = PALETTE["warning"]; neg = PALETTE["negative"]
    txt = "var(--sc-text-dim,#465366)"
    scale = 20.0  # full bar width == VIF 20; higher clamps and shows ">"
    t5 = 5 / scale * 100.0
    t10 = 10 / scale * 100.0
    out = ['<div style="margin:4px 0 2px;">']
    for v in rows:
        vif = float(v["vif"])
        color = neg if vif > 10 else (warn if vif > 5 else pos)
        w = min(vif, scale) / scale * 100.0
        val = "&infin;" if vif >= 999 else (f"{vif:.0f}" if vif >= 10 else f"{vif:.1f}")
        over = "&nbsp;&gt;" if vif > scale else ""
        name = _html.escape(str(v["feature"]).replace("_", " ").title())
        out.append(
            f'<div style="display:grid;grid-template-columns:150px 1fr 50px;'
            f'align-items:center;gap:10px;margin:5px 0;font-size:12px;">'
            f'<span style="color:{txt};text-align:right;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;">{name}</span>'
            f'<div style="position:relative;height:16px;background:#ece6d6;'
            f'border-radius:2px;">'
            f'<span style="position:absolute;left:{t5:.0f}%;top:-2px;bottom:-2px;'
            f'width:1px;background:{warn};opacity:.65;"></span>'
            f'<span style="position:absolute;left:{t10:.0f}%;top:-2px;bottom:-2px;'
            f'width:1px;background:{neg};opacity:.65;"></span>'
            f'<div style="height:100%;width:{w:.0f}%;background:{color};'
            f'border-radius:2px;"></div></div>'
            f'<span style="font-family:var(--sc-mono,monospace);color:{color};'
            f'font-weight:700;text-align:right;">{val}{over}</span></div>')
    out.append(
        f'<div style="font-size:10.5px;color:{txt};margin-top:8px;'
        f'font-family:var(--sc-mono,monospace);">'
        f'<span style="color:{pos};">&#9632;</span> &lt;5 ok&nbsp;&nbsp;'
        f'<span style="color:{warn};">&#9632;</span> 5&ndash;10 caution&nbsp;&nbsp;'
        f'<span style="color:{neg};">&#9632;</span> &gt;10 unreliable'
        f' &middot; thin lines mark the 5 &amp; 10 thresholds</div></div>')
    return "".join(out)


def _univariate_corr_chart(corrs: List[Dict[str, Any]]) -> str:
    """Diverging bar chart of each feature's raw correlation with the target —
    positive right (green), negative left (red), from a centre zero line. Read
    alongside the model: a feature can correlate strongly here yet be dropped
    as a redundant transform, which is exactly the univariate-vs-multivariate
    distinction the coefficients answer."""
    rows = sorted(list(corrs or []), key=lambda c: -abs(c.get("correlation", 0)))[:14]
    if not rows:
        return ""
    pos = PALETTE["positive"]; neg = PALETTE["negative"]
    txt = "var(--sc-text-dim,#465366)"
    out = ['<div style="margin:4px 0 2px;">']
    for c in rows:
        r = float(c.get("correlation", 0))
        color = pos if r >= 0 else neg
        half = min(abs(r), 1.0) * 50.0
        left = 50.0 - half if r < 0 else 50.0
        name = _html.escape(str(c["feature"]).replace("_", " ").title())
        out.append(
            f'<div style="display:grid;grid-template-columns:150px 1fr 46px;'
            f'align-items:center;gap:10px;margin:4px 0;font-size:12px;">'
            f'<span style="color:{txt};text-align:right;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;">{name}</span>'
            f'<div style="position:relative;height:14px;background:#ece6d6;'
            f'border-radius:2px;">'
            f'<span style="position:absolute;left:50%;top:0;bottom:0;width:1px;'
            f'background:#b7ae98;"></span>'
            f'<div style="position:absolute;left:{left:.1f}%;width:{half:.1f}%;'
            f'top:0;bottom:0;background:{color};border-radius:2px;"></div></div>'
            f'<span style="font-family:var(--sc-mono,monospace);color:{color};'
            f'text-align:right;">{r:+.2f}</span></div>')
    out.append('</div>')
    return "".join(out)


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

# Curated low-collinearity predictor sets per target — the "strong but
# clean" defaults. Rather than throw every leakage-safe column at OLS
# (which leaves VIFs in the hundreds: beds ≈ bed_days ≈ patient_days ≈
# medicare_days, and medicare%+medicaid%+commercial% sum to 100), the
# default fit uses ONE volume measure + occupancy + payer mix + size.
# Verified on live HCRIS: net_patient_revenue ~ this set (log target)
# gives R²≈0.71, 7/7 coefficients significant, max VIF ≈ 5.5, signs all
# directionally sensible. Callers can still override `features` to fit a
# different / wider set. Keyed by target; absent target → all-safe.
_CURATED_DEFAULTS: Dict[str, List[str]] = {
    "net_patient_revenue": [
        "total_patient_days", "occupancy_rate", "medicare_day_pct",
        "medicaid_day_pct", "payer_diversity", "size_quartile",
        "operating_expenses",
    ],
}


# Features that are transforms / proxies of ONE underlying quantity. Linear
# VIF cannot always catch these: payer_diversity = 1-(mc²+md²+comm²) and
# medicare_intensity = mc·beds are NONLINEAR functions of the payer shares, so
# their VIF stays low even though they carry no independent information. Left
# in, they invite p-hacking — a dozen "significant" coefficients that are
# really one driver wearing several hats. Before VIF pruning we collapse each
# family to its most target-correlated member(s) so the model keeps exactly one
# clean representative per real dimension. (members, max_keep).
_FEATURE_FAMILIES: List[Tuple[set, int]] = [
    # Size / volume — beds, days, per-bed ratios, and the size quartile all
    # move together; keep the single most predictive size proxy.
    ({"beds", "bed_days_available", "total_patient_days", "size_quartile",
      "revenue_per_bed", "expense_per_bed", "medicare_days", "medicaid_days"}, 1),
    # Dollar scale — every P&L line scales with the others; keep one.
    ({"net_patient_revenue", "gross_patient_revenue", "operating_expenses",
      "net_income", "contractual_allowances", "total_patient_revenue"}, 1),
    # Payer mix — the three day-shares sum to 1 (only 2 are independent), and
    # payer_diversity / medicare_intensity are derived from them. Keep 2.
    ({"medicare_day_pct", "medicaid_day_pct", "commercial_pct",
      "payer_diversity", "medicare_intensity"}, 2),
]

# Engineered / derived features — ratios, interactions, quartiles, and the
# linearly-dependent third payer share. When a family must pick a
# representative we prefer a RAW, directly-interpretable measure over one of
# these (so the headline model reads "medicare %, medicaid %" rather than
# "medicare intensity, payer diversity"), unless no raw member is present.
_ENGINEERED_FEATURES = {
    "size_quartile", "revenue_per_bed", "expense_per_bed", "revenue_per_day",
    "commercial_pct", "payer_diversity", "medicare_intensity",
    "net_to_gross_ratio",
}


def _abs_target_corr(df: pd.DataFrame, feature: str, target: str) -> float:
    """|Pearson r| of one feature with the target, 0 if undefined."""
    try:
        sub = df[[feature, target]].dropna()
        if len(sub) < 3 or sub[feature].std() == 0 or sub[target].std() == 0:
            return 0.0
        return abs(float(np.corrcoef(sub[feature], sub[target])[0, 1]))
    except Exception:
        return 0.0


def _dedupe_feature_families(
    df: pd.DataFrame, target: str, features: List[str],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Collapse each structural family to its most target-correlated member(s).

    Returns ``(kept, dropped)`` where each dropped entry is
    ``{"feature", "reason": "redundant", "explained_by": [{"feature","r"}],
    "univariate_r"}`` so the UI can say *why* a feature that looks individually
    predictive was excluded — it is a transform of one already in the model,
    not independent signal. This runs BEFORE VIF pruning; VIF then cleans up
    any residual linear collinearity among the survivors.
    """
    kept = list(features)
    dropped: List[Dict[str, Any]] = []
    for members, max_keep in _FEATURE_FAMILIES:
        present = [f for f in kept if f in members]
        if len(present) <= max_keep:
            continue
        # Prefer raw measures over engineered transforms, then by how strongly
        # each correlates with the target.
        ranked = sorted(
            present,
            key=lambda f: (f not in _ENGINEERED_FEATURES,
                           _abs_target_corr(df, f, target)),
            reverse=True)
        keepers = ranked[:max_keep]
        for f in ranked[max_keep:]:
            kept.remove(f)
            dropped.append({
                "feature": f,
                "reason": "redundant",
                "univariate_r": round(_abs_target_corr(df, f, target), 3),
                "explained_by": [
                    {"feature": k,
                     "r": round(_abs_target_corr(df, k, target), 3)}
                    for k in keepers],
            })
    return kept, dropped


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
    # Drop features that DON'T VARY within this subset. A constant column can't
    # be measured or regressed here — it would otherwise sit on the charts as a
    # meaningless zero bar (the "things left at 0 because it doesn't measure
    # certain things" a universe filter like acquisition_targets exposes). They
    # simply drop out of the model + every chart instead.
    if len(clean) >= 3:
        available = [f for f in available
                     if float(clean[f].std(skipna=True) or 0.0) > 0.0]
    if not available:
        return None
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
        # Clamp the variance diagonal at 0 before sqrt: collinear HCRIS
        # features make XᵀX near-singular, so pinv's diagonal carries tiny
        # negative round-off that would sqrt to NaN (leaking 'nan' SEs into
        # the page). max(.,0) keeps every SE a real, non-negative number.
        var_diag = np.clip(np.diag(mse * np.linalg.pinv(X_aug.T @ X_aug)), 0.0, None)
        classical_se = np.sqrt(var_diag)
        # Inference uses HETEROSKEDASTICITY-ROBUST (HC1) standard errors —
        # cross-sectional hospital data is almost never homoskedastic (a $9B AMC
        # and a $400K rural CAH don't share an error scale), so classical SEs
        # overstate precision. The Breusch–Pagan test reports whether that
        # assumption is actually violated. Robust SEs fall back to classical if
        # the sandwich can't be formed.
        try:
            se = _hc1_robust_se(X_aug, resid)
            if se.shape != classical_se.shape or not np.all(np.isfinite(se)):
                se = classical_se
        except Exception:  # noqa: BLE001
            se = classical_se
        bp_test = _breusch_pagan(X_aug, resid)
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

        # F-statistic + its upper-tail p-value (joint significance).
        f_stat = ((ss_tot - ss_res) / p) / (ss_res / (n - p - 1)) if p > 0 and n > p + 1 and ss_res > 0 else 0
        from ..finance.regression import f_pvalue as _f_pvalue
        f_pval = _f_pvalue(f_stat, p, n - p - 1)

        # Residual analysis — top outliers
        std_resid = resid / rmse if rmse > 0 else resid

        # Phase 4B: compute leverage + Cook's D for every row so we
        # can both (a) rank by influence (the academic-medical-
        # centre signal the rebuild plan calls for) and (b) classify
        # each high-residual row as legitimate_but_different_class /
        # data_issue / high_influence / possible_opportunity rather
        # than just "big σ".
        try:
            leverage_arr, _stud_arr, cooks_arr = _compute_influence(
                X, y, y_hat,
            )
        except Exception:
            leverage_arr = np.full(len(y), np.nan)
            cooks_arr = np.full(len(y), np.nan)

        # Rank by Cook's D when it's available, else fall back to
        # |std residual| as before
        if np.any(np.isfinite(cooks_arr)):
            rank_key = np.where(
                np.isfinite(cooks_arr), -cooks_arr, np.inf,
            )
            outlier_idx = np.argsort(rank_key)[:20]
        else:
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
            row_segment = (
                str(clean.iloc[idx].get("segment_label", ""))
                if segment_col else None
            )
            cls, sev = _classify_influence(
                float(leverage_arr[idx]),
                float(std_resid[idx]),
                float(cooks_arr[idx]),
                n=n, p=p,
                segment=row_segment,
            )
            row_data = {
                "index": int(idx),
                "actual": actual_disp,
                "predicted": predicted_disp,
                "residual": float(resid[idx]),
                "std_residual": float(std_resid[idx]),
                "leverage": float(leverage_arr[idx]),
                "cooks_d": float(cooks_arr[idx]),
                "influence_class": cls,
                "influence_severity": sev,
            }
            if ccn_col:
                row_data["ccn"] = str(clean.iloc[idx].get("ccn", ""))
            if name_col:
                row_data["name"] = str(clean.iloc[idx].get("name", ""))[:40]
            if state_col:
                row_data["state"] = str(clean.iloc[idx].get("state", ""))
            if segment_col:
                row_data["segment"] = row_segment or ""
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

        # Multicollinearity summary — condition number + plain-English
        # verdict + the VIF-pruned ("optimized") feature set. This is what
        # stops the page from presenting a high-R²/high-F fit built on
        # inter-correlated predictors as if its coefficients were reliable.
        from ..finance.regression import (
            condition_number as _cond_num,
            multicollinearity_verdict as _mc_verdict,
            prune_collinear as _prune_collinear,
        )
        cond_num = _cond_num(clean[available])
        max_vif = max((v["vif"] for v in vifs), default=1.0)
        verdict = _mc_verdict(max_vif, cond_num)
        # The "optimized" (clean) feature set is built in two passes:
        #   1. structural dedup — drop transforms/proxies of a dimension already
        #      represented (catches the NONLINEAR duplicates VIF misses), then
        #   2. VIF pruning at 5.0 (textbook "serious collinearity"), tighter
        #      than the old 10 so every surviving coefficient is interpretable.
        fam_keep, fam_dropped = _dedupe_feature_families(clean, target, available)
        vif_keep, vif_dropped = _prune_collinear(clean[fam_keep], max_vif=5.0)
        for d in vif_dropped:
            d["reason"] = "high_vif"
        opt_features = vif_keep
        opt_dropped = fam_dropped + vif_dropped

        return {
            "r2": r2,
            "adj_r2": adj_r2,
            "n": n,
            "p": p,
            "f_stat": f_stat,
            "f_pvalue": f_pval,
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
            "condition_number": cond_num,
            "max_vif": max_vif,
            "verdict": verdict,
            "optimized_features": opt_features,
            "optimized_dropped": opt_dropped,
            # Inference diagnostics: SEs are HC1-robust; BP reports whether the
            # homoskedasticity assumption is actually violated for this fit.
            "robust_se": True,
            "breusch_pagan": bp_test,
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
    cv: bool = False,
    cluster: bool = False,
    cluster_k: int = 6,
    buyability: bool = False,
    optimized: bool = False,
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
    #
    # UI fix (post-Phase-6 review): splitting the pills into two
    # semantic rows. Earlier version rendered all 17 pills as a
    # single wrapping line which crammed the form. Row 1 is the
    # 5 preset universes (All / Acquisition / Community / Rural /
    # Academic+Teaching) that partners use ~95% of the time; Row 2
    # is the 12 explicit segment labels for power-user drill-in.
    _UNIVERSE_PRESETS = [
        ("all",                  "All hospitals"),
        ("acquisition_targets",  "Acquisition targets"),
        ("community",            "Community"),
        ("rural",                "Rural / CAH"),
        ("academic_teaching",    "Academic & teaching"),
    ]
    _UNIVERSE_SEGMENTS = [(seg, seg) for seg in SEGMENT_LABELS]

    def _render_pills(options):
        out = ""
        for u_key, u_label in options:
            active = "rg-pill-active" if u_key == universe else ""
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
            if cv:
                href_params.append("cv=1")
            if cluster:
                href_params.append("cluster=1")
            if buyability:
                href_params.append("buyability=1")
            href = "/portfolio/regression?" + "&amp;".join(href_params)
            out += (
                f'<a href="{href}" class="rg-pill {active}">'
                f'{_html.escape(u_label)}</a>'
            )
        return out

    universe_pills_presets = _render_pills(_UNIVERSE_PRESETS)
    universe_pills_segments = _render_pills(_UNIVERSE_SEGMENTS)

    # Data source + target + log + segmented controls
    selector_form = (
        '<form method="GET" action="/portfolio/regression" class="rg-selector-form">'
        # Marker so the route can tell an explicit form submit (where an
        # unchecked box legitimately means "off") from a fresh page load
        # (where we apply the honest defaults: drop leakage + log $ target).
        '<input type="hidden" name="submitted" value="1">'
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
        '<label class="rg-selector-checkbox">'
        f'<input type="checkbox" name="cv" value="1" '
        f'{"checked" if cv else ""}> Cross-validate (5-fold OOS R²)'
        '</label>'
        '<label class="rg-selector-checkbox">'
        f'<input type="checkbox" name="cluster" value="1" '
        f'{"checked" if cluster else ""}> Cluster explorer '
        f'(k-means on structural features)'
        '</label>'
        '<label class="rg-selector-checkbox">'
        f'<input type="checkbox" name="buyability" value="1" '
        f'{"checked" if buyability else ""}> Buyability lens '
        f'(P(acquirable) per hospital + attractiveness composite)'
        '</label>'
        '</div>'
        '<div class="rg-selector-submit">'
        '<button type="submit" class="cad-btn cad-btn-primary">Run Regression</button>'
        '</div></form>'
    )
    source_selector = ck_panel(
        '<div class="rg-pills-row">'
        '<div class="rg-pills-label">UNIVERSE</div>'
        f'<div class="rg-pills">{universe_pills_presets}</div>'
        '</div>'
        '<div class="rg-pills-row rg-pills-row-sub">'
        '<div class="rg-pills-label">BY SEGMENT</div>'
        f'<div class="rg-pills">{universe_pills_segments}</div>'
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
        next_step = (
            "Add or import deals from the Pipeline, then reload this page."
            if data_source == "portfolio"
            else "Load CMS HCRIS public data first (run "
            "<code>rcm-mc data refresh</code> or use the Data Catalog), "
            "then reload this page."
        )
        body = (
            f'{source_selector}'
            + ck_panel(
                '<p class="ck-section-body">'
                '<strong>No data loaded yet.</strong> Regression Analysis fits '
                'KPI driver models across a dataset, so it needs records before '
                'it can show coefficients, fit quality, or driver rankings.<br>'
                f'{next_step}'
                '</p>',
                title="Regression Analysis",
            )
        )
        return chartis_shell(
            body, "Regression Analysis",
            subtitle="No data loaded — add records to run a regression")

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

    _features_was_none = features is None
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
    # On a default load (no explicit feature override) prefer the curated
    # low-collinearity set for this target — keeps the headline fit
    # defensible (significant coefficients, VIF < 10) instead of dumping
    # every safe-but-collinear column into OLS. The leakage panel above
    # still audits the full candidate list, so partners see what's excluded.
    if _features_was_none and drop_leakage and target in _CURATED_DEFAULTS:
        curated = [f for f in _CURATED_DEFAULTS[target] if f in df.columns]
        if len(curated) >= 2:
            features = curated

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

    # Optimized mode: refit on the VIF-pruned feature set so the partner gets a
    # model with interpretable coefficients instead of the collinear one. The
    # verdict banner links here when collinearity is real; we keep the original
    # drop list around so the banner can say what was removed.
    optimized_applied = False
    _orig_dropped = list(result.get("optimized_dropped") or [])
    if optimized and _orig_dropped:
        opt_feats = result.get("optimized_features") or features
        if len(opt_feats) >= 1:
            opt_result = _run_ols(df, target, opt_feats, log_target=log_target)
            if opt_result is not None:
                result = opt_result
                optimized_applied = True

    # ── Editorial intro + KPI strip ──
    # Guided, plain-language lead — what you're predicting and what the model
    # found, not a row of statistics the reader has to decode. Every value is
    # interpolated from the live fit (no static copy), and the wording reflects
    # whether we auto-cleaned the feature set.
    _tgt_words = target.replace('_', ' ')
    _n_drop = len(_orig_dropped)
    if optimized_applied and _n_drop:
        _clean_clause = (
            f" We automatically dropped {_n_drop} collinear "
            f"feature{'s' if _n_drop != 1 else ''} so each coefficient is "
            f"trustworthy — see exactly why just below.")
    elif _orig_dropped:
        _clean_clause = (
            f" You're viewing the full model; {len(result.get('optimized_features') or [])} "
            "of these predictors are collinear and a cleaner model is one "
            "click away below.")
    else:
        _clean_clause = (" No predictors are collinear, so every coefficient "
                         "can be read directly.")
    _r2_pct = f"{result['r2']:.0%}"
    intro = ck_section_intro(
        eyebrow=f"REGRESSION · {_html.escape(_tgt_words.upper())}",
        headline=(f"Predicting {_html.escape(_tgt_words)} across "
                  f"{result['n']:,} hospitals."),
        italic_word="Predicting",
        body=(
            f"These {result['p']} predictors explain {_r2_pct} of the "
            f"variation in {_html.escape(_tgt_words)} "
            f"(R² = {result['r2']:.1%}, adjusted {result['adj_r2']:.1%})."
            f"{_clean_clause}"
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
            sub=(
                "p &lt; 0.001" if result.get("f_pvalue", 1.0) < 0.001
                else f"p = {result.get('f_pvalue', 1.0):.3f}"
            ),
            help={
                "definition": (
                    "Joint significance of all features taken "
                    "together vs the null model (intercept only). "
                    "Higher F means the regression as a whole is "
                    "statistically meaningful. The p-value is the "
                    "verdict — but note a tiny p next to a high F with "
                    "few individually-significant coefficients is the "
                    "classic multicollinearity signature (see the "
                    "verdict banner)."
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
        + ck_kpi_block(
            "Condition #",
            ("&infin;" if result.get("condition_number", 0) == float("inf")
             else f"{result.get('condition_number', 0):,.0f}"),
            help={
                "definition": (
                    "Belsley condition number of the design matrix — the "
                    "single-number multicollinearity diagnostic. <30 is "
                    "fine; 30–100 moderate; >100 means predictors are so "
                    "inter-correlated that individual coefficients are "
                    "numerically unstable and the R² is inflated."
                ),
            },
        )
        + '</div>'
    )

    # ── Multicollinearity verdict banner ──
    # The reader must never mistake a high-R²/high-F fit propped up by
    # inter-correlated predictors for a trustworthy one. This banner states
    # the verdict in plain English and, when collinearity is real, names the
    # optimized (VIF-pruned) feature set that fixes it.
    _verdict = result.get("verdict") or {}
    _sev = _verdict.get("severity", "low")
    _sev_color = {"severe": "#b5321e", "moderate": "#b8732a",
                  "low": "#0a8a5f"}.get(_sev, "#6a7480")
    _sev_label = {"severe": "Severe multicollinearity",
                  "moderate": "Moderate multicollinearity",
                  "low": "Low multicollinearity"}.get(_sev, "Multicollinearity")
    # Self-referential link that toggles ?optimized, preserving the other
    # controls so a partner can flip between the full and the de-collinearized
    # model without losing their target / universe / log selection.
    def _toggle_url(opt_on: bool) -> str:
        parts = [f"source={_html.escape(data_source, quote=True)}",
                 f"target={_html.escape(target, quote=True)}",
                 f"universe={_html.escape(universe, quote=True)}"]
        if log_target:
            parts.append("log=1")
        if segmented:
            parts.append("segmented=1")
        if drop_leakage:
            parts.append("drop_leakage=1")
        if cv:
            parts.append("cv=1")
        # Always explicit so it survives the honest-by-default (optimized-on)
        # route logic: =1 forces the pruned model, =0 forces the full one.
        parts.append("optimized=1" if opt_on else "optimized=0")
        return "/portfolio/regression?" + "&amp;".join(parts)

    def _why_dropped(drops: List[Dict[str, Any]]) -> str:
        # Per-feature plain-language reason — what each dropped feature was
        # collinear with — so a removal is never a black box.
        items = []
        for d in drops:
            feat = _html.escape(d["feature"].replace("_", " "))
            eb = d.get("explained_by") or []
            partners = ", ".join(
                f'{_html.escape(e["feature"].replace("_", " "))} '
                f'(r&nbsp;{e["r"]:.2f})' for e in eb)
            if d.get("reason") == "redundant":
                # Structural duplicate: individually it may correlate with the
                # target, but it carries no information beyond its family rep.
                uni = d.get("univariate_r")
                uni_txt = (f" — its own correlation with the target "
                           f"(r&nbsp;{uni:.2f}) is already captured"
                           if uni is not None else "")
                tag = "redundant transform"
                reason = (f"a transform of {partners}{uni_txt}"
                          if partners else "a transform of a predictor already "
                          "in the model")
            else:
                vif = d.get("vif")
                tag = "VIF &infin;" if vif is None else f"VIF&nbsp;{vif:.0f}"
                reason = (f"nearly determined by {partners}" if partners
                          else "almost fully explained by the other predictors")
            items.append(
                f'<li style="margin:3px 0;"><b>{feat}</b> &mdash; {tag}; '
                f'{reason}.</li>')
        return ('<ul style="margin:6px 0 0;padding-left:18px;font-size:12px;'
                'line-height:1.5;color:var(--sc-text-dim,#465366);">'
                f'{"".join(items)}</ul>')

    if optimized_applied:
        _n = len(_orig_dropped)
        _opt_html = (
            f'<div style="margin-top:8px;font-size:12.5px;line-height:1.55;'
            f'color:var(--sc-text,#1a2332);">&#10003; <b>Built you a clean '
            f'model</b> — dropped {_n} collinear '
            f'feature{"s" if _n != 1 else ""} so every coefficient below is '
            f'trustworthy:'
            f'{_why_dropped(_orig_dropped)}'
            f'<div style="margin-top:6px;">'
            f'<a href="{_toggle_url(False)}" style="color:var(--sc-teal,#155752);">'
            f'See the full (collinear) model instead &rarr;</a></div></div>')
    elif _orig_dropped:
        _opt = result.get("optimized_features") or []
        _opt_html = (
            f'<div style="margin-top:8px;font-size:12.5px;line-height:1.55;'
            f'color:var(--sc-text,#1a2332);">You are viewing the full model. '
            f'A cleaner {len(_opt)}-feature model drops these collinear '
            f'predictors:'
            f'{_why_dropped(_orig_dropped)}'
            f'<div style="margin-top:6px;">'
            f'<a href="{_toggle_url(True)}" style="color:var(--sc-teal,#155752);'
            f'font-weight:600;">Switch to the clean model &rarr;</a></div></div>')
    else:
        _opt_html = (
            '<div style="margin-top:8px;font-size:12.5px;color:'
            'var(--sc-text-dim,#465366);">&#10003; Every predictor is below the '
            'VIF&nbsp;10 threshold — no collinear features to drop.</div>')
    multicollinearity_banner = (
        f'<div style="background:var(--sc-paper,#faf6ec);border:1px solid '
        f'var(--sc-rule,#c9c1ac);border-left:4px solid {_sev_color};'
        f'border-radius:3px;padding:13px 16px;margin:0 0 16px;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;'
        f'flex-wrap:wrap;margin-bottom:4px;">'
        f'<span style="font-family:var(--sc-mono);font-size:10px;'
        f'font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:{_sev_color};">{_html.escape(_sev_label)}</span>'
        f'<span style="font-family:var(--sc-mono);font-size:10px;'
        f'color:var(--sc-text-faint,#8b94a0);">condition # '
        f'{("&infin;" if result.get("condition_number",0)==float("inf") else format(result.get("condition_number",0), ",.0f"))}'
        f' · max VIF {min(result.get("max_vif",1.0),999):.0f}</span></div>'
        f'<div style="font-size:12.5px;line-height:1.55;color:'
        f'var(--sc-text,#1a2332);">{_html.escape(_verdict.get("message",""))} '
        f'<i>{_html.escape(_verdict.get("recommendation",""))}</i></div>'
        f'{_opt_html}</div>'
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

    _coef_chart = _coefficient_forest_chart(result["coefficients"])
    _coef_fig = (
        f'<style>{_REG_CHART_CAPTION_CSS}</style>'
        f'<div class="rg-figcap">Standardized coefficients with 95% CI '
        f'&middot; bar = effect, whisker = confidence interval</div>'
        f'{_coef_chart}'
    ) if _coef_chart else ""
    # Inference-method note: SEs are HC1-robust; report the Breusch–Pagan
    # verdict so the reader knows whether the robustness actually mattered.
    _bp = result.get("breusch_pagan") or {}
    if _bp.get("heteroskedastic") is True:
        _bp_verdict = (
            f'Breusch&ndash;Pagan F={_bp.get("f_stat", 0):.1f}, '
            f'p={_bp.get("p_value", 1):.4f} &mdash; <strong>heteroskedasticity '
            'detected</strong>, so the robust SEs (wider, honest) are what you '
            'should read here, not the classical ones.'
        )
    elif _bp.get("heteroskedastic") is False:
        _bp_verdict = (
            f'Breusch&ndash;Pagan p={_bp.get("p_value", 1):.3f} &mdash; no '
            'heteroskedasticity detected; robust and classical SEs agree.'
        )
    else:
        _bp_verdict = "Heteroskedasticity test not available for this fit."
    coef_section = ck_panel(
        '<p class="ck-section-body">'
        f'Target: <strong>{_html.escape(target.replace("_", " ").title())}</strong>. '
        'Standardized coefficients (-1.0 to +1.0): a one-SD increase in the feature produces '
        'this fraction of the strongest effect. '
        '*** p&lt;0.001, ** p&lt;0.01, * p&lt;0.05.</p>'
        '<p class="ck-section-body" style="font-size:12px;">'
        'Standard errors are <strong>HC1 heteroskedasticity-robust</strong> '
        '(White sandwich) &mdash; the t-stats, p-values and 95% CIs below use '
        f'them. {_bp_verdict}</p>'
        f'{_coef_fig}'
        '<table class="cad-table"><thead><tr>'
        '<th>Variable</th><th>Strength</th><th>t</th><th>p-value</th>'
        '<th>Sig</th><th>95% CI</th><th>Impact</th>'
        f'</tr></thead><tbody>{coef_rows}</tbody></table>',
        title="Coefficients (Standardized)",
    )

    # ── Target correlations (univariate) ──
    tcorr_section = ck_panel(
        '<p class="ck-section-body">'
        f'Pearson r for each feature vs {_html.escape(target.replace("_", " ").title())}. '
        'Shows the raw linear relationship <em>before</em> controlling for other '
        'variables &mdash; a feature can land high here yet be dropped from the '
        'model as a redundant transform of another driver.</p>'
        f'{_univariate_corr_chart(result["target_correlations"])}',
        title="Univariate Correlations with Target",
    ) if result.get("target_correlations") else ""

    # ── VIF (multicollinearity) ──
    vif_section = ck_panel(
        '<p class="ck-section-body">'
        'How much each coefficient&rsquo;s variance is inflated by correlation '
        'with the other predictors. VIF&nbsp;&gt;&nbsp;10 = severe (estimates '
        'unreliable); 5&ndash;10 = caution. The clean model keeps every feature '
        'below&nbsp;5.</p>'
        f'{_vif_bar_chart(result["vifs"])}',
        title="Variance Inflation Factors",
    ) if result.get("vifs") else ""

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
    # Phase-4B: per-row influence classification + Cook's D /
    # leverage columns.
    _CLS_BADGE = {
        "legitimate_but_different_class": "rg-influence-legitimate",
        "possible_opportunity":           "rg-influence-opportunity",
        "data_issue":                     "rg-influence-data-issue",
        "high_influence":                 "rg-influence-high",
        "perfect_leverage":               "rg-influence-data-issue",
        "in_band":                        "rg-influence-ok",
        "unknown":                        "rg-influence-info",
    }
    _CLS_DISPLAY = {
        "legitimate_but_different_class": "diff. regime",
        "possible_opportunity":           "opportunity",
        "data_issue":                     "data issue?",
        "high_influence":                 "high influence",
        "perfect_leverage":               "perfect leverage",
        "in_band":                        "in band",
        "unknown":                        "—",
    }
    has_influence = bool(
        result["outliers"] and "cooks_d" in result["outliers"][0]
    )
    # Phase-6: when the buyability lens is on, compute P(acquirable)
    # for every outlier row by joining back to the taxonomy-tagged
    # df via CCN, then derive attractiveness from the row's residual
    # severity as a financial proxy. Surfaces the partner-critical
    # insight: Stanford has a huge residual but ~2% buyability, so
    # attractiveness ~0 even with a perfect financial score.
    has_buyability = bool(
        buyability and result["outliers"]
        and "ccn" in result["outliers"][0]
    )
    _outlier_buyability: Dict[str, Dict[str, Any]] = {}
    if has_buyability:
        try:
            from ..finance.buyability import score_buyability as _sb
            ccn_index = (
                df.set_index("ccn")
                if "ccn" in df.columns else None
            )
            for o in result["outliers"]:
                ccn = o.get("ccn", "")
                if ccn_index is not None and ccn in ccn_index.index:
                    row_data = ccn_index.loc[ccn]
                    # ccn_index.loc[ccn] returns Series for a unique
                    # match, DataFrame for duplicates. Take the first
                    # row in either case.
                    if isinstance(row_data, pd.DataFrame):
                        row_dict = row_data.iloc[0].to_dict()
                    elif isinstance(row_data, pd.Series):
                        row_dict = row_data.to_dict()
                    else:
                        row_dict = dict(row_data)
                    score = _sb(row_dict)
                    # Financial proxy: clip |residual σ| / 3 → [0, 1]
                    fin = min(1.0, abs(o["std_residual"]) / 3.0)
                    att = _attractiveness(fin, score.score)
                    _outlier_buyability[ccn] = {
                        "score": score.score,
                        "tier": score.tier,
                        "attractiveness": att,
                        "attractiveness_tier": _attractiveness_tier(att),
                    }
        except Exception:
            has_buyability = False

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
        cooks_cell = ""
        cls_cell = ""
        if has_influence:
            cooks = o.get("cooks_d", float("nan"))
            cooks_disp = (
                f'{cooks:.3f}' if isinstance(cooks, float)
                and cooks == cooks else '—'
            )
            cooks_cls = (
                "cad-neg" if isinstance(cooks, float) and cooks > 1.0
                else "cad-warn" if isinstance(cooks, float) and cooks > 0.5
                else ""
            )
            cooks_cell = (
                f'<td class="num {cooks_cls}">{cooks_disp}</td>'
            )
            inf_cls = o.get("influence_class", "unknown")
            badge_cls = _CLS_BADGE.get(inf_cls, "rg-influence-info")
            cls_cell = (
                f'<td><span class="rg-influence-badge {badge_cls}">'
                f'{_html.escape(_CLS_DISPLAY.get(inf_cls, inf_cls))}'
                '</span></td>'
            )
        buy_cell = ""
        att_cell = ""
        if has_buyability:
            ccn = o.get("ccn", "")
            buy_info = _outlier_buyability.get(ccn)
            if buy_info:
                buy_pct = buy_info["score"] * 100
                buy_cls = {
                    "high":     "cad-pos",
                    "medium":   "cad-warn",
                    "low":      "cad-warn",
                    "very_low": "cad-neg",
                }.get(buy_info["tier"], "")
                buy_cell = (
                    f'<td class="num {buy_cls}">'
                    f'{buy_pct:.0f}%</td>'
                )
                att_pct = buy_info["attractiveness"] * 100
                att_tier_cls = {
                    "pursue":      "cad-pos",
                    "investigate": "cad-warn",
                    "monitor":     "",
                    "skip":        "cad-neg",
                }.get(buy_info["attractiveness_tier"], "")
                att_cell = (
                    f'<td class="num {att_tier_cls}">'
                    f'{att_pct:.0f}%</td>'
                )
            else:
                buy_cell = '<td class="num">—</td>'
                att_cell = '<td class="num">—</td>'
        outlier_rows += (
            f'<tr>'
            f'<td>{link}</td>'
            f'{seg_cell}'
            f'<td>{_html.escape(state)}</td>'
            f'<td class="num">{_fmt_num(o["actual"])}</td>'
            f'<td class="num">{_fmt_num(o["predicted"])}</td>'
            f'<td class="num {resid_cls}"><strong>{resid_val:+.2f}σ</strong></td>'
            f'{cooks_cell}'
            f'{cls_cell}'
            f'{buy_cell}'
            f'{att_cell}'
            f'</tr>'
        )

    seg_header = '<th>Segment</th>' if has_segments else ''
    influence_headers = (
        '<th>Cook\'s D</th><th>Class</th>' if has_influence else ''
    )
    buyability_headers = (
        '<th>P(buyable)</th><th>Attractiveness</th>'
        if has_buyability else ''
    )
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
        + (
            ' Rows are ranked by <strong>Cook\'s distance</strong> '
            '(combines leverage and residual) — Cook\'s D &gt; 1 '
            '= definitely influential. The <strong>Class</strong> '
            'column labels each row: <em>diff. regime</em> = '
            'academic/specialty hospital that\'s influential because '
            'it lives at the top of the distribution, not a data '
            'error (don\'t delete). <em>opportunity</em> = community/CAH '
            'with large positive residual — actuals beat the model. '
            '<em>data issue?</em> = big residual without high '
            'leverage — investigate the entry.'
            if has_influence else ''
        )
        + '<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th>{seg_header}<th>State</th>'
        '<th>Actual</th><th>Predicted</th><th>Residual</th>'
        f'{influence_headers}'
        f'{buyability_headers}'
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
        "LEAKS":           "rg-leak-critical",
        "SELF":            "rg-leak-critical",
        "FORMULA_RELATED": "rg-leak-warning",
        "SAFE":            "rg-leak-ok",
        "UNKNOWN":         "rg-leak-info",
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
        # Transitive chip — only for FORMULA_RELATED cases that came
        # from the multi-hop atomic-input walk (PR #248). Lets the
        # partner distinguish "direct cousin" from "chain cousin"
        # at a glance; the reason text already explains the chain
        # but the chip surfaces the signal without reading it.
        transitive_chip = (
            ' <span class="rg-leak-transitive-chip" '
            'title="Detected via multi-hop atomic-input walk — '
            'feature and target share raw ancestors through an '
            'intermediate derived feature">transitive</span>'
            if getattr(v, "transitive", False) else ''
        )
        leak_rows.append(
            f'<tr>'
            f'<td><strong>{_html.escape(v.feature.replace("_", " ").title())}</strong></td>'
            f'<td><span class="rg-leak-badge {badge_cls}">'
            f'{_html.escape(v.verdict)}</span>{transitive_chip}</td>'
            f'<td style="font-size:12px;color:var(--cad-text2);">'
            f'{_html.escape(v.reason)}</td>'
            f'<td>{in_fit_mark}</td>'
            f'</tr>'
        )

    # Count critical leaks for the panel header
    leak_count = sum(
        1 for v in leakage_verdicts if v.severity == "critical"
    )
    # FORMULA_RELATED count for the amber sibling banner. Counts
    # warning-severity verdicts that are FORMULA_RELATED specifically
    # — SAFE+warning (explanation_only features) is a separate signal.
    formula_related_count = sum(
        1 for v in leakage_verdicts if v.verdict == "FORMULA_RELATED"
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
        'predicting anything. <strong>FORMULA_RELATED</strong> = '
        'feature and target are accounting-identity cousins (they '
        'share underlying inputs but neither contains the other) — '
        'softer warning; kept by default. A '
        '<span class="rg-leak-transitive-chip">transitive</span> '
        'chip means the cousin relationship was detected via the '
        'multi-hop atomic-input walk (one or both go through an '
        'intermediate derived feature) rather than a 1-hop direct '
        'shared input. <strong>SAFE</strong> = no algebraic path. '
        '<strong>SELF</strong> = feature IS the target. '
        '<strong>UNKNOWN</strong> = no provenance record (caller '
        'decides; defaults to staying in the fit).</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Feature</th><th>Verdict</th>'
        '<th>Reason</th><th>Status</th>'
        f'</tr></thead><tbody>{"".join(leak_rows)}</tbody></table>',
        title="Feature Leakage Audit",
    )

    # ── Cross-validation panel (Phase 4A) ──
    # Only computed when the partner explicitly toggles
    # "Cross-validate". CV is expensive (~k × baseline fit cost)
    # so we don't run it by default. Result is the OOS R² + RMSE
    # the diagnostic banner says we don't yet have without CV.
    cv_section = ""
    if cv:
        try:
            cv_res = _run_cv(
                df, target, result["features"],
                k=5, log_transform_target=log_target,
                random_state=42,
                auto_reduce_k=True,
            )
        except ValueError as exc:
            cv_section = ck_panel(
                f'<p class="ck-section-body cad-warn">'
                f'Cross-validation could not run: '
                f'{_html.escape(str(exc))}</p>',
                title="Cross-Validation (5-fold)",
            )
            cv_res = None

        if cv_res is not None:
            import math as _math
            # Per-fold rows
            fold_rows = ""
            for f in cv_res.folds:
                fold_rows += (
                    f'<tr>'
                    f'<td class="num"><strong>{f.fold + 1}</strong></td>'
                    f'<td class="num">{f.n_train:,}</td>'
                    f'<td class="num">{f.n_test:,}</td>'
                    f'<td class="num">{f.train_r_squared:.1%}</td>'
                    f'<td class="num">{f.test_r_squared:.1%}</td>'
                    f'<td class="num">{f.test_rmse:.3f}</td>'
                    f'</tr>'
                )

            gap = cv_res.overfit_gap
            if gap > 0.15:
                gap_cls = "cad-neg"
                gap_note = (
                    " — substantial overfit signal; in-sample R² is "
                    "reading off noise, leakage, or high-influence rows."
                )
            elif gap > 0.05:
                gap_cls = "cad-warn"
                gap_note = (
                    " — modest overfit; consider dropping leakage "
                    "features or running segmented."
                )
            else:
                gap_cls = "cad-pos"
                gap_note = (
                    " — small gap; the in-sample fit generalises "
                    "to held-out folds."
                )
            # auto_reduce_k=True can knock k down when the universe
            # is too thin (CAH, Small Community). Surface this so the
            # partner knows their "5-fold" request actually became
            # 3-fold or 2-fold — otherwise the headline "Mean test R²"
            # looks identical to a real 5-fold result.
            k_note = ""
            if cv_res.requested_k and cv_res.requested_k != cv_res.k:
                k_note = (
                    f' <span class="cad-warn">k auto-reduced from '
                    f'{cv_res.requested_k} → {cv_res.k} because '
                    f'the universe is too small for stable '
                    f'{cv_res.requested_k}-fold splits.</span>'
                )
            panel_title = f"Cross-Validation ({cv_res.k}-fold)"
            cv_section = ck_panel(
                '<p class="ck-section-body">'
                f'k={cv_res.k} random-fold cross-validation, '
                'seed = 42 '
                '(deterministic — same input → same OOS numbers). '
                'Test R² is the average across folds of the R² '
                'measured on the held-out rows after fitting '
                'on the rest. Big gap between in-sample R² and mean '
                f'test R² = overfit signal.{gap_note}{k_note}</p>'
                '<div class="ck-kpi-strip">'
                + ck_kpi_block(
                    "In-sample R²",
                    f"{cv_res.baseline_in_sample_r2:.1%}",
                )
                + ck_kpi_block(
                    "Mean test R² (OOS)",
                    f"{cv_res.mean_test_r2:.1%}",
                )
                + ck_kpi_block(
                    "Test R² std",
                    f"±{cv_res.std_test_r2:.1%}",
                )
                + ck_kpi_block(
                    "Overfit gap",
                    f"{gap * 100:+.1f}pp",
                )
                + ck_kpi_block(
                    # For a log-target fit the raw RMSE is in log units,
                    # which is hard to read; convert to the partner-facing
                    # "typical prediction is off by ±X%" (exp(rmse)-1).
                    # For a raw fit show RMSE in the target's own units.
                    "Mean test RMSE (OOS)",
                    (f"±{(_math.exp(cv_res.mean_test_rmse) - 1.0) * 100:.0f}%"
                     if cv_res.target_was_log_transformed
                     else f"{cv_res.mean_test_rmse:,.3g}"),
                    "typical OOS error" if cv_res.target_was_log_transformed else "",
                )
                + '</div>'
                '<table class="cad-table"><thead><tr>'
                '<th>Fold</th><th>n train</th><th>n test</th>'
                '<th>Train R²</th><th>Test R²</th><th>Test RMSE</th>'
                f'</tr></thead><tbody>{fold_rows}</tbody></table>',
                title=panel_title,
            )

    # ── Buyability Lens panel (Phase 6) ──
    # Per-hospital P(acquirable) + the target_attractiveness
    # composite (financial × buyability). Surfaces the partner-
    # critical insight that high-financial-revenue institutions
    # aren't necessarily acquirable — Stanford has a $9B NPSR but
    # buyability ~2%, so attractiveness ~0 even with a perfect
    # financial score.
    buyability_section = ""
    if buyability and "segment_label" in df.columns:
        try:
            scored_df = _score_buyability_batch(df)
            dist = _buyability_distribution(scored_df)
        except Exception as exc:
            buyability_section = ck_panel(
                f'<p class="ck-section-body cad-warn">'
                f'Buyability scoring failed: '
                f'{_html.escape(str(exc))}</p>',
                title="Buyability Lens",
            )
            scored_df = None
            dist = None

        if scored_df is not None and dist is not None:
            # Segment-mean table — most informative single view
            seg_rows = ""
            sorted_segs = sorted(
                dist.segment_means.items(), key=lambda kv: kv[1],
            )
            for seg_name, mean in sorted_segs:
                share_str = f"{mean * 100:.0f}%"
                tier_cls = (
                    "cad-pos" if mean >= 0.55
                    else "cad-warn" if mean >= 0.30
                    else "cad-neg"
                )
                seg_rows += (
                    '<tr>'
                    f'<td><span class="rg-segment-chip">'
                    f'{_html.escape(seg_name)}</span></td>'
                    f'<td class="num {tier_cls}">'
                    f'<strong>{share_str}</strong></td>'
                    '</tr>'
                )

            # Tier counts strip
            tier_strip = (
                '<div class="ck-kpi-strip">'
                + ck_kpi_block(
                    "high (≥55%)",
                    f'{dist.tier_counts.get("high", 0):,}',
                )
                + ck_kpi_block(
                    "medium (30-55%)",
                    f'{dist.tier_counts.get("medium", 0):,}',
                )
                + ck_kpi_block(
                    "low (15-30%)",
                    f'{dist.tier_counts.get("low", 0):,}',
                )
                + ck_kpi_block(
                    "very_low (<15%)",
                    f'{dist.tier_counts.get("very_low", 0):,}',
                )
                + ck_kpi_block(
                    "mean P(buyable)",
                    f'{dist.mean_score * 100:.1f}%',
                )
                + '</div>'
            )

            buyability_section = ck_panel(
                '<p class="ck-section-body">'
                'Rule-based P(acquirable by PE) per hospital, '
                'driven by the Phase-1 segment label (academic / '
                'flagship-specialty / children\'s ≈ unbuyable; '
                'community + CAH + rehab + LTACH at mid-bed size '
                '= sweet spot) plus penalties for membership in '
                'large nonprofit / Catholic / government systems '
                '(Ascension, Kaiser, VA, etc.) and for '
                'safety-net public hospitals. <strong>Heuristic '
                'v1</strong> — treat the ordering as the reliable '
                'signal; absolute percentages are partner-friendly '
                'summaries, not calibrated probabilities. '
                'Combined with the financial fit via '
                'target_attractiveness = financial × buyable × '
                'strategic_fit so the regression\'s top outliers '
                'don\'t over-weight institutions that are '
                'financially large but practically unbuyable.</p>'
                f'{tier_strip}'
                '<h4 class="rg-subhead">'
                'Mean buyability by hospital segment'
                '</h4>'
                '<table class="cad-table"><thead><tr>'
                '<th>Segment</th><th>Mean P(buyable)</th>'
                f'</tr></thead><tbody>{seg_rows}</tbody></table>',
                title="Buyability Lens",
            )

    # ── Cluster Explorer panel (Phase 5) ──
    # Unsupervised pass on structural features (log_beds, occupancy,
    # payer mix, taxonomy flags — deliberately NOT npr) to surface
    # within-rule-segment regime differences. PCA + k-means + auto-
    # naming via dominant rule-based segment + flavour modifiers.
    cluster_section = ""
    if cluster and "segment_label" in df.columns:
        try:
            cluster_res = _cluster_hospitals(
                df, k=max(2, min(12, cluster_k)),
                random_state=42,
            )
        except (ValueError, Exception) as exc:
            cluster_section = ck_panel(
                f'<p class="ck-section-body cad-warn">'
                f'Cluster explorer failed: '
                f'{_html.escape(str(exc))}</p>',
                title="Cluster Explorer",
            )
            cluster_res = None

        if cluster_res is not None:
            # Rows sorted by size descending
            sorted_profiles = sorted(
                cluster_res.profiles, key=lambda p: -p.size,
            )
            cluster_rows = ""
            for p in sorted_profiles:
                cluster_rows += (
                    '<tr>'
                    f'<td><strong>{p.cluster_id}</strong></td>'
                    f'<td><span class="rg-segment-chip">'
                    f'{_html.escape(p.name)}</span></td>'
                    f'<td class="num">{p.size:,}</td>'
                    f'<td>{_html.escape(p.dominant_segment)} '
                    f'<span class="cad-text2">'
                    f'({p.segment_share * 100:.0f}%)</span></td>'
                    f'<td class="num">{p.median_beds:.0f}</td>'
                    f'<td class="num">{p.median_medicare_pct:.0f}%</td>'
                    f'<td class="num">{p.median_medicaid_pct:.0f}%</td>'
                    f'<td class="num">{p.safety_net_share * 100:.0f}%</td>'
                    f'<td class="num">{p.academic_share * 100:.0f}%</td>'
                    '</tr>'
                )
            pca_var = cluster_res.pca.explained_variance_ratio
            var_str = " · ".join(
                f"PC{i + 1}: {v * 100:.0f}%"
                for i, v in enumerate(pca_var)
            )
            # PCA scatter plot — turns the cluster panel from a
            # table dump into a real visualization. Every hospital
            # plots at its (PC1, PC2) projection coloured by cluster;
            # cluster centroids render as larger diamonds on top.
            scatter_svg = _render_cluster_scatter(cluster_res)
            cluster_section = ck_panel(
                '<p class="ck-section-body">'
                f'<strong>k = {cluster_res.k}</strong> · '
                f'{cluster_res.n_rows:,} hospitals clustered on '
                f'{len(cluster_res.features)} structural features '
                f'({", ".join(cluster_res.features[:3])}…). PCA top-2 '
                f'explained variance: <strong>{var_str}</strong>. '
                'Cluster names are auto-generated from the dominant '
                'rule-based segment + structural flavour. Use this '
                'to surface within-segment regime differences the '
                'taxonomy alone misses — e.g. a Large Community '
                'cluster that\'s actually 90% Medicaid + urban '
                'belongs in its own regression slope.</p>'
                '<div class="rg-cluster-scatter-wrap" '
                'style="margin:8px 0 18px;display:flex;'
                'justify-content:center;">'
                f'{scatter_svg}'
                '</div>'
                '<table class="cad-table"><thead><tr>'
                '<th>#</th><th>Cluster name</th><th>n</th>'
                '<th>Dominant segment</th><th>Med beds</th>'
                '<th>Med MC%</th><th>Med MD%</th>'
                '<th>Safety-net share</th><th>Academic share</th>'
                f'</tr></thead><tbody>{cluster_rows}</tbody></table>',
                title="Cluster Explorer (PCA + k-means)",
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
.rg-selector-form{display:flex;flex-wrap:wrap;gap:14px 18px;
align-items:flex-end;}
.rg-selector-label{font-size:12px;color:var(--cad-text2);
display:block;margin-bottom:4px;}
.rg-selector-input{padding:7px 12px;border:1px solid var(--cad-border);
border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;
transition:border-color 120ms ease, box-shadow 120ms ease;min-width:220px;}
.rg-selector-input:focus{outline:none;border-color:var(--cad-link);
box-shadow:0 0 0 2px rgba(21,87,82,0.18);}
.rg-selector-submit{align-self:flex-end;}
/* Form-layout fix: 6 checkbox toggles in a single column made
 * the form tall and squished the dropdowns inline. 2-column
 * grid wraps to 1-column on narrow viewports. */
.rg-selector-toggles{display:grid;
grid-template-columns:repeat(2, minmax(220px, 1fr));
gap:6px 18px;align-self:flex-end;padding-bottom:2px;
flex:1 1 460px;}
.rg-selector-checkbox{font-size:12px;color:var(--cad-text);
display:flex;align-items:center;gap:6px;cursor:pointer;
white-space:nowrap;}
.rg-pills-row{display:flex;align-items:baseline;gap:14px;margin:0 0 14px;
flex-wrap:wrap;}
/* Sub-row (BY SEGMENT) — slightly muted to signal it's the
 * power-user drill-in below the 5 preset universes. */
.rg-pills-row-sub{margin-top:-8px;opacity:0.85;}
.rg-pills-row-sub .rg-pill{font-size:11px;padding:3px 10px;}
.rg-pills-label{font-family:var(--sc-mono,monospace);font-size:10px;
font-weight:600;letter-spacing:0.16em;text-transform:uppercase;
color:var(--sc-text-faint,#7a8699);min-width:88px;}
.rg-pills{display:flex;flex-wrap:wrap;gap:6px;}
.rg-pill{display:inline-block;padding:5px 12px;font-family:var(--sc-sans,Inter);
font-size:11.5px;font-weight:500;border:1px solid var(--sc-rule,#d6cfc0);
background:#fff;color:var(--sc-navy,#0b2341);text-decoration:none;
border-radius:14px;transition:border-color 120ms ease,background 120ms ease;}
.rg-pill:hover{border-color:var(--sc-teal-ink,#155752);}
.rg-pill-active{background:var(--sc-navy,#0b2341);color:#fff;
border-color:var(--sc-navy,#0b2341);}
.rg-diagnostic-banner{display:flex;align-items:baseline;gap:12px;
padding:14px 18px;margin:0 0 16px;background:#fff;
border:1px solid var(--sc-rule,#d6cfc0);
border-left:3px solid var(--sc-teal-ink,#155752);}
.rg-diagnostic-tag{font-family:var(--sc-mono,monospace);font-size:11px;
font-weight:700;letter-spacing:0.14em;color:var(--sc-teal-ink,#155752);
flex-shrink:0;}
.rg-diagnostic-text{font-size:14px;color:var(--sc-text,#1a2332);
line-height:1.55;}
.rg-diagnostic-text em{color:var(--sc-teal-ink,#155752);font-style:italic;}
/* Leakage alert banner — fires when drop_leakage=off + critical
 * leaks exist. Red border + parchment background so partners can't
 * miss the inflated-R² warning the inline panel was burying. */
.rg-leakage-banner{display:flex;align-items:baseline;gap:14px;
padding:14px 18px;margin:0 0 16px;background:#fff;
border:1px solid #b5321e;border-left:5px solid #b5321e;}
.rg-leakage-banner-tag{font-family:var(--sc-mono,monospace);font-size:11px;
font-weight:700;letter-spacing:0.14em;color:#b5321e;flex-shrink:0;}
.rg-leakage-banner-text{font-size:14px;color:var(--sc-text,#1a2332);
line-height:1.55;}
.rg-leakage-banner-text strong{color:#b5321e;}
/* Amber sibling — fires when FORMULA_RELATED (accounting-cousin)
 * features are in the fit. Not a critical leak but the R² is still
 * suspect because the feature shares atomic inputs with the target.
 * Softer tone than the red banner so the partner can tell at a
 * glance which severity bucket they're in. */
.rg-leakage-banner.warn{border-color:#b8732a;border-left-color:#b8732a;}
.rg-leakage-banner.warn .rg-leakage-banner-tag{color:#b8732a;}
.rg-leakage-banner.warn .rg-leakage-banner-text strong{color:#b8732a;}
/* Readability bump (user-reported "text is impossible to read"):
 * the panel description paragraphs were unstyled bare <p>s that
 * picked up the browser default (12-13px). Bump to 14px + 1.6
 * line-height so the multi-line descriptions on the leakage,
 * cluster, segmented, buyability, and outliers panels are
 * comfortable to read. Restricted to .ck-panel-body so it doesn't
 * leak into other surfaces. */
.ck-panel-body .ck-section-body{
  font-size:14px;line-height:1.6;color:var(--sc-text,#1a2332);
  margin:0 0 12px;max-width:88ch;
}
.ck-panel-body .ck-section-body strong{color:var(--sc-navy,#0b2341);}
.ck-panel-body .ck-section-body em{
  color:var(--sc-teal-ink,#155752);font-style:italic;
}
/* Bump the inline reason cells in the leakage + insufficient_n
 * tables — were 12px and squished. */
.ck-panel-body td[style*="font-size:12px"]{font-size:13px !important;}
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
.rg-leak-warning{color:#b8732a;background:#fff;border-color:#b8732a;}
.rg-leak-ok{color:#0a8a5f;background:#fff;border-color:#0a8a5f;}
.rg-leak-info{color:var(--sc-text-faint,#7a8699);background:#fff;
border-color:var(--sc-rule,#d6cfc0);}
/* Transitive chip — small mono pill that sits next to a
 * FORMULA_RELATED badge when the verdict came from the multi-hop
 * atomic-input walk (PR #248) rather than a 1-hop direct shared
 * input. Subtle teal-ink tone so partners can read the distinction
 * without the chip competing with the verdict badge itself. */
.rg-leak-transitive-chip{display:inline-block;margin-left:6px;
padding:1px 6px;font-family:var(--sc-mono,monospace);font-size:9px;
font-weight:600;letter-spacing:0.06em;text-transform:uppercase;
color:var(--sc-teal-ink,#155752);background:var(--sc-parchment,#f2ede3);
border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;
cursor:help;}
.rg-influence-badge{display:inline-block;padding:2px 8px;
font-family:var(--sc-mono,monospace);font-size:10px;font-weight:600;
letter-spacing:0.04em;border-radius:2px;border:1px solid transparent;}
.rg-influence-legitimate{color:var(--sc-teal-ink,#155752);
background:#fff;border-color:var(--sc-teal-ink,#155752);}
.rg-influence-opportunity{color:#0a8a5f;background:#fff;
border-color:#0a8a5f;}
.rg-influence-data-issue{color:#b5321e;background:#fff;
border-color:#b5321e;}
.rg-influence-high{color:#b8732a;background:#fff;
border-color:#b8732a;}
.rg-influence-ok{color:var(--sc-text-faint,#7a8699);background:#fff;
border-color:var(--sc-rule,#d6cfc0);}
.rg-influence-info{color:var(--sc-text-faint,#7a8699);background:#fff;
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
    # Unmissable red banner — user reported R²=83% on a fit with 4
    # known-leaky features still in. The inline panel warning isn't
    # loud enough; a banner above the source selector tells the
    # partner the inflated R² has a known cause and links the toggle.
    leakage_banner = ""
    if leak_count > 0 and not drop_leakage:
        leakage_banner = (
            '<div class="rg-leakage-banner">'
            '<span class="rg-leakage-banner-tag">⚠ LEAKAGE</span>'
            '<span class="rg-leakage-banner-text">'
            f'<strong>{leak_count} leaky feature'
            f'{"s" if leak_count != 1 else ""}</strong> '
            'still in the fit — R² is inflated by features '
            'mathematically derived from the target (revenue per '
            'bed, operating margin, net-to-gross ratio, …). Toggle '
            '<strong>Drop leakage features</strong> in the Regression '
            'Inputs above to see the honest fit.'
            '</span>'
            '</div>'
        )

    # Amber sibling — FORMULA_RELATED features share atomic inputs
    # with the target without being direct leaks. R² is still
    # softly inflated by the shared denominator/numerator, but it's
    # not the "fitting y ~ y/x" critical case. Surfaces only when
    # there are no critical leaks (otherwise the red banner already
    # covers the inflated-R² story); avoids stacking two near-
    # identical warnings.
    formula_related_banner = ""
    if (
        formula_related_count > 0
        and leak_count == 0
        and not drop_leakage
    ):
        formula_related_banner = (
            '<div class="rg-leakage-banner warn">'
            '<span class="rg-leakage-banner-tag">⚠ FORMULA-RELATED</span>'
            '<span class="rg-leakage-banner-text">'
            f'<strong>{formula_related_count} accounting-cousin '
            f'feature{"s" if formula_related_count != 1 else ""}</strong> '
            'in the fit — these aren\'t direct leaks but share '
            'atomic inputs with the target (e.g. operating margin '
            'vs. net-to-gross ratio both involve NPR + opex), so '
            'R² is softly inflated. Toggle <strong>Drop leakage '
            'features (strict)</strong> in the Regression Inputs '
            'to also drop these.'
            '</span>'
            '</div>'
        )

    body = (
        f'{rg_styles}{intro}{diagnostic_banner}{source_selector}'
        f'{leakage_banner}{formula_related_banner}'
        f'{leakage_section}{cv_section}{cluster_section}'
        f'{buyability_section}{segmented_section}'
        f'{kpis}{multicollinearity_banner}{intercept_section}'
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
    if cv:
        subtitle_bits.append("+CV")
    if cluster:
        subtitle_bits.append(f"+cluster(k={cluster_k})")
    if buyability:
        subtitle_bits.append("+buyability")
    subtitle_bits.append(f"{sig_count} significant")
    return chartis_shell(
        body, "Regression Analysis",
        active_nav="/portfolio/regression",
        subtitle=" | ".join(subtitle_bits),
    )
