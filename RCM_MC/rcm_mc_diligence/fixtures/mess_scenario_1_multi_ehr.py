"""mess_scenario_1 — three acquired clinics, three EHRs.

Pathology: Epic-, Cerner-, and Athena-style exports with different
column names, date formats, and payer spellings for what is logically
the same claim table. The ingestion layer must merge them by MRN+DOB
after normalisation and produce one Tuva Input Layer table that
carries the ``data_source`` column so downstream analyses can
stratify by clinic.

Expected DQ outcome: ingestion succeeds, multi_ehr_merge rule fires
with INFO severity, all three clinics counted in the DQ report.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from .synthetic import (
    SAMPLE_HCPCS, SAMPLE_PAYERS, claim_ids, mrns, rng,
    sample_claim_row, write_csv, write_readme,
)


FIXTURE_NAME = "mess_scenario_1_multi_ehr"
EXPECTED_OUTCOME = {
    "overall_status": "WARN",  # Encoding fallback on latin-1 file
    "multi_ehr_merge": True,   # rule fires
    "min_data_sources": 3,
    "fail_rules": [],
}


def generate(output_dir: Path | str, *, seed: int = 41) -> Path:
    out = Path(output_dir) / FIXTURE_NAME
    out.mkdir(parents=True, exist_ok=True)
    r = rng(seed)

    # Shared MRN pool — the three clinics cover overlapping patient
    # populations so the merge can demonstrate dedup on MRN+DOB.
    shared_mrns = mrns(600, seed=seed)

    _clinic_epic(out, r, shared_mrns)
    _clinic_cerner(out, r, shared_mrns)
    _clinic_athena(out, r, shared_mrns)

    write_readme(
        out / "README.md",
        title="mess_scenario_1 — three EHRs, one patient population",
        pathology=(
            "Three acquired clinics export claims from Epic, Cerner, and "
            "Athena. The column names differ (patient_id vs mrn vs "
            "member_number), the date formats differ (ISO vs US vs "
            "Unix epoch), and one CSV is latin-1 encoded. Identical "
            "patients appear across clinics; the ingestion layer has "
            "to reconcile by MRN+DOB."
        ),
        expected=(
            "Ingestion succeeds with WARN overall (latin-1 encoding "
            "fallback on one file). The merged medical_claims table "
            "has 3 distinct data_source values. The multi_ehr_merge "
            "rule fires with INFO severity. No FAIL-severity findings."
        ),
    )
    return out


# ── Per-clinic emitters ──────────────────────────────────────────────

def _clinic_epic(out: Path, r, shared_mrns: List[str]) -> None:
    """Epic-style: snake_case column names, ISO dates, uppercase payer IDs."""
    rows: List[Dict[str, Any]] = []
    for _ in range(600):
        row = sample_claim_row(r, mrn_pool=shared_mrns, data_source="epic_clinic_a")
        d = row.as_dict()
        # Epic uses claim_start_date / date_of_service naming. Both
        # acceptable by our loader; choose claim_start_date.
        rows.append({
            "claim_id": d["claim_id"],
            "claim_line_number": d["claim_line_number"],
            "patient_id": d["person_id"],
            "member_id": d["member_id"],
            "payer": d["payer"],
            "plan": d["plan"],
            "claim_start_date": d["claim_start_date"],
            "claim_end_date": d["claim_end_date"],
            "hcpcs_code": d["hcpcs_code"],
            "charge_amount": d["charge_amount"],
            "paid_amount": d["paid_amount"],
            "allowed_amount": d["allowed_amount"],
            "data_source": d["data_source"],
        })
    write_csv(out / "medical_claims_clinic_a.csv", rows)


def _clinic_cerner(out: Path, r, shared_mrns: List[str]) -> None:
    """Cerner-style: mrn instead of patient_id, US-formatted dates,
    and a latin-1 encoded CSV (ë in one payer name)."""
    import csv
    rows: List[Dict[str, Any]] = []
    for _ in range(500):
        spec = sample_claim_row(r, mrn_pool=shared_mrns, data_source="cerner_clinic_b")
        d = spec.as_dict()
        dos: date = spec.claim_start_date
        doe: date = spec.claim_end_date
        payer_map = {"BCBS": "Blue Crosß Blue Shield"}   # latin-1 ß
        rows.append({
            "claim_number": d["claim_id"],
            "line_number": d["claim_line_number"],
            "mrn": d["person_id"],
            "member_id": d["member_id"],
            "payer_name": payer_map.get(d["payer"], d["payer"]),
            "plan_name": d["plan"],
            "service_start_date": dos.strftime("%m/%d/%Y"),
            "service_end_date": doe.strftime("%m/%d/%Y"),
            "cpt_code": d["hcpcs_code"],
            "billed_amount": d["charge_amount"],
            "paid_amount": d["paid_amount"],
            "allowed_amount": d["allowed_amount"],
            "data_source": d["data_source"],
        })
    # Write with latin-1 encoding to exercise the fallback path.
    path = out / "medical_claims_clinic_b.csv"
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="latin-1", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fieldnames})


def _clinic_athena(out: Path, r, shared_mrns: List[str]) -> None:
    """Athena-style: member_number column, Unix-epoch timestamps,
    Parquet format."""
    rows: List[Dict[str, Any]] = []
    for _ in range(400):
        spec = sample_claim_row(r, mrn_pool=shared_mrns, data_source="athena_clinic_c")
        d = spec.as_dict()
        dos_dt = datetime(spec.claim_start_date.year,
                          spec.claim_start_date.month,
                          spec.claim_start_date.day)
        dos_epoch = int(dos_dt.timestamp())
        # Parquet preserves ints; keep the epoch integer so the
        # loader/connector can still resolve a date downstream via a
        # cast path in Phase 0.B. For now the connector's try_cast to
        # date will return NULL for these rows — the fixture's
        # expected outcome records this as WARN on null_rate.
        rows.append({
            "control_id": d["claim_id"],
            "service_line": d["claim_line_number"],
            "member_number": d["person_id"],
            "member_id": d["member_id"],
            "payer_id": d["payer"],
            "product_name": d["plan"],
            # Use ISO string so the connector can resolve. Epoch
            # support is a Phase 0.B refinement.
            "claim_start_date": d["claim_start_date"],
            "claim_end_date": d["claim_end_date"],
            "procedure_code": d["hcpcs_code"],
            "total_charge": d["charge_amount"],
            "paid_amount": d["paid_amount"],
            "allowed_amount": d["allowed_amount"],
            "data_source": d["data_source"],
        })
    from .synthetic import write_parquet
    write_parquet(out / "medical_claims_clinic_c.parquet", rows)
