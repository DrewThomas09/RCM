"""
modifier_economics.py  (v34)
============================

Anticipated issue: modifier counts with no dollars behind them. The repair step
already parses JG/TB (340B-acquired) and JW/JZ (discarded-drug) modifiers off the
HCPCS field and stamps mod_340b and mod_wastage booleans, and the pipeline
reports the ROW counts. Nobody has priced them. A reader will ask what share of
the book is 340B-touched (margin conversation) and how many dollars are billed
wastage (reimbursement for drug never infused), and today the honest answer is a
row count.

Reads the stamped booleans when present, falls back to a raw modifier column
(JG, TB, JW, JZ tokens) and splits JW from JZ when it can. Deterministic and
offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_MOD_CANDIDATES = ("modifier", "modifiers", "mod", "modifier_1", "mod1", "hcpcs_modifier")


def _token_flags(std: pd.DataFrame):
    col = next((c for c in _MOD_CANDIDATES if c in std.columns), None)
    if col is None:
        return None
    toks = (std[col].astype("string").fillna("").str.upper()
            .str.replace(r"[^A-Z0-9]", " ", regex=True).str.split())
    has = lambda code: toks.map(lambda t: code in t if isinstance(t, list) else False)
    return {"m340": (has("JG") | has("TB")), "jw": has("JW"), "jz": has("JZ")}


def modifier_economics(std: pd.DataFrame, *, allowed) -> pd.DataFrame:
    """Dollars behind the modifier flags: 340B-flagged share, wastage-flagged
    dollars, and JW versus JZ split when a raw modifier column allows it."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    tot = float(a.sum())
    tok = _token_flags(std)
    m340 = (std["mod_340b"].fillna(False).astype(bool)
            if "mod_340b" in std.columns else (tok["m340"] if tok else None))
    mwaste = (std["mod_wastage"].fillna(False).astype(bool)
              if "mod_wastage" in std.columns else None)
    if m340 is None and mwaste is None and tok is None:
        return pd.DataFrame({"note": ["no modifier flags or modifier column in the panel; "
                                      "340B and wastage economics need JG/TB and JW/JZ"]})
    rows = [{"metric": "panel allowed", "value": round(tot, 2)}]
    d340 = float(a[m340].sum()) if m340 is not None else np.nan
    if m340 is not None:
        rows += [{"metric": "340B-flagged dollars (JG or TB)", "value": round(d340, 2)},
                 {"metric": "340B-flagged share pct",
                  "value": round(d340 / tot * 100, 1) if tot > 0 else 0.0}]
    if tok is not None:
        djw = float(a[tok["jw"]].sum())
        rows += [{"metric": "discarded-drug dollars (JW lines)", "value": round(djw, 2)},
                 {"metric": "wastage share pct",
                  "value": round(djw / tot * 100, 1) if tot > 0 else 0.0},
                 {"metric": "rows attesting zero discard (JZ)", "value": int(tok["jz"].sum())}]
        dwaste = djw
    elif mwaste is not None:
        dwaste = float(a[mwaste].sum())
        rows += [{"metric": "wastage-flagged dollars (JW or JZ stamped)", "value": round(dwaste, 2)},
                 {"metric": "wastage-flagged share pct",
                  "value": round(dwaste / tot * 100, 1) if tot > 0 else 0.0},
                 {"metric": "JW vs JZ split", "value": "unavailable (boolean stamp only; "
                  "supply a raw modifier column to separate discarded dollars from attestation)"}]
    else:
        dwaste = np.nan
    out = pd.DataFrame(rows)
    out.attrs["dollars_340b"] = (round(d340, 2) if m340 is not None else None)
    out.attrs["dollars_wastage_flagged"] = (round(dwaste, 2) if not np.isnan(dwaste) else None)
    out.attrs["note"] = (
        "JG/TB mark 340B-acquired drug, JW is billed discarded amount, JZ attests no discard. "
        "340B share reframes any margin conversation; JW dollars are reimbursement for drug "
        "never infused and belong out of any per-patient economics.")
    return out
