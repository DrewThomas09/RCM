"""NPPES bulk ingest — every NPI ever issued, crosswalked to a health system.

What this is for
----------------
NPPES is the only complete register of US provider identifiers: roughly
8 million NPIs, of which ~6 million are active, published monthly by CMS
as a ~9 GB CSV. It is the missing side of the crosswalk — CCN says who
files a cost report, NPI says who bills — and nothing joins the industry
together without it.

Deactivated NPIs are kept, not dropped
--------------------------------------
This ingest used to skip any NPI that had been deactivated and never
reactivated, on the reasoning that a dead identifier cannot bill. That
is true and it is the wrong thing to do for a crosswalk. A master file
exists to resolve identifiers found in *other* data — a 2019 claim
extract, an acquisition-era roster, a payer file — and those are full of
NPIs that NPPES has since retired. An identifier the crosswalk refuses
to recognise looks exactly like a data error to whoever is holding it.

So every NPI is written with a ``status`` (``active``, ``reactivated``
or ``deactivated``) and its deactivation and reactivation dates.
Callers that want only billable providers filter on status; callers
resolving history get the history. ``ingest_nppes(..., active_only=True)``
restores the old behaviour for the rare caller that wants it.

CMS also publishes a monthly deactivation file listing NPIs that have
been removed from the dissemination file entirely. :func:`ingest_deactivations`
folds it in as tombstone rows, which is the only way "every NPI ever"
can survive a snapshot that no longer mentions them.

Three things make this harder than a CSV read, and each one is a design
constraint here:

1. **Size.** The file does not fit in memory. Everything below streams
   in chunks and writes to SQLite as it goes; peak memory is one chunk,
   not one file. ``ingest_nppes`` on a 9 GB file is a long job, not a
   function call, so it reports progress and is resumable by CCN-free
   idempotent upsert.

2. **DBAs.** A hospital's legal business name is frequently a holding
   company — "SSM HEALTH CARE CORPORATION" — while the name anyone
   would recognise sits in the *other* organization name field as a
   d/b/a. Matching only the legal name loses the brand on a large
   share of facilities, so every record is matched on legal name AND
   d/b/a, and the crosswalk records which one hit.

3. **Individuals have no employer.** NPPES carries no affiliation field
   for an individual NPI: there is no column that says which system a
   physician works for, and no amount of parsing invents one. Individual
   NPIs therefore crosswalk to geography and taxonomy here, and to a
   system only through a facility-affiliation source (CMS Doctors and
   Clinicians "Facility Affiliation" file), which is a separate ingest.
   Claiming otherwise would be the single easiest way to make this whole
   crosswalk untrustworthy.

Getting the file
----------------
    https://download.cms.gov/nppes/NPPES_Data_Dissemination_<Month>_<Year>.zip

Unzip and point ``ingest_nppes`` at ``npidata_pfile_*.csv``. The
environment this was written in cannot reach that host (the egress
policy denies it), which is why the ingest is written against the
documented schema and exercised by a fixture rather than by a live
download — the code path is real, the file has to be supplied.

Public API::

    ingest_nppes(csv_path, db_path, *, chunk_size=200_000) -> IngestReport
    ingest_deactivations(csv_path, db_path) -> dict
    npi_rows(db_path, *, system_id=None, state=None, limit=...) -> list[dict]
    npi_coverage(db_path) -> dict
    match_organization(legal_name, dba, state) -> (system_id, basis)
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pandas as pd

from .health_systems import match_system, normalize_name
from .nucc_categories import classify_taxonomy

# NPPES dissemination column names. They are verbose and stable — CMS
# has kept this header since the 2007 layout — so matching on the exact
# string is safer than positional indexing into a 330-column file.
COL_NPI = "NPI"
COL_ENTITY = "Entity Type Code"
COL_LEGAL_NAME = "Provider Organization Name (Legal Business Name)"
COL_DBA = "Provider Other Organization Name"
COL_LAST = "Provider Last Name (Legal Name)"
COL_FIRST = "Provider First Name"
COL_CITY = "Provider Business Practice Location Address City Name"
COL_STATE = "Provider Business Practice Location Address State Name"
COL_ZIP = "Provider Business Practice Location Address Postal Code"
COL_ADDR = "Provider First Line Business Practice Location Address"
COL_TAXONOMY = "Healthcare Provider Taxonomy Code_1"
COL_DEACTIVATION = "NPI Deactivation Date"
COL_REACTIVATION = "NPI Reactivation Date"
COL_ENUMERATION = "Provider Enumeration Date"
COL_LAST_UPDATE = "Last Update Date"
COL_CERTIFICATION = "Certification Date"
COL_CREDENTIAL = "Provider Credential Text"
COL_SOLE_PROPRIETOR = "Is Sole Proprietor"
COL_SUBPART = "Is Organization Subpart"
COL_PARENT_LBN = "Parent Organization LBN"
COL_PARENT_TIN = "Parent Organization TIN"
COL_EIN = "Employer Identification Number (EIN)"

#: NPPES carries up to fifteen taxonomies per NPI with a "primary"
#: switch on each. Reading only the first one is how an infusion
#: pharmacy that also enrolled as a DME supplier ends up categorised as
#: one thing when it is two.
TAXONOMY_SLOTS = 15
COL_TAXONOMY_N: Tuple[str, ...] = tuple(
    f"Healthcare Provider Taxonomy Code_{i}" for i in range(1, TAXONOMY_SLOTS + 1))
COL_TAXONOMY_SWITCH_N: Tuple[str, ...] = tuple(
    f"Healthcare Provider Primary Taxonomy Switch_{i}"
    for i in range(1, TAXONOMY_SLOTS + 1))

#: Only these columns are read off the wire. The file carries ~330; a
#: full read is what turns a 9 GB file into an out-of-memory error.
USE_COLUMNS: Tuple[str, ...] = (
    COL_NPI, COL_ENTITY, COL_LEGAL_NAME, COL_DBA, COL_LAST, COL_FIRST,
    COL_ADDR, COL_CITY, COL_STATE, COL_ZIP,
    COL_DEACTIVATION, COL_REACTIVATION, COL_ENUMERATION, COL_LAST_UPDATE,
    COL_CERTIFICATION, COL_CREDENTIAL, COL_SOLE_PROPRIETOR, COL_SUBPART,
    COL_PARENT_LBN, COL_PARENT_TIN, COL_EIN,
) + COL_TAXONOMY_N + COL_TAXONOMY_SWITCH_N

ENTITY_INDIVIDUAL = "1"
ENTITY_ORGANIZATION = "2"

#: An NPI is one of exactly three things, and "deactivated" is a state
#: the crosswalk records rather than a reason to forget the identifier.
STATUS_ACTIVE = "active"
STATUS_REACTIVATED = "reactivated"
STATUS_DEACTIVATED = "deactivated"

_TABLE = "npi_crosswalk"

#: Columns added after the table's first release. Each is applied with
#: ALTER TABLE on open so an ingest DB written by an earlier build keeps
#: working instead of raising on the first SELECT.
_ADDED_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("ccn", "TEXT"),
    ("status", "TEXT"),
    ("deactivation_date", "TEXT"),
    ("reactivation_date", "TEXT"),
    ("enumeration_date", "TEXT"),
    ("last_updated", "TEXT"),
    ("certification_date", "TEXT"),
    ("credential", "TEXT"),
    ("sole_proprietor", "TEXT"),
    ("is_subpart", "TEXT"),
    ("parent_org_lbn", "TEXT"),
    ("parent_org_tin", "TEXT"),
    ("ein", "TEXT"),
    ("taxonomy_codes", "TEXT"),
    ("taxonomy_category", "TEXT"),
    ("taxonomy_level_i", "TEXT"),
    ("is_organisation", "INTEGER"),
)


@dataclass
class IngestReport:
    """What one ingest run actually did — every number measured, not estimated."""

    rows_read: int = 0
    rows_written: int = 0
    deactivated_kept: int = 0
    reactivated: int = 0
    deactivated_skipped: int = 0
    subparts: int = 0
    with_parent_org: int = 0
    organizations: int = 0
    individuals: int = 0
    matched_by_legal_name: int = 0
    matched_by_dba: int = 0
    unmatched_organizations: int = 0
    chunks: int = 0
    systems_seen: set = field(default_factory=set)

    @property
    def matched_organizations(self) -> int:
        return self.matched_by_legal_name + self.matched_by_dba

    @property
    def org_match_pct(self) -> float:
        return (self.matched_organizations / self.organizations * 100.0
                if self.organizations else 0.0)

    def summary(self) -> str:
        return (
            f"{self.rows_written:,} NPIs written from {self.rows_read:,} read "
            f"({self.chunks} chunks) · {self.organizations:,} organizations, "
            f"{self.individuals:,} individuals · "
            f"{self.matched_organizations:,} organizations matched to a system "
            f"({self.org_match_pct:.1f}%: {self.matched_by_legal_name:,} on legal "
            f"name, {self.matched_by_dba:,} on d/b/a) · "
            f"{self.deactivated_kept:,} deactivated kept, "
            f"{self.reactivated:,} reactivated, "
            f"{self.deactivated_skipped:,} deactivated skipped · "
            f"{self.subparts:,} subparts, "
            f"{self.with_parent_org:,} naming a parent organization"
        )


def ensure_table(con: sqlite3.Connection) -> None:
    """Create — and forward-migrate — the NPI crosswalk table.

    ``npi`` is the primary key so a re-run upserts rather than
    duplicating: an ingest of a 9 GB file will get interrupted, and
    resuming has to be safe.

    The later columns arrive by ALTER rather than by a table rewrite.
    A crosswalk DB is expensive to rebuild — hours of streaming — so a
    schema change must never be a reason to throw one away.
    """
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_TABLE} (
            npi TEXT PRIMARY KEY,
            entity_type TEXT,
            legal_name TEXT,
            dba_name TEXT,
            state TEXT,
            city TEXT,
            zip TEXT,
            address TEXT,
            taxonomy_code TEXT,
            system_id TEXT,
            match_basis TEXT,
            ingested_at TEXT
        )
        """
    )
    existing = {r[1] for r in con.execute(f"PRAGMA table_info({_TABLE})")}
    for name, decl in _ADDED_COLUMNS:
        if name not in existing:
            con.execute(f"ALTER TABLE {_TABLE} ADD COLUMN {name} {decl}")
    con.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_system ON {_TABLE}(system_id)")
    con.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_state ON {_TABLE}(state)")
    con.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_status ON {_TABLE}(status)")
    con.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_category "
        f"ON {_TABLE}(taxonomy_category)")
    con.commit()


