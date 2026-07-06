"""HTTP transport for BLS QCEW slice downloads: streamed CSV + retry/backoff.

QCEW's open data access is a set of pre-cut CSV files behind stable
URLs — no key, no JSON, no paging. That shapes this transport the same
way it shaped the HRSA connector's:

  * **Streaming, not buffering** — the default opener hands the live
    ``http.client`` response back as a binary stream and the CSV parser
    reads it incrementally, so a ``max_rows``-capped ingest never
    buffers a whole slice (the biggest healthcare slice probed live,
    industry 62 for one quarter, is ~1.4 MB / ~11k rows — small, but
    the contract matters for uniformity and for pathological slices).
  * **Whole-file retry envelope** — a slice either downloads completely
    or it doesn't; there is no page to resume. HTTP 429/5xx and
    transport errors (including a mid-stream drop while parsing) retry
    the whole request with exponential backoff + full jitter, honouring
    ``Retry-After`` (clamped to ``[0, backoff cap]`` — a hostile or
    buggy negative value must not abort the loop). Download integrity
    is verified: an uncapped parse that consumes fewer bytes than the
    response's ``Content-Length`` declared, or a chunked-body
    ``http.client.IncompleteRead``, is a *retryable* failure — a
    silently truncated slice is never treated as complete.
  * **404 is a signal, not a transient** — QCEW answers 404 for any
    year/quarter/code outside the published window, so the error names
    the live-verified window (2014 Q1 - 2025 Q4 as of 2026-07-06) and
    points at the BLS slice documentation instead of retrying.

The opener is injectable so every retry / backoff / parse path is unit
tested against an in-memory fake with no socket — the same testability
contract the rest of RCM-MC's public-data clients follow.

Politeness: BLS publishes no rate limit for these files; the
inter-request floor below is a courtesy default (each request is one
whole slice, so traffic is naturally low).
"""
from __future__ import annotations

import csv
import io
import random
import time
from dataclasses import dataclass, field
from http.client import IncompleteRead
from typing import Any, BinaryIO, Callable, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .endpoints import EARLIEST_YEAR, LATEST_QTR, LATEST_YEAR, _BLS_BASE

USER_AGENT = "rcm-connectors/bls_qcew"
DEFAULT_BASE_URL = _BLS_BASE

_SLICE_DOC_URL = (
    "https://www.bls.gov/cew/additional-resources/open-data/"
    "csv-data-slices.htm")

# Conservative defaults. Overridable via the constructor.
_DEFAULT_MIN_INTERVAL_S = 0.5         # whole-slice pulls; stay polite
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0
_DEFAULT_TIMEOUT_S = 30.0


class QcewApiError(RuntimeError):
    """Raised when QCEW is unreachable or returns an unrecoverable error."""


class _TruncatedBodyError(OSError):
    """The body ended before the declared ``Content-Length`` was delivered.

    A connection dropped mid-body must never yield a silently partial
    slice. ``OSError`` so the mid-stream retry handler in
    :meth:`QcewTransport.get_csv` treats it as a transient and re-pulls;
    on exhaustion it surfaces wrapped in :class:`QcewApiError` like
    every other transport failure.
    """


class _CountingStream(io.RawIOBase):
    """Counts bytes consumed from a wrapped binary stream.

    Lets the parser verify, once it reaches EOF, that the number of
    bytes actually delivered matches the response's ``Content-Length``
    — ``http.client`` returns a short read (not an error) when a
    non-chunked connection drops mid-body.
    """

    def __init__(self, raw: BinaryIO) -> None:
        super().__init__()
        self._raw = raw
        self.bytes_read = 0

    def readable(self) -> bool:  # pragma: no cover - io protocol
        return True

    def readinto(self, b) -> int:
        chunk = self._raw.read(len(b))
        n = len(chunk)
        b[:n] = chunk
        self.bytes_read += n
        return n


def _declared_content_length(resp: "RawResponse") -> Optional[int]:
    """The response's ``Content-Length`` as an int, or ``None`` when the
    header is absent/malformed (nothing to verify against)."""
    raw = resp.header("content-length")
    if raw is None:
        return None
    try:
        value = int(raw.strip())
    except (ValueError, AttributeError):
        return None
    return value if value >= 0 else None


def _verify_body_complete(resp: "RawResponse", counting: _CountingStream,
                          url: str) -> None:
    """Raise :class:`_TruncatedBodyError` when fewer bytes arrived than
    ``Content-Length`` declared (connection dropped mid-body)."""
    expected = _declared_content_length(resp)
    if expected is not None and counting.bytes_read < expected:
        raise _TruncatedBodyError(
            f"{url}: truncated body: read {counting.bytes_read} of "
            f"{expected} bytes (Content-Length)")


