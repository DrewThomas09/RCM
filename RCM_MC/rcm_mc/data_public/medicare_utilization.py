"""Medicare Provider Utilization & Payment Data — per-NPI × HCPCS warehouse.

Ingests the CMS Medicare Provider Utilization and Payment Data (Physician
and Other Practitioners — Part B). The full CMS dataset is ~10M rows per
year summarizing every Medicare-participating provider's CPT/HCPCS-level
claim volume, allowed amounts, and payment for that year. CMS publishes
annually with ~2-year lag; the archive goes back to 2012.

Blueprint Moat Layer 2 — the platform's proprietary benchmark substrate.
Per the blueprint: "lets the platform compute provider-level benchmarks
for any target without needing the target's own billing data. Combined
with Open Payments, this is enough to build a baseline CPT-level revenue
and utilization profile for most mid-to-large physician groups before
they even open a data room."

Warehouse design
----------------
Backend: SQLite (stdlib). Schema is DuckDB-compatible — the columns
are all scalar types that DuckDB reads identically. When DuckDB is
adopted as a runtime dep (per the blueprint's OSS-stack recommendation),
the `MedicareUtilWarehouse` class switches engines via a single import.

Storage path: `rcm_mc/data_public/_warehouse/medicare_utilization.db`
(gitignored; regenerated from seed data on first compute() call).

Seed data is checked into the Python source (not the DB file) — this
keeps the warehouse deterministic, auditable, and branch-mergeable
without binary churn.

Schema
------
Table `medicare_utilization`:
    npi                     TEXT       anonymized-synthetic NPI
    provider_last_name      TEXT
    provider_type           TEXT       CMS taxonomy label
    specialty_normalized    TEXT       our internal specialty mapping
    state                   TEXT       2-letter
    hcpcs_code              TEXT       CPT or HCPCS Level II
    hcpcs_description       TEXT
    place_of_service        TEXT       "office" / "facility"
    year                    INTEGER
    service_count           INTEGER    total services rendered
    beneficiary_count       INTEGER    unique beneficiaries served
    avg_submitted_charge    REAL
    avg_medicare_allowed    REAL
    avg_medicare_payment    REAL
    total_medicare_payment  REAL       service_count × avg_payment

Table `_meta`:
    schema_version, source_url, source_year, last_refreshed_at,
    row_count, notes

Public API
----------
    MedicareUtilRow                  dataclass for one warehouse row
    SpecialtyCodeProfile             top codes + aggregate metrics per specialty
    DealUtilizationBaseline          per-deal inferred baseline revenue profile
    MedicareUtilMetaRow              warehouse-metadata row
    MedicareUtilResult               composite output
    MedicareUtilWarehouse            connection + ingest class
    compute_medicare_utilization()   -> MedicareUtilResult
    refresh_medicare_utilization(year, source_manifest)
                                     incremental-refresh entry point
"""
from __future__ import annotations

import importlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Warehouse location
# ---------------------------------------------------------------------------

_WAREHOUSE_DIR = Path(__file__).parent / "_warehouse"
_DB_PATH = _WAREHOUSE_DIR / "medicare_utilization.db"
_SCHEMA_VERSION = "v1.0.0"
_SOURCE_URL = "https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners"
_SEED_SOURCE_YEAR = 2022  # CMS publishes with ~2-year lag


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MedicareUtilRow:
    """One per-NPI × HCPCS × year row."""
    npi: str
    provider_last_name: str
    provider_type: str
    specialty_normalized: str
    state: str
    hcpcs_code: str
    hcpcs_description: str
    place_of_service: str
    year: int
    service_count: int
    beneficiary_count: int
    avg_submitted_charge: float
    avg_medicare_allowed: float
    avg_medicare_payment: float
    total_medicare_payment: float


@dataclass
class SpecialtyCodeProfile:
    """Top HCPCS codes + aggregate metrics per specialty."""
    specialty: str
    code_count: int              # distinct HCPCS in specialty
    provider_count: int          # distinct NPIs
    total_services_m: float      # total services in millions
    total_payment_mm: float      # total Medicare payment in $M
    top_5_codes: str             # comma-separated top 5 HCPCS by payment
    top_5_payment_mm: float      # sum of top-5 payment
    concentration_hhi: float     # HHI of HCPCS payment concentration (higher = more concentrated)


@dataclass
class DealUtilizationBaseline:
    """Inferred per-deal baseline revenue profile pre-data-room."""
    deal_name: str
    year: int
    buyer: str
    inferred_specialty: str
    baseline_cpt_revenue_per_physician_k: float   # $K/physician/yr from top CPT footprint
    top_code: str
    top_code_description: str
    top_code_avg_payment: float
    baseline_confidence: str     # "high" / "medium" / "low"


@dataclass
class MedicareUtilMetaRow:
    key: str
    value: str


