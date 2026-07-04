"""
cross_source.py  (v33)
======================

Evan's 1:45 decision (reuse Ryan's Komodo in/out flags so the commercial and the
Medicare/Medicaid workstreams share one inclusion universe) made structural.
Without it, "any cross-source comparison of payer mix or channel mix is confounded
by differing drug scopes." v32 built the frozen universe; this module enforces it
across sources and proves scope parity before anything is compared.

Inputs are any number of sources, each a frame already grouped to common name (or
carrying drug_common_key). The harness applies the SAME frozen universe keys to
every source, builds a per-molecule matrix of dollars by source, and flags every
molecule that is present in one source and absent in another, so a mix comparison
never silently runs on unequal scopes.

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def cross_source_matrix(sources: dict, *, universe_keys=None,
                        common_key_col: str = "drug_common_key",
                        common_name_col: str = "drug_common_name",
                        allowed_col: str = "allowed_amt") -> pd.DataFrame:
    """sources: {source_name: DataFrame} where each frame carries the common-name
    columns and an allowed column (allowed_col, falling back to 'allowed'). Returns
    one row per molecule with dollars per source, presence flags, and the frozen
    in_universe decision applied identically everywhere."""
    if not sources:
        return pd.DataFrame({"note": ["no sources supplied to the cross-source harness"]})
    per = {}
    names = {}
    for src, df in sources.items():
        if df is None or len(df) == 0:
            per[src] = {}
            continue
        key = (df[common_key_col].astype("string").fillna("")
               if common_key_col in df.columns else pd.Series("", index=df.index))
        nm = (df[common_name_col].astype("string").fillna("(unknown)")
              if common_name_col in df.columns else key)
        acol = allowed_col if allowed_col in df.columns else ("allowed" if "allowed" in df.columns else None)
        a = (pd.to_numeric(df[acol], errors="coerce").fillna(0.0)
             if acol else pd.Series(0.0, index=df.index))
        g = a.groupby(key).sum()
        per[src] = {k: float(v) for k, v in g.items() if str(k)}
        for k, n in zip(key, nm):
            if str(k):
                names.setdefault(str(k), str(n))

    keys = sorted({k for d in per.values() for k in d})
    uk = {str(k) for k in (universe_keys or set())}
    rows = []
    for k in keys:
        row = {"molecule_key": k, "molecule": names.get(k, k)}
        pres = 0
        for src in sources:
            v = per.get(src, {}).get(k, 0.0)
            row[f"{src}_allowed"] = round(v, 2)
            row[f"{src}_present"] = bool(v > 0)
            pres += int(v > 0)
        row["n_sources_present"] = pres
        row["in_universe_frozen"] = (k in uk) if uk else np.nan
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("n_sources_present").reset_index(drop=True)
    out.attrs["sources"] = list(sources)
    out.attrs["note"] = (
        "One inclusion decision (in_universe_frozen) applied identically to every source. "
        "Dollars differ by source; scope must not.")
    return out


def scope_parity_check(matrix: pd.DataFrame) -> pd.DataFrame:
    """Flag scope hazards before any cross-source chart: molecules present in some
    sources and absent in others (a mix comparison would misread absence as zero
    share), and molecules outside the frozen universe that still carry dollars
    somewhere (they must be excluded everywhere, not source by source)."""
    if matrix is None or "n_sources_present" not in getattr(matrix, "columns", []):
        return pd.DataFrame({"note": ["cross-source matrix unavailable"]})
    srcs = matrix.attrs.get("sources", [])
    n_src = len(srcs)
    partial = matrix[(matrix["n_sources_present"] >= 1)
                     & (matrix["n_sources_present"] < n_src)].copy()
    rows = []
    for _, r in partial.iterrows():
        present = [s for s in srcs if bool(r.get(f"{s}_present"))]
        absent = [s for s in srcs if not bool(r.get(f"{s}_present"))]
        rows.append({"molecule": r["molecule"],
                     "hazard": "PRESENT_IN_SOME_SOURCES_ONLY",
                     "present_in": ", ".join(present),
                     "absent_from": ", ".join(absent),
                     "in_universe_frozen": r.get("in_universe_frozen")})
    if "in_universe_frozen" in matrix.columns and matrix["in_universe_frozen"].notna().any():
        outu = matrix[(matrix["in_universe_frozen"] == False)  # noqa: E712
                      & (matrix["n_sources_present"] > 0)]
        for _, r in outu.iterrows():
            rows.append({"molecule": r["molecule"],
                         "hazard": "OUT_OF_FROZEN_UNIVERSE_BUT_OBSERVED",
                         "present_in": ", ".join(s for s in srcs if bool(r.get(f"{s}_present"))),
                         "absent_from": "",
                         "in_universe_frozen": False})
    if not rows:
        return pd.DataFrame({"note": ["scope parity clean: every molecule present in all "
                                      "sources and consistent with the frozen universe"]})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "PRESENT_IN_SOME_SOURCES_ONLY rows confound any payer-mix or channel-mix comparison. "
        "OUT_OF_FROZEN_UNIVERSE rows must be excluded from every source, not re-litigated per "
        "source; that is what the freeze is for.")
    return out
