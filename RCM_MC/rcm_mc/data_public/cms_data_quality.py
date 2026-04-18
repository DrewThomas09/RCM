"""CMS data quality and run-summary reporting.

Ported and cleaned from cms_api_advisory_analytics.py (DrewThomas09/cms_medicare).
Provides column-level missingness audit and machine-readable run summaries for
CMS analytics runs.

Public API:
    data_quality_report(df)         -> DataFrame   (column-level missingness)
    cms_run_summary(report, ...)    -> dict         (machine-readable summary)
    quality_report_text(dq_df)      -> str          (formatted text table)
    winsorize_metrics(df, quantile) -> DataFrame    (clip heavy-tailed columns)
"""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Data quality audit
# ---------------------------------------------------------------------------

def data_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Column-level missingness and zero-rate summary for auditability.

    Returns one row per column with: dtype, null_pct, zero_pct, nunique.
    Sorted descending by null_pct so problem columns float to the top.
    """
    if df.empty:
        return pd.DataFrame(columns=["column", "dtype", "null_pct", "zero_pct", "nunique"])

    rows = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        null_pct = float(s.isna().sum() / n)
        zero_pct = 0.0
        if pd.api.types.is_numeric_dtype(s):
            zero_pct = float((pd.to_numeric(s, errors="coerce").fillna(0) == 0).sum() / n)
        rows.append(
            {
                "column": col,
                "dtype": str(s.dtype),
                "null_pct": null_pct,
                "zero_pct": zero_pct,
                "nunique": int(s.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows).sort_values(["null_pct", "zero_pct"], ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Run summary
# ---------------------------------------------------------------------------

def cms_run_summary(
    report: Any,  # MarketAnalysisReport
    screen: pd.DataFrame = None,
    benchmark_flags: pd.DataFrame = None,
    investability: pd.DataFrame = None,
) -> Dict[str, Any]:
    """Machine-readable CMS analytics run summary for downstream orchestration.

    Accepts a MarketAnalysisReport plus optional supplementary DataFrames.
    All values JSON-serialisable (no pandas objects in output).
    """
    from .cms_market_analysis import MarketAnalysisReport

    if benchmark_flags is None:
        benchmark_flags = pd.DataFrame()
    if investability is None:
        investability = pd.DataFrame()
    if screen is None:
        screen = pd.DataFrame()

    summary: Dict[str, Any] = {
        "year": report.year,
        "state_filter": report.state_filter,
        "provider_type_filter": report.provider_type_filter,
        "row_count": report.row_count,
        "errors": report.errors,
    }

    # Concentration
    if not report.concentration.empty:
        summary["concentration_markets"] = int(len(report.concentration))
        top_conc = report.concentration.iloc[0]
        summary["highest_hhi_state"] = str(top_conc.get("state", ""))
        summary["highest_hhi"] = float(top_conc.get("hhi", 0))
    else:
        summary["concentration_markets"] = 0

    # Regime
    if not report.regimes.empty and "regime" in report.regimes.columns:
        durable = report.regimes[report.regimes["regime"].astype(str) == "durable_growth"]
        declining = report.regimes[report.regimes["regime"].astype(str) == "declining_risk"]
        summary["durable_growth_count"] = int(len(durable))
        summary["declining_risk_count"] = int(len(declining))
        summary["top_durable_provider"] = (
            str(durable.iloc[0]["provider_type"]) if not durable.empty else None
        )
    else:
        summary["durable_growth_count"] = 0
        summary["declining_risk_count"] = 0
        summary["top_durable_provider"] = None

    # Watchlist
    if not report.watchlist.empty and "watchlist_bucket" in report.watchlist.columns:
        priority = report.watchlist[report.watchlist["watchlist_bucket"] == "priority"]
        high_risk = report.watchlist[report.watchlist["watchlist_bucket"] == "high_risk"]
        summary["priority_watchlist_count"] = int(len(priority))
        summary["high_risk_watchlist_count"] = int(len(high_risk))
    else:
        summary["priority_watchlist_count"] = 0
        summary["high_risk_watchlist_count"] = 0

    # State fit
    if not report.portfolio_fit.empty and "state_fit_score" in report.portfolio_fit.columns:
        top_fit = report.portfolio_fit.iloc[0]
        summary["top_fit_state"] = str(top_fit.get("state", ""))
        summary["top_fit_score"] = float(top_fit.get("state_fit_score", 0))
    else:
        summary["top_fit_state"] = None
        summary["top_fit_score"] = None

    # Geo dependency
    if not report.geo_dependency.empty and "geo_dependency_flag" in report.geo_dependency.columns:
        dep_count = int(report.geo_dependency["geo_dependency_flag"].sum())
        summary["high_geo_dependency_count"] = dep_count
    else:
        summary["high_geo_dependency_count"] = 0

    # Benchmark flags
    if not benchmark_flags.empty and "benchmark_flag" in benchmark_flags.columns:
        flagged = benchmark_flags[benchmark_flags["benchmark_flag"].astype(str) != "normal"]
        summary["benchmark_flag_count"] = int(len(flagged))
    else:
        summary["benchmark_flag_count"] = 0

    # Investability
    if not investability.empty and "investability_score" in investability.columns:
        top_inv = investability.iloc[0]
        summary["top_investability_provider"] = str(top_inv.get("provider_type", ""))
        summary["top_investability_score"] = float(top_inv.get("investability_score", 0))
    else:
        summary["top_investability_provider"] = None
        summary["top_investability_score"] = None

    # Screen
    if not screen.empty and "opportunity_score" in screen.columns:
        summary["provider_type_count"] = int(len(screen))
        summary["top_opportunity_provider"] = str(screen.iloc[0].get("provider_type", ""))
    else:
        summary["provider_type_count"] = int(
            len(report.regimes) if not report.regimes.empty else 0
        )
        summary["top_opportunity_provider"] = None

    return summary


# ---------------------------------------------------------------------------
# Winsorization
# ---------------------------------------------------------------------------

def winsorize_metrics(
    df: pd.DataFrame,
    upper_quantile: float = 0.99,
) -> pd.DataFrame:
    """Clip heavy-tailed payment columns to improve comparability.

    Clips: payment_per_service, payment_per_bene, charge_to_payment_ratio
    at the given upper_quantile. Values below the quantile are unchanged.
    """
    if upper_quantile >= 1.0:
        return df.copy()

    out = df.copy()
    for col in ["payment_per_service", "payment_per_bene", "charge_to_payment_ratio"]:
        if col in out.columns:
            numeric = pd.to_numeric(out[col], errors="coerce")
            cap = numeric.quantile(upper_quantile)
            out[col] = numeric.clip(upper=cap)
    return out


# ---------------------------------------------------------------------------
# Formatted output
# ---------------------------------------------------------------------------

def quality_report_text(dq_df: pd.DataFrame, max_rows: int = 25) -> str:
    """Formatted text table of the data quality report."""
    if dq_df.empty:
        return "No data quality information available.\n"

    lines = ["CMS Data Quality Report", "=" * 64]
    header = f"{'Column':<38} {'Null%':>7} {'Zero%':>7} {'Uniq':>6}"
    lines.append(header)
    lines.append("-" * 64)

    for _, row in dq_df.head(max_rows).iterrows():
        col = str(row.get("column", ""))[:37]
        null_p = row.get("null_pct", 0)
        zero_p = row.get("zero_pct", 0)
        nu = int(row.get("nunique", 0))
        flag = " ⚠" if null_p > 0.20 else ""
        lines.append(f"{col:<38} {null_p:>6.1%} {zero_p:>7.1%} {nu:>6}{flag}")

    lines.append("=" * 64)
    return "\n".join(lines) + "\n"
