"""
market_view.py  (v33)
=====================

Joe's salvage at 0:52: "the vendor-agnostic market view survives." These are the
three analyses that view runs on, built so they cannot be bent by the failures the
report names.

  biosimilar_adoption   per molecule-year, originator J-code dollars versus
                        biosimilar Q-code dollars and the adoption share. Runs on
                        the grouped panel, so entry mid-window is a real trend,
                        not an inclusion artifact.
  asp_rate_position     panel allowed-per-unit against the ASP payment limit per
                        code, the unit-reimbursement-dynamics read.
  floor_sensitivity     the universe at several floors (the notes flag $1M as
                        "e.g."): molecule count, spend share, and top-10 stability
                        per floor, so the floor is either pinned or shown not to
                        matter.

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .calibration import load_kv_csv


def biosimilar_adoption(std_named: pd.DataFrame, *, allowed, year,
                        hcpcs_col: str = "hcpcs",
                        common_name_col: str = "drug_common_name") -> pd.DataFrame:
    """Per molecule-year: originator dollars (J-codes), biosimilar dollars
    (Q5xxx codes), and the biosimilar share. Only molecules that carry both code
    classes somewhere in the panel are shown."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    yr = pd.Series(np.asarray(year), index=std_named.index)
    hc = (std_named[hcpcs_col].astype("string").fillna("").str.strip().str.upper()
          if hcpcs_col in std_named.columns else pd.Series("", index=std_named.index))
    name = (std_named[common_name_col].astype("string").fillna("(unknown)")
            if common_name_col in std_named.columns
            else pd.Series("(unknown)", index=std_named.index))
    is_bio = hc.str.match(r"^Q5\d{3}$").fillna(False)
    df = pd.DataFrame({"m": name.to_numpy(), "y": yr.to_numpy(),
                       "bio": np.where(is_bio, a, 0.0),
                       "orig": np.where(~is_bio & (hc != "").to_numpy(), a, 0.0)})
    df = df.dropna(subset=["y"])
    both = {m for m, g in df.groupby("m")
            if float(g["bio"].sum()) > 0 and float(g["orig"].sum()) > 0}
    if not both:
        return pd.DataFrame({"note": ["no molecule carries both originator and biosimilar "
                                      "codes in the panel"]})
    g = (df[df["m"].isin(both)].groupby(["m", "y"]).sum(numeric_only=True).reset_index()
         .rename(columns={"m": "molecule", "y": "year",
                          "orig": "originator_allowed", "bio": "biosimilar_allowed"}))
    tot = g["originator_allowed"] + g["biosimilar_allowed"]
    g["biosimilar_share_pct"] = np.where(tot > 0, g["biosimilar_allowed"] / tot * 100, 0.0).round(1)
    for c in ("originator_allowed", "biosimilar_allowed"):
        g[c] = g[c].round(2)
    g = g.sort_values(["molecule", "year"]).reset_index(drop=True)
    g.attrs["note"] = (
        "Computed on the grouped molecule, so a Q-code entering mid-window shows as adoption, "
        "not as spend leaving the universe.")
    return g


def asp_rate_position(std: pd.DataFrame, *, allowed, units, asp_limits,
                      hcpcs_col: str = "hcpcs", band: float = 0.05,
                      min_units: float = 1.0) -> pd.DataFrame:
    """Per code: panel allowed-per-unit against the ASP payment limit
    (asp_limits: {hcpcs: dollars per billing unit}). Position is ABOVE / AT /
    BELOW inside a plus-or-minus band."""
    limits = {str(k).strip().upper(): float(v) for k, v in load_kv_csv(asp_limits).items()}
    if not limits:
        return pd.DataFrame({"note": ["supply asp_limits (hcpcs -> dollars per unit) to "
                                      "position panel rates against the ASP payment limit"]})
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    u = pd.to_numeric(units, errors="coerce").fillna(0.0)
    hc = (std[hcpcs_col].astype("string").fillna("").str.strip().str.upper()
          if hcpcs_col in std.columns else pd.Series("", index=std.index))
    df = pd.DataFrame({"h": hc.to_numpy(), "a": a.to_numpy(), "u": u.to_numpy()})
    g = df[df["h"] != ""].groupby("h").sum(numeric_only=True).reset_index()
    rows = []
    for _, r in g.iterrows():
        h = r["h"]
        if h not in limits or r["u"] < min_units:
            continue
        rate = r["a"] / r["u"]
        lim = limits[h]
        ratio = rate / lim if lim > 0 else np.nan
        pos = ("AT" if abs(ratio - 1.0) <= band else ("ABOVE" if ratio > 1.0 else "BELOW")) \
            if not np.isnan(ratio) else "NO_LIMIT"
        rows.append({"hcpcs": h, "panel_allowed": round(float(r["a"]), 2),
                     "panel_units": round(float(r["u"]), 1),
                     "panel_rate_per_unit": round(rate, 4),
                     "asp_limit_per_unit": round(lim, 4),
                     "rate_vs_limit": round(ratio, 3),
                     "position": pos})
    if not rows:
        return pd.DataFrame({"note": ["no panel codes matched the supplied ASP limits"]})
    out = pd.DataFrame(rows).sort_values("panel_allowed", ascending=False).reset_index(drop=True)
    out.attrs["note"] = (
        "Panel allowed-per-unit vs the ASP payment limit; ABOVE at scale is the rate-positioning "
        "signal, BELOW suggests unit-basis or payer-mix effects worth a look before charting.")
    return out


def floor_sensitivity(std_named: pd.DataFrame, *, allowed,
                      floors=(500_000.0, 1_000_000.0, 2_000_000.0),
                      base_floor: float = 1_000_000.0, ref_dir=None) -> pd.DataFrame:
    """The universe at each candidate floor: molecules in, spend share in, and
    top-10 stability (overlap with the base floor's top 10). If nothing moves, the
    'e.g. $1M' floor is defensible as stated; if the top 10 flips, the floor is a
    real decision and needs pinning."""
    from . import universe as _uni
    rows = []
    base_top = None
    results = {}
    for f in sorted(set(list(floors) + [base_floor])):
        u = _uni.define_universe(std_named, allowed=allowed, floor=float(f), ref_dir=ref_dir)
        if "status" not in u.columns:
            return pd.DataFrame({"note": ["universe definition unavailable for floor test"]})
        inn = u[u["status"] == "IN_UNIVERSE"]
        top10 = set(inn.sort_values("allowed", ascending=False).head(10)["key"])
        results[f] = (inn, top10)
        if abs(f - base_floor) < 1e-6:
            base_top = top10
    total = float(pd.to_numeric(allowed, errors="coerce").fillna(0.0).sum())
    for f in sorted(results):
        inn, top10 = results[f]
        inter = len(top10 & base_top) if base_top else 0
        union = len(top10 | base_top) if base_top else 0
        rows.append({"floor": f, "n_molecules_in": int(len(inn)),
                     "spend_share_in_pct": round(float(inn["allowed"].sum()) / total * 100, 1) if total > 0 else 0.0,
                     "top10_overlap_with_base": round(inter / union, 2) if union else np.nan})
    out = pd.DataFrame(rows)
    stable = bool(all(abs(x - 1.0) < 1e-9 for x in out["top10_overlap_with_base"].dropna()))
    out.attrs["verdict"] = ("floor choice does not move the top 10; the stated floor is safe"
                            if stable else
                            "the top 10 changes with the floor; pin the floor before charting")
    out.attrs["note"] = out.attrs["verdict"]
    return out
