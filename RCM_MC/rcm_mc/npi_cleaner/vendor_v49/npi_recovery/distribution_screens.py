"""
distribution_screens.py  (v35)
==============================

Stage 3 of the deep-clean process: screens that only exist at the distribution
level. A file can pass every field and row rule and still carry a fabricated or
system-generated block of amounts; these tests catch the shape of the numbers.

  Benford first digit   natural multi-magnitude dollar amounts follow
                        log10(1 + 1/d); flat or spiked first-digit profiles mark
                        generated fills, copied blocks, or fee-schedule artifacts
  rounding pathology    the share of amounts at exact dollars and round hundreds
                        per payer separates contracted fee schedules (legitimate
                        roundness) from hand-keyed or fabricated blocks

The chi-square statistic is hand-rolled and compared to the fixed df=8 critical
value at the 5 percent level (15.507); no scipy. Screens flag for INSPECTION,
they do not accuse. Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_BENFORD = {d: np.log10(1 + 1 / d) for d in range(1, 10)}
_CHI2_CRIT_DF8_05 = 15.507


def _first_digits(values: pd.Series) -> pd.Series:
    v = pd.to_numeric(values, errors="coerce").abs()
    v = v[v >= 1]
    return v.map(lambda x: int(str(x).lstrip("0.")[0]) if str(x).lstrip("0.") else np.nan).dropna()


def benford_first_digit(values: pd.Series, *, min_n: int = 100) -> pd.DataFrame:
    """Observed vs expected first-digit frequencies with the chi-square verdict."""
    d = _first_digits(values)
    n = int(len(d))
    if n < min_n:
        out = pd.DataFrame({"note": ["only {} usable amounts (need {}); Benford "
                                     "screen not meaningful".format(n, min_n)]})
        out.attrs["verdict"] = "INSUFFICIENT_N"
        return out
    obs = d.value_counts().reindex(range(1, 10), fill_value=0)
    rows = []
    chi = 0.0
    for digit in range(1, 10):
        p_obs = obs[digit] / n
        p_exp = _BENFORD[digit]
        chi += n * (p_obs - p_exp) ** 2 / p_exp
        rows.append({"first_digit": digit, "observed_pct": round(p_obs * 100, 1),
                     "benford_pct": round(p_exp * 100, 1),
                     "deviation_pts": round((p_obs - p_exp) * 100, 1)})
    out = pd.DataFrame(rows)
    conforms = chi <= _CHI2_CRIT_DF8_05
    out.attrs["chi_square"] = round(float(chi), 1)
    out.attrs["n"] = n
    out.attrs["verdict"] = ("CONFORMS (chi-square {:.1f} <= {:.3f})".format(chi, _CHI2_CRIT_DF8_05)
                            if conforms else
                            "DEVIATES (chi-square {:.1f} > {:.3f}): inspect for generated "
                            "fills, copied blocks, or a fee-schedule artifact".format(
                                chi, _CHI2_CRIT_DF8_05))
    out.attrs["note"] = out.attrs["verdict"] + \
        ". Deviation flags for inspection; contracted flat rates deviate legitimately."
    return out


def benford_by_group(std: pd.DataFrame, *, allowed, group_col: str,
                     min_n: int = 100, top_groups: int = 10) -> pd.DataFrame:
    """The Benford verdict per group (payer or provider), largest groups first,
    so a single bad feed does not hide inside a passing total."""
    if group_col not in std.columns:
        return pd.DataFrame({"note": ["no {} column".format(group_col)]})
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    g = std[group_col].astype("string").fillna("(blank)")
    order = a.groupby(g).sum().sort_values(ascending=False).head(top_groups).index
    rows = []
    for grp in order:
        r = benford_first_digit(a[g == grp], min_n=min_n)
        rows.append({"group": grp, "n_amounts": r.attrs.get("n", 0),
                     "chi_square": r.attrs.get("chi_square", np.nan),
                     "verdict": r.attrs.get("verdict", "INSUFFICIENT_N")})
    out = pd.DataFrame(rows)
    out.attrs["note"] = ("Per-group first-digit conformance; DEVIATES rows are the feeds "
                         "to open first.")
    return out


def rounding_pathology(std: pd.DataFrame, *, allowed, group_col: str = "payer",
                       top_groups: int = 10) -> pd.DataFrame:
    """Share of dollars on whole-dollar, round-hundred, and round-thousand
    amounts per group. High roundness in a payer that should adjudicate to the
    cent is the tell for schedules, caps, or hand keying."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    g = (std[group_col].astype("string").fillna("(blank)")
         if group_col in std.columns else pd.Series("(all)", index=std.index))
    cents = (a * 100).round().astype("int64")
    whole = cents % 100 == 0
    h = cents % 10000 == 0
    k = cents % 100000 == 0
    rows = []
    order = a.abs().groupby(g).sum().sort_values(ascending=False).head(top_groups).index
    for grp in order:
        m = g == grp
        tot = float(a[m].abs().sum())
        n = int(m.sum())
        if tot <= 0 or n == 0:
            continue
        rows.append({"group": grp, "rows": n,
                     "whole_dollar_share_pct": round(float(a[m & whole].abs().sum()) / tot * 100, 1),
                     "round_hundred_share_pct": round(float(a[m & h].abs().sum()) / tot * 100, 1),
                     "round_thousand_share_pct": round(float(a[m & k].abs().sum()) / tot * 100, 1)})
    if not rows:
        return pd.DataFrame({"note": ["no dollars to profile"]})
    out = pd.DataFrame(rows)
    out.attrs["note"] = ("Adjudicated commercial claims rarely land on round hundreds at "
                         "scale; a group far above its peers is a schedule, a cap, or a "
                         "keyed block worth opening.")
    return out
