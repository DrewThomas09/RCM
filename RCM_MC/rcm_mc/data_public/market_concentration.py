"""Medicare market concentration analytics for PE-style rollup screening.

Ported and cleaned from cms_api_advisory_analytics.py (DrewThomas09/cms_medicare).
Requires pandas; all functions accept a DataFrame produced by cms_api_client and
return DataFrames so callers can chain or export freely.

Public API:
    market_concentration_summary(df)  -> DataFrame  (HHI, CR3, CR5 per state/year)
    provider_geo_dependency(df)       -> DataFrame  (single-state concentration risk)
    state_volatility_summary(df)      -> DataFrame  (YoY payment volatility by state)
    state_growth_summary(df)          -> DataFrame  (state-level trend targets)
    state_portfolio_fit(...)          -> DataFrame  (blended fit score)
    concentration_table(df)           -> str        (formatted text table)
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_numeric_cols(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


def _percentile_rank(series: pd.Series) -> pd.Series:
    return series.rank(pct=True)


# ---------------------------------------------------------------------------
# Market concentration
# ---------------------------------------------------------------------------

def market_concentration_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute market concentration by state/year.

    Returns HHI, CR3, CR5, and total Medicare payment per state-year market.
    Higher HHI → more concentrated; PE rollups prefer HHI 0.15-0.40 headroom.
    """
    required = {"state", "provider_type", "total_medicare_payment_amt"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    if "year" not in work.columns:
        work["year"] = "all"
    _to_numeric_cols(work, ["total_medicare_payment_amt"])
    work = work.dropna(subset=["state", "provider_type", "total_medicare_payment_amt"])
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby(["state", "year", "provider_type"], as_index=False)["total_medicare_payment_amt"]
        .sum()
    )

    rows = []
    for (state, year), g in grouped.groupby(["state", "year"]):
        total = g["total_medicare_payment_amt"].sum()
        if total <= 0:
            continue
        shares = (g["total_medicare_payment_amt"] / total).sort_values(ascending=False)
        rows.append(
            {
                "state": state,
                "year": year,
                "provider_type_count": int(len(g)),
                "hhi": float((shares ** 2).sum()),
                "cr3": float(shares.head(3).sum()),
                "cr5": float(shares.head(5).sum()),
                "total_payment": float(total),
            }
        )

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    return out.sort_values(["hhi", "cr3"], ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Geographic dependency
# ---------------------------------------------------------------------------

def provider_geo_dependency(
    df: pd.DataFrame,
    dependency_threshold: float = 0.50,
) -> pd.DataFrame:
    """Measure how dependent each provider type is on a single state.

    A provider with >50% revenue from one state has single-state concentration
    risk that elevates regulatory and rate-cut exposure.
    """
    required = {"provider_type", "state", "total_medicare_payment_amt"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _to_numeric_cols(work, ["total_medicare_payment_amt"])
    work = work.dropna(subset=["provider_type", "state", "total_medicare_payment_amt"])
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby(["provider_type", "state"], as_index=False)["total_medicare_payment_amt"]
        .sum()
    )

    rows = []
    for provider, g in grouped.groupby("provider_type"):
        total = g["total_medicare_payment_amt"].sum()
        if total <= 0:
            continue
        shares = (g["total_medicare_payment_amt"] / total).sort_values(ascending=False)
        top_idx = g["total_medicare_payment_amt"].idxmax()
        top_state = str(g.loc[top_idx, "state"])
        top_share = float(shares.iloc[0])
        hhi_geo = float((shares ** 2).sum())
        rows.append(
            {
                "provider_type": provider,
                "state_count": int(g["state"].nunique()),
                "top_state": top_state,
                "top_state_share": top_share,
                "geo_hhi": hhi_geo,
                "geo_dependency_flag": bool(top_share >= dependency_threshold),
            }
        )

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out["geo_dependency_percentile"] = _percentile_rank(out["top_state_share"])
    return out.sort_values("top_state_share", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# State-level trend summaries
# ---------------------------------------------------------------------------

def state_volatility_summary(df: pd.DataFrame) -> pd.DataFrame:
    """YoY Medicare payment volatility by state — flags stable vs erratic markets."""
    if not {"state", "year", "total_medicare_payment_amt"}.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _to_numeric_cols(work, ["year", "total_medicare_payment_amt"])
    work = work.dropna(subset=["state", "year", "total_medicare_payment_amt"])
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby(["state", "year"], as_index=False)["total_medicare_payment_amt"]
        .sum()
        .sort_values(["state", "year"])
    )
    grouped["state_yoy_pct"] = grouped.groupby("state")["total_medicare_payment_amt"].pct_change()

    out = (
        grouped.groupby("state", as_index=False)
        .agg(
            yoy_volatility=("state_yoy_pct", "std"),
            avg_growth=("state_yoy_pct", "mean"),
            latest_growth=("state_yoy_pct", "last"),
            latest_payment=("total_medicare_payment_amt", "last"),
        )
        .sort_values("yoy_volatility", ascending=False)
        .reset_index(drop=True)
    )
    return out


def state_growth_summary(df: pd.DataFrame) -> pd.DataFrame:
    """State-level growth trend — identifies geographic expansion targets."""
    if not {"state", "year", "total_medicare_payment_amt"}.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _to_numeric_cols(work, ["year", "total_medicare_payment_amt"])
    work = work.dropna(subset=["state", "year", "total_medicare_payment_amt"])
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby(["state", "year"], as_index=False)["total_medicare_payment_amt"]
        .sum()
        .sort_values(["state", "year"])
    )
    grouped["state_payment_yoy_pct"] = grouped.groupby("state")["total_medicare_payment_amt"].pct_change()

    out = (
        grouped.groupby("state", as_index=False)
        .agg(
            avg_state_growth=("state_payment_yoy_pct", "mean"),
            latest_state_growth=("state_payment_yoy_pct", "last"),
            latest_payment=("total_medicare_payment_amt", "last"),
        )
        .sort_values(["latest_state_growth", "latest_payment"], ascending=False)
        .reset_index(drop=True)
    )
    return out


