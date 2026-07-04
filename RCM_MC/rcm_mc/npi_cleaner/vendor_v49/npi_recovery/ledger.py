"""
ledger.py  (v44)
================

One auditable record per recovered or repaired value. The toolkit already knows,
per value, how it was produced, how confident it is, and what it rests on; those
facts have lived in separate frames (recovery, repairs_log, agreement, the
calibrated model, the reference manifest). The ledger pulls them into a single
row-level table so a reviewer can answer, for any changed cell, four questions
without leaving the sheet:

  what changed        field, original value, new value, change type
  by what method      the recovery tier or repair rule that produced it
  how sure            the incumbent confidence, the calibrated probability when
                      available, and the two-method agreement class
  on what basis       the reference sources and their vintages, and one flag:
                      is this safe to carry into a diligence base case

The last column is the point. A recovered NPI that rests on two-method agreement
with a high calibrated probability is base-case safe; a single-method recovery
with a two-method disagreement is a lead, not a fact, and the ledger says so in
one place instead of making the reader assemble it.

Deterministic. Adds no new inference; it is a join and a rule.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


# a recovery is base-case safe when it is a point attribution that was not
# demoted, is not a two-method disagreement, and clears a calibrated-probability
# floor when a calibrated probability is available.
_BASECASE_PROB_FLOOR = 0.75


def _safe_for_basecase(attribution, demoted, agreement, calib_prob):
    if str(attribution) != "point":
        return False
    if bool(demoted):
        return False
    if str(agreement) == "disagree":
        return False
    if calib_prob is not None and not (isinstance(calib_prob, float) and np.isnan(calib_prob)):
        return float(calib_prob) >= _BASECASE_PROB_FLOOR
    return True


def build_ledger(recovery: pd.DataFrame, repairs_log: pd.DataFrame = None,
                 agreement_tbl: pd.DataFrame = None, calib_probs=None,
                 vintages: dict = None, mapping=None) -> pd.DataFrame:
    """Assemble the evidence ledger.

    recovery       the per-blank recovery frame (recovered_npi, tier, confidence,
                   attribution, margin, demote_reason, orig_row, blank_allowed...)
    repairs_log    field-repair summary (repair, field, rows_fixed, method)
    agreement_tbl  two-method agreement table keyed by 'row' (agreement, boost)
    calib_probs    optional Series/array of calibrated probabilities aligned to
                   the recovery frame's index
    vintages       {source_name: vintage_string} for the basis column
    """
    vintages = vintages or {}
    rows = []

    # ---- recovered billing NPIs ----
    if recovery is not None and not recovery.empty:
        rec = recovery.reset_index(drop=True).copy()
        agree_map = {}
        if agreement_tbl is not None and not agreement_tbl.empty:
            agree_map = dict(zip(agreement_tbl["row"], agreement_tbl["agreement"]))
        cp = None
        if calib_probs is not None:
            cp = np.asarray(calib_probs, dtype=float)
        src = ("in-file co-occurrence pattern" )
        for i, r in rec.iterrows():
            npi = r.get("recovered_npi")
            if npi is None or (isinstance(npi, float) and np.isnan(npi)) or str(npi) in ("", "nan", "<NA>"):
                change_type = "unrecovered"
            else:
                change_type = "recovered_billing_npi"
            orig_row = r.get("orig_row")
            agreement = agree_map.get(orig_row, agree_map.get(i, ""))
            calib = float(cp[i]) if (cp is not None and i < len(cp)) else None
            tier_source = str(r.get("tier_source", ""))
            basis_src = ("CMS Medicare utilization pool"
                         if tier_source == "cms_pool" else "in-file co-occurrence pattern")
            safe = _safe_for_basecase(r.get("attribution"), r.get("demoted_near_tie"),
                                      agreement, calib)
            rows.append({
                "orig_row": orig_row,
                "field": "billing_npi",
                "original_value": "(blank)",
                "new_value": "" if change_type == "unrecovered" else str(npi),
                "change_type": change_type,
                "method": str(r.get("tier", "")),
                "method_source": basis_src,
                "incumbent_confidence": r.get("confidence"),
                "calibrated_probability": (round(calib, 4) if calib is not None else pd.NA),
                "two_method_agreement": agreement or "not_run",
                "attribution": r.get("attribution"),
                "demoted": bool(r.get("demoted_near_tie", False)),
                "demote_reason": r.get("demote_reason", ""),
                "dollars": pd.to_numeric(pd.Series([r.get("blank_allowed", 0)]),
                                         errors="coerce").fillna(0).iloc[0],
                "reference_basis": basis_src,
                "reference_vintage": vintages.get("cms_utilization", "") if tier_source == "cms_pool"
                                     else "in-file",
                "safe_for_basecase": safe,
            })

    # ---- field repairs (deterministic cleaning) ----
    if repairs_log is not None and not repairs_log.empty:
        for _, r in repairs_log.iterrows():
            rows.append({
                "orig_row": pd.NA,
                "field": r.get("field", ""),
                "original_value": "(various)",
                "new_value": f"{int(r.get('rows_fixed', 0))} rows repaired",
                "change_type": "field_repair",
                "method": r.get("repair", ""),
                "method_source": r.get("method", ""),
                "incumbent_confidence": 1.0,   # deterministic repair
                "calibrated_probability": pd.NA,
                "two_method_agreement": "n/a",
                "attribution": "deterministic",
                "demoted": False,
                "demote_reason": "",
                "dollars": pd.NA,
                "reference_basis": r.get("method", ""),
                "reference_vintage": "deterministic",
                "safe_for_basecase": True,     # deterministic repairs are safe
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    # headline note
    recs = out[out["change_type"] == "recovered_billing_npi"]
    if not recs.empty:
        d = pd.to_numeric(recs["dollars"], errors="coerce").fillna(0)
        safe_d = float(d[recs["safe_for_basecase"]].sum())
        tot_d = float(d.sum()) or 1.0
        out.attrs["note"] = (
            f"{len(recs)} recovered billing NPIs; {round(100.0*safe_d/tot_d,1)}% of "
            f"recovered dollars are base-case safe (point attribution, not demoted, "
            f"not a two-method disagreement, clears the calibrated-probability floor "
            f"when available). The rest are leads to verify. Every field-repair row is "
            f"deterministic and base-case safe.")
    return out


def basecase_rollup(ledger: pd.DataFrame) -> pd.DataFrame:
    """Small summary: recovered dollars split into base-case safe vs leads, the
    number a diligence reader wants at the top of the ledger."""
    if ledger is None or ledger.empty:
        return pd.DataFrame(columns=["bucket", "rows", "dollars", "pct_dollars"])
    recs = ledger[ledger["change_type"] == "recovered_billing_npi"].copy()
    if recs.empty:
        return pd.DataFrame(columns=["bucket", "rows", "dollars", "pct_dollars"])
    recs["dollars"] = pd.to_numeric(recs["dollars"], errors="coerce").fillna(0)
    recs["bucket"] = np.where(recs["safe_for_basecase"], "base_case_safe", "lead_verify")
    g = (recs.groupby("bucket")
         .agg(rows=("field", "size"), dollars=("dollars", "sum")).reset_index())
    tot = float(g["dollars"].sum()) or 1.0
    g["pct_dollars"] = (100.0 * g["dollars"] / tot).round(1)
    return g.sort_values("dollars", ascending=False).reset_index(drop=True)
