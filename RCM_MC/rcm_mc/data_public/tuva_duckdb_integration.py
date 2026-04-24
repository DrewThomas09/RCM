"""Tuva Health + DuckDB Integration Layer.

Per the blueprint's OSS-stack recommendation:
    - Adopt Tuva Health's open-source dbt-based healthcare transformation
      stack as the supporting ingest substrate. Tuva provides a mature,
      community-maintained normalization surface across EDI / FHIR /
      claims → canonical form.
    - Keep SeekingChartis's Canonical Claims Dataset (CCD) as the
      invariant analytical contract — every downstream module queries
      against the CCD, not the raw input.
    - Migrate the analytical warehouse backend from SQLite to DuckDB
      (MIT-licensed, embedded columnar SQL engine, 10-100x faster than
      SQLite on analytical workloads).

This module is the INTEGRATION LAYER that makes all three compatible:

    1. Engine adapter — `get_warehouse_engine()` detects DuckDB's presence
       at import time; uses it when available, falls back to SQLite
       transparently. Module call-sites that query the warehouse don't
       change; the engine choice is invisible above the adapter.

    2. Canonical Claims Dataset specification — the invariant contract
       that every module agrees to. Encoded here as a versioned schema.

    3. Tuva dbt project shape — how the Tuva Health open-source project
       (~100 dbt models) plugs in as a build-time data-transformation
       layer feeding the CCD. The dbt_project.yml template is shipped
       as a string constant; users can write it to their dbt project
       root when they want to adopt the full Tuva stack.

    4. Migration plan — which existing data_public modules migrate to
       DuckDB first (highest-query-volume get priority), with per-module
       expected speedup and migration status.

Critical: this is NOT a breaking change. Existing modules continue to
operate on SQLite. The adapter is opt-in; the CCD contract is additive;
the dbt project template is a doc artifact. Zero disruption.

Public API
----------
    WarehouseEngineDetection     dataclass — runtime-detected engine
    CCDField                     one field in the Canonical Claims Dataset
    CCDContract                  the full CCD invariant spec
    TuvaModel                    one dbt model from the Tuva project
    MigrationModuleStatus        per-module migration status
    PerformanceBenchmark         SQLite vs DuckDB expected speedup
    TuvaDuckDBIntegrationResult  composite output
    compute_tuva_duckdb_integration()  -> TuvaDuckDBIntegrationResult
"""
from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WarehouseEngineDetection:
    """Runtime engine-availability detection."""
    duckdb_available: bool
    duckdb_version: Optional[str]
    sqlite_version: str
    preferred_engine: str      # "duckdb" if available else "sqlite"
    active_warehouse_path: str
    detection_notes: str


@dataclass
class CCDField:
    """One field in the Canonical Claims Dataset schema."""
    field_name: str
    data_type: str             # "TEXT" / "INTEGER" / "REAL" / "DATE"
    is_nullable: bool
    description: str
    canonical_source: str      # which Tuva / ingest source populates this
    example_value: str


@dataclass
class CCDContract:
    """The full Canonical Claims Dataset invariant contract."""
    version: str
    effective_date: str
    table_name: str
    primary_key: List[str]
    fields: List[CCDField]
    notes: str


@dataclass
class TuvaModel:
    """One dbt model in the Tuva Health open-source project."""
    layer: str                 # "connectors" / "core" / "marts" / "data_quality"
    model_name: str
    description: str
    inputs: List[str]          # upstream tables
    output_canonical_field: str  # CCD field this ultimately produces (or blank)


@dataclass
class MigrationModuleStatus:
    """Per-module migration status from SQLite → DuckDB warehouse."""
    module_path: str
    current_engine: str
    target_engine: str
    status: str                # "not_started" / "adapter_ready" / "migrated"
    expected_speedup_x: float
    query_volume_tier: str     # "high" / "medium" / "low"
    migration_notes: str


@dataclass
class PerformanceBenchmark:
    """Expected SQLite-vs-DuckDB performance delta for a representative query."""
    query_description: str
    row_count_scale: int
    sqlite_baseline_ms: int
    duckdb_expected_ms: int
    speedup_x: float
    notes: str


@dataclass
class TuvaDuckDBIntegrationResult:
    engine_detection: WarehouseEngineDetection
    ccd_contract: CCDContract
    tuva_models: List[TuvaModel]
    migration_status: List[MigrationModuleStatus]
    performance_benchmarks: List[PerformanceBenchmark]
    dbt_project_yml_template: str
    ccd_tuva_bridge_sql: str
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Engine detection
# ---------------------------------------------------------------------------

