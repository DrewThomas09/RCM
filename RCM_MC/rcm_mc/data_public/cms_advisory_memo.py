"""Senior-partner CMS advisory memo generator.

Ported and adapted from cms_api_advisory_analytics.build_advisory_memo()
(DrewThomas09/cms_medicare).

Takes a MarketAnalysisReport (from cms_market_analysis.run_market_analysis)
plus optional supplementary DataFrames and produces a single markdown-style
memo that a PE senior partner can read in < 5 minutes.

Public API:
    build_advisory_memo(report, ...)  -> str   (markdown memo)
    quick_memo(df, year)              -> str   (one-call convenience wrapper)
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .cms_market_analysis import MarketAnalysisReport, run_market_analysis
from .cms_opportunity_scoring import (
    provider_screen,
    state_provider_opportunities,
    provider_state_benchmark_flags,
)
from .cms_stress_test import (
    provider_value_summary,
    provider_investability_summary,
    provider_stress_test,
    stress_scenario_grid,
    provider_operating_posture,
)
from .provider_regime import yearly_trends, provider_volatility, growth_volatility_watchlist


# ---------------------------------------------------------------------------
# Memo builder
# ---------------------------------------------------------------------------

def build_advisory_memo(
    report: MarketAnalysisReport,
    *,
    benchmark_flags: Optional[pd.DataFrame] = None,
    investability: Optional[pd.DataFrame] = None,
    stress_test: Optional[pd.DataFrame] = None,
    operating_posture: Optional[pd.DataFrame] = None,
    scenario_grid: Optional[pd.DataFrame] = None,
    top_n: int = 5,
) -> str:
    """Build a markdown advisory memo from a MarketAnalysisReport.

    Supplementary DataFrames are all optional — the memo gracefully skips
    sections where data is absent.
    """
    lines = ["# CMS Advisory Snapshot", ""]
    year = report.year
    state = report.state_filter or "All States"
    lines.append(f"**Year:** {year}  |  **Geography:** {state}  |  **Rows:** {report.row_count:,}\n")

    if report.errors:
        lines.append("**⚠ Errors during fetch:**")
        for e in report.errors:
            lines.append(f"- {e}")
        lines.append("")

    # -- Regime classification --
    if not report.regimes.empty:
        dur = report.regimes[report.regimes["regime"].astype(str) == "durable_growth"].head(top_n)
        risk_r = report.regimes[report.regimes["regime"].astype(str) == "declining_risk"].head(top_n)
        lines.append("## Provider Regime Classification")
        lines.append("- **Durable Growth:** " + (", ".join(dur["provider_type"].tolist()) or "none"))
        lines.append("- **Declining Risk:**  " + (", ".join(risk_r["provider_type"].tolist()) or "none"))
        lines.append("")

    # -- Watchlist --
    if not report.watchlist.empty and "watchlist_bucket" in report.watchlist.columns:
        priority = report.watchlist[report.watchlist["watchlist_bucket"] == "priority"].head(top_n)
        risky = report.watchlist[report.watchlist["watchlist_bucket"] == "high_risk"].head(top_n)
        lines.append("## Growth-Volatility Watchlist")
        lines.append("- **Priority (grow + stable):** " + (", ".join(priority["provider_type"].tolist()) or "none"))
        lines.append("- **High-Risk:**  " + (", ".join(risky["provider_type"].tolist()) or "none"))
        lines.append("")

    # -- Geographic fit --
    if not report.portfolio_fit.empty and "state_fit_percentile" in report.portfolio_fit.columns:
        top_fit = report.portfolio_fit.head(top_n)
        lines.append("## State Portfolio Fit (Expansion Targets)")
        for _, row in top_fit.iterrows():
            score = row.get("state_fit_score", float("nan"))
            pct = row.get("state_fit_percentile", float("nan"))
            score_s = f"{score:.3f}" if score == score else "N/A"
            pct_s = f"{pct:.0%}" if pct == pct else "N/A"
            lines.append(f"- **{row.get('state','')}**: fit={score_s} ({pct_s})")
        lines.append("")

    # -- Concentration --
    if not report.concentration.empty:
        top_conc = report.concentration.head(top_n)
        lines.append("## Market Concentration Hotspots (by HHI)")
        for _, row in top_conc.iterrows():
            lines.append(
                f"- **{row.get('state','')}/{row.get('year','')}**: "
                f"HHI={row.get('hhi', 0):.3f}, CR3={row.get('cr3', 0):.3f}, "
                f"CR5={row.get('cr5', 0):.3f}"
            )
        lines.append("")

    # -- Geographic dependency --
    if not report.geo_dependency.empty:
        conc_risk = report.geo_dependency[
            report.geo_dependency.get("geo_dependency_flag", pd.Series(False))
        ].head(top_n) if "geo_dependency_flag" in report.geo_dependency.columns else pd.DataFrame()
        if not conc_risk.empty:
            lines.append("## Geographic Concentration Risk (> 50% in one state)")
            for _, row in conc_risk.iterrows():
                lines.append(
                    f"- **{row.get('provider_type','')}** → "
                    f"{row.get('top_state','')} ({row.get('top_state_share', 0):.0%})"
                )
            lines.append("")

    # -- State volatility --
    if not report.state_volatility.empty:
        volatile = report.state_volatility.head(top_n)
        lines.append("## Most Volatile State Markets")
        lines.append("- " + ", ".join(volatile["state"].tolist()))
        lines.append("")

    # -- Benchmark flags --
    if benchmark_flags is not None and not benchmark_flags.empty:
        high = benchmark_flags[benchmark_flags["benchmark_flag"] == "high_price"].head(top_n)
        low = benchmark_flags[benchmark_flags["benchmark_flag"] == "low_price"].head(top_n)
        if not high.empty or not low.empty:
            lines.append("## Benchmark Price Flags")
            if not high.empty:
                labels = (high["provider_type"] + "|" + high["state"]).tolist()
                lines.append("- **High-price outliers:** " + ", ".join(labels))
            if not low.empty:
                labels = (low["provider_type"] + "|" + low["state"]).tolist()
                lines.append("- **Low-price outliers:** " + ", ".join(labels))
            lines.append("")

    # -- Investability --
    if investability is not None and not investability.empty:
        top_inv = investability.head(top_n)
        lines.append("## Top Investability Blend")
        for _, row in top_inv.iterrows():
            score = row.get("investability_score", float("nan"))
            lines.append(
                f"- **{row.get('provider_type','')}**: "
                f"score={score:.3f}" if score == score
                else f"- **{row.get('provider_type','')}**"
            )
        lines.append("")

    # -- Stress resilience --
    if stress_test is not None and not stress_test.empty:
        top_stress = stress_test.head(top_n)
        lines.append("## Stress-Test Resilient Providers")
        lines.append("- " + ", ".join(top_stress["provider_type"].astype(str).tolist()))
        lines.append("")

    # -- Scenario grid --
    if scenario_grid is not None and not scenario_grid.empty and "top_provider" in scenario_grid.columns:
        dominant = scenario_grid["top_provider"].value_counts(dropna=True).head(3)
        lines.append("## Scenario Robustness")
        lines.append("- " + ", ".join(f"{k} ({v} wins)" for k, v in dominant.items()))
        lines.append("")

    # -- Operating posture --
    if operating_posture is not None and not operating_posture.empty:
        core = operating_posture[
            operating_posture["operating_posture"].astype(str) == "resilient_core"
        ]["provider_type"].head(top_n).tolist()
        leaders = operating_posture[
            operating_posture["operating_posture"].astype(str) == "scenario_leader"
        ]["provider_type"].head(top_n).tolist()
        conc = operating_posture[
            operating_posture["operating_posture"].astype(str) == "concentration_risk"
        ]["provider_type"].head(top_n).tolist()
        lines.append("## Operating Posture Summary")
        if leaders:
            lines.append("- **Scenario Leaders:**   " + ", ".join(leaders))
        if core:
            lines.append("- **Resilient Core:**     " + ", ".join(core))
        if conc:
            lines.append("- **Concentration Risk:** " + ", ".join(conc))
        lines.append("")

    lines.append("---")
    lines.append("*Generated by rcm_mc.data_public.cms_advisory_memo*")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# One-call convenience wrapper
# ---------------------------------------------------------------------------

def quick_memo(
    df: Optional[pd.DataFrame] = None,
    year: int = 2021,
    state: Optional[str] = None,
    top_n: int = 5,
) -> str:
    """Run the full CMS analytics pipeline and return an advisory memo.

    If `df` is provided it is used directly (no HTTP call).
    Otherwise calls the CMS API — requires network access.
    """
    report = run_market_analysis(year=year, state=state, df=df)

    # Enrich report with opportunity / stress layers
    benchmark_flags = pd.DataFrame()
    investability = pd.DataFrame()
    stress = pd.DataFrame()
    grid = pd.DataFrame()
    posture = pd.DataFrame()

    if not report.concentration.empty or not report.regimes.empty:
        # Reconstruct raw df if needed for supplementary analytics
        raw_df = df if df is not None else pd.DataFrame()
        if not raw_df.empty:
            try:
                screen = provider_screen(raw_df)
                val = provider_value_summary(raw_df)
                vol = report.watchlist  # already computed in MarketAnalysisReport
                investability = provider_investability_summary(screen, val, vol)
                if not investability.empty:
                    stress = provider_stress_test(investability)
                    grid = stress_scenario_grid(investability)
                    posture = provider_operating_posture(
                        investability, pd.DataFrame(), report.geo_dependency, grid
                    )
                benchmark_flags = provider_state_benchmark_flags(raw_df)
            except Exception:
                pass

    return build_advisory_memo(
        report,
        benchmark_flags=benchmark_flags,
        investability=investability,
        stress_test=stress,
        operating_posture=posture,
        scenario_grid=grid,
        top_n=top_n,
    )
