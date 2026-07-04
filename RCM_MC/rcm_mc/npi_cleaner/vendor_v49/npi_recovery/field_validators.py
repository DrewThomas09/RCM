"""
field_validators.py  (v35)
==========================

Stage 1 of the deep-clean process: per-field validation and normalization, one
small pure function per rule, assembled through a registry so the set is
inspectable and extendable. Each validator answers two questions separately:
is the value VALID, and if not, is there a DETERMINISTIC repair (never a guess).

The rules that matter most here are the ones generic cleaners get wrong:

  NPI Luhn check      the NPI check digit runs Luhn over 80840 plus the first
                      nine digits; format-valid ten-digit numbers still fail it
  NDC 11-digit        hyphenated NDCs come in 4-4-2, 5-3-2, and 5-4-1; each pads
                      a DIFFERENT segment to reach 5-4-2. Unhyphenated ten-digit
                      NDCs are AMBIGUOUS and must be flagged, never left-padded
  Excel serial dates  45123 is a date; parse it from the 1899-12-30 origin
  accounting money    (1,234.50) is negative; $1,234 has separators

Deterministic and offline.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# NPI
# --------------------------------------------------------------------------- #

def luhn_npi_valid(npi) -> bool:
    """True when the 10-digit NPI passes the Luhn check over 80840 + first 9."""
    s = "".join(ch for ch in str(npi) if ch.isdigit())
    if len(s) != 10:
        return False
    full = "80840" + s[:9]
    total = 0
    for i, ch in enumerate(reversed(full)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10 == int(s[9])


def validate_npi_series(s: pd.Series) -> pd.DataFrame:
    v = s.astype("string").fillna("").str.replace(r"\D", "", regex=True)
    blank = v == ""
    bad_len = (~blank) & (v.str.len() != 10)
    ten = (~blank) & (v.str.len() == 10)
    luhn_fail = ten & ~v.map(luhn_npi_valid)
    return pd.DataFrame({"blank": blank, "bad_length": bad_len,
                         "luhn_fail": luhn_fail,
                         "valid": ten & ~luhn_fail})


# --------------------------------------------------------------------------- #
# NDC
# --------------------------------------------------------------------------- #

_NDC_PAD = {(4, 4, 2): 0, (5, 3, 2): 1, (5, 4, 1): 2}


def normalize_ndc11(raw) -> tuple[str, str]:
    """Return (ndc11, status). Hyphenated 10-digit forms pad the correct
    segment; 11-digit inputs pass through; unhyphenated 10-digit inputs are
    AMBIGUOUS_10DIGIT and returned unchanged rather than guessed."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return "", "BLANK"
    s = str(raw).strip()
    if not s:
        return "", "BLANK"
    if "-" in s:
        segs = s.split("-")
        if len(segs) == 3 and all(seg.isdigit() for seg in segs):
            lens = tuple(len(seg) for seg in segs)
            if lens == (5, 4, 2):
                return "".join(segs), "OK_HYPHENATED_11"
            if lens in _NDC_PAD:
                i = _NDC_PAD[lens]
                segs[i] = segs[i].zfill(len(segs[i]) + 1)
                return "".join(segs), "PADDED_{}_{}_{}".format(*lens)
        return re.sub(r"\D", "", s), "IRREGULAR_HYPHENATION"
    digits = re.sub(r"\D", "", s)
    if len(digits) == 11:
        return digits, "OK_11"
    if len(digits) == 10:
        return digits, "AMBIGUOUS_10DIGIT (segment unknown; do not left-pad)"
    return digits, "INVALID_LENGTH_{}".format(len(digits))


def normalize_ndc_series(s: pd.Series):
    pairs = s.map(normalize_ndc11)
    return pairs.map(lambda p: p[0]), pairs.map(lambda p: p[1])


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #

_EXCEL_ORIGIN = datetime(1899, 12, 30)


def parse_date_multi(v):
    """Return (timestamp_or_NaT, status). Handles ISO, US slash, compact
    YYYYMMDD, and Excel serials in the plausible claims window."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return pd.NaT, "BLANK"
    if isinstance(v, (pd.Timestamp, datetime)):
        return pd.Timestamp(v), "ALREADY_DATE"
    s = str(v).strip()
    if not s:
        return pd.NaT, "BLANK"
    if re.fullmatch(r"\d{4,6}(\.0)?", s):
        try:
            serial = float(s)
            if 20000 <= serial <= 60000:
                return pd.Timestamp(_EXCEL_ORIGIN + timedelta(days=serial)), "EXCEL_SERIAL"
        except ValueError:
            pass
    for fmt, tag in (("%Y-%m-%d", "ISO"), ("%m/%d/%Y", "US_SLASH"),
                     ("%Y%m%d", "COMPACT"), ("%m/%d/%y", "US_SLASH_2Y"),
                     ("%Y-%m-%d %H:%M:%S", "ISO_TS")):
        try:
            return pd.Timestamp(datetime.strptime(s, fmt)), tag
        except ValueError:
            continue
    ts = pd.to_datetime(s, errors="coerce")
    return (ts, "FALLBACK_PARSE") if pd.notna(ts) else (pd.NaT, "UNPARSEABLE")


def validate_date_series(s: pd.Series, *, now=None) -> pd.DataFrame:
    now = pd.Timestamp(now) if now is not None else pd.Timestamp.today().normalize()
    pairs = s.map(parse_date_multi)
    ts = pd.Series([p[0] for p in pairs], index=s.index)
    status = pd.Series([p[1] for p in pairs], index=s.index)
    return pd.DataFrame({"parsed": ts, "status": status,
                         "future": ts.notna() & (ts > now),
                         "pre_2000": ts.notna() & (ts < pd.Timestamp("2000-01-01")),
                         "unparseable": status == "UNPARSEABLE",
                         "excel_serial": status == "EXCEL_SERIAL"})


# --------------------------------------------------------------------------- #
# Money and units
# --------------------------------------------------------------------------- #

def parse_money(v):
    """Return (float_or_nan, status). Accounting negatives in parentheses,
    currency symbols, thousands separators, trailing minus."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan, "BLANK"
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v), "NUMERIC"
    s = str(v).strip()
    if not s:
        return np.nan, "BLANK"
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    if s.endswith("-"):
        neg, s = True, s[:-1]
    s2 = s.replace("$", "").replace(",", "").replace(" ", "")
    try:
        val = float(s2)
    except ValueError:
        return np.nan, "UNPARSEABLE"
    return (-val if neg else val), ("PARENS_NEGATIVE" if neg and "(" in str(v)
                                    else ("TRAILING_MINUS" if neg else "PARSED"))