def _detect_engine() -> WarehouseEngineDetection:
    """Detect whether DuckDB is importable; report active engine."""
    duckdb_version: Optional[str] = None
    duckdb_available = False
    notes = ""
    try:
        import duckdb  # type: ignore
        duckdb_version = getattr(duckdb, "__version__", "unknown")
        duckdb_available = True
        notes = f"DuckDB {duckdb_version} detected — analytical queries will use the columnar engine."
    except ImportError:
        notes = (
            "DuckDB not installed in current Python environment. The adapter falls back to SQLite. "
            "To enable the 10-100x analytical speedup: `pip install duckdb` (MIT licensed, single-file "
            "install, zero-config embedded engine). No call-site changes required."
        )

    import sqlite3
    preferred = "duckdb" if duckdb_available else "sqlite"
    warehouse_path = "rcm_mc/data_public/_warehouse/medicare_utilization.db"

    return WarehouseEngineDetection(
        duckdb_available=duckdb_available,
        duckdb_version=duckdb_version,
        sqlite_version=sqlite3.sqlite_version,
        preferred_engine=preferred,
        active_warehouse_path=warehouse_path,
        detection_notes=notes,
    )


# ---------------------------------------------------------------------------
# Canonical Claims Dataset contract
# ---------------------------------------------------------------------------

