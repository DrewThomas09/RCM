"""CMS provider-state opportunity scoring and benchmark flagging.

Ported and cleaned from cms_api_advisory_analytics.py (DrewThomas09/cms_medicare).
Identifies high-opportunity provider-state combinations and benchmark anomalies
for use in PE regional expansion screening.

Public API:
    enrich_features(df)                      -> DataFrame  (adds computed cols)
    state_provider_opportunities(df, ...)    -> DataFrame  (regional opp scores)
    provider_state_benchmark_flags(df, ...)  -> DataFrame  (high/low price flags)
    provider_screen(df)                      -> DataFrame  (top-line market share screen)
    opportunity_table(df)                    -> str        (formatted text table)
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_numeric(df: pd.DataFrame, cols: List[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


def _percentile_rank(series: pd.Series) -> pd.Series:
    return series.rank(pct=True)


def _norm(s: pd.Series) -> pd.Series:
    """Min-max normalize a series to [0, 1]."""
    rng = s.max() - s.min()
    if pd.isna(rng) or rng == 0:
        return pd.Series(0.0, index=s.index)
    return (s - s.min()) / rng


# ---------------------------------------------------------------------------
# Feature enrichment
# ---------------------------------------------------------------------------

def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived per-service and per-beneficiary payment columns.

    Adds (where source columns are present):
        payment_per_service  = total_medicare_payment_amt / total_services
        payment_per_bene     = total_medicare_payment_amt / total_unique_benes
        charge_to_payment_ratio = total_submitted_chrg_amt / total_medicare_payment_amt
    """
    work = df.copy()
    _to_numeric(work, [
        "total_medicare_payment_amt", "total_services",
        "total_unique_benes", "total_submitted_chrg_amt",
    ])

    if "total_services" in work.columns and "payment_per_service" not in work.columns:
        work["payment_per_service"] = (
            work["total_medicare_payment_amt"]
            / work["total_services"].replace(0, float("nan"))
        )

    if "total_unique_benes" in work.columns and "payment_per_bene" not in work.columns:
        work["payment_per_bene"] = (
            work["total_medicare_payment_amt"]
            / work["total_unique_benes"].replace(0, float("nan"))
        )

    if "total_submitted_chrg_amt" in work.columns and "charge_to_payment_ratio" not in work.columns:
        work["charge_to_payment_ratio"] = (
            work["total_submitted_chrg_amt"]
            / work["total_medicare_payment_amt"].replace(0, float("nan"))
        )

    return work


# ---------------------------------------------------------------------------
# Regional opportunity scoring
# ---------------------------------------------------------------------------

