"""
calibration.py  (v33)
=====================

The report's own resolution of VRDC's role: "VRDC's residual role becomes
calibration, a 100% FFS census against which to validate Komodo's FFS coverage
drug by drug, rather than primary source." This module computes exactly that:
per-drug FFS coverage ratios (Komodo FFS captured over the VRDC census), flags
thin-capture molecules where any gross-up would be unstable, and returns the
per-drug ratio set so the MA gross-up can stop leaning on one blended 14.1%.

Inputs are two drug-to-dollars maps (dict, or a two-column CSV/frame with
sniffed headers). Deterministic and offline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

_KEY_HEADERS = ("drug", "molecule", "drug_common_name", "common_name", "name", "state", "payer_class", "class")
_VAL_HEADERS = ("allowed", "allowed_amt", "dollars", "amount", "spend", "value", "ratio", "units", "captured", "universe", "limit", "price")


def load_kv_csv(path_or_obj, *, key_headers=_KEY_HEADERS, val_headers=_VAL_HEADERS) -> dict:
    """Read {key: float} from a dict, a two-column frame, or a CSV path with
    sniffed headers. Returns {} on any failure (honest no-op upstream)."""
    if path_or_obj is None:
        return {}
    if isinstance(path_or_obj, dict):
        try:
            return {str(k): float(v) for k, v in path_or_obj.items()}
        except Exception:
            return {}
    df = None
    if isinstance(path_or_obj, pd.DataFrame):
        df = path_or_obj
    else:
        p = Path(str(path_or_obj))
        if p.exists():
            try:
                df = pd.read_csv(p)
            except Exception:
                return {}
    if df is None or df.empty:
        return {}
    cols = {c.strip().lower(): c for c in df.columns}
    kc = next((cols[h] for h in key_headers if h in cols), df.columns[0])
    vc = next((cols[h] for h in val_headers if h in cols and cols[h] != kc), None)
    if vc is None:
        num = [c for c in df.columns if c != kc and pd.to_numeric(df[c], errors="coerce").notna().any()]
        if not num:
            return {}
        vc = num[0]
    out = {}
    for _, r in df.iterrows():
        k = str(r[kc]).strip()
        v = pd.to_numeric(pd.Series([r[vc]]), errors="coerce").iloc[0]
        if k and pd.notna(v):
            out[k] = float(v)
    return out


def komodo_ffs_calibration(komodo_ffs, vrdc_census, *, thin_threshold: float = 0.05,
                           blended_stated: float | None = None) -> pd.DataFrame:
    """Per drug: Komodo FFS captured, the VRDC FFS census, the coverage ratio,
    and a thin-capture flag below thin_threshold. Also reports the computed
    blended ratio against a stated blend (the 14.1%) when supplied."""
    k = load_kv_csv(komodo_ffs)
    v = load_kv_csv(vrdc_census)
    if not k or not v:
        return pd.DataFrame({"note": [
            "supply komodo_ffs and vrdc_census (drug -> dollars) to calibrate per-drug "
            "coverage against the 100 percent FFS census"]})
    drugs = sorted(set(k) | set(v))
    rows = []
    for d in drugs:
        cap = float(k.get(d, 0.0))
        cen = float(v.get(d, 0.0))
        ratio = (cap / cen) if cen > 0 else np.nan
        rows.append({"drug": d, "komodo_ffs_captured": round(cap, 2),
                     "vrdc_ffs_census": round(cen, 2),
                     "coverage_ratio": (round(ratio, 4) if not np.isnan(ratio) else np.nan),
                     "thin_capture_flag": bool(not np.isnan(ratio) and ratio < thin_threshold),
                     "census_missing_flag": bool(cen <= 0 and cap > 0)})
    out = pd.DataFrame(rows).sort_values("vrdc_ffs_census", ascending=False).reset_index(drop=True)
    tot_k = sum(k.values())
    tot_v = sum(x for x in v.values() if x > 0)
    blended = (tot_k / tot_v) if tot_v > 0 else np.nan
    out.attrs["blended_ratio"] = (round(blended, 4) if not np.isnan(blended) else None)
    out.attrs["per_drug_ratios"] = {
        r["drug"]: r["coverage_ratio"] for _, r in out.iterrows()
        if pd.notna(r["coverage_ratio"])}
    ratios = [r for r in out["coverage_ratio"] if pd.notna(r)]
    out.attrs["ratio_spread"] = (round(max(ratios) - min(ratios), 4) if ratios else None)
    note = ("Blended FFS coverage {}. Per-drug ratios span {}; a wide span means one blended "
            "ratio misprices the gross-up drug by drug.").format(
        out.attrs["blended_ratio"], out.attrs["ratio_spread"])
    if blended_stated is not None and not np.isnan(blended):
        delta = (blended - float(blended_stated)) * 100
        note += " Computed blend vs stated {}: {:+.1f} pts.".format(blended_stated, delta)
        out.attrs["blend_delta_pts"] = round(delta, 1)
    out.attrs["note"] = note
    return out