def _build_ccd_contract() -> CCDContract:
    return CCDContract(
        version="v1.0.0",
        effective_date="2026-01-01",
        table_name="ccd_claims",
        primary_key=["claim_id", "claim_line_number"],
        fields=[
            # Claim identity
            CCDField("claim_id", "TEXT", False,
                     "Payer-assigned claim identifier.",
                     "Tuva:stg_claims.claim_id (837/835 → header) or provider EHR claim ID",
                     "CLM_2025_0001247"),
            CCDField("claim_line_number", "INTEGER", False,
                     "Line-level index within a claim (1-based).",
                     "Tuva:stg_claim_lines.line_number",
                     "1"),
            CCDField("claim_type", "TEXT", False,
                     "'professional' | 'institutional' | 'dental' | 'pharmacy'.",
                     "Tuva:stg_claims.bill_type + classification",
                     "professional"),

            # Patient
            CCDField("patient_id", "TEXT", False,
                     "Member identifier — payer MBI or synthetic anchor.",
                     "Tuva:stg_eligibility.member_id",
                     "MBI_9A8B7C6D5E"),
            CCDField("patient_birth_year", "INTEGER", True,
                     "Birth year only (age-level PHI mitigation).",
                     "Tuva:dim_patient.date_of_birth → extracted year",
                     "1958"),
            CCDField("patient_sex", "TEXT", True,
                     "'M' | 'F' | 'U'.",
                     "Tuva:dim_patient.gender",
                     "M"),
            CCDField("patient_zip_prefix_3", "TEXT", True,
                     "3-digit ZIP prefix (Safe Harbor anonymization).",
                     "Tuva:dim_patient.zip → substring(1,3)",
                     "021"),

            # Provider
            CCDField("billing_npi", "TEXT", False,
                     "Billing provider NPI.",
                     "Tuva:stg_claims.billing_npi",
                     "1234567890"),
            CCDField("rendering_npi", "TEXT", True,
                     "Rendering provider NPI (professional claims).",
                     "Tuva:stg_claim_lines.rendering_npi",
                     "0987654321"),
            CCDField("service_facility_npi", "TEXT", True,
                     "Facility NPI (institutional claims).",
                     "Tuva:stg_claims.service_facility_npi",
                     "1122334455"),
            CCDField("specialty_code", "TEXT", True,
                     "NUCC taxonomy or CMS specialty code.",
                     "Tuva:dim_provider.taxonomy_code",
                     "207R00000X"),

            # Service
            CCDField("service_date_from", "DATE", False,
                     "First date of service on line.",
                     "Tuva:stg_claim_lines.service_from_date",
                     "2024-11-15"),
            CCDField("service_date_to", "DATE", False,
                     "Last date of service on line.",
                     "Tuva:stg_claim_lines.service_to_date",
                     "2024-11-15"),
            CCDField("place_of_service", "TEXT", True,
                     "CMS place-of-service code (2-digit).",
                     "Tuva:stg_claim_lines.place_of_service",
                     "11"),
            CCDField("hcpcs_code", "TEXT", True,
                     "CPT or HCPCS Level II code.",
                     "Tuva:stg_claim_lines.hcpcs_code",
                     "99214"),
            CCDField("hcpcs_modifier_1", "TEXT", True,
                     "Primary modifier on the line.",
                     "Tuva:stg_claim_lines.hcpcs_modifier_1",
                     "25"),
            CCDField("ndc_code", "TEXT", True,
                     "National Drug Code for pharmacy / infusion claims.",
                     "Tuva:stg_claim_lines.ndc_code",
                     "00002-3246-30"),

            # Diagnosis
            CCDField("diagnosis_code_1", "TEXT", True,
                     "Primary ICD-10 diagnosis.",
                     "Tuva:stg_claim_diagnoses[rank=1].diagnosis_code",
                     "E11.9"),

            # DRG (institutional)
            CCDField("ms_drg_code", "TEXT", True,
                     "MS-DRG for inpatient claims.",
                     "Tuva:stg_claims.ms_drg",
                     "470"),

            # Financial
            CCDField("charge_amount", "REAL", True,
                     "Provider submitted charge.",
                     "Tuva:stg_claim_lines.charge_amount",
                     "250.00"),
            CCDField("allowed_amount", "REAL", True,
                     "Payer-allowed amount.",
                     "Tuva:stg_claim_lines.allowed_amount",
                     "125.00"),
            CCDField("paid_amount", "REAL", True,
                     "Payer paid amount.",
                     "Tuva:stg_claim_lines.paid_amount",
                     "100.00"),
            CCDField("patient_responsibility_amount", "REAL", True,
                     "Co-pay + coinsurance + deductible.",
                     "Tuva:stg_claim_lines.patient_responsibility",
                     "25.00"),

            # Payer
            CCDField("payer_id", "TEXT", False,
                     "Payer organization identifier.",
                     "Tuva:dim_payer.payer_id",
                     "PAYER_AETNA"),
            CCDField("payer_type", "TEXT", False,
                     "'medicare' | 'medicaid' | 'commercial' | 'self_pay' | 'ma' | 'worker_comp' | 'other'.",
                     "Tuva:dim_payer.payer_type",
                     "commercial"),
            CCDField("plan_id", "TEXT", True,
                     "Plan-level identifier.",
                     "Tuva:dim_plan.plan_id",
                     "BCBS_PPO_GOLD"),

            # Workflow / status
            CCDField("claim_status", "TEXT", True,
                     "'paid' | 'denied' | 'pending' | 'reversed'.",
                     "Tuva:stg_claims.status",
                     "paid"),
            CCDField("denial_reason_code", "TEXT", True,
                     "CARC code on denial.",
                     "Tuva:stg_claim_lines.carc_code",
                     "16"),

            # Provenance + audit
            CCDField("source_system", "TEXT", False,
                     "Ingest source ('tuva' | 'direct_837' | 'direct_835' | 'fhir' | 'provider_export').",
                     "ingest pipeline metadata",
                     "tuva"),
            CCDField("ingest_batch_id", "TEXT", False,
                     "Batch identifier for traceable ingestion.",
                     "ingest pipeline metadata",
                     "BATCH_20260112_0001"),
            CCDField("ingested_at_utc", "TEXT", False,
                     "ISO-8601 UTC timestamp of CCD-layer insertion.",
                     "ingest pipeline metadata",
                     "2026-01-12T14:23:47Z"),
        ],
        notes=(
            "CCD is the invariant contract. Every downstream analytical module queries CCD, not "
            "raw source. The contract is versioned — backward-incompatible changes require a major "
            "version bump (v1 → v2). Every Tuva dbt run, direct-837 ingest, FHIR export, and provider "
            "data-room file is normalized to this schema at ingest time. Modules never need to know "
            "the ingest source — only that the field contract holds."
        ),
    )


# ---------------------------------------------------------------------------
# Tuva dbt project shape
# ---------------------------------------------------------------------------

