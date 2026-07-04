"""The ICD-10 connector: ``discover()`` + ``fetch()``.

Pagination, rate-limit handling and retries all live *inside* the
connector — callers (the CLI, the registry, the lookup handlers) never
see the NLM API's native ``offset``/``maxList``.

How a full ingest is paged
--------------------------
The NLM Clinical Tables API caps ``maxList`` (page size) at 500 and
refuses an ``offset`` past ~7500, so you cannot linearly page the whole
code set from a single query. Instead the connector iterates a set of
**code-prefix seeds** (``q=code:A*`` … ``code:Z*`` for CM, ``code:0*`` …
for PCS) declared on the :class:`EndpointSpec`; each seed's result window
is small enough to page by ``offset`` under the ceiling.

``fetch`` is a single *step* of this state machine: it drains one seed
(or resumes a seed mid-offset), returns those rows plus a ``next_cursor``
describing where to resume, and ``None`` when the endpoint is exhausted.
Every cursor is JSON-serialisable so a run can persist it and resume
exactly where it stopped. ``fetch`` also accepts a caller-supplied
``terms``/``q`` in ``params`` — when given, the seed list collapses to
that single query.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .endpoints import ENDPOINTS, EndpointSpec
from .transport import NlmTransport, Opener

# NLM Clinical Tables limits (verify live before bulk runs).
PAGE_LIMIT = 500               # max records per request (maxList ceiling)
OFFSET_CAP = 7500              # deep-paging ceiling; offset beyond this fails
MAX_PAGES_PER_STEP = 30        # bound the work (and rows) one fetch() returns


@dataclass
class FetchResult:
    """One ``fetch`` step's output."""

    rows: List[Dict[str, Any]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    seed: Optional[str] = None                 # the code-prefix seed drained
    total_in_seed: int = 0
    truncated: bool = False                    # offset ceiling hit, rows dropped
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class Icd10Connector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call (or via the transport) so tests drive the full state
    machine with a fake server.
    """

    def __init__(
        self,
        transport: Optional[NlmTransport] = None,
        *,
        page_limit: int = PAGE_LIMIT,
        sleep: Any = None,
    ) -> None:
        self.transport = transport or NlmTransport.from_env()
        self.page_limit = page_limit
        self._sleep = sleep or (lambda _s: None)

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the endpoints this connector ingests."""
        return list(ENDPOINTS.values())

    # ── cheap total ───────────────────────────────────────────────────
    def total_count(self, spec: EndpointSpec, *, terms: str = "", q: str = "",
                    opener: Optional[Opener] = None) -> int:
        """Total matches for a query (element ``[0]`` of the array)."""
        params: Dict[str, Any] = {"terms": terms or "", "sf": spec.sf,
                                  "df": ",".join(spec.df), "maxList": 1, "offset": 0}
        if q:
            params["q"] = q
        arr = self.transport.get_json(spec.path, params, opener=opener)
        total, _codes, _disp = _parse_array(arr)
        return total

    # ── the fetch state machine ───────────────────────────────────────
    def fetch(
        self,
        endpoint: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Advance one step. Returns rows for the current seed slice + a
        ``next_cursor`` (``None`` when the endpoint is exhausted)."""
        params = dict(params or {})
        cursor = self._init_cursor(cursor)
        seeds = self._seeds(endpoint, params)
        idx = int(cursor.get("idx", 0))
        offset = int(cursor.get("offset", 0))
        if idx >= len(seeds):
            return FetchResult([], None, endpoint.key, None, 0)

        seed = seeds[idx]
        terms, q = self._terms_q(params, seed)
        rows, total, new_offset = self._drain(endpoint, terms, q, offset, opener)

        hit_ceiling = new_offset >= OFFSET_CAP and new_offset < total
        exhausted = new_offset >= total or new_offset >= OFFSET_CAP or not rows
        if exhausted:
            nxt_idx, nxt_off = idx + 1, 0
        else:
            nxt_idx, nxt_off = idx, new_offset
        nxt: Optional[Dict[str, Any]]
        if nxt_idx >= len(seeds):
            nxt = None
        else:
            nxt = {"idx": nxt_idx, "offset": nxt_off}
        return FetchResult(rows, nxt, endpoint.key, seed=seed,
                           total_in_seed=total, truncated=hit_ceiling)

    # ── cursor + seed helpers ─────────────────────────────────────────
    def _init_cursor(self, cursor: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return dict(cursor) if cursor else {"idx": 0, "offset": 0}

    def _seeds(self, spec: EndpointSpec, params: Dict[str, Any]) -> List[Optional[str]]:
        # A caller-supplied query collapses the seed sweep to one pass.
        if params.get("q") or params.get("terms"):
            return [None]
        return list(spec.seeds)

    def _terms_q(self, params: Dict[str, Any], seed: Optional[str]
                 ) -> Tuple[str, str]:
        if seed is None:
            return params.get("terms", "") or "", params.get("q", "") or ""
        return "", f"code:{seed}*"

    # ── inner pager ───────────────────────────────────────────────────
    def _drain(self, spec: EndpointSpec, terms: str, q: str, start_offset: int,
               opener: Optional[Opener]
               ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Page ``offset`` until the query is exhausted or a bound is hit.

        Returns ``(rows, total, next_offset)``. Each raw row is a dict of
        the requested ``df`` fields, built by zipping the ``df`` names
        against the returned columns — a shorter row (variable df width,
        e.g. a missing ``long_name``) simply yields fewer keys.
        """
        rows: List[Dict[str, Any]] = []
        offset = start_offset
        total = 0
        pages = 0
        while True:
            params: Dict[str, Any] = {
                "terms": terms or "", "sf": spec.sf, "df": ",".join(spec.df),
                "maxList": self.page_limit, "offset": offset,
            }
            if q:
                params["q"] = q
            arr = self.transport.get_json(spec.path, params, opener=opener)
            total, _codes, disp = _parse_array(arr)
            for r in disp:
                rec = dict(zip(spec.df, r))   # variable width absorbed by zip
                rec["code_type"] = spec.code_type
                rows.append(rec)
            got = len(disp)
            offset += got
            pages += 1
            if got < self.page_limit:
                break
            if offset >= total or offset >= OFFSET_CAP:
                break
            if pages >= MAX_PAGES_PER_STEP:
                break
        return rows, total, offset


def _parse_array(arr: Any) -> Tuple[int, List[Any], List[Any]]:
    """Defensively unpack the 4-element NLM array ``[total, codes, hash, rows]``."""
    if not isinstance(arr, list):
        return 0, [], []
    total = 0
    if len(arr) > 0:
        try:
            total = int(arr[0])
        except (TypeError, ValueError):
            total = 0
    codes = arr[1] if len(arr) > 1 and isinstance(arr[1], list) else []
    disp = arr[3] if len(arr) > 3 and isinstance(arr[3], list) else []
    return total, codes, disp
