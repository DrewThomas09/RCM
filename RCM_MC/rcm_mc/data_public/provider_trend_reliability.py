"""Provider trend reliability scoring — statistical consistency of CMS payment growth.

Ported and cleaned from DrewThomas09/cms_medicare:
  provider_trend_reliability(), growth_volatility_watchlist(),
  provider_momentum_profile(), provider_trend_shift()

These functions score how dependable a provider type's payment trend is
for investment decision support.

Public API:
    provider_trend_reliability(trends_df, min_obs)    -> DataFrame
    growth_volatility_watchlist(vol_df, ...)          -> DataFrame
    provider_momentum_profile(trends_df, min_years)   -> DataFrame
    provider_trend_shift(trends_df, base_year, comp_year) -> DataFrame
    reliability_table(rel_df, max_rows)               -> str
    watchlist_text(watchlist_df)                      -> str
"""
from __future__ import annotations

from typing import Any, Optional


def provider_trend_reliability(
    trends_df: Any,
    min_observations: int = 3,
) -> Any:
    """Score statistical reliability of each provider type's payment growth trend.

    Args:
        trends_df:        DataFrame with columns: provider_type, payment_yoy_pct,
                          services_yoy_pct, bene_yoy_pct, payment_yoy_accel
                          (output of yearly_trends() from provider_regime.py)
        min_observations: Minimum YoY observations required (drop below)

    Returns:
        DataFrame sorted by reliability_score descending, with columns:
        provider_type, yoy_obs_count, yoy_growth_mean, yoy_growth_std,
        yoy_growth_median, positive_growth_share, acceleration_mean,
        growth_signal_to_noise, reliability_score, reliability_percentile
    """
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        raise RuntimeError("pandas and numpy required for provider_trend_reliability")

    if trends_df is None or (hasattr(trends_df, 'empty') and trends_df.empty):
        return pd.DataFrame()

    if "provider_type" not in trends_df.columns:
        return pd.DataFrame()

    work = trends_df.copy()

    # Ensure numeric
    for col in ["payment_yoy_pct", "services_yoy_pct", "bene_yoy_pct", "payment_yoy_accel"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    # Add payment_yoy_pct if missing but we have total_medicare_payment_amt
    if "payment_yoy_pct" not in work.columns and "total_medicare_payment_amt" in work.columns:
        pay_col = "total_medicare_payment_amt"
        work[pay_col] = pd.to_numeric(work[pay_col], errors="coerce")
        if "year" in work.columns:
            work = work.sort_values(["provider_type", "year"])
            work["payment_yoy_pct"] = work.groupby("provider_type")[pay_col].pct_change()
            work["payment_yoy_accel"] = work.groupby("provider_type")["payment_yoy_pct"].diff()

    if "payment_yoy_pct" not in work.columns:
        return pd.DataFrame()

    rel = (
        work.groupby("provider_type", as_index=False)
        .agg(
            yoy_obs_count=("payment_yoy_pct", lambda s: int(s.notna().sum())),
            yoy_growth_mean=("payment_yoy_pct", "mean"),
            yoy_growth_std=("payment_yoy_pct", "std"),
            yoy_growth_median=("payment_yoy_pct", "median"),
            positive_growth_share=(
                "payment_yoy_pct",
                lambda s: float((s > 0).mean()) if s.notna().any() else np.nan,
            ),
            acceleration_mean=("payment_yoy_accel", "mean") if "payment_yoy_accel" in work.columns
            else ("payment_yoy_pct", "mean"),
        )
    )

    rel = rel[rel["yoy_obs_count"] >= min_observations].copy()
    if rel.empty:
        return rel

    rel["growth_signal_to_noise"] = (
        rel["yoy_growth_mean"] / rel["yoy_growth_std"].replace(0, np.nan)
    )

    # Reliability score: signal-to-noise, consistency, median, penalize volatility
    rel["reliability_score"] = (
        0.40 * rel["growth_signal_to_noise"].fillna(0)
        + 0.30 * rel["positive_growth_share"].fillna(0)
        + 0.20 * rel["yoy_growth_median"].fillna(0)
        - 0.10 * rel["yoy_growth_std"].fillna(0)
    )

    # Percentile rank
    rel["reliability_percentile"] = rel["reliability_score"].rank(pct=True).round(3)

    return rel.sort_values("reliability_score", ascending=False).reset_index(drop=True)


def growth_volatility_watchlist(
    volatility_df: Any,
    min_growth: float = 0.05,
    max_volatility: float = 0.35,
) -> Any:
    """Flag providers by growth/risk profile.

    Buckets: priority (good growth + low vol), monitor (in between), high_risk.

    Args:
        volatility_df:  DataFrame with yoy_payment_volatility and avg/last_payment_growth
        min_growth:     Minimum growth rate for priority bucket
        max_volatility: Maximum volatility for priority bucket
    """
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("pandas required for growth_volatility_watchlist")

    if volatility_df is None or (hasattr(volatility_df, 'empty') and volatility_df.empty):
        return pd.DataFrame()

    out = volatility_df.copy()
    for col in ["last_payment_growth", "yoy_payment_volatility", "avg_payment_growth"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    growth_col = "last_payment_growth" if "last_payment_growth" in out.columns else "avg_payment_growth"
    vol_col = "yoy_payment_volatility"

    if growth_col not in out.columns or vol_col not in out.columns:
        return pd.DataFrame()

    out["watchlist_bucket"] = "monitor"
    out.loc[
        (out[growth_col] >= min_growth) & (out[vol_col] <= max_volatility),
        "watchlist_bucket",
    ] = "priority"
    out.loc[
        (out[growth_col] < 0) & (out[vol_col] > max_volatility),
        "watchlist_bucket",
    ] = "high_risk"

    out["growth_to_risk"] = out[growth_col] / out[vol_col].replace(0, float("nan"))

    bucket_order = pd.CategoricalDtype(["priority", "monitor", "high_risk"], ordered=True)
    out["watchlist_bucket"] = out["watchlist_bucket"].astype(bucket_order)
    return out.sort_values(["watchlist_bucket", "growth_to_risk"], ascending=[True, False]).reset_index(drop=True)


def provider_momentum_profile(
    trends_df: Any,
    min_years: int = 3,
) -> Any:
    """Profile growth consistency — separates durable trends from one-year spikes.

    Returns DataFrame with consistency_score, trend_type classification.
    """
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        raise RuntimeError("pandas required for provider_momentum_profile")

    if trends_df is None or (hasattr(trends_df, 'empty') and trends_df.empty):
        return pd.DataFrame()

    work = trends_df.copy()
    for col in ["total_medicare_payment_amt", "payment_yoy_pct"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    # Compute YoY if not already present
    pay_col = None
    for c in ["total_medicare_payment_amt", "tot_mdcr_pymt_amt"]:
        if c in work.columns:
            pay_col = c
            break

    if "payment_yoy_pct" not in work.columns and pay_col and "year" in work.columns:
        work = work.sort_values(["provider_type", "year"])
        work["payment_yoy_pct"] = work.groupby("provider_type")[pay_col].pct_change()

    if "payment_yoy_pct" not in work.columns:
        return pd.DataFrame()

    grouped = (
        work.groupby("provider_type", as_index=False)
        .agg(
            obs_count=("payment_yoy_pct", lambda s: int(s.notna().sum())),
            mean_growth=("payment_yoy_pct", "mean"),
            std_growth=("payment_yoy_pct", "std"),
            min_growth=("payment_yoy_pct", "min"),
            max_growth=("payment_yoy_pct", "max"),
            recent_growth=("payment_yoy_pct", "last"),
            positive_years_pct=("payment_yoy_pct", lambda s: float((s > 0).sum()) / max(s.notna().sum(), 1)),
        )
    )

    grouped = grouped[grouped["obs_count"] >= min_years].copy()
    if grouped.empty:
        return grouped

    # Consistency score: % positive years, low std dev relative to mean
    grouped["consistency_score"] = (
        0.5 * grouped["positive_years_pct"]
        + 0.3 * (grouped["mean_growth"] / grouped["std_growth"].replace(0, np.nan)).fillna(0).clip(-2, 2)
        + 0.2 * (grouped["recent_growth"] / grouped["mean_growth"].replace(0, np.nan)).fillna(1.0).clip(0, 2)
    )

    # Trend type classification
    def classify(row):
        if row["mean_growth"] >= 0.05 and row["positive_years_pct"] >= 0.75:
            return "durable_grower"
        elif row["mean_growth"] >= 0.05 and row["positive_years_pct"] < 0.75:
            return "volatile_grower"
        elif row["mean_growth"] < 0.0:
            return "decliner"
        else:
            return "slow_steady"

    grouped["trend_type"] = grouped.apply(classify, axis=1)
    return grouped.sort_values("consistency_score", ascending=False).reset_index(drop=True)


def provider_trend_shift(
    trends_df: Any,
    baseline_year: Optional[int],
    compare_year: Optional[int],
) -> Any:
    """Compare provider payment levels between two years to spot inflections.

    Returns DataFrame with payment_delta and payment_delta_pct for each
    provider type, sorted by payment_delta descending.
    """
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        raise RuntimeError("pandas required for provider_trend_shift")

    if (trends_df is None or (hasattr(trends_df, 'empty') and trends_df.empty)
            or baseline_year is None or compare_year is None):
        return pd.DataFrame()

    pay_col = None
    for c in ["total_medicare_payment_amt", "tot_mdcr_pymt_amt"]:
        if c in trends_df.columns:
            pay_col = c
            break

    if pay_col is None or "provider_type" not in trends_df.columns:
        return pd.DataFrame()

    work = trends_df.copy()
    work["year"] = pd.to_numeric(work.get("year", pd.Series(dtype=float)), errors="coerce")
    work[pay_col] = pd.to_numeric(work[pay_col], errors="coerce")

    base = (
        work[work["year"] == baseline_year]
        .groupby("provider_type", as_index=False)[pay_col]
        .sum()
        .rename(columns={pay_col: "payment_baseline"})
    )
    comp = (
        work[work["year"] == compare_year]
        .groupby("provider_type", as_index=False)[pay_col]
        .sum()
        .rename(columns={pay_col: "payment_compare"})
    )

    merged = base.merge(comp, on="provider_type", how="inner")
    if merged.empty:
        return merged

    merged["payment_delta"] = merged["payment_compare"] - merged["payment_baseline"]
    merged["payment_delta_pct"] = (
        merged["payment_delta"] / merged["payment_baseline"].replace(0, np.nan)
    )
    merged["abs_delta_rank"] = (
        merged["payment_delta"].abs().rank(ascending=False, method="dense").astype(int)
    )
    return merged.sort_values("payment_delta", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def reliability_table(rel_df: Any, max_rows: int = 20) -> str:
    """Formatted table of reliability scores."""
    if rel_df is None or (hasattr(rel_df, 'empty') and rel_df.empty):
        return "No reliability data"

    lines = [
        f"{'Provider Type':<35} {'Mean Growth':>12} {'Std':>8} {'Pos%':>6} {'Reliability':>12}",
        "-" * 80,
    ]
    for _, row in rel_df.head(max_rows).iterrows():
        pt = str(row.get("provider_type", ""))[:34]
        mg = f"{row.get('yoy_growth_mean', 0):.1%}" if row.get("yoy_growth_mean") is not None else "  —  "
        std = f"{row.get('yoy_growth_std', 0):.1%}" if row.get("yoy_growth_std") is not None else " — "
        pos = f"{row.get('positive_growth_share', 0):.0%}" if row.get("positive_growth_share") is not None else "  —"
        rel = f"{row.get('reliability_score', 0):.3f}" if row.get("reliability_score") is not None else "  —"
        lines.append(f"{pt:<35} {mg:>12} {std:>8} {pos:>6} {rel:>12}")

    return "\n".join(lines) + "\n"


def watchlist_text(watchlist_df: Any, max_rows: int = 20) -> str:
    """Formatted watchlist output."""
    if watchlist_df is None or (hasattr(watchlist_df, 'empty') and watchlist_df.empty):
        return "No watchlist data"

    lines = [
        f"{'Provider Type':<35} {'Bucket':<12} {'Growth':>8} {'Volatility':>12} {'G/R Ratio':>10}",
        "-" * 85,
    ]
    for _, row in watchlist_df.head(max_rows).iterrows():
        pt = str(row.get("provider_type", ""))[:34]
        bucket = str(row.get("watchlist_bucket", ""))
        grw = row.get("last_payment_growth") or row.get("avg_payment_growth")
        grw_s = f"{grw:.1%}" if grw is not None else "  —  "
        vol = row.get("yoy_payment_volatility")
        vol_s = f"{vol:.1%}" if vol is not None else "  —  "
        gr = row.get("growth_to_risk")
        gr_s = f"{gr:.2f}" if gr is not None else "  —"
        lines.append(f"{pt:<35} {bucket:<12} {grw_s:>8} {vol_s:>12} {gr_s:>10}")

    return "\n".join(lines) + "\n"
