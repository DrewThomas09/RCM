"""CMS Provider of Services (POS) file — facility-level ownership.

Public quarterly drop from CMS — free, ungated, well-documented:
    https://data.cms.gov/provider-of-services

What POS adds on top of HCRIS:
  - **chain_identifier** — the gold field for PE sector intel.
    Two facilities with the same chain_identifier share corporate
    ownership (HCA, LifePoint, Tenet, etc.). HCRIS doesn't carry
    this directly; it's the field that lets you say "of my 12
    deals, 4 are LifePoint and 2 are HCA."
  - **provider_subtype** — finer-grained than HCRIS's bed class
    (Short-Term Acute Care, CAH, Rehabilitation, LTCH, Psych, etc.)
  - **ownership_type** — government / voluntary-nonprofit / proprietary
  - **multi_hospital_system** — boolean flag for chain membership,
    independent of chain_identifier (some chains don't have a
    well-formed identifier but ARE multi-hospital).

Table shape in SQLite::

    CREATE TABLE IF NOT EXISTS cms_pos (
        ccn TEXT PRIMARY KEY,
        facility_name TEXT,
        state TEXT,
        city TEXT,
        zip TEXT,
        provider_type TEXT,
        provider_subtype TEXT,
        ownership_type TEXT,
        chain_identifier TEXT,
        multi_hospital_system INTEGER DEFAULT 0,
        total_beds INTEGER,
        loaded_at TEXT NOT NULL
    )

Public API::

    parse_pos_csv(path) -> List[POSRecord]
    load_pos_to_store(store, records) -> int
    refresh_pos_source(store) -> int                 # for data_refresh
    get_facility_by_ccn(store, ccn) -> Optional[dict]
    get_chain_members(store, chain_identifier) -> List[dict]
    count_facilities_in_chain(store, ccn) -> int     # useful concentration stat

The module ships with a tiny ``pos_sample.csv`` covering common
test CCNs so the refresher works on a fresh install without a
network call. Real data fetches replace it when the user runs
``rcm-mc data refresh --source cms_pos``.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# POS file column headers (2024 vintage). The real CSV has ~150
# columns; we extract only the fields that matter for PE diligence.
# Keys are the header names CMS publishes; we tolerate both the
# long column codes (e.g. CRTFCTN_EFCTV_DT) and the friendly
# column headers that the Data Dictionary publishes.
_COL_CCN          = ("PRVDR_NUM", "ccn", "provider_number",
                     "CCN")
_COL_NAME         = ("FAC_NAME", "facility_name", "FACILITY NAME",
                     "provider_name")
_COL_STATE        = ("STATE_CD", "state", "STATE")
_COL_CITY         = ("CITY_NAME", "city", "CITY")
_COL_ZIP          = ("ZIP_CD", "zip", "ZIP", "zip_code")
_COL_PROV_TYPE    = ("PRVDR_CTGRY_CD", "provider_type",
                     "PROVIDER CATEGORY")
_COL_PROV_SUBTYPE = ("PRVDR_CTGRY_SBTYP_CD", "provider_subtype",
                     "PROVIDER SUBTYPE")
_COL_OWNER        = ("GNRL_CNTL_TYPE_CD", "ownership_type",
                     "OWNERSHIP")
_COL_CHAIN        = ("CHAIN_IDENT_NUM", "chain_identifier",
                     "CHAIN ID")
_COL_MULTI        = ("MLT_HSPTL_SYS_IND", "multi_hospital_system",
                     "MULTI HOSPITAL SYSTEM")
_COL_BEDS         = ("BED_CNT", "total_beds", "TOTAL BEDS", "beds")


DEFAULT_POS_SAMPLE_PATH = (
    Path(__file__).parent / "pos_sample.csv"
)


# ── Dataclass ──────────────────────────────────────────────────────

@dataclass
class POSRecord:
    """One hospital / facility row from the CMS POS file."""
    ccn: str
    facility_name: str = ""
    state: str = ""
    city: str = ""
    zip: str = ""
    provider_type: str = ""
    provider_subtype: str = ""
    ownership_type: str = ""
    chain_identifier: str = ""
    multi_hospital_system: int = 0
    total_beds: Optional[int] = None


# ── Parser ─────────────────────────────────────────────────────────

def _first_present(row: Dict[str, str], candidates) -> str:
    """Return the first non-empty value across a tuple of column-name
    candidates. POS CSV headers vary across vintages — sometimes
    `PRVDR_NUM`, sometimes `ccn`. This shrugs and takes what's there.
    """
    for c in candidates:
        if c in row and row[c] is not None:
            v = str(row[c]).strip()
            if v:
                return v
    return ""


def _safe_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def parse_pos_csv(path: Path) -> List[POSRecord]:
    """Parse a POS CSV into POSRecord rows. Column names are
    auto-detected from the first-row header — see the _COL_* tuples
    above for accepted variants."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"POS CSV not found at {path}")

    out: List[POSRecord] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ccn = _first_present(row, _COL_CCN)
            if not ccn:
                continue  # every useful row must have a CCN
            multi = _first_present(row, _COL_MULTI).upper()
            multi_bool = 1 if multi in ("Y", "YES", "1", "TRUE") else 0
            out.append(POSRecord(
                ccn=ccn,
                facility_name=_first_present(row, _COL_NAME),
                state=_first_present(row, _COL_STATE).upper(),
                city=_first_present(row, _COL_CITY),
                zip=_first_present(row, _COL_ZIP),
                provider_type=_first_present(row, _COL_PROV_TYPE),
                provider_subtype=_first_present(row, _COL_PROV_SUBTYPE),
                ownership_type=_first_present(row, _COL_OWNER),
                chain_identifier=_first_present(row, _COL_CHAIN),
                multi_hospital_system=multi_bool,
                total_beds=_safe_int(_first_present(row, _COL_BEDS)),
            ))
    return out


