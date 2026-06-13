"""The openFDA connector: ``discover()`` + ``fetch()``.

Pagination, rate-limit handling, retries and the deep-paging workaround
all live *inside* the connector — callers (the pipeline, the registry,
the lookup handlers) never see openFDA's native ``skip``/``limit``.

The deep-paging problem and how we absorb it
--------------------------------------------
openFDA caps ``limit`` at 1000 and refuses ``skip`` past ~25,000, so you
cannot linearly page a large endpoint. For endpoints with a usable date
field we chunk the full history into date windows each small enough to
hold under the skip ceiling, page ``skip`` *inside* a window, then
advance the window. Windows are **adaptive**: if a window's total
exceeds the cap we halve it and retry; after a comfortably-drained
window we grow back toward the default. Endpoints with no date
(``dim`` references) page by ``skip`` and, once the cap is reached, fall
back to partitioning by a categorical field discovered via ``count=``.

``fetch`` is a single *step* of this state machine: it drains one window
(or one skip batch / one partition slice), returns those rows plus a
``next_cursor`` describing where to resume, and ``None`` when the
endpoint is exhausted. Every cursor is JSON-serialisable so STATE.md can
persist it and a hard kill resumes exactly where it stopped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from .endpoints import EndpointSpec
from .flatten import dig
from .transport import OpenFdaTransport, Opener

# openFDA hard limits (verify live at open.fda.gov/apis before bulk runs).
PAGE_LIMIT = 1000              # max records per request
SKIP_CAP = 25000              # deep-paging ceiling; skip beyond this 400s
# Stay safely under the ceiling so the last page never trips it.
SAFE_SKIP_CAP = 25000 - PAGE_LIMIT
DEFAULT_WINDOW_DAYS = 30
MAX_PAGES_PER_STEP = 30        # bound the work (and rows) one fetch() returns


@dataclass
class FetchResult:
    """One ``fetch`` step's output."""

    rows: List[Dict[str, Any]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    window: Optional[Tuple[str, str]] = None   # (start, end) when windowed
    total_in_window: int = 0
    truncated: bool = False                    # cap hit, rows dropped — logged
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class OpenFdaConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call (or via the transport) so tests drive the full state
    machine with a fake server.
    """

    def __init__(
        self,
        transport: Optional[OpenFdaTransport] = None,
        *,
        page_limit: int = PAGE_LIMIT,
        backfill_start: str = "20040101",
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or OpenFdaTransport.from_env()
        self.page_limit = page_limit
        self.backfill_start = backfill_start
        self._sleep = sleep

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the endpoints this connector ingests.

        Imported lazily so ``discover`` reflects the registry of specs
        without a network round-trip.
        """
        from .endpoints import ENDPOINTS
        return list(ENDPOINTS.values())

    # ── cheap aggregates ──────────────────────────────────────────────
    def count_aggregate(
        self, spec: EndpointSpec, field_name: Optional[str] = None, *,
        search: str = "", opener: Optional[Opener] = None,
    ) -> List[Dict[str, Any]]:
        """Run a ``count=`` market-map aggregate (no full-record pull).

        Returns openFDA's ``[{term, count}, ...]``. Used for cheap
        market maps and for DQ reconciliation against ingested rows.
        """
        cf = field_name or spec.count_field
        if not cf:
            return []
        params: Dict[str, Any] = {"count": cf, "limit": self.page_limit}
        if search:
            params["search"] = search
        payload = self.transport.get_json(spec.path, params, opener=opener)
        res = payload.get("results")
        return res if isinstance(res, list) else []

    def total_count(self, spec: EndpointSpec, *, search: str = "",
                    opener: Optional[Opener] = None) -> int:
        """Total matching records for a search (``meta.results.total``)."""
        params: Dict[str, Any] = {"limit": 1}
        if search:
            params["search"] = search
        payload = self.transport.get_json(spec.path, params, opener=opener)
        return int(dig(payload, "meta.results.total", 0) or 0)

    # ── the fetch state machine ───────────────────────────────────────
    def fetch(
        self,
        endpoint: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Advance one step. Returns rows for the current slice + a
        ``next_cursor`` (``None`` when the endpoint is exhausted)."""
        params = dict(params or {})
        cursor = self._init_cursor(endpoint, cursor)
        mode = cursor.get("mode")
        if mode == "window":
            return self._fetch_window(endpoint, params, cursor, opener)
        if mode == "partition":
            return self._fetch_partition(endpoint, params, cursor, opener)
        return self._fetch_skip(endpoint, params, cursor, opener)

    # ── cursor seeding ────────────────────────────────────────────────
    def _init_cursor(self, spec: EndpointSpec, cursor: Optional[Dict[str, Any]]
                     ) -> Dict[str, Any]:
        if cursor:
            return dict(cursor)
        if spec.date_field:
            return {
                "mode": "window",
                "cursor_start": _coerce_date(self.backfill_start, spec.date_format),
                "overall_end": _today_str(spec.date_format),
                "window_days": DEFAULT_WINDOW_DAYS,
            }
        return {"mode": "skip", "skip": 0}

    # ── windowed mode ─────────────────────────────────────────────────
    def _fetch_window(self, spec: EndpointSpec, params: Dict[str, Any],
                      cursor: Dict[str, Any], opener: Optional[Opener]
                      ) -> FetchResult:
        fmt = spec.date_format
        start = cursor["cursor_start"]
        overall_end = cursor.get("overall_end") or _today_str(fmt)
        window_days = int(cursor.get("window_days") or DEFAULT_WINDOW_DAYS)
        start_d = _parse(start, fmt)
        end_d = min(_parse(overall_end, fmt), start_d + timedelta(days=window_days - 1))
        end = _fmt(end_d, fmt)

        base = params.get("search", "")
        search = _and(base, _date_range(spec.date_field, start, end))
        total = self.total_count(spec, search=search, opener=opener)

        # Window too big and shrinkable → halve and retry the same start.
        if total > SAFE_SKIP_CAP and end_d > start_d:
            new_days = max(1, window_days // 2)
            nxt = {**cursor, "window_days": new_days}
            return FetchResult([], nxt, spec.key, (start, end), total,
                               truncated=False)

        # Drain this window (single day still over cap → truncate + log).
        rows, _t, drained = self._drain(spec, search, opener,
                                        max_records=SAFE_SKIP_CAP)
        truncated = total > SAFE_SKIP_CAP and end_d <= start_d

        next_start_d = end_d + timedelta(days=1)
        if next_start_d > _parse(overall_end, fmt):
            nxt = None
        else:
            # Grow window back toward default after a comfortable drain.
            grow = window_days
            if total < SAFE_SKIP_CAP // 2:
                grow = min(DEFAULT_WINDOW_DAYS, max(window_days * 2, 1))
            nxt = {
                "mode": "window",
                "cursor_start": _fmt(next_start_d, fmt),
                "overall_end": overall_end,
                "window_days": grow,
            }
        return FetchResult(rows, nxt, spec.key, (start, end), total,
                           truncated=truncated)

    # ── skip mode ─────────────────────────────────────────────────────
    def _fetch_skip(self, spec: EndpointSpec, params: Dict[str, Any],
                    cursor: Dict[str, Any], opener: Optional[Opener]
                    ) -> FetchResult:
        skip = int(cursor.get("skip", 0))
        base = params.get("search", "")
        rows, total, new_skip = self._drain(
            spec, base, opener, start_skip=skip,
            max_records=skip + self.page_limit * MAX_PAGES_PER_STEP,
        )
        # Exhausted the endpoint within the cap.
        if new_skip >= total or not rows:
            return FetchResult(rows, None, spec.key, None, total)
        # Hit the skip ceiling but more remain → switch to partitioning.
        if new_skip >= SAFE_SKIP_CAP:
            if spec.partition_field:
                part_cursor = self._build_partition_cursor(
                    spec, base, opener)
                return FetchResult(rows, part_cursor, spec.key, None, total)
            # No partition strategy: accept the cap, log truncation.
            return FetchResult(rows, None, spec.key, None, total,
                               truncated=True)
        return FetchResult(rows, {"mode": "skip", "skip": new_skip},
                           spec.key, None, total)

    # ── partition mode (skip-cap fallback for non-dated endpoints) ─────
    def _build_partition_cursor(self, spec: EndpointSpec, base: str,
                                opener: Optional[Opener]) -> Dict[str, Any]:
        agg = self.count_aggregate(spec, spec.partition_field, search=base,
                                   opener=opener)
        terms = [str(r.get("term")) for r in agg if r.get("term") not in (None, "")]
        return {
            "mode": "partition",
            "field": spec.partition_field,
            "terms": terms,
            "idx": 0,
            "skip": 0,
            "base": base,
        }

    def _fetch_partition(self, spec: EndpointSpec, params: Dict[str, Any],
                         cursor: Dict[str, Any], opener: Optional[Opener]
                         ) -> FetchResult:
        terms: List[str] = cursor.get("terms", [])
        idx = int(cursor.get("idx", 0))
        skip = int(cursor.get("skip", 0))
        base = cursor.get("base", params.get("search", ""))
        field_name = cursor["field"].replace(".exact", "")
        if idx >= len(terms):
            return FetchResult([], None, spec.key, None, 0)
        term = terms[idx]
        search = _and(base, f'{field_name}.exact:"{term}"')
        rows, total, new_skip = self._drain(
            spec, search, opener, start_skip=skip,
            max_records=skip + self.page_limit * MAX_PAGES_PER_STEP)
        truncated = False
        if new_skip >= total or not rows:
            nxt_idx, nxt_skip = idx + 1, 0
        elif new_skip >= SAFE_SKIP_CAP:
            # A single partition value still exceeds the cap — rare; log + skip on.
            nxt_idx, nxt_skip, truncated = idx + 1, 0, True
        else:
            nxt_idx, nxt_skip = idx, new_skip
        if nxt_idx >= len(terms) and nxt_skip == 0:
            nxt = None
        else:
            nxt = {**cursor, "idx": nxt_idx, "skip": nxt_skip}
        return FetchResult(rows, nxt, spec.key, None, total, truncated=truncated)

    # ── inner pager ───────────────────────────────────────────────────
    def _drain(self, spec: EndpointSpec, search: str, opener: Optional[Opener],
               *, start_skip: int = 0, max_records: int = SAFE_SKIP_CAP
               ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Page ``skip`` until the search is exhausted or a bound is hit.

        Returns ``(rows, total, next_skip)``. ``total`` is openFDA's
        reported match count for ``search``; ``next_skip`` is where the
        next step resumes.
        """
        rows: List[Dict[str, Any]] = []
        skip = start_skip
        total = 0
        pages = 0
        while True:
            params: Dict[str, Any] = {"limit": self.page_limit, "skip": skip}
            if search:
                params["search"] = search
            payload = self.transport.get_json(spec.path, params, opener=opener)
            total = int(dig(payload, "meta.results.total", 0) or 0)
            results = payload.get("results") or []
            if not isinstance(results, list):
                results = []
            rows.extend(results)
            got = len(results)
            skip += got
            pages += 1
            if got < self.page_limit:
                break
            if skip >= total or skip >= max_records or skip >= SAFE_SKIP_CAP:
                break
            if pages >= MAX_PAGES_PER_STEP:
                break
        return rows, total, skip


# ── date helpers (handle YYYYMMDD and YYYY-MM-DD per spec) ─────────────
def _strptime_fmt(fmt: str) -> str:
    return "%Y-%m-%d" if "-" in fmt else "%Y%m%d"


def _parse(s: str, fmt: str) -> date:
    return datetime.strptime(s, _strptime_fmt(fmt)).date()


def _fmt(d: date, fmt: str) -> str:
    return d.strftime(_strptime_fmt(fmt))


def _today_str(fmt: str) -> str:
    return datetime.now(timezone.utc).date().strftime(_strptime_fmt(fmt))


def _coerce_date(s: str, fmt: str) -> str:
    """Reformat a start date (``YYYYMMDD`` or ``YYYY-MM-DD``) to ``fmt``.

    ``backfill_start`` is configured once as ``YYYYMMDD`` but ISO-dated
    endpoints (510k/pma/recall/udi) need ``YYYY-MM-DD`` in the range
    search, so normalize per endpoint.
    """
    raw = s.replace("-", "")
    d = datetime.strptime(raw, "%Y%m%d").date()
    return d.strftime(_strptime_fmt(fmt))


def _date_range(field_name: str, start: str, end: str) -> str:
    return f"{field_name}:[{start} TO {end}]"


def _and(a: str, b: str) -> str:
    if a and b:
        return f"({a})+AND+{b}"
    return a or b
