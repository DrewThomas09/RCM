"""Generic claim-field repair (Step 0.5).

Beyond the missing billing NPI, a real extract from a data team usually has a
handful of other recoverable problems. This module fixes the ones that have a
defensible, documented proxy and logs every change so nothing is silent:

  • invalid billing NPIs (wrong length / bad check digit)  -> treated as blank
    so the recovery engine refills them (the original bad value is logged)
  • missing service state                                  -> derived from ZIP
  • missing drug name                                      -> filled from the
    HCPCS description (CMS-sourced where available, else a bundled starter map)
  • messy HCPCS / POS                                       -> normalised

Each repair is recorded per-row (surfaced in Cleaned_Claims) and summarised in
the Repairs_Log tab. Nothing here invents a biller — that is the recovery
engine's job, under its confidence tiers.
"""

import re

import pandas as pd

from . import config
from .geo import state_from_zip, US_STATES

# Full state / territory names -> USPS code, so "Texas", "New York", "Calif."
# normalise instead of being dropped as junk.
STATE_NAME_TO_ABBR = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "CALIF": "CA", "COLORADO": "CO", "CONNECTICUT": "CT",
    "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI",
    "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA",
    "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME",
    "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MASS": "MA", "MICHIGAN": "MI",
    "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT",
    "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR",
    "PENNSYLVANIA": "PA", "PENN": "PA", "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD", "TENNESSEE": "TN",
    "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA",
    "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI",
    "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC", "PUERTO RICO": "PR",
    "GUAM": "GU", "VIRGIN ISLANDS": "VI", "AMERICAN SAMOA": "AS",
    "NORTHERN MARIANA ISLANDS": "MP",
}

# A small starter HCPCS -> description map for common provider-administered
# injectables/infusions, used to fill a missing drug name when the live CMS
# description is unavailable. Extended at runtime by descriptions seen in the
# CMS candidate pulls, so it stays current for whatever codes appear.
HCPCS_DESC_SEED = {
    "J1745": "Infliximab injection", "Q5103": "Infliximab-dyyb (biosimilar)",
    "Q5104": "Infliximab-abda (biosimilar)", "Q5121": "Infliximab-axxq (biosimilar)",
    "J1459": "Immune globulin (IVIG)", "J1561": "Immune globulin (IVIG)",
    "J1568": "Immune globulin (IVIG)", "J1569": "Immune globulin (IVIG)",
    "J1572": "Immune globulin (IVIG)", "J1599": "Immune globulin, NOS",
    "J1551": "Immune globulin, subcutaneous (SCIG)",
    "J1555": "Immune globulin, subcutaneous (SCIG)",
    "J1558": "Immune globulin, subcutaneous (SCIG)",
    "J1559": "Immune globulin, subcutaneous (SCIG)",
    "J1561": "Immune globulin (IVIG)", "J1575": "Immune globulin/hyaluronidase",
    "J2350": "Ocrelizumab (Ocrevus)", "J2323": "Natalizumab (Tysabri)",
    "J3241": "Teprotumumab-trbw (Tepezza)", "J3357": "Ustekinumab, subcutaneous (Stelara)",
    "J3358": "Ustekinumab, intravenous", "J0202": "Alemtuzumab (Lemtrada)",
    "J1745": "Infliximab injection", "J9035": "Bevacizumab (Avastin)",
    "J2778": "Ranibizumab (Lucentis)", "J0178": "Aflibercept (Eylea)",
    "J0717": "Certolizumab pegol (Cimzia)", "J1602": "Golimumab (Simponi Aria)",
    "J0490": "Belimumab (Benlysta)", "J2182": "Mepolizumab (Nucala)",
    "J2786": "Reslizumab (Cinqair)", "J2357": "Omalizumab (Xolair)",
    "J0257": "Alpha-1 proteinase inhibitor", "J0220": "Alglucosidase alfa",
    "J0221": "Alglucosidase alfa (Lumizyme)", "J1300": "Eculizumab (Soliris)",
    "J1303": "Ravulizumab (Ultomiris)", "J0584": "Burosumab-twza (Crysvita)",
    "J3590": "Unclassified biologics", "J3490": "Unclassified drugs",
    "J9999": "Chemotherapy drug, NOC", "C9399": "Unclassified drug or biological",
}