# A civil body whose place name happens to be a health-system brand.
# The registry's patterns were tuned against 6,123 hospitals, where
# "^JEFFERSON" and "^AURORA" are unambiguous. Against a national NPI
# roster they also reach Jefferson Township Volunteer Ambulance, Aurora
# Township Fire Protection District and Grady County Board of
# Commissioners — municipalities, not subsidiaries. There is no
# plausible reading in which a fire district is part of a health system
# because it shares a town name.
_CIVIL_BODY_RE = re.compile(
    r"(?:BOARD OF (?:COMMISSIONERS|SUPERVISORS)|COUNTY OF |CITY OF "
    r"|TOWN OF |VILLAGE OF |TOWNSHIP|BOROUGH OF "
    r"|FIRE (?:DEPARTMENT|DEPT|DISTRICT|COMPANY|PROTECTION)"
    r"|VOLUNTEER|VOL FIRE|RESCUE SQUAD|SCHOOL DISTRICT)"
)


@lru_cache(maxsize=1)
def _system_footprints() -> Dict[str, frozenset]:
    """system_id -> the states where it demonstrably operates a facility.

    Derived from the certified universe, not asserted. A name match
    outside that footprint is the single most common way this matcher
    goes wrong: eight independent ambulance companies are called
    MedStar, in eight states MedStar Health has never operated, and
    ``^MEDSTAR`` reaches every one of them.
    """
    from .health_systems import UNMAPPED_ID, assign_all

    universe = assign_all()
    out: Dict[str, set] = {}
    for system_id, state in zip(universe["system_id"], universe["state"],
                                strict=True):
        if system_id and system_id != UNMAPPED_ID:
            out.setdefault(system_id, set()).add(str(state).upper().strip())
    return {k: frozenset(v) for k, v in out.items()}


