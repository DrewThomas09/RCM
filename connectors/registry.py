"""The unified connector registry — one database of every API dataset.

Each connector under ``connectors/`` keeps its own declarative registry
(``connectors.<name>.registry``). This module *aggregates* them into a
single estate view so a caller can answer "what public APIs do we connect,
and what datasets do they expose?" in one call — the "all the APIs, in one
place, easy to use" surface.

Every row is already uniform (the connectors share a ``RegistryRow`` with
identical field names), so aggregation is a flat concatenation plus a
``connector`` / ``source`` tag that is already present on each row.

Public API::

    from connectors.registry import (
        all_registry_rows, all_dataset_ids, dataset_owner,
        connectors_summary, catalog,
    )
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._spi import CONNECTOR_NAMES, Adapter, load_all

# Loaded once at import; the per-connector registries are pure/declarative.
_ADAPTERS: Dict[str, Adapter] = load_all()


def adapters() -> Dict[str, Adapter]:
    """The loaded connector adapters, keyed by name (registration order)."""
    return dict(_ADAPTERS)


def all_registry_rows() -> List[Dict[str, Any]]:
    """Every dataset across every connector as a plain declarative dict.

    Rows carry the shared ``RegistryRow`` fields (``dataset_id``,
    ``connector``, ``base_url``, ``endpoint``, ``default_params``,
    ``refresh_cadence``, ``join_keys``, ``target_table``, ``source``,
    ``source_filter``, ``date_field``).
    """
    out: List[Dict[str, Any]] = []
    for name in CONNECTOR_NAMES:
        out.extend(_ADAPTERS[name].registry_as_dicts())
    return out


def all_dataset_ids() -> List[str]:
    """Sorted list of every dataset id in the estate."""
    return sorted(r["dataset_id"] for r in all_registry_rows())


def _owner_index() -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for name in CONNECTOR_NAMES:
        for did in _ADAPTERS[name].dataset_ids():
            idx[did] = name
    return idx


def dataset_owner(dataset_id: str) -> Optional[str]:
    """Which connector owns ``dataset_id`` (``None`` if unknown)."""
    return _owner_index().get(dataset_id)


def connectors_summary() -> List[Dict[str, Any]]:
    """One row per connector: label, base URL(s), dataset count + ids."""
    summary: List[Dict[str, Any]] = []
    for name in CONNECTOR_NAMES:
        a = _ADAPTERS[name]
        summary.append({
            "connector": name,
            "label": a.label,
            "base_urls": a.base_urls(),
            "n_datasets": len(a.dataset_ids()),
            "dataset_ids": a.dataset_ids(),
        })
    return summary


def catalog() -> Dict[str, Any]:
    """A compact estate catalog: totals + per-connector + every dataset.

    The single call a partner (or the assistant) makes to see the whole
    API estate at a glance.
    """
    rows = all_registry_rows()
    return {
        "n_connectors": len(CONNECTOR_NAMES),
        "n_datasets": len(rows),
        "connectors": connectors_summary(),
        "datasets": rows,
    }