@dataclass(frozen=True)
class RawResponse:
    """A minimal HTTP response the retry loop can reason about.

    Injectable openers return this so tests can assert on 429 +
    ``Retry-After`` handling without a real socket. ``headers`` keys are
    lower-cased. ``stream`` is set only by the live opener (the raw
    ``http.client`` response) so slices are parsed incrementally; fakes
    populate ``body`` and :meth:`reader` bridges the two.
    """

    status: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    stream: Optional[BinaryIO] = None

    def header(self, name: str) -> Optional[str]:
        return self.headers.get(name.lower())

    def reader(self) -> BinaryIO:
        return self.stream if self.stream is not None else io.BytesIO(self.body)

    def close(self) -> None:
        if self.stream is not None:
            try:
                self.stream.close()
            except Exception:
                pass


# Opener signature: (full_url, headers, timeout_s) -> RawResponse.
Opener = Callable[[str, Dict[str, str], float], RawResponse]


def _default_opener(url: str, headers: Dict[str, str], timeout_s: float
                    ) -> RawResponse:
    """urllib opener that never raises on HTTP status — it folds HTTPError
    into a :class:`RawResponse` so the retry loop owns all status logic.

    On 200 the response object itself is returned as ``stream`` (not
    read into memory) so the CSV parser can stop early under
    ``max_rows`` without downloading the rest of the file.
    """
    req = Request(url, headers=headers)
    try:
        resp = urlopen(req, timeout=timeout_s)  # noqa: S310 (fixed https base)
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        return RawResponse(status=resp.status, headers=hdrs, stream=resp)
    except HTTPError as exc:
        raw = b""
        try:
            raw = exc.read()
        except Exception:
            pass
        hdrs = {k.lower(): v for k, v in (exc.headers or {}).items()}
        return RawResponse(status=exc.code, headers=hdrs, body=raw)
    except (URLError, TimeoutError, OSError) as exc:
        # Surface transport-level failures as status 0 so the loop retries.
        return RawResponse(status=0, headers={}, body=str(exc).encode())