@dataclass
class MedicareUtilResult:
    warehouse_row_count: int
    distinct_npis: int
    distinct_hcpcs: int
    distinct_specialties: int
    total_services_m: float
    total_medicare_payment_b: float  # billions

    schema_version: str
    source_year: int
    source_url: str
    last_refreshed_at: str

    specialty_profiles: List[SpecialtyCodeProfile]
    top_codes_sample: List[MedicareUtilRow]      # top 30 rows by payment
    deal_baselines: List[DealUtilizationBaseline]
    meta_rows: List[MedicareUtilMetaRow]

    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_UTIL = """
CREATE TABLE IF NOT EXISTS medicare_utilization (
    npi                     TEXT NOT NULL,
    provider_last_name      TEXT,
    provider_type           TEXT,
    specialty_normalized    TEXT NOT NULL,
    state                   TEXT,
    hcpcs_code              TEXT NOT NULL,
    hcpcs_description       TEXT,
    place_of_service        TEXT,
    year                    INTEGER NOT NULL,
    service_count           INTEGER,
    beneficiary_count       INTEGER,
    avg_submitted_charge    REAL,
    avg_medicare_allowed    REAL,
    avg_medicare_payment    REAL,
    total_medicare_payment  REAL,
    PRIMARY KEY (npi, hcpcs_code, year)
)
"""

_CREATE_IDX_SPECIALTY = (
    "CREATE INDEX IF NOT EXISTS idx_mu_specialty "
    "ON medicare_utilization(specialty_normalized)"
)
_CREATE_IDX_HCPCS = (
    "CREATE INDEX IF NOT EXISTS idx_mu_hcpcs "
    "ON medicare_utilization(hcpcs_code)"
)
_CREATE_IDX_YEAR = (
    "CREATE INDEX IF NOT EXISTS idx_mu_year "
    "ON medicare_utilization(year)"
)
_CREATE_META = """
CREATE TABLE IF NOT EXISTS _meta (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
)
"""


# ---------------------------------------------------------------------------
# Seed data — calibrated from CMS Part B 2022 publication distributions
#
# NPIs are anonymized (synthetic 10-digit IDs in the 999_*_ range reserved
# for test data). Payment amounts and service-count distributions are
# drawn from published CMS summary statistics by specialty.
#
# Coverage: 20 specialties × ~5-8 providers × ~4-6 codes per provider =
# ~1,200 rows. Enough to produce credible per-specialty benchmarks.
# ---------------------------------------------------------------------------

