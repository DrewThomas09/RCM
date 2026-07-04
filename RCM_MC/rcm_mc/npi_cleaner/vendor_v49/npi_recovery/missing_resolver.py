"""
missing_resolver.py  (v39)
==========================

Missing information is scattered across a dozen tabs (blank NPIs, blank NDCs,
blank states, unpriced encounters, unmapped payers, ambiguous SAD lines). A
reader has no single place that says: what is missing, how much money sits on it,
and what specifically closes each gap. This module is that place.

It inventories every recoverable gap in the standardized frame, prices each in
dollars, and routes each to the concrete mechanism that fills it (a v35 imputation
strategy, a v39 SAD modifier, an NPPES lookup, a data-request line). The output
is a ranked resolution plan, dollars-first, plus a one-line recoverability
verdict per gap class so nothing recoverable is left on the table and nothing
unrecoverable is chased.

Deterministic and offline; the routes reference other modules but this one only
reports.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .field_validators import luhn_npi_valid, normalize_ndc11
from .text_hygiene import is_sentinel


def _blank(series) -> pd.Series:
    v = series.astype("string")
    return v.isna() | (v.str.strip() == "") | v.map(
        lambda x: is_sentinel(x) if isinstance(x, str) else False)


def gap_inventory(std: pd.DataFrame, *, allowed=None, ref_dir=None) -> pd.DataFrame:
    """One row per gap class: rows affected, dollars on them, a recoverability
    tier, and the route that closes it. Ranked by dollars."""
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0))
    n = len(std)
    rows = []

    def _add(gap, mask, tier, route):
        mask = pd.Series(mask, index=std.index).fillna(False)
        r = int(mask.sum())
        if r:
            rows.append({"gap": gap, "rows": r,
                         "dollars": round(float(a[mask].sum()), 2),
                         "pct_rows": round(r / n * 100, 1) if n else 0.0,
                         "recoverability": tier, "route": route})

    if "billing_npi" in std.columns:
        b = _blank(std["billing_npi"])
        _add("billing NPI blank", b, "PARTIAL (referral/cluster inference; some are "
             "pharmacy-benefit with no medical NPI by design)",
             "recovery stack (v25 imputer) + blank_decomposition buckets")
        bad_luhn = (~b) & ~std["billing_npi"].map(
            lambda x: luhn_npi_valid(x) if str(x).strip() else True)
        _add("billing NPI fails Luhn", bad_luhn, "LOW (keying error, not "
             "deterministically repairable)", "flag for source correction (v35 NPI-LUHN)")
    if "referring_npi" in std.columns:
        _add("referring NPI blank", _blank(std["referring_npi"]),
             "PARTIAL (Open Payments + Order/Referring file narrow it)",
             "connector enrichment (Open Payments, CMS Order and Referring)")
    if "ndc" in std.columns:
        nd_blank = _blank(std["ndc"])
        _add("NDC blank", nd_blank, "PARTIAL (crosswalk from J-code where the "
             "molecule has one dominant NDC; NOC codes cannot)",
             "crosswalk NDC attribution (v33) + drug-identity join")
        if not nd_blank.all():
            amb = (~nd_blank) & std["ndc"].map(
                lambda x: normalize_ndc11(x)[1].startswith("AMBIGUOUS"))
            _add("NDC 10-digit ambiguous", amb, "LOW (segment unknowable without "
                 "the hyphenated source)", "request hyphenated NDCs from the vendor")
    if "state" in std.columns:
        _add("state blank", _blank(std["state"]), "HIGH (zip3 or provider-state "
             "imputation, agreement-checked)",
             "imputation options: from_zip3 / provider_mode (v35)")
    if "drug_name" in std.columns:
        _add("drug name blank", _blank(std["drug_name"]), "HIGH (code-mode or "
             "NDC crosswalk fills most)",
             "imputation options: code_mode / from_ndc (v35)")
    if "units" in std.columns and "allowed_amt" in std.columns:
        u = pd.to_numeric(std["units"], errors="coerce")
        _add("units missing on paid line", (a > 0) & (u.isna() | (u <= 0)),
             "HIGH (code-median or rate-implied fill)",
             "imputation options: code_median / rate_implied (v35)")
    if "payer" in std.columns:
        # unmapped-payer signal is best measured after normalization, but a blank
        # payer is always a gap
        _add("payer blank", _blank(std["payer"]), "MEDIUM (sometimes recoverable "
             "from plan id or group; often a data-request item)",
             "payer normalization audit (v34) then source request")

    # SAD route ambiguity, if the snapshot is available
    if ref_dir is not None and "hcpcs" in std.columns:
        try:
            from . import sad_jurisdiction as _sad
            cls = _sad.classify_frame(std, ref_dir=ref_dir, allowed=a)
            vs = cls.attrs.get("verdict_series") if hasattr(cls, "attrs") else None
            if vs is not None:
                _add("SAD route ambiguous (no JA/JB modifier)",
                     vs == "ROUTE_AMBIGUOUS", "HIGH (a route modifier resolves it)",
                     "supply JA (IV) or JB (SC) modifier; sad_jurisdiction")
                _add("SAD jurisdiction unknown (state unmapped)",
                     vs == "UNKNOWN_JURISDICTION", "HIGH (billing state resolves it)",
                     "supply billing state; sad_jurisdiction MAC map")
        except Exception:
            pass

    if not rows:
        return pd.DataFrame({"note": ["no recoverable gaps detected in the standardized frame"]})
    order = {"HIGH": 0, "MEDIUM": 1, "PARTIAL": 2, "LOW": 3}
    out = (pd.DataFrame(rows)
           .assign(_o=lambda d: d["recoverability"].str.split().str[0].map(order).fillna(9))
           .sort_values(["dollars"], ascending=False).drop(columns="_o")
           .reset_index(drop=True))
    out.attrs["total_gap_dollars"] = round(float(out["dollars"].sum()), 2)
    out.attrs["note"] = (
        "Every recoverable gap in one place, ranked by dollars. HIGH gaps are "
        "deterministically fillable now; PARTIAL split between recoverable and "
        "structural; LOW needs a source or vendor request.")
    return out


def resolution_plan(std: pd.DataFrame, *, allowed=None, ref_dir=None) -> pd.DataFrame:
    """The action list: for each HIGH and MEDIUM gap, the exact flag or strategy
    to run, so the plan is executable, not just descriptive."""
    inv = gap_inventory(std, allowed=allowed, ref_dir=ref_dir)
    if "gap" not in getattr(inv, "columns", []):
        return inv
    act = {
        "state blank": "--deep-clean --impute state:from_zip3 (then review disagreements "
                       "against provider_mode in Imputation_Options)",
        "drug name blank": "--deep-clean --impute drug_name:from_ndc,drug_name:code_mode",
        "units missing on paid line": "--deep-clean --impute units:rate_implied "
                                      "(compare to code_median first)",
        "SAD route ambiguous (no JA/JB modifier)": "add the JA/JB modifier column to the "
                                                    "extract; re-run for a definitive SAD split",
        "SAD jurisdiction unknown (state unmapped)": "populate billing state; extend "
                                                     "mac_jurisdictions_seed.csv if a new MAC appears",
        "NDC blank": "supply --asp-crosswalk and --fda-ndc so NDC attribution can run",
        "referring NPI blank": "enable connectors (Open Payments, Order/Referring) for the "
                               "prescriber gap",
        "payer blank": "review Payer_Normalization_Audit; request plan id from the vendor",
    }
    rows = []
    for _, r in inv.iterrows():
        if str(r["recoverability"]).split()[0] in ("HIGH", "MEDIUM", "PARTIAL"):
            rows.append({"priority_dollars": r["dollars"], "gap": r["gap"],
                         "recoverability": r["recoverability"],
                         "action": act.get(r["gap"], r["route"])})
    if not rows:
        return pd.DataFrame({"note": ["no actionable HIGH/MEDIUM gaps"]})
    out = pd.DataFrame(rows).sort_values("priority_dollars", ascending=False).reset_index(drop=True)
    out.attrs["note"] = ("Executable resolution plan, highest-dollar gap first. Each action is "
                         "a concrete flag, strategy, or data-request line.")
    return out
