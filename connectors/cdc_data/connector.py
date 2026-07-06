"""The cdc_data connector: ``discover()`` + ``fetch()`` + ``refresh()``.

Pagination, throttling and retries all live *inside* the connector —
callers (the pipeline, the registry, the lookup handlers) never see
Socrata's native ``$limit``/``$offset`` or the metadata API's
``limit``/``page``.

Two pagination shapes, absorbed here
------------------------------------
* SODA row endpoints (``/resource/{4x4}.json``) return a bare JSON array
  and page by ``$limit``/``$offset``. Pages without an explicit order are
  NOT guaranteed stable, so every request pins ``$order=:id`` (Socrata's
  documented stable system ordering) unless the caller supplies an
  ``$order`` of their own.
* The catalog metadata API (``/api/views/metadata/v1``) also returns a
  JSON array but pages by ``limit`` + **1-based ``page``** — VERIFIED
  LIVE 2026-07-06: the documented ``offset`` param is silently ignored on
  data.cdc.gov and would replay page 1 forever.

Both loops stop on the first short/empty page.

Politeness cap: every fetch takes a ``max_pages`` bound (default
:data:`DEFAULT_MAX_PAGES` = 5) so an accidental "give me BRFSS" doesn't
hammer the API with a ~2M-row pull; pass a larger ``max_pages``
explicitly (bounded by :data:`MAX_PAGES_HARD_CAP`) for a deliberate bulk
run. ``discover`` uses its own default sized to drain the whole catalog
(~1.5k datasets / 500-per-page ≈ 4 pages).
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Dict, List, Optional, Union

from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .normalize import normalize, normalize_generic
from .transport import CdcSodaTransport, Opener

DEFAULT_MAX_PAGES = 5          # polite bound on any single fetch call
CATALOG_MAX_PAGES = 20         # catalog is ~4 pages at 500/page; headroom
MAX_PAGES_HARD_CAP = 1000      # absolute bound: no loop can run away

_SODA_LIMIT_CAP = 50_000       # Socrata's own per-request $limit ceiling


@dataclass
class FetchResult:
    """One ``fetch`` call's output (paging already absorbed)."""

    rows: List[Dict[str, Any]]
    endpoint: str
    pages: int = 0
    requests: int = 0
    exhausted: bool = True     # False when the max_pages cap cut the pull short
    params: Dict[str, Any] = dc_field(default_factory=dict)


class CdcDataConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full paging state machine with a fake
    server.
    """

    def __init__(
        self,
        transport: Optional[CdcSodaTransport] = None,
        *,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or CdcSodaTransport.from_env()
        self._sleep = sleep

    # ── discovery: sync the full data.cdc.gov catalog ─────────────────
    def discover(
        self,
        *,
        opener: Optional[Opener] = None,
        store: Any = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Page the Socrata metadata API and return normalized catalog rows.

        This is the "every dataset connected" sync: each dataset on
        data.cdc.gov lands as one ``cdc_data_catalog`` row. When a
        ``store`` is passed the rows are also upserted (idempotent on the
        4x4 id), making ``discover(store=...)`` the one-call catalog
        refresh.
        """
        spec = get_endpoint("catalog")
        limit = int(page_size or spec.page_size)
        cap = _clamp_pages(max_pages, CATALOG_MAX_PAGES)
        raw: List[Dict[str, Any]] = []
        for page in range(1, cap + 1):
            payload = self.transport.get_json(
                spec.path, {"limit": limit, "page": page}, opener=opener)
            items = payload if isinstance(payload, list) else []
            raw.extend(r for r in items if isinstance(r, dict))
            if len(items) < limit:      # short/empty page → catalog drained
                break
        rows = normalize(spec, raw).rows.get("cdc_data_catalog", [])
        if store is not None:
            store.upsert("cdc_data_catalog", rows)
        return rows

    # ── fetch: absorb SODA $limit/$offset paging ──────────────────────
    def fetch(
        self,
        dataset: Union[str, EndpointSpec],
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> FetchResult:
        """Fetch raw rows for a registered dataset, paging absorbed.

        ``dataset`` is an endpoint key (``"places_county"``), a full
        dataset id (``"cdc_data_places_county"``), or an
        :class:`EndpointSpec`. ``params`` are passed straight to SoQL —
        plain ``column=value`` equality or ``$where``/``$select``/
        ``$order`` — and never include paging: ``$limit``/``$offset``
        belong to this loop.
        """
        spec = dataset if isinstance(dataset, EndpointSpec) else _resolve(dataset)
        if spec.kind == "catalog":
            rows = self.discover(opener=opener, max_pages=max_pages,
                                 page_size=page_size)
            return FetchResult(rows=rows, endpoint=spec.key,
                               pages=0, requests=0, exhausted=True)
        if spec.kind == "generic":
            raise ValueError(
                "the generic dataset needs a concrete 4x4 id — call "
                "fetch_dataset(dataset_key, ...) instead")
        return self._fetch_resource(
            spec.path, spec.key, dict(spec.default_params), params,
            opener=opener,
            max_pages=_clamp_pages(max_pages, DEFAULT_MAX_PAGES),
            page_size=int(page_size or spec.page_size))

    def fetch_dataset(
        self,
        dataset_key: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> FetchResult:
        """Fetch raw rows from ANY data.cdc.gov 4x4 dataset on demand.

        The escape hatch that keeps the whole catalog reachable: rows go
        through :func:`normalize_generic` into ``cdc_data_rows`` (see
        :meth:`refresh`), so even unregistered datasets stay queryable
        through the uniform engine. An unknown 4x4 yields zero rows (the
        API 404 folds to empty) rather than an exception.
        """
        key = str(dataset_key).strip()
        spec = ENDPOINTS["fetched_rows"]
        return self._fetch_resource(
            f"/resource/{key}.json", key, dict(spec.default_params), params,
            opener=opener,
            max_pages=_clamp_pages(max_pages, DEFAULT_MAX_PAGES),
            page_size=int(page_size or spec.page_size))

    def _fetch_resource(
        self,
        path: str,
        endpoint_key: str,
        base_params: Dict[str, Any],
        params: Optional[Dict[str, Any]],
        *,
        opener: Optional[Opener],
        max_pages: int,
        page_size: int,
    ) -> FetchResult:
        req = dict(base_params)
        req.update(params or {})
        req.pop("$limit", None)      # paging belongs to this loop only
        req.pop("$offset", None)
        # Stable paging needs an explicit order; :id is Socrata's
        # documented system ordering (verified live).
        req.setdefault("$order", ":id")
        limit = max(1, min(page_size, _SODA_LIMIT_CAP))

        rows: List[Dict[str, Any]] = []
        pages = 0
        requests = 0
        exhausted = True
        offset = 0
        while pages < max_pages:
            page_params = dict(req)
            page_params["$limit"] = limit
            page_params["$offset"] = offset
            payload = self.transport.get_json(path, page_params, opener=opener)
            items = payload if isinstance(payload, list) else []
            rows.extend(r for r in items if isinstance(r, dict))
            pages += 1
            requests += 1
            if len(items) < limit:   # short/empty page → dataset drained
                break
            offset += limit
        else:
            exhausted = False        # cap hit with a full final page
        return FetchResult(rows=rows, endpoint=endpoint_key, pages=pages,
                           requests=requests, exhausted=exhausted, params=req)

    # ── refresh: fetch + normalize + upsert ───────────────────────────
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
        """Fetch a dataset, normalize it and upsert into ``store``.

        ``dataset`` may be an endpoint key, a full ``cdc_data_*`` dataset
        id, or a raw 4x4 id (which lands in the generic
        ``cdc_data_rows`` table). Returns
        ``{"dataset", "endpoint", "fetched", "exhausted", "written"}``
        where ``written`` maps table → row count.
        """
        name = str(dataset).strip()
        spec = _try_resolve(name)

        if spec is not None and spec.kind == "catalog":
            rows = self.discover(opener=opener, store=store,
                                 max_pages=max_pages, page_size=page_size)
            return {"dataset": spec.dataset_id, "endpoint": spec.key,
                    "fetched": len(rows), "exhausted": True,
                    "written": {"cdc_data_catalog": len(rows)}}

        if spec is not None and spec.kind == "curated":
            result = self.fetch(spec, params, opener=opener,
                                max_pages=max_pages, page_size=page_size)
            normalized = normalize(spec, result.rows)
            written = {t: store.upsert(t, rs) for t, rs in normalized.rows.items()}
            return {"dataset": spec.dataset_id, "endpoint": spec.key,
                    "fetched": len(result.rows), "exhausted": result.exhausted,
                    "written": written}

        # Anything else is treated as a raw 4x4 for the generic table
        # (including an explicit "fetched_rows" key with a 4x4 in params).
        key = name
        if spec is not None and spec.kind == "generic":
            key = str((params or {}).pop("dataset_key", "") or "").strip()
            if not key:
                raise ValueError(
                    "refresh('fetched_rows') needs params={'dataset_key': <4x4>}")
        result = self.fetch_dataset(key, params, opener=opener,
                                    max_pages=max_pages, page_size=page_size)
        # Key integrity for the shared rows table: the caller's non-paging
        # SoQL params sign the row keys so refreshes of the same dataset
        # with different $where/column filters coexist instead of silently
        # overwriting each other (row_idx is only meaningful within one
        # filter slice; refresh itself always starts at offset 0).
        slice_params = {k: v for k, v in (params or {}).items()
                        if str(k) not in ("$limit", "$offset")}
        rows = normalize_generic(key, result.rows, slice_params=slice_params)
        n = store.upsert("cdc_data_rows", rows)
        return {"dataset": "cdc_data_fetched_rows", "endpoint": key,
                "fetched": len(result.rows), "exhausted": result.exhausted,
                "written": {"cdc_data_rows": n}}


# ── helpers ───────────────────────────────────────────────────────────
def _resolve(name: str) -> EndpointSpec:
    spec = _try_resolve(name)
    if spec is None:
        raise KeyError(
            f"unknown cdc_data dataset {name!r}; known keys: "
            f"{sorted(ENDPOINTS)} (or pass a raw 4x4 to fetch_dataset)")
    return spec


def _try_resolve(name: str) -> Optional[EndpointSpec]:
    """Accept a bare endpoint key or the estate-wide ``cdc_data_*`` id."""
    key = name[len("cdc_data_"):] if name.startswith("cdc_data_") else name
    return ENDPOINTS.get(key)


def _clamp_pages(requested: Optional[int], default: int) -> int:
    """None → the modest default; explicit asks are honoured up to the cap."""
    if requested is None:
        return default
    try:
        n = int(requested)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, MAX_PAGES_HARD_CAP))