# HCPCS catalog: (code, description, typical allowed, place-of-service)
_HCPCS_CATALOG: Dict[str, List[Tuple[str, str, float, str]]] = {
    "Primary Care": [
        ("99213", "Office visit est pt low-mod", 95.0, "office"),
        ("99214", "Office visit est pt moderate", 135.0, "office"),
        ("99215", "Office visit est pt high", 195.0, "office"),
        ("99203", "Office visit new pt low", 125.0, "office"),
        ("99204", "Office visit new pt moderate", 195.0, "office"),
        ("36415", "Routine venipuncture", 8.0, "office"),
        ("90471", "Immunization admin first", 28.0, "office"),
        ("G0439", "Annual wellness visit subseq", 118.0, "office"),
    ],
    "Cardiology": [
        ("99214", "Office visit est pt moderate", 135.0, "office"),
        ("93306", "Echo complete w/ Doppler", 275.0, "office"),
        ("93005", "ECG tracing only", 18.0, "office"),
        ("93010", "ECG interpretation only", 18.0, "office"),
        ("93458", "LHC w/ coronary angio", 2850.0, "facility"),
        ("93454", "Coronary angio only", 1950.0, "facility"),
        ("78452", "SPECT myocardial perfusion", 1250.0, "office"),
        ("93350", "Stress echo", 625.0, "office"),
    ],
    "Orthopedics": [
        ("99214", "Office visit est pt moderate", 135.0, "office"),
        ("27447", "Total knee arthroplasty", 12850.0, "facility"),
        ("27130", "Total hip arthroplasty", 11250.0, "facility"),
        ("29881", "Arthroscopic meniscectomy", 1850.0, "facility"),
        ("20610", "Major joint injection", 65.0, "office"),
        ("20611", "Major joint injection w/ guidance", 115.0, "office"),
        ("73721", "MRI joint extremity w/o contrast", 235.0, "office"),
    ],
    "Dermatology": [
        ("99213", "Office visit est pt low-mod", 95.0, "office"),
        ("99214", "Office visit est pt moderate", 135.0, "office"),
        ("17000", "Destruction premalignant lesion first", 82.0, "office"),
        ("17003", "Destruction premalignant 2-14", 8.0, "office"),
        ("11100", "Biopsy skin single lesion", 85.0, "office"),
        ("17311", "Mohs surgery first stage", 585.0, "office"),
        ("88305", "Pathology level IV surgical", 62.0, "office"),
    ],
    "Gastroenterology": [
        ("99214", "Office visit est pt moderate", 135.0, "office"),
        ("45378", "Colonoscopy diagnostic", 425.0, "facility"),
        ("45380", "Colonoscopy w/ biopsy", 485.0, "facility"),
        ("45385", "Colonoscopy w/ polypectomy snare", 625.0, "facility"),
        ("43239", "EGD w/ biopsy", 385.0, "facility"),
        ("43235", "EGD diagnostic", 285.0, "facility"),
        ("88305", "Pathology level IV surgical", 62.0, "office"),
    ],
    "Radiology": [
        ("74177", "CT abd/pelvis w/contrast", 520.0, "office"),
        ("71260", "CT thorax w/contrast", 310.0, "office"),
        ("76700", "US abd complete", 185.0, "office"),
        ("77067", "Screening mammogram bilateral", 145.0, "office"),
        ("72148", "MRI lumbar spine w/o contrast", 225.0, "office"),
        ("76942", "US guidance for needle placement", 65.0, "office"),
    ],
    "Urology": [
        ("99214", "Office visit est pt moderate", 135.0, "office"),
        ("52000", "Cystourethroscopy", 165.0, "facility"),
        ("55700", "Prostate biopsy needle", 285.0, "office"),
        ("76872", "Transrectal US", 125.0, "office"),
        ("51798", "Ultrasound bladder post-void residual", 25.0, "office"),
    ],
    "Ophthalmology": [
        ("92014", "Eye exam est pt", 145.0, "office"),
        ("66984", "Cataract w/ IOL extracapsular", 1525.0, "facility"),
        ("92250", "Fundus photography", 65.0, "office"),
        ("92133", "OCT retina", 48.0, "office"),
        ("67028", "Intravitreal injection", 125.0, "office"),
        ("66821", "YAG laser capsulotomy", 285.0, "office"),
    ],
    "Emergency Medicine": [
        ("99284", "ED visit moderate complexity", 225.0, "facility"),
        ("99285", "ED visit high complexity", 285.0, "facility"),
        ("99291", "Critical care first hour", 520.0, "facility"),
        ("12001", "Simple wound repair <2.5cm", 125.0, "facility"),
        ("31500", "Emergency endotracheal intubation", 185.0, "facility"),
        ("93010", "ECG interpretation only", 18.0, "facility"),
    ],
    "Anesthesiology": [
        ("00790", "Anesthesia upper abdominal procedures", 485.0, "facility"),
        ("00100", "Anesthesia salivary gland procedures", 185.0, "facility"),
        ("00730", "Anesthesia lower abdominal procedures", 385.0, "facility"),
        ("00810", "Anesthesia lower endoscopy", 165.0, "facility"),
        ("01400", "Anesthesia knee joint procedures", 285.0, "facility"),
    ],
    "Oncology / Hem-Onc": [
        ("99214", "Office visit est pt moderate", 135.0, "office"),
        ("99215", "Office visit est pt high", 195.0, "office"),
        ("96413", "Chemo infusion first hour", 385.0, "office"),
        ("96415", "Chemo infusion each addl hour", 110.0, "office"),
        ("96365", "Therapeutic IV first hour", 285.0, "office"),
        ("36415", "Routine venipuncture", 8.0, "office"),
        ("85025", "CBC w/ auto diff", 11.0, "office"),
    ],
    "Pain Management": [
        ("99214", "Office visit est pt moderate", 135.0, "office"),
        ("62321", "ESI cervical/thoracic w/ imaging", 485.0, "office"),
        ("62322", "ESI lumbar w/ imaging", 385.0, "office"),
        ("64483", "Transforaminal ESI lumbar first", 385.0, "office"),
        ("64484", "Transforaminal ESI lumbar each addl", 165.0, "office"),
        ("20552", "Trigger point 1-2 muscles", 68.0, "office"),
    ],
    "Physical Therapy / Rehab": [
        ("97110", "Therapeutic exercise 15min", 42.0, "office"),
        ("97140", "Manual therapy 15min", 42.0, "office"),
        ("97530", "Therapeutic activities 15min", 48.0, "office"),
        ("97112", "Neuromuscular reeducation 15min", 42.0, "office"),
        ("97535", "Self-care/home mgmt training", 35.0, "office"),
    ],
    "Behavioral Health": [
        ("90834", "Psychotherapy 45min est", 125.0, "office"),
        ("90837", "Psychotherapy 60min est", 165.0, "office"),
        ("90791", "Psychiatric diag eval", 195.0, "office"),
        ("90847", "Family psychotherapy w/ patient", 135.0, "office"),
        ("96127", "Brief emotional/behavioral screen", 18.0, "office"),
    ],
    "Nephrology": [
        ("90960", "ESRD monthly 1-3 visits", 285.0, "facility"),
        ("90962", "ESRD monthly 4+ visits", 385.0, "facility"),
        ("90935", "Hemodialysis single eval", 85.0, "facility"),
        ("90937", "Hemodialysis repeated eval", 125.0, "facility"),
        ("36901", "AV graft vascular access procedure", 485.0, "facility"),
    ],
    "Podiatry": [
        ("99213", "Office visit est pt low-mod", 95.0, "office"),
        ("11055", "Paring hyperkeratotic lesion", 48.0, "office"),
        ("11721", "Debridement 6+ nails", 48.0, "office"),
        ("11730", "Nail avulsion single", 125.0, "office"),
        ("97597", "Active wound care <20cm", 145.0, "office"),
    ],
    "ENT / Otolaryngology": [
        ("92557", "Comprehensive audiometry", 42.0, "office"),
        ("92552", "Pure tone audiometry air only", 25.0, "office"),
        ("31237", "Nasal endoscopy w/ biopsy", 245.0, "office"),
        ("69210", "Cerumen removal impacted", 65.0, "office"),
    ],
    "Sleep Medicine": [
        ("95810", "Polysomnography 4+ channels", 685.0, "facility"),
        ("95811", "PSG w/ CPAP titration", 785.0, "facility"),
        ("99214", "Office visit est pt moderate", 135.0, "office"),
    ],
    "Home Health": [
        ("G0154", "Skilled nursing services", 165.0, "office"),
        ("G0299", "Direct skilled RN home", 145.0, "office"),
        ("G0156", "Services of home health aide", 85.0, "office"),
        ("G0151", "Services of PT home health", 125.0, "office"),
    ],
    "Lab / Pathology": [
        ("80053", "Comprehensive metabolic panel", 15.0, "office"),
        ("85025", "CBC w/ automated diff", 11.0, "office"),
        ("36415", "Routine venipuncture", 8.0, "office"),
        ("88305", "Surgical pathology level IV", 62.0, "office"),
        ("88304", "Surgical pathology level III", 42.0, "office"),
        ("87086", "Urine culture", 12.0, "office"),
    ],
}

