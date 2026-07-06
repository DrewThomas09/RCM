"""Declarative specs for every data.medicaid.gov dataset this connector ingests.

One :class:`EndpointSpec` per registered dataset. The spec is the single
place that knows the DKAN-specific quirks: the dataset's metastore
``identifier`` (a UUID), which canonical table the normalizer writes
into, the ordered fields the composed upsert key is built from, and the
date field used for recency sorting. The registry rows
(:mod:`connectors.medicaid_data.registry`) and the connector both read
these — adding or retuning a dataset is a data edit here, never new
routing logic elsewhere.

Three endpoint kinds, mirroring the estate's catalog-connector pattern:

``catalog``
    The DKAN metastore itself (``/api/1/metastore/schemas/dataset/items``)
    — all 541 datasets on data.medicaid.gov, synced into
    ``medicaid_data_catalog`` so "every dataset connected" is literally a
    table you can query.
``datastore``
    A curated flagship dataset with a first-class canonical table whose
    columns were snapshotted from a LIVE sample of
    ``/api/1/datastore/query/{identifier}/0`` (probed 2026-07-06; DKAN
    already returns lower-snake-case column names, so the live names are
    used verbatim). The per-year NADAC and SDUD files share one physical
    table each, sliced by ``source_endpoint`` — the estate's documented
    shared-table + ``source_filter`` pattern.
``generic``
    The escape hatch: any of the 541 catalog datasets can be pulled on
    demand into ``medicaid_data_rows`` (row JSON keyed by
    ``{dataset_key}:{row_idx}``) without a schema edit.

Identifier churn note: year-versioned families (NADAC per year, SDUD per
year, blood-disorder pricing per snapshot date) get a NEW UUID per
release. The curated rows below pin the identifiers verified live on
2026-07-06; future years are reachable immediately via the generic
``fetched_rows`` path and can be promoted to curated rows with a one-line
spec addition. The date-versioned "Pricing Comparison for Blood Disorder
Treatments" snapshots were deliberately left generic-only for that reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_MEDICAID_DATA_BASE = "https://data.medicaid.gov"

# DKAN route templates (verified live 2026-07-06).
CATALOG_PATH = "/api/1/metastore/schemas/dataset/items"
DATASTORE_PATH_TEMPLATE = "/api/1/datastore/query/{identifier}/0"


@dataclass(frozen=True)
class EndpointSpec:
    """One data.medicaid.gov dataset.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix and
        the value written into each row's ``source_endpoint`` column so
        datasets sharing a table stay individually queryable.
    identifier:
        The DKAN metastore UUID (empty for the catalog itself and for the
        generic rows pseudo-dataset).
    title:
        The dataset's live title, kept verbatim for provenance.
    kind:
        ``catalog`` | ``datastore`` | ``generic`` — drives which fetch
        path and normalizer mapper runs.
    target_table:
        Canonical table the normalizer upserts into.
    id_fields:
        Ordered raw-row fields the composed upsert key is built from
        (always prefixed with ``key`` in the normalizer so shared tables
        can never collide across year slices).
    date_field:
        Column used for recency ordering / registry ``date_field``.
    """

    key: str
    identifier: str
    title: str
    kind: str
    target_table: str
    id_fields: Tuple[str, ...] = ()
    date_field: str = ""
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "monthly"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"medicaid_data_{self.key}"

    @property
    def base_url(self) -> str:
        return _MEDICAID_DATA_BASE

    @property
    def path(self) -> str:
        """The URL path this spec fetches (template kept for generic)."""
        if self.kind == "catalog":
            return CATALOG_PATH
        if self.kind == "generic":
            return DATASTORE_PATH_TEMPLATE
        return DATASTORE_PATH_TEMPLATE.format(identifier=self.identifier)


_SPECS: List[EndpointSpec] = [
    # ── the catalog itself ────────────────────────────────────────────
    EndpointSpec(
        key="catalog",
        identifier="",
        title="data.medicaid.gov dataset catalog (DKAN metastore)",
        kind="catalog",
        target_table="medicaid_data_catalog",
        id_fields=("identifier",),
        date_field="modified",
        join_keys=("identifier",),
        refresh_cadence="weekly",
    ),
    # ── NADAC: per-year datasets, ONE shared table (source_endpoint slices) ─
    EndpointSpec(
        key="nadac_2026",
        identifier="fbb83258-11c7-47f5-8b18-5f8e79f7e704",
        title="NADAC (National Average Drug Acquisition Cost) 2026",
        kind="datastore",
        target_table="medicaid_nadac",
        # Weekly files re-list an (ndc, effective_date) pair in every
        # snapshot where the rate is still current, so as_of_date must be
        # part of the key or upserts would silently collapse snapshots.
        id_fields=("ndc", "effective_date", "as_of_date"),
        date_field="as_of_date",
        join_keys=("ndc",),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="nadac_2025",
        identifier="f38d0706-1239-442c-a3cc-40ef1b686ac0",
        title="NADAC (National Average Drug Acquisition Cost) 2025",
        kind="datastore",
        target_table="medicaid_nadac",
        id_fields=("ndc", "effective_date", "as_of_date"),
        date_field="as_of_date",
        join_keys=("ndc",),
        refresh_cadence="annual",       # closed year, corrections only
    ),
    # ── SDUD: per-year datasets, ONE shared table ─────────────────────
    EndpointSpec(
        key="sdud_2025",
        identifier="158a1baa-5506-400a-8ec3-97756f0b0536",
        title="State Drug Utilization Data 2025",
        kind="datastore",
        target_table="medicaid_sdud",
        id_fields=("utilization_type", "state", "ndc", "year", "quarter"),
        date_field="year",
        join_keys=("state", "ndc"),
        refresh_cadence="quarterly",
    ),
    EndpointSpec(
        key="sdud_2024",
        identifier="61729e5a-7aa8-448c-8903-ba3e0cd0ea3c",
        title="State Drug Utilization Data 2024",
        kind="datastore",
        target_table="medicaid_sdud",
        id_fields=("utilization_type", "state", "ndc", "year", "quarter"),
        date_field="year",
        join_keys=("state", "ndc"),
        refresh_cadence="annual",       # closed year, corrections only
    ),
    # ── Drug rebate program dimension ─────────────────────────────────
    EndpointSpec(
        key="drug_products_rebate",
        identifier="0ad65fe5-3ad3-5d79-a3f9-7893ded7963a",
        title="Drug Products in the Medicaid Drug Rebate Program",
        kind="datastore",
        target_table="medicaid_rebate_drug_product",
        # Live sample shows one row per NDC per (year, quarter) release,
        # not per NDC — 1.95M rows with year/quarter columns.
        id_fields=("ndc", "year", "quarter"),
        date_field="year",
        join_keys=("ndc",),
        refresh_cadence="quarterly",
    ),
    # ── Enrollment ────────────────────────────────────────────────────
    EndpointSpec(
        key="enrollment_new_adult_group",
        identifier="6c114b2c-cb83-559b-832f-4d8b06d6c1b9",
        title="Medicaid Enrollment - New Adult Group",
        kind="datastore",
        target_table="medicaid_enrollment_new_adult_group",
        # A report period can appear once per update cycle; both period
        # and update stamps are needed for a stable natural key.
        id_fields=("state", "enrollment_year", "enrollment_month",
                   "updated_year", "updated_month"),
        date_field="enrollment_year",
        join_keys=("state",),
        refresh_cadence="monthly",
    ),
    EndpointSpec(
        key="enrollment_monthly",
        identifier="6165f45b-ca93-5bb5-9d06-db29c692a360",
        title=("State Medicaid and CHIP Applications, Eligibility "
               "Determinations, and Enrollment Data"),
        kind="datastore",
        target_table="medicaid_enrollment_monthly",
        # Preliminary (P) and updated (U) rows coexist for one period.
        id_fields=("state_abbreviation", "reporting_period",
                   "preliminary_or_updated"),
        date_field="reporting_period",
        join_keys=("state_abbreviation",),
        refresh_cadence="monthly",
    ),
    # ── Managed care ──────────────────────────────────────────────────
    EndpointSpec(
        key="managed_care_by_state_2024",
        identifier="ef16c490-861a-4b1f-9e6d-f321abdcaab1",
        title="2024 Managed Care Programs By State",
        kind="datastore",
        target_table="medicaid_managed_care_program",
        # 'features' is the program name column in the live sample.
        id_fields=("state", "features", "program_type"),
        date_field="program_start_date",
        join_keys=("state",),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="mc_enrollment_summary",
        identifier="52ed908b-0cb8-5dd2-846d-99d4af12b369",
        title="Managed Care Enrollment Summary",
        kind="datastore",
        target_table="medicaid_mc_enrollment_summary",
        id_fields=("state", "year"),
        date_field="year",
        join_keys=("state",),
        refresh_cadence="annual",
    ),
    # ── Drug pricing references ───────────────────────────────────────
    EndpointSpec(
        key="aca_federal_upper_limits",
        identifier="ce4cf49b-a21b-5a53-bbc3-509414940847",
        title="ACA Federal Upper Limits",
        kind="datastore",
        # Monthly FUL files: one row per NDC per (year, month) release.
        target_table="medicaid_aca_ful",
        id_fields=("ndc", "year", "month"),
        date_field="year",
        join_keys=("ndc",),
        refresh_cadence="monthly",
    ),
    EndpointSpec(
        key="nadac_comparison",
        identifier="a217613c-12bc-5137-8b3a-ada0e4dad1ff",
        title="NADAC Comparison",
        kind="datastore",
        target_table="medicaid_nadac_comparison",
        id_fields=("ndc", "effective_date", "start_date", "end_date",
                   "primary_reason"),
        date_field="effective_date",
        join_keys=("ndc",),
        refresh_cadence="weekly",
    ),
    # ── Financial + quality ───────────────────────────────────────────
    EndpointSpec(
        key="financial_management_data",
        identifier="5b19d1d4-ae43-5fcd-ba14-3cecd99f473f",
        title="Medicaid Financial Management Data",
        kind="datastore",
        target_table="medicaid_financial_management",
        id_fields=("state", "year", "program", "service_category"),
        date_field="year",
        join_keys=("state",),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="quality_measures_2024",
        identifier="a5023394-ab10-465b-bb4a-7de5ac98d90c",
        title="2024 Child and Adult Health Care Quality Measures",
        kind="datastore",
        target_table="medicaid_quality_measure",
        # rate_definition disambiguates multiple published rates for one
        # (measure, population) pair in the live sample.
        id_fields=("state", "core_set_year", "reporting_program",
                   "measure_abbreviation", "population", "rate_definition"),
        date_field="core_set_year",
        join_keys=("state",),
        refresh_cadence="annual",
    ),
    # ── generic escape hatch: any of the 541 catalog datasets ─────────
    EndpointSpec(
        key="fetched_rows",
        identifier="",
        title="Generic fetched rows (any data.medicaid.gov datastore)",
        kind="generic",
        target_table="medicaid_data_rows",
        id_fields=("dataset_key", "row_idx"),
        date_field="fetched_at",
        join_keys=("dataset_key",),
        refresh_cadence="on_demand",
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {s.key: s for s in _SPECS}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown medicaid_data endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def datastore_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.kind == "datastore"]


def datastore_path(identifier: str) -> str:
    """The DKAN datastore query path for an arbitrary dataset UUID."""
    return DATASTORE_PATH_TEMPLATE.format(identifier=identifier)
