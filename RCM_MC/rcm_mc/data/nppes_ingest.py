"""NPPES bulk ingest — every active NPI, crosswalked to a health system.

What this is for
----------------
NPPES is the only complete register of US provider identifiers: roughly
8 million NPIs, of which ~6 million are active, published monthly by CMS
as a ~9 GB CSV. It is the missing side of the crosswalk — CCN says who
files a cost report, NPI says who bills — and nothing joins the industry
together without it.

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

#: Only these columns are read off the wire. The file carries ~330; a
#: full read is what turns a 9 GB file into an out-of-memory error.
USE_COLUMNS: Tuple[str, ...] = (
    COL_NPI, COL_ENTITY, COL_LEGAL_NAME, COL_DBA, COL_LAST, COL_FIRST,
    COL_ADDR, COL_CITY, COL_STATE, COL_ZIP, COL_TAXONOMY,
    COL_DEACTIVATION, COL_REACTIVATION,
)

ENTITY_INDIVIDUAL = "1"
ENTITY_ORGANIZATION = "2"

_TABLE = "npi_crosswalk"


@dataclass
class IngestReport:
    """What one ingest run actually did — every number measured, not estimated."""

    rows_read: int = 0
    rows_written: int = 0
    deactivated_skipped: int = 0
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
            f"{self.deactivated_skipped:,} deactivated skipped"
        )


def ensure_table(con: sqlite3.Connection) -> None:
    """Create the NPI crosswalk table.

    ``npi`` is the primary key so a re-run upserts rather than
    duplicating — an ingest of a 9 GB file will get interrupted, and
    resuming has to be safe.
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
    con.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_system ON {_TABLE}(system_id)")
    con.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_state ON {_TABLE}(state)")
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


def _is_active(row: Dict[str, Any]) -> bool:
    """An NPI is inactive only if deactivated and never reactivated.

    NPPES leaves the deactivation date populated on records that were
    later reactivated, so testing deactivation alone throws away live
    providers.
    """
    deact = str(row.get(COL_DEACTIVATION) or "").strip()
    react = str(row.get(COL_REACTIVATION) or "").strip()
    return not deact or bool(react)


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
    progress: Optional[Any] = None,
) -> IngestReport:
    """Stream an NPPES dissemination file into the NPI crosswalk table.

    Peak memory is one chunk, not one file. ``organizations_only``
    limits the write to entity-type-2 records, which is the ~1.8 M
    subset that can carry a system brand at all — worth it when the
    goal is the system crosswalk rather than the full register.
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
                if not _is_active(row):
                    report.deactivated_skipped += 1
                    continue

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

                payload.append((
                    npi, entity, legal, dba, state,
                    str(row.get(COL_CITY) or "").strip(),
                    str(row.get(COL_ZIP) or "").strip()[:5],
                    str(row.get(COL_ADDR) or "").strip(),
                    str(row.get(COL_TAXONOMY) or "").strip(),
                    system_id, basis, now,
                ))

            if payload:
                con.executemany(
                    f"INSERT INTO {_TABLE} (npi, entity_type, legal_name, "
                    f"dba_name, state, city, zip, address, taxonomy_code, "
                    f"system_id, match_basis, ingested_at) "
                    f"VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
                    f"ON CONFLICT(npi) DO UPDATE SET "
                    f"legal_name=excluded.legal_name, dba_name=excluded.dba_name, "
                    f"state=excluded.state, city=excluded.city, zip=excluded.zip, "
                    f"address=excluded.address, taxonomy_code=excluded.taxonomy_code, "
                    f"system_id=excluded.system_id, match_basis=excluded.match_basis, "
                    f"ingested_at=excluded.ingested_at",
                    payload,
                )
                con.commit()
                report.rows_written += len(payload)

            if progress is not None:
                progress(report)
    finally:
        con.close()

    return report


def link_npis_to_ccns(db_path: Any, *, crosswalk: Optional[pd.DataFrame] = None
                      ) -> Dict[str, int]:
    """Attach CCNs to organization NPIs by name + state + ZIP.

    The join nobody publishes: CMS issues CCNs and NPIs from different
    systems and does not release a mapping between them. Address is the
    only bridge, so the match requires normalized-name equality within
    the same state AND the same 5-digit ZIP — all three, because name
    alone collides ("MEMORIAL HOSPITAL") and ZIP alone puts a physician
    group in the same bucket as the hospital across the street.

    Returns counts, and leaves anything ambiguous unlinked: a CCN that
    two NPIs both match is a question, not a link.
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
    stats = {"considered": 0, "linked": 0, "ambiguous": 0}
    try:
        ensure_table(con)
        con.execute(f"ALTER TABLE {_TABLE} ADD COLUMN ccn TEXT"
                    ) if not _has_column(con, "ccn") else None
        rows = con.execute(
            f"SELECT npi, legal_name, dba_name, state, zip FROM {_TABLE} "
            f"WHERE entity_type = ?", (ENTITY_ORGANIZATION,)).fetchall()
        updates: List[Tuple[str, str]] = []
        for npi, legal, dba, state, zip5 in rows:
            stats["considered"] += 1
            st = str(state or "").upper()
            z = str(zip5 or "")[:5]
            for name in (legal, dba):
                ccns = keyed.get((normalize_name(name), st, z)) if name else None
                if not ccns:
                    continue
                if len(ccns) > 1:
                    stats["ambiguous"] += 1
                    break
                updates.append((ccns[0], npi))
                stats["linked"] += 1
                break
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
        return {
            "npis": total,
            "organizations": orgs,
            "individuals": total - orgs,
            "system_matched": matched,
            "systems_represented": systems,
            "linked_to_ccn": linked,
        }
    finally:
        con.close()


def npi_rows(
    db_path: Any,
    *,
    system_id: Optional[str] = None,
    state: Optional[str] = None,
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
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(max(1, int(limit)))
        cur = con.execute(
            f"SELECT npi, entity_type, legal_name, dba_name, state, city, zip, "
            f"taxonomy_code, system_id, match_basis FROM {_TABLE}{where} "
            f"ORDER BY npi LIMIT ?", params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
    finally:
        con.close()
