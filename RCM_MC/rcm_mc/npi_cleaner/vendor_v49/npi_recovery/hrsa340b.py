"""340B coverage enrichment — fills the "blank 340B spots" on a claims file.

There are two complementary sources, because no single public feed both (a) is
freely machine-pullable and (b) carries the billing NPI:

  1. NPPES provider taxonomy (automatic, always on). Several 340B covered-entity
     classes are identifiable directly from the provider's NUCC taxonomy /
     organization type — FQHCs, Critical Access Hospitals, Children's Hospitals,
     Rural Health Clinics, etc. For every billing NPI we already resolve in
     NPPES, we derive a 340B *eligibility signal* and the entity class it implies.
     This is a signal (the taxonomy implies the entity is of a 340B-eligible
     type), not proof of active registration.

  2. HRSA OPAIS Covered Entity export (authoritative, opt-in). HRSA publishes a
     daily Covered Entity file (Excel/JSON) of every registered 340B entity with
     its 340B ID, entity type, participation status and identifiers. It is gated
     behind the OPAIS app, so rather than scrape it we let the user drop the file
     in with --hrsa-340b-file; we then match billing NPIs / CCNs / names against
     it for *registered* 340B status. This is the ground truth when supplied.

Both fill a consistent block of B340_* columns, and the drug side flags the
J-codes most associated with 340B arbitrage (deep ASP-vs-340B spread).
"""

import re

import pandas as pd

# -- NPPES NUCC taxonomies that imply a 340B-eligible covered-entity class -----
# code -> (entity class, the 340B entity-type bucket it maps to)
TAXONOMY_340B = {
    "261QF0400X": ("Federally Qualified Health Center", "FQHC / CH"),
    "261QC1500X": ("Community Health Center", "FQHC / CH"),
    "261QR1300X": ("Rural Health Clinic", "RHC (FQHC-LA eligible)"),
    "282NC0060X": ("Critical Access Hospital", "CAH"),
    "261QC0050X": ("Critical Access Hospital", "CAH"),
    "282NC2000X": ("Children's Hospital", "PED (Children's)"),
    "282NR1301X": ("Rural Acute Care Hospital", "RRC/SCH eligible"),
    "281P00000X": ("Chronic Disease Hospital", "Hospital (verify)"),
    "282N00000X": ("General Acute Care Hospital", "DSH-eligible (verify)"),
    "286500000X": ("Military Hospital", "Federal (review)"),
    "261QR0405X": ("Tribal/638 Clinic", "638 Tribal"),
    "261QS1000X": ("STD Clinic", "STD grantee"),
    "261QM0801X": ("Mental Health (community)", "CMHC (verify)"),
    "261QX0203X": ("Hemophilia Treatment Center", "HM (Hemophilia)"),
    "261QF0050X": ("Family Planning / Title X", "FP (Title X)"),
    "261QR1100X": ("Black Lung Clinic", "BL (Black Lung)"),
    "261QP0905X": ("Comprehensive Hemophilia Diagnostic & Treatment Center", "HM"),
}

# OPAIS entity-type codes -> friendly label (for when the authoritative file is fed in)
OPAIS_ENTITY_TYPES = {
    "DSH": "Disproportionate Share Hospital", "CAH": "Critical Access Hospital",
    "CAN": "Free-standing Cancer Hospital", "CH": "Community Health Center (FQHC)",
    "FQHC": "Federally Qualified Health Center", "FQHCLA": "FQHC Look-Alike",
    "RRC": "Rural Referral Center", "SCH": "Sole Community Hospital",
    "PED": "Children's Hospital", "RWC": "Ryan White HIV/AIDS Program",
    "STD": "STD Clinic", "TB": "Tuberculosis Clinic", "BL": "Black Lung Clinic",
    "HM": "Hemophilia Treatment Center", "FP": "Title X Family Planning",
    "CMHC": "Community Mental Health Center", "638": "Tribal / Urban Indian (638)",
    "NHC": "Native Hawaiian Health Center",
}