# Common place-of-service normalisation -> a compact canonical token.
POS_CANON = {
    "11": "11", "OFFICE": "11", "O": "11", "CLINIC": "11",
    "12": "12", "HOME": "12", "H": "12",
    "22": "22", "OUTPATIENT": "22", "HOPD": "22",
    "19": "19", "21": "21", "INPATIENT": "21",
    "32": "32", "34": "34", "49": "49", "50": "50", "60": "60", "65": "65",
    "F": "F", "FACILITY": "F", "INSTITUTIONAL": "F",
}

_HCPCS_RE = re.compile(r"\b([A-Z]\d{4}|\d{5})\b")
# Capture any modifier token(s) trailing the base code, with or without a
# separator: "J1459JW", "J1459-JW", "J1459 JW KX" all yield the modifier(s).
_CODE_MOD_RE = re.compile(r"([A-Z]\d{4}|\d{5})[\s\-:]*([A-Z0-9]{2}(?:[\s\-:]*[A-Z0-9]{2})*)?")
_MOD_340B = {"JG", "TB"}     # claim-level 340B-acquired drug
_MOD_WASTE = {"JW", "JZ"}    # discarded (JW) / no-discard (JZ) wastage


def _extract_modifier(v):
    if pd.isna(v):
        return ""
    s = str(v).strip().upper()
    m = _CODE_MOD_RE.search(s)
    if not m or not m.group(2):
        return ""
    toks = [t for t in re.split(r"[\s\-:]+", m.group(2).strip()) if t]
    return ";".join(toks)


def _has_mod(modstr, wanted):
    toks = {t for t in re.split(r"[;\s\-:]+", str(modstr or "").upper()) if t}
    return bool(toks & wanted)


def npi_is_valid(npi):
    """A valid NPI is 10 digits and passes the Luhn check with the 80840 prefix."""
    if npi is None or pd.isna(npi):
        return False
    s = re.sub(r"\D", "", str(npi))
    if len(s) != 10:
        return False
    payload = "80840" + s[:9]
    total, alt = 0, True
    for ch in reversed(payload):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return (10 - (total % 10)) % 10 == int(s[9])


def _clean_hcpcs(v):
    if pd.isna(v):
        return v
    s = str(v).strip().upper().replace(" ", "")
    m = _HCPCS_RE.search(s)
    return m.group(1) if m else (s[:5] if s else s)


