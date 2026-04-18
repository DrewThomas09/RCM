"""Provider consensus ranking and anomaly detection for CMS Medicare data.

Ported and cleaned from cms_medicare/cms_api_advisory_analytics.py
(DrewThomas09/cms_medicare).  Original logic extracted; rewritten for
stdlib compatibility and integrated with the corpus pipeline.

Two key capabilities:

1. Consensus Rank — blends 5 analytical lenses into a single ranked list:
   opportunity score, value summary, investability, stress-adjusted score,
   momentum consistency, and regime classification.  Each lens is
   percentile-ranked; the consensus score is the row mean across lens
   percentiles.  Regime boost: durable_growth=1.0, declining_risk=0.1.

2. State-Provider Anomaly Detection — Z-score–based detection of
   provider-state-year cohorts that are unusually high/low in payment
   per service versus national peers of the same provider type.

Both functions accept pandas DataFrames when pandas is available and fall
back gracefully to plain-dict operation otherwise.

Public API:
    provider_consensus_rank(scores, value_summary, investability,
                            stress_test, momentum, regimes) -> DataFrame
    detect_state_provider_anomalies(df, z_threshold, min_rows) -> DataFrame
    consensus_rank_table(rank_df, top_n)  -> str
    anomaly_table(anomalies_df, top_n)    -> str
    consensus_rank_from_dicts(lens_dicts) -> List[Dict]  (no-pandas path)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Pandas-free consensus rank (for environments without pandas)
# ---------------------------------------------------------------------------

_REGIME_BOOST: Dict[str, float] = {
    "durable_growth": 1.00,
    "steady_compounders": 0.75,
    "emerging_volatile": 0.55,
    "stagnant": 0.30,
    "declining_risk": 0.10,
}


def _percentile_rank_list(values: List[float]) -> List[float]:
    """Percentile rank for a list of floats (0-1)."""
    if not values:
        return []
    n = len(values)
    sorted_vals = sorted(enumerate(values), key=lambda x: (x[1] is None, x[1]))
    ranks = [0.0] * n
    for rank, (orig_idx, val) in enumerate(sorted_vals):
        ranks[orig_idx] = rank / max(n - 1, 1)
    return ranks


def consensus_rank_from_dicts(
    lens_dicts: List[Dict[str, Any]],
    provider_key: str = "provider_type",
) -> List[Dict[str, Any]]:
    """Blend score lenses into a consensus rank without pandas.

    Args:
        lens_dicts:    List of per-lens score dicts. Each dict must have
                       a `provider_type` key and one or more score fields.
        provider_key:  Key used to join across lenses.

    Returns:
        List of dicts sorted by `consensus_score` descending, each with
        all lens scores, their percentile ranks, and a final consensus_score.
    """
    if not lens_dicts:
        return []

    # Merge all lens dicts by provider_type
    merged: Dict[str, Dict[str, Any]] = {}
    for lens in lens_dicts:
        pt = lens.get(provider_key)
        if not pt:
            continue
        if pt not in merged:
            merged[pt] = {provider_key: pt}
        for k, v in lens.items():
            if k != provider_key:
                merged[pt][k] = v

    rows = list(merged.values())
    if not rows:
        return []

    # Collect all numeric score columns
    score_cols = set()
    for row in rows:
        for k, v in row.items():
            if k != provider_key and isinstance(v, (int, float)):
                score_cols.add(k)

    # Percentile rank each score column
    for col in score_cols:
        vals = [row.get(col) for row in rows]
        # Replace None with 0
        nums = [v if v is not None else 0.0 for v in vals]
        ranks = _percentile_rank_list(nums)
        for row, r in zip(rows, ranks):
            row[f"{col}_pct"] = round(r, 4)

    # Compute consensus score as mean of available percentile ranks
    for row in rows:
        pct_vals = [v for k, v in row.items() if k.endswith("_pct")]
        row["consensus_score"] = round(sum(pct_vals) / len(pct_vals), 4) if pct_vals else 0.0

    rows.sort(key=lambda r: r["consensus_score"], reverse=True)

    # Add consensus_percentile
    scores = [r["consensus_score"] for r in rows]
    ranks = _percentile_rank_list(scores)
    for row, r in zip(rows, ranks):
        row["consensus_percentile"] = round(r, 4)

    return rows


# ---------------------------------------------------------------------------
# Pandas-aware functions (used when pandas is available)
# ---------------------------------------------------------------------------

def provider_consensus_rank(
    scores=None,
    value_summary=None,
    investability=None,
    stress_test=None,
    momentum=None,
    provider_regimes=None,
):
    """Blend multiple ranking lenses into a consensus leader table.

    All arguments are optional pandas DataFrames; pass None to skip a lens.
    Returns a DataFrame sorted by consensus_score descending, or an empty
    list of dicts when pandas is not available.

    Ported from cms_medicare/cms_api_advisory_analytics.py::provider_consensus_rank.
    """
    try:
        import pandas as pd
    except ImportError:
        return []

    def _safe(df):
        return df if df is not None and not df.empty else pd.DataFrame()

    def _pct_rank(series: "pd.Series") -> "pd.Series":
        n = len(series)
        if n == 0:
            return series
        return series.rank(method="average", na_option="keep") / n

    tables = []

    s = _safe(scores)
    if not s.empty:
        keep = [c for c in ["provider_type", "opportunity_percentile",
                             "opportunity_score", "total_payment"] if c in s.columns]
        if keep:
            tables.append(s[keep].copy())

    v = _safe(value_summary)
    if not v.empty:
        keep = [c for c in ["provider_type", "value_percentile",
                             "value_score"] if c in v.columns]
        if keep:
            tables.append(v[keep].copy())

    iv = _safe(investability)
    if not iv.empty:
        keep = [c for c in ["provider_type", "investability_score"] if c in iv.columns]
        if keep:
            tables.append(iv[keep].copy())

    st = _safe(stress_test)
    if not st.empty:
        keep = [c for c in ["provider_type", "stress_adjusted_score"] if c in st.columns]
        if keep:
            tables.append(st[keep].copy())

    mo = _safe(momentum)
    if not mo.empty:
        keep = [c for c in ["provider_type", "consistency_percentile",
                             "consistency_score"] if c in mo.columns]
        if keep:
            tables.append(mo[keep].copy())

    reg = _safe(provider_regimes)
    if not reg.empty and "regime" in reg.columns:
        reg = reg.copy()
        reg["regime_score"] = reg["regime"].astype(str).map(_REGIME_BOOST).fillna(0.0)
        keep = [c for c in ["provider_type", "regime_score"] if c in reg.columns]
        tables.append(reg[keep])

    if not tables:
        return pd.DataFrame()

    out = tables[0].copy()
    for t in tables[1:]:
        out = out.merge(t, on="provider_type", how="outer")

    pct_cols = [c for c in ["opportunity_percentile", "value_percentile",
                             "consistency_percentile"] if c in out.columns]
    for col in pct_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    score_cols = [c for c in ["investability_score", "stress_adjusted_score",
                               "opportunity_score", "value_score",
                               "consistency_score"] if c in out.columns]
    for col in score_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        out[f"{col}_pct"] = _pct_rank(out[col])

    # Include all computed _pct columns + pre-existing percentile cols + regime boost
    all_pct = [c for c in out.columns if c.endswith("_pct")]
    rank_inputs = list(set(pct_cols + all_pct + [c for c in ["regime_score"] if c in out.columns]))

    if not rank_inputs:
        return pd.DataFrame()

    out["consensus_score"] = out[rank_inputs].mean(axis=1, skipna=True)
    out["consensus_percentile"] = _pct_rank(out["consensus_score"])
    return out.sort_values("consensus_score", ascending=False).reset_index(drop=True)


def detect_state_provider_anomalies(
    df,
    z_threshold: float = 2.5,
    min_rows: int = 15,
):
    """Detect unusually priced provider-state-year cohorts vs. national peers.

    For each (provider_type, state, year) cohort, computes:
        service_z = (cohort_median_payment_per_service - peer_median) / peer_std

    Flags cohorts where |z| >= z_threshold as 'cost_spike' or 'cost_trough'.

    Ported from cms_medicare/cms_api_advisory_analytics.py::detect_state_provider_anomalies.

    Returns empty DataFrame if required columns are absent or pandas not available.
    """
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        return []

    needed = {"provider_type", "state", "year",
              "payment_per_service", "total_medicare_payment_amt"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    for col in ["payment_per_service", "total_medicare_payment_amt", "year"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")
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
        grouped.groupby(["provider_type", "year"], as_index=False)
        ["median_payment_per_service"]
        .agg(peer_median="median", peer_std="std")
    )
    out = grouped.merge(peer, on=["provider_type", "year"], how="left")
    out["peer_std"] = out["peer_std"].replace(0, np.nan)
    out["service_z"] = (
        (out["median_payment_per_service"] - out["peer_median"]) / out["peer_std"]
    )
    out["anomaly_flag"] = "normal"
    out.loc[out["service_z"] >= z_threshold, "anomaly_flag"] = "cost_spike"
    out.loc[out["service_z"] <= -z_threshold, "anomaly_flag"] = "cost_trough"
    out["anomaly_magnitude"] = out["service_z"].abs()
    return out.sort_values(
        ["anomaly_magnitude", "total_payment"], ascending=[False, False]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def consensus_rank_table(rank_result, top_n: int = 20) -> str:
    """Format consensus rank as a text table.

    Accepts either a pandas DataFrame or a list of dicts.
    """
    try:
        import pandas as pd
        if isinstance(rank_result, pd.DataFrame):
            rows = rank_result.head(top_n).to_dict("records")
        else:
            rows = rank_result[:top_n]
    except ImportError:
        rows = rank_result[:top_n] if isinstance(rank_result, list) else []

    if not rows:
        return "No consensus rank data.\n"

    lines = [
        f"{'Provider Type':<35} {'Consensus Score':>16} {'Percentile':>11}",
        "-" * 65,
    ]
    for row in rows:
        pt = str(row.get("provider_type", ""))[:33]
        score = row.get("consensus_score")
        pct = row.get("consensus_percentile")
        score_s = f"{score:.4f}" if isinstance(score, float) else "n/a"
        pct_s = f"{pct:.1%}" if isinstance(pct, float) else "n/a"
        lines.append(f"{pt:<35} {score_s:>16} {pct_s:>11}")
    return "\n".join(lines) + "\n"


def anomaly_table(anomalies, top_n: int = 20) -> str:
    """Format anomaly detection results as a text table."""
    try:
        import pandas as pd
        if isinstance(anomalies, pd.DataFrame):
            rows = anomalies.head(top_n).to_dict("records")
        else:
            rows = anomalies[:top_n] if isinstance(anomalies, list) else []
    except ImportError:
        rows = anomalies[:top_n] if isinstance(anomalies, list) else []

    if not rows:
        return "No anomalies detected.\n"

    lines = [
        f"{'Provider Type':<30} {'State':>6} {'Year':>5} {'Z-Score':>8} {'Flag':<14} {'Total Pay ($M)':>14}",
        "-" * 82,
    ]
    for row in rows:
        pt = str(row.get("provider_type", ""))[:28]
        st = str(row.get("state", ""))
        yr = str(int(row["year"])) if row.get("year") else "n/a"
        z = row.get("service_z")
        flag = str(row.get("anomaly_flag", ""))
        pay = row.get("total_payment")
        z_s = f"{z:+.2f}" if isinstance(z, float) else "n/a"
        pay_s = f"${pay/1e6:,.1f}M" if isinstance(pay, (int, float)) else "n/a"
        lines.append(f"{pt:<30} {st:>6} {yr:>5} {z_s:>8} {flag:<14} {pay_s:>14}")
    return "\n".join(lines) + "\n"