@dataclass
class CsvResult:
    """One parsed CSV slice (possibly capped by ``max_rows``).

    ``fieldnames`` are the raw header names exactly as published — QCEW
    headers are already lowercase snake_case (``area_fips``,
    ``month3_emplvl``, …), which normalize.py verifies rather than
    rewrites. ``rows`` are raw ``{header: value}`` dicts; key
    composition happens in :mod:`connectors.bls_qcew.normalize`.
    """

    fieldnames: List[str]
    rows: List[Dict[str, str]]
    truncated: bool = False        # True when max_rows cut the file short

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass
class QcewTransport:
    """Throttled, retrying CSV transport against ``data.bls.gov``."""

    user_agent: str = USER_AGENT
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = _DEFAULT_TIMEOUT_S
    min_interval_s: float = _DEFAULT_MIN_INTERVAL_S
    max_retries: int = _DEFAULT_MAX_RETRIES
    backoff_base_s: float = _DEFAULT_BACKOFF_BASE_S
    backoff_cap_s: float = _DEFAULT_BACKOFF_CAP_S
    _last_call_s: float = field(default=0.0, repr=False)
    requests_made: int = field(default=0, repr=False)

    @classmethod
    def from_env(cls, **overrides: Any) -> "QcewTransport":
        """Build a transport. No key exists for QCEW slices; env only
        tunes the user agent so a shared crawler can identify itself."""
        import os
        params: Dict[str, Any] = {}
        ua = os.environ.get("BLS_QCEW_USER_AGENT")
        if ua:
            params["user_agent"] = ua
        params.update(overrides)
        return cls(**params)

    def build_url(self, path: str) -> str:
        """Pure URL builder. QCEW slice URLs take no query string — the
        year/qtr/code are path segments, validated and rendered by
        :func:`connectors.bls_qcew.endpoints.slice_path`. The seam keeps
        URLs (and test assertions) deterministic."""
        return f"{self.base_url}{path}"

    def _throttle(self, sleep: Callable[[float], None],
                  now: Callable[[], float]) -> None:
        if self.min_interval_s <= 0:
            return
        wait = self.min_interval_s - (now() - self._last_call_s)
        if wait > 0:
            sleep(wait)

    def _backoff_seconds(self, attempt: int, resp: Optional[RawResponse],
                         rand: Callable[[], float]) -> float:
        """Retry-After wins; otherwise exponential backoff with full jitter."""
        if resp is not None:
            ra = resp.header("retry-after")
            if ra:
                try:
                    parsed = float(ra)
                except ValueError:
                    pass  # HTTP-date / garbage form; fall through to backoff
                else:
                    # Clamp to [0, cap]: a negative (or NaN) Retry-After
                    # must never reach time.sleep(), which raises
                    # ValueError and would abort the retry loop.
                    return max(0.0, min(parsed, self.backoff_cap_s))
        ceiling = min(self.backoff_cap_s, self.backoff_base_s * (2 ** attempt))
        return ceiling * rand()  # full jitter in [0, ceiling)

    def get_csv(
        self,
        path: str,
        *,
        max_rows: Optional[int] = None,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
        rand: Callable[[], float] = random.random,
    ) -> CsvResult:
        """Download one CSV slice and parse up to ``max_rows`` data rows.

        Retries 429/5xx/transport errors — including a failure that
        happens *mid-stream* while parsing, since a partial slice is
        useless and the whole file must be re-pulled. Raises
        :class:`QcewApiError` after exhausting retries, on an
        unrecoverable 4xx, or on a 404 (a year/quarter/code outside the
        published window — the message names the window because
        retrying cannot fix that).
        """
        opener = opener or _default_opener
        url = self.build_url(path)
        # Accept stays */* — some .gov download hosts answer 406 to a
        # narrow Accept (HRSA verifiably does); QCEW serves */* fine.
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        last_status = -1
        last_detail = ""
        for attempt in range(self.max_retries + 1):
            self._throttle(sleep, now)
            resp = opener(url, headers, self.timeout_s)
            self._last_call_s = now()
            self.requests_made += 1
            status = resp.status

            if status == 200:
                try:
                    return self._parse_csv(resp, max_rows, url)
                except (OSError, TimeoutError, IncompleteRead, csv.Error,
                        UnicodeDecodeError) as exc:
                    # Mid-stream failure (incl. a chunked-body
                    # IncompleteRead or a Content-Length shortfall):
                    # treat like a transient and re-pull the file
                    # (bounded by max_retries).
                    last_status, last_detail = 200, f"mid-stream: {exc}"
                    if attempt < self.max_retries:
                        sleep(self._backoff_seconds(attempt, None, rand))
                        continue
                    break
                finally:
                    resp.close()
            if status == 404:
                resp.close()
                raise QcewApiError(
                    f"{url}: HTTP 404 — no QCEW slice at this "
                    f"year/qtr/code. Quarterly slices exist for "
                    f"{EARLIEST_YEAR} Q1 through {LATEST_YEAR} "
                    f"Q{LATEST_QTR} (window verified live 2026-07-06; "
                    f"BLS publishes a quarter ~5 months after it ends). "
                    f"Check the code spelling and see {_SLICE_DOC_URL}")
            if status == 429 or status >= 500 or status == 0:
                last_status, last_detail = status, _short_body(resp.body)
                resp.close()
                if attempt < self.max_retries:
                    sleep(self._backoff_seconds(attempt, resp, rand))
                    continue
                break
            # Other 4xx (400, 403) won't fix on retry.
            detail = _short_body(resp.body)
            resp.close()
            raise QcewApiError(f"{url}: HTTP {status} {detail}")
        raise QcewApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    @staticmethod
    def _parse_csv(resp: RawResponse, max_rows: Optional[int], url: str
                   ) -> CsvResult:
        """Incrementally parse a CSV byte stream into raw row dicts.

        QCEW files are clean RFC-4180 CSV (quoted string cells, bare
        numeric cells, no dangling trailing commas — verified live
        2026-07-06), but the parser stays defensive for uniformity with
        the estate's other CSV transports:

          * decoded as ``utf-8-sig`` so a BOM, if BLS ever adds one,
            never pollutes the first header;
          * empty header cells are dropped and the matching value
            ignored;
          * rows shorter than the header are padded with ``""`` so the
            dict shape is stable for the normalizer;
          * when the response declares ``Content-Length`` and the parse
            reaches end-of-stream (i.e. was not cut short by
            ``max_rows``), the bytes actually consumed are verified
            against it — ``http.client`` returns a short read, not an
            error, when a non-chunked connection drops mid-body, and a
            silently truncated slice must never be treated as complete.
            A shortfall raises (retryable) so the whole file is
            re-pulled.
        """
        counting = _CountingStream(resp.reader())
        text = io.TextIOWrapper(io.BufferedReader(counting),
                                encoding="utf-8-sig", newline="")
        reader = csv.reader(text)
        try:
            header_row = next(reader)
        except StopIteration:
            _verify_body_complete(resp, counting, url)
            raise QcewApiError(f"{url}: empty CSV (no header row)") from None
        keep = [(i, h.strip()) for i, h in enumerate(header_row) if h.strip()]
        if not keep:
            raise QcewApiError(f"{url}: header row has no named columns")
        fieldnames = [h for _, h in keep]

        rows: List[Dict[str, str]] = []
        truncated = False
        for row in reader:
            if not row:
                continue  # tolerate stray blank lines
            if max_rows is not None and len(rows) >= max_rows:
                truncated = True
                break
            rows.append({h: (row[i] if i < len(row) else "") for i, h in keep})
        if not truncated:
            # EOF reached: every delivered byte was consumed, so the
            # count is comparable to Content-Length. A max_rows-capped
            # parse stops early by design and cannot be verified.
            _verify_body_complete(resp, counting, url)
        return CsvResult(fieldnames=fieldnames, rows=rows, truncated=truncated)


def _short_body(body: bytes, limit: int = 200) -> str:
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        text = repr(body[:limit])
    text = " ".join(text.split())
    return text[:limit]
