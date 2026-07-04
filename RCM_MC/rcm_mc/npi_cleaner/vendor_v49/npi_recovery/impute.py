"""Step 4: referral-anchored imputation with hierarchical backoff.

Train on the rows that already have a billing NPI: learn, at successively
coarser keys, which billing NPI tends to follow a (referring NPI, drug, site,
ZIP3). For a blank row, walk tiers strongest->weakest and stop at the first
tier with support. The matched tier is the confidence signal; we also keep
top-3 and a numeric score. The weakest tier draws on the CMS candidate pool so
codes with no in-panel history still get a plausible (clearly-labelled) guess."""

import numpy as np
import pandas as pd

from . import config

TIER_RANK = {t["name"]: i for i, t in enumerate(config.IMPUTE_TIERS)}
_POINT_MAX = TIER_RANK[config.POINT_ATTRIBUTION_MAX_TIER]


class ReferralImputer:
    def __init__(self, min_support=1):
        self.min_support = min_support
        self.tables = {}          # tier_name -> {key: {"w": {npi: $}, "n": {npi: count}}}
        self.pools = {}           # (hcpcs, state) -> pool DataFrame (CMS)
        self.in_panel_tiers = [t for t in config.IMPUTE_TIERS if t["source"] == "in_panel"]

    def fit(self, train, pools=None, weight_col=None):
        self.pools = pools or {}
        train = train[train["billing_npi"].notna()].copy()
        # weight candidate billers by allowed dollars (config default) so a few
        # high-dollar claims drive attribution, not a pile of cheap rows.
        if weight_col is None:
            weight_col = getattr(config, "ATTRIBUTION_WEIGHT_COL", None)
        self.weight_col = weight_col if (weight_col and weight_col in train.columns) else None
        for t in self.in_panel_tiers:
            self.tables[t["name"]] = _build_table(train, t["keys"], self.weight_col)
        return self

    def _row_key(self, row, keys):
        vals = []
        for k in keys:
            v = row.get(k)
            if pd.isna(v) or v == "":
                return None
            vals.append(str(v))
        return tuple(vals)

    def predict_row(self, row):
        # in-panel tiers
        for t in self.in_panel_tiers:
            key = self._row_key(row, t["keys"])
            if key is None:
                continue
            entry = self.tables.get(t["name"], {}).get(key)
            if not entry:
                continue
            w, nobs = entry["w"], entry["n"]
            total_w = sum(w.values())
            total_n = sum(nobs.values())
            if total_n < self.min_support or total_w <= 0:
                continue
            ranked = sorted(w.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
            top1, w1 = ranked[0]
            share1 = w1 / total_w
            share2 = (ranked[1][1] / total_w) if len(ranked) > 1 else 0.0
            margin = share1 - share2
            n_top1 = int(nobs.get(top1, 0))
            return _result(top1, [n for n, _ in ranked], t, share1, total_n,
                           margin=margin, n_top1=n_top1)
        # CMS-pool tier
        hcpcs = str(row.get("hcpcs")) if not pd.isna(row.get("hcpcs")) else None
        state = str(row.get("state")) if not pd.isna(row.get("state")) else None
        pool = self.pools.get((hcpcs, state))
        tcms = config.IMPUTE_TIERS[-1]
        if pool is not None and not pool.empty:
            ranked = pool.head(3)
            tot = float(pool["srvcs"].sum()) or 1.0
            share = float(ranked.iloc[0]["srvcs"]) / tot
            share2 = float(ranked.iloc[1]["srvcs"]) / tot if len(ranked) > 1 else 0.0
            return _result(str(ranked.iloc[0]["npi"]), [str(x) for x in ranked["npi"].tolist()],
                           tcms, share, int(round(tot)),
                           name=str(ranked.iloc[0]["name"]), margin=share - share2)
        return _result(None, [], None, 0.0, 0)

    def predict(self, rows):
        recs = [self.predict_row(r) for _, r in rows.iterrows()]
        out = pd.DataFrame(recs, index=rows.index)
        return out


def _build_table(train, keys, weight_col=None):
    cols = keys + ["billing_npi"]
    t = train.dropna(subset=cols).copy()
    if t.empty:
        return {}
    if weight_col and weight_col in t.columns:
        w = pd.to_numeric(t[weight_col], errors="coerce").fillna(0.0).to_numpy()
        # zero / negative / missing dollars still count as one observation, so a
        # reversal or an un-priced row never erases a biller from the key.
        t["_w"] = np.where(w <= 0, 1.0, w)
    else:
        t["_w"] = 1.0
    t["_n"] = 1
    agg = (t.groupby(keys + ["billing_npi"], sort=False)
             .agg(_w=("_w", "sum"), _n=("_n", "sum")).reset_index())
    tables = {}
    grp_keys = keys[0] if len(keys) == 1 else keys
    for k, sub in agg.groupby(grp_keys, sort=False):
        kk = (str(k),) if len(keys) == 1 else tuple(str(x) for x in (k if isinstance(k, tuple) else (k,)))
        bn = sub["billing_npi"].astype(str)
        # per key: dollar-weight and observation-count for each billing NPI
        tables[kk] = {"w": dict(zip(bn, sub["_w"])), "n": dict(zip(bn, sub["_n"]))}
    return tables


def _result(top1, top3, tier, score, support, name=None, margin=None, n_top1=None):
    if tier is None:
        return {"recovered_npi": None, "recovered_top3": "", "tier": "none",
                "tier_source": "none", "confidence": 0.0, "support": 0,
                "attribution": "unrecovered", "recovered_name": name or "",
                "margin": pd.NA, "demoted_near_tie": False, "demote_reason": ""}
    conf = round(float(tier["weight"]) * float(score), 4)
    attribution = "point" if TIER_RANK[tier["name"]] <= _POINT_MAX else "distributional"
    # A point tier only stays point if the winning biller clears every evidence
    # gate: wins by a real dollar margin, owns a majority of the dollar mass, AND
    # rests on enough training observations for the tier. Any failure demotes it
    # to a best-guess (surfaced in _NPI_BestGuess, never the billing column).
    demoted, reasons = False, []
    if attribution == "point":
        if not ((margin is None) or (float(margin) >= config.POINT_MARGIN_MIN)):
            reasons.append("near_tie_margin")
        if not (float(score) >= config.POINT_PURITY_MIN):
            reasons.append("low_purity")
        min_obs = config.POINT_MIN_OBS.get(tier["name"], 1)
        if not ((n_top1 is None) or (int(n_top1) >= int(min_obs))):
            reasons.append(f"low_support(n={n_top1}<{min_obs})")
        if reasons:
            attribution = "distributional"
            demoted = True
    return {
        "recovered_npi": top1,
        "recovered_top3": ";".join(top3),
        "tier": tier["name"],
        "tier_source": tier["source"],
        "confidence": conf,
        "support": int(support),
        "attribution": attribution,
        "recovered_name": name or "",
        "margin": round(float(margin), 4) if margin is not None else pd.NA,
        "demoted_near_tie": demoted,
        "demote_reason": ";".join(reasons),
    }
