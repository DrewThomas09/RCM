"""CMS provider-level advisory analytics.

Ports the scoring math from ``cms_medicare-master/cms_api_advisory_analytics.py``
(a sibling project on disk, no LICENSE file — treated as internal
material authored by the same team) into the RCM_MC domain model.
Plotting, file IO, Basemap, and the argparse CLI are dropped;
partners consume the numbers via the chartis UI + packet surface
rather than matplotlib PNGs.

Public surface:

- :func:`screen_providers` — opportunity score per provider_type
- :func:`provider_volatility` — year-over-year volatility rollup
- :func:`regime_classification` — durable_growth / emerging_volatile /
  steady_compounders / stagnant / declining_risk per provider_type
- :func:`stress_test` — downside scenarios against payment_per_bene
- :func:`consensus_rank` — ensemble of the above into one rank

Every function is a pure function over a pandas DataFrame that
follows the CMS Public Use File column contract (as standardised by
:func:`standardize_columns`). The output is another DataFrame whose
columns are the risk signals downstream modules consume.

Integration points (wired via :mod:`rcm_mc.pe.cms_advisory_bridge`):

- Opportunity + regime scores feed the packet's ``risk_flags`` list
  as ``RiskFlag(category="market_posture", ...)`` entries.
- Volatility feeds ``DiligenceQuestion`` generation — a HIGH-volatility
  provider_type triggers a question about earnings durability.
- Stress-test outputs can be overlaid on the v2 bridge's Monte Carlo
  as a scenario ceiling.

See :doc:`/diligence/INTEGRATION_MAP.md` for the full flow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


# Column contract every function below assumes. Matches the CMS
# Physician & Supplier Public Use File headers after normalisation.
REQUIRED_COLUMNS = {
    "provider_type",
    "total_medicare_payment_amt",
    "total_services",
    "total_unique_benes",
    "payment_per_service",
    "payment_per_bene",
}


# ── Helpers ────────────────────────────────────────────────────────

def _numeric(df: pd.DataFrame, cols: Iterable[str]) -> None:
    """Coerce named columns to numeric in-place. Missing cols ignored."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


def _percentile_rank(series: pd.Series) -> pd.Series:
    """0..1 quantile rank. NaNs propagate."""
    if series.dropna().empty:
        return pd.Series(np.nan, index=series.index)
    return series.rank(pct=True, method="average", na_option="keep")


def _minmax(s: pd.Series) -> pd.Series:
    """Min-max scaling into [0, 1]. Degenerate (single-value) series → 0."""
    rng = s.max() - s.min()
    if pd.isna(rng) or rng == 0:
        return pd.Series(0.0, index=s.index)
    return (s - s.min()) / rng


