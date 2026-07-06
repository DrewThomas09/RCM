"""Declarative dataset registry — one row per OIG LEIE dataset.

Conforms to the shared registry contract exactly: every dataset is a
single declarative row with the same field names every RCM connector
exposes::

    {dataset_id, connector, base_url, endpoint, default_params,
     refresh_cadence, join_keys, target_table,
     source, source_filter, date_field}

Adding a dataset is a row here (derived from an :class:`EndpointSpec`),
never new routing code. The ``/v1/query/{dataset}`` engine
(:mod:`connectors.oig_leie.query`) auto-exposes anything in this
registry.

``source_filter`` is deliberately empty on every row. The full file and
the monthly exclusions supplement share ``oig_exclusions`` — but unlike
the estate's usual shared-table pattern they are *one logical dataset*
(the supplement is incremental adds to the cumulative list), so slicing
them apart by ``source_endpoint`` would make a query for
``oig_leie_exclusions`` blind to providers excluded since the last full
pull — exactly the rows a compliance screen most needs. Provenance
still lives in each row's ``source_endpoint`` column
(``exclusions`` / ``supplement:YYYY-MM``) for auditing via filters.

``join_keys`` is ``["npi"]``: the LEIE's screening join is NPI → NPPES /
Care Compare / Open Payments providers. Note the caveat that ~85% of
historic rows have no NPI (normalized ``''``) — name matching is the
fallback, served by the ``exclusion-name`` lookup.

All rows are tagged ``source='oig_leie'`` so the central aggregator can
ingest them uniformly alongside every other connector.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .endpoints import ENDPOINTS, EndpointSpec

SOURCE = "oig_leie"


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
        connector="oig_leie",
        base_url=spec.base_url,
        endpoint=spec.path_template,
        default_params=dict(spec.default_params),
        refresh_cadence=spec.refresh_cadence,
        join_keys=list(spec.join_keys),
        target_table=spec.target_table,
        source_filter="",   # union view; see module docstring
        date_field=spec.date_field,
    )


def registry_rows() -> List[RegistryRow]:
    """Every OIG LEIE dataset as a declarative registry row."""
    return [_row(s) for s in ENDPOINTS.values()]


def registry_as_dicts() -> List[Dict[str, Any]]:
    """Registry rows as plain dicts (for the central registry to ingest)."""
    return [r.as_dict() for r in registry_rows()]


def by_dataset_id() -> Dict[str, RegistryRow]:
    return {r.dataset_id: r for r in registry_rows()}


def dataset_ids() -> List[str]:
    return sorted(r.dataset_id for r in registry_rows())
