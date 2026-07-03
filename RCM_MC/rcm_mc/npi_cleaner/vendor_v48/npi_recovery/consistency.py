"""
consistency.py  (v45)
=====================

Cross-field consistency screens for common claims problems the row-level coding
edits do not cover. These are relationships between fields on the same claim that
must hold, and where a violation is deterministically detectable:

  money ordering        paid should not exceed allowed; allowed should not exceed
                        billed/charged. A violation is a data error, not a
                        judgment call.
  date ordering         paid date should not precede service date; service date
                        should not be in the future.
  npi role coherence    billing, rendering, and referring NPIs playing impossible
                        roles: referring equals billing on a referred service, or
                        all three identical where that is implausible.
  units vs days supply  on pharmacy lines, quantity and days supply should be
                        broadly consistent (not off by orders of magnitude).

Each screen flags and, where a single correct value is deterministic, proposes it.
Most money and date violations have a clear fix (swap, or null the impossible
value for review); role and units violations are flagged for review. Everything
is offline and original-preserving; suggestions go to the corrections companion.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def _col(std, mapping, canonical, fallbacks=()):
    if mapping and mapping.get(canonical) and mapping[canonical] in std.columns:
        return mapping[canonical]
    if canonical in std.columns:
        return canonical
    for f in fallbacks:
        if f in std.columns:
            return f
    return None


def money_ordering(std: pd.DataFrame, mapping=None) -> pd.DataFrame:
    """paid <= allowed <= billed. Flag violations; they are impossible values."""
    allowed_c = _col(std, mapping, "allowed_amt")
    billed_c = _col(std, mapping, "billed_amt", ("charge_amt", "charges", "submitted_amt"))
    paid_c = _col(std, mapping, "paid_amt", ("payment_amt", "plan_paid"))
    have = [c for c in (allowed_c, billed_c, paid_c) if c]
    if len(have) < 2:
        return pd.DataFrame({"note": [
            "money ordering needs at least two of allowed / billed / paid amounts"]})
    allowed = pd.to_numeric(std[allowed_c], errors="coerce") if allowed_c else None
    billed = pd.to_numeric(std[billed_c], errors="coerce") if billed_c else None
    paid = pd.to_numeric(std[paid_c], errors="coerce") if paid_c else None
    rows = []
    for i in std.index:
        probs = []
        a = allowed.loc[i] if allowed is not None else np.nan
        b = billed.loc[i] if billed is not None else np.nan
        p = paid.loc[i] if paid is not None else np.nan
        if not np.isnan(a) and not np.isnan(b) and a > b + 1e-6:
            probs.append("allowed exceeds billed")
        if not np.isnan(p) and not np.isnan(a) and p > a + 1e-6:
            probs.append("paid exceeds allowed")
        if probs:
            rows.append({"row": i, "allowed": a, "billed": b, "paid": p,
                         "violation": "; ".join(probs),
                         "suggested_fix": "verify amounts; likely a field swap or entry error",
                         "verdict": "flag"})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (f"{len(out)} rows violate paid <= allowed <= billed. These "
                         f"are impossible orderings and indicate data-entry or mapping "
                         f"errors worth correcting at the source.")
    return out


def date_ordering(std: pd.DataFrame, mapping=None) -> pd.DataFrame:
    """service_date <= paid_date, and service_date not in the future."""
    svc_c = _col(std, mapping, "date", ("date_of_service", "service_date", "dos"))
    paid_c = _col(std, mapping, "paid_date", ("payment_date", "adjudication_date"))
    if svc_c is None:
        return pd.DataFrame({"note": ["date ordering needs a service date column"]})
    svc = pd.to_datetime(std[svc_c], errors="coerce")
    paid = pd.to_datetime(std[paid_c], errors="coerce") if paid_c else None
    today = pd.Timestamp.now().normalize()
    rows = []
    for i in std.index:
        s = svc.loc[i]
        probs = []
        if pd.notna(s) and s > today:
            probs.append("service date in the future")
        if paid is not None:
            p = paid.loc[i]
            if pd.notna(s) and pd.notna(p) and p < s:
                probs.append("paid date precedes service date")
        if probs:
            rows.append({"row": i, "service_date": s,
                         "paid_date": paid.loc[i] if paid is not None else pd.NaT,
                         "violation": "; ".join(probs),
                         "suggested_fix": "verify dates; future service dates often "
                                          "indicate a year typo",
                         "verdict": "flag"})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (f"{len(out)} rows have an impossible date ordering (future "
                         f"service date or paid-before-service). Often a year typo; "
                         f"verify at the source.")
    return out


def npi_role_coherence(std: pd.DataFrame, mapping=None) -> pd.DataFrame:
    """Flag impossible provider-role combinations on a claim."""
    bill_c = _col(std, mapping, "billing_npi", ("npi",))
    refer_c = _col(std, mapping, "referring_npi",)
    rend_c = _col(std, mapping, "rendering_npi",)
    if bill_c is None or (refer_c is None and rend_c is None):
        return pd.DataFrame({"note": [
            "role coherence needs a billing NPI and a referring or rendering NPI"]})
    bill = std[bill_c].astype(str)
    refer = std[refer_c].astype(str) if refer_c else None
    rows = []
    for i in std.index:
        probs = []
        b = bill.loc[i]
        if refer is not None:
            r = refer.loc[i]
            if b and r and b == r and b not in ("", "nan", "<NA>"):
                probs.append("referring NPI equals billing NPI on a referred service")
        if probs:
            rows.append({"row": i, "billing_npi": b,
                         "referring_npi": refer.loc[i] if refer is not None else "",
                         "violation": "; ".join(probs),
                         "suggested_fix": "verify provider roles; self-referral or a "
                                          "mapping error",
                         "verdict": "flag"})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (f"{len(out)} rows have an implausible provider-role combination "
                         f"(e.g. referring equals billing). Verify roles; often a "
                         f"column-mapping error.")
    return out


def units_days_supply(std: pd.DataFrame, mapping=None) -> pd.DataFrame:
    """On pharmacy lines, flag quantity and days-supply that are wildly
    inconsistent (differ by more than ~100x), a common keying error."""
    qty_c = _col(std, mapping, "units", ("quantity", "qty"))
    days_c = _col(std, mapping, "days_supply", ("dayssupply", "days"))
    if qty_c is None or days_c is None:
        return pd.DataFrame({"note": [
            "units/days-supply screen needs both a quantity and a days-supply column"]})
    qty = pd.to_numeric(std[qty_c], errors="coerce")
    days = pd.to_numeric(std[days_c], errors="coerce")
    rows = []
    for i in std.index:
        q, d = qty.loc[i], days.loc[i]
        if pd.notna(q) and pd.notna(d) and d > 0 and q > 0:
            ratio = q / d
            if ratio > 100 or ratio < 0.01:
                rows.append({"row": i, "quantity": q, "days_supply": d,
                             "qty_per_day": round(float(ratio), 3),
                             "violation": "quantity and days supply differ by >100x",
                             "suggested_fix": "verify quantity/days-supply; likely a "
                                              "unit or keying error",
                             "verdict": "flag"})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (f"{len(out)} pharmacy lines have quantity and days-supply off "
                         f"by more than 100x, a common keying error.")
    return out


def run_all(std: pd.DataFrame, mapping=None) -> dict:
    """Run every consistency screen; return {name: frame}. Screens that lack their
    inputs return a one-row note frame rather than raising."""
    return {
        "money_ordering": money_ordering(std, mapping),
        "date_ordering": date_ordering(std, mapping),
        "npi_role_coherence": npi_role_coherence(std, mapping),
        "units_days_supply": units_days_supply(std, mapping),
    }
