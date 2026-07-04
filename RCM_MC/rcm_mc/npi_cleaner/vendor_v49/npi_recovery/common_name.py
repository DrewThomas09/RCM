"""common_name (v31): the authoritative "common drug name" grouper.

Why this exists — the headline problem from the pre-readout sync.
    "make sure that all NDCs and multiple J-codes that are attributable to the
     same drug are together and grouped so that we don't misrepresent ... we
     only captured half of their Stelara revenue, because the other half is
     attributable to a different code lower down the list, and our formulas just
     pick up the first one."

A single molecule bills under several codes at once:
  * ustekinumab: J3357 (SC), J3358 (IV), plus biosimilars under the J3590 NOC;
  * immune globulin: ~15 brand-specific J-codes (J1569, J1561, J1459, ...) plus
    J1599 (IVIG NOS);
  * plus, in a dual-feed run, the NDCs on the pharmacy side.
If a per-drug cut groups on the raw HCPCS or the free-text drug name, each code
becomes its own row and a "top drug" / formulary line captures only the single
biggest code — so Stelara reads ~46% of its true size and the second code is
silently dropped.

This module collapses every member code (J-code AND NDC) of one molecule to a
single canonical common name and key, so the per-drug analytics sum across ALL
of them. It reuses the same curated crosswalk + resolution the rx_bridge uses,
so the medical and pharmacy channels land on identical names, and it runs on the
MEDICAL panel even when no pharmacy feed is supplied (in v30 the class label was
only computed in a dual-feed run, which is exactly when the medical-only cuts
still split). Resolution is crosswalk / name-token / drug_ident only — no LLM,
consistent with the toolkit's rule. Rows it cannot resolve keep their own
drug_name / HCPCS as the name and are never merged or dropped.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config
from . import rx_bridge as _rxb

UNRESOLVED = "(unresolved drug)"


def _drug_ident_name(hcpcs, ndc, drug_name, drug_ident):
    """Pull a name from the API-enriched drug_ident dict, which the pipeline keys
    on ('ndc', code) and ('name', lowered). Returns "" when nothing matches."""
    di = drug_ident or {}
    if not di:
        return ""
    keys = []
    if pd.notna(ndc):
        nd = "".join(ch for ch in str(ndc) if ch.isdigit())
        if nd:
            keys += [("ndc", nd), ("ndc", nd[:9] if len(nd) >= 11 else nd)]
    if isinstance(drug_name, str) and drug_name.strip():
        keys.append(("name", drug_name.strip().lower()))
    for k in keys:
        rec = di.get(k)
        if isinstance(rec, dict):
            for f in ("drug_class", "ingredient", "name", "label"):
                if rec.get(f):
                    return str(rec[f])
    return ""


def assign_common_name(std: pd.DataFrame, *, crosswalk=None, drug_ident=None,
                       ref_dir=None, rxnorm=None, progress=None) -> pd.DataFrame:
    """Add the canonical grouping columns to a standardized frame.

    Adds:
      drug_common_name   canonical molecule label shared across J-codes + NDCs
                         (e.g. 'Ustekinumab (Stelara)'), or the row's own
                         drug_name / HCPCS when it cannot be resolved.
      drug_common_key    normalized ingredient key ('ustekinumab') — the join key.
      _common_source     hcpcs | drug_class_rx | ingredient_rx | ndc | name |
                         drug_ident | drug_name_fallback | hcpcs_fallback | unresolved

    Resolution order, strongest first:
      1. an already-resolved drug_class_rx from the rx_bridge (dual-feed runs);
      2. the row's HCPCS in the curated crosswalk (offline, deterministic);
      3. an ingredient_rx already on the row -> its class;
      4. the free-text drug name via the brand/ingredient seed (offline);
      5. the NDC / name via live RxNorm when a client is supplied;
      6. the API drug_ident dictionary;
      7. fall back to the row's own drug_name, else its HCPCS. Never merges rows
         it cannot resolve, never drops them.
    Idempotent: safe to call after rx_bridge.resolve_feed or on a bare frame.
    """
    progress = progress or (lambda *_: None)
    xwalk = crosswalk or _rxb.load_crosswalk(ref_dir)
    out = std.copy()
    n = len(out)

    def _col(name):
        return out[name].astype("string") if name in out.columns else pd.Series([pd.NA] * n)

    hc = _col("hcpcs")
    nd = _col("ndc")
    dn = _col("drug_name")
    dc_rx = _col("drug_class_rx")
    ing_rx = _col("ingredient_rx")

    names = np.array([UNRESOLVED] * n, dtype=object)
    keys = np.array([""] * n, dtype=object)
    sources = np.array(["unresolved"] * n, dtype=object)

    # small caches: many rows share an NDC / name / code
    name_cache, ndc_cache = {}, {}

    for i in range(n):
        if i % 1000 == 0:
            progress(f"common name {i}/{n}", (i + 1) / max(n, 1))

        # 1. already-resolved class from the rx bridge (most reliable, shared
        #    across feeds). UNMAPPED_RX means "the bridge could not place it".
        cls = dc_rx.iat[i] if i < len(dc_rx) else pd.NA
        if pd.notna(cls) and str(cls) not in ("", _rxb.UNMAPPED):
            names[i] = str(cls)
            keys[i] = _norm_key(str(cls), xwalk)
            sources[i] = "drug_class_rx"
            continue

        # 2. HCPCS in the curated crosswalk -> class + ingredient key.
        #    Catch-all / NOC codes (J3590, J3490, J9999, ...) are shared by many
        #    unrelated molecules, so a bare NOC code is NOT a reliable identifier.
        #    Skip it here and let the drug name / NDC drive resolution instead;
        #    this stops an unknown J3590 row from being merged into whichever
        #    branded biosimilar happens to list the same NOC code.
        code = (str(hc.iat[i]).strip().upper() if i < len(hc) and pd.notna(hc.iat[i]) else "")
        if code and not config.is_catchall_code(code):
            row = xwalk["by_hcpcs"].get(code)
            if row:
                names[i] = row["drug_class"]
                keys[i] = row["ingredient"] or _norm_key(row["drug_class"], xwalk)
                sources[i] = "hcpcs"
                continue

        # 3. an ingredient already resolved on the row (e.g. from a prior bridge)
        ing = (str(ing_rx.iat[i]).strip() if i < len(ing_rx) and pd.notna(ing_rx.iat[i]) else "")
        if ing:
            row = _rxb._class_for_ingredient(_rxb._norm(ing), xwalk)
            if row:
                names[i] = row["drug_class"]
                keys[i] = row["ingredient"]
                sources[i] = "ingredient_rx"
                continue

        # 4/5. resolve from the free-text drug name (seed offline, RxNorm live)
        name_val = str(dn.iat[i]) if i < len(dn) and pd.notna(dn.iat[i]) else ""
        ndc_val = str(nd.iat[i]) if i < len(nd) and pd.notna(nd.iat[i]) else ""
        ing2, how = _resolve_name_ndc(name_val, ndc_val, xwalk, rxnorm, name_cache, ndc_cache)
        if ing2:
            row = _rxb._class_for_ingredient(ing2, xwalk)
            if row:
                names[i] = row["drug_class"]
                keys[i] = row["ingredient"]
                sources[i] = how
                continue

        # 6. API-enriched drug_ident dictionary
        di_name = _drug_ident_name(
            nd.iat[i] if i < len(nd) else pd.NA,
            nd.iat[i] if i < len(nd) else pd.NA,
            name_val, drug_ident)
        if di_name:
            names[i] = di_name
            keys[i] = _norm_key(di_name, xwalk)
            sources[i] = "drug_ident"
            continue

        # 7. fall back to the row's own name, else the bare code. NEVER merged.
        if name_val.strip():
            names[i] = name_val.strip()
            keys[i] = "name::" + _rxb._norm(name_val)
            sources[i] = "drug_name_fallback"
        elif code:
            names[i] = code
            keys[i] = "hcpcs::" + code
            sources[i] = "hcpcs_fallback"

    out["drug_common_name"] = names
    out["drug_common_key"] = keys
    out["_common_source"] = sources
    return out


def _norm_key(class_label, xwalk):
    """Map a class label back to its ingredient key when the crosswalk knows it,
    else a normalized version of the label so identical labels still group."""
    lab = _rxb._norm(class_label)
    for ing, row in xwalk["by_ingredient"].items():
        if _rxb._norm(row["drug_class"]) == lab:
            return ing
    return lab


def _resolve_name_ndc(name_val, ndc_val, xwalk, rxnorm, name_cache, ndc_cache):
    """Ingredient from a drug name (seed brand/ingredient tokens, offline) or an
    NDC (live RxNorm when available). Returns (ingredient_norm, source)."""
    # NDC via RxNorm first (only when a client is supplied)
    nd_digits = "".join(ch for ch in ndc_val if ch.isdigit())
    if nd_digits and len(nd_digits) >= 9 and rxnorm is not None:
        if nd_digits in ndc_cache:
            ing = ndc_cache[nd_digits]
        else:
            ing = ""
            try:
                rec = rxnorm.lookup_ndc(nd_digits)
                if rec:
                    ing = _rxb._norm(rec.get("ingredient") or rec.get("name") or "")
            except Exception:
                ing = ""
            ndc_cache[nd_digits] = ing
        if ing:
            return ing, "ndc"

    if not name_val.strip():
        return "", "unresolved"
    if name_val in name_cache:
        return name_cache[name_val]
    nnorm = _rxb._norm(name_val)
    # brand in parentheses / leading token
    brand = _rxb._brand_from_name(name_val)
    row = xwalk["by_brand"].get(_rxb._norm(brand)) or xwalk["by_brand"].get(_rxb._norm(name_val))
    if row:
        name_cache[name_val] = (row["ingredient"], "name")
        return name_cache[name_val]
    # ingredient token in the name
    for token, canon in _rxb._INGREDIENT_CONTAINS:
        if token in nnorm:
            name_cache[name_val] = (canon, "name")
            return name_cache[name_val]
    # brand token anywhere in the name
    for bk, brow in xwalk.get("brand_tokens", []):
        if re.search(r"\b" + re.escape(bk) + r"\b", nnorm):
            name_cache[name_val] = (brow["ingredient"], "name")
            return name_cache[name_val]
    name_cache[name_val] = ("", "unresolved")
    return name_cache[name_val]


def grouped_label_series(std_named: pd.DataFrame,
                         fallback_label: pd.Series | None = None) -> pd.Series:
    """The label to feed every per-drug cut: the resolved common name, else the
    caller's existing per-row label (so nothing regresses when unresolved)."""
    cn = std_named["drug_common_name"].astype("object")
    if fallback_label is None:
        return cn.where(cn.ne(UNRESOLVED), std_named.get("drug_name", cn))
    fb = pd.Series(np.asarray(fallback_label), index=std_named.index).astype("object")
    return cn.where(cn.ne(UNRESOLVED), fb)


