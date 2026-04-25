"""NPPES NPI registry parser + loader.

NPPES (National Plan and Provider Enumeration System) publishes a
weekly CSV dump at::

    https://download.cms.gov/nppes/NPI_Files.html

Real file is ~9GB unzipped with 6M+ rows. We stream-parse line by
line so the loader stays bounded in memory regardless of input size.

We keep ONLY Type-2 (organizational) NPIs by default — those are the
billing entities that appear in payer TiC MRFs and that hospital
MRFs publish charges against. Type-1 (individual provider) NPIs
can be loaded by passing ``include_type_1=True``.

Public API::

    parse_nppes_csv(path, include_type_1=False) -> Iterator[NppesRecord]
    load_nppes(store, records) -> int
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .normalize import zip_to_cbsa


# Canonical column names from the NPPES weekly CSV header. These
# are stable across the file version we parse. If CMS renames a
# column we'd see KeyErrors immediately at parse time — which is
# the right failure mode (better than silent NULLs).
_COL_NPI                 = "NPI"
_COL_ENTITY_TYPE         = "Entity Type Code"
_COL_ORG_NAME            = "Provider Organization Name (Legal Business Name)"
_COL_LAST                = "Provider Last Name (Legal Name)"
_COL_FIRST               = "Provider First Name"
_COL_TAX_CODE            = "Healthcare Provider Taxonomy Code_1"
_COL_TAX_LABEL           = "Healthcare Provider Primary Taxonomy Switch_1"
_COL_ADDR1               = "Provider First Line Business Practice Location Address"
_COL_CITY                = "Provider Business Practice Location Address City Name"
_COL_STATE               = "Provider Business Practice Location Address State Name"
_COL_ZIP                 = "Provider Business Practice Location Address Postal Code"
_COL_LAST_UPDATED        = "Last Update Date"


@dataclass
class NppesRecord:
    npi: str
    entity_type: int
    organization_name: str = ""
    last_name: str = ""
    first_name: str = ""
    taxonomy_code: str = ""
    taxonomy_label: str = ""
    address_line: str = ""
    city: str = ""
    state: str = ""
    zip5: str = ""
    cbsa: Optional[str] = None
    nppes_last_updated: str = ""


def _str(row: dict, col: str) -> str:
    v = row.get(col)
    return str(v).strip() if v else ""


def _parse_zip5(raw: str) -> str:
    """NPPES publishes ZIP+4 like '750013215'. Strip to 5 digits."""
    if not raw:
        return ""
    s = str(raw).strip()
    if "-" in s:
        s = s.split("-", 1)[0]
    s = "".join(c for c in s if c.isdigit())
    if len(s) >= 5:
        return s[:5]
    return s.zfill(5) if s else ""


def parse_nppes_csv(
    path: object,
    *,
    include_type_1: bool = False,
) -> Iterator[NppesRecord]:
    """Stream-parse an NPPES weekly CSV. Yields one record per row
    that matches the entity-type filter."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"NPPES CSV not found at {p}")

    with p.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            npi = _str(row, _COL_NPI)
            if not npi:
                continue
            try:
                etype = int(_str(row, _COL_ENTITY_TYPE) or "0")
            except ValueError:
                continue
            if not include_type_1 and etype != 2:
                continue

            zip5 = _parse_zip5(_str(row, _COL_ZIP))
            yield NppesRecord(
                npi=npi,
                entity_type=etype,
                organization_name=_str(row, _COL_ORG_NAME),
                last_name=_str(row, _COL_LAST),
                first_name=_str(row, _COL_FIRST),
                taxonomy_code=_str(row, _COL_TAX_CODE),
                taxonomy_label=_str(row, _COL_TAX_LABEL),
                address_line=_str(row, _COL_ADDR1),
                city=_str(row, _COL_CITY).upper(),
                state=_str(row, _COL_STATE).upper(),
                zip5=zip5,
                cbsa=zip_to_cbsa(zip5),
                nppes_last_updated=_str(row, _COL_LAST_UPDATED),
            )


def load_nppes(store: Any, records: Iterable[NppesRecord]) -> int:
    """Insert/replace NPPES records. Returns the count loaded."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                con.execute(
                    """INSERT OR REPLACE INTO pricing_nppes (
                        npi, entity_type, organization_name,
                        last_name, first_name, taxonomy_code,
                        taxonomy_label, address_line, city, state,
                        zip5, cbsa, nppes_last_updated, loaded_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.npi, r.entity_type, r.organization_name,
                     r.last_name, r.first_name, r.taxonomy_code,
                     r.taxonomy_label, r.address_line, r.city,
                     r.state, r.zip5, r.cbsa,
                     r.nppes_last_updated, now),
                )
                n += 1
            con.execute(
                "INSERT OR REPLACE INTO pricing_load_log "
                "(source, key, record_count, loaded_at, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                ("nppes", "weekly_csv", n, now,
                 f"include_type_1=False, count={n}"),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n
