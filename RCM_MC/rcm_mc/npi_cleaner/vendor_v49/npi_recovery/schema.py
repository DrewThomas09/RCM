"""Detect which input columns correspond to the canonical claim fields, then
return a clean, typed DataFrame plus a mapping report. Tolerant of arbitrary
header names via normalised-synonym matching with a fuzzy fallback."""

import difflib
import re

import numpy as np
import pandas as pd

from . import config


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


_NPI_FLOAT = re.compile(r"^\d+\.\d+$")
_NPI_SCI = re.compile(r"^\d+(\.\d+)?[eE][+-]?\d+$")


def normalize_npi(v):
    """Coerce a messy NPI cell to a clean 10-digit string. Handles Excel
    artifacts: leading apostrophes/quotes ('1003914151), float coercion
    (1003914151.0), and scientific notation (1.003914151E9). Returns the digit
    string if it's exactly 10 digits; a shorter/longer digit string otherwise
    (so the Luhn check can reject it and route it to recovery); NA if there are
    no digits at all."""
    if pd.isna(v):
        return v
    s = str(v).strip().strip("'\"`").strip()
    if not s:
        return pd.NA
    if _NPI_FLOAT.match(s) or _NPI_SCI.match(s):
        try:
            s = str(int(float(s)))
        except Exception:
            pass
    digits = re.sub(r"\D", "", s)
    if not digits:
        return pd.NA
    return digits


def _blank_to_na(s):
    """Map sentinel 'missing' tokens (NULL, N/A, -, (Not Mapped), ...) to NA,
    compared case-insensitively against the stripped text."""
    low = s.str.strip().str.lower()
    return s.mask(low.isin(config.BLANK_TOKENS), pd.NA)


def detect_columns(df, overrides=None):
    """Return {canonical_key: real_column_name or None} and a per-field report."""
    overrides = overrides or {}
    norm_to_real = {}
    for col in df.columns:
        norm_to_real.setdefault(_norm(col), col)
    norm_cols = list(norm_to_real.keys())

    mapping, report = {}, {}
    claimed = set()  # a real column may map to only one canonical field

    def _free(real):
        return real is not None and real not in claimed

    for canon_key, synonyms in config.COLUMN_SYNONYMS.items():
        if canon_key in overrides:
            mapping[canon_key] = overrides[canon_key]
            report[canon_key] = ("override", overrides[canon_key])
            claimed.add(overrides[canon_key])
            continue
        chosen, how = None, None
        # 1) exact normalised synonym match
        for syn in [_norm(canon_key)] + [_norm(s) for s in synonyms]:
            if syn in norm_to_real and _free(norm_to_real[syn]):
                chosen, how = norm_to_real[syn], "exact"
                break
        # 2) substring match (header contains a synonym or vice versa)
        if chosen is None:
            for syn in [_norm(s) for s in synonyms]:
                for nc in norm_cols:
                    if len(syn) >= 4 and (syn in nc or nc in syn) and _free(norm_to_real[nc]):
                        chosen, how = norm_to_real[nc], "substring"
                        break
                if chosen:
                    break
        # 3) fuzzy match as last resort
        if chosen is None:
            cand = difflib.get_close_matches(_norm(canon_key), norm_cols, n=3, cutoff=0.82)
            cand = [c for c in cand if _free(norm_to_real[c])]
            if not cand:
                for syn in [_norm(s) for s in synonyms]:
                    cc = difflib.get_close_matches(syn, norm_cols, n=3, cutoff=0.88)
                    cand = [c for c in cc if _free(norm_to_real[c])]
                    if cand:
                        break
            if cand:
                chosen, how = norm_to_real[cand[0]], "fuzzy"
        mapping[canon_key] = chosen
        report[canon_key] = (how or "unmatched", chosen)
        if chosen is not None:
            claimed.add(chosen)
    return mapping, report


def _zip3(z):
    digits = re.sub(r"\D", "", str(z))
    return digits[:3] if len(digits) >= 3 else ""


def standardize(df, mapping):
    """Build a canonical-keyed frame. Keeps original index alignment via 'orig_row'."""
    out = pd.DataFrame(index=df.index)
    out["orig_row"] = np.arange(len(df))
    for canon_key, real_col in mapping.items():
        if real_col is None or real_col not in df.columns:
            out[canon_key] = pd.NA
            continue
        col = df[real_col]
        if isinstance(col, pd.DataFrame):   # duplicate header slipped through
            col = col.iloc[:, 0]
        if canon_key in config.STRING_FIELDS:
            s = col.astype("string").str.strip()
            s = _blank_to_na(s)
            if canon_key in ("billing_npi", "referring_npi"):
                s = s.map(normalize_npi).astype("string")
            elif canon_key in ("hcpcs", "state", "pos"):
                s = s.str.upper()
            out[canon_key] = s
        elif canon_key in ("allowed_amt", "units", "ingredient_cost", "dispensing_fee", "days_supply"):
            cleaned_num = (col.astype(str)
                           .str.replace(r"[,$\s]", "", regex=True)
                           .str.replace(r"^\((.+)\)$", r"-\1", regex=True))  # (100) -> -100
            out[canon_key] = pd.to_numeric(cleaned_num, errors="coerce")
        else:
            out[canon_key] = col

    # Derive ZIP3 and a usable state.
    out["zip3"] = out["zip"].apply(_zip3) if "zip" in out else ""
    if "state" not in out or out["state"].isna().all():
        out["state"] = pd.NA
    out["is_blank_billing"] = out["billing_npi"].isna()
    # v19: keep payer + referring specialty as training features when the file
    # carries them (a commercial extract usually does). Absent -> all-NA, which
    # makes the tiers that use them build empty and never fire, so it's safe.
    for _opt in ("payer", "referring_specialty"):
        if _opt in out.columns:
            out[_opt] = out[_opt].astype("string").str.strip().replace({"": pd.NA})
        else:
            out[_opt] = pd.NA
    return out


def coverage_summary(std):
    """Quick field-presence percentages, for the audit/QA report."""
    n = len(std)
    fields = ["billing_npi", "referring_npi", "hcpcs", "pos", "zip3", "state",
              "allowed_amt", "units", "drug_name"]
    rows = []
    for f in fields:
        present = int(std[f].notna().sum()) if f in std else 0
        rows.append({"field": f, "present": present,
                     "pct_present": round(100 * present / n, 1) if n else 0.0})
    return pd.DataFrame(rows)


def standardize_any(df, overrides=None):
    """v47: standardize either a commercial extract or a Medicare RIF file into the
    canonical model, auto-detecting which. Returns (std, mapping, report) where
    report carries a 'source_format' of 'commercial' or 'rif:<type>'. This lets the
    same pipeline run on a Komodo panel or on VRDC/CCW data without the caller
    choosing a path."""
    try:
        from . import rif_schema
        rif_type, score, _ = rif_schema.detect_rif_type(df)
    except Exception:
        rif_type = None
    if rif_type is not None:
        std, rtype, rep = rif_schema.standardize_rif(df, rif_type)
        mapping = {c: c for c in std.columns if c != "orig_row"}
        rep = dict(rep)
        rep["source_format"] = f"rif:{rtype}"
        return std, mapping, rep
    # commercial path
    mapping, report = detect_columns(df, overrides)
    std = standardize(df, mapping)
    real_map = {k: k for k, v in mapping.items() if v is not None and k in std.columns}
    return std, real_map, {"source_format": "commercial", "detail": report}
