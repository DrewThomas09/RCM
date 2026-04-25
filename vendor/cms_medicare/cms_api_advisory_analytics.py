"""CMS Data API analytics for private-equity style advisory research.

Adds repeatable analytics outputs to support provider-market screening:
- Correlation matrices + heatmaps
- Provider opportunity scoring with concentration and volatility nuance
- Year-over-year trend and acceleration metrics
- State/provider heatmaps for geographic pricing and volume patterns
- Quality filtering, outlier clipping, and an auto-generated memo summary
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


COLUMN_ALIASES = {
    "provider_type": ["provider_type", "rndrng_prvdr_type"],
    "state": ["nppes_provider_state", "rndrng_prvdr_state_abrvtn"],
    "year": ["year", "rndrng_prvdr_geo_lvl"],
    "total_services": ["total_services", "tot_srvcs"],
    "total_unique_benes": ["total_unique_benes", "tot_benes"],
    "total_submitted_chrg_amt": ["total_submitted_chrg_amt", "tot_submitted_chrg_amt"],
    "total_medicare_payment_amt": ["total_medicare_payment_amt", "tot_mdcr_pymt_amt"],
    "beneficiary_average_age": ["beneficiary_average_age", "bene_avg_age"],
    "beneficiary_average_risk_score": [
        "beneficiary_average_risk_score",
        "Beneficiary_Average_Risk_Score",
    ],
}

DEFAULT_NUMERIC_FIELDS = [
    "total_services",
    "total_unique_benes",
    "total_submitted_chrg_amt",
    "total_medicare_payment_amt",
    "beneficiary_average_age",
    "beneficiary_average_risk_score",
]


def _resolve_col(df: pd.DataFrame, canonical: str, override: Optional[str] = None) -> Optional[str]:
    if override and override in df.columns:
        return override
    for candidate in COLUMN_ALIASES.get(canonical, [canonical]):
        if candidate in df.columns:
            return candidate
    return None


def fetch_cms_api_pages(
    endpoint: str,
    limit: int = 5000,
    max_pages: int = 10,
    offset_param: str = "offset",
    limit_param: str = "size",
    extra_params: Optional[Dict[str, str]] = None,
    retry_count: int = 2,
    retry_backoff_s: float = 1.0,
) -> pd.DataFrame:
    """Fetch paginated JSON data from a CMS Data API endpoint."""
    frames: List[pd.DataFrame] = []

    for page in range(max_pages):
        offset = page * limit
        params = {offset_param: offset, limit_param: limit}
        if extra_params:
            params.update(extra_params)
        query = urlencode(params)
        url = endpoint + ("&" if "?" in endpoint else "?") + query

        payload = None
        last_exc: Optional[Exception] = None
        for attempt in range(retry_count + 1):
            try:
                with urlopen(url, timeout=45) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except (HTTPError, URLError, TimeoutError) as exc:
                last_exc = exc
                if attempt == retry_count:
                    raise RuntimeError("Unable to fetch CMS API data: %s" % exc) from exc
                time.sleep(retry_backoff_s * (attempt + 1))

        if payload is None and last_exc is not None:
            raise RuntimeError("Unable to fetch CMS API data: %s" % last_exc)

        if not payload:
            break

        frame = pd.DataFrame(payload)
        frames.append(frame)

        if len(frame) < limit:
            break

    if not frames:
        raise RuntimeError("CMS API returned no rows for endpoint: %s" % endpoint)

    return pd.concat(frames, ignore_index=True)


def _select_numeric_columns(df: pd.DataFrame, requested: Iterable[str]) -> List[str]:
    available = [col for col in requested if col in df.columns]
    for col in available:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return available


def _percentile_rank(series: pd.Series) -> pd.Series:
    """Return percentile rank [0,1] handling all-null edge cases."""
    if series.notna().sum() == 0:
        return pd.Series(0.0, index=series.index)
    return series.rank(pct=True, method="average")


def standardize_columns(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    out = df.copy()
    rename_map = {}
    for canonical, override in [
        ("provider_type", args.provider_col),
        ("state", args.state_col),
        ("year", args.year_col),
    ]:
        resolved = _resolve_col(out, canonical, override=override)
        if resolved and resolved != canonical:
            rename_map[resolved] = canonical

    for field in DEFAULT_NUMERIC_FIELDS:
        resolved = _resolve_col(out, field)
        if resolved and resolved != field:
            rename_map[resolved] = field

    if rename_map:
        out = out.rename(columns=rename_map)

    return out


def filter_year_range(df: pd.DataFrame, min_year: Optional[int], max_year: Optional[int]) -> pd.DataFrame:
    """Filter rows by inclusive year range when year is available."""
    if "year" not in df.columns:
        return df
    out = df.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    if min_year is not None:
        out = out[out["year"] >= min_year]
    if max_year is not None:
        out = out[out["year"] <= max_year]
    return out


def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if {"total_medicare_payment_amt", "total_services"}.issubset(out.columns):
        out["payment_per_service"] = (
            pd.to_numeric(out["total_medicare_payment_amt"], errors="coerce")
            / pd.to_numeric(out["total_services"], errors="coerce").replace(0, np.nan)
        )

    if {"total_medicare_payment_amt", "total_unique_benes"}.issubset(out.columns):
        out["payment_per_bene"] = (
            pd.to_numeric(out["total_medicare_payment_amt"], errors="coerce")
            / pd.to_numeric(out["total_unique_benes"], errors="coerce").replace(0, np.nan)
        )

    if {"total_submitted_chrg_amt", "total_medicare_payment_amt"}.issubset(out.columns):
        out["charge_to_payment_ratio"] = (
            pd.to_numeric(out["total_submitted_chrg_amt"], errors="coerce")
            / pd.to_numeric(out["total_medicare_payment_amt"], errors="coerce").replace(0, np.nan)
        )

    if "payment_per_bene" in out.columns:
        out["log_payment_per_bene"] = np.log10(out["payment_per_bene"].replace(0, np.nan))

    return out


def apply_quality_filters(df: pd.DataFrame, min_services: int, min_benes: int) -> pd.DataFrame:
    """Drop low-signal rows so rankings are less noisy for advisory work."""
    out = df.copy()
    _select_numeric_columns(out, ["total_services", "total_unique_benes"])
    if "total_services" in out.columns:
        out = out[out["total_services"].fillna(0) >= min_services]
    if "total_unique_benes" in out.columns:
        out = out[out["total_unique_benes"].fillna(0) >= min_benes]
    return out


def winsorize_metrics(df: pd.DataFrame, upper_quantile: float) -> pd.DataFrame:
    """Clip heavy-tailed payment fields to improve comparability."""
    out = df.copy()
    if upper_quantile >= 1.0:
        return out
    for col in ["payment_per_service", "payment_per_bene", "charge_to_payment_ratio"]:
        if col in out.columns:
            cap = out[col].quantile(upper_quantile)
            out[col] = out[col].clip(upper=cap)
    return out


def validate_runtime_inputs(args: argparse.Namespace) -> None:
    """Validate CLI/runtime knobs early to avoid silent bad runs."""
    if args.limit <= 0:
        raise ValueError("--limit must be > 0")
    if args.max_pages <= 0:
        raise ValueError("--max-pages must be > 0")
    if args.top_n <= 0:
        raise ValueError("--top-n must be > 0")
    if args.min_services < 0 or args.min_benes < 0:
        raise ValueError("--min-services and --min-benes must be >= 0")
    if not (0 < args.winsor_upper_quantile <= 1.0):
        raise ValueError("--winsor-upper-quantile must be in (0, 1]")
    if args.watch_min_growth < -1.0:
        raise ValueError("--watch-min-growth must be >= -1.0")
    if args.watch_max_volatility <= 0:
        raise ValueError("--watch-max-volatility must be > 0")
    if args.min_state_provider_rows <= 0:
        raise ValueError("--min-state-provider-rows must be > 0")
    if args.benchmark_z_threshold <= 0:
        raise ValueError("--benchmark-z-threshold must be > 0")
    if args.retry_count < 0:
        raise ValueError("--retry-count must be >= 0")
    if args.retry_backoff_s <= 0:
        raise ValueError("--retry-backoff-s must be > 0")
    if args.min_year is not None and args.max_year is not None and args.min_year > args.max_year:
        raise ValueError("--min-year cannot be greater than --max-year")
    if (args.baseline_year is None) ^ (args.compare_year is None):
        raise ValueError("--baseline-year and --compare-year must be provided together")
    if args.baseline_year is not None and args.compare_year is not None and args.baseline_year == args.compare_year:
        raise ValueError("--baseline-year and --compare-year must be different")
    if not (0 <= args.downside_shock < 1):
        raise ValueError("--downside-shock must be in [0,1)")
    if args.upside_shock < 0:
        raise ValueError("--upside-shock must be >= 0")
    if args.momentum_min_years < 2:
        raise ValueError("--momentum-min-years must be >= 2")
    if args.anomaly_z_threshold <= 0:
        raise ValueError("--anomaly-z-threshold must be > 0")
    if args.anomaly_min_rows <= 0:
        raise ValueError("--anomaly-min-rows must be > 0")
    if args.regime_strong_growth <= -1:
        raise ValueError("--regime-strong-growth must be > -1")
    if args.regime_high_volatility <= 0:
        raise ValueError("--regime-high-volatility must be > 0")
    if not (0 <= args.white_space_min_percentile <= 1):
        raise ValueError("--white-space-min-percentile must be in [0,1]")
    if args.scenario_downside_step <= 0 or args.scenario_upside_step <= 0:
        raise ValueError("--scenario-downside-step and --scenario-upside-step must be > 0")
    if not (0 <= args.geo_dependency_threshold <= 1):
        raise ValueError("--geo-dependency-threshold must be in [0,1]")
    if args.reliability_min_observations < 2:
        raise ValueError("--reliability-min-observations must be >= 2")
    if not (0 <= args.scenario_min_win_share <= 1):
        raise ValueError("--scenario-min-win-share must be in [0,1]")


def provider_screen(df: pd.DataFrame) -> pd.DataFrame:
    if "provider_type" not in df.columns:
        raise ValueError("Expected provider_type column for screening output")

    _select_numeric_columns(
        df,
        [
            "total_services",
            "total_unique_benes",
            "total_medicare_payment_amt",
            "beneficiary_average_risk_score",
            "payment_per_service",
            "payment_per_bene",
        ],
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
            median_risk=("beneficiary_average_risk_score", "median"),
        )
        .replace([np.inf, -np.inf], np.nan)
    )

    market_total = grouped["total_payment"].sum()
    grouped["market_share"] = grouped["total_payment"] / market_total if market_total else 0
    grouped["hhi_component"] = grouped["market_share"] ** 2

    def norm(s: pd.Series) -> pd.Series:
        rng = s.max() - s.min()
        if pd.isna(rng) or rng == 0:
            return pd.Series(0.0, index=s.index)
        return (s - s.min()) / rng

    grouped["scale_score"] = norm(np.log1p(grouped["total_payment"]))
    grouped["margin_proxy_score"] = norm(grouped["median_payment_per_service"])
    grouped["acuity_score"] = norm(grouped["median_risk"])
    grouped["fragmentation_score"] = 1 - norm(grouped["hhi_component"])
    grouped["opportunity_score"] = (
        0.35 * grouped["scale_score"]
        + 0.30 * grouped["margin_proxy_score"]
        + 0.20 * grouped["acuity_score"]
        + 0.15 * grouped["fragmentation_score"]
    )
    grouped["payment_percentile"] = _percentile_rank(grouped["total_payment"])
    grouped["risk_percentile"] = _percentile_rank(grouped["median_risk"])
    grouped["opportunity_percentile"] = _percentile_rank(grouped["opportunity_score"])

    return grouped.sort_values("opportunity_score", ascending=False)


def state_provider_opportunities(df: pd.DataFrame, min_rows: int = 20) -> pd.DataFrame:
    """Score opportunities at provider-type x state granularity for regional strategy."""
    required = {"provider_type", "state", "total_medicare_payment_amt", "payment_per_service"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _select_numeric_columns(work, ["total_medicare_payment_amt", "payment_per_service", "beneficiary_average_risk_score"])

    grouped = (
        work.groupby(["provider_type", "state"], as_index=False)
        .agg(
            row_count=("provider_type", "count"),
            total_payment=("total_medicare_payment_amt", "sum"),
            median_payment_per_service=("payment_per_service", "median"),
            median_risk=("beneficiary_average_risk_score", "median"),
        )
    )
    grouped = grouped[grouped["row_count"] >= min_rows]
    if grouped.empty:
        return grouped

    def norm(s: pd.Series) -> pd.Series:
        rng = s.max() - s.min()
        if pd.isna(rng) or rng == 0:
            return pd.Series(0.0, index=s.index)
        return (s - s.min()) / rng

    grouped["regional_scale_score"] = norm(np.log1p(grouped["total_payment"]))
    grouped["regional_margin_score"] = norm(grouped["median_payment_per_service"])
    grouped["regional_acuity_score"] = norm(grouped["median_risk"])
    grouped["regional_opportunity_score"] = (
        0.45 * grouped["regional_scale_score"]
        + 0.35 * grouped["regional_margin_score"]
        + 0.20 * grouped["regional_acuity_score"]
    )
    grouped["regional_opportunity_percentile"] = _percentile_rank(grouped["regional_opportunity_score"])
    return grouped.sort_values("regional_opportunity_score", ascending=False)


def provider_state_benchmark_flags(
    df: pd.DataFrame,
    z_threshold: float = 1.5,
    min_rows: int = 20,
) -> pd.DataFrame:
    """Flag provider-state combos with unusually high/low payment-per-service vs peer provider type."""
    required = {"provider_type", "state", "payment_per_service"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _select_numeric_columns(work, ["payment_per_service", "total_medicare_payment_amt"])

    provider_peer = (
        work.groupby("provider_type", as_index=False)["payment_per_service"]
        .agg(peer_median="median", peer_std="std")
    )

    grouped = (
        work.groupby(["provider_type", "state"], as_index=False)
        .agg(
            row_count=("provider_type", "count"),
            state_median_payment_per_service=("payment_per_service", "median"),
            state_total_payment=("total_medicare_payment_amt", "sum"),
        )
    )
    grouped = grouped[grouped["row_count"] >= min_rows]
    if grouped.empty:
        return grouped

    merged = grouped.merge(provider_peer, on="provider_type", how="left")
    merged["peer_std"] = merged["peer_std"].replace(0, np.nan)
    merged["service_price_z"] = (
        merged["state_median_payment_per_service"] - merged["peer_median"]
    ) / merged["peer_std"]

    merged["benchmark_flag"] = "normal"
    merged.loc[merged["service_price_z"] >= z_threshold, "benchmark_flag"] = "high_price"
    merged.loc[merged["service_price_z"] <= -z_threshold, "benchmark_flag"] = "low_price"
    bench_order = pd.CategoricalDtype(["high_price", "normal", "low_price"], ordered=True)
    merged["benchmark_flag"] = merged["benchmark_flag"].astype(bench_order)

    return merged.sort_values(["benchmark_flag", "service_price_z"], ascending=[True, False])


def yearly_trends(df: pd.DataFrame) -> pd.DataFrame:
    if "year" not in df.columns or "provider_type" not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    _select_numeric_columns(work, ["year", "total_medicare_payment_amt", "total_services", "total_unique_benes"])
    work = work.dropna(subset=["year", "provider_type", "total_medicare_payment_amt"])
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby(["year", "provider_type"], as_index=False)[
            ["total_medicare_payment_amt", "total_services", "total_unique_benes"]
        ]
        .sum()
        .sort_values(["provider_type", "year"])
    )

    grouped["payment_yoy_pct"] = grouped.groupby("provider_type")["total_medicare_payment_amt"].pct_change()
    grouped["services_yoy_pct"] = grouped.groupby("provider_type")["total_services"].pct_change()
    grouped["bene_yoy_pct"] = grouped.groupby("provider_type")["total_unique_benes"].pct_change()
    grouped["payment_yoy_accel"] = grouped.groupby("provider_type")["payment_yoy_pct"].diff()

    return grouped


def provider_trend_shift(
    trends: pd.DataFrame,
    baseline_year: Optional[int],
    compare_year: Optional[int],
) -> pd.DataFrame:
    """Compare provider payment trends between two years for inflection spotting."""
    if trends.empty or baseline_year is None or compare_year is None:
        return pd.DataFrame()

    work = trends.copy()
    work["year"] = pd.to_numeric(work["year"], errors="coerce")
    base = work[work["year"] == baseline_year][["provider_type", "total_medicare_payment_amt"]].rename(
        columns={"total_medicare_payment_amt": "payment_baseline"}
    )
    comp = work[work["year"] == compare_year][["provider_type", "total_medicare_payment_amt"]].rename(
        columns={"total_medicare_payment_amt": "payment_compare"}
    )

    merged = base.merge(comp, on="provider_type", how="inner")
    if merged.empty:
        return merged

    merged["payment_delta"] = merged["payment_compare"] - merged["payment_baseline"]
    merged["payment_delta_pct"] = merged["payment_delta"] / merged["payment_baseline"].replace(0, np.nan)
    merged["abs_delta_rank"] = merged["payment_delta"].abs().rank(ascending=False, method="dense")
    return merged.sort_values("payment_delta", ascending=False)


def provider_volatility(trends: pd.DataFrame) -> pd.DataFrame:
    if trends.empty:
        return pd.DataFrame()
    vol = (
        trends.groupby("provider_type", as_index=False)
        .agg(
            yoy_payment_volatility=("payment_yoy_pct", "std"),
            yoy_services_volatility=("services_yoy_pct", "std"),
            avg_payment_growth=("payment_yoy_pct", "mean"),
            last_payment_growth=("payment_yoy_pct", "last"),
        )
        .sort_values("yoy_payment_volatility", ascending=False)
    )
    return vol


def provider_trend_reliability(trends: pd.DataFrame, min_observations: int = 3) -> pd.DataFrame:
    """Score how statistically reliable provider growth patterns are over time."""
    if trends.empty or "provider_type" not in trends.columns:
        return pd.DataFrame()

    work = trends.copy()
    for col in ["payment_yoy_pct", "services_yoy_pct", "bene_yoy_pct", "payment_yoy_accel"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    rel = (
        work.groupby("provider_type", as_index=False)
        .agg(
            yoy_obs_count=("payment_yoy_pct", lambda s: int(s.notna().sum())),
            yoy_growth_mean=("payment_yoy_pct", "mean"),
            yoy_growth_std=("payment_yoy_pct", "std"),
            yoy_growth_median=("payment_yoy_pct", "median"),
            positive_growth_share=("payment_yoy_pct", lambda s: float((s > 0).mean()) if s.notna().any() else np.nan),
            acceleration_mean=("payment_yoy_accel", "mean"),
        )
    )
    rel = rel[rel["yoy_obs_count"] >= min_observations]
    if rel.empty:
        return rel

    rel["growth_signal_to_noise"] = rel["yoy_growth_mean"] / rel["yoy_growth_std"].replace(0, np.nan)
    rel["reliability_score"] = (
        0.40 * rel["growth_signal_to_noise"].fillna(0)
        + 0.30 * rel["positive_growth_share"].fillna(0)
        + 0.20 * rel["yoy_growth_median"].fillna(0)
        - 0.10 * rel["yoy_growth_std"].fillna(0)
    )
    rel["reliability_percentile"] = _percentile_rank(rel["reliability_score"])
    return rel.sort_values("reliability_score", ascending=False)


def growth_volatility_watchlist(
    volatility: pd.DataFrame,
    min_growth: float = 0.05,
    max_volatility: float = 0.35,
) -> pd.DataFrame:
    """Flag providers with attractive growth-to-risk profile and high-risk outliers."""
    if volatility.empty:
        return pd.DataFrame()

    out = volatility.copy()
    for col in ["last_payment_growth", "yoy_payment_volatility"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

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

    out["growth_to_risk"] = out["last_payment_growth"] / out["yoy_payment_volatility"].replace(0, np.nan)
    bucket_order = pd.CategoricalDtype(["priority", "monitor", "high_risk"], ordered=True)
    out["watchlist_bucket"] = out["watchlist_bucket"].astype(bucket_order)
    return out.sort_values(["watchlist_bucket", "growth_to_risk"], ascending=[True, False])


def provider_momentum_profile(trends: pd.DataFrame, min_years: int = 3) -> pd.DataFrame:
    """Profile growth consistency to separate durable trends from one-year spikes."""
    if trends.empty:
        return pd.DataFrame()

    work = trends.copy()
    for col in ["payment_yoy_pct", "payment_yoy_accel", "total_medicare_payment_amt"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    grouped = (
        work.groupby("provider_type", as_index=False)
        .agg(
            observed_years=("year", "nunique"),
            positive_yoy_share=("payment_yoy_pct", lambda s: float((s > 0).mean()) if s.notna().any() else np.nan),
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
        (grouped["latest_payment"] / grouped["first_payment"].replace(0, np.nan))
        ** (1 / (grouped["observed_years"] - 1).clip(lower=1))
    ) - 1
    grouped["consistency_score"] = (
        grouped["positive_yoy_share"].fillna(0) * 0.45
        + grouped["yoy_growth_median"].fillna(0) * 0.25
        + grouped["growth_cagr"].fillna(0) * 0.20
        - grouped["yoy_growth_volatility"].fillna(0) * 0.10
    )
    grouped["consistency_percentile"] = grouped["consistency_score"].rank(pct=True)
    return grouped.sort_values("consistency_score", ascending=False)


def detect_state_provider_anomalies(
    df: pd.DataFrame,
    z_threshold: float = 2.5,
    min_rows: int = 15,
) -> pd.DataFrame:
    """Detect unusually priced provider-state-year cohorts versus provider peers."""
    needed = {"provider_type", "state", "year", "payment_per_service", "total_medicare_payment_amt"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _select_numeric_columns(work, ["payment_per_service", "total_medicare_payment_amt", "year"])
    work = work.dropna(subset=["provider_type", "state", "year", "payment_per_service"])
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby(["provider_type", "state", "year"], as_index=False)
        .agg(
            row_count=("provider_type", "count"),
            median_payment_per_service=("payment_per_service", "median"),
            total_payment=("total_medicare_payment_amt", "sum"),
        )
    )
    grouped = grouped[grouped["row_count"] >= min_rows]
    if grouped.empty:
        return grouped

    peer = (
        grouped.groupby(["provider_type", "year"], as_index=False)["median_payment_per_service"]
        .agg(peer_median="median", peer_std="std")
    )
    out = grouped.merge(peer, on=["provider_type", "year"], how="left")
    out["peer_std"] = out["peer_std"].replace(0, np.nan)
    out["service_z"] = (out["median_payment_per_service"] - out["peer_median"]) / out["peer_std"]
    out["anomaly_flag"] = "normal"
    out.loc[out["service_z"] >= z_threshold, "anomaly_flag"] = "cost_spike"
    out.loc[out["service_z"] <= -z_threshold, "anomaly_flag"] = "cost_trough"
    out["anomaly_magnitude"] = out["service_z"].abs()
    return out.sort_values(["anomaly_magnitude", "total_payment"], ascending=[False, False])


def provider_regime_classification(
    momentum: pd.DataFrame,
    volatility: pd.DataFrame,
    strong_growth_threshold: float = 0.12,
    weak_growth_threshold: float = 0.0,
    high_vol_threshold: float = 0.35,
) -> pd.DataFrame:
    """Classify provider types into operating regimes for investment posture."""
    if momentum.empty and volatility.empty:
        return pd.DataFrame()

    base = pd.DataFrame()
    if not momentum.empty:
        keep = [
            c
            for c in [
                "provider_type",
                "consistency_score",
                "growth_cagr",
                "positive_yoy_share",
                "yoy_growth_volatility",
            ]
            if c in momentum.columns
        ]
        base = momentum[keep].copy()

    if not volatility.empty:
        vkeep = [c for c in ["provider_type", "last_payment_growth", "yoy_payment_volatility"] if c in volatility.columns]
        vdf = volatility[vkeep].copy()
        base = vdf if base.empty else base.merge(vdf, on="provider_type", how="outer")

    if base.empty or "provider_type" not in base.columns:
        return pd.DataFrame()

    for col in ["growth_cagr", "last_payment_growth", "yoy_payment_volatility", "consistency_score"]:
        if col not in base.columns:
            base[col] = np.nan
        base[col] = pd.to_numeric(base[col], errors="coerce")

    growth_proxy = base["last_payment_growth"].fillna(base["growth_cagr"])
    vol_proxy = base["yoy_payment_volatility"].fillna(base.get("yoy_growth_volatility", np.nan))

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
    regime_order = pd.CategoricalDtype(
        ["durable_growth", "steady_compounders", "emerging_volatile", "stagnant", "declining_risk"],
        ordered=True,
    )
    base["regime"] = base["regime"].astype(regime_order)
    return base.sort_values(["regime", "regime_rank_score"], ascending=[True, False])


def market_concentration_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute market concentration by state/year for PE-style rollup screening."""
    required = {"state", "provider_type", "total_medicare_payment_amt"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    if "year" not in work.columns:
        work["year"] = "all"
    _select_numeric_columns(work, ["total_medicare_payment_amt"])
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
    return out.sort_values(["hhi", "cr3"], ascending=False)


def state_volatility_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Measure payment volatility by state using yearly totals."""
    if not {"state", "year", "total_medicare_payment_amt"}.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _select_numeric_columns(work, ["year", "total_medicare_payment_amt"])
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
    )
    return out


def state_growth_summary(df: pd.DataFrame) -> pd.DataFrame:
    """State-level trend summary for identifying geographic expansion targets."""
    if not {"state", "year", "total_medicare_payment_amt"}.issubset(df.columns):
        return pd.DataFrame()
    work = df.copy()
    _select_numeric_columns(work, ["year", "total_medicare_payment_amt"])
    work = work.dropna(subset=["state", "year", "total_medicare_payment_amt"])
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby(["state", "year"], as_index=False)["total_medicare_payment_amt"]
        .sum()
        .sort_values(["state", "year"])
    )
    grouped["state_payment_yoy_pct"] = grouped.groupby("state")["total_medicare_payment_amt"].pct_change()

    summary = (
        grouped.groupby("state", as_index=False)
        .agg(
            avg_state_growth=("state_payment_yoy_pct", "mean"),
            latest_state_growth=("state_payment_yoy_pct", "last"),
            latest_payment=("total_medicare_payment_amt", "last"),
        )
        .sort_values(["latest_state_growth", "latest_payment"], ascending=False)
    )
    return summary


def state_portfolio_fit(
    state_growth: pd.DataFrame,
    state_volatility: pd.DataFrame,
    concentration: pd.DataFrame,
) -> pd.DataFrame:
    """Blend state momentum, stability, and concentration into expansion fit scores."""
    if state_growth.empty:
        return pd.DataFrame()

    fit = state_growth.copy()
    if not state_volatility.empty:
        keep = [c for c in ["state", "yoy_volatility", "latest_growth"] if c in state_volatility.columns]
        fit = fit.merge(state_volatility[keep], on="state", how="left", suffixes=("", "_vol"))

    if not concentration.empty:
        conc_latest = concentration.sort_values(["state", "year"]).groupby("state", as_index=False).tail(1)
        keep = [col for col in ["state", "hhi", "cr3", "provider_type_count"] if col in conc_latest.columns]
        fit = fit.merge(conc_latest[keep], on="state", how="left")

    for col in ["latest_state_growth", "avg_state_growth", "latest_payment", "yoy_volatility", "hhi"]:
        if col not in fit.columns:
            fit[col] = np.nan
        fit[col] = pd.to_numeric(fit[col], errors="coerce")

    fit["stability_score"] = 1 / (1 + fit["yoy_volatility"].clip(lower=0).fillna(fit["yoy_volatility"].median()))
    fit["fragmentation_bonus"] = 1 - fit["hhi"].fillna(fit["hhi"].median())
    fit["state_fit_score"] = (
        0.35 * fit["latest_state_growth"].fillna(0)
        + 0.20 * fit["avg_state_growth"].fillna(0)
        + 0.20 * np.log1p(fit["latest_payment"].clip(lower=0).fillna(0))
        + 0.15 * fit["stability_score"].fillna(0)
        + 0.10 * fit["fragmentation_bonus"].fillna(0)
    )
    fit["state_fit_percentile"] = _percentile_rank(fit["state_fit_score"])
    return fit.sort_values("state_fit_score", ascending=False)


def state_provider_white_space(
    regional_scores: pd.DataFrame,
    state_fit: pd.DataFrame,
    benchmark_flags: pd.DataFrame,
    min_percentile: float = 0.70,
) -> pd.DataFrame:
    """Identify provider-state expansion white-space opportunities with blended evidence."""
    if regional_scores.empty:
        return pd.DataFrame()

    work = regional_scores.copy()
    needed = {"provider_type", "state", "regional_opportunity_score"}
    if not needed.issubset(work.columns):
        return pd.DataFrame()

    if "regional_opportunity_percentile" not in work.columns:
        work["regional_opportunity_percentile"] = _percentile_rank(work["regional_opportunity_score"])

    if not state_fit.empty and {"state", "state_fit_percentile"}.issubset(state_fit.columns):
        work = work.merge(state_fit[["state", "state_fit_percentile"]], on="state", how="left")
    else:
        work["state_fit_percentile"] = np.nan

    work["state_fit_percentile"] = pd.to_numeric(work["state_fit_percentile"], errors="coerce").fillna(0.5)

    bench_signal = pd.DataFrame(columns=["provider_type", "state", "benchmark_signal"])
    if not benchmark_flags.empty and {"provider_type", "state", "benchmark_flag"}.issubset(benchmark_flags.columns):
        b = benchmark_flags[["provider_type", "state", "benchmark_flag"]].copy()
        b["benchmark_signal"] = b["benchmark_flag"].astype(str).map({"low_price": 1.0, "normal": 0.0, "high_price": -1.0}).fillna(0.0)
        bench_signal = b.groupby(["provider_type", "state"], as_index=False)["benchmark_signal"].mean()

    work = work.merge(bench_signal, on=["provider_type", "state"], how="left")
    work["benchmark_signal"] = pd.to_numeric(work["benchmark_signal"], errors="coerce").fillna(0.0)

    work["white_space_score"] = (
        0.55 * pd.to_numeric(work["regional_opportunity_percentile"], errors="coerce").fillna(0)
        + 0.30 * work["state_fit_percentile"]
        + 0.15 * ((work["benchmark_signal"] + 1) / 2)
    )
    work["white_space_percentile"] = _percentile_rank(work["white_space_score"])
    work = work[work["white_space_percentile"] >= min_percentile]
    return work.sort_values("white_space_score", ascending=False)


def provider_geo_dependency(df: pd.DataFrame, dependency_threshold: float = 0.50) -> pd.DataFrame:
    """Measure provider concentration risk by dependence on a single state."""
    required = {"provider_type", "state", "total_medicare_payment_amt"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _select_numeric_columns(work, ["total_medicare_payment_amt"])
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
        top_state = g.loc[g["total_medicare_payment_amt"].idxmax(), "state"]
        top_share = float(shares.iloc[0])
        hhi_geo = float((shares ** 2).sum())
        rows.append(
            {
                "provider_type": provider,
                "state_count": int(g["state"].nunique()),
                "top_state": str(top_state),
                "top_state_share": top_share,
                "geo_hhi": hhi_geo,
                "geo_dependency_flag": bool(top_share >= dependency_threshold),
            }
        )

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out["geo_dependency_percentile"] = _percentile_rank(out["top_state_share"])
    return out.sort_values("top_state_share", ascending=False)


def state_provider_heatmap(df: pd.DataFrame, value_col: str = "payment_per_bene") -> pd.DataFrame:
    if not {"state", "provider_type", value_col}.issubset(df.columns):
        return pd.DataFrame()
    pivot = df.pivot_table(
        index="provider_type",
        columns="state",
        values=value_col,
        aggfunc="median",
    )
    return pivot


def provider_value_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Assess provider-type value via risk-adjusted payment efficiency."""
    required = {"provider_type", "payment_per_bene", "beneficiary_average_risk_score", "total_medicare_payment_amt"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    _select_numeric_columns(work, ["payment_per_bene", "beneficiary_average_risk_score", "total_medicare_payment_amt"])

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

    grouped["risk_adjusted_cost"] = grouped["median_payment_per_bene"] / grouped["median_risk"].replace(0, np.nan)
    grouped["value_score"] = 1 / grouped["risk_adjusted_cost"].replace(0, np.nan)
    grouped["value_percentile"] = _percentile_rank(grouped["value_score"])
    return grouped.sort_values("value_score", ascending=False)


def provider_investability_summary(
    scores: pd.DataFrame,
    value_summary: pd.DataFrame,
    volatility: pd.DataFrame,
) -> pd.DataFrame:
    """Create a blended provider investability ranking (growth/value/stability)."""
    if scores.empty:
        return pd.DataFrame()

    base = scores.reset_index().rename(columns={"index": "provider_type"})
    if "provider_type" not in base.columns:
        return pd.DataFrame()

    keep = ["provider_type", "opportunity_score", "opportunity_percentile", "total_payment"]
    base = base[[c for c in keep if c in base.columns]].copy()

    if not value_summary.empty:
        vkeep = ["provider_type", "value_score", "value_percentile"]
        base = base.merge(value_summary[[c for c in vkeep if c in value_summary.columns]], on="provider_type", how="left")

    if not volatility.empty:
        st = volatility.copy()
        if "yoy_payment_volatility" in st.columns:
            st["stability_score"] = 1 / (1 + st["yoy_payment_volatility"].clip(lower=0))
        skeep = ["provider_type", "stability_score", "yoy_payment_volatility", "last_payment_growth"]
        base = base.merge(st[[c for c in skeep if c in st.columns]], on="provider_type", how="left")

    for col in ["value_score", "stability_score", "opportunity_score"]:
        if col not in base.columns:
            base[col] = np.nan
        base[col] = pd.to_numeric(base[col], errors="coerce")

    # rank-normalized blend
    base["opp_rank"] = _percentile_rank(base["opportunity_score"])
    base["value_rank"] = _percentile_rank(base["value_score"])
    base["stability_rank"] = _percentile_rank(base["stability_score"])
    base["investability_score"] = 0.45 * base["opp_rank"] + 0.35 * base["value_rank"] + 0.20 * base["stability_rank"]

    return base.sort_values("investability_score", ascending=False)


def provider_stress_test(
    investability: pd.DataFrame,
    downside_shock: float = 0.15,
    upside_shock: float = 0.10,
) -> pd.DataFrame:
    """Simple scenario analysis for investability under payment shocks."""
    if investability.empty:
        return pd.DataFrame()

    out = investability.copy()
    if "total_payment" not in out.columns:
        out["total_payment"] = np.nan
    if "investability_score" not in out.columns:
        out["investability_score"] = np.nan

    out["downside_payment"] = out["total_payment"] * (1 - downside_shock)
    out["upside_payment"] = out["total_payment"] * (1 + upside_shock)

    # blended stress score penalizes downside, rewards upside lightly
    out["stress_adjusted_score"] = (
        out["investability_score"] * (1 - downside_shock) + 0.25 * out["investability_score"] * upside_shock
    )
    out["stress_rank"] = out["stress_adjusted_score"].rank(ascending=False, method="dense")
    return out.sort_values("stress_adjusted_score", ascending=False)


def stress_scenario_grid(
    investability: pd.DataFrame,
    downsides: Optional[List[float]] = None,
    upsides: Optional[List[float]] = None,
) -> pd.DataFrame:
    """Run a compact shock grid to understand ranking robustness across scenarios."""
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
            top_provider = str(st.iloc[0]["provider_type"]) if "provider_type" in st.columns else None
            rows.append(
                {
                    "downside_shock": float(d),
                    "upside_shock": float(u),
                    "scenario_label": f"d{int(d*100)}_u{int(u*100)}",
                    "top_provider": top_provider,
                    "top_stress_score": float(st.iloc[0].get("stress_adjusted_score", np.nan)),
                    "median_stress_score": float(pd.to_numeric(st["stress_adjusted_score"], errors="coerce").median()),
                    "mean_stress_score": float(pd.to_numeric(st["stress_adjusted_score"], errors="coerce").mean()),
                }
            )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["downside_shock", "upside_shock"]).reset_index(drop=True)


def provider_operating_posture(
    consensus: pd.DataFrame,
    trend_reliability: pd.DataFrame,
    geo_dependency: pd.DataFrame,
    scenario_grid: pd.DataFrame,
    scenario_min_win_share: float = 0.30,
) -> pd.DataFrame:
    """Classify providers into operating postures by return quality and concentration risk."""
    if consensus.empty:
        return pd.DataFrame()

    base = consensus.copy()
    if "provider_type" not in base.columns:
        return pd.DataFrame()

    keep = [c for c in ["provider_type", "consensus_score", "consensus_percentile"] if c in base.columns]
    base = base[keep].copy()

    if not trend_reliability.empty:
        rkeep = [c for c in ["provider_type", "reliability_score", "reliability_percentile"] if c in trend_reliability.columns]
        base = base.merge(trend_reliability[rkeep], on="provider_type", how="left")

    if not geo_dependency.empty:
        gkeep = [c for c in ["provider_type", "top_state_share", "geo_dependency_flag"] if c in geo_dependency.columns]
        base = base.merge(geo_dependency[gkeep], on="provider_type", how="left")

    win_rate = pd.DataFrame(columns=["provider_type", "scenario_win_share"])
    if not scenario_grid.empty and "top_provider" in scenario_grid.columns:
        vc = scenario_grid["top_provider"].value_counts(dropna=True)
        if not vc.empty:
            win_rate = vc.rename_axis("provider_type").reset_index(name="scenario_win_count")
            win_rate["scenario_win_share"] = win_rate["scenario_win_count"] / float(len(scenario_grid))

    base = base.merge(win_rate[[c for c in ["provider_type", "scenario_win_share"] if c in win_rate.columns]], on="provider_type", how="left")

    for col in ["consensus_percentile", "reliability_percentile", "top_state_share", "scenario_win_share"]:
        if col not in base.columns:
            base[col] = np.nan
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

    posture_order = pd.CategoricalDtype(
        ["scenario_leader", "resilient_core", "balanced", "growth_optional", "concentration_risk"],
        ordered=True,
    )
    base["operating_posture"] = base["operating_posture"].astype(posture_order)
    base["posture_score"] = (
        0.45 * base["consensus_percentile"].fillna(0)
        + 0.25 * base["reliability_percentile"].fillna(0)
        + 0.20 * base["scenario_win_share"].fillna(0)
        - 0.10 * base["top_state_share"].fillna(0)
    )
    return base.sort_values(["operating_posture", "posture_score"], ascending=[True, False])


def provider_consensus_rank(
    scores: pd.DataFrame,
    value_summary: pd.DataFrame,
    investability: pd.DataFrame,
    stress_test: pd.DataFrame,
    momentum: pd.DataFrame,
    provider_regimes: pd.DataFrame,
) -> pd.DataFrame:
    """Blend multiple ranking lenses into a robust consensus leader table."""
    tables = []

    if not scores.empty:
        sbase = scores.reset_index().rename(columns={"index": "provider_type"})
        keep = [c for c in ["provider_type", "opportunity_percentile", "opportunity_score", "total_payment"] if c in sbase.columns]
        tables.append(sbase[keep])

    if not value_summary.empty:
        keep = [c for c in ["provider_type", "value_percentile", "value_score"] if c in value_summary.columns]
        tables.append(value_summary[keep])

    if not investability.empty:
        keep = [c for c in ["provider_type", "investability_score"] if c in investability.columns]
        tables.append(investability[keep])

    if not stress_test.empty:
        keep = [c for c in ["provider_type", "stress_adjusted_score"] if c in stress_test.columns]
        tables.append(stress_test[keep])

    if not momentum.empty:
        keep = [c for c in ["provider_type", "consistency_percentile", "consistency_score"] if c in momentum.columns]
        tables.append(momentum[keep])

    if not provider_regimes.empty:
        reg = provider_regimes.copy()
        regime_boost = {
            "durable_growth": 1.00,
            "steady_compounders": 0.75,
            "emerging_volatile": 0.55,
            "stagnant": 0.30,
            "declining_risk": 0.10,
        }
        if "regime" in reg.columns:
            reg["regime_score"] = reg["regime"].astype(str).map(regime_boost)
            keep = [c for c in ["provider_type", "regime_score"] if c in reg.columns]
            tables.append(reg[keep])

    if not tables:
        return pd.DataFrame()

    out = tables[0].copy()
    for t in tables[1:]:
        out = out.merge(t, on="provider_type", how="outer")

    pct_cols = [c for c in ["opportunity_percentile", "value_percentile", "consistency_percentile"] if c in out.columns]
    for col in pct_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    score_cols = [c for c in ["investability_score", "stress_adjusted_score", "opportunity_score", "value_score", "consistency_score"] if c in out.columns]
    for col in score_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        out[f"{col}_pct"] = _percentile_rank(out[col])

    rank_inputs = []
    rank_inputs.extend(pct_cols)
    rank_inputs.extend([c for c in ["investability_score_pct", "stress_adjusted_score_pct", "regime_score"] if c in out.columns])

    if not rank_inputs:
        return pd.DataFrame()

    out["consensus_score"] = out[rank_inputs].mean(axis=1, skipna=True)
    out["consensus_percentile"] = _percentile_rank(out["consensus_score"])
    return out.sort_values("consensus_score", ascending=False)


def correlation_table(df: pd.DataFrame) -> pd.DataFrame:
    fields = _select_numeric_columns(df, DEFAULT_NUMERIC_FIELDS)
    fields.extend(
        [c for c in ["payment_per_service", "payment_per_bene", "charge_to_payment_ratio", "log_payment_per_bene"] if c in df.columns]
    )
    fields = list(dict.fromkeys(fields))
    if len(fields) < 2:
        return pd.DataFrame()
    return df[fields].corr(numeric_only=True)




def data_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Column-level missingness/zero-rate summary for auditability."""
    if df.empty:
        return pd.DataFrame(columns=["column", "dtype", "null_pct", "zero_pct", "nunique"])

    rows = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        null_pct = float(s.isna().sum() / n)
        zero_pct = 0.0
        if pd.api.types.is_numeric_dtype(s):
            zero_pct = float((s.fillna(0) == 0).sum() / n)
        rows.append(
            {
                "column": col,
                "dtype": str(s.dtype),
                "null_pct": null_pct,
                "zero_pct": zero_pct,
                "nunique": int(s.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows).sort_values(["null_pct", "zero_pct"], ascending=False)


def build_run_summary(
    enriched: pd.DataFrame,
    scores: pd.DataFrame,
    watchlist: pd.DataFrame,
    regional_scores: pd.DataFrame,
    benchmark_flags: pd.DataFrame,
    value_summary: pd.DataFrame,
    investability: pd.DataFrame,
    stress_test: pd.DataFrame,
    momentum: pd.DataFrame,
    anomalies: pd.DataFrame,
    provider_regimes: pd.DataFrame,
    state_fit: pd.DataFrame,
    consensus: pd.DataFrame,
    white_space: pd.DataFrame,
    scenario_grid: pd.DataFrame,
    geo_dependency: pd.DataFrame,
    trend_reliability: pd.DataFrame,
    operating_posture: pd.DataFrame,
) -> Dict[str, object]:
    """Machine-readable run summary for downstream orchestration/reporting."""
    summary: Dict[str, object] = {
        "row_count": int(len(enriched)),
        "min_year_in_data": int(pd.to_numeric(enriched["year"], errors="coerce").min()) if ("year" in enriched.columns and enriched["year"].notna().any()) else None,
        "max_year_in_data": int(pd.to_numeric(enriched["year"], errors="coerce").max()) if ("year" in enriched.columns and enriched["year"].notna().any()) else None,
        "provider_type_count": int(enriched["provider_type"].nunique()) if "provider_type" in enriched.columns else 0,
        "state_count": int(enriched["state"].nunique()) if "state" in enriched.columns else 0,
        "top_provider": None,
        "priority_watchlist_count": 0,
        "regional_opportunity_count": int(len(regional_scores)),
        "benchmark_flag_count": int(
            len(benchmark_flags[benchmark_flags["benchmark_flag"].astype(str) != "normal"])
        ) if (not benchmark_flags.empty and "benchmark_flag" in benchmark_flags.columns) else 0,
        "top_value_provider": None,
        "top_investability_provider": None,
        "top_stress_adjusted_provider": None,
        "momentum_leader": None,
        "anomaly_flag_count": int(len(anomalies[anomalies["anomaly_flag"] != "normal"])) if (not anomalies.empty and "anomaly_flag" in anomalies.columns) else 0,
        "durable_growth_provider_count": int((provider_regimes["regime"].astype(str) == "durable_growth").sum()) if (not provider_regimes.empty and "regime" in provider_regimes.columns) else 0,
        "top_state_fit": None,
        "top_consensus_provider": None,
        "top_white_space_state_provider": None,
        "scenario_top_provider_stability": None,
        "high_geo_dependency_count": int(geo_dependency["geo_dependency_flag"].sum()) if (not geo_dependency.empty and "geo_dependency_flag" in geo_dependency.columns) else 0,
        "highest_geo_dependency_provider": None,
        "top_reliability_provider": None,
        "resilient_core_count": int((operating_posture["operating_posture"].astype(str) == "resilient_core").sum()) if (not operating_posture.empty and "operating_posture" in operating_posture.columns) else 0,
    }
    if not scores.empty:
        summary["top_provider"] = str(scores.index[0])
        summary["top_provider_opportunity_percentile"] = float(scores.iloc[0].get("opportunity_percentile", np.nan))
    if not watchlist.empty and "watchlist_bucket" in watchlist.columns:
        summary["priority_watchlist_count"] = int((watchlist["watchlist_bucket"].astype(str) == "priority").sum())
    if not value_summary.empty and "provider_type" in value_summary.columns:
        summary["top_value_provider"] = str(value_summary.iloc[0]["provider_type"])
    if not investability.empty and "provider_type" in investability.columns:
        summary["top_investability_provider"] = str(investability.iloc[0]["provider_type"])
    if not stress_test.empty and "provider_type" in stress_test.columns:
        summary["top_stress_adjusted_provider"] = str(stress_test.iloc[0]["provider_type"])
    if not momentum.empty and "provider_type" in momentum.columns:
        summary["momentum_leader"] = str(momentum.iloc[0]["provider_type"])
    if not state_fit.empty and "state" in state_fit.columns:
        summary["top_state_fit"] = str(state_fit.iloc[0]["state"])
    if not consensus.empty and "provider_type" in consensus.columns:
        summary["top_consensus_provider"] = str(consensus.iloc[0]["provider_type"])
    if not white_space.empty and {"provider_type", "state"}.issubset(white_space.columns):
        summary["top_white_space_state_provider"] = f"{white_space.iloc[0]['provider_type']}|{white_space.iloc[0]['state']}"
    if not scenario_grid.empty and "top_provider" in scenario_grid.columns:
        freq = scenario_grid["top_provider"].value_counts(dropna=True)
        if not freq.empty:
            summary["scenario_top_provider_stability"] = {
                "provider_type": str(freq.index[0]),
                "scenario_share": float(freq.iloc[0] / len(scenario_grid)),
            }
    if not geo_dependency.empty and "provider_type" in geo_dependency.columns:
        summary["highest_geo_dependency_provider"] = str(geo_dependency.iloc[0]["provider_type"])
    if not trend_reliability.empty and "provider_type" in trend_reliability.columns:
        summary["top_reliability_provider"] = str(trend_reliability.iloc[0]["provider_type"])
    return summary


def build_advisory_memo(
    provider_scores: pd.DataFrame,
    volatility: pd.DataFrame,
    watchlist: pd.DataFrame,
    state_summary: pd.DataFrame,
    benchmark_flags: pd.DataFrame,
    concentration: pd.DataFrame,
    trend_shift: pd.DataFrame,
    state_volatility: pd.DataFrame,
    value_summary: pd.DataFrame,
    investability: pd.DataFrame,
    stress_test: pd.DataFrame,
    momentum: pd.DataFrame,
    anomalies: pd.DataFrame,
    provider_regimes: pd.DataFrame,
    state_fit: pd.DataFrame,
    consensus: pd.DataFrame,
    white_space: pd.DataFrame,
    scenario_grid: pd.DataFrame,
    geo_dependency: pd.DataFrame,
    trend_reliability: pd.DataFrame,
    operating_posture: pd.DataFrame,
    top_n: int,
) -> str:
    """Create a compact markdown memo from the generated analytics tables."""
    lines = ["# CMS Advisory Snapshot", ""]

    if not provider_scores.empty:
        lines.append("## Top Provider Opportunities")
        for provider, row in provider_scores.head(top_n).iterrows():
            lines.append(
                "- **%s**: score=%.3f, payment=$%.0f, median/service=$%.2f" % (
                    provider,
                    row.get("opportunity_score", float("nan")),
                    row.get("total_payment", 0.0),
                    row.get("median_payment_per_service", 0.0),
                )
            )
        lines.append("")

    if not volatility.empty:
        calm = volatility.sort_values("yoy_payment_volatility").head(5)
        fast = volatility.sort_values("last_payment_growth", ascending=False).head(5)
        lines.append("## Stability + Growth Signals")
        lines.append("- Lowest volatility: %s" % ", ".join(calm["provider_type"].tolist()))
        lines.append("- Fastest latest growth: %s" % ", ".join(fast["provider_type"].tolist()))
        lines.append("")

    if not watchlist.empty:
        priority = watchlist[watchlist["watchlist_bucket"] == "priority"].head(5)
        risky = watchlist[watchlist["watchlist_bucket"] == "high_risk"].head(5)
        lines.append("## Watchlist Buckets")
        lines.append("- Priority (growth with controlled volatility): %s" % ", ".join(priority["provider_type"].tolist()))
        lines.append("- High-risk watchlist: %s" % ", ".join(risky["provider_type"].tolist()))
        lines.append("")

    if not state_summary.empty:
        top_states = state_summary.head(5)["state"].tolist()
        lines.append("## Geographic Momentum")
        lines.append("- Top growth states: %s" % ", ".join(top_states))
        lines.append("")

    if not benchmark_flags.empty:
        high = benchmark_flags[benchmark_flags["benchmark_flag"] == "high_price"].head(5)
        low = benchmark_flags[benchmark_flags["benchmark_flag"] == "low_price"].head(5)
        lines.append("## Provider-State Benchmark Flags")
        lines.append("- High-price outliers: %s" % ", ".join((high["provider_type"] + "|" + high["state"]).tolist()))
        lines.append("- Low-price outliers: %s" % ", ".join((low["provider_type"] + "|" + low["state"]).tolist()))
        lines.append("")

    if not concentration.empty:
        top_conc = concentration.head(5)
        labels = [f"{r.state}|{r.year} (HHI={r.hhi:.3f})" for r in top_conc.itertuples()]
        lines.append("## Market Concentration Hotspots")
        lines.append("- Highest concentration state-years: %s" % ", ".join(labels))
        lines.append("")

    if not trend_shift.empty:
        movers = trend_shift.head(5)
        lines.append("## Largest Provider Trend Shifts")
        lines.append("- Positive movers: %s" % ", ".join(movers["provider_type"].tolist()))
        lines.append("")

    if not state_volatility.empty:
        volatile = state_volatility.head(5)
        lines.append("## Highest State Volatility")
        lines.append("- Most volatile states: %s" % ", ".join(volatile["state"].tolist()))
        lines.append("")

    if not value_summary.empty:
        top_value = value_summary.head(5)
        lines.append("## Best Value Provider Types")
        lines.append("- Top value leaders: %s" % ", ".join(top_value["provider_type"].tolist()))
        lines.append("")

    if not investability.empty:
        top_inv = investability.head(5)
        lines.append("## Top Investability Blend")
        lines.append("- Best blended opportunities: %s" % ", ".join(top_inv["provider_type"].tolist()))
        lines.append("")

    if not stress_test.empty:
        top_stress = stress_test.head(5)
        lines.append("## Stress-Test Resilient Providers")
        lines.append("- Top downside-resilient picks: %s" % ", ".join(top_stress["provider_type"].tolist()))
        lines.append("")

    if not momentum.empty:
        leaders = momentum.head(5)
        lines.append("## Durable Momentum Leaders")
        lines.append("- Most consistent growth patterns: %s" % ", ".join(leaders["provider_type"].tolist()))
        lines.append("")

    if not anomalies.empty:
        spikes = anomalies[anomalies["anomaly_flag"] == "cost_spike"].head(5)
        troughs = anomalies[anomalies["anomaly_flag"] == "cost_trough"].head(5)
        lines.append("## Provider-State-Year Anomalies")
        lines.append("- Cost spikes: %s" % ", ".join((spikes["provider_type"] + "|" + spikes["state"].astype(str) + "|" + spikes["year"].astype(str)).tolist()))
        lines.append("- Cost troughs: %s" % ", ".join((troughs["provider_type"] + "|" + troughs["state"].astype(str) + "|" + troughs["year"].astype(str)).tolist()))
        lines.append("")

    if not provider_regimes.empty:
        dur = provider_regimes[provider_regimes["regime"].astype(str) == "durable_growth"].head(5)
        risk = provider_regimes[provider_regimes["regime"].astype(str) == "declining_risk"].head(5)
        lines.append("## Provider Regime Classification")
        lines.append("- Durable growth regime: %s" % ", ".join(dur["provider_type"].tolist()))
        lines.append("- Declining-risk regime: %s" % ", ".join(risk["provider_type"].tolist()))
        lines.append("")

    if not state_fit.empty:
        top_states = state_fit.head(5)
        lines.append("## State Portfolio Fit")
        lines.append("- Best fit states for expansion: %s" % ", ".join(top_states["state"].astype(str).tolist()))
        lines.append("")

    if not consensus.empty:
        top_consensus = consensus.head(5)
        lines.append("## Consensus Provider Leaders")
        lines.append("- Most robust providers across scoring lenses: %s" % ", ".join(top_consensus["provider_type"].astype(str).tolist()))
        lines.append("")

    if not white_space.empty:
        top_ws = white_space.head(5)
        labels = (top_ws["provider_type"].astype(str) + "|" + top_ws["state"].astype(str)).tolist()
        lines.append("## White-Space Expansion Targets")
        lines.append("- Highest-confidence provider-state plays: %s" % ", ".join(labels))
        lines.append("")

    if not scenario_grid.empty:
        dominant = scenario_grid["top_provider"].value_counts(dropna=True).head(3)
        lines.append("## Scenario Robustness")
        lines.append("- Most frequent top providers across stress scenarios: %s" % ", ".join([f"{k} ({v})" for k, v in dominant.items()]))
        lines.append("")

    if not geo_dependency.empty:
        frag = geo_dependency.head(5)
        lines.append("## Geographic Dependency Risk")
        lines.append("- Most concentrated provider geographies: %s" % ", ".join((frag["provider_type"].astype(str) + "->" + frag["top_state"].astype(str)).tolist()))
        lines.append("")

    if not trend_reliability.empty:
        rel = trend_reliability.head(5)
        lines.append("## Most Reliable Growth Trends")
        lines.append("- Highest reliability providers: %s" % ", ".join(rel["provider_type"].astype(str).tolist()))
        lines.append("")

    if not operating_posture.empty:
        core = operating_posture[operating_posture["operating_posture"].astype(str) == "resilient_core"].head(5)
        risk = operating_posture[operating_posture["operating_posture"].astype(str) == "concentration_risk"].head(5)
        lines.append("## Operating Posture Map")
        lines.append("- Resilient-core providers: %s" % ", ".join(core["provider_type"].astype(str).tolist()))
        lines.append("- Concentration-risk providers: %s" % ", ".join(risk["provider_type"].astype(str).tolist()))
        lines.append("")

    return "\n".join(lines) + "\n"

def _plot_matrix(matrix: pd.DataFrame, title: str, out_path: Path, cmap: str = "coolwarm") -> None:
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(matrix.values, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def make_outputs(
    enriched: pd.DataFrame,
    provider_scores: pd.DataFrame,
    corr: pd.DataFrame,
    trends: pd.DataFrame,
    volatility: pd.DataFrame,
    watchlist: pd.DataFrame,
    state_summary: pd.DataFrame,
    regional_scores: pd.DataFrame,
    benchmark_flags: pd.DataFrame,
    concentration: pd.DataFrame,
    run_summary: Dict[str, object],
    quality_report: pd.DataFrame,
    trend_shift: pd.DataFrame,
    state_volatility: pd.DataFrame,
    value_summary: pd.DataFrame,
    investability: pd.DataFrame,
    stress_test: pd.DataFrame,
    momentum: pd.DataFrame,
    anomalies: pd.DataFrame,
    provider_regimes: pd.DataFrame,
    state_fit: pd.DataFrame,
    consensus: pd.DataFrame,
    white_space: pd.DataFrame,
    scenario_grid: pd.DataFrame,
    geo_dependency: pd.DataFrame,
    trend_reliability: pd.DataFrame,
    operating_posture: pd.DataFrame,
    geo_heatmap: pd.DataFrame,
    output_dir: Path,
    top_n: int,
    artifact_prefix: str = "",
    generate_plots: bool = True,
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: Dict[str, Path] = {}

    outputs = {
        "provider_scores": (provider_scores, "provider_opportunity_scores.csv"),
        "correlation": (corr, "correlation_matrix.csv"),
        "enriched_sample": (enriched.head(25000), "enriched_sample.csv"),
    }
    if not trends.empty:
        outputs["trends"] = (trends, "yearly_provider_trends.csv")
    if not volatility.empty:
        outputs["volatility"] = (volatility, "provider_volatility.csv")
    if not watchlist.empty:
        outputs["watchlist"] = (watchlist, "provider_watchlist.csv")
    if not state_summary.empty:
        outputs["state_summary"] = (state_summary, "state_growth_summary.csv")
    if not regional_scores.empty:
        outputs["regional_scores"] = (regional_scores, "provider_state_opportunities.csv")
    if not benchmark_flags.empty:
        outputs["benchmark_flags"] = (benchmark_flags, "provider_state_benchmark_flags.csv")
    if not concentration.empty:
        outputs["concentration"] = (concentration, "market_concentration_summary.csv")
    if not geo_heatmap.empty:
        outputs["state_provider_heatmap"] = (geo_heatmap, "state_provider_heatmap.csv")
    if not quality_report.empty:
        outputs["quality_report"] = (quality_report, "data_quality_report.csv")
    if not trend_shift.empty:
        outputs["trend_shift"] = (trend_shift, "provider_trend_shift.csv")
    if not state_volatility.empty:
        outputs["state_volatility"] = (state_volatility, "state_volatility_summary.csv")
    if not value_summary.empty:
        outputs["value_summary"] = (value_summary, "provider_value_summary.csv")
    if not investability.empty:
        outputs["investability"] = (investability, "provider_investability_summary.csv")
    if not stress_test.empty:
        outputs["stress_test"] = (stress_test, "provider_stress_test.csv")
    if not momentum.empty:
        outputs["momentum"] = (momentum, "provider_momentum_profile.csv")
    if not anomalies.empty:
        outputs["anomalies"] = (anomalies, "provider_state_year_anomalies.csv")
    if not provider_regimes.empty:
        outputs["provider_regimes"] = (provider_regimes, "provider_regime_classification.csv")
    if not state_fit.empty:
        outputs["state_fit"] = (state_fit, "state_portfolio_fit.csv")
    if not consensus.empty:
        outputs["consensus"] = (consensus, "provider_consensus_rank.csv")
    if not white_space.empty:
        outputs["white_space"] = (white_space, "state_provider_white_space.csv")
    if not scenario_grid.empty:
        outputs["scenario_grid"] = (scenario_grid, "stress_scenario_grid.csv")
    if not geo_dependency.empty:
        outputs["geo_dependency"] = (geo_dependency, "provider_geo_dependency.csv")
    if not trend_reliability.empty:
        outputs["trend_reliability"] = (trend_reliability, "provider_trend_reliability.csv")
    if not operating_posture.empty:
        outputs["operating_posture"] = (operating_posture, "provider_operating_posture.csv")

    for name, (frame, fname) in outputs.items():
        path = output_dir / (f"{artifact_prefix}{fname}" if artifact_prefix else fname)
        frame.to_csv(path, index=(name != "enriched_sample"))
        artifacts[name] = path

    run_summary_path = output_dir / (f"{artifact_prefix}run_summary.json" if artifact_prefix else "run_summary.json")
    run_summary_path.write_text(json.dumps(run_summary, indent=2, sort_keys=True))
    artifacts["run_summary"] = run_summary_path

    if generate_plots and not corr.empty:
        heatmap_path = output_dir / (f"{artifact_prefix}correlation_heatmap.png" if artifact_prefix else "correlation_heatmap.png")
        _plot_matrix(corr, "CMS Metric Correlation Heatmap", heatmap_path)
        artifacts["correlation_heatmap"] = heatmap_path

    if generate_plots and not geo_heatmap.empty:
        geo_path = output_dir / (f"{artifact_prefix}state_provider_heatmap.png" if artifact_prefix else "state_provider_heatmap.png")
        _plot_matrix(geo_heatmap.fillna(0), "Median Payment per Beneficiary by State/Provider", geo_path, cmap="viridis")
        artifacts["state_provider_heatmap_plot"] = geo_path

    if generate_plots and not provider_scores.empty:
        top = provider_scores.head(top_n).copy()
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.scatter(top["median_payment_per_service"], top["total_payment"], s=100 + 500 * top["opportunity_score"], alpha=0.72)
        for idx, row in top.iterrows():
            ax.annotate(str(idx), (row["median_payment_per_service"], row["total_payment"]))
        ax.set_xlabel("Median Payment per Service")
        ax.set_ylabel("Total Medicare Payment")
        ax.set_title("Top Provider Types: Scale vs Margin Proxy")
        scatter_path = output_dir / (f"{artifact_prefix}provider_opportunity_scatter.png" if artifact_prefix else "provider_opportunity_scatter.png")
        fig.tight_layout()
        fig.savefig(scatter_path, dpi=180)
        plt.close(fig)
        artifacts["provider_scatter"] = scatter_path

    if generate_plots and not trends.empty:
        latest = trends.dropna(subset=["payment_yoy_pct"]).sort_values("payment_yoy_pct", ascending=False).head(top_n)
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(latest["provider_type"], latest["payment_yoy_pct"])
        ax.invert_yaxis()
        ax.set_xlabel("Year-over-Year Payment Change")
        ax.set_title("Fastest Growing Provider Types (YoY)")
        trend_path = output_dir / (f"{artifact_prefix}provider_yoy_growth.png" if artifact_prefix else "provider_yoy_growth.png")
        fig.tight_layout()
        fig.savefig(trend_path, dpi=180)
        plt.close(fig)
        artifacts["provider_yoy_growth"] = trend_path

    if generate_plots and not watchlist.empty:
        plot_df = watchlist.dropna(subset=["last_payment_growth", "yoy_payment_volatility"]).head(top_n)
        fig, ax = plt.subplots(figsize=(10, 7))
        colors = plot_df["watchlist_bucket"].map({"priority": "green", "monitor": "orange", "high_risk": "red"}).fillna("gray")
        ax.scatter(plot_df["yoy_payment_volatility"], plot_df["last_payment_growth"], c=colors, alpha=0.75)
        for _, row in plot_df.iterrows():
            ax.annotate(str(row["provider_type"]), (row["yoy_payment_volatility"], row["last_payment_growth"]))
        ax.set_xlabel("YoY Payment Volatility")
        ax.set_ylabel("Latest Payment Growth")
        ax.set_title("Provider Risk-Return Watchlist")
        watch_path = output_dir / (f"{artifact_prefix}provider_watchlist_quadrant.png" if artifact_prefix else "provider_watchlist_quadrant.png")
        fig.tight_layout()
        fig.savefig(watch_path, dpi=180)
        plt.close(fig)
        artifacts["watchlist_quadrant"] = watch_path

    if generate_plots and not regional_scores.empty:
        regional_top = regional_scores.head(top_n).copy()
        labels = regional_top["provider_type"] + " | " + regional_top["state"]
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(labels, regional_top["regional_opportunity_score"])
        ax.invert_yaxis()
        ax.set_xlabel("Regional Opportunity Score")
        ax.set_title("Top Provider-State Opportunities")
        reg_path = output_dir / (f"{artifact_prefix}provider_state_opportunity_top.png" if artifact_prefix else "provider_state_opportunity_top.png")
        fig.tight_layout()
        fig.savefig(reg_path, dpi=180)
        plt.close(fig)
        artifacts["regional_opportunity_plot"] = reg_path

    if generate_plots and not benchmark_flags.empty:
        flagged = benchmark_flags[benchmark_flags["benchmark_flag"] != "normal"].head(top_n)
        if not flagged.empty:
            labels = flagged["provider_type"] + " | " + flagged["state"]
            fig, ax = plt.subplots(figsize=(12, 8))
            colors = flagged["benchmark_flag"].map({"high_price": "crimson", "low_price": "royalblue"}).fillna("gray")
            ax.barh(labels, flagged["service_price_z"], color=colors)
            ax.invert_yaxis()
            ax.set_xlabel("Service Price Z-Score vs Provider Peer")
            ax.set_title("Provider-State Benchmark Flags")
            bench_path = output_dir / (f"{artifact_prefix}provider_state_benchmark_flags.png" if artifact_prefix else "provider_state_benchmark_flags.png")
            fig.tight_layout()
            fig.savefig(bench_path, dpi=180)
            plt.close(fig)
            artifacts["benchmark_flag_plot"] = bench_path

    if generate_plots and not concentration.empty:
        ctop = concentration.head(top_n).copy()
        labels = ctop["state"].astype(str) + " | " + ctop["year"].astype(str)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(labels, ctop["hhi"])
        ax.invert_yaxis()
        ax.set_xlabel("HHI")
        ax.set_title("Most Concentrated State-Year Markets")
        cpath = output_dir / (f"{artifact_prefix}market_concentration_hhi_top.png" if artifact_prefix else "market_concentration_hhi_top.png")
        fig.tight_layout()
        fig.savefig(cpath, dpi=180)
        plt.close(fig)
        artifacts["concentration_plot"] = cpath

    if generate_plots and not trend_shift.empty:
        top_shift = trend_shift.head(top_n)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(top_shift["provider_type"], top_shift["payment_delta"])
        ax.invert_yaxis()
        ax.set_xlabel("Payment Delta")
        ax.set_title("Top Provider Payment Shifts")
        shift_path = output_dir / (f"{artifact_prefix}provider_trend_shift_top.png" if artifact_prefix else "provider_trend_shift_top.png")
        fig.tight_layout()
        fig.savefig(shift_path, dpi=180)
        plt.close(fig)
        artifacts["trend_shift_plot"] = shift_path

    if generate_plots and not state_volatility.empty:
        top_vol = state_volatility.head(top_n)
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(top_vol["state"], top_vol["yoy_volatility"])
        ax.invert_yaxis()
        ax.set_xlabel("YoY Volatility")
        ax.set_title("Highest State Payment Volatility")
        svol_path = output_dir / (f"{artifact_prefix}state_volatility_top.png" if artifact_prefix else "state_volatility_top.png")
        fig.tight_layout()
        fig.savefig(svol_path, dpi=180)
        plt.close(fig)
        artifacts["state_volatility_plot"] = svol_path

    if generate_plots and not value_summary.empty:
        top_value = value_summary.head(top_n)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(top_value["provider_type"], top_value["value_score"])
        ax.invert_yaxis()
        ax.set_xlabel("Value Score")
        ax.set_title("Top Value Provider Types")
        vpath = output_dir / (f"{artifact_prefix}provider_value_top.png" if artifact_prefix else "provider_value_top.png")
        fig.tight_layout()
        fig.savefig(vpath, dpi=180)
        plt.close(fig)
        artifacts["value_plot"] = vpath

    if generate_plots and not investability.empty:
        top_inv = investability.head(top_n)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(top_inv["provider_type"], top_inv["investability_score"])
        ax.invert_yaxis()
        ax.set_xlabel("Investability Score")
        ax.set_title("Top Investability Provider Types")
        ipath = output_dir / (f"{artifact_prefix}provider_investability_top.png" if artifact_prefix else "provider_investability_top.png")
        fig.tight_layout()
        fig.savefig(ipath, dpi=180)
        plt.close(fig)
        artifacts["investability_plot"] = ipath

    if generate_plots and not stress_test.empty:
        top_stress = stress_test.head(top_n)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(top_stress["provider_type"], top_stress["stress_adjusted_score"])
        ax.invert_yaxis()
        ax.set_xlabel("Stress Adjusted Score")
        ax.set_title("Top Stress-Test Resilient Providers")
        spath = output_dir / (f"{artifact_prefix}provider_stress_test_top.png" if artifact_prefix else "provider_stress_test_top.png")
        fig.tight_layout()
        fig.savefig(spath, dpi=180)
        plt.close(fig)
        artifacts["stress_test_plot"] = spath

    if generate_plots and not white_space.empty:
        ws_top = white_space.head(top_n).copy()
        labels = ws_top["provider_type"].astype(str) + " | " + ws_top["state"].astype(str)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(labels, ws_top["white_space_score"])
        ax.invert_yaxis()
        ax.set_xlabel("White-Space Score")
        ax.set_title("Top Provider-State White-Space Expansion Targets")
        wpath = output_dir / (f"{artifact_prefix}state_provider_white_space_top.png" if artifact_prefix else "state_provider_white_space_top.png")
        fig.tight_layout()
        fig.savefig(wpath, dpi=180)
        plt.close(fig)
        artifacts["white_space_plot"] = wpath

    if generate_plots and not geo_dependency.empty:
        dep_top = geo_dependency.head(top_n)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(dep_top["provider_type"], dep_top["top_state_share"])
        ax.invert_yaxis()
        ax.set_xlabel("Top-State Share")
        ax.set_title("Highest Geographic Dependency by Provider")
        gpath = output_dir / (f"{artifact_prefix}provider_geo_dependency_top.png" if artifact_prefix else "provider_geo_dependency_top.png")
        fig.tight_layout()
        fig.savefig(gpath, dpi=180)
        plt.close(fig)
        artifacts["geo_dependency_plot"] = gpath

    if generate_plots and not trend_reliability.empty:
        rel_top = trend_reliability.head(top_n)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(rel_top["provider_type"], rel_top["reliability_score"])
        ax.invert_yaxis()
        ax.set_xlabel("Reliability Score")
        ax.set_title("Most Reliable Provider Growth Trends")
        rpath = output_dir / (f"{artifact_prefix}provider_trend_reliability_top.png" if artifact_prefix else "provider_trend_reliability_top.png")
        fig.tight_layout()
        fig.savefig(rpath, dpi=180)
        plt.close(fig)
        artifacts["trend_reliability_plot"] = rpath

    if generate_plots and not operating_posture.empty:
        pos = operating_posture.head(top_n)
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.barh(pos["provider_type"], pos["posture_score"])
        ax.invert_yaxis()
        ax.set_xlabel("Posture Score")
        ax.set_title("Provider Operating Posture Leaders")
        ppath = output_dir / (f"{artifact_prefix}provider_operating_posture_top.png" if artifact_prefix else "provider_operating_posture_top.png")
        fig.tight_layout()
        fig.savefig(ppath, dpi=180)
        plt.close(fig)
        artifacts["operating_posture_plot"] = ppath

    memo_path = output_dir / (f"{artifact_prefix}advisory_snapshot.md" if artifact_prefix else "advisory_snapshot.md")
    memo_path.write_text(build_advisory_memo(provider_scores, volatility, watchlist, state_summary, benchmark_flags, concentration, trend_shift, state_volatility, value_summary, investability, stress_test, momentum, anomalies, provider_regimes, state_fit, consensus, white_space, scenario_grid, geo_dependency, trend_reliability, operating_posture, top_n))
    artifacts["advisory_snapshot"] = memo_path

    return artifacts


def parse_extra_params(params: List[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for p in params:
        if "=" not in p:
            raise ValueError("extra-param must be key=value")
        k, v = p.split("=", 1)
        if not k.strip():
            raise ValueError("extra-param key cannot be empty")
        parsed[k] = v
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CMS API analytics for PE advisory")
    parser.add_argument("--endpoint", required=True, help="CMS Data API endpoint URL")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--max-pages", type=int, default=8)
    parser.add_argument("--output-dir", default="cms_advisory_outputs")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--min-services", type=int, default=11, help="Minimum services per row for quality filtering")
    parser.add_argument("--min-benes", type=int, default=11, help="Minimum beneficiaries per row for quality filtering")
    parser.add_argument("--winsor-upper-quantile", type=float, default=0.99, help="Upper quantile cap for heavy-tailed payment metrics")
    parser.add_argument("--watch-min-growth", type=float, default=0.05, help="Watchlist minimum latest growth for priority bucket")
    parser.add_argument("--watch-max-volatility", type=float, default=0.35, help="Watchlist max volatility for priority bucket")
    parser.add_argument("--min-state-provider-rows", type=int, default=20, help="Minimum rows for provider-state opportunity scoring")
    parser.add_argument("--benchmark-z-threshold", type=float, default=1.5, help="Absolute z-score threshold for provider-state benchmark flags")
    parser.add_argument("--retry-count", type=int, default=2, help="Retries per API page fetch on transient errors")
    parser.add_argument("--retry-backoff-s", type=float, default=1.0, help="Base seconds for linear backoff between fetch retries")
    parser.add_argument("--min-year", type=int, default=None, help="Optional inclusive minimum year filter")
    parser.add_argument("--max-year", type=int, default=None, help="Optional inclusive maximum year filter")
    parser.add_argument("--baseline-year", type=int, default=None, help="Baseline year for provider trend shift comparison")
    parser.add_argument("--compare-year", type=int, default=None, help="Comparison year for provider trend shift comparison")
    parser.add_argument("--downside-shock", type=float, default=0.15, help="Downside payment shock for stress testing investability")
    parser.add_argument("--upside-shock", type=float, default=0.10, help="Upside payment shock for stress testing investability")
    parser.add_argument("--momentum-min-years", type=int, default=3, help="Minimum observed years required for momentum consistency scoring")
    parser.add_argument("--anomaly-z-threshold", type=float, default=2.5, help="Absolute z-score threshold for anomaly detection")
    parser.add_argument("--anomaly-min-rows", type=int, default=15, help="Minimum rows for provider-state-year anomaly detection")
    parser.add_argument("--regime-strong-growth", type=float, default=0.12, help="Growth threshold for durable/emerging provider regime classification")
    parser.add_argument("--regime-high-volatility", type=float, default=0.35, help="Volatility threshold for provider regime classification")
    parser.add_argument("--white-space-min-percentile", type=float, default=0.70, help="Minimum white-space percentile threshold to retain provider-state targets")
    parser.add_argument("--scenario-downside-step", type=float, default=0.10, help="Step size for downside shock grid generation")
    parser.add_argument("--scenario-upside-step", type=float, default=0.10, help="Step size for upside shock grid generation")
    parser.add_argument("--geo-dependency-threshold", type=float, default=0.50, help="Top-state share threshold for provider geographic dependency flagging")
    parser.add_argument("--reliability-min-observations", type=int, default=3, help="Minimum YoY observations required for provider trend reliability scoring")
    parser.add_argument("--scenario-min-win-share", type=float, default=0.30, help="Minimum scenario win-share threshold for operating posture scenario leaders")
    parser.add_argument("--artifact-prefix", default="", help="Optional filename prefix for generated artifacts")
    parser.add_argument("--no-plots", action="store_true", help="Skip PNG chart generation for faster/headless runs")
    parser.add_argument("--provider-col", default=None, help="Override provider-type column name")
    parser.add_argument("--state-col", default=None, help="Override state column name")
    parser.add_argument("--year-col", default=None, help="Override year column name")
    parser.add_argument(
        "--extra-param",
        action="append",
        default=[],
        help="Additional query params as key=value (repeatable)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_runtime_inputs(args)
    raw = fetch_cms_api_pages(
        args.endpoint,
        limit=args.limit,
        max_pages=args.max_pages,
        extra_params=parse_extra_params(args.extra_param),
        retry_count=args.retry_count,
        retry_backoff_s=args.retry_backoff_s,
    )
    standardized = standardize_columns(raw, args)
    standardized = filter_year_range(standardized, args.min_year, args.max_year)
    enriched = enrich_features(standardized)
    enriched = apply_quality_filters(enriched, args.min_services, args.min_benes)
    enriched = winsorize_metrics(enriched, args.winsor_upper_quantile)

    scores = provider_screen(enriched)
    corr = correlation_table(enriched)
    trends = yearly_trends(enriched)
    volatility = provider_volatility(trends)
    watchlist = growth_volatility_watchlist(volatility, min_growth=args.watch_min_growth, max_volatility=args.watch_max_volatility)
    state_summary = state_growth_summary(enriched)
    state_volatility = state_volatility_summary(enriched)
    value_summary = provider_value_summary(enriched)
    investability = provider_investability_summary(scores, value_summary, volatility)
    stress_test = provider_stress_test(investability, downside_shock=args.downside_shock, upside_shock=args.upside_shock)
    momentum = provider_momentum_profile(trends, min_years=args.momentum_min_years)
    anomalies = detect_state_provider_anomalies(enriched, z_threshold=args.anomaly_z_threshold, min_rows=args.anomaly_min_rows)
    provider_regimes = provider_regime_classification(
        momentum,
        volatility,
        strong_growth_threshold=args.regime_strong_growth,
        high_vol_threshold=args.regime_high_volatility,
    )
    regional_scores = state_provider_opportunities(enriched, min_rows=args.min_state_provider_rows)
    benchmark_flags = provider_state_benchmark_flags(
        enriched,
        z_threshold=args.benchmark_z_threshold,
        min_rows=args.min_state_provider_rows,
    )
    concentration = market_concentration_summary(enriched)
    trend_shift = provider_trend_shift(trends, args.baseline_year, args.compare_year)
    geo_heatmap = state_provider_heatmap(enriched)
    state_fit = state_portfolio_fit(state_summary, state_volatility, concentration)
    consensus = provider_consensus_rank(scores, value_summary, investability, stress_test, momentum, provider_regimes)
    white_space = state_provider_white_space(regional_scores, state_fit, benchmark_flags, min_percentile=args.white_space_min_percentile)
    downsides = [round(x, 6) for x in np.arange(args.scenario_downside_step, 0.31, args.scenario_downside_step)]
    upsides = [round(x, 6) for x in np.arange(0.0, 0.21, args.scenario_upside_step)]
    scenario_grid = stress_scenario_grid(investability, downsides=downsides, upsides=upsides)
    geo_dependency = provider_geo_dependency(enriched, dependency_threshold=args.geo_dependency_threshold)
    trend_reliability = provider_trend_reliability(trends, min_observations=args.reliability_min_observations)
    operating_posture = provider_operating_posture(
        consensus,
        trend_reliability,
        geo_dependency,
        scenario_grid,
        scenario_min_win_share=args.scenario_min_win_share,
    )
    run_summary = build_run_summary(
        enriched,
        scores,
        watchlist,
        regional_scores,
        benchmark_flags,
        value_summary,
        investability,
        stress_test,
        momentum,
        anomalies,
        provider_regimes,
        state_fit,
        consensus,
        white_space,
        scenario_grid,
        geo_dependency,
        trend_reliability,
        operating_posture,
    )
    quality_report = data_quality_report(enriched)

    artifacts = make_outputs(
        enriched,
        scores,
        corr,
        trends,
        volatility,
        watchlist,
        state_summary,
        regional_scores,
        benchmark_flags,
        concentration,
        run_summary,
        quality_report,
        trend_shift,
        state_volatility,
        value_summary,
        investability,
        stress_test,
        momentum,
        anomalies,
        provider_regimes,
        state_fit,
        consensus,
        white_space,
        scenario_grid,
        geo_dependency,
        trend_reliability,
        operating_posture,
        geo_heatmap,
        Path(args.output_dir),
        args.top_n,
        artifact_prefix=args.artifact_prefix,
        generate_plots=not args.no_plots,
    )

    print("Generated artifacts:")
    for name, path in sorted(artifacts.items()):
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
