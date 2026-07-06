"""Declarative specs for every healthdata.gov dataset this connector ingests.

One :class:`EndpointSpec` per dataset. The spec is the single place that
knows the Socrata-specific quirks: the 4x4 resource id, the live-sampled
column snapshot the canonical table is derived from, the fields the
idempotent upsert key composes from, and the paging posture (page size,
date field, cadence).

Why specs and not code branches: adding or retuning a dataset is a data
edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.healthdata_gov.registry`), the tables
(:mod:`connectors.healthdata_gov.tables`) and the connector all read
these.

Three dataset kinds:

  ``catalog``   — the full healthdata.gov catalog itself, synced from the
                  Socrata metadata API (``/api/views/metadata/v1``);
                  23,080 entries live 2026-07-06. healthdata.gov is the
                  HHS-wide *meta*-catalog: 20,580 entries are HHS's own
                  hub records (``domain=datahub.hhs.gov`` — every
                  row-serving native dataset lives here, but so do
                  thousands of href mirrors whose ``attribution`` names
                  the home portal: data.cdc.gov, data.medicaid.gov,
                  data.cms.gov, …) and 2,500 are copies federated in
                  from state/city portals (``domain=healthdata.gov``).
                  Non-row entries 403 on ``/resource/``. The catalog
                  table carries the live ``domain`` + ``attribution``
                  fields precisely so mirrors are distinguishable from
                  natives.
  ``curated``   — flagship NATIVE datasets promoted to first-class
                  canonical tables. Each 4x4 id was VERIFIED LIVE on
                  2026-07-06 via ``/resource/{id}.json`` and each
                  ``columns`` tuple is a snapshot of the live field names
                  from ``/api/views/{id}.json`` (Socrata JSON rows omit
                  null fields, so sampling rows alone under-reports
                  columns). Every ``pk_fields`` grain was verified with a
                  live SoQL ``$group … $having count(*) > 1`` probe
                  returning zero duplicates.
  ``generic``   — the on-demand escape hatch: ANY 4x4 on the domain can
                  be pulled with ``connector.fetch_dataset()`` into the
                  ``healthdata_gov_rows`` JSON-blob table and still be
                  queried through the uniform engine.

Curation notes from the live sweep (2026-07-06)
-----------------------------------------------
Only ~114 assets on healthdata.gov are native ``type=dataset`` rows
(Socrata discovery API, ``only=dataset``); the assignment's other strong
candidates all turned out to be ``href`` mirrors or absent as natives and
were SKIPPED as estate duplicates / non-fetchable:

  * SAMHSA behavioral-health treatment facility directories → ``href``
    links to PDFs / findtreatment.gov, no rows API.
  * AHRQ Social Determinants of Health database → ``href`` only.
  * Organ procurement / transplant → ``href`` to HRSA (separate
    connector's domain).
  * Drug overdose / naloxone → all ``href`` mirrors of data.cdc.gov
    (VSRR xkb8-kh2a etc. are curated in the cdc_data connector already).
  * Nursing-home COVID → ``href`` mirror of data.cms.gov.

Two natives were REJECTED on grain grounds after live key probes:
``ehpz-xc9n`` (HHS Unaccompanied Alien Children) duplicates ``date`` rows
with conflicting values, and ``g89t-x93h`` (Project Tycho Level 1)
duplicates ``(epi_week, state, loc, loc_type, disease)``. Both remain
reachable via the generic ``fetched_rows`` escape hatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_HEALTHDATA_BASE = "https://healthdata.gov"

# The Socrata catalog metadata endpoint. VERIFIED LIVE 2026-07-06: it
# pages by ``limit`` + 1-based ``page`` and the documented ``offset``
# param is silently IGNORED on this domain (offset paging returns page 1
# forever, which would loop an ingest) — the exact same quirk the estate
# recorded for data.cdc.gov. Stop on a short/empty page.
CATALOG_PATH = "/api/views/metadata/v1"


@dataclass(frozen=True)
class EndpointSpec:
    """One healthdata.gov dataset.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix and
        the value written into each row's ``source_endpoint`` column.
    resource_id:
        The Socrata 4x4 id (empty for the catalog + generic pseudo
        datasets, which have no single backing resource).
    kind:
        ``catalog`` | ``curated`` | ``generic`` — drives which normalizer
        mapper runs and how the connector fetches.
    target_table:
        Canonical table the normalizer upserts into.
    title:
        The dataset's live name on healthdata.gov (documentation only).
    columns:
        Snapshot of the live column field names (already lowercase
        snake_case in Socrata JSON) that the canonical table carries.
        Empty for catalog/generic, whose tables are hand-shaped.
    pk_fields:
        Ordered raw fields the composed upsert key is built from in
        :mod:`connectors.healthdata_gov.normalize` (``"a:b:c"``). Missing
        fields compose as ``""`` so sparse rows still key stably.
    date_field:
        Column used for recency ordering / registry ``date_field``.
    page_size:
        Polite per-request ``$limit`` for this dataset (the two hospital
        capacity tables carry 128-135 columns per row, so they page
        smaller by default).
    """

    key: str
    resource_id: str
    kind: str
    target_table: str
    title: str = ""
    columns: Tuple[str, ...] = ()
    pk_fields: Tuple[str, ...] = ()
    date_field: str = ""
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "static"
    page_size: int = 1000
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"healthdata_gov_{self.key}"

    @property
    def base_url(self) -> str:
        return _HEALTHDATA_BASE

    @property
    def path(self) -> str:
        """URL path for this dataset (the generic spec keeps a template)."""
        if self.kind == "catalog":
            return CATALOG_PATH
        if self.kind == "generic":
            return "/resource/{dataset}.json"
        return f"/resource/{self.resource_id}.json"


# ── the catalog itself ────────────────────────────────────────────────
_CATALOG: List[EndpointSpec] = [
    EndpointSpec(
        key="catalog",
        resource_id="",
        kind="catalog",
        target_table="healthdata_gov_catalog",
        title="healthdata.gov dataset catalog (Socrata metadata API)",
        pk_fields=("id",),
        date_field="data_updated_at",
        join_keys=("dataset_uid",),
        refresh_cadence="weekly",
        # ~19k catalog items live; 1000/page was reliable (~15-20s/page)
        # where 5000/page hit gateway read timeouts on this domain.
        page_size=1000,
    ),
]

# ── curated flagship NATIVE datasets (all verified live 2026-07-06) ───
_CURATED: List[EndpointSpec] = [
    EndpointSpec(
        key="hospital_capacity_facility",
        resource_id="anag-cw7u",
        kind="curated",
        target_table="hhs_hospital_capacity_facility",
        title=("COVID-19 Reported Patient Impact and Hospital Capacity by "
               "Facility"),
        # 1,045,406 rows live; weekly facility grain. The HHS Protect /
        # Unified Hospital Data Surge reporting system's facility file —
        # the COVID-era hospital-utilization series whose home IS
        # healthdata.gov. Reporting ended 2024-04 (rowsUpdatedAt
        # 2024-05-03), so the series is a frozen archive: cadence static.
        columns=(
            "hospital_pk", "collection_week", "state", "ccn", "hospital_name",
            "address", "city", "zip", "hospital_subtype", "fips_code",
            "is_metro_micro", "total_beds_7_day_avg",
            "all_adult_hospital_beds_7_day_avg",
            "all_adult_hospital_inpatient_beds_7_day_avg",
            "inpatient_beds_used_7_day_avg",
            "all_adult_hospital_inpatient_bed_occupied_7_day_avg",
            "inpatient_beds_used_covid_7_day_avg",
            "total_adult_patients_hospitalized_confirmed_and_suspected_covid_7_day_avg",
            "total_adult_patients_hospitalized_confirmed_covid_7_day_avg",
            "total_pediatric_patients_hospitalized_confirmed_and_suspected_covid_7_day_avg",
            "total_pediatric_patients_hospitalized_confirmed_covid_7_day_avg",
            "inpatient_beds_7_day_avg", "total_icu_beds_7_day_avg",
            "total_staffed_adult_icu_beds_7_day_avg",
            "icu_beds_used_7_day_avg",
            "staffed_adult_icu_bed_occupancy_7_day_avg",
            "staffed_icu_adult_patients_confirmed_and_suspected_covid_7_day_avg",
            "staffed_icu_adult_patients_confirmed_covid_7_day_avg",
            "total_patients_hospitalized_confirmed_influenza_7_day_avg",
            "icu_patients_confirmed_influenza_7_day_avg",
            "total_patients_hospitalized_confirmed_influenza_and_covid_7_day_avg",
            "total_beds_7_day_sum", "all_adult_hospital_beds_7_day_sum",
            "all_adult_hospital_inpatient_beds_7_day_sum",
            "inpatient_beds_used_7_day_sum",
            "all_adult_hospital_inpatient_bed_occupied_7_day_sum",
            "inpatient_beds_used_covid_7_day_sum",
            "total_adult_patients_hospitalized_confirmed_and_suspected_covid_7_day_sum",
            "total_adult_patients_hospitalized_confirmed_covid_7_day_sum",
            "total_pediatric_patients_hospitalized_confirmed_and_suspected_covid_7_day_sum",
            "total_pediatric_patients_hospitalized_confirmed_covid_7_day_sum",
            "inpatient_beds_7_day_sum", "total_icu_beds_7_day_sum",
            "total_staffed_adult_icu_beds_7_day_sum",
            "icu_beds_used_7_day_sum",
            "staffed_adult_icu_bed_occupancy_7_day_sum",
            "staffed_icu_adult_patients_confirmed_and_suspected_covid_7_day_sum",
            "staffed_icu_adult_patients_confirmed_covid_7_day_sum",
            "total_patients_hospitalized_confirmed_influenza_7_day_sum",
            "icu_patients_confirmed_influenza_7_day_sum",
            "total_patients_hospitalized_confirmed_influenza_and_covid_7_day_sum",
            "total_beds_7_day_coverage",
            "all_adult_hospital_beds_7_day_coverage",
            "all_adult_hospital_inpatient_beds_7_day_coverage",
            "inpatient_beds_used_7_day_coverage",
            "all_adult_hospital_inpatient_bed_occupied_7_day_coverage",
            "inpatient_beds_used_covid_7_day_coverage",
            "total_adult_patients_hospitalized_confirmed_and_suspected_covid_7_day_coverage",
            "total_adult_patients_hospitalized_confirmed_covid_7_day_coverage",
            "total_pediatric_patients_hospitalized_confirmed_and_suspected_covid_7_day_coverage",
            "total_pediatric_patients_hospitalized_confirmed_covid_7_day_coverage",
            "inpatient_beds_7_day_coverage", "total_icu_beds_7_day_coverage",
            "total_staffed_adult_icu_beds_7_day_coverage",
            "icu_beds_used_7_day_coverage",
            "staffed_adult_icu_bed_occupancy_7_day_coverage",
            "staffed_icu_adult_patients_confirmed_and_suspected_covid_7_day_coverage",
            "staffed_icu_adult_patients_confirmed_covid_7_day_coverage",
            "total_patients_hospitalized_confirmed_influenza_7_day_coverage",
            "icu_patients_confirmed_influenza_7_day_coverage",
            "total_patients_hospitalized_confirmed_influenza_and_covid_7_day_coverage",
            "previous_day_admission_adult_covid_confirmed_7_day_sum",
            "previous_day_admission_adult_covid_confirmed_18_19_7_day_sum",
            "previous_day_admission_adult_covid_confirmed_20_29_7_day_sum",
            "previous_day_admission_adult_covid_confirmed_30_39_7_day_sum",
            "previous_day_admission_adult_covid_confirmed_40_49_7_day_sum",
            "previous_day_admission_adult_covid_confirmed_50",
            "previous_day_admission_adult_covid_confirmed_60",
            "previous_day_admission_adult_covid_confirmed_70",
            "previous_day_admission_adult_covid_confirmed_80",
            "previous_day_admission_adult_covid_confirmed_unknown_7_day_sum",
            "previous_day_admission_pediatric_covid_confirmed_7_day_sum",
            "previous_day_covid_ed_visits_7_day_sum",
            "previous_day_admission_adult_covid_suspected_7_day_sum",
            "previous_day_admission_adult_covid_suspected_18",
            "previous_day_admission_adult_covid_suspected_20",
            "previous_day_admission_adult_covid_suspected_30",
            "previous_day_admission_adult_covid_suspected_40",
            "previous_day_admission_adult_covid_suspected_50",
            "previous_day_admission_adult_covid_suspected_60",
            "previous_day_admission_adult_covid_suspected_70_79_7_day_sum",
            "previous_day_admission_adult_covid_suspected_80",
            "previous_day_admission_adult_covid_suspected_unknown_7_day_sum",
            "previous_day_admission_pediatric_covid_suspected_7_day_sum",
            "previous_day_total_ed_visits_7_day_sum",
            "previous_day_admission_influenza_confirmed_7_day_sum",
            "geocoded_hospital_address", "hhs_ids",
            "previous_day_admission_adult_covid_confirmed_7_day_coverage",
            "previous_day_admission_pediatric_covid_confirmed_7_day_coverage",
            "previous_day_admission_adult_covid_suspected_7_day_coverage",
            "previous_day_admission_pediatric_covid_suspected_7_day_coverage",
            "previous_week_personnel_covid_vaccinated_doses_administered_7_day",
            "total_personnel_covid_vaccinated_doses_none_7_day",
            "total_personnel_covid_vaccinated_doses_one_7_day",
            "total_personnel_covid_vaccinated_doses_all_7_day",
            "previous_week_patients_covid_vaccinated_doses_one_7_day",
            "previous_week_patients_covid_vaccinated_doses_all_7_day",
            "is_corrected", "all_pediatric_inpatient_bed_occupied_7_day_avg",
            "all_pediatric_inpatient_bed_occupied_7_day_coverage",
            "all_pediatric_inpatient_bed_occupied_7_day_sum",
            "all_pediatric_inpatient_beds_7_day_avg",
            "all_pediatric_inpatient_beds_7_day_coverage",
            "all_pediatric_inpatient_beds_7_day_sum",
            "previous_day_admission_pediatric_covid_confirmed_0_4_7_day_sum",
            "previous_day_admission_pediatric_covid_confirmed_12_17_7_day_sum",
            "previous_day_admission_pediatric_covid_confirmed_5_11_7_day_sum",
            "previous_day_admission_pediatric_covid_confirmed_unknown_7_day_sum",
            "staffed_icu_pediatric_patients_confirmed_covid_7_day_avg",
            "staffed_icu_pediatric_patients_confirmed_covid_7_day_coverage",
            "staffed_icu_pediatric_patients_confirmed_covid_7_day_sum",
            "staffed_pediatric_icu_bed_occupancy_7_day_avg",
            "staffed_pediatric_icu_bed_occupancy_7_day_coverage",
            "staffed_pediatric_icu_bed_occupancy_7_day_sum",
            "total_staffed_pediatric_icu_beds_7_day_avg",
            "total_staffed_pediatric_icu_beds_7_day_coverage",
            "total_staffed_pediatric_icu_beds_7_day_sum",
        ),
        # VERIFIED LIVE: zero duplicate (hospital_pk, collection_week)
        # pairs across all 1,045,406 rows. hospital_pk is usually the CCN;
        # ccn is carried separately for estate joins.
        pk_fields=("hospital_pk", "collection_week"),
        date_field="collection_week",
        join_keys=("ccn",),
        refresh_cadence="static",
        # 128 columns/row → smaller pages keep response sizes sane.
        page_size=500,
    ),
    EndpointSpec(
        key="hospital_capacity_state_ts",
        resource_id="sgxm-t72h",
        kind="curated",
        target_table="hhs_hospital_capacity_state_ts",
        title=("COVID-19 Reported Patient Impact and Hospital Capacity by "
               "State Timeseries"),
        # 81,335 rows live; daily state grain 2020-01 → 2024-04. The
        # polished companion of the facility file (the RAW variant
        # g62h-syeh is skipped as redundant). Note the live schema quirk:
        # field previous_day_admission_adult_covid_suspected_80_ carries a
        # trailing underscore — snapshotted verbatim.
        columns=(
            "state", "date", "critical_staffing_shortage_today_yes",
            "critical_staffing_shortage_today_no",
            "critical_staffing_shortage_today_not_reported",
            "critical_staffing_shortage_anticipated_within_week_yes",
            "critical_staffing_shortage_anticipated_within_week_no",
            "critical_staffing_shortage_anticipated_within_week_not_reported",
            "hospital_onset_covid", "hospital_onset_covid_coverage",
            "inpatient_beds", "inpatient_beds_coverage",
            "inpatient_beds_used", "inpatient_beds_used_coverage",
            "inpatient_beds_used_covid", "inpatient_beds_used_covid_coverage",
            "previous_day_admission_adult_covid_confirmed",
            "previous_day_admission_adult_covid_confirmed_coverage",
            "previous_day_admission_adult_covid_suspected",
            "previous_day_admission_adult_covid_suspected_coverage",
            "previous_day_admission_pediatric_covid_confirmed",
            "previous_day_admission_pediatric_covid_confirmed_coverage",
            "previous_day_admission_pediatric_covid_suspected",
            "previous_day_admission_pediatric_covid_suspected_coverage",
            "staffed_adult_icu_bed_occupancy",
            "staffed_adult_icu_bed_occupancy_coverage",
            "staffed_icu_adult_patients_confirmed_and_suspected_covid",
            "staffed_icu_adult_patients_confirmed_and_suspected_covid_coverage",
            "staffed_icu_adult_patients_confirmed_covid",
            "staffed_icu_adult_patients_confirmed_covid_coverage",
            "total_adult_patients_hospitalized_confirmed_and_suspected_covid",
            "total_adult_patients_hospitalized_confirmed_and_suspected_covid_coverage",
            "total_adult_patients_hospitalized_confirmed_covid",
            "total_adult_patients_hospitalized_confirmed_covid_coverage",
            "total_pediatric_patients_hospitalized_confirmed_and_suspected_covid",
            "total_pediatric_patients_hospitalized_confirmed_and_suspected_covid_coverage",
            "total_pediatric_patients_hospitalized_confirmed_covid",
            "total_pediatric_patients_hospitalized_confirmed_covid_coverage",
            "total_staffed_adult_icu_beds",
            "total_staffed_adult_icu_beds_coverage",
            "inpatient_beds_utilization",
            "inpatient_beds_utilization_coverage",
            "inpatient_beds_utilization_numerator",
            "inpatient_beds_utilization_denominator",
            "percent_of_inpatients_with_covid",
            "percent_of_inpatients_with_covid_coverage",
            "percent_of_inpatients_with_covid_numerator",
            "percent_of_inpatients_with_covid_denominator",
            "inpatient_bed_covid_utilization",
            "inpatient_bed_covid_utilization_coverage",
            "inpatient_bed_covid_utilization_numerator",
            "inpatient_bed_covid_utilization_denominator",
            "adult_icu_bed_covid_utilization",
            "adult_icu_bed_covid_utilization_coverage",
            "adult_icu_bed_covid_utilization_numerator",
            "adult_icu_bed_covid_utilization_denominator",
            "adult_icu_bed_utilization", "adult_icu_bed_utilization_coverage",
            "adult_icu_bed_utilization_numerator",
            "adult_icu_bed_utilization_denominator", "geocoded_state",
            "previous_day_admission_adult_covid_confirmed_18_19",
            "previous_day_admission_adult_covid_confirmed_18_19_coverage",
            "previous_day_admission_adult_covid_confirmed_20_29",
            "previous_day_admission_adult_covid_confirmed_20_29_coverage",
            "previous_day_admission_adult_covid_confirmed_30_39",
            "previous_day_admission_adult_covid_confirmed_30_39_coverage",
            "previous_day_admission_adult_covid_confirmed_40_49",
            "previous_day_admission_adult_covid_confirmed_40_49_coverage",
            "previous_day_admission_adult_covid_confirmed_50_59",
            "previous_day_admission_adult_covid_confirmed_50_59_coverage",
            "previous_day_admission_adult_covid_confirmed_60_69",
            "previous_day_admission_adult_covid_confirmed_60_69_coverage",
            "previous_day_admission_adult_covid_confirmed_70_79",
            "previous_day_admission_adult_covid_confirmed_70_79_coverage",
            "previous_day_admission_adult_covid_confirmed_80",
            "previous_day_admission_adult_covid_confirmed_80_coverage",
            "previous_day_admission_adult_covid_confirmed_unknown",
            "previous_day_admission_adult_covid_confirmed_unknown_coverage",
            "previous_day_admission_adult_covid_suspected_18_19",
            "previous_day_admission_adult_covid_suspected_18_19_coverage",
            "previous_day_admission_adult_covid_suspected_20_29",
            "previous_day_admission_adult_covid_suspected_20_29_coverage",
            "previous_day_admission_adult_covid_suspected_30_39",
            "previous_day_admission_adult_covid_suspected_30_39_coverage",
            "previous_day_admission_adult_covid_suspected_40_49",
            "previous_day_admission_adult_covid_suspected_40_49_coverage",
            "previous_day_admission_adult_covid_suspected_50_59",
            "previous_day_admission_adult_covid_suspected_50_59_coverage",
            "previous_day_admission_adult_covid_suspected_60_69",
            "previous_day_admission_adult_covid_suspected_60_69_coverage",
            "previous_day_admission_adult_covid_suspected_70_79",
            "previous_day_admission_adult_covid_suspected_70_79_coverage",
            "previous_day_admission_adult_covid_suspected_80_",
            "previous_day_admission_adult_covid_suspected_80_coverage",
            "previous_day_admission_adult_covid_suspected_unknown",
            "previous_day_admission_adult_covid_suspected_unknown_coverage",
            "deaths_covid", "deaths_covid_coverage",
            "on_hand_supply_therapeutic_a_casirivimab_imdevimab_courses",
            "on_hand_supply_therapeutic_b_bamlanivimab_courses",
            "on_hand_supply_therapeutic_c_bamlanivimab_etesevimab_courses",
            "previous_week_therapeutic_a_casirivimab_imdevimab_courses_used",
            "previous_week_therapeutic_b_bamlanivimab_courses_used",
            "previous_week_therapeutic_c_bamlanivimab_etesevimab_courses_used",
            "icu_patients_confirmed_influenza",
            "icu_patients_confirmed_influenza_coverage",
            "previous_day_admission_influenza_confirmed",
            "previous_day_admission_influenza_confirmed_coverage",
            "previous_day_deaths_covid_and_influenza",
            "previous_day_deaths_covid_and_influenza_coverage",
            "previous_day_deaths_influenza",
            "previous_day_deaths_influenza_coverage",
            "total_patients_hospitalized_confirmed_influenza",
            "total_patients_hospitalized_confirmed_influenza_and_covid",
            "total_patients_hospitalized_confirmed_influenza_and_covid_coverage",
            "total_patients_hospitalized_confirmed_influenza_coverage",
            "all_pediatric_inpatient_bed_occupied",
            "all_pediatric_inpatient_bed_occupied_coverage",
            "all_pediatric_inpatient_beds",
            "all_pediatric_inpatient_beds_coverage",
            "previous_day_admission_pediatric_covid_confirmed_0_4",
            "previous_day_admission_pediatric_covid_confirmed_0_4_coverage",
            "previous_day_admission_pediatric_covid_confirmed_12_17",
            "previous_day_admission_pediatric_covid_confirmed_12_17_coverage",
            "previous_day_admission_pediatric_covid_confirmed_5_11",
            "previous_day_admission_pediatric_covid_confirmed_5_11_coverage",
            "previous_day_admission_pediatric_covid_confirmed_unknown",
            "previous_day_admission_pediatric_covid_confirmed_unknown_coverage",
            "staffed_icu_pediatric_patients_confirmed_covid",
            "staffed_icu_pediatric_patients_confirmed_covid_coverage",
            "staffed_pediatric_icu_bed_occupancy",
            "staffed_pediatric_icu_bed_occupancy_coverage",
            "total_staffed_pediatric_icu_beds",
            "total_staffed_pediatric_icu_beds_coverage",
        ),
        # VERIFIED LIVE: zero duplicate (state, date) pairs.
        pk_fields=("state", "date"),
        date_field="date",
        join_keys=("state",),
        refresh_cadence="static",
        page_size=500,
    ),
    EndpointSpec(
        key="covid_pcr_testing",
        resource_id="j8mb-icvb",
        kind="curated",
        target_table="hhs_covid_pcr_testing",
        title="COVID-19 Diagnostic Laboratory Testing (PCR Testing) Time Series",
        # 242,970 rows live; state × date × outcome grain (Positive /
        # Negative / Inconclusive). The national lab-testing series whose
        # home is healthdata.gov (not a CDC mirror).
        columns=(
            "state", "state_name", "state_fips", "fema_region",
            "overall_outcome", "date", "new_results_reported",
            "total_results_reported", "geocoded_state",
        ),
        # VERIFIED LIVE: zero duplicate (state, date, overall_outcome).
        pk_fields=("state", "date", "overall_outcome"),
        date_field="date",
        join_keys=("state",),
        refresh_cadence="static",
    ),
    EndpointSpec(
        key="community_profile_county",
        resource_id="di4u-7yu6",
        kind="curated",
        target_table="hhs_community_profile_county",
        title="COVID-19 Community Profile Report - County-Level",
        # 3,294 rows live — the FINAL snapshot (every county, single
        # date 2023-05-10): cases, deaths, testing, hospital utilization
        # and vaccination per county FIPS in one row. The White House /
        # HHS Community Profile Report's county sheet, native here.
        columns=(
            "fips", "county", "state", "fema_region", "date",
            "cases_last_7_days", "cases_per_100k_last_7_days", "total_cases",
            "cases_pct_change_from_prev_week", "deaths_last_7_days",
            "deaths_per_100k_last_7_days", "total_deaths",
            "deaths_pct_change_from_prev_week",
            "test_positivity_rate_last_7_days",
            "total_positive_tests_last_7_days", "total_tests_last_7_days",
            "total_tests_per_100k_last_7_days",
            "test_positivity_rate_pct_change_from_prev_week",
            "total_tests_pct_change_from_prev_week",
            "confirmed_covid_hosp_last_7_days",
            "confirmed_covid_hosp_per_100_beds_last_7_days",
            "confirmed_covid_hosp_per_100_beds_pct_change_from_prev_week",
            "suspected_covid_hosp_last_7_days",
            "suspected_covid_hosp_per_100_beds_last_7_days",
            "suspected_covid_hosp_per_100_beds_pct_change_from_prev_week",
            "pct_inpatient_beds_used_avg_last_7_days",
            "pct_inpatient_beds_used_abs_change_from_prev_week",
            "pct_inpatient_beds_used_covid_avg_last_7_days",
            "pct_inpatient_beds_used_covid_abs_change_from_prev_week",
            "pct_icu_beds_used_avg_last_7_days",
            "pct_icu_beds_used_abs_change_from_prev_week",
            "pct_icu_beds_used_covid_avg_last_7_days",
            "pct_icu_beds_used_covid_abs_change_from_prev_week",
            "pct_vents_used_avg_last_7_days",
            "pct_vents_used_abs_change_from_prev_week",
            "pct_vents_used_covid_avg_last_7_days",
            "pct_vents_used_covid_abs_change_from_prev_week",
            "pct_fully_vacc_total_pop", "pct_fully_vacc_65_and_older",
        ),
        # VERIFIED LIVE: zero duplicate (fips, date) pairs.
        pk_fields=("fips", "date"),
        date_field="date",
        join_keys=("fips",),
        refresh_cadence="static",
    ),
    EndpointSpec(
        key="covid_therapeutics_locator",
        resource_id="rxn6-qnx8",
        kind="curated",
        target_table="hhs_covid_therapeutics_locator",
        title="COVID-19 Public Therapeutic Locator",
        # 69,184 rows live; dispensing-location × NDC grain, with NPI —
        # joins to the estate's npi_registry slice. ASPR's public
        # therapeutics availability file (Paxlovid/Lagevrio courses),
        # native here.
        columns=(
            "provider_name", "address1", "address2", "city", "county",
            "state_code", "zip", "national_drug_code", "order_label",
            "courses_available", "geocoded_address", "npi",
            "last_report_date", "provider_status", "provider_note",
        ),
        # VERIFIED LIVE: the intuitive (provider_name, address1, ndc) key
        # duplicates (e.g. two Kaiser pharmacies in one building differing
        # only in address2) — the full 7-field address+NDC compose is the
        # first duplicate-free grain.
        pk_fields=("provider_name", "address1", "address2", "city",
                   "state_code", "zip", "national_drug_code"),
        date_field="last_report_date",
        join_keys=("npi",),
        refresh_cadence="static",
    ),
    EndpointSpec(
        key="hospital_ids",
        resource_id="vz64-k9wr",
        kind="curated",
        target_table="hhs_hospital_ids",
        title="HHS IDs",
        # 7,621 rows live; one row per HHS Protect facility id with its
        # CCN, name, address and county FIPS — the identifier crosswalk
        # that bridges the facility capacity table to every CCN-keyed
        # dataset in the estate (Care Compare, cost reports, ...).
        columns=(
            "hhs_id", "ccn", "facility_name", "address", "city", "zip",
            "fips_code", "state", "geohash", "geocoded_hospital_address",
        ),
        # VERIFIED LIVE: hhs_id is unique across all rows.
        pk_fields=("hhs_id",),
        date_field="",
        join_keys=("ccn",),
        refresh_cadence="static",
    ),
    EndpointSpec(
        key="school_learning_modalities",
        resource_id="aitj-yx37",
        kind="curated",
        target_table="hhs_school_learning_modalities",
        title="School Learning Modalities, 2021-2022",
        # 994,788 rows live; school-district × week grain (NCES district
        # id): In Person / Hybrid / Remote status through the 2021-22
        # school year.
        columns=(
            "district_nces_id", "district_name", "week", "learning_modality",
            "operational_schools", "student_count", "city", "state",
            "zip_code",
        ),
        # VERIFIED LIVE: zero duplicate (district_nces_id, week) pairs.
        pk_fields=("district_nces_id", "week"),
        date_field="week",
        join_keys=("district_nces_id",),
        refresh_cadence="static",
    ),
    EndpointSpec(
        key="covid_policy_orders",
        resource_id="gyqz-9u7n",
        kind="curated",
        target_table="hhs_covid_policy_orders",
        title="COVID-19 State and County Policy Orders",
        # 4,218 rows live; state/county policy actions (masking, closures,
        # phase changes) with start/stop dates — the policy timeline that
        # contextualizes the capacity + testing series.
        columns=(
            "state_id", "county", "fips_code", "policy_level", "date",
            "policy_type", "start_stop", "comments", "source",
            "total_phases", "geocoded_state",
        ),
        # VERIFIED LIVE: the shorter 6-field grain duplicates (same
        # county/date/type rows differing only in comments/source), so
        # those two ride in the key. Long keys, but deterministic and
        # duplicate-free — grain verified live with $group/$having.
        pk_fields=("state_id", "county", "fips_code", "policy_level",
                   "date", "policy_type", "start_stop", "comments",
                   "source"),
        date_field="date",
        join_keys=("state_id", "fips_code"),
        refresh_cadence="static",
    ),
]

# ── the generic on-demand escape hatch ────────────────────────────────
_GENERIC: List[EndpointSpec] = [
    EndpointSpec(
        key="fetched_rows",
        resource_id="",
        kind="generic",
        target_table="healthdata_gov_rows",
        title="Generic on-demand rows from any healthdata.gov 4x4 dataset",
        pk_fields=("dataset_key", "row_idx"),
        date_field="fetched_at",
        join_keys=("dataset_key",),
        refresh_cadence="on_demand",
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {
    s.key: s for s in (_CATALOG + _CURATED + _GENERIC)
}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown healthdata_gov endpoint {key!r}; known: "
            f"{sorted(ENDPOINTS)}"
        ) from exc


def curated_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.kind == "curated"]


def catalog_endpoint() -> EndpointSpec:
    return ENDPOINTS["catalog"]


def generic_endpoint() -> EndpointSpec:
    return ENDPOINTS["fetched_rows"]
