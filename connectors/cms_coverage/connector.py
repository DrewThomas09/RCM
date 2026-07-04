"""The CMS Coverage connector: ``discover()`` + ``fetch()``.

Pagination, rate-limit handling and retries all live *inside* the
connector — callers (the pipeline, the registry, the lookup handlers)
never see the API's native ``page_token``/``limit``.

Two pagination shapes, absorbed here
------------------------------------
National and local coverage list endpoints return an envelope::

    {"result": {"count": N, "total": M,
                "next_page_token": "eyJvIjoyfQ==", "items": [...]}}

and are paged by echoing ``next_page_token`` back as ``page_token`` until
it is absent. The contractor dimension returns everything in one call::

    {"count": 120, "items": [...]}

``fetch`` is a single *step*: it returns the current page's rows plus a
``next_cursor`` describing where to resume, and ``None`` when the
endpoint is exhausted. Every cursor is JSON-serialisable so a hard kill
resumes exactly where it stopped. :meth:`fetch_all` drives the loop to
completion for callers that want every row in one go.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .endpoints import ENDPOINTS, EndpointSpec
from .transport import CmsCoverageTransport, Opener

# Conservative page size (verify live at the CMS MCD developer portal).
PAGE_LIMIT = 100
MAX_PAGES_PER_STEP = 1          # one HTTP page per fetch() step
MAX_PAGES_TOTAL = 10_000        # hard bound on fetch_all's loop


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


class CmsCoverageConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full paging state machine with a fake
    server.
    """

    def __init__(
        self,
        transport: Optional[CmsCoverageTransport] = None,
        *,
        page_limit: int = PAGE_LIMIT,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or CmsCoverageTransport.from_env()
        self.page_limit = page_limit
        self._sleep = sleep

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the endpoints this connector ingests."""
        return list(ENDPOINTS.values())

    # ── the fetch state machine ───────────────────────────────────────
    def fetch(
        self,
        endpoint: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Advance one step. Returns rows for the current page + a
        ``next_cursor`` (``None`` when the endpoint is exhausted)."""
        params = dict(params or {})
        if not endpoint.paginated:
            return self._fetch_single(endpoint, params, opener)
        return self._fetch_page(endpoint, params, cursor, opener)

    def fetch_all(
        self,
        endpoint: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> List[Dict[str, Any]]:
        """Drive :meth:`fetch` to exhaustion, returning every row.

        Follows ``next_page_token`` for paginated endpoints and issues a
        single call for the contractor dimension.
        """
        rows: List[Dict[str, Any]] = []
        cursor: Optional[Dict[str, Any]] = None
        for _ in range(MAX_PAGES_TOTAL):
            step = self.fetch(endpoint, params, cursor, opener=opener)
            rows.extend(step.rows)
            if step.next_cursor is None:
                break
            cursor = step.next_cursor
        return rows

    # ── paged national/local documents ────────────────────────────────
    def _fetch_page(self, spec: EndpointSpec, params: Dict[str, Any],
                    cursor: Optional[Dict[str, Any]], opener: Optional[Opener]
                    ) -> FetchResult:
        req: Dict[str, Any] = dict(spec.default_params)
        req.update(params)
        req.setdefault("limit", self.page_limit)
        token = (cursor or {}).get("page_token")
        if token:
            req["page_token"] = token
        payload = self.transport.get_json(spec.path, req, opener=opener)
        result = payload.get("result")
        if not isinstance(result, dict):
            result = {}
        items = result.get("items") or []
        if not isinstance(items, list):
            items = []
        next_token = result.get("next_page_token")
        next_cursor = {"page_token": next_token} if next_token else None
        total = int(result.get("total") or 0)
        return FetchResult(rows=items, next_cursor=next_cursor,
                           endpoint=spec.key, total=total, requests=1)

    # ── single-shot contractor dimension ──────────────────────────────
    def _fetch_single(self, spec: EndpointSpec, params: Dict[str, Any],
                      opener: Optional[Opener]) -> FetchResult:
        req: Dict[str, Any] = dict(spec.default_params)
        req.update(params)
        payload = self.transport.get_json(spec.path, req, opener=opener)
        # Contractors use a bare {"count", "items"} envelope; tolerate a
        # nested {"result": {...}} too in case the live shape differs.
        items = payload.get("items")
        if items is None:
            result = payload.get("result")
            items = result.get("items") if isinstance(result, dict) else None
        if not isinstance(items, list):
            items = []
        total = int(payload.get("count") or len(items))
        return FetchResult(rows=items, next_cursor=None, endpoint=spec.key,
                           total=total, requests=1)