def state_provider_opportunities(
    df: pd.DataFrame,
    min_rows: int = 5,
) -> pd.DataFrame:
    """Score provider-type × state combinations by PE expansion opportunity.

    regional_opportunity_score components (weights sum to 1.00):
        0.45 × regional_scale_score   (log total Medicare payment)
        0.35 × regional_margin_score  (median payment per service)
        0.20 × regional_acuity_score  (median beneficiary risk score)

    Lower min_rows (default=5 vs source=20) suits smaller test datasets.
    """
    required = {"provider_type", "state", "total_medicare_payment_amt"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = enrich_features(df)
    _to_numeric(work, ["total_medicare_payment_amt", "payment_per_service", "beneficiary_average_risk_score"])

    agg_map: dict = {
        "row_count": ("provider_type", "count"),
        "total_payment": ("total_medicare_payment_amt", "sum"),
    }
    if "payment_per_service" in work.columns:
        agg_map["median_payment_per_service"] = ("payment_per_service", "median")
    if "beneficiary_average_risk_score" in work.columns:
        agg_map["median_risk"] = ("beneficiary_average_risk_score", "median")

    grouped = work.groupby(["provider_type", "state"], as_index=False).agg(**agg_map)
    grouped = grouped[grouped["row_count"] >= min_rows]
    if grouped.empty:
        return grouped

    grouped["regional_scale_score"] = _norm(np.log1p(grouped["total_payment"]))

    if "median_payment_per_service" in grouped.columns:
        grouped["regional_margin_score"] = _norm(grouped["median_payment_per_service"])
    else:
        grouped["regional_margin_score"] = 0.0

    if "median_risk" in grouped.columns:
        grouped["regional_acuity_score"] = _norm(grouped["median_risk"])
    else:
        grouped["regional_acuity_score"] = 0.0

    grouped["regional_opportunity_score"] = (
        0.45 * grouped["regional_scale_score"]
        + 0.35 * grouped["regional_margin_score"]
        + 0.20 * grouped["regional_acuity_score"]
    )
    grouped["regional_opportunity_percentile"] = _percentile_rank(grouped["regional_opportunity_score"])
    return grouped.sort_values("regional_opportunity_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Benchmark flags
# ---------------------------------------------------------------------------

def provider_state_benchmark_flags(
    df: pd.DataFrame,
    z_threshold: float = 1.5,
    min_rows: int = 5,
) -> pd.DataFrame:
    """Flag provider-state combos with unusually high/low payment vs peer providers.

    benchmark_flag values: 'high_price', 'normal', 'low_price'
    Based on Z-score of state median vs provider-type national peer median.
    """
    work = enrich_features(df)

    if not {"provider_type", "state", "payment_per_service"}.issubset(work.columns):
        return pd.DataFrame()

    _to_numeric(work, ["payment_per_service", "total_medicare_payment_amt"])

    provider_peer = (
        work.groupby("provider_type", as_index=False)["payment_per_service"]
        .agg(peer_median="median", peer_std="std")
    )

    grouped = (
        work.groupby(["provider_type", "state"], as_index=False)
        .agg(
            row_count=("provider_type", "count"),
            state_median_pps=("payment_per_service", "median"),
            state_total_payment=("total_medicare_payment_amt", "sum"),
        )
    )
    grouped = grouped[grouped["row_count"] >= min_rows]
    if grouped.empty:
        return grouped

    merged = grouped.merge(provider_peer, on="provider_type", how="left")
    merged["peer_std"] = merged["peer_std"].replace(0, float("nan"))
    merged["service_price_z"] = (
        (merged["state_median_pps"] - merged["peer_median"]) / merged["peer_std"]
    )

    merged["benchmark_flag"] = "normal"
    merged.loc[merged["service_price_z"] >= z_threshold, "benchmark_flag"] = "high_price"
    merged.loc[merged["service_price_z"] <= -z_threshold, "benchmark_flag"] = "low_price"
    bench_order = pd.CategoricalDtype(["high_price", "normal", "low_price"], ordered=True)
    merged["benchmark_flag"] = merged["benchmark_flag"].astype(bench_order)
    return merged.sort_values(["benchmark_flag", "service_price_z"], ascending=[True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Provider-level market screen
# ---------------------------------------------------------------------------

def provider_screen(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate CMS rows to provider-type level with market-share computation.

    Returns one row per provider_type with:
        total_payment, total_services, total_benes,
        market_share, opportunity_score, opportunity_percentile
    """
    if "provider_type" not in df.columns:
        return pd.DataFrame()

    work = enrich_features(df)
    _to_numeric(work, [
        "total_services", "total_unique_benes",
        "total_medicare_payment_amt", "payment_per_service", "payment_per_bene",
    ])

    grouped = (
        work.groupby("provider_type", dropna=False)
        .agg(
            row_count=("provider_type", "count"),
            total_services=("total_services", "sum"),
            total_benes=("total_unique_benes", "sum"),
            total_payment=("total_medicare_payment_amt", "sum"),
            median_pps=("payment_per_service", "median"),
            median_ppb=("payment_per_bene", "median"),
        )
        .reset_index()
    )

    market_total = grouped["total_payment"].sum()
    grouped["market_share"] = grouped["total_payment"] / market_total if market_total > 0 else 0.0

    grouped["opportunity_score"] = (
        0.50 * _norm(np.log1p(grouped["total_payment"]))
        + 0.30 * _norm(grouped["market_share"])
        + 0.20 * _norm(grouped["median_pps"].fillna(0))
    )
    grouped["opportunity_percentile"] = _percentile_rank(grouped["opportunity_score"])
    return grouped.sort_values("opportunity_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Formatted output
# ---------------------------------------------------------------------------

def opportunity_table(df: pd.DataFrame, top_n: int = 20) -> str:
    """Formatted text table of regional opportunity scores."""
    if df.empty:
        return "No opportunity data available.\n"

    has_state = "state" in df.columns
    lines = ["Provider-State Opportunity Scores" if has_state else "Provider Opportunity Scores", "=" * 68]

    if has_state:
        header = f"{'Provider Type':<35} {'State':<6} {'Score':>8} {'Pct':>6}"
    else:
        header = f"{'Provider Type':<40} {'Mkt Share':>10} {'Score':>8} {'Pct':>6}"
    lines.append(header)
    lines.append("-" * 68)

    score_col = "regional_opportunity_score" if has_state else "opportunity_score"
    pct_col = "regional_opportunity_percentile" if has_state else "opportunity_percentile"

    for _, row in df.head(top_n).iterrows():
        score = row.get(score_col, float("nan"))
        pct = row.get(pct_col, float("nan"))
        score_s = f"{score:.3f}" if score == score else "  N/A"
        pct_s = f"{pct:.0%}" if pct == pct else "  N/A"

        if has_state:
            pt = str(row.get("provider_type", ""))[:34]
            state = str(row.get("state", ""))[:5]
            lines.append(f"{pt:<35} {state:<6} {score_s:>8} {pct_s:>6}")
        else:
            pt = str(row.get("provider_type", ""))[:39]
            mkt = row.get("market_share", float("nan"))
            mkt_s = f"{mkt:.1%}" if mkt == mkt else "  N/A"
            lines.append(f"{pt:<40} {mkt_s:>10} {score_s:>8} {pct_s:>6}")

    lines.append("=" * 68)
    return "\n".join(lines) + "\n"
