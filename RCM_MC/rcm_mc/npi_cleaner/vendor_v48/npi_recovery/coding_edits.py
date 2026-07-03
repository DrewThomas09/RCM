"""
coding_edits.py  (v42)
======================

Deterministic claims coding-edit screens built on real, dated CMS reference
files that ship in npi_recovery/reference:

  ncci_mue_seed.csv          NCCI Medically Unlikely Edits (practitioner + OPH),
                             effective 2026-07-01, code / MUE value / MAI
  ncci_ptp_sample.csv        NCCI PTP column1/column2 pairs with modifier
                             indicator (0 = never allowed, 1 = modifier allowed)
  icd10cm_validity_seed.csv  ICD-10-CM code validity by fiscal year (FY2025,
                             FY2026), for date-of-service validity checks
  jw_jz_single_dose_seed.csv single-dose HCPCS requiring a JW or JZ modifier
  nppes_deactivated_seed.csv deactivated NPI + deactivation date

Every function is a screen: it FLAGS, it does not silently rewrite. On multi
payer commercial data (Komodo), NCCI/MCE edits encode Medicare/Medicaid rules
that most but not all commercial payers mirror, so the honest posture is to
surface issues for review, not delete rows. Each function is offline, resolves
its own columns via schema.detect_columns when a mapping is not supplied, and
returns a tidy frame plus a one-line verdict in .attrs["note"].

Reference data can be refreshed to the current CMS quarter/fiscal year via the
source adapters and refresh helpers; the shipped seeds are dated in .attrs.
"""
from __future__ import annotations

import os
import pandas as pd
import numpy as np


def _ref(ref_dir, name):
    path = os.path.join(ref_dir or _default_ref(), name)
    return path if os.path.exists(path) else None


def _default_ref():
    return os.path.join(os.path.dirname(__file__), "reference")


def _has_data(std, col):
    return col is not None and col in std.columns and std[col].notna().any()


def _resolve(std, mapping, canonical, fallbacks=()):
    """Find the column for a canonical field: explicit mapping, else the
    canonical name, else a fallback name. A candidate only qualifies if it
    actually carries data; schema.standardize() manufactures all-NA canonical
    columns for fields the source never delivered, and an all-NA column must
    read as absent, not present."""
    if mapping and mapping.get(canonical) and _has_data(std, mapping[canonical]):
        return mapping[canonical]
    if _has_data(std, canonical):
        return canonical
    for f in fallbacks:
        if _has_data(std, f):
            return f
    return None


def _hcpcs_col(std, mapping):
    return _resolve(std, mapping, "hcpcs", ("hcpcs_cpt", "code", "procedure_code"))


def _fy_for_date(ts):
    """US ICD-10-CM fiscal year: FY starts Oct 1. Oct-Dec -> next calendar year."""
    if pd.isna(ts):
        return None
    return ts.year + 1 if ts.month >= 10 else ts.year


# --------------------------------------------------------------------------- #
# MUE: units above the Medicare cap
# --------------------------------------------------------------------------- #
def mue_screen(std: pd.DataFrame, *, ref_dir=None, mapping=None,
               service="practitioner") -> pd.DataFrame:
    path = _ref(ref_dir, "ncci_mue_seed.csv")
    if path is None:
        return pd.DataFrame({"note": ["MUE reference file not found"]})
    mue = pd.read_csv(path, dtype={"hcpcs": str})
    # prefer the requested service line; MUE values can differ practitioner vs OPH
    sub = mue[mue["service"] == service]
    if sub.empty:
        sub = mue
    cap = sub.dropna(subset=["mue_value"]).set_index("hcpcs")
    hc = _hcpcs_col(std, mapping)
    uc = _resolve(std, mapping, "units", ("unit", "quantity", "srvc_cnt"))
    if hc is None or uc is None:
        return pd.DataFrame({"note": ["MUE needs an HCPCS column and a units column"]})
    code = std[hc].astype(str).str.strip().str.upper()
    units = pd.to_numeric(std[uc], errors="coerce")
    capval = code.map(cap["mue_value"]).astype("Float64")
    mai = code.map(cap["mai"])
    over = (units > capval).fillna(False)
    out = pd.DataFrame({
        "row": std.index, "hcpcs": code, "units": units,
        "mue_value": capval, "mai": mai, "units_over_mue": over,
    })
    flagged = out[out["units_over_mue"]].copy()
    flagged["excess_units"] = (flagged["units"] - flagged["mue_value"]).astype("Float64")
    flagged["verdict"] = "flag"
    flagged.attrs["note"] = (
        f"{len(flagged)} of {int(capval.notna().sum())} MUE-covered lines exceed the "
        f"Medicare {service} MUE cap.")
    flagged.attrs["source"] = "CMS NCCI MUE 2026 Q3 (public tables)"
    return flagged.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# PTP: same-day column1/column2 code pairs not allowed together
