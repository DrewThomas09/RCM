"""Streaming parsers for the NPPES dissemination files and the NUCC CSV.

The monthly full-replacement file is 8M+ rows / multiple GB unzipped, so
every parser here is a *generator* over ``csv.DictReader`` — one row in
flight at a time, never the whole file in memory. The canonical NPPES
column names are wide (the main file carries 15 taxonomy slots and a
mailing + practice address block); we map only the fields the canonical
tables need and tolerate a fixture that omits unused columns (DictReader
yields ``None`` → we coerce to "").

Parsers do not validate NPIs — that is the pipeline's job (it quarantines
invalid NPIs). Parsers only shape rows.
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

# NPPES main-file rows can exceed the default csv field-size limit on some
# platforms (long endpoint/other-name concatenations). Raise it once.
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:  # 32-bit guard
    csv.field_size_limit(2**31 - 1)

MAX_TAXONOMY_SLOTS = 15


@dataclass
class TaxonomySlot:
    code: str
    primary: bool
    license_number: str = ""
    license_state: str = ""
    group: str = ""


@dataclass
class AddressBlock:
    purpose: str          # 'practice' | 'mailing'
    line_1: str = ""
    line_2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country_code: str = ""
    telephone: str = ""
    fax: str = ""


@dataclass
class ProviderRow:
    npi: str
    entity_type: int
    replacement_npi: str = ""
    organization_name: str = ""
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    name_prefix: str = ""
    name_suffix: str = ""
    credential: str = ""
    authorized_official_last_name: str = ""
    authorized_official_first_name: str = ""
    authorized_official_title: str = ""
    authorized_official_phone: str = ""
    sole_proprietor: str = ""
    enumeration_date: str = ""
    last_update_date: str = ""
    deactivation_date: str = ""
    reactivation_date: str = ""
    taxonomies: List[TaxonomySlot] = field(default_factory=list)
    addresses: List[AddressBlock] = field(default_factory=list)


def _s(row: dict, col: str) -> str:
    v = row.get(col)
    return str(v).strip() if v not in (None, "") else ""


def zip5_of(postal: str) -> str:
    if not postal:
        return ""
    s = "".join(c for c in str(postal).split("-", 1)[0] if c.isdigit())
    return s[:5] if len(s) >= 5 else s


# Canonical column names from the NPPES data-dissemination main file.
_C_NPI = "NPI"
_C_ENTITY = "Entity Type Code"
_C_REPL = "Replacement NPI"
_C_ORG = "Provider Organization Name (Legal Business Name)"
_C_LAST = "Provider Last Name (Legal Name)"
_C_FIRST = "Provider First Name"
_C_MIDDLE = "Provider Middle Name"
_C_PREFIX = "Provider Name Prefix Text"
_C_SUFFIX = "Provider Name Suffix Text"
_C_CRED = "Provider Credential Text"
_C_AO_LAST = "Authorized Official Last Name"
_C_AO_FIRST = "Authorized Official First Name"
_C_AO_TITLE = "Authorized Official Title or Position"
_C_AO_PHONE = "Authorized Official Telephone Number"
_C_SOLE = "Is Sole Proprietor"
_C_ENUM = "Provider Enumeration Date"
_C_UPDATE = "Last Update Date"
_C_DEACT = "NPI Deactivation Date"
_C_REACT = "NPI Reactivation Date"

# Practice-location address block.
_C_P_L1 = "Provider First Line Business Practice Location Address"
_C_P_L2 = "Provider Second Line Business Practice Location Address"
_C_P_CITY = "Provider Business Practice Location Address City Name"
_C_P_STATE = "Provider Business Practice Location Address State Name"
_C_P_ZIP = "Provider Business Practice Location Address Postal Code"
_C_P_CC = "Provider Business Practice Location Address Country Code (If outside U.S.)"
_C_P_TEL = "Provider Business Practice Location Address Telephone Number"
_C_P_FAX = "Provider Business Practice Location Address Fax Number"

# Mailing address block.
_C_M_L1 = "Provider First Line Business Mailing Address"
_C_M_L2 = "Provider Second Line Business Mailing Address"
_C_M_CITY = "Provider Business Mailing Address City Name"
_C_M_STATE = "Provider Business Mailing Address State Name"
_C_M_ZIP = "Provider Business Mailing Address Postal Code"
_C_M_CC = "Provider Business Mailing Address Country Code (If outside U.S.)"
_C_M_TEL = "Provider Business Mailing Address Telephone Number"
_C_M_FAX = "Provider Business Mailing Address Fax Number"


def _taxonomy_slots(row: dict) -> List[TaxonomySlot]:
    slots: List[TaxonomySlot] = []
    for i in range(1, MAX_TAXONOMY_SLOTS + 1):
        code = _s(row, f"Healthcare Provider Taxonomy Code_{i}")
        if not code:
            continue
        switch = _s(row, f"Healthcare Provider Primary Taxonomy Switch_{i}")
        slots.append(
            TaxonomySlot(
                code=code,
                primary=(switch.upper() == "Y"),
                license_number=_s(row, f"Provider License Number_{i}"),
                license_state=_s(row, f"Provider License Number State Code_{i}"),
                group=_s(row, f"Healthcare Provider Taxonomy Group_{i}"),
            )
        )
    return slots


def _address_blocks(row: dict) -> List[AddressBlock]:
    blocks = []
    practice = AddressBlock(
        purpose="practice",
        line_1=_s(row, _C_P_L1), line_2=_s(row, _C_P_L2),
        city=_s(row, _C_P_CITY).upper(), state=_s(row, _C_P_STATE).upper(),
        postal_code=_s(row, _C_P_ZIP), country_code=_s(row, _C_P_CC) or "US",
        telephone=_s(row, _C_P_TEL), fax=_s(row, _C_P_FAX),
    )
    if practice.line_1 or practice.city:
        blocks.append(practice)
    mailing = AddressBlock(
        purpose="mailing",
        line_1=_s(row, _C_M_L1), line_2=_s(row, _C_M_L2),
        city=_s(row, _C_M_CITY).upper(), state=_s(row, _C_M_STATE).upper(),
        postal_code=_s(row, _C_M_ZIP), country_code=_s(row, _C_M_CC) or "US",
        telephone=_s(row, _C_M_TEL), fax=_s(row, _C_M_FAX),
    )
    if mailing.line_1 or mailing.city:
        blocks.append(mailing)
    return blocks


def parse_main_file(path: object) -> Iterator[ProviderRow]:
    """Stream the NPPES monthly/weekly main file. Yields one ProviderRow
    per data row (both entity types). Rows without an NPI or entity type
    are skipped at the parse layer only when entirely empty; malformed
    entity types still yield (entity_type=0) so the pipeline can decide."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"NPPES main file not found: {p}")
    with p.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            npi = _s(row, _C_NPI)
            if not npi:
                continue
            try:
                etype = int(_s(row, _C_ENTITY) or "0")
            except ValueError:
                etype = 0
            yield ProviderRow(
                npi=npi,
                entity_type=etype,
                replacement_npi=_s(row, _C_REPL),
                organization_name=_s(row, _C_ORG),
                last_name=_s(row, _C_LAST),
                first_name=_s(row, _C_FIRST),
                middle_name=_s(row, _C_MIDDLE),
                name_prefix=_s(row, _C_PREFIX),
                name_suffix=_s(row, _C_SUFFIX),
                credential=_s(row, _C_CRED),
                authorized_official_last_name=_s(row, _C_AO_LAST),
                authorized_official_first_name=_s(row, _C_AO_FIRST),
                authorized_official_title=_s(row, _C_AO_TITLE),
                authorized_official_phone=_s(row, _C_AO_PHONE),
                sole_proprietor=_s(row, _C_SOLE),
                enumeration_date=_s(row, _C_ENUM),
                last_update_date=_s(row, _C_UPDATE),
                deactivation_date=_s(row, _C_DEACT),
                reactivation_date=_s(row, _C_REACT),
                taxonomies=_taxonomy_slots(row),
                addresses=_address_blocks(row),
            )


