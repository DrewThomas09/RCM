"""
sad_jurisdiction.py  (v39)
==========================

The item carried in every changelog since v33, now shipped: jurisdiction-aware
self-administered-drug (SAD) classification. A drug excluded from Part B in one
MAC jurisdiction may be billable in another, and the same molecule can be Part B
eligible by one route and SAD by another (Orencia IV under modifier JA is
covered; subcutaneous under JB is self-administered and excluded). A flat
"SAD or not" flag gets both of these wrong.

This module reads a real CMS Coverage snapshot (shipped reference CSVs, sourced
from the Self-Administered Drug Exclusion List and the MAC roster) and answers,
per claim: given this HCPCS, this billing state, and any modifier, is the line
Part B eligible, SAD-excluded, or route-ambiguous. It maps state to MAC, checks
the code against that MAC's exclusion set, and applies the JA/JB route rule.

The classification is deterministic and offline against the shipped snapshot. An
optional refresh_from_cms hook re-pulls the live list when a connector callable
is supplied, so the snapshot never goes stale silently.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# route modifiers that flip SAD status: JA = intravenous (provider-administered,
# Part B eligible), JB = subcutaneous (self-administered, excluded).
MOD_IV = {"JA"}
MOD_SC = {"JB"}
_MISC_CODES = {"J3490", "J3590", "J9999", "C9399", "Q9999"}

# SAD article id -> MAC id. The eight per-MAC articles; Noridian publishes two
# (JE=A53032, JF=A53033), so the article disambiguates where the contractor name
# alone cannot. Used to normalize a live CMS pull back to MAC ids.
_ARTICLE_TO_MAC = {
    "A53021": "NGS", "A52800": "WPS", "A52527": "CGS",
    "A53032": "NORIDIAN_JE", "A53033": "NORIDIAN_JF",
    "A53127": "NOVITAS", "A52571": "FCSO", "A53066": "PALMETTO",
}
# contractor-name substring -> MAC id, the fallback when no article id is present.
# Noridian falls back to JE (its larger jurisdiction) if the article is missing.
_NAME_TO_MAC = [
    ("national government", "NGS"), ("wps", "WPS"), ("cgs", "CGS"),
    ("noridian", "NORIDIAN_JE"), ("novitas", "NOVITAS"),
    ("first coast", "FCSO"), ("palmetto", "PALMETTO"),
]


def _item_to_mac(item: dict) -> str:
    """Best-effort MAC id for one live CMS SAD row. Prefer the article id
    (disambiguates Noridian JE/JF), else the contractor name."""
    art = str(item.get("document_display_id") or "").strip().upper()
    if not art:
        did = item.get("document_id")
        art = ("A" + str(did)) if did not in (None, "") else ""
    if art in _ARTICLE_TO_MAC:
        return _ARTICLE_TO_MAC[art]
    name = str(item.get("contractor_name_type") or item.get("contractor") or "").lower()
    for frag, mac in _NAME_TO_MAC:
        if frag in name:
            return mac
    return ""


def route_note_from_text(text: str) -> str:
    """Parse the route rule out of a CMS brand/description string. The list
    encodes route in prose: a JA/JB mention means the IV form is Part B eligible
    and the SC form is excluded; a bare 'subcutaneous' means SC self-administered;
    an unclassified/NOC code means resolve the drug by NDC first."""
    t = str(text or "").lower()
    if ("jb" in t and "ja" in t) or "modifier decides" in t:
        return "JA=IV (Part B eligible), JB=SC (SAD); modifier decides"
    if "unclassified" in t or "miscellaneous" in t:
        return "NOC / miscellaneous code; resolve drug by NDC before routing"
    if "subcutaneous" in t or "self-inject" in t or "self administered" in t \
            or "self-administered" in t:
        return "SUBCUTANEOUS self-administered; SAD"
    return "on the SAD exclusion list for the listed MAC(s)"


def _read_seed(ref_dir, name) -> pd.DataFrame:
    p = Path(ref_dir) / name if ref_dir else None
    if p and p.exists():
        try:
            return pd.read_csv(p, dtype=str).fillna("")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def load_mac_map(ref_dir) -> dict:
    """state (upper) -> contractor_id, from the shipped MAC roster."""
    df = _read_seed(ref_dir, "mac_jurisdictions_seed.csv")
    if df.empty:
        return {}
    out = {}
    for _, r in df.iterrows():
        cid = str(r.get("contractor_id", "")).strip()
        for st in str(r.get("jurisdiction_states", "")).split(","):
            st = st.strip().upper()
            if st and cid:
                out[st] = cid
    return out


def load_sad_table(ref_dir) -> pd.DataFrame:
    """The shipped SAD snapshot, one row per (hcpcs, drug) with the MAC set and
    the route note parsed into a coarse rule."""
    df = _read_seed(ref_dir, "sad_exclusion_seed.csv")
    if df.empty:
        return pd.DataFrame(columns=["hcpcs", "macs", "route_rule"])
    df["hcpcs"] = df["hcpcs"].str.strip().str.upper()
    df["mac_set"] = df["macs"].map(lambda s: {m.strip() for m in str(s).split(",") if m.strip()})

    def _rule(note):
        n = str(note).lower()
        if "jb" in n or ("modifier decides" in n) or ("modifier" in n and "ja" in n):
            return "ROUTE_DEPENDENT"  # IV eligible, SC excluded
        if "subcutaneous" in n or "self-inject" in n or "self injected" in n:
            return "SC_EXCLUDED"
        return "EXCLUDED"

    df["route_rule"] = df["route_note"].map(_rule)
    return df


def load_sad_full(ref_dir) -> pd.DataFrame:
    """The long, source-faithful SAD snapshot: one row per (article, MAC, code,
    brand) with the real CMS article URL. This is the audit trail behind the
    collapsed seed; every row is click-through verifiable. Empty frame if the
    file is not shipped (older packages)."""
    df = _read_seed(ref_dir, "sad_exclusion_full.csv")
    if df.empty:
        return pd.DataFrame(columns=["article_id", "mac_id", "code_id",
                                     "drug_brand_name", "url"])
    return df


def build_sad_index(ref_dir) -> dict:
    """{hcpcs: {mac_set, route_rule, molecule, drug_brand}} for O(1) lookup."""
    tbl = load_sad_table(ref_dir)
    idx = {}
    for _, r in tbl.iterrows():
        idx[r["hcpcs"]] = {"mac_set": r.get("mac_set", set()),
                           "route_rule": r.get("route_rule", "EXCLUDED"),
                           "molecule": r.get("molecule", ""),
                           "drug_brand": r.get("drug_brand", "")}
    return idx


def classify_row(hcpcs, state, modifier, *, mac_map, sad_index) -> tuple[str, str]:
    """Return (verdict, rationale) for one line. Verdicts:
      PART_B_ELIGIBLE       not on the SAD list for this MAC, or billed IV (JA)
      SAD_EXCLUDED          on the SAD list for this MAC (route confirms or n/a)
      SAD_EXCLUDED_SC       route-dependent code billed subcutaneous (JB)
      ROUTE_AMBIGUOUS       route-dependent code with no modifier to decide
      UNKNOWN_JURISDICTION  state does not map to a known MAC in the snapshot
    """
    # NA-safe scalars: a standardized frame materializes unmapped columns as
    # pandas NA, and `pd.NA or ""` raises ("boolean value of NA is
    # ambiguous") while str(NA) is the literal "<NA>" — both poisoned the
    # classification when the file had no modifier/state column.
    def _s(v):
        try:
            if v is None or pd.isna(v):
                return ""
        except (TypeError, ValueError):
            pass
        return str(v)

    code = _s(hcpcs).strip().upper()
    st = _s(state).strip().upper()
    mods = {m.strip().upper() for m in _s(modifier).replace(",", " ").split() if m.strip()}
    entry = sad_index.get(code)
    if entry is None:
        return "PART_B_ELIGIBLE", "code not on the SAD snapshot (provider-administered)"
    mac = mac_map.get(st)
    if st and mac is None:
        return "UNKNOWN_JURISDICTION", "billing state {} not mapped to a MAC in the snapshot".format(st)
    if mac is not None and entry["mac_set"] and mac not in entry["mac_set"]:
        return "PART_B_ELIGIBLE", "not excluded by {} (excluded only in {})".format(
            mac, ", ".join(sorted(entry["mac_set"])))
    rule = entry["route_rule"]
    if rule == "ROUTE_DEPENDENT":
        if mods & MOD_IV:
            return "PART_B_ELIGIBLE", "billed IV (JA); provider-administered form is covered"
        if mods & MOD_SC:
            return "SAD_EXCLUDED_SC", "billed subcutaneous (JB); self-administered form excluded"
        return "ROUTE_AMBIGUOUS", "route-dependent code with no JA/JB modifier; cannot decide"
    if rule == "SC_EXCLUDED":
        if mods & MOD_IV:
            return "PART_B_ELIGIBLE", "billed IV (JA) despite SC-typical listing"
        return "SAD_EXCLUDED", "subcutaneous self-administered drug on {}'s SAD list".format(mac or "the MAC")
    return "SAD_EXCLUDED", "on {}'s SAD list".format(mac or "the MAC")


def classify_frame(std: pd.DataFrame, *, ref_dir, allowed=None,
                   hcpcs_col="hcpcs", state_col="state",
                   modifier_col=None) -> pd.DataFrame:
    """Per-verdict rollup with rows and dollars, plus the ambiguous and
    jurisdiction-gap lines called out. The exposure lens: how much panel spend
    sits on codes whose Part B eligibility depends on jurisdiction or route."""
    mac_map = load_mac_map(ref_dir)
    sad_index = build_sad_index(ref_dir)
    if not sad_index:
        return pd.DataFrame({"note": ["SAD snapshot not found; ship "
                                      "sad_exclusion_seed.csv and mac_jurisdictions_seed.csv"]})
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0))
    hc = std.get(hcpcs_col, pd.Series("", index=std.index)).fillna("")
    stt = std.get(state_col, pd.Series("", index=std.index)).fillna("")
    mod_col = modifier_col or next(
        (c for c in ("modifier", "modifiers", "mod", "modifier_1") if c in std.columns), None)
    md = (std.get(mod_col, pd.Series("", index=std.index)) if mod_col
          else pd.Series("", index=std.index)).fillna("")

    verdicts, rats = [], []
    for h, s, m in zip(hc, stt, md):
        v, r = classify_row(h, s, m, mac_map=mac_map, sad_index=sad_index)
        verdicts.append(v)
        rats.append(r)
    vs = pd.Series(verdicts, index=std.index)
    tot = float(a.sum())
    rows = []
    for v in ["PART_B_ELIGIBLE", "SAD_EXCLUDED", "SAD_EXCLUDED_SC",
              "ROUTE_AMBIGUOUS", "UNKNOWN_JURISDICTION"]:
        mask = vs == v
        n = int(mask.sum())
        if n == 0:
            continue
        rows.append({"verdict": v, "rows": n, "dollars": round(float(a[mask].sum()), 2),
                     "pct_dollars": round(float(a[mask].sum()) / tot * 100, 1) if tot > 0 else 0.0})
    out = pd.DataFrame(rows)
    amb = float(a[vs.isin(["ROUTE_AMBIGUOUS", "UNKNOWN_JURISDICTION"])].sum())
    out.attrs["ambiguous_dollars"] = round(amb, 2)
    out.attrs["verdict_series"] = vs
    out.attrs["rationale_series"] = pd.Series(rats, index=std.index)
    out.attrs["snapshot_codes"] = len(sad_index)
    # A small shipped snapshot means PART_B_ELIGIBLE is a floor, not a
    # clearance — codes outside the slice default to eligible. Disclose the
    # coverage inline so a rollup rendered from this frame cannot read as
    # authoritative when the seed is a 15-code slice of the ~1,502-row list.
    coverage = ("" if len(sad_index) >= 1000 else
                " Snapshot covers {} HCPCS codes — a curated slice of the "
                "~1,502-row CMS SAD list; codes outside it read as "
                "PART_B_ELIGIBLE, so treat eligibility as a floor. Refresh "
                "via refresh_from_cms for full coverage.".format(len(sad_index)))
    out.attrs["note"] = (
        "Jurisdiction- and route-aware SAD read against the shipped CMS snapshot. "
        "ROUTE_AMBIGUOUS and UNKNOWN_JURISDICTION dollars ({}) are the lines to resolve "
        "with a modifier or a state before treating them as Part B.".format(round(amb, 2))
        + coverage)
    return out


def ambiguous_lines(std: pd.DataFrame, classification: pd.DataFrame, *,
                    allowed=None, hcpcs_col="hcpcs", top_n: int = 40) -> pd.DataFrame:
    """The worklist: the specific route-ambiguous and jurisdiction-gap rows,
    with the code, state, dollars, and what would resolve each."""
    vs = classification.attrs.get("verdict_series") if hasattr(classification, "attrs") else None
    rs = classification.attrs.get("rationale_series") if hasattr(classification, "attrs") else None
    if vs is None:
        return pd.DataFrame({"note": ["run classify_frame first"]})
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0) if allowed is not None
         else pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0))
    sel = vs.isin(["ROUTE_AMBIGUOUS", "UNKNOWN_JURISDICTION"])
    if not sel.any():
        return pd.DataFrame({"note": ["no route-ambiguous or jurisdiction-gap lines"]})
    df = pd.DataFrame({
        "hcpcs": std.get(hcpcs_col, pd.Series("", index=std.index))[sel].astype(str),
        "state": std.get("state", pd.Series("", index=std.index))[sel].astype(str),
        "verdict": vs[sel], "dollars": a[sel].round(2),
        "resolve_by": rs[sel] if rs is not None else ""})
    out = df.sort_values("dollars", ascending=False).head(top_n).reset_index(drop=True)
    out.attrs["note"] = ("Resolve ROUTE_AMBIGUOUS with the JA/JB modifier; resolve "
                         "UNKNOWN_JURISDICTION by supplying the billing state.")
    return out


def refresh_from_cms(fetch_callable, *, states=None, max_pages: int = 8,
                     raw: bool = False) -> pd.DataFrame:
    """Optional live refresh. fetch_callable(**kwargs) must wrap the CMS Coverage
    sad_exclusion_list tool and return its dict (keys: items[], next_page_token).

    Default (raw=False) returns a frame in the EXACT shape of the shipped
    classifier seed, columns [hcpcs, drug_brand, molecule, route_note, macs,
    effective_date, source], so a live pull is a genuine drop-in replacement for
    sad_exclusion_seed.csv after a diff. Each code's `macs` is the union of the
    MAC ids that list it (article id disambiguates Noridian JE/JF), and
    `route_note` is parsed from the source brand text.

    raw=True returns the long, source-faithful rows (one per code x MAC) instead,
    matching sad_exclusion_full.csv.

    Returns a one-column note frame on no-callable or any failure. Never called
    automatically; the pipeline runs on the shipped snapshot unless asked.
    """
    if fetch_callable is None:
        return pd.DataFrame({"note": ["no CMS fetch callable supplied; running on the "
                                      "shipped snapshot"]})
    long_rows = []
    token = None
    try:
        for _ in range(max_pages):
            resp = fetch_callable(limit=200, page_token=token)
            items = resp.get("items", []) if isinstance(resp, dict) else []
            for it in items:
                code = str(it.get("code_id", "")).strip().upper()
                if not code:
                    continue
                brand = str(it.get("drug_brand_name", "")).replace("\n", " ").strip()
                long_rows.append({
                    "hcpcs": code,
                    "drug_brand_name": brand[:120],
                    "mac_id": _item_to_mac(it),
                    "article_id": str(it.get("document_display_id", "")).strip(),
                    "effective_date": str(it.get("effective_date", "")),
                    "url": str(it.get("url", ""))})
            token = resp.get("next_page_token") if isinstance(resp, dict) else None
            if not token:
                break
    except Exception as e:
        return pd.DataFrame({"note": ["CMS refresh failed: {}: {}".format(type(e).__name__, e)]})
    if not long_rows:
        return pd.DataFrame({"note": ["CMS refresh returned no rows"]})

    long = pd.DataFrame(long_rows)
    if raw:
        long.attrs["note"] = ("Live SAD pull (long form); {} rows across {} codes and "
                              "{} MACs.".format(len(long), long["hcpcs"].nunique(),
                                                long["mac_id"].replace("", pd.NA).nunique()))
        return long

    # collapse to the classifier seed shape: one row per code -----------------
    seed_rows = []
    for code, grp in long.groupby("hcpcs"):
        macs = sorted({m for m in grp["mac_id"] if m})
        # prefer a named (non-unclassified) brand string for readability/route
        named = grp[~grp["drug_brand_name"].str.contains(
            "unclassified|miscellaneous", case=False, na=False)]
        brand = (named["drug_brand_name"].iloc[0] if len(named)
                 else grp["drug_brand_name"].iloc[0])
        eff = (named["effective_date"].iloc[0] if len(named)
               else grp["effective_date"].iloc[0])
        seed_rows.append({"hcpcs": code, "drug_brand": brand, "molecule": "",
                          "route_note": route_note_from_text(brand),
                          "macs": ",".join(macs), "effective_date": eff,
                          "source": "cms_live_refresh"})
    out = pd.DataFrame(seed_rows).sort_values("hcpcs").reset_index(drop=True)
    out.attrs["note"] = ("Live SAD pull normalized to seed shape; {} codes across {} MACs. "
                         "Diff against sad_exclusion_seed.csv before replacing it.".format(
                             out["hcpcs"].nunique(),
                             long["mac_id"].replace("", pd.NA).nunique()))
    return out
