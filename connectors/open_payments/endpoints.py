"""Declarative specs for every Open Payments dataset this connector ingests.

One :class:`EndpointSpec` per dataset. The spec is the single place that
knows Open-Payments-specific quirks: the DKAN dataset UUID the datastore
is queried by, the native id fields the idempotent upsert keys on
(``record_id`` for the detail payment files; composed natural keys for
the pre-aggregated summaries), the CLI filter aliases (``--state`` /
``--npi`` map onto different native columns per dataset), and the
canonical table the normalizer writes into.

Why specs and not code branches: adding or retuning a dataset is a data
edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.open_payments.registry`) and the connector both read
these.

Three kinds of spec:

  * ``catalog``   — the DKAN metastore list of all 74 Open Payments
                    datasets (one GET, no paging),
  * ``datastore`` — a curated dataset queried through the DKAN
                    datastore engine (``limit``/``offset`` paging +
                    ``conditions[...]`` filters),
  * ``generic``   — the on-demand slot: any of the 74 catalog datasets
                    (e.g. older program years) fetched by UUID into the
                    ``open_payments_rows`` JSON table.

SCALE WARNING: the General Payment Data files exceed 15M rows per
program year (live count 2026-07-06: 15,498,687 for 2024). Fetches are
filter-driven by design and the connector's ``max_pages`` default is
deliberately small — see :mod:`connectors.open_payments.connector`.

All identifiers/columns verified live 2026-07-06 against
``openpaymentsdata.cms.gov``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_OPEN_PAYMENTS_BASE = "https://openpaymentsdata.cms.gov"

# DKAN route shapes (shared with data.medicaid.gov's engine).
CATALOG_PATH = "/api/1/metastore/schemas/dataset/items"
DATASTORE_PATH_TEMPLATE = "/api/1/datastore/query/{identifier}/0"


@dataclass(frozen=True)
class EndpointSpec:
    """One Open Payments dataset.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix
        and the value written into each row's ``source_endpoint`` column.
    title:
        Human title (mirrors the catalog entry's ``title``).
    kind:
        ``catalog`` | ``datastore`` | ``generic`` — drives which fetch
        path and which normalizer mapper runs.
    target_table:
        Canonical table the normalizer upserts into.
    identifier:
        The DKAN dataset UUID (datastore kinds only). Program-year
        detail files get a NEW uuid each publication cycle; re-verify in
        the synced catalog before a bulk run.
    pk_fields:
        Ordered native fields the upsert key is built from. A single
        field means that column IS the primary key; several fields mean
        a composed ``a:b:c`` key built in the normalizer.
    pk_column:
        The composed key's column name when ``pk_fields`` has more than
        one entry ("" when the first pk_field is itself the pk).
    date_field:
        Field used for recency ordering / registry ``date_field``.
    filter_aliases:
        CLI convenience mapping: ``--state``/``--npi`` flag → the native
        column that dataset filters on (they differ per dataset — e.g.
        ownership rows carry ``physician_npi``, profiles ``entity_npi``).
    """

    key: str
    title: str
    kind: str
    target_table: str
    identifier: str = ""
    pk_fields: Tuple[str, ...] = ()
    pk_column: str = ""
    date_field: str = ""
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "semiannual"
    default_params: Dict[str, str] = field(default_factory=dict)
    filter_aliases: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"open_payments_{self.key}"

    @property
    def base_url(self) -> str:
        return _OPEN_PAYMENTS_BASE

    @property
    def path(self) -> str:
        """URL path under the base. The generic slot has no fixed path —
        the connector formats one per requested dataset UUID."""
        if self.kind == "catalog":
            return CATALOG_PATH
        if self.identifier:
            return DATASTORE_PATH_TEMPLATE.format(identifier=self.identifier)
        return ""


# ── the catalog (all 74 datasets, one row each) ───────────────────────
_CATALOG = EndpointSpec(
    key="catalog",
    title="Open Payments dataset catalog (DKAN metastore)",
    kind="catalog",
    target_table="open_payments_catalog",
    pk_fields=("identifier",),
    date_field="modified",
    join_keys=("identifier",),
    refresh_cadence="monthly",
)

# ── curated 2024 detail + profile + summary datasets ──────────────────
# Open Payments republishes program years twice a year (June + January
# refresh), hence "semiannual". The detail files are WIDE — every native
# column is kept (see tables.py; that width is the dataset's value).
_CURATED: List[EndpointSpec] = [
    EndpointSpec(
        key="general_payments_2024",
        title="2024 General Payment Data",
        kind="datastore",
        target_table="op_general_payment",
        identifier="e6b17c6a-2534-4207-a4a1-6746a14911ff",
        pk_fields=("record_id",),
        date_field="date_of_payment",
        join_keys=("covered_recipient_npi",),
        filter_aliases={"state": "recipient_state",
                        "npi": "covered_recipient_npi"},
    ),
    EndpointSpec(
        key="research_payments_2024",
        title="2024 Research Payment Data",
        kind="datastore",
        target_table="op_research_payment",
        identifier="2f15cb85-8887-4dcc-a318-1f8ec1d815b3",
        pk_fields=("record_id",),
        date_field="date_of_payment",
        join_keys=("covered_recipient_npi",),
        filter_aliases={"state": "recipient_state",
                        "npi": "covered_recipient_npi"},
    ),
    EndpointSpec(
        key="ownership_payments_2024",
        title="2024 Ownership Payment Data",
        kind="datastore",
        target_table="op_ownership_payment",
        identifier="9ac4f7f8-b6e4-4d80-8410-4aba7e71dd02",
        pk_fields=("record_id",),
        date_field="payment_publication_date",
        join_keys=("physician_npi",),
        filter_aliases={"state": "recipient_state",
                        "npi": "physician_npi"},
    ),
    EndpointSpec(
        key="profiles",
        title="Profile Information (covered recipients)",
        kind="datastore",
        target_table="op_profile",
        identifier="f2ed17cc-f045-4e25-9b28-75c72f0c7efe",
        pk_fields=("entity_id",),
        join_keys=("entity_npi",),
        filter_aliases={"state": "entity_state", "npi": "entity_npi"},
    ),
    EndpointSpec(
        key="recipient_profile_supplement",
        title="Covered Recipient Profile Supplement",
        kind="datastore",
        target_table="op_profile_supplement",
        identifier="23160558-6742-54ff-8b9f-cac7d514ff4e",
        pk_fields=("covered_recipient_profile_id",),
        join_keys=("covered_recipient_npi",),
        filter_aliases={"state": "covered_recipient_profile_state",
                        "npi": "covered_recipient_npi"},
    ),
    EndpointSpec(
        key="summary_dashboard",
        title="Summary Dashboard - all program years",
        kind="datastore",
        target_table="op_summary_dashboard",
        identifier="e0d225fc-8230-401d-8fad-e2262fb22b4c",
        pk_fields=("dashboard_row_number",),
        join_keys=(),
    ),
    EndpointSpec(
        key="payments_by_recipient_nature_2024",
        title="2024 payments grouped by covered recipient and nature of payments",
        kind="datastore",
        target_table="op_payments_by_recipient_nature",
        identifier="88822473-9093-46fc-ad38-81330eb8de4b",
        pk_fields=("recipient_id", "nature_of_payment_type_code"),
        pk_column="recipient_nature_key",
        join_keys=("covered_recipient_npi",),
        filter_aliases={"npi": "covered_recipient_npi"},
    ),
    EndpointSpec(
        key="payments_by_entity_nature_2024",
        title="2024 payments grouped by reporting entities and nature of payments",
        kind="datastore",
        target_table="op_payments_by_entity_nature",
        identifier="d7e3f320-9ddc-4a5b-8aaf-45048cbd7386",
        pk_fields=("amgpo_id", "nature_of_payment_type_code"),
        pk_column="entity_nature_key",
        join_keys=("amgpo_id",),
    ),
    EndpointSpec(
        key="state_payment_totals",
        title="State payment totals by nature of payment, all program years",
        kind="datastore",
        target_table="op_state_payment_totals",
        identifier="e8a6db6a-a540-46aa-b04c-e216e2c72618",
        pk_fields=("country_code", "state_code", "program_year",
                   "nature_of_payment", "recipient_type"),
        pk_column="state_totals_key",
        date_field="program_year",
        join_keys=("state_code", "program_year"),
        filter_aliases={"state": "state_code"},
    ),
]

# ── the generic on-demand slot ─────────────────────────────────────────
_FETCHED_ROWS = EndpointSpec(
    key="fetched_rows",
    title="Any Open Payments dataset, fetched on demand by catalog UUID",
    kind="generic",
    target_table="open_payments_rows",
    pk_fields=("dataset_key", "row_idx"),
    pk_column="row_key",
    date_field="fetched_at",
    join_keys=("dataset_key",),
    refresh_cadence="on_demand",
)

ENDPOINTS: Dict[str, EndpointSpec] = {
    s.key: s for s in ([_CATALOG] + _CURATED + [_FETCHED_ROWS])
}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown Open Payments endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def datastore_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.kind == "datastore"]
