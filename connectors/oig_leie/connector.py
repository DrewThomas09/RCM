"""The OIG LEIE connector: ``discover()`` + ``fetch()`` + ``refresh()``.

There is no native paging to absorb — each dataset is one CSV file — so
the caller-facing knob is ``max_rows``. The default cap of
:data:`DEFAULT_MAX_ROWS` (100,000) deliberately *covers the whole full
file* (~83k rows as of 2026-06): the LEIE is a compliance list, and a
silently-truncated exclusion screen is worse than a 15 MB download. The
cap still guards against the file unexpectedly ballooning; pass
``max_rows=None`` (CLI ``--full``) for an explicitly uncapped pull.

The two supplement datasets are month-parameterised. When the caller
names a month, exactly that file is fetched. When no month is given, the
connector walks back from the current UTC month through
:data:`SUPPLEMENT_LOOKBACK_MONTHS` months, skipping 404s, and ingests
the most recent published file — the live index shows some months
publish no file at all (e.g. there is no ``2505excl.csv``), so "latest"
genuinely requires probing.

``fetch`` keeps the estate's step shape (rows + ``next_cursor``) for
uniformity with the paging connectors; for a single-file source the
cursor is always ``None`` — one step is the whole (possibly capped)
file. ``refresh`` is the fetch → normalize → upsert convenience the CLI
drives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .normalize import normalize
from .transport import OigLeieApiError, OigLeieTransport, Opener

# Default ingest cap. Covers the whole ~83k-row full file (a compliance
# list must not be silently partial) while still bounding a runaway pull.
DEFAULT_MAX_ROWS = 100_000

# How many months the supplement fetch walks back from the current UTC
# month when the caller names none. Six covers OIG's observed gaps (a
# month or two without a published file) with room to spare.
SUPPLEMENT_LOOKBACK_MONTHS = 6


@dataclass
class FetchResult:
    """One ``fetch`` step's output (for CSV files, the only step)."""

    rows: List[Dict[str, str]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    fieldnames: List[str] = field(default_factory=list)
    truncated: bool = False        # max_rows cut the file short
    requests: int = 0
    url: str = ""
    year: Optional[int] = None     # resolved supplement month (None = full file)
    month: Optional[int] = None

    @property
    def done(self) -> bool:
        return self.next_cursor is None

    @property
    def month_tag(self) -> Optional[str]:
        if self.year is None or self.month is None:
            return None
        return f"{self.year:04d}-{self.month:02d}"


def _previous_month(year: int, month: int) -> Tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


class OigLeieConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive the full download/parse path with a fake
    server. ``today`` is injectable so the supplement month walk-back is
    deterministic under test.
    """

    def __init__(
        self,
        transport: Optional[OigLeieTransport] = None,
        *,
        sleep: Callable[[float], None] = __import__("time").sleep,
        today: Optional[Callable[[], date]] = None,
    ) -> None:
        self.transport = transport or OigLeieTransport.from_env()
        self._sleep = sleep
        self._today = today or (lambda: datetime.now(timezone.utc).date())

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the LEIE datasets this connector ingests."""
        return list(ENDPOINTS.values())

    # ── fetch (single-shot per file; cursor kept for estate parity) ───
    def fetch(
        self,
        endpoint: Union[EndpointSpec, str],
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,  # accepted for parity; unused
        *,
        max_rows: Optional[int] = DEFAULT_MAX_ROWS,
        year: Optional[int] = None,
        month: Optional[int] = None,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Download one file's raw rows (capped at ``max_rows``).

        ``cursor`` exists for signature parity with the paging
        connectors; ``next_cursor`` is always ``None`` — there is
        nothing to resume. ``year``/``month`` select a supplement month
        (also accepted inside ``params`` for estate parity); omitted,
        the newest published month within the walk-back window is used.
        The full-file dataset ignores both.
        """
        spec = get_endpoint(endpoint) if isinstance(endpoint, str) else endpoint
        params = dict(params or {})
        year = int(params.get("year", year)) if params.get("year") or year else None
        month = int(params.get("month", month)) if params.get("month") or month else None

        if spec.dataset_kind == "full":
            return self._fetch_path(spec, spec.path(), max_rows, opener,
                                    None, None)
        if year is not None and month is not None:
            return self._fetch_path(spec, spec.path(year, month), max_rows,
                                    opener, year, month)
        if (year is None) != (month is None):
            raise ValueError(
                f"dataset {spec.key!r}: give both year and month, or neither "
                f"(neither = newest published month)")
        return self._fetch_latest_supplement(spec, max_rows, opener)

    def _fetch_path(
        self,
        spec: EndpointSpec,
        path: str,
        max_rows: Optional[int],
        opener: Optional[Opener],
        year: Optional[int],
        month: Optional[int],
    ) -> FetchResult:
        start_requests = self.transport.requests_made
        result = self.transport.get_csv(
            path, dict(spec.default_params), max_rows=max_rows,
            opener=opener, sleep=self._sleep)
        return FetchResult(
            rows=result.rows,
            next_cursor=None,
            endpoint=spec.key,
            fieldnames=result.fieldnames,
            truncated=result.truncated,
            requests=self.transport.requests_made - start_requests,
            url=self.transport.build_url(path),
            year=year,
            month=month,
        )

    def _fetch_latest_supplement(
        self,
        spec: EndpointSpec,
        max_rows: Optional[int],
        opener: Optional[Opener],
    ) -> FetchResult:
        """Walk back month-by-month until a published file answers 200.

        A 404 is expected traffic here — OIG publishes the supplements
        per month and skips months with nothing to report — so only a
        404 continues the walk; any other failure propagates.
        """
        today = self._today()
        y, m = today.year, today.month
        tried: List[str] = []
        for _ in range(SUPPLEMENT_LOOKBACK_MONTHS):
            path = spec.path(y, m)
            try:
                return self._fetch_path(spec, path, max_rows, opener, y, m)
            except OigLeieApiError as exc:
                if exc.status != 404:
                    raise
                tried.append(f"{y:04d}-{m:02d}")
                y, m = _previous_month(y, m)
        raise OigLeieApiError(
            f"no published {spec.key} supplement found in the last "
            f"{SUPPLEMENT_LOOKBACK_MONTHS} months (tried {', '.join(tried)}); "
            f"see https://oig.hhs.gov/exclusions/exclusions_list.asp for the "
            f"published index, or pass an explicit year/month",
            status=404,
        )

    def fetch_all(
        self,
        endpoint: Union[EndpointSpec, str],
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        opener: Optional[Opener] = None,
    ) -> List[Dict[str, str]]:
        """Convenience: the *entire* file, uncapped. The full LEIE is
        ~15 MB / ~83k rows."""
        return self.fetch(endpoint, max_rows=None, year=year, month=month,
                          opener=opener).rows

    # ── refresh: fetch + normalize + upsert ───────────────────────────
    def refresh(
        self,
        store: Any,
        endpoint: Union[EndpointSpec, str],
        *,
        max_rows: Optional[int] = DEFAULT_MAX_ROWS,
        year: Optional[int] = None,
        month: Optional[int] = None,
        opener: Optional[Opener] = None,
    ) -> Dict[str, Any]:
        """Ingest one dataset end-to-end; returns counts for reporting.

        ``store`` is duck-typed (needs ``upsert(table, rows)``) so this
        module never imports :mod:`tables` — normalize and storage stay
        independently testable.
        """
        spec = get_endpoint(endpoint) if isinstance(endpoint, str) else endpoint
        step = self.fetch(spec, max_rows=max_rows, year=year, month=month,
                          opener=opener)
        res = normalize(spec, step.rows, month_tag=step.month_tag)
        upserted: Dict[str, int] = {}
        for table, rows in res.rows.items():
            upserted[table] = store.upsert(table, rows)
        return {
            "dataset_id": spec.dataset_id,
            "endpoint": spec.key,
            "url": step.url,
            "year": step.year,
            "month": step.month,
            "fetched": len(step.rows),
            "truncated": step.truncated,
            "upserted": upserted,
            "unmapped_fields": dict(res.unmapped),
            "requests": step.requests,
        }