def standardize_columns(
    df: pd.DataFrame,
    *,
    column_overrides: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """Normalise column names so downstream functions can rely on the
    canonical vocabulary without handling every CMS vintage.

    ``column_overrides`` is ``{canonical_name: source_name}`` for
    partners whose extract uses a non-standard header. Unknown
    columns pass through unchanged.
    """
    out = df.copy()
    aliases = {
        "Provider_Type": "provider_type",
        "HCPCS_Cd": "hcpcs_code",
        "Avg_Mdcr_Pymt_Amt": "avg_medicare_payment_amt",
        "Tot_Mdcr_Pymt_Amt": "total_medicare_payment_amt",
        "Tot_Srvcs": "total_services",
        "Tot_Benes": "total_unique_benes",
        "Rndrng_Prvdr_State_Abrvtn": "state",
        "Rndrng_Prvdr_Zip5": "zip_code",
        "Bene_Avg_Risk_Scre": "beneficiary_average_risk_score",
    }
    aliases.update({v: k for k, v in (column_overrides or {}).items()})
    out = out.rename(columns={k: v for k, v in aliases.items() if k in out.columns})
    _numeric(out, [
        "total_services", "total_unique_benes", "total_medicare_payment_amt",
        "beneficiary_average_risk_score",
    ])
    if "total_services" in out.columns and "total_medicare_payment_amt" in out.columns:
        out["payment_per_service"] = (
            out["total_medicare_payment_amt"] / out["total_services"].replace(0, np.nan)
        )
    if "total_unique_benes" in out.columns and "total_medicare_payment_amt" in out.columns:
        out["payment_per_bene"] = (
            out["total_medicare_payment_amt"] / out["total_unique_benes"].replace(0, np.nan)
        )
    return out


# ── Provider screen ────────────────────────────────────────────────

@dataclass
class ProviderScreenRow:
    provider_type: str
    opportunity_score: float
    opportunity_percentile: float
    scale_score: float
    margin_proxy_score: float
    acuity_score: float
    fragmentation_score: float
    total_payment: float
    market_share: float
    median_payment_per_service: float
    median_payment_per_bene: float


def screen_providers(df: pd.DataFrame) -> pd.DataFrame:
    """Rank provider_types by a composite "opportunity score".

    Weights (sum to 1.0):
        scale 0.35, margin 0.30, acuity 0.20, fragmentation 0.15

    Fragmentation is 1 − normalised(HHI_component), so unconsolidated
    markets (low HHI) score higher — the rollup thesis. Output is
    sorted descending by opportunity_score.
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"screen_providers: missing required columns {sorted(missing)}. "
            f"Did you call standardize_columns first?"
        )

    grouped = (
        df.groupby("provider_type", dropna=False)
        .agg(
            row_count=("provider_type", "count"),
            total_services=("total_services", "sum"),
            total_benes=("total_unique_benes", "sum"),
            total_payment=("total_medicare_payment_amt", "sum"),
            median_payment_per_service=("payment_per_service", "median"),
            median_payment_per_bene=("payment_per_bene", "median"),
            median_risk=(
                "beneficiary_average_risk_score", "median",
            ) if "beneficiary_average_risk_score" in df.columns
            else ("payment_per_bene", lambda x: np.nan),
        )
        .replace([np.inf, -np.inf], np.nan)
    )

    market_total = float(grouped["total_payment"].sum() or 0.0)
    grouped["market_share"] = (
        grouped["total_payment"] / market_total if market_total > 0 else 0.0
    )
    grouped["hhi_component"] = grouped["market_share"] ** 2

    grouped["scale_score"] = _minmax(np.log1p(grouped["total_payment"]))
    grouped["margin_proxy_score"] = _minmax(grouped["median_payment_per_service"])
    grouped["acuity_score"] = _minmax(grouped["median_risk"])
    grouped["fragmentation_score"] = 1.0 - _minmax(grouped["hhi_component"])
    grouped["opportunity_score"] = (
        0.35 * grouped["scale_score"]
        + 0.30 * grouped["margin_proxy_score"]
        + 0.20 * grouped["acuity_score"]
        + 0.15 * grouped["fragmentation_score"]
    )
    grouped["opportunity_percentile"] = _percentile_rank(grouped["opportunity_score"])
    return grouped.sort_values("opportunity_score", ascending=False)


# ── Yearly trends + volatility ────────────────────────────────────

def yearly_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Year-over-year payment / service / bene growth per provider_type.

    Requires ``year`` column. Returns one row per (provider_type, year)
    with ``payment_yoy_pct``, ``services_yoy_pct``, ``bene_yoy_pct``
    and a ``payment_yoy_accel`` second-difference.
    """
    if "year" not in df.columns:
        return pd.DataFrame()
    agg = (
        df.groupby(["provider_type", "year"], as_index=False)
        .agg(
            total_payment=("total_medicare_payment_amt", "sum"),
            total_services=("total_services", "sum"),
            total_benes=("total_unique_benes", "sum"),
        )
        .sort_values(["provider_type", "year"])
    )
    for target, src in [
        ("payment_yoy_pct", "total_payment"),
        ("services_yoy_pct", "total_services"),
        ("bene_yoy_pct", "total_benes"),
    ]:
        agg[target] = agg.groupby("provider_type")[src].pct_change()
    agg["payment_yoy_accel"] = (
        agg.groupby("provider_type")["payment_yoy_pct"].diff()
    )
    return agg


def provider_volatility(trends: pd.DataFrame) -> pd.DataFrame:
    """Rollup of YoY growth volatility per provider_type."""
    if trends.empty:
        return pd.DataFrame()
    return (
        trends.groupby("provider_type", as_index=False)
        .agg(
            yoy_payment_volatility=("payment_yoy_pct", "std"),
            yoy_services_volatility=("services_yoy_pct", "std"),
            avg_payment_growth=("payment_yoy_pct", "mean"),
            last_payment_growth=("payment_yoy_pct", "last"),
        )
        .sort_values("yoy_payment_volatility", ascending=False)
    )


def momentum_profile(
    trends: pd.DataFrame, *, min_years: int = 3,
) -> pd.DataFrame:
    """CAGR + consistency over ≥ ``min_years`` observations per
    provider_type. Drops provider_types with insufficient history."""
    if trends.empty:
        return pd.DataFrame()
    work = trends.copy()
    for c in ["payment_yoy_pct", "services_yoy_pct"]:
        if c in work.columns:
            work[c] = pd.to_numeric(work[c], errors="coerce")
    prof = (
        work.groupby("provider_type", as_index=False)
        .agg(
            obs_years=("year", "nunique"),
            growth_cagr=("payment_yoy_pct",
                         lambda s: float((1 + s.dropna()).prod() ** (1 / max(len(s.dropna()), 1)) - 1)
                         if s.notna().any() else np.nan),
            positive_yoy_share=("payment_yoy_pct",
                                lambda s: float((s > 0).mean()) if s.notna().any() else np.nan),
            yoy_growth_volatility=("payment_yoy_pct", "std"),
        )
    )
    prof = prof[prof["obs_years"] >= min_years]
    if prof.empty:
        return prof
    prof["consistency_score"] = prof["positive_yoy_share"].fillna(0) - \
        0.5 * prof["yoy_growth_volatility"].fillna(0)
    return prof.sort_values("growth_cagr", ascending=False)


# ── Regime classification ─────────────────────────────────────────

REGIMES = (
    "durable_growth",       # strong growth + low vol
    "steady_compounders",   # moderate growth + any vol
    "emerging_volatile",    # strong growth + high vol
    "stagnant",             # weak growth + low vol
    "declining_risk",       # weak/negative growth + high vol
)


@dataclass
class RegimeRow:
    provider_type: str
    regime: str
    regime_rank_score: float
    growth: float
    volatility: float
    consistency: float


def regime_classification(
    momentum: pd.DataFrame,
    volatility: pd.DataFrame,
    *,
    strong_growth: float = 0.12,
    weak_growth: float = 0.0,
    high_vol: float = 0.35,
) -> pd.DataFrame:
    """Classify each provider_type into one of the five operating
    regimes in :data:`REGIMES`. Thresholds default to the same values
    as the source project but are partner-tunable."""
    if momentum.empty and volatility.empty:
        return pd.DataFrame()

    base = pd.DataFrame()
    if not momentum.empty:
        keep = [c for c in ("provider_type", "consistency_score",
                             "growth_cagr", "positive_yoy_share",
                             "yoy_growth_volatility")
                if c in momentum.columns]
        base = momentum[keep].copy()
    if not volatility.empty:
        vkeep = [c for c in ("provider_type", "last_payment_growth",
                              "yoy_payment_volatility")
                 if c in volatility.columns]
        vdf = volatility[vkeep].copy()
        base = vdf if base.empty else base.merge(vdf, on="provider_type", how="outer")

    if base.empty or "provider_type" not in base.columns:
        return pd.DataFrame()

    for col in ("growth_cagr", "last_payment_growth", "yoy_payment_volatility",
                "consistency_score", "yoy_growth_volatility"):
        if col not in base.columns:
            base[col] = np.nan
        base[col] = pd.to_numeric(base[col], errors="coerce")

    growth = base["last_payment_growth"].fillna(base["growth_cagr"])
    vol = base["yoy_payment_volatility"].fillna(base["yoy_growth_volatility"])

    base["regime"] = "steady_compounders"
    base.loc[(growth >= strong_growth) & (vol > high_vol), "regime"] = "emerging_volatile"
    base.loc[(growth >= strong_growth) & (vol <= high_vol), "regime"] = "durable_growth"
    base.loc[(growth < weak_growth) & (vol <= high_vol), "regime"] = "stagnant"
    base.loc[(growth < weak_growth) & (vol > high_vol), "regime"] = "declining_risk"

    base["regime_rank_score"] = (
        0.50 * growth.fillna(0)
        + 0.30 * base["consistency_score"].fillna(0)
        - 0.20 * vol.fillna(0)
    )
    regime_order = pd.CategoricalDtype(list(REGIMES), ordered=True)
    base["regime"] = base["regime"].astype(regime_order)
    return base.sort_values(["regime", "regime_rank_score"],
                            ascending=[True, False])


# ── Stress test ────────────────────────────────────────────────────

DEFAULT_STRESS_SCENARIOS = {
    "payer_rate_cut_5pct":        {"payment_multiplier": 0.95, "bene_multiplier": 1.00},
    "payer_rate_cut_10pct":       {"payment_multiplier": 0.90, "bene_multiplier": 1.00},
    "volume_shock_down_15pct":    {"payment_multiplier": 1.00, "bene_multiplier": 0.85},
    "rate_and_volume_combined":   {"payment_multiplier": 0.90, "bene_multiplier": 0.85},
    "obbba_medicaid_churn":       {"payment_multiplier": 0.92, "bene_multiplier": 0.90},
    "site_neutral_full":          {"payment_multiplier": 0.82, "bene_multiplier": 1.00},
}


def stress_test(
    screen: pd.DataFrame,
    *,
    scenarios: Optional[Dict[str, Dict[str, float]]] = None,
) -> pd.DataFrame:
    """Apply multiplicative stress scenarios to total_payment + bene
    counts. Returns one row per (provider_type, scenario) with the
    stressed payment_per_bene.

    ``scenarios`` defaults to :data:`DEFAULT_STRESS_SCENARIOS` which
    includes OBBBA Medicaid churn and site-neutral full exposure —
    events from the regulatory calendar in
    :mod:`rcm_mc.diligence.integrity.temporal_validity`.
    """
    if screen.empty:
        return pd.DataFrame()
    scenarios = scenarios or DEFAULT_STRESS_SCENARIOS
    rows: List[Dict[str, Any]] = []
    for provider_type, row in screen.reset_index().iterrows() \
            if "provider_type" not in screen.columns else \
            ((r["provider_type"], r) for _, r in screen.reset_index().iterrows()):
        # pandas gives us (idx, series) for the else branch above — we
        # overload the variable name `provider_type` in the else.
        pt = row["provider_type"] if hasattr(row, "__getitem__") and "provider_type" in row else provider_type
        base_payment = float(row["total_payment"]) if "total_payment" in row else 0.0
        base_benes = float(row.get("total_benes", 1) or 1)
        base_ppb = base_payment / base_benes if base_benes else 0.0
        for scenario_name, shocks in scenarios.items():
            stressed_payment = base_payment * shocks["payment_multiplier"]
            stressed_benes = base_benes * shocks["bene_multiplier"]
            stressed_ppb = stressed_payment / stressed_benes if stressed_benes else 0.0
            # RATIONALE: partners read delta_pct as "how much does
            # total Medicare revenue shrink under this scenario?" We
            # report total-payment delta, not per-bene. Per-bene can
            # go UP when both numerator and denominator shrink (e.g.,
            # rate-and-volume combined), which is technically true
            # but counter-intuitive for a stress label. Total-payment
            # delta is what flows into the v2 bridge EBITDA shock.
            delta = (stressed_payment - base_payment) / base_payment \
                if base_payment else 0.0
            rows.append({
                "provider_type": pt,
                "scenario": scenario_name,
                "base_payment": base_payment,
                "stressed_payment": stressed_payment,
                "stressed_payment_per_bene": stressed_ppb,
                "delta_pct": delta,
            })
    return pd.DataFrame(rows).sort_values(["provider_type", "delta_pct"])


# ── Consensus rank ─────────────────────────────────────────────────

def consensus_rank(
    screen: pd.DataFrame,
    momentum: Optional[pd.DataFrame] = None,
    volatility: Optional[pd.DataFrame] = None,
    *,
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Ensemble of opportunity, momentum, and volatility (inverted)
    into a single 0..1 rank per provider_type.

    Default weights: opportunity 0.5, growth 0.3, vol-inverse 0.2.
    """
    weights = weights or {"opportunity": 0.5, "growth": 0.3, "vol_inverse": 0.2}
    if screen.empty or "opportunity_percentile" not in screen.columns:
        return pd.DataFrame()
    base = screen.reset_index()[[
        "provider_type", "opportunity_score", "opportunity_percentile",
    ]].copy()
    if momentum is not None and not momentum.empty and "growth_cagr" in momentum.columns:
        mrank = momentum[["provider_type", "growth_cagr"]].copy()
        mrank["growth_percentile"] = _percentile_rank(mrank["growth_cagr"])
        base = base.merge(mrank[["provider_type", "growth_percentile"]],
                          on="provider_type", how="left")
    else:
        base["growth_percentile"] = 0.5
    if volatility is not None and not volatility.empty \
            and "yoy_payment_volatility" in volatility.columns:
        vrank = volatility[["provider_type", "yoy_payment_volatility"]].copy()
        vrank["vol_inverse_percentile"] = 1.0 - _percentile_rank(
            vrank["yoy_payment_volatility"]
        )
        base = base.merge(vrank[["provider_type", "vol_inverse_percentile"]],
                          on="provider_type", how="left")
    else:
        base["vol_inverse_percentile"] = 0.5
    base["consensus_score"] = (
        weights["opportunity"] * base["opportunity_percentile"].fillna(0.5)
        + weights["growth"] * base["growth_percentile"].fillna(0.5)
        + weights["vol_inverse"] * base["vol_inverse_percentile"].fillna(0.5)
    )
    base["consensus_rank"] = base["consensus_score"].rank(
        ascending=False, method="min",
    ).astype(int)
    return base.sort_values("consensus_rank")