def match_organization(
    legal_name: Any,
    dba: Any,
    state: Any,
    *,
    require_footprint: bool = True,
) -> Tuple[str, str]:
    """Resolve an organization NPI to a health system.

    Tries the legal business name first, then the d/b/a. The order
    matters and the losing case is instructive: SSM Health's hospitals
    file legal names like "SSM HEALTH CARE CORPORATION" (which matches)
    but plenty of systems file a holding-company legal name and put the
    recognisable brand in the d/b/a, so a legal-name-only match drops
    them. Returns ``("", "")`` when neither carries a brand.

    Two guards sit on top of the name match, because NPPES is a far
    harsher test of a pattern than HCRIS is. A match is rejected when
    the organization is a municipal body that merely shares a place
    name, and — unless ``require_footprint=False`` — when it sits in a
    state where the system operates nothing. On a 20,401-NPI ambulance
    roster the two guards together reject 56 of 423 raw matches, and
    every one of the 56 is wrong: MedStar Ambulance in eight states,
    Kindred Area Ambulance in Kindred ND, Aurora Township Fire
    Protection District.

    The cost is real and worth paying: a handful of true matches go
    with them, mostly air-ambulance subsidiaries based outside their
    parent's hospital footprint. A wrong parent is worse than a missing
    one, because nobody audits a mapping that looks complete.
    """
    st = str(state or "").upper().strip()

    for candidate, label in ((legal_name, "legal name"), (dba, "dba")):
        sysdef, pattern = match_system(candidate, st)
        if sysdef is None:
            continue
        if _CIVIL_BODY_RE.search(normalize_name(candidate)):
            continue
        # An operator with no CCN anywhere — an ambulance or air-medical
        # company — has no footprint for the guard to check. Absence of
        # evidence is not a veto: the guard exists to reject a match
        # OUTSIDE a known footprint, not to demand that one exist.
        footprint = _system_footprints().get(sysdef.system_id)
        if require_footprint and footprint and st not in footprint:
            continue
        return sysdef.system_id, f"{label}: {pattern}"

    return "", ""


