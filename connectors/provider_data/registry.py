"""Declarative dataset registry — one row per Provider Data dataset.

Conforms to the shared registry contract exactly: every dataset is a
single declarative row with the same field names every RCM connector
exposes::

    {dataset_id, connector, base_url, endpoint, default_params,
     refresh_cadence, join_keys, target_table,
     source, source_filter, date_field}

Adding a dataset is a row here (derived from an :class:`EndpointSpec`),
never new routing code. The ``/v1/query/{dataset}`` engine
(:mod:`connectors.provider_data.query`) auto-exposes anything in this
registry.

Slice semantics: each curated dataset owns its whole table, and the
catalog owns ``provider_data_catalog`` — their ``source_filter`` still
pins ``source_endpoint`` for uniformity with the estate. The generic
``fetched_rows`` dataset deliberately carries an **empty**
``source_filter``: its shared table holds one slice per pulled catalog
dataset (``source_endpoint = dataset_key``), and pinning to a single
value would hide every other slice — callers filter on ``dataset_key``
instead.

All rows are tagged ``source='provider_data'`` so the central aggregator
can ingest them uniformly alongside every other connector.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .endpoints import ENDPOINTS, EndpointSpec

SOURCE = "provider_data"


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
    # Shared addenda (still declarative, no routing code):
    source: str = SOURCE
    source_filter: str = ""        # value for target_table.source_endpoint
    date_field: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _row(spec: EndpointSpec) -> RegistryRow:
    return RegistryRow(
        dataset_id=spec.dataset_id,
        connector="provider_data",
        base_url=spec.base_url,
        endpoint=spec.path,
        default_params=dict(spec.default_params),
        refresh_cadence=spec.refresh_cadence,
        join_keys=list(spec.join_keys),
        target_table=spec.target_table,
        # The generic table is multi-slice by design; see module docstring.
        source_filter="" if spec.kind == "generic" else spec.key,
        date_field=spec.date_field or "",
    )


def registry_rows() -> List[RegistryRow]:
    """Every Provider Data dataset as a declarative registry row."""
    return [_row(s) for s in ENDPOINTS.values()]


def registry_as_dicts() -> List[Dict[str, Any]]:
    """Registry rows as plain dicts (for the central registry to ingest)."""
    return [r.as_dict() for r in registry_rows()]


def by_dataset_id() -> Dict[str, RegistryRow]:
    return {r.dataset_id: r for r in registry_rows()}


def dataset_ids() -> List[str]:
    return sorted(r.dataset_id for r in registry_rows())
