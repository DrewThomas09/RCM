"""The data.healthcare.gov connector: ``discover()`` + ``fetch()`` + ``refresh()``.

Pagination, throttling and retries all live *inside* the connector —
callers (the pipeline, the registry, the lookup handlers) never see
DKAN's native ``limit``/``offset``.

The two native shapes, absorbed here
------------------------------------
The metastore catalog returns every dataset in one JSON list (no
paging). The datastore query endpoint returns::

    {"count": N, "results": [...], "schema": {...}, "query": {...}}

and pages by ``limit``/``offset`` with a hard per-request cap of
**500 rows** (``limit=501`` answers HTTP 400 — verified live). We always
request ``rowIds=true`` so every row carries DKAN's ``record_number``,
which the generic-rows normalizer uses as a stable row id.

Politeness cap: one ``fetch``/``refresh`` call pulls at most
``max_pages`` pages (default :data:`DEFAULT_MAX_PAGES` = 5, i.e. ≤2,500
rows) so an accidental full pull of the 2.2M-row Rate PUF can't hammer
the API. Pass a larger ``max_pages`` deliberately to go deeper; the
returned ``next_offset``/``exhausted`` fields let callers resume where
a capped call stopped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .endpoints import ENDPOINTS, CATALOG_PATH, EndpointSpec, datastore_path, get_endpoint
from .normalize import generic_rows, normalize
from .tables import HealthcareGovStore
from .transport import HealthcareGovTransport, Opener

PAGE_LIMIT = 500          # DKAN hard maximum rows per request (verified live)
DEFAULT_MAX_PAGES = 5     # polite per-call cap; override deliberately


@dataclass
class FetchResult:
    """One ``fetch`` call's output (native paging already absorbed)."""

    rows: List[Dict[str, Any]]
    endpoint: str                  # endpoint key, or DKAN id for generic pulls
    pages: int = 0
    total: int = 0                 # server-side row count for the dataset
    requests: int = 0
    next_offset: int = 0           # where a capped fetch would resume
    exhausted: bool = True         # False when max_pages stopped us early
    params: Dict[str, Any] = field(default_factory=dict)


class HealthcareGovConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full paging state machine with a fake
    server.
    """

    def __init__(
        self,
        transport: Optional[HealthcareGovTransport] = None,
        *,
        page_limit: int = PAGE_LIMIT,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or HealthcareGovTransport.from_env()
        # Never exceed DKAN's hard cap — a bigger ask is a guaranteed 400.
        self.page_limit = max(1, min(page_limit, PAGE_LIMIT))
        self._sleep = sleep

    # ── discovery: sync the whole catalog ─────────────────────────────
    def endpoints(self) -> List[EndpointSpec]:
        """Enumerate the endpoint specs this connector ingests."""
        return list(ENDPOINTS.values())

    def discover(self, *, opener: Optional[Opener] = None
                 ) -> List[Dict[str, Any]]:
        """Fetch the full DKAN catalog and return *normalized* catalog rows.

        One metastore call returns every dataset (337 at build time) —
        no paging. Callers usually pass the result straight to
        ``store.upsert`` (or use :meth:`refresh` which does both).
        """
        spec = get_endpoint("catalog")
        payload = self.transport.get_json(CATALOG_PATH, opener=opener)
        items = payload if isinstance(payload, list) else []
        return normalize(spec, items).rows.get(spec.target_table, [])

    # ── fetch: absorb limit/offset paging ─────────────────────────────
    def fetch(
        self,
        key: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        start_offset: int = 0,
    ) -> FetchResult:
        """Fetch raw rows for a registered endpoint, absorbing paging.

        ``params`` are equality filters on real dataset columns (e.g.
        ``{"statecode": "TX"}``); they compile to DKAN's bracketed
        ``conditions[i][...]`` query params. Already-bracketed keys pass
        through untouched for advanced use.
        """
        spec = get_endpoint(key)
        if spec.kind == "catalog":
            payload = self.transport.get_json(CATALOG_PATH, opener=opener)
            items = payload if isinstance(payload, list) else []
            return FetchResult(rows=items, endpoint=spec.key, pages=1,
                               total=len(items), requests=1,
                               next_offset=len(items), exhausted=True)
        if spec.kind == "generic":
            raise ValueError(
                "fetch('fetched_rows') is a placeholder — pull an arbitrary "
                "catalog dataset with fetch_dataset(<DKAN identifier>)")
        return self._fetch_datastore(
            datastore_path(spec.identifier), spec.key, params,
            opener=opener, max_pages=max_pages, page_size=page_size,
            start_offset=start_offset)

    def fetch_dataset(
        self,
        identifier: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        start_offset: int = 0,
    ) -> FetchResult:
        """Pull ANY catalog dataset's datastore rows by DKAN identifier.

        This is the on-demand generic path: rows land in
        ``healthcare_gov_rows`` (via :meth:`refresh_dataset`) so every
        one of the catalog's datasets is reachable without a bespoke
        table. Datasets whose distribution was never imported into the
        datastore (ZIP-only files) raise a clear transport error.
        """
        ident = str(identifier).strip()
        if not ident:
            raise ValueError("fetch_dataset requires a DKAN dataset identifier")
        return self._fetch_datastore(
            datastore_path(ident), ident, params, opener=opener,
            max_pages=max_pages, page_size=page_size,
            start_offset=start_offset)

    def _fetch_datastore(
        self,
        path: str,
        endpoint_label: str,
        params: Optional[Dict[str, Any]],
        *,
        opener: Optional[Opener],
        max_pages: Optional[int],
        page_size: Optional[int],
        start_offset: int,
    ) -> FetchResult:
        cap = DEFAULT_MAX_PAGES if max_pages is None else max(1, int(max_pages))
        limit = max(1, min(int(page_size or self.page_limit), PAGE_LIMIT))
        conditions = _compile_conditions(params)
        rows: List[Dict[str, Any]] = []
        offset = max(0, int(start_offset))
        pages = 0
        total = 0
        requests = 0
        exhausted = False
        while pages < cap:
            req: Dict[str, Any] = dict(conditions)
            req["limit"] = limit
            req["offset"] = offset
            req["rowIds"] = "true"
            payload = self.transport.get_json(path, req, opener=opener)
            result = payload if isinstance(payload, dict) else {}
            page = result.get("results") or []
            if not isinstance(page, list):
                page = []
            total = int(result.get("count") or 0)
            rows.extend(r for r in page if isinstance(r, dict))
            offset += len(page)
            pages += 1
            requests += 1
            if len(page) < limit:      # short page → dataset drained
                exhausted = True
                break
        else:
            # cap hit; a full page may still mean "exactly done" — treat
            # offset >= total as drained so callers don't loop forever.
            exhausted = offset >= total > 0
        return FetchResult(rows=rows, endpoint=endpoint_label, pages=pages,
                           total=total, requests=requests, next_offset=offset,
                           exhausted=exhausted, params=dict(params or {}))

    # ── refresh: fetch + normalize + upsert ────────────────────────────
    def refresh(
        self,
        store: HealthcareGovStore,
        key: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        start_offset: int = 0,
    ) -> Dict[str, Any]:
        """One ingest step for a registered endpoint; returns counts.

        ``refresh(store, "catalog")`` syncs the whole catalog table;
        curated keys pull up to ``max_pages`` pages into their canonical
        table. Idempotent by construction (natural-key upserts).
        """
        spec = get_endpoint(key)
        step = self.fetch(key, params, opener=opener, max_pages=max_pages,
                          page_size=page_size, start_offset=start_offset)
        res = normalize(spec, step.rows)
        upserted = 0
        for table, table_rows in res.rows.items():
            upserted += store.upsert(table, table_rows)
        return {
            "dataset_id": spec.dataset_id,
            "endpoint": spec.key,
            "table": spec.target_table,
            "rows_fetched": len(step.rows),
            "rows_upserted": upserted,
            "pages": step.pages,
            "requests": step.requests,
            "server_total": step.total,
            "next_offset": step.next_offset,
            "exhausted": step.exhausted,
            "unmapped_fields": dict(res.unmapped),
        }

    def refresh_dataset(
        self,
        store: HealthcareGovStore,
        identifier: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: Optional[int] = None,
        page_size: Optional[int] = None,
        start_offset: int = 0,
    ) -> Dict[str, Any]:
        """On-demand ingest of ANY catalog dataset into the generic table."""
        step = self.fetch_dataset(identifier, params, opener=opener,
                                  max_pages=max_pages, page_size=page_size,
                                  start_offset=start_offset)
        # Sign the keys with the filter slice so refreshes of one dataset
        # under different conditions coexist (same contract as the other
        # DKAN connectors' generic rows).
        rows = generic_rows(step.endpoint, step.rows, start_idx=start_offset,
                            slice_params=params)
        upserted = store.upsert("healthcare_gov_rows", rows)
        return {
            "dataset_id": "healthcare_gov_fetched_rows",
            "dataset_key": step.endpoint,
            "table": "healthcare_gov_rows",
            "rows_fetched": len(step.rows),
            "rows_upserted": upserted,
            "pages": step.pages,
            "requests": step.requests,
            "server_total": step.total,
            "next_offset": step.next_offset,
            "exhausted": step.exhausted,
        }


def _compile_conditions(params: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """``{"statecode": "TX"}`` → DKAN ``conditions[0][property]=...`` params.

    Equality-only on purpose: richer operators belong to the local
    ``/v1/query`` engine after ingest. Keys that already look like
    bracketed DKAN params (or paging keys) pass through untouched so
    power users aren't blocked.
    """
    out: Dict[str, str] = {}
    i = 0
    for k, v in (params or {}).items():
        key = str(k)
        if "[" in key or key in ("limit", "offset", "rowIds", "keys"):
            out[key] = str(v)
            continue
        out[f"conditions[{i}][property]"] = key
        out[f"conditions[{i}][value]"] = str(v)
        i += 1
    return out
