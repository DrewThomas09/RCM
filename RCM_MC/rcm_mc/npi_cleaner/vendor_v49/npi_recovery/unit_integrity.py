"""
unit_integrity.py  (v34)
========================

Anticipated issue: rate outliers from unit keying errors. J-code billing units
are drug-specific (per 500 mg, per 1 mg, per 10 units), and a single misplaced
decimal in units or allowed produces a 10x or 100x rate that survives every
molecule-level rollup and detonates in the rate-per-unit chart. The ASP position
tab (v33) makes rates client-facing, so the first keying error is now the first
thing a reader clicks.

Per code, this screens rate = allowed/units against the code's own median using
a hand-rolled median absolute deviation, flags rows at decimal-error magnitudes,
and prices the overstatement. Quarantine list only; nothing is dropped.

Deterministic and offline. No scipy; MAD is hand-rolled.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rate_outlier_screen(std: pd.DataFrame, *, allowed, units,
                        hcpcs_col: str = "hcpcs", min_rows: int = 5,
                        ratio_flag: float = 8.0) -> pd.DataFrame:
    """Per flagged row: the code, its panel median rate, this row's rate, the
    ratio, the likely error class (units or dollars, 10x or 100x), and the
    overstatement dollars versus the median-priced row."""
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    u = pd.to_numeric(units, errors="coerce").fillna(0.0)
    hc = (std[hcpcs_col].astype("string").fillna("").str.strip().str.upper()
          if hcpcs_col in std.columns else pd.Series("", index=std.index))
    df = pd.DataFrame({"h": hc, "a": a, "u": u})
    df = df[(df["h"] != "") & (df["u"] > 0) & (df["a"] > 0)].copy()
    if df.empty:
        return pd.DataFrame({"note": ["no priceable rows (positive allowed and units)"]})
    df["rate"] = df["a"] / df["u"]

    med = df.groupby("h")["rate"].median()
    cnt = df.groupby("h")["rate"].size()
    mad = df.groupby("h")["rate"].apply(lambda s: float(np.median(np.abs(s - np.median(s)))))
    df["med"] = df["h"].map(med)
    df["n"] = df["h"].map(cnt)
    df["mad"] = df["h"].map(mad)
    df["ratio"] = df["rate"] / df["med"]

    flagged = df[(df["n"] >= min_rows)
                 & ((df["ratio"] >= ratio_flag) | (df["ratio"] <= 1.0 / ratio_flag))].copy()
    if flagged.empty:
        out = pd.DataFrame({"note": ["no decimal-magnitude rate outliers at the current "
                                     "thresholds; rates are internally consistent per code"]})
        out.attrs["overstatement_dollars"] = 0.0
        return out

    def _cls(r):
        for f, lab in ((100.0, "100x"), (10.0, "10x")):
            if abs(np.log10(r) - np.log10(f)) < 0.18:
                return f"{lab} high (units understated or dollars overstated)"
            if abs(np.log10(r) + np.log10(f)) < 0.18:
                return f"{lab} low (units overstated or dollars understated)"
        return "irregular magnitude"

    flagged["error_class"] = flagged["ratio"].map(_cls)
    flagged["overstatement"] = np.where(flagged["ratio"] > 1,
                                        flagged["a"] - flagged["u"] * flagged["med"], 0.0)
    out = pd.DataFrame({
        "row_index": flagged.index,
        "hcpcs": flagged["h"].to_numpy(),
        "allowed": flagged["a"].round(2).to_numpy(),
        "units": flagged["u"].round(1).to_numpy(),
        "rate_per_unit": flagged["rate"].round(4).to_numpy(),
        "code_median_rate": flagged["med"].round(4).to_numpy(),
        "ratio_to_median": flagged["ratio"].round(2).to_numpy(),
        "robust_sigma": (1.4826 * flagged["mad"]).round(4).to_numpy(),
        "error_class": flagged["error_class"].to_numpy(),
        "overstatement_dollars": flagged["overstatement"].round(2).to_numpy(),
    }).sort_values("overstatement_dollars", ascending=False).reset_index(drop=True)
    out.attrs["overstatement_dollars"] = round(float(flagged["overstatement"].sum()), 2)
    out.attrs["n_flagged"] = int(len(flagged))
    out.attrs["note"] = (
        "Quarantine list only; nothing dropped. overstatement_dollars is the excess over the "
        "code's median-priced equivalent for high-side outliers, the amount a keying error is "
        "currently adding to the market. Fix rows at source, or exclude with the register.")
    return out


def unit_basis_check(std: pd.DataFrame, *, allowed, units, asp_limits=None,
                     hcpcs_col: str = "hcpcs",
                     factor_candidates=(10.0, 100.0, 1000.0)) -> pd.DataFrame:
    """Anticipated cross-source trap: a whole CODE whose panel rate sits at a
    clean multiple of the ASP limit, meaning the source reports quantity in a
    different basis (mg vs billing units, ml vs each) rather than a per-row error.
    Requires asp_limits (hcpcs -> dollars per billing unit)."""
    from .calibration import load_kv_csv
    limits = {str(k).strip().upper(): float(v) for k, v in load_kv_csv(asp_limits).items()}
    if not limits:
        return pd.DataFrame({"note": ["supply asp_limits to test whole-code unit-basis "
                                      "mismatches against the payment limit"]})
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    u = pd.to_numeric(units, errors="coerce").fillna(0.0)
    hc = (std[hcpcs_col].astype("string").fillna("").str.strip().str.upper()
          if hcpcs_col in std.columns else pd.Series("", index=std.index))
    g = (pd.DataFrame({"h": hc, "a": a, "u": u})
         .query("h != '' and u > 0").groupby("h").sum(numeric_only=True))
    rows = []
    for h, r in g.iterrows():
        if h not in limits or limits[h] <= 0:
            continue
        ratio = (r["a"] / r["u"]) / limits[h]
        hit = None
        for f in factor_candidates:
            if abs(np.log10(ratio) - np.log10(f)) < 0.12:
                hit = ("panel units appear {}x too COARSE (rate {}x limit): source likely "
                       "reports a larger pack basis".format(int(f), int(f)))
            elif abs(np.log10(ratio) + np.log10(f)) < 0.12:
                hit = ("panel units appear {}x too FINE (rate 1/{} of limit): source likely "
                       "reports mg or ml, not billing units".format(int(f), int(f)))
            if hit:
                break
        if hit:
            rows.append({"hcpcs": h, "panel_rate_per_unit": round(r["a"] / r["u"], 4),
                         "asp_limit_per_unit": round(limits[h], 4),
                         "rate_vs_limit": round(ratio, 3), "diagnosis": hit})
    if not rows:
        return pd.DataFrame({"note": ["no whole-code unit-basis mismatches against the "
                                      "supplied limits"]})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "A whole code at a clean multiple of the limit is a basis mismatch, not fraud and not "
        "a keying error; convert the source's quantity to billing units before any rate chart.")
    return out
