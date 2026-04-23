"""Map a :class:`CanonicalClaimsDataset` into the Tuva Input Layer
schema so a partner who wants the richer claims marts (CCSR, HCC,
financial_pmpm, chronic conditions, readmissions) can run the
vendored Tuva dbt project on top of our CCD.

Tuva is vendored locally at
``Coding Projects/ChartisDrewIntel-main/`` (Apache 2.0, unmodified
content of ``the_tuva_project`` v0.17.1). This bridge does NOT pull
Tuva from GitHub — if the vendored path exists, we use it; otherwise
the functions raise with a clear error pointing at the expected
location.

What this module does:

- ``ccd_to_tuva_input_layer_arrow(ccd)`` — returns a
  ``{table_name: pyarrow.Table}`` map for the three tables Tuva's
  input layer expects (``medical_claim``, ``pharmacy_claim``,
  ``eligibility``), with column names + types matching Tuva's
  contract. No external dependencies beyond pyarrow.
- ``write_tuva_input_layer_duckdb(ccd, duckdb_path)`` — write those
  tables into an existing DuckDB file's ``raw_data`` schema. Partners
  who want the full Tuva run then point dbt at this DuckDB.
- ``vendored_tuva_path()`` — returns the Path to the vendored Tuva
  project, or None if it isn't on disk.

What this module does NOT do:

- Execute ``dbt deps`` / ``dbt build``. That requires dbt-core +
  dbt-duckdb which are NOT in the base ``rcm_mc`` install footprint
  (see ``pyproject.toml`` ``[diligence]`` optional extra — currently
  deprecated; use session-1's ``rcm_mc_diligence`` package if you
  need the full dbt invocation).
- Mint Tuva's seed tables. Seeds live in Tuva's S3 bucket and are
  installed by ``dbt deps``.

When the user runs the Phase 2 benchmarks page, we intentionally do
NOT invoke Tuva — KPI engine outputs are sufficient for the
scorecard. The bridge is for partners who want to drill into CCSR
condition categories, HCC risk scores, or readmission flags after
Phase 2 numbers are in hand.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .ccd import CanonicalClaim, CanonicalClaimsDataset


# The vendored Tuva project's on-disk location, computed from this
# file's path so it resolves consistently whether the package is
# installed in dev mode or via wheel.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_VENDORED_TUVA_DIR = _REPO_ROOT / "ChartisDrewIntel-main"


def vendored_tuva_path() -> Optional[Path]:
    """Return the vendored Tuva project path, or None if not on disk.

    Partners installing ``rcm_mc`` as a wheel won't get the vendored
    copy — that's expected. The bridge functions still work in
    arrow-output mode; only the ``write_tuva_input_layer_duckdb``
    pathway requires the vendored tree.
    """
    if _VENDORED_TUVA_DIR.exists() and (_VENDORED_TUVA_DIR / "dbt_project.yml").exists():
        return _VENDORED_TUVA_DIR
    return None


# ── Input Layer contract ────────────────────────────────────────────

# Tuva v0.17.1 Input Layer column list for the three tables Phase 1
# populates. Pulled from
# github.com/tuva-health/tuva/blob/v0.17.1/models/input_layer/.
# Kept here as a module-level constant so the mapping is explicit and
# reviewable without opening the vendored project.
TUVA_MEDICAL_CLAIM_COLUMNS = [
    "claim_id", "claim_line_number", "claim_type",
    "person_id", "member_id", "payer", "plan",
    "claim_start_date", "claim_end_date",
    "claim_line_start_date", "claim_line_end_date",
    "admission_date", "discharge_date",
    "admit_source_code", "admit_type_code",
    "discharge_disposition_code",
    "place_of_service_code", "bill_type_code",
    "drg_code_type", "drg_code",
    "revenue_center_code", "service_unit_quantity",
    "hcpcs_code", "hcpcs_modifier_1", "hcpcs_modifier_2",
    "hcpcs_modifier_3", "hcpcs_modifier_4", "hcpcs_modifier_5",
    "rendering_npi", "rendering_tin", "billing_npi", "billing_tin",
    "facility_npi",
    "paid_date", "paid_amount", "allowed_amount", "charge_amount",
    "coinsurance_amount", "copayment_amount", "deductible_amount",
    "total_cost_amount",
    "diagnosis_code_type",
    "diagnosis_code_1", "diagnosis_code_2", "diagnosis_code_3",
    "diagnosis_code_4", "diagnosis_code_5",
    "in_network_flag", "data_source", "file_name", "file_date",
    "ingest_datetime",
]
TUVA_PHARMACY_CLAIM_COLUMNS = [
    "claim_id", "claim_line_number", "person_id", "member_id",
    "payer", "plan",
    "prescribing_provider_npi", "dispensing_provider_npi",
    "dispensing_date",
    "ndc_code", "quantity", "days_supply", "refills",
    "paid_date", "paid_amount", "allowed_amount", "charge_amount",
    "coinsurance_amount", "copayment_amount", "deductible_amount",
    "in_network_flag", "data_source", "file_name", "file_date",
    "ingest_datetime",
]
TUVA_ELIGIBILITY_COLUMNS = [
    "person_id", "member_id", "subscriber_id",
    "gender", "race", "birth_date", "death_date", "death_flag",
    "enrollment_start_date", "enrollment_end_date",
    "payer", "payer_type", "plan",
    "original_reason_entitlement_code", "dual_status_code",
    "medicare_status_code", "enrollment_status",
    "first_name", "last_name",
    "data_source", "file_name", "file_date", "ingest_datetime",
]


# ── Conversion functions ────────────────────────────────────────────

def ccd_to_tuva_input_layer_arrow(
    ccd: CanonicalClaimsDataset,
) -> Dict[str, Any]:
    """Convert a CCD into pyarrow tables matching Tuva's input layer.

    Returns a dict keyed by Tuva table name with ``pyarrow.Table``
    values. Missing columns get null-typed arrays so Tuva's
    ``input_layer__*`` models materialise cleanly with nulls where
    the CCD doesn't carry the signal (e.g., DRG on an outpatient-only
    export).
    """
    import pyarrow as pa

    medical_rows: list[dict] = []
    for c in ccd.claims:
        medical_rows.append(_claim_to_tuva_medical_row(c))
    # If no claims, emit an empty-but-typed table.
    med_table = _to_arrow_table(medical_rows, TUVA_MEDICAL_CLAIM_COLUMNS)

    # Phase 1 CCD doesn't yet distinguish pharmacy — keep an empty
    # scaffold. When the ingester grows pharmacy support, populate
    # from ``c.ndc_code`` and related fields here.
    pharm_table = _to_arrow_table([], TUVA_PHARMACY_CLAIM_COLUMNS)

    # Eligibility: one row per distinct patient_id that has a DOB or
    # enrollment_start_date. Partners without eligibility in the CCD
    # get an empty-but-typed table.
    elig_rows: list[dict] = []
    seen: set[str] = set()
    for c in ccd.claims:
        if not c.patient_id or c.patient_id in seen:
            continue
        seen.add(c.patient_id)
        elig_rows.append(_claim_to_tuva_eligibility_row(c))
    elig_table = _to_arrow_table(elig_rows, TUVA_ELIGIBILITY_COLUMNS)

    return {
        "medical_claim": med_table,
        "pharmacy_claim": pharm_table,
        "eligibility": elig_table,
    }


def write_tuva_input_layer_duckdb(
    ccd: CanonicalClaimsDataset, duckdb_path: Path | str,
) -> Dict[str, int]:
    """Write the three Tuva input-layer tables into ``duckdb_path``'s
    ``raw_data`` schema. Returns a ``{table_name: row_count}`` dict.

    The target DuckDB file is created if missing. Existing tables
    with the same names are dropped and recreated (idempotent).
    Partners point dbt at this DuckDB to run the vendored Tuva
    project end-to-end.

    This is the only function in the module that requires ``duckdb``
    to be importable.
    """
    import duckdb

    duckdb_path = Path(duckdb_path)
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    tables = ccd_to_tuva_input_layer_arrow(ccd)

    row_counts: Dict[str, int] = {}
    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute("create schema if not exists raw_data")
        for name, arrow_tbl in tables.items():
            alias = f"__tmp_{name}"
            con.register(alias, arrow_tbl)
            try:
                con.execute(f'drop table if exists raw_data."{name}"')
                con.execute(
                    f'create table raw_data."{name}" as select * from {alias}'
                )
                row_counts[name] = int(
                    con.execute(f'select count(*) from raw_data."{name}"').fetchone()[0]
                )
            finally:
                con.unregister(alias)
    finally:
        con.close()
    return row_counts


# ── Per-row mapping ────────────────────────────────────────────────

def _claim_to_tuva_medical_row(c: CanonicalClaim) -> dict:
    """Map one :class:`CanonicalClaim` into Tuva medical_claim shape."""
    mods = list(c.cpt_modifiers) + [None] * 5
    secondary_dx = list(c.icd10_secondary) + [None] * 4
    return {
        "claim_id": c.claim_id,
        "claim_line_number": c.line_number,
        "claim_type": "institutional" if c.bill_type else "professional",
        "person_id": c.patient_id,
        "member_id": c.patient_id,
        "payer": c.payer_canonical or c.payer_raw,
        "plan": None,
        "claim_start_date": c.service_date_from,
        "claim_end_date": c.service_date_to or c.service_date_from,
        "claim_line_start_date": c.service_date_from,
        "claim_line_end_date": c.service_date_to or c.service_date_from,
        "admission_date": None,
        "discharge_date": None,
        "admit_source_code": None,
        "admit_type_code": None,
        "discharge_disposition_code": None,
        "place_of_service_code": c.place_of_service,
        "bill_type_code": c.bill_type,
        "drg_code_type": "ms-drg" if c.drg else None,
        "drg_code": c.drg,
        "revenue_center_code": None,
        "service_unit_quantity": 1,
        "hcpcs_code": c.cpt_code,
        "hcpcs_modifier_1": mods[0],
        "hcpcs_modifier_2": mods[1],
        "hcpcs_modifier_3": mods[2],
        "hcpcs_modifier_4": mods[3],
        "hcpcs_modifier_5": mods[4],
        "rendering_npi": c.rendering_npi,
        "rendering_tin": None,
        "billing_npi": c.billing_npi,
        "billing_tin": None,
        "facility_npi": None,
        "paid_date": c.paid_date,
        "paid_amount": c.paid_amount,
        "allowed_amount": c.allowed_amount,
        "charge_amount": c.charge_amount,
        "coinsurance_amount": None,
        "copayment_amount": None,
        "deductible_amount": None,
        "total_cost_amount": c.charge_amount,
        "diagnosis_code_type": "icd-10-cm" if c.icd10_primary else None,
        "diagnosis_code_1": c.icd10_primary,
        "diagnosis_code_2": secondary_dx[0],
        "diagnosis_code_3": secondary_dx[1],
        "diagnosis_code_4": secondary_dx[2],
        "diagnosis_code_5": secondary_dx[3],
        "in_network_flag": None,
        "data_source": c.source_system,
        "file_name": c.source_file,
        "file_date": None,
        "ingest_datetime": c.ingest_datetime,
    }


def _claim_to_tuva_eligibility_row(c: CanonicalClaim) -> dict:
    return {
        "person_id": c.patient_id,
        "member_id": c.patient_id,
        "subscriber_id": c.patient_id,
        "gender": c.patient_sex,
        "race": None,
        "birth_date": c.patient_dob,
        "death_date": None,
        "death_flag": False,
        "enrollment_start_date": c.service_date_from,
        "enrollment_end_date": None,
        "payer": c.payer_canonical or c.payer_raw,
        "payer_type": c.payer_class.value,
        "plan": None,
        "original_reason_entitlement_code": None,
        "dual_status_code": None,
        "medicare_status_code": None,
        "enrollment_status": "active",
        "first_name": None,
        "last_name": None,
        "data_source": c.source_system,
        "file_name": c.source_file,
        "file_date": None,
        "ingest_datetime": c.ingest_datetime,
    }


def _to_arrow_table(rows: list[dict], columns: list[str]):
    """Build a ``pyarrow.Table`` with every column in ``columns``
    present. Missing columns get a null column; extras are dropped.
    Preserves column order for stable downstream hashing.
    """
    import pyarrow as pa

    if not rows:
        # Use a single-null row then slice it out — the cheapest way
        # to get a schema-correct empty table without hand-writing
        # each column's arrow type.
        placeholder = {c: None for c in columns}
        tbl = pa.Table.from_pylist([placeholder], schema=None)
        return tbl.slice(0, 0)

    rows_aligned = [
        {c: r.get(c) for c in columns} for r in rows
    ]
    return pa.Table.from_pylist(rows_aligned)
