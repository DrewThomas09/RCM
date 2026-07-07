"""HTTP transport for the CMS Coverage API: rate-limit floor + backoff.

The CMS Coverage API (``api.coverage.cms.gov``, the Medicare Coverage
Database) is public and needs no key. It publishes no hard rate limit,
so we default to a conservative inter-request floor (confirm current
limits at the CMS Medicare Coverage Database developer portal before a
bulk run — this is a courtesy default, NOT a documented contract).

This transport:
  * reads an optional key from ``$CMS_COVERAGE_API_KEY`` and degrades
    gracefully when it is absent (the API needs none — this is only a
    forward-compatible seam),
  * keeps a minimum inter-request interval so a tight ingest loop stays
    polite,
  * handles HTTP 429 and 5xx with exponential backoff + full jitter and
    honours the ``Retry-After`` header when the server sends one,
  * treats a 404 as an empty result envelope rather than raising.

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
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_DEFAULT_USER_AGENT = (
    "rcm-mc/cms-coverage-connector (github.com/DrewThomas09/RCM; "
    "commercial-diligence research)"
)
_CMS_COVERAGE_BASE = "https://api.coverage.cms.gov"

# Conservative defaults. Overridable via the constructor; documented as a
# floor, not a contract — verify live at the CMS MCD developer portal.
_DEFAULT_MIN_INTERVAL_S = 0.25        # ~240 req/min, deliberately polite
_DEFAULT_MAX_RETRIES = 5
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0

# Empty-result envelope returned on a 404 (mirrors the live list shape).
_EMPTY_PAYLOAD: Dict[str, Any] = {
    "result": {"count": 0, "total": 0, "next_page_token": None, "items": []}
}


class CmsCoverageApiError(RuntimeError):
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
class CmsCoverageTransport:
    """Throttled, retrying JSON transport against ``api.coverage.cms.gov``."""

    api_key: Optional[str] = None
    user_agent: str = _DEFAULT_USER_AGENT
    base_url: str = _CMS_COVERAGE_BASE
    timeout_s: float = 30.0
    min_interval_s: float = _DEFAULT_MIN_INTERVAL_S
    max_retries: int = _DEFAULT_MAX_RETRIES
    backoff_base_s: float = _DEFAULT_BACKOFF_BASE_S
    backoff_cap_s: float = _DEFAULT_BACKOFF_CAP_S
    _last_call_s: float = field(default=0.0, repr=False)
    requests_made: int = field(default=0, repr=False)

    @classmethod
    def from_env(cls, **overrides: Any) -> "CmsCoverageTransport":
        """Build a transport, reading an optional key from
        ``$CMS_COVERAGE_API_KEY``.

        Absent key is fine — the CMS Coverage API is fully public. The
        key is a forward-compatible seam only.
        """
        key = os.environ.get("CMS_COVERAGE_API_KEY") or None
        params: Dict[str, Any] = {"api_key": key}
        params.update(overrides)
        return cls(**params)

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    def build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Pure URL builder; merges the key in when configured."""
        merged: Dict[str, Any] = dict(params or {})
        if self.api_key:
            merged.setdefault("api_key", self.api_key)
        # Stable ordering keeps URLs (and test assertions) deterministic.
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
                    # Clamp to [0, cap]: a negative (or NaN) Retry-After
                    # must never reach time.sleep(), which raises
                    # ValueError and would abort the retry loop.
                    return max(0.0, min(float(ra), self.backoff_cap_s))
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
    ) -> Dict[str, Any]:
        """Issue one GET, parse JSON, retrying 429/5xx/transport errors.

        Returns the decoded CMS Coverage payload. A 404 returns an empty
        result envelope. Raises :class:`CmsCoverageApiError` only after
        exhausting retries or on an unrecoverable 4xx.
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
                # No matching document/report — an empty list, not a failure.
                return {"result": dict(_EMPTY_PAYLOAD["result"])}
            if status == 429 or status >= 500 or status == 0:
                last_status, last_detail = status, _short_body(resp.body)
                if attempt < self.max_retries:
                    sleep(self._backoff_seconds(attempt, resp, rand))
                    continue
                break
            # Other 4xx (400 bad query, 403 forbidden) won't fix on retry.
            raise CmsCoverageApiError(
                f"{url}: HTTP {status} {_short_body(resp.body)}"
            )
        raise CmsCoverageApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    @staticmethod
    def _parse(body: bytes, url: str) -> Dict[str, Any]:
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            raise CmsCoverageApiError(
                f"{url}: non-JSON response ({len(body)} bytes)"
            ) from exc
        if not isinstance(doc, dict):
            raise CmsCoverageApiError(
                f"{url}: unexpected JSON shape {type(doc).__name__}")
        return doc


def _short_body(body: bytes, limit: int = 200) -> str:
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        text = repr(body[:limit])
    text = " ".join(text.split())
    return text[:limit]
