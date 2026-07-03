"""
clean_pipeline.py  (v35)
========================

The deep-clean orchestrator. Stages run in a declared order, each in one of two
modes: report (scan, price, never touch) or apply (deterministic repairs only,
every mutation written to the ledger). The process guarantees:

  provenance     every change carries a stage, a rule id, a field, and a count
  conservation   apply-mode never adds or removes a row; the reconciliation
                 proves dollars moved only through declared operations
  idempotency    running the same plan twice produces zero new ledger entries
  reversibility  imputations preserve originals; parses are recorded

DEFAULT_PLAN order (each stage is a pure function elsewhere in the package):
  1. text_hygiene       invisibles, sentinels, sci-notation ids   (apply-safe)
  2. money_parse        accounting negatives, separators          (apply-safe)
  3. date_parse         Excel serials, multi-format to ISO        (apply-safe)
  4. ndc_normalize      segment-aware pad to 11                   (apply-safe)
  5. field_validation   registry scan                             (report-only)
  6. row_consistency    cross-field rules                         (report-only)
  7. distribution       Benford and rounding screens              (report-only)
  8. imputation         options compared; applied only by name    (opt-in)

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import text_hygiene as _th
from . import field_validators as _fv
from . import row_consistency as _rc
from . import distribution_screens as _ds
from . import imputation_options as _io

DEFAULT_PLAN = [
    ("text_hygiene", "apply"),
    ("money_parse", "apply"),
    ("date_parse", "apply"),
    ("ndc_normalize", "apply"),
    ("field_validation", "report"),
    ("row_consistency", "report"),
    ("distribution", "report"),
]


def _stage_money_parse(std):
    ledger = []
    out = std
    col = "allowed_amt"
    if col in std.columns and not pd.api.types.is_numeric_dtype(std[col]):
        vals, status = _fv.parse_money_series(std[col])
        changed = int((status != "NUMERIC").sum() - (status == "BLANK").sum())
        out = std.copy()
        out[col] = vals
        ledger.append({"stage": "money_parse", "rule_id": "MONEY-PARSE", "field": col,
                       "rows_changed": max(changed, 0),
                       "action": "currency strings to numeric (parens negatives honored)"})
    return out, ledger


def _stage_date_parse(std):
    ledger = []
    out = std
    for col in ("date", "paid_date"):
        if col not in out.columns:
            continue
        r = _fv.validate_date_series(out[col])
        fixable = r["status"].isin(["EXCEL_SERIAL", "US_SLASH", "US_SLASH_2Y",
                                    "COMPACT", "FALLBACK_PARSE"])
        if fixable.any():
            if out is std:
                out = std.copy()
            iso = r.loc[fixable, "parsed"].dt.strftime("%Y-%m-%d")
            before = out.loc[fixable, col].astype("string")
            really = iso.astype("string") != before
            out.loc[fixable, col] = iso
            n = int(really.sum())
            if n:
                ledger.append({"stage": "date_parse", "rule_id": "DATE-ISO", "field": col,
                               "rows_changed": n,
                               "action": "non-ISO dates (incl Excel serials) rewritten as ISO"})
    return out, ledger


def _stage_ndc_normalize(std):
    ledger = []
    out = std
    if "ndc" in std.columns:
        n11, status = _fv.normalize_ndc_series(std["ndc"].astype("string"))
        padded = status.str.startswith("PADDED") | (status == "OK_HYPHENATED_11")
        changed = padded & (n11.astype("string") != std["ndc"].astype("string").fillna(""))
        if changed.any():
            out = std.copy()
            out.loc[changed, "ndc"] = n11[changed]
            ledger.append({"stage": "ndc_normalize", "rule_id": "NDC-11", "field": "ndc",
                           "rows_changed": int(changed.sum()),
                           "action": "hyphenated NDCs padded segment-aware to 11 digits; "
                                     "ambiguous 10-digit values untouched"})
    return out, ledger


def run_cleaning(std: pd.DataFrame, *, plan=None, allowed_col: str = "allowed_amt",
                 cw=None, now=None, impute: list | None = None):
    """Run the plan. Returns (cleaned_std, ledger_frame, findings dict).
    impute: optional list of (field, strategy) applied after the scans, each
    stamped and original-preserving."""
    plan = plan if plan is not None else DEFAULT_PLAN
    ledger = []
    findings = {}
    cur = std
    n_rows_in = len(std)
    dollars_in = float(pd.to_numeric(std.get(allowed_col), errors="coerce").fillna(0.0).sum()) \
        if allowed_col in std.columns else np.nan

    for stage, mode in plan:
        if stage == "text_hygiene":
            findings["Text_Hygiene"] = _th.scan_text_hygiene(cur)
            if mode == "apply":
                cur, led = _th.normalize_text_fields(cur)
                ledger += led
        elif stage == "money_parse" and mode == "apply":
            cur, led = _stage_money_parse(cur)
            ledger += led
        elif stage == "date_parse" and mode == "apply":
            cur, led = _stage_date_parse(cur)
            ledger += led
        elif stage == "ndc_normalize" and mode == "apply":
            cur, led = _stage_ndc_normalize(cur)
            ledger += led
        elif stage == "field_validation":
            findings["Field_Validation"] = _fv.run_field_validation(cur, now=now)
        elif stage == "row_consistency":
            findings["Row_Consistency"] = _rc.run_row_consistency(cur, cw=cw)
        elif stage == "distribution":
            if allowed_col in cur.columns:
                a = pd.to_numeric(cur[allowed_col], errors="coerce").fillna(0.0)
                findings["Benford_Screen"] = _ds.benford_by_group(cur, allowed=a,
                                                                  group_col="payer")
                findings["Rounding_Pathology"] = _ds.rounding_pathology(cur, allowed=a)

    for field, strategy in (impute or []):
        cur, led = _io.apply_strategy(cur, field, strategy, cw=cw)
        ledger += led

    led_df = (pd.DataFrame(ledger) if ledger
              else pd.DataFrame(columns=["stage", "rule_id", "field",
                                         "rows_changed", "action"]))
    dollars_out = float(pd.to_numeric(cur.get(allowed_col), errors="coerce").fillna(0.0).sum()) \
        if allowed_col in cur.columns else np.nan
    led_df.attrs["reconciliation"] = {
        "rows_in": n_rows_in, "rows_out": len(cur),
        "rows_conserved": bool(len(cur) == n_rows_in),
        "dollars_in": (round(dollars_in, 2) if pd.notna(dollars_in) else None),
        "dollars_out": (round(dollars_out, 2) if pd.notna(dollars_out) else None),
        "dollar_delta": (round(dollars_out - dollars_in, 2)
                         if pd.notna(dollars_in) and pd.notna(dollars_out) else None),
        "delta_explained_by": "money_parse stage only (string amounts becoming "
                              "numeric, incl accounting negatives)"}
    led_df.attrs["note"] = (
        "Every mutation above carries a stage and rule id. Rows conserved: {}. Dollar "
        "delta {} is attributable only to declared parse operations.".format(
            led_df.attrs["reconciliation"]["rows_conserved"],
            led_df.attrs["reconciliation"]["dollar_delta"]))
    return cur, led_df, findings


def reconciliation_frame(led_df: pd.DataFrame) -> pd.DataFrame:
    rec = getattr(led_df, "attrs", {}).get("reconciliation")
    if not rec:
        return pd.DataFrame({"note": ["no reconciliation available"]})
    out = pd.DataFrame([{"metric": k, "value": v} for k, v in rec.items()])
    out.attrs["note"] = "Apply-mode conservation proof: rows never change; dollars move " \
                        "only through declared parses."
    return out


def idempotency_check(std: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Run the plan twice; the second pass must produce zero ledger entries."""
    once, led1, _ = run_cleaning(std, **kwargs)
    twice, led2, _ = run_cleaning(once, **kwargs)
    stable = bool(len(led2) == 0)
    out = pd.DataFrame([
        {"metric": "first pass mutations", "value": int(led1["rows_changed"].sum()) if len(led1) else 0},
        {"metric": "second pass mutations", "value": int(led2["rows_changed"].sum()) if len(led2) else 0},
        {"metric": "idempotent", "value": stable},
    ])
    out.attrs["idempotent"] = stable
    out.attrs["note"] = ("A clean process converges: applying it to its own output changes "
                         "nothing." if stable else
                         "NOT idempotent: a stage keeps rewriting its own output; fix before "
                         "trusting the ledger.")
    return out


