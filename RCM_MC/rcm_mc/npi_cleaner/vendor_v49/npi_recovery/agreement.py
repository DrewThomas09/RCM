"""
agreement.py  (v44)
===================

Recover each blank billing NPI two independent ways and treat agreement as a
precision signal. Ensemble disagreement is a rigorous, model-free source of
confidence: when two methods that use genuinely different evidence land on the
same biller, that recovery is far more trustworthy than either method alone; when
they disagree, that is a signal to hold the recovery for review rather than ship
a guess.

The two methods are independent by construction:

  Method A (in-panel pattern):  who bills this drug for this referring provider,
                                in this geography, on this payer, as observed in
                                THIS file. Evidence is the file's own co-occurrence
                                structure.
  Method B (CMS candidate pool): who bills this drug in this state at national
                                scale, from the CMS utilization pool. Evidence is
                                external Medicare volume, not this file.

They share no inputs beyond the drug and the row, so agreement is meaningful.

For each blank the module reports:
  method_a_npi, method_b_npi   each method's independent top-1 (or blank)
  agreement                    agree / disagree / a_only / b_only / neither
  agreement_boost              a confidence multiplier the recovery model and the
                               tiering can consume (agree lifts, disagree damps)

This does not overwrite the primary recovery. It annotates it, feeds the
calibrated model a signal, and drives the review queue and the seller data
request list.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def _method_a_row(imp, row):
    """Best in-panel prediction for one row, ignoring the CMS pool entirely."""
    for t in imp.in_panel_tiers:
        key = imp._row_key(row, t["keys"])
        if key is None:
            continue
        entry = imp.tables.get(t["name"], {}).get(key)
        if not entry:
            continue
        w, nobs = entry["w"], entry["n"]
        total_w = sum(w.values())
        total_n = sum(nobs.values())
        if total_n < imp.min_support or total_w <= 0:
            continue
        ranked = sorted(w.items(), key=lambda kv: (-kv[1], kv[0]))
        top1, w1 = ranked[0]
        share1 = w1 / total_w
        return {"npi": str(top1), "tier": t["name"], "share": round(share1, 4),
                "support": int(total_n)}
    return {"npi": "", "tier": "", "share": 0.0, "support": 0}


def _method_b_row(imp, row):
    """CMS candidate-pool prediction for one row, ignoring in-panel patterns."""
    hcpcs = str(row.get("hcpcs")) if not pd.isna(row.get("hcpcs")) else None
    state = str(row.get("state")) if not pd.isna(row.get("state")) else None
    pool = imp.pools.get((hcpcs, state))
    if pool is None or pool.empty:
        return {"npi": "", "share": 0.0, "support": 0}
    tot = float(pool["srvcs"].sum()) or 1.0
    top = pool.iloc[0]
    return {"npi": str(top["npi"]), "share": round(float(top["srvcs"]) / tot, 4),
            "support": int(round(tot))}


def two_method_table(std: pd.DataFrame, imp, blank_index) -> pd.DataFrame:
    """For each blank row, run both methods independently and classify agreement.

    std          standardized frame
    imp          a fitted ReferralImputer (has .tables, .pools, .in_panel_tiers)
    blank_index  index of rows whose billing NPI is blank (the recovery targets)
    """
    rows = []
    sub = std.loc[blank_index]
    for idx, row in sub.iterrows():
        a = _method_a_row(imp, row)
        b = _method_b_row(imp, row)
        an, bn = a["npi"], b["npi"]
        if an and bn:
            state = "agree" if an == bn else "disagree"
        elif an:
            state = "a_only"
        elif bn:
            state = "b_only"
        else:
            state = "neither"
        # agreement boost: agree lifts, disagree damps, single-method neutral.
        boost = {"agree": 1.15, "disagree": 0.6, "a_only": 1.0,
                 "b_only": 0.9, "neither": 0.8}[state]
        rows.append({
            "row": idx,
            "method_a_npi": an, "method_a_tier": a.get("tier", ""),
            "method_a_share": a["share"],
            "method_b_npi": bn, "method_b_share": b["share"],
            "agreement": state, "agreement_boost": boost,
        })
    out = pd.DataFrame(rows)
    if out.empty:
        out = pd.DataFrame(columns=["row", "method_a_npi", "method_a_tier",
                                    "method_a_share", "method_b_npi",
                                    "method_b_share", "agreement", "agreement_boost"])
    return out


def agreement_summary(tbl: pd.DataFrame, std: pd.DataFrame = None,
                      mapping=None) -> pd.DataFrame:
    """Dollar- and count-weighted rollup of the agreement classes, the headline
    diligence cut: how much of the recovered book rests on two-method agreement
    versus a single method versus an unresolved disagreement."""
    if tbl.empty:
        return pd.DataFrame(columns=["agreement", "rows", "dollars", "pct_dollars"])
    amt = None
    if std is not None:
        acol = (mapping or {}).get("allowed_amt", "allowed_amt")
        acol = acol if acol in std.columns else ("allowed_amt" if "allowed_amt" in std.columns else None)
        if acol is not None:
            amt = pd.to_numeric(std.loc[tbl["row"], acol], errors="coerce").fillna(0.0).clip(lower=0).to_numpy()
    d = tbl.copy()
    d["dollars"] = amt if amt is not None else 1.0
    g = (d.groupby("agreement")
         .agg(rows=("row", "size"), dollars=("dollars", "sum")).reset_index())
    tot = float(g["dollars"].sum()) or 1.0
    g["pct_dollars"] = (100.0 * g["dollars"] / tot).round(1)
    g = g.sort_values("dollars", ascending=False).reset_index(drop=True)
    agree_d = float(g[g["agreement"] == "agree"]["dollars"].sum())
    disagree_d = float(g[g["agreement"] == "disagree"]["dollars"].sum())
    g.attrs["note"] = (
        f"{round(100.0*agree_d/tot,1)}% of recovered dollars rest on two-method "
        f"agreement (in-panel pattern and CMS pool independently name the same "
        f"biller). {round(100.0*disagree_d/tot,1)}% are two-method disagreements: "
        f"treat those as leads to verify, not base-case recoveries.")
    return g


def disagreement_queue(tbl: pd.DataFrame, std: pd.DataFrame = None,
                       mapping=None, top_n=200) -> pd.DataFrame:
    """The rows where the two methods disagree, ranked by dollars, for review.
    These are the highest-value precision risks in the recovery."""
    dis = tbl[tbl["agreement"] == "disagree"].copy()
    if dis.empty:
        out = pd.DataFrame(columns=["row", "method_a_npi", "method_b_npi",
                                    "dollars", "recommended_action"])
        out.attrs["note"] = "No two-method disagreements. Recovery is internally consistent."
        return out
    if std is not None:
        acol = (mapping or {}).get("allowed_amt", "allowed_amt")
        acol = acol if acol in std.columns else ("allowed_amt" if "allowed_amt" in std.columns else None)
        if acol is not None:
            dis["dollars"] = pd.to_numeric(std.loc[dis["row"], acol], errors="coerce").fillna(0.0).clip(lower=0).to_numpy()
        else:
            dis["dollars"] = 1.0
    else:
        dis["dollars"] = 1.0
    dis["recommended_action"] = (
        "verify biller: in-panel pattern and CMS pool name different NPIs")
    keep = ["row", "method_a_npi", "method_a_tier", "method_b_npi", "dollars",
            "recommended_action"]
    out = dis.sort_values("dollars", ascending=False).head(top_n)[keep].reset_index(drop=True)
    out.attrs["note"] = (
        f"{len(dis)} rows where the two methods disagree ({int(dis['dollars'].sum()):,} "
        f"dollars). Top {min(top_n, len(dis))} shown. These recovered NPIs are the "
        f"ones most worth a second look before relying on them.")
    return out
