"""
text_hygiene.py  (v35)
======================

Stage 0 of the deep-clean process: the damage a file picks up before it ever
reaches an analyst. Excel and warehouse exports mangle identifiers and text in
recurring, mechanical ways, and every one of them silently corrupts joins and
sums downstream:

  scientific notation   an NPI opened in Excel becomes 1.234567893E9 and stops
                        joining against any roster
  leading-zero loss     NDCs and ZIPs read as numbers lose their left zeros
  sentinel strings      N/A, NULL, -, --, #N/A, UNK sit in cells and count as
                        populated while meaning missing
  invisible characters  NBSP, zero-width spaces, control characters break
                        equality on keys that print identically
  mojibake              UTF-8 read as Latin-1 (A-tilde sequences, a-circumflex
                        euro sequences) marks a double-encoded export upstream

Every function is pure: scanners return findings, normalizers return the fixed
series plus ledger entries, nothing mutates in place. Deterministic and offline.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

SENTINELS = {"N/A", "NA", "N.A.", "NULL", "NONE", "#N/A", "#REF!", "#VALUE!",
             "-", "--", ".", "?", "UNK", "UNKNOWN", "MISSING", "(BLANK)", "NAN"}

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b\u200c\u200d\ufeff]")
_NBSP = "\u00a0"
_SCI = re.compile(r"^\d\.\d+E\+?\d+$", re.IGNORECASE)
_MOJI = re.compile(r"\u00c3[\u0080-\u00bf]|\u00e2\u0080|\u00ef\u00bf\u00bd")


def is_sentinel(v) -> bool:
    return isinstance(v, str) and v.strip().upper() in SENTINELS


def fix_scientific_notation_id(v, *, width: int | None = None) -> str | None:
    """Restore an identifier Excel rewrote as scientific notation. Returns the
    digit string, zero-padded to width when given, or None when the value is not
    a clean scientific-notation rendering (never guesses)."""
    if not isinstance(v, str) or not _SCI.match(v.strip()):
        return None
    try:
        f = float(v.strip())
    except ValueError:
        return None
    i = int(round(f))
    if abs(f - i) > 1e-6 * max(abs(f), 1.0):
        return None
    s = str(i)
    if width is not None:
        if len(s) > width:
            return None
        s = s.zfill(width)
    return s


def scan_text_hygiene(std: pd.DataFrame, *, id_widths: dict | None = None) -> pd.DataFrame:
    """Findings per column: sentinel strings, invisible characters, mojibake,
    scientific-notation identifiers, and leading-zero risk on identifier columns
    (numeric dtype where a fixed-width string was expected). Report-only."""
    id_widths = id_widths or {"billing_npi": 10, "referring_npi": 10, "ndc": 11}
    rows = []
    for col in std.columns:
        s = std[col]
        if pd.api.types.is_numeric_dtype(s):
            if col in id_widths:
                rows.append({"column": col, "finding": "IDENTIFIER_STORED_NUMERIC",
                             "rows": int(s.notna().sum()),
                             "detail": "leading zeros unrecoverable if ever present; "
                                       "read as text at source"})
            continue
        v = s.astype("string")
        sent = v.map(lambda x: is_sentinel(x) if isinstance(x, str) else False)
        ctrl = v.map(lambda x: bool(_CTRL.search(x)) if isinstance(x, str) else False)
        nbsp = v.map(lambda x: _NBSP in x if isinstance(x, str) else False)
        moji = v.map(lambda x: bool(_MOJI.search(x)) if isinstance(x, str) else False)
        sci = v.map(lambda x: bool(_SCI.match(x.strip())) if isinstance(x, str) else False)
        pad = v.map(lambda x: isinstance(x, str) and x != x.strip())
        for name, mask, detail in [
                ("SENTINEL_AS_VALUE", sent, "counts as populated, means missing"),
                ("CONTROL_OR_ZEROWIDTH_CHARS", ctrl, "breaks key equality invisibly"),
                ("NBSP_IN_VALUE", nbsp, "prints as space, fails joins"),
                ("MOJIBAKE_SUSPECTED", moji, "double-encoded export upstream"),
                ("SCIENTIFIC_NOTATION_ID", sci, "Excel rewrote an identifier"),
                ("UNTRIMMED_WHITESPACE", pad, "leading or trailing spaces on values")]:
            n = int(mask.sum())
            if n:
                ex = v[mask].iloc[0]
                rows.append({"column": col, "finding": name, "rows": n,
                             "detail": "{} (example: {!r})".format(detail, str(ex)[:40])})
    if not rows:
        return pd.DataFrame({"note": ["no text-hygiene findings; the file is clean at "
                                      "the encoding layer"]})
    out = pd.DataFrame(rows).sort_values(["column", "finding"]).reset_index(drop=True)
    out.attrs["note"] = ("Every finding here corrupts joins or sums BEFORE any business "
                         "logic runs; fix at this layer first.")
    return out


def normalize_text_fields(std: pd.DataFrame, *, fields=None,
                          id_widths: dict | None = None):
    """Apply-mode: strip control and zero-width characters, replace NBSP with
    space, collapse whitespace, blank out sentinels, and restore scientific-
    notation identifiers (zero-padded to the declared width). Returns
    (new_frame, ledger_rows). Originals preserved per cell only through the
    ledger; row count and column set never change."""
    id_widths = id_widths or {"billing_npi": 10, "referring_npi": 10, "ndc": 11}
    out = std.copy()
    ledger = []
    cols = fields or [c for c in out.columns if not pd.api.types.is_numeric_dtype(out[c])]
    for col in cols:
        if col not in out.columns or pd.api.types.is_numeric_dtype(out[col]):
            continue
        v = out[col].astype("string")
        w = id_widths.get(col)

        def _fix(x):
            if not isinstance(x, str):
                return x
            y = _CTRL.sub("", x).replace(_NBSP, " ")
            y = " ".join(y.split())
            if is_sentinel(y):
                return pd.NA
            if w is not None:
                sci = fix_scientific_notation_id(y, width=w)
                if sci is not None:
                    return sci
            return y

        new = v.map(_fix)
        changed = (new.fillna("\x00") != v.fillna("\x00"))
        n = int(changed.sum())
        if n:
            out[col] = new
            ledger.append({"stage": "text_hygiene", "rule_id": "TXT-NORM",
                           "field": col, "rows_changed": n,
                           "action": "strip invisibles, blank sentinels, restore "
                                     "sci-notation ids"})
    return out, ledger
