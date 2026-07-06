"""Canonical HRSA tables + an idempotent SQLite store.

Three normalization targets:

  hrsa_hpsa                — Health Professional Shortage Area component
                             rows for all three disciplines (primary
                             care / dental / mental health share this
                             table; ``source_endpoint`` slices them),
                             keyed by ``{hpsa_id}:{discipline}:{geo_id}``.
  hrsa_mua                 — Medically Underserved Area/Population
                             component rows, keyed by the MUA/P id +
                             service-area name + component geography.
  hrsa_health_center_sites — Health Center Program service delivery and
                             look-alike sites, keyed by the BPHC
                             assigned site number.

Column lists are snapshots of the LIVE file headers (sampled
2026-07-06) passed through :func:`connectors.hrsa_data.normalize.snake`;
every published column is kept. ``pc_mcta_score`` exists only in the
primary-care HPSA file — dental/mental-health rows leave it NULL, which
is exactly what "one shared table, union of columns" means.

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the composed natural id**
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

# Live headers of BCD_HPSA_FCT_DET_PC.csv (superset: the DH/MH files
# publish the same columns minus pc_mcta_score), snake_cased in file
# order.
_HPSA_COLUMNS: Tuple[str, ...] = (
    "hpsa_name", "hpsa_id", "designation_type", "hpsa_discipline_class",
    "hpsa_score", "pc_mcta_score", "primary_state_abbreviation",
    "hpsa_status", "hpsa_designation_date",
    "hpsa_designation_last_update_date", "metropolitan_indicator",
    "hpsa_geography_identification_number", "hpsa_degree_of_shortage",
    "withdrawn_date", "hpsa_fte", "hpsa_designation_population",
    "pct_of_population_below_100_pct_poverty", "hpsa_formal_ratio",
    "hpsa_population_type", "rural_status", "longitude", "latitude",
    "bhcmis_organization_identification_number", "break_in_designation",
    "common_county_name", "common_postal_code", "common_region_name",
    "common_state_abbreviation", "common_state_county_fips_code",
    "common_state_fips_code", "common_state_name",
    "county_equivalent_name",
    "county_or_county_equivalent_federal_information_processing_standard_code",
    "discipline_class_number", "hpsa_address", "hpsa_city",
    "hpsa_component_name", "hpsa_component_source_identification_number",
    "hpsa_component_state_abbreviation", "hpsa_component_type_code",
    "hpsa_component_type_description",
    "hpsa_designation_population_type_description",
    "hpsa_estimated_served_population",
    "hpsa_estimated_underserved_population",
    "hpsa_metropolitan_indicator_code", "hpsa_population_type_code",
    "hpsa_postal_code", "hpsa_provider_ratio_goal",
    "hpsa_resident_civilian_population", "hpsa_shortage",
    "hpsa_status_code", "hpsa_type_code", "hpsa_withdrawn_date_string",
    "primary_state_fips_code", "primary_state_name", "provider_type",
    "rural_status_code", "state_abbreviation",
    "state_and_county_federal_information_processing_standard_code",
    "state_fips_code", "state_name",
    "u_s_mexico_border_100_kilometer_indicator",
    "u_s_mexico_border_county_indicator",
    "data_warehouse_record_create_date",
    "data_warehouse_record_create_date_text",
)

# Live headers of MUA_DET.csv, snake_cased in file order.
_MUA_COLUMNS: Tuple[str, ...] = (
    "mua_p_id", "mua_p_area_code", "mua_p_service_area_name",
    "designation_type_code", "designation_type", "mua_p_status_code",
    "mua_p_status_description", "designation_date",
    "mua_p_designation_date_string", "mua_p_update_date",
    "mua_p_update_date_string",
    "medically_underserved_area_population_mua_p_withdrawal_date",
    "medically_underserved_area_population_mua_p_withdrawal_date_in_text_format",
    "break_in_designation", "imu_score", "mua_p_population_type_code",
    "population_type",
    "medically_underserved_area_population_mua_p_metropolitan_indicator",
    "medically_underserved_area_population_mua_p_metropolitan_description",
    "medically_underserved_area_population_mua_p_component_geographic_name",
    "medically_underserved_area_population_mua_p_component_geographic_type_code",
    "medically_underserved_area_population_mua_p_component_geographic_type_description",
    "hhs_region_code", "hhs_region_name", "state_fips_code",
    "state_name", "state_abbreviation",
    "state_and_county_federal_information_processing_standard_code",
    "county_or_county_equivalent_federal_information_processing_standard_code",
    "complete_county_name", "county_equivalent_name",
    "county_description", "county_subdivision_name",
    "county_subdivision_fips_code", "census_tract", "rural_status_code",
    "rural_status_description",
    "u_s_mexico_border_100_kilometer_indicator",
    "u_s_mexico_border_county_indicator",
    "percent_of_population_with_incomes_at_or_below_100_percent_of_the_u_s_federal_poverty_level",
    "percent_of_population_with_incomes_at_or_below_100_percent_of_the_u_s_federal_poverty_level_index_of_medical_underservice_score",
    "percentage_of_population_age_65_and_over",
    "percentage_of_population_age_65_and_over_imu_score",
    "infant_mortality_rate", "infant_mortality_rate_imu_score",
    "designation_population_in_a_medically_underserved_area_population_mua_p",
    "medically_underserved_area_population_mua_p_total_resident_civilian_population",
    "providers_per_1000_population",
    "ratio_of_providers_per_1000_population",
    "ratio_of_providers_per_1000_population_imu_score",
    "primary_hhs_region_code", "primary_hhs_region_name",
    "primary_state_fips_code", "primary_state_abbreviation",
    "primary_state_name", "common_region_code", "common_region_name",
    "common_state_name", "common_state_abbreviation",
    "common_state_fips_code", "common_state_county_fips_code",
    "common_county_name", "data_warehouse_record_create_date",
    "data_warehouse_record_create_date_text",
)

# Live headers of Health_Center_Service_Delivery_and_LookAlike_Sites.csv,
# snake_cased in file order.
_SITE_COLUMNS: Tuple[str, ...] = (
    "health_center_type", "health_center_number",
    "bhcmis_organization_identification_number", "bphc_assigned_number",
    "site_name", "site_address", "site_city", "site_state_abbreviation",
    "site_postal_code", "site_telephone_number", "site_web_address",
    "operating_hours_per_week",
    "health_center_location_setting_identification_number",
    "health_center_service_delivery_site_location_setting_description",
    "health_center_status_identification_number",
    "site_status_description", "fqhc_site_medicare_billing_number",
    "fqhc_site_npi_number",
    "health_center_location_identification_number",
    "health_center_location_type_description",
    "health_center_type_identification_number",
    "health_center_type_description",
    "health_center_operator_identification_number",
    "health_center_operator_description",
    "health_center_operating_schedule_identification_number",
    "health_center_operational_schedule_description",
    "health_center_operating_calendar_surrogate_key",
    "health_center_operating_calendar", "site_added_to_scope_this_date",
    "health_center_name", "health_center_organization_street_address",
    "health_center_organization_city",
    "health_center_organization_state",
    "health_center_organization_zip_code",
    "grantee_organization_type_description",
    "geocoding_artifact_address_primary_x_coordinate",
    "geocoding_artifact_address_primary_y_coordinate",
    "u_s_mexico_border_100_kilometer_indicator",
    "u_s_mexico_border_county_indicator",
    "state_and_county_federal_information_processing_standard_code",
    "complete_county_name", "county_equivalent_name",
    "county_description", "hhs_region_code", "hhs_region_name",
    "state_fips_code", "state_name",
    "state_fips_and_congressional_district_number_code",
    "congressional_district_number", "congressional_district_name",
    "congressional_district_code",
    "u_s_congressional_representative_name",
    "name_of_u_s_senator_number_one", "name_of_u_s_senator_number_two",
    "data_warehouse_record_create_date",
)

TABLES: Dict[str, TableDef] = {
    "hrsa_hpsa": TableDef(
        "hrsa_hpsa", "hpsa_key",
        ("hpsa_key", *_HPSA_COLUMNS, *_META),
    ),
    "hrsa_mua": TableDef(
        "hrsa_mua", "mua_key",
        ("mua_key", *_MUA_COLUMNS, *_META),
    ),
    "hrsa_health_center_sites": TableDef(
        "hrsa_health_center_sites", "site_key",
        ("site_key", *_SITE_COLUMNS, *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = (
    "hrsa_hpsa", "hrsa_mua", "hrsa_health_center_sites",
)


class HrsaDataStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the HRSA SQLite file directly,
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
        # Helpful secondary indexes for the /v1/query + lookup paths
        # (state slicing is the dominant access pattern).
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hpsa_id "
                    "ON hrsa_hpsa(hpsa_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hpsa_state "
                    "ON hrsa_hpsa(common_state_abbreviation)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hpsa_status "
                    "ON hrsa_hpsa(hpsa_status)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_mua_id "
                    "ON hrsa_mua(mua_p_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_mua_state "
                    "ON hrsa_mua(state_abbreviation)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_sites_state "
                    "ON hrsa_health_center_sites(site_state_abbreviation)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_sites_npi "
                    "ON hrsa_health_center_sites(fqhc_site_npi_number)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_sites_center "
                    "ON hrsa_health_center_sites(health_center_number)")
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

    None stays None (NULL). We keep everything TEXT so the uniform
    ``/v1/query`` layer has one type model — numeric comparisons there
    cast explicitly.
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)
