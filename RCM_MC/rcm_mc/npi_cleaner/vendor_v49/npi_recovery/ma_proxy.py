"""
ma_proxy.py  (v33)
==================

"FFS files carry no usable MA payment," so the coverage-ratio gross-up has been
the only MA estimate on the page, and the whole page swings with the ratio. But
MA encounter VOLUMES exist even where payment does not. Pricing those encounters
at an FFS allowed-per-unit or the ASP payment limit gives a second, independent
MA estimate, clearly stamped proxy-priced, and a third leg comes from management
data. When the legs converge, the number is safe to chart; when they diverge, the
divergence is the finding. This also converts the book-structure hypothesis from
a reframed idea into a dollar estimate the deficit scorer can use.

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .calibration import load_kv_csv


def ma_proxy_estimate(encounters, prices) -> pd.DataFrame:
    """encounters: {drug: units}; prices: {drug: dollars per unit} (an FFS
    allowed-per-unit or the ASP payment limit converted to the same unit basis).
    Returns per-drug proxy dollars, all stamped proxy-priced."""
    e = load_kv_csv(encounters)
    p = load_kv_csv(prices)
    if not e or not p:
        return pd.DataFrame({"note": [
            "supply ma_encounters (drug -> units) and ma_prices (drug -> dollars/unit) to "
            "build the proxy-priced MA estimate"]})
    rows = []
    unpriced = 0
    for d, u in sorted(e.items(), key=lambda kv: -kv[1]):
        pr = p.get(d)
        if pr is None:
            unpriced += 1
            rows.append({"drug": d, "units": round(float(u), 1), "price_per_unit": np.nan,
                         "proxy_allowed": np.nan, "pricing_basis": "UNPRICED"})
            continue
        rows.append({"drug": d, "units": round(float(u), 1),
                     "price_per_unit": round(float(pr), 4),
                     "proxy_allowed": round(float(u) * float(pr), 2),
                     "pricing_basis": "PROXY (FFS/ASP per unit)"})
    out = pd.DataFrame(rows)
    total = float(pd.to_numeric(out["proxy_allowed"], errors="coerce").fillna(0).sum())
    out.attrs["proxy_total"] = round(total, 2)
    out.attrs["n_unpriced"] = unpriced
    out.attrs["note"] = (
        "Every dollar here is PROXY-PRICED: MA encounter units at an FFS/ASP unit price, not "
        "observed MA payment. Total {}; {} drug(s) unpriced and excluded from the total, "
        "never guessed.".format(round(total, 2), unpriced))
    return out


def ma_triangulation(*, ratio_estimate=None, proxy_estimate=None,
                     management_estimate=None, convergence_pct: float = 20.0) -> pd.DataFrame:
    """The three legs on one page: the coverage-ratio gross-up, the proxy-priced
    encounter estimate, and management's figure. Reports the spread and a verdict.
    Any leg can be absent; the table says which legs it stands on."""
    legs = [("coverage-ratio gross-up", ratio_estimate),
            ("proxy-priced encounters", proxy_estimate),
            ("management data", management_estimate)]
    rows = []
    vals = []
    for name, v in legs:
        if v is None:
            rows.append({"leg": name, "ma_estimate": np.nan, "status": "not supplied"})
        else:
            rows.append({"leg": name, "ma_estimate": round(float(v), 2), "status": "supplied"})
            vals.append(float(v))
    out = pd.DataFrame(rows)
    if len(vals) >= 2 and min(vals) > 0:
        spread = (max(vals) - min(vals)) / min(vals) * 100
        verdict = ("CONVERGENT (spread {:.1f}% <= {:.0f}%)".format(spread, convergence_pct)
                   if spread <= convergence_pct else
                   "DIVERGENT (spread {:.1f}%): do not chart a point estimate; reconcile "
                   "the legs first".format(spread))
        out.attrs["spread_pct"] = round(spread, 1)
    else:
        verdict = "single leg only: the estimate is unconfirmed"
        out.attrs["spread_pct"] = None
    out.attrs["verdict"] = verdict
    out.attrs["book_structure_estimate"] = (round(float(np.median(vals)), 2) if vals else None)
    out.attrs["note"] = (
        "Verdict: {}. The median leg doubles as the book-structure dollar estimate for the "
        "deficit diagnosis, since it is the MA mass a Carrier/Outpatient pull could never "
        "have seen.".format(verdict))
    return out
