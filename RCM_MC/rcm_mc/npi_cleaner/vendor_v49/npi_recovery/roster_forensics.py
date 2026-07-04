"""
roster_forensics.py  (v33)
==========================

The reconciliation found the master list carries 270 NPIs the client file lacks,
attributed to historical acquisitions with declining revenue, and the notes'
unstated reason for keeping them is that "dropping retired billing entities
manufactures artificial growth as volume migrates from legacy NPIs to surviving
ones." That claim is testable, and this module tests it: growth computed on the
full roster versus the surviving-only roster, with the difference quantified as
migration inflation. It also produces the entity-leakage dollar estimate (panel
dollars billed under NPIs absent from the full roster) that the four-hypothesis
deficit scorer needs.

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _digits(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return "".join(ch for ch in str(x) if ch.isdigit())


def _clean_set(npis):
    return {d for d in (_digits(x) for x in (npis or set())) if len(d) == 10}


def legacy_npi_migration(std: pd.DataFrame, *, allowed, year,
                         full_roster, surviving_roster) -> pd.DataFrame:
    """Per period: dollars on the full roster, dollars on the surviving-only
    roster, dollars on legacy NPIs (full minus surviving), and the legacy share.
    A legacy share that shrinks over time is the migration in motion."""
    full = _clean_set(full_roster)
    surv = _clean_set(surviving_roster)
    legacy = full - surv
    if not full:
        return pd.DataFrame({"note": ["no full roster supplied; migration analysis skipped"]})
    npi = std["billing_npi"].map(_digits) if "billing_npi" in std.columns else pd.Series("", index=std.index)
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    yr = pd.Series(np.asarray(year), index=std.index)
    df = pd.DataFrame({"y": yr, "npi": npi, "a": a.to_numpy()}).dropna(subset=["y"])
    rows = []
    for y, g in df.groupby("y"):
        on_full = float(g.loc[g["npi"].isin(full), "a"].sum())
        on_surv = float(g.loc[g["npi"].isin(surv), "a"].sum())
        on_leg = float(g.loc[g["npi"].isin(legacy), "a"].sum())
        rows.append({"year": y, "full_roster_allowed": round(on_full, 2),
                     "surviving_only_allowed": round(on_surv, 2),
                     "legacy_npi_allowed": round(on_leg, 2),
                     "legacy_share_pct": round(on_leg / on_full * 100, 1) if on_full > 0 else 0.0})
    out = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    out.attrs["n_legacy_npis"] = len(legacy)
    out.attrs["note"] = (
        "legacy_npi_allowed is volume on the {} NPIs the surviving list drops. If it declines "
        "while surviving volume rises, the difference is migration, not growth.".format(len(legacy)))
    return out


def _cagr(first, last, periods):
    if first <= 0 or periods < 1:
        return np.nan
    return (last / first) ** (1.0 / periods) - 1.0


def artificial_growth_test(migration: pd.DataFrame) -> pd.DataFrame:
    """CAGR on the full roster vs the surviving-only roster. The surviving-only
    figure minus the full figure is the artificial growth a dropped-legacy build
    would report. Verdict names the inflation in points."""
    if migration is None or "full_roster_allowed" not in getattr(migration, "columns", []):
        return pd.DataFrame({"note": ["migration table unavailable"]})
    m = migration.sort_values("year")
    if len(m) < 2:
        return pd.DataFrame({"note": ["need at least two periods to compute growth"]})
    _yrs = pd.to_numeric(m["year"], errors="coerce")
    p = (float(_yrs.iloc[-1] - _yrs.iloc[0])
         if _yrs.notna().all() and float(_yrs.iloc[-1] - _yrs.iloc[0]) >= 1
         else float(len(m) - 1))
    full = _cagr(float(m["full_roster_allowed"].iloc[0]),
                 float(m["full_roster_allowed"].iloc[-1]), p)
    surv = _cagr(float(m["surviving_only_allowed"].iloc[0]),
                 float(m["surviving_only_allowed"].iloc[-1]), p)
    infl = (surv - full) if (not np.isnan(surv) and not np.isnan(full)) else np.nan
    rows = [
        {"metric": "CAGR on full roster (true)", "value_pct": round(full * 100, 1) if not np.isnan(full) else np.nan},
        {"metric": "CAGR on surviving-only roster", "value_pct": round(surv * 100, 1) if not np.isnan(surv) else np.nan},
        {"metric": "artificial growth from dropping legacy NPIs (pts)",
         "value_pct": round(infl * 100, 1) if not np.isnan(infl) else np.nan},
    ]
    out = pd.DataFrame(rows)
    out.attrs["verdict"] = (
        "surviving-only roster inflates growth by {:.1f} pts; keep the legacy NPIs".format(infl * 100)
        if not np.isnan(infl) and infl > 0.001 else
        "no material inflation detected; roster choice does not move growth")
    out.attrs["note"] = out.attrs["verdict"]
    return out


def entity_leakage_estimate(std: pd.DataFrame, *, allowed, full_roster) -> pd.DataFrame:
    """Dollars in the panel billed under NPIs absent from the full roster: the
    candidate entity-leakage mass, and the dollar signal the deficit scorer's
    entity-roster hypothesis needs. In a target-scoped panel these rows are either
    roster gaps or attribution errors; either way they are the leakage ceiling."""
    full = _clean_set(full_roster)
    if not full:
        return pd.DataFrame({"note": ["no full roster supplied; leakage estimate skipped"]})
    npi = std["billing_npi"].map(_digits) if "billing_npi" in std.columns else pd.Series("", index=std.index)
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    mask = ~npi.isin(full) & (npi.str.len() == 10)
    leak = float(a[mask].sum())
    tot = float(a.sum())
    by = (pd.DataFrame({"npi": npi[mask], "a": a[mask]})
          .groupby("npi")["a"].sum().sort_values(ascending=False).head(15))
    rows = [{"line": "panel total", "amount": round(tot, 2)},
            {"line": "on NPIs absent from full roster (leakage ceiling)", "amount": round(leak, 2)},
            {"line": "leakage share of panel (pct)",
             "amount": round(leak / tot * 100, 1) if tot > 0 else 0.0}]
    for k, v in by.items():
        rows.append({"line": f"  top absent NPI {k}", "amount": round(float(v), 2)})
    out = pd.DataFrame(rows)
    out.attrs["entity_leakage_dollars"] = round(leak, 2)
    out.attrs["note"] = (
        "The leakage ceiling feeds the entity-roster hypothesis in the deficit diagnosis. "
        "Top absent NPIs are the candidates to resolve first.")
    return out