# J-codes with the deepest ASP-vs-340B spread, i.e. the drugs where 340B status
# most changes the economics. Flagged on the drug side so blanks here get extra
# scrutiny. (Curated; pegloticase is the classic high-spread example.)
ARBITRAGE_J_CODES = {
    "J2507": "pegloticase (Krystexxa) — very high 340B spread",
    "J0178": "aflibercept (Eylea)", "J2778": "ranibizumab (Lucentis)",
    "J9035": "bevacizumab (Avastin)", "J1745": "infliximab (Remicade)",
    "J2350": "ocrelizumab (Ocrevus)", "J1300": "eculizumab (Soliris)",
    "J1303": "ravulizumab (Ultomiris)", "J3380": "vedolizumab (Entyvio) IV",
    "J0517": "benralizumab (Fasenra)", "J2182": "mepolizumab (Nucala)",
    "J1569": "immune globulin (Gammagard)", "J1561": "immune globulin (Gamunex)",
    "J9271": "pembrolizumab (Keytruda)", "J9299": "nivolumab (Opdivo)",
}


def classify_taxonomy(taxonomy_code, taxonomy_desc=""):
    """Map a NUCC taxonomy to a 340B-eligible class, or ('','') if none."""
    code = ("" if pd.isna(taxonomy_code) else str(taxonomy_code)).strip().upper()
    if code in TAXONOMY_340B:
        return TAXONOMY_340B[code]
    # fall back to a description keyword scan for the common classes
    d = ("" if pd.isna(taxonomy_desc) else str(taxonomy_desc)).lower()
    if "federally qualified" in d or "fqhc" in d:
        return ("Federally Qualified Health Center", "FQHC / CH")
    if "critical access" in d:
        return ("Critical Access Hospital", "CAH")
    if "rural health" in d:
        return ("Rural Health Clinic", "RHC (FQHC-LA eligible)")
    if "children" in d and "hospital" in d:
        return ("Children's Hospital", "PED (Children's)")
    if "hemophilia" in d:
        return ("Hemophilia Treatment Center", "HM (Hemophilia)")
    return ("", "")


def build_340b_directory(provider_directory):
    """From the NPPES Provider_Directory, derive a 340B eligibility signal per NPI.

    Returns a DataFrame keyed on NPI with the B340_* signal columns. Pure
    transform of data already pulled — no extra network.
    """
    if provider_directory is None or provider_directory.empty:
        return pd.DataFrame(columns=["NPI", "B340_Eligibility_Signal", "B340_Entity_Class",
                                     "B340_Entity_Bucket", "B340_Basis"])
    rows = []
    for _, r in provider_directory.iterrows():
        cls, bucket = classify_taxonomy(r.get("Taxonomy_Code", ""), r.get("Primary_Specialty", ""))
        signal = bool(cls)
        rows.append({
            "NPI": r.get("NPI", ""),
            "B340_Eligibility_Signal": "Eligible-type" if signal else "",
            "B340_Entity_Class": cls,
            "B340_Entity_Bucket": bucket,
            "B340_Basis": f"NPPES taxonomy {r.get('Taxonomy_Code','')}" if signal else "",
        })
    return pd.DataFrame(rows)


# -- authoritative OPAIS file ingestion ---------------------------------------
def _norm_npi(v):
    s = re.sub(r"\D", "", "" if pd.isna(v) else str(v))
    return s if len(s) == 10 else ""


