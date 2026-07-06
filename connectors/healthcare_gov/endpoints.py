"""Declarative specs for every data.healthcare.gov dataset this connector ingests.

One :class:`EndpointSpec` per dataset. The spec is the single place that
knows data.healthcare.gov-specific quirks: the DKAN dataset identifier
the datastore is queried by, the ordered natural-key fields the
idempotent upsert composes, the date field used for recency, and the
canonical table the normalizer writes into.

Why specs and not code branches: adding or retuning a dataset is a data
edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.healthcare_gov.registry`) and the connector both read
these.

data.healthcare.gov is a DKAN 2 catalog for the federal Health Insurance
Marketplace. Three families of specs:

  * ``catalog`` — the full metastore dataset list (every dataset's
    identifier, title, periodicity, distribution URLs, ...). Syncing it
    is what makes "every dataset connected" true.
  * CURATED datasets — the flagship Marketplace public-use files that
    are actually queryable through the DKAN datastore. Selected by
    enumerating the live catalog (337 items, July 2026): the QHP
    Landscape files ship as ZIP downloads only (no datastore storage —
    verified live with ``/api/1/datastore/query/{id}/0`` returning
    "No datastore storage found"), and no Rate Review or Marketplace
    enrollment PUF exists in this catalog, so the curated picks are the
    latest-plan-year (PY2026) PUFs that *are* datastore-queryable:
    Plan Attributes, Benefits and Cost Sharing, Rate, Quality, and
    Service Area.
  * ``fetched_rows`` — the generic on-demand slot: ANY of the 337
    catalog datasets with datastore storage can be pulled by its DKAN
    identifier into the ``healthcare_gov_rows`` table and queried
    uniformly (filter on ``dataset_key``, ``LIKE`` on ``row_json``).

Column lists in :mod:`connectors.healthcare_gov.tables` were snapshotted
from LIVE datastore samples of each identifier below (DKAN returns the
PUF CSV headers already lower-cased).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_HEALTHCARE_GOV_BASE = "https://data.healthcare.gov"

# DKAN metastore path serving the full catalog in one call (no paging).
CATALOG_PATH = "/api/1/metastore/schemas/dataset/items"


def datastore_path(identifier: str) -> str:
    """Datastore query path for a DKAN dataset id (first distribution).

    DKAN addresses the datastore as ``{dataset identifier}/{distribution
    index}``; every dataset on data.healthcare.gov carries a single
    distribution, so index 0 is the whole dataset.
    """
    return f"/api/1/datastore/query/{identifier}/0"


@dataclass(frozen=True)
class EndpointSpec:
    """One data.healthcare.gov dataset.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix
        and the value written into each row's ``source_endpoint`` column
        so datasets sharing a table stay individually queryable.
    kind:
        ``catalog`` (metastore list, one call) | ``datastore`` (curated
        PUF paged by limit/offset) | ``generic`` (on-demand rows table).
    identifier:
        The DKAN dataset UUID/slug the datastore is queried by. Empty
        for ``catalog`` and ``generic``.
    target_table:
        Canonical table the normalizer upserts into.
    id_fields:
        Ordered natural-key fields; the composed upsert key
        ``{key}:{f1}:{f2}:...`` is built from these in the normalizer.
        Verified unique on live 500-row samples during the build.
    date_field:
        Field used for recency ordering / registry ``date_field``.
    """

    key: str
    kind: str
    target_table: str
    identifier: str = ""
    title: str = ""
    id_fields: Tuple[str, ...] = ()
    date_field: str = ""
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "annual"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"healthcare_gov_{self.key}"

    @property
    def base_url(self) -> str:
        return _HEALTHCARE_GOV_BASE

    @property
    def path(self) -> str:
        """URL path under ``data.healthcare.gov`` this spec is fetched from."""
        if self.kind == "catalog":
            return CATALOG_PATH
        if self.kind == "generic":
            # Template only — the concrete id arrives at fetch time.
            return "/api/1/datastore/query/{identifier}/0"
        return datastore_path(self.identifier)


_SPECS: List[EndpointSpec] = [
    # ── the full catalog ────────────────────────────────────────────────
    EndpointSpec(
        key="catalog",
        kind="catalog",
        target_table="healthcare_gov_catalog",
        title="data.healthcare.gov dataset catalog (DKAN metastore)",
        id_fields=("identifier",),
        date_field="modified",
        join_keys=("identifier",),
        refresh_cadence="weekly",
    ),
    # ── curated PY2026 Marketplace PUFs (datastore-queryable, verified) ─
    EndpointSpec(
        key="plan_attributes_py2026",
        kind="datastore",
        identifier="ca253298-c4ef-4a77-9c44-0de0bbe91941",
        target_table="healthcare_gov_plan_attributes",
        title="Plan Attributes PUF - PY2026",
        # One row per plan-variant id within a business year (verified
        # unique on a live 500-row sample).
        id_fields=("businessyear", "planid"),
        date_field="importdate",
        join_keys=("planid", "standardcomponentid", "issuerid", "statecode"),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="benefits_cost_sharing_py2026",
        kind="datastore",
        identifier="57b37731-ceda-48d0-a467-0c8f044e8f18",
        target_table="healthcare_gov_benefits_cost_sharing",
        title="Benefits and Cost Sharing PUF - PY2026",
        # One row per plan-variant + benefit (verified unique live).
        # ~1.46M rows total — WIDE table, keep fetch defaults small.
        id_fields=("businessyear", "planid", "benefitname"),
        date_field="importdate",
        join_keys=("planid",),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="rate_puf_py2026",
        kind="datastore",
        identifier="477ffb11-db39-44ae-9f96-40d9db2ba79f",
        target_table="healthcare_gov_rates",
        title="Rate PUF - PY2026",
        # One rate cell per plan × rating area × tobacco × age band ×
        # effective date (verified unique live). ~2.24M rows total.
        id_fields=("businessyear", "planid", "ratingareaid", "tobacco",
                   "age", "rateeffectivedate"),
        date_field="importdate",
        join_keys=("planid", "ratingareaid"),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="quality_puf_py2026",
        kind="datastore",
        identifier="d1d5aef7-0549-4173-b625-c0ace09c8634",
        target_table="healthcare_gov_plan_quality",
        title="Quality PUF - PY2026",
        # One star-ratings row per plan id (verified unique live).
        id_fields=("planid",),
        date_field="",
        join_keys=("planid", "issuerid"),
        refresh_cadence="annual",
    ),
    EndpointSpec(
        key="service_area_puf_py2026",
        kind="datastore",
        identifier="55c47876-cfdd-438c-964e-7f88093b7ef2",
        target_table="healthcare_gov_service_areas",
        title="Service Area PUF - PY2026",
        # A service area repeats per covered county; market coverage and
        # dental-only are kept in the key defensively (issuers may reuse
        # a service-area id across market templates).
        id_fields=("businessyear", "statecode", "issuerid", "serviceareaid",
                   "county", "marketcoverage", "dentalonlyplan"),
        date_field="importdate",
        join_keys=("statecode", "county"),
        refresh_cadence="annual",
    ),
    # ── generic on-demand rows for any catalog dataset ──────────────────
    EndpointSpec(
        key="fetched_rows",
        kind="generic",
        target_table="healthcare_gov_rows",
        title="Generic fetched rows (any catalog dataset, by DKAN id)",
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
            f"unknown healthcare.gov endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def curated_endpoints() -> List[EndpointSpec]:
    """The flagship datastore-backed PUF specs (excludes catalog/generic)."""
    return [s for s in ENDPOINTS.values() if s.kind == "datastore"]