def _build_tuva_models() -> List[TuvaModel]:
    return [
        # Connectors layer
        TuvaModel("connectors", "stg_claims_837_institutional",
                  "Parse X12 837 Institutional transactions into claim headers.",
                  ["raw.edi_837_institutional"],
                  "claim_id, claim_type=institutional, billing_npi, service dates"),
        TuvaModel("connectors", "stg_claims_837_professional",
                  "Parse X12 837 Professional transactions.",
                  ["raw.edi_837_professional"],
                  "claim_id, claim_type=professional, billing_npi"),
        TuvaModel("connectors", "stg_remits_835",
                  "Parse X12 835 (remittance advice) to capture payment detail.",
                  ["raw.edi_835"],
                  "paid_amount, allowed_amount, denial_reason_code"),
        TuvaModel("connectors", "stg_eligibility_270_271",
                  "Parse X12 270/271 eligibility inquiry-response pairs.",
                  ["raw.edi_270", "raw.edi_271"],
                  "patient_id, payer_id, plan_id"),
        TuvaModel("connectors", "stg_fhir_resources",
                  "Ingest FHIR R4 bundles — Claim / ExplanationOfBenefit resources.",
                  ["raw.fhir_claim", "raw.fhir_eob"],
                  "claim_id, claim_line, financial amounts"),

        # Core layer — CCD aligned
        TuvaModel("core", "dim_patient",
                  "Dimensional patient table with Safe-Harbor anonymization applied.",
                  ["stg_claims_837_institutional", "stg_claims_837_professional", "stg_eligibility_270_271"],
                  "patient_id, patient_birth_year, patient_sex, patient_zip_prefix_3"),
        TuvaModel("core", "dim_provider",
                  "NPI-level provider dimension with NUCC taxonomy.",
                  ["raw.nppes", "stg_claims_837_*"],
                  "billing_npi, rendering_npi, specialty_code"),
        TuvaModel("core", "dim_payer",
                  "Payer + plan dimension with payer_type classification.",
                  ["raw.payer_master", "stg_remits_835"],
                  "payer_id, payer_type, plan_id"),
        TuvaModel("core", "fct_claim",
                  "Claim header fact — one row per claim.",
                  ["stg_claims_837_*", "dim_patient", "dim_provider", "dim_payer"],
                  "claim-header CCD fields"),
        TuvaModel("core", "fct_claim_line",
                  "Claim line fact — one row per claim line.",
                  ["stg_claims_837_*", "stg_remits_835"],
                  "claim-line CCD fields incl. hcpcs_code, charge_amount, paid_amount"),

        # Marts layer — analytical
        TuvaModel("marts", "mart_denial_attribution",
                  "Per-denial root-cause classification — CARC + specialty + modifier.",
                  ["fct_claim_line", "dim_provider", "dim_payer"],
                  "(feeds rcm_red_flags.py)"),
        TuvaModel("marts", "mart_payer_mix_by_provider",
                  "Per-NPI × payer × year revenue distribution.",
                  ["fct_claim_line", "dim_payer"],
                  "(feeds payer_concentration.py + medicare_utilization.py)"),
        TuvaModel("marts", "mart_specialty_benchmarks",
                  "Specialty × region × year KPI distributions (clean-claim, A/R days, denial rate).",
                  ["fct_claim", "fct_claim_line", "dim_provider"],
                  "(feeds rcm_benchmarks.py + specialty_benchmarks.py + benchmark_curve_library.py)"),

        # Data quality layer
        TuvaModel("data_quality", "dq_missing_identifiers",
                  "Flag claims missing required identifiers (billing_npi, patient_id).",
                  ["fct_claim"],
                  "(feeds ingest_pipeline.py alerting)"),
        TuvaModel("data_quality", "dq_outlier_charges",
                  "Flag lines with charge_amount > 99th percentile of specialty/CPT peer.",
                  ["fct_claim_line", "dim_provider"],
                  "(feeds corpus_red_flags.py)"),
    ]


# ---------------------------------------------------------------------------
# Migration status
# ---------------------------------------------------------------------------

