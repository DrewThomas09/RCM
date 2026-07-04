"""Declarative dataset registry — one row per NPI query dataset.

Conforms to the shared registry contract exactly: every dataset is a
single declarative row with the **same fields** as every other RCM
connector, so a top-level aggregator can ingest all connectors
uniformly::

    {dataset_id, connector, base_url, endpoint, default_params,
     refresh_cadence, join_keys, target_table,
     source, source_filter, date_field}

The three canonical NPI tables map 1:1 to three query datasets:

  * ``npi_provider``          → ``dim_provider``
  * ``npi_provider_taxonomy`` → ``fact_provider_taxonomy``
  * ``npi_provider_address``  → ``fact_provider_address``

Because each table has a single physical source, ``source_filter`` is
empty (there is no shared-table slice to pin, unlike openFDA). The
``/v1/query/{dataset}`` engine (:mod:`connectors.npi_registry.query`)
auto-exposes anything in this registry. All rows are tagged
``source='npi_registry'``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .endpoints import NPPES_BASE, NPPES_PATH

SOURCE = "npi_registry"
CONNECTOR = "npi_registry"


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


# One declarative row per dataset. ``default_params`` documents the NPPES
# call shape (always version=2.1); ``date_field`` names the incremental
# watermark column where one exists.
_DATASETS = (
    {
        "dataset_id": "npi_provider",
        "target_table": "dim_provider",
        "date_field": "last_updated",
    },
    {
        "dataset_id": "npi_provider_taxonomy",
        "target_table": "fact_provider_taxonomy",
        "date_field": "",
    },
    {
        "dataset_id": "npi_provider_address",
        "target_table": "fact_provider_address",
        "date_field": "",
    },
)


def _row(spec: Dict[str, str]) -> RegistryRow:
    return RegistryRow(
        dataset_id=spec["dataset_id"],
        connector=CONNECTOR,
        base_url=NPPES_BASE,
        endpoint=NPPES_PATH,
        default_params={"version": "2.1"},
        refresh_cadence="weekly",
        join_keys=["npi"],
        target_table=spec["target_table"],
        source_filter="",
        date_field=spec.get("date_field", ""),
    )


def registry_rows() -> List[RegistryRow]:
    """Every NPI dataset as a declarative registry row."""
    return [_row(s) for s in _DATASETS]


def registry_as_dicts() -> List[Dict[str, Any]]:
    """Registry rows as plain dicts (for the central registry to ingest)."""
    return [r.as_dict() for r in registry_rows()]


def by_dataset_id() -> Dict[str, RegistryRow]:
    return {r.dataset_id: r for r in registry_rows()}


def dataset_ids() -> List[str]:
    return sorted(r.dataset_id for r in registry_rows())