# --------------------------------------------------------------------------- #
def ptp_screen(std: pd.DataFrame, *, ref_dir=None, mapping=None) -> pd.DataFrame:
    path = _ref(ref_dir, "ncci_ptp_sample.csv")
    if path is None:
        return pd.DataFrame({"note": ["PTP reference file not found"]})
    ptp = pd.read_csv(path, dtype={"col1": str, "col2": str})
    pairs = {(a.strip().upper(), b.strip().upper()): str(m)
             for a, b, m in zip(ptp["col1"], ptp["col2"], ptp["modifier_indicator"])}
    hc = _hcpcs_col(std, mapping)
    if hc is None:
        return pd.DataFrame({"note": ["PTP needs an HCPCS column"]})
    # group by the same claim episode: provider + patient + date when available
    keycols = [c for c in [
        _resolve(std, mapping, "billing_npi", ("npi",)),
        _resolve(std, mapping, "patient_id", ("patient_token", "member_id")),
        _resolve(std, mapping, "date_of_service", ("date", "service_date", "dos")),
    ] if c]
    df = std[[hc] + keycols].copy()
    df[hc] = df[hc].astype(str).str.strip().str.upper()
    if not keycols:
        # no episode key: fall back to whole-file pairwise on distinct codes (coarse)
        codes = sorted(df[hc].dropna().unique())
        hits = [(a, b, m) for (a, b), m in pairs.items() if a in codes and b in codes]
        res = pd.DataFrame(hits, columns=["col1", "col2", "modifier_indicator"])
        res.attrs["note"] = (f"{len(res)} PTP-listed code pairs co-occur in the file "
                             f"(no episode key to localize; coarse screen).")
        return res
    rows = []
    for key, g in df.groupby(keycols, dropna=False):
        codes = set(g[hc].dropna())
        for a in codes:
            for b in codes:
                if (a, b) in pairs:
                    rows.append({**dict(zip(keycols, key if isinstance(key, tuple) else (key,))),
                                 "col1": a, "col2": b,
                                 "modifier_indicator": pairs[(a, b)],
                                 "severity": "never_allowed" if pairs[(a, b)] == "0"
                                 else "modifier_required"})
    res = pd.DataFrame(rows)
    if len(res):
        res["verdict"] = "flag"
    n0 = int((res["modifier_indicator"] == "0").sum()) if len(res) else 0
    res.attrs["note"] = (f"{len(res)} same-episode PTP conflicts "
                         f"({n0} never-allowed, {len(res)-n0} modifier-required).")
    res.attrs["source"] = "CMS NCCI PTP 2026 Q3 quarterly change files (public sample)"
    return res


# --------------------------------------------------------------------------- #
# ICD-10 date-of-service validity
# --------------------------------------------------------------------------- #
def _icd_validity(ref_dir):
    path = _ref(ref_dir, "icd10cm_validity_seed.csv")
    if path is None:
        return None
    v = pd.read_csv(path, dtype={"code": str, "fy": str, "billable": str})
    v["code"] = v["code"].str.strip().str.upper()
    return v


