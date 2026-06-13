"""Synthetic NPPES universe generator.

The live CMS download and the NPI Registry API are unreachable from this
environment (every outbound host returns HTTP 403). To verify the full
pipeline end-to-end — parse → land → normalize → affiliate → DQ → query —
we generate a representative universe with the *real* NPPES column headers,
so the production streaming parsers run against it unchanged.

What the generator deliberately includes so every DQ check is exercised:
  • both entity types (1 individual, 2 organization) with their distinct
    field sets (orgs carry legal business name + authorized official);
  • valid Luhn NPIs, plus a few intentionally invalid NPIs to exercise the
    quarantine path;
  • multiple taxonomy codes per provider with exactly one primary;
  • shared practice addresses + name overlap so affiliations form;
  • deactivated and reactivated providers for roster-integrity checks;
  • a weekly increment with new / updated / newly-deactivated rows.

This is a verification fixture, not real provider data. The same code path
will ingest the real dissemination file the moment one is staged on disk
(``pipeline.run(monthly_path=...)``).
"""
from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Tuple

from .luhn import make_valid_npi

# A small, real subset of NUCC taxonomy codes (code, grouping, classification,
# specialization). Enough to make the resolution-rate check meaningful.
NUCC_SUBSET: List[Tuple[str, str, str, str]] = [
    ("207Q00000X", "Allopathic & Osteopathic Physicians", "Family Medicine", ""),
    ("207R00000X", "Allopathic & Osteopathic Physicians", "Internal Medicine", ""),
    ("207RC0000X", "Allopathic & Osteopathic Physicians", "Internal Medicine", "Cardiovascular Disease"),
    ("208D00000X", "Allopathic & Osteopathic Physicians", "General Practice", ""),
    ("207RG0100X", "Allopathic & Osteopathic Physicians", "Internal Medicine", "Gastroenterology"),
    ("363LF0000X", "Physician Assistants & Advanced Practice Nursing Providers", "Nurse Practitioner", "Family"),
    ("282N00000X", "Hospitals", "General Acute Care Hospital", ""),
    ("282NC0060X", "Hospitals", "General Acute Care Hospital", "Critical Access"),
    ("261QP2300X", "Ambulatory Health Care Facilities", "Clinic/Center", "Primary Care"),
    ("314000000X", "Nursing & Custodial Care Facilities", "Skilled Nursing Facility", ""),
]

_MAIN_COLUMNS = [
    "NPI", "Entity Type Code", "Replacement NPI",
    "Provider Organization Name (Legal Business Name)",
    "Provider Last Name (Legal Name)", "Provider First Name",
    "Provider Middle Name", "Provider Name Prefix Text",
    "Provider Name Suffix Text", "Provider Credential Text",
    "Provider First Line Business Mailing Address",
    "Provider Business Mailing Address City Name",
    "Provider Business Mailing Address State Name",
    "Provider Business Mailing Address Postal Code",
    "Provider First Line Business Practice Location Address",
    "Provider Second Line Business Practice Location Address",
    "Provider Business Practice Location Address City Name",
    "Provider Business Practice Location Address State Name",
    "Provider Business Practice Location Address Postal Code",
    "Provider Business Practice Location Address Telephone Number",
    "Authorized Official Last Name", "Authorized Official First Name",
    "Authorized Official Title or Position",
    "Authorized Official Telephone Number",
    "Provider Enumeration Date", "Last Update Date",
    "NPI Deactivation Date", "NPI Reactivation Date", "Is Sole Proprietor",
    "Healthcare Provider Taxonomy Code_1",
    "Provider License Number_1", "Provider License Number State Code_1",
    "Healthcare Provider Primary Taxonomy Switch_1",
    "Healthcare Provider Taxonomy Code_2",
    "Provider License Number_2", "Provider License Number State Code_2",
    "Healthcare Provider Primary Taxonomy Switch_2",
]

_CITIES = [("DALLAS", "TX", "75201"), ("HOUSTON", "TX", "77030"),
           ("CHICAGO", "IL", "60611"), ("NEW YORK", "NY", "10016"),
           ("DENVER", "CO", "80202"), ("PHOENIX", "AZ", "85004")]