# ── Store loader ───────────────────────────────────────────────────

def _ensure_table(store: Any) -> None:
    """Idempotent schema — identical semantics to every other
    data-source table in rcm_mc.data.*."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS cms_pos (
                ccn TEXT PRIMARY KEY,
                facility_name TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                zip TEXT NOT NULL DEFAULT '',
                provider_type TEXT NOT NULL DEFAULT '',
                provider_subtype TEXT NOT NULL DEFAULT '',
                ownership_type TEXT NOT NULL DEFAULT '',
                chain_identifier TEXT NOT NULL DEFAULT '',
                multi_hospital_system INTEGER NOT NULL DEFAULT 0,
                total_beds INTEGER,
                loaded_at TEXT NOT NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_cms_pos_chain "
            "ON cms_pos(chain_identifier) "
            "WHERE chain_identifier != ''"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_cms_pos_state "
            "ON cms_pos(state)"
        )
        con.commit()


def load_pos_to_store(store: Any, records: List[POSRecord]) -> int:
    """Insert-or-replace every POS record. Returns row count."""
    from datetime import datetime as _dt, timezone as _tz
    _ensure_table(store)
    now = _dt.now(_tz.utc).isoformat()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                con.execute(
                    """INSERT OR REPLACE INTO cms_pos (
                        ccn, facility_name, state, city, zip,
                        provider_type, provider_subtype, ownership_type,
                        chain_identifier, multi_hospital_system,
                        total_beds, loaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (r.ccn, r.facility_name, r.state, r.city, r.zip,
                     r.provider_type, r.provider_subtype, r.ownership_type,
                     r.chain_identifier, r.multi_hospital_system,
                     r.total_beds, now),
                )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return len(records)


def refresh_pos_source(store: Any) -> int:
    """Called by :func:`rcm_mc.data.data_refresh.refresh_all_sources`.

    Uses the bundled ``pos_sample.csv`` as the authoritative source
    for fresh installs. A real deploy replaces that file (or sets
    ``RCM_MC_POS_CSV`` to point at a full CMS POS CSV) to bring in
    the full ~7000-row national dataset.
    """
    import os as _os
    path = Path(
        _os.environ.get("RCM_MC_POS_CSV", DEFAULT_POS_SAMPLE_PATH)
    )
    records = parse_pos_csv(path)
    return load_pos_to_store(store, records)


# ── Read helpers (consumed by UI + peer matching) ──────────────────

def get_facility_by_ccn(store: Any, ccn: str) -> Optional[Dict[str, Any]]:
    """Single-row lookup. Returns None for unknown CCNs."""
    if not ccn:
        return None
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT * FROM cms_pos WHERE ccn = ?", (str(ccn),),
        ).fetchone()
    return dict(row) if row else None


def get_chain_members(
    store: Any, chain_identifier: str,
) -> List[Dict[str, Any]]:
    """Return every CCN in a chain. Empty list for unknown chain."""
    if not chain_identifier:
        return []
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM cms_pos WHERE chain_identifier = ? "
            "ORDER BY state, facility_name",
            (str(chain_identifier),),
        ).fetchall()
    return [dict(r) for r in rows]


def count_facilities_in_chain(store: Any, ccn: str) -> int:
    """How many facilities does this CCN's chain own? Returns 1 for
    an independent (or unknown-chain) facility, so the return is
    always meaningful for a concentration-risk chart."""
    fac = get_facility_by_ccn(store, ccn)
    if not fac:
        return 0
    chain = fac.get("chain_identifier") or ""
    if not chain:
        return 1
    return len(get_chain_members(store, chain))
