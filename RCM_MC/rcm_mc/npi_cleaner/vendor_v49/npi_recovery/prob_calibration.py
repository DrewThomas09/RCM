"""
prob_calibration.py  (v43)
==========================

Measures whether a recovery method's stated confidence means what it says. Not to
be confused with calibration.py (v33), which is about Komodo FFS coverage vs a
VRDC census. This module is about predicted-probability calibration.

The toolkit already reports a confidence per recovered NPI and already runs a
k-fold back-test that masks known NPIs and checks whether the top-1 guess matched.
That back-test yields a labeled table: per held-out row, the stated confidence and
the 0/1 outcome. This module turns that into the numbers that decide trust:

  reliability curve   bin by stated confidence, compare mean stated confidence in
                      each bin to the actual hit rate. Calibrated sits on the
                      diagonal.
  Brier score         mean squared error between confidence and the 0/1 outcome.
                      Lower is better.
  ECE                 population-weighted average gap between stated and actual
                      across bins. The single "how far off is the confidence".
  AUC                 threshold-free rank quality: does the score put true
                      recoveries above false ones. Discrimination, separate from
                      calibration.

None of this is a model. It is measurement, and it is the spine v43 hangs on: any
new scorer must beat the incumbent on these on the SAME held-out rows or it does
not ship. Deterministic, dollar-weightable, offline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _clean(score, correct, weight):
    c = pd.to_numeric(pd.Series(score), errors="coerce").to_numpy(dtype=float)
    y = pd.Series(correct).astype(float).to_numpy()
    w = (np.ones_like(c) if weight is None
         else pd.to_numeric(pd.Series(weight), errors="coerce").fillna(0.0).to_numpy(dtype=float))
    m = ~np.isnan(c)
    c, y, w = c[m], y[m], w[m]
    if w.sum() <= 0:
        w = np.ones_like(c)
    return c, y, w


def reliability_table(confidence, correct, weight=None, n_bins=10) -> pd.DataFrame:
    c, y, w = _clean(confidence, correct, weight)
    if len(c) == 0:
        return pd.DataFrame(columns=["bin_lo", "bin_hi", "n", "dollars",
                                     "mean_confidence", "actual_hit_rate", "gap"])
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(c, edges[1:-1], right=False), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        sel = idx == b
        if not sel.any():
            continue
        ww = w[sel]
        use = ww if ww.sum() > 0 else None
        rows.append({"bin_lo": round(float(edges[b]), 3),
                     "bin_hi": round(float(edges[b + 1]), 3),
                     "n": int(sel.sum()), "dollars": round(float(ww.sum()), 2),
                     "mean_confidence": round(float(np.average(c[sel], weights=use)), 4),
                     "actual_hit_rate": round(float(np.average(y[sel], weights=use)), 4),
                     "gap": round(float(np.average(y[sel], weights=use)
                                       - np.average(c[sel], weights=use)), 4)})
    return pd.DataFrame(rows)


def brier_score(confidence, correct, weight=None) -> float:
    c, y, w = _clean(confidence, correct, weight)
    if len(c) == 0:
        return float("nan")
    return round(float(np.average((c - y) ** 2, weights=w)), 4)


def expected_calibration_error(confidence, correct, weight=None, n_bins=10) -> float:
    tbl = reliability_table(confidence, correct, weight=weight, n_bins=n_bins)
    if tbl.empty:
        return float("nan")
    pop = tbl["dollars"].to_numpy()
    if pop.sum() <= 0:
        pop = tbl["n"].to_numpy().astype(float)
    return round(float(np.average(tbl["gap"].abs().to_numpy(), weights=pop)), 4)


def auc_roc(score, correct, weight=None) -> float:
    """Weighted AUC via concordant-pair fraction (robust, ties count half)."""
    s, y, w = _clean(score, correct, weight)
    pos = y == 1
    neg = y == 0
    if not pos.any() or not neg.any():
        return float("nan")
    sp, wp = s[pos], w[pos]
    sn, wn = s[neg], w[neg]
    conc = 0.0
    for spi, wpi in zip(sp, wp):
        conc += wpi * (float(np.sum(wn * (sn < spi))) + 0.5 * float(np.sum(wn * (sn == spi))))
    denom = float(wp.sum()) * float(wn.sum())
    return round(float(conc / denom), 4) if denom > 0 else float("nan")


def calibration_report(confidence, correct, weight=None, n_bins=10,
                       label="method") -> dict:
    tbl = reliability_table(confidence, correct, weight=weight, n_bins=n_bins)
    brier = brier_score(confidence, correct, weight=weight)
    ece = expected_calibration_error(confidence, correct, weight=weight, n_bins=n_bins)
    auc = auc_roc(confidence, correct, weight=weight)
    _, y, w = _clean(confidence, correct, weight)
    base = float(np.average(y, weights=w)) if len(y) else float("nan")
    over = float(tbl[tbl["gap"] < -0.05]["dollars"].sum()) if not tbl.empty else 0.0
    tot = float(tbl["dollars"].sum()) if not tbl.empty else 0.0
    frac_over = round(over / tot, 3) if tot else 0.0
    return {
        "label": label, "n": int(len(y)), "base_rate": round(base, 4),
        "brier": brier, "ece": ece, "auc": auc, "reliability": tbl,
        "frac_dollars_overconfident": frac_over,
        "note": (f"{label}: Brier {brier}, ECE {ece}, AUC {auc} on {int(len(y))} "
                 f"held-out rows (base rate {round(base,3)}). "
                 f"{int(frac_over*100)}% of dollars sit in overconfident bins.")}
