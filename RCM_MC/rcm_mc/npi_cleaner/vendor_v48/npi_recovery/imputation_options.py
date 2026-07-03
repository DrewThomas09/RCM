"""
imputation_options.py  (v35)
============================

Stage 4 of the deep-clean process: the OPTIONS layer. Where a field is missing
or broken there is usually more than one defensible deterministic fill, and the
honest process is to compute the candidates, show where they agree and disagree,
and let the analyst pick with the disagreement in view, rather than bake one
strategy in silently.

Strategies are small pure functions registered per field. Applying any strategy
always preserves the original in <field>_original and stamps
<field>_imputed_method on filled rows, so every imputation is reversible and
citable.

Registered strategies:
  units       code_median      median units per HCPCS among valid rows
              rate_implied     allowed divided by the code's median rate
  state       from_zip3        modal state of the row's zip3 (learned in-panel)
              provider_mode    modal state of the row's billing NPI
  drug_name   code_mode        modal populated name under the same HCPCS
              from_ndc         crosswalk resolution of the row's NDC (needs cw)

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .row_consistency import build_zip3_state_map


def _units_fillable(std):
    a = pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0)
    u = pd.to_numeric(std.get("units"), errors="coerce")
    return (a > 0) & (u.isna() | (u <= 0))


def _impute_units_code_median(std):
    u = pd.to_numeric(std.get("units"), errors="coerce")
    hc = std.get("hcpcs", pd.Series("", index=std.index)).astype("string").fillna("")
    valid = u > 0
    med = u[valid].groupby(hc[valid]).median()
    fill = hc.map(med)
    return fill.where(_units_fillable(std))


def _impute_units_rate_implied(std):
    a = pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0)
    u = pd.to_numeric(std.get("units"), errors="coerce")
    hc = std.get("hcpcs", pd.Series("", index=std.index)).astype("string").fillna("")
    valid = (u > 0) & (a > 0)
    rate = (a[valid] / u[valid]).groupby(hc[valid]).median()
    r = hc.map(rate)
    fill = (a / r).where(r > 0)
    return fill.round(1).where(_units_fillable(std))


def _state_fillable(std):
    st = std.get("state", pd.Series("", index=std.index)).astype("string").fillna("").str.strip()
    return st == ""


def _impute_state_from_zip3(std):
    zmap = build_zip3_state_map(std, min_rows=5)
    z3 = std.get("zip3", pd.Series("", index=std.index)).astype("string") \
        .fillna("").str.replace(r"\D", "", regex=True).str[:3]
    fill = z3.map(lambda z: zmap.get(z, np.nan))
    return pd.Series(fill, index=std.index).where(_state_fillable(std))


def _impute_state_provider_mode(std):
    st = std.get("state", pd.Series("", index=std.index)).astype("string").fillna("").str.strip()
    npi = std.get("billing_npi", pd.Series("", index=std.index)).astype("string").fillna("")
    have = st != ""
    mode = {}
    for n, g in st[have].groupby(npi[have]):
        c = g.value_counts()
        if len(c) and c.iloc[0] / len(g) >= 0.8:
            mode[n] = c.index[0]
    fill = npi.map(lambda n: mode.get(n, np.nan))
    return pd.Series(fill, index=std.index).where(_state_fillable(std))


def _drug_fillable(std):
    dn = std.get("drug_name", pd.Series("", index=std.index)).astype("string").fillna("").str.strip()
    return dn == ""


def _impute_drug_code_mode(std):
    dn = std.get("drug_name", pd.Series("", index=std.index)).astype("string").fillna("").str.strip()
    hc = std.get("hcpcs", pd.Series("", index=std.index)).astype("string").fillna("")
    have = dn != ""
    mode = {}
    for h, g in dn[have].groupby(hc[have]):
        c = g.value_counts()
        if len(c) and c.iloc[0] / len(g) >= 0.6:
            mode[h] = c.index[0]
    fill = hc.map(lambda h: mode.get(h, np.nan))
    return pd.Series(fill, index=std.index).where(_drug_fillable(std))


def _impute_drug_from_ndc(std, *, cw=None):
    if cw is None or "ndc" not in std.columns:
        return pd.Series(np.nan, index=std.index)
    ndc_to_name = cw.get("ndc_to_name") if isinstance(cw, dict) else None
    if not ndc_to_name:
        return pd.Series(np.nan, index=std.index)
    from .field_validators import normalize_ndc11
    nd = std["ndc"].map(lambda x: normalize_ndc11(x)[0])
    fill = nd.map(lambda n: ndc_to_name.get(n, np.nan))
    return pd.Series(fill, index=std.index).where(_drug_fillable(std))


STRATEGIES = {
    "units": {"code_median": _impute_units_code_median,
              "rate_implied": _impute_units_rate_implied},
    "state": {"from_zip3": _impute_state_from_zip3,
              "provider_mode": _impute_state_provider_mode},
    "drug_name": {"code_mode": _impute_drug_code_mode,
                  "from_ndc": _impute_drug_from_ndc},
}


def compare_strategies(std: pd.DataFrame, field: str, *, allowed=None,
                       cw=None) -> pd.DataFrame:
    """Every registered strategy for the field, side by side: fillable rows,
    rows each fills, dollars on filled rows, and pairwise agreement where two
    strategies both fill. The decision table, not the decision."""
    if field not in STRATEGIES:
        return pd.DataFrame({"note": ["no strategies registered for {}".format(field)]})
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0))
    fills = {}
    for name, fn in STRATEGIES[field].items():
        fills[name] = fn(std, cw=cw) if name == "from_ndc" else fn(std)
    fillable = {"units": _units_fillable, "state": _state_fillable,
                "drug_name": _drug_fillable}[field](std)
    n_fillable = int(fillable.sum())
    rows = []
    for name, f in fills.items():
        got = f.notna()
        rows.append({"strategy": name, "fillable_rows": n_fillable,
                     "rows_filled": int(got.sum()),
                     "fill_rate_pct": round(got.sum() / n_fillable * 100, 1) if n_fillable else 0.0,
                     "dollars_on_filled": round(float(a[got].sum()), 2)})
    names = list(fills)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            f1, f2 = fills[names[i]], fills[names[j]]
            both = f1.notna() & f2.notna()
            if field == "units":
                agree = both & (np.isclose(pd.to_numeric(f1, errors="coerce"),
                                           pd.to_numeric(f2, errors="coerce"),
                                           rtol=0.05))
            else:
                agree = both & (f1.astype("string") == f2.astype("string"))
            rows.append({"strategy": "{} vs {}".format(names[i], names[j]),
                         "fillable_rows": int(both.sum()),
                         "rows_filled": int(agree.sum()),
                         "fill_rate_pct": round(agree.sum() / both.sum() * 100, 1) if both.sum() else np.nan,
                         "dollars_on_filled": round(float(a[both & ~agree].sum()), 2)})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "Comparison rows read: fillable_rows = both filled, rows_filled = agreements, "
        "fill_rate_pct = agreement rate, dollars_on_filled = dollars where they DISAGREE. "
        "High agreement means the fill is safe under either method; disagreement dollars "
        "are the rows to decide by hand.")
    return out


def apply_strategy(std: pd.DataFrame, field: str, strategy: str, *, cw=None):
    """Apply one strategy: fill, preserve <field>_original, stamp
    <field>_imputed_method on filled rows only. Returns (frame, ledger_rows)."""
    if field not in STRATEGIES or strategy not in STRATEGIES[field]:
        return std, []
    fn = STRATEGIES[field][strategy]
    fill = fn(std, cw=cw) if strategy == "from_ndc" else fn(std)
    got = fill.notna()
    if not got.any():
        return std, []
    out = std.copy()
    orig_col = "{}_original".format(field)
    if orig_col not in out.columns:
        out[orig_col] = out.get(field)
    meth_col = "{}_imputed_method".format(field)
    if meth_col not in out.columns:
        out[meth_col] = ""
    out.loc[got, field] = fill[got]
    out.loc[got, meth_col] = strategy
    ledger = [{"stage": "imputation", "rule_id": "IMP-{}-{}".format(field.upper(), strategy),
               "field": field, "rows_changed": int(got.sum()),
               "action": "filled via {} (original kept in {})".format(strategy, orig_col)}]
    return out, ledger
