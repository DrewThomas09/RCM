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

from ._spi import (
    CATALOG_CONNECTORS, CATALOG_ROW_FIELDS, CONNECTOR_NAMES, Adapter,
    _clamp_limit, load_all,
)

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


def catalog_connectors() -> List[str]:
    """The connectors that sync a searchable upstream open-data catalog."""
    return list(CATALOG_CONNECTORS)


def catalog_search_all(
    stores: Dict[str, Any],
    q: str,
    *,
    limit: int = 50,
    per_connector_limit: int = 50,
    connectors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Keyword-search every synced open-data catalog at once.

    The registered datasets (:func:`all_dataset_ids`) are the slice of the
    upstream catalogs someone curated into first-class typed tables. The
    catalogs themselves are far larger — tens of thousands of datasets
    across data.cms.gov, the Provider Data Catalog, Open Payments,
    data.medicaid.gov, Healthcare.gov, data.cdc.gov and healthdata.gov —
    and every one of them is already pullable through its connector's
    generic fetched-rows slot. What was missing was *finding* one: you
    had to know its identifier first. This is that missing half.

    Two limits, deliberately separate:

    ``per_connector_limit``
        how many hits each catalog contributes, so one huge catalog
        (healthdata.gov carries ~23k datasets) cannot crowd out the
        others;
    ``limit``
        how many merged rows come back overall.

    Both are clamped. ``connectors`` narrows the fan-out to a subset;
    unknown names are ignored rather than raising, so a caller can pass a
    speculative list. Connectors with no catalog are skipped silently —
    that is the normal case (openFDA, ICD-10, HCPCS, QPP, RxNorm, …).

    Ordering is deterministic: connector registration order, then title,
    which keeps the merged result stable across runs and makes the
    provenance of a hit obvious from its position.

    ``stores`` is the same ``{connector: store}`` mapping the unified
    server's ``open_stores()`` builds; a connector missing from it is
    skipped, so a partially-ingested estate still answers.
    """
    term = str(q or "").strip()
    wanted = [n for n in CATALOG_CONNECTORS
              if connectors is None or n in set(connectors)]
    overall = _clamp_limit(limit)
    searched: List[str] = []
    results: List[Dict[str, Any]] = []
    if term:
        per = _clamp_limit(per_connector_limit)
        for name in wanted:
            store = stores.get(name)
            if store is None:
                continue
            searched.append(name)
            results.extend(
                _ADAPTERS[name].catalog_search(store, term, limit=per))
    merged = results[:overall]
    return {
        "q": term,
        "fields": list(CATALOG_ROW_FIELDS),
        "connectors_searched": searched,
        # count is what came back; total_before_limit is what was found, so a
        # truncated answer is visibly truncated instead of reading as complete.
        "count": len(merged),
        "total_before_limit": len(results),
        "results": merged,
    }
