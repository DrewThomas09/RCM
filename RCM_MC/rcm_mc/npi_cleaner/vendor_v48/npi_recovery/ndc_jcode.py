"""ndc_jcode (v31): deterministic NDC -> BEST J-code disambiguation.

Why this exists — the second thing the data team was stuck on:
    "I pulled in the NDCs we have in Komodo, and some of them are mapped to a J
     code. Some are mapped to MULTIPLE potential codes, and the idea was to find
     the code that BEST matches, because to map it in the CMS data we need the
     J-code to get the average spend per beneficiary."
and the guardrail Joe insisted on:
    "not all NDCs are going to have a J-code and we should not force-map it,
     because that would just be wrong."

An NDC / brand often has several plausible J-codes: its own brand-specific
descriptor code, a non-specific NOS code inside the same class (immune globulin
-> J1599), and an unclassified catch-all (J3590 / C9399 / J9999). The rx_bridge
picks ONE representative code per ingredient (fine for grouping to a common name)
but that is not necessarily the right code to *price against CMS ASP*.

The decision is brand-first and defensible — the standard being "no embarrassing
claim if someone clicks the link":
  1. brand identified AND it has its own specific code -> use that code (a real
     brand descriptor). Cuvitru -> J1555, Gammagard -> J1569, Stelara -> J3357.
  2. brand identified but its ONLY code is an unclassified catch-all (a biosimilar
     or pharmacy-only NOC drug, e.g. Wezlana -> J3590) -> DO NOT borrow another
     brand's code; keep it as an NDC, flagged.
  3. brand NOT identified but the ingredient is -> use a shared class code, i.e.
     the class NOS code (IVIG -> J1599) or a code common to several brands; never
     a single other brand's exclusive code.
  4. nothing resolvable, or only single-brand codes with no brand match ->
     NO_JCODE_KEEP_AS_NDC. Never invent.
When a CMS-ASP-priced-codes set is supplied, an ASP-priced candidate is preferred
among otherwise-tied options (the whole point is to price against CMS). Fully
deterministic, offline-safe, no LLM / scipy / sklearn.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config
from . import rx_bridge as _rxb


def _route_of(text) -> str:
    """SC | IV | '' from a drug-name / route string. 'IVIG' is NOT an IV signal."""
    s = str(text or "").lower()
    if re.search(r"\b(subcut|subcutaneous|sub-q|sub q)\b", s) or re.search(r"\bsc\b", s):
        return "SC"
    if re.search(r"\b(intraven|infus)\b", s) or re.search(r"\biv\b", s):
        return "IV"
    return ""


def _benefit_route(benefit) -> str:
    b = str(benefit or "").lower()
    if b == "pharmacy":
        return "SC"
    if b == "medical":
        return "IV"
    return ""


def _is_nos(code, descriptor="") -> bool:
    c = str(code).strip().upper()
    d = str(descriptor or "").lower()
    return (c in config.NOS_CODES) or ("nos" in d) or ("not otherwise specified" in d)


def _find_brand_row(brand_name, xwalk):
    """Resolve a claims drug string to its crosswalk brand row. Tries the full
    normalized string, the parenthesized brand, the leading 1-2 tokens, then a
    brand token appearing anywhere. Returns (row, matched_key) or (None, '')."""
    if not str(brand_name).strip():
        return None, ""
    by_brand = xwalk["by_brand"]
    full = _rxb._norm(brand_name)
    paren = _rxb._norm(_rxb._brand_from_name(brand_name))
    toks = full.split()
    lead1 = toks[0] if toks else ""
    lead2 = " ".join(toks[:2]) if len(toks) >= 2 else ""
    for k in (full, paren, lead2, lead1):
        if k and k in by_brand:
            return by_brand[k], k
    for bk, brow in xwalk.get("brand_tokens", []):
        if re.search(r"\b" + re.escape(bk) + r"\b", full):
            return brow, bk
    return None, ""


def _ingredient_code_index(ingredient_norm, xwalk):
    """For one ingredient: the list of {hcpcs, brands, is_nos, route, is_catchall}
    across the crosswalk, and the set of codes that are a SINGLE real brand's
    exclusive specific code (so another drug never steals them)."""
    per_code = {}
    for b, row in xwalk["by_brand"].items():
        if row.get("ingredient") != ingredient_norm:
            continue
        code = str(row.get("hcpcs", "")).strip().upper()
        if not code:
            continue
        rec = per_code.setdefault(code, {"hcpcs": code, "brands": set(),
                                         "is_nos": _is_nos(code), "route": _benefit_route(row.get("benefit")),
                                         "is_catchall": config.is_catchall_code(code)})
        # pseudo-brands like 'IVIG NOS' are not real exclusive brands
        if not rec["is_nos"] and not rec["is_catchall"]:
            rec["brands"].add(b)
    exclusive = {c: rec["brands"] for c, rec in per_code.items()
                 if len(rec["brands"]) == 1 and not rec["is_nos"] and not rec["is_catchall"]}
    return per_code, exclusive


def candidates_for(brand_name, ingredient_key, xwalk, *, row_route="", asp_codes=None):
    """Return (decision) for a brand/ingredient as a dict:
       {best, candidates(ordered list of codes), reason, confidence, disposition}.
    Pure function of the crosswalk + inputs; used by resolve_best_jcode and tests.
    """
    asp = {str(c).strip().upper() for c in (asp_codes or set())}
    brand_row, matched_key = _find_brand_row(brand_name, xwalk)

    # establish the ingredient we are working in
    ing_norm = ""
    if brand_row and brand_row.get("ingredient"):
        ing_norm = brand_row["ingredient"]
    else:
        nk = _rxb._norm(ingredient_key)
        if nk in xwalk["by_ingredient"]:
            ing_norm = nk
        else:
            r = _rxb._class_for_ingredient(nk, xwalk)
            ing_norm = r["ingredient"] if r else nk

    per_code, exclusive = _ingredient_code_index(ing_norm, xwalk)
    ordered = _rank(list(per_code.values()), row_route, asp)
    cand_list = [c["hcpcs"] for c in ordered]

    # 1. brand identified with its own specific (non-catch-all) code
    if brand_row:
        own = str(brand_row.get("hcpcs", "")).strip().upper()
        if own and not config.is_catchall_code(own):
            conf = "high"
            reason = "brand-specific descriptor code"
            brow_route = _benefit_route(brand_row.get("benefit"))
            if row_route and brow_route and row_route != brow_route:
                conf, reason = "medium", "brand-specific code (route conflict noted)"
            return {"best": own, "candidates": cand_list, "reason": reason,
                    "confidence": conf, "disposition": "BRAND_SPECIFIC"}
        # 2. brand's only code is a catch-all -> do not borrow another brand's code
        return {"best": "", "candidates": cand_list,
                "reason": "brand's only HCPCS is an unclassified catch-all (e.g. biosimilar/NOC) — not force-mapped",
                "confidence": "none", "disposition": "NO_JCODE_KEEP_AS_NDC"}

    # 3. brand unknown, ingredient known -> shared class code only (NOS, or a code
    #    used by >1 brand). Never a single other brand's exclusive code.
    shared = [c for c in ordered
              if not c["is_catchall"] and c["hcpcs"] not in exclusive]
    if shared:
        # brand unknown -> prefer the class NOS code (claiming a specific product
        # we cannot identify is the embarrassing case); an ASP-priced NOS wins.
        nos = [c for c in shared if c["is_nos"]]
        best = (sorted(nos, key=lambda c: (-(c["hcpcs"] in asp), c["hcpcs"]))[0]
                if nos else shared[0])
        if best["is_nos"]:
            reason, conf = "class NOS code (specific brand unknown)", "medium"
            disp = "SPECIFICITY"
        elif best["hcpcs"] in asp:
            reason, conf = "shared class code with a CMS ASP price (specific brand unknown)", "medium"
            disp = "ASP_PREFERRED"
        else:
            reason, conf = "shared class code (specific brand unknown)", "low"
            disp = "SPECIFICITY"
        return {"best": best["hcpcs"], "candidates": cand_list, "reason": reason,
                "confidence": conf, "disposition": disp}

    # 4. only single-brand exclusive codes and we cannot tell which brand
    if ordered:
        return {"best": "", "candidates": cand_list,
                "reason": "ingredient known but brand/code ambiguous (only brand-exclusive codes) — not force-mapped",
                "confidence": "none", "disposition": "NO_JCODE_KEEP_AS_NDC"}
    return {"best": "", "candidates": [], "reason": "no candidate J-code for this NDC/ingredient",
            "confidence": "none", "disposition": "NO_JCODE_KEEP_AS_NDC"}


def _rank(codes, row_route, asp):
    """Order candidate code records best-first (display + shared-pick)."""
    for c in codes:
        route_match = 1 if (row_route and c["route"] and row_route == c["route"]) else 0
        route_conflict = 1 if (row_route and c["route"] and row_route != c["route"]) else 0
        spec = 1 if c["is_catchall"] else (2 if c["is_nos"] else 3)
        c["_score"] = (100 * route_match - 100 * route_conflict + 10 * spec
                       + 5 * int(c["hcpcs"] in asp))
    return sorted(codes, key=lambda c: (-c["_score"], c["hcpcs"]))


def resolve_best_jcode(std: pd.DataFrame, *, crosswalk=None, ref_dir=None,
                       rxnorm=None, asp_codes=None, progress=None) -> pd.DataFrame:
    """Add best-J-code columns to a standardized frame.

    Adds: hcpcs_best, hcpcs_candidates, hcpcs_best_reason, hcpcs_best_confidence,
    _best_disposition (ALREADY_HAS_HCPCS | BRAND_SPECIFIC | ROUTE_MATCH |
    ASP_PREFERRED | SPECIFICITY | NO_JCODE_KEEP_AS_NDC).

    A row already carrying a real (non-catch-all) HCPCS keeps it — the resolver
    targets NDC-only / catch-all rows that need a code to hit CMS. Never raises.
    """
    progress = progress or (lambda *_: None)
    xwalk = crosswalk or _rxb.load_crosswalk(ref_dir)
    out = std.copy()
    n = len(out)

    def _col(c):
        return out[c].astype("string") if c in out.columns else pd.Series([pd.NA] * n)

    hc, nd, dn = _col("hcpcs"), _col("ndc"), _col("drug_name")
    key, ingrx = _col("drug_common_key"), _col("ingredient_rx")

    best = np.array([""] * n, dtype=object)
    cand_str = np.array([""] * n, dtype=object)
    reason = np.array([""] * n, dtype=object)
    conf = np.array(["none"] * n, dtype=object)
    disp = np.array([""] * n, dtype=object)

    cache = {}
    for i in range(n):
        if i % 1000 == 0:
            progress(f"ndc->jcode {i}/{n}", (i + 1) / max(n, 1))
        code = (str(hc.iat[i]).strip().upper() if i < len(hc) and pd.notna(hc.iat[i]) else "")
        if code and re.fullmatch(r"[A-Z]?\d{3,4}[A-Z]?", code) and not config.is_catchall_code(code):
            best[i] = code
            reason[i] = "row already carries a specific HCPCS"
            conf[i] = "high"
            disp[i] = "ALREADY_HAS_HCPCS"
            continue
        brand = str(dn.iat[i]) if i < len(dn) and pd.notna(dn.iat[i]) else ""
        ing = (str(key.iat[i]) if i < len(key) and pd.notna(key.iat[i]) and str(key.iat[i]).strip()
               else (str(ingrx.iat[i]) if i < len(ingrx) and pd.notna(ingrx.iat[i]) else ""))
        row_route = _route_of(brand)
        ck = (_rxb._norm(brand), _rxb._norm(ing), row_route)
        if ck in cache:
            dec = cache[ck]
        else:
            dec = candidates_for(brand, ing, xwalk, row_route=row_route, asp_codes=asp_codes)
            cache[ck] = dec
        best[i] = dec["best"]
        cand_str[i] = ">".join(dec["candidates"])
        reason[i] = dec["reason"]
        conf[i] = dec["confidence"]
        disp[i] = dec["disposition"]

    out["hcpcs_best"] = best
    out["hcpcs_candidates"] = cand_str
    out["hcpcs_best_reason"] = reason
    out["hcpcs_best_confidence"] = conf
    out["_best_disposition"] = disp
    return out


def bestmatch_audit(std_resolved, allowed=None, only_multi=True):
    """One row per distinct (ingredient, brand) that had MORE THAN ONE candidate:
    chosen code, alternatives, reason, confidence, dollars — for spot-checking."""
    if "hcpcs_best" not in std_resolved.columns:
        return pd.DataFrame({"note": ["run resolve_best_jcode first"]})
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std_resolved.get("allowed_amt"), errors="coerce").fillna(0.0))
    df = std_resolved.assign(_a=a.values)
    df["_brand"] = df.get("drug_name", "").astype("string").fillna("")
    df["_key"] = df.get("drug_common_key", "").astype("string").fillna("")
    df["_ncand"] = df["hcpcs_candidates"].astype("string").fillna("").str.count(">") + 1
    if only_multi:
        df = df[(df["_ncand"] > 1) & df["_best_disposition"].ne("ALREADY_HAS_HCPCS")]
    if df.empty:
        return pd.DataFrame({"note": ["no NDC/brand had multiple candidate J-codes to disambiguate"]})
    g = (df.groupby(["_key", "_brand", "hcpcs_best", "hcpcs_candidates",
                     "hcpcs_best_reason", "hcpcs_best_confidence", "_best_disposition"])
         .agg(rows=("_a", "size"), allowed=("_a", "sum")).reset_index()
         .sort_values("allowed", ascending=False)
         .rename(columns={"_key": "drug_common_key", "_brand": "drug_name"}))
    g["allowed"] = g["allowed"].round(2)
    g.attrs["note"] = ("Every NDC / brand that mapped to more than one candidate J-code and the single "
                       "best code chosen. brand-specific > class NOS/shared > CMS-ASP-priced. A blank "
                       "best with disposition NO_JCODE means it was deliberately not force-mapped.")
    return g


def no_jcode_audit(std_resolved, allowed=None):
    """Rows deliberately LEFT without a J-code (no-force-map rule) and the dollars
    at stake — the decision made explicit rather than a silent gap."""
    if "_best_disposition" not in std_resolved.columns:
        return pd.DataFrame({"note": ["run resolve_best_jcode first"]})
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std_resolved.get("allowed_amt"), errors="coerce").fillna(0.0))
    df = std_resolved.assign(_a=a.values)
    nj = df[df["_best_disposition"] == "NO_JCODE_KEEP_AS_NDC"]
    if nj.empty:
        return pd.DataFrame({"metric": ["rows_kept_as_ndc"], "value": [0],
                             "note": ["every row resolved to a real J-code — nothing force-mapped or dropped"]})
    nj = nj.assign(drug_name=nj.get("drug_name", "").astype("string").fillna(""),
                   ndc=nj.get("ndc", "").astype("string").fillna(""))
    g = (nj.groupby(["drug_name", "ndc", "hcpcs_best_reason"])
         .agg(rows=("_a", "size"), allowed=("_a", "sum")).reset_index()
         .sort_values("allowed", ascending=False))
    g["allowed"] = g["allowed"].round(2)
    tot = pd.DataFrame([{"drug_name": "TOTAL kept as NDC (no J-code invented)", "ndc": "",
                         "hcpcs_best_reason": "", "rows": int(nj.shape[0]),
                         "allowed": round(float(nj["_a"].sum()), 2)}])
    out = pd.concat([g, tot], ignore_index=True)
    out.attrs["note"] = ("These NDCs had no defensible J-code (no candidate, only a catch-all, or an "
                         "ambiguous class). Per the team's rule they are NOT force-mapped: they keep "
                         "their NDC, still count in dollar totals, and are listed for a conscious call.")
    return out
