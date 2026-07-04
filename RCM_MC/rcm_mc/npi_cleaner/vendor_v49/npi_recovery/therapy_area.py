"""
therapy_area.py  (v32)
======================

Mapping spend to the client's own three-letter therapy codes buys apples-to-apples
comparability with management's reporting, which is what makes validation
meaningful. The headline validation is the acute-share check: a computed acute
share inside the client's stated band (the notes' 22% inside a 20 to 26% band) is
a JOINT test of the grouper and the mapping, because acute share is computed on
grouped spend and an error in either layer pushes it out of band.

Two honesty rails the notes attached:

  * the band is presumably a revenue figure while the claims number is allowed
    spend, so in-band shows consistency, not truth; the verdict says so.
  * dominant-therapy assignment for a multi-mapped drug is fine in aggregate but
    must be hand-checked for high-spend molecules that straddle the acute/chronic
    line or the oncology-exclusion line. Rituximab-class is the classic case where
    one dominant-code decision determines whether a nine-figure molecule is in or
    out of the universe. Those rows are surfaced, not silently resolved.

The chronic book is then subdivided IVIG versus rare/orphan, mirroring how the
asset is underwritten (IG as the volume engine and shared risk, rare/orphan as the
moat). The rare/orphan list is an external choice and is documented, because FDA
orphan designation is neither necessary nor sufficient for rare/orphan infusion
economics.

Deterministic and offline. Accepts a client override so the real client codes
replace the shipped seed.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config


def load_therapy_map(ref_dir=None, client_map_path=None):
    """Return a list of (token, therapy_code, acute_chronic, chronic_subclass,
    straddle_note) from the seed plus an optional client override (same schema).
    Client rows win on token collision."""
    ref = Path(ref_dir or config.REF_DIR)
    frames = []
    seed = ref / "therapy_area_seed.csv"
    if seed.exists():
        frames.append(pd.read_csv(seed, dtype=str).assign(_prio=0))
    paths = []
    if client_map_path:
        paths.append(Path(client_map_path))
    paths += sorted(ref.glob("*therapy*area*user*.csv"))
    for p in paths:
        try:
            frames.append(pd.read_csv(p, dtype=str).assign(_prio=1))
        except Exception:
            pass
    if not frames:
        return []
    df = pd.concat(frames, ignore_index=True).fillna("").sort_values("_prio")
    seen, out = set(), []
    for _, r in df.iterrows():
        tok = str(r.get("molecule_token", "")).strip().lower()
        if not tok or tok in seen:
            continue
        seen.add(tok)
        out.append((
            tok,
            str(r.get("therapy_code", "")).strip().upper() or "OTH",
            str(r.get("acute_chronic", "")).strip().lower() or "unknown",
            str(r.get("chronic_subclass", "")).strip().lower(),
            str(r.get("straddle_note", "")).strip(),
        ))
    return out


def _match(name_norm, tmap):
    for tok, code, ac, sub, note in tmap:
        if tok and re.search(r"\b" + re.escape(tok) + r"\b", name_norm):
            return code, ac, sub, note
    return "OTH", "unknown", "", ""


def assign_therapy_area(std_named: pd.DataFrame, therapy_map=None, ref_dir=None,
                        common_name_col: str = "drug_common_name",
                        common_key_col: str = "drug_common_key") -> pd.DataFrame:
    """Per row: therapy_code, acute_chronic, chronic_subclass, and straddle_note.
    Matching is on the resolved common name / key so it runs after the grouper."""
    tmap = therapy_map if therapy_map is not None else load_therapy_map(ref_dir)
    out = std_named.copy()
    n = len(out)
    name = (out[common_name_col].astype("string").fillna("")
            if common_name_col in out.columns else pd.Series([""] * n, index=out.index))
    key = (out[common_key_col].astype("string").fillna("")
           if common_key_col in out.columns else pd.Series([""] * n, index=out.index))

    codes, acs, subs, notes = [], [], [], []
    for i in range(n):
        nm = f"{name.iat[i]} {key.iat[i]}".lower()
        code, ac, sub, note = _match(nm, tmap)
        codes.append(code); acs.append(ac); subs.append(sub); notes.append(note)
    out["therapy_code"] = codes
    out["acute_chronic"] = acs
    out["chronic_subclass"] = subs
    out["straddle_note"] = notes
    return out


def acute_share_check(std_tagged: pd.DataFrame, *, allowed,
                      band=(0.20, 0.26)) -> pd.DataFrame:
    """Compute the acute share on grouped spend and test it against the client's
    band. This is the joint test of grouper and mapping."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    ac = (std_tagged["acute_chronic"].astype("string").fillna("unknown")
          if "acute_chronic" in std_tagged.columns else pd.Series("unknown", index=std_tagged.index))
    df = pd.DataFrame({"ac": ac.to_numpy(), "allowed": a.to_numpy()})
    by = df.groupby("ac")["allowed"].sum()
    total = float(by.sum())
    known = float(by.get("acute", 0.0) + by.get("chronic", 0.0))
    acute = float(by.get("acute", 0.0))
    acute_share = (acute / known) if known > 0 else np.nan

    lo, hi = band
    in_band = bool(known > 0 and lo <= acute_share <= hi)
    rows = [
        {"metric": "acute allowed", "value": round(acute, 2)},
        {"metric": "chronic allowed", "value": round(float(by.get("chronic", 0.0)), 2)},
        {"metric": "unknown allowed (excluded from share)", "value": round(float(by.get("unknown", 0.0)), 2)},
        {"metric": "acute share of acute+chronic (%)",
         "value": (round(acute_share * 100, 1) if not np.isnan(acute_share) else np.nan)},
        {"metric": f"client band (%)", "value": f"{lo*100:.0f}-{hi*100:.0f}"},
        {"metric": "in band", "value": in_band},
    ]
    out = pd.DataFrame(rows)
    out.attrs["in_band"] = in_band
    out.attrs["acute_share_pct"] = (round(acute_share * 100, 1) if not np.isnan(acute_share) else None)
    out.attrs["note"] = (
        "Acute share is computed on grouped spend, so in-band is a joint pass of the grouper "
        "and the therapy mapping. The band is a revenue figure while this is allowed spend, so "
        "in-band demonstrates consistency, not truth.")
    return out