def parse_money_series(s: pd.Series):
    pairs = s.map(parse_money)
    return (pd.Series([p[0] for p in pairs], index=s.index),
            pd.Series([p[1] for p in pairs], index=s.index))


_STATE_SET = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC", "PR",
    "VI", "GU", "AS", "MP"}


def validate_state_series(s: pd.Series) -> pd.Series:
    v = s.astype("string").fillna("").str.strip().str.upper()
    return (v != "") & ~v.isin(_STATE_SET)


# --------------------------------------------------------------------------- #
# Registry and runner
# --------------------------------------------------------------------------- #

def run_field_validation(std: pd.DataFrame, *, now=None) -> pd.DataFrame:
    """One row per field-level rule with rows hit and a repairability verdict.
    Report-only; apply-mode repairs live in clean_pipeline."""
    rows = []

    def _add(field, rule_id, mask, repair):
        n = int(pd.Series(mask).sum())
        if n:
            rows.append({"field": field, "rule_id": rule_id, "rows": n,
                         "repair": repair})

    for col in ("billing_npi", "referring_npi"):
        if col in std.columns:
            r = validate_npi_series(std[col])
            _add(col, "NPI-LEN", r["bad_length"], "NOT REPAIRABLE (source fix)")
            _add(col, "NPI-LUHN", r["luhn_fail"],
                 "NOT REPAIRABLE deterministically (check digit fails; likely keying)")
    if "ndc" in std.columns:
        _, status = normalize_ndc_series(std["ndc"].astype("string"))
        _add("ndc", "NDC-PAD", status.str.startswith("PADDED"),
             "REPAIRABLE (segment-aware pad to 11)")
        _add("ndc", "NDC-AMBIG", status.str.startswith("AMBIGUOUS"),
             "NOT REPAIRABLE (10 digits unhyphenated; segment unknown)")
        _add("ndc", "NDC-LEN", status.str.startswith("INVALID_LENGTH"),
             "NOT REPAIRABLE (wrong digit count)")
    for col in ("date", "paid_date"):
        if col in std.columns:
            r = validate_date_series(std[col], now=now)
            _add(col, "DATE-EXCEL", r["excel_serial"], "REPAIRABLE (serial origin parse)")
            _add(col, "DATE-FUTURE", r["future"], "QUARANTINE (service in the future)")
            _add(col, "DATE-PRE2000", r["pre_2000"], "QUARANTINE (implausibly old)")
            _add(col, "DATE-UNPARSE", r["unparseable"], "NOT REPAIRABLE")
    if "allowed_amt" in std.columns and not pd.api.types.is_numeric_dtype(std["allowed_amt"]):
        _, stat = parse_money_series(std["allowed_amt"])
        _add("allowed_amt", "MONEY-PARENS", stat == "PARENS_NEGATIVE",
             "REPAIRABLE (accounting negative)")
        _add("allowed_amt", "MONEY-FMT", stat == "PARSED",
             "REPAIRABLE (currency symbols / separators)")
        _add("allowed_amt", "MONEY-UNPARSE", stat == "UNPARSEABLE", "NOT REPAIRABLE")
    if "state" in std.columns:
        _add("state", "STATE-CODE", validate_state_series(std["state"]),
             "REPAIRABLE where zip3 or provider state agrees (imputation options)")
    if "hcpcs" in std.columns:
        hc = std["hcpcs"].astype("string").fillna("").str.strip().str.upper()
        bad = (hc != "") & ~hc.str.fullmatch(r"[A-Z]\d{4}|\d{5}")
        _add("hcpcs", "HCPCS-FMT", bad, "NOT REPAIRABLE (not a HCPCS/CPT shape)")

    if not rows:
        return pd.DataFrame({"note": ["all field-level validators pass"]})
    out = pd.DataFrame(rows).sort_values(["field", "rule_id"]).reset_index(drop=True)
    out.attrs["note"] = ("Each rule is a pure function in field_validators; REPAIRABLE "
                         "rows are fixed deterministically under apply-mode cleaning, "
                         "everything else is quarantined or left for the source.")
    return out