def npi_status(row: Dict[str, Any]) -> str:
    """``active``, ``reactivated`` or ``deactivated`` for one NPPES row.

    NPPES leaves the deactivation date populated on records that were
    later reactivated, so testing deactivation alone condemns live
    providers. The three-way answer keeps that distinction visible
    instead of collapsing it into a boolean the caller has to guess at:
    a reactivated NPI bills today but has a gap in its history, and a
    claim from inside that gap is a different question from a claim
    outside it.
    """
    deact = str(row.get(COL_DEACTIVATION) or "").strip()
    react = str(row.get(COL_REACTIVATION) or "").strip()
    if not deact:
        return STATUS_ACTIVE
    return STATUS_REACTIVATED if react else STATUS_DEACTIVATED


def _is_active(row: Dict[str, Any]) -> bool:
    """Back-compat shim: True unless the NPI is deactivated for good."""
    return npi_status(row) != STATUS_DEACTIVATED


def _taxonomies(row: Dict[str, Any]) -> Tuple[str, Tuple[str, ...]]:
    """``(primary_code, all_codes)`` from the fifteen taxonomy slots.

    The primary is whichever slot carries the "Y" switch, because slot 1
    is not reliably the primary — providers reorder them across
    updates. Falling back to the first populated slot keeps a code on
    records where no switch is set at all, which is a real and
    surprisingly common state in the dissemination file.
    """
    codes: List[str] = []
    primary = ""
    for code_col, switch_col in zip(COL_TAXONOMY_N, COL_TAXONOMY_SWITCH_N,
                                    strict=True):
        code = str(row.get(code_col) or "").strip().upper()
        if not code:
            continue
        if code not in codes:
            codes.append(code)
        if not primary and str(row.get(switch_col) or "").strip().upper() == "Y":
            primary = code
    if not primary and codes:
        primary = codes[0]
    return primary, tuple(codes)


def _yes_no(value: Any) -> str:
    """NPPES flags are ``Y``/``N``/blank. Normalise without inventing."""
    text = str(value or "").strip().upper()
    return text if text in {"Y", "N"} else ""


