"""
payer_normalizer.py  (v34)
==========================

Anticipated issue: payer mix on raw strings. The same payer arrives as BCBSTX,
BCBS TX, Blue Cross Blue Shield of Texas, and HCSC; United arrives as UHC, UMR,
Optum, and Oxford. A payer-mix chart on raw strings understates concentration,
splits the anchor payer across three bars, and any payer HHI computed on it is
fiction. The meeting line this preempts: "why is the top payer only twelve
percent, the target says BCBS is half their book."

Longest-alias-first token matching against a seed table (payer_aliases_seed.csv,
extendable via the payer_aliases flag), rolled up to parent organizations. The
audit shows exactly which strings remapped where and how much money moved, so
the normalization is inspectable, never silent.

Deterministic and offline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _clean(s: str) -> str:
    out = []
    for ch in str(s).upper():
        out.append(ch if (ch.isalnum() or ch == " ") else " ")
    return " ".join("".join(out).split())


def load_alias_table(path_or_obj=None, *, ref_dir=None) -> list[tuple[str, str]]:
    """Alias -> parent pairs, longest alias first. Accepts a CSV path, a frame,
    or a dict; falls back to the shipped seed under ref_dir."""
    df = None
    if isinstance(path_or_obj, dict):
        df = pd.DataFrame({"alias": list(path_or_obj), "parent": list(path_or_obj.values())})
    elif isinstance(path_or_obj, pd.DataFrame):
        df = path_or_obj
    elif path_or_obj is not None and Path(str(path_or_obj)).exists():
        df = pd.read_csv(path_or_obj)
    if df is None and ref_dir is not None:
        p = Path(ref_dir) / "payer_aliases_seed.csv"
        if p.exists():
            df = pd.read_csv(p)
    if df is None or df.empty:
        return []
    cols = {c.strip().lower(): c for c in df.columns}
    ac, pc = cols.get("alias", df.columns[0]), cols.get("parent", df.columns[-1])
    pairs = [(_clean(r[ac]), str(r[pc]).strip()) for _, r in df.iterrows() if str(r[ac]).strip()]
    return sorted(pairs, key=lambda kv: -len(kv[0]))


def normalize_payers(std: pd.DataFrame, *, allowed, payer_col: str = "payer",
                     aliases=None, ref_dir=None) -> pd.DataFrame:
    """Audit of raw payer string -> parent org, with dollars. Unmatched strings
    keep themselves as parent (title-cased), flagged UNMAPPED so the seed can be
    extended rather than the tail silently absorbed."""
    if payer_col not in std.columns:
        return pd.DataFrame({"note": ["no payer column in the panel"]})
    table = load_alias_table(aliases, ref_dir=ref_dir)
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    raw = std[payer_col].astype("string").fillna("(blank)")
    cleaned = raw.map(_clean)

    def _map(c: str) -> tuple[str, bool]:
        padded = f" {c} "
        for alias, parent in table:
            if f" {alias} " in padded:
                return parent, True
        return (c.title() if c else "(blank)"), False

    uniq = {c: _map(c) for c in cleaned.unique()}
    parent = cleaned.map(lambda c: uniq[c][0])
    mapped = cleaned.map(lambda c: uniq[c][1])
    audit = (pd.DataFrame({"raw_payer": raw, "parent_org": parent,
                           "mapped": mapped, "allowed": a})
             .groupby(["raw_payer", "parent_org", "mapped"], as_index=False)["allowed"].sum()
             .sort_values("allowed", ascending=False).reset_index(drop=True))
    audit["allowed"] = audit["allowed"].round(2)
    audit["status"] = np.where(audit["mapped"], "MAPPED", "UNMAPPED (extend the alias seed)")
    audit = audit.drop(columns=["mapped"])
    n_from = int(raw.nunique())
    n_to = int(parent.nunique())
    moved = float(a[mapped & (cleaned != parent.map(_clean))].sum())
    audit.attrs["parent_series"] = parent
    audit.attrs["distinct_raw"] = n_from
    audit.attrs["distinct_parents"] = n_to
    audit.attrs["dollars_remapped"] = round(moved, 2)
    audit.attrs["note"] = (
        "{} raw payer strings roll to {} parent organizations; {} dollars remapped. Compute "
        "every payer mix and payer HHI on parent_org, never on the raw string.".format(
            n_from, n_to, round(moved, 2)))
    return audit


def payer_mix_normalized(std: pd.DataFrame, *, allowed, payer_col: str = "payer",
                         aliases=None, ref_dir=None, top_n: int = 12) -> pd.DataFrame:
    """Top parents by dollars with shares, the chart-ready payer mix."""
    audit = normalize_payers(std, allowed=allowed, payer_col=payer_col,
                             aliases=aliases, ref_dir=ref_dir)
    if "parent_series" not in getattr(audit, "attrs", {}):
        return audit
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    parent = audit.attrs["parent_series"]
    g = a.groupby(parent).sum().sort_values(ascending=False)
    tot = float(g.sum())
    out = pd.DataFrame({"parent_org": g.index, "allowed": g.round(2).to_numpy(),
                        "share_pct": (g / tot * 100).round(1).to_numpy() if tot > 0 else 0.0}).head(top_n)
    out.attrs["note"] = "Mix on normalized parent organizations."
    return out
