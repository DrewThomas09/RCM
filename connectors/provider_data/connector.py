"""The Provider Data connector: ``discover()`` + ``fetch()`` + ``refresh()``.

Pagination, rate-limit handling and retries all live *inside* the
connector — callers (the pipeline, the registry, the lookup handlers)
never see the DKAN datastore's native ``limit``/``offset``.

Two fetch shapes, absorbed here
-------------------------------
The metastore catalog returns every dataset in one JSON array::

    [{"identifier": "xubh-q36u", "title": ..., "distribution": [...]}, ...]

Datastore queries page by ``limit``/``offset`` inside an envelope::

    {"results": [{col: val, ...}], "count": total, "query": {...}, ...}

``count`` is always present and reflects the *filtered* total when
equality conditions are applied (verified live 2026-07-06), so a fetch
knows exactly when it stopped short.

Politeness bounds: page size defaults to 500 (the API's hard max is
1500 — a larger ``limit`` is a 400) and ``max_pages`` defaults to
:data:`DEFAULT_MAX_PAGES` = 5 so an accidental ``fetch`` of the 3.4M-row
clinician file costs at most a few requests. Callers doing a deliberate
bulk pull raise ``max_pages`` explicitly; :data:`MAX_PAGES_TOTAL` is the
absolute ceiling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .endpoints import (CATALOG_PATH, ENDPOINTS, EndpointSpec,
                        datastore_path)
from .normalize import normalize
from .transport import (DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Opener,
                        ProviderDataTransport)

DEFAULT_MAX_PAGES = 5          # polite cap; raise explicitly for bulk pulls
MAX_PAGES_TOTAL = 10_000       # absolute ceiling on any paging loop

# DKAN 4x4 identifiers look like "xubh-q36u".
_IDENTIFIER_RE = re.compile(r"^[a-z0-9]{4}-[a-z0-9]{4}$")

_DATASET_PREFIX = "provider_data_"


@dataclass
class FetchResult:
    """One ``fetch`` call's output (paging already absorbed)."""

    rows: List[Dict[str, Any]]
    endpoint: str                  # spec key, or the 4x4 id for generic pulls
    dataset_key: str = ""          # the 4x4 identifier actually queried
    total: int = 0                 # datastore "count" (filtered total)
    pages: int = 0
    requests: int = 0
    start_offset: int = 0          # offset of rows[0] (stable generic row_idx)
    truncated: bool = False        # stopped at max_pages with more available


class ProviderDataConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full paging loop with a fake server.
    """

    def __init__(
        self,
        transport: Optional[ProviderDataTransport] = None,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or ProviderDataTransport.from_env()
        self.page_size = min(int(page_size), MAX_PAGE_SIZE)
        self._sleep = sleep

    # ── discovery: sync the catalog ───────────────────────────────────
    def discover(self, *, opener: Optional[Opener] = None
                 ) -> List[Dict[str, Any]]:
        """Fetch the full metastore catalog as normalized catalog rows.

        One request returns all ~234 datasets, so there is no paging to
        absorb here — the catalog IS the discovery surface.
        """
        payload = self.transport.get_json(CATALOG_PATH, opener=opener)
        items = payload if isinstance(payload, list) else []
        spec = ENDPOINTS["catalog"]
        res = normalize(spec, [i for i in items if isinstance(i, dict)])
        return res.rows.get(spec.target_table, [])

    def endpoints(self) -> List[EndpointSpec]:
        """Enumerate the registered endpoint specs."""
        return list(ENDPOINTS.values())

    # ── dataset resolution ────────────────────────────────────────────
    def resolve(self, dataset: str) -> Tuple[EndpointSpec, str]:
        """Map a caller-supplied dataset name to ``(spec, identifier)``.

        Accepts an endpoint key (``hospital_general``), a full dataset id
        (``provider_data_hospital_general``), or a raw DKAN 4x4
        identifier — the last resolving to the generic ``fetched_rows``
        spec so *any* of the 234 catalog datasets is fetchable without a
        registry edit.
        """
        key = dataset.strip()
        if key.startswith(_DATASET_PREFIX) and key[len(_DATASET_PREFIX):] in ENDPOINTS:
            key = key[len(_DATASET_PREFIX):]
        if key in ENDPOINTS:
            spec = ENDPOINTS[key]
            return spec, spec.identifier
        if _IDENTIFIER_RE.match(key):
            return ENDPOINTS["fetched_rows"], key
        raise KeyError(
            f"unknown dataset {dataset!r}; pass an endpoint key "
            f"({sorted(ENDPOINTS)}), a provider_data_* dataset id, or a "
            f"DKAN 4x4 identifier like 'xubh-q36u'")

    # ── the datastore pager ───────────────────────────────────────────
    def fetch(
        self,
        dataset: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> FetchResult:
        """Fetch raw rows for a dataset, absorbing limit/offset paging.

        ``conditions`` is a dict of column→value equality filters, sent
        as DKAN ``conditions[i][property/value/operator]`` params (the
        server then reports the *filtered* total in ``count``).
        ``params`` may carry a starting ``offset``; anything else in it
        is passed through verbatim. Stops after ``max_pages`` pages
        (default :data:`DEFAULT_MAX_PAGES`) or on the first short page.
        """
        spec, identifier = self.resolve(dataset)
        if spec.kind == "catalog":
            # The catalog is one un-paged array; hand back raw items so
            # fetch() has one uniform return type.
            payload = self.transport.get_json(CATALOG_PATH, opener=opener)
            items = payload if isinstance(payload, list) else []
            return FetchResult(rows=items, endpoint=spec.key,
                               total=len(items), pages=1, requests=1)
        if not identifier:
            raise KeyError(
                "fetch('fetched_rows') needs a concrete dataset: pass the "
                "4x4 identifier itself (e.g. fetch('xubh-q36u'))")

        req_base: Dict[str, Any] = dict(spec.default_params)
        req_base.update(params or {})
        offset = _to_int(req_base.pop("offset", 0), 0)
        start_offset = offset
        size = min(int(page_size or spec.page_size or self.page_size),
                   MAX_PAGE_SIZE)
        pages_cap = DEFAULT_MAX_PAGES if max_pages is None else int(max_pages)
        pages_cap = max(1, min(pages_cap, MAX_PAGES_TOTAL))
        req_base.update(_condition_params(conditions))

        path = datastore_path(identifier)
        start_requests = self.transport.requests_made
        rows: List[Dict[str, Any]] = []
        total = 0
        pages = 0
        truncated = False
        while pages < pages_cap:
            req = dict(req_base)
            req["limit"] = size
            req["offset"] = offset
            payload = self.transport.get_json(path, req, opener=opener)
            results = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(results, list):
                results = []
            if isinstance(payload, dict):
                total = _to_int(payload.get("count"), total)
            rows.extend(r for r in results if isinstance(r, dict))
            got = len(results)
            offset += got
            pages += 1
            if got < size:
                break            # short page → dataset (or filter) drained
        else:
            truncated = offset < total
        return FetchResult(
            rows=rows,
            endpoint=spec.key if spec.kind == "curated" else identifier,
            dataset_key=identifier,
            total=total,
            pages=pages,
            requests=self.transport.requests_made - start_requests,
            start_offset=start_offset,
            truncated=truncated,
        )

    def fetch_dataset(
        self,
        dataset_key: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> FetchResult:
        """Fetch raw rows for *any* catalog dataset by 4x4 identifier.

        The generic escape hatch that makes all 234 catalog datasets
        reachable: rows land in ``provider_data_rows`` via ``refresh``.
        """
        key = dataset_key.strip()
        if not _IDENTIFIER_RE.match(key):
            raise KeyError(
                f"fetch_dataset expects a DKAN 4x4 identifier, got {dataset_key!r}")
        return self.fetch(key, params, opener=opener, max_pages=max_pages,
                          page_size=page_size, conditions=conditions)

    # ── fetch + normalize + upsert ────────────────────────────────────
    def refresh(
        self,
        store: Any,
        dataset: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience: fetch a dataset, normalize, upsert; return counts.

        ``store`` is a :class:`~connectors.provider_data.tables.ProviderDataStore`
        (typed ``Any`` to keep this module import-light). The catalog
        syncs whole; curated datasets land in their canonical table; a
        raw 4x4 identifier lands in the generic ``provider_data_rows``.
        """
        spec, identifier = self.resolve(dataset)
        if spec.kind == "catalog":
            rows = self.discover(opener=opener)
            written = store.upsert(spec.target_table, rows)
            return {"dataset_id": spec.dataset_id, "table": spec.target_table,
                    "fetched": len(rows), "upserted": written,
                    "total": len(rows), "pages": 1, "truncated": False}

        result = self.fetch(dataset, params, opener=opener,
                            max_pages=max_pages, page_size=page_size,
                            conditions=conditions)
        if spec.kind == "curated":
            norm = normalize(spec, result.rows)
        else:
            norm = normalize(spec, result.rows, dataset_key=identifier,
                             start_idx=result.start_offset)
        written = store.upsert(spec.target_table,
                               norm.rows.get(spec.target_table, []))
        return {"dataset_id": spec.dataset_id, "table": spec.target_table,
                "dataset_key": identifier, "fetched": len(result.rows),
                "upserted": written, "total": result.total,
                "pages": result.pages, "truncated": result.truncated,
                "unmapped": dict(norm.unmapped)}


def _condition_params(conditions: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """DKAN equality conditions → indexed bracket query params.

    ``{"state": "TX"}`` becomes ``conditions[0][property]=state``,
    ``conditions[0][value]=TX``, ``conditions[0][operator]==`` — the
    simple, live-verified subset of DKAN's condition grammar (richer
    operators exist but equality covers the estate's slicing needs).
    """
    out: Dict[str, str] = {}
    for i, (prop, value) in enumerate(sorted((conditions or {}).items())):
        out[f"conditions[{i}][property]"] = str(prop)
        out[f"conditions[{i}][value]"] = str(value)
        out[f"conditions[{i}][operator]"] = "="
    return out


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