def _iter_chunks(
    csv_path: Path,
    chunk_size: int,
) -> Iterator[pd.DataFrame]:
    """Stream the dissemination file in chunks, reading only what we use.

    ``usecols`` is applied defensively: CMS has added columns over the
    years, and a hard-coded column list that assumes a fixed width
    breaks on the next release. Anything missing is filled empty rather
    than raising, so an older or newer extract still ingests.
    """
    header = pd.read_csv(csv_path, nrows=0, dtype=str)
    present = [c for c in USE_COLUMNS if c in header.columns]
    if COL_NPI not in present:
        raise ValueError(
            f"{csv_path} does not look like an NPPES dissemination file "
            f"— no '{COL_NPI}' column")
    reader = pd.read_csv(csv_path, dtype=str, usecols=present,
                         chunksize=chunk_size, keep_default_na=False)
    for chunk in reader:
        for missing in (c for c in USE_COLUMNS if c not in present):
            chunk[missing] = ""
        yield chunk


def ingest_nppes(
    csv_path: Any,
    db_path: Any,
    *,
    chunk_size: int = 200_000,
    organizations_only: bool = False,
    active_only: bool = False,
    progress: Optional[Any] = None,
) -> IngestReport:
    """Stream an NPPES dissemination file into the NPI crosswalk table.

    Peak memory is one chunk, not one file. ``organizations_only``
    limits the write to entity-type-2 records, which is the ~1.8 M
    subset that can carry a system brand at all — worth it when the
    goal is the system crosswalk rather than the full register.

    ``active_only`` drops NPIs that were deactivated and never came
    back. It defaults to False: a crosswalk that cannot resolve a
    retired identifier fails exactly when it is needed most, on
    historical claims and pre-acquisition rosters.
    """
    csv_path = Path(csv_path)
    report = IngestReport()
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode=WAL")
    ensure_table(con)
    now = pd.Timestamp.now("UTC").isoformat()

    try:
        for chunk in _iter_chunks(csv_path, chunk_size):
            report.chunks += 1
            report.rows_read += len(chunk)
            payload: List[Tuple[Any, ...]] = []

            for row in chunk.to_dict("records"):
                npi = str(row.get(COL_NPI) or "").strip()
                if not npi:
                    continue

                status = npi_status(row)
                if status == STATUS_DEACTIVATED:
                    if active_only:
                        report.deactivated_skipped += 1
                        continue
                    report.deactivated_kept += 1
                elif status == STATUS_REACTIVATED:
                    report.reactivated += 1

                entity = str(row.get(COL_ENTITY) or "").strip()
                is_org = entity == ENTITY_ORGANIZATION
                if is_org:
                    report.organizations += 1
                else:
                    report.individuals += 1
                    if organizations_only:
                        continue

                legal = str(row.get(COL_LEGAL_NAME) or "").strip()
                dba = str(row.get(COL_DBA) or "").strip()
                state = str(row.get(COL_STATE) or "").strip().upper()

                system_id, basis = ("", "")
                if is_org:
                    system_id, basis = match_organization(legal, dba, state)
                    if basis.startswith("legal name"):
                        report.matched_by_legal_name += 1
                    elif basis.startswith("dba"):
                        report.matched_by_dba += 1
                    else:
                        report.unmatched_organizations += 1
                    if system_id:
                        report.systems_seen.add(system_id)

                if not legal and not is_org:
                    legal = " ".join(x for x in (
                        str(row.get(COL_FIRST) or "").strip(),
                        str(row.get(COL_LAST) or "").strip()) if x)

                primary_tax, all_tax = _taxonomies(row)
                klass = classify_taxonomy(primary_tax)
                subpart = _yes_no(row.get(COL_SUBPART))
                parent_lbn = str(row.get(COL_PARENT_LBN) or "").strip()
                if subpart == "Y":
                    report.subparts += 1
                if parent_lbn:
                    report.with_parent_org += 1

                payload.append((
                    npi, entity, legal, dba, state,
                    str(row.get(COL_CITY) or "").strip(),
                    str(row.get(COL_ZIP) or "").strip()[:5],
                    str(row.get(COL_ADDR) or "").strip(),
                    primary_tax,
                    system_id, basis, now,
                    status,
                    str(row.get(COL_DEACTIVATION) or "").strip(),
                    str(row.get(COL_REACTIVATION) or "").strip(),
                    str(row.get(COL_ENUMERATION) or "").strip(),
                    str(row.get(COL_LAST_UPDATE) or "").strip(),
                    str(row.get(COL_CERTIFICATION) or "").strip(),
                    str(row.get(COL_CREDENTIAL) or "").strip(),
                    _yes_no(row.get(COL_SOLE_PROPRIETOR)),
                    subpart,
                    parent_lbn,
                    str(row.get(COL_PARENT_TIN) or "").strip(),
                    str(row.get(COL_EIN) or "").strip(),
                    "|".join(all_tax),
                    klass.category,
                    klass.level_i,
                    1 if klass.is_organisation else 0,
                ))

            if payload:
                con.executemany(
                    f"INSERT INTO {_TABLE} (npi, entity_type, legal_name, "
                    f"dba_name, state, city, zip, address, taxonomy_code, "
                    f"system_id, match_basis, ingested_at, status, "
                    f"deactivation_date, reactivation_date, enumeration_date, "
                    f"last_updated, certification_date, credential, "
                    f"sole_proprietor, is_subpart, parent_org_lbn, "
                    f"parent_org_tin, ein, taxonomy_codes, taxonomy_category, "
                    f"taxonomy_level_i, is_organisation) "
                    f"VALUES ({','.join('?' * 28)}) "
                    f"ON CONFLICT(npi) DO UPDATE SET "
                    f"legal_name=excluded.legal_name, dba_name=excluded.dba_name, "
                    f"state=excluded.state, city=excluded.city, zip=excluded.zip, "
                    f"address=excluded.address, taxonomy_code=excluded.taxonomy_code, "
                    f"system_id=excluded.system_id, match_basis=excluded.match_basis, "
                    f"ingested_at=excluded.ingested_at, status=excluded.status, "
                    f"deactivation_date=excluded.deactivation_date, "
                    f"reactivation_date=excluded.reactivation_date, "
                    f"enumeration_date=excluded.enumeration_date, "
                    f"last_updated=excluded.last_updated, "
                    f"certification_date=excluded.certification_date, "
                    f"credential=excluded.credential, "
                    f"sole_proprietor=excluded.sole_proprietor, "
                    f"is_subpart=excluded.is_subpart, "
                    f"parent_org_lbn=excluded.parent_org_lbn, "
                    f"parent_org_tin=excluded.parent_org_tin, "
                    f"ein=excluded.ein, "
                    f"taxonomy_codes=excluded.taxonomy_codes, "
                    f"taxonomy_category=excluded.taxonomy_category, "
                    f"taxonomy_level_i=excluded.taxonomy_level_i, "
                    f"is_organisation=excluded.is_organisation",
                    payload,
                )
                con.commit()
                report.rows_written += len(payload)

            if progress is not None:
                progress(report)
    finally:
        con.close()

    return report


