"""
runout.py  (v34)
================

Anticipated issue: the fake cliff. The most recent service months of any claims
feed are incomplete because claims lag adjudication by weeks to months. Summed
naively, the panel's last two or three months always look like a sharp decline,
and a trend chart cut at the extract date manufactures a deceleration story the
data does not contain. The meeting line this preempts: "volume fell off in the
last quarter, is the target losing share?"

Two paths:
  with a paid date    build the lag triangle properly: completion factors by
                      service-month age from mature months, applied to restate
                      the immature tail (deterministic chain-ladder style,
                      hand-rolled).
  without a paid date cliff heuristic: flag trailing months materially below the
                      trailing-twelve median that also decline monotonically
                      into the extract edge, and restate the trend without them.

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _month(s) -> pd.Series:
    d = pd.to_datetime(s, errors="coerce")
    return d.dt.to_period("M")


def completeness_report(std: pd.DataFrame, *, allowed, date_col: str = "date",
                        paid_col: str | None = None,
                        cliff_threshold: float = 0.70) -> pd.DataFrame:
    """Per service month: observed dollars, completeness estimate, and a status
    (MATURE / INCOMPLETE_TAIL / RESTATED). Uses the paid-lag triangle when a paid
    date column exists in std (auto-detected), the cliff heuristic otherwise."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    svc = _month(std.get(date_col))
    if svc.isna().all():
        return pd.DataFrame({"note": ["no parseable service dates; runout check skipped"]})

    paid_col = paid_col or next((c for c in ("paid_date", "payment_date", "date_paid",
                                             "adjudication_date") if c in std.columns), None)
    df = pd.DataFrame({"svc": svc, "a": a.to_numpy()}).dropna(subset=["svc"])
    obs = df.groupby("svc")["a"].sum().sort_index()
    if len(obs) < 4:
        return pd.DataFrame({"note": ["fewer than four service months; runout check skipped"]})
    last = obs.index.max()

    if paid_col is not None:
        paid = _month(std[paid_col])
        lag = (paid - svc).map(lambda x: x.n if pd.notna(x) else np.nan)
        d2 = pd.DataFrame({"svc": svc, "lag": lag, "a": a.to_numpy()}).dropna()
        d2 = d2[d2["lag"] >= 0]
        max_age = int(d2["lag"].quantile(0.99)) if len(d2) else 0
        age_of = {m: (last - m).n for m in obs.index}
        mature = [m for m in obs.index if age_of[m] >= max_age]
        if len(mature) >= 3:
            mat = d2[d2["svc"].isin(mature)]
            tot = float(mat["a"].sum())
            cum = mat.groupby("lag")["a"].sum().sort_index().cumsum() / tot if tot > 0 else None
            rows = []
            for m in obs.index:
                age = age_of[m]
                cf = np.nan
                if cum is not None and age >= 0:
                    cf = float(cum.reindex(range(0, age + 1)).ffill().iloc[-1])
                if pd.isna(cf) or cf < 0.02:
                    # Younger than the first observed lag (or essentially zero
                    # completion): dividing by it manufactures a number. Say so.
                    rows.append({"service_month": str(m),
                                 "observed_allowed": round(float(obs[m]), 2),
                                 "completeness_est": (round(cf, 3) if pd.notna(cf) else np.nan),
                                 "restated_allowed": np.nan,
                                 "status": "IMMATURE (below reliable completion; excluded)"})
                    continue
                cf = min(cf, 1.0)
                restated = obs[m] / cf
                status = "MATURE" if cf >= 0.995 else "RESTATED (lag triangle)"
                rows.append({"service_month": str(m), "observed_allowed": round(float(obs[m]), 2),
                             "completeness_est": round(cf, 3),
                             "restated_allowed": round(float(restated), 2), "status": status})
            out = pd.DataFrame(rows)
            out.attrs["method"] = "paid-lag triangle"
            out.attrs["note"] = (
                "Completion factors from mature months' paid-lag pattern; immature months "
                "restated by dividing observed by completeness. Chart restated_allowed, or "
                "exclude non-MATURE months; never chart the raw tail.")
            return out

    med = float(obs.iloc[:-1].tail(12).median()) if len(obs) > 1 else float(obs.median())
    flagged = []
    for i in range(len(obs) - 1, -1, -1):
        m, v = obs.index[i], float(obs.iloc[i])
        below = med > 0 and v < cliff_threshold * med
        declining = i == len(obs) - 1 or float(obs.iloc[i]) >= float(obs.iloc[i + 1]) * 0.9999
        if below and declining:
            flagged.append(m)
        else:
            break
    flagged = set(flagged)
    rows = [{"service_month": str(m), "observed_allowed": round(float(v), 2),
             "completeness_est": np.nan,
             "restated_allowed": np.nan,
             "status": ("INCOMPLETE_TAIL (suspected claims lag)" if m in flagged else "MATURE")}
            for m, v in obs.items()]
    out = pd.DataFrame(rows)
    out.attrs["method"] = "cliff heuristic (no paid date)"
    out.attrs["n_flagged"] = len(flagged)
    out.attrs["note"] = (
        "{} trailing month(s) sit below {:.0f} percent of the trailing-twelve median and "
        "decline monotonically into the extract edge: the signature of claims lag, not demand. "
        "Exclude them from any trend, or supply a paid date column for a proper lag triangle."
        .format(len(flagged), cliff_threshold * 100))
    return out


def restated_trend(completeness: pd.DataFrame) -> pd.DataFrame:
    """Year-over-year growth computed three ways: raw (the fake cliff included),
    mature-only, and restated where the triangle ran. The spread between raw and
    the others is the deceleration the lag manufactured."""
    if completeness is None or "service_month" not in getattr(completeness, "columns", []):
        return pd.DataFrame({"note": ["completeness table unavailable"]})
    c = completeness.copy()
    c["m"] = pd.PeriodIndex(c["service_month"], freq="M")
    c["year"] = c["m"].map(lambda p: p.year)

    def _yoy(col, mask):
        g = c[mask].groupby("year")[col].sum()
        if len(g) < 2:
            return np.nan
        y0, y1 = g.index[-2], g.index[-1]
        return (g[y1] / g[y0] - 1) * 100 if g[y0] > 0 else np.nan

    raw = _yoy("observed_allowed", c["observed_allowed"].notna())
    mat = _yoy("observed_allowed", c["status"].str.startswith("MATURE"))
    has_restate = c["restated_allowed"].notna().any()
    res = _yoy("restated_allowed", c["restated_allowed"].notna()) if has_restate else np.nan
    rows = [{"basis": "raw (incomplete tail included)", "yoy_growth_pct": round(raw, 1) if pd.notna(raw) else np.nan},
            {"basis": "mature months only", "yoy_growth_pct": round(mat, 1) if pd.notna(mat) else np.nan}]
    if has_restate:
        rows.append({"basis": "restated (lag triangle)", "yoy_growth_pct": round(res, 1) if pd.notna(res) else np.nan})
    out = pd.DataFrame(rows)
    if pd.notna(raw) and pd.notna(mat):
        out.attrs["lag_artifact_pts"] = round(mat - raw, 1)
        out.attrs["note"] = ("The raw basis understates growth by {:.1f} pts versus mature "
                             "months: that gap is claims lag, not demand.".format(mat - raw))
    else:
        out.attrs["note"] = "insufficient complete periods for a year-over-year comparison"
    return out
