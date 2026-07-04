"""The NPI Registry connector: ``discover()`` + ``fetch()``.

NPPES is a single search endpoint, so ingest is modelled as **seeded
searches** (see :mod:`connectors.npi_registry.endpoints`). ``fetch``
runs one seed and pages it by ``skip`` — callers never see NPPES's
native ``limit``/``skip`` or its hard result ceiling.

NPPES paging limits (verify live at npiregistry.cms.hhs.gov/api-page):
  * ``limit`` maxes at 200 records per request,
  * ``skip`` maxes at 1000,
  * so a single query yields at most **1,200** results (limit 200 ×
    skip up to 1000). Past that the API simply won't return more — a
    seed that would exceed 1,200 must be narrowed (finer state/taxonomy
    slices). ``fetch`` drains a seed up to that ceiling, pages by
    ``skip`` step 200, and stops on the first short page (seed
    exhausted) or the cap (``truncated=True``).

``fetch`` is one *step* of a resumable crawl: it returns the rows for a
seed plus a ``next_cursor`` describing where to resume, and ``None``
when the seed is exhausted (or capped). Cursors are JSON-serialisable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .endpoints import EndpointSpec
from .transport import NppesTransport, Opener

# NPPES hard limits (verify live before bulk runs).
PAGE_LIMIT = 200               # max records per request
SKIP_CAP = 1000                # max skip the API accepts
MAX_RESULTS = 1200             # limit 200 × skip 1000 → hard per-query ceiling
MAX_PAGES_PER_STEP = 6         # 6 × 200 = 1200 drains a full seed in one step


@dataclass
class FetchResult:
    """One ``fetch`` step's output."""

    rows: List[Dict[str, Any]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    seed: Optional[Dict[str, Any]] = None
    total: int = 0                 # NPPES result_count for the seed
    truncated: bool = False        # hit the 1,200 cap with more available
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class NppesConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full seed pager with a fake server.
    """

    def __init__(
        self,
        transport: Optional[NppesTransport] = None,
        *,
        page_limit: int = PAGE_LIMIT,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or NppesTransport.from_env()
        self.page_limit = min(page_limit, PAGE_LIMIT)
        self._sleep = sleep

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the seeded-search datasets this connector ingests."""
        from .endpoints import ENDPOINTS
        return list(ENDPOINTS.values())

    def seeds(self, spec: EndpointSpec) -> List[Dict[str, Any]]:
        """The default seed queries for a spec (as plain dicts)."""
        return [dict(s) for s in spec.seeds]

    # ── the seed pager ────────────────────────────────────────────────
    def fetch(
        self,
        spec: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Advance one step for a single seed.

        ``params`` is the seed query dict; when omitted the spec's first
        default seed is used. Returns the rows drained this step plus a
        ``next_cursor`` (``None`` when the seed is exhausted or capped).
        """
        seed = dict(params if params is not None
                    else (spec.seeds[0] if spec.seeds else {}))
        cursor = dict(cursor or {"skip": 0})
        skip = int(cursor.get("skip", 0))
        start_requests = self.transport.requests_made

        rows: List[Dict[str, Any]] = []
        total = 0
        pages = 0
        truncated = False
        next_cursor: Optional[Dict[str, Any]] = None

        while True:
            payload = self.transport.get_json(
                spec.path, self._page_params(seed, skip), opener=opener)
            results = payload.get("results") or []
            if not isinstance(results, list):
                results = []
            total = int(payload.get("result_count", len(results)) or 0)
            rows.extend(results)
            got = len(results)
            skip += got
            pages += 1

            # Short page → this seed is fully drained.
            if got < self.page_limit:
                next_cursor = None
                break
            # Reached the API's hard ceiling with (likely) more available.
            if skip >= MAX_RESULTS or skip > SKIP_CAP:
                next_cursor = None
                truncated = True
                break
            # Bounded work per step; resume from this skip next call.
            if pages >= MAX_PAGES_PER_STEP:
                next_cursor = {"skip": skip}
                break

        return FetchResult(
            rows=rows,
            next_cursor=next_cursor,
            endpoint=spec.key,
            seed=seed,
            total=total,
            truncated=truncated,
            requests=self.transport.requests_made - start_requests,
        )

    def fetch_seed(
        self,
        spec: EndpointSpec,
        seed: Dict[str, Any],
        *,
        opener: Optional[Opener] = None,
    ) -> List[Dict[str, Any]]:
        """Convenience: fully drain one seed across steps into a row list."""
        rows: List[Dict[str, Any]] = []
        cursor: Optional[Dict[str, Any]] = None
        for _ in range(MAX_PAGES_PER_STEP + 2):
            res = self.fetch(spec, seed, cursor, opener=opener)
            rows.extend(res.rows)
            if res.next_cursor is None:
                break
            cursor = res.next_cursor
        return rows

    def _page_params(self, seed: Dict[str, Any], skip: int) -> Dict[str, Any]:
        params: Dict[str, Any] = dict(seed)
        params["limit"] = self.page_limit
        params["skip"] = skip
        return params