#: The monthly deactivation file's header, which is not the
#: dissemination file's. CMS ships it as ``NPI,NPPES Deactivation Date``;
#: the copy vendored in this repository normalises that to
#: ``npi,deactivation_date,source``. Accept both rather than making the
#: caller reshape a CMS file by hand.
_DEACT_NPI_COLUMNS = ("NPI", "npi")
_DEACT_DATE_COLUMNS = ("NPPES Deactivation Date", "Deactivation Date",
                       "deactivation_date")


def ingest_deactivations(csv_path: Any, db_path: Any) -> Dict[str, int]:
    """Fold CMS's monthly deactivation file into the crosswalk.

    "Every NPI ever" cannot come from the dissemination file alone.
    NPIs deactivated long enough ago stop appearing in it entirely, and
    a snapshot-only crosswalk therefore forgets exactly the identifiers
    that outlive their owners — the ones still sitting in old claims and
    pre-acquisition rosters.

    Every NPI named here ends up ``deactivated`` with its date. One that
    the crosswalk has never seen is written as a tombstone: an NPI, a
    status and a date, and nothing else, because nothing else is known.
    A tombstone is not a provider record and does not pretend to be one;
    it is the difference between "retired in 2019" and "no such NPI",
    and only one of those is an answer.

    An NPI already carrying a *later* reactivation is left active — the
    deactivation file records a moment, not the current state.

    Returns ``read``, ``tombstoned`` (rows the crosswalk had never
    seen), ``updated`` (existing rows moved to deactivated) and
    ``kept_reactivated``.
    """
    frame = pd.read_csv(str(csv_path), dtype=str, keep_default_na=False)
    npi_col = next((c for c in _DEACT_NPI_COLUMNS if c in frame.columns), "")
    date_col = next((c for c in _DEACT_DATE_COLUMNS if c in frame.columns), "")
    if not npi_col:
        raise ValueError(
            f"{csv_path} does not look like an NPPES deactivation file "
            f"— no NPI column")

    stats = {"read": 0, "tombstoned": 0, "updated": 0, "kept_reactivated": 0}
    con = sqlite3.connect(str(db_path))
    try:
        ensure_table(con)
        known = {
            row[0]: (row[1] or "")
            for row in con.execute(
                f"SELECT npi, reactivation_date FROM {_TABLE}")
        }
        now = pd.Timestamp.now("UTC").isoformat()
        tombstones: List[Tuple[Any, ...]] = []
        updates: List[Tuple[Any, ...]] = []

        for record in frame.to_dict("records"):
            npi = str(record.get(npi_col) or "").strip()
            if not npi:
                continue
            stats["read"] += 1
            when = str(record.get(date_col) or "").strip() if date_col else ""
            if npi not in known:
                tombstones.append((npi, STATUS_DEACTIVATED, when, now))
                stats["tombstoned"] += 1
            elif known[npi]:
                stats["kept_reactivated"] += 1
            else:
                updates.append((STATUS_DEACTIVATED, when, npi))
                stats["updated"] += 1

        if tombstones:
            con.executemany(
                f"INSERT INTO {_TABLE} (npi, status, deactivation_date, "
                f"ingested_at) VALUES (?,?,?,?) "
                f"ON CONFLICT(npi) DO NOTHING",
                tombstones)
        if updates:
            con.executemany(
                f"UPDATE {_TABLE} SET status = ?, deactivation_date = ? "
                f"WHERE npi = ?", updates)
        con.commit()
    finally:
        con.close()
    return stats


