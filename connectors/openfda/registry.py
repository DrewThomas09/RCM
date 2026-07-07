"""Declarative dataset registry — one row per openFDA dataset.

Conforms to the registry contract exactly: every dataset is a single
declarative row::

    {dataset_id, connector, base_url, endpoint, default_params,
     refresh_cadence, join_keys, target_table}

Adding a dataset is a row here (derived from an :class:`EndpointSpec`),
never new routing code. The ``/v1/query/{dataset}`` engine
(:mod:`connectors.openfda.query`) auto-exposes anything in this registry.

Because several endpoints land in the same canonical table (e.g.
``drug_ndc`` and ``drug_label`` both feed ``dim_drug_product``), each
registry row also carries a ``source_filter`` (the ``source_endpoint``
column) so a dataset query returns exactly that endpoint's slice while
still sharing one physical table.

All rows are tagged ``source='openfda'`` so the central registry can
ingest them without the openFDA workstream touching the router core.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .endpoints import ENDPOINTS, EndpointSpec
from .tables import TABLES

SOURCE = "openfda"

# A spec's ``date_field`` names the RAW openFDA field (used by the live
# incremental fetch window), which is not always a canonical column — the
# registry's ``date_field`` is a *query* contract (``{date_field}__gte=…``
# must work against the target table), so raw-only names are mapped to
# the canonical column the normalizer writes them into, or dropped when
# the canonical table carries no date at all (drug_label → the dateless
# dim_drug_product). Keyed by endpoint key so an unrelated spec reusing a
# raw name is not silently remapped.
_RAW_DATE_TO_CANONICAL: Dict[str, str] = {
    "device_recall": "report_date",   # raw event_date_posted → report_date
}


@dataclass(frozen=True)
class RegistryRow:
    dataset_id: str
    connector: str
    base_url: str
    endpoint: str
    default_params: Dict[str, str]
    refresh_cadence: str
    join_keys: List[str]
    target_table: str
    # openFDA-specific addenda (still declarative, no routing code):
    source: str = SOURCE
    source_filter: str = ""        # value for target_table.source_endpoint
    date_field: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _canonical_date_field(spec: EndpointSpec) -> str:
    """The spec's date field only if it is a real column of the target table.

    Advertising a raw-only field here would hand every caller a
    ``QueryError('unknown filter field …')`` the moment they build the
    documented incremental filter — the exact drift this guards against
    (drug_label's ``effective_time``, device_recall's
    ``event_date_posted``).
    """
    if not spec.date_field:
        return ""
    if spec.date_field in TABLES[spec.target_table].columns:
        return spec.date_field
    return _RAW_DATE_TO_CANONICAL.get(spec.key, "")


def _row(spec: EndpointSpec) -> RegistryRow:
    return RegistryRow(
        dataset_id=spec.dataset_id,
        connector="openfda",
        base_url=spec.base_url,
        endpoint=spec.path,
        default_params=dict(spec.default_params),
        refresh_cadence=spec.refresh_cadence,
        join_keys=list(spec.join_keys),
        target_table=spec.target_table,
        source_filter=spec.key,
        date_field=_canonical_date_field(spec),
    )


def registry_rows() -> List[RegistryRow]:
    """Every openFDA dataset as a declarative registry row."""
    return [_row(s) for s in ENDPOINTS.values()]


def registry_as_dicts() -> List[Dict[str, Any]]:
    """Registry rows as plain dicts (for the central registry to ingest)."""
    return [r.as_dict() for r in registry_rows()]


def by_dataset_id() -> Dict[str, RegistryRow]:
    return {r.dataset_id: r for r in registry_rows()}


def dataset_ids() -> List[str]:
    return sorted(r.dataset_id for r in registry_rows())