@dataclass
class TaxonomyDef:
    code: str
    grouping: str = ""
    classification: str = ""
    specialization: str = ""
    definition: str = ""
    notes: str = ""
    display_name: str = ""
    section: str = ""


def parse_nucc_csv(path: object) -> Iterator[TaxonomyDef]:
    """Parse the published NUCC Health Care Provider Taxonomy CSV.

    The NUCC header uses Title-case columns: Code, Grouping, Classification,
    Specialization, Definition, Notes, Display Name, Section. We tolerate
    minor header variants (case-insensitive lookup)."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"NUCC CSV not found: {p}")
    with p.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        # case-insensitive header map
        field_map = {(h or "").strip().lower(): h for h in (reader.fieldnames or [])}

        def g(row: dict, name: str) -> str:
            h = field_map.get(name.lower())
            return _s(row, h) if h else ""

        for row in reader:
            code = g(row, "Code")
            if not code:
                continue
            yield TaxonomyDef(
                code=code,
                grouping=g(row, "Grouping"),
                classification=g(row, "Classification"),
                specialization=g(row, "Specialization"),
                definition=g(row, "Definition"),
                notes=g(row, "Notes"),
                display_name=g(row, "Display Name"),
                section=g(row, "Section"),
            )


def parse_othername(path: object) -> Iterator[dict]:
    """Type-2 organization other-name file (othername_pfile.csv).
    Columns: NPI, Provider Other Organization Name,
    Provider Other Organization Name Type Code."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"othername file not found: {p}")
    with p.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            npi = _s(row, "NPI")
            if not npi:
                continue
            yield {
                "npi": npi,
                "other_name": _s(row, "Provider Other Organization Name"),
                "other_name_type_code": _s(
                    row, "Provider Other Organization Name Type Code"),
            }


