"""
concentration.py  (v34)
=======================

Anticipated issue: the fragmentation slide with no numbers behind it. Payer
concentration, provider concentration, prescriber (referral) concentration, and
molecule concentration are standard market-structure exhibits, and each needs an
HHI and top-N shares computed on the right entity grain (normalized payers, not
strings; molecules, not codes). Prescriber taxonomy mix answers where demand
originates when a referring NPI column exists.

Hand-rolled HHI: sum of squared percentage shares. Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def hhi(values: pd.Series) -> float:
    """Sum of squared percentage shares (0 to 10000)."""
    v = pd.to_numeric(values, errors="coerce").fillna(0.0)
    v = v[v > 0]
    tot = float(v.sum())
    if tot <= 0:
        return 0.0
    sh = v / tot * 100
    return round(float((sh ** 2).sum()), 0)


def _band(h: float) -> str:
    if h < 1500:
        return "UNCONCENTRATED (<1500)"
    if h < 2500:
        return "MODERATELY CONCENTRATED (1500 to 2500)"
    return "HIGHLY CONCENTRATED (>2500)"


def concentration_table(std_named: pd.DataFrame, *, allowed,
                        payer_parent: pd.Series | None = None,
                        common_name_col: str = "drug_common_name") -> pd.DataFrame:
    """One row per lens: entity count, HHI with the DOJ band, and top-1/5/10
    dollar shares. Lenses run only where the column exists."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    lenses = []
    if payer_parent is not None:
        lenses.append(("payer (normalized parent)", payer_parent))
    elif "payer" in std_named.columns:
        lenses.append(("payer (RAW STRINGS, normalize first)",
                       std_named["payer"].astype("string").fillna("(blank)")))
    if "billing_npi" in std_named.columns:
        lenses.append(("billing provider", std_named["billing_npi"].astype("string").fillna("")))
    if "referring_npi" in std_named.columns:
        ref = std_named["referring_npi"].astype("string").fillna("")
        if (ref.str.strip() != "").any():
            lenses.append(("prescriber / referring", ref))
    if common_name_col in std_named.columns:
        lenses.append(("molecule", std_named[common_name_col].astype("string").fillna("(unknown)")))

    rows = []
    for label, key in lenses:
        k = key.astype("string").fillna("")
        mask = k.str.strip() != ""
        g = a[mask].groupby(k[mask]).sum().sort_values(ascending=False)
        tot = float(g.sum())
        if tot <= 0:
            continue
        h = hhi(g)
        rows.append({"lens": label, "n_entities": int(len(g)), "hhi": h,
                     "band": _band(h),
                     "top1_share_pct": round(float(g.iloc[:1].sum()) / tot * 100, 1),
                     "top5_share_pct": round(float(g.iloc[:5].sum()) / tot * 100, 1),
                     "top10_share_pct": round(float(g.iloc[:10].sum()) / tot * 100, 1)})
    if not rows:
        return pd.DataFrame({"note": ["no concentration lenses available on this panel"]})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "HHI is the sum of squared percentage shares; bands follow the DOJ thresholds. Payer "
        "concentration is only meaningful on normalized parents.")
    return out


def prescriber_taxonomy_mix(std: pd.DataFrame, *, allowed, taxonomy_of=None,
                            referring_col: str = "referring_npi",
                            top_n: int = 12) -> pd.DataFrame:
    """Where demand originates: referring-NPI dollars rolled up by taxonomy code
    (taxonomy_of: npi -> taxonomy). The neurology-led-or-not answer."""
    if referring_col not in std.columns or not taxonomy_of:
        return pd.DataFrame({"note": ["needs a referring NPI column and a taxonomy map "
                                      "(taxonomy_of) to attribute demand origin"]})
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    ref = std[referring_col].astype("string").fillna("").str.strip()
    tax = ref.map(lambda n: taxonomy_of.get(n, "") if n else "")
    mask = tax != ""
    if not mask.any():
        return pd.DataFrame({"note": ["no referring NPIs resolved to a taxonomy; extend the "
                                      "taxonomy map or run NPPES enrichment"]})
    g = a[mask].groupby(tax[mask]).sum().sort_values(ascending=False)
    tot_all = float(a.sum())
    out = pd.DataFrame({"referring_taxonomy": g.index, "allowed": g.round(2).to_numpy(),
                        "share_of_attributed_pct": (g / float(g.sum()) * 100).round(1).to_numpy()}).head(top_n)
    out.attrs["attributed_share_of_panel_pct"] = round(float(g.sum()) / tot_all * 100, 1) if tot_all > 0 else 0.0
    out.attrs["note"] = (
        "Referral dollars by prescriber taxonomy; {} percent of panel dollars carry a resolved "
        "referring taxonomy. Cite the attributed share alongside the mix.".format(
            out.attrs["attributed_share_of_panel_pct"]))
    return out
