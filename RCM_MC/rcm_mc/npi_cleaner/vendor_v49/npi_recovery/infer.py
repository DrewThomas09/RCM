"""Step 4.5: two-hop / group-inference recovery for the billing NPI.

Single-hop referral imputation (impute.py) caps out because each blank row's
direct key is missing. But claims travel in groups — same referrer + drug +
area, same patient across visits — and a blank in one row is usually populated
in a sibling row. This module borrows from those siblings to fill attributable
blanks the point imputer didn't confidently resolve.

These fills are tiered "inferred", NOT "point": they land in the billing column
(so the blank rate can drop to a few percent) but are labelled distinctly and
never presented as a direct lookup. Two layers, strongest first:

  1. Continuity inheritance — same patient + same drug + same site across
     visits is the same biller. A blank inherits the nearest populated biller of
     that (patient, drug, site) within a gap guard; it never bridges a long break
     or a site change. Needs a patient/member ID + a date column.

  2. Cluster dominance — within a tight (referrer, drug, ZIP3 [, payer]) cluster,
     if one operator bills the overwhelming majority of the populated rows, the
     blanks inherit it. Billers are rolled to parent via the entity crosswalk
     first, so post-acquisition siblings count together; the high dominance
     threshold means a real change-of-ownership splits the cluster and fails
     CLOSED rather than inferring the wrong operator.

Both return a frame indexed by the std row index, so the pipeline can fold the
result back into the per-blank recovery table.
"""

import pandas as pd

from . import config


def _roll_map(crosswalk):
    if crosswalk is None or crosswalk.empty or "legacy_npi" not in crosswalk.columns:
        return {}
    return dict(zip(crosswalk["legacy_npi"].astype(str),
                    crosswalk["parent_operator"].astype(str)))


def _cluster_key(df, keys):
    """A per-row tuple key over `keys`, NA where any component is blank."""
    sub = df[keys].astype("string")
    mask = sub.notna().all(axis=1) & (sub != "").all(axis=1)
    key = pd.Series(pd.NA, index=df.index, dtype="object")
    if mask.any():
        key.loc[mask] = [tuple(v) for v in sub.loc[mask].to_numpy()]
    return key


def infer_continuity(std, eligible_index, max_gap_days=None):
    """Same patient + same drug + same site => same biller, within a gap guard.

    Returns a DataFrame indexed by std row index with columns inferred_npi,
    gap_days. Empty if the data lacks a patient ID or a usable date column.
    """
    cols = ["inferred_npi", "gap_days"]
    if max_gap_days is None:
        max_gap_days = config.CONTINUITY_MAX_GAP_DAYS
    if "patient_id" not in std.columns or "date" not in std.columns:
        return pd.DataFrame(columns=cols)

    df = std.copy()
    df["_bn"] = df["billing_npi"].astype("string")
    df["_dt"] = pd.to_datetime(df["date"], errors="coerce")
    by = ["patient_id", "hcpcs"] + (["pos"] if "pos" in df.columns else [])

    pop = df[(~df["is_blank_billing"].fillna(False)) & df["_bn"].notna() & df["_dt"].notna()]
    pop = pop.dropna(subset=by)
    elig = df[df.index.isin(eligible_index) & df["is_blank_billing"].fillna(False) & df["_dt"].notna()]
    elig = elig.dropna(subset=by)
    if pop.empty or elig.empty:
        return pd.DataFrame(columns=cols)

    # nearest populated biller in the same (patient, drug, site) within tolerance
    left = (elig.assign(_idx=elig.index)[["_dt", "_idx"] + by]
            .sort_values("_dt").reset_index(drop=True))
    right = pop[["_dt", "_bn"] + by].sort_values("_dt").reset_index(drop=True)
    for c in by:                       # merge_asof needs matching 'by' dtypes
        left[c] = left[c].astype("string")
        right[c] = right[c].astype("string")
    merged = pd.merge_asof(left, right, on="_dt", by=by, direction="nearest",
                           tolerance=pd.Timedelta(days=int(max_gap_days)))
    merged = merged.dropna(subset=["_bn"])
    if merged.empty:
        return pd.DataFrame(columns=cols)
    res = pd.DataFrame({"inferred_npi": merged["_bn"].astype(str).values},
                       index=merged["_idx"].values)
    res["gap_days"] = pd.NA           # tolerance enforces the guard; exact gap not retained
    return res


