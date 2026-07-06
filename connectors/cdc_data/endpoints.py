"""Declarative specs for every data.cdc.gov dataset this connector ingests.

One :class:`EndpointSpec` per dataset. The spec is the single place that
knows the Socrata-specific quirks: the 4x4 resource id, the live-sampled
column snapshot the canonical table is derived from, the fields the
idempotent upsert key composes from, and the paging posture (page size,
date field, cadence).

Why specs and not code branches: adding or retuning a dataset is a data
edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.cdc_data.registry`), the tables
(:mod:`connectors.cdc_data.tables`) and the connector all read these.

Three dataset kinds:

  ``catalog``   — the full data.cdc.gov catalog itself, synced from the
                  Socrata metadata API (``/api/views/metadata/v1``). This
                  is what makes "every CDC dataset connected" true: every
                  4x4 on the domain lands as a row in ``cdc_data_catalog``.
  ``curated``   — flagship datasets promoted to first-class canonical
                  tables. Each 4x4 id was VERIFIED LIVE on 2026-07-06 via
                  ``/resource/{id}.json?$limit=1`` and each ``columns``
                  tuple is a snapshot of the live field names from
                  ``/api/views/{id}.json`` (Socrata JSON rows omit null
                  fields, so sampling rows alone under-reports columns).
  ``generic``   — the on-demand escape hatch: ANY 4x4 on the domain can be
                  pulled with ``connector.fetch_dataset()`` into the
                  ``cdc_data_rows`` JSON-blob table and still be queried
                  through the uniform engine.

Two ids in the original assignment did not survive live verification and
were substituted after searching the catalog by name:

  * ``pj7m-y5uh`` exists but is "Provisional COVID-19 Deaths: Distribution
    of Deaths by Race and Hispanic Origin", NOT the U.S. Chronic Disease
    Indicators — the correct CDI id is ``hksd-2xuw``.
  * ``ikd3-hr7f`` 404s — the live life-expectancy dataset is
    ``5h56-n989`` ("U.S. Life Expectancy at Birth by State and Census
    Tract - 2010-2015", tract grain with "(blank)" county rows carrying
    the state aggregate).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_CDC_DATA_BASE = "https://data.cdc.gov"

# The Socrata catalog metadata endpoint. VERIFIED LIVE: it pages by
# ``limit`` + 1-based ``page`` (the documented ``offset`` param is
# silently IGNORED on this domain — offset paging returns page 1 forever,
# which would loop an ingest). Stop on a short/empty page.
CATALOG_PATH = "/api/views/metadata/v1"


@dataclass(frozen=True)
class EndpointSpec:
    """One data.cdc.gov dataset.

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
        The dataset's live name on data.cdc.gov (documentation only).
    columns:
        Snapshot of the live column field names (already lowercase
        snake_case in Socrata JSON) that the canonical table carries.
        Empty for catalog/generic, whose tables are hand-shaped.
    pk_fields:
        Ordered raw fields the composed upsert key is built from in
        :mod:`connectors.cdc_data.normalize` (``"a:b:c"``). Missing
        fields compose as ``""`` so sparse rows still key stably.
    date_field:
        Column used for recency ordering / registry ``date_field``.
    page_size:
        Polite per-request ``$limit`` for this dataset (BRFSS is huge, so
        it pages smaller by default).
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
    refresh_cadence: str = "annual"
    page_size: int = 1000
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"cdc_data_{self.key}"

    @property
    def base_url(self) -> str:
        return _CDC_DATA_BASE

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
        target_table="cdc_data_catalog",
        title="data.cdc.gov dataset catalog (Socrata metadata API)",
        pk_fields=("id",),
        date_field="data_updated_at",
        join_keys=("dataset_uid",),
        refresh_cadence="weekly",
        page_size=500,
    ),
]

