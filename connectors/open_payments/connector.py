"""The Open Payments connector: ``discover()`` + ``fetch()`` + ``refresh()``.

Pagination, rate-limit handling and retries all live *inside* the
connector — callers (the pipeline, the registry, the lookup handlers)
never see DKAN's native ``limit``/``offset`` or ``conditions[...]``
query grammar.

The DKAN datastore envelope (verified live 2026-07-06)::

    {"count": 15498687, "query": {...}, "results": [...], "schema": {...}}

paged by ``limit``/``offset`` with ``limit`` hard-capped at **500** by
the server (400 above that). ``count=false&schema=false`` trims the
envelope, so we only pay for the (expensive, filtered-COUNT) ``count``
on the first page of a fetch.

SCALE GUARDRAIL — this is the load-bearing design constraint: General
Payment Data years exceed 15M rows. ``fetch`` therefore NEVER defaults
to a full pull:

  * ``max_pages`` defaults to :data:`DEFAULT_MAX_PAGES` (3 → at most
    1,500 rows per call) and is clamped to :data:`MAX_PAGES_CAP` even
    when the caller asks for more;
  * fetches are **filter-driven**: pass ``filters`` (e.g.
    ``{"recipient_state": "VT"}`` or ``{"covered_recipient_npi": ...}``)
    and they become DKAN ``conditions`` evaluated server-side, so the
    page budget is spent on the slice you actually want;
  * a fetch that stops with a full last page reports ``truncated=True``
    so callers know rows remain — narrow the filter or raise
    ``max_pages`` deliberately.

``discover()`` syncs the catalog (74 datasets, one cheap GET) and
``fetch_dataset()`` pulls ANY catalog dataset by UUID into the generic
JSON rows table, so older program years need no code changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional

from .endpoints import (DATASTORE_PATH_TEMPLATE, ENDPOINTS, EndpointSpec,
                        get_endpoint)
from .normalize import NormalizeResult, normalize, normalize_generic
from .transport import Opener, OpenPaymentsTransport

# Server-verified page ceiling: the datastore 400s on limit > 500.
PAGE_LIMIT = 500
# Modest defaults so an unfiltered call against a 15M-row payment file
# costs at most a few requests. Deliberate bulk pulls raise max_pages
# explicitly — and still hit the hard cap.
DEFAULT_MAX_PAGES = 3
MAX_PAGES_CAP = 200          # 200 × 500 = 100k rows, the per-call ceiling

# field__op filter grammar → DKAN condition operators. Equality is the
# default; "like" values use % wildcards (DKAN evaluates them server-side).
_CONDITION_OPS = {
    "eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
    "like": "like",
}


@dataclass
class FetchResult:
    """One ``fetch``/``fetch_dataset`` call's output (paging absorbed)."""

    rows: List[Dict[str, Any]]
    endpoint: str                     # spec key, or dataset UUID for generic
    total: int = 0                    # server-side count for the filter slice
    pages: int = 0
    truncated: bool = False           # stopped at max_pages with more left
    requests: int = 0
    filters: Dict[str, Any] = dc_field(default_factory=dict)
    start_offset: int = 0             # datastore offset of rows[0]

    @property
    def done(self) -> bool:
        return not self.truncated


class OpenPaymentsConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full paging state machine with a fake
    server.
    """

    def __init__(
        self,
        transport: Optional[OpenPaymentsTransport] = None,
        *,
        page_size: int = PAGE_LIMIT,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        self.transport = transport or OpenPaymentsTransport.from_env()
        self.page_size = max(1, min(int(page_size), PAGE_LIMIT))
        self.max_pages = max(1, min(int(max_pages), MAX_PAGES_CAP))

    # ── discovery: sync the whole catalog ─────────────────────────────
    def discover(self, *, opener: Optional[Opener] = None
                 ) -> List[Dict[str, Any]]:
        """Fetch the DKAN metastore catalog and return normalized
        ``open_payments_catalog`` rows (one per dataset, ~74 live).

        This is the "every dataset connected" guarantee: anything listed
        here is fetchable by UUID via :meth:`fetch_dataset` even without
        a curated spec.
        """
        spec = get_endpoint("catalog")
        payload = self.transport.get_json(spec.path, opener=opener)
        items = payload if isinstance(payload, list) else []
        res = normalize(spec, items)
        return res.rows.get(spec.target_table, [])

    def specs(self) -> List[EndpointSpec]:
        """Enumerate the declarative endpoint specs (no network)."""
        return list(ENDPOINTS.values())

    # ── curated datastore fetch ───────────────────────────────────────
    def fetch(
        self,
        key: str,
        filters: Optional[Dict[str, Any]] = None,
        *,
        params: Optional[Dict[str, Any]] = None,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> FetchResult:
        """Fetch raw rows for a curated dataset, absorbing limit/offset.

        ``filters`` become server-side DKAN conditions (equality by
        default; ``field__like``/``__gt``/... for other operators).
        Returns raw datastore rows — :mod:`normalize` converts them.
        """
        spec = get_endpoint(key) if isinstance(key, str) else key
        if spec.kind == "catalog":
            rows = self._fetch_catalog_raw(opener)
            return FetchResult(rows=rows, endpoint=spec.key, total=len(rows),
                               pages=1, requests=1)
        if spec.kind == "generic":
            raise ValueError(
                "the generic slot has no fixed dataset — call "
                "fetch_dataset(dataset_key, ...) with a catalog UUID")
        return self._paged_fetch(spec.path, spec.key, filters,
                                 params=params, opener=opener,
                                 max_pages=max_pages, page_size=page_size)

    def fetch_dataset(
        self,
        dataset_key: str,
        filters: Optional[Dict[str, Any]] = None,
        *,
        params: Optional[Dict[str, Any]] = None,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> FetchResult:
        """Fetch ANY catalog dataset by its DKAN UUID (generic slot).

        Same paging/filter engine as curated fetches; rows land in the
        ``open_payments_rows`` JSON table via
        :func:`normalize.normalize_generic`.
        """
        path = DATASTORE_PATH_TEMPLATE.format(identifier=dataset_key)
        return self._paged_fetch(path, dataset_key, filters, params=params,
                                 opener=opener, max_pages=max_pages,
                                 page_size=page_size)

    # ── fetch + normalize + upsert convenience ────────────────────────
    def refresh(
        self,
        store: Any,
        key: str,
        filters: Optional[Dict[str, Any]] = None,
        *,
        dataset_key: str = "",
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch a dataset, normalize it, upsert it; return counts.

        ``key`` is an endpoint key (``catalog``, ``general_payments_2024``,
        ...); for ``fetched_rows`` pass the target catalog UUID as
        ``dataset_key``. Mirrors how the estate CLIs drive ingest.
        """
        spec = get_endpoint(key)
        if spec.kind == "generic":
            if not dataset_key:
                raise ValueError("refresh('fetched_rows', ...) needs "
                                 "dataset_key=<catalog uuid>")
            result = self.fetch_dataset(dataset_key, filters, opener=opener,
                                        max_pages=max_pages,
                                        page_size=page_size)
            # Key integrity for the shared rows table: row_offset is the
            # fetch's absolute start offset (a mid-dataset resume must
            # not re-key its rows as 0..N) and the filters sign the key
            # so differently-filtered fetches coexist instead of
            # silently overwriting each other.
            norm = normalize_generic(dataset_key, result.rows,
                                     row_offset=result.start_offset,
                                     slice_params=dict(filters or {}))
        elif spec.kind == "catalog":
            rows = self.discover(opener=opener)
            norm = NormalizeResult(rows={spec.target_table: rows})
            result = FetchResult(rows=rows, endpoint=spec.key,
                                 total=len(rows), pages=1, requests=1)
        else:
            result = self.fetch(key, filters, opener=opener,
                                max_pages=max_pages, page_size=page_size)
            norm = normalize(spec, result.rows)
        upserted = 0
        for table, table_rows in norm.rows.items():
            upserted += store.upsert(table, table_rows)
        return {
            "dataset_id": spec.dataset_id,
            "endpoint": result.endpoint,
            "table": spec.target_table,
            "fetched": len(result.rows),
            "upserted": upserted,
            "pages": result.pages,
            "total": result.total,
            "truncated": result.truncated,
            "unmapped": dict(norm.unmapped),
        }

    # ── the limit/offset pager ────────────────────────────────────────
    def _paged_fetch(self, path: str, endpoint_key: str,
                     filters: Optional[Dict[str, Any]], *,
                     params: Optional[Dict[str, Any]],
                     opener: Optional[Opener],
                     max_pages: Optional[int],
                     page_size: Optional[int]) -> FetchResult:
        limit = max(1, min(int(page_size or self.page_size), PAGE_LIMIT))
        budget = max(1, min(int(max_pages or self.max_pages), MAX_PAGES_CAP))
        cond = conditions_params(filters or {})
        base_params: Dict[str, Any] = dict(params or {})
        offset = int(base_params.pop("offset", 0))
        start_offset = offset
        start_requests = self.transport.requests_made

        rows: List[Dict[str, Any]] = []
        total = 0
        pages = 0
        exhausted = False
        while pages < budget:
            req: Dict[str, Any] = dict(base_params)
            req.update(cond)
            req["limit"] = limit
            req["offset"] = offset
            # The COUNT over a filtered 15M-row table is the expensive
            # part of the query; only pay for it once per fetch.
            req["schema"] = "false"
            if pages > 0:
                req["count"] = "false"
            payload = self.transport.get_json(path, req, opener=opener)
            results = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(results, list):
                results = []
            if pages == 0 and isinstance(payload, dict):
                try:
                    total = int(payload.get("count") or 0)
                except (TypeError, ValueError):
                    total = 0
            rows.extend(r for r in results if isinstance(r, dict))
            got = len(results)
            offset += got
            pages += 1
            if got < limit:          # short page → the slice is drained
                exhausted = True
                break
        truncated = not exhausted and (total == 0 or offset < total)
        return FetchResult(
            rows=rows, endpoint=endpoint_key, total=total, pages=pages,
            truncated=truncated,
            requests=self.transport.requests_made - start_requests,
            filters=dict(filters or {}),
            start_offset=start_offset,
        )

    def _fetch_catalog_raw(self, opener: Optional[Opener]
                           ) -> List[Dict[str, Any]]:
        payload = self.transport.get_json(get_endpoint("catalog").path,
                                          opener=opener)
        return payload if isinstance(payload, list) else []


def conditions_params(filters: Dict[str, Any]) -> Dict[str, str]:
    """Flatten a filter dict into DKAN ``conditions[i][...]`` params.

    ``{"recipient_state": "VT", "total_amount_of_payment_usdollars__gt":
    "500"}`` becomes the indexed property/value/operator triplets DKAN
    expects (verified live: the query echo confirms the parse). Keys are
    sorted so the emitted URL — and test assertions — are deterministic.
    Keys starting with ``_`` are reserved for future hints and skipped.
    """
    out: Dict[str, str] = {}
    i = 0
    for key in sorted(filters):
        if key.startswith("_"):
            continue
        value = filters[key]
        prop, op = key, "eq"
        if "__" in key:
            candidate_prop, candidate_op = key.rsplit("__", 1)
            if candidate_op in _CONDITION_OPS:
                prop, op = candidate_prop, candidate_op
        out[f"conditions[{i}][property]"] = prop
        out[f"conditions[{i}][value]"] = str(value)
        out[f"conditions[{i}][operator]"] = _CONDITION_OPS[op]
        i += 1
    return out
