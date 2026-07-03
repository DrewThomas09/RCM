"""
closed_claims.py  (v42)
=======================

The "closed claims only" selectable output. Komodo delivers a mix of open
(submitted, near-real-time, not payer-adjudicated) and closed (payer-final,
adjudicated) claims. Open data materially biases market-share and mono/combo
therapy estimates, so a closed-only view is a legitimate high-value run mode.

There is no public Komodo record-level dictionary, so this module is schema
adaptive: it looks for a status/adjudication field by pattern and, when found,
keeps rows whose status reads as closed/paid/adjudicated. When no such field is
present it says so honestly and returns the frame unfiltered with a note, rather
than guessing. It never invents a closed flag.
"""
from __future__ import annotations

import pandas as pd

# tokens that, in a status/adjudication/claim-type field, indicate a closed
# (payer-final, adjudicated) claim vs an open (submitted-only) claim.
_CLOSED_TOKENS = ("closed", "adjudicat", "paid", "final", "remit", "settled")
_OPEN_TOKENS = ("open", "submitted", "pending", "pre-adjud", "unadjud")

_STATUS_HINTS = ("status", "claim_status", "claim_type", "adjudication",
                 "adjud", "claim_stage", "openclosed", "open_closed",
                 "source_type", "claim_source")


def _find_status_col(std: pd.DataFrame, mapping=None):
    """A candidate only qualifies if it carries data: schema.standardize()
    manufactures an all-NA claim_status column when the source never delivered
    one, and an empty column is not a status field."""
    def _ok(col):
        return col in std.columns and std[col].notna().any()
    if mapping and mapping.get("claim_status") and _ok(mapping["claim_status"]):
        return mapping["claim_status"]
    lc = {c.lower().replace(" ", "_"): c for c in std.columns}
    for hint in _STATUS_HINTS:
        for norm, orig in lc.items():
            if hint in norm and _ok(orig):
                return orig
    return None


def classify_open_closed(series: pd.Series) -> pd.Series:
    """Map a status column to 'closed' / 'open' / 'unknown' per value."""
    s = series.astype(str).str.lower()
    out = pd.Series("unknown", index=series.index)
    for tok in _OPEN_TOKENS:
        out = out.mask(s.str.contains(tok, na=False), "open")
    for tok in _CLOSED_TOKENS:
        out = out.mask(s.str.contains(tok, na=False), "closed")
    return out


def closed_claims_view(std: pd.DataFrame, ctx: dict) -> pd.DataFrame:
    """Return an audit frame describing the closed-only filter. The filtered
    data itself is attached as .attrs['closed_frame'] so a caller can either use
    the row-level audit or pull the reduced dataset."""
    mapping = (ctx or {}).get("mapping")
    col = _find_status_col(std, mapping)
    if col is None:
        note = ("No adjudication/status field detected, so open vs closed cannot be "
                "determined. Returning all rows. If this is Komodo data, request the "
                "claim-status field in the extract to enable a closed-only view.")
        audit = pd.DataFrame({"bucket": ["all_rows_unfiltered"], "rows": [len(std)]})
        audit.attrs["note"] = note
        audit.attrs["closed_frame"] = std
        return audit
    klass = classify_open_closed(std[col])
    closed = std[klass == "closed"]
    audit = (klass.value_counts().rename_axis("bucket").reset_index(name="rows"))
    audit.attrs["note"] = (
        f"Status field '{col}': {int((klass=='closed').sum())} closed, "
        f"{int((klass=='open').sum())} open, {int((klass=='unknown').sum())} unknown. "
        f"Closed-only view keeps {len(closed)} rows.")
    audit.attrs["closed_frame"] = closed
    audit.attrs["status_column"] = col
    return audit