def link_npis_to_ccns(db_path: Any, *, crosswalk: Optional[pd.DataFrame] = None
                      ) -> Dict[str, int]:
    """Attach CCNs to organization NPIs by name + state + ZIP.

    The join nobody publishes: CMS issues CCNs and NPIs from different
    systems and does not release a mapping between them. Address is the
    only bridge, so the match requires normalized-name equality within
    the same state AND the same 5-digit ZIP — all three, because name
    alone collides ("MEMORIAL HOSPITAL") and ZIP alone puts a physician
    group in the same bucket as the hospital across the street.

    Ambiguity runs in BOTH directions, and only one of them is obvious.
    One NPI matching two CCNs is a question, not a link — that check was
    always here. Two NPIs matching one CCN is the same question wearing
    a different hat, and it was invisible: each NPI saw a single-element
    candidate list, so all of them linked and ``ambiguous`` stayed at
    zero while the CCN quietly acquired several NPIs. On a synthetic
    full-universe run that silently multiply-claimed 24 CCNs, one of
    them by 13 NPIs.

    So candidates are gathered first and committed second. A CCN
    claimed by more than one NPI is dropped from every claimant and
    counted once in ``ccn_contested``.

    Returns ``considered``, ``linked``, ``ambiguous`` (an NPI whose key
    hit several CCNs) and ``ccn_contested`` (a CCN several NPIs hit).
    """
    from .provider_crosswalk import get_crosswalk

    xw = get_crosswalk() if crosswalk is None else crosswalk
    keyed: Dict[Tuple[str, str, str], List[str]] = {}
    for rec in xw.to_dict("records"):
        key = (normalize_name(rec.get("name")),
               str(rec.get("state") or "").upper(),
               str(rec.get("zip") or "")[:5])
        if all(key):
            keyed.setdefault(key, []).append(str(rec.get("ccn")))

    con = sqlite3.connect(str(db_path))
    stats = {"considered": 0, "linked": 0, "ambiguous": 0, "ccn_contested": 0}
    try:
        ensure_table(con)
        if not _has_column(con, "ccn"):
            con.execute(f"ALTER TABLE {_TABLE} ADD COLUMN ccn TEXT")
        rows = con.execute(
            f"SELECT npi, legal_name, dba_name, state, zip FROM {_TABLE} "
            f"WHERE entity_type = ?", (ENTITY_ORGANIZATION,)).fetchall()

        candidates: List[Tuple[str, str]] = []       # (ccn, npi)
        for npi, legal, dba, state, zip5 in rows:
            stats["considered"] += 1
            st = str(state or "").upper()
            z = str(zip5 or "")[:5]
            for name in (legal, dba):
                if not name:
                    continue
                ccns = keyed.get((normalize_name(name), st, z))
                if not ccns:
                    # Not a match on this name — try the d/b/a rather
                    # than giving up on the NPI.
                    continue
                if len(ccns) > 1:
                    stats["ambiguous"] += 1
                    break
                candidates.append((ccns[0], npi))
                break

        claimants: Dict[str, List[str]] = {}
        for ccn, npi in candidates:
            claimants.setdefault(ccn, []).append(npi)
        contested = {ccn for ccn, npis in claimants.items() if len(npis) > 1}
        stats["ccn_contested"] = len(contested)

        updates = [(ccn, npi) for ccn, npi in candidates if ccn not in contested]
        stats["linked"] = len(updates)
        if updates:
            con.executemany(f"UPDATE {_TABLE} SET ccn = ? WHERE npi = ?", updates)
            con.commit()
    finally:
        con.close()
    return stats


