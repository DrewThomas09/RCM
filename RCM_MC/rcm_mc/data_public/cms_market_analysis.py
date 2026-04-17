"""High-level CMS market analysis — chains API fetch → concentration → regime.

Orchestrates the full CMS analytics pipeline for PE due diligence:
    1. Fetch provider utilization from CMS Data API
    2. Compute market concentration (HHI, CR3, CR5) by state/year
    3. Classify provider operating regimes (5-bucket)
    4. Score state portfolio fit (growth × stability × fragmentation)
    5. Identify white-space opportunities (high-fit + under-penetrated)

All analytics functions accept DataFrames so callers can swap in local
test data without hitting the live CMS API.

Public API:
    MarketAnalysisReport      dataclass
    run_market_analysis(...)  → MarketAnalysisReport
    white_space_opportunities(...)  → DataFrame
    top_regimes(...)          → DataFrame
    analysis_summary_text(report)  → str
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .cms_api_client import fetch_provider_utilization, CmsApiError
from .market_concentration import (
    market_concentration_summary,
    provider_geo_dependency,
    state_volatility_summary,
    state_growth_summary,
    state_portfolio_fit,
    concentration_table,
)
from .provider_regime import (
    yearly_trends,
    provider_volatility,
    provider_momentum_profile,
    growth_volatility_watchlist,
    provider_regime_classification,
    regime_table,
)


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------

@dataclass
class MarketAnalysisReport:
    year: int
    state_filter: Optional[str]
    provider_type_filter: Optional[str]
    row_count: int
    concentration: pd.DataFrame
    geo_dependency: pd.DataFrame
    state_growth: pd.DataFrame
    state_volatility: pd.DataFrame
    portfolio_fit: pd.DataFrame
    regimes: pd.DataFrame
    watchlist: pd.DataFrame
    errors: List[str] = field(default_factory=list)

    def as_summary_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable summary (no DataFrames)."""
        top_regime = (
            self.regimes.iloc[0]["provider_type"]
            if not self.regimes.empty
            else None
        )
        top_state = (
            self.portfolio_fit.iloc[0]["state"]
            if not self.portfolio_fit.empty
            else None
        )
        priority_wl = (
            self.watchlist[self.watchlist["watchlist_bucket"] == "priority"]["provider_type"].tolist()[:5]
            if not self.watchlist.empty and "watchlist_bucket" in self.watchlist.columns
            else []
        )
        return {
            "year": self.year,
            "state_filter": self.state_filter,
            "provider_type_filter": self.provider_type_filter,
            "row_count": self.row_count,
            "concentration_markets": len(self.concentration),
            "regimes_classified": len(self.regimes),
            "top_regime_provider": top_regime,
            "top_fit_state": top_state,
            "priority_watchlist": priority_wl,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# White-space detection
# ---------------------------------------------------------------------------

def white_space_opportunities(
    report: MarketAnalysisReport,
    min_fit_percentile: float = 0.60,
) -> pd.DataFrame:
    """Identify high-fit states with under-penetrated provider segments.

    Cross-references portfolio_fit with watchlist priority providers:
    high fit score + priority growth profile = white-space opportunity.
    """
    if report.portfolio_fit.empty or report.watchlist.empty:
        return pd.DataFrame()

    priority = report.watchlist[
        report.watchlist.get("watchlist_bucket", pd.Series(dtype=str)) == "priority"
    ][["provider_type"]].copy() if "watchlist_bucket" in report.watchlist.columns else pd.DataFrame()

    fit = report.portfolio_fit[
        report.portfolio_fit.get("state_fit_percentile", pd.Series(dtype=float)) >= min_fit_percentile
    ].copy() if "state_fit_percentile" in report.portfolio_fit.columns else report.portfolio_fit.copy()

    if priority.empty or fit.empty:
        return pd.DataFrame()

    # Cross join: every priority provider × every high-fit state
    fit["_key"] = 1
    priority["_key"] = 1
    cross = fit.merge(priority, on="_key").drop("_key", axis=1)

    cross = cross.sort_values(
        ["state_fit_percentile", "latest_state_growth"],
        ascending=[False, False],
    ).reset_index(drop=True)
    return cross


# ---------------------------------------------------------------------------
# Convenience slicers
# ---------------------------------------------------------------------------

def top_regimes(report: MarketAnalysisReport, n: int = 10) -> pd.DataFrame:
    """Return the top-n providers by regime rank score (durable_growth first)."""
    if report.regimes.empty:
        return pd.DataFrame()
    return report.regimes.head(n)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_market_analysis(
    year: int = 2021,
    state: Optional[str] = None,
    provider_type: Optional[str] = None,
    max_pages: int = 4,
    limit: int = 5000,
    df: Optional[pd.DataFrame] = None,
) -> MarketAnalysisReport:
    """Run the full CMS market analysis pipeline.

    If `df` is provided it is used directly (for testing / offline use).
    Otherwise the CMS Data API is called to fetch provider utilization data.

    Args:
        year:           CMS dataset year
        state:          Optional 2-letter state filter
        provider_type:  Optional provider type filter
        max_pages:      Max API pages (each 5000 rows)
        limit:          Rows per page
        df:             Optional pre-fetched DataFrame (skips HTTP call)

    Returns:
        MarketAnalysisReport with all analytics sub-results.
    """
    errors: List[str] = []

    if df is None:
        try:
            rows = fetch_provider_utilization(
                year=year,
                state=state,
                provider_type=provider_type,
                max_pages=max_pages,
                limit=limit,
            )
            df = pd.DataFrame(rows)
        except CmsApiError as e:
            errors.append(f"CMS API fetch failed: {e}")
            df = pd.DataFrame()

    if df.empty:
        empty = pd.DataFrame()
        return MarketAnalysisReport(
            year=year,
            state_filter=state,
            provider_type_filter=provider_type,
            row_count=0,
            concentration=empty,
            geo_dependency=empty,
            state_growth=empty,
            state_volatility=empty,
            portfolio_fit=empty,
            regimes=empty,
            watchlist=empty,
            errors=errors,
        )

    # --- concentration analytics ---
    concentration = market_concentration_summary(df)
    geo_dep = provider_geo_dependency(df)

    # --- state trend analytics ---
    s_growth = state_growth_summary(df)
    s_vol = state_volatility_summary(df)
    fit = state_portfolio_fit(s_growth, s_vol, concentration)

    # --- regime analytics ---
    trends = yearly_trends(df)
    vol = provider_volatility(trends) if not trends.empty else pd.DataFrame()
    mom = provider_momentum_profile(trends) if not trends.empty else pd.DataFrame()
    regimes = provider_regime_classification(mom, vol) if not (mom.empty and vol.empty) else pd.DataFrame()
    wl = growth_volatility_watchlist(vol) if not vol.empty else pd.DataFrame()

    return MarketAnalysisReport(
        year=year,
        state_filter=state,
        provider_type_filter=provider_type,
        row_count=len(df),
        concentration=concentration,
        geo_dependency=geo_dep,
        state_growth=s_growth,
        state_volatility=s_vol,
        portfolio_fit=fit,
        regimes=regimes,
        watchlist=wl,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Formatted output
# ---------------------------------------------------------------------------

def analysis_summary_text(report: MarketAnalysisReport) -> str:
    """One-page text summary of a MarketAnalysisReport."""
    lines = [
        "CMS Market Analysis Report",
        "=" * 64,
        f"Year: {report.year}  |  State: {report.state_filter or 'All'}  |  Provider: {report.provider_type_filter or 'All'}",
        f"Rows fetched: {report.row_count:,}",
        "",
    ]

    if not report.regimes.empty:
        lines += ["── Provider Regimes (top 5) ──"]
        for _, row in report.regimes.head(5).iterrows():
            pt = str(row.get("provider_type", ""))[:40]
            regime = str(row.get("regime", ""))
            score = row.get("regime_rank_score", float("nan"))
            score_s = f"{score:.3f}" if score == score else "N/A"
            lines.append(f"  {pt:<40} {regime:<22} {score_s}")
        lines.append("")

    if not report.portfolio_fit.empty and "state_fit_score" in report.portfolio_fit.columns:
        lines += ["── Top Portfolio Fit States ──"]
        for _, row in report.portfolio_fit.head(5).iterrows():
            state = str(row.get("state", ""))
            score = row.get("state_fit_score", float("nan"))
            pct = row.get("state_fit_percentile", float("nan"))
            lines.append(
                f"  {state:<4}  fit={score:.3f}  pct={pct:.0%}"
                if score == score else f"  {state}"
            )
        lines.append("")

    if not report.concentration.empty:
        lines.append("── Most Concentrated Markets (HHI) ──")
        for _, row in report.concentration.head(5).iterrows():
            lines.append(
                f"  {row.get('state','')}/{row.get('year','')}  "
                f"HHI={row.get('hhi',0):.3f}  CR3={row.get('cr3',0):.3f}"
            )
        lines.append("")

    if report.errors:
        lines += ["── Errors ──"] + [f"  {e}" for e in report.errors]

    lines.append("=" * 64)
    return "\n".join(lines) + "\n"
