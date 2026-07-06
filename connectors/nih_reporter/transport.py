"""HTTP transport for NIH RePORTER v2: POST JSON + throttle + 429/5xx backoff.

The NIH RePORTER API (``api.reporter.nih.gov``) is public and needs no
key, but unlike the estate's GET connectors every search is an HTTP
**POST** with a JSON body (``{"criteria": ..., "offset": ..., "limit":
...}``) — so the workhorse here is :meth:`NihReporterTransport.post_json`
rather than a ``get_json``. The retry envelope is identical to the rest
of the estate.

NIH asks callers to stay at or below **one request per second** (see
https://api.reporter.nih.gov), so the default inter-request floor is a
full second — a courtesy default, verify live before a bulk run. Deep
``offset`` pages can be slow server-side, hence the generous timeout.

This transport:
  * keeps a minimum inter-request interval so a tight ingest loop stays
    polite,
  * handles HTTP 429 and 5xx with exponential backoff + full jitter and
    honours the ``Retry-After`` header when the server sends one,
  * raises immediately on other 4xx — RePORTER returns a JSON *array of
    strings* for validation errors (e.g. limit > 500, offset > 14,999),
    which won't fix themselves on retry, so the message is surfaced
    verbatim,
  * treats a 404 as an empty result envelope rather than raising.

The opener is injectable so every retry / backoff / parse path is unit
tested with a fake server and no socket — the same testability contract
the rest of RCM-MC's public-data clients follow. Because requests are
POSTs, the opener signature carries the encoded body:
``(url, data, headers, timeout_s) -> RawResponse``.
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .endpoints import NIH_REPORTER_BASE

USER_AGENT = "rcm-connectors/nih_reporter"
DEFAULT_BASE_URL = NIH_REPORTER_BASE

# Conservative defaults. Overridable via the constructor; documented as a
# floor, not a contract — verify live at api.reporter.nih.gov.
_DEFAULT_MIN_INTERVAL_S = 1.0        # NIH asks for <= 1 request/second
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0
_DEFAULT_TIMEOUT_S = 60.0            # deep offsets are slow server-side

# Empty-result envelope returned on a 404 (mirrors the live search shape).
_EMPTY_PAYLOAD: Dict[str, Any] = {
    "meta": {"total": 0, "offset": 0, "limit": 0},
    "results": [],
}


class NihReporterApiError(RuntimeError):
    """Raised when RePORTER is unreachable or returns an unrecoverable error."""


@dataclass(frozen=True)
class RawResponse:
    """A minimal HTTP response the retry loop can reason about.

    Injectable openers return this so tests can assert on 429 +
    ``Retry-After`` handling without a real socket. ``headers`` keys are
    lower-cased.
    """

    status: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def header(self, name: str) -> Optional[str]:
        return self.headers.get(name.lower())


# Opener signature: (full_url, post_body_bytes, headers, timeout_s) -> RawResponse.
Opener = Callable[[str, bytes, Dict[str, str], float], RawResponse]


def _default_opener(url: str, data: bytes, headers: Dict[str, str],
                    timeout_s: float) -> RawResponse:
    """urllib POST opener that never raises on HTTP status — it folds
    HTTPError into a :class:`RawResponse` so the retry loop owns all
    status logic."""
    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return RawResponse(status=resp.status, headers=hdrs, body=raw)
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
class NihReporterTransport:
    """Throttled, retrying JSON-POST transport against ``api.reporter.nih.gov``."""

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
    def from_env(cls, **overrides: Any) -> "NihReporterTransport":
        """Build a transport. RePORTER has no API key; env only tunes the
        user agent so a shared crawler can identify itself."""
        params: Dict[str, Any] = {}
        ua = os.environ.get("NIH_REPORTER_USER_AGENT")
        if ua:
            params["user_agent"] = ua
        params.update(overrides)
        return cls(**params)

    def build_url(self, path: str) -> str:
        """Pure URL builder. RePORTER carries everything in the POST body,
        so there is no query string to merge — this exists to keep the
        estate's transport surface uniform and test-assertable."""
        return f"{self.base_url}{path}"

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
                    return min(float(ra), self.backoff_cap_s)
                except ValueError:
                    pass  # HTTP-date form is rare here; fall through
        ceiling = min(self.backoff_cap_s, self.backoff_base_s * (2 ** attempt))
        return ceiling * rand()  # full jitter in [0, ceiling)

    def post_json(
        self,
        path: str,
        body: Dict[str, Any],
        *,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
        rand: Callable[[], float] = random.random,
    ) -> Dict[str, Any]:
        """Issue one POST, parse JSON, retrying 429/5xx/transport errors.

        Returns the decoded RePORTER payload
        (``{"meta": {"total": ...}, "results": [...]}``). A 404 returns an
        empty-results envelope. Raises :class:`NihReporterApiError` only
        after exhausting retries or on an unrecoverable 4xx (RePORTER's
        validation errors — bad limit/offset/criteria — arrive as 400
        with a JSON array of message strings; surfaced verbatim).
        """
        opener = opener or _default_opener
        url = self.build_url(path)
        # separators + sort_keys keep the encoded body byte-stable so test
        # assertions on captured requests are deterministic.
        data = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        last_status = -1
        last_detail = ""
        for attempt in range(self.max_retries + 1):
            self._throttle(sleep, now)
            resp = opener(url, data, headers, self.timeout_s)
            self._last_call_s = now()
            self.requests_made += 1
            status = resp.status

            if status == 200:
                return self._parse(resp.body, url)
            if status == 404:
                # No matching records — an empty list, not a failure.
                return {"meta": dict(_EMPTY_PAYLOAD["meta"]), "results": []}
            if status == 429 or status >= 500 or status == 0:
                last_status, last_detail = status, _short_body(resp.body)
                if attempt < self.max_retries:
                    sleep(self._backoff_seconds(attempt, resp, rand))
                    continue
                break
            # Other 4xx (limit > 500, offset > 14,999, malformed criteria)
            # won't fix on retry — surface RePORTER's message verbatim.
            raise NihReporterApiError(
                f"{url}: HTTP {status} {_short_body(resp.body)}"
            )
        raise NihReporterApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    @staticmethod
    def _parse(body: bytes, url: str) -> Dict[str, Any]:
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            raise NihReporterApiError(
                f"{url}: non-JSON response ({len(body)} bytes)"
            ) from exc
        if not isinstance(doc, dict):
            raise NihReporterApiError(
                f"{url}: unexpected JSON shape {type(doc).__name__}")
        return doc


def _short_body(body: bytes, limit: int = 200) -> str:
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        text = repr(body[:limit])
    text = " ".join(text.split())
    return text[:limit]