def _has_column(con: sqlite3.Connection, column: str) -> bool:
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({_TABLE})")}
    return column in cols


def npi_coverage(db_path: Any) -> Dict[str, Any]:
    """Counts by entity type and system-match state."""
    con = sqlite3.connect(str(db_path))
    try:
        ensure_table(con)
        total = con.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0]
        orgs = con.execute(
            f"SELECT COUNT(*) FROM {_TABLE} WHERE entity_type = ?",
            (ENTITY_ORGANIZATION,)).fetchone()[0]
        matched = con.execute(
            f"SELECT COUNT(*) FROM {_TABLE} WHERE system_id != ''").fetchone()[0]
        systems = con.execute(
            f"SELECT COUNT(DISTINCT system_id) FROM {_TABLE} "
            f"WHERE system_id != ''").fetchone()[0]
        linked = 0
        if _has_column(con, "ccn"):
            linked = con.execute(
                f"SELECT COUNT(*) FROM {_TABLE} WHERE ccn IS NOT NULL "
                f"AND ccn != ''").fetchone()[0]
        by_status = dict(con.execute(
            f"SELECT COALESCE(NULLIF(status, ''), ?), COUNT(*) FROM {_TABLE} "
            f"GROUP BY 1", (STATUS_ACTIVE,)).fetchall())
        by_category = dict(con.execute(
            f"SELECT COALESCE(NULLIF(taxonomy_category, ''), 'unclassified'), "
            f"COUNT(*) FROM {_TABLE} GROUP BY 1 ORDER BY 2 DESC").fetchall())
        subparts = con.execute(
            f"SELECT COUNT(*) FROM {_TABLE} WHERE is_subpart = 'Y'").fetchone()[0]
        with_parent = con.execute(
            f"SELECT COUNT(*) FROM {_TABLE} WHERE parent_org_lbn IS NOT NULL "
            f"AND parent_org_lbn != ''").fetchone()[0]
        return {
            "npis": total,
            "organizations": orgs,
            "individuals": total - orgs,
            "system_matched": matched,
            "systems_represented": systems,
            "linked_to_ccn": linked,
            "by_status": by_status,
            "by_category": by_category,
            "subparts": subparts,
            "naming_a_parent_organization": with_parent,
        }
    finally:
        con.close()


def npi_rows(
    db_path: Any,
    *,
    system_id: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Read back crosswalk rows. Parameterised — never f-string a value."""
    con = sqlite3.connect(str(db_path))
    try:
        ensure_table(con)
        clauses, params = [], []
        if system_id:
            clauses.append("system_id = ?")
            params.append(system_id)
        if state:
            clauses.append("state = ?")
            params.append(str(state).upper())
        if status:
            clauses.append("status = ?")
            params.append(str(status).lower())
        if category:
            clauses.append("taxonomy_category = ?")
            params.append(str(category).lower())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(max(1, int(limit)))
        cur = con.execute(
            f"SELECT npi, entity_type, legal_name, dba_name, state, city, zip, "
            f"taxonomy_code, taxonomy_codes, taxonomy_category, "
            f"taxonomy_level_i, status, deactivation_date, reactivation_date, "
            f"is_subpart, parent_org_lbn, ein, system_id, match_basis "
            f"FROM {_TABLE}{where} ORDER BY npi LIMIT ?", params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
    finally:
        con.close()