def relevant_populated_billers(std, eligible_index, keys=None, use_payer=None, min_support=None):
    """Distinct POPULATED billing NPIs that share a cluster with an eligible
    blank — the only billers whose entity rollup can change cluster dominance.
    The pipeline rolls just these (not the whole file) so the CHOW guard runs on
    rolled operators without an unbounded NPPES pass."""
    keys = list(keys or config.CLUSTER_KEYS)
    use_payer = config.CLUSTER_USE_PAYER if use_payer is None else use_payer
    keys = [k for k in keys if k in std.columns]
    if use_payer and "payer" in std.columns and std["payer"].notna().any() and "payer" not in keys:
        keys = keys + ["payer"]
    if not keys:
        return set()
    df = std.copy()
    df["_bn"] = df["billing_npi"].astype("string")
    df["_ckey"] = _cluster_key(df, keys)
    elig_keys = set(df.loc[df.index.isin(eligible_index)
                           & df["is_blank_billing"].fillna(False), "_ckey"].dropna())
    if not elig_keys:
        return set()
    pop = df[(~df["is_blank_billing"].fillna(False)) & df["_bn"].notna() & df["_ckey"].isin(elig_keys)]
    return {str(x) for x in pop["_bn"].dropna()}


def infer_cluster(std, eligible_index, crosswalk=None, keys=None,
                  use_payer=None, dominance=None, min_support=None):
    """Cluster-dominance inference for the billing NPI.

    Returns a DataFrame indexed by std row index with columns inferred_npi,
    dominance, cluster_n. Empty if no cluster clears the threshold.
    """
    cols = ["inferred_npi", "dominance", "cluster_n"]
    keys = list(keys or config.CLUSTER_KEYS)
    use_payer = config.CLUSTER_USE_PAYER if use_payer is None else use_payer
    dominance = config.CLUSTER_DOMINANCE_MIN if dominance is None else dominance
    min_support = config.CLUSTER_MIN_SUPPORT if min_support is None else min_support

    keys = [k for k in keys if k in std.columns]
    if use_payer and "payer" in std.columns and std["payer"].notna().any() and "payer" not in keys:
        keys = keys + ["payer"]
    if not keys:
        return pd.DataFrame(columns=cols)

    roll = _roll_map(crosswalk)
    df = std.copy()
    df["_bn"] = df["billing_npi"].astype("string")
    df["_ckey"] = _cluster_key(df, keys)

    pop = df[(~df["is_blank_billing"].fillna(False)) & df["_bn"].notna() & df["_ckey"].notna()].copy()
    if pop.empty:
        return pd.DataFrame(columns=cols)
    pop["_parent"] = pop["_bn"].map(lambda n: roll.get(str(n), str(n)))

    # dominant operator per cluster (rolled), with the modal NPI as the fill value
    dom = {}
    for ckey, g in pop.groupby("_ckey"):
        n = len(g)
        if n < min_support:
            continue
        pc = g["_parent"].value_counts()
        share = pc.iloc[0] / n
        if share < dominance:
            continue
        top_parent = pc.index[0]
        modal_npi = g.loc[g["_parent"] == top_parent, "_bn"].value_counts().index[0]
        dom[ckey] = (str(modal_npi), float(round(share, 3)), int(n))
    if not dom:
        return pd.DataFrame(columns=cols)

    elig = df[df.index.isin(eligible_index) & df["is_blank_billing"].fillna(False) & df["_ckey"].notna()]
    rows = {}
    for idx, ck in elig["_ckey"].items():
        hit = dom.get(ck)
        if hit:
            rows[idx] = hit
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame.from_dict(rows, orient="index", columns=cols)
