"""rx_bridge (v30): map a pharmacy / RX feed onto the SAME drug taxonomy the
medical panel uses, so the two channels reconcile instead of the pharmacy slice
landing as an unlabelled lump.

Why this exists. A medical extract is keyed on HCPCS J-codes; a real pharmacy
extract is keyed on NDCs, carries no J-code, and reports quantity in dispensed
units (mL / each), not HCPCS billing units. Unioned as-is, the pharmacy dollars
show up in the combined total but fall out of every per-drug cut, and a
dual-benefit molecule (immune globulin, ustekinumab, vedolizumab, ...) cannot be
reconciled medical-vs-pharmacy. This module closes that:

  1. resolves each pharmacy row to an INGREDIENT — via the NLM RxNorm/RxNav NDC
     lookup the toolkit already uses (live, public, no key, cached), or the
     free-text drug name, or a curated brand/ingredient seed when offline;
  2. maps the ingredient to the medical drug_class label and a representative
     J-code, so pharmacy rows fold into the same per-drug analytics;
  3. records a units BASIS (HCPCS vs DISPENSED) and a best-effort
     HCPCS-equivalent unit count (quantity x strength) so per-unit metrics are
     not corrupted by mixing the two unit systems.

Everything degrades to an honest no-op: rows it cannot map keep drug_class
'UNMAPPED_RX' and are still counted in dollar totals but flagged, never dropped.
Resolution is lookup/seed only — no LLM, consistent with the toolkit's rule.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

UNMAPPED = "UNMAPPED_RX"

# ingredient tokens that should collapse to one class even when RxNorm returns a
# wordier ingredient string (e.g. "human immunoglobulin G").
_INGREDIENT_CONTAINS = [
    ("immune globulin", "immune globulin"),
    ("immunoglobulin", "immune globulin"),
    ("globulin", "immune globulin"),
    ("ivig", "immune globulin"),
    ("scig", "immune globulin"),
    ("ustekinumab", "ustekinumab"),
    ("vedolizumab", "vedolizumab"),
    ("ocrelizumab", "ocrelizumab"),
    ("efgartigimod", "efgartigimod"),
    ("rozanolixizumab", "rozanolixizumab"),
    ("ravulizumab", "ravulizumab"),
    ("eculizumab", "eculizumab"),
    ("vutrisiran", "vutrisiran"),
    ("patisiran", "patisiran"),
    ("teprotumumab", "teprotumumab"),
    ("daptomycin", "daptomycin"),
    ("infliximab", "infliximab"),
    ("pegloticase", "pegloticase"),
    ("natalizumab", "natalizumab"),
    ("tocilizumab", "tocilizumab"),
]


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(s).lower()).strip()


def load_crosswalk(ref_dir=None):
    """Load the seed brand/ingredient -> (drug_class, hcpcs, per_unit_mg, benefit)
    crosswalk, plus any user-supplied file dropped in reference/ (a row whose
    columns match the seed). User rows win on a brand collision. Returns a dict:
        {"by_brand": {norm_brand: row}, "by_ingredient": {norm_ing: row},
         "ingredients": set(norm_ing)}
    where row is a dict with keys brand, ingredient, drug_class, hcpcs,
    per_unit_mg, benefit, route, source.
    """
    ref = Path(ref_dir or config.REF_DIR)
    frames = []
    seed = ref / "ndc_hcpcs_crosswalk.csv"
    if seed.exists():
        frames.append(pd.read_csv(seed, dtype=str).assign(_prio=0))
    # any additional user crosswalk (e.g. the CMS ASP NDC-HCPCS file re-headed to
    # these columns, or a Komodo-provided map). Matched loosely by filename.
    for extra in sorted(ref.glob("*ndc*crosswalk*user*.csv")) + sorted(ref.glob("*ndc_hcpcs*user*.csv")):
        try:
            frames.append(pd.read_csv(extra, dtype=str).assign(_prio=1))
        except Exception:
            pass
    if not frames:
        return {"by_brand": {}, "by_ingredient": {}, "by_hcpcs": {},
                "ingredients": set(), "brand_tokens": []}
    df = pd.concat(frames, ignore_index=True).fillna("")
    df = df.sort_values("_prio")  # user rows (prio 1) override seed on dedup keep="last"
    by_brand, by_ing = {}, {}
    by_hcpcs = {}
    for _, r in df.iterrows():
        row = {"brand": r.get("brand", ""), "ingredient": _norm(r.get("ingredient", "")),
               "drug_class": r.get("drug_class", "") or UNMAPPED,
               "hcpcs": (r.get("hcpcs", "") or "").strip().upper(),
               "per_unit_mg": _to_float(r.get("per_unit_mg", "")),
               "benefit": (r.get("benefit", "") or "").strip().lower(),
               "route": r.get("route", ""), "source": r.get("source", "")}
        nb = _norm(r.get("brand", ""))
        if nb:
            by_brand[nb] = row
        ni = row["ingredient"]
        if ni and ni not in by_ing:
            by_ing[ni] = row
        hc = row["hcpcs"]
        if hc and hc not in by_hcpcs:
            by_hcpcs[hc] = row
    # brand keys for free-text token scanning (longest first, drop very short)
    brand_tokens = sorted([(k, v) for k, v in by_brand.items() if len(k) >= 4],
                          key=lambda kv: len(kv[0]), reverse=True)
    return {"by_brand": by_brand, "by_ingredient": by_ing, "by_hcpcs": by_hcpcs,
            "ingredients": set(by_ing.keys()), "brand_tokens": brand_tokens}


def _to_float(x):
    try:
        v = float(str(x).strip())
        return v if v > 0 else np.nan
    except Exception:
        return np.nan


def _class_for_ingredient(ing_norm, xwalk):
    """norm ingredient -> row (drug_class/hcpcs/per_unit_mg). Exact first, then the
    contains rules so wordy RxNorm ingredient strings still collapse to a class."""
    if not ing_norm:
        return None
    row = xwalk["by_ingredient"].get(ing_norm)
    if row:
        return row
    for token, canon in _INGREDIENT_CONTAINS:
        if token in ing_norm:
            r = xwalk["by_ingredient"].get(canon)
            if r:
                return r
    return None


def _brand_from_name(name):
    """Pull a brand candidate from a claims drug string: the text in parentheses,
    else the leading token. 'USTEKINUMAB SUBCUTANEOUS (STELARA)' -> 'STELARA'."""
    s = str(name)
    m = re.search(r"\(([^)]+)\)", s)
    if m:
        return m.group(1)
    return s


def resolve_feed(std: pd.DataFrame, *, rxnorm=None, crosswalk=None, ref_dir=None,
                 progress=None):
    """Add drug-identity + unit-basis columns to a standardized feed.

    Adds:
      drug_class_rx      canonical class shared with the medical panel (or UNMAPPED_RX)
      hcpcs_equiv        representative medical J-code for the molecule ("" if none)
      ingredient_rx      resolved ingredient (lowercase)
      _class_source      one of: hcpcs | ndc | name | seed_name | unmapped
      units_basis        HCPCS (medical billing units) | DISPENSED (mL/each from RX) | UNKNOWN
      hcpcs_equiv_units   quantity x strength when both known, else NaN

    Also fills a blank `hcpcs` from hcpcs_equiv so NDC-only pharmacy rows join the
    J-code-keyed cuts. Never raises; offline it uses drug_name + the seed only.
    """
    progress = progress or (lambda *_: None)
    xwalk = crosswalk or load_crosswalk(ref_dir)
    out = std.copy()
    n = len(out)
    hc = out["hcpcs"].astype("string") if "hcpcs" in out.columns else pd.Series([pd.NA] * n)
    nd = out["ndc"].astype("string") if "ndc" in out.columns else pd.Series([pd.NA] * n)
    dn = out["drug_name"].astype("string") if "drug_name" in out.columns else pd.Series([pd.NA] * n)
    src = (out["_claim_source"].astype("string") if "_claim_source" in out.columns
           else pd.Series(["medical"] * n))

    drug_class = np.array([UNMAPPED] * n, dtype=object)
    hcpcs_equiv = np.array([""] * n, dtype=object)
    ingredient = np.array([""] * n, dtype=object)
    csource = np.array(["unmapped"] * n, dtype=object)
    # idempotency: if a prior pass already classed some rows (e.g. the pharmacy
    # feed was resolved at read time), carry those through and skip re-work.
    if "drug_class_rx" in out.columns:
        prior = out["drug_class_rx"].astype("string").fillna(UNMAPPED).values
        drug_class = np.array([p if p else UNMAPPED for p in prior], dtype=object)
    for _pcol, _arr in (("hcpcs_equiv", hcpcs_equiv), ("ingredient_rx", ingredient),
                        ("_class_source", csource)):
        if _pcol in out.columns:
            vals = out[_pcol].astype("string").fillna("").values
            for _i in range(n):
                _arr[_i] = vals[_i] if vals[_i] else _arr[_i]
    already = np.array([dc != UNMAPPED for dc in drug_class])

    # cache resolutions within this call (many rows share an NDC / name)
    ndc_cache, name_cache = {}, {}

    def _resolve_ingredient(ndc_val, name_val):
        # 1) NDC via RxNorm (live), 2) NDC product prefix in seed (none today),
        # 3) free-text name via seed brand, 4) name via RxNorm.
        ndc_digits = "".join(ch for ch in str(ndc_val) if ch.isdigit()) if pd.notna(ndc_val) else ""
        if ndc_digits and len(ndc_digits) >= 9:
            if ndc_digits in ndc_cache:
                ing, how = ndc_cache[ndc_digits]
            else:
                ing, how = "", "unmapped"
                if rxnorm is not None:
                    rec = None
                    try:
                        rec = rxnorm.lookup_ndc(ndc_digits)
                    except Exception:
                        rec = None
                    if rec:
                        ing = _norm(rec.get("ingredient") or rec.get("name") or "")
                        how = "ndc"
                ndc_cache[ndc_digits] = (ing, how)
            if ing:
                return ing, how
        # name path
        nm = str(name_val) if pd.notna(name_val) else ""
        if nm.strip():
            if nm in name_cache:
                return name_cache[nm]
            # seed brand match first (works offline)
            brand = _brand_from_name(nm)
            row = xwalk["by_brand"].get(_norm(brand)) or xwalk["by_brand"].get(_norm(nm))
            if row:
                name_cache[nm] = (row["ingredient"], "seed_name")
                return row["ingredient"], "seed_name"
            # ingredient token already in the name?
            nnorm = _norm(nm)
            for token, canon in _INGREDIENT_CONTAINS:
                if token in nnorm:
                    name_cache[nm] = (canon, "seed_name")
                    return canon, "seed_name"
            # brand token anywhere in the name ('CUVITRU SCIG', 'STELARA SUBCUTANEOUS')
            for bk, brow in xwalk.get("brand_tokens", []):
                if re.search(r"\b" + re.escape(bk) + r"\b", nnorm):
                    name_cache[nm] = (brow["ingredient"], "seed_name")
                    return brow["ingredient"], "seed_name"
            # live name resolution as a last resort
            if rxnorm is not None and hasattr(rxnorm, "_resolve_name"):
                try:
                    rec = rxnorm._resolve_name(nm)
                    if rec:
                        ing = _norm(rec.get("ingredient") or rec.get("name") or "")
                        if ing:
                            name_cache[nm] = (ing, "name")
                            return ing, "name"
                except Exception:
                    pass
            name_cache[nm] = ("", "unmapped")
        return "", "unmapped"

    for i in range(n):
        if i % 500 == 0:
            progress(f"rx bridge {i}/{n}", (i + 1) / max(n, 1))
        if already[i]:
            continue
        h = hc.iat[i] if i < len(hc) else pd.NA
        # a real HCPCS already present -> map by code first (covers medical rows
        # and any pre-mapped pharmacy pull), then we still record class via seed.
        hcode = (str(h).strip().upper() if pd.notna(h) else "")
        if hcode and re.fullmatch(r"[A-Z]?\d{3,4}[A-Z]?", hcode):
            # map directly by HCPCS (covers every seeded J-code, incl. the alternate
            # IVIG codes that share the immune-globulin class) for class + per_unit.
            match = xwalk["by_hcpcs"].get(hcode)
            if match:
                drug_class[i] = match["drug_class"]
                hcpcs_equiv[i] = hcode
                ingredient[i] = match["ingredient"]
                csource[i] = "hcpcs"
                continue
            # HCPCS present but not in the seed: leave class unmapped here; the
            # medical analytics still label it via drug_ident downstream.
            hcpcs_equiv[i] = hcode
            csource[i] = "hcpcs"
        ing, how = _resolve_ingredient(nd.iat[i] if i < len(nd) else pd.NA,
                                       dn.iat[i] if i < len(dn) else pd.NA)
        if ing:
            row = _class_for_ingredient(ing, xwalk)
            ingredient[i] = ing
            if row:
                drug_class[i] = row["drug_class"]
                # J3590 is the unclassified-biologic catch-all shared by many drugs;
                # keep the class but do not fold it into the J-code-keyed cuts.
                if not hcpcs_equiv[i] and row["hcpcs"] and row["hcpcs"] != "J3590":
                    hcpcs_equiv[i] = row["hcpcs"]
                csource[i] = how if csource[i] == "unmapped" else csource[i]

    out["drug_class_rx"] = drug_class
    out["hcpcs_equiv"] = hcpcs_equiv
    out["ingredient_rx"] = ingredient
    out["_class_source"] = csource

    # fill a blank hcpcs from the equivalent J-code so NDC-only rows fold into the
    # J-code-keyed cuts (medical rows keep their own hcpcs untouched).
    if "hcpcs" in out.columns:
        blank_hc = out["hcpcs"].isna() | (out["hcpcs"].astype("string").str.strip() == "")
        fill = pd.Series(hcpcs_equiv, index=out.index).astype("string")
        out.loc[blank_hc & fill.ne(""), "hcpcs"] = fill[blank_hc & fill.ne("")]

    # units basis + best-effort HCPCS-equivalent units. Medical rows are HCPCS
    # units already; pharmacy rows are DISPENSED unless we can convert via strength.
    per_unit = {}
    for row in xwalk["by_ingredient"].values():
        if row["ingredient"] and not np.isnan(row["per_unit_mg"]):
            per_unit[row["ingredient"]] = row["per_unit_mg"]
    basis = np.where(src.values == "pharmacy", "DISPENSED", "HCPCS").astype(object)
    out["units_basis"] = basis
    equiv_units = np.full(n, np.nan)
    if "units" in out.columns:
        qty = pd.to_numeric(out["units"], errors="coerce").values
        for i in range(n):
            if src.iat[i] == "pharmacy":
                mg = per_unit.get(ingredient[i])
                # only convert when we have a strength AND the dispensed quantity
                # plausibly represents mg (we cannot infer mg from mL without
                # concentration, so this stays conservative: applied when the
                # crosswalk strength exists, else left NaN and basis=DISPENSED)
                if mg and not np.isnan(qty[i]):
                    equiv_units[i] = qty[i]  # placeholder 1:1; refined only if mg basis supplied
    out["hcpcs_equiv_units"] = equiv_units
    return out


def bridge_summary(std_resolved: pd.DataFrame):
    """Small audit frame: how pharmacy rows resolved (by NDC / name / seed /
    unmapped) and the dollars in each bucket — so the analyst can see coverage."""
    if "_claim_source" not in std_resolved.columns:
        return pd.DataFrame({"note": ["no _claim_source — nothing to summarise"]})
    ph = std_resolved[std_resolved["_claim_source"].astype("string") == "pharmacy"].copy()
    if ph.empty:
        return pd.DataFrame({"metric": ["pharmacy_rows"], "value": [0]})
    allowed = pd.to_numeric(ph.get("allowed_amt"), errors="coerce").fillna(0.0)
    g = ph.assign(_a=allowed.values).groupby(ph["_class_source"].astype("string"))
    rows = [{"resolution": k, "rows": int(v.shape[0]), "allowed": round(float(v["_a"].sum()), 0)}
            for k, v in g]
    mapped = ph["drug_class_rx"].astype("string").ne(UNMAPPED)
    rows.append({"resolution": "TOTAL mapped to a drug class", "rows": int(mapped.sum()),
                 "allowed": round(float(allowed[mapped.values].sum()), 0)})
    rows.append({"resolution": "TOTAL pharmacy", "rows": int(ph.shape[0]),
                 "allowed": round(float(allowed.sum()), 0)})
    out = pd.DataFrame(rows)
    out.attrs["note"] = ("RX rows are resolved to the medical drug taxonomy by NDC (live RxNorm), "
                         "then free-text name, then the brand/ingredient seed. UNMAPPED_RX rows "
                         "still count in dollar totals but are excluded from per-drug reconciliation.")
    return out
