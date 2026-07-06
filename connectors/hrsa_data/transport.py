"""HTTP transport for HRSA data downloads: streamed CSV + retry/backoff.

HRSA publishes these datasets as plain CSV files (10-60 MB each) under
``https://data.hrsa.gov/DataDownload/DD_Files/`` — there is no JSON API
and no key. That shapes this transport in two ways:

  * **Streaming, not buffering** — the default opener hands the live
    ``http.client`` response back as a binary stream and the CSV parser
    reads it incrementally, so a ``max_rows``-capped ingest of a 48 MB
    file never buffers the whole body. Fake openers used in tests keep
    the simple ``body: bytes`` contract; :meth:`RawResponse.reader`
    unifies both.
  * **Whole-file retry envelope** — a CSV download either completes or
    it doesn't; there is no page to resume. HTTP 429/5xx and transport
    errors (including a mid-stream socket drop while parsing) retry the
    whole request with exponential backoff + full jitter, honouring
    ``Retry-After`` (clamped to ``[0, backoff cap]`` — a hostile or
    buggy negative value must not abort the loop). Download integrity
    is verified: an uncapped parse that consumes fewer bytes than the
    response's ``Content-Length`` declared, or a chunked-body
    ``http.client.IncompleteRead``, is a *retryable* failure — a
    silently truncated file is never treated as complete. A 404 raises
    immediately with a pointer to
    https://data.hrsa.gov/data/download because it means HRSA renamed
    the file — retrying cannot fix that.

The opener is injectable so every retry / backoff / parse path is unit
tested against an in-memory fake with no socket — the same testability
contract the rest of RCM-MC's public-data clients follow.

Politeness: no rate limit is published for the download files; the
inter-request floor below is a courtesy default, not a documented
contract (each request is one whole file, so traffic is naturally low).
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
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_DEFAULT_USER_AGENT = (
    "rcm/hrsa-data-connector (github.com/DrewThomas09/RCM; "
    "commercial-diligence research)"
)
_HRSA_BASE = "https://data.hrsa.gov"

# Conservative defaults. Overridable via the constructor.
_DEFAULT_MIN_INTERVAL_S = 1.0         # whole-file pulls; stay very polite
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0
_DEFAULT_TIMEOUT_S = 60.0             # socket-level; the files are large


class HrsaApiError(RuntimeError):
    """Raised when HRSA is unreachable or returns an unrecoverable error."""


class _TruncatedBodyError(OSError):
    """The body ended before the declared ``Content-Length`` was delivered.

    A connection dropped mid-body must never yield a silently partial
    file. ``OSError`` so the mid-stream retry handler in
    :meth:`HrsaTransport.get_csv` treats it as a transient and re-pulls;
    on exhaustion it surfaces wrapped in :class:`HrsaApiError` like
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
    ``http.client`` response) so multi-MB files are parsed incrementally;
    fakes populate ``body`` and :meth:`reader` bridges the two.
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


