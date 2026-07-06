"""The NIH RePORTER connector: ``discover()`` + ``fetch()`` + ``refresh()``.

Pagination, rate-limit handling and retries all live *inside* the
connector — callers (the pipeline, the registry, the lookup handlers)
never see the API's native ``offset``/``limit`` POST-body paging.

The paging shape, absorbed here
-------------------------------
Every RePORTER search POST returns an envelope::

    {"meta": {"total": N, "offset": O, "limit": L, ...},
     "results": [...]}

and is paged by re-POSTing with ``offset += len(results)`` until a short
page or the API's hard ceiling. Two live-verified hard limits (see
:mod:`connectors.nih_reporter.endpoints`): ``limit`` ≤ 500 and ``offset``
≤ 14,999 — so one criteria set can surface at most ~15.5k rows. When a
result set is bigger than the reachable window, ``fetch`` stops and marks
the step ``truncated`` instead of erroring; callers narrow the criteria
(per fiscal year / state / IC) to go deeper.

``fetch`` is a single *step*: one HTTP page. It returns the page's rows
plus a ``next_cursor`` describing where to resume, and ``None`` when the
search is exhausted (or capped). Every cursor is JSON-serialisable so a
hard kill resumes exactly where it stopped. :meth:`fetch_all` drives the
loop for callers that want many rows in one go — bounded by ``max_pages``
(default **5** pages = up to 2,500 rows) so an accidental
empty-criteria pull (RePORTER matches *everything* on empty criteria)
never hammers the API. :meth:`refresh` is the fetch → normalize → upsert
convenience the CLI drives.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from .endpoints import ENDPOINTS, OFFSET_CAP, PAGE_LIMIT_MAX, EndpointSpec, get_endpoint
from .transport import NihReporterTransport, Opener

# Polite defaults (the API's own max page size keeps request counts low).
PAGE_LIMIT = PAGE_LIMIT_MAX     # 500 — fewer requests is the polite choice here
MAX_PAGES_DEFAULT = 5           # fetch_all/refresh cap: 5 × 500 = 2,500 rows
MAX_PAGES_TOTAL = 30            # absolute bound: (14,999 + 500) / 500 pages


@dataclass
class FetchResult:
    """One ``fetch`` step's output."""

    rows: List[Dict[str, Any]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    total: int = 0                 # RePORTER meta.total for the criteria
    truncated: bool = False        # hit the offset cap with more available
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class NihReporterConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full paging state machine with a fake
    server.
    """

    def __init__(
        self,
        transport: Optional[NihReporterTransport] = None,
        *,
        page_limit: int = PAGE_LIMIT,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or NihReporterTransport.from_env()
        # Never exceed the API's hard 500/request — a bigger value is a 400.
        self.page_limit = max(1, min(page_limit, PAGE_LIMIT_MAX))
        self._sleep = sleep

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the endpoints this connector ingests."""
        return list(ENDPOINTS.values())

    # ── the fetch state machine ───────────────────────────────────────
    def fetch(
        self,
        endpoint: EndpointSpec,
        criteria: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Advance one step (= one HTTP page).

        ``criteria`` is the RePORTER criteria object (see the
        ``project_criteria`` / ``publication_criteria`` helpers). Returns
        the page's rows plus a ``next_cursor`` — ``None`` when the search
        is exhausted or the API's offset ceiling makes deeper paging
        impossible (then ``truncated=True``).
        """
        merged = dict(endpoint.default_criteria)
        merged.update(criteria or {})
        offset = int((cursor or {}).get("offset", 0))
        body = {"criteria": merged, "offset": offset, "limit": self.page_limit}
        payload = self.transport.post_json(endpoint.path, body, opener=opener)

        meta = payload.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        results = payload.get("results") or []
        if not isinstance(results, list):
            results = []
        total = int(meta.get("total") or 0)

        next_offset = offset + len(results)
        truncated = False
        next_cursor: Optional[Dict[str, Any]] = None
        if len(results) == self.page_limit and next_offset < total:
            if next_offset <= OFFSET_CAP:
                next_cursor = {"offset": next_offset}
            else:
                # More rows exist but the API refuses offsets past 14,999.
                truncated = True
        return FetchResult(rows=results, next_cursor=next_cursor,
                           endpoint=endpoint.key, total=total,
                           truncated=truncated, requests=1)

    def fetch_all(
        self,
        endpoint: EndpointSpec,
        criteria: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: int = MAX_PAGES_DEFAULT,
    ) -> List[Dict[str, Any]]:
        """Drive :meth:`fetch` up to ``max_pages`` pages, returning the rows.

        ``max_pages`` is a deliberate hard cap (default 5 → ≤ 2,500 rows):
        empty criteria match every RePORTER record, so an unbounded drain
        must be an explicit caller decision, never an accident.
        """
        rows: List[Dict[str, Any]] = []
        cursor: Optional[Dict[str, Any]] = None
        for _ in range(max(1, min(max_pages, MAX_PAGES_TOTAL))):
            step = self.fetch(endpoint, criteria, cursor, opener=opener)
            rows.extend(step.rows)
            if step.next_cursor is None:
                break
            cursor = step.next_cursor
        return rows

    # ── fetch → normalize → upsert convenience ────────────────────────
    def refresh(
        self,
        store: Any,
        dataset_key: str,
        criteria: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        max_pages: int = MAX_PAGES_DEFAULT,
    ) -> Dict[str, Any]:
        """Fetch a dataset slice and upsert it into ``store``; return counts.

        ``store`` is a :class:`~connectors.nih_reporter.tables.NihReporterStore`
        (typed ``Any`` to keep this module import-light). The idempotent
        upsert keys on the native ids, so re-running the same criteria
        refreshes in place rather than double-counting.
        """
        from .normalize import normalize  # local import: keep fetch path light

        spec = get_endpoint(dataset_key)
        rows: List[Dict[str, Any]] = []
        cursor: Optional[Dict[str, Any]] = None
        pages = 0
        requests = 0
        total = 0
        truncated = False
        for _ in range(max(1, min(max_pages, MAX_PAGES_TOTAL))):
            step = self.fetch(spec, criteria, cursor, opener=opener)
            rows.extend(step.rows)
            pages += 1
            requests += step.requests
            total = step.total
            truncated = truncated or step.truncated
            if step.next_cursor is None:
                break
            cursor = step.next_cursor
        res = normalize(spec, rows)
        upserted = {table: store.upsert(table, trows)
                    for table, trows in res.rows.items()}
        return {
            "dataset_id": spec.dataset_id,
            "endpoint": spec.key,
            "fetched": len(rows),
            "upserted": upserted,
            "total_matching": total,
            "pages": pages,
            "requests": requests,
            "truncated": truncated,
            "unmapped_fields": res.unmapped,
        }

    # ── criteria builders (live-verified shapes) ──────────────────────
    @staticmethod
    def project_criteria(
        *,
        fiscal_years: Union[None, int, Sequence[int]] = None,
        org_states: Union[None, str, Sequence[str]] = None,
        org_names: Union[None, str, Sequence[str]] = None,
        pi_names: Union[None, str, Sequence[Any]] = None,
        activity_codes: Union[None, str, Sequence[str]] = None,
        advanced_text_search: Union[None, str, Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a ``/v2/projects/search`` criteria object.

        Shapes verified live: ``fiscal_years`` ints, ``org_states``
        two-letter codes, ``org_names`` substring-matched by the API,
        ``pi_names`` a list of ``{"any_name": ...}`` objects (bare strings
        are wrapped), ``activity_codes`` like ``R01``, and
        ``advanced_text_search`` ``{operator, search_field, search_text}``
        (a bare string searches title+terms+abstract). ``extra`` merges any
        further native criteria verbatim.
        """
        crit: Dict[str, Any] = {}
        if fiscal_years is not None:
            crit["fiscal_years"] = [int(y) for y in _as_seq(fiscal_years)]
        if org_states is not None:
            crit["org_states"] = [str(s).upper() for s in _as_seq(org_states)]
        if org_names is not None:
            crit["org_names"] = [str(n) for n in _as_seq(org_names)]
        if pi_names is not None:
            crit["pi_names"] = [
                p if isinstance(p, dict) else {"any_name": str(p)}
                for p in _as_seq(pi_names)
            ]
        if activity_codes is not None:
            crit["activity_codes"] = [str(c).upper() for c in _as_seq(activity_codes)]
        if advanced_text_search is not None:
            if isinstance(advanced_text_search, dict):
                crit["advanced_text_search"] = dict(advanced_text_search)
            else:
                crit["advanced_text_search"] = {
                    "operator": "and",
                    "search_field": "projecttitle,terms,abstracttext",
                    "search_text": str(advanced_text_search),
                }
        if extra:
            crit.update(extra)
        return crit

    @staticmethod
    def publication_criteria(
        *,
        core_project_nums: Union[None, str, Sequence[str]] = None,
        appl_ids: Union[None, int, Sequence[int]] = None,
        pmids: Union[None, int, Sequence[int]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a ``/v2/publications/search`` criteria object.

        Shapes verified live: ``core_project_nums`` strings (e.g.
        ``R37GM070977``), ``appl_ids`` / ``pmids`` integers.
        """
        crit: Dict[str, Any] = {}
        if core_project_nums is not None:
            crit["core_project_nums"] = [str(c) for c in _as_seq(core_project_nums)]
        if appl_ids is not None:
            crit["appl_ids"] = [int(a) for a in _as_seq(appl_ids)]
        if pmids is not None:
            crit["pmids"] = [int(p) for p in _as_seq(pmids)]
        if extra:
            crit.update(extra)
        return crit


def _as_seq(value: Any) -> List[Any]:
    """Wrap a bare scalar into a list; pass sequences through."""
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]