# ---------------------------------------------------------------------------
# Portfolio-fit blended score
# ---------------------------------------------------------------------------

def state_portfolio_fit(
    state_growth: pd.DataFrame,
    state_volatility: pd.DataFrame,
    concentration: pd.DataFrame,
) -> pd.DataFrame:
    """Blend state momentum, stability, and concentration into an expansion-fit score.

    Score components (weights sum to 1.00):
        0.35 — latest YoY growth
        0.20 — avg growth
        0.20 — log(latest payment volume)
        0.15 — stability (inverse volatility)
        0.10 — fragmentation bonus (1 - HHI)
    """
    if state_growth.empty:
        return pd.DataFrame()

    fit = state_growth.copy()

    if not state_volatility.empty:
        keep = [c for c in ["state", "yoy_volatility", "latest_growth"] if c in state_volatility.columns]
        fit = fit.merge(state_volatility[keep], on="state", how="left", suffixes=("", "_vol"))

    if not concentration.empty:
        conc_latest = (
            concentration.sort_values(["state", "year"])
            .groupby("state", as_index=False)
            .tail(1)
        )
        keep = [c for c in ["state", "hhi", "cr3", "provider_type_count"] if c in conc_latest.columns]
        fit = fit.merge(conc_latest[keep], on="state", how="left")

    for col in ["latest_state_growth", "avg_state_growth", "latest_payment", "yoy_volatility", "hhi"]:
        if col not in fit.columns:
            fit[col] = np.nan
        fit[col] = pd.to_numeric(fit[col], errors="coerce")

    fit["stability_score"] = 1 / (
        1 + fit["yoy_volatility"].clip(lower=0).fillna(fit["yoy_volatility"].median())
    )
    fit["fragmentation_bonus"] = 1 - fit["hhi"].fillna(fit["hhi"].median())
    fit["state_fit_score"] = (
        0.35 * fit["latest_state_growth"].fillna(0)
        + 0.20 * fit["avg_state_growth"].fillna(0)
        + 0.20 * np.log1p(fit["latest_payment"].clip(lower=0).fillna(0))
        + 0.15 * fit["stability_score"].fillna(0)
        + 0.10 * fit["fragmentation_bonus"].fillna(0)
    )
    fit["state_fit_percentile"] = _percentile_rank(fit["state_fit_score"])
    return fit.sort_values("state_fit_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Formatted output
# ---------------------------------------------------------------------------

def concentration_table(df: pd.DataFrame, top_n: int = 20) -> str:
    """Return a formatted text table of concentration metrics."""
    if df.empty:
        return "No concentration data available.\n"

    lines = ["Market Concentration Summary", "=" * 64]
    header = f"{'State':<6} {'Year':<6} {'#Types':>6} {'HHI':>8} {'CR3':>8} {'CR5':>8} {'Payment $M':>12}"
    lines.append(header)
    lines.append("-" * 64)

    show = df.head(top_n)
    for _, row in show.iterrows():
        payment_mm = row.get("total_payment", 0) / 1_000_000
        lines.append(
            f"{str(row.get('state','')):<6} "
            f"{str(row.get('year','')):<6} "
            f"{int(row.get('provider_type_count', 0)):>6} "
            f"{row.get('hhi', 0):>8.3f} "
            f"{row.get('cr3', 0):>8.3f} "
            f"{row.get('cr5', 0):>8.3f} "
            f"{payment_mm:>12.1f}"
        )

    lines.append("=" * 64)
    return "\n".join(lines) + "\n"
