"""Declarative dataset registry — one row per ICD-10 dataset.

Conforms to the registry contract exactly: every dataset is a single
declarative row::

    {dataset_id, connector, base_url, endpoint, default_params,
     refresh_cadence, join_keys, target_table}

Adding a dataset is a row here (derived from an :class:`EndpointSpec`),
never new routing code. The ``/v1/query/{dataset}`` engine
(:mod:`connectors.icd10.query`) auto-exposes anything in this registry.

Both endpoints (CM and PCS) land in the same canonical table
``dim_icd10_code``, so each registry row also carries a ``source_filter``
(the ``source_endpoint`` value) so a dataset query returns exactly that
code set's slice while sharing one physical table.

All rows are tagged ``source='icd10'`` so the central registry can ingest
them without the ICD-10 workstream touching the router core.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .endpoints import ENDPOINTS, EndpointSpec

SOURCE = "icd10"


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
    # source-specific addenda (still declarative, no routing code):
    source: str = SOURCE
    source_filter: str = ""        # value for target_table.source_endpoint
    date_field: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _row(spec: EndpointSpec) -> RegistryRow:
    default_params = dict(spec.default_params)
    default_params.setdefault("sf", spec.sf)
    default_params.setdefault("df", ",".join(spec.df))
    return RegistryRow(
        dataset_id=spec.dataset_id,
        connector="icd10",
        base_url=spec.base_url,
        endpoint=spec.path,
        default_params=default_params,
        refresh_cadence=spec.refresh_cadence,
        join_keys=list(spec.join_keys),
        target_table=spec.target_table,
        source_filter=spec.key,
        date_field="",                 # ICD-10 is a reference dimension, no date
    )


def registry_rows() -> List[RegistryRow]:
    """Every ICD-10 dataset as a declarative registry row."""
    return [_row(s) for s in ENDPOINTS.values()]


def registry_as_dicts() -> List[Dict[str, Any]]:
    """Registry rows as plain dicts (for the central registry to ingest)."""
    return [r.as_dict() for r in registry_rows()]


def by_dataset_id() -> Dict[str, RegistryRow]:
    return {r.dataset_id: r for r in registry_rows()}


def dataset_ids() -> List[str]:
    return sorted(r.dataset_id for r in registry_rows())
