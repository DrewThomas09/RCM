"""Declarative dataset registry — one row per QCEW slice dataset.

Conforms to the shared registry contract exactly: every dataset is a
single declarative row with the same field names every RCM connector
exposes::

    {dataset_id, connector, base_url, endpoint, default_params,
     refresh_cadence, join_keys, target_table,
     source, source_filter, date_field}

Adding a dataset is a row here (derived from an :class:`EndpointSpec`),
never new routing code. The ``/v1/query/{dataset}`` engine
(:mod:`connectors.bls_qcew.query`) auto-exposes anything in this
registry.

Both slice datasets land in the same canonical table
(``qcew_industry_area`` — the row shape is identical), so each registry
row also carries a ``source_filter`` (the ``source_endpoint`` column
value) so a dataset query returns exactly that slice kind's rows while
still sharing one physical table — the cms_coverage shared-table
pattern.

``endpoint`` is the URL path *template* (year/qtr/code are path
segments, not a query string); ``default_params`` carry the pinned
latest published quarter (2025 Q4, verified live 2026-07-06) plus the
default slice code (NAICS 62 / US000).

All rows are tagged ``source='bls_qcew'`` so the central aggregator can
ingest them uniformly alongside every other connector.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .endpoints import ENDPOINTS, EndpointSpec

SOURCE = "bls_qcew"


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
        connector="bls_qcew",
        base_url=spec.base_url,
        endpoint=spec.path_template,
        default_params=dict(spec.default_params),
        refresh_cadence=spec.refresh_cadence,
        join_keys=list(spec.join_keys),
        target_table=spec.target_table,
        source_filter=spec.key,
        date_field=spec.date_field,
    )


def registry_rows() -> List[RegistryRow]:
    """Every QCEW slice dataset as a declarative registry row."""
    return [_row(s) for s in ENDPOINTS.values()]


def registry_as_dicts() -> List[Dict[str, Any]]:
    """Registry rows as plain dicts (for the central registry to ingest)."""
    return [r.as_dict() for r in registry_rows()]


def by_dataset_id() -> Dict[str, RegistryRow]:
    return {r.dataset_id: r for r in registry_rows()}


def dataset_ids() -> List[str]:
    return sorted(r.dataset_id for r in registry_rows())
