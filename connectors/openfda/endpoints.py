"""Declarative specs for every openFDA endpoint this connector ingests.

One :class:`EndpointSpec` per source endpoint. The spec is the single
place that knows openFDA-specific quirks: which native id to key
idempotent upserts on, which date field to chunk deep backfills by, a
cheap ``count=`` field for market-map aggregates, and the canonical
table the normalizer writes into.

Why specs and not code branches: adding or retuning an endpoint is a
data edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.openfda.registry`) and the pipeline both read these.

Food and every non drug/device endpoint is deliberately out of scope.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class EndpointSpec:
    """One openFDA endpoint.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug.
    noun / path:
        ``drug`` | ``device`` and the URL path (e.g. ``/drug/ndc.json``).
    id_fields:
        Ordered candidate dotted paths for the native record id. The
        first non-empty wins; this is the idempotency key for upsert.
        Multiple paths support endpoints whose id moved across openFDA
        schema versions (e.g. MAUDE ``report_number`` vs
        ``mdr_report_key``).
    date_field:
        openFDA field used to chunk a full backfill into date windows
        small enough to stay under the ~25k ``skip`` ceiling. ``None``
        for reference/dimension endpoints with no usable date — those
        page by ``skip`` and, past the cap, by ``partition_field``.
    date_format:
        How the date field is encoded so we can build ``[a TO b]``
        range searches. openFDA dates are ``YYYYMMDD`` except a few
        ISO ones.
    count_field:
        A low-cardinality field good for a cheap ``count=`` market map
        (and for DQ row-count reconciliation).
    partition_field:
        Fallback partition key for non-dated endpoints that exceed the
        skip cap (see DECISIONS.md). ``None`` when skip alone suffices.
    target_table:
        Canonical table the normalizer upserts into.
    supports_search_after:
        Whether the endpoint honours a stable ``sort`` for cursoring.
        openFDA universally supports ``skip``; ``search_after`` is not
        offered, so this stays ``False`` and we rely on windowing.
    """

    key: str
    noun: str
    path: str
    id_fields: Tuple[str, ...]
    target_table: str
    date_field: Optional[str] = None
    date_format: str = "YYYYMMDD"
    count_field: Optional[str] = None
    partition_field: Optional[str] = None
    supports_search_after: bool = False
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "nightly"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"openfda_{self.key}"

    @property
    def base_url(self) -> str:
        return "https://api.fda.gov"


# ── Drug endpoints ────────────────────────────────────────────────────
_DRUG: List[EndpointSpec] = [
    EndpointSpec(
        key="drug_ndc",
        noun="drug",
        path="/drug/ndc.json",
        id_fields=("product_ndc",),
        target_table="dim_drug_product",
        date_field=None,                       # NDC directory has no event date
        count_field="dosage_form",
        partition_field="dosage_form",
        join_keys=("ndc", "rxcui"),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="drug_label",
        noun="drug",
        path="/drug/label.json",
        id_fields=("id", "set_id"),
        target_table="dim_drug_product",       # enriches by openfda.product_ndc fan-out
        date_field="effective_time",
        count_field="openfda.route",
        partition_field="openfda.product_type",
        join_keys=("ndc", "rxcui"),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="drug_event",
        noun="drug",
        path="/drug/event.json",
        id_fields=("safetyreportid",),
        target_table="fact_drug_adverse_event",
        date_field="receivedate",
        count_field="patient.drug.openfda.product_ndc.exact",
        join_keys=("ndc",),
        refresh_cadence="nightly",
    ),
    EndpointSpec(
        key="drug_enforcement",
        noun="drug",
        path="/drug/enforcement.json",
        id_fields=("recall_number",),
        target_table="fact_drug_recall",
        date_field="report_date",
        count_field="classification.exact",
        join_keys=("ndc",),
        refresh_cadence="nightly",
    ),
    EndpointSpec(
        key="drugsfda",
        noun="drug",
        path="/drug/drugsfda.json",
        id_fields=("application_number",),
        target_table="dim_drug_approval",
        date_field=None,                       # submission dates are nested + sparse
        count_field="sponsor_name.exact",
        partition_field="application_number",  # partition by ANDA/NDA/BLA prefix
        join_keys=("ndc", "application_number"),
        refresh_cadence="weekly",
    ),
]

# ── Device endpoints ──────────────────────────────────────────────────
_DEVICE: List[EndpointSpec] = [
    EndpointSpec(
        key="device_classification",
        noun="device",
        path="/device/classification.json",
        id_fields=("product_code",),
        target_table="dim_device",
        date_field=None,                       # classification is a stable dimension
        count_field="device_class",
        partition_field="medical_specialty_description",
        join_keys=("product_code",),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="device_510k",
        noun="device",
        path="/device/510k.json",
        id_fields=("k_number",),
        target_table="dim_device",
        date_field="decision_date",
        date_format="YYYY-MM-DD",
        count_field="product_code.exact",
        join_keys=("product_code",),
        refresh_cadence="nightly",
    ),
    EndpointSpec(
        key="device_pma",
        noun="device",
        path="/device/pma.json",
        id_fields=("pma_number", "supplement_number"),
        target_table="dim_device",
        date_field="decision_date",
        date_format="YYYY-MM-DD",
        count_field="product_code.exact",
        join_keys=("product_code",),
        refresh_cadence="nightly",
    ),
    EndpointSpec(
        key="device_event",
        noun="device",
        path="/device/event.json",
        id_fields=("report_number", "mdr_report_key"),
        target_table="fact_device_adverse_event",
        date_field="date_received",
        count_field="device.openfda.device_class",
        join_keys=("product_code",),
        refresh_cadence="nightly",
    ),
    EndpointSpec(
        key="device_recall",
        noun="device",
        path="/device/recall.json",
        id_fields=("cfres_id", "product_res_number"),
        target_table="fact_device_recall",
        date_field="event_date_posted",
        date_format="YYYY-MM-DD",
        count_field="product_code.exact",
        join_keys=("product_code",),
        refresh_cadence="nightly",
    ),
    EndpointSpec(
        key="device_enforcement",
        noun="device",
        path="/device/enforcement.json",
        id_fields=("recall_number",),
        target_table="fact_device_recall",
        date_field="report_date",
        count_field="classification.exact",
        join_keys=("product_code",),
        refresh_cadence="nightly",
    ),
    EndpointSpec(
        key="device_udi",
        noun="device",
        path="/device/udi.json",
        id_fields=("public_device_record_key",),
        target_table="dim_device_udi",
        date_field="publish_date",
        date_format="YYYY-MM-DD",
        count_field="product_codes.code.exact",
        partition_field="product_codes.code",
        join_keys=("product_code",),
        refresh_cadence="weekly",
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {s.key: s for s in (_DRUG + _DEVICE)}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown openFDA endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def drug_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.noun == "drug"]


def device_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.noun == "device"]
