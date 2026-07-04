"""
row_consistency.py  (v35)
=========================

Stage 2 of the deep-clean process: rules that only fire across fields. A row can
pass every field validator and still be internally impossible; these are the
contradictions that survive column-by-column cleaning.

Each rule is one small function returning (bad_mask, severity, description), and
the registry runs them all, pricing every hit in dollars so triage is by money,
not row count. Report-only; quarantine decisions belong to the analyst.

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _num(std, col):
    return pd.to_numeric(std.get(col), errors="coerce") if col in std.columns else None


def _dt(std, col):
    return pd.to_datetime(std[col], errors="coerce") if col in std.columns else None


def rule_service_after_paid(std):
    svc, paid = _dt(std, "date"), _dt(std, "paid_date")
    if svc is None or paid is None:
        return None
    return (svc.notna() & paid.notna() & (svc > paid), "HIGH",
            "service date after paid date (impossible sequence)")


def rule_zero_units_positive_dollars(std):
    a, u = _num(std, "allowed_amt"), _num(std, "units")
    if a is None or u is None:
        return None
    return ((a > 0) & (u.fillna(0) == 0), "MEDIUM",
            "positive dollars on zero units (rate math breaks; unit feed gap)")


def rule_positive_units_zero_dollars(std):
    a, u = _num(std, "allowed_amt"), _num(std, "units")
    if a is None or u is None:
        return None
    return ((a.fillna(0) == 0) & (u > 0), "LOW",
            "units with zero dollars (denied, capitated, or bundled lines)")


def rule_sign_mismatch(std):
    a, u = _num(std, "allowed_amt"), _num(std, "units")
    if a is None or u is None:
        return None
    return (((a > 0) & (u < 0)) | ((a < 0) & (u > 0)), "HIGH",
            "dollars and units disagree in sign (partial reversal keyed wrong)")


def rule_ndc_without_hcpcs(std):
    if "ndc" not in std.columns or "hcpcs" not in std.columns:
        return None
    nd = std["ndc"].astype("string").fillna("").str.strip()
    hc = std["hcpcs"].astype("string").fillna("").str.strip()
    return ((nd != "") & (hc == ""), "LOW",
            "NDC present with no procedure code (pharmacy row in a medical feed?)")


def rule_state_zip3_mismatch(std, *, zip3_state=None):
    if "state" not in std.columns or "zip3" not in std.columns or not zip3_state:
        return None
    st = std["state"].astype("string").fillna("").str.strip().str.upper()
    z3 = std["zip3"].astype("string").fillna("").str.replace(r"\D", "", regex=True).str[:3]
    exp = z3.map(lambda z: zip3_state.get(z, ""))
    return ((st != "") & (exp != "") & (st != exp), "MEDIUM",
            "state disagrees with the zip3's state (address fields out of sync)")


def rule_ndc_hcpcs_pair_unknown(std, *, cw=None):
    if cw is None or "ndc" not in std.columns or "hcpcs" not in std.columns:
        return None
    ndc_to_codes = cw.get("ndc_to_hcpcs") if isinstance(cw, dict) else None
    if not ndc_to_codes:
        return None
    from .field_validators import normalize_ndc11
    nd = std["ndc"].map(lambda x: normalize_ndc11(x)[0])
    hc = std["hcpcs"].astype("string").fillna("").str.strip().str.upper()

    def _bad(n, h):
        if not n or not h or n not in ndc_to_codes:
            return False
        return h not in ndc_to_codes[n]

    mask = pd.Series([_bad(n, h) for n, h in zip(nd, hc)], index=std.index)
    return (mask, "MEDIUM",
            "NDC maps to a different code than billed (crosswalk disagreement; "
            "check unit basis and drug identity)")


def build_zip3_state_map(std: pd.DataFrame, *, min_rows: int = 20) -> dict:
    """Learn the modal state per zip3 from the panel's own well-populated rows;
    deterministic, used only to flag disagreements, never to overwrite."""
    if "state" not in std.columns or "zip3" not in std.columns:
        return {}
    st = std["state"].astype("string").fillna("").str.strip().str.upper()
    z3 = std["zip3"].astype("string").fillna("").str.replace(r"\D", "", regex=True).str[:3]
    df = pd.DataFrame({"z": z3, "s": st})
    df = df[(df["z"].str.len() == 3) & (df["s"] != "")]
    out = {}
    for z, g in df.groupby("z"):
        if len(g) >= min_rows:
            counts = g["s"].value_counts()
            if counts.iloc[0] / len(g) >= 0.8:
                out[z] = counts.index[0]
    return out


RULES = [
    ("ROW-SVC-PAID", rule_service_after_paid),
    ("ROW-0U-POSD", rule_zero_units_positive_dollars),
    ("ROW-POSU-0D", rule_positive_units_zero_dollars),
    ("ROW-SIGN", rule_sign_mismatch),
    ("ROW-NDC-NOHCPCS", rule_ndc_without_hcpcs),
]


def run_row_consistency(std: pd.DataFrame, *, allowed=None, cw=None,
                        zip3_state=None) -> pd.DataFrame:
    """All rules, rows and dollars per hit, worst first. zip3_state defaults to
    a map learned from the panel itself (flag-only)."""
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0))
    zmap = zip3_state if zip3_state is not None else build_zip3_state_map(std)
    results = []
    for rule_id, fn in RULES:
        r = fn(std)
        if r is None:
            continue
        mask, sev, desc = r
        results.append((rule_id, mask, sev, desc))
    r = rule_state_zip3_mismatch(std, zip3_state=zmap)
    if r is not None:
        results.append(("ROW-ST-ZIP3", r[0], r[1], r[2]))
    r = rule_ndc_hcpcs_pair_unknown(std, cw=cw)
    if r is not None:
        results.append(("ROW-NDC-CODE", r[0], r[1], r[2]))

    rows = []
    any_mask = pd.Series(False, index=std.index)
    for rule_id, mask, sev, desc in results:
        mask = pd.Series(mask, index=std.index).fillna(False)
        n = int(mask.sum())
        if n == 0:
            continue
        any_mask |= mask
        rows.append({"rule_id": rule_id, "severity": sev, "rows": n,
                     "dollars": round(float(a[mask].abs().sum()), 2),
                     "description": desc})
    if not rows:
        return pd.DataFrame({"note": ["no cross-field contradictions; rows are "
                                      "internally consistent"]})
    out = (pd.DataFrame(rows)
           .sort_values(["severity", "dollars"], ascending=[True, False])
           .reset_index(drop=True))
    out.attrs["rows_any_rule"] = int(any_mask.sum())
    out.attrs["dollars_any_rule"] = round(float(a[any_mask].abs().sum()), 2)
    out.attrs["note"] = (
        "{} rows ({} dollars) hit at least one rule. Triage by dollars, not row count; "
        "LOW-severity zero-dollar lines are often benign feed behavior.".format(
            out.attrs["rows_any_rule"], out.attrs["dollars_any_rule"]))
    return out
