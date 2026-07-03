"""
deficit_diagnostics.py  (v32)
=============================

The morning left four candidate root causes for the low Option Care total, each
with a different fix, and the notes never scored them. This module scores them
from what the panel can actually measure, and runs the cheap filter test the
notes dropped.

The four hypotheses:

  1. entity roster leakage   volume billed under target entities missing from the
                             finder list (legacy NPIs, acquired-practice names).
  2. claim-type / file scope a home-infusion book runs through the DME benefit
                             (pump + SCIG), the post-Cures home-infusion-therapy
                             G-codes, and Part D, not Carrier/Outpatient. A pull
                             scoped to medical claim types collapses this asset
                             specifically. classify_claim_channel measures the
                             share of volume in channels a medical-only pull
                             misses.
  3. book structure          FFS files carry no MA payment and home infusion is
                             structurally underweight in FFS, so some shortfall is
                             genuinely explicable rather than an artifact.
  4. filter logic            if totals were computed downstream of the code-level
                             formulary filter, part of the shortfall is
                             self-inflicted. filter_attribution_test recomputes
                             unfiltered and under drug-level inclusion and shows
                             how much of the gap closes.

diagnose_deficit assembles whatever signals are supplied into one attribution
table with an honest residual and a verdict. Everything is deterministic and
offline; unsupplied signals are simply reported as unquantified, never guessed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config


# Post-Cures home-infusion-therapy professional codes (Part B, HIT supplier) and
# the commercial home-infusion per-diem S-codes. Small, stable reference set.
HIT_GCODES = {"G0068", "G0069", "G0070", "G0088", "G0089", "G0090"}
HIT_SCODES = {
    "S9061", "S9490", "S9494", "S9497", "S9500", "S9501", "S9502", "S9503",
    "S9504", "S9537", "S9538", "S9542", "S9558", "S9559", "S9590",
}


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def load_dme_codes(ref_dir=None) -> set:
    """DMEPOS / external-pump channel HCPCS from the shipped reference."""
    ref = Path(ref_dir or config.REF_DIR)
    f = ref / "home_dme_hcpcs.csv"
    if not f.exists():
        return set()
    try:
        d = pd.read_csv(f, dtype=str)
    except Exception:
        return set()
    col = "hcpcs" if "hcpcs" in d.columns else d.columns[0]
    return {str(x).strip().upper() for x in d[col].dropna()}


def _sad_codes() -> set:
    # self-administered / Part D-leaning codes the codebase already tracks
    codes = set()
    for name in ("SAD_CODES", "SELF_ADMIN_CODES"):
        codes |= set(getattr(config, name, set()) or set())
    # the SC ustekinumab sibling is the canonical SAD example
    codes |= {"J3357"}
    return {str(c).strip().upper() for c in codes}


def classify_claim_channel(std: pd.DataFrame, *, ref_dir=None,
                           hcpcs_col: str = "hcpcs") -> pd.Series:
    """Per row, the CMS benefit/file the code implies:
        HIT_PROF       home-infusion-therapy professional (G-codes / S per-diems)
        DME_SUPPLY     DMEPOS / external-pump channel (SCIG, pump drugs)
        PARTD_SAD      self-administered, Part D territory
        PARTB_MEDICAL  everything else (Carrier / Outpatient J-codes)
    This is what tells you whether a medical-only pull could ever have seen the
    volume."""
    n = len(std)
    if hcpcs_col not in std.columns:
        return pd.Series(["PARTB_MEDICAL"] * n, index=std.index)
    code = std[hcpcs_col].astype("string").fillna("").str.strip().str.upper()
    dme = load_dme_codes(ref_dir)
    sad = _sad_codes()

    out = np.array(["PARTB_MEDICAL"] * n, dtype=object)
    c = code.to_numpy()
    for i in range(n):
        k = c[i]
        if not k:
            continue
        if k in HIT_GCODES or k in HIT_SCODES:
            out[i] = "HIT_PROF"
        elif k in dme:
            out[i] = "DME_SUPPLY"
        elif k in sad:
            out[i] = "PARTD_SAD"
    return pd.Series(out, index=std.index)


def claim_scope_coverage(std: pd.DataFrame, *, allowed, ref_dir=None,
                         pull_channels=("PARTB_MEDICAL",),
                         hcpcs_col: str = "hcpcs") -> pd.DataFrame:
    """Share of dollars by claim channel and, given which channels the pull
    actually covered, the share that sits in channels the pull missed. That missed
    share is the claim-type-scope signal: for a home-infusion asset pulled from
    Carrier/Outpatient only, DME + HIT + Part D fall outside the net."""
    ch = classify_claim_channel(std, ref_dir=ref_dir, hcpcs_col=hcpcs_col)
    a = _num(allowed).fillna(0.0).to_numpy()
    tot = float(a.sum())
    df = pd.DataFrame({"channel": ch.to_numpy(), "allowed": a})
    g = df.groupby("channel")["allowed"].sum()
    pull = {str(x).strip().upper() for x in pull_channels}

    rows = []
    for chn, amt in g.sort_values(ascending=False).items():
        rows.append({
            "channel": chn,
            "allowed": round(float(amt), 2),
            "share_pct": round(float(amt) / tot * 100, 1) if tot > 0 else 0.0,
            "in_pull_scope": chn in pull,
        })
    missed = float(sum(v for k, v in g.items() if k not in pull))
    out = pd.DataFrame(rows)
    out.attrs["missed_share_allowed"] = round(missed, 2)
    out.attrs["missed_share_pct"] = round(missed / tot * 100, 1) if tot > 0 else 0.0
    out.attrs["note"] = (
        "in_pull_scope=False channels are volume a pull limited to {} could not have "
        "captured. For a home-infusion book that is DME_SUPPLY (SCIG/pump), HIT_PROF "
        "(home-infusion G/S codes), and PARTD_SAD (self-administered), which is the "
        "claim-type-scope root cause made concrete.".format(sorted(pull)))
    return out


def filter_attribution_test(std: pd.DataFrame, *, allowed,
                            code_level_mask=None, drug_level_mask=None) -> pd.DataFrame:
    """The hour-long test the notes dropped. Recompute the total three ways:
    unfiltered, under the code-level formulary filter, and under drug-level
    inclusion. Reports how much the code-level filter removed and how much
    drug-level inclusion recovers over it, i.e. the self-inflicted portion of a
    low total.

    Masks are boolean Series aligned to std where True = kept."""
    a = _num(allowed).fillna(0.0)
    total_unfiltered = float(a.sum())

    def _kept(mask):
        if mask is None:
            return np.nan
        m = pd.Series(np.asarray(mask), index=std.index).astype(bool)
        return float(a[m].sum())

    code_kept = _kept(code_level_mask)
    drug_kept = _kept(drug_level_mask)

    rows = [{"basis": "unfiltered total", "allowed": round(total_unfiltered, 2),
             "pct_of_unfiltered": 100.0}]
    if not np.isnan(code_kept):
        rows.append({"basis": "code-level formulary filter", "allowed": round(code_kept, 2),
                     "pct_of_unfiltered": round(code_kept / total_unfiltered * 100, 1) if total_unfiltered else np.nan})
    if not np.isnan(drug_kept):
        rows.append({"basis": "drug-level inclusion (grouper)", "allowed": round(drug_kept, 2),
                     "pct_of_unfiltered": round(drug_kept / total_unfiltered * 100, 1) if total_unfiltered else np.nan})
    if not np.isnan(code_kept):
        rows.append({"basis": "removed by code-level filter", "allowed": round(total_unfiltered - code_kept, 2),
                     "pct_of_unfiltered": round((total_unfiltered - code_kept) / total_unfiltered * 100, 1) if total_unfiltered else np.nan})
    if not np.isnan(code_kept) and not np.isnan(drug_kept):
        rows.append({"basis": "recovered by drug-level over code-level (self-inflicted)",
                     "allowed": round(drug_kept - code_kept, 2),
                     "pct_of_unfiltered": round((drug_kept - code_kept) / total_unfiltered * 100, 1) if total_unfiltered else np.nan})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "If the 'inexplicably low' total was computed after the code-level filter, the "
        "'recovered by drug-level over code-level' line is the part of the shortfall that was "
        "self-inflicted. If it is small, the deficit is entity roster, claim-type scope, or "
        "genuine FFS book structure, not the filter.")
    return out


def diagnose_deficit(*, captured_total, expected_total,
                     entity_leakage=None, claim_scope_deficit=None,
                     book_structure_deficit=None, filter_deficit=None,
                     entity_label: str = "target") -> pd.DataFrame:
    """Attribute the shortfall (expected - captured) across the four hypotheses
    from whatever signals are supplied, with an honest unattributed residual and a
    verdict naming the dominant cause. Each signal is a dollar estimate; omit one
    and it is reported as unquantified rather than assumed zero-cause."""
    if expected_total is None or float(expected_total) <= 0:
        return pd.DataFrame({"note": [
            "no expected total supplied; cannot scope the deficit. Provide the management / "
            "Komodo expected total to attribute the shortfall."]})
    cap = float(captured_total or 0.0)
    exp = float(expected_total)
    shortfall = exp - cap

    signals = [
        ("entity roster leakage", entity_leakage),
        ("claim-type / file scope", claim_scope_deficit),
        ("book structure (FFS vs MA/Part D)", book_structure_deficit),
        ("filter logic (formulary grain)", filter_deficit),
    ]
    rows = [
        {"cause": f"expected total ({entity_label})", "amount": round(exp, 2), "pct_of_shortfall": np.nan},
        {"cause": "captured total", "amount": round(cap, 2), "pct_of_shortfall": np.nan},
        {"cause": "shortfall (expected - captured)", "amount": round(shortfall, 2), "pct_of_shortfall": 100.0},
        {"cause": "---- attribution ----", "amount": np.nan, "pct_of_shortfall": np.nan},
    ]
    explained = 0.0
    quantified = []
    for label, val in signals:
        if val is None:
            rows.append({"cause": f"{label}", "amount": np.nan, "pct_of_shortfall": np.nan,
                         "status": "unquantified"})
            continue
        v = float(val)
        explained += v
        quantified.append((label, v))
        rows.append({"cause": f"{label}", "amount": round(v, 2),
                     "pct_of_shortfall": round(v / shortfall * 100, 1) if shortfall > 0 else np.nan,
                     "status": "quantified"})
    residual = shortfall - explained
    rows.append({"cause": "unattributed residual", "amount": round(residual, 2),
                 "pct_of_shortfall": round(residual / shortfall * 100, 1) if shortfall > 0 else np.nan})

    if shortfall <= 0:
        verdict = "NO SHORTFALL"
    elif quantified:
        top_label, top_val = max(quantified, key=lambda kv: kv[1])
        verdict = (f"dominant cause: {top_label}" if top_val / shortfall >= 0.4
                   else "no single dominant cause")
    else:
        verdict = "shortfall unattributed (no signals supplied)"
    out = pd.DataFrame(rows)
    out.attrs["verdict"] = verdict
    out.attrs["note"] = (
        "Attribution uses only supplied signals; 'unquantified' causes are not assumed absent. "
        "A large residual means the deficit is not yet explained by the measured signals. "
        "Verdict: {}.".format(verdict))
    return out