def parse_practice_location(path: object) -> Iterator[dict]:
    """Non-primary practice-location file (pl_pfile.csv).
    Columns are the practice-location address block prefixed
    'Provider Secondary Practice Location Address-...'."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"practice-location file not found: {p}")
    pre = "Provider Secondary Practice Location Address-"
    with p.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            npi = _s(row, "NPI")
            if not npi:
                continue
            yield {
                "npi": npi,
                "line_1": _s(row, pre + "Address Line 1"),
                "line_2": _s(row, pre + "Address Line 2"),
                "city": _s(row, pre + "City Name").upper(),
                "state": _s(row, pre + "State Name").upper(),
                "postal_code": _s(row, pre + "Postal Code"),
                "country_code": _s(row, pre + "Country Code (If outside USA)") or "US",
                "telephone": _s(row, pre + "Telephone Number"),
                "fax": _s(row, pre + "Fax Number"),
            }


def parse_endpoint(path: object) -> Iterator[dict]:
    """FHIR endpoint file (endpoint_pfile.csv).
    Columns: NPI, Endpoint Type, Endpoint Type Description, Endpoint,
    Affiliation, Use Description, Content Type Description."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"endpoint file not found: {p}")
    with p.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            npi = _s(row, "NPI")
            if not npi:
                continue
            yield {
                "npi": npi,
                "endpoint_type": _s(row, "Endpoint Type"),
                "endpoint_type_description": _s(row, "Endpoint Type Description"),
                "endpoint": _s(row, "Endpoint"),
                "affiliation": _s(row, "Affiliation"),
                "use_description": _s(row, "Use Description"),
                "content_type": _s(row, "Content Type Description"),
            }
