"""CMS Hospital General Information — official quality + type signals.

Public dataset:
    https://data.cms.gov/provider-data/dataset/xubh-q36u

What General Info adds beyond HCRIS + POS:

  - **Overall rating (1-5 stars)** — CMS's composite quality score
    from patient experience, safety, mortality, readmission. Real
    PE signal: a 1-2 star hospital has revenue-cycle + labor
    issues that flow straight into the EBITDA bridge.
  - **Hospital type** — Acute Care / Critical Access / Children's /
    Psychiatric. Sharper sector classification than HCRIS bed-class.
  - **Emergency services** — Y/N. ER drives volume + payer mix.
  - **Mortality / readmission / safety national comparison** —
    each is "Above" / "Same as" / "Below" national. A hospital
    "Below national" on readmission is bleeding CMS penalty $.

Schema in SQLite::

    CREATE TABLE IF NOT EXISTS cms_hospital_general (
        ccn TEXT PRIMARY KEY,
        facility_name TEXT,
        state TEXT,
        hospital_type TEXT,
        ownership_type TEXT,
        emergency_services INTEGER DEFAULT 0,
        overall_rating INTEGER,
        mortality_compare TEXT,
        safety_compare TEXT,
        readmission_compare TEXT,
        patient_experience_compare TEXT,
        loaded_at TEXT NOT NULL
    )

Public API::

    parse_general_csv(path) -> List[GeneralRecord]
    load_general_to_store(store, records) -> int
    refresh_general_source(store) -> int                  # data_refresh hook
    get_quality_by_ccn(store, ccn) -> Optional[dict]
    list_low_rated(store, max_stars=2) -> List[dict]      # for insights

Ships with a bundled sample CSV (~25 rows covering common test
CCNs). Real fetches replace the file or set ``RCM_MC_GENERAL_CSV``
to point at a CMS download.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Column-name candidates — CMS publishes both code-style headers
# (PRVDR_NUM) and friendly headers (Facility ID). Tolerate both.
_COL_CCN          = ("PRVDR_NUM", "ccn", "Facility ID", "facility_id")
_COL_NAME         = ("FAC_NAME", "Facility Name", "facility_name")
_COL_STATE        = ("STATE_CD", "State", "state")
_COL_HOSP_TYPE    = ("Hospital Type", "hospital_type", "HSPTL_TYPE")
_COL_OWNER        = ("Hospital Ownership", "ownership_type", "OWNERSHIP")
_COL_ER           = ("Emergency Services", "emergency_services",
                     "ER")
_COL_RATING       = ("Hospital overall rating", "overall_rating",
                     "OVRLL_RTNG")
_COL_MORTALITY    = ("Mortality national comparison",
                     "mortality_compare")
_COL_SAFETY       = ("Safety of care national comparison",
                     "safety_compare")
_COL_READMIT      = ("Readmission national comparison",
                     "readmission_compare")
_COL_PT_EXP       = ("Patient experience national comparison",
                     "patient_experience_compare")


DEFAULT_GENERAL_SAMPLE_PATH = (
    Path(__file__).parent / "general_sample.csv"
)


@dataclass
class GeneralRecord:
    """One row from the Hospital General Information file."""
    ccn: str
    facility_name: str = ""
    state: str = ""
    hospital_type: str = ""
    ownership_type: str = ""
    emergency_services: int = 0
    overall_rating: Optional[int] = None
    mortality_compare: str = ""
    safety_compare: str = ""
    readmission_compare: str = ""
    patient_experience_compare: str = ""


def _first_present(row: Dict[str, str], candidates) -> str:
    for c in candidates:
        if c in row and row[c] is not None:
            v = str(row[c]).strip()
            if v:
                return v
    return ""


def _safe_int(v: Any) -> Optional[int]:
    if v is None or v == "" or str(v).strip() in ("Not Available",
                                                  "Not Applicable"):
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def parse_general_csv(path: Path) -> List[GeneralRecord]:
    """Parse a CMS General Information CSV. Skip rows missing CCN."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"General CSV not found at {path}")

    out: List[GeneralRecord] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ccn = _first_present(row, _COL_CCN)
            if not ccn:
                continue
            er_val = _first_present(row, _COL_ER).upper()
            er_bool = 1 if er_val in ("YES", "Y", "1", "TRUE") else 0
            out.append(GeneralRecord(
                ccn=ccn,
                facility_name=_first_present(row, _COL_NAME),
                state=_first_present(row, _COL_STATE).upper(),
                hospital_type=_first_present(row, _COL_HOSP_TYPE),
                ownership_type=_first_present(row, _COL_OWNER),
                emergency_services=er_bool,
                overall_rating=_safe_int(
                    _first_present(row, _COL_RATING)),
                mortality_compare=_first_present(row, _COL_MORTALITY),
                safety_compare=_first_present(row, _COL_SAFETY),
                readmission_compare=_first_present(row, _COL_READMIT),
                patient_experience_compare=_first_present(
                    row, _COL_PT_EXP),
            ))
    return out


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS cms_hospital_general (
                ccn TEXT PRIMARY KEY,
                facility_name TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT '',
                hospital_type TEXT NOT NULL DEFAULT '',
                ownership_type TEXT NOT NULL DEFAULT '',
                emergency_services INTEGER NOT NULL DEFAULT 0,
                overall_rating INTEGER,
                mortality_compare TEXT NOT NULL DEFAULT '',
                safety_compare TEXT NOT NULL DEFAULT '',
                readmission_compare TEXT NOT NULL DEFAULT '',
                patient_experience_compare TEXT NOT NULL DEFAULT '',
                loaded_at TEXT NOT NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_cms_general_rating "
            "ON cms_hospital_general(overall_rating) "
            "WHERE overall_rating IS NOT NULL"
        )
        con.commit()