# ── curated flagship datasets (all 4x4 ids verified live 2026-07-06) ──
_CURATED: List[EndpointSpec] = [
    EndpointSpec(
        key="places_county",
        resource_id="swc5-untb",
        kind="curated",
        target_table="cdc_places_county",
        title="PLACES: Local Data for Better Health, County Data (latest release)",
        columns=(
            "year", "stateabbr", "statedesc", "locationname", "datasource",
            "category", "measure", "data_value_unit", "data_value_type",
            "data_value", "data_value_footnote_symbol", "data_value_footnote",
            "low_confidence_limit", "high_confidence_limit", "totalpopulation",
            "totalpop18plus", "locationid", "categoryid", "measureid",
            "datavaluetypeid", "short_question_text", "geolocation",
        ),
        # locationid is the 5-digit county FIPS; datavaluetypeid (CrdPrv /
        # AgeAdjPrv) keys the data_value_type dimension the assignment named.
        pk_fields=("stateabbr", "locationid", "measureid", "datavaluetypeid"),
        date_field="year",
        join_keys=("stateabbr", "locationid"),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="provisional_deaths_state",
        resource_id="9bhg-hcku",
        kind="curated",
        target_table="cdc_provisional_deaths_state",
        title="Provisional COVID-19 Deaths by Sex and Age",
        columns=(
            # Live field "group" is an SQL keyword; the documented
            # to_column() rule renames it group_field (see flatten.py).
            "data_as_of", "start_date", "end_date", "group_field", "year",
            "month", "state", "sex", "age_group", "covid_19_deaths",
            "total_deaths", "pneumonia_deaths",
            "pneumonia_and_covid_19_deaths", "influenza_deaths",
            "pneumonia_influenza_or_covid", "footnote",
        ),
        # The live schema has no single "period" column; the reporting
        # period the assignment meant is the (group, year, month) triple.
        pk_fields=("group_field", "year", "month", "state", "sex",
                   "age_group"),
        date_field="end_date",
        join_keys=("state",),
        refresh_cadence="monthly",
    ),
    EndpointSpec(
        key="vsrr_drug_overdose",
        resource_id="xkb8-kh2a",
        kind="curated",
        target_table="cdc_vsrr_drug_overdose",
        title="VSRR Provisional Drug Overdose Death Counts",
        columns=(
            "state", "year", "month", "period", "indicator", "data_value",
            "percent_complete", "percent_pending_investigation", "state_name",
            "footnote", "footnote_symbol", "predicted_value",
        ),
        pk_fields=("state", "year", "month", "indicator"),
        date_field="year",
        join_keys=("state",),
        refresh_cadence="monthly",
    ),
    EndpointSpec(
        key="nchs_leading_causes",
        resource_id="bi63-dtpu",
        kind="curated",
        target_table="cdc_nchs_leading_causes",
        title="NCHS - Leading Causes of Death: United States",
        columns=(
            "year", "_113_cause_name", "cause_name", "state", "deaths", "aadr",
        ),
        pk_fields=("year", "state", "cause_name"),
        date_field="year",
        join_keys=("state",),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="weekly_deaths_by_cause",
        resource_id="u6jv-9ijr",
        kind="curated",
        target_table="cdc_weekly_deaths_by_cause",
        title="Weekly Provisional Counts of Deaths by State and Select Causes",
        columns=(
            "jurisdiction", "week_ending_date", "state_abbreviation",
            "mmwryear", "mmwrweek", "cause_group", "number_of_deaths",
            "cause_subgroup", "time_period", "suppress", "note",
            "average_number_of_deaths", "difference_from_2015_2019_to_2020",
            "percent_difference_from_15_19_to_20", "type",
        ),
        # (state, week) alone under-keys: each week carries one row per
        # cause subgroup per estimate type (Predicted vs Unweighted).
        pk_fields=("state_abbreviation", "mmwryear", "mmwrweek",
                   "cause_subgroup", "type"),
        date_field="week_ending_date",
        join_keys=("state_abbreviation",),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="brfss_prevalence",
        resource_id="dttw-5yxu",
        kind="curated",
        target_table="cdc_brfss_prevalence",
        title="BRFSS Prevalence and Trends Data",
        columns=(
            "year", "locationabbr", "locationdesc", "class", "topic",
            "question", "response", "break_out", "break_out_category",
            "sample_size", "data_value", "confidence_limit_low",
            "confidence_limit_high", "display_order", "data_value_unit",
            "data_value_type", "data_value_footnote_symbol",
            "data_value_footnote", "datasource", "classid", "topicid",
            "locationid", "breakoutid", "breakoutcategoryid", "questionid",
            "responseid", "geolocation",
        ),
        pk_fields=("year", "locationabbr", "classid", "topicid", "questionid",
                   "responseid", "breakoutid"),
        date_field="year",
        join_keys=("locationabbr",),
        refresh_cadence="annual",
        # ~2M rows live — keep pages small so the default 5-page cap stays
        # a genuinely modest pull.
        page_size=500,
    ),
    EndpointSpec(
        key="chronic_disease_indicators",
        resource_id="hksd-2xuw",   # assignment guessed pj7m-y5uh (wrong dataset)
        kind="curated",
        target_table="cdc_chronic_disease_indicators",
        title="U.S. Chronic Disease Indicators",
        columns=(
            "yearstart", "yearend", "locationabbr", "locationdesc",
            "datasource", "topic", "question", "response", "datavalueunit",
            "datavaluetype", "datavalue", "datavaluealt",
            "datavaluefootnotesymbol", "datavaluefootnote",
            "lowconfidencelimit", "highconfidencelimit",
            "stratificationcategory1", "stratification1",
            "stratificationcategory2", "stratification2",
            "stratificationcategory3", "stratification3", "geolocation",
            "locationid", "topicid", "questionid", "responseid",
            "datavaluetypeid", "stratificationcategoryid1",
            "stratificationid1", "stratificationcategoryid2",
            "stratificationid2", "stratificationcategoryid3",
            "stratificationid3",
        ),
        pk_fields=("yearstart", "yearend", "locationabbr", "questionid",
                   "responseid", "datavaluetypeid", "stratificationid1"),
        date_field="yearend",
        join_keys=("locationabbr",),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="life_expectancy_tract",
        resource_id="5h56-n989",   # assignment's ikd3-hr7f 404s live
        kind="curated",
        target_table="cdc_life_expectancy_tract",
        title="U.S. Life Expectancy at Birth by State and Census Tract - 2010-2015",
        columns=(
            "state_name", "county_name", "full_ct_num", "le", "le_range",
            "se_le",
        ),
        # county_name "(blank)" rows carry the state aggregate; full_ct_num
        # is absent there — composing with "" keeps those rows keyed.
        pk_fields=("state_name", "county_name", "full_ct_num"),
        date_field="",
        join_keys=("state_name", "county_name"),
        refresh_cadence="static",
    ),
    EndpointSpec(
        key="drug_poisoning_county",
        resource_id="rpvx-m2md",   # most recently updated county vintage
        kind="curated",
        target_table="cdc_drug_poisoning_county",
        title="NCHS - Drug Poisoning Mortality by County: United States",
        columns=(
            "fips", "year", "state", "fipsstate", "county", "population",
            "model_based_death_rate", "standard_deviation", "lower95ci",
            "upper95ci", "urbanrural", "censusdivision",
        ),
        pk_fields=("fips", "year"),
        date_field="year",
        join_keys=("fips",),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="heart_disease_mortality_county",
        resource_id="th8y-thx5",   # 2021-2023 vintage, latest live release
        kind="curated",
        target_table="cdc_heart_disease_mortality",
        title=("Heart Disease Mortality Data Among US Adults (35+) by "
               "State/Territory and County - 2021-2023"),
        columns=(
            "year", "locationabbr", "locationdesc", "geographiclevel",
            "datasource", "class", "topic", "data_value", "data_value_unit",
            "data_value_type", "data_value_footnote_symbol",
            "data_value_footnote", "stratificationcategory1",
            "stratification1", "stratificationcategory2", "stratification2",
            "topicid", "locationid", "y_lat", "x_lon",
        ),
        pk_fields=("locationid", "year", "stratification1", "stratification2"),
        date_field="year",
        join_keys=("locationid",),
        refresh_cadence="annual",
    ),
]

# ── the generic on-demand escape hatch ────────────────────────────────
_GENERIC: List[EndpointSpec] = [
    EndpointSpec(
        key="fetched_rows",
        resource_id="",
        kind="generic",
        target_table="cdc_data_rows",
        title="Generic on-demand rows from any data.cdc.gov 4x4 dataset",
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
            f"unknown cdc_data endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def curated_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.kind == "curated"]


def catalog_endpoint() -> EndpointSpec:
    return ENDPOINTS["catalog"]


def generic_endpoint() -> EndpointSpec:
    return ENDPOINTS["fetched_rows"]
