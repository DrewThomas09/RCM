"""
crosswalk_builder.py  (v32)
===========================

Curtis's real blocker at 3:23: the common-name and all-codes fields are built
bottom-up from codes already observed in the dataset, so "the array of all
possible codes per common name" does not exist, and Nico's any-match formula has
nothing complete to evaluate against. The fix the team named is a top-down
crosswalk assembled from reference sources rather than from the claims:

  * the CMS quarterly ASP NDC-to-HCPCS crosswalk (every payable NDC and its code),
  * the DME drug fee-schedule files (the pump / SCIG channel codes),
  * the FDA NDC directory (NDC to proprietary / non-proprietary name and labeler),

rolled up to the molecule. This module ingests any of those that are provided,
sniffing their real column headers, normalizes them to one schema, and rolls them
up so every common name carries the COMPLETE set of its J-codes and NDCs, not
just the ones the panel happened to contain. With no files provided it falls back
to the shipped seed so it always returns a usable crosswalk.

On top of the crosswalk it implements the dual-flag design Nico asked to keep:

  drug-level capture flag   a molecule is IN if ANY of its codes (J-code, NDC, or
                            any combination) is in the formulary; if it is in, all
                            its codes are in. NOC / catch-all codes are excluded
                            from the "all codes are in" rule (they carry many
                            molecules) and must be adjudicated by the claim NDC.
  code-level evidence flag  which exact codes / NDCs the target actually stocks,
                            retained separately as the evidence layer, and the
                            basis for NDC-level gap targeting (the Inflectra case,
                            where gapping is at particular NDCs under a J-code
                            rather than the whole code).

Deterministic and offline. No network, no model.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from . import rx_bridge as _rxb


# header synonyms for sniffing real reference files
_NDC_HEADERS = ("ndc", "ndc11", "productndc", "package_ndc", "packagendc", "ndc_code")
_HCPCS_HEADERS = ("hcpcs", "hcpcs_code", "hcpcscode", "code", "jcode", "j_code", "hcpc")
_NAME_HEADERS = ("drug_name", "drugname", "proprietaryname", "proprietary_name",
                 "nonproprietaryname", "nonproprietary_name", "name", "label",
                 "brand", "description", "product")
_ING_HEADERS = ("ingredient", "nonproprietaryname", "nonproprietary_name",
                "substance", "active_ingredient", "substancename")
_LABELER_HEADERS = ("labeler", "labeler_name", "labelername", "manufacturer")


def _norm_ndc(x) -> str:
    return "".join(ch for ch in str(x) if ch.isdigit())


def _pick(cols, wanted):
    low = {c.strip().lower().replace(" ", "").replace("-", "_"): c for c in cols}
    for w in wanted:
        key = w.replace(" ", "").replace("-", "_")
        if key in low:
            return low[key]
    # loose contains
    for w in wanted:
        for lk, orig in low.items():
            if w.replace(" ", "").replace("-", "_") in lk:
                return orig
    return None


def _read(path):
    try:
        return pd.read_csv(path, dtype=str)
    except Exception:
        try:
            return pd.read_csv(path, dtype=str, encoding="latin-1", on_bad_lines="skip")
        except Exception:
            return None


def _ingest_source(path, source_tag, xwalk_seed):
    """Normalize one reference file to columns ndc, hcpcs, name, ingredient,
    labeler, source. Missing fields are blank. Ingredient is resolved from the
    seed brand/ingredient tables when the file only carries a name."""
    df = _read(path)
    if df is None or df.empty:
        return pd.DataFrame(columns=["ndc", "hcpcs", "name", "ingredient", "labeler", "source"])
    cols = list(df.columns)
    ndc_c = _pick(cols, _NDC_HEADERS)
    hc_c = _pick(cols, _HCPCS_HEADERS)
    nm_c = _pick(cols, _NAME_HEADERS)
    ing_c = _pick(cols, _ING_HEADERS)
    lab_c = _pick(cols, _LABELER_HEADERS)

    out = pd.DataFrame({
        "ndc": (df[ndc_c].map(_norm_ndc) if ndc_c else ""),
        "hcpcs": (df[hc_c].astype(str).str.strip().str.upper() if hc_c else ""),
        "name": (df[nm_c].astype(str).str.strip() if nm_c else ""),
        "ingredient": (df[ing_c].astype(str).str.strip().str.lower() if ing_c else ""),
        "labeler": (df[lab_c].astype(str).str.strip() if lab_c else ""),
    })
    # resolve a molecule ingredient from the seed when absent, via brand/name
    need = out["ingredient"].eq("") | out["ingredient"].isna()
    if need.any():
        resolved = []
        for nm in out.loc[need, "name"].tolist():
            ing = _resolve_ingredient(nm, xwalk_seed)
            resolved.append(ing)
        out.loc[need, "ingredient"] = resolved
    out["source"] = source_tag
    return out


def _resolve_ingredient(name, xwalk_seed):
    """Seed-based brand/name -> normalized ingredient (offline). '' if unknown."""
    if not name or not str(name).strip():
        return ""
    nrm = _rxb._norm(str(name))
    brand = _rxb._brand_from_name(str(name)) if hasattr(_rxb, "_brand_from_name") else ""
    for cand in (nrm, _rxb._norm(brand) if brand else ""):
        if not cand:
            continue
        row = (xwalk_seed.get("by_brand", {}) or {}).get(cand)
        if row and row.get("ingredient"):
            return _rxb._norm(row["ingredient"])
    # try ingredient-contains map
    for ing in (xwalk_seed.get("ingredients", set()) or set()):
        if ing and ing in nrm:
            return ing
    return ""


def build_crosswalk(*, asp_ndc_hcpcs=None, fda_ndc=None, dme_fee=None,
                    seed_ref_dir=None, use_example=False) -> dict:
    """Assemble a top-down crosswalk. Each source path is optional. Returns:
        table              normalized rows (ndc, hcpcs, name, ingredient, labeler, source)
        codes_by_molecule  {ingredient: {"hcpcs": set, "ndc": set}}
        molecule_of_hcpcs  {hcpcs: ingredient}    (excludes NOC/catch-all codes)
        molecule_of_ndc    {ndc: ingredient}
        dme_codes          set of DME-channel HCPCS seen in the DME fee source
    Falls back to the shipped seed crosswalk so it always returns something."""
    ref = Path(seed_ref_dir or config.REF_DIR)
    seed = _rxb.load_crosswalk(ref)

    frames = []
    # 1) seed rows (brand/ingredient/hcpcs) as a baseline
    seed_rows = []
    for nb, row in (seed.get("by_brand", {}) or {}).items():
        seed_rows.append({"ndc": "", "hcpcs": str(row.get("hcpcs", "")).strip().upper(),
                          "name": row.get("brand", ""), "ingredient": _rxb._norm(row.get("ingredient", "")),
                          "labeler": "", "source": "seed"})
    if seed_rows:
        frames.append(pd.DataFrame(seed_rows))

    # 2) optional external sources (auto-use the shipped example when asked)
    if use_example and asp_ndc_hcpcs is None:
        ex = ref / "asp_ndc_hcpcs_example.csv"
        if ex.exists():
            asp_ndc_hcpcs = str(ex)
    for path, tag in ((asp_ndc_hcpcs, "asp_crosswalk"),
                      (fda_ndc, "fda_ndc_directory"),
                      (dme_fee, "dme_fee_schedule")):
        if path:
            frames.append(_ingest_source(path, tag, seed))

    table = (pd.concat(frames, ignore_index=True) if frames
             else pd.DataFrame(columns=["ndc", "hcpcs", "name", "ingredient", "labeler", "source"]))
    table["hcpcs"] = table["hcpcs"].fillna("").astype(str).str.strip().str.upper()
    table["ndc"] = table["ndc"].fillna("").map(_norm_ndc)
    table["ingredient"] = table["ingredient"].fillna("").astype(str).str.strip().str.lower()

    codes_by_molecule = {}
    molecule_of_hcpcs = {}
    molecule_of_ndc = {}
    for _, r in table.iterrows():
        ing = r["ingredient"]
        if not ing:
            continue
        d = codes_by_molecule.setdefault(ing, {"hcpcs": set(), "ndc": set()})
        hc = r["hcpcs"]
        nd = r["ndc"]
        if hc:
            d["hcpcs"].add(hc)
            if not config.is_catchall_code(hc):
                molecule_of_hcpcs.setdefault(hc, ing)
        if nd:
            d["ndc"].add(nd)
            molecule_of_ndc.setdefault(nd, ing)

    dme_codes = set()
    if dme_fee:
        dme_codes = {str(x).strip().upper()
                     for x in table.loc[table["source"] == "dme_fee_schedule", "hcpcs"] if str(x).strip()}

    return {
        "table": table,
        "codes_by_molecule": codes_by_molecule,
        "molecule_of_hcpcs": molecule_of_hcpcs,
        "molecule_of_ndc": molecule_of_ndc,
        "dme_codes": dme_codes,
        "seed": seed,
    }


def crosswalk_coverage(cw: dict) -> pd.DataFrame:
    """Per molecule, how many distinct HCPCS and NDCs the top-down crosswalk knows
    about, so the completeness gain over a bottom-up (observed-only) build is
    visible."""
    rows = []
    for ing, d in cw["codes_by_molecule"].items():
        rows.append({"molecule": ing, "n_hcpcs": len(d["hcpcs"]),
                     "n_ndc": len(d["ndc"]),
                     "hcpcs": ", ".join(sorted(d["hcpcs"])[:12]),
                     "example_ndcs": ", ".join(sorted(d["ndc"])[:4])})
    out = pd.DataFrame(rows).sort_values(["n_hcpcs", "n_ndc"], ascending=False).reset_index(drop=True)
    out.attrs["note"] = (
        "The complete code array per molecule, assembled top-down from reference sources. "
        "This is what the any-match membership rule evaluates against, so a molecule is not "
        "missed just because the panel never contained one of its codes.")
    return out


def load_formulary_codes(path) -> dict:
    """Load the formulary's code snapshot: {'hcpcs': set, 'ndc': set}. Accepts a
    CSV with any of hcpcs/ndc columns."""
    df = _read(path)
    if df is None or df.empty:
        return {"hcpcs": set(), "ndc": set()}
    hc = _pick(list(df.columns), _HCPCS_HEADERS)
    nd = _pick(list(df.columns), _NDC_HEADERS)
    return {
        "hcpcs": ({str(x).strip().upper() for x in df[hc].dropna()} if hc else set()),
        "ndc": ({_norm_ndc(x) for x in df[nd].dropna()} if nd else set()),
    }


def any_match_membership(std_named: pd.DataFrame, cw: dict, formulary_codes: dict, *,
                         hcpcs_col: str = "hcpcs", ndc_col: str = "ndc",
                         common_key_col: str = "drug_common_key") -> pd.DataFrame:
    """The dual-flag output. For each molecule present in the panel decide the
    drug-level capture flag by any-match against the formulary's code snapshot,
    using the COMPLETE top-down code array (so an NDC that maps by J-code to an
    in-formulary drug is captured, per Curtis's 2:58 counter-case). Then stamp
    every row: `capture_in` (drug-level), `code_evidence` (this exact code/NDC is
    the formulary snapshot), and `noc_needs_ndc` (a shared NOC code that cannot be
    admitted wholesale)."""
    out = std_named.copy()
    n = len(out)
    fh = {str(x).strip().upper() for x in formulary_codes.get("hcpcs", set())}
    fn = {_norm_ndc(x) for x in formulary_codes.get("ndc", set())}
    cbm = cw["codes_by_molecule"]
    mo_h = cw["molecule_of_hcpcs"]
    mo_n = cw["molecule_of_ndc"]

    hc = (out[hcpcs_col].astype("string").fillna("").str.strip().str.upper()
          if hcpcs_col in out.columns else pd.Series([""] * n, index=out.index))
    nd = (out[ndc_col].map(_norm_ndc) if ndc_col in out.columns
          else pd.Series([""] * n, index=out.index))
    key = (out[common_key_col].astype("string").fillna("")
           if common_key_col in out.columns else pd.Series([""] * n, index=out.index))

    # molecule per row: prefer the resolved common key, else map via crosswalk
    def _mol(i):
        k = str(key.iat[i]).strip().lower()
        if k and not k.startswith(("name::", "hcpcs::")):
            return k
        h = hc.iat[i]
        if h and h in mo_h:
            return mo_h[h]
        d = nd.iat[i]
        if d and d in mo_n:
            return mo_n[d]
        return ""

    # decide capture per molecule once (any-match over the full code array)
    molecules = {_mol(i) for i in range(n)}
    capture_by_mol = {}
    for m in molecules:
        if not m:
            capture_by_mol[m] = False
            continue
        codes = cbm.get(m, {"hcpcs": set(), "ndc": set()})
        hit = bool((codes["hcpcs"] & fh) or (codes["ndc"] & fn))
        capture_by_mol[m] = hit

    cap = np.zeros(n, dtype=bool)
    ev = np.zeros(n, dtype=bool)
    noc = np.zeros(n, dtype=bool)
    mol_out = np.array([""] * n, dtype=object)
    for i in range(n):
        m = _mol(i)
        mol_out[i] = m
        cap[i] = capture_by_mol.get(m, False)
        h = hc.iat[i]
        d = nd.iat[i]
        ev[i] = bool((h and h in fh) or (d and d in fn))
        if h and config.is_catchall_code(h):
            noc[i] = True
            # a NOC line is only truly in if its own NDC is in the formulary
            cap[i] = bool(d and d in fn)

    out["molecule_key"] = mol_out
    out["capture_in"] = cap
    out["code_evidence"] = ev
    out["noc_needs_ndc"] = noc
    out.attrs["note"] = (
        "capture_in is the drug-level flag (any of the molecule's complete code array is in "
        "the formulary, so all its codes are in). code_evidence is the code-level flag (this "
        "exact code/NDC is the formulary snapshot). noc_needs_ndc rows sit on a shared NOC "
        "code and are admitted only when their own NDC is in the formulary, never wholesale.")
    return out


def ndc_gap_targets(std_named: pd.DataFrame, cw: dict, *, allowed=None,
                    ndc_col: str = "ndc", hcpcs_col: str = "hcpcs",
                    common_key_col: str = "drug_common_key",
                    molecules=None) -> pd.DataFrame:
    """The Inflectra case: within a J-code that is included, find the specific NDCs
    that are gapped, i.e. present in the complete crosswalk for the molecule but
    absent from (or thin in) the panel. Returns one row per (molecule, hcpcs, ndc)
    with whether it was observed and its panel dollars, so gapping can be targeted
    at the NDC rather than the whole code."""
    cbm = cw["codes_by_molecule"]
    mo_h = cw["molecule_of_hcpcs"]
    mo_n = cw["molecule_of_ndc"]
    table = cw["table"]

    n = len(std_named)
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0)
         if allowed is not None else pd.Series(0.0, index=std_named.index))
    obs_ndc = (std_named[ndc_col].map(_norm_ndc) if ndc_col in std_named.columns
               else pd.Series([""] * n, index=std_named.index))
    key = (std_named[common_key_col].astype("string").fillna("")
           if common_key_col in std_named.columns else pd.Series([""] * n, index=std_named.index))

    # observed dollars per NDC
    obs = pd.DataFrame({"ndc": obs_ndc.to_numpy(), "allowed": a.to_numpy()})
    obs_dollars = obs.groupby("ndc")["allowed"].sum().to_dict()
    observed_ndcs = {k for k in obs_dollars if k}

    # molecules present in the panel (via resolved key or crosswalk map)
    present = set()
    for i in range(n):
        k = str(key.iat[i]).strip().lower()
        if k and not k.startswith(("name::", "hcpcs::")):
            present.add(k)
        d = obs_ndc.iat[i]
        if d and d in mo_n:
            present.add(mo_n[d])
    if molecules:
        present &= {str(m).strip().lower() for m in molecules}

    rows = []
    for m in sorted(present):
        codes = cbm.get(m)
        if not codes:
            continue
        # map each known NDC of the molecule to its HCPCS via the table
        sub = table[(table["ingredient"] == m) & (table["ndc"] != "")]
        for _, r in sub.iterrows():
            nd = r["ndc"]
            hcp = r["hcpcs"]
            was_obs = nd in observed_ndcs
            rows.append({
                "molecule": m,
                "hcpcs": hcp,
                "ndc": nd,
                "labeler": r.get("labeler", ""),
                "observed_in_panel": was_obs,
                "panel_allowed": round(float(obs_dollars.get(nd, 0.0)), 2),
                "gap_flag": (not was_obs),
            })
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame({"note": ["no NDC-level crosswalk rows for the panel molecules; "
                                      "supply the ASP/FDA NDC sources to enable NDC gap targeting"]})
    out = out.sort_values(["molecule", "gap_flag", "panel_allowed"],
                          ascending=[True, False, False]).reset_index(drop=True)
    out.attrs["note"] = (
        "gap_flag=True marks an NDC in the molecule's complete crosswalk that the panel did "
        "not contain, i.e. a gap at the NDC level under an included J-code (the Inflectra "
        "pattern). Target gapping at these NDCs, not the whole code.")
    return out


def ndc_attribution(std_named: pd.DataFrame, cw: dict, *, allowed,
                    hcpcs_col: str = "hcpcs", ndc_col: str = "ndc",
                    common_key_col: str = "drug_common_key") -> pd.DataFrame:
    """v33: the Inflectra pass, worked. Rows billing a J-code with a BLANK NDC are
    the reason NDC-level gapping cannot be finished from the panel alone. This
    redistributes each such row's dollars across the molecule's OBSERVED NDC mix
    (from rows of the same molecule that do carry NDCs), stamps everything, and
    reports what could not be attributed rather than forcing it. Redistribution
    of observed volume only; nothing is invented."""
    n = len(std_named)
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    hc = (std_named[hcpcs_col].astype("string").fillna("").str.strip().str.upper()
          if hcpcs_col in std_named.columns else pd.Series("", index=std_named.index))
    nd = (std_named[ndc_col].map(_norm_ndc) if ndc_col in std_named.columns
          else pd.Series([""] * n, index=std_named.index))
    key = (std_named[common_key_col].astype("string").fillna("")
           if common_key_col in std_named.columns else pd.Series([""] * n, index=std_named.index))

    df = pd.DataFrame({"key": key.to_numpy(), "hcpcs": hc.to_numpy(),
                       "ndc": nd.to_numpy(), "allowed": a.to_numpy()})
    # observed NDC mix per molecule
    with_ndc = df[(df["ndc"] != "") & (df["key"] != "")]
    mix = {}
    for k, g in with_ndc.groupby("key"):
        s = g.groupby("ndc")["allowed"].sum()
        tot = float(s.sum())
        if tot > 0:
            mix[k] = {nd_: float(v) / tot for nd_, v in s.items()}

    blanks = df[(df["ndc"] == "") & (df["hcpcs"] != "")]
    if blanks.empty:
        return pd.DataFrame({"note": ["no J-code rows with a blank NDC; nothing to attribute"]})
    rows = []
    for (k, h), g in blanks.groupby(["key", "hcpcs"]):
        dollars = float(g["allowed"].sum())
        m = mix.get(k)
        if m:
            for nd_, share in sorted(m.items(), key=lambda kv: -kv[1]):
                rows.append({"molecule_key": k, "hcpcs": h, "ndc": nd_,
                             "blank_ndc_dollars": round(dollars, 2),
                             "attributed_dollars": round(dollars * share, 2),
                             "mix_share_pct": round(share * 100, 1),
                             "basis": "observed NDC mix", "_ndc_attributed": True})
        else:
            rows.append({"molecule_key": k, "hcpcs": h, "ndc": "",
                         "blank_ndc_dollars": round(dollars, 2),
                         "attributed_dollars": 0.0, "mix_share_pct": np.nan,
                         "basis": "UNATTRIBUTED (no observed NDCs for molecule)",
                         "_ndc_attributed": False})
    out = pd.DataFrame(rows)
    out.attrs["unattributed_dollars"] = round(float(
        out.loc[~out["_ndc_attributed"], "blank_ndc_dollars"].drop_duplicates().sum()), 2)
    out.attrs["note"] = (
        "Blank-NDC J-code dollars spread across the molecule's observed NDC mix and stamped "
        "_ndc_attributed. Molecules with no observed NDCs stay UNATTRIBUTED; nothing is "
        "invented and nothing is merged silently.")
    return out