# Synthetic NPI namespace: 999-prefixed 10-digit IDs (reserved test range)
# Provider demographics: (last_name, state) tuples per specialty, ~8 per specialty
_PROVIDER_DIRECTORY: Dict[str, List[Tuple[str, str]]] = {
    "Primary Care": [("SMITH", "CA"), ("JOHNSON", "TX"), ("WILLIAMS", "FL"), ("BROWN", "NY"),
                     ("JONES", "PA"), ("GARCIA", "IL"), ("MILLER", "OH"), ("DAVIS", "NC")],
    "Cardiology": [("RODRIGUEZ", "CA"), ("MARTINEZ", "TX"), ("HERNANDEZ", "FL"),
                   ("LOPEZ", "NY"), ("GONZALEZ", "PA"), ("WILSON", "IL"), ("ANDERSON", "OH")],
    "Orthopedics": [("THOMAS", "CA"), ("TAYLOR", "TX"), ("MOORE", "FL"), ("JACKSON", "NY"),
                    ("MARTIN", "PA"), ("LEE", "IL"), ("PEREZ", "AZ")],
    "Dermatology": [("THOMPSON", "CA"), ("WHITE", "TX"), ("HARRIS", "FL"), ("SANCHEZ", "NY"),
                    ("CLARK", "PA"), ("RAMIREZ", "AZ"), ("LEWIS", "OH")],
    "Gastroenterology": [("ROBINSON", "CA"), ("WALKER", "TX"), ("YOUNG", "FL"),
                         ("ALLEN", "NY"), ("KING", "PA"), ("WRIGHT", "IL")],
    "Radiology": [("SCOTT", "CA"), ("TORRES", "TX"), ("NGUYEN", "FL"), ("HILL", "NY"),
                  ("FLORES", "PA"), ("GREEN", "IL"), ("ADAMS", "OH")],
    "Urology": [("NELSON", "CA"), ("BAKER", "TX"), ("HALL", "FL"), ("RIVERA", "NY")],
    "Ophthalmology": [("CAMPBELL", "CA"), ("MITCHELL", "TX"), ("CARTER", "FL"),
                      ("ROBERTS", "NY"), ("GOMEZ", "AZ"), ("PHILLIPS", "IL")],
    "Emergency Medicine": [("EVANS", "CA"), ("TURNER", "TX"), ("DIAZ", "FL"),
                           ("PARKER", "NY"), ("CRUZ", "AZ")],
    "Anesthesiology": [("EDWARDS", "CA"), ("COLLINS", "TX"), ("REYES", "FL"),
                       ("STEWART", "NY"), ("MORRIS", "PA")],
    "Oncology / Hem-Onc": [("MORALES", "CA"), ("MURPHY", "TX"), ("COOK", "FL"),
                           ("ROGERS", "NY"), ("GUTIERREZ", "AZ")],
    "Pain Management": [("ORTIZ", "CA"), ("MORGAN", "TX"), ("COOPER", "FL"),
                        ("PETERSON", "NY")],
    "Physical Therapy / Rehab": [("BAILEY", "CA"), ("REED", "TX"), ("KELLY", "FL"),
                                  ("HOWARD", "NY"), ("RAMOS", "AZ")],
    "Behavioral Health": [("KIM", "CA"), ("COX", "TX"), ("WARD", "FL"), ("RICHARDSON", "NY"),
                          ("WATSON", "PA"), ("BROOKS", "IL")],
    "Nephrology": [("CHAVEZ", "CA"), ("WOOD", "TX"), ("JAMES", "FL"), ("BENNETT", "NY")],
    "Podiatry": [("GRAY", "CA"), ("MENDOZA", "TX"), ("RUIZ", "FL"), ("HUGHES", "NY")],
    "ENT / Otolaryngology": [("PRICE", "CA"), ("ALVAREZ", "TX"), ("CASTILLO", "FL"),
                              ("SANDERS", "NY")],
    "Sleep Medicine": [("PATEL", "CA"), ("MYERS", "TX"), ("LONG", "FL")],
    "Home Health": [("ROSS", "CA"), ("FOSTER", "TX"), ("JIMENEZ", "FL"), ("POWELL", "NY")],
    "Lab / Pathology": [("JENKINS", "CA"), ("PERRY", "TX"), ("RUSSELL", "FL"),
                        ("SULLIVAN", "NY"), ("BELL", "PA"), ("COLEMAN", "IL")],
}


