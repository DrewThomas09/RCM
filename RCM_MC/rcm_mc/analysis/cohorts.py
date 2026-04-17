"""Cohort analytics: group-by-tag portfolio rollup (Brick 106).

Partners don't just ask "how is the portfolio doing?" — they slice it:
"how are our growth deals vs the roll-ups?" "is the legacy fund
under-performing the new one?" Tags (B86) are the vehicle for those
slices; this module aggregates latest-per-deal metrics by tag so the
comparison is one SQL query away.

Public API::

    cohort_rollup(store) -> pd.DataFrame
        # one row per tag, across all tags in the store

    cohort_detail(store, tag) -> pd.DataFrame
        # one row per deal in that cohort with latest metrics

Note on NULL handling: deals with no MOIC/IRR (e.g., pre-underwrite
stages) are excluded from the weighted averages — a cohort average
that silently drops ciphered values is misleading. The ``n_priced``
column reflects how many deals actually had entry_ev to weight.
"""
from __future__ import annotations

from typing import List

import pandas as pd

from ..deals.deal_tags import _ensure_tags_table  # noqa — used implicitly via queries
from ..portfolio.store import PortfolioStore
from ..portfolio.portfolio_snapshots import latest_per_deal


def _tags_joined(store: PortfolioStore) -> pd.DataFrame:
    """Return (deal_id, tag) rows — empty DF if no tags yet."""
    _ensure_tags_table(store)
    with store.connect() as con:
        return pd.read_sql_query(
            "SELECT deal_id, tag FROM deal_tags", con,
        )


def cohort_rollup(store: PortfolioStore) -> pd.DataFrame:
    """Aggregate per-tag rollup. Empty DF if there are no tags.

    Columns: tag, deal_count, weighted_moic, weighted_irr,
    covenant_trips, covenant_tight, concerning_deals, n_priced.
    """
    latest = latest_per_deal(store)
    tags = _tags_joined(store)
    if tags.empty or latest.empty:
        return pd.DataFrame(columns=[
            "tag", "deal_count", "weighted_moic", "weighted_irr",
            "covenant_trips", "covenant_tight", "concerning_deals",
            "n_priced",
        ])

    # Join tags onto latest — deals can have multiple tags → row fanout
    merged = tags.merge(latest, on="deal_id", how="inner")
    if merged.empty:
        return pd.DataFrame(columns=[
            "tag", "deal_count", "weighted_moic", "weighted_irr",
            "covenant_trips", "covenant_tight", "concerning_deals",
            "n_priced",
        ])

    # B150 fix: Decimal-summed weighted averages, same as
    # portfolio_snapshots.portfolio_rollup — avoids float drift over
    # many deals.
    from decimal import Decimal as _D
    out_rows: List[dict] = []
    for tag, group in merged.groupby("tag"):
        sized = group.dropna(subset=["moic", "irr", "entry_ev"])
        weighted_moic = None
        weighted_irr = None
        if not sized.empty:
            weights_f = sized["entry_ev"].astype(float).tolist()
            moic_f = sized["moic"].astype(float).tolist()
            irr_f = sized["irr"].astype(float).tolist()
            total_w = sum(_D(str(w)) for w in weights_f)
            if total_w > 0:
                wm = sum(_D(str(m)) * _D(str(w))
                         for m, w in zip(moic_f, weights_f)) / total_w
                wi = sum(_D(str(r)) * _D(str(w))
                         for r, w in zip(irr_f, weights_f)) / total_w
                weighted_moic = float(wm)
                weighted_irr = float(wi)
        concerning = group["concerning_signals"].fillna(0).astype(int)
        out_rows.append({
            "tag": tag,
            "deal_count": int(len(group)),
            "weighted_moic": weighted_moic,
            "weighted_irr": weighted_irr,
            "covenant_trips": int((group["covenant_status"] == "TRIPPED").sum()),
            "covenant_tight": int((group["covenant_status"] == "TIGHT").sum()),
            "concerning_deals": int((concerning >= 1).sum()),
            "n_priced": int(len(sized)),
        })
    df = pd.DataFrame(out_rows)
    return df.sort_values("deal_count", ascending=False).reset_index(drop=True)


def cohort_detail(store: PortfolioStore, tag: str) -> pd.DataFrame:
    """Per-deal latest metrics for one tag cohort. Empty DF on unknown tag."""
    latest = latest_per_deal(store)
    tags = _tags_joined(store)
    if tags.empty or latest.empty:
        return pd.DataFrame()
    members = tags[tags["tag"] == str(tag).lower()]["deal_id"].tolist()
    if not members:
        return latest.iloc[0:0]  # same columns, zero rows
    return (
        latest[latest["deal_id"].isin(members)]
        .sort_values("created_at", ascending=False)
        .reset_index(drop=True)
    )
