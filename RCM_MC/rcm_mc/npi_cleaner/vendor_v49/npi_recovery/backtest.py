"""Step 6: k-fold masking back-test.

Hide the billing NPI on held-out rows that have one, re-impute from the rest, and
score dollar-weighted top-1 / top-3 accuracy by confidence tier. v9 uses k folds
instead of a single split, so EVERY known row is tested exactly once (a more
stable estimate that uses all the data) and we also get the fold-to-fold spread
of each tier's accuracy -- which calibration uses so a lucky or unlucky single
split can't demote a good tier or keep a bad one.

Then blend those per-tier accuracies onto the tier mix of the *real* blanks ->
the honest expected accuracy on the rows we actually have to fill.
"""

import numpy as np
import pandas as pd

from .impute import ReferralImputer


def _empty_result(known_n, status="insufficient_training"):
    return {
        "n_known": known_n, "status": status, "per_tier": pd.DataFrame(),
        "blanks_mix": pd.DataFrame(), "holdout_top1": np.nan, "holdout_top3": np.nan,
        "honest_top1": np.nan, "honest_top3": np.nan, "honest_top1_validated_only": np.nan,
        "honest_top3_validated_only": np.nan, "validated_dollar_share": np.nan, "n_folds_used": 0,
    }


def run_backtest(std, pools, blanks_pred, holdout_frac=0.2, seed=7, min_support=1, n_folds=5):
    known = std[std["billing_npi"].notna()].copy()
    result = {"n_known": len(known)}
    if len(known) < 50:
        return _empty_result(len(known))

    known = known.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    fold_id = rng.integers(0, n_folds, size=len(known))

    frames = []
    for f in range(n_folds):
        test = known[fold_id == f]
        train = known[fold_id != f]
        if len(test) == 0 or len(train) < 20:
            continue
        imp = ReferralImputer(min_support=min_support).fit(train, pools=pools)
        pred = imp.predict(test).reset_index(drop=True)
        t = test.reset_index(drop=True)
        truth = t["billing_npi"].astype(str)
        amt = t["allowed_amt"].fillna(0).clip(lower=0).to_numpy()
        if amt.sum() == 0:
            amt = np.ones(len(t))
        top1 = (pred["recovered_npi"].astype("string").fillna("") == truth).to_numpy()
        top3 = np.array([str(tr) in str(s).split(";") if s else False
                         for tr, s in zip(truth, pred["recovered_top3"])])
        frames.append(pd.DataFrame({"tier": pred["tier"].values, "amt": amt,
                                    "t1": top1, "t3": top3, "fold": f,
                                    "hcpcs": t["hcpcs"].astype(str).values
                                    if "hcpcs" in t.columns else "",
                                    "true_npi": truth.values,
                                    "pred_npi": pred["recovered_npi"].astype("string").fillna("").values,
                                    "pred_top3": pred["recovered_top3"].astype("string").fillna("").values,
                                    "confidence": pd.to_numeric(pred.get("confidence"), errors="coerce").fillna(0.0).values,
                                    "tier_source": pred.get("tier_source", pd.Series([""] * len(pred))).values,
                                    "margin": pd.to_numeric(pred.get("margin"), errors="coerce").values,
                                    "support": pd.to_numeric(pred.get("support"), errors="coerce").fillna(0).values}))

    if not frames:
        return _empty_result(len(known), status="insufficient_training")

    allp = pd.concat(frames, ignore_index=True)
    A = float(allp["amt"].sum()) or 1.0
    result["status"] = "ok"
    result["holdout_n"] = int(len(allp))
    result["n_folds_used"] = int(allp["fold"].nunique())
    result["holdout_top1"] = round(float((allp["t1"] * allp["amt"]).sum() / A), 4)
    result["holdout_top3"] = round(float((allp["t3"] * allp["amt"]).sum() / A), 4)

    # per-tier accuracy, dollar-weighted across ALL tested rows (every row once)
    allp["_w1"] = allp["t1"] * allp["amt"]
    allp["_w3"] = allp["t3"] * allp["amt"]
    agg = (allp.groupby("tier")
           .agg(rows=("amt", "size"), dollars=("amt", "sum"),
                w1=("_w1", "sum"), w3=("_w3", "sum")).reset_index())
    agg["top1_acc"] = (agg["w1"] / agg["dollars"]).round(4)
    agg["top3_acc"] = (agg["w3"] / agg["dollars"]).round(4)

    # fold-to-fold spread of each tier's top-1 accuracy
    ft = (allp.groupby(["fold", "tier"])
          .agg(w1=("_w1", "sum"), amt=("amt", "sum")).reset_index())
    ft["acc"] = ft["w1"] / ft["amt"]
    tier_std = ft.groupby("tier")["acc"].std(ddof=0).fillna(0.0).to_dict()
    agg["top1_std"] = agg["tier"].map(lambda t: round(float(tier_std.get(t, 0.0)), 4))
    per_tier = agg[["tier", "rows", "dollars", "top1_acc", "top3_acc", "top1_std"]]
    result["per_tier"] = per_tier
    # v23: keep per-row holdout detail so a per-operator leaderboard can be built
    # from the SAME held-out rows (no new modeling).
    result["holdout_detail"] = allp[["tier", "amt", "t1", "t3",
                                     "true_npi", "pred_npi", "pred_top3",
                                     "confidence", "tier_source", "margin",
                                     "support"]].copy()

    # tier mix of the REAL blanks (dollar-weighted)
    bp = blanks_pred.copy()
    bp["amt"] = pd.to_numeric(bp.get("blank_allowed", 0), errors="coerce").fillna(0).clip(lower=0)
    if bp["amt"].sum() == 0:
        bp["amt"] = 1.0
    blanks_mix = (bp.groupby("tier")["amt"].sum()
                  .reset_index().rename(columns={"amt": "blank_dollars"}))
    blanks_mix["share"] = blanks_mix["blank_dollars"] / blanks_mix["blank_dollars"].sum()
    result["blanks_mix"] = blanks_mix

    # blend: per-tier measured accuracy x blanks tier share
    acc1 = dict(zip(per_tier["tier"], per_tier["top1_acc"]))
    acc3 = dict(zip(per_tier["tier"], per_tier["top3_acc"]))
    honest1 = honest3 = validated_share = 0.0
    for _, r in blanks_mix.iterrows():
        if r["tier"] in acc1:
            honest1 += r["share"] * acc1[r["tier"]]
            honest3 += r["share"] * acc3[r["tier"]]
            validated_share += r["share"]
    result["honest_top1"] = round(honest1, 4)
    result["honest_top3"] = round(honest3, 4)
    result["validated_dollar_share"] = round(validated_share, 4)
    result["honest_top1_validated_only"] = round(honest1 / validated_share, 4) if validated_share else np.nan
    result["honest_top3_validated_only"] = round(honest3 / validated_share, 4) if validated_share else np.nan

    # --- v17: honesty by DRUG -------------------------------------------------
    # The blanks are not a random sample — they skew toward drugs the non-blank
    # rows barely contain (pharmacy-benefit, military/VA, home IVIG). A tier can
    # be accurate on provider-administered IV and useless on those. So we measure
    # per-drug holdout accuracy, reweight by the blanks' DRUG mix, and — most
    # importantly — report the share of blank dollars sitting in drugs we have too
    # little holdout to validate at all. That last number is the honest "we don't
    # actually know how good recovery is here" figure.
    MIN_DRUG_DOLLARS = 250.0   # minimum held-out dollars to call a drug "measured"
    try:
        if "hcpcs" in allp.columns and allp["hcpcs"].astype(str).str.len().gt(0).any():
            dg = (allp.assign(_w1=allp["t1"] * allp["amt"], _w3=allp["t3"] * allp["amt"])
                  .groupby("hcpcs")
                  .agg(hold_dollars=("amt", "sum"), w1=("_w1", "sum"), w3=("_w3", "sum")).reset_index())
            dg["d_top1"] = dg["w1"] / dg["hold_dollars"]
            dg["d_top3"] = dg["w3"] / dg["hold_dollars"]
            measured = dg[dg["hold_dollars"] >= MIN_DRUG_DOLLARS]
            acc1d = dict(zip(measured["hcpcs"], measured["d_top1"]))
            acc3d = dict(zip(measured["hcpcs"], measured["d_top3"]))

            bd = bp.copy()
            if "hcpcs" in bd.columns:
                bd["hcpcs"] = bd["hcpcs"].astype(str)
                blank_by_drug = bd.groupby("hcpcs")["amt"].sum()
                total_blank = float(blank_by_drug.sum()) or 1.0
                h1 = h3 = meas_share = 0.0
                unmeasured = 0.0
                for code, dollars in blank_by_drug.items():
                    share = dollars / total_blank
                    if code in acc1d:
                        h1 += share * acc1d[code]
                        h3 += share * acc3d[code]
                        meas_share += share
                    else:
                        unmeasured += share
                result["drug_honest_top1"] = round(h1 / meas_share, 4) if meas_share else np.nan
                result["drug_honest_top3"] = round(h3 / meas_share, 4) if meas_share else np.nan
                result["blank_validated_drug_share"] = round(meas_share, 4)
                result["blank_unvalidated_drug_share"] = round(unmeasured, 4)
                # the actual drugs we could not validate, by blank dollars (for the report)
                un = blank_by_drug[[c not in acc1d for c in blank_by_drug.index]].sort_values(ascending=False)
                result["unvalidated_drugs"] = (un.reset_index()
                                               .rename(columns={"hcpcs": "drug", "amt": "blank_dollars"}))
    except Exception:
        pass
    return result


