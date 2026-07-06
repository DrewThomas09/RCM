"""The data.medicaid.gov connector: ``discover()`` + ``fetch()`` + ``refresh()``.

Pagination, rate-limit handling and retries all live *inside* the
connector — callers (the pipeline, the registry, the lookup handlers)
never see DKAN's native ``limit``/``offset``.

Two DKAN shapes, absorbed here
------------------------------
The metastore catalog returns every dataset in one bare JSON array::

    GET /api/1/metastore/schemas/dataset/items          → [ {...}, ... ]

Datastore queries page by ``limit``/``offset`` in an object envelope::

    GET /api/1/datastore/query/{uuid}/0?limit=N&offset=M
        → {"results": [...], "count": TOTAL, "schema": {...}, "query": {...}}

``fetch`` is a single *step*: it returns the current page's rows plus a
``next_cursor`` describing where to resume, and ``None`` when the dataset
is exhausted. Every cursor is JSON-serialisable so a hard kill resumes
exactly where it stopped. :meth:`fetch_all` drives the loop under a
``max_pages`` bound.

Why ``max_pages`` defaults LOW (5): several curated datasets are huge
(NADAC 2025 is 1.6M rows, SDUD years are >5M, NADAC Comparison is 3.4M)
— an accidental unbounded pull would hammer the API for hours. Callers
that genuinely want a full drain must opt in with an explicit, larger
``max_pages``.

Simple equality filters are pushed down to DKAN as
``conditions[i][property/value/operator]`` params (verified live) so a
filtered ingest doesn't pull the whole year file.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .endpoints import ENDPOINTS, EndpointSpec, datastore_path, get_endpoint
from .normalize import normalize, normalize_generic
from .transport import MedicaidDataTransport, Opener

# Polite default page size. DKAN accepted limit=2000 in live probes, but
# 500 keeps response sizes and server load modest.
PAGE_LIMIT = 500
MAX_PAGES_DEFAULT = 5           # bounded by default; see module docstring
MAX_PAGES_HARD = 100_000        # absolute ceiling on any single drive loop


@dataclass
class FetchResult:
    """One ``fetch`` step's output."""

    rows: List[Dict[str, Any]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    total: int = 0
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class MedicaidDataConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full paging state machine with a fake
    server.
    """

    def __init__(
        self,
        transport: Optional[MedicaidDataTransport] = None,
        *,
        page_limit: int = PAGE_LIMIT,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or MedicaidDataTransport.from_env()
        self.page_limit = page_limit
        self._sleep = sleep

    # ── discovery: sync the DKAN catalog ──────────────────────────────
    def discover(self, *, opener: Optional[Opener] = None
                 ) -> List[Dict[str, Any]]:
        """Fetch the full metastore catalog (all ~541 datasets, one call).

        Returns the raw DCAT items; :func:`normalize` +
        :meth:`refresh_catalog` turn them into ``medicaid_data_catalog``
        rows. The catalog is the discovery surface — every identifier in
        it is fetchable via :meth:`fetch_dataset`.
        """
        spec = get_endpoint("catalog")
        payload = self.transport.get_json(spec.path, opener=opener)
        if isinstance(payload, list):
            return [it for it in payload if isinstance(it, dict)]
        # A 404 (or drift) yields the empty datastore envelope — no items.
        return []

    def endpoints(self) -> List[EndpointSpec]:
        """Enumerate the endpoint specs this connector registers."""
        return list(ENDPOINTS.values())

    # ── the fetch state machine (limit/offset absorbed) ───────────────
    def fetch(
        self,
        spec: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Advance one page. Returns rows for the current page + a
        ``next_cursor`` (``None`` when the dataset is exhausted).

        ``params['filters']`` (a ``{column: value}`` dict) is pushed down
        as DKAN equality conditions; any other params pass through.
        """
        if spec.kind == "catalog":
            items = self.discover(opener=opener)
            return FetchResult(rows=items, next_cursor=None,
                               endpoint=spec.key, total=len(items), requests=1)
        if spec.kind == "generic":
            raise ValueError(
                "the generic fetched_rows dataset has no identifier of its "
                "own; call fetch_dataset(dataset_key, ...) instead")
        return self._fetch_page(spec.key, spec.path, params, cursor, opener)

    def fetch_dataset(
        self,
        dataset_key: str,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """One page of an ARBITRARY catalog dataset by its DKAN UUID.

        This is the generic escape hatch behind the ``fetched_rows``
        dataset: anything :meth:`discover` lists is fetchable here with
        no schema edit.
        """
        return self._fetch_page(dataset_key, datastore_path(dataset_key),
                                params, cursor, opener)

    def fetch_all(
        self,
        spec: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = MAX_PAGES_DEFAULT,
    ) -> List[Dict[str, Any]]:
        """Drive :meth:`fetch` under a page bound, returning the rows.

        ``max_pages`` defaults deliberately low (5); pass a larger value
        (or ``None`` for the hard ceiling) for a full drain — see module
        docstring for why.
        """
        pages = MAX_PAGES_HARD if max_pages is None else min(int(max_pages),
                                                             MAX_PAGES_HARD)
        rows: List[Dict[str, Any]] = []
        cursor: Optional[Dict[str, Any]] = None
        for _ in range(max(pages, 1)):
            step = self.fetch(spec, params, cursor, opener=opener)
            rows.extend(step.rows)
            if step.next_cursor is None:
                break
            cursor = step.next_cursor
        return rows

    # ── refresh: fetch + normalize + upsert ────────────────────────────
    def refresh_catalog(self, store: Any, *, opener: Optional[Opener] = None
                        ) -> Dict[str, int]:
        """Sync the full catalog into ``medicaid_data_catalog``."""
        spec = get_endpoint("catalog")
        items = self.discover(opener=opener)
        res = normalize(spec, items)
        written = sum(store.upsert(t, rows) for t, rows in res.rows.items())
        return {"fetched": len(items), "written": written}

    def refresh(
        self,
        store: Any,
        key: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = MAX_PAGES_DEFAULT,
    ) -> Dict[str, int]:
        """Fetch + normalize + upsert one dataset; returns counts.

        ``key`` is either a registered endpoint key (``nadac_2026``) —
        rows land in its canonical table — or a raw DKAN UUID / unknown
        key, which lands as generic rows in ``medicaid_data_rows``.
        """
        spec = ENDPOINTS.get(key)
        if spec is not None and spec.kind == "catalog":
            return self.refresh_catalog(store, opener=opener)
        if spec is not None and spec.kind == "datastore":
            raw = self.fetch_all(spec, params, opener=opener,
                                 max_pages=max_pages)
            res = normalize(spec, raw)
            written = sum(store.upsert(t, rows) for t, rows in res.rows.items())
            return {"fetched": len(raw), "written": written}
        # Generic path: any catalog UUID (or an alias the caller manages).
        pages = MAX_PAGES_HARD if max_pages is None else min(int(max_pages),
                                                             MAX_PAGES_HARD)
        fetched = written = 0
        cursor: Optional[Dict[str, Any]] = None
        fetched_at = _utc_now()
        # Key integrity for the shared rows table: the non-paging params
        # (filters and passthrough conditions) sign the row keys so
        # refreshes of the same dataset with different filters coexist
        # instead of silently overwriting each other (row_idx is only
        # meaningful within one filter slice).
        slice_params = {k: v for k, v in (params or {}).items()
                        if str(k) not in ("limit", "offset")}
        for _ in range(max(pages, 1)):
            step = self.fetch_dataset(key, params, cursor, opener=opener)
            start_idx = int((cursor or {}).get("offset", 0))
            res = normalize_generic(key, step.rows, start_idx=start_idx,
                                    fetched_at=fetched_at,
                                    slice_params=slice_params)
            for t, rows in res.rows.items():
                written += store.upsert(t, rows)
            fetched += len(step.rows)
            if step.next_cursor is None:
                break
            cursor = step.next_cursor
        return {"fetched": fetched, "written": written}

    # ── one limit/offset page ──────────────────────────────────────────
    def _fetch_page(self, key: str, path: str,
                    params: Optional[Dict[str, Any]],
                    cursor: Optional[Dict[str, Any]],
                    opener: Optional[Opener]) -> FetchResult:
        params = dict(params or {})
        filters = params.pop("filters", None) or {}
        req: Dict[str, Any] = dict(params)
        req.setdefault("limit", self.page_limit)
        offset = int((cursor or {}).get("offset", 0))
        req["offset"] = offset
        for i, (col, value) in enumerate(sorted(filters.items())):
            req[f"conditions[{i}][property]"] = col
            req[f"conditions[{i}][value]"] = value
            req[f"conditions[{i}][operator]"] = "="
        payload = self.transport.get_json(path, req, opener=opener)
        if not isinstance(payload, dict):
            payload = {}
        results = payload.get("results") or []
        if not isinstance(results, list):
            results = []
        total = int(payload.get("count") or 0)
        got = len(results)
        next_offset = offset + got
        # A short (or empty) page means the datastore is exhausted; DKAN
        # returns an empty results list past the end rather than erroring.
        exhausted = got < int(req["limit"]) or (total and next_offset >= total)
        next_cursor = None if exhausted else {"offset": next_offset}
        return FetchResult(rows=results, next_cursor=next_cursor,
                           endpoint=key, total=total, requests=1)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
