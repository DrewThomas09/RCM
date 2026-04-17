"""CMS provider stress-testing and investability ranking for PE diligence.

Ported and cleaned from cms_api_advisory_analytics.py (DrewThomas09/cms_medicare).
Adds payment-shock scenarios and operating-posture classification on top of
the regime/concentration analytics in market_concentration.py and provider_regime.py.

Investment postures:
    scenario_leader   — top across multiple shock scenarios + strong fundamentals
    resilient_core    — high consensus + high reliability + low concentration
    balanced          — moderate on all dimensions
    growth_optional   — high current score but unreliable growth trend
    concentration_risk — single-state overexposure

Public API:
    provider_value_summary(df)                          -> DataFrame
    provider_investability_summary(screen, value, vol)  -> DataFrame
    provider_stress_test(investability, ...)             -> DataFrame
    stress_scenario_grid(investability, ...)             -> DataFrame
    provider_operating_posture(...)                      -> DataFrame
    stress_table(grid)                                   -> str
    posture_table(posture)                               -> str
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_numeric(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


def _percentile_rank(series: pd.Series) -> pd.Series:
    return series.rank(pct=True)


# ---------------------------------------------------------------------------
# Value summary (risk-adjusted payment efficiency)
# ---------------------------------------------------------------------------

def provider_value_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Risk-adjusted payment efficiency per provider type.

    value_score = 1 / (payment_per_bene / avg_risk_score)
    Higher value_score → more efficient per-beneficiary care relative to acuity.
    """
    required = {
        "provider_type", "total_medicare_payment_amt",
        "total_unique_benes", "beneficiary_average_risk_score",
    }
    # Allow flexible presence of payment_per_bene or compute it
    if not {"provider_type", "total_medicare_payment_amt"}.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _to_numeric(work, [
        "total_medicare_payment_amt", "total_unique_benes",
        "beneficiary_average_risk_score",
    ])

    if "payment_per_bene" not in work.columns:
        benes = work.get("total_unique_benes", pd.Series(dtype=float))
        if benes.notna().any():
            work["payment_per_bene"] = work["total_medicare_payment_amt"] / benes.replace(0, float("nan"))
        else:
            work["payment_per_bene"] = float("nan")

    if "beneficiary_average_risk_score" not in work.columns:
        work["beneficiary_average_risk_score"] = float("nan")

    grouped = (
        work.groupby("provider_type", as_index=False)
        .agg(
            total_payment=("total_medicare_payment_amt", "sum"),
            median_payment_per_bene=("payment_per_bene", "median"),
            median_risk=("beneficiary_average_risk_score", "median"),
            row_count=("provider_type", "count"),
        )
    )
    grouped = grouped[grouped["median_payment_per_bene"] > 0]
    if grouped.empty:
        return grouped

    grouped["risk_adjusted_cost"] = (
        grouped["median_payment_per_bene"]
        / grouped["median_risk"].replace(0, float("nan"))
    )
    grouped["value_score"] = 1 / grouped["risk_adjusted_cost"].replace(0, float("nan"))
    grouped["value_percentile"] = _percentile_rank(grouped["value_score"])
    return grouped.sort_values("value_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Investability summary
# ---------------------------------------------------------------------------

def provider_investability_summary(
    screen: pd.DataFrame,
    value_summary: pd.DataFrame,
    volatility: pd.DataFrame,
) -> pd.DataFrame:
    """Blended investability score combining opportunity, value, and stability.

    Weights:
        0.45 × opportunity_percentile (growth / market share)
        0.35 × value_percentile       (risk-adjusted efficiency)
        0.20 × stability_percentile   (1 / (1 + vol))
    """
    if screen.empty:
        return pd.DataFrame()

    base = screen.copy()
    if "provider_type" not in base.columns and base.index.name == "provider_type":
        base = base.reset_index()
    if "provider_type" not in base.columns:
        return pd.DataFrame()

    keep = [c for c in ["provider_type", "opportunity_score", "opportunity_percentile", "total_payment"]
            if c in base.columns]
    base = base[keep].copy()

    if not value_summary.empty:
        vkeep = [c for c in ["provider_type", "value_score", "value_percentile"]
                 if c in value_summary.columns]
        base = base.merge(value_summary[vkeep], on="provider_type", how="left")

    if not volatility.empty:
        stab = volatility.copy()
        if "yoy_payment_volatility" in stab.columns:
            stab["stability_score"] = 1 / (
                1 + pd.to_numeric(stab["yoy_payment_volatility"], errors="coerce").clip(lower=0)
            )
        skeep = [c for c in ["provider_type", "stability_score", "yoy_payment_volatility", "last_payment_growth"]
                 if c in stab.columns]
        base = base.merge(stab[skeep], on="provider_type", how="left")

    for col in ["value_score", "stability_score", "opportunity_score"]:
        if col not in base.columns:
            base[col] = float("nan")
        base[col] = pd.to_numeric(base[col], errors="coerce")

    base["opp_rank"] = _percentile_rank(base["opportunity_score"])
    base["value_rank"] = _percentile_rank(base["value_score"])
    base["stability_rank"] = _percentile_rank(base.get("stability_score", pd.Series(dtype=float)))
    base["investability_score"] = (
        0.45 * base["opp_rank"]
        + 0.35 * base["value_rank"]
        + 0.20 * base["stability_rank"]
    )
    return base.sort_values("investability_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Stress test
# ---------------------------------------------------------------------------

def provider_stress_test(
    investability: pd.DataFrame,
    downside_shock: float = 0.15,
    upside_shock: float = 0.10,
) -> pd.DataFrame:
    """Apply payment shocks to investability scores.

    stress_adjusted_score = base_score × (1 - downside_shock)
                           + 0.25 × base_score × upside_shock
    """
    if investability.empty:
        return pd.DataFrame()

    out = investability.copy()
    if "total_payment" not in out.columns:
        out["total_payment"] = float("nan")
    if "investability_score" not in out.columns:
        out["investability_score"] = float("nan")

    _to_numeric(out, ["total_payment", "investability_score"])

    out["downside_payment"] = out["total_payment"] * (1 - downside_shock)
    out["upside_payment"] = out["total_payment"] * (1 + upside_shock)
    out["stress_adjusted_score"] = (
        out["investability_score"] * (1 - downside_shock)
        + 0.25 * out["investability_score"] * upside_shock
    )
    out["stress_rank"] = out["stress_adjusted_score"].rank(ascending=False, method="dense")
    return out.sort_values("stress_adjusted_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Scenario grid
# ---------------------------------------------------------------------------

def stress_scenario_grid(
    investability: pd.DataFrame,
    downsides: Optional[List[float]] = None,
    upsides: Optional[List[float]] = None,
) -> pd.DataFrame:
    """Run a compact shock grid to understand ranking robustness across scenarios.

    Returns one row per (downside, upside) pair with top provider and score stats.
    """
    if investability.empty:
        return pd.DataFrame()

    downsides = downsides or [0.05, 0.15, 0.25]
    upsides = upsides or [0.00, 0.10, 0.20]
    rows = []

    for d in downsides:
        for u in upsides:
            st = provider_stress_test(investability, downside_shock=d, upside_shock=u)
            if st.empty:
                continue
            top = str(st.iloc[0].get("provider_type", "")) if "provider_type" in st.columns else None
            score_col = pd.to_numeric(st["stress_adjusted_score"], errors="coerce")
            rows.append(
                {
                    "downside_shock": float(d),
                    "upside_shock": float(u),
                    "scenario_label": f"d{int(d * 100)}_u{int(u * 100)}",
                    "top_provider": top,
                    "top_stress_score": float(st.iloc[0].get("stress_adjusted_score", float("nan"))),
                    "median_stress_score": float(score_col.median()),
                    "mean_stress_score": float(score_col.mean()),
                }
            )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["downside_shock", "upside_shock"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Operating posture
# ---------------------------------------------------------------------------

POSTURE_ORDER = [
    "scenario_leader", "resilient_core", "balanced", "growth_optional", "concentration_risk",
]


def provider_operating_posture(
    investability: pd.DataFrame,
    trend_reliability: pd.DataFrame,
    geo_dependency: pd.DataFrame,
    scenario_grid: pd.DataFrame,
    scenario_min_win_share: float = 0.30,
) -> pd.DataFrame:
    """Classify providers into 5 operating postures.

    Logic (priority order — last match wins):
        balanced          — default
        resilient_core    — high consensus + reliable + low geo concentration
        growth_optional   — high score but low reliability
        concentration_risk — top_state_share >= 0.60
        scenario_leader   — consistent scenario winner + good fundamentals
    """
    if investability.empty:
        return pd.DataFrame()

    base = investability.copy()
    if "provider_type" not in base.columns:
        return pd.DataFrame()

    keep = [c for c in ["provider_type", "investability_score"] if c in base.columns]
    base = base[keep].copy()
    base["consensus_percentile"] = _percentile_rank(base.get("investability_score", pd.Series(dtype=float)))

    if not trend_reliability.empty:
        rkeep = [c for c in ["provider_type", "reliability_score", "reliability_percentile"]
                 if c in trend_reliability.columns]
        base = base.merge(trend_reliability[rkeep], on="provider_type", how="left")

    if not geo_dependency.empty:
        gkeep = [c for c in ["provider_type", "top_state_share", "geo_dependency_flag"]
                 if c in geo_dependency.columns]
        base = base.merge(geo_dependency[gkeep], on="provider_type", how="left")

    win_rate = pd.DataFrame(columns=["provider_type", "scenario_win_share"])
    if not scenario_grid.empty and "top_provider" in scenario_grid.columns:
        vc = scenario_grid["top_provider"].value_counts(dropna=True)
        if not vc.empty:
            win_rate = vc.rename_axis("provider_type").reset_index(name="scenario_win_count")
            win_rate["scenario_win_share"] = win_rate["scenario_win_count"] / float(len(scenario_grid))
            win_rate = win_rate[["provider_type", "scenario_win_share"]]

    base = base.merge(win_rate, on="provider_type", how="left")

    for col in ["consensus_percentile", "reliability_percentile", "top_state_share", "scenario_win_share"]:
        if col not in base.columns:
            base[col] = float("nan")
        base[col] = pd.to_numeric(base[col], errors="coerce")

    base["top_state_share"] = base["top_state_share"].fillna(base["top_state_share"].median())
    base["scenario_win_share"] = base["scenario_win_share"].fillna(0)

    base["operating_posture"] = "balanced"
    base.loc[
        (base["consensus_percentile"] >= 0.75)
        & (base["reliability_percentile"].fillna(0) >= 0.60)
        & (base["top_state_share"] < 0.50),
        "operating_posture",
    ] = "resilient_core"
    base.loc[
        (base["consensus_percentile"] >= 0.60)
        & (base["reliability_percentile"].fillna(0) < 0.50),
        "operating_posture",
    ] = "growth_optional"
    base.loc[
        base["top_state_share"] >= 0.60,
        "operating_posture",
    ] = "concentration_risk"
    base.loc[
        (base["scenario_win_share"] >= scenario_min_win_share)
        & (base["consensus_percentile"] >= 0.50),
        "operating_posture",
    ] = "scenario_leader"

    posture_order = pd.CategoricalDtype(POSTURE_ORDER, ordered=True)
    base["operating_posture"] = base["operating_posture"].astype(posture_order)
    base["posture_score"] = (
        0.45 * base["consensus_percentile"].fillna(0)
        + 0.25 * base.get("reliability_percentile", pd.Series(0, index=base.index)).fillna(0)
        + 0.20 * base["scenario_win_share"].fillna(0)
        - 0.10 * base["top_state_share"].fillna(0)
    )
    return base.sort_values(["operating_posture", "posture_score"], ascending=[True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Formatted output
# ---------------------------------------------------------------------------

def stress_table(grid: pd.DataFrame) -> str:
    """Formatted text table of the stress scenario grid."""
    if grid.empty:
        return "No stress scenario data available.\n"

    lines = ["Provider Stress Scenario Grid", "=" * 68]
    header = f"{'Scenario':<14} {'Downside':>9} {'Upside':>8} {'Top Provider':<35} {'Score':>8}"
    lines.append(header)
    lines.append("-" * 68)

    for _, row in grid.iterrows():
        top = str(row.get("top_provider", ""))[:34]
        score = row.get("top_stress_score", float("nan"))
        score_s = f"{score:.3f}" if score == score else "  N/A"
        lines.append(
            f"{row.get('scenario_label',''):<14} "
            f"{row.get('downside_shock', 0):>8.0%} "
            f"{row.get('upside_shock', 0):>7.0%} "
            f"{top:<35} "
            f"{score_s:>8}"
        )

    lines.append("=" * 68)
    return "\n".join(lines) + "\n"


def posture_table(posture: pd.DataFrame, top_n: int = 20) -> str:
    """Formatted text table of operating postures."""
    if posture.empty:
        return "No operating posture data available.\n"

    lines = ["Provider Operating Posture", "=" * 72]
    header = f"{'Provider Type':<38} {'Posture':<22} {'Score':>8}"
    lines.append(header)
    lines.append("-" * 72)

    for _, row in posture.head(top_n).iterrows():
        pt = str(row.get("provider_type", ""))[:37]
        p = str(row.get("operating_posture", ""))
        score = row.get("posture_score", float("nan"))
        score_s = f"{score:.3f}" if score == score else "  N/A"
        lines.append(f"{pt:<38} {p:<22} {score_s:>8}")

    lines.append("=" * 72)
    return "\n".join(lines) + "\n"
