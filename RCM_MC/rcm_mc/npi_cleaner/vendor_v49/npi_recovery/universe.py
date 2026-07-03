"""
universe.py  (v32)
==================

Two disciplines the notes attached to the spend floor, made operational.

First, the floor (about $1M) is applied at the DRUG grain and only after the
grouper, so no molecule is dropped merely because its volume is shredded across
codes. Second, and this is the part that protects every cross-source comparison:
the universe is defined ONCE on total panel spend and frozen, then reapplied to
Komodo commercial, Komodo government, and VRDC identically. Without the freeze a
drug near the floor flickers in and out between sources and manufactures spurious
mix shifts, which is exactly the failure the vendor-agnostic view is retreating
to avoid.

The module also separates two different reasons a drug leaves the universe:

  BELOW_FLOOR         quantitative: molecule spend under the floor. The excluded
                      tail is quantified ("X% of spend") so the cut survives
                      challenge.
  EXCLUDED_MARKET_DEF qualitative: a market-definition act, e.g. striking Keytruda
                      because it is hospital/clinic buy-and-bill oncology absent
                      from the home/AIC channel. These go on a documented register
                      with a one-line rationale each, because it is the first thing
                      a reader clicks on.

Deterministic and offline.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from . import common_name as _cn


def load_market_exclusions(ref_dir=None):
    """Return [(token, rationale, source)] from the seed plus any
    *market*exclusion*user*.csv override."""
    ref = Path(ref_dir or config.REF_DIR)
    frames = []
    seed = ref / "market_exclusions_seed.csv"
    if seed.exists():
        frames.append(pd.read_csv(seed, dtype=str))
    for extra in sorted(ref.glob("*market*exclusion*user*.csv")):
        try:
            frames.append(pd.read_csv(extra, dtype=str))
        except Exception:
            pass
    if not frames:
        return []
    df = pd.concat(frames, ignore_index=True).fillna("")
    seen, out = set(), []
    for _, r in df.iterrows():
        tok = str(r.get("molecule_token", "")).strip().lower()
        if not tok or tok in seen:
            continue
        seen.add(tok)
        out.append((tok, str(r.get("rationale", "")), str(r.get("source", "Market definition"))))
    return out


def _molecule_rollup(std_named, allowed, common_name_col, common_key_col):
    name = (std_named[common_name_col].astype("string").fillna("(unknown)")
            if common_name_col in std_named.columns else pd.Series("(unknown)", index=std_named.index))
    key = (std_named[common_key_col].astype("string").fillna("")
           if common_key_col in std_named.columns else name.str.lower())
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    df = pd.DataFrame({"name": name.to_numpy(), "key": key.to_numpy(), "allowed": a.to_numpy()})
    g = (df.groupby(["key", "name"], dropna=False)["allowed"]
         .agg(["sum", "size"]).reset_index()
         .rename(columns={"sum": "allowed", "size": "rows"}))
    return g


def _excluded_by_market(name, key, exclusions):
    nm = f"{name} {key}".lower()
    for tok, rationale, source in exclusions:
        if tok and re.search(r"\b" + re.escape(tok) + r"\b", nm):
            return rationale or f"market exclusion: {tok}", source
    return None, None


def define_universe(std_named: pd.DataFrame, *, allowed, floor: float = 1_000_000.0,
                    common_name_col: str = "drug_common_name",
                    common_key_col: str = "drug_common_key",
                    exclusions=None, ref_dir=None) -> pd.DataFrame:
    """Define the universe once on total panel spend at the molecule grain. Returns
    one row per molecule with total allowed, status (IN_UNIVERSE / BELOW_FLOOR /
    EXCLUDED_MARKET_DEF), and a rationale. The IN_UNIVERSE set is the frozen
    universe to reapply to every other source."""
    exclusions = exclusions if exclusions is not None else load_market_exclusions(ref_dir)
    g = _molecule_rollup(std_named, allowed, common_name_col, common_key_col)
    if g.empty:
        return pd.DataFrame({"note": ["no molecules to scope; empty panel"]})

    total = float(g["allowed"].sum())
    statuses, rationales, sources = [], [], []
    for _, r in g.iterrows():
        exc, src = _excluded_by_market(r["name"], r["key"], exclusions)
        if exc:
            statuses.append("EXCLUDED_MARKET_DEF"); rationales.append(exc); sources.append(src)
        elif float(r["allowed"]) >= floor:
            statuses.append("IN_UNIVERSE"); rationales.append(""); sources.append("")
        else:
            statuses.append("BELOW_FLOOR")
            rationales.append(f"molecule spend {r['allowed']:.0f} below floor {floor:.0f}")
            sources.append("Spend floor")
    g["status"] = statuses
    g["rationale"] = rationales
    g["exclusion_source"] = sources
    g["share_of_panel_pct"] = np.where(total > 0, np.round(g["allowed"] / total * 100, 2), 0.0)
    g = g.sort_values(["status", "allowed"], ascending=[True, False]).reset_index(drop=True)
    g.attrs["floor"] = floor
    g.attrs["panel_total"] = round(total, 2)
    g.attrs["note"] = (
        "Universe defined once on total panel spend at the molecule grain (post-grouper). "
        "IN_UNIVERSE is the frozen set to reapply to every other source via "
        "apply_frozen_universe, so drugs do not flicker in and out between Komodo and VRDC. "
        "BELOW_FLOOR is quantitative; EXCLUDED_MARKET_DEF is a documented market-definition act.")
    return g


def frozen_universe_keys(universe: pd.DataFrame) -> set:
    """The set of molecule keys that define the frozen universe (IN_UNIVERSE only)."""
    if universe is None or "status" not in getattr(universe, "columns", []):
        return set()
    return set(universe.loc[universe["status"] == "IN_UNIVERSE", "key"].astype(str))


def apply_frozen_universe(std_named: pd.DataFrame, universe, *,
                          common_key_col: str = "drug_common_key") -> pd.DataFrame:
    """Tag rows of any source against the frozen universe defined elsewhere, so the
    in/out decision is identical across Komodo commercial, Komodo government, and
    VRDC. Adds `in_universe`. Never re-derives the floor on this source."""
    keys = frozen_universe_keys(universe) if not isinstance(universe, (set, frozenset)) else set(universe)
    out = std_named.copy()
    key = (out[common_key_col].astype("string").fillna("")
           if common_key_col in out.columns else pd.Series([""] * len(out), index=out.index))
    out["in_universe"] = key.isin(keys).to_numpy()
    out.attrs["note"] = (
        "in_universe applies the frozen IN_UNIVERSE molecule set from the master definition; "
        "the floor is not recomputed on this source, which is what keeps the universe stable "
        "across sources.")
    return out


def excluded_tail_summary(universe: pd.DataFrame) -> pd.DataFrame:
    """Quantify what the floor removes, so the universe definition survives
    challenge: molecules below floor, their count, and their share of panel
    spend."""
    if universe is None or "status" not in getattr(universe, "columns", []):
        return pd.DataFrame({"note": ["universe unavailable"]})
    total = float(universe["allowed"].sum())
    rows = []
    for st in ("IN_UNIVERSE", "BELOW_FLOOR", "EXCLUDED_MARKET_DEF"):
        d = universe[universe["status"] == st]
        rows.append({"status": st, "n_molecules": int(len(d)),
                     "allowed": round(float(d["allowed"].sum()), 2),
                     "share_of_panel_pct": round(float(d["allowed"].sum()) / total * 100, 2) if total > 0 else 0.0})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "The BELOW_FLOOR share is the excluded tail to report alongside the universe "
        "definition ('drugs below floor represent X% of spend').")
    return out


def exclusion_register(universe: pd.DataFrame) -> pd.DataFrame:
    """The documented market-definition exclusion list, top dollar first, with a
    one-line rationale each. This is the audit artifact a reader clicks on."""
    if universe is None or "status" not in getattr(universe, "columns", []):
        return pd.DataFrame({"note": ["universe unavailable"]})
    d = universe[universe["status"] == "EXCLUDED_MARKET_DEF"].copy()
    if d.empty:
        return pd.DataFrame({"note": ["no market-definition exclusions applied"]})
    d = d.sort_values("allowed", ascending=False)
    out = d[["name", "allowed", "share_of_panel_pct", "rationale", "exclusion_source"]].rename(
        columns={"name": "molecule"}).reset_index(drop=True)
    out.attrs["note"] = (
        "Market-definition exclusions are deliberate scope decisions, not data cleaning. Each "
        "carries a one-line rationale so the cut is defensible when challenged.")
    return out