def dominant_therapy_review(std_tagged: pd.DataFrame, *, allowed,
                            top_n: int = 25) -> pd.DataFrame:
    """High-spend molecules that carry a straddle note (acute/chronic or oncology
    line), for hand-check before the dominant-code decision is trusted. Rituximab
    is the archetype: one decision moves a nine-figure molecule in or out."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    name = (std_tagged["drug_common_name"].astype("string").fillna("(unknown)")
            if "drug_common_name" in std_tagged.columns else pd.Series("(unknown)", index=std_tagged.index))
    note = (std_tagged["straddle_note"].astype("string").fillna("")
            if "straddle_note" in std_tagged.columns else pd.Series("", index=std_tagged.index))
    code = (std_tagged["therapy_code"].astype("string").fillna("")
            if "therapy_code" in std_tagged.columns else pd.Series("", index=std_tagged.index))
    df = pd.DataFrame({"molecule": name.to_numpy(), "therapy_code": code.to_numpy(),
                       "straddle_note": note.to_numpy(), "allowed": a.to_numpy()})
    df = df[df["straddle_note"].str.len() > 0]
    if df.empty:
        return pd.DataFrame({"note": ["no straddle molecules flagged in the panel"]})
    g = (df.groupby(["molecule", "therapy_code", "straddle_note"])["allowed"]
         .sum().reset_index().sort_values("allowed", ascending=False).head(top_n))
    g["allowed"] = g["allowed"].round(2)
    g.attrs["note"] = (
        "These molecules straddle the acute/chronic or oncology-exclusion line; the "
        "dominant-therapy code assigned here should be hand-checked because the decision can "
        "move a very large molecule in or out of the universe.")
    return g.reset_index(drop=True)


def chronic_subdivision(std_tagged: pd.DataFrame, *, allowed) -> pd.DataFrame:
    """Subdivide the chronic book into IVIG versus rare/orphan versus other
    chronic, mirroring the underwriting (IG the volume engine, rare/orphan the
    moat)."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    ac = (std_tagged["acute_chronic"].astype("string").fillna("unknown")
          if "acute_chronic" in std_tagged.columns else pd.Series("unknown", index=std_tagged.index))
    sub = (std_tagged["chronic_subclass"].astype("string").fillna("")
           if "chronic_subclass" in std_tagged.columns else pd.Series("", index=std_tagged.index))
    df = pd.DataFrame({"ac": ac.to_numpy(), "sub": sub.to_numpy(), "allowed": a.to_numpy()})
    chronic = df[df["ac"] == "chronic"].copy()
    if chronic.empty:
        return pd.DataFrame({"note": ["no chronic spend to subdivide"]})
    chronic["sub"] = chronic["sub"].replace({"": "other_chronic"})
    label = {"ivig": "IVIG (volume engine / shared risk)",
             "rare_orphan": "Rare / orphan (moat)",
             "other_chronic": "Other chronic"}
    g = chronic.groupby("sub")["allowed"].sum()
    tot = float(g.sum())
    rows = [{"chronic_subclass": label.get(k, k), "allowed": round(float(v), 2),
             "share_of_chronic_pct": round(float(v) / tot * 100, 1) if tot > 0 else 0.0}
            for k, v in g.sort_values(ascending=False).items()]
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "IVIG vs rare/orphan mirrors how the asset is underwritten. The rare/orphan list is an "
        "external choice and is documented; FDA orphan designation is neither necessary nor "
        "sufficient for rare/orphan infusion economics.")
    return out
