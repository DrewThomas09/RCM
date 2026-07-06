"""Declarative dataset registry — one row per CMS Open Data dataset.

Conforms to the shared registry contract exactly: every dataset is a
single declarative row with the same field names every RCM connector
exposes::

    {dataset_id, connector, base_url, endpoint, default_params,
     refresh_cadence, join_keys, target_table,
     source, source_filter, date_field}

Adding a dataset is a row here (derived from an :class:`EndpointSpec`),
never new routing code. The ``/v1/query/{dataset}`` engine
(:mod:`connectors.cms_open_data.query`) auto-exposes anything in this
registry.

``source_filter`` semantics per kind:

  * catalog + curated rows pin their table slice to the spec key (their
    tables are exclusive today, so the pin is a cheap invariant, not a
    necessity);
  * the generic ``fetched_rows`` dataset deliberately carries an EMPTY
    ``source_filter`` — its shared table stores one slice per *fetched*
    catalog dataset (``source_endpoint = dataset_key``), and a query
    against ``cms_open_data_fetched_rows`` must see all of them and
    narrow with a ``dataset_key`` filter.

All rows are tagged ``source='cms_open_data'`` so the central aggregator
can ingest them uniformly alongside every other connector.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .endpoints import ENDPOINTS, EndpointSpec

SOURCE = "cms_open_data"


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
        connector="cms_open_data",
        base_url=spec.base_url,
        endpoint=spec.path,
        default_params=dict(spec.default_params),
        refresh_cadence=spec.refresh_cadence,
        join_keys=list(spec.join_keys),
        target_table=spec.target_table,
        source_filter="" if spec.kind == "generic" else spec.key,
        date_field=spec.date_field or "",
    )


def registry_rows() -> List[RegistryRow]:
    """Every CMS Open Data dataset as a declarative registry row."""
    return [_row(s) for s in ENDPOINTS.values()]


def registry_as_dicts() -> List[Dict[str, Any]]:
    """Registry rows as plain dicts (for the central registry to ingest)."""
    return [r.as_dict() for r in registry_rows()]


def by_dataset_id() -> Dict[str, RegistryRow]:
    return {r.dataset_id: r for r in registry_rows()}


def dataset_ids() -> List[str]:
    return sorted(r.dataset_id for r in registry_rows())