def icd10_dos_validity(std: pd.DataFrame, *, ref_dir=None, mapping=None) -> pd.DataFrame:
    v = _icd_validity(ref_dir)
    if v is None:
        return pd.DataFrame({"note": ["ICD-10 validity reference not found"]})
    dx = _resolve(std, mapping, "diagnosis", ("dx", "icd10", "diagnosis_code", "dx1"))
    if dx is None:
        return pd.DataFrame({"note": ["ICD-10 validity needs a diagnosis column"]})
    dos = _resolve(std, mapping, "date_of_service", ("date", "service_date", "dos"))
    valid_by_fy = {fy: set(g["code"]) for fy, g in v.groupby("fy")}
    fys = sorted(valid_by_fy)
    raw = std[dx]
    codes = raw.astype(str).str.replace(".", "", regex=False).str.strip().str.upper()
    blank = raw.isna() | codes.isin(("", "NAN", "<NA>", "NONE", "NULL", "NA"))
    if dos is not None:
        ds = pd.to_datetime(std[dos], errors="coerce")
        fy = ds.map(_fy_for_date).astype("Int64").astype(str)
    else:
        fy = pd.Series([fys[-1]] * len(std), index=std.index)  # assume latest FY
    def _check(c, f, b):
        if b:                              # no diagnosis delivered on this row
            return pd.NA
        s = valid_by_fy.get(f)
        if s is None:                      # FY not in our seed: cannot judge
            return pd.NA
        return c in s
    valid = [_check(c, f, b) for c, f, b in zip(codes, fy, blank)]
    out = pd.DataFrame({"row": std.index, "diagnosis": codes, "fiscal_year": fy,
                        "valid_in_fy": valid})
    n_blank = int(blank.sum())
    known = out[out["valid_in_fy"].notna()]
    n_outside = int(len(std) - n_blank - len(known))
    invalid = known[known["valid_in_fy"] == False].copy()   # noqa: E712
    invalid["verdict"] = "flag"
    invalid.attrs["note"] = (
        f"{len(invalid)} of {len(known)} coded lines carry a diagnosis not valid in "
        f"the fiscal year of service. Unjudged: {n_blank} lines with no diagnosis "
        f"delivered, {n_outside} codes outside the shipped FY seed. Blank is not a "
        f"flag; a missing code cannot fail a validity check.")
    invalid.attrs["source"] = "CMS ICD-10-CM order files FY2025-FY2026 (public)"
    return invalid.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Age / sex conflicts (maternity + newborn logic; deterministic subset of MCE/IOCE)
# --------------------------------------------------------------------------- #
# CMS deactivated the diagnosis/procedure sex-conflict edits (MCE and OCE 003)
# effective 2024-10-01. What remains defensible without the licensed full MCE
# tables is the structural logic: pregnancy/childbirth (ICD-10 chapter O) and
# certain newborn (chapter P) diagnoses against patient age and sex.
_MATERNITY_PREFIX = ("O",)         # pregnancy, childbirth, puerperium
_NEWBORN_PREFIX = ("P",)           # certain conditions originating in perinatal period
_MALE_TOKENS = {"M", "MALE", "1"}
_FEMALE_TOKENS = {"F", "FEMALE", "2"}


def age_sex_conflicts(std: pd.DataFrame, *, ref_dir=None, mapping=None) -> pd.DataFrame:
    dx = _resolve(std, mapping, "diagnosis", ("dx", "icd10", "diagnosis_code", "dx1"))
    if dx is None:
        return pd.DataFrame({"note": ["age/sex screen needs a diagnosis column"]})
    age_c = _resolve(std, mapping, "patient_age", ("age", "pat_age"))
    sex_c = _resolve(std, mapping, "patient_sex", ("sex", "gender", "pat_sex"))
    if age_c is None and sex_c is None:
        return pd.DataFrame({"note": [
            "age/sex screen needs a patient age or sex column (neither present)"]})
    codes = std[dx].astype(str).str.replace(".", "", regex=False).str.strip().str.upper()
    is_mat = codes.str.startswith(_MATERNITY_PREFIX)
    is_nb = codes.str.startswith(_NEWBORN_PREFIX)
    flags = []
    sex = std[sex_c].astype(str).str.strip().str.upper() if sex_c else None
    age = pd.to_numeric(std[age_c], errors="coerce") if age_c else None
    for i in range(len(std)):
        c = codes.iloc[i]
        reason = None
        if is_mat.iloc[i]:
            if sex is not None and sex.iloc[i] in _MALE_TOKENS:
                reason = "maternity diagnosis on a male patient"
            elif age is not None and pd.notna(age.iloc[i]) and (age.iloc[i] < 9 or age.iloc[i] > 65):
                reason = "maternity diagnosis outside plausible childbearing age"
        elif is_nb.iloc[i]:
            if age is not None and pd.notna(age.iloc[i]) and age.iloc[i] > 1:
                reason = "perinatal (newborn) diagnosis on a patient older than 1"
        if reason:
            flags.append({"row": std.index[i], "diagnosis": c,
                          "patient_age": None if age is None else age.iloc[i],
                          "patient_sex": None if sex is None else sex.iloc[i],
                          "conflict": reason})
    out = pd.DataFrame(flags)
    if len(out):
        out["verdict"] = "flag"
    out.attrs["note"] = (
        f"{len(out)} age/sex diagnosis conflicts (maternity/newborn logic; note CMS "
        f"deactivated the sex-conflict code-pair edits effective 2024-10-01).")
    return out