def repair_frame(std, code_desc=None, do_state_from_zip=True, do_drug_name=True,
                 do_pos=True, do_npi_validation=True, mue_map=None):
    """Repair std in place-ish (returns a new frame) plus a (log_df, per_row_tags).

    code_desc: optional {hcpcs: description} learned from live CMS pulls; merged
    over the bundled seed so filled names reflect the actual data when possible.
    """
    df = std.copy()
    n = len(df)
    tags = {i: [] for i in df.index}
    log = []

    def record(name, field, idxs, method, example=""):
        if len(idxs):
            log.append({"repair": name, "field": field, "rows_fixed": int(len(idxs)),
                        "method": method, "example": str(example)[:60]})
            for i in idxs:
                tags[i].append(name)

    # -- 1. normalise HCPCS ---------------------------------------------------
    if "hcpcs" in df:
        before = df["hcpcs"].copy()
        # preserve modifiers BEFORE stripping to the base code. JG/TB is a
        # claim-level 340B confirmation (stronger than the taxonomy signal);
        # JW/JZ is wastage. v5 threw these away when it reduced to the base code.
        mods = before.map(_extract_modifier)
        df["hcpcs_modifier"] = mods
        df["mod_340b"] = mods.map(lambda m: _has_mod(m, _MOD_340B))
        df["mod_wastage"] = mods.map(lambda m: _has_mod(m, _MOD_WASTE))
        df["hcpcs"] = df["hcpcs"].map(_clean_hcpcs)
        # segregate reversals/adjustments: negative allowed $ are voids, not new
        # volume, and would distort gross-up and HHI if pooled with real claims.
        if "allowed_amt" in df:
            _amt = pd.to_numeric(df["allowed_amt"], errors="coerce")
            df["is_reversal"] = (_amt < 0).fillna(False)
        changed = before.fillna("").astype(str) != df["hcpcs"].fillna("").astype(str)
        ex = ""
        if changed.any():
            j = df.index[changed][0]
            ex = f"{before.get(j)!r}->{df['hcpcs'].get(j)!r}"
        record("hcpcs_normalized", "hcpcs", list(df.index[changed]), "uppercase/strip/extract code", ex)

    # -- 2. normalise POS -----------------------------------------------------
    if do_pos and "pos" in df:
        def _canon_pos(v):
            if pd.isna(v):
                return v
            key = str(v).strip().upper()
            return POS_CANON.get(key, key)
        before = df["pos"].copy()
        df["pos"] = df["pos"].map(_canon_pos)
        changed = before.fillna("").astype(str) != df["pos"].fillna("").astype(str)
        record("pos_normalized", "pos", list(df.index[changed]), "mapped to canonical POS token")

    # -- 3. validate billing NPI; invalid -> blank (so it gets recovered) -----
    # first strip float artifacts like '1234567890.0' that come from Excel typing
    def _denorm_npi(v):
        if pd.isna(v):
            return v
        s = str(v).strip()
        if re.fullmatch(r"\d+\.0+", s):          # 1234567890.0 -> 1234567890
            s = s.split(".")[0]
        return s
    for c in ("billing_npi", "referring_npi"):
        if c in df:
            cleaned = df[c].map(_denorm_npi)
            changed = df[c].astype("string").fillna("") != cleaned.astype("string").fillna("")
            if changed.any():
                df[c] = cleaned
                record("npi_float_artifact_fixed", c, list(df.index[changed]), "removed trailing .0")
    df["billing_npi_original"] = df.get("billing_npi")
    df["billing_npi_invalid"] = False
    if do_npi_validation and "billing_npi" in df:
        present = df["billing_npi"].notna()
        bad = present & ~df["billing_npi"].map(npi_is_valid)
        if bad.any():
            ex = repr(df.loc[df.index[bad][0], "billing_npi"])
            df.loc[bad, "billing_npi"] = pd.NA
            df.loc[bad, "billing_npi_invalid"] = True
            record("invalid_billing_npi_blanked", "billing_npi", list(df.index[bad]),
                   "failed 10-digit Luhn check; cleared for recovery", ex)
    # also flag invalid referring NPIs (kept, but flagged) — they weaken imputation
    if "referring_npi" in df:
        present = df["referring_npi"].notna()
        badref = present & ~df["referring_npi"].map(npi_is_valid)
        if badref.any():
            df.loc[badref, "referring_npi"] = pd.NA
            record("invalid_referring_npi_blanked", "referring_npi", list(df.index[badref]),
                   "failed Luhn check; cleared (no longer used as an anchor)")

    # recompute the blank flag AFTER NPI validation
    df["is_blank_billing"] = df["billing_npi"].isna()

    # -- 4. derive missing state from ZIP ------------------------------------
    if do_state_from_zip and "state" in df:
        st = df["state"].astype("string").str.strip().str.upper()
        # map full state names -> USPS abbreviation before validating
        named = st.map(STATE_NAME_TO_ABBR)
        renamed = named.notna() & ~st.isin(US_STATES)
        st = named.where(named.notna(), st)
        if renamed.any():
            record("state_name_normalized", "state", list(df.index[renamed]),
                   "full state name -> USPS code")
        st = st.where(st.isin(US_STATES))                       # drop junk states
        need = st.isna() & df.get("zip", pd.Series(index=df.index)).notna()
        if need.any():
            derived = df.loc[need, "zip"].map(state_from_zip)
            ok = derived[derived.astype(bool)]
            st.loc[ok.index] = ok
            record("state_from_zip", "state", list(ok.index), "ZIP3->state crosswalk")
        df["state"] = st

    # -- 5. fill missing drug name from HCPCS description ---------------------
    if do_drug_name and "hcpcs" in df:
        desc = dict(HCPCS_DESC_SEED)
        if code_desc:
            desc.update({str(k).upper(): v for k, v in code_desc.items() if v})
        dn = df.get("drug_name")
        if dn is None:
            df["drug_name"] = pd.NA
            dn = df["drug_name"]
        dn = dn.astype("string")
        need = dn.isna() | (dn.str.strip() == "")
        fill = df.loc[need, "hcpcs"].map(lambda h: desc.get(str(h).upper(), pd.NA))
        got = fill[fill.notna()]
        df.loc[got.index, "drug_name"] = got.values
        record("drug_name_from_hcpcs", "drug_name", list(got.index), "HCPCS description (CMS/seed)")

    # -- 6. normalise ZIP (strip ZIP+4 / float artifacts to 5 digits) --------
    if "zip" in df:
        def _clean_zip(v):
            if pd.isna(v):
                return v
            s = re.sub(r"\D", "", str(v))
            return s[:5].zfill(5) if s else v
        before = df["zip"].copy()
        df["zip"] = df["zip"].map(_clean_zip)
        changed = before.fillna("").astype(str) != df["zip"].fillna("").astype(str)
        record("zip_normalized", "zip", list(df.index[changed]), "kept 5-digit ZIP")

    # -- 7. non-positive / missing units -> 1, but FLAGGED -------------------
    # J-codes bill per mg/unit, so a silently-defaulted "1" quietly corrupts any
    # $/unit or volume math downstream. We still default so the row stays usable,
    # but stamp units_imputed=True so unit-based analysis can exclude these.
    if "units" in df:
        u = pd.to_numeric(df["units"], errors="coerce")
        bad = (u.isna() | (u <= 0)).fillna(True)
        df["units_imputed"] = bad.values
        if bad.any():
            df.loc[bad, "units"] = 1
            record("units_defaulted", "units", list(df.index[bad]),
                   "non-positive/blank units set to 1 (flagged units_imputed)")
    else:
        df["units_imputed"] = False

    # -- 7b. MUE ceiling: flag impossible unit counts -----------------------
    # CMS Medically Unlikely Edits cap units per HCPCS per day. A row above the
    # cap is a data error (or a multi-day bill on one line) and would inflate any
    # volume math, so flag it. Opt-in: mue_map is {hcpcs: max_units_per_day}.
    df["units_over_mue"] = False
    if mue_map and "units" in df and "hcpcs" in df:
        u = pd.to_numeric(df["units"], errors="coerce")
        cap = df["hcpcs"].astype(str).str.upper().map(lambda h: mue_map.get(h))
        cap = pd.to_numeric(cap, errors="coerce")
        over = (u.notna() & cap.notna() & (u > cap)).fillna(False)
        df["units_over_mue"] = over.values
        if over.any():
            record("units_over_mue", "units", list(df.index[over]),
                   "units exceed CMS MUE per-day ceiling")

    # -- 8. trim stray whitespace on key string fields -----------------------
    for col in ("drug_name", "state", "pos", "hcpcs"):
        if col in df:
            s = df[col].astype("string")
            trimmed = s.str.strip()
            changed = (s.fillna("") != trimmed.fillna("")) & s.notna()
            if changed.any():
                df.loc[changed, col] = trimmed[changed]
                record("whitespace_trimmed", col, list(df.index[changed]), "trimmed surrounding spaces")

    # -- assemble outputs -----------------------------------------------------
    log_df = pd.DataFrame(log, columns=["repair", "field", "rows_fixed", "method", "example"])
    if not log_df.empty:
        log_df = log_df.sort_values("rows_fixed", ascending=False).reset_index(drop=True)
    per_row = pd.Series({i: ";".join(t) for i, t in tags.items()})
    df["repairs_applied"] = per_row
    return df, log_df, per_row
