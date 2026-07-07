"""Canonical data.medicaid.gov tables + an idempotent SQLite store.

Every curated table's columns were snapshotted from a LIVE sample of the
DKAN datastore on 2026-07-06 (``/api/1/datastore/query/{uuid}/0?limit=1``).
DKAN already returns lower-snake-case column names — including the
hash-suffixed ones DKAN generates for long headers (e.g.
``populations_enrolled_lowincome_adults_not_covered_under_aca_0778``) —
so the live names are used verbatim; no renaming layer to drift.

Everything is stored TEXT: DKAN itself serves most values as strings
(even ``nadac_per_unit`` arrives quoted) and SQLite is dynamically typed,
so TEXT keeps one type model for the uniform ``/v1/query`` layer — numeric
comparisons there cast explicitly.

Shared-table pattern (the estate's documented approach for per-year
files): all NADAC year datasets land in ``medicaid_nadac`` and all SDUD
year datasets in ``medicaid_sdud``, sliced by the ``source_endpoint``
column; each row's composed key is prefixed with the dataset key so year
slices can never collide.

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the composed natural key**
so a re-run never double-counts — idempotency is enforced at the table,
not the caller. All SQL is parameterised; the column lists below are the
only interpolated identifiers and they are module constants, never user
input.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class TableDef:
    name: str
    pk: str
    columns: Tuple[str, ...]   # all columns incl. pk, in order

    def create_sql(self) -> str:
        cols = []
        for c in self.columns:
            if c == self.pk:
                cols.append(f"{c} TEXT PRIMARY KEY")
            elif c == "row_idx":
                # The one intentionally-numeric column (generic row order).
                cols.append(f"{c} INTEGER")
            else:
                cols.append(f"{c} TEXT")
        return f"CREATE TABLE IF NOT EXISTS {self.name} (\n  " + ",\n  ".join(cols) + "\n)"

    def upsert_sql(self) -> str:
        cols = ", ".join(self.columns)
        placeholders = ", ".join("?" for _ in self.columns)
        updates = ", ".join(
            f"{c}=excluded.{c}" for c in self.columns if c != self.pk
        )
        return (
            f"INSERT INTO {self.name} ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT({self.pk}) DO UPDATE SET {updates}"
        )


# ── Canonical schema ──────────────────────────────────────────────────
_META = ("source_endpoint", "ingested_at")

TABLES: Dict[str, TableDef] = {
    # The full DKAN catalog: one row per dataset on data.medicaid.gov.
    "medicaid_data_catalog": TableDef(
        "medicaid_data_catalog", "identifier",
        ("identifier", "title", "description", "themes", "keywords",
         "access_level", "periodicity", "issued", "modified", "temporal",
         "publisher", "contact", "contact_email", "license", "references_urls",
         "distribution_format", "distribution_download_url",
         "distribution_described_by", "n_distributions", "api_url", *_META),
    ),
    # NADAC weekly reference rows — SHARED across nadac_YYYY datasets.
    "medicaid_nadac": TableDef(
        "medicaid_nadac", "nadac_key",
        ("nadac_key", "ndc_description", "ndc", "nadac_per_unit",
         "effective_date", "pricing_unit", "pharmacy_type_indicator", "otc",
         "explanation_code", "classification_for_rate_setting",
         "corresponding_generic_drug_nadac_per_unit",
         "corresponding_generic_drug_effective_date", "as_of_date", *_META),
    ),
    # State Drug Utilization Data — SHARED across sdud_YYYY datasets.
    "medicaid_sdud": TableDef(
        "medicaid_sdud", "sdud_key",
        ("sdud_key", "utilization_type", "state", "ndc", "labeler_code",
         "product_code", "package_size", "year", "quarter",
         "suppression_used", "product_name", "units_reimbursed",
         "number_of_prescriptions", "total_amount_reimbursed",
         "medicaid_amount_reimbursed", "non_medicaid_amount_reimbursed",
         *_META),
    ),
    "medicaid_rebate_drug_product": TableDef(
        "medicaid_rebate_drug_product", "rebate_key",
        ("rebate_key", "year", "quarter", "labeler_name", "ndc",
         "labeler_code", "product_code", "package_size_code", "drug_category",
         "drug_type_indicator", "termination_date", "unit_type",
         "units_per_pkg_size", "fda_approval_date", "market_date",
         "fda_therapeutic_equivalence_code", "fda_product_name",
         "clotting_factor_indicator", "pediatric_indicator",
         "package_size_intro_date", "purchased_product_date", "cod_status",
         "fda_application_number", "reactivation_date",
         "line_extension_drug_indicator", *_META),
    ),
    "medicaid_enrollment_new_adult_group": TableDef(
        "medicaid_enrollment_new_adult_group", "enrollment_key",
        ("enrollment_key", "state", "total_medicaid_enrollees",
         "total_viii_group_enrollees",
         "total_viii_group_newly_eligible_enrollees",
         "total_viii_group_not_newly_eligible_enrollees", "updated_year",
         "updated_month", "enrollment_year", "enrollment_month", "notes",
         *_META),
    ),
    "medicaid_enrollment_monthly": TableDef(
        "medicaid_enrollment_monthly", "period_key",
        ("period_key", "state_abbreviation", "state_name", "reporting_period",
         "state_expanded_medicaid", "preliminary_or_updated", "final_report",
         "new_applications_submitted_to_medicaid_and_chip_agencies",
         "new_applications_submitted_to_medicaid_and_chip_agencies__f_85d7",
         "applications_for_financial_assistance_submitted_to_the_stat_104d",
         "applications_for_financial_assistance_submitted_to_the_stat_c640",
         "total_applications_for_financial_assistance_submitted_at_st_d6fa",
         "total_applications_for_financial_assistance_submitted_at_st_9919",
         "individuals_determined_eligible_for_medicaid_at_application",
         "individuals_determined_eligible_for_medicaid_at_application_4f96",
         "individuals_determined_eligible_for_chip_at_application",
         "individuals_determined_eligible_for_chip_at_application__fo_e28a",
         "total_medicaid_and_chip_determinations",
         "total_medicaid_and_chip_determinations__footnotes",
         "medicaid_and_chip_child_enrollment",
         "medicaid_and_chip_child_enrollment__footnotes",
         "total_medicaid_and_chip_enrollment",
         "total_medicaid_and_chip_enrollment__footnotes",
         "total_medicaid_enrollment", "total_medicaid_enrollment__footnotes",
         "total_chip_enrollment", "total_chip_enrollment__footnotes",
         "total_adult_medicaid_enrollment",
         "total_adult_medicaid_enrollment__footnotes",
         "total_medicaid_and_chip_determinations_processed_in_less_th_1e84",
         "total_medicaid_and_chip_determinations_processed_in_less_th_46c2",
         "total_medicaid_and_chip_determinations_processed_between_24_756e",
         "total_medicaid_and_chip_determinations_processed_between_24_cf22",
         "total_medicaid_and_chip_determinations_processed_between_8__a7a5",
         "total_medicaid_and_chip_determinations_processed_between_8__e6e5",
         "total_medicaid_and_chip_determinations_processed_between_31_a42c",
         "total_medicaid_and_chip_determinations_processed_between_31_49fa",
         "total_medicaid_and_chip_determinations_processed_in_more_th_a7ec",
         "total_medicaid_and_chip_determinations_processed_in_more_th_bfce",
         "total_call_center_volume_number_of_calls",
         "total_call_center_volume_number_of_calls__footnotes",
         "average_call_center_wait_time_minutes",
         "average_call_center_wait_time_minutes__footnotes",
         "average_call_center_abandonment_rate",
         "average_call_center_abandonment_rate__footnotes", *_META),
    ),
    "medicaid_managed_care_program": TableDef(
        "medicaid_managed_care_program", "program_key",
        ("program_key", "features", "program_type",
         "statewide_or_regionspecific", "federal_operating_authority",
         "program_start_date", "waiver_expiration_date_if_applicable",
         "if_the_program_ended_in_2024_indicate_the_end_date",
         "populations_enrolled_lowincome_adults_not_covered_under_aca_0778",
         "populations_enrolled_lowincome_adults_covered_under_aca_sec_03d9",
         "populations_enrolled_aged_blind_or_disabled_children_or_adults",
         "populations_enrolled_nondisabled_children_excludes_children_1dda",
         "populations_enrolled_individuals_receiving_limited_benefits_facc",
         "populations_enrolled_full_duals",
         "populations_enrolled_children_with_special_health_care_needs",
         "populations_enrolled_native_americanalaskan_natives",
         "populations_enrolled_foster_care_and_adoption_assistance_ch_b424",
         "populations_enrolled_enrollment_choice_period",
         "populations_enrolled_enrollment_broker_name_if_applicable",
         "populations_enrolled_notes_on_enrollment_choice_period",
         "benefits_covered_inpatient_hospital_physical_health",
         "benefits_covered_inpatient_hospital_behavioral_health_mh_an_4041",
         "benefits_covered_outpatient_hospital_physical_health",
         "benefits_covered_outpatient_hospital_behavioral_health_mh_a_ceee",
         "benefits_covered_partial_hospitalization",
         "benefits_covered_physician", "benefits_covered_nurse_practitioner",
         "benefits_covered_rural_health_clinics_and_fqhcs",
         "benefits_covered_clinic_services", "benefits_covered_lab_and_xray",
         "benefits_covered_prescription_drugs",
         "benefits_covered_prosthetic_devices", "benefits_covered_epsdt",
         "benefits_covered_case_management",
         "benefits_covered_ssa_section_1945authorized_health_home",
         "benefits_covered_home_health_services_services_in_home",
         "benefits_covered_family_planning",
         "benefits_covered_dental_services_medicalsurgical",
         "benefits_covered_dental_preventative_or_corrective",
         "benefits_covered_personal_care_state_plan_option",
         "benefits_covered_hcbs_waiver_services",
         "benefits_covered_private_duty_nursing", "benefits_covered_icfidd",
         "benefits_covered_nursing_facility_services",
         "benefits_covered_hospice_care",
         "benefits_covered_nonemergency_medical_transportation",
         "benefits_covered_institution_for_mental_disease_inpatient_t_448a",
         "benefits_covered_other_eg_nurse_midwife_services_freestandi_bfd7",
         "quality_assurance_and_improvement_hedis_data_required",
         "quality_assurance_and_improvement_cahps_data_required",
         "quality_assurance_and_improvement_accreditation_required",
         "quality_assurance_and_improvement_accrediting_organization",
         "quality_assurance_and_improvement_eqro_contractor_name_if_a_f2dc",
         "performance_incentives_payment_bonusesdifferentials_to_rewa_eece",
         "performance_incentives_preferential_autoenrollment_to_rewar_ab96",
         "performance_incentives_public_reports_comparing_plan_perfor_42d0",
         "performance_incentives_withholds_tied_to_performance_metrics",
         "performance_incentives_mcosphps_required_or_encouraged_to_p_bf59",
         "participating_plans_in_program", "program_notes", "state", *_META),
    ),
    "medicaid_mc_enrollment_summary": TableDef(
        "medicaid_mc_enrollment_summary", "summary_key",
        ("summary_key", "state", "notes", "total_medicaid_enrollees",
         "total_medicaid_enrollment_in_any_type_of_managed_care",
         "medicaid_enrollment_in_comprehensive_managed_care",
         "medicaid_newly_eligible_adults_enrolled_in_comprehensive_mcos",
         "year", *_META),
    ),
    "medicaid_aca_ful": TableDef(
        "medicaid_aca_ful", "ful_key",
        ("ful_key", "product_group", "ingredient", "strength", "dosage",
         "route", "mdr_unit_type", "weighted_average_of_amps", "aca_ful",
         "package_size", "ndc", "arated",
         "multiplier_greater_than_175_percent_of_weighted_avg_of_amps",
         "year", "month", *_META),
    ),
    "medicaid_nadac_comparison": TableDef(
        "medicaid_nadac_comparison", "comparison_key",
        ("comparison_key", "ndc_description", "ndc", "old_nadac_per_unit",
         "new_nadac_per_unit", "classification_for_rate_setting",
         "percent_change", "primary_reason", "start_date", "end_date",
         "effective_date", *_META),
    ),
    "medicaid_financial_management": TableDef(
        "medicaid_financial_management", "fin_key",
        ("fin_key", "state", "program", "service_category", "notes",
         "total_computable", "federal_share", "federal_share_medicaid",
         "federal_share_arra", "federal_share_bipp", "state_share", "year",
         "location", *_META),
    ),
    "medicaid_quality_measure": TableDef(
        "medicaid_quality_measure", "measure_key",
        ("measure_key", "state", "domain", "reporting_program",
         "measure_name", "measure_abbreviation", "measure_type",
         "rate_definition", "core_set_year", "population", "methodology",
         "state_rate", "number_of_states_reporting", "mean", "median",
         "bottom_quartile", "top_quartile", "notes", "source",
         "statespecific_comments",
         "rate_used_in_calculating_state_mean_and_median", *_META),
    ),
    # Generic escape hatch: raw row JSON for ANY of the 541 catalog datasets.
    "medicaid_data_rows": TableDef(
        "medicaid_data_rows", "row_key",
        ("row_key", "dataset_key", "row_idx", "row_json", "fetched_at",
         *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = tuple(TABLES)


class MedicaidDataStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the medicaid_data SQLite file directly,
    mirroring the RCM-MC convention that a single store owns the
    connection.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        # check_same_thread=False so the read-only HTTP surface
        # (ThreadingHTTPServer, one worker thread per request) can share the
        # connection. Writes only happen single-threaded in the pipeline, so
        # this does not introduce a write race; WAL + busy_timeout cover the
        # rest.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.ensure_schema()

    def ensure_schema(self) -> None:
        cur = self.conn.cursor()
        for tdef in TABLES.values():
            cur.execute(tdef.create_sql())
        # Helpful secondary indexes for the /v1/query + lookup paths.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_nadac_ndc "
                    "ON medicaid_nadac(ndc)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_nadac_as_of "
                    "ON medicaid_nadac(as_of_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_sdud_state "
                    "ON medicaid_sdud(state)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_sdud_ndc "
                    "ON medicaid_sdud(ndc)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rebate_ndc "
                    "ON medicaid_rebate_drug_product(ndc)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_catalog_title "
                    "ON medicaid_data_catalog(title)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rows_dataset_key "
                    "ON medicaid_data_rows(dataset_key)")
        self.conn.commit()

    def upsert(self, table: str, rows: Sequence[Dict[str, Any]]) -> int:
        """Upsert canonical rows keyed by the table's natural PK.

        Rows are dicts of column→value; missing columns default to NULL,
        extra keys are ignored. Returns the number of rows written.
        """
        if not rows:
            return 0
        tdef = TABLES[table]
        now = _utc_now()
        sql = tdef.upsert_sql()
        params: List[Tuple[Any, ...]] = []
        for r in rows:
            r = dict(r)
            r.setdefault("ingested_at", now)
            params.append(tuple(_coerce(r.get(c)) for c in tdef.columns))
        with self.conn:  # implicit BEGIN/COMMIT, atomic
            self.conn.executemany(sql, params)
        return len(params)

    def replace_slice(self, table: str, dataset_key: str,
                      rows: Sequence[Dict[str, Any]], *,
                      slice_sig: str = "") -> int:
        """Atomically replace ONE dataset's slice of a shared generic table.

        A re-fetch that returns fewer rows than the previous pull would,
        under plain upserts, strand the earlier pull's trailing
        ``row_idx`` rows — served intermixed with fresh rows and counted
        by every surface, with nothing flagging the mixed vintages. One
        transaction deletes exactly the slice being re-pulled and writes
        the fresh rows (mirroring ``oig_leie``'s replace-in-transaction
        semantics), so a reader never observes a half-replaced slice.

        Slice targeting matches the normalizer's key grammar: unfiltered
        pulls key ``{dataset_key}:{row_idx}`` (one colon segment) and
        filtered pulls ``{dataset_key}:{slice_sig}:{row_idx}`` — dataset
        keys are slugs/UUIDs (never contain ``:``) and signatures are
        fixed-length hex, so the LIKE shapes below classify exactly.
        Only meaningful for the generic ``*_rows`` table.
        """
        tdef = TABLES[table]
        for needed in ("row_key", "dataset_key", "row_idx"):
            if needed not in tdef.columns:
                raise ValueError(
                    f"replace_slice targets generic row tables; {table!r} "
                    f"has no {needed!r} column")
        sql = tdef.upsert_sql()
        now = _utc_now()
        params: List[Tuple[Any, ...]] = []
        for r in rows:
            r = dict(r)
            r.setdefault("ingested_at", now)
            params.append(tuple(_coerce(r.get(c)) for c in tdef.columns))
        with self.conn:  # implicit BEGIN/COMMIT, atomic
            if slice_sig:
                self.conn.execute(
                    f"DELETE FROM {tdef.name} WHERE dataset_key = ? "
                    f"AND row_key LIKE ? || ':' || ? || ':%'",
                    (dataset_key, dataset_key, slice_sig))
            else:
                self.conn.execute(
                    f"DELETE FROM {tdef.name} WHERE dataset_key = ? "
                    f"AND row_key LIKE ? || ':%' "
                    f"AND row_key NOT LIKE ? || ':%:%'",
                    (dataset_key, dataset_key, dataset_key))
            if params:
                self.conn.executemany(sql, params)
        return len(params)

    def count(self, table: str, where: str = "", args: Sequence[Any] = ()) -> int:
        sql = f"SELECT COUNT(*) AS n FROM {table}"
        if where:
            sql += f" WHERE {where}"
        row = self.conn.execute(sql, tuple(args)).fetchone()
        return int(row["n"]) if row else 0

    def fetchall(self, sql: str, args: Sequence[Any] = ()) -> List[sqlite3.Row]:
        return list(self.conn.execute(sql, tuple(args)).fetchall())

    def close(self) -> None:
        self.conn.close()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _coerce(value: Any) -> Any:
    """SQLite stores TEXT; coerce lists/dicts to JSON and scalars to str.

    None stays None (NULL). Ints pass through for the one INTEGER column
    (``row_idx``); everything else becomes str so the uniform ``/v1/query``
    layer has one type model — numeric comparisons there cast explicitly.
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return value
    return str(value)
