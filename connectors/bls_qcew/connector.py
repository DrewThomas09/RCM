"""The BLS QCEW connector: ``discover()`` + ``fetch()`` + ``refresh()``.

There is no native paging to absorb — each (year, qtr, code) slice is
one CSV file — so the caller-facing knob is ``max_rows``. Slices are
modest (the biggest healthcare slice probed live, industry 62 for one
quarter, is ~11k rows / ~1.4 MB), so :data:`DEFAULT_MAX_ROWS` is set
high enough to be a full pull for every real slice while still bounding
a pathological response; the transport streams, so a capped fetch
downloads only what it parses.

``fetch`` keeps the estate's step shape (rows + ``next_cursor``) for
uniformity with the paging connectors; for a single-file source the
cursor is always ``None`` — one step is the whole (possibly capped)
slice. ``refresh`` is the fetch → normalize → upsert convenience the
CLI drives.

Which slice a call lands on is ``params``-driven and defaults to the
pinned latest published quarter (see endpoints.py)::

    fetch("industry_area", {"industry": "622", "year": 2024, "qtr": 1})
    fetch("area_industry", {"area": "48453"})   # → 2025 Q4 default
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from .endpoints import (ENDPOINTS, EndpointSpec, get_endpoint,
                        resolve_params, slice_path)
from .normalize import normalize
from .transport import Opener, QcewTransport

# Default ingest cap. Every live slice probed 2026-07-06 is well under
# this (industry 62: ~11k rows/quarter; area US000: ~7k; county areas:
# ~2-3k), so the default is a *full* pull in practice; the cap exists so
# a pathological or future giant slice cannot balloon an ingest
# unnoticed. Pass max_rows=None (CLI --full) to remove it.
DEFAULT_MAX_ROWS = 50_000


@dataclass
class FetchResult:
    """One ``fetch`` step's output (for CSV slices, the only step)."""

    rows: List[Dict[str, str]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    params: Dict[str, str] = field(default_factory=dict)  # resolved slice
    path: str = ""
    fieldnames: List[str] = field(default_factory=list)
    truncated: bool = False        # max_rows cut the slice short
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class BlsQcewConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full download/parse path with a fake
    server.
    """

    def __init__(
        self,
        transport: Optional[QcewTransport] = None,
        *,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or QcewTransport.from_env()
        self._sleep = sleep

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the slice kinds this connector ingests (offline —
        the slice universe is declarative, not crawled)."""
        return list(ENDPOINTS.values())

    # ── fetch (single-shot per slice; cursor kept for estate parity) ──
    def fetch(
        self,
        endpoint: Union[EndpointSpec, str],
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,  # accepted for parity; unused
        *,
        max_rows: Optional[int] = DEFAULT_MAX_ROWS,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Download one slice's raw rows (capped at ``max_rows``).

        ``params`` picks the slice (``industry``/``area`` code +
        ``year`` + ``qtr``), defaulting to the pinned latest published
        quarter. Validation happens before any network call, so a bad
        year/qtr/code raises ``ValueError`` instantly. ``cursor`` exists
        for signature parity with the paging connectors; ``next_cursor``
        is always ``None`` — there is nothing to resume.
        """
        spec = get_endpoint(endpoint) if isinstance(endpoint, str) else endpoint
        resolved = resolve_params(spec, params or {})
        path = slice_path(spec, resolved["year"], resolved["qtr"],
                          resolved[spec.code_param])
        start_requests = self.transport.requests_made
        result = self.transport.get_csv(
            path, max_rows=max_rows, opener=opener, sleep=self._sleep)
        return FetchResult(
            rows=result.rows,
            next_cursor=None,
            endpoint=spec.key,
            params=resolved,
            path=path,
            fieldnames=result.fieldnames,
            truncated=result.truncated,
            requests=self.transport.requests_made - start_requests,
        )

    def fetch_all(
        self,
        endpoint: Union[EndpointSpec, str],
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> List[Dict[str, str]]:
        """Convenience: one entire slice, uncapped."""
        return self.fetch(endpoint, params, max_rows=None, opener=opener).rows

    # ── refresh: fetch + normalize + upsert ───────────────────────────
    def refresh(
        self,
        store: Any,
        endpoint: Union[EndpointSpec, str],
        params: Optional[Dict[str, Any]] = None,
        *,
        max_rows: Optional[int] = DEFAULT_MAX_ROWS,
        opener: Optional[Opener] = None,
    ) -> Dict[str, Any]:
        """Ingest one slice end-to-end; returns counts for reporting.

        ``store`` is duck-typed (needs ``upsert(table, rows)``) so this
        module never imports :mod:`tables` — normalize and storage stay
        independently testable.
        """
        spec = get_endpoint(endpoint) if isinstance(endpoint, str) else endpoint
        step = self.fetch(spec, params, max_rows=max_rows, opener=opener)
        res = normalize(spec, step.rows)
        upserted: Dict[str, int] = {}
        for table, rows in res.rows.items():
            upserted[table] = store.upsert(table, rows)
        return {
            "dataset_id": spec.dataset_id,
            "endpoint": spec.key,
            "params": step.params,
            "path": step.path,
            "fetched": len(step.rows),
            "truncated": step.truncated,
            "upserted": upserted,
            "unmapped_fields": dict(res.unmapped),
            "requests": step.requests,
        }