def load_opais_file(path):
    """Parse an OPAIS Covered Entity export (Excel .xlsx or JSON) into a tidy
    frame: NPI, CCN (Medicare provider number), Entity_Name, Entity_Type,
    Participating, B340_ID, State. Column names vary, so we match flexibly.
    Returns (df, note). df may be empty if nothing usable was found.
    """
    import json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(), f"file not found: {path}"

    recs = []
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text())
        items = data if isinstance(data, list) else data.get("coveredEntities", data.get("data", []))
        for it in items:
            recs.append(it if isinstance(it, dict) else {})
        raw = pd.DataFrame(recs)
    else:
        try:
            raw = pd.read_excel(p, sheet_name=0, dtype=str)
        except Exception as e:
            return pd.DataFrame(), f"could not read Excel: {e}"

    if raw.empty:
        return pd.DataFrame(), "file had no rows"

    cols = {c.lower().strip(): c for c in raw.columns}

    def pick(*names):
        for n in names:
            for lc, orig in cols.items():
                if n in lc:
                    return orig
        return None

    npi_c = pick("npi")
    ccn_c = pick("medicare provider", "ccn", "provider number")
    name_c = pick("entity name", "name")
    type_c = pick("entity type", "type")
    part_c = pick("participating", "active")
    id_c = pick("340b id", "340bid", "id_340b")
    state_c = pick("state")

    out = pd.DataFrame({
        "NPI": raw[npi_c].map(_norm_npi) if npi_c else "",
        "CCN": raw[ccn_c].astype(str).str.strip() if ccn_c else "",
        "Entity_Name": raw[name_c].astype(str).str.strip() if name_c else "",
        "Entity_Type": raw[type_c].astype(str).str.strip() if type_c else "",
        "Participating": raw[part_c].astype(str).str.strip() if part_c else "",
        "B340_ID": raw[id_c].astype(str).str.strip() if id_c else "",
        "State": raw[state_c].astype(str).str.strip() if state_c else "",
    })
    note = (f"loaded {len(out):,} covered-entity rows; "
            f"{'has NPI' if npi_c else 'NO NPI column — will match on name/CCN'}")
    return out, note


def match_registered_340b(npis, names_by_npi, opais_df):
    """Match a set of billing NPIs against the authoritative OPAIS frame.
    Returns a DataFrame keyed on NPI with registered-status columns.
    """
    cols = ["NPI", "B340_Registered", "B340_ID", "B340_Entity_Type",
            "B340_Entity_Type_Desc", "B340_Participating", "B340_Match_Basis"]
    if opais_df is None or opais_df.empty:
        return pd.DataFrame(columns=cols)

    by_npi = {}
    if "NPI" in opais_df and opais_df["NPI"].astype(bool).any():
        for _, r in opais_df[opais_df["NPI"].astype(bool)].iterrows():
            by_npi.setdefault(r["NPI"], r)
    by_name = {}
    for _, r in opais_df.iterrows():
        nm = re.sub(r"[^a-z0-9]", "", str(r.get("Entity_Name", "")).lower())
        if nm:
            by_name.setdefault(nm, r)

    rows = []
    for npi in npis:
        npi = str(npi)
        hit, basis = None, ""
        if npi in by_npi:
            hit, basis = by_npi[npi], "NPI match"
        else:
            nm = re.sub(r"[^a-z0-9]", "", str(names_by_npi.get(npi, "")).lower())
            if nm and nm in by_name:
                hit, basis = by_name[nm], "entity-name match"
        if hit is not None:
            et = str(hit.get("Entity_Type", "")).upper()
            rows.append({
                "NPI": npi, "B340_Registered": "Yes", "B340_ID": hit.get("B340_ID", ""),
                "B340_Entity_Type": et,
                "B340_Entity_Type_Desc": OPAIS_ENTITY_TYPES.get(et, ""),
                "B340_Participating": hit.get("Participating", ""),
                "B340_Match_Basis": basis,
            })
        else:
            rows.append({"NPI": npi, "B340_Registered": "No", "B340_ID": "",
                         "B340_Entity_Type": "", "B340_Entity_Type_Desc": "",
                         "B340_Participating": "", "B340_Match_Basis": ""})
    return pd.DataFrame(rows, columns=cols)


def arbitrage_flag(hcpcs):
    """Return a note if this HCPCS is a high 340B-spread / arbitrage drug, else ''."""
    return ARBITRAGE_J_CODES.get(("" if pd.isna(hcpcs) else str(hcpcs)).strip().upper(), "")
