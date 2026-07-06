"""Declarative specs for every Provider Data Catalog dataset this connector ingests.

One :class:`EndpointSpec` per registered dataset. The spec is the single
place that knows PDC-specific quirks: the DKAN 4x4 identifier the
datastore is queried by, the raw field names that compose the idempotent
upsert key, the canonical table the normalizer writes into, and the page
size a polite ingest should use.

Why specs and not code branches: adding or retuning a dataset is a data
edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.provider_data.registry`), the normalizer and the
connector all read these.

The CMS Provider Data Catalog (``data.cms.gov/provider-data``) is a DKAN
open-data catalog of 234 Care Compare datasets (verified live
2026-07-06). We register three kinds of dataset:

  * ``catalog`` — the full metastore catalog itself (every dataset's id,
    title, theme, modified date, CSV url …), synced by ``discover()``;
  * 34 CURATED flagship Care Compare datasets — each a first-class
    canonical table whose columns were locked from a live sample of the
    real datastore (see ``tables._CURATED_COLUMNS``);
  * ``fetched_rows`` — a generic rows table so *any* of the 234 catalog
    datasets can be pulled on demand by its 4x4 identifier and still be
    queryable through the uniform engine.

Identifier shapes: most datasets use DKAN 4x4 identifiers
(``xubh-q36u``), but the ESRD QIP payment-year files use bare SLUGS
(``complete_qip_data``, ``tps``, ``pppw``) — verified live 2026-07-06
that the datastore accepts them at the same query path
(``/api/1/datastore/query/tps/0`` returns rows and a count exactly like
a 4x4). Slug-identified datasets are only reachable through their
curated endpoint keys: the generic 4x4 fall-through in
``connector.resolve`` deliberately rejects arbitrary strings so a typo'd
dataset name stays a KeyError instead of a speculative fetch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_PROVIDER_DATA_BASE = "https://data.cms.gov/provider-data"

# DKAN metastore path listing every dataset (a JSON array, ~234 items).
CATALOG_PATH = "/api/1/metastore/schemas/dataset/items"


def datastore_path(identifier: str) -> str:
    """The DKAN datastore query path for a dataset's first distribution.

    Index ``0`` is the dataset's only distribution on this catalog (each
    PDC dataset publishes exactly one CSV resource).
    """
    return f"/api/1/datastore/query/{identifier}/0"


@dataclass(frozen=True)
class EndpointSpec:
    """One Provider Data Catalog dataset.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix and
        the value written into each row's ``source_endpoint`` column.
    identifier:
        The DKAN dataset identifier — a 4x4 (e.g. ``xubh-q36u``) or, for
        the ESRD QIP payment-year files, a bare slug (e.g. ``tps``; see
        module docstring). Empty for the two meta datasets (``catalog``
        / ``fetched_rows``).
    kind:
        ``catalog`` | ``curated`` | ``generic``. Drives which normalizer
        mapper runs and how the connector fetches.
    target_table:
        Canonical table the normalizer upserts into.
    title:
        Human title (matches the catalog entry for curated datasets).
    pk_fields:
        Ordered snake_cased field names whose values compose the
        idempotent upsert key (built in the normalizer). Verified unique
        against a live sample on 2026-07-06.
    date_field:
        Field used for recency ordering / registry ``date_field``.
    page_size:
        Per-dataset polite page size override (``None`` → transport
        default). The DAC national file is ~3.4M rows, so it defaults
        small to keep accidental pulls cheap.
    """

    key: str
    identifier: str
    kind: str
    target_table: str
    title: str
    pk_fields: Tuple[str, ...] = ()
    date_field: Optional[str] = None
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "quarterly"
    default_params: Dict[str, str] = field(default_factory=dict)
    page_size: Optional[int] = None

    @property
    def dataset_id(self) -> str:
        return f"provider_data_{self.key}"

    @property
    def base_url(self) -> str:
        return _PROVIDER_DATA_BASE

    @property
    def path(self) -> str:
        """The API path this dataset is fetched from.

        The generic ``fetched_rows`` dataset has no identifier of its
        own — its path is a template filled per ``fetch_dataset`` call.
        """
        if self.kind == "catalog":
            return CATALOG_PATH
        if self.kind == "generic":
            return datastore_path("{identifier}")
        return datastore_path(self.identifier)


# ── the catalog itself ────────────────────────────────────────────────
_CATALOG = EndpointSpec(
    key="catalog",
    identifier="",
    kind="catalog",
    target_table="provider_data_catalog",
    title="CMS Provider Data Catalog — all datasets",
    pk_fields=("identifier",),
    date_field="modified",
    join_keys=("identifier",),
    refresh_cadence="weekly",
)

# ── curated Care Compare flagships ────────────────────────────────────
# pk_fields verified unique against a 500-row live sample per dataset
# (2026-07-06). Note nursing_home_penalties needs fine_id on top of the
# obvious ccn+date+type key — the live file has same-day duplicate fines.
_CURATED: List[EndpointSpec] = [
    EndpointSpec(
        key="hospital_general", identifier="xubh-q36u", kind="curated",
        target_table="hospital_general",
        title="Hospital General Information",
        pk_fields=("facility_id",),
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="hcahps_hospital", identifier="dgck-syfz", kind="curated",
        target_table="hcahps_hospital",
        title="Patient survey (HCAHPS) - Hospital",
        pk_fields=("facility_id", "hcahps_measure_id"),
        date_field="end_date",
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="complications_deaths_hospital", identifier="ynj2-r877",
        kind="curated", target_table="complications_deaths_hospital",
        title="Complications and Deaths - Hospital",
        pk_fields=("facility_id", "measure_id"),
        date_field="end_date",
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="timely_effective_care_hospital", identifier="yv7e-xc69",
        kind="curated", target_table="timely_effective_care_hospital",
        title="Timely and Effective Care - Hospital",
        pk_fields=("facility_id", "measure_id"),
        date_field="end_date",
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="unplanned_visits_hospital", identifier="632h-zaca",
        kind="curated", target_table="unplanned_visits_hospital",
        title="Unplanned Hospital Visits - Hospital",
        pk_fields=("facility_id", "measure_id"),
        date_field="end_date",
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="mspb_hospital", identifier="rrqw-56er", kind="curated",
        target_table="mspb_hospital",
        title="Medicare Spending Per Beneficiary - Hospital",
        pk_fields=("facility_id",),
        date_field="end_date",
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="imaging_efficiency_hospital", identifier="wkfw-kthe",
        kind="curated", target_table="imaging_efficiency_hospital",
        title="Outpatient Imaging Efficiency - Hospital",
        pk_fields=("facility_id", "measure_id"),
        date_field="end_date",
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="nursing_home_provider_info", identifier="4pq5-n9py",
        kind="curated", target_table="nursing_home_provider_info",
        title="Nursing homes including rehab services - Provider Information",
        pk_fields=("cms_certification_number_ccn",),
        date_field="processing_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="monthly",
    ),
    EndpointSpec(
        key="nursing_home_penalties", identifier="g6vv-u9sr",
        kind="curated", target_table="nursing_home_penalties",
        title="Nursing homes including rehab services - Penalties",
        pk_fields=("cms_certification_number_ccn", "penalty_date",
                   "penalty_type", "fine_id"),
        date_field="processing_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="monthly",
    ),
    EndpointSpec(
        key="mds_quality_measures", identifier="djen-97ju",
        kind="curated", target_table="mds_quality_measures",
        title="Nursing homes including rehab services - MDS Quality Measures",
        pk_fields=("cms_certification_number_ccn", "measure_code"),
        date_field="processing_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="monthly",
    ),
    EndpointSpec(
        key="snf_qrp_provider", identifier="fykj-qjee", kind="curated",
        target_table="snf_qrp_provider",
        title="SNF Quality Reporting Program - Provider Data",
        pk_fields=("cms_certification_number_ccn", "measure_code"),
        date_field="end_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="home_health_agencies", identifier="6jpm-sxkc", kind="curated",
        target_table="home_health_agencies",
        title="Home Health Care Agencies",
        pk_fields=("cms_certification_number_ccn",),
        date_field="certification_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="hospice_provider", identifier="252m-zfp9", kind="curated",
        target_table="hospice_provider",
        title="Hospice - Provider Data",
        pk_fields=("cms_certification_number_ccn", "measure_code"),
        date_field="measure_date_range",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="hospice_general", identifier="yc9t-dgbk", kind="curated",
        target_table="hospice_general",
        title="Hospice - General Information",
        pk_fields=("cms_certification_number_ccn",),
        date_field="certification_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="dialysis_facilities", identifier="23ew-n7w9", kind="curated",
        target_table="dialysis_facilities",
        title="Dialysis Facility - Listing by Facility",
        pk_fields=("cms_certification_number_ccn",),
        date_field="certification_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="irf_general", identifier="7t8x-u3ir", kind="curated",
        target_table="irf_general",
        title="Inpatient Rehabilitation Facility - General Information",
        pk_fields=("cms_certification_number_ccn",),
        date_field="certification_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="ltch_general", identifier="azum-44iv", kind="curated",
        target_table="ltch_general",
        title="Long-Term Care Hospital - General Information",
        pk_fields=("cms_certification_number_ccn",),
        date_field="certification_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="dac_national", identifier="mj5m-pzi6", kind="curated",
        target_table="dac_national",
        title="Doctors and Clinicians - National Downloadable File",
        # One row per clinician x organization x address. The 4-field key
        # covers both individual and organizational enrolments (verified
        # unique on a live sample; ~3.4M rows total).
        pk_fields=("npi", "ind_enrl_id", "org_pac_id", "adrs_id"),
        join_keys=("npi",),
        refresh_cadence="monthly",
        page_size=100,           # huge file: keep accidental pulls cheap
    ),
    # ── kidney / dialysis deep set (all keys verified unique against a
    # FULL live pull per dataset, 2026-07-06) ─────────────────────────
    EndpointSpec(
        key="dialysis_state_averages", identifier="2fpu-cgbb",
        kind="curated", target_table="dialysis_state_averages",
        title="Dialysis Facility - State Averages",
        pk_fields=("state",),           # 56/56 unique live
        join_keys=("state",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="dialysis_national_averages", identifier="2rkq-ygai",
        kind="curated", target_table="dialysis_national_averages",
        title="Dialysis Facility - National Averages",
        pk_fields=("country",),         # single live row, country="NATION"
        join_keys=("country",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="ich_cahps_facility", identifier="59mq-zhts", kind="curated",
        target_table="ich_cahps_facility",
        title="Patient survey (ICH CAHPS) - Facility",
        pk_fields=("cms_certification_number_ccn",),   # 7557/7557 unique
        date_field="ichcahps_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="ich_cahps_state", identifier="hanv-ru8h", kind="curated",
        target_table="ich_cahps_state",
        title="Patient survey (ICH CAHPS) - State",
        pk_fields=("state",),           # 56/56 unique live
        join_keys=("state",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="ich_cahps_national", identifier="utgq-v46w", kind="curated",
        target_table="ich_cahps_national",
        title="Patient survey (ICH CAHPS) - National",
        pk_fields=("country",),         # single live row, country="NATION"
        join_keys=("country",), refresh_cadence="quarterly",
    ),
    # The three ESRD QIP files below are the catalog's slug-identified
    # datasets (not 4x4s) — see the module docstring. One row per
    # facility CCN (7558/7558 unique on the full live files).
    EndpointSpec(
        key="esrd_qip_complete", identifier="complete_qip_data",
        kind="curated", target_table="esrd_qip_complete",
        title="ESRD QIP - Complete QIP Data - Payment Year 2026",
        pk_fields=("cms_certification_number_ccn",),
        date_field="cms_certification_date",
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="esrd_qip_tps", identifier="tps", kind="curated",
        target_table="esrd_qip_tps",
        title="ESRD QIP - Total Performance Scores - Payment Year 2026",
        pk_fields=("cms_certification_number_ccn",),
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="esrd_qip_pppw", identifier="pppw", kind="curated",
        target_table="esrd_qip_pppw",
        title="ESRD QIP - Percentage of Prevalent Patients Waitlisted - "
              "Payment Year 2026",
        pk_fields=("cms_certification_number_ccn",),
        join_keys=("cms_certification_number_ccn",),
        refresh_cadence="annual",
    ),
    # ── outpatient / ASC set ──────────────────────────────────────────
    EndpointSpec(
        key="asc_quality_facility", identifier="4jcv-atw7", kind="curated",
        target_table="asc_quality_facility",
        title="Ambulatory Surgical Center Quality Measures - Facility",
        # npi leads: 3 of 5711 live rows have an empty facility_id (their
        # npi is populated), and (facility_id, year) alone duplicates for
        # 98 shared-CCN pairs. (npi, facility_id, year) is 5711/5711
        # unique on the full live file.
        pk_fields=("npi", "facility_id", "year"),
        date_field="year",
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="asc_quality_state", identifier="axe7-s95e", kind="curated",
        target_table="asc_quality_state",
        title="Ambulatory Surgical Center Quality Measures - State",
        pk_fields=("state", "year"),    # 54/54 unique live
        date_field="year",
        join_keys=("state",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="asc_quality_national", identifier="wue8-3vwe", kind="curated",
        target_table="asc_quality_national",
        title="Ambulatory Surgical Center Quality Measures - National",
        pk_fields=("year",),            # single live row per year
        date_field="year",
        join_keys=("year",), refresh_cadence="quarterly",
    ),
    # OAS CAHPS: the catalog carries six files (ASC + HOPD, each at
    # facility/state/national grain). We curate the two the estate asked
    # for — 48nr-hqxx IS the ASC facility-level file and tf3h-mrrs its
    # national companion (titles verified in the live catalog, so they
    # are distinguishable, not duplicates).
    EndpointSpec(
        key="oas_cahps_asc_facility", identifier="48nr-hqxx",
        kind="curated", target_table="oas_cahps_asc_facility",
        title="Outpatient and Ambulatory Surgery Consumer Assessment of "
              "Healthcare Providers and Systems (OAS CAHPS) survey for "
              "ambulatory surgical centers - Facility",
        pk_fields=("facility_id",),     # 4633/4633 unique live
        date_field="end_date",
        join_keys=("facility_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="oas_cahps_asc_national", identifier="tf3h-mrrs",
        kind="curated", target_table="oas_cahps_asc_national",
        title="Outpatient and Ambulatory Surgery Consumer Assessment of "
              "Healthcare Providers and Systems (OAS CAHPS) survey for "
              "ambulatory surgical centers - National",
        # No id column on the live file — one row per survey window.
        pk_fields=("start_date", "end_date"),
        date_field="end_date",
        join_keys=("start_date", "end_date"),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="imaging_efficiency_state", identifier="if5v-4x48",
        kind="curated", target_table="imaging_efficiency_state",
        title="Outpatient Imaging Efficiency - State",
        pk_fields=("state", "measure_id"),   # 224/224 unique live
        date_field="end_date",
        join_keys=("state",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="imaging_efficiency_national", identifier="di9i-zzrc",
        kind="curated", target_table="imaging_efficiency_national",
        title="Outpatient Imaging Efficiency - National",
        pk_fields=("measure_id",),      # 4/4 unique live
        date_field="end_date",
        join_keys=("measure_id",), refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="medical_equipment_suppliers", identifier="ct36-nrcq",
        kind="curated", target_table="medical_equipment_suppliers",
        title="Medical Equipment Suppliers",
        pk_fields=("provider_id",),     # 57298/57298 unique live
        date_field="participationbegindate",
        join_keys=("provider_id",),
        refresh_cadence="weekly",       # catalog modified daily-ish live
    ),
]

# ── generic on-demand rows for any of the 234 catalog datasets ────────
_GENERIC = EndpointSpec(
    key="fetched_rows",
    identifier="",
    kind="generic",
    target_table="provider_data_rows",
    title="Provider Data Catalog — generic fetched rows (any dataset)",
    pk_fields=("dataset_key", "row_idx"),
    date_field="fetched_at",
    join_keys=("dataset_key",),
    refresh_cadence="on_demand",
)

ENDPOINTS: Dict[str, EndpointSpec] = {
    s.key: s for s in ([_CATALOG] + _CURATED + [_GENERIC])
}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown Provider Data endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def curated_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.kind == "curated"]


def by_identifier() -> Dict[str, EndpointSpec]:
    """Curated specs keyed by their DKAN 4x4 identifier."""
    return {s.identifier: s for s in ENDPOINTS.values() if s.identifier}
