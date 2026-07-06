"""The HRSA data connector: ``discover()`` + ``fetch()`` + ``refresh()``.

There is no native paging to absorb — each dataset is one CSV file — so
the caller-facing knob is ``max_rows``: the files run 10-60 MB (the
primary-care HPSA file alone is ~79k rows / 48 MB), and accidental
full pulls of all five files would move ~125 MB. ``fetch`` therefore
caps ingest at :data:`DEFAULT_MAX_ROWS` unless the caller explicitly
passes ``max_rows=None`` (the CLI exposes this as ``--full``). The
transport streams, so a capped fetch downloads only what it parses.

``fetch`` keeps the estate's step shape (rows + ``next_cursor``) for
uniformity with the paging connectors; for a single-file source the
cursor is always ``None`` — one step is the whole (possibly capped)
file. ``refresh`` is the fetch → normalize → upsert convenience the CLI
drives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .normalize import normalize
from .transport import HrsaTransport, Opener

# Default ingest cap. ~50k rows keeps a default run of the biggest file
# (79k-row primary-care HPSA) bounded while still being a full pull for
# MUA (~20k) and sites (~19k). Pass max_rows=None (CLI --full) for all.
DEFAULT_MAX_ROWS = 50_000


@dataclass
class FetchResult:
    """One ``fetch`` step's output (for CSV files, the only step)."""

    rows: List[Dict[str, str]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    fieldnames: List[str] = field(default_factory=list)
    truncated: bool = False        # max_rows cut the file short
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class HrsaDataConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full download/parse path with a fake
    server.
    """

    def __init__(
        self,
        transport: Optional[HrsaTransport] = None,
        *,
        sleep: Callable[[float], None] = __import__("time").sleep,
    ) -> None:
        self.transport = transport or HrsaTransport.from_env()
        self._sleep = sleep

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the download files this connector ingests."""
        return list(ENDPOINTS.values())

    # ── fetch (single-shot per file; cursor kept for estate parity) ───
    def fetch(
        self,
        endpoint: Union[EndpointSpec, str],
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,  # accepted for parity; unused
        *,
        max_rows: Optional[int] = DEFAULT_MAX_ROWS,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Download one file's raw rows (capped at ``max_rows``).

        ``params``/``cursor`` exist for signature parity with the paging
        connectors; HRSA downloads take neither. ``next_cursor`` is
        always ``None`` — there is nothing to resume.
        """
        spec = get_endpoint(endpoint) if isinstance(endpoint, str) else endpoint
        start_requests = self.transport.requests_made
        result = self.transport.get_csv(
            spec.path, dict(spec.default_params), max_rows=max_rows,
            opener=opener, sleep=self._sleep)
        return FetchResult(
            rows=result.rows,
            next_cursor=None,
            endpoint=spec.key,
            fieldnames=result.fieldnames,
            truncated=result.truncated,
            requests=self.transport.requests_made - start_requests,
        )

    def fetch_all(
        self,
        endpoint: Union[EndpointSpec, str],
        *,
        opener: Optional[Opener] = None,
    ) -> List[Dict[str, str]]:
        """Convenience: the *entire* file, uncapped. Use deliberately —
        the HPSA primary-care file is ~48 MB."""
        return self.fetch(endpoint, max_rows=None, opener=opener).rows

    # ── refresh: fetch + normalize + upsert ───────────────────────────
    def refresh(
        self,
        store: Any,
        endpoint: Union[EndpointSpec, str],
        *,
        max_rows: Optional[int] = DEFAULT_MAX_ROWS,
        opener: Optional[Opener] = None,
    ) -> Dict[str, Any]:
        """Ingest one dataset end-to-end; returns counts for reporting.

        ``store`` is duck-typed (needs ``upsert(table, rows)``) so this
        module never imports :mod:`tables` — normalize and storage stay
        independently testable.
        """
        spec = get_endpoint(endpoint) if isinstance(endpoint, str) else endpoint
        step = self.fetch(spec, max_rows=max_rows, opener=opener)
        res = normalize(spec, step.rows)
        upserted: Dict[str, int] = {}
        for table, rows in res.rows.items():
            upserted[table] = store.upsert(table, rows)
        return {
            "dataset_id": spec.dataset_id,
            "endpoint": spec.key,
            "file": spec.file_name,
            "fetched": len(step.rows),
            "truncated": step.truncated,
            "upserted": upserted,
            "unmapped_fields": dict(res.unmapped),
            "requests": step.requests,
        }