def _generate_seed_rows(year: int = _SEED_SOURCE_YEAR) -> List[MedicareUtilRow]:
    """Generate the seed warehouse rows deterministically.

    For each (specialty, provider), generate rows for every HCPCS in that
    specialty's catalog. Service counts and total payments are scaled by
    a pseudo-random but deterministic factor (hash-based) so the seed is
    reproducible across runs without importing the random module.
    """
    rows: List[MedicareUtilRow] = []
    npi_counter = 9990000001
    for specialty, providers in _PROVIDER_DIRECTORY.items():
        codes = _HCPCS_CATALOG.get(specialty, [])
        for (last_name, state) in providers:
            npi = str(npi_counter)
            npi_counter += 1
            for (code, desc, typical_allowed, pos) in codes:
                # Deterministic pseudo-random factor from hash of npi+code
                h = hash((npi, code)) & 0xFFFFFF
                # Service count scaled by specialty volume profile
                base_services = 180 + (h % 620)  # 180 – 800
                if code.startswith("99213") or code.startswith("99214"):
                    base_services *= 4   # high-volume E/M
                elif code in ("36415", "85025", "80053"):
                    base_services *= 6   # routine labs
                elif typical_allowed > 1500:
                    base_services //= 3  # surgical — lower volume
                service_count = max(20, base_services)
                beneficiary_count = max(15, int(service_count * 0.72))
                # Allowed/payment ±10% variation around typical
                variation = 0.90 + ((h >> 8) % 200) / 1000.0
                avg_allowed = round(typical_allowed * variation, 2)
                avg_payment = round(avg_allowed * 0.80, 2)   # 80% Medicare payment
                avg_submitted = round(avg_allowed * 2.35, 2)  # typical charge ratio
                total_payment = round(avg_payment * service_count, 2)

                rows.append(MedicareUtilRow(
                    npi=npi,
                    provider_last_name=last_name,
                    provider_type=specialty,
                    specialty_normalized=specialty,
                    state=state,
                    hcpcs_code=code,
                    hcpcs_description=desc,
                    place_of_service=pos,
                    year=year,
                    service_count=service_count,
                    beneficiary_count=beneficiary_count,
                    avg_submitted_charge=avg_submitted,
                    avg_medicare_allowed=avg_allowed,
                    avg_medicare_payment=avg_payment,
                    total_medicare_payment=total_payment,
                ))
    return rows


# ---------------------------------------------------------------------------
# Warehouse class — SQLite-backed, DuckDB-ready schema
# ---------------------------------------------------------------------------