_LAST = ["SMITH", "JOHNSON", "PATEL", "GARCIA", "NGUYEN", "WILLIAMS", "BROWN"]
_FIRST = ["JAMES", "MARY", "RAJ", "ANA", "LINH", "DAVID", "SARAH"]
_ORG_STEMS = ["BAYLOR", "METHODIST", "NORTHWESTERN", "LANGONE", "PRESBYTERIAN",
              "MERCY", "ASCENSION"]
_ORG_KINDS = ["MEDICAL CENTER", "FAMILY MEDICINE", "CARDIOLOGY GROUP",
              "INTERNAL MEDICINE ASSOCIATES", "HEALTH SYSTEM"]


def _blank_row() -> Dict[str, str]:
    return {c: "" for c in _MAIN_COLUMNS}


def generate(out_dir: str, *, n_orgs: int = 80, n_individuals: int = 420,
             seed: int = 7) -> Dict[str, object]:
    """Write the synthetic dissemination + NUCC fixtures into ``out_dir``.
    Returns a manifest with paths and the monthly header count."""
    rng = random.Random(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    npi_seq = 100000000  # 9-digit base counter; make_valid_npi appends check
    def next_npi() -> str:
        nonlocal npi_seq
        npi_seq += 7
        return make_valid_npi(str(npi_seq))

    monthly_rows: List[Dict[str, str]] = []
    # Build org "campuses": each campus has one address shared by orgs+indivs.
    campuses: List[Tuple[str, str, str, str, str]] = []  # (line1, city, state, zip, stem)
    for i in range(max(1, n_orgs // 3)):
        city, st, zp = rng.choice(_CITIES)
        stem = rng.choice(_ORG_STEMS)
        line1 = f"{rng.randint(100, 9999)} {rng.choice(['MAIN', 'GASTON', 'FANNIN', 'HURON'])} ST"
        campuses.append((line1, city, st, zp, stem))

    org_npis: List[str] = []
    # Organizations (Type 2)
    for i in range(n_orgs):
        line1, city, st, zp, stem = rng.choice(campuses)
        npi = next_npi()
        org_npis.append(npi)
        r = _blank_row()
        org_name = f"{stem} {rng.choice(_ORG_KINDS)}"
        taxo = rng.choice(["282N00000X", "261QP2300X", "314000000X", "282NC0060X"])
        r.update({
            "NPI": npi, "Entity Type Code": "2",
            "Provider Organization Name (Legal Business Name)": org_name,
            "Provider First Line Business Practice Location Address": line1,
            "Provider Business Practice Location Address City Name": city,
            "Provider Business Practice Location Address State Name": st,
            "Provider Business Practice Location Address Postal Code": zp + "0000",
            "Provider First Line Business Mailing Address": line1,
            "Provider Business Mailing Address City Name": city,
            "Provider Business Mailing Address State Name": st,
            "Provider Business Mailing Address Postal Code": zp + "0000",
            "Authorized Official Last Name": rng.choice(_LAST),
            "Authorized Official First Name": rng.choice(_FIRST),
            "Authorized Official Title or Position": "CEO",
            "Provider Enumeration Date": "2008-05-23",
            "Last Update Date": "2026-01-10",
            "Is Sole Proprietor": "",
            "Healthcare Provider Taxonomy Code_1": taxo,
            "Healthcare Provider Primary Taxonomy Switch_1": "Y",
        })
        monthly_rows.append(r)

    # Individuals (Type 1) — some share a campus + surname stem with an org.
    for i in range(n_individuals):
        line1, city, st, zp, stem = rng.choice(campuses)
        npi = next_npi()
        last = rng.choice(_LAST)
        # 35% chance the individual's surname seeds a same-address org name
        seed_org_name = (rng.random() < 0.35)
        r = _blank_row()
        primary = rng.choice(["207Q00000X", "207R00000X", "207RC0000X",
                              "363LF0000X", "207RG0100X"])
        secondary = rng.choice(["207R00000X", "208D00000X", ""])
        deact = ""
        react = ""
        roll = rng.random()
        if roll < 0.06:
            deact = "2025-08-01"          # deactivated
        elif roll < 0.09:
            deact, react = "2024-03-01", "2025-06-01"  # reactivated
        r.update({
            "NPI": npi, "Entity Type Code": "1",
            "Provider Last Name (Legal Name)": last,
            "Provider First Name": rng.choice(_FIRST),
            "Provider Credential Text": rng.choice(["MD", "DO", "NP", "PA"]),
            "Provider First Line Business Practice Location Address": line1,
            "Provider Business Practice Location Address City Name": city,
            "Provider Business Practice Location Address State Name": st,
            "Provider Business Practice Location Address Postal Code": zp + "1234",
            "Provider First Line Business Mailing Address": line1,
            "Provider Business Mailing Address City Name": city,
            "Provider Business Mailing Address State Name": st,
            "Provider Business Mailing Address Postal Code": zp + "1234",
            "Provider Enumeration Date": "2010-09-01",
            "Last Update Date": "2026-01-12",
            "NPI Deactivation Date": deact,
            "NPI Reactivation Date": react,
            "Is Sole Proprietor": rng.choice(["Y", "N"]),
            "Healthcare Provider Taxonomy Code_1": primary,
            "Provider License Number_1": f"{st}{rng.randint(10000, 99999)}",
            "Provider License Number State Code_1": st,
            "Healthcare Provider Primary Taxonomy Switch_1": "Y",
        })
        if secondary:
            r.update({
                "Healthcare Provider Taxonomy Code_2": secondary,
                "Provider License Number State Code_2": st,
                "Healthcare Provider Primary Taxonomy Switch_2": "N",
            })
        if seed_org_name and org_npis:
            # plant a same-address org whose legal name contains this surname
            onpi = next_npi()
            org_npis.append(onpi)
            orow = _blank_row()
            orow.update({
                "NPI": onpi, "Entity Type Code": "2",
                "Provider Organization Name (Legal Business Name)":
                    f"{last} {rng.choice(['FAMILY MEDICINE', 'CARDIOLOGY'])} PLLC",
                "Provider First Line Business Practice Location Address": line1,
                "Provider Business Practice Location Address City Name": city,
                "Provider Business Practice Location Address State Name": st,
                "Provider Business Practice Location Address Postal Code": zp + "0000",
                "Authorized Official Last Name": last,
                "Authorized Official First Name": rng.choice(_FIRST),
                "Authorized Official Title or Position": "OWNER",
                "Provider Enumeration Date": "2012-02-01",
                "Last Update Date": "2026-01-09",
                "Healthcare Provider Taxonomy Code_1": "261QP2300X",
                "Healthcare Provider Primary Taxonomy Switch_1": "Y",
            })
            monthly_rows.append(orow)
        monthly_rows.append(r)

    # Two intentionally invalid NPIs (bad check digit / wrong length).
    for bad in ("1234567890", "999"):
        r = _blank_row()
        r.update({"NPI": bad, "Entity Type Code": "1",
                  "Provider Last Name (Legal Name)": "BADRECORD",
                  "Healthcare Provider Taxonomy Code_1": "207Q00000X",
                  "Healthcare Provider Primary Taxonomy Switch_1": "Y",
                  "Last Update Date": "2026-01-12"})
        monthly_rows.append(r)

    monthly_path = out / "nppes_monthly.csv"
    _write_csv(monthly_path, _MAIN_COLUMNS, monthly_rows)

    # Weekly increment: a few new orgs, an update to an existing provider,
    # and a deactivation of an existing active individual.
    weekly_rows: List[Dict[str, str]] = []
    for i in range(8):
        line1, city, st, zp, stem = rng.choice(campuses)
        npi = next_npi()
        r = _blank_row()
        r.update({
            "NPI": npi, "Entity Type Code": "2",
            "Provider Organization Name (Legal Business Name)":
                f"{stem} NEW {rng.choice(_ORG_KINDS)}",
            "Provider First Line Business Practice Location Address": line1,
            "Provider Business Practice Location Address City Name": city,
            "Provider Business Practice Location Address State Name": st,
            "Provider Business Practice Location Address Postal Code": zp + "0000",
            "Authorized Official Last Name": rng.choice(_LAST),
            "Authorized Official Title or Position": "CEO",
            "Provider Enumeration Date": "2026-02-01",
            "Last Update Date": "2026-02-07",
            "Healthcare Provider Taxonomy Code_1": "282N00000X",
            "Healthcare Provider Primary Taxonomy Switch_1": "Y",
        })
        weekly_rows.append(r)
    # Update an existing org (newer Last Update Date) + deactivate an existing.
    if monthly_rows:
        existing_org = next(r for r in monthly_rows
                            if r["Entity Type Code"] == "2" and r["NPI"].isdigit()
                            and len(r["NPI"]) == 10)
        upd = dict(existing_org)
        upd["Provider Credential Text"] = ""
        upd["Last Update Date"] = "2026-02-08"
        upd["Provider Organization Name (Legal Business Name)"] = (
            existing_org["Provider Organization Name (Legal Business Name)"] + " (RENAMED)")
        weekly_rows.append(upd)
        existing_ind = next(r for r in monthly_rows
                            if r["Entity Type Code"] == "1"
                            and not r["NPI Deactivation Date"]
                            and len(r["NPI"]) == 10 and r["NPI"].isdigit())
        dea = dict(existing_ind)
        dea["NPI Deactivation Date"] = "2026-02-05"
        dea["Last Update Date"] = "2026-02-08"
        weekly_rows.append(dea)

    weekly_path = out / "nppes_weekly_2026-02-08.csv"
    _write_csv(weekly_path, _MAIN_COLUMNS, weekly_rows)

    # NUCC subset CSV (real header names).
    nucc_path = out / "nucc_taxonomy.csv"
    with nucc_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Code", "Grouping", "Classification", "Specialization",
                    "Definition", "Notes", "Display Name", "Section"])
        for code, grp, cls, spec in NUCC_SUBSET:
            section = "Non-Individual" if grp in (
                "Hospitals", "Nursing & Custodial Care Facilities",
                "Ambulatory Health Care Facilities") else "Individual"
            display = " - ".join([x for x in (cls, spec) if x]) or grp
            w.writerow([code, grp, cls, spec, "", "", display, section])

    # Other-name file (org other names).
    othername_path = out / "othername_pfile.csv"
    with othername_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["NPI", "Provider Other Organization Name",
                    "Provider Other Organization Name Type Code"])
        for r in monthly_rows[:30]:
            if r["Entity Type Code"] == "2" and r["NPI"].isdigit() and len(r["NPI"]) == 10:
                w.writerow([r["NPI"],
                            r["Provider Organization Name (Legal Business Name)"] + " DBA",
                            "3"])

    # Practice-location file (non-primary locations).
    pl_path = out / "pl_pfile.csv"
    pre = "Provider Secondary Practice Location Address-"
    with pl_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        cols = ["NPI", pre + "Address Line 1", pre + "Address Line 2",
                pre + "City Name", pre + "State Name", pre + "Postal Code",
                pre + "Telephone Number"]
        w.writerow(cols)
        for r in monthly_rows[:20]:
            if r["NPI"].isdigit() and len(r["NPI"]) == 10:
                w.writerow([r["NPI"], "200 ANNEX BLVD", "STE 5",
                            "DALLAS", "TX", "752010000", "2145551212"])

    # Endpoint (FHIR) file.
    endpoint_path = out / "endpoint_pfile.csv"
    with endpoint_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["NPI", "Endpoint Type", "Endpoint Type Description",
                    "Endpoint", "Affiliation", "Use Description",
                    "Content Type Description"])
        for r in monthly_rows[:15]:
            if r["Entity Type Code"] == "2" and r["NPI"].isdigit() and len(r["NPI"]) == 10:
                w.writerow([r["NPI"], "FHIR", "FHIR R4 API",
                            f"https://fhir.example.org/{r['NPI']}/metadata",
                            "Y", "Production", "application/fhir+json"])

    header_count = len(monthly_rows)
    return {
        "monthly_path": str(monthly_path),
        "weekly_paths": [str(weekly_path)],
        "nucc_path": str(nucc_path),
        "othername_path": str(othername_path),
        "practice_location_path": str(pl_path),
        "endpoint_path": str(endpoint_path),
        "monthly_header_count": header_count,
        "monthly_version": "2026-02-SYNTH",
    }


def _write_csv(path: Path, columns: List[str], rows: List[Dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow(r)
