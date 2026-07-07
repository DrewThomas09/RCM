"""Medicare market concentration analytics for PE-style rollup screening.

Ported and cleaned from cms_api_advisory_analytics.py (DrewThomas09/cms_medicare).
Requires pandas; all functions accept a DataFrame produced by cms_api_client and
return DataFrames so callers can chain or export freely.

Public API:
    market_concentration_summary(df)      -> DataFrame  (provider-type MIX HHI, CR3, CR5 per state/year)
    competitor_concentration_summary(df)  -> DataFrame  (true competitor HHI when provider ids exist)
    provider_geo_dependency(df)           -> DataFrame  (single-state concentration risk)
    state_volatility_summary(df)          -> DataFrame  (YoY payment volatility by state)
    state_growth_summary(df)              -> DataFrame  (state-level trend targets)
    state_portfolio_fit(...)              -> DataFrame  (blended fit score, rank-normalized)
    concentration_table(df)               -> str        (formatted text table)

Scale convention: ``hhi`` columns here are Σ(share²) on the 0-1
fractional scale; every frame also carries ``hhi_10k`` (× 10,000) for
comparison against the merger-guideline cutoffs used by the MSA-level
modules.
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
    """Compute provider-type MIX concentration by state/year.

    WARNING — this is NOT a competitor HHI. Shares are computed across
    *provider-type categories* (Cardiology vs Orthopedics vs ...), so the
    number measures how concentrated a state's Medicare spend is in a few
    service lines, not how concentrated any provider market is among
    competing organizations. It cannot be read against the FTC/DOJ merger
    thresholds and must not be used to screen rollup antitrust headroom —
    use :func:`competitor_concentration_summary` (provider-level shares)
    for that question when the input carries a provider identifier.

    Returns HHI (0-1 fractional scale), the same value on the familiar
    0-10,000 convention (``hhi_10k``), CR3, CR5, and total Medicare
    payment per state-year market. The dual scale exists because the
    sibling MSA module and the merger-guideline cutoffs (1,500/2,500)
    use the 10,000-point convention — a consumer joining the two tables
    misread 0.18 vs 1,800 by four orders of magnitude before ``hhi_10k``
    was added.

    Missing-mass disclosure: rows whose payment is known but whose
    ``provider_type`` is missing are EXCLUDED from the share
    denominator, so the shares (and therefore HHI/CR3/CR5) describe
    only the categorised dollars. Each market row carries
    ``excluded_payment`` (those known-but-uncategorised dollars) and
    ``excluded_payment_share`` (excluded ÷ (observed + excluded)) so a
    pull where 30% of the money has no category cannot masquerade as a
    full-coverage concentration read. Rows CMS suppressed at source
    never reach the frame at all — observed shares are upper bounds on
    true shares, which the caller must remember when reading HHI as
    precise.
    """
    required = {"state", "provider_type", "total_medicare_payment_amt"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    if "year" not in work.columns:
        work["year"] = "all"
    _to_numeric_cols(work, ["total_medicare_payment_amt"])
    # Ledger of known-but-uncategorised mass, per market (see
    # docstring) — computed before the dropna that discards it.
    payment_known = work.dropna(subset=["state", "total_medicare_payment_amt"])
    dropped = payment_known[payment_known["provider_type"].isna()]
    excluded_by_market = (
        dropped.groupby(["state", "year"])["total_medicare_payment_amt"].sum()
        if not dropped.empty else {}
    )
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
        hhi = float((shares ** 2).sum())
        excluded = (
            float(excluded_by_market.get((state, year), 0.0))
            if len(excluded_by_market) else 0.0
        )
        rows.append(
            {
                "state": state,
                "year": year,
                "provider_type_count": int(len(g)),
                "hhi": hhi,
                "hhi_10k": round(hhi * 10_000),
                "cr3": float(shares.head(3).sum()),
                "cr5": float(shares.head(5).sum()),
                "total_payment": float(total),
                "excluded_payment": excluded,
                "excluded_payment_share": float(
                    excluded / (total + excluded)
                ),
            }
        )

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    return out.sort_values(["hhi", "cr3"], ascending=False).reset_index(drop=True)


def competitor_concentration_summary(
    df: pd.DataFrame,
    provider_col: str = "npi",
) -> pd.DataFrame:
    """True competitor concentration by state/year — shares per provider.

    This is the concentration read that CAN be compared against the
    merger-guideline bands: shares are computed across individual
    providers (``provider_col``, default ``npi``) rather than across
    provider-type categories, so HHI measures how the market splits
    among competing organizations. Opt-in because most CMS aggregate
    pulls arrive without a provider identifier — when the column is
    absent an empty frame is returned rather than a category-level
    number masquerading as a competitor screen.

    Output columns mirror :func:`market_concentration_summary`
    (``hhi`` 0-1, ``hhi_10k``, ``cr3``, ``cr5``, ``total_payment``,
    ``excluded_payment``, ``excluded_payment_share``) with
    ``provider_count`` in place of ``provider_type_count``.

    Missing-mass disclosure matters MORE here than in the mix summary:
    CMS suppresses low-volume providers at source and rows with a
    payment but no provider id are excluded from the share
    denominator, both of which overstate the observed players' shares
    — so this HHI is an upper bound. ``excluded_payment_share``
    quantifies the second effect per market; the first is invisible in
    the input and stays a documented caveat.
    """
    required = {"state", provider_col, "total_medicare_payment_amt"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    if "year" not in work.columns:
        work["year"] = "all"
    _to_numeric_cols(work, ["total_medicare_payment_amt"])
    payment_known = work.dropna(subset=["state", "total_medicare_payment_amt"])
    dropped = payment_known[payment_known[provider_col].isna()]
    excluded_by_market = (
        dropped.groupby(["state", "year"])["total_medicare_payment_amt"].sum()
        if not dropped.empty else {}
    )
    work = work.dropna(subset=["state", provider_col, "total_medicare_payment_amt"])
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby(["state", "year", provider_col], as_index=False)["total_medicare_payment_amt"]
        .sum()
    )

    rows = []
    for (state, year), g in grouped.groupby(["state", "year"]):
        total = g["total_medicare_payment_amt"].sum()
        if total <= 0:
            continue
        shares = (g["total_medicare_payment_amt"] / total).sort_values(ascending=False)
        hhi = float((shares ** 2).sum())
        excluded = (
            float(excluded_by_market.get((state, year), 0.0))
            if len(excluded_by_market) else 0.0
        )
        rows.append(
            {
                "state": state,
                "year": year,
                "provider_count": int(len(g)),
                "hhi": hhi,
                "hhi_10k": round(hhi * 10_000),
                "cr3": float(shares.head(3).sum()),
                "cr5": float(shares.head(5).sum()),
                "total_payment": float(total),
                "excluded_payment": excluded,
                "excluded_payment_share": float(
                    excluded / (total + excluded)
                ),
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

    Score components (weights sum to 1.00), each converted to a
    percentile rank WITHIN the state panel before weighting:
        0.35 — latest YoY growth
        0.20 — avg growth
        0.20 — latest payment volume
        0.15 — stability (inverse volatility)
        0.10 — fragmentation bonus (1 - provider-type-mix HHI)

    Why percentile ranks: the original implementation blended raw
    units — growth fractions (~0.05), 0-1 stability scores, and
    ``log1p`` of a dollar payment base (~20 for a $1B state) — so the
    nominally-20% payment term contributed ~200x the growth terms and
    the delivered score was effectively a payment-volume ranking that
    contradicted the documented weights. Ranking each component onto a
    common 0-1 scale first makes the weights mean what they say: a
    small, fast-growing state can now outrank a large, flat one.
    Missing component values rank neutral (0.5) rather than dragging a
    state to the floor. ``state_fit_score`` is therefore bounded 0-1;
    ``state_fit_percentile`` remains the stable cross-version output.
    ``fit_panel_n`` discloses how many states were ranked — a "90th
    percentile" over a three-state pull is a rank among three, and the
    memo consumer can only weigh the percentile correctly with the n
    beside it.

    Note the fragmentation input is the provider-type MIX HHI from
    :func:`market_concentration_summary` — a service-line-diversity
    bonus, not a competitor-fragmentation read (see that function's
    warning).
    """
    if state_growth.empty:
        return pd.DataFrame()

    def _rank_component(series: pd.Series) -> pd.Series:
        # Percentile rank with NaNs held out then filled neutral, so a
        # state missing (say) volatility data isn't scored as worst-in-
        # panel on a component we simply don't have.
        s = pd.to_numeric(series, errors="coerce")
        return s.rank(pct=True).fillna(0.5)

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

    # Per-component percentile ranks (0-1, NaN → neutral 0.5). Kept as
    # output columns so the memo can show WHY a state ranks where it
    # does, not just the blended number.
    fit["latest_growth_rank"] = _rank_component(fit["latest_state_growth"])
    fit["avg_growth_rank"] = _rank_component(fit["avg_state_growth"])
    fit["payment_rank"] = _rank_component(fit["latest_payment"])
    fit["stability_rank"] = _rank_component(fit["stability_score"])
    fit["fragmentation_rank"] = _rank_component(fit["fragmentation_bonus"])

    fit["state_fit_score"] = (
        0.35 * fit["latest_growth_rank"]
        + 0.20 * fit["avg_growth_rank"]
        + 0.20 * fit["payment_rank"]
        + 0.15 * fit["stability_rank"]
        + 0.10 * fit["fragmentation_rank"]
    )
    fit["state_fit_percentile"] = _percentile_rank(fit["state_fit_score"])
    # n= disclosure for the percentile columns (see docstring).
    fit["fit_panel_n"] = len(fit)
    return fit.sort_values("state_fit_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Formatted output
# ---------------------------------------------------------------------------

def concentration_table(df: pd.DataFrame, top_n: int = 20) -> str:
    """Return a formatted text table of concentration metrics.

    The scale/meaning note is printed with the table because this string
    reaches the corpus CLI and advisory memo verbatim — the one place a
    reader would otherwise assume a competitor HHI on the 10,000 scale.
    """
    if df.empty:
        return "No concentration data available.\n"

    lines = [
        "Market Concentration Summary",
        "(provider-type mix shares, HHI on 0-1 scale — not a competitor HHI)",
        "=" * 64,
    ]
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
