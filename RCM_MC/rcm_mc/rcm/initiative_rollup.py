"""Cross-deal initiative rollup (Brick 83).

Single-deal initiative variance (B57) answers "which workstream is behind
*on this deal*?". The cross-deal rollup answers the portfolio-level
question: "is `prior_auth_improvement` consistently delivering? Which
deals are running it? Where's it off?".

Given a PE firm holds 5-15 RCM platforms running 2-4 initiatives each,
pattern recognition across deals is the leverage point. If 6 out of 8
deals running ``coding_cdi_improvement`` are lagging, the problem isn't
deal-specific — it's the playbook.

Public API:
    initiative_portfolio_rollup(store) -> pd.DataFrame
        One row per initiative. Columns: initiative_id, deal_count,
        avg_variance_pct, cumulative_actual, cumulative_plan, severity.

    initiative_deals_detail(store, initiative_id) -> pd.DataFrame
        Drill-down: every deal running the given initiative with its
        per-deal variance + severity.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .initiative_tracking import initiative_variance_report
from ..portfolio.store import PortfolioStore


def initiative_portfolio_rollup(store: PortfolioStore) -> pd.DataFrame:
    """Aggregate per-initiative stats across every deal in the store.

    Returns one row per initiative_id with:
      - ``deal_count``: how many deals are running it
      - ``cumulative_actual``: Σ across deals of cumulative EBITDA impact
      - ``cumulative_plan``: Σ across deals of pro-rated plan
      - ``avg_variance_pct``: mean of per-deal variance (simple, not weighted)
      - ``severity``: worst severity across deals
        (off_track > lagging > on_track > no_plan)
    """
    # Pull every deal_id that has at least one initiative actual recorded
    _ensure = _get_initiative_deal_ids
    deal_ids = _ensure(store)
    if not deal_ids:
        return pd.DataFrame(columns=[
            "initiative_id", "deal_count",
            "cumulative_actual", "cumulative_plan",
            "avg_variance_pct", "severity",
        ])

    # Per-deal variance frames → union
    per_init: dict = {}
    for did in deal_ids:
        df = initiative_variance_report(store, did)
        if df.empty:
            continue
        for _, r in df.iterrows():
            init_id = str(r["initiative_id"])
            per_init.setdefault(init_id, []).append(r)

    _sev_rank = {"off_track": 3, "lagging": 2, "no_plan": 1, "on_track": 0}
    rows = []
    for init_id, records in per_init.items():
        actuals = [float(r["cumulative_actual"]) for r in records
                   if r["cumulative_actual"] is not None
                   and r["cumulative_actual"] == r["cumulative_actual"]]
        plans = [float(r["cumulative_plan"]) for r in records
                 if r["cumulative_plan"] is not None
                 and r["cumulative_plan"] == r["cumulative_plan"]]
        variances = [float(r["variance_pct"]) for r in records
                     if r["variance_pct"] is not None
                     and r["variance_pct"] == r["variance_pct"]]
        severities = [str(r["severity"]) for r in records if r.get("severity")]

        worst_severity = max(severities, key=lambda s: _sev_rank.get(s, -1)) if severities else "no_plan"
        rows.append({
            "initiative_id": init_id,
            "deal_count": len(records),
            "cumulative_actual": sum(actuals) if actuals else 0.0,
            "cumulative_plan": sum(plans) if plans else None,
            "avg_variance_pct": (sum(variances) / len(variances)) if variances else None,
            "severity": worst_severity,
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        # Worst-first by severity, then by magnitude of variance
        _sev_order = {"off_track": 0, "lagging": 1, "no_plan": 2, "on_track": 3}
        out = out.sort_values(
            ["severity", "avg_variance_pct"],
            key=lambda col: col.map(_sev_order) if col.name == "severity" else col,
            na_position="last",
        ).reset_index(drop=True)
    return out


def initiative_deals_detail(
    store: PortfolioStore,
    initiative_id: str,
) -> pd.DataFrame:
    """Drill-down: every deal that runs ``initiative_id``.

    Returns one row per deal with that initiative, preserving the
    per-deal columns from :func:`initiative_variance_report`. Sorted
    worst-variance-first so partners see the laggards immediately.
    """
    deal_ids = _get_initiative_deal_ids(store)
    rows = []
    for did in deal_ids:
        df = initiative_variance_report(store, did)
        if df.empty:
            continue
        matching = df[df["initiative_id"] == initiative_id]
        for _, r in matching.iterrows():
            rows.append(r.to_dict())
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(
            "variance_pct", ascending=True, na_position="last",
        ).reset_index(drop=True)
    return out


# ── Internal helpers ──────────────────────────────────────────────────────

def _get_initiative_deal_ids(store: PortfolioStore) -> list:
    """Return unique deal_ids that appear in initiative_actuals."""
    from .initiative_tracking import _ensure_initiative_table
    _ensure_initiative_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT DISTINCT deal_id FROM initiative_actuals "
            "ORDER BY deal_id"
        ).fetchall()
    return [r["deal_id"] for r in rows]
