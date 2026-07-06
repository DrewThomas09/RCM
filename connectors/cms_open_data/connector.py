"""The CMS Open Data connector: ``discover()`` + ``fetch()`` + ``refresh()``.

Pagination, rate-limit handling and retries all live *inside* the
connector — callers (the pipeline, the registry, the lookup handlers)
never see the data API's native ``size``/``offset``.

The one pagination shape, absorbed here
---------------------------------------
``GET /data-api/v1/dataset/{uuid}/data?size=N&offset=M`` returns a bare
JSON array of row objects. Paging is offset arithmetic: advance
``offset`` by the page length until a short page (dataset exhausted) or
the ``max_pages`` cap. The cap defaults to :data:`DEFAULT_MAX_PAGES` (5)
so an accidental "fetch everything" against a 28-million-row dataset
stays a bounded, polite probe — callers that really want more pass
``max_pages`` explicitly. ``FetchResult.truncated`` says whether the cap
(not exhaustion) stopped the loop.

UUID re-resolution
------------------
Dataset version UUIDs rotate when CMS publishes new data. Every fetch
therefore prefers the UUID re-resolved from a synced catalog table
(matched by the spec's title slug) and falls back to the literal pinned
in endpoints.py, so a stale pin degrades to "last-known version" instead
of breaking. Pass ``store=`` to opt in; without a store the pin is used
as-is.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .endpoints import (
    CATALOG_TABLE,
    ENDPOINTS,
    GENERIC_TABLE,
    EndpointSpec,
    find_endpoint,
)
from .normalize import (
    normalize_catalog,
    normalize_curated,
    normalize_generic,
    slugify,
)
from .transport import CmsOpenDataTransport, Opener

DEFAULT_PAGE_SIZE = 1000     # polite default; the API accepts up to 5000
MAX_PAGE_SIZE = 5000
DEFAULT_MAX_PAGES = 5        # hard cap per fetch unless the caller raises it

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                      r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

# Params the data API understands natively; anything else the caller
# passes is treated as a column equality and wrapped as filter[COL]=v.
_NATIVE_PARAMS = {"size", "offset", "keyword", "column"}


@dataclass
class FetchResult:
    """One ``fetch`` call's output (native paging already absorbed)."""

    rows: List[Dict[str, Any]]
    endpoint: str                 # spec key or generic dataset_key
    uuid: str = ""                # the UUID actually queried
    pages: int = 0
    truncated: bool = False       # stopped by max_pages with a full last page
    requests: int = 0
    start_offset: int = 0         # dataset offset of rows[0] (absolute row_idx)

    @property
    def done(self) -> bool:
        return not self.truncated


class CmsOpenDataConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full paging loop with a fake server.
    """

    def __init__(
        self,
        transport: Optional[CmsOpenDataTransport] = None,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        self.transport = transport or CmsOpenDataTransport.from_env()
        self.page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
        self.max_pages = max(1, int(max_pages))

    # ── discovery: the DCAT catalog ───────────────────────────────────
    def discover(self, *, opener: Optional[Opener] = None) -> List[Dict[str, Any]]:
        """Download ``data.json`` and return normalized catalog rows.

        One row per dataset data.cms.gov publishes — this is what makes
        "every dataset connected" true. Pure fetch+normalize; use
        :meth:`sync_catalog` to persist.
        """
        doc = self.transport.get_json("/data.json", opener=opener)
        return normalize_catalog(doc if isinstance(doc, dict) else {})

    def sync_catalog(self, store: Any, *, opener: Optional[Opener] = None) -> int:
        """discover() + upsert into ``cms_open_data_catalog``; returns count."""
        rows = self.discover(opener=opener)
        return store.upsert(CATALOG_TABLE, rows)

    # ── UUID re-resolution ────────────────────────────────────────────
    def resolve_uuid(self, spec: EndpointSpec, store: Any = None) -> str:
        """Current UUID for a curated spec: catalog-resolved, else pinned.

        The catalog row is matched by the spec's title slug — titles are
        the stable handle across version rotations, UUIDs are not.
        """
        if store is not None:
            try:
                hit = store.fetchall(
                    f"SELECT uuid FROM {CATALOG_TABLE} "
                    "WHERE dataset_key = ? AND uuid <> ''",
                    (slugify(spec.title),))
            except Exception:
                hit = []
            if hit:
                return str(hit[0]["uuid"])
        return spec.uuid

    # ── the paged fetch ───────────────────────────────────────────────
    def fetch(
        self,
        dataset: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        store: Any = None,
    ) -> FetchResult:
        """Fetch raw rows for a registered dataset, absorbing paging.

        ``dataset`` is a spec key or full dataset_id. Filters use the
        API's ORIGINAL column names (``{"HCPCS_Cd": "J9271"}`` becomes
        ``filter[HCPCS_Cd]=J9271``); ``keyword`` passes through for
        full-text search. Post-ingest queries use the uniform snake_cased
        grammar instead — this native surface exists only for targeted
        pulls.
        """
        spec = find_endpoint(dataset)
        if spec is None:
            raise KeyError(
                f"unknown CMS Open Data dataset {dataset!r}; "
                f"use fetch_dataset() for arbitrary catalog datasets")
        if spec.kind == "catalog":
            rows = self.discover(opener=opener)
            return FetchResult(rows=rows, endpoint=spec.key, pages=1, requests=1)
        if spec.kind == "generic":
            raise KeyError(
                "the generic fetched_rows dataset needs a concrete catalog "
                "dataset_key or UUID — call fetch_dataset() instead")
        uuid = self.resolve_uuid(spec, store)
        return self._fetch_pages(spec.key, uuid, spec.default_params, params,
                                 opener=opener, max_pages=max_pages,
                                 page_size=page_size)

    def fetch_dataset(
        self,
        dataset_key_or_uuid: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        store: Any = None,
    ) -> Tuple[str, FetchResult]:
        """Fetch raw rows for ANY catalog dataset (on-demand, generic path).

        Accepts a catalog ``dataset_key`` slug (resolved to the current
        UUID via the synced catalog table) or a raw dataset UUID.
        Returns ``(dataset_key, FetchResult)`` — the key is what the
        generic normalizer slices the shared table by.
        """
        handle = str(dataset_key_or_uuid).strip()
        if _UUID_RE.match(handle):
            uuid = handle
            dataset_key = self._catalog_key_for_uuid(store, uuid) or uuid
        else:
            dataset_key = slugify(handle)
            uuid = self._catalog_uuid_for_key(store, dataset_key)
            if not uuid:
                raise KeyError(
                    f"dataset_key {dataset_key!r} not found in the synced "
                    "catalog — run discover first, or pass the dataset UUID")
        res = self._fetch_pages(dataset_key, uuid, {}, params, opener=opener,
                                max_pages=max_pages, page_size=page_size)
        return dataset_key, res

    def stats(self, dataset: str, *, opener: Optional[Opener] = None,
              store: Any = None) -> Optional[Dict[str, Any]]:
        """The dataset's ``/data/stats`` envelope ({found_rows, total_rows}).

        Returns ``None`` when the endpoint is absent for this dataset —
        callers absorb totals by paging until a short page instead.
        """
        spec = find_endpoint(dataset)
        if spec is not None and spec.kind == "curated":
            uuid = self.resolve_uuid(spec, store)
        elif _UUID_RE.match(str(dataset).strip()):
            uuid = str(dataset).strip()
        else:
            uuid = self._catalog_uuid_for_key(store, slugify(dataset))
        if not uuid:
            return None
        doc = self.transport.get_json(
            f"/data-api/v1/dataset/{uuid}/data/stats", opener=opener)
        return doc if isinstance(doc, dict) else None

    # ── fetch + normalize + upsert convenience ────────────────────────
    def refresh(
        self,
        store: Any,
        dataset: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch a dataset, normalize it, upsert it; return the counts.

        Routes by kind: ``catalog`` syncs the catalog table; a curated
        key lands in its own canonical table; anything else (a catalog
        slug or UUID) lands in the generic ``cms_open_data_rows`` store.
        """
        spec = find_endpoint(dataset)
        if spec is not None and spec.kind == "catalog":
            rows = self.discover(opener=opener)
            n = store.upsert(CATALOG_TABLE, rows)
            return {"dataset": spec.key, "table": CATALOG_TABLE,
                    "fetched": len(rows), "upserted": n,
                    "pages": 1, "truncated": False}
        if spec is not None and spec.kind == "curated":
            res = self.fetch(spec.key, params, opener=opener,
                             max_pages=max_pages, page_size=page_size,
                             store=store)
            rows = normalize_curated(spec, res.rows)
            n = store.upsert(spec.target_table, rows)
            return {"dataset": spec.key, "table": spec.target_table,
                    "uuid": res.uuid, "fetched": len(res.rows),
                    "upserted": n, "pages": res.pages,
                    "truncated": res.truncated}
        # Generic on-demand path (also reached for spec.kind == "generic"
        # only via a concrete key/uuid, enforced by fetch_dataset).
        dataset_key, res = self.fetch_dataset(
            dataset, params, opener=opener, max_pages=max_pages,
            page_size=page_size, store=store)
        # Key integrity for the shared rows table: start_idx is the
        # fetch's absolute start offset (a mid-dataset resume must not
        # re-key its rows as 0..N) and the non-paging params sign the
        # key so differently-filtered fetches coexist instead of
        # silently overwriting each other.
        slice_params = {k: v for k, v in (params or {}).items()
                        if str(k) not in ("size", "offset")}
        rows = normalize_generic(dataset_key, res.rows,
                                 start_idx=res.start_offset,
                                 slice_params=slice_params)
        n = store.upsert(GENERIC_TABLE, rows)
        return {"dataset": dataset_key, "table": GENERIC_TABLE,
                "uuid": res.uuid, "fetched": len(res.rows), "upserted": n,
                "pages": res.pages, "truncated": res.truncated}

    # ── internals ─────────────────────────────────────────────────────
    def _fetch_pages(
        self,
        endpoint_key: str,
        uuid: str,
        default_params: Dict[str, str],
        params: Optional[Dict[str, Any]],
        *,
        opener: Optional[Opener],
        max_pages: Optional[int],
        page_size: Optional[int],
    ) -> FetchResult:
        merged: Dict[str, Any] = dict(default_params)
        merged.update(params or {})
        native = self._native_params(merged)
        # Explicit page_size wins; then a size in params/default_params;
        # then the connector default. Clamped to the API's 5000 max.
        size = int(page_size if page_size is not None
                   else native.pop("size", self.page_size))
        size = max(1, min(size, MAX_PAGE_SIZE))
        offset = int(native.pop("offset", 0))
        start_offset = offset
        cap = self.max_pages if max_pages is None else max(1, int(max_pages))

        path = f"/data-api/v1/dataset/{uuid}/data"
        rows: List[Dict[str, Any]] = []
        pages = 0
        truncated = False
        start_requests = self.transport.requests_made
        while pages < cap:
            page = self.transport.get_json(
                path, {**native, "size": size, "offset": offset},
                opener=opener)
            if not isinstance(page, list):
                page = []
            rows.extend(r for r in page if isinstance(r, dict))
            pages += 1
            offset += len(page)
            if len(page) < size:
                break
        else:
            truncated = True
        return FetchResult(rows=rows, endpoint=endpoint_key, uuid=uuid,
                           pages=pages, truncated=truncated,
                           requests=self.transport.requests_made - start_requests,
                           start_offset=start_offset)

    @staticmethod
    def _native_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """Map caller params onto the API's native query grammar.

        ``size``/``offset``/``keyword``/``column`` and pre-formed
        ``filter[...]`` keys pass through; every other key is a column
        equality and becomes ``filter[COL]=value``.
        """
        out: Dict[str, Any] = {}
        for k, v in params.items():
            key = str(k)
            if key in _NATIVE_PARAMS or key.startswith("filter"):
                out[key] = v
            else:
                out[f"filter[{key}]"] = v
        return out

    def _catalog_uuid_for_key(self, store: Any, dataset_key: str) -> str:
        if store is None:
            return ""
        try:
            hit = store.fetchall(
                f"SELECT uuid FROM {CATALOG_TABLE} "
                "WHERE dataset_key = ? AND uuid <> ''", (dataset_key,))
        except Exception:
            return ""
        return str(hit[0]["uuid"]) if hit else ""

    def _catalog_key_for_uuid(self, store: Any, uuid: str) -> str:
        if store is None:
            return ""
        try:
            hit = store.fetchall(
                f"SELECT dataset_key FROM {CATALOG_TABLE} WHERE uuid = ?",
                (uuid,))
        except Exception:
            return ""
        return str(hit[0]["dataset_key"]) if hit else ""