def _default_opener(url: str, headers: Dict[str, str], timeout_s: float) -> RawResponse:
    """urllib opener that never raises on HTTP status — it folds HTTPError
    into a :class:`RawResponse` so the retry loop owns all status logic.

    On 200 the response object itself is returned as ``stream`` (not
    read into memory) so the CSV parser can stop early under
    ``max_rows`` without downloading the rest of a 48 MB file.
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
    """One parsed CSV download (possibly capped by ``max_rows``).

    ``fieldnames`` are the *raw* header names as published (spaces,
    slashes, ``%`` and all) with empty trailing header cells dropped —
    every live HRSA file ends its header row with a dangling comma.
    ``rows`` are raw ``{header: value}`` dicts; snake_casing and key
    composition happen in :mod:`connectors.hrsa_data.normalize`.
    """

    fieldnames: List[str]
    rows: List[Dict[str, str]]
    truncated: bool = False        # True when max_rows cut the file short

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass
class HrsaTransport:
    """Throttled, retrying CSV transport against ``data.hrsa.gov``."""

    user_agent: str = _DEFAULT_USER_AGENT
    base_url: str = _HRSA_BASE
    timeout_s: float = _DEFAULT_TIMEOUT_S
    min_interval_s: float = _DEFAULT_MIN_INTERVAL_S
    max_retries: int = _DEFAULT_MAX_RETRIES
    backoff_base_s: float = _DEFAULT_BACKOFF_BASE_S
    backoff_cap_s: float = _DEFAULT_BACKOFF_CAP_S
    _last_call_s: float = field(default=0.0, repr=False)
    requests_made: int = field(default=0, repr=False)

    @classmethod
    def from_env(cls, **overrides: Any) -> "HrsaTransport":
        """Build a transport. No key exists for HRSA downloads; env only
        tunes the user agent so a shared crawler can identify itself."""
        import os
        params: Dict[str, Any] = {}
        ua = os.environ.get("HRSA_DATA_USER_AGENT")
        if ua:
            params["user_agent"] = ua
        params.update(overrides)
        return cls(**params)

    def build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Pure URL builder. HRSA download files take no query params in
        practice; the seam exists for parity with the other connectors
        and keeps URLs (and test assertions) deterministic."""
        merged: Dict[str, Any] = dict(params or {})
        query = urlencode([(k, merged[k]) for k in sorted(merged)])
        sep = "&" if "?" in path else "?"
        tail = f"{sep}{query}" if query else ""
        return f"{self.base_url}{path}{tail}"

    def _throttle(self, sleep: Callable[[float], None], now: Callable[[], float]) -> None:
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
        params: Optional[Dict[str, Any]] = None,
        *,
        max_rows: Optional[int] = None,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
        rand: Callable[[], float] = random.random,
    ) -> CsvResult:
        """Download one CSV file and parse up to ``max_rows`` data rows.

        Retries 429/5xx/transport errors — including a failure that
        happens *mid-stream* while parsing, since a partial CSV is
        useless and the whole file must be re-pulled. Raises
        :class:`HrsaApiError` after exhausting retries, on an
        unrecoverable 4xx, or on a 404 (a renamed file: check
        https://data.hrsa.gov/data/download for the current name).
        """
        opener = opener or _default_opener
        url = self.build_url(path, params)
        # Accept must stay */* — HRSA's server answers 406 to
        # ``Accept: text/csv`` on these download paths (verified live
        # 2026-07-06 with curl; the header, not the user agent, trips it).
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
                raise HrsaApiError(
                    f"{url}: HTTP 404 — HRSA download file not found. HRSA "
                    f"occasionally renames files; check the current name at "
                    f"https://data.hrsa.gov/data/download and update "
                    f"connectors/hrsa_data/endpoints.py")
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
            raise HrsaApiError(f"{url}: HTTP {status} {detail}")
        raise HrsaApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    @staticmethod
    def _parse_csv(resp: RawResponse, max_rows: Optional[int], url: str
                   ) -> CsvResult:
        """Incrementally parse a CSV byte stream into raw row dicts.

        Quirks handled here because every live HRSA file exhibits them
        (verified 2026-07-06):

          * decoded as ``utf-8-sig`` so a BOM, if HRSA ever adds one,
            never pollutes the first header;
          * the header row ends with a dangling comma → empty trailing
            header cells are dropped, and the matching trailing value
            on every data row is ignored;
          * rows shorter than the header are padded with ``""`` so the
            dict shape is stable for the normalizer;
          * when the response declares ``Content-Length`` and the parse
            reaches end-of-stream (i.e. was not cut short by
            ``max_rows``), the bytes actually consumed are verified
            against it — ``http.client`` returns a short read, not an
            error, when a non-chunked connection drops mid-body, and a
            silently truncated file must never be treated as complete.
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
            raise HrsaApiError(f"{url}: empty CSV (no header row)") from None
        keep = [(i, h.strip()) for i, h in enumerate(header_row) if h.strip()]
        if not keep:
            raise HrsaApiError(f"{url}: header row has no named columns")
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
