"""
preflight.py  (v36)
===================

The error-handling layer BEFORE the pipeline: real extracts arrive with the
wrong encoding, a pipe or tab delimiter, two title rows above the header, a
totals row at the bottom, duplicate header names, and columns that are almost
but not exactly what the standardizer expects. Today those files die at
read_csv or silently map to nothing. This module makes the failure modes
first-class:

  robust_read           encoding fallback (utf-8-sig, utf-8, cp1252, latin-1),
                        delimiter sniff (comma, tab, pipe, semicolon), header
                        row detection by keyword scoring (skips title/junk
                        rows), duplicate-header disambiguation, and a facts
                        report of every decision it made
  column_diagnosis      near-miss suggestions for expected canonical columns,
                        hand-rolled token overlap plus Levenshtein, so a
                        mapping failure says "Billing NPI #" looks like
                        billing_npi instead of failing mute
  coercion_report       per numeric-expected column, how many non-blank values
                        die in numeric coercion, with examples, so silent
                        NaN-ing is visible

Deterministic and offline; no chardet, no fuzzy libraries.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
_DELIMS = (",", "\t", "|", ";")

CANONICAL_HINTS = {
    "billing_npi": ("billing", "npi", "provider", "servicing", "rendering"),
    "referring_npi": ("referring", "prescriber", "ordering", "npi"),
    "hcpcs": ("hcpcs", "cpt", "procedure", "proc", "code"),
    "ndc": ("ndc", "national drug code", "ndc11", "ndc code"),
    "drug_name": ("drug", "product", "medication", "name", "description"),
    "allowed_amt": ("allowed", "paid", "amount", "amt", "dollars", "reimbursed"),
    "units": ("units", "quantity", "qty", "service", "count"),
    "date": ("date", "service", "dos", "svc"),
    "paid_date": ("paid", "payment", "adjudication", "date"),
    "payer": ("payer", "payor", "plan", "insurer", "carrier"),
    "state": ("state", "st"),
    "zip3": ("zip", "postal"),
    "pos": ("pos", "place", "service"),
}


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _norm_header(h: str) -> str:
    return "".join(ch if ch.isalnum() else " " for ch in str(h).lower()).strip()


def similarity(a: str, b: str) -> float:
    """Blend of token overlap and normalized edit distance, 0 to 1."""
    na, nb = _norm_header(a), _norm_header(b)
    if not na or not nb:
        return 0.0
    ta, tb = set(na.split()), set(nb.split())
    tok = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    ca, cb = na.replace(" ", ""), nb.replace(" ", "")
    lev = 1.0 - _levenshtein(ca, cb) / max(len(ca), len(cb))
    return round(0.5 * tok + 0.5 * lev, 3)


def _score_header_row(cells) -> int:
    """How header-like a row is: cells matching any canonical hint token."""
    score = 0
    for c in cells:
        n = _norm_header(c)
        if not n:
            continue
        toks = set(n.split())
        for hints in CANONICAL_HINTS.values():
            if toks & set(hints):
                score += 1
                break
    return score


def robust_read(path, *, max_probe_lines: int = 30):
    """Read a delimited file that a plain read_csv chokes on. Returns
    (DataFrame or None, facts DataFrame). Never raises; the facts table
    explains every decision or the exact failure."""
    facts = []
    p = Path(str(path))
    if not p.exists():
        facts.append({"decision": "file", "value": "NOT FOUND: {}".format(p)})
        return None, _facts_frame(facts, ok=False)
    raw = p.read_bytes()
    text = None
    enc_used = None
    for enc in _ENCODINGS:
        try:
            text = raw.decode(enc)
            enc_used = enc
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        facts.append({"decision": "encoding", "value": "UNDECODABLE under {}".format(_ENCODINGS)})
        return None, _facts_frame(facts, ok=False)
    facts.append({"decision": "encoding", "value": enc_used})

    lines = text.splitlines()
    probe = [ln for ln in lines[:max_probe_lines]]
    best = (0, ",", 0)  # (score, delim, header_idx)
    for delim in _DELIMS:
        for idx, ln in enumerate(probe):
            cells = ln.split(delim)
            if len(cells) < 3:
                continue
            sc = _score_header_row(cells)
            if sc > best[0]:
                best = (sc, delim, idx)
    score, delim, hdr = best
    if score < 2:
        facts.append({"decision": "header", "value": "NO HEADER-LIKE ROW in first {} lines "
                      "(best score {})".format(max_probe_lines, score)})
        return None, _facts_frame(facts, ok=False)
    facts.append({"decision": "delimiter", "value": repr(delim)})
    facts.append({"decision": "header_row_index", "value": hdr})
    if hdr > 0:
        facts.append({"decision": "junk_rows_skipped", "value": hdr})

    df = None
    padded = merged = 0
    try:
        # strict, quote-aware first: handles delimiters inside quoted fields
        df = pd.read_csv(io.StringIO(text), sep=delim, skiprows=hdr, dtype=str,
                         engine="python", on_bad_lines="error")
        # pandas pads SHORT rows silently (only long rows raise); surface them.
        _nexp = len(df.columns)
        _short = sum(1 for ln in lines[hdr + 1:]
                     if ln.strip() and len(ln.split(delim)) < _nexp)
        if _short:
            padded = _short
            facts.append({"decision": "rows_padded_short", "value": _short})
            facts.append({"decision": "rows_lost_to_raggedness", "value": 0})
    except Exception:
        # ragged file: pad short rows, merge overflow into the LAST field.
        # Deterministic, and NO row (no dollars) is ever silently dropped.
        header_cells = [c.strip() for c in lines[hdr].split(delim)]
        n_expected = len(header_cells)
        records = []
        for ln in lines[hdr + 1:]:
            if not ln.strip():
                continue
            cells = ln.split(delim)
            if len(cells) < n_expected:
                cells = cells + [""] * (n_expected - len(cells))
                padded += 1
            elif len(cells) > n_expected:
                cells = cells[:n_expected - 1] + [delim.join(cells[n_expected - 1:])]
                merged += 1
            records.append(cells)
        if not records:
            facts.append({"decision": "parse", "value": "FAILED: no data rows under header"})
            return None, _facts_frame(facts, ok=False)
        df = pd.DataFrame(records, columns=header_cells)
        if padded:
            facts.append({"decision": "rows_padded_short", "value": padded})
        if merged:
            facts.append({"decision": "rows_overflow_merged_last_field", "value": merged})
        facts.append({"decision": "rows_lost_to_raggedness", "value": 0})
    if padded or merged:
        facts.append({"decision": "ragged_rows_detected", "value": padded + merged})

    cols = list(df.columns)
    seen = {}
    renamed = 0
    for i, c in enumerate(cols):
        if c in seen:
            seen[c] += 1
            cols[i] = "{}__dup{}".format(c, seen[c])
            renamed += 1
        else:
            seen[c] = 0
    if renamed:
        df.columns = cols
        facts.append({"decision": "duplicate_headers_disambiguated", "value": renamed})
    empty = [c for c in df.columns
             if df[c].isna().all() or (df[c].astype("string").str.strip() == "").all()]
    if empty:
        facts.append({"decision": "empty_columns", "value": ", ".join(empty[:8])})
    facts.append({"decision": "rows_read", "value": len(df)})
    facts.append({"decision": "columns_read", "value": len(df.columns)})
    return df, _facts_frame(facts, ok=True)


def _facts_frame(facts, *, ok: bool) -> pd.DataFrame:
    out = pd.DataFrame(facts)
    out.attrs["ok"] = ok
    out.attrs["note"] = ("Every read decision recorded; a failed preflight names the exact "
                         "layer that broke instead of a stack trace." if not ok else
                         "Read succeeded with the decisions above.")
    return out


def column_diagnosis(headers, *, threshold: float = 0.45,
                     canonical=None) -> pd.DataFrame:
    """For each expected canonical column: the best-matching raw header, its
    similarity, and a verdict. A NEAR MISS says exactly which header to map."""
    canonical = canonical or CANONICAL_HINTS
    rows = []
    hdrs = [str(h) for h in headers]
    for canon, hints in canonical.items():
        best_h, best_s = "", 0.0
        for h in hdrs:
            s = max(similarity(h, canon), max(similarity(h, t) for t in hints))
            if s > best_s:
                best_h, best_s = h, s
        if best_s >= 0.85:
            verdict = "MATCHED"
        elif best_s >= threshold:
            verdict = "NEAR MISS: map {!r} to {}".format(best_h, canon)
        else:
            verdict = "ABSENT"
        rows.append({"canonical": canon, "best_header": best_h,
                     "similarity": best_s, "verdict": verdict})
    out = pd.DataFrame(rows).sort_values("similarity", ascending=False).reset_index(drop=True)
    out.attrs["note"] = ("NEAR MISS rows are one rename away from mapping; ABSENT rows "
                         "are genuinely not in the file and belong on the data request.")
    return out


def coercion_report(raw: pd.DataFrame,
                    numeric_cols=("allowed_amt", "units")) -> pd.DataFrame:
    """Values that would die in numeric coercion, per column, with examples.
    Silent NaN-ing is the quietest way to lose dollars; this prices it."""
    rows = []
    for col in numeric_cols:
        if col not in raw.columns:
            continue
        v = raw[col].astype("string")
        nonblank = v.notna() & (v.str.strip() != "")
        coerced = pd.to_numeric(v, errors="coerce")
        dead = nonblank & coerced.isna()
        n = int(dead.sum())
        if n:
            ex = v[dead].iloc[0]
            rows.append({"column": col, "nonblank_values": int(nonblank.sum()),
                         "coercion_casualties": n,
                         "casualty_share_pct": round(n / int(nonblank.sum()) * 100, 1),
                         "example": str(ex)[:40]})
        else:
            rows.append({"column": col, "nonblank_values": int(nonblank.sum()),
                         "coercion_casualties": 0, "casualty_share_pct": 0.0,
                         "example": ""})
    if not rows:
        return pd.DataFrame({"note": ["no numeric-expected columns present"]})
    out = pd.DataFrame(rows)
    total = int(out["coercion_casualties"].sum())
    out.attrs["total_casualties"] = total
    out.attrs["note"] = ("{} non-blank values would coerce to NaN and drop out of every "
                         "sum. The deep-clean money parser (v35) rescues accounting "
                         "formats; the rest are here with examples.".format(total))
    return out
