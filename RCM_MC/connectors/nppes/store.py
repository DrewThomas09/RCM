"""SQLite store for the NPPES canonical dimensions.

Why SQLite (stdlib) rather than duckdb/parquet for the *canonical* tables:
the read patterns the contract cares about — point lookups by NPI, filtered
scans by taxonomy/geography, and the ``/v1/query`` uniform filter/sort/
paginate — are exactly what an indexed relational store serves cheaply,
and SQLite ships in the stdlib so the slice has no hard runtime dependency.
Raw landing still goes to partitioned parquet/NDJSON first (see ``landing``);
this store holds the normalized result.

All writes are idempotent upserts keyed by NPI (or the natural composite
key of each bridge), never blind appends — re-running a load converges.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class NppesStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout = 5000")
        con.execute("PRAGMA journal_mode = WAL")
        try:
            yield con
        finally:
            con.close()

    def init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(_SCHEMA)
            con.commit()


_SCHEMA = """
-- ── dim_provider : the provider (NPI) dimension we own ──────────────
CREATE TABLE IF NOT EXISTS dim_provider (
    npi TEXT PRIMARY KEY,
    entity_type INTEGER,                 -- 1=individual, 2=organization
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    name_prefix TEXT,
    name_suffix TEXT,
    credential TEXT,
    organization_name TEXT,              -- legal business name (Type 2)
    authorized_official_last_name TEXT,  -- Type 2
    authorized_official_first_name TEXT,
    authorized_official_title TEXT,
    authorized_official_phone TEXT,
    sole_proprietor TEXT,                -- 'Y'/'N'/'' (Type 1)
    enumeration_date TEXT,
    last_update_date TEXT,
    deactivation_date TEXT,
    reactivation_date TEXT,
    status TEXT,                         -- 'active' | 'deactivated'
    replacement_npi TEXT,
    nppes_last_updated TEXT,
    monthly_version TEXT,                -- provenance: which base it came from
    source_row TEXT,                     -- 'monthly' | 'weekly' | 'api'
    loaded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dimprov_entity ON dim_provider(entity_type);
CREATE INDEX IF NOT EXISTS idx_dimprov_status ON dim_provider(status);
CREATE INDEX IF NOT EXISTS idx_dimprov_org ON dim_provider(organization_name);
CREATE INDEX IF NOT EXISTS idx_dimprov_last ON dim_provider(last_name);

-- ── bridge_provider_taxonomy : one-to-many, one primary ─────────────
CREATE TABLE IF NOT EXISTS bridge_provider_taxonomy (
    npi TEXT NOT NULL,
    taxonomy_code TEXT NOT NULL,
    primary_flag INTEGER NOT NULL DEFAULT 0,   -- 1 if the primary taxonomy
    license_number TEXT,
    license_state TEXT,
    taxonomy_group TEXT,                       -- NPPES "group" field (rare)
    loaded_at TEXT NOT NULL,
    PRIMARY KEY (npi, taxonomy_code)
);
CREATE INDEX IF NOT EXISTS idx_bpt_code ON bridge_provider_taxonomy(taxonomy_code);
CREATE INDEX IF NOT EXISTS idx_bpt_primary ON bridge_provider_taxonomy(primary_flag);

-- ── dim_taxonomy : NUCC crosswalk we own ────────────────────────────
CREATE TABLE IF NOT EXISTS dim_taxonomy (
    taxonomy_code TEXT PRIMARY KEY,
    grouping TEXT,
    classification TEXT,
    specialization TEXT,
    definition TEXT,
    nucc_notes TEXT,
    display_name TEXT,
    section TEXT,                              -- Individual | Non-Individual
    nucc_version TEXT,
    loaded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_taxo_class ON dim_taxonomy(classification);
CREATE INDEX IF NOT EXISTS idx_taxo_group ON dim_taxonomy(grouping);

-- ── dim_provider_address ────────────────────────────────────────────
-- address_purpose ∈ {practice, mailing, secondary_practice}.
-- fips_county / latitude / longitude are NULL-stubbed pending the Census
-- geocoder (owned by a separate session); columns are wireable.
CREATE TABLE IF NOT EXISTS dim_provider_address (
    npi TEXT NOT NULL,
    address_purpose TEXT NOT NULL,
    address_seq INTEGER NOT NULL DEFAULT 0,    -- 0 primary; >0 for non-primary PLs
    address_line_1 TEXT,
    address_line_2 TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    zip5 TEXT,
    country_code TEXT,
    telephone TEXT,
    fax TEXT,
    fips_county TEXT,                          -- nullable, pending geocode
    latitude REAL,                             -- nullable, pending geocode
    longitude REAL,                            -- nullable, pending geocode
    geocode_status TEXT NOT NULL DEFAULT 'pending',
    loaded_at TEXT NOT NULL,
    PRIMARY KEY (npi, address_purpose, address_seq)
);
CREATE INDEX IF NOT EXISTS idx_addr_state ON dim_provider_address(state);
CREATE INDEX IF NOT EXISTS idx_addr_zip ON dim_provider_address(zip5);
CREATE INDEX IF NOT EXISTS idx_addr_fips ON dim_provider_address(fips_county);

-- ── bridge_provider_affiliation : derived, heuristic ────────────────
CREATE TABLE IF NOT EXISTS bridge_provider_affiliation (
    individual_npi TEXT NOT NULL,
    organization_npi TEXT NOT NULL,
    method TEXT NOT NULL,                      -- which heuristic fired
    confidence REAL NOT NULL,                  -- 0..1
    evidence TEXT,                             -- human-readable rationale
    loaded_at TEXT NOT NULL,
    PRIMARY KEY (individual_npi, organization_npi, method)
);
CREATE INDEX IF NOT EXISTS idx_affil_org ON bridge_provider_affiliation(organization_npi);
CREATE INDEX IF NOT EXISTS idx_affil_conf ON bridge_provider_affiliation(confidence);

-- ── dim_provider_endpoint : FHIR endpoints (optional aux file) ───────
CREATE TABLE IF NOT EXISTS dim_provider_endpoint (
    npi TEXT NOT NULL,
    endpoint_seq INTEGER NOT NULL DEFAULT 0,
    endpoint_type TEXT,
    endpoint_type_description TEXT,
    endpoint TEXT,                             -- the URL
    affiliation TEXT,
    use_description TEXT,
    content_type TEXT,
    loaded_at TEXT NOT NULL,
    PRIMARY KEY (npi, endpoint_seq)
);
CREATE INDEX IF NOT EXISTS idx_endpoint_npi ON dim_provider_endpoint(npi);

-- ── nppes_other_name : Type-2 organization other names (aux file) ────
CREATE TABLE IF NOT EXISTS nppes_other_name (
    npi TEXT NOT NULL,
    other_name_seq INTEGER NOT NULL DEFAULT 0,
    other_name TEXT,
    other_name_type_code TEXT,
    loaded_at TEXT NOT NULL,
    PRIMARY KEY (npi, other_name_seq)
);
CREATE INDEX IF NOT EXISTS idx_othername_npi ON nppes_other_name(npi);

-- ── nppes_invalid_npi : quarantine, never silently dropped ──────────
CREATE TABLE IF NOT EXISTS nppes_invalid_npi (
    raw_npi TEXT,
    reason TEXT,
    source_row TEXT,
    payload TEXT,
    quarantined_at TEXT NOT NULL
);

-- ── nppes_load_state : monthly version + weeklies applied ───────────
CREATE TABLE IF NOT EXISTS nppes_load_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    monthly_version TEXT,
    monthly_header_count INTEGER,
    weeklies_applied TEXT,                     -- JSON list of weekly ids
    last_run_at TEXT,
    notes TEXT
);

-- ── nppes_load_log : append-only per-batch provenance ───────────────
CREATE TABLE IF NOT EXISTS nppes_load_log (
    batch TEXT NOT NULL,
    dataset_id TEXT,
    action TEXT,                               -- monthly|weekly|aux|normalize|dq
    rows_in INTEGER DEFAULT 0,
    rows_inserted INTEGER DEFAULT 0,
    rows_updated INTEGER DEFAULT 0,
    rows_quarantined INTEGER DEFAULT 0,
    notes TEXT,
    logged_at TEXT NOT NULL
);
"""