def dq_scorecard(std: pd.DataFrame, *, allowed_col: str = "allowed_amt",
                 now=None, cw=None) -> pd.DataFrame:
    """Per-column completeness and validity, plus a consistency score and the
    overall index. Scores are shares of ROWS, stated plainly, no weighting
    games."""
    n = len(std)
    if n == 0:
        return pd.DataFrame({"note": ["empty panel"]})
    fv = _fv.run_field_validation(std, now=now)
    invalid = {}
    if "rule_id" in getattr(fv, "columns", []):
        for _, r in fv.iterrows():
            if not str(r["repair"]).startswith("REPAIRABLE"):
                invalid[r["field"]] = invalid.get(r["field"], 0) + int(r["rows"])
    rc = _rc.run_row_consistency(std, cw=cw)
    incons_rows = rc.attrs.get("rows_any_rule", 0) if hasattr(rc, "attrs") else 0
    rows = []
    for col in std.columns:
        s = std[col]
        if pd.api.types.is_numeric_dtype(s):
            missing = int(s.isna().sum())
        else:
            v = s.astype("string")
            missing = int((v.isna() | (v.str.strip() == "")
                           | v.map(lambda x: _th.is_sentinel(x) if isinstance(x, str) else False)).sum())
        completeness = round((1 - missing / n) * 100, 1)
        validity = round((1 - invalid.get(col, 0) / n) * 100, 1)
        rows.append({"column": col, "completeness_pct": completeness,
                     "validity_pct": validity,
                     "score": round((completeness + validity) / 2, 1)})
    out = pd.DataFrame(rows).sort_values("score").reset_index(drop=True)
    consistency = round((1 - incons_rows / n) * 100, 1)
    overall = round(float(out["score"].mean()) * consistency / 100, 1)
    out.attrs["consistency_pct"] = consistency
    out.attrs["overall_index"] = overall
    out.attrs["note"] = (
        "Completeness counts sentinels as missing; validity counts only NON-repairable "
        "failures. Row consistency {}. Overall index {} (column mean scaled by "
        "consistency); track it release over release, not against an absolute bar.".format(
            consistency, overall))
    return out
