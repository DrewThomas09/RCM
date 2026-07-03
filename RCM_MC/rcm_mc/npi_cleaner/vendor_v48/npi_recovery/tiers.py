"""v23: three certainty-tiered deliverables + a genuine fill report.

The three outputs, each a strict superset of the one above it, with certainty
DECREASING as more cells are populated:

  1. Closed_Claims        — observed values + direct authoritative lookups only
                            (NPPES / CMS facts). Zero inference. Everything is true.
  2. Recovered_Claims     — + measured recovery: billing NPIs point-attributed by the
                            referral-anchored imputer at a k-fold-MEASURED hit-rate
                            (~89% on the held-out test). High-confidence, still inferred.
  3. Statistically_Filled — + the distributional best-guess written INTO the cells, so the
                            MAJORITY of missing cells carry a value. Every estimated cell is
                            flagged _Review_Required='Y' and scored. REQUIRES REVIEW.

Plus, for the analysis report:
  * cell_census()        — per field: certain / recovered / estimated / unfillable counts,
                           the literal answer to "how many were filled vs estimated vs missing";
  * statistical_method() — a truthful explanation of how the estimation works;
  * pivot_landscape()    — does writing the estimates distort the operator market-share
                           picture? Compares concentration (HHI, top-operator share) between
                           the Recovered and Statistically-Filled tiers and renders a verdict.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .fill import TOK, NAP, _is_blank

_ESTIMATE_PENDING = "ESTIMATE_PENDING_REVIEW"
# a cell counts as a real, usable value only if it is none of these
_NONVALUE = set(TOK.values()) | {NAP, _ESTIMATE_PENDING}


def _is_real(series):
    """True where the cell holds a usable value (not blank, not a token, not pending)."""
    s = series.astype("string").str.strip()
    blank = _is_blank(series)
    token = s.isin(_NONVALUE)
    return ~(blank | token)


def _first_candidate(bestguess_cell):
    """Top-ranked NPI from a '111; 222; 333' best-guess string."""
    if bestguess_cell is None:
        return ""
    s = str(bestguess_cell).strip()
    if not s or s == NAP:
        return ""
    return s.split(";")[0].strip()


# --------------------------------------------------------------------------- #
# Tier 3: write the distributional best-guess into the cells (with review flags)
# --------------------------------------------------------------------------- #
def escalate_to_statistical_full(recovered, provider_directory, mapping):
    """Take the Recovered (statistical) frame and fill the residual billing cells
    with the #1 distributional candidate, deriving identity off it from the
    already-fetched provider directory. Nothing new is queried. Every written
    estimate is marked _Review_Required='Y' and keeps its measured _NPI_Confidence.
    Returns a NEW frame; the input is not mutated.
    """
    df = recovered.copy()
    n = len(df)
    df["_Review_Required"] = pd.Series([""] * n, index=df.index, dtype="object")
    if not n:
        return df

    bill_col = mapping.get("billing_npi")
    final_col = "Billing_NPI_Final" if "Billing_NPI_Final" in df.columns else None
    bg_col = "_NPI_BestGuess" if "_NPI_BestGuess" in df.columns else None
    if not bill_col or bill_col not in df.columns or not bg_col:
        return df

    # rows whose billing NPI is a below-bar best-guess token AND have candidates
    is_token = df[bill_col].astype("string").str.strip().eq(TOK["bestguess"])
    cand = df[bg_col].map(_first_candidate)
    has_cand = cand.str.len().gt(0)
    target = is_token & has_cand
    if not target.any():
        return df

    # directory lookup: NPI -> identity (already fetched during enrichment)
    dir_name, dir_ent, dir_spec = {}, {}, {}
    if provider_directory is not None and not provider_directory.empty and "NPI" in provider_directory.columns:
        pdir = provider_directory.astype({"NPI": "string"})
        for _, rr in pdir.iterrows():
            k = str(rr.get("NPI", "")).strip()
            if k:
                dir_name[k] = rr.get("Provider_Name", "") or ""
                dir_ent[k] = rr.get("Entity_Type", "") or ""
                dir_spec[k] = rr.get("Primary_Specialty", "") or ""

    cand_t = cand.where(target, other="")
    # write the estimate into the billing column(s)
    df.loc[target, bill_col] = cand_t[target].values
    if final_col:
        df.loc[target, final_col] = cand_t[target].values
    if "_NPI_Source" in df.columns:
        df.loc[target, "_NPI_Source"] = "statistical_estimate"
    df.loc[target, "_Review_Required"] = "Y"

    # derive identity off the estimated NPI from the directory; else leave pending
    def _fill_identity(canon, lookup):
        col = mapping.get(canon)
        if not col or col not in df.columns:
            return
        cur_token = df[col].astype("string").str.strip().isin(_NONVALUE)
        rows = target & cur_token
        if not rows.any():
            return
        vals = cand_t[rows].map(lambda k: lookup.get(k, "")).fillna("")
        vals = vals.where(vals.str.len() > 0, other=_ESTIMATE_PENDING)
        df.loc[rows, col] = vals.values

    _fill_identity("billing_name", dir_name)
    _fill_identity("entity_type", dir_ent)
    _fill_identity("billing_specialty", dir_spec)
    return df


# --------------------------------------------------------------------------- #
# The genuine fill report: per-field census across the three tiers
# --------------------------------------------------------------------------- #
def cell_census(closed, recovered, statistical, mapping):
    """Per fillable field, classify every cell by the HIGHEST-certainty tier that
    populates it: certain (in Closed) / recovered (added in Recovered) / estimated
    (added in Statistically-Filled) / unfillable (token in all three). Frames are
    row-aligned (same dedup), so this is an exact cell-wise accounting.
    """
    canon_fields = [
        ("billing_npi", "Billing NPI"),
        ("billing_name", "Billing name"),
        ("entity_type", "Entity type"),
        ("billing_specialty", "Billing specialty"),
        ("billing_affiliation", "Billing affiliation"),
        ("referring_npi", "Referring NPI"),
        ("referring_name", "Referring name"),
        ("referring_specialty", "Referring specialty"),
        ("referring_affiliation", "Referring affiliation"),
        ("payer", "Payer name"),
    ]
    rows = []
    tot_cells = tot_cert = tot_rec = tot_est = tot_un = 0
    for canon, label in canon_fields:
        col = mapping.get(canon)
        if not col or col not in closed.columns:
            continue
        n = len(closed)
        cert = _is_real(closed[col]).to_numpy()
        rec = _is_real(recovered[col]).to_numpy() if col in recovered.columns else np.zeros(n, bool)
        sta = _is_real(statistical[col]).to_numpy() if col in statistical.columns else np.zeros(n, bool)
        c_cert = int(cert.sum())
        c_rec = int((rec & ~cert).sum())
        c_est = int((sta & ~rec & ~cert).sum())
        c_un = int(n - c_cert - c_rec - c_est)
        rows.append({
            "field": label,
            "certain_closed": c_cert,
            "recovered_api": c_rec,
            "estimated_review": c_est,
            "still_unfillable": c_un,
            "pct_populated": round(100.0 * (c_cert + c_rec + c_est) / n, 1) if n else 0.0,
        })
        tot_cells += n; tot_cert += c_cert; tot_rec += c_rec; tot_est += c_est; tot_un += c_un
    if rows:
        rows.append({
            "field": "— ALL FIELDS —",
            "certain_closed": tot_cert, "recovered_api": tot_rec,
            "estimated_review": tot_est, "still_unfillable": tot_un,
            "pct_populated": round(100.0 * (tot_cert + tot_rec + tot_est) / tot_cells, 1) if tot_cells else 0.0,
        })
    df = pd.DataFrame(rows)
    df.attrs["totals"] = {"cells": tot_cells, "certain": tot_cert, "recovered": tot_rec,
                          "estimated": tot_est, "unfillable": tot_un}
    return df


def statistical_method():
    """Truthful explanation of how the statistical estimation works."""
    return pd.DataFrame([
        {"topic": "What gets estimated",
         "explanation": "Only the residual BILLING provider NPI (and the identity fields derived from it). "
         "Payer name and missing referrers are never estimated — no signal exists to estimate them from, so they "
         "stay labeled unrecoverable in all three outputs."},
        {"topic": "The estimator",
         "explanation": "A referral-anchored imputer. For a claim with a known referring provider, drug (HCPCS) and "
         "geography but a blank biller, it ranks the billers that referring providers like this one actually send "
         "this drug to, learned from the non-blank rows in your own panel and from CMS provider files (who bills "
         "each HCPCS, by state)."},
        {"topic": "Tiers (T1–T6)",
         "explanation": "Candidates are graded by evidence strength: T1–T3 are point attribution (a specific biller "
         "implied by the referral/identifier pattern); T4–T5 are weaker in-panel signals; T6 is a CMS pool with no "
         "in-panel confirmation. Recovered_Claims writes ONLY tiers that pass the bar; Statistically_Filled writes "
         "the top remaining candidate for the rest."},
        {"topic": "Measured accuracy, not asserted",
         "explanation": "A masking back-test hides a fraction of the KNOWN billers, re-predicts them, and measures "
         "the dollar-weighted top-1 hit-rate per tier on that held-out set (k-fold). Tiers whose measured accuracy "
         "fell below the configured floor were demoted, not trusted. The number you see in _NPI_Confidence is that "
         "measured rate, carried per row."},
        {"topic": "Confidence on an estimate",
         "explanation": "Each estimated cell keeps the measured hit-rate of the tier it came from in _NPI_Confidence, "
         "and the full ranked candidate list stays in _NPI_BestGuess so a reviewer can see the alternatives. Estimated "
         "cells are flagged _Review_Required='Y'."},
        {"topic": "Why three files",
         "explanation": "So an estimate can never be mistaken for a fact. Use Closed_Claims for what is certain, "
         "Recovered_Claims for the defensible diligence base (certain + measured), and Statistically_Filled only when "
         "you need a fully-populated frame AND will review the flagged cells. The census quantifies each tier."},
    ], columns=["topic", "explanation"])


# --------------------------------------------------------------------------- #
# Landscape pivot: do the estimates distort the operator market-share picture?
# --------------------------------------------------------------------------- #
def _operator_series(df, mapping):
    for cand in ("_Billing_Parent_Group", "Billing_NPI_Final", mapping.get("billing_npi")):
        if cand and cand in df.columns:
            return df[cand].astype("string").str.strip()
    return None


def _amount_series(df, mapping):
    col = mapping.get("allowed_amt")
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return pd.Series(0.0, index=df.index)


def _share_table(op, amt):
    """$ and share by operator, excluding token/unknown operators into one bucket."""
    real = ~op.isin(_NONVALUE) & op.str.len().gt(0)
    g = pd.DataFrame({"op": op.where(real, other="(unattributed)"), "amt": amt})
    by = g.groupby("op")["amt"].sum().sort_values(ascending=False)
    total = float(by.sum()) or 1.0
    share = by / total
    named = share.drop(index="(unattributed)", errors="ignore")
    hhi = float((named ** 2).sum() * 10000)  # HHI over NAMED operators
    unattr = float(share.get("(unattributed)", 0.0))
    return by, share, hhi, unattr


def pivot_landscape(recovered, statistical, mapping, top=12):
    """Compare the operator landscape between the Recovered tier (defensible) and the
    Statistically-Filled tier (with estimates). Returns a top-operator comparison
    table; verdict + concentration metrics ride in .attrs.
    """
    op_r, amt_r = _operator_series(recovered, mapping), _amount_series(recovered, mapping)
    op_s, amt_s = _operator_series(statistical, mapping), _amount_series(statistical, mapping)
    if op_r is None or op_s is None:
        out = pd.DataFrame([{"note": "no operator column available for a landscape pivot"}])
        out.attrs["verdict"] = "Landscape pivot unavailable (no billing-operator column)."
        return out

    by_r, sh_r, hhi_r, un_r = _share_table(op_r, amt_r)
    by_s, sh_s, hhi_s, un_s = _share_table(op_s, amt_s)

    ops = list(by_s.drop(index="(unattributed)", errors="ignore").head(top).index)
    rows = []
    for i, name in enumerate(ops, 1):
        rows.append({
            "rank_in_filled": i,
            "operator": (name[:48] if isinstance(name, str) else name),
            "$_recovered": round(float(by_r.get(name, 0.0)), 0),
            "share_recovered": round(float(sh_r.get(name, 0.0)) * 100, 2),
            "$_statistical": round(float(by_s.get(name, 0.0)), 0),
            "share_statistical": round(float(sh_s.get(name, 0.0)) * 100, 2),
        })
    out = pd.DataFrame(rows)

    top5_r = float(sh_r.drop(index="(unattributed)", errors="ignore").head(5).sum()) * 100
    top5_s = float(sh_s.drop(index="(unattributed)", errors="ignore").head(5).sum()) * 100
    d_hhi = hhi_s - hhi_r
    d_top5 = top5_s - top5_r
    moved = (un_r - un_s) * 100  # share of $ moved from unattributed into named operators

    # verdict: are market-share conclusions robust to the estimates?
    stable = abs(d_hhi) < 150 and abs(d_top5) < 5
    verdict = (
        ("ROBUST. " if stable else "SENSITIVE. ") +
        f"Estimates reassign {moved:.1f}% of dollars from unattributed into named operators. "
        f"Named-operator HHI moves {d_hhi:+.0f} ({hhi_r:.0f} -> {hhi_s:.0f}); top-5 share moves {d_top5:+.1f} pts "
        f"({top5_r:.1f}% -> {top5_s:.1f}%). " +
        ("The concentration picture barely changes, so the operator market-share read holds whether or not you "
         "accept the estimates — they fill detail without reshaping the landscape."
         if stable else
         "The estimates materially shift concentration, so the operator ranking is estimate-dependent: cite it from "
         "Recovered_Claims and treat the Statistically-Filled ranking as a reviewable scenario, not a finding.")
    )
    out.attrs.update({"verdict": verdict, "hhi_recovered": round(hhi_r), "hhi_statistical": round(hhi_s),
                      "top5_recovered": round(top5_r, 1), "top5_statistical": round(top5_s, 1),
                      "dollars_moved_pct": round(moved, 1), "unattributed_recovered_pct": round(un_r * 100, 1),
                      "unattributed_statistical_pct": round(un_s * 100, 1)})
    return out