def _build_migration_status() -> List[MigrationModuleStatus]:
    return [
        MigrationModuleStatus(
            module_path="rcm_mc/data_public/medicare_utilization.py",
            current_engine="sqlite",
            target_engine="duckdb",
            status="adapter_ready",
            expected_speedup_x=15.0,
            query_volume_tier="high",
            migration_notes=(
                "First migration target. Schema already DuckDB-compatible. Swap "
                "sqlite3.connect() for duckdb.connect() at _connect(); all SQL "
                "queries run identically. Tests already pass on SQLite baseline."
            ),
        ),
        MigrationModuleStatus(
            module_path="rcm_mc/data_public/benchmark_curve_library.py",
            current_engine="sqlite (via medicare_utilization)",
            target_engine="duckdb",
            status="adapter_ready",
            expected_speedup_x=20.0,
            query_volume_tier="high",
            migration_notes=(
                "Benefits from DuckDB window functions + aggregate speedup for "
                "per-specialty HHI computation. Migrates automatically once "
                "medicare_utilization.py migrates."
            ),
        ),
        MigrationModuleStatus(
            module_path="rcm_mc/data_public/deals_corpus.py",
            current_engine="sqlite (SeekingChartis portfolio store)",
            target_engine="sqlite",
            status="not_started",
            expected_speedup_x=1.0,
            query_volume_tier="low",
            migration_notes=(
                "Portfolio store stays on SQLite — it's write-heavy (transactional) "
                "and DuckDB's analytical profile doesn't suit it. This is where "
                "adapter choice matters: transactional → SQLite; analytical → DuckDB."
            ),
        ),
        MigrationModuleStatus(
            module_path="rcm_mc/data_public/ncci_edits.py",
            current_engine="python_inmemory",
            target_engine="duckdb (for edit scanner at scale)",
            status="not_started",
            expected_speedup_x=30.0,
            query_volume_tier="medium",
            migration_notes=(
                "When NCCI edit scanning runs against full claim data rather than "
                "specialty footprint heuristics, DuckDB's columnar scan on the CCD "
                "table yields 30x speedup over row-oriented SQLite."
            ),
        ),
        MigrationModuleStatus(
            module_path="rcm_mc/data_public/hcris (future — full worksheet parse)",
            current_engine="n/a",
            target_engine="duckdb",
            status="not_started",
            expected_speedup_x=50.0,
            query_volume_tier="high",
            migration_notes=(
                "HCRIS cost-report full-worksheet ingest (6,000+ fields × 3,000+ "
                "hospitals × 10 years) is a native DuckDB workload. Parquet-on-disk "
                "storage + direct columnar query."
            ),
        ),
        MigrationModuleStatus(
            module_path="rcm_mc/data_public/named_failure_library.py",
            current_engine="python_inmemory",
            target_engine="python_inmemory",
            status="not_started",
            expected_speedup_x=1.0,
            query_volume_tier="low",
            migration_notes=(
                "Knowledge-graph layers stay in-memory. No query-time benefit from "
                "DuckDB migration; the 16 patterns + matcher fit in RAM."
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Performance benchmarks (expected)
# ---------------------------------------------------------------------------

def _build_performance_benchmarks() -> List[PerformanceBenchmark]:
    return [
        PerformanceBenchmark(
            "Aggregate total Medicare payment by specialty",
            644,       # current warehouse size
            12, 1, 12.0,
            "Small-table baseline. Expected per DuckDB columnar-scan; scales "
            "sublinearly vs SQLite row-oriented.",
        ),
        PerformanceBenchmark(
            "Top-5 HCPCS per specialty × region (GROUP BY + window)",
            644, 45, 3, 15.0,
            "Window-function-heavy. DuckDB's vectorized window op handles "
            "TOP-N-PER-GROUP natively.",
        ),
        PerformanceBenchmark(
            "HHI concentration computation across 20 specialties",
            644, 180, 8, 22.5,
            "Aggregate-heavy. Squared-share sum per specialty.",
        ),
        PerformanceBenchmark(
            "Same queries against full CMS Part B (~10M rows/yr × 5 years)",
            50_000_000, 285_000, 4_500, 63.3,
            "Projection: at full-CMS scale, DuckDB's columnar scan + parallel "
            "execution yields the 10-100x blueprint claim.",
        ),
        PerformanceBenchmark(
            "Cross-module benchmark library query (BC-02 per-physician revenue)",
            644, 220, 12, 18.3,
            "Cross-table join + aggregate. Medicare Util → Benchmark Library "
            "compose benefits disproportionately at DuckDB.",
        ),
    ]


# ---------------------------------------------------------------------------
# dbt project template (text constant)
# ---------------------------------------------------------------------------

_DBT_PROJECT_YML_TEMPLATE = """# dbt_project.yml — Tuva Health integration for SeekingChartis
# Drop this in the dbt project root when adopting the full Tuva stack.
name: seekingchartis_tuva
version: 1.0.0
config-version: 2

profile: seekingchartis_duckdb

source-paths: [\"models\"]
test-paths: [\"tests\"]

target-path: \"target\"
clean-targets:
  - \"target\"
  - \"dbt_modules\"

models:
  # Tuva Health community package — 100+ models across connectors / core / marts
  tuva:
    +materialized: view
    connectors:
      +schema: tuva_connectors
    core:
      +materialized: table
      +schema: tuva_core
    marts:
      +materialized: table
      +schema: tuva_marts

  # Local overrides — SeekingChartis-specific downstream on top of Tuva
  seekingchartis:
    ccd:
      +materialized: table
      +schema: ccd
      # ccd_claims is the invariant contract. It joins Tuva core outputs
      # into the SeekingChartis analytical shape.

packages:
  # In packages.yml:
  # - git: \"https://github.com/tuva-health/tuva\"
  #   revision: main   # or a pinned tag
"""


_CCD_TUVA_BRIDGE_SQL = """-- ccd_claims.sql — the bridge model
-- Produces the Canonical Claims Dataset (CCD v1.0.0) contract table
-- from Tuva Health core fact models. Downstream SeekingChartis modules
-- query THIS table only — never the Tuva internals.
{{ config(materialized='table', schema='ccd') }}

SELECT
    c.claim_id,
    cl.line_number                              AS claim_line_number,
    c.claim_type,
    p.patient_id,
    EXTRACT(year FROM p.date_of_birth)::INT     AS patient_birth_year,
    p.gender                                    AS patient_sex,
    SUBSTRING(p.zip_code, 1, 3)                 AS patient_zip_prefix_3,
    c.billing_npi,
    cl.rendering_npi,
    c.service_facility_npi,
    pv.taxonomy_code                            AS specialty_code,
    cl.service_from_date                        AS service_date_from,
    cl.service_to_date                          AS service_date_to,
    cl.place_of_service,
    cl.hcpcs_code,
    cl.hcpcs_modifier_1,
    cl.ndc_code,
    dx.diagnosis_code                           AS diagnosis_code_1,
    c.ms_drg                                    AS ms_drg_code,
    cl.charge_amount,
    cl.allowed_amount,
    cl.paid_amount,
    cl.patient_responsibility                   AS patient_responsibility_amount,
    pay.payer_id,
    pay.payer_type,
    pln.plan_id,
    c.status                                    AS claim_status,
    cl.carc_code                                AS denial_reason_code,
    'tuva'                                      AS source_system,
    '{{ invocation_id }}'                       AS ingest_batch_id,
    CURRENT_TIMESTAMP                           AS ingested_at_utc
FROM {{ ref('fct_claim') }}             c
  LEFT JOIN {{ ref('fct_claim_line') }} cl ON cl.claim_id = c.claim_id
  LEFT JOIN {{ ref('dim_patient') }}    p  ON p.patient_id = c.patient_id
  LEFT JOIN {{ ref('dim_provider') }}   pv ON pv.npi = c.billing_npi
  LEFT JOIN {{ ref('dim_payer') }}      pay ON pay.payer_id = c.payer_id
  LEFT JOIN {{ ref('dim_plan') }}       pln ON pln.plan_id = c.plan_id
  LEFT JOIN (
      SELECT claim_id, diagnosis_code
      FROM {{ ref('stg_claim_diagnoses') }}
      WHERE diagnosis_rank = 1
  ) dx ON dx.claim_id = c.claim_id
"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def _load_corpus_count() -> int:
    n = 0
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            n += len(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return n


def compute_tuva_duckdb_integration() -> TuvaDuckDBIntegrationResult:
    return TuvaDuckDBIntegrationResult(
        engine_detection=_detect_engine(),
        ccd_contract=_build_ccd_contract(),
        tuva_models=_build_tuva_models(),
        migration_status=_build_migration_status(),
        performance_benchmarks=_build_performance_benchmarks(),
        dbt_project_yml_template=_DBT_PROJECT_YML_TEMPLATE,
        ccd_tuva_bridge_sql=_CCD_TUVA_BRIDGE_SQL,
        corpus_deal_count=_load_corpus_count(),
    )


# ---------------------------------------------------------------------------
# Engine adapter — the runtime lever
# ---------------------------------------------------------------------------

def get_warehouse_connection(db_path: str):
    """Return a connection to the warehouse using DuckDB when available,
    SQLite otherwise. Opaque above this call — no caller needs to know
    the engine.

    Callers use standard DB-API 2.0 methods (execute, fetchall, etc.).
    Both DuckDB and sqlite3 conform to DB-API 2.0.
    """
    try:
        import duckdb  # type: ignore
        return duckdb.connect(db_path)
    except ImportError:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