def common_name_rollup(std_named: pd.DataFrame, allowed: pd.Series,
                       units: pd.Series | None = None, top_n: int = 200) -> pd.DataFrame:
    """Per common name: total rows, allowed $, units, the distinct member codes,
    and — the proof the split was caught — how many distinct HCPCS contributed and
    what share the single largest member code represents. A `first_code_only_$`
    column shows what a pick-the-first-code approach would have booked, and
    `undercount_$` the dollars that grouping recovers.

    This is the audit that answers "did we finally capture all of Stelara".
    """
    name = std_named["drug_common_name"].astype("string").fillna(UNRESOLVED)
    key = std_named["drug_common_key"].astype("string").fillna("")
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    u = (pd.to_numeric(units, errors="coerce").fillna(0.0)
         if units is not None else pd.Series(0.0, index=std_named.index))
    hc = (std_named["hcpcs"].astype("string").fillna("")
          if "hcpcs" in std_named.columns else pd.Series("", index=std_named.index))
    nd = (std_named["ndc"].astype("string").fillna("")
          if "ndc" in std_named.columns else pd.Series("", index=std_named.index))

    df = pd.DataFrame({"name": name.values, "key": key.values, "a": a.values,
                       "u": u.values, "hc": hc.values, "nd": nd.values})
    rows = []
    for (nm, ky), g in df.groupby(["name", "key"], sort=False):
        codes = sorted({c for c in g["hc"].tolist() if c})
        ndc_ct = g.loc[g["nd"].ne(""), "nd"].nunique()
        by_code = g.groupby("hc")["a"].sum()
        largest = float(by_code.max()) if len(by_code) else 0.0
        total = float(g["a"].sum())
        rows.append({
            "drug_common_name": nm,
            "drug_common_key": ky,
            "rows": int(g.shape[0]),
            "member_j_codes": ", ".join(codes) if codes else "",
            "n_member_j_codes": len(codes),
            "n_member_ndcs": int(ndc_ct),
            "units": round(float(g["u"].sum()), 1),
            "allowed": round(total, 2),
            "largest_code_allowed": round(largest, 2),
            "largest_code_share_pct": round(100.0 * largest / total, 1) if total > 0 else np.nan,
            "split_across_codes": len(codes) > 1,
            "undercount_if_first_code_only": round(total - largest, 2),
        })
    out = pd.DataFrame(rows).sort_values("allowed", ascending=False)
    if top_n and len(out) > top_n:
        out = out.head(top_n)
    # push unresolved to the bottom so it is visible but not first
    if (out["drug_common_name"] == UNRESOLVED).any():
        unm = out[out["drug_common_name"] == UNRESOLVED]
        out = pd.concat([out[out["drug_common_name"] != UNRESOLVED], unm], ignore_index=True)
    split_dollars = float(out.loc[out["split_across_codes"], "undercount_if_first_code_only"].sum())
    out.attrs["note"] = (
        "One row per molecule. Every J-code AND NDC attributable to a drug is collapsed to a "
        "single common name and the dollars summed across all of them. 'split_across_codes' "
        "marks molecules that bill under more than one J-code (e.g. Stelara J3357/J3358/J3590, "
        "IVIG's brand codes); 'undercount_if_first_code_only' is what a pick-the-first-code "
        f"cut would have dropped — ${split_dollars:,.0f} across all split molecules here.")
    return out
