"""HTTP transport for the CMS Provider Data Catalog (DKAN): retry + backoff.

The Provider Data Catalog API (``data.cms.gov/provider-data``) is public
and needs no key. It publishes no hard rate limit, so we default to a
conservative inter-request floor (a courtesy default, NOT a documented
contract — verify at data.cms.gov before a bulk run).

Live-verified facts this transport encodes (probed 2026-07-06):

  * the datastore accepts ``limit`` up to **1500** — a larger value is a
    hard 400 ("must be less than or equal 1500"). We default to a polite
    500 per page (:data:`DEFAULT_PAGE_SIZE`) and clamp callers at
    :data:`MAX_PAGE_SIZE`;
  * the datastore envelope is ``{"results": [...], "count": N, "query":
    {...}, "schema": {...}}`` and ``count`` is always present;
  * the metastore catalog returns a bare JSON **array**, so
    :meth:`get_json` must tolerate both dict and list payloads;
  * an unknown dataset/index is a 404 with a JSON message — treated here
    as an empty results envelope, not a failure, so a speculative
    ``fetch_dataset`` on a stale identifier degrades gracefully.

This transport handles HTTP 429 and 5xx with exponential backoff + full
jitter and honours the ``Retry-After`` header when the server sends one.
The opener is injectable so every retry / backoff / parse path is unit
tested with a fake server and no socket — the same testability contract
the rest of RCM-MC's public-data clients follow.
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = (
    "rcm-connectors/provider_data (github.com/DrewThomas09/RCM; "
    "commercial-diligence research)"
)
DEFAULT_BASE_URL = "https://data.cms.gov/provider-data"

# Live-verified paging bounds (see module docstring).
DEFAULT_PAGE_SIZE = 500
MAX_PAGE_SIZE = 1500

# Conservative defaults. Overridable via the constructor; documented as a
# floor, not a contract — verify live at data.cms.gov.
_DEFAULT_MIN_INTERVAL_S = 0.25        # ~240 req/min, deliberately polite
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0

# Empty-result envelope returned on a 404 (mirrors the live datastore
# shape minus the echo-back "query"/"schema" blocks nothing reads).
_EMPTY_PAYLOAD: Dict[str, Any] = {"results": [], "count": 0}

JsonPayload = Union[Dict[str, Any], List[Any]]


class ProviderDataApiError(RuntimeError):
    """Raised when the API is unreachable or returns an unrecoverable error."""


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


# Opener signature: (full_url, headers, timeout_s) -> RawResponse.
Opener = Callable[[str, Dict[str, str], float], RawResponse]


def _default_opener(url: str, headers: Dict[str, str], timeout_s: float) -> RawResponse:
    """urllib opener that never raises on HTTP status — it folds HTTPError
    into a :class:`RawResponse` so the retry loop owns all status logic."""
    req = Request(url, headers=headers)
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
class ProviderDataTransport:
    """Throttled, retrying JSON transport against ``data.cms.gov/provider-data``."""

    user_agent: str = USER_AGENT
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = 30.0
    min_interval_s: float = _DEFAULT_MIN_INTERVAL_S
    max_retries: int = _DEFAULT_MAX_RETRIES
    backoff_base_s: float = _DEFAULT_BACKOFF_BASE_S
    backoff_cap_s: float = _DEFAULT_BACKOFF_CAP_S
    _last_call_s: float = field(default=0.0, repr=False)
    requests_made: int = field(default=0, repr=False)

    @classmethod
    def from_env(cls, **overrides: Any) -> "ProviderDataTransport":
        """Build a transport. No key exists for the PDC; env only tunes
        the user agent so a shared crawler can identify itself."""
        params: Dict[str, Any] = {}
        ua = os.environ.get("PROVIDER_DATA_USER_AGENT")
        if ua:
            params["user_agent"] = ua
        params.update(overrides)
        return cls(**params)

    def build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Pure URL builder with stable param ordering.

        Stable (sorted) ordering keeps URLs — and test assertions —
        deterministic. DKAN ``conditions[i][...]`` bracket keys sort
        adjacently, so grouped condition triples stay together.
        """
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
                    return min(float(ra), self.backoff_cap_s)
                except ValueError:
                    pass  # HTTP-date form is rare here; fall through
        ceiling = min(self.backoff_cap_s, self.backoff_base_s * (2 ** attempt))
        return ceiling * rand()  # full jitter in [0, ceiling)

    def get_json(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
        rand: Callable[[], float] = random.random,
    ) -> JsonPayload:
        """Issue one GET, parse JSON, retrying 429/5xx/transport errors.

        Returns the decoded payload: a dict for datastore queries
        (``{"results": [...], "count": N, ...}``), a list for the
        metastore catalog. A 404 returns an empty datastore envelope.
        Raises :class:`ProviderDataApiError` only after exhausting
        retries or on an unrecoverable 4xx.
        """
        opener = opener or _default_opener
        url = self.build_url(path, params)
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        last_status = -1
        last_detail = ""
        for attempt in range(self.max_retries + 1):
            self._throttle(sleep, now)
            resp = opener(url, headers, self.timeout_s)
            self._last_call_s = now()
            self.requests_made += 1
            status = resp.status

            if status == 200:
                return self._parse(resp.body, url)
            if status == 404:
                # Unknown dataset/index — an empty result, not a failure.
                return dict(_EMPTY_PAYLOAD)
            if status == 429 or status >= 500 or status == 0:
                last_status, last_detail = status, _short_body(resp.body)
                if attempt < self.max_retries:
                    sleep(self._backoff_seconds(attempt, resp, rand))
                    continue
                break
            # Other 4xx (400 bad query, 403 forbidden) won't fix on retry.
            raise ProviderDataApiError(
                f"{url}: HTTP {status} {_short_body(resp.body)}"
            )
        raise ProviderDataApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    @staticmethod
    def _parse(body: bytes, url: str) -> JsonPayload:
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ProviderDataApiError(
                f"{url}: non-JSON response ({len(body)} bytes)"
            ) from exc
        # Both live shapes are legitimate here: the metastore catalog is a
        # bare array; datastore queries are an object envelope.
        if not isinstance(doc, (dict, list)):
            raise ProviderDataApiError(
                f"{url}: unexpected JSON shape {type(doc).__name__}")
        return doc


def _short_body(body: bytes, limit: int = 200) -> str:
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        text = repr(body[:limit])
    text = " ".join(text.split())
    return text[:limit]