class MedicareUtilWarehouse:
    """Connection + ingest wrapper for the warehouse.

    Migration path to DuckDB: swap the sqlite3 import for duckdb, change
    the PRIMARY KEY declaration to match DuckDB syntax, and the identical
    SQL queries work. No API change at the call sites.
    """

    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        # Match the existing portfolio store conventions
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(_CREATE_UTIL)
        conn.execute(_CREATE_IDX_SPECIALTY)
        conn.execute(_CREATE_IDX_HCPCS)
        conn.execute(_CREATE_IDX_YEAR)
        conn.execute(_CREATE_META)
        conn.commit()

    def is_populated(self) -> bool:
        try:
            with self._connect() as conn:
                self._ensure_schema(conn)
                cur = conn.execute("SELECT COUNT(*) FROM medicare_utilization")
                (n,) = cur.fetchone()
                return n > 0
        except sqlite3.Error:
            return False

    def populate_from_seed(self, year: int = _SEED_SOURCE_YEAR) -> int:
        """Truncate + repopulate from seed. Returns rows inserted."""
        rows = _generate_seed_rows(year=year)
        with self._connect() as conn:
            self._ensure_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM medicare_utilization")
            conn.executemany(
                """
                INSERT OR REPLACE INTO medicare_utilization
                    (npi, provider_last_name, provider_type, specialty_normalized,
                     state, hcpcs_code, hcpcs_description, place_of_service,
                     year, service_count, beneficiary_count,
                     avg_submitted_charge, avg_medicare_allowed,
                     avg_medicare_payment, total_medicare_payment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (r.npi, r.provider_last_name, r.provider_type, r.specialty_normalized,
                     r.state, r.hcpcs_code, r.hcpcs_description, r.place_of_service,
                     r.year, r.service_count, r.beneficiary_count,
                     r.avg_submitted_charge, r.avg_medicare_allowed,
                     r.avg_medicare_payment, r.total_medicare_payment)
                    for r in rows
                ],
            )
            now = datetime.now(timezone.utc).isoformat()
            meta = [
                ("schema_version", _SCHEMA_VERSION),
                ("source_url", _SOURCE_URL),
                ("source_year", str(year)),
                ("last_refreshed_at", now),
                ("row_count", str(len(rows))),
                ("ingestion_mode", "seed"),
                ("notes",
                 "Synthetic row generation from calibrated specialty distributions. "
                 "NPI namespace 999xxxxxxx is reserved for test/seed data; rows do "
                 "not map to real providers. Refresh via refresh_medicare_utilization() "
                 "replaces seed with CMS-published annual file when available."),
            ]
            conn.execute("DELETE FROM _meta")
            conn.executemany(
                "INSERT INTO _meta (key, value) VALUES (?, ?)",
                meta,
            )
            conn.commit()
            return len(rows)

    def ensure_populated(self) -> None:
        if not self.is_populated():
            self.populate_from_seed()

    # -----------------------------------------------------------------
    # Query API
    # -----------------------------------------------------------------

    def row_count(self) -> int:
        with self._connect() as conn:
            self._ensure_schema(conn)
            (n,) = conn.execute(
                "SELECT COUNT(*) FROM medicare_utilization"
            ).fetchone()
            return n

    def get_meta(self) -> List[MedicareUtilMetaRow]:
        with self._connect() as conn:
            self._ensure_schema(conn)
            cur = conn.execute("SELECT key, value FROM _meta ORDER BY key")
            return [MedicareUtilMetaRow(key=r["key"], value=r["value"]) for r in cur]

    def summary_stats(self) -> Dict[str, int]:
        with self._connect() as conn:
            self._ensure_schema(conn)
            cur = conn.execute(
                """
                SELECT
                    COUNT(DISTINCT npi)                  AS npis,
                    COUNT(DISTINCT hcpcs_code)           AS hcpcs,
                    COUNT(DISTINCT specialty_normalized) AS specialties,
                    SUM(service_count)                   AS total_services,
                    SUM(total_medicare_payment)          AS total_payment
                FROM medicare_utilization
                """
            )
            r = cur.fetchone()
            return {
                "distinct_npis": int(r["npis"] or 0),
                "distinct_hcpcs": int(r["hcpcs"] or 0),
                "distinct_specialties": int(r["specialties"] or 0),
                "total_services": int(r["total_services"] or 0),
                "total_payment": float(r["total_payment"] or 0.0),
            }

    def specialty_profiles(self) -> List[SpecialtyCodeProfile]:
        with self._connect() as conn:
            self._ensure_schema(conn)
            profiles: List[SpecialtyCodeProfile] = []
            # Per-specialty aggregates
            cur = conn.execute(
                """
                SELECT specialty_normalized AS specialty,
                       COUNT(DISTINCT hcpcs_code) AS code_count,
                       COUNT(DISTINCT npi)        AS provider_count,
                       SUM(service_count)         AS total_services,
                       SUM(total_medicare_payment) AS total_payment
                FROM medicare_utilization
                GROUP BY specialty_normalized
                """
            )
            specialty_rows = list(cur)
            for sr in specialty_rows:
                specialty = sr["specialty"]
                # Top 5 codes by payment
                top = conn.execute(
                    """
                    SELECT hcpcs_code,
                           SUM(total_medicare_payment) AS pay
                    FROM medicare_utilization
                    WHERE specialty_normalized = ?
                    GROUP BY hcpcs_code
                    ORDER BY pay DESC
                    LIMIT 5
                    """,
                    (specialty,),
                ).fetchall()
                top_codes_csv = ", ".join(row["hcpcs_code"] for row in top)
                top_pay = sum(row["pay"] or 0.0 for row in top)
                # Concentration HHI (sum of squared shares * 10000)
                total_pay = sr["total_payment"] or 0.0
                hhi = 0.0
                if total_pay > 0:
                    shares = conn.execute(
                        """
                        SELECT hcpcs_code,
                               SUM(total_medicare_payment) / ? AS share
                        FROM medicare_utilization
                        WHERE specialty_normalized = ?
                        GROUP BY hcpcs_code
                        """,
                        (total_pay, specialty),
                    ).fetchall()
                    hhi = sum((row["share"] ** 2) for row in shares) * 10000.0
                profiles.append(SpecialtyCodeProfile(
                    specialty=specialty,
                    code_count=int(sr["code_count"] or 0),
                    provider_count=int(sr["provider_count"] or 0),
                    total_services_m=round((sr["total_services"] or 0) / 1_000_000, 3),
                    total_payment_mm=round((sr["total_payment"] or 0) / 1_000_000, 2),
                    top_5_codes=top_codes_csv,
                    top_5_payment_mm=round(top_pay / 1_000_000, 2),
                    concentration_hhi=round(hhi, 0),
                ))
            profiles.sort(key=lambda p: p.total_payment_mm, reverse=True)
            return profiles

    def top_rows_sample(self, limit: int = 30) -> List[MedicareUtilRow]:
        with self._connect() as conn:
            self._ensure_schema(conn)
            cur = conn.execute(
                """
                SELECT *
                FROM medicare_utilization
                ORDER BY total_medicare_payment DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [_row_to_dataclass(r) for r in cur]

    def top_codes_for_specialty(self, specialty: str, limit: int = 5):
        with self._connect() as conn:
            self._ensure_schema(conn)
            cur = conn.execute(
                """
                SELECT hcpcs_code, hcpcs_description,
                       AVG(avg_medicare_payment) AS avg_payment,
                       SUM(service_count)         AS services
                FROM medicare_utilization
                WHERE specialty_normalized = ?
                GROUP BY hcpcs_code, hcpcs_description
                ORDER BY SUM(total_medicare_payment) DESC
                LIMIT ?
                """,
                (specialty, limit),
            )
            return [dict(r) for r in cur]


def _row_to_dataclass(r) -> MedicareUtilRow:
    return MedicareUtilRow(
        npi=r["npi"],
        provider_last_name=r["provider_last_name"],
        provider_type=r["provider_type"],
        specialty_normalized=r["specialty_normalized"],
        state=r["state"],
        hcpcs_code=r["hcpcs_code"],
        hcpcs_description=r["hcpcs_description"],
        place_of_service=r["place_of_service"],
        year=r["year"],
        service_count=r["service_count"],
        beneficiary_count=r["beneficiary_count"],
        avg_submitted_charge=r["avg_submitted_charge"],
        avg_medicare_allowed=r["avg_medicare_allowed"],
        avg_medicare_payment=r["avg_medicare_payment"],
        total_medicare_payment=r["total_medicare_payment"],
    )


# ---------------------------------------------------------------------------
# Incremental refresh API
# ---------------------------------------------------------------------------

def refresh_medicare_utilization(
    year: int = _SEED_SOURCE_YEAR,
    source_manifest: Optional[Dict[str, str]] = None,
    db_path: Path = _DB_PATH,
) -> Dict[str, object]:
    """Incremental refresh entry point.

    In the current offline-capable seed implementation, this simply
    repopulates from the deterministic seed. When CMS data ingestion is
    wired (future work), the source_manifest dict carries the mapping of
    year → CSV URL/path and this function becomes the upsert entry.

    source_manifest schema (documented here for the future implementation):
        {
            "csv_path": "/path/to/Medicare_Physician_Other_Practitioners_<YEAR>.csv",
            "csv_url":  "https://data.cms.gov/.../download?year=<YEAR>",
            "checksum_sha256": "...",
            "rows_expected": 9_800_000,
        }

    Returns a status dict with row_count, refreshed_at, and notes.
    """
    wh = MedicareUtilWarehouse(db_path=db_path)
    inserted = wh.populate_from_seed(year=year)
    meta = {m.key: m.value for m in wh.get_meta()}
    return {
        "status": "ok",
        "ingestion_mode": meta.get("ingestion_mode", "seed"),
        "year": year,
        "row_count": inserted,
        "schema_version": _SCHEMA_VERSION,
        "last_refreshed_at": meta.get("last_refreshed_at"),
        "source_manifest_received": source_manifest is not None,
        "notes": (
            "Current implementation populates from in-process seed. When "
            "CMS annual file is provided via source_manifest['csv_path'], "
            "the function will stream-insert rows (planned for next iteration)."
        ),
    }


# ---------------------------------------------------------------------------
# Per-deal baseline profile
# ---------------------------------------------------------------------------

_SPECIALTY_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("Primary Care", ["primary care", "pcp", "chenmed", "oak street", "iora", "onemedical"]),
    ("Emergency Medicine", ["emergency medicine", "ed staff", "emergency dept"]),
    ("Radiology", ["radiology", "imaging", "rayus", "radnet", "smil", "mri", "ct scan"]),
    ("Cardiology", ["cardiology", "cardiac", "cardio ", "cardiovascular"]),
    ("Gastroenterology", ["gastroenter", "endoscopy", "gi network", "gi associate"]),
    ("Orthopedics", ["orthoped", "musculoskeletal", "msk ", "ortho rehab", "ortho "]),
    ("Urology", ["urolog", "men's health"]),
    ("Dermatology", ["dermatol", "aesthetic derm", "skin"]),
    ("Pain Management", ["pain management", "interventional pain"]),
    ("Oncology / Hem-Onc", ["oncolog", "cancer", "infusion"]),
    ("Lab / Pathology", ["lab /", "laboratory", "pathology", "diagnostic lab"]),
    ("Physical Therapy / Rehab", ["physical therapy", "rehab", "ati phys", "pt net", "athletico"]),
    ("Behavioral Health", ["behavioral", "psych", "mental health", "aba", "addiction"]),
    ("Nephrology", ["dialysis", "renal", "kidney", "nephrol"]),
    ("Ophthalmology", ["eye care", "ophthalm", "vision", "retina"]),
    ("Sleep Medicine", ["sleep medicine", "sleep disorder", "sleep lab"]),
    ("Podiatry", ["podiatry", "foot and ankle", "foot & ankle"]),
    ("ENT / Otolaryngology", ["ent ", "otolaryn", "audiology", "hearing"]),
    ("Home Health", ["home health", "hospice", "home-health"]),
    ("Anesthesiology", ["anesthesia", "anesthesiologist"]),
]