# --------------------------------------------------------------------------- #
# JW/JZ single-dose wastage modifier logic
# --------------------------------------------------------------------------- #
def jw_jz_wastage(std: pd.DataFrame, *, ref_dir=None, mapping=None) -> pd.DataFrame:
    path = _ref(ref_dir, "jw_jz_single_dose_seed.csv")
    if path is None:
        return pd.DataFrame({"note": ["JW/JZ reference file not found"]})
    single = set(pd.read_csv(path, dtype={"hcpcs": str})["hcpcs"].str.strip().str.upper())
    hc = _hcpcs_col(std, mapping)
    if hc is None:
        return pd.DataFrame({"note": ["JW/JZ needs an HCPCS column"]})
    mod_c = _resolve(std, mapping, "modifiers", ("modifier", "mods", "modifier_1"))
    code = std[hc].astype(str).str.strip().str.upper()
    is_single = code.isin(single)
    if mod_c is None:
        # No modifier evidence delivered. A missing column cannot prove a missing
        # modifier, so these lines are UNJUDGED, not failed: an inventory of what
        # could not be verified, which is itself a diligence finding (ask the
        # seller for the modifier field).
        inv = pd.DataFrame({"row": std.index, "hcpcs": code,
                            "single_dose": is_single})
        inv = inv[inv["single_dose"]].copy()
        inv["verdict"] = "unjudged_missing_field"
        inv.attrs["note"] = (
            f"{len(inv)} single-dose drug lines could not be verified: no modifier "
            f"field was delivered, so JW/JZ presence is unknowable from this extract. "
            f"These are unjudged, not failures. Request the modifier field to judge.")
        inv.attrs["source"] = "CMS JW/JZ Policy HCPCS list (updated 2025-06-20)"
        return inv.reset_index(drop=True)
    mods = std[mod_c].astype(str).str.upper()
    has_jw = mods.str.contains("JW", na=False)
    has_jz = mods.str.contains("JZ", na=False)
    missing = is_single & ~(has_jw | has_jz)
    out = pd.DataFrame({"row": std.index, "hcpcs": code,
                        "single_dose": is_single,
                        "has_jw": has_jw, "has_jz": has_jz,
                        "missing_wastage_modifier": missing})
    flagged = out[out["missing_wastage_modifier"]].copy()
    flagged["verdict"] = "flag"
    flagged.attrs["note"] = (
        f"{len(flagged)} single-dose drug lines missing a JW/JZ modifier "
        f"(required for DOS >= 2023-07-01).")
    flagged.attrs["source"] = "CMS JW/JZ Policy HCPCS list (updated 2025-06-20)"
    return flagged.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Deactivated-NPI screen
# --------------------------------------------------------------------------- #
def deactivated_npi_screen(std: pd.DataFrame, *, ref_dir=None, mapping=None) -> pd.DataFrame:
    path = _ref(ref_dir, "nppes_deactivated_seed.csv")
    if path is None:
        return pd.DataFrame({"note": ["deactivated-NPI reference file not found"]})
    deact = pd.read_csv(path, dtype={"npi": str})
    deact["deactivation_date"] = pd.to_datetime(deact["deactivation_date"], errors="coerce")
    dmap = dict(zip(deact["npi"], deact["deactivation_date"]))
    npi_c = _resolve(std, mapping, "billing_npi", ("npi", "provider_npi"))
    if npi_c is None:
        return pd.DataFrame({"note": ["deactivated-NPI screen needs a billing NPI column"]})
    npi = std[npi_c].astype(str).str.strip()
    dd = npi.map(dmap)
    dos_c = _resolve(std, mapping, "date_of_service", ("date", "service_date", "dos"))
    if dos_c is not None:
        dos = pd.to_datetime(std[dos_c], errors="coerce")
        # deactivated as of service date (or deactivated at all if date unknown)
        flagged_mask = dd.notna() & (dos.isna() | (dos >= dd))
    else:
        flagged_mask = dd.notna()
    out = pd.DataFrame({"row": std.index, "billing_npi": npi,
                        "deactivation_date": dd})
    flagged = out[flagged_mask].copy()
    flagged["verdict"] = "flag"
    flagged.attrs["note"] = (
        f"{len(flagged)} claim lines bill a deactivated NPI"
        + (" as of the service date." if dos_c is not None else " (no service date to compare).")
        + " Seed is a sample of the full CMS file; run the full pull for complete coverage.")
    flagged.attrs["source"] = "CMS NPPES Monthly Deactivation V.2 2026-06-08 (sample)"
    return flagged.reset_index(drop=True)
