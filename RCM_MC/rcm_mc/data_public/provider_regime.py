"""Provider operating-regime classification for Medicare market analytics.

Ported and cleaned from cms_api_advisory_analytics.py (DrewThomas09/cms_medicare).
Classifies provider types into five investment postures based on growth and volatility:

    durable_growth     — high CAGR, low volatility  → buy/hold
    emerging_volatile  — high CAGR, high volatility → selective / monitor
    steady_compounders — moderate growth, low vol   → core portfolio
    stagnant           — low/zero growth, low vol   → value-add only
    declining_risk     — negative growth, high vol  → avoid / exit

Public API:
    yearly_trends(df)                    -> DataFrame
    provider_volatility(trends)          -> DataFrame
    provider_momentum_profile(trends)    -> DataFrame
    growth_volatility_watchlist(vol)     -> DataFrame
    provider_regime_classification(mom, vol) -> DataFrame
    regime_table(regimes)                -> str
"""
from __future__ import annotations

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_numeric_cols(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


# ---------------------------------------------------------------------------
# Trend computation
# ---------------------------------------------------------------------------

def yearly_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate CMS payment data to provider-type/year and compute YoY growth.

    Requires columns: year, provider_type, total_medicare_payment_amt
    Optional: total_services, total_unique_benes
    """
    if df.empty or not {"year", "provider_type", "total_medicare_payment_amt"}.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _to_numeric_cols(work, ["year", "total_medicare_payment_amt", "total_services", "total_unique_benes"])
    work = work.dropna(subset=["year", "provider_type", "total_medicare_payment_amt"])
    if work.empty:
        return pd.DataFrame()

    agg_cols = [c for c in ["total_medicare_payment_amt", "total_services", "total_unique_benes"]
                if c in work.columns]
    grouped = (
        work.groupby(["year", "provider_type"], as_index=False)[agg_cols]
        .sum()
        .sort_values(["provider_type", "year"])
    )

    grouped["payment_yoy_pct"] = grouped.groupby("provider_type")["total_medicare_payment_amt"].pct_change()
    if "total_services" in grouped.columns:
        grouped["services_yoy_pct"] = grouped.groupby("provider_type")["total_services"].pct_change()
    if "total_unique_benes" in grouped.columns:
        grouped["bene_yoy_pct"] = grouped.groupby("provider_type")["total_unique_benes"].pct_change()
    grouped["payment_yoy_accel"] = grouped.groupby("provider_type")["payment_yoy_pct"].diff()

    return grouped.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------

def provider_volatility(trends: pd.DataFrame) -> pd.DataFrame:
    """Standard deviation of YoY growth — separates stable from erratic providers."""
    if trends.empty:
        return pd.DataFrame()

    vol = (
        trends.groupby("provider_type", as_index=False)
        .agg(
            yoy_payment_volatility=("payment_yoy_pct", "std"),
            avg_payment_growth=("payment_yoy_pct", "mean"),
            last_payment_growth=("payment_yoy_pct", "last"),
        )
        .sort_values("yoy_payment_volatility", ascending=False)
        .reset_index(drop=True)
    )
    return vol


# ---------------------------------------------------------------------------
# Momentum profile
# ---------------------------------------------------------------------------

def provider_momentum_profile(trends: pd.DataFrame, min_years: int = 3) -> pd.DataFrame:
    """Growth consistency profile — separates durable trends from single-year spikes.

    consistency_score weights:
        0.45 × positive_yoy_share (reliability of positive growth)
        0.25 × yoy_growth_median  (central tendency)
        0.20 × growth_cagr        (compounding power)
       -0.10 × yoy_growth_volatility (penalise noise)
    """
    if trends.empty:
        return pd.DataFrame()

    work = trends.copy()
    _to_numeric_cols(work, ["payment_yoy_pct", "payment_yoy_accel", "total_medicare_payment_amt"])

    grouped = (
        work.groupby("provider_type", as_index=False)
        .agg(
            observed_years=("year", "nunique"),
            positive_yoy_share=(
                "payment_yoy_pct",
                lambda s: float((s > 0).mean()) if s.notna().any() else float("nan"),
            ),
            yoy_growth_median=("payment_yoy_pct", "median"),
            yoy_growth_volatility=("payment_yoy_pct", "std"),
            avg_yoy_accel=("payment_yoy_accel", "mean"),
            first_payment=("total_medicare_payment_amt", "first"),
            latest_payment=("total_medicare_payment_amt", "last"),
        )
    )

    grouped = grouped[grouped["observed_years"] >= min_years]
    if grouped.empty:
        return grouped

    grouped["growth_cagr"] = (
        (grouped["latest_payment"] / grouped["first_payment"].replace(0, float("nan")))
        ** (1 / (grouped["observed_years"] - 1).clip(lower=1))
    ) - 1

    grouped["consistency_score"] = (
        grouped["positive_yoy_share"].fillna(0) * 0.45
        + grouped["yoy_growth_median"].fillna(0) * 0.25
        + grouped["growth_cagr"].fillna(0) * 0.20
        - grouped["yoy_growth_volatility"].fillna(0) * 0.10
    )
    grouped["consistency_percentile"] = grouped["consistency_score"].rank(pct=True)
    return grouped.sort_values("consistency_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def growth_volatility_watchlist(
    volatility: pd.DataFrame,
    min_growth: float = 0.05,
    max_volatility: float = 0.35,
) -> pd.DataFrame:
    """Flag providers by growth-to-risk profile.

    Buckets:
        priority   — last growth ≥ min_growth AND vol ≤ max_volatility
        high_risk  — last growth < 0 AND vol > max_volatility
        monitor    — everything else
    """
    if volatility.empty:
        return pd.DataFrame()

    out = volatility.copy()
    _to_numeric_cols(out, ["last_payment_growth", "yoy_payment_volatility"])

    out["watchlist_bucket"] = "monitor"
    out.loc[
        (out["last_payment_growth"] >= min_growth)
        & (out["yoy_payment_volatility"] <= max_volatility),
        "watchlist_bucket",
    ] = "priority"
    out.loc[
        (out["last_payment_growth"] < 0)
        & (out["yoy_payment_volatility"] > max_volatility),
        "watchlist_bucket",
    ] = "high_risk"

    out["growth_to_risk"] = out["last_payment_growth"] / out["yoy_payment_volatility"].replace(0, float("nan"))
    bucket_order = pd.CategoricalDtype(["priority", "monitor", "high_risk"], ordered=True)
    out["watchlist_bucket"] = out["watchlist_bucket"].astype(bucket_order)
    return out.sort_values(["watchlist_bucket", "growth_to_risk"], ascending=[True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------

REGIME_ORDER = ["durable_growth", "steady_compounders", "emerging_volatile", "stagnant", "declining_risk"]

def provider_regime_classification(
    momentum: pd.DataFrame,
    volatility: pd.DataFrame,
    strong_growth_threshold: float = 0.12,
    weak_growth_threshold: float = 0.0,
    high_vol_threshold: float = 0.35,
) -> pd.DataFrame:
    """Classify provider types into investment-posture regimes.

    Logic (growth_proxy × vol_proxy matrix):
        growth ≥ strong AND vol ≤ high → durable_growth
        growth ≥ strong AND vol >  high → emerging_volatile
        growth <  weak  AND vol ≤ high → stagnant
        growth <  weak  AND vol >  high → declining_risk
        else                            → steady_compounders

    regime_rank_score = 0.50×growth + 0.30×consistency - 0.20×vol
    """
    if momentum.empty and volatility.empty:
        return pd.DataFrame()

    base = pd.DataFrame()
    if not momentum.empty:
        keep = [c for c in ["provider_type", "consistency_score", "growth_cagr",
                             "positive_yoy_share", "yoy_growth_volatility"]
                if c in momentum.columns]
        base = momentum[keep].copy()

    if not volatility.empty:
        vkeep = [c for c in ["provider_type", "last_payment_growth", "yoy_payment_volatility"]
                 if c in volatility.columns]
        vdf = volatility[vkeep].copy()
        base = vdf if base.empty else base.merge(vdf, on="provider_type", how="outer")

    if base.empty or "provider_type" not in base.columns:
        return pd.DataFrame()

    for col in ["growth_cagr", "last_payment_growth", "yoy_payment_volatility", "consistency_score"]:
        if col not in base.columns:
            base[col] = float("nan")
        base[col] = pd.to_numeric(base[col], errors="coerce")

    growth_proxy = base["last_payment_growth"].fillna(base["growth_cagr"])
    vol_col = "yoy_payment_volatility" if "yoy_payment_volatility" in base.columns else "yoy_growth_volatility"
    vol_proxy = base[vol_col] if vol_col in base.columns else pd.Series(float("nan"), index=base.index)

    base["regime"] = "steady_compounders"
    base.loc[(growth_proxy >= strong_growth_threshold) & (vol_proxy > high_vol_threshold), "regime"] = "emerging_volatile"
    base.loc[(growth_proxy >= strong_growth_threshold) & (vol_proxy <= high_vol_threshold), "regime"] = "durable_growth"
    base.loc[(growth_proxy < weak_growth_threshold) & (vol_proxy <= high_vol_threshold), "regime"] = "stagnant"
    base.loc[(growth_proxy < weak_growth_threshold) & (vol_proxy > high_vol_threshold), "regime"] = "declining_risk"

    base["regime_rank_score"] = (
        0.50 * growth_proxy.fillna(0)
        + 0.30 * base["consistency_score"].fillna(0)
        - 0.20 * vol_proxy.fillna(0)
    )
    regime_order = pd.CategoricalDtype(REGIME_ORDER, ordered=True)
    base["regime"] = base["regime"].astype(regime_order)
    return base.sort_values(["regime", "regime_rank_score"], ascending=[True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Formatted output
# ---------------------------------------------------------------------------

_REGIME_LABEL = {
    "durable_growth":     "Durable Growth     ★★★★★",
    "steady_compounders": "Steady Compounders ★★★★",
    "emerging_volatile":  "Emerging / Volatile ★★★",
    "stagnant":           "Stagnant           ★★",
    "declining_risk":     "Declining / Risk   ★",
}


def regime_table(regimes: pd.DataFrame, top_n: int = 30) -> str:
    """Return a formatted text table of provider regimes."""
    if regimes.empty:
        return "No regime data available.\n"

    lines = ["Provider Regime Classification", "=" * 72]
    header = f"{'Provider Type':<38} {'Regime':<22} {'Score':>8}"
    lines.append(header)
    lines.append("-" * 72)

    for _, row in regimes.head(top_n).iterrows():
        regime_str = str(row.get("regime", ""))
        label = _REGIME_LABEL.get(regime_str, regime_str)
        score = row.get("regime_rank_score", float("nan"))
        score_str = f"{score:.3f}" if not (isinstance(score, float) and score != score) else "  N/A"
        pt = str(row.get("provider_type", ""))[:37]
        lines.append(f"{pt:<38} {label:<22} {score_str:>8}")

    lines.append("=" * 72)
    return "\n".join(lines) + "\n"
