"""
growth_decomposition.py  (v34)
==============================

Anticipated issue: the growth number with no anatomy. The first question any IC
asks about a "market growing X percent" slide is how much is price (ASP
inflation on single-source drugs) versus volume (utilization) versus mix (new
molecules, biosimilar substitution). The panel can answer it exactly, and if the
toolkit does not, someone will eyeball it in the meeting.

Laspeyres-style decomposition between the first and last full period, per
molecule and in total:

  dollars_delta = price effect      base units at new rate minus base rate
                + volume effect     base rate on unit change
                + interaction       rate change times unit change
                + entry             molecules with dollars only in the last period
                + exit              molecules with dollars only in the first period

Rates are allowed per unit at the molecule grain. Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def price_volume_mix(std_named: pd.DataFrame, *, allowed, units, year,
                     common_name_col: str = "drug_common_name",
                     top_n: int = 15) -> pd.DataFrame:
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    u = pd.to_numeric(units, errors="coerce").fillna(0.0)
    yr = pd.Series(np.asarray(year), index=std_named.index)
    name = (std_named[common_name_col].astype("string").fillna("(unknown)")
            if common_name_col in std_named.columns
            else pd.Series("(unknown)", index=std_named.index))
    yrs = sorted(pd.unique(yr.dropna()))
    if len(yrs) < 2:
        return pd.DataFrame({"note": ["need at least two periods to decompose growth"]})
    y0, y1 = yrs[0], yrs[-1]
    df = pd.DataFrame({"m": name.to_numpy(), "y": yr.to_numpy(),
                       "a": a.to_numpy(), "u": u.to_numpy()})
    g = df[df["y"].isin([y0, y1])].groupby(["m", "y"]).sum(numeric_only=True)

    rows = []
    tot = {"price": 0.0, "volume": 0.0, "interaction": 0.0, "entry": 0.0,
           "exit": 0.0, "unpriceable": 0.0}
    mols = sorted({m for m, _ in g.index})
    for m in mols:
        a0 = float(g["a"].get((m, y0), 0.0))
        u0 = float(g["u"].get((m, y0), 0.0))
        a1 = float(g["a"].get((m, y1), 0.0))
        u1 = float(g["u"].get((m, y1), 0.0))
        delta = a1 - a0
        if a0 > 0 and u0 > 0 and a1 > 0 and u1 > 0:
            p0, p1 = a0 / u0, a1 / u1
            pe = u0 * (p1 - p0)
            ve = p0 * (u1 - u0)
            ie = (p1 - p0) * (u1 - u0)
            rows.append({"molecule": m, "dollars_first": round(a0, 2), "dollars_last": round(a1, 2),
                         "dollars_delta": round(delta, 2), "price_effect": round(pe, 2),
                         "volume_effect": round(ve, 2), "interaction": round(ie, 2),
                         "entry_exit": 0.0,
                         "class": "continuing"})
            tot["price"] += pe
            tot["volume"] += ve
            tot["interaction"] += ie
        elif a0 <= 0 and a1 > 0:
            rows.append({"molecule": m, "dollars_first": 0.0, "dollars_last": round(a1, 2),
                         "dollars_delta": round(delta, 2), "price_effect": 0.0,
                         "volume_effect": 0.0, "interaction": 0.0,
                         "entry_exit": round(a1, 2), "class": "entry (new molecule)"})
            tot["entry"] += a1
        elif a0 > 0 and a1 <= 0:
            rows.append({"molecule": m, "dollars_first": round(a0, 2), "dollars_last": 0.0,
                         "dollars_delta": round(delta, 2), "price_effect": 0.0,
                         "volume_effect": 0.0, "interaction": 0.0,
                         "entry_exit": round(-a0, 2), "class": "exit"})
            tot["exit"] -= a0
        elif abs(delta) > 0:
            # Dollars in both periods but units missing in one: the delta is
            # REAL and must stay in the tie-out; it just cannot be decomposed.
            rows.append({"molecule": m, "dollars_first": round(a0, 2),
                         "dollars_last": round(a1, 2),
                         "dollars_delta": round(delta, 2), "price_effect": 0.0,
                         "volume_effect": 0.0, "interaction": 0.0,
                         "entry_exit": round(delta, 2),
                         "class": "unpriceable (units missing in a period; "
                                  "delta carried undecomposed)"})
            tot["unpriceable"] += delta
        else:
            continue
    body = (pd.DataFrame(rows)
            .assign(_abs=lambda d: d["dollars_delta"].abs())
            .sort_values("_abs", ascending=False).drop(columns="_abs")
            .head(top_n))
    total_delta = sum(tot.values())
    summary = pd.DataFrame([{
        "molecule": "TOTAL ({} to {})".format(y0, y1),
        "dollars_first": round(float(df.loc[df["y"] == y0, "a"].sum()), 2),
        "dollars_last": round(float(df.loc[df["y"] == y1, "a"].sum()), 2),
        "dollars_delta": round(total_delta, 2),
        "price_effect": round(tot["price"], 2),
        "volume_effect": round(tot["volume"], 2),
        "interaction": round(tot["interaction"], 2),
        "entry_exit": round(tot["entry"] + tot["exit"] + tot["unpriceable"], 2),
        "class": "decomposition ties to delta by construction "
                 "(entry_exit cell includes any undecomposed unit-missing residual)"}])
    out = pd.concat([summary, body], ignore_index=True)
    d = abs(total_delta)
    if d > 0:
        out.attrs["price_share_pct"] = round(tot["price"] / total_delta * 100, 1) if total_delta != 0 else np.nan
        out.attrs["volume_share_pct"] = round(tot["volume"] / total_delta * 100, 1) if total_delta != 0 else np.nan
    out.attrs["note"] = (
        "Laspeyres decomposition at the molecule grain; price is base units at the rate "
        "change, volume is base rate at the unit change, entry/exit is molecules present in "
        "only one period. The shares answer the is-it-price-or-utilization question exactly.")
    return out