def load_general_to_store(
    store: Any, records: List[GeneralRecord],
) -> int:
    """Insert-or-replace every record. Returns row count."""
    from datetime import datetime as _dt, timezone as _tz
    _ensure_table(store)
    now = _dt.now(_tz.utc).isoformat()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                con.execute(
                    """INSERT OR REPLACE INTO cms_hospital_general (
                        ccn, facility_name, state, hospital_type,
                        ownership_type, emergency_services,
                        overall_rating, mortality_compare,
                        safety_compare, readmission_compare,
                        patient_experience_compare, loaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (r.ccn, r.facility_name, r.state, r.hospital_type,
                     r.ownership_type, r.emergency_services,
                     r.overall_rating, r.mortality_compare,
                     r.safety_compare, r.readmission_compare,
                     r.patient_experience_compare, now),
                )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return len(records)


def refresh_general_source(store: Any) -> int:
    """data_refresh hook. Uses bundled sample by default; set
    ``RCM_MC_GENERAL_CSV`` to point at a real CMS download."""
    import os as _os
    path = Path(
        _os.environ.get("RCM_MC_GENERAL_CSV",
                        DEFAULT_GENERAL_SAMPLE_PATH)
    )
    records = parse_general_csv(path)
    return load_general_to_store(store, records)


# ── Read helpers (consumed by UI + insights) ──────────────────────

def get_quality_by_ccn(
    store: Any, ccn: str,
) -> Optional[Dict[str, Any]]:
    """Single-row lookup. Returns None for unknown CCNs."""
    if not ccn:
        return None
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT * FROM cms_hospital_general WHERE ccn = ?",
            (str(ccn),),
        ).fetchone()
    return dict(row) if row else None


def list_low_rated(
    store: Any, *, max_stars: int = 2,
) -> List[Dict[str, Any]]:
    """Return CCNs at or below a quality threshold — useful for
    surfacing "your portfolio has 3 hospitals at ≤2 stars."""
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM cms_hospital_general "
            "WHERE overall_rating IS NOT NULL AND overall_rating <= ? "
            "ORDER BY overall_rating, facility_name",
            (int(max_stars),),
        ).fetchall()
    return [dict(r) for r in rows]