# --------------------------------------------------------------------------- #
# v23: operator-stratified leaderboard. Pure measurement on the SAME holdout
# rows, aggregated by the true biller's parent operator. No model change.
# --------------------------------------------------------------------------- #
def _wilson_lcb(k, n, z=1.96):
    """Wilson 95% lower bound of a proportion k/n. Small samples sink on their own."""
    if n <= 0:
        return 0.0
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2 * n)
    margin = z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5)
    return max(0.0, (centre - margin) / denom)


_LB_COLS = ["parent_operator", "npi_count", "holdout_claims", "holdout_dollars",
            "recall_top1", "recall_top3", "recall_top1_dollar", "precision_top1",
            "precision_lcb", "dominant_tier", "mean_pred_conf", "calibration_gap",
            "blanks_attributed", "blanks_dollars", "verdict"]


def operator_leaderboard(holdout_detail, per_tier, parent_map, parent_size=None,
                         filled=None, mapping=None, min_holdout=30):
    """One row per parent operator with a holdout footprint (plus blank-only
    operators flagged UNMEASURABLE), ranked by the Wilson LB of precision.

    recall is grouped by the TRUE operator (how findable it is); precision is
    grouped by the PREDICTED operator (how trustworthy the label is). Both are
    reported per operator. Nothing here changes the model — it re-aggregates the
    existing held-out predictions.
    """
    if holdout_detail is None or len(holdout_detail) == 0:
        return pd.DataFrame(columns=_LB_COLS)
    pm = {str(k): v for k, v in (parent_map or {}).items()}
    psize = {k: int(v) for k, v in (parent_size or {}).items()}
    _BAD = {"", "nan", "none", "n/a"}

    def _op(npi):
        s = str(npi).strip()
        if s.lower() in _BAD:
            return "(none)"
        return pm.get(s, s)

    d = holdout_detail.copy()
    d["true_npi"] = d["true_npi"].astype(str)
    d["pred_npi"] = d["pred_npi"].astype(str)
    d["true_op"] = d["true_npi"].map(_op)
    d["pred_op"] = d["pred_npi"].map(_op)
    d["hit"] = (d["true_op"] == d["pred_op"]) & (d["pred_npi"].str.len() > 0) & (d["pred_op"] != "(none)")
    d["hit3"] = [t in {_op(x) for x in str(s).split(";") if x} for t, s in zip(d["true_op"], d["pred_top3"])]
    tier_acc = (dict(zip(per_tier["tier"], per_tier["top1_acc"]))
                if per_tier is not None and not per_tier.empty else {})
    d["pred_conf"] = d["tier"].map(lambda t: float(tier_acc.get(t, float("nan"))))

    # blank attributions (predicted operator) read straight off the filled frame
    blanks_n, blanks_d = {}, {}
    if (filled is not None and len(filled)
            and "_Billing_Parent_Group" in filled.columns and "_NPI_Source" in filled.columns):
        src = filled["_NPI_Source"].astype("string").str.lower().fillna("")
        recov = src.str.startswith(("recovered", "inferred", "best-guess", "statistical"))
        amtcol = mapping.get("allowed_amt") if mapping else None
        amt = (pd.to_numeric(filled[amtcol], errors="coerce").fillna(0.0)
               if (amtcol and amtcol in filled.columns) else pd.Series(0.0, index=filled.index))
        grp = filled.loc[recov, "_Billing_Parent_Group"].astype(str)
        blanks_n = grp.value_counts().to_dict()
        blanks_d = amt[recov].groupby(grp).sum().to_dict()

    true_groups = d.groupby("true_op")
    pred_groups = d.groupby("pred_op")
    operators = (set(d["true_op"].unique()) | set(blanks_n.keys())) - {"(none)"}

    def _r(x, nd=4):
        return round(float(x), nd) if x == x else ""

    rows = []
    for op in operators:
        tg = true_groups.get_group(op) if op in true_groups.groups else d.iloc[0:0]
        n_true = int(len(tg))
        dollars_true = float(tg["amt"].sum()) if n_true else 0.0
        if n_true:
            recall_top1 = float(tg["hit"].mean())
            recall_top3 = float(tg["hit3"].mean())
            wsum = float(tg["amt"].sum()) or 1.0
            recall_top1_d = float((tg["hit"] * tg["amt"]).sum() / wsum)
            dom_tier = tg["tier"].mode().iloc[0] if not tg["tier"].mode().empty else ""
        else:
            recall_top1 = recall_top3 = recall_top1_d = float("nan")
            dom_tier = ""
        pg = pred_groups.get_group(op) if op in pred_groups.groups else d.iloc[0:0]
        m_pred = int(len(pg))
        if m_pred:
            k = int(pg["hit"].sum())
            precision_top1 = k / m_pred
            precision_lcb = _wilson_lcb(k, m_pred)
            mean_conf = float(pg["pred_conf"].mean())
        else:
            precision_top1 = precision_lcb = mean_conf = float("nan")
        calib = (precision_top1 - mean_conf) if (precision_top1 == precision_top1 and mean_conf == mean_conf) else float("nan")
        b_n = int(blanks_n.get(op, 0))
        b_d = float(blanks_d.get(op, 0.0))

        if n_true == 0 and b_n > 0:
            verdict = "UNMEASURABLE"
        elif n_true < min_holdout:
            verdict = "INSUFFICIENT_HOLDOUT"
        elif precision_lcb == precision_lcb and precision_lcb >= 0.85:
            verdict = "HIGH_CONFIDENCE_RECOVERABLE"
        elif precision_lcb == precision_lcb and precision_lcb >= 0.60:
            verdict = "MODERATE"
        else:
            verdict = "LOW_CONFIDENCE"

        rows.append({
            "parent_operator": op,
            "npi_count": int(psize.get(op, 0)) or "",
            "holdout_claims": n_true,
            "holdout_dollars": round(dollars_true, 0),
            "recall_top1": _r(recall_top1), "recall_top3": _r(recall_top3),
            "recall_top1_dollar": _r(recall_top1_d), "precision_top1": _r(precision_top1),
            "precision_lcb": _r(precision_lcb), "dominant_tier": dom_tier,
            "mean_pred_conf": _r(mean_conf), "calibration_gap": _r(calib),
            "blanks_attributed": b_n, "blanks_dollars": round(b_d, 0),
            "verdict": verdict,
        })

    out = pd.DataFrame(rows, columns=_LB_COLS)
    if out.empty:
        return out
    # ranked operators (>=30 holdout) by precision_lcb first; flagged ones after
    rank_order = {"HIGH_CONFIDENCE_RECOVERABLE": 0, "MODERATE": 0, "LOW_CONFIDENCE": 0,
                  "INSUFFICIENT_HOLDOUT": 1, "UNMEASURABLE": 2}
    out["_o"] = out["verdict"].map(lambda v: rank_order.get(v, 3))
    out["_p"] = pd.to_numeric(out["precision_lcb"], errors="coerce").fillna(-1.0)
    out = out.sort_values(["_o", "_p"], ascending=[True, False]).drop(columns=["_o", "_p"]).reset_index(drop=True)
    return out