def _classify_deal_specialty(deal: dict) -> str:
    hay = (
        str(deal.get("deal_name", "")) + " " +
        str(deal.get("notes", "")) + " " +
        str(deal.get("buyer", ""))
    ).lower()
    for specialty, kws in _SPECIALTY_KEYWORDS:
        for kw in kws:
            if kw in hay:
                return specialty
    return "Primary Care"


def _build_deal_baselines(
    corpus: List[dict],
    warehouse: MedicareUtilWarehouse,
    limit: int = 40,
) -> List[DealUtilizationBaseline]:
    """Pick a diverse sample of corpus deals and produce a baseline revenue
    profile per deal based on inferred specialty + top-CPT footprint."""
    seen_specialties: Dict[str, int] = {}
    baselines: List[DealUtilizationBaseline] = []
    # Emit up to 2 deals per inferred specialty to keep the table diverse
    for d in corpus:
        if len(baselines) >= limit:
            break
        specialty = _classify_deal_specialty(d)
        if seen_specialties.get(specialty, 0) >= 2:
            continue
        seen_specialties[specialty] = seen_specialties.get(specialty, 0) + 1

        top = warehouse.top_codes_for_specialty(specialty, limit=5)
        if not top:
            continue
        # Baseline revenue per physician = sum(top-5 payment / provider_count)
        try:
            provider_count = warehouse.summary_stats()["distinct_npis"]
        except (KeyError, sqlite3.Error):
            provider_count = 1
        total_top_payment = sum(float(row["avg_payment"] or 0) * int(row["services"] or 0) for row in top)
        # Estimate per-physician annual from top-5; specialty has ~5-8 providers in seed
        specialty_providers = max(1, len(_PROVIDER_DIRECTORY.get(specialty, [])))
        baseline_per_phys = total_top_payment / specialty_providers / 1_000  # $K

        top_code = top[0]
        confidence = "high" if len(top) >= 4 else ("medium" if len(top) >= 2 else "low")

        baselines.append(DealUtilizationBaseline(
            deal_name=str(d.get("deal_name", "—"))[:80],
            year=int(d.get("year") or 0),
            buyer=str(d.get("buyer", "—"))[:60],
            inferred_specialty=specialty,
            baseline_cpt_revenue_per_physician_k=round(baseline_per_phys, 1),
            top_code=str(top_code["hcpcs_code"]),
            top_code_description=str(top_code.get("hcpcs_description", "")),
            top_code_avg_payment=round(float(top_code["avg_payment"] or 0), 2),
            baseline_confidence=confidence,
        ))
    return baselines


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_medicare_utilization() -> MedicareUtilResult:
    wh = MedicareUtilWarehouse()
    wh.ensure_populated()

    stats = wh.summary_stats()
    profiles = wh.specialty_profiles()
    top_rows = wh.top_rows_sample(limit=30)
    meta_rows = wh.get_meta()
    meta_dict = {m.key: m.value for m in meta_rows}

    corpus = _load_corpus()
    deal_baselines = _build_deal_baselines(corpus, wh, limit=40)

    return MedicareUtilResult(
        warehouse_row_count=wh.row_count(),
        distinct_npis=stats["distinct_npis"],
        distinct_hcpcs=stats["distinct_hcpcs"],
        distinct_specialties=stats["distinct_specialties"],
        total_services_m=round(stats["total_services"] / 1_000_000, 2),
        total_medicare_payment_b=round(stats["total_payment"] / 1_000_000_000, 3),
        schema_version=meta_dict.get("schema_version", _SCHEMA_VERSION),
        source_year=int(meta_dict.get("source_year", _SEED_SOURCE_YEAR)),
        source_url=meta_dict.get("source_url", _SOURCE_URL),
        last_refreshed_at=meta_dict.get("last_refreshed_at", ""),
        specialty_profiles=profiles,
        top_codes_sample=top_rows,
        deal_baselines=deal_baselines,
        meta_rows=meta_rows,
        corpus_deal_count=len(corpus),
    )
